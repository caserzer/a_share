from pathlib import Path

from experiments.templates.experiment_template.code.diagnostics import (
    missing_output_dirs,
)


def test_template_output_dirs_exist() -> None:
    experiment_root = Path(__file__).resolve().parents[1]
    assert missing_output_dirs(experiment_root) == []
