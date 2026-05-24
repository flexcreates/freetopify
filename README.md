# Freetopify

Self-hosted, folder-first music server with a Gen Z neon glassmorphism web client.

![Freetopify — Now Playing view](docs/assets/preview.png)

## Docs Map
- PRD index: `docs/prd.md`
- Server plan: `docs/server.md`
- Web plan: `docs/web.md`
- Android plan: `docs/android.md`

## Current Status
- Server core implemented and validated
- Web UI (light client) implemented
- Next phase: Flutter Android App implementation

## Login
- Admin users sign in with the server account from `.env`
- Optional guest access can be enabled with `GUEST_PIN` in `.env`
- The login screen keeps the prompt minimal: choose a role, then enter only the required fields
- The web app also includes an About page with developer credits and social links

## Quick Start
```bash
./install.sh
source venv/bin/activate
pytest -q server/tests/test_api.py
./scripts/run_server.sh
```

## Config Notes
- `GUEST_PIN` enables guest sign-in
- `GUEST_TOKEN_EXPIRE_HOURS` sets shorter guest token lifetime
- `SECURE_COOKIES=true` marks auth cookies secure when running behind HTTPS

## Default Health URL
- `http://127.0.0.1:7171/api/v1/system/health`

## License
This project is licensed under the [Freetopify Personal Use License](LICENSE). 
It is free for personal use. Commercial use and monetization are strictly prohibited without explicit written permission.
