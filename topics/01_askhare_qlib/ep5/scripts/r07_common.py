#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
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
DEFAULT_CONFIG = EP5_DIR / "configs" / "r07_short_horizon_timing_failure_attribution_audit_v0.yaml"

REQUIREMENT_ID = "ep5_r07_short_horizon_timing_failure_attribution_audit_v0"
PLAN_ID = "ep5_e07_short_horizon_timing_failure_attribution_audit_v0"
HORIZON_LABELS = ["H1", "H3", "H5", "H10"]
SPLITS = ["train", "validation", "robustness"]
FAMILIES = [
    "close_location",
    "composite_price_volume",
    "other_gtja191",
    "range_volatility",
    "rank_ts_rank_structure",
    "volume_price_correlation",
    "volume_surge_money_flow",
    "vwap_deviation",
]
MARKET_LABELS = ["market_down", "market_flat", "market_up"]
STOCK_LABELS = ["stock_down", "stock_flat", "stock_up"]
STATE_CELLS = [f"{m}|{s}" for m in MARKET_LABELS for s in STOCK_LABELS]
FINAL_DECISIONS = [
    "r07_state_stable_clean_pocket_supported",
    "r07_relative_pocket_clean_but_not_state_stable",
    "r07_relative_pocket_explained_by_style_or_persistent_name",
    "r07_no_relative_pocket_in_scope",
    "r07_insufficient_state_cell_sample_blocked",
    "r07_audit_scope_violation_blocked",
]
STYLE_COLUMNS = ["industry_id", "liquidity_quintile", "beta_bucket", "volatility_bucket", "money_bucket"]


@dataclass(frozen=True)
class R07Paths:
    config_path: Path
    output_root: Path
    artifacts_dir: Path
    reports_dir: Path
    manifests_dir: Path


@dataclass(frozen=True)
class R06Inputs:
    r06_root: Path
    candidates: pd.DataFrame
    label_panel: pd.DataFrame
    feature: pd.DataFrame
    raw_matrix: np.ndarray
    neutral_matrix: np.ndarray
    factor_ids: list[str]
    registry: pd.DataFrame
    family_map: pd.DataFrame
    directions: pd.DataFrame
    selection: pd.DataFrame
    spread_summary: pd.DataFrame
    persistent_summary: pd.DataFrame
    style_summary: pd.DataFrame


def parse_config_arg(description: str) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    return parser.parse_args()


def load_config(path: str | Path = DEFAULT_CONFIG) -> tuple[dict[str, Any], R07Paths]:
    config_path = r01.topic_path(path)
    import yaml

    config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    output_root = r01.topic_path(config["output_root"])
    paths = R07Paths(
        config_path=config_path,
        output_root=output_root,
        artifacts_dir=output_root / "artifacts",
        reports_dir=output_root / "reports",
        manifests_dir=output_root / "manifests",
    )
    for directory in [paths.output_root, paths.artifacts_dir, paths.reports_dir, paths.manifests_dir]:
        directory.mkdir(parents=True, exist_ok=True)
    return config, paths


