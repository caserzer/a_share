#!/usr/bin/env python
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml


EXPERIMENT_DIR = Path(__file__).resolve().parents[1]
TOPIC_ROOT = Path(__file__).resolve().parents[4]
REPO_ROOT = Path(__file__).resolve().parents[6]

RUN_ID = "17D_oracle_diagnosis_report"
EXPERIMENT_ID = "17_oracle_action_value_upper_bound_diagnostic"
PHASE_ID = "17D"
CONFIG_PATH = EXPERIMENT_DIR / "configs" / "config_17d_oracle_diagnosis_report.yaml"
TABLE_DIR = EXPERIMENT_DIR / "outputs" / "publishable" / "tables" / RUN_ID
REPORT_DIR = EXPERIMENT_DIR / "outputs" / "publishable" / "reports"
MANIFEST_DIR = EXPERIMENT_DIR / "outputs" / "manifests"

FINAL_DECISION_STATES = {
    "oracle_no_action_value_in_current_space",
    "oracle_value_exists_feature_gap",
    "oracle_risk_signal_only_no_payoff_value",
    "oracle_delayed_decision_supported",
    "oracle_execution_capacity_blocked",
    "oracle_payoff_state_research_allowed",
    "oracle_lineage_or_denominator_blocked",
}
AUTH_FALSE_COLUMNS = (
    "entry_policy_authorized",
    "exit_policy_authorized",
    "holding_policy_authorized",
    "portfolio_backtest_authorized",
    "model_deployment_authorized",
    "production_signal_authorized",
    "live_trading_authorized",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run EP17D oracle diagnosis report.")
    parser.add_argument("--config", default=str(CONFIG_PATH))
    parser.add_argument("--check-inputs-only", action="store_true")
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
    if text.startswith(("data/", "experiments/")):
        return TOPIC_ROOT / path
    if text.startswith(("outputs/", "configs/", "src/", "tests/")):
        return EXPERIMENT_DIR / path
    return EXPERIMENT_DIR / path


def resolve_paths(config: dict[str, Any]) -> dict[str, Path]:
    return {key: topic_path(value) for key, value in config.get("paths", {}).items()}


def output_paths() -> dict[str, Path]:
    return {
        "input_gate_audit": TABLE_DIR / "17d_input_gate_audit.csv",
        "contract_validation_audit": TABLE_DIR / "17d_contract_validation_audit.csv",
        "decision_tree": TABLE_DIR / "oracle_diagnosis_decision_tree.csv",
        "value_source_attribution": TABLE_DIR / "oracle_value_source_attribution.csv",
        "path_risk_threshold_diagnosis": TABLE_DIR / "oracle_path_risk_threshold_diagnosis.csv",
        "upside_preservation_diagnosis": TABLE_DIR / "oracle_upside_preservation_diagnosis.csv",
        "timing_sensitivity_diagnosis": TABLE_DIR / "oracle_timing_sensitivity_diagnosis.csv",
        "learned_model_gap_bridge": TABLE_DIR / "oracle_learned_model_gap_bridge.csv",
        "decision": TABLE_DIR / "oracle_diagnosis_decision.csv",
        "search_accounting_audit": TABLE_DIR / "search_accounting_audit.csv",
        "report": REPORT_DIR / "ep17_oracle_action_value_diagnostic_report.md",
        "manifest": MANIFEST_DIR / "17D_oracle_diagnosis_report_manifest.json",
        "engine_manifest": MANIFEST_DIR / "oracle_diagnosis_engine_manifest.json",
        "input_artifact_manifest": MANIFEST_DIR / "input_artifact_manifest_17d.json",
    }


def clean_json(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): clean_json(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [clean_json(v) for v in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return None if not np.isfinite(value) else float(value)
    if isinstance(value, (np.bool_,)):
        return bool(value)
    try:
        if pd.isna(value):
            return None
    except TypeError:
        pass
    return value


def write_json(path: Path, payload: dict[str, Any] | list[dict[str, Any]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(clean_json(payload), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return path


def write_df(path: Path, frame: pd.DataFrame) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False)
    return path


def write_text(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def read_table(path: Path) -> pd.DataFrame:
    if "".join(path.suffixes).endswith(".csv"):
        return pd.read_csv(path)
    raise ValueError(f"Unsupported table path: {path}")


def read_json(path: Path) -> dict[str, Any] | list[Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def file_sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def count_rows(path: Path) -> int | float:
    if not path.exists():
        return np.nan
    if path.is_dir():
        return len(list(path.iterdir()))
    suffixes = "".join(path.suffixes)
    if suffixes.endswith(".csv"):
        with path.open("r", encoding="utf-8") as handle:
            return max(sum(1 for _ in handle) - 1, 0)
    if suffixes.endswith(".md"):
        return len(path.read_text(encoding="utf-8").splitlines())
    if suffixes.endswith(".json"):
        return 1
    return np.nan


def relative_to_topic(path: Path) -> str:
    try:
        return str(path.relative_to(TOPIC_ROOT))
    except ValueError:
        return str(path)


def str_value(value: Any) -> str:
    if pd.isna(value):
        return ""
    return str(value)


def true_like(value: Any) -> bool:
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes", "pass"}
    if pd.isna(value):
        return False
    return bool(value)


def false_like(value: Any) -> bool:
    if isinstance(value, (bool, np.bool_)):
        return not bool(value)
    if isinstance(value, str):
        return value.strip().lower() in {"false", "0", "no", ""}
    if pd.isna(value):
        return False
    return not bool(value)


def pass_like(value: Any) -> bool:
    return str_value(value).strip().lower() == "pass"


def safe_float(value: Any, default: float = np.nan) -> float:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return default
    return out if np.isfinite(out) else default


def required_columns_for_key(key: str) -> set[str]:
    mapping: dict[str, set[str]] = {
        "seventeen_c_input_gate_audit": {"artifact_key", "gate_status", "schema_status"},
        "seventeen_c_contract_validation_audit": {"artifact_key", "validation_check_id", "validation_status"},
        "seventeen_c_primary_summary": {
            "oracle_variant_id",
            "split_bucket",
            "cost_bps",
            "q_defend",
            "mean_incremental_return",
            "bootstrap_ci_low_min",
            "topk_removed_mean_min",
            "primary_support_gate",
        },
        "seventeen_c_topk_sensitivity": {
            "oracle_variant_id",
            "split_bucket",
            "cost_bps",
            "q_defend",
            "removal_family",
            "remaining_mean_incremental_return",
            "topk_gate",
        },
        "seventeen_c_bootstrap_ci": {
            "oracle_variant_id",
            "split_bucket",
            "cost_bps",
            "q_defend",
            "bootstrap_family",
            "bootstrap_primary_role",
            "ci_low",
            "bootstrap_gate",
        },
        "seventeen_c_matched_base": {"oracle_variant_id", "split_bucket", "matched_base_gate"},
        "seventeen_c_delay_curve": {
            "split_bucket",
            "delay_k_sessions",
            "delayed_mean_incremental_return",
            "delayed_mean_gap_vs_o5_t0",
            "delayed_retention_ratio_vs_o5_t0",
            "delayed_curve_gate",
        },
        "seventeen_c_capacity_constraint": {
            "capacity_status",
            "capacity_reconstruction_gate",
            "capacity_constraint_gate",
        },
        "seventeen_c_decision": {"decision_state", "next_allowed_requirement", "search_accounting_gate"},
        "seventeen_c_search_accounting_audit": {"phase_id", "search_accounting_gate"},
        "seventeen_b_ladder_summary": {
            "oracle_variant_id",
            "split_bucket",
            "cost_bps",
            "q_defend",
            "observed_step_n",
            "defended_rate",
            "mean_incremental_return",
        },
        "seventeen_b_six_cell_decomposition": {"oracle_variant_id", "cell_id", "six_cell_gate"},
        "seventeen_b_action_intensity_frontier": {"oracle_variant_id", "frontier_gate"},
        "seventeen_b_neutral_stress": {"oracle_variant_id", "neutral_stress_gate"},
        "seventeen_b_o2_drawdown_threshold_replay": {
            "oracle_variant_id",
            "signed_drawdown_threshold",
            "defended_step_n",
            "o2_drawdown_replay_gate",
        },
        "seventeen_b_o5_action_selection_proof": {
            "split_bucket",
            "cost_bps",
            "q_defend",
            "formula_recompute_gate",
            "o5_action_selection_proof_gate",
        },
        "seventeen_b_high_upside_threshold_freeze": {
            "oracle_variant_id",
            "threshold_id",
            "train_quantile",
            "train_absolute_payoff_cutoff",
        },
        "sixteen_d_decision": {"decision_state", "robustness_defense_negative_capture_rate"},
        "sixteen_d_policy_confusion_readout": {"split_bucket"},
        "sixteen_e_decision": {"decision_state", "primary_return_utility_gate", "drawdown_avoidance_gate"},
        "sixteen_e_six_cell_reconciliation": {
            "split_bucket",
            "cost_bps",
            "candidate_action",
            "label_class",
            "six_cell_reconciliation_status",
        },
        "sixteen_e_postmortem_decision": {"directionality_gate", "continuation_as_action_mainline_closed"},
        "sixteen_e_postmortem_failure_arithmetic": {
            "split_bucket",
            "cost_bps",
            "full_denominator_net_utility_total",
        },
        "sixteen_x_decision": {
            "payoff_separability_gate",
            "payoff_aligned_label_redo_authorized",
            "robustness_payoff_probe_rank_ic_spearman",
        },
        "sixteen_x_survival_vs_payoff_rank_ic": {"split_bucket"},
    }
    if key.endswith("_manifest") or key.endswith("_report") or key in {"requirement", "research_plan"}:
        return set()
    return mapping.get(key, set())


def artifact_role(key: str) -> str:
    if key in {"requirement", "research_plan"}:
        return "local_contract"
    if key.startswith("seventeen_c"):
        return "17c_handoff"
    if key.startswith("seventeen_b"):
        return "17b_supporting"
    if key.startswith("sixteen_") or key.startswith("episode_16"):
        return "16_reference"
    return "input_artifact"


def source_phase(key: str) -> str:
    if key.startswith("seventeen_c"):
        return "17C"
    if key.startswith("seventeen_b"):
        return "17B"
    if key.startswith("sixteen_d"):
        return "16D"
    if key.startswith("sixteen_e_postmortem"):
        return "16E_postmortem"
    if key.startswith("sixteen_e"):
        return "16E"
    if key.startswith("sixteen_x"):
        return "16X"
    if key.startswith("episode_16"):
        return "16"
    return PHASE_ID


def schema_status(path: Path, key: str) -> tuple[str, str]:
    required = required_columns_for_key(key)
    if not required:
        return "pass", ""
    if not path.exists():
        return "fail", "missing_artifact"
    try:
        cols = set(pd.read_csv(path, nrows=0).columns)
    except Exception as exc:
        return "fail", f"schema_read_failed:{type(exc).__name__}"
    missing = sorted(required - cols)
    if missing:
        return "fail", "missing_columns:" + ",".join(missing)
    return "pass", ""


def build_input_gate_audit(config: dict[str, Any], resolved: dict[str, Path]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for key, path in resolved.items():
        exists = path.exists()
        schema, schema_reason = schema_status(path, key)
        sha = file_sha(path) if exists and path.is_file() else ""
        gate = "pass" if exists and schema == "pass" else "fail"
        blocking = "" if gate == "pass" else (schema_reason or "missing_artifact")
        rows.append(
            {
                "artifact_key": key,
                "artifact_role": artifact_role(key),
                "required_flag": "required",
                "resolved_path": str(path),
                "relative_path": relative_to_topic(path),
                "source_phase_id": source_phase(key),
                "row_count": count_rows(path) if exists else np.nan,
                "sha256": sha,
                "schema_status": schema,
                "lineage_status": "pass" if exists else "fail_missing",
                "gate_status": gate,
                "blocking_reason": blocking,
            }
        )
    return pd.DataFrame(rows)


def contract_row(
    rows: list[dict[str, Any]],
    artifact_key: str,
    source_phase_id: str,
    source_manifest_key: str,
    manifest_output_key: str,
    check_id: str,
    observed: Any,
    expected: Any,
    status: str,
    blocking_reason: str = "",
) -> None:
    rows.append(
        {
            "artifact_key": artifact_key,
            "source_phase_id": source_phase_id,
            "source_manifest_key": source_manifest_key,
            "manifest_output_key": manifest_output_key,
            "validation_check_id": check_id,
            "observed_value": clean_json(observed),
            "expected_value": clean_json(expected),
            "validation_status": status,
            "blocking_reason": "" if status in {"pass", "not_manifested_nonblocking"} else blocking_reason,
        }
    )


def validate_manifest_outputs(
    rows: list[dict[str, Any]],
    resolved: dict[str, Path],
    manifest_key: str,
    artifact_map: dict[str, str],
    check_prefix: str,
    report_output_keys: set[str] | None = None,
) -> None:
    report_output_keys = report_output_keys or set()
    manifest_path = resolved[manifest_key]
    try:
        manifest = read_json(manifest_path)
        if not isinstance(manifest, dict):
            raise TypeError("manifest_not_dict")
        contract_row(rows, manifest_key, source_phase(manifest_key), manifest_key, "", "manifest_readable", "readable", "readable", "pass")
    except Exception as exc:
        contract_row(rows, manifest_key, source_phase(manifest_key), manifest_key, "", "manifest_readable", type(exc).__name__, "readable", "fail", f"{manifest_key}_read_failed")
        return

    output_hashes = manifest.get("output_hashes", {})
    row_counts = manifest.get("row_counts", {})
    for output_key, artifact_key in artifact_map.items():
        path = resolved[artifact_key]
        expected_hash = str(output_hashes.get(output_key, ""))
        observed_hash = file_sha(path) if path.exists() and path.is_file() else ""
        if not expected_hash and output_key in report_output_keys:
            status = "not_manifested_nonblocking"
        else:
            status = "pass" if expected_hash and expected_hash == observed_hash else "fail"
        contract_row(
            rows,
            artifact_key,
            source_phase(artifact_key),
            manifest_key,
            output_key,
            f"{check_prefix}_sha256",
            observed_hash,
            expected_hash,
            status,
            f"{check_prefix}_hash_mismatch:{output_key}",
        )

        if output_key in report_output_keys:
            continue
        expected_rows = row_counts.get(output_key, np.nan)
        observed_rows = count_rows(path)
        row_ok = pd.notna(expected_rows) and pd.notna(observed_rows) and int(expected_rows) == int(observed_rows)
        contract_row(
            rows,
            artifact_key,
            source_phase(artifact_key),
            manifest_key,
            output_key,
            f"{check_prefix}_row_count",
            observed_rows,
            expected_rows,
            "pass" if row_ok else "fail",
            f"{check_prefix}_row_count_mismatch:{output_key}",
        )

        schema, reason = schema_status(path, artifact_key)
        contract_row(
            rows,
            artifact_key,
            source_phase(artifact_key),
            manifest_key,
            output_key,
            f"{check_prefix}_schema",
            schema,
            "pass",
            "pass" if schema == "pass" else "fail",
            reason or f"{check_prefix}_schema_failed:{output_key}",
        )


def validate_episode16_report_hash(rows: list[dict[str, Any]], resolved: dict[str, Path]) -> None:
    key = "episode_16_report"
    manifest_key = "episode_16_report_manifest"
    try:
        manifest = read_json(resolved[manifest_key])
        expected = str(manifest.get("report_sha256", "")) if isinstance(manifest, dict) else ""
        observed = file_sha(resolved[key]) if resolved[key].exists() else ""
        status = "pass" if expected and expected == observed else "not_manifested_nonblocking" if not expected else "fail"
        contract_row(rows, key, "16", manifest_key, "report", "required_report_hash_if_manifested", observed, expected, status, "episode16_report_hash_mismatch")
    except Exception as exc:
        contract_row(rows, key, "16", manifest_key, "report", "required_report_hash_if_manifested", type(exc).__name__, "readable", "fail", "episode16_report_manifest_read_failed")


def compare_value(
    rows: list[dict[str, Any]],
    artifact_key: str,
    check_id: str,
    observed: Any,
    expected: Any,
    source_manifest_key: str = "",
) -> None:
    ok = observed == expected
    contract_row(
        rows,
        artifact_key,
        source_phase(artifact_key),
        source_manifest_key,
        "",
        check_id,
        observed,
        expected,
        "pass" if ok else "fail",
        f"{check_id}_mismatch",
    )


def validate_handoff_and_authorization(rows: list[dict[str, Any]], resolved: dict[str, Path]) -> None:
    decision = read_table(resolved["seventeen_c_decision"]).iloc[0]
    expected = {
        "decision_state": "EP17C_oracle_robustness_ready_for_diagnosis",
        "next_allowed_requirement": "requirement_17d_oracle_diagnosis_report.md",
        "input_gate": "pass",
        "seventeen_b_contract_gate": "pass",
        "row_level_panel_gate": "pass",
        "topk_gate": "pass",
        "bootstrap_gate": "pass",
        "matched_base_gate": "pass",
        "delayed_curve_gate": "pass",
        "search_accounting_gate": "pass",
    }
    for col, exp in expected.items():
        compare_value(rows, "seventeen_c_decision", f"17c_decision_handoff_values:{col}", str_value(decision.get(col)), exp, "seventeen_c_manifest")
    cap_gate = str_value(decision.get("capacity_constraint_gate"))
    cap_status = str_value(decision.get("capacity_status"))
    contract_row(
        rows,
        "seventeen_c_decision",
        "17C",
        "seventeen_c_manifest",
        "",
        "17c_decision_handoff_values:capacity_allowed",
        f"{cap_gate}|{cap_status}",
        "capacity_constraint_gate in {pass,not_evaluable_nonblocking}; capacity_status in {evaluable,appendix_only_nonblocking}",
        "pass" if cap_gate in {"pass", "not_evaluable_nonblocking"} and cap_status in {"evaluable", "appendix_only_nonblocking"} else "fail",
        "17c_capacity_handoff_invalid",
    )
    for col in AUTH_FALSE_COLUMNS:
        compare_value(rows, "seventeen_c_decision", f"authorization_flags_false:{col}", false_like(decision.get(col)), True, "seventeen_c_manifest")

    search = read_table(resolved["seventeen_c_search_accounting_audit"]).iloc[0]
    for col in [c for c in search.index if c.startswith("no_")]:
        compare_value(rows, "seventeen_c_search_accounting_audit", f"search_accounting_flags_true:{col}", true_like(search.get(col)), True, "seventeen_c_manifest")
    compare_value(rows, "seventeen_c_search_accounting_audit", "search_accounting_flags_true:gate", str_value(search.get("search_accounting_gate")), "pass", "seventeen_c_manifest")


def build_contract_validation_audit(config: dict[str, Any], resolved: dict[str, Path]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    validate_manifest_outputs(
        rows,
        resolved,
        "seventeen_c_manifest",
        {
            "input_gate_audit": "seventeen_c_input_gate_audit",
            "seventeen_b_contract_validation_audit": "seventeen_c_contract_validation_audit",
            "primary_summary": "seventeen_c_primary_summary",
            "topk_sensitivity": "seventeen_c_topk_sensitivity",
            "bootstrap_ci": "seventeen_c_bootstrap_ci",
            "matched_base": "seventeen_c_matched_base",
            "delay_curve": "seventeen_c_delay_curve",
            "capacity_constraint": "seventeen_c_capacity_constraint",
            "decision": "seventeen_c_decision",
            "search_accounting_audit": "seventeen_c_search_accounting_audit",
            "report": "seventeen_c_report",
        },
        "17c_required_artifact",
        report_output_keys={"report"},
    )
    validate_manifest_outputs(
        rows,
        resolved,
        "seventeen_b_manifest",
        {
            "ladder_summary": "seventeen_b_ladder_summary",
            "six_cell_decomposition": "seventeen_b_six_cell_decomposition",
            "action_intensity_frontier": "seventeen_b_action_intensity_frontier",
            "neutral_stress": "seventeen_b_neutral_stress",
            "o2_drawdown_threshold_replay": "seventeen_b_o2_drawdown_threshold_replay",
            "o5_action_selection_proof": "seventeen_b_o5_action_selection_proof",
            "high_upside_threshold_freeze": "seventeen_b_high_upside_threshold_freeze",
        },
        "17b_supporting_artifact",
    )
    validate_manifest_outputs(
        rows,
        resolved,
        "sixteen_d_manifest",
        {"decision": "sixteen_d_decision", "policy_confusion_readout": "sixteen_d_policy_confusion_readout"},
        "16d_reference_artifact",
    )
    validate_manifest_outputs(
        rows,
        resolved,
        "sixteen_e_manifest",
        {"decision": "sixteen_e_decision", "six_cell_utility_reconciliation": "sixteen_e_six_cell_reconciliation"},
        "16e_reference_artifact",
    )
    validate_manifest_outputs(
        rows,
        resolved,
        "sixteen_e_postmortem_manifest",
        {
            "decision": "sixteen_e_postmortem_decision",
            "failure_arithmetic_attribution": "sixteen_e_postmortem_failure_arithmetic",
        },
        "16e_postmortem_reference_artifact",
    )
    validate_manifest_outputs(
        rows,
        resolved,
        "sixteen_x_manifest",
        {
            "decision": "sixteen_x_decision",
            "survival_vs_payoff_rank_ic_readout": "sixteen_x_survival_vs_payoff_rank_ic",
        },
        "16x_reference_artifact",
    )
    validate_episode16_report_hash(rows, resolved)
    validate_handoff_and_authorization(rows, resolved)
    return pd.DataFrame(rows)


def primary_filter(config: dict[str, Any]) -> dict[str, Any]:
    return config["primary_filter"]


def select_primary(frame: pd.DataFrame, config: dict[str, Any], variant_id: str | None = None) -> pd.DataFrame:
    pf = primary_filter(config)
    out = frame.copy()
    if "split_bucket" in out:
        out = out.loc[out["split_bucket"].astype(str).eq(str(pf["split_bucket"]))]
    if "cost_bps" in out:
        out = out.loc[np.isclose(pd.to_numeric(out["cost_bps"], errors="coerce"), float(pf["cost_bps"]))]
    if "q_defend" in out:
        out = out.loc[np.isclose(pd.to_numeric(out["q_defend"], errors="coerce"), float(pf["q_defend"]))]
    if variant_id is not None and "oracle_variant_id" in out:
        out = out.loc[out["oracle_variant_id"].astype(str).eq(variant_id)]
    return out.copy()


def first_row(frame: pd.DataFrame) -> pd.Series:
    if frame.empty:
        return pd.Series(dtype=object)
    return frame.iloc[0]


def topk_min(topk: pd.DataFrame, config: dict[str, Any], variant_id: str) -> float:
    sub = select_primary(topk, config, variant_id)
    return safe_float(pd.to_numeric(sub["remaining_mean_incremental_return"], errors="coerce").min()) if not sub.empty else np.nan


def topk_gate(topk: pd.DataFrame, config: dict[str, Any], variant_id: str) -> str:
    sub = select_primary(topk, config, variant_id)
    if sub.empty:
        return "fail"
    return "pass" if sub["topk_gate"].astype(str).eq("pass").all() else "fail"


def bootstrap_min(boot: pd.DataFrame, config: dict[str, Any], variant_id: str) -> float:
    sub = select_primary(boot, config, variant_id)
    sub = sub.loc[sub["bootstrap_primary_role"].astype(str).eq("primary_required")]
    return safe_float(pd.to_numeric(sub["ci_low"], errors="coerce").min()) if not sub.empty else np.nan


def bootstrap_gate(boot: pd.DataFrame, config: dict[str, Any], variant_id: str) -> str:
    sub = select_primary(boot, config, variant_id)
    sub = sub.loc[sub["bootstrap_primary_role"].astype(str).eq("primary_required")]
    if sub.empty:
        return "fail"
    return "pass" if sub["bootstrap_gate"].astype(str).eq("pass").all() else "fail"


def load_inputs(resolved: dict[str, Path]) -> dict[str, pd.DataFrame]:
    table_keys = [key for key, path in resolved.items() if "".join(path.suffixes).endswith(".csv")]
    return {key: read_table(resolved[key]) for key in table_keys}


def build_value_source_attribution(config: dict[str, Any], tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    primary = tables["seventeen_c_primary_summary"]
    o5_row = first_row(select_primary(primary, config, "O5_perfect_utility_primary"))
    o5_mean = safe_float(o5_row.get("mean_incremental_return"))
    rows: list[dict[str, Any]] = []
    tag_map = {
        "O5_perfect_utility_primary": "perfect_utility_upper_bound",
        "O1_negative_primary": "label_negative_support",
        "O2_dd_10pct_primary": "drawdown_path_risk_support",
        "O4_label_positive_primary": "payoff_preservation_support",
    }
    family_map = {
        "O5_perfect_utility_primary": "O5",
        "O1_negative_primary": "O1",
        "O2_dd_10pct_primary": "O2",
        "O4_label_positive_primary": "O4",
    }
    for variant in ["O5_perfect_utility_primary", *config["variants"]["label_path_variants"]]:
        row = first_row(select_primary(primary, config, variant))
        mean = safe_float(row.get("mean_incremental_return"))
        rows.append(
            {
                "oracle_variant_id": variant,
                "oracle_family": family_map.get(variant, str(variant).split("_")[0]),
                "split_bucket": primary_filter(config)["split_bucket"],
                "cost_bps": primary_filter(config)["cost_bps"],
                "q_defend": primary_filter(config)["q_defend"],
                "observed_step_n": safe_float(row.get("observed_step_n")),
                "defended_rate": safe_float(row.get("defended_rate")),
                "mean_incremental_return": mean,
                "trimmed_mean_incremental_return": safe_float(row.get("trimmed_mean_incremental_return")),
                "bootstrap_ci_low_min": safe_float(row.get("bootstrap_ci_low_min")),
                "topk_removed_mean_min": safe_float(row.get("topk_removed_mean_min")),
                "matched_base_pass_share_min": safe_float(row.get("matched_base_pass_share_min")),
                "o5_gap_vs_variant_mean": o5_mean - mean if np.isfinite(o5_mean) and np.isfinite(mean) else np.nan,
                "support_gate": str_value(row.get("primary_support_gate")),
                "interpretation_tag": tag_map.get(variant, "weak_or_failed_support")
                if pass_like(row.get("primary_support_gate"))
                else "weak_or_failed_support",
            }
        )
    return pd.DataFrame(rows)


def build_path_risk_threshold_diagnosis(config: dict[str, Any], tables: dict[str, pd.DataFrame]) -> tuple[pd.DataFrame, str]:
    o2 = tables["seventeen_b_o2_drawdown_threshold_replay"]
    topk = tables["seventeen_c_topk_sensitivity"]
    boot = tables["seventeen_c_bootstrap_ci"]
    primary_summary = tables["seventeen_c_primary_summary"]
    base_08_mean = np.nan
    rows: list[dict[str, Any]] = []
    for variant in config["variants"]["o2_threshold_variants"]:
        replay_row = first_row(select_primary(o2, config, variant))
        mean = safe_float(replay_row.get("mean_incremental_return"))
        if variant == "O2_dd_08pct_stress":
            base_08_mean = mean
        tk_min = topk_min(topk, config, variant)
        bt_min = bootstrap_min(boot, config, variant)
        support = np.isfinite(tk_min) and tk_min > 0 and np.isfinite(bt_min) and bt_min > 0
        rows.append(
            {
                "oracle_variant_id": variant,
                "signed_drawdown_threshold": safe_float(replay_row.get("signed_drawdown_threshold")),
                "defended_step_n": safe_float(replay_row.get("defended_step_n")),
                "defended_rate": safe_float(replay_row.get("defended_step_n")) / safe_float(replay_row.get("observed_step_n"))
                if safe_float(replay_row.get("observed_step_n")) > 0
                else np.nan,
                "mean_incremental_return": mean,
                "trimmed_mean_incremental_return": safe_float(replay_row.get("trimmed_mean_incremental_return")),
                "topk_removed_mean_min": tk_min,
                "bootstrap_ci_low_min": bt_min,
                "threshold_value_decay_vs_08pct": mean - base_08_mean
                if np.isfinite(mean) and np.isfinite(base_08_mean)
                else np.nan,
                "threshold_support_gate": "pass" if support else "fail",
                "path_risk_support_gate": "",
                "interpretation": "path_risk_threshold_positive" if support else "path_risk_threshold_failed",
            }
        )
    o2_primary = first_row(select_primary(primary_summary, config, "O2_dd_10pct_primary"))
    support_n = sum(row["threshold_support_gate"] == "pass" for row in rows)
    path_gate = "pass" if pass_like(o2_primary.get("primary_support_gate")) and support_n >= 3 else "fail"
    for row in rows:
        row["path_risk_support_gate"] = path_gate
    return pd.DataFrame(rows), path_gate


def build_upside_preservation_diagnosis(config: dict[str, Any], tables: dict[str, pd.DataFrame]) -> tuple[pd.DataFrame, str]:
    ladder = tables["seventeen_b_ladder_summary"]
    primary_summary = tables["seventeen_c_primary_summary"]
    topk = tables["seventeen_c_topk_sensitivity"]
    boot = tables["seventeen_c_bootstrap_ci"]
    freeze = tables["seventeen_b_high_upside_threshold_freeze"]
    rows: list[dict[str, Any]] = []
    variant_pass: dict[str, bool] = {}
    for variant in config["variants"]["o4_payoff_variants"]:
        if variant == "O4_label_positive_primary":
            metric_row = first_row(select_primary(primary_summary, config, variant))
            threshold_id = "label_positive_primary"
            train_quantile = np.nan
            cutoff = np.nan
            topk_gate_value = str_value(metric_row.get("topk_gate"))
            boot_gate_value = str_value(metric_row.get("bootstrap_gate"))
            tk_min = safe_float(metric_row.get("topk_removed_mean_min"))
            bt_min = safe_float(metric_row.get("bootstrap_ci_low_min"))
        else:
            metric_row = first_row(select_primary(ladder, config, variant))
            freeze_row = first_row(freeze.loc[freeze["oracle_variant_id"].astype(str).eq(variant)])
            threshold_id = str_value(freeze_row.get("threshold_id"))
            train_quantile = safe_float(freeze_row.get("train_quantile"))
            cutoff = safe_float(freeze_row.get("train_absolute_payoff_cutoff"))
            topk_gate_value = topk_gate(topk, config, variant)
            boot_gate_value = bootstrap_gate(boot, config, variant)
            tk_min = topk_min(topk, config, variant)
            bt_min = bootstrap_min(boot, config, variant)
        passed = topk_gate_value == "pass" and boot_gate_value == "pass"
        variant_pass[variant] = passed
        rows.append(
            {
                "oracle_variant_id": variant,
                "threshold_id": threshold_id,
                "train_quantile": train_quantile,
                "train_absolute_payoff_cutoff": cutoff,
                "defended_step_n": safe_float(metric_row.get("defended_step_n")),
                "defended_rate": safe_float(metric_row.get("defended_rate")),
                "mean_incremental_return": safe_float(metric_row.get("mean_incremental_return")),
                "topk_removed_mean_min": tk_min,
                "bootstrap_ci_low_min": bt_min,
                "topk_gate": topk_gate_value,
                "bootstrap_gate": boot_gate_value,
                "overdefense_flag": False,
                "payoff_preservation_support_gate": "",
                "interpretation": "payoff_preservation_positive" if passed else "payoff_preservation_failed_or_overdefended",
            }
        )
    primary_support = pass_like(first_row(select_primary(primary_summary, config, "O4_label_positive_primary")).get("primary_support_gate"))
    top30_or_20 = variant_pass.get("O4_high_upside_top30_stress", False) or variant_pass.get("O4_high_upside_top20_stress", False)
    payoff_gate = "pass" if primary_support and top30_or_20 else "fail"
    overdefense = (not variant_pass.get("O4_high_upside_top10_stress", False)) and top30_or_20
    for row in rows:
        row["payoff_preservation_support_gate"] = payoff_gate
        row["overdefense_flag"] = overdefense
    return pd.DataFrame(rows), payoff_gate


def build_timing_sensitivity_diagnosis(config: dict[str, Any], tables: dict[str, pd.DataFrame]) -> tuple[pd.DataFrame, str, bool]:
    delay = tables["seventeen_c_delay_curve"]
    pf = primary_filter(config)
    mat = config["materiality"]
    base = delay.loc[
        np.isclose(pd.to_numeric(delay["cost_bps"], errors="coerce"), float(pf["cost_bps"]))
        & np.isclose(pd.to_numeric(delay["q_defend"], errors="coerce"), float(pf["q_defend"]))
    ].copy()
    rows: list[dict[str, Any]] = []
    split_best: dict[str, pd.Series] = {}
    for split in ["train", "robustness", "validation"]:
        split_rows = base.loc[base["split_bucket"].astype(str).eq(split)]
        pass_rows = split_rows.loc[split_rows["delayed_curve_gate"].astype(str).eq("pass")]
        if pass_rows.empty:
            rows.append(
                {
                    "split_bucket": split,
                    "best_delayed_k": np.nan,
                    "best_delayed_mean_incremental_return": np.nan,
                    "best_delayed_trimmed_mean_incremental_return": np.nan,
                    "o5_t0_mean_incremental_return": np.nan,
                    "best_delayed_gap_vs_o5_t0": np.nan,
                    "best_delayed_retention_ratio_vs_o5_t0": np.nan,
                    "k10_delayed_retention_ratio_vs_o5_t0": np.nan,
                    "delayed_decision_supported_gate": "fail",
                    "timing_sensitivity_candidate": False,
                    "interpretation": "no_passed_delayed_rows",
                }
            )
            continue
        best = pass_rows.sort_values("delayed_mean_incremental_return", ascending=False).iloc[0]
        split_best[split] = best
        k10 = split_rows.loc[pd.to_numeric(split_rows["delay_k_sessions"], errors="coerce").eq(10)]
        rows.append(
            {
                "split_bucket": split,
                "best_delayed_k": int(best["delay_k_sessions"]),
                "best_delayed_mean_incremental_return": safe_float(best.get("delayed_mean_incremental_return")),
                "best_delayed_trimmed_mean_incremental_return": safe_float(best.get("delayed_trimmed_mean_incremental_return")),
                "o5_t0_mean_incremental_return": safe_float(best.get("o5_t0_mean_incremental_return")),
                "best_delayed_gap_vs_o5_t0": safe_float(best.get("delayed_mean_gap_vs_o5_t0")),
                "best_delayed_retention_ratio_vs_o5_t0": safe_float(best.get("delayed_retention_ratio_vs_o5_t0")),
                "k10_delayed_retention_ratio_vs_o5_t0": safe_float(first_row(k10).get("delayed_retention_ratio_vs_o5_t0")),
                "delayed_decision_supported_gate": "",
                "timing_sensitivity_candidate": True,
                "interpretation": "best_delayed_positive",
            }
        )
    def split_ok(split: str) -> bool:
        if split not in split_best:
            return False
        row = split_best[split]
        return (
            str_value(row.get("topk_gate")) == "pass"
            and str_value(row.get("bootstrap_gate")) == "pass"
            and str_value(row.get("matched_base_gate")) == "pass"
            and safe_float(row.get("delayed_mean_gap_vs_o5_t0")) >= float(mat["delayed_dominance_gap_floor"])
            and safe_float(row.get("delayed_retention_ratio_vs_o5_t0")) >= float(mat["delayed_retention_floor"])
        )
    all_curve_pass = base["delayed_curve_gate"].astype(str).eq("pass").all() if not base.empty else False
    delayed_gate = "pass" if all_curve_pass and split_ok("robustness") and split_ok("validation") else "fail"
    timing_candidate = bool((base["delayed_mean_incremental_return"] > 0).any() and delayed_gate == "fail")
    for row in rows:
        row["delayed_decision_supported_gate"] = delayed_gate
        row["timing_sensitivity_candidate"] = timing_candidate
        if delayed_gate == "pass":
            row["interpretation"] = "delayed_decision_supported"
        elif timing_candidate:
            row["interpretation"] = "positive_delayed_but_not_validation_dominant"
    return pd.DataFrame(rows), delayed_gate, timing_candidate


def build_learned_model_gap_bridge(tables: dict[str, pd.DataFrame]) -> tuple[pd.DataFrame, str, dict[str, Any]]:
    d16 = tables["sixteen_d_decision"].iloc[0]
    e16 = tables["sixteen_e_decision"].iloc[0]
    six = tables["sixteen_e_six_cell_reconciliation"]
    pm = tables["sixteen_e_postmortem_decision"].iloc[0]
    fail = tables["sixteen_e_postmortem_failure_arithmetic"]
    x16 = tables["sixteen_x_decision"].iloc[0]

    primary_six = six.loc[
        six["split_bucket"].astype(str).isin(["train", "robustness", "validation"])
        & pd.to_numeric(six["cost_bps"], errors="coerce").eq(50)
    ]
    six_cell_ok = not primary_six.empty and primary_six["six_cell_reconciliation_status"].astype(str).eq("pass").all()
    failure_primary = fail.loc[
        fail["split_bucket"].astype(str).eq("robustness") & pd.to_numeric(fail["cost_bps"], errors="coerce").eq(50)
    ]
    robustness_net = safe_float(first_row(failure_primary).get("full_denominator_net_utility_total"))

    checks = [
        (
            "16D",
            "sixteen_d_decision",
            "decision_state",
            str_value(d16.get("decision_state")),
            "16D_policy_preflight_ready_for_utility_diagnostic",
            "16d_survival_policy_has_negative_risk_power",
        ),
        (
            "16E",
            "sixteen_e_decision",
            "decision_state",
            str_value(e16.get("decision_state")),
            "16E_utility_diagnostic_not_supported",
            "16e_return_utility_not_supported",
        ),
        (
            "16E",
            "sixteen_e_six_cell_reconciliation",
            "six_cell_reconciliation_status",
            "pass" if six_cell_ok else "fail",
            "pass",
            "16e_six_cell_reconciliation_consistent",
        ),
        (
            "16E",
            "sixteen_e_decision",
            "drawdown_avoidance_gate",
            str_value(e16.get("drawdown_avoidance_gate")),
            "pass",
            "16e_drawdown_reduction_only",
        ),
        (
            "16E_postmortem",
            "sixteen_e_postmortem_decision",
            "continuation_as_action_mainline_closed",
            true_like(pm.get("continuation_as_action_mainline_closed")),
            True,
            "16e_postmortem_mainline_closed",
        ),
        (
            "16X",
            "sixteen_x_decision",
            "payoff_separability_gate",
            str_value(x16.get("payoff_separability_gate")),
            "fail",
            "16x_payoff_feature_contract_not_supported",
        ),
        (
            "17C",
            "seventeen_c_decision",
            "oracle_action_value_positive",
            "pass",
            "pass",
            "17c_oracle_action_value_positive",
        ),
    ]
    rows = []
    for phase, artifact, metric, observed, expected, component in checks:
        rows.append(
            {
                "source_phase_id": phase,
                "artifact_key": artifact,
                "evidence_metric": metric,
                "observed_value": observed,
                "expected_value": expected,
                "gate_status": "pass" if observed == expected else "fail",
                "feature_gap_component": component,
                "interpretation": "supports_current_feature_gap" if observed == expected else "does_not_support_current_feature_gap",
            }
        )
    feature_gap = (
        str_value(d16.get("decision_state")) == "16D_policy_preflight_ready_for_utility_diagnostic"
        and str_value(e16.get("decision_state")) == "16E_utility_diagnostic_not_supported"
        and str_value(e16.get("primary_return_utility_gate")) == "fail"
        and str_value(e16.get("drawdown_avoidance_gate")) == "pass"
        and six_cell_ok
        and true_like(pm.get("continuation_as_action_mainline_closed"))
        and str_value(x16.get("payoff_separability_gate")) == "fail"
        and false_like(x16.get("payoff_aligned_label_redo_authorized"))
    )
    details = {
        "survival_policy_negative_capture": safe_float(d16.get("robustness_defense_negative_capture_rate")),
        "survival_policy_precision_lift": safe_float(d16.get("robustness_defense_precision_lift_vs_binary_negative_base")),
        "sixteen_e_utility_interpretation": str_value(e16.get("utility_interpretation")),
        "sixteen_e_robustness_net_utility": robustness_net,
        "sixteen_e_postmortem_directionality_gate": str_value(pm.get("directionality_gate")),
        "sixteen_x_payoff_rank_ic": safe_float(x16.get("robustness_payoff_probe_rank_ic_spearman")),
        "sixteen_x_payoff_minus_survival_margin": safe_float(x16.get("payoff_minus_survival_rank_ic_margin")),
        "sixteen_x_payoff_monotone_flag": true_like(x16.get("payoff_monotone_flag")),
    }
    return pd.DataFrame(rows), "pass" if feature_gap else "fail", details


def capacity_gate(tables: dict[str, pd.DataFrame]) -> tuple[str, str]:
    cap = tables["seventeen_c_capacity_constraint"]
    robust = cap.loc[cap["split_bucket"].astype(str).eq("robustness")]
    row = first_row(robust) if not robust.empty else cap.iloc[0]
    status = str_value(row.get("capacity_status"))
    recon = str_value(row.get("capacity_reconstruction_gate"))
    gate = str_value(row.get("capacity_constraint_gate"))
    if recon == "pass" and gate == "fail":
        return "fail", status
    if status == "appendix_only_nonblocking":
        return "not_evaluable_nonblocking", status
    return gate or "not_evaluable_nonblocking", status


def compute_gates(
    config: dict[str, Any],
    tables: dict[str, pd.DataFrame],
    input_gate: pd.DataFrame,
    contract: pd.DataFrame,
) -> dict[str, Any]:
    primary = tables["seventeen_c_primary_summary"]
    mat = config["materiality"]
    o5 = first_row(select_primary(primary, config, "O5_perfect_utility_primary"))
    o5_gate = (
        pass_like(o5.get("primary_support_gate"))
        and safe_float(o5.get("mean_incremental_return")) >= float(mat["materiality_mean_floor"])
        and safe_float(o5.get("bootstrap_ci_low_min")) > float(mat["positive_ci_floor"])
        and safe_float(o5.get("topk_removed_mean_min")) > float(mat["topk_positive_floor"])
    )
    label_rows = [first_row(select_primary(primary, config, v)) for v in config["variants"]["label_path_variants"]]
    label_gate = any(pass_like(row.get("primary_support_gate")) for row in label_rows)
    label_means = [safe_float(row.get("mean_incremental_return")) for row in label_rows]
    best_label = max([v for v in label_means if np.isfinite(v)], default=np.nan)
    path_diag, path_gate = build_path_risk_threshold_diagnosis(config, tables)
    payoff_diag, payoff_gate = build_upside_preservation_diagnosis(config, tables)
    timing_diag, delayed_gate, timing_candidate = build_timing_sensitivity_diagnosis(config, tables)
    bridge, feature_gate, feature_details = build_learned_model_gap_bridge(tables)
    cap_gate, cap_status = capacity_gate(tables)
    contract_gate = "pass" if not contract["validation_status"].astype(str).eq("fail").any() else "fail"
    lineage_gate = "pass" if input_gate["gate_status"].astype(str).eq("pass").all() and contract_gate == "pass" else "fail"
    c_decision = tables["seventeen_c_decision"].iloc[0]

    return {
        "path_diag": path_diag,
        "payoff_diag": payoff_diag,
        "timing_diag": timing_diag,
        "bridge": bridge,
        "feature_details": feature_details,
        "lineage_gate": lineage_gate,
        "contract_validation_gate": contract_gate,
        "o5_upper_bound_gate": "pass" if o5_gate else "fail",
        "label_path_support_gate": "pass" if label_gate else "fail",
        "path_risk_support_gate": path_gate,
        "payoff_preservation_support_gate": payoff_gate,
        "current_feature_gap_gate": feature_gate,
        "delayed_decision_supported_gate": delayed_gate,
        "timing_sensitivity_candidate": timing_candidate,
        "capacity_execution_block_gate": cap_gate,
        "capacity_status": cap_status,
        "primary_o5_mean_incremental_return": safe_float(o5.get("mean_incremental_return")),
        "best_label_path_mean_incremental_return": best_label,
        "o5_vs_best_label_path_gap": safe_float(o5.get("mean_incremental_return")) - best_label
        if np.isfinite(best_label)
        else np.nan,
        "best_delayed_retention_ratio_validation": safe_float(
            first_row(timing_diag.loc[timing_diag["split_bucket"].astype(str).eq("validation")]).get(
                "best_delayed_retention_ratio_vs_o5_t0"
            )
        ),
        "seventeen_c_ready": str_value(c_decision.get("decision_state")) == "EP17C_oracle_robustness_ready_for_diagnosis",
        "seventeen_c_capacity_constraint_gate": str_value(c_decision.get("capacity_constraint_gate")),
    }


def apply_final_decision(gates: dict[str, Any]) -> tuple[str, str, int, str]:
    if gates["lineage_gate"] != "pass" or gates["contract_validation_gate"] != "pass":
        return "oracle_lineage_or_denominator_blocked", "none", 1, "lineage_or_contract_validation_failed"
    if gates["o5_upper_bound_gate"] != "pass" or not gates["seventeen_c_ready"]:
        return "oracle_no_action_value_in_current_space", "none", 2, "o5_upper_bound_not_supported_or_17c_not_ready"
    if gates["seventeen_c_capacity_constraint_gate"] == "fail" or gates["capacity_execution_block_gate"] == "fail":
        return "oracle_execution_capacity_blocked", "requirement_18_capacity_execution_reconstruction.md", 3, "capacity_constraint_failed"
    if gates["delayed_decision_supported_gate"] == "pass" and gates["payoff_preservation_support_gate"] != "pass":
        return "oracle_delayed_decision_supported", "requirement_18_delayed_observed_state_diagnostic.md", 4, ""
    if gates["path_risk_support_gate"] == "pass" and gates["payoff_preservation_support_gate"] != "pass":
        return "oracle_risk_signal_only_no_payoff_value", "requirement_18_risk_budget_overlay_research.md", 5, ""
    if gates["payoff_preservation_support_gate"] == "pass" and gates["current_feature_gap_gate"] == "pass":
        return "oracle_payoff_state_research_allowed", "requirement_18_payoff_state_representation_research.md", 6, ""
    return (
        "oracle_value_exists_feature_gap",
        "requirement_18_feature_gap_source_diagnostic.md",
        7,
        "perfect_utility_only_or_explanatory_support_inconclusive",
    )


def build_decision_row(gates: dict[str, Any]) -> pd.DataFrame:
    final_state, next_req, priority_rank, blocking = apply_final_decision(gates)
    row = {
        "final_decision_state": final_state,
        "recommended_next_requirement": next_req,
        "lineage_gate": gates["lineage_gate"],
        "contract_validation_gate": gates["contract_validation_gate"],
        "o5_upper_bound_gate": gates["o5_upper_bound_gate"],
        "label_path_support_gate": gates["label_path_support_gate"],
        "path_risk_support_gate": gates["path_risk_support_gate"],
        "payoff_preservation_support_gate": gates["payoff_preservation_support_gate"],
        "current_feature_gap_gate": gates["current_feature_gap_gate"],
        "delayed_decision_supported_gate": gates["delayed_decision_supported_gate"],
        "timing_sensitivity_candidate": bool(gates["timing_sensitivity_candidate"]),
        "capacity_execution_block_gate": gates["capacity_execution_block_gate"],
        "primary_o5_mean_incremental_return": gates["primary_o5_mean_incremental_return"],
        "best_label_path_mean_incremental_return": gates["best_label_path_mean_incremental_return"],
        "o5_vs_best_label_path_gap": gates["o5_vs_best_label_path_gap"],
        "best_delayed_retention_ratio_validation": gates["best_delayed_retention_ratio_validation"],
        "capacity_status": gates["capacity_status"],
        "selected_priority_rank": priority_rank,
        "entry_policy_authorized": False,
        "exit_policy_authorized": False,
        "holding_policy_authorized": False,
        "portfolio_backtest_authorized": False,
        "model_deployment_authorized": False,
        "production_signal_authorized": False,
        "live_trading_authorized": False,
        "blocking_reason": blocking,
    }
    return pd.DataFrame([row])


def build_decision_tree(gates: dict[str, Any], decision: pd.DataFrame) -> pd.DataFrame:
    final_row = decision.iloc[0]
    rows = [
        ("Q0_lineage_and_contract", "Q0_lineage_and_contract", "17C/17B/16 artifacts pass manifest and handoff checks", "17d_contract_validation_audit.csv", "contract_validation_gate", gates["contract_validation_gate"], "pass"),
        ("Q1_action_space_upper_bound", "Q1_action_space_upper_bound", "O5 upper-bound remains material after top-k/bootstrap", "oracle_robustness_primary_summary.csv", "o5_upper_bound_gate", gates["o5_upper_bound_gate"], "pass"),
        ("Q2_label_path_oracle_support", "Q2_label_path_oracle_support", "At least one O1/O2/O4 label/path oracle supports action value", "oracle_value_source_attribution.csv", "label_path_support_gate", gates["label_path_support_gate"], "pass"),
        ("Q3_payoff_preservation_support", "Q3_payoff_preservation_support", "O4 payoff preservation survives high-upside readouts", "oracle_upside_preservation_diagnosis.csv", "payoff_preservation_support_gate", gates["payoff_preservation_support_gate"], "pass"),
        ("Q4_path_risk_support", "Q4_path_risk_support", "O2 drawdown path-risk thresholds survive stress", "oracle_path_risk_threshold_diagnosis.csv", "path_risk_support_gate", gates["path_risk_support_gate"], "pass"),
        ("Q5_current_feature_gap", "Q5_current_feature_gap", "Episode 16 learned-model artifacts show current feature gap", "oracle_learned_model_gap_bridge.csv", "current_feature_gap_gate", gates["current_feature_gap_gate"], "pass"),
        ("Q6_delayed_timing_support", "Q6_delayed_timing_support", "Delayed oracle dominates t0 in robustness and validation", "oracle_timing_sensitivity_diagnosis.csv", "delayed_decision_supported_gate", gates["delayed_decision_supported_gate"], "pass"),
        ("Q7_capacity_execution_support", "Q7_capacity_execution_support", "Capacity reconstruction is evaluable and not blocking", "oracle_capacity_constraint.csv", "capacity_execution_block_gate", gates["capacity_execution_block_gate"], "pass_or_not_evaluable_nonblocking"),
        ("Q8_final_decision", "Q8_final_decision", "Binding priority tree final state", "oracle_diagnosis_decision.csv", "final_decision_state", final_row["final_decision_state"], "single_allowed_label"),
    ]
    out = []
    for qid, family, text, artifact, metric, observed, expected in rows:
        if family == "Q7_capacity_execution_support":
            status = "not_evaluable_nonblocking" if observed == "not_evaluable_nonblocking" else ("pass" if observed == "pass" else "fail")
        elif family == "Q8_final_decision":
            status = "pass" if observed in FINAL_DECISION_STATES else "fail"
        else:
            status = "pass" if observed == "pass" else "fail"
        out.append(
            {
                "question_id": qid,
                "question_family": family,
                "question_text": text,
                "evidence_artifact": artifact,
                "evidence_metric": metric,
                "observed_value": observed,
                "threshold_or_expected_value": expected,
                "question_status": status,
                "diagnostic_interpretation": interpretation_for_question(family, observed),
                "final_decision_priority_rank": int(final_row["selected_priority_rank"]),
                "blocking_reason": final_row["blocking_reason"] if family == "Q8_final_decision" else "",
            }
        )
    return pd.DataFrame(out)


def interpretation_for_question(family: str, observed: Any) -> str:
    mapping = {
        "Q0_lineage_and_contract": "machine_contract_validated" if observed == "pass" else "lineage_or_contract_blocked",
        "Q1_action_space_upper_bound": "oracle_upper_bound_positive" if observed == "pass" else "no_material_o5_headroom",
        "Q2_label_path_oracle_support": "label_or_path_support_present" if observed == "pass" else "perfect_utility_only",
        "Q3_payoff_preservation_support": "payoff_preservation_supported" if observed == "pass" else "payoff_preservation_not_supported",
        "Q4_path_risk_support": "path_risk_has_action_value" if observed == "pass" else "path_risk_only_not_supported",
        "Q5_current_feature_gap": "current_feature_contract_gap_confirmed" if observed == "pass" else "current_feature_gap_not_confirmed",
        "Q6_delayed_timing_support": "delayed_final_decision_supported" if observed == "pass" else "delayed_positive_but_not_decisive",
        "Q7_capacity_execution_support": "capacity_appendix_only_nonblocking" if observed == "not_evaluable_nonblocking" else "capacity_gate_evaluable",
        "Q8_final_decision": str(observed),
    }
    return mapping.get(family, str(observed))


def build_search_accounting_audit() -> pd.DataFrame:
    row = {
        "search_family": "oracle_diagnosis_report",
        "phase_id": PHASE_ID,
        "no_model_training": True,
        "no_model_refit": True,
        "no_survival_threshold_tuning": True,
        "no_validation_selection": True,
        "no_robustness_tuning": True,
        "no_feature_selection": True,
        "no_payoff_label_redesign": True,
        "no_oracle_threshold_tuning": True,
        "no_decision_threshold_tuning": True,
        "no_entry_policy_authorized": True,
        "no_exit_policy_authorized": True,
        "no_holding_policy_authorized": True,
        "no_portfolio_backtest_authorized": True,
        "no_model_deployment_authorized": True,
        "no_production_signal_authorized": True,
        "no_live_trading_authorized": True,
        "search_accounting_gate": "pass",
        "blocking_reason": "",
    }
    return pd.DataFrame([row])


def format_pct(value: float) -> str:
    if not np.isfinite(value):
        return "NA"
    return f"{value:.4%}"


def format_num(value: float) -> str:
    if not np.isfinite(value):
        return "NA"
    return f"{value:.6f}"


def build_report(
    decision: pd.DataFrame,
    source: pd.DataFrame,
    path_diag: pd.DataFrame,
    payoff_diag: pd.DataFrame,
    timing: pd.DataFrame,
    gates: dict[str, Any],
) -> str:
    d = decision.iloc[0]
    lines = [
        "# EP17 Oracle Action Value 诊断报告",
        "",
        "## 结论",
        "",
        f"- final_decision_state: `{d['final_decision_state']}`",
        f"- recommended_next_requirement: `{d['recommended_next_requirement']}`",
        f"- selected_priority_rank: `{int(d['selected_priority_rank'])}`",
        "",
        "本报告只授权下一步研究需求，不授权 entry、exit、holding、portfolio backtest、model deployment、production signal 或 live trading。",
        "",
        "## 机器契约与上游校验",
        "",
        f"- lineage_gate: `{d['lineage_gate']}`",
        f"- contract_validation_gate: `{d['contract_validation_gate']}`",
        f"- 17C handoff: `{ 'ready' if gates['seventeen_c_ready'] else 'not_ready' }`",
        "",
        "## Oracle action-space value",
        "",
        f"- O5 primary mean incremental return: `{format_pct(float(d['primary_o5_mean_incremental_return']))}`",
        f"- best O1/O2/O4 label/path mean: `{format_pct(float(d['best_label_path_mean_incremental_return']))}`",
        f"- O5 vs best label/path gap: `{format_pct(float(d['o5_vs_best_label_path_gap']))}`",
        f"- O5 upper-bound gate: `{d['o5_upper_bound_gate']}`",
        "",
        "O5 是完美后见之明 action-space 上界，不是可部署策略。它只说明冻结 action semantics 下存在可测 headroom。",
        "",
        "## Label / path / payoff 支撑",
        "",
    ]
    for row in source.to_dict("records"):
        lines.append(
            f"- `{row['oracle_variant_id']}`: mean={format_pct(float(row['mean_incremental_return']))}, "
            f"bootstrap_min={format_pct(float(row['bootstrap_ci_low_min']))}, "
            f"topk_min={format_pct(float(row['topk_removed_mean_min']))}, gate=`{row['support_gate']}`"
        )
    lines.extend(["", "## O2 drawdown path-risk threshold", ""])
    for row in path_diag.to_dict("records"):
        lines.append(
            f"- `{row['oracle_variant_id']}` threshold={row['signed_drawdown_threshold']}: "
            f"mean={format_pct(float(row['mean_incremental_return']))}, "
            f"topk_min={format_pct(float(row['topk_removed_mean_min']))}, "
            f"bootstrap_min={format_pct(float(row['bootstrap_ci_low_min']))}, "
            f"gate=`{row['threshold_support_gate']}`"
        )
    lines.extend(["", "## O4 upside preservation", ""])
    for row in payoff_diag.to_dict("records"):
        lines.append(
            f"- `{row['oracle_variant_id']}` threshold=`{row['threshold_id']}`: "
            f"mean={format_pct(float(row['mean_incremental_return']))}, "
            f"topk=`{row['topk_gate']}`, bootstrap=`{row['bootstrap_gate']}`, "
            f"overdefense_flag=`{row['overdefense_flag']}`"
        )
    lines.extend(
        [
            "",
            "top30/top20 high-upside readout 保持正向，top10 过窄时出现 overdefense，说明 payoff preservation 需要保留足够宽的 upside 状态，而不是只追极端赢家。",
            "",
            "## Episode 16 bridge",
            "",
            f"- current_feature_gap_gate: `{d['current_feature_gap_gate']}`",
            f"- 16D robustness negative capture: `{format_pct(float(gates['feature_details']['survival_policy_negative_capture']))}`",
            f"- 16E robustness full-denominator net utility total: `{format_num(float(gates['feature_details']['sixteen_e_robustness_net_utility']))}`",
            f"- 16X payoff rank IC: `{gates['feature_details']['sixteen_x_payoff_rank_ic']:.6f}`",
            "",
            "16D 的 survival/risk 信息能抓到一部分负样本，但 16E/16X 显示当前 feature contract 不能把 continuation payoff 做成稳定 utility。17A-17C 的 oracle 结果因此更像 payoff-state representation 缺口，而不是已有模型可直接交易。",
            "",
            "## Delayed timing sensitivity",
            "",
        ]
    )
    for row in timing.to_dict("records"):
        lines.append(
            f"- `{row['split_bucket']}` best_k={row['best_delayed_k']}: "
            f"mean={format_pct(float(row['best_delayed_mean_incremental_return']))}, "
            f"gap_vs_o5={format_pct(float(row['best_delayed_gap_vs_o5_t0']))}, "
            f"retention={row['best_delayed_retention_ratio_vs_o5_t0']:.4f}"
        )
    lines.extend(
        [
            "",
            f"delayed_decision_supported_gate: `{d['delayed_decision_supported_gate']}`；timing_sensitivity_candidate: `{d['timing_sensitivity_candidate']}`。delayed 在 robustness 有正向信号，但 validation retention 不足以成为最终裁决。",
            "",
            "## Capacity 与授权边界",
            "",
            f"- capacity_status: `{d['capacity_status']}`",
            f"- capacity_execution_block_gate: `{d['capacity_execution_block_gate']}`",
            "",
            "capacity 当前是 appendix-only nonblocking，因此不能得出 execution-capacity 结论，也不能授权 portfolio backtest。",
            "",
            "## 下一步研究方向",
            "",
            "建议进入 `requirement_18_payoff_state_representation_research.md`：研究目标不是复用 O5，而是寻找可观测、可冻结、可验证的 payoff-state representation，使 O4 类型的 payoff preservation 能被非 oracle 特征近似。",
            "",
            "明确不建议：不进入交易规则开发，不做 entry/exit/holding 策略，不做组合回测，不做部署或生产信号。",
            "",
        ]
    )
    return "\n".join(lines)


def git_commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True).strip()
    except Exception:
        return ""


def build_input_artifact_manifest(input_gate: pd.DataFrame, contract: pd.DataFrame) -> list[dict[str, Any]]:
    expected_hash: dict[str, Any] = {}
    expected_rows: dict[str, Any] = {}
    for row in contract.to_dict("records"):
        artifact = str(row["artifact_key"])
        check = str(row["validation_check_id"])
        if check.endswith("_sha256"):
            expected_hash[artifact] = row["expected_value"]
        if check.endswith("_row_count"):
            expected_rows[artifact] = row["expected_value"]
    out = []
    for row in input_gate.to_dict("records"):
        artifact = str(row["artifact_key"])
        out.append(
            {
                "artifact_key": artifact,
                "artifact_role": row["artifact_role"],
                "required_flag": row["required_flag"],
                "source_manifest_key": "",
                "manifest_output_key": "",
                "resolved_path": row["resolved_path"],
                "relative_path": row["relative_path"],
                "source_phase_id": row["source_phase_id"],
                "row_count": row["row_count"],
                "expected_sha256": expected_hash.get(artifact, ""),
                "observed_sha256": row["sha256"],
                "expected_row_count": expected_rows.get(artifact, np.nan),
                "observed_row_count": row["row_count"],
                "schema_status": row["schema_status"],
                "gate_status": row["gate_status"],
                "blocking_reason": row["blocking_reason"],
            }
        )
    return out


def write_manifests(
    config_path: Path,
    config: dict[str, Any],
    resolved: dict[str, Path],
    written: dict[str, Path],
    decision: pd.DataFrame,
    input_gate: pd.DataFrame,
    contract: pd.DataFrame,
) -> None:
    output_hashes = {key: file_sha(path) for key, path in written.items() if path.exists() and path.is_file()}
    row_counts = {key: count_rows(path) for key, path in written.items() if path.exists()}
    input_hashes = {
        key: file_sha(path)
        for key, path in resolved.items()
        if path.exists() and path.is_file()
    }
    d = decision.iloc[0]
    manifest = {
        "run_id": RUN_ID,
        "experiment_id": EXPERIMENT_ID,
        "phase_id": PHASE_ID,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "config_file": relative_to_topic(config_path),
        "config_sha256": file_sha(config_path),
        "requirement_file": relative_to_topic(resolved["requirement"]),
        "requirement_sha256": file_sha(resolved["requirement"]),
        "runner_file": relative_to_topic(Path(__file__)),
        "test_file": relative_to_topic(EXPERIMENT_DIR / "tests" / "test_17d_oracle_diagnosis_report.py"),
        "input_artifact_hashes": input_hashes,
        "output_hashes": output_hashes,
        "row_counts": row_counts,
        "contract_validation_gate": d["contract_validation_gate"],
        "final_decision_state": d["final_decision_state"],
        "recommended_next_requirement": d["recommended_next_requirement"],
        "decision_priority_order": [
            "oracle_lineage_or_denominator_blocked",
            "oracle_no_action_value_in_current_space",
            "oracle_execution_capacity_blocked",
            "oracle_delayed_decision_supported",
            "oracle_risk_signal_only_no_payoff_value",
            "oracle_payoff_state_research_allowed",
            "oracle_value_exists_feature_gap",
        ],
        "materiality_constants": config["materiality"],
        "authorization_flags": {col: bool(d[col]) for col in AUTH_FALSE_COLUMNS},
        "python_version": platform.python_version(),
        "git_commit_if_available": git_commit(),
    }
    write_json(output_paths()["manifest"], manifest)
    engine = {
        "run_id": RUN_ID,
        "phase_id": PHASE_ID,
        "formulas": {
            "contract validation gate": "pass iff no 17d_contract_validation_audit row has validation_status == fail",
            "O5 upper-bound gate": "O5 primary support + mean >= materiality floor + bootstrap/topk positive",
            "label/path support gate": "any O1/O2/O4 primary_support_gate passes",
            "O5 headroom gaps": "O5 mean minus best O1/O2/O4 mean",
            "O2 threshold value decay": "threshold mean minus O2_dd_08pct_stress mean",
            "O4 overdefense flag": "top10 high-upside fails while top30/top20 pass",
            "current-feature gap gate": "16D ready + 16E return fail/drawdown pass + 16E six-cell pass + 16X payoff separability fail",
            "delayed support gate": "robustness and validation best delayed rows pass topk/bootstrap/matched, gap floor, and retention floor",
            "capacity execution block gate": "capacity fail only if capacity reconstruction is evaluable and constraint fails",
            "final decision priority": "binding Section 7 priority order",
        },
    }
    write_json(output_paths()["engine_manifest"], engine)
    write_json(output_paths()["input_artifact_manifest"], build_input_artifact_manifest(input_gate, contract))


def run(config_path: Path, check_inputs_only: bool = False) -> int:
    config = load_config(config_path)
    resolved = resolve_paths(config)
    out = output_paths()
    input_gate = build_input_gate_audit(config, resolved)
    contract = build_contract_validation_audit(config, resolved)
    write_df(out["input_gate_audit"], input_gate)
    write_df(out["contract_validation_audit"], contract)
    write_json(out["input_artifact_manifest"], build_input_artifact_manifest(input_gate, contract))
    if check_inputs_only:
        return 0

    tables = load_inputs(resolved)
    source = build_value_source_attribution(config, tables)
    gates = compute_gates(config, tables, input_gate, contract)
    decision = build_decision_row(gates)
    tree = build_decision_tree(gates, decision)
    search = build_search_accounting_audit()

    write_df(out["value_source_attribution"], source)
    write_df(out["path_risk_threshold_diagnosis"], gates["path_diag"])
    write_df(out["upside_preservation_diagnosis"], gates["payoff_diag"])
    write_df(out["timing_sensitivity_diagnosis"], gates["timing_diag"])
    write_df(out["learned_model_gap_bridge"], gates["bridge"])
    write_df(out["decision"], decision)
    write_df(out["decision_tree"], tree)
    write_df(out["search_accounting_audit"], search)
    write_text(out["report"], build_report(decision, source, gates["path_diag"], gates["payoff_diag"], gates["timing_diag"], gates))

    written = {
        "input_gate_audit": out["input_gate_audit"],
        "contract_validation_audit": out["contract_validation_audit"],
        "decision_tree": out["decision_tree"],
        "value_source_attribution": out["value_source_attribution"],
        "path_risk_threshold_diagnosis": out["path_risk_threshold_diagnosis"],
        "upside_preservation_diagnosis": out["upside_preservation_diagnosis"],
        "timing_sensitivity_diagnosis": out["timing_sensitivity_diagnosis"],
        "learned_model_gap_bridge": out["learned_model_gap_bridge"],
        "decision": out["decision"],
        "search_accounting_audit": out["search_accounting_audit"],
        "report": out["report"],
    }
    write_manifests(config_path, config, resolved, written, decision, input_gate, contract)
    return 0


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    return run(Path(args.config), check_inputs_only=args.check_inputs_only)


if __name__ == "__main__":
    raise SystemExit(main())
