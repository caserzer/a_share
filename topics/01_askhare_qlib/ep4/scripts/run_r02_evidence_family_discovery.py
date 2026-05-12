#!/usr/bin/env python3
from __future__ import annotations

import json

from r02_evidence_family_discovery_common import DEFAULT_CONFIG, parse_config_arg, run_r02


def main() -> int:
    args = parse_config_arg("Run EP4 R02 evidence family discovery.", DEFAULT_CONFIG)
    result = run_r02(args.config)
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
