from __future__ import annotations

import asyncio
import json
import logging
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal
from uuid import UUID, uuid4

from fastapi import WebSocket, WebSocketDisconnect
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError
from app.db.archive_queries import get_conversation
from app.db.models import Conversation, Message, Project, Settings, User
from app.db.session import SessionLocal
from app.domains.chat.title_summary import enqueue_title_summary_job_if_ready
from app.domains.codex.runtime import (
    RuntimeExecutionError,
    RuntimeStoppedError,
    RuntimeThreadResumeError,
    RuntimeTimeoutError,
    RuntimeUnavailableError,
    codex_process_runner,
)
from app.domains.files.service import assign_files_to_message
from app.domains.files.workspace_service import resolve_workspace_file_refs
from app.domains.locks.service import LockState, conversation_lock_service
from app.domains.projects.service import (
    ProjectResolution,
    build_project_context_block,
    build_project_options,
    get_project,
    resolve_project_for_content,
    sanitize_pending_project_clarification,
    validate_project_paths,
)

logger = logging.getLogger("app.api")


class ResumeEvent(BaseModel):
    model_config = ConfigDict(extra="ignore")

    type: Literal["resume"]
    conversation_id: UUID


class SendMessageEvent(BaseModel):
    model_config = ConfigDict(extra="ignore")

    type: Literal["send_message"]
    conversation_id: UUID
    content: str
    file_ids: list[UUID] = Field(default_factory=list)
    file_refs: list["WorkspaceFileRefInput"] = Field(default_factory=list)
    client_message_id: str | None = None


class WorkspaceFileRefInput(BaseModel):
    model_config = ConfigDict(extra="ignore")

    kind: Literal["workspace"] = "workspace"
    relative_path: str


class StopEvent(BaseModel):
    model_config = ConfigDict(extra="ignore")

    type: Literal["stop"]
    conversation_id: UUID


class ProjectClarifyReplyEvent(BaseModel):
    model_config = ConfigDict(extra="ignore")

    type: Literal["project_clarify_reply"]
    conversation_id: UUID
    selection: int


class CreateProjectEvent(BaseModel):
    model_config = ConfigDict(extra="ignore")

    type: Literal["create_project"]
    conversation_id: UUID
    name: str
    root_path: str
    index_md_path: str | None = None


ClientEvent = ResumeEvent | SendMessageEvent | StopEvent | ProjectClarifyReplyEvent | CreateProjectEvent


class ClientEventError(Exception):
    def __init__(self, *, code: str, message: str, details: dict[str, object]) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details


