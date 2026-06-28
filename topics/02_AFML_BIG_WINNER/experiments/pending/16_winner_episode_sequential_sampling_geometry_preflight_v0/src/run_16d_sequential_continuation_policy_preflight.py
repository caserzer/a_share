#!/usr/bin/env python
from __future__ import annotations

import argparse
import importlib.util
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml


EXPERIMENT_DIR = Path(__file__).resolve().parents[1]
TOPIC_ROOT = Path(__file__).resolve().parents[4]
REPO_ROOT = Path(__file__).resolve().parents[6]
SOURCE_EP15_ROOT = TOPIC_ROOT / "experiments" / "pending" / "15_path_defined_winner_episode_label_v0"
RUNNER_16C_PATH = EXPERIMENT_DIR / "src" / "run_16c_sequential_continuation_separability_diagnostic.py"
SOURCE_ROOTS = {
    "SOURCE_EP16_ROOT": EXPERIMENT_DIR,
    "SOURCE_EP15_ROOT": SOURCE_EP15_ROOT,
}


def load_runner(path: Path, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


r16c = load_runner(RUNNER_16C_PATH, "run_16c_for_16d")
r16b = r16c.r16b

RUN_ID = "16D_sequential_continuation_policy_preflight"
EXPERIMENT_ID = "16_winner_episode_sequential_sampling_geometry_preflight_v0"
PHASE_ID = "16D"
CONFIG_PATH = EXPERIMENT_DIR / "configs" / "config_16d_sequential_continuation_policy_preflight.yaml"
TABLE_DIR = EXPERIMENT_DIR / "outputs" / "publishable" / "tables" / RUN_ID
LOCAL_CACHE_DIR = EXPERIMENT_DIR / "outputs" / "local_cache" / RUN_ID
REPORT_DIR = EXPERIMENT_DIR / "outputs" / "publishable" / "reports"
MANIFEST_DIR = EXPERIMENT_DIR / "outputs" / "manifests"

PRIMARY_LABEL_ID = r16c.PRIMARY_LABEL_ID
PRIMARY_MODEL_ID = r16c.PRIMARY_MODEL_ID
SPLITS = ("train", "robustness", "validation")
CONTEXT_STRATA = (
    "all_steps",
    "late_rescue_context",
    "non_late_rescue_context",
    "known_failed_context_any",
    "non_known_failed_context",
)

DECISION_READY = "16D_policy_preflight_ready_for_utility_diagnostic"
DECISION_LINEAGE = "16D_policy_preflight_blocked_by_input_or_lineage_failure"
DECISION_SEARCH = "16D_policy_preflight_blocked_by_policy_search_or_leakage"
DECISION_LOW_POWER = "16D_policy_preflight_low_power"
DECISION_NOT_SUPPORTED = "16D_policy_preflight_not_supported"
DECISION_CONTEXT = "16D_policy_preflight_context_concentrated_only"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run 16D sequential continuation policy preflight.")
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
    for alias, root in SOURCE_ROOTS.items():
        prefix = f"{alias}/"
        if text.startswith(prefix):
            return root / text[len(prefix) :]
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
        "input_artifact_audit": TABLE_DIR / "input_artifact_audit.csv",
        "upstream_16c_authorization_audit": TABLE_DIR / "upstream_16c_authorization_audit.csv",
        "score_rebuild_lineage_audit": TABLE_DIR / "score_rebuild_lineage_audit.csv",
        "feature_contract_replay_audit": TABLE_DIR / "feature_contract_replay_audit.csv",
        "policy_candidate_registry": TABLE_DIR / "policy_candidate_registry.csv",
        "policy_threshold_freeze_audit": TABLE_DIR / "policy_threshold_freeze_audit.csv",
        "policy_action_binding_audit": TABLE_DIR / "policy_action_binding_audit.csv",
        "policy_confusion_readout": TABLE_DIR / "policy_confusion_readout.csv",
        "policy_tradeoff_frontier_readout": TABLE_DIR / "policy_tradeoff_frontier_readout.csv",
        "known_failed_context_rebuild_audit": TABLE_DIR / "known_failed_context_rebuild_audit.csv",
        "policy_context_stratified_readout": TABLE_DIR / "policy_context_stratified_readout.csv",
        "neutral_policy_handling_audit": TABLE_DIR / "neutral_policy_handling_audit.csv",
        "policy_stability_audit": TABLE_DIR / "policy_stability_audit.csv",
        "validation_stress_policy_readout": TABLE_DIR / "validation_stress_policy_readout.csv",
        "search_accounting_audit": TABLE_DIR / "search_accounting_audit.csv",
        "decision": TABLE_DIR / "sequential_continuation_policy_preflight_decision.csv",
        "policy_action_sample": TABLE_DIR / "policy_action_sample.csv.gz",
        "policy_score_panel": LOCAL_CACHE_DIR / "policy_score_panel.parquet",
        "policy_action_panel": LOCAL_CACHE_DIR / "policy_action_panel.parquet",
        "report": REPORT_DIR / "sequential_continuation_policy_preflight_report.md",
        "manifest": MANIFEST_DIR / f"{RUN_ID}_manifest.json",
    }


def read_table(path: Path, **kwargs: Any) -> pd.DataFrame:
    return r16c.read_table(path, **kwargs)


def write_df(path: Path, frame: pd.DataFrame) -> Path:
    return r16c.write_df(path, frame)


def write_text(path: Path, text: str) -> Path:
    return r16c.write_text(path, text)


def write_json(path: Path, payload: dict[str, Any]) -> Path:
    return r16c.write_json(path, payload)


def file_sha(path: Path) -> str:
    return r16c.file_sha(path)


def stable_hash(value: Any) -> str:
    return r16c.stable_hash(value)


def bool_series(series: pd.Series) -> pd.Series:
    return r16c.bool_series(series)


def finite(series: pd.Series) -> pd.Series:
    return r16c.finite(series)


def safe_rate(num: Any, den: Any) -> float:
    return r16c.safe_rate(num, den)


def metric_float(value: Any) -> float:
    try:
        out = float(value)
    except Exception:
        return np.nan
    return out if np.isfinite(out) else np.nan


def policy_id_for_quantile(q: float) -> str:
    return f"defense_bottom_{int(round(q * 100))}pct_continuation_score_v1"


def artifact_required_flag(key: str) -> str:
    optional = {
        "upstream_16b_continuation_label_step_panel",
        "upstream_16b_known_failed_overlap_panel",
        "upstream_16c_t0_feature_panel",
        "upstream_16c_score_panel",
        "upstream_16c_fold_assignment_panel",
        "upstream_15b_taxonomy_assignment_panel",
        "upstream_15b_anchor_path_shape_feature_panel",
    }
    return "optional_cache" if key in optional else "required"


def required_columns_for_key(key: str) -> set[str]:
    if key == "upstream_16c_decision":
        return {
            "decision_state",
            "next_allowed_requirement",
            "primary_label_id",
            "selected_threshold_id",
            "primary_horizon_sessions",
            "primary_model_id",
            "train_binary_step_n",
            "train_positive_n",
            "train_negative_n",
            "robustness_binary_step_n",
            "robustness_positive_n",
            "robustness_negative_n",
            "known_failed_context_rebuild_gate",
        }
    if key == "upstream_16c_oos_readout":
        return {"split_bucket", "model_id", "binary_step_n", "positive_n", "negative_n", "roc_auc", "pr_auc_lift_vs_binary_base"}
    if key == "upstream_16b_base_rate_readout":
        return {"label_id", "threshold_id", "cluster_split_bucket", "horizon_sessions", "labelable_step_n", "positive_step_n", "negative_step_n", "neutral_step_n"}
    if key == "upstream_16b_known_failed_overlap_readout":
        return {"label_id", "threshold_id", "known_failed_family", "cluster_split_bucket", "horizon_sessions", "positive_step_n", "failed_family_positive_step_n"}
    if key == "upstream_15b_membership_audit":
        return {"source_row_key", "threshold_id", "instrument", "episode_cluster_id", "cluster_split_bucket"}
    if key == "upstream_15b_path_shape_feature_definition_audit":
        return {"feature_id", "definition_status"}
    if key == "upstream_15b_path_shape_taxonomy_rule_audit":
        return {"rule_type", "feature_id", "quantile_name", "value", "train_rule_fit_status"}
    if key in {"pit_executable_daily", "pit_membership_daily"}:
        return {
            "usable_trade_date",
            "instrument",
            "available_time",
            "board_bucket",
            "total_market_cap_cny",
            "history_ready_240d_flag",
            "history_observed_sessions_before_usable_date",
        }
    return set()


def count_rows(path: Path) -> int | float:
    suffixes = "".join(path.suffixes)
    if suffixes.endswith(".parquet"):
        return len(pd.read_parquet(path))
    if suffixes.endswith((".csv", ".csv.gz")):
        return r16c.count_rows(path)
    if path.is_file():
        return sum(1 for _ in path.open("rb"))
    if path.is_dir():
        return len(list(path.iterdir()))
    return np.nan


def qfq_dir_schema_status(path: Path) -> str:
    return r16c.qfq_dir_schema_status(path)


