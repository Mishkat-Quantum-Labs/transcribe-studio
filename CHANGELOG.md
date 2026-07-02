# Changelog

## 0.2.6 — 2026-07-02

### Added
- `transcribe` — one-word CLI command (like `grok`); runs server in foreground
- `scripts/build.ps1` / `scripts/build.sh` — Grok-style one-line install

### Changed
- Install scripts add `transcribe` to user PATH permanently (Windows + Linux)

## 0.2.5 — 2026-07-02

### Added
- Supabase auto-create tables (`projects`, `recordings`, `segments`) on save/test
- One-command install scripts: `scripts/install.ps1` (PowerShell) and `scripts/install.sh` (Linux/macOS)
- Short CLI alias: `ts` (same as `transcribe-studio`)
- Credential redaction — keys and DB passwords never returned in API or error messages

### Changed
- Supabase Database URL required for table migration (REST check + Postgres DDL)
- Improved `stop` / `--force` on Windows (`taskkill /T`, uvicorn process detection)
- Settings test/save reuse saved anon key when password field is left blank

### Dependencies
- `psycopg[binary]>=3.2.0` for Supabase schema setup

## 0.2.4 — 2026-07-02

### Changed
- Improved `-h` / `--help` with all flags, defaults, and examples
- CLI flags `--host`, `--port` / `-p`, `--force` / `-f` visible on main help
- Explicit foreground-only mode (no background daemon)
- Added [docs/INSTALL.md](docs/INSTALL.md) PyPI user guide

## 0.2.3 — 2026-07-01

### Added
- `transcribe-studio stop` — free the port when a previous instance is still running
- `transcribe-studio status` — check if the server is running
- `transcribe-studio start --force` — replace a stuck instance
- PID file under data dir to detect orphaned background processes

## 0.2.2 — 2026-07-01

### Added
- Terraform `/infra` for AWS free-tier EC2 (Amazon Linux 2, nginx on port 80)
- `TRANSCRIBE_STUDIO_HOST` / `TRANSCRIBE_STUDIO_PORT` environment variables
- Settings UI to connect your own Supabase project (URL, anon key, optional DB URL)

## 0.2.1 — 2026-07-01

### Added
- `--port` and `--host` CLI options
- `python -m app` fallback when `transcribe-studio` is not on PATH (Windows)

## 0.2.0 — 2026-07-01

### Added
- Project-centric UI (dashboard, project settings, per-project upload)
- Chunk playback speed controls (0.25×–2×) with +/- buttons and `,` / `.` hotkeys
- Open-source packaging (MIT license, PyPI metadata, CI)
- User data directory at `~/.transcribe-studio`

### Changed
- Config files moved into `app/config/` for pip/uv installs
- Page routes split into `app/web/routes/`

## 0.1.0

- Initial classroom transcription editor with WER evaluation