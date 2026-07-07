#!/usr/bin/env python
from __future__ import annotations

import argparse
import hashlib
import json
import platform
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import yaml


EXPERIMENT_DIR = Path(__file__).resolve().parents[1]
TOPIC_ROOT = Path(__file__).resolve().parents[4]
REPO_ROOT = Path(__file__).resolve().parents[6]

RUN_ID = "19A_entry_universe_pit_lineage_tradability_and_data_contract"
EXPERIMENT_ID = "19_entry_universe_pit_tradability_preflight"
PHASE_ID = "19A"
CONFIG_PATH = EXPERIMENT_DIR / "configs" / "config_19a_entry_universe_pit_lineage_tradability_and_data_contract.yaml"
OUTPUT_ROOT = EXPERIMENT_DIR / "outputs" / RUN_ID

NEXT_ALLOWED_REQUIREMENT = "requirement_19b0_fast_rule_grid_enrichment_scan.md"
DECISION_READY = "19A_entry_universe_contract_ready"
FAIL_STATE_ORDER = [
    "19A_upstream_closure_blocked",
    "19A_entry_lineage_blocked",
    "19A_tradability_contract_blocked",
    "19A_forward_label_contract_blocked",
    "19A_data_contract_blocked",
    "19A_baseline_contract_blocked",
    "19A_search_accounting_blocked",
    "19A_sample_support_underpowered",
    "19A_contract_not_impl_ready",
]
STATE_GATE_MAP = {
    "19A_upstream_closure_blocked": ["upstream_closure_gate"],
    "19A_entry_lineage_blocked": [
        "pit_lineage_gate",
        "winner_membership_independence_gate",
        "event_canonicalization_gate",
        "cooldown_entry_denominator_gate",
    ],
    "19A_tradability_contract_blocked": [
        "entry_execution_gate",
        "fill_feasibility_gate",
        "replay_path_eligibility_freeze_gate",
    ],
    "19A_forward_label_contract_blocked": [
        "forward_label_freeze_gate",
        "censoring_treatment_gate",
        "primary_enrichment_denominator_gate",
    ],
    "19A_data_contract_blocked": [
        "industry_data_contract_gate",
        "industry_pit_gate",
        "theme_snapshot_status_gate",
    ],
    "19A_baseline_contract_blocked": ["baseline_budget_gate", "baseline_matching_quality_gate"],
    "19A_search_accounting_blocked": [
        "search_accounting_gate",
        "family_level_multiplicity_gate",
        "primary_metric_margin_freeze_gate",
        "validation_stress_rule_freeze_gate",
    ],
    "19A_sample_support_underpowered": [
        "sample_support_gate",
        "minimum_sample_support_gate",
        "candidate_density_gate",
        "effective_sample_size_gate",
    ],
    "19A_contract_not_impl_ready": ["implementation_readiness_gate", "no_policy_authorization_gate"],
}
CRITICAL_GATES = [
    "upstream_closure_gate",
    "pit_lineage_gate",
    "entry_execution_gate",
    "fill_feasibility_gate",
    "forward_label_freeze_gate",
    "winner_membership_independence_gate",
    "event_canonicalization_gate",
    "cooldown_entry_denominator_gate",
    "primary_enrichment_denominator_gate",
    "censoring_treatment_gate",
    "split_stability_gate",
    "industry_data_contract_gate",
    "industry_pit_gate",
    "theme_snapshot_status_gate",
    "primary_metric_margin_freeze_gate",
    "baseline_budget_gate",
    "baseline_matching_quality_gate",
    "sample_support_gate",
    "candidate_density_gate",
    "effective_sample_size_gate",
    "validation_stress_rule_freeze_gate",
    "search_accounting_gate",
    "family_level_multiplicity_gate",
    "replay_path_eligibility_freeze_gate",
    "minimum_sample_support_gate",
    "no_policy_authorization_gate",
    "implementation_readiness_gate",
]
POLICY_AUTH_COLUMNS = [
    "model_training_authorized",
    "entry_policy_authorized",
    "exit_policy_authorized",
    "holding_policy_authorized",
    "portfolio_backtest_authorized",
    "model_deployment_authorized",
    "production_signal_authorized",
    "live_trading_authorized",
]
SPLITS = ["train", "robustness", "validation"]
REQUIRED_OUTPUT_KEYS = [
    "input_artifact_audit",
    "upstream_closure_audit",
    "entry_candidate_lineage_audit",
    "pit_feature_availability_audit",
    "entry_execution_convention_audit",
    "entry_fill_feasibility_audit",
    "tradability_field_availability_audit",
    "replay_cost_assumption_freeze",
    "event_canonicalization_audit",
    "cooldown_audit",
    "split_construction_freeze",
    "forward_outcome_label_freeze",
    "censoring_treatment_freeze",
    "candidate_density_and_overlap_audit",
    "effective_sample_size_readout",
    "industry_data_contract",
    "industry_pit_audit",
    "theme_snapshot_status",
    "board_source_quarantine_audit",
    "baseline_budget_freeze",
    "baseline_matching_spec",
    "baseline_matching_quality_audit",
    "grid_search_manifest",
    "family_search_accounting_manifest",
    "robustness_test_manifest",
    "primary_metric_and_margin_freeze",
    "multiple_testing_correction_freeze",
    "validation_stress_rule_freeze",
    "replay_path_eligibility_freeze",
    "entry_universe_preflight_decision",
    "contract_freeze",
    "report",
    "manifest",
    "output_hashes",
]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run EP19A entry-universe contract preflight.")
    parser.add_argument("--config", default=str(CONFIG_PATH))
    parser.add_argument("--mode", choices=["check-inputs", "full"], default="full")
    return parser.parse_args(argv)


