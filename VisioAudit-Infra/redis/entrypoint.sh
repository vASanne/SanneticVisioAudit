#!/bin/sh
# Start Redis with a password from the environment so it is not part of argv.
set -eu
if [ -z "${REDIS_PASSWORD:-}" ]; then
  echo "REDIS_PASSWORD is required" >&2
  exit 1
fi
case "$REDIS_PASSWORD" in
  *[[:space:]]*|*'#'*)
    echo "REDIS_PASSWORD must be a single token without spaces or #" >&2
    exit 1
    ;;
esac
umask 077
printf 'appendonly yes\nprotected-mode yes\nrequirepass %s\n' "$REDIS_PASSWORD" > /tmp/redis.conf
# The official image drops to the redis user. A root-only config makes the server exit.
chown redis:redis /tmp/redis.conf
chmod 600 /tmp/redis.conf
export REDISCLI_AUTH="$REDIS_PASSWORD"
exec docker-entrypoint.sh redis-server /tmp/redis.conf
