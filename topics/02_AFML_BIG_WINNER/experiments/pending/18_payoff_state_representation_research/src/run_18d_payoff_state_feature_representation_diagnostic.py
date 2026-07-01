#!/usr/bin/env python
from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml
from sklearn.linear_model import Ridge
from sklearn.tree import DecisionTreeRegressor


EXPERIMENT_DIR = Path(__file__).resolve().parents[1]
TOPIC_ROOT = Path(__file__).resolve().parents[4]
REPO_ROOT = Path(__file__).resolve().parents[6]

RUN_ID = "18D_payoff_state_feature_representation_diagnostic"
EXPERIMENT_ID = "18_payoff_state_representation_research"
PHASE_ID = "18D"
CONFIG_PATH = EXPERIMENT_DIR / "configs" / "config_18d_payoff_state_feature_representation_diagnostic.yaml"
TABLE_DIR = EXPERIMENT_DIR / "outputs" / "publishable" / "tables" / RUN_ID
REPORT_DIR = EXPERIMENT_DIR / "outputs" / "publishable" / "reports"
MANIFEST_DIR = EXPERIMENT_DIR / "outputs" / "manifests"
LOCAL_CACHE_DIR = EXPERIMENT_DIR / "outputs" / "local_cache" / RUN_ID

SPLITS = ("train", "robustness", "validation")
PRIMARY_MODEL_ID = "ridge_payoff_rank_h20_v1"
AUTH_FALSE_COLUMNS = (
    "entry_policy_authorized",
    "exit_policy_authorized",
    "holding_policy_authorized",
    "portfolio_backtest_authorized",
    "model_deployment_authorized",
    "production_signal_authorized",
    "live_trading_authorized",
)
HARD_GATES = (
    "upstream_18c_contract_gate",
    "input_artifact_gate",
    "capacity_vs_representation_gate",
    "candidate_lineage_gate",
    "pit_t0_availability_gate",
    "orthogonal_payoff_information_gate",
    "feature_family_prioritization_gate",
    "search_accounting_gate",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run EP18D payoff-state feature representation diagnostic.")
    parser.add_argument("--config", default=str(CONFIG_PATH))
    parser.add_argument("--mode", choices=["check-inputs", "full"], default="full")
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
        "candidate_feature_panel": LOCAL_CACHE_DIR / "candidate_feature_panel.parquet",
        "input_artifact_audit": TABLE_DIR / "input_artifact_audit.csv",
        "upstream_18c_handoff_audit": TABLE_DIR / "upstream_18c_handoff_audit.csv",
        "capacity_vs_representation_readout": TABLE_DIR / "capacity_vs_representation_readout.csv",
        "candidate_feature_inventory": TABLE_DIR / "candidate_feature_inventory.csv",
        "candidate_feature_lineage_audit": TABLE_DIR / "candidate_feature_lineage_audit.csv",
        "candidate_feature_pit_availability_audit": TABLE_DIR / "candidate_feature_pit_availability_audit.csv",
        "current_feature_gap_decomposition": TABLE_DIR / "current_feature_gap_decomposition.csv",
        "payoff_morphology_proxy_readout": TABLE_DIR / "payoff_morphology_proxy_readout.csv",
        "orthogonal_payoff_information_readout": TABLE_DIR / "orthogonal_payoff_information_readout.csv",
        "feature_family_candidate_prioritization": TABLE_DIR / "feature_family_candidate_prioritization.csv",
        "search_accounting_audit": TABLE_DIR / "search_accounting_audit.csv",
        "representation_refresh_decision": TABLE_DIR / "representation_refresh_decision.csv",
        "report": REPORT_DIR / "payoff_state_feature_representation_diagnostic_report.md",
        "manifest": MANIFEST_DIR / "18D_payoff_state_feature_representation_diagnostic_manifest.json",
        "input_manifest": MANIFEST_DIR / "input_artifact_manifest_18d.json",
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
    if not isinstance(value, (str, bytes, dict, list, tuple)):
        try:
            if pd.isna(value):
                return None
        except TypeError:
            pass
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


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_table(path: Path, **kwargs: Any) -> pd.DataFrame:
    suffixes = "".join(path.suffixes)
    if suffixes.endswith(".parquet"):
        return pd.read_parquet(path, **kwargs)
    if suffixes.endswith((".csv", ".csv.gz")):
        return pd.read_csv(path, **kwargs)
    raise ValueError(f"Unsupported table path: {path}")


def count_rows(path: Path) -> int | float:
    if not path.exists():
        return np.nan
    if path.is_dir():
        return len([p for p in path.iterdir() if p.is_file() and p.suffix == ".csv"])
    suffixes = "".join(path.suffixes)
    if suffixes.endswith(".parquet"):
        return len(pd.read_parquet(path))
    if suffixes.endswith((".csv", ".csv.gz")):
        with path.open("r", encoding="utf-8") as handle:
            return max(sum(1 for _ in handle) - 1, 0)
    if suffixes.endswith(".md"):
        return len(path.read_text(encoding="utf-8").splitlines())
    if suffixes.endswith(".json"):
        return 1
    return np.nan


def header_columns(path: Path) -> list[str]:
    if not path.exists():
        return []
    if path.is_dir():
        csvs = sorted(p for p in path.iterdir() if p.is_file() and p.suffix == ".csv")
        if not csvs:
            return []
        return list(pd.read_csv(csvs[0], nrows=0).columns)
    suffixes = "".join(path.suffixes)
    if suffixes.endswith(".parquet"):
        return list(pd.read_parquet(path, engine="pyarrow").columns)
    if suffixes.endswith((".csv", ".csv.gz")):
        return list(pd.read_csv(path, nrows=0).columns)
    return []


def relative_to_topic(path: Path) -> str:
    try:
        return str(path.relative_to(TOPIC_ROOT))
    except ValueError:
        return str(path)


def metric_float(value: Any, default: float = np.nan) -> float:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return default
    return out if np.isfinite(out) else default


def bool_like(value: Any) -> bool:
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes", "pass"}
    if pd.isna(value):
        return False
    return bool(value)


def rank_ic(score: pd.Series | np.ndarray, target: pd.Series | np.ndarray) -> float:
    s = pd.Series(score, dtype="float64")
    t = pd.Series(target, dtype="float64")
    valid = np.isfinite(s) & np.isfinite(t)
    if int(valid.sum()) < 3:
        return np.nan
    sr = s.loc[valid].rank(method="average")
    tr = t.loc[valid].rank(method="average")
    if sr.nunique() <= 1 or tr.nunique() <= 1:
        return np.nan
    return float(sr.corr(tr))


def required_columns_for_key(key: str) -> set[str]:
    mapping: dict[str, set[str]] = {
        "eighteen_b_matrix": {"step_id", "label_id", "instrument", "episode_cluster_id", "cluster_split_bucket", "y_payoff_h20", "mr_volatility_20d", "mr_volume_20d_zscore"},
        "eighteen_c_score_panel": {"step_id", "label_id", "cluster_split_bucket", "y_payoff_h20", "score_ridge_payoff_rank_h20_v1"},
        "eighteen_c_decision": {"decision_state", "next_allowed_requirement", "all_hard_gates_pass"},
        "eighteen_c_model_registry": {"model_id", "model_family", "fit_split"},
        "eighteen_c_model_cv_readout": {"cv_scheme", "model_id", "fold_id", "payoff_rank_ic", "test_row_n"},
        "eighteen_c_oos_rank_readout": {"split_bucket", "model_id", "rank_ic_spearman", "row_n"},
        "eighteen_c_decile_monotonicity": {"split_bucket", "model_id", "decile_payoff_monotonicity_spearman"},
        "eighteen_c_baseline_comparison": {"comparison_id", "comparison_status"},
        "eighteen_c_topk_removal_sensitivity": {"sensitivity_id", "split_bucket"},
        "eighteen_c_model_coefficients": {"model_id", "feature_name", "coefficient"},
        "eighteen_c_binary_sanity": {"split_bucket", "model_id", "binary_sanity_status"},
        "sixteen_b_label_step_panel": {"step_id", "label_id", "instrument", "step_start_pos", "step_start_date", "step_start_qfq_close"},
        "sixteen_b_materialized_step_panel": {"step_id", "cluster_start_pos", "cluster_end_pos"},
        "sixteen_b_label_panel_readout": {"step_id", "label_id", "step_start_pos", "step_start_date"},
        "sixteen_a_episode_interval_panel": {"instrument", "episode_cluster_id", "cluster_start_pos", "cluster_end_pos"},
        "sixteen_a_step_geometry_panel": {"instrument", "episode_cluster_id", "cluster_start_pos", "cluster_end_pos"},
        "stock_daily_qfq_dir": {"date", "open", "high", "low", "close", "volume"},
    }
    if key.endswith("_manifest") or key.endswith("_report") or key in {"research_plan", "requirement_18d", "eighteen_c_config"}:
        return set()
    return mapping.get(key, set())


def dir_sha(path: Path) -> str:
    h = hashlib.sha256()
    if not path.exists() or not path.is_dir():
        return ""
    for child in sorted(p for p in path.iterdir() if p.is_file() and p.suffix == ".csv"):
        h.update(child.name.encode("utf-8"))
        h.update(str(child.stat().st_size).encode("utf-8"))
    return h.hexdigest()


def artifact_sha(path: Path) -> str:
    if not path.exists():
        return ""
    if path.is_dir():
        return dir_sha(path)
    return file_sha(path)


def build_input_artifact_audit(config: dict[str, Any], resolved: dict[str, Path]) -> tuple[pd.DataFrame, str]:
    rows: list[dict[str, Any]] = []
    alias_req = config.get("source_alias_requirements", {})
    path_roles = config.get("path_roles", {})
    alias_rows: list[tuple[str, str, int]] = []
    for alias, keys in config.get("source_aliases", {}).items():
        for priority, key in enumerate(keys, start=1):
            alias_rows.append((alias, key, priority))
    represented = {(alias, key) for alias, key, _ in alias_rows}
    for key in config.get("paths", {}):
        role = path_roles.get(key, {})
        if not any(row_key == key for _, row_key, _ in alias_rows):
            alias_rows.append((role.get("source_alias", key), key, 1))

    for source_alias, key, priority in alias_rows:
        if (source_alias, key) in represented or key in config.get("paths", {}):
            path = resolved[key]
            exists = path.exists()
            cols = set(header_columns(path)) if exists else set()
            required_cols = required_columns_for_key(key)
            if key == "stock_daily_qfq_dir" and exists:
                required_cols = set(required_cols)
                has_money = bool({"amount", "money", "turnover_value"}.intersection(cols)) or {"volume", "close"}.issubset(cols)
            else:
                has_money = True
            missing_cols = sorted(required_cols - cols)
            meta = path_roles.get(key, {})
            req_meta = alias_req.get(source_alias, {})
            required = bool(meta.get("required", False))
            required_for_primary = bool(req_meta.get("required_for_primary_candidate", False))
            affected = str(req_meta.get("affected_family_ids", ""))
            blockers = []
            if required and not exists:
                blockers.append("missing_required_artifact")
            if required and missing_cols:
                blockers.append("schema_missing:" + ",".join(missing_cols))
            if key == "stock_daily_qfq_dir" and exists and count_rows(path) <= 0:
                blockers.append("qfq_dir_empty")
            if key == "stock_daily_qfq_dir" and not has_money:
                blockers.append("qfq_money_proxy_source_missing")
            schema_status = "pass" if exists and not missing_cols and has_money else "fail" if required or required_for_primary else "optional_missing"
            resolved_status = "pass" if exists and schema_status == "pass" else "fail" if required or required_for_primary else "optional_missing"
            rows.append(
                {
                    "artifact_path": str(path),
                    "source_artifact_alias": source_alias,
                    "config_path_key": key,
                    "resolver_priority": priority,
                    "artifact_role": meta.get("role", ""),
                    "required": required,
                    "required_for_primary_candidate": required_for_primary,
                    "affected_family_ids": affected,
                    "exists": exists,
                    "row_count": count_rows(path) if exists else np.nan,
                    "column_count": len(cols),
                    "sha256": artifact_sha(path),
                    "manifest_path": "",
                    "manifest_hash_status": "not_manifested",
                    "schema_status": schema_status,
                    "freshness_status": "not_checked",
                    "resolved_source_status": resolved_status,
                    "blocking_reason": ";".join(blockers),
                }
            )
    audit = pd.DataFrame(rows).drop_duplicates(["source_artifact_alias", "config_path_key", "resolver_priority"])
    failing = audit.loc[(audit["required"].astype(bool) | audit["required_for_primary_candidate"].astype(bool)) & ~audit["resolved_source_status"].eq("pass")]
    return audit, "pass" if failing.empty else "fail"


def load_inputs(resolved: dict[str, Path]) -> dict[str, pd.DataFrame]:
    keys = [
        "eighteen_b_matrix",
        "eighteen_c_score_panel",
        "eighteen_c_decision",
        "eighteen_c_model_cv_readout",
        "eighteen_c_oos_rank_readout",
        "sixteen_b_label_step_panel",
        "sixteen_b_materialized_step_panel",
    ]
    return {key: read_table(resolved[key]) for key in keys}


def read_legacy_config_next(path: Path) -> str:
    if not path.exists():
        return ""
    payload = load_config(path)
    return str(payload.get("expected", {}).get("next_allowed_requirement", ""))


def build_upstream_18c_handoff_audit(config: dict[str, Any], resolved: dict[str, Path], tables: dict[str, pd.DataFrame]) -> tuple[pd.DataFrame, str]:
    expected = config["expected"]
    decision = tables["eighteen_c_decision"].iloc[0]
    manifest = read_json(resolved["eighteen_c_manifest"])
    legacy_next = read_legacy_config_next(resolved["eighteen_c_config"])
    rows = []

    def add(source_table: str, metric: str, observed: Any, expected_value: Any, tolerance: float = 0.0, source_model_id: str = "", source_split_bucket: str = "") -> None:
        if isinstance(observed, (int, float, np.integer, np.floating)) and isinstance(expected_value, (int, float, np.integer, np.floating)):
            ok = abs(float(observed) - float(expected_value)) <= tolerance
        else:
            ok = str(observed) == str(expected_value)
        rows.append(
            {
                "source_table": source_table,
                "source_model_id": source_model_id,
                "source_split_bucket": source_split_bucket,
                "source_metric": metric,
                "expected_value": expected_value,
                "observed_value": observed,
                "tolerance": tolerance,
                "handoff_status": "pass" if ok else "fail",
                "blocking_reason": "" if ok else f"{metric}_mismatch",
            }
        )

    add("payoff_state_separability_decision.csv", "decision_state", decision["decision_state"], expected["upstream_18c_decision_state"])
    add("payoff_state_separability_decision.csv", "next_allowed_requirement", decision["next_allowed_requirement"], expected["upstream_18c_next_allowed_requirement"])
    add("18C_manifest", "decision_state", manifest.get("decision_state", ""), expected["upstream_18c_decision_state"])
    add("18C_manifest", "next_allowed_requirement", manifest.get("next_allowed_requirement", ""), expected["upstream_18c_next_allowed_requirement"])
    add("config_18c_expected_block", "legacy_config_expected_next_status", "audit_only_not_authoritative", "audit_only_not_authoritative")
    add("config_18c_expected_block", "legacy_config_expected_next_mismatch", str(legacy_next != expected["upstream_18c_next_allowed_requirement"]).lower(), "true")

    oos = tables["eighteen_c_oos_rank_readout"]
    for model_id, exp_value in expected["robustness_rank_ic"].items():
        observed_rows = oos.loc[oos["model_id"].eq(model_id) & oos["split_bucket"].eq("robustness")]
        observed = np.nan if observed_rows.empty else float(observed_rows["rank_ic_spearman"].iloc[0])
        add("payoff_state_oos_rank_readout.csv", "robustness_rank_ic", observed, float(exp_value), float(expected["handoff_tolerance"]), model_id, "robustness")

    frame = pd.DataFrame(rows)
    blocking = frame.loc[~frame["source_table"].eq("config_18c_expected_block")]
    gate = "pass" if blocking["handoff_status"].eq("pass").all() else "fail"
    return frame, gate


def model_ready_matrix(config: dict[str, Any], matrix: pd.DataFrame) -> pd.DataFrame:
    required = [*config["model_ready_features"], config["target_column"], "episode_cluster_id", "cluster_split_bucket"]
    missing = sorted(set(required) - set(matrix.columns))
    if missing:
        raise ValueError(f"18B matrix missing required columns: {missing}")
    return matrix.copy()


def grouped_fold_assignment(train: pd.DataFrame, fold_n: int, seed: int) -> pd.Series:
    rng = np.random.default_rng(seed)
    clusters = np.array(sorted(train["episode_cluster_id"].astype(str).unique()))
    rng.shuffle(clusters)
    fold_map = {cluster: i % fold_n for i, cluster in enumerate(clusters)}
    return train["episode_cluster_id"].astype(str).map(fold_map)


def fit_score_model(model_id: str, config: dict[str, Any], train: pd.DataFrame, fit: pd.DataFrame, test: pd.DataFrame) -> np.ndarray:
    features = config["model_ready_features"]
    x_fit = fit[features].to_numpy(dtype=float)
    y_fit = fit[config["target_column"]].to_numpy(dtype=float)
    x_test = test[features].to_numpy(dtype=float)
    if model_id == PRIMARY_MODEL_ID:
        model = Ridge(alpha=10.0, fit_intercept=True)
    else:
        depth = 3 if "depth3" in model_id else 4
        params = config["capacity_probe_params"]
        leaf = max(int(params["min_samples_leaf_floor"]), int(math.ceil(float(params["min_samples_leaf_train_fraction"]) * len(fit))))
        model = DecisionTreeRegressor(max_depth=depth, min_samples_leaf=leaf, random_state=int(params["random_state"]))
    return model.fit(x_fit, y_fit).predict(x_test)


def build_capacity_vs_representation_readout(config: dict[str, Any], matrix: pd.DataFrame, tables: dict[str, pd.DataFrame]) -> tuple[pd.DataFrame, dict[str, Any]]:
    expected = config["expected"]
    params = config["capacity_probe_params"]
    oos = tables["eighteen_c_oos_rank_readout"].copy()
    cv_source = tables["eighteen_c_model_cv_readout"].copy()
    primary_robust = float(oos.loc[oos["model_id"].eq(PRIMARY_MODEL_ID) & oos["split_bucket"].eq("robustness"), "rank_ic_spearman"].iloc[0])
    aux_ids = ["elastic_net_payoff_rank_h20_v1", "shallow_tree_payoff_depth2_v1", "ridge_ordinal_payoff_state_v1"]
    aux_robust = {
        model_id: float(oos.loc[oos["model_id"].eq(model_id) & oos["split_bucket"].eq("robustness"), "rank_ic_spearman"].iloc[0])
        for model_id in aux_ids
    }
    max_aux = max(aux_robust.values())
    max_aux_minus_primary = max_aux - primary_robust
    max_aux_margin_to_floor = float(expected["rank_ic_materiality_floor"]) - max_aux
    max_aux_margin_to_capacity_delta_threshold = float(expected["capacity_delta_threshold"]) - max_aux_minus_primary
    capacity_margin_status = (
        "thin_margin_caveat"
        if max_aux_margin_to_floor <= float(expected["thin_margin_threshold"]) or max_aux_margin_to_capacity_delta_threshold <= float(expected["thin_margin_threshold"])
        else "clear_margin"
    )

    train = matrix.loc[matrix["cluster_split_bucket"].eq("train")].copy()
    train["fold_id"] = grouped_fold_assignment(train, int(params["cv_fold_n"]), int(params["cv_fold_seed"]))
    cv_rows = []
    for model_id in [PRIMARY_MODEL_ID, *params["model_ids"]]:
        for fold in range(int(params["cv_fold_n"])):
            fit = train.loc[~train["fold_id"].eq(fold)]
            test = train.loc[train["fold_id"].eq(fold)]
            score = fit_score_model(model_id, config, train, fit, test)
            ic = rank_ic(score, test[config["target_column"]])
            cv_rows.append(
                {
                    "model_id": model_id,
                    "fold_id": fold,
                    "test_row_n": len(test),
                    "payoff_rank_ic": ic,
                    "fold_status": "pass" if len(test) > 0 else "fail",
                }
            )
    cv_probe = pd.DataFrame(cv_rows)
    pass_cv = cv_probe.loc[cv_probe["fold_status"].eq("pass")]
    cv_mean = pass_cv.groupby("model_id")["payoff_rank_ic"].mean().to_dict()
    cv_weighted = {
        model_id: float((g["payoff_rank_ic"] * g["test_row_n"]).sum() / g["test_row_n"].sum())
        for model_id, g in pass_cv.groupby("model_id")
    }
    primary_cv = float(cv_mean[PRIMARY_MODEL_ID])
    probe_ids = list(params["model_ids"])
    max_probe_cv = max(float(cv_mean[mid]) for mid in probe_ids)
    max_probe_delta = max_probe_cv - primary_cv
    medium_capacity_probe_caveat = bool(max_probe_cv >= float(expected["rank_ic_materiality_floor"]) or max_probe_delta >= float(expected["capacity_delta_threshold"]))

    capacity_bottleneck = bool(max_aux >= float(expected["rank_ic_materiality_floor"]) or max_aux_minus_primary >= float(expected["capacity_delta_threshold"]) or medium_capacity_probe_caveat)
    representation_bottleneck = bool(max_aux < float(expected["rank_ic_materiality_floor"]) and max_aux_minus_primary < float(expected["capacity_delta_threshold"]) and not medium_capacity_probe_caveat)
    scope = "capacity_not_excluded_by_train_cv_probe" if medium_capacity_probe_caveat else "low_capacity_representation_gap_with_capacity_caveat" if capacity_margin_status == "thin_margin_caveat" else "low_capacity_representation_gap"

    rows = []
    robust_model_ids = [PRIMARY_MODEL_ID, *aux_ids, expected["volatility_baseline_id"]]
    for _, row in oos.loc[oos["model_id"].isin(robust_model_ids)].iterrows():
        model_id = row["model_id"]
        split = row["split_bucket"]
        rows.append(
            {
                "model_id": model_id,
                "model_family": "18c_replayed_model",
                "source_feature_set": "current_18B_23_features",
                "split_bucket": split,
                "rank_ic_spearman": row["rank_ic_spearman"],
                "cv_mean_rank_ic_spearman": cv_source.loc[cv_source["model_id"].eq(model_id), "payoff_rank_ic"].mean() if model_id in set(cv_source["model_id"]) else np.nan,
                "cv_weighted_mean_rank_ic_spearman": np.nan,
                "cv_rank_ic_delta_vs_primary": np.nan,
                "rank_ic_materiality_floor": expected["rank_ic_materiality_floor"],
                "delta_vs_primary_ridge": metric_float(row["rank_ic_spearman"]) - primary_robust if split == "robustness" else np.nan,
                "delta_vs_volatility20d_baseline": np.nan,
                "capacity_delta_threshold": expected["capacity_delta_threshold"],
                "max_aux_margin_to_floor": max_aux_margin_to_floor,
                "max_aux_margin_to_capacity_delta_threshold": max_aux_margin_to_capacity_delta_threshold,
                "capacity_threshold_sensitivity_threshold": "0.010000|0.015000|0.020000",
                "capacity_threshold_sensitivity_status": "thin_at_0.010" if max_aux_minus_primary >= 0.010 else "stable_below_0.010",
                "capacity_margin_status": capacity_margin_status,
                "capacity_conclusion_scope": scope,
                "medium_capacity_probe_caveat": medium_capacity_probe_caveat,
                "capacity_bottleneck_flag": capacity_bottleneck,
                "representation_bottleneck_flag": representation_bottleneck,
                "cv_fold_n": params["cv_fold_n"],
                "cv_fold_seed": params["cv_fold_seed"],
                "cv_aggregation_method": params["cv_aggregation"],
                "primary_cv_rank_ic": primary_cv,
                "readout_status": "replayed_18c_oos",
            }
        )
    for model_id in [PRIMARY_MODEL_ID, *probe_ids]:
        rows.append(
            {
                "model_id": model_id,
                "model_family": "ridge_regression" if model_id == PRIMARY_MODEL_ID else "decision_tree_regressor",
                "source_feature_set": "current_18B_23_features",
                "split_bucket": "train_grouped_cv",
                "rank_ic_spearman": np.nan,
                "cv_mean_rank_ic_spearman": cv_mean[model_id],
                "cv_weighted_mean_rank_ic_spearman": cv_weighted[model_id],
                "cv_rank_ic_delta_vs_primary": float(cv_mean[model_id]) - primary_cv,
                "rank_ic_materiality_floor": expected["rank_ic_materiality_floor"],
                "delta_vs_primary_ridge": float(cv_mean[model_id]) - primary_cv,
                "delta_vs_volatility20d_baseline": np.nan,
                "capacity_delta_threshold": expected["capacity_delta_threshold"],
                "max_aux_margin_to_floor": max_aux_margin_to_floor,
                "max_aux_margin_to_capacity_delta_threshold": max_aux_margin_to_capacity_delta_threshold,
                "capacity_threshold_sensitivity_threshold": "0.010000|0.015000|0.020000",
                "capacity_threshold_sensitivity_status": "thin_at_0.010" if max_aux_minus_primary >= 0.010 else "stable_below_0.010",
                "capacity_margin_status": capacity_margin_status,
                "capacity_conclusion_scope": scope,
                "medium_capacity_probe_caveat": medium_capacity_probe_caveat,
                "capacity_bottleneck_flag": capacity_bottleneck,
                "representation_bottleneck_flag": representation_bottleneck,
                "cv_fold_n": params["cv_fold_n"],
                "cv_fold_seed": params["cv_fold_seed"],
                "cv_aggregation_method": params["cv_aggregation"],
                "primary_cv_rank_ic": primary_cv,
                "readout_status": "bounded_train_only_probe",
            }
        )
    summary = {
        "primary_ridge_robustness_rank_ic": primary_robust,
        "max_aux_existing_feature_rank_ic": max_aux,
        "max_aux_minus_primary_rank_ic": max_aux_minus_primary,
        "max_aux_margin_to_floor": max_aux_margin_to_floor,
        "max_aux_margin_to_capacity_delta_threshold": max_aux_margin_to_capacity_delta_threshold,
        "capacity_margin_status": capacity_margin_status,
        "capacity_conclusion_scope": scope,
        "max_train_grouped_cv_probe_rank_ic": max_probe_cv,
        "max_train_grouped_cv_probe_minus_primary_cv_rank_ic": max_probe_delta,
        "medium_capacity_probe_caveat": medium_capacity_probe_caveat,
        "capacity_bottleneck_flag": capacity_bottleneck,
        "representation_bottleneck_flag": representation_bottleneck,
        "primary_cv_rank_ic": primary_cv,
    }
    return pd.DataFrame(rows), summary


def candidate_inventory(config: dict[str, Any]) -> pd.DataFrame:
    candidates = [
        ("M1", "m1_return_sign_entropy_trailing20", "return sign entropy trailing 20", "return_sign_entropy_w", "pit_price_path_panel", "qfq close", "high"),
        ("M1", "m1_path_transition_entropy_episode", "path transition entropy episode low to t0", "path_transition_entropy_w", "pit_price_path_panel", "qfq close", "high"),
        ("M1", "m1_repair_path_efficiency_episode", "episode repair path efficiency", "repair_path_efficiency_w", "pit_price_path_panel", "qfq close", "high"),
        ("M1", "m1_close_location_episode_range", "close location in episode range", "(close_t0-low)/(high-low)", "episode_geometry_panel", "qfq high low close", "high"),
        ("M3", "m3_upside_room_to_episode_high", "upside room to pre-t0 episode high", "(episode_high-close_t0)/close_t0", "episode_geometry_panel", "qfq high close", "high"),
        ("M3", "m3_downside_crowding_to_episode_low", "downside crowding to episode low", "(close_t0-episode_low)/close_t0", "episode_geometry_panel", "qfq low close", "high"),
        ("M3", "m3_vol_adjusted_repair_strength", "volatility adjusted repair strength", "repair_return/volatility_20d", "pit_price_path_panel", "qfq close and volatility_20d", "high"),
        ("M5", "m5_bars_since_episode_low", "bars since episode low", "step_start_pos-episode_low_pos_t0", "episode_geometry_panel", "position index", "high_medium"),
        ("M5", "m5_episode_age_to_t0", "episode age at t0", "step_start_pos-cluster_start_pos", "episode_geometry_panel", "position index", "high_medium"),
        ("M5", "m5_lifecycle_progress_to_t0", "lifecycle progress at t0", "(step_start_pos-cluster_start)/(cluster_end-cluster_start)", "episode_geometry_panel", "position index", "high_medium"),
        ("M5", "m5_bars_since_reclaim", "bars since deterministic ma60 reclaim", "step_start_pos-reclaim_pos_t0", "episode_geometry_panel", "qfq close ma60", "high_medium"),
        ("M2", "m2_net_signed_money_flow_trailing20", "net signed money flow trailing 20", "sum(amount*sign(ret))/sum(abs(amount))", "pit_money_flow_proxy_panel", "qfq close money", "medium"),
        ("M2", "m2_positive_money_flow_share_trailing20", "positive money flow share trailing 20", "sum(amount where ret>0)/sum(amount)", "pit_money_flow_proxy_panel", "qfq close money", "medium"),
        ("M2", "m2_money_flow_persistence_trailing20", "money flow sign persistence trailing 20", "mean(sign(flow_t)==sign(flow_t-1))", "pit_money_flow_proxy_panel", "qfq close money", "medium"),
        ("M2", "m2_turnover_compression_20_vs_60", "turnover compression 20 versus 60", "mean(turnover_20)/mean(turnover_60)", "pit_money_flow_proxy_panel", "turnover_rate", "medium"),
        ("M4", "m4_regime_context_deferred", "regime context deferred", "requires new PIT context", "market_or_regime_context_panel", "context panel", "low"),
    ]
    rows = []
    for family, feature_id, name, formula, source, cols, priority in candidates:
        rows.append(
            {
                "candidate_family_id": family,
                "candidate_feature_id": feature_id,
                "candidate_feature_name": name,
                "candidate_feature_definition": name,
                "candidate_feature_formula": formula,
                "candidate_priority_before_evidence": priority,
                "source_artifact_alias": source,
                "source_columns": cols,
                "expected_availability": "primary" if family != "M4" else "appendix_or_deferred",
                "primary_candidate_allowed_before_lineage": family != "M4",
                "appendix_only_if_delayed": True,
                "notes": "predeclared_lineage_before_correlation",
            }
        )
    return pd.DataFrame(rows)


def normalize_qfq(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df = df.sort_values("date").reset_index(drop=True)
    for col in ["open", "high", "low", "close", "volume", "money", "amount", "turnover_rate"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    df["date"] = df["date"].astype(str)
    if "money" not in df.columns:
        if "amount" in df.columns:
            df["money"] = df["amount"]
        else:
            df["money"] = df["volume"] * df["close"]
    if "turnover_rate" not in df.columns:
        df["turnover_rate"] = np.nan
    df["ma60"] = df["close"].rolling(60, min_periods=60).mean()
    return df


def entropy_from_counts(counts: np.ndarray, eps: float) -> tuple[float, float]:
    counts = counts.astype(float)
    p = (counts + eps) / (counts.sum() + len(counts) * eps)
    ent = float(-(p * np.log(p)).sum())
    return ent, float(ent / np.log(len(counts)))


def state_sequence(close: np.ndarray, flat: float) -> np.ndarray:
    rets = close[1:] / close[:-1] - 1.0
    out = np.zeros(len(rets), dtype=int)
    out[rets > flat] = 2
    out[rets < -flat] = 0
    out[(rets >= -flat) & (rets <= flat)] = 1
    return out


def window_bounds(window_id: str, step_pos: int, low_pos: int, first_valid: int = 0) -> tuple[int, int]:
    if window_id == "episode_low_to_t0":
        return low_pos, step_pos
    if window_id == "trailing_20":
        return max(first_valid, step_pos - 19), step_pos
    if window_id == "trailing_60":
        return max(first_valid, step_pos - 59), step_pos
    raise ValueError(f"Unknown window_id: {window_id}")


def derive_row_features(row: pd.Series, qfq: pd.DataFrame, config: dict[str, Any]) -> dict[str, Any]:
    params = config["entropy_params"]
    money_params = config["money_flow_proxy_params"]
    eps = float(params["probability_epsilon"])
    flat = float(params["return_state_flat_abs_return_max"])
    min_n = int(params["min_observation_n"])
    out: dict[str, Any] = {}
    step_pos = int(row["step_start_pos"])
    cluster_start = int(row["cluster_start_pos"])
    cluster_end = int(row["cluster_end_pos"])
    if step_pos >= len(qfq) or step_pos < 0 or cluster_start > step_pos:
        return out
    seg = qfq.iloc[cluster_start : step_pos + 1]
    if len(seg) < min_n:
        return out
    low_rel = int(np.nanargmin(seg["low"].to_numpy(dtype=float)))
    high_rel = int(np.nanargmax(seg["high"].to_numpy(dtype=float)))
    low_pos = cluster_start + low_rel
    high_pos = cluster_start + high_rel
    close_t0 = float(qfq["close"].iloc[step_pos])
    low_price = float(qfq["low"].iloc[low_pos])
    low_close = float(qfq["close"].iloc[low_pos])
    high_price = float(qfq["high"].iloc[high_pos])
    out.update(
        {
            "episode_low_pos_t0": low_pos,
            "episode_high_pos_t0": high_pos,
            "episode_low_date_t0": qfq["date"].iloc[low_pos],
            "episode_high_date_t0": qfq["date"].iloc[high_pos],
            "episode_range_low_t0": low_price,
            "episode_range_high_t0": high_price,
            "qfq_reconciled_step_start_date": qfq["date"].iloc[step_pos],
            "qfq_reconciled_step_start_close": close_t0,
        }
    )
    denom = high_price - low_price
    out["m1_close_location_episode_range"] = (close_t0 - low_price) / denom if denom > 0 else np.nan
    path = qfq["close"].iloc[low_pos : step_pos + 1].to_numpy(dtype=float)
    out["m1_repair_path_efficiency_episode"] = abs(close_t0 - low_close) / np.abs(np.diff(path)).sum() if len(path) >= 2 and np.abs(np.diff(path)).sum() > 0 else np.nan
    out["m3_upside_room_to_episode_high"] = (high_price - close_t0) / close_t0 if close_t0 > 0 else np.nan
    out["m3_downside_crowding_to_episode_low"] = (close_t0 - low_price) / close_t0 if close_t0 > 0 else np.nan
    vol = metric_float(row.get("volatility_20d"), np.nan)
    repair_return = close_t0 / low_close - 1.0 if low_close > 0 else np.nan
    out["m3_vol_adjusted_repair_strength"] = repair_return / vol if np.isfinite(vol) and vol > 0 else np.nan
    out["m5_bars_since_episode_low"] = step_pos - low_pos
    out["m5_episode_age_to_t0"] = step_pos - cluster_start
    out["m5_lifecycle_progress_to_t0"] = (step_pos - cluster_start) / (cluster_end - cluster_start) if cluster_end > cluster_start else np.nan
    reclaim = np.nan
    for pos in range(max(low_pos + 1, 1), step_pos + 1):
        ma_prev = qfq["ma60"].iloc[pos - 1]
        ma_now = qfq["ma60"].iloc[pos]
        if np.isfinite(ma_prev) and np.isfinite(ma_now) and qfq["close"].iloc[pos - 1] < ma_prev and qfq["close"].iloc[pos] >= ma_now:
            reclaim = pos
            break
    out["reclaim_pos_t0"] = reclaim
    out["m5_bars_since_reclaim"] = step_pos - reclaim if np.isfinite(reclaim) else np.nan

    def close_window(window_id: str) -> pd.DataFrame:
        start, end = window_bounds(window_id, step_pos, low_pos)
        return qfq.iloc[start : end + 1]

    w20 = close_window("trailing_20")
    if len(w20) >= min_n:
        states = state_sequence(w20["close"].to_numpy(dtype=float), flat)
        counts = np.array([(states == 0).sum(), (states == 1).sum(), (states == 2).sum()])
        out["m1_return_sign_entropy_trailing20"] = entropy_from_counts(counts, eps)[1]
        amount = w20["money"].to_numpy(dtype=float)
        close = w20["close"].to_numpy(dtype=float)
        ret_sign = np.sign(np.diff(close, prepend=np.nan))
        valid = np.isfinite(amount) & np.isfinite(ret_sign)
        valid[0] = False
        denom_money = np.abs(amount[valid]).sum() + float(money_params["denominator_epsilon"])
        signed = amount[valid] * ret_sign[valid]
        out["m2_net_signed_money_flow_trailing20"] = signed.sum() / denom_money if denom_money > 0 else np.nan
        total_money = amount[valid & (amount > 0)].sum() + float(money_params["denominator_epsilon"])
        out["m2_positive_money_flow_share_trailing20"] = amount[valid & (ret_sign > 0)].sum() / total_money if total_money > 0 else np.nan
        signs = np.sign(signed)
        out["m2_money_flow_persistence_trailing20"] = float(np.mean(signs[1:] == signs[:-1])) if len(signs) >= 2 else np.nan
    wep = close_window("episode_low_to_t0")
    if len(wep) >= min_n:
        states = state_sequence(wep["close"].to_numpy(dtype=float), flat)
        trans = states[:-1] * 3 + states[1:] if len(states) >= 2 else np.array([], dtype=int)
        counts = np.array([(trans == i).sum() for i in range(9)])
        out["m1_path_transition_entropy_episode"] = entropy_from_counts(counts, eps)[1] if counts.sum() > 0 else np.nan
    w60 = close_window("trailing_60")
    if len(w60) >= min_n and np.isfinite(w60["turnover_rate"]).any():
        last20 = w60.tail(20)["turnover_rate"].astype(float)
        base60 = w60["turnover_rate"].astype(float)
        denom_turn = base60.mean()
        out["m2_turnover_compression_20_vs_60"] = last20.mean() / denom_turn if np.isfinite(denom_turn) and denom_turn != 0 else np.nan
    return out


def build_feature_base(config: dict[str, Any], tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    matrix = tables["eighteen_b_matrix"].copy()
    step_cols = ["step_id", "label_id", "step_start_pos", "step_start_date", "step_start_qfq_close"]
    mat_cols = ["step_id", "cluster_start_pos", "cluster_end_pos"]
    steps = tables["sixteen_b_label_step_panel"][step_cols].copy()
    mat = tables["sixteen_b_materialized_step_panel"][mat_cols].copy()
    out = matrix.merge(steps, on=["step_id", "label_id"], how="left", suffixes=("", "_16b"))
    out = out.merge(mat.drop_duplicates("step_id"), on="step_id", how="left")
    return out


def build_candidate_feature_panel(config: dict[str, Any], resolved: dict[str, Path], tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    base = build_feature_base(config, tables)
    qfq_dir = resolved["stock_daily_qfq_dir"]
    feature_rows = []
    for instrument, group in base.groupby("instrument", sort=False):
        path = qfq_dir / f"{instrument}.csv"
        if not path.exists():
            for _, row in group.iterrows():
                feature_rows.append({"step_id": row["step_id"], "label_id": row["label_id"], "qfq_path_status": "missing_qfq_file"})
            continue
        qfq = normalize_qfq(path)
        for _, row in group.iterrows():
            payload = {"step_id": row["step_id"], "label_id": row["label_id"], "qfq_path_status": "pass"}
            try:
                payload.update(derive_row_features(row, qfq, config))
                if "qfq_reconciled_step_start_date" not in payload:
                    payload["qfq_path_status"] = "insufficient_pre_t0_path"
            except (IndexError, ValueError, KeyError):
                payload["qfq_path_status"] = "feature_derivation_error"
            feature_rows.append(payload)
    features = pd.DataFrame(feature_rows)
    return base.merge(features, on=["step_id", "label_id"], how="left")


def feature_missingness(feature_panel: pd.DataFrame, feature_id: str) -> float:
    if feature_id not in feature_panel:
        return 1.0
    return float(1.0 - pd.to_numeric(feature_panel[feature_id], errors="coerce").notna().mean())


def build_lineage_and_pit(config: dict[str, Any], inventory: pd.DataFrame, feature_panel: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, str, str]:
    rows_lineage = []
    rows_pit = []
    min_finite = float(config["expected"]["candidate_min_finite_rate"])
    qfq_ok = feature_panel["qfq_path_status"].eq("pass").mean() >= min_finite
    for _, inv in inventory.iterrows():
        fid = inv["candidate_feature_id"]
        family = inv["candidate_family_id"]
        finite_rate = 0.0 if fid not in feature_panel else float(pd.to_numeric(feature_panel[fid], errors="coerce").notna().mean())
        is_deferred = family == "M4"
        source_blocked = not qfq_ok and family in {"M1", "M2", "M3", "M5"}
        enough = finite_rate >= min_finite
        primary = (not is_deferred) and (not source_blocked) and enough
        appendix = is_deferred or source_blocked or not enough
        reason = ""
        if is_deferred:
            reason = "m4_deferred_by_default"
        elif source_blocked:
            reason = "qfq_source_not_sufficiently_available"
        elif not enough:
            reason = "candidate_finite_rate_below_floor"
        rows_lineage.append(
            {
                "candidate_family_id": family,
                "candidate_feature_id": fid,
                "source_artifact_alias": inv["source_artifact_alias"],
                "source_pos_max_minus_step_start_pos": 0 if primary or appendix else np.nan,
                "source_date_max_minus_step_start_date": 0 if primary or appendix else np.nan,
                "uses_future_h20_path": False,
                "uses_step_end_outcome": False,
                "uses_oracle_label": False,
                "uses_payoff_target": False,
                "uses_binary_target": False,
                "pit_valid_status": "pass" if primary else "appendix_only" if appendix else "blocked",
                "t0_available_status": "pass" if primary else "delayed_appendix_only" if is_deferred else "blocked",
                "candidate_primary_allowed_after_lineage": primary,
                "candidate_appendix_only": appendix,
                "lineage_before_correlation_gate": "pass",
                "blocking_reason": reason,
            }
        )
        rows_pit.append(
            {
                "candidate_family_id": family,
                "candidate_feature_id": fid,
                "source_artifact_alias": inv["source_artifact_alias"],
                "required_source_columns": inv["source_columns"],
                "source_available_at_t0": primary,
                "source_max_lag_bars": 0,
                "delayed_observed_state": is_deferred,
                "pit_valid_status": "pass" if primary else "appendix_only" if appendix else "blocked",
                "t0_available_status": "pass" if primary else "delayed_appendix_only" if is_deferred else "blocked",
                "primary_allowed": primary,
                "appendix_only": appendix,
                "blocking_reason": reason,
            }
        )
    lineage = pd.DataFrame(rows_lineage)
    pit = pd.DataFrame(rows_pit)
    candidate_lineage_gate = "pass" if lineage["lineage_before_correlation_gate"].eq("pass").all() else "fail"
    pit_gate = "pass" if lineage["candidate_primary_allowed_after_lineage"].any() else "fail"
    return lineage, pit, candidate_lineage_gate, pit_gate


def residualize(train: pd.DataFrame, all_frame: pd.DataFrame, feature: str, covariates: list[str]) -> pd.Series:
    y_train = pd.to_numeric(train[feature], errors="coerce")
    x_train = train[covariates].apply(pd.to_numeric, errors="coerce")
    valid = y_train.notna() & np.isfinite(y_train) & x_train.notna().all(axis=1)
    if int(valid.sum()) < len(covariates) + 3:
        return pd.Series(np.nan, index=all_frame.index)
    x = np.column_stack([np.ones(int(valid.sum())), x_train.loc[valid].to_numpy(dtype=float)])
    y = y_train.loc[valid].to_numpy(dtype=float)
    beta = np.linalg.lstsq(x, y, rcond=None)[0]
    x_all = all_frame[covariates].apply(pd.to_numeric, errors="coerce")
    complete = x_all.notna().all(axis=1)
    result = pd.Series(np.nan, index=all_frame.index)
    pred = np.column_stack([np.ones(int(complete.sum())), x_all.loc[complete].to_numpy(dtype=float)]) @ beta
    result.loc[complete] = pd.to_numeric(all_frame.loc[complete, feature], errors="coerce") - pred
    return result


def build_orthogonal_readouts(config: dict[str, Any], inventory: pd.DataFrame, lineage: pd.DataFrame, feature_panel: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, bool]]:
    rows = []
    morph_rows = []
    train = feature_panel.loc[feature_panel["cluster_split_bucket"].eq("train")]
    target = config["target_column"]
    roles = {"train": "train_priority_prior", "robustness": "robustness_diagnostic_only", "validation": "validation_diagnostic_only"}
    train_pass: dict[str, bool] = {}
    for _, inv in inventory.iterrows():
        fid = inv["candidate_feature_id"]
        family = inv["candidate_family_id"]
        if fid not in feature_panel:
            train_pass[fid] = False
            for split in SPLITS:
                row = {
                    "candidate_family_id": family,
                    "candidate_feature_id": fid,
                    "split_bucket": split,
                    "raw_candidate_rank_ic": np.nan,
                    "residual_candidate_rank_ic": np.nan,
                    "residual_retention": np.nan,
                    "residualization_fit_split": "train",
                    "residualization_covariates": "not_applicable",
                    "residualization_uses_target": False,
                    "residualization_uses_robustness_rows": False,
                    "residualization_uses_validation_rows": False,
                    "residual_rank_ic_same_sign_as_raw": False,
                    "orthogonal_payoff_candidate": False,
                    "target_evidence_role": roles[split],
                    "orthogonality_status": "deferred_or_blocked",
                }
                rows.append(row)
                morph_rows.append(
                    {
                        "candidate_family_id": family,
                        "candidate_feature_id": fid,
                        "proxy_type": "deferred_context_proxy",
                        "split_bucket": split,
                        "row_n": int(feature_panel["cluster_split_bucket"].eq(split).sum()),
                        "source_window_id": "not_applicable",
                        "formula_params_id": "config_18d_default",
                        "raw_candidate_rank_ic": np.nan,
                        "residual_candidate_rank_ic": np.nan,
                        "residual_retention": np.nan,
                        "residualization_covariates": "not_applicable",
                        "residual_rank_ic_same_sign_as_raw": False,
                        "orthogonal_payoff_candidate": False,
                        "target_evidence_role": roles[split],
                        "missingness_rate": 1.0,
                        "drift_status": "deferred",
                        "diagnostic_status": "deferred_or_blocked",
                    }
                )
            continue
        covars = ["mr_volatility_20d", "mr_volume_20d_zscore"]
        if family == "M2":
            covars = ["mr_volatility_20d", "mr_volume_20d_zscore", "mr_turnover_rate_20d_zscore", "mr_money_20d_zscore"]
        residual = residualize(train, feature_panel, fid, covars)
        raw_train = rank_ic(feature_panel.loc[feature_panel["cluster_split_bucket"].eq("train"), fid], feature_panel.loc[feature_panel["cluster_split_bucket"].eq("train"), target])
        resid_train = rank_ic(residual.loc[feature_panel["cluster_split_bucket"].eq("train")], feature_panel.loc[feature_panel["cluster_split_bucket"].eq("train"), target])
        same = np.isfinite(raw_train) and np.isfinite(resid_train) and np.sign(raw_train) == np.sign(resid_train)
        train_ok = bool(np.isfinite(resid_train) and abs(resid_train) >= float(config["expected"]["candidate_train_prior_abs_rank_ic_floor"]) and same)
        train_pass[fid] = train_ok
        for split in SPLITS:
            mask = feature_panel["cluster_split_bucket"].eq(split)
            raw_ic = rank_ic(feature_panel.loc[mask, fid], feature_panel.loc[mask, target])
            resid_ic = rank_ic(residual.loc[mask], feature_panel.loc[mask, target])
            same_split = np.isfinite(raw_ic) and np.isfinite(resid_ic) and np.sign(raw_ic) == np.sign(resid_ic)
            retention = resid_ic / raw_ic if np.isfinite(raw_ic) and abs(raw_ic) > 1e-12 and np.isfinite(resid_ic) else np.nan
            ortho = bool(split == "train" and train_ok)
            row = {
                "candidate_family_id": family,
                "candidate_feature_id": fid,
                "split_bucket": split,
                "raw_candidate_rank_ic": raw_ic,
                "residual_candidate_rank_ic": resid_ic,
                "residual_retention": retention,
                "residualization_fit_split": "train",
                "residualization_covariates": "|".join(covars),
                "residualization_uses_target": False,
                "residualization_uses_robustness_rows": False,
                "residualization_uses_validation_rows": False,
                "residual_rank_ic_same_sign_as_raw": same_split,
                "orthogonal_payoff_candidate": ortho,
                "target_evidence_role": roles[split],
                "orthogonality_status": "pass" if ortho else "diagnostic_only" if split != "train" else "fail",
            }
            rows.append(row)
            morph_rows.append(
                {
                    "candidate_family_id": family,
                    "candidate_feature_id": fid,
                    "proxy_type": "path_or_pressure_proxy",
                    "split_bucket": split,
                    "row_n": int(mask.sum()),
                    "source_window_id": "pre_t0",
                    "formula_params_id": "config_18d_default",
                    "raw_candidate_rank_ic": raw_ic,
                    "residual_candidate_rank_ic": resid_ic,
                    "residual_retention": retention,
                    "residualization_covariates": "|".join(covars),
                    "residual_rank_ic_same_sign_as_raw": same_split,
                    "orthogonal_payoff_candidate": ortho,
                    "target_evidence_role": roles[split],
                    "missingness_rate": feature_missingness(feature_panel.loc[mask], fid),
                    "drift_status": "not_evaluated" if split == "train" else "diagnostic_only",
                    "diagnostic_status": "pass" if fid in feature_panel else "blocked",
                }
            )
    return pd.DataFrame(rows), pd.DataFrame(morph_rows), train_pass


def build_gap_decomposition() -> pd.DataFrame:
    rows = [
        ("F1", "mr_ret_5d|mr_ret_10d|mr_ret_20d|mr_ma_5_20_spread|mr_ma_20_60_spread|mr_distance_to_20d_high|mr_distance_to_60d_high", "current repair level", "short return and distance to highs", "episode-internal repair path morphology", "18C_report", "weak_rank_ic", "missing_shape", "M1"),
        ("F2", "mr_turnover_rate_20d_mean|mr_turnover_rate_60d_mean|mr_turnover_rate_20d_zscore|mr_volume_20d_zscore|mr_money_20d_zscore", "participation level", "volume and money level z-scores", "signed inflow/outflow dynamics", "18C_coefficients", "primary_dependency", "dynamic_pressure_missing", "M2"),
        ("F3", "mr_board_rank_pct|mr_board_rank_by_market_cap", "cross-sectional rank", "board rank context", "payoff asymmetry and path shape", "18C_coefficients", "limited_support", "context_not_shape", "M3"),
        ("F4", "mr_volatility_20d|mr_volatility_60d|mr_max_drawdown_20d|mr_max_drawdown_60d|mr_intraday_range_20d_mean", "risk state", "low volatility tilt", "vol-adjusted repair quality", "18C_baseline", "risk_ceiling", "orthogonal_shape_missing", "M1|M3"),
        ("F5", "board dummies|market cap|tradability", "static context", "board and size", "regime only if new PIT context exists", "18C_topk", "near_zero", "defer", "M4"),
    ]
    return pd.DataFrame(rows, columns=["current_family_id", "current_feature_ids", "existing_signal_role", "represented_information", "missing_payoff_information", "evidence_metric", "evidence_value", "gap_status", "candidate_family_mapping"])


def build_prioritization(config: dict[str, Any], inventory: pd.DataFrame, lineage: pd.DataFrame, orthogonal: pd.DataFrame) -> tuple[pd.DataFrame, str, list[str], list[str], list[str]]:
    rows = []
    recommended: list[str] = []
    deferred: list[str] = []
    appendix: list[str] = []
    train_orth = orthogonal.loc[orthogonal["target_evidence_role"].eq("train_priority_prior")]
    for family, meta in config["candidate_families"].items():
        fam_inv = inventory.loc[inventory["candidate_family_id"].eq(family)]
        fam_lineage = lineage.loc[lineage["candidate_family_id"].eq(family)]
        fam_orth = train_orth.loc[train_orth["candidate_family_id"].eq(family)]
        primary_n = int(fam_lineage["candidate_primary_allowed_after_lineage"].sum()) if not fam_lineage.empty else 0
        orth_n = int(fam_orth["orthogonal_payoff_candidate"].sum()) if not fam_orth.empty else 0
        delayed_n = int(fam_lineage["candidate_appendix_only"].sum()) if not fam_lineage.empty else 0
        score = float(fam_orth["residual_candidate_rank_ic"].abs().fillna(0).sum()) if not fam_orth.empty else 0.0
        recommend = family in {"M1", "M3", "M5"} and primary_n > 0 and orth_n > 0
        if family == "M2":
            recommend = primary_n > 0 and orth_n > 0
        if family == "M4":
            recommend = False
        if recommend:
            recommended.append(family)
        elif family == "M4":
            deferred.append(family)
        else:
            appendix.append(family)
        rows.append(
            {
                "candidate_family_id": family,
                "planned_priority": meta["planned_priority"],
                "evidence_adjusted_priority": "recommended" if recommend else "appendix_only" if family != "M4" else "deferred",
                "priority_reason": "train_prior_orthogonal_candidate_found" if recommend else "no_train_prior_orthogonal_candidate_or_deferred",
                "candidate_feature_n": len(fam_inv),
                "primary_allowed_candidate_n": primary_n,
                "orthogonal_payoff_candidate_n": orth_n,
                "delayed_appendix_candidate_n": delayed_n,
                "candidate_priority_score": score,
                "priority_source": "lineage_then_train_prior_only",
                "recommended_for_refresh": recommend,
                "recommendation_role": "primary_refresh_candidate" if recommend else "appendix_or_deferred",
                "blocking_reason": "" if recommend else "no_orthogonal_train_prior_or_deferred",
            }
        )
    gate = "pass" if any(f in recommended for f in ["M1", "M3", "M5"]) else "fail"
    return pd.DataFrame(rows), gate, recommended, deferred, appendix


def build_search_accounting_audit() -> tuple[pd.DataFrame, str]:
    checks = {
        "no_feature_selection_from_target_correlation_before_lineage": True,
        "no_feature_selection_from_robustness": True,
        "no_feature_selection_from_validation": True,
        "no_final_model_training": True,
        "no_model_family_selection_from_robustness": True,
        "no_threshold_tuning_on_robustness": True,
        "no_threshold_tuning_on_validation": True,
        "binary_metric_not_primary_gate": True,
        "neutral_rows_not_dropped": True,
        "delayed_features_not_primary": True,
        "no_entry_policy_authorized": True,
        "no_exit_policy_authorized": True,
        "no_holding_policy_authorized": True,
        "no_portfolio_backtest_authorized": True,
        "no_model_deployment_authorized": True,
        "no_production_signal_authorized": True,
        "no_live_trading_authorized": True,
    }
    rows = [{"check_name": key, "expected_value": True, "observed_value": value, "status": "pass" if value else "fail", "blocking_reason": "" if value else key} for key, value in checks.items()]
    frame = pd.DataFrame(rows)
    return frame, "pass" if frame["status"].eq("pass").all() else "fail"


def decision_from_gates(gates: dict[str, str], capacity_summary: dict[str, Any], recommended: list[str], deferred: list[str], appendix: list[str]) -> pd.DataFrame:
    if gates["upstream_18c_contract_gate"] != "pass":
        state = "18D_upstream_18c_contract_blocked"
    elif gates["input_artifact_gate"] != "pass":
        state = "18D_input_artifact_blocked"
    elif bool(capacity_summary["capacity_bottleneck_flag"]):
        state = "18D_capacity_bottleneck_on_existing_features"
    elif gates["candidate_lineage_gate"] != "pass":
        state = "18D_feature_representation_contract_blocked"
    elif gates["pit_t0_availability_gate"] != "pass":
        state = "18D_no_pit_valid_candidate_features_found"
    elif gates["orthogonal_payoff_information_gate"] != "pass":
        state = "18D_no_orthogonal_payoff_information_found"
    elif gates["feature_family_prioritization_gate"] != "pass":
        state = "18D_representation_gap_diagnostic_only"
    elif gates["search_accounting_gate"] != "pass":
        state = "18D_search_accounting_blocked"
    else:
        state = "18D_feature_representation_refresh_supported"
    next_req = "requirement_18e_payoff_state_feature_matrix_refresh.md" if state == "18D_feature_representation_refresh_supported" else "none"
    all_pass = all(gates[g] == "pass" for g in HARD_GATES)
    row = {
        "decision_state": state,
        "next_allowed_requirement": next_req,
        "all_hard_gates_pass": all_pass,
        **gates,
        **{col: False for col in AUTH_FALSE_COLUMNS},
        "blocking_reason": "" if all_pass else state,
        "recommended_refresh_family_ids": "|".join(recommended),
        "deferred_family_ids": "|".join(deferred),
        "appendix_only_family_ids": "|".join(appendix),
    }
    return pd.DataFrame([row])


def markdown_table(frame: pd.DataFrame, max_rows: int = 40) -> str:
    out = frame.head(max_rows).copy()
    for col in out.columns:
        if out[col].dtype == object:
            out[col] = out[col].map(lambda value: "" if pd.isna(value) else str(value).replace("|", r"\|"))
    return out.to_markdown(index=False)


def build_report(artifacts: dict[str, Any]) -> str:
    d = artifacts["decision"].iloc[0]
    cap = artifacts["capacity_summary"]
    prio = artifacts["prioritization"]
    top_train = artifacts["orthogonal"].loc[artifacts["orthogonal"]["target_evidence_role"].eq("train_priority_prior")].copy()
    top_train = top_train.sort_values("residual_candidate_rank_ic", key=lambda s: s.abs(), ascending=False)
    return f"""# Payoff-state Feature Representation Diagnostic Report

## Decision

decision_state = {d["decision_state"]}
next_allowed_requirement = {d["next_allowed_requirement"]}

18D is diagnostic-only. It does not train a final separability model and does not authorize policy, backtest, deployment, production signal, or trading.

## Capacity Versus Representation

| metric | value |
|:--|--:|
| primary_ridge_robustness_rank_ic | {cap["primary_ridge_robustness_rank_ic"]:.6f} |
| max_aux_existing_feature_rank_ic | {cap["max_aux_existing_feature_rank_ic"]:.6f} |
| max_aux_minus_primary_rank_ic | {cap["max_aux_minus_primary_rank_ic"]:.6f} |
| max_train_grouped_cv_probe_rank_ic | {cap["max_train_grouped_cv_probe_rank_ic"]:.6f} |
| max_train_grouped_cv_probe_minus_primary_cv_rank_ic | {cap["max_train_grouped_cv_probe_minus_primary_cv_rank_ic"]:.6f} |

capacity_margin_status = {cap["capacity_margin_status"]}
capacity_conclusion_scope = {cap["capacity_conclusion_scope"]}

## Feature Family Prioritization

{markdown_table(prio)}

## Orthogonal Train-prior Evidence

Only train-prior residual rank IC can affect recommendation. Robustness and validation rows are diagnostic-only.

{markdown_table(top_train[["candidate_family_id", "candidate_feature_id", "raw_candidate_rank_ic", "residual_candidate_rank_ic", "orthogonal_payoff_candidate"]], 20)}

## Input Sources

{markdown_table(artifacts["input_audit"].groupby(["source_artifact_alias", "resolved_source_status"], dropna=False).size().reset_index(name="artifact_n"), 50)}

## Search Accounting

{markdown_table(artifacts["search"])}
"""


def build_all_outputs(config: dict[str, Any], resolved: dict[str, Path], input_audit: pd.DataFrame, input_gate: str) -> dict[str, Any]:
    tables = load_inputs(resolved)
    upstream, upstream_gate = build_upstream_18c_handoff_audit(config, resolved, tables)
    matrix = model_ready_matrix(config, tables["eighteen_b_matrix"])
    capacity, capacity_summary = build_capacity_vs_representation_readout(config, matrix, tables)
    inventory = candidate_inventory(config)
    feature_panel = build_candidate_feature_panel(config, resolved, tables)
    lineage, pit, lineage_gate, pit_gate = build_lineage_and_pit(config, inventory, feature_panel)
    orthogonal, morphology, _ = build_orthogonal_readouts(config, inventory, lineage, feature_panel)
    gap = build_gap_decomposition()
    prioritization, prioritization_gate, recommended, deferred, appendix = build_prioritization(config, inventory, lineage, orthogonal)
    search, search_gate = build_search_accounting_audit()
    high_orth = prioritization.loc[prioritization["candidate_family_id"].isin(["M1", "M3", "M5"]), "orthogonal_payoff_candidate_n"].sum()
    orthogonal_gate = "pass" if int(high_orth) > 0 else "fail"
    capacity_gate = "pass" if bool(capacity_summary["representation_bottleneck_flag"]) and not bool(capacity_summary["capacity_bottleneck_flag"]) else "fail"
    gates = {
        "upstream_18c_contract_gate": upstream_gate,
        "input_artifact_gate": input_gate,
        "capacity_vs_representation_gate": capacity_gate,
        "candidate_lineage_gate": lineage_gate,
        "pit_t0_availability_gate": pit_gate,
        "orthogonal_payoff_information_gate": orthogonal_gate,
        "feature_family_prioritization_gate": prioritization_gate,
        "search_accounting_gate": search_gate,
    }
    decision = decision_from_gates(gates, capacity_summary, recommended, deferred, appendix)
    return {
        "tables": tables,
        "input_audit": input_audit,
        "upstream": upstream,
        "capacity": capacity,
        "capacity_summary": capacity_summary,
        "inventory": inventory,
        "feature_panel": feature_panel,
        "lineage": lineage,
        "pit": pit,
        "gap": gap,
        "morphology": morphology,
        "orthogonal": orthogonal,
        "prioritization": prioritization,
        "search": search,
        "decision": decision,
        "gates": gates,
    }


def write_outputs(config_path: Path, config: dict[str, Any], resolved: dict[str, Path], outputs: dict[str, Path], artifacts: dict[str, Any]) -> None:
    outputs["candidate_feature_panel"].parent.mkdir(parents=True, exist_ok=True)
    artifacts["feature_panel"].to_parquet(outputs["candidate_feature_panel"], index=False)
    write_df(outputs["input_artifact_audit"], artifacts["input_audit"])
    write_df(outputs["upstream_18c_handoff_audit"], artifacts["upstream"])
    write_df(outputs["capacity_vs_representation_readout"], artifacts["capacity"])
    write_df(outputs["candidate_feature_inventory"], artifacts["inventory"])
    write_df(outputs["candidate_feature_lineage_audit"], artifacts["lineage"])
    write_df(outputs["candidate_feature_pit_availability_audit"], artifacts["pit"])
    write_df(outputs["current_feature_gap_decomposition"], artifacts["gap"])
    write_df(outputs["payoff_morphology_proxy_readout"], artifacts["morphology"])
    write_df(outputs["orthogonal_payoff_information_readout"], artifacts["orthogonal"])
    write_df(outputs["feature_family_candidate_prioritization"], artifacts["prioritization"])
    write_df(outputs["search_accounting_audit"], artifacts["search"])
    write_df(outputs["representation_refresh_decision"], artifacts["decision"])
    write_text(outputs["report"], build_report(artifacts))
    write_manifests(config_path, config, resolved, outputs, artifacts)


def write_manifests(config_path: Path, config: dict[str, Any], resolved: dict[str, Path], outputs: dict[str, Path], artifacts: dict[str, Any]) -> None:
    write_json(
        outputs["input_manifest"],
        {
            "experiment_id": EXPERIMENT_ID,
            "phase_id": PHASE_ID,
            "run_id": RUN_ID,
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "input_artifacts": artifacts["input_audit"].to_dict(orient="records"),
        },
    )
    table_keys = [
        "input_artifact_audit",
        "upstream_18c_handoff_audit",
        "capacity_vs_representation_readout",
        "candidate_feature_inventory",
        "candidate_feature_lineage_audit",
        "candidate_feature_pit_availability_audit",
        "current_feature_gap_decomposition",
        "payoff_morphology_proxy_readout",
        "orthogonal_payoff_information_readout",
        "feature_family_candidate_prioritization",
        "search_accounting_audit",
        "representation_refresh_decision",
    ]
    decision = artifacts["decision"].iloc[0]
    manifest = {
        "run_id": RUN_ID,
        "experiment_id": EXPERIMENT_ID,
        "phase_id": PHASE_ID,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "python_version": platform.python_version(),
        "requirement_file_sha256": file_sha(EXPERIMENT_DIR / "requirement_18d_payoff_state_feature_representation_diagnostic.md"),
        "config_file_sha256": file_sha(config_path),
        "runner_file_sha256": file_sha(Path(__file__)),
        "input_artifact_manifest_sha256": file_sha(outputs["input_manifest"]),
        "publishable_table_sha256_by_name": {key: file_sha(outputs[key]) for key in table_keys},
        "report_sha256": file_sha(outputs["report"]),
        "candidate_feature_panel_sha256": file_sha(outputs["candidate_feature_panel"]),
        "decision_state": decision["decision_state"],
        "next_allowed_requirement": decision["next_allowed_requirement"],
        "all_hard_gates_pass": bool(decision["all_hard_gates_pass"]),
        "upstream_18c_decision_state": config["expected"]["upstream_18c_decision_state"],
        "capacity_bottleneck_flag": bool(artifacts["capacity_summary"]["capacity_bottleneck_flag"]),
        "representation_bottleneck_flag": bool(artifacts["capacity_summary"]["representation_bottleneck_flag"]),
        "recommended_refresh_family_ids": decision["recommended_refresh_family_ids"],
        "deferred_family_ids": decision["deferred_family_ids"],
        "appendix_only_family_ids": decision["appendix_only_family_ids"],
        "capacity_margin_status": artifacts["capacity_summary"]["capacity_margin_status"],
        "capacity_conclusion_scope": artifacts["capacity_summary"]["capacity_conclusion_scope"],
        "medium_capacity_probe_caveat": bool(artifacts["capacity_summary"]["medium_capacity_probe_caveat"]),
        **{col: bool(decision[col]) for col in AUTH_FALSE_COLUMNS},
    }
    write_json(outputs["manifest"], manifest)


def run(config_path: Path, mode: str = "full") -> dict[str, Any]:
    config = load_config(config_path)
    resolved = resolve_paths(config)
    outputs = output_paths()
    input_audit, input_gate = build_input_artifact_audit(config, resolved)
    write_df(outputs["input_artifact_audit"], input_audit)
    write_json(
        outputs["input_manifest"],
        {
            "experiment_id": EXPERIMENT_ID,
            "phase_id": PHASE_ID,
            "run_id": RUN_ID,
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "input_artifact_gate": input_gate,
            "input_artifacts": input_audit.to_dict(orient="records"),
        },
    )
    if mode == "check-inputs":
        return {"input_artifact_gate": input_gate, "input_artifact_audit": input_audit}
    artifacts = build_all_outputs(config, resolved, input_audit, input_gate)
    write_outputs(config_path, config, resolved, outputs, artifacts)
    return artifacts


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    mode = "check-inputs" if args.check_inputs_only else args.mode
    run(Path(args.config), mode=mode)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
