from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from fastapi import APIRouter, Depends, Query

from app.domains.auth.dependencies import get_current_user
from app.domains.files.workspace_service import (
    browse_workspace,
    normalize_workspace_relative_path,
    resolve_workspace_file_refs,
    search_workspace_files,
)

router = APIRouter(prefix="/workspace/files", tags=["files"])


class WorkspaceItemResponse(BaseModel):
    relative_path: str
    display_name: str
    is_directory: bool


class WorkspaceFileResponse(BaseModel):
    kind: str = "workspace"
    relative_path: str
    display_name: str


class ResolveWorkspaceFilesRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    relative_paths: list[str] = Field(default_factory=list, min_length=1, max_length=100)


@router.get("/browse")
def browse_workspace_files(
    path: str | None = Query(default=None),
    _=Depends(get_current_user),
) -> dict[str, object]:
    normalized_path, items = browse_workspace(path)
    return {
        "path": normalized_path,
        "items": [WorkspaceItemResponse.model_validate(item) for item in items],
    }


@router.get("/search")
def search_workspace_file_index(
    q: str = Query(min_length=1, max_length=255),
    path: str | None = Query(default=None),
    limit: int = Query(default=30, ge=1, le=100),
    _=Depends(get_current_user),
) -> dict[str, object]:
    normalized_path, items = search_workspace_files(query=q, relative_path=path, limit=limit)
    return {
        "path": normalized_path,
        "items": [WorkspaceFileResponse.model_validate(item) for item in items],
    }


@router.post("/resolve")
def resolve_workspace_files(
    payload: ResolveWorkspaceFilesRequest,
    _=Depends(get_current_user),
) -> dict[str, object]:
    refs = resolve_workspace_file_refs(payload.relative_paths)
    return {
        "items": [
            WorkspaceFileResponse(
                kind=str(item["kind"]),
                relative_path=normalize_workspace_relative_path(str(item["relative_path"])),
                display_name=str(item["display_name"]),
            )
            for item in refs
        ]
    }
