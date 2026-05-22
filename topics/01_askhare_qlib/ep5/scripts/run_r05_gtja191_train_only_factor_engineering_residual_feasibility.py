#!/usr/bin/env python3
from __future__ import annotations

from r05_common import parse_config_arg, run_pipeline


def main() -> None:
    args = parse_config_arg("Run EP5 R05 GTJA191 train-only factor engineering residual feasibility probe")
    run_pipeline(args.config)


if __name__ == "__main__":
    main()
