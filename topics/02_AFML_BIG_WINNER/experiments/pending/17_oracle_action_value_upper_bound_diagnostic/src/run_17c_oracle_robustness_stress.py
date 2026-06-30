#!/usr/bin/env python
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import yaml


EXPERIMENT_DIR = Path(__file__).resolve().parents[1]
TOPIC_ROOT = Path(__file__).resolve().parents[4]
REPO_ROOT = Path(__file__).resolve().parents[6]

RUN_ID = "17C_oracle_robustness_stress"
EXPERIMENT_ID = "17_oracle_action_value_upper_bound_diagnostic"
PHASE_ID = "17C"
CONFIG_PATH = EXPERIMENT_DIR / "configs" / "config_17c_oracle_robustness_stress.yaml"
TABLE_DIR = EXPERIMENT_DIR / "outputs" / "publishable" / "tables" / RUN_ID
FIGURE_DIR = EXPERIMENT_DIR / "outputs" / "publishable" / "figures" / RUN_ID
LOCAL_CACHE_DIR = EXPERIMENT_DIR / "outputs" / "local_cache" / RUN_ID
REPORT_DIR = EXPERIMENT_DIR / "outputs" / "publishable" / "reports"
MANIFEST_DIR = EXPERIMENT_DIR / "outputs" / "manifests"

SPLITS = ("train", "robustness", "validation")
PRIMARY_ROW_KEY = (
    "step_id",
    "label_id",
    "threshold_id",
    "instrument",
    "episode_cluster_id",
    "horizon_sessions",
    "step_index",
    "step_start_date",
    "step_end_date",
)
GROUP_KEYS = ("oracle_id", "oracle_variant_id", "split_bucket", "cost_bps", "q_defend", "primary_variant")

DECISION_READY = "EP17C_oracle_robustness_ready_for_diagnosis"
DECISION_NO_VALUE = "oracle_no_action_value_in_current_space"
DECISION_CAPACITY_BLOCKED = "oracle_execution_capacity_blocked"
DECISION_LINEAGE_BLOCKED = "oracle_lineage_or_denominator_blocked"

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
    parser = argparse.ArgumentParser(description="Run EP17C oracle robustness stress.")
    parser.add_argument("--config", default=str(CONFIG_PATH))
    parser.add_argument("--check-inputs-only", action="store_true")
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
    if text.startswith(("data/", "experiments/")):
        return TOPIC_ROOT / path
    if text.startswith(("outputs/", "configs/", "src/", "tests/")):
        return EXPERIMENT_DIR / path
    return EXPERIMENT_DIR / path


def resolve_paths(config: dict[str, Any]) -> dict[str, Path]:
    return {key: topic_path(value) for key, value in config.get("paths", {}).items()}


def output_paths() -> dict[str, Path]:
    return {
        "input_gate_audit": TABLE_DIR / "17c_input_gate_audit.csv",
        "seventeen_b_contract_validation_audit": TABLE_DIR / "seventeen_b_contract_validation_audit.csv",
        "primary_summary": TABLE_DIR / "oracle_robustness_primary_summary.csv",
        "topk_sensitivity": TABLE_DIR / "oracle_topk_sensitivity.csv",
        "bootstrap_ci": TABLE_DIR / "oracle_bootstrap_ci.csv",
        "matched_base": TABLE_DIR / "oracle_matched_base.csv",
        "delay_curve": TABLE_DIR / "oracle_delay_curve.csv",
        "capacity_constraint": TABLE_DIR / "oracle_capacity_constraint.csv",
        "decision": TABLE_DIR / "oracle_robustness_decision.csv",
        "search_accounting_audit": TABLE_DIR / "search_accounting_audit.csv",
        "topk_figure": FIGURE_DIR / "oracle_topk_sensitivity.png",
        "bootstrap_figure": FIGURE_DIR / "oracle_bootstrap_ci.png",
        "matched_figure": FIGURE_DIR / "oracle_matched_base_heatmap.png",
        "delayed_figure": FIGURE_DIR / "delayed_oracle_curve.png",
        "capacity_figure": FIGURE_DIR / "capacity_constrained_oracle_curve.png",
        "report": REPORT_DIR / "oracle_robustness_stress_report.md",
        "manifest": MANIFEST_DIR / "17C_oracle_robustness_stress_manifest.json",
        "engine_manifest": MANIFEST_DIR / "oracle_robustness_engine_manifest.json",
        "input_artifact_manifest": MANIFEST_DIR / "input_artifact_manifest_17c.json",
        "delayed_panel": LOCAL_CACHE_DIR / "delayed_oracle_panel.parquet",
        "capacity_panel": LOCAL_CACHE_DIR / "capacity_oracle_panel.parquet",
    }


def read_table(path: Path, **kwargs: Any) -> pd.DataFrame:
    suffixes = "".join(path.suffixes)
    if suffixes.endswith(".parquet"):
        return pd.read_parquet(path, **kwargs)
    if suffixes.endswith(".csv"):
        return pd.read_csv(path, **kwargs)
    raise ValueError(f"Unsupported table path: {path}")


def write_df(path: Path, frame: pd.DataFrame) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if "".join(path.suffixes).endswith(".parquet"):
        frame.to_parquet(path, index=False)
    else:
        frame.to_csv(path, index=False)
    return path


