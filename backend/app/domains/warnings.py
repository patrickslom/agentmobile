from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

WarningId = Literal["destructive_operations", "yolo_mode", "shared_vps_non_private"]
WarningSeverity = Literal["info", "warning", "critical"]
WarningSurface = Literal["settings", "chat"]


class WarningPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: WarningId
    title: str
    content: str
    severity: WarningSeverity
    surfaces: list[WarningSurface]
    metadata: dict[str, object] = Field(default_factory=dict)


def build_warning_payloads(*, execution_mode_default: str) -> list[WarningPayload]:
    yolo_enabled = execution_mode_default == "yolo"

    return [
        WarningPayload(
            id="destructive_operations",
            title="Destructive Actions Can Modify Shared Data",
            content=(
                "Commands and file operations may permanently modify or delete shared workspace data. "
                "Review actions carefully before executing destructive changes."
            ),
            severity="critical",
            surfaces=["settings", "chat"],
            metadata={
                "requires_confirmation": True,
            },
        ),
        WarningPayload(
            id="yolo_mode",
            title="YOLO Mode Reduces Confirmation Safeguards",
            content=(
                "YOLO mode allows high-impact actions without additional confirmation prompts. "
                "Use only when you accept elevated execution risk."
            ),
            severity="warning",
            surfaces=["settings", "chat"],
            metadata={
                "execution_mode_default": execution_mode_default,
                "enabled": yolo_enabled,
            },
        ),
        WarningPayload(
            id="shared_vps_non_private",
            title="Shared VPS Is Not Private",
            content=(
                "Shared VPS mode is not private. Other users can access shared conversations, files, "
                "and workspace data on this deployment."
            ),
            severity="critical",
            surfaces=["settings", "chat"],
            metadata={
                "shared_workspace": True,
                "privacy": "none",
            },
        ),
    ]
