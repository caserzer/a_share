#!/usr/bin/env python3
from __future__ import annotations

from r06_common import parse_config_arg, run_pipeline


def main() -> None:
    args = parse_config_arg("Run EP5 R06 GTJA191 factor decay and information content audit")
    run_pipeline(args.config)


if __name__ == "__main__":
    main()
