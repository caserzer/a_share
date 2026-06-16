from __future__ import annotations

import math
import sys
from pathlib import Path

import pandas as pd


EXPERIMENT_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = Path(__file__).resolve().parents[6]
SRC_DIR = EXPERIMENT_DIR / "src"

for import_path in (PROJECT_ROOT / "topics" / "02_AFML_BIG_WINNER" / "src", SRC_DIR):
    if str(import_path) not in sys.path:
        sys.path.insert(0, str(import_path))

import run_winner_archetype_profiling as profiling  # noqa: E402


def minimal_config() -> dict:
    return {
        "scope": {
            "pit_universe_name": "pit_largecap_main_chinext",
            "pit_universe_join_key": ["instrument", "usable_trade_date"],
            "pit_universe_date_key": "usable_trade_date",
            "pit_universe_filter_policy": "require_instrument_trade_open_date_in_executable_universe",
        }
    }


def test_path_regime_uses_event_fallback_before_missing() -> None:
    assert profiling.normalize_path_regime(None) == "regime_missing"
    assert profiling.normalize_path_regime("") == "regime_missing"
    assert profiling.normalize_path_regime("risk_on") == "risk_on"
    assert profiling.resolve_path_regime("risk_off", "risk_on") == ("risk_off", "episode_regime_bucket")
    assert profiling.resolve_path_regime("", "risk_on") == ("risk_on", "event_regime_bucket_fallback")
    assert profiling.resolve_path_regime(None, "transition") == ("transition", "event_regime_bucket_fallback")
    assert profiling.resolve_path_regime("", "") == ("regime_missing", "unresolved_missing")


def test_load_winner_base_records_path_regime_source(tmp_path: Path) -> None:
    frame = pd.DataFrame(
        [
            {
                "sample_id": "s1",
                "selected_target_id": "t1",
                "canonical_event_id": "e1",
                "instrument": "SH600000",
                "trade_time": "2024-01-02",
                "event_split": "train",
                "event_regime_bucket": "risk_on",
                "episode_regime_bucket": "",
                "denominator_id": "denom_a",
                "horizon_complete_120d": True,
                "event_big_winner_120d_label": True,
            },
            {
                "sample_id": "s2",
                "selected_target_id": "t2",
                "canonical_event_id": "e2",
                "instrument": "SZ300001",
                "trade_time": "2024-01-03",
                "event_split": "validation",
                "event_regime_bucket": "risk_off",
                "episode_regime_bucket": "transition",
                "denominator_id": "denom_b",
                "horizon_complete_120d": True,
                "event_big_winner_120d_label": True,
            },
        ]
    )
    path = tmp_path / "selected_label_event_bindings.parquet"
    frame.to_parquet(path, index=False)
    config = {"run": {"winner_label_column": "event_big_winner_120d_label"}}

    out, audit, failures = profiling.load_winner_base(path, config)

    assert failures == []
    assert out.loc[out["sample_id"].eq("s1"), "path_regime_state"].iloc[0] == "risk_on"
    assert out.loc[out["sample_id"].eq("s1"), "path_regime_source"].iloc[0] == "event_regime_bucket_fallback"
    assert out.loc[out["sample_id"].eq("s2"), "path_regime_state"].iloc[0] == "transition"
    assert out.loc[out["sample_id"].eq("s2"), "path_regime_source"].iloc[0] == "episode_regime_bucket"
    assert audit["raw_episode_regime_missing_event_fallback_n"] == 1
    assert audit["raw_path_regime_unresolved_missing_n"] == 0


def test_apply_pit_universe_filter_excludes_non_pit_rows() -> None:
    raw_base = pd.DataFrame(
        [
            {
                "sample_id": "s1",
                "selected_target_id": "t1",
                "instrument": "SH600000",
                "trade_open_date": "2024-01-02",
                "split": "train",
                "event_regime_state": "risk_on",
                "path_regime_state": "risk_on",
                "binding_canonical_event_id": "e1",
                "source_denominator_id": "denom_a",
                "profiling_row_identity": "s1|t1|denom_a",
                "winner_120": True,
                "horizon_complete_120d": True,
            },
            {
                "sample_id": "s2",
                "selected_target_id": "t2",
                "instrument": "SZ300001",
                "trade_open_date": "2024-01-02",
                "split": "validation",
                "event_regime_state": "risk_off",
                "path_regime_state": "risk_off",
                "binding_canonical_event_id": "e2",
                "source_denominator_id": "denom_b",
                "profiling_row_identity": "s2|t2|denom_b",
                "winner_120": True,
                "horizon_complete_120d": True,
            },
        ]
    )
    pit = pd.DataFrame(
        [
            {
                "instrument": "SH600000",
                "pit_usable_trade_date": "2024-01-02",
                "pit_membership_date": "2023-12-29",
                "pit_available_time": "2023-12-29 close",
                "pit_membership_rule_version": "pit_largecap_akshare_qlib_v0",
                "pit_board_bucket": "main_board",
                "pit_status_source": "daily_bar_presence",
            }
        ]
    )

    pit_base, excluded, audit, failures = profiling.apply_pit_universe_filter(raw_base, pit, minimal_config())

    assert failures == []
    assert len(pit_base) == 1
    assert len(excluded) == 1
    assert audit["raw_09a_winner_candidate_n"] == 2
    assert audit["pit_filtered_profiling_scope_winner_n"] == 1
    assert audit["excluded_non_pit_winner_candidate_n"] == 1
    assert bool(pit_base["pit_universe_member_flag"].iloc[0]) is True
    assert pit_base["pit_membership_rule_version"].iloc[0] == "pit_largecap_akshare_qlib_v0"


