#!/usr/bin/env python3
from __future__ import annotations

import sys

from r08_1_common import parse_config_arg, validate_outputs


def main() -> None:
    args = parse_config_arg("Validate EP5 R08.1 vwap_deviation H3 k-fold transferability sensitivity audit outputs")
    payload = validate_outputs(args.config)
    print(payload["validation_status"])
    if payload.get("validation_status") != "passed":
        sys.exit(1)


if __name__ == "__main__":
    main()
