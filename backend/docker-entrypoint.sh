#!/bin/sh
set -eu
cd /app

require_var() {
  eval "value=\${$1:-}"
  if [ -z "$value" ]; then
    echo "$1 is required" >&2
    exit 1
  fi
}

# Unset is fine for local runs that do not enable proxy headers.
# A wildcard would trust X-Forwarded-* from every peer.
if [ -n "${TRUSTED_PROXY_IPS:-}" ]; then
  old_ifs=$IFS
  IFS=','
  set -f
  for item in $TRUSTED_PROXY_IPS; do
    case "$item" in
      \*|0.0.0.0/0|::/0|*[[:space:]]*|"")
        echo "TRUSTED_PROXY_IPS must list specific proxy addresses" >&2
        exit 1
        ;;
    esac
  done
  set +f
  IFS=$old_ifs
fi

if [ "${AUTH_DISABLED:-false}" != "true" ]; then
  require_var AUTH_SECRET
  if [ "${#AUTH_SECRET}" -lt 32 ]; then
    echo "AUTH_SECRET is missing or shorter than 32 characters" >&2
    exit 1
  fi
fi

require_var API_KEY_PEPPER
if [ "${#API_KEY_PEPPER}" -lt 32 ]; then
  echo "API_KEY_PEPPER is missing or shorter than 32 characters" >&2
  exit 1
fi

# Build connection URLs from separate variables so compose files never embed credentials.
if [ -z "${DATABASE_URL:-}" ]; then
  require_var POSTGRES_PASSWORD
  DATABASE_URL="$(python - <<'PY'
import os
from urllib.parse import quote

user = quote(os.environ.get("POSTGRES_USER", "visio"), safe="")
password = quote(os.environ["POSTGRES_PASSWORD"], safe="")
host = os.environ.get("POSTGRES_HOST", "db")
database = quote(os.environ.get("POSTGRES_DB", "visioaudit"), safe="")
print(f"postgresql+psycopg://{user}:{password}@{host}:5432/{database}")
PY
)"
  export DATABASE_URL
fi

if [ -z "${REDIS_URL:-}" ]; then
  require_var REDIS_PASSWORD
  REDIS_URL="$(python - <<'PY'
import os
from urllib.parse import quote

password = quote(os.environ["REDIS_PASSWORD"], safe="")
host = os.environ.get("REDIS_HOST", "redis")
print(f"redis://:{password}@{host}:6379/0")
PY
)"
  export REDIS_URL
fi
if [ -z "${CELERY_BROKER_URL:-}" ]; then
  export CELERY_BROKER_URL="$REDIS_URL"
fi
if [ -z "${S3_SECRET_KEY:-}" ]; then
  require_var MINIO_ROOT_PASSWORD
  export S3_SECRET_KEY="$MINIO_ROOT_PASSWORD"
fi
if [ -z "${S3_ACCESS_KEY:-}" ] && [ -n "${MINIO_ROOT_USER:-}" ]; then
  export S3_ACCESS_KEY="$MINIO_ROOT_USER"
fi

if [ "${RUN_MIGRATIONS:-false}" = "true" ]; then
  alembic upgrade head
fi
exec "$@"
