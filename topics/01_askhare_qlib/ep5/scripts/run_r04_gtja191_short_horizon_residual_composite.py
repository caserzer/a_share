#!/usr/bin/env python3
from __future__ import annotations

from r04_common import parse_config_arg, run_pipeline


def main() -> None:
    args = parse_config_arg("Run EP5 R04 GTJA191 short-horizon residual composite feasibility probe")
    run_pipeline(args.config)


if __name__ == "__main__":
    main()
