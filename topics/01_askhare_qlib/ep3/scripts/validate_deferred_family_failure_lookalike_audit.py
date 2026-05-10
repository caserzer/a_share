#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from deferred_family_common import load_config, parse_config_arg, validate_deferred_family_failure_lookalike_audit


def main() -> None:
    args = parse_config_arg("Validate EP3 deferred-family failure-lookalike audit")
    config, paths = load_config(args.config)
    validate_deferred_family_failure_lookalike_audit(config, paths)


if __name__ == "__main__":
    main()
