#!/usr/bin/env python3
from __future__ import annotations

import json
import argparse

from r01_high_recall_probe_fail_fast_common import R01_1_DEFAULT_CONFIG, run_r01_1


def main() -> int:
    parser = argparse.ArgumentParser(description="Run EP4 R01.1 emission-throttled cooling probe experiment.")
    parser.add_argument("--config", default=str(R01_1_DEFAULT_CONFIG))
    args = parser.parse_args()
    result = run_r01_1(args.config)
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
