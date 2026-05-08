#!/usr/bin/env python3
from __future__ import annotations

import json

from ep2_common import build_launch_pool, load_config, parse_config_arg


def main() -> int:
    args = parse_config_arg("Build EP2 launch observation pool.")
    config, paths = load_config(args.config)
    result = build_launch_pool(config, paths)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
