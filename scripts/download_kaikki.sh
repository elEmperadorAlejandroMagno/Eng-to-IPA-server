#!/usr/bin/env bash
set -euo pipefail

DATA_DIR="$(dirname "$0")/data"
mkdir -p "$DATA_DIR"

URL="https://kaikki.org/dictionary/raw-wiktextract-data.jsonl.gz"
echo "Downloading ${URL}..."
curl -L "$URL" | gunzip > "$DATA_DIR/words.jsonl"


echo "Done: $DATA_DIR/words.jsonl"
