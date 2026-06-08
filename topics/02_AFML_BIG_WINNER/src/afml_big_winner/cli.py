"""Small CLI for smoke-running the experiment template."""

from __future__ import annotations

import argparse
from pathlib import Path

from afml_big_winner.config import load_yaml
from afml_big_winner.manifest import write_run_manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        default="experiments/templates/experiment_template/config.yaml",
        help="Path to an experiment config.",
    )
    parser.add_argument(
        "--output-dir",
        default="experiments/templates/experiment_template/outputs",
        help="Experiment output directory.",
    )
    args = parser.parse_args(argv)

    config_path = Path(args.config)
    output_dir = Path(args.output_dir)
    config = load_yaml(config_path)
    report_path = output_dir / "reports" / "template_smoke_report.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        "# Template Smoke Report\n\n"
        "This report confirms the experiment template can load its config and "
        "write a manifest. It is not research evidence.\n",
        encoding="utf-8",
    )
    manifest_path = write_run_manifest(
        manifest_path=output_dir / "manifests" / "run_manifest.json",
        config_path=config_path,
        config=config,
        command=["afml-bw-template-run", "--config", str(config_path)],
        decision="template_smoke_only",
        outputs={"template_smoke_report": str(report_path)},
        data_cutoff=config.get("data", {}).get("data_cutoff"),
    )
    print(f"wrote {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
