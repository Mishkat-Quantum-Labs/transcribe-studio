#!/usr/bin/env bash
# Transcribe Studio — install (one-liner)
#   curl -fsSL https://raw.githubusercontent.com/Mishkat-Quantum-Labs/transcribe-studio/main/scripts/build.sh | bash
# Then:
#   transcribe

set -euo pipefail

step() { printf '  \033[36m%s\033[0m\n' "$1"; }

echo ""
echo "  Transcribe Studio"
echo "  Install once. Run with: transcribe"
echo ""

PY=""
for cmd in python3.13 python3.12 python3.11 python3 python; do
  command -v "$cmd" >/dev/null 2>&1 || continue
  minor=$("$cmd" -c 'import sys; print(sys.version_info.minor)' 2>/dev/null) || continue
  if [ "$minor" -ge 11 ] 2>/dev/null; then PY=$cmd; break; fi
done
[ -n "$PY" ] || { echo "  Python 3.11+ required." >&2; exit 1; }

step "Python: $PY"
step "Installing transcribe-studio (pipx)..."

"$PY" -m pip install --upgrade pip pipx wheel >/dev/null

if ! command -v pipx >/dev/null 2>&1; then
  "$PY" -m pipx >/dev/null
fi

export PATH="${HOME}/.local/bin:${PATH}"
pipx install transcribe-studio --force >/dev/null 2>&1 || {
  step "pipx failed — using pip --user"
  "$PY" -m pip install --user --upgrade transcribe-studio >/dev/null
}

"$PY" -m pipx ensurepath >/dev/null 2>&1 || true

# Persist PATH in shell rc if missing
LOCAL_BIN="${HOME}/.local/bin"
for rc in "${HOME}/.bashrc" "${HOME}/.zshrc"; do
  if [ -f "$rc" ] && ! grep -q '.local/bin' "$rc" 2>/dev/null; then
    printf '\n# Transcribe Studio\nexport PATH="%s:$PATH"\n' "$LOCAL_BIN" >> "$rc"
  fi
done

echo ""
echo "  Installed."
echo ""
echo "  Open a new terminal, then type:"
echo ""
echo "    transcribe"
echo ""
echo "  Opens http://127.0.0.1:8082 (foreground — Ctrl+C to stop)"
echo ""