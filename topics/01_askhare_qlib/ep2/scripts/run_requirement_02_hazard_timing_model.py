#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json

from requirement_02_hazard_common import run_requirement_02


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run EP2 Requirement 02 hazard timing model.")
    parser.add_argument("--config", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = run_requirement_02(args.config)
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