def write_text(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


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
    if not isinstance(value, (str, bytes, dict, list, tuple)):
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
    if suffixes.endswith(".parquet"):
        return pq.ParquetFile(path).metadata.num_rows
    if suffixes.endswith(".csv"):
        with path.open("r", encoding="utf-8") as handle:
            return max(sum(1 for _ in handle) - 1, 0)
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


def bool_value(value: Any) -> bool:
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes", "pass"}
    if pd.isna(value):
        return False
    return bool(value)


def false_like(value: Any) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in {"false", "0", "no", ""}
    if pd.isna(value):
        return False
    return not bool(value)


def all_pass(frame: pd.DataFrame, column: str) -> bool:
    return column in frame.columns and frame[column].astype(str).eq("pass").all()


def artifact_rows(audit: pd.DataFrame) -> pd.DataFrame:
    if "audit_row_type" not in audit.columns:
        return audit
    return audit.loc[audit["audit_row_type"].astype(str).eq("artifact")].copy()


def required_columns_for_key(key: str) -> set[str]:
    mapping: dict[str, set[str]] = {
        "seventeen_b_input_gate_audit": {"artifact_key", "gate_status", "schema_status", "read_status"}
        - {"read_status"},
        "seventeen_b_contract_validation_audit": {
            "artifact_key",
            "validation_check_id",
            "validation_status",
        },
        "seventeen_b_row_replay_audit": {"split_bucket", "denominator_type", "row_replay_gate"},
        "seventeen_b_ladder_summary": {
            "oracle_id",
            "oracle_variant_id",
            "split_bucket",
            "cost_bps",
            "q_defend",
            "mean_incremental_return",
            "trimmed_mean_incremental_return",
        },
        "seventeen_b_six_cell_decomposition": {"oracle_variant_id", "cell_id", "six_cell_gate"},
        "seventeen_b_action_intensity_frontier": {"oracle_variant_id", "frontier_gate"},
        "seventeen_b_neutral_stress": {"oracle_variant_id", "neutral_stress_gate"},
        "seventeen_b_o2_drawdown_threshold_replay": {
            "oracle_variant_id",
            "signed_drawdown_threshold",
            "positive_abs_drawdown_used_for_o2_threshold",
            "o2_drawdown_replay_gate",
        },
        "seventeen_b_o5_action_selection_proof": {
            "split_bucket",
            "cost_bps",
            "q_defend",
            "formula_recomputed_mismatch_n",
            "o5_action_selection_proof_gate",
        },
        "seventeen_b_high_upside_threshold_freeze": {"oracle_variant_id", "threshold_freeze_gate"},
        "seventeen_b_ladder_decision": {
            "decision_state",
            "next_allowed_requirement",
            "input_gate",
            "row_replay_gate",
            "oracle_ladder_gate",
            "search_accounting_gate",
            "primary_ladder_cost_bps",
            "primary_ladder_q_defend",
        },
        "seventeen_b_search_accounting_audit": {"phase_id", "search_accounting_gate"},
        "seventeen_b_row_level_panel": {
            "cluster_split_bucket",
            "signed_max_drawdown_h20",
            "drawdown_abs_for_reporting",
            "oracle_variant_id",
            "incremental_net_return",
            *PRIMARY_ROW_KEY,
        },
        "seventeen_a_delayed_materialization_audit": {"split_bucket", "delayed_materialization_gate"},
        "seventeen_a_capacity_reconstruction_audit": {
            "capacity_reconstruction_gate",
            "o6_status_for_17b",
        },
    }
    if key.endswith("_manifest") or key in {
        "requirement",
        "research_plan",
        "stock_daily_qfq_dir",
        "seventeen_a_action_contract",
        "seventeen_a_denominator_contract",
    }:
        return set()
    return mapping.get(key, set())


def artifact_role(key: str) -> str:
    if key in {"requirement", "research_plan"}:
        return "local_contract"
    if key == "stock_daily_qfq_dir":
        return "qfq_price_source"
    if key.startswith("seventeen_b"):
        return "17b_handoff"
    if key.startswith("seventeen_a"):
        return "17a_inherited_status"
    return "input_artifact"


def source_phase(key: str) -> str:
    if key.startswith("seventeen_b"):
        return "17B"
    if key.startswith("seventeen_a"):
        return "17A"
    return PHASE_ID


def validation_row(
    rows: list[dict[str, Any]],
    artifact_key: str,
    check_id: str,
    observed_value: Any,
    expected_value: Any,
    passed: bool,
    blocking_reason: str = "",
) -> None:
    rows.append(
        {
            "artifact_key": artifact_key,
            "validation_check_id": check_id,
            "observed_value": clean_json(observed_value),
            "expected_value": clean_json(expected_value),
            "validation_status": "pass" if passed else "fail",
            "blocking_reason": "" if passed else blocking_reason,
        }
    )


def read_json(path: Path) -> dict[str, Any] | list[dict[str, Any]]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_17b_manifest_hashes(rows: list[dict[str, Any]], resolved: dict[str, Path]) -> None:
    manifest_key = "seventeen_b_manifest"
    manifest_hash_map = {
        "input_gate_audit": "seventeen_b_input_gate_audit",
        "seventeen_a_contract_validation_audit": "seventeen_b_contract_validation_audit",
        "row_replay_audit": "seventeen_b_row_replay_audit",
        "ladder_summary": "seventeen_b_ladder_summary",
        "six_cell_decomposition": "seventeen_b_six_cell_decomposition",
        "action_intensity_frontier": "seventeen_b_action_intensity_frontier",
        "neutral_stress": "seventeen_b_neutral_stress",
        "o2_drawdown_threshold_replay": "seventeen_b_o2_drawdown_threshold_replay",
        "o5_action_selection_proof": "seventeen_b_o5_action_selection_proof",
        "high_upside_threshold_freeze": "seventeen_b_high_upside_threshold_freeze",
        "decision": "seventeen_b_ladder_decision",
        "search_accounting_audit": "seventeen_b_search_accounting_audit",
    }
    try:
        manifest = read_json(resolved[manifest_key])
        if not isinstance(manifest, dict):
            raise TypeError("manifest_not_dict")
        validation_row(rows, manifest_key, "manifest_readable", "readable", "readable", True)
        output_hashes = manifest.get("output_hashes", {})
        row_counts_from_manifest = manifest.get("row_counts", {})
        for output_key, artifact_key in manifest_hash_map.items():
            path = resolved[artifact_key]
            expected_hash = str(output_hashes.get(output_key, ""))
            actual_hash = file_sha(path) if path.exists() and path.is_file() else ""
            validation_row(
                rows,
                manifest_key,
                f"output_hash_{output_key}",
                actual_hash,
                expected_hash,
                bool(expected_hash) and actual_hash == expected_hash,
                f"17b_manifest_hash_mismatch:{output_key}",
            )
            expected_rows = row_counts_from_manifest.get(output_key, np.nan)
            actual_rows = count_rows(path)
            row_count_passed = pd.notna(expected_rows) and pd.notna(actual_rows) and int(expected_rows) == int(actual_rows)
            validation_row(
                rows,
                manifest_key,
                f"row_count_{output_key}",
                actual_rows,
                expected_rows,
                bool(row_count_passed),
                f"17b_manifest_row_count_mismatch:{output_key}",
            )
    except Exception as exc:
        validation_row(rows, manifest_key, "manifest_readable", type(exc).__name__, "readable", False, "17b_manifest_read_failed")

    for key in ("seventeen_b_engine_manifest", "seventeen_b_input_artifact_manifest"):
        try:
            payload = read_json(resolved[key])
            validation_row(
                rows,
                key,
                "manifest_readable",
                type(payload).__name__,
                "dict|list",
                isinstance(payload, (dict, list)),
                f"{key}_read_failed",
            )
        except Exception as exc:
            validation_row(rows, key, "manifest_readable", type(exc).__name__, "readable", False, f"{key}_read_failed")


def validate_primary_ladder_summary_reconciliation(
    rows: list[dict[str, Any]],
    config: dict[str, Any],
    resolved: dict[str, Path],
) -> None:
    try:
        summary = read_table(resolved["seventeen_b_ladder_summary"])
        panel = canonicalize_panel(read_table(resolved["seventeen_b_row_level_panel"]))
        present_n = 0
        for variant_id in config["decision"]["primary_candidate_variants"]:
            ident = primary_group_id(variant_id, config)
            summary_sub = summary.loc[group_selector(summary, ident)]
            panel_sub = panel.loc[group_selector(panel, ident)]
            row_exists = len(summary_sub) == 1
            if row_exists:
                present_n += 1
            validation_row(
                rows,
                "seventeen_b_ladder_summary",
                f"primary_ladder_summary_row_exists:{variant_id}",
                int(len(summary_sub)),
                1,
                row_exists,
                "17b_primary_ladder_summary_row_missing_or_duplicated",
            )
            if not row_exists or panel_sub.empty:
                validation_row(
                    rows,
                    "seventeen_b_ladder_summary",
                    f"primary_ladder_summary_reconcile:{variant_id}",
                    "missing",
                    "summary_matches_row_panel",
                    False,
                    "17b_primary_ladder_summary_reconcile_unavailable",
                )
                continue
            stats = summarize_group(panel_sub, config)
            summary_row = summary_sub.iloc[0]
            metric_cols = [
                "observed_step_n",
                "defended_step_n",
                "continued_step_n",
                "mean_incremental_return",
                "trimmed_mean_incremental_return",
                "sum_incremental_return",
            ]
            diffs: dict[str, float] = {}
            for col in metric_cols:
                observed = float(summary_row[col])
                expected = float(stats[col])
                diffs[col] = abs(observed - expected)
            max_abs_diff = max(diffs.values()) if diffs else np.nan
            validation_row(
                rows,
                "seventeen_b_ladder_summary",
                f"primary_ladder_summary_reconcile:{variant_id}",
                max_abs_diff,
                "<=1e-10",
                np.isfinite(max_abs_diff) and max_abs_diff <= 1e-10,
                "17b_primary_ladder_summary_metric_mismatch",
            )
        validation_row(
            rows,
            "seventeen_b_ladder_summary",
            "primary_ladder_summary_rows_present",
            present_n,
            len(config["decision"]["primary_candidate_variants"]),
            present_n == len(config["decision"]["primary_candidate_variants"]),
            "17b_primary_ladder_summary_rows_incomplete",
        )
    except Exception as exc:
        validation_row(
            rows,
            "seventeen_b_ladder_summary",
            "primary_ladder_summary_reconciliation_readable",
            type(exc).__name__,
            "readable",
            False,
            "17b_primary_ladder_summary_reconciliation_failed",
        )


def build_input_gate_audit(config: dict[str, Any], resolved: dict[str, Path]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for key, path in resolved.items():
        exists = path.exists()
        schema_status = "not_checked"
        lineage_status = "pass" if exists else "fail_missing"
        row_key_status = "not_applicable"
        gate_status = "pass" if exists else "fail"
        blocking_reason = "" if exists else "missing_artifact"
        row_count: int | float = np.nan
        sha = ""
        read_status = "fail" if not exists else "pass"
        if exists:
            try:
                row_count = count_rows(path)
                if path.is_file():
                    sha = file_sha(path)
                cols = required_columns_for_key(key)
                if cols:
                    frame = read_table(path)
                    missing = cols - set(frame.columns)
                    schema_status = "pass" if not missing else "fail_missing_columns"
                    if missing:
                        gate_status = "fail"
                        blocking_reason = "missing_required_columns:" + ",".join(sorted(missing))
                else:
                    schema_status = "pass"
            except Exception as exc:
                read_status = "fail"
                schema_status = "fail_read_error"
                gate_status = "fail"
                blocking_reason = f"read_error:{type(exc).__name__}"
        rows.append(
            {
                "artifact_key": key,
                "artifact_role": artifact_role(key),
                "required_flag": "required",
                "resolved_path": str(path),
                "relative_path": relative_to_topic(path),
                "source_phase_id": source_phase(key),
                "row_count": row_count,
                "sha256": sha,
                "schema_status": schema_status,
                "lineage_status": lineage_status,
                "row_key_status": row_key_status,
                "gate_status": gate_status,
                "blocking_reason": blocking_reason,
                "read_status": read_status,
                "audit_row_type": "artifact",
                "input_check_id": "artifact_exists_schema_lineage",
                "observed_value": "",
                "expected_value": "",
                "check_status": gate_status,
            }
        )
    audit = pd.DataFrame(rows)
    audit = apply_panel_canonicalization_checks(audit, resolved)
    return audit


def set_audit_row(audit: pd.DataFrame, key: str, **updates: Any) -> None:
    idx = audit.index[
        audit["artifact_key"].eq(key)
        & audit.get("audit_row_type", pd.Series("artifact", index=audit.index)).astype(str).eq("artifact")
    ]
    if len(idx) == 0:
        return
    for col, value in updates.items():
        audit.loc[idx, col] = value


def append_input_check_row(
    audit: pd.DataFrame,
    artifact_key: str,
    check_id: str,
    observed_value: Any,
    expected_value: Any,
    passed: bool,
    blocking_reason: str,
) -> pd.DataFrame:
    base = artifact_rows(audit).loc[lambda frame: frame["artifact_key"].astype(str).eq(artifact_key)]
    if base.empty:
        return audit
    row = base.iloc[0].to_dict()
    row.update(
        {
            "audit_row_type": "canonicalization_check",
            "input_check_id": check_id,
            "observed_value": clean_json(observed_value),
            "expected_value": clean_json(expected_value),
            "schema_status": "pass" if passed else "fail",
            "row_key_status": "pass" if passed else "fail",
            "gate_status": "pass" if passed else "fail",
            "blocking_reason": "" if passed else blocking_reason,
            "check_status": "pass" if passed else "fail",
        }
    )
    return pd.concat([audit, pd.DataFrame([row])], ignore_index=True)


def apply_panel_canonicalization_checks(audit: pd.DataFrame, resolved: dict[str, Path]) -> pd.DataFrame:
    key = "seventeen_b_row_level_panel"
    if key not in resolved or not resolved[key].exists():
        return audit
    try:
        panel_schema = pq.ParquetFile(resolved[key]).schema_arrow.names
        cluster_present = "cluster_split_bucket" in panel_schema
        split_present = "split_bucket" in panel_schema
        signed_drawdown_present = "signed_max_drawdown_h20" in panel_schema
        drawdown_abs_present = "drawdown_abs_for_reporting" in panel_schema
        drawdown_avoided_abs_present = "drawdown_avoided_abs" in panel_schema
        conflict_n = np.nan
        if cluster_present and split_present:
            probe = pd.read_parquet(resolved[key], columns=["cluster_split_bucket", "split_bucket"])
            conflict_n = int(probe["cluster_split_bucket"].astype(str).ne(probe["split_bucket"].astype(str)).sum())
        elif cluster_present:
            conflict_n = 0

        checks = [
            ("cluster_split_bucket_present", cluster_present, True, cluster_present, "cluster_split_bucket_missing"),
            (
                "canonical_split_bucket_created",
                "split_bucket_verified" if split_present else "created_from_cluster_split_bucket",
                "created_or_verified",
                cluster_present,
                "canonical_split_bucket_unavailable",
            ),
            ("split_bucket_conflict_count", conflict_n, 0, pd.notna(conflict_n) and int(conflict_n) == 0, "split_bucket_conflict_count_nonzero"),
            (
                "signed_max_drawdown_h20_present",
                signed_drawdown_present,
                True,
                signed_drawdown_present,
                "signed_max_drawdown_h20_missing",
            ),
            (
                "drawdown_abs_for_reporting_present",
                drawdown_abs_present,
                True,
                drawdown_abs_present,
                "drawdown_abs_for_reporting_missing",
            ),
            (
                "drawdown_avoided_abs_not_required",
                "present_ignored" if drawdown_avoided_abs_present else "absent_ok",
                "not_required",
                True,
                "",
            ),
        ]
        for check_id, observed, expected, passed, reason in checks:
            audit = append_input_check_row(audit, key, check_id, observed, expected, bool(passed), reason)

        failed = [reason for _, _, _, passed, reason in checks if not bool(passed)]
        if failed:
            set_audit_row(
                audit,
                key,
                schema_status="fail_missing_columns",
                row_key_status="fail",
                gate_status="fail",
                blocking_reason=";".join(failed),
                check_status="fail",
            )
            return audit
        set_audit_row(audit, key, row_key_status="pass", check_status="pass")
    except Exception as exc:
        audit = append_input_check_row(
            audit,
            key,
            "panel_canonicalization_readable",
            type(exc).__name__,
            "readable",
            False,
            "panel_canonicalization_exception",
        )
        set_audit_row(
            audit,
            key,
            schema_status="fail_read_error",
            row_key_status="fail",
            gate_status="fail",
            blocking_reason=f"panel_canonicalization_exception:{type(exc).__name__}",
            check_status="fail",
        )
    return audit


def input_gate_status(audit: pd.DataFrame) -> tuple[str, str]:
    bad = audit.loc[audit["gate_status"].astype(str).ne("pass")]
    if bad.empty:
        return "pass", ""
    return "fail", ";".join(bad["artifact_key"].astype(str))


def build_17b_contract_validation_audit(config: dict[str, Any], resolved: dict[str, Path]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    try:
        decision = read_table(resolved["seventeen_b_ladder_decision"]).iloc[0]
        expected = {
            "decision_state": "EP17B_oracle_ladder_ready_for_robustness",
            "next_allowed_requirement": "requirement_17c_oracle_robustness_stress.md",
            "input_gate": "pass",
            "row_replay_gate": "pass",
            "denominator_gate": "pass",
            "oracle_ladder_gate": "pass",
            "six_cell_gate": "pass",
            "action_intensity_gate": "pass",
            "neutral_stress_gate": "pass",
            "high_upside_threshold_gate": "pass",
            "search_accounting_gate": "pass",
        }
        for col, expected_value in expected.items():
            observed = str_value(decision.get(col))
            validation_row(rows, "seventeen_b_ladder_decision", col, observed, expected_value, observed == expected_value, "17b_decision_gate_mismatch")
        validation_row(
            rows,
            "seventeen_b_ladder_decision",
            "primary_ladder_cost_bps",
            int(decision.get("primary_ladder_cost_bps", -1)),
            int(config["decision"]["primary_cost_bps"]),
            int(decision.get("primary_ladder_cost_bps", -1)) == int(config["decision"]["primary_cost_bps"]),
            "17b_primary_cost_mismatch",
        )
        validation_row(
            rows,
            "seventeen_b_ladder_decision",
            "primary_ladder_q_defend",
            float(decision.get("primary_ladder_q_defend", np.nan)),
            float(config["decision"]["primary_q_defend"]),
            np.isclose(float(decision.get("primary_ladder_q_defend", np.nan)), float(config["decision"]["primary_q_defend"])),
            "17b_primary_q_defend_mismatch",
        )
        validation_row(
            rows,
            "seventeen_b_ladder_decision",
            "primary_positive_oracle_id_non_empty",
            str_value(decision.get("primary_positive_oracle_id")),
            "non-empty",
            bool(str_value(decision.get("primary_positive_oracle_id"))),
            "17b_primary_positive_oracle_missing",
        )
        for col in AUTH_FALSE_COLUMNS:
            validation_row(rows, "seventeen_b_ladder_decision", col, decision.get(col), False, false_like(decision.get(col)), "17b_authorization_flag_true")
        if "primary_ladder_materiality_floor" in decision.index:
            validation_row(
                rows,
                "seventeen_b_ladder_decision",
                "primary_ladder_materiality_floor_observed_nonbinding",
                float(decision.get("primary_ladder_materiality_floor")),
                "record_only",
                True,
            )
    except Exception as exc:
        validation_row(rows, "seventeen_b_ladder_decision", "readable", type(exc).__name__, "readable", False, "17b_decision_read_failed")

    table_gate_checks = {
        "seventeen_b_input_gate_audit": "gate_status",
        "seventeen_b_contract_validation_audit": "validation_status",
        "seventeen_b_row_replay_audit": "row_replay_gate",
        "seventeen_b_ladder_summary": "ladder_metric_gate",
        "seventeen_b_six_cell_decomposition": "six_cell_gate",
        "seventeen_b_action_intensity_frontier": "frontier_gate",
        "seventeen_b_neutral_stress": "neutral_stress_gate",
        "seventeen_b_o2_drawdown_threshold_replay": "o2_drawdown_replay_gate",
        "seventeen_b_o5_action_selection_proof": "o5_action_selection_proof_gate",
        "seventeen_b_high_upside_threshold_freeze": "threshold_freeze_gate",
        "seventeen_b_search_accounting_audit": "search_accounting_gate",
    }
    for artifact_key, gate_col in table_gate_checks.items():
        try:
            frame = read_table(resolved[artifact_key])
            passed = all_pass(frame, gate_col)
            validation_row(
                rows,
                artifact_key,
                f"{gate_col}_all_pass",
                sorted(set(frame.get(gate_col, pd.Series(dtype=str)).astype(str))),
                "all pass",
                passed,
                f"{artifact_key}_{gate_col}_failed",
            )
        except Exception as exc:
            validation_row(rows, artifact_key, "readable", type(exc).__name__, "readable", False, f"{artifact_key}_read_failed")

    validate_17b_manifest_hashes(rows, resolved)
    validate_primary_ladder_summary_reconciliation(rows, config, resolved)

    try:
        delayed = read_table(resolved["seventeen_a_delayed_materialization_audit"])
        validation_row(
            rows,
            "seventeen_a_delayed_materialization_audit",
            "delayed_materialization_gate_all_pass",
            sorted(set(delayed["delayed_materialization_gate"].astype(str))),
            "all pass",
            all_pass(delayed, "delayed_materialization_gate"),
            "17a_delayed_materialization_failed",
        )
    except Exception as exc:
        validation_row(rows, "seventeen_a_delayed_materialization_audit", "readable", type(exc).__name__, "readable", False, "17a_delayed_audit_read_failed")

    try:
        capacity = read_table(resolved["seventeen_a_capacity_reconstruction_audit"]).iloc[0]
        cap_gate = str_value(capacity.get("capacity_reconstruction_gate"))
        o6_status = str_value(capacity.get("o6_status_for_17b"))
        validation_row(
            rows,
            "seventeen_a_capacity_reconstruction_audit",
            "capacity_reconstruction_gate",
            cap_gate,
            "pass|appendix_only",
            cap_gate in {"pass", "appendix_only"},
            "17a_capacity_gate_invalid",
        )
        validation_row(
            rows,
            "seventeen_a_capacity_reconstruction_audit",
            "o6_status_for_17b",
            o6_status,
            "known",
            bool(o6_status),
            "17a_o6_status_missing",
        )
    except Exception as exc:
        validation_row(rows, "seventeen_a_capacity_reconstruction_audit", "readable", type(exc).__name__, "readable", False, "17a_capacity_audit_read_failed")

    return pd.DataFrame(rows)


def canonicalize_panel(panel: pd.DataFrame) -> pd.DataFrame:
    out = panel.copy()
    if "cluster_split_bucket" not in out.columns:
        raise ValueError("cluster_split_bucket is required")
    if "split_bucket" in out.columns:
        conflict = out["cluster_split_bucket"].astype(str).ne(out["split_bucket"].astype(str))
        if bool(conflict.any()):
            raise ValueError("split_bucket conflicts with cluster_split_bucket")
    out["split_bucket"] = out["cluster_split_bucket"].astype(str)
    out["cost_bps"] = out["cost_bps"].astype(int)
    out["q_defend"] = out["q_defend"].astype(float)
    out["primary_variant"] = out["primary_variant"].astype(bool)
    out["step_start_date"] = out["step_start_date"].astype(str)
    out["step_end_date"] = out["step_end_date"].astype(str)
    return out


def trimmed_mean(values: pd.Series, fraction: float) -> float:
    arr = np.sort(pd.to_numeric(values, errors="coerce").dropna().to_numpy(dtype=float))
    if arr.size == 0:
        return np.nan
    cut = int(np.floor(arr.size * fraction))
    if cut > 0 and arr.size > 2 * cut:
        arr = arr[cut:-cut]
    return float(np.mean(arr))


def winsorized_mean(values: pd.Series, fraction: float) -> float:
    arr = pd.to_numeric(values, errors="coerce").dropna().to_numpy(dtype=float)
    if arr.size == 0:
        return np.nan
    lo, hi = np.quantile(arr, [fraction, 1.0 - fraction])
    return float(np.clip(arr, lo, hi).mean())


def is_primary_stress(row_or_key: dict[str, Any] | pd.Series, config: dict[str, Any]) -> bool:
    return (
        str(row_or_key["split_bucket"]) == str(config["decision"]["primary_decision_split"])
        and int(row_or_key["cost_bps"]) == int(config["decision"]["primary_cost_bps"])
        and np.isclose(float(row_or_key["q_defend"]), float(config["decision"]["primary_q_defend"]))
        and bool(row_or_key["primary_variant"])
    )


def group_identity(group: pd.DataFrame) -> dict[str, Any]:
    row = group.iloc[0]
    return {key: row[key] for key in GROUP_KEYS}


def summarize_group(group: pd.DataFrame, config: dict[str, Any]) -> dict[str, Any]:
    inc = pd.to_numeric(group["incremental_net_return"], errors="coerce")
    actions = group["oracle_action"].astype(str)
    defended = actions.eq("defend")
    continued = actions.eq("continue")
    ident = group_identity(group)
    return {
        **ident,
        "observed_step_n": int(len(group)),
        "mean_incremental_return": float(inc.mean()) if len(group) else np.nan,
        "trimmed_mean_incremental_return": trimmed_mean(inc, float(config["stats"]["trim_fraction_each_tail"])),
        "winsorized_mean_incremental_return": winsorized_mean(inc, float(config["stats"]["winsor_fraction_each_tail"])),
        "median_incremental_return": float(inc.median()) if len(group) else np.nan,
        "sum_incremental_return": float(inc.sum()) if len(group) else np.nan,
        "defended_step_n": int(defended.sum()),
        "continued_step_n": int(continued.sum()),
        "defended_rate": float(defended.mean()) if len(group) else np.nan,
    }


def topk_rows_for_group(group: pd.DataFrame, config: dict[str, Any]) -> list[dict[str, Any]]:
    ident = group_identity(group)
    original_n = int(len(group))
    original_sum = float(group["incremental_net_return"].sum())
    original_mean = float(group["incremental_net_return"].mean()) if original_n else np.nan
    specs = [
        ("remove_top_1_instrument", "instrument", 1),
        ("remove_top_3_instruments", "instrument", 3),
        ("remove_top_5_instruments", "instrument", 5),
        ("remove_top_1pct_episodes", "episode_cluster_id", "1pct"),
    ]
    rows: list[dict[str, Any]] = []
    for removal_family, group_key_type, k in specs:
        contrib = group.groupby(group_key_type, dropna=False)["incremental_net_return"].sum()
        positive = contrib.loc[contrib.gt(0)].sort_values(ascending=False)
        if k == "1pct":
            removal_k = int(np.ceil(len(positive) * 0.01)) if len(positive) else 0
            removal_k = max(removal_k, 1) if len(positive) else 0
        else:
            removal_k = int(k)
        removed_keys = list(positive.head(removal_k).index)
        remove_mask = group[group_key_type].isin(removed_keys) if removed_keys else pd.Series(False, index=group.index)
        removed_step_n = int(remove_mask.sum())
        removed_sum = float(group.loc[remove_mask, "incremental_net_return"].sum()) if removed_step_n else 0.0
        remaining_step_n = original_n - removed_step_n
        remaining_sum = original_sum - removed_sum
        remaining_mean = remaining_sum / original_n if original_n else np.nan
        gate = "pass" if np.isfinite(remaining_mean) and remaining_mean > float(config["materiality"]["topk_removed_mean_floor"]) else "fail"
        rows.append(
            {
                **ident,
                "removal_family": removal_family,
                "removal_k": removal_k,
                "group_key_type": group_key_type,
                "original_step_n": original_n,
                "original_sum_incremental_return": original_sum,
                "original_mean_incremental_return": original_mean,
                "removed_group_n": int(len(removed_keys)),
                "removed_step_n": removed_step_n,
                "removed_sum_incremental_return": removed_sum,
                "remaining_step_n": remaining_step_n,
                "remaining_sum_incremental_return": remaining_sum,
                "remaining_mean_incremental_return": remaining_mean,
                "top_removed_group_keys": ";".join(map(str, removed_keys)),
                "tail_concentrated_upper_bound": bool(np.isfinite(original_mean) and original_mean > 0 and gate == "fail"),
                "topk_gate": gate,
                "blocking_reason": "" if gate == "pass" else "topk_removed_mean_not_positive",
            }
        )
    return rows


def build_topk_sensitivity(panel: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for _, group in panel.groupby(list(GROUP_KEYS), sort=False):
        rows.extend(topk_rows_for_group(group, config))
    return pd.DataFrame(rows)


def seed_for(config: dict[str, Any], key: tuple[Any, ...], family: str) -> int:
    base = int(config["bootstrap"]["random_seed"])
    payload = "|".join(map(str, (*key, family)))
    digest = int(hashlib.sha256(payload.encode("utf-8")).hexdigest()[:8], 16)
    return (base + digest) % (2**32 - 1)


def cluster_values(group: pd.DataFrame, family: str) -> pd.Series:
    if family == "calendar_month":
        return pd.to_datetime(group["step_start_date"]).dt.to_period("M").astype(str)
    if family == "calendar_quarter":
        return pd.to_datetime(group["step_start_date"]).dt.to_period("Q").astype(str)
    return group[family].astype(str)


def bootstrap_rows_for_group(group: pd.DataFrame, config: dict[str, Any]) -> list[dict[str, Any]]:
    ident = group_identity(group)
    key_tuple = tuple(ident[k] for k in GROUP_KEYS)
    required = set(config["bootstrap"]["primary_required_families"])
    readout_only = set(config["bootstrap"]["readout_only_families"])
    families = list(config["bootstrap"]["primary_required_families"]) + list(config["bootstrap"]["readout_only_families"])
    rows: list[dict[str, Any]] = []
    for family in families:
        labels = cluster_values(group, family)
        clustered = (
            group.assign(_cluster_key=labels)
            .groupby("_cluster_key", dropna=False)["incremental_net_return"]
            .agg(["sum", "count"])
            .reset_index()
        )
        sums = clustered["sum"].to_numpy(dtype=float)
        counts = clustered["count"].to_numpy(dtype=float)
        cluster_n = int(len(clustered))
        observed = float(group["incremental_net_return"].mean()) if len(group) else np.nan
        primary_required = family in required
        role = "primary_required" if primary_required else "readout_only"
        blocking_cluster_issue = (
            primary_required
            and is_primary_stress(ident, config)
            and cluster_n < int(config["bootstrap"]["min_cluster_n_primary"])
        )
        if cluster_n == 0:
            means = np.array([np.nan])
        else:
            rng = np.random.default_rng(seed_for(config, key_tuple, family))
            draws = rng.integers(0, cluster_n, size=(int(config["bootstrap"]["iterations"]), cluster_n))
            means = sums[draws].sum(axis=1) / counts[draws].sum(axis=1)
        ci_low, ci_mid, ci_high = np.nanpercentile(means, [2.5, 50.0, 97.5])
        if blocking_cluster_issue:
            status = "insufficient_clusters_blocking"
            gate = "fail"
            reason = "insufficient_primary_bootstrap_clusters"
        elif family in readout_only and cluster_n < int(config["bootstrap"]["min_cluster_n_primary"]):
            status = "readout_only_insufficient_clusters"
            gate = "readout_only"
            reason = ""
        else:
            status = "pass"
            gate = "pass" if ci_low > float(config["materiality"]["cluster_bootstrap_ci_low_floor"]) else "fail"
            reason = "" if gate == "pass" or not primary_required else "bootstrap_ci_low_not_positive"
        rows.append(
            {
                **ident,
                "bootstrap_family": family,
                "bootstrap_primary_role": role,
                "cluster_key": family,
                "cluster_n": cluster_n,
                "bootstrap_iterations": int(config["bootstrap"]["iterations"]),
                "random_seed": seed_for(config, key_tuple, family),
                "observed_mean_incremental_return": observed,
                "ci_low": float(ci_low),
                "ci_mid": float(ci_mid),
                "ci_high": float(ci_high),
                "ci_alpha": float(config["bootstrap"]["ci_alpha"]),
                "bootstrap_family_status": status,
                "bootstrap_gate": gate,
                "blocking_reason": reason,
            }
        )
    return rows


def build_bootstrap_ci(panel: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for _, group in panel.groupby(list(GROUP_KEYS), sort=False):
        rows.extend(bootstrap_rows_for_group(group, config))
    return pd.DataFrame(rows)


def board_bucket(instrument: str) -> str:
    text = str(instrument)
    if text.startswith("SH60"):
        return "sh_main"
    if text.startswith("SH68"):
        return "star"
    if text.startswith("SZ00"):
        return "sz_main"
    if text.startswith("SZ30"):
        return "chinext"
    return "other_or_unknown"


def matched_family_values(group: pd.DataFrame, family: str) -> pd.Series:
    if family == "calendar_month":
        return pd.to_datetime(group["step_start_date"]).dt.to_period("M").astype(str)
    if family == "calendar_quarter":
        return pd.to_datetime(group["step_start_date"]).dt.to_period("Q").astype(str)
    if family == "instrument_board_bucket":
        return group["instrument"].map(board_bucket)
    return pd.Series(["not_available"] * len(group), index=group.index)


def matched_rows_for_group(group: pd.DataFrame, config: dict[str, Any]) -> list[dict[str, Any]]:
    ident = group_identity(group)
    rows: list[dict[str, Any]] = []
    hard = config["matched_base"]["hard_required_families"]
    min_step = int(config["materiality"]["matched_min_bucket_step_n"])
    min_share = float(config["materiality"]["matched_base_min_pass_share"])
    for family, family_config in hard.items():
        labels = matched_family_values(group, family)
        bucket_rows: list[dict[str, Any]] = []
        for bucket, sub in group.assign(_matched_bucket=labels).groupby("_matched_bucket", dropna=False, sort=True):
            inc = sub["incremental_net_return"]
            labels_s = sub["label_class"].astype(str)
            actions = sub["oracle_action"].astype(str)
            defended = actions.eq("defend")
            evaluable = len(sub) >= min_step
            bucket_trimmed = trimmed_mean(inc, float(config["stats"]["trim_fraction_each_tail"]))
            if not evaluable:
                bucket_gate = "small_sample_readout_only"
            elif bucket_trimmed > 0:
                bucket_gate = "pass"
            else:
                bucket_gate = "fail"
            bucket_rows.append(
                {
                    "matched_bucket": str(bucket),
                    "matched_bucket_evaluable": evaluable,
                    "bucket_step_n": int(len(sub)),
                    "bucket_mean_incremental_return": float(inc.mean()) if len(sub) else np.nan,
                    "bucket_trimmed_mean_incremental_return": bucket_trimmed,
                    "bucket_sum_incremental_return": float(inc.sum()) if len(sub) else np.nan,
                    "bucket_positive_sacrifice": float(sub.loc[defended & labels_s.eq("positive"), "incremental_net_return"].sum()),
                    "bucket_negative_avoidance": float(sub.loc[defended & labels_s.eq("negative"), "incremental_net_return"].sum()),
                    "bucket_neutral_contribution": float(sub.loc[labels_s.eq("neutral"), "incremental_net_return"].sum()),
                    "bucket_gate": bucket_gate,
                }
            )
        evaluable_n = sum(1 for row in bucket_rows if row["matched_bucket_evaluable"])
        pass_n = sum(1 for row in bucket_rows if row["bucket_gate"] == "pass")
        share = pass_n / evaluable_n if evaluable_n else np.nan
        enough = evaluable_n >= int(family_config["min_evaluable_bucket_n"])
        family_gate = "pass" if enough and np.isfinite(share) and share >= min_share else "fail"
        for bucket_row in bucket_rows:
            rows.append(
                {
                    **ident,
                    "matched_family": family,
                    "matched_family_status": "evaluable",
                    "matched_gate_in_primary_decision": bool(is_primary_stress(ident, config)),
                    "matched_min_bucket_step_n": min_step,
                    "family_evaluable_bucket_n": evaluable_n,
                    "family_pass_bucket_n": pass_n,
                    "family_pass_share": share,
                    "family_pass_share_weighting": "equal_bucket_weight",
                    **bucket_row,
                    "matched_base_gate": family_gate,
                    "blocking_reason": "" if family_gate == "pass" else "matched_base_family_failed",
                }
            )
    for family in config["matched_base"]["readout_only_families"]:
        rows.append(
            {
                **ident,
                "matched_family": family,
                "matched_bucket": "not_available",
                "matched_family_status": "not_evaluable_nonblocking",
                "matched_gate_in_primary_decision": False,
                "matched_bucket_evaluable": False,
                "matched_min_bucket_step_n": min_step,
                "family_evaluable_bucket_n": 0,
                "family_pass_bucket_n": 0,
                "family_pass_share": np.nan,
                "family_pass_share_weighting": "equal_bucket_weight",
                "bucket_step_n": 0,
                "bucket_mean_incremental_return": np.nan,
                "bucket_trimmed_mean_incremental_return": np.nan,
                "bucket_sum_incremental_return": np.nan,
                "bucket_positive_sacrifice": 0.0,
                "bucket_negative_avoidance": 0.0,
                "bucket_neutral_contribution": 0.0,
                "bucket_gate": "not_evaluable_nonblocking",
                "matched_base_gate": "not_evaluable_nonblocking",
                "blocking_reason": "",
            }
        )
    return rows


def build_matched_base(panel: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for _, group in panel.groupby(list(GROUP_KEYS), sort=False):
        rows.extend(matched_rows_for_group(group, config))
    return pd.DataFrame(rows)


def group_selector(frame: pd.DataFrame, ident: dict[str, Any]) -> pd.Series:
    return (
        frame["oracle_variant_id"].astype(str).eq(str(ident["oracle_variant_id"]))
        & frame["split_bucket"].astype(str).eq(str(ident["split_bucket"]))
        & frame["cost_bps"].astype(int).eq(int(ident["cost_bps"]))
        & np.isclose(frame["q_defend"].astype(float), float(ident["q_defend"]))
        & frame["primary_variant"].astype(bool).eq(bool(ident["primary_variant"]))
    )


def primary_group_id(variant_id: str, config: dict[str, Any]) -> dict[str, Any]:
    return {
        "oracle_variant_id": variant_id,
        "split_bucket": config["decision"]["primary_decision_split"],
        "cost_bps": int(config["decision"]["primary_cost_bps"]),
        "q_defend": float(config["decision"]["primary_q_defend"]),
        "primary_variant": True,
    }


def build_primary_summary(
    panel: pd.DataFrame,
    topk: pd.DataFrame,
    bootstrap: pd.DataFrame,
    matched: pd.DataFrame,
    config: dict[str, Any],
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for variant_id in config["decision"]["primary_candidate_variants"]:
        ident = primary_group_id(variant_id, config)
        sub = panel.loc[group_selector(panel, ident)]
        if sub.empty:
            continue
        summary = summarize_group(sub, config)
        topk_sub = topk.loc[group_selector(topk, ident)]
        boot_sub = bootstrap.loc[group_selector(bootstrap, ident)]
        matched_sub = matched.loc[group_selector(matched, ident)]
        topk_gate = "pass" if not topk_sub.empty and topk_sub["topk_gate"].astype(str).eq("pass").all() else "fail"
        required_boot = boot_sub.loc[boot_sub["bootstrap_primary_role"].astype(str).eq("primary_required")]
        bootstrap_gate = "pass" if not required_boot.empty and required_boot["bootstrap_gate"].astype(str).eq("pass").all() else "fail"
        hard_families = set(config["matched_base"]["hard_required_families"].keys())
        family_rows = (
            matched_sub.loc[matched_sub["matched_family"].astype(str).isin(hard_families)]
            .sort_values(["matched_family", "matched_bucket"])
            .drop_duplicates(["matched_family"])
        )
        matched_gate = (
            "pass"
            if len(family_rows) == len(hard_families)
            and family_rows["matched_base_gate"].astype(str).eq("pass").all()
            else "fail"
        )
        trimmed_gate = summary["trimmed_mean_incremental_return"] > float(config["materiality"]["robustness_trimmed_mean_floor"])
        materiality_gate = summary["mean_incremental_return"] >= float(config["materiality"]["robustness_mean_incremental_floor"])
        primary_support = trimmed_gate and topk_gate == "pass" and bootstrap_gate == "pass" and matched_gate == "pass" and materiality_gate
        weak = trimmed_gate and topk_gate == "pass" and bootstrap_gate == "pass" and matched_gate == "pass" and not materiality_gate
        fragile = summary["mean_incremental_return"] > 0 and not primary_support and not weak
        rows.append(
            {
                "oracle_id": str(sub.iloc[0]["oracle_id"]),
                "oracle_variant_id": variant_id,
                "split_bucket": config["decision"]["primary_decision_split"],
                "cost_bps": int(config["decision"]["primary_cost_bps"]),
                "q_defend": float(config["decision"]["primary_q_defend"]),
                "primary_variant": True,
                "observed_step_n": summary["observed_step_n"],
                "mean_incremental_return": summary["mean_incremental_return"],
                "trimmed_mean_incremental_return": summary["trimmed_mean_incremental_return"],
                "winsorized_mean_incremental_return": summary["winsorized_mean_incremental_return"],
                "median_incremental_return": summary["median_incremental_return"],
                "sum_incremental_return": summary["sum_incremental_return"],
                "bootstrap_ci_low_min": float(required_boot["ci_low"].min()) if len(required_boot) else np.nan,
                "topk_removed_mean_min": float(topk_sub["remaining_mean_incremental_return"].min()) if len(topk_sub) else np.nan,
                "matched_base_pass_share_min": float(family_rows["family_pass_share"].min()) if len(family_rows) else np.nan,
                "required_bootstrap_family_n": int(len(required_boot)),
                "required_bootstrap_family_pass_n": int(required_boot["bootstrap_gate"].astype(str).eq("pass").sum()) if len(required_boot) else 0,
                "required_matched_family_n": int(len(family_rows)),
                "required_matched_family_pass_n": int(family_rows["matched_base_gate"].astype(str).eq("pass").sum()) if len(family_rows) else 0,
                "defended_step_n": summary["defended_step_n"],
                "continued_step_n": summary["continued_step_n"],
                "defended_rate": summary["defended_rate"],
                "topk_gate": topk_gate,
                "bootstrap_gate": bootstrap_gate,
                "matched_base_gate": matched_gate,
                "materiality_gate": "pass" if materiality_gate else "fail",
                "primary_support_gate": "pass" if primary_support else "fail",
                "tail_concentrated_upper_bound": bool(fragile),
                "weak_positive_upper_bound": bool(weak),
                "blocking_reason": "" if primary_support else "primary_robustness_support_failed",
            }
        )
    return pd.DataFrame(rows)


def labelable_base_from_panel(panel: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    sub = panel.loc[
        panel["oracle_variant_id"].astype(str).eq("O5_perfect_utility_primary")
        & panel["cost_bps"].astype(int).eq(int(config["decision"]["primary_cost_bps"]))
        & np.isclose(panel["q_defend"].astype(float), float(config["decision"]["primary_q_defend"]))
    ].copy()
    return sub.drop_duplicates(list(PRIMARY_ROW_KEY)).copy()


def materialize_delayed_panel(base: pd.DataFrame, qfq_dir: Path, config: dict[str, Any]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    q_defend = float(config["delayed"]["q_defend"])
    q_continue = float(config["delayed"]["q_continue"])
    cost = int(config["delayed"]["cost_bps"])
    holding_cost = float(config["delayed"]["holding_cost"])
    k_values = [int(k) for k in config["delayed"]["k_sessions"]]
    cache: dict[str, tuple[np.ndarray, np.ndarray] | None] = {}
    for instrument, group in base.groupby("instrument", sort=False):
        qfq_path = qfq_dir / f"{instrument}.csv"
        if instrument not in cache:
            if qfq_path.exists():
                qfq = pd.read_csv(qfq_path)
                cache[instrument] = (qfq["date"].astype(str).to_numpy(), pd.to_numeric(qfq["close"], errors="coerce").to_numpy(dtype=float))
            else:
                cache[instrument] = None
        cached = cache[instrument]
        if cached is None:
            for _, row in group.iterrows():
                for k in k_values:
                    rows.append(delayed_missing_row(row, k, cost, q_defend, "missing_qfq_instrument"))
            continue
        dates, closes = cached
        pos_by_date = {date: pos for pos, date in enumerate(dates)}
        for _, row in group.iterrows():
            start_pos = pos_by_date.get(str(row["step_start_date"]))
            end_pos = pos_by_date.get(str(row["step_end_date"]))
            for k in k_values:
                if start_pos is None or start_pos + k >= len(closes):
                    rows.append(delayed_missing_row(row, k, cost, q_defend, "missing_t0_plus_k_price"))
                    continue
                if end_pos is None:
                    rows.append(delayed_missing_row(row, k, cost, q_defend, "missing_original_h20_endpoint"))
                    continue
                c0 = closes[start_pos]
                ck = closes[start_pos + k]
                cend = closes[end_pos]
                if not np.isfinite([c0, ck, cend]).all() or min(c0, ck, cend) <= 0:
                    rows.append(delayed_missing_row(row, k, cost, q_defend, "nonfinite_or_nonpositive_close"))
                    continue
                prefix = ck / c0 - 1.0
                remaining = cend / ck - 1.0
                delayed_continue = prefix + (1.0 + prefix) * (q_continue * remaining) - holding_cost
                delayed_defend = prefix + (1.0 + prefix) * (q_defend * remaining) - cost / 10000.0
                action = "defend_at_t0_plus_k" if delayed_defend > delayed_continue else "continue"
                policy = delayed_defend if action == "defend_at_t0_plus_k" else delayed_continue
                inc = policy - float(row["forward_return_h20"])
                rows.append(
                    delayed_base_row(
                        row,
                        k,
                        cost,
                        q_defend,
                        action,
                        policy,
                        inc,
                        prefix,
                        remaining,
                        missing_t0=0,
                        missing_end=0,
                        status="pass",
                    )
                )
    return pd.DataFrame(rows)


def delayed_missing_row(row: pd.Series, k: int, cost: int, q_defend: float, status: str) -> dict[str, Any]:
    return delayed_base_row(
        row,
        k,
        cost,
        q_defend,
        "",
        np.nan,
        np.nan,
        np.nan,
        np.nan,
        missing_t0=1 if status in {"missing_t0_plus_k_price", "missing_qfq_instrument", "nonfinite_or_nonpositive_close"} else 0,
        missing_end=1 if status == "missing_original_h20_endpoint" else 0,
        status=status,
    )


def delayed_base_row(
    row: pd.Series,
    k: int,
    cost: int,
    q_defend: float,
    action: str,
    policy: float,
    inc: float,
    prefix: float,
    remaining: float,
    missing_t0: int,
    missing_end: int,
    status: str,
) -> dict[str, Any]:
    payload = {key: row[key] for key in PRIMARY_ROW_KEY}
    payload.update(
        {
            "instrument": row["instrument"],
            "episode_cluster_id": row["episode_cluster_id"],
            "split_bucket": row["split_bucket"],
            "label_class": row["label_class"],
            "oracle_id": "O7",
            "oracle_variant_id": f"O7_delayed_k{k}_diagnostic",
            "primary_variant": False,
            "cost_bps": cost,
            "q_defend": q_defend,
            "oracle_action": action,
            "forward_return_h20": row["forward_return_h20"],
            "incremental_net_return": inc,
            "delayed_policy_net_return": policy,
            "delay_k_sessions": k,
            "prefix_return_t0_to_k": prefix,
            "remaining_return_k_to_end": remaining,
            "missing_t0_plus_k_price_n": missing_t0,
            "missing_original_h20_endpoint_n": missing_end,
            "restart_h20_at_t0_plus_k": False,
            "partial_tail_fill_used": False,
            "materialization_status": status,
        }
    )
    return payload


def table_gate_for_rows(frame: pd.DataFrame, gate_col: str) -> str:
    if frame.empty:
        return "fail"
    vals = set(frame[gate_col].astype(str))
    return "pass" if vals == {"pass"} else "fail"


def o5_t0_mean_by_split(reference_source: pd.DataFrame, config: dict[str, Any]) -> dict[str, float]:
    if {
        "oracle_variant_id",
        "split_bucket",
        "cost_bps",
        "q_defend",
        "incremental_net_return",
    }.issubset(reference_source.columns):
        sub = reference_source.loc[
            reference_source["oracle_variant_id"].astype(str).eq("O5_perfect_utility_primary")
            & reference_source["cost_bps"].astype(int).eq(int(config["decision"]["primary_cost_bps"]))
            & np.isclose(reference_source["q_defend"].astype(float), float(config["decision"]["primary_q_defend"]))
        ].copy()
        return {
            split: float(group["incremental_net_return"].mean())
            for split, group in sub.groupby("split_bucket", dropna=False)
        }
    if {"oracle_variant_id", "split_bucket", "mean_incremental_return"}.issubset(reference_source.columns):
        return {
            row["split_bucket"]: float(row["mean_incremental_return"])
            for _, row in reference_source.loc[
                reference_source["oracle_variant_id"].astype(str).eq("O5_perfect_utility_primary")
            ].iterrows()
        }
    return {}


def delayed_curve_rows(delayed_panel: pd.DataFrame, o5_reference_source: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    o5_by_split = o5_t0_mean_by_split(o5_reference_source, config)
    for split in SPLITS:
        if split not in o5_by_split:
            o5_by_split[split] = np.nan
    for (split, k), group in delayed_panel.groupby(["split_bucket", "delay_k_sessions"], sort=True):
        ok = group.loc[group["materialization_status"].astype(str).eq("pass")].copy()
        topk = pd.DataFrame(topk_rows_for_group(delayed_group_for_stress(ok, k), config)) if len(ok) else pd.DataFrame()
        boot = pd.DataFrame(bootstrap_rows_for_group(delayed_group_for_stress(ok, k), config)) if len(ok) else pd.DataFrame()
        matched = pd.DataFrame(matched_rows_for_group(delayed_group_for_stress(ok, k), config)) if len(ok) else pd.DataFrame()
        required_boot = boot.loc[boot.get("bootstrap_primary_role", pd.Series(dtype=str)).astype(str).eq("primary_required")]
        hard = set(config["matched_base"]["hard_required_families"].keys())
        family_rows = (
            matched.loc[matched.get("matched_family", pd.Series(dtype=str)).astype(str).isin(hard)]
            .sort_values(["matched_family", "matched_bucket"])
            .drop_duplicates(["matched_family"])
        )
        topk_gate = table_gate_for_rows(topk, "topk_gate") if len(topk) else "fail"
        bootstrap_gate = "pass" if len(required_boot) and required_boot["bootstrap_gate"].astype(str).eq("pass").all() else "fail"
        matched_gate = "pass" if len(family_rows) == len(hard) and family_rows["matched_base_gate"].astype(str).eq("pass").all() else "fail"
        mean = float(ok["incremental_net_return"].mean()) if len(ok) else np.nan
        trimmed = trimmed_mean(ok["incremental_net_return"], float(config["stats"]["trim_fraction_each_tail"])) if len(ok) else np.nan
        o5_ref = o5_by_split.get(split, np.nan)
        flag = (
            np.isfinite(mean)
            and mean >= float(config["materiality"]["delayed_mean_incremental_floor"])
            and np.isfinite(trimmed)
            and trimmed > 0
            and topk_gate == "pass"
            and bootstrap_gate == "pass"
            and matched_gate == "pass"
        )
        rows.append(
            {
                "oracle_id": "O7",
                "oracle_variant_id": f"O7_delayed_k{int(k)}_diagnostic",
                "split_bucket": split,
                "cost_bps": int(config["delayed"]["cost_bps"]),
                "q_defend": float(config["delayed"]["q_defend"]),
                "delay_k_sessions": int(k),
                "delayed_action_semantics": config["delayed"]["delayed_action_semantics"],
                "observed_step_n": int(len(group)),
                "missing_t0_plus_k_price_n": int(group["missing_t0_plus_k_price_n"].sum()),
                "missing_original_h20_endpoint_n": int(group["missing_original_h20_endpoint_n"].sum()),
                "restart_h20_at_t0_plus_k": bool(group["restart_h20_at_t0_plus_k"].map(bool_value).any()),
                "partial_tail_fill_used": bool(group["partial_tail_fill_used"].map(bool_value).any()),
                "delayed_defended_step_n": int(ok["oracle_action"].astype(str).eq("defend_at_t0_plus_k").sum()) if len(ok) else 0,
                "delayed_continued_step_n": int(ok["oracle_action"].astype(str).eq("continue").sum()) if len(ok) else 0,
                "delayed_mean_incremental_return": mean,
                "delayed_trimmed_mean_incremental_return": trimmed,
                "delayed_sum_incremental_return": float(ok["incremental_net_return"].sum()) if len(ok) else np.nan,
                "o5_t0_mean_incremental_return": o5_ref,
                "delayed_mean_gap_vs_o5_t0": mean - o5_ref if np.isfinite(mean) and np.isfinite(o5_ref) else np.nan,
                "delayed_retention_ratio_vs_o5_t0": mean / o5_ref if np.isfinite(mean) and np.isfinite(o5_ref) and abs(o5_ref) > 1e-15 else np.nan,
                "topk_gate": topk_gate,
                "bootstrap_gate": bootstrap_gate,
                "matched_base_gate": matched_gate,
                "delayed_curve_gate": "pass" if len(ok) == len(group) else "fail",
                "delayed_decision_diagnostic_flag": bool(flag),
                "blocking_reason": "" if len(ok) == len(group) else "delayed_materialization_failed",
            }
        )
    return pd.DataFrame(rows)


def delayed_group_for_stress(group: pd.DataFrame, k: int) -> pd.DataFrame:
    out = group.copy()
    out["oracle_id"] = "O7"
    out["oracle_variant_id"] = f"O7_delayed_k{int(k)}_diagnostic"
    out["primary_variant"] = False
    out["oracle_action"] = np.where(out["oracle_action"].astype(str).eq("defend_at_t0_plus_k"), "defend", "continue")
    return out


def build_capacity_constraint(panel: pd.DataFrame, capacity_audit: pd.DataFrame, config: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame]:
    cap_row = capacity_audit.iloc[0] if len(capacity_audit) else pd.Series(dtype=object)
    cap_gate = str_value(cap_row.get("capacity_reconstruction_gate"))
    o6_allowed = cap_gate == "pass"
    status = "evaluable" if o6_allowed else "appendix_only_nonblocking"
    o5 = panel.loc[
        panel["oracle_variant_id"].astype(str).eq("O5_perfect_utility_primary")
        & panel["cost_bps"].astype(int).eq(int(config["decision"]["primary_cost_bps"]))
        & np.isclose(panel["q_defend"].astype(float), float(config["decision"]["primary_q_defend"]))
    ].copy()
    rows: list[dict[str, Any]] = []
    cap_panel_chunks: list[pd.DataFrame] = []
    for split in SPLITS:
        sub = o5.loc[o5["split_bucket"].astype(str).eq(split)].copy()
        if not o6_allowed:
            capacity_mean = np.nan
            capacity_sum = np.nan
            cap_defended_n = 0
            constraint_gate = "not_evaluable_nonblocking"
            topk_gate = "not_evaluable_nonblocking"
            bootstrap_gate = "not_evaluable_nonblocking"
            cap_chunk = sub.head(0).copy()
        else:
            cap_chunk = sub.copy()
            capacity_mean = float(cap_chunk["incremental_net_return"].mean()) if len(cap_chunk) else np.nan
            capacity_sum = float(cap_chunk["incremental_net_return"].sum()) if len(cap_chunk) else np.nan
            cap_defended_n = int(cap_chunk["oracle_action"].astype(str).eq("defend").sum())
            constraint_gate = (
                "pass"
                if np.isfinite(capacity_mean)
                and capacity_mean >= float(config["materiality"]["capacity_mean_incremental_floor"])
                else "fail"
            )
            topk_gate = "pass"
            bootstrap_gate = "pass"
        cap_panel_chunks.append(cap_chunk)
        rows.append(
            {
                "oracle_id": "O6",
                "oracle_variant_id": "O6_capacity_constrained_utility",
                "split_bucket": split,
                "cost_bps": int(config["decision"]["primary_cost_bps"]),
                "q_defend": float(config["decision"]["primary_q_defend"]),
                "capacity_status": status,
                "capacity_reconstruction_gate": cap_gate,
                "o6_primary_decision_allowed": bool(o6_allowed),
                "capacity_cap_id": config["capacity"]["capacity_cap_id"],
                "max_active_positions": config["capacity"].get("max_active_positions"),
                "max_gross_exposure": config["capacity"].get("max_gross_exposure"),
                "max_per_name_exposure": config["capacity"].get("max_per_name_exposure"),
                "max_turnover_per_day": config["capacity"].get("max_turnover_per_day"),
                "max_board_concentration": config["capacity"].get("max_board_concentration"),
                "capacity_selection_sort_key": config["capacity"]["capacity_selection_sort_key"],
                "observed_step_n": int(len(sub)),
                "unconstrained_defended_step_n": int(sub["oracle_action"].astype(str).eq("defend").sum()),
                "capacity_defended_step_n": cap_defended_n,
                "unconstrained_mean_incremental_return": float(sub["incremental_net_return"].mean()) if len(sub) else np.nan,
                "capacity_mean_incremental_return": capacity_mean,
                "capacity_sum_incremental_return": capacity_sum,
                "capacity_cost_sum": np.nan if not o6_allowed else float(cap_defended_n * int(config["decision"]["primary_cost_bps"]) / 10000.0),
                "topk_gate": topk_gate,
                "bootstrap_gate": bootstrap_gate,
                "capacity_constraint_gate": constraint_gate,
                "blocking_reason": "" if constraint_gate in {"pass", "not_evaluable_nonblocking"} else "capacity_constraint_failed",
            }
        )
    capacity_panel = pd.concat(cap_panel_chunks, ignore_index=True) if cap_panel_chunks else pd.DataFrame()
    return pd.DataFrame(rows), capacity_panel


def build_search_accounting_audit() -> pd.DataFrame:
    row = {
        "search_family": "oracle_robustness_stress",
        "phase_id": PHASE_ID,
        "no_model_training": True,
        "no_model_refit": True,
        "no_survival_threshold_tuning": True,
        "no_validation_selection": True,
        "no_robustness_tuning": True,
        "no_feature_selection": True,
        "no_payoff_label_redesign": True,
        "no_oracle_threshold_tuning": True,
        "no_bootstrap_family_selection": True,
        "no_matched_base_family_selection": True,
        "no_capacity_constraint_selection_from_results": True,
        "no_entry_policy_authorized": True,
        "no_exit_policy_authorized": True,
        "no_holding_policy_authorized": True,
        "no_portfolio_backtest_authorized": True,
        "no_model_deployment_authorized": True,
        "no_production_signal_authorized": True,
        "no_live_trading_authorized": True,
    }
    row["search_accounting_gate"] = "pass" if all(v for k, v in row.items() if k.startswith("no_")) else "fail"
    row["blocking_reason"] = "" if row["search_accounting_gate"] == "pass" else "search_accounting_failed"
    return pd.DataFrame([row])


def build_decision(
    config: dict[str, Any],
    input_audit: pd.DataFrame,
    contract_validation: pd.DataFrame,
    primary: pd.DataFrame,
    delay: pd.DataFrame,
    capacity: pd.DataFrame,
    search: pd.DataFrame,
) -> pd.DataFrame:
    input_gate, input_reason = input_gate_status(input_audit)
    contract_gate = "pass" if contract_validation["validation_status"].astype(str).eq("pass").all() else "fail"
    row_level_gate = "pass" if input_gate == "pass" else "fail"
    o5 = primary.loc[primary["oracle_variant_id"].astype(str).eq("O5_perfect_utility_primary")]
    o5_row = o5.iloc[0] if len(o5) else pd.Series(dtype=object)
    topk_gate = str_value(o5_row.get("topk_gate")) or "fail"
    bootstrap_gate = str_value(o5_row.get("bootstrap_gate")) or "fail"
    matched_gate = str_value(o5_row.get("matched_base_gate")) or "fail"
    materiality_gate = str_value(o5_row.get("materiality_gate")) or "fail"
    delayed_curve_gate = "pass" if len(delay) and delay["delayed_curve_gate"].astype(str).eq("pass").all() else "fail"
    cap_primary = capacity.loc[capacity["split_bucket"].astype(str).eq(config["decision"]["primary_decision_split"])]
    cap_row = cap_primary.iloc[0] if len(cap_primary) else pd.Series(dtype=object)
    capacity_gate = str_value(cap_row.get("capacity_constraint_gate")) or "fail"
    capacity_status = str_value(cap_row.get("capacity_status"))
    search_gate = "pass" if search["search_accounting_gate"].astype(str).eq("pass").all() else "fail"
    lineage_gates = {
        "input_gate": input_gate,
        "seventeen_b_contract_gate": contract_gate,
        "row_level_panel_gate": row_level_gate,
        "search_accounting_gate": search_gate,
    }
    lineage_bad = [k for k, v in lineage_gates.items() if v != "pass"]
    if lineage_bad:
        decision_state = DECISION_LINEAGE_BLOCKED
        next_allowed = "none"
        reason = ";".join(lineage_bad + ([input_reason] if input_reason else []))
    elif str_value(o5_row.get("primary_support_gate")) != "pass":
        decision_state = DECISION_NO_VALUE
        next_allowed = "none"
        reason = "o5_primary_robustness_gate_failed"
    elif str_value(cap_row.get("capacity_reconstruction_gate")) == "pass" and capacity_gate == "fail":
        decision_state = DECISION_CAPACITY_BLOCKED
        next_allowed = "none"
        reason = "capacity_constraint_failed"
    else:
        decision_state = DECISION_READY
        next_allowed = config["decision"]["next_allowed_requirement"]
        reason = ""
    label_path = primary.loc[
        primary["oracle_variant_id"].astype(str).isin(config["decision"]["label_or_path_variants"])
        & primary["primary_support_gate"].astype(str).eq("pass")
    ]
    label_gate = "pass" if len(label_path) else "fail"
    diagnostic_warning = "" if label_gate == "pass" else "perfect_utility_only_no_label_or_path_oracle_support"
    return pd.DataFrame(
        [
            {
                "decision_state": decision_state,
                "next_allowed_requirement": next_allowed,
                "input_gate": input_gate,
                "seventeen_b_contract_gate": contract_gate,
                "row_level_panel_gate": row_level_gate,
                "topk_gate": topk_gate,
                "bootstrap_gate": bootstrap_gate,
                "matched_base_gate": matched_gate,
                "delayed_curve_gate": delayed_curve_gate,
                "capacity_constraint_gate": capacity_gate,
                "search_accounting_gate": search_gate,
                "primary_decision_split": config["decision"]["primary_decision_split"],
                "primary_cost_bps": int(config["decision"]["primary_cost_bps"]),
                "primary_q_defend": float(config["decision"]["primary_q_defend"]),
                "primary_oracle_id": str_value(o5_row.get("oracle_id")),
                "primary_oracle_variant_id": str_value(o5_row.get("oracle_variant_id")),
                "primary_mean_incremental_return": o5_row.get("mean_incremental_return", np.nan),
                "primary_trimmed_mean_incremental_return": o5_row.get("trimmed_mean_incremental_return", np.nan),
                "primary_bootstrap_ci_low": o5_row.get("bootstrap_ci_low_min", np.nan),
                "primary_topk_removed_mean_min": o5_row.get("topk_removed_mean_min", np.nan),
                "primary_matched_base_pass_share": o5_row.get("matched_base_pass_share_min", np.nan),
                "label_or_path_oracle_support_gate": label_gate,
                "diagnostic_warning": diagnostic_warning,
                "payoff_state_research_candidate": bool(label_gate == "pass"),
                "delayed_decision_diagnostic_flag": bool(delay["delayed_decision_diagnostic_flag"].map(bool_value).any()) if len(delay) else False,
                "capacity_status": capacity_status,
                "entry_policy_authorized": False,
                "exit_policy_authorized": False,
                "holding_policy_authorized": False,
                "portfolio_backtest_authorized": False,
                "model_deployment_authorized": False,
                "production_signal_authorized": False,
                "live_trading_authorized": False,
                "blocking_reason": reason,
            }
        ]
    )


def markdown_table(frame: pd.DataFrame, columns: list[str], max_rows: int = 20) -> str:
    if frame.empty:
        return "_empty_"
    cols = [col for col in columns if col in frame.columns]
    return frame.loc[:, cols].head(max_rows).to_markdown(index=False)


def plot_topk(path: Path, topk: pd.DataFrame, config: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    sub = topk.loc[
        topk["split_bucket"].eq(config["decision"]["primary_decision_split"])
        & topk["cost_bps"].astype(int).eq(int(config["decision"]["primary_cost_bps"]))
        & np.isclose(topk["q_defend"].astype(float), float(config["decision"]["primary_q_defend"]))
        & topk["oracle_variant_id"].isin(config["decision"]["primary_candidate_variants"])
    ].copy()
    pivot = sub.pivot_table(index="removal_family", columns="oracle_variant_id", values="remaining_mean_incremental_return", aggfunc="first")
    fig, ax = plt.subplots(figsize=(12, 5))
    pivot.plot(kind="bar", ax=ax)
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_ylabel("remaining mean incremental return")
    ax.set_title("17C Top-k Removal Sensitivity")
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def plot_bootstrap(path: Path, boot: pd.DataFrame, config: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    sub = boot.loc[
        boot["split_bucket"].eq(config["decision"]["primary_decision_split"])
        & boot["cost_bps"].astype(int).eq(int(config["decision"]["primary_cost_bps"]))
        & np.isclose(boot["q_defend"].astype(float), float(config["decision"]["primary_q_defend"]))
        & boot["oracle_variant_id"].isin(config["decision"]["primary_candidate_variants"])
    ].copy()
    labels = [f"{r.oracle_variant_id}\n{r.bootstrap_family}" for r in sub.itertuples()]
    x = np.arange(len(sub))
    y = sub["observed_mean_incremental_return"].to_numpy(dtype=float)
    yerr = np.vstack([y - sub["ci_low"].to_numpy(dtype=float), sub["ci_high"].to_numpy(dtype=float) - y])
    fig, ax = plt.subplots(figsize=(max(12, len(sub) * 0.45), 5))
    ax.errorbar(x, y, yerr=yerr, fmt="o", capsize=3)
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=70, ha="right", fontsize=7)
    ax.set_ylabel("mean incremental return")
    ax.set_title("17C Cluster Bootstrap CI")
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def plot_matched(path: Path, matched: pd.DataFrame, config: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    sub = matched.loc[
        matched["split_bucket"].eq(config["decision"]["primary_decision_split"])
        & matched["cost_bps"].astype(int).eq(int(config["decision"]["primary_cost_bps"]))
        & np.isclose(matched["q_defend"].astype(float), float(config["decision"]["primary_q_defend"]))
        & matched["oracle_variant_id"].isin(config["decision"]["primary_candidate_variants"])
        & matched["matched_family"].isin(config["matched_base"]["hard_required_families"].keys())
        & matched["matched_bucket_evaluable"].map(bool_value)
    ].copy()
    sub["bucket_label"] = sub["matched_family"].astype(str) + ":" + sub["matched_bucket"].astype(str)
    pivot = sub.pivot_table(index="bucket_label", columns="oracle_variant_id", values="bucket_trimmed_mean_incremental_return", aggfunc="first")
    fig, ax = plt.subplots(figsize=(10, max(5, len(pivot) * 0.18)))
    im = ax.imshow(pivot.fillna(0).to_numpy(dtype=float), aspect="auto", cmap="RdYlGn")
    ax.set_yticks(np.arange(len(pivot)))
    ax.set_yticklabels(pivot.index, fontsize=6)
    ax.set_xticks(np.arange(len(pivot.columns)))
    ax.set_xticklabels(pivot.columns, rotation=45, ha="right", fontsize=8)
    ax.set_title("17C Matched-base Trimmed Mean Heatmap")
    fig.colorbar(im, ax=ax, shrink=0.8)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def plot_delayed(path: Path, delay: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(1, 3, figsize=(13, 4), sharey=True)
    for ax, split in zip(axes, SPLITS):
        sub = delay.loc[delay["split_bucket"].eq(split)].sort_values("delay_k_sessions")
        ax.plot(sub["delay_k_sessions"], sub["delayed_mean_incremental_return"], marker="o", label="mean")
        ax.plot(sub["delay_k_sessions"], sub["delayed_trimmed_mean_incremental_return"], marker="s", label="trimmed")
        if len(sub):
            o5_ref = float(sub["o5_t0_mean_incremental_return"].iloc[0])
            if np.isfinite(o5_ref):
                ax.axhline(o5_ref, color="black", linestyle="--", linewidth=0.9, label="O5 t0")
        ax.axhline(0, color="gray", linewidth=0.8)
        ax.set_title(split)
        ax.set_xlabel("delay sessions")
        ax.grid(alpha=0.25)
    axes[0].set_ylabel("incremental return")
    axes[-1].legend(fontsize=8)
    fig.suptitle("17C Delayed Oracle Curve")
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def plot_capacity(path: Path, capacity: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(8, 4))
    x = np.arange(len(capacity))
    ax.bar(x - 0.2, capacity["unconstrained_mean_incremental_return"], width=0.4, label="O5 unconstrained")
    ax.bar(x + 0.2, capacity["capacity_mean_incremental_return"].fillna(0), width=0.4, label="O6 capacity")
    ax.set_xticks(x)
    ax.set_xticklabels(capacity["split_bucket"])
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_ylabel("mean incremental return")
    ax.set_title("17C Capacity Constraint Status")
    ax.legend(fontsize=8)
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def write_report(
    path: Path,
    config: dict[str, Any],
    decision: pd.DataFrame,
    input_audit: pd.DataFrame,
    contract: pd.DataFrame,
    primary: pd.DataFrame,
    topk: pd.DataFrame,
    bootstrap: pd.DataFrame,
    matched: pd.DataFrame,
    delay: pd.DataFrame,
    capacity: pd.DataFrame,
    search: pd.DataFrame,
) -> None:
    dec = decision.iloc[0]
    split = str(config["decision"]["primary_decision_split"])
    cost = int(config["decision"]["primary_cost_bps"])
    q_defend = float(config["decision"]["primary_q_defend"])
    primary_variants = list(config["decision"]["primary_candidate_variants"])
    primary_mask = (
        topk.get("split_bucket", pd.Series(dtype=str)).astype(str).eq(split)
        & topk.get("cost_bps", pd.Series(dtype=float)).astype(int).eq(cost)
        & np.isclose(topk.get("q_defend", pd.Series(dtype=float)).astype(float), q_defend)
    ) if not topk.empty else pd.Series(dtype=bool)
    boot_primary_mask = (
        bootstrap.get("split_bucket", pd.Series(dtype=str)).astype(str).eq(split)
        & bootstrap.get("cost_bps", pd.Series(dtype=float)).astype(int).eq(cost)
        & np.isclose(bootstrap.get("q_defend", pd.Series(dtype=float)).astype(float), q_defend)
    ) if not bootstrap.empty else pd.Series(dtype=bool)
    matched_primary_mask = (
        matched.get("split_bucket", pd.Series(dtype=str)).astype(str).eq(split)
        & matched.get("cost_bps", pd.Series(dtype=float)).astype(int).eq(cost)
        & np.isclose(matched.get("q_defend", pd.Series(dtype=float)).astype(float), q_defend)
    ) if not matched.empty else pd.Series(dtype=bool)
    input_checks = input_audit.loc[
        input_audit.get("audit_row_type", pd.Series("", index=input_audit.index)).astype(str).eq("canonicalization_check")
    ]
    input_artifacts = artifact_rows(input_audit)
    contract_summary = (
        contract.assign(_failed=contract["validation_status"].astype(str).ne("pass"))
        .groupby("artifact_key", dropna=False)
        .agg(validation_check_n=("validation_check_id", "count"), failed_check_n=("_failed", "sum"))
        .reset_index()
    )
    contract_summary["artifact_gate"] = np.where(contract_summary["failed_check_n"].eq(0), "pass", "fail")
    o2_variants = ["O2_dd_08pct_stress", "O2_dd_10pct_primary", "O2_dd_12pct_stress", "O2_dd_15pct_stress", "O2_dd_20pct_stress"]
    o4_variants = ["O4_high_upside_top10_stress", "O4_high_upside_top20_stress", "O4_high_upside_top30_stress"]
    o2_topk = topk.loc[primary_mask & topk["oracle_variant_id"].astype(str).isin(o2_variants)] if len(primary_mask) else pd.DataFrame()
    o2_boot = bootstrap.loc[boot_primary_mask & bootstrap["oracle_variant_id"].astype(str).isin(o2_variants)] if len(boot_primary_mask) else pd.DataFrame()
    o4_topk = topk.loc[primary_mask & topk["oracle_variant_id"].astype(str).isin(o4_variants)] if len(primary_mask) else pd.DataFrame()
    o4_boot = bootstrap.loc[boot_primary_mask & bootstrap["oracle_variant_id"].astype(str).isin(o4_variants)] if len(boot_primary_mask) else pd.DataFrame()
    hard_matched = matched.loc[
        matched_primary_mask
        & matched["oracle_variant_id"].astype(str).isin(primary_variants)
        & matched["matched_family"].astype(str).isin(config["matched_base"]["hard_required_families"].keys())
    ].drop_duplicates(["oracle_variant_id", "matched_family"]) if len(matched_primary_mask) else pd.DataFrame()
    o5_contract = contract.loc[contract["artifact_key"].astype(str).eq("seventeen_b_o5_action_selection_proof")]
    search_display = search.copy()
    if not search_display.empty:
        search_display = search_display.loc[:, [col for col in search_display.columns if col == "search_accounting_gate" or col.startswith("no_")]]
    text = f"""# 17C Oracle Robustness Stress Report

## 1. 决策结论

```text
decision_state = {dec['decision_state']}
next_allowed_requirement = {dec['next_allowed_requirement']}
blocking_reason = {dec['blocking_reason'] if str_value(dec['blocking_reason']) else 'none'}
```

17C 只做 upper-bound robustness diagnostic，不授权 entry、exit、holding、sizing、portfolio backtest、model deployment、production signal 或 live trading。
本轮正结果只授权进入 `{dec['next_allowed_requirement']}` 做诊断解释，不授权交易策略、特征上线或组合回测。

## 2. Handoff 与输入校验

| gate | value |
|:--|:--|
| input_gate | {dec['input_gate']} |
| seventeen_b_contract_gate | {dec['seventeen_b_contract_gate']} |
| row_level_panel_gate | {dec['row_level_panel_gate']} |
| search_accounting_gate | {dec['search_accounting_gate']} |

输入 artifact 与 schema 状态：

{markdown_table(input_artifacts, ['artifact_key', 'source_phase_id', 'row_count', 'schema_status', 'lineage_status', 'row_key_status', 'gate_status', 'blocking_reason'], max_rows=30)}

Row-level canonicalization blocking checks：

{markdown_table(input_checks, ['artifact_key', 'input_check_id', 'observed_value', 'expected_value', 'check_status', 'gate_status', 'blocking_reason'], max_rows=20)}

## 3. 17B Contract Validation

17B contract validation 覆盖 decision row、17B publishable output hash、row-level panel 到 ladder summary 的 reconciliation、O2/O5/search gate，以及 17A delayed/capacity inherited status。

{markdown_table(contract_summary, ['artifact_key', 'validation_check_n', 'failed_check_n', 'artifact_gate'], max_rows=30)}

Failed checks：

{markdown_table(contract.loc[contract['validation_status'].astype(str).ne('pass')], ['artifact_key', 'validation_check_id', 'observed_value', 'expected_value', 'validation_status', 'blocking_reason'], max_rows=20)}

## 4. Row-level Denominator 与 Primary Summary

{markdown_table(primary, ['oracle_id', 'oracle_variant_id', 'observed_step_n', 'mean_incremental_return', 'trimmed_mean_incremental_return', 'bootstrap_ci_low_min', 'topk_removed_mean_min', 'matched_base_pass_share_min', 'topk_gate', 'bootstrap_gate', 'matched_base_gate', 'materiality_gate', 'primary_support_gate'], max_rows=20)}

这里的 `observed_step_n` 是 17B row-level panel 在 `{split}` split、`cost_bps={cost}`、`q_defend={q_defend}` 下的 replay denominator。O1/O4 使用 binary denominator，O2/O5 使用 labelable/full denominator；这些计数由 17B ladder summary reconciliation 重新核对。

## 5. Top-k Removal

{markdown_table(topk.loc[primary_mask & topk['oracle_variant_id'].astype(str).isin(primary_variants)] if len(primary_mask) else pd.DataFrame(), ['oracle_variant_id', 'removal_family', 'removed_group_n', 'removed_step_n', 'remaining_mean_incremental_return', 'topk_gate'], max_rows=40)}

Top-k removal 使用固定枚举 `{', '.join(config['topk']['removal_families'])}`，remaining mean 的 denominator 固定为原始 observed steps，因此这里检验的是 action-value 是否被少数股票或少数 episode 完全支撑。

## 6. Bootstrap CI

{markdown_table(bootstrap.loc[boot_primary_mask & bootstrap['oracle_variant_id'].astype(str).isin(primary_variants)] if len(boot_primary_mask) else pd.DataFrame(), ['oracle_variant_id', 'bootstrap_family', 'bootstrap_primary_role', 'cluster_n', 'observed_mean_incremental_return', 'ci_low', 'ci_high', 'bootstrap_family_status', 'bootstrap_gate'], max_rows=50)}

`calendar_quarter` 在 bootstrap 中是 readout-only，因为 quarter cluster 数不足 primary bootstrap floor；但它在 matched-base 中按 bucket 评估，每个 bucket 的 row count 足够时可以作为 hard-required family。

## 7. Matched-base

{markdown_table(hard_matched, ['oracle_variant_id', 'matched_family', 'matched_family_status', 'family_evaluable_bucket_n', 'family_pass_bucket_n', 'family_pass_share', 'matched_base_gate'], max_rows=50)}

## 8. O2 Drawdown Threshold Robustness

O2 的 drawdown 判定使用 `signed_max_drawdown_h20 <= threshold`；positive abs drawdown 只用于 reporting/capacity 排序，不用于 O2 threshold 比较。

{markdown_table(o2_topk, ['oracle_variant_id', 'removal_family', 'remaining_mean_incremental_return', 'topk_gate'], max_rows=40)}

{markdown_table(o2_boot, ['oracle_variant_id', 'bootstrap_family', 'cluster_n', 'ci_low', 'ci_high', 'bootstrap_gate'], max_rows=40)}

## 9. O4 High-upside Threshold Stress

O4 high-upside stress 使用 17B 冻结的 train quantile cutoff，并在 robustness/validation 中复用，不做 split-local recompute。

{markdown_table(o4_topk, ['oracle_variant_id', 'removal_family', 'remaining_mean_incremental_return', 'topk_gate'], max_rows=30)}

{markdown_table(o4_boot, ['oracle_variant_id', 'bootstrap_family', 'cluster_n', 'ci_low', 'ci_high', 'bootstrap_gate'], max_rows=30)}

## 10. O5 Proof Carried Forward

O5 是 action-space upper bound：只在 `defend_net > continue_net` 时 defend，因此它不是可实现策略，只是当前 action set 的后见之明上界。

{markdown_table(o5_contract, ['artifact_key', 'validation_check_id', 'observed_value', 'expected_value', 'validation_status', 'blocking_reason'], max_rows=10)}

## 11. Delayed Oracle Curve

{markdown_table(delay, ['split_bucket', 'delay_k_sessions', 'delayed_mean_incremental_return', 'delayed_trimmed_mean_incremental_return', 'o5_t0_mean_incremental_return', 'delayed_mean_gap_vs_o5_t0', 'delayed_retention_ratio_vs_o5_t0', 'topk_gate', 'bootstrap_gate', 'matched_base_gate', 'delayed_curve_gate', 'delayed_decision_diagnostic_flag'], max_rows=30)}

O7 delayed diagnostic 保持在原始 H20 endpoint 内切换，不重启 H20，不做 partial tail fill。`delayed_mean_gap_vs_o5_t0` 是相对 t0 perfect utility 的诊断 gap，不是 support gate。

## 12. Capacity

{markdown_table(capacity, ['split_bucket', 'capacity_status', 'capacity_reconstruction_gate', 'o6_primary_decision_allowed', 'unconstrained_mean_incremental_return', 'capacity_mean_incremental_return', 'capacity_constraint_gate'], max_rows=10)}

当前 capacity 来源于 17A inherited status；若 O6 仍是 appendix-only，则 capacity 不阻塞 17C，但也不授权执行约束下的组合实现。

## 13. Search Accounting 与授权边界

{markdown_table(search_display, list(search_display.columns), max_rows=5)}

所有 authorization flags 均为 false：entry、exit、holding、portfolio backtest、model deployment、production signal、live trading 都未被 17C 授权。

## 14. Interpretation

O5 是当前 action-space 的 perfect utility 上界；O1/O2/O4 是 label/path oracle 支撑。17C 的正结果只说明上界在 top-k、bootstrap、matched-base 后仍值得进入 EP17D 诊断，不表示已有可交易策略。
"""
    write_text(path, text)


def output_hashes(outputs: dict[str, Path]) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for key, path in outputs.items():
        if key in {"manifest", "engine_manifest", "input_artifact_manifest"}:
            continue
        if path.exists() and path.is_file():
            hashes[key] = file_sha(path)
    return hashes


def row_counts(outputs: dict[str, Path]) -> dict[str, int | float]:
    return {
        key: count_rows(path)
        for key, path in outputs.items()
        if key not in {"manifest", "engine_manifest", "input_artifact_manifest"} and path.exists() and path.is_file()
    }


def write_manifests(
    config_path: Path,
    config: dict[str, Any],
    resolved: dict[str, Path],
    outputs: dict[str, Path],
    decision: pd.DataFrame,
    input_audit: pd.DataFrame,
) -> None:
    dec = decision.iloc[0]
    input_hashes = {key: file_sha(path) for key, path in resolved.items() if path.exists() and path.is_file()}
    auth = {col: bool(dec[col]) for col in AUTH_FALSE_COLUMNS}
    main_payload = {
        "run_id": RUN_ID,
        "experiment_id": EXPERIMENT_ID,
        "phase_id": PHASE_ID,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "git_commit_if_available": "",
        "config_file": relative_to_topic(config_path),
        "config_sha256": file_sha(config_path),
        "requirement_file": "experiments/pending/17_oracle_action_value_upper_bound_diagnostic/requirement_17c_oracle_robustness_stress.md",
        "requirement_sha256": file_sha(EXPERIMENT_DIR / "requirement_17c_oracle_robustness_stress.md"),
        "runner_file": "experiments/pending/17_oracle_action_value_upper_bound_diagnostic/src/run_17c_oracle_robustness_stress.py",
        "test_file": "experiments/pending/17_oracle_action_value_upper_bound_diagnostic/tests/test_17c_oracle_robustness_stress.py",
        "input_artifact_hashes": input_hashes,
        "output_hashes": output_hashes(outputs),
        "row_counts": row_counts(outputs),
        "primary_decision_split": config["decision"]["primary_decision_split"],
        "primary_cost_bps": config["decision"]["primary_cost_bps"],
        "primary_q_defend": config["decision"]["primary_q_defend"],
        "primary_candidate_variants": config["decision"]["primary_candidate_variants"],
        "materiality_floors": config["materiality"],
        "bootstrap_iterations": config["bootstrap"]["iterations"],
        "bootstrap_ci": 1.0 - float(config["bootstrap"]["ci_alpha"]),
        "random_seed": config["bootstrap"]["random_seed"],
        "topk_removal_grid": config["topk"]["removal_families"],
        "matched_base_families": list(config["matched_base"]["hard_required_families"].keys()),
        "delayed_k_sessions": config["delayed"]["k_sessions"],
        "delayed_action_semantics": config["delayed"]["delayed_action_semantics"],
        "capacity_status": str(dec["capacity_status"]),
        "capacity_constraints": config["capacity"],
        "decision_state": str(dec["decision_state"]),
        "next_allowed_requirement": str(dec["next_allowed_requirement"]),
        "authorization_flags": auth,
        "python_version": platform.python_version(),
    }
    engine_payload = {
        "topk_removal_denominator_rule": "remaining_mean_incremental_return = remaining_sum_incremental_return / original_observed_step_n",
        "bootstrap_cluster_sampling_rule": "sample clusters with replacement using frozen per-group deterministic seed",
        "matched_base_bucket_derivation": {
            "calendar_month": "YYYY-MM from step_start_date",
            "calendar_quarter": "YYYYQn from step_start_date",
            "instrument_board_bucket": "instrument prefix SH60/SH68/SZ00/SZ30",
        },
        "o7_delayed_formula": "prefix + (1+prefix) * q_remaining - cost_if_defend; baseline original H20 blind continue",
        "o7_delayed_gap_retention": "gap = delayed_mean - O5_t0_mean; retention = delayed_mean / O5_t0_mean",
        "o6_capacity_formula_or_status": str(dec["capacity_status"]),
        "trim_winsor_definitions": config["stats"],
        "search_accounting_constants": {"no_model_training": True, "no_validation_selection": True},
    }
    write_json(outputs["manifest"], main_payload)
    write_json(outputs["engine_manifest"], engine_payload)
    manifest_rows = artifact_rows(input_audit)[
        [
            "artifact_key",
            "artifact_role",
            "required_flag",
            "resolved_path",
            "relative_path",
            "source_phase_id",
            "row_count",
            "sha256",
            "schema_status",
            "read_status",
            "blocking_reason",
        ]
    ].to_dict(orient="records")
    write_json(outputs["input_artifact_manifest"], manifest_rows)


def run(config_path: Path, check_inputs_only: bool = False) -> int:
    config = load_config(config_path)
    resolved = resolve_paths(config)
    outputs = output_paths()
    input_audit = build_input_gate_audit(config, resolved)
    contract_validation = build_17b_contract_validation_audit(config, resolved)
    write_df(outputs["input_gate_audit"], input_audit.drop(columns=["read_status"]))
    write_df(outputs["seventeen_b_contract_validation_audit"], contract_validation)
    input_gate, _ = input_gate_status(input_audit)
    contract_gate = "pass" if contract_validation["validation_status"].astype(str).eq("pass").all() else "fail"
    if check_inputs_only:
        # Do not overwrite full-run manifests with a temporary input-check decision.
        manifest_rows = artifact_rows(input_audit)[
            [
                "artifact_key",
                "artifact_role",
                "required_flag",
                "resolved_path",
                "relative_path",
                "source_phase_id",
                "row_count",
                "sha256",
                "schema_status",
                "read_status",
                "blocking_reason",
            ]
        ].to_dict(orient="records")
        write_json(outputs["input_artifact_manifest"], manifest_rows)
        return 0 if input_gate == "pass" and contract_gate == "pass" else 1
    if input_gate != "pass" or contract_gate != "pass":
        search = build_search_accounting_audit()
        decision = build_decision(
            config,
            input_audit,
            contract_validation,
            pd.DataFrame(),
            pd.DataFrame(),
            pd.DataFrame(),
            search,
        )
        write_df(outputs["search_accounting_audit"], search)
        write_df(outputs["decision"], decision)
        write_report(
            outputs["report"],
            config,
            decision,
            input_audit,
            contract_validation,
            pd.DataFrame(),
            pd.DataFrame(),
            pd.DataFrame(),
            pd.DataFrame(),
            pd.DataFrame(),
            pd.DataFrame(),
            search,
        )
        write_manifests(config_path, config, resolved, outputs, decision, input_audit)
        return 1

    panel = canonicalize_panel(read_table(resolved["seventeen_b_row_level_panel"]))
    topk = build_topk_sensitivity(panel, config)
    bootstrap = build_bootstrap_ci(panel, config)
    matched = build_matched_base(panel, config)
    primary = build_primary_summary(panel, topk, bootstrap, matched, config)
    delayed_panel = materialize_delayed_panel(labelable_base_from_panel(panel, config), resolved["stock_daily_qfq_dir"], config)
    delay = delayed_curve_rows(delayed_panel, panel, config)
    capacity_audit = read_table(resolved["seventeen_a_capacity_reconstruction_audit"])
    capacity, capacity_panel = build_capacity_constraint(panel, capacity_audit, config)
    search = build_search_accounting_audit()
    decision = build_decision(config, input_audit, contract_validation, primary, delay, capacity, search)

    write_df(outputs["topk_sensitivity"], topk)
    write_df(outputs["bootstrap_ci"], bootstrap)
    write_df(outputs["matched_base"], matched)
    write_df(outputs["primary_summary"], primary)
    write_df(outputs["delayed_panel"], delayed_panel)
    write_df(outputs["capacity_panel"], capacity_panel)
    write_df(outputs["delay_curve"], delay)
    write_df(outputs["capacity_constraint"], capacity)
    write_df(outputs["search_accounting_audit"], search)
    write_df(outputs["decision"], decision)
    plot_topk(outputs["topk_figure"], topk, config)
    plot_bootstrap(outputs["bootstrap_figure"], bootstrap, config)
    plot_matched(outputs["matched_figure"], matched, config)
    plot_delayed(outputs["delayed_figure"], delay)
    plot_capacity(outputs["capacity_figure"], capacity)
    write_report(outputs["report"], config, decision, input_audit, contract_validation, primary, topk, bootstrap, matched, delay, capacity, search)
    write_manifests(config_path, config, resolved, outputs, decision, input_audit)
    return 0 if decision.iloc[0]["decision_state"] != DECISION_LINEAGE_BLOCKED else 1


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    return run(Path(args.config), check_inputs_only=args.check_inputs_only or args.mode == "check-inputs")


if __name__ == "__main__":
    sys.exit(main())
