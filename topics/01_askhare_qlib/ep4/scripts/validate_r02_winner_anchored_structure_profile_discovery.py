#!/usr/bin/env python3
from __future__ import annotations

import json

from r02_winner_anchored_structure_profile_discovery_common import DEFAULT_CONFIG, parse_config_arg, validate_r02_v2


def main() -> int:
    args = parse_config_arg("Validate EP4 R02 V2 winner-anchored structure profile discovery artifacts.", DEFAULT_CONFIG)
    result = validate_r02_v2(args.config)
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
