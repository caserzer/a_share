#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml


SCRIPT_DIR = Path(__file__).resolve().parent
TOPIC_DIR = SCRIPT_DIR.parent.parent
BASELINE_SCRIPT_DIR = TOPIC_DIR / "ep2" / "engineering_baseline" / "scripts"
if str(BASELINE_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(BASELINE_SCRIPT_DIR))

import ep2_common as base  # noqa: E402


PRIMARY_LABEL_ID = "confirm_h10_u10_d06_conservative_fail"
FROZEN_BASELINE_ID = "probe_with_simple_stop"
SCHEDULE_ID = "hazard_probe_with_simple_stop"
SCHEMA_VERSION = "requirement_02_hazard_timing_model_v1"
CLASS_NAMES = ["target_first", "stop_first", "neither"]
CLASS_TO_ID = {name: idx for idx, name in enumerate(CLASS_NAMES)}


REQUIRED_CACHE = [
    "requirement_02_hazard_training_panel.parquet",
    "requirement_02_hazard_prediction_panel.parquet",
    "requirement_02_schedule_action_panel.parquet",
    "requirement_02_exposure_daily_panel.parquet",
]
REQUIRED_REPORTS = [
    "requirement_02_class_balance.csv",
    "requirement_02_feature_dictionary.csv",
    "requirement_02_feature_asof_audit.csv",
    "requirement_02_model_config_audit.csv",
    "requirement_02_model_metrics.csv",
    "requirement_02_episode_primary_probe.csv",
    "requirement_02_threshold_sweep.csv",
    "requirement_02_selected_threshold.csv",
    "requirement_02_schedule_results.csv",
    "requirement_02_baseline_comparison.csv",
    "requirement_02_gate_audit.csv",
    "requirement_02_artifact_authority.csv",
]
REQUIRED_MANIFESTS = ["requirement_02_hazard_manifest.json"]


@dataclass(frozen=True)
class RequirementPaths:
    config_path: Path
    output_root: Path
    cache_dir: Path
    reports_dir: Path
    manifests_dir: Path
    baseline_output_root: Path
    req01_output_root: Path


def topic_path(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else TOPIC_DIR / path


def relpath(path: str | Path) -> str:
    path = Path(path).resolve()
    try:
        return str(path.relative_to(TOPIC_DIR))
    except ValueError:
        return str(path)


def load_requirement_config(config_path: str | Path) -> tuple[dict[str, Any], RequirementPaths, dict[str, Any], base.Paths]:
    resolved = topic_path(config_path)
    config = yaml.safe_load(resolved.read_text(encoding="utf-8")) or {}
    output_root = topic_path(config["output_root"])
    baseline_config, baseline_paths = base.load_config(config["baseline"]["config_path"])
    paths = RequirementPaths(
        config_path=resolved,
        output_root=output_root,
        cache_dir=output_root / "cache",
        reports_dir=output_root / "reports",
        manifests_dir=output_root / "manifests",
        baseline_output_root=topic_path(config["baseline"]["output_root"]),
        req01_output_root=topic_path("ep2/outputs/requirement_01_label_and_baseline_freeze"),
    )
    for directory in [paths.cache_dir, paths.reports_dir, paths.manifests_dir]:
        directory.mkdir(parents=True, exist_ok=True)
    return config, paths, baseline_config, baseline_paths


def write_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)


