from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.db.models import Project, User
from app.db.session import get_db
from app.domains.auth.dependencies import get_current_user
from app.domains.projects.service import (
    get_project,
    list_projects,
    load_project_index_excerpt,
    validate_project_paths,
)
from app.domains.files.workspace_service import (
    browse_workspace_directories,
    resolve_workspace_path,
    search_workspace_directories,
)

router = APIRouter(prefix="/projects", tags=["projects"])


class ProjectResponse(BaseModel):
    id: str
    name: str
    root_path: str
    index_md_path: str | None
    is_active: bool
    created_at: str
    updated_at: str


class ProjectIndexResponse(BaseModel):
    path: str | None
    content: str | None


class ProjectWorkspaceDirectoryResponse(BaseModel):
    relative_path: str
    absolute_path: str
    display_name: str


class ProjectCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=255)
    root_path: str = Field(min_length=1, max_length=2048)
    index_md_path: str | None = Field(default=None, max_length=2048)


class ProjectPatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=255)
    root_path: str | None = Field(default=None, min_length=1, max_length=2048)
    index_md_path: str | None = Field(default=None, max_length=2048)
    is_active: bool | None = None


def _project_to_response(project: Project) -> ProjectResponse:
    return ProjectResponse(
        id=str(project.id),
        name=project.name,
        root_path=project.root_path,
        index_md_path=project.index_md_path,
        is_active=project.is_active,
        created_at=project.created_at.isoformat(),
        updated_at=project.updated_at.isoformat(),
    )


@router.get("")
def get_projects(
    include_inactive: bool = False,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, list[ProjectResponse]]:
    return {
        "projects": [
            _project_to_response(project)
            for project in list_projects(db, include_inactive=include_inactive)
        ]
    }


@router.get("/workspace/directories/browse")
def browse_project_workspace_directories(
    path: str | None = Query(default=None),
    _: User = Depends(get_current_user),
) -> dict[str, object]:
    normalized_path, items = browse_workspace_directories(path)
    _, absolute_path = resolve_workspace_path(normalized_path, expected_kind="directory")
    return {
        "path": normalized_path,
        "absolute_path": str(absolute_path),
        "items": [ProjectWorkspaceDirectoryResponse.model_validate(item) for item in items],
    }


@router.get("/workspace/directories/search")
def search_project_workspace_directories(
    q: str = Query(min_length=1, max_length=255),
    path: str | None = Query(default=None),
    limit: int = Query(default=30, ge=1, le=100),
    _: User = Depends(get_current_user),
) -> dict[str, object]:
    normalized_path, items = search_workspace_directories(query=q, relative_path=path, limit=limit)
    _, absolute_path = resolve_workspace_path(normalized_path, expected_kind="directory")
    return {
        "path": normalized_path,
        "absolute_path": str(absolute_path),
        "items": [ProjectWorkspaceDirectoryResponse.model_validate(item) for item in items],
    }


@router.post("", status_code=status.HTTP_201_CREATED)
def create_project(
    payload: ProjectCreateRequest,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, ProjectResponse]:
    root_path, index_md_path = validate_project_paths(
        root_path=payload.root_path,
        index_md_path=payload.index_md_path,
    )
    project = Project(
        name=payload.name.strip(),
        root_path=root_path,
        index_md_path=index_md_path,
    )
    db.add(project)
    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        raise _map_project_write_error(exc) from exc
    db.refresh(project)
    return {"project": _project_to_response(project)}


@router.patch("/{project_id}")
def patch_project(
    project_id: str,
    payload: ProjectPatchRequest,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, ProjectResponse]:
    project = _require_project(db, project_id)
    provided = payload.model_fields_set
    if not provided:
        raise AppError(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="BAD_REQUEST",
            message="No updates were provided",
            details={},
        )

    next_name = payload.name.strip() if payload.name is not None else project.name
    next_root_path = payload.root_path if payload.root_path is not None else project.root_path
    next_index_path = payload.index_md_path if "index_md_path" in provided else project.index_md_path
    validated_root, validated_index = validate_project_paths(
        root_path=next_root_path,
        index_md_path=next_index_path,
    )

    project.name = next_name
    project.root_path = validated_root
    project.index_md_path = validated_index
    if payload.is_active is not None:
        project.is_active = payload.is_active

    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        raise _map_project_write_error(exc) from exc
    db.refresh(project)
    return {"project": _project_to_response(project)}


@router.get("/{project_id}/index")
def get_project_index(
    project_id: str,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, ProjectIndexResponse]:
    project = _require_project(db, project_id)
    return {
        "index": ProjectIndexResponse(
            path=project.index_md_path,
            content=load_project_index_excerpt(project.index_md_path) if project.index_md_path else None,
        )
    }


def _require_project(db: Session, project_id: str) -> Project:
    try:
        from uuid import UUID

        parsed_id = UUID(project_id)
    except ValueError as exc:
        raise AppError(
            status_code=status.HTTP_404_NOT_FOUND,
            code="NOT_FOUND",
            message="Project not found",
            details={},
        ) from exc

    project = get_project(db, parsed_id)
    if project is None:
        raise AppError(
            status_code=status.HTTP_404_NOT_FOUND,
            code="NOT_FOUND",
            message="Project not found",
            details={},
        )
    return project


def _map_project_write_error(exc: Exception) -> AppError:
    message = str(exc).lower()
    if "uq_projects_name" in message:
        return AppError(
            status_code=status.HTTP_409_CONFLICT,
            code="PROJECT_NAME_CONFLICT",
            message="A project with that name already exists",
            details={},
        )
    if "uq_projects_root_path" in message:
        return AppError(
            status_code=status.HTTP_409_CONFLICT,
            code="PROJECT_ROOT_PATH_CONFLICT",
            message="A project with that root path already exists",
            details={},
        )
    return AppError(
        status_code=status.HTTP_400_BAD_REQUEST,
        code="BAD_REQUEST",
        message="Project update failed",
        details={},
    )