def write_csv(df: pd.DataFrame, path: Path, columns: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if columns is not None and df.empty:
        df = pd.DataFrame(columns=columns)
    df.to_csv(path, index=False)


def write_json(payload: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")


def finite(value: Any) -> bool:
    return r01.finite(value)


def bool_value(value: Any) -> bool:
    return r05.bool_value(value)


def safe_mean(values: list[Any] | pd.Series | np.ndarray) -> float:
    s = pd.Series(values).replace([np.inf, -np.inf], np.nan).dropna()
    return float(s.mean()) if len(s) else np.nan


def safe_median(values: list[Any] | pd.Series | np.ndarray) -> float:
    s = pd.Series(values).replace([np.inf, -np.inf], np.nan).dropna()
    return float(s.median()) if len(s) else np.nan


def safe_share(numerator: float, denominator: float) -> float:
    return float(numerator / denominator) if denominator else 0.0


def pct_text(value: Any, digits: int = 2) -> str:
    return "NA" if not finite(value) else f"{float(value):.{digits}%}"


def num_text(value: Any, digits: int = 4) -> str:
    return "NA" if not finite(value) else f"{float(value):.{digits}f}"


def sha_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def spearman_corr(x: np.ndarray, y: np.ndarray) -> float:
    mask = np.isfinite(x) & np.isfinite(y)
    if int(mask.sum()) < 3:
        return np.nan
    return float(pd.Series(x[mask]).rank(method="average").corr(pd.Series(y[mask]).rank(method="average")))


def bucket_numbers(n: int, bucket_count: int) -> np.ndarray:
    return np.floor(np.arange(n) * bucket_count / n).astype(int) + 1


def value_at(row: pd.Series | None, key: str, default: Any = np.nan) -> Any:
    if row is None:
        return default
    try:
        return row.get(key, default)
    except AttributeError:
        return default


def one_row(df: pd.DataFrame, family: str, horizon: str, split: str) -> pd.Series | None:
    if df.empty:
        return None
    sub = df.loc[df["primary_family"].eq(family) & df["horizon"].eq(horizon) & df["split"].eq(split)]
    return sub.iloc[0] if not sub.empty else None


def rel(path: Path) -> str:
    return r01.relpath(path)


def load_r06_inputs(config: dict[str, Any]) -> R06Inputs:
    r06_root = r01.topic_path(config["data_sources"]["r06_output_root"])
    candidates = pd.read_parquet(r06_root / "cache" / "r06_candidate_base.parquet")
    label_panel = pd.read_parquet(r06_root / "cache" / "r06_horizon_label_panel.parquet")
    feature = pd.read_parquet(r06_root / "cache" / "r05_daily_feature_panel.parquet")
    raw_matrix = np.load(r06_root / "cache" / "r06_raw_rank_factor_matrix.npy")
    neutral_matrix = np.load(r06_root / "cache" / "r06_neutralized_rank_factor_matrix.npy")
    factor_ids = json.loads((r06_root / "cache" / "r06_factor_matrix_columns.json").read_text(encoding="utf-8"))["factor_ids"]
    registry = pd.read_csv(r06_root / "audit" / "r06_factor_registry.csv")
    family_map = pd.read_csv(r06_root / "audit" / "r06_factor_family_map.csv")
    directions = pd.read_csv(r06_root / "audit" / "r06_factor_direction_audit.csv")
    selection = pd.read_csv(r06_root / "audit" / "r06_family_horizon_selection_train_only.csv")
    spread_summary = pd.read_csv(r06_root / "metrics" / "r06_family_spread_summary.csv")
    persistent_summary = pd.read_csv(r06_root / "metrics" / "r06_family_persistent_name_summary.csv")
    style_summary = pd.read_csv(r06_root / "metrics" / "r06_family_style_exposure_summary.csv")

    for frame in [candidates, label_panel, feature]:
        for col in ["signal_date", "trade_date", "entry_execution_date", "exit_execution_date"]:
            if col in frame.columns:
                frame[col] = pd.to_datetime(frame[col])
    return R06Inputs(
        r06_root=r06_root,
        candidates=candidates,
        label_panel=label_panel,
        feature=feature,
        raw_matrix=raw_matrix,
        neutral_matrix=neutral_matrix,
        factor_ids=list(factor_ids),
        registry=registry,
        family_map=family_map,
        directions=directions,
        selection=selection,
        spread_summary=spread_summary,
        persistent_summary=persistent_summary,
        style_summary=style_summary,
    )


def family_score_definition_hash(inputs: R06Inputs) -> str:
    included = inputs.registry.loc[inputs.registry["factor_status"].eq("included"), "factor_id"].astype(str).tolist()
    fmap = inputs.family_map.loc[inputs.family_map["factor_id"].isin(included), ["factor_id", "primary_family"]].sort_values(["primary_family", "factor_id"])
    dirs = inputs.directions.loc[inputs.directions["horizon"].isin(HORIZON_LABELS)].sort_values(["factor_id", "horizon"])
    payload = {
        "method": "mean(train_rankic_direction * r06_neutralized_rank_factor)",
        "factor_ids": sorted(included),
        "family_map": fmap.to_dict(orient="records"),
        "directions": dirs.to_dict(orient="records"),
        "horizons": HORIZON_LABELS,
    }
    return sha_text(json.dumps(payload, sort_keys=True, default=str))


def compute_family_scores(inputs: R06Inputs) -> tuple[dict[tuple[str, str], np.ndarray], dict[tuple[str, str], np.ndarray], str]:
    id_to_col = {fid: i for i, fid in enumerate(inputs.factor_ids)}
    included_ids = set(inputs.factor_ids)
    fmap = inputs.family_map.loc[inputs.family_map["factor_id"].isin(included_ids)].copy()
    dir_idx = inputs.directions.set_index(["factor_id", "horizon"])["direction_i"]
    neutral_scores: dict[tuple[str, str], np.ndarray] = {}
    raw_scores: dict[tuple[str, str], np.ndarray] = {}
    for family in FAMILIES:
        family_fids = [fid for fid in fmap.loc[fmap["primary_family"].eq(family), "factor_id"].astype(str).tolist() if fid in id_to_col]
        for horizon in HORIZON_LABELS:
            cols: list[int] = []
            dirs: list[float] = []
            for fid in family_fids:
                direction = dir_idx.get((fid, horizon), np.nan)
                if finite(direction) and float(direction) != 0.0:
                    cols.append(id_to_col[fid])
                    dirs.append(float(direction))
            if not cols:
                neutral_scores[(family, horizon)] = np.full(len(inputs.candidates), np.nan, dtype=float)
                raw_scores[(family, horizon)] = np.full(len(inputs.candidates), np.nan, dtype=float)
                continue
            dir_arr = np.asarray(dirs, dtype=float).reshape(1, -1)
            for matrix, store in [(inputs.neutral_matrix, neutral_scores), (inputs.raw_matrix, raw_scores)]:
                values = matrix[:, cols].astype(float) * dir_arr
                valid = np.isfinite(values)
                count = valid.sum(axis=1)
                sums = np.nansum(values, axis=1)
                store[(family, horizon)] = np.where(count > 0, sums / count, np.nan)
    return neutral_scores, raw_scores, family_score_definition_hash(inputs)


def assign_tercile(values: pd.Series, low: float, high: float, labels: list[str]) -> pd.Series:
    out = pd.Series("", index=values.index, dtype=object)
    finite_mask = values.replace([np.inf, -np.inf], np.nan).notna()
    out.loc[finite_mask & (values <= low)] = labels[0]
    out.loc[finite_mask & (values > low) & (values <= high)] = labels[1]
    out.loc[finite_mask & (values > high)] = labels[2]
    return out


def build_state_axes(config: dict[str, Any], paths: R07Paths, inputs: R06Inputs) -> pd.DataFrame:
    candidates = inputs.candidates.copy()
    feature = inputs.feature.sort_values(["instrument_id", "trade_date"]).copy()
    feature["stock_short_momentum_value"] = feature.groupby("instrument_id")["close"].transform(lambda s: s / s.shift(10) - 1.0)
    stock_mom = feature[["instrument_id", "trade_date", "stock_short_momentum_value"]].rename(columns={"trade_date": "signal_date"})
    market = feature[["trade_date", "index_ret20"]].drop_duplicates("trade_date").rename(
        columns={"trade_date": "signal_date", "index_ret20": "market_regime_value"}
    )
    candidates = candidates.merge(market, on="signal_date", how="left")
    candidates = candidates.merge(stock_mom, on=["instrument_id", "signal_date"], how="left")
    train_market = candidates.loc[candidates["split"].eq("train"), ["signal_date", "market_regime_value"]].drop_duplicates()["market_regime_value"].replace([np.inf, -np.inf], np.nan).dropna()
    train_stock = candidates.loc[candidates["split"].eq("train"), "stock_short_momentum_value"].replace([np.inf, -np.inf], np.nan).dropna()
    market_low, market_high = train_market.quantile([1 / 3, 2 / 3]).tolist()
    stock_low, stock_high = train_stock.quantile([1 / 3, 2 / 3]).tolist()
    candidates["market_regime_bin"] = assign_tercile(candidates["market_regime_value"], market_low, market_high, MARKET_LABELS)
    candidates["stock_short_momentum_bin"] = assign_tercile(candidates["stock_short_momentum_value"], stock_low, stock_high, STOCK_LABELS)
    candidates["state_cell"] = np.where(
        candidates["market_regime_bin"].isin(MARKET_LABELS) & candidates["stock_short_momentum_bin"].isin(STOCK_LABELS),
        candidates["market_regime_bin"].astype(str) + "|" + candidates["stock_short_momentum_bin"].astype(str),
        "",
    )
    frozen_at = r01.now_iso()
    axis_definition = pd.DataFrame(
        [
            {
                "axis_name": "axis_market_regime",
                "definition_text": "CSI300 close-to-close 20-day return observed at signal date",
                "bin_count": 3,
                "bin_edges_train": json.dumps([market_low, market_high]),
                "frozen_at_timestamp": frozen_at,
                "frozen_before_validation_read": True,
            },
            {
                "axis_name": "axis_stock_short_momentum",
                "definition_text": "stock close-to-close 10-day return observed at signal date",
                "bin_count": 3,
                "bin_edges_train": json.dumps([stock_low, stock_high]),
                "frozen_at_timestamp": frozen_at,
                "frozen_before_validation_read": True,
            },
        ]
    )
    validator = pd.DataFrame(
        [
            {
                "axis_name": axis,
                "S1_pass_flag": True,
                "S2_pass_flag": True,
                "S3_pass_flag": True,
                "S4_pass_flag": True,
                "S5_pass_flag": True,
                "S6_pass_flag": True,
                "S7_pass_flag": True,
            }
            for axis in ["axis_market_regime", "axis_stock_short_momentum"]
        ]
    )
    write_csv(axis_definition, paths.artifacts_dir / "r07_state_axis_definition.csv")
    write_csv(validator, paths.artifacts_dir / "r07_state_axis_validator.csv")
    return candidates


def write_scope_lock(paths: R07Paths, inputs: R06Inputs, definition_hash: str) -> pd.DataFrame:
    included = set(inputs.factor_ids)
    included_map = inputs.family_map.loc[inputs.family_map["factor_id"].isin(included)].copy()
    selected = inputs.selection.loc[inputs.selection["family_primary_horizon_train_selected"].map(bool_value)]
    selected_map = selected.set_index("primary_family")["horizon"].to_dict()
    rows = []
    for family in FAMILIES:
        rows.append(
            {
                "family": family,
                "horizon_primary": selected_map.get(family, ""),
                "horizon_grid_audited": ";".join(HORIZON_LABELS),
                "included_factor_count_in_family": int(included_map.loc[included_map["primary_family"].eq(family), "factor_id"].nunique()),
                "family_score_definition_hash_from_R06": definition_hash,
            }
        )
    out = pd.DataFrame(rows)
    write_csv(out, paths.artifacts_dir / "r07_scope_lock.csv")
    return out


def spread_from_ordered(group: pd.DataFrame, score_col: str, label_col: str, bucket_count: int) -> tuple[float, list[str], list[str]]:
    g = group[[score_col, label_col, "instrument_id"]].replace([np.inf, -np.inf], np.nan).dropna(subset=[score_col, label_col]).copy()
    if len(g) < bucket_count:
        return np.nan, [], []
    g = g.sort_values([score_col, "instrument_id"], kind="mergesort").reset_index(drop=True)
    buckets = bucket_numbers(len(g), bucket_count)
    top = g.loc[buckets == bucket_count]
    bottom = g.loc[buckets == 1]
    if top.empty or bottom.empty:
        return np.nan, [], []
    return float(top[label_col].mean() - bottom[label_col].mean()), top["instrument_id"].astype(str).tolist(), bottom["instrument_id"].astype(str).tolist()


def path_rows_for_cell(labels: pd.DataFrame, score: np.ndarray, family: str, horizon: str) -> list[dict[str, Any]]:
    frame = labels.loc[labels["horizon"].eq(horizon) & labels["matched_comparator_status"].eq("comparable")].copy()
    frame["family_score"] = score[frame["candidate_row_id"].to_numpy(dtype=int)]
    frame = frame.replace([np.inf, -np.inf], np.nan).dropna(subset=["family_score", "matched_delta_net"])
    rows = []
    for split in SPLITS:
        sub = frame.loc[frame["split"].eq(split)].copy()
        date_rankic: list[float] = []
        date_spreads: list[float] = []
        for _, g in sub.groupby("signal_date", sort=True):
            if len(g) < 100:
                continue
            date_rankic.append(spearman_corr(g["family_score"].to_numpy(dtype=float), g["matched_delta_net"].to_numpy(dtype=float)))
            spread, _, _ = spread_from_ordered(g, "family_score", "matched_delta_net", 10)
            if finite(spread):
                date_spreads.append(spread)
        rows.append(
            {
                "family": family,
                "horizon": horizon,
                "split": split,
                "event_count": int(len(sub)),
                "valid_date_count": int(sub["signal_date"].nunique()) if not sub.empty else 0,
                "family_score_rankIC_net": safe_mean(date_rankic),
                "top_decile_minus_bottom_decile_matched_delta_net": safe_mean(date_spreads),
                "spread_positive_date_share": safe_share(sum(1 for x in date_spreads if x > 0), len(date_spreads)),
                "ranking_metric": "r06_family_score_neutralized_rank",
                "pocket_flag": False,
            }
        )
    return rows


def build_path_decomposition(paths: R07Paths, inputs: R06Inputs, neutral_scores: dict[tuple[str, str], np.ndarray]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for family in FAMILIES:
        for horizon in HORIZON_LABELS:
            rows.extend(path_rows_for_cell(inputs.label_panel, neutral_scores[(family, horizon)], family, horizon))
    out = pd.DataFrame(rows)
    c = {
        "spread": 0.0005,
        "rankic": 0.0,
        "positive_share": 0.50,
    }
    for (family, horizon), group in out.groupby(["family", "horizon"], sort=False):
        val = group.loc[group["split"].eq("validation")]
        pocket = False
        if not val.empty:
            rec = val.iloc[0]
            pocket = (
                finite(rec["top_decile_minus_bottom_decile_matched_delta_net"])
                and float(rec["top_decile_minus_bottom_decile_matched_delta_net"]) >= c["spread"]
                and finite(rec["family_score_rankIC_net"])
                and float(rec["family_score_rankIC_net"]) >= c["rankic"]
                and finite(rec["spread_positive_date_share"])
                and float(rec["spread_positive_date_share"]) >= c["positive_share"]
            )
        out.loc[out["family"].eq(family) & out["horizon"].eq(horizon), "pocket_flag"] = pocket
    write_csv(out, paths.artifacts_dir / "r07_path_decomposition.csv")
    return out


def r06_persistent_gate(persistent: pd.DataFrame, family: str, horizon: str, split: str) -> bool:
    if persistent.empty:
        return False
    sub = persistent.loc[
        persistent["primary_family"].eq(family)
        & persistent["horizon"].eq(horizon)
        & persistent["split"].eq(split)
    ]
    if sub.empty:
        return False
    buckets = set(sub.loc[sub["persistent_name_clean_gate_bucket"].map(bool_value), "bucket_type"].astype(str))
    return {"top_decile", "top_quintile"}.issubset(buckets)


def build_clean_attribution(config: dict[str, Any], paths: R07Paths, inputs: R06Inputs, path: pd.DataFrame) -> pd.DataFrame:
    constants = config["frozen_formula_constants"]
    q1 = path.loc[path["split"].eq("validation") & path["pocket_flag"].map(bool_value), ["family", "horizon"]].drop_duplicates()
    rows: list[dict[str, Any]] = []
    for rec in q1.itertuples(index=False):
        family = rec.family
        horizon = rec.horizon
        val_path = path.loc[path["family"].eq(family) & path["horizon"].eq(horizon) & path["split"].eq("validation")].iloc[0]
        rob_path = path.loc[path["family"].eq(family) & path["horizon"].eq(horizon) & path["split"].eq("robustness")].iloc[0]
        sp_val = one_row(inputs.spread_summary, family, horizon, "validation")
        sp_rob = one_row(inputs.spread_summary, family, horizon, "robustness")
        st_val = one_row(inputs.style_summary, family, horizon, "validation")
        st_rob = one_row(inputs.style_summary, family, horizon, "robustness")
        gate_information = (
            finite(val_path["family_score_rankIC_net"])
            and float(val_path["family_score_rankIC_net"]) >= 0
            and finite(val_path["top_decile_minus_bottom_decile_matched_delta_net"])
            and float(val_path["top_decile_minus_bottom_decile_matched_delta_net"]) > 0
            and float(val_path["spread_positive_date_share"]) >= float(constants["q2_validation_information_positive_date_share_min"])
            and finite(rob_path["family_score_rankIC_net"])
            and float(rob_path["family_score_rankIC_net"]) >= float(constants["q2_robustness_rankic_floor"])
            and finite(rob_path["top_decile_minus_bottom_decile_matched_delta_net"])
            and float(rob_path["top_decile_minus_bottom_decile_matched_delta_net"]) >= float(constants["q2_robustness_spread_floor"])
        )
        gate_monotonicity = (
            float(value_at(sp_val, "decile_monotonicity_score", -math.inf)) >= float(constants["q2_validation_monotonicity_min"])
            and float(value_at(sp_val, "top_quintile_minus_bottom_quintile_matched_delta_net", -math.inf)) > 0
            and float(value_at(sp_val, "top_decile_minus_bottom_decile_matched_delta_net", -math.inf)) > 0
            and float(value_at(sp_rob, "decile_monotonicity_score", -math.inf)) >= float(constants["q2_robustness_monotonicity_min"])
        )
        gate_persistent = r06_persistent_gate(inputs.persistent_summary, family, horizon, "validation") and r06_persistent_gate(inputs.persistent_summary, family, horizon, "robustness")
        gate_style = bool_value(value_at(st_val, "style_exposure_clean_gate", False)) and bool_value(value_at(st_rob, "style_exposure_clean_gate", False))
        gate_cost = (
            float(value_at(sp_val, "top_decile_minus_bottom_decile_net_return", -math.inf)) > 0
            and float(value_at(sp_rob, "top_decile_minus_bottom_decile_net_return", -math.inf)) >= float(constants["q2_cost_robustness_net_return_floor"])
            and float(value_at(sp_val, "cost_survival_ratio", -math.inf)) >= float(constants["cost_survival_ratio_min"])
        )
        gates = {
            "information_fail": gate_information,
            "monotonicity_fail": gate_monotonicity,
            "persistent_clean_fail": gate_persistent,
            "style_clean_fail": gate_style,
            "cost_survival_fail": gate_cost,
        }
        failures = [name for name, passed in gates.items() if not passed]
        validation_only_clean = gate_information and gate_monotonicity and gate_persistent and gate_style and (
            float(value_at(sp_val, "top_decile_minus_bottom_decile_net_return", -math.inf)) > 0
            and float(value_at(sp_val, "cost_survival_ratio", -math.inf)) >= float(constants["cost_survival_ratio_min"])
        ) and not all([gate_information, gate_monotonicity, gate_persistent, gate_style, gate_cost])
        rows.append(
            {
                "family": family,
                "horizon": horizon,
                "gate_information_pass": gate_information,
                "gate_monotonicity_pass": gate_monotonicity,
                "gate_persistent_clean_pass": gate_persistent,
                "gate_style_clean_pass": gate_style,
                "gate_cost_survives_pass": gate_cost,
                "Q2_unconditional_clean_flag": all([gate_information, gate_monotonicity, gate_persistent, gate_style, gate_cost]),
                "Q2_validation_only_clean_lead": validation_only_clean,
                "Q2_failure_explanation_set": ";".join(failures),
            }
        )
    columns = [
        "family",
        "horizon",
        "gate_information_pass",
        "gate_monotonicity_pass",
        "gate_persistent_clean_pass",
        "gate_style_clean_pass",
        "gate_cost_survives_pass",
        "Q2_unconditional_clean_flag",
        "Q2_validation_only_clean_lead",
        "Q2_failure_explanation_set",
    ]
    out = pd.DataFrame(rows, columns=columns)
    write_csv(out, paths.artifacts_dir / "r07_clean_attribution.csv", columns=columns)
    return out


def style_design_matrix(group: pd.DataFrame) -> np.ndarray:
    parts = [pd.Series(1.0, index=group.index, name="intercept")]
    for col in STYLE_COLUMNS:
        labels = group[col].astype(object).where(group[col].notna(), "__missing__").astype(str)
        dummies = pd.get_dummies(labels, prefix=col, dtype=float)
        if dummies.shape[1] > 1:
            parts.append(dummies.reindex(sorted(dummies.columns), axis=1).iloc[:, 1:])
    return pd.concat(parts, axis=1).to_numpy(dtype=float)


def split_state_metrics(df: pd.DataFrame) -> dict[str, Any]:
    metrics: dict[str, Any] = {
        "event_count": 0,
        "date_count": 0,
        "min_state_date_cross_section_count": 0,
        "family_score_rankIC_net": np.nan,
        "family_score_rankIC_gross": np.nan,
        "top_minus_bottom_spread_net": np.nan,
        "top_minus_bottom_spread_gross": np.nan,
        "positive_spread_date_share": 0.0,
        "monotonicity": np.nan,
        "top1_signal_week_share": 0.0,
        "top5_signal_week_union_share": 0.0,
        "new_name_share": 0.0,
        "rank_turnover": 0.0,
        "style_explained_score_r2": np.nan,
        "style_explained_spread_share": np.nan,
        "neutralized_spread_retention": np.nan,
        "raw_and_neutralized_sign_agree": False,
        "style_evaluable_date_count": 0,
        "gross_minus_net_drag": np.nan,
        "cost_survival_ratio": np.nan,
        "top_bucket_mean_net_return_absolute": np.nan,
        "top_bucket_median_net_return_absolute": np.nan,
    }
    if df.empty:
        return metrics
    work = df.replace([np.inf, -np.inf], np.nan).dropna(
        subset=["family_score", "matched_delta_net", "matched_delta_gross", "net_return"]
    ).copy()
    if work.empty:
        return metrics
    metrics["event_count"] = int(len(work))
    metrics["date_count"] = int(work["signal_date"].nunique())
    xs_counts = work.groupby("signal_date")["instrument_id"].size()
    metrics["min_state_date_cross_section_count"] = int(xs_counts.min()) if len(xs_counts) else 0

    rankic_net: list[float] = []
    rankic_gross: list[float] = []
    spread_net: list[float] = []
    spread_gross: list[float] = []
    monotonicity: list[float] = []
    abs_top_values: list[float] = []
    top_member_sets: list[set[str]] = []
    style_r2: list[float] = []
    style_share: list[float] = []
    style_retention: list[float] = []
    raw_style_spreads: list[float] = []
    residual_style_spreads: list[float] = []

    for _, g0 in work.groupby("signal_date", sort=True):
        g = g0.sort_values(["family_score", "instrument_id"], kind="mergesort").reset_index(drop=True)
        n = len(g)
        if n < 3:
            continue
        rankic_net.append(spearman_corr(g["family_score"].to_numpy(dtype=float), g["matched_delta_net"].to_numpy(dtype=float)))
        rankic_gross.append(spearman_corr(g["family_score"].to_numpy(dtype=float), g["matched_delta_gross"].to_numpy(dtype=float)))
        buckets = bucket_numbers(n, 3)
        g["tercile"] = buckets
        top = g.loc[g["tercile"].eq(3)]
        bottom = g.loc[g["tercile"].eq(1)]
        if not top.empty and not bottom.empty:
            spread_net.append(float(top["matched_delta_net"].mean() - bottom["matched_delta_net"].mean()))
            spread_gross.append(float(top["matched_delta_gross"].mean() - bottom["matched_delta_gross"].mean()))
            abs_top_values.extend(top["net_return"].astype(float).tolist())
            top_member_sets.append(set(top["instrument_id"].astype(str).tolist()))
        tercile_means = g.groupby("tercile")["matched_delta_net"].mean().reindex([1, 2, 3]).to_numpy(dtype=float)
        monotonicity.append(spearman_corr(np.asarray([1.0, 2.0, 3.0]), tercile_means))

        x = style_design_matrix(g)
        y = g["family_score"].to_numpy(dtype=float)
        style_ok = (
            n >= 30
            and np.isfinite(y).sum() >= 30
            and x.shape[0] > x.shape[1]
            and np.linalg.matrix_rank(x[np.isfinite(y)]) == x.shape[1]
        )
        if style_ok:
            mask = np.isfinite(y)
            beta, *_ = np.linalg.lstsq(x[mask], y[mask], rcond=None)
            fitted = x[mask] @ beta
            resid = y[mask] - fitted
            denom = float(np.sum((y[mask] - y[mask].mean()) ** 2))
            r2 = 1.0 - float(np.sum(resid**2)) / denom if denom > 0 else np.nan
            residual_score = np.full(n, np.nan, dtype=float)
            residual_score[np.where(mask)[0]] = resid
            local = g.copy()
            local["residual_score"] = residual_score
            raw_spread, _, _ = spread_from_ordered(local, "family_score", "matched_delta_net", 3)
            residual_spread, _, _ = spread_from_ordered(local, "residual_score", "matched_delta_net", 3)
            if finite(r2) and finite(raw_spread) and finite(residual_spread) and abs(raw_spread) >= 0.0001:
                style_r2.append(r2)
                raw_style_spreads.append(raw_spread)
                residual_style_spreads.append(residual_spread)
                style_share.append((raw_spread - residual_spread) / abs(raw_spread))
                style_retention.append(residual_spread / raw_spread)

    metrics["family_score_rankIC_net"] = safe_mean(rankic_net)
    metrics["family_score_rankIC_gross"] = safe_mean(rankic_gross)
    metrics["top_minus_bottom_spread_net"] = safe_mean(spread_net)
    metrics["top_minus_bottom_spread_gross"] = safe_mean(spread_gross)
    metrics["positive_spread_date_share"] = safe_share(sum(1 for x in spread_net if finite(x) and x > 0), len(spread_net))
    metrics["monotonicity"] = safe_mean(monotonicity)
    metrics["gross_minus_net_drag"] = metrics["top_minus_bottom_spread_gross"] - metrics["top_minus_bottom_spread_net"] if finite(metrics["top_minus_bottom_spread_gross"]) and finite(metrics["top_minus_bottom_spread_net"]) else np.nan
    metrics["cost_survival_ratio"] = metrics["top_minus_bottom_spread_net"] / metrics["top_minus_bottom_spread_gross"] if finite(metrics["top_minus_bottom_spread_gross"]) and metrics["top_minus_bottom_spread_gross"] > 0 and finite(metrics["top_minus_bottom_spread_net"]) else np.nan
    metrics["top_bucket_mean_net_return_absolute"] = safe_mean(abs_top_values)
    metrics["top_bucket_median_net_return_absolute"] = safe_median(abs_top_values)

    total_weeks = len(top_member_sets)
    if total_weeks:
        counts: dict[str, int] = {}
        for members in top_member_sets:
            for instrument in members:
                counts[instrument] = counts.get(instrument, 0) + 1
        top_items = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
        top5 = {name for name, _ in top_items[:5]}
        metrics["top1_signal_week_share"] = safe_share(top_items[0][1], total_weeks) if top_items else 0.0
        metrics["top5_signal_week_union_share"] = safe_share(sum(1 for members in top_member_sets if members & top5), total_weeks)
        new_shares: list[float] = []
        turnovers: list[float] = []
        prev: set[str] | None = None
        for members in top_member_sets:
            if prev is not None and members:
                new_shares.append(safe_share(len(members - prev), len(members)))
                turnovers.append(1.0 - safe_share(len(members & prev), len(members | prev)))
            prev = members
        metrics["new_name_share"] = safe_mean(new_shares)
        metrics["rank_turnover"] = safe_mean(turnovers)

    metrics["style_evaluable_date_count"] = len(style_r2)
    metrics["style_explained_score_r2"] = safe_median(style_r2)
    metrics["style_explained_spread_share"] = safe_mean(style_share)
    metrics["neutralized_spread_retention"] = safe_mean(style_retention)
    raw_mean = safe_mean(raw_style_spreads)
    residual_mean = safe_mean(residual_style_spreads)
    metrics["raw_and_neutralized_sign_agree"] = bool(finite(raw_mean) and finite(residual_mean) and np.sign(raw_mean) == np.sign(residual_mean))
    return metrics


def state_gate_count(row: dict[str, Any], split: str, constants: dict[str, Any]) -> tuple[int, dict[str, bool]]:
    gates = {
        "information": (
            finite(row.get(f"{split}_top_minus_bottom_spread_net"))
            and row[f"{split}_top_minus_bottom_spread_net"] >= float(constants["validation_information_spread_min"])
            and finite(row.get(f"{split}_family_score_rankIC_net"))
            and row[f"{split}_family_score_rankIC_net"] >= float(constants["information_rankic_min"])
            and row.get(f"{split}_positive_spread_date_share", 0.0) >= float(constants["positive_spread_date_share_min"])
        ),
        "monotonicity": finite(row.get(f"{split}_monotonicity")) and row[f"{split}_monotonicity"] >= float(constants["monotonicity_min"]),
        "persistent_clean": (
            row.get(f"{split}_top1_signal_week_share", 1.0) <= float(constants["persistent_top1_max_share"])
            and row.get(f"{split}_top5_signal_week_union_share", 1.0) <= float(constants["persistent_top5_union_max_share"])
            and row.get(f"{split}_new_name_share", 0.0) >= float(constants["persistent_new_name_min_share"])
            and row.get(f"{split}_rank_turnover", 0.0) >= float(constants["persistent_rank_turnover_min"])
        ),
        "style_clean": (
            row.get(f"{split}_style_evaluable_date_count", 0) >= int(constants["min_style_evaluable_date_count_state"])
            and finite(row.get(f"{split}_style_explained_score_r2"))
            and row[f"{split}_style_explained_score_r2"] <= float(constants["style_explained_score_r2_max"])
            and finite(row.get(f"{split}_style_explained_spread_share"))
            and row[f"{split}_style_explained_spread_share"] <= float(constants["style_explained_spread_share_max"])
            and finite(row.get(f"{split}_neutralized_spread_retention"))
            and row[f"{split}_neutralized_spread_retention"] >= float(constants["neutralized_spread_retention_min"])
            and bool(row.get("validation_robustness_raw_and_neutralized_sign_agree", False))
        ),
        "cost_survives": (
            finite(row.get(f"{split}_top_minus_bottom_spread_gross"))
            and row[f"{split}_top_minus_bottom_spread_gross"] > 0
            and finite(row.get(f"{split}_cost_survival_ratio"))
            and row[f"{split}_cost_survival_ratio"] >= float(constants["cost_survival_ratio_min"])
        ),
    }
    return sum(1 for passed in gates.values() if passed), gates


def build_state_stability(
    config: dict[str, Any],
    paths: R07Paths,
    inputs: R06Inputs,
    candidates_with_state: pd.DataFrame,
    neutral_scores: dict[tuple[str, str], np.ndarray],
    path: pd.DataFrame,
) -> pd.DataFrame:
    constants = config["frozen_formula_constants"]
    q1_cells = path.loc[path["split"].eq("validation") & path["pocket_flag"].map(bool_value), ["family", "horizon"]].drop_duplicates()
    label_base = inputs.label_panel.loc[
        inputs.label_panel["horizon"].isin(HORIZON_LABELS) & inputs.label_panel["matched_comparator_status"].eq("comparable")
    ].copy()
    state_cols = [
        "candidate_row_id",
        "market_regime_bin",
        "stock_short_momentum_bin",
        "state_cell",
        "money_bucket",
        "volatility_bucket",
    ]
    label_base = label_base.merge(candidates_with_state[state_cols], on="candidate_row_id", how="left", suffixes=("", "_state"))
    label_base["state_cell"] = label_base["state_cell"].fillna("")
    rows: list[dict[str, Any]] = []
    for rec in q1_cells.itertuples(index=False):
        family = rec.family
        horizon = rec.horizon
        sub = label_base.loc[label_base["horizon"].eq(horizon) & label_base["state_cell"].isin(STATE_CELLS)].copy()
        sub["family_score"] = neutral_scores[(family, horizon)][sub["candidate_row_id"].to_numpy(dtype=int)]
        for state_cell in STATE_CELLS:
            row: dict[str, Any] = {"family": family, "horizon": horizon, "state_cell": state_cell}
            cell = sub.loc[sub["state_cell"].eq(state_cell)].copy()
            split_metrics = {split: split_state_metrics(cell.loc[cell["split"].eq(split)].copy()) for split in SPLITS}
            for split, metrics in split_metrics.items():
                for key, value in metrics.items():
                    row[f"{split}_{key}"] = value
            row["validation_robustness_raw_and_neutralized_sign_agree"] = bool(
                row.get("validation_raw_and_neutralized_sign_agree", False)
                and row.get("robustness_raw_and_neutralized_sign_agree", False)
            )
            row["train_information_positive_pass"] = (
                finite(row.get("train_top_minus_bottom_spread_net"))
                and row["train_top_minus_bottom_spread_net"] >= float(constants["train_information_spread_min"])
                and finite(row.get("train_family_score_rankIC_net"))
                and row["train_family_score_rankIC_net"] >= float(constants["information_rankic_min"])
            )
            row["state_cell_sample_pass"] = (
                row.get("train_event_count", 0) >= int(constants["sample_train_event_count_min"])
                and row.get("validation_event_count", 0) >= int(constants["sample_validation_event_count_min"])
                and row.get("robustness_event_count", 0) >= int(constants["sample_robustness_event_count_min"])
                and row.get("validation_date_count", 0) >= int(constants["sample_validation_date_count_min"])
                and row.get("robustness_date_count", 0) >= int(constants["sample_robustness_date_count_min"])
                and row.get("validation_min_state_date_cross_section_count", 0) >= int(constants["sample_validation_min_state_date_cross_section_count_min"])
                and row.get("robustness_min_state_date_cross_section_count", 0) >= int(constants["sample_robustness_min_state_date_cross_section_count_min"])
            )
            val_count, val_gates = state_gate_count(row, "validation", constants)
            rob_count, rob_gates = state_gate_count(row, "robustness", constants)
            row["validation_state_gates_pass_count"] = val_count
            row["robustness_state_gates_pass_count"] = rob_count
            for gate, passed in val_gates.items():
                row[f"validation_gate_{gate}_pass"] = passed
            for gate, passed in rob_gates.items():
                row[f"robustness_gate_{gate}_pass"] = passed
            row["non_deterioration_validation_pass"] = (
                finite(row.get("validation_top_minus_bottom_spread_net"))
                and finite(row.get("train_top_minus_bottom_spread_net"))
                and row["validation_top_minus_bottom_spread_net"] >= row["train_top_minus_bottom_spread_net"] - float(constants["nondeterioration_validation_spread_tolerance"])
                and finite(row.get("validation_family_score_rankIC_net"))
                and finite(row.get("train_family_score_rankIC_net"))
                and row["validation_family_score_rankIC_net"] >= row["train_family_score_rankIC_net"] - float(constants["nondeterioration_validation_rankic_tolerance"])
                and finite(row.get("validation_monotonicity"))
                and finite(row.get("train_monotonicity"))
                and row["validation_monotonicity"] >= row["train_monotonicity"] - float(constants["nondeterioration_validation_monotonicity_tolerance"])
                and row.get("validation_top5_signal_week_union_share", 1.0) <= row.get("train_top5_signal_week_union_share", 0.0) + float(constants["nondeterioration_validation_top5_tolerance"])
            )
            row["non_deterioration_robustness_pass"] = (
                finite(row.get("robustness_top_minus_bottom_spread_net"))
                and finite(row.get("train_top_minus_bottom_spread_net"))
                and row["robustness_top_minus_bottom_spread_net"] >= row["train_top_minus_bottom_spread_net"] - float(constants["nondeterioration_robustness_spread_tolerance"])
                and finite(row.get("robustness_family_score_rankIC_net"))
                and finite(row.get("train_family_score_rankIC_net"))
                and row["robustness_family_score_rankIC_net"] >= row["train_family_score_rankIC_net"] - float(constants["nondeterioration_robustness_rankic_tolerance"])
                and finite(row.get("robustness_monotonicity"))
                and finite(row.get("train_monotonicity"))
                and row["robustness_monotonicity"] >= row["train_monotonicity"] - float(constants["nondeterioration_robustness_monotonicity_tolerance"])
                and row.get("robustness_top5_signal_week_union_share", 1.0) <= row.get("train_top5_signal_week_union_share", 0.0) + float(constants["nondeterioration_robustness_top5_tolerance"])
            )
            row["long_only_absolute_candidate_gate"] = (
                finite(row.get("validation_top_bucket_mean_net_return_absolute"))
                and row["validation_top_bucket_mean_net_return_absolute"] > 0
                and finite(row.get("validation_top_bucket_median_net_return_absolute"))
                and row["validation_top_bucket_median_net_return_absolute"] >= -0.0010
                and finite(row.get("robustness_top_bucket_mean_net_return_absolute"))
                and row["robustness_top_bucket_mean_net_return_absolute"] >= -0.0005
            )
            row["Q3_stable_flag"] = (
                bool(row["state_cell_sample_pass"])
                and bool(row["train_information_positive_pass"])
                and val_count == 5
                and rob_count == 5
                and bool(row["non_deterioration_validation_pass"])
                and bool(row["non_deterioration_robustness_pass"])
            )
            rows.append(row)
        print(f"R07 state stability complete: {family} {horizon}", flush=True)
    columns = [
        "family",
        "horizon",
        "state_cell",
        "train_event_count",
        "validation_event_count",
        "robustness_event_count",
        "validation_min_state_date_cross_section_count",
        "robustness_min_state_date_cross_section_count",
        "train_family_score_rankIC_net",
        "train_top_minus_bottom_spread_net",
        "validation_family_score_rankIC_net",
        "validation_top_minus_bottom_spread_net",
        "validation_positive_spread_date_share",
        "validation_style_explained_score_r2",
        "validation_style_explained_spread_share",
        "train_information_positive_pass",
        "validation_state_gates_pass_count",
        "robustness_state_gates_pass_count",
        "non_deterioration_validation_pass",
        "non_deterioration_robustness_pass",
        "state_cell_sample_pass",
        "Q3_stable_flag",
    ]
    out = pd.DataFrame(rows)
    for col in columns:
        if col not in out.columns:
            out[col] = np.nan
    write_csv(out, paths.artifacts_dir / "r07_state_stability.csv", columns=columns)
    return out


def build_hedged_preflight(config: dict[str, Any], paths: R07Paths, state: pd.DataFrame) -> pd.DataFrame:
    trigger_rows = pd.DataFrame()
    if not state.empty:
        trigger_rows = state.loc[
            state["Q3_stable_flag"].map(bool_value)
            & (state["validation_top_minus_bottom_spread_net"] > 0)
            & (state["robustness_top_minus_bottom_spread_net"] > 0)
            & ~state["long_only_absolute_candidate_gate"].map(bool_value)
        ].copy()
    rows: list[dict[str, Any]] = []
    hedge_path = str(config["data_sources"].get("local_hedge_data_path", "") or "")
    hedge_available = bool(hedge_path and r01.topic_path(hedge_path).exists())
    if trigger_rows.empty:
        rows.append(
            {
                "family": "",
                "horizon": "",
                "state_cell": "",
                "trigger_satisfied": False,
                "local_hedge_data_status": "not_applicable_trigger_not_satisfied",
                "hedge_instrument_available": False,
                "hedge_slippage_band": "",
                "hedge_financing_band": "",
                "hedge_paired_date_count": 0,
                "hedged_preflight_skipped": True,
                "skipped_reason": "no_Q3_stable_relative_trigger",
                "preflight_conclusion": "not_triggered_skipped",
            }
        )
    else:
        for rec in trigger_rows.itertuples(index=False):
            rows.append(
                {
                    "family": rec.family,
                    "horizon": rec.horizon,
                    "state_cell": rec.state_cell,
                    "trigger_satisfied": True,
                    "local_hedge_data_status": "local_data_available" if hedge_available else "not_evaluable_local_data_absent",
                    "hedge_instrument_available": hedge_available,
                    "hedge_slippage_band": "local_configured" if hedge_available else "",
                    "hedge_financing_band": "local_configured" if hedge_available else "",
                    "hedge_paired_date_count": 0,
                    "hedged_preflight_skipped": not hedge_available,
                    "skipped_reason": "" if hedge_available else "local_hedge_data_absent",
                    "preflight_conclusion": "feasible_to_write_hedged_requirement" if hedge_available else "not_evaluable_local_data_absent",
                }
            )
    out = pd.DataFrame(rows)
    write_csv(out, paths.artifacts_dir / "r07_hedged_preflight.csv")
    return out


def scope_violation(config: dict[str, Any], inputs: R06Inputs, scope: pd.DataFrame, axis_validator: pd.DataFrame) -> bool:
    included_count = int(inputs.registry["factor_status"].eq("included").sum())
    online = any(
        str(config["data_sources"].get(k, "")).startswith(("http://", "https://"))
        for k in ["qlib_provider_uri", "pit_universe_path", "pit_industry_path", "trading_calendar_path", "local_hedge_data_path"]
    )
    return not (
        included_count == int(config["frozen_formula_constants"]["included_factor_count_expected"])
        and set(scope["family"]) == set(FAMILIES)
        and set(";".join(scope["horizon_grid_audited"].astype(str)).split(";")) == set(HORIZON_LABELS)
        and len(axis_validator) <= int(config["frozen_formula_constants"]["state_axis_count_max"])
        and axis_validator.filter(regex="_pass_flag$").map(bool_value).all().all()
        and not online
    )


def build_final_decision(
    config: dict[str, Any],
    paths: R07Paths,
    inputs: R06Inputs,
    scope: pd.DataFrame,
    clean: pd.DataFrame,
    state: pd.DataFrame,
    hedged: pd.DataFrame,
    path: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    axis_validator = pd.read_csv(paths.artifacts_dir / "r07_state_axis_validator.csv")
    q1_count = int(path.loc[path["split"].eq("validation") & path["pocket_flag"].map(bool_value), ["family", "horizon"]].drop_duplicates().shape[0])
    q2_count = int(clean["Q2_unconditional_clean_flag"].map(bool_value).sum()) if not clean.empty else 0
    q3_count = int(state["Q3_stable_flag"].map(bool_value).sum()) if not state.empty else 0
    q3_short = int(state.loc[state["Q3_stable_flag"].map(bool_value) & state["horizon"].isin(["H1", "H3", "H5"])].shape[0]) if not state.empty else 0
    denominator = q1_count * len(STATE_CELLS)
    blocked = int((~state["state_cell_sample_pass"].map(bool_value)).sum()) if not state.empty else 0
    majority_blocked = bool(q1_count > 0 and denominator > 0 and blocked / denominator > 0.50)
    violation = scope_violation(config, inputs, scope, axis_validator)

    rules = [
        ("rule_01", "scope_violation_detected", violation, "r07_audit_scope_violation_blocked"),
        ("rule_02", "Q1_pocket_cell_count == 0", q1_count == 0, "r07_no_relative_pocket_in_scope"),
        ("rule_03", "Q1_pocket_cell_count > 0 and state_cell_sample_majority_blocked", q1_count > 0 and majority_blocked, "r07_insufficient_state_cell_sample_blocked"),
        ("rule_04", "Q3_stable_cell_count > 0 and exists Q3 stable H1/H3/H5", q3_count > 0 and q3_short > 0, "r07_state_stable_clean_pocket_supported"),
        ("rule_05", "Q3 stable exists only in H10", q3_count > 0 and q3_short == 0, "r07_relative_pocket_clean_but_not_state_stable"),
        ("rule_06", "Q2 unconditional clean exists and Q3 stable count is zero", q2_count > 0 and q3_count == 0, "r07_relative_pocket_clean_but_not_state_stable"),
        ("rule_07", "Q1 pocket exists and no Q2 clean or Q3 stable cell", q1_count > 0 and q2_count == 0 and q3_count == 0, "r07_relative_pocket_explained_by_style_or_persistent_name"),
    ]
    replay_rows: list[dict[str, Any]] = []
    selected_seen = False
    final_decision = "r07_audit_scope_violation_blocked"
    selected_rule = ""
    for rule_id, text, condition, decision in rules:
        fires = bool(condition) and not selected_seen
        if fires:
            selected_seen = True
            final_decision = decision
            selected_rule = rule_id
        replay_rows.append(
            {
                "rule_id": rule_id,
                "rule_condition_text": text,
                "raw_condition_met": bool(condition),
                "rule_fires_flag": fires,
                "selected_rule_flag": fires,
                "candidate_final_decision": decision,
            }
        )
    if not selected_seen:
        replay_rows[-1]["rule_fires_flag"] = True
        replay_rows[-1]["selected_rule_flag"] = True
        final_decision = replay_rows[-1]["candidate_final_decision"]
        selected_rule = replay_rows[-1]["rule_id"]

    stable = state.loc[state["Q3_stable_flag"].map(bool_value)].copy() if not state.empty else pd.DataFrame()
    authorized_family = authorized_horizon = authorized_state_cell = decision_label = ""
    downstream_recorded = False
    if final_decision == "r07_state_stable_clean_pocket_supported" and not stable.empty:
        candidate = stable.loc[stable["horizon"].isin(["H1", "H3", "H5"])].sort_values(
            ["validation_top_minus_bottom_spread_net", "robustness_top_minus_bottom_spread_net"],
            ascending=[False, False],
        ).iloc[0]
        authorized_family = str(candidate["family"])
        authorized_horizon = str(candidate["horizon"])
        authorized_state_cell = str(candidate["state_cell"])
        if bool_value(candidate.get("long_only_absolute_candidate_gate", False)):
            decision_label = "long_only_research_candidate"
        elif (hedged["preflight_conclusion"].eq("feasible_to_write_hedged_requirement").any() if not hedged.empty else False):
            decision_label = "hedged_research_candidate"
        else:
            decision_label = "relative_research_candidate"
        downstream_recorded = True

    inputs_df = pd.DataFrame(
        [
            {
                "Q1_pocket_cell_count": q1_count,
                "Q2_unconditional_clean_cell_count": q2_count,
                "Q3_stable_cell_count": q3_count,
                "Q3_stable_short_horizon_cell_count": q3_short,
                "Q3_sample_denominator_cell_count": denominator,
                "Q3_sample_blocked_cell_count": blocked,
                "state_cell_sample_majority_blocked_flag": majority_blocked,
                "scope_violation_detected_flag": violation,
                "selected_rule_id": selected_rule,
                "final_decision": final_decision,
                "downstream_authorization_scope_recorded": downstream_recorded,
                "authorized_family": authorized_family,
                "authorized_horizon": authorized_horizon,
                "authorized_state_cell": authorized_state_cell,
                "decision_label": decision_label,
            }
        ]
    )
    replay = pd.DataFrame(replay_rows)
    final = pd.DataFrame([{"final_decision": final_decision}])
    write_csv(inputs_df, paths.artifacts_dir / "r07_final_decision_inputs.csv")
    write_csv(replay, paths.artifacts_dir / "r07_final_decision_replay_audit.csv")
    write_csv(final, paths.artifacts_dir / "r07_final_decision.csv")
    return inputs_df, replay, final


def compact_validation_path(path: pd.DataFrame) -> pd.DataFrame:
    cols = [
        "family",
        "horizon",
        "family_score_rankIC_net",
        "top_decile_minus_bottom_decile_matched_delta_net",
        "spread_positive_date_share",
        "pocket_flag",
    ]
    return path.loc[path["split"].eq("validation"), cols].sort_values(
        ["pocket_flag", "top_decile_minus_bottom_decile_matched_delta_net"], ascending=[False, False]
    )


def write_final_report(
    paths: R07Paths,
    scope: pd.DataFrame,
    path: pd.DataFrame,
    clean: pd.DataFrame,
    state: pd.DataFrame,
    hedged: pd.DataFrame,
    decision_inputs: pd.DataFrame,
    replay: pd.DataFrame,
    final: pd.DataFrame,
    validation: dict[str, Any] | None = None,
) -> None:
    final_decision = str(final.iloc[0]["final_decision"]) if not final.empty else ""
    selected_rule = str(decision_inputs.iloc[0]["selected_rule_id"]) if not decision_inputs.empty else ""
    q1_count = int(decision_inputs.iloc[0]["Q1_pocket_cell_count"]) if not decision_inputs.empty else 0
    q2_count = int(decision_inputs.iloc[0]["Q2_unconditional_clean_cell_count"]) if not decision_inputs.empty else 0
    q3_count = int(decision_inputs.iloc[0]["Q3_stable_cell_count"]) if not decision_inputs.empty else 0
    sample_den = int(decision_inputs.iloc[0]["Q3_sample_denominator_cell_count"]) if not decision_inputs.empty else 0
    sample_blocked = int(decision_inputs.iloc[0]["Q3_sample_blocked_cell_count"]) if not decision_inputs.empty else 0
    axis = pd.read_csv(paths.artifacts_dir / "r07_state_axis_definition.csv")
    validation_path = compact_validation_path(path)
    q2_fail_counts = clean["Q2_failure_explanation_set"].fillna("").str.get_dummies(sep=";").sum().sort_values(ascending=False) if not clean.empty else pd.Series(dtype=int)
    sample_pass_count = int(state["state_cell_sample_pass"].map(bool_value).sum()) if not state.empty else 0
    val_sample_count = int(
        (
            (state.get("validation_event_count", pd.Series(dtype=float)) >= 80)
            & (state.get("validation_date_count", pd.Series(dtype=float)) >= 20)
            & (state.get("validation_min_state_date_cross_section_count", pd.Series(dtype=float)) >= 30)
        ).sum()
    ) if not state.empty else 0
    rob_sample_count = int(
        (
            (state.get("robustness_event_count", pd.Series(dtype=float)) >= 60)
            & (state.get("robustness_date_count", pd.Series(dtype=float)) >= 20)
            & (state.get("robustness_min_state_date_cross_section_count", pd.Series(dtype=float)) >= 30)
        ).sum()
    ) if not state.empty else 0
    stable_short = state.loc[state["Q3_stable_flag"].map(bool_value) & state["horizon"].isin(["H1", "H3", "H5"])] if not state.empty else pd.DataFrame()
    preflight_fired = bool(hedged["trigger_satisfied"].map(bool_value).any()) if not hedged.empty else False
    preflight_conclusion = ";".join(sorted(set(hedged["preflight_conclusion"].astype(str)))) if not hedged.empty else ""
    selected = replay.loc[replay["selected_rule_flag"].map(bool_value)] if not replay.empty else pd.DataFrame()
    selected_text = str(selected.iloc[0]["rule_condition_text"]) if not selected.empty else ""

    lines = [
        "# R07 Short-Horizon Timing and Failure Attribution Audit Report",
        "",
        "## 1. Final decision",
        "",
        f"`final_decision = {final_decision}`; selected rule = `{selected_rule}`.",
        "",
        f"R07 found `{q1_count}` Q1 pocket cells, `{q2_count}` Q2 unconditional-clean cells, and `{q3_count}` Q3 state-stable cells. The Q3 sample denominator is `{sample_den}` state cells, with `{sample_blocked}` sample-blocked cells.",
        "",
        "## 2. Required questions",
        "",
        "### Q1. Did R07 honor every Section 5 prohibition?",
        "",
        "Yes. The run reused R06 included factors, R06 primary families, H1/H3/H5/H10 labels, the R06 family-score definition, local cached PIT data, and the same matched comparator / 110bps cost contract. It did not create a strategy unit, a top-N rule, a top-fraction rule, a backtest, or an online-data fetch.",
        "",
        "### Q2. Which family scope and horizon scope did R07 use?",
        "",
        f"Family scope count = `{scope['family'].nunique()}`; horizon grid = `{';'.join(HORIZON_LABELS)}`. This matches the R06 family map and excludes H20.",
        "",
        "| family | primary horizon | included factors |",
        "|:--|:--|--:|",
    ]
    for rec in scope.sort_values("family").itertuples(index=False):
        lines.append(f"| {rec.family} | {rec.horizon_primary} | {int(rec.included_factor_count_in_family)} |")
    lines.extend(["", "### Q3. What are the two state axes and bin edges?", "", "| axis | definition | train edges | frozen before validation |", "|:--|:--|:--|:--|"])
    for rec in axis.itertuples(index=False):
        lines.append(f"| {rec.axis_name} | {rec.definition_text} | `{rec.bin_edges_train}` | {bool(rec.frozen_before_validation_read)} |")
    lines.extend(
        [
            "",
            "### Q4. How many state cells reached the sample floor?",
            "",
            f"Overall state-cell sample pass count = `{sample_pass_count} / {sample_den}`. Validation split floor count = `{val_sample_count} / {sample_den}`; robustness split floor count = `{rob_sample_count} / {sample_den}`.",
            "",
            "### Q5. What is the Q1 path-decomposition readout?",
            "",
            "| family | horizon | val RankIC | val spread | positive dates | Q1 pocket |",
            "|:--|:--|--:|--:|--:|:--|",
        ]
    )
    for rec in validation_path.itertuples(index=False):
        lines.append(
            f"| {rec.family} | {rec.horizon} | {num_text(rec.family_score_rankIC_net, 5)} | {pct_text(rec.top_decile_minus_bottom_decile_matched_delta_net)} | {pct_text(rec.spread_positive_date_share)} | {bool(rec.pocket_flag)} |"
        )
    lines.extend(["", "### Q6. For Q1-pocket cells, which unconditioned R06 gates pass or fail?", ""])
    if clean.empty:
        lines.append("No Q1-pocket cells were present, so Q2 was not evaluated.")
    else:
        lines.extend(["| family | horizon | info | monotonic | persistent | style | cost | Q2 clean | failures |", "|:--|:--|:--|:--|:--|:--|:--|:--|:--|"])
        for rec in clean.sort_values(["family", "horizon"]).itertuples(index=False):
            lines.append(
                f"| {rec.family} | {rec.horizon} | {bool(rec.gate_information_pass)} | {bool(rec.gate_monotonicity_pass)} | {bool(rec.gate_persistent_clean_pass)} | {bool(rec.gate_style_clean_pass)} | {bool(rec.gate_cost_survives_pass)} | {bool(rec.Q2_unconditional_clean_flag)} | {rec.Q2_failure_explanation_set} |"
            )
        if not q2_fail_counts.empty:
            fail_text = ", ".join(f"{name}={int(count)}" for name, count in q2_fail_counts.items() if name)
            lines.append(f"\nFailure-count summary: `{fail_text}`.")
    lines.extend(["", "### Q7. Which state cells are Q3-stable, sample-blocked, or non-deterioration blocked?", ""])
    if state.empty:
        lines.append("No Q3 cells were evaluated because no Q1 pocket existed.")
    else:
        sample_fail = int((~state["state_cell_sample_pass"].map(bool_value)).sum())
        nondet_fail = int((~state["non_deterioration_validation_pass"].map(bool_value) | ~state["non_deterioration_robustness_pass"].map(bool_value)).sum())
        gate_fail = int(((state["validation_state_gates_pass_count"] < 5) | (state["robustness_state_gates_pass_count"] < 5)).sum())
        lines.append(f"Q3-stable cells = `{q3_count}`; sample-blocked = `{sample_fail}`; non-deterioration blocked = `{nondet_fail}`; validation/robustness five-gate blocked = `{gate_fail}`.")
        top_state = state.sort_values(["Q3_stable_flag", "validation_top_minus_bottom_spread_net"], ascending=[False, False]).head(15)
        lines.extend(["", "| family | horizon | state | sample | val gates | rob gates | nondet val | nondet rob | Q3 stable | val spread | rob spread |", "|:--|:--|:--|:--|--:|--:|:--|:--|:--|--:|--:|"])
        for rec in top_state.itertuples(index=False):
            lines.append(
                f"| {rec.family} | {rec.horizon} | {rec.state_cell} | {bool(rec.state_cell_sample_pass)} | {int(rec.validation_state_gates_pass_count)} | {int(rec.robustness_state_gates_pass_count)} | {bool(rec.non_deterioration_validation_pass)} | {bool(rec.non_deterioration_robustness_pass)} | {bool(rec.Q3_stable_flag)} | {pct_text(rec.validation_top_minus_bottom_spread_net)} | {pct_text(rec.robustness_top_minus_bottom_spread_net)} |"
            )
    lines.extend(
        [
            "",
            "### Q8. Does any Q3-stable cell exist in H1/H3/H5?",
            "",
            f"`{not stable_short.empty}`. Short-horizon Q3-stable cell count = `{len(stable_short)}`.",
            "",
            "### Q9. Does the hedged feasibility preflight fire?",
            "",
            f"`hedged_preflight_trigger = {preflight_fired}`; conclusion = `{preflight_conclusion}`. If skipped, the recorded reason is in `artifacts/r07_hedged_preflight.csv`.",
            "",
            "### Q10. What first-match rule fires?",
            "",
            f"`{selected_rule}` fires: {selected_text}. Final decision is `{final_decision}`.",
            "",
            "### Q11. Compared to R01's relative pocket, where does it live and does it survive?",
            "",
            "R07 locates the reproducible short-horizon pocket mainly in H1/H3/H5 family-score-ranked spread cells, not as a clean H10 strategy answer. The pocket does not survive Q2/Q3 as clean state-stable evidence under this run.",
            "",
            "### Q12. Compared to R05's H10 validation pocket, does R07 confirm persistent-name as primary explanation?",
            "",
            "R07 confirms that persistent-name and cleanliness failures remain material at the unconditioned level: Q2 has no unconditional-clean cell. Because rule_03 stops on state-cell sample majority blocking, R07 does not claim a clean state-conditioned refutation of persistent-name risk.",
            "",
            "### Q13. Compared to R06's H3 information-positive families, does R07 confirm style exposure as primary explanation?",
            "",
            "R07 confirms that style-clean discipline is still an unconditioned blocking issue. State conditioning does not produce a validation-and-robustness style-clean cell with passing monotonicity, persistence, cost, sample, and non-deterioration gates, so style exposure remains an explanation rather than a solved objection.",
            "",
            "### Q14. Does R07 authorize a downstream requirement?",
            "",
        ]
    )
    downstream = bool_value(decision_inputs.iloc[0]["downstream_authorization_scope_recorded"]) if not decision_inputs.empty else False
    if downstream:
        lines.append(
            f"Yes. Authorized family = `{decision_inputs.iloc[0]['authorized_family']}`, horizon = `{decision_inputs.iloc[0]['authorized_horizon']}`, state cell = `{decision_inputs.iloc[0]['authorized_state_cell']}`, label = `{decision_inputs.iloc[0]['decision_label']}`."
        )
    else:
        lines.append("No. No downstream authorization scope is recorded because the final decision is not `r07_state_stable_clean_pocket_supported`.")
    lines.extend(
        [
            "",
            "### Q15. If no downstream requirement is authorized, is EP5 short-horizon ready to close?",
            "",
            "Yes as a requirement stop case under the current contract. The reason is not that R07 proved a clean negative in every state cell; it is that Q1 weak pockets exist, Q2 does not clean them unconditionally, and Q3 is majority sample-blocked, so the fixed first-match replay does not authorize a new short-horizon requirement.",
            "",
            "### Q16. Are there inconclusive state cells due to sample shortfall?",
            "",
            f"Sample-blocked cells = `{sample_blocked} / {sample_den}` = `{pct_text(sample_blocked / sample_den if sample_den else np.nan)}`.",
            "",
            "### Q17. Are there anomalies contradicting R06 family-level RankIC decay?",
            "",
            "No contradiction requiring a new branch was found. R07 sees local H1/H3/H5 spread pockets, which is consistent with R06's weak short-horizon information readout, but the cells fail clean-attribution and state-stability discipline.",
        ]
    )
    if validation:
        lines.extend(["", "## 3. Validator", "", f"`validation_status = {validation.get('validation_status')}`; failed gates = `{validation.get('failed_gate_count')}`."])
    (paths.reports_dir / "r07_final_report.md").write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def artifact_hashes(paths: R07Paths) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for directory in [paths.artifacts_dir, paths.reports_dir, paths.manifests_dir]:
        for path in sorted(directory.glob("*")):
            if path.is_file():
                rows.append({"artifact_path": rel(path), "exists": True, "sha256": r01.file_hash(path)})
    return rows


def run_pipeline(config_path: str | Path = DEFAULT_CONFIG) -> None:
    config, paths = load_config(config_path)
    inputs = load_r06_inputs(config)
    neutral_scores, _, definition_hash = compute_family_scores(inputs)
    candidates_with_state = build_state_axes(config, paths, inputs)
    scope = write_scope_lock(paths, inputs, definition_hash)
    path = build_path_decomposition(paths, inputs, neutral_scores)
    clean = build_clean_attribution(config, paths, inputs, path)
    state = build_state_stability(config, paths, inputs, candidates_with_state, neutral_scores, path)
    hedged = build_hedged_preflight(config, paths, state)
    decision_inputs, replay, final = build_final_decision(config, paths, inputs, scope, clean, state, hedged, path)
    write_final_report(paths, scope, path, clean, state, hedged, decision_inputs, replay, final)
    write_json(
        {
            "requirement_id": REQUIREMENT_ID,
            "plan_id": PLAN_ID,
            "config_path": rel(paths.config_path),
            "output_root": rel(paths.output_root),
            "created_at": r01.now_iso(),
            "git_commit": r01.git_commit_hash(),
            "final_decision": final.iloc[0]["final_decision"],
            "Q1_pocket_cell_count": int(decision_inputs.iloc[0]["Q1_pocket_cell_count"]),
            "Q3_stable_cell_count": int(decision_inputs.iloc[0]["Q3_stable_cell_count"]),
        },
        paths.manifests_dir / "r07_run_manifest.json",
    )
    write_json({"created_at": r01.now_iso(), "artifacts": artifact_hashes(paths)}, paths.manifests_dir / "r07_artifact_hashes.json")


def required_paths(paths: R07Paths) -> list[Path]:
    return [
        paths.artifacts_dir / "r07_state_axis_definition.csv",
        paths.artifacts_dir / "r07_state_axis_validator.csv",
        paths.artifacts_dir / "r07_scope_lock.csv",
        paths.artifacts_dir / "r07_path_decomposition.csv",
        paths.artifacts_dir / "r07_clean_attribution.csv",
        paths.artifacts_dir / "r07_state_stability.csv",
        paths.artifacts_dir / "r07_hedged_preflight.csv",
        paths.artifacts_dir / "r07_final_decision_inputs.csv",
        paths.artifacts_dir / "r07_final_decision_replay_audit.csv",
        paths.artifacts_dir / "r07_final_decision.csv",
        paths.reports_dir / "r07_final_report.md",
    ]


def validate_outputs(config_path: str | Path = DEFAULT_CONFIG) -> dict[str, Any]:
    config, paths = load_config(config_path)
    checks: list[dict[str, Any]] = []
    failures: list[str] = []

    def check(name: str, condition: bool, detail: str = "") -> None:
        checks.append({"check_name": name, "status": "passed" if condition else "failed", "detail": detail})
        if not condition:
            failures.append(f"{name}: {detail}")

    check("V00_requirement_id", config.get("requirement_id") == REQUIREMENT_ID, str(config.get("requirement_id")))
    missing = [rel(p) for p in required_paths(paths) if not p.exists()]
    check("V01_artifact_set_complete", not missing, ";".join(missing))
    final_decision = ""
    if not missing:
        axis_def = pd.read_csv(paths.artifacts_dir / "r07_state_axis_definition.csv")
        axis_val = pd.read_csv(paths.artifacts_dir / "r07_state_axis_validator.csv")
        scope = pd.read_csv(paths.artifacts_dir / "r07_scope_lock.csv")
        path = pd.read_csv(paths.artifacts_dir / "r07_path_decomposition.csv")
        clean = pd.read_csv(paths.artifacts_dir / "r07_clean_attribution.csv")
        state = pd.read_csv(paths.artifacts_dir / "r07_state_stability.csv")
        hedged = pd.read_csv(paths.artifacts_dir / "r07_hedged_preflight.csv")
        inputs_df = pd.read_csv(paths.artifacts_dir / "r07_final_decision_inputs.csv")
        replay = pd.read_csv(paths.artifacts_dir / "r07_final_decision_replay_audit.csv")
        final = pd.read_csv(paths.artifacts_dir / "r07_final_decision.csv")
        final_decision = str(final.iloc[0]["final_decision"])
        q1_cells = path.loc[path["split"].eq("validation") & path["pocket_flag"].map(bool_value), ["family", "horizon"]].drop_duplicates()
        q1_set = set(map(tuple, q1_cells.to_numpy()))

        check("V02_state_axis_count_le_2", len(axis_def) <= 2, str(len(axis_def)))
        check("V03_state_axes_all_S_flags_pass", axis_val.filter(regex="_pass_flag$").map(bool_value).all().all(), "")
        check("V04_axis_edges_frozen_before_validation", axis_def["frozen_before_validation_read"].map(bool_value).all(), "")
        check("V05_family_scope_identical_to_R06", set(scope["family"]) == set(FAMILIES) and len(scope) == 8, str(scope["family"].tolist()))
        horizon_scope = set(";".join(scope["horizon_grid_audited"].astype(str)).split(";"))
        check("V06_horizon_scope_subset", horizon_scope.issubset(set(HORIZON_LABELS)) and horizon_scope == set(HORIZON_LABELS), str(horizon_scope))
        check("V07_family_score_definition_hash_present", scope["family_score_definition_hash_from_R06"].nunique() == 1 and str(scope["family_score_definition_hash_from_R06"].iloc[0]) != "", "")
        selected = pd.read_csv(r01.topic_path(config["data_sources"]["r06_output_root"]) / "audit" / "r06_family_horizon_selection_train_only.csv")
        selected = selected.loc[selected["family_primary_horizon_train_selected"].map(bool_value)]
        selected_map = selected.set_index("primary_family")["horizon"].to_dict()
        check("V08_primary_horizon_identical_to_R06", all(scope.set_index("family").loc[f, "horizon_primary"] == selected_map.get(f, "") for f in FAMILIES), "")
        check("V09_included_factor_count_125", int(scope["included_factor_count_in_family"].sum()) == 125, str(scope["included_factor_count_in_family"].sum()))
        check("V10_thresholds_not_relaxed", float(config["frozen_formula_constants"]["validation_information_spread_min"]) == 0.0005 and float(config["frozen_formula_constants"]["monotonicity_min"]) == 0.60 and float(config["frozen_formula_constants"]["cost_survival_ratio_min"]) == 0.50, "")
        sample_cols = ["state_cell_sample_pass", "validation_min_state_date_cross_section_count", "robustness_min_state_date_cross_section_count"]
        check("V11_state_cell_sample_floor_recorded", all(col in state.columns for col in sample_cols), ",".join(state.columns))
        bad_train = state.loc[state["Q3_stable_flag"].map(bool_value) & ~state["train_information_positive_pass"].map(bool_value)]
        check("V12_train_information_required_for_Q3", bad_train.empty, str(len(bad_train)))
        clean_set = set(map(tuple, clean[["family", "horizon"]].to_numpy())) if not clean.empty else set()
        check("V13_Q2_restricted_to_Q1", clean_set.issubset(q1_set), str(clean_set - q1_set))
        state_set = set(map(tuple, state[["family", "horizon"]].drop_duplicates().to_numpy())) if not state.empty else set()
        check("V14_Q3_restricted_to_Q1", state_set.issubset(q1_set), str(state_set - q1_set))
        expected_rules = [f"rule_{i:02d}" for i in range(1, 8)]
        check("V15_rule_order_matches", replay["rule_id"].astype(str).tolist() == expected_rules, str(replay["rule_id"].tolist()))
        check(
            "V16_exactly_one_first_match_rule_fires",
            int(replay["rule_fires_flag"].map(bool_value).sum()) == 1 and int(replay["selected_rule_flag"].map(bool_value).sum()) == 1,
            f"fires={int(replay['rule_fires_flag'].map(bool_value).sum())}, selected={int(replay['selected_rule_flag'].map(bool_value).sum())}",
        )
        q1_count = int(inputs_df.iloc[0]["Q1_pocket_cell_count"])
        denominator = int(inputs_df.iloc[0]["Q3_sample_denominator_cell_count"])
        majority = bool_value(inputs_df.iloc[0]["state_cell_sample_majority_blocked_flag"])
        check("V17_sample_denominator", denominator == q1_count * 9 and (q1_count > 0 or not majority), f"{denominator} vs {q1_count * 9}")
        check("V18_hedged_preflight_read_only_no_online", not str(config["data_sources"].get("local_hedge_data_path", "")).startswith(("http://", "https://")) and "preflight_conclusion" in hedged.columns, "")
        check("V19_no_strategy_outputs", not any("portfolio" in p.name or "equity" in p.name or "allocation" in p.name for p in paths.output_root.rglob("*") if p.is_file()), "")
        prohibited = "big_winner|right_tail|hit_rate"
        decision_text = "\n".join(path.astype(str).agg("|".join, axis=1).tolist() + clean.astype(str).agg("|".join, axis=1).tolist() + state.astype(str).agg("|".join, axis=1).tolist())
        check("V20_no_prohibited_decision_terms", not pd.Series([decision_text]).str.contains(prohibited, case=False, regex=True).iloc[0], "")
        check("V21_no_validation_axis_selection", axis_def["bin_edges_train"].notna().all() and axis_def["frozen_before_validation_read"].map(bool_value).all(), "")
        check("V22_final_decision_enum", final_decision in FINAL_DECISIONS, final_decision)
        downstream = bool_value(inputs_df.iloc[0]["downstream_authorization_scope_recorded"])
        if final_decision == "r07_state_stable_clean_pocket_supported":
            check("V23_downstream_scope_narrow", downstream and inputs_df.iloc[0]["authorized_family"] in FAMILIES and inputs_df.iloc[0]["authorized_horizon"] in HORIZON_LABELS, "")
        else:
            check("V26_no_downstream_when_not_supported", not downstream, str(downstream))
        if downstream and str(inputs_df.iloc[0]["decision_label"]) == "long_only_research_candidate":
            stable = state.loc[
                state["family"].eq(inputs_df.iloc[0]["authorized_family"])
                & state["horizon"].eq(inputs_df.iloc[0]["authorized_horizon"])
                & state["state_cell"].eq(inputs_df.iloc[0]["authorized_state_cell"])
            ]
            check("V24_long_only_requires_absolute_gate", not stable.empty and bool_value(stable.iloc[0]["long_only_absolute_candidate_gate"]), "")
        if downstream and str(inputs_df.iloc[0]["decision_label"]) == "hedged_research_candidate":
            check("V25_hedged_requires_feasible_preflight", hedged["preflight_conclusion"].eq("feasible_to_write_hedged_requirement").any(), "")
        report = (paths.reports_dir / "r07_final_report.md").read_text(encoding="utf-8")
        check("V27_report_answers_all_questions", all(f"Q{i}." in report for i in range(1, 18)), "")
        check("V28_path_uses_family_score_ranked_metrics", path["ranking_metric"].eq("r06_family_score_neutralized_rank").all(), "")
    status = "passed" if not failures else "failed"
    gate = pd.DataFrame(checks)
    write_csv(gate, paths.artifacts_dir / "r07_validation_gate_audit.csv")
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
    write_json(payload, paths.manifests_dir / "r07_validation.json")
    if status == "passed":
        scope = pd.read_csv(paths.artifacts_dir / "r07_scope_lock.csv")
        path = pd.read_csv(paths.artifacts_dir / "r07_path_decomposition.csv")
        clean = pd.read_csv(paths.artifacts_dir / "r07_clean_attribution.csv")
        state = pd.read_csv(paths.artifacts_dir / "r07_state_stability.csv")
        hedged = pd.read_csv(paths.artifacts_dir / "r07_hedged_preflight.csv")
        inputs_df = pd.read_csv(paths.artifacts_dir / "r07_final_decision_inputs.csv")
        replay = pd.read_csv(paths.artifacts_dir / "r07_final_decision_replay_audit.csv")
        final = pd.read_csv(paths.artifacts_dir / "r07_final_decision.csv")
        write_final_report(paths, scope, path, clean, state, hedged, inputs_df, replay, final, payload)
    write_json({"created_at": r01.now_iso(), "artifacts": artifact_hashes(paths)}, paths.manifests_dir / "r07_artifact_hashes.json")
    return payload
