#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from p0_5_common import load_config, parse_config_arg, validate_p0_5_anchor_failure_diagnostic


def main() -> None:
    args = parse_config_arg("Validate EP3 P0.5 anchor failure diagnostic")
    config, paths = load_config(args.config)
    validate_p0_5_anchor_failure_diagnostic(config, paths)


if __name__ == "__main__":
    main()
