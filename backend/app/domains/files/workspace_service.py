from __future__ import annotations

import os
from pathlib import Path, PurePosixPath
from typing import Iterable

from fastapi import status

from app.core.config import get_settings
from app.core.errors import AppError


def ensure_workspace_root() -> Path:
    workspace_root = Path(get_settings().codex_workspace_path).expanduser().resolve()
    if not workspace_root.exists() or not workspace_root.is_dir():
        raise AppError(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="WORKSPACE_UNAVAILABLE",
            message="Configured workspace root is unavailable",
            details={"workspace_root": str(workspace_root)},
        )
    return workspace_root


def normalize_workspace_relative_path(relative_path: str | None) -> str:
    if relative_path is None:
        return ""

    raw_value = relative_path.strip()
    if not raw_value or raw_value == ".":
        return ""

    if raw_value.startswith("/") or raw_value.startswith("~"):
        raise AppError(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="INVALID_WORKSPACE_PATH",
            message="Workspace path must be relative to the configured workspace root",
            details={"relative_path": relative_path},
        )

    normalized = PurePosixPath(raw_value).as_posix()
    if normalized == ".":
        return ""

    path_parts = PurePosixPath(normalized).parts
    if any(part == ".." for part in path_parts):
        raise AppError(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="INVALID_WORKSPACE_PATH",
            message="Workspace path cannot traverse outside the configured workspace root",
            details={"relative_path": relative_path},
        )

    return normalized


def resolve_workspace_path(
    relative_path: str | None,
    *,
    require_exists: bool = True,
    expected_kind: str | None = None,
) -> tuple[str, Path]:
    workspace_root = ensure_workspace_root()
    normalized = normalize_workspace_relative_path(relative_path)
    candidate = (workspace_root / normalized).resolve()
    if candidate != workspace_root and workspace_root not in candidate.parents:
        raise AppError(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="INVALID_WORKSPACE_PATH",
            message="Workspace path cannot traverse outside the configured workspace root",
            details={"relative_path": relative_path},
        )

    if require_exists and not candidate.exists():
        raise AppError(
            status_code=status.HTTP_404_NOT_FOUND,
            code="WORKSPACE_PATH_NOT_FOUND",
            message="Workspace path was not found",
            details={"relative_path": normalized},
        )

    if expected_kind == "directory" and candidate.exists() and not candidate.is_dir():
        raise AppError(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="INVALID_WORKSPACE_PATH",
            message="Workspace path must be a directory",
            details={"relative_path": normalized},
        )

    if expected_kind == "file" and candidate.exists() and not candidate.is_file():
        raise AppError(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="INVALID_FILE_REF",
            message="Workspace file reference must point to a file",
            details={"relative_path": normalized},
        )

    return normalized, candidate


def browse_workspace(relative_path: str | None) -> tuple[str, list[dict[str, object]]]:
    normalized, directory = resolve_workspace_path(relative_path, expected_kind="directory")
    entries: list[dict[str, object]] = []
    workspace_root = ensure_workspace_root()

    with os.scandir(directory) as scan_result:
        for entry in scan_result:
            entry_path = Path(entry.path)
            relative_entry_path = entry_path.relative_to(workspace_root).as_posix()
            is_directory = entry.is_dir(follow_symlinks=False)
            entries.append(
                {
                    "relative_path": relative_entry_path,
                    "display_name": entry.name,
                    "is_directory": is_directory,
                }
            )

    entries.sort(key=lambda item: (not bool(item["is_directory"]), str(item["display_name"]).lower()))
    return normalized, entries


def browse_workspace_directories(relative_path: str | None) -> tuple[str, list[dict[str, str]]]:
    normalized, entries = browse_workspace(relative_path)
    workspace_root = ensure_workspace_root()
    directories: list[dict[str, str]] = []

    for entry in entries:
        if not bool(entry["is_directory"]):
            continue
        entry_relative_path = str(entry["relative_path"])
        _, absolute_path = resolve_workspace_path(entry_relative_path, expected_kind="directory")
        directories.append(
            {
                "relative_path": entry_relative_path,
                "absolute_path": str(absolute_path if entry_relative_path else workspace_root),
                "display_name": str(entry["display_name"]),
            }
        )

    return normalized, directories


