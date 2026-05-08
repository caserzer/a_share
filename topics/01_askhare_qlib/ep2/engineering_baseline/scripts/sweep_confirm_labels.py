#!/usr/bin/env python3
from __future__ import annotations

import json

from ep2_common import load_config, parse_config_arg, sweep_confirm_labels


def main() -> int:
    args = parse_config_arg("Sweep EP2 confirm labels.")
    config, paths = load_config(args.config)
    result = sweep_confirm_labels(config, paths)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
