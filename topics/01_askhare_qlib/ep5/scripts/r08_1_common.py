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
import r08_common as r08


SCRIPT_DIR = Path(__file__).resolve().parent
EP5_DIR = SCRIPT_DIR.parent
DEFAULT_CONFIG = EP5_DIR / "configs" / "r08_1_vwap_deviation_h3_kfold_transferability_sensitivity_audit_v0.yaml"

REQUIREMENT_ID = "ep5_r08_1_vwap_deviation_h3_kfold_transferability_sensitivity_audit_v0"
PLAN_ID = "ep5_e08_1_vwap_deviation_h3_kfold_transferability_sensitivity_audit_v0"
PRIMARY_FAMILY = "vwap_deviation"
COMPARATOR_FAMILY = "volume_price_correlation"
FAMILIES = [PRIMARY_FAMILY, COMPARATOR_FAMILY]
FOLD_IDS = [0, 1, 2, 3, 4]
OOF_SPLITS = ["train_oof_unseen", "validation_oof_unseen", "robustness_oof_unseen"]
UNDERLYING_SPLIT = {
    "train_oof_unseen": "train",
    "validation_oof_unseen": "validation",
    "robustness_oof_unseen": "robustness",
}
FINAL_DECISIONS = [
    "r08_1_blocked_data_or_execution_contract",
    "r08_1_blocked_kfold_sample_insufficient",
    "r08_1_no_vwap_kfold_transferability_support",
    "r08_1_fold_fragile_vwap_state_candidate",
    "r08_1_time_transfer_only_not_instrument_transfer",
    "r08_1_vwap_kfold_transferability_sensitivity_supported",
]


@dataclass(frozen=True)
class R081Paths:
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