class ChatWebSocketService:
    def __init__(self) -> None:
        self._state_lock = asyncio.Lock()
        self._subscriptions: dict[UUID, set[WebSocket]] = defaultdict(set)
        self._socket_subscriptions: dict[WebSocket, set[UUID]] = defaultdict(set)
        self._active_turn_tasks: dict[UUID, asyncio.Task[None]] = {}
        self._active_turn_stop_events: dict[UUID, asyncio.Event] = {}

    async def handle_connection(self, websocket: WebSocket, *, user: User) -> None:
        request_id = websocket.headers.get("x-request-id") or str(uuid4())
        connection_id = str(uuid4())
        await websocket.accept()
        logger.info(
            "websocket_connected",
            extra={
                "event_data": {
                    "user_id": str(user.id),
                    "request_id": request_id,
                    "connection_id": connection_id,
                }
            },
        )

        try:
            while True:
                payload_text = await websocket.receive_text()
                try:
                    event = _parse_client_event(payload_text)
                except ClientEventError as exc:
                    await self._send_error(
                        websocket,
                        code=exc.code,
                        message=exc.message,
                        details=exc.details,
                    )
                    continue

                if isinstance(event, ResumeEvent):
                    await self._handle_resume(websocket, event=event)
                    continue

                if isinstance(event, StopEvent):
                    await self._handle_stop(websocket, user=user, event=event)
                    continue

                if isinstance(event, ProjectClarifyReplyEvent):
                    await self._handle_project_clarify_reply(
                        websocket,
                        user=user,
                        request_id=request_id,
                        connection_id=connection_id,
                        event=event,
                    )
                    continue

                if isinstance(event, CreateProjectEvent):
                    await self._handle_create_project(
                        websocket,
                        user=user,
                        request_id=request_id,
                        connection_id=connection_id,
                        event=event,
                    )
                    continue

                await self._handle_send_message(
                    websocket,
                    user=user,
                    request_id=request_id,
                    connection_id=connection_id,
                    event=event,
                )
        except WebSocketDisconnect:
            logger.info(
                "websocket_disconnected",
                extra={
                    "event_data": {
                        "user_id": str(user.id),
                        "request_id": request_id,
                        "connection_id": connection_id,
                    }
                },
            )
        except RuntimeError as exc:
            # Some disconnect paths surface as RuntimeError instead of WebSocketDisconnect.
            if "WebSocket is not connected" in str(exc):
                logger.info(
                    "websocket_disconnected",
                    extra={
                        "event_data": {
                            "user_id": str(user.id),
                            "request_id": request_id,
                            "connection_id": connection_id,
                            "reason": "not_connected_runtime",
                        }
                    },
                )
            else:
                raise
        finally:
            await self._unsubscribe_socket(websocket)

    async def _handle_resume(self, websocket: WebSocket, *, event: ResumeEvent) -> None:
        conversation_id = event.conversation_id
        pending_clarification: dict[str, Any] | None = None
        with SessionLocal() as db:
            conversation = get_conversation(db, conversation_id, include_archived=False)
            if conversation is None:
                await self._send_error(
                    websocket,
                    code="NOT_FOUND",
                    message="Conversation not found",
                    details={"conversation_id": str(conversation_id)},
                )
                return

            latest_assistant_message = db.execute(
                select(Message)
                .where(
                    Message.conversation_id == conversation_id,
                    Message.role == "assistant",
                    Message.archived_at.is_(None),
                )
                .order_by(Message.created_at.desc())
                .limit(1)
            ).scalar_one_or_none()
            pending_clarification = sanitize_pending_project_clarification(
                conversation.project_clarification_json,
            )

        await self._subscribe_socket_to_conversation(websocket, conversation_id)
        await self._emit_busy_state_for_socket(websocket, conversation_id=conversation_id)
        if pending_clarification is not None:
            await self._send_pending_project_clarification(
                websocket,
                conversation_id=conversation_id,
                payload=pending_clarification,
            )

        if latest_assistant_message is not None:
            await self._send_json(
                websocket,
                {
                    "type": "assistant_done",
                    "conversation_id": str(conversation_id),
                    "message_id": str(latest_assistant_message.id),
                    "content": latest_assistant_message.content,
                    "status": latest_assistant_message.metadata_json.get("turn_status", "completed"),
                    "partial": bool(latest_assistant_message.metadata_json.get("partial", False)),
                    **_assistant_author_fields(),
                },
            )

    async def _handle_stop(self, websocket: WebSocket, *, user: User, event: StopEvent) -> None:
        conversation_id = event.conversation_id
        with SessionLocal() as db:
            conversation = get_conversation(db, conversation_id, include_archived=False)
            if conversation is None:
                await self._send_error(
                    websocket,
                    code="NOT_FOUND",
                    message="Conversation not found",
                    details={"conversation_id": str(conversation_id)},
                )
                return

            state = conversation_lock_service.get_state(db, conversation_id=conversation_id)

        await self._subscribe_socket_to_conversation(websocket, conversation_id)

        if not state.is_busy or state.locked_by != user.id:
            await self._send_error(
                websocket,
                code="STOP_NOT_ALLOWED",
                message="No active turn for this conversation can be stopped",
                details={
                    "conversation_id": str(conversation_id),
                    "busy": state.is_busy,
                },
            )
            return

        task = self._active_turn_tasks.get(conversation_id)
        stop_event = self._active_turn_stop_events.get(conversation_id)
        if stop_event is not None:
            stop_event.set()
        if task is not None and not task.done():
            task.cancel()

    async def _handle_send_message(
        self,
        websocket: WebSocket,
        *,
        user: User,
        request_id: str,
        connection_id: str,
        event: SendMessageEvent,
    ) -> None:
        conversation_id = event.conversation_id
        content = event.content.strip()
        if not content:
            await self._send_error(
                websocket,
                code="VALIDATION_ERROR",
                message="Message content cannot be empty",
                details={"conversation_id": str(conversation_id)},
            )
            return

        with SessionLocal() as db:
            conversation = get_conversation(db, conversation_id, include_archived=False)
            if conversation is None:
                await self._send_error(
                    websocket,
                    code="NOT_FOUND",
                    message="Conversation not found",
                    details={"conversation_id": str(conversation_id)},
                )
                return

        await self._subscribe_socket_to_conversation(websocket, conversation_id)
        owner_token = str(uuid4())
        with SessionLocal() as db:
            acquire_result = conversation_lock_service.acquire(
                db,
                conversation_id=conversation_id,
                user_id=user.id,
                owner_token=owner_token,
                metadata={
                    "connection_id": connection_id,
                    "request_id": request_id,
                    "source": "websocket",
                },
            )

        if not acquire_result.acquired:
            await self._broadcast_thread_busy_state(conversation_id, state=acquire_result.state)
            await self._send_error(
                websocket,
                code="THREAD_BUSY",
                message="thread busy",
                details={
                    "conversation_id": str(conversation_id),
                    "busy": True,
                    "locked_by": str(acquire_result.state.locked_by) if acquire_result.state.locked_by else None,
                },
            )
            return

        await self._broadcast_thread_busy_state(conversation_id, state=acquire_result.state)
        stop_event = asyncio.Event()
        task = asyncio.create_task(
            self._run_turn(
                conversation_id=conversation_id,
                user=user,
                request_id=request_id,
                content=content,
                file_ids=event.file_ids,
                file_refs=event.file_refs,
                client_message_id=event.client_message_id,
                owner_token=owner_token,
                stop_event=stop_event,
            )
        )
        self._active_turn_tasks[conversation_id] = task
        self._active_turn_stop_events[conversation_id] = stop_event

    async def _handle_project_clarify_reply(
        self,
        websocket: WebSocket,
        *,
        user: User,
        request_id: str,
        connection_id: str,
        event: ProjectClarifyReplyEvent,
    ) -> None:
        await self._subscribe_socket_to_conversation(websocket, event.conversation_id)
        owner_token = str(uuid4())
        with SessionLocal() as db:
            acquire_result = conversation_lock_service.acquire(
                db,
                conversation_id=event.conversation_id,
                user_id=user.id,
                owner_token=owner_token,
                metadata={
                    "connection_id": connection_id,
                    "request_id": request_id,
                    "source": "websocket_project_clarify_reply",
                },
            )

        if not acquire_result.acquired:
            await self._broadcast_thread_busy_state(event.conversation_id, state=acquire_result.state)
            await self._send_error(
                websocket,
                code="THREAD_BUSY",
                message="thread busy",
                details={"conversation_id": str(event.conversation_id), "busy": True},
            )
            return

        await self._broadcast_thread_busy_state(event.conversation_id, state=acquire_result.state)
        stop_event = asyncio.Event()
        task = asyncio.create_task(
            self._resolve_project_selection(
                conversation_id=event.conversation_id,
                selection=event.selection,
                user=user,
                request_id=request_id,
                owner_token=owner_token,
                stop_event=stop_event,
            )
        )
        self._active_turn_tasks[event.conversation_id] = task
        self._active_turn_stop_events[event.conversation_id] = stop_event

    async def _handle_create_project(
        self,
        websocket: WebSocket,
        *,
        user: User,
        request_id: str,
        connection_id: str,
        event: CreateProjectEvent,
    ) -> None:
        await self._subscribe_socket_to_conversation(websocket, event.conversation_id)
        owner_token = str(uuid4())
        with SessionLocal() as db:
            acquire_result = conversation_lock_service.acquire(
                db,
                conversation_id=event.conversation_id,
                user_id=user.id,
                owner_token=owner_token,
                metadata={
                    "connection_id": connection_id,
                    "request_id": request_id,
                    "source": "websocket_create_project",
                },
            )

        if not acquire_result.acquired:
            await self._broadcast_thread_busy_state(event.conversation_id, state=acquire_result.state)
            await self._send_error(
                websocket,
                code="THREAD_BUSY",
                message="thread busy",
                details={"conversation_id": str(event.conversation_id), "busy": True},
            )
            return

        await self._broadcast_thread_busy_state(event.conversation_id, state=acquire_result.state)
        stop_event = asyncio.Event()
        task = asyncio.create_task(
            self._create_project_and_resume_pending_turn(
                conversation_id=event.conversation_id,
                name=event.name,
                root_path=event.root_path,
                index_md_path=event.index_md_path,
                user=user,
                request_id=request_id,
                owner_token=owner_token,
                stop_event=stop_event,
            )
        )
        self._active_turn_tasks[event.conversation_id] = task
        self._active_turn_stop_events[event.conversation_id] = stop_event

    async def _run_turn(
        self,
        *,
        conversation_id: UUID,
        user: User,
        request_id: str,
        content: str,
        file_ids: list[UUID],
        file_refs: list[WorkspaceFileRefInput],
        client_message_id: str | None,
        owner_token: str,
        stop_event: asyncio.Event,
    ) -> None:
        assistant_content = ""
        thread_id: str | None = None
        turn_id: str | None = None
        message_file_paths: list[str] = []
        project_context_block: str | None = None
        heartbeat_stop = asyncio.Event()
        heartbeat_task = asyncio.create_task(
            self._heartbeat_lock(
                conversation_id=conversation_id,
                owner_token=owner_token,
                stop_event=heartbeat_stop,
            )
        )
        try:
            sandbox_mode = "workspace-write"
            with SessionLocal() as db:
                conversation = get_conversation(db, conversation_id, include_archived=False)
                if conversation is None:
                    await self._broadcast_error(
                        conversation_id,
                        code="NOT_FOUND",
                        message="Conversation not found",
                    )
                    return

                project_resolution = self._apply_project_preflight(
                    db,
                    conversation=conversation,
                    user=user,
                    content=content,
                    file_ids=file_ids,
                    file_refs=file_refs,
                    client_message_id=client_message_id,
                    request_id=request_id,
                )
                if project_resolution.mode == "clarify":
                    await self._broadcast_pending_project_clarification(conversation)
                    return
                if project_resolution.project is not None:
                    project_context_block = build_project_context_block(project_resolution.project)
                    await self._broadcast_conversation_project_state(
                        conversation_id=conversation_id,
                        project=project_resolution.project,
                        project_mode=conversation.project_mode,
                        pending_clarification=None,
                    )

                thread_id = conversation.codex_thread_id
                settings_row = db.get(Settings, 1)
                execution_mode_default = (
                    settings_row.execution_mode_default if settings_row is not None else "regular"
                )
                sandbox_mode = codex_process_runner.sandbox_mode_for_execution_mode(execution_mode_default)
                user_message = Message(
                    conversation_id=conversation_id,
                    role="user",
                    content=content,
                    user_id=user.id,
                    metadata_json={
                        "source": "websocket",
                        "request_id": request_id,
                        "client_message_id": client_message_id,
                        **_user_author_metadata(user),
                    },
                )
                db.add(user_message)
                db.commit()
                db.refresh(user_message)

                user_message_id = str(user_message.id)
                user_message_role = user_message.role
                user_message_content = user_message.content
                user_message_created_at = user_message.created_at.isoformat()

                attached_files = assign_files_to_message(
                    db,
                    conversation_id=conversation_id,
                    message_id=user_message.id,
                    file_ids=file_ids,
                )
                resolved_workspace_refs = resolve_workspace_file_refs(
                    file_ref.relative_path
                    for file_ref in file_refs
                    if file_ref.kind == "workspace"
                )

                attached_refs = []
                for attached_file in attached_files:
                    attached_refs.append(
                        {
                            "id": str(attached_file.id),
                            "original_name": attached_file.original_name,
                            "storage_path": attached_file.storage_path,
                            "download_path": f"/api/files/{attached_file.id}",
                        }
                    )
                user_message.metadata_json = {
                    **(user_message.metadata_json or {}),
                    "attached_files": attached_refs,
                    "workspace_refs": [
                        {
                            "kind": str(ref["kind"]),
                            "relative_path": str(ref["relative_path"]),
                            "display_name": str(ref["display_name"]),
                        }
                        for ref in resolved_workspace_refs
                    ],
                }
                user_message_metadata = dict(user_message.metadata_json or {})
                uploads_root = Path(get_settings().uploads_path).expanduser().resolve()
                message_file_paths = []
                for attached_file in attached_files:
                    resolved_path = (uploads_root / attached_file.storage_path).resolve()
                    if uploads_root not in resolved_path.parents:
                        raise AppError(
                            status_code=400,
                            code="BAD_REQUEST",
                            message="Invalid attached file path",
                            details={"file_id": str(attached_file.id)},
                        )
                    message_file_paths.append(str(resolved_path))
                message_file_paths.extend(str(ref["absolute_path"]) for ref in resolved_workspace_refs)
                db.commit()

            await self._broadcast_to_conversation(
                conversation_id,
                {
                    "type": "message_created",
                    "conversation_id": str(conversation_id),
                    "message": {
                        "id": user_message_id,
                        "role": user_message_role,
                        "content": user_message_content,
                        "author_user_id": str(user.id),
                        "author_display_name": user.display_name,
                        "author_profile_picture_url": user.profile_picture_url,
                        "is_current_user_author": None,
                        "created_at": user_message_created_at,
                        "files": attached_refs,
                        "metadata_json": user_message_metadata,
                        "client_message_id": client_message_id,
                    },
                },
            )
            await self._broadcast_assistant_waiting(conversation_id)

            prompt = _build_prompt_with_files(
                content=content,
                file_paths=message_file_paths,
                project_context_block=project_context_block,
            )
            turn_result = await codex_process_runner.run_turn(
                prompt=prompt,
                existing_thread_id=thread_id,
                sandbox_mode=sandbox_mode,
                conversation_id=conversation_id,
                user_id=user.id,
                request_id=request_id,
                on_delta=lambda delta: asyncio.create_task(
                    self._broadcast_to_conversation(
                        conversation_id,
                        {
                            "type": "assistant_delta",
                            "conversation_id": str(conversation_id),
                            "delta": delta,
                        },
                    )
                ),
                stop_event=stop_event,
            )
            assistant_content = turn_result.content
            thread_id = turn_result.thread_id
            turn_id = turn_result.turn_id

            with SessionLocal() as db:
                conversation = get_conversation(db, conversation_id, include_archived=False)
                if conversation is None:
                    return

                if conversation.codex_thread_id and conversation.codex_thread_id != thread_id:
                    raise RuntimeThreadResumeError(
                        "Codex runtime returned a different thread id than persisted for this conversation"
                    )
                if conversation.codex_thread_id is None:
                    conversation.codex_thread_id = thread_id

                assistant_message = Message(
                    conversation_id=conversation_id,
                    role="assistant",
                    content=assistant_content,
                    metadata_json={
                        "partial": False,
                        "turn_status": "completed",
                        "request_id": request_id,
                        "user_id": str(user.id),
                        "thread_id": thread_id,
                        "turn_id": turn_id,
                        "runtime": "codex_app_server_stdio",
                    },
                )
                db.add(assistant_message)
                db.commit()
                db.refresh(assistant_message)
                enqueue_title_summary_job_if_ready(db, conversation_id=conversation_id)
                db.commit()

            await self._broadcast_to_conversation(
                conversation_id,
                {
                    "type": "assistant_done",
                    "conversation_id": str(conversation_id),
                    "message_id": str(assistant_message.id),
                    "content": assistant_content,
                    "status": "completed",
                    "partial": False,
                    **_assistant_author_fields(),
                },
            )
        except AppError as exc:
            await self._broadcast_to_conversation(
                conversation_id,
                {
                    "type": "error",
                    "conversation_id": str(conversation_id),
                    "code": exc.code,
                    "message": exc.message,
                    "details": {
                        **exc.details,
                        "conversation_id": str(conversation_id),
                        "busy": False,
                    },
                },
            )
            return
        except RuntimeTimeoutError:
            await self._persist_partial_if_meaningful(
                conversation_id=conversation_id,
                user_id=user.id,
                request_id=request_id,
                content=assistant_content,
                thread_id=thread_id,
                turn_id=turn_id,
                status="timed_out",
                error_code="CODEX_TIMEOUT",
                error_message="Codex runtime timed out",
            )
            await self._broadcast_error(
                conversation_id,
                code="CODEX_TIMEOUT",
                message="Codex runtime timed out",
            )
            return
        except RuntimeUnavailableError as exc:
            await self._persist_partial_if_meaningful(
                conversation_id=conversation_id,
                user_id=user.id,
                request_id=request_id,
                content=assistant_content,
                thread_id=thread_id,
                turn_id=turn_id,
                status="failed",
                error_code="CODEX_UNAVAILABLE",
                error_message=str(exc),
            )
            await self._broadcast_error(
                conversation_id,
                code="CODEX_UNAVAILABLE",
                message=str(exc),
            )
            return
        except RuntimeStoppedError:
            await self._persist_stop_result(
                conversation_id=conversation_id,
                user_id=user.id,
                request_id=request_id,
                content=assistant_content,
                thread_id=thread_id,
                turn_id=turn_id,
            )
            return
        except RuntimeThreadResumeError:
            await self._broadcast_error(
                conversation_id,
                code="THREAD_RESUME_FAILED",
                message="Conversation continuity check failed; could not resume existing thread",
            )
            return
        except RuntimeExecutionError as exc:
            await self._persist_partial_if_meaningful(
                conversation_id=conversation_id,
                user_id=user.id,
                request_id=request_id,
                content=assistant_content,
                thread_id=thread_id,
                turn_id=turn_id,
                status="failed",
                error_code="CODEX_RUNTIME_ERROR",
                error_message=str(exc),
            )
            await self._broadcast_error(
                conversation_id,
                code="CODEX_RUNTIME_ERROR",
                message=str(exc),
            )
            return
        except Exception:
            logger.exception(
                "websocket_turn_runtime_failure",
                extra={"event_data": {"conversation_id": str(conversation_id), "user_id": str(user.id)}},
            )
            await self._persist_partial_if_meaningful(
                conversation_id=conversation_id,
                user_id=user.id,
                request_id=request_id,
                content=assistant_content,
                thread_id=thread_id,
                turn_id=turn_id,
                status="failed",
                error_code="CODEX_RUNTIME_ERROR",
                error_message="Codex runtime failed while processing the turn",
            )
            await self._broadcast_error(
                conversation_id,
                code="CODEX_RUNTIME_ERROR",
                message="Codex runtime failed while processing the turn",
            )
        finally:
            heartbeat_stop.set()
            await heartbeat_task
            self._active_turn_tasks.pop(conversation_id, None)
            self._active_turn_stop_events.pop(conversation_id, None)
            with SessionLocal() as db:
                conversation_lock_service.release(
                    db,
                    conversation_id=conversation_id,
                    owner_token=owner_token,
                )
                current_state = conversation_lock_service.get_state(db, conversation_id=conversation_id)
            await self._broadcast_thread_busy_state(conversation_id, state=current_state)

    def _apply_project_preflight(
        self,
        db: Session,
        *,
        conversation: Conversation,
        user: User,
        content: str,
        file_ids: list[UUID],
        file_refs: list[WorkspaceFileRefInput],
        client_message_id: str | None,
        request_id: str,
    ) -> ProjectResolution:
        resolution = resolve_project_for_content(
            db,
            content=content,
            conversation=conversation,
        )
        if resolution.mode == "clarify":
            conversation.project_clarification_json = {
                "state": "awaiting_selection",
                "question": "Which project are you working on?",
                "options": build_project_options(resolution.options),
                "allow_create": True,
                "pending_user_id": str(user.id),
                "pending_request_id": request_id,
                "pending_content": content,
                "pending_file_ids": [str(file_id) for file_id in file_ids],
                "pending_file_refs": [
                    {"kind": file_ref.kind, "relative_path": file_ref.relative_path}
                    for file_ref in file_refs
                ],
                "pending_client_message_id": client_message_id,
            }
            conversation.project_mode = "unknown"
            db.commit()
            return resolution
        if resolution.project is not None:
            conversation.project_id = resolution.project.id
            conversation.project_mode = "project_bound"
            conversation.project_clarification_json = {}
            db.commit()
            return resolution

        conversation.project_clarification_json = {}
        conversation.project_mode = "general"
        db.commit()
        return resolution

    async def _resolve_project_selection(
        self,
        *,
        conversation_id: UUID,
        selection: int,
        user: User,
        request_id: str,
        owner_token: str,
        stop_event: asyncio.Event,
    ) -> None:
        resumed_turn = False
        try:
            with SessionLocal() as db:
                conversation = get_conversation(db, conversation_id, include_archived=False)
                if conversation is None:
                    await self._broadcast_error(conversation_id, code="NOT_FOUND", message="Conversation not found")
                    return

                pending = sanitize_pending_project_clarification(conversation.project_clarification_json)
                raw_pending = conversation.project_clarification_json if isinstance(conversation.project_clarification_json, dict) else {}
                self._ensure_pending_clarification_ownership(raw_pending, user=user)
                if pending is None or pending.get("state") != "awaiting_selection":
                    await self._broadcast_error(
                        conversation_id,
                        code="PROJECT_SELECTION_NOT_PENDING",
                        message="There is no pending project selection for this conversation",
                    )
                    return

                if selection == 0:
                    conversation.project_clarification_json = {
                        **raw_pending,
                        "state": "awaiting_create",
                        "question": "Create a new project to continue this turn.",
                    }
                    db.commit()
                    await self._broadcast_pending_project_clarification(conversation)
                    return

                options = raw_pending.get("options") if isinstance(raw_pending.get("options"), list) else []
                selected_option = next(
                    (
                        option
                        for option in options
                        if isinstance(option, dict) and option.get("number") == selection
                    ),
                    None,
                )
                if not isinstance(selected_option, dict):
                    await self._broadcast_error(
                        conversation_id,
                        code="INVALID_PROJECT_SELECTION",
                        message="Reply with one of the listed project numbers",
                    )
                    return

                project_id = selected_option.get("id")
                if not isinstance(project_id, str):
                    await self._broadcast_error(
                        conversation_id,
                        code="INVALID_PROJECT_SELECTION",
                        message="Reply with one of the listed project numbers",
                    )
                    return

                project = get_project(db, UUID(project_id))
                if project is None or not project.is_active:
                    await self._broadcast_error(
                        conversation_id,
                        code="PROJECT_NOT_FOUND",
                        message="Selected project is no longer available",
                    )
                    return

                conversation.project_id = project.id
                conversation.project_mode = "project_bound"
                conversation.project_clarification_json = {}
                db.commit()
                pending_turn = _extract_pending_turn_payload(raw_pending)

            await self._broadcast_conversation_project_state(
                conversation_id=conversation_id,
                project=project,
                project_mode="project_bound",
                pending_clarification=None,
            )
            await self._run_turn(
                conversation_id=conversation_id,
                user=user,
                request_id=pending_turn["request_id"] or request_id,
                content=pending_turn["content"],
                file_ids=pending_turn["file_ids"],
                file_refs=pending_turn["file_refs"],
                client_message_id=pending_turn["client_message_id"],
                owner_token=owner_token,
                stop_event=stop_event,
            )
            resumed_turn = True
        except AppError as exc:
            await self._broadcast_to_conversation(
                conversation_id,
                {
                    "type": "error",
                    "conversation_id": str(conversation_id),
                    "code": exc.code,
                    "message": exc.message,
                    "details": {**exc.details, "conversation_id": str(conversation_id), "busy": False},
                },
            )
        finally:
            if resumed_turn:
                return
            self._active_turn_tasks.pop(conversation_id, None)
            self._active_turn_stop_events.pop(conversation_id, None)
            with SessionLocal() as db:
                conversation_lock_service.release(
                    db,
                    conversation_id=conversation_id,
                    owner_token=owner_token,
                )
                current_state = conversation_lock_service.get_state(db, conversation_id=conversation_id)
            await self._broadcast_thread_busy_state(conversation_id, state=current_state)

    async def _create_project_and_resume_pending_turn(
        self,
        *,
        conversation_id: UUID,
        name: str,
        root_path: str,
        index_md_path: str | None,
        user: User,
        request_id: str,
        owner_token: str,
        stop_event: asyncio.Event,
    ) -> None:
        resumed_turn = False
        try:
            normalized_root, normalized_index = validate_project_paths(
                root_path=root_path,
                index_md_path=index_md_path,
            )
            with SessionLocal() as db:
                conversation = get_conversation(db, conversation_id, include_archived=False)
                if conversation is None:
                    await self._broadcast_error(conversation_id, code="NOT_FOUND", message="Conversation not found")
                    return

                raw_pending = conversation.project_clarification_json if isinstance(conversation.project_clarification_json, dict) else {}
                self._ensure_pending_clarification_ownership(raw_pending, user=user)
                pending = sanitize_pending_project_clarification(raw_pending)
                if pending is None or pending.get("state") != "awaiting_create":
                    await self._broadcast_error(
                        conversation_id,
                        code="PROJECT_CREATE_NOT_PENDING",
                        message="Project creation is not pending for this conversation",
                    )
                    return

                project = Project(
                    name=name.strip(),
                    root_path=normalized_root,
                    index_md_path=normalized_index,
                )
                db.add(project)
                db.flush()

                conversation.project_id = project.id
                conversation.project_mode = "project_bound"
                conversation.project_clarification_json = {}
                db.commit()
                pending_turn = _extract_pending_turn_payload(raw_pending)

            await self._broadcast_conversation_project_state(
                conversation_id=conversation_id,
                project=project,
                project_mode="project_bound",
                pending_clarification=None,
            )
            await self._run_turn(
                conversation_id=conversation_id,
                user=user,
                request_id=pending_turn["request_id"] or request_id,
                content=pending_turn["content"],
                file_ids=pending_turn["file_ids"],
                file_refs=pending_turn["file_refs"],
                client_message_id=pending_turn["client_message_id"],
                owner_token=owner_token,
                stop_event=stop_event,
            )
            resumed_turn = True
        except AppError as exc:
            await self._broadcast_to_conversation(
                conversation_id,
                {
                    "type": "error",
                    "conversation_id": str(conversation_id),
                    "code": exc.code,
                    "message": exc.message,
                    "details": {**exc.details, "conversation_id": str(conversation_id), "busy": False},
                },
            )
        except Exception as exc:
            await self._broadcast_error(
                conversation_id,
                code="PROJECT_CREATE_FAILED",
                message=str(exc),
            )
        finally:
            if resumed_turn:
                return
            self._active_turn_tasks.pop(conversation_id, None)
            self._active_turn_stop_events.pop(conversation_id, None)
            with SessionLocal() as db:
                conversation_lock_service.release(
                    db,
                    conversation_id=conversation_id,
                    owner_token=owner_token,
                )
                current_state = conversation_lock_service.get_state(db, conversation_id=conversation_id)
            await self._broadcast_thread_busy_state(conversation_id, state=current_state)

    def _ensure_pending_clarification_ownership(self, payload: dict[str, Any], *, user: User) -> None:
        pending_user_id = payload.get("pending_user_id")
        if isinstance(pending_user_id, str) and pending_user_id != str(user.id):
            raise AppError(
                status_code=403,
                code="PROJECT_SELECTION_FORBIDDEN",
                message="Only the user who triggered the pending clarification can resolve it",
                details={},
            )

    async def _send_pending_project_clarification(
        self,
        websocket: WebSocket,
        *,
        conversation_id: UUID,
        payload: dict[str, Any],
    ) -> None:
        if payload.get("state") == "awaiting_create":
            await self._send_json(
                websocket,
                {
                    "type": "assistant_project_create",
                    "conversation_id": str(conversation_id),
                    "question": payload.get("question"),
                },
            )
            return

        await self._send_json(
            websocket,
            {
                "type": "assistant_clarify",
                "conversation_id": str(conversation_id),
                "question": payload.get("question"),
                "options": payload.get("options", []),
                "expected_reply": "number",
                "allow_create": bool(payload.get("allow_create", True)),
            },
        )

    async def _broadcast_pending_project_clarification(self, conversation: Conversation) -> None:
        payload = sanitize_pending_project_clarification(conversation.project_clarification_json)
        if payload is None:
            return
        await self._broadcast_to_conversation(
            conversation.id,
            {
                "type": "assistant_project_create" if payload.get("state") == "awaiting_create" else "assistant_clarify",
                "conversation_id": str(conversation.id),
                "question": payload.get("question"),
                "options": payload.get("options", []),
                "expected_reply": "number" if payload.get("state") == "awaiting_selection" else None,
                "allow_create": bool(payload.get("allow_create", True)),
            },
        )
        await self._broadcast_conversation_project_state(
            conversation_id=conversation.id,
            project=None,
            project_mode=conversation.project_mode,
            pending_clarification=payload,
        )

    async def _broadcast_conversation_project_state(
        self,
        *,
        conversation_id: UUID,
        project: Project | None,
        project_mode: str,
        pending_clarification: dict[str, Any] | None,
    ) -> None:
        await self._broadcast_to_conversation(
            conversation_id,
            {
                "type": "conversation_project_state",
                "conversation_id": str(conversation_id),
                "project_mode": project_mode,
                "project": (
                    {
                        "id": str(project.id),
                        "name": project.name,
                        "root_path": project.root_path,
                        "index_md_path": project.index_md_path,
                        "is_active": project.is_active,
                    }
                    if project is not None
                    else None
                ),
                "pending_project_clarification": pending_clarification,
            },
        )

    async def _persist_partial_if_meaningful(
        self,
        *,
        conversation_id: UUID,
        user_id: UUID,
        request_id: str,
        content: str,
        thread_id: str | None,
        turn_id: str | None,
        status: str,
        error_code: str,
        error_message: str,
    ) -> None:
        if not _is_meaningful_content(content):
            return

        with SessionLocal() as db:
            conversation = get_conversation(db, conversation_id, include_archived=False)
            if conversation is None:
                return

            if thread_id and conversation.codex_thread_id and conversation.codex_thread_id != thread_id:
                return
            if thread_id and conversation.codex_thread_id is None:
                conversation.codex_thread_id = thread_id

            assistant_message = Message(
                conversation_id=conversation_id,
                role="assistant",
                content=content,
                metadata_json={
                    "partial": True,
                    "turn_status": status,
                    "request_id": request_id,
                    "user_id": str(user_id),
                    "thread_id": thread_id,
                    "turn_id": turn_id,
                    "runtime": "codex_app_server_stdio",
                    "error_code": error_code,
                    "error_message": error_message,
                    "saved_at": datetime.now(tz=UTC).isoformat(),
                },
            )
            db.add(assistant_message)
            db.commit()
            db.refresh(assistant_message)

        await self._broadcast_to_conversation(
            conversation_id,
                {
                    "type": "assistant_done",
                    "conversation_id": str(conversation_id),
                    "message_id": str(assistant_message.id),
                    "content": content,
                    "status": status,
                    "partial": True,
                    **_assistant_author_fields(),
                },
            )

    async def _persist_stop_result(
        self,
        *,
        conversation_id: UUID,
        user_id: UUID,
        request_id: str,
        content: str,
        thread_id: str | None,
        turn_id: str | None,
    ) -> None:
        partial = _is_meaningful_content(content)

        with SessionLocal() as db:
            conversation = get_conversation(db, conversation_id, include_archived=False)
            if conversation is None:
                return

            if thread_id and conversation.codex_thread_id and conversation.codex_thread_id != thread_id:
                return
            if thread_id and conversation.codex_thread_id is None:
                conversation.codex_thread_id = thread_id

            assistant_message = Message(
                conversation_id=conversation_id,
                role="assistant",
                content=content,
                metadata_json={
                    "partial": partial,
                    "turn_status": "stopped",
                    "request_id": request_id,
                    "user_id": str(user_id),
                    "thread_id": thread_id,
                    "turn_id": turn_id,
                    "runtime": "codex_app_server_stdio",
                    "error_code": "STOPPED",
                    "error_message": "Codex runtime stopped by user",
                    "saved_at": datetime.now(tz=UTC).isoformat(),
                },
            )
            db.add(assistant_message)
            db.commit()
            db.refresh(assistant_message)

        await self._broadcast_to_conversation(
            conversation_id,
            {
                "type": "assistant_done",
                "conversation_id": str(conversation_id),
                "message_id": str(assistant_message.id),
                "content": content,
                "status": "stopped",
                "partial": partial,
                **_assistant_author_fields(),
            },
        )

    async def _send_error(
        self,
        websocket: WebSocket,
        *,
        code: str,
        message: str,
        details: dict[str, object] | None = None,
    ) -> None:
        payload = {
            "type": "error",
            "code": code,
            "message": message,
            "details": details or {},
        }
        await self._send_json(websocket, payload)

    async def _broadcast_error(self, conversation_id: UUID, *, code: str, message: str) -> None:
        await self._broadcast_to_conversation(
            conversation_id,
            {
                "type": "error",
                "conversation_id": str(conversation_id),
                "code": code,
                "message": message,
                "details": {
                    "conversation_id": str(conversation_id),
                    "busy": False,
                },
            },
        )

    async def _heartbeat_lock(
        self,
        *,
        conversation_id: UUID,
        owner_token: str,
        stop_event: asyncio.Event,
    ) -> None:
        while True:
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=30)
                return
            except TimeoutError:
                pass

            with SessionLocal() as db:
                keepalive_ok = conversation_lock_service.heartbeat(
                    db,
                    conversation_id=conversation_id,
                    owner_token=owner_token,
                )
            if not keepalive_ok:
                return

    async def _emit_busy_state_for_socket(self, websocket: WebSocket, *, conversation_id: UUID) -> None:
        with SessionLocal() as db:
            state = conversation_lock_service.get_state(db, conversation_id=conversation_id)
        await self._send_thread_busy_state(websocket, state=state)
        if state.is_busy:
            await self._send_assistant_waiting(websocket, conversation_id=conversation_id)

    async def _send_thread_busy_state(self, websocket: WebSocket, *, state: LockState) -> None:
        await self._send_json(
            websocket,
            {
                "type": "thread_busy_state",
                "conversation_id": str(state.conversation_id),
                "is_busy": state.is_busy,
                "locked_by": str(state.locked_by) if state.locked_by else None,
                "reason": state.reason,
            },
        )

    async def _broadcast_thread_busy_state(self, conversation_id: UUID, *, state: LockState) -> None:
        await self._broadcast_to_conversation(
            conversation_id,
            {
                "type": "thread_busy_state",
                "conversation_id": str(state.conversation_id),
                "is_busy": state.is_busy,
                "locked_by": str(state.locked_by) if state.locked_by else None,
                "reason": state.reason,
            },
        )

    async def _send_json(self, websocket: WebSocket, payload: dict[str, object]) -> None:
        try:
            await websocket.send_json(payload)
        except Exception:
            await self._unsubscribe_socket(websocket)

    async def _send_assistant_waiting(self, websocket: WebSocket, *, conversation_id: UUID) -> None:
        await self._send_json(
            websocket,
            {
                "type": "assistant_waiting",
                "conversation_id": str(conversation_id),
            },
        )

    async def _broadcast_assistant_waiting(self, conversation_id: UUID) -> None:
        await self._broadcast_to_conversation(
            conversation_id,
            {
                "type": "assistant_waiting",
                "conversation_id": str(conversation_id),
            },
        )

    async def _broadcast_to_conversation(self, conversation_id: UUID, payload: dict[str, object]) -> None:
        async with self._state_lock:
            subscribers = list(self._subscriptions.get(conversation_id, set()))

        for socket in subscribers:
            await self._send_json(socket, payload)

    async def _subscribe_socket_to_conversation(self, websocket: WebSocket, conversation_id: UUID) -> None:
        async with self._state_lock:
            self._subscriptions[conversation_id].add(websocket)
            self._socket_subscriptions[websocket].add(conversation_id)

    async def _unsubscribe_socket(self, websocket: WebSocket) -> None:
        async with self._state_lock:
            conversations = self._socket_subscriptions.pop(websocket, set())
            for conversation_id in conversations:
                subscribers = self._subscriptions.get(conversation_id)
                if subscribers is None:
                    continue
                subscribers.discard(websocket)
                if not subscribers:
                    self._subscriptions.pop(conversation_id, None)


