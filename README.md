# Transcribe Studio

[![CI](https://github.com/Mishkat-Quantum-Labs/transcribe-studio/actions/workflows/ci.yml/badge.svg)](https://github.com/Mishkat-Quantum-Labs/transcribe-studio/actions/workflows/ci.yml)

A local, browser-based tool for classroom audio transcription. Organize work by **project**, split audio into timed chunks, label speakers in free text, and evaluate human transcripts against LLM output (WER + semantic WER).

Built for researchers and annotators who need millisecond timestamps and exportable data — without Label Studio complexity.

## Features

- **Projects** — group recordings by class, session, or study
- **Waveform editor** — divide audio into chunks (by duration or count), overlap speakers at the same timestamp
- **Chunk playback** — play one chunk at a time with **speed up/down** (0.25×–2×, keys `,` / `.`)
- **Exports** — TXT, Markdown, JSON, CSV, SRT, WebVTT
- **LLM evaluation** — paste or upload hypothesis transcripts; strict + semantic WER
- **Pluggable formats** — timestamp/speaker lines, JSON segments, plain text (TOML-driven)

## Quick start

### With uv (recommended)

```bash
git clone https://github.com/Mishkat-Quantum-Labs/transcribe-studio.git
cd transcribe-studio
uv venv
uv pip install -e ".[dev]"
uv run transcribe-studio
```

Open **http://127.0.0.1:8082**

### With pip

```bash
pip install transcribe-studio
transcribe-studio
```

## Usage

1. Create a **project** from the dashboard
2. **Upload** an MP3/WAV/M4A/OGG/FLAC recording
3. **Divide** the wave into chunks, then transcribe each segment
4. Use **Evaluation** to compare your transcript against an LLM upload
5. **Export** when done

Data is stored under `~/.transcribe-studio/` (override with `TRANSCRIBE_STUDIO_DATA`).

## Development

```bash
uv pip install -e ".[dev]"
uv run pytest
```

## Publishing

### PyPI via uv (recommended)

```bash
uv build
uv publish   # uses UV_PUBLISH_TOKEN or prompts for PyPI credentials
```

### PyPI via pip/twine

```bash
pip install build twine
python -m build
twine upload dist/*
```

### GitHub release

```bash
git tag v0.2.0
git push origin v0.2.0
gh release create v0.2.0 dist/*
```

## Configuration

Evaluation and transcript import settings ship inside the package:

- `app/config/evaluation.toml`
- `app/config/transcript_formats.toml`
- `app/config/languages/en.toml`

## License

MIT — see [LICENSE](LICENSE).

## Contributing

Issues and PRs welcome at [github.com/Mishkat-Quantum-Labs/transcribe-studio](https://github.com/Mishkat-Quantum-Labs/transcribe-studio).