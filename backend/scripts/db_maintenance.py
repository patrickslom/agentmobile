"""Execute database maintenance jobs manually or from cron/scheduler."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.maintenance import (
    archive_old_messages_and_files,
    cleanup_expired_sessions,
    cleanup_stale_locks,
)
from app.db.session import SessionLocal


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="AGENTMOBILE DB maintenance jobs")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("cleanup-sessions", help="Delete expired session rows")
    subparsers.add_parser("cleanup-locks", help="Delete stale/expired lock rows")

    archive_parser = subparsers.add_parser(
        "archive-old",
        help="Archive old messages/files and archive affected conversations",
    )
    archive_parser.add_argument(
        "--days-old",
        type=int,
        default=90,
        help="Archive data older than this many days (default: 90)",
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()
    with SessionLocal() as db:
        if args.command == "cleanup-sessions":
            result = {"deleted_sessions": cleanup_expired_sessions(db)}
        elif args.command == "cleanup-locks":
            result = {"deleted_stale_locks": cleanup_stale_locks(db)}
        else:
            result = archive_old_messages_and_files(db, days_old=args.days_old)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