def _is_meaningful_content(content: str) -> bool:
    normalized = " ".join(content.split())
    if len(normalized) < 3:
        return False
    if all(character in ".,!?;:-_()[]{}'\"`~" for character in normalized):
        return False
    return True


def _normalize_client_payload(raw_payload: dict[str, object]) -> dict[str, object]:
    normalized = dict(raw_payload)
    if "conversation_id" not in normalized and "conversationId" in normalized:
        normalized["conversation_id"] = normalized["conversationId"]
    if "file_ids" not in normalized and "fileIds" in normalized:
        normalized["file_ids"] = normalized["fileIds"]
    if "file_refs" not in normalized and "fileRefs" in normalized:
        normalized["file_refs"] = normalized["fileRefs"]
    if "client_message_id" not in normalized and "clientMessageId" in normalized:
        normalized["client_message_id"] = normalized["clientMessageId"]
    if "index_md_path" not in normalized and "indexMdPath" in normalized:
        normalized["index_md_path"] = normalized["indexMdPath"]
    return normalized


def _user_author_metadata(user: User) -> dict[str, object]:
    metadata: dict[str, object] = {
        "user_id": str(user.id),
        "author_user_id": str(user.id),
        "author_display_name": user.display_name,
    }
    if user.profile_picture_url:
        metadata["author_profile_picture_url"] = user.profile_picture_url
    return metadata


