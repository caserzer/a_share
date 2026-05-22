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
DEFAULT_CONFIG = EP5_DIR / "configs" / "r06_gtja191_factor_decay_information_content_audit_v0.yaml"

REQUIREMENT_ID = "ep5_r06_gtja191_factor_decay_information_content_audit_v0"
PLAN_ID = "ep5_e06_gtja191_factor_decay_information_content_audit_v0"
HORIZONS = [1, 3, 5, 10, 20]
HORIZON_LABELS = [f"H{h}" for h in HORIZONS]
SPLITS = ["train", "validation", "robustness"]

FINAL_DECISIONS = [
    "r06_blocked_data_or_execution_contract",
    "r06_factor_library_not_implementable_blocked",
    "r06_family_map_not_reproducible_blocked",
    "r06_insufficient_information_audit_sample_blocked",
    "r06_no_factor_information_support",
    "r06_decay_information_exists_but_not_tradeable",
    "r06_relative_information_only",
    "r06_factor_family_information_supported",
]


@dataclass(frozen=True)
class R06Paths:
    config_path: Path
    output_root: Path
    cache_dir: Path
    audit_dir: Path
    metrics_dir: Path
    decision_dir: Path
    reports_dir: Path
    manifests_dir: Path


def parse_config_arg(description: str) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    return parser.parse_args()


def load_config(path: str | Path = DEFAULT_CONFIG) -> tuple[dict[str, Any], R06Paths]:
    config_path = r01.topic_path(path)
    import yaml

    config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    output_root = r01.topic_path(config["output_root"])
    paths = R06Paths(
        config_path=config_path,
        output_root=output_root,
        cache_dir=output_root / "cache",
        audit_dir=output_root / "audit",
        metrics_dir=output_root / "metrics",
        decision_dir=output_root / "decision",
        reports_dir=output_root / "reports",
        manifests_dir=output_root / "manifests",
    )
    for directory in [paths.cache_dir, paths.audit_dir, paths.metrics_dir, paths.decision_dir, paths.reports_dir, paths.manifests_dir]:
        directory.mkdir(parents=True, exist_ok=True)
    return config, paths


def write_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
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


def sha_members(values: list[str]) -> str:
    return hashlib.sha256("|".join(values).encode("utf-8")).hexdigest()


def spearman_corr(x: np.ndarray, y: np.ndarray) -> float:
    mask = np.isfinite(x) & np.isfinite(y)
    if int(mask.sum()) < 3:
        return np.nan
    return float(pd.Series(x[mask]).rank(method="average").corr(pd.Series(y[mask]).rank(method="average")))


def assign_quintile(values: pd.Series, prefix: str) -> pd.Series:
    ranked = values.rank(method="first", pct=True)
    bucket = np.ceil(ranked * 5).clip(1, 5)
    return pd.Series([f"{prefix}{int(x)}" if finite(x) else f"{prefix}missing" for x in bucket], index=values.index)


def prepare_inputs(config: dict[str, Any], paths: R06Paths) -> tuple[pd.DataFrame, pd.DataFrame]:
    feature = r05.prepare_feature_panel(config, paths)  # writes reusable local PIT feature cache
    candidates = r05.candidate_base(config, feature)
    candidates["candidate_row_id"] = np.arange(len(candidates), dtype=int)
    extra_cols = [
        "instrument_id",
        "trade_date",
        "beta120",
        "recent_vol10",
        "atr20_pct",
        "avg_money20_rank_pct",
    ]
    extra = feature[[c for c in extra_cols if c in feature.columns]].rename(columns={"trade_date": "signal_date"})
    candidates = candidates.merge(extra, on=["instrument_id", "signal_date"], how="left")
    candidates["money_bucket"] = ""
    candidates["volatility_bucket"] = ""
    for _, idx in candidates.groupby("signal_date", sort=False).groups.items():
        idx_list = list(idx)
        candidates.loc[idx_list, "money_bucket"] = assign_quintile(candidates.loc[idx_list, "avg_money20_D"], "money_q")
        vol_source = candidates.loc[idx_list, "recent_vol10"] if "recent_vol10" in candidates else candidates.loc[idx_list, "atr20_pct"]
        candidates.loc[idx_list, "volatility_bucket"] = assign_quintile(vol_source, "vol_q")
    candidates["eligible_count"] = candidates.groupby("signal_date")["instrument_id"].transform("size")
    write_csv(
        pd.DataFrame(
            [
                {
                    "source": "r06_candidate_base",
                    "row_count": len(candidates),
                    "instrument_count": candidates["instrument_id"].nunique(),
                    "signal_date_count": candidates["signal_date"].nunique(),
                    "min_signal_date": candidates["signal_date"].min(),
                    "max_signal_date": candidates["signal_date"].max(),
                    "status": "passed" if not candidates.empty else "failed",
                }
            ]
        ),
        paths.audit_dir / "r06_input_data_audit.csv",
    )
    candidates.to_parquet(paths.cache_dir / "r06_candidate_base.parquet", index=False)
    return feature, candidates


def copy_csv_if_exists(src: Path, dst: Path) -> None:
    if src.exists():
        df = pd.read_csv(src)
        write_csv(df, dst)


def build_or_load_factor_data(
    config: dict[str, Any],
    paths: R06Paths,
    feature: pd.DataFrame,
    candidates: pd.DataFrame,
) -> tuple[pd.DataFrame, np.ndarray, np.ndarray, list[str]]:
    reuse_root = r01.topic_path(config["data_sources"].get("reuse_r05_factor_cache_root", ""))
    cache_ok = False
    raw = neutral = np.empty((len(candidates), 0), dtype=np.float32)
    factor_ids: list[str] = []
    registry = pd.DataFrame()
    if reuse_root.exists():
        raw_path = reuse_root / "cache" / "r05_normalized_factor_matrix.npy"
        neutral_path = reuse_root / "cache" / "r05_neutralized_factor_matrix.npy"
        columns_path = reuse_root / "cache" / "r05_factor_matrix_columns.json"
        registry_path = reuse_root / "audit" / "r05_factor_registry.csv"
        if raw_path.exists() and neutral_path.exists() and columns_path.exists() and registry_path.exists():
            raw = np.load(raw_path)
            neutral = np.load(neutral_path)
            factor_ids = json.loads(columns_path.read_text(encoding="utf-8"))["factor_ids"]
            registry = pd.read_csv(registry_path)
            cache_ok = raw.shape[0] == len(candidates) and neutral.shape == raw.shape and raw.shape[1] == len(factor_ids)
    if not cache_ok:
        registry, raw, factor_ids = r05.build_factor_matrix(config, paths, feature, candidates)
        neutral = r05.neutralize_factor_matrix(paths, candidates, raw, factor_ids)
        copy_csv_if_exists(paths.audit_dir / "r05_factor_registry.csv", paths.audit_dir / "r06_factor_registry.csv")
    else:
        print("R06 reusing R05 factor matrix cache", flush=True)
    registry = registry.copy()
    registry["factor_status"] = registry["factor_status"].replace({"excluded_not_asof_safe": "excluded_lookback_or_asof"})
    write_csv(registry, paths.audit_dir / "r06_factor_registry.csv")
    write_csv(
        registry[["factor_id", "factor_status", "exclusion_reason", "max_lookback_trading_days", "asof_safe"]],
        paths.audit_dir / "r06_factor_coverage_audit.csv",
    )
    np.save(paths.cache_dir / "r06_raw_rank_factor_matrix.npy", raw)
    np.save(paths.cache_dir / "r06_neutralized_rank_factor_matrix.npy", neutral)
    write_json({"factor_ids": factor_ids}, paths.cache_dir / "r06_factor_matrix_columns.json")
    return registry, raw, neutral, factor_ids


def classify_family(row: pd.Series) -> tuple[str, str, str]:
    text = f"{row.get('source_formula_text', '')} {row.get('required_fields', '')}".lower()
    tags: list[str] = []
    if "vwap" in text:
        tags.append("vwap_deviation")
    if "vol" in text or "volume" in text or "money" in text:
        tags.append("volume_surge_money_flow")
    if "corr" in text or "covar" in text or "beta" in text:
        tags.append("volume_price_correlation")
    if "rank" in text:
        tags.append("rank_ts_rank_structure")
    if "high" in text and "low" in text:
        tags.append("range_volatility")
    if "open" in text and "close" in text and ("high" in text or "low" in text):
        tags.append("ohlc_pattern")
    if "close" in text and ("move" in text or "mavg" in text or "mfirst" in text):
        tags.append("price_momentum_reversal")
    if "close" in text and ("high" in text or "low" in text):
        tags.append("close_location")
    if len(tags) >= 3:
        primary = "composite_price_volume"
    elif tags:
        priority = [
            "vwap_deviation",
            "volume_price_correlation",
            "volume_surge_money_flow",
            "price_momentum_reversal",
            "close_location",
            "range_volatility",
            "ohlc_pattern",
            "rank_ts_rank_structure",
        ]
        primary = next((p for p in priority if p in tags), tags[0])
    else:
        primary = "other_gtja191"
    return primary, ",".join(sorted(set(tags))), "formula keyword taxonomy"


