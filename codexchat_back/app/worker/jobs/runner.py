"""Job execution primitives for worker tasks."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
import logging
from pathlib import Path
from uuid import UUID, uuid4

from sqlalchemy import select

from app.db.models import Conversation, HeartbeatJob, HeartbeatRun, Message, Settings
from app.db.session import SessionLocal
from app.domains.codex.runtime import (
    RuntimeExecutionError,
    RuntimeThreadResumeError,
    RuntimeTimeoutError,
    RuntimeUnavailableError,
    codex_process_runner,
)
from app.domains.locks.service import conversation_lock_service
from app.worker.heartbeat.service import ClaimedHeartbeatRun, heartbeat_service

logger = logging.getLogger("app.worker")
SYSTEM_USER_ID = UUID("00000000-0000-0000-0000-000000000000")


async def run_claimed_heartbeat_run(claimed: ClaimedHeartbeatRun) -> None:
    owner_token = str(uuid4())
    lock_acquired = False
    heartbeat_stop = asyncio.Event()
    heartbeat_task: asyncio.Task[None] | None = None
    assistant_content = ""
    thread_id: str | None = None
    turn_id: str | None = None
    sandbox_mode = "workspace-write"
    try:
        with SessionLocal() as db:
            row = db.execute(
                select(HeartbeatRun, HeartbeatJob, Conversation)
                .join(HeartbeatJob, HeartbeatJob.id == HeartbeatRun.heartbeat_job_id)
                .join(Conversation, Conversation.id == HeartbeatJob.conversation_id)
                .where(HeartbeatRun.id == claimed.run_id)
            ).one_or_none()
            if row is None:
                return
            _, job, conversation = row
            acquire_result = conversation_lock_service.acquire(
                db,
                conversation_id=conversation.id,
                user_id=None,
                owner_token=owner_token,
                metadata={
                    "source": "heartbeat_worker",
                    "heartbeat_job_id": str(job.id),
                    "heartbeat_run_id": str(claimed.run_id),
                },
            )
            if not acquire_result.acquired:
                heartbeat_service.mark_run_failed(
                    db,
                    run_id=claimed.run_id,
                    error_text="thread busy",
                )
                return
            lock_acquired = True

        heartbeat_task = asyncio.create_task(
            _heartbeat_lock(
                conversation_id=claimed.conversation_id,
                owner_token=owner_token,
                stop_event=heartbeat_stop,
            )
        )

        instruction_text = _read_instruction_file(claimed.instruction_file_path)
        prompt = _build_heartbeat_prompt(
            instruction_file_path=claimed.instruction_file_path,
            instruction_text=instruction_text,
        )

        with SessionLocal() as db:
            conversation = db.get(Conversation, claimed.conversation_id)
            if conversation is None or conversation.archived_at is not None:
                heartbeat_service.mark_run_failed(
                    db,
                    run_id=claimed.run_id,
                    error_text="Conversation not found",
                )
                return
            thread_id = conversation.codex_thread_id
            settings_row = db.get(Settings, 1)
            execution_mode_default = settings_row.execution_mode_default if settings_row is not None else "regular"
            sandbox_mode = codex_process_runner.sandbox_mode_for_execution_mode(execution_mode_default)
            user_message = Message(
                conversation_id=conversation.id,
                role="user",
                content=instruction_text,
                metadata_json={
                    **_heartbeat_author_metadata(
                        heartbeat_job_id=claimed.heartbeat_job_id,
                        heartbeat_run_id=claimed.run_id,
                        instruction_file_path=claimed.instruction_file_path,
                    ),
                },
            )
            db.add(user_message)
            db.commit()

        turn_result = await codex_process_runner.run_turn(
            prompt=prompt,
            existing_thread_id=thread_id,
            sandbox_mode=sandbox_mode,
            conversation_id=claimed.conversation_id,
            user_id=SYSTEM_USER_ID,
            request_id=str(claimed.run_id),
            on_delta=lambda _: None,
        )
        assistant_content = turn_result.content
        thread_id = turn_result.thread_id
        turn_id = turn_result.turn_id

        with SessionLocal() as db:
            conversation = db.get(Conversation, claimed.conversation_id)
            if conversation is None:
                heartbeat_service.mark_run_failed(
                    db,
                    run_id=claimed.run_id,
                    error_text="Conversation not found",
                )
                return
            if conversation.codex_thread_id and conversation.codex_thread_id != thread_id:
                heartbeat_service.mark_run_failed(
                    db,
                    run_id=claimed.run_id,
                    error_text=(
                        "Conversation continuity check failed; runtime returned a different thread id"
                    ),
                )
                return
            if conversation.codex_thread_id is None:
                conversation.codex_thread_id = thread_id
            assistant_message = Message(
                conversation_id=conversation.id,
                role="assistant",
                content=assistant_content,
                metadata_json={
                    "source": "heartbeat",
                    "heartbeat_job_id": str(claimed.heartbeat_job_id),
                    "heartbeat_run_id": str(claimed.run_id),
                    "thread_id": thread_id,
                    "turn_id": turn_id,
                    "partial": False,
                    "turn_status": "completed",
                    "runtime": "codex_app_server_stdio",
                },
            )
            db.add(assistant_message)
            db.commit()
            heartbeat_service.mark_run_succeeded(db, run_id=claimed.run_id)
    except (
        OSError,
        RuntimeTimeoutError,
        RuntimeUnavailableError,
        RuntimeExecutionError,
        RuntimeThreadResumeError,
    ) as exc:
        with SessionLocal() as db:
            heartbeat_service.mark_run_failed(db, run_id=claimed.run_id, error_text=str(exc))
            if assistant_content.strip():
                message = Message(
                    conversation_id=claimed.conversation_id,
                    role="assistant",
                    content=assistant_content,
                    metadata_json={
                        "source": "heartbeat",
                        "heartbeat_job_id": str(claimed.heartbeat_job_id),
                        "heartbeat_run_id": str(claimed.run_id),
                        "thread_id": thread_id,
                        "turn_id": turn_id,
                        "partial": True,
                        "turn_status": "failed",
                        "runtime": "codex_app_server_stdio",
                        "saved_at": datetime.now(tz=UTC).isoformat(),
                        "error": str(exc),
                    },
                )
                db.add(message)
                db.commit()
    except Exception as exc:
        logger.exception(
            "heartbeat_run_failed",
            extra={
                "event_data": {
                    "heartbeat_run_id": str(claimed.run_id),
                    "heartbeat_job_id": str(claimed.heartbeat_job_id),
                    "conversation_id": str(claimed.conversation_id),
                }
            },
        )
        with SessionLocal() as db:
            heartbeat_service.mark_run_failed(db, run_id=claimed.run_id, error_text=str(exc))
    finally:
        heartbeat_stop.set()
        if heartbeat_task is not None:
            await heartbeat_task
        if lock_acquired:
            with SessionLocal() as db:
                conversation_lock_service.release(
                    db,
                    conversation_id=claimed.conversation_id,
                    owner_token=owner_token,
                )


def _read_instruction_file(path_raw: str) -> str:
    path = Path(path_raw).expanduser().resolve()
    if not path.is_absolute() or not path.exists() or not path.is_file():
        raise OSError("Heartbeat instruction file is missing or invalid")
    return path.read_text(encoding="utf-8")


def _build_heartbeat_prompt(*, instruction_file_path: str, instruction_text: str) -> str:
    return (
        f"Heartbeat instruction file: {instruction_file_path}\n"
        "Execute the instruction content below as this scheduled heartbeat turn.\n\n"
        f"{instruction_text}"
    )


def _heartbeat_author_metadata(
    *,
    heartbeat_job_id: UUID,
    heartbeat_run_id: UUID,
    instruction_file_path: str,
) -> dict[str, object]:
    return {
        "source": "heartbeat",
        "heartbeat_job_id": str(heartbeat_job_id),
        "heartbeat_run_id": str(heartbeat_run_id),
        "instruction_file_path": instruction_file_path,
        "author_display_name": "Heartbeat",
    }


async def _heartbeat_lock(
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