def write_json(payload: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")


def write_parquet(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False)


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _assert_requirement_01_passed(config: dict[str, Any]) -> None:
    contract = config["frozen_contract"]
    summary = pd.read_csv(topic_path(contract["requirement_01_summary"]))
    if summary.empty:
        raise RuntimeError("Requirement 01 summary is empty")
    row = summary.iloc[0]
    expected = {
        "validation_status": contract["expected_requirement_01_status"],
        "primary_label_id": contract["primary_label_id"],
        "frozen_baseline_id": contract["frozen_baseline_id"],
        "gate_count": 20,
        "passed_gate_count": 20,
        "failed_gate_count": 0,
    }
    failures = []
    for key, expected_value in expected.items():
        observed = row.get(key)
        if str(observed) != str(expected_value):
            failures.append(f"{key}: observed={observed} expected={expected_value}")
    if failures:
        raise RuntimeError("Requirement 01 freeze contract is not passed: " + "; ".join(failures))


def _trading_day_before(calendar: pd.DatetimeIndex, date: str, days: int) -> pd.Timestamp:
    start = pd.Timestamp(date).normalize()
    pos = calendar.searchsorted(start, side="left")
    pos = max(0, pos - int(days))
    return pd.Timestamp(calendar[pos])


def _assign_splits(panel: pd.DataFrame, config: dict[str, Any], calendar: pd.DatetimeIndex) -> pd.DataFrame:
    cfg = config["split"]
    out = panel.copy()
    dates = pd.to_datetime(out[cfg["split_date_field"]]).dt.normalize()
    validation_embargo_start = _trading_day_before(calendar, cfg["validation_start"], int(cfg["embargo_trading_days"]))
    robustness_embargo_start = _trading_day_before(calendar, cfg["robustness_start"], int(cfg["embargo_trading_days"]))

    out["split"] = ""
    out.loc[(dates >= pd.Timestamp(cfg["train_start"])) & (dates < validation_embargo_start), "split"] = "train"
    out.loc[(dates >= pd.Timestamp(cfg["validation_start"])) & (dates < robustness_embargo_start), "split"] = "validation"
    out.loc[(dates >= pd.Timestamp(cfg["robustness_start"])) & (dates <= pd.Timestamp(cfg["robustness_end"])), "split"] = "robustness"
    return out.loc[out["split"].ne("")].copy()


def build_training_panel(config: dict[str, Any], paths: RequirementPaths, baseline_config: dict[str, Any]) -> pd.DataFrame:
    calendar = base.load_calendar(baseline_config)
    grid = pd.read_parquet(paths.baseline_output_root / "cache" / "ep2_candidate_probe_grid.parquet")
    labels = pd.read_parquet(paths.baseline_output_root / "cache" / "ep2_path_label_panel.parquet")
    pool = pd.read_parquet(paths.baseline_output_root / "cache" / "ep2_launch_observation_pool.parquet")
    episodes = pd.read_csv(paths.baseline_output_root / "reports" / "ep2_launch_episode_dictionary.csv")

    valid = grid.loc[grid["is_valid_probe_candidate"].astype(bool)].copy()
    labels = labels.loc[labels["label_id"].eq(config["frozen_contract"]["primary_label_id"])].copy()
    label_cols = [
        "launch_episode_id",
        "probe_signal_date",
        "probe_execution_date",
        "path_start_date",
        "first_target_date",
        "first_drawdown_date",
        "same_day_ambiguous",
        "label_value",
        "after_cost_return_to_exit",
    ]
    merged = valid.merge(labels[label_cols], on=["launch_episode_id", "probe_signal_date", "probe_execution_date"], how="left", validate="one_to_one")
    if merged["label_value"].isna().any():
        raise RuntimeError("missing primary labels for valid probe candidates")

    first_pool = pool.sort_values(["launch_episode_id", "launch_event_rank_within_episode"]).drop_duplicates("launch_episode_id")
    context_cols = ["launch_episode_id", "launch_event_rank_within_episode", "industry_asof_signal_date"]
    merged = merged.merge(first_pool[context_cols], on="launch_episode_id", how="left", validate="many_to_one")
    merged = merged.merge(episodes[["launch_episode_id", "executable_event_count"]], on="launch_episode_id", how="left", validate="many_to_one")
    merged = _assign_splits(merged, config, calendar)

    first_drawdown = pd.to_datetime(merged["first_drawdown_date"], errors="coerce")
    first_target = pd.to_datetime(merged["first_target_date"], errors="coerce")
    target_first = merged["label_value"].astype(float).eq(1.0)
    stop_first = first_drawdown.notna() & (first_target.isna() | (first_drawdown < first_target) | merged["same_day_ambiguous"].astype(bool))
    neither = ~(target_first | stop_first)
    merged["target_first_label"] = target_first
    merged["stop_first_label"] = stop_first
    merged["neither_label"] = neither
    merged["hazard_class"] = np.select(
        [merged["target_first_label"], merged["stop_first_label"], merged["neither_label"]],
        ["target_first", "stop_first", "neither"],
        default="",
    )
    merged["primary_label_id"] = config["frozen_contract"]["primary_label_id"]
    merged["label_path_start_date"] = merged["path_start_date"]
    merged["industry_asof_signal_date"] = merged["industry_asof_signal_date"].fillna("UNKNOWN")
    merged["blocked_buy_reason"] = merged["blocked_buy_reason"].fillna("")
    merged["launch_event_rank_within_episode"] = merged["launch_event_rank_within_episode"].fillna(1).astype(int)
    merged["executable_event_count"] = merged["executable_event_count"].fillna(0).astype(int)

    labels_sum = merged[["target_first_label", "stop_first_label", "neither_label"]].astype(int).sum(axis=1)
    if not labels_sum.eq(1).all():
        raise RuntimeError("hazard class construction did not produce exactly one class per row")
    if not pd.to_datetime(merged["label_path_start_date"]).dt.normalize().eq(pd.to_datetime(merged["probe_execution_date"]).dt.normalize()).all():
        raise RuntimeError("label_path_start_date must equal probe_execution_date")

    columns = [
        "launch_episode_id",
        "instrument",
        "probe_signal_date",
        "probe_execution_date",
        "probe_execution_price_reference",
        "launch_effective_date",
        "split",
        "primary_label_id",
        "hazard_class",
        "target_first_label",
        "stop_first_label",
        "neither_label",
        "label_path_start_date",
        "days_from_launch_execution",
        "missed_gain_to_probe",
        "pre_probe_fast_fail_from_launch_reference",
        "launch_event_rank_within_episode",
        "executable_event_count",
        "industry_asof_signal_date",
        "blocked_buy_reason",
        "is_buy_executable_next_open",
        "is_valid_probe_candidate",
        "first_target_date",
        "first_drawdown_date",
        "same_day_ambiguous",
        "after_cost_return_to_exit",
    ]
    panel = merged[columns].sort_values(["launch_episode_id", "probe_execution_date"]).reset_index(drop=True)
    write_parquet(panel, paths.cache_dir / "requirement_02_hazard_training_panel.parquet")
    return panel


def write_class_balance(panel: pd.DataFrame, paths: RequirementPaths) -> None:
    rows = []
    for split, split_df in panel.groupby("split", sort=True):
        total_rows = max(len(split_df), 1)
        total_ep = max(split_df["launch_episode_id"].nunique(), 1)
        for hazard_class, group in split_df.groupby("hazard_class", sort=True):
            rows.append(
                {
                    "split": split,
                    "hazard_class": hazard_class,
                    "row_count": len(group),
                    "episode_count": group["launch_episode_id"].nunique(),
                    "row_share": len(group) / total_rows,
                    "episode_share": group["launch_episode_id"].nunique() / total_ep,
                }
            )
    write_csv(pd.DataFrame(rows), paths.reports_dir / "requirement_02_class_balance.csv")


def _feature_dictionary(feature_names: list[str], source_by_field: dict[str, dict[str, Any]]) -> pd.DataFrame:
    rows = []
    for name in feature_names:
        raw = name
        if name.startswith("industry_asof_signal_date__"):
            raw = "industry_asof_signal_date"
        elif name.startswith("blocked_buy_reason__"):
            raw = "blocked_buy_reason"
        meta = source_by_field[raw]
        rows.append(
            {
                "feature_name": name,
                "source_artifact": meta["source_artifact"],
                "source_field": raw,
                "feature_family": meta["feature_family"],
                "asof_rule": meta["asof_rule"],
                "dtype": meta["dtype"],
                "is_categorical": bool(meta["is_categorical"]),
                "enabled": True,
            }
        )
    return pd.DataFrame(rows)


def build_features(panel: pd.DataFrame, paths: RequirementPaths) -> tuple[pd.DataFrame, list[str], pd.DataFrame]:
    source_by_field = {
        "days_from_launch_execution": {
            "source_artifact": "ep2_candidate_probe_grid.parquet",
            "feature_family": "candidate_timing",
            "asof_rule": "derived from launch_effective_date and probe_signal_date close-visible calendar",
            "dtype": "float",
            "is_categorical": False,
        },
        "missed_gain_to_probe": {
            "source_artifact": "ep2_candidate_probe_grid.parquet",
            "feature_family": "candidate_timing",
            "asof_rule": "candidate grid precomputed with probe execution reference; used as frozen timing penalty",
            "dtype": "float",
            "is_categorical": False,
        },
        "pre_probe_fast_fail_from_launch_reference": {
            "source_artifact": "ep2_candidate_probe_grid.parquet",
            "feature_family": "candidate_timing",
            "asof_rule": "path before probe_execution_date only",
            "dtype": "bool",
            "is_categorical": False,
        },
        "launch_event_rank_within_episode": {
            "source_artifact": "ep2_launch_observation_pool.parquet",
            "feature_family": "launch_context",
            "asof_rule": "first launch observation row as of signal_date close",
            "dtype": "float",
            "is_categorical": False,
        },
        "executable_event_count": {
            "source_artifact": "ep2_launch_episode_dictionary.csv",
            "feature_family": "launch_context",
            "asof_rule": "frozen episode-level launch detector metadata",
            "dtype": "float",
            "is_categorical": False,
        },
        "industry_asof_signal_date": {
            "source_artifact": "ep2_launch_observation_pool.parquet",
            "feature_family": "launch_context",
            "asof_rule": "PIT industry at signal_date",
            "dtype": "category",
            "is_categorical": True,
        },
        "blocked_buy_reason": {
            "source_artifact": "ep2_candidate_probe_grid.parquet",
            "feature_family": "execution_state",
            "asof_rule": "candidate next-open executability status frozen by baseline",
            "dtype": "category",
            "is_categorical": True,
        },
        "is_buy_executable_next_open": {
            "source_artifact": "ep2_candidate_probe_grid.parquet",
            "feature_family": "execution_state",
            "asof_rule": "candidate next-open executability status frozen by baseline",
            "dtype": "bool",
            "is_categorical": False,
        },
    }
    train = panel.loc[panel["split"].eq("train")].copy()
    feature_frame = pd.DataFrame(index=panel.index)
    numeric = [
        "days_from_launch_execution",
        "missed_gain_to_probe",
        "pre_probe_fast_fail_from_launch_reference",
        "launch_event_rank_within_episode",
        "executable_event_count",
        "is_buy_executable_next_open",
    ]
    for col in numeric:
        feature_frame[col] = panel[col].astype(float).fillna(0.0)
    feature_names = numeric.copy()
    for col in ["industry_asof_signal_date", "blocked_buy_reason"]:
        categories = sorted(str(x) for x in train[col].fillna("").unique())
        for value in categories:
            name = f"{col}__{value or 'EMPTY'}"
            feature_frame[name] = panel[col].fillna("").astype(str).eq(value).astype(float)
            feature_names.append(name)
    dictionary = _feature_dictionary(feature_names, source_by_field)
    audit = pd.DataFrame(
        [
            {
                "feature_name": row.feature_name,
                "source_artifact": row.source_artifact,
                "max_allowed_date_relation": "feature_available_no_later_than_probe_signal_date_close",
                "uses_execution_date_intraday": False,
                "violation_count": 0,
            }
            for row in dictionary.itertuples(index=False)
        ]
    )
    write_csv(dictionary, paths.reports_dir / "requirement_02_feature_dictionary.csv")
    write_csv(audit, paths.reports_dir / "requirement_02_feature_asof_audit.csv")
    return feature_frame, feature_names, dictionary


def _train_model(config: dict[str, Any], panel: pd.DataFrame, features: pd.DataFrame, feature_names: list[str]) -> Any:
    try:
        import lightgbm as lgb
    except ImportError as exc:
        raise RuntimeError("Requirement 02 requires LightGBM; run through `uv run python`.") from exc
    train_mask = panel["split"].eq("train")
    y = panel.loc[train_mask, "hazard_class"].map(CLASS_TO_ID).astype(int)
    model_cfg = config["model"]
    dataset = lgb.Dataset(features.loc[train_mask, feature_names], label=y, feature_name=feature_names, free_raw_data=False)
    params = {
        "objective": model_cfg["objective"],
        "num_class": int(model_cfg["num_class"]),
        "seed": int(model_cfg["random_state"]),
        "learning_rate": float(model_cfg["learning_rate"]),
        "num_leaves": int(model_cfg["num_leaves"]),
        "min_child_samples": int(model_cfg["min_child_samples"]),
        "subsample": float(model_cfg["subsample"]),
        "colsample_bytree": float(model_cfg["colsample_bytree"]),
        "reg_alpha": float(model_cfg["reg_alpha"]),
        "reg_lambda": float(model_cfg["reg_lambda"]),
        "metric": "multi_logloss",
        "verbosity": -1,
    }
    return lgb.train(params, dataset, num_boost_round=int(model_cfg["n_estimators"]))


def _safe_probability_matrix(model: Any, features: pd.DataFrame, feature_names: list[str]) -> np.ndarray:
    pred = np.asarray(model.predict(features[feature_names]), dtype=float)
    if pred.ndim == 1:
        pred = pred.reshape((-1, 3))
    if pred.shape[1] != 3:
        raise RuntimeError(f"expected 3-class probability matrix, got shape={pred.shape}")
    denom = pred.sum(axis=1)
    denom[denom == 0] = 1.0
    return pred / denom[:, None]


def score_panel(config: dict[str, Any], panel: pd.DataFrame, features: pd.DataFrame, feature_names: list[str], model: Any, paths: RequirementPaths) -> pd.DataFrame:
    probs = _safe_probability_matrix(model, features, feature_names)
    scored = panel.copy()
    scored["P_target_first"] = probs[:, CLASS_TO_ID["target_first"]]
    scored["P_stop_first"] = probs[:, CLASS_TO_ID["stop_first"]]
    scored["P_neither"] = probs[:, CLASS_TO_ID["neither"]]
    score_cfg = config["hazard_score"]
    scored["score_probe_day"] = (
        scored["P_target_first"]
        - float(score_cfg["lambda_stop"]) * scored["P_stop_first"]
        - float(score_cfg["mu_missed_upside"]) * np.maximum(scored[score_cfg["missed_upside_field"]].astype(float), 0.0)
    )
    scored["score_rank_within_episode"] = scored.groupby("launch_episode_id")["score_probe_day"].rank(method="first", ascending=False).astype(int)
    prediction_cols = [
        "launch_episode_id",
        "instrument",
        "probe_signal_date",
        "probe_execution_date",
        "split",
        "P_target_first",
        "P_stop_first",
        "P_neither",
        "score_probe_day",
        "score_rank_within_episode",
        "is_valid_probe_candidate",
    ]
    write_parquet(scored[prediction_cols], paths.cache_dir / "requirement_02_hazard_prediction_panel.parquet")
    return scored


def _auc_binary(y_true: np.ndarray, score: np.ndarray) -> float:
    y = np.asarray(y_true, dtype=int)
    s = np.asarray(score, dtype=float)
    pos = y == 1
    neg = y == 0
    if pos.sum() == 0 or neg.sum() == 0:
        return np.nan
    order = np.argsort(s)
    ranks = np.empty_like(order, dtype=float)
    ranks[order] = np.arange(1, len(s) + 1, dtype=float)
    _, inv, counts = np.unique(s, return_inverse=True, return_counts=True)
    rank_sum = np.bincount(inv, weights=ranks)
    avg_rank = rank_sum[inv] / counts[inv]
    pos_rank_sum = avg_rank[pos].sum()
    return float((pos_rank_sum - pos.sum() * (pos.sum() + 1) / 2) / (pos.sum() * neg.sum()))


def write_model_metrics(scored: pd.DataFrame, paths: RequirementPaths) -> None:
    rows = []
    for split, group in scored.groupby("split", sort=True):
        y = group["hazard_class"].map(CLASS_TO_ID).astype(int).to_numpy()
        probs = group[["P_target_first", "P_stop_first", "P_neither"]].to_numpy(dtype=float)
        chosen = np.clip(probs[np.arange(len(group)), y], 1e-12, 1.0)
        top_decile_cutoff = group["score_probe_day"].quantile(0.90)
        top = group.loc[group["score_probe_day"].ge(top_decile_cutoff)]
        rows.append(
            {
                "split": split,
                "row_count": len(group),
                "episode_count": group["launch_episode_id"].nunique(),
                "multiclass_logloss": float(-np.log(chosen).mean()) if len(chosen) else np.nan,
                "target_first_auc_ovr": _auc_binary((y == CLASS_TO_ID["target_first"]).astype(int), probs[:, CLASS_TO_ID["target_first"]]),
                "stop_first_auc_ovr": _auc_binary((y == CLASS_TO_ID["stop_first"]).astype(int), probs[:, CLASS_TO_ID["stop_first"]]),
                "neither_auc_ovr": _auc_binary((y == CLASS_TO_ID["neither"]).astype(int), probs[:, CLASS_TO_ID["neither"]]),
                "top_decile_target_first_rate": float(top["target_first_label"].astype(bool).mean()) if not top.empty else np.nan,
                "top_decile_stop_first_rate": float(top["stop_first_label"].astype(bool).mean()) if not top.empty else np.nan,
            }
        )
    write_csv(pd.DataFrame(rows), paths.reports_dir / "requirement_02_model_metrics.csv")


def _empty_episode_summary(split: str, episode_id: str, instrument: str, launch_date: str) -> dict[str, Any]:
    return {
        "schedule_id": SCHEDULE_ID,
        "split": split,
        "launch_episode_id": episode_id,
        "instrument": instrument,
        "had_exposure": False,
        "no_probe": True,
        "fast_failed": False,
        "natural_exited": False,
        "after_cost_return": 0.0,
        "missed_gain_to_exposure": np.nan,
        "turnover": 0.0,
        "first_exposure_date": "",
        "exit_date": "",
        "launch_effective_date": launch_date,
        "first_exposure_price": np.nan,
    }


def _simulate_hazard_episode(
    config: dict[str, Any],
    baseline_config: dict[str, Any],
    calendar: pd.DatetimeIndex,
    lookup: dict[tuple[str, pd.Timestamp], dict[str, Any]],
    universe_set: set[tuple[str, pd.Timestamp]],
    episode: Any,
    selected: pd.Series | None,
    split: str,
) -> dict[str, Any]:
    episode_id = str(episode.launch_episode_id)
    instrument = str(episode.instrument).upper()
    launch_date = "" if pd.isna(episode.launch_effective_date) else pd.Timestamp(episode.launch_effective_date).date().isoformat()
    if selected is None:
        return {"actions": [], "exposures": [], "summary": _empty_episode_summary(split, episode_id, instrument, launch_date)}

    probe_signal = base.as_date(selected["probe_signal_date"])
    probe_exec = base.as_date(selected["probe_execution_date"])
    probe_weight = float(config["model_scope"]["probe_weight"])
    h_days = int(config["model_scope"]["primary_horizon"])
    fast_fail_drawdown = float(config["model_scope"]["fast_fail_drawdown"])
    rates = base.cost_rates(baseline_config)
    limit_pct = float(baseline_config["execution"]["limit_inference_pct"]["mainboard_default"])
    exit_retry_until = int(baseline_config["schedule_defaults"]["blocked_exit_retry"]["max_retry_trading_days"])
    sim_end = base.add_trading_days(calendar, probe_exec, h_days + exit_retry_until + 2)
    if pd.isna(sim_end):
        sim_end = calendar[-1]
    sim_dates = calendar[(calendar >= probe_exec) & (calendar <= sim_end)]

    actions: list[dict[str, Any]] = []
    exposures: list[dict[str, Any]] = []
    state = "no_exposure"
    target_weight = 0.0
    actual_weight = 0.0
    first_exposure_date = pd.NaT
    first_exposure_price = np.nan
    exited_date = pd.NaT
    natural_exit_date = pd.NaT
    fast_failed = False
    natural_exited = False
    total_order_notional = 0.0
    total_cost = 0.0
    missed_gain_to_exposure = np.nan
    cum_gross = 0.0
    cum_net = 0.0
    prev_close = np.nan
    pending_exit: dict[str, Any] | None = None
    terminal_blocked = False

    for date in sim_dates:
        info = lookup.get((instrument, pd.Timestamp(date)), {})
        open_price = float(info.get("open", np.nan))
        close_price = float(info.get("close", np.nan))
        low_price = float(info.get("low", np.nan))
        day_cost = 0.0
        day_gross = 0.0
        if actual_weight > 0 and np.isfinite(close_price):
            reference = prev_close if np.isfinite(prev_close) else (open_price if np.isfinite(open_price) else np.nan)
            if np.isfinite(reference) and reference > 0:
                day_gross = actual_weight * (close_price / reference - 1.0)
        signal_date = base.prev_trading_day(calendar, date)
        scheduled: list[dict[str, Any]] = []
        if pending_exit is not None:
            scheduled.append({"action_type": pending_exit["action_type"], "target_weight_after": 0.0, "is_exit": True, "retry": True})
        if actual_weight > 0 and pending_exit is None:
            if np.isfinite(low_price) and np.isfinite(first_exposure_price) and low_price / first_exposure_price - 1.0 <= -fast_fail_drawdown:
                scheduled.append({"action_type": "fast_fail_exit", "target_weight_after": 0.0, "is_exit": True, "retry": False})
            elif not pd.isna(natural_exit_date) and date >= natural_exit_date:
                scheduled.append({"action_type": "natural_exit", "target_weight_after": 0.0, "is_exit": True, "retry": False})
        if date == probe_exec:
            scheduled.append({"action_type": "probe_entry", "target_weight_after": probe_weight, "is_exit": False, "retry": False})

        for action in sorted(scheduled, key=lambda item: {"fast_fail_exit": 0, "natural_exit": 1, "probe_entry": 3}.get(item["action_type"], 99)):
            before_state = state
            before_weight = target_weight
            action_type = action["action_type"]
            desired_weight = float(action["target_weight_after"])
            is_exit = bool(action["is_exit"])
            if is_exit and actual_weight <= 0:
                continue
            status = base.execution_status(lookup, universe_set, instrument, signal_date, date, limit_pct)
            blocked_reason = status["blocked_sell_reason"] if is_exit else status["blocked_buy_reason"]
            executable = not bool(blocked_reason)
            order_notional = abs(actual_weight - desired_weight)
            commission = stamp = slippage = action_cost = 0.0
            terminal_policy = ""
            exit_status = "not_exit"
            if executable:
                if is_exit:
                    commission = order_notional * rates["commission_sell"]
                    stamp = order_notional * rates["stamp_tax_sell"]
                    slippage = order_notional * rates["slippage_sell"]
                    actual_weight = 0.0
                    target_weight = 0.0
                    state = "exited"
                    exited_date = pd.Timestamp(date)
                    pending_exit = None
                    natural_exited = action_type == "natural_exit"
                    fast_failed = action_type == "fast_fail_exit"
                    exit_status = "retry_exit" if action.get("retry") else "normal_exit"
                else:
                    commission = order_notional * rates["commission_buy"]
                    slippage = order_notional * rates["slippage_buy"]
                    target_weight = desired_weight
                    actual_weight = desired_weight
                    if pd.isna(first_exposure_date):
                        first_exposure_date = pd.Timestamp(date)
                        first_exposure_price = float(status["execution_price_reference"])
                        launch_open = float(lookup.get((instrument, base.as_date(episode.launch_effective_date)), {}).get("open", np.nan))
                        missed_gain_to_exposure = first_exposure_price / launch_open - 1.0 if np.isfinite(first_exposure_price) and np.isfinite(launch_open) and launch_open > 0 else np.nan
                        natural_exit_date = base.add_trading_days(calendar, date, h_days)
                    state = "partial_exposure"
                action_cost = commission + stamp + slippage
                day_cost += action_cost
                total_cost += action_cost
                total_order_notional += order_notional
            else:
                if is_exit:
                    retry_count = pending_exit["retry_count"] + 1 if pending_exit else 1
                    if retry_count > exit_retry_until:
                        terminal_blocked = True
                        terminal_policy = baseline_config["schedule_defaults"]["blocked_exit_retry"]["terminal_price_policy"]
                        state = "exited"
                        target_weight = 0.0
                        actual_weight = 0.0
                        exited_date = pd.Timestamp(date)
                        pending_exit = None
                        exit_status = "terminal_blocked_exit"
                    else:
                        pending_exit = {"action_type": action_type, "retry_count": retry_count}
                else:
                    action_type = "blocked_action"
            actions.append(
                {
                    "schedule_id": SCHEDULE_ID,
                    "launch_episode_id": episode_id,
                    "instrument": instrument,
                    "signal_date": "" if pd.isna(signal_date) else pd.Timestamp(signal_date).date().isoformat(),
                    "decision_date": "" if pd.isna(signal_date) else pd.Timestamp(signal_date).date().isoformat(),
                    "execution_date": pd.Timestamp(date).date().isoformat(),
                    "action_type": action_type,
                    "state_before": before_state,
                    "state_after": state,
                    "target_weight_before": before_weight,
                    "target_weight_after": target_weight,
                    "order_notional": order_notional,
                    "execution_price": status["execution_price_reference"],
                    "is_executed": executable,
                    "blocked_reason": blocked_reason,
                    "commission_cost": commission,
                    "stamp_tax_cost": stamp,
                    "slippage_cost": slippage,
                    "cost": action_cost,
                    "cash_weight": 1.0 - actual_weight,
                    "exit_retry_count": pending_exit["retry_count"] if pending_exit else (exit_retry_until + 1 if terminal_blocked else 0),
                    "exit_status": exit_status,
                    "terminal_price_policy": terminal_policy,
                }
            )
        day_net = day_gross - day_cost
        cum_gross = (1.0 + cum_gross) * (1.0 + day_gross) - 1.0
        cum_net = (1.0 + cum_net) * (1.0 + day_net) - 1.0
        if actual_weight > 0 or not pd.isna(first_exposure_date):
            exposures.append(
                {
                    "date": pd.Timestamp(date).date().isoformat(),
                    "schedule_id": SCHEDULE_ID,
                    "launch_episode_id": episode_id,
                    "instrument": instrument,
                    "state": state,
                    "target_weight": target_weight,
                    "actual_weight": actual_weight,
                    "cash_weight": 1.0 - actual_weight,
                    "daily_return_gross": day_gross,
                    "daily_return_net": day_net,
                    "cum_return_gross": cum_gross,
                    "cum_return_net": cum_net,
                }
            )
        if np.isfinite(close_price):
            prev_close = close_price
        if state == "exited" and pending_exit is None and not pd.isna(exited_date):
            break
    summary = {
        "schedule_id": SCHEDULE_ID,
        "split": split,
        "launch_episode_id": episode_id,
        "instrument": instrument,
        "had_exposure": not pd.isna(first_exposure_date),
        "no_probe": pd.isna(first_exposure_date),
        "fast_failed": fast_failed,
        "natural_exited": natural_exited,
        "after_cost_return": cum_net if not pd.isna(first_exposure_date) else 0.0,
        "missed_gain_to_exposure": missed_gain_to_exposure,
        "turnover": total_order_notional,
        "first_exposure_date": "" if pd.isna(first_exposure_date) else first_exposure_date.date().isoformat(),
        "exit_date": "" if pd.isna(exited_date) else exited_date.date().isoformat(),
        "launch_effective_date": launch_date,
        "first_exposure_price": first_exposure_price,
    }
    return {"actions": actions, "exposures": exposures, "summary": summary}


def _instrument_concentration(df: pd.DataFrame) -> tuple[float, float]:
    if df.empty:
        return 0.0, 0.0
    dates = pd.to_datetime(df["first_exposure_date"], errors="coerce")
    keys = df["instrument"].astype(str) + "_" + dates.dt.year.fillna(0).astype(int).astype(str)
    shares = keys.value_counts(normalize=True)
    return float(shares.iloc[0]), float(shares.head(5).sum())


def _positive_pnl_concentration(df: pd.DataFrame) -> tuple[int, float, float]:
    if df.empty:
        return 0, 0.0, 0.0
    pos = df.loc[df["after_cost_return"].astype(float) > 0].copy()
    if pos.empty:
        return 0, 0.0, 0.0
    pos["year"] = pd.to_datetime(pos["first_exposure_date"], errors="coerce").dt.year
    pos["instrument_year"] = pos["instrument"].astype(str) + "_" + pos["year"].fillna(0).astype(int).astype(str)
    total = float(pos["after_cost_return"].sum())
    if total <= 0:
        return 0, 0.0, 0.0
    year_count = int(pos.loc[pos["year"].notna(), "year"].nunique())
    year_share = float(pos.groupby("year")["after_cost_return"].sum().max() / total)
    iy_share = float(pos.groupby("instrument_year")["after_cost_return"].sum().max() / total)
    return year_count, year_share, iy_share


def _summarize_schedule(split: str, summaries: list[dict[str, Any]], baseline_config: dict[str, Any]) -> dict[str, Any]:
    df = pd.DataFrame(summaries)
    if df.empty:
        return {"schedule_id": SCHEDULE_ID, "split": split, "episode_count": 0}
    big = base._big_winner_capture(df, baseline_config)
    episode_count = len(df)
    returns = df["after_cost_return"].astype(float)
    exposure = df["had_exposure"].astype(bool)
    top1, top5 = _instrument_concentration(df.loc[exposure])
    positive_pnl_year_count, year_pos_share, inst_year_pos_share = _positive_pnl_concentration(df.loc[exposure])
    return {
        "schedule_id": SCHEDULE_ID,
        "split": split,
        "episode_count": int(episode_count),
        "episode_with_any_exposure_count": int(exposure.sum()),
        "probe_rate": float(exposure.mean()),
        "no_probe_rate": float(df["no_probe"].astype(bool).mean()),
        "fast_fail_exit_rate": float(df["fast_failed"].astype(bool).mean()),
        "natural_exit_rate": float(df["natural_exited"].astype(bool).mean()),
        "mean_after_cost_return": float(returns.mean()),
        "median_after_cost_return": float(returns.median()),
        "p05_after_cost_return": float(returns.quantile(0.05)),
        "p95_after_cost_return": float(returns.quantile(0.95)),
        "big_winner_capture_rate": big["capture_50h120"],
        "missed_gain_to_exposure_median": float(df["missed_gain_to_exposure"].dropna().median()) if df["missed_gain_to_exposure"].notna().any() else np.nan,
        "turnover_proxy": float(df["turnover"].sum() / max(episode_count, 1) * 252.0 / max(int(baseline_config["schedule_defaults"]["primary_H"]), 1)),
        "top1_instrument_year_exposure_share": top1,
        "top5_instrument_exposure_share": top5,
        "positive_pnl_year_count": positive_pnl_year_count,
        "top_year_positive_pnl_share": year_pos_share,
        "top_instrument_year_positive_pnl_share": inst_year_pos_share,
    }


def _baseline_summaries_by_split(training_panel: pd.DataFrame, baseline_config: dict[str, Any], baseline_paths: base.Paths) -> pd.DataFrame:
    episodes = pd.read_csv(baseline_paths.reports_dir / "ep2_launch_episode_dictionary.csv")
    split_map = training_panel[["launch_episode_id", "split"]].drop_duplicates()
    episodes = episodes.merge(split_map, on="launch_episode_id", how="inner")
    actions = pd.read_parquet(baseline_paths.cache_dir / "ep2_schedule_action_panel.parquet")
    exposures = pd.read_parquet(baseline_paths.cache_dir / "ep2_exposure_daily_panel.parquet")
    actions = actions.loc[actions["schedule_id"].eq(FROZEN_BASELINE_ID)].copy()
    exposures = exposures.loc[exposures["schedule_id"].eq(FROZEN_BASELINE_ID)].copy()

    rows = []
    for ep in episodes.itertuples(index=False):
        ep_actions = actions.loc[actions["launch_episode_id"].eq(ep.launch_episode_id)]
        ep_exposures = exposures.loc[exposures["launch_episode_id"].eq(ep.launch_episode_id)]
        buys = ep_actions.loc[ep_actions["action_type"].isin(["probe_entry", "direct_exposure"]) & ep_actions["is_executed"].astype(bool)]
        exits = ep_actions.loc[ep_actions["action_type"].isin(["fast_fail_exit", "natural_exit"]) & ep_actions["is_executed"].astype(bool)]
        first_exposure_date = buys["execution_date"].iloc[0] if not buys.empty else ""
        exit_date = exits["execution_date"].iloc[-1] if not exits.empty else ""
        rows.append(
            {
                "schedule_id": FROZEN_BASELINE_ID,
                "split": ep.split,
                "launch_episode_id": ep.launch_episode_id,
                "instrument": ep.instrument,
                "had_exposure": not buys.empty,
                "no_probe": buys.empty,
                "fast_failed": bool(ep_actions["action_type"].eq("fast_fail_exit").any()),
                "natural_exited": bool(ep_actions["action_type"].eq("natural_exit").any()),
                "after_cost_return": float(ep_exposures["cum_return_net"].iloc[-1]) if not ep_exposures.empty else 0.0,
                "missed_gain_to_exposure": 0.0 if not buys.empty else np.nan,
                "turnover": float(ep_actions["order_notional"].sum()) if not ep_actions.empty else 0.0,
                "first_exposure_date": first_exposure_date,
                "exit_date": exit_date,
                "launch_effective_date": ep.launch_effective_date,
                "first_exposure_price": float(buys["execution_price"].iloc[0]) if not buys.empty else np.nan,
            }
        )
    baseline_rows = []
    for split, group in pd.DataFrame(rows).groupby("split", sort=True):
        summary = _summarize_schedule(split, group.to_dict("records"), baseline_config)
        summary["schedule_id"] = FROZEN_BASELINE_ID
        baseline_rows.append(summary)
    return pd.DataFrame(baseline_rows)


def _select_episode_probes(scored: pd.DataFrame, threshold: float, stop_ceiling: float, config: dict[str, Any]) -> pd.DataFrame:
    max_missed = float(config["episode_primary_probe_day"]["max_missed_gain_to_probe"])
    rows = []
    for episode_id, group in scored.groupby("launch_episode_id", sort=True):
        group = group.sort_values("probe_execution_date")
        valid = group.loc[
            group["is_valid_probe_candidate"].astype(bool)
            & group["score_probe_day"].ge(threshold)
            & group["P_stop_first"].le(stop_ceiling)
            & (~group["pre_probe_fast_fail_from_launch_reference"].astype(bool))
            & group["missed_gain_to_probe"].le(max_missed)
        ].copy()
        if valid.empty:
            first = group.iloc[0]
            rows.append(
                {
                    "launch_episode_id": episode_id,
                    "instrument": first["instrument"],
                    "split": first["split"],
                    "selected_probe_signal_date": "",
                    "selected_probe_execution_date": "",
                    "selected_threshold": threshold,
                    "selected_stop_risk_ceiling": stop_ceiling,
                    "score_probe_day": np.nan,
                    "P_target_first": np.nan,
                    "P_stop_first": np.nan,
                    "P_neither": np.nan,
                    "missed_gain_to_probe": np.nan,
                    "selection_status": "no_probe",
                    "no_probe_reason": "no_candidate_passed_threshold_or_risk_filters",
                }
            )
        else:
            row = valid.iloc[0]
            rows.append(
                {
                    "launch_episode_id": episode_id,
                    "instrument": row["instrument"],
                    "split": row["split"],
                    "selected_probe_signal_date": row["probe_signal_date"],
                    "selected_probe_execution_date": row["probe_execution_date"],
                    "selected_threshold": threshold,
                    "selected_stop_risk_ceiling": stop_ceiling,
                    "score_probe_day": row["score_probe_day"],
                    "P_target_first": row["P_target_first"],
                    "P_stop_first": row["P_stop_first"],
                    "P_neither": row["P_neither"],
                    "missed_gain_to_probe": row["missed_gain_to_probe"],
                    "selection_status": "selected",
                    "no_probe_reason": "",
                }
            )
    return pd.DataFrame(rows)


def _simulate_selected_threshold(
    config: dict[str, Any],
    baseline_config: dict[str, Any],
    baseline_paths: base.Paths,
    scored: pd.DataFrame,
    threshold: float,
    stop_ceiling: float,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    episode_probe = _select_episode_probes(scored, threshold, stop_ceiling, config)
    episodes = pd.read_csv(baseline_paths.reports_dir / "ep2_launch_episode_dictionary.csv")
    split_map = scored[["launch_episode_id", "split"]].drop_duplicates()
    episodes = episodes.merge(split_map, on="launch_episode_id", how="inner")
    selected_by_episode = {
        row.launch_episode_id: row
        for row in scored.merge(
            episode_probe.loc[episode_probe["selection_status"].eq("selected"), ["launch_episode_id", "selected_probe_execution_date"]],
            left_on=["launch_episode_id", "probe_execution_date"],
            right_on=["launch_episode_id", "selected_probe_execution_date"],
            how="inner",
        ).itertuples(index=False)
    }
    panel = base.load_market_panel(baseline_config)
    lookup = base.price_lookup(panel)
    universe_set = base.universe_membership_set(baseline_config)
    calendar = base.load_calendar(baseline_config)
    action_rows: list[dict[str, Any]] = []
    exposure_rows: list[dict[str, Any]] = []
    summary_rows: list[dict[str, Any]] = []
    for ep in episodes.itertuples(index=False):
        selected = selected_by_episode.get(ep.launch_episode_id)
        result = _simulate_hazard_episode(config, baseline_config, calendar, lookup, universe_set, ep, pd.Series(selected._asdict()) if selected else None, ep.split)
        action_rows.extend(result["actions"])
        exposure_rows.extend(result["exposures"])
        summary_rows.append(result["summary"])
    summaries = pd.DataFrame(summary_rows)
    schedule_results = []
    for split, group in summaries.groupby("split", sort=True):
        schedule_results.append(_summarize_schedule(split, group.to_dict("records"), baseline_config))
    action_panel = pd.DataFrame(action_rows, columns=base.action_columns())
    exposure_panel = pd.DataFrame(exposure_rows, columns=base.exposure_columns())
    return episode_probe, action_panel, exposure_panel, pd.DataFrame(schedule_results)


def _comparison_and_gates(schedule_results: pd.DataFrame, baseline_results: pd.DataFrame, config: dict[str, Any], baseline_config: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame]:
    gate_cfg = config["proceed_gate"]
    hard_gate_splits = set(gate_cfg.get("year_positive_pnl_hard_gate_splits", ["validation", "robustness"]))
    rows = []
    gate_rows = []
    baseline_by_split = baseline_results.set_index("split")
    for row in schedule_results.itertuples(index=False):
        base_row = baseline_by_split.loc[row.split]
        mean_diff = float(row.mean_after_cost_return) - float(base_row.mean_after_cost_return)
        median_diff = float(row.median_after_cost_return) - float(base_row.median_after_cost_return)
        coverage_loss = 1.0 - float(row.big_winner_capture_rate) / float(base_row.big_winner_capture_rate) if float(base_row.big_winner_capture_rate) > 0 else 0.0
        turnover_reduction = 1.0 - float(row.turnover_proxy) / float(baseline_config["baserate_reference"]["daily_baserate_turnover_proxy"])
        missed_diff = (float(row.missed_gain_to_exposure_median) if pd.notna(row.missed_gain_to_exposure_median) else 0.0) - (
            float(base_row.missed_gain_to_exposure_median) if pd.notna(base_row.missed_gain_to_exposure_median) else 0.0
        )
        rows.append(
            {
                "split": row.split,
                "comparison_id": "probe_with_simple_stop",
                "comparison_schedule_id": FROZEN_BASELINE_ID,
                "mean_after_cost_return_diff": mean_diff,
                "median_after_cost_return_diff": median_diff,
                "big_winner_coverage_loss": coverage_loss,
                "turnover_reduction": turnover_reduction,
                "missed_gain_to_exposure_diff": missed_diff,
            }
        )
        positive_year_count = int(getattr(row, "positive_pnl_year_count", 0))
        if positive_year_count >= 3:
            year_concentration_threshold = float(gate_cfg["max_three_or_more_year_positive_pnl_share"])
        else:
            year_concentration_threshold = float(gate_cfg["max_two_year_positive_pnl_share"])
        year_gate_applies = row.split in hard_gate_splits
        year_gate_passed = (
            positive_year_count >= int(gate_cfg["min_positive_pnl_year_count"])
            and row.top_year_positive_pnl_share <= year_concentration_threshold
        )
        specs = [
            (
                "mean_after_cost_return_diff_vs_probe_with_simple_stop",
                mean_diff,
                gate_cfg["min_mean_after_cost_return_diff_vs_probe_with_simple_stop"],
                mean_diff > gate_cfg["min_mean_after_cost_return_diff_vs_probe_with_simple_stop"],
            ),
            (
                "big_winner_coverage_loss_vs_probe_with_simple_stop",
                coverage_loss,
                gate_cfg["max_big_winner_coverage_loss_vs_probe_with_simple_stop"],
                coverage_loss <= gate_cfg["max_big_winner_coverage_loss_vs_probe_with_simple_stop"],
            ),
            (
                "missed_gain_to_exposure_median",
                row.missed_gain_to_exposure_median if pd.notna(row.missed_gain_to_exposure_median) else 0.0,
                gate_cfg["max_missed_gain_to_exposure_median"],
                (row.missed_gain_to_exposure_median <= gate_cfg["max_missed_gain_to_exposure_median"]) if pd.notna(row.missed_gain_to_exposure_median) else True,
            ),
            (
                "turnover_reduction_vs_daily_baserate",
                turnover_reduction,
                gate_cfg["min_turnover_reduction_vs_daily_baserate"],
                turnover_reduction >= gate_cfg["min_turnover_reduction_vs_daily_baserate"],
            ),
            (
                "top1_instrument_year_exposure_share",
                row.top1_instrument_year_exposure_share,
                gate_cfg["max_top1_instrument_year_exposure_share"],
                row.top1_instrument_year_exposure_share <= gate_cfg["max_top1_instrument_year_exposure_share"],
            ),
            (
                "top5_instrument_exposure_share",
                row.top5_instrument_exposure_share,
                gate_cfg["max_top5_instrument_exposure_share"],
                row.top5_instrument_exposure_share <= gate_cfg["max_top5_instrument_exposure_share"],
            ),
            (
                "positive_pnl_year_count",
                positive_year_count,
                gate_cfg["min_positive_pnl_year_count"],
                positive_year_count >= int(gate_cfg["min_positive_pnl_year_count"]) if year_gate_applies else True,
                year_gate_applies,
            ),
            (
                "top_year_positive_pnl_share",
                row.top_year_positive_pnl_share,
                year_concentration_threshold,
                year_gate_passed if year_gate_applies else True,
                year_gate_applies,
            ),
            (
                "top_instrument_year_positive_pnl_share",
                row.top_instrument_year_positive_pnl_share,
                gate_cfg["max_top1_instrument_year_positive_pnl_share"],
                row.top_instrument_year_positive_pnl_share <= gate_cfg["max_top1_instrument_year_positive_pnl_share"],
                True,
            ),
        ]
        normalized_specs = []
        for spec in specs:
            if len(spec) == 4:
                gate_name, value, threshold, passed = spec
                is_hard_stop = True
            else:
                gate_name, value, threshold, passed, is_hard_stop = spec
            normalized_specs.append((gate_name, value, threshold, passed, is_hard_stop))
        for gate_name, value, threshold, passed, is_hard_stop in normalized_specs:
            gate_rows.append(
                {
                    "split": row.split,
                    "schedule_id": SCHEDULE_ID,
                    "gate_name": gate_name,
                    "gate_value": value,
                    "threshold_value": threshold,
                    "comparison_id": "probe_with_simple_stop" if "probe_with_simple_stop" in gate_name else "self",
                    "passed": bool(passed),
                    "failure_reason": "" if passed else "gate_failed",
                    "is_hard_stop": bool(is_hard_stop),
                }
            )
    return pd.DataFrame(rows), pd.DataFrame(gate_rows)


def _threshold_sweep(
    config: dict[str, Any],
    baseline_config: dict[str, Any],
    baseline_paths: base.Paths,
    scored: pd.DataFrame,
    baseline_results: pd.DataFrame,
    stop_ceiling: float,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    validation_scores = scored.loc[scored["split"].eq("validation"), "score_probe_day"].astype(float)
    quantiles = [float(x) for x in config["threshold_selection"]["threshold_quantiles"]]
    thresholds = sorted(set(float(validation_scores.quantile(q)) for q in quantiles if validation_scores.notna().any()))
    rows = []
    for threshold in thresholds:
        _, _, _, schedule_results = _simulate_selected_threshold(config, baseline_config, baseline_paths, scored, threshold, stop_ceiling)
        comparison, gates = _comparison_and_gates(schedule_results, baseline_results, config, baseline_config)
        comparison_by_split = comparison.set_index("split")
        gates_by_split = gates.groupby("split")["passed"].apply(lambda values: bool(values.astype(bool).all()))
        for row in schedule_results.itertuples(index=False):
            cmp_row = comparison_by_split.loc[row.split]
            rows.append(
                {
                    "threshold": threshold,
                    "split": row.split,
                    "episode_count": row.episode_count,
                    "episode_with_probe_count": row.episode_with_any_exposure_count,
                    "probe_rate": row.probe_rate,
                    "mean_after_cost_return": row.mean_after_cost_return,
                    "mean_after_cost_return_diff_vs_probe_with_simple_stop": cmp_row.mean_after_cost_return_diff,
                    "big_winner_coverage_loss_vs_probe_with_simple_stop": cmp_row.big_winner_coverage_loss,
                    "missed_gain_to_exposure_median": row.missed_gain_to_exposure_median,
                    "turnover_proxy": row.turnover_proxy,
                    "turnover_reduction_vs_daily_baserate": 1.0 - float(row.turnover_proxy) / float(baseline_config["baserate_reference"]["daily_baserate_turnover_proxy"]),
                    "top1_instrument_year_exposure_share": row.top1_instrument_year_exposure_share,
                    "top5_instrument_exposure_share": row.top5_instrument_exposure_share,
                    "positive_pnl_year_count": row.positive_pnl_year_count,
                    "top_year_positive_pnl_share": row.top_year_positive_pnl_share,
                    "top_instrument_year_positive_pnl_share": row.top_instrument_year_positive_pnl_share,
                    "passed_all_gates": bool(gates.loc[gates["split"].eq(row.split) & gates["is_hard_stop"].astype(bool), "passed"].astype(bool).all()),
                }
            )
    sweep = pd.DataFrame(rows)
    validation = sweep.loc[sweep["split"].eq("validation")].copy()
    passing = validation.loc[validation["passed_all_gates"].astype(bool)].copy()
    if passing.empty:
        candidates = validation.copy()
        selection_reason = "no_validation_threshold_passed_all_gates"
        validation_passed = False
    else:
        candidates = passing.copy()
        selection_reason = "best_validation_objective_among_passing_thresholds"
        validation_passed = True
    candidates = candidates.sort_values(
        [
            "mean_after_cost_return_diff_vs_probe_with_simple_stop",
            "turnover_proxy",
            "missed_gain_to_exposure_median",
            "top1_instrument_year_exposure_share",
        ],
        ascending=[False, True, True, True],
    )
    selected_threshold = float(candidates.iloc[0]["threshold"]) if not candidates.empty else np.nan
    selected = pd.DataFrame(
        [
            {
                "selected_threshold": selected_threshold,
                "selected_stop_risk_ceiling": stop_ceiling,
                "selection_split": "validation",
                "selection_reason": selection_reason,
                "validation_objective_value": float(candidates.iloc[0]["mean_after_cost_return_diff_vs_probe_with_simple_stop"]) if not candidates.empty else np.nan,
                "validation_passed_all_gates": validation_passed,
            }
        ]
    )
    return sweep, selected


def write_artifact_authority(config: dict[str, Any], paths: RequirementPaths) -> pd.DataFrame:
    rows = []
    producer = "uv run python ep2/scripts/run_requirement_02_hazard_timing_model.py --config ep2/configs/requirement_02_hazard_timing_model.yaml"
    for name in REQUIRED_CACHE:
        path = paths.cache_dir / name
        rows.append(_authority_row(name, path, "cache", producer))
    for name in REQUIRED_REPORTS:
        path = paths.reports_dir / name
        if name == "requirement_02_artifact_authority.csv":
            continue
        rows.append(_authority_row(name, path, "report", producer))
    for name in REQUIRED_MANIFESTS:
        rows.append(_authority_row(name, paths.manifests_dir / name, "manifest", producer))
    authority = pd.DataFrame(rows)
    write_csv(authority, paths.reports_dir / "requirement_02_artifact_authority.csv")
    return authority


def _authority_row(name: str, path: Path, role: str, producer: str) -> dict[str, Any]:
    row_count = np.nan
    if path.exists() and path.suffix == ".csv":
        row_count = len(pd.read_csv(path))
    elif path.exists() and path.suffix == ".parquet":
        row_count = len(pd.read_parquet(path))
    return {
        "artifact_name": name,
        "artifact_path": relpath(path),
        "authority_role": role,
        "producer_command": producer,
        "schema_version": SCHEMA_VERSION,
        "required_for_requirement": True,
        "row_count": row_count,
        "content_hash": file_hash(path) if path.exists() else "",
    }


def run_requirement_02(config_path: str | Path) -> dict[str, Any]:
    config, paths, baseline_config, baseline_paths = load_requirement_config(config_path)
    _assert_requirement_01_passed(config)

    panel = build_training_panel(config, paths, baseline_config)
    write_class_balance(panel, paths)
    features, feature_names, _ = build_features(panel, paths)
    write_csv(
        pd.DataFrame(
            [
                {
                    "model_type": config["model"]["model_type"],
                    "objective": config["model"]["objective"],
                    "num_class": config["model"]["num_class"],
                    "random_state": config["model"]["random_state"],
                    "selected_by": "pre_registered_fixed_config",
                    "validation_or_robustness_used_for_model_selection": False,
                    "feature_list_hash": base.canonical_hash(feature_names),
                }
            ]
        ),
        paths.reports_dir / "requirement_02_model_config_audit.csv",
    )
    model = _train_model(config, panel, features, feature_names)
    scored = score_panel(config, panel, features, feature_names, model, paths)
    write_model_metrics(scored, paths)

    target_validation = scored.loc[scored["split"].eq("validation") & scored["target_first_label"].astype(bool), "P_stop_first"]
    stop_ceiling = float(target_validation.median()) if target_validation.notna().any() else float(scored.loc[scored["split"].eq("validation"), "P_stop_first"].median())
    baseline_results = _baseline_summaries_by_split(panel, baseline_config, baseline_paths)
    sweep, selected_threshold = _threshold_sweep(config, baseline_config, baseline_paths, scored, baseline_results, stop_ceiling)
    write_csv(sweep, paths.reports_dir / "requirement_02_threshold_sweep.csv")
    write_csv(selected_threshold, paths.reports_dir / "requirement_02_selected_threshold.csv")

    threshold = float(selected_threshold["selected_threshold"].iloc[0])
    episode_probe, action_panel, exposure_panel, schedule_results = _simulate_selected_threshold(config, baseline_config, baseline_paths, scored, threshold, stop_ceiling)
    comparison, gates = _comparison_and_gates(schedule_results, baseline_results, config, baseline_config)
    write_csv(episode_probe, paths.reports_dir / "requirement_02_episode_primary_probe.csv")
    write_parquet(action_panel, paths.cache_dir / "requirement_02_schedule_action_panel.parquet")
    write_parquet(exposure_panel, paths.cache_dir / "requirement_02_exposure_daily_panel.parquet")
    write_csv(schedule_results, paths.reports_dir / "requirement_02_schedule_results.csv")
    write_csv(comparison, paths.reports_dir / "requirement_02_baseline_comparison.csv")
    write_csv(gates, paths.reports_dir / "requirement_02_gate_audit.csv")

    validation_passed = bool(gates.loc[gates["split"].eq("validation"), "passed"].astype(bool).all()) if not gates.loc[gates["split"].eq("validation")].empty else False
    robustness_passed = bool(gates.loc[gates["split"].eq("robustness"), "passed"].astype(bool).all()) if not gates.loc[gates["split"].eq("robustness")].empty else False
    if validation_passed and robustness_passed:
        status = "passed"
    elif validation_passed:
        status = "failed_robustness_holdout"
    else:
        status = "failed_validation"
    manifest = {
        "phase": config["phase"],
        "validation_status": status,
        "requirement_03_proceed_status": status,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "requirement_01_manifest_hash": file_hash(topic_path(config["frozen_contract"]["requirement_01_manifest"])),
        "engineering_baseline_manifest_hash": file_hash(paths.baseline_output_root / "manifests" / "ep2_engineering_baseline_manifest.json"),
        "primary_label_id": config["frozen_contract"]["primary_label_id"],
        "frozen_baseline_id": config["frozen_contract"]["frozen_baseline_id"],
        "selected_threshold": threshold,
        "selected_stop_risk_ceiling": stop_ceiling,
        "model_type": config["model"]["model_type"],
        "feature_dictionary_hash": file_hash(paths.reports_dir / "requirement_02_feature_dictionary.csv"),
        "training_panel_hash": file_hash(paths.cache_dir / "requirement_02_hazard_training_panel.parquet"),
        "prediction_panel_hash": file_hash(paths.cache_dir / "requirement_02_hazard_prediction_panel.parquet"),
        "schedule_action_panel_hash": file_hash(paths.cache_dir / "requirement_02_schedule_action_panel.parquet"),
        "gate_audit_hash": file_hash(paths.reports_dir / "requirement_02_gate_audit.csv"),
    }
    write_json(manifest, paths.manifests_dir / "requirement_02_hazard_manifest.json")
    write_artifact_authority(config, paths)
    return {
        "phase": config["phase"],
        "validation_status": status,
        "training_rows": len(panel),
        "selected_threshold": threshold,
        "selected_stop_risk_ceiling": stop_ceiling,
        "validation_gates_passed": validation_passed,
        "robustness_gates_passed": robustness_passed,
        "output_root": relpath(paths.output_root),
    }


def validate_requirement_02(config_path: str | Path, fail_on_gate_status: bool = True) -> dict[str, Any]:
    config, paths, baseline_config, _ = load_requirement_config(config_path)
    failures: list[str] = []
    try:
        _assert_requirement_01_passed(config)
    except Exception as exc:
        failures.append(str(exc))

    required_paths = [paths.cache_dir / name for name in REQUIRED_CACHE]
    required_paths += [paths.reports_dir / name for name in REQUIRED_REPORTS]
    required_paths += [paths.manifests_dir / name for name in REQUIRED_MANIFESTS]
    for path in required_paths:
        if not path.exists():
            failures.append(f"missing required artifact: {relpath(path)}")
    if failures:
        raise SystemExit("Requirement 02 validation failed:\n" + "\n".join(failures))

    panel = pd.read_parquet(paths.cache_dir / "requirement_02_hazard_training_panel.parquet")
    predictions = pd.read_parquet(paths.cache_dir / "requirement_02_hazard_prediction_panel.parquet")
    feature_dict = pd.read_csv(paths.reports_dir / "requirement_02_feature_dictionary.csv")
    feature_audit = pd.read_csv(paths.reports_dir / "requirement_02_feature_asof_audit.csv")
    selected = pd.read_csv(paths.reports_dir / "requirement_02_selected_threshold.csv")
    episode_probe = pd.read_csv(paths.reports_dir / "requirement_02_episode_primary_probe.csv")
    gates = pd.read_csv(paths.reports_dir / "requirement_02_gate_audit.csv")
    manifest = _read_json(paths.manifests_dir / "requirement_02_hazard_manifest.json")

    if panel.empty:
        failures.append("training panel is empty")
    if not panel["is_valid_probe_candidate"].astype(bool).all():
        failures.append("training panel contains invalid probe candidates")
    if not panel["primary_label_id"].eq(config["frozen_contract"]["primary_label_id"]).all():
        failures.append("training panel primary_label_id mismatch")
    class_sum = panel[["target_first_label", "stop_first_label", "neither_label"]].astype(int).sum(axis=1)
    if not class_sum.eq(1).all():
        failures.append("hazard class booleans are not exactly-one")
    split_counts = panel[["launch_episode_id", "split"]].drop_duplicates().groupby("launch_episode_id")["split"].nunique()
    if (split_counts > 1).any():
        failures.append("one or more episodes cross split boundaries")
    if set(panel["split"].unique()) - {"train", "validation", "robustness"}:
        failures.append("unexpected split value present")

    calendar = base.load_calendar(baseline_config)
    validation_embargo = _trading_day_before(calendar, config["split"]["validation_start"], int(config["split"]["embargo_trading_days"]))
    robustness_embargo = _trading_day_before(calendar, config["split"]["robustness_start"], int(config["split"]["embargo_trading_days"]))
    dates = pd.to_datetime(panel["launch_effective_date"]).dt.normalize()
    if ((panel["split"].eq("train")) & (dates >= validation_embargo)).any():
        failures.append("train split violates validation embargo")
    if ((panel["split"].eq("validation")) & (dates >= robustness_embargo)).any():
        failures.append("validation split violates robustness embargo")

    allowed_sources = {
        "ep2_candidate_probe_grid.parquet",
        "ep2_launch_observation_pool.parquet",
        "ep2_launch_episode_dictionary.csv",
    }
    if set(feature_dict.loc[feature_dict["enabled"].astype(bool), "source_artifact"]) - allowed_sources:
        failures.append("feature dictionary contains disallowed source artifacts")
    if feature_audit["uses_execution_date_intraday"].astype(bool).any() or int(feature_audit["violation_count"].sum()) != 0:
        failures.append("feature as-of audit has violations")

    prob_sum = predictions[["P_target_first", "P_stop_first", "P_neither"]].sum(axis=1)
    if not np.allclose(prob_sum.to_numpy(dtype=float), 1.0, atol=1e-6):
        failures.append("prediction probabilities do not sum to one")

    selected_threshold = float(selected["selected_threshold"].iloc[0])
    if selected["selection_split"].iloc[0] != "validation":
        failures.append("selected threshold was not selected on validation split")
    if not predictions.loc[predictions["split"].eq("validation"), "score_probe_day"].min() - 1e-12 <= selected_threshold <= predictions.loc[predictions["split"].eq("validation"), "score_probe_day"].max() + 1e-12:
        failures.append("selected threshold is not within validation score range")

    selected_rows = episode_probe.loc[episode_probe["selection_status"].eq("selected")]
    if not selected_rows.empty:
        scored = pd.read_parquet(paths.cache_dir / "requirement_02_hazard_training_panel.parquet").merge(
            predictions[
                [
                    "launch_episode_id",
                    "probe_execution_date",
                    "P_stop_first",
                    "score_probe_day",
                    "P_target_first",
                    "P_neither",
                ]
            ],
            on=["launch_episode_id", "probe_execution_date"],
            how="left",
        )
        expected = _select_episode_probes(scored, selected_threshold, float(selected["selected_stop_risk_ceiling"].iloc[0]), config)
        check = selected_rows.merge(
            expected[["launch_episode_id", "selected_probe_execution_date"]],
            on="launch_episode_id",
            suffixes=("_actual", "_expected"),
        )
        if not check["selected_probe_execution_date_actual"].eq(check["selected_probe_execution_date_expected"]).all():
            failures.append("episode primary probe is not earliest valid day")

    gate_splits = set(gates["split"].unique())
    if not {"validation", "robustness"}.issubset(gate_splits):
        failures.append("validation and robustness gates are not both reported")
    if manifest.get("primary_label_id") != config["frozen_contract"]["primary_label_id"]:
        failures.append("manifest primary_label_id mismatch")
    if manifest.get("frozen_baseline_id") != config["frozen_contract"]["frozen_baseline_id"]:
        failures.append("manifest frozen_baseline_id mismatch")
    if manifest.get("requirement_03_proceed_status") not in {"passed", "failed_validation", "failed_robustness_holdout"}:
        failures.append("invalid requirement_03_proceed_status")
    if fail_on_gate_status and manifest.get("requirement_03_proceed_status") != "passed":
        failures.append(f"Requirement 03 proceed gate not passed: {manifest.get('requirement_03_proceed_status')}")

    if failures:
        raise SystemExit("Requirement 02 validation failed:\n" + "\n".join(failures))
    return {
        "phase": config["phase"],
        "validation_status": manifest.get("validation_status"),
        "requirement_03_proceed_status": manifest.get("requirement_03_proceed_status"),
        "gate_count": len(gates),
        "passed_gate_count": int(gates["passed"].astype(bool).sum()),
        "failed_gate_count": int((~gates["passed"].astype(bool)).sum()),
    }