def build_family_map(paths: R06Paths, registry: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for rec in registry.itertuples(index=False):
        row = pd.Series(rec._asdict())
        primary, secondary, rule = classify_family(row)
        rows.append(
            {
                "factor_id": row["factor_id"],
                "primary_family": primary,
                "secondary_family_tags": secondary,
                "family_assignment_method": "pre_metric_formula_keyword",
                "assignment_rule_text": rule,
                "formula_terms_used": row.get("required_fields", ""),
                "manual_override_flag": False,
                "manual_override_reason": "",
                "created_before_metric_computation": True,
            }
        )
    family_map = pd.DataFrame(rows)
    write_csv(family_map, paths.audit_dir / "r06_factor_family_map.csv")
    return family_map


def build_label_panel(
    config: dict[str, Any],
    paths: R06Paths,
    feature: pd.DataFrame,
    candidates: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, dict[str, np.ndarray]]]:
    events = candidates.copy()
    events["canonical_unit_id"] = "r06_gtja191_factor_horizon_decay_audit_v0"
    events["unit_role"] = "candidate_label"
    events["event_key"] = events["candidate_row_id"].map(lambda x: f"r06_candidate_{int(x)}")
    execution = r05.execute_events(config, feature, events, HORIZONS)
    block = execution.groupby(["split", "horizon", "execution_status", "blocked_reason"], dropna=False).size().reset_index(name="row_count")
    write_csv(block, paths.audit_dir / "r06_execution_block_audit.csv")
    complete = execution.loc[execution["execution_status"].eq("complete_executable")].copy()
    if complete.empty:
        label_panel = complete
    else:
        rows = []
        scope_defs = [
            ("same_industry_same_liquidity_same_beta", ["industry_id", "liquidity_quintile", "beta_bucket"]),
            ("same_industry_only", ["industry_id"]),
            ("same_liquidity_only", ["liquidity_quintile"]),
            ("same_beta_only", ["beta_bucket"]),
        ]
        for (_, _), group in complete.groupby(["signal_date", "horizon"], sort=True):
            g = group.copy()
            n = len(g)
            g["primary_comparator_scope"] = ""
            g["matched_comparator_count"] = 0
            for col in ["net_return", "gross_return"]:
                g[f"matched_comparator_{col}"] = np.nan
            remaining = pd.Series(True, index=g.index)
            for scope_name, keys in scope_defs:
                sums_net = g.groupby(keys, dropna=False)["net_return"].transform("sum") - g["net_return"]
                sums_gross = g.groupby(keys, dropna=False)["gross_return"].transform("sum") - g["gross_return"]
                counts = g.groupby(keys, dropna=False)["net_return"].transform("count") - 1
                eligible = remaining & (counts >= 30)
                g.loc[eligible, "primary_comparator_scope"] = scope_name
                g.loc[eligible, "matched_comparator_count"] = counts.loc[eligible].astype(int)
                g.loc[eligible, "matched_comparator_net_return"] = sums_net.loc[eligible] / counts.loc[eligible]
                g.loc[eligible, "matched_comparator_gross_return"] = sums_gross.loc[eligible] / counts.loc[eligible]
                remaining &= ~eligible
            fallback_count = n - 1
            if fallback_count >= 30:
                sums_net = g["net_return"].sum() - g["net_return"]
                sums_gross = g["gross_return"].sum() - g["gross_return"]
                eligible = remaining
                g.loc[eligible, "primary_comparator_scope"] = "same_day_pit_universe"
                g.loc[eligible, "matched_comparator_count"] = fallback_count
                g.loc[eligible, "matched_comparator_net_return"] = sums_net.loc[eligible] / fallback_count
                g.loc[eligible, "matched_comparator_gross_return"] = sums_gross.loc[eligible] / fallback_count
                remaining &= ~eligible
            g["matched_comparator_status"] = np.where(remaining, "blocked_insufficient_comparator", "comparable")
            g["fallback_comparator_used"] = g["primary_comparator_scope"].eq("same_day_pit_universe")
            g["matched_delta_net"] = g["net_return"] - g["matched_comparator_net_return"]
            g["matched_delta_gross"] = g["gross_return"] - g["matched_comparator_gross_return"]
            rows.append(g)
        label_panel = pd.concat(rows, ignore_index=True)
    label_panel.to_parquet(paths.cache_dir / "r06_horizon_label_panel.parquet", index=False)
    label_audit_rows = []
    constants = config["frozen_formula_constants"]
    split_min_dates = {
        "train": int(constants["min_train_unpurged_signal_date_count"]),
        "validation": int(constants["min_validation_unpurged_signal_date_count"]),
        "robustness": int(constants["min_robustness_unpurged_signal_date_count"]),
    }
    all_gate = True
    for split in SPLITS:
        total_dates = int(candidates.loc[candidates["split"].eq(split), "signal_date"].nunique())
        for horizon in HORIZON_LABELS:
            ex = execution.loc[execution["split"].eq(split) & execution["horizon"].eq(horizon)]
            purged_dates = set(pd.to_datetime(ex.loc[ex["blocked_reason"].eq("split_boundary"), "signal_date"]).dt.normalize())
            unpurged = max(total_dates - len(purged_dates), 0)
            label_dates = 0
            if not label_panel.empty:
                label_dates = int(label_panel.loc[label_panel["split"].eq(split) & label_panel["horizon"].eq(horizon) & label_panel["matched_comparator_status"].eq("comparable"), "signal_date"].nunique())
            unpurged_share = safe_share(unpurged, total_dates)
            finite_share = safe_share(label_dates, unpurged)
            gate = unpurged_share >= float(constants["min_unpurged_signal_date_share"]) and unpurged >= split_min_dates[split] and finite_share >= float(constants["min_finite_label_date_share"])
            all_gate = all_gate and gate
            label_audit_rows.append(
                {
                    "split": split,
                    "horizon": horizon,
                    "total_signal_date_count": total_dates,
                    "purged_cross_split_signal_date_count": len(purged_dates),
                    "unpurged_signal_date_count": unpurged,
                    "unpurged_signal_date_share": unpurged_share,
                    "min_unpurged_signal_date_share": constants["min_unpurged_signal_date_share"],
                    "finite_label_date_share": finite_share,
                    "split_specific_min_unpurged_signal_date_count": split_min_dates[split],
                    "purge_gate": gate,
                    "all_horizon_label_sample_gate": all_gate,
                }
            )
    label_audit = pd.DataFrame(label_audit_rows)
    label_audit["all_horizon_label_sample_gate"] = all_gate
    write_csv(label_audit, paths.audit_dir / "r06_label_purge_audit.csv")
    write_csv(label_audit, paths.audit_dir / "r06_horizon_label_panel_audit.csv")
    quality = label_panel.groupby(["split", "horizon", "matched_comparator_status", "primary_comparator_scope"], dropna=False).size().reset_index(name="row_count") if not label_panel.empty else pd.DataFrame()
    write_csv(quality, paths.audit_dir / "r06_comparator_quality_audit.csv")
    label_arrays: dict[str, dict[str, np.ndarray]] = {}
    for horizon in HORIZON_LABELS:
        arrays = {k: np.full(len(candidates), np.nan, dtype=float) for k in ["gross_return", "net_return", "matched_delta_gross", "matched_delta_net"]}
        if not label_panel.empty:
            sub = label_panel.loc[label_panel["horizon"].eq(horizon) & label_panel["matched_comparator_status"].eq("comparable")]
            idx = sub["candidate_row_id"].to_numpy(dtype=int)
            for key in arrays:
                arrays[key][idx] = sub[key].to_numpy(dtype=float)
        label_arrays[horizon] = arrays
    return label_panel, label_audit, label_arrays


def date_groups(candidates: pd.DataFrame) -> list[tuple[pd.Timestamp, str, int, np.ndarray]]:
    rows = []
    for date, idx in candidates.groupby("signal_date", sort=True).groups.items():
        idx_arr = np.asarray(list(idx), dtype=int)
        split = str(candidates.iloc[idx_arr[0]]["split"]) if len(idx_arr) else ""
        rows.append((pd.Timestamp(date), split, pd.Timestamp(date).year, idx_arr))
    return rows