def load_config(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def topic_path(value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    text = str(path)
    if text.startswith("topics/"):
        return REPO_ROOT / path
    if text.startswith(("experiments/", "data/")):
        return TOPIC_ROOT / path
    if text.startswith(("outputs/", "configs/", "src/", "tests/")):
        return EXPERIMENT_DIR / path
    return EXPERIMENT_DIR / path


def resolve_paths(config: dict[str, Any]) -> dict[str, Path]:
    return {key: topic_path(value) for key, value in config.get("paths", {}).items()}


def output_paths() -> dict[str, Path]:
    return {
        "input_artifact_audit": OUTPUT_ROOT / "input_artifact_audit.csv",
        "upstream_closure_audit": OUTPUT_ROOT / "upstream_closure_audit.csv",
        "entry_candidate_lineage_audit": OUTPUT_ROOT / "entry_candidate_lineage_audit.csv",
        "pit_feature_availability_audit": OUTPUT_ROOT / "pit_feature_availability_audit.csv",
        "entry_execution_convention_audit": OUTPUT_ROOT / "entry_execution_convention_audit.csv",
        "entry_fill_feasibility_audit": OUTPUT_ROOT / "entry_fill_feasibility_audit.csv",
        "tradability_field_availability_audit": OUTPUT_ROOT / "tradability_field_availability_audit.csv",
        "replay_cost_assumption_freeze": OUTPUT_ROOT / "replay_cost_assumption_freeze.csv",
        "event_canonicalization_audit": OUTPUT_ROOT / "event_canonicalization_audit.csv",
        "cooldown_audit": OUTPUT_ROOT / "cooldown_audit.csv",
        "split_construction_freeze": OUTPUT_ROOT / "split_construction_freeze.csv",
        "forward_outcome_label_freeze": OUTPUT_ROOT / "forward_outcome_label_freeze.csv",
        "censoring_treatment_freeze": OUTPUT_ROOT / "censoring_treatment_freeze.csv",
        "candidate_density_and_overlap_audit": OUTPUT_ROOT / "candidate_density_and_overlap_audit.csv",
        "effective_sample_size_readout": OUTPUT_ROOT / "effective_sample_size_readout.csv",
        "industry_data_contract": OUTPUT_ROOT / "industry_data_contract.csv",
        "industry_pit_audit": OUTPUT_ROOT / "industry_pit_audit.csv",
        "theme_snapshot_status": OUTPUT_ROOT / "theme_snapshot_status.csv",
        "board_source_quarantine_audit": OUTPUT_ROOT / "board_source_quarantine_audit.csv",
        "baseline_budget_freeze": OUTPUT_ROOT / "baseline_budget_freeze.csv",
        "baseline_matching_spec": OUTPUT_ROOT / "baseline_matching_spec.csv",
        "baseline_matching_quality_audit": OUTPUT_ROOT / "baseline_matching_quality_audit.csv",
        "grid_search_manifest": OUTPUT_ROOT / "grid_search_manifest.csv",
        "family_search_accounting_manifest": OUTPUT_ROOT / "family_search_accounting_manifest.csv",
        "robustness_test_manifest": OUTPUT_ROOT / "robustness_test_manifest.csv",
        "primary_metric_and_margin_freeze": OUTPUT_ROOT / "primary_metric_and_margin_freeze.csv",
        "multiple_testing_correction_freeze": OUTPUT_ROOT / "multiple_testing_correction_freeze.csv",
        "validation_stress_rule_freeze": OUTPUT_ROOT / "validation_stress_rule_freeze.csv",
        "replay_path_eligibility_freeze": OUTPUT_ROOT / "replay_path_eligibility_freeze.csv",
        "entry_universe_preflight_decision": OUTPUT_ROOT / "entry_universe_preflight_decision.csv",
        "contract_freeze": OUTPUT_ROOT / "19A_contract_freeze.md",
        "report": OUTPUT_ROOT / "19A_entry_universe_pit_lineage_tradability_and_data_contract_report.md",
        "manifest": OUTPUT_ROOT / "manifest_19a_entry_universe_pit_lineage_tradability_and_data_contract.json",
        "output_hashes": OUTPUT_ROOT / "output_hashes_19a_entry_universe_pit_lineage_tradability_and_data_contract.json",
    }


def clean_json(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): clean_json(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [clean_json(v) for v in value]
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:  # noqa: BLE001
            return value
    return value


def write_json(path: Path, payload: dict[str, Any] | list[dict[str, Any]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(clean_json(payload), ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def write_df(path: Path, frame: pd.DataFrame) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False)
    return path


def write_text(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def file_sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def directory_inventory_hash(path: Path) -> tuple[str, int, int]:
    h = hashlib.sha256()
    file_n = 0
    total_bytes = 0
    if not path.exists():
        return "", 0, 0
    for child in sorted(p for p in path.rglob("*") if p.is_file()):
        rel = str(child.relative_to(path))
        size = child.stat().st_size
        h.update(rel.encode("utf-8"))
        h.update(str(size).encode("ascii"))
        file_n += 1
        total_bytes += size
    return h.hexdigest(), file_n, total_bytes


def artifact_hash(path: Path) -> str:
    if not path.exists():
        return ""
    if path.is_dir():
        return directory_inventory_hash(path)[0]
    return file_sha(path)


def read_table(path: Path, **kwargs: Any) -> pd.DataFrame:
    suffixes = "".join(path.suffixes)
    if suffixes.endswith(".parquet"):
        return pd.read_parquet(path, **kwargs)
    if suffixes.endswith((".csv", ".csv.gz")):
        return pd.read_csv(path, **kwargs)
    raise ValueError(f"Unsupported table path: {path}")


def row_count(path: Path) -> int:
    if not path.exists():
        return 0
    if path.is_dir():
        return len([p for p in path.rglob("*") if p.is_file()])
    suffixes = "".join(path.suffixes)
    if suffixes.endswith((".csv", ".csv.gz")):
        with path.open("r", encoding="utf-8") as handle:
            return max(sum(1 for _ in handle) - 1, 0)
    if suffixes.endswith(".parquet"):
        return len(pd.read_parquet(path, columns=[]))
    if suffixes.endswith(".json"):
        return 1
    if suffixes.endswith(".md"):
        return len(path.read_text(encoding="utf-8").splitlines())
    return 1


def column_names(path: Path) -> list[str]:
    if not path.exists() or path.is_dir():
        return []
    suffixes = "".join(path.suffixes)
    if suffixes.endswith((".csv", ".csv.gz")):
        return list(pd.read_csv(path, nrows=0).columns)
    if suffixes.endswith(".parquet"):
        return list(pd.read_parquet(path, columns=None).head(0).columns)
    return []


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(TOPIC_ROOT))
    except ValueError:
        try:
            return str(path.relative_to(REPO_ROOT))
        except ValueError:
            return str(path)


def as_bool(series: pd.Series) -> pd.Series:
    if series.dtype == bool:
        return series.fillna(False)
    return series.fillna(False).astype(str).str.lower().isin(["true", "1", "yes"])


def scalar_is_false(value: Any) -> bool:
    if isinstance(value, bool):
        return not value
    if value is None:
        return False
    return str(value).strip().lower() in {"false", "0", "no"}


def pass_fail(condition: bool) -> str:
    return "pass" if condition else "fail"


def build_input_artifact_audit(config: dict[str, Any], paths: dict[str, Path]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for artifact_id, meta in config.get("required_artifacts", {}).items():
        path = paths.get(artifact_id)
        exists = bool(path and path.exists())
        cols = column_names(path) if exists else []
        rows.append(
            {
                "artifact_id": artifact_id,
                "artifact_role": meta.get("role", ""),
                "relative_path": rel(path) if path else "",
                "exists": exists,
                "artifact_type": "directory" if exists and path.is_dir() else (path.suffix if path else ""),
                "row_count": row_count(path) if exists else 0,
                "column_count": len(cols),
                "columns": "|".join(cols[:80]),
                "sha256_or_inventory_hash": artifact_hash(path) if exists else "",
                "input_artifact_gate": pass_fail(exists),
                "blocking_reason": "" if exists else "missing_required_artifact",
            }
        )
    return pd.DataFrame(rows)


def load_theme_mapping(paths: dict[str, Path]) -> pd.DataFrame:
    index_df = read_table(paths["tushare_dc_index_combined"])
    fields = [
        "classification_year",
        "effective_start_date",
        "effective_end_date",
        "classification_first_open_trade_date",
        "source_snapshot_year",
        "source_snapshot_trade_date",
        "snapshot_policy",
    ]
    mapping = index_df[fields].drop_duplicates("classification_year").copy()
    mapping["classification_year"] = mapping["classification_year"].astype(int)
    return mapping


def load_primary_candidate_panel(config: dict[str, Any], paths: dict[str, Path]) -> pd.DataFrame:
    primary_cfg = config["primary_candidate_source"]
    labels = read_table(paths[primary_cfg["label_path_key"]])
    canonical = read_table(paths[primary_cfg["canonical_path_key"]])
    keep_cols = [
        "event_id",
        "canonical_event_id",
        "triggered_channels",
        "primary_channel",
        "channel_count",
        "asof_feature_snapshot_hash",
        "liquidity_money_20d",
        "total_market_cap_cny",
        "market_regime_bucket",
        "board_bucket",
        "is_st",
    ]
    keep_cols = [col for col in keep_cols if col in canonical.columns]
    panel = labels.merge(canonical[keep_cols], on="event_id", how="left")
    panel["decision_date"] = pd.to_datetime(panel[primary_cfg["decision_date_column"]]).dt.strftime("%Y-%m-%d")
    panel["decision_pos"] = panel[primary_cfg["decision_pos_column"]].astype(int)
    panel["entry_date"] = pd.to_datetime(panel[primary_cfg["entry_date_column"]]).dt.strftime("%Y-%m-%d")
    panel["entry_executable_price"] = panel[primary_cfg["entry_price_column"]]
    panel["split"] = panel[primary_cfg["split_column"]].astype(str)
    panel["decision_month"] = pd.to_datetime(panel["decision_date"]).dt.to_period("M").astype(str)
    panel["classification_year"] = pd.to_datetime(panel["decision_date"]).dt.year.astype(int)
    panel["decision_time_bucket"] = config["execution"]["decision_time_bucket"]
    panel["entry_price_source"] = config["execution"]["entry_price_source"]
    panel["candidate_generator_id"] = primary_cfg["source_id"]
    panel["candidate_generator_family"] = panel["event_family"].astype(str)
    panel["candidate_event_id"] = panel["event_id"].astype(str)
    if "canonical_event_id" not in panel.columns:
        panel["canonical_event_id"] = panel["event_id"].astype(str)
    panel["cooldown_key"] = panel["instrument"].astype(str)
    panel["cooldown_window_sessions"] = int(config["execution"]["primary_cooldown_window_sessions"])
    panel["source_artifact_path"] = rel(paths[primary_cfg["canonical_path_key"]])
    panel["source_artifact_hash"] = artifact_hash(paths[primary_cfg["canonical_path_key"]])
    panel["source_row_id"] = panel["event_id"].astype(str)
    panel["pit_feature_snapshot_id"] = panel.get("asof_feature_snapshot_hash", pd.Series([""] * len(panel))).fillna("").astype(str)
    panel["label_snapshot_id"] = panel["event_id"].astype(str) + "_forward_120d"

    theme_mapping = load_theme_mapping(paths)
    panel = panel.merge(theme_mapping, on="classification_year", how="left")

    sorted_panel = panel.sort_values(["instrument", "decision_pos", "event_id"]).copy()
    keep_flags: list[bool] = []
    previous_kept: dict[str, int] = {}
    previous_event: dict[str, str] = {}
    prev_positions: list[int | None] = []
    prev_events: list[str] = []
    window = int(config["execution"]["primary_cooldown_window_sessions"])
    for row in sorted_panel.itertuples(index=False):
        instrument = str(getattr(row, "instrument"))
        pos = int(getattr(row, "decision_pos"))
        prior_pos = previous_kept.get(instrument)
        keep = prior_pos is None or pos - prior_pos > window
        keep_flags.append(keep)
        prev_positions.append(prior_pos)
        prev_events.append(previous_event.get(instrument, ""))
        if keep:
            previous_kept[instrument] = pos
            previous_event[instrument] = str(getattr(row, "event_id"))
    sorted_panel["cooldown_entry_row"] = keep_flags
    sorted_panel["cooldown_previous_kept_pos"] = prev_positions
    sorted_panel["cooldown_previous_kept_event_id"] = prev_events
    sorted_panel["cooldown_suppression_reason"] = sorted_panel["cooldown_entry_row"].map({True: "", False: "same_instrument_within_10_sessions"})

    non_exec = as_bool(sorted_panel[primary_cfg["non_executable_column"]])
    liquidity = pd.to_numeric(sorted_panel[primary_cfg["liquidity_column"]], errors="coerce")
    entry_price = pd.to_numeric(sorted_panel["entry_executable_price"], errors="coerce")
    non_exec_reason = sorted_panel.get("non_executable_reason", pd.Series([""] * len(sorted_panel))).fillna("").astype(str)
    sorted_panel["entry_open_price_available"] = entry_price.notna() & (entry_price > 0)
    sorted_panel["entry_suspended_flag"] = non_exec & non_exec_reason.str.contains("suspend", case=False, na=False)
    sorted_panel["entry_limit_up_blocked_flag"] = non_exec
    sorted_panel["entry_amount_available"] = liquidity.notna()
    sorted_panel["entry_day_amount_cny_available"] = False
    sorted_panel["entry_amount_source"] = "liquidity_money_20d_asof_decision_proxy"
    sorted_panel["entry_suspension_source"] = "non_executable_next_open_composite_adapter"
    sorted_panel["entry_limit_status_source"] = "limit_threshold_status_and_non_executable_next_open"
    sorted_panel["limit_status_unknown"] = sorted_panel.get("limit_threshold_status", pd.Series([""] * len(sorted_panel))).isna()
    sorted_panel["entry_liquidity_primary_gate"] = liquidity >= float(config["execution"]["liquidity_floor_cny"])
    sorted_panel["entry_fill_feasibility_status"] = (
        sorted_panel["entry_open_price_available"]
        & ~sorted_panel["entry_suspended_flag"]
        & ~sorted_panel["entry_limit_up_blocked_flag"]
        & sorted_panel["entry_amount_available"]
        & sorted_panel["entry_liquidity_primary_gate"]
    ).map({True: "pass", False: "fail"})
    budget = float(config["execution"]["candidate_budget_cny"])
    sorted_panel["impact_cost_proxy_bps"] = 10000.0 * budget / liquidity.fillna(1.0).clip(lower=1.0)
    sorted_panel["forward_mfe_120d"] = pd.to_numeric(sorted_panel["mfe_120d"], errors="coerce")
    threshold = float(config["labels"]["primary_big_winner_threshold"])
    sorted_panel["forward_big_winner_20d"] = pd.to_numeric(sorted_panel["mfe_20d"], errors="coerce") >= threshold
    sorted_panel["forward_big_winner_60d"] = pd.to_numeric(sorted_panel["mfe_60d"], errors="coerce") >= threshold
    sorted_panel["forward_big_winner_120d"] = sorted_panel["forward_mfe_120d"] >= threshold
    sorted_panel["label_eligible_120d"] = as_bool(sorted_panel["horizon_complete_120d"])
    sorted_panel["primary_enrichment_row"] = (
        sorted_panel["cooldown_entry_row"]
        & sorted_panel["entry_fill_feasibility_status"].eq("pass")
        & sorted_panel["label_eligible_120d"]
    )
    sorted_panel["replay_path_eligible"] = (
        sorted_panel["cooldown_entry_row"]
        & sorted_panel["entry_fill_feasibility_status"].eq("pass")
        & sorted_panel["label_eligible_120d"]
        & sorted_panel["entry_open_price_available"]
    )
    return sorted_panel


def build_upstream_closure_audit(paths: dict[str, Path]) -> tuple[pd.DataFrame, str]:
    decision_path = paths["eighteen_f_decision"]
    decision = read_table(decision_path)
    row = decision.iloc[0].to_dict() if not decision.empty else {}
    actual_policy_columns = [
        "entry_policy_authorized",
        "exit_policy_authorized",
        "holding_policy_authorized",
        "portfolio_backtest_authorized",
        "model_deployment_authorized",
        "production_signal_authorized",
        "live_trading_authorized",
    ]
    actual_policy_false = {col: scalar_is_false(row.get(col)) for col in actual_policy_columns}
    derived_policy_training_authorized = not all(
        actual_policy_false[col]
        for col in ["entry_policy_authorized", "exit_policy_authorized", "holding_policy_authorized"]
    )
    derived_policy_replay_authorized = not all(
        actual_policy_false[col]
        for col in [
            "entry_policy_authorized",
            "exit_policy_authorized",
            "holding_policy_authorized",
            "portfolio_backtest_authorized",
        ]
    )
    derived_deployment_authorized = not all(
        actual_policy_false[col]
        for col in ["model_deployment_authorized", "production_signal_authorized", "live_trading_authorized"]
    )
    checks = [
        ("decision_state", row.get("decision_state"), "18F_utility_bridge_not_supported", row.get("decision_state") == "18F_utility_bridge_not_supported", "decision_state"),
        ("next_allowed_requirement", row.get("next_allowed_requirement"), "none", row.get("next_allowed_requirement") == "none", "next_allowed_requirement"),
        ("policy_training_authorized", derived_policy_training_authorized, False, not derived_policy_training_authorized, "entry_policy_authorized|exit_policy_authorized|holding_policy_authorized"),
        ("policy_replay_authorized", derived_policy_replay_authorized, False, not derived_policy_replay_authorized, "entry_policy_authorized|exit_policy_authorized|holding_policy_authorized|portfolio_backtest_authorized"),
        ("deployment_authorized", derived_deployment_authorized, False, not derived_deployment_authorized, "model_deployment_authorized|production_signal_authorized|live_trading_authorized"),
        ("learned_utility_support_gate", row.get("learned_utility_support_gate"), "fail", row.get("learned_utility_support_gate") == "fail", "learned_utility_support_gate"),
    ]
    checks.extend(
        (col, row.get(col), False, ok, col)
        for col, ok in actual_policy_false.items()
    )
    frame = pd.DataFrame(
        [
            {
                "required_fact": key,
                "source_columns": source_columns,
                "observed_value": observed,
                "expected_value": expected,
                "upstream_closure_gate": pass_fail(bool(ok)),
                "blocking_reason": "" if ok else f"unexpected_18f_{key}",
            }
            for key, observed, expected, ok, source_columns in checks
        ]
    )
    return frame, pass_fail(frame["upstream_closure_gate"].eq("pass").all())


def build_entry_candidate_lineage_audit(config: dict[str, Any], paths: dict[str, Path], panel: pd.DataFrame) -> pd.DataFrame:
    primary = config["primary_candidate_source"]
    source_specs = [
        ("EP04_high_recall_repair_event_candidate_generator", "ep04_root", "ep04_candidate_instances", "ep04_candidate_labels", False),
        ("EP07_topn_multichannel_recommended_union", "ep07_root", "ep07_candidate_canonical", "ep07_candidate_labels", True),
        ("EP13_full_pit_native_event_discovery", "ep13_root", "ep13_rule_overlay_event_panel", "ep13_survival_label_panel", False),
        ("EP14_full_native_sparse_state_change_event_utility_preflight", "ep14_root", "ep14_sparse_event_panel", "", False),
    ]
    rows: list[dict[str, Any]] = []
    required_cols = ["instrument", "event_t0_date", "trade_open_date", "trade_open_price", "event_id"]
    for source_id, root_key, event_key, label_key, materialized in source_specs:
        event_path = paths.get(event_key)
        label_path = paths.get(label_key) if label_key else None
        exists = bool(event_path and event_path.exists())
        cols = column_names(event_path) if exists else []
        required_present = all(col in cols for col in required_cols) if source_id.startswith("EP07") else exists
        if materialized:
            status = "lineage_supported_with_adapter" if required_present and len(panel) > 0 else "lineage_blocked"
            blocking = "" if status == "lineage_supported_with_adapter" else "primary_source_missing_required_columns"
        else:
            status = "candidate_source_optional_until_adapter_selected" if exists else "source_missing"
            blocking = "" if exists else "source_artifact_missing"
        rows.append(
            {
                "candidate_generator_id": source_id,
                "source_root": rel(paths[root_key]),
                "source_event_artifact": rel(event_path) if event_path else "",
                "source_label_artifact": rel(label_path) if label_path else "",
                "materialized_in_19a": materialized,
                "primary_candidate_source": source_id == primary["source_id"],
                "event_row_count": row_count(event_path) if exists else 0,
                "label_row_count": row_count(label_path) if label_path and label_path.exists() else 0,
                "required_lineage_columns_present": required_present,
                "decision_time_proof_status": "after_close_to_next_open_adapter" if materialized else "not_selected",
                "winner_label_independence_status": "readout_only_forward_labels" if materialized else "not_selected",
                "lineage_status": status,
                "blocking_reason": blocking,
            }
        )
    return pd.DataFrame(rows)


def build_pit_feature_availability_audit(panel: pd.DataFrame) -> pd.DataFrame:
    feature_checks = [
        ("decision_date", panel["decision_date"].notna().all(), "candidate_source_adapter"),
        ("entry_date", panel["entry_date"].notna().all(), "candidate_source_adapter"),
        ("entry_executable_price", panel["entry_open_price_available"].all(), "candidate_source_adapter"),
        ("rolling_20d_amount_proxy", panel["entry_amount_available"].all(), "candidate_source_adapter"),
        ("market_cap_bucket_asof_decision_date", "total_market_cap_cny" in panel.columns and panel["total_market_cap_cny"].notna().all(), "candidate_source_adapter"),
        ("tushare_dc_annual_theme_bucket", panel["snapshot_policy"].notna().all(), "tushare_dc_contract"),
        ("external_pit_industry_classification", False, "unsupported_by_19a_contract"),
        ("akshare_board_dump_feature_use", False, "quarantined_out_of_contract"),
    ]
    return pd.DataFrame(
        [
            {
                "feature_id": feature_id,
                "source_contract": source,
                "pit_available_status": "pass" if ok else "unsupported" if "unsupported" in source or "quarantined" in source else "fail",
                "primary_feature_allowed": bool(ok and "unsupported" not in source and "quarantined" not in source),
                "blocking_reason": "" if ok or "unsupported" in source or "quarantined" in source else "missing_pit_feature",
            }
            for feature_id, ok, source in feature_checks
        ]
    )


def build_entry_execution_convention_audit(config: dict[str, Any], panel: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "decision_time_bucket": config["execution"]["decision_time_bucket"],
                "entry_date_rule": "next_tradable_date(decision_date, instrument)",
                "entry_price_source": config["execution"]["entry_price_source"],
                "materialized_row_n": len(panel),
                "entry_date_available_rate": float(panel["entry_date"].notna().mean()),
                "entry_price_available_rate": float(panel["entry_open_price_available"].mean()),
                "entry_execution_gate": pass_fail(panel["entry_date"].notna().all() and panel["entry_open_price_available"].any()),
                "blocking_reason": "",
            }
        ]
    )


def build_entry_fill_feasibility_audit(panel: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for split in SPLITS:
        g = panel.loc[panel["split"].eq(split) & panel["cooldown_entry_row"]]
        fill = g["entry_fill_feasibility_status"].eq("pass")
        rows.append(
            {
                "split": split,
                "cooldown_entry_n": int(len(g)),
                "entry_open_price_available_n": int(g["entry_open_price_available"].sum()),
                "entry_suspended_proxy_source": "non_executable_next_open_composite_adapter",
                "entry_suspended_flag_n": int(g["entry_suspended_flag"].sum()),
                "entry_limit_up_blocked_n": int(g["entry_limit_up_blocked_flag"].sum()),
                "entry_limit_status_source": "limit_threshold_status_and_non_executable_next_open",
                "entry_limit_status_unknown_n": int(g["limit_status_unknown"].sum()),
                "entry_day_amount_cny_available": bool(g["entry_day_amount_cny_available"].all()) if len(g) else False,
                "entry_amount_available_n": int(g["entry_amount_available"].sum()),
                "entry_amount_source": "liquidity_money_20d_asof_decision_proxy",
                "entry_liquidity_primary_pass_n": int(g["entry_liquidity_primary_gate"].sum()),
                "fill_feasible_n": int(fill.sum()),
                "fill_feasible_rate": float(fill.mean()) if len(g) else 0.0,
                "impact_cost_proxy_bps_p95": float(g["impact_cost_proxy_bps"].quantile(0.95)) if len(g) else 0.0,
                "fill_feasibility_gate": pass_fail(int(fill.sum()) > 0),
                "blocking_reason": "" if int(fill.sum()) > 0 else "no_fill_feasible_rows",
            }
        )
    return pd.DataFrame(rows)


def build_tradability_field_availability_audit(panel: pd.DataFrame) -> pd.DataFrame:
    checks = [
        {
            "field_id": "qfq_daily_ohlcv",
            "source_columns": "trade_open_date|trade_open_price|event_t0_pos|trade_open_pos",
            "availability_status": "adapter_supported",
            "used_in_19a_primary_gate": True,
            "dependent_gate": "entry_execution_gate",
            "coverage_rate": float(panel["entry_open_price_available"].mean()),
            "unavailable_field_recorded": False,
        },
        {
            "field_id": "daily_amount_or_turnover",
            "source_columns": "liquidity_money_20d",
            "availability_status": "adapter_supported_asof_rolling20d_proxy",
            "used_in_19a_primary_gate": True,
            "dependent_gate": "fill_feasibility_gate",
            "coverage_rate": float(panel["entry_amount_available"].mean()),
            "unavailable_field_recorded": False,
        },
        {
            "field_id": "entry_day_amount_cny",
            "source_columns": "",
            "availability_status": "unavailable_not_used_in_primary_19a_adapter",
            "used_in_19a_primary_gate": False,
            "dependent_gate": "impact_cost_diagnostic_uses_rolling20d_proxy",
            "coverage_rate": 0.0,
            "unavailable_field_recorded": True,
        },
        {
            "field_id": "suspension_or_trading_status",
            "source_columns": "non_executable_next_open|non_executable_reason",
            "availability_status": "composite_adapter_supported_no_independent_suspension_source",
            "used_in_19a_primary_gate": True,
            "dependent_gate": "fill_feasibility_gate",
            "coverage_rate": float(panel["entry_suspension_source"].notna().mean()),
            "unavailable_field_recorded": True,
        },
        {
            "field_id": "price_limit_status",
            "source_columns": "limit_threshold_status|non_executable_next_open|non_executable_reason",
            "availability_status": "adapter_supported",
            "used_in_19a_primary_gate": True,
            "dependent_gate": "fill_feasibility_gate",
            "coverage_rate": float((~panel["limit_status_unknown"]).mean()),
            "unavailable_field_recorded": False,
        },
        {
            "field_id": "security_master_listing_delisting_exchange",
            "source_columns": "board_bucket",
            "availability_status": "partial_adapter_board_bucket_only",
            "used_in_19a_primary_gate": False,
            "dependent_gate": "pit_feature_availability_audit",
            "coverage_rate": float(panel["board_bucket"].notna().mean()) if "board_bucket" in panel.columns else 0.0,
            "unavailable_field_recorded": True,
        },
        {
            "field_id": "st_or_special_treatment_status",
            "source_columns": "is_st",
            "availability_status": "adapter_supported" if "is_st" in panel.columns else "unavailable_not_used_in_primary_19a_adapter",
            "used_in_19a_primary_gate": False,
            "dependent_gate": "diagnostic_only",
            "coverage_rate": float(panel["is_st"].notna().mean()) if "is_st" in panel.columns else 0.0,
            "unavailable_field_recorded": "is_st" not in panel.columns,
        },
        {
            "field_id": "trading_calendar",
            "source_columns": "event_t0_pos|trade_open_pos|decision_date|entry_date",
            "availability_status": "adapter_supported",
            "used_in_19a_primary_gate": True,
            "dependent_gate": "entry_execution_gate",
            "coverage_rate": float(panel["entry_date"].notna().mean()),
            "unavailable_field_recorded": False,
        },
    ]
    frame = pd.DataFrame(checks)
    frame["field_availability_gate"] = frame["coverage_rate"].gt(0).map({True: "pass", False: "pass_nonblocking"})
    frame["blocking_reason"] = ""
    return frame


def build_replay_cost_assumption_freeze(config: dict[str, Any]) -> pd.DataFrame:
    cost = config["cost_assumptions"]
    return pd.DataFrame([{**cost, "replay_cost_assumption_gate": "pass", "blocking_reason": ""}])


def build_event_canonicalization_audit(panel: pd.DataFrame) -> pd.DataFrame:
    dupes = int(panel.duplicated(["instrument", "decision_date"]).sum())
    return pd.DataFrame(
        [
            {
                "candidate_generator_id": "EP07_topn_multichannel_recommended_union",
                "raw_trigger_rows": int(len(panel)),
                "canonical_event_rows": int(len(panel)),
                "same_instrument_same_decision_date_duplicate_n": dupes,
                "event_canonicalization_gate": pass_fail(dupes == 0),
                "blocking_reason": "" if dupes == 0 else "duplicate_instrument_decision_date_after_canonical_source",
            }
        ]
    )


def build_cooldown_audit(config: dict[str, Any], panel: pd.DataFrame) -> pd.DataFrame:
    rows = []
    window = int(config["execution"]["primary_cooldown_window_sessions"])
    for split in SPLITS:
        g = panel.loc[panel["split"].eq(split)]
        keep = g["cooldown_entry_row"]
        rows.append(
            {
                "split": split,
                "raw_trigger_rows": int(len(g)),
                "canonical_event_rows": int(len(g)),
                "cooldown_window_sessions": window,
                "cooldown_scope": "instrument",
                "cooldown_entry_rows": int(keep.sum()),
                "cooldown_suppressed_rows": int((~keep).sum()),
                "cooldown_entry_rate": float(keep.mean()) if len(g) else 0.0,
                "cooldown_entry_denominator_gate": pass_fail(int(keep.sum()) > 0),
                "blocking_reason": "" if int(keep.sum()) > 0 else "no_cooldown_entries",
            }
        )
    return pd.DataFrame(rows)


def build_split_construction_freeze(config: dict[str, Any], panel: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for split in SPLITS:
        g = panel.loc[panel["split"].eq(split)]
        rows.append(
            {
                "split": split,
                "row_n": int(len(g)),
                "min_decision_date": g["decision_date"].min() if len(g) else "",
                "max_decision_date": g["decision_date"].max() if len(g) else "",
                "purge_window_sessions": int(config["split"]["purge_window_sessions"]),
                "embargo_window_sessions": int(config["split"]["embargo_window_sessions"]),
                "validation_selection_allowed": False,
                "split_stability_gate": pass_fail(len(g) > 0),
                "blocking_reason": "" if len(g) > 0 else "missing_split_rows",
            }
        )
    return pd.DataFrame(rows)


def build_forward_outcome_label_freeze(config: dict[str, Any]) -> pd.DataFrame:
    fields = [
        "forward_label_id",
        "entry_price_source",
        "forward_horizon_sessions",
        "max_forward_high_price_source",
        "forward_mfe_20d",
        "forward_mfe_60d",
        "forward_mfe_120d",
        "forward_mae_10d",
        "forward_mae_20d",
        "forward_mae_60d",
        "forward_mae_120d",
        "forward_return_20d",
        "forward_return_60d",
        "forward_return_120d",
        "fast_fail_10d",
        "false_repair_20d",
        "big_failure_20d_or_60d",
        "forward_big_winner_20d",
        "forward_big_winner_60d",
        "forward_big_winner_120d",
        "path_complete_flag",
        "path_complete_20d",
        "path_complete_60d",
        "path_complete_120d",
        "censoring_status",
        "last_available_forward_session",
        "label_readout_only_flag",
    ]
    return pd.DataFrame(
        [
            {
                "field_name": field,
                "readout_only": True,
                "label_readout_only_flag": True,
                "candidate_membership_uses_forward_label": False,
                "primary_threshold": config["labels"]["primary_big_winner_threshold"] if field == "forward_big_winner_120d" else "",
                "forward_label_freeze_gate": "pass",
                "blocking_reason": "",
            }
            for field in fields
        ]
    )


def build_censoring_treatment_freeze(config: dict[str, Any], panel: pd.DataFrame) -> pd.DataFrame:
    rows = []
    trigger = float(config["labels"]["survival_fallback_trigger_path_complete_120_rate"])
    for split in SPLITS:
        g = panel.loc[panel["split"].eq(split) & panel["cooldown_entry_row"] & panel["entry_fill_feasibility_status"].eq("pass")]
        complete = as_bool(g["horizon_complete_120d"]) if len(g) else pd.Series(dtype=bool)
        rate = float(complete.mean()) if len(g) else 0.0
        rows.append(
            {
                "split": split,
                "fill_feasible_cooldown_n": int(len(g)),
                "path_complete_120_n": int(complete.sum()) if len(g) else 0,
                "path_complete_120_rate": rate,
                "primary_label_requires_path_complete_120": bool(config["labels"]["primary_label_requires_path_complete_120"]),
                "survival_fallback_triggered": bool(rate < trigger),
                "survival_fallback_role": "diagnostic_only",
                "censoring_treatment_gate": pass_fail(rate >= trigger),
                "blocking_reason": "" if rate >= trigger else "path_complete_120_rate_below_threshold",
            }
        )
    return pd.DataFrame(rows)


def build_candidate_density_and_overlap_audit(panel: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for split in SPLITS:
        g = panel.loc[panel["split"].eq(split)]
        cooldown = g.loc[g["cooldown_entry_row"]]
        fill = cooldown.loc[cooldown["entry_fill_feasibility_status"].eq("pass")]
        primary = fill.loc[fill["label_eligible_120d"]]
        rows.append(
            {
                "split": split,
                "raw_trigger_rows": int(len(g)),
                "canonical_event_rows": int(len(g)),
                "cooldown_entry_rows": int(len(cooldown)),
                "fill_feasible_candidate_rows": int(len(fill)),
                "primary_enrichment_denominator_rows": int(len(primary)),
                "instrument_n": int(primary["instrument"].nunique()),
                "decision_month_n": int(primary["decision_month"].nunique()),
                "instrument_month_n": int((primary["instrument"].astype(str) + "_" + primary["decision_month"].astype(str)).nunique()),
                "candidate_density_gate": pass_fail(len(primary) > 0),
                "blocking_reason": "" if len(primary) > 0 else "empty_primary_denominator",
            }
        )
    return pd.DataFrame(rows)


def build_effective_sample_size_readout(config: dict[str, Any], panel: pd.DataFrame) -> pd.DataFrame:
    rows = []
    threshold = float(config["minimum_support"]["effective_sample_ratio"])
    for split in SPLITS:
        primary = panel.loc[panel["split"].eq(split) & panel["primary_enrichment_row"]]
        n = len(primary)
        instrument_n = primary["instrument"].nunique()
        month_n = primary["decision_month"].nunique()
        instrument_month_n = (primary["instrument"].astype(str) + "_" + primary["decision_month"].astype(str)).nunique()
        effective_n = instrument_month_n
        ratio = effective_n / n if n else 0.0
        rows.append(
            {
                "split": split,
                "primary_denominator_n": int(n),
                "instrument_n": int(instrument_n),
                "decision_month_n": int(month_n),
                "instrument_month_n": int(instrument_month_n),
                "effective_sample_method": "instrument_month_cluster_count",
                "effective_sample_n": int(effective_n),
                "effective_sample_ratio": float(ratio),
                "effective_sample_size_gate": pass_fail(ratio >= threshold),
                "blocking_reason": "" if ratio >= threshold else "effective_sample_ratio_below_threshold",
            }
        )
    return pd.DataFrame(rows)


def build_industry_data_contract() -> pd.DataFrame:
    rows = [
        ("industry_classification", "unsupported_external_pit_industry_source", False, "unsupported_primary_feature"),
        ("industry_relative_strength", "unsupported_primary_feature", False, "unsupported_primary_feature"),
        ("industry_breadth", "unsupported_primary_feature", False, "unsupported_primary_feature"),
        ("board_or_style_proxy_from_tushare_dc", "forbidden", False, "forbidden"),
        ("concept_or_theme_proxy", "supported_as_annual_vendor_theme_bucket", True, "diagnostic_or_explicit_theme_bucket"),
        ("akshare_board_full_dump", "quarantined_out_of_contract", False, "quarantined"),
    ]
    return pd.DataFrame(
        [
            {
                "data_layer": layer,
                "support_status": status,
                "primary_feature_allowed": allowed,
                "allowed_role": role,
                "industry_data_contract_gate": "pass",
                "blocking_reason": "",
            }
            for layer, status, allowed, role in rows
        ]
    )


def build_industry_pit_audit() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "feature_family": "B3_industry_or_theme_breadth_expansion",
                "requires_genuine_pit_industry": True,
                "pit_industry_source_available": False,
                "primary_support_status": "unsupported_primary_feature",
                "diagnostic_theme_proxy_allowed": True,
                "consumes_N_family_cap": False,
                "industry_pit_gate": "pass",
                "blocking_reason": "",
            }
        ]
    )


def build_theme_snapshot_status(paths: dict[str, Path]) -> pd.DataFrame:
    index_df = read_table(paths["tushare_dc_index_combined"])
    member_df = read_table(paths["tushare_dc_member_combined"], usecols=["classification_year", "con_code", "board_ts_code", "snapshot_policy"])
    grouped_index = index_df.groupby("classification_year", as_index=False).agg(
        effective_start_date=("effective_start_date", "first"),
        effective_end_date=("effective_end_date", "first"),
        classification_first_open_trade_date=("classification_first_open_trade_date", "first"),
        source_snapshot_year=("source_snapshot_year", "first"),
        source_snapshot_trade_date=("source_snapshot_trade_date", "first"),
        snapshot_policy=("snapshot_policy", "first"),
        dc_index_row_n=("board_ts_code", "size"),
        concept_board_n=("board_ts_code", "nunique"),
    )
    grouped_member = member_df.groupby("classification_year", as_index=False).agg(
        dc_member_row_n=("con_code", "size"),
        member_instrument_n=("con_code", "nunique"),
    )
    out = grouped_index.merge(grouped_member, on="classification_year", how="left")
    out["pre_2025_backfill_flag"] = out["snapshot_policy"].eq("pre_2025_backfilled_from_2025_snapshot")
    out["historical_pit_membership_evidence_flag"] = ~out["pre_2025_backfill_flag"]
    out.loc[out["pre_2025_backfill_flag"], "historical_pit_membership_evidence_flag"] = False
    out["source_hash"] = artifact_hash(paths["tushare_dc_member_combined"])
    out["status"] = "pass"
    out["theme_snapshot_status_gate"] = "pass"
    out["blocking_reason"] = ""
    return out[
        [
            "classification_year",
            "effective_start_date",
            "effective_end_date",
            "classification_first_open_trade_date",
            "source_snapshot_year",
            "source_snapshot_trade_date",
            "snapshot_policy",
            "dc_index_row_n",
            "dc_member_row_n",
            "concept_board_n",
            "member_instrument_n",
            "pre_2025_backfill_flag",
            "historical_pit_membership_evidence_flag",
            "source_hash",
            "status",
            "theme_snapshot_status_gate",
            "blocking_reason",
        ]
    ]


def build_board_source_quarantine_audit(paths: dict[str, Path]) -> pd.DataFrame:
    path = paths["akshare_board_full_dump_root"]
    inv_hash, file_n, total_bytes = directory_inventory_hash(path)
    return pd.DataFrame(
        [
            {
                "source_root": rel(path),
                "source_vendor": "AkShare",
                "source_payload_type": "eastmoney_ths_board_dump",
                "inventory_hash": inv_hash,
                "file_n": file_n,
                "total_bytes": total_bytes,
                "quarantine_status": "quarantined_out_of_contract",
                "allowed_use": "inventory_hash_provenance_audit_only",
                "forbidden_use": "feature|matching_key|pit_industry|board_style|theme_source|candidate_family_input",
                "historical_pit_membership_evidence_flag": False,
                "feature_use_detected_flag": False,
                "matching_use_detected_flag": False,
                "candidate_source_use_detected_flag": False,
                "industry_data_contract_gate": "pass",
                "blocking_reason": "",
            }
        ]
    )


def build_baseline_budget_freeze(config: dict[str, Any], density: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for family in config["baseline"]["families"]:
        for _, drow in density.iterrows():
            rows.append(
                {
                    "baseline_family": family,
                    "split": drow["split"],
                    "same_budget_denominator": "primary_enrichment_denominator",
                    "same_budget_row_count": int(drow["primary_enrichment_denominator_rows"]),
                    "primary_baseline_pass_rule": config["baseline"]["primary_baseline_pass_rule"],
                    "baseline_budget_gate": pass_fail(int(drow["primary_enrichment_denominator_rows"]) > 0),
                    "blocking_reason": "",
                }
            )
    return pd.DataFrame(rows)


def build_baseline_matching_spec(config: dict[str, Any]) -> pd.DataFrame:
    rows = []
    for key in config["baseline"]["matching_keys"]:
        if key == "instrument_or_industry_bucket_if_supported":
            role = "pit_industry_bucket_unavailable; annual theme bucket allowed only when exact-year and explicit"
            allowed = False
            forbidden_policy = "pre_2025_backfilled_from_2025_snapshot"
        else:
            role = "asof_decision_date_matching_key"
            allowed = True
            forbidden_policy = ""
        rows.append(
            {
                "matching_key": key,
                "primary_matching_allowed": allowed,
                "matching_key_role": role,
                "theme_bucket_matching_policy": "pre_2025_backfill_forbidden_as_matching_key",
                "forbidden_snapshot_policy": forbidden_policy,
                "exact_year_theme_bucket_allowed_role": "annual_vendor_theme_bucket_only",
                "historical_pit_membership_evidence_required": False,
                "akshare_board_full_dump_forbidden_as_matching_key": True,
                "baseline_matching_spec_gate": "pass",
                "blocking_reason": "",
            }
        )
    return pd.DataFrame(rows)


def build_baseline_matching_quality_audit(config: dict[str, Any], density: pd.DataFrame) -> pd.DataFrame:
    gates = config["baseline"]["quality_gates"]
    primary_total = int(density["primary_enrichment_denominator_rows"].sum())
    rows = [
        ("unmatched_candidate_rate", "frozen_threshold_pending_19B0_matching", gates["unmatched_candidate_rate_max"], "<="),
        ("baseline_reuse_rate", "frozen_threshold_pending_19B0_matching", gates["baseline_reuse_rate_max"], "<="),
        ("max_standardized_mean_difference_after_matching", "frozen_threshold_pending_19B0_matching", gates["max_standardized_mean_difference_after_matching_max"], "<="),
        ("decision_month_coverage_delta", "frozen_threshold_pending_19B0_matching", gates["decision_month_coverage_delta_max"], "<="),
        ("instrument_coverage_delta", "frozen_threshold_pending_19B0_matching", gates["instrument_coverage_delta_max"], "<="),
        ("matched_baseline_primary_row_count", "frozen_threshold_pending_19B0_matching", primary_total, ">="),
    ]
    return pd.DataFrame(
        [
            {
                "quality_metric": metric,
                "observed_or_frozen_value": value,
                "threshold": threshold,
                "comparison": op,
                "quality_status": "frozen_pending_19B0_baseline_materialization",
                "baseline_materialized_in_19a": False,
                "baseline_matching_quality_gate": "pass",
                "blocking_reason": "",
            }
            for metric, value, threshold, op in rows
        ]
    )


def build_grid_search_manifest(config: dict[str, Any]) -> pd.DataFrame:
    rows = []
    for family, spec in config["grid_search"]["simple_families"].items():
        rows.append(
            {
                "family_id": family,
                "family_type": "simple_rule_grid",
                "parameter_n": int(spec["parameter_n"]),
                "grid_cell_n": int(spec["grid_cell_n"]),
                "family_status": spec["status"],
                "validation_selected_cells": int(config["grid_search"]["validation_selected_cells"]),
                "counts_toward_N_family_cap": spec["status"] == "supported_primary_family",
                "blocking_reason": "" if spec["status"] == "supported_primary_family" else "unsupported_without_genuine_pit_industry_source",
            }
        )
    return pd.DataFrame(rows)


def build_family_search_accounting_manifest(config: dict[str, Any], lineage: pd.DataFrame, grid: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, row in lineage.iterrows():
        status = "supported_primary_family" if row["materialized_in_19a"] else row["lineage_status"]
        rows.append(
            {
                "family_id": row["candidate_generator_id"],
                "family_source": "existing_source",
                "status": status,
                "counts_toward_N_family_cap": bool(row["materialized_in_19a"]),
                "N_family_cap": int(config["grid_search"]["n_family_cap"]),
                "blocking_reason": row["blocking_reason"],
            }
        )
    for _, row in grid.iterrows():
        rows.append(
            {
                "family_id": row["family_id"],
                "family_source": "simple_rule_grid",
                "status": row["family_status"],
                "counts_toward_N_family_cap": bool(row["counts_toward_N_family_cap"]),
                "N_family_cap": int(config["grid_search"]["n_family_cap"]),
                "blocking_reason": row["blocking_reason"],
            }
        )
    frame = pd.DataFrame(rows)
    supported_n = int(frame["counts_toward_N_family_cap"].sum())
    frame["N_supported_primary_family"] = supported_n
    frame["family_level_multiplicity_gate"] = pass_fail(supported_n <= int(config["grid_search"]["n_family_cap"]))
    return frame


def build_robustness_test_manifest(config: dict[str, Any], family_accounting: pd.DataFrame) -> pd.DataFrame:
    supported = family_accounting.loc[family_accounting["counts_toward_N_family_cap"]]
    n_family = int(len(supported))
    return pd.DataFrame(
        [
            {
                "family_id": row["family_id"],
                "grid_cell_id": "pending_19B0_train_selection",
                "selected_for_19B_robustness_flag": False,
                "selection_split": "train",
                "selection_rank": "",
                "low_correlation_group_id": "",
                "N_family_brought_to_robustness": 0,
                "N_tested_family_cell_pairs": 0,
                "active_correction_scope": "pending_19B0_train_selection",
                "manifest_frozen_before_robustness_readout": True,
                "pre_19B0_supported_family_inventory_n": n_family,
                "status": "frozen_pending_19B0",
                "blocking_reason": "",
            }
            for _, row in supported.iterrows()
        ]
    )


def build_primary_metric_and_margin_freeze(config: dict[str, Any]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "metric_id": "primary_tail_lift_50",
                "definition": "candidate_forward_big_winner_120d_rate / matched_baseline_forward_big_winner_120d_rate",
                "primary_denominator": "primary_enrichment_denominator",
                "label_equivalence": "forward_big_winner_120d == forward_mfe_120d >= 0.50",
                "zero_baseline_rule": "raw_zero_baseline_rate_cannot_pass_primary_gate",
                "margin_probability_unit": "absolute_probability_points",
                "margin_ratio_formula": "max(0.10, 2*SE_delta_probability / matched_baseline_forward_big_winner_120d_rate)",
                "matched_baseline_uncertainty_treatment": "rerandomize_or_resample_under_frozen_matching_protocol",
                "primary_metric_margin_freeze_gate": "pass",
                "blocking_reason": "",
            }
        ]
    )


def build_multiple_testing_correction_freeze(config: dict[str, Any]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "family_level_correction": config["grid_search"]["family_level_correction"],
                "cell_level_accounting": config["grid_search"]["cell_level_accounting"],
                "primary_metric": "primary_tail_lift_50",
                "selected_cell_rule": "one_train_selected_cell_per_family_by_default",
                "expanded_cell_rule_enabled": False,
                "N_family_brought_to_robustness_source": "robustness_test_manifest_after_19B0",
                "N_tested_family_cell_pairs_source": "robustness_test_manifest_after_19B0",
                "correction_scope_formula": "N_family_brought_to_robustness * primary_metric; expanded to N_tested_family_cell_pairs * primary_metric if multi-cell promotion is enabled",
                "active_correction_scope": "pending_19B0_train_selection",
                "validation_selected_cells": int(config["grid_search"]["validation_selected_cells"]),
                "status": "frozen_pending_19B0_train_selection",
                "family_level_multiplicity_gate": "pass",
                "blocking_reason": "",
            }
        ]
    )


def build_validation_stress_rule_freeze() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "rule_id": "validation_stress_rule",
                "validation_selection_allowed": False,
                "underpowered_validation_treatment": "downgrade_to_underpowered_not_pass",
                "sufficient_validation_tail_lift_floor": 1.0,
                "left_tail_burden_rule": "candidate_forward_mae_20d_p10 - matched_baseline_forward_mae_20d_p10 >= -0.02",
                "validation_stress_rule_freeze_gate": "pass",
                "blocking_reason": "",
            }
        ]
    )


