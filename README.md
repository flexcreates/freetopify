# Freetopify

Self-hosted, folder-first music server.

## Docs Map
- PRD index: `docs/prd.md`
- Server plan: `docs/server.md`
- Web plan: `docs/web.md`
- Android plan: `docs/android.md`

## Current Status
- Server core implemented
- Server API starter tests passing (`3 passed`)
- Next phase: Web UI implementation

## Quick Start
```bash
./install.sh
source venv/bin/activate
pytest -q server/tests/test_api.py
uvicorn server.main:app --host 0.0.0.0 --port 7171
```

## Default Health URL
- `http://127.0.0.1:7171/api/v1/system/health`
