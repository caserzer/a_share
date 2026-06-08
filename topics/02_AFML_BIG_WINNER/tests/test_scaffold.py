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


def test_first_data_prepare_experiment_contract() -> None:
    root = Path(__file__).resolve().parents[1]
    config = load_yaml(
        root
        / "experiments"
        / "pending"
        / "data_prepare_pit_largecap_akshare_qlib_v0"
        / "config.yaml"
    )

    assert config["date_range"]["start_date"] == "2017-01-01"
    assert config["date_range"]["end_date"] == "2026-05-31"
    assert (
        config["date_range"]["start_date_policy"]
        == "first_trading_session_on_or_after_start_date"
    )
    assert (
        config["date_range"]["end_date_policy"]
        == "last_trading_session_on_or_before_end_date"
    )
    assert (
        config["universe"]["board_buckets"]["main_board"][
            "market_cap_threshold_cny"
        ]
        == 100_000_000_000
    )
    assert (
        config["universe"]["board_buckets"]["chinext"]["market_cap_threshold_cny"]
        == 50_000_000_000
    )
    assert config["universe"]["exclude_st"] is True
    assert config["universe"]["exclude_suspended"] is True
    assert config["universe"]["qlib_market_date_key"] == "usable_trade_date"
    assert config["fields"]["transaction_value"]["canonical_qlib_field"] == "$money"
    assert "$money" in config["fields"]["qlib_required"]
    assert "$amount" not in config["fields"]["qlib_required"]
    assert config["validation"]["reject_st_or_suspended_membership"] is True
    assert config["validation"]["require_executable_date_keyed_qlib_market"] is True
    assert (
        config["validation"]["coverage_gates"]["price_provider_coverage"]
        == "resolved_start_to_resolved_end_by_trade_date"
    )
    assert config["paths"]["project_data_root"] == "data"
    assert (
        config["paths"]["candidate_before_status_exclusion_csv"]
        == "data/processed/universe/pit_largecap_main_chinext_candidate_before_status_exclusion.csv"
    )
    assert (
        config["paths"]["raw_membership_csv"]
        == "data/processed/universe/pit_largecap_main_chinext_membership_daily.csv"
    )
    assert (
        config["paths"]["executable_membership_csv"]
        == "data/processed/universe/pit_largecap_main_chinext_executable_daily.csv"
    )
    assert all(
        not str(path).startswith("topics/01_askhare_qlib")
        for path in config["paths"].values()
    )