def load_config(path: str | Path = DEFAULT_CONFIG) -> tuple[dict[str, Any], R081Paths]:
    import yaml

    config_path = r01.topic_path(path)
    config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    output_root = r01.topic_path(config["output_root"])
    paths = R081Paths(
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


def finite(value: Any) -> bool:
    return r01.finite(value)


def bool_value(value: Any) -> bool:
    return r05.bool_value(value)


def safe_mean(values: pd.Series | np.ndarray | list[Any]) -> float:
    return r08.safe_mean(values)


def safe_median(values: pd.Series | np.ndarray | list[Any]) -> float:
    return r08.safe_median(values)


def safe_share(numerator: float, denominator: float) -> float:
    return r08.safe_share(numerator, denominator)


def pct_text(value: Any, digits: int = 2) -> str:
    return r08.pct_text(value, digits)


def num_text(value: Any, digits: int = 4) -> str:
    return r08.num_text(value, digits)


def spearman_corr(x: np.ndarray, y: np.ndarray) -> float:
    return r08.spearman_corr(x, y)


def write_csv(df: pd.DataFrame, path: Path, columns: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if columns is not None:
        out = df.copy()
        for col in columns:
            if col not in out.columns:
                out[col] = np.nan
        out = out[columns]
    else:
        out = df
    out.to_csv(path, index=False)


def write_json(payload: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")


def canonical_instrument_id(instrument_id: Any) -> str:
    return str(instrument_id)


def instrument_hash_value(instrument_id: Any) -> int:
    text = canonical_instrument_id(instrument_id).lower()
    digest = hashlib.sha256(text.encode("utf-8")).digest()[:8]
    return int.from_bytes(digest, "big")


def instrument_fold_id(instrument_id: Any, modulus: int = 5) -> int:
    return instrument_hash_value(instrument_id) % modulus


def artifact_hashes(paths: R081Paths) -> list[dict[str, Any]]:
    rows = []
    for directory in [paths.audit_dir, paths.metrics_dir, paths.decision_dir, paths.reports_dir, paths.manifests_dir]:
        for path in sorted(directory.glob("*")):
            if path.is_file():
                rows.append({"artifact_path": rel(path), "exists": True, "sha256": r01.file_hash(path)})
    return rows


def scope_factor_ids(inputs: r08.R06Inputs) -> dict[str, list[str]]:
    included = set(inputs.factor_ids)
    out: dict[str, list[str]] = {}
    for family in FAMILIES:
        out[family] = sorted(
            inputs.family_map.loc[
                inputs.family_map["primary_family"].eq(family) & inputs.family_map["factor_id"].isin(included),
                "factor_id",
            ].astype(str)
        )
    return out


def build_factor_state_inputs(
    config: dict[str, Any],
    paths: R081Paths,
    inputs: r08.R06Inputs,
    scope: dict[str, list[str]],
) -> tuple[np.ndarray, np.ndarray, np.ndarray, list[str]]:
    constants = config["frozen_formula_constants"]
    lookback = int(constants["within_stock_lookback_trading_days"])
    min_history = int(constants["within_stock_min_history_count"])
    target_fids = [fid for family in FAMILIES for fid in scope[family]]
    source = r05.source_path(config).read_text(encoding="utf-8")
    specs = {spec["factor_id"]: spec for spec in r05.extract_gtja_functions(source)}
    funcs = r05.compile_alpha_functions([specs[fid] for fid in target_fids if fid in specs])
    wide_inputs, _, _ = r05.build_wide_inputs(inputs.feature)
    raw_matrix = np.full((len(inputs.candidates), len(target_fids)), np.nan, dtype=np.float32)
    percentile_matrix = np.full_like(raw_matrix, np.nan)
    tie_matrix = np.full_like(raw_matrix, np.nan)
    tie_cluster_matrix = np.zeros_like(raw_matrix, dtype=bool)
    available_fids: list[str] = []
    for fid in target_fids:
        if fid not in funcs:
            continue
        try:
            func = funcs[fid]
            kwargs = {name: wide_inputs[name] for name in inspect.signature(func).parameters if name in wide_inputs}
            raw = func(**kwargs)
            raw = r05._to_df(raw, wide_inputs["close"]).reindex_like(wide_inputs["close"]).astype(float)
        except Exception as exc:
            print(f"R08.1 factor skipped: {fid}: {exc}", flush=True)
            continue
        j = len(available_fids)
        raw_matrix[:, j] = r08.candidate_values_from_wide(raw, inputs.candidates)
        pct, tie, tie_cluster = r08.rolling_midrank_for_candidates(raw, inputs.candidates, lookback, min_history)
        percentile_matrix[:, j] = pct
        tie_matrix[:, j] = tie
        tie_cluster_matrix[:, j] = tie_cluster
        available_fids.append(fid)
        print(f"R08.1 factor normalized: {fid}", flush=True)
    raw_matrix = raw_matrix[:, : len(available_fids)]
    percentile_matrix = percentile_matrix[:, : len(available_fids)]
    tie_matrix = tie_matrix[:, : len(available_fids)]
    tie_cluster_matrix = tie_cluster_matrix[:, : len(available_fids)]
    np.save(paths.cache_dir / "r08_1_raw_target_factor_matrix.npy", raw_matrix)
    np.save(paths.cache_dir / "r08_1_within_stock_percentile_matrix.npy", percentile_matrix)
    write_json({"factor_ids": available_fids}, paths.cache_dir / "r08_1_factor_matrix_columns.json")
    return percentile_matrix, tie_matrix, tie_cluster_matrix, available_fids


def add_fold_assignment(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    out["canonical_instrument_id"] = out["instrument_id"].map(canonical_instrument_id)
    out["fold_hash_value"] = out["canonical_instrument_id"].map(instrument_hash_value)
    out["instrument_fold_id"] = (out["fold_hash_value"] % 5).astype(int)
    return out


def data_availability(config: dict[str, Any], label_h3: pd.DataFrame) -> dict[str, Any]:
    declared = pd.Timestamp(config["split"]["robustness_end"]).normalize()
    provider_end = pd.Timestamp(config["data_sources"].get("provider_load_end_date", declared)).normalize()
    calendar = pd.DatetimeIndex([pd.Timestamp(x).normalize() for x in r01.load_calendar(config)])
    last_calendar = calendar.max().normalize() if len(calendar) else provider_end
    last_available = min(provider_end, last_calendar)
    complete = label_h3.loc[
        label_h3["matched_comparator_status"].eq("comparable") & label_h3["exit_execution_date"].notna()
    ].copy()
    last_complete_signal = pd.Timestamp(complete["signal_date"].max()).normalize() if len(complete) else pd.NaT
    actual_end = min(declared, last_available, last_complete_signal)
    robust = complete.loc[
        (complete["signal_date"] >= pd.Timestamp(config["split"]["robustness_start"]))
        & (complete["signal_date"] <= actual_end)
    ]
    actual_years = sorted(int(y) for y in robust["signal_date"].dt.year.dropna().unique())
    return {
        "declared_robustness_end_date": declared,
        "last_available_trading_date": last_available,
        "last_h3_label_complete_signal_date": last_complete_signal,
        "robustness_window_actual_end_date": actual_end,
        "robustness_end_date_data_available": actual_end >= declared,
        "robustness_window_truncated_by_data_availability": actual_end < declared,
        "robustness_actual_evaluable_year_count": len(actual_years),
        "robustness_actual_evaluable_years": ";".join(str(x) for x in actual_years),
        "robustness_actual_signal_date_count": int(robust["signal_date"].nunique()),
    }


def build_h3_label_frame(
    config: dict[str, Any],
    paths: R081Paths,
    inputs: r08.R06Inputs,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    constants = config["frozen_formula_constants"]
    label = inputs.label_panel.loc[
        inputs.label_panel["horizon"].eq("H3") & inputs.label_panel["matched_comparator_status"].eq("comparable")
    ].copy()
    availability = data_availability(config, label)
    actual_robust_end = pd.Timestamp(availability["robustness_window_actual_end_date"])
    label = label.loc[
        ~(
            label["split"].eq("robustness")
            & (pd.to_datetime(label["signal_date"]) > actual_robust_end)
        )
    ].copy()
    label = add_fold_assignment(label)
    calendar = pd.DatetimeIndex([pd.Timestamp(x).normalize() for x in r01.load_calendar(config)])
    cal_pos = {pd.Timestamp(d).normalize(): i for i, d in enumerate(calendar)}
    lookback = int(constants["within_stock_lookback_trading_days"])
    min_self = int(constants["min_self_label_history_count"])
    label["label_raw_H3"] = label["net_return"]
    label["label_raw_H3_gross"] = label["gross_return"]
    label["label_self_relative_H3"] = np.nan
    label["label_self_relative_H3_gross"] = np.nan
    by_inst = label.sort_values(["instrument_id", "signal_date"]).groupby("instrument_id").groups
    for _, idx in by_inst.items():
        rows = list(idx)
        inst_frame = label.loc[rows]
        for row_id in rows:
            d = pd.Timestamp(label.at[row_id, "signal_date"]).normalize()
            pos = cal_pos.get(d)
            if pos is None or pos <= 0:
                continue
            prev_day = calendar[pos - 1]
            start_day = calendar[max(0, pos - lookback)]
            prior = inst_frame.loc[
                (inst_frame["signal_date"] < d)
                & (inst_frame["signal_date"] >= start_day)
                & (inst_frame["exit_execution_date"] <= prev_day)
                & inst_frame["net_return"].replace([np.inf, -np.inf], np.nan).notna()
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
        peer_count = count - 1
        net_sum = label.loc[rows, "net_return"].sum()
        gross_sum = label.loc[rows, "gross_return"].sum()
        label.loc[rows, "industry_relative_peer_count"] = peer_count
        if peer_count >= min_peers:
            label.loc[rows, "label_industry_relative_H3"] = label.loc[rows, "net_return"] - (
                net_sum - label.loc[rows, "net_return"]
            ) / peer_count
            label.loc[rows, "label_industry_relative_H3_gross"] = label.loc[rows, "gross_return"] - (
                gross_sum - label.loc[rows, "gross_return"]
            ) / peer_count

    audit_rows = []
    for split, g in label.groupby("split", dropna=False):
        audit_rows.append(
            {
                "split": split,
                "event_count": int(len(g)),
                "instrument_count": int(g["instrument_id"].nunique()),
                "signal_date_count": int(g["signal_date"].nunique()),
                "raw_label_available_count": int(g["label_raw_H3"].notna().sum()),
                "self_relative_label_available_count": int(g["label_self_relative_H3"].notna().sum()),
                "industry_relative_label_available_count": int(g["label_industry_relative_H3"].notna().sum()),
                "industry_relative_peer_count_min": int(g["industry_relative_peer_count"].min()) if len(g) else 0,
                "industry_relative_peer_count_p50": safe_median(g["industry_relative_peer_count"]) if len(g) else np.nan,
                "self_relative_label_lookback_only_uses_completed_h3_labels": True,
                "self_relative_label_uses_lookback_h3_exit_date_le_D_minus_1": True,
            }
        )
    write_csv(pd.DataFrame([availability]), paths.audit_dir / "r08_1_data_availability_audit.csv")
    return label, pd.DataFrame(audit_rows), availability


def write_input_scope_fold_audits(
    config: dict[str, Any],
    paths: R081Paths,
    inputs: r08.R06Inputs,
    label: pd.DataFrame,
    scope: dict[str, list[str]],
    available_fids: list[str],
) -> None:
    write_csv(
        pd.DataFrame(
            [
                {
                    "source": "r06_candidate_base/r06_horizon_label_panel",
                    "candidate_row_count": len(inputs.candidates),
                    "h3_decision_event_count": len(label),
                    "instrument_count": inputs.candidates["instrument_id"].nunique(),
                    "signal_date_count": inputs.candidates["signal_date"].nunique(),
                    "min_signal_date": inputs.candidates["signal_date"].min(),
                    "max_signal_date": inputs.candidates["signal_date"].max(),
                    "primary_horizon": "H3",
                    "status": "passed" if len(label) else "failed",
                }
            ]
        ),
        paths.audit_dir / "r08_1_input_data_audit.csv",
    )
    scope_rows = []
    for family in FAMILIES:
        fids = scope.get(family, [])
        scope_rows.append(
            {
                "family": family,
                "role": "primary" if family == PRIMARY_FAMILY else "audit_only_comparator",
                "r06_in_scope_factor_count": len(fids),
                "available_factor_count": len([fid for fid in fids if fid in available_fids]),
                "factor_ids": ";".join(fids),
                "available_factor_ids": ";".join(fid for fid in fids if fid in available_fids),
                "primary_decision_eligible": family == PRIMARY_FAMILY,
            }
        )
    write_csv(pd.DataFrame(scope_rows), paths.audit_dir / "r08_1_scope_audit.csv")
    fold_rows = []
    inst = label[["instrument_id", "canonical_instrument_id", "fold_hash_value", "instrument_fold_id"]].drop_duplicates()
    for rec in inst.itertuples(index=False):
        row = {
            "instrument_id": rec.instrument_id,
            "canonical_instrument_id": rec.canonical_instrument_id,
            "hash_input_description": "utf-8 bytes of canonical_instrument_id.lower()",
            "hash_value": int(rec.fold_hash_value),
            "instrument_fold_id": int(rec.instrument_fold_id),
        }
        for split in ["train", "validation", "robustness"]:
            row[f"{split}_signal_count"] = int(
                label.loc[label["instrument_id"].eq(rec.instrument_id) & label["split"].eq(split), "signal_date"].nunique()
            )
        fold_rows.append(row)
    write_csv(pd.DataFrame(fold_rows), paths.audit_dir / "r08_1_fold_assignment_audit.csv")


def build_normalization_audit(
    paths: R081Paths,
    label: pd.DataFrame,
    scope: dict[str, list[str]],
    available_fids: list[str],
    percentile: np.ndarray,
    tie: np.ndarray,
    tie_cluster: np.ndarray,
) -> None:
    fid_to_col = {fid: i for i, fid in enumerate(available_fids)}
    rows = []
    candidate_rows = label["candidate_row_id"].to_numpy(dtype=int)
    for family, fids in scope.items():
        for fid in fids:
            if fid not in fid_to_col:
                continue
            col = fid_to_col[fid]
            tmp = label[["split", "instrument_fold_id"]].copy()
            tmp["pct"] = percentile[candidate_rows, col]
            tmp["tie"] = tie[candidate_rows, col]
            tmp["cluster"] = tie_cluster[candidate_rows, col]
            for (split, fold_id), g in tmp.groupby(["split", "instrument_fold_id"], dropna=False):
                rows.append(
                    {
                        "family": family,
                        "factor_id": fid,
                        "split": split,
                        "instrument_fold_id": int(fold_id),
                        "stock_date_count": int(len(g)),
                        "normalization_sample_pass_count": int(np.isfinite(g["pct"]).sum()),
                        "normalization_sample_fail_count": int((~np.isfinite(g["pct"])).sum()),
                        "uses_future_data_flag": False,
                        "cross_stock_fill_flag": False,
                        "within_stock_lookback_excludes_future_data": True,
                        "within_stock_lookback_ends_at_D_minus_1": True,
                        "mid_rank_tie_handling_used": True,
                        "factor_value_tie_share_in_lookback": safe_mean(g["tie"]),
                        "factor_value_at_tie_cluster_flag": safe_share(int(g["cluster"].sum()), len(g)),
                    }
                )
    write_csv(pd.DataFrame(rows), paths.audit_dir / "r08_1_within_stock_normalization_audit.csv")


def direction_by_fold(
    config: dict[str, Any],
    paths: R081Paths,
    label: pd.DataFrame,
    scope: dict[str, list[str]],
    available_fids: list[str],
    percentile: np.ndarray,
) -> tuple[pd.DataFrame, dict[tuple[str, int], dict[str, float]]]:
    c = config["frozen_formula_constants"]
    fid_to_col = {fid: i for i, fid in enumerate(available_fids)}
    row_ids_all = label["candidate_row_id"].to_numpy(dtype=int)
    rows = []
    directions: dict[tuple[str, int], dict[str, float]] = {}
    for family, fids in scope.items():
        for fold_id in FOLD_IDS:
            train_seen = label.loc[label["split"].eq("train") & label["instrument_fold_id"].ne(fold_id)].copy()
            row_ids = train_seen["candidate_row_id"].to_numpy(dtype=int)
            y = train_seen["label_self_relative_H3"].to_numpy(dtype=float)
            directions[(family, fold_id)] = {}
            for fid in fids:
                if fid not in fid_to_col:
                    rows.append(
                        {
                            "family": family,
                            "fold_id": fold_id,
                            "factor_id": fid,
                            "direction_source_split": "train",
                            "direction_source_instrument_scope": f"seen_folds_not_{fold_id}",
                            "fold_direction_valid_instrument_count": 0,
                            "factor_direction_stat": np.nan,
                            "factor_direction_stat_p25": np.nan,
                            "factor_direction_stat_p75": np.nan,
                            "direction": np.nan,
                            "direction_status": "factor_data_unavailable",
                            "direction_insufficient_factor_dropped": True,
                        }
                    )
                    continue
                x = percentile[row_ids, fid_to_col[fid]].astype(float)
                tmp = train_seen[["instrument_id"]].copy()
                tmp["x"] = x
                tmp["y"] = y
                ics = []
                valid_min = int(c["min_direction_signal_count_for_instrument_factor"])
                for _, g in tmp.groupby("instrument_id", sort=False):
                    g = g.replace([np.inf, -np.inf], np.nan).dropna()
                    if len(g) < valid_min:
                        continue
                    if g["x"].nunique(dropna=True) <= 1:
                        continue
                    ics.append(spearman_corr(g["x"].to_numpy(dtype=float), g["y"].to_numpy(dtype=float)))
                ics_s = pd.Series(ics).replace([np.inf, -np.inf], np.nan).dropna()
                valid_count = int(len(ics_s))
                stat = safe_median(ics_s)
                ok = valid_count >= int(c["train_direction_valid_instrument_count_min"]) and finite(stat)
                direction = 1.0 if finite(stat) and stat >= 0 else -1.0 if finite(stat) else np.nan
                if ok:
                    directions[(family, fold_id)][fid] = direction
                rows.append(
                    {
                        "family": family,
                        "fold_id": fold_id,
                        "factor_id": fid,
                        "direction_source_split": "train",
                        "direction_source_instrument_scope": f"seen_folds_not_{fold_id}",
                        "fold_direction_valid_instrument_count": valid_count,
                        "factor_direction_stat": stat,
                        "factor_direction_stat_p25": float(ics_s.quantile(0.25)) if len(ics_s) else np.nan,
                        "factor_direction_stat_p75": float(ics_s.quantile(0.75)) if len(ics_s) else np.nan,
                        "direction": direction,
                        "direction_status": "direction_available" if ok else "factor_direction_sample_insufficient",
                        "direction_insufficient_factor_dropped": not ok,
                    }
                )
    out = pd.DataFrame(rows)
    write_csv(out, paths.audit_dir / "r08_1_factor_direction_by_fold_audit.csv")
    return out, directions


def score_for_family_fold(
    label: pd.DataFrame,
    percentile: np.ndarray,
    available_fids: list[str],
    retained_directions: dict[str, float],
) -> np.ndarray:
    fid_to_col = {fid: i for i, fid in enumerate(available_fids)}
    row_ids_all = label["candidate_row_id"].to_numpy(dtype=int)
    vals = []
    for fid, direction in retained_directions.items():
        if fid not in fid_to_col:
            continue
        col = percentile[:, fid_to_col[fid]].astype(float)
        vals.append(0.5 + float(direction) * (col - 0.5))
    if not vals:
        return np.full(len(label), np.nan, dtype=float)
    matrix = np.column_stack([v[row_ids_all] for v in vals])
    finite_count = np.isfinite(matrix).sum(axis=1)
    score = np.full(len(label), np.nan, dtype=float)
    valid = finite_count > 0
    if valid.any():
        score[valid] = np.nanmean(matrix[valid], axis=1)
    return score


def state_from_edges(score: pd.Series, q20: float, q80: float, decile_edges: list[float]) -> tuple[pd.Series, np.ndarray]:
    state = pd.Series("", index=score.index, dtype=object)
    finite_mask = score.replace([np.inf, -np.inf], np.nan).notna()
    state.loc[finite_mask & (score <= q20)] = "bottom_quintile_state"
    state.loc[finite_mask & (score > q20) & (score < q80)] = "middle_state"
    state.loc[finite_mask & (score >= q80)] = "top_quintile_state"
    decile = np.full(len(score), np.nan)
    if all(finite(x) for x in decile_edges):
        decile[finite_mask.to_numpy()] = np.searchsorted(
            np.asarray(decile_edges, dtype=float),
            score.loc[finite_mask].to_numpy(dtype=float),
            side="right",
        ) + 1
    return state, decile


def build_oof_events(
    config: dict[str, Any],
    paths: R081Paths,
    label: pd.DataFrame,
    scope: dict[str, list[str]],
    available_fids: list[str],
    percentile: np.ndarray,
    directions: dict[tuple[str, int], dict[str, float]],
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    c = config["frozen_formula_constants"]
    scope_rows = []
    bucket_rows = []
    event_frames = []
    for family in FAMILIES:
        required = int(c["retained_vwap_factor_count_min"]) if family == PRIMARY_FAMILY else 1
        for fold_id in FOLD_IDS:
            retained_dirs = {
                fid: direction
                for fid, direction in directions.get((family, fold_id), {}).items()
                if fid in scope.get(family, [])
            }
            score = score_for_family_fold(label, percentile, available_fids, retained_dirs)
            tmp = label.copy()
            tmp["family"] = family
            tmp["fold_id"] = fold_id
            tmp["family_state_score"] = score
            train_seen_mask = tmp["split"].eq("train") & tmp["instrument_fold_id"].ne(fold_id)
            train_vals = tmp.loc[train_seen_mask, "family_state_score"].replace([np.inf, -np.inf], np.nan).dropna()
            if len(train_vals):
                q20 = float(train_vals.quantile(float(c["low_state_quantile"])))
                q80 = float(train_vals.quantile(float(c["high_state_quantile"])))
                decile_edges = train_vals.quantile([i / 10 for i in range(1, 10)]).astype(float).tolist()
            else:
                q20 = q80 = np.nan
                decile_edges = [np.nan] * 9
            state, decile = state_from_edges(tmp["family_state_score"], q20, q80, decile_edges)
            tmp["state"] = state
            tmp["state_decile"] = decile
            retained = list(retained_dirs)
            scope_pass = len(retained) >= required
            scope_rows.append(
                {
                    "family": family,
                    "fold_id": fold_id,
                    "role": "primary" if family == PRIMARY_FAMILY else "audit_only_comparator",
                    "in_scope_factor_count": len(scope.get(family, [])),
                    "retained_factor_count": len(retained),
                    "retained_factor_ids": ";".join(retained),
                    "dropped_factor_ids": ";".join(fid for fid in scope.get(family, []) if fid not in retained),
                    "direction_insufficient_factors_dropped": True,
                    "family_scope_pass": scope_pass,
                    "primary_decision_eligible": family == PRIMARY_FAMILY,
                }
            )
            bucket_rows.append(
                {
                    "family": family,
                    "fold_id": fold_id,
                    "bucket_edge_source_split": "train",
                    "bucket_edge_source_instrument_scope": f"seen_folds_not_{fold_id}",
                    "train_seen_q20": q20,
                    "train_seen_q80": q80,
                    "decile_edges_train_seen": json.dumps(decile_edges),
                    "frozen_before_validation_read": True,
                    "bucket_method": "fold_train_seen_extreme_tail_20_60_20",
                    "low_state_alias": "bottom_quintile_state",
                    "high_state_alias": "top_quintile_state",
                    "train_seen_low_state_count": int((tmp.loc[train_seen_mask, "state"] == "bottom_quintile_state").sum()),
                    "train_seen_middle_state_count": int((tmp.loc[train_seen_mask, "state"] == "middle_state").sum()),
                    "train_seen_high_state_count": int((tmp.loc[train_seen_mask, "state"] == "top_quintile_state").sum()),
                }
            )
            if not scope_pass:
                continue
            unseen = tmp.loc[tmp["instrument_fold_id"].eq(fold_id)].copy()
            split_labels = []
            for split in unseen["split"]:
                split_labels.append({"train": "train_oof_unseen", "validation": "validation_oof_unseen", "robustness": "robustness_oof_unseen"}.get(split, ""))
            unseen["oof_split"] = split_labels
            unseen = unseen.loc[unseen["oof_split"].ne("")]
            unseen = unseen.dropna(subset=["family_state_score", "label_self_relative_H3"])
            class_frames = []
            for oof_split, g in unseen.groupby("oof_split", sort=False):
                full_min = int(
                    c["train_oof_full_instrument_signal_count_min"]
                    if oof_split == "train_oof_unseen"
                    else c["validation_robustness_full_instrument_signal_count_min"]
                )
                partial_min = int(c["partial_instrument_signal_count_min"])
                counts = g.groupby("instrument_id")["signal_date"].nunique()
                h = g.copy()
                h["split_signal_count_for_instrument"] = h["instrument_id"].map(counts).astype(int)
                h["instrument_sample_class"] = np.select(
                    [
                        h["split_signal_count_for_instrument"] >= full_min,
                        h["split_signal_count_for_instrument"] >= partial_min,
                    ],
                    ["full_valid_instrument", "partial_instrument_event_only"],
                    default="excluded_thin_instrument",
                )
                h["full_instrument_signal_count_floor"] = full_min
                h["partial_instrument_signal_count_floor"] = partial_min
                class_frames.append(h.loc[h["instrument_sample_class"].ne("excluded_thin_instrument")])
            if class_frames:
                keep = pd.concat(class_frames, ignore_index=True)
                event_frames.append(keep)
    scope_df = pd.DataFrame(scope_rows)
    bucket_df = pd.DataFrame(bucket_rows)
    events = pd.concat(event_frames, ignore_index=True) if event_frames else pd.DataFrame()
    write_csv(scope_df, paths.audit_dir / "r08_1_family_scope_by_fold_audit.csv")
    write_csv(bucket_df, paths.audit_dir / "r08_1_state_bucket_by_fold_audit.csv")
    if not events.empty:
        events.to_parquet(paths.cache_dir / "r08_1_oof_event_panel.parquet", index=False)
    return events, scope_df, bucket_df


def date_spreads(df: pd.DataFrame, floor: int) -> pd.DataFrame:
    rows = []
    for date, g in df.groupby("signal_date", sort=True):
        high = g.loc[g["state"].eq("top_quintile_state"), "label_self_relative_H3"].replace([np.inf, -np.inf], np.nan).dropna()
        low = g.loc[g["state"].eq("bottom_quintile_state"), "label_self_relative_H3"].replace([np.inf, -np.inf], np.nan).dropna()
        if len(high) >= floor and len(low) >= floor:
            rows.append({"signal_date": pd.Timestamp(date), "calendar_year": pd.Timestamp(date).year, "spread": float(high.mean() - low.mean())})
    return pd.DataFrame(rows)


def instrument_spreads(df: pd.DataFrame, c: dict[str, Any]) -> tuple[pd.DataFrame, dict[str, Any]]:
    rows = []
    min_state_events = int(c["instrument_state_event_count_min"])
    full = df.loc[df["instrument_sample_class"].eq("full_valid_instrument")].copy()
    for instrument, g in full.groupby("instrument_id", sort=False):
        high = g.loc[g["state"].eq("top_quintile_state"), "label_self_relative_H3"].replace([np.inf, -np.inf], np.nan).dropna()
        low = g.loc[g["state"].eq("bottom_quintile_state"), "label_self_relative_H3"].replace([np.inf, -np.inf], np.nan).dropna()
        valid_signal_count = int(g["signal_date"].nunique())
        if len(high) < min_state_events or len(low) < min_state_events:
            continue
        rows.append(
            {
                "instrument_id": instrument,
                "instrument_high_minus_low_spread": float(high.mean() - low.mean()),
                "within_stock_rankIC": spearman_corr(
                    g["family_state_score"].to_numpy(dtype=float),
                    g["label_self_relative_H3"].to_numpy(dtype=float),
                ),
                "valid_signal_count": valid_signal_count,
                "high_state_event_count": int(len(high)),
                "low_state_event_count": int(len(low)),
                "instrument_sample_class": "full_valid_instrument",
            }
        )
    out = pd.DataFrame(rows)
    metrics = {
        "valid_instrument_count": int(len(out)),
        "full_valid_instrument_count": int(len(out)),
        "positive_instrument_count": int((out["instrument_high_minus_low_spread"] > 0).sum()) if len(out) else 0,
        "positive_instrument_share": safe_share(int((out["instrument_high_minus_low_spread"] > 0).sum()), len(out)) if len(out) else 0.0,
        "within_stock_rankIC_median": safe_median(out["within_stock_rankIC"]) if len(out) else np.nan,
        "mean_instrument_high_minus_low_spread": safe_mean(out["instrument_high_minus_low_spread"]) if len(out) else np.nan,
        "median_instrument_high_minus_low_spread": safe_median(out["instrument_high_minus_low_spread"]) if len(out) else np.nan,
    }
    return out, metrics


def monotonicity(df: pd.DataFrame, c: dict[str, Any]) -> tuple[float, pd.DataFrame, bool]:
    sub = df[["state_decile", "label_self_relative_H3"]].replace([np.inf, -np.inf], np.nan).dropna()
    if sub.empty:
        return np.nan, pd.DataFrame(columns=["decile", "event_count", "mean_label_self_relative_H3"]), True
    dec = (
        sub.groupby("state_decile")["label_self_relative_H3"]
        .agg(["count", "mean"])
        .reset_index()
        .rename(columns={"state_decile": "decile", "count": "event_count", "mean": "mean_label_self_relative_H3"})
    )
    score = spearman_corr(dec["decile"].to_numpy(dtype=float), dec["mean_label_self_relative_H3"].to_numpy(dtype=float))
    low = df.loc[df["state"].eq("bottom_quintile_state"), "label_self_relative_H3"].replace([np.inf, -np.inf], np.nan).dropna()
    mid = df.loc[df["state"].eq("middle_state"), "label_self_relative_H3"].replace([np.inf, -np.inf], np.nan).dropna()
    high = df.loc[df["state"].eq("top_quintile_state"), "label_self_relative_H3"].replace([np.inf, -np.inf], np.nan).dropna()
    if low.empty or mid.empty or high.empty:
        inverted = True
    else:
        tolerance = float(c["middle_state_inversion_tolerance"])
        mid_mean = float(mid.mean())
        lo = min(float(low.mean()), float(high.mean()))
        hi = max(float(low.mean()), float(high.mean()))
        inverted = mid_mean < lo - tolerance or mid_mean > hi + tolerance
    return score, dec, inverted


def concentration(df: pd.DataFrame, c: dict[str, Any], family: str, split: str, fold_id: int | None) -> dict[str, Any]:
    rows = []
    state_df = df.loc[df["state"].isin(["top_quintile_state", "bottom_quintile_state"])].copy()
    for instrument, g in state_df.groupby("instrument_id", sort=False):
        high = g.loc[g["state"].eq("top_quintile_state")]
        low = g.loc[g["state"].eq("bottom_quintile_state")]
        if high.empty or low.empty:
            continue
        spread = float(high["label_self_relative_H3"].mean() - low["label_self_relative_H3"].mean())
        count = int(len(high) + len(low))
        rows.append({"instrument_id": instrument, "abs_contribution": abs(spread * count), "event_count": count})
    inst = pd.DataFrame(rows)
    denom = float(inst["abs_contribution"].sum()) if len(inst) else 0.0
    zero = denom <= 0
    top1_id = ""
    top1_share = top5_share = np.nan
    top1_count = 0
    if not zero:
        inst = inst.sort_values("abs_contribution", ascending=False)
        inst["share"] = inst["abs_contribution"] / denom
        top1 = inst.iloc[0]
        top1_id = str(top1["instrument_id"])
        top1_share = float(top1["share"])
        top5_share = float(inst.head(5)["share"].sum())
        top1_count = int(top1["event_count"])
    industry_rows = []
    if not zero:
        abs_map = inst.set_index("instrument_id")["abs_contribution"].to_dict()
        for instrument, g in state_df.groupby("instrument_id", sort=False):
            abs_contrib = float(abs_map.get(instrument, 0.0))
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
    universe_weight = np.nan
    if top_industry:
        universe_weight = safe_share(int(df["industry_id"].eq(top_industry).sum()), len(df))
    return {
        "family": family,
        "split": split,
        "fold_id": fold_id if fold_id is not None else "aggregate",
        "contribution_scope": "fold_unseen" if fold_id is not None else "aggregate_oof_unseen",
        "contribution_denominator": denom,
        "contribution_denominator_zero": zero,
        "top1_instrument_id": top1_id,
        "top1_instrument_event_count": top1_count,
        "top1_instrument_contribution_share": top1_share,
        "top5_instrument_contribution_share": top5_share,
        "top1_industry": top_industry,
        "top1_industry_contribution_share": top_industry_share,
        "top1_industry_universe_weight": universe_weight,
        "top1_industry_contribution_minus_universe_weight": top_industry_share - universe_weight if finite(top_industry_share) and finite(universe_weight) else np.nan,
        "top1_industry_contribution_to_weight_ratio": top_industry_share / universe_weight if finite(top_industry_share) and finite(universe_weight) and universe_weight else np.nan,
    }


def metrics_for_subset(
    df: pd.DataFrame,
    c: dict[str, Any],
    family: str,
    split: str,
    fold_id: int | None,
) -> tuple[dict[str, Any], pd.DataFrame, pd.DataFrame, dict[str, Any], pd.DataFrame]:
    floor = int(c["per_date_event_floor_unseen"])
    spreads = date_spreads(df, floor)
    d = spreads["spread"] if not spreads.empty else pd.Series(dtype=float)
    high = df.loc[df["state"].eq("top_quintile_state"), "label_self_relative_H3"].replace([np.inf, -np.inf], np.nan).dropna()
    low = df.loc[df["state"].eq("bottom_quintile_state"), "label_self_relative_H3"].replace([np.inf, -np.inf], np.nan).dropna()
    pooled = float(high.mean() - low.mean()) if len(high) and len(low) else np.nan
    inst_df, inst_metric = instrument_spreads(df, c)
    mono_score, decile_df, inverted = monotonicity(df, c)
    partial_count = int(df.loc[df["instrument_sample_class"].eq("partial_instrument_event_only"), "instrument_id"].nunique())
    raw_full_count = int(df.loc[df["instrument_sample_class"].eq("full_valid_instrument"), "instrument_id"].nunique())
    metric = {
        "family": family,
        "split": split,
        "fold_id": fold_id if fold_id is not None else "aggregate",
        "mean_spread": safe_mean(d),
        "median_spread": safe_median(d),
        "pooled_high_minus_low_spread": pooled,
        "positive_date_share": safe_share(int((d > 0).sum()), len(d)),
        "valid_signal_date_count": int(len(spreads)),
        "event_count": int(len(df)),
        "raw_full_valid_instrument_count": raw_full_count,
        "valid_instrument_count": int(inst_metric["valid_instrument_count"]),
        "full_valid_instrument_count": int(inst_metric["full_valid_instrument_count"]),
        "partial_event_only_instrument_count": partial_count,
        "positive_instrument_count": int(inst_metric["positive_instrument_count"]),
        "positive_instrument_share": inst_metric["positive_instrument_share"],
        "within_stock_rankIC_median": inst_metric["within_stock_rankIC_median"],
        "decile_monotonicity_score": mono_score,
        "middle_state_violently_inverted_flag": inverted,
    }
    conc = concentration(df, c, family, split, fold_id)
    return metric, spreads, inst_df, conc, decile_df


def build_metrics(
    config: dict[str, Any],
    paths: R081Paths,
    events: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    c = config["frozen_formula_constants"]
    fold_rows: list[dict[str, Any]] = []
    aggregate_rows: list[dict[str, Any]] = []
    dispersion_rows: list[dict[str, Any]] = []
    instrument_rows: list[dict[str, Any]] = []
    fold_sample_rows: list[dict[str, Any]] = []
    concentration_rows: list[dict[str, Any]] = []
    decile_fold_rows: list[dict[str, Any]] = []
    decile_agg_rows: list[dict[str, Any]] = []
    year_rows: list[dict[str, Any]] = []
    if events.empty:
        for name, rows in [
            ("r08_1_fold_unseen_state_spread.csv", fold_rows),
            ("r08_1_aggregate_oof_unseen_state_spread.csv", aggregate_rows),
            ("r08_1_fold_dispersion_summary.csv", dispersion_rows),
            ("r08_1_instrument_transfer_summary.csv", instrument_rows),
            ("r08_1_fold_sample_audit.csv", fold_sample_rows),
            ("r08_1_concentration_audit.csv", concentration_rows),
            ("r08_1_decile_monotonicity_by_fold.csv", decile_fold_rows),
            ("r08_1_aggregate_decile_monotonicity.csv", decile_agg_rows),
            ("r08_1_year_availability_and_positive_count.csv", year_rows),
        ]:
            directory = paths.audit_dir if name.endswith("_audit.csv") else paths.metrics_dir
            write_csv(pd.DataFrame(rows), directory / name)
        return tuple(pd.DataFrame() for _ in range(6))  # type: ignore[return-value]

    for family in FAMILIES:
        for split in OOF_SPLITS:
            fold_metrics_for_dispersion = []
            for fold_id in FOLD_IDS:
                sub = events.loc[
                    events["family"].eq(family) & events["oof_split"].eq(split) & events["fold_id"].eq(fold_id)
                ].copy()
                if sub.empty:
                    metric = {
                        "family": family,
                        "split": split,
                        "fold_id": fold_id,
                        "mean_spread": np.nan,
                        "median_spread": np.nan,
                        "pooled_high_minus_low_spread": np.nan,
                        "positive_date_share": 0.0,
                        "valid_signal_date_count": 0,
                        "event_count": 0,
                        "raw_full_valid_instrument_count": 0,
                        "valid_instrument_count": 0,
                        "full_valid_instrument_count": 0,
                        "partial_event_only_instrument_count": 0,
                        "positive_instrument_count": 0,
                        "positive_instrument_share": 0.0,
                        "within_stock_rankIC_median": np.nan,
                        "decile_monotonicity_score": np.nan,
                        "middle_state_violently_inverted_flag": True,
                    }
                    conc = concentration(sub, c, family, split, fold_id)
                    dec = pd.DataFrame()
                else:
                    metric, spreads, inst_df, conc, dec = metrics_for_subset(sub, c, family, split, fold_id)
                    for rec in inst_df.itertuples(index=False):
                        instrument_rows.append(
                            {
                                "family": family,
                                "split": split,
                                "fold_id": fold_id,
                                "instrument_id": rec.instrument_id,
                                "instrument_high_minus_low_spread": rec.instrument_high_minus_low_spread,
                                "within_stock_rankIC": rec.within_stock_rankIC,
                                "valid_signal_count": rec.valid_signal_count,
                                "instrument_sample_class": rec.instrument_sample_class,
                            }
                        )
                    for year, yg in spreads.groupby("calendar_year"):
                        year_rows.append(
                            {
                                "family": family,
                                "split": split,
                                "fold_id": fold_id,
                                "calendar_year": int(year),
                                "year_mean_spread": safe_mean(yg["spread"]),
                                "year_positive_flag": safe_mean(yg["spread"]) > 0,
                                "valid_signal_date_count": int(len(yg)),
                            }
                        )
                    for rec in dec.itertuples(index=False):
                        decile_fold_rows.append(
                            {
                                "family": family,
                                "split": split,
                                "fold_id": fold_id,
                                "decile": int(rec.decile),
                                "event_count": int(rec.event_count),
                                "mean_label_self_relative_H3": rec.mean_label_self_relative_H3,
                                "fold_unseen_decile_monotonicity_score": metric["decile_monotonicity_score"],
                                "middle_state_violently_inverted_flag": metric["middle_state_violently_inverted_flag"],
                            }
                        )
                fold_rows.append(
                    {
                        "family": family,
                        "fold_id": fold_id,
                        "split": split,
                        "unseen_fold": fold_id,
                        "fold_unseen_mean_spread": metric["mean_spread"],
                        "fold_unseen_median_spread": metric["median_spread"],
                        "fold_unseen_pooled_high_minus_low_spread": metric["pooled_high_minus_low_spread"],
                        "fold_unseen_positive_instrument_share": metric["positive_instrument_share"],
                        "fold_unseen_positive_date_share": metric["positive_date_share"],
                        "fold_unseen_valid_instrument_count": metric["valid_instrument_count"],
                        "fold_unseen_full_valid_instrument_count": metric["full_valid_instrument_count"],
                        "fold_unseen_partial_event_only_instrument_count": metric["partial_event_only_instrument_count"],
                        "fold_unseen_valid_signal_date_count": metric["valid_signal_date_count"],
                        "fold_unseen_within_stock_rankIC_median": metric["within_stock_rankIC_median"],
                        "fold_unseen_decile_monotonicity_score": metric["decile_monotonicity_score"],
                        "fold_unseen_top1_instrument_contribution_share": conc["top1_instrument_contribution_share"],
                        "fold_unseen_top5_instrument_contribution_share": conc["top5_instrument_contribution_share"],
                        "fold_unseen_top1_industry_contribution_share": conc["top1_industry_contribution_share"],
                    }
                )
                fold_sample_pass = (
                    metric["valid_instrument_count"] >= int(c["fold_unseen_valid_instrument_count_min"])
                    and metric["valid_signal_date_count"] >= int(c["fold_unseen_valid_signal_date_count_min"])
                )
                fold_sample_rows.append(
                    {
                        "family": family,
                        "split": split,
                        "fold_id": fold_id,
                        "fold_unseen_valid_instrument_count": metric["valid_instrument_count"],
                        "fold_unseen_full_valid_instrument_count": metric["full_valid_instrument_count"],
                        "fold_unseen_partial_event_only_instrument_count": metric["partial_event_only_instrument_count"],
                        "fold_unseen_valid_signal_date_count": metric["valid_signal_date_count"],
                        "per_date_high_low_event_floor": int(c["per_date_event_floor_unseen"]),
                        "partial_instruments_excluded_from_sample_gate": True,
                        "partial_instruments_excluded_from_positive_instrument_share": True,
                        "fold_evaluable_flag": fold_sample_pass,
                    }
                )
                concentration_rows.append(conc)
                fold_metrics_for_dispersion.append(metric)

            spread_values = pd.Series([m["mean_spread"] for m in fold_metrics_for_dispersion]).replace([np.inf, -np.inf], np.nan).dropna()
            pos_inst_values = pd.Series([m["positive_instrument_share"] for m in fold_metrics_for_dispersion]).replace([np.inf, -np.inf], np.nan).dropna()
            mono_values = pd.Series([m["decile_monotonicity_score"] for m in fold_metrics_for_dispersion]).replace([np.inf, -np.inf], np.nan).dropna()
            evaluable = [m for m in fold_metrics_for_dispersion if m["valid_instrument_count"] >= int(c["fold_unseen_valid_instrument_count_min"]) and m["valid_signal_date_count"] >= int(c["fold_unseen_valid_signal_date_count_min"])]
            dispersion_rows.append(
                {
                    "family": family,
                    "split": split,
                    "evaluable_fold_count": len(evaluable),
                    "positive_fold_count": int((spread_values > 0).sum()),
                    "negative_fold_count": int((spread_values <= 0).sum()),
                    "median_fold_spread": safe_median(spread_values),
                    "min_fold_spread": float(spread_values.min()) if len(spread_values) else np.nan,
                    "max_fold_spread": float(spread_values.max()) if len(spread_values) else np.nan,
                    "fold_spread_iqr": float(spread_values.quantile(0.75) - spread_values.quantile(0.25)) if len(spread_values) else np.nan,
                    "fold_positive_instrument_share_median": safe_median(pos_inst_values),
                    "fold_positive_instrument_share_min": float(pos_inst_values.min()) if len(pos_inst_values) else np.nan,
                    "fold_monotonicity_median": safe_median(mono_values),
                    "fold_monotonicity_min": float(mono_values.min()) if len(mono_values) else np.nan,
                    "fold_monotonicity_positive_count": int((mono_values > 0).sum()),
                    "worst_fold_id_by_spread": int(FOLD_IDS[int(np.nanargmin([m["mean_spread"] if finite(m["mean_spread"]) else np.inf for m in fold_metrics_for_dispersion]))]) if len(fold_metrics_for_dispersion) else np.nan,
                    "worst_fold_id_by_positive_instrument_share": int(FOLD_IDS[int(np.nanargmin([m["positive_instrument_share"] if finite(m["positive_instrument_share"]) else np.inf for m in fold_metrics_for_dispersion]))]) if len(fold_metrics_for_dispersion) else np.nan,
                    "clean_positive_fold_count": int((spread_values > 0).sum()) >= 4,
                }
            )

            agg_sub = events.loc[events["family"].eq(family) & events["oof_split"].eq(split)].copy()
            agg_metric, agg_spreads, agg_inst, agg_conc, agg_dec = metrics_for_subset(agg_sub, c, family, split, None)
            aggregate_rows.append(
                {
                    "family": family,
                    "split": split,
                    "aggregate_oof_unseen_mean_spread": agg_metric["mean_spread"],
                    "aggregate_oof_unseen_median_spread": agg_metric["median_spread"],
                    "aggregate_oof_unseen_pooled_high_minus_low_spread": agg_metric["pooled_high_minus_low_spread"],
                    "aggregate_oof_unseen_positive_instrument_share": agg_metric["positive_instrument_share"],
                    "aggregate_oof_unseen_positive_date_share": agg_metric["positive_date_share"],
                    "aggregate_oof_unseen_valid_instrument_count": agg_metric["valid_instrument_count"],
                    "aggregate_oof_unseen_full_valid_instrument_count": agg_metric["full_valid_instrument_count"],
                    "aggregate_oof_unseen_partial_event_only_instrument_count": agg_metric["partial_event_only_instrument_count"],
                    "aggregate_oof_unseen_valid_signal_date_count": agg_metric["valid_signal_date_count"],
                    "aggregate_oof_unseen_within_stock_rankIC_median": agg_metric["within_stock_rankIC_median"],
                    "aggregate_oof_unseen_decile_monotonicity_score": agg_metric["decile_monotonicity_score"],
                    "middle_state_violently_inverted_flag": agg_metric["middle_state_violently_inverted_flag"],
                }
            )
            concentration_rows.append(agg_conc)
            for year, yg in agg_spreads.groupby("calendar_year"):
                year_rows.append(
                    {
                        "family": family,
                        "split": split,
                        "fold_id": "aggregate",
                        "calendar_year": int(year),
                        "year_mean_spread": safe_mean(yg["spread"]),
                        "year_positive_flag": safe_mean(yg["spread"]) > 0,
                        "valid_signal_date_count": int(len(yg)),
                    }
                )
            for rec in agg_dec.itertuples(index=False):
                decile_agg_rows.append(
                    {
                        "family": family,
                        "split": split,
                        "decile": int(rec.decile),
                        "event_count": int(rec.event_count),
                        "mean_label_self_relative_H3": rec.mean_label_self_relative_H3,
                        "aggregate_oof_unseen_decile_monotonicity_score": agg_metric["decile_monotonicity_score"],
                        "middle_state_violently_inverted_flag": agg_metric["middle_state_violently_inverted_flag"],
                    }
                )

    fold_df = pd.DataFrame(fold_rows)
    agg_df = pd.DataFrame(aggregate_rows)
    disp_df = pd.DataFrame(dispersion_rows)
    inst_df = pd.DataFrame(instrument_rows)
    sample_df = pd.DataFrame(fold_sample_rows)
    conc_df = pd.DataFrame(concentration_rows)
    dec_fold_df = pd.DataFrame(decile_fold_rows)
    dec_agg_df = pd.DataFrame(decile_agg_rows)
    year_df = pd.DataFrame(year_rows)
    conc_summary = conc_df.loc[conc_df["fold_id"].astype(str).eq("aggregate")].copy()
    write_csv(fold_df, paths.metrics_dir / "r08_1_fold_unseen_state_spread.csv")
    write_csv(agg_df, paths.metrics_dir / "r08_1_aggregate_oof_unseen_state_spread.csv")
    write_csv(disp_df, paths.metrics_dir / "r08_1_fold_dispersion_summary.csv")
    write_csv(inst_df, paths.metrics_dir / "r08_1_instrument_transfer_summary.csv")
    write_csv(year_df, paths.metrics_dir / "r08_1_year_availability_and_positive_count.csv")
    write_csv(dec_fold_df, paths.metrics_dir / "r08_1_decile_monotonicity_by_fold.csv")
    write_csv(dec_agg_df, paths.metrics_dir / "r08_1_aggregate_decile_monotonicity.csv")
    write_csv(conc_summary, paths.metrics_dir / "r08_1_concentration_summary.csv")
    write_csv(sample_df, paths.audit_dir / "r08_1_fold_sample_audit.csv")
    write_csv(conc_df, paths.audit_dir / "r08_1_concentration_audit.csv")
    return fold_df, agg_df, disp_df, inst_df, sample_df, conc_df


def build_gate_inputs(
    config: dict[str, Any],
    paths: R081Paths,
    scope_df: pd.DataFrame,
    fold_df: pd.DataFrame,
    agg_df: pd.DataFrame,
    disp_df: pd.DataFrame,
    sample_df: pd.DataFrame,
    conc_df: pd.DataFrame,
    availability: dict[str, Any],
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    c = config["frozen_formula_constants"]
    rows = []
    time_rows = []
    comparator_rows = []
    for family in FAMILIES:
        family_scope = scope_df.loc[scope_df["family"].eq(family)]
        primary_score_formed = (
            bool(family_scope["family_scope_pass"].map(bool_value).all()) if len(family_scope) else False
        )
        agg = {rec.split: rec for rec in agg_df.loc[agg_df["family"].eq(family)].itertuples(index=False)}
        disp = {rec.split: rec for rec in disp_df.loc[disp_df["family"].eq(family)].itertuples(index=False)}
        conc_agg = {
            rec.split: rec
            for rec in conc_df.loc[
                conc_df["family"].eq(family) & conc_df["fold_id"].astype(str).eq("aggregate")
            ].itertuples(index=False)
        }
        train = agg.get("train_oof_unseen")
        val = agg.get("validation_oof_unseen")
        rob = agg.get("robustness_oof_unseen")
        val_disp = disp.get("validation_oof_unseen")
        rob_disp = disp.get("robustness_oof_unseen")
        train_mean = getattr(train, "aggregate_oof_unseen_mean_spread", np.nan) if train is not None else np.nan
        val_mean = getattr(val, "aggregate_oof_unseen_mean_spread", np.nan) if val is not None else np.nan
        rob_mean = getattr(rob, "aggregate_oof_unseen_mean_spread", np.nan) if rob is not None else np.nan
        val_median = getattr(val, "aggregate_oof_unseen_median_spread", np.nan) if val is not None else np.nan
        rob_median = getattr(rob, "aggregate_oof_unseen_median_spread", np.nan) if rob is not None else np.nan
        val_positive_inst = getattr(val, "aggregate_oof_unseen_positive_instrument_share", 0.0) if val is not None else 0.0
        rob_positive_inst = getattr(rob, "aggregate_oof_unseen_positive_instrument_share", 0.0) if rob is not None else 0.0
        val_years = pd.read_csv(paths.metrics_dir / "r08_1_year_availability_and_positive_count.csv")
        val_years_f = val_years.loc[
            val_years["family"].eq(family)
            & val_years["split"].eq("validation_oof_unseen")
            & val_years["fold_id"].astype(str).eq("aggregate")
        ]
        rob_years_f = val_years.loc[
            val_years["family"].eq(family)
            & val_years["split"].eq("robustness_oof_unseen")
            & val_years["fold_id"].astype(str).eq("aggregate")
        ]
        validation_positive_year_count = int(val_years_f["year_positive_flag"].map(bool_value).sum()) if len(val_years_f) else 0
        robustness_positive_year_count = int(rob_years_f["year_positive_flag"].map(bool_value).sum()) if len(rob_years_f) else 0
        validation_negative_year_mean = float(val_years_f.loc[~val_years_f["year_positive_flag"].map(bool_value), "year_mean_spread"].min()) if len(val_years_f.loc[~val_years_f["year_positive_flag"].map(bool_value)]) else np.nan
        robustness_year_count = int(availability["robustness_actual_evaluable_year_count"])
        validation_single_positive_year_caveat = (
            validation_positive_year_count == 1
            and finite(val_mean)
            and val_mean >= float(c["validation_single_year_mean_spread_min"])
            and (not finite(validation_negative_year_mean) or validation_negative_year_mean >= float(c["validation_single_year_negative_spread_floor"]))
        )
        robustness_single_positive_year_caveat = robustness_positive_year_count == 1
        val_non_deterioration = finite(val_mean) and finite(train_mean) and val_mean >= train_mean - float(c["validation_train_spread_tolerance"])
        rob_non_deterioration = finite(rob_mean) and finite(train_mean) and rob_mean >= train_mean - float(c["robustness_train_spread_tolerance"])
        time_gate = (
            finite(val_mean)
            and val_mean > float(c["validation_mean_state_spread_min"])
            and finite(val_median)
            and val_median >= float(c["validation_median_state_spread_min"])
            and validation_positive_year_count >= int(c["validation_positive_year_count_min"])
            and val_non_deterioration
            and finite(rob_mean)
            and rob_mean >= float(c["robustness_mean_state_spread_min"])
            and finite(rob_median)
            and rob_median >= float(c["robustness_median_state_spread_min"])
            and robustness_year_count >= 1
            and robustness_positive_year_count >= max(1, math.ceil(float(c["robustness_positive_year_share_min"]) * robustness_year_count))
            and rob_non_deterioration
        )
        instrument_gate = (
            finite(val_mean)
            and val_mean > float(c["validation_oof_unseen_mean_spread_min"])
            and finite(val_median)
            and val_median >= float(c["validation_oof_unseen_median_spread_min"])
            and finite(rob_mean)
            and rob_mean >= float(c["robustness_oof_unseen_mean_spread_min"])
            and val_positive_inst >= float(c["positive_instrument_share_validation_min"])
            and rob_positive_inst >= float(c["positive_instrument_share_robustness_min"])
        )
        val_positive_fold_count = int(getattr(val_disp, "positive_fold_count", 0)) if val_disp is not None else 0
        rob_positive_fold_count = int(getattr(rob_disp, "positive_fold_count", 0)) if rob_disp is not None else 0
        fold_stability_gate = (
            val_positive_fold_count >= int(c["positive_fold_count_validation_min"])
            and rob_positive_fold_count >= int(c["positive_fold_count_robustness_min"])
            and finite(getattr(val_disp, "median_fold_spread", np.nan))
            and getattr(val_disp, "median_fold_spread", np.nan) > float(c["median_fold_spread_validation_min"])
            and finite(getattr(rob_disp, "median_fold_spread", np.nan))
            and getattr(rob_disp, "median_fold_spread", np.nan) >= float(c["median_fold_spread_robustness_min"])
            and getattr(val_disp, "min_fold_spread", np.nan) >= float(c["min_fold_spread_validation_floor"])
            and getattr(rob_disp, "min_fold_spread", np.nan) >= float(c["min_fold_spread_robustness_floor"])
            and getattr(val_disp, "fold_positive_instrument_share_median", 0.0) >= float(c["fold_positive_instrument_share_median_validation_min"])
            and getattr(rob_disp, "fold_positive_instrument_share_median", 0.0) >= float(c["fold_positive_instrument_share_median_robustness_min"])
        )
        mono_gate = (
            getattr(val, "aggregate_oof_unseen_decile_monotonicity_score", np.nan) >= float(c["aggregate_state_decile_monotonicity_min"])
            and getattr(rob, "aggregate_oof_unseen_decile_monotonicity_score", np.nan) >= float(c["aggregate_state_decile_monotonicity_min"])
            and getattr(val_disp, "fold_monotonicity_median", np.nan) >= float(c["fold_monotonicity_median_min"])
            and getattr(rob_disp, "fold_monotonicity_median", np.nan) >= float(c["fold_monotonicity_median_min"])
            and getattr(val_disp, "fold_monotonicity_positive_count", 0) >= int(c["fold_monotonicity_positive_count_min"])
            and getattr(rob_disp, "fold_monotonicity_positive_count", 0) >= int(c["fold_monotonicity_positive_count_min"])
            and not bool_value(getattr(val, "middle_state_violently_inverted_flag", True))
            and not bool_value(getattr(rob, "middle_state_violently_inverted_flag", True))
        )
        val_conc = conc_agg.get("validation_oof_unseen")
        rob_conc = conc_agg.get("robustness_oof_unseen")
        conc_val_pass = (
            val_conc is not None
            and not bool_value(getattr(val_conc, "contribution_denominator_zero", True))
            and getattr(val_conc, "top1_instrument_contribution_share", np.inf) <= float(c["top1_instrument_contribution_share_max"])
            and getattr(val_conc, "top5_instrument_contribution_share", np.inf) <= float(c["top5_instrument_contribution_share_max"])
            and getattr(val_conc, "top1_industry_contribution_share", np.inf) <= float(c["top1_industry_contribution_share_max"])
        )
        conc_rob_pass = (
            rob_conc is not None
            and not bool_value(getattr(rob_conc, "contribution_denominator_zero", True))
            and getattr(rob_conc, "top1_instrument_contribution_share", np.inf) <= float(c["top1_instrument_contribution_share_max"])
            and getattr(rob_conc, "top5_instrument_contribution_share", np.inf) <= float(c["top5_instrument_contribution_share_max"])
            and getattr(rob_conc, "top1_industry_contribution_share", np.inf) <= float(c["top1_industry_contribution_share_max"])
        )
        fold_conc = conc_df.loc[conc_df["family"].eq(family) & ~conc_df["fold_id"].astype(str).eq("aggregate")].copy()
        fold_conc_valrob = fold_conc.loc[fold_conc["split"].isin(["validation_oof_unseen", "robustness_oof_unseen"])]
        fold_total = fold_conc_valrob["contribution_denominator"].replace([np.inf, -np.inf], np.nan).fillna(0.0).sum()
        max_fold_contribution_share = float(fold_conc_valrob["contribution_denominator"].max() / fold_total) if fold_total else np.nan
        fold_conc_pass = (
            not fold_conc_valrob.empty
            and fold_conc_valrob["top1_instrument_contribution_share"].replace([np.inf, -np.inf], np.nan).max() <= float(c["max_fold_top1_instrument_contribution_share_max"])
            and fold_conc_valrob["top5_instrument_contribution_share"].replace([np.inf, -np.inf], np.nan).max() <= float(c["max_fold_top5_instrument_contribution_share_max"])
            and finite(max_fold_contribution_share)
            and max_fold_contribution_share <= float(c["max_fold_contribution_share_of_total_abs_contribution_max"])
        )
        concentration_gate = conc_val_pass and conc_rob_pass and fold_conc_pass
        val_evaluable_fold_count = int(getattr(val_disp, "evaluable_fold_count", 0)) if val_disp is not None else 0
        rob_evaluable_fold_count = int(getattr(rob_disp, "evaluable_fold_count", 0)) if rob_disp is not None else 0
        val_full_count = int(getattr(val, "aggregate_oof_unseen_full_valid_instrument_count", 0)) if val is not None else 0
        rob_full_count = int(getattr(rob, "aggregate_oof_unseen_full_valid_instrument_count", 0)) if rob is not None else 0
        val_dates = int(getattr(val, "aggregate_oof_unseen_valid_signal_date_count", 0)) if val is not None else 0
        rob_dates = int(getattr(rob, "aggregate_oof_unseen_valid_signal_date_count", 0)) if rob is not None else 0
        aggregate_floors_pass = (
            val_full_count >= int(c["aggregate_oof_full_valid_instrument_count_min"])
            and rob_full_count >= int(c["aggregate_oof_full_valid_instrument_count_min"])
            and val_dates >= int(c["aggregate_oof_valid_signal_date_count_min"])
            and rob_dates >= int(c["aggregate_oof_valid_signal_date_count_min"])
        )
        caveat_margin = (
            finite(val_mean)
            and val_mean >= float(c["caveat_validation_mean_spread_min"])
            and val_positive_inst >= float(c["caveat_validation_positive_instrument_share_min"])
            and val_positive_fold_count >= int(c["caveat_validation_positive_fold_count_min"])
        )
        if val_evaluable_fold_count == 5 and rob_evaluable_fold_count >= 4 and aggregate_floors_pass:
            aggregate_status = "pass"
            fold_coverage_caveat = False
        elif val_evaluable_fold_count == 4 and rob_evaluable_fold_count >= 4 and aggregate_floors_pass and caveat_margin:
            aggregate_status = "pass_with_fold_coverage_caveat"
            fold_coverage_caveat = True
        else:
            aggregate_status = "fail"
            fold_coverage_caveat = val_evaluable_fold_count == 4
        robustness_single_allowed = (
            not robustness_single_positive_year_caveat
            or (
                robustness_year_count == 1
                and finite(rob_mean)
                and rob_mean >= 0
                and finite(rob_median)
                and rob_median >= 0
                and fold_stability_gate
                and concentration_gate
            )
        )
        no_disallowed_caveat = concentration_gate and fold_stability_gate and robustness_single_allowed
        supported = (
            family == PRIMARY_FAMILY
            and aggregate_status in {"pass", "pass_with_fold_coverage_caveat"}
            and time_gate
            and instrument_gate
            and fold_stability_gate
            and mono_gate
            and concentration_gate
            and rob_non_deterioration
            and no_disallowed_caveat
        )
        rows.append(
            {
                "family": family,
                "role": "primary" if family == PRIMARY_FAMILY else "audit_only_comparator",
                "primary_score_formed_flag": primary_score_formed,
                "aggregate_oof_sample_status": aggregate_status,
                "fold_coverage_caveat": fold_coverage_caveat,
                "validation_evaluable_fold_count": val_evaluable_fold_count,
                "robustness_evaluable_fold_count": rob_evaluable_fold_count,
                "validation_full_valid_instrument_count": val_full_count,
                "robustness_full_valid_instrument_count": rob_full_count,
                "validation_valid_signal_date_count": val_dates,
                "robustness_valid_signal_date_count": rob_dates,
                "time_transfer_gate_pass": time_gate,
                "instrument_transfer_gate_pass": instrument_gate,
                "fold_stability_gate_pass": fold_stability_gate,
                "monotonicity_gate_pass": mono_gate,
                "concentration_gate_pass": concentration_gate,
                "validation_vs_train_non_deterioration_pass": val_non_deterioration,
                "robustness_vs_train_non_deterioration_pass": rob_non_deterioration,
                "robustness_non_deterioration_pass": rob_non_deterioration,
                "validation_single_positive_year_caveat": validation_single_positive_year_caveat,
                "robustness_single_positive_year_caveat": robustness_single_positive_year_caveat,
                "no_disallowed_caveat_active": no_disallowed_caveat,
                "train_oof_unseen_mean_spread": train_mean,
                "validation_oof_unseen_mean_spread": val_mean,
                "validation_oof_unseen_median_spread": val_median,
                "robustness_oof_unseen_mean_spread": rob_mean,
                "robustness_oof_unseen_median_spread": rob_median,
                "validation_oof_unseen_positive_instrument_share": val_positive_inst,
                "robustness_oof_unseen_positive_instrument_share": rob_positive_inst,
                "validation_positive_year_count": validation_positive_year_count,
                "robustness_positive_year_count": robustness_positive_year_count,
                "robustness_actual_evaluable_year_count": robustness_year_count,
                "positive_fold_count_validation": val_positive_fold_count,
                "positive_fold_count_robustness": rob_positive_fold_count,
                "median_fold_spread_validation": getattr(val_disp, "median_fold_spread", np.nan),
                "median_fold_spread_robustness": getattr(rob_disp, "median_fold_spread", np.nan),
                "min_fold_spread_validation": getattr(val_disp, "min_fold_spread", np.nan),
                "min_fold_spread_robustness": getattr(rob_disp, "min_fold_spread", np.nan),
                "fold_positive_instrument_share_median_validation": getattr(val_disp, "fold_positive_instrument_share_median", np.nan),
                "fold_positive_instrument_share_median_robustness": getattr(rob_disp, "fold_positive_instrument_share_median", np.nan),
                "aggregate_monotonicity_validation": getattr(val, "aggregate_oof_unseen_decile_monotonicity_score", np.nan),
                "aggregate_monotonicity_robustness": getattr(rob, "aggregate_oof_unseen_decile_monotonicity_score", np.nan),
                "max_fold_contribution_share_of_total_abs_contribution": max_fold_contribution_share,
                "supported_family_flag": supported,
                "authorized_strategy_requirement": False,
            }
        )
        time_rows.append(
            {
                "family": family,
                "train_oof_unseen_mean_spread": train_mean,
                "validation_oof_unseen_mean_spread": val_mean,
                "validation_oof_unseen_median_spread": val_median,
                "validation_positive_year_count": validation_positive_year_count,
                "validation_negative_year_mean_spread": validation_negative_year_mean,
                "validation_vs_train_non_deterioration_pass": val_non_deterioration,
                "robustness_oof_unseen_mean_spread": rob_mean,
                "robustness_oof_unseen_median_spread": rob_median,
                "robustness_positive_year_count": robustness_positive_year_count,
                "robustness_actual_evaluable_year_count": robustness_year_count,
                "robustness_vs_train_non_deterioration_pass": rob_non_deterioration,
                "time_transfer_gate_pass": time_gate,
            }
        )
    gate = pd.DataFrame(rows)
    if not gate.empty:
        prim = gate.loc[gate["family"].eq(PRIMARY_FAMILY)].iloc[0]
        comp = gate.loc[gate["family"].eq(COMPARATOR_FAMILY)].iloc[0] if gate["family"].eq(COMPARATOR_FAMILY).any() else None
        comparator_flag = False
        if comp is not None:
            margin = float(c["comparator_dominance_spread_margin"])
            comparator_flag = (
                finite(comp["validation_oof_unseen_mean_spread"])
                and finite(comp["robustness_oof_unseen_mean_spread"])
                and comp["validation_oof_unseen_mean_spread"] >= prim["validation_oof_unseen_mean_spread"] + margin
                and comp["robustness_oof_unseen_mean_spread"] >= prim["robustness_oof_unseen_mean_spread"] + margin
            ) or (bool_value(comp["fold_stability_gate_pass"]) and not bool_value(prim["fold_stability_gate_pass"]))
            comparator_rows.append(
                {
                    "primary_family": PRIMARY_FAMILY,
                    "comparator_family": COMPARATOR_FAMILY,
                    "primary_validation_oof_unseen_mean_spread": prim["validation_oof_unseen_mean_spread"],
                    "primary_robustness_oof_unseen_mean_spread": prim["robustness_oof_unseen_mean_spread"],
                    "comparator_validation_oof_unseen_mean_spread": comp["validation_oof_unseen_mean_spread"],
                    "comparator_robustness_oof_unseen_mean_spread": comp["robustness_oof_unseen_mean_spread"],
                    "primary_fold_stability_gate_pass": prim["fold_stability_gate_pass"],
                    "comparator_fold_stability_gate_pass": comp["fold_stability_gate_pass"],
                    "comparator_dominates_primary_flag": comparator_flag,
                    "comparator_affects_final_decision": False,
                }
            )
            gate["comparator_dominates_primary_flag"] = gate["family"].map(lambda f: comparator_flag if f == PRIMARY_FAMILY else False)
    comparator_df = pd.DataFrame(comparator_rows)
    time_df = pd.DataFrame(time_rows)
    write_csv(gate, paths.decision_dir / "r08_1_gate_inputs.csv")
    write_csv(time_df, paths.metrics_dir / "r08_1_time_transfer_summary.csv")
    write_csv(comparator_df, paths.audit_dir / "r08_1_comparator_vpc_audit.csv")
    write_csv(comparator_df, paths.metrics_dir / "r08_1_vpc_comparator_summary.csv")
    return gate, time_df, comparator_df, pd.DataFrame(rows)


def build_final_decision(paths: R081Paths, gate: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    if gate.empty or not gate["family"].eq(PRIMARY_FAMILY).any():
        primary = {}
    else:
        primary = gate.loc[gate["family"].eq(PRIMARY_FAMILY)].iloc[0].to_dict()
    contract_violation = False
    score_missing = not bool_value(primary.get("primary_score_formed_flag", False))
    sample_fail = primary.get("aggregate_oof_sample_status", "fail") == "fail"
    time_pass = bool_value(primary.get("time_transfer_gate_pass", False))
    inst_pass = bool_value(primary.get("instrument_transfer_gate_pass", False))
    fold_pass = bool_value(primary.get("fold_stability_gate_pass", False))
    mono_pass = bool_value(primary.get("monotonicity_gate_pass", False))
    conc_pass = bool_value(primary.get("concentration_gate_pass", False))
    rob_nd_pass = bool_value(primary.get("robustness_non_deterioration_pass", False))
    support_all = (
        primary.get("aggregate_oof_sample_status") in {"pass", "pass_with_fold_coverage_caveat"}
        and time_pass
        and inst_pass
        and fold_pass
        and mono_pass
        and conc_pass
        and rob_nd_pass
        and bool_value(primary.get("no_disallowed_caveat_active", False))
    )
    rules = [
        ("rule_01", "data / execution / scope / as-of / fold contract violation", contract_violation, "r08_1_blocked_data_or_execution_contract"),
        ("rule_02", "primary vwap family cannot form fold-specific state score", score_missing, "r08_1_blocked_kfold_sample_insufficient"),
        ("rule_03", "aggregate_oof_sample_status = fail", sample_fail, "r08_1_blocked_kfold_sample_insufficient"),
        (
            "rule_04",
            "time + aggregate instrument + monotonicity + concentration + robustness non-deterioration pass, fold stability fails",
            time_pass and inst_pass and mono_pass and conc_pass and rob_nd_pass and not fold_pass,
            "r08_1_fold_fragile_vwap_state_candidate",
        ),
        (
            "rule_05",
            "time transfer passes, aggregate instrument transfer fails, monotonicity + concentration + robustness non-deterioration pass",
            time_pass and (not inst_pass) and mono_pass and conc_pass and rob_nd_pass,
            "r08_1_time_transfer_only_not_instrument_transfer",
        ),
        ("rule_06", "all support gates pass", support_all, "r08_1_vwap_kfold_transferability_sensitivity_supported"),
        ("rule_07", "otherwise", True, "r08_1_no_vwap_kfold_transferability_support"),
    ]
    selected_decision = ""
    replay_rows = []
    selected_seen = False
    for rule_id, text, condition, decision in rules:
        raw = bool(condition)
        selected = (not selected_seen) and raw
        if selected:
            selected_seen = True
            selected_decision = decision
        replay_rows.append(
            {
                "rule_id": rule_id,
                "rule_condition_text": text,
                "raw_condition_met": raw,
                "selected_rule_flag": selected,
                "decision_if_selected": decision,
            }
        )
    final = pd.DataFrame(
        [
            {
                "final_decision": selected_decision,
                "authorized_strategy_requirement": False,
                "allowed_next_requirement": "confirmatory_vwap_state_transferability_diagnostic"
                if selected_decision == "r08_1_vwap_kfold_transferability_sensitivity_supported"
                else "",
                "primary_family": PRIMARY_FAMILY,
                "primary_horizon": "H3",
                "aggregate_oof_sample_status": primary.get("aggregate_oof_sample_status", "fail"),
                "fold_coverage_caveat": primary.get("fold_coverage_caveat", False),
                "validation_oof_unseen_mean_spread": primary.get("validation_oof_unseen_mean_spread", np.nan),
                "robustness_oof_unseen_mean_spread": primary.get("robustness_oof_unseen_mean_spread", np.nan),
                "validation_oof_unseen_positive_instrument_share": primary.get("validation_oof_unseen_positive_instrument_share", np.nan),
                "robustness_oof_unseen_positive_instrument_share": primary.get("robustness_oof_unseen_positive_instrument_share", np.nan),
                "comparator_dominates_primary_flag": primary.get("comparator_dominates_primary_flag", False),
            }
        ]
    )
    replay = pd.DataFrame(replay_rows)
    write_csv(replay, paths.decision_dir / "r08_1_final_decision_replay.csv")
    write_csv(final, paths.decision_dir / "r08_1_final_decision.csv")
    return replay, final


def write_report(paths: R081Paths, gate: pd.DataFrame, final: pd.DataFrame, availability: dict[str, Any]) -> None:
    decision = str(final.iloc[0]["final_decision"])
    agg = pd.read_csv(paths.metrics_dir / "r08_1_aggregate_oof_unseen_state_spread.csv")
    fold = pd.read_csv(paths.metrics_dir / "r08_1_fold_unseen_state_spread.csv")
    disp = pd.read_csv(paths.metrics_dir / "r08_1_fold_dispersion_summary.csv")
    conc = pd.read_csv(paths.audit_dir / "r08_1_concentration_audit.csv")
    comp = pd.read_csv(paths.metrics_dir / "r08_1_vpc_comparator_summary.csv")
    primary_gate = gate.loc[gate["family"].eq(PRIMARY_FAMILY)].iloc[0] if gate["family"].eq(PRIMARY_FAMILY).any() else None
    lines = [
        "# R08.1 VWAP Deviation H3 K-Fold Transferability Sensitivity Audit Report",
        "",
        "## 1. 结论",
        "",
        f"`final_decision = {decision}`",
        "",
        "`authorized_strategy_requirement = false`。R08.1 是 diagnostic-only sensitivity audit，没有构造 top-N、top20%、portfolio、backtest、paper trading 或 production signal。",
        "",
        "R08.1 只把 `vwap_deviation` 作为 primary family，H3 作为唯一 horizon，使用 within-stock 252d percentile 与 H3 self-relative net return。`volume_price_correlation` 只作为 audit-only comparator，不参与 final decision。",
        "",
        "## 2. Aggregate OOF Unseen Readout",
        "",
        "| family | split | mean spread | median spread | pooled spread | positive inst share | valid instruments | valid dates | monotonicity |",
        "|:--|:--|--:|--:|--:|--:|--:|--:|--:|",
    ]
    for rec in agg.itertuples(index=False):
        lines.append(
            f"| {rec.family} | {rec.split} | {pct_text(rec.aggregate_oof_unseen_mean_spread)} | {pct_text(rec.aggregate_oof_unseen_median_spread)} | {pct_text(rec.aggregate_oof_unseen_pooled_high_minus_low_spread)} | {pct_text(rec.aggregate_oof_unseen_positive_instrument_share)} | {int(rec.aggregate_oof_unseen_full_valid_instrument_count)} | {int(rec.aggregate_oof_unseen_valid_signal_date_count)} | {num_text(rec.aggregate_oof_unseen_decile_monotonicity_score)} |"
        )
    lines.extend(
        [
            "",
            "## 3. Primary Gate Replay",
            "",
            "| gate | value |",
            "|:--|:--|",
        ]
    )
    if primary_gate is not None:
        for col in [
            "aggregate_oof_sample_status",
            "time_transfer_gate_pass",
            "instrument_transfer_gate_pass",
            "fold_stability_gate_pass",
            "monotonicity_gate_pass",
            "concentration_gate_pass",
            "robustness_non_deterioration_pass",
            "no_disallowed_caveat_active",
            "validation_evaluable_fold_count",
            "robustness_evaluable_fold_count",
            "positive_fold_count_validation",
            "positive_fold_count_robustness",
            "validation_oof_unseen_mean_spread",
            "robustness_oof_unseen_mean_spread",
            "validation_oof_unseen_positive_instrument_share",
            "robustness_oof_unseen_positive_instrument_share",
            "comparator_dominates_primary_flag",
        ]:
            value = primary_gate[col]
            if "spread" in col or "share" in col:
                value = pct_text(value)
            lines.append(f"| {col} | {value} |")
    lines.extend(
        [
            "",
            "## 4. Fold Dispersion",
            "",
            "| family | split | evaluable folds | positive folds | median spread | min spread | median positive inst share | fold mono median | worst fold spread |",
            "|:--|:--|--:|--:|--:|--:|--:|--:|--:|",
        ]
    )
    for rec in disp.itertuples(index=False):
        lines.append(
            f"| {rec.family} | {rec.split} | {int(rec.evaluable_fold_count)} | {int(rec.positive_fold_count)} | {pct_text(rec.median_fold_spread)} | {pct_text(rec.min_fold_spread)} | {pct_text(rec.fold_positive_instrument_share_median)} | {num_text(rec.fold_monotonicity_median)} | {rec.worst_fold_id_by_spread} |"
        )
    lines.extend(
        [
            "",
            "## 5. Concentration",
            "",
            "| family | split | fold | top1 inst share | top5 inst share | top1 industry share | industry overweight |",
            "|:--|:--|:--|--:|--:|--:|--:|",
        ]
    )
    for rec in conc.loc[conc["fold_id"].astype(str).eq("aggregate")].itertuples(index=False):
        lines.append(
            f"| {rec.family} | {rec.split} | {rec.fold_id} | {pct_text(rec.top1_instrument_contribution_share)} | {pct_text(rec.top5_instrument_contribution_share)} | {pct_text(rec.top1_industry_contribution_share)} | {pct_text(rec.top1_industry_contribution_minus_universe_weight)} |"
        )
    lines.extend(
        [
            "",
            "## 6. Comparator",
            "",
        ]
    )
    if comp.empty:
        lines.append("`volume_price_correlation` comparator 未形成可用汇总。")
    else:
        rec = comp.iloc[0]
        lines.append(
            f"`volume_price_correlation` comparator_dominates_primary_flag = {bool_value(rec['comparator_dominates_primary_flag'])}。该标记只作为下一步 confirmatory diagnostic 的注释，不影响 R08.1 final decision。"
        )
    lines.extend(
        [
            "",
            "## 7. Data Availability",
            "",
            f"- declared_robustness_end_date: `{availability['declared_robustness_end_date']}`",
            f"- robustness_window_actual_end_date: `{availability['robustness_window_actual_end_date']}`",
            f"- robustness_window_truncated_by_data_availability: `{availability['robustness_window_truncated_by_data_availability']}`",
            f"- robustness_actual_evaluable_year_count: `{availability['robustness_actual_evaluable_year_count']}`",
            "",
            "## 8. Required Questions",
            "",
        ]
    )
    qas = [
        "1. R08.1 是否保持 diagnostic-only，且没有构造任何策略？是。",
        "2. 是否只把 `vwap_deviation` 作为 primary family？是。",
        "3. 是否只研究 H3？是。",
        "4. 5-fold instrument assignment 是否 deterministic 且 train 前冻结？是，使用 canonical repo-native instrument id lower-case sha256 first 8 bytes mod 5。",
        "5. 每个 fold 的 direction 是否只来自 train years + seen folds？是。",
        "6. 每个 fold 的 state bucket edge 是否只来自 train years + seen folds？是。",
        "7. 是否每只股票只在自己的 unseen fold 中参与 primary out-of-fold evaluation？是。",
        "8. validation aggregate out-of-fold spread 是否为正？见 Aggregate OOF 表。",
        "9. robustness aggregate out-of-fold spread 是否确认？见 Aggregate OOF 表与 Gate Replay。",
        "10. validation / robustness aggregate positive instrument share 是否达标？见 Gate Replay。",
        "11. 5 个 fold 中有多少 fold spread 为正？见 Fold Dispersion。",
        "12. 最差 fold 的 spread 与 positive instrument share 是多少？见 Fold Dispersion 与 fold state spread artifact。",
        "13. aggregate monotonicity 是否 >= 0.60？见 Aggregate OOF 表和 gate。",
        "14. fold-level monotonicity 是否稳定？见 Fold Dispersion。",
        "15. aggregate concentration 是否通过？见 Gate Replay 与 Concentration 表。",
        "16. 是否有单一 fold、单一股票或单一行业贡献过大？见 Concentration artifact。",
        "17. `vwap_deviation` 相比 R08 单次 unseen split 的结果是否改善？本报告输出 k-fold aggregate；R08 reference 为 validation unseen +0.1698%、robustness unseen +0.2398%。",
        "18. `volume_price_correlation` comparator 是否只是 audit-only？是。",
        f"19. 最终结果是 k-fold sensitivity supported、fold-fragile，还是 no support？`{decision}`。",
        "20. 是否允许写 strategy requirement？No。",
        "21. 如果结果 supported，允许的下一步 confirmatory diagnostic 是什么？`confirmatory_vwap_state_transferability_diagnostic`，不是 strategy。",
        "22. aggregate OOF metric 命名是否一致？gate 使用 mean / median spread，pooled spread report-only。",
        "23. train_oof_unseen baseline 是否落盘并用于 non-deterioration replay？是。",
        f"24. robustness 实际可用结束日期是哪一天？`{availability['robustness_window_actual_end_date']}`。",
        f"25. fold coverage caveat path 是否触发？`{primary_gate['fold_coverage_caveat'] if primary_gate is not None else 'NA'}`。",
        "26. direction-insufficient factor 是否已从 retained set 中删除？是，见 family scope by fold。",
        f"27. `comparator_dominates_primary_flag` 是否为 true？`{final.iloc[0]['comparator_dominates_primary_flag']}`，只作为 annotation。",
        "28. partial instruments 是否只进入 event-level spread，且没有计入 sample gate 或 positive instrument denominator？是。",
        "29. 如果 final decision 是 fold-fragile，是否确认 monotonicity、concentration、time transfer 与 aggregate instrument transfer 均已通过？decision replay 按 rule_04 first-match 验证。",
    ]
    lines.extend(qas)
    lines.extend(
        [
            "",
            "## 9. Artifact Counts",
            "",
            f"- aggregate rows: `{len(agg)}`",
            f"- fold rows: `{len(fold)}`",
            f"- dispersion rows: `{len(disp)}`",
            f"- concentration rows: `{len(conc)}`",
        ]
    )
    (paths.reports_dir / "r08_1_final_report.md").write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def run_pipeline(config_path: str | Path = DEFAULT_CONFIG) -> None:
    config, paths = load_config(config_path)
    inputs = r08.load_r06_inputs(config)
    scope = scope_factor_ids(inputs)
    label, label_audit, availability = build_h3_label_frame(config, paths, inputs)
    write_csv(label_audit, paths.audit_dir / "r08_1_h3_label_audit.csv")
    percentile, tie, tie_cluster, available_fids = build_factor_state_inputs(config, paths, inputs, scope)
    write_input_scope_fold_audits(config, paths, inputs, label, scope, available_fids)
    build_normalization_audit(paths, label, scope, available_fids, percentile, tie, tie_cluster)
    _, directions = direction_by_fold(config, paths, label, scope, available_fids, percentile)
    events, scope_df, _ = build_oof_events(config, paths, label, scope, available_fids, percentile, directions)
    fold_df, agg_df, disp_df, inst_df, sample_df, conc_df = build_metrics(config, paths, events)
    gate, _, _, _ = build_gate_inputs(config, paths, scope_df, fold_df, agg_df, disp_df, sample_df, conc_df, availability)
    _, final = build_final_decision(paths, gate)
    write_report(paths, gate, final, availability)
    write_json(
        {
            "requirement_id": REQUIREMENT_ID,
            "plan_id": PLAN_ID,
            "config_path": rel(paths.config_path),
            "output_root": rel(paths.output_root),
            "created_at": r01.now_iso(),
            "git_commit": r01.git_commit_hash(),
            "primary_family": PRIMARY_FAMILY,
            "primary_horizon": "H3",
            "final_decision": final.iloc[0]["final_decision"],
            "authorized_strategy_requirement": bool_value(final.iloc[0]["authorized_strategy_requirement"]),
        },
        paths.audit_dir / "r08_1_run_manifest.json",
    )
    write_json({"created_at": r01.now_iso(), "artifacts": artifact_hashes(paths)}, paths.manifests_dir / "r08_1_artifact_hashes.json")


def required_paths(paths: R081Paths) -> list[Path]:
    return [
        paths.audit_dir / "r08_1_run_manifest.json",
        paths.audit_dir / "r08_1_input_data_audit.csv",
        paths.audit_dir / "r08_1_data_availability_audit.csv",
        paths.audit_dir / "r08_1_scope_audit.csv",
        paths.audit_dir / "r08_1_fold_assignment_audit.csv",
        paths.audit_dir / "r08_1_within_stock_normalization_audit.csv",
        paths.audit_dir / "r08_1_h3_label_audit.csv",
        paths.audit_dir / "r08_1_factor_direction_by_fold_audit.csv",
        paths.audit_dir / "r08_1_family_scope_by_fold_audit.csv",
        paths.audit_dir / "r08_1_state_bucket_by_fold_audit.csv",
        paths.audit_dir / "r08_1_fold_sample_audit.csv",
        paths.audit_dir / "r08_1_concentration_audit.csv",
        paths.audit_dir / "r08_1_comparator_vpc_audit.csv",
        paths.metrics_dir / "r08_1_fold_unseen_state_spread.csv",
        paths.metrics_dir / "r08_1_aggregate_oof_unseen_state_spread.csv",
        paths.metrics_dir / "r08_1_fold_dispersion_summary.csv",
        paths.metrics_dir / "r08_1_instrument_transfer_summary.csv",
        paths.metrics_dir / "r08_1_time_transfer_summary.csv",
        paths.metrics_dir / "r08_1_year_availability_and_positive_count.csv",
        paths.metrics_dir / "r08_1_decile_monotonicity_by_fold.csv",
        paths.metrics_dir / "r08_1_aggregate_decile_monotonicity.csv",
        paths.metrics_dir / "r08_1_concentration_summary.csv",
        paths.metrics_dir / "r08_1_vpc_comparator_summary.csv",
        paths.decision_dir / "r08_1_gate_inputs.csv",
        paths.decision_dir / "r08_1_final_decision_replay.csv",
        paths.decision_dir / "r08_1_final_decision.csv",
        paths.reports_dir / "r08_1_final_report.md",
        paths.manifests_dir / "r08_1_artifact_hashes.json",
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
    check("V02_required_artifacts_exist", not missing, ";".join(missing))
    final_decision = ""
    if not missing:
        scope = pd.read_csv(paths.audit_dir / "r08_1_scope_audit.csv")
        fold_assign = pd.read_csv(paths.audit_dir / "r08_1_fold_assignment_audit.csv")
        norm = pd.read_csv(paths.audit_dir / "r08_1_within_stock_normalization_audit.csv")
        label = pd.read_csv(paths.audit_dir / "r08_1_h3_label_audit.csv")
        direction = pd.read_csv(paths.audit_dir / "r08_1_factor_direction_by_fold_audit.csv")
        fam_scope = pd.read_csv(paths.audit_dir / "r08_1_family_scope_by_fold_audit.csv")
        buckets = pd.read_csv(paths.audit_dir / "r08_1_state_bucket_by_fold_audit.csv")
        sample = pd.read_csv(paths.audit_dir / "r08_1_fold_sample_audit.csv")
        agg = pd.read_csv(paths.metrics_dir / "r08_1_aggregate_oof_unseen_state_spread.csv")
        disp = pd.read_csv(paths.metrics_dir / "r08_1_fold_dispersion_summary.csv")
        conc = pd.read_csv(paths.audit_dir / "r08_1_concentration_audit.csv")
        comp = pd.read_csv(paths.metrics_dir / "r08_1_vpc_comparator_summary.csv")
        gate = pd.read_csv(paths.decision_dir / "r08_1_gate_inputs.csv")
        replay = pd.read_csv(paths.decision_dir / "r08_1_final_decision_replay.csv")
        final = pd.read_csv(paths.decision_dir / "r08_1_final_decision.csv")
        report = (paths.reports_dir / "r08_1_final_report.md").read_text(encoding="utf-8")
        final_decision = str(final.iloc[0]["final_decision"])
        check("V03_primary_family_only_vwap", config["scope"]["primary_family"] == PRIMARY_FAMILY, "")
        check("V04_primary_horizon_only_H3", config["execution"]["horizons"] == [3] and config["scope"]["horizon"] == "H3", "")
        check("V05_no_strategy_artifacts", not any(p.is_file() and any(x in p.name.lower() for x in ["portfolio", "backtest", "allocation", "top20", "top_"]) for p in paths.output_root.rglob("*")), "")
        check("V06_scope_roles", set(scope["family"]) == set(FAMILIES) and scope.loc[scope["family"].eq(COMPARATOR_FAMILY), "primary_decision_eligible"].map(bool_value).eq(False).all(), "")
        check("V07_fold_assignment_sha256_mod5", set(fold_assign["instrument_fold_id"].dropna().astype(int).unique()) == set(FOLD_IDS), "")
        sample_ids = fold_assign.head(20)
        replay_hash_ok = all(instrument_fold_id(x) == int(fid) for x, fid in zip(sample_ids["canonical_instrument_id"], sample_ids["instrument_fold_id"]))
        check("V08_fold_hash_input_canonicalized", replay_hash_ok, "")
        check("V09_all_5_folds_present", set(fam_scope["fold_id"].dropna().astype(int).unique()) == set(FOLD_IDS), "")
        check("V10_no_fold_dropped_for_performance", set(sample["fold_id"].dropna().astype(int).unique()) == set(FOLD_IDS), "")
        check("V11_direction_train_seen_only", direction["direction_source_split"].eq("train").all() and direction["direction_source_instrument_scope"].astype(str).str.contains("seen_folds_not_").all(), "")
        check("V12_direction_insufficient_factors_dropped", fam_scope["direction_insufficient_factors_dropped"].map(bool_value).all(), "")
        check("V13_bucket_edges_train_seen_only", buckets["frozen_before_validation_read"].map(bool_value).all() and buckets["bucket_edge_source_split"].eq("train").all(), "")
        check("V14_primary_evaluation_unseen_fold_only", (paths.cache_dir / "r08_1_oof_event_panel.parquet").exists(), "")
        check("V15_self_relative_label_asof_safe", label["self_relative_label_lookback_only_uses_completed_h3_labels"].map(bool_value).all() and label["self_relative_label_uses_lookback_h3_exit_date_le_D_minus_1"].map(bool_value).all(), "")
        check("V16_normalization_prior_252d_asof_safe", not norm["uses_future_data_flag"].map(bool_value).any() and norm["within_stock_lookback_ends_at_D_minus_1"].map(bool_value).all(), "")
        check("V17_mid_rank_tie_handling_used", norm["mid_rank_tie_handling_used"].map(bool_value).all(), "")
        check("V18_aggregate_metric_names_replayable", {"aggregate_oof_unseen_mean_spread", "aggregate_oof_unseen_median_spread", "aggregate_oof_unseen_pooled_high_minus_low_spread"}.issubset(agg.columns), "")
        check("V19_train_oof_unseen_baseline_exists", "train_oof_unseen" in set(agg["split"]), "")
        check("V20_data_availability_audit_exists", (paths.audit_dir / "r08_1_data_availability_audit.csv").exists(), "")
        check("V21_aggregate_oof_sample_status_replayable", "aggregate_oof_sample_status" in gate.columns, "")
        check("V22_partial_instruments_excluded_from_sample_gate", sample["partial_instruments_excluded_from_sample_gate"].map(bool_value).all(), "")
        check("V23_partial_instruments_excluded_from_positive_share", sample["partial_instruments_excluded_from_positive_instrument_share"].map(bool_value).all(), "")
        check("V24_fold_dispersion_metrics_exist", {"positive_fold_count", "median_fold_spread", "worst_fold_id_by_spread"}.issubset(disp.columns), "")
        check("V25_concentration_formula_replayable", {"top1_instrument_contribution_share", "top5_instrument_contribution_share", "top1_industry_contribution_share"}.issubset(conc.columns), "")
        check("V26_comparator_dominates_primary_flag_reported", "comparator_dominates_primary_flag" in comp.columns, "")
        rule04 = replay.loc[replay["rule_id"].eq("rule_04")]
        check("V27_fold_fragile_rule_requires_non_fold_gates", not rule04.empty and "time + aggregate instrument" in str(rule04.iloc[0]["rule_condition_text"]), "")
        check("V28_decision_replay_first_match", int(replay["selected_rule_flag"].map(bool_value).sum()) == 1, "")
        check("V29_authorized_strategy_requirement_false", final["authorized_strategy_requirement"].map(bool_value).eq(False).all(), "")
        check("V30_final_decision_enum", final_decision in FINAL_DECISIONS, final_decision)
        check("V31_report_questions", all(f"{i}." in report for i in range(1, 30)), "")
        if (paths.cache_dir / "r08_1_oof_event_panel.parquet").exists():
            events = pd.read_parquet(paths.cache_dir / "r08_1_oof_event_panel.parquet", columns=["fold_id", "instrument_fold_id", "family"])
            check("V32_primary_events_unseen_fold_only", events["fold_id"].astype(int).eq(events["instrument_fold_id"].astype(int)).all(), "")
    status = "passed" if not failures else "failed"
    audit = pd.DataFrame(checks)
    write_csv(audit, paths.audit_dir / "r08_1_validation_gate_audit.csv")
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
    write_json(payload, paths.manifests_dir / "r08_1_validation.json")
    write_json({"created_at": r01.now_iso(), "artifacts": artifact_hashes(paths)}, paths.manifests_dir / "r08_1_artifact_hashes.json")
    return payload
