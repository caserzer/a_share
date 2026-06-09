from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from afml_big_winner.config import load_yaml

from pipeline import run_pipeline


EXPERIMENT_DIR = Path(__file__).resolve().parents[1]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run high-recall repair event candidate generator v0."
    )
    parser.add_argument(
        "--config",
        default=str(EXPERIMENT_DIR / "config.yaml"),
        help="Path to experiment config.",
    )
    parser.add_argument(
        "--max-instruments",
        type=int,
        default=None,
        help="Optional smoke-run instrument cap. Full runs should omit this.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    config_path = Path(args.config)
    config: dict[str, Any] = load_yaml(config_path)
    result = run_pipeline(
        config,
        config_path=config_path,
        max_instruments=args.max_instruments,
    )
    print(f"decision={result['decision']}")
    print(f"raw_events={result['raw_event_count']}")
    print(f"canonical_events={result['canonical_event_count']}")
    print(f"target_episodes={result['target_episode_count']}")
    print(f"manifest={result['manifest_path']}")
    print(f"report={result['report_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
