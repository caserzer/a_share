#!/usr/bin/env python3
from __future__ import annotations

import json

from r01_high_recall_probe_fail_fast_common import parse_config_arg, run_r01


def main() -> int:
    args = parse_config_arg("Run EP4 R01 high-recall probe fail-fast experiment.")
    result = run_r01(args.config)
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