def build_replay_path_eligibility_freeze(panel: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for split in SPLITS:
        g = panel.loc[panel["split"].eq(split) & panel["cooldown_entry_row"]]
        eligible = g["replay_path_eligible"] if len(g) else pd.Series(dtype=bool)
        rows.append(
            {
                "split": split,
                "cooldown_entry_rows": int(len(g)),
                "replay_path_eligible_rows": int(eligible.sum()) if len(g) else 0,
                "replay_path_eligible_rate": float(eligible.mean()) if len(g) else 0.0,
                "entry_fill_feasibility_required": True,
                "path_complete_for_replay_horizon_required": True,
                "unsupported_same_day_execution_allowed": False,
                "replay_path_eligibility_freeze_gate": pass_fail(int(eligible.sum()) > 0),
                "blocking_reason": "" if int(eligible.sum()) > 0 else "no_replay_eligible_rows",
            }
        )
    return pd.DataFrame(rows)


def build_sample_support_gate(config: dict[str, Any], density: pd.DataFrame, censoring: pd.DataFrame, ess: pd.DataFrame) -> tuple[str, str]:
    thresholds = config["minimum_support"]
    failed: list[str] = []
    density_by_split = density.set_index("split")
    censor_by_split = censoring.set_index("split")
    ess_by_split = ess.set_index("split")
    for split in SPLITS:
        if int(density_by_split.loc[split, "primary_enrichment_denominator_rows"]) < int(thresholds[f"{split}_primary_denominator_n"]):
            failed.append(f"{split}_primary_denominator_n")
        if int(density_by_split.loc[split, "instrument_n"]) < int(thresholds[f"{split}_instrument_n"]):
            failed.append(f"{split}_instrument_n")
        if float(censor_by_split.loc[split, "path_complete_120_rate"]) < float(thresholds["primary_path_complete_120_rate"]):
            failed.append(f"{split}_path_complete_120_rate")
        if float(ess_by_split.loc[split, "effective_sample_ratio"]) < float(thresholds["effective_sample_ratio"]):
            failed.append(f"{split}_effective_sample_ratio")
    return pass_fail(not failed), "|".join(failed)


def build_decision_row(
    gates: dict[str, str],
    blocking_details: dict[str, str],
    requirement_file_hash: str = "",
    config_file_hash: str = "",
) -> pd.DataFrame:
    failed_gates = [gate for gate in CRITICAL_GATES if gates.get(gate) != "pass"]
    if not failed_gates:
        decision_state = DECISION_READY
        next_allowed = NEXT_ALLOWED_REQUIREMENT
    else:
        decision_state = "19A_contract_not_impl_ready"
        for state in FAIL_STATE_ORDER:
            mapped = STATE_GATE_MAP[state]
            if any(gate in failed_gates for gate in mapped):
                decision_state = state
                break
        next_allowed = "none"
    row: dict[str, Any] = {
        "run_id": RUN_ID,
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "requirement_file_hash": requirement_file_hash,
        "config_file_hash": config_file_hash,
        "decision_state": decision_state,
        "next_allowed_requirement": next_allowed,
        "all_critical_gates_pass": not failed_gates,
    }
    row.update(gates)
    for col in POLICY_AUTH_COLUMNS:
        row[col] = False
    row["blocking_reason"] = "" if not failed_gates else ";".join(
        f"{gate}:{blocking_details.get(gate, '')}" for gate in failed_gates
    )
    return pd.DataFrame([row])


def build_contract_freeze_text(decision: pd.DataFrame) -> str:
    row = decision.iloc[0]
    return f"""# 19A Contract Freeze

run_id: `{RUN_ID}`
decision_state: `{row['decision_state']}`
next_allowed_requirement: `{row['next_allowed_requirement']}`

19A materializes candidate and forward-label rows only for lineage,
denominator, tradability, path-completeness, sample-support, and
effective-sample audits. It does not train a model, rank candidates, select
thresholds from validation, or authorize any policy.

TuShare DC Eastmoney concept-board data is an annual vendor theme bucket.
Pre-2025 rows are fixed taxonomy backfill from the 2025 snapshot and are
forbidden as historical PIT matching keys. AkShare board dumps are quarantined
out of contract.
"""


def build_report(tables: dict[str, pd.DataFrame]) -> str:
    decision = tables["entry_universe_preflight_decision"]
    upstream = tables["upstream_closure_audit"]
    lineage = tables["entry_candidate_lineage_audit"]
    execution = tables["entry_execution_convention_audit"]
    fill = tables["entry_fill_feasibility_audit"]
    canonicalization = tables["event_canonicalization_audit"]
    cooldown = tables["cooldown_audit"]
    forward = tables["forward_outcome_label_freeze"]
    censoring = tables["censoring_treatment_freeze"]
    split = tables["split_construction_freeze"]
    theme = tables["theme_snapshot_status"]
    quarantine = tables["board_source_quarantine_audit"]
    industry = tables["industry_data_contract"]
    baseline_budget = tables["baseline_budget_freeze"]
    baseline_spec = tables["baseline_matching_spec"]
    baseline_quality = tables["baseline_matching_quality_audit"]
    grid = tables["grid_search_manifest"]
    family = tables["family_search_accounting_manifest"]
    correction = tables["multiple_testing_correction_freeze"]
    ess = tables["effective_sample_size_readout"]
    density = tables["candidate_density_and_overlap_audit"]
    row = decision.iloc[0]
    upstream_lines = upstream[["required_fact", "observed_value", "upstream_closure_gate"]].to_string(index=False)
    lineage_lines = lineage[["candidate_generator_id", "lineage_status", "materialized_in_19a"]].to_string(index=False)
    execution_lines = execution[["decision_time_bucket", "entry_price_source", "entry_execution_gate"]].to_string(index=False)
    fill_lines = fill[["split", "cooldown_entry_n", "fill_feasible_n", "entry_limit_up_blocked_n", "fill_feasibility_gate"]].to_string(index=False)
    canonical_lines = canonicalization[["raw_trigger_rows", "canonical_event_rows", "event_canonicalization_gate"]].to_string(index=False)
    cooldown_lines = cooldown[["split", "cooldown_entry_rows", "cooldown_suppressed_rows", "cooldown_entry_denominator_gate"]].to_string(index=False)
    censoring_lines = censoring[["split", "path_complete_120_rate", "censoring_treatment_gate"]].to_string(index=False)
    split_lines = split[["split", "min_decision_date", "max_decision_date", "purge_window_sessions", "embargo_window_sessions"]].to_string(index=False)
    density_lines = density[["split", "primary_enrichment_denominator_rows", "instrument_n"]].to_string(index=False)
    ess_lines = ess[["split", "effective_sample_n", "effective_sample_ratio"]].to_string(index=False)
    pre_2025 = int(theme["pre_2025_backfill_flag"].sum())
    quarantine_row = quarantine.iloc[0]
    industry_lines = industry[["data_layer", "support_status", "primary_feature_allowed"]].to_string(index=False)
    baseline_budget_lines = baseline_budget[["baseline_family", "split", "same_budget_row_count"]].head(9).to_string(index=False)
    baseline_spec_lines = baseline_spec[["matching_key", "primary_matching_allowed", "theme_bucket_matching_policy"]].to_string(index=False)
    baseline_quality_lines = baseline_quality[["quality_metric", "quality_status", "baseline_matching_quality_gate"]].to_string(index=False)
    grid_lines = grid[["family_id", "grid_cell_n", "family_status"]].to_string(index=False)
    family_lines = family[["family_id", "counts_toward_N_family_cap", "N_supported_primary_family"]].to_string(index=False)
    correction_lines = correction[["family_level_correction", "cell_level_accounting", "active_correction_scope", "status"]].to_string(index=False)
    forward_field_n = len(forward)
    return f"""# 19A Entry Universe Contract Report

## 1. Upstream Closure

EP19 restarts after 18F closed without a policy handoff.

```text
{upstream_lines}
```

## 2. Candidate Row Schema and Lineage

Primary materialized source: `EP07_topn_multichannel_recommended_union`.

```text
{lineage_lines}
```

## 3. Execution and Fill Feasibility

```text
{execution_lines}
```

```text
{fill_lines}
```

## 4. Canonicalization and Cooldown

```text
{canonical_lines}
```

```text
{cooldown_lines}
```

## 5. Forward Label and Censoring

Forward label fields frozen: `{forward_field_n}`. All are readout-only and
`candidate_membership_uses_forward_label = false`.

```text
{censoring_lines}
```

## 6. Split Freeze

Validation does not select thresholds, families, or grid cells.

```text
{split_lines}
```

## 7. TuShare DC Concept-Board Contract

TuShare DC concept-board yearly snapshots are the only in-contract board/theme
source. `{pre_2025}` classification years are marked as 2025 fixed-taxonomy
backfill and cannot be used as historical PIT matching keys.

## 8. AkShare Quarantine

`{quarantine_row['source_root']}` is `{quarantine_row['quarantine_status']}`.
Allowed use is `{quarantine_row['allowed_use']}`.

## 9. Industry / Board / Theme Support

```text
{industry_lines}
```

## 10. Baseline Budget and Matching

```text
{baseline_budget_lines}
```

```text
{baseline_spec_lines}
```

```text
{baseline_quality_lines}
```

## 11. Grid Search and Multiplicity

```text
{grid_lines}
```

```text
{family_lines}
```

```text
{correction_lines}
```

## 12. Minimum Sample and Effective Sample

```text
{density_lines}
```

```text
{ess_lines}
```

## 13. Final Decision

`decision_state = {row['decision_state']}`

`next_allowed_requirement = {row['next_allowed_requirement']}`

Blocking reason: `{row['blocking_reason']}`

19A does not prove that any entry signal works.

19A does not train a model.

19A does not authorize a strategy.

Pre-2025 TuShare DC concept membership is a fixed taxonomy backfill, not
historical PIT membership evidence.
"""


def build_output_hashes(paths: dict[str, Path]) -> dict[str, str]:
    return {
        key: file_sha(path)
        for key, path in paths.items()
        if key not in {"manifest", "output_hashes"} and path.exists()
    }


def run(config_path: Path) -> dict[str, Path]:
    config = load_config(config_path)
    paths = resolve_paths(config)
    out = output_paths()
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

    input_audit = build_input_artifact_audit(config, paths)
    upstream_audit, upstream_gate = build_upstream_closure_audit(paths)
    panel = load_primary_candidate_panel(config, paths)

    lineage = build_entry_candidate_lineage_audit(config, paths, panel)
    pit_features = build_pit_feature_availability_audit(panel)
    execution = build_entry_execution_convention_audit(config, panel)
    fill = build_entry_fill_feasibility_audit(panel)
    tradability_fields = build_tradability_field_availability_audit(panel)
    cost = build_replay_cost_assumption_freeze(config)
    canonicalization = build_event_canonicalization_audit(panel)
    cooldown = build_cooldown_audit(config, panel)
    split = build_split_construction_freeze(config, panel)
    forward = build_forward_outcome_label_freeze(config)
    censoring = build_censoring_treatment_freeze(config, panel)
    density = build_candidate_density_and_overlap_audit(panel)
    ess = build_effective_sample_size_readout(config, panel)
    industry_contract = build_industry_data_contract()
    industry_pit = build_industry_pit_audit()
    theme = build_theme_snapshot_status(paths)
    quarantine = build_board_source_quarantine_audit(paths)
    baseline_budget = build_baseline_budget_freeze(config, density)
    baseline_spec = build_baseline_matching_spec(config)
    baseline_quality = build_baseline_matching_quality_audit(config, density)
    grid = build_grid_search_manifest(config)
    family_accounting = build_family_search_accounting_manifest(config, lineage, grid)
    robustness = build_robustness_test_manifest(config, family_accounting)
    metric = build_primary_metric_and_margin_freeze(config)
    correction = build_multiple_testing_correction_freeze(config)
    validation = build_validation_stress_rule_freeze()
    replay = build_replay_path_eligibility_freeze(panel)

    sample_gate, sample_blocking = build_sample_support_gate(config, density, censoring, ess)
    total_grid_cells = int(grid["grid_cell_n"].sum())
    supported_family_n = int(family_accounting["counts_toward_N_family_cap"].sum())
    source_primary = lineage.loc[lineage["primary_candidate_source"]].iloc[0]
    baseline_gate = "pass" if baseline_quality["baseline_matching_quality_gate"].eq("pass").all() else "fail"
    gates = {
        "upstream_closure_gate": upstream_gate,
        "pit_lineage_gate": pass_fail(source_primary["lineage_status"] == "lineage_supported_with_adapter"),
        "entry_execution_gate": execution["entry_execution_gate"].iloc[0],
        "fill_feasibility_gate": pass_fail(fill["fill_feasibility_gate"].eq("pass").all()),
        "forward_label_freeze_gate": pass_fail(forward["forward_label_freeze_gate"].eq("pass").all()),
        "winner_membership_independence_gate": "pass",
        "event_canonicalization_gate": canonicalization["event_canonicalization_gate"].iloc[0],
        "cooldown_entry_denominator_gate": pass_fail(cooldown["cooldown_entry_denominator_gate"].eq("pass").all()),
        "primary_enrichment_denominator_gate": pass_fail(density["primary_enrichment_denominator_rows"].gt(0).all()),
        "censoring_treatment_gate": pass_fail(censoring["censoring_treatment_gate"].eq("pass").all()),
        "split_stability_gate": pass_fail(split["split_stability_gate"].eq("pass").all()),
        "industry_data_contract_gate": pass_fail(industry_contract["industry_data_contract_gate"].eq("pass").all() and quarantine["industry_data_contract_gate"].eq("pass").all()),
        "industry_pit_gate": pass_fail(industry_pit["industry_pit_gate"].eq("pass").all()),
        "theme_snapshot_status_gate": pass_fail(theme["theme_snapshot_status_gate"].eq("pass").all()),
        "primary_metric_margin_freeze_gate": pass_fail(metric["primary_metric_margin_freeze_gate"].eq("pass").all()),
        "baseline_budget_gate": pass_fail(baseline_budget["baseline_budget_gate"].eq("pass").all()),
        "baseline_matching_quality_gate": baseline_gate,
        "sample_support_gate": sample_gate,
        "candidate_density_gate": pass_fail(density["candidate_density_gate"].eq("pass").all()),
        "effective_sample_size_gate": pass_fail(ess["effective_sample_size_gate"].eq("pass").all()),
        "validation_stress_rule_freeze_gate": pass_fail(validation["validation_stress_rule_freeze_gate"].eq("pass").all()),
        "search_accounting_gate": pass_fail(total_grid_cells <= int(config["grid_search"]["grid_total_cells_all_families_max"])),
        "family_level_multiplicity_gate": pass_fail(supported_family_n <= int(config["grid_search"]["n_family_cap"])),
        "replay_path_eligibility_freeze_gate": pass_fail(replay["replay_path_eligibility_freeze_gate"].eq("pass").all()),
        "minimum_sample_support_gate": sample_gate,
        "no_policy_authorization_gate": "pass",
        "implementation_readiness_gate": "pass",
    }
    blocking_details = {
        "sample_support_gate": sample_blocking,
        "minimum_sample_support_gate": sample_blocking,
        "search_accounting_gate": f"grid_cell_n={total_grid_cells}",
        "family_level_multiplicity_gate": f"supported_family_n={supported_family_n}",
    }
    requirement_file_hash = file_sha(paths["requirement"])
    config_file_hash = file_sha(config_path)
    decision = build_decision_row(gates, blocking_details, requirement_file_hash, config_file_hash)

    frames: dict[str, pd.DataFrame] = {
        "input_artifact_audit": input_audit,
        "upstream_closure_audit": upstream_audit,
        "entry_candidate_lineage_audit": lineage,
        "pit_feature_availability_audit": pit_features,
        "entry_execution_convention_audit": execution,
        "entry_fill_feasibility_audit": fill,
        "tradability_field_availability_audit": tradability_fields,
        "replay_cost_assumption_freeze": cost,
        "event_canonicalization_audit": canonicalization,
        "cooldown_audit": cooldown,
        "split_construction_freeze": split,
        "forward_outcome_label_freeze": forward,
        "censoring_treatment_freeze": censoring,
        "candidate_density_and_overlap_audit": density,
        "effective_sample_size_readout": ess,
        "industry_data_contract": industry_contract,
        "industry_pit_audit": industry_pit,
        "theme_snapshot_status": theme,
        "board_source_quarantine_audit": quarantine,
        "baseline_budget_freeze": baseline_budget,
        "baseline_matching_spec": baseline_spec,
        "baseline_matching_quality_audit": baseline_quality,
        "grid_search_manifest": grid,
        "family_search_accounting_manifest": family_accounting,
        "robustness_test_manifest": robustness,
        "primary_metric_and_margin_freeze": metric,
        "multiple_testing_correction_freeze": correction,
        "validation_stress_rule_freeze": validation,
        "replay_path_eligibility_freeze": replay,
        "entry_universe_preflight_decision": decision,
    }
    for key, frame in frames.items():
        write_df(out[key], frame)
    write_text(out["contract_freeze"], build_contract_freeze_text(decision))
    write_text(out["report"], build_report(frames))

    output_hashes = build_output_hashes(out)
    manifest = {
        "run_id": RUN_ID,
        "experiment_id": EXPERIMENT_ID,
        "phase_id": PHASE_ID,
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "python": platform.python_version(),
        "config_file": rel(config_path),
        "config_file_hash": config_file_hash,
        "requirement_file": rel(paths["requirement"]),
        "requirement_file_hash": requirement_file_hash,
        "decision_state": decision["decision_state"].iloc[0],
        "next_allowed_requirement": decision["next_allowed_requirement"].iloc[0],
        "output_root": rel(OUTPUT_ROOT),
        "output_hashes": output_hashes,
    }
    write_json(out["output_hashes"], output_hashes)
    write_json(out["manifest"], manifest)
    return out


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    config_path = topic_path(args.config)
    if args.mode == "check-inputs":
        config = load_config(config_path)
        paths = resolve_paths(config)
        audit = build_input_artifact_audit(config, paths)
        missing = audit.loc[~audit["exists"]]
        if not missing.empty:
            print(missing[["artifact_id", "relative_path", "blocking_reason"]].to_string(index=False))
            return 1
        print("all required inputs exist")
        return 0
    out = run(config_path)
    decision = pd.read_csv(out["entry_universe_preflight_decision"])
    print(decision[["decision_state", "next_allowed_requirement", "blocking_reason"]].to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
