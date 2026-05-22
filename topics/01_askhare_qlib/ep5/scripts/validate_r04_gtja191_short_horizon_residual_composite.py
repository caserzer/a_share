#!/usr/bin/env python3
from __future__ import annotations

from r04_common import parse_config_arg, validate_outputs


def main() -> None:
    args = parse_config_arg("Validate EP5 R04 GTJA191 short-horizon residual composite outputs")
    result = validate_outputs(args.config)
    print(result["validation_status"])


if __name__ == "__main__":
    main()
