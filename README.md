# Transcribe Studio

[![CI](https://github.com/Mishkat-Quantum-Labs/transcribe-studio/actions/workflows/ci.yml/badge.svg)](https://github.com/Mishkat-Quantum-Labs/transcribe-studio/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/transcribe-studio)](https://pypi.org/project/transcribe-studio/)

A local, browser-based tool for classroom audio transcription. Organize work by **project**, split audio into timed chunks, label speakers in free text, and evaluate human transcripts against LLM output (WER + semantic WER).

Built for researchers and annotators who need millisecond timestamps and exportable data — without Label Studio complexity.

## Features

- **Projects** — group recordings by class, session, or study
- **Waveform editor** — divide audio into chunks, overlap speakers at the same timestamp
- **Chunk playback** — speed up/down (0.25×–2×)
- **Exports** — TXT, Markdown, JSON, CSV, SRT, WebVTT
- **LLM evaluation** — WER + semantic WER vs uploaded transcripts
- **Supabase** — connect your own project; tables auto-created from **Settings**

## Setup (simple & classic)

Python 3.11+ required.

### 1. From PyPI (recommended)

```bash
# With uv (fastest)
uv pip install transcribe-studio

# Or classic pip
pip install transcribe-studio
```

### 2. From git clone (latest code)

```bash
git clone https://github.com/Mishkat-Quantum-Labs/transcribe-studio.git
cd transcribe-studio
uv pip install -e .     # or: pip install -e .
```

### Run

```bash
transcribe
# or: python -m app
# or: uvicorn app.main:app --host 0.0.0.0 --port 8082
```

Runs in the **foreground** (Ctrl+C to stop). Opens http://127.0.0.1:8082

Full instructions + one-liner option: [docs/INSTALL.md](docs/INSTALL.md)

**For server deployment** (free-tier EC2 + git clone + uv + pm2):
see `infra/README.md`

**Important security:**
- Never commit `terraform.tfvars` or `*.tfstate` (already gitignored)
- The Python package on PyPI only contains the `app/` code (infra/ and secrets are excluded via MANIFEST.in + pyproject.toml)

## CLI

| Command | Description |
|---------|-------------|
| `transcribe` | Start web UI (foreground) |
| `transcribe stop` | Free the port |
| `transcribe status` | Check if running |
| `transcribe -p 8083` | Use another port |
| `transcribe --force` | Replace stuck instance |

Aliases: `ts`, `transcribe-studio`

```bash
transcribe -h    # full help
```

| Variable | Default | Description |
|----------|---------|-------------|
| `TRANSCRIBE_STUDIO_HOST` | `127.0.0.1` | Bind address |
| `TRANSCRIBE_STUDIO_PORT` | `8082` | Listen port |
| `TRANSCRIBE_STUDIO_DATA` | `~/.transcribe-studio` | Database & audio |

## Usage

1. Create a **project** from the dashboard
2. **Upload** audio (MP3, WAV, M4A, OGG, FLAC)
3. **Divide** into chunks and transcribe
4. **Evaluation** — compare against LLM transcript
5. **Export** when done
6. **Settings** — optional Supabase backup (URL + anon key + database URL)

## Develop from source

```bash
git clone https://github.com/Mishkat-Quantum-Labs/transcribe-studio.git
cd transcribe-studio
python -m venv .venv && .venv\Scripts\activate   # Windows
pip install -e ".[dev]"
transcribe
pytest
```

Without installing: `python -m app`

## Deploy on AWS (free tier)

```bash
cd infra && cp terraform.tfvars.example terraform.tfvars
terraform init && terraform apply
```

Nginx on port **80** → app on **8082**. See [infra/README.md](infra/README.md).

## Publish to PyPI (maintainers)

```bash
python -m build
TWINE_USERNAME=__token__ TWINE_PASSWORD=pypi-xxx python -m twine upload dist/*
```

## License

MIT — see [LICENSE](LICENSE).

## Contributing

[github.com/Mishkat-Quantum-Labs/transcribe-studio](https://github.com/Mishkat-Quantum-Labs/transcribe-studio)