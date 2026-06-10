#!/usr/bin/env python
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import yaml


EXPERIMENT_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = Path(__file__).resolve().parents[4]
SRC_DIR = Path(__file__).resolve().parent

for import_path in (PROJECT_ROOT / "src", SRC_DIR):
    if str(import_path) not in sys.path:
        sys.path.insert(0, str(import_path))

from pipeline import run_pipeline, validate_config  # noqa: E402


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = yaml.safe_load(handle) or {}
    if not isinstance(value, dict):
        raise TypeError(f"expected YAML mapping in {path}")
    return value


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run 07 Top-N multichannel repair candidate generator."
    )
    parser.add_argument(
        "--config",
        default=str(EXPERIMENT_DIR / "config.yaml"),
        help="Experiment config YAML.",
    )
    parser.add_argument(
        "--mode",
        choices=["validate-config", "full"],
        default="full",
        help="Validate config or run the full experiment.",
    )
    parser.add_argument(
        "--max-instruments",
        type=int,
        default=None,
        help="Debug/smoke instrument cap. Full publishable runs must omit this.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Reserved for compatibility; current implementation overwrites outputs.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    config_path = Path(args.config).resolve()
    config = load_yaml(config_path)
    if args.mode == "validate-config":
        validate_config(config)
    result = run_pipeline(
        config,
        config_path=config_path,
        mode=args.mode,
        max_instruments=args.max_instruments,
    )
    print(f"decision={result['decision']}")
    print(f"run_scope={result['run_scope']}")
    if "event_instance_count" in result:
        print(f"event_instances={result['event_instance_count']}")
        print(f"canonical_events={result['canonical_event_count']}")
        print(f"target_episodes={result['target_episode_count']}")
        print(f"manifest={result['manifest_path']}")
        print(f"report={result['report_path']}")
    elif result.get("input_gate_failure_reason"):
        print(f"input_gate_failure_reason={result['input_gate_failure_reason']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
