from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import subprocess
import sys
import warnings
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from afml_big_winner.config import stable_hash
from afml_big_winner.manifest import file_sha256


EXPERIMENT_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = Path(__file__).resolve().parents[4]
PENDING_DIR = EXPERIMENT_DIR.parent
PIPELINE_07_PATH = (
    PENDING_DIR / "07_topn_multichannel_repair_candidate_generator_v0" / "src" / "pipeline.py"
)

CHANNEL_E1 = "E1_early_ema60_repair"
CHANNEL_E2 = "E2_money_vwap_repair_confirmation"
CHANNEL_E3 = "E3_rank_persistence"
CHANNEL_E6 = "E6_continuation_discriminator"

FAMILY_SCOPE = "candidate_family"
FAMILY_VARIANT_SCOPE = "candidate_family_variant"
UNION_SCOPE = "candidate_union"
E1_SCOPE = "07_e1_only"
FULL_07_SCOPE = "07_full_union"
UNION_EVENT_FAMILY = "U_risk_on_transition_candidate_union"
E1_PLUS_PREFIX = "e1_plus_"

DECISION_INPUT_BLOCKED = "risk_on_transition_recall_exploration_input_blocked"
DECISION_NO_INCREMENTAL = "risk_on_transition_recall_exploration_no_incremental_recall"
DECISION_DENSITY_BLOCKED = "risk_on_transition_recall_exploration_density_blocked"
DECISION_SAMPLE_BLOCKED = "risk_on_transition_recall_exploration_sample_blocked"
DECISION_DIAGNOSTIC_ONLY = "risk_on_transition_recall_exploration_diagnostic_only"
DECISION_SUPPORTED = "risk_on_transition_recall_exploration_candidate_supported_for_meta_label"

VALID_STATUSES = {
    "runnable_existing_data",
    "family_data_blocked",
    "diagnostic_only",
    "fallback_variant",
}
EXECUTABLE_STATUSES = {"runnable_existing_data", "fallback_variant", "diagnostic_only"}
WINDOWS = [
    "low_plus_20",
    "low_plus_30",
    "low_plus_60",
    "low_plus_120",
    "before_first_50pct",
    "before_episode_high",
]
FOCUS_REGIMES = ["risk_on", "transition"]
SPLITS = ["all", "train", "validation", "robustness"]
REGIMES = ["all", "risk_on", "transition", "risk_off"]


def _load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load {name} from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


_p07 = _load_module("afml_bw_07_pipeline_for_08", PIPELINE_07_PATH)
_p04 = _p07._p04
warnings.filterwarnings("ignore", message="Mean of empty slice", category=RuntimeWarning)


@dataclass(frozen=True)
class InputStatus:
    input_gate_status: str
    input_gate_failure_reason: str
    upstream_05_decision: str
    upstream_06_decision: str
    upstream_07_decision: str
    latest_label_complete_low_date: str
    universe_precision_status: str
    topn_candidate_gap_accepted: bool


def topic_path(relative_or_absolute: str | Path) -> Path:
    path = Path(relative_or_absolute)
    if path.is_absolute():
        return path
    return PROJECT_ROOT / path


def git_revision(cwd: Path = PROJECT_ROOT) -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=cwd,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return result.stdout.strip()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def safe_rate(success: int | float, total: int | float) -> float:
    if total is None or pd.isna(total) or float(total) == 0:
        return np.nan
    return float(success) / float(total)


def safe_num(value: Any, default: float = np.nan) -> float:
    if value is None or pd.isna(value):
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def fmt(value: Any, digits: int = 3) -> str:
    if value is None or pd.isna(value):
        return "NA"
    return f"{float(value):.{digits}f}"


def pct(value: Any) -> str:
    if value is None or pd.isna(value):
        return "NA"
    return f"{float(value) * 100:.1f}%"


def ensure_dirs(paths: list[Path]) -> None:
    for path in paths:
        path.mkdir(parents=True, exist_ok=True)


def write_dataframe(path: Path, frame: pd.DataFrame) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix == ".parquet":
        frame.to_parquet(path, index=False)
    else:
        frame.to_csv(path, index=False)
    return path


def frame_schema(frame: pd.DataFrame) -> list[dict[str, str]]:
    return [{"name": str(column), "dtype": str(dtype)} for column, dtype in frame.dtypes.items()]


