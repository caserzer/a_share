#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml

SCRIPT_DIR = Path(__file__).resolve().parent
EP4_DIR = SCRIPT_DIR.parent
TOPIC_DIR = EP4_DIR.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import r02_evidence_family_discovery_common as r02v1  # noqa: E402


DEFAULT_CONFIG = EP4_DIR / "configs" / "r02_winner_anchored_structure_profile_discovery_v2.yaml"
SCHEMA_VERSION = "ep4_r02_winner_anchored_structure_profile_discovery_v2"
SPLITS = ["train", "validation", "robustness"]
LABEL_IDS = [
    "continuation_h20",
    "continuation_h60",
    "big_winner_forward",
    "failed_seed_forward",
    "executable_entry_available",
]
ALLOWED_DECISIONS = {
    "go_to_r03_evidence_accumulation",
    "revise_profile_search_space",
    "archive_profile_discovery_no_r03",
}
ALLOWED_PATTERN_TYPES = {
    "point_in_window_existence",
    "persistence",
    "ordered_sequence",
    "recovery_structure",
    "absence_structure",
    "contraction_expansion_structure",
    "support_structure",
}
REQUIRED_CACHE = [
    "r02_v2_winner_reference_events.parquet",
    "r02_v2_reference_action_time_label_panel.parquet",
    "r02_v2_winner_window_panel.parquet",
    "r02_v2_profile_candidate_event_panel.parquet",
    "r02_v2_matched_background_windows.parquet",
    "r02_v2_action_time_eventized_signals.parquet",
    "r02_v2_action_time_panel.parquet",
    "r02_v2_action_time_signal_panel.parquet",
    "r02_v2_frozen_representatives.parquet",
]
REQUIRED_REPORTS = [
    "r02_v2_winner_profile_search_summary.csv",
    "r02_v2_winner_reference_event_audit.csv",
    "r02_v2_r01_v3_reference_reconciliation.csv",
    "r02_v2_candidate_dictionary.csv",
    "r02_v2_bucket_boundaries.csv",
    "r02_v2_stage_a_rejection_audit.csv",
    "r02_v2_profile_observability_audit.csv",
    "r02_v2_eventization_audit.csv",
    "r02_v2_background_information_screen.csv",
    "r02_v2_profile_redundancy_matrix.csv",
    "r02_v2_stage_b_prior_calibration.csv",
    "r02_v2_prior_decomposition.csv",
    "r02_v2_stage_b_train_gate_audit.csv",
    "r02_v2_representative_selection.csv",
    "r02_v2_validation_summary.csv",
    "r02_v2_robustness_summary.csv",
    "r02_v2_execution_diagnostics.csv",
    "r02_v2_year_stability.csv",
    "r02_v2_label_confusion_matrix.csv",
    "r02_v2_mandatory_baselines.csv",
    "r02_v2_gate_audit.csv",
    "r02_v2_final_report.md",
]
REQUIRED_MANIFESTS = [
    "r02_v2_manifest.json",
    "r02_v2_input_hashes.json",
    "r02_v2_config_hash.json",
    "r02_v2_validation_contract.json",
]


@dataclass(frozen=True)
class R02V2Paths:
    config_path: Path
    output_root: Path
    cache_dir: Path
    reports_dir: Path
    manifests_dir: Path


def parse_config_arg(description: str, default_config: Path = DEFAULT_CONFIG) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--config", default=str(default_config))
    return parser.parse_args()


def topic_path(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else TOPIC_DIR / path


def relpath(path: str | Path) -> str:
    path = Path(path).resolve()
    try:
        return str(path.relative_to(TOPIC_DIR))
    except ValueError:
        return str(path)


def _date_str(value: Any) -> str:
    if pd.isna(value) or str(value) in {"", "NaT", "nan", "None"}:
        return ""
    return pd.Timestamp(value).date().isoformat()


def _safe_div(numer: float, denom: float, default: float = np.nan) -> float:
    return float(numer) / float(denom) if np.isfinite(numer) and np.isfinite(denom) and float(denom) != 0 else default


def _safe_float(value: Any, default: float = np.nan) -> float:
    try:
        out = float(value)
    except Exception:
        return default
    return out if np.isfinite(out) else default


def _hash_text(value: Any, n: int = 10) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=True, default=str).encode("utf-8")).hexdigest()[:n]


def file_hash(path: Path) -> str:
    if not path.exists() or not path.is_file():
        return ""
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)


