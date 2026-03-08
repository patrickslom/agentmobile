from __future__ import annotations

import json
from datetime import UTC, datetime
import logging
from uuid import UUID

from app.db.models import Conversation
from app.db.session import SessionLocal
from app.domains.chat.title_summary import (
    DEFAULT_CONVERSATION_TITLE,
    TITLE_SUMMARY_TRIGGER_MESSAGE_COUNT,
    conversation_needs_title_summary,
    list_first_window_messages,
)
from app.domains.codex.runtime import (
    RuntimeExecutionError,
    RuntimeTimeoutError,
    RuntimeUnavailableError,
    codex_process_runner,
)
from app.worker.title_summary.service import ClaimedTitleSummaryJob, title_summary_service

logger = logging.getLogger("app.worker")
TITLE_SUMMARY_SYSTEM_USER_ID = UUID("00000000-0000-0000-0000-000000000001")


async def run_claimed_title_summary_job(claimed: ClaimedTitleSummaryJob) -> None:
    try:
        with SessionLocal() as db:
            conversation = db.get(Conversation, claimed.conversation_id)
            if conversation is None or conversation.archived_at is not None:
                title_summary_service.mark_job_succeeded(db, job_id=claimed.job_id)
                return
            if not conversation_needs_title_summary(conversation):
                title_summary_service.mark_job_succeeded(db, job_id=claimed.job_id)
                return

            messages = list_first_window_messages(db, conversation_id=claimed.conversation_id)
            if len(messages) < TITLE_SUMMARY_TRIGGER_MESSAGE_COUNT:
                title_summary_service.mark_job_failed(
                    db,
                    job_id=claimed.job_id,
                    error_text="Conversation does not yet have five exchanges",
                )
                return

            current_title = conversation.title
            should_generate_title = (
                conversation.title_generated_at is None
                and conversation.title.strip() == DEFAULT_CONVERSATION_TITLE
            )

        prompt = _build_title_summary_prompt(
            current_title=current_title,
            messages=messages,
            should_generate_title=should_generate_title,
        )
        result = await codex_process_runner.run_turn(
            prompt=prompt,
            existing_thread_id=None,
            sandbox_mode="read-only",
            conversation_id=claimed.conversation_id,
            user_id=TITLE_SUMMARY_SYSTEM_USER_ID,
            request_id=str(claimed.job_id),
            on_delta=lambda _: None,
        )
        parsed = _parse_title_summary_payload(result.content)

        with SessionLocal() as db:
            conversation = db.get(Conversation, claimed.conversation_id)
            if conversation is None or conversation.archived_at is not None:
                title_summary_service.mark_job_succeeded(db, job_id=claimed.job_id)
                return

            now = datetime.now(tz=UTC)
            should_apply_generated_title = (
                conversation.title_generated_at is None
                and conversation.title.strip() == DEFAULT_CONVERSATION_TITLE
            )
            if should_apply_generated_title and parsed["title"]:
                conversation.title = parsed["title"]
                conversation.title_generated_at = now

            conversation.summary_short = parsed["summary_short"]
            conversation.summary_generated_at = now
            db.commit()
            title_summary_service.mark_job_succeeded(db, job_id=claimed.job_id)
    except (RuntimeTimeoutError, RuntimeUnavailableError, RuntimeExecutionError, ValueError) as exc:
        with SessionLocal() as db:
            title_summary_service.mark_job_failed(db, job_id=claimed.job_id, error_text=str(exc))
    except Exception:
        logger.exception(
            "title_summary_generation_failed",
            extra={"event_data": {"conversation_id": str(claimed.conversation_id), "job_id": str(claimed.job_id)}},
        )
        with SessionLocal() as db:
            title_summary_service.mark_job_failed(
                db,
                job_id=claimed.job_id,
                error_text="Unexpected title/summary generation failure",
            )


def _build_title_summary_prompt(*, current_title: str, messages: list[object], should_generate_title: bool) -> str:
    transcript_lines: list[str] = []
    for index, message in enumerate(messages, start=1):
        role = getattr(message, "role", "assistant")
        content = getattr(message, "content", "")
        normalized_content = str(content).strip()
        transcript_lines.append(f"{index}. {role.upper()}: {normalized_content}")

    title_instruction = (
        "Generate a title if and only if the current title is the generic placeholder."
        if should_generate_title
        else "Keep the current user-visible title unchanged and return it exactly as provided."
    )

    return (
        "You are generating conversation metadata for a chat sidebar.\n"
        "Use only the first five exchanges shown below.\n"
        "Return strict JSON with keys \"title\" and \"summary_short\".\n"
        "The title should be 3-8 words, specific, and actionable.\n"
        "The summary_short should be exactly one sentence, roughly 12-24 words, neutral and factual.\n"
        "Do not include secrets, tokens, or unnecessary personal data.\n"
        f"Current title: {current_title}\n"
        f"{title_instruction}\n"
        "If title generation is not allowed, set \"title\" to the current title exactly.\n"
        "Transcript:\n"
        f"{chr(10).join(transcript_lines)}"
    )


def _parse_title_summary_payload(raw_content: str) -> dict[str, str]:
    content = raw_content.strip()
    if content.startswith("```"):
        lines = content.splitlines()
        if len(lines) >= 3:
            content = "\n".join(lines[1:-1]).strip()
    if not content.startswith("{"):
        start = content.find("{")
        end = content.rfind("}")
        if start != -1 and end != -1 and end > start:
            content = content[start : end + 1]

    payload = json.loads(content)
    if not isinstance(payload, dict):
        raise ValueError("Title/summary generator returned invalid JSON payload")

    title = payload.get("title")
    summary_short = payload.get("summary_short")
    if not isinstance(title, str) or not title.strip():
        raise ValueError("Title/summary generator returned an empty title")
    if not isinstance(summary_short, str) or not summary_short.strip():
        raise ValueError("Title/summary generator returned an empty summary")

    normalized_title = title.strip()[:255]
    normalized_summary = summary_short.strip()[:255]
    return {
        "title": normalized_title,
        "summary_short": normalized_summary,
    }
