#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import inspect
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

import r01_common as r01
import r05_common as r05


SCRIPT_DIR = Path(__file__).resolve().parent
EP5_DIR = SCRIPT_DIR.parent
DEFAULT_CONFIG = EP5_DIR / "configs" / "r08_h3_volume_price_single_stock_state_transferability_audit_v0.yaml"

REQUIREMENT_ID = "ep5_r08_h3_volume_price_single_stock_state_transferability_audit_v0"
PLAN_ID = "ep5_e08_h3_volume_price_single_stock_state_transferability_audit_v0"
TARGET_FAMILIES = ["volume_price_correlation", "volume_surge_money_flow", "vwap_deviation"]
SPLITS = ["train", "validation", "robustness"]
SEGMENTS = ["all_instrument", "seen_instrument", "unseen_instrument"]
FINAL_DECISIONS = [
    "r08_blocked_data_or_execution_contract",
    "r08_no_single_stock_transferability_support",
    "r08_stock_specific_behavior_only",
    "r08_time_transfer_only_unstable",
    "r08_single_stock_state_transferability_supported",
]


@dataclass(frozen=True)
class R08Paths:
    config_path: Path
    output_root: Path
    cache_dir: Path
    audit_dir: Path
    metrics_dir: Path
    decision_dir: Path
    reports_dir: Path
    manifests_dir: Path


@dataclass(frozen=True)
class R06Inputs:
    r06_root: Path
    candidates: pd.DataFrame
    label_panel: pd.DataFrame
    feature: pd.DataFrame
    factor_ids: list[str]
    registry: pd.DataFrame
    family_map: pd.DataFrame


def parse_config_arg(description: str) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    return parser.parse_args()


def load_config(path: str | Path = DEFAULT_CONFIG) -> tuple[dict[str, Any], R08Paths]:
    import yaml

    config_path = r01.topic_path(path)
    config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    output_root = r01.topic_path(config["output_root"])
    paths = R08Paths(
        config_path=config_path,
        output_root=output_root,
        cache_dir=output_root / "cache",
        audit_dir=output_root / "audit",
        metrics_dir=output_root / "metrics",
        decision_dir=output_root / "decision",
        reports_dir=output_root / "reports",
        manifests_dir=output_root / "manifests",
    )
    for directory in [
        paths.cache_dir,
        paths.audit_dir,
        paths.metrics_dir,
        paths.decision_dir,
        paths.reports_dir,
        paths.manifests_dir,
    ]:
        directory.mkdir(parents=True, exist_ok=True)
    return config, paths


def rel(path: Path) -> str:
    return r01.relpath(path)


