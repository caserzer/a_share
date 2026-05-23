#!/usr/bin/env python3
from __future__ import annotations

from r07_common import parse_config_arg, run_pipeline


def main() -> None:
    args = parse_config_arg("Run EP5 R07 short-horizon timing and failure attribution audit")
    run_pipeline(args.config)


if __name__ == "__main__":
    main()
