#!/usr/bin/env python3
from __future__ import annotations

import json

from r02_evidence_family_discovery_common import DEFAULT_CONFIG, parse_config_arg, validate_r02


def main() -> int:
    args = parse_config_arg("Validate EP4 R02 evidence family discovery artifacts.", DEFAULT_CONFIG)
    result = validate_r02(args.config, fail_on_research_gates=False)
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
