from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable
from uuid import UUID

from app.core.config import get_settings

logger = logging.getLogger("app.api")


class RuntimeUnavailableError(Exception):
    pass


class RuntimeExecutionError(Exception):
    pass


class RuntimeTimeoutError(Exception):
    pass


@dataclass(slots=True)
class TurnResult:
    thread_id: str
    turn_id: str | None
    content: str


@dataclass(slots=True)
class _RuntimeState:
    process: asyncio.subprocess.Process
    message_id: int = 0


class CodexProcessRunner:
    def __init__(self) -> None:
        settings = get_settings()
        self._turn_timeout_seconds = settings.codex_turn_timeout_seconds
        self._workspace_path = Path(settings.codex_workspace_path).expanduser()

    @property
    def turn_timeout_seconds(self) -> int:
        return self._turn_timeout_seconds

    async def run_turn(
        self,
        *,
        prompt: str,
        existing_thread_id: str | None,
        sandbox_mode: str,
        conversation_id: UUID,
        user_id: UUID,
        request_id: str,
        on_delta: Callable[[str], Any],
    ) -> TurnResult:
        sandbox_mode_normalized = self._normalize_sandbox_mode(sandbox_mode)
        state = await self._start_process()
        assistant_content = ""
        task_complete_last_message: str | None = None
        turn_id: str | None = None

        try:
            await self._initialize(state)
            thread_id = await self._ensure_thread(
                state,
                existing_thread_id=existing_thread_id,
                sandbox_mode=sandbox_mode_normalized,
            )

            turn_result = await self._send_request(
                state,
                method="turn/start",
                params={
                    "threadId": thread_id,
                    "approvalPolicy": "never",
                    "sandboxPolicy": self._sandbox_policy_for_mode(sandbox_mode_normalized),
                    "input": [{"type": "text", "text": prompt}],
                },
            )
            turn_id = self._extract_turn_id(turn_result)

            async with asyncio.timeout(self._turn_timeout_seconds):
                while True:
                    message = await self._read_message(state)
                    if message is None:
                        raise RuntimeExecutionError("Codex runtime closed stdout before turn completion")

                    if "id" in message:
                        if message.get("error") is not None:
                            raise RuntimeExecutionError(self._error_message(message["error"]))
                        continue

                    method = message.get("method")
                    params = message.get("params") if isinstance(message.get("params"), dict) else {}

                    if method == "item/agentMessage/delta":
                        delta = params.get("delta")
                        if isinstance(delta, str) and delta:
                            assistant_content += delta
                            on_delta(delta)
                        continue

                    if method == "codex/event/task_complete":
                        msg = params.get("msg") if isinstance(params, dict) else None
                        if isinstance(msg, dict):
                            last_message = msg.get("last_agent_message")
                            if isinstance(last_message, str) and last_message:
                                task_complete_last_message = last_message
                        continue

                    if method == "turn/completed":
                        completed_turn_id = self._extract_turn_id_from_notification(params)
                        if turn_id is not None and completed_turn_id not in {None, turn_id}:
                            continue
                        break

                    if method == "error":
                        raise RuntimeExecutionError(self._error_message(params))

            if not assistant_content and task_complete_last_message:
                assistant_content = task_complete_last_message

            logger.info(
                "codex_turn_completed",
                extra={
                    "event_data": {
                        "conversation_id": str(conversation_id),
                        "user_id": str(user_id),
                        "request_id": request_id,
                        "thread_id": thread_id,
                        "turn_id": turn_id,
                        "output_chars": len(assistant_content),
                    }
                },
            )

            return TurnResult(
                thread_id=thread_id,
                turn_id=turn_id,
                content=assistant_content,
            )
        except TimeoutError as exc:
            raise RuntimeTimeoutError("Codex runtime timed out") from exc
        finally:
            await self._terminate_process(state)

    async def _start_process(self) -> _RuntimeState:
        cwd_path = self._workspace_path
        if not cwd_path.exists() or not cwd_path.is_dir():
            raise RuntimeUnavailableError(
                f"Codex workspace path is missing or not a directory: {cwd_path}"
            )
        try:
            process = await asyncio.create_subprocess_exec(
                "codex",
                "app-server",
                "--listen",
                "stdio://",
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(cwd_path),
            )
        except FileNotFoundError as exc:
            raise RuntimeUnavailableError("Codex CLI is not installed in the backend runtime") from exc
        except Exception as exc:  # pragma: no cover
            raise RuntimeUnavailableError("Unable to start Codex runtime process") from exc

        if process.stdin is None or process.stdout is None or process.stderr is None:
            raise RuntimeUnavailableError("Codex runtime stdio channels were not initialized")

        return _RuntimeState(process=process)

    async def _initialize(self, state: _RuntimeState) -> None:
        await self._send_request(
            state,
            method="initialize",
            params={
                "protocolVersion": 2,
                "clientInfo": {
                    "name": "codexchat_back",
                    "version": "mvp",
                },
            },
        )
        await self._send_notification(state, method="initialized", params={})

    async def _ensure_thread(
        self,
        state: _RuntimeState,
        *,
        existing_thread_id: str | None,
        sandbox_mode: str,
    ) -> str:
        if existing_thread_id:
            try:
                result = await self._send_request(
                    state,
                    method="thread/resume",
                    params={
                        "threadId": existing_thread_id,
                        "approvalPolicy": "never",
                        "sandbox": sandbox_mode,
                    },
                )
                resumed_thread_id = self._extract_thread_id(result)
                if resumed_thread_id:
                    return resumed_thread_id
            except RuntimeExecutionError:
                logger.warning(
                    "codex_thread_resume_failed_starting_new_thread",
                    extra={"event_data": {"thread_id": existing_thread_id}},
                )

        result = await self._send_request(
            state,
            method="thread/start",
            params={
                "approvalPolicy": "never",
                "sandbox": sandbox_mode,
            },
        )
        started_thread_id = self._extract_thread_id(result)
        if not started_thread_id:
            raise RuntimeExecutionError("Codex runtime did not return a thread id")
        return started_thread_id

    async def _send_request(self, state: _RuntimeState, *, method: str, params: dict[str, Any]) -> dict[str, Any]:
        state.message_id += 1
        request_id = state.message_id
        await self._write_message(
            state,
            {
                "jsonrpc": "2.0",
                "id": request_id,
                "method": method,
                "params": params,
            },
        )

        while True:
            message = await self._read_message(state)
            if message is None:
                raise RuntimeExecutionError(f"Codex runtime exited before response to {method}")

            if message.get("id") != request_id:
                if "error" in message and message.get("id") == request_id:
                    raise RuntimeExecutionError(self._error_message(message["error"]))
                continue

            if message.get("error") is not None:
                raise RuntimeExecutionError(self._error_message(message["error"]))

            result = message.get("result")
            if not isinstance(result, dict):
                raise RuntimeExecutionError(f"Invalid response payload for {method}")
            return result

    async def _send_notification(self, state: _RuntimeState, *, method: str, params: dict[str, Any]) -> None:
        await self._write_message(
            state,
            {
                "jsonrpc": "2.0",
                "method": method,
                "params": params,
            },
        )

    async def _write_message(self, state: _RuntimeState, message: dict[str, Any]) -> None:
        line = json.dumps(message, separators=(",", ":")) + "\n"
        assert state.process.stdin is not None
        state.process.stdin.write(line.encode("utf-8"))
        await state.process.stdin.drain()

    async def _read_message(self, state: _RuntimeState) -> dict[str, Any] | None:
        assert state.process.stdout is not None
        while True:
            line = await state.process.stdout.readline()
            if not line:
                return None

            text = line.decode("utf-8", errors="replace").strip()
            if text:
                break

        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            raise RuntimeExecutionError("Codex runtime returned non-JSON message") from exc

        if not isinstance(payload, dict):
            raise RuntimeExecutionError("Codex runtime returned invalid message envelope")

        return payload

    async def _terminate_process(self, state: _RuntimeState) -> None:
        process = state.process
        if process.returncode is None:
            process.terminate()
            try:
                await asyncio.wait_for(process.wait(), timeout=3)
            except TimeoutError:
                process.kill()
                await process.wait()

        stderr_output = ""
        assert process.stderr is not None
        try:
            stderr_bytes = await asyncio.wait_for(process.stderr.read(), timeout=0.2)
            stderr_output = stderr_bytes.decode("utf-8", errors="replace").strip()
        except Exception:
            stderr_output = ""

        if process.returncode not in {0, -15} and stderr_output:
            logger.warning(
                "codex_process_non_zero_exit",
                extra={"event_data": {"return_code": process.returncode, "stderr": stderr_output[:500]}},
            )

    @staticmethod
    def _extract_thread_id(result: dict[str, Any]) -> str | None:
        thread = result.get("thread") if isinstance(result.get("thread"), dict) else {}
        thread_id = thread.get("id")
        if isinstance(thread_id, str) and thread_id:
            return thread_id
        return None

    @staticmethod
    def _extract_turn_id(result: dict[str, Any]) -> str | None:
        turn = result.get("turn") if isinstance(result.get("turn"), dict) else {}
        turn_id = turn.get("id")
        if isinstance(turn_id, str) and turn_id:
            return turn_id
        return None

    @staticmethod
    def _normalize_sandbox_mode(sandbox_mode: str) -> str:
        normalized = sandbox_mode.strip().lower()
        if normalized not in {"read-only", "workspace-write", "danger-full-access"}:
            raise RuntimeExecutionError(f"Unsupported sandbox mode: {sandbox_mode}")
        return normalized

    @staticmethod
    def _sandbox_policy_for_mode(sandbox_mode: str) -> dict[str, object]:
        if sandbox_mode == "danger-full-access":
            return {"type": "dangerFullAccess"}
        if sandbox_mode == "workspace-write":
            return {"type": "workspaceWrite"}
        return {"type": "readOnly"}

    @staticmethod
    def sandbox_mode_for_execution_mode(execution_mode: str | None) -> str:
        if (execution_mode or "").strip().lower() == "yolo":
            return "danger-full-access"
        return "workspace-write"

    @staticmethod
    def _extract_turn_id_from_notification(params: dict[str, Any]) -> str | None:
        turn = params.get("turn") if isinstance(params.get("turn"), dict) else {}
        turn_id = turn.get("id")
        if isinstance(turn_id, str) and turn_id:
            return turn_id
        return None

    @staticmethod
    def _error_message(error_payload: Any) -> str:
        if isinstance(error_payload, dict):
            message = error_payload.get("message")
            if isinstance(message, str) and message.strip():
                return message

            nested_error = error_payload.get("error")
            if isinstance(nested_error, dict):
                nested_message = nested_error.get("message")
                additional_details = nested_error.get("additionalDetails")
                if isinstance(nested_message, str) and nested_message.strip():
                    if isinstance(additional_details, str) and additional_details.strip():
                        return f"{nested_message} ({additional_details})"
                    return nested_message

            code = error_payload.get("code")
            if code is not None:
                return f"Codex runtime error: {code}"
        if isinstance(error_payload, str) and error_payload.strip():
            return error_payload
        return "Codex runtime error"


codex_process_runner = CodexProcessRunner()
