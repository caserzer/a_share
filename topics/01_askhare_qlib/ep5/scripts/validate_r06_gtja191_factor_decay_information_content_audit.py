#!/usr/bin/env python3
from __future__ import annotations

import sys

from r06_common import parse_config_arg, validate_outputs


def main() -> None:
    args = parse_config_arg("Validate EP5 R06 GTJA191 factor decay and information content audit outputs")
    payload = validate_outputs(args.config)
    if payload.get("validation_status") != "passed":
        sys.exit(1)


if __name__ == "__main__":
    main()
