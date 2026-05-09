#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json

from requirement_04_holding_exit_winner_capture_extension_common import validate_requirement_04


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate EP2 Requirement 04 holding/exit winner-capture extension artifacts.")
    parser.add_argument("--config", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = validate_requirement_04(args.config, fail_on_gate_status=True)
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
