#!/bin/sh
set -eu
mkdir -p /data
chown appuser:appgroup /data
exec su-exec appuser:appgroup /usr/local/bin/minio "$@"
