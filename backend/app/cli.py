"""Server-side management commands.

Create an API user and print its secret once::

    python -m app.cli create-api-key --name "Nightly" --client-id CLIENT_UUID

The secret is printed to stdout and is not written to the log.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from uuid import UUID

from app.core.api_keys import ApiKeyNotConfigured
from app.core.database import session_scope
from app.services.api_key_service import ApiKeyError, create_api_user, record_key_event


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    sub = parser.add_subparsers(dest="command", required=True)
    create = sub.add_parser("create-api-key", help="Create an API user and print its secret once")
    create.add_argument("--name", required=True)
    create.add_argument("--client-id", required=True)
    create.add_argument("--scope", action="append", dest="scopes", default=None)
    create.add_argument("--expires-at", default=None, help="ISO-8601 timestamp")
    create.add_argument("--email", default=None)
    args = parser.parse_args(argv)
    if args.command == "create-api-key":
        return _create(args)
    parser.error("unknown command")
    return 2


def _create(args: argparse.Namespace) -> int:
    try:
        client_id = UUID(str(args.client_id))
    except ValueError:
        print("client-id must be a UUID", file=sys.stderr)
        return 2
    expires_at = None
    if args.expires_at:
        try:
            expires_at = datetime.fromisoformat(str(args.expires_at).replace("Z", "+00:00"))
        except ValueError:
            print("expires-at must be ISO-8601", file=sys.stderr)
            return 2
    scopes = list(args.scopes) if args.scopes else ["audits:create", "audits:read"]
    try:
        with session_scope() as db:
            _user, key, secret = create_api_user(
                db,
                name=str(args.name),
                client_id=client_id,
                scopes=scopes,
                expires_at=expires_at,
                created_by=None,
                email=str(args.email).strip().lower() if args.email else None,
            )
            record_key_event(
                db,
                api_key=key,
                presented_key=key.key_id,
                action="created_cli",
                method="CLI",
                path="create-api-key",
                status_code=0,
            )
            db.commit()
            key_id = key.key_id
    except ApiKeyNotConfigured:
        print("API_KEY_PEPPER is missing or shorter than 32 characters", file=sys.stderr)
        return 1
    except ApiKeyError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print("Secret is shown once and cannot be retrieved again.", file=sys.stderr)
    print(f"key_id={key_id}")
    # Shown once on stdout for the operator. This is not a log file.
    print(f"secret={secret}")  # codeql[py/clear-text-logging-sensitive-data]
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