def test_injury_join_uses_input_denominator_not_sample_target_only() -> None:
    path_df = pd.DataFrame(
        [
            {
                "sample_id": "s1",
                "selected_target_id": "t1",
                "source_denominator_id": "denom_a",
                "split": "train",
                "profiling_row_identity": "s1|t1|denom_a",
                "path_regime_state": "risk_on",
            },
            {
                "sample_id": "s1",
                "selected_target_id": "t1",
                "source_denominator_id": "denom_b",
                "split": "train",
                "profiling_row_identity": "s1|t1|denom_b",
                "path_regime_state": "risk_off",
            },
        ]
    )
    injury = pd.DataFrame(
        [
            {
                "sample_id": "s1",
                "selected_target_id": "t1",
                "input_denominator_id": "denom_b",
                "injury_input_denominator_id": "denom_b",
                "input_event_key": "k1",
                "split": "train",
                "injury_event_regime_state": "risk_on",
                "winner_120": True,
                "E1_missed_winner_flag": True,
            }
        ]
    )
    tenc_ref = pd.DataFrame(
        [
            {
                "input_event_key": "k1",
                "split": "train",
                "tenc_full_keep9000_rejected_flag": True,
                "bridge_winner": False,
                "tenc_mfe_20d": 0.25,
            }
        ]
    )

    merged, audit, failures = profiling.join_injury_and_10c(path_df, injury, tenc_ref)

    assert failures == []
    assert audit["injury_winner_to_09a_missing_n"] == 0
    assert bool(merged.loc[merged["source_denominator_id"].eq("denom_a"), "injury_scope_flag"].iloc[0]) is False
    assert bool(merged.loc[merged["source_denominator_id"].eq("denom_b"), "injury_scope_flag"].iloc[0]) is True


def test_injury_missing_from_pit_profile_is_exclusion_not_failure() -> None:
    path_df = pd.DataFrame(
        [
            {
                "sample_id": "s1",
                "selected_target_id": "t1",
                "source_denominator_id": "denom_a",
                "split": "train",
                "profiling_row_identity": "s1|t1|denom_a",
                "path_regime_state": "risk_on",
            }
        ]
    )
    injury = pd.DataFrame(
        [
            {
                "sample_id": "s2",
                "selected_target_id": "t2",
                "input_denominator_id": "denom_b",
                "injury_input_denominator_id": "denom_b",
                "input_event_key": "k2",
                "split": "train",
                "injury_event_regime_state": "risk_off",
                "winner_120": True,
                "E1_missed_winner_flag": True,
            }
        ]
    )
    tenc_ref = pd.DataFrame(
        [
            {
                "input_event_key": "k2",
                "split": "train",
                "tenc_full_keep9000_rejected_flag": False,
                "bridge_winner": False,
                "tenc_mfe_20d": 0.10,
            }
        ]
    )

    merged, audit, failures = profiling.join_injury_and_10c(path_df, injury, tenc_ref)

    assert failures == []
    assert audit["injury_winner_to_pit_profile_missing_n"] == 1
    assert audit["injury_excluded_non_pit_universe_n"] == 1
    assert int(merged["injury_scope_flag"].sum()) == 0


def test_day_to_target_one_has_empty_pre_target_window() -> None:
    rows = [{"date": "2020-01-01", "open": 10.0, "high": 10.2, "low": 9.9, "close": 10.0}]
    for idx in range(1, 121):
        rows.append(
            {
                "date": f"2020-01-{idx + 1:02d}" if idx < 30 else f"2020-02-{idx - 29:02d}",
                "open": 10.0,
                "high": 16.0 if idx == 1 else 12.0,
                "low": 9.8,
                "close": 15.5 if idx == 1 else 11.0,
            }
        )
    bars = pd.DataFrame(rows)
    thresholds = profiling.Thresholds(
        winner_mfe_threshold=0.50,
        confirm_upper_barrier=0.12,
        failure_lower_barrier=-0.08,
        failure_max_drawdown=-0.10,
        close_based_drawdown_policy=True,
        hard_failure_first_blocks_winner=True,
        continuation_60_min_mfe_pct=0.20,
        confirm_20_horizon_days=20,
    )

    result = profiling.compute_path_metrics_for_event(bars, "2020-01-01", thresholds, 120, 0.095)

    assert result["winner_path_status"] == "ok"
    assert result["day_to_target"] == 1.0
    assert result["pre_target_window_status"] == "empty_pre_target_window"
    assert math.isnan(result["deepest_pre_target_ret_low"])
    assert result["pre_target_touch_failure_lower_flag"] is False
    assert result["pre_target_close_drawdown_failure_proxy_flag"] is False
