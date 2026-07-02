#!/usr/bin/env bash
# Alias — use build.sh
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec bash "$DIR/build.sh" "$@"