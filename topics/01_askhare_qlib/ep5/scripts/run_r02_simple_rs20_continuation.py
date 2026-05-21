#!/usr/bin/env python3
from __future__ import annotations

from r02_common import parse_config_arg, run_pipeline


def main() -> None:
    args = parse_config_arg("Run EP5 R02 simple RS20 continuation probe")
    run_pipeline(args.config)


if __name__ == "__main__":
    main()
