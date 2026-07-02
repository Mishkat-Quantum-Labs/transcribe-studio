# Install & run

Transcribe Studio runs in the **foreground** — your terminal stays open until you press **Ctrl+C**. It does not run in the background.

Requires **Python 3.11+**.

---

## Quick setup (recommended)

Install once, then run with one word: **`transcribe`** (like typing `grok`).

### Windows (PowerShell)

```powershell
irm https://raw.githubusercontent.com/Mishkat-Quantum-Labs/transcribe-studio/main/scripts/build.ps1 | iex
```

### Linux / macOS

```bash
curl -fsSL https://raw.githubusercontent.com/Mishkat-Quantum-Labs/transcribe-studio/main/scripts/build.sh | bash
```

### Run

1. **Close** the install terminal
2. Open a **new** terminal
3. Type:

```bash
transcribe
```

Opens **http://127.0.0.1:8082**

| Action | Command |
|--------|---------|
| Start (foreground) | `transcribe` |
| Stop (in running terminal) | `Ctrl+C` |
| Stop (from another terminal) | `transcribe stop` |
| Check if running | `transcribe status` |
| Replace stuck instance | `transcribe --force` |
| Different port | `transcribe -p 8083` |

**Aliases:** `ts`, `transcribe-studio` (same commands)

---

## Manual install (PyPI)

```bash
pipx install transcribe-studio
# or: pip install transcribe-studio
```

Upgrade:

```bash
pipx upgrade transcribe-studio
# or: pip install -U transcribe-studio
```

Package: https://pypi.org/project/transcribe-studio/

---

## CLI reference

```bash
transcribe -h
```

| Flag | Short | Default | Description |
|------|-------|---------|-------------|
| `--host ADDR` | | `127.0.0.1` | Bind address |
| `--port PORT` | `-p` | `8082` | TCP port |
| `--force` | `-f` | off | Stop old instance, then start |
| `--help` | `-h` | | Show help |

**Commands:** `start` (default), `stop`, `status`

### Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `TRANSCRIBE_STUDIO_HOST` | `127.0.0.1` | Bind address |
| `TRANSCRIBE_STUDIO_PORT` | `8082` | Listen port |
| `TRANSCRIBE_STUDIO_DATA` | `~/.transcribe-studio` | Database, audio, uploads |

### Examples

```bash
transcribe
transcribe -p 8083
transcribe --host 0.0.0.0 -p 9000
transcribe stop
transcribe start --force
```

---

## Supabase (optional)

1. Open **Settings** in the app (`/settings`)
2. Paste from your [Supabase dashboard](https://supabase.com/dashboard) → Project Settings → API:
   - **Project URL**
   - **Anon (public) key**
   - **Database URL** (Connection string URI — required to auto-create tables)
3. Click **Save** — creates `projects`, `recordings`, `segments` if missing
4. **Test connection** to verify

Credentials are stored **only on your machine**. Keys and database passwords are **never** returned by the API or shown in logs after save.

---

## Troubleshooting

### `transcribe` not recognized (Windows)

Close and reopen PowerShell after install. If still missing:

```powershell
pipx install transcribe-studio
pipx ensurepath
```

Or run from source:

```powershell
cd path\to\transcribe-studio
python -m app
```

### Python `WinError 123` / `_pyrepl` errors (Windows)

If you see repeated `_pyrepl\windows_console.py` / `WinError 123` tracebacks (common in Python 3.13 + Cursor or integrated terminals):

```powershell
$env:PYTHON_BASIC_REPL = "1"
[Environment]::SetEnvironmentVariable("PYTHON_BASIC_REPL", "1", "User")
```

Close the terminal, open a new one, then run `transcribe` again. The install script (`build.ps1`) sets this automatically.

### Port already in use

```bash
transcribe stop
transcribe --force
# or use another port:
transcribe -p 8083
```

On Windows, if the port is stuck after many restarts, **reboot** then `transcribe --force`.

### Local install (from git clone)

```bash
git clone https://github.com/Mishkat-Quantum-Labs/transcribe-studio.git
cd transcribe-studio
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate       # Linux/macOS
pip install -e .
transcribe
```

Or without installing:

```bash
python -m app
```

---

## Security notes

- Supabase anon keys and database URLs stay in local SQLite (`TRANSCRIBE_STUDIO_DATA`)
- API responses mask all secrets; only `configured` / `*_set` flags are exposed
- Install scripts do not collect or transmit credentials
- Revoke and rotate keys in Supabase if a machine is compromised