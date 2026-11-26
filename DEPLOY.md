# Deploy

Production is `VisioAudit-Infra/compose.yaml`. `docker compose up` does not load `compose.dev.yaml` or `compose.override.yaml`. Only the API and the frontend publish ports. Postgres, Redis, and MinIO stay on an internal Docker network with no host ports.

The public site is `https://visioaudit.va`. The dashboard is that origin. The API is the same origin under `/api` (`/api/v1/...`).

## Environment

```bash
cd VisioAudit-Infra
cp .env.example .env
```

Fill every empty required value. `openssl rand -hex 32` for secrets. Use that hex for `POSTGRES_PASSWORD` and `REDIS_PASSWORD` (URL-safe, no spaces or `#`). `AUTH_SECRET` must be at least 32 characters. `MINIO_ROOT_PASSWORD` must be at least 8 characters.

| Variable | Production value |
| --- | --- |
| `NEXT_PUBLIC_API_URL` | `https://visioaudit.va` (no path, no trailing slash; baked in at frontend build) |
| `CORS_ORIGINS` | `https://visioaudit.va` |
| `COOKIE_SECURE` | `true` |
| `COOKIE_SAMESITE` | `lax` |
| `ROOT_PATH` | empty |
| `TRUSTED_PROXY_IPS` | see below |
| `API_BIND_ADDRESS` / `API_PUBLISH_PORT` | `0.0.0.0` / `8000` |
| `FRONTEND_BIND_ADDRESS` / `FRONTEND_PUBLISH_PORT` | `0.0.0.0` / `3000` |

`TRUSTED_PROXY_IPS` is the TCP address the API and frontend containers see for Caddy. Comma-separated IPs or IPv4 CIDRs, no spaces. `*` and `0.0.0.0/0` are rejected. With Docker's userland proxy this is usually the `app` network gateway, not the Caddy VM:

```bash
docker network inspect visioaudit_app --format '{{(index .IPAM.Config 0).Gateway}}'
```

If the daemon runs with `"userland-proxy": false`, use the Caddy VM address instead. Uvicorn accepts `X-Forwarded-*` only from these peers, which is also the client address the login rate limit sees. The frontend drops those headers from every other peer.

Leave `ROOT_PATH` empty. Caddy forwards `/api/*` without stripping it, and the API is already mounted at `/api/v1`. Set `ROOT_PATH=/api` only if a proxy removes that prefix before the request reaches the process.

Redis is required. The API and the workers use it, and login limiting fails closed when it is down. The Redis entrypoint writes the password file as root, `chown`s it to `redis:redis`, then the official image drops to the `redis` user. Do not set `user:` on that service. The healthcheck is `redis-cli ping` with `REDISCLI_AUTH` set in the environment, so the password is not part of the process arguments.

## Caddy

On the Caddy VM. Replace `10.0.0.10` with this VM.

```
visioaudit.va {
	tls internal
	handle /api/* {
		reverse_proxy 10.0.0.10:8000
	}
	handle {
		reverse_proxy 10.0.0.10:3000
	}
}
```

Do not use `handle_path` (that strips `/api`). OPNsense should allow the Caddy host to reach this VM on TCP 8000 and TCP 3000 only.

## First start

```bash
cd VisioAudit-Infra
docker compose up -d --build
```

The API container runs migrations before it listens. The first start creates the agency admin from `AGENCY_EMAIL` and `AGENCY_PASSWORD` when that user does not exist. Sign in at `https://visioaudit.va`.

Changing `NEXT_PUBLIC_API_URL` needs a frontend image rebuild.

## Backups

Volumes: `visioaudit_postgres-data`, `visioaudit_redis-data`, `visioaudit_minio-data`.

```bash
docker compose exec -T db pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" > visioaudit.sql
```

For Redis and MinIO, `docker compose stop` (this keeps the volumes), then archive those two volumes. Do not use `docker compose down -v`.

## Local development

```bash
docker compose -f compose.dev.yaml up --build
```

That file binds to `127.0.0.1`, mounts the source tree, enables API docs, and sets `COOKIE_SECURE=false`.
