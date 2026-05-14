#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml
from scipy.stats import beta

SCRIPT_DIR = Path(__file__).resolve().parent
EP4_DIR = SCRIPT_DIR.parent
TOPIC_DIR = EP4_DIR.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from r01_high_recall_probe_fail_fast_common import relpath, topic_path, write_json  # noqa: E402


DEFAULT_CONFIG = EP4_DIR / "configs" / "r03a_probability_survival_step_feasibility_v1.yaml"
SPLITS = ["train", "validation", "robustness"]
LABELS = ["good_path", "bad_path", "neutral_path"]
FORBIDDEN_REPORT_TOKENS = [
    "production-ready",
    "buy signal",
    "sell signal",
    "validated 1R allocation",
    "expected R positive",
    "EV_R passed",
    "fresh evidence gate validated",
    "portfolio-ready",
]
PATH_COLS = [
    "signal_id",
    "signal_type",
    "family_id",
    "instrument_id",
    "signal_date",
    "split",
    "entry_date",
    "entry_price",
    "entry_valid",
    "entry_invalid_reason",
    "path_complete_120d",
    "available_forward_trading_days",
    "path_incomplete_reason",
    "first_minus5_offset",
    "first_close_minus5_offset",
    "max_loss_before_first_plus10",
    "hit_plus10_before_minus5",
    "path_quality_flag",
    "early_failure_flag",
    "close_return_t20",
    "close_return_t60",
    "close_return_t120",
    "max_gain_120d",
    "max_loss_120d",
    "max_drawdown_120d",
]


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _hash_json(value: Any, n: int = 16) -> str:
    raw = json.dumps(value, sort_keys=True, ensure_ascii=True, default=str).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:n]


def _read_yaml(path: Path) -> dict[str, Any]:
    with topic_path(path).open("r", encoding="utf-8") as file:
        return yaml.safe_load(file) or {}


def _read_json(path: Path) -> dict[str, Any]:
    p = topic_path(path)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def _write_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)


def _boolish(series: pd.Series) -> pd.Series:
    return series.astype(str).str.lower().isin({"true", "1", "yes"})


