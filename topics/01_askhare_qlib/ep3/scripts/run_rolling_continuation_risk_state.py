#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from rolling_continuation_risk_state_common import load_config, run_build, run_report, run_validate


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run EP3 rolling continuation / risk-state audit")
    parser.add_argument("command", choices=["build", "validate", "report"])
    parser.add_argument("--config", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config, paths = load_config(args.config)
    if args.command == "build":
        result = run_build(config, paths)
    elif args.command == "validate":
        result = run_validate(config, paths)
    else:
        result = run_report(config, paths)
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
