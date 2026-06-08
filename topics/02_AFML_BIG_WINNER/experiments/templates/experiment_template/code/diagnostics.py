"""Basic diagnostics for an experiment folder."""

from __future__ import annotations

from pathlib import Path


EXPECTED_OUTPUT_DIRS = [
    "data",
    "metrics",
    "tables",
    "figures",
    "reports",
    "manifests",
    "publishable",
    "local_cache",
    "large_raw",
]


def missing_output_dirs(experiment_root: Path) -> list[str]:
    outputs_root = experiment_root / "outputs"
    return [
        name
        for name in EXPECTED_OUTPUT_DIRS
        if not (outputs_root / name).is_dir()
    ]


def main() -> int:
    experiment_root = Path(__file__).resolve().parents[1]
    missing = missing_output_dirs(experiment_root)
    if missing:
        print("missing output dirs: " + ", ".join(missing))
        return 1
    print("output directory contract ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