def search_workspace_files(
    *,
    query: str,
    relative_path: str | None,
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

    normalized_directory, directory = resolve_workspace_path(relative_path, expected_kind="directory")
    workspace_root = ensure_workspace_root()
    matches: list[tuple[tuple[int, int, int], dict[str, str]]] = []

    for current_root, _, files in os.walk(directory, topdown=True, followlinks=False):
        current_root_path = Path(current_root)
        for file_name in files:
            lowered_name = file_name.lower()
            if normalized_query not in lowered_name:
                continue

            file_path = current_root_path / file_name
            relative_file_path = file_path.relative_to(workspace_root).as_posix()
            matches.append(
                (
                    _workspace_search_score(
                        file_name=file_name,
                        relative_file_path=relative_file_path,
                        query=normalized_query,
                    ),
                    {
                        "relative_path": relative_file_path,
                        "display_name": file_name,
                    },
                )
            )

    matches.sort(key=lambda item: item[0])
    return normalized_directory, [item for _, item in matches[:limit]]


def search_workspace_directories(
    *,
    query: str,
    relative_path: str | None,
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

    normalized_directory, directory = resolve_workspace_path(relative_path, expected_kind="directory")
    workspace_root = ensure_workspace_root()
    matches: list[tuple[tuple[int, int, int], dict[str, str]]] = []

    for current_root, dir_names, _ in os.walk(directory, topdown=True, followlinks=False):
        current_root_path = Path(current_root)
        for directory_name in dir_names:
            lowered_name = directory_name.lower()
            if normalized_query not in lowered_name:
                continue

            directory_path = current_root_path / directory_name
            relative_directory_path = directory_path.relative_to(workspace_root).as_posix()
            matches.append(
                (
                    _workspace_search_score(
                        file_name=directory_name,
                        relative_file_path=relative_directory_path,
                        query=normalized_query,
                    ),
                    {
                        "relative_path": relative_directory_path,
                        "absolute_path": str(directory_path.resolve()),
                        "display_name": directory_name,
                    },
                )
            )

    matches.sort(key=lambda item: item[0])
    return normalized_directory, [item for _, item in matches[:limit]]


def resolve_workspace_file_refs(relative_paths: Iterable[str]) -> list[dict[str, str]]:
    normalized_paths = [normalize_workspace_relative_path(path) for path in relative_paths]
    deduped_paths = list(dict.fromkeys(path for path in normalized_paths if path))
    resolved_refs: list[dict[str, str]] = []
    invalid_paths: list[str] = []

    for relative_path in deduped_paths:
        try:
            normalized, candidate = resolve_workspace_path(relative_path, expected_kind="file")
        except AppError:
            invalid_paths.append(relative_path)
            continue

        if not candidate.exists():
            invalid_paths.append(normalized)
            continue

        resolved_refs.append(
            {
                "kind": "workspace",
                "relative_path": normalized,
                "display_name": candidate.name,
                "absolute_path": str(candidate),
            }
        )

    if invalid_paths:
        raise AppError(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="INVALID_FILE_REF",
            message="One or more selected workspace files are unavailable",
            details={"invalid_relative_paths": invalid_paths},
        )

    return resolved_refs


def _workspace_search_score(*, file_name: str, relative_file_path: str, query: str) -> tuple[int, int, int]:
    lowered_name = file_name.lower()
    if lowered_name.startswith(query):
        bucket = 0
    elif query in lowered_name:
        bucket = 1
    else:
        bucket = 2

    contains_index = lowered_name.find(query)
    return (bucket, contains_index if contains_index >= 0 else 9999, len(relative_file_path))
