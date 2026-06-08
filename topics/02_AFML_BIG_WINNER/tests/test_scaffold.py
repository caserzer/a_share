from pathlib import Path

from afml_big_winner.config import load_yaml, stable_hash


def test_default_label_config_has_required_clock_fields() -> None:
    root = Path(__file__).resolve().parents[1]
    labels = load_yaml(root / "configs" / "labels.yaml")

    assert labels["labels"]["entry"]["t0"] == "signal_date"
    assert labels["labels"]["entry"]["trade_time"] == "next_executable_open_after_t0"
    assert labels["labels"]["label_families"]["failure_10"]["horizon_days"] == 10


def test_stable_hash_is_deterministic() -> None:
    assert stable_hash({"b": 2, "a": 1}) == stable_hash({"a": 1, "b": 2})
