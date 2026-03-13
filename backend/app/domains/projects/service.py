from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import re
from typing import Any, Iterable
from uuid import UUID

from fastapi import status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.db.models import Conversation, Project

PROJECT_SPECIFIC_CUES = (
    "project",
    "repo",
    "repository",
    "codebase",
    "workspace",
    "frontend",
    "backend",
    "api",
    "route",
    "page",
    "component",
    "migration",
    "schema",
    "deploy",
    "build",
    "bug",
    "fix",
    "feature",
    "file",
    "folder",
    "directory",
)
PROJECT_PATH_HINT_PATTERN = re.compile(r"[/\\]|[A-Za-z0-9_-]+\.(py|ts|tsx|js|jsx|md|json|yaml|yml|css|sql)\b")
TOKEN_PATTERN = re.compile(r"[a-z0-9]+")


@dataclass(frozen=True)
class ProjectResolution:
    mode: str
    project: Project | None = None
    options: tuple[Project, ...] = ()


def list_projects(db: Session, *, include_inactive: bool = False) -> list[Project]:
    stmt = select(Project).order_by(Project.updated_at.desc(), Project.created_at.desc())
    if not include_inactive:
        stmt = stmt.where(Project.is_active.is_(True))
    return list(db.execute(stmt).scalars())


def get_project(db: Session, project_id: UUID) -> Project | None:
    return db.get(Project, project_id)


def validate_project_paths(*, root_path: str, index_md_path: str | None) -> tuple[str, str | None]:
    normalized_root = _normalize_absolute_path(root_path, field_name="root_path", require_directory=True)
    normalized_index: str | None = None
    if index_md_path is not None:
        normalized_index = _normalize_absolute_path(
            index_md_path,
            field_name="index_md_path",
            require_file=True,
        )
        index_path = Path(normalized_index)
        root = Path(normalized_root)
        if root != index_path and root not in index_path.parents:
            raise AppError(
                status_code=400,
                code="BAD_REQUEST",
                message="Project index markdown must live inside the project root path",
                details={"index_md_path": normalized_index, "root_path": normalized_root},
            )
    return (normalized_root, normalized_index)


def browse_host_directories(path: str | None) -> tuple[str, list[dict[str, str]]]:
    normalized = normalize_host_directory_path(path)
    directory = Path(normalized)
    entries: list[dict[str, str]] = []

    try:
        with os.scandir(directory) as scan_result:
            for entry in scan_result:
                try:
                    if not entry.is_dir(follow_symlinks=False):
                        continue
                except OSError:
                    continue

                entry_path = Path(entry.path)
                entries.append(
                    {
                        "path": str(entry_path.resolve()),
                        "display_name": entry.name,
                    }
                )
    except PermissionError as exc:
        raise AppError(
            status_code=status.HTTP_403_FORBIDDEN,
            code="DIRECTORY_ACCESS_DENIED",
            message="That directory is not accessible to the backend process",
            details={"path": normalized},
        ) from exc
    except OSError as exc:
        raise AppError(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="BAD_REQUEST",
            message="Unable to browse that directory",
            details={"path": normalized},
        ) from exc

    entries.sort(key=lambda item: item["display_name"].lower())
    return normalized, entries


def search_host_directories(
    *,
    query: str,
    path: str | None,
    limit: int,
) -> tuple[str, list[dict[str, str]]]:
    normalized_query = query.strip().lower()
    if not normalized_query:
        raise AppError(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="BAD_REQUEST",
            message="Search query cannot be empty",
            details={},
        )

    normalized_root = normalize_host_directory_path(path)
    root = Path(normalized_root)
    matches: list[tuple[tuple[int, int, int], dict[str, str]]] = []

    def _on_walk_error(exc: OSError) -> None:
        return None

    for current_root, dir_names, _ in os.walk(root, topdown=True, followlinks=False, onerror=_on_walk_error):
        current_root_path = Path(current_root)
        dir_names[:] = [name for name in dir_names if not name.startswith(".git")]
        for directory_name in dir_names:
            lowered_name = directory_name.lower()
            if normalized_query not in lowered_name:
                continue

            directory_path = current_root_path / directory_name
            matches.append(
                (
                    _path_search_score(
                        file_name=directory_name,
                        absolute_path=str(directory_path),
                        query=normalized_query,
                    ),
                    {
                        "path": str(directory_path.resolve()),
                        "display_name": directory_name,
                    },
                )
            )

    matches.sort(key=lambda item: item[0])
    return normalized_root, [item for _, item in matches[:limit]]


def normalize_host_directory_path(path: str | None) -> str:
    if path is None or not path.strip():
        return "/"
    return _normalize_absolute_path(path, field_name="path", require_directory=True)


def resolve_project_for_content(
    db: Session,
    *,
    content: str,
    conversation: Conversation,
) -> ProjectResolution:
    if conversation.project_id is not None:
        project = get_project(db, conversation.project_id)
        if project is not None and project.is_active:
            return ProjectResolution(mode="project_bound", project=project)

    active_projects = list_projects(db)
    if not active_projects:
        return ProjectResolution(mode="general")

    matches = _rank_projects(content, active_projects)
    if len(matches) == 1:
        return ProjectResolution(mode="project_bound", project=matches[0])
    if len(matches) > 1:
        return ProjectResolution(mode="clarify", options=tuple(matches[:5]))

    if _looks_project_specific(content):
        if len(active_projects) == 1:
            return ProjectResolution(mode="project_bound", project=active_projects[0])
        return ProjectResolution(mode="clarify", options=tuple(active_projects[:5]))

    return ProjectResolution(mode="general")


