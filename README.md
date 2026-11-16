# Sannetic Vision Audit

SEO- und GEO-Analyse für Agentur-Audits. Der erste Stand crawlt eine Start-URL plus interne Links, bewertet die Checks T01–T05, O01–O03, G01 und G04 und schreibt einen HTML-Bericht.

## Lokal starten

```bash
cd VisioAudit-Infra
docker compose up --build
```

- Dashboard: http://127.0.0.1:3000
- API-Dokumentation: http://127.0.0.1:8000/docs

URL: http://127.0.0.1:3000/login
E-Mail: admin@sannetic.local
Passwort: REDACTED


`docker compose up` lädt zusätzlich `compose.override.yaml`: Quellcode ist gemountet, die API startet mit Reload, Postgres und MinIO sind nur auf localhost erreichbar. Redis wird auf `127.0.0.1:63799` gelegt, damit ein bereits belegter Port 6379 nicht kollidiert.

Ohne diese Entwicklungseinstellungen:

```bash
docker compose -f compose.yaml up --build
```

Die Passwörter in `compose.yaml` sind lokale Entwicklungs-Fallbacks. Für jede andere Nutzung `VisioAudit-Infra/.env` aus `.env.example` anlegen.

Tests der Checks und des Scorings:

```bash
cd backend
python -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/pytest
```
