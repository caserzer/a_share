#!/usr/bin/env python3
from __future__ import annotations

import sys

from r03_common import parse_config_arg, validate_outputs


def main() -> None:
    args = parse_config_arg("Validate EP5 R03 downside volatility shock rebound outputs")
    payload = validate_outputs(args.config)
    print(f"validation_status = {payload['validation_status']}")
    if payload["validation_status"] != "passed":
        for failure in payload.get("failures", []):
            print(f"FAILED: {failure}", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
