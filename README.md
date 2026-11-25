# Sannetic Vision Audit

SEO and GEO analysis for agency audits. The current build crawls a start URL plus internal links, scores checks T01–T05, O01–O03, G01 and G04, and writes an HTML report.

## Run locally

Copy `VisioAudit-Infra/.env.example` to `VisioAudit-Infra/.env` and replace every placeholder with a unique value. Generate secrets with:

```bash
openssl rand -hex 32
```

`REDIS_PASSWORD` and `POSTGRES_PASSWORD` must be URL-safe. `AUTH_SECRET` must be at least 32 characters. Then:

```bash
cd VisioAudit-Infra
docker compose up --build
```

- Dashboard: http://127.0.0.1:3000
- API docs (loaded only with the development override): http://127.0.0.1:8000/docs

Sign in with `AGENCY_EMAIL` and `AGENCY_PASSWORD` from `.env`.

`docker compose up` also loads `compose.override.yaml`: the source tree is mounted, the API reloads on change, and Postgres, Redis, and MinIO are published on localhost only. Redis is mapped to `127.0.0.1:63799` so an existing service on port 6379 does not collide.

Without those development settings:

```bash
docker compose -f compose.yaml up --build
```

That file does not publish the datastores, does not enable API docs, and refuses to start until the secrets above are set. There are no built-in passwords.

## Tests

```bash
cd backend
python -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/pytest
```
