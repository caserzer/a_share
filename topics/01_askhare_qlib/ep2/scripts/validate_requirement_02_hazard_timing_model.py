#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json

from requirement_02_hazard_common import validate_requirement_02


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate EP2 Requirement 02 hazard timing model artifacts.")
    parser.add_argument("--config", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = validate_requirement_02(args.config, fail_on_gate_status=True)
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