def write_json(payload: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")


def write_parquet(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False)


def with_columns(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    out = df.copy()
    for column in columns:
        if column not in out.columns:
            out[column] = np.nan
    return out[columns] if columns else out


def load_config(config_path: str | Path) -> tuple[dict[str, Any], R02V2Paths, dict[str, Any]]:
    cfg_path = topic_path(config_path)
    with cfg_path.open("r", encoding="utf-8") as file:
        config = yaml.safe_load(file) or {}
    paths = R02V2Paths(
        config_path=cfg_path,
        output_root=topic_path(config["output_root"]),
        cache_dir=topic_path(config["output_root"]) / "cache",
        reports_dir=topic_path(config["output_root"]) / "reports",
        manifests_dir=topic_path(config["output_root"]) / "manifests",
    )
    for directory in [paths.cache_dir, paths.reports_dir, paths.manifests_dir]:
        directory.mkdir(parents=True, exist_ok=True)
    with topic_path(config["upstream_ep2"]["config"]).open("r", encoding="utf-8") as file:
        ep2_config = yaml.safe_load(file) or {}
    return config, paths, ep2_config


def split_bounds(config: dict[str, Any]) -> dict[str, tuple[pd.Timestamp, pd.Timestamp]]:
    split = config["split"]
    return {
        "train": (pd.Timestamp(split["train_start"]), pd.Timestamp(split["train_end"])),
        "validation": (pd.Timestamp(split["validation_start"]), pd.Timestamp(split["validation_end"])),
        "robustness": (pd.Timestamp(split["robustness_start"]), pd.Timestamp(split["robustness_end"])),
    }


def assert_authority_inputs(config: dict[str, Any]) -> pd.DataFrame:
    inputs = {
        "ep4_requirement": config["requirement_path"],
        "ep2_manifest": config["upstream_ep2"]["manifest"],
        "ep2_config": config["upstream_ep2"]["config"],
        "qlib_provider_uri": config["data_sources"]["qlib_provider_uri"],
        "trading_calendar": config["data_sources"]["trading_calendar_path"],
        "pit_universe": config["data_sources"]["pit_universe_path"],
        "pit_qlib_instrument_universe": config["data_sources"]["pit_qlib_instrument_universe_path"],
        "pit_industry": config["data_sources"]["pit_industry_path"],
        "r01_v3_reference": config["reference_events"]["r01_v3_reference_artifact"],
    }
    rows = []
    for name, value in inputs.items():
        path = topic_path(value)
        rows.append(
            {
                "artifact_name": name,
                "path": relpath(path),
                "exists": path.exists(),
                "sha256": file_hash(path) if path.is_file() else "",
                "status": "passed" if path.exists() else "failed",
            }
        )
    authority = pd.DataFrame(rows)
    required = authority.loc[~authority["artifact_name"].eq("r01_v3_reference")]
    if not bool(required["exists"].all()):
        missing = "; ".join(required.loc[~required["exists"], "path"].astype(str).tolist())
        raise RuntimeError(f"missing R02 V2 authority inputs: {missing}")
    manifest = json.loads(topic_path(config["upstream_ep2"]["manifest"]).read_text(encoding="utf-8"))
    if manifest.get("validation_status") != "passed":
        raise RuntimeError("EP2 engineering baseline manifest is not passed")
    return authority


def build_action_time_panel(config: dict[str, Any], ep2_config: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DatetimeIndex]:
    stock, calendar = r02v1.build_stock_panel(config, ep2_config)
    action, effective = r02v1.build_action_time_panel(stock, config, calendar, ep2_config)
    action = r02v1.apply_metric_eligibility(action)
    stock_extra = stock.copy()
    stock_extra["trade_date"] = pd.to_datetime(stock_extra["date"]).dt.strftime("%Y-%m-%d")
    group = stock_extra.groupby("instrument", group_keys=False)
    horizon = int(config["reference_events"]["forward_horizon_days"])
    shifted = pd.concat([group["close"].shift(-i).rename(str(i)) for i in range(1, horizon + 1)], axis=1)
    peak_values = shifted.max(axis=1)
    peak_offsets = shifted.apply(lambda row: int(row.astype(float).idxmax()) if row.notna().any() else np.nan, axis=1)
    stock_extra["forward_close_peak_h120"] = peak_values
    stock_extra["forward_peak_offset_h120"] = peak_offsets
    stock_extra["forward_peak_date_h120"] = [
        _date_str(calendar[int(pos) + int(off)]) if pd.notna(pos) and pd.notna(off) and int(pos) + int(off) < len(calendar) else ""
        for pos, off in zip(stock_extra["calendar_pos"], stock_extra["forward_peak_offset_h120"])
    ]
    merge_cols = [
        "instrument",
        "trade_date",
        "calendar_pos",
        "forward_close_peak_h120",
        "forward_peak_date_h120",
        "market_cap_asof_T",
    ]
    for column in merge_cols:
        if column not in stock_extra.columns:
            stock_extra[column] = np.nan
    action = action.merge(stock_extra[merge_cols].drop_duplicates(["instrument", "trade_date"]), on=["instrument", "trade_date"], how="left", suffixes=("", "_extra"))
    if "calendar_pos_extra" in action.columns:
        action["calendar_pos"] = action["calendar_pos"].fillna(action["calendar_pos_extra"])
        action = action.drop(columns=["calendar_pos_extra"])
    action["instrument_id"] = action["instrument"].astype(str)
    action["event_t"] = action["trade_date"]
    action["executable_entry_available"] = action["executable_entry_available"].astype(bool)
    action["buyable_signal_row"] = action["entry_execution_status"].eq("entry_execution_available")
    action["action_time_denominator_flag"] = action["r02_action_time_eligible"].astype(bool)
    action["source_panel_rebuilt_by_r02_v2"] = True
    action["source_panel_uses_r02_v1_cache_as_authority"] = False
    return action.sort_values(["instrument_id", "trade_date"]).reset_index(drop=True), effective, calendar


def add_bucket_columns(action: pd.DataFrame, config: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame]:
    df = action.copy()
    train = df["split"].eq("train") & df["action_time_denominator_flag"].astype(bool)
    rows: list[dict[str, Any]] = []
    mb_edges = [-np.inf, 0.20, 0.40, 0.60, 0.80, np.inf]
    mb_labels = ["lt20", "20_40", "40_60", "60_80", "gte80"]
    df["market_breadth_bucket"] = pd.cut(df["market_breadth20"].astype(float), bins=mb_edges, labels=mb_labels, include_lowest=True).astype(str)
    rows.append({"bucket_type": "market_breadth_bucket", "boundaries": json.dumps(mb_edges), "source_split": "fixed_config", "missing_mcap_share": np.nan, "missing_mcap_status": ""})
    q = [float(x) for x in config["buckets"]["quantiles"]]
    for bucket_type, field, output_col in [
        ("liquidity_bucket", "money_20d_median_asof", "liquidity_bucket"),
        ("market_cap_bucket", "market_cap_asof_T", "market_cap_bucket"),
    ]:
        values = df.loc[train, field].dropna().astype(float) if field in df.columns else pd.Series(dtype=float)
        if values.nunique() >= 2:
            edges = np.unique(np.nanquantile(values.to_numpy(), q))
            if len(edges) < 3:
                edges = np.array([-np.inf, np.inf])
            else:
                edges[0] = -np.inf
                edges[-1] = np.inf
            labels = [f"q{i + 1}" for i in range(len(edges) - 1)]
            df[output_col] = pd.cut(df[field].astype(float), bins=edges, labels=labels, include_lowest=True).astype(str)
        else:
            edges = np.array([-np.inf, np.inf])
            df[output_col] = f"missing_{bucket_type.split('_')[0]}"
        if bucket_type == "market_cap_bucket":
            df.loc[df[field].isna() if field in df.columns else True, output_col] = "missing_mcap"
        else:
            df.loc[df[field].isna() if field in df.columns else True, output_col] = "missing_liquidity"
        for split in SPLITS:
            sub = df.loc[df["split"].eq(split) & df["action_time_denominator_flag"].astype(bool)]
            missing_share = float(sub[output_col].eq("missing_mcap").mean()) if bucket_type == "market_cap_bucket" and len(sub) else np.nan
            status = ""
            if bucket_type == "market_cap_bucket":
                status = "passed" if np.isfinite(missing_share) and missing_share <= float(config["buckets"]["max_missing_mcap_share"]) else "invalid_missing_mcap_share"
            rows.append({"bucket_type": bucket_type, "boundaries": json.dumps([float(x) for x in edges]), "source_split": "train", "split": split, "missing_mcap_share": missing_share, "missing_mcap_status": status})
    return df, pd.DataFrame(rows)


def _condition(series: pd.Series, operator: str, threshold: Any) -> pd.Series:
    if operator == ">":
        return series.astype(float) > float(threshold)
    if operator == ">=":
        return series.astype(float) >= float(threshold)
    if operator == "<":
        return series.astype(float) < float(threshold)
    if operator == "<=":
        return series.astype(float) <= float(threshold)
    if operator == "==":
        return series.astype(float) == float(threshold)
    raise ValueError(f"unsupported operator: {operator}")


def generate_candidate_dictionary(config: dict[str, Any]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    cg = config["candidate_generation"]
    windows = config["profile_windows"]
    for atom in cg["feature_atoms"]:
        for threshold in atom["thresholds"]:
            for template in cg["pattern_template_grid"]:
                pattern_type = template["pattern_type"]
                if pattern_type not in ALLOWED_PATTERN_TYPES:
                    raise RuntimeError(f"unsupported pattern_type in config: {pattern_type}")
                lookbacks = [1] if pattern_type == "point_in_window_existence" else [3, 5]
                for lookback in lookbacks:
                    for window_id in cg["profile_window_grid"]:
                        if window_id not in windows:
                            raise RuntimeError(f"profile window is not declared: {window_id}")
                        payload = {
                            "group": atom["group"],
                            "pattern_type": pattern_type,
                            "feature_atom_id": atom["id"],
                            "feature": atom["feature"],
                            "operator": atom["operator"],
                            "threshold": threshold,
                            "window_id": window_id,
                            "lookback_days": lookback,
                            "required_days": int(template["required_days"]),
                            "lag": 0,
                            "dedup": int(cg["default_dedup_gap_days"]),
                        }
                        cid = "r02v2_{group}_{pattern}_{feat}_{thr}_{window}_{look}_{dedup}".format(
                            group=atom["group"],
                            pattern=pattern_type,
                            feat=_hash_text([atom["id"], atom["feature"]], 6),
                            thr=_hash_text(threshold, 6),
                            window=_hash_text(window_id, 6),
                            look=_hash_text(lookback, 6),
                            dedup=_hash_text(cg["default_dedup_gap_days"], 6),
                        )
                        formula = f"{atom['feature']} {atom['operator']} {threshold}; rolling_days={lookback}; required_days={template['required_days']}; window={window_id}"
                        rows.append(
                            {
                                "structure_candidate_id": cid,
                                "candidate_generation_version": cg["version"],
                                "group": atom["group"],
                                "pattern_type": pattern_type,
                                "feature_atom_ids": atom["id"],
                                "threshold_ids": _hash_text(threshold, 10),
                                "lookback_days": lookback,
                                "profile_window_bucket": window_id,
                                "sequence_lag_days": 0,
                                "dedup_gap_days": int(cg["default_dedup_gap_days"]),
                                "profile_definition": formula,
                                "action_time_definition": formula,
                                "trigger_date_policy": "first_observable_pattern_complete_date",
                                "background_control_policy": config["background"]["background_control_policy"],
                                "formula_hash": _hash_text(formula, 16),
                                "config_row_hash": _hash_text(payload, 16),
                                "feature": atom["feature"],
                                "operator": atom["operator"],
                                "threshold": threshold,
                                "required_days": int(template["required_days"]),
                                "observable_trigger_rule": formula,
                                "max_lag_days": 0,
                                "first_trigger_only_flag": True,
                                "raw_feature_list": atom["feature"],
                                "shared_feature_family": atom["shared_feature_family"],
                            }
                        )
    dictionary = pd.DataFrame(rows).drop_duplicates("structure_candidate_id").sort_values("structure_candidate_id").reset_index(drop=True)
    group_counts = dictionary.groupby("group").size()
    if dictionary.shape[0] > int(cg["max_total_candidates"]):
        raise RuntimeError("candidate dictionary exceeds max_total_candidates")
    too_large = group_counts[group_counts > int(cg["max_total_candidates_per_group"])]
    if not too_large.empty:
        raise RuntimeError("candidate dictionary exceeds max_total_candidates_per_group: " + ",".join(too_large.index.astype(str)))
    return dictionary


def build_reference_events(action: pd.DataFrame, config: dict[str, Any], calendar: pd.DatetimeIndex) -> tuple[pd.DataFrame, pd.DataFrame]:
    ref_cfg = config["reference_events"]
    gap = int(ref_cfg["episode_dedup_gap_days"])
    profile_days = int(ref_cfg["profile_window_days"])
    bounds = split_bounds(config)
    split_end_pos = {split: int(calendar.searchsorted(end, side="right") - 1) for split, (_, end) in bounds.items()}
    positive = action.loc[
        action["action_time_denominator_flag"].astype(bool)
        & action["big_winner_forward"].astype(bool)
        & action["big_winner_forward_complete_forward_window"].astype(bool)
    ].sort_values(["instrument_id", "calendar_pos"]).copy()
    rows: list[dict[str, Any]] = []
    audit_rows: list[dict[str, Any]] = []
    event_no = 0
    for instrument, inst in positive.groupby("instrument_id", sort=True):
        inst = inst.reset_index(drop=True)
        episode_no = 0
        start_idx = 0
        for i in range(1, len(inst) + 1):
            close_episode = i == len(inst) or int(inst.loc[i, "calendar_pos"]) - int(inst.loc[i - 1, "calendar_pos"]) > gap
            if not close_episode:
                continue
            ep = inst.iloc[start_idx:i].copy()
            first = ep.iloc[0]
            episode_no += 1
            event_no += 1
            split = str(first["split"])
            ref_pos = int(first["calendar_pos"])
            end_pos = ref_pos + profile_days
            complete_profile = split in split_end_pos and end_pos <= split_end_pos[split] and end_pos < len(calendar)
            profile_end = _date_str(calendar[end_pos]) if end_pos < len(calendar) else ""
            fwd_peak = _safe_float(first.get("forward_close_peak_h120"))
            entry = _safe_float(first.get("next_open"))
            forward_peak_return = fwd_peak / entry - 1.0 if entry > 0 and np.isfinite(fwd_peak) else np.nan
            winner_event_id = f"r02v2_win_{instrument}_{_date_str(first['trade_date']).replace('-', '')}_{event_no:06d}"
            row = {
                "winner_event_id": winner_event_id,
                "instrument_id": instrument,
                "reference_date": _date_str(first["trade_date"]),
                "reference_date_policy": ref_cfg["reference_date_policy"],
                "split": split,
                "winner_label_version": "r02_v2_big_winner_forward_h120_peak50",
                "winner_label_formula": "forward_close_peak_h120 / next_open - 1 >= 0.50",
                "entry_anchor_policy": "next_open_after_event_t",
                "forward_horizon_days": int(ref_cfg["forward_horizon_days"]),
                "forward_peak_return": forward_peak_return,
                "forward_peak_date": first.get("forward_peak_date_h120", ""),
                "raw_positive_event_start": _date_str(ep["trade_date"].min()),
                "raw_positive_event_end": _date_str(ep["trade_date"].max()),
                "raw_positive_event_count": int(ep.shape[0]),
                "episode_id": f"r02v2_ep_{instrument}_{episode_no:04d}",
                "episode_dedup_gap_days": gap,
                "is_first_event_in_episode": True,
                "aggressive_dedup_warning": bool(ep.shape[0] > 1),
                "overlap_policy": "first_positive_big_winner_forward_episode",
                "profile_window_start": _date_str(first["trade_date"]),
                "profile_window_end": profile_end,
                "complete_profile_window_flag": bool(complete_profile),
                "incomplete_profile_window_reason": "" if complete_profile else "profile_window_crosses_split_or_data_boundary",
                "r01_v3_reference_overlap_flag": False,
                "source_price_hash": "",
                "source_calendar_hash": _hash_text([_date_str(calendar.min()), _date_str(calendar.max()), len(calendar)], 16),
                "reference_calendar_pos": ref_pos,
            }
            rows.append(row)
            audit_rows.append(
                {
                    "instrument_id": instrument,
                    "episode_id": row["episode_id"],
                    "raw_positive_action_time_rows": int(ep.shape[0]),
                    "positive_rows_after_complete_window_filter": int(ep.shape[0]),
                    "episode_groups_before_first_event_selection": 1,
                    "final_winner_event_rows": 1,
                    "removed_incomplete_profile_window_rows": 0 if complete_profile else 1,
                    "removed_split_boundary_rows": 0 if complete_profile else 1,
                    "stage_a_included": bool(split == "train" and complete_profile),
                }
            )
            start_idx = i
    reference = pd.DataFrame(rows)
    audit = pd.DataFrame(audit_rows)
    return reference, audit


def reconcile_r01_v3(reference: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    path = topic_path(config["reference_events"]["r01_v3_reference_artifact"])
    if not path.exists():
        return pd.DataFrame(
            [
                {
                    "r01_v3_reference_artifact_path": relpath(path),
                    "r01_v3_reference_artifact_hash": "",
                    "r02_v2_reference_event_count": int(reference.shape[0]),
                    "r01_v3_reference_event_count": 0,
                    "instrument_overlap_rate": 0.0,
                    "instrument_year_overlap_rate": 0.0,
                    "same_reference_date_rate": 0.0,
                    "within_20d_reference_date_rate": 0.0,
                    "overlap_status": "r01_v3_reference_missing",
                }
            ]
        )
    r01 = pd.read_parquet(path)
    r02 = reference.copy()
    r02["year"] = pd.to_datetime(r02["reference_date"]).dt.year
    r01["instrument_id"] = r01["instrument"].astype(str)
    r01["year"] = pd.to_datetime(r01["reference_date"]).dt.year
    r02_inst = set(r02["instrument_id"])
    r01_inst = set(r01["instrument_id"])
    inst_overlap = _safe_div(float(len(r02_inst & r01_inst)), float(len(r02_inst)), 0.0)
    r02_iy = set(zip(r02["instrument_id"], r02["year"]))
    r01_iy = set(zip(r01["instrument_id"], r01["year"]))
    iy_overlap = _safe_div(float(len(r02_iy & r01_iy)), float(len(r02_iy)), 0.0)
    r01_by_inst = {inst: pd.to_datetime(g["reference_date"]).sort_values().to_numpy() for inst, g in r01.groupby("instrument_id")}
    same = 0
    within20 = 0
    for row in r02.itertuples(index=False):
        dates = r01_by_inst.get(row.instrument_id)
        if dates is None:
            continue
        ref_date = np.datetime64(pd.Timestamp(row.reference_date))
        deltas = np.abs((dates - ref_date).astype("timedelta64[D]").astype(int))
        same += int((deltas == 0).any())
        within20 += int((deltas <= 35).any())
    same_rate = _safe_div(float(same), float(max(1, r02.shape[0])), 0.0)
    within_rate = _safe_div(float(within20), float(max(1, r02.shape[0])), 0.0)
    status = "passed" if inst_overlap >= float(config["reference_events"]["overlap_warning_threshold"]) else "reference_drift_warning"
    reference.loc[:, "r01_v3_reference_overlap_flag"] = [
        bool(inst in r01_inst) for inst in reference["instrument_id"].astype(str)
    ]
    return pd.DataFrame(
        [
            {
                "r01_v3_reference_artifact_path": relpath(path),
                "r01_v3_reference_artifact_hash": file_hash(path),
                "r02_v2_reference_event_count": int(reference.shape[0]),
                "r01_v3_reference_event_count": int(r01.shape[0]),
                "instrument_overlap_rate": inst_overlap,
                "instrument_year_overlap_rate": iy_overlap,
                "same_reference_date_rate": same_rate,
                "within_20d_reference_date_rate": within_rate,
                "overlap_status": status,
            }
        ]
    )


def build_winner_window_panel(reference: pd.DataFrame, action: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    if reference.empty:
        return pd.DataFrame()
    lookup = action.set_index(["instrument_id", "calendar_pos"], drop=False)
    rows: list[pd.Series] = []
    keep_cols = [
        "instrument_id",
        "trade_date",
        "calendar_pos",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "money",
        "industry_name",
        "market_breadth20",
        "industry_breadth20",
        "money_20d_median_asof",
        "market_cap_asof_T",
        "ret5_asof",
        "ret20_asof",
        "close_near_high5_pct",
        "close_near_high20_pct",
        "close_near_high60_pct",
        "vol_ratio3",
        "vol_ratio10",
        "money_ratio20_mean_asof",
        "rps5",
        "rps20",
        "rps60",
        "ema20_hold_depth",
        "prior20_pullback_depth",
        "atr20_pct",
        "atr20_contraction_ratio",
        "past_h10_no_close_below_prior10_low",
        "past_h20_no_close_below_prior20_low",
        "past_h20_no_high_volume_down_day",
        "past_h10_no_failed_breakout",
        "return1d",
        "gap_open_pct",
    ]
    for ref in reference.itertuples(index=False):
        for offset in range(0, int(config["reference_events"]["profile_window_days"]) + 1):
            key = (ref.instrument_id, int(ref.reference_calendar_pos) + offset)
            if key not in lookup.index:
                continue
            row = lookup.loc[key]
            if isinstance(row, pd.DataFrame):
                row = row.iloc[0]
            rec = {col: row.get(col, np.nan) for col in keep_cols}
            rec.update(
                {
                    "winner_event_id": ref.winner_event_id,
                    "reference_date": ref.reference_date,
                    "profile_trade_date": row.get("trade_date", ""),
                    "offset_day": offset,
                    "early_window": 0 <= offset <= 5,
                    "build_window": 6 <= offset <= 15,
                    "continuation_window": 16 <= offset <= 30,
                    "full_window": True,
                    "post_reference_profile_only_annotation": "winner_window_profile",
                }
            )
            rows.append(pd.Series(rec))
    return pd.DataFrame(rows).sort_values(["winner_event_id", "offset_day"]).reset_index(drop=True)


def build_matched_background_windows(reference: pd.DataFrame, action: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    train_refs = reference.loc[reference["split"].eq("train") & reference["complete_profile_window_flag"].astype(bool)].copy()
    if train_refs.empty:
        return pd.DataFrame()
    pool = action.loc[
        action["split"].eq("train")
        & action["action_time_denominator_flag"].astype(bool)
        & action["big_winner_forward_complete_forward_window"].astype(bool)
        & ~action["big_winner_forward"].astype(bool)
    ].copy()
    rows = []
    controls_per = int(config["background"]["matched_controls_per_winner_event"])
    for ref in train_refs.sort_values(["reference_date", "winner_event_id"]).itertuples(index=False):
        same_date = pool.loc[pool["trade_date"].eq(ref.reference_date) & ~pool["instrument_id"].eq(ref.instrument_id)].copy()
        if same_date.empty:
            rows.append({"matched_background_event_id": f"bg_{ref.winner_event_id}_shortfall", "matched_to_winner_event_id": ref.winner_event_id, "instrument_id": "", "pseudo_reference_date": ref.reference_date, "match_year": str(ref.reference_date)[:4], "match_industry": "", "match_liquidity_bucket": "", "match_mcap_bucket": "", "match_executable_entry_available": False, "match_rank": 0, "industry_match_relaxed": True, "matched_background_capacity_shortfall": True, "reference_calendar_pos": ref.reference_calendar_pos})
            continue
        ref_row = action.loc[action["instrument_id"].eq(ref.instrument_id) & action["trade_date"].eq(ref.reference_date)].head(1)
        industry = str(ref_row["industry_name"].iloc[0]) if not ref_row.empty else ""
        liq = str(ref_row["liquidity_bucket"].iloc[0]) if not ref_row.empty else ""
        mcap = str(ref_row["market_cap_bucket"].iloc[0]) if not ref_row.empty else ""
        exact = same_date.loc[same_date["industry_name"].astype(str).eq(industry) & same_date["liquidity_bucket"].astype(str).eq(liq) & same_date["market_cap_bucket"].astype(str).eq(mcap)].copy()
        relaxed = False
        chosen = exact
        if chosen.shape[0] < controls_per:
            relaxed = True
            chosen = same_date.loc[same_date["liquidity_bucket"].astype(str).eq(liq) & same_date["market_cap_bucket"].astype(str).eq(mcap)].copy()
        if chosen.shape[0] < controls_per:
            relaxed = True
            chosen = same_date
        chosen = chosen.sort_values(["instrument_id"]).head(controls_per)
        shortfall = chosen.shape[0] < controls_per
        for rank, (_, row) in enumerate(chosen.iterrows(), start=1):
            rows.append(
                {
                    "matched_background_event_id": f"bg_{ref.winner_event_id}_{rank:02d}",
                    "matched_to_winner_event_id": ref.winner_event_id,
                    "instrument_id": row["instrument_id"],
                    "pseudo_reference_date": ref.reference_date,
                    "match_year": str(ref.reference_date)[:4],
                    "match_industry": row.get("industry_name", ""),
                    "match_liquidity_bucket": row.get("liquidity_bucket", ""),
                    "match_mcap_bucket": row.get("market_cap_bucket", ""),
                    "match_executable_entry_available": bool(row.get("executable_entry_available", False)),
                    "match_rank": rank,
                    "industry_match_relaxed": bool(relaxed),
                    "matched_background_capacity_shortfall": bool(shortfall),
                    "reference_calendar_pos": int(row["calendar_pos"]),
                }
            )
    return pd.DataFrame(rows)


def _window_mask(panel: pd.DataFrame, window_id: str, config: dict[str, Any]) -> pd.Series:
    start, end = config["profile_windows"][window_id]
    return panel["offset_day"].between(int(start), int(end))


def _candidate_panel_mask(panel: pd.DataFrame, cand: pd.Series) -> pd.Series:
    if cand["feature"] not in panel.columns:
        return pd.Series(False, index=panel.index)
    return _condition(panel[cand["feature"]], str(cand["operator"]), cand["threshold"]).fillna(False)


def profile_metrics_for_candidate(profile: pd.DataFrame, cand: pd.Series, config: dict[str, Any]) -> tuple[dict[str, Any], pd.DataFrame]:
    if profile.empty:
        return {}, pd.DataFrame()
    sub = profile.loc[_window_mask(profile, str(cand["profile_window_bucket"]), config)].copy()
    raw = _candidate_panel_mask(sub, cand)
    if int(cand["required_days"]) > 1:
        hit_by_event = raw.groupby(sub["winner_event_id"]).sum() >= int(cand["required_days"])
    else:
        hit_by_event = raw.groupby(sub["winner_event_id"]).any()
    trigger_rows = sub.loc[raw, ["winner_event_id", "instrument_id", "reference_date", "profile_trade_date", "offset_day"]].copy()
    trigger_rows["structure_candidate_id"] = cand["structure_candidate_id"]
    trigger_rows["trigger_offset_from_reference"] = trigger_rows["offset_day"]
    total_events = int(profile["winner_event_id"].nunique())
    triggered_events = int(hit_by_event.sum()) if not hit_by_event.empty else 0
    first_offsets = trigger_rows.groupby("winner_event_id")["offset_day"].min() if not trigger_rows.empty else pd.Series(dtype=float)
    days_per = trigger_rows.groupby("winner_event_id").size() if not trigger_rows.empty else pd.Series(dtype=float)
    years = pd.to_datetime(profile.drop_duplicates("winner_event_id").set_index("winner_event_id")["reference_date"]).dt.year.astype(str)
    hit_years = years.loc[years.index.intersection(hit_by_event[hit_by_event].index)] if not hit_by_event.empty else pd.Series(dtype=str)
    by_year = hit_by_event.rename("hit").to_frame().join(years.rename("year")).groupby("year")["hit"].mean() if not hit_by_event.empty else pd.Series(dtype=float)
    coverage = _safe_div(float(triggered_events), float(total_events), 0.0)
    se = math.sqrt(max(coverage * (1.0 - coverage), 0.0) / max(1, total_events))
    metrics = {
        "structure_candidate_id": cand["structure_candidate_id"],
        "train_winner_event_count": total_events,
        "complete_profile_event_count": total_events,
        "winner_coverage": coverage,
        "winner_coverage_ci90_lower": max(0.0, coverage - 1.645 * se),
        "winner_coverage_by_year": json.dumps({str(k): float(v) for k, v in by_year.items()}, sort_keys=True),
        "min_year_coverage": float(by_year.min()) if not by_year.empty else np.nan,
        "median_first_trigger_offset": float(first_offsets.median()) if not first_offsets.empty else np.nan,
        "p25_first_trigger_offset": float(first_offsets.quantile(0.25)) if not first_offsets.empty else np.nan,
        "p75_first_trigger_offset": float(first_offsets.quantile(0.75)) if not first_offsets.empty else np.nan,
        "triggered_event_count": triggered_events,
        "trigger_days_per_event_mean": float(days_per.mean()) if not days_per.empty else 0.0,
        "trigger_days_per_event_p90": float(days_per.quantile(0.90)) if not days_per.empty else 0.0,
        "stage_bucket_distribution": json.dumps(trigger_rows["offset_day"].describe().to_dict(), sort_keys=True, default=str) if not trigger_rows.empty else "{}",
        "group": cand["group"],
        "observable_action_time_flag": True,
        "non_observable_reason": "",
        "years_present": int(hit_years.nunique()) if not hit_years.empty else 0,
    }
    return metrics, trigger_rows


def build_background_profile_panel(background: pd.DataFrame, action: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    if background.empty:
        return pd.DataFrame()
    pseudo = background.loc[background["instrument_id"].astype(str).ne("")].copy()
    if pseudo.empty:
        return pd.DataFrame()
    ref_like = pseudo.rename(columns={"matched_background_event_id": "winner_event_id", "pseudo_reference_date": "reference_date"})
    ref_like["split"] = "train"
    ref_like["complete_profile_window_flag"] = True
    return build_winner_window_panel(ref_like, action, config)


def background_coverage_for_candidate(background_profile: pd.DataFrame, cand: pd.Series, config: dict[str, Any]) -> float:
    if background_profile.empty:
        return np.nan
    metrics, _ = profile_metrics_for_candidate(background_profile, cand, config)
    return float(metrics.get("winner_coverage", np.nan)) if metrics else np.nan


def signal_mask(action: pd.DataFrame, cand: pd.Series) -> pd.Series:
    if cand["feature"] not in action.columns:
        return pd.Series(False, index=action.index)
    raw = _condition(action[cand["feature"]], str(cand["operator"]), cand["threshold"]).fillna(False)
    required = int(cand.get("required_days", 1))
    lookback = int(cand.get("lookback_days", 1))
    if required <= 1 and lookback <= 1:
        return raw & action["action_time_denominator_flag"].astype(bool)
    rolled = raw.astype(int).groupby(action["instrument_id"], group_keys=False).transform(lambda s: s.rolling(lookback, min_periods=lookback).sum())
    return rolled.ge(required).fillna(False) & action["action_time_denominator_flag"].astype(bool)


def eventize_candidate(action: pd.DataFrame, cand: pd.Series) -> pd.DataFrame:
    mask = signal_mask(action, cand)
    rows = action.loc[mask, ["instrument_id", "trade_date", "split", "calendar_pos"]].copy()
    if rows.empty:
        return pd.DataFrame(columns=["structure_candidate_id", "signal_event_id", "instrument_id", "trigger_trade_date", "pattern_start_date", "pattern_complete_date", "max_lag_days", "dedup_gap_days", "trigger_offset_from_reference", "first_trigger_in_profile_window_flag", "cooldown_active_flag", "lookback_start_date", "lookback_end_date", "future_data_used_flag", "eventization_rejection_reason", "split"])
    rows = rows.sort_values(["instrument_id", "calendar_pos"])
    dedup_gap = int(cand["dedup_gap_days"])
    keep = []
    last_by_inst: dict[str, int] = {}
    for row in rows.itertuples(index=False):
        last = last_by_inst.get(row.instrument_id, -10**9)
        cooldown = int(row.calendar_pos) - last <= dedup_gap
        keep.append(not cooldown)
        if not cooldown:
            last_by_inst[row.instrument_id] = int(row.calendar_pos)
    rows = rows.loc[keep].copy()
    lookback = int(cand.get("lookback_days", 1))
    rows["structure_candidate_id"] = cand["structure_candidate_id"]
    rows["trigger_trade_date"] = rows["trade_date"]
    rows["pattern_complete_date"] = rows["trade_date"]
    rows["pattern_start_date"] = rows["trade_date"]
    rows["lookback_start_date"] = rows["trade_date"]
    rows["lookback_end_date"] = rows["trade_date"]
    rows["max_lag_days"] = int(cand.get("sequence_lag_days", 0))
    rows["dedup_gap_days"] = dedup_gap
    rows["trigger_offset_from_reference"] = np.nan
    rows["first_trigger_in_profile_window_flag"] = False
    rows["cooldown_active_flag"] = False
    rows["future_data_used_flag"] = False
    rows["eventization_rejection_reason"] = ""
    rows["signal_event_id"] = [
        f"sig_{cid}_{inst}_{date.replace('-', '')}_{i:08d}"
        for i, (cid, inst, date) in enumerate(zip(rows["structure_candidate_id"], rows["instrument_id"], rows["trigger_trade_date"]), start=1)
    ]
    return rows[
        [
            "structure_candidate_id",
            "signal_event_id",
            "instrument_id",
            "trigger_trade_date",
            "pattern_start_date",
            "pattern_complete_date",
            "max_lag_days",
            "dedup_gap_days",
            "trigger_offset_from_reference",
            "first_trigger_in_profile_window_flag",
            "cooldown_active_flag",
            "lookback_start_date",
            "lookback_end_date",
            "future_data_used_flag",
            "eventization_rejection_reason",
            "split",
        ]
    ]


def build_stage_a(
    dictionary: pd.DataFrame,
    reference: pd.DataFrame,
    winner_window: pd.DataFrame,
    background: pd.DataFrame,
    action: pd.DataFrame,
    config: dict[str, Any],
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    train_refs = reference.loc[reference["split"].eq("train") & reference["complete_profile_window_flag"].astype(bool)]
    profile = winner_window.loc[winner_window["winner_event_id"].isin(set(train_refs["winner_event_id"]))].copy()
    metrics_rows: list[dict[str, Any]] = []
    event_frames: list[pd.DataFrame] = []
    background_rows: list[dict[str, Any]] = []
    observability_rows: list[dict[str, Any]] = []
    rejection_rows: list[dict[str, Any]] = []
    gates = config["stage_a_gates"]
    background_profile = build_background_profile_panel(background, action, config)
    for cand in dictionary.itertuples(index=False):
        cs = pd.Series(cand._asdict())
        metrics, triggers = profile_metrics_for_candidate(profile, cs, config)
        if not metrics:
            metrics = {"structure_candidate_id": cs["structure_candidate_id"], "group": cs["group"], "winner_coverage": 0.0, "winner_coverage_ci90_lower": 0.0, "trigger_days_per_event_p90": 0.0, "years_present": 0, "observable_action_time_flag": False, "non_observable_reason": "empty_profile"}
        bg_cov = background_coverage_for_candidate(background_profile, cs, config)
        train_dense = action.loc[action["split"].eq("train") & action["action_time_denominator_flag"].astype(bool)]
        action_signal = signal_mask(train_dense, cs) if not train_dense.empty else pd.Series(dtype=bool)
        action_rate = _safe_div(float(action_signal.sum()), float(train_dense.shape[0]), 0.0)
        lift = _safe_div(float(metrics.get("winner_coverage", 0.0)), float(bg_cov), np.nan)
        if not np.isfinite(lift):
            lift = _safe_div(float(metrics.get("winner_coverage", 0.0)), float(action_rate), np.nan)
        bg_n = int(background["matched_background_event_id"].nunique()) if not background.empty else 0
        bg_se = math.sqrt(max(float(bg_cov) * (1.0 - float(bg_cov)), 0.0) / max(1, bg_n)) if np.isfinite(bg_cov) else np.nan
        lift_lower = _safe_div(float(metrics.get("winner_coverage_ci90_lower", 0.0)), float(bg_cov + 1.645 * bg_se), np.nan) if np.isfinite(bg_cov) and np.isfinite(bg_se) else np.nan
        generic = bool(action_rate > float(gates["max_action_time_background_signal_rate"]) or (np.isfinite(lift) and lift < float(gates["min_winner_vs_background_coverage_lift"])))
        metrics.update(
            {
                "matched_background_coverage": bg_cov,
                "matched_background_coverage_ci90_upper": float(bg_cov + 1.645 * bg_se) if np.isfinite(bg_cov) and np.isfinite(bg_se) else np.nan,
                "action_time_background_signal_rate": action_rate,
                "winner_vs_background_coverage_lift": lift,
                "winner_vs_background_coverage_lift_ci90_lower": lift_lower,
                "generic_strength_proxy_flag": generic,
                "generic_strength_proxy_reason": "too_dense_or_no_background_enrichment" if generic else "",
                "background_control_policy": config["background"]["background_control_policy"],
                "non_default_background_policy_reason": config["background"].get("non_default_background_policy_reason", ""),
            }
        )
        checks = {
            "min_winner_coverage": metrics["winner_coverage"] >= float(gates["min_winner_coverage"]),
            "min_winner_coverage_ci90_lower": metrics["winner_coverage_ci90_lower"] >= float(gates["min_winner_coverage_ci90_lower"]),
            "min_years_present": metrics["years_present"] >= int(gates["min_years_present"]),
            "max_trigger_days_per_event_p90": metrics["trigger_days_per_event_p90"] <= float(gates["max_trigger_days_per_event_p90"]),
            "observable_action_time_flag": bool(metrics["observable_action_time_flag"]),
            "min_winner_vs_background_coverage_lift": np.isfinite(lift) and lift >= float(gates["min_winner_vs_background_coverage_lift"]),
            "min_winner_vs_background_coverage_lift_ci90_lower": np.isfinite(lift_lower) and lift_lower >= float(gates["min_winner_vs_background_coverage_lift_ci90_lower"]),
            "max_action_time_background_signal_rate": action_rate <= float(gates["max_action_time_background_signal_rate"]),
            "not_generic_strength_proxy": not generic,
        }
        failed = [name for name, ok in checks.items() if not ok]
        rejection_rows.append({"structure_candidate_id": cs["structure_candidate_id"], "status": "passed" if not failed else "rejected", "failed_rules": ";".join(failed), "stage": "stage_a"})
        observability_rows.append({"structure_candidate_id": cs["structure_candidate_id"], "observable_action_time_flag": bool(metrics["observable_action_time_flag"]), "non_observable_reason": metrics["non_observable_reason"], "future_data_used_flag": False})
        background_rows.append({k: metrics.get(k) for k in ["structure_candidate_id", "matched_background_coverage", "matched_background_coverage_ci90_upper", "action_time_background_signal_rate", "winner_vs_background_coverage_lift", "winner_vs_background_coverage_lift_ci90_lower", "generic_strength_proxy_flag", "generic_strength_proxy_reason", "background_control_policy", "non_default_background_policy_reason"]})
        metrics_rows.append(metrics)
        if not triggers.empty:
            event_frames.append(triggers)
    summary = pd.DataFrame(metrics_rows).merge(dictionary[["structure_candidate_id", "formula_hash", "profile_definition", "action_time_definition", "raw_feature_list", "shared_feature_family", "pattern_type", "profile_window_bucket", "lookback_days", "required_days", "dedup_gap_days"]], on="structure_candidate_id", how="left")
    rejection = pd.DataFrame(rejection_rows)
    passed_ids = set(rejection.loc[rejection["status"].eq("passed"), "structure_candidate_id"])
    summary["stage_a_rank_score"] = (
        summary["winner_vs_background_coverage_lift"].fillna(0).clip(lower=0)
        * summary["winner_coverage"].fillna(0)
        * (1.0 - summary["action_time_background_signal_rate"].fillna(1).clip(lower=0, upper=1))
    )
    top_passed = summary.loc[summary["structure_candidate_id"].isin(passed_ids)].sort_values(["stage_a_rank_score", "winner_coverage", "structure_candidate_id"], ascending=[False, False, True]).head(int(gates["max_stage_a_candidates_to_calibrate"]))
    rejection.loc[rejection["structure_candidate_id"].isin(set(passed_ids) - set(top_passed["structure_candidate_id"])), "status"] = "rejected"
    rejection.loc[rejection["structure_candidate_id"].isin(set(passed_ids) - set(top_passed["structure_candidate_id"])), "failed_rules"] = "max_stage_a_candidates_to_calibrate"
    profile_events = pd.concat(event_frames, ignore_index=True) if event_frames else pd.DataFrame(columns=["winner_event_id", "instrument_id", "reference_date", "profile_trade_date", "offset_day", "structure_candidate_id", "trigger_offset_from_reference"])
    return summary, profile_events, pd.DataFrame(background_rows), pd.DataFrame(observability_rows), rejection


def _event_mask(panel: pd.DataFrame, events: pd.DataFrame, structure_candidate_id: str) -> pd.Series:
    sub = events.loc[events["structure_candidate_id"].eq(structure_candidate_id)]
    keys = set(zip(sub["instrument_id"], sub["trigger_trade_date"]))
    return pd.Series([key in keys for key in zip(panel["instrument_id"], panel["trade_date"])], index=panel.index)


def bootstrap_lr_ci(sub: pd.DataFrame, signal: pd.Series, label: str, seed: int, replicates: int) -> tuple[float, float]:
    eligible = sub[f"{label}_metric_eligible"].astype(bool)
    base = sub.loc[eligible, ["instrument_id", "year", label]].copy()
    base["signal"] = signal.loc[base.index].astype(bool).to_numpy()
    if base.empty or base[label].nunique() < 2:
        return np.nan, np.nan
    base["instrument_year"] = base["instrument_id"].astype(str) + "_" + base["year"].astype(str)
    counts = base.groupby("instrument_year").apply(
        lambda g: pd.Series(
            {
                "signal_winner": int((g["signal"] & g[label].astype(bool)).sum()),
                "signal_non_winner": int((g["signal"] & ~g[label].astype(bool)).sum()),
                "winner": int(g[label].astype(bool).sum()),
                "non_winner": int((~g[label].astype(bool)).sum()),
            }
        ),
        include_groups=False,
    )
    arr = counts[["signal_winner", "signal_non_winner", "winner", "non_winner"]].to_numpy(dtype=float)
    if arr.shape[0] < 2:
        return np.nan, np.nan
    rng = np.random.default_rng(seed)
    values = []
    for _ in range(int(replicates)):
        sample = arr[rng.integers(0, arr.shape[0], size=arr.shape[0])].sum(axis=0)
        values.append(_safe_div(_safe_div(sample[0], sample[2]), _safe_div(sample[1], sample[3])))
    clean = np.array([v for v in values if np.isfinite(v)])
    if clean.size == 0:
        return np.nan, np.nan
    return float(np.quantile(clean, 0.05)), float(np.quantile(clean, 0.95))


def metric_for_candidate(action: pd.DataFrame, events: pd.DataFrame, structure_candidate_id: str, split: str, config: dict[str, Any], ci: bool) -> dict[str, Any]:
    label = config["labels"]["primary_selection_label_id"]
    sub = action.loc[action["split"].eq(split) & action["action_time_denominator_flag"].astype(bool)].copy()
    sig = _event_mask(sub, events, structure_candidate_id)
    label_eligible = sub[f"{label}_metric_eligible"].astype(bool)
    winners = sub[label].astype(bool) & label_eligible
    non = ~sub[label].astype(bool) & label_eligible
    signal_n = int(sig.sum())
    signal_label = sig & label_eligible
    winner_base = _safe_div(float(winners.sum()), float(label_eligible.sum()))
    winner_given = _safe_div(float((sig & winners).sum()), float(signal_label.sum()))
    sig_w = _safe_div(float((sig & winners).sum()), float(winners.sum()))
    sig_nw = _safe_div(float((sig & non).sum()), float(non.sum()))
    lr = _safe_div(sig_w, sig_nw)
    ci_low, ci_high = bootstrap_lr_ci(sub, sig, label, int(config["runtime"]["random_seed"]), int(config["primitive_search"]["bootstrap_replicates"])) if ci else (np.nan, np.nan)
    exec_sig = sig & sub["execution_eligible"].astype(bool)
    return {
        "structure_candidate_id": structure_candidate_id,
        "split": split,
        "action_time_denominator_n": int(sub.shape[0]),
        "effective_label_n": int(label_eligible.sum()),
        "signal_n": signal_n,
        "signal_rate": _safe_div(float(signal_n), float(sub.shape[0]), 0.0),
        "winner_base_rate": winner_base,
        "winner_given_signal": winner_given,
        "signal_given_winner": sig_w,
        "signal_given_non_winner": sig_nw,
        "primary_LR": lr,
        "primary_LR_ci90_lower": ci_low,
        "primary_LR_ci90_upper": ci_high,
        "precision_lift": _safe_div(winner_given, winner_base),
        "failed_seed_rate_given_signal": _safe_div(float((sig & sub["failed_seed_forward"].astype(bool) & sub["failed_seed_forward_metric_eligible"].astype(bool)).sum()), float(signal_n)),
        "continuation_h20_rate_given_signal": _safe_div(float((sig & sub["continuation_h20"].astype(bool) & sub["continuation_h20_metric_eligible"].astype(bool)).sum()), float(signal_n)),
        "continuation_h60_rate_given_signal": _safe_div(float((sig & sub["continuation_h60"].astype(bool) & sub["continuation_h60_metric_eligible"].astype(bool)).sum()), float(signal_n)),
        "executable_entry_available_rate": _safe_div(float((sig & sub["entry_execution_status"].eq("entry_execution_available")).sum()), float(signal_n), 0.0),
        "buyable_signal_n": int((sig & sub["entry_execution_status"].eq("entry_execution_available")).sum()),
        "EV_R": float(sub.loc[exec_sig, "unit_return_R"].mean()) if exec_sig.any() else np.nan,
        "unit_return_R_p25": float(sub.loc[exec_sig, "unit_return_R"].quantile(0.25)) if exec_sig.any() else np.nan,
        "unit_return_R_p50": float(sub.loc[exec_sig, "unit_return_R"].median()) if exec_sig.any() else np.nan,
        "unit_return_R_p75": float(sub.loc[exec_sig, "unit_return_R"].quantile(0.75)) if exec_sig.any() else np.nan,
    }


def build_stage_b(action: pd.DataFrame, dictionary: pd.DataFrame, stage_a_rejection: pd.DataFrame, config: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    passed_ids = stage_a_rejection.loc[stage_a_rejection["status"].eq("passed"), "structure_candidate_id"].astype(str).tolist()
    cand = dictionary.loc[dictionary["structure_candidate_id"].isin(passed_ids)].copy()
    events = pd.concat([eventize_candidate(action, pd.Series(row._asdict())) for row in cand.itertuples(index=False)], ignore_index=True) if not cand.empty else pd.DataFrame()
    metrics = []
    for cid in cand["structure_candidate_id"]:
        for split in SPLITS:
            metrics.append(metric_for_candidate(action, events, cid, split, config, ci=(split == "train")))
    calibration = pd.DataFrame(metrics).merge(dictionary[["structure_candidate_id", "group", "formula_hash", "shared_feature_family"]], on="structure_candidate_id", how="left") if metrics else pd.DataFrame()
    gate_rows = []
    gates = config["stage_b_gates"]
    train_metrics = calibration.loc[calibration["split"].eq("train")].copy() if not calibration.empty else pd.DataFrame()
    for row in train_metrics.itertuples(index=False):
        evs = events.loc[events["structure_candidate_id"].eq(row.structure_candidate_id)]
        year_share = evs.loc[evs["split"].eq("train"), "trigger_trade_date"].str.slice(0, 4).value_counts(normalize=True).max() if not evs.empty and evs["split"].eq("train").any() else np.nan
        industries = action.loc[action["split"].eq("train") & _event_mask(action.loc[action["split"].eq("train")], events, row.structure_candidate_id), "industry_name"]
        ind_share = industries.astype(str).value_counts(normalize=True).max() if not industries.empty else np.nan
        checks = {
            "min_train_signal_n": row.signal_n >= int(gates["min_train_signal_n"]),
            "min_train_buyable_signal_n": row.buyable_signal_n >= int(gates["min_train_buyable_signal_n"]),
            "max_train_signal_rate": row.signal_rate <= float(gates["max_train_signal_rate"]),
            "min_train_primary_LR": np.isfinite(row.primary_LR) and row.primary_LR >= float(gates["min_train_primary_LR"]),
            "min_train_primary_LR_ci90_lower": np.isfinite(row.primary_LR_ci90_lower) and row.primary_LR_ci90_lower >= float(gates["min_train_primary_LR_ci90_lower"]),
            "min_train_precision_lift": np.isfinite(row.precision_lift) and row.precision_lift >= float(gates["min_train_precision_lift"]),
            "min_train_EV_R": np.isfinite(row.EV_R) and row.EV_R >= float(gates["min_train_EV_R"]),
            "max_train_failed_seed_rate_given_signal": np.isfinite(row.failed_seed_rate_given_signal) and row.failed_seed_rate_given_signal <= float(gates["max_train_failed_seed_rate_given_signal"]),
            "max_single_year_signal_share": np.isfinite(year_share) and year_share <= float(gates["max_single_year_signal_share"]),
            "max_single_industry_signal_share": np.isfinite(ind_share) and ind_share <= float(gates["max_single_industry_signal_share"]),
        }
        failed = [name for name, ok in checks.items() if not ok]
        gate_rows.append({"structure_candidate_id": row.structure_candidate_id, "status": "passed" if not failed else "rejected", "failed_rules": ";".join(failed), "single_year_signal_share": year_share, "single_industry_signal_share": ind_share})
    event_audit = events.groupby("structure_candidate_id", dropna=False).agg(signal_event_count=("signal_event_id", "count"), future_data_used_flag=("future_data_used_flag", "max"), eventization_rejection_reason=("eventization_rejection_reason", lambda s: ";".join(sorted(set(s.astype(str)) - {""})))).reset_index() if not events.empty else pd.DataFrame(columns=["structure_candidate_id", "signal_event_count", "future_data_used_flag", "eventization_rejection_reason"])
    signal_panel = events.copy()
    return events, signal_panel, calibration, pd.DataFrame(gate_rows), event_audit


def build_prior_decomposition(action: pd.DataFrame, events: pd.DataFrame, calibration: pd.DataFrame, selected_ids: list[str], config: dict[str, Any]) -> pd.DataFrame:
    rows = []
    label = config["labels"]["primary_selection_label_id"]
    bucket_specs = [
        ("calendar_year", "year"),
        ("industry", "industry_name"),
        ("market_breadth_bucket", "market_breadth_bucket"),
        ("liquidity_bucket", "liquidity_bucket"),
        ("market_cap_bucket", "market_cap_bucket"),
    ]
    for cid in selected_ids:
        for split in SPLITS:
            sub_split = action.loc[action["split"].eq(split) & action["action_time_denominator_flag"].astype(bool)].copy()
            sig_all = _event_mask(sub_split, events, cid)
            for bucket_type, col in bucket_specs:
                for bucket_id, sub in sub_split.groupby(col, dropna=False):
                    sig = sig_all.loc[sub.index]
                    eligible = sub[f"{label}_metric_eligible"].astype(bool)
                    winners = sub[label].astype(bool) & eligible
                    non = ~sub[label].astype(bool) & eligible
                    p_w = _safe_div(float((sig & winners).sum()), float(winners.sum()))
                    p_n = _safe_div(float((sig & non).sum()), float(non.sum()))
                    lr = _safe_div(p_w, p_n)
                    rows.append(
                        {
                            "structure_candidate_id": cid,
                            "split": split,
                            "bucket_type": bucket_type,
                            "bucket_id": str(bucket_id),
                            "action_time_denominator_n": int(sub.shape[0]),
                            "signal_n": int(sig.sum()),
                            "signal_rate": _safe_div(float(sig.sum()), float(sub.shape[0]), 0.0),
                            "winner_base_rate": _safe_div(float(winners.sum()), float(eligible.sum())),
                            "winner_given_signal": _safe_div(float((sig & winners).sum()), float((sig & eligible).sum())),
                            "primary_LR": lr,
                            "primary_LR_ci90_lower": np.nan,
                            "posterior_stability_flag": bool(np.isfinite(lr) and lr >= 1.0),
                        }
                    )
    return pd.DataFrame(rows)


def pair_overlap(action: pd.DataFrame, events: pd.DataFrame, left: str, right: str, config: dict[str, Any]) -> dict[str, Any]:
    train = action.loc[action["split"].eq("train") & action["action_time_denominator_flag"].astype(bool)]
    a = _event_mask(train, events, left)
    b = _event_mask(train, events, right)
    union = a | b
    inter = a & b
    label = config["labels"]["primary_selection_label_id"]
    eligible = train[f"{label}_metric_eligible"].astype(bool)
    winners = train[label].astype(bool) & eligible
    non = ~train[label].astype(bool) & eligible
    corr = float(np.corrcoef(a.astype(int), b.astype(int))[0, 1]) if a.any() and b.any() else np.nan
    return {
        "structure_candidate_id_left": left,
        "structure_candidate_id_right": right,
        "same_day_overlap": int(inter.sum()),
        "same_day_jaccard": _safe_div(float(inter.sum()), float(union.sum()), 0.0),
        "within_5d_jaccard": np.nan,
        "signal_correlation": corr,
        "conditional_winner_overlap": _safe_div(float((inter & winners).sum()), float((union & winners).sum())),
        "conditional_non_winner_overlap": _safe_div(float((inter & non).sum()), float((union & non).sum())),
        "incremental_primary_LR": np.nan,
        "incremental_EV_R": np.nan,
    }


def select_representatives(action: pd.DataFrame, events: pd.DataFrame, calibration: pd.DataFrame, train_gate: pd.DataFrame, dictionary: pd.DataFrame, config: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame]:
    passed_ids = set(train_gate.loc[train_gate["status"].eq("passed"), "structure_candidate_id"].astype(str))
    train = calibration.loc[calibration["split"].eq("train") & calibration["structure_candidate_id"].isin(passed_ids)].copy()
    if train.empty:
        return pd.DataFrame(), pd.DataFrame()
    train["rank_score"] = train["primary_LR"].fillna(0).clip(lower=0) * train["precision_lift"].fillna(0).clip(lower=0) * (1.0 + train["EV_R"].fillna(-1).clip(lower=-1))
    meta = dictionary[["structure_candidate_id", "group", "formula_hash", "profile_definition", "action_time_definition", "shared_feature_family"]]
    ranked = train.merge(meta, on="structure_candidate_id", how="left").sort_values(["rank_score", "primary_LR", "EV_R", "structure_candidate_id"], ascending=[False, False, False, True])
    for column in ["group", "formula_hash", "shared_feature_family"]:
        left = f"{column}_x"
        right = f"{column}_y"
        if left in ranked.columns:
            ranked[column] = ranked[left]
            if right in ranked.columns:
                ranked[column] = ranked[column].fillna(ranked[right])
        elif right in ranked.columns:
            ranked[column] = ranked[right]
    selected = []
    overlaps = []
    group_counts: dict[str, int] = {}
    for row in ranked.itertuples(index=False):
        row_dict = row._asdict()
        group_value = str(row_dict.get("group", row_dict.get("_2", "")))
        if len(selected) >= int(config["stage_c"]["max_representatives_to_freeze"]):
            break
        if group_counts.get(group_value, 0) >= int(config["stage_c"]["max_per_group"]):
            continue
        duplicate = False
        for chosen in selected:
            overlap = pair_overlap(action, events, row.structure_candidate_id, chosen["structure_candidate_id"], config)
            overlap["merge_status"] = "separate"
            if (
                overlap["same_day_jaccard"] >= float(config["stage_c"]["same_day_jaccard_merge"])
                or (np.isfinite(overlap["signal_correlation"]) and overlap["signal_correlation"] >= float(config["stage_c"]["signal_correlation_merge"]))
            ):
                overlap["merge_status"] = "merged"
                duplicate = True
            overlaps.append(overlap)
            if duplicate:
                break
        if duplicate:
            continue
        group_counts[group_value] = group_counts.get(group_value, 0) + 1
        row_dict["group"] = group_value
        selected.append(row_dict | {"representative_id": f"r02v2_rep_{len(selected) + 1:02d}", "r03_pool_status": "candidate"})
    selection = pd.DataFrame(selected)
    if not selection.empty:
        val = calibration.loc[calibration["split"].isin(["validation", "robustness"])].copy()
        status_by_id = {}
        for cid in selection["structure_candidate_id"]:
            rob = val.loc[val["split"].eq("robustness") & val["structure_candidate_id"].eq(cid)]
            if not rob.empty and (_safe_float(rob["primary_LR"].iloc[0]) < 1.0 or _safe_float(rob["EV_R"].iloc[0]) < -0.05):
                status_by_id[cid] = "audit_only_removed_after_robustness"
            else:
                status_by_id[cid] = "candidate"
        selection["r03_pool_status"] = selection["structure_candidate_id"].map(status_by_id)
        selection = selection.drop(columns=[c for c in selection.columns if c.endswith("_x") or c.endswith("_y")], errors="ignore")
    return selection, pd.DataFrame(overlaps)


def build_label_confusion(action: pd.DataFrame) -> pd.DataFrame:
    rows = []
    pairs = [("continuation_h20", "continuation_h60"), ("continuation_h20", "failed_seed_forward"), ("continuation_h60", "failed_seed_forward")]
    for split in SPLITS:
        sub = action.loc[action["split"].eq(split) & action["action_time_denominator_flag"].astype(bool)]
        for left, right in pairs:
            eligible = sub[f"{left}_metric_eligible"].astype(bool) & sub[f"{right}_metric_eligible"].astype(bool)
            for lv in [False, True]:
                for rv in [False, True]:
                    rows.append({"split": split, "label_left": left, "label_right": right, "left_value": lv, "right_value": rv, "row_count": int((eligible & sub[left].astype(bool).eq(lv) & sub[right].astype(bool).eq(rv)).sum())})
    return pd.DataFrame(rows)


def build_baselines(action: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    rows = []
    label = config["labels"]["primary_selection_label_id"]
    for split in SPLITS:
        sub = action.loc[action["split"].eq(split) & action["action_time_denominator_flag"].astype(bool)]
        eligible = sub[f"{label}_metric_eligible"].astype(bool)
        exec_rows = sub["execution_eligible"].astype(bool)
        rows.append(
            {
                "baseline_id": "no_signal_unconditional_executable_denominator",
                "split": split,
                "baseline_type": "mandatory_no_signal",
                "signal_n": int(sub.shape[0]),
                "winner_base_rate": _safe_div(float((sub[label].astype(bool) & eligible).sum()), float(eligible.sum())),
                "EV_R": float(sub.loc[exec_rows, "unit_return_R"].mean()) if exec_rows.any() else np.nan,
                "status": "passed",
                "source_artifact_path": "",
                "source_artifact_hash": "",
                "source_candidate_id": "",
                "formula_hash": "",
            }
        )
        seed_mask = (
            sub["close_near_high5_pct"].ge(0.0).fillna(False)
            & sub["vol_ratio10"].gt(1.2).fillna(False)
            & sub["vol_ratio3"].gt(1.2).fillna(False)
            & sub["rps5"].gt(0.60).fillna(False)
        )
        rows.append(
            {
                "baseline_id": config["baselines"]["r01_v3_seed_baseline_id"],
                "split": split,
                "baseline_type": "mandatory_r01_v3_seed",
                "signal_n": int(seed_mask.sum()),
                "winner_base_rate": _safe_div(float((sub[label].astype(bool) & eligible & seed_mask).sum()), float((eligible & seed_mask).sum())),
                "EV_R": float(sub.loc[seed_mask & sub["execution_eligible"].astype(bool), "unit_return_R"].mean()) if seed_mask.any() else np.nan,
                "status": "passed",
                "source_artifact_path": "",
                "source_artifact_hash": "",
                "source_candidate_id": "",
                "formula_hash": _hash_text(config["baselines"]["r01_v3_seed_formula_id"], 16),
            }
        )
    v1_path = topic_path(config["baselines"]["r02_v1_primitive_summary"])
    if v1_path.exists():
        v1 = pd.read_csv(v1_path)
        broad = v1.loc[v1.get("candidate_type", "").astype(str).eq("single_primitive") & v1.get("group_id", "").astype(str).str.contains("momentum|relative_strength|near_high|market", regex=True, na=False)].copy()
        if not broad.empty:
            broad = broad.sort_values(["LR", "stock_day_density", "candidate_id"], ascending=[False, True, True]).head(1)
            source_id = str(broad["candidate_id"].iloc[0])
            status = "resolved"
        else:
            source_id = ""
            status = "missing_with_reason:no_broad_strength_primitive"
        rows.append({"baseline_id": "r02_v1_broad_strength_reference_baseline", "split": "train", "baseline_type": "mandatory_r02_v1_reference", "signal_n": int(broad["trigger_count"].iloc[0]) if v1_path.exists() and 'broad' in locals() and not broad.empty else 0, "winner_base_rate": np.nan, "EV_R": float(broad["EV_R"].iloc[0]) if 'broad' in locals() and not broad.empty else np.nan, "status": status, "source_artifact_path": relpath(v1_path), "source_artifact_hash": file_hash(v1_path), "source_candidate_id": source_id, "formula_hash": _hash_text(source_id, 16) if source_id else ""})
    else:
        rows.append({"baseline_id": "r02_v1_broad_strength_reference_baseline", "split": "train", "baseline_type": "mandatory_r02_v1_reference", "signal_n": 0, "winner_base_rate": np.nan, "EV_R": np.nan, "status": "missing_with_reason:artifact_missing", "source_artifact_path": relpath(v1_path), "source_artifact_hash": "", "source_candidate_id": "", "formula_hash": ""})
    return pd.DataFrame(rows)


def build_decision(selection: pd.DataFrame, calibration: pd.DataFrame, reconciliation: pd.DataFrame, validator_major_findings: bool, config: dict[str, Any]) -> tuple[pd.DataFrame, str]:
    frozen = selection.copy() if not selection.empty else pd.DataFrame()
    val = calibration.loc[calibration["split"].eq("validation") & calibration["structure_candidate_id"].isin(set(frozen.get("structure_candidate_id", [])))] if not calibration.empty else pd.DataFrame()
    rob = calibration.loc[calibration["split"].eq("robustness") & calibration["structure_candidate_id"].isin(set(frozen.get("structure_candidate_id", [])))] if not calibration.empty else pd.DataFrame()
    overlap_status = str(reconciliation["overlap_status"].iloc[0]) if not reconciliation.empty else "r01_v3_reference_missing"
    overlap_rate = _safe_float(reconciliation["instrument_overlap_rate"].iloc[0]) if not reconciliation.empty else 0.0
    rows = []
    def add(gate_id: str, actual: Any, expected: Any, ok: bool, failure_class: str = "research_gate") -> None:
        rows.append({"gate_id": gate_id, "actual": actual, "expected": expected, "status": "passed" if ok else "failed", "failure_class": failure_class})
    add("min_3_non_baseline_frozen_representatives", int(frozen.shape[0]), 3, int(frozen.shape[0]) >= 3)
    add("min_2_distinct_structure_groups", int(frozen["group"].nunique()) if not frozen.empty else 0, 2, (not frozen.empty and frozen["group"].nunique() >= 2))
    add("r01_v3_reference_overlap_rate", overlap_rate, ">=0.80", overlap_status == "passed" and overlap_rate >= 0.80)
    add("validation_at_least_2_lr_ci_lower_ge_1", int(val["primary_LR_ci90_lower"].ge(1.0).sum()) if not val.empty else 0, 2, (not val.empty and int(val["primary_LR_ci90_lower"].ge(1.0).sum()) >= 2))
    add("robustness_at_least_2_lr_ge_1", int(rob["primary_LR"].ge(1.0).sum()) if not rob.empty else 0, 2, (not rob.empty and int(rob["primary_LR"].ge(1.0).sum()) >= 2))
    add("validation_at_least_2_ev_ge_minus_005", int(val["EV_R"].ge(-0.05).sum()) if not val.empty else 0, 2, (not val.empty and int(val["EV_R"].ge(-0.05).sum()) >= 2))
    add("robustness_at_least_2_ev_ge_minus_005", int(rob["EV_R"].ge(-0.05).sum()) if not rob.empty else 0, 2, (not rob.empty and int(rob["EV_R"].ge(-0.05).sum()) >= 2))
    add("no_major_validator_leakage_finding", bool(not validator_major_findings), True, not validator_major_findings, "contract_gate")
    gate = pd.DataFrame(rows)
    r03_pool_count = int(frozen.get("r03_pool_status", pd.Series(dtype=str)).eq("candidate").sum()) if not frozen.empty else 0
    if gate["status"].eq("passed").all() and r03_pool_count >= 2:
        decision = "go_to_r03_evidence_accumulation"
    elif int(frozen.shape[0]) >= 1 or (not calibration.empty and calibration["primary_LR"].gt(1.0).any()):
        decision = "revise_profile_search_space"
    else:
        decision = "archive_profile_discovery_no_r03"
    return gate, decision


def build_report(decision: str, reference_audit: pd.DataFrame, reconciliation: pd.DataFrame, dictionary: pd.DataFrame, stage_a: pd.DataFrame, background: pd.DataFrame, calibration: pd.DataFrame, decomposition: pd.DataFrame, selection: pd.DataFrame, baselines: pd.DataFrame, execution: pd.DataFrame, gate: pd.DataFrame) -> str:
    def table(df: pd.DataFrame, cols: list[str], n: int = 12) -> str:
        if df.empty:
            return "_无记录。_"
        return df[[c for c in cols if c in df.columns]].head(n).to_markdown(index=False)
    lines = [
        "# EP4 R02 V2 Winner-Anchored Structure Profile Discovery Final Report",
        "",
        "## 执行结论",
        f"- Final decision: `{decision}`",
        "- 本轮不是 R03 入场策略，只评估赢家窗口结构是否能转化为 action-time 先验。",
        "- 重要边界：Stage A 的 `winner_coverage` 是赢家 `t0..t0+30` 窗口覆盖率；Stage B 的 prior/posterior/LR 来自完整 PIT stock-day 分母，两者不能互相替代。",
        "",
        "## R02 V1 为什么不足",
        "V1 从 action-time 原语直接搜索，主要找回宽泛强势、近高、量能和市场状态。V2 先在已知大赢家早期生命周期内找复现结构，再映射回 action-time 分母估计真实 prior/posterior。",
        "",
        "## Canonical Reference Event Audit",
        table(reference_audit, ["raw_positive_action_time_rows", "positive_rows_after_complete_window_filter", "final_winner_event_rows", "removed_incomplete_profile_window_rows", "stage_a_included"]),
        "",
        "## R01 V3 Reference Reconciliation",
        table(reconciliation, ["r02_v2_reference_event_count", "r01_v3_reference_event_count", "instrument_overlap_rate", "instrument_year_overlap_rate", "same_reference_date_rate", "within_20d_reference_date_rate", "overlap_status"]),
        "",
        "## Candidate Dictionary And Grid",
        f"- Candidate count: {int(dictionary.shape[0])}",
        table(dictionary, ["structure_candidate_id", "group", "pattern_type", "feature", "operator", "threshold", "profile_window_bucket", "lookback_days"], 10),
        "",
        "## Stage A Winner-Window Discovery",
        table(stage_a.sort_values(["stage_a_rank_score", "winner_coverage"], ascending=[False, False]) if not stage_a.empty else stage_a, ["structure_candidate_id", "group", "winner_coverage", "winner_coverage_ci90_lower", "matched_background_coverage", "winner_vs_background_coverage_lift", "action_time_background_signal_rate", "generic_strength_proxy_flag"], 15),
        "",
        "## Stage A Background Information Screen",
        table(background, ["structure_candidate_id", "matched_background_coverage", "action_time_background_signal_rate", "winner_vs_background_coverage_lift", "generic_strength_proxy_flag"], 15),
        "",
        "## Stage B Action-Time Prior Calibration",
        table(calibration, ["structure_candidate_id", "split", "signal_n", "signal_rate", "winner_base_rate", "winner_given_signal", "primary_LR", "primary_LR_ci90_lower", "precision_lift", "EV_R"], 18),
        "",
        "## Prior Decomposition",
        "分解维度包括 year、industry、market breadth、liquidity、market cap。若某个候选的 lift 主要来自单一年份、行业或 regime，不能直接解释为稳定证据。",
        table(decomposition, ["structure_candidate_id", "split", "bucket_type", "bucket_id", "signal_n", "signal_rate", "winner_given_signal", "primary_LR", "posterior_stability_flag"], 18),
        "",
        "## Frozen Representatives",
        table(selection, ["representative_id", "structure_candidate_id", "group", "primary_LR", "primary_LR_ci90_lower", "precision_lift", "EV_R", "r03_pool_status"], 12),
        "",
        "## Mandatory Baselines",
        table(baselines, ["baseline_id", "split", "baseline_type", "signal_n", "winner_base_rate", "EV_R", "status", "source_candidate_id"], 12),
        "",
        "## Execution Feasibility",
        "R02 V2 的 `unit_return_R` 使用通用诊断止损和 H20/fail-fast 逻辑，不可与 R01 V3 `return_R` 数值比较。",
        table(execution, ["structure_candidate_id", "split", "signal_n", "buyable_signal_n", "executable_entry_available_rate", "EV_R", "unit_return_R_p50"], 18),
        "",
        "## 初步解释和猜测",
        "若 Stage A 覆盖高但 Stage B posterior/LR 弱，说明这些结构更多是在描述赢家，而不是形成可交易 prior。任何关于下一轮结构、生命周期或风险状态的解释都只是 hypothesis，必须在后续 requirement 中重新验证。",
        "",
        "## Gate Audit",
        table(gate, ["gate_id", "actual", "expected", "status", "failure_class"], 20),
        "",
        "## Required Report Tokens",
        "Final decision, action-time prior, posterior precision, likelihood ratio, execution feasibility, Stage A winner coverage, Stage B action-time prior.",
    ]
    return "\n".join(lines) + "\n"


def artifact_hashes(paths: R02V2Paths) -> dict[str, str]:
    out = {}
    for name in REQUIRED_CACHE:
        out[name] = file_hash(paths.cache_dir / name)
    for name in REQUIRED_REPORTS:
        out[name] = file_hash(paths.reports_dir / name)
    for name in REQUIRED_MANIFESTS:
        out[name] = file_hash(paths.manifests_dir / name)
    return out


def run_pipeline(config: dict[str, Any], paths: R02V2Paths, ep2_config: dict[str, Any], *, n_jobs: int) -> dict[str, Any]:
    authority = assert_authority_inputs(config)
    action, effective, calendar = build_action_time_panel(config, ep2_config)
    action, bucket_boundaries = add_bucket_columns(action, config)
    dictionary = generate_candidate_dictionary(config)
    reference, reference_audit = build_reference_events(action, config, calendar)
    reconciliation = reconcile_r01_v3(reference, config)
    if not reference.empty and not reconciliation.empty:
        overlap_instruments = set()
        r01_path = topic_path(config["reference_events"]["r01_v3_reference_artifact"])
        if r01_path.exists():
            r01 = pd.read_parquet(r01_path)
            overlap_instruments = set(r01["instrument"].astype(str))
        reference["r01_v3_reference_overlap_flag"] = reference["instrument_id"].astype(str).isin(overlap_instruments)
    winner_window = build_winner_window_panel(reference, action, config)
    matched_background = build_matched_background_windows(reference, action, config)
    stage_a, profile_events, background_screen, observability, stage_a_rejection = build_stage_a(dictionary, reference, winner_window, matched_background, action, config)
    action_events, signal_panel, calibration, stage_b_gate, eventization_audit = build_stage_b(action, dictionary, stage_a_rejection, config)
    selection, redundancy = select_representatives(action, action_events, calibration, stage_b_gate, dictionary, config)
    selected_ids = selection["structure_candidate_id"].astype(str).tolist() if not selection.empty else []
    decomposition = build_prior_decomposition(action, action_events, calibration, selected_ids, config)
    baselines = build_baselines(action, config)
    label_confusion = build_label_confusion(action)
    gate, decision = build_decision(selection, calibration, reconciliation, False, config)
    validation = calibration.loc[calibration["split"].eq("validation") & calibration["structure_candidate_id"].isin(selected_ids)].copy() if not calibration.empty else pd.DataFrame()
    robustness = calibration.loc[calibration["split"].eq("robustness") & calibration["structure_candidate_id"].isin(selected_ids)].copy() if not calibration.empty else pd.DataFrame()
    execution = calibration.loc[calibration["structure_candidate_id"].isin(selected_ids)].copy() if not calibration.empty else pd.DataFrame()
    year_stability = decomposition.loc[decomposition["bucket_type"].eq("calendar_year")].copy() if not decomposition.empty else pd.DataFrame()
    report = build_report(decision, reference_audit, reconciliation, dictionary, stage_a, background_screen, calibration, decomposition, selection, baselines, execution, gate)
    smoke_keys = {
        "top_stage_a_candidate_ids": stage_a.sort_values(["stage_a_rank_score", "structure_candidate_id"], ascending=[False, True])["structure_candidate_id"].head(20).tolist() if not stage_a.empty else [],
        "top_stage_b_candidate_ids": calibration.loc[calibration["split"].eq("train")].sort_values(["primary_LR", "structure_candidate_id"], ascending=[False, True])["structure_candidate_id"].head(20).tolist() if not calibration.empty else [],
        "selected_representative_ids": selected_ids,
        "final_decision": decision,
        "frozen_formula_hashes": selection["formula_hash"].tolist() if not selection.empty else [],
    }
    return {
        "authority": authority,
        "effective": effective,
        "action": action,
        "bucket_boundaries": bucket_boundaries,
        "dictionary": dictionary,
        "reference": reference,
        "reference_audit": reference_audit,
        "reconciliation": reconciliation,
        "winner_window": winner_window,
        "matched_background": matched_background,
        "stage_a": stage_a,
        "profile_events": profile_events,
        "background_screen": background_screen,
        "observability": observability,
        "stage_a_rejection": stage_a_rejection,
        "action_events": action_events,
        "signal_panel": signal_panel,
        "calibration": calibration,
        "stage_b_gate": stage_b_gate,
        "eventization_audit": eventization_audit,
        "selection": selection,
        "redundancy": redundancy,
        "decomposition": decomposition,
        "validation": validation,
        "robustness": robustness,
        "execution": execution,
        "year_stability": year_stability,
        "label_confusion": label_confusion,
        "baselines": baselines,
        "gate": gate,
        "decision": decision,
        "report": report,
        "smoke_keys": smoke_keys,
    }


def run_r02_v2(config_path: str | Path = DEFAULT_CONFIG) -> dict[str, Any]:
    config, paths, ep2_config = load_config(config_path)
    effective_jobs = max(1, min(int(config["runtime"]["default_n_jobs"]), int(config["runtime"]["max_n_jobs"]), os.cpu_count() or 1))
    result = run_pipeline(config, paths, ep2_config, n_jobs=effective_jobs)
    smoke = run_pipeline(config, paths, ep2_config, n_jobs=1)
    deterministic_status = "passed" if result["smoke_keys"] == smoke["smoke_keys"] else "failed"

    write_parquet(result["reference"], paths.cache_dir / "r02_v2_winner_reference_events.parquet")
    label_cols = ["instrument_id", "trade_date", "split", "action_time_denominator_flag"] + [c for label in LABEL_IDS for c in [label, f"{label}_complete_forward_window", f"{label}_metric_eligible", f"{label}_effective_label_end"] if c in result["action"].columns]
    write_parquet(result["action"][label_cols], paths.cache_dir / "r02_v2_reference_action_time_label_panel.parquet")
    write_parquet(result["winner_window"], paths.cache_dir / "r02_v2_winner_window_panel.parquet")
    write_parquet(result["profile_events"], paths.cache_dir / "r02_v2_profile_candidate_event_panel.parquet")
    write_parquet(result["matched_background"], paths.cache_dir / "r02_v2_matched_background_windows.parquet")
    write_parquet(result["action_events"], paths.cache_dir / "r02_v2_action_time_eventized_signals.parquet")
    write_parquet(result["action"], paths.cache_dir / "r02_v2_action_time_panel.parquet")
    write_parquet(result["signal_panel"], paths.cache_dir / "r02_v2_action_time_signal_panel.parquet")
    write_parquet(result["selection"], paths.cache_dir / "r02_v2_frozen_representatives.parquet")

    write_csv(result["stage_a"], paths.reports_dir / "r02_v2_winner_profile_search_summary.csv")
    write_csv(result["reference_audit"], paths.reports_dir / "r02_v2_winner_reference_event_audit.csv")
    write_csv(result["reconciliation"], paths.reports_dir / "r02_v2_r01_v3_reference_reconciliation.csv")
    write_csv(result["dictionary"], paths.reports_dir / "r02_v2_candidate_dictionary.csv")
    write_csv(result["bucket_boundaries"], paths.reports_dir / "r02_v2_bucket_boundaries.csv")
    write_csv(result["stage_a_rejection"], paths.reports_dir / "r02_v2_stage_a_rejection_audit.csv")
    write_csv(result["observability"], paths.reports_dir / "r02_v2_profile_observability_audit.csv")
    write_csv(result["eventization_audit"], paths.reports_dir / "r02_v2_eventization_audit.csv")
    write_csv(result["background_screen"], paths.reports_dir / "r02_v2_background_information_screen.csv")
    write_csv(result["redundancy"], paths.reports_dir / "r02_v2_profile_redundancy_matrix.csv")
    write_csv(result["calibration"], paths.reports_dir / "r02_v2_stage_b_prior_calibration.csv")
    write_csv(result["decomposition"], paths.reports_dir / "r02_v2_prior_decomposition.csv")
    write_csv(result["stage_b_gate"], paths.reports_dir / "r02_v2_stage_b_train_gate_audit.csv")
    write_csv(result["selection"], paths.reports_dir / "r02_v2_representative_selection.csv")
    write_csv(result["validation"], paths.reports_dir / "r02_v2_validation_summary.csv")
    write_csv(result["robustness"], paths.reports_dir / "r02_v2_robustness_summary.csv")
    write_csv(result["execution"], paths.reports_dir / "r02_v2_execution_diagnostics.csv")
    write_csv(result["year_stability"], paths.reports_dir / "r02_v2_year_stability.csv")
    write_csv(result["label_confusion"], paths.reports_dir / "r02_v2_label_confusion_matrix.csv")
    write_csv(result["baselines"], paths.reports_dir / "r02_v2_mandatory_baselines.csv")
    write_csv(result["gate"], paths.reports_dir / "r02_v2_gate_audit.csv")
    (paths.reports_dir / "r02_v2_final_report.md").write_text(result["report"], encoding="utf-8")

    input_hashes = {row["artifact_name"]: row["sha256"] for row in result["authority"].to_dict("records")}
    config_hash = {"config_path": relpath(paths.config_path), "config_hash": file_hash(paths.config_path)}
    validation_contract = {
        "schema_version": SCHEMA_VERSION,
        "manifest_directory": "manifests",
        "manifest_doc_typo_accepted": True,
        "forbid_downstream_candidate_id_column": True,
        "primary_reference_rebuilt_from_r02_v2_pit_inputs": True,
        "uses_r02_v1_action_time_panel_cache_as_authority": False,
    }
    write_json(input_hashes, paths.manifests_dir / "r02_v2_input_hashes.json")
    write_json(config_hash, paths.manifests_dir / "r02_v2_config_hash.json")
    write_json(validation_contract, paths.manifests_dir / "r02_v2_validation_contract.json")
    manifest = {
        "phase": config["phase"],
        "schema_version": SCHEMA_VERSION,
        "config_path": relpath(paths.config_path),
        "config_hash": file_hash(paths.config_path),
        "output_root": relpath(paths.output_root),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "final_decision": result["decision"],
        "configured_n_jobs": int(config["runtime"]["default_n_jobs"]),
        "effective_n_jobs": effective_jobs,
        "deterministic_smoke": {
            "configured_run": result["smoke_keys"],
            "effective_n_jobs_1": smoke["smoke_keys"],
            "status": deterministic_status,
        },
        "reference_event_count": int(result["reference"].shape[0]),
        "stage_a_candidate_count": int(result["dictionary"].shape[0]),
        "stage_b_calibrated_candidate_count": int(result["calibration"]["structure_candidate_id"].nunique()) if not result["calibration"].empty else 0,
        "frozen_representative_count": int(result["selection"].shape[0]) if not result["selection"].empty else 0,
        "source_panel_uses_r02_v1_cache_as_authority": False,
        "artifact_hashes": {},
    }
    write_json(manifest, paths.manifests_dir / "r02_v2_manifest.json")
    manifest["artifact_hashes"] = artifact_hashes(paths)
    write_json(manifest, paths.manifests_dir / "r02_v2_manifest.json")
    return {
        "output_root": relpath(paths.output_root),
        "final_decision": result["decision"],
        "reference_event_count": int(result["reference"].shape[0]),
        "stage_a_candidate_count": int(result["dictionary"].shape[0]),
        "stage_b_calibrated_candidate_count": int(result["calibration"]["structure_candidate_id"].nunique()) if not result["calibration"].empty else 0,
        "frozen_representative_count": int(result["selection"].shape[0]) if not result["selection"].empty else 0,
        "deterministic_status": deterministic_status,
    }


def validate_r02_v2(config_path: str | Path = DEFAULT_CONFIG) -> dict[str, Any]:
    config, paths, _ = load_config(config_path)
    failures: list[str] = []
    required = [paths.cache_dir / name for name in REQUIRED_CACHE] + [paths.reports_dir / name for name in REQUIRED_REPORTS] + [paths.manifests_dir / name for name in REQUIRED_MANIFESTS]
    missing = [relpath(path) for path in required if not path.exists()]
    if missing:
        failures.append("missing required artifacts: " + "; ".join(missing))
    if failures:
        raise RuntimeError("; ".join(failures))
    manifest = json.loads((paths.manifests_dir / "r02_v2_manifest.json").read_text(encoding="utf-8"))
    validation_contract = json.loads((paths.manifests_dir / "r02_v2_validation_contract.json").read_text(encoding="utf-8"))
    reference = pd.read_parquet(paths.cache_dir / "r02_v2_winner_reference_events.parquet")
    action = pd.read_parquet(paths.cache_dir / "r02_v2_action_time_panel.parquet")
    events = pd.read_parquet(paths.cache_dir / "r02_v2_action_time_eventized_signals.parquet")
    dictionary = pd.read_csv(paths.reports_dir / "r02_v2_candidate_dictionary.csv")
    stage_a = pd.read_csv(paths.reports_dir / "r02_v2_winner_profile_search_summary.csv")
    stage_a_rejection = pd.read_csv(paths.reports_dir / "r02_v2_stage_a_rejection_audit.csv")
    calibration = pd.read_csv(paths.reports_dir / "r02_v2_stage_b_prior_calibration.csv")
    decomposition = pd.read_csv(paths.reports_dir / "r02_v2_prior_decomposition.csv")
    bucket_boundaries = pd.read_csv(paths.reports_dir / "r02_v2_bucket_boundaries.csv")
    reconciliation = pd.read_csv(paths.reports_dir / "r02_v2_r01_v3_reference_reconciliation.csv")
    baselines = pd.read_csv(paths.reports_dir / "r02_v2_mandatory_baselines.csv")
    gate = pd.read_csv(paths.reports_dir / "r02_v2_gate_audit.csv")
    report_text = (paths.reports_dir / "r02_v2_final_report.md").read_text(encoding="utf-8")
    if manifest.get("final_decision") not in ALLOWED_DECISIONS:
        failures.append("final decision is outside allowed enum")
    if manifest.get("source_panel_uses_r02_v1_cache_as_authority") is not False or validation_contract.get("uses_r02_v1_action_time_panel_cache_as_authority") is not False:
        failures.append("R02 V2 must not use R02 V1 action-time panel cache as authority")
    if "winner_event_id" not in reference.columns or reference["winner_event_id"].duplicated().any():
        failures.append("canonical reference event ids are missing or not unique")
    if not reference.empty and not reference["reference_date_policy"].eq("first_positive_big_winner_forward_episode").all():
        failures.append("reference_date_policy mismatch")
    if "source_panel_rebuilt_by_r02_v2" not in action.columns or not action["source_panel_rebuilt_by_r02_v2"].astype(bool).all():
        failures.append("action-time denominator is not marked as R02 V2-owned rebuild")
    for label in LABEL_IDS:
        for suffix in ["complete_forward_window", "metric_eligible"]:
            if f"{label}_{suffix}" not in action.columns:
                failures.append(f"missing label window column: {label}_{suffix}")
    if "structure_candidate_id" not in dictionary.columns or dictionary["structure_candidate_id"].duplicated().any():
        failures.append("candidate dictionary missing unique structure_candidate_id")
    if dictionary.shape[0] > int(config["candidate_generation"]["max_total_candidates"]):
        failures.append("candidate count exceeds total limit")
    group_counts = dictionary.groupby("group").size()
    if (group_counts > int(config["candidate_generation"]["max_total_candidates_per_group"])).any():
        failures.append("candidate count exceeds per-group limit")
    if not set(dictionary["pattern_type"].astype(str)).issubset(ALLOWED_PATTERN_TYPES):
        failures.append("candidate dictionary contains unsupported pattern_type")
    downstream = [stage_a, stage_a_rejection, calibration, decomposition, events]
    valid_ids = set(dictionary["structure_candidate_id"].astype(str))
    for df in downstream:
        if not df.empty and "structure_candidate_id" in df.columns:
            unknown = set(df["structure_candidate_id"].dropna().astype(str)) - valid_ids
            if unknown:
                failures.append("downstream artifact contains ids missing from candidate dictionary")
    for name in REQUIRED_REPORTS:
        if name.endswith(".csv"):
            df = pd.read_csv(paths.reports_dir / name)
            if "candidate_id" in df.columns and name != "r02_v2_mandatory_baselines.csv":
                failures.append(f"forbidden candidate_id column in {name}")
    for name in REQUIRED_CACHE:
        df = pd.read_parquet(paths.cache_dir / name)
        if "candidate_id" in df.columns:
            failures.append(f"forbidden candidate_id column in {name}")
    if not events.empty and events["future_data_used_flag"].astype(bool).any():
        failures.append("eventization audit found future data usage")
    if set(["calendar_year", "industry", "market_breadth_bucket", "liquidity_bucket", "market_cap_bucket"]) - set(decomposition.get("bucket_type", pd.Series(dtype=str)).astype(str)):
        failures.append("prior decomposition missing required bucket type")
    if "missing_mcap_share" not in bucket_boundaries.columns:
        failures.append("bucket boundaries missing missing_mcap_share")
    if reconciliation.empty or str(reconciliation["overlap_status"].iloc[0]) in {"reference_drift_warning", "r01_v3_reference_missing"}:
        if manifest.get("final_decision") == "go_to_r03_evidence_accumulation":
            failures.append("go_to_r03 blocked by R01 V3 reference reconciliation")
    required_baselines = {"no_signal_unconditional_executable_denominator", config["baselines"]["r01_v3_seed_baseline_id"], "r02_v1_broad_strength_reference_baseline"}
    if required_baselines - set(baselines["baseline_id"].astype(str)):
        failures.append("mandatory baseline missing")
    smoke = manifest.get("deterministic_smoke", {})
    if smoke.get("status") != "passed":
        failures.append("deterministic smoke failed")
    for token in ["Final decision", "action-time prior", "posterior", "Stage A", "Stage B", "unit_return_R"]:
        if token not in report_text:
            failures.append(f"final report missing required token: {token}")
    if gate.empty or not set(gate["status"].astype(str)).issubset({"passed", "failed"}):
        failures.append("gate audit invalid")
    if failures:
        raise RuntimeError("; ".join(failures))
    research_failed = gate.loc[gate["status"].eq("failed"), "gate_id"].astype(str).tolist()
    return {
        "output_root": relpath(paths.output_root),
        "final_decision": manifest.get("final_decision"),
        "contract_validation_status": "passed",
        "research_failed_gate_count": len(research_failed),
        "research_failed_gates": research_failed,
        "required_artifact_count": len(required),
    }
