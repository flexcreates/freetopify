# Freetopify Cross-Platform Implementation Playbook

## AI Execution Instructions (Read First)
This document is the single implementation sequence for cross-platform support.

Rules for any AI/dev agent working this file:
1. Execute tasks strictly in order from Step 1 to final step.
2. Do not skip validation gates.
3. Never regress Linux behavior while adding macOS/Windows support.
4. After each step, update status markers in this file:
- `[DONE]` when fully complete and validated.
- `[NOT DONE]` when pending or partially complete.
5. Keep commits small: one step or one sub-step per commit.
6. If a step fails validation, fix before moving to next.
7. If uncertain, prefer backward-compatible wrappers over hard replacement.

Status legend:
- `[DONE]` Completed and validated.
- `[NOT DONE]` Not implemented yet.

---

## Objective
Add stable support for Linux + macOS + Windows for setup/start scripts and runtime flows, plus Safari compatibility, while keeping current Linux path stable.

---

## Current Baseline Snapshot
- Linux flow is stable.
- Installer is Linux/APT-first (`install.sh`).
- Server launcher is Linux-specific (`scripts/run_server.sh`).
- Helper scripts are bash-only (`scripts/ftsmdl.sh`, `scripts/organize_music_library.sh`).
- WebSocket URL currently needs secure-protocol hardening for HTTPS deployments.

---

## Master Task List (Strict Order)

## Step 1 — Baseline Lock and Regression Guardrails
Status: `[NOT DONE]`

Tasks:
1. Record Linux baseline behavior and commands used for startup/download flows.
2. Add a lightweight regression checklist doc section in this file (or `docs/TASK.md`).
3. Ensure all future steps run the Linux validation gate below.

Linux validation gate:
1. `python3 -m py_compile server/*.py server/tests/test_api.py`
2. `bash -n scripts/run_server.sh scripts/ftsmdl.sh scripts/organize_music_library.sh`
3. `pytest -q server/tests/test_api.py` (if dependencies are installed)

Completion criteria:
- Baseline commands documented.
- Validation gate written and run at least once.

---

## Step 2 — Cross-Platform Server Runner Core
Status: `[NOT DONE]`

Tasks:
1. Add `scripts/run_server.py` as the platform-neutral runner.
2. Runner must:
- Load `.env` values (`SERVER_HOST`, `SERVER_PORT`, `VENV_PATH`, `MAX_CONNECTIONS`).
- Resolve uvicorn executable safely on Linux/macOS/Windows.
- Stop previous server process safely (cross-platform process matching).
- Start uvicorn with same semantics as current Linux flow.
3. Keep compatibility with current command behavior.

Linux validation gate:
1. `python3 scripts/run_server.py --dry-run` (add dry-run mode)
2. `./scripts/run_server.sh` still works.

Completion criteria:
- `run_server.py` exists and can run server from Linux.
- Existing Linux shell workflow still valid.

---

## Step 3 — Wrapper Scripts by OS
Status: `[NOT DONE]`

Tasks:
1. Refactor `scripts/run_server.sh` to delegate to `run_server.py`.
2. Add `scripts/run_server.ps1` for Windows.
3. Keep shell wrapper minimal and backward-compatible.

Linux validation gate:
1. `bash -n scripts/run_server.sh`
2. `./scripts/run_server.sh` boots server successfully.

Completion criteria:
- Linux wrapper works.
- PowerShell wrapper exists and documented.

---

## Step 4 — Installer Split (Linux/macOS/Windows)
Status: `[NOT DONE]`

Tasks:
1. Keep `install.sh` for Linux with minimal risk changes.
2. Add `install_macos.sh`:
- Homebrew checks
- install `python`, `ffmpeg`, `sqlite`, `node`
- create venv and install Python requirements
3. Add `install_windows.ps1`:
- Python presence check
- dependency guidance/install path
- create venv and install requirements
4. Ensure all installers produce compatible `.env` keys.

Linux validation gate:
1. `bash -n install.sh install_macos.sh`
2. `.env` contains required keys after Linux installer run.

