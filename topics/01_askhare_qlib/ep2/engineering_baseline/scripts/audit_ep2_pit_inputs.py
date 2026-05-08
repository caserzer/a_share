#!/usr/bin/env python3
from __future__ import annotations

import json

from ep2_common import load_config, parse_config_arg, run_input_audits


def main() -> int:
    args = parse_config_arg("Audit EP2 PIT inputs and execution blocks.")
    config, paths = load_config(args.config)
    result = run_input_audits(config, paths)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
