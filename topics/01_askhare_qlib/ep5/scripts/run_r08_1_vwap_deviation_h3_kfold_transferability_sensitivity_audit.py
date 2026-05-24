#!/usr/bin/env python3
from __future__ import annotations

from r08_1_common import parse_config_arg, run_pipeline


def main() -> None:
    args = parse_config_arg("Run EP5 R08.1 vwap_deviation H3 k-fold transferability sensitivity audit")
    run_pipeline(args.config)


if __name__ == "__main__":
    main()
