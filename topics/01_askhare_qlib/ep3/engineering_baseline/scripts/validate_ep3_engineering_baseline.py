#!/usr/bin/env python3
from __future__ import annotations

import json

from ep3_common import load_config, parse_config_arg, validate_ep3_engineering_baseline


def main() -> int:
    args = parse_config_arg("Validate EP3 engineering baseline artifacts.")
    config, paths = load_config(args.config)
    result = validate_ep3_engineering_baseline(config, paths)
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    return 0 if result["validation_status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