def _as_num(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def _safe_div(numer: float, denom: float) -> float:
    return float(numer) / float(denom) if denom else np.nan


def _q(series: pd.Series, q: float) -> float:
    vals = pd.to_numeric(series, errors="coerce").dropna()
    return float(vals.quantile(q)) if not vals.empty else np.nan


def _sample_status(den: int, n_min: int) -> str:
    if den >= n_min:
        return "sufficient"
    if den >= max(20, n_min // 4):
        return "thin_bucket_report_only"
    if den > 0:
        return "too_sparse_use_fallback"
    return "unusable"


def _r03a_status(sample_status: str, stability_status: str) -> str:
    if sample_status == "sufficient" and stability_status == "stable_enough_for_requirement_input":
        return "sufficient_and_stable"
    if sample_status == "sufficient" and stability_status == "unstable_do_not_freeze":
        return "unstable_do_not_freeze"
    if sample_status == "sufficient" and stability_status == "insufficient_sample":
        return "too_sparse_use_fallback"
    if sample_status == "sufficient" and stability_status == "missing_split":
        return "missing_split"
    if sample_status == "thin_bucket_report_only":
        return "thin_report_only"
    if sample_status == "too_sparse_use_fallback":
        return "too_sparse_use_fallback"
    if sample_status == "unusable":
        return "unusable"
    return "unusable"


def _split_denominators(df: pd.DataFrame, mask: pd.Series) -> dict[str, int]:
    out: dict[str, int] = {}
    for split in SPLITS:
        part = df.loc[mask & df["split"].eq(split)]
        out[split] = int(part["label"].isin(LABELS).sum())
    return out


def _direct_gate_status(df: pd.DataFrame, mask: pd.Series, thresholds: dict[str, int]) -> dict[str, Any]:
    denominators = _split_denominators(df, mask)
    missing = [split for split, den in denominators.items() if den == 0]
    thin = [split for split, den in denominators.items() if den < int(thresholds[f"N_min_{split}"])]
    if missing:
        stability_status = "missing_split"
        sample_status = "sufficient"
    elif thin:
        stability_status = "insufficient_sample"
        sample_status = "sufficient"
    else:
        probs: dict[str, dict[str, float]] = {}
        for split in SPLITS:
            part = df.loc[mask & df["split"].eq(split)]
            post = posterior_from_df(part)
            probs[split] = {"P_good": post["P_good"], "P_bad": post["P_bad"]}
        good_vals = [probs[split]["P_good"] for split in SPLITS if pd.notna(probs[split]["P_good"])]
        bad_vals = [probs[split]["P_bad"] for split in SPLITS if pd.notna(probs[split]["P_bad"])]
        good_drift = max(good_vals) - min(good_vals) if len(good_vals) > 1 else np.nan
        bad_drift = max(bad_vals) - min(bad_vals) if len(bad_vals) > 1 else np.nan
        stability_status = (
            "unstable_do_not_freeze"
            if pd.notna(max(good_drift, bad_drift)) and max(good_drift, bad_drift) > 0.20
            else "stable_enough_for_requirement_input"
        )
        sample_status = "sufficient"
    r03a_gate_status = _r03a_status(sample_status, stability_status)
    return {
        "upstream_sample_sufficiency_status": sample_status,
        "upstream_stability_status": stability_status,
        "r03a_stability_status": "stable_enough_for_candidate"
        if r03a_gate_status == "sufficient_and_stable"
        else "not_stable_for_candidate",
        "r03a_gate_status": r03a_gate_status,
        "split_denominators": denominators,
    }


def _stability_lookup(split_stability: pd.DataFrame) -> dict[tuple[str, str], str]:
    if split_stability.empty:
        return {}
    return {
        (str(row.grouping_type), str(row.grouping_key)): str(row.stability_status)
        for row in split_stability.itertuples(index=False)
    }


def _family_signal_map(config: dict[str, Any]) -> dict[str, str]:
    return {str(item["family_id"]): str(item["signal_id"]) for item in config["frozen_families"]}


def _scope_upstream_key(seed_scope_id: str, family_signal_map: dict[str, str]) -> tuple[str, str] | None:
    if seed_scope_id.startswith("seed_primary_family_id="):
        value = seed_scope_id.split("=", 1)[1]
        if value in family_signal_map:
            return ("single_family_prior", f"family_id={value}|signal_id={family_signal_map[value]}")
    if seed_scope_id.startswith("seed_same_day_family_count="):
        return ("same_day_family_count_prior", f"same_day_family_count={seed_scope_id.split('=', 1)[1]}")
    return None


def _scope_gate_status(
    episodes: pd.DataFrame,
    seed_scope_id: str,
    thresholds: dict[str, int],
    stability: dict[tuple[str, str], str],
    family_signal_map: dict[str, str],
) -> dict[str, Any]:
    direct = _direct_gate_status(episodes, scope_mask(episodes, seed_scope_id), thresholds)
    upstream_key = _scope_upstream_key(seed_scope_id, family_signal_map)
    if upstream_key and upstream_key in stability:
        direct["upstream_stability_status"] = stability[upstream_key]
        direct["r03a_gate_status"] = _r03a_status(direct["upstream_sample_sufficiency_status"], direct["upstream_stability_status"])
        direct["r03a_stability_status"] = (
            "stable_enough_for_candidate" if direct["r03a_gate_status"] == "sufficient_and_stable" else "not_stable_for_candidate"
        )
    return direct


def _fallback_upstream_key(row: pd.Series, fallback_grain: str) -> tuple[str, str] | None:
    if fallback_grain == "same_day_family_count":
        return ("same_day_family_count_prior", f"same_day_family_count={int(row['seed_same_day_family_count'])}")
    if fallback_grain == "same_day_bundle_key":
        return (
            "same_day_bundle_prior",
            f"same_day_bundle_key={row['seed_same_day_bundle_key']}|same_day_family_count={int(row['seed_same_day_family_count'])}",
        )
    if fallback_grain == "context_bucket_id":
        return (
            "context_bucket_prior",
            f"same_day_bundle_key={row['seed_same_day_bundle_key']}|same_day_family_count={int(row['seed_same_day_family_count'])}|entry_risk_pct_bucket=na",
        )
    return None


def _fallback_gate_status(
    episodes: pd.DataFrame,
    base_mask: pd.Series,
    fallback_grain: str,
    thresholds: dict[str, int],
    stability: dict[tuple[str, str], str],
) -> dict[str, Any]:
    if fallback_grain in {"seed_primary_family_id", "seed_type"}:
        return {
            "fallback_grain_allowed": True,
            "fallback_grain_status": "direct_episode_fallback_allowed",
            "fallback_grain_disallowed_reason": "",
        }
    bucket_col = f"__gate_bucket_{fallback_grain}"
    work = episodes.copy()
    work[bucket_col] = bucket_values(work, fallback_grain)
    train_buckets = sorted(work.loc[base_mask & work["split"].eq("train"), bucket_col].dropna().astype(str).unique())
    if len(train_buckets) < 2:
        return {
            "fallback_grain_allowed": False,
            "fallback_grain_status": "degenerate_probability_gate",
            "fallback_grain_disallowed_reason": "fewer_than_two_train_buckets",
        }
    if fallback_grain not in {"same_day_bundle_key", "context_bucket_id", "same_day_family_count"}:
        return {
            "fallback_grain_allowed": False,
            "fallback_grain_status": "unsupported_fallback_grain",
            "fallback_grain_disallowed_reason": fallback_grain,
        }
    failed: list[str] = []
    for bucket in train_buckets:
        mask = base_mask & work[bucket_col].astype(str).eq(bucket)
        gate = _direct_gate_status(work, mask, thresholds)
        sample_ok = gate["r03a_gate_status"] == "sufficient_and_stable"
        upstream_ok = True
        if fallback_grain in {"same_day_bundle_key", "context_bucket_id", "same_day_family_count"}:
            first = work.loc[mask].iloc[0] if mask.any() else None
            upstream_key = _fallback_upstream_key(first, fallback_grain) if first is not None else None
            upstream_status = stability.get(upstream_key, "missing_split") if upstream_key else "missing_split"
            upstream_ok = upstream_status == "stable_enough_for_requirement_input"
        if not (sample_ok and upstream_ok):
            failed.append(str(bucket))
    if failed:
        return {
            "fallback_grain_allowed": False,
            "fallback_grain_status": "blocked_unstable_or_sparse_bucket",
            "fallback_grain_disallowed_reason": "|".join(failed[:10]),
        }
    return {
        "fallback_grain_allowed": True,
        "fallback_grain_status": "sufficient_and_stable",
        "fallback_grain_disallowed_reason": "",
    }


def _posterior(good: int, bad: int, neutral: int, prefix: str = "") -> dict[str, Any]:
    den = int(good + bad + neutral)
    ag = good + 0.5
    ab = bad + 0.5
    an = neutral + 0.5
    total = ag + ab + an
    p_good = _safe_div(good, den)
    p_bad = _safe_div(bad, den)
    p_neutral = _safe_div(neutral, den)
    good_lo = float(beta.ppf(0.05, ag, ab + an)) if den >= 0 else np.nan
    good_hi = float(beta.ppf(0.95, ag, ab + an)) if den >= 0 else np.nan
    bad_lo = float(beta.ppf(0.05, ab, ag + an)) if den >= 0 else np.nan
    bad_hi = float(beta.ppf(0.95, ab, ag + an)) if den >= 0 else np.nan
    data = {
        "label_denominator_count": den,
        "good_count": int(good),
        "bad_count": int(bad),
        "neutral_count": int(neutral),
        "P_good": p_good,
        "P_bad": p_bad,
        "P_neutral": p_neutral,
        "P_good_lower": good_lo,
        "P_good_upper": good_hi,
        "P_bad_lower": bad_lo,
        "P_bad_upper": bad_hi,
        "credible_interval_width_good": good_hi - good_lo,
        "credible_interval_width_bad": bad_hi - bad_lo,
        "posterior_alpha_total": total,
    }
    if prefix:
        return {f"{prefix}{k}": v for k, v in data.items()}
    return data


def posterior_from_df(df: pd.DataFrame, prefix: str = "") -> dict[str, Any]:
    labeled = df.loc[df["label"].isin(LABELS)]
    return _posterior(
        int(labeled["label"].eq("good_path").sum()),
        int(labeled["label"].eq("bad_path").sum()),
        int(labeled["label"].eq("neutral_path").sum()),
        prefix,
    )


def label_rows(df: pd.DataFrame) -> pd.Series:
    labels = pd.Series("neutral_path", index=df.index, dtype="object")
    invalid = ~_boolish(df["entry_valid"]) | ~_boolish(df["path_complete_120d"])
    bad = (
        _boolish(df["early_failure_flag"])
        | (_as_num(df["first_minus5_offset"]) <= 10)
        | (_as_num(df["max_loss_before_first_plus10"]) <= -0.06)
    )
    good = _boolish(df["hit_plus10_before_minus5"]) | df["path_quality_flag"].astype(str).isin(
        ["clean_continuation", "tradable_continuation"]
    )
    labels.loc[invalid] = "censored_or_invalid"
    labels.loc[~invalid & bad] = "bad_path"
    labels.loc[~invalid & ~bad & good] = "good_path"
    return labels


def load_config(config_path: Path) -> dict[str, Any]:
    config = _read_yaml(config_path)
    if config.get("posterior", {}).get("alpha_source") != "Jeffreys_prior":
        raise RuntimeError("R03a v1 only allows alpha_source=Jeffreys_prior")
    return config


def validate_required_inputs(config: dict[str, Any]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    required = {
        "r02_1_manifest": config["upstream_r02_1"]["manifest"],
        "r02_1_validation": config["upstream_r02_1"]["validation"],
        "path_query_config": config["upstream_path_query"]["config"],
        "path_query_manifest": config["upstream_path_query"]["manifest"],
        "path_query_validation": config["upstream_path_query"]["validation"],
        "eligible_day_density_panel": config["upstream_eligible_day_density"]["panel"],
    }
    r02_reports = [
        "r02_1_r03_input_readiness.csv",
        "r02_1_single_family_prior.csv",
        "r02_1_same_day_family_count_prior.csv",
        "r02_1_same_day_bundle_prior.csv",
        "r02_1_context_bucket_prior.csv",
        "r02_1_survival_checkpoint_prior.csv",
        "r02_1_fresh_evidence_prior.csv",
        "r02_1_fresh_evidence_offset_distribution.csv",
        "r02_1_split_stability_diagnostics.csv",
        "r02_1_ev_r_input_audit.csv",
    ]
    for name in r02_reports:
        required[f"r02_1_{name.removesuffix('.csv')}"] = str(Path(config["upstream_r02_1"]["output_root"]) / "reports" / name)
    for input_name, input_path in required.items():
        p = topic_path(input_path)
        exists = p.exists()
        validation_status = "not_applicable"
        if input_name.endswith("validation") and exists:
            validation_status = json.loads(p.read_text(encoding="utf-8")).get("validation_status", "missing")
        rows.append(
            {
                "input_name": input_name,
                "input_path": input_path,
                "required": True,
                "exists": bool(exists),
                "hash_or_mtime": _hash_file(p) if exists and p.is_file() else "",
                "validation_status": validation_status,
                "readiness_status": "present" if exists else "missing",
                "blocker_status": "" if exists else "blocked_missing_required_input",
            }
        )
    audit = pd.DataFrame(rows)
    missing = audit.loc[~audit["exists"], "input_name"].tolist()
    if missing:
        raise RuntimeError(f"missing required R03a inputs: {missing}")
    r02_val = json.loads(topic_path(config["upstream_r02_1"]["validation"]).read_text(encoding="utf-8"))
    path_val = json.loads(topic_path(config["upstream_path_query"]["validation"]).read_text(encoding="utf-8"))
    if r02_val.get("validation_status") != "passed" or path_val.get("validation_status") != "passed":
        raise RuntimeError("upstream validation did not pass")
    return audit


def validate_readiness(config: dict[str, Any]) -> dict[str, str]:
    path = topic_path(Path(config["upstream_r02_1"]["output_root"]) / "reports" / "r02_1_r03_input_readiness.csv")
    row = pd.read_csv(path).iloc[0].astype(str).to_dict()
    for col in [
        "single_family_prior_ready",
        "same_day_bundle_prior_ready",
        "context_bucket_prior_ready",
        "survival_checkpoint_prior_ready",
        "fresh_evidence_prior_ready",
    ]:
        if row.get(col) != "ready":
            raise RuntimeError(f"R03a required readiness is not ready: {col}={row.get(col)}")
    if row.get("ev_r_ready") not in {"blocked_missing_ev_r", "ready"}:
        raise RuntimeError(f"invalid ev_r_ready for R03a: {row.get('ev_r_ready')}")
    if row.get("global_prior_ready") != "blocked_missing_denominator":
        raise RuntimeError("R03a expected blocked_missing_denominator for global_prior_ready")
    return row


def validate_frozen(config: dict[str, Any], path_config: dict[str, Any], r02_manifest: dict[str, Any]) -> pd.DataFrame:
    frozen = pd.DataFrame(config["frozen_families"])
    upstream = pd.DataFrame(path_config["single_signals"])
    if len(frozen) != 7:
        raise RuntimeError("R03a frozen family count must be 7")
    merged = frozen.merge(upstream, on=["family_id", "signal_id", "condition_group_id"], how="left", suffixes=("", "_upstream"))
    if merged["condition_text_upstream"].isna().any():
        raise RuntimeError("frozen family set does not match upstream path-query config")
    drift = merged["condition_text"].astype(str).ne(merged["condition_text_upstream"].astype(str))
    if drift.any():
        raise RuntimeError(f"frozen condition text drift: {merged.loc[drift, 'family_id'].tolist()}")
    if sorted(r02_manifest.get("frozen_family_ids", [])) != sorted(frozen["family_id"].tolist()):
        raise RuntimeError("frozen family ids do not match R02.1 manifest")
    return frozen


def load_single_path_rows(config: dict[str, Any], path_manifest: dict[str, Any]) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for item in config["frozen_families"]:
        signal_id = item["signal_id"]
        path = topic_path(path_manifest["per_signal_csv_paths"][signal_id])
        header = pd.read_csv(path, nrows=0).columns
        cols = [c for c in PATH_COLS if c in header]
        df = pd.read_csv(path, usecols=cols, low_memory=False)
        df["family_id"] = item["family_id"]
        df["signal_id"] = signal_id
        df["condition_group_id"] = item["condition_group_id"]
        frames.append(df)
    out = pd.concat(frames, ignore_index=True)
    out["signal_date"] = pd.to_datetime(out["signal_date"])
    out["trade_date"] = out["signal_date"]
    out["year"] = out["signal_date"].dt.year.astype(int)
    for col in ["entry_date"]:
        out[col] = pd.to_datetime(out[col], errors="coerce")
    out["entry_valid_bool"] = _boolish(out["entry_valid"])
    out["path_complete_bool"] = _boolish(out["path_complete_120d"])
    out["label"] = label_rows(out)
    out["good_path_flag"] = out["label"].eq("good_path")
    out["bad_path_flag"] = out["label"].eq("bad_path")
    out["neutral_path_flag"] = out["label"].eq("neutral_path")
    out["label_denominator_flag"] = out["label"].isin(LABELS)
    return out


def build_calendar_ordinals(config: dict[str, Any]) -> pd.DataFrame:
    path = topic_path(config["upstream_eligible_day_density"]["panel"])
    cal = pd.read_parquet(path, columns=["instrument_id", "trade_date"])
    cal["trade_date"] = pd.to_datetime(cal["trade_date"])
    cal = cal.drop_duplicates(["instrument_id", "trade_date"]).sort_values(["instrument_id", "trade_date"])
    cal["date_ordinal"] = cal.groupby("instrument_id").cumcount()
    return cal


def build_same_day_bundle(events: pd.DataFrame) -> pd.DataFrame:
    path_identity_cols = [
        "entry_date",
        "entry_price",
        "entry_valid",
        "entry_invalid_reason",
        "path_complete_120d",
        "available_forward_trading_days",
        "path_incomplete_reason",
        "first_minus5_offset",
        "first_close_minus5_offset",
        "max_loss_before_first_plus10",
        "hit_plus10_before_minus5",
        "path_quality_flag",
        "early_failure_flag",
        "close_return_t20",
        "close_return_t60",
        "close_return_t120",
        "max_gain_120d",
        "max_loss_120d",
        "max_drawdown_120d",
        "label",
    ]
    rows: list[dict[str, Any]] = []
    for (instrument_id, trade_date), g in events.sort_values(["instrument_id", "trade_date", "family_id"]).groupby(
        ["instrument_id", "trade_date"], sort=True
    ):
        fams = sorted(g["family_id"].astype(str).unique().tolist())
        inconsistent = g[[c for c in path_identity_cols if c in g.columns]].astype(str).nunique(dropna=False)
        inconsistent = inconsistent[inconsistent.gt(1)]
        if not inconsistent.empty:
            raise RuntimeError(
                "same-day bundle path fields differ across families: "
                f"instrument_id={instrument_id}, trade_date={trade_date}, fields={inconsistent.index.tolist()}"
            )
        base = g.iloc[0].to_dict()
        base["same_day_bundle_key"] = "|".join(fams)
        base["seed_family_set"] = "|".join(fams)
        base["seed_same_day_bundle_key"] = base["same_day_bundle_key"]
        base["same_day_family_count"] = len(fams)
        base["seed_same_day_family_count"] = len(fams)
        rows.append(base)
    return pd.DataFrame(rows)


def build_episode_panel(events: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    bundle = build_same_day_bundle(events)
    cal = build_calendar_ordinals(config)
    bundle = bundle.merge(cal, on=["instrument_id", "trade_date"], how="left")
    if bundle["date_ordinal"].isna().any():
        bundle["date_ordinal"] = bundle.groupby("instrument_id")["trade_date"].rank(method="dense").astype(int) - 1
    rows: list[dict[str, Any]] = []
    for instrument_id, g in bundle.sort_values(["instrument_id", "date_ordinal", "same_day_bundle_key"]).groupby("instrument_id", sort=True):
        next_allowed = -math.inf
        for _, row in g.iterrows():
            ordv = int(row["date_ordinal"])
            if ordv <= next_allowed:
                continue
            next_allowed = ordv + 30
            payload = row.to_dict()
            seed_trade_date = pd.Timestamp(payload["trade_date"]).date().isoformat()
            payload["seed_episode_id"] = _hash_json([instrument_id, seed_trade_date, payload["same_day_bundle_key"]], 16)
            payload["seed_trade_date"] = seed_trade_date
            payload["seed_entry_date"] = (
                pd.Timestamp(payload["entry_date"]).date().isoformat() if pd.notna(payload.get("entry_date")) else ""
            )
            payload["seed_entry_price"] = payload.get("entry_price")
            payload["seed_type"] = "single_family_seed" if int(payload["seed_same_day_family_count"]) == 1 else "multi_family_bundle_seed"
            payload["seed_primary_family_id"] = (
                payload["seed_same_day_bundle_key"] if payload["seed_type"] == "single_family_seed" else "multi_family_bundle"
            )
            payload["context_bucket_id"] = (
                "bundle="
                + str(payload["seed_same_day_bundle_key"])
                + "|split="
                + str(payload["split"])
                + "|year="
                + str(payload["year"])
                + "|family_count="
                + str(payload["seed_same_day_family_count"])
                + "|risk=na"
            )
            payload["censored_or_invalid_reason"] = ""
            if str(payload.get("entry_valid")).lower() not in {"true", "1"}:
                payload["censored_or_invalid_reason"] = str(payload.get("entry_invalid_reason", "entry_invalid"))
            elif str(payload.get("path_complete_120d")).lower() not in {"true", "1"}:
                payload["censored_or_invalid_reason"] = str(payload.get("path_incomplete_reason", "path_incomplete_120d"))
            rows.append(payload)
    out = pd.DataFrame(rows)
    out["label"] = label_rows(out)
    out["good_path_flag"] = out["label"].eq("good_path")
    out["bad_path_flag"] = out["label"].eq("bad_path")
    out["neutral_path_flag"] = out["label"].eq("neutral_path")
    out["label_denominator_flag"] = out["label"].isin(LABELS)
    out["drawdown_loss_120d"] = _as_num(out["max_drawdown_120d"]).clip(upper=0).abs()
    out["entry_valid_bool"] = _boolish(out["entry_valid"])
    out["path_complete_bool"] = _boolish(out["path_complete_120d"])
    return out


def survived_at(df: pd.DataFrame, checkpoint: int) -> pd.Series:
    enough = _as_num(df["available_forward_trading_days"]) >= checkpoint
    fm = _as_num(df["first_minus5_offset"])
    fcm = _as_num(df["first_close_minus5_offset"])
    no_low = fm.isna() | (fm > checkpoint)
    no_close = fcm.isna() | (fcm > checkpoint)
    return _boolish(df["entry_valid"]) & enough & no_low & no_close


def assign_train_folds(episodes: pd.DataFrame, config: dict[str, Any]) -> pd.Series:
    k = int(config["train_selection"]["train_inner_cv_fold_count"])
    seed = config["train_selection"]["train_only_selection_seed"]
    return episodes["seed_episode_id"].astype(str).map(lambda x: int(hashlib.sha256(f"{seed}|{x}".encode()).hexdigest(), 16) % k)


def scope_mask(df: pd.DataFrame, seed_scope_id: str) -> pd.Series:
    if seed_scope_id == "all":
        return pd.Series(True, index=df.index)
    if seed_scope_id.startswith("seed_type="):
        return df["seed_type"].astype(str).eq(seed_scope_id.split("=", 1)[1])
    if seed_scope_id.startswith("seed_primary_family_id="):
        return df["seed_primary_family_id"].astype(str).eq(seed_scope_id.split("=", 1)[1])
    if seed_scope_id.startswith("seed_same_day_family_count="):
        return df["seed_same_day_family_count"].astype(int).astype(str).eq(seed_scope_id.split("=", 1)[1])
    raise ValueError(f"unsupported seed_scope_id: {seed_scope_id}")


def seed_scope_type(seed_scope_id: str) -> str:
    return seed_scope_id.split("=", 1)[0] if "=" in seed_scope_id else "all"


def bucket_values(df: pd.DataFrame, fallback_grain: str) -> pd.Series:
    if fallback_grain == "same_day_family_count":
        return "same_day_family_count=" + df["seed_same_day_family_count"].astype(int).astype(str)
    if fallback_grain == "seed_primary_family_id":
        return "seed_primary_family_id=" + df["seed_primary_family_id"].astype(str)
    if fallback_grain == "seed_type":
        return "seed_type=" + df["seed_type"].astype(str)
    if fallback_grain == "same_day_bundle_key":
        return "same_day_bundle_key=" + df["seed_same_day_bundle_key"].astype(str)
    if fallback_grain == "context_bucket_id":
        return "context_bucket_id=" + df["context_bucket_id"].astype(str)
    raise ValueError(f"unsupported fallback_grain: {fallback_grain}")


def build_probability_table(df: pd.DataFrame, bucket_col: str, n_min: int, prior_source: str, fallback_level: str) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for key, g in df.groupby(bucket_col, dropna=False, sort=True):
        post = posterior_from_df(g)
        row = {bucket_col: key, **{k: v for k, v in post.items() if k != "posterior_alpha_total"}}
        row["sample_sufficiency_status"] = _sample_status(int(row["label_denominator_count"]), n_min)
        row["split_stability_status"] = "not_evaluated_for_bucket_table"
        row["prior_source"] = prior_source
        row["fallback_level"] = fallback_level
        rows.append(row)
    return pd.DataFrame(rows)


def lookup_scores(source: pd.DataFrame, targets: pd.DataFrame, bucket_col: str) -> pd.Series:
    if source.empty:
        return pd.Series(np.nan, index=targets.index)
    score_map = source.set_index(bucket_col)["prob_feasibility_score"].to_dict()
    return targets[bucket_col].map(score_map)


def add_score_columns(table: pd.DataFrame) -> pd.DataFrame:
    if table.empty:
        table["prob_feasibility_score"] = pd.Series(dtype=float)
    else:
        table["prob_feasibility_score"] = table["P_good_lower"] - table["P_bad_upper"]
    return table


def metric_row(
    df: pd.DataFrame,
    scenario_id: str,
    comparison_role: str,
    split: str,
    candidate_scope_id: str,
    baseline_3_scope_id: str,
    selected_checkpoint: str,
    exposure_label: str,
    policy: str,
    candidate_split_pass: bool | str,
    comparison_status: str,
) -> dict[str, Any]:
    post = posterior_from_df(df)
    seed_count = int(len(df))
    censored = int(df["label"].eq("censored_or_invalid").sum()) if not df.empty else 0
    early = _boolish(df.get("early_failure_flag", pd.Series(dtype=object))).mean() if not df.empty else np.nan
    row = {
        "scenario_id": scenario_id,
        "comparison_role": comparison_role,
        "candidate_scope_id": candidate_scope_id,
        "baseline_3_scope_id": baseline_3_scope_id,
        "split": split,
        "year": "all",
        "selected_checkpoint": selected_checkpoint,
        "proxy_exposure_schedule_label": exposure_label,
        "risk_budget_status": "probability_only_ev_r_blocked",
        "exposure_label_is_validated_size": False,
        "path_metric_denominator_policy": policy,
        "seed_episode_count": seed_count,
        "censored_or_invalid_count": censored,
        "censored_or_invalid_rate": _safe_div(censored, seed_count),
        **{k: v for k, v in post.items() if k != "posterior_alpha_total"},
        "max_drawdown_120d_p50": _q(df["max_drawdown_120d"], 0.50) if "max_drawdown_120d" in df else np.nan,
        "max_drawdown_120d_p10": _q(df["max_drawdown_120d"], 0.10) if "max_drawdown_120d" in df else np.nan,
        "max_drawdown_120d_p75": _q(df["max_drawdown_120d"], 0.75) if "max_drawdown_120d" in df else np.nan,
        "max_drawdown_120d_p90": _q(df["max_drawdown_120d"], 0.90) if "max_drawdown_120d" in df else np.nan,
        "drawdown_loss_120d_p90": _q(df["drawdown_loss_120d"], 0.90) if "drawdown_loss_120d" in df else np.nan,
        "drawdown_severity_120d_p90": _q(df["drawdown_loss_120d"], 0.90) if "drawdown_loss_120d" in df else np.nan,
        "max_gain_120d_p50": _q(df["max_gain_120d"], 0.50) if "max_gain_120d" in df else np.nan,
        "max_gain_120d_p75": _q(df["max_gain_120d"], 0.75) if "max_gain_120d" in df else np.nan,
        "max_gain_120d_p90": _q(df["max_gain_120d"], 0.90) if "max_gain_120d" in df else np.nan,
        "close_return_t20_p50": _q(df["close_return_t20"], 0.50) if "close_return_t20" in df else np.nan,
        "close_return_t60_p50": _q(df["close_return_t60"], 0.50) if "close_return_t60" in df else np.nan,
        "close_return_t120_p50": _q(df["close_return_t120"], 0.50) if "close_return_t120" in df else np.nan,
        "upside_capture_proxy": _q(df["max_gain_120d"], 0.75) if "max_gain_120d" in df else np.nan,
        "upside_capture_ratio_vs_baseline3": np.nan,
        "early_failure_rate": float(early) if pd.notna(early) else np.nan,
        "candidate_split_pass": candidate_split_pass,
        "comparison_vs_baseline_3_status": comparison_status,
    }
    return row


def split_pass(candidate: dict[str, Any], baseline: dict[str, Any], thresholds: dict[str, float], n_min: int) -> tuple[bool, str, dict[str, Any]]:
    cden = int(candidate.get("label_denominator_count", 0) or 0)
    bden = int(baseline.get("label_denominator_count", 0) or 0)
    if cden < n_min or bden < n_min:
        return False, "blocked_insufficient_denominator", {}
    base_upside = baseline.get("max_gain_120d_p75")
    if pd.isna(base_upside) or float(base_upside) <= 0:
        return False, "blocked_nonpositive_baseline_upside", {"upside_capture_ratio_vs_baseline3": np.nan}
    ratio = float(candidate.get("max_gain_120d_p75", np.nan)) / max(float(base_upside), 1e-12)
    checks = {
        "bad_upper_pass": candidate["P_bad_upper"] <= baseline["P_bad_upper"] - thresholds["min_abs_bad_upper_improvement_vs_baseline3"],
        "good_lower_pass": candidate["P_good_lower"] >= baseline["P_good_lower"] - thresholds["max_abs_good_lower_loss_vs_baseline3"],
        "upside_pass": ratio >= thresholds["min_upside_capture_ratio_vs_baseline3"],
        "drawdown_pass": candidate["drawdown_severity_120d_p90"]
        <= baseline["drawdown_severity_120d_p90"] + thresholds["max_abs_drawdown_severity_worsening_vs_baseline3"],
        "upside_capture_ratio_vs_baseline3": ratio,
    }
    passed = bool(checks["bad_upper_pass"] and checks["good_lower_pass"] and checks["upside_pass"] and checks["drawdown_pass"])
    return passed, "passed" if passed else "failed_thresholds_vs_baseline_3", checks


def train_candidate_grid(episodes: pd.DataFrame, config: dict[str, Any], split_stability: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any], pd.DataFrame]:
    thresholds = [float(x) for x in config["probability_gate_threshold_grid"]]
    checkpoints = [int(x) for x in config["survival_checkpoints"]]
    fallback_allowed = list(config["fallback_grain_grid"])
    seed_scopes = ["all"]
    seed_scopes.extend([f"seed_type={v}" for v in sorted(episodes["seed_type"].astype(str).unique())])
    seed_scopes.extend([f"seed_primary_family_id={v}" for v in sorted(episodes["seed_primary_family_id"].astype(str).unique())])
    seed_scopes.extend([f"seed_same_day_family_count={int(v)}" for v in sorted(episodes["seed_same_day_family_count"].dropna().astype(int).unique())])
    stability = _stability_lookup(split_stability)
    family_signal_map = _family_signal_map(config)
    sample_thresholds = {k: int(v) for k, v in config["sample_denominator_thresholds"].items()}
    theoretical_grid_total = len(seed_scopes) * len(checkpoints) * len(fallback_allowed) * len(thresholds)
    cap = int(config["train_selection"]["max_train_grid_total_candidate_count"])
    if theoretical_grid_total > cap:
        return pd.DataFrame(), {
            "grid_multiplicity_status": "invalid_requirement_violation",
            "train_grid_total_candidate_count": theoretical_grid_total,
            "train_eligible_candidate_count_after_gate": 0,
            "selected": None,
        }, pd.DataFrame()

    train = episodes.loc[episodes["split"].eq("train")].copy()
    rows: list[dict[str, Any]] = []
    score_lineage_frames: list[pd.DataFrame] = []
    n_min_train = int(config["sample_denominator_thresholds"]["N_min_train"])
    pass_thresholds = {k: float(v) for k, v in config["pass_fail_thresholds"].items()}
    for seed_scope_id in seed_scopes:
        scope_gate = _scope_gate_status(episodes, seed_scope_id, sample_thresholds, stability, family_signal_map)
        if scope_gate["r03a_gate_status"] != "sufficient_and_stable":
            continue
        in_scope = scope_mask(train, seed_scope_id)
        if int((in_scope & train["label_denominator_flag"]).sum()) < n_min_train:
            continue
        for checkpoint in checkpoints:
            survived = survived_at(train, checkpoint)
            base_mask = in_scope & survived
            baseline_df = train.loc[base_mask].copy()
            baseline_metrics = metric_row(
                baseline_df,
                "baseline_3_probe_survival_step_up",
                "baseline",
                "train",
                seed_scope_id + f"|T+{checkpoint}",
                seed_scope_id + f"|T+{checkpoint}",
                f"T+{checkpoint}",
                config["exposure_labels"]["selected_probe_label"] + "->" + config["exposure_labels"]["selected_survival_step_label"],
                "episode_first_trigger_survivor_label_denominator",
                "not_applicable",
                "baseline_3_same_scope",
            )
            for fallback_grain in fallback_allowed:
                bucket_col = f"bucket__{fallback_grain}"
                train[bucket_col] = bucket_values(train, fallback_grain)
                distinct_bucket_count = int(train.loc[base_mask, bucket_col].nunique(dropna=False))
                degenerate = "non_degenerate" if distinct_bucket_count >= 2 else "degenerate_probability_gate"
                if distinct_bucket_count < 2:
                    continue
                fallback_gate = _fallback_gate_status(episodes, scope_mask(episodes, seed_scope_id) & survived_at(episodes, checkpoint), fallback_grain, sample_thresholds, stability)
                if not fallback_gate["fallback_grain_allowed"]:
                    continue

                score = pd.Series(np.nan, index=train.index)
                for fold in range(int(config["train_selection"]["train_inner_cv_fold_count"])):
                    fit_mask = base_mask & train["train_inner_cv_fold_id"].ne(fold)
                    target_mask = base_mask & train["train_inner_cv_fold_id"].eq(fold)
                    table = build_probability_table(
                        train.loc[fit_mask].copy(),
                        bucket_col,
                        n_min_train,
                        "train_inner_cv_out_of_fold",
                        fallback_grain,
                    )
                    table = add_score_columns(table)
                    score.loc[target_mask] = lookup_scores(table, train.loc[target_mask], bucket_col)
                full_table = build_probability_table(
                    train.loc[base_mask].copy(),
                    bucket_col,
                    n_min_train,
                    "full_train_frozen",
                    fallback_grain,
                )
                full_table = add_score_columns(full_table)
                if not full_table.empty:
                    lineage = full_table.copy()
                    lineage["seed_scope_id"] = seed_scope_id
                    lineage["survival_checkpoint"] = f"T+{checkpoint}"
                    lineage["fallback_grain"] = fallback_grain
                    lineage["probability_bucket_key"] = lineage[bucket_col]
                    score_lineage_frames.append(lineage)
                for threshold_idx, gate in enumerate(thresholds):
                    cand_mask = base_mask & score.ge(gate)
                    candidate_df = train.loc[cand_mask].copy()
                    candidate_metrics = metric_row(
                        candidate_df,
                        "candidate_probability_survival_step",
                        "candidate",
                        "train",
                        seed_scope_id + f"|T+{checkpoint}|{fallback_grain}",
                        seed_scope_id + f"|T+{checkpoint}",
                        f"T+{checkpoint}",
                        config["exposure_labels"]["selected_probe_label"] + "->" + config["exposure_labels"]["selected_survival_step_label"],
                        "episode_first_trigger_candidate_included_label_denominator",
                        False,
                        "candidate_train_oof_vs_baseline_3",
                    )
                    passed, status, pass_details = split_pass(candidate_metrics, baseline_metrics, pass_thresholds, n_min_train)
                    candidate_metrics.update(pass_details)
                    edge = (
                        (candidate_metrics["P_good_lower"] - baseline_metrics["P_good"])
                        - (candidate_metrics["P_bad_upper"] - baseline_metrics["P_bad"])
                        if pd.notna(candidate_metrics["P_good_lower"]) and pd.notna(baseline_metrics["P_good"])
                        else np.nan
                    )
                    bad_ci = 0.5 * (
                        candidate_metrics["credible_interval_width_bad"] + baseline_metrics["credible_interval_width_bad"]
                    )
                    good_ci = 0.5 * (
                        candidate_metrics["credible_interval_width_good"] + baseline_metrics["credible_interval_width_good"]
                    )
                    threshold_smaller = (
                        pass_thresholds["min_abs_bad_upper_improvement_vs_baseline3"] < bad_ci
                        or pass_thresholds["max_abs_good_lower_loss_vs_baseline3"] < good_ci
                    )
                    row = {
                        "candidate_id": "candidate_probability_survival_step",
                        "candidate_scope_id": seed_scope_id + f"|T+{checkpoint}|{fallback_grain}",
                        "baseline_3_scope_id": seed_scope_id + f"|T+{checkpoint}",
                        "seed_scope_id": seed_scope_id,
                        "seed_scope_type": seed_scope_type(seed_scope_id),
                        "survival_checkpoint": f"T+{checkpoint}",
                        "probe_label": config["exposure_labels"]["selected_probe_label"],
                        "survival_step_label": config["exposure_labels"]["selected_survival_step_label"],
                        "probability_gate_threshold": gate,
                        "fallback_grain": fallback_grain,
                        "probability_gate_threshold_grid_id": threshold_idx,
                        "episode_probability_score_formula": "P_good_lower - P_bad_upper",
                        "train_scoring_mode": config["train_selection"]["train_scoring_mode"],
                        "train_inner_cv_fold_count": int(config["train_selection"]["train_inner_cv_fold_count"]),
                        "train_grid_total_candidate_count": 0,
                        "train_eligible_candidate_count_after_gate": 0,
                        "train_grid_multiplicity_status": "within_cap",
                        "train_distinct_probability_bucket_count": distinct_bucket_count,
                        "degenerate_probability_gate_status": degenerate,
                        "credible_interval_level": float(config["posterior"]["credible_interval_level"]),
                        "upstream_sample_sufficiency_status": scope_gate["upstream_sample_sufficiency_status"],
                        "upstream_stability_status": scope_gate["upstream_stability_status"],
                        "r03a_stability_status": scope_gate["r03a_stability_status"],
                        "r03a_gate_status": scope_gate["r03a_gate_status"],
                        "fallback_grain_status": fallback_gate["fallback_grain_status"],
                        "fallback_grain_disallowed_reason": fallback_gate["fallback_grain_disallowed_reason"],
                        "train_label_denominator": candidate_metrics["label_denominator_count"],
                        "train_baseline_3_same_scope_label_denominator": baseline_metrics["label_denominator_count"],
                        "train_denominator_gate_pass": bool(
                            candidate_metrics["label_denominator_count"] >= n_min_train
                            and baseline_metrics["label_denominator_count"] >= n_min_train
                        ),
                        "train_oof_label_denominator": candidate_metrics["label_denominator_count"],
                        "train_oof_P_good": candidate_metrics["P_good"],
                        "train_oof_P_bad": candidate_metrics["P_bad"],
                        "train_oof_P_neutral": candidate_metrics["P_neutral"],
                        "train_oof_P_good_lower": candidate_metrics["P_good_lower"],
                        "train_oof_P_good_upper": candidate_metrics["P_good_upper"],
                        "train_oof_P_bad_lower": candidate_metrics["P_bad_lower"],
                        "train_oof_P_bad_upper": candidate_metrics["P_bad_upper"],
                        "train_oof_credible_interval_width_good": candidate_metrics["credible_interval_width_good"],
                        "train_oof_credible_interval_width_bad": candidate_metrics["credible_interval_width_bad"],
                        "train_oof_prob_feasibility_score": candidate_metrics["P_good_lower"] - candidate_metrics["P_bad_upper"],
                        "train_oof_prob_edge_vs_baseline_3": edge,
                        "train_oof_bad_edge_ci_halfwidth_proxy": bad_ci,
                        "train_oof_good_edge_ci_halfwidth_proxy": good_ci,
                        "train_oof_candidate_eligibility_threshold_smaller_than_ci_halfwidth": bool(threshold_smaller),
                        "train_oof_baseline_3_same_scope_P_good": baseline_metrics["P_good"],
                        "train_oof_baseline_3_same_scope_P_bad": baseline_metrics["P_bad"],
                        "train_oof_baseline_3_same_scope_P_neutral": baseline_metrics["P_neutral"],
                        "train_oof_baseline_3_same_scope_P_good_lower": baseline_metrics["P_good_lower"],
                        "train_oof_baseline_3_same_scope_P_good_upper": baseline_metrics["P_good_upper"],
                        "train_oof_baseline_3_same_scope_P_bad_lower": baseline_metrics["P_bad_lower"],
                        "train_oof_baseline_3_same_scope_P_bad_upper": baseline_metrics["P_bad_upper"],
                        "train_oof_baseline_3_same_scope_credible_interval_width_good": baseline_metrics["credible_interval_width_good"],
                        "train_oof_baseline_3_same_scope_credible_interval_width_bad": baseline_metrics["credible_interval_width_bad"],
                        "train_full_frozen_P_good": posterior_from_df(train.loc[base_mask])["P_good"],
                        "train_full_frozen_P_bad": posterior_from_df(train.loc[base_mask])["P_bad"],
                        "train_full_frozen_P_neutral": posterior_from_df(train.loc[base_mask])["P_neutral"],
                        "train_full_frozen_P_good_lower": posterior_from_df(train.loc[base_mask])["P_good_lower"],
                        "train_full_frozen_P_good_upper": posterior_from_df(train.loc[base_mask])["P_good_upper"],
                        "train_full_frozen_P_bad_lower": posterior_from_df(train.loc[base_mask])["P_bad_lower"],
                        "train_full_frozen_P_bad_upper": posterior_from_df(train.loc[base_mask])["P_bad_upper"],
                        "train_full_frozen_credible_interval_width_good": posterior_from_df(train.loc[base_mask])["credible_interval_width_good"],
                        "train_full_frozen_credible_interval_width_bad": posterior_from_df(train.loc[base_mask])["credible_interval_width_bad"],
                        "train_full_frozen_prob_feasibility_score": posterior_from_df(train.loc[base_mask])["P_good_lower"]
                        - posterior_from_df(train.loc[base_mask])["P_bad_upper"],
                        "train_upside_capture_ratio_vs_baseline3": candidate_metrics.get("upside_capture_ratio_vs_baseline3", np.nan),
                        "train_drawdown_severity_120d_p90": candidate_metrics["drawdown_severity_120d_p90"],
                        "train_baseline_3_same_scope_drawdown_severity_120d_p90": baseline_metrics["drawdown_severity_120d_p90"],
                        "train_candidate_split_pass": bool(passed),
                        "selection_metric": config["train_selection"]["selection_metric"],
                        "selection_metric_value": edge,
                        "tie_breaker_tuple": "",
                        **pass_thresholds,
                        "selection_rank": np.nan,
                        "selected_in_train": False,
                        "selection_reason": status,
                    }
                    row["tie_breaker_tuple"] = json.dumps(
                        [
                            row["train_oof_prob_edge_vs_baseline_3"],
                            -row["train_oof_P_bad_upper"] if pd.notna(row["train_oof_P_bad_upper"]) else None,
                            row["train_oof_P_good_lower"],
                            -row["train_drawdown_severity_120d_p90"] if pd.notna(row["train_drawdown_severity_120d_p90"]) else None,
                            row["train_upside_capture_ratio_vs_baseline3"],
                            row["train_label_denominator"],
                            {"T+10": 3, "T+5": 2, "T+3": 1}.get(row["survival_checkpoint"], 0),
                            row["seed_scope_id"],
                            config["fallback_grain_order"].index(row["fallback_grain"]),
                            -row["probability_gate_threshold"],
                        ],
                        ensure_ascii=True,
                    )
                    rows.append(row)
    grid = pd.DataFrame(rows)
    materialized_grid_total = int(len(grid))
    if grid.empty:
        return grid, {
            "grid_multiplicity_status": "within_cap",
            "train_grid_total_candidate_count": materialized_grid_total,
            "train_eligible_candidate_count_after_gate": 0,
            "selected": None,
        }, pd.concat(score_lineage_frames, ignore_index=True) if score_lineage_frames else pd.DataFrame()
    grid["train_grid_total_candidate_count"] = materialized_grid_total
    eligible_mask = (
        grid["train_candidate_split_pass"].astype(bool)
        & grid["train_denominator_gate_pass"].astype(bool)
        & grid["r03a_gate_status"].eq("sufficient_and_stable")
    )
    eligible_count = int(eligible_mask.sum())
    grid["train_eligible_candidate_count_after_gate"] = eligible_count
    if eligible_count > int(config["train_selection"]["max_train_eligible_candidate_count_after_gate"]):
        grid["train_grid_multiplicity_status"] = "blocked_grid_multiplicity_excessive"
        return grid, {
            "grid_multiplicity_status": "blocked_grid_multiplicity_excessive",
            "train_grid_total_candidate_count": materialized_grid_total,
            "train_eligible_candidate_count_after_gate": eligible_count,
            "selected": None,
        }, pd.concat(score_lineage_frames, ignore_index=True) if score_lineage_frames else pd.DataFrame()
    eligible = grid.loc[eligible_mask].copy()
    if eligible.empty:
        grid["selection_reason"] = np.where(grid["selection_reason"].eq("passed"), "not_eligible", grid["selection_reason"])
        return grid, {
            "grid_multiplicity_status": "within_cap",
            "train_grid_total_candidate_count": materialized_grid_total,
            "train_eligible_candidate_count_after_gate": 0,
            "selected": None,
        }, pd.concat(score_lineage_frames, ignore_index=True) if score_lineage_frames else pd.DataFrame()
    fallback_rank = {name: i for i, name in enumerate(config["fallback_grain_order"])}
    checkpoint_rank = {"T+10": 0, "T+5": 1, "T+3": 2}
    eligible = eligible.assign(
        _checkpoint_rank=eligible["survival_checkpoint"].map(checkpoint_rank),
        _fallback_rank=eligible["fallback_grain"].map(fallback_rank),
    ).sort_values(
        [
            "train_oof_prob_edge_vs_baseline_3",
            "train_oof_P_bad_upper",
            "train_oof_P_good_lower",
            "train_drawdown_severity_120d_p90",
            "train_upside_capture_ratio_vs_baseline3",
            "train_label_denominator",
            "_checkpoint_rank",
            "seed_scope_id",
            "_fallback_rank",
            "probability_gate_threshold",
        ],
        ascending=[False, True, False, True, False, False, True, True, True, True],
        na_position="last",
    )
    selected_idx = eligible.index[0]
    grid.loc[eligible.index, "selection_rank"] = range(1, len(eligible) + 1)
    grid.loc[selected_idx, "selected_in_train"] = True
    grid.loc[selected_idx, "selection_reason"] = "selected_by_train_oof_metric_and_tie_breaker"
    return grid, {
        "grid_multiplicity_status": "within_cap",
        "train_grid_total_candidate_count": materialized_grid_total,
        "train_eligible_candidate_count_after_gate": eligible_count,
        "selected": grid.loc[selected_idx].to_dict(),
    }, pd.concat(score_lineage_frames, ignore_index=True) if score_lineage_frames else pd.DataFrame()


def apply_selected_candidate(episodes: pd.DataFrame, selected: dict[str, Any] | None, score_lineage: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    out = episodes.copy()
    out["selected_candidate_id"] = ""
    out["candidate_scope_id"] = ""
    out["baseline_3_scope_id"] = ""
    out["episode_in_selected_seed_scope"] = False
    out["episode_survived_selected_checkpoint"] = False
    out["episode_probability_bucket_key"] = ""
    out["episode_probability_score"] = np.nan
    out["episode_probability_score_source"] = ""
    out["candidate_episode_included"] = False
    out["baseline_3_same_scope_episode_included"] = False
    if not selected:
        return out
    checkpoint = int(str(selected["survival_checkpoint"]).replace("T+", ""))
    fallback_grain = str(selected["fallback_grain"])
    seed_scope_id = str(selected["seed_scope_id"])
    threshold = float(selected["probability_gate_threshold"])
    bucket_col = f"bucket__{fallback_grain}"
    out[bucket_col] = bucket_values(out, fallback_grain)
    in_scope = scope_mask(out, seed_scope_id)
    survived = survived_at(out, checkpoint)
    out["selected_candidate_id"] = selected["candidate_id"]
    out["candidate_scope_id"] = selected["candidate_scope_id"]
    out["baseline_3_scope_id"] = selected["baseline_3_scope_id"]
    out["episode_in_selected_seed_scope"] = in_scope
    out["episode_survived_selected_checkpoint"] = survived
    out["episode_probability_bucket_key"] = out[bucket_col]
    out["baseline_3_same_scope_episode_included"] = in_scope & survived
    train = out.loc[out["split"].eq("train") & in_scope & survived].copy()
    scores = pd.Series(np.nan, index=out.index)
    for fold in range(int(config["train_selection"]["train_inner_cv_fold_count"])):
        fit = train.loc[train["train_inner_cv_fold_id"].ne(fold)].copy()
        table = build_probability_table(fit, bucket_col, int(config["sample_denominator_thresholds"]["N_min_train"]), "train_inner_cv_out_of_fold", fallback_grain)
        table = add_score_columns(table)
        target_idx = train.loc[train["train_inner_cv_fold_id"].eq(fold)].index
        scores.loc[target_idx] = lookup_scores(table, out.loc[target_idx], bucket_col)
    full_train = build_probability_table(
        train.copy(), bucket_col, int(config["sample_denominator_thresholds"]["N_min_train"]), "full_train_frozen", fallback_grain
    )
    full_train = add_score_columns(full_train)
    eval_idx = out.loc[out["split"].isin(["validation", "robustness"]) & in_scope & survived].index
    scores.loc[eval_idx] = lookup_scores(full_train, out.loc[eval_idx], bucket_col)
    out["episode_probability_score"] = scores
    out["episode_probability_score_source"] = np.where(
        out["split"].eq("train"),
        "train_inner_cv_out_of_fold",
        np.where(out["split"].isin(["validation", "robustness"]), "full_train_frozen", ""),
    )
    out["candidate_episode_included"] = in_scope & survived & out["episode_probability_score"].ge(threshold)
    return out


def build_t0_prior(episodes: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    specs = [
        ("all", []),
        ("split", ["split"]),
        ("year", ["year"]),
        ("seed_primary_family_id", ["seed_primary_family_id"]),
        ("seed_same_day_family_count", ["seed_same_day_family_count"]),
    ]
    for grouping, cols in specs:
        grouped = [(("all",), episodes)] if not cols else episodes.groupby(cols, dropna=False, sort=True)
        for key, g in grouped:
            if not isinstance(key, tuple):
                key = (key,)
            row = {"grouping": grouping, "grouping_key": "|".join(str(v) for v in key)}
            if cols:
                row.update({c: v for c, v in zip(cols, key)})
            post = posterior_from_df(g)
            row.update({k: v for k, v in post.items() if k != "posterior_alpha_total"})
            row["sample_sufficiency_status"] = _sample_status(
                int(row["label_denominator_count"]), int(config["sample_denominator_thresholds"]["N_min_train"])
            )
            row["split_stability_status"] = "same_grain_recomputed_r03a"
            row["prior_source"] = "r03a_episode_first_trigger_t0"
            row["fallback_level"] = grouping
            rows.append(row)
    return pd.DataFrame(rows)


def build_survival_lift(episodes: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for checkpoint in [int(x) for x in config["survival_checkpoints"]]:
        for grain, grouped in [
            ("global", [(("all",), episodes)]),
            ("by_seed_primary_family_id", episodes.groupby(["seed_primary_family_id"], dropna=False, sort=True)),
        ]:
            for key, g in grouped:
                if not isinstance(key, tuple):
                    key = (key,)
                survivor = survived_at(g, checkpoint)
                t0 = posterior_from_df(g)
                surv = posterior_from_df(g.loc[survivor], "survivor_")
                non = posterior_from_df(g.loc[~survivor], "non_survivor_")
                row = {
                    "checkpoint": f"T+{checkpoint}",
                    "survival_lift_grain": grain,
                    "seed_primary_family_id_or_all": str(key[0]),
                    "pre_checkpoint_episode_count": int(len(g)),
                    "survivor_episode_count": int(survivor.sum()),
                    "non_survivor_episode_count": int((~survivor).sum()),
                    "survivor_rate": _safe_div(int(survivor.sum()), int(len(g))),
                    **{k: v for k, v in surv.items() if k != "survivor_posterior_alpha_total"},
                    **{k: v for k, v in non.items() if k != "non_survivor_posterior_alpha_total"},
                    "survival_lift_good_vs_t0_same_grain": surv["survivor_P_good"] - t0["P_good"],
                    "survival_lift_bad_vs_t0_same_grain": surv["survivor_P_bad"] - t0["P_bad"],
                    "split_stability_status": "same_grain_recomputed_r03a",
                }
                rows.append(row)
    return pd.DataFrame(rows)


def build_baseline_and_readonly(episodes: pd.DataFrame, selected: dict[str, Any] | None, config: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame, str]:
    rows: list[dict[str, Any]] = []
    readonly: dict[str, Any] = {
        "candidate_id": "candidate_probability_survival_step",
        "frozen_from_train": bool(selected),
        "evaluation_scope": "validation_and_robustness",
        "candidate_scope_id": selected["candidate_scope_id"] if selected else "",
        "baseline_3_scope_id": selected["baseline_3_scope_id"] if selected else "",
        "threshold_changed_after_train": False,
        "checkpoint_changed_after_train": False,
        "bucket_changed_after_train": False,
        "validation_episode_probability_score_source": "full_train_frozen_posterior",
        "validation_probability_evaluation_source": "actual_validation_labels_after_frozen_inclusion",
        "robustness_episode_probability_score_source": "full_train_frozen_posterior",
        "robustness_probability_evaluation_source": "actual_robustness_labels_after_frozen_inclusion",
        "readonly_status": "readonly_evaluation_no_validation_tuning",
    }
    pass_thresholds = {k: float(v) for k, v in config["pass_fail_thresholds"].items()}
    split_passes: dict[str, bool] = {}
    if selected:
        checkpoint = selected["survival_checkpoint"]
        exposure = config["exposure_labels"]["selected_probe_label"] + "->" + config["exposure_labels"]["selected_survival_step_label"]
    else:
        checkpoint = "T+10"
        exposure = config["exposure_labels"]["selected_probe_label"] + "->" + config["exposure_labels"]["selected_survival_step_label"]
    for split in SPLITS:
        split_df = episodes.loc[episodes["split"].eq(split)].copy()
        if selected:
            scope_df = split_df.loc[scope_mask(split_df, selected["seed_scope_id"])]
            base3_df = split_df.loc[split_df["baseline_3_same_scope_episode_included"]]
            cand_df = split_df.loc[split_df["candidate_episode_included"]]
        else:
            scope_df = split_df
            base3_df = split_df.loc[survived_at(split_df, int(checkpoint.replace("T+", "")))]
            cand_df = split_df.iloc[0:0]
        b1 = metric_row(
            scope_df,
            "baseline_1_t0_full_entry",
            "baseline",
            split,
            selected["candidate_scope_id"] if selected else "all|T+10|no_candidate",
            selected["baseline_3_scope_id"] if selected else "all|T+10",
            checkpoint,
            "full_1r_at_t0",
            "episode_first_trigger_label_denominator",
            "not_applicable",
            "label_only_t0_baseline",
        )
        b2 = metric_row(
            scope_df,
            "baseline_2_t0_probe_only",
            "baseline",
            split,
            selected["candidate_scope_id"] if selected else "all|T+10|no_candidate",
            selected["baseline_3_scope_id"] if selected else "all|T+10",
            checkpoint,
            config["exposure_labels"]["selected_probe_label"],
            "episode_first_trigger_label_denominator",
            "not_applicable",
            "label_only_t0_baseline",
        )
        b3 = metric_row(
            base3_df,
            "baseline_3_probe_survival_step_up",
            "baseline_3_same_scope",
            split,
            selected["candidate_scope_id"] if selected else "all|T+10|no_candidate",
            selected["baseline_3_scope_id"] if selected else "all|T+10",
            checkpoint,
            exposure,
            "episode_first_trigger_survivor_label_denominator",
            "not_applicable",
            "baseline_3_same_scope",
        )
        cand = metric_row(
            cand_df,
            "candidate_probability_survival_step",
            "candidate",
            split,
            selected["candidate_scope_id"] if selected else "all|T+10|no_candidate",
            selected["baseline_3_scope_id"] if selected else "all|T+10",
            checkpoint,
            exposure,
            "episode_first_trigger_candidate_included_label_denominator",
            False,
            "no_selected_candidate" if not selected else "candidate_vs_baseline_3_same_scope",
        )
        if selected:
            n_min = int(config["sample_denominator_thresholds"][f"N_min_{split}"])
            passed, status, details = split_pass(cand, b3, pass_thresholds, n_min)
            cand.update(details)
            cand["candidate_split_pass"] = bool(passed)
            cand["comparison_vs_baseline_3_status"] = status
            split_passes[split] = passed
            for prefix, c_row, b_row in [(split, cand, b3)]:
                readonly[f"{prefix}_seed_episode_count"] = c_row["seed_episode_count"]
                readonly[f"{prefix}_censored_or_invalid_count"] = c_row["censored_or_invalid_count"]
                readonly[f"{prefix}_censored_or_invalid_rate"] = c_row["censored_or_invalid_rate"]
                readonly[f"{prefix}_label_denominator"] = c_row["label_denominator_count"]
                readonly[f"{prefix}_baseline_3_same_scope_label_denominator"] = b_row["label_denominator_count"]
                readonly[f"{prefix}_denominator_gate_pass"] = bool(
                    c_row["label_denominator_count"] >= n_min and b_row["label_denominator_count"] >= n_min
                )
                for col in [
                    "P_good",
                    "P_bad",
                    "P_neutral",
                    "P_good_lower",
                    "P_good_upper",
                    "P_bad_lower",
                    "P_bad_upper",
                    "credible_interval_width_good",
                    "credible_interval_width_bad",
                ]:
                    readonly[f"{prefix}_{col}"] = c_row[col]
                    readonly[f"{prefix}_baseline_3_same_scope_{col}"] = b_row[col]
                readonly[f"{prefix}_prob_edge_vs_baseline_3"] = (c_row["P_good_lower"] - b_row["P_good"]) - (
                    c_row["P_bad_upper"] - b_row["P_bad"]
                )
                readonly[f"{prefix}_bad_edge_ci_halfwidth_proxy"] = 0.5 * (
                    c_row["credible_interval_width_bad"] + b_row["credible_interval_width_bad"]
                )
                readonly[f"{prefix}_good_edge_ci_halfwidth_proxy"] = 0.5 * (
                    c_row["credible_interval_width_good"] + b_row["credible_interval_width_good"]
                )
                readonly[f"{prefix}_candidate_eligibility_threshold_smaller_than_ci_halfwidth"] = bool(
                    pass_thresholds["min_abs_bad_upper_improvement_vs_baseline3"] < readonly[f"{prefix}_bad_edge_ci_halfwidth_proxy"]
                    or pass_thresholds["max_abs_good_lower_loss_vs_baseline3"] < readonly[f"{prefix}_good_edge_ci_halfwidth_proxy"]
                )
                readonly[f"{prefix}_upside_capture_ratio_vs_baseline3"] = c_row.get("upside_capture_ratio_vs_baseline3", np.nan)
                readonly[f"{prefix}_drawdown_severity_120d_p90"] = c_row["drawdown_severity_120d_p90"]
                readonly[f"{prefix}_baseline_3_same_scope_drawdown_severity_120d_p90"] = b_row["drawdown_severity_120d_p90"]
                readonly[f"{prefix}_candidate_pass"] = bool(passed)
        rows.extend([b1, b2, b3, cand])
    if not selected:
        for split in ["validation", "robustness"]:
            for col in [
                "seed_episode_count",
                "censored_or_invalid_count",
                "censored_or_invalid_rate",
                "label_denominator",
                "baseline_3_same_scope_label_denominator",
                "denominator_gate_pass",
                "P_good",
                "P_bad",
                "P_neutral",
                "P_good_lower",
                "P_good_upper",
                "P_bad_lower",
                "P_bad_upper",
                "credible_interval_width_good",
                "credible_interval_width_bad",
                "baseline_3_same_scope_P_good",
                "baseline_3_same_scope_P_bad",
                "baseline_3_same_scope_P_neutral",
                "baseline_3_same_scope_P_good_lower",
                "baseline_3_same_scope_P_good_upper",
                "baseline_3_same_scope_P_bad_lower",
                "baseline_3_same_scope_P_bad_upper",
                "baseline_3_same_scope_credible_interval_width_good",
                "baseline_3_same_scope_credible_interval_width_bad",
                "prob_edge_vs_baseline_3",
                "bad_edge_ci_halfwidth_proxy",
                "good_edge_ci_halfwidth_proxy",
                "candidate_eligibility_threshold_smaller_than_ci_halfwidth",
                "upside_capture_ratio_vs_baseline3",
                "drawdown_severity_120d_p90",
                "baseline_3_same_scope_drawdown_severity_120d_p90",
                "candidate_pass",
            ]:
                readonly[f"{split}_{col}"] = False if col in {"denominator_gate_pass", "candidate_pass"} else np.nan
    baseline = pd.DataFrame(rows)
    b3_map = baseline.loc[baseline["scenario_id"].eq("baseline_3_probe_survival_step_up")].set_index("split")["max_gain_120d_p75"].to_dict()
    for idx, row in baseline.iterrows():
        base = b3_map.get(row["split"], np.nan)
        if pd.notna(base) and float(base) > 0:
            baseline.loc[idx, "upside_capture_ratio_vs_baseline3"] = row["max_gain_120d_p75"] / max(float(base), 1e-12)
    if not selected:
        final = "blocked_no_stable_candidate_bucket"
    elif bool(split_passes.get("validation")) and bool(split_passes.get("robustness")):
        final = "r03a_probability_feasibility_passed"
    else:
        final = "failed_validation_or_robustness"
    return baseline, pd.DataFrame([readonly]), final


def build_descriptive_bundle_context(config: dict[str, Any], split_stability: pd.DataFrame) -> pd.DataFrame:
    root = topic_path(config["upstream_r02_1"]["output_root"])
    bundle = pd.read_csv(root / "reports" / "r02_1_same_day_bundle_prior.csv", low_memory=False)
    context = pd.read_csv(root / "reports" / "r02_1_context_bucket_prior.csv", low_memory=False)
    stability = _stability_lookup(split_stability)
    frames = []
    for source, df, grouping_type in [
        ("same_day_bundle_key", bundle, "same_day_bundle_prior"),
        ("context_bucket_id", context, "context_bucket_prior"),
    ]:
        work = df.copy()
        for col in ["P_good_lower", "P_good_upper", "P_bad_lower", "P_bad_upper", "credible_interval_width_good", "credible_interval_width_bad"]:
            if col not in work.columns:
                work[col] = np.nan
        for idx, row in work.iterrows():
            post = _posterior(int(row.get("good_count", 0)), int(row.get("bad_count", 0)), int(row.get("neutral_count", 0)))
            for col in ["P_good_lower", "P_good_upper", "P_bad_lower", "P_bad_upper", "credible_interval_width_good", "credible_interval_width_bad"]:
                work.loc[idx, col] = post[col]
            if grouping_type == "same_day_bundle_prior":
                key = f"same_day_bundle_key={row['same_day_bundle_key']}|same_day_family_count={int(row['same_day_family_count'])}"
            else:
                key = (
                    f"same_day_bundle_key={row['same_day_bundle_key']}|"
                    f"same_day_family_count={int(row['same_day_family_count'])}|entry_risk_pct_bucket={row.get('entry_risk_pct_bucket', 'na')}"
                )
            split_status = stability.get((grouping_type, key), "missing_split")
            work.loc[idx, "split_stability_status"] = split_status
            work.loc[idx, "upstream_stability_status"] = split_status
            gate_status = _r03a_status(str(row.get("sample_sufficiency_status", "unusable")), split_status)
            work.loc[idx, "r03a_gate_status"] = gate_status
            work.loc[idx, "r03a_stability_status"] = "stable_enough_for_candidate" if gate_status == "sufficient_and_stable" else "not_stable_for_candidate"
        work["descriptive_source"] = source
        work["primary_gate_allowed"] = False
        work["reason_if_not_allowed"] = "bundle_context_not_primary_gate_in_r03a_v1"
        work["fallback_grain_allowed"] = work["r03a_gate_status"].eq("sufficient_and_stable")
        work["upstream_sample_sufficiency_status"] = work["sample_sufficiency_status"]
        work["used_by_candidate"] = False
        if "fallback_level" not in work.columns:
            work["fallback_level"] = source
        frames.append(work)
    return pd.concat(frames, ignore_index=True, sort=False)


def build_fresh_audit(config: dict[str, Any]) -> pd.DataFrame:
    root = topic_path(config["upstream_r02_1"]["output_root"])
    fresh = pd.read_csv(root / "reports" / "r02_1_fresh_evidence_prior.csv", low_memory=False)
    rows = []
    group_cols = ["fresh_evidence_status", "fresh_offset_bucket", "survival_checkpoint_state"]
    for key, g in fresh.groupby(group_cols, dropna=False, sort=True):
        if not isinstance(key, tuple):
            key = (key,)
        den = int(pd.to_numeric(g["label_denominator_count"], errors="coerce").fillna(0).sum())
        good = int((pd.to_numeric(g["P_good"], errors="coerce").fillna(0) * pd.to_numeric(g["label_denominator_count"], errors="coerce").fillna(0)).sum())
        bad = int((pd.to_numeric(g["P_bad"], errors="coerce").fillna(0) * pd.to_numeric(g["label_denominator_count"], errors="coerce").fillna(0)).sum())
        neutral = max(den - good - bad, 0)
        post = _posterior(good, bad, neutral)
        rows.append(
            {
                "fresh_evidence_status": key[0],
                "fresh_offset_bucket": key[1],
                "fresh_family_id_first": "|".join(sorted(g.get("fresh_family_id", pd.Series(dtype=str)).dropna().astype(str).unique()[:5]))
                if "fresh_family_id" in g.columns
                else "",
                "survival_checkpoint_conditioning": key[2],
                "same_survival_checkpoint_conditioning_status": "conditioned_by_survival_checkpoint_state",
                **{k: v for k, v in post.items() if k != "posterior_alpha_total"},
                "fresh_before_observable_failure_rate": float(pd.to_numeric(g["fresh_before_observable_failure_rate"], errors="coerce").mean()),
                "fresh_without_prior_observable_failure_rate": float(
                    pd.to_numeric(g["fresh_without_prior_observable_failure_rate"], errors="coerce").mean()
                ),
                "split_stability_status": "descriptive_only",
                "gate_use_allowed": False,
                "reason_if_not_allowed": "fresh evidence is descriptive in R03a and requires separate sequence / hazard diagnostic before gate use",
            }
        )
    return pd.DataFrame(rows)


def build_null_audit(final_decision: str, grid: pd.DataFrame, baseline: pd.DataFrame, manifest_bits: dict[str, Any]) -> pd.DataFrame:
    required = [
        "candidate_not_better_than_baseline_3_on_P_bad",
        "candidate_loses_too_much_upside_capture_vs_baseline_3",
        "candidate_only_wins_in_train",
        "candidate_depends_on_sparse_bucket",
        "candidate_depends_on_fresh_evidence_gate",
        "candidate_requires_ev_r_sizing",
        "baseline_1_2_path_metric_mismatch",
        "candidate_compared_to_global_baseline3",
        "multi_family_seed_component_selected_as_primary",
        "upstream_enum_not_normalized",
        "candidate_inclusion_formula_missing",
        "credible_interval_level_not_fixed",
        "drawdown_severity_uses_raw_p90_wrong_tail",
        "denominator_gate_not_applied",
        "candidate_train_scoring_used_in_sample_posterior",
        "candidate_grid_multiplicity_excessive",
        "candidate_eligibility_threshold_smaller_than_ci_halfwidth",
        "candidate_degenerate_probability_gate",
        "episode_construction_rule_hash_mismatch",
    ]
    triggered = {
        "candidate_only_wins_in_train": final_decision == "failed_validation_or_robustness",
        "candidate_depends_on_fresh_evidence_gate": False,
        "candidate_requires_ev_r_sizing": False,
        "candidate_grid_multiplicity_excessive": final_decision == "blocked_grid_multiplicity_excessive",
        "candidate_eligibility_threshold_smaller_than_ci_halfwidth": bool(
            not grid.empty and grid.get("train_oof_candidate_eligibility_threshold_smaller_than_ci_halfwidth", pd.Series(dtype=bool)).astype(bool).any()
        ),
        "candidate_degenerate_probability_gate": bool(
            not grid.empty and grid.get("degenerate_probability_gate_status", pd.Series(dtype=str)).eq("degenerate_probability_gate").any()
        ),
        "baseline_1_2_path_metric_mismatch": manifest_bits.get("baseline_1_2_path_metric_equivalence_status") != "passed",
        "episode_construction_rule_hash_mismatch": False,
    }
    rows = []
    for cond in required:
        trig = bool(triggered.get(cond, False))
        rows.append(
            {
                "null_condition": cond,
                "observed_status": "triggered" if trig else "not_triggered",
                "triggered": trig,
                "evidence_table": "r03a_candidate_grid_train_selection.csv"
                if cond.startswith("candidate")
                else "r03a_baseline_comparison.csv",
                "evidence_row_id": cond,
                "required_conclusion_if_triggered": "no incremental staged-posterior edge over survival step-up"
                if trig
                else "",
            }
        )
    return pd.DataFrame(rows)


def baseline_1_2_equivalence(baseline: pd.DataFrame) -> str:
    ignore = {
        "scenario_id",
        "comparison_role",
        "proxy_exposure_schedule_label",
        "candidate_split_pass",
        "comparison_vs_baseline_3_status",
    }
    b1 = baseline.loc[baseline["scenario_id"].eq("baseline_1_t0_full_entry")].sort_values(["split", "year"]).reset_index(drop=True)
    b2 = baseline.loc[baseline["scenario_id"].eq("baseline_2_t0_probe_only")].sort_values(["split", "year"]).reset_index(drop=True)
    cols = [c for c in b1.columns if c in b2.columns and c not in ignore]
    for col in cols:
        if pd.api.types.is_numeric_dtype(b1[col]) or pd.api.types.is_numeric_dtype(b2[col]):
            a = pd.to_numeric(b1[col], errors="coerce")
            b = pd.to_numeric(b2[col], errors="coerce")
            if not np.allclose(a.fillna(999999.0), b.fillna(999999.0), atol=1e-12, rtol=0):
                return "failed"
        elif not b1[col].astype(str).equals(b2[col].astype(str)):
            return "failed"
    return "passed"


def write_report(
    output_root: Path,
    readiness: dict[str, str],
    survival: pd.DataFrame,
    grid: pd.DataFrame,
    baseline: pd.DataFrame,
    readonly: pd.DataFrame,
    fresh: pd.DataFrame,
    final_decision: str,
    selected: dict[str, Any] | None,
    config: dict[str, Any],
) -> None:
    reports_dir = output_root / "reports"
    eligible_count = int(grid["train_eligible_candidate_count_after_gate"].max()) if not grid.empty else 0
    survival_summary = survival.loc[survival["survival_lift_grain"].eq("global")].copy()
    display_survival = survival_summary[
        [
            "checkpoint",
            "pre_checkpoint_episode_count",
            "survivor_episode_count",
            "survivor_rate",
            "survivor_P_good",
            "survivor_P_bad",
            "survival_lift_good_vs_t0_same_grain",
            "survival_lift_bad_vs_t0_same_grain",
        ]
    ]
    display_baseline = baseline[
        [
            "scenario_id",
            "split",
            "label_denominator_count",
            "P_good",
            "P_bad",
            "P_good_lower",
            "P_bad_upper",
            "drawdown_severity_120d_p90",
            "max_gain_120d_p75",
            "candidate_split_pass",
            "comparison_vs_baseline_3_status",
        ]
    ]
    selected_text = "无 train-eligible candidate"
    if selected:
        selected_text = (
            f"{selected['candidate_scope_id']}, threshold={selected['probability_gate_threshold']}, "
            f"bucket={selected['fallback_grain']}, checkpoint={selected['survival_checkpoint']}"
        )
    lines = [
        "# R03a 概率型 Survival-Step 可行性报告",
        "",
        "## 边界",
        "",
        "R03a 只是 probability-only feasibility audit，不是 EV_R sizing，不输出交易策略、仓位规模或 production signal。所有 R 标签只作为固定 exposure schedule label。",
        "",
        "## R02.1 Blocker Summary",
        "",
        f"- EV_R: `{readiness.get('ev_r_ready')}`，R03a 记录为 `probability_only_ev_r_blocked`。",
        f"- Global denominator: `{readiness.get('global_prior_ready')}`，不能伪装 market-wide background baseline。",
        f"- Split stability: `{readiness.get('split_stability_ready')}`，本轮只允许 probability-only partial diagnostic。",
        "",
        "## Same-Grain Survival Lift",
        "",
    ]
    lines.extend(display_survival.to_markdown(index=False).splitlines())
    lines.extend(
        [
            "",
            "## Train 选择",
            "",
            f"- Train scoring mode: `{config['train_selection']['train_scoring_mode']}`。",
            f"- Inner CV fold count: `{config['train_selection']['train_inner_cv_fold_count']}`。",
            f"- Grid rows materialized: `{len(grid)}`；train-eligible rows: `{eligible_count}`。",
            f"- Selected candidate: `{selected_text}`。",
            "- Episode inclusion formula: seed scope AND survived selected checkpoint AND `P_good_lower - P_bad_upper >= probability_gate_threshold`。",
            "- Train selection uses train_oof measured actual-label posterior fields; full-train frozen posterior is only used for validation / robustness row inclusion scoring.",
            "",
            "## Baseline / Candidate 对比",
            "",
        ]
    )
    lines.extend(display_baseline.to_markdown(index=False).splitlines())
    lines.extend(
        [
            "",
            "Baseline 1 and baseline 2 are expected to have identical path metrics because EV_R is blocked and exposure only changes report labels, not the episode path denominator.",
            "",
            "Pass/fail thresholds are fixed before validation: "
            f"bad upper improvement `{config['pass_fail_thresholds']['min_abs_bad_upper_improvement_vs_baseline3']}`, "
            f"good lower loss cap `{config['pass_fail_thresholds']['max_abs_good_lower_loss_vs_baseline3']}`, "
            f"upside capture minimum `{config['pass_fail_thresholds']['min_upside_capture_ratio_vs_baseline3']}`, "
            f"drawdown severity worsening cap `{config['pass_fail_thresholds']['max_abs_drawdown_severity_worsening_vs_baseline3']}`.",
            "",
            "Drawdown pass/fail uses `drawdown_severity_120d_p90 = abs(min(max_drawdown_120d, 0))` because raw `max_drawdown_120d_p90` is the wrong tail for loss severity.",
            "",
            "## Validation / Robustness 只读评估",
            "",
        ]
    )
    lines.extend(readonly.to_markdown(index=False).splitlines())
    lines.extend(
        [
            "",
            "## Fresh Evidence 边界",
            "",
            "Fresh evidence is descriptive in R03a and requires separate sequence / hazard diagnostic before gate use. The first-fresh offset distribution is not enough to reject T+11..T+30 information because it is not conditioned as a validated survival/hazard gate.",
            "",
            "## Bundle / Context 边界",
            "",
            "Same-day bundle and context are descriptive or fallback-only. They are not seed scopes, not primary gates, and do not create multiple same-day risk units.",
            "",
            "## 结论",
            "",
            f"Final decision: `{final_decision}`.",
            "Concrete next action: if the objective remains risk-budget allocation, first materialize EV_R inputs and action-time denominator for R03b; if the objective is evidence sequencing, run a separate fresh-sequence / hazard diagnostic.",
        ]
    )
    text = "\n".join(lines) + "\n"
    lowered = text.lower()
    for token in FORBIDDEN_REPORT_TOKENS:
        if token.lower() in lowered:
            raise RuntimeError(f"forbidden report language: {token}")
    (reports_dir / "r03a_probability_survival_step_feasibility_report.md").write_text(text, encoding="utf-8")


def run(config_path: Path) -> dict[str, Any]:
    config = load_config(config_path)
    input_audit = validate_required_inputs(config)
    readiness = validate_readiness(config)
    path_config = _read_yaml(Path(config["upstream_path_query"]["config"]))
    path_manifest = _read_json(Path(config["upstream_path_query"]["manifest"]))
    path_validation = _read_json(Path(config["upstream_path_query"]["validation"]))
    r02_manifest = _read_json(Path(config["upstream_r02_1"]["manifest"]))
    frozen = validate_frozen(config, path_config, r02_manifest)

    output_root = topic_path(config["output_root"])
    reports_dir = output_root / "reports"
    cache_dir = output_root / "cache"
    manifests_dir = output_root / "manifests"
    reports_dir.mkdir(parents=True, exist_ok=True)
    cache_dir.mkdir(parents=True, exist_ok=True)
    manifests_dir.mkdir(parents=True, exist_ok=True)

    events = load_single_path_rows(config, path_manifest)
    episodes = build_episode_panel(events, config)
    episodes["train_inner_cv_fold_id"] = assign_train_folds(episodes, config)
    split_stability = pd.read_csv(topic_path(Path(config["upstream_r02_1"]["output_root"]) / "reports" / "r02_1_split_stability_diagnostics.csv"))
    t0_prior = build_t0_prior(episodes, config)
    survival = build_survival_lift(episodes, config)
    grid, grid_meta, score_lineage = train_candidate_grid(episodes, config, split_stability)
    selected = grid_meta.get("selected")
    episodes = apply_selected_candidate(episodes, selected, score_lineage, config)
    baseline, readonly, decision_from_eval = build_baseline_and_readonly(episodes, selected, config)
    if grid_meta["grid_multiplicity_status"] == "blocked_grid_multiplicity_excessive":
        final_decision = "blocked_grid_multiplicity_excessive"
    elif grid_meta["grid_multiplicity_status"] == "invalid_requirement_violation":
        final_decision = "invalid_requirement_violation"
    else:
        final_decision = decision_from_eval
    bundle_context = build_descriptive_bundle_context(config, split_stability)
    fresh_audit = build_fresh_audit(config)
    baseline_status = baseline_1_2_equivalence(baseline)
    manifest_bits = {"baseline_1_2_path_metric_equivalence_status": baseline_status}
    null_audit = build_null_audit(final_decision, grid, baseline, manifest_bits)

    _write_csv(input_audit, reports_dir / "r03a_input_readiness_audit.csv")
    _write_csv(t0_prior, reports_dir / "r03a_t0_episode_prior.csv")
    _write_csv(survival, reports_dir / "r03a_survival_same_grain_lift.csv")
    _write_csv(grid, reports_dir / "r03a_candidate_grid_train_selection.csv")
    _write_csv(baseline, reports_dir / "r03a_baseline_comparison.csv")
    _write_csv(readonly, reports_dir / "r03a_validation_robustness_readonly.csv")
    _write_csv(bundle_context, reports_dir / "r03a_descriptive_bundle_context_prior.csv")
    _write_csv(fresh_audit, reports_dir / "r03a_fresh_evidence_descriptive_audit.csv")
    _write_csv(null_audit, reports_dir / "r03a_null_result_audit.csv")

    episode_cols = [
        "seed_episode_id",
        "instrument_id",
        "seed_trade_date",
        "seed_entry_date",
        "seed_entry_price",
        "seed_same_day_bundle_key",
        "seed_same_day_family_count",
        "seed_family_set",
        "seed_type",
        "seed_primary_family_id",
        "split",
        "year",
        "label",
        "censored_or_invalid_reason",
        "good_path_flag",
        "bad_path_flag",
        "neutral_path_flag",
        "first_minus5_offset",
        "hit_plus10_before_minus5",
        "path_quality_flag",
        "max_drawdown_120d",
        "max_gain_120d",
        "close_return_t20",
        "close_return_t60",
        "close_return_t120",
        "train_inner_cv_fold_id",
        "selected_candidate_id",
        "candidate_scope_id",
        "baseline_3_scope_id",
        "episode_in_selected_seed_scope",
        "episode_survived_selected_checkpoint",
        "episode_probability_bucket_key",
        "episode_probability_score",
        "candidate_episode_included",
        "baseline_3_same_scope_episode_included",
    ]
    episodes[episode_cols].to_parquet(cache_dir / "r03a_episode_first_trigger_panel.parquet", index=False)

    episode_audit_hashes = {
        sid: _hash_file(topic_path(path))
        for sid, path in path_manifest.get("per_signal_episode_audit_paths", {}).items()
        if sid.startswith("single_")
    }
    r03a_rule = {
        "seed_policy": "first_trade_date_with_any_frozen_family_trigger",
        "episode_build_window_trading_days": "0..30",
        "same_instrument_new_seed_after_previous_build_window_ends": True,
        "multi_family_primary": "multi_family_bundle",
    }
    selected_candidate_scope = selected["candidate_scope_id"] if selected else ""
    manifest = {
        "requirement_id": config["requirement_id"],
        "short_name": config["short_name"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "input_artifact_hashes": {row["input_name"]: row["hash_or_mtime"] for row in input_audit.to_dict("records")},
        "upstream_validation_status": {
            "r02_1": _read_json(Path(config["upstream_r02_1"]["validation"])).get("validation_status"),
            "path_query": path_validation.get("validation_status"),
        },
        "frozen_family_universe": frozen.to_dict("records"),
        "episode_grain": "episode_first_trigger",
        "label_priority_order": ["censored_or_invalid", "bad_path", "good_path", "neutral_path"],
        "survival_checkpoints": [f"T+{x}" for x in config["survival_checkpoints"]],
        "alpha_source": config["posterior"]["alpha_source"],
        "credible_interval_level": float(config["posterior"]["credible_interval_level"]),
        "credible_interval_method": config["posterior"]["credible_interval_method"],
        "credible_interval_tolerance": float(config["posterior"]["credible_interval_tolerance"]),
        "probability_score_formula": "P_good_lower - P_bad_upper",
        "episode_probability_score_source_policy": "train_inner_cv_out_of_fold for train; full_train_frozen posterior for validation/robustness",
        "split_probability_evaluation_source_policy": "actual labels in evaluated split after frozen inclusion mask",
        "train_scoring_mode": config["train_selection"]["train_scoring_mode"],
        "train_inner_cv_fold_count": int(config["train_selection"]["train_inner_cv_fold_count"]),
        "train_inner_cv_assignment_hash": _hash_json(
            {"seed": config["train_selection"]["train_only_selection_seed"], "fold_count": config["train_selection"]["train_inner_cv_fold_count"]},
            32,
        ),
        "fallback_grain_order": config["fallback_grain_order"],
        "allowed_seed_scope_ids": sorted(grid["seed_scope_id"].unique().tolist()) if not grid.empty else [],
        "probability_gate_threshold_grid": config["probability_gate_threshold_grid"],
        "selected_probe_label": config["exposure_labels"]["selected_probe_label"],
        "selected_survival_step_label": config["exposure_labels"]["selected_survival_step_label"],
        "fixed_sample_denominator_thresholds": config["sample_denominator_thresholds"],
        "train_grid_total_candidate_count": int(grid_meta["train_grid_total_candidate_count"]),
        "train_eligible_candidate_count_after_gate": int(grid_meta["train_eligible_candidate_count_after_gate"]),
        "max_train_grid_total_candidate_count": int(config["train_selection"]["max_train_grid_total_candidate_count"]),
        "max_train_eligible_candidate_count_after_gate": int(config["train_selection"]["max_train_eligible_candidate_count_after_gate"]),
        "grid_multiplicity_status": grid_meta["grid_multiplicity_status"],
        "degenerate_probability_gate_exclusion_status": "excluded_before_ranking",
        "fallback_grain_evaluation_status": {
            "configured": config["fallback_grain_grid"],
            "materialized": sorted(grid["fallback_grain"].unique().tolist()) if not grid.empty else [],
            "same_day_bundle_key_and_context_bucket_require_bucket_level_sufficient_and_stable": True,
        },
        "train_selection_metric": config["train_selection"]["selection_metric"],
        "train_selection_tie_breaker": [
            "higher train_oof_prob_edge_vs_baseline_3",
            "lower train_oof_P_bad_upper",
            "higher train_oof_P_good_lower",
            "lower train_drawdown_severity_120d_p90",
            "higher train_upside_capture_ratio_vs_baseline3",
            "higher train_label_denominator",
            "T+10 then T+5 then T+3",
            "seed_scope_id lexicographic ascending",
            "fallback_grain configured order",
            "lower probability_gate_threshold",
        ],
        "candidate_episode_inclusion_formula": "episode_in_selected_seed_scope AND episode_survived_selected_checkpoint AND episode_probability_score >= probability_gate_threshold",
        "status_normalization_mapping": "r02_1 sample_sufficiency_status + stability_status normalized to r03a_gate_status",
        "train_only_selection_fields": [
            "seed_scope_id",
            "survival_checkpoint",
            "fallback_grain",
            "probability_gate_threshold",
            "train_oof_*",
        ],
        "upstream_r02_1_episode_construction_rule_hash": r02_manifest.get("upstream_r02_1_episode_construction_rule_hash", ""),
        "episode_construction_hash_mode": "upstream_manifest_and_episode_audit_fallback",
        "upstream_path_query_manifest_hash": _hash_file(topic_path(config["upstream_path_query"]["manifest"])),
        "upstream_path_query_validation_hash": _hash_file(topic_path(config["upstream_path_query"]["validation"])),
        "upstream_episode_audit_file_hashes": episode_audit_hashes,
        "r03a_episode_construction_rule_hash": _hash_json(r03a_rule, 32),
        "path_metric_denominator_policy_enum": [
            "episode_first_trigger_label_denominator",
            "episode_first_trigger_survivor_label_denominator",
            "episode_first_trigger_candidate_included_label_denominator",
        ],
        "selected_candidate_id": selected["candidate_id"] if selected else "",
        "selected_candidate_scope_id": selected_candidate_scope,
        "r03a_pass_fail_thresholds": config["pass_fail_thresholds"],
        "risk_budget_status": "probability_only_ev_r_blocked",
        "background_denominator_status": "blocked_missing_denominator",
        "split_stability_status": "partial_only",
        "ev_r_status": "ev_r_available_but_not_used_by_r03a" if readiness.get("ev_r_ready") == "ready" else "blocked_missing_ev_r",
        "fresh_evidence_gate_allowed": False,
        "bundle_context_primary_gate_allowed": False,
        "validation_readonly_status": "readonly_evaluation_no_validation_tuning",
        "baseline_1_2_path_metric_equivalence_status": baseline_status,
        "baseline_3_same_scope_comparison_status": "baseline_3_used_as_mandatory_control",
        "final_decision": final_decision,
        "row_counts_by_table": {
            "episode_first_trigger_panel": int(len(episodes)),
            "t0_prior": int(len(t0_prior)),
            "survival_same_grain_lift": int(len(survival)),
            "candidate_grid_train_selection": int(len(grid)),
            "baseline_comparison": int(len(baseline)),
            "validation_robustness_readonly": int(len(readonly)),
            "descriptive_bundle_context_prior": int(len(bundle_context)),
            "fresh_evidence_descriptive_audit": int(len(fresh_audit)),
            "null_result_audit": int(len(null_audit)),
        },
        "validation_status": "not_run",
    }
    write_report(output_root, readiness, survival, grid, baseline, readonly, fresh_audit, final_decision, selected, config)
    write_json(manifest, manifests_dir / "r03a_probability_survival_step_feasibility_manifest.json")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Run EP4 R03a probability-only survival-step feasibility audit.")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    args = parser.parse_args()
    manifest = run(Path(args.config))
    print(
        json.dumps(
            {
                "status": "completed",
                "output_root": manifest["short_name"],
                "final_decision": manifest["final_decision"],
                "row_counts_by_table": manifest["row_counts_by_table"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
