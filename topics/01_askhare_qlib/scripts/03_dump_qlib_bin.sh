#!/usr/bin/env bash
set -euo pipefail

TOPIC_DIR="${TOPIC_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
QLIB_REPO="${QLIB_REPO:-$HOME/code/qlib}"
QLIB_DIR="${QLIB_DIR:-$TOPIC_DIR/data/qlib/cn_data}"
CSV_DIR="${CSV_DIR:-$TOPIC_DIR/data/interim/qlib_csv/day}"
QLIB_INSTRUMENT_FILE="${QLIB_INSTRUMENT_FILE:-$TOPIC_DIR/data/universe/qlib_selected.txt}"
QLIB_MARKET_NAME="${QLIB_MARKET_NAME:-selected}"
DUMP_BIN="$QLIB_REPO/scripts/dump_bin.py"

if [[ ! -f "$DUMP_BIN" ]]; then
  cat >&2 <<EOF
Missing Qlib dump script: $DUMP_BIN

Set QLIB_REPO to a local microsoft/qlib checkout, for example:
  mkdir -p "$HOME/code"
  git clone https://github.com/microsoft/qlib.git "$HOME/code/qlib"
EOF
  exit 1
fi

if ! compgen -G "$CSV_DIR/*.csv" >/dev/null; then
  echo "No CSV files found in $CSV_DIR. Run scripts/02_transform_to_qlib_csv.py first." >&2
  exit 1
fi

mkdir -p "$QLIB_DIR"

if [[ -z "${PYTHON_BIN:-}" ]]; then
  if [[ -x "$TOPIC_DIR/.venv/bin/python" ]]; then
    PYTHON_BIN="$TOPIC_DIR/.venv/bin/python"
  else
    PYTHON_BIN="python"
  fi
fi

"$PYTHON_BIN" "$DUMP_BIN" dump_all \
  --data_path "$CSV_DIR" \
  --qlib_dir "$QLIB_DIR" \
  --freq day \
  --include_fields open,close,high,low,volume,money,factor \
  --date_field_name date \
  --file_suffix .csv

mkdir -p "$QLIB_DIR/instruments"
cp "$QLIB_INSTRUMENT_FILE" "$QLIB_DIR/instruments/$QLIB_MARKET_NAME.txt"

echo "Qlib data written to $QLIB_DIR"
echo "Custom market written to $QLIB_DIR/instruments/$QLIB_MARKET_NAME.txt"
