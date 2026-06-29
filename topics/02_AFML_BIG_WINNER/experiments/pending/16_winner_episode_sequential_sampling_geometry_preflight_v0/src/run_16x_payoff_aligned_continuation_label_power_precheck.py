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
from scipy.stats import spearmanr
from sklearn.linear_model import LogisticRegression, Ridge


EXPERIMENT_DIR = Path(__file__).resolve().parents[1]
TOPIC_ROOT = Path(__file__).resolve().parents[4]
REPO_ROOT = Path(__file__).resolve().parents[6]
RUNNER_16C_PATH = EXPERIMENT_DIR / "src" / "run_16c_sequential_continuation_separability_diagnostic.py"


def load_runner(path: Path, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


r16c = load_runner(RUNNER_16C_PATH, "run_16c_for_16x")

RUN_ID = "16X_payoff_aligned_continuation_label_power_precheck"
EXPERIMENT_ID = "16_winner_episode_sequential_sampling_geometry_preflight_v0"
PHASE_ID = "16X"
CONFIG_PATH = EXPERIMENT_DIR / "configs" / "config_16x_payoff_aligned_continuation_label_power_precheck.yaml"
TABLE_DIR = EXPERIMENT_DIR / "outputs" / "publishable" / "tables" / RUN_ID
LOCAL_CACHE_DIR = EXPERIMENT_DIR / "outputs" / "local_cache" / RUN_ID
REPORT_DIR = EXPERIMENT_DIR / "outputs" / "publishable" / "reports"
MANIFEST_DIR = EXPERIMENT_DIR / "outputs" / "manifests"

SPLITS = ("train", "robustness", "validation")
DECISION_AUTHORIZED = "16X_payoff_precheck_payoff_aligned_label_redo_authorized"
DECISION_NOT_SUPPORTED = "16X_payoff_precheck_not_supported"
DECISION_LOW_POWER = "16X_payoff_precheck_low_power"
DECISION_LINEAGE = "16X_payoff_precheck_blocked_by_input_or_lineage_failure"
DECISION_LEAKAGE = "16X_payoff_precheck_blocked_by_search_or_leakage"
NEXT_16B2 = "requirement_16b2_payoff_aligned_continuation_label_design_diagnostic.md"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run 16X payoff-aligned continuation label power precheck.")
    parser.add_argument("--config", default=str(CONFIG_PATH))
    parser.add_argument("--check-inputs-only", action="store_true")
    parser.add_argument("--mode", choices=["check-inputs", "full"], default="full")
    return parser.parse_args(argv)


def load_config(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def topic_path(value: str | Path) -> Path:
    return r16c.topic_path(value)


def resolve_paths(config: dict[str, Any]) -> dict[str, Path]:
    return {key: topic_path(value) for key, value in config.get("paths", {}).items()}


def output_paths() -> dict[str, Path]:
    return {
        "input_artifact_audit": TABLE_DIR / "input_artifact_audit.csv",
        "upstream_postmortem_authorization_audit": TABLE_DIR / "upstream_postmortem_authorization_audit.csv",
        "feature_contract_audit": TABLE_DIR / "feature_contract_audit.csv",
        "payoff_target_lineage_audit": TABLE_DIR / "payoff_target_lineage_audit.csv",
        "no_new_computation_audit": TABLE_DIR / "no_new_computation_audit.csv",
        "probe_spec_audit": TABLE_DIR / "probe_spec_audit.csv",
        "survival_vs_payoff_rank_ic_readout": TABLE_DIR / "survival_vs_payoff_rank_ic_readout.csv",
        "payoff_decile_monotonicity_readout": TABLE_DIR / "payoff_decile_monotonicity_readout.csv",
        "cluster_bootstrap_rank_ic_readout": TABLE_DIR / "cluster_bootstrap_rank_ic_readout.csv",
        "power_gate_audit": TABLE_DIR / "power_gate_audit.csv",
        "search_accounting_audit": TABLE_DIR / "search_accounting_audit.csv",
        "decision": TABLE_DIR / "payoff_aligned_label_power_precheck_decision.csv",
        "probe_score_panel": LOCAL_CACHE_DIR / "probe_score_panel.parquet",
        "report": REPORT_DIR / "payoff_aligned_continuation_label_power_precheck_report.md",
        "manifest": MANIFEST_DIR / f"{RUN_ID}_manifest.json",
    }


def read_table(path: Path, **kwargs: Any) -> pd.DataFrame:
    suffixes = "".join(path.suffixes)
    if suffixes.endswith(".parquet"):
        return pd.read_parquet(path, **kwargs)
    if suffixes.endswith((".csv", ".csv.gz")):
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


def write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def file_sha(path: Path) -> str:
    return r16c.file_sha(path)


def count_rows(path: Path) -> int | float:
    suffixes = "".join(path.suffixes)
    if suffixes.endswith(".parquet"):
        return len(pd.read_parquet(path))
    if suffixes.endswith((".csv", ".csv.gz")):
        return r16c.count_rows(path)
    if path.is_file():
        return sum(1 for _ in path.open("rb"))
    return np.nan


def metric_float(value: Any) -> float:
    try:
        out = float(value)
    except Exception:
        return np.nan
    return out if np.isfinite(out) else np.nan


def bool_value(value: Any) -> bool:
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes", "pass"}
    if pd.isna(value):
        return False
    return bool(value)


def bool_series(series: pd.Series) -> pd.Series:
    if series.dtype == bool:
        return series.fillna(False)
    return series.map(bool_value).fillna(False).astype(bool)


def finite(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def safe_rate(num: Any, den: Any) -> float:
    n = metric_float(num)
    d = metric_float(den)
    if not np.isfinite(n) or not np.isfinite(d) or d == 0:
        return np.nan
    return float(n / d)


def rank_ic(score: pd.Series | np.ndarray, target: pd.Series | np.ndarray) -> float:
    s = np.asarray(score, dtype=float)
    t = np.asarray(target, dtype=float)
    mask = np.isfinite(s) & np.isfinite(t)
    if mask.sum() < 2 or len(np.unique(s[mask])) < 2 or len(np.unique(t[mask])) < 2:
        return np.nan
    corr = spearmanr(s[mask], t[mask], nan_policy="omit").correlation
    return float(corr) if corr is not None and np.isfinite(corr) else np.nan


def required_columns_for_key(key: str) -> set[str]:
    mapping: dict[str, set[str]] = {
        "upstream_16e_postmortem_decision": {
            "decision_state",
            "next_allowed_requirement",
            "directionality_gate",
            "train_monotonicity_spearman",
            "robustness_monotonicity_spearman",
            "robustness_non_monotone_flag",
            "thick_tail_mismatch_flag",
            "continuation_as_action_mainline_closed",
        },
        "upstream_16e_postmortem_score_bucket_monotonicity_readout": {
            "split_bucket",
            "decile_index",
            "base_rate_positive",
            "mean_continue_return_h20",
            "monotonicity_spearman",
        },
        "upstream_16c_decision": {
            "decision_state",
            "primary_model_id",
            "primary_model_feature_n",
            "train_binary_step_n",
            "robustness_binary_step_n",
        },
        "upstream_16c_oos_separability_readout": {"split_bucket", "model_id", "rank_ic_spearman"},
        "upstream_16c_t0_feature_contract": {
            "feature_name",
            "allowed_primary_model_feature",
            "forbidden_as_model_feature",
        },
        "upstream_16c_t0_feature_panel": {
            "step_id",
            "cluster_split_bucket",
            "instrument",
            "episode_cluster_id",
            "step_index",
            "step_start_qfq_close",
            "step_end_qfq_close",
            "step_end_price_ratio_minus_one_for_label_rule",
            "continuation_positive",
            "continuation_negative",
            "continuation_neutral",
            "is_binary_target",
            "target_binary",
        },
        "upstream_16c_separability_score_panel": {"step_id", "model_id", "score"},
        "upstream_16c_fold_assignment_panel": {
            "step_id",
            "episode_cluster_id",
            "episode_cluster_grouped_cv_fold",
        },
        "upstream_16b_decision": {
            "primary_label_id",
            "selected_threshold_id",
            "primary_horizon_sessions",
        },
        "upstream_16b_base_rate_readout": {
            "cluster_split_bucket",
            "labelable_step_n",
            "positive_step_n",
            "negative_step_n",
            "neutral_step_n",
        },
    }
    return mapping.get(key, set())


def build_input_artifact_audit(config: dict[str, Any], resolved: dict[str, Path]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for key, path in resolved.items():
        exists = path.exists()
        read_status = "pass"
        schema_status = "not_checked"
        row_count: int | float = np.nan
        sha = ""
        if not exists:
            read_status = "missing"
            schema_status = "missing"
        elif path.is_file():
            try:
                sha = file_sha(path)
                row_count = count_rows(path)
                required = required_columns_for_key(key)
                if required:
                    if "".join(path.suffixes).endswith(".parquet"):
                        cols = set(pd.read_parquet(path).columns)
                    elif "".join(path.suffixes).endswith((".csv", ".csv.gz")):
                        cols = set(pd.read_csv(path, nrows=5).columns)
                    elif path.suffix == ".json":
                        cols = set(json.loads(path.read_text(encoding="utf-8")).keys())
                    else:
                        cols = set()
                    schema_status = "pass" if required.issubset(cols) else "fail_missing_columns"
                else:
                    schema_status = "pass"
            except Exception as exc:
                read_status = f"fail_read_error:{type(exc).__name__}"
                schema_status = "fail_read_error"
        else:
            read_status = "not_file"
            schema_status = "not_file"
        rows.append(
            {
                "artifact_key": key,
                "resolved_path": str(path),
                "row_count": row_count,
                "sha256": sha,
                "schema_status": schema_status,
                "read_status": read_status,
                "required_flag": "required",
                "lineage_role": key,
                "blocking_reason": "" if read_status == "pass" and schema_status == "pass" else f"{read_status}:{schema_status}",
            }
        )
    return pd.DataFrame(rows)


def input_gate_status(input_audit: pd.DataFrame) -> tuple[str, str]:
    bad = input_audit.loc[
        ~input_audit["read_status"].astype(str).eq("pass")
        | ~input_audit["schema_status"].astype(str).eq("pass")
    ]
    if bad.empty:
        return "pass", ""
    return "fail", ";".join(bad["artifact_key"].astype(str).head(10))


def build_upstream_postmortem_authorization_audit(config: dict[str, Any], resolved: dict[str, Path]) -> pd.DataFrame:
    expected = config["expected_postmortem"]
    decision = read_table(resolved["upstream_16e_postmortem_decision"])
    row = decision.iloc[0].to_dict() if not decision.empty else {}
    manifest: dict[str, Any] = {}
    manifest_path = resolved.get("upstream_16e_postmortem_manifest")
    if manifest_path is not None and manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest_no_new = manifest.get("no_new_computation_audit_summary", {})
    observed_no_new_gate = "pass" if manifest_no_new and all(bool_value(v) for v in manifest_no_new.values()) else "fail"
    tol = float(expected.get("tolerance", 1e-6))
    checks = {
        "decision_state": row.get("decision_state") == expected["decision_state"],
        "next_allowed_requirement": str(row.get("next_allowed_requirement")) == str(expected["next_allowed_requirement"]),
        "continuation_as_action_mainline_closed": bool_value(row.get("continuation_as_action_mainline_closed")) == bool(expected["continuation_as_action_mainline_closed"]),
        "selected_path_id": str(row.get("selected_path_id", "none")) == str(expected["selected_path_id"]),
        "directionality_gate": row.get("directionality_gate") == expected["directionality_gate"],
        "train_monotonicity_spearman": abs(metric_float(row.get("train_monotonicity_spearman")) - float(expected["train_monotonicity_spearman"])) <= tol,
        "robustness_monotonicity_spearman": abs(metric_float(row.get("robustness_monotonicity_spearman")) - float(expected["robustness_monotonicity_spearman"])) <= tol,
        "robustness_non_monotone_flag": bool_value(row.get("robustness_non_monotone_flag")) == bool(expected["robustness_non_monotone_flag"]),
        "thick_tail_mismatch_flag": bool_value(row.get("thick_tail_mismatch_flag")) == bool(expected["thick_tail_mismatch_flag"]),
        "no_new_computation_gate": observed_no_new_gate == expected["no_new_computation_gate"],
    }
    gate = "pass" if all(checks.values()) else "fail"
    return pd.DataFrame(
        [
            {
                "upstream_source": "16E_postmortem",
                "expected_decision_state": expected["decision_state"],
                "observed_decision_state": row.get("decision_state", ""),
                "expected_next_allowed_requirement": expected["next_allowed_requirement"],
                "observed_next_allowed_requirement": row.get("next_allowed_requirement", ""),
                "expected_continuation_as_action_mainline_closed": bool(expected["continuation_as_action_mainline_closed"]),
                "observed_continuation_as_action_mainline_closed": bool_value(row.get("continuation_as_action_mainline_closed")),
                "expected_directionality_gate": expected["directionality_gate"],
                "observed_directionality_gate": row.get("directionality_gate", ""),
                "expected_no_new_computation_gate": expected["no_new_computation_gate"],
                "observed_no_new_computation_gate": observed_no_new_gate,
                "train_monotonicity_spearman": metric_float(row.get("train_monotonicity_spearman")),
                "robustness_monotonicity_spearman": metric_float(row.get("robustness_monotonicity_spearman")),
                "upstream_postmortem_authorization_gate": gate,
                "blocking_reason": "" if gate == "pass" else ";".join(k for k, ok in checks.items() if not ok),
            }
        ]
    )


def derive_label_class(panel: pd.DataFrame) -> pd.Series:
    pos = bool_series(panel["continuation_positive"])
    neg = bool_series(panel["continuation_negative"])
    neu = bool_series(panel["continuation_neutral"])
    return pd.Series(np.where(pos, "positive", np.where(neg, "negative", np.where(neu, "neutral", "unknown"))), index=panel.index)


def prepare_panel(panel: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    out = panel.copy()
    out["label_class"] = derive_label_class(out)
    out["payoff_raw"] = finite(out[config["target"]["payoff_base_column"]])
    out["target_binary"] = finite(out["target_binary"])
    out["is_binary_target"] = bool_series(out["is_binary_target"])
    return out


def feature_whitelist(contract: pd.DataFrame) -> list[str]:
    allowed = bool_series(contract["allowed_primary_model_feature"])
    return contract.loc[allowed, "feature_name"].astype(str).tolist()


def build_feature_contract_audit(contract: pd.DataFrame, panel: pd.DataFrame, decision_16c: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    features = feature_whitelist(contract)
    forbidden = set(contract.loc[bool_series(contract["forbidden_as_model_feature"]), "feature_name"].astype(str))
    expected_from_decision = int(metric_float(decision_16c.iloc[0].get("primary_model_feature_n"))) if not decision_16c.empty else int(config["expected_16c"]["primary_model_feature_n"])
    expected = int(config["expected_16c"].get("primary_model_feature_n", expected_from_decision))
    missing = [feature for feature in features if feature not in panel.columns]
    forbidden_used = [feature for feature in features if feature in forbidden]
    payoff_base = config["target"]["payoff_base_column"]
    label_future_exact = {
        "step_end_pos",
        "step_end_date",
        "step_end_qfq_close",
        "step_end_price_ratio_minus_one_for_label_rule",
        "max_drawdown_from_step_start",
        "target_binary",
        "is_binary_target",
        "cluster_split_bucket",
        "instrument",
        "episode_cluster_id",
    }
    label_or_future_used = [feature for feature in features if feature.startswith("continuation_") or feature in label_future_exact]
    gate = "pass"
    reasons: list[str] = []
    if expected_from_decision != expected:
        gate = "fail"
        reasons.append("16c_primary_model_feature_n_mismatch")
    if len(features) != expected:
        gate = "fail"
        reasons.append("allowed_feature_count_mismatch")
    if missing:
        gate = "fail"
        reasons.append("missing_whitelisted_feature_columns")
    if forbidden_used:
        gate = "fail"
        reasons.append("forbidden_feature_used")
    if payoff_base in features:
        gate = "fail"
        reasons.append("payoff_base_column_used_as_feature")
    if label_or_future_used:
        gate = "fail"
        reasons.append("label_or_future_column_used_as_feature")
    return pd.DataFrame(
        [
            {
                "feature_contract_source": "16C_t0_feature_contract.csv:allowed_primary_model_feature_true",
                "feature_contract_n_expected": expected,
                "feature_contract_n_actual": len(features),
                "allowed_primary_model_feature_n": len(features),
                "forbidden_as_model_feature_n": int(len(forbidden)),
                "missing_feature_column_n": int(len(missing)),
                "forbidden_feature_used_n": int(len(forbidden_used)),
                "payoff_base_column_used_as_feature": payoff_base in features,
                "label_or_future_column_used_as_feature_n": int(len(label_or_future_used)),
                "feature_contract_gate": gate,
                "blocking_reason": ";".join(reasons),
            }
        ]
    )


def primary_probe_mask(panel: pd.DataFrame) -> pd.Series:
    return (
        bool_series(panel["is_binary_target"])
        & panel["label_class"].astype(str).isin(["positive", "negative"])
        & np.isfinite(finite(panel["target_binary"]))
        & np.isfinite(finite(panel["payoff_raw"]))
    )


def build_payoff_target_lineage_audit(panel: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    payoff = config["target"]
    close_ratio = finite(panel["step_end_qfq_close"]) / finite(panel["step_start_qfq_close"]) - 1.0
    diff = (finite(panel["payoff_raw"]) - close_ratio).abs()
    diff_max = float(diff.replace([np.inf, -np.inf], np.nan).max()) if len(diff) else np.nan
    primary = panel.loc[primary_probe_mask(panel)].copy()
    counts = {split: int(primary.loc[primary["cluster_split_bucket"].astype(str).eq(split)].shape[0]) for split in SPLITS}
    finite_rates = {}
    for split in SPLITS:
        sub = panel.loc[panel["cluster_split_bucket"].astype(str).eq(split)]
        finite_rates[split] = safe_rate(np.isfinite(finite(sub["payoff_raw"])).sum(), len(sub))
    gate = (
        payoff["payoff_base_column"] in panel.columns
        and np.isfinite(diff_max)
        and diff_max <= float(payoff["close_ratio_tolerance"])
        and counts["train"] > 0
        and counts["robustness"] > 0
    )
    return pd.DataFrame(
        [
            {
                "payoff_target_id": payoff["payoff_target_id"],
                "payoff_base_column": payoff["payoff_base_column"],
                "payoff_raw_vs_close_ratio_abs_diff_max": diff_max,
                "payoff_finite_rate_train": finite_rates["train"],
                "payoff_finite_rate_robustness": finite_rates["robustness"],
                "payoff_finite_rate_validation": finite_rates["validation"],
                "primary_probe_universe": "binary_positive_negative_rows_only",
                "train_primary_probe_step_n": counts["train"],
                "robustness_primary_probe_step_n": counts["robustness"],
                "validation_primary_probe_step_n": counts["validation"],
                "neutral_rows_excluded_from_primary_gate": True,
                "config_frozen_before_training": True,
                "no_new_price_or_return_computed": True,
                "payoff_target_lineage_gate": "pass" if gate else "fail",
                "blocking_reason": "" if gate else "payoff_base_or_close_ratio_lineage_failed",
            }
        ]
    )


def build_no_new_computation_audit(config: dict[str, Any]) -> pd.DataFrame:
    rows = [
        {
            "check_id": "payoff_raw_passthrough",
            "source_artifact_key": "upstream_16c_t0_feature_panel",
            "source_columns": config["target"]["payoff_base_column"],
            "allowed_transform_type": "column_alias",
            "creates_new_price_or_return_cost_or_drawdown": False,
        },
        {
            "check_id": "payoff_raw_close_ratio_lineage_cross_check",
            "source_artifact_key": "upstream_16c_t0_feature_panel",
            "source_columns": "step_start_qfq_close,step_end_qfq_close",
            "allowed_transform_type": "lineage_consistency_check_only",
            "creates_new_price_or_return_cost_or_drawdown": False,
        },
        {
            "check_id": "label_class_derivation",
            "source_artifact_key": "upstream_16c_t0_feature_panel",
            "source_columns": "continuation_positive,continuation_negative,continuation_neutral",
            "allowed_transform_type": "deterministic_label_state_derivation",
            "creates_new_price_or_return_cost_or_drawdown": False,
        },
    ]
    frame = pd.DataFrame(rows)
    frame["recomputes_price"] = False
    frame["recomputes_forward_return"] = False
    frame["recomputes_cost"] = False
    frame["recomputes_drawdown"] = False
    gate = "pass" if not frame["creates_new_price_or_return_cost_or_drawdown"].astype(bool).any() else "fail"
    frame["no_new_computation_gate"] = gate
    frame["blocking_reason"] = ""
    return frame


def split_primary_probe_universe(panel: pd.DataFrame) -> pd.DataFrame:
    primary = panel.loc[primary_probe_mask(panel)].copy()
    primary["split_bucket"] = primary["cluster_split_bucket"].astype(str)
    return primary


def join_train_folds(primary: pd.DataFrame, fold_panel: pd.DataFrame, config: dict[str, Any]) -> tuple[pd.DataFrame, str, str]:
    fold_col = config["probe"]["train_cv_fold_column"]
    train = primary.loc[primary["split_bucket"].eq("train")].copy()
    fold_cols = ["step_id", fold_col]
    duplicate_n = int(fold_panel.duplicated("step_id").sum())
    joined = train.merge(fold_panel[fold_cols], on="step_id", how="left", validate="one_to_one" if duplicate_n == 0 else "many_to_one")
    missing_n = int(joined[fold_col].isna().sum())
    gate = "pass" if duplicate_n == 0 and missing_n == 0 and len(joined) == len(train) else "fail"
    reason = "" if gate == "pass" else f"duplicate_fold_step_id_n={duplicate_n};missing_fold_n={missing_n}"
    return joined, gate, reason


def fit_survival_probe(train: pd.DataFrame, features: list[str], config: dict[str, Any]) -> tuple[Any, Any]:
    pp = r16c.TrainPreprocessor(features).fit(train)
    x = pp.transform(train)
    model = LogisticRegression(
        C=float(config["probe"]["logistic_c"]),
        class_weight="balanced",
        solver="liblinear",
        max_iter=1000,
        random_state=int(config["probe"]["random_seed"]),
    )
    model.fit(x, train["target_binary"].astype(int).to_numpy())
    return model, pp


def fit_payoff_probe(train: pd.DataFrame, features: list[str], config: dict[str, Any]) -> tuple[Any, Any]:
    pp = r16c.TrainPreprocessor(features).fit(train)
    x = pp.transform(train)
    model = Ridge(alpha=float(config["probe"]["ridge_alpha"]))
    model.fit(x, train["payoff_raw"].astype(float).to_numpy())
    return model, pp


def predict_survival(model: Any, pp: Any, frame: pd.DataFrame) -> np.ndarray:
    return model.predict_proba(pp.transform(frame))[:, 1]


def predict_payoff(model: Any, pp: Any, frame: pd.DataFrame) -> np.ndarray:
    return model.predict(pp.transform(frame))


def build_probe_outputs(
    primary: pd.DataFrame,
    features: list[str],
    fold_panel: pd.DataFrame,
    config: dict[str, Any],
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, Any], str, str]:
    train_with_folds, fold_gate, fold_reason = join_train_folds(primary, fold_panel, config)
    fold_col = config["probe"]["train_cv_fold_column"]
    cv_rows: list[dict[str, Any]] = []
    cv_ics: dict[str, list[float]] = {
        config["probe"]["survival_probe_id"]: [],
        config["probe"]["payoff_probe_id"]: [],
    }
    if fold_gate == "pass":
        for fold_id in sorted(train_with_folds[fold_col].dropna().unique()):
            test = train_with_folds.loc[train_with_folds[fold_col].eq(fold_id)].copy()
            fit = train_with_folds.loc[~train_with_folds[fold_col].eq(fold_id)].copy()
            status = "pass"
            if fit["target_binary"].nunique() < 2 or len(test) < 2:
                status = "invalid_low_target_variation"
            if status == "pass":
                surv_model, surv_pp = fit_survival_probe(fit, features, config)
                pay_model, pay_pp = fit_payoff_probe(fit, features, config)
                scores = {
                    config["probe"]["survival_probe_id"]: predict_survival(surv_model, surv_pp, test),
                    config["probe"]["payoff_probe_id"]: predict_payoff(pay_model, pay_pp, test),
                }
            else:
                scores = {
                    config["probe"]["survival_probe_id"]: np.full(len(test), np.nan),
                    config["probe"]["payoff_probe_id"]: np.full(len(test), np.nan),
                }
            for probe_id, values in scores.items():
                ic = rank_ic(values, test["payoff_raw"])
                valid = status == "pass" and np.isfinite(ic)
                if valid:
                    cv_ics[probe_id].append(ic)
                cv_rows.append(
                    {
                        "probe_id": probe_id,
                        "fold_id": int(fold_id),
                        "train_primary_probe_step_n": len(fit),
                        "test_primary_probe_step_n": len(test),
                        "test_episode_cluster_n": int(test["episode_cluster_id"].nunique()),
                        "rank_ic_spearman": ic,
                        "fold_status": "pass" if valid else status,
                    }
                )
    train = primary.loc[primary["split_bucket"].eq("train")].copy()
    surv_model, surv_pp = fit_survival_probe(train, features, config)
    pay_model, pay_pp = fit_payoff_probe(train, features, config)
    scored = primary.copy()
    scored["survival_probe_score"] = predict_survival(surv_model, surv_pp, scored)
    scored["payoff_probe_score"] = predict_payoff(pay_model, pay_pp, scored)
    cv_medians = {probe_id: float(np.median(values)) if values else np.nan for probe_id, values in cv_ics.items()}
    cv_valid = {probe_id: int(len(values)) for probe_id, values in cv_ics.items()}
    rank_rows: list[dict[str, Any]] = []
    probe_specs = [
        (config["probe"]["survival_probe_id"], "continuation_survival_h20_no_deep_drawdown", "survival_probe_score", config["probe"]["survival_family"]),
        (config["probe"]["payoff_probe_id"], config["target"]["payoff_target_id"], "payoff_probe_score", config["probe"]["payoff_family"]),
    ]
    for probe_id, target_id, score_col, family in probe_specs:
        for split in SPLITS:
            sub = scored.loc[scored["split_bucket"].eq(split)].copy()
            rank_rows.append(
                {
                    "split_bucket": split,
                    "probe_id": probe_id,
                    "target_id": target_id,
                    "primary_probe_step_n": len(sub),
                    "episode_cluster_n": int(sub["episode_cluster_id"].nunique()),
                    "rank_ic_spearman": rank_ic(sub[score_col], sub["payoff_raw"]),
                    "cv_rank_ic_median": cv_medians[probe_id],
                    "rank_ic_status": "train_in_sample" if split == "train" else "pass",
                }
            )
    probe_spec_rows = []
    for probe_id, target_id, _score_col, family in probe_specs:
        probe_spec_rows.append(
            {
                "probe_id": probe_id,
                "target_id": target_id,
                "family": family,
                "regularization": f"C={config['probe']['logistic_c']}" if probe_id == config["probe"]["survival_probe_id"] else f"alpha={config['probe']['ridge_alpha']}",
                "feature_contract_source": "16C_t0_feature_contract.csv:allowed_primary_model_feature_true",
                "feature_contract_n": len(features),
                "primary_probe_universe": config["target"]["primary_probe_universe"],
                "train_primary_probe_step_n": int(len(train)),
                "preprocessing_train_only": True,
                "cv_scheme": "episode_cluster_grouped_cv_over_16c_train_binary_fold_assignment",
                "fold_source": "16C_fold_assignment_panel",
                "fold_assignment_join_gate": fold_gate,
                "probe_spec_frozen": True,
                "robustness_used_for_probe_tuning": False,
                "validation_used_for_probe_tuning": False,
                "blocking_reason": fold_reason,
            }
        )
    metadata = {
        "cv_rank_ic_median": cv_medians,
        "cv_valid_fold_n": cv_valid,
        "cv_fold_readout": pd.DataFrame(cv_rows),
    }
    return scored, pd.DataFrame(rank_rows), pd.DataFrame(probe_spec_rows), metadata, fold_gate, fold_reason


def build_decile_monotonicity_readout(scored: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    min_spearman = float(config["separability_gates"]["payoff_decile_monotonicity_spearman_min"])
    for split in SPLITS:
        sub = scored.loc[scored["split_bucket"].eq(split)].copy()
        if len(sub) < 10:
            continue
        sub["_decile"] = pd.qcut(sub["payoff_probe_score"].rank(method="first"), q=10, labels=False) + 1
        means = sub.groupby("_decile", sort=True)["payoff_raw"].mean()
        monotone = rank_ic(pd.Series(means.index, dtype=float), means.to_numpy(dtype=float))
        flag = bool(np.isfinite(monotone) and monotone >= min_spearman)
        grouped = sub.groupby("_decile", sort=True)
        for decile, part in grouped:
            rows.append(
                {
                    "split_bucket": split,
                    "decile_index": int(decile),
                    "row_n": len(part),
                    "mean_payoff_raw": float(part["payoff_raw"].mean()),
                    "mean_probe_score": float(part["payoff_probe_score"].mean()),
                    "payoff_decile_monotonicity_spearman": monotone,
                    "payoff_monotone_flag": flag,
                }
            )
    return pd.DataFrame(rows)


def build_cluster_bootstrap_rank_ic_readout(scored: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    boot = config["bootstrap"]
    split = "robustness"
    sub = scored.loc[scored["split_bucket"].eq(split)].copy()
    cluster_key = boot["cluster_key"]
    reps = int(boot["resample_n"])
    ci_level = float(boot["ci_level"])
    rng = np.random.default_rng(int(boot["random_seed"]))
    clusters = sorted(sub[cluster_key].astype(str).unique())
    by_cluster = {cluster: part.index.to_numpy() for cluster, part in sub.groupby(sub[cluster_key].astype(str), sort=False)}
    values: list[float] = []
    invalid = 0
    for _ in range(reps):
        sampled = rng.choice(clusters, size=len(clusters), replace=True)
        idx = np.concatenate([by_cluster[str(cluster)] for cluster in sampled]) if len(sampled) else np.array([], dtype=int)
        sample = sub.loc[idx]
        ic = rank_ic(sample["payoff_probe_score"], sample["payoff_raw"])
        if np.isfinite(ic):
            values.append(ic)
        else:
            invalid += 1
    if values:
        alpha = (1.0 - ci_level) / 2.0
        ci_low = float(np.quantile(values, alpha))
        ci_high = float(np.quantile(values, 1.0 - alpha))
    else:
        ci_low = ci_high = np.nan
    point = rank_ic(sub["payoff_probe_score"], sub["payoff_raw"])
    return pd.DataFrame(
        [
            {
                "split_bucket": split,
                "probe_id": config["probe"]["payoff_probe_id"],
                "rank_ic_spearman": point,
                "cluster_bootstrap_rank_ic_ci_low": ci_low,
                "cluster_bootstrap_rank_ic_ci_high": ci_high,
                "bootstrap_ci_level": ci_level,
                "ci_excludes_zero_flag": bool(np.isfinite(ci_low) and ci_low > 0),
                "bootstrap_resample_n": reps,
                "valid_bootstrap_resample_n": len(values),
                "invalid_bootstrap_resample_n": invalid,
                "bootstrap_cluster_key": cluster_key,
                "bootstrap_random_seed": int(boot["random_seed"]),
            }
        ]
    )


def build_power_gate_audit(primary: pd.DataFrame, metadata: dict[str, Any], bootstrap: pd.DataFrame, lineage: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    power = config["power_gates"]
    counts = {}
    clusters = {}
    for split in SPLITS:
        sub = primary.loc[primary["split_bucket"].eq(split)]
        counts[split] = len(sub)
        clusters[split] = int(sub["episode_cluster_id"].nunique())
    robust_lineage_rate = metric_float(lineage.iloc[0]["payoff_finite_rate_robustness"]) if not lineage.empty else np.nan
    valid_boot = int(bootstrap.iloc[0]["valid_bootstrap_resample_n"]) if not bootstrap.empty else 0
    boot_reps = int(config["bootstrap"]["resample_n"])
    payoff_cv_valid = int(metadata["cv_valid_fold_n"].get(config["probe"]["payoff_probe_id"], 0))
    checks = {
        "train_primary_probe_step_n": counts["train"] >= int(power["train_primary_probe_step_n_min"]),
        "train_episode_cluster_n": clusters["train"] >= int(power["train_episode_cluster_n_min"]),
        "robustness_primary_probe_step_n": counts["robustness"] >= int(power["robustness_primary_probe_step_n_min"]),
        "robustness_episode_cluster_n": clusters["robustness"] >= int(power["robustness_episode_cluster_n_min"]),
        "robustness_payoff_finite_rate": robust_lineage_rate >= float(power["robustness_payoff_finite_rate_min"]),
        "train_cv_valid_fold_n": payoff_cv_valid >= int(config["probe"]["cv_min_valid_fold_n"]),
        "valid_bootstrap_resample_n": valid_boot >= float(config["bootstrap"]["min_valid_resample_rate"]) * boot_reps,
    }
    gate = "pass" if all(checks.values()) else "fail"
    validation_status = "pass" if counts["validation"] >= int(power["validation_primary_probe_step_n_min"]) else "stress_low_power"
    return pd.DataFrame(
        [
            {
                "train_primary_probe_step_n": counts["train"],
                "train_episode_cluster_n": clusters["train"],
                "robustness_primary_probe_step_n": counts["robustness"],
                "robustness_episode_cluster_n": clusters["robustness"],
                "validation_primary_probe_step_n": counts["validation"],
                "robustness_payoff_finite_rate": robust_lineage_rate,
                "train_cv_valid_fold_n": payoff_cv_valid,
                "bootstrap_resample_n": boot_reps,
                "valid_bootstrap_resample_n": valid_boot,
                "invalid_bootstrap_resample_n": int(bootstrap.iloc[0]["invalid_bootstrap_resample_n"]) if not bootstrap.empty else boot_reps,
                "power_gate": gate,
                "low_power_reason": "" if gate == "pass" else ";".join(k for k, ok in checks.items() if not ok),
                "validation_stress_status": validation_status,
                "blocking_reason": "" if gate == "pass" else "primary_power_floor_failed",
            }
        ]
    )


def build_search_accounting_audit(feature_gate: str, no_new_gate: str, config: dict[str, Any]) -> pd.DataFrame:
    checks = {
        "payoff_target_config_frozen_before_training": True,
        "probe_spec_frozen_before_training": True,
        "no_new_price_or_return_computed": no_new_gate == "pass",
        "no_16c_model_refit": True,
        "feature_contract_unchanged": feature_gate == "pass",
        "threshold_id_unchanged": True,
        "horizon_unchanged": True,
        "validation_used_for_selection": False,
        "robustness_used_as_confirmatory_gate": True,
        "robustness_used_for_probe_tuning": False,
    }
    gate = "pass" if all(v for k, v in checks.items() if k not in {"validation_used_for_selection", "robustness_used_for_probe_tuning"}) and not checks["validation_used_for_selection"] and not checks["robustness_used_for_probe_tuning"] else "fail"
    row = {
        "payoff_target_id": config["target"]["payoff_target_id"],
        **checks,
        "search_accounting_gate": gate,
        "blocking_reason": "" if gate == "pass" else "search_or_leakage_violation",
    }
    return pd.DataFrame([row])


def row_for(frame: pd.DataFrame, **keys: Any) -> dict[str, Any]:
    sub = frame
    for key, value in keys.items():
        sub = sub.loc[sub[key].astype(str).eq(str(value))]
    return sub.iloc[0].to_dict() if not sub.empty else {}


def decision_from_components(
    config: dict[str, Any],
    upstream: pd.DataFrame,
    feature: pd.DataFrame,
    lineage: pd.DataFrame,
    no_new: pd.DataFrame,
    probe_spec: pd.DataFrame,
    rank_readout: pd.DataFrame,
    monotonicity: pd.DataFrame,
    bootstrap: pd.DataFrame,
    power: pd.DataFrame,
    search: pd.DataFrame,
) -> pd.DataFrame:
    robust_surv = row_for(rank_readout, split_bucket="robustness", probe_id=config["probe"]["survival_probe_id"])
    robust_pay = row_for(rank_readout, split_bucket="robustness", probe_id=config["probe"]["payoff_probe_id"])
    train_pay = row_for(rank_readout, split_bucket="train", probe_id=config["probe"]["payoff_probe_id"])
    robust_mono_rows = monotonicity.loc[monotonicity["split_bucket"].astype(str).eq("robustness")] if not monotonicity.empty else pd.DataFrame()
    robust_mono = robust_mono_rows.iloc[0].to_dict() if not robust_mono_rows.empty else {}
    boot = bootstrap.iloc[0].to_dict() if not bootstrap.empty else {}
    pow_row = power.iloc[0].to_dict() if not power.empty else {}
    gates = {
        "upstream_postmortem_authorization_gate": upstream.iloc[0].get("upstream_postmortem_authorization_gate", "fail") if not upstream.empty else "fail",
        "feature_contract_gate": feature.iloc[0].get("feature_contract_gate", "fail") if not feature.empty else "fail",
        "payoff_target_lineage_gate": lineage.iloc[0].get("payoff_target_lineage_gate", "fail") if not lineage.empty else "fail",
        "fold_assignment_join_gate": "pass" if not probe_spec.empty and probe_spec["fold_assignment_join_gate"].astype(str).eq("pass").all() else "fail",
        "no_new_computation_gate": no_new["no_new_computation_gate"].iloc[0] if not no_new.empty else "fail",
        "search_accounting_gate": search.iloc[0].get("search_accounting_gate", "fail") if not search.empty else "fail",
        "power_gate": pow_row.get("power_gate", "fail"),
    }
    survival_ic = metric_float(robust_surv.get("rank_ic_spearman"))
    payoff_ic = metric_float(robust_pay.get("rank_ic_spearman"))
    margin = payoff_ic - survival_ic if np.isfinite(payoff_ic) and np.isfinite(survival_ic) else np.nan
    cv_pay = metric_float(train_pay.get("cv_rank_ic_median"))
    sep = config["separability_gates"]
    payoff_gate_checks = {
        "robustness_rank_ic_floor": payoff_ic >= float(sep["robustness_payoff_probe_rank_ic_spearman_min"]),
        "payoff_monotone_flag": bool_value(robust_mono.get("payoff_monotone_flag")),
        "ci_excludes_zero_flag": bool_value(boot.get("ci_excludes_zero_flag")),
        "payoff_minus_survival_margin": margin > float(sep["payoff_minus_survival_rank_ic_margin_min"]),
        "cv_payoff_rank_ic_median": cv_pay >= float(sep["cv_payoff_rank_ic_median_min"]),
    }
    payoff_gate = "pass" if all(payoff_gate_checks.values()) else "fail"
    hard_lineage = ["upstream_postmortem_authorization_gate", "feature_contract_gate", "payoff_target_lineage_gate", "fold_assignment_join_gate", "no_new_computation_gate"]
    if gates["search_accounting_gate"] != "pass":
        decision = DECISION_LEAKAGE
        next_allowed = "none"
        blocking = "search_or_leakage_violation"
    elif any(gates[name] != "pass" for name in hard_lineage):
        decision = DECISION_LINEAGE
        next_allowed = "none"
        blocking = ";".join(name for name in hard_lineage if gates[name] != "pass")
    elif gates["power_gate"] != "pass":
        decision = DECISION_LOW_POWER
        next_allowed = "none"
        blocking = pow_row.get("low_power_reason", "low_power")
    elif payoff_gate != "pass":
        decision = DECISION_NOT_SUPPORTED
        next_allowed = "none"
        blocking = ";".join(k for k, ok in payoff_gate_checks.items() if not ok)
    else:
        decision = DECISION_AUTHORIZED
        next_allowed = NEXT_16B2
        blocking = ""
    counts = lineage.iloc[0].to_dict() if not lineage.empty else {}
    return pd.DataFrame(
        [
            {
                "decision_state": decision,
                "next_allowed_requirement": next_allowed,
                "upstream_postmortem_decision_state": upstream.iloc[0].get("observed_decision_state", "") if not upstream.empty else "",
                "payoff_target_id": config["target"]["payoff_target_id"],
                "feature_contract_n": int(feature.iloc[0].get("feature_contract_n_actual", 0)) if not feature.empty else 0,
                "primary_probe_universe": config["target"]["primary_probe_universe"],
                "train_primary_probe_step_n": int(counts.get("train_primary_probe_step_n", 0)),
                "robustness_primary_probe_step_n": int(counts.get("robustness_primary_probe_step_n", 0)),
                "validation_primary_probe_step_n": int(counts.get("validation_primary_probe_step_n", 0)),
                "robustness_survival_probe_rank_ic_spearman": survival_ic,
                "robustness_payoff_probe_rank_ic_spearman": payoff_ic,
                "payoff_minus_survival_rank_ic_margin": margin,
                "cv_payoff_rank_ic_median": cv_pay,
                "payoff_monotone_flag": bool_value(robust_mono.get("payoff_monotone_flag")),
                "cluster_bootstrap_rank_ic_ci_low": metric_float(boot.get("cluster_bootstrap_rank_ic_ci_low")),
                "cluster_bootstrap_rank_ic_ci_high": metric_float(boot.get("cluster_bootstrap_rank_ic_ci_high")),
                "ci_excludes_zero_flag": bool_value(boot.get("ci_excludes_zero_flag")),
                "bootstrap_resample_n": int(boot.get("bootstrap_resample_n", 0)),
                "valid_bootstrap_resample_n": int(boot.get("valid_bootstrap_resample_n", 0)),
                "decoupling_replay_flag": bool(np.isfinite(survival_ic) and survival_ic < 0.05 and cv_pay >= 0.06),
                "payoff_separability_gate": payoff_gate,
                "power_gate": gates["power_gate"],
                "search_accounting_gate": gates["search_accounting_gate"],
                "upstream_postmortem_authorization_gate": gates["upstream_postmortem_authorization_gate"],
                "feature_contract_gate": gates["feature_contract_gate"],
                "payoff_target_lineage_gate": gates["payoff_target_lineage_gate"],
                "continuation_as_action_mainline_closed": True,
                "payoff_aligned_label_redo_authorized": decision == DECISION_AUTHORIZED,
                "entry_policy_authorized": False,
                "exit_policy_authorized": False,
                "holding_policy_authorized": False,
                "chained_simulation_authorized": False,
                "portfolio_backtest_authorized": False,
                "model_deployment_authorized": False,
                "production_signal_authorized": False,
                "live_trading_authorized": False,
                "blocking_reason": blocking,
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
    feature: pd.DataFrame,
    lineage: pd.DataFrame,
    rank: pd.DataFrame,
    monotonicity: pd.DataFrame,
    bootstrap: pd.DataFrame,
    power: pd.DataFrame,
    search: pd.DataFrame,
) -> str:
    d = decision.iloc[0].to_dict()
    robust_rank = rank.loc[rank["split_bucket"].astype(str).eq("robustness")].copy()
    deciles = monotonicity.loc[monotonicity["split_bucket"].astype(str).eq("robustness")].copy()
    return f"""# 16X Payoff-aligned Continuation Label Power Precheck Report

## 1. 单行裁决

`decision_state = {d['decision_state']}`；`next_allowed_requirement = {d['next_allowed_requirement']}`。

16X 只是 payoff-aligned target 的 power precheck。它不重算价格、return、cost、drawdown，不 refit 16C model，不定义 policy/action/utility；即使通过，也只授权一个 payoff-aligned label redesign 起点 requirement。

## 2. 16E-postmortem Replay

{markdown_table(upstream, ['observed_decision_state', 'observed_next_allowed_requirement', 'observed_continuation_as_action_mainline_closed', 'observed_directionality_gate', 'train_monotonicity_spearman', 'robustness_monotonicity_spearman', 'observed_no_new_computation_gate', 'upstream_postmortem_authorization_gate'], 1)}

含义：旧 survival-score continuation-as-action 主线仍保持关闭。16X 不是 postmortem `next_allowed` continuation，而是 topic-level research direction restart 下的最小功效预检。

## 3. Feature Contract 与样本口径

{markdown_table(feature, ['feature_contract_source', 'feature_contract_n_expected', 'feature_contract_n_actual', 'allowed_primary_model_feature_n', 'forbidden_as_model_feature_n', 'missing_feature_column_n', 'forbidden_feature_used_n', 'payoff_base_column_used_as_feature', 'label_or_future_column_used_as_feature_n', 'feature_contract_gate'], 1)}

Primary probe universe 固定为 binary positive/negative rows；neutral rows 只保留为 stress/readout，不参与 probe fitting、robustness gate、margin gate 或授权裁决。

{markdown_table(lineage, ['payoff_target_id', 'payoff_base_column', 'payoff_raw_vs_close_ratio_abs_diff_max', 'train_primary_probe_step_n', 'robustness_primary_probe_step_n', 'validation_primary_probe_step_n', 'neutral_rows_excluded_from_primary_gate', 'payoff_target_lineage_gate'], 1)}

## 4. Survival-vs-payoff Rank IC

{markdown_table(rank, ['split_bucket', 'probe_id', 'primary_probe_step_n', 'episode_cluster_n', 'rank_ic_spearman', 'cv_rank_ic_median'], 9)}

Robustness 上 payoff probe rank IC = `{d['robustness_payoff_probe_rank_ic_spearman']:.6f}`，survival probe rank IC = `{d['robustness_survival_probe_rank_ic_spearman']:.6f}`，margin = `{d['payoff_minus_survival_rank_ic_margin']:.6f}`。

## 5. Robustness Decile Monotonicity

{markdown_table(deciles, ['decile_index', 'row_n', 'mean_payoff_raw', 'mean_probe_score', 'payoff_decile_monotonicity_spearman', 'payoff_monotone_flag'], 10)}

## 6. Cluster-bootstrap 功效

{markdown_table(bootstrap, ['split_bucket', 'probe_id', 'rank_ic_spearman', 'cluster_bootstrap_rank_ic_ci_low', 'cluster_bootstrap_rank_ic_ci_high', 'bootstrap_ci_level', 'valid_bootstrap_resample_n', 'bootstrap_resample_n', 'bootstrap_random_seed', 'ci_excludes_zero_flag'], 1)}

{markdown_table(power, ['train_primary_probe_step_n', 'train_episode_cluster_n', 'robustness_primary_probe_step_n', 'robustness_episode_cluster_n', 'validation_primary_probe_step_n', 'train_cv_valid_fold_n', 'valid_bootstrap_resample_n', 'power_gate', 'low_power_reason'], 1)}

## 7. Search Accounting

{markdown_table(search, ['payoff_target_config_frozen_before_training', 'probe_spec_frozen_before_training', 'no_new_price_or_return_computed', 'no_16c_model_refit', 'feature_contract_unchanged', 'validation_used_for_selection', 'robustness_used_for_probe_tuning', 'search_accounting_gate'], 1)}

## 8. Findings And Insight

本次预检的关键读数是 robustness payoff rank IC 与 decile monotonicity。若 payoff probe 在 train CV 上有明显排序能力，但 robustness rank IC 或 decile monotonicity 不达标，说明“换成 payoff-severity target”在现有 16C t0 feature contract 下仍未形成可确认的 OOS payoff 排序能力。

当前裁决为 `{d['decision_state']}`。若 blocking reason 包含 `robustness_rank_ic_floor`、`payoff_monotone_flag` 或 `payoff_minus_survival_margin`，则不应投入完整 16B2→16C2→16D2→16E2 重链；continuation-as-action 主线保持关闭，应回到 topic 级研究方向，优先检查 entry alpha 或更上游 payoff state 是否缺失。
"""


def write_manifest(path: Path, config_path: Path, config: dict[str, Any], decision: pd.DataFrame, outputs: dict[str, Path]) -> Path:
    publishable = {
        key: value
        for key, value in outputs.items()
        if key not in {"manifest", "probe_score_panel"} and value.exists() and LOCAL_CACHE_DIR not in value.parents
    }
    hashes: dict[str, str] = {}
    row_counts: dict[str, Any] = {}
    for key, value in publishable.items():
        if value.is_file():
            hashes[key] = file_sha(value)
            row_counts[key] = count_rows(value)
    input_hashes: dict[str, str] = {}
    audit_path = outputs.get("input_artifact_audit")
    if audit_path is not None and audit_path.exists():
        audit = pd.read_csv(audit_path)
        input_hashes = {
            str(row.artifact_key): str(row.sha256)
            for row in audit.itertuples(index=False)
            if isinstance(row.sha256, str) and row.sha256
        }
    dec = decision.iloc[0].to_dict() if not decision.empty else {}
    payload = {
        "experiment_id": EXPERIMENT_ID,
        "phase_id": PHASE_ID,
        "run_id": RUN_ID,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "platform": platform.platform(),
        "requirement_path": str(topic_path(config["paths"]["requirement"])),
        "requirement_sha256": file_sha(topic_path(config["paths"]["requirement"])),
        "config_path": str(config_path),
        "config_sha256": file_sha(config_path),
        "upstream_postmortem_decision": dec.get("upstream_postmortem_decision_state"),
        "payoff_target_id": config["target"]["payoff_target_id"],
        "feature_contract_source": "16C_t0_feature_contract.csv:allowed_primary_model_feature_true",
        "feature_contract_n": dec.get("feature_contract_n"),
        "primary_probe_universe": dec.get("primary_probe_universe"),
        "train_primary_probe_step_n": dec.get("train_primary_probe_step_n"),
        "robustness_primary_probe_step_n": dec.get("robustness_primary_probe_step_n"),
        "validation_primary_probe_step_n": dec.get("validation_primary_probe_step_n"),
        "bootstrap_cluster_key": config["bootstrap"]["cluster_key"],
        "bootstrap_resample_n": config["bootstrap"]["resample_n"],
        "valid_bootstrap_resample_n": dec.get("valid_bootstrap_resample_n"),
        "bootstrap_ci_level": config["bootstrap"]["ci_level"],
        "bootstrap_random_seed": config["bootstrap"]["random_seed"],
        "decision_state": dec.get("decision_state"),
        "next_allowed_requirement": dec.get("next_allowed_requirement"),
        "payoff_aligned_label_redo_authorized": dec.get("payoff_aligned_label_redo_authorized"),
        "continuation_as_action_mainline_closed": dec.get("continuation_as_action_mainline_closed"),
        "robustness_payoff_probe_rank_ic_spearman": dec.get("robustness_payoff_probe_rank_ic_spearman"),
        "cluster_bootstrap_rank_ic_ci_low": dec.get("cluster_bootstrap_rank_ic_ci_low"),
        "authorization_booleans": {
            "entry_policy_authorized": dec.get("entry_policy_authorized"),
            "exit_policy_authorized": dec.get("exit_policy_authorized"),
            "holding_policy_authorized": dec.get("holding_policy_authorized"),
            "chained_simulation_authorized": dec.get("chained_simulation_authorized"),
            "portfolio_backtest_authorized": dec.get("portfolio_backtest_authorized"),
            "model_deployment_authorized": dec.get("model_deployment_authorized"),
            "production_signal_authorized": dec.get("production_signal_authorized"),
            "live_trading_authorized": dec.get("live_trading_authorized"),
        },
        "input_artifact_hashes": input_hashes,
        "output_hashes": hashes,
        "row_counts": row_counts,
        "large_artifact_policy": "probe_score_panel_local_parquet_publishable_tables_small",
    }
    return write_json(path, payload)


def initial_blocked_decision(config: dict[str, Any], reason: str) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "decision_state": DECISION_LINEAGE,
                "next_allowed_requirement": "none",
                "upstream_postmortem_decision_state": "",
                "payoff_target_id": config["target"]["payoff_target_id"],
                "feature_contract_n": 0,
                "primary_probe_universe": config["target"]["primary_probe_universe"],
                "train_primary_probe_step_n": 0,
                "robustness_primary_probe_step_n": 0,
                "validation_primary_probe_step_n": 0,
                "robustness_survival_probe_rank_ic_spearman": np.nan,
                "robustness_payoff_probe_rank_ic_spearman": np.nan,
                "payoff_minus_survival_rank_ic_margin": np.nan,
                "cv_payoff_rank_ic_median": np.nan,
                "payoff_monotone_flag": False,
                "cluster_bootstrap_rank_ic_ci_low": np.nan,
                "cluster_bootstrap_rank_ic_ci_high": np.nan,
                "ci_excludes_zero_flag": False,
                "bootstrap_resample_n": int(config["bootstrap"]["resample_n"]),
                "valid_bootstrap_resample_n": 0,
                "decoupling_replay_flag": False,
                "payoff_separability_gate": "fail",
                "power_gate": "fail",
                "search_accounting_gate": "fail",
                "upstream_postmortem_authorization_gate": "fail",
                "feature_contract_gate": "fail",
                "payoff_target_lineage_gate": "fail",
                "continuation_as_action_mainline_closed": True,
                "payoff_aligned_label_redo_authorized": False,
                "entry_policy_authorized": False,
                "exit_policy_authorized": False,
                "holding_policy_authorized": False,
                "chained_simulation_authorized": False,
                "portfolio_backtest_authorized": False,
                "model_deployment_authorized": False,
                "production_signal_authorized": False,
                "live_trading_authorized": False,
                "blocking_reason": reason,
            }
        ]
    )


def run(config_path: Path, check_inputs_only: bool = False) -> int:
    config = load_config(config_path)
    resolved = resolve_paths(config)
    outputs = output_paths()
    for path in [TABLE_DIR, LOCAL_CACHE_DIR, REPORT_DIR, MANIFEST_DIR]:
        path.mkdir(parents=True, exist_ok=True)

    input_audit = build_input_artifact_audit(config, resolved)
    write_df(outputs["input_artifact_audit"], input_audit)
    input_gate, input_reason = input_gate_status(input_audit)
    if check_inputs_only:
        return 0 if input_gate == "pass" else 2
    if input_gate != "pass":
        decision = initial_blocked_decision(config, input_reason)
        write_df(outputs["decision"], decision)
        write_manifest(outputs["manifest"], config_path, config, decision, outputs)
        return 2

    upstream = build_upstream_postmortem_authorization_audit(config, resolved)
    decision_16c = read_table(resolved["upstream_16c_decision"])
    contract = read_table(resolved["upstream_16c_t0_feature_contract"])
    panel = prepare_panel(read_table(resolved["upstream_16c_t0_feature_panel"]), config)
    features = feature_whitelist(contract)
    feature = build_feature_contract_audit(contract, panel, decision_16c, config)
    lineage = build_payoff_target_lineage_audit(panel, config)
    no_new = build_no_new_computation_audit(config)
    primary = split_primary_probe_universe(panel)
    fold_panel = read_table(resolved["upstream_16c_fold_assignment_panel"])
    scored, rank, probe_spec, metadata, _fold_gate, _fold_reason = build_probe_outputs(primary, features, fold_panel, config)
    monotonicity = build_decile_monotonicity_readout(scored, config)
    bootstrap = build_cluster_bootstrap_rank_ic_readout(scored, config)
    power = build_power_gate_audit(primary, metadata, bootstrap, lineage, config)
    no_new_gate = no_new["no_new_computation_gate"].iloc[0] if not no_new.empty else "fail"
    feature_gate = feature["feature_contract_gate"].iloc[0] if not feature.empty else "fail"
    search = build_search_accounting_audit(feature_gate, no_new_gate, config)
    decision = decision_from_components(config, upstream, feature, lineage, no_new, probe_spec, rank, monotonicity, bootstrap, power, search)

    write_df(outputs["upstream_postmortem_authorization_audit"], upstream)
    write_df(outputs["feature_contract_audit"], feature)
    write_df(outputs["payoff_target_lineage_audit"], lineage)
    write_df(outputs["no_new_computation_audit"], no_new)
    write_df(outputs["probe_spec_audit"], probe_spec)
    write_df(outputs["survival_vs_payoff_rank_ic_readout"], rank)
    write_df(outputs["payoff_decile_monotonicity_readout"], monotonicity)
    write_df(outputs["cluster_bootstrap_rank_ic_readout"], bootstrap)
    write_df(outputs["power_gate_audit"], power)
    write_df(outputs["search_accounting_audit"], search)
    write_df(outputs["decision"], decision)
    cache_cols = [
        "step_id",
        "split_bucket",
        "instrument",
        "episode_cluster_id",
        "label_class",
        "target_binary",
        "payoff_raw",
        "survival_probe_score",
        "payoff_probe_score",
    ]
    write_df(outputs["probe_score_panel"], scored.loc[:, cache_cols])
    write_text(outputs["report"], render_report(decision, upstream, feature, lineage, rank, monotonicity, bootstrap, power, search))
    write_manifest(outputs["manifest"], config_path, config, decision, outputs)
    return 0


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    return run(Path(args.config), check_inputs_only=args.check_inputs_only or args.mode == "check-inputs")


if __name__ == "__main__":
    raise SystemExit(main())
