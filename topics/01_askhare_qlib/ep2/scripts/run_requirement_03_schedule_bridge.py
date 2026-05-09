#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json

from requirement_03_schedule_bridge_common import run_requirement_03


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run EP2 Requirement 03 schedule bridge.")
    parser.add_argument("--config", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = run_requirement_03(args.config)
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