Completion criteria:
- Three installer entrypoints available.
- `.env` contract consistent across OS installers.

---

## Step 5 — Downloader/Organizer Script Compatibility Layer
Status: `[NOT DONE]`

Tasks:
1. Keep bash scripts for Linux/macOS unchanged in behavior.
2. Add PowerShell equivalents or Python alternatives for Windows:
- `scripts/ftsmdl.ps1`
- `scripts/organize_music_library.ps1`
3. Ensure `.env` defaults are used consistently across variants.

Linux validation gate:
1. `bash -n scripts/ftsmdl.sh scripts/organize_music_library.sh`
2. Manual smoke test one download flow in Linux CLI.

Completion criteria:
- Windows-compatible helper workflow exists and documented.

---

## Step 6 — Safari and Secure WebSocket Hardening
Status: `[NOT DONE]`

Tasks:
1. Update `web/js/websocket.js`:
- `wss://` when `location.protocol === 'https:'`
- `ws://` otherwise.
2. Add CSS fallback rules where needed (`backdrop-filter` and other progressive effects).
3. Add browser smoke checklist for Safari.

Linux validation gate:
1. App loads and live updates work in Linux browser.
2. No regressions in Chrome/Firefox.

Completion criteria:
- Protocol-aware websocket logic merged.
- Browser checklist documented.

---

## Step 7 — Documentation Overhaul
Status: `[NOT DONE]`

Tasks:
1. Update `README.md` with platform-specific install/run sections.
2. Update `docs/server.md` with cross-platform runner details.
3. Add:
- `docs/setup-linux.md`
- `docs/setup-macos.md`
- `docs/setup-windows.md`
4. Keep examples copy-paste safe.

Linux validation gate:
1. Verify every Linux command in docs runs.
2. Verify no stale references to removed scripts/components.

Completion criteria:
- New setup docs exist.
- README/server docs updated and consistent.

---

## Step 8 — CI Matrix and Emulated Cross-OS Confidence from Linux
Status: `[NOT DONE]`

Tasks:
1. Add CI matrix jobs for Linux/macOS/Windows.
2. Add fast startup smoke test using `run_server.py --dry-run` in all jobs.
3. Add lint/static checks for shell and PowerShell syntax where possible.

Linux-only confidence strategy (since you develop on Linux):
1. Use static checks for cross-platform scripts:
- `bash -n` for `.sh`
- `pwsh -NoProfile -Command { <path> -? }` when PowerShell Core available
2. Add unit tests for path normalization and env parsing in Python (platform-neutral logic).
3. Add a no-spawn dry-run mode in runner to validate command construction on all OS targets.
4. Use CI as the authoritative runtime verifier for macOS/Windows.

Completion criteria:
- CI matrix green for baseline checks.
- Linux dev workflow can validate without booting other OS locally.

---

## Step 9 — Final Verification and Release Readiness
Status: `[NOT DONE]`

Tasks:
1. Run Linux regression suite end-to-end.
2. Confirm docs match actual scripts and commands.
3. Ensure all steps above marked `[DONE]` before release.

Release checklist:
- Linux startup and downloads unchanged.
- macOS install/start documented and CI-validated.
- Windows install/start documented and CI-validated.
- Safari live updates and core UI behavior validated.

Completion criteria:
- All step statuses `[DONE]`.
- No open high-severity regression.

---

## Progress Board
- Step 1: `[NOT DONE]`
- Step 2: `[NOT DONE]`
- Step 3: `[NOT DONE]`
- Step 4: `[NOT DONE]`
- Step 5: `[NOT DONE]`
- Step 6: `[NOT DONE]`
- Step 7: `[NOT DONE]`
- Step 8: `[NOT DONE]`
- Step 9: `[NOT DONE]`

---

## Notes for Linux-Only Development
You do not need to boot other OS locally for every change.
Use this pattern:
1. Implement platform-neutral core logic in Python.
2. Validate Linux behavior locally.
3. Validate Windows/macOS via CI matrix and dry-run tests.
4. Only do manual external OS testing for final acceptance or tricky edge cases.