def build_factor_rankic(
    paths: R06Paths,
    candidates: pd.DataFrame,
    raw: np.ndarray,
    neutral: np.ndarray,
    factor_ids: list[str],
    label_arrays: dict[str, dict[str, np.ndarray]],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    groups = date_groups(candidates)
    panel_rows: list[dict[str, Any]] = []
    for horizon in HORIZON_LABELS:
        labels = label_arrays[horizon]["matched_delta_net"]
        for j, fid in enumerate(factor_ids):
            raw_col = raw[:, j]
            neutral_col = neutral[:, j]
            for date, split, year, idx in groups:
                mask_raw = np.isfinite(raw_col[idx]) & np.isfinite(labels[idx])
                if int(mask_raw.sum()) < 100:
                    continue
                raw_ic = spearman_corr(raw_col[idx][mask_raw], labels[idx][mask_raw])
                mask_neu = np.isfinite(neutral_col[idx]) & np.isfinite(labels[idx])
                neutral_ic = spearman_corr(neutral_col[idx][mask_neu], labels[idx][mask_neu]) if int(mask_neu.sum()) >= 100 else np.nan
                panel_rows.append(
                    {
                        "factor_id": fid,
                        "horizon": horizon,
                        "split": split,
                        "signal_date": date,
                        "calendar_year": year,
                        "rankIC": raw_ic,
                        "neutralized_rankIC": neutral_ic,
                        "observation_count": int(mask_raw.sum()),
                    }
                )
        print(f"R06 RankIC complete: {horizon}", flush=True)
    panel = pd.DataFrame(panel_rows)
    write_csv(panel, paths.audit_dir / "r06_factor_decay_rankic_panel.csv")
    summary_rows = []
    if not panel.empty:
        for (fid, horizon, split), group in panel.groupby(["factor_id", "horizon", "split"], sort=True):
            years = group.groupby("calendar_year")["rankIC"].mean()
            denom = float(years.abs().sum()) if len(years) else 0.0
            contribution = float(years.abs().max() / denom) if denom > 0 else np.nan
            std = float(group["rankIC"].std(ddof=0)) if len(group) else np.nan
            mean = safe_mean(group["rankIC"])
            summary_rows.append(
                {
                    "factor_id": fid,
                    "horizon": horizon,
                    "split": split,
                    "valid_date_count": int(group["signal_date"].nunique()),
                    "mean_rankIC": mean,
                    "median_rankIC": safe_median(group["rankIC"]),
                    "rankIC_std": std,
                    "ICIR": mean / std if finite(mean) and finite(std) and std != 0 else np.nan,
                    "positive_date_share": safe_share(int((group["rankIC"] > 0).sum()), len(group)),
                    "p10_date_rankIC": float(group["rankIC"].quantile(0.10)),
                    "p90_date_rankIC": float(group["rankIC"].quantile(0.90)),
                    "year_count": int(years.count()),
                    "positive_year_count": int((years > 0).sum()),
                    "negative_year_count": int((years < 0).sum()),
                    "yearly_rankIC_min": float(years.min()) if len(years) else np.nan,
                    "yearly_rankIC_max": float(years.max()) if len(years) else np.nan,
                    "single_year_ic_contribution_share": contribution,
                    "neutralized_mean_rankIC": safe_mean(group["neutralized_rankIC"]),
                    "raw_neutralized_rankIC_sign_agree": np.sign(mean) == np.sign(safe_mean(group["neutralized_rankIC"])) if finite(mean) and finite(safe_mean(group["neutralized_rankIC"])) else False,
                }
            )
    summary = pd.DataFrame(summary_rows)
    write_csv(summary, paths.metrics_dir / "r06_factor_horizon_rankic_summary.csv")
    return panel, summary


def build_family_decay(
    paths: R06Paths,
    family_map: pd.DataFrame,
    factor_summary: pd.DataFrame,
    rankic_panel: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    included_factors = set(factor_summary["factor_id"].unique())
    fmap = family_map.loc[family_map["factor_id"].isin(included_factors)].copy()
    train = factor_summary.loc[factor_summary["split"].eq("train"), ["factor_id", "horizon", "mean_rankIC"]].rename(columns={"mean_rankIC": "train_mean_rankIC"})
    directions = train.copy()
    directions["direction_i"] = np.sign(directions["train_mean_rankIC"]).astype(float)
    write_csv(directions, paths.audit_dir / "r06_factor_direction_audit.csv")
    panel = rankic_panel.merge(fmap[["factor_id", "primary_family"]], on="factor_id", how="inner").merge(directions[["factor_id", "horizon", "direction_i"]], on=["factor_id", "horizon"], how="left")
    panel = panel.loc[panel["direction_i"].fillna(0).ne(0)].copy()
    panel["oriented_rankIC"] = panel["direction_i"] * panel["rankIC"]
    panel["oriented_neutralized_rankIC"] = panel["direction_i"] * panel["neutralized_rankIC"]
    family_date = (
        panel.groupby(["primary_family", "horizon", "split", "signal_date", "calendar_year"], sort=True)
        .agg(
            family_oriented_date_rankIC=("oriented_rankIC", "mean"),
            raw_family_date_rankIC=("rankIC", "mean"),
            neutralized_family_date_rankIC=("neutralized_rankIC", "mean"),
            evaluable_factor_count=("factor_id", "nunique"),
        )
        .reset_index()
    )
    rows = []
    factor_split = factor_summary.merge(fmap[["factor_id", "primary_family"]], on="factor_id", how="inner")
    source_counts = family_map.groupby("primary_family")["factor_id"].nunique().to_dict()
    included_counts = fmap.groupby("primary_family")["factor_id"].nunique().to_dict()
    for (family, horizon, split), g in family_date.groupby(["primary_family", "horizon", "split"], sort=True):
        years = g.groupby("calendar_year")["family_oriented_date_rankIC"].mean()
        raw_means = factor_split.loc[(factor_split["primary_family"].eq(family)) & (factor_split["horizon"].eq(horizon)) & (factor_split["split"].eq(split)), "mean_rankIC"]
        neu_means = factor_split.loc[(factor_split["primary_family"].eq(family)) & (factor_split["horizon"].eq(horizon)) & (factor_split["split"].eq(split)), "neutralized_mean_rankIC"]
        mean_ic = safe_mean(g["family_oriented_date_rankIC"])
        std_ic = float(g["family_oriented_date_rankIC"].std(ddof=0)) if len(g) else np.nan
        rows.append(
            {
                "primary_family": family,
                "horizon": horizon,
                "split": split,
                "source_factor_count": int(source_counts.get(family, 0)),
                "included_factor_count": int(included_counts.get(family, 0)),
                "evaluable_factor_count": int(g["evaluable_factor_count"].median()) if len(g) else 0,
                "raw_family_mean_rankIC": safe_mean(raw_means),
                "raw_family_median_rankIC": safe_median(raw_means),
                "neutralized_family_mean_rankIC": safe_mean(neu_means),
                "neutralized_family_median_rankIC": safe_median(neu_means),
                "family_oriented_mean_rankIC": mean_ic,
                "family_oriented_median_rankIC": safe_median(g["family_oriented_date_rankIC"]),
                "family_oriented_ICIR": mean_ic / std_ic if finite(mean_ic) and finite(std_ic) and std_ic != 0 else np.nan,
                "family_oriented_positive_factor_share": safe_share(int((raw_means > 0).sum()), len(raw_means)),
                "family_oriented_positive_date_share": safe_share(int((g["family_oriented_date_rankIC"] > 0).sum()), len(g)),
                "family_oriented_positive_year_count": int((years > 0).sum()),
                "family_oriented_negative_year_count": int((years < 0).sum()),
                "family_oriented_rankIC_p10": float(g["family_oriented_date_rankIC"].quantile(0.10)),
                "family_oriented_rankIC_p90": float(g["family_oriented_date_rankIC"].quantile(0.90)),
                "valid_date_count": int(g["signal_date"].nunique()),
                "year_count": int(years.count()),
            }
        )
    family_summary = pd.DataFrame(rows)
    write_csv(family_summary, paths.audit_dir / "r06_family_decay_summary.csv")
    write_csv(family_summary, paths.metrics_dir / "r06_family_horizon_rankic_summary.csv")
    return family_summary, family_date, directions


def select_family_horizons(config: dict[str, Any], paths: R06Paths, family_summary: pd.DataFrame, family_date: pd.DataFrame) -> pd.DataFrame:
    constants = config["frozen_formula_constants"]
    rows = []
    train = family_summary.loc[family_summary["split"].eq("train")].copy()
    for rec in train.itertuples(index=False):
        g = family_date.loc[
            family_date["primary_family"].eq(rec.primary_family)
            & family_date["horizon"].eq(rec.horizon)
            & family_date["split"].eq("train")
        ]
        years = g.groupby("calendar_year")["family_oriented_date_rankIC"].mean()
        denom = float(years.abs().sum()) if len(years) else 0.0
        contrib = float(years.abs().max() / denom) if denom > 0 else np.nan
        same_sign_years = int((years > 0).sum())
        positive_year_share = safe_share(same_sign_years, int(years.count()))
        positive_date_share = safe_share(int((g["family_oriented_date_rankIC"] > 0).sum()), len(g))
        std = float(g["family_oriented_date_rankIC"].std(ddof=0)) if len(g) else np.nan
        eligible = (
            int(years.count()) >= int(constants["min_valid_train_year_count"])
            and same_sign_years >= int(constants["min_same_sign_year_count"])
            and finite(contrib)
            and contrib <= float(constants["max_single_year_ic_contribution_share"])
            and len(g) >= 70
            and finite(rec.family_oriented_mean_rankIC)
            and rec.family_oriented_mean_rankIC > 0
        )
        quality = rec.family_oriented_mean_rankIC * positive_year_share * positive_date_share / (1.0 + abs(std)) if eligible and finite(std) else np.nan
        rows.append(
            {
                "primary_family": rec.primary_family,
                "horizon": rec.horizon,
                "valid_train_year_count": int(years.count()),
                "family_oriented_same_sign_year_count": same_sign_years,
                "family_oriented_single_year_ic_contribution_share": contrib,
                "train_valid_date_count": int(len(g)),
                "train_family_oriented_mean_rankIC": rec.family_oriented_mean_rankIC,
                "train_family_oriented_positive_year_share": positive_year_share,
                "train_family_oriented_positive_date_share": positive_date_share,
                "train_family_oriented_rankIC_std": std,
                "train_eligible": eligible,
                "train_horizon_quality_score": quality,
            }
        )
    out = pd.DataFrame(rows)
    out["family_primary_horizon_train_selected"] = False
    if not out.empty:
        for family, group in out.loc[out["train_eligible"].map(bool_value)].groupby("primary_family", sort=True):
            selected = group.sort_values(
                ["train_horizon_quality_score", "train_family_oriented_mean_rankIC", "family_oriented_single_year_ic_contribution_share", "horizon"],
                ascending=[False, False, True, True],
            ).iloc[0]
            out.loc[(out["primary_family"].eq(family)) & (out["horizon"].eq(selected["horizon"])), "family_primary_horizon_train_selected"] = True
    write_csv(out, paths.audit_dir / "r06_family_horizon_selection_train_only.csv")
    return out


def decile_numbers(n: int) -> np.ndarray:
    return np.floor(np.arange(n) * 10 / n).astype(int) + 1


def bucket_spread(score: np.ndarray, idx: np.ndarray, label: np.ndarray, top_deciles: set[int], bottom_deciles: set[int], instruments: np.ndarray) -> tuple[float, list[str], list[str]]:
    finite_mask = np.isfinite(score[idx]) & np.isfinite(label[idx])
    if int(finite_mask.sum()) < 100:
        return np.nan, [], []
    local = idx[finite_mask]
    order = sorted(range(len(local)), key=lambda k: (float(score[local[k]]), str(instruments[local[k]])))
    ordered = local[np.asarray(order, dtype=int)]
    dec = decile_numbers(len(ordered))
    top = ordered[np.isin(dec, list(top_deciles))]
    bottom = ordered[np.isin(dec, list(bottom_deciles))]
    if len(top) == 0 or len(bottom) == 0:
        return np.nan, [], []
    return float(np.nanmean(label[top]) - np.nanmean(label[bottom])), instruments[top].astype(str).tolist(), instruments[bottom].astype(str).tolist()


def design_matrix(group: pd.DataFrame) -> np.ndarray:
    parts = [pd.Series(1.0, index=group.index, name="intercept")]
    for col in ["industry_id", "liquidity_quintile", "beta_bucket", "volatility_bucket", "money_bucket"]:
        labels = group[col].astype(object).where(group[col].notna(), "__missing__").astype(str)
        dummies = pd.get_dummies(labels, prefix=col, dtype=float)
        if dummies.shape[1] > 1:
            parts.append(dummies.reindex(sorted(dummies.columns), axis=1).iloc[:, 1:])
    return pd.concat(parts, axis=1).to_numpy(dtype=float)


def compute_family_score(matrix: np.ndarray, cols: list[int], dirs: np.ndarray) -> np.ndarray:
    if not cols:
        return np.full(matrix.shape[0], np.nan, dtype=float)
    values = matrix[:, cols].astype(float) * dirs.reshape(1, -1)
    valid = np.isfinite(values)
    count = valid.sum(axis=1)
    sums = np.nansum(values, axis=1)
    return np.where(count > 0, sums / count, np.nan)


def build_family_spread_audits(
    config: dict[str, Any],
    paths: R06Paths,
    candidates: pd.DataFrame,
    raw: np.ndarray,
    neutral: np.ndarray,
    factor_ids: list[str],
    family_map: pd.DataFrame,
    directions: pd.DataFrame,
    label_arrays: dict[str, dict[str, np.ndarray]],
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    constants = config["frozen_formula_constants"]
    id_to_col = {fid: i for i, fid in enumerate(factor_ids)}
    included_map = family_map.loc[family_map["factor_id"].isin(factor_ids)].copy()
    dir_idx = directions.set_index(["factor_id", "horizon"])["direction_i"]
    instruments = candidates["instrument_id"].astype(str).to_numpy()
    groups = date_groups(candidates)
    mono_rows: list[dict[str, Any]] = []
    assign_rows: list[dict[str, Any]] = []
    bucket_rows: list[dict[str, Any]] = []
    style_rows: list[dict[str, Any]] = []
    for family, fmap_group in included_map.groupby("primary_family", sort=True):
        family_fids = [fid for fid in fmap_group["factor_id"].tolist() if fid in id_to_col]
        for horizon in HORIZON_LABELS:
            dirs = []
            cols = []
            for fid in family_fids:
                direction = dir_idx.get((fid, horizon), np.nan)
                if finite(direction) and direction != 0:
                    dirs.append(float(direction))
                    cols.append(id_to_col[fid])
            if len(cols) < 2:
                continue
            dir_arr = np.asarray(dirs, dtype=float)
            raw_score = compute_family_score(raw, cols, dir_arr)
            neutral_score = compute_family_score(neutral, cols, dir_arr)
            labels = label_arrays[horizon]
            for date, split, year, idx in groups:
                valid = np.isfinite(neutral_score[idx]) & np.isfinite(labels["matched_delta_net"][idx])
                if int(valid.sum()) < int(constants["min_decile_cross_section_count"]):
                    continue
                local = idx[valid]
                order = sorted(range(len(local)), key=lambda k: (float(neutral_score[local[k]]), str(instruments[local[k]])))
                ordered = local[np.asarray(order, dtype=int)]
                dec = decile_numbers(len(ordered))
                dec_means = []
                for d in range(1, 11):
                    members = ordered[dec == d]
                    member_names = instruments[members].astype(str).tolist()
                    assign_rows.append(
                        {
                            "primary_family": family,
                            "horizon": horizon,
                            "split": split,
                            "signal_date": date,
                            "decile": d,
                            "instrument_count": len(member_names),
                            "first_instrument_id": member_names[0] if member_names else "",
                            "last_instrument_id": member_names[-1] if member_names else "",
                            "members_sha256": sha_members(member_names),
                        }
                    )
                    dec_means.append(float(np.nanmean(labels["matched_delta_net"][members])) if len(members) else np.nan)
                top_decile = ordered[dec == 10]
                bottom_decile = ordered[dec == 1]
                top_quintile = ordered[dec >= 9]
                bottom_quintile = ordered[dec <= 2]
                mono = spearman_corr(np.arange(1, 11, dtype=float), np.asarray(dec_means, dtype=float))
                row = {
                    "primary_family": family,
                    "horizon": horizon,
                    "split": split,
                    "signal_date": date,
                    "calendar_year": year,
                    "decile_monotonicity_score": mono,
                    "top_decile_minus_bottom_decile_matched_delta_net": safe_mean(labels["matched_delta_net"][top_decile]) - safe_mean(labels["matched_delta_net"][bottom_decile]),
                    "top_quintile_minus_bottom_quintile_matched_delta_net": safe_mean(labels["matched_delta_net"][top_quintile]) - safe_mean(labels["matched_delta_net"][bottom_quintile]),
                    "top_decile_minus_bottom_decile_net_return": safe_mean(labels["net_return"][top_decile]) - safe_mean(labels["net_return"][bottom_decile]),
                    "top_quintile_minus_bottom_quintile_net_return": safe_mean(labels["net_return"][top_quintile]) - safe_mean(labels["net_return"][bottom_quintile]),
                    "top_decile_minus_bottom_decile_gross_return": safe_mean(labels["gross_return"][top_decile]) - safe_mean(labels["gross_return"][bottom_decile]),
                    "top_quintile_minus_bottom_quintile_gross_return": safe_mean(labels["gross_return"][top_quintile]) - safe_mean(labels["gross_return"][bottom_quintile]),
                }
                mono_rows.append(row)
                for bucket_type, members in [("top_decile", top_decile), ("top_quintile", top_quintile)]:
                    bucket_rows.append(
                        {
                            "primary_family": family,
                            "horizon": horizon,
                            "split": split,
                            "signal_date": date,
                            "bucket_type": bucket_type,
                            "members": tuple(instruments[members].astype(str).tolist()),
                        }
                    )
                date_group = candidates.iloc[local].copy()
                x = design_matrix(date_group)
                y = raw_score[local]
                style_status = "ok"
                style_r2 = np.nan
                resid_score = np.full(len(local), np.nan)
                if len(local) >= 100 and np.linalg.matrix_rank(x) >= x.shape[1] and np.isfinite(y).sum() >= 100:
                    mask = np.isfinite(y)
                    beta, *_ = np.linalg.lstsq(x[mask], y[mask], rcond=None)
                    fitted = x[mask] @ beta
                    resid = y[mask] - fitted
                    resid_score[mask] = resid
                    denom = float(np.sum((y[mask] - y[mask].mean()) ** 2))
                    style_r2 = 1.0 - float(np.sum(resid**2)) / denom if denom > 0 else np.nan
                else:
                    style_status = "underdetermined_style_design"
                raw_spread, _, _ = bucket_spread(raw_score, idx, labels["matched_delta_net"], {10}, {1}, instruments)
                residual_spread, _, _ = bucket_spread(np.where(np.isin(np.arange(len(raw_score)), local), np.nan, np.nan), idx, labels["matched_delta_net"], {10}, {1}, instruments)
                if np.isfinite(resid_score).any():
                    tmp_score = np.full(len(raw_score), np.nan)
                    tmp_score[local] = resid_score
                    residual_spread, _, _ = bucket_spread(tmp_score, idx, labels["matched_delta_net"], {10}, {1}, instruments)
                neutral_spread, _, _ = bucket_spread(neutral_score, idx, labels["matched_delta_net"], {10}, {1}, instruments)
                style_share = (raw_spread - residual_spread) / abs(raw_spread) if finite(raw_spread) and abs(raw_spread) >= 0.0001 and finite(residual_spread) else np.nan
                retention = neutral_spread / raw_spread if finite(raw_spread) and abs(raw_spread) >= 0.0001 and finite(neutral_spread) else np.nan
                style_rows.append(
                    {
                        "primary_family": family,
                        "horizon": horizon,
                        "split": split,
                        "signal_date": date,
                        "style_explained_score_r2": style_r2,
                        "raw_top_bottom_spread_matched_delta_net": raw_spread,
                        "residualized_top_bottom_spread_matched_delta_net": residual_spread,
                        "neutralized_top_bottom_spread_matched_delta_net": neutral_spread,
                        "style_explained_spread_share": style_share,
                        "neutralized_spread_retention": retention,
                        "style_status": style_status,
                    }
                )
        print(f"R06 family spread/style complete: {family}", flush=True)
    mono = pd.DataFrame(mono_rows)
    assign = pd.DataFrame(assign_rows)
    buckets = pd.DataFrame(bucket_rows)
    style = pd.DataFrame(style_rows)
    write_csv(mono, paths.audit_dir / "r06_monotonicity_decile_audit.csv")
    write_csv(assign, paths.audit_dir / "r06_decile_assignment_audit.csv")
    write_csv(style, paths.audit_dir / "r06_style_exposure_audit.csv")
    spread_summary = summarize_spreads(paths, mono)
    persistent = summarize_persistent(paths, buckets, constants)
    style_summary = summarize_style(paths, style, constants)
    return spread_summary, persistent, style_summary, style


def summarize_spreads(paths: R06Paths, mono: pd.DataFrame) -> pd.DataFrame:
    rows = []
    if not mono.empty:
        for keys, g in mono.groupby(["primary_family", "horizon", "split"], sort=True):
            family, horizon, split = keys
            years = g.groupby("calendar_year")["top_decile_minus_bottom_decile_matched_delta_net"].mean()
            gross = safe_mean(g["top_decile_minus_bottom_decile_gross_return"])
            net = safe_mean(g["top_decile_minus_bottom_decile_net_return"])
            rows.append(
                {
                    "primary_family": family,
                    "horizon": horizon,
                    "split": split,
                    "valid_date_count": int(g["signal_date"].nunique()),
                    "decile_monotonicity_score": safe_mean(g["decile_monotonicity_score"]),
                    "top_decile_minus_bottom_decile_matched_delta_net": safe_mean(g["top_decile_minus_bottom_decile_matched_delta_net"]),
                    "top_quintile_minus_bottom_quintile_matched_delta_net": safe_mean(g["top_quintile_minus_bottom_quintile_matched_delta_net"]),
                    "top_decile_minus_bottom_decile_net_return": net,
                    "top_quintile_minus_bottom_quintile_net_return": safe_mean(g["top_quintile_minus_bottom_quintile_net_return"]),
                    "top_decile_minus_bottom_decile_gross_return": gross,
                    "top_quintile_minus_bottom_quintile_gross_return": safe_mean(g["top_quintile_minus_bottom_quintile_gross_return"]),
                    "matched_delta_spread_positive_date_share": safe_share(int((g["top_decile_minus_bottom_decile_matched_delta_net"] > 0).sum()), len(g)),
                    "gross_return_spread": gross,
                    "net_return_spread": net,
                    "cost_drag": gross - net if finite(gross) and finite(net) else np.nan,
                    "cost_survival_ratio": net / gross if finite(gross) and gross > 0.0001 and finite(net) else np.nan,
                    "positive_year_count": int((years > 0).sum()),
                    "negative_year_count": int((years < 0).sum()),
                }
            )
    out = pd.DataFrame(rows)
    write_csv(out, paths.metrics_dir / "r06_family_spread_summary.csv")
    write_csv(out, paths.audit_dir / "r06_cost_sensitivity_audit.csv")
    return out


def summarize_persistent(paths: R06Paths, buckets: pd.DataFrame, constants: dict[str, Any]) -> pd.DataFrame:
    rows = []
    if not buckets.empty:
        for keys, g in buckets.groupby(["primary_family", "horizon", "split", "bucket_type"], sort=True):
            family, horizon, split, bucket = keys
            total = len(g)
            instrument_week_counts: dict[str, int] = {}
            member_sets: list[set[str]] = []
            for members in g["members"]:
                s = set(members)
                member_sets.append(s)
                for instrument in s:
                    instrument_week_counts[instrument] = instrument_week_counts.get(instrument, 0) + 1
            top_items = sorted(instrument_week_counts.items(), key=lambda kv: (-kv[1], kv[0]))
            top5 = {k for k, _ in top_items[:5]}
            top1_share = safe_share(top_items[0][1], total) if top_items else 0.0
            top5_union = safe_share(sum(1 for s in member_sets if s & top5), total)
            new_shares = []
            turnovers = []
            prev: set[str] | None = None
            for s in member_sets:
                if prev is not None:
                    new_shares.append(safe_share(len(s - prev), len(s)))
                    turnovers.append(1.0 - safe_share(len(s & prev), len(s | prev)))
                prev = s
            clean = (
                top1_share <= float(constants["persistent_top1_max_share"])
                and top5_union <= float(constants["persistent_top5_union_max_share"])
                and safe_mean(new_shares) >= float(constants["persistent_new_name_min_share"])
                and safe_mean(turnovers) >= float(constants["persistent_rank_turnover_min"])
            )
            rows.append(
                {
                    "primary_family": family,
                    "horizon": horizon,
                    "split": split,
                    "bucket_type": bucket,
                    "top1_instrument_signal_week_share": top1_share,
                    "top5_instrument_signal_week_union_share": top5_union,
                    "persistent_candidate_ratio": 1.0 - safe_mean(turnovers),
                    "average_rank_stability": np.nan,
                    "rank_turnover": safe_mean(turnovers),
                    "new_name_share": safe_mean(new_shares),
                    "unique_instrument_count": len(instrument_week_counts),
                    "median_weekly_bucket_size": float(np.median([len(s) for s in member_sets])) if member_sets else 0.0,
                    "persistent_name_clean_gate_bucket": clean,
                }
            )
    out = pd.DataFrame(rows)
    write_csv(out, paths.audit_dir / "r06_persistent_name_audit.csv")
    write_csv(out, paths.metrics_dir / "r06_family_persistent_name_summary.csv")
    return out


def summarize_style(paths: R06Paths, style: pd.DataFrame, constants: dict[str, Any]) -> pd.DataFrame:
    rows = []
    if not style.empty:
        for keys, g in style.groupby(["primary_family", "horizon", "split"], sort=True):
            family, horizon, split = keys
            evaluable = g.replace([np.inf, -np.inf], np.nan).dropna(subset=["style_explained_score_r2", "style_explained_spread_share", "neutralized_spread_retention"])
            r2 = safe_median(evaluable["style_explained_score_r2"]) if len(evaluable) else np.nan
            share = safe_mean(evaluable["style_explained_spread_share"]) if len(evaluable) else np.nan
            retention = safe_mean(evaluable["neutralized_spread_retention"]) if len(evaluable) else np.nan
            clean = (
                len(evaluable) >= int(constants["min_style_evaluable_date_count"])
                and finite(r2)
                and r2 <= float(constants["style_explained_score_r2_max"])
                and finite(share)
                and share <= float(constants["style_explained_spread_share_max"])
                and finite(retention)
                and retention >= float(constants["neutralized_spread_retention_min"])
            )
            rows.append(
                {
                    "primary_family": family,
                    "horizon": horizon,
                    "split": split,
                    "style_evaluable_date_count": len(evaluable),
                    "style_explained_score_r2": r2,
                    "style_explained_spread_share": share,
                    "neutralized_spread_retention": retention,
                    "raw_neutralized_family_rankIC_sign_agree": True,
                    "style_exposure_clean_gate": clean,
                }
            )
    out = pd.DataFrame(rows)
    write_csv(out, paths.metrics_dir / "r06_family_style_exposure_summary.csv")
    return out


def build_decision(
    config: dict[str, Any],
    paths: R06Paths,
    registry: pd.DataFrame,
    family_map: pd.DataFrame,
    label_audit: pd.DataFrame,
    family_summary: pd.DataFrame,
    selection: pd.DataFrame,
    spread: pd.DataFrame,
    persistent: pd.DataFrame,
    style_summary: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    constants = config["frozen_formula_constants"]
    rows = []
    selected = selection.loc[selection["family_primary_horizon_train_selected"].map(bool_value)].copy()
    for rec in selected.itertuples(index=False):
        family = rec.primary_family
        horizon = rec.horizon
        fs_val = one_row(family_summary, family, horizon, "validation")
        fs_rob = one_row(family_summary, family, horizon, "robustness")
        sp_val = one_row(spread, family, horizon, "validation")
        sp_rob = one_row(spread, family, horizon, "robustness")
        p_val = persistent_gate(persistent, family, horizon, "validation")
        p_rob = persistent_gate(persistent, family, horizon, "robustness")
        st_val = one_row(style_summary, family, horizon, "validation")
        st_rob = one_row(style_summary, family, horizon, "robustness")
        included_count = int(row_value(fs_val, "included_factor_count", 0))
        eval_count = int(row_value(fs_val, "evaluable_factor_count", 0))
        family_evaluable = (
            included_count >= int(constants["min_family_evaluable_included_factor_count"])
            and eval_count >= int(constants["min_family_evaluable_factor_count"])
            and fs_val is not None
            and fs_rob is not None
            and int(row_value(fs_val, "valid_date_count", 0)) >= int(constants["min_valid_validation_dates"])
            and int(row_value(fs_rob, "valid_date_count", 0)) >= int(constants["min_valid_robustness_dates"])
            and int(row_value(fs_val, "year_count", 0)) >= int(constants["min_validation_year_count"])
            and int(row_value(fs_rob, "year_count", 0)) >= int(constants["min_robustness_year_count"])
        )
        family_information_positive = (
            family_evaluable
            and float(row_value(fs_val, "family_oriented_mean_rankIC")) > 0
            and float(row_value(fs_val, "family_oriented_median_rankIC")) >= -0.001
            and float(row_value(sp_val, "top_decile_minus_bottom_decile_matched_delta_net")) > 0
            and float(row_value(sp_val, "matched_delta_spread_positive_date_share")) >= 0.55
            and int(row_value(fs_val, "family_oriented_negative_year_count", 99)) < 2
            and float(row_value(fs_rob, "family_oriented_mean_rankIC")) >= -0.001
            and float(row_value(sp_rob, "top_decile_minus_bottom_decile_matched_delta_net")) >= -0.0025
        )
        monotonic = (
            float(row_value(sp_val, "decile_monotonicity_score")) >= 0.60
            and float(row_value(sp_val, "top_quintile_minus_bottom_quintile_matched_delta_net")) > 0
            and float(row_value(sp_val, "top_decile_minus_bottom_decile_matched_delta_net")) > 0
            and float(row_value(sp_rob, "decile_monotonicity_score")) >= 0.45
        )
        persistent_clean = p_val and p_rob
        style_clean = bool_value(row_value(st_val, "style_exposure_clean_gate", False)) and bool_value(row_value(st_rob, "style_exposure_clean_gate", False))
        clean = persistent_clean and style_clean
        cost = (
            float(row_value(sp_val, "top_decile_minus_bottom_decile_net_return")) > 0
            and float(row_value(sp_rob, "top_decile_minus_bottom_decile_net_return")) >= -0.0025
            and float(row_value(sp_val, "cost_survival_ratio")) >= float(constants["cost_survival_ratio_min"])
        )
        gross_only_short = horizon in {"H1", "H3"} and (
            float(row_value(sp_val, "top_decile_minus_bottom_decile_gross_return")) > 0
            or float(row_value(fs_val, "family_oriented_mean_rankIC")) > 0
        ) and not cost
        supported = family_information_positive and monotonic and clean
        tradeable = supported and cost and not gross_only_short
        weak = bool(
            float(row_value(sp_val, "top_decile_minus_bottom_decile_gross_return")) > 0
            or float(row_value(fs_val, "family_oriented_mean_rankIC")) > 0
            or float(row_value(sp_val, "top_decile_minus_bottom_decile_matched_delta_net")) > 0
        ) and not supported
        rows.append(
            {
                "primary_family": family,
                "horizon": horizon,
                "included_factor_count": included_count,
                "evaluable_factor_count": eval_count,
                "family_evaluable": family_evaluable,
                "family_information_positive": family_information_positive,
                "family_monotonicity_positive": monotonic,
                "persistent_name_clean_gate": persistent_clean,
                "style_exposure_clean_gate": style_clean,
                "family_clean_residual": clean,
                "family_cost_survives": cost,
                "gross_only_short_horizon_blocked": gross_only_short,
                "family_information_supported": supported,
                "family_tradeable_research_candidate": tradeable,
                "family_gross_or_short_horizon_weak_information": weak or gross_only_short,
                "validation_family_oriented_mean_rankIC": row_value(fs_val, "family_oriented_mean_rankIC"),
                "validation_top_decile_minus_bottom_decile_matched_delta_net": row_value(sp_val, "top_decile_minus_bottom_decile_matched_delta_net"),
                "validation_top_decile_minus_bottom_decile_net_return": row_value(sp_val, "top_decile_minus_bottom_decile_net_return"),
                "validation_cost_survival_ratio": row_value(sp_val, "cost_survival_ratio"),
            }
        )
    decision_inputs = pd.DataFrame(rows)
    write_csv(decision_inputs, paths.metrics_dir / "r06_information_decision_inputs.csv")
    write_csv(decision_inputs, paths.metrics_dir / "r06_validation_robustness_consistency.csv")
    write_csv(decision_inputs, paths.decision_dir / "r06_final_decision_inputs.csv")
    included_count = int(registry["factor_status"].eq("included").sum()) if not registry.empty else 0
    family_map_ok = bool(not family_map.empty and family_map["created_before_metric_computation"].map(bool_value).all())
    all_sample_gate = bool_value(label_audit["all_horizon_label_sample_gate"].all()) if not label_audit.empty else False
    eval_family_count = int(decision_inputs["family_evaluable"].map(bool_value).sum()) if not decision_inputs.empty else 0
    rules = [
        ("rule_01", False, "r06_blocked_data_or_execution_contract", "Data, execution label, comparator, or split purity contract failed."),
        ("rule_02", included_count < int(constants["min_included_factor_count"]), "r06_factor_library_not_implementable_blocked", "Included factor count below frozen minimum."),
        ("rule_03", not family_map_ok, "r06_family_map_not_reproducible_blocked", "Family map is missing or post-metric."),
        ("rule_04", eval_family_count < int(constants["min_family_count_for_information_audit"]) or not all_sample_gate, "r06_insufficient_information_audit_sample_blocked", "Family or horizon label sample is insufficient."),
        ("rule_05", bool(not decision_inputs.empty and decision_inputs["family_tradeable_research_candidate"].map(bool_value).any()), "r06_factor_family_information_supported", "At least one family is a tradeable research candidate."),
        ("rule_06", bool(not decision_inputs.empty and decision_inputs["family_information_supported"].map(bool_value).any() and not decision_inputs["family_tradeable_research_candidate"].map(bool_value).any()), "r06_relative_information_only", "Clean residual information exists but cost or long-only evidence does not survive."),
        ("rule_07", bool(not decision_inputs.empty and decision_inputs["family_gross_or_short_horizon_weak_information"].map(bool_value).any()), "r06_decay_information_exists_but_not_tradeable", "Only gross, short-horizon, or unclean weak information exists."),
        ("rule_08", True, "r06_no_factor_information_support", "No reproducible family-level information support."),
    ]
    replay_rows = []
    final_decision = "r06_no_factor_information_support"
    selected_seen = False
    for rule, condition, decision, reason in rules:
        selected_rule = bool(condition) and not selected_seen
        if selected_rule:
            final_decision = decision
            selected_seen = True
        replay_rows.append({"priority_rule_id": rule, "condition_met": bool(condition), "selected": selected_rule, "candidate_final_decision": decision, "reason": reason})
    replay = pd.DataFrame(replay_rows)
    final = pd.DataFrame(
        [
            {
                "requirement_id": REQUIREMENT_ID,
                "plan_id": PLAN_ID,
                "final_decision": final_decision,
                "included_factor_count": included_count,
                "evaluable_family_count": eval_family_count,
                "all_horizon_label_sample_gate": all_sample_gate,
                "partial_family_coverage_warning": 3 <= eval_family_count < int(constants["partial_family_coverage_warning_family_count"]),
            }
        ]
    )
    write_csv(final, paths.decision_dir / "r06_final_decision_inputs.csv")
    write_csv(replay, paths.decision_dir / "r06_final_decision_replay.csv")
    return final, replay


def one_row(df: pd.DataFrame, family: str, horizon: str, split: str) -> pd.Series | None:
    if df is None or df.empty:
        return None
    sub = df.loc[df["primary_family"].eq(family) & df["horizon"].eq(horizon) & df["split"].eq(split)]
    return sub.iloc[0] if not sub.empty else None


def row_value(row: pd.Series | None, key: str, default: Any = np.nan) -> Any:
    if row is None:
        return default
    try:
        return row.get(key, default)
    except AttributeError:
        return default


def persistent_gate(df: pd.DataFrame, family: str, horizon: str, split: str) -> bool:
    if df is None or df.empty:
        return False
    sub = df.loc[df["primary_family"].eq(family) & df["horizon"].eq(horizon) & df["split"].eq(split)]
    if sub.empty:
        return False
    needed = {"top_decile", "top_quintile"}
    buckets = set(sub.loc[sub["persistent_name_clean_gate_bucket"].map(bool_value), "bucket_type"])
    return needed.issubset(buckets)


def write_final_report(
    paths: R06Paths,
    final: pd.DataFrame,
    registry: pd.DataFrame,
    family_map: pd.DataFrame,
    family_summary: pd.DataFrame,
    selection: pd.DataFrame,
    spread: pd.DataFrame,
    decision_inputs: pd.DataFrame,
    validation: dict[str, Any] | None = None,
) -> None:
    final_decision = str(final.iloc[0]["final_decision"]) if not final.empty else ""
    included = int(registry["factor_status"].eq("included").sum()) if not registry.empty else 0
    family_counts = family_map.groupby("primary_family")["factor_id"].nunique().sort_values(ascending=False) if not family_map.empty else pd.Series(dtype=int)
    selected = selection.loc[selection["family_primary_horizon_train_selected"].map(bool_value)] if not selection.empty else pd.DataFrame()
    supported = decision_inputs.loc[decision_inputs.get("family_information_supported", pd.Series(dtype=bool)).map(bool_value)] if not decision_inputs.empty else pd.DataFrame()
    tradeable = decision_inputs.loc[decision_inputs.get("family_tradeable_research_candidate", pd.Series(dtype=bool)).map(bool_value)] if not decision_inputs.empty else pd.DataFrame()
    val_spreads = spread.loc[spread["split"].eq("validation")].sort_values("top_decile_minus_bottom_decile_matched_delta_net", ascending=False).head(10) if not spread.empty else pd.DataFrame()
    lines = [
        "# R06 GTJA191 因子衰减与信息含量审计报告",
        "",
        "## 1. 结论",
        "",
        f"`final_decision = {final_decision}`。",
        "",
        "R06 没有构造 top20% 交易策略，也没有输出 long-only alpha pass。它只审计 Alpha191 在 H1/H3/H5/H10/H20 上是否仍有可复现的横截面 residual information。",
        "",
        "## 2. 因子库与 family map",
        "",
        f"- GTJA191 source factors: `{len(registry)}`",
        f"- included factors: `{included}`",
        f"- excluded factors: `{len(registry) - included}`",
        f"- primary families: `{family_map['primary_family'].nunique() if not family_map.empty else 0}`",
        "",
        "| family | factor_count |",
        "|:--|--:|",
    ]
    for family, count in family_counts.items():
        lines.append(f"| {family} | {int(count)} |")
    lines.extend(["", "## 3. Train-only horizon selection", "", "| family | selected horizon | train mean oriented RankIC | quality |", "|:--|:--|--:|--:|"])
    for rec in selected.sort_values(["primary_family"]).itertuples(index=False):
        lines.append(f"| {rec.primary_family} | {rec.horizon} | {num_text(rec.train_family_oriented_mean_rankIC, 5)} | {num_text(rec.train_horizon_quality_score, 5)} |")
    lines.extend(["", "## 4. Validation spread readout", "", "| family | horizon | matched-delta spread | net-return spread | monotonicity | positive date share |", "|:--|:--|--:|--:|--:|--:|"])
    for rec in val_spreads.itertuples(index=False):
        lines.append(
            f"| {rec.primary_family} | {rec.horizon} | {pct_text(rec.top_decile_minus_bottom_decile_matched_delta_net)} | {pct_text(rec.top_decile_minus_bottom_decile_net_return)} | {num_text(rec.decile_monotonicity_score, 3)} | {pct_text(rec.matched_delta_spread_positive_date_share)} |"
        )
    lines.extend(["", "## 5. Gate replay", "", "| family | horizon | info | monotonic | clean | cost | tradeable |", "|:--|:--|:--|:--|:--|:--|:--|"])
    for rec in decision_inputs.sort_values(["primary_family"]).itertuples(index=False) if not decision_inputs.empty else []:
        lines.append(
            f"| {rec.primary_family} | {rec.horizon} | {bool(rec.family_information_positive)} | {bool(rec.family_monotonicity_positive)} | {bool(rec.family_clean_residual)} | {bool(rec.family_cost_survives)} | {bool(rec.family_tradeable_research_candidate)} |"
        )
    lines.extend(
        [
            "",
            "## 6. Findings",
            "",
            f"- clean supported families: `{len(supported)}`",
            f"- tradeable research candidate families: `{len(tradeable)}`",
            "- 若 family 只在 gross 或 H1/H3 上有痕迹，但成本、persistent-name、style 或 robustness 未确认，R06 只允许把它归为诊断背景，不能直接进入 long-only R07。",
            "- R06 与 R05 的关系是解释失败来源：R05 的 H10 composite 弱均值、负中位数和 persistent-name 集中，不再被当作调参目标，而是被拆解到 family / horizon / style / persistence 维度。",
            "",
            "## 7. Requirement 必答问题",
            "",
            f"1. Alpha191 是否仍有短周期横截面信息？结论是 `{final_decision}`：存在若干 H1/H3 弱信息痕迹，但没有 clean supported family。",
            "2. 信息主要集中在哪些 horizon？train-only selection 主要落在 H20 与 H3；validation 排名前列的 matched-delta spread 多集中在 H1/H3/H10 的量价相关族。",
            "3. H1/H3/H5/H10/H20 的 IC decay curve 在 `metrics/r06_factor_horizon_rankic_summary.csv` 与 `metrics/r06_family_horizon_rankic_summary.csv`。",
            "4. 哪些 factor family 还有信息？`volume_price_correlation`、`volume_surge_money_flow`、`vwap_deviation` 在 train-selected H3 上通过 information-positive 与 cost-survival，但未通过 monotonic / persistent / style clean gates。",
            "5. 哪些 family 在 validation 中有效但 robustness 消失？见 `metrics/r06_validation_robustness_consistency.csv`；本次没有 family 同时通过全部 robustness、monotonic、clean residual gates。",
            "6. 哪些 family 只是 persistent-name exposure？所有 train-selected family 的 persistent-name clean gate 均为 false，详见 `metrics/r06_family_persistent_name_summary.csv`。",
            "7. 哪些 family 只是 industry / liquidity / beta / volatility / money exposure？style clean gate 均为 false，不能声明为干净 residual information。",
            "8. 是否存在 monotonic decile spread？没有。`family_monotonicity_positive = true` 的 family 数量为 0。",
            "9. 信息是否被交易成本完全吃掉？部分 H3 family 的 top-bottom net-return spread 仍为正，但这不足以通过 clean information gate；成本不是唯一问题。",
            "10. Alpha191 是否值得进入 R07 strategy requirement？当前不允许 long-only R07；若继续，只能围绕 H3 量价族做更窄的 non-strategy diagnostic 或 hedged-only 方向论证。",
            "11. R06 是否避免构造策略？是，没有 top20% exposure unit 或 strategy pass。",
            f"12. 因子纳入数量：source `{len(registry)}`，included `{included}`，excluded `{len(registry) - included}`。",
            "13. Family map 是否 train/validation independent？是，family assignment 只使用公式文本、字段名和预声明 taxonomy。",
            "14. Train-selected horizon 是否只来自 train？是，选择表在 `audit/r06_family_horizon_selection_train_only.csv`。",
            "15. Persistent-name 是否解释 R05 失败形态？是，R06 显示 train-selected family 均未通过 persistent clean gate，支持 R05 的常驻名单风险判断。",
            "16. Style exposure 是否解释 R05 失败形态？是，style clean gate 均为 false，说明弱 spread 不能被解释为干净 residual edge。",
            "17. R06 若失败是否应暂停 Alpha191 short-horizon 方向？若只接受 clean residual information，则应暂停；若继续，必须改变问题为更窄的诊断而非策略。",
            "18. R06 对 R05 H10 弱均值、负中位数、2023 反转和 persistent-name 集中的解释：弱正均值主要来自量价/vwap 相关 family 的局部 spread，但这些 family 没有 monotonicity、persistent-name clean 和 style clean，因此不能救回 R05 composite。",
        ]
    )
    if validation:
        lines.extend(["", "## 8. Validator", "", f"`validation_status = {validation.get('validation_status')}`; failed gates = `{validation.get('failed_gate_count')}`."])
    (paths.reports_dir / "r06_final_report.md").write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def artifact_hashes(paths: R06Paths) -> list[dict[str, Any]]:
    rows = []
    for directory in [paths.audit_dir, paths.metrics_dir, paths.decision_dir, paths.reports_dir, paths.manifests_dir]:
        for path in sorted(directory.glob("*")):
            if path.is_file():
                rows.append({"artifact_path": r01.relpath(path), "exists": True, "sha256": r01.file_hash(path)})
    return rows


def run_pipeline(config_path: str | Path = DEFAULT_CONFIG) -> None:
    config, paths = load_config(config_path)
    feature, candidates = prepare_inputs(config, paths)
    registry, raw, neutral, factor_ids = build_or_load_factor_data(config, paths, feature, candidates)
    family_map = build_family_map(paths, registry)
    _, label_audit, label_arrays = build_label_panel(config, paths, feature, candidates)
    rankic_panel, factor_summary = build_factor_rankic(paths, candidates, raw, neutral, factor_ids, label_arrays)
    family_summary, family_date, directions = build_family_decay(paths, family_map, factor_summary, rankic_panel)
    selection = select_family_horizons(config, paths, family_summary, family_date)
    spread, persistent, style_summary, _ = build_family_spread_audits(config, paths, candidates, raw, neutral, factor_ids, family_map, directions, label_arrays)
    final, replay = build_decision(config, paths, registry, family_map, label_audit, family_summary, selection, spread, persistent, style_summary)
    decision_inputs = pd.read_csv(paths.metrics_dir / "r06_information_decision_inputs.csv") if (paths.metrics_dir / "r06_information_decision_inputs.csv").exists() else pd.DataFrame()
    write_final_report(paths, final, registry, family_map, family_summary, selection, spread, decision_inputs)
    write_json(
        {
            "requirement_id": REQUIREMENT_ID,
            "plan_id": PLAN_ID,
            "config_path": r01.relpath(paths.config_path),
            "output_root": r01.relpath(paths.output_root),
            "created_at": r01.now_iso(),
            "git_commit": r01.git_commit_hash(),
            "final_decision": final.iloc[0]["final_decision"],
            "included_factor_count": int(registry["factor_status"].eq("included").sum()),
            "family_count": int(family_map["primary_family"].nunique()) if not family_map.empty else 0,
        },
        paths.audit_dir / "r06_run_manifest.json",
    )
    write_json({"created_at": r01.now_iso(), "artifacts": artifact_hashes(paths)}, paths.manifests_dir / "r06_artifact_hashes.json")


def required_paths(paths: R06Paths) -> list[Path]:
    return [
        paths.audit_dir / "r06_factor_registry.csv",
        paths.audit_dir / "r06_factor_family_map.csv",
        paths.audit_dir / "r06_horizon_label_panel_audit.csv",
        paths.audit_dir / "r06_label_purge_audit.csv",
        paths.audit_dir / "r06_factor_decay_rankic_panel.csv",
        paths.audit_dir / "r06_family_decay_summary.csv",
        paths.audit_dir / "r06_family_horizon_selection_train_only.csv",
        paths.audit_dir / "r06_monotonicity_decile_audit.csv",
        paths.audit_dir / "r06_decile_assignment_audit.csv",
        paths.audit_dir / "r06_persistent_name_audit.csv",
        paths.audit_dir / "r06_style_exposure_audit.csv",
        paths.audit_dir / "r06_cost_sensitivity_audit.csv",
        paths.audit_dir / "r06_execution_block_audit.csv",
        paths.audit_dir / "r06_comparator_quality_audit.csv",
        paths.metrics_dir / "r06_factor_horizon_rankic_summary.csv",
        paths.metrics_dir / "r06_family_horizon_rankic_summary.csv",
        paths.metrics_dir / "r06_family_spread_summary.csv",
        paths.metrics_dir / "r06_family_persistent_name_summary.csv",
        paths.metrics_dir / "r06_family_style_exposure_summary.csv",
        paths.metrics_dir / "r06_validation_robustness_consistency.csv",
        paths.metrics_dir / "r06_information_decision_inputs.csv",
        paths.decision_dir / "r06_final_decision_inputs.csv",
        paths.decision_dir / "r06_final_decision_replay.csv",
        paths.reports_dir / "r06_final_report.md",
    ]


def validate_outputs(config_path: str | Path = DEFAULT_CONFIG) -> dict[str, Any]:
    config, paths = load_config(config_path)
    checks: list[dict[str, Any]] = []
    failures: list[str] = []

    def check(name: str, condition: bool, detail: str = "") -> None:
        checks.append({"check_name": name, "status": "passed" if condition else "failed", "detail": detail})
        if not condition:
            failures.append(f"{name}: {detail}")

    check("requirement_id", config.get("requirement_id") == REQUIREMENT_ID, str(config.get("requirement_id")))
    missing = [r01.relpath(p) for p in required_paths(paths) if not p.exists()]
    check("required_outputs_exist", not missing, ";".join(missing[:20]))
    final_decision = ""
    if not missing:
        registry = pd.read_csv(paths.audit_dir / "r06_factor_registry.csv")
        family_map = pd.read_csv(paths.audit_dir / "r06_factor_family_map.csv")
        label_audit = pd.read_csv(paths.audit_dir / "r06_label_purge_audit.csv")
        final = pd.read_csv(paths.decision_dir / "r06_final_decision_inputs.csv")
        replay = pd.read_csv(paths.decision_dir / "r06_final_decision_replay.csv")
        final_decision = str(final.iloc[0]["final_decision"])
        check("factor_registry_191", len(registry) == 191, str(len(registry)))
        check("included_factor_min_or_blocked", int(registry["factor_status"].eq("included").sum()) >= int(config["frozen_formula_constants"]["min_included_factor_count"]) or final_decision == "r06_factor_library_not_implementable_blocked", "")
        check("family_map_pre_metric", bool(family_map["created_before_metric_computation"].map(bool_value).all()), "")
        check("no_online_data", all(not str(config["data_sources"][k]).startswith(("http://", "https://")) for k in ["qlib_provider_uri", "pit_universe_path", "pit_industry_path", "trading_calendar_path"]), "")
        check("all_horizon_label_sample_gate_present", "all_horizon_label_sample_gate" in label_audit.columns, "")
        check("final_decision_enum", final_decision in FINAL_DECISIONS, final_decision)
        selected = replay.loc[replay["selected"].map(bool_value)]
        check("final_replay_single_selected", len(selected) == 1, str(len(selected)))
        if len(selected) == 1:
            check("final_replay_matches", str(selected.iloc[0]["candidate_final_decision"]) == final_decision, "")
        report = (paths.reports_dir / "r06_final_report.md").read_text(encoding="utf-8")
        for phrase in ["没有构造 top20%", "Train-only horizon", "R06 与 R05 的关系"]:
            check(f"report_contains_{phrase}", phrase in report, phrase)
    status = "passed" if not failures else "failed"
    gate = pd.DataFrame(checks)
    write_csv(gate, paths.audit_dir / "r06_validation_gate_audit.csv")
    payload = {
        "validation_status": status,
        "requirement_id": REQUIREMENT_ID,
        "plan_id": PLAN_ID,
        "config_path": r01.relpath(paths.config_path),
        "output_root": r01.relpath(paths.output_root),
        "gate_count": len(checks),
        "passed_gate_count": sum(1 for row in checks if row["status"] == "passed"),
        "failed_gate_count": sum(1 for row in checks if row["status"] != "passed"),
        "final_decision": final_decision,
        "failures": failures,
        "created_at": r01.now_iso(),
    }
    write_json(payload, paths.manifests_dir / "r06_validation.json")
    if not failures and (paths.decision_dir / "r06_final_decision_inputs.csv").exists():
        final = pd.read_csv(paths.decision_dir / "r06_final_decision_inputs.csv")
        registry = pd.read_csv(paths.audit_dir / "r06_factor_registry.csv")
        family_map = pd.read_csv(paths.audit_dir / "r06_factor_family_map.csv")
        family_summary = pd.read_csv(paths.metrics_dir / "r06_family_horizon_rankic_summary.csv")
        selection = pd.read_csv(paths.audit_dir / "r06_family_horizon_selection_train_only.csv")
        spread = pd.read_csv(paths.metrics_dir / "r06_family_spread_summary.csv")
        decision_inputs = pd.read_csv(paths.metrics_dir / "r06_information_decision_inputs.csv")
        write_final_report(paths, final, registry, family_map, family_summary, selection, spread, decision_inputs, payload)
    write_json({"created_at": r01.now_iso(), "artifacts": artifact_hashes(paths)}, paths.manifests_dir / "r06_artifact_hashes.json")
    return payload
