#!/bin/sh
set -eu
cd /app
if [ "${RUN_MIGRATIONS:-false}" = "true" ]; then
  alembic upgrade head
fi
exec "$@"
