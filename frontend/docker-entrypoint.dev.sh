#!/bin/sh
set -eu
cd /src
if [ ! -x node_modules/.bin/next ]; then
  npm ci
fi
exec npm run dev