def _assistant_author_fields() -> dict[str, object | None]:
    return {
        "author_user_id": None,
        "author_display_name": "Assistant",
        "author_profile_picture_url": None,
        "is_current_user_author": None,
    }


def _build_prompt_with_files(
    *,
    content: str,
    file_paths: list[str],
    project_context_block: str | None = None,
) -> str:
    lines = []
    if project_context_block:
        lines.extend([project_context_block, ""])
    lines.append(content)
    if not file_paths:
        return "\n".join(lines)
    lines.extend(["", "Available file paths for this turn (use these exact paths when reading/writing files):"])
    for path in file_paths:
        lines.append(f"- {path}")
    return "\n".join(lines)


def _extract_pending_turn_payload(payload: dict[str, Any]) -> dict[str, Any]:
    raw_file_ids = payload.get("pending_file_ids")
    file_ids: list[UUID] = []
    if isinstance(raw_file_ids, list):
        for raw_file_id in raw_file_ids:
            if not isinstance(raw_file_id, str):
                continue
            try:
                file_ids.append(UUID(raw_file_id))
            except ValueError:
                continue

    raw_file_refs = payload.get("pending_file_refs")
    file_refs: list[WorkspaceFileRefInput] = []
    if isinstance(raw_file_refs, list):
        for raw_file_ref in raw_file_refs:
            if not isinstance(raw_file_ref, dict):
                continue
            try:
                file_refs.append(WorkspaceFileRefInput.model_validate(raw_file_ref))
            except ValidationError:
                continue

    return {
        "request_id": payload.get("pending_request_id") if isinstance(payload.get("pending_request_id"), str) else None,
        "content": payload.get("pending_content") if isinstance(payload.get("pending_content"), str) else "",
        "file_ids": file_ids,
        "file_refs": file_refs,
        "client_message_id": payload.get("pending_client_message_id")
        if isinstance(payload.get("pending_client_message_id"), str)
        else None,
    }


