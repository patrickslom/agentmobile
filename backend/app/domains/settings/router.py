from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.db.models import Settings, User
from app.db.session import get_db
from app.domains.auth.dependencies import get_current_user
from app.domains.warnings import WarningPayload, build_warning_payloads

router = APIRouter(prefix="/settings", tags=["settings"])

_EXECUTION_MODE_OPTIONS: tuple[str, ...] = ("regular", "yolo")
_THEME_OPTIONS: tuple[str, ...] = ("light", "dark")


class SharedWorkspaceWarningResponse(BaseModel):
    enabled: bool
    content: str


class SettingsResponse(BaseModel):
    execution_mode_default: str
    execution_mode_options: list[str]
    upload_limit_mb_default: int
    heartbeat_enabled_default: bool
    heartbeat_cap_default: int
    heartbeat_unlimited_default: bool
    theme_preference: str
    theme_preference_source: Literal["user", "default"]
    theme_options: list[str]
    destructive_operations_warning: WarningPayload
    yolo_mode_warning: WarningPayload
    shared_workspace_warning: SharedWorkspaceWarningResponse
    warnings: list[WarningPayload]


class SettingsPatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    execution_mode_default: Literal["regular", "yolo"] | None = None
    upload_limit_mb_default: int | None = Field(default=None, ge=1)
    heartbeat_enabled_default: bool | None = None
    heartbeat_cap_default: int | None = Field(default=None, ge=1)
    heartbeat_unlimited_default: bool | None = None
    theme_preference: Literal["light", "dark"] | None = None


def _ensure_settings_row(db: Session) -> Settings:
    settings_row = db.get(Settings, 1)
    if settings_row is None:
        settings_row = Settings(id=1)
        db.add(settings_row)
        db.flush()
    return settings_row


def _to_settings_response(*, settings_row: Settings, current_user: User) -> SettingsResponse:
    theme_source: Literal["user", "default"] = "user" if current_user.theme_preference else "default"
    theme_value = current_user.theme_preference or settings_row.theme_default
    warnings = build_warning_payloads(execution_mode_default=settings_row.execution_mode_default)
    warning_by_id = {warning.id: warning for warning in warnings}
    shared_workspace_warning = warning_by_id["shared_vps_non_private"]

    return SettingsResponse(
        execution_mode_default=settings_row.execution_mode_default,
        execution_mode_options=list(_EXECUTION_MODE_OPTIONS),
        upload_limit_mb_default=settings_row.upload_limit_mb_default,
        heartbeat_enabled_default=settings_row.heartbeat_enabled_default,
        heartbeat_cap_default=settings_row.heartbeat_cap_default,
        heartbeat_unlimited_default=settings_row.heartbeat_unlimited_default,
        theme_preference=theme_value,
        theme_preference_source=theme_source,
        theme_options=list(_THEME_OPTIONS),
        destructive_operations_warning=warning_by_id["destructive_operations"],
        yolo_mode_warning=warning_by_id["yolo_mode"],
        shared_workspace_warning=SharedWorkspaceWarningResponse(
            enabled=True,
            content=shared_workspace_warning.content,
        ),
        warnings=warnings,
    )


@router.get("")
def get_settings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, SettingsResponse]:
    settings_row = _ensure_settings_row(db)
    return {"settings": _to_settings_response(settings_row=settings_row, current_user=current_user)}


@router.patch("")
def patch_settings(
    payload: SettingsPatchRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, SettingsResponse]:
    provided_fields = payload.model_fields_set
    if not provided_fields:
        raise AppError(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="BAD_REQUEST",
            message="No updates were provided",
            details={},
        )

    global_fields = {
        "execution_mode_default",
        "upload_limit_mb_default",
        "heartbeat_enabled_default",
        "heartbeat_cap_default",
        "heartbeat_unlimited_default",
    }
    touched_global_fields = provided_fields.intersection(global_fields)
    if touched_global_fields and current_user.role != "admin":
        raise AppError(
            status_code=status.HTTP_403_FORBIDDEN,
            code="FORBIDDEN",
            message="Admin access required for global settings updates",
            details={"fields": sorted(touched_global_fields)},
        )

    settings_row = _ensure_settings_row(db)
    if "execution_mode_default" in provided_fields:
        if payload.execution_mode_default is None:
            raise AppError(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                code="VALIDATION_ERROR",
                message="execution_mode_default cannot be null",
                details={},
            )
        settings_row.execution_mode_default = payload.execution_mode_default
    if "upload_limit_mb_default" in provided_fields:
        if payload.upload_limit_mb_default is None:
            raise AppError(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                code="VALIDATION_ERROR",
                message="upload_limit_mb_default cannot be null",
                details={},
            )
        settings_row.upload_limit_mb_default = payload.upload_limit_mb_default
    if "heartbeat_enabled_default" in provided_fields:
        if payload.heartbeat_enabled_default is None:
            raise AppError(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                code="VALIDATION_ERROR",
                message="heartbeat_enabled_default cannot be null",
                details={},
            )
        settings_row.heartbeat_enabled_default = payload.heartbeat_enabled_default
    if "heartbeat_cap_default" in provided_fields:
        if payload.heartbeat_cap_default is None:
            raise AppError(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                code="VALIDATION_ERROR",
                message="heartbeat_cap_default cannot be null",
                details={},
            )
        settings_row.heartbeat_cap_default = payload.heartbeat_cap_default
    if "heartbeat_unlimited_default" in provided_fields:
        if payload.heartbeat_unlimited_default is None:
            raise AppError(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                code="VALIDATION_ERROR",
                message="heartbeat_unlimited_default cannot be null",
                details={},
            )
        settings_row.heartbeat_unlimited_default = payload.heartbeat_unlimited_default
    if touched_global_fields:
        settings_row.updated_by_user_id = current_user.id

    if "theme_preference" in provided_fields:
        current_user.theme_preference = payload.theme_preference

    db.commit()
    db.refresh(settings_row)
    db.refresh(current_user)
    return {"settings": _to_settings_response(settings_row=settings_row, current_user=current_user)}