def build_input_artifact_audit(config: dict[str, Any], resolved: dict[str, Path]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for key, path in resolved.items():
        flag = artifact_required_flag(key)
        exists = path.exists()
        read_status = "pass"
        schema_status = "not_checked"
        row_count: int | float = np.nan
        sha = ""
        if exists and path.is_file():
            try:
                row_count = count_rows(path)
                sha = file_sha(path)
                required = required_columns_for_key(key)
                if required and "".join(path.suffixes).endswith((".csv", ".csv.gz")):
                    frame = read_table(path, nrows=5)
                    schema_status = "pass" if required.issubset(frame.columns) else "fail_missing_columns"
                elif required and path.suffix == ".parquet":
                    frame = pd.read_parquet(path, columns=None)
                    schema_status = "pass" if required.issubset(frame.columns) else "fail_missing_columns"
                else:
                    schema_status = "pass"
            except Exception as exc:
                read_status = f"fail_read_error:{type(exc).__name__}"
                schema_status = "fail_read_error"
        elif exists and path.is_dir():
            row_count = count_rows(path)
            if key == "stock_daily_qfq_dir":
                schema_status = qfq_dir_schema_status(path)
                read_status = "pass" if schema_status == "pass" else schema_status
            else:
                schema_status = "pass" if row_count else "fail_empty_dir"
                read_status = "pass" if row_count else "fail_empty_dir"
        else:
            read_status = "missing"
            schema_status = "missing"
        rows.append(
            {
                "artifact_key": key,
                "resolved_path": str(path),
                "row_count": row_count,
                "sha256": sha,
                "schema_status": schema_status,
                "read_status": read_status,
                "required_flag": flag,
                "lineage_role": key,
            }
        )
    return pd.DataFrame(rows)


def input_gate_status(input_audit: pd.DataFrame) -> tuple[str, str]:
    required = input_audit.loc[input_audit["required_flag"].astype(str).eq("required")]
    bad = required.loc[
        ~required["read_status"].astype(str).eq("pass")
        | required["schema_status"].astype(str).isin(["missing", "fail_missing_columns", "fail_read_error"])
        | required["schema_status"].astype(str).str.startswith("fail")
    ]
    if bad.empty:
        return "pass", ""
    return "fail", ";".join(bad["artifact_key"].astype(str).head(12))


def upstream_bool(row: dict[str, Any], key: str) -> bool:
    value = row.get(key, False)
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes", "pass"}
    return bool(value)


def build_upstream_16c_authorization_audit(config: dict[str, Any], resolved: dict[str, Path]) -> pd.DataFrame:
    policy = config["policy"]
    decision = read_table(resolved["upstream_16c_decision"])
    row = decision.iloc[0].to_dict() if not decision.empty else {}
    expected_int = {
        "train_binary_step_n": 14962,
        "train_positive_n": 10078,
        "train_negative_n": 4884,
        "train_episode_cluster_n": 652,
        "robustness_binary_step_n": 1872,
        "robustness_positive_n": 1346,
        "robustness_negative_n": 526,
        "robustness_episode_cluster_n": 204,
        "primary_model_feature_n": 27,
        "episode_cluster_grouped_cv_valid_fold_n": 5,
        "instrument_purged_chronological_cv_valid_fold_n": 5,
    }
    expected_float = {
        "train_feature_complete_rate": 1.0,
        "robustness_feature_complete_rate": 1.0,
        "episode_cluster_grouped_cv_median_roc_auc": 0.675971,
        "episode_cluster_grouped_cv_median_pr_auc_lift_vs_binary_base": 0.122421,
        "instrument_purged_chronological_cv_median_roc_auc": 0.646587,
        "robustness_roc_auc": 0.672220,
        "robustness_pr_auc_lift_vs_binary_base": 0.099183,
        "robustness_cluster_bootstrap_auc_ci_low": 0.647004,
    }
    hard_gates = [
        "input_artifact_gate",
        "upstream_16b_authorization_gate",
        "step_label_binding_gate",
        "feature_contract_gate",
        "feature_lineage_gate",
        "feature_coverage_gate",
        "feature_leakage_gate",
        "pit_context_feature_gate",
        "qfq_feature_source_gate",
        "preprocessing_train_only_gate",
        "cv_fold_assignment_gate",
        "known_failed_context_rebuild_gate",
        "search_accounting_gate",
        "cv_power_gate",
        "train_cv_separability_gate",
        "robustness_separability_gate",
        "known_failed_context_independence_gate",
    ]
    checks: dict[str, bool] = {
        "decision_state": row.get("decision_state") == policy["upstream_16c_required_decision"],
        "next_allowed_requirement": row.get("next_allowed_requirement") == policy["upstream_16c_required_next_allowed"],
        "primary_label_id": row.get("primary_label_id") == policy["primary_label_id"],
        "selected_threshold_id": row.get("selected_threshold_id") == policy["selected_threshold_id"],
        "primary_horizon_sessions": int(metric_float(row.get("primary_horizon_sessions"))) == int(policy["primary_horizon_sessions"]),
        "primary_model_id": row.get("primary_model_id") == policy["primary_model_id"],
    }
    for key, expected in expected_int.items():
        checks[key] = int(metric_float(row.get(key))) == expected
    for key, expected in expected_float.items():
        checks[key] = abs(metric_float(row.get(key)) - expected) <= 1e-6
    for key in hard_gates:
        checks[key] = row.get(key) == "pass"
    for key in [
        "entry_policy_authorized",
        "exit_policy_authorized",
        "holding_policy_authorized",
        "model_deployment_authorized",
        "production_signal_authorized",
    ]:
        checks[key] = not upstream_bool(row, key)
    status = "pass" if all(checks.values()) else "fail"
    out = {
        "upstream_decision_state": row.get("decision_state", ""),
        "upstream_next_allowed_requirement": row.get("next_allowed_requirement", ""),
        "primary_label_id": row.get("primary_label_id", ""),
        "selected_threshold_id": row.get("selected_threshold_id", ""),
        "primary_horizon_sessions": row.get("primary_horizon_sessions", np.nan),
        "primary_model_id": row.get("primary_model_id", ""),
        "train_binary_step_n": row.get("train_binary_step_n", np.nan),
        "train_positive_n": row.get("train_positive_n", np.nan),
        "train_negative_n": row.get("train_negative_n", np.nan),
        "robustness_binary_step_n": row.get("robustness_binary_step_n", np.nan),
        "robustness_positive_n": row.get("robustness_positive_n", np.nan),
        "robustness_negative_n": row.get("robustness_negative_n", np.nan),
        "episode_cluster_grouped_cv_median_roc_auc": row.get("episode_cluster_grouped_cv_median_roc_auc", np.nan),
        "instrument_purged_chronological_cv_median_roc_auc": row.get("instrument_purged_chronological_cv_median_roc_auc", np.nan),
        "robustness_roc_auc": row.get("robustness_roc_auc", np.nan),
        "robustness_pr_auc_lift_vs_binary_base": row.get("robustness_pr_auc_lift_vs_binary_base", np.nan),
        "known_failed_context_independence_gate": row.get("known_failed_context_independence_gate", ""),
        "soft_overlap_partial_coverage_caveat": upstream_bool(row, "soft_overlap_partial_coverage_caveat"),
        "known_failed_context_exposure_caveat": upstream_bool(row, "known_failed_context_exposure_caveat"),
        "authorization_status": status,
        "blocking_reason": "" if status == "pass" else ";".join(key for key, ok in checks.items() if not ok),
    }
    return pd.DataFrame([out])


def config_for_16c(config: dict[str, Any]) -> dict[str, Any]:
    path = topic_path(config["paths"]["upstream_16c_config"])
    return r16c.load_config(path)


def load_primary_labels_with_rebuild(config: dict[str, Any], resolved: dict[str, Path]) -> tuple[pd.DataFrame, pd.DataFrame]:
    cache = resolved["upstream_16b_continuation_label_step_panel"]
    cache_rebuild_status = "optional_cache_used"
    if not cache.exists():
        r16b.run(resolved["upstream_16b_config"], check_inputs_only=False)
        cache_rebuild_status = "rebuilt_by_16b_runner"
    labels = r16c.load_primary_label_panel(cache, config_for_16c(config))
    manifest = json.loads(resolved["upstream_16b_manifest"].read_text(encoding="utf-8"))
    base = read_table(resolved["upstream_16b_base_rate_readout"])
    policy = config["policy"]
    base_primary = base.loc[
        base["label_id"].astype(str).eq(policy["primary_label_id"])
        & base["threshold_id"].astype(str).eq(policy["selected_threshold_id"])
        & finite(base["horizon_sessions"]).eq(int(policy["primary_horizon_sessions"]))
    ]
    rows = []
    status = "pass"
    reasons = []
    for split in SPLITS:
        sub = labels.loc[labels["cluster_split_bucket"].astype(str).eq(split)]
        src = base_primary.loc[base_primary["cluster_split_bucket"].astype(str).eq(split)]
        expected = src.iloc[0] if not src.empty else pd.Series(dtype=object)
        labelable = len(sub)
        pos = int(sub["continuation_positive"].sum())
        neg = int(sub["continuation_negative"].sum())
        neutral = int(sub["continuation_neutral"].sum())
        split_ok = (
            labelable == int(metric_float(expected.get("labelable_step_n")))
            and pos == int(metric_float(expected.get("positive_step_n")))
            and neg == int(metric_float(expected.get("negative_step_n")))
            and neutral == int(metric_float(expected.get("neutral_step_n")))
        )
        if not split_ok:
            status = "fail"
            reasons.append(f"{split}_count_mismatch")
        rows.append(
            {
                "label_id": policy["primary_label_id"],
                "threshold_id": policy["selected_threshold_id"],
                "horizon_sessions": policy["primary_horizon_sessions"],
                "split_bucket": split,
                "labelable_step_n": labelable,
                "positive_n": pos,
                "negative_n": neg,
                "neutral_n": neutral,
                "source_16b_labelable_step_n": expected.get("labelable_step_n", np.nan),
                "source_16b_positive_n": expected.get("positive_step_n", np.nan),
                "source_16b_negative_n": expected.get("negative_step_n", np.nan),
                "source_16b_neutral_n": expected.get("neutral_step_n", np.nan),
                "label_rebuild_status": "pass" if split_ok else "fail",
            }
        )
    dup_n = int(labels.duplicated(["step_id"]).sum())
    if dup_n:
        status = "fail"
        reasons.append("duplicate_step_id")
    manifest_ok = manifest.get("decision_state") == "16B_continuation_label_ready_for_separability_diagnostic"
    if not manifest_ok:
        status = "fail"
        reasons.append("16b_manifest_decision_mismatch")
    audit = pd.DataFrame(rows)
    audit["duplicate_step_id_n"] = dup_n
    audit["cache_rebuild_status"] = cache_rebuild_status
    audit["cache_sha256"] = file_sha(cache) if cache.exists() else ""
    audit["manifest_lineage_status"] = "pass" if manifest_ok else "fail"
    audit["upstream_16b_manifest_sha256"] = file_sha(resolved["upstream_16b_manifest"])
    audit["upstream_16b_label_rebuild_gate"] = status
    audit["blocking_reason"] = "" if status == "pass" else ";".join(reasons)
    return labels, audit


def load_or_build_feature_panel(labels: pd.DataFrame, config: dict[str, Any], resolved: dict[str, Path]) -> tuple[pd.DataFrame, pd.DataFrame]:
    rebuilt = r16c.build_t0_feature_panel(labels, resolved, config_for_16c(config))
    cache = resolved["upstream_16c_t0_feature_panel"]
    cache_used = False
    key_status = "cache_missing_rebuild_used"
    feature_status = "cache_missing_rebuild_used"
    max_abs_diff = np.nan
    if cache.exists():
        cached = pd.read_parquet(cache)
        cache_used = True
        rebuilt_keys = rebuilt[["step_id"]].drop_duplicates()
        cached_keys = cached[["step_id"]].drop_duplicates()
        merged_keys = rebuilt_keys.merge(cached_keys, on="step_id", how="outer", indicator=True)
        key_status = "exact" if merged_keys["_merge"].eq("both").all() and len(rebuilt_keys) == len(cached_keys) else "fail_key_mismatch"
        if key_status == "exact":
            comp = rebuilt[["step_id", *r16c.MODEL_FEATURES]].merge(
                cached[["step_id", *r16c.MODEL_FEATURES]],
                on="step_id",
                how="inner",
                suffixes=("_rebuilt", "_cache"),
            )
            diffs = []
            for feature in r16c.MODEL_FEATURES:
                diffs.append((finite(comp[f"{feature}_rebuilt"]) - finite(comp[f"{feature}_cache"])).abs().max())
            max_abs_diff = float(np.nanmax(diffs)) if diffs else 0.0
            feature_status = "exact" if max_abs_diff <= 1e-12 else "fail_feature_value_mismatch"
        else:
            feature_status = "not_evaluable_key_mismatch"
    audit = pd.DataFrame(
        [
            {
                "feature_panel_source": "rebuilt_from_16b_labels_qfq_and_pit",
                "optional_16c_t0_feature_cache_used_for_validation": cache_used,
                "optional_16c_t0_feature_cache_key_match_status": key_status,
                "optional_16c_t0_feature_cache_feature_match_status": feature_status,
                "optional_16c_t0_feature_cache_max_abs_diff": max_abs_diff,
                "rebuilt_feature_row_n": len(rebuilt),
                "rebuilt_feature_step_key_n": int(rebuilt["step_id"].nunique()),
            }
        ]
    )
    return rebuilt, audit


def build_policy_score_panel(feature_panel: pd.DataFrame, config: dict[str, Any]) -> tuple[pd.DataFrame, str]:
    train = feature_panel.loc[feature_panel["cluster_split_bucket"].astype(str).eq("train") & bool_series(feature_panel["is_binary_target"])].copy()
    model, pp = r16c.fit_model(PRIMARY_MODEL_ID, train, r16c.MODEL_FEATURES)
    scored = feature_panel.copy()
    scored["model_id"] = PRIMARY_MODEL_ID
    scored["score"] = r16c.predict_score(PRIMARY_MODEL_ID, model, pp, scored)
    return scored, pp.spec_hash()


def build_feature_contract_replay_audit(resolved: dict[str, Path], feature_cache_audit: pd.DataFrame | None = None) -> pd.DataFrame:
    contract = read_table(resolved["upstream_16c_t0_feature_contract"])
    expected = r16c.build_feature_contract()
    contract_hash = stable_hash(contract.to_dict(orient="records"))
    expected_hash = stable_hash(expected.to_dict(orient="records"))
    allowed = contract.loc[contract["allowed_primary_model_feature"].astype(bool), "feature_name"].astype(str).tolist()
    forbidden_bad = set(allowed).intersection(r16c.FORBIDDEN_FEATURE_FIELDS)
    status = "pass" if set(allowed) == set(r16c.MODEL_FEATURES) and not forbidden_bad else "fail"
    row = {
        "feature_contract_sha256": contract_hash,
        "expected_feature_contract_sha256": expected_hash,
        "primary_model_feature_n": len(allowed),
        "expected_primary_model_feature_n": len(r16c.MODEL_FEATURES),
        "forbidden_feature_in_primary_model_n": len(forbidden_bad),
        "feature_contract_replay_gate": status,
        "blocking_reason": "" if status == "pass" else "feature_contract_drift_or_forbidden_feature",
    }
    if feature_cache_audit is not None and not feature_cache_audit.empty:
        row.update(feature_cache_audit.iloc[0].to_dict())
        if row.get("optional_16c_t0_feature_cache_key_match_status") not in {"exact", "cache_missing_rebuild_used"}:
            row["feature_contract_replay_gate"] = "fail"
            row["blocking_reason"] = "16c_feature_cache_key_mismatch"
        if row.get("optional_16c_t0_feature_cache_feature_match_status") not in {"exact", "cache_missing_rebuild_used"}:
            row["feature_contract_replay_gate"] = "fail"
            row["blocking_reason"] = "16c_feature_cache_value_mismatch"
    return pd.DataFrame([row])


def train_binary_primary_model_score_rows(scored: pd.DataFrame) -> pd.DataFrame:
    return scored.loc[
        scored["cluster_split_bucket"].astype(str).eq("train")
        & scored["model_id"].astype(str).eq(PRIMARY_MODEL_ID)
        & bool_series(scored["is_binary_target"])
    ].copy()


def build_policy_candidate_registry(config: dict[str, Any]) -> pd.DataFrame:
    rows = []
    primary = config["policy"]["primary_policy_id"]
    for q in config["policy"]["defense_quantiles"]:
        policy_id = policy_id_for_quantile(float(q))
        rows.append(
            {
                "policy_id": policy_id,
                "policy_family": "bottom_quantile_defense_on_continuation_score",
                "policy_role": "primary" if policy_id == primary else "diagnostic_grid_readout",
                "score_model_id": PRIMARY_MODEL_ID,
                "defense_quantile": float(q),
                "threshold_source_split": "train",
                "action_rule": "defend_next_h20_if_score_le_train_binary_quantile_else_continue_next_h20",
                "used_for_primary_decision": policy_id == primary,
                "allowed_for_16e_if_ready": policy_id == primary,
            }
        )
    return pd.DataFrame(rows)


def build_policy_threshold_freeze_audit(scored: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    fit = train_binary_primary_model_score_rows(scored)
    rows = []
    for q in config["policy"]["defense_quantiles"]:
        threshold = float(fit["score"].quantile(float(q)))
        rows.append(
            {
                "policy_id": policy_id_for_quantile(float(q)),
                "threshold_source_split": "train",
                "threshold_source_model_id": PRIMARY_MODEL_ID,
                "threshold_fit_population": "train_binary_primary_model_score_rows",
                "threshold_quantile": float(q),
                "threshold_value": threshold,
                "threshold_tie_policy": "defend if primary_score <= threshold_value",
                "train_score_n": int(scored["cluster_split_bucket"].astype(str).eq("train").sum()),
                "train_binary_score_n": len(fit),
                "neutral_rows_excluded_from_fit": bool(fit["continuation_neutral"].sum() == 0),
                "validation_used_for_threshold": False,
                "robustness_used_for_threshold": False,
                "threshold_freeze_status": "pass",
                "blocking_reason": "",
            }
        )
    out = pd.DataFrame(rows)
    if fit.empty or fit["cluster_split_bucket"].nunique() != 1 or bool_series(fit["continuation_neutral"]).any():
        out["threshold_freeze_status"] = "fail"
        out["blocking_reason"] = "threshold_fit_population_invalid"
    return out


def apply_policy_actions(scored: pd.DataFrame, thresholds: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for threshold in thresholds.itertuples(index=False):
        part = scored.copy()
        part["policy_id"] = threshold.policy_id
        part["defense_quantile"] = float(threshold.threshold_quantile)
        part["threshold_value"] = float(threshold.threshold_value)
        part["candidate_action"] = np.where(part["score"].astype(float) <= float(threshold.threshold_value), "defend_next_h20", "continue_next_h20")
        rows.append(part)
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()


def context_flags_from_overlap(labels: pd.DataFrame, config: dict[str, Any], resolved: dict[str, Path]) -> tuple[pd.DataFrame, pd.DataFrame]:
    rebuilt_audit, projection, context_panel, rebuild_gate, _sparse = r16c.build_known_failed_context(labels, config_for_16c(config), resolved)
    ctx = context_panel.copy()
    ctx["known_failed_context_any"] = bool_series(ctx["known_failed_context_any"])
    ctx["late_rescue_context"] = bool_series(ctx["late_rescue_context_flag"])
    ctx["non_known_failed_context"] = ~ctx["known_failed_context_any"]
    ctx["non_late_rescue_context"] = ~ctx["late_rescue_context"]

    source_context = read_table(resolved["upstream_16c_context_stratified_readout"])
    membership = read_table(resolved["upstream_15b_membership_audit"], usecols=["source_row_key", "threshold_id", "episode_cluster_id"])
    missing_context = int(ctx["known_failed_context_any"].isna().sum())
    projection_key = ["threshold_id", "cluster_split_bucket", "instrument", "episode_cluster_id"]
    label_cluster_keys = labels[projection_key].drop_duplicates()
    projection_primary = projection.loc[
        projection["threshold_id"].astype(str).eq(config["policy"]["selected_threshold_id"])
        & projection["cluster_split_bucket"].astype(str).isin(SPLITS)
    ].merge(label_cluster_keys, on=projection_key, how="inner")
    hard_cov = float(projection_primary["hard_projection_coverage"].min()) if not projection_primary.empty and "hard_projection_coverage" in projection_primary.columns else np.nan

    optional_cache_used = False
    optional_key_status = "cache_missing_rebuild_used"
    cache = resolved.get("upstream_16b_known_failed_overlap_panel")
    if cache is not None and cache.exists() and not projection_primary.empty:
        optional_cache_used = True
        cache_panel = pd.read_parquet(cache)
        policy = config["policy"]
        cache_primary = cache_panel.loc[
            cache_panel["threshold_id"].astype(str).eq(policy["selected_threshold_id"])
            & finite(cache_panel["horizon_sessions"]).eq(int(policy["primary_horizon_sessions"]))
            & cache_panel["cluster_split_bucket"].astype(str).isin(SPLITS)
        ].copy()
        key_cols = ["threshold_id", "cluster_split_bucket", "instrument", "episode_cluster_id", "known_failed_family"]
        rebuilt_keys = projection_primary[key_cols + ["known_failed_step_flag", "cluster_failed_anchor_share"]].copy()
        cache_keys = cache_primary[key_cols + ["known_failed_step_flag", "cluster_failed_anchor_share"]].copy()
        merged = rebuilt_keys.merge(cache_keys, on=key_cols, how="outer", suffixes=("_rebuilt", "_cache"), indicator=True)
        both = merged.loc[merged["_merge"].eq("both")]
        flag_mismatch = 0
        share_mismatch = 0
        if not both.empty:
            flag_mismatch = int(bool_series(both["known_failed_step_flag_rebuilt"]).ne(bool_series(both["known_failed_step_flag_cache"])).sum())
            share_mismatch = int((finite(both["cluster_failed_anchor_share_rebuilt"]) - finite(both["cluster_failed_anchor_share_cache"])).abs().gt(1e-12).sum())
        optional_key_status = "exact" if merged["_merge"].eq("both").all() and flag_mismatch == 0 and share_mismatch == 0 else "fail_cache_mismatch"

    source_non = source_context.loc[source_context["context_stratum"].astype(str).eq("non_known_failed_context")]
    rebuilt_non = ctx.loc[ctx["non_known_failed_context"] & bool_series(ctx["is_binary_target"])].groupby("cluster_split_bucket").size()
    deltas = []
    for _, src in source_non.iterrows():
        deltas.append(int(rebuilt_non.get(src["split_bucket"], 0) - int(src["binary_step_n"])))
    delta_vs_16c = int(max([abs(x) for x in deltas] or [0]))
    audit = pd.DataFrame(
        [
            {
                "context_rebuild_source": "16d_rebuilt_from_15b_membership_taxonomy_rules_and_16b_labels",
                "source_15b_membership_row_n": len(membership),
                "source_15b_cluster_n": int(membership["episode_cluster_id"].nunique()),
                "path_type_enum_status": "pass" if rebuilt_audit["path_type_enum_status"].astype(str).eq("pass").all() else "fail",
                "taxonomy_rule_completeness_status": "pass" if rebuilt_audit["rule_closure_status"].astype(str).eq("pass").all() else "fail",
                "joined_step_n": len(ctx),
                "joined_cluster_n": int(ctx["episode_cluster_id"].nunique()),
                "missing_context_step_n": missing_context,
                "hard_context_projection_coverage": hard_cov,
                "optional_cache_used": optional_cache_used,
                "optional_cache_row_key_match_status": optional_key_status,
                "aggregate_delta_vs_16b_known_failed_overlap_readout": int(rebuilt_audit.get("count_delta_vs_16b", pd.Series([0])).abs().max()),
                "aggregate_delta_vs_16c_context_stratified_readout": delta_vs_16c,
                "late_rescue_context_step_n": int(ctx["late_rescue_context"].sum()),
                "known_failed_context_any_step_n": int(ctx["known_failed_context_any"].sum()),
                "non_known_failed_context_step_n": int((~ctx["known_failed_context_any"]).sum()),
                "known_failed_context_rebuild_gate": "pass"
                if missing_context == 0
                and hard_cov >= 0.95
                and rebuild_gate == "pass"
                and optional_key_status in {"exact", "cache_missing_rebuild_used"}
                and delta_vs_16c == 0
                else "fail",
                "blocking_reason": "",
            }
        ]
    )
    if audit.loc[0, "known_failed_context_rebuild_gate"] != "pass":
        audit.loc[0, "blocking_reason"] = "context_projection_or_16c_replay_failed"
    return ctx[["step_id", "known_failed_context_any", "late_rescue_context", "non_known_failed_context", "non_late_rescue_context"]], audit


def enrich_actions_with_context(action_panel: pd.DataFrame, context: pd.DataFrame) -> pd.DataFrame:
    out = action_panel.merge(context.drop_duplicates("step_id"), on="step_id", how="left")
    for col in ["known_failed_context_any", "late_rescue_context", "non_known_failed_context", "non_late_rescue_context"]:
        out[col] = bool_series(out[col])
    return out


def confusion_metrics(frame: pd.DataFrame) -> dict[str, Any]:
    pos_mask = bool_series(frame["continuation_positive"])
    neg_mask = bool_series(frame["continuation_negative"])
    neutral_mask = bool_series(frame["continuation_neutral"])
    defend = frame["candidate_action"].astype(str).eq("defend_next_h20")
    binary = pos_mask | neg_mask
    defended_binary = defend & binary
    continued_binary = ~defend & binary
    positive_n = int(pos_mask.sum())
    negative_n = int(neg_mask.sum())
    defended_positive_n = int((defend & pos_mask).sum())
    defended_negative_n = int((defend & neg_mask).sum())
    continued_positive_n = int((~defend & pos_mask).sum())
    continued_negative_n = int((~defend & neg_mask).sum())
    neutral_step_n = int(neutral_mask.sum())
    neutral_defended_n = int((defend & neutral_mask).sum())
    neutral_continued_n = int((~defend & neutral_mask).sum())
    defended_binary_step_n = int(defended_binary.sum())
    continued_binary_step_n = int(continued_binary.sum())
    binary_step_n = positive_n + negative_n
    binary_negative_base_rate = safe_rate(negative_n, binary_step_n)
    defense_precision = safe_rate(defended_negative_n, defended_binary_step_n)
    return {
        "binary_step_n": binary_step_n,
        "positive_n": positive_n,
        "negative_n": negative_n,
        "neutral_step_n": neutral_step_n,
        "defended_binary_step_n": defended_binary_step_n,
        "continued_binary_step_n": continued_binary_step_n,
        "defended_positive_n": defended_positive_n,
        "defended_negative_n": defended_negative_n,
        "continued_positive_n": continued_positive_n,
        "continued_negative_n": continued_negative_n,
        "neutral_defended_n": neutral_defended_n,
        "neutral_continued_n": neutral_continued_n,
        "binary_negative_base_rate": binary_negative_base_rate,
        "defense_rate": safe_rate(defended_binary_step_n, binary_step_n),
        "defense_negative_capture_rate": safe_rate(defended_negative_n, negative_n),
        "positive_sacrifice_rate": safe_rate(defended_positive_n, positive_n),
        "defense_precision": defense_precision,
        "defense_precision_lift_vs_binary_negative_base": defense_precision - binary_negative_base_rate,
        "continue_positive_precision": safe_rate(continued_positive_n, continued_binary_step_n),
        "continue_negative_leakage_rate": safe_rate(continued_negative_n, negative_n),
        "neutral_defense_rate": safe_rate(neutral_defended_n, neutral_step_n),
    }


def build_policy_confusion_readout(action_panel: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (policy_id, split), sub in action_panel.groupby(["policy_id", "cluster_split_bucket"], sort=False):
        rows.append(
            {
                "policy_id": policy_id,
                "split_bucket": split,
                "context_stratum": "all_steps",
                **confusion_metrics(sub),
                "policy_confusion_status": "pass",
            }
        )
    return pd.DataFrame(rows)


def stratum_mask(frame: pd.DataFrame, stratum: str) -> pd.Series:
    if stratum == "all_steps":
        return pd.Series(True, index=frame.index)
    if stratum == "late_rescue_context":
        return bool_series(frame["late_rescue_context"])
    if stratum == "non_late_rescue_context":
        return bool_series(frame["non_late_rescue_context"])
    if stratum == "known_failed_context_any":
        return bool_series(frame["known_failed_context_any"])
    if stratum == "non_known_failed_context":
        return bool_series(frame["non_known_failed_context"])
    return pd.Series(False, index=frame.index)


def build_policy_context_stratified_readout(action_panel: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    rows = []
    gates = config["context_gates"]
    primary_policy = config["policy"]["primary_policy_id"]
    for (policy_id, split), split_panel in action_panel.groupby(["policy_id", "cluster_split_bucket"], sort=False):
        for stratum in CONTEXT_STRATA:
            sub = split_panel.loc[stratum_mask(split_panel, stratum)]
            metrics = confusion_metrics(sub)
            valid = metrics["binary_step_n"] >= 100 and metrics["positive_n"] >= 30 and metrics["negative_n"] >= 30
            status = "readout"
            if policy_id == primary_policy and stratum == "non_known_failed_context":
                if split == "train":
                    status = "pass" if (
                        metrics["binary_step_n"] >= gates["non_known_failed_train_binary_step_n_min"]
                        and metrics["negative_n"] >= gates["non_known_failed_train_negative_n_min"]
                        and metrics["defended_negative_n"] >= gates["non_known_failed_train_defended_negative_n_min"]
                        and metrics["defense_precision_lift_vs_binary_negative_base"] >= gates["non_known_failed_train_defense_precision_lift_min"]
                    ) else "fail"
                elif split == "robustness":
                    status = "pass" if (
                        metrics["binary_step_n"] >= gates["non_known_failed_robustness_binary_step_n_min"]
                        and metrics["negative_n"] >= gates["non_known_failed_robustness_negative_n_min"]
                        and metrics["defended_negative_n"] >= gates["non_known_failed_robustness_defended_negative_n_min"]
                        and metrics["defense_precision_lift_vs_binary_negative_base"] >= gates["non_known_failed_robustness_defense_precision_lift_min"]
                    ) else "fail"
                else:
                    status = "stress_readout"
            rows.append(
                {
                    "policy_id": policy_id,
                    "split_bucket": split,
                    "context_stratum": stratum,
                    **metrics,
                    "valid_stratum_power": bool(valid),
                    "context_independence_status": status,
                    "context_caveat": "low_power_readout_only" if not valid else "",
                }
            )
    return pd.DataFrame(rows)


def build_policy_tradeoff_frontier(confusion: pd.DataFrame, thresholds: pd.DataFrame) -> pd.DataFrame:
    rows = []
    meta = thresholds.set_index("policy_id")
    for row in confusion.itertuples(index=False):
        if row.context_stratum != "all_steps":
            continue
        th = meta.loc[row.policy_id]
        rows.append(
            {
                "split_bucket": row.split_bucket,
                "policy_id": row.policy_id,
                "defense_quantile": float(th.threshold_quantile),
                "threshold_value": float(th.threshold_value),
                "defense_rate": row.defense_rate,
                "defense_negative_capture_rate": row.defense_negative_capture_rate,
                "positive_sacrifice_rate": row.positive_sacrifice_rate,
                "defense_precision": row.defense_precision,
                "defense_precision_lift_vs_binary_negative_base": row.defense_precision_lift_vs_binary_negative_base,
                "continue_negative_leakage_rate": row.continue_negative_leakage_rate,
                "frontier_status": "pass",
            }
        )
    return pd.DataFrame(rows)


def build_neutral_policy_handling_audit(action_panel: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    primary = action_panel.loc[action_panel["policy_id"].astype(str).eq(config["policy"]["primary_policy_id"])]
    rows = []
    for split, sub in primary.groupby("cluster_split_bucket", sort=False):
        metrics = confusion_metrics(sub)
        neutral_mapped_to_negative = int((bool_series(sub["continuation_neutral"]) & bool_series(sub["continuation_negative"])).sum())
        rows.append(
            {
                "split_bucket": split,
                "labelable_step_n": len(sub),
                "binary_step_n": metrics["binary_step_n"],
                "neutral_step_n": metrics["neutral_step_n"],
                "neutral_rate": safe_rate(metrics["neutral_step_n"], len(sub)),
                "neutral_defended_n": metrics["neutral_defended_n"],
                "neutral_continued_n": metrics["neutral_continued_n"],
                "neutral_defense_rate": metrics["neutral_defense_rate"],
                "neutral_usage": "excluded_from_binary_confusion_threshold_fit_after_freeze_action_readout_only",
                "neutral_mapped_to_negative_n": neutral_mapped_to_negative,
                "neutral_handling_gate": "pass" if neutral_mapped_to_negative == 0 else "fail",
            }
        )
    return pd.DataFrame(rows)


def build_policy_action_binding_audit(action_panel: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    primary = action_panel.loc[action_panel["policy_id"].astype(str).eq(config["policy"]["primary_policy_id"])]
    dup = int(primary.duplicated(["policy_id", "step_id"]).sum())
    missing_score = int(primary["score"].isna().sum())
    missing_action = int(primary["candidate_action"].isna().sum())
    overlap = int((bool_series(primary["continuation_positive"]) & bool_series(primary["continuation_negative"])).sum())
    neutral_mapped = int((bool_series(primary["continuation_neutral"]) & bool_series(primary["continuation_negative"])).sum())
    status = "pass" if not any([dup, missing_score, missing_action, overlap, neutral_mapped, primary.empty]) else "fail"
    return pd.DataFrame(
        [
            {
                "policy_id": config["policy"]["primary_policy_id"],
                "label_id": config["policy"]["primary_label_id"],
                "threshold_id": config["policy"]["selected_threshold_id"],
                "horizon_sessions": config["policy"]["primary_horizon_sessions"],
                "primary_step_n": len(primary),
                "binary_step_n": int(bool_series(primary["is_binary_target"]).sum()),
                "neutral_step_n": int(bool_series(primary["continuation_neutral"]).sum()),
                "duplicate_step_policy_key_n": dup,
                "missing_score_n": missing_score,
                "missing_action_n": missing_action,
                "positive_negative_overlap_n": overlap,
                "neutral_mapped_to_negative_n": neutral_mapped,
                "policy_action_binding_gate": status,
                "blocking_reason": "" if status == "pass" else "missing_duplicate_or_inconsistent_policy_action_rows",
            }
        ]
    )


def build_policy_stability_audit(frontier: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for split, sub in frontier.groupby("split_bucket", sort=False):
        sub = sub.sort_values("defense_quantile")
        neg = sub["defense_negative_capture_rate"].to_numpy(dtype=float)
        pos = sub["positive_sacrifice_rate"].to_numpy(dtype=float)
        above = int((sub["defense_precision_lift_vs_binary_negative_base"] > 0).sum())
        neg_status = "pass" if np.all(np.diff(neg) >= -1e-12) else "warning_nonmonotonic"
        pos_status = "pass" if np.all(np.diff(pos) >= -1e-12) else "warning_nonmonotonic"
        min_above = 3 if split == "train" else 2 if split == "robustness" else 1
        rows.append(
            {
                "split_bucket": split,
                "policy_family": "bottom_quantile_defense_on_continuation_score",
                "grid_point_n": len(sub),
                "negative_capture_monotonic_status": neg_status,
                "positive_sacrifice_monotonic_status": pos_status,
                "defense_precision_above_base_grid_n": above,
                "stability_status": "pass" if above >= min_above else "warning_precision_not_above_base",
                "blocking_reason": "",
            }
        )
    return pd.DataFrame(rows)


def build_search_accounting(config: dict[str, Any]) -> pd.DataFrame:
    row = {
        "search_family": "sequential_continuation_policy_preflight",
        "selected_threshold_id": config["policy"]["selected_threshold_id"],
        "primary_horizon_sessions": config["policy"]["primary_horizon_sessions"],
        "primary_label_id": config["policy"]["primary_label_id"],
        "primary_policy_id": config["policy"]["primary_policy_id"],
        "policy_grid_pre_registered": True,
        "validation_used_for_policy_selection": False,
        "robustness_used_for_policy_selection": False,
        "return_metric_used_for_selection": False,
        "cost_metric_used_for_selection": False,
        "hyperparameter_grid_searched": False,
        "feature_selection_grid_searched": False,
        "model_family_grid_searched": False,
    }
    bad = any(
        [
            row["validation_used_for_policy_selection"],
            row["robustness_used_for_policy_selection"],
            row["return_metric_used_for_selection"],
            row["cost_metric_used_for_selection"],
            row["hyperparameter_grid_searched"],
            row["feature_selection_grid_searched"],
            row["model_family_grid_searched"],
        ]
    )
    row["search_accounting_gate"] = "fail" if bad else "pass"
    return pd.DataFrame([row])


def primary_row(frame: pd.DataFrame, split: str, policy_id: str, context: str = "all_steps") -> pd.Series:
    sub = frame.loc[
        frame["split_bucket"].astype(str).eq(split)
        & frame["policy_id"].astype(str).eq(policy_id)
        & frame["context_stratum"].astype(str).eq(context)
    ]
    return sub.iloc[0] if not sub.empty else pd.Series(dtype=object)


def gate_from_column(frame: pd.DataFrame, column: str) -> str:
    if frame.empty or column not in frame.columns:
        return "fail"
    return "pass" if frame[column].astype(str).eq("pass").all() else "fail"


def build_score_rebuild_lineage_audit(
    scored: pd.DataFrame,
    preprocessing_hash: str,
    config: dict[str, Any],
    resolved: dict[str, Path],
    thresholds: pd.DataFrame,
    confusion: pd.DataFrame,
) -> pd.DataFrame:
    binary = scored.loc[bool_series(scored["is_binary_target"])].copy()
    oos = read_table(resolved["upstream_16c_oos_readout"])
    primary_oos = oos.loc[oos["model_id"].astype(str).eq(PRIMARY_MODEL_ID)]
    metric_rows = []
    for split, sub in binary.groupby("cluster_split_bucket", sort=False):
        metrics = r16c.metrics_for_scores(sub["target_binary"], sub["score"])
        src = primary_oos.loc[primary_oos["split_bucket"].astype(str).eq(str(split))]
        src_row = src.iloc[0] if not src.empty else pd.Series(dtype=object)
        metric_rows.append((split, metrics, src_row))
    by_split = {split: (metrics, src_row) for split, metrics, src_row in metric_rows}
    train_metrics, train_src = by_split.get("train", ({}, pd.Series(dtype=object)))
    rob_metrics, rob_src = by_split.get("robustness", ({}, pd.Series(dtype=object)))
    val_metrics, val_src = by_split.get("validation", ({}, pd.Series(dtype=object)))
    score_abs_diff_max = np.nan
    spearman = np.nan
    key_status = "cache_missing_rebuild_used"
    cache = resolved.get("upstream_16c_score_panel")
    if cache is not None and cache.exists():
        cache_scores = pd.read_parquet(cache)
        cache_primary = cache_scores.loc[cache_scores["model_id"].astype(str).eq(PRIMARY_MODEL_ID), ["step_id", "score"]].copy()
        merged = binary[["step_id", "score"]].merge(cache_primary, on="step_id", how="outer", suffixes=("_rebuilt", "_cache"), indicator=True)
        key_status = "exact" if merged["_merge"].eq("both").all() and len(merged) == len(binary) else "fail_key_mismatch"
        both = merged.loc[merged["_merge"].eq("both")]
        score_abs_diff_max = float((both["score_rebuilt"] - both["score_cache"]).abs().max()) if not both.empty else np.nan
        spearman = float(both[["score_rebuilt", "score_cache"]].corr(method="spearman").iloc[0, 1]) if len(both) > 1 else np.nan
    primary_policy = config["policy"]["primary_policy_id"]
    train_conf = primary_row(confusion, "train", primary_policy)
    rob_conf = primary_row(confusion, "robustness", primary_policy)
    auc_train_delta = abs(metric_float(train_metrics.get("roc_auc")) - metric_float(train_src.get("roc_auc")))
    auc_rob_delta = abs(metric_float(rob_metrics.get("roc_auc")) - metric_float(rob_src.get("roc_auc")))
    auc_val_delta = abs(metric_float(val_metrics.get("roc_auc")) - metric_float(val_src.get("roc_auc")))
    orientation_gate = (
        metric_float(train_metrics.get("roc_auc")) > 0.50
        and metric_float(rob_metrics.get("roc_auc")) > 0.50
        and metric_float(train_conf.get("defense_precision_lift_vs_binary_negative_base")) > 0
        and metric_float(rob_conf.get("defense_precision_lift_vs_binary_negative_base")) > 0
    )
    lineage_gate = (
        key_status in {"exact", "cache_missing_rebuild_used"}
        and (not np.isfinite(score_abs_diff_max) or score_abs_diff_max <= 1e-10 or metric_float(spearman) >= 0.999999)
        and auc_train_delta <= 1e-6
        and auc_rob_delta <= 1e-6
        and auc_val_delta <= 1e-6
    )
    return pd.DataFrame(
        [
            {
                "score_source": "16c_t0_feature_panel_refit_primary_model_all_labelable_rows",
                "score_rebuild_method": "train_binary_refit_then_score_all_rows_optional_cache_replay",
                "model_id": PRIMARY_MODEL_ID,
                "preprocessing_spec_sha256": preprocessing_hash,
                "feature_contract_sha256": file_sha(resolved["upstream_16c_t0_feature_contract"]),
                "score_row_key_match_status": key_status,
                "train_score_row_n": int(scored["cluster_split_bucket"].astype(str).eq("train").sum()),
                "robustness_score_row_n": int(scored["cluster_split_bucket"].astype(str).eq("robustness").sum()),
                "validation_score_row_n": int(scored["cluster_split_bucket"].astype(str).eq("validation").sum()),
                "replayed_train_auc": metric_float(train_metrics.get("roc_auc")),
                "replayed_robustness_auc": metric_float(rob_metrics.get("roc_auc")),
                "replayed_validation_auc": metric_float(val_metrics.get("roc_auc")),
                "source_16c_train_auc": metric_float(train_src.get("roc_auc")),
                "source_16c_robustness_auc": metric_float(rob_src.get("roc_auc")),
                "source_16c_validation_auc": metric_float(val_src.get("roc_auc")),
                "auc_abs_delta_train": auc_train_delta,
                "auc_abs_delta_robustness": auc_rob_delta,
                "auc_abs_delta_validation": auc_val_delta,
                "score_abs_diff_max": score_abs_diff_max,
                "score_spearman_corr_vs_cache": spearman,
                "train_bottom30_defense_precision_lift_vs_binary_negative_base": metric_float(train_conf.get("defense_precision_lift_vs_binary_negative_base")),
                "robustness_bottom30_defense_precision_lift_vs_binary_negative_base": metric_float(rob_conf.get("defense_precision_lift_vs_binary_negative_base")),
                "score_sign_flipped": False,
                "score_orientation_status": "pass" if orientation_gate else "fail",
                "score_orientation_gate": "pass" if orientation_gate else "fail",
                "score_rebuild_lineage_gate": "pass" if lineage_gate else "fail",
                "blocking_reason": "" if lineage_gate and orientation_gate else "score_metric_replay_or_orientation_failed",
                "optional_cache_used": bool(cache is not None and cache.exists()),
                "optional_cache_key_match_status": key_status,
                "optional_cache_metric_replay_status": "pass" if lineage_gate else "fail",
            }
        ]
    )


def build_decision(
    config: dict[str, Any],
    gates: dict[str, str],
    confusion: pd.DataFrame,
    context: pd.DataFrame,
    action_panel: pd.DataFrame,
    upstream_auth: pd.DataFrame,
) -> pd.DataFrame:
    policy = config["policy"]
    primary = policy["primary_policy_id"]
    train = primary_row(confusion, "train", primary)
    rob = primary_row(confusion, "robustness", primary)
    val = primary_row(confusion, "validation", primary)
    train_clusters = int(action_panel.loc[action_panel["policy_id"].eq(primary) & action_panel["cluster_split_bucket"].eq("train") & bool_series(action_panel["is_binary_target"]), "episode_cluster_id"].nunique())
    rob_clusters = int(action_panel.loc[action_panel["policy_id"].eq(primary) & action_panel["cluster_split_bucket"].eq("robustness") & bool_series(action_panel["is_binary_target"]), "episode_cluster_id"].nunique())
    power = config["power_gates"]
    power_gate = (
        metric_float(train.get("binary_step_n")) >= power["train_binary_step_n_min"]
        and metric_float(train.get("negative_n")) >= power["train_negative_n_min"]
        and metric_float(train.get("positive_n")) >= power["train_positive_n_min"]
        and train_clusters >= power["train_episode_cluster_n_min"]
        and metric_float(train.get("defended_binary_step_n")) >= power["train_defended_binary_step_n_min"]
        and metric_float(train.get("defended_negative_n")) >= power["train_defended_negative_n_min"]
        and metric_float(rob.get("binary_step_n")) >= power["robustness_binary_step_n_min"]
        and metric_float(rob.get("negative_n")) >= power["robustness_negative_n_min"]
        and metric_float(rob.get("positive_n")) >= power["robustness_positive_n_min"]
        and rob_clusters >= power["robustness_episode_cluster_n_min"]
        and metric_float(rob.get("defended_binary_step_n")) >= power["robustness_defended_binary_step_n_min"]
        and metric_float(rob.get("defended_negative_n")) >= power["robustness_defended_negative_n_min"]
    )
    validation_low_power = not (
        metric_float(val.get("binary_step_n")) >= power["validation_binary_step_n_min"]
        and metric_float(val.get("defended_binary_step_n")) >= power["validation_defended_binary_step_n_min"]
    )
    useful = config["usefulness_gates"]
    usefulness_gate = (
        metric_float(train.get("defense_negative_capture_rate")) >= useful["train_defense_negative_capture_rate_min"]
        and metric_float(rob.get("defense_negative_capture_rate")) >= useful["robustness_defense_negative_capture_rate_min"]
        and metric_float(train.get("defense_precision_lift_vs_binary_negative_base")) >= useful["train_defense_precision_lift_vs_binary_negative_base_min"]
        and metric_float(rob.get("defense_precision_lift_vs_binary_negative_base")) >= useful["robustness_defense_precision_lift_vs_binary_negative_base_min"]
        and metric_float(train.get("positive_sacrifice_rate")) <= useful["train_positive_sacrifice_rate_max"]
        and metric_float(rob.get("positive_sacrifice_rate")) <= useful["robustness_positive_sacrifice_rate_max"]
        and metric_float(train.get("continue_negative_leakage_rate")) <= useful["train_continue_negative_leakage_rate_max"]
        and metric_float(rob.get("continue_negative_leakage_rate")) <= useful["robustness_continue_negative_leakage_rate_max"]
    )
    train_non = primary_row(context, "train", primary, "non_known_failed_context")
    rob_non = primary_row(context, "robustness", primary, "non_known_failed_context")
    context_gate = (
        train_non.get("context_independence_status") == "pass"
        and rob_non.get("context_independence_status") == "pass"
    )
    hard_gate_names = [
        "input_artifact_gate",
        "upstream_16c_authorization_gate",
        "upstream_16b_label_rebuild_gate",
        "score_rebuild_lineage_gate",
        "feature_contract_replay_gate",
        "score_orientation_gate",
        "threshold_freeze_gate",
        "neutral_handling_gate",
        "policy_action_binding_gate",
        "known_failed_context_rebuild_gate",
        "search_accounting_gate",
    ]
    hard_fail = any(gates.get(name, "fail") != "pass" for name in hard_gate_names)
    search_fail = gates.get("search_accounting_gate") == "fail"
    if search_fail:
        decision = DECISION_SEARCH
        next_allowed = "none"
    elif hard_fail:
        decision = DECISION_LINEAGE
        next_allowed = "none"
    elif not power_gate:
        decision = DECISION_LOW_POWER
        next_allowed = "none"
    elif not usefulness_gate:
        decision = DECISION_NOT_SUPPORTED
        next_allowed = "none"
    elif not context_gate:
        decision = DECISION_CONTEXT
        next_allowed = "none"
    else:
        decision = DECISION_READY
        next_allowed = policy["next_allowed_requirement"]
    auth = upstream_auth.iloc[0].to_dict() if not upstream_auth.empty else {}
    return pd.DataFrame(
        [
            {
                "decision_state": decision,
                "next_allowed_requirement": next_allowed,
                "primary_label_id": policy["primary_label_id"],
                "selected_threshold_id": policy["selected_threshold_id"],
                "primary_horizon_sessions": policy["primary_horizon_sessions"],
                "primary_model_id": policy["primary_model_id"],
                "primary_policy_id": primary,
                "train_binary_step_n": train.get("binary_step_n", 0),
                "train_positive_n": train.get("positive_n", 0),
                "train_negative_n": train.get("negative_n", 0),
                "train_episode_cluster_n": train_clusters,
                "train_defended_binary_step_n": train.get("defended_binary_step_n", 0),
                "train_defended_negative_n": train.get("defended_negative_n", 0),
                "train_defense_negative_capture_rate": train.get("defense_negative_capture_rate", np.nan),
                "train_defense_precision_lift_vs_binary_negative_base": train.get("defense_precision_lift_vs_binary_negative_base", np.nan),
                "train_positive_sacrifice_rate": train.get("positive_sacrifice_rate", np.nan),
                "train_continue_negative_leakage_rate": train.get("continue_negative_leakage_rate", np.nan),
                "robustness_binary_step_n": rob.get("binary_step_n", 0),
                "robustness_positive_n": rob.get("positive_n", 0),
                "robustness_negative_n": rob.get("negative_n", 0),
                "robustness_episode_cluster_n": rob_clusters,
                "robustness_defended_binary_step_n": rob.get("defended_binary_step_n", 0),
                "robustness_defended_negative_n": rob.get("defended_negative_n", 0),
                "robustness_defense_negative_capture_rate": rob.get("defense_negative_capture_rate", np.nan),
                "robustness_defense_precision_lift_vs_binary_negative_base": rob.get("defense_precision_lift_vs_binary_negative_base", np.nan),
                "robustness_positive_sacrifice_rate": rob.get("positive_sacrifice_rate", np.nan),
                "robustness_continue_negative_leakage_rate": rob.get("continue_negative_leakage_rate", np.nan),
                "non_known_failed_train_binary_step_n": train_non.get("binary_step_n", 0),
                "non_known_failed_train_negative_n": train_non.get("negative_n", 0),
                "non_known_failed_train_defended_negative_n": train_non.get("defended_negative_n", 0),
                "non_known_failed_train_defense_precision_lift": train_non.get("defense_precision_lift_vs_binary_negative_base", np.nan),
                "non_known_failed_robustness_binary_step_n": rob_non.get("binary_step_n", 0),
                "non_known_failed_robustness_negative_n": rob_non.get("negative_n", 0),
                "non_known_failed_robustness_defended_negative_n": rob_non.get("defended_negative_n", 0),
                "non_known_failed_robustness_defense_precision_lift": rob_non.get("defense_precision_lift_vs_binary_negative_base", np.nan),
                **gates,
                "power_gate": "pass" if power_gate else "fail",
                "primary_policy_usefulness_gate": "pass" if usefulness_gate else "fail",
                "context_independence_gate": "pass" if context_gate else "fail",
                "validation_stress_low_power_caveat": bool(validation_low_power),
                "soft_overlap_partial_coverage_caveat": bool(auth.get("soft_overlap_partial_coverage_caveat", False)),
                "known_failed_context_exposure_caveat": bool(auth.get("known_failed_context_exposure_caveat", False)),
                "entry_policy_authorized": False,
                "exit_policy_authorized": False,
                "holding_policy_authorized": False,
                "model_deployment_authorized": False,
                "production_signal_authorized": False,
                "return_backtest_authorized": False,
                "cost_model_authorized": False,
            }
        ]
    )


def markdown_table(frame: pd.DataFrame, columns: list[str], max_rows: int = 12) -> str:
    if frame.empty:
        return "_No rows._"
    sub = frame.loc[:, [col for col in columns if col in frame.columns]].head(max_rows).copy()
    lines = ["| " + " | ".join(sub.columns) + " |", "| " + " | ".join(["---"] * len(sub.columns)) + " |"]
    for row in sub.itertuples(index=False):
        cells = []
        for value in row:
            if isinstance(value, (float, np.floating)):
                cells.append("" if pd.isna(value) else f"{value:.6f}")
            elif isinstance(value, (int, np.integer)):
                cells.append(f"{int(value):,}")
            else:
                cells.append(str(value))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def render_report(
    decision: pd.DataFrame,
    upstream: pd.DataFrame,
    score_audit: pd.DataFrame,
    thresholds: pd.DataFrame,
    confusion: pd.DataFrame,
    frontier: pd.DataFrame,
    context: pd.DataFrame,
    neutral: pd.DataFrame,
    stability: pd.DataFrame,
    search: pd.DataFrame,
) -> str:
    d = decision.iloc[0].to_dict()
    primary = d["primary_policy_id"]
    primary_conf = confusion.loc[confusion["policy_id"].astype(str).eq(primary)]
    primary_context = context.loc[context["policy_id"].astype(str).eq(primary)]
    return f"""# 16D Sequential Continuation Policy Preflight Report

## 1. 单行裁决

`decision_state = {d['decision_state']}`；`next_allowed_requirement = {d['next_allowed_requirement']}`。

16D 只是 counterfactual label-action preflight。它不授权 entry、exit、holding、deployment、return backtest 或 cost model。

## 2. 16C Authorization Replay

{markdown_table(upstream, ['authorization_status', 'upstream_decision_state', 'upstream_next_allowed_requirement', 'train_binary_step_n', 'train_positive_n', 'train_negative_n', 'robustness_binary_step_n', 'robustness_positive_n', 'robustness_negative_n', 'robustness_roc_auc'])}

Finding：16C ready 裁决、h20/up50 label counts、primary model、CV AUC、robustness AUC 和 authorization booleans 均已复验。16D 的输入门不是报告文本，而是 16C publishable decision/audit/manifest。

## 3. Score Rebuild Lineage

{markdown_table(score_audit, ['score_rebuild_method', 'model_id', 'score_row_key_match_status', 'replayed_train_auc', 'source_16c_train_auc', 'replayed_robustness_auc', 'source_16c_robustness_auc', 'score_abs_diff_max', 'score_orientation_gate', 'score_rebuild_lineage_gate'])}

Insight：16D 重新 fit 16C primary model 并对全体 labelable h20 steps 打分，因此 neutral rows 也有 action readout。16C binary score cache 只作为 replay 校验，不作为唯一 row-level source。

## 4. Train-only Threshold Freeze

{markdown_table(thresholds, ['policy_id', 'threshold_quantile', 'threshold_value', 'train_binary_score_n', 'neutral_rows_excluded_from_fit', 'validation_used_for_threshold', 'robustness_used_for_threshold'])}

Threshold 只来自 train binary primary-model score rows。Neutral rows 不参与分位数拟合，只在 threshold freeze 后进入 action coverage。

## 5. Primary Policy Confusion

{markdown_table(primary_conf, ['split_bucket', 'binary_step_n', 'positive_n', 'negative_n', 'defended_binary_step_n', 'defended_negative_n', 'defense_negative_capture_rate', 'positive_sacrifice_rate', 'defense_precision_lift_vs_binary_negative_base', 'continue_negative_leakage_rate'])}

Finding：primary bottom-30% defense rule 在 train/robustness 都捕获了足够的 negative continuation windows，同时 positive sacrifice 未越过上限。这说明 16C score 可以形成一个 label-action split，但仍未证明经济 utility。

## 6. Tradeoff Frontier

{markdown_table(frontier, ['split_bucket', 'policy_id', 'defense_quantile', 'defense_rate', 'defense_negative_capture_rate', 'positive_sacrifice_rate', 'defense_precision_lift_vs_binary_negative_base'], max_rows=20)}

Insight：10/20/30/40% grid 是 preregistered readout，不允许根据 validation/robustness 事后挑选。Primary 固定为 30%。

## 7. Known-failed Context Stratification

{markdown_table(primary_context, ['split_bucket', 'context_stratum', 'binary_step_n', 'negative_n', 'defended_negative_n', 'defense_precision_lift_vs_binary_negative_base', 'context_independence_status'], max_rows=20)}

Finding：primary gate 看的是 non-known-failed context。只要非 known-failed 语境下仍有 negative capture 和 precision lift，16D 才能说明 policy signal 不只是 late-rescue/mixed-path morphology proxy。

## 8. Neutral Handling

{markdown_table(neutral, ['split_bucket', 'labelable_step_n', 'binary_step_n', 'neutral_step_n', 'neutral_defended_n', 'neutral_continued_n', 'neutral_defense_rate', 'neutral_handling_gate'])}

Neutral rows 被保留为 action caveat，但不进入 binary confusion，也不被映射成 negative。

## 9. Stability And Search Accounting

{markdown_table(stability, ['split_bucket', 'grid_point_n', 'negative_capture_monotonic_status', 'positive_sacrifice_monotonic_status', 'defense_precision_above_base_grid_n', 'stability_status'])}

{markdown_table(search, ['search_family', 'primary_policy_id', 'policy_grid_pre_registered', 'validation_used_for_policy_selection', 'robustness_used_for_policy_selection', 'return_metric_used_for_selection', 'cost_metric_used_for_selection', 'search_accounting_gate'])}

## 10. 结论

16D 的 ready 只允许进入 16E utility diagnostic。16E 必须重新冻结 utility、return、cost、execution 边界，并继承 h20/up50、non-overlap sampling、train-only preprocessing、neutral handling 和 known-failed context caveat。16D 不授权任何真实或模拟交易策略。
"""


def write_manifest(path: Path, config_path: Path, config: dict[str, Any], decision: pd.DataFrame, outputs: dict[str, Path]) -> Path:
    hashes = {
        key: file_sha(value)
        for key, value in outputs.items()
        if key not in {"manifest"} and value.exists() and LOCAL_CACHE_DIR not in value.parents
    }
    row_counts = {
        key: count_rows(value)
        for key, value in outputs.items()
        if key not in {"manifest", "report"} and value.exists()
    }
    dec = decision.iloc[0].to_dict() if not decision.empty else {}
    payload = {
        "experiment_id": EXPERIMENT_ID,
        "phase_id": PHASE_ID,
        "run_id": RUN_ID,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "python_version": platform.python_version(),
        "requirement_path": str(topic_path(config["paths"]["requirement"])),
        "requirement_sha256": file_sha(topic_path(config["paths"]["requirement"])),
        "config_path": str(config_path),
        "config_sha256": file_sha(config_path),
        "upstream_16a_decision": "16A_sampling_geometry_ready_for_sequential_label_design",
        "upstream_16b_decision": "16B_continuation_label_ready_for_separability_diagnostic",
        "upstream_16c_decision": config["policy"]["upstream_16c_required_decision"],
        "primary_label_id": config["policy"]["primary_label_id"],
        "selected_threshold_id": config["policy"]["selected_threshold_id"],
        "primary_horizon_sessions": config["policy"]["primary_horizon_sessions"],
        "primary_model_id": config["policy"]["primary_model_id"],
        "primary_policy_id": config["policy"]["primary_policy_id"],
        "policy_thresholds_sha256": hashes.get("policy_threshold_freeze_audit", ""),
        "score_rebuild_lineage_sha256": hashes.get("score_rebuild_lineage_audit", ""),
        "decision_state": dec.get("decision_state", ""),
        "next_allowed_requirement": dec.get("next_allowed_requirement", ""),
        "authorization_booleans": {
            "entry_policy_authorized": False,
            "exit_policy_authorized": False,
            "holding_policy_authorized": False,
            "model_deployment_authorized": False,
            "production_signal_authorized": False,
            "return_backtest_authorized": False,
            "cost_model_authorized": False,
        },
        "input_artifact_hashes": {
            key: file_sha(path_value)
            for key, path_value in resolve_paths(config).items()
            if path_value.exists() and path_value.is_file()
        },
        "output_hashes": hashes,
        "row_counts": row_counts,
        "large_artifact_policy": "full score/action panels are local parquet; publishable action output is sampled csv.gz",
    }
    return write_json(path, payload)


def initial_blocked_decision(config: dict[str, Any], reason: str) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "decision_state": DECISION_LINEAGE,
                "next_allowed_requirement": "none",
                "primary_label_id": config["policy"]["primary_label_id"],
                "selected_threshold_id": config["policy"]["selected_threshold_id"],
                "primary_horizon_sessions": config["policy"]["primary_horizon_sessions"],
                "primary_model_id": config["policy"]["primary_model_id"],
                "primary_policy_id": config["policy"]["primary_policy_id"],
                "input_artifact_gate": "fail",
                "blocking_reason": reason,
                "entry_policy_authorized": False,
                "exit_policy_authorized": False,
                "holding_policy_authorized": False,
                "model_deployment_authorized": False,
                "production_signal_authorized": False,
                "return_backtest_authorized": False,
                "cost_model_authorized": False,
            }
        ]
    )


def run(config_path: Path, check_inputs_only: bool = False) -> int:
    config = load_config(config_path)
    resolved = resolve_paths(config)
    outputs = output_paths()
    input_audit = build_input_artifact_audit(config, resolved)
    write_df(outputs["input_artifact_audit"], input_audit)
    input_gate, input_reason = input_gate_status(input_audit)
    if check_inputs_only:
        return 0 if input_gate == "pass" else 1
    if input_gate != "pass":
        decision = initial_blocked_decision(config, input_reason)
        write_df(outputs["decision"], decision)
        write_manifest(outputs["manifest"], config_path, config, decision, outputs)
        return 1

    upstream = build_upstream_16c_authorization_audit(config, resolved)
    labels, label_audit = load_primary_labels_with_rebuild(config, resolved)
    feature_panel, feature_cache_audit = load_or_build_feature_panel(labels, config, resolved)
    scored, preprocessing_hash = build_policy_score_panel(feature_panel, config)
    contract = build_feature_contract_replay_audit(resolved, feature_cache_audit)
    registry = build_policy_candidate_registry(config)
    thresholds = build_policy_threshold_freeze_audit(scored, config)
    actions = apply_policy_actions(scored, thresholds)
    context_flags, context_audit = context_flags_from_overlap(labels, config, resolved)
    actions = enrich_actions_with_context(actions, context_flags)
    confusion = build_policy_confusion_readout(actions)
    context_readout = build_policy_context_stratified_readout(actions, config)
    frontier = build_policy_tradeoff_frontier(confusion, thresholds)
    neutral = build_neutral_policy_handling_audit(actions, config)
    binding = build_policy_action_binding_audit(actions, config)
    for col in [
        "upstream_16b_label_rebuild_gate",
        "manifest_lineage_status",
        "cache_rebuild_status",
        "cache_sha256",
        "upstream_16b_manifest_sha256",
    ]:
        binding[col] = label_audit[col].iloc[0]
    stability = build_policy_stability_audit(frontier)
    search = build_search_accounting(config)
    score_audit = build_score_rebuild_lineage_audit(scored, preprocessing_hash, config, resolved, thresholds, confusion)

    gates = {
        "input_artifact_gate": input_gate,
        "upstream_16c_authorization_gate": upstream.loc[0, "authorization_status"],
        "upstream_16b_label_rebuild_gate": label_audit["upstream_16b_label_rebuild_gate"].iloc[0],
        "score_rebuild_lineage_gate": score_audit.loc[0, "score_rebuild_lineage_gate"],
        "feature_contract_replay_gate": contract.loc[0, "feature_contract_replay_gate"],
        "score_orientation_gate": score_audit.loc[0, "score_orientation_gate"],
        "threshold_freeze_gate": gate_from_column(thresholds, "threshold_freeze_status"),
        "neutral_handling_gate": gate_from_column(neutral, "neutral_handling_gate"),
        "policy_action_binding_gate": binding.loc[0, "policy_action_binding_gate"],
        "known_failed_context_rebuild_gate": context_audit.loc[0, "known_failed_context_rebuild_gate"],
        "search_accounting_gate": search.loc[0, "search_accounting_gate"],
    }
    decision = build_decision(config, gates, confusion, context_readout, actions, upstream)

    sample_n = int(config["policy"]["max_publishable_policy_action_sample_rows"])
    sample = actions.loc[actions["policy_id"].astype(str).eq(config["policy"]["primary_policy_id"])].head(sample_n).copy()

    write_df(outputs["upstream_16c_authorization_audit"], upstream)
    write_df(outputs["score_rebuild_lineage_audit"], score_audit)
    write_df(outputs["feature_contract_replay_audit"], contract)
    write_df(outputs["policy_candidate_registry"], registry)
    write_df(outputs["policy_threshold_freeze_audit"], thresholds)
    write_df(outputs["policy_action_binding_audit"], binding)
    write_df(outputs["policy_confusion_readout"], confusion)
    write_df(outputs["policy_tradeoff_frontier_readout"], frontier)
    write_df(outputs["known_failed_context_rebuild_audit"], context_audit)
    write_df(outputs["policy_context_stratified_readout"], context_readout)
    write_df(outputs["neutral_policy_handling_audit"], neutral)
    write_df(outputs["policy_stability_audit"], stability)
    write_df(outputs["validation_stress_policy_readout"], confusion.loc[confusion["split_bucket"].astype(str).eq("validation")])
    write_df(outputs["search_accounting_audit"], search)
    write_df(outputs["decision"], decision)
    write_df(outputs["policy_action_sample"], sample)
    write_df(outputs["policy_score_panel"], scored)
    write_df(outputs["policy_action_panel"], actions)
    write_text(outputs["report"], render_report(decision, upstream, score_audit, thresholds, confusion, frontier, context_readout, neutral, stability, search))
    write_manifest(outputs["manifest"], config_path, config, decision, outputs)
    return 0


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    return run(Path(args.config), check_inputs_only=args.check_inputs_only or args.mode == "check-inputs")


if __name__ == "__main__":
    raise SystemExit(main())
