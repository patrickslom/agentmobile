"""Runtime checks that DB revision state is aligned with Alembic heads."""

from __future__ import annotations

from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import text
from sqlalchemy.engine import Connection
from sqlalchemy.exc import SQLAlchemyError


def _alembic_config() -> Config:
    project_root = Path(__file__).resolve().parents[2]
    config = Config(str(project_root / "alembic.ini"))
    config.set_main_option("script_location", str(project_root / "alembic"))
    return config


def expected_heads() -> set[str]:
    script = ScriptDirectory.from_config(_alembic_config())
    return set(script.get_heads())


def current_revisions(connection: Connection) -> set[str]:
    try:
        rows = connection.execute(text("SELECT version_num FROM alembic_version")).fetchall()
    except SQLAlchemyError as exc:
        raise RuntimeError("alembic_version table missing or unreadable") from exc
    return {row[0] for row in rows}


def assert_database_at_head(connection: Connection) -> None:
    expected = expected_heads()
    current = current_revisions(connection)
    if current != expected:
        raise RuntimeError(
            "Database revision is behind expected head(s): "
            f"current={sorted(current)} expected={sorted(expected)}"
        )