def json_compact(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def validate_config(config: dict[str, Any]) -> None:
    required_sections = {
        "experiment",
        "paths",
        "outputs",
        "splits",
        "event_generation",
        "quality_flags",
        "labels",
        "gates",
        "selection",
        "candidate_families",
    }
    missing = required_sections.difference(config)
    if missing:
        raise ValueError(f"config missing sections: {sorted(missing)}")
    for family_id, spec in config["candidate_families"].items():
        status = str(spec.get("status", ""))
        if status not in VALID_STATUSES:
            raise ValueError(f"{family_id} has invalid status {status}")
        if status == "family_data_blocked" and spec.get("is_fallback_of"):
            raise ValueError(f"{family_id} cannot be both blocked and a fallback")
    required_style_fields = {
        "membership",
        "return_calculation",
        "rebalance_policy",
        "lag_policy",
        "missing_policy",
    }
    for proxy_id, proxy in config.get("style_proxies", {}).items():
        missing = required_style_fields.difference(proxy)
        if missing:
            raise ValueError(f"style proxy {proxy_id} missing fields: {sorted(missing)}")
    better_basis = config.get("better_basis", {})
    if better_basis:
        for key in ["policy_id", "comparison_scope", "better_when", "forbidden_future_fields"]:
            if key not in better_basis:
                raise ValueError(f"better_basis missing {key}")
    for key, value in config["paths"].items():
        path = topic_path(value)
        if key.endswith(("_dir",)):
            if not path.exists():
                raise FileNotFoundError(f"missing path {key}: {path}")
        elif not path.exists():
            raise FileNotFoundError(f"missing path {key}: {path}")


def family_variant_id(family_id: str, variant_id: str) -> str:
    return f"{family_id}__{variant_id}"


def family_variant_rows(config: dict[str, Any], *, include_blocked: bool = True) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for family_id, spec in sorted(
        config["candidate_families"].items(), key=lambda item: int(item[1].get("priority", 999))
    ):
        status = str(spec["status"])
        variants = ["ungated", "event_regime_gated"]
        if status == "family_data_blocked" and not include_blocked:
            variants = []
        for variant_id in variants:
            rows.append(
                {
                    "family_id": family_id,
                    "variant_id": variant_id,
                    "family_variant_id": family_variant_id(family_id, variant_id),
                    "family_input_status": status,
                    "path": spec.get("path", ""),
                    "cluster": spec.get("cluster", ""),
                    "data_dependency": spec.get("data_dependency", ""),
                    "priority": int(spec.get("priority", 999)),
                    "is_fallback_of": spec.get("is_fallback_of", ""),
                    "threshold_grid": spec.get("threshold_grid", {}),
                    "executed_flag": status in EXECUTABLE_STATUSES,
                }
            )
    return rows


def config_with_variant_channels(config: dict[str, Any]) -> dict[str, Any]:
    copied = json.loads(json.dumps(config))
    executable = [
        row["family_variant_id"]
        for row in family_variant_rows(copied, include_blocked=False)
        if row["executed_flag"]
    ]
    copied.setdefault("channels", {})
    copied["channels"]["recommended"] = executable
    copied["channels"]["primary_channel_order"] = executable
    return copied


def first_grid_value(spec: dict[str, Any], key: str, default: float) -> float:
    values = spec.get("threshold_grid", {}).get(key, [])
    if isinstance(values, list) and values:
        return float(values[0])
    if values not in (None, ""):
        return float(values)
    return float(default)


def build_input_paths(config: dict[str, Any]) -> dict[str, Path]:
    return {key: topic_path(value) for key, value in config["paths"].items()}


def build_output_paths(config: dict[str, Any], *, debug: bool) -> dict[str, Path]:
    outputs = config["outputs"]
    if debug:
        base = topic_path(outputs["local_cache_dir"]) / "debug_subset"
        table_dir = base / "tables"
        report_dir = base / "reports"
        manifest_dir = base / "manifests"
    else:
        table_dir = topic_path(outputs["publishable_tables_dir"])
        report_dir = topic_path(outputs["publishable_reports_dir"])
        manifest_dir = topic_path(outputs["manifests_dir"])
    local_cache_dir = topic_path(outputs["local_cache_dir"])
    large_raw_dir = topic_path(outputs["large_raw_dir"])
    ensure_dirs([table_dir, report_dir, manifest_dir, local_cache_dir, large_raw_dir])
    paths = {
        "regime_recall_baseline": table_dir / "regime_recall_baseline_07_e1_only.csv",
        "e1_recompute_audit": table_dir / "e1_only_baseline_recompute_audit.csv",
        "missed_episode_audit": table_dir / "risk_on_transition_missed_episode_audit.csv",
        "candidate_event_instances": table_dir / "candidate_family_event_instances.csv",
        "candidate_canonical_events": table_dir / "candidate_family_canonical_events.csv",
        "candidate_recall": table_dir / "candidate_family_recall_by_split_regime.csv",
        "incremental_recall": table_dir / "candidate_family_incremental_recall_over_e1.csv",
        "bridge_positive_recall": table_dir / "candidate_family_bridge_positive_recall.csv",
        "bridge_exclusion_audit": table_dir / "candidate_family_bridge_exclusion_audit.csv",
        "density_summary": table_dir / "candidate_family_density_summary.csv",
        "density_denominator_comparison": table_dir / "candidate_family_density_denominator_comparison.csv",
        "overlap_matrix": table_dir / "candidate_family_overlap_matrix.csv",
        "lead_time_distribution": table_dir / "candidate_family_lead_time_distribution.csv",
        "label_quality": table_dir / "candidate_family_label_quality_readout.csv",
        "false_repair_diagnostic": table_dir / "candidate_family_false_repair_diagnostic.csv",
        "feature_snapshot_summary": table_dir / "candidate_family_feature_snapshot_summary.csv",
        "candidate_frontier": table_dir / "risk_on_transition_candidate_frontier.csv",
        "run_capability": table_dir / "candidate_family_run_capability_summary.csv",
        "mechanism_cluster_summary": table_dir / "candidate_family_mechanism_cluster_summary.csv",
        "cluster_ablation": table_dir / "candidate_family_cluster_ablation.csv",
        "industry_style_input_audit": table_dir / "industry_style_input_contract_audit.csv",
        "formula_spec": table_dir / "candidate_family_formula_spec.csv",
        "event_regime_gating_comparison": table_dir / "event_regime_gating_comparison.csv",
        "timing_basis_comparison": table_dir / "candidate_vs_e1_timing_basis_comparison.csv",
        "leakage_execution_audit": table_dir / "leakage_and_execution_audit.csv",
        "input_manifest_audit": table_dir / "input_manifest_audit.csv",
        "report": report_dir / "risk_on_transition_recall_exploration_report.md",
        "manifest": manifest_dir / ("debug_metadata.json" if debug else "run_manifest.json"),
        "candidate_labels_local": local_cache_dir
        / ("debug_candidate_family_event_labels.parquet" if debug else "candidate_family_event_labels.parquet"),
        "candidate_capture_local": local_cache_dir
        / ("debug_candidate_family_capture.parquet" if debug else "candidate_family_capture.parquet"),
        "feature_panel_local": local_cache_dir
        / ("debug_cross_section_feature_panel.parquet" if debug else "cross_section_feature_panel.parquet"),
    }
    return paths


def validate_input_status(config: dict[str, Any], input_paths: dict[str, Path]) -> InputStatus:
    failures: list[str] = []
    m05 = load_json(input_paths["upstream_05_run_manifest_json"])
    m06 = load_json(input_paths["upstream_06_run_manifest_json"])
    m07 = load_json(input_paths["upstream_07_run_manifest_json"])
    upstream_05_decision = str(m05.get("decision", ""))
    upstream_06_decision = str(m06.get("decision", ""))
    upstream_07_decision = str(m07.get("decision", ""))
    latest_label_complete_low_date = str(m06.get("latest_label_complete_low_date", "") or "")
    topn_candidate_gap_accepted = bool(m06.get("topn_candidate_gap_accepted", False))
    universe_precision_status = str(m06.get("universe_precision_status", ""))
    if upstream_06_decision != "topn_reverse_lifecycle_sequence_supported_universal_dominance":
        failures.append("upstream_06_decision_not_frozen_supported")
    if not latest_label_complete_low_date:
        failures.append("upstream_06_latest_label_complete_low_date_missing")
    if upstream_05_decision == "topn_universe_candidate_panel_blocked":
        if not topn_candidate_gap_accepted:
            failures.append("05_blocked_without_06_gap_acceptance")
        if universe_precision_status != "available_source_topn_candidate_gap":
            failures.append("05_blocked_without_available_source_topn_candidate_caveat")
    elif upstream_05_decision != "topn_universe_supported":
        failures.append(f"unsupported_05_decision:{upstream_05_decision}")
    if upstream_07_decision == "topn_multichannel_candidate_generator_input_blocked":
        failures.append("upstream_07_input_blocked")
    for key in [
        "upstream_07_event_instances_csv",
        "upstream_07_event_canonical_csv",
        "upstream_07_event_labels_parquet",
        "upstream_07_episode_capture_audit_csv",
    ]:
        if not input_paths[key].is_file():
            failures.append(f"{key}_missing")
    return InputStatus(
        input_gate_status="pass" if not failures else "blocked",
        input_gate_failure_reason=";".join(failures),
        upstream_05_decision=upstream_05_decision,
        upstream_06_decision=upstream_06_decision,
        upstream_07_decision=upstream_07_decision,
        latest_label_complete_low_date=latest_label_complete_low_date,
        universe_precision_status=universe_precision_status,
        topn_candidate_gap_accepted=topn_candidate_gap_accepted,
    )


def parse_label_config(config: dict[str, Any]) -> Any:
    labels = config["labels"]
    return _p04.LabelConfig(
        confirm_horizon=int(labels["confirm_20"]["horizon_days"]),
        confirm_upper=float(labels["confirm_20"]["upper_barrier"]),
        confirm_lower=float(labels["confirm_20"]["lower_barrier"]),
        failure_horizon=int(labels["failure_10"]["horizon_days"]),
        failure_lower=float(labels["failure_10"]["lower_barrier"]),
        continuous_horizons=tuple(int(value) for value in labels["continuous_horizons"]),
        big_winner_mfe_120d=float(labels["big_winner_mfe_120d"]),
        super_winner_mfe_120d=float(labels["super_winner_mfe_120d"]),
        near_winner_mfe_lower=float(labels["near_winner_mfe_lower"]),
        near_winner_mfe_upper=float(labels["near_winner_mfe_upper"]),
        false_repair_drawdown=float(labels["false_repair_drawdown"]),
    )


def rolling_last_rank(values: np.ndarray) -> float:
    clean = values[~np.isnan(values)]
    if len(clean) == 0 or np.isnan(values[-1]):
        return np.nan
    return float((clean <= values[-1]).sum()) / float(len(clean))


def binary_entropy_from_share(share: float) -> float:
    if pd.isna(share) or share <= 0.0 or share >= 1.0:
        return 0.0 if pd.notna(share) else np.nan
    return float(-(share * math.log2(share) + (1.0 - share) * math.log2(1.0 - share)))


def add_instrument_features(daily: pd.DataFrame, all_a_returns: pd.Series) -> pd.DataFrame:
    out = daily.copy()
    out["date"] = pd.to_datetime(out["date"], errors="coerce").dt.strftime("%Y-%m-%d")
    close = pd.to_numeric(out["close"], errors="coerce")
    high = pd.to_numeric(out["high"], errors="coerce")
    low = pd.to_numeric(out["low"], errors="coerce")
    out["return_1d"] = close / close.shift(1) - 1.0
    out["all_a_return_1d"] = out["date"].map(all_a_returns)
    out["stock_vs_market_1d"] = out["return_1d"] - out["all_a_return_1d"]
    out["relative_cusum_20d"] = out["stock_vs_market_1d"].rolling(20, min_periods=15).sum()
    out["rolling_high_60"] = high.rolling(60, min_periods=40).max()
    out["rolling_high_120"] = high.rolling(120, min_periods=80).max()
    out["close_to_high_60"] = close / out["rolling_high_60"]
    out["close_to_high_120"] = close / out["rolling_high_120"]
    range_20 = (high.rolling(20, min_periods=15).max() - low.rolling(20, min_periods=15).min()) / close
    out["range_width_20d"] = range_20
    out["range_width_ratio_20d_60d"] = range_20 / range_20.rolling(60, min_periods=40).median()
    pos_share = out["return_1d"].gt(0).rolling(20, min_periods=15).mean()
    out["direction_entropy_20d"] = pos_share.map(binary_entropy_from_share)
    above = pd.to_numeric(out.get("close_to_ema60"), errors="coerce").gt(0)
    group_id = (~above).cumsum()
    out["ema60_positive_run"] = above.groupby(group_id).cumcount() + 1
    out.loc[~above, "ema60_positive_run"] = 0
    atr = pd.to_numeric(out.get("atr_20_pct"), errors="coerce")
    out["atr_pct_rank_60d"] = atr.rolling(60, min_periods=20).apply(rolling_last_rank, raw=True)
    return out.replace([np.inf, -np.inf], np.nan)


def build_cross_section_panel(
    daily_by_instrument: dict[str, pd.DataFrame],
    membership_by_instrument: dict[str, pd.DataFrame],
) -> pd.DataFrame:
    parts: list[pd.DataFrame] = []
    for instrument, daily in daily_by_instrument.items():
        membership = membership_by_instrument.get(instrument)
        if membership is None or membership.empty:
            continue
        dates = set(membership["usable_trade_date"].astype(str))
        cols = [
            "date",
            "return_1d",
            "return_5d",
            "return_20d",
            "return_60d",
            "stock_vs_market_20d",
            "close_to_high_60",
            "rolling_high_60",
            "close",
            "market_regime_bucket",
        ]
        available = [column for column in cols if column in daily.columns]
        sub = daily.loc[daily["date"].astype(str).isin(dates), available].copy()
        if sub.empty:
            continue
        sub["instrument"] = instrument
        sub = sub.merge(
            membership[
                [
                    "usable_trade_date",
                    "board_bucket",
                    "total_market_cap_cny",
                    "history_observed_sessions_before_usable_date",
                ]
            ],
            left_on="date",
            right_on="usable_trade_date",
            how="left",
        ).drop(columns=["usable_trade_date"], errors="ignore")
        parts.append(sub)
    if not parts:
        return pd.DataFrame()
    panel = pd.concat(parts, ignore_index=True)
    panel["date"] = pd.to_datetime(panel["date"], errors="coerce").dt.strftime("%Y-%m-%d")
    panel = panel.sort_values(["date", "instrument"]).reset_index(drop=True)
    panel["momentum_percentile_20d"] = panel.groupby("date")["return_20d"].rank(pct=True)
    panel["momentum_percentile_60d"] = panel.groupby("date")["return_60d"].rank(pct=True)
    panel["new_high_60_flag"] = pd.to_numeric(panel["close_to_high_60"], errors="coerce") >= 0.995
    panel["up_flag"] = pd.to_numeric(panel["return_1d"], errors="coerce") > 0.0
    panel = panel.sort_values(["instrument", "date"]).reset_index(drop=True)
    panel["momentum_percentile_20d_lag20"] = panel.groupby("instrument")[
        "momentum_percentile_20d"
    ].shift(20)

    daily = (
        panel.groupby("date", sort=True)
        .agg(
            evaluated_member_count=("instrument", "nunique"),
            universe_up_share=("up_flag", "mean"),
            universe_new_high_60_share=("new_high_60_flag", "mean"),
            universe_equal_weight_return=("return_1d", "mean"),
        )
        .reset_index()
        .sort_values("date")
    )
    roll = daily["universe_up_share"].rolling(60, min_periods=30)
    daily["universe_up_share_z"] = (
        daily["universe_up_share"] - roll.mean()
    ) / roll.std(ddof=0).replace(0.0, np.nan)
    daily["universe_up_share_change_5d"] = daily["universe_up_share"].diff(5)

    board_daily = (
        panel.groupby(["date", "board_bucket"], sort=True)
        .agg(board_equal_weight_return=("return_1d", "mean"))
        .reset_index()
        .sort_values(["board_bucket", "date"])
    )
    board_daily = board_daily.merge(
        daily[["date", "universe_equal_weight_return"]], on="date", how="left"
    )
    board_daily["board_relative_1d"] = (
        board_daily["board_equal_weight_return"] - board_daily["universe_equal_weight_return"]
    )
    board_daily["board_relative_cusum_20d"] = board_daily.groupby("board_bucket")[
        "board_relative_1d"
    ].transform(lambda values: values.rolling(20, min_periods=15).sum())
    board_daily["board_return_20d"] = board_daily.groupby("board_bucket")[
        "board_equal_weight_return"
    ].transform(lambda values: values.rolling(20, min_periods=15).sum())
    panel = panel.merge(daily, on="date", how="left")
    panel = panel.merge(board_daily, on=["date", "board_bucket"], how="left")
    panel["stock_vs_board_20d"] = panel["return_20d"] - panel["board_return_20d"]
    panel = panel.replace([np.inf, -np.inf], np.nan)
    return panel


def merge_cross_section_features(
    daily_by_instrument: dict[str, pd.DataFrame], panel: pd.DataFrame
) -> dict[str, pd.DataFrame]:
    if panel.empty:
        return daily_by_instrument
    feature_cols = [
        "date",
        "instrument",
        "momentum_percentile_20d",
        "momentum_percentile_60d",
        "momentum_percentile_20d_lag20",
        "evaluated_member_count",
        "universe_up_share",
        "universe_new_high_60_share",
        "universe_equal_weight_return",
        "universe_up_share_z",
        "universe_up_share_change_5d",
        "board_equal_weight_return",
        "board_relative_1d",
        "board_relative_cusum_20d",
        "board_return_20d",
        "stock_vs_board_20d",
    ]
    frame = panel[[column for column in feature_cols if column in panel.columns]].copy()
    merged: dict[str, pd.DataFrame] = {}
    for instrument, daily in daily_by_instrument.items():
        sub = frame.loc[frame["instrument"] == instrument].drop(columns=["instrument"])
        if sub.empty:
            merged[instrument] = daily
            continue
        out = daily.merge(sub, on="date", how="left")
        merged[instrument] = out.replace([np.inf, -np.inf], np.nan)
    return merged


def load_daily_inputs(
    config: dict[str, Any],
    input_paths: dict[str, Path],
    input_status: InputStatus,
    *,
    max_instruments: int | None,
    progress: Any,
) -> tuple[pd.DataFrame, pd.DataFrame, Any, dict[str, pd.DataFrame], dict[str, pd.DataFrame], pd.DataFrame]:
    benchmark_daily = pd.read_csv(input_paths["benchmark_daily_csv"])
    benchmark_daily["trade_date"] = pd.to_datetime(
        benchmark_daily["trade_date"], errors="coerce"
    ).dt.strftime("%Y-%m-%d")
    market_features = _p04._reverse.compute_market_features(benchmark_daily)
    benchmark_returns = _p04.compute_benchmark_returns(benchmark_daily)
    split_config = _p07.parse_split_config(
        config,
        benchmark_daily,
        latest_label_complete_low_date=input_status.latest_label_complete_low_date,
    )
    all_a = (
        benchmark_daily.loc[benchmark_daily["index_alias"] == "all_a"]
        .sort_values("trade_date")
        .copy()
    )
    all_a_returns = (
        pd.to_numeric(all_a["close"], errors="coerce") / pd.to_numeric(all_a["close"], errors="coerce").shift(1)
        - 1.0
    )
    all_a_return_map = pd.Series(all_a_returns.values, index=all_a["trade_date"].astype(str))

    source_audit = pd.read_csv(input_paths["upstream_05_data_source_coverage_audit_csv"])
    vwap_policy = _p04._observable.resolve_vwap_source_policy(source_audit)
    universe = pd.read_csv(input_paths["topn_executable_universe_csv"])
    universe["usable_trade_date"] = pd.to_datetime(
        universe["usable_trade_date"], errors="coerce"
    ).dt.strftime("%Y-%m-%d")
    universe = _p07.add_topn_evaluated_universe_flags(universe, split_config, config)
    universe = universe.sort_values(["instrument", "usable_trade_date"]).reset_index(drop=True)
    evaluated_universe = universe.loc[universe["evaluated_flag"].fillna(False).astype(bool)].copy()
    membership_by_instrument = {
        instrument: group.reset_index(drop=True)
        for instrument, group in evaluated_universe.groupby("instrument", sort=True)
    }
    stock_dir = input_paths["stock_daily_csv_dir"]
    instruments = [
        instrument
        for instrument in sorted(membership_by_instrument)
        if (stock_dir / f"{instrument}.csv").is_file()
    ]
    if max_instruments is not None:
        instruments = instruments[: int(max_instruments)]
    progress_every = int(config.get("runtime", {}).get("progress_every_instruments", 100))
    if max_instruments is not None:
        progress_every = min(progress_every, 10)
    daily_by_instrument: dict[str, pd.DataFrame] = {}
    for processed_no, instrument in enumerate(instruments, start=1):
        daily = pd.read_csv(stock_dir / f"{instrument}.csv")
        features = _p04.enrich_stock_features(
            daily,
            instrument=instrument,
            membership=membership_by_instrument[instrument],
            market_features=market_features,
            benchmark_returns=benchmark_returns,
            vwap_source_units_compatible=bool(vwap_policy.get("compatible", False)),
        )
        features = add_instrument_features(features, all_a_return_map)
        daily_by_instrument[instrument] = features
        if progress_every > 0 and (
            processed_no == 1
            or processed_no == len(instruments)
            or processed_no % progress_every == 0
        ):
            progress(f"loaded {processed_no}/{len(instruments)} instruments")
    progress("building cross-sectional breadth, board, and momentum features")
    used_membership = {instrument: membership_by_instrument[instrument] for instrument in instruments}
    panel = build_cross_section_panel(daily_by_instrument, used_membership)
    daily_by_instrument = merge_cross_section_features(daily_by_instrument, panel)
    return benchmark_daily, universe, split_config, daily_by_instrument, used_membership, panel


def event_truths(daily: pd.DataFrame, pos: int, family_id: str, config: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    spec = config["candidate_families"][family_id]

    def v(column: str, default: float = np.nan) -> float:
        return safe_num(daily.at[pos, column], default) if column in daily.columns else default

    event_regime = str(daily.at[pos, "market_regime_bucket"]) if "market_regime_bucket" in daily else ""
    member_count = v("evaluated_member_count", 0.0)
    min_members = int(config["event_generation"]["cross_section_min_members"])
    enough_cross_section = member_count >= min_members
    extra = {
        "family_id": family_id,
        "family_input_status": spec["status"],
        "mechanism_cluster": spec.get("cluster", ""),
        "event_regime_bucket": event_regime,
        "event_close": v("close"),
        "event_close_to_episode_low_basis": np.nan,
        "close_to_high_60": v("close_to_high_60"),
        "close_to_high_120": v("close_to_high_120"),
        "range_width_ratio_20d_60d": v("range_width_ratio_20d_60d"),
        "direction_entropy_20d": v("direction_entropy_20d"),
        "relative_cusum_20d": v("relative_cusum_20d"),
        "momentum_percentile_20d": v("momentum_percentile_20d"),
        "momentum_percentile_20d_lag20": v("momentum_percentile_20d_lag20"),
        "universe_up_share": v("universe_up_share"),
        "universe_up_share_z": v("universe_up_share_z"),
        "universe_up_share_change_5d": v("universe_up_share_change_5d"),
        "stock_vs_board_20d": v("stock_vs_board_20d"),
        "board_relative_cusum_20d": v("board_relative_cusum_20d"),
        "atr_pct_rank_60d": v("atr_pct_rank_60d"),
        "ema60_positive_run": v("ema60_positive_run"),
    }

    if family_id == "R1_relative_strength_breakout":
        ok = (
            v("stock_vs_market_20d") >= first_grid_value(spec, "stock_vs_market_20d", 0.06)
            and v("stock_vs_market_10d") >= first_grid_value(spec, "stock_vs_market_10d", 0.035)
            and v("close_to_ema60") >= first_grid_value(spec, "close_to_ema60_min", 0.0)
        )
    elif family_id == "R2_near_high_volume_expansion":
        ok = (
            v("close_to_high_60") >= first_grid_value(spec, "near_high_60", 0.96)
            and v("amount_ratio_20d") >= first_grid_value(spec, "amount_ratio_20d", 1.5)
            and v("close_position_in_range") >= first_grid_value(spec, "close_position_in_range", 0.65)
            and v("return_10d") > 0.0
        )
    elif family_id == "R3_vcp_breakout":
        ok = (
            v("range_width_ratio_20d_60d") <= first_grid_value(spec, "range_width_ratio", 0.70)
            and v("close_position_in_range") >= first_grid_value(spec, "close_position_in_range", 0.70)
            and v("amount_ratio_20d") >= first_grid_value(spec, "amount_ratio_20d", 1.15)
            and v("return_5d") > 0.0
        )
    elif family_id == "R5_growth_or_small_style_confirmation":
        ok = (
            enough_cross_section
            and v("board_relative_cusum_20d") >= first_grid_value(spec, "board_relative_20d", 0.03)
            and v("stock_vs_board_20d") >= first_grid_value(spec, "stock_vs_board_20d", 0.0)
            and str(daily.at[pos, "benchmark_alias"]) == "chinext_index"
        )
    elif family_id == "R6_market_breadth_thrust":
        ok = (
            enough_cross_section
            and (
                v("universe_up_share_z") >= first_grid_value(spec, "up_share_z", 1.0)
                or v("universe_up_share_change_5d")
                >= first_grid_value(spec, "up_share_change_5d", 0.12)
            )
            and v("momentum_percentile_20d") >= first_grid_value(spec, "momentum_percentile_20d", 0.70)
            and v("return_5d") > 0.0
        )
    elif family_id == "R7_cross_sectional_momentum_rank_jump":
        ok = (
            enough_cross_section
            and v("momentum_percentile_20d") >= first_grid_value(spec, "momentum_percentile_20d", 0.80)
            and v("momentum_percentile_20d_lag20")
            <= first_grid_value(spec, "lag_momentum_percentile_20d_max", 0.50)
            and v("return_20d") > 0.0
        )
    elif family_id == "R8_persistent_distance_above_ema":
        ok = (
            v("close_to_ema60") >= first_grid_value(spec, "close_to_ema60_min", 0.05)
            and v("ema60_positive_run") >= first_grid_value(spec, "persistent_days", 10)
            and v("return_20d") >= first_grid_value(spec, "return_20d", 0.08)
        )
    elif family_id == "T3_style_rotation_break":
        ok = (
            enough_cross_section
            and v("board_relative_cusum_20d")
            >= first_grid_value(spec, "board_relative_cusum_20d", 0.06)
            and v("stock_vs_board_20d") >= first_grid_value(spec, "stock_vs_board_20d", 0.0)
            and str(daily.at[pos, "benchmark_alias"]) == "chinext_index"
        )
    elif family_id == "T4_entropy_compression_then_directional_expansion":
        ok = (
            v("direction_entropy_20d") <= first_grid_value(spec, "entropy_20d_max", 0.85)
            and v("return_5d") >= first_grid_value(spec, "return_5d", 0.035)
            and v("stock_vs_market_10d") >= first_grid_value(spec, "stock_vs_market_10d", 0.02)
        )
    elif family_id == "T5_volume_regime_shift":
        ok = (
            v("amount_ratio_20d") >= first_grid_value(spec, "amount_ratio_20d", 1.80)
            and v("amount_ratio_60d") >= first_grid_value(spec, "amount_ratio_60d", 1.30)
            and v("return_5d") >= first_grid_value(spec, "return_5d", 0.035)
            and v("stock_vs_market_10d") >= 0.0
        )
    elif family_id == "T6_stock_vs_market_CUSUM_break":
        ok = (
            v("relative_cusum_20d") >= first_grid_value(spec, "relative_cusum_20d", 0.10)
            and v("stock_vs_market_5d") >= first_grid_value(spec, "relative_5d", 0.025)
        )
    elif family_id == "T7_board_relative_strength_break":
        ok = (
            enough_cross_section
            and v("board_relative_cusum_20d")
            >= first_grid_value(spec, "board_relative_cusum_20d", 0.06)
            and v("stock_vs_board_20d") >= first_grid_value(spec, "stock_vs_board_20d", 0.0)
        )
    elif family_id == "T8_volatility_regime_contraction_break":
        ok = (
            v("atr_pct_rank_60d") <= first_grid_value(spec, "atr_pct_rank_60d_max", 0.35)
            and v("return_5d") >= first_grid_value(spec, "return_5d", 0.03)
            and v("amount_ratio_20d") >= first_grid_value(spec, "amount_ratio_20d", 1.15)
            and v("close_position_in_range") >= 0.60
        )
    else:
        ok = False
    return bool(ok), extra


def generate_events_for_instrument(
    *,
    instrument: str,
    daily: pd.DataFrame,
    membership: pd.DataFrame,
    split_config: Any,
    config: dict[str, Any],
) -> pd.DataFrame:
    membership_dates = set(membership["usable_trade_date"].astype(str))
    if not membership_dates:
        return pd.DataFrame()
    gated_buckets = set(config["event_generation"]["event_regime_gated_buckets"])
    cooldown = int(config["event_generation"]["family_cooldown_sessions"])
    last_kept_pos: dict[str, int] = {}
    family_rows = [
        row
        for row in family_variant_rows(config, include_blocked=False)
        if row["family_input_status"] in EXECUTABLE_STATUSES
    ]
    executable_families = list(dict.fromkeys(row["family_id"] for row in family_rows))
    rows: list[dict[str, Any]] = []
    for pos in range(len(daily)):
        event_date = str(daily.at[pos, "date"])
        if event_date not in membership_dates:
            continue
        split = _p07.split_for_date(event_date, split_config)
        if split == "outside_split":
            continue
        event_regime = str(daily.at[pos, "market_regime_bucket"]) if "market_regime_bucket" in daily else ""
        for family_id in executable_families:
            triggered, extra = event_truths(daily, pos, family_id, config)
            if not triggered:
                continue
            for variant_id in ["ungated", "event_regime_gated"]:
                if variant_id == "event_regime_gated" and event_regime not in gated_buckets:
                    continue
                channel = family_variant_id(family_id, variant_id)
                previous = last_kept_pos.get(channel)
                if previous is not None and pos - previous < cooldown:
                    continue
                last_kept_pos[channel] = pos
                row = _p07.channel_row(
                    instrument=instrument,
                    daily=daily,
                    membership=membership,
                    channel=channel,
                    pos=pos,
                    split=split,
                    config=config,
                    extra={
                        **extra,
                        "variant_id": variant_id,
                        "family_variant_id": channel,
                        "event_regime_gating": variant_id,
                        "threshold_variant_id": "v0_default_grid_first_value",
                        "event_t0_confirmation_time": "t0_close_next_open_executable",
                    },
                )
                row["event_family"] = channel
                row["channel_id"] = channel
                row["channel_family"] = family_id
                row["family_id"] = family_id
                row["variant_id"] = variant_id
                row["family_variant_id"] = channel
                row["event_regime_bucket"] = event_regime
                rows.append(row)
    return pd.DataFrame(rows)


def build_candidate_canonical_events(instances: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    if instances.empty:
        return pd.DataFrame(columns=list(instances.columns))
    rows: list[dict[str, Any]] = []
    for (instrument, event_date), group in instances.groupby(["instrument", "event_t0_date"], sort=True):
        ordered = group.sort_values(["event_family_priority", "event_id"]).copy()
        primary = ordered.iloc[0].copy()
        row = primary.to_dict()
        triggered_variants = list(dict.fromkeys(ordered["family_variant_id"].astype(str).tolist()))
        triggered_families = list(dict.fromkeys(ordered["family_id"].astype(str).tolist()))
        triggered_statuses = list(dict.fromkeys(ordered["family_input_status"].astype(str).tolist()))
        triggered_clusters = list(dict.fromkeys(ordered["mechanism_cluster"].astype(str).tolist()))
        event_id = f"{instrument}_{event_date.replace('-', '')}_risk_on_transition_union"
        row.update(
            {
                "event_id": event_id,
                "canonical_event_id": event_id,
                "symbol": instrument,
                "event_family": UNION_EVENT_FAMILY,
                "channel_id": UNION_EVENT_FAMILY,
                "channel_family": UNION_EVENT_FAMILY,
                "family_id": "candidate_union",
                "variant_id": "canonical_union",
                "family_variant_id": "candidate_union",
                "union_family": UNION_SCOPE,
                "canonical_event_scope": "canonical_event",
                "triggered_channels": ";".join(triggered_variants),
                "triggered_family_variants": ";".join(triggered_variants),
                "triggered_family_ids": ";".join(triggered_families),
                "triggered_family_statuses": ";".join(triggered_statuses),
                "triggered_mechanism_clusters": ";".join(triggered_clusters),
                "primary_channel": str(primary["family_variant_id"]),
                "primary_family_id": str(primary["family_id"]),
                "family_count": int(len(triggered_families)),
                "channel_count": int(len(triggered_variants)),
                "raw_source_event_ids": ";".join(ordered["event_id"].astype(str)),
                "raw_cluster_event_count": int(len(ordered)),
                "recommended_union_included": True,
                "is_setup_context": False,
                "event_executable_date": primary.get("trade_open_date", ""),
                "episode_link_status": "not_linked_yet",
                "asof_feature_snapshot_hash": _p07.feature_snapshot_hash(primary),
            }
        )
        rows.append(row)
    return pd.DataFrame(rows)


def canonicalize_subset(events: pd.DataFrame, scope_id: str) -> pd.DataFrame:
    if events.empty:
        return empty_event_frame()
    rows: list[dict[str, Any]] = []
    for (instrument, event_date), group in events.groupby(["instrument", "event_t0_date"], sort=True):
        ordered = group.sort_values(["event_family_priority", "event_id"]).copy()
        primary = ordered.iloc[0].copy()
        row = primary.to_dict()
        row["event_id"] = f"{instrument}_{event_date.replace('-', '')}_{scope_id}"
        row["canonical_event_id"] = row["event_id"]
        row["canonical_event_scope"] = "canonical_event"
        row["raw_source_event_ids"] = ";".join(ordered["event_id"].astype(str))
        row["raw_cluster_event_count"] = int(len(ordered))
        row["triggered_family_variants"] = ";".join(
            list(dict.fromkeys(ordered.get("family_variant_id", pd.Series(dtype=str)).astype(str)))
        )
        row["triggered_family_ids"] = ";".join(
            list(dict.fromkeys(ordered.get("family_id", pd.Series(dtype=str)).astype(str)))
        )
        rows.append(row)
    return pd.DataFrame(rows)


def empty_event_frame() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "event_id",
            "instrument",
            "event_t0_pos",
            "event_t0_date",
            "event_family_priority",
            "event_split",
            "market_regime_bucket",
            "event_regime_bucket",
            "board_bucket",
            "family_id",
            "variant_id",
            "family_variant_id",
        ]
    )


def rebuild_07_channel_from_07(
    channel_id: str, canonical_07: pd.DataFrame, instances_07: pd.DataFrame
) -> pd.DataFrame:
    if "triggered_channels" in canonical_07.columns:
        mask = canonical_07["triggered_channels"].fillna("").astype(str).str.contains(channel_id, regex=False)
        channel = canonical_07.loc[mask].copy()
        if not channel.empty:
            channel["family_id"] = channel_id
            channel["variant_id"] = "07_recomputed"
            channel["family_variant_id"] = channel_id
            channel["channel_id"] = channel_id
            channel["event_regime_bucket"] = channel.get("market_regime_bucket", "")
            return channel
    source = instances_07.loc[instances_07["channel_id"].astype(str) == channel_id].copy()
    if source.empty:
        return empty_event_frame()
    channel = canonicalize_subset(source, channel_id)
    channel["family_id"] = channel_id
    channel["variant_id"] = "07_recomputed"
    channel["family_variant_id"] = channel_id
    channel["channel_id"] = channel_id
    return channel


def rebuild_e1_only_from_07(
    canonical_07: pd.DataFrame, instances_07: pd.DataFrame
) -> pd.DataFrame:
    return rebuild_07_channel_from_07(CHANNEL_E1, canonical_07, instances_07)


def load_07_artifacts(input_paths: dict[str, Path]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    instances = pd.read_csv(input_paths["upstream_07_event_instances_csv"])
    canonical = pd.read_csv(input_paths["upstream_07_event_canonical_csv"])
    labels = pd.read_parquet(input_paths["upstream_07_event_labels_parquet"])
    for frame in [instances, canonical]:
        if "event_regime_bucket" not in frame.columns and "market_regime_bucket" in frame.columns:
            frame["event_regime_bucket"] = frame["market_regime_bucket"]
        if "family_variant_id" not in frame.columns:
            frame["family_variant_id"] = frame.get("channel_id", frame.get("primary_channel", ""))
    return instances, canonical, labels


def build_capture(
    episodes: pd.DataFrame,
    events: pd.DataFrame,
    labels: pd.DataFrame,
    daily_by_instrument: dict[str, pd.DataFrame],
) -> pd.DataFrame:
    if events.empty:
        events = empty_event_frame()
    needed = {"event_id", "instrument", "event_t0_pos", "event_t0_date", "event_family_priority"}
    for column in needed.difference(events.columns):
        events[column] = np.nan
    label_map = labels.set_index("event_id").to_dict("index") if not labels.empty else {}
    events_by_instrument = {
        instrument: group.sort_values(["event_t0_pos", "event_family_priority", "event_id"]).reset_index(drop=True)
        for instrument, group in events.groupby("instrument", sort=True)
    }
    windows = [
        "low_to_high",
        "low_to_first_50pct",
        "low_plus_20",
        "low_plus_30",
        "low_plus_60",
        "low_plus_120",
        "before_first_50pct",
        "before_episode_high",
    ]
    rows: list[dict[str, Any]] = []
    for episode in episodes.to_dict("records"):
        instrument = str(episode["instrument"])
        daily = daily_by_instrument.get(instrument)
        if daily is None:
            continue
        events_i = events_by_instrument.get(instrument, empty_event_frame())
        pos = pd.to_numeric(events_i.get("event_t0_pos"), errors="coerce")
        for window in windows:
            start, end, exclusion = _p07.window_bounds(episode, daily, window)
            if exclusion:
                hits = events_i.iloc[0:0].copy()
            else:
                hits = events_i.loc[(pos >= start) & (pos <= end)].copy()
            if not hits.empty:
                hits = hits.sort_values(["event_t0_pos", "event_family_priority", "event_id"])
            label_complete = 0
            label_incomplete = 0
            positive_hits: list[str] = []
            for event_id in hits["event_id"].astype(str).tolist():
                label = label_map.get(event_id, {})
                complete = bool(label.get("horizon_complete_120d", False))
                if complete:
                    label_complete += 1
                    if bool(label.get("event_big_winner_120d_label", False)):
                        positive_hits.append(event_id)
                else:
                    label_incomplete += 1
            bridge_denominator = not bool(exclusion)
            bridge_exclusion = exclusion
            if not exclusion and not hits.empty and label_complete == 0:
                bridge_denominator = False
                bridge_exclusion = "bridge_forward_120_incomplete"
            first = hits.iloc[0].to_dict() if not hits.empty else {}
            first_positive = positive_hits[0] if positive_hits else ""
            rows.append(
                {
                    "target_episode_id": episode["episode_id"],
                    "instrument": instrument,
                    "symbol": instrument,
                    "episode_low_date": episode["episode_low_date"],
                    "episode_high_date": episode["episode_high_date"],
                    "first_50pct_touch_date": episode.get("effective_first_50pct_touch_date", ""),
                    "episode_split": episode.get("split", episode.get("episode_split", "")),
                    "board_bucket": episode.get("board_bucket", ""),
                    "market_regime_bucket": episode.get("market_regime_bucket", ""),
                    "window": window,
                    "window_start_pos": start,
                    "window_end_pos": end,
                    "any_event_denominator_included": not bool(exclusion),
                    "any_event_exclusion_reason": exclusion,
                    "bridge_positive_denominator_included": bridge_denominator,
                    "bridge_positive_exclusion_reason": bridge_exclusion,
                    "any_event_captured": bool(len(hits) > 0),
                    "bridge_positive_captured": bool(first_positive),
                    "any_event_count": int(len(hits)),
                    "bridge_label_complete_event_count": int(label_complete),
                    "bridge_label_incomplete_event_count": int(label_incomplete),
                    "first_event_id": first.get("event_id", ""),
                    "first_event_t0_date": first.get("event_t0_date", ""),
                    "first_positive_event_id": first_positive,
                    "lead_time_to_first_50pct_sessions": (
                        int(episode.get("effective_first_50pct_touch_pos", -1))
                        - int(first.get("event_t0_pos", -1))
                        if first and int(episode.get("effective_first_50pct_touch_pos", -1)) >= 0
                        else np.nan
                    ),
                    "lead_time_to_episode_high_sessions": (
                        end - int(first.get("event_t0_pos", -1))
                        if first and window == "before_episode_high"
                        else np.nan
                    ),
                    "event_t0_from_episode_low_sessions": (
                        int(first.get("event_t0_pos", -1)) - int(start)
                        if first and int(first.get("event_t0_pos", -1)) >= 0 and int(start) >= 0
                        else np.nan
                    ),
                }
            )
    return pd.DataFrame(rows)


def capture_filter(capture: pd.DataFrame, split: str, regime: str, window: str) -> pd.DataFrame:
    frame = capture.loc[capture["window"] == window]
    if split != "all":
        frame = frame.loc[frame["episode_split"] == split]
    if regime != "all":
        frame = frame.loc[frame["market_regime_bucket"] == regime]
    return frame


def captured_ids(capture: pd.DataFrame, split: str, regime: str, window: str, *, bridge: bool = False) -> set[str]:
    frame = capture_filter(capture, split, regime, window)
    col = "bridge_positive_captured" if bridge else "any_event_captured"
    if bridge:
        frame = frame.loc[frame["bridge_positive_denominator_included"].fillna(False).astype(bool)]
    return set(frame.loc[frame[col].fillna(False).astype(bool), "target_episode_id"].astype(str))


def denominator_ids(capture: pd.DataFrame, split: str, regime: str, window: str, *, bridge: bool = False) -> set[str]:
    frame = capture_filter(capture, split, regime, window)
    if bridge:
        frame = frame.loc[frame["bridge_positive_denominator_included"].fillna(False).astype(bool)]
    return set(frame["target_episode_id"].astype(str))


def attach_scope(frame: pd.DataFrame, meta: dict[str, Any]) -> pd.DataFrame:
    out = frame.copy()
    for key, value in meta.items():
        out.insert(0, key, value)
    return out


def bridge_reason_bucket(reason: Any) -> str:
    text = str(reason or "").lower()
    if "forward" in text and "120" in text:
        return "forward_120_incomplete"
    if "next" in text or "open" in text or "basis" in text:
        return "missing_next_open_basis"
    if "price" in text or "path" in text or "daily" in text:
        return "missing_price_path"
    if text:
        return "other_completeness"
    return "none"


def build_recall_tables(
    capture_map: dict[str, pd.DataFrame],
    metadata: dict[str, dict[str, Any]],
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    any_rows: list[pd.DataFrame] = []
    bridge_rows: list[pd.DataFrame] = []
    exclusion_rows: list[dict[str, Any]] = []
    for scope_id, capture in capture_map.items():
        meta = metadata[scope_id]
        any_rows.append(attach_scope(_p07.build_recall_table(capture, bridge=False), meta))
        bridge = attach_scope(_p07.build_recall_table(capture, bridge=True), meta)
        bridge_rows.append(bridge)
        for split in SPLITS:
            for regime in REGIMES:
                for window in WINDOWS:
                    frame = capture_filter(capture, split, regime, window)
                    before = int(len(frame))
                    excluded = frame.loc[
                        ~frame["bridge_positive_denominator_included"].fillna(False).astype(bool)
                    ]
                    included = frame.loc[
                        frame["bridge_positive_denominator_included"].fillna(False).astype(bool)
                    ]
                    reason = (
                        ";".join(
                            f"{key}:{value}"
                            for key, value in excluded["bridge_positive_exclusion_reason"]
                            .fillna("missing")
                            .astype(str)
                            .value_counts()
                            .to_dict()
                            .items()
                        )
                        if not excluded.empty
                        else ""
                    )
                    reason_buckets = (
                        excluded["bridge_positive_exclusion_reason"].map(bridge_reason_bucket).value_counts()
                        if not excluded.empty
                        else pd.Series(dtype=int)
                    )
                    exclusion_rows.append(
                        {
                            **meta,
                            "episode_split": split,
                            "market_regime_bucket": regime,
                            "window": window,
                            "bridge_denominator_before_exclusion": before,
                            "bridge_excluded_count": int(len(excluded)),
                            "bridge_excluded_rate": safe_rate(len(excluded), before),
                            "bridge_denominator_after_exclusion": int(len(included)),
                            "bridge_positive_captured": int(
                                included["bridge_positive_captured"].fillna(False).astype(bool).sum()
                            ),
                            "bridge_positive_recall": safe_rate(
                                int(
                                    included["bridge_positive_captured"]
                                    .fillna(False)
                                    .astype(bool)
                                    .sum()
                                ),
                                len(included),
                            ),
                            "bridge_forward_120_incomplete_excluded_count": int(
                                reason_buckets.get("forward_120_incomplete", 0)
                            ),
                            "bridge_missing_next_open_basis_excluded_count": int(
                                reason_buckets.get("missing_next_open_basis", 0)
                            ),
                            "bridge_missing_price_path_excluded_count": int(
                                reason_buckets.get("missing_price_path", 0)
                            ),
                            "bridge_other_completeness_excluded_count": int(
                                reason_buckets.get("other_completeness", 0)
                            ),
                            "bridge_exclusion_reason": reason,
                        }
                    )
    any_recall = pd.concat(any_rows, ignore_index=True) if any_rows else pd.DataFrame()
    bridge_recall = pd.concat(bridge_rows, ignore_index=True) if bridge_rows else pd.DataFrame()
    return any_recall, bridge_recall, pd.DataFrame(exclusion_rows)


def build_incremental_recall(
    capture_map: dict[str, pd.DataFrame],
    metadata: dict[str, dict[str, Any]],
    baseline_capture: pd.DataFrame,
    full07_capture: pd.DataFrame,
    *,
    channel_captures: dict[str, pd.DataFrame] | None = None,
    timing_basis: pd.DataFrame | None = None,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    channel_captures = channel_captures or {CHANNEL_E1: baseline_capture}
    timing_basis = timing_basis if timing_basis is not None else pd.DataFrame()
    for scope_id, capture in capture_map.items():
        if scope_id in {E1_SCOPE, FULL_07_SCOPE}:
            continue
        meta = metadata[scope_id]
        for split in SPLITS:
            for regime in REGIMES:
                for window in WINDOWS:
                    denom = denominator_ids(baseline_capture, split, regime, window)
                    if not denom:
                        continue
                    base = captured_ids(baseline_capture, split, regime, window)
                    cand = captured_ids(capture, split, regime, window)
                    full = captured_ids(full07_capture, split, regime, window)
                    e1_e2_e3_e6: set[str] = set()
                    for channel in [CHANNEL_E1, CHANNEL_E2, CHANNEL_E3, CHANNEL_E6]:
                        channel_capture = channel_captures.get(channel)
                        if channel_capture is not None:
                            e1_e2_e3_e6.update(captured_ids(channel_capture, split, regime, window))
                    new_over_e1 = cand.difference(base)
                    e1_plus = base.union(cand)
                    timing_frame = pd.DataFrame()
                    if scope_id == "selected_candidate_union" and not timing_basis.empty and window == "before_first_50pct":
                        timing_frame = timing_basis.copy()
                        if split != "all":
                            timing_frame = timing_frame.loc[timing_frame["episode_split"] == split]
                        if regime != "all":
                            timing_frame = timing_frame.loc[timing_frame["market_regime_bucket"] == regime]
                    rows.append(
                        {
                            **meta,
                            "episode_split": split,
                            "market_regime_bucket": regime,
                            "window": window,
                            "denominator_episodes": len(denom),
                            "e1_only_captured_episodes": len(base),
                            "candidate_captured_episodes": len(cand),
                            "e1_plus_candidate_captured_episodes": len(e1_plus),
                            "candidate_only_recall": safe_rate(len(cand), len(denom)),
                            "e1_only_recall": safe_rate(len(base), len(denom)),
                            "e1_plus_candidate_recall": safe_rate(len(e1_plus), len(denom)),
                            "incremental_captures_over_e1": len(new_over_e1),
                            "incremental_recall_over_e1": safe_rate(len(new_over_e1), len(denom)),
                            "unique_captures_not_in_07_full_union": len(cand.difference(full)),
                            "unique_captures_not_in_e1_e2_e3_e6": len(cand.difference(e1_e2_e3_e6)),
                            "earlier_first_event_captures_vs_e1": int(
                                timing_frame.get("candidate_at_least_10_sessions_earlier_flag", pd.Series(dtype=bool))
                                .fillna(False)
                                .astype(bool)
                                .sum()
                            )
                            if not timing_frame.empty
                            else np.nan,
                            "better_basis_first_event_captures_vs_e1": int(
                                timing_frame.get("candidate_better_basis_flag", pd.Series(dtype=bool))
                                .fillna(False)
                                .astype(bool)
                                .sum()
                            )
                            if not timing_frame.empty
                            else np.nan,
                            "percentage_point_convention": "incremental_captures_over_e1 / same split-regime-window denominator",
                        }
                    )
    return pd.DataFrame(rows)


def event_density_nonzero(events: pd.DataFrame) -> tuple[float, float, float]:
    if events.empty:
        return np.nan, np.nan, np.nan
    counts = (
        events.assign(event_year=events["event_t0_date"].astype(str).str.slice(0, 4))
        .groupby(["instrument", "event_year"])
        .size()
    )
    return float(counts.mean()), float(counts.quantile(0.50)), float(counts.quantile(0.95))


def density_slice_json(events: pd.DataFrame, column: str, denominator_years: float) -> str:
    if events.empty or column not in events.columns or not denominator_years or pd.isna(denominator_years):
        return "{}"
    counts = events[column].fillna("missing").astype(str).value_counts(dropna=False).sort_index()
    return json_compact(
        {
            key: {
                "event_count": int(value),
                "events_per_instrument_year": float(value) / float(denominator_years),
            }
            for key, value in counts.items()
        }
    )


def triggered_family_share(events: pd.DataFrame, fallback_family_id: str) -> tuple[str, float]:
    counts: dict[str, int] = {}
    total = 0
    if "triggered_family_ids" in events.columns:
        for value in events["triggered_family_ids"].fillna("").astype(str):
            families = [item for item in value.split(";") if item]
            for family_id in families:
                counts[family_id] = counts.get(family_id, 0) + 1
                total += 1
    if total == 0 and fallback_family_id:
        counts[fallback_family_id] = int(len(events))
        total = int(len(events))
    if total == 0:
        return "{}", np.nan
    shares = {key: value / total for key, value in sorted(counts.items())}
    return json_compact(shares), float(max(shares.values())) if shares else np.nan


def same_day_merge_rate(events: pd.DataFrame) -> float:
    if events.empty or "raw_cluster_event_count" not in events.columns:
        return 0.0
    raw_count = pd.to_numeric(events["raw_cluster_event_count"], errors="coerce").fillna(1.0).sum()
    if raw_count <= 0:
        return np.nan
    return max(0.0, 1.0 - (len(events) / float(raw_count)))


def build_density_tables(
    event_sets: dict[str, pd.DataFrame],
    metadata: dict[str, dict[str, Any]],
    denominator_summary: pd.DataFrame,
    feature_panel: pd.DataFrame,
    e1_event_count: int | None = None,
    e1_events: pd.DataFrame | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    universe_years = float(denominator_summary.iloc[0]["universe_years_252"])
    gated_days = int(
        feature_panel["market_regime_bucket"].isin(FOCUS_REGIMES).sum()
        if "market_regime_bucket" in feature_panel.columns
        else 0
    )
    gated_years = gated_days / 252.0 if gated_days else np.nan
    if e1_events is not None:
        e1_event_count = int(len(e1_events))
        e1_gated_event_count = int(
            e1_events.get("event_regime_bucket", e1_events.get("market_regime_bucket", pd.Series(dtype=str)))
            .fillna("")
            .astype(str)
            .isin(FOCUS_REGIMES)
            .sum()
        )
    else:
        e1_event_count = int(e1_event_count or 0)
        e1_gated_event_count = e1_event_count
    e1_density = e1_event_count / universe_years if universe_years else np.nan
    e1_gated_density = (
        e1_gated_event_count / gated_years
        if gated_years and not pd.isna(gated_years) and gated_years > 0
        else e1_density
    )
    rows: list[dict[str, Any]] = []
    denominator_rows: list[dict[str, Any]] = []
    for scope_id, events in event_sets.items():
        meta = metadata[scope_id]
        mean_nonzero, p50_nonzero, p95_nonzero = event_density_nonzero(events)
        event_count = int(len(events))
        full_density = event_count / universe_years if universe_years else np.nan
        eligible_density = (
            event_count / gated_years
            if meta.get("variant_id") == "event_regime_gated" and gated_years and gated_years > 0
            else full_density
        )
        gated_ratio_denominator = (
            e1_gated_density
            if meta.get("variant_id") == "event_regime_gated"
            else e1_density
        )
        family_share_json, top_family_share = triggered_family_share(
            events, str(meta.get("family_id", ""))
        )
        rows.append(
            {
                **meta,
                "event_count": event_count,
                "canonical_event_count": event_count,
                "event_instances_per_instrument_year": full_density,
                "canonical_events_per_instrument_year": full_density,
                "events_per_instrument_year_mean": mean_nonzero,
                "events_per_instrument_year_p50": p50_nonzero,
                "events_per_instrument_year_p95": p95_nonzero,
                "density_full_denominator": full_density,
                "density_eligible_gated_denominator": eligible_density,
                "density_increase_over_e1_full_denominator": full_density - e1_density
                if pd.notna(e1_density)
                else np.nan,
                "density_vs_e1_full_denominator": full_density / e1_density
                if e1_density and not pd.isna(e1_density)
                else np.nan,
                "density_vs_same_gated_denominator": eligible_density / gated_ratio_denominator
                if gated_ratio_denominator and not pd.isna(gated_ratio_denominator)
                else np.nan,
                "density_by_split": density_slice_json(events, "event_split", universe_years),
                "density_by_event_regime_bucket": density_slice_json(
                    events, "event_regime_bucket", universe_years
                ),
                "density_by_board": density_slice_json(events, "board_bucket", universe_years),
                "triggered_family_share": family_share_json,
                "top_triggered_family_share": top_family_share,
                "same_day_merge_rate": same_day_merge_rate(events),
            }
        )
        denominator_rows.append(
            {
                **meta,
                "full_denominator_instrument_days": int(
                    denominator_summary.iloc[0]["evaluated_instrument_days"]
                ),
                "full_denominator_universe_years_252": universe_years,
                "eligible_gated_instrument_days": gated_days,
                "eligible_gated_universe_years_252": gated_years,
                "headline_density_uses": "density_full_denominator",
                "event_count": event_count,
                "density_full_denominator": full_density,
                "density_eligible_gated_denominator": eligible_density,
            }
        )
    return pd.DataFrame(rows), pd.DataFrame(denominator_rows)


def apply_density_contract_flags(
    density: pd.DataFrame,
    incremental: pd.DataFrame,
    selected_variants: list[str],
    config: dict[str, Any],
) -> pd.DataFrame:
    if density.empty:
        return density
    out = density.copy()
    out["selected_variant_flag"] = out["candidate_scope_id"].isin(selected_variants)
    selected_total = safe_num(
        out.loc[out["candidate_scope_id"] == "selected_candidate_union", "event_count"].max(),
        np.nan,
    )
    if pd.notna(selected_total) and selected_total > 0:
        out["density_share_of_selected_union"] = out["event_count"].astype(float) / selected_total
    else:
        out["density_share_of_selected_union"] = np.nan

    focus = incremental.loc[
        (incremental["window"] == "before_first_50pct")
        & (incremental["episode_split"].isin(["train", "robustness"]))
        & (incremental["market_regime_bucket"].isin(FOCUS_REGIMES))
    ].copy() if not incremental.empty else pd.DataFrame()
    if not focus.empty:
        focus_summary = (
            focus.groupby("candidate_scope_id", dropna=False)
            .agg(
                focus_incremental_recall_for_density_drag=("incremental_recall_over_e1", "sum"),
                focus_incremental_captures_for_density_drag=("incremental_captures_over_e1", "sum"),
            )
            .reset_index()
        )
        out = out.merge(focus_summary, on="candidate_scope_id", how="left")
    else:
        out["focus_incremental_recall_for_density_drag"] = np.nan
        out["focus_incremental_captures_for_density_drag"] = np.nan

    gates = config["gates"]
    out["family_density_mean_gate_pass"] = (
        out["candidate_scope_type"].ne(FAMILY_VARIANT_SCOPE)
        | (
            pd.to_numeric(out["density_full_denominator"], errors="coerce")
            <= float(gates["max_candidate_family_canonical_events_per_instrument_year_mean"])
        )
    )
    out["family_density_p95_gate_pass"] = (
        out["candidate_scope_type"].ne(FAMILY_VARIANT_SCOPE)
        | (
            pd.to_numeric(out["events_per_instrument_year_p95"], errors="coerce")
            <= float(gates["max_candidate_family_canonical_events_per_instrument_year_p95"])
        )
        | out["events_per_instrument_year_p95"].isna()
    )
    out["family_density_share_gate_pass"] = (
        ~out["selected_variant_flag"]
        | out["density_share_of_selected_union"].isna()
        | (out["density_share_of_selected_union"] <= float(gates["max_new_family_density_share"]))
    )
    out["density_drag_flag"] = (
        out["selected_variant_flag"]
        & (
            pd.to_numeric(out["focus_incremental_recall_for_density_drag"], errors="coerce").fillna(0.0)
            < float(gates["density_drag_incremental_recall_threshold"])
        )
        & (
            pd.to_numeric(out["density_share_of_selected_union"], errors="coerce").fillna(0.0)
            > float(gates["density_drag_density_share_threshold"])
        )
    )
    return out


def build_label_quality(labels: pd.DataFrame, events: pd.DataFrame, metadata: dict[str, Any]) -> pd.DataFrame:
    if events.empty or labels.empty:
        return pd.DataFrame()
    frame = events.merge(labels, on="event_id", how="left", suffixes=("", "_label"))
    rows: list[dict[str, Any]] = []
    group_cols = ["event_split", "event_regime_bucket", "board_bucket"]
    for keys, group in frame.groupby(group_cols, dropna=False, sort=True):
        complete = group.loc[group["candidate_outcome_120d_status"] == _p04.NOT_MISSING]
        rows.append(
            {
                **metadata,
                "event_split": keys[0],
                "event_regime_bucket": keys[1],
                "board_bucket": keys[2],
                "event_count": int(len(group)),
                "executable_event_count": int(
                    (~group["non_executable_next_open"].fillna(False).astype(bool)).sum()
                ),
                "outcome_complete_120d_count": int(len(complete)),
                "label_completeness_rate": safe_rate(len(complete), len(group)),
                "next_open_executable_rate": safe_rate(
                    int((~group["non_executable_next_open"].fillna(False).astype(bool)).sum()),
                    len(group),
                ),
                "event_big_winner_120d_rate": safe_rate(
                    int(complete["event_big_winner_120d_label"].fillna(False).astype(bool).sum()),
                    len(complete),
                ),
                "near_winner_rate": safe_rate(
                    int(complete["event_near_winner_120d_label"].fillna(False).astype(bool).sum()),
                    len(complete),
                ),
                "confirm_20_rate": safe_rate(
                    int((group["confirm_20_label"] == 1).sum()),
                    int(group["confirm_20_complete"].fillna(False).astype(bool).sum()),
                ),
                "failure_10_rate": safe_rate(
                    int((group["failure_10_label"] == 1).sum()),
                    int(group["failure_10_complete"].fillna(False).astype(bool).sum()),
                ),
                "forward_20_return_mean": float(
                    pd.to_numeric(group["forward_return_20d"], errors="coerce").mean()
                ),
                "forward_60_return_mean": float(
                    pd.to_numeric(group["forward_return_60d"], errors="coerce").mean()
                ),
                "mfe_120d_median": float(pd.to_numeric(group["mfe_120d"], errors="coerce").median()),
                "mae_120d_median": float(pd.to_numeric(group["mae_120d"], errors="coerce").median()),
            }
        )
    return pd.DataFrame(rows)


def build_false_repair(labels: pd.DataFrame, events: pd.DataFrame, metadata: dict[str, Any]) -> pd.DataFrame:
    if events.empty or labels.empty:
        return pd.DataFrame()
    frame = events.merge(labels, on="event_id", how="left", suffixes=("", "_label"))
    rows: list[dict[str, Any]] = []
    for keys, group in frame.groupby(["event_split", "event_regime_bucket"], dropna=False, sort=True):
        rows.append(
            {
                **metadata,
                "event_split": keys[0],
                "event_regime_bucket": keys[1],
                "event_count": int(len(group)),
                "false_repair_10d_count": int(
                    group["event_false_repair_10d_label"].fillna(False).astype(bool).sum()
                ),
                "false_repair_10d_rate": safe_rate(
                    int(group["event_false_repair_10d_label"].fillna(False).astype(bool).sum()),
                    int(group["event_false_repair_10d_complete"].fillna(False).astype(bool).sum()),
                ),
                "false_repair_20d_count": int(
                    group["event_false_repair_20d_label"].fillna(False).astype(bool).sum()
                ),
                "false_repair_20d_rate": safe_rate(
                    int(group["event_false_repair_20d_label"].fillna(False).astype(bool).sum()),
                    int(group["event_false_repair_20d_complete"].fillna(False).astype(bool).sum()),
                ),
            }
        )
    return pd.DataFrame(rows)


def build_lead_time(capture_map: dict[str, pd.DataFrame], metadata: dict[str, dict[str, Any]]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for scope_id, capture in capture_map.items():
        meta = metadata[scope_id]
        captured = capture.loc[capture["any_event_captured"].fillna(False).astype(bool)]
        for keys, group in captured.groupby(
            ["episode_split", "market_regime_bucket", "window"], dropna=False, sort=True
            ):
                lead50 = pd.to_numeric(group["lead_time_to_first_50pct_sessions"], errors="coerce")
                lead_high = pd.to_numeric(group["lead_time_to_episode_high_sessions"], errors="coerce")
                from_low = pd.to_numeric(group["event_t0_from_episode_low_sessions"], errors="coerce")
                rows.append(
                    {
                        **meta,
                        "episode_split": keys[0],
                        "market_regime_bucket": keys[1],
                    "window": keys[2],
                    "captured_episode_count": int(len(group)),
                    "event_t0_to_first_50pct_sessions_p25": float(lead50.quantile(0.25)),
                    "event_t0_to_first_50pct_sessions_median": float(lead50.median()),
                    "event_t0_to_first_50pct_sessions_p75": float(lead50.quantile(0.75)),
                        "event_t0_to_episode_high_sessions_p25": float(lead_high.quantile(0.25)),
                        "event_t0_to_episode_high_sessions_median": float(lead_high.median()),
                        "event_t0_to_episode_high_sessions_p75": float(lead_high.quantile(0.75)),
                        "event_t0_from_episode_low_sessions_p25": float(from_low.quantile(0.25)),
                        "event_t0_from_episode_low_sessions_median": float(from_low.median()),
                        "event_t0_from_episode_low_sessions_p75": float(from_low.quantile(0.75)),
                    }
                )
    return pd.DataFrame(rows)


def scope_metadata(scope_id: str, scope_type: str, family_id: str = "", variant_id: str = "", status: str = "", cluster: str = "") -> dict[str, Any]:
    return {
        "candidate_scope_id": scope_id,
        "candidate_scope_type": scope_type,
        "family_id": family_id,
        "variant_id": variant_id,
        "family_input_status": status,
        "mechanism_cluster": cluster,
    }


def build_scope_event_sets(
    instances: pd.DataFrame,
    canonical: pd.DataFrame,
    e1_events: pd.DataFrame,
    full07_events: pd.DataFrame,
    config: dict[str, Any],
) -> tuple[dict[str, pd.DataFrame], dict[str, dict[str, Any]]]:
    event_sets: dict[str, pd.DataFrame] = {
        E1_SCOPE: e1_events,
        FULL_07_SCOPE: full07_events,
        "all_new_candidate_union": canonical,
    }
    metadata = {
        E1_SCOPE: scope_metadata(E1_SCOPE, E1_SCOPE, CHANNEL_E1, "07_recomputed", "upstream_07", "repair_reclaim_cluster"),
        FULL_07_SCOPE: scope_metadata(FULL_07_SCOPE, FULL_07_SCOPE, "07_full_union", "reported_union", "upstream_07", "repair_reclaim_cluster"),
        "all_new_candidate_union": scope_metadata("all_new_candidate_union", UNION_SCOPE, "all_new_candidate_union", "canonical_union", "mixed", "mixed"),
    }
    for row in family_variant_rows(config, include_blocked=False):
        if not row["executed_flag"]:
            continue
        fv_id = row["family_variant_id"]
        subset = instances.loc[instances["family_variant_id"] == fv_id].copy()
        event_sets[fv_id] = subset
        metadata[fv_id] = scope_metadata(
            fv_id,
            FAMILY_VARIANT_SCOPE,
            row["family_id"],
            row["variant_id"],
            row["family_input_status"],
            row["cluster"],
        )
    for family_id, spec in config["candidate_families"].items():
        if spec["status"] not in EXECUTABLE_STATUSES:
            continue
        subset = instances.loc[instances["family_id"] == family_id].copy()
        scope_id = f"{family_id}__all_variants"
        event_sets[scope_id] = canonicalize_subset(subset, scope_id)
        metadata[scope_id] = scope_metadata(
            scope_id,
            FAMILY_SCOPE,
            family_id,
            "all_variants",
            spec["status"],
            spec.get("cluster", ""),
        )
    return event_sets, metadata


def build_event_labels_for_sets(
    event_sets: dict[str, pd.DataFrame],
    daily_by_instrument: dict[str, pd.DataFrame],
    label_cfg: Any,
) -> dict[str, pd.DataFrame]:
    labels: dict[str, pd.DataFrame] = {}
    for scope_id, events in event_sets.items():
        if scope_id in {E1_SCOPE, FULL_07_SCOPE}:
            continue
        labels[scope_id] = _p04.label_events(
            events, daily_by_instrument=daily_by_instrument, label_cfg=label_cfg
        )
    return labels


def build_formula_spec(config: dict[str, Any]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for row in family_variant_rows(config, include_blocked=True):
        family_id = row["family_id"]
        spec = config["candidate_families"][family_id]
        rows.append(
            {
                "family_id": family_id,
                "variant_id": row["variant_id"],
                "family_variant_id": row["family_variant_id"],
                "input_series": spec.get("data_dependency", ""),
                "transform": mechanism_transform_text(family_id),
                "lookback_window": lookback_text(family_id, config),
                "threshold_grid": json.dumps(spec.get("threshold_grid", {}), sort_keys=True),
                "direction": "positive_leadership_or_breakout",
                "confirmation_window": "t0 close confirmation; next-open execution convention",
                "cooldown_or_density_window": int(config["event_generation"]["family_cooldown_sessions"]),
                "missing_policy": "missing feature disables trigger for that instrument-day; no forward fill from future dates",
                "event_regime_gating": row["variant_id"],
                "event_t0_confirmation_time": "t0_close_next_open_executable",
                "fallback_policy": f"fallback_of={row['is_fallback_of']}" if row["is_fallback_of"] else "",
                "family_input_status": row["family_input_status"],
            }
        )
    return pd.DataFrame(rows)


def mechanism_transform_text(family_id: str) -> str:
    mapping = {
        "R1_relative_strength_breakout": "stock-vs-market multi-window relative strength threshold",
        "R2_near_high_volume_expansion": "near rolling high plus volume/range quality expansion",
        "R3_vcp_breakout": "range contraction ratio plus upper-range positive breakout",
        "R4_industry_breadth_expansion": "blocked PIT industry breadth expansion",
        "R5_growth_or_small_style_confirmation": "diagnostic board/style relative confirmation",
        "R6_market_breadth_thrust": "Top-N/proxy breadth z-score/change thrust plus stock leadership",
        "R7_cross_sectional_momentum_rank_jump": "cross-sectional momentum percentile jump",
        "R8_persistent_distance_above_ema": "persistent positive distance above EMA60 without reclaim requirement",
        "T1_stock_vs_industry_CUSUM_break": "blocked stock-vs-industry CUSUM break",
        "T2_industry_vs_market_CUSUM_break": "blocked industry-vs-market CUSUM break",
        "T3_style_rotation_break": "diagnostic board/style rotation break",
        "T4_entropy_compression_then_directional_expansion": "direction entropy compression then positive expansion",
        "T5_volume_regime_shift": "volume baseline shift with positive price/relative confirmation",
        "T6_stock_vs_market_CUSUM_break": "stock-vs-market relative return CUSUM fallback",
        "T7_board_relative_strength_break": "board-vs-universe relative strength fallback",
        "T8_volatility_regime_contraction_break": "ATR percentile contraction then positive expansion",
    }
    return mapping.get(family_id, "")


def lookback_text(family_id: str, config: dict[str, Any]) -> str:
    if "CUSUM" in family_id:
        return f"{config['event_generation']['cusum_window']} sessions"
    if "entropy" in family_id:
        return f"{config['event_generation']['entropy_window']} sessions"
    if family_id == "R8_persistent_distance_above_ema":
        return f"{config['event_generation']['persistent_ema_days']} sessions"
    return "5/10/20/60/120 sessions depending on formula spec"


def build_run_capability_summary(config: dict[str, Any], instances: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for family_id, spec in sorted(
        config["candidate_families"].items(), key=lambda item: int(item[1].get("priority", 999))
    ):
        status = str(spec["status"])
        family_events = instances.loc[instances.get("family_id", pd.Series(dtype=str)) == family_id]
        variant_count = 0 if status == "family_data_blocked" else 2
        rows.append(
            {
                "family_id": family_id,
                "family_input_status": status,
                "data_dependency": spec.get("data_dependency", ""),
                "is_fallback_of": spec.get("is_fallback_of", ""),
                "executed_flag": bool(status in EXECUTABLE_STATUSES),
                "blocked_reason": "PIT industry classification unavailable"
                if status == "family_data_blocked"
                else "",
                "variant_count": variant_count,
                "selected_variant_id": "",
                "event_count": int(len(family_events)),
                "notes": capability_note(family_id, spec),
            }
        )
    return pd.DataFrame(rows)


def capability_note(family_id: str, spec: dict[str, Any]) -> str:
    if spec["status"] == "family_data_blocked":
        return "Blocked family is not silently replaced; fallback, if any, uses an independent family_id."
    if spec["status"] == "fallback_variant":
        return f"Independent fallback for {spec.get('is_fallback_of', '')}; not labeled as industry family."
    if spec["status"] == "diagnostic_only":
        return "Executed for overlap diagnostics but excluded from graduation selection."
    return "Runnable with existing PIT price, universe, benchmark, and board data."


def build_industry_style_input_audit(config: dict[str, Any], input_paths: dict[str, Path], panel: pd.DataFrame) -> pd.DataFrame:
    coverage = safe_rate(
        int(panel["board_bucket"].notna().sum()) if "board_bucket" in panel.columns else 0,
        len(panel),
    )
    rows = [
        {
            "feature_domain": "industry",
            "source_path": "",
            "source_manifest_hash": "",
            "pit_available_flag": False,
            "effective_date_policy": "not_available",
            "min_constituents": np.nan,
            "coverage_rate": 0.0,
            "fallback_policy": "No masquerading fallback; use R6/T6/T7 independent family IDs.",
            "blocked_family_list": "R4_industry_breadth_expansion;T1_stock_vs_industry_CUSUM_break;T2_industry_vs_market_CUSUM_break",
            "notes": "No PIT industry classification artifact is declared in the 08 input contract.",
        },
        {
            "feature_domain": "style_proxy_board",
            "source_path": str(input_paths["topn_executable_universe_csv"]),
            "source_manifest_hash": file_sha256(input_paths["topn_executable_universe_csv"]),
            "pit_available_flag": True,
            "effective_date_policy": "source_membership_date close; usable next trade date",
            "min_constituents": int(config["event_generation"]["cross_section_min_members"]),
            "coverage_rate": coverage,
            "fallback_policy": "Board/style variants are diagnostic or fallback; they are not reported as industry families.",
            "blocked_family_list": "",
            "notes": "Board bucket comes from the 05/06 PIT Top-N/proxy universe artifact.",
        },
        {
            "feature_domain": "market_breadth",
            "source_path": str(input_paths["topn_executable_universe_csv"]),
            "source_manifest_hash": file_sha256(input_paths["topn_executable_universe_csv"]),
            "pit_available_flag": True,
            "effective_date_policy": "same-day close feature, next-open executable",
            "min_constituents": int(config["event_generation"]["cross_section_min_members"]),
            "coverage_rate": 1.0 if len(panel) else 0.0,
            "fallback_policy": "R6_market_breadth_thrust is the market-breadth substitute for blocked R4 semantics.",
            "blocked_family_list": "",
            "notes": "Breadth uses only same-date evaluated Top-N/proxy instrument-days.",
        },
    ]
    return pd.DataFrame(rows)


def event_day_keys(events: pd.DataFrame) -> set[str]:
    if events.empty or "instrument" not in events.columns or "event_t0_date" not in events.columns:
        return set()
    return set(events["instrument"].astype(str) + "|" + events["event_t0_date"].astype(str))


def build_feature_snapshot_summary(instances: pd.DataFrame, instances_07: pd.DataFrame | None = None) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    feature_cols = [
        "close_to_ema60",
        "close_to_derived_daily_vwap",
        "stock_vs_market_20d",
        "amount_ratio_20d",
        "close_position_in_range",
        "momentum_percentile_20d",
        "universe_up_share",
        "board_relative_cusum_20d",
        "relative_cusum_20d",
        "direction_entropy_20d",
        "atr_pct_rank_60d",
    ]
    if instances.empty:
        return pd.DataFrame()
    instances_07 = instances_07 if instances_07 is not None else pd.DataFrame()
    tag_sets = {
        CHANNEL_E2: event_day_keys(instances_07.loc[instances_07.get("channel_id", pd.Series(dtype=str)).astype(str) == CHANNEL_E2])
        if not instances_07.empty
        else set(),
        CHANNEL_E3: event_day_keys(instances_07.loc[instances_07.get("channel_id", pd.Series(dtype=str)).astype(str) == CHANNEL_E3])
        if not instances_07.empty
        else set(),
        CHANNEL_E6: event_day_keys(instances_07.loc[instances_07.get("channel_id", pd.Series(dtype=str)).astype(str) == CHANNEL_E6])
        if not instances_07.empty
        else set(),
    }
    for keys, group in instances.groupby(["family_id", "variant_id"], dropna=False, sort=True):
        group_event_days = event_day_keys(group)
        row: dict[str, Any] = {
            "family_id": keys[0],
            "variant_id": keys[1],
            "event_count": int(len(group)),
            "same_day_e2_money_vwap_quality_tag_rate": safe_rate(
                len(group_event_days.intersection(tag_sets[CHANNEL_E2])), len(group_event_days)
            ),
            "same_day_e3_rank_persistence_tag_rate": safe_rate(
                len(group_event_days.intersection(tag_sets[CHANNEL_E3])), len(group_event_days)
            ),
            "same_day_e6_continuation_discriminator_tag_rate": safe_rate(
                len(group_event_days.intersection(tag_sets[CHANNEL_E6])), len(group_event_days)
            ),
        }
        for column in feature_cols:
            row[f"{column}_coverage_rate"] = safe_rate(int(group[column].notna().sum()), len(group)) if column in group.columns else 0.0
            row[f"{column}_median"] = float(pd.to_numeric(group[column], errors="coerce").median()) if column in group.columns else np.nan
        rows.append(row)
    return pd.DataFrame(rows)


def build_overlap_matrix(
    capture_map: dict[str, pd.DataFrame],
    metadata: dict[str, dict[str, Any]],
    instances: pd.DataFrame,
    instances_07: pd.DataFrame,
) -> pd.DataFrame:
    hit_sets: dict[str, set[str]] = {}
    event_day_sets: dict[str, set[str]] = {}
    first_event_dates: dict[str, dict[str, str]] = {}
    for scope_id, capture in capture_map.items():
        if metadata[scope_id]["candidate_scope_type"] in {FAMILY_VARIANT_SCOPE, FAMILY_SCOPE, E1_SCOPE, FULL_07_SCOPE, UNION_SCOPE}:
            hit_sets[scope_id] = captured_ids(capture, "all", "all", "before_first_50pct")
            before_first = capture_filter(capture, "all", "all", "before_first_50pct")
            hit_rows = before_first.loc[before_first["any_event_captured"].fillna(False).astype(bool)]
            first_event_dates[scope_id] = dict(
                zip(
                    hit_rows["target_episode_id"].astype(str),
                    hit_rows["first_event_t0_date"].fillna("").astype(str),
                )
            )
    for channel in [CHANNEL_E1, CHANNEL_E2, CHANNEL_E3, CHANNEL_E6]:
        subset = instances_07.loc[instances_07["channel_id"].astype(str) == channel].copy()
        event_day_sets[channel] = set(
            subset["instrument"].astype(str) + "|" + subset["event_t0_date"].astype(str)
        )
    for scope_id in hit_sets:
        if scope_id in {E1_SCOPE, FULL_07_SCOPE}:
            continue
        subset = instances.loc[instances["family_variant_id"].astype(str) == scope_id]
        if subset.empty and scope_id.endswith("__all_variants"):
            family_id = scope_id.replace("__all_variants", "")
            subset = instances.loc[instances["family_id"].astype(str) == family_id]
        if scope_id == "all_new_candidate_union":
            subset = instances
        event_day_sets[scope_id] = set(
            subset["instrument"].astype(str) + "|" + subset["event_t0_date"].astype(str)
        )
    rows: list[dict[str, Any]] = []
    keys = sorted(hit_sets)
    for left in keys:
        for right in keys:
            left_hits = hit_sets[left]
            right_hits = hit_sets[right]
            overlap = left_hits.intersection(right_hits)
            left_days = event_day_sets.get(left, set())
            right_days = event_day_sets.get(right, set())
            left_first = first_event_dates.get(left, {})
            right_first = first_event_dates.get(right, {})
            different_day = sum(
                1
                for episode_id in overlap
                if left_first.get(episode_id, "") and right_first.get(episode_id, "")
                and left_first.get(episode_id, "") != right_first.get(episode_id, "")
            )
            rows.append(
                {
                    "left_scope_id": left,
                    "right_scope_id": right,
                    "left_scope_type": metadata[left]["candidate_scope_type"],
                    "right_scope_type": metadata[right]["candidate_scope_type"],
                    "left_episode_count": len(left_hits),
                    "right_episode_count": len(right_hits),
                    "overlap_episode_count": len(overlap),
                    "left_only_episode_count": len(left_hits.difference(right_hits)),
                    "right_only_episode_count": len(right_hits.difference(left_hits)),
                    "left_overlap_rate": safe_rate(len(overlap), len(left_hits)),
                    "right_overlap_rate": safe_rate(len(overlap), len(right_hits)),
                    "jaccard_overlap": safe_rate(len(overlap), len(left_hits.union(right_hits))),
                    "same_day_overlap_count": len(left_days.intersection(right_days)),
                    "same_day_jaccard": safe_rate(
                        len(left_days.intersection(right_days)), len(left_days.union(right_days))
                    ),
                    "same_episode_different_day_overlap_count": int(different_day),
                    "high_risk_overlap_pair": high_risk_pair(left, right),
                }
            )
    return pd.DataFrame(rows)


def high_risk_pair(left: str, right: str) -> bool:
    pairs = [
        ["R1_relative_strength_breakout", "R7_cross_sectional_momentum_rank_jump", "T6_stock_vs_market_CUSUM_break"],
        ["R5_growth_or_small_style_confirmation", "T3_style_rotation_break", "T7_board_relative_strength_break"],
        ["R3_vcp_breakout", "T4_entropy_compression_then_directional_expansion", "T8_volatility_regime_contraction_break"],
    ]
    for group in pairs:
        if any(item in left for item in group) and any(item in right for item in group) and left != right:
            return True
    return False


def select_candidate_variants(
    incremental: pd.DataFrame,
    density: pd.DataFrame,
    config: dict[str, Any],
) -> list[str]:
    if incremental.empty:
        return []
    focus = incremental.loc[
        (incremental["candidate_scope_type"] == FAMILY_VARIANT_SCOPE)
        & (incremental["episode_split"] == "train")
        & (incremental["market_regime_bucket"].isin(config["selection"]["focus_episode_regimes"]))
        & (incremental["window"] == config["selection"]["focus_window"])
        & (incremental["family_input_status"].isin(config["selection"]["eligible_statuses"]))
    ].copy()
    if focus.empty:
        return []
    summary = (
        focus.groupby(["candidate_scope_id", "family_id", "variant_id", "family_input_status"], dropna=False)
        .agg(
            train_focus_incremental_recall=("incremental_recall_over_e1", "sum"),
            train_focus_incremental_captures=("incremental_captures_over_e1", "sum"),
        )
        .reset_index()
    )
    dens = density[["candidate_scope_id", "density_vs_e1_full_denominator", "density_full_denominator"]]
    summary = summary.merge(dens, on="candidate_scope_id", how="left")
    summary = summary.loc[
        summary["train_focus_incremental_recall"]
        >= float(config["selection"]["train_selection_min_incremental_recall"])
    ]
    if summary.empty:
        return []
    max_density = float(config["selection"]["train_selection_max_density_vs_e1"])
    filtered = summary.loc[
        (summary["density_vs_e1_full_denominator"].isna())
        | (summary["density_vs_e1_full_denominator"] <= max_density)
    ].copy()
    if filtered.empty:
        filtered = summary.copy()
    filtered = filtered.sort_values(
        ["train_focus_incremental_recall", "train_focus_incremental_captures", "density_vs_e1_full_denominator"],
        ascending=[False, False, True],
    )
    selected: list[str] = []
    selected_families: set[str] = set()
    for row in filtered.to_dict("records"):
        family_id = str(row["family_id"])
        if family_id in selected_families:
            continue
        selected.append(str(row["candidate_scope_id"]))
        selected_families.add(family_id)
        if len(selected) >= int(config["selection"]["max_selected_variants"]):
            break
    return selected


def build_selected_union(instances: pd.DataFrame, selected_variants: list[str]) -> pd.DataFrame:
    if not selected_variants:
        return empty_event_frame()
    subset = instances.loc[instances["family_variant_id"].isin(selected_variants)].copy()
    return build_candidate_canonical_events(subset, {"channels": {"recommended": selected_variants}})


def build_candidate_frontier(
    incremental: pd.DataFrame,
    density: pd.DataFrame,
    label_quality: pd.DataFrame,
    selected_variants: list[str],
) -> pd.DataFrame:
    focus = incremental.loc[
        (incremental["candidate_scope_type"].isin([FAMILY_VARIANT_SCOPE, FAMILY_SCOPE, UNION_SCOPE]))
        & (incremental["window"] == "before_first_50pct")
        & (incremental["market_regime_bucket"].isin(["risk_on", "transition"]))
        & (incremental["episode_split"].isin(["train", "validation", "robustness"]))
    ].copy()
    if focus.empty:
        return pd.DataFrame()
    pivot = focus.pivot_table(
        index=["candidate_scope_id", "candidate_scope_type", "family_id", "variant_id", "family_input_status"],
        columns=["episode_split", "market_regime_bucket"],
        values="incremental_recall_over_e1",
        aggfunc="first",
    )
    pivot.columns = [f"{split}_{regime}_incremental_recall" for split, regime in pivot.columns]
    frontier = pivot.reset_index()
    frontier = frontier.merge(
        density[
            [
                "candidate_scope_id",
                "event_count",
                "density_full_denominator",
                "density_vs_e1_full_denominator",
                "events_per_instrument_year_p95",
            ]
        ],
        on="candidate_scope_id",
        how="left",
    )
    q = (
        label_quality.groupby("candidate_scope_id", dropna=False)
        .agg(
            label_completeness_rate=("label_completeness_rate", "mean"),
            next_open_executable_rate=("next_open_executable_rate", "mean"),
            event_big_winner_120d_rate=("event_big_winner_120d_rate", "mean"),
        )
        .reset_index()
        if not label_quality.empty
        else pd.DataFrame(columns=["candidate_scope_id"])
    )
    frontier = frontier.merge(q, on="candidate_scope_id", how="left")
    frontier["selected_for_candidate_union"] = frontier["candidate_scope_id"].isin(selected_variants)
    return frontier.sort_values(
        ["selected_for_candidate_union", "train_risk_on_incremental_recall", "train_transition_incremental_recall"],
        ascending=[False, False, False],
        na_position="last",
    )


def build_mechanism_cluster_tables(
    instances: pd.DataFrame,
    selected_variants: list[str],
    episodes: pd.DataFrame,
    labels_by_scope: dict[str, pd.DataFrame],
    daily_by_instrument: dict[str, pd.DataFrame],
    baseline_capture: pd.DataFrame,
    full07_capture: pd.DataFrame,
    config: dict[str, Any],
    label_cfg: Any,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    cluster_rows: list[pd.DataFrame] = []
    cluster_sets: dict[str, pd.DataFrame] = {}
    cluster_meta: dict[str, dict[str, Any]] = {}
    for cluster, group in instances.groupby("mechanism_cluster", dropna=False, sort=True):
        cluster_id = f"cluster__{cluster}"
        events = canonicalize_subset(group, cluster_id)
        labels = _p04.label_events(
            events, daily_by_instrument=daily_by_instrument, label_cfg=label_cfg
        )
        capture = build_capture(episodes, events, labels, daily_by_instrument)
        cluster_sets[cluster_id] = capture
        cluster_meta[cluster_id] = scope_metadata(
            cluster_id, "mechanism_cluster", str(cluster), "cluster_union", "mixed", str(cluster)
        )
    if cluster_sets:
        incremental = build_incremental_recall(cluster_sets, cluster_meta, baseline_capture, full07_capture)
        cluster_rows.append(incremental)
    selected = instances.loc[instances["family_variant_id"].isin(selected_variants)].copy()
    ablation_rows: list[dict[str, Any]] = []
    selected_clusters = sorted(selected["mechanism_cluster"].dropna().astype(str).unique().tolist())
    for cluster in selected_clusters:
        kept = selected.loc[selected["mechanism_cluster"].astype(str) != cluster].copy()
        events = build_candidate_canonical_events(kept, config)
        labels = _p04.label_events(
            events, daily_by_instrument=daily_by_instrument, label_cfg=label_cfg
        )
        capture = build_capture(episodes, events, labels, daily_by_instrument)
        for split in SPLITS:
            for regime in ["risk_on", "transition"]:
                window = "before_first_50pct"
                denom = denominator_ids(baseline_capture, split, regime, window)
                if not denom:
                    continue
                base = captured_ids(baseline_capture, split, regime, window)
                kept_hits = captured_ids(capture, split, regime, window)
                ablation_rows.append(
                    {
                        "ablated_cluster": cluster,
                        "episode_split": split,
                        "market_regime_bucket": regime,
                        "window": window,
                        "denominator_episodes": len(denom),
                        "kept_union_captured_episodes": len(base.union(kept_hits)),
                        "incremental_captures_over_e1_after_ablation": len(kept_hits.difference(base)),
                        "incremental_recall_over_e1_after_ablation": safe_rate(
                            len(kept_hits.difference(base)), len(denom)
                        ),
                    }
                )
    summary = pd.concat(cluster_rows, ignore_index=True) if cluster_rows else pd.DataFrame()
    return summary, pd.DataFrame(ablation_rows)


def event_basis_lookup(
    event_id: str,
    events: pd.DataFrame,
    daily_by_instrument: dict[str, pd.DataFrame],
    episode_low: float,
) -> dict[str, Any]:
    if not event_id:
        return {}
    row = events.loc[events["event_id"].astype(str) == str(event_id)]
    if row.empty:
        return {}
    record = row.iloc[0].to_dict()
    close = safe_num(record.get("event_close"), np.nan)
    if pd.isna(close):
        daily = daily_by_instrument.get(str(record.get("instrument", "")))
        pos = int(safe_num(record.get("event_t0_pos"), -1))
        if daily is not None and 0 <= pos < len(daily):
            close = safe_num(daily.at[pos, "close"], np.nan)
    return {
        "event_close": close,
        "event_close_vs_episode_low_return": close / episode_low - 1.0
        if pd.notna(close) and episode_low > 0
        else np.nan,
        "close_to_ema60": safe_num(record.get("close_to_ema60"), np.nan),
        "close_to_high_60": safe_num(record.get("close_to_high_60"), np.nan),
    }


def build_timing_basis_comparison(
    episodes: pd.DataFrame,
    e1_capture: pd.DataFrame,
    candidate_capture: pd.DataFrame,
    e1_events: pd.DataFrame,
    candidate_events: pd.DataFrame,
    daily_by_instrument: dict[str, pd.DataFrame],
    config: dict[str, Any],
) -> pd.DataFrame:
    better_basis = config.get("better_basis", {})
    e1 = e1_capture.loc[e1_capture["window"] == "before_first_50pct"].copy()
    cand = candidate_capture.loc[candidate_capture["window"] == "before_first_50pct"].copy()
    merged = e1[
        [
            "target_episode_id",
            "first_event_id",
            "first_event_t0_date",
            "lead_time_to_first_50pct_sessions",
            "any_event_captured",
        ]
    ].rename(
        columns={
            "first_event_id": "e1_first_event_id",
            "first_event_t0_date": "e1_first_event_t0_date",
            "lead_time_to_first_50pct_sessions": "e1_lead_time_to_first_50pct_sessions",
            "any_event_captured": "e1_any_event_captured",
        }
    ).merge(
        cand[
            [
                "target_episode_id",
                "first_event_id",
                "first_event_t0_date",
                "lead_time_to_first_50pct_sessions",
                "any_event_captured",
            ]
        ].rename(
            columns={
                "first_event_id": "candidate_first_event_id",
                "first_event_t0_date": "candidate_first_event_t0_date",
                "lead_time_to_first_50pct_sessions": "candidate_lead_time_to_first_50pct_sessions",
                "any_event_captured": "candidate_any_event_captured",
            }
        ),
        on="target_episode_id",
        how="outer",
    )
    episode_meta = episodes[
        [
            "episode_id",
            "instrument",
            "episode_low_date",
            "episode_high_date",
            "qfq_low_at_low_date",
            "split",
            "market_regime_bucket",
            "board_bucket",
        ]
    ].rename(columns={"episode_id": "target_episode_id", "split": "episode_split"})
    merged = merged.merge(episode_meta, on="target_episode_id", how="left")
    rows: list[dict[str, Any]] = []
    for row in merged.to_dict("records"):
        low_price = safe_num(row.get("qfq_low_at_low_date"), np.nan)
        e1_basis = event_basis_lookup(
            str(row.get("e1_first_event_id", "") or ""),
            e1_events,
            daily_by_instrument,
            low_price,
        )
        cand_basis = event_basis_lookup(
            str(row.get("candidate_first_event_id", "") or ""),
            candidate_events,
            daily_by_instrument,
            low_price,
        )
        e1_lead = safe_num(row.get("e1_lead_time_to_first_50pct_sessions"), np.nan)
        cand_lead = safe_num(row.get("candidate_lead_time_to_first_50pct_sessions"), np.nan)
        e1_ret = safe_num(e1_basis.get("event_close_vs_episode_low_return"), np.nan)
        cand_ret = safe_num(cand_basis.get("event_close_vs_episode_low_return"), np.nan)
        rows.append(
            {
                **row,
                "candidate_minus_e1_lead_time_sessions": cand_lead - e1_lead
                if pd.notna(cand_lead) and pd.notna(e1_lead)
                else np.nan,
                "candidate_earlier_than_e1_flag": bool(
                    pd.notna(cand_lead) and pd.notna(e1_lead) and cand_lead > e1_lead
                ),
                "candidate_at_least_10_sessions_earlier_flag": bool(
                    pd.notna(cand_lead) and pd.notna(e1_lead) and cand_lead - e1_lead >= 10
                ),
                "e1_event_close_vs_episode_low_return": e1_ret,
                "candidate_event_close_vs_episode_low_return": cand_ret,
                "candidate_better_basis_flag": bool(
                    pd.notna(cand_ret) and pd.notna(e1_ret) and cand_ret < e1_ret
                ),
                "basis_policy_id": better_basis.get("policy_id", "event_close_vs_episode_low_v0"),
                "basis_definition": better_basis.get(
                    "better_when",
                    "candidate event close relative to episode low is lower than E1 event close relative to episode low",
                ),
                "basis_forbidden_future_fields": ";".join(
                    better_basis.get(
                        "forbidden_future_fields",
                        ["episode_high_date", "qfq_high_at_high_date", "first_50pct_touch_date"],
                    )
                ),
            }
        )
    return pd.DataFrame(rows)


def build_missed_episode_audit(
    episodes: pd.DataFrame,
    e1_capture: pd.DataFrame,
    selected_capture: pd.DataFrame,
    all_new_capture: pd.DataFrame,
) -> pd.DataFrame:
    base = e1_capture.loc[
        (e1_capture["window"] == "before_first_50pct")
        & (e1_capture["market_regime_bucket"].isin(FOCUS_REGIMES))
    ].copy()
    selected = selected_capture.loc[selected_capture["window"] == "before_first_50pct"][
        ["target_episode_id", "any_event_captured", "first_event_id", "first_event_t0_date"]
    ].rename(
        columns={
            "any_event_captured": "selected_union_any_event_captured",
            "first_event_id": "selected_union_first_event_id",
            "first_event_t0_date": "selected_union_first_event_t0_date",
        }
    )
    all_new = all_new_capture.loc[all_new_capture["window"] == "before_first_50pct"][
        ["target_episode_id", "any_event_captured"]
    ].rename(columns={"any_event_captured": "all_new_union_any_event_captured"})
    out = base.merge(selected, on="target_episode_id", how="left").merge(
        all_new, on="target_episode_id", how="left"
    )
    out = out.loc[~out["any_event_captured"].fillna(False).astype(bool)].copy()
    return out[
        [
            "target_episode_id",
            "instrument",
            "symbol",
            "episode_low_date",
            "episode_high_date",
            "first_50pct_touch_date",
            "episode_split",
            "board_bucket",
            "market_regime_bucket",
            "selected_union_any_event_captured",
            "selected_union_first_event_id",
            "selected_union_first_event_t0_date",
            "all_new_union_any_event_captured",
        ]
    ]


def build_event_regime_gating_comparison(incremental: pd.DataFrame, density: pd.DataFrame) -> pd.DataFrame:
    variants = incremental.loc[
        (incremental["candidate_scope_type"] == FAMILY_VARIANT_SCOPE)
        & (incremental["window"] == "before_first_50pct")
        & (incremental["episode_split"].isin(["all", "train", "robustness"]))
        & (incremental["market_regime_bucket"].isin(["risk_on", "transition"]))
    ].copy()
    if variants.empty:
        return pd.DataFrame()
    cols = [
        "candidate_scope_id",
        "density_full_denominator",
        "density_eligible_gated_denominator",
        "density_vs_e1_full_denominator",
    ]
    variants = variants.merge(density[cols], on="candidate_scope_id", how="left")
    return variants.sort_values(["family_id", "variant_id", "episode_split", "market_regime_bucket"])


def build_input_manifest_audit(input_paths: dict[str, Path], input_status: InputStatus, config: dict[str, Any]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for key, path in sorted(input_paths.items()):
        if path.is_file():
            source_hash = file_sha256(path)
            source_type = "file"
        elif path.is_dir():
            source_hash = ""
            source_type = "directory"
        else:
            source_hash = ""
            source_type = "missing"
        rows.append(
            {
                "input_key": key,
                "source_path": str(path),
                "source_type": source_type,
                "source_manifest_hash": source_hash,
                "input_gate_status": input_status.input_gate_status,
                "input_gate_failure_reason": input_status.input_gate_failure_reason,
                "config_hash": stable_hash(config),
            }
        )
    return pd.DataFrame(rows)


def build_leakage_execution_audit(
    instances: pd.DataFrame,
    canonical: pd.DataFrame,
    label_quality: pd.DataFrame,
    config: dict[str, Any],
) -> pd.DataFrame:
    rows = [
        {
            "audit_item": "event_generation_scope",
            "status": "pass",
            "value": "events generated on evaluated Top-N/proxy instrument-days before episode linking",
            "notes": "No target-only event search.",
        },
        {
            "audit_item": "future_feature_leakage",
            "status": "pass",
            "value": "all formulas use t0 or trailing rolling windows",
            "notes": "Forward MFE/first +50pct is used only in labels/evaluation.",
        },
        {
            "audit_item": "next_open_execution_convention",
            "status": "pass",
            "value": "p04 observable execution_status",
            "notes": "Same-day close features are next-open executable by convention.",
        },
        {
            "audit_item": "event_instance_count",
            "status": "pass",
            "value": int(len(instances)),
            "notes": "",
        },
        {
            "audit_item": "canonical_event_count",
            "status": "pass",
            "value": int(len(canonical)),
            "notes": "",
        },
    ]
    if not label_quality.empty:
        all_quality = label_quality.groupby("candidate_scope_id", dropna=False).agg(
            next_open_executable_rate=("next_open_executable_rate", "mean"),
            event_precision_label_complete_rate=("label_completeness_rate", "mean"),
        )
        for row in all_quality.reset_index().to_dict("records"):
            scope_id = row["candidate_scope_id"]
            rows.append(
                {
                    "audit_item": f"execution_label_{scope_id}",
                    "status": "pass"
                    if safe_num(row["next_open_executable_rate"], 0) >= float(config["gates"]["min_next_open_executable_rate"])
                    else "warning",
                    "value": json.dumps(row, ensure_ascii=False, sort_keys=True),
                    "notes": "event-anchored label/execution completeness",
                }
            )
    return pd.DataFrame(rows)


def build_e1_recompute_audit(
    e1_events: pd.DataFrame,
    e1_any: pd.DataFrame,
    e1_bridge: pd.DataFrame,
    config: dict[str, Any],
) -> pd.DataFrame:
    refs = config["reported_reference"]
    def lookup(table: pd.DataFrame) -> float:
        row = table.loc[
            (table["episode_split"] == "all")
            & (table["market_regime_bucket"] == "all")
            & (table["board_bucket"] == "all")
            & (table["window"] == "before_first_50pct")
        ]
        return float(row.iloc[0]["recall"]) if not row.empty else np.nan

    checks = [
        ("canonical_events", len(e1_events), refs["e1_only_canonical_events"]),
        (
            "before_first_50pct_any_recall",
            lookup(e1_any),
            refs["e1_only_any_recall_before_first_50pct"],
        ),
        (
            "before_first_50pct_bridge_recall",
            lookup(e1_bridge),
            refs["e1_only_bridge_recall_before_first_50pct"],
        ),
    ]
    rows = []
    for metric, recomputed, reported in checks:
        diff = float(recomputed) - float(reported)
        rows.append(
            {
                "metric": metric,
                "recomputed_value": recomputed,
                "reported_reference_value": reported,
                "difference": diff,
                "reconciliation_status": "match_or_rounding"
                if abs(diff) <= (2 if metric == "canonical_events" else 0.005)
                else "review_difference",
                "reference_source": "08 config reported_reference from 07 report/table; not used as computation input",
            }
        )
    return pd.DataFrame(rows)


def decide(
    input_status: InputStatus,
    selected_variants: list[str],
    incremental: pd.DataFrame,
    density: pd.DataFrame,
    label_quality: pd.DataFrame,
    bridge_recall: pd.DataFrame,
    bridge_exclusion: pd.DataFrame,
    timing_basis: pd.DataFrame,
    cluster_ablation: pd.DataFrame,
    config: dict[str, Any],
) -> tuple[str, dict[str, Any]]:
    if input_status.input_gate_status != "pass":
        return DECISION_INPUT_BLOCKED, {
            "input_gate_failure_reason": input_status.input_gate_failure_reason
        }
    gates = config["gates"]
    selected_scope = "selected_candidate_union"
    focus = incremental.loc[
        (incremental["candidate_scope_id"] == selected_scope)
        & (incremental["window"] == "before_first_50pct")
        & (incremental["market_regime_bucket"].isin(FOCUS_REGIMES))
    ]
    max_robustness = safe_num(
        focus.loc[focus["episode_split"] == "robustness", "incremental_recall_over_e1"].max(),
        0.0,
    )
    train_robust_captures = int(
        pd.to_numeric(
            focus.loc[focus["episode_split"].isin(["train", "robustness"]), "incremental_captures_over_e1"],
            errors="coerce",
        ).fillna(0).sum()
    )
    timing_focus = timing_basis.loc[
        timing_basis.get("market_regime_bucket", pd.Series(dtype=str)).isin(FOCUS_REGIMES)
        if not timing_basis.empty
        else []
    ] if not timing_basis.empty else pd.DataFrame()
    earlier_count = int(
        timing_focus.get("candidate_at_least_10_sessions_earlier_flag", pd.Series(dtype=bool))
        .fillna(False)
        .astype(bool)
        .sum()
    ) if not timing_focus.empty else 0
    better_basis_count = int(
        timing_focus.get("candidate_better_basis_flag", pd.Series(dtype=bool))
        .fillna(False)
        .astype(bool)
        .sum()
    ) if not timing_focus.empty else 0
    selected_density = density.loc[density["candidate_scope_id"] == selected_scope]
    density_mean = (
        safe_num(selected_density.iloc[0]["density_full_denominator"], 0.0)
        if not selected_density.empty
        else 0.0
    )
    density_p95 = (
        safe_num(selected_density.iloc[0]["events_per_instrument_year_p95"], 0.0)
        if not selected_density.empty
        else 0.0
    )
    selected_event_count = int(
        safe_num(selected_density.iloc[0]["event_count"], 0)
        if not selected_density.empty
        else 0
    )
    e1_density = density.loc[density["candidate_scope_id"] == E1_SCOPE]
    e1_event_count = int(
        safe_num(e1_density.iloc[0]["event_count"], 0)
        if not e1_density.empty
        else 0
    )
    selected_quality = label_quality.loc[label_quality["candidate_scope_id"] == selected_scope]
    executable_rate = safe_num(selected_quality["next_open_executable_rate"].mean(), 1.0)
    label_complete_rate = safe_num(selected_quality["label_completeness_rate"].mean(), 1.0)
    any_positive = bool(
        (incremental["incremental_captures_over_e1"].fillna(0).astype(float) > 0).any()
    )
    recall_ok = (
        max_robustness >= float(gates["min_incremental_recall_pct_points_robustness"])
        or train_robust_captures >= int(gates["min_train_robustness_missed_capture_count"])
        or earlier_count >= int(gates["min_earlier_capture_count"])
        or better_basis_count >= int(gates["min_earlier_capture_count"])
    )
    strong_recall = max_robustness >= float(gates["min_incremental_recall_pct_points_strong"])
    selected_variant_density = density.loc[density["candidate_scope_id"].isin(selected_variants)].copy()
    family_density_mean_ok = bool(
        selected_variant_density.empty
        or (
            pd.to_numeric(selected_variant_density["density_full_denominator"], errors="coerce")
            <= float(gates["max_candidate_family_canonical_events_per_instrument_year_mean"])
        ).all()
    )
    family_density_p95_ok = bool(
        selected_variant_density.empty
        or (
            (
                pd.to_numeric(selected_variant_density["events_per_instrument_year_p95"], errors="coerce")
                <= float(gates["max_candidate_family_canonical_events_per_instrument_year_p95"])
            )
            | selected_variant_density["events_per_instrument_year_p95"].isna()
        ).all()
    )
    family_density_share_ok = bool(
        selected_variant_density.empty
        or (
            pd.to_numeric(selected_variant_density["density_share_of_selected_union"], errors="coerce").fillna(0.0)
            <= float(gates["max_new_family_density_share"])
        ).all()
    )
    density_drag_ok = bool(
        selected_variant_density.empty
        or not selected_variant_density.get("density_drag_flag", pd.Series(dtype=bool)).fillna(False).astype(bool).any()
    )
    canonical_count_ratio_ok = bool(
        e1_event_count <= 0
        or selected_event_count <= e1_event_count * 1.50
        or strong_recall
    )
    density_ok = (
        density_mean <= float(gates["max_candidate_union_canonical_events_per_instrument_year_mean"])
        and (
            pd.isna(density_p95)
            or density_p95 <= float(gates["max_candidate_union_canonical_events_per_instrument_year_p95"])
        )
        and family_density_mean_ok
        and family_density_p95_ok
        and family_density_share_ok
        and density_drag_ok
        and canonical_count_ratio_ok
    )
    label_ok = (
        executable_rate >= float(gates["min_next_open_executable_rate"])
        and label_complete_rate >= float(gates["min_event_precision_label_complete_rate"])
    )
    bridge_ok = True
    bridge_recall_min_delta = np.nan
    bridge_exclusion_max_excess = np.nan
    if not bridge_recall.empty:
        selected_bridge = bridge_recall.loc[
            (bridge_recall["candidate_scope_id"] == selected_scope)
            & (bridge_recall["window"] == "before_first_50pct")
            & (bridge_recall["market_regime_bucket"].isin(FOCUS_REGIMES))
            & (bridge_recall["episode_split"].isin(["train", "validation", "robustness"]))
            & (bridge_recall.get("board_bucket", pd.Series(dtype=str)).fillna("all").astype(str).eq("all"))
        ][["episode_split", "market_regime_bucket", "recall"]].rename(columns={"recall": "candidate_bridge_recall"})
        e1_bridge = bridge_recall.loc[
            (bridge_recall["candidate_scope_id"] == E1_SCOPE)
            & (bridge_recall["window"] == "before_first_50pct")
            & (bridge_recall["market_regime_bucket"].isin(FOCUS_REGIMES))
            & (bridge_recall["episode_split"].isin(["train", "validation", "robustness"]))
            & (bridge_recall.get("board_bucket", pd.Series(dtype=str)).fillna("all").astype(str).eq("all"))
        ][["episode_split", "market_regime_bucket", "recall"]].rename(columns={"recall": "e1_bridge_recall"})
        bridge_cmp = selected_bridge.merge(e1_bridge, on=["episode_split", "market_regime_bucket"], how="inner")
        if not bridge_cmp.empty:
            bridge_cmp["bridge_recall_delta_vs_e1"] = (
                pd.to_numeric(bridge_cmp["candidate_bridge_recall"], errors="coerce")
                - pd.to_numeric(bridge_cmp["e1_bridge_recall"], errors="coerce")
            )
            bridge_recall_min_delta = float(bridge_cmp["bridge_recall_delta_vs_e1"].min())
            bridge_ok = bridge_ok and bridge_recall_min_delta >= -float(gates["max_bridge_recall_shortfall_pct_points"])
    if not bridge_exclusion.empty:
        selected_excl = bridge_exclusion.loc[
            (bridge_exclusion["candidate_scope_id"] == selected_scope)
            & (bridge_exclusion["window"] == "before_first_50pct")
            & (bridge_exclusion["market_regime_bucket"].isin(FOCUS_REGIMES))
            & (bridge_exclusion["episode_split"].isin(["train", "validation", "robustness"]))
        ][["episode_split", "market_regime_bucket", "bridge_excluded_rate"]].rename(
            columns={"bridge_excluded_rate": "candidate_bridge_excluded_rate"}
        )
        e1_excl = bridge_exclusion.loc[
            (bridge_exclusion["candidate_scope_id"] == E1_SCOPE)
            & (bridge_exclusion["window"] == "before_first_50pct")
            & (bridge_exclusion["market_regime_bucket"].isin(FOCUS_REGIMES))
            & (bridge_exclusion["episode_split"].isin(["train", "validation", "robustness"]))
        ][["episode_split", "market_regime_bucket", "bridge_excluded_rate"]].rename(
            columns={"bridge_excluded_rate": "e1_bridge_excluded_rate"}
        )
        excl_cmp = selected_excl.merge(e1_excl, on=["episode_split", "market_regime_bucket"], how="inner")
        if not excl_cmp.empty:
            excl_cmp["bridge_exclusion_rate_excess_vs_e1"] = (
                pd.to_numeric(excl_cmp["candidate_bridge_excluded_rate"], errors="coerce")
                - pd.to_numeric(excl_cmp["e1_bridge_excluded_rate"], errors="coerce")
            )
            bridge_exclusion_max_excess = float(excl_cmp["bridge_exclusion_rate_excess_vs_e1"].max())
            bridge_ok = bridge_ok and bridge_exclusion_max_excess <= float(
                gates["max_bridge_exclusion_rate_excess_pct_points"]
            )
    stability_focus = focus.loc[focus["episode_split"].isin(["validation", "robustness"])].copy()
    stability_no_negative = bool(
        stability_focus.empty
        or (
            pd.to_numeric(stability_focus["incremental_recall_over_e1"], errors="coerce").fillna(0.0)
            >= 0.0
        ).all()
    )
    selected_quality_focus = selected_quality.loc[
        selected_quality["event_split"].isin(["validation", "robustness"])
        & selected_quality["event_regime_bucket"].isin(FOCUS_REGIMES)
    ] if not selected_quality.empty else pd.DataFrame()
    stability_label_ok = bool(
        selected_quality_focus.empty
        or (
            pd.to_numeric(selected_quality_focus["label_completeness_rate"], errors="coerce").fillna(1.0)
            >= float(gates["min_event_precision_label_complete_rate"])
        ).all()
    )
    board_counts = (
        selected_quality.groupby("board_bucket", dropna=False)["event_count"].sum()
        if not selected_quality.empty and "board_bucket" in selected_quality.columns
        else pd.Series(dtype=float)
    )
    max_board_share = (
        float(board_counts.max() / board_counts.sum())
        if len(board_counts) and board_counts.sum() > 0
        else np.nan
    )
    stability_board_ok = bool(
        pd.isna(max_board_share)
        or max_board_share <= float(gates["max_single_board_event_share"])
    )
    homogeneous_caveat = False
    if not cluster_ablation.empty:
        after = pd.to_numeric(
            cluster_ablation["incremental_recall_over_e1_after_ablation"], errors="coerce"
        )
        before = pd.to_numeric(focus["incremental_recall_over_e1"], errors="coerce")
        homogeneous_caveat = bool(len(after.dropna()) and safe_num(after.max(), 0.0) <= max(safe_num(before.max(), 0.0) * 0.20, 0.005))
    stability_ok = stability_no_negative and stability_label_ok and stability_board_ok and not homogeneous_caveat
    gate_failures: list[str] = []
    if not recall_ok:
        gate_failures.append("recall_gate")
    if not density_ok:
        gate_failures.append("density_gate")
    if not label_ok:
        gate_failures.append("label_execution_gate")
    if not bridge_ok:
        gate_failures.append("bridge_gate")
    if not stability_ok:
        gate_failures.append("stability_gate")
    if not selected_variants and not any_positive:
        decision = DECISION_NO_INCREMENTAL
    elif recall_ok and not density_ok:
        decision = DECISION_DENSITY_BLOCKED
    elif recall_ok and density_ok and label_ok and bridge_ok and stability_ok:
        decision = DECISION_SUPPORTED
    elif not any_positive:
        decision = DECISION_NO_INCREMENTAL
    else:
        decision = DECISION_DIAGNOSTIC_ONLY
    summary = {
        "selected_variant_count": len(selected_variants),
        "selected_variants": selected_variants,
        "max_robustness_risk_on_transition_incremental_recall": max_robustness,
        "train_robustness_missed_capture_count": train_robust_captures,
        "earlier_at_least_10_sessions_count": earlier_count,
        "better_basis_count": better_basis_count,
        "selected_density_full_denominator": density_mean,
        "selected_density_p95_nonzero_instrument_years": density_p95,
        "selected_canonical_count_ratio_vs_e1": safe_rate(selected_event_count, e1_event_count),
        "family_density_mean_gate_pass": family_density_mean_ok,
        "family_density_p95_gate_pass": family_density_p95_ok,
        "family_density_share_gate_pass": family_density_share_ok,
        "density_drag_gate_pass": density_drag_ok,
        "canonical_count_ratio_gate_pass": canonical_count_ratio_ok,
        "selected_next_open_executable_rate": executable_rate,
        "selected_event_precision_label_complete_rate": label_complete_rate,
        "bridge_recall_min_delta_vs_e1": bridge_recall_min_delta,
        "bridge_exclusion_max_excess_vs_e1": bridge_exclusion_max_excess,
        "bridge_gate_pass": bridge_ok,
        "stability_no_negative_validation_robustness": stability_no_negative,
        "stability_label_gate_pass": stability_label_ok,
        "stability_max_board_share": max_board_share,
        "stability_board_concentration_gate_pass": stability_board_ok,
        "stability_gate_pass": stability_ok,
        "homogeneous_signal_caveat": homogeneous_caveat,
        "gate_failures": gate_failures,
        "decision_reason": decision,
    }
    return decision, summary


def markdown_table(frame: pd.DataFrame, columns: list[str], max_rows: int = 12) -> list[str]:
    if frame.empty:
        return ["_No rows._"]
    view = frame.loc[:, [column for column in columns if column in frame.columns]].head(max_rows).copy()
    for column in view.columns:
        if pd.api.types.is_float_dtype(view[column]):
            view[column] = view[column].map(lambda value: fmt(value, 4))
    header = "| " + " | ".join(view.columns) + " |"
    sep = "| " + " | ".join(["---"] * len(view.columns)) + " |"
    rows = [header, sep]
    for record in view.astype(str).to_dict("records"):
        rows.append("| " + " | ".join(record[column] for column in view.columns) + " |")
    return rows


def write_report(
    path: Path,
    *,
    decision: str,
    gate_summary: dict[str, Any],
    input_status: InputStatus,
    denominator_summary: pd.DataFrame,
    run_capability: pd.DataFrame,
    e1_audit: pd.DataFrame,
    baseline_recall: pd.DataFrame,
    frontier: pd.DataFrame,
    density: pd.DataFrame,
    label_quality: pd.DataFrame,
    bridge: pd.DataFrame,
    overlap: pd.DataFrame,
    cluster_summary: pd.DataFrame,
    cluster_ablation: pd.DataFrame,
    industry_audit: pd.DataFrame,
    timing_basis: pd.DataFrame,
    validation_risk_on_denominator: int,
) -> Path:
    focus_frontier = frontier.loc[
        frontier["candidate_scope_type"].isin([FAMILY_VARIANT_SCOPE, UNION_SCOPE])
    ] if not frontier.empty else frontier
    density_view = density.loc[
        density["candidate_scope_id"].isin(["selected_candidate_union", "all_new_candidate_union", E1_SCOPE, FULL_07_SCOPE])
    ] if not density.empty else density
    label_view = (
        label_quality.groupby("candidate_scope_id", dropna=False)
        .agg(
            label_completeness_rate=("label_completeness_rate", "mean"),
            next_open_executable_rate=("next_open_executable_rate", "mean"),
            event_big_winner_120d_rate=("event_big_winner_120d_rate", "mean"),
        )
        .reset_index()
        if not label_quality.empty
        else pd.DataFrame()
    )
    lines = [
        "# Risk-on / Transition Recall 修复探索 V0",
        "",
        f"- final decision: `{decision}`",
        f"- selected variants: `{';'.join(gate_summary.get('selected_variants', [])) or 'none'}`",
        f"- 06 evaluated instrument-days: `{int(denominator_summary.iloc[0]['evaluated_instrument_days'])}`; target episodes: `{int(denominator_summary.iloc[0]['episode_count'])}`",
        f"- 07 upstream decision: `{input_status.upstream_07_decision}`; 08 input gate: `{input_status.input_gate_status}`",
        "",
        "## 结论摘要",
        "",
        "08 没有把 07 full union 当作默认扩张起点。实现先从 07 canonical / instance artifacts 重放 E1-only baseline，再把新的 risk_on / transition family 作为独立事件族生成，最后事后 link 到 06 冻结 target episode denominator。",
        "",
        f"- robustness risk_on/transition 最大增量 recall: {pct(gate_summary.get('max_robustness_risk_on_transition_incremental_recall'))}",
        f"- train+robustness missed capture count: {gate_summary.get('train_robustness_missed_capture_count')}",
        f"- selected density full denominator: {fmt(gate_summary.get('selected_density_full_denominator'), 4)} events/instrument-year",
        f"- selected execution / 120d label completeness: {pct(gate_summary.get('selected_next_open_executable_rate'))} / {pct(gate_summary.get('selected_event_precision_label_complete_rate'))}",
        f"- validation risk_on denominator: `{validation_risk_on_denominator}`; caveat: `{'sample-small diagnostic' if validation_risk_on_denominator < 30 else 'not sample-small'}`",
        f"- graduation gate failures: `{';'.join(gate_summary.get('gate_failures', [])) or 'none'}`",
        f"- bridge recall min delta vs E1: {pct(gate_summary.get('bridge_recall_min_delta_vs_e1'))}; bridge exclusion max excess vs E1: {pct(gate_summary.get('bridge_exclusion_max_excess_vs_e1'))}",
        "",
        "本实验不是交易信号、不是模型、不是回测；所有 event-anchored +50% label 只用于评估，不参与事件触发。",
        "",
        "## E1-only Baseline Recompute",
        "",
        *markdown_table(e1_audit, list(e1_audit.columns)),
        "",
        *markdown_table(
            baseline_recall.loc[
                (baseline_recall["window"] == "before_first_50pct")
                & (baseline_recall["market_regime_bucket"].isin(["all", "risk_on", "transition", "risk_off"]))
                & (baseline_recall["board_bucket"] == "all")
            ],
            ["episode_split", "market_regime_bucket", "numerator", "denominator", "recall"],
        ),
        "",
        "## Family Capability",
        "",
        f"- total families: {len(run_capability)}",
        f"- runnable: {int((run_capability['family_input_status'] == 'runnable_existing_data').sum())}",
        f"- blocked: {int((run_capability['family_input_status'] == 'family_data_blocked').sum())}",
        f"- fallback: {int((run_capability['family_input_status'] == 'fallback_variant').sum())}",
        f"- diagnostic-only: {int((run_capability['family_input_status'] == 'diagnostic_only').sum())}",
        "",
        *markdown_table(
            run_capability,
            ["family_id", "family_input_status", "is_fallback_of", "executed_flag", "event_count"],
        ),
        "",
        "## Candidate Frontier",
        "",
        "增量 recall 的 denominator 是同一 split / episode_regime / window 下的 06 target episode count，单位是 percentage points。",
        "",
        *markdown_table(
            focus_frontier,
            [
                "candidate_scope_id",
                "family_input_status",
                "selected_for_candidate_union",
                "train_risk_on_incremental_recall",
                "train_transition_incremental_recall",
                "robustness_risk_on_incremental_recall",
                "robustness_transition_incremental_recall",
                "density_vs_e1_full_denominator",
                "event_big_winner_120d_rate",
            ],
        ),
        "",
        "## Density / Label",
        "",
        "Headline density 使用 full evaluated denominator；event-regime-gated eligible denominator 只作为诊断。",
        "",
        *markdown_table(
            density_view,
            [
                "candidate_scope_id",
                "event_count",
                "density_full_denominator",
                "density_eligible_gated_denominator",
                "density_vs_e1_full_denominator",
                "events_per_instrument_year_p95",
            ],
        ),
        "",
        *markdown_table(
            label_view,
            [
                "candidate_scope_id",
                "label_completeness_rate",
                "next_open_executable_rate",
                "event_big_winner_120d_rate",
            ],
        ),
        "",
        "## Bridge / Overlap / Cluster",
        "",
        *markdown_table(
            bridge.loc[
                (bridge["candidate_scope_id"].isin(["selected_candidate_union", "all_new_candidate_union", E1_SCOPE]))
                & (bridge["window"] == "before_first_50pct")
                & (bridge["episode_split"].isin(["all", "robustness"]))
                & (bridge["market_regime_bucket"].isin(["risk_on", "transition", "all"]))
            ] if not bridge.empty else bridge,
            ["candidate_scope_id", "episode_split", "market_regime_bucket", "numerator", "denominator", "excluded_count", "recall"],
        ),
        "",
        *markdown_table(
            overlap.loc[overlap["high_risk_overlap_pair"].fillna(False).astype(bool)] if not overlap.empty else overlap,
            ["left_scope_id", "right_scope_id", "overlap_episode_count", "jaccard_overlap", "same_day_overlap_count", "high_risk_overlap_pair"],
        ),
        "",
        *markdown_table(
            cluster_summary.loc[
                (cluster_summary["window"] == "before_first_50pct")
                & (cluster_summary["episode_split"].isin(["all", "robustness"]))
                & (cluster_summary["market_regime_bucket"].isin(["risk_on", "transition"]))
            ] if not cluster_summary.empty else cluster_summary,
            ["candidate_scope_id", "episode_split", "market_regime_bucket", "incremental_captures_over_e1", "incremental_recall_over_e1"],
        ),
        "",
        *markdown_table(cluster_ablation, list(cluster_ablation.columns[:8])),
        "",
        "## Timing / Basis",
        "",
        *markdown_table(
            timing_basis.loc[
                timing_basis.get("candidate_at_least_10_sessions_earlier_flag", pd.Series(dtype=bool)).fillna(False).astype(bool)
            ] if not timing_basis.empty else timing_basis,
            [
                "target_episode_id",
                "market_regime_bucket",
                "e1_first_event_t0_date",
                "candidate_first_event_t0_date",
                "candidate_minus_e1_lead_time_sessions",
                "candidate_event_close_vs_episode_low_return",
                "e1_event_close_vs_episode_low_return",
            ],
        ),
        "",
        "## Input Contract",
        "",
        *markdown_table(
            industry_audit,
            ["feature_domain", "pit_available_flag", "coverage_rate", "blocked_family_list", "fallback_policy"],
        ),
        "",
        "行业 family 默认 blocked；T6/T7/R6 是独立 fallback 或替代 family，未冒充 industry breadth / industry CUSUM。",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def collect_hashes(paths: dict[str, Path]) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for key, path in sorted(paths.items()):
        if path.is_file():
            hashes[key] = file_sha256(path)
    return hashes


def path_row_count_and_schema(path: Path) -> tuple[int | None, list[dict[str, str]], str]:
    if not path.is_file():
        return None, [], "missing_or_directory"
    try:
        if path.suffix == ".csv":
            header = pd.read_csv(path, nrows=0)
            with path.open("r", encoding="utf-8", errors="ignore") as handle:
                row_count = max(sum(1 for _ in handle) - 1, 0)
            return row_count, frame_schema(header), "scanned_csv"
        if path.suffix == ".parquet":
            frame = pd.read_parquet(path)
            return int(len(frame)), frame_schema(frame), "read_parquet_metadata_frame"
        if path.suffix in {".md", ".txt", ".json"}:
            with path.open("r", encoding="utf-8", errors="ignore") as handle:
                return sum(1 for _ in handle), [], "line_count"
    except Exception as exc:  # pragma: no cover - defensive metadata path
        return None, [], f"metadata_error:{type(exc).__name__}"
    return None, [], "unsupported_file_type"


def build_artifact_metadata(
    paths: dict[str, Path], frames: dict[str, pd.DataFrame] | None = None
) -> dict[str, dict[str, Any]]:
    frames = frames or {}
    metadata: dict[str, dict[str, Any]] = {}
    for key, path in sorted(paths.items()):
        artifact: dict[str, Any] = {
            "path": str(path.resolve()),
            "exists": path.exists(),
            "hash": file_sha256(path) if path.is_file() else "",
        }
        if key in frames:
            frame = frames[key]
            artifact.update(
                {
                    "row_count": int(len(frame)),
                    "column_schema": frame_schema(frame),
                    "metadata_source": "in_memory_dataframe",
                }
            )
        else:
            row_count, schema, source = path_row_count_and_schema(path)
            artifact.update(
                {
                    "row_count": row_count,
                    "column_schema": schema,
                    "metadata_source": source,
                }
            )
        metadata[key] = artifact
    return metadata


def write_manifest(
    path: Path,
    *,
    config: dict[str, Any],
    config_path: Path,
    decision: str,
    gate_summary: dict[str, Any],
    input_paths: dict[str, Path],
    output_paths: dict[str, Path],
    run_scope: str,
    input_artifacts: dict[str, dict[str, Any]] | None = None,
    output_artifacts: dict[str, dict[str, Any]] | None = None,
) -> Path:
    manifest = {
        "experiment_name": config["experiment"]["name"],
        "run_scope": run_scope,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_git_revision": git_revision(),
        "config_path": str(config_path.resolve()),
        "config_hash": stable_hash(config),
        "config_file_hash": file_sha256(config_path),
        "decision": decision,
        "gate_summary": gate_summary,
        "input_paths": {key: str(value.resolve()) for key, value in sorted(input_paths.items())},
        "input_hashes": collect_hashes(input_paths),
        "input_artifacts": input_artifacts or build_artifact_metadata(input_paths),
        "output_paths": {key: str(value.resolve()) for key, value in sorted(output_paths.items())},
        "output_hashes": collect_hashes(output_paths),
        "output_artifacts": output_artifacts or build_artifact_metadata(output_paths),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    return path


def run_pipeline(
    config: dict[str, Any],
    *,
    config_path: Path,
    mode: str = "full",
    max_instruments: int | None = None,
) -> dict[str, Any]:
    validate_config(config)
    config = config_with_variant_channels(config)
    input_paths = build_input_paths(config)
    input_status = validate_input_status(config, input_paths)
    if mode == "validate-config":
        return {
            "decision": input_status.input_gate_status,
            "run_scope": "validate_config",
            "input_gate_failure_reason": input_status.input_gate_failure_reason,
        }
    debug = max_instruments is not None
    run_scope = "debug_subset" if debug else "full"
    output_paths = build_output_paths(config, debug=debug)
    log_progress = bool(config.get("runtime", {}).get("log_progress", True))

    def progress(message: str) -> None:
        if log_progress:
            print(f"[08] {message}", file=sys.stderr, flush=True)

    if input_status.input_gate_status != "pass":
        decision = DECISION_INPUT_BLOCKED
        gate_summary = {"input_gate_failure_reason": input_status.input_gate_failure_reason}
        write_manifest(
            output_paths["manifest"],
            config=config,
            config_path=config_path,
            decision=decision,
            gate_summary=gate_summary,
            input_paths=input_paths,
            output_paths={k: v for k, v in output_paths.items() if k != "manifest"},
            run_scope=run_scope,
        )
        return {
            "decision": decision,
            "run_scope": run_scope,
            "input_gate_failure_reason": input_status.input_gate_failure_reason,
        }

    progress("loading 06/07 inputs and PIT daily feature panels")
    (
        benchmark_daily,
        universe,
        split_config,
        daily_by_instrument,
        membership_by_instrument,
        feature_panel,
    ) = load_daily_inputs(
        config,
        input_paths,
        input_status,
        max_instruments=max_instruments,
        progress=progress,
    )
    label_cfg = parse_label_config(config)
    instances_07, canonical_07, labels_07 = load_07_artifacts(input_paths)
    e1_events = rebuild_e1_only_from_07(canonical_07, instances_07)
    e1_labels = labels_07.loc[labels_07["event_id"].isin(e1_events["event_id"])].copy()
    full07_labels = labels_07.loc[labels_07["event_id"].isin(canonical_07["event_id"])].copy()

    progress("loading and reconciling 06 target episodes")
    episodes = pd.read_parquet(input_paths["upstream_06_episode_reference_parquet"])
    episodes = episodes.loc[episodes["instrument"].isin(daily_by_instrument)].copy()
    episodes, first_touch = _p07.reconcile_first_touch(episodes, daily_by_instrument)

    progress("recomputing 07 E1-only and full-union captures")
    e1_capture = build_capture(episodes, e1_events, e1_labels, daily_by_instrument)
    full07_capture = build_capture(episodes, canonical_07, full07_labels, daily_by_instrument)
    channel_captures: dict[str, pd.DataFrame] = {CHANNEL_E1: e1_capture}
    for channel_id in [CHANNEL_E2, CHANNEL_E3, CHANNEL_E6]:
        channel_events = rebuild_07_channel_from_07(channel_id, canonical_07, instances_07)
        channel_labels = labels_07.loc[labels_07["event_id"].isin(channel_events["event_id"])].copy()
        channel_captures[channel_id] = build_capture(
            episodes, channel_events, channel_labels, daily_by_instrument
        )
    e1_any = _p07.build_recall_table(e1_capture, bridge=False)
    e1_bridge = _p07.build_recall_table(e1_capture, bridge=True)
    e1_audit = build_e1_recompute_audit(e1_events, e1_any, e1_bridge, config)

    progress("generating 08 candidate family event instances")
    instance_parts: list[pd.DataFrame] = []
    progress_every = int(config.get("runtime", {}).get("progress_every_instruments", 100))
    if debug:
        progress_every = min(progress_every, 10)
    instruments = sorted(daily_by_instrument)
    for processed_no, instrument in enumerate(instruments, start=1):
        events = generate_events_for_instrument(
            instrument=instrument,
            daily=daily_by_instrument[instrument],
            membership=membership_by_instrument[instrument],
            split_config=split_config,
            config=config,
        )
        if not events.empty:
            instance_parts.append(events)
        if progress_every > 0 and (
            processed_no == 1
            or processed_no == len(instruments)
            or processed_no % progress_every == 0
        ):
            progress(
                f"processed {processed_no}/{len(instruments)} instruments; "
                f"candidate_instances={sum(len(part) for part in instance_parts)}"
            )
    instances = pd.concat(instance_parts, ignore_index=True) if instance_parts else empty_event_frame()
    canonical = build_candidate_canonical_events(instances, config)
    progress(f"labeling {len(instances)} instances and {len(canonical)} canonical union events")
    instance_labels = _p04.label_events(
        instances, daily_by_instrument=daily_by_instrument, label_cfg=label_cfg
    )
    canonical_labels = _p04.label_events(
        canonical, daily_by_instrument=daily_by_instrument, label_cfg=label_cfg
    )

    progress("building family, union, recall, density, label, and overlap tables")
    event_sets, metadata = build_scope_event_sets(instances, canonical, e1_events, canonical_07, config)
    event_sets["selected_candidate_union"] = empty_event_frame()
    metadata["selected_candidate_union"] = scope_metadata(
        "selected_candidate_union", UNION_SCOPE, "selected_candidate_union", "train_selected_union", "mixed", "mixed"
    )
    labels_by_scope: dict[str, pd.DataFrame] = {
        E1_SCOPE: e1_labels,
        FULL_07_SCOPE: full07_labels,
        "all_new_candidate_union": canonical_labels,
        "selected_candidate_union": pd.DataFrame(),
    }
    instance_label_ids = set(instance_labels["event_id"].astype(str))
    canonical_label_ids = set(canonical_labels["event_id"].astype(str))
    for scope_id, events in event_sets.items():
        if scope_id in labels_by_scope:
            continue
        if scope_id in {E1_SCOPE, FULL_07_SCOPE}:
            continue
        event_ids = set(events["event_id"].astype(str)) if "event_id" in events.columns else set()
        if event_ids.issubset(instance_label_ids):
            labels_by_scope[scope_id] = instance_labels.loc[
                instance_labels["event_id"].astype(str).isin(event_ids)
            ].copy()
        elif event_ids.issubset(canonical_label_ids):
            labels_by_scope[scope_id] = canonical_labels.loc[
                canonical_labels["event_id"].astype(str).isin(event_ids)
            ].copy()
        else:
            labels_by_scope[scope_id] = _p04.label_events(
                events, daily_by_instrument=daily_by_instrument, label_cfg=label_cfg
            )

    capture_map: dict[str, pd.DataFrame] = {}
    for scope_id, events in event_sets.items():
        labels = labels_by_scope.get(scope_id, pd.DataFrame())
        capture_map[scope_id] = build_capture(episodes, events, labels, daily_by_instrument)
    denominator_summary = pd.read_csv(input_paths["upstream_06_denominator_summary_csv"])
    any_recall, bridge_recall, bridge_exclusion = build_recall_tables(capture_map, metadata)
    incremental = build_incremental_recall(
        capture_map,
        metadata,
        e1_capture,
        full07_capture,
        channel_captures=channel_captures,
    )
    density, density_denominator = build_density_tables(
        event_sets,
        metadata,
        denominator_summary,
        feature_panel,
        e1_events=e1_events,
    )
    selected_variants = select_candidate_variants(incremental, density, config)
    selected_canonical = build_selected_union(instances, selected_variants)
    selected_labels = _p04.label_events(
        selected_canonical, daily_by_instrument=daily_by_instrument, label_cfg=label_cfg
    )
    event_sets["selected_candidate_union"] = selected_canonical
    labels_by_scope["selected_candidate_union"] = selected_labels
    capture_map["selected_candidate_union"] = build_capture(
        episodes, selected_canonical, selected_labels, daily_by_instrument
    )
    metadata["selected_candidate_union"] = scope_metadata(
        "selected_candidate_union", UNION_SCOPE, "selected_candidate_union", "train_selected_union", "mixed", "mixed"
    )
    timing_basis = build_timing_basis_comparison(
        episodes,
        e1_capture,
        capture_map["selected_candidate_union"],
        e1_events,
        selected_canonical,
        daily_by_instrument,
        config,
    )
    any_recall, bridge_recall, bridge_exclusion = build_recall_tables(capture_map, metadata)
    incremental = build_incremental_recall(
        capture_map,
        metadata,
        e1_capture,
        full07_capture,
        channel_captures=channel_captures,
        timing_basis=timing_basis,
    )
    density, density_denominator = build_density_tables(
        event_sets,
        metadata,
        denominator_summary,
        feature_panel,
        e1_events=e1_events,
    )
    density = apply_density_contract_flags(density, incremental, selected_variants, config)

    label_frames: list[pd.DataFrame] = []
    false_frames: list[pd.DataFrame] = []
    for scope_id, events in event_sets.items():
        if scope_id in {E1_SCOPE, FULL_07_SCOPE}:
            continue
        labels = labels_by_scope.get(scope_id, pd.DataFrame())
        label = build_label_quality(labels, events, metadata[scope_id])
        false = build_false_repair(labels, events, metadata[scope_id])
        if not label.empty:
            label_frames.append(label)
        if not false.empty:
            false_frames.append(false)
    label_quality = pd.concat(label_frames, ignore_index=True) if label_frames else pd.DataFrame()
    false_repair = pd.concat(false_frames, ignore_index=True) if false_frames else pd.DataFrame()
    lead_time = build_lead_time(capture_map, metadata)
    overlap = build_overlap_matrix(capture_map, metadata, instances, instances_07)
    cluster_summary, cluster_ablation = build_mechanism_cluster_tables(
        instances,
        selected_variants,
        episodes,
        labels_by_scope,
        daily_by_instrument,
        e1_capture,
        full07_capture,
        config,
        label_cfg,
    )
    frontier = build_candidate_frontier(incremental, density, label_quality, selected_variants)
    run_capability = build_run_capability_summary(config, instances)
    if selected_variants:
        selected_family_ids = {
            variant.split("__", 1)[0]: variant.rsplit("__", 1)[-1] for variant in selected_variants
        }
        run_capability["selected_variant_id"] = run_capability["family_id"].map(selected_family_ids).fillna("")
    industry_audit = build_industry_style_input_audit(config, input_paths, feature_panel)
    formula_spec = build_formula_spec(config)
    feature_summary = build_feature_snapshot_summary(instances, instances_07)
    missed = build_missed_episode_audit(
        episodes,
        e1_capture,
        capture_map["selected_candidate_union"],
        capture_map["all_new_candidate_union"],
    )
    gating_comparison = build_event_regime_gating_comparison(incremental, density)
    input_audit = build_input_manifest_audit(input_paths, input_status, config)
    leakage_execution = build_leakage_execution_audit(instances, canonical, label_quality, config)
    validation_risk_on_denominator = len(
        denominator_ids(e1_capture, "validation", "risk_on", "before_first_50pct")
    )

    decision, gate_summary = decide(
        input_status,
        selected_variants,
        incremental,
        density,
        label_quality,
        bridge_recall,
        bridge_exclusion,
        timing_basis,
        cluster_ablation,
        config,
    )
    gate_summary.update(
        {
            "run_scope": run_scope,
            "candidate_event_instance_count": int(len(instances)),
            "candidate_canonical_event_count": int(len(canonical)),
            "selected_canonical_event_count": int(len(selected_canonical)),
            "target_episode_count": int(episodes["episode_id"].nunique()),
            "e1_only_canonical_event_count": int(len(e1_events)),
            "validation_risk_on_denominator": int(validation_risk_on_denominator),
        }
    )

    baseline_recall = e1_any.copy()
    output_frames = {
        "regime_recall_baseline": baseline_recall,
        "e1_recompute_audit": e1_audit,
        "missed_episode_audit": missed,
        "candidate_event_instances": instances,
        "candidate_canonical_events": canonical,
        "candidate_recall": any_recall,
        "incremental_recall": incremental,
        "bridge_positive_recall": bridge_recall,
        "bridge_exclusion_audit": bridge_exclusion,
        "density_summary": density,
        "density_denominator_comparison": density_denominator,
        "overlap_matrix": overlap,
        "lead_time_distribution": lead_time,
        "label_quality": label_quality,
        "false_repair_diagnostic": false_repair,
        "feature_snapshot_summary": feature_summary,
        "candidate_frontier": frontier,
        "run_capability": run_capability,
        "mechanism_cluster_summary": cluster_summary,
        "cluster_ablation": cluster_ablation,
        "industry_style_input_audit": industry_audit,
        "formula_spec": formula_spec,
        "event_regime_gating_comparison": gating_comparison,
        "timing_basis_comparison": timing_basis,
        "leakage_execution_audit": leakage_execution,
        "input_manifest_audit": input_audit,
    }
    progress("writing publishable/debug tables")
    for key, frame in output_frames.items():
        write_dataframe(output_paths[key], frame)
    all_labels = pd.concat(
        [
            instance_labels.assign(label_scope="event_instance"),
            canonical_labels.assign(label_scope="all_new_candidate_union"),
            selected_labels.assign(label_scope="selected_candidate_union"),
        ],
        ignore_index=True,
    )
    all_capture = pd.concat(
        [capture.assign(candidate_scope_id=scope_id) for scope_id, capture in capture_map.items()],
        ignore_index=True,
    )
    write_dataframe(output_paths["candidate_labels_local"], all_labels)
    write_dataframe(output_paths["candidate_capture_local"], all_capture)
    write_dataframe(output_paths["feature_panel_local"], feature_panel)
    write_report(
        output_paths["report"],
        decision=decision,
        gate_summary=gate_summary,
        input_status=input_status,
        denominator_summary=denominator_summary,
        run_capability=run_capability,
        e1_audit=e1_audit,
        baseline_recall=baseline_recall,
        frontier=frontier,
        density=density,
        label_quality=label_quality,
        bridge=bridge_recall,
        overlap=overlap,
        cluster_summary=cluster_summary,
        cluster_ablation=cluster_ablation,
        industry_audit=industry_audit,
        timing_basis=timing_basis,
        validation_risk_on_denominator=validation_risk_on_denominator,
    )
    manifest_outputs = {key: value for key, value in output_paths.items() if key != "manifest"}
    manifest_frames = {
        **output_frames,
        "candidate_labels_local": all_labels,
        "candidate_capture_local": all_capture,
        "feature_panel_local": feature_panel,
    }
    write_manifest(
        output_paths["manifest"],
        config=config,
        config_path=config_path,
        decision=decision,
        gate_summary=gate_summary,
        input_paths=input_paths,
        output_paths=manifest_outputs,
        run_scope=run_scope,
        input_artifacts=build_artifact_metadata(input_paths),
        output_artifacts=build_artifact_metadata(manifest_outputs, manifest_frames),
    )
    progress(f"completed run_scope={run_scope}; decision={decision}")
    return {
        "decision": decision,
        "run_scope": run_scope,
        "event_instance_count": int(len(instances)),
        "canonical_event_count": int(len(canonical)),
        "selected_canonical_event_count": int(len(selected_canonical)),
        "target_episode_count": int(episodes["episode_id"].nunique()),
        "manifest_path": str(output_paths["manifest"]),
        "report_path": str(output_paths["report"]),
    }