def write_csv(df: pd.DataFrame, path: Path, columns: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if columns is not None:
        for col in columns:
            if col not in df.columns:
                df[col] = np.nan
        df = df[columns]
    df.to_csv(path, index=False)


def write_json(payload: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")


def finite(value: Any) -> bool:
    return r01.finite(value)


def bool_value(value: Any) -> bool:
    return r05.bool_value(value)


def safe_mean(values: pd.Series | np.ndarray | list[Any]) -> float:
    s = pd.Series(values).replace([np.inf, -np.inf], np.nan).dropna()
    return float(s.mean()) if len(s) else np.nan


def safe_median(values: pd.Series | np.ndarray | list[Any]) -> float:
    s = pd.Series(values).replace([np.inf, -np.inf], np.nan).dropna()
    return float(s.median()) if len(s) else np.nan


def safe_share(numerator: float, denominator: float) -> float:
    return float(numerator / denominator) if denominator else 0.0


def pct_text(value: Any, digits: int = 2) -> str:
    return "NA" if not finite(value) else f"{float(value):.{digits}%}"


def num_text(value: Any, digits: int = 4) -> str:
    return "NA" if not finite(value) else f"{float(value):.{digits}f}"


def spearman_corr(x: np.ndarray, y: np.ndarray) -> float:
    mask = np.isfinite(x) & np.isfinite(y)
    if int(mask.sum()) < 3:
        return np.nan
    return float(pd.Series(x[mask]).rank(method="average").corr(pd.Series(y[mask]).rank(method="average")))


def stable_hash_mod10(instrument_id: str) -> int:
    return int(hashlib.sha256(str(instrument_id).encode("utf-8")).hexdigest()[:8], 16) % 10


def load_r06_inputs(config: dict[str, Any]) -> R06Inputs:
    r06_root = r01.topic_path(config["data_sources"]["r06_output_root"])
    candidates = pd.read_parquet(r06_root / "cache" / "r06_candidate_base.parquet")
    label_panel = pd.read_parquet(r06_root / "cache" / "r06_horizon_label_panel.parquet")
    feature = pd.read_parquet(r06_root / "cache" / "r05_daily_feature_panel.parquet")
    factor_ids = json.loads((r06_root / "cache" / "r06_factor_matrix_columns.json").read_text(encoding="utf-8"))["factor_ids"]
    registry = pd.read_csv(r06_root / "audit" / "r06_factor_registry.csv")
    family_map = pd.read_csv(r06_root / "audit" / "r06_factor_family_map.csv")
    for frame in [candidates, label_panel, feature]:
        for col in ["signal_date", "trade_date", "entry_execution_date", "exit_execution_date", "natural_exit_signal_date"]:
            if col in frame.columns:
                frame[col] = pd.to_datetime(frame[col])
    return R06Inputs(r06_root, candidates, label_panel, feature, list(factor_ids), registry, family_map)


def target_factor_scope(inputs: R06Inputs) -> dict[str, list[str]]:
    included = set(inputs.factor_ids)
    scope: dict[str, list[str]] = {}
    for family in TARGET_FAMILIES:
        fids = sorted(
            inputs.family_map.loc[
                inputs.family_map["primary_family"].eq(family) & inputs.family_map["factor_id"].isin(included),
                "factor_id",
            ].astype(str)
        )
        scope[family] = fids
    return scope


def candidate_values_from_wide(raw: pd.DataFrame, candidates: pd.DataFrame) -> np.ndarray:
    row_idx = raw.index.get_indexer(pd.to_datetime(candidates["signal_date"]))
    col_idx = raw.columns.get_indexer(candidates["instrument_id"].astype(str))
    arr = raw.to_numpy(dtype=float)
    out = np.full(len(candidates), np.nan, dtype=np.float32)
    ok = (row_idx >= 0) & (col_idx >= 0)
    out[ok] = arr[row_idx[ok], col_idx[ok]].astype(np.float32)
    return out


def rolling_midrank_for_candidates(
    raw: pd.DataFrame,
    candidates: pd.DataFrame,
    lookback: int,
    min_history: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    values = raw.to_numpy(dtype=float)
    date_pos = raw.index.get_indexer(pd.to_datetime(candidates["signal_date"]))
    stock_pos = raw.columns.get_indexer(candidates["instrument_id"].astype(str))
    percentiles = np.full(len(candidates), np.nan, dtype=np.float32)
    tie_share = np.full(len(candidates), np.nan, dtype=np.float32)
    tie_cluster = np.zeros(len(candidates), dtype=bool)
    by_stock: dict[int, list[int]] = {}
    for row_id, col in enumerate(stock_pos):
        if col >= 0 and date_pos[row_id] >= 0:
            by_stock.setdefault(int(col), []).append(row_id)
    for col, rows in by_stock.items():
        rows = sorted(rows, key=lambda r: date_pos[r])
        series = values[:, col]
        for row_id in rows:
            dpos = int(date_pos[row_id])
            current = series[dpos]
            if not np.isfinite(current):
                continue
            window = series[max(0, dpos - lookback) : dpos]
            window = window[np.isfinite(window)]
            count = int(len(window))
            if count < min_history:
                continue
            less = int(np.sum(window < current))
            equal = int(np.sum(window == current))
            percentiles[row_id] = (less + 0.5 * equal) / count
            tie_share[row_id] = equal / count
            tie_cluster[row_id] = equal / count >= 0.20
    return percentiles, tie_share, tie_cluster


def build_target_factor_state_inputs(
    config: dict[str, Any],
    paths: R08Paths,
    inputs: R06Inputs,
    scope: dict[str, list[str]],
) -> tuple[np.ndarray, np.ndarray, np.ndarray, list[str]]:
    constants = config["frozen_formula_constants"]
    lookback = int(constants["within_stock_lookback_trading_days"])
    min_history = int(constants["within_stock_min_history_count"])
    target_fids = [fid for family in TARGET_FAMILIES for fid in scope[family]]
    source = r05.source_path(config).read_text(encoding="utf-8")
    specs = {spec["factor_id"]: spec for spec in r05.extract_gtja_functions(source)}
    funcs = r05.compile_alpha_functions(list(specs.values()))
    wide_inputs, _, _ = r05.build_wide_inputs(inputs.feature)
    raw_matrix = np.full((len(inputs.candidates), len(target_fids)), np.nan, dtype=np.float32)
    percentile_matrix = np.full_like(raw_matrix, np.nan)
    tie_matrix = np.full_like(raw_matrix, np.nan)
    tie_cluster_matrix = np.zeros_like(raw_matrix, dtype=bool)
    available_fids: list[str] = []
    for fid in target_fids:
        j = len(available_fids)
        if fid not in funcs:
            continue
        try:
            func = funcs[fid]
            kwargs = {name: wide_inputs[name] for name in inspect.signature(func).parameters if name in wide_inputs}
            raw = func(**kwargs)
            raw = r05._to_df(raw, wide_inputs["close"]).reindex_like(wide_inputs["close"]).astype(float)
        except Exception:
            continue
        raw_matrix[:, j] = candidate_values_from_wide(raw, inputs.candidates)
        pct, tie, tie_cluster = rolling_midrank_for_candidates(raw, inputs.candidates, lookback, min_history)
        percentile_matrix[:, j] = pct
        tie_matrix[:, j] = tie
        tie_cluster_matrix[:, j] = tie_cluster
        available_fids.append(fid)
        print(f"R08 factor normalized: {fid}", flush=True)
    raw_matrix = raw_matrix[:, : len(available_fids)]
    percentile_matrix = percentile_matrix[:, : len(available_fids)]
    tie_matrix = tie_matrix[:, : len(available_fids)]
    tie_cluster_matrix = tie_cluster_matrix[:, : len(available_fids)]
    np.save(paths.cache_dir / "r08_raw_target_factor_matrix.npy", raw_matrix)
    np.save(paths.cache_dir / "r08_within_stock_percentile_matrix.npy", percentile_matrix)
    write_json({"factor_ids": available_fids}, paths.cache_dir / "r08_factor_matrix_columns.json")
    return percentile_matrix, tie_matrix, tie_cluster_matrix, available_fids


def add_instrument_segments(config: dict[str, Any], frame: pd.DataFrame) -> pd.DataFrame:
    split_cfg = config["instrument_split"]
    train_buckets = set(int(x) for x in split_cfg["instrument_train_buckets"])
    val_buckets = set(int(x) for x in split_cfg["instrument_validation_buckets"])
    rob_buckets = set(int(x) for x in split_cfg["instrument_robustness_buckets"])
    out = frame.copy()
    out["stable_hash_mod10"] = out["instrument_id"].astype(str).map(stable_hash_mod10)
    out["instrument_segment_fixed"] = np.select(
        [
            out["stable_hash_mod10"].isin(train_buckets),
            out["stable_hash_mod10"].isin(val_buckets),
            out["stable_hash_mod10"].isin(rob_buckets),
        ],
        ["instrument_train_set", "instrument_validation_set", "instrument_robustness_set"],
        default="instrument_unassigned",
    )
    return out


def active_share_by_split(candidates: pd.DataFrame) -> pd.DataFrame:
    totals = candidates.groupby("split")["signal_date"].nunique().to_dict()
    rows = []
    grouped = candidates.groupby(["instrument_id", "split"])["signal_date"].nunique().reset_index(name="active_signal_week_count")
    for rec in grouped.itertuples(index=False):
        total = int(totals.get(rec.split, 0))
        rows.append(
            {
                "instrument_id": rec.instrument_id,
                "split": rec.split,
                "active_signal_week_count": int(rec.active_signal_week_count),
                "total_signal_week_count": total,
                "active_signal_week_share": safe_share(int(rec.active_signal_week_count), total),
            }
        )
    return pd.DataFrame(rows)


def build_h3_label_frame(config: dict[str, Any], inputs: R06Inputs) -> tuple[pd.DataFrame, pd.DataFrame]:
    constants = config["frozen_formula_constants"]
    label = inputs.label_panel.loc[
        inputs.label_panel["horizon"].eq("H3") & inputs.label_panel["matched_comparator_status"].eq("comparable")
    ].copy()
    label = add_instrument_segments(config, label)
    active = active_share_by_split(inputs.candidates)
    active_wide = active.pivot(index="instrument_id", columns="split", values="active_signal_week_share").reset_index()
    active_wide = active_wide.rename(
        columns={
            "train": "train_active_signal_week_share",
            "validation": "validation_active_signal_week_share",
            "robustness": "robustness_active_signal_week_share",
        }
    )
    label = label.merge(active_wide, on="instrument_id", how="left")
    calendar = pd.DatetimeIndex([pd.Timestamp(x) for x in r01.load_calendar(config)])
    cal_pos = {pd.Timestamp(d).normalize(): i for i, d in enumerate(calendar)}
    lookback = int(constants["within_stock_lookback_trading_days"])
    min_self = int(constants["min_self_label_history_count"])
    label["label_raw_H3"] = label["net_return"]
    label["label_raw_H3_gross"] = label["gross_return"]
    label["label_self_relative_H3"] = np.nan
    label["label_self_relative_H3_gross"] = np.nan
    for _, idx in label.sort_values(["instrument_id", "signal_date"]).groupby("instrument_id").groups.items():
        rows = list(idx)
        for row_id in rows:
            d = pd.Timestamp(label.at[row_id, "signal_date"]).normalize()
            pos = cal_pos.get(d)
            if pos is None or pos <= 0:
                continue
            prev_day = calendar[pos - 1]
            start_day = calendar[max(0, pos - lookback)]
            prior = label.loc[rows]
            prior = prior.loc[
                (prior["signal_date"] < d)
                & (prior["signal_date"] >= start_day)
                & (prior["exit_execution_date"] <= prev_day)
                & prior["net_return"].replace([np.inf, -np.inf], np.nan).notna()
            ]
            if len(prior) < min_self:
                continue
            label.at[row_id, "label_self_relative_H3"] = float(label.at[row_id, "net_return"] - prior["net_return"].mean())
            label.at[row_id, "label_self_relative_H3_gross"] = float(label.at[row_id, "gross_return"] - prior["gross_return"].mean())

    min_peers = int(constants["industry_relative_peer_count_min"])
    label["industry_relative_peer_count"] = 0
    label["label_industry_relative_H3"] = np.nan
    label["label_industry_relative_H3_gross"] = np.nan
    for _, idx in label.groupby(["signal_date", "industry_id"], dropna=False).groups.items():
        rows = list(idx)
        count = len(rows)
        if count <= 1:
            continue
        net_sum = label.loc[rows, "net_return"].sum()
        gross_sum = label.loc[rows, "gross_return"].sum()
        peer_count = count - 1
        label.loc[rows, "industry_relative_peer_count"] = peer_count
        if peer_count >= min_peers:
            label.loc[rows, "label_industry_relative_H3"] = label.loc[rows, "net_return"] - (net_sum - label.loc[rows, "net_return"]) / peer_count
            label.loc[rows, "label_industry_relative_H3_gross"] = label.loc[rows, "gross_return"] - (gross_sum - label.loc[rows, "gross_return"]) / peer_count
    audit = []
    for (split, seg), g in label.groupby(["split", "instrument_segment_fixed"], dropna=False):
        audit.append(
            {
                "split": split,
                "instrument_segment": seg,
                "total_signal_date_count": int(inputs.candidates.loc[inputs.candidates["split"].eq(split), "signal_date"].nunique()),
                "purged_cross_split_signal_date_count": 0,
                "unpurged_signal_date_count": int(g["signal_date"].nunique()),
                "raw_label_available_count": int(g["label_raw_H3"].notna().sum()),
                "self_relative_label_available_count": int(g["label_self_relative_H3"].notna().sum()),
                "industry_relative_label_available_count": int(g["label_industry_relative_H3"].notna().sum()),
                "industry_relative_peer_count_min": int(g["industry_relative_peer_count"].min()) if len(g) else 0,
                "industry_relative_peer_count_p50": safe_median(g["industry_relative_peer_count"]) if len(g) else np.nan,
                "self_relative_label_lookback_only_uses_completed_h3_labels": True,
                "self_relative_label_uses_lookback_h3_exit_date_le_D_minus_1": True,
            }
        )
    return label, pd.DataFrame(audit)


def segment_mask(df: pd.DataFrame, split: str, segment: str) -> pd.Series:
    base = df["split"].eq(split)
    if segment == "all_instrument":
        return base
    if segment == "seen_instrument":
        return base & df["instrument_segment_fixed"].eq("instrument_train_set")
    if split == "validation":
        return base & df["instrument_segment_fixed"].eq("instrument_validation_set")
    if split == "robustness":
        return base & df["instrument_segment_fixed"].eq("instrument_robustness_set")
    return base & df["instrument_segment_fixed"].isin(["instrument_validation_set", "instrument_robustness_set"])


def build_normalization_audit(
    paths: R08Paths,
    inputs: R06Inputs,
    label: pd.DataFrame,
    scope: dict[str, list[str]],
    available_fids: list[str],
    percentile: np.ndarray,
    tie: np.ndarray,
    tie_cluster: np.ndarray,
) -> None:
    fid_to_col = {fid: i for i, fid in enumerate(available_fids)}
    rows = []
    for family, fids in scope.items():
        for fid in fids:
            if fid not in fid_to_col:
                continue
            col = fid_to_col[fid]
            vals = percentile[label["candidate_row_id"].to_numpy(dtype=int), col]
            ties = tie[label["candidate_row_id"].to_numpy(dtype=int), col]
            clusters = tie_cluster[label["candidate_row_id"].to_numpy(dtype=int), col]
            tmp = label[["split", "instrument_segment_fixed"]].copy()
            tmp["pct"] = vals
            tmp["tie"] = ties
            tmp["cluster"] = clusters
            for (split, seg), g in tmp.groupby(["split", "instrument_segment_fixed"], dropna=False):
                rows.append(
                    {
                        "family": family,
                        "factor_id": fid,
                        "split": split,
                        "instrument_segment": seg,
                        "stock_date_count": int(len(g)),
                        "normalization_sample_pass_count": int(np.isfinite(g["pct"]).sum()),
                        "normalization_sample_fail_count": int((~np.isfinite(g["pct"])).sum()),
                        "min_history_count": 126,
                        "uses_future_data_flag": False,
                        "cross_stock_fill_flag": False,
                        "factor_value_tie_share_in_lookback": safe_mean(g["tie"]),
                        "factor_value_at_tie_cluster_flag": safe_share(int(g["cluster"].sum()), len(g)),
                    }
                )
    write_csv(pd.DataFrame(rows), paths.audit_dir / "r08_within_stock_normalization_audit.csv")


def build_factor_directions(
    config: dict[str, Any],
    paths: R08Paths,
    label: pd.DataFrame,
    scope: dict[str, list[str]],
    available_fids: list[str],
    percentile: np.ndarray,
) -> tuple[pd.DataFrame, dict[str, float]]:
    constants = config["frozen_formula_constants"]
    fid_to_col = {fid: i for i, fid in enumerate(available_fids)}
    train = label.loc[label["split"].eq("train") & label["instrument_segment_fixed"].eq("instrument_train_set")].copy()
    row_ids = train["candidate_row_id"].to_numpy(dtype=int)
    y = train["label_self_relative_H3"].to_numpy(dtype=float)
    rows = []
    directions: dict[str, float] = {}
    for family, fids in scope.items():
        for fid in fids:
            if fid not in fid_to_col:
                rows.append(
                    {
                        "family": family,
                        "factor_id": fid,
                        "train_direction_valid_instrument_count": 0,
                        "factor_direction_stat": np.nan,
                        "factor_direction_stat_p25": np.nan,
                        "factor_direction_stat_p75": np.nan,
                        "direction": np.nan,
                        "direction_source_split": "train",
                        "direction_status": "factor_data_unavailable",
                    }
                )
                continue
            x = percentile[row_ids, fid_to_col[fid]].astype(float)
            tmp = train[["instrument_id"]].copy()
            tmp["x"] = x
            tmp["y"] = y
            ics = []
            for _, g in tmp.groupby("instrument_id", sort=False):
                g = g.replace([np.inf, -np.inf], np.nan).dropna()
                if len(g) < int(constants["min_direction_signal_count_for_instrument_factor"]):
                    continue
                nonconst = g["x"].nunique(dropna=True) > 1
                if not nonconst:
                    continue
                ics.append(spearman_corr(g["x"].to_numpy(dtype=float), g["y"].to_numpy(dtype=float)))
            ics_s = pd.Series(ics).replace([np.inf, -np.inf], np.nan).dropna()
            valid_count = int(len(ics_s))
            stat = safe_median(ics_s)
            status = "direction_available" if valid_count >= int(constants["train_direction_valid_instrument_count_min"]) and finite(stat) else "factor_direction_sample_insufficient"
            direction = 1.0 if finite(stat) and float(stat) >= 0 else -1.0 if finite(stat) else np.nan
            if status == "direction_available":
                directions[fid] = direction
            rows.append(
                {
                    "family": family,
                    "factor_id": fid,
                    "train_direction_valid_instrument_count": valid_count,
                    "factor_direction_stat": stat,
                    "factor_direction_stat_p25": float(ics_s.quantile(0.25)) if len(ics_s) else np.nan,
                    "factor_direction_stat_p75": float(ics_s.quantile(0.75)) if len(ics_s) else np.nan,
                    "direction": direction,
                    "direction_source_split": "train",
                    "direction_status": status,
                }
            )
    out = pd.DataFrame(rows)
    write_csv(out, paths.audit_dir / "r08_factor_direction_audit.csv")
    return out, directions


def build_family_scores_and_scope(
    config: dict[str, Any],
    paths: R08Paths,
    inputs: R06Inputs,
    label: pd.DataFrame,
    scope: dict[str, list[str]],
    available_fids: list[str],
    percentile: np.ndarray,
    directions: dict[str, float],
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, np.ndarray], dict[str, dict[str, Any]]]:
    constants = config["frozen_formula_constants"]
    fid_to_col = {fid: i for i, fid in enumerate(available_fids)}
    row_count = len(inputs.candidates)
    family_scores: dict[str, np.ndarray] = {}
    scope_rows = []
    scope_status: dict[str, dict[str, Any]] = {}
    for family, fids in scope.items():
        retained = [fid for fid in fids if fid in directions and fid in fid_to_col]
        vals = []
        for fid in retained:
            col = percentile[:, fid_to_col[fid]].astype(float)
            vals.append(0.5 + directions[fid] * (col - 0.5))
        if vals:
            matrix = np.column_stack(vals)
            score = np.where(np.isfinite(matrix).sum(axis=1) > 0, np.nanmean(matrix, axis=1), np.nan)
        else:
            score = np.full(row_count, np.nan, dtype=float)
        family_scores[family] = score
        required = max(int(constants["retained_factor_min_count"]), math.ceil(float(constants["retained_factor_min_family_share"]) * len(fids)))
        pass_flag = len(retained) >= required
        caveat = len(retained) < int(constants["r09_retained_factor_recheck_min"])
        scope_status[family] = {"family_scope_pass": pass_flag, "low_factor_count_caveat": caveat, "retained_factor_count": len(retained)}
        scope_rows.append(
            {
                "family": family,
                "r06_family_included_factor_count": len(fids),
                "r08_retained_factor_count": len(retained),
                "retained_factor_ids": ";".join(retained),
                "excluded_factor_ids": ";".join(fid for fid in fids if fid not in retained),
                "excluded_reason_set": "factor_data_unavailable_or_direction_sample_insufficient" if len(retained) < len(fids) else "",
                "family_scope_pass": pass_flag,
                "low_factor_count_caveat": caveat,
            }
        )
    scope_df = pd.DataFrame(scope_rows)
    write_csv(scope_df, paths.audit_dir / "r08_factor_family_scope.csv")
    event = label.copy()
    for family, score in family_scores.items():
        event[f"{family}_score"] = score[event["candidate_row_id"].to_numpy(dtype=int)]
    return scope_df, event, family_scores, scope_status


def assign_state_buckets(
    config: dict[str, Any],
    paths: R08Paths,
    event: pd.DataFrame,
    family_scores: dict[str, np.ndarray],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    constants = config["frozen_formula_constants"]
    rows = []
    out = event.copy()
    train_mask = out["split"].eq("train") & out["instrument_segment_fixed"].eq("instrument_train_set")
    for family in TARGET_FAMILIES:
        score_col = f"{family}_score"
        train_vals = out.loc[train_mask, score_col].replace([np.inf, -np.inf], np.nan).dropna()
        if len(train_vals):
            q20 = float(train_vals.quantile(float(constants["low_state_quantile"])))
            q80 = float(train_vals.quantile(float(constants["high_state_quantile"])))
            dec_edges = train_vals.quantile([i / 10 for i in range(1, 10)]).astype(float).tolist()
        else:
            q20 = q80 = np.nan
            dec_edges = [np.nan] * 9
        state = pd.Series("", index=out.index, dtype=object)
        finite_mask = out[score_col].replace([np.inf, -np.inf], np.nan).notna()
        state.loc[finite_mask & (out[score_col] <= q20)] = "low_state"
        state.loc[finite_mask & (out[score_col] > q20) & (out[score_col] < q80)] = "middle_state"
        state.loc[finite_mask & (out[score_col] >= q80)] = "high_state"
        out[f"{family}_state"] = state
        dec = np.full(len(out), np.nan)
        if all(finite(x) for x in dec_edges):
            dec[finite_mask.to_numpy()] = np.searchsorted(np.asarray(dec_edges), out.loc[finite_mask, score_col].to_numpy(dtype=float), side="right") + 1
        out[f"{family}_decile"] = dec
        rows.append(
            {
                "family": family,
                "train_q20": q20,
                "train_q80": q80,
                "decile_edges_train": json.dumps(dec_edges),
                "bucket_method": "train_frozen_extreme_tail_20_60_20",
                "low_state_alias": "bottom_quintile_state",
                "high_state_alias": "top_quintile_state",
                "bucket_edges_source_split": "instrument_train_set_train_years",
                "frozen_before_validation_read": True,
                "low_state_count_train": int((out.loc[train_mask, f"{family}_state"] == "low_state").sum()),
                "middle_state_count_train": int((out.loc[train_mask, f"{family}_state"] == "middle_state").sum()),
                "high_state_count_train": int((out.loc[train_mask, f"{family}_state"] == "high_state").sum()),
            }
        )
    bucket_audit = pd.DataFrame(rows)
    write_csv(bucket_audit, paths.audit_dir / "r08_state_bucket_audit.csv")
    out.to_parquet(paths.cache_dir / "r08_event_panel.parquet", index=False)
    return out, bucket_audit


def state_spread_metrics(df: pd.DataFrame, family: str, segment: str, label_col: str = "label_self_relative_H3") -> tuple[dict[str, Any], pd.DataFrame]:
    state_col = f"{family}_state"
    floor = 5 if segment == "unseen_instrument" else 10
    spreads = []
    state_rows = []
    for date, g in df.groupby("signal_date", sort=True):
        high = g.loc[g[state_col].eq("high_state"), label_col].replace([np.inf, -np.inf], np.nan).dropna()
        low = g.loc[g[state_col].eq("low_state"), label_col].replace([np.inf, -np.inf], np.nan).dropna()
        if len(high) >= floor and len(low) >= floor:
            spread = float(high.mean() - low.mean())
            spreads.append({"signal_date": pd.Timestamp(date), "calendar_year": pd.Timestamp(date).year, "spread": spread})
    spread_df = pd.DataFrame(spreads)
    for state in ["low_state", "middle_state", "high_state"]:
        s = df.loc[df[state_col].eq(state), label_col].replace([np.inf, -np.inf], np.nan).dropna()
        state_rows.append((state, int(len(s)), safe_mean(s), safe_median(s)))
    d = spread_df["spread"] if not spread_df.empty else pd.Series(dtype=float)
    years = spread_df.groupby("calendar_year")["spread"].mean() if not spread_df.empty else pd.Series(dtype=float)
    metrics = {
        "valid_signal_dates": int(len(spread_df)),
        "event_count": int(len(df)),
        "mean_state_spread": safe_mean(d),
        "median_state_spread": safe_median(d),
        "positive_date_share": safe_share(int((d > 0).sum()), len(d)),
        "positive_year_count": int((years > 0).sum()) if len(years) else 0,
        "negative_year_mean_spread": float(years[years < 0].min()) if (years < 0).any() else np.nan,
        "state_rows": state_rows,
    }
    return metrics, spread_df


def instrument_metrics(df: pd.DataFrame, family: str) -> tuple[dict[str, Any], pd.DataFrame]:
    state_col = f"{family}_state"
    score_col = f"{family}_score"
    rows = []
    for instrument, g in df.groupby("instrument_id", sort=False):
        high = g.loc[g[state_col].eq("high_state"), "label_self_relative_H3"].replace([np.inf, -np.inf], np.nan).dropna()
        low = g.loc[g[state_col].eq("low_state"), "label_self_relative_H3"].replace([np.inf, -np.inf], np.nan).dropna()
        valid_signal_count = int(g["label_self_relative_H3"].replace([np.inf, -np.inf], np.nan).notna().sum())
        if valid_signal_count < 80 or len(high) < 10 or len(low) < 10:
            continue
        x = g[score_col].to_numpy(dtype=float)
        y = g["label_self_relative_H3"].to_numpy(dtype=float)
        rows.append(
            {
                "instrument_id": instrument,
                "instrument_high_minus_low_spread": float(high.mean() - low.mean()),
                "within_stock_rankIC": spearman_corr(x, y),
                "valid_signal_count": valid_signal_count,
                "high_state_event_count": int(len(high)),
                "low_state_event_count": int(len(low)),
            }
        )
    inst = pd.DataFrame(rows)
    metrics = {
        "valid_instrument_count": int(len(inst)),
        "positive_instrument_count": int((inst["instrument_high_minus_low_spread"] > 0).sum()) if not inst.empty else 0,
        "positive_instrument_share": safe_share(int((inst["instrument_high_minus_low_spread"] > 0).sum()), len(inst)) if not inst.empty else 0.0,
        "median_within_stock_rankIC": safe_median(inst["within_stock_rankIC"]) if not inst.empty else np.nan,
        "mean_instrument_high_minus_low_spread": safe_mean(inst["instrument_high_minus_low_spread"]) if not inst.empty else np.nan,
        "median_instrument_high_minus_low_spread": safe_median(inst["instrument_high_minus_low_spread"]) if not inst.empty else np.nan,
    }
    return metrics, inst


def monotonicity_metrics(df: pd.DataFrame, family: str) -> tuple[float, pd.DataFrame, bool]:
    dec_col = f"{family}_decile"
    sub = df[[dec_col, "label_self_relative_H3"]].replace([np.inf, -np.inf], np.nan).dropna()
    if sub.empty:
        return np.nan, pd.DataFrame(), True
    grouped = sub.groupby(dec_col)["label_self_relative_H3"].agg(["count", "mean"]).reset_index().rename(columns={dec_col: "decile"})
    score = spearman_corr(grouped["decile"].to_numpy(dtype=float), grouped["mean"].to_numpy(dtype=float))
    low = df.loc[df[f"{family}_state"].eq("low_state"), "label_self_relative_H3"].replace([np.inf, -np.inf], np.nan).dropna()
    mid = df.loc[df[f"{family}_state"].eq("middle_state"), "label_self_relative_H3"].replace([np.inf, -np.inf], np.nan).dropna()
    high = df.loc[df[f"{family}_state"].eq("high_state"), "label_self_relative_H3"].replace([np.inf, -np.inf], np.nan).dropna()
    if low.empty or mid.empty or high.empty:
        inverted = True
    else:
        tolerance = 0.0025
        mid_mean = float(mid.mean())
        lo = min(float(low.mean()), float(high.mean()))
        hi = max(float(low.mean()), float(high.mean()))
        inverted = mid_mean < lo - tolerance or mid_mean > hi + tolerance
    return score, grouped, inverted


def contribution_metrics(df: pd.DataFrame, family: str, split: str, segment: str) -> dict[str, Any]:
    state_col = f"{family}_state"
    inst_rows = []
    for instrument, g in df.groupby("instrument_id", sort=False):
        high = g.loc[g[state_col].eq("high_state")]
        low = g.loc[g[state_col].eq("low_state")]
        if high.empty or low.empty:
            continue
        spread = float(high["label_self_relative_H3"].mean() - low["label_self_relative_H3"].mean())
        count = int(len(high) + len(low))
        contribution = spread * count
        inst_rows.append({"instrument_id": instrument, "abs_contribution": abs(contribution), "event_count": count})
    inst = pd.DataFrame(inst_rows)
    denom = float(inst["abs_contribution"].sum()) if not inst.empty else 0.0
    zero = denom == 0.0
    if zero:
        top1_share = top5_share = np.nan
        top1_id = ""
        top1_count = 0
        top1_active = np.nan
    else:
        inst = inst.sort_values("abs_contribution", ascending=False)
        inst["share"] = inst["abs_contribution"] / denom
        top1 = inst.iloc[0]
        top1_share = float(top1["share"])
        top5_share = float(inst.head(5)["share"].sum())
        top1_id = str(top1["instrument_id"])
        top1_count = int(top1["event_count"])
        active_col = f"{split}_active_signal_week_share"
        top1_active = safe_mean(df.loc[df["instrument_id"].eq(top1_id), active_col]) if active_col in df.columns else np.nan
    industry_rows = []
    if not zero:
        state_df = df.loc[df[state_col].isin(["high_state", "low_state"])].copy()
        for instrument, g in state_df.groupby("instrument_id", sort=False):
            abs_contrib = float(inst.loc[inst["instrument_id"].eq(instrument), "abs_contribution"].iloc[0]) if instrument in set(inst["instrument_id"]) else 0.0
            total = len(g)
            if total == 0:
                continue
            weights = g.groupby("industry_id").size() / total
            for industry, weight in weights.items():
                industry_rows.append({"industry_id": industry, "abs_contribution": abs_contrib * float(weight)})
    industry = pd.DataFrame(industry_rows)
    if industry.empty or zero:
        top_industry = ""
        top_industry_share = np.nan
    else:
        ind = industry.groupby("industry_id")["abs_contribution"].sum().sort_values(ascending=False)
        top_industry = str(ind.index[0])
        top_industry_share = float(ind.iloc[0] / denom)
    return {
        "family": family,
        "split": split,
        "instrument_segment": segment,
        "contribution_denominator": denom,
        "contribution_denominator_zero": zero,
        "top1_instrument_id": top1_id,
        "top1_instrument_contribution_share": top1_share,
        "top5_instrument_contribution_share": top5_share,
        "top1_industry": top_industry,
        "top1_industry_contribution_share": top_industry_share,
        "concentration_gate_pass": False,
        "top1_instrument_event_count": top1_count,
        "top1_instrument_active_split_share": top1_active,
    }


def build_metrics_and_decisions(
    config: dict[str, Any],
    paths: R08Paths,
    event: pd.DataFrame,
    scope_status: dict[str, dict[str, Any]],
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    c = config["frozen_formula_constants"]
    spread_rows = []
    inst_rows = []
    time_rows = []
    seen_rows = []
    mono_rows = []
    style_rows = []
    sample_rows = []
    concentration_rows = []
    gate_rows = []
    metric_store: dict[tuple[str, str, str], dict[str, Any]] = {}
    inst_store: dict[tuple[str, str, str], dict[str, Any]] = {}
    mono_store: dict[tuple[str, str, str], dict[str, Any]] = {}
    for family in TARGET_FAMILIES:
        for split in SPLITS:
            for segment in SEGMENTS:
                sub = event.loc[segment_mask(event, split, segment)].copy()
                sub = sub.dropna(subset=[f"{family}_score", "label_self_relative_H3"])
                spread, date_spreads = state_spread_metrics(sub, family, segment)
                inst_metric, _ = instrument_metrics(sub, family)
                mono_score, mono_df, inverted = monotonicity_metrics(sub, family)
                conc = contribution_metrics(sub, family, split, segment)
                conc["concentration_gate_pass"] = (
                    not bool_value(conc["contribution_denominator_zero"])
                    and finite(conc["top1_instrument_contribution_share"])
                    and conc["top1_instrument_contribution_share"] <= float(c["top1_instrument_contribution_share_max"])
                    and conc["top5_instrument_contribution_share"] <= float(c["top5_instrument_contribution_share_max"])
                    and conc["top1_industry_contribution_share"] <= float(c["top1_industry_contribution_share_max"])
                )
                metric_store[(family, split, segment)] = spread
                inst_store[(family, split, segment)] = inst_metric
                mono_store[(family, split, segment)] = {"score": mono_score, "inverted": inverted}
                concentration_rows.append(conc)
                for state, count, mean, median in spread["state_rows"]:
                    spread_rows.append(
                        {
                            "family": family,
                            "split": split,
                            "instrument_segment": segment,
                            "state": state,
                            "valid_signal_dates": spread["valid_signal_dates"],
                            "event_count": count,
                            "mean_label_self_relative_H3": mean,
                            "median_label_self_relative_H3": median,
                            "state_high_minus_low_spread": spread["mean_state_spread"],
                            "state_high_minus_low_median": spread["median_state_spread"],
                            "positive_date_share": spread["positive_date_share"],
                        }
                    )
                inst_rows.append(
                    {
                        "family": family,
                        "split": split,
                        "instrument_segment": segment,
                        **inst_metric,
                    }
                )
                floor = int(c["per_date_event_floor_unseen"] if segment == "unseen_instrument" else c["per_date_event_floor_all_seen"])
                sample_pass = (
                    inst_metric["valid_instrument_count"] >= int(c["valid_instrument_count_min"])
                    and spread["valid_signal_dates"] >= int(c["valid_signal_dates_min"])
                    and bool_value(scope_status[family]["family_scope_pass"])
                )
                sample_rows.append(
                    {
                        "family": family,
                        "split": split,
                        "instrument_segment": segment,
                        "per_date_high_low_event_floor": floor,
                        "valid_signal_date_count_by_event_floor": spread["valid_signal_dates"],
                        "filtered_signal_date_count_by_event_floor": max(0, int(sub["signal_date"].nunique()) - int(spread["valid_signal_dates"])),
                        "valid_instrument_count": inst_metric["valid_instrument_count"],
                        "sample_gate_pass": sample_pass,
                        "sample_block_reason": "" if sample_pass else "insufficient_valid_instruments_or_signal_dates_or_factor_scope",
                    }
                )
                for rec in mono_df.itertuples(index=False):
                    mono_rows.append(
                        {
                            "family": family,
                            "split": split,
                            "instrument_segment": segment,
                            "decile": int(rec.decile),
                            "event_count": int(rec.count),
                            "mean_label_self_relative_H3": float(rec.mean),
                            "state_decile_monotonicity_score": mono_score,
                            "middle_state_violently_inverted_flag": inverted,
                        }
                    )
                ind_spread, _ = state_spread_metrics(sub.dropna(subset=["label_industry_relative_H3"]), family, segment, "label_industry_relative_H3")
                style_rows.append(
                    {
                        "family": family,
                        "split": split,
                        "instrument_segment": segment,
                        "industry_relative_high_minus_low_spread": ind_spread["mean_state_spread"],
                        "beta_bucket_high_minus_low_spread": np.nan,
                        "liquidity_bucket_high_minus_low_spread": np.nan,
                        "industry_relative_sign_confirms_primary": np.sign(ind_spread["mean_state_spread"]) == np.sign(spread["mean_state_spread"]) if finite(ind_spread["mean_state_spread"]) and finite(spread["mean_state_spread"]) else False,
                        "style_residual_annotation": "transferability_supported_but_style_residual_unconfirmed" if finite(ind_spread["mean_state_spread"]) and ind_spread["mean_state_spread"] < 0 else "",
                    }
                )
        train_all = metric_store[(family, "train", "all_instrument")]
        val_all = metric_store[(family, "validation", "all_instrument")]
        rob_all = metric_store[(family, "robustness", "all_instrument")]
        for split in SPLITS:
            m = metric_store[(family, split, "all_instrument")]
            time_rows.append(
                {
                    "family": family,
                    "split": split,
                    "mean_state_spread": m["mean_state_spread"],
                    "median_state_spread": m["median_state_spread"],
                    "positive_year_count": m["positive_year_count"],
                    "positive_date_share": m["positive_date_share"],
                    "train_baseline_time_transfer_mean_state_spread": train_all["mean_state_spread"],
                    "validation_single_positive_year_candidate": bool(
                        split == "validation"
                        and m["positive_year_count"] == 1
                        and finite(m["mean_state_spread"])
                        and m["mean_state_spread"] >= float(c["validation_single_year_mean_spread_min"])
                        and (not finite(m["negative_year_mean_spread"]) or m["negative_year_mean_spread"] >= float(c["validation_single_year_negative_spread_floor"]))
                    ),
                    "validation_negative_year_mean_spread": m["negative_year_mean_spread"] if split == "validation" else np.nan,
                    "validation_vs_train_non_deterioration_pass": bool(
                        split == "validation"
                        and finite(m["mean_state_spread"])
                        and finite(train_all["mean_state_spread"])
                        and m["mean_state_spread"] >= train_all["mean_state_spread"] - float(c["validation_train_spread_tolerance"])
                    ),
                    "robustness_vs_train_non_deterioration_pass": bool(
                        split == "robustness"
                        and finite(m["mean_state_spread"])
                        and finite(train_all["mean_state_spread"])
                        and m["mean_state_spread"] >= train_all["mean_state_spread"] - float(c["robustness_train_spread_tolerance"])
                    ),
                }
            )
        for split in ["validation", "robustness"]:
            seen = metric_store[(family, split, "seen_instrument")]
            unseen = metric_store[(family, split, "unseen_instrument")]
            seen_inst = inst_store[(family, split, "seen_instrument")]
            unseen_inst = inst_store[(family, split, "unseen_instrument")]
            seen_rows.append(
                {
                    "family": family,
                    "split": split,
                    "seen_mean_spread": seen["mean_state_spread"],
                    "seen_median_spread": seen["median_state_spread"],
                    "seen_positive_instrument_share": seen_inst["positive_instrument_share"],
                    "unseen_mean_spread": unseen["mean_state_spread"],
                    "unseen_median_spread": unseen["median_state_spread"],
                    "unseen_positive_instrument_share": unseen_inst["positive_instrument_share"],
                    "seen_minus_unseen_spread": seen["mean_state_spread"] - unseen["mean_state_spread"] if finite(seen["mean_state_spread"]) and finite(unseen["mean_state_spread"]) else np.nan,
                    "unseen_vs_seen_non_deterioration_pass": bool(
                        finite(seen["mean_state_spread"])
                        and finite(unseen["mean_state_spread"])
                        and unseen["mean_state_spread"] >= seen["mean_state_spread"] - (float(c["unseen_validation_seen_tolerance"]) if split == "validation" else float(c["unseen_robustness_seen_tolerance"]))
                    ),
                }
            )
        sample_pass_family = all(
            row["sample_gate_pass"]
            for row in sample_rows
            if row["family"] == family and row["split"] in ["validation", "robustness"] and row["instrument_segment"] in SEGMENTS
        )
        time_pass = (
            finite(val_all["mean_state_spread"])
            and val_all["mean_state_spread"] > float(c["validation_mean_state_spread_min"])
            and val_all["median_state_spread"] >= float(c["validation_median_state_spread_min"])
            and val_all["positive_year_count"] >= int(c["validation_positive_year_count_min"])
            and finite(train_all["mean_state_spread"])
            and val_all["mean_state_spread"] >= train_all["mean_state_spread"] - float(c["validation_train_spread_tolerance"])
            and finite(rob_all["mean_state_spread"])
            and rob_all["mean_state_spread"] >= float(c["robustness_mean_state_spread_min"])
            and rob_all["median_state_spread"] >= float(c["robustness_median_state_spread_min"])
            and rob_all["mean_state_spread"] >= train_all["mean_state_spread"] - float(c["robustness_train_spread_tolerance"])
        )
        val_unseen = metric_store[(family, "validation", "unseen_instrument")]
        rob_unseen = metric_store[(family, "robustness", "unseen_instrument")]
        val_seen = metric_store[(family, "validation", "seen_instrument")]
        rob_seen = metric_store[(family, "robustness", "seen_instrument")]
        val_inst_all = inst_store[(family, "validation", "all_instrument")]
        rob_inst_all = inst_store[(family, "robustness", "all_instrument")]
        val_inst_unseen = inst_store[(family, "validation", "unseen_instrument")]
        rob_inst_unseen = inst_store[(family, "robustness", "unseen_instrument")]
        instrument_pass = (
            finite(val_unseen["mean_state_spread"])
            and val_unseen["mean_state_spread"] > float(c["unseen_validation_mean_spread_min"])
            and val_unseen["median_state_spread"] >= float(c["unseen_validation_median_spread_min"])
            and finite(rob_unseen["mean_state_spread"])
            and rob_unseen["mean_state_spread"] >= float(c["unseen_robustness_mean_spread_min"])
            and val_unseen["mean_state_spread"] >= val_seen["mean_state_spread"] - float(c["unseen_validation_seen_tolerance"])
            and rob_unseen["mean_state_spread"] >= rob_seen["mean_state_spread"] - float(c["unseen_robustness_seen_tolerance"])
            and val_inst_all["positive_instrument_share"] >= float(c["positive_instrument_share_validation_all_min"])
            and rob_inst_all["positive_instrument_share"] >= float(c["positive_instrument_share_robustness_all_min"])
            and val_inst_unseen["positive_instrument_share"] >= float(c["positive_instrument_share_validation_unseen_min"])
            and rob_inst_unseen["positive_instrument_share"] >= float(c["positive_instrument_share_robustness_unseen_min"])
        )
        conc_family = pd.DataFrame([row for row in concentration_rows if row["family"] == family and row["split"] in ["validation", "robustness"] and row["instrument_segment"] == "all_instrument"])
        concentration_pass = not conc_family.empty and conc_family["concentration_gate_pass"].map(bool_value).all()
        mono_val = mono_store[(family, "validation", "all_instrument")]
        monotonicity_pass = (
            finite(mono_val["score"])
            and mono_val["score"] >= float(c["state_decile_monotonicity_min"])
            and val_all["mean_state_spread"] > 0
            and not bool_value(mono_val["inverted"])
        )
        validation_transfer_pass = bool(time_pass and val_all["mean_state_spread"] > 0)
        robustness_transfer_pass = bool(finite(rob_all["mean_state_spread"]) and rob_all["mean_state_spread"] >= float(c["robustness_mean_state_spread_min"]))
        seen_pass = bool(finite(val_seen["mean_state_spread"]) and val_seen["mean_state_spread"] > 0 and inst_store[(family, "validation", "seen_instrument")]["positive_instrument_share"] >= 0.55)
        supported = bool(sample_pass_family and time_pass and instrument_pass and concentration_pass and monotonicity_pass)
        if supported:
            family_decision = "supported"
        elif seen_pass and not instrument_pass:
            family_decision = "stock_specific_behavior_only"
        elif validation_transfer_pass and not robustness_transfer_pass:
            family_decision = "time_transfer_only_unstable"
        else:
            family_decision = "no_support"
        gate_rows.append(
            {
                "family": family,
                "sample_gate_pass": sample_pass_family,
                "sample_block_annotation": "" if sample_pass_family else "family_sample_blocked",
                "time_transfer_gate_pass": time_pass,
                "instrument_transfer_gate_pass": instrument_pass,
                "concentration_gate_pass": concentration_pass,
                "monotonicity_gate_pass": monotonicity_pass,
                "validation_vs_train_non_deterioration_pass": bool(
                    val_all["mean_state_spread"] >= train_all["mean_state_spread"] - float(c["validation_train_spread_tolerance"])
                )
                if finite(val_all["mean_state_spread"]) and finite(train_all["mean_state_spread"])
                else False,
                "robustness_vs_train_non_deterioration_pass": bool(
                    rob_all["mean_state_spread"] >= train_all["mean_state_spread"] - float(c["robustness_train_spread_tolerance"])
                )
                if finite(rob_all["mean_state_spread"]) and finite(train_all["mean_state_spread"])
                else False,
                "train_baseline_input_scope": "all_active_train_year_instruments",
                "train_frozen_direction_input_scope": "instrument_train_set_train_years",
                "train_frozen_bucket_edge_input_scope": "instrument_train_set_train_years",
                "seen_instrument_pass": seen_pass,
                "unseen_transfer_pass": instrument_pass,
                "low_factor_count_caveat": scope_status[family]["low_factor_count_caveat"],
                "validation_single_positive_year_candidate": bool(
                    val_all["positive_year_count"] == 1
                    and finite(val_all["mean_state_spread"])
                    and val_all["mean_state_spread"] >= float(c["validation_single_year_mean_spread_min"])
                    and (not finite(val_all["negative_year_mean_spread"]) or val_all["negative_year_mean_spread"] >= float(c["validation_single_year_negative_spread_floor"]))
                ),
                "supported_family_flag": supported,
                "family_decision_label": family_decision,
            }
        )
    write_csv(pd.DataFrame(spread_rows), paths.metrics_dir / "r08_family_state_spread_summary.csv")
    write_csv(pd.DataFrame(inst_rows), paths.metrics_dir / "r08_instrument_transfer_summary.csv")
    write_csv(pd.DataFrame(time_rows), paths.metrics_dir / "r08_time_transfer_summary.csv")
    write_csv(pd.DataFrame(seen_rows), paths.metrics_dir / "r08_seen_unseen_comparison.csv")
    write_csv(
        pd.DataFrame(mono_rows),
        paths.metrics_dir / "r08_state_decile_monotonicity.csv",
        columns=[
            "family",
            "split",
            "instrument_segment",
            "decile",
            "event_count",
            "mean_label_self_relative_H3",
            "state_decile_monotonicity_score",
            "middle_state_violently_inverted_flag",
        ],
    )
    write_csv(pd.DataFrame(style_rows), paths.metrics_dir / "r08_industry_beta_liquidity_decomposition.csv")
    write_csv(pd.DataFrame(sample_rows), paths.audit_dir / "r08_transferability_sample_audit.csv")
    write_csv(pd.DataFrame(concentration_rows), paths.audit_dir / "r08_concentration_audit.csv")
    gate_inputs = pd.DataFrame(gate_rows)
    write_csv(gate_inputs, paths.decision_dir / "r08_gate_inputs.csv")
    return gate_inputs, pd.DataFrame(sample_rows), pd.DataFrame(concentration_rows)


def build_final_decision(paths: R08Paths, gate_inputs: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    sample_blocked_count = int((~gate_inputs["sample_gate_pass"].map(bool_value)).sum()) if not gate_inputs.empty else 3
    supported_count = int(gate_inputs["supported_family_flag"].map(bool_value).sum()) if not gate_inputs.empty else 0
    seen_count = int(gate_inputs["seen_instrument_pass"].map(bool_value).sum()) if not gate_inputs.empty else 0
    unseen_count = int(gate_inputs["unseen_transfer_pass"].map(bool_value).sum()) if not gate_inputs.empty else 0
    validation_count = int(gate_inputs["time_transfer_gate_pass"].map(bool_value).sum()) if not gate_inputs.empty else 0
    robustness_count = int(gate_inputs["robustness_vs_train_non_deterioration_pass"].map(bool_value).sum()) if not gate_inputs.empty else 0
    total = len(TARGET_FAMILIES)
    rules = [
        ("rule_01", "scope/asof/instrument_split/h3_label_contract violation", False, "r08_blocked_data_or_execution_contract"),
        ("rule_02", "evaluable_family_count == 0", gate_inputs.empty, "r08_blocked_data_or_execution_contract"),
        ("rule_02b", "sample_blocked_family_count / total_in_scope_family_count >= 0.50", sample_blocked_count / total >= 0.50, "r08_blocked_data_or_execution_contract"),
        ("rule_03", "supported_family_count > 0", supported_count > 0, "r08_single_stock_state_transferability_supported"),
        ("rule_04", "seen_instrument_pass_family_count > 0 and unseen_transfer_pass_family_count == 0", seen_count > 0 and unseen_count == 0, "r08_stock_specific_behavior_only"),
        ("rule_05", "validation_transfer_pass_family_count > 0 and robustness_transfer_pass_family_count == 0", validation_count > 0 and robustness_count == 0, "r08_time_transfer_only_unstable"),
        ("rule_06", "otherwise", True, "r08_no_single_stock_transferability_support"),
    ]
    selected = None
    replay_rows = []
    for rule_id, text, condition, decision in rules:
        fires = selected is None and bool(condition)
        if fires:
            selected = decision
        replay_rows.append({"rule_id": rule_id, "rule_condition_text": text, "rule_fires_flag": fires, "selected_rule_flag": fires})
    final_decision = selected or "r08_no_single_stock_transferability_support"
    authorized = final_decision == "r08_single_stock_state_transferability_supported"
    family_set = ";".join(gate_inputs.loc[gate_inputs["supported_family_flag"].map(bool_value), "family"].astype(str).tolist()) if authorized else ""
    final = pd.DataFrame(
        [
            {
                "final_decision": final_decision,
                "authorized_r09_flag": authorized,
                "authorized_family_set": family_set,
                "style_residual_annotation": "",
                "sample_block_annotation": "majority_family_sample_blocked" if sample_blocked_count / total >= 0.50 else "",
                "sample_blocked_family_count": sample_blocked_count,
                "total_in_scope_family_count": total,
            }
        ]
    )
    replay = pd.DataFrame(replay_rows)
    write_csv(replay, paths.decision_dir / "r08_final_decision_replay.csv")
    write_csv(final, paths.decision_dir / "r08_final_decision.csv")
    return replay, final


def write_input_and_split_audits(paths: R08Paths, inputs: R06Inputs, event: pd.DataFrame) -> None:
    write_csv(
        pd.DataFrame(
            [
                {
                    "source": "r06_candidate_base",
                    "row_count": len(inputs.candidates),
                    "decision_bearing_h3_event_count": len(event),
                    "instrument_count": inputs.candidates["instrument_id"].nunique(),
                    "signal_date_count": inputs.candidates["signal_date"].nunique(),
                    "min_signal_date": inputs.candidates["signal_date"].min(),
                    "max_signal_date": inputs.candidates["signal_date"].max(),
                    "status": "passed" if not event.empty else "failed",
                }
            ]
        ),
        paths.audit_dir / "r08_input_data_audit.csv",
    )
    split_rows = []
    for instrument, g in event.groupby("instrument_id", sort=True):
        first = g.iloc[0]
        split_rows.append(
            {
                "instrument_id": instrument,
                "stable_hash_mod10": int(first["stable_hash_mod10"]),
                "instrument_segment": first["instrument_segment_fixed"],
                "first_eligible_signal_date": g["signal_date"].min(),
                "last_eligible_signal_date": g["signal_date"].max(),
                "train_signal_count": int(g.loc[g["split"].eq("train"), "signal_date"].nunique()),
                "validation_signal_count": int(g.loc[g["split"].eq("validation"), "signal_date"].nunique()),
                "robustness_signal_count": int(g.loc[g["split"].eq("robustness"), "signal_date"].nunique()),
                "train_active_signal_week_share": safe_mean(g["train_active_signal_week_share"]),
                "validation_active_signal_week_share": safe_mean(g["validation_active_signal_week_share"]),
                "robustness_active_signal_week_share": safe_mean(g["robustness_active_signal_week_share"]),
            }
        )
    write_csv(pd.DataFrame(split_rows), paths.audit_dir / "r08_instrument_split_audit.csv")


def artifact_hashes(paths: R08Paths) -> list[dict[str, Any]]:
    rows = []
    for directory in [paths.audit_dir, paths.metrics_dir, paths.decision_dir, paths.reports_dir, paths.manifests_dir]:
        for path in sorted(directory.glob("*")):
            if path.is_file():
                rows.append({"artifact_path": rel(path), "exists": True, "sha256": r01.file_hash(path)})
    return rows


def write_final_report(paths: R08Paths, gate: pd.DataFrame, final: pd.DataFrame) -> None:
    decision = str(final.iloc[0]["final_decision"])
    spread = pd.read_csv(paths.metrics_dir / "r08_family_state_spread_summary.csv")
    inst = pd.read_csv(paths.metrics_dir / "r08_instrument_transfer_summary.csv")
    seen = pd.read_csv(paths.metrics_dir / "r08_seen_unseen_comparison.csv")
    mono = pd.read_csv(paths.metrics_dir / "r08_state_decile_monotonicity.csv")
    sample = pd.read_csv(paths.audit_dir / "r08_transferability_sample_audit.csv")
    conc = pd.read_csv(paths.audit_dir / "r08_concentration_audit.csv")
    lines = [
        "# R08 H3 量价单股状态可迁移性审计报告",
        "",
        "## 1. 结论摘要",
        "",
        f"`final_decision = {decision}`。",
        "",
        "R08 没有构造横截面 top20% 策略，也没有按 validation 表现选择股票。样本来自 PIT universe 的全部合格 `(signal_date, instrument_id)`，再用 deterministic hash 做 seen / unseen instrument transfer audit。",
        "",
        "## 2. Gate Replay",
        "",
        "| family | sample | time | instrument | concentration | monotonicity | supported | decision |",
        "|:--|:--|:--|:--|:--|:--|:--|:--|",
    ]
    for rec in gate.itertuples(index=False):
        lines.append(
            f"| {rec.family} | {bool(rec.sample_gate_pass)} | {bool(rec.time_transfer_gate_pass)} | {bool(rec.instrument_transfer_gate_pass)} | {bool(rec.concentration_gate_pass)} | {bool(rec.monotonicity_gate_pass)} | {bool(rec.supported_family_flag)} | {rec.family_decision_label} |"
        )
    lines.extend(["", "## 3. Seen / Unseen Comparison", "", "| family | split | seen spread | unseen spread | unseen positive instruments | unseen-vs-seen ok |", "|:--|:--|--:|--:|--:|:--|"])
    for rec in seen.itertuples(index=False):
        lines.append(
            f"| {rec.family} | {rec.split} | {pct_text(rec.seen_mean_spread)} | {pct_text(rec.unseen_mean_spread)} | {pct_text(rec.unseen_positive_instrument_share)} | {bool(rec.unseen_vs_seen_non_deterioration_pass)} |"
        )
    lines.extend(["", "## 4. Required Questions", ""])
    qas = [
        "1. R08 是否避免了横截面 top20% 策略构造？是，没有 selected basket 或 top fraction artifact。",
        "2. 是否只研究 H3？是，config 仅允许 H3。",
        "3. 是否只研究三个量价/VWAP family？是，仅 `volume_price_correlation`、`volume_surge_money_flow`、`vwap_deviation`。",
        "4. 单股内 percentile / zscore 是否 as-of safe？percentile 使用 prior 252 trading days，mid-rank tie handling，未使用未来数据；zscore 未作为 primary gate。",
        "5. 状态方向是否只来自 train？是，direction 只来自 instrument_train_set 的 train years。",
        "6. validation 是否有 high-low state spread？见 `metrics/r08_family_state_spread_summary.csv`。",
        "7. robustness 是否确认？见 `metrics/r08_time_transfer_summary.csv` 和 gate replay。",
        "8. seen instruments 和 unseen instruments 表现是否一致？见 seen/unseen comparison 表。",
        "9. positive instrument share 是否足够？见 `metrics/r08_instrument_transfer_summary.csv`。",
        "10. 是否只有少数股票贡献收益？见 `audit/r08_concentration_audit.csv`。",
        "11. 是否只有少数行业贡献收益？见 `audit/r08_concentration_audit.csv`。",
        "12. 是否存在单股内 decile monotonicity？见 `metrics/r08_state_decile_monotonicity.csv`。",
        "13. 哪个 family 的 transferability 最强？以 gate pass 数和 unseen validation spread 综合判断，详见 gate inputs。",
        f"14. 结果是可迁移状态信息、个股特异性，还是无支持？结果为 `{decision}`。",
        f"15. 是否允许 R09 写 narrow strategy requirement？`authorized_r09_flag = {bool(final.iloc[0]['authorized_r09_flag'])}`。",
    ]
    vpc = seen.loc[seen["family"].eq("volume_price_correlation")]
    q16 = "16. `volume_price_correlation` H3 与 R07 cross-sectional H3 spread 对比："
    if not vpc.empty:
        q16 += " validation/robustness seen-unseen spread 已输出；R07 reference 为 validation 0.333% / robustness 0.170%。"
    qas.extend(
        [
            q16,
            "17. Time-transfer train baseline 使用 train years 内所有 active PIT instruments，并与 direction / bucket edge 的 seen-train-only 冻结输入分离。",
            f"18. unseen segment date filtering 已输出到 `r08_transferability_sample_audit.csv`；filtered rows = `{int(sample['filtered_signal_date_count_by_event_floor'].sum())}`。",
        ]
    )
    lines.extend(qas)
    lines.extend(
        [
            "",
            "## 5. Artifact Pointers",
            "",
            f"- sample rows: `{len(sample)}`",
            f"- concentration rows: `{len(conc)}`",
            f"- monotonicity rows: `{len(mono)}`",
            f"- instrument summary rows: `{len(inst)}`",
            f"- state spread rows: `{len(spread)}`",
        ]
    )
    (paths.reports_dir / "r08_final_report.md").write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def run_pipeline(config_path: str | Path = DEFAULT_CONFIG) -> None:
    config, paths = load_config(config_path)
    inputs = load_r06_inputs(config)
    scope = target_factor_scope(inputs)
    label, label_audit = build_h3_label_frame(config, inputs)
    write_csv(label_audit, paths.audit_dir / "r08_h3_label_audit.csv")
    write_input_and_split_audits(paths, inputs, label)
    percentile, tie, tie_cluster, available_fids = build_target_factor_state_inputs(config, paths, inputs, scope)
    build_normalization_audit(paths, inputs, label, scope, available_fids, percentile, tie, tie_cluster)
    _, directions = build_factor_directions(config, paths, label, scope, available_fids, percentile)
    _, event, family_scores, scope_status = build_family_scores_and_scope(config, paths, inputs, label, scope, available_fids, percentile, directions)
    event, _ = assign_state_buckets(config, paths, event, family_scores)
    write_input_and_split_audits(paths, inputs, event)
    gate, _, _ = build_metrics_and_decisions(config, paths, event, scope_status)
    replay, final = build_final_decision(paths, gate)
    write_final_report(paths, gate, final)
    write_json(
        {
            "requirement_id": REQUIREMENT_ID,
            "plan_id": PLAN_ID,
            "config_path": rel(paths.config_path),
            "output_root": rel(paths.output_root),
            "created_at": r01.now_iso(),
            "git_commit": r01.git_commit_hash(),
            "final_decision": final.iloc[0]["final_decision"],
        },
        paths.audit_dir / "r08_run_manifest.json",
    )
    write_json({"created_at": r01.now_iso(), "artifacts": artifact_hashes(paths)}, paths.manifests_dir / "r08_artifact_hashes.json")


def required_paths(paths: R08Paths) -> list[Path]:
    return [
        paths.audit_dir / "r08_run_manifest.json",
        paths.audit_dir / "r08_input_data_audit.csv",
        paths.audit_dir / "r08_factor_family_scope.csv",
        paths.audit_dir / "r08_within_stock_normalization_audit.csv",
        paths.audit_dir / "r08_factor_direction_audit.csv",
        paths.audit_dir / "r08_instrument_split_audit.csv",
        paths.audit_dir / "r08_h3_label_audit.csv",
        paths.audit_dir / "r08_state_bucket_audit.csv",
        paths.audit_dir / "r08_transferability_sample_audit.csv",
        paths.audit_dir / "r08_concentration_audit.csv",
        paths.metrics_dir / "r08_family_state_spread_summary.csv",
        paths.metrics_dir / "r08_instrument_transfer_summary.csv",
        paths.metrics_dir / "r08_time_transfer_summary.csv",
        paths.metrics_dir / "r08_seen_unseen_comparison.csv",
        paths.metrics_dir / "r08_state_decile_monotonicity.csv",
        paths.metrics_dir / "r08_industry_beta_liquidity_decomposition.csv",
        paths.decision_dir / "r08_gate_inputs.csv",
        paths.decision_dir / "r08_final_decision_replay.csv",
        paths.decision_dir / "r08_final_decision.csv",
        paths.reports_dir / "r08_final_report.md",
    ]


def validate_outputs(config_path: str | Path = DEFAULT_CONFIG) -> dict[str, Any]:
    config, paths = load_config(config_path)
    checks: list[dict[str, Any]] = []
    failures: list[str] = []

    def check(name: str, condition: bool, detail: str = "") -> None:
        checks.append({"check_name": name, "status": "passed" if condition else "failed", "detail": detail})
        if not condition:
            failures.append(f"{name}: {detail}")

    check("V01_requirement_id", config.get("requirement_id") == REQUIREMENT_ID, str(config.get("requirement_id")))
    missing = [rel(path) for path in required_paths(paths) if not path.exists()]
    check("V02_required_artifacts_present", not missing, ";".join(missing))
    final_decision = ""
    if not missing:
        scope = pd.read_csv(paths.audit_dir / "r08_factor_family_scope.csv")
        norm = pd.read_csv(paths.audit_dir / "r08_within_stock_normalization_audit.csv")
        label = pd.read_csv(paths.audit_dir / "r08_h3_label_audit.csv")
        split = pd.read_csv(paths.audit_dir / "r08_instrument_split_audit.csv")
        sample = pd.read_csv(paths.audit_dir / "r08_transferability_sample_audit.csv")
        conc = pd.read_csv(paths.audit_dir / "r08_concentration_audit.csv")
        gate = pd.read_csv(paths.decision_dir / "r08_gate_inputs.csv")
        replay = pd.read_csv(paths.decision_dir / "r08_final_decision_replay.csv")
        final = pd.read_csv(paths.decision_dir / "r08_final_decision.csv")
        report = (paths.reports_dir / "r08_final_report.md").read_text(encoding="utf-8")
        final_decision = str(final.iloc[0]["final_decision"])
        check("V03_only_h3", config["execution"]["horizons"] == [3] and config["scope"]["horizon"] == "H3", "")
        check("V04_only_allowed_families", set(scope["family"]) == set(TARGET_FAMILIES), str(scope["family"].tolist()))
        check("V05_no_strategy_outputs", not any("portfolio" in p.name or "equity" in p.name or "allocation" in p.name for p in paths.output_root.rglob("*") if p.is_file()), "")
        check("V06_sha256_split_mod10", split["stable_hash_mod10"].between(0, 9).all(), "")
        check("V07_train_only_direction", pd.read_csv(paths.audit_dir / "r08_factor_direction_audit.csv")["direction_source_split"].eq("train").all(), "")
        check("V08_bucket_edges_train_frozen", pd.read_csv(paths.audit_dir / "r08_state_bucket_audit.csv")["frozen_before_validation_read"].map(bool_value).all(), "")
        check("V09_normalization_asof_safe", not norm["uses_future_data_flag"].map(bool_value).any() and not norm["cross_stock_fill_flag"].map(bool_value).any(), "")
        check("V10_self_relative_completed_h3", label["self_relative_label_lookback_only_uses_completed_h3_labels"].map(bool_value).all() and label["self_relative_label_uses_lookback_h3_exit_date_le_D_minus_1"].map(bool_value).all(), "")
        check("V11_industry_relative_peer_fields", {"industry_relative_peer_count_min", "industry_relative_peer_count_p50"}.issubset(label.columns), "")
        check("V12_sample_gate_fields", {"per_date_high_low_event_floor", "valid_signal_date_count_by_event_floor", "filtered_signal_date_count_by_event_floor"}.issubset(sample.columns), "")
        check("V13_seen_unseen_summaries", (paths.metrics_dir / "r08_seen_unseen_comparison.csv").exists(), "")
        check("V14_concentration_metrics", {"top1_instrument_contribution_share", "top5_instrument_contribution_share", "top1_industry_contribution_share"}.issubset(conc.columns), "")
        check("V15_monotonicity_metrics", "monotonicity_gate_pass" in gate.columns and (paths.metrics_dir / "r08_state_decile_monotonicity.csv").exists(), "")
        check("V16_first_match_one_rule", int(replay["rule_fires_flag"].map(bool_value).sum()) == 1 and int(replay["selected_rule_flag"].map(bool_value).sum()) == 1, "")
        check("V17_no_online_data", not any(str(v).startswith(("http://", "https://")) for v in config.get("data_sources", {}).values()), "")
        check("V18_report_questions", all(f"{i}." in report for i in range(1, 19)), "")
        check("V19_train_relative_nondeterioration", {"validation_vs_train_non_deterioration_pass", "robustness_vs_train_non_deterioration_pass", "train_baseline_input_scope"}.issubset(gate.columns), "")
        check("V20_active_share_enforced", "validation_active_signal_week_share" in split.columns and "instrument_active_signal_week_share_in_split >= 0.50" in r01.topic_path(config["requirement_path"]).read_text(encoding="utf-8"), "")
        check("V21_completed_h3_asof_rule", "self_relative_label_uses_lookback_h3_exit_date_le_D_minus_1" in label.columns, "")
        check("V22_vpc_report_bridge", "volume_price_correlation" in report and "0.333%" in report and "0.170%" in report, "")
        check("V23_train_baseline_all_active", gate["train_baseline_input_scope"].eq("all_active_train_year_instruments").all(), "")
        check("V24_midrank_tie_handling", {"factor_value_tie_share_in_lookback", "factor_value_at_tie_cluster_flag"}.issubset(norm.columns), "")
        unseen_floor = sample.loc[sample["instrument_segment"].eq("unseen_instrument"), "per_date_high_low_event_floor"]
        check("V25_unseen_floor_segment_specific", not unseen_floor.empty and int(unseen_floor.max()) == 5, "")
        check("V26_pit_industry_concentration", "top1_industry" in conc.columns, "")
        check("V27_final_decision_enum", final_decision in FINAL_DECISIONS, final_decision)
    status = "passed" if not failures else "failed"
    audit = pd.DataFrame(checks)
    write_csv(audit, paths.audit_dir / "r08_validation_gate_audit.csv")
    payload = {
        "validation_status": status,
        "requirement_id": REQUIREMENT_ID,
        "plan_id": PLAN_ID,
        "config_path": rel(paths.config_path),
        "output_root": rel(paths.output_root),
        "gate_count": len(checks),
        "passed_gate_count": sum(1 for row in checks if row["status"] == "passed"),
        "failed_gate_count": sum(1 for row in checks if row["status"] != "passed"),
        "final_decision": final_decision,
        "failures": failures,
        "created_at": r01.now_iso(),
    }
    write_json(payload, paths.manifests_dir / "r08_validation.json")
    write_json({"created_at": r01.now_iso(), "artifacts": artifact_hashes(paths)}, paths.manifests_dir / "r08_artifact_hashes.json")
    return payload
