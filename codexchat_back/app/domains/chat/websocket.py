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

from app.core.config import get_settings
from app.core.errors import AppError
from app.db.archive_queries import get_conversation
from app.db.models import Message, Settings, User
from app.db.session import SessionLocal
from app.domains.chat.title_summary import enqueue_title_summary_job_if_ready
from app.domains.codex.runtime import (
    RuntimeExecutionError,
    RuntimeThreadResumeError,
    RuntimeTimeoutError,
    RuntimeUnavailableError,
    codex_process_runner,
)
from app.domains.files.service import assign_files_to_message
from app.domains.locks.service import LockState, conversation_lock_service

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
    client_message_id: str | None = None


ClientEvent = ResumeEvent | SendMessageEvent


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

        await self._subscribe_socket_to_conversation(websocket, conversation_id)
        await self._emit_busy_state_for_socket(websocket, conversation_id=conversation_id)

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
        asyncio.create_task(
            self._run_turn(
                conversation_id=conversation_id,
                user=user,
                request_id=request_id,
                content=content,
                file_ids=event.file_ids,
                client_message_id=event.client_message_id,
                owner_token=owner_token,
            )
        )

    async def _run_turn(
        self,
        *,
        conversation_id: UUID,
        user: User,
        request_id: str,
        content: str,
        file_ids: list[UUID],
        client_message_id: str | None,
        owner_token: str,
    ) -> None:
        assistant_content = ""
        thread_id: str | None = None
        turn_id: str | None = None
        message_file_paths: list[str] = []
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

                attached_refs = []
                for attached_file in attached_files:
                    attached_refs.append(
                        {
                            "id": str(attached_file.id),
                            "name": attached_file.original_name,
                            "storage_path": attached_file.storage_path,
                            "download_path": f"/api/files/{attached_file.id}",
                        }
                    )
                user_message.metadata_json = {
                    **(user_message.metadata_json or {}),
                    "attached_files": attached_refs,
                }
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
                        "client_message_id": client_message_id,
                    },
                },
            )

            prompt = _build_prompt_with_files(content=content, file_paths=message_file_paths)
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
            with SessionLocal() as db:
                conversation_lock_service.release(
                    db,
                    conversation_id=conversation_id,
                    owner_token=owner_token,
                )
                current_state = conversation_lock_service.get_state(db, conversation_id=conversation_id)
            await self._broadcast_thread_busy_state(conversation_id, state=current_state)

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
    if "client_message_id" not in normalized and "clientMessageId" in normalized:
        normalized["client_message_id"] = normalized["clientMessageId"]
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


def _build_prompt_with_files(*, content: str, file_paths: list[str]) -> str:
    if not file_paths:
        return content
    lines = [content, "", "Attached files (use these paths when reading/writing files):"]
    for path in file_paths:
        lines.append(f"- {path}")
    return "\n".join(lines)


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
    except ValidationError as exc:
        raise ClientEventError(
            code="VALIDATION_ERROR",
            message="WebSocket payload validation failed",
            details={"errors": exc.errors()},
        ) from exc

    raise ClientEventError(
        code="BAD_EVENT_TYPE",
        message="Unsupported websocket event type",
        details={"allowed_types": ["send_message", "resume"]},
    )


chat_websocket_service = ChatWebSocketService()
