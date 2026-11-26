# Sannetic Vision Audit

SEO and GEO analysis for agency audits. The current build crawls a start URL plus internal links, scores checks T01–T05, O01–O03, G01 and G04, and writes an HTML report.

## Run locally

Copy `VisioAudit-Infra/.env.example` to `VisioAudit-Infra/.env` and fill every empty required value. Generate secrets with:

```bash
openssl rand -hex 32
```

`REDIS_PASSWORD` and `POSTGRES_PASSWORD` must be URL-safe. `AUTH_SECRET` and `API_KEY_PEPPER` must each be at least 32 characters. `API_KEY_PEPPER` hashes agent API secrets and has no default. For a local stack, set `NEXT_PUBLIC_API_URL=http://127.0.0.1:8000` in that file (the example value is the production origin). `TRUSTED_PROXY_IPS` can stay empty locally. Then:

```bash
cd VisioAudit-Infra
docker compose -f compose.dev.yaml up --build
```

- Dashboard: http://127.0.0.1:3000
- API docs: http://127.0.0.1:8000/docs

Sign in with `AGENCY_EMAIL` and `AGENCY_PASSWORD` from `.env`. The API sets an HttpOnly session cookie (`visioaudit_session`, `SameSite=Lax`). The browser will only store it when the dashboard and the API are the same site: use http://127.0.0.1:3000 with `NEXT_PUBLIC_API_URL=http://127.0.0.1:8000`, or put both names under one registrable domain. Mixing `localhost` and `127.0.0.1` drops the cookie.

`COOKIE_SECURE` defaults to true. Browsers ignore Secure cookies on plain HTTP, so `compose.dev.yaml` sets it to false for local development. Leave it true behind HTTPS. `COOKIE_SAMESITE` is `lax` or `strict`.

State-changing requests need a double-submit CSRF token. The dashboard reads it from `GET /api/v1/auth/csrf` (and again after login and logout) and sends it as `X-CSRF-Token`. It is kept in memory only. CORS allows credentials only for the origins in `CORS_ORIGINS`, never for `*`. Logout clears the session cookie.

`compose.dev.yaml` is not loaded automatically. It bind-mounts the source tree, reloads the API, publishes Postgres, Redis, and MinIO on localhost only, and sets `COOKIE_SECURE=false` for plain HTTP. Redis is mapped to `127.0.0.1:63799` so an existing service on port 6379 does not collide.

`docker compose up` is the production file: no datastore ports, docs and debug off, and it refuses to start until the required secrets are set. Deployment notes are in the repository root file `DEPLOY.md` (not under `VisioAudit-Infra/`). There are no built-in passwords.

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

## Agent API

Automated agents submit URLs and read the stored audit back from `/api/v1/agent/`. This is separate from the browser session. The browser API keeps using the HttpOnly cookie and the CSRF token. The agent API ignores that cookie.

Access is a key id plus a secret, sent as headers over TLS:

- `X-Api-Key`: public id (`vak_...`)
- `X-Api-Secret`: secret (`vas_...`), shown once when the key is created

The secret is stored as HMAC-SHA256 with `API_KEY_PEPPER` (at least 32 characters, no default). A database copy does not reveal the secret. Comparison is constant-time. Request signing (timestamp, nonce, replay window) was not added: Caddy already terminates TLS, and a second signature protocol is easy for an agent to get wrong. The secret must not be logged. Revocation, an optional expiry, `last_used_at`, and the scopes `audits:create` and `audits:read` are stored on the key. A key only reads and creates audits for its own client.

An agency admin creates an API user in **Nutzerverwaltung** (no password, no browser login) or on the server:

```bash
python -m app.cli create-api-key --name "Nightly" --client-id CLIENT_UUID
```

The command prints the secret once. Interactive docs (`/docs`, on when `EXPOSE_DOCS` is set) describe the agent tag, including this placeholder call:

```bash
curl -sS -X POST "https://visioaudit.va/api/v1/agent/audits" \
  -H "Content-Type: application/json" \
  -H "X-Api-Key: ${VISIOAUDIT_API_KEY}" \
  -H "X-Api-Secret: ${VISIOAUDIT_API_SECRET}" \
  -H "Idempotency-Key: audit-example-1" \
  -d '{"urls":["https://example.com/"]}'
```

Poll `GET /api/v1/agent/audits/AUDIT_ID/status`, then `GET /api/v1/agent/audits/AUDIT_ID` for scores and findings. `GET /api/v1/agent/audits` lists that key's tenant. Submitted URLs go through the same public-address check as the dashboard, including DNS answers and, inside the crawler, redirect targets. Repeat a create with the same `Idempotency-Key` and the same body to get the original ids back. The default batch size is 10. Each key is limited to 60 requests per minute and 30 created audits per hour. If Redis does not answer, those routes return 503.

## Rate limits

Login is limited to 10 attempts per minute per direct client address. Starting an audit is limited to 30 per hour per signed-in user (or per client address when auth is off). The window lives in Redis and is shared by every API process. The update is one Lua script.

If Redis does not answer, login, audit start, and the agent API fail closed with HTTP 503. A Redis outage must not turn into unlimited password guesses or unlimited agent calls. The login limit key is the TCP peer, not `X-Forwarded-For`. Behind a reverse proxy, set the peer from a trusted proxy before treating that limit as per end user. Agent limits are counted per key id.

## Matrix background

The dashboard draws the Sannetic matrix rain behind the login page and the workspace. The animation is the design-system module from [SanneticDesign](https://github.com/vASanne/SanneticDesign) `matrix/matrix-rain.js` and `matrix/matrix-rain.css` (taken from SanneticDashboard `public/scripts/matrix-rain.js`, commit `d47716b`). Glyphs are `0` and `1` in the brand gradient (`#8FD11B` → `#1CC4A0` → `#08C2D4`), at 24 frames per second, with the device pixel ratio capped at 2. Canvas opacity is `0.78` in the dark theme and `0.35` in the light theme. `prefers-reduced-motion: reduce` paints one static frame, and the loop pauses while the tab is hidden. Headings, paragraphs, and tables sit on the page color so the rain stays in the gaps and text contrast does not change.

## Content Security Policy

The production dashboard allows scripts only with a per-request nonce and `strict-dynamic`. Styles load from `'self'` stylesheets. Inline style attributes are not used. The development server still allows inline styles because the Next.js error overlay injects them.

HTML audit reports keep their CSS in one `<style>` block. The API CSP allows that block by its SHA-256 hash, not by `'unsafe-inline'`.

## Continuous integration

GitHub Actions runs the test suite, Bandit, Semgrep, CodeQL, `pip-audit`, `npm audit`, and gitleaks. No passwords are stored in the workflow files. The DAST job writes a throwaway `VisioAudit-Infra/.env` at runtime and starts `docker compose -f compose.yaml`. OWASP ZAP then runs a baseline scan against the API and the dashboard on the runner's loopback interface. `COOKIE_SECURE=false` in that job is only so the scanner can speak HTTP. Warnings do not fail the baseline (`zap-baseline.py -I`); failing alerts do. The scan is unauthenticated.
