#!/usr/bin/env python3
from __future__ import annotations

import json

from ep2_common import load_config, parse_config_arg, run_no_model_baselines


def main() -> int:
    args = parse_config_arg("Run EP2 no-model baseline schedules.")
    config, paths = load_config(args.config)
    result = run_no_model_baselines(config, paths)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