def build_project_context_block(project: Project) -> str:
    lines = [
        "Project context for this conversation:",
        f"- Project name: {project.name}",
        f"- Project root path: {project.root_path}",
    ]
    if project.index_md_path:
        lines.append(f"- Project index markdown: {project.index_md_path}")
        excerpt = load_project_index_excerpt(project.index_md_path)
        if excerpt:
            lines.append("")
            lines.append("Project index excerpt:")
            lines.append(excerpt)
    return "\n".join(lines)


def load_project_index_excerpt(index_md_path: str, *, max_chars: int = 1600) -> str | None:
    path = Path(index_md_path)
    try:
        content = path.read_text(encoding="utf-8")
    except OSError:
        return None

    normalized = content.strip()
    if not normalized:
        return None
    if len(normalized) > max_chars:
        normalized = f"{normalized[:max_chars].rstrip()}..."
    return normalized


def build_project_options(projects: Iterable[Project]) -> list[dict[str, Any]]:
    options: list[dict[str, Any]] = []
    for index, project in enumerate(projects, start=1):
        options.append(
            {
                "number": index,
                "id": str(project.id),
                "label": f"{project.name} ({project.root_path})",
                "name": project.name,
                "root_path": project.root_path,
            }
        )
    return options


def sanitize_pending_project_clarification(payload: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(payload, dict):
        return None
    state = payload.get("state")
    if state not in {"awaiting_selection", "awaiting_create"}:
        return None

    question = payload.get("question")
    if not isinstance(question, str) or not question.strip():
        return None

    response: dict[str, Any] = {
        "state": state,
        "question": question.strip(),
    }
    if state == "awaiting_selection":
        options = payload.get("options")
        if isinstance(options, list):
            response["options"] = [
                item
                for item in options
                if isinstance(item, dict)
                and isinstance(item.get("number"), int)
                and isinstance(item.get("id"), str)
                and isinstance(item.get("label"), str)
            ]
        response["allow_create"] = bool(payload.get("allow_create", True))
    if state == "awaiting_create":
        response["root_path_hint"] = payload.get("root_path_hint") if isinstance(payload.get("root_path_hint"), str) else None
    return response


def _normalize_absolute_path(
    raw_path: str,
    *,
    field_name: str,
    require_directory: bool = False,
    require_file: bool = False,
) -> str:
    normalized = raw_path.strip()
    if not normalized:
        raise AppError(
            status_code=400,
            code="BAD_REQUEST",
            message=f"{field_name} cannot be empty",
            details={field_name: raw_path},
        )
    path = Path(normalized).expanduser()
    if not path.is_absolute():
        raise AppError(
            status_code=400,
            code="BAD_REQUEST",
            message=f"{field_name} must be an absolute path",
            details={field_name: normalized},
        )
    if not path.exists():
        raise AppError(
            status_code=400,
            code="BAD_REQUEST",
            message=f"{field_name} does not exist",
            details={field_name: normalized},
        )
    if require_directory and not path.is_dir():
        raise AppError(
            status_code=400,
            code="BAD_REQUEST",
            message=f"{field_name} must point to a directory",
            details={field_name: normalized},
        )
    if require_file and not path.is_file():
        raise AppError(
            status_code=400,
            code="BAD_REQUEST",
            message=f"{field_name} must point to a file",
            details={field_name: normalized},
        )
    return str(path.resolve())


def _rank_projects(content: str, projects: list[Project]) -> list[Project]:
    lowered = content.lower()
    content_tokens = set(TOKEN_PATTERN.findall(lowered))
    scored: list[tuple[int, Project]] = []
    for project in projects:
        score = 0
        name = project.name.lower()
        root_name = Path(project.root_path).name.lower()
        if name and name in lowered:
            score += 8
        if project.root_path.lower() in lowered:
            score += 10
        if root_name and root_name != name and root_name in lowered:
            score += 6

        for token in TOKEN_PATTERN.findall(name):
            if len(token) > 2 and token in content_tokens:
                score += 2
        for token in TOKEN_PATTERN.findall(root_name):
            if len(token) > 2 and token in content_tokens:
                score += 1

        if score > 0:
            scored.append((score, project))

    scored.sort(key=lambda item: (item[0], item[1].updated_at), reverse=True)
    if not scored:
        return []
    best_score = scored[0][0]
    return [project for score, project in scored if score >= max(3, best_score - 2)]


def _looks_project_specific(content: str) -> bool:
    lowered = content.lower()
    if PROJECT_PATH_HINT_PATTERN.search(content):
        return True
    return any(cue in lowered for cue in PROJECT_SPECIFIC_CUES)


def _path_search_score(*, file_name: str, absolute_path: str, query: str) -> tuple[int, int, int]:
    lowered_name = file_name.lower()
    if lowered_name.startswith(query):
        bucket = 0
    elif query in lowered_name:
        bucket = 1
    else:
        bucket = 2

    contains_index = lowered_name.find(query)
    return (bucket, contains_index if contains_index >= 0 else 9999, len(absolute_path))
