"""Smoke runner for a copied experiment template."""

from __future__ import annotations

import argparse
from pathlib import Path

from afml_big_winner.config import load_yaml
from afml_big_winner.manifest import write_run_manifest


def parse_args() -> argparse.Namespace:
    experiment_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        default=str(experiment_root / "config.yaml"),
        help="Path to this experiment's config.yaml.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config_path = Path(args.config)
    experiment_root = config_path.resolve().parent
    output_dir = experiment_root / "outputs"
    report_path = output_dir / "reports" / "template_smoke_report.md"
    publishable_path = output_dir / "publishable" / "README.md"

    config = load_yaml(config_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    publishable_path.parent.mkdir(parents=True, exist_ok=True)

    report_text = (
        "# Template Smoke Report\n\n"
        "This smoke run proves the experiment folder can load config, write "
        "outputs, and emit a manifest. It is not research evidence.\n\n"
        f"- experiment: `{config.get('experiment', {}).get('name')}`\n"
        f"- workstream: `{config.get('experiment', {}).get('workstream')}`\n"
        f"- status: `{config.get('experiment', {}).get('status')}`\n"
    )
    report_path.write_text(report_text, encoding="utf-8")
    publishable_path.write_text(
        "# Publishable Outputs\n\n"
        "Small reviewed artifacts for this experiment belong here.\n",
        encoding="utf-8",
    )
    script_path = Path(__file__).resolve()
    try:
        script_for_command = script_path.relative_to(Path.cwd().resolve())
    except ValueError:
        script_for_command = script_path

    manifest_path = write_run_manifest(
        manifest_path=output_dir / "manifests" / "run_manifest.json",
        config_path=config_path,
        config=config,
        command=["python", str(script_for_command)],
        decision="template_smoke_only",
        outputs={
            "template_smoke_report": str(report_path),
            "publishable_readme": str(publishable_path),
        },
        data_cutoff=config.get("data", {}).get("data_cutoff"),
    )
    print(f"wrote {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
