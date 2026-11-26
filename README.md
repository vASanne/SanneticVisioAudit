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

Sign in with `AGENCY_EMAIL` and `AGENCY_PASSWORD` from `.env`. The API sets an HttpOnly session cookie (`visioaudit_session`, `SameSite=Lax`). The browser will only store it when the dashboard and the API are the same site: use http://127.0.0.1:3000 with `NEXT_PUBLIC_API_URL=http://127.0.0.1:8000`, or put both names under one registrable domain. Mixing `localhost` and `127.0.0.1` drops the cookie.

`COOKIE_SECURE` defaults to true. Browsers ignore Secure cookies on plain HTTP, so `compose.override.yaml` sets it to false for local development. Leave it true behind HTTPS. `COOKIE_SAMESITE` is `lax` or `strict`.

State-changing requests need a double-submit CSRF token. The dashboard reads it from `GET /api/v1/auth/csrf` (and again after login and logout) and sends it as `X-CSRF-Token`. It is kept in memory only. CORS allows credentials only for the origins in `CORS_ORIGINS`, never for `*`. Logout clears the session cookie.

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

```bash
cd frontend
npm ci
npm test
npm run lint
npm run build
```

## Rate limits

Login is limited to 10 attempts per minute per direct client address. Starting an audit is limited to 30 per hour per signed-in user (or per client address when auth is off). The window lives in Redis and is shared by every API process. The update is one Lua script.

If Redis does not answer, those two routes fail closed with HTTP 503. A Redis outage must not turn into unlimited password guesses. The rest of the API does not use this limiter. The limit key is the TCP peer, not `X-Forwarded-For`. Behind a reverse proxy, set the peer from a trusted proxy before treating the limit as per end user.

## Content Security Policy

The production dashboard allows scripts only with a per-request nonce and `strict-dynamic`. Styles load from `'self'` stylesheets. Inline style attributes are not used. The development server still allows inline styles because the Next.js error overlay injects them.

HTML audit reports keep their CSS in one `<style>` block. The API CSP allows that block by its SHA-256 hash, not by `'unsafe-inline'`.

## Continuous integration

GitHub Actions runs the test suite, Bandit, Semgrep, CodeQL, `pip-audit`, `npm audit`, and gitleaks. No passwords are stored in the workflow files. The DAST job writes a throwaway `VisioAudit-Infra/.env` at runtime and starts `docker compose -f compose.yaml`. OWASP ZAP then runs a baseline scan against the API and the dashboard on the runner's loopback interface. `COOKIE_SECURE=false` in that job is only so the scanner can speak HTTP. Warnings do not fail the baseline (`zap-baseline.py -I`); failing alerts do. The scan is unauthenticated.