def _parse_client_event(payload_text: str) -> ClientEvent:
    try:
        payload = json.loads(payload_text)
    except json.JSONDecodeError as exc:
        raise ClientEventError(
            code="INVALID_JSON",
            message="WebSocket payload must be valid JSON",
            details={"error": str(exc)},
        ) from exc

    if not isinstance(payload, dict):
        raise ClientEventError(
            code="VALIDATION_ERROR",
            message="WebSocket payload must be an object",
            details={},
        )

    normalized = _normalize_client_payload(payload)
    event_type = normalized.get("type")
    try:
        if event_type == "resume":
            return ResumeEvent.model_validate(normalized)
        if event_type == "send_message":
            return SendMessageEvent.model_validate(normalized)
        if event_type == "stop":
            return StopEvent.model_validate(normalized)
        if event_type == "project_clarify_reply":
            return ProjectClarifyReplyEvent.model_validate(normalized)
        if event_type == "create_project":
            return CreateProjectEvent.model_validate(normalized)
    except ValidationError as exc:
        raise ClientEventError(
            code="VALIDATION_ERROR",
            message="WebSocket payload validation failed",
            details={"errors": exc.errors()},
        ) from exc

    raise ClientEventError(
        code="BAD_EVENT_TYPE",
        message="Unsupported websocket event type",
        details={"allowed_types": ["send_message", "resume", "stop", "project_clarify_reply", "create_project"]},
    )


chat_websocket_service = ChatWebSocketService()
