#!/usr/bin/env python3
from __future__ import annotations

from r08_3_common import parse_config_arg, run_pipeline


def main() -> None:
    args = parse_config_arg("Run EP5 R08.3 daily-observed volume/rank family H3/H5/H10 transferability diagnostic")
    run_pipeline(args.config)


if __name__ == "__main__":
    main()
