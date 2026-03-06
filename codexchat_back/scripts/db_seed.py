"""Run idempotent bootstrap seed for settings + optional first admin."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.bootstrap import seed_defaults
from app.db.session import SessionLocal


def main() -> int:
    with SessionLocal() as db:
        result = seed_defaults(db)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
