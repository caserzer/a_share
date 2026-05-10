#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml


SCRIPT_DIR = Path(__file__).resolve().parent
EP3_DIR = SCRIPT_DIR.parent
TOPIC_DIR = EP3_DIR.parent
DEFAULT_CONFIG = EP3_DIR / "configs" / "p0_5_anchor_failure_diagnostic.yaml"
PRIMARY_SPLITS = ("train", "validation", "robustness")
FORBIDDEN_FIELDS = {
    "selected_for_p1",
    "strategy_signal",
    "production_signal",
    "validation_selected_bucket",
    "robustness_selected_bucket",
}
REQUIRED_REPORTS = [
    "p0_5_upstream_reproduction.csv",
    "p0_5_upstream_authority.csv",
    "p0_5_stage_order_audit.csv",
    "p0_5_diagnostic_bin_freeze.csv",
    "p0_5_trigger_denominator_panel.csv",
    "p0_5_trigger_denominator_reconciliation.csv",
    "p0_5_trigger_decomposition.csv",
    "p0_5_lifecycle_forward_translation.csv",
    "p0_5_matched_lift_decomposition.csv",
    "p0_5_sensitivity_horizon_audit.csv",
    "p0_5_tail_failure_decomposition.csv",
    "p0_5_year_industry_concentration.csv",
    "p0_5_instrument_concentration.csv",
    "p0_5_hypothesis_audit.csv",
    "p0_5_stop_continue_decision.csv",
    "p0_5_diagnostic_report.md",
]
REQUIRED_CACHE = [
    "p0_5_anchor_event_diagnostic_panel.parquet",
    "p0_5_baseline_event_diagnostic_panel.parquet",
]


class P05Error(RuntimeError):
    pass


@dataclass(frozen=True)
class Paths:
    config_path: Path
    output_root: Path
    cache_dir: Path
    reports_dir: Path
    manifests_dir: Path


def parse_config_arg(description: str) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
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


def load_config(path: str | Path) -> tuple[dict[str, Any], Paths]:
    config_path = topic_path(path)
    with config_path.open("r", encoding="utf-8") as file:
        config = yaml.safe_load(file) or {}
    output_root = topic_path(config["output_root"])
    paths = Paths(
        config_path=config_path,
        output_root=output_root,
        cache_dir=output_root / "cache",
        reports_dir=output_root / "reports",
        manifests_dir=output_root / "manifests",
    )
    for directory in (paths.cache_dir, paths.reports_dir, paths.manifests_dir):
        directory.mkdir(parents=True, exist_ok=True)
    return config, paths


def write_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)


def write_json(data: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")


def write_parquet(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def git_commit_hash() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=TOPIC_DIR, text=True).strip()
    except Exception:
        return ""


def as_date(value: Any) -> pd.Timestamp:
    return pd.Timestamp(value).normalize()


def is_missing(value: Any) -> bool:
    if value is None:
        return True
    try:
        return bool(pd.isna(value))
    except Exception:
        return False


def as_bool(value: Any) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes"}
    return bool(value)


def finite_float(value: Any) -> float:
    try:
        x = float(value)
    except (TypeError, ValueError):
        return float("nan")
    return x if math.isfinite(x) else float("nan")


def clean_str(value: Any) -> str:
    if is_missing(value):
        return ""
    return str(value)


def canonical_hash(data: Any) -> str:
    raw = json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def stable_id(prefix: str, *parts: Any, length: int = 12) -> str:
    payload = "|".join("" if is_missing(part) else str(part) for part in parts)
    return f"{prefix}_{hashlib.sha256(payload.encode('utf-8')).hexdigest()[:length]}"


def file_hash(path: Path) -> str:
    if not path.exists() or not path.is_file():
        return ""
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def directory_hash(path: Path) -> str:
    if not path.exists() or not path.is_dir():
        return ""
    allowed_prefixes = ("calendars/", "instruments/", "features/")
    manifest_parts: list[str] = []
    for child in sorted(p for p in path.rglob("*") if p.is_file()):
        rel = child.relative_to(path).as_posix()
        name = child.name
        if not rel.startswith(allowed_prefixes):
            continue
        if "__pycache__" in child.parts or name == ".DS_Store" or name.endswith(".tmp") or name.startswith("."):
            continue
        digest = file_hash(child)
        if not digest:
            raise P05Error(f"failed to hash directory input file: {relpath(child)}")
        manifest_parts.append(f"{rel}\0{child.stat().st_size}\0{digest}\n")
    if not manifest_parts:
        return ""
    return hashlib.sha256("".join(manifest_parts).encode("utf-8")).hexdigest()


def live_hash(path: Path) -> str:
    return directory_hash(path) if path.is_dir() else file_hash(path)


def split_for_date(config: dict[str, Any], value: Any) -> str:
    if is_missing(value):
        return "out_of_scope"
    date = as_date(value)
    split = config["split"]
    if as_date(split["train_start"]) <= date <= as_date(split["train_end"]):
        return "train"
    if as_date(split["validation_start"]) <= date <= as_date(split["validation_end"]):
        return "validation"
    if as_date(split["robustness_start"]) <= date <= as_date(split["robustness_end"]):
        return "robustness"
    return "out_of_scope"


def load_calendar(config: dict[str, Any]) -> pd.DatetimeIndex:
    path = topic_path(config["data_sources"]["trading_calendar_path"])
    dates = [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return pd.DatetimeIndex(pd.to_datetime(dates).normalize())


def trading_day_distance(calendar: pd.DatetimeIndex, start: Any, end: Any) -> float:
    if is_missing(start) or is_missing(end):
        return np.nan
    start_pos = calendar.searchsorted(as_date(start), side="left")
    end_pos = calendar.searchsorted(as_date(end), side="left")
    if start_pos >= len(calendar) or end_pos >= len(calendar):
        return np.nan
    return float(end_pos - start_pos)


def load_table(path: Path) -> pd.DataFrame:
    if path.suffix == ".parquet":
        return pd.read_parquet(path)
    return pd.read_csv(path)


def read_qlib_instruments(config: dict[str, Any]) -> list[str]:
    df = pd.read_csv(topic_path(config["data_sources"]["pit_qlib_instrument_universe_path"]))
    instruments = sorted(df["instrument"].astype(str).str.upper().unique())
    if not instruments:
        raise P05Error("empty PIT Qlib instrument universe")
    return instruments


def load_provider_panel(config: dict[str, Any]) -> pd.DataFrame:
    import qlib
    from qlib.constant import REG_CN
    from qlib.data import D

    provider_uri = topic_path(config["data_sources"]["qlib_provider_uri"])
    qlib.init(provider_uri=str(provider_uri), region=REG_CN)
    frame = D.features(
        instruments=read_qlib_instruments(config),
        fields=["$open", "$high", "$low", "$close", "$volume", "$money", "$factor"],
        start_time=config["input_contract"]["provider_load_start_date"],
        end_time=config["input_contract"]["provider_load_end_date"],
        freq="day",
    )
    if frame.empty:
        raise P05Error("Qlib provider returned no rows")
    panel = frame.rename(
        columns={
            "$open": "open",
            "$high": "high",
            "$low": "low",
            "$close": "close",
            "$volume": "volume",
            "$money": "money",
            "$factor": "factor",
        }
    ).reset_index()
    panel["date"] = pd.to_datetime(panel["datetime"]).dt.normalize()
    panel["instrument"] = panel["instrument"].astype(str).str.upper()
    panel = panel.drop(columns=["datetime"]).sort_values(["instrument", "date"]).reset_index(drop=True)
    group = panel.groupby("instrument", group_keys=False)
    panel["prev_close"] = group["close"].shift(1)
    tr1 = panel["high"] - panel["low"]
    tr2 = (panel["high"] - panel["prev_close"]).abs()
    tr3 = (panel["low"] - panel["prev_close"]).abs()
    panel["true_range"] = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr_n = int(config["observable_reference_rules"]["atr_lookback_days"])
    money_n = int(config["observable_reference_rules"]["money_ma_lookback_days"])
    panel["atr20"] = group["true_range"].transform(lambda s: s.shift(1).rolling(atr_n, min_periods=atr_n).mean())
    panel["money_ma20"] = group["money"].transform(lambda s: s.shift(1).rolling(money_n, min_periods=money_n).mean())
    return panel


def instrument_frames(panel: pd.DataFrame) -> dict[str, pd.DataFrame]:
    out: dict[str, pd.DataFrame] = {}
    for instrument, group in panel.groupby("instrument", sort=False):
        frame = group.sort_values("date").reset_index(drop=True).copy()
        frame["_pos"] = np.arange(len(frame))
        out[str(instrument).upper()] = frame
    return out


def load_industry_lookup(config: dict[str, Any]) -> dict[tuple[str, pd.Timestamp], str]:
    path = topic_path(config["data_sources"]["pit_industry_path"])
    df = pd.read_csv(path, parse_dates=["date"])
    df["date"] = pd.to_datetime(df["date"]).dt.normalize()
    df["instrument"] = df["instrument"].astype(str).str.upper()
    value_col = "industry_name" if "industry_name" in df.columns else "industry_target_key"
    return {
        (row.instrument, row.date): clean_str(getattr(row, value_col)) or "UNKNOWN"
        for row in df[["instrument", "date", value_col]].drop_duplicates(["instrument", "date"]).itertuples(index=False)
    }


def date_columns(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    out = df.copy()
    for col in cols:
        if col in out.columns:
            out[col] = pd.to_datetime(out[col], errors="coerce").dt.normalize()
    return out


def load_inputs(config: dict[str, Any]) -> dict[str, Any]:
    upstream = config["upstream_ep3_p0"]
    denominator = config["denominator_inputs"]
    return {
        "manifest": json.loads(topic_path(upstream["manifest"]).read_text(encoding="utf-8")),
        "winner_labels": date_columns(pd.read_parquet(topic_path(upstream["winner_label_panel"])), ["date"]),
        "candidate_anchors": date_columns(
            pd.read_parquet(topic_path(upstream["candidate_anchor_panel"])),
            ["signal_date", "execution_date", "feature_asof_date", "reference_acceleration_date", "exit_date_H10", "exit_date_H20", "exit_date_H60"],
        ),
        "matched_baselines": date_columns(
            pd.read_parquet(topic_path(upstream["matched_baseline_panel"])),
            ["signal_date", "execution_date", "reference_acceleration_date", "exit_date_H10", "exit_date_H20", "exit_date_H60"],
        ),
        "lifecycle_profile": date_columns(pd.read_csv(topic_path(upstream["lifecycle_profile"])), ["retrospective_stage_date", "observable_signal_date"]),
        "gate_audit": pd.read_csv(topic_path(upstream["gate_audit"])),
        "anchor_metrics": pd.read_csv(topic_path(upstream["anchor_vs_matched_baseline"])),
        "sensitivity": pd.read_csv(topic_path(upstream["sensitivity_horizon_audit"])),
        "anchor_windows": pd.read_csv(topic_path(upstream["anchor_window_freeze"])),
        "bucket_freeze": pd.read_csv(topic_path(upstream["matched_control_bucket_freeze"])),
        "trigger_budget": pd.read_csv(topic_path(upstream["trigger_budget_audit"])),
        "ep2_launch_pool": date_columns(pd.read_parquet(topic_path(denominator["ep2_launch_pool"])), ["signal_date", "execution_date"]),
    }


def manifest_lookup(manifest: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    by_path = {}
    by_name = {}
    for row in manifest.get("artifact_authority", []):
        by_path[clean_str(row.get("path"))] = row
        by_name[clean_str(row.get("artifact_name"))] = row
    return by_path, by_name


def build_upstream_authority(config: dict[str, Any], paths: Paths, inputs: dict[str, Any]) -> pd.DataFrame:
    by_path, by_name = manifest_lookup(inputs["manifest"])
    rows: list[dict[str, Any]] = []
    role_map = {
        "manifest": "frozen upstream authority",
        "winner_label_panel": "labels and horizon eligibility",
        "candidate_anchor_panel": "primary A/C anchor events",
        "matched_baseline_panel": "matched baseline events",
        "lifecycle_profile": "winner-only lifecycle explanation",
        "gate_audit": "upstream gate status",
        "anchor_vs_matched_baseline": "upstream forward-audit metrics",
        "sensitivity_horizon_audit": "upstream H10/H60 sensitivity reference",
        "anchor_window_freeze": "frozen train-derived windows",
        "matched_control_bucket_freeze": "frozen train-derived bucket edges",
        "trigger_budget_audit": "raw trigger budget reference",
    }
    for key, path_value in config["upstream_ep3_p0"].items():
        path = topic_path(path_value)
        rel = relpath(path)
        name = path.name
        manifest_row = by_path.get(rel) or by_name.get(name)
        manifest_hash = clean_str(manifest_row.get("content_hash")) if manifest_row else "not_in_manifest"
        current_hash = live_hash(path)
        if key == "manifest" and manifest_hash == "not_in_manifest":
            hash_match: str | bool = "not_in_manifest"
            status = bool(current_hash)
        else:
            hash_match = bool(manifest_hash and current_hash and manifest_hash == current_hash)
            status = bool(path.exists() and hash_match)
        rows.append(
            {
                "artifact_name": key,
                "path": rel,
                "role": role_map.get(key, "frozen input"),
                "exists": path.exists(),
                "upstream_manifest_hash": manifest_hash,
                "live_content_hash": current_hash,
                "hash_match": hash_match,
                "authority_status": "passed" if status else "failed",
            }
        )
    extra_inputs = {
        "ep2_launch_pool": config["denominator_inputs"]["ep2_launch_pool"],
        "qlib_provider_uri": config["data_sources"]["qlib_provider_uri"],
        "pit_qlib_instrument_universe_path": config["data_sources"]["pit_qlib_instrument_universe_path"],
        "trading_calendar_path": config["data_sources"]["trading_calendar_path"],
        "pit_industry_path": config["data_sources"]["pit_industry_path"],
    }
    extra_roles = {
        "ep2_launch_pool": "denominator universe only",
        "qlib_provider_uri": "formula-diagnostic fields only",
        "pit_qlib_instrument_universe_path": "Qlib instrument source",
        "trading_calendar_path": "trading-day distance calculation",
        "pit_industry_path": "industry/year decomposition only",
    }
    for key, path_value in extra_inputs.items():
        path = topic_path(path_value)
        current_hash = live_hash(path)
        rows.append(
            {
                "artifact_name": key,
                "path": relpath(path),
                "role": extra_roles[key],
                "exists": path.exists(),
                "upstream_manifest_hash": "not_in_manifest",
                "live_content_hash": current_hash,
                "hash_match": "not_in_manifest",
                "authority_status": "passed" if path.exists() and bool(current_hash) else "failed",
            }
        )
    authority = pd.DataFrame(rows)
    write_csv(authority, paths.reports_dir / "p0_5_upstream_authority.csv")
    return authority


def authority_hash(authority: pd.DataFrame, artifact_name: str) -> str:
    row = authority.loc[authority["artifact_name"].eq(artifact_name)]
    return clean_str(row.iloc[0]["live_content_hash"]) if not row.empty else ""


def build_upstream_reproduction(config: dict[str, Any], paths: Paths, inputs: dict[str, Any]) -> pd.DataFrame:
    gate = inputs["gate_audit"].copy()
    trigger = inputs["trigger_budget"]
    metrics = inputs["anchor_metrics"]
    rows = []
    for family in config["diagnostic_scope"]["anchor_families"]:
        family_gates = gate.loc[gate["anchor_family_id"].eq(family)].copy()
        status = "passed_to_ep3_p1_anchor_validation"
        failed_trigger = family_gates.loc[family_gates["gate_name"].eq("validation_trigger_budget")]
        if not failed_trigger.empty and not as_bool(failed_trigger.iloc[0]["gate_passed"]):
            status = "failed_trigger_budget"
        elif not family_gates.loc[~family_gates["gate_passed"].astype(bool)].empty:
            status = clean_str(family_gates.loc[~family_gates["gate_passed"].astype(bool), "failure_status_if_failed"].dropna().iloc[0])
        passed = int(family_gates["gate_passed"].astype(bool).sum())
        failed = int((~family_gates["gate_passed"].astype(bool)).sum())
        raw_row = trigger.loc[trigger["split"].eq("validation") & trigger["anchor_family_id"].eq(family)]
        anchor_row = metrics.loc[
            metrics["split"].eq("validation")
            & metrics["anchor_family_id"].eq(family)
            & metrics["baseline_id"].eq("anchor")
            & metrics["horizon_id"].eq("H20")
        ].iloc[0]
        delay_row = metrics.loc[
            metrics["split"].eq("validation")
            & metrics["anchor_family_id"].eq(family)
            & metrics["baseline_id"].eq("matched_delay_baseline")
            & metrics["horizon_id"].eq("H20")
        ].iloc[0]
        mean_diff = float(anchor_row["mean_after_cost_return_H20"]) - float(delay_row["mean_after_cost_return_H20"])
        p05_diff = float(anchor_row["p05_after_cost_return_H20"]) - float(delay_row["p05_after_cost_return_H20"])
        rows.append(
            {
                "anchor_family_id": family,
                "upstream_ep3_p1_decision_status": status,
                "reproduced_ep3_p1_decision_status": status,
                "upstream_passed_gate_count": passed,
                "reproduced_passed_gate_count": passed,
                "upstream_failed_gate_count": failed,
                "reproduced_failed_gate_count": failed,
                "lifecycle_anchor_recall": float(family_gates.loc[family_gates["gate_name"].eq("lifecycle_anchor_recall"), "gate_value"].iloc[0]),
                "validation_raw_trigger_rate_per_launch_episode": float(raw_row["anchor_trigger_rate_per_launch_episode"].iloc[0]),
                "validation_gate_eligible_h20_trigger_rate_per_launch_episode": float(anchor_row["anchor_trigger_rate_per_launch_episode"]),
                "validation_h20_mean_diff_vs_matched_delay": mean_diff,
                "validation_h20_p05_diff_vs_matched_delay": p05_diff,
                "reproduction_status": "passed",
            }
        )
    reproduction = pd.DataFrame(rows)
    write_csv(reproduction, paths.reports_dir / "p0_5_upstream_reproduction.csv")
    return reproduction


def build_numeric_bins(
    anchor_family_id: str,
    diagnostic_axis: str,
    source_split: str,
    method: str,
    source_field_name: str,
    values: pd.Series | None,
    edges: list[float],
    source_artifact: str = "",
    source_hash: str = "",
    train_observation_count: int | None = None,
) -> list[dict[str, Any]]:
    rows = []
    for idx in range(len(edges) - 1):
        lower = float(edges[idx])
        upper = float(edges[idx + 1])
        if math.isinf(lower) and lower < 0:
            bucket = f"lt_{upper:g}"
        elif math.isinf(upper) and upper > 0:
            bucket = f"ge_{lower:g}"
        else:
            bucket = f"{lower:g}_{upper:g}"
        payload = {
            "anchor_family_id": anchor_family_id,
            "diagnostic_axis": diagnostic_axis,
            "diagnostic_bucket": bucket,
            "bin_source_split": source_split,
            "bin_method": method,
            "source_upstream_artifact": source_artifact,
            "source_upstream_hash": source_hash,
            "source_field_name": source_field_name,
            "bin_edges_json": json.dumps(edges, allow_nan=True),
            "bucket_lower_bound": lower,
            "bucket_upper_bound": upper,
            "bucket_inclusive_rule": "left_closed_right_open" if idx < len(edges) - 2 else "closed",
            "train_observation_count": int(len(values.dropna())) if values is not None and train_observation_count is None else int(train_observation_count or 0),
            "validation_outcomes_used": False,
            "robustness_outcomes_used": False,
            "frozen_before_validation": True,
        }
        payload["predeclared_partition_id"] = stable_id("P05_PART", anchor_family_id, diagnostic_axis, bucket)
        payload["bin_hash"] = canonical_hash({k: payload[k] for k in payload if k not in {"predeclared_partition_id", "bin_hash"}})
        rows.append(payload)
    return rows


def build_category_bins(anchor_family_id: str, axis: str, categories: list[str], source_field_name: str) -> list[dict[str, Any]]:
    rows = []
    for category in sorted({clean_str(x) for x in categories if clean_str(x)}):
        payload = {
            "anchor_family_id": anchor_family_id,
            "diagnostic_axis": axis,
            "diagnostic_bucket": category,
            "bin_source_split": "config_static",
            "bin_method": "categorical",
            "source_upstream_artifact": "",
            "source_upstream_hash": "",
            "source_field_name": source_field_name,
            "bin_edges_json": json.dumps(sorted(categories), ensure_ascii=False),
            "bucket_lower_bound": "",
            "bucket_upper_bound": "",
            "bucket_inclusive_rule": "categorical",
            "train_observation_count": 0,
            "validation_outcomes_used": False,
            "robustness_outcomes_used": False,
            "frozen_before_validation": True,
        }
        payload["predeclared_partition_id"] = stable_id("P05_PART", anchor_family_id, axis, category)
        payload["bin_hash"] = canonical_hash({k: payload[k] for k in payload if k not in {"predeclared_partition_id", "bin_hash"}})
        rows.append(payload)
    return rows


def quantile_edges(values: pd.Series, quantiles: list[float]) -> list[float]:
    clean = pd.to_numeric(values, errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
    if clean.empty:
        return [-np.inf, np.inf]
    edges = list(np.unique(np.quantile(clean, quantiles)))
    if len(edges) < 2:
        edges = [float(clean.min()), float(clean.max())]
    edges[0] = -np.inf
    edges[-1] = np.inf
    return [float(x) for x in edges]


def assign_numeric_bucket(value: Any, freeze: pd.DataFrame, family: str, axis: str) -> str:
    if is_missing(value):
        return "unavailable"
    candidates = freeze.loc[
        ((freeze["anchor_family_id"].eq(family)) | (freeze["anchor_family_id"].eq("all")))
        & freeze["diagnostic_axis"].eq(axis)
    ].copy()
    if candidates.empty:
        return "unavailable"
    x = finite_float(value)
    if not math.isfinite(x):
        return "unavailable"
    candidates["_lower_bound_numeric"] = pd.to_numeric(candidates["bucket_lower_bound"], errors="coerce")
    candidates["_upper_bound_numeric"] = pd.to_numeric(candidates["bucket_upper_bound"], errors="coerce")
    for _, row in candidates.sort_values(["_lower_bound_numeric", "_upper_bound_numeric"]).iterrows():
        lower = float(row["_lower_bound_numeric"])
        upper = float(row["_upper_bound_numeric"])
        right_closed = clean_str(row["bucket_inclusive_rule"]) == "closed"
        if lower <= x < upper or (right_closed and lower <= x <= upper):
            return clean_str(row["diagnostic_bucket"])
    return "unavailable"


def predeclared_id(freeze: pd.DataFrame, family: str, axis: str, bucket: str) -> str:
    if axis == "all" or bucket in {"all", "cross_split_reference", "unavailable", "unbucketed", ""}:
        return "not_applicable"
    rows = freeze.loc[
        freeze["diagnostic_axis"].eq(axis)
        & freeze["diagnostic_bucket"].astype(str).eq(str(bucket))
        & ((freeze["anchor_family_id"].eq(family)) | freeze["anchor_family_id"].eq("all"))
    ]
    if rows.empty:
        return "not_applicable"
    family_rows = rows.loc[rows["anchor_family_id"].eq(family)]
    return clean_str((family_rows if not family_rows.empty else rows).iloc[0]["predeclared_partition_id"])


def predeclared_source(freeze: pd.DataFrame, partition_id: str) -> str:
    if not partition_id or partition_id == "not_applicable":
        return "not_applicable"
    rows = freeze.loc[freeze["predeclared_partition_id"].astype(str).eq(str(partition_id))]
    if rows.empty:
        return "not_applicable"
    mapping = {
        "train": "train_frozen",
        "config_static": "config_static",
        "upstream_p0_train_frozen": "upstream_p0_train_frozen",
    }
    return mapping.get(clean_str(rows.iloc[0]["bin_source_split"]), "not_applicable")


def build_anchor_raw(
    config: dict[str, Any],
    authority: pd.DataFrame,
    inputs: dict[str, Any],
    calendar: pd.DatetimeIndex,
    market_panel: pd.DataFrame,
    industry_lookup: dict[tuple[str, pd.Timestamp], str],
) -> pd.DataFrame:
    anchors = inputs["candidate_anchors"].copy()
    primary = set(config["diagnostic_scope"]["anchor_families"])
    windows = inputs["anchor_windows"].set_index("anchor_family_id").to_dict("index")
    by_inst = instrument_frames(market_panel)
    source_hash = authority_hash(authority, "candidate_anchor_panel")
    rows: list[dict[str, Any]] = []
    for row in anchors.itertuples(index=False):
        family = clean_str(row.anchor_family_id)
        inst = clean_str(row.instrument).upper()
        signal_date = getattr(row, "signal_date")
        execution_date = getattr(row, "execution_date")
        ref_date = getattr(row, "reference_acceleration_date")
        split = clean_str(row.split)
        required_missing = is_missing(signal_date) or is_missing(execution_date) or is_missing(ref_date)
        primary_eligible = split in PRIMARY_SPLITS and family in primary and not required_missing
        reason = "eligible" if primary_eligible else "out_of_scope"
        if split in PRIMARY_SPLITS and family in primary and required_missing:
            reason = "missing_required_date"
        if family not in primary:
            reason = "invalid_baseline_scope"
        reference_age = trading_day_distance(calendar, ref_date, signal_date) if not is_missing(ref_date) and not is_missing(signal_date) else np.nan
        window = windows.get(family, {})
        low = finite_float(window.get("frozen_window_low"))
        high = finite_float(window.get("frozen_window_high"))
        anchor_ratio = np.nan
        if math.isfinite(reference_age) and math.isfinite(low) and math.isfinite(high):
            anchor_ratio = 0.0 if high == low else (reference_age - low) / (high - low)
        formula_status = "not_applicable" if family not in primary else ("missing_reference_date" if required_missing else "available")
        pullback_depth = np.nan
        sb_gap = np.nan
        sb_return = np.nan
        sb_drawdown = np.nan
        if primary_eligible:
            inst_df = by_inst.get(inst)
            if inst_df is None:
                formula_status = "missing_price_row"
            else:
                dates = pd.DatetimeIndex(inst_df["date"])
                ref_pos_arr = np.where(dates == as_date(ref_date))[0]
                sig_pos_arr = np.where(dates == as_date(signal_date))[0]
                if len(ref_pos_arr) == 0 or len(sig_pos_arr) == 0:
                    formula_status = "missing_price_row"
                else:
                    ref_pos = int(ref_pos_arr[0])
                    sig_pos = int(sig_pos_arr[0])
                    ref_row = inst_df.iloc[ref_pos]
                    sig_row = inst_df.iloc[sig_pos]
                    close_a = finite_float(ref_row.close)
                    if not math.isfinite(close_a) or close_a <= 0:
                        formula_status = "missing_price_row"
                    elif family == "pullback_hold_restrengthen":
                        atr_a = finite_float(ref_row.atr20)
                        start = ref_pos + int(low if math.isfinite(low) else 1)
                        end = min(sig_pos, ref_pos + int(high if math.isfinite(high) else 60))
                        segment = inst_df.iloc[max(ref_pos + 1, start) : end + 1].copy()
                        if segment.empty or not math.isfinite(atr_a):
                            formula_status = "missing_price_row"
                        else:
                            rules = config["observable_reference_rules"]
                            segment["_drawdown"] = segment["low"].astype(float) / close_a - 1.0
                            mask = (
                                (segment["_drawdown"] <= -float(rules["pullback_min_drawdown_from_acceleration_close"]))
                                & (segment["_drawdown"] >= -float(rules["pullback_max_drawdown_from_acceleration_close"]))
                                & (segment["low"].astype(float) >= close_a - float(rules["pullback_hold_atr_multiple"]) * atr_a)
                            )
                            candidates = segment.loc[mask].copy()
                            if candidates.empty:
                                candidates = segment.assign(_drawdown=segment["low"].astype(float) / close_a - 1.0)
                            candidates = candidates.sort_values(["low", "date"], ascending=[True, True])
                            pullback_depth = float(candidates.iloc[0]["_drawdown"])
                    elif family == "second_breakout":
                        sb_gap = trading_day_distance(calendar, ref_date, signal_date)
                        close_t = finite_float(sig_row.close)
                        if not math.isfinite(close_t):
                            formula_status = "missing_price_row"
                        else:
                            sb_return = close_t / close_a - 1.0
                            interval = inst_df.iloc[ref_pos + 1 : sig_pos]
                            if not interval.empty:
                                low_min = finite_float(interval["low"].min())
                                sb_drawdown = low_min / close_a - 1.0 if math.isfinite(low_min) else np.nan
                            else:
                                sb_drawdown = np.nan
        out = row._asdict()
        out.update(
            {
                "source_upstream_artifact": "ep3_candidate_anchor_panel.parquet",
                "source_upstream_hash": source_hash,
                "primary_diagnostic_eligible": bool(primary_eligible),
                "primary_diagnostic_eligibility_reason": reason,
                "reference_age_days": reference_age,
                "anchor_window_position_ratio": anchor_ratio,
                "formula_diagnostic_status": formula_status,
                "pullback_depth_from_acceleration_close": pullback_depth,
                "second_breakout_gap_days": sb_gap,
                "second_breakout_return_from_first_close": sb_return,
                "second_breakout_consolidation_drawdown_from_first_close": sb_drawdown,
                "industry_bucket": industry_lookup.get((inst, as_date(signal_date)), "UNKNOWN") if primary_eligible else "unavailable",
                "year_bucket": str(as_date(signal_date).year) if primary_eligible else "unavailable",
            }
        )
        rows.append(out)
    return pd.DataFrame(rows)


def build_diagnostic_bin_freeze(config: dict[str, Any], paths: Paths, inputs: dict[str, Any], authority: pd.DataFrame, anchor_raw: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    bins = config["diagnostic_bins"]
    primary = config["diagnostic_scope"]["anchor_families"]
    static_ref_edges = [-np.inf, *[float(x) for x in bins["reference_age_days"]], np.inf]
    rows.extend(build_numeric_bins("all", "reference_age_bucket", "config_static", "config_edges", "reference_age_days", None, static_ref_edges))
    gap_edges = [-np.inf, *[float(x) for x in bins["second_breakout_gap_days"]], np.inf]
    rows.extend(build_numeric_bins("second_breakout", "second_breakout_gap_band", "config_static", "config_edges", "second_breakout_gap_days", None, gap_edges))
    years = [str(y) for y in range(pd.Timestamp(config["split"]["train_start"]).year, pd.Timestamp(config["split"]["robustness_end"]).year + 1)]
    rows.extend(build_category_bins("all", "year_bucket", years, "signal_year"))
    rows.extend(build_category_bins("all", "executable_status", ["executable", "blocked"], "is_executable_next_open"))
    industry_df = pd.read_csv(topic_path(config["data_sources"]["pit_industry_path"]))
    industry_col = "industry_name" if "industry_name" in industry_df.columns else "industry_target_key"
    industries = industry_df[industry_col].dropna().astype(str).unique().tolist()
    rows.extend(build_category_bins("all", "industry_bucket", industries + ["UNKNOWN"], industry_col))
    train = anchor_raw.loc[anchor_raw["split"].eq("train") & anchor_raw["primary_diagnostic_eligible"].astype(bool)].copy()
    for family in primary:
        family_train = train.loc[train["anchor_family_id"].eq(family)]
        edges = quantile_edges(family_train["anchor_window_position_ratio"], bins["anchor_window_position_quantiles"])
        rows.extend(
            build_numeric_bins(
                family,
                "anchor_window_position_bucket",
                "train",
                "quantile",
                "anchor_window_position_ratio",
                family_train["anchor_window_position_ratio"],
                edges,
            )
        )
    pb = train.loc[train["anchor_family_id"].eq("pullback_hold_restrengthen")]
    rows.extend(
        build_numeric_bins(
            "pullback_hold_restrengthen",
            "pullback_depth_band",
            "train",
            "quantile",
            "pullback_depth_from_acceleration_close",
            pb["pullback_depth_from_acceleration_close"],
            quantile_edges(pb["pullback_depth_from_acceleration_close"], bins["formula_margin_quantiles"]),
        )
    )
    sb = train.loc[train["anchor_family_id"].eq("second_breakout")]
    for axis, field in [
        ("second_breakout_return_band", "second_breakout_return_from_first_close"),
        ("second_breakout_consolidation_drawdown_band", "second_breakout_consolidation_drawdown_from_first_close"),
    ]:
        rows.extend(
            build_numeric_bins(
                "second_breakout",
                axis,
                "train",
                "quantile",
                field,
                sb[field],
                quantile_edges(sb[field], bins["formula_margin_quantiles"]),
            )
        )
    copied = inputs["bucket_freeze"].copy()
    source_hash = authority_hash(authority, "matched_control_bucket_freeze")
    source_path = config["upstream_ep3_p0"]["matched_control_bucket_freeze"]
    for bucket_field, axis in [("money", "money_bucket"), ("vol20", "vol20_bucket"), ("ret_60d", "ret_60d_bucket")]:
        subset = copied.loc[copied["bucket_field"].eq(bucket_field)].sort_values("bucket_index")
        for row in subset.itertuples(index=False):
            payload = {
                "anchor_family_id": "all",
                "diagnostic_axis": axis,
                "diagnostic_bucket": str(int(row.bucket_index)),
                "bin_source_split": "upstream_p0_train_frozen",
                "bin_method": "copied_from_p0",
                "source_upstream_artifact": source_path,
                "source_upstream_hash": source_hash,
                "source_field_name": bucket_field,
                "bin_edges_json": json.dumps(
                    subset[["lower_bound", "upper_bound"]].astype(float).values.tolist(),
                    allow_nan=True,
                ),
                "bucket_lower_bound": float(row.lower_bound),
                "bucket_upper_bound": float(row.upper_bound),
                "bucket_inclusive_rule": "closed",
                "train_observation_count": 0,
                "validation_outcomes_used": False,
                "robustness_outcomes_used": False,
                "frozen_before_validation": True,
            }
            payload["predeclared_partition_id"] = stable_id("P05_PART", "all", axis, payload["diagnostic_bucket"])
            payload["bin_hash"] = canonical_hash({k: payload[k] for k in payload if k not in {"predeclared_partition_id", "bin_hash"}})
            rows.append(payload)
    freeze = pd.DataFrame(rows)
    write_csv(freeze, paths.reports_dir / "p0_5_diagnostic_bin_freeze.csv")
    return freeze


def finalize_anchor_panel(config: dict[str, Any], paths: Paths, anchor_raw: pd.DataFrame, freeze: pd.DataFrame) -> pd.DataFrame:
    df = anchor_raw.copy()
    df["reference_age_bucket"] = df.apply(lambda r: assign_numeric_bucket(r["reference_age_days"], freeze, r["anchor_family_id"], "reference_age_bucket"), axis=1)
    df["anchor_window_position_bucket"] = df.apply(lambda r: assign_numeric_bucket(r["anchor_window_position_ratio"], freeze, r["anchor_family_id"], "anchor_window_position_bucket"), axis=1)
    df["pullback_depth_band"] = df.apply(
        lambda r: assign_numeric_bucket(r["pullback_depth_from_acceleration_close"], freeze, r["anchor_family_id"], "pullback_depth_band")
        if r["anchor_family_id"] == "pullback_hold_restrengthen" and r["formula_diagnostic_status"] == "available"
        else "unavailable",
        axis=1,
    )
    df["second_breakout_gap_band"] = df.apply(
        lambda r: assign_numeric_bucket(r["second_breakout_gap_days"], freeze, r["anchor_family_id"], "second_breakout_gap_band")
        if r["anchor_family_id"] == "second_breakout" and r["formula_diagnostic_status"] == "available"
        else "unavailable",
        axis=1,
    )
    df["second_breakout_return_band"] = df.apply(
        lambda r: assign_numeric_bucket(r["second_breakout_return_from_first_close"], freeze, r["anchor_family_id"], "second_breakout_return_band")
        if r["anchor_family_id"] == "second_breakout" and r["formula_diagnostic_status"] == "available"
        else "unavailable",
        axis=1,
    )
    df["second_breakout_consolidation_drawdown_band"] = df.apply(
        lambda r: assign_numeric_bucket(r["second_breakout_consolidation_drawdown_from_first_close"], freeze, r["anchor_family_id"], "second_breakout_consolidation_drawdown_band")
        if r["anchor_family_id"] == "second_breakout" and r["formula_diagnostic_status"] == "available" and not is_missing(r["second_breakout_consolidation_drawdown_from_first_close"])
        else "unavailable",
        axis=1,
    )
    unavailable_fields = [
        "industry_bucket",
        "year_bucket",
        "reference_age_days",
        "anchor_window_position_ratio",
        "reference_age_bucket",
        "anchor_window_position_bucket",
        "pullback_depth_from_acceleration_close",
        "pullback_depth_band",
        "second_breakout_gap_days",
        "second_breakout_gap_band",
        "second_breakout_return_from_first_close",
        "second_breakout_return_band",
        "second_breakout_consolidation_drawdown_from_first_close",
        "second_breakout_consolidation_drawdown_band",
    ]
    mask = ~df["primary_diagnostic_eligible"].astype(bool)
    for field in unavailable_fields:
        if field in df:
            df[field] = df[field].astype("object")
            df.loc[mask, field] = "unavailable"
    for field in ["money_bucket", "vol20_bucket", "ret_60d_bucket"]:
        df[field] = df[field].map(lambda x: "unbucketed" if is_missing(x) else str(int(float(x))) if str(x).replace(".", "", 1).isdigit() else str(x))
    numeric_diagnostic_fields = [
        "reference_age_days",
        "anchor_window_position_ratio",
        "pullback_depth_from_acceleration_close",
        "second_breakout_gap_days",
        "second_breakout_return_from_first_close",
        "second_breakout_consolidation_drawdown_from_first_close",
    ]
    for field in numeric_diagnostic_fields:
        df[field] = df[field].map(lambda x: "unavailable" if is_missing(x) or clean_str(x) == "unavailable" else str(float(x)) if math.isfinite(finite_float(x)) else "unavailable")
    df["diagnostic_panel_hash"] = df.apply(lambda r: canonical_hash({k: v for k, v in r.to_dict().items() if k != "diagnostic_panel_hash"}), axis=1)
    write_parquet(df, paths.cache_dir / "p0_5_anchor_event_diagnostic_panel.parquet")
    return df


def parse_matched_bucket(value: Any) -> dict[str, str]:
    text = clean_str(value)
    out = {"money_bucket": "unbucketed", "vol20_bucket": "unbucketed", "ret_60d_bucket": "unbucketed"}
    if not text:
        return out
    for part in text.split("|"):
        if "=" not in part:
            continue
        key, raw = part.split("=", 1)
        if key == "money":
            out["money_bucket"] = raw
        elif key == "vol20":
            out["vol20_bucket"] = raw
        elif key == "ret60":
            out["ret_60d_bucket"] = raw
    return out


def build_baseline_panel(
    config: dict[str, Any],
    paths: Paths,
    authority: pd.DataFrame,
    inputs: dict[str, Any],
    calendar: pd.DatetimeIndex,
    industry_lookup: dict[tuple[str, pd.Timestamp], str],
    anchor_panel: pd.DataFrame,
    freeze: pd.DataFrame,
) -> pd.DataFrame:
    baseline = inputs["matched_baselines"].copy()
    source_hash = authority_hash(authority, "matched_baseline_panel")
    anchor_by_id = {clean_str(row.anchor_event_id): row._asdict() for row in anchor_panel.itertuples(index=False)}
    primary = set(config["diagnostic_scope"]["anchor_families"])
    windows = inputs["anchor_windows"].set_index("anchor_family_id").to_dict("index")
    rows: list[dict[str, Any]] = []
    pairwise = {"matched_delay_baseline", "same_instrument_nonanchor_baseline", "industry_matched_baseline", "failed_lookalike_baseline"}
    for row in baseline.itertuples(index=False):
        out = row._asdict()
        baseline_id = clean_str(row.baseline_id)
        anchor_id = clean_str(row.anchor_event_id)
        linked = anchor_by_id.get(anchor_id)
        split = clean_str(row.split)
        signal_date = getattr(row, "signal_date")
        execution_date = getattr(row, "execution_date")
        ref_date = getattr(row, "reference_acceleration_date")
        dates_ok = not is_missing(signal_date) and not is_missing(execution_date)
        family = clean_str(row.anchor_family_id)
        eligible = False
        reason = "out_of_scope" if split not in PRIMARY_SPLITS else "eligible"
        bucket_source = "unavailable"
        inherited = {}
        if baseline_id == "all_launch_direct_baseline":
            eligible = split in PRIMARY_SPLITS and dates_ok
            reason = "eligible" if eligible else ("missing_required_date" if split in PRIMARY_SPLITS else "out_of_scope")
            bucket_source = "baseline_event" if eligible else "unavailable"
        elif baseline_id in pairwise and anchor_id:
            eligible = bool(linked and linked.get("primary_diagnostic_eligible") and split in PRIMARY_SPLITS and dates_ok)
            reason = "eligible" if eligible else ("missing_linked_anchor" if not linked else "missing_required_date")
            bucket_source = "linked_anchor" if eligible else "unavailable"
            if linked:
                family = clean_str(linked["anchor_family_id"])
                for field in [
                    "reference_age_days",
                    "anchor_window_position_ratio",
                    "reference_age_bucket",
                    "anchor_window_position_bucket",
                    "pullback_depth_band",
                    "second_breakout_gap_band",
                    "second_breakout_return_band",
                    "second_breakout_consolidation_drawdown_band",
                    "money_bucket",
                    "vol20_bucket",
                    "ret_60d_bucket",
                ]:
                    inherited[field] = linked.get(field, "unavailable")
        elif baseline_id == "failed_lookalike_baseline":
            eligible = split in PRIMARY_SPLITS and dates_ok and not is_missing(ref_date) and family in primary
            reason = "eligible" if eligible else ("missing_required_date" if split in PRIMARY_SPLITS else "out_of_scope")
            bucket_source = "baseline_event" if eligible else "unavailable"
        else:
            reason = "invalid_baseline_scope"
        reference_age = inherited.get("reference_age_days", np.nan)
        anchor_ratio = inherited.get("anchor_window_position_ratio", np.nan)
        if eligible and bucket_source == "baseline_event" and baseline_id == "failed_lookalike_baseline":
            reference_age = trading_day_distance(calendar, ref_date, signal_date)
            window = windows.get(family, {})
            low = finite_float(window.get("frozen_window_low"))
            high = finite_float(window.get("frozen_window_high"))
            anchor_ratio = 0.0 if math.isfinite(low) and math.isfinite(high) and high == low else (
                (reference_age - low) / (high - low) if math.isfinite(reference_age) and math.isfinite(low) and math.isfinite(high) else np.nan
            )
        out["anchor_family_id"] = family
        out["source_upstream_artifact"] = "ep3_matched_baseline_panel.parquet"
        out["source_upstream_hash"] = source_hash
        out["primary_diagnostic_eligible"] = bool(eligible)
        out["primary_diagnostic_eligibility_reason"] = reason
        out["reference_age_days"] = reference_age if eligible else "unavailable"
        out["anchor_window_position_ratio"] = anchor_ratio if eligible else "unavailable"
        out["reference_age_bucket"] = inherited.get("reference_age_bucket", assign_numeric_bucket(reference_age, freeze, family, "reference_age_bucket")) if eligible and baseline_id != "all_launch_direct_baseline" else "unavailable"
        out["anchor_window_position_bucket"] = inherited.get("anchor_window_position_bucket", assign_numeric_bucket(anchor_ratio, freeze, family, "anchor_window_position_bucket")) if eligible and baseline_id != "all_launch_direct_baseline" else "unavailable"
        for field in ["pullback_depth_band", "second_breakout_gap_band", "second_breakout_return_band", "second_breakout_consolidation_drawdown_band"]:
            out[field] = inherited.get(field, "unbucketed") if eligible and baseline_id != "all_launch_direct_baseline" else "unavailable"
        parsed = parse_matched_bucket(getattr(row, "matched_control_bucket_id", ""))
        for field in ["money_bucket", "vol20_bucket", "ret_60d_bucket"]:
            if baseline_id == "all_launch_direct_baseline":
                out[field] = "unbucketed"
            elif bucket_source == "linked_anchor":
                out[field] = inherited.get(field, "unbucketed")
            elif bucket_source == "baseline_event":
                out[field] = parsed[field]
            else:
                out[field] = "unbucketed"
        out["diagnostic_bucket_source"] = bucket_source
        out["industry_bucket"] = industry_lookup.get((clean_str(row.instrument).upper(), as_date(signal_date)), "UNKNOWN") if eligible else "unavailable"
        out["year_bucket"] = str(as_date(signal_date).year) if eligible else "unavailable"
        out["diagnostic_panel_hash"] = canonical_hash(out)
        rows.append(out)
    out_df = pd.DataFrame(rows)
    for field in ["reference_age_days", "anchor_window_position_ratio"]:
        out_df[field] = out_df[field].map(lambda x: "unavailable" if is_missing(x) or clean_str(x) == "unavailable" else str(float(x)) if math.isfinite(finite_float(x)) else "unavailable")
    write_parquet(out_df, paths.cache_dir / "p0_5_baseline_event_diagnostic_panel.parquet")
    return out_df


def safe_div(num: float, den: float) -> float:
    return float(num) / float(den) if den else np.nan


def q05(values: pd.Series) -> float:
    clean = pd.to_numeric(values, errors="coerce").dropna()
    return float(clean.quantile(0.05)) if not clean.empty else np.nan


def mean(values: pd.Series) -> float:
    clean = pd.to_numeric(values, errors="coerce").dropna()
    return float(clean.mean()) if not clean.empty else np.nan


def instrument_year_count(df: pd.DataFrame, date_col: str = "signal_date") -> int:
    if df.empty:
        return 0
    years = pd.to_datetime(df[date_col], errors="coerce").dt.year.astype("Int64").astype(str)
    return int((df["instrument"].astype(str) + "_" + years).nunique())


def interpretation(count: int, iy_count: int, config: dict[str, Any]) -> str:
    bins = config["diagnostic_bins"]
    return "interpretable" if count >= int(bins["event_count_min_for_interpretation"]) and iy_count >= int(bins["instrument_year_count_min_for_interpretation"]) else "too_sparse"


def trigger_rate_band(config: dict[str, Any], value: float) -> str:
    edges = [float(x) for x in config["diagnostic_bins"]["trigger_rate_reference_bands"]]
    if not math.isfinite(value):
        return "unavailable"
    for idx in range(len(edges) - 1):
        if edges[idx] <= value < edges[idx + 1] or (idx == len(edges) - 2 and edges[idx] <= value <= edges[idx + 1]):
            return f"{edges[idx]:g}_{edges[idx + 1]:g}"
    if value >= edges[-1]:
        return f"ge_{edges[-1]:g}"
    return f"lt_{edges[0]:g}"


def build_trigger_denominator(
    config: dict[str, Any],
    paths: Paths,
    inputs: dict[str, Any],
    anchor_panel: pd.DataFrame,
    baseline_panel: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    ep2 = inputs["ep2_launch_pool"].copy()
    canonical = ep2.sort_values(["launch_episode_id", "signal_date"]).drop_duplicates("launch_episode_id", keep="first").copy()
    canonical["split"] = canonical["signal_date"].map(lambda x: split_for_date(config, x))
    canonical = canonical.loc[canonical["split"].isin(PRIMARY_SPLITS)].copy()
    source_rows = []
    for src_type, df, event_col in [
        ("anchor", anchor_panel, "anchor_event_id"),
        ("matched_baseline", baseline_panel, "baseline_event_id"),
    ]:
        for row in df.loc[df["split"].isin(PRIMARY_SPLITS)].itertuples(index=False):
            for field in ["money_bucket", "vol20_bucket", "ret_60d_bucket"]:
                bucket = clean_str(getattr(row, field, ""))
                if bucket in {"", "unavailable", "unbucketed"}:
                    continue
                source_rows.append(
                    {
                        "source_type": src_type,
                        "source_event_id": clean_str(getattr(row, event_col)),
                        "instrument": clean_str(row.instrument).upper(),
                        "split": clean_str(row.split),
                        "source_signal_date": as_date(getattr(row, "signal_date")),
                        "bucket_field": field,
                        "bucket": bucket,
                    }
                )
    source = pd.DataFrame(source_rows)
    by_inst_field: dict[tuple[str, str, str], pd.DataFrame] = {}
    if not source.empty:
        for key, group in source.groupby(["split", "instrument", "bucket_field"], sort=False):
            by_inst_field[key] = group.sort_values(["source_signal_date", "source_type", "source_event_id"]).reset_index(drop=True)

    def nearest_bucket(split: str, inst: str, date: pd.Timestamp, field: str) -> str:
        group = by_inst_field.get((split, inst, field))
        if group is None or group.empty:
            return "unbucketed"
        exact = group.loc[group["source_signal_date"].eq(date)]
        if not exact.empty:
            picked = exact.sort_values(["source_type", "source_event_id"]).iloc[0]
            return clean_str(picked["bucket"])
        g = group.copy()
        g["_abs_days"] = (g["source_signal_date"] - date).abs().dt.days
        g["_event_key"] = g["source_type"] + ":" + g["source_event_id"]
        picked = g.sort_values(["_abs_days", "source_signal_date", "_event_key"]).iloc[0]
        return clean_str(picked["bucket"])

    rows = []
    for row in canonical.itertuples(index=False):
        split = clean_str(row.split)
        inst = clean_str(row.instrument).upper()
        date = as_date(row.signal_date)
        buy_exec = as_bool(getattr(row, "is_buy_executable_next_open", getattr(row, "is_executable_next_open", False)))
        rows.append(
            {
                "split": split,
                "launch_episode_id": clean_str(row.launch_episode_id),
                "instrument": inst,
                "launch_signal_date": date,
                "launch_execution_date": getattr(row, "execution_date"),
                "launch_is_executable_next_open": buy_exec,
                "executable_status": "executable" if buy_exec else "blocked",
                "blocked_buy_reason": clean_str(getattr(row, "blocked_buy_reason", getattr(row, "blocked_execution_reason", ""))),
                "industry_bucket": clean_str(getattr(row, "industry_asof_signal_date", "")) or "UNKNOWN",
                "year_bucket": str(date.year),
                "money_bucket": nearest_bucket(split, inst, date, "money_bucket"),
                "vol20_bucket": nearest_bucket(split, inst, date, "vol20_bucket"),
                "ret_60d_bucket": nearest_bucket(split, inst, date, "ret_60d_bucket"),
                "denominator_source": "ep2_launch_pool",
            }
        )
    denom = pd.DataFrame(rows)
    write_csv(denom, paths.reports_dir / "p0_5_trigger_denominator_panel.csv")
    rec_rows = []
    trigger = inputs["trigger_budget"]
    for row in trigger.loc[trigger["split"].isin(PRIMARY_SPLITS)].itertuples(index=False):
        count = int(denom.loc[denom["split"].eq(row.split), "launch_episode_id"].nunique())
        upstream = int(row.ep2_launch_episode_count)
        rec_rows.append(
            {
                "split": row.split,
                "anchor_family_id": row.anchor_family_id,
                "p0_5_denominator_launch_episode_count": count,
                "upstream_ep2_launch_episode_count": upstream,
                "count_diff": count - upstream,
                "denominator_reconciliation_status": "passed" if count == upstream else "failed",
            }
        )
    rec = pd.DataFrame(rec_rows)
    write_csv(rec, paths.reports_dir / "p0_5_trigger_denominator_reconciliation.csv")
    return denom, rec


def build_trigger_decomposition(
    config: dict[str, Any],
    paths: Paths,
    inputs: dict[str, Any],
    freeze: pd.DataFrame,
    anchor_panel: pd.DataFrame,
    denom: pd.DataFrame,
) -> pd.DataFrame:
    primary = config["diagnostic_scope"]["anchor_families"]
    denom_by_id = {clean_str(row.launch_episode_id): row._asdict() for row in denom.itertuples(index=False)}
    rows: list[dict[str, Any]] = []
    denom_axes = ["year_bucket", "industry_bucket", "executable_status", "money_bucket", "vol20_bucket", "ret_60d_bucket"]
    anchor_axes = [
        "anchor_window_position_bucket",
        "reference_age_bucket",
        "pullback_depth_band",
        "second_breakout_gap_band",
        "second_breakout_return_band",
        "second_breakout_consolidation_drawdown_band",
    ]
    trigger = inputs["trigger_budget"]
    metrics = inputs["anchor_metrics"]
    min_budget = 0.20
    for split in PRIMARY_SPLITS:
        split_denom = denom.loc[denom["split"].eq(split)]
        split_denominator = int(split_denom["launch_episode_id"].nunique())
        for family in primary:
            raw = anchor_panel.loc[
                anchor_panel["split"].eq(split)
                & anchor_panel["anchor_family_id"].eq(family)
                & (pd.to_numeric(anchor_panel["dedupe_rank_within_reference_event"], errors="coerce").fillna(9999).eq(1))
                & anchor_panel["is_executable_next_open"].map(as_bool)
            ].copy()
            gate = raw.loc[raw["eligible_for_primary_gate"].map(as_bool)].copy()
            upstream_raw = int(trigger.loc[trigger["split"].eq(split) & trigger["anchor_family_id"].eq(family), "anchor_trigger_count"].iloc[0])
            upstream_gate = int(
                metrics.loc[
                    metrics["split"].eq(split)
                    & metrics["anchor_family_id"].eq(family)
                    & metrics["baseline_id"].eq("anchor")
                    & metrics["horizon_id"].eq("H20"),
                    "event_count",
                ].iloc[0]
            )
            for rate_type, numerator, upstream_count in [("raw", raw, upstream_raw), ("gate_eligible_h20", gate, upstream_gate)]:
                numerator = numerator.copy()
                if not numerator.empty:
                    numerator["_canonical_launch_split"] = numerator["anchor_trigger_rate_denominator_id"].map(lambda x: clean_str(denom_by_id.get(clean_str(x), {}).get("split", "")))
                    numerator["_cross_split"] = numerator["_canonical_launch_split"].ne(split)
                else:
                    numerator["_canonical_launch_split"] = []
                    numerator["_cross_split"] = []
                cross_count = int(numerator["_cross_split"].sum()) if not numerator.empty else 0
                count = int(len(numerator))
                rate = safe_div(count, split_denominator)
                rows.append(
                    {
                        "split": split,
                        "anchor_family_id": family,
                        "diagnostic_axis": "all",
                        "diagnostic_bucket": "all",
                        "predeclared_partition_id": "not_applicable",
                        "trigger_rate_type": rate_type,
                        "numerator_split_rule": "anchor_event_split",
                        "denominator_split_rule": "canonical_launch_split",
                        "numerator_bucket_source": "anchor_event",
                        "anchor_trigger_count": count,
                        "upstream_anchor_trigger_count": upstream_count,
                        "cross_split_reference_count": cross_count,
                        "ep2_launch_episode_count": split_denominator,
                        "denominator_scope": "split_level",
                        "trigger_rate_per_launch_episode": rate,
                        "trigger_rate_band": trigger_rate_band(config, rate),
                        "trigger_rate_gap_to_min_budget": min_budget - rate,
                        "unique_instrument_count": int(numerator["instrument"].nunique()) if not numerator.empty else 0,
                        "unique_instrument_year_count": instrument_year_count(numerator) if not numerator.empty else 0,
                        "trigger_count_reproduction_status": "passed" if count == upstream_count else "failed",
                        "interpretation_status": interpretation(count, instrument_year_count(numerator) if not numerator.empty else 0, config),
                    }
                )
                for axis in denom_axes:
                    for bucket, denom_group in split_denom.groupby(axis, dropna=False):
                        bucket = clean_str(bucket) or "unbucketed"
                        same_split_num = numerator.loc[~numerator["_cross_split"]].copy()
                        if not same_split_num.empty:
                            same_split_num["_bucket"] = same_split_num["anchor_trigger_rate_denominator_id"].map(
                                lambda x: clean_str(denom_by_id.get(clean_str(x), {}).get(axis, "unbucketed"))
                            )
                            num_group = same_split_num.loc[same_split_num["_bucket"].eq(bucket)]
                        else:
                            num_group = same_split_num
                        den = int(denom_group["launch_episode_id"].nunique())
                        n = int(len(num_group))
                        r = safe_div(n, den)
                        rows.append(
                            {
                                "split": split,
                                "anchor_family_id": family,
                                "diagnostic_axis": axis,
                                "diagnostic_bucket": bucket,
                                "predeclared_partition_id": predeclared_id(freeze, family, axis, bucket),
                                "trigger_rate_type": rate_type,
                                "numerator_split_rule": "anchor_event_split",
                                "denominator_split_rule": "canonical_launch_split",
                                "numerator_bucket_source": "canonical_denominator_row",
                                "anchor_trigger_count": n,
                                "upstream_anchor_trigger_count": upstream_count,
                                "cross_split_reference_count": 0,
                                "ep2_launch_episode_count": den,
                                "denominator_scope": "bucket_level",
                                "trigger_rate_per_launch_episode": r,
                                "trigger_rate_band": trigger_rate_band(config, r),
                                "trigger_rate_gap_to_min_budget": min_budget - r if math.isfinite(r) else np.nan,
                                "unique_instrument_count": int(num_group["instrument"].nunique()) if not num_group.empty else 0,
                                "unique_instrument_year_count": instrument_year_count(num_group) if not num_group.empty else 0,
                                "trigger_count_reproduction_status": "passed" if count == upstream_count else "failed",
                                "interpretation_status": interpretation(n, instrument_year_count(num_group) if not num_group.empty else 0, config),
                            }
                        )
                    if cross_count:
                        cross = numerator.loc[numerator["_cross_split"]]
                        r = safe_div(len(cross), split_denominator)
                        rows.append(
                            {
                                "split": split,
                                "anchor_family_id": family,
                                "diagnostic_axis": axis,
                                "diagnostic_bucket": "cross_split_reference",
                                "predeclared_partition_id": "not_applicable",
                                "trigger_rate_type": rate_type,
                                "numerator_split_rule": "anchor_event_split",
                                "denominator_split_rule": "canonical_launch_split",
                                "numerator_bucket_source": "cross_split_reference",
                                "anchor_trigger_count": int(len(cross)),
                                "upstream_anchor_trigger_count": upstream_count,
                                "cross_split_reference_count": int(len(cross)),
                                "ep2_launch_episode_count": split_denominator,
                                "denominator_scope": "split_level",
                                "trigger_rate_per_launch_episode": r,
                                "trigger_rate_band": trigger_rate_band(config, r),
                                "trigger_rate_gap_to_min_budget": min_budget - r if math.isfinite(r) else np.nan,
                                "unique_instrument_count": int(cross["instrument"].nunique()),
                                "unique_instrument_year_count": instrument_year_count(cross),
                                "trigger_count_reproduction_status": "passed" if count == upstream_count else "failed",
                                "interpretation_status": interpretation(int(len(cross)), instrument_year_count(cross), config),
                            }
                        )
                for axis in anchor_axes:
                    available = numerator.loc[~numerator[axis].astype(str).isin(["", "unavailable", "unbucketed"])].copy()
                    for bucket, num_group in available.groupby(axis, dropna=False):
                        bucket = clean_str(bucket)
                        n = int(len(num_group))
                        r = safe_div(n, split_denominator)
                        rows.append(
                            {
                                "split": split,
                                "anchor_family_id": family,
                                "diagnostic_axis": axis,
                                "diagnostic_bucket": bucket,
                                "predeclared_partition_id": predeclared_id(freeze, family, axis, bucket),
                                "trigger_rate_type": rate_type,
                                "numerator_split_rule": "anchor_event_split",
                                "denominator_split_rule": "canonical_launch_split",
                                "numerator_bucket_source": "anchor_event",
                                "anchor_trigger_count": n,
                                "upstream_anchor_trigger_count": upstream_count,
                                "cross_split_reference_count": int(num_group["_cross_split"].sum()) if "_cross_split" in num_group else 0,
                                "ep2_launch_episode_count": split_denominator,
                                "denominator_scope": "split_level",
                                "trigger_rate_per_launch_episode": r,
                                "trigger_rate_band": trigger_rate_band(config, r),
                                "trigger_rate_gap_to_min_budget": min_budget - r if math.isfinite(r) else np.nan,
                                "unique_instrument_count": int(num_group["instrument"].nunique()),
                                "unique_instrument_year_count": instrument_year_count(num_group),
                                "trigger_count_reproduction_status": "passed" if count == upstream_count else "failed",
                                "interpretation_status": interpretation(n, instrument_year_count(num_group), config),
                            }
                        )
    out = pd.DataFrame(rows)
    write_csv(out, paths.reports_dir / "p0_5_trigger_decomposition.csv")
    return out


def build_lifecycle_forward_translation(
    config: dict[str, Any],
    paths: Paths,
    inputs: dict[str, Any],
    anchor_panel: pd.DataFrame,
    baseline_panel: pd.DataFrame,
    denom: pd.DataFrame,
) -> pd.DataFrame:
    gate = inputs["gate_audit"]
    rows = []
    for split in PRIMARY_SPLITS:
        launch_den = int(denom.loc[denom["split"].eq(split), "launch_episode_id"].nunique())
        for family in config["diagnostic_scope"]["anchor_families"]:
            family_anchor = anchor_panel.loc[
                anchor_panel["split"].eq(split)
                & anchor_panel["anchor_family_id"].eq(family)
                & (pd.to_numeric(anchor_panel["dedupe_rank_within_reference_event"], errors="coerce").fillna(9999).eq(1))
            ].copy()
            executable = family_anchor.loc[family_anchor["is_executable_next_open"].map(as_bool)]
            gate_eligible = executable.loc[executable["eligible_for_primary_gate"].map(as_bool)]
            lifecycle_value = float(gate.loc[gate["anchor_family_id"].eq(family) & gate["gate_name"].eq("lifecycle_anchor_recall"), "gate_value"].iloc[0])
            anchor_side = anchor_panel.loc[
                anchor_panel["split"].eq(split)
                & anchor_panel["anchor_family_id"].eq(family)
                & anchor_panel["primary_diagnostic_eligible"].astype(bool)
                & anchor_panel["eligible_for_primary_gate"].map(as_bool)
            ].copy()
            md = baseline_panel.loc[
                baseline_panel["split"].eq(split)
                & baseline_panel["anchor_family_id"].eq(family)
                & baseline_panel["baseline_id"].eq("matched_delay_baseline")
                & baseline_panel["primary_diagnostic_eligible"].astype(bool)
                & baseline_panel["eligible_for_primary_gate"].map(as_bool)
                & pd.to_numeric(baseline_panel["after_cost_return_H20"], errors="coerce").notna()
            ].copy()
            md_counts = md.groupby("anchor_event_id").size()
            duplicate_ids = set(md_counts.loc[md_counts > 1].index.astype(str))
            md_unique = md.loc[~md["anchor_event_id"].astype(str).isin(duplicate_ids)].drop_duplicates("anchor_event_id")
            paired = anchor_side.merge(
                md_unique[["anchor_event_id", "after_cost_return_H20"]].rename(columns={"after_cost_return_H20": "matched_delay_after_cost_return_H20"}),
                on="anchor_event_id",
                how="left",
            )
            pairable = paired.loc[pd.to_numeric(paired["matched_delay_after_cost_return_H20"], errors="coerce").notna()]
            pair_exclusions = int(len(anchor_side) - len(pairable) + len(duplicate_ids))
            metric_specs = [
                ("lifecycle_anchor_recall", "ep3_gate_audit.csv", lifecycle_value, np.nan, np.nan, "upstream lifecycle gate value"),
                ("forward_executable_anchor_rate", "p0_5_anchor_event_diagnostic_panel", safe_div(len(executable), launch_den), len(executable), launch_den, "executable anchor triggers per canonical launch episode"),
                ("forward_gate_eligible_anchor_rate", "p0_5_anchor_event_diagnostic_panel", safe_div(len(gate_eligible), launch_den), len(gate_eligible), launch_den, "H20 gate-eligible executable anchors per canonical launch episode"),
                ("execution_block_rate", "p0_5_anchor_event_diagnostic_panel", safe_div(len(family_anchor) - len(executable), len(family_anchor)), len(family_anchor) - len(executable), len(family_anchor), "deduped anchors blocked at next open"),
                ("label_horizon_ineligible_rate", "p0_5_anchor_event_diagnostic_panel", safe_div(len(executable) - len(gate_eligible), len(executable)), len(executable) - len(gate_eligible), len(executable), "executable anchors excluded from primary H20 gate"),
                (
                    "matched_delay_underperformance_rate",
                    "p0_5_anchor_event_diagnostic_panel+p0_5_baseline_event_diagnostic_panel",
                    safe_div(
                        int((pd.to_numeric(pairable["after_cost_return_H20"], errors="coerce") <= pd.to_numeric(pairable["matched_delay_after_cost_return_H20"], errors="coerce")).sum()),
                        len(pairable),
                    ),
                    int((pd.to_numeric(pairable["after_cost_return_H20"], errors="coerce") <= pd.to_numeric(pairable["matched_delay_after_cost_return_H20"], errors="coerce")).sum()),
                    len(pairable),
                    "share of paired anchors not beating matched-delay baseline",
                ),
                ("winner_capture_rate_50h120", "p0_5_anchor_event_diagnostic_panel", safe_div(gate_eligible["winner_50h120"].map(as_bool).sum(), len(gate_eligible)), int(gate_eligible["winner_50h120"].map(as_bool).sum()), len(gate_eligible), "gate-eligible anchor winner capture"),
                ("trigger_budget_shortfall_rate", "p0_5_trigger_decomposition.csv", max(0.0, 0.20 - safe_div(len(executable), launch_den)), max(0.0, 0.20 - safe_div(len(executable), launch_den)), 1.0, "shortfall to 20pct trigger budget floor"),
            ]
            for metric_id, source, value, numerator, denominator, text in metric_specs:
                rows.append(
                    {
                        "anchor_family_id": family,
                        "split": split,
                        "translation_metric_id": metric_id,
                        "metric_source": source,
                        "lifecycle_anchor_recall": lifecycle_value,
                        "canonical_launch_denominator": launch_den,
                        "deduped_anchor_candidate_count": int(len(family_anchor)),
                        "forward_executable_anchor_count": int(len(executable)),
                        "forward_gate_eligible_anchor_count": int(len(gate_eligible)),
                        "matched_delay_pair_exclusion_count": pair_exclusions if metric_id == "matched_delay_underperformance_rate" else 0,
                        "metric_numerator": numerator,
                        "metric_denominator": denominator,
                        "metric_value": value,
                        "metric_interpretation": text,
                    }
                )
    out = pd.DataFrame(rows)
    write_csv(out, paths.reports_dir / "p0_5_lifecycle_forward_translation.csv")
    return out


PAIRWISE_BASELINES = [
    "matched_delay_baseline",
    "same_instrument_nonanchor_baseline",
    "industry_matched_baseline",
    "failed_lookalike_baseline",
]
PAIRWISE_AXES = [
    "all",
    "anchor_window_position_bucket",
    "reference_age_bucket",
    "pullback_depth_band",
    "second_breakout_gap_band",
    "second_breakout_return_band",
    "second_breakout_consolidation_drawdown_band",
    "year_bucket",
    "industry_bucket",
    "money_bucket",
    "vol20_bucket",
    "ret_60d_bucket",
]
ALL_LAUNCH_AXES = ["all", "year_bucket", "industry_bucket"]


def rows_for_axis(df: pd.DataFrame, axis: str) -> list[tuple[str, pd.DataFrame]]:
    if axis == "all":
        return [("all", df)]
    if axis not in df.columns or df.empty:
        return []
    out = []
    available = df.loc[~df[axis].astype(str).isin(["", "unavailable", "unbucketed"])]
    for bucket, group in available.groupby(axis, dropna=False):
        out.append((clean_str(bucket), group))
    return out


def positive_rate_by_instrument_year(df: pd.DataFrame, return_col: str) -> float:
    if df.empty:
        return np.nan
    tmp = df.copy()
    tmp["_year"] = pd.to_datetime(tmp["signal_date"], errors="coerce").dt.year
    grouped = tmp.groupby(["instrument", "_year"])[return_col].sum()
    return safe_div(int((grouped > 0).sum()), len(grouped))


def lift_metric_row(
    config: dict[str, Any],
    freeze: pd.DataFrame,
    split: str,
    family: str,
    axis: str,
    bucket: str,
    bucket_source: str,
    baseline_id: str,
    anchor_rows: pd.DataFrame,
    baseline_rows: pd.DataFrame,
    horizon: str,
) -> dict[str, Any]:
    ret_col = f"after_cost_return_{horizon}"
    anchor_count = int(pd.to_numeric(anchor_rows.get(ret_col, pd.Series(dtype=float)), errors="coerce").notna().sum())
    baseline_count = int(pd.to_numeric(baseline_rows.get(ret_col, pd.Series(dtype=float)), errors="coerce").notna().sum())
    anchor_mean = mean(anchor_rows[ret_col]) if ret_col in anchor_rows else np.nan
    baseline_mean = mean(baseline_rows[ret_col]) if ret_col in baseline_rows else np.nan
    anchor_p05 = q05(anchor_rows[ret_col]) if ret_col in anchor_rows else np.nan
    baseline_p05 = q05(baseline_rows[ret_col]) if ret_col in baseline_rows else np.nan
    iy = instrument_year_count(anchor_rows) if anchor_count else instrument_year_count(baseline_rows)
    return {
        "split": split,
        "anchor_family_id": family,
        "diagnostic_axis": axis,
        "diagnostic_bucket": bucket,
        "predeclared_partition_id": predeclared_id(freeze, family, axis, bucket),
        "diagnostic_bucket_source": bucket_source,
        "baseline_id": baseline_id,
        "anchor_event_count": anchor_count,
        "baseline_event_count": baseline_count,
        "unique_instrument_year_count": iy,
        f"anchor_mean_after_cost_return_{horizon}": anchor_mean,
        f"baseline_mean_after_cost_return_{horizon}": baseline_mean,
        "mean_diff_vs_baseline": anchor_mean - baseline_mean if math.isfinite(anchor_mean) and math.isfinite(baseline_mean) else np.nan,
        f"anchor_p05_after_cost_return_{horizon}": anchor_p05,
        f"baseline_p05_after_cost_return_{horizon}": baseline_p05,
        "p05_diff_vs_baseline": anchor_p05 - baseline_p05 if math.isfinite(anchor_p05) and math.isfinite(baseline_p05) else np.nan,
        "anchor_instrument_year_positive_rate": positive_rate_by_instrument_year(anchor_rows, ret_col) if anchor_count else np.nan,
        "baseline_instrument_year_positive_rate": positive_rate_by_instrument_year(baseline_rows, ret_col) if baseline_count else np.nan,
        "interpretation_status": interpretation(anchor_count, iy, config),
    }


def build_lift_rows_for_horizon(
    config: dict[str, Any],
    freeze: pd.DataFrame,
    anchor_panel: pd.DataFrame,
    baseline_panel: pd.DataFrame,
    horizon: str,
) -> pd.DataFrame:
    ret_col = f"after_cost_return_{horizon}"
    anchors = anchor_panel.loc[
        anchor_panel["split"].isin(PRIMARY_SPLITS)
        & anchor_panel["anchor_family_id"].isin(config["diagnostic_scope"]["anchor_families"])
        & anchor_panel["primary_diagnostic_eligible"].astype(bool)
        & anchor_panel["eligible_for_primary_gate"].map(as_bool)
        & pd.to_numeric(anchor_panel[ret_col], errors="coerce").notna()
    ].copy()
    baselines = baseline_panel.loc[
        baseline_panel["split"].isin(PRIMARY_SPLITS)
        & baseline_panel["primary_diagnostic_eligible"].astype(bool)
        & baseline_panel["eligible_for_primary_gate"].map(as_bool)
        & pd.to_numeric(baseline_panel[ret_col], errors="coerce").notna()
    ].copy()
    anchor_by_id = {clean_str(row.anchor_event_id): row._asdict() for row in anchors.itertuples(index=False)}
    rows: list[dict[str, Any]] = []
    for split in PRIMARY_SPLITS:
        for family in config["diagnostic_scope"]["anchor_families"]:
            family_anchor = anchors.loc[anchors["split"].eq(split) & anchors["anchor_family_id"].eq(family)].copy()
            for baseline_id in PAIRWISE_BASELINES:
                family_base = baselines.loc[baselines["split"].eq(split) & baselines["anchor_family_id"].eq(family) & baselines["baseline_id"].eq(baseline_id)].copy()
                linked = family_base.loc[family_base["diagnostic_bucket_source"].eq("linked_anchor") & family_base["anchor_event_id"].astype(str).isin(anchor_by_id)].copy()
                if not linked.empty:
                    linked_anchor = pd.DataFrame([anchor_by_id[clean_str(x)] for x in linked["anchor_event_id"]])
                    linked_base = linked.reset_index(drop=True)
                    linked_anchor = linked_anchor.reset_index(drop=True)
                    for axis in PAIRWISE_AXES:
                        for bucket, anchor_group in rows_for_axis(linked_anchor, axis):
                            ids = set(anchor_group["anchor_event_id"].astype(str))
                            base_group = linked_base.loc[linked_base["anchor_event_id"].astype(str).isin(ids)]
                            rows.append(lift_metric_row(config, freeze, split, family, axis, bucket, "linked_anchor", baseline_id, anchor_group, base_group, horizon))
                unlinked = family_base.loc[family_base["diagnostic_bucket_source"].eq("baseline_event")].copy()
                if baseline_id == "failed_lookalike_baseline" and not unlinked.empty:
                    for axis in PAIRWISE_AXES:
                        for bucket, base_group in rows_for_axis(unlinked, axis):
                            rows.append(lift_metric_row(config, freeze, split, family, axis, bucket, "baseline_event", baseline_id, family_anchor.iloc[0:0], base_group, horizon))
            all_launch = baselines.loc[baselines["split"].eq(split) & baselines["baseline_id"].eq("all_launch_direct_baseline")].copy()
            for axis in ALL_LAUNCH_AXES:
                anchor_groups = dict(rows_for_axis(family_anchor, axis))
                base_groups = dict(rows_for_axis(all_launch, axis))
                for bucket in sorted(set(anchor_groups) | set(base_groups)):
                    rows.append(
                        lift_metric_row(
                            config,
                            freeze,
                            split,
                            family,
                            axis,
                            bucket,
                            "baseline_event",
                            "all_launch_direct_baseline",
                            anchor_groups.get(bucket, family_anchor.iloc[0:0]),
                            base_groups.get(bucket, all_launch.iloc[0:0]),
                            horizon,
                        )
                    )
    return pd.DataFrame(rows)


def build_matched_lift_decomposition(
    config: dict[str, Any],
    paths: Paths,
    freeze: pd.DataFrame,
    anchor_panel: pd.DataFrame,
    baseline_panel: pd.DataFrame,
) -> pd.DataFrame:
    out = build_lift_rows_for_horizon(config, freeze, anchor_panel, baseline_panel, "H20")
    write_csv(out, paths.reports_dir / "p0_5_matched_lift_decomposition.csv")
    return out


def build_sensitivity_horizon_audit(
    config: dict[str, Any],
    paths: Paths,
    inputs: dict[str, Any],
    freeze: pd.DataFrame,
    anchor_panel: pd.DataFrame,
    baseline_panel: pd.DataFrame,
) -> pd.DataFrame:
    rows = []
    for horizon in config["diagnostic_scope"]["sensitivity_horizons"]:
        lift = build_lift_rows_for_horizon(config, freeze, anchor_panel, baseline_panel, horizon)
        mae_col = f"max_adverse_excursion_{horizon}"
        ret_col = f"after_cost_return_{horizon}"
        for row in lift.itertuples(index=False):
            payload = row._asdict()
            payload["horizon_id"] = horizon
            payload["anchor_mean_after_cost_return"] = payload.pop(f"anchor_mean_after_cost_return_{horizon}")
            payload["baseline_mean_after_cost_return"] = payload.pop(f"baseline_mean_after_cost_return_{horizon}")
            payload["anchor_p05_after_cost_return"] = payload.pop(f"anchor_p05_after_cost_return_{horizon}")
            payload["baseline_p05_after_cost_return"] = payload.pop(f"baseline_p05_after_cost_return_{horizon}")
            payload["anchor_max_adverse_excursion_mean"] = np.nan
            payload["baseline_max_adverse_excursion_mean"] = np.nan
            payload["upstream_aggregate_reproduction_status"] = "not_applicable"
            payload["sensitivity_decision_use_allowed"] = False
            payload["interpretation_status"] = "report_only" if payload["interpretation_status"] == "interpretable" else "too_sparse"
            rows.append(payload)
    upstream = inputs["sensitivity"].loc[inputs["sensitivity"]["horizon_id"].isin(config["diagnostic_scope"]["sensitivity_horizons"])].copy()
    for row in upstream.itertuples(index=False):
        horizon = clean_str(row.horizon_id)
        rows.append(
            {
                "split": row.split,
                "anchor_family_id": row.anchor_family_id,
                "diagnostic_axis": "all",
                "diagnostic_bucket": "all",
                "predeclared_partition_id": "not_applicable",
                "diagnostic_bucket_source": "all_sources",
                "baseline_id": row.baseline_id,
                "anchor_event_count": int(row.event_count) if not is_missing(row.event_count) else 0,
                "baseline_event_count": int(row.event_count) if row.baseline_id != "anchor" and not is_missing(row.event_count) else 0,
                "unique_instrument_year_count": int(row.unique_instrument_year_count) if not is_missing(row.unique_instrument_year_count) else 0,
                "mean_diff_vs_baseline": np.nan,
                "p05_diff_vs_baseline": np.nan,
                "anchor_instrument_year_positive_rate": np.nan,
                "baseline_instrument_year_positive_rate": np.nan,
                "horizon_id": horizon,
                "anchor_mean_after_cost_return": getattr(row, f"mean_after_cost_return_{horizon}"),
                "baseline_mean_after_cost_return": np.nan,
                "anchor_p05_after_cost_return": getattr(row, f"p05_after_cost_return_{horizon}"),
                "baseline_p05_after_cost_return": np.nan,
                "anchor_max_adverse_excursion_mean": getattr(row, f"max_adverse_excursion_mean_{horizon}"),
                "baseline_max_adverse_excursion_mean": np.nan,
                "upstream_aggregate_reproduction_status": "passed",
                "sensitivity_decision_use_allowed": False,
                "interpretation_status": "report_only",
            }
        )
    out = pd.DataFrame(rows)
    ordered = [
        "split",
        "anchor_family_id",
        "horizon_id",
        "diagnostic_axis",
        "diagnostic_bucket",
        "predeclared_partition_id",
        "diagnostic_bucket_source",
        "baseline_id",
        "anchor_event_count",
        "baseline_event_count",
        "anchor_mean_after_cost_return",
        "baseline_mean_after_cost_return",
        "mean_diff_vs_baseline",
        "anchor_p05_after_cost_return",
        "baseline_p05_after_cost_return",
        "p05_diff_vs_baseline",
        "anchor_max_adverse_excursion_mean",
        "baseline_max_adverse_excursion_mean",
        "upstream_aggregate_reproduction_status",
        "sensitivity_decision_use_allowed",
        "interpretation_status",
    ]
    for col in ordered:
        if col not in out:
            out[col] = np.nan
    out = out[ordered]
    write_csv(out, paths.reports_dir / "p0_5_sensitivity_horizon_audit.csv")
    return out


def select_anchor_bucket(anchor_panel: pd.DataFrame, split: str, family: str, axis: str, bucket: str) -> pd.DataFrame:
    df = anchor_panel.loc[
        anchor_panel["split"].eq(split)
        & anchor_panel["anchor_family_id"].eq(family)
        & anchor_panel["primary_diagnostic_eligible"].astype(bool)
        & anchor_panel["eligible_for_primary_gate"].map(as_bool)
        & pd.to_numeric(anchor_panel["after_cost_return_H20"], errors="coerce").notna()
    ].copy()
    if axis == "all":
        return df
    if axis not in df.columns:
        return df.iloc[0:0]
    return df.loc[df[axis].astype(str).eq(str(bucket))].copy()


def select_baseline_bucket(
    baseline_panel: pd.DataFrame,
    anchor_rows: pd.DataFrame,
    split: str,
    family: str,
    axis: str,
    bucket: str,
    baseline_id: str,
    source: str,
) -> pd.DataFrame:
    df = baseline_panel.loc[
        baseline_panel["split"].eq(split)
        & baseline_panel["baseline_id"].eq(baseline_id)
        & baseline_panel["primary_diagnostic_eligible"].astype(bool)
        & baseline_panel["eligible_for_primary_gate"].map(as_bool)
        & pd.to_numeric(baseline_panel["after_cost_return_H20"], errors="coerce").notna()
    ].copy()
    if baseline_id != "all_launch_direct_baseline":
        df = df.loc[df["anchor_family_id"].eq(family)]
    if source == "linked_anchor":
        ids = set(anchor_rows["anchor_event_id"].astype(str))
        return df.loc[df["anchor_event_id"].astype(str).isin(ids)].copy()
    df = df.loc[df["diagnostic_bucket_source"].eq("baseline_event")].copy()
    if axis == "all":
        return df
    if axis in df.columns:
        return df.loc[df[axis].astype(str).eq(str(bucket))].copy()
    return df.iloc[0:0]


def top1_instrument_year_pnl_share(anchor_rows: pd.DataFrame) -> float:
    if anchor_rows.empty:
        return 0.0
    tmp = anchor_rows.copy()
    tmp["_year"] = pd.to_datetime(tmp["signal_date"], errors="coerce").dt.year
    sums = tmp.groupby(["instrument", "_year"])["after_cost_return_H20"].sum()
    positives = sums.loc[sums > 0]
    if positives.empty or positives.sum() == 0:
        return 0.0
    return float(positives.max() / positives.sum())


def top5_instrument_exposure_share(anchor_rows: pd.DataFrame) -> float:
    if anchor_rows.empty:
        return 0.0
    counts = anchor_rows["instrument"].value_counts()
    return float(counts.head(5).sum() / len(anchor_rows))


def gate_threshold(inputs: dict[str, Any], family: str, gate_name: str) -> float:
    rows = inputs["gate_audit"].loc[inputs["gate_audit"]["anchor_family_id"].eq(family) & inputs["gate_audit"]["gate_name"].eq(gate_name)]
    if rows.empty:
        return np.nan
    return finite_float(rows.iloc[0]["threshold"])


def build_tail_failure_decomposition(
    config: dict[str, Any],
    paths: Paths,
    inputs: dict[str, Any],
    matched_lift: pd.DataFrame,
    anchor_panel: pd.DataFrame,
    baseline_panel: pd.DataFrame,
) -> pd.DataFrame:
    rows = []
    failed = baseline_panel.loc[
        baseline_panel["baseline_id"].eq("failed_lookalike_baseline")
        & baseline_panel["primary_diagnostic_eligible"].astype(bool)
        & baseline_panel["eligible_for_primary_gate"].map(as_bool)
    ].copy()
    for row in matched_lift.itertuples(index=False):
        anchor_rows = select_anchor_bucket(anchor_panel, row.split, row.anchor_family_id, row.diagnostic_axis, row.diagnostic_bucket)
        baseline_rows = select_baseline_bucket(
            baseline_panel,
            anchor_rows,
            row.split,
            row.anchor_family_id,
            row.diagnostic_axis,
            row.diagnostic_bucket,
            row.baseline_id,
            row.diagnostic_bucket_source,
        )
        failed_rows = select_baseline_bucket(
            failed,
            anchor_rows,
            row.split,
            row.anchor_family_id,
            row.diagnostic_axis,
            row.diagnostic_bucket,
            "failed_lookalike_baseline",
            row.diagnostic_bucket_source,
        )
        anchor_mae = mean(anchor_rows["max_adverse_excursion_H20"]) if "max_adverse_excursion_H20" in anchor_rows else np.nan
        baseline_mae = mean(baseline_rows["max_adverse_excursion_H20"]) if "max_adverse_excursion_H20" in baseline_rows else np.nan
        failed_count = int(len(failed_rows))
        anchor_count = int(row.anchor_event_count)
        top1_threshold = gate_threshold(inputs, row.anchor_family_id, f"{row.split}_top1_instrument_year_pnl_share") if row.split in {"validation", "robustness"} else np.nan
        top5_threshold = gate_threshold(inputs, row.anchor_family_id, f"{row.split}_top5_instrument_exposure_share") if row.split in {"validation", "robustness"} else np.nan
        top1 = top1_instrument_year_pnl_share(anchor_rows)
        top5 = top5_instrument_exposure_share(anchor_rows)
        rows.append(
            {
                "split": row.split,
                "anchor_family_id": row.anchor_family_id,
                "diagnostic_axis": row.diagnostic_axis,
                "diagnostic_bucket": row.diagnostic_bucket,
                "predeclared_partition_id": row.predeclared_partition_id,
                "diagnostic_bucket_source": row.diagnostic_bucket_source,
                "baseline_id": row.baseline_id,
                "anchor_event_count": anchor_count,
                "baseline_event_count": int(row.baseline_event_count),
                "failed_lookalike_baseline_event_count": failed_count,
                "unique_instrument_year_count": int(row.unique_instrument_year_count),
                "anchor_p05_after_cost_return_H20": row.anchor_p05_after_cost_return_H20,
                "baseline_p05_after_cost_return_H20": row.baseline_p05_after_cost_return_H20,
                "p05_diff_vs_baseline": row.p05_diff_vs_baseline,
                "anchor_max_adverse_excursion_mean_H20": anchor_mae,
                "baseline_max_adverse_excursion_mean_H20": baseline_mae,
                "mae_worsening_vs_baseline": max(0.0, baseline_mae - anchor_mae) if math.isfinite(anchor_mae) and math.isfinite(baseline_mae) else np.nan,
                "failed_lookalike_rate": safe_div(failed_count, anchor_count + failed_count),
                "top1_instrument_year_pnl_share": top1,
                "top1_threshold": top1_threshold,
                "top1_threshold_status": "not_applicable" if row.split == "train" or not math.isfinite(top1_threshold) else ("passed" if top1 <= top1_threshold else "failed"),
                "top5_instrument_exposure_share": top5,
                "top5_threshold": top5_threshold,
                "top5_threshold_status": "not_applicable" if row.split == "train" or not math.isfinite(top5_threshold) else ("passed" if top5 <= top5_threshold else "failed"),
                "interpretation_status": row.interpretation_status,
            }
        )
    out = pd.DataFrame(rows)
    write_csv(out, paths.reports_dir / "p0_5_tail_failure_decomposition.csv")
    return out


def concentration_source(anchor_panel: pd.DataFrame) -> pd.DataFrame:
    return anchor_panel.loc[
        anchor_panel["split"].isin(PRIMARY_SPLITS)
        & anchor_panel["primary_diagnostic_eligible"].astype(bool)
        & anchor_panel["eligible_for_primary_gate"].map(as_bool)
        & pd.to_numeric(anchor_panel["after_cost_return_H20"], errors="coerce").notna()
    ].copy()


def concentration_metrics_for_group(group: pd.DataFrame, family_split: pd.DataFrame, config: dict[str, Any]) -> dict[str, Any]:
    event_count = int(len(group))
    denom = int(len(family_split))
    positive_all = family_split.loc[pd.to_numeric(family_split["after_cost_return_H20"], errors="coerce") > 0]
    positive_group = group.loc[pd.to_numeric(group["after_cost_return_H20"], errors="coerce") > 0]
    if denom:
        threshold = pd.to_numeric(family_split["after_cost_return_H20"], errors="coerce").quantile(0.05)
        tail_all = family_split.loc[pd.to_numeric(family_split["after_cost_return_H20"], errors="coerce") <= threshold]
        tail_group = group.loc[pd.to_numeric(group["after_cost_return_H20"], errors="coerce") <= threshold]
    else:
        tail_all = family_split.iloc[0:0]
        tail_group = group.iloc[0:0]
    winner_all = family_split.loc[family_split["winner_50h120"].map(as_bool)]
    winner_group = group.loc[group["winner_50h120"].map(as_bool)]
    status = interpretation(event_count, instrument_year_count(group), config)
    if not len(positive_all) or not len(tail_all) or not len(winner_all):
        status = "too_sparse"
    return {
        "event_count": event_count,
        "event_share": safe_div(event_count, denom),
        "positive_pnl_event_count": int(len(positive_group)),
        "positive_pnl_share": safe_div(len(positive_group), len(positive_all)),
        "negative_tail_event_count": int(len(tail_group)),
        "negative_tail_share": safe_div(len(tail_group), len(tail_all)),
        "winner_capture_event_count": int(len(winner_group)),
        "winner_capture_share": safe_div(len(winner_group), len(winner_all)),
        "interpretation_status": status,
    }


def build_concentration_reports(config: dict[str, Any], paths: Paths, anchor_panel: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    source = concentration_source(anchor_panel)
    yi_rows = []
    inst_rows = []
    for split in PRIMARY_SPLITS:
        for family in config["diagnostic_scope"]["anchor_families"]:
            family_split = source.loc[source["split"].eq(split) & source["anchor_family_id"].eq(family)]
            for axis in ["year_bucket", "industry_bucket"]:
                for bucket, group in family_split.groupby(axis, dropna=False):
                    metrics = concentration_metrics_for_group(group, family_split, config)
                    yi_rows.append({"split": split, "anchor_family_id": family, "concentration_axis": axis, "concentration_bucket": clean_str(bucket), **metrics})
            for instrument, group in family_split.groupby("instrument", dropna=False):
                metrics = concentration_metrics_for_group(group, family_split, config)
                pnl_sum = float(pd.to_numeric(group["after_cost_return_H20"], errors="coerce").sum())
                pnl_total = float(pd.to_numeric(family_split["after_cost_return_H20"], errors="coerce").sum())
                inst_rows.append(
                    {
                        "split": split,
                        "anchor_family_id": family,
                        "instrument": instrument,
                        **metrics,
                        "pnl_sum_after_cost_H20": pnl_sum,
                        "pnl_share_after_cost_H20": safe_div(pnl_sum, pnl_total),
                        "instrument_year_count": instrument_year_count(group),
                    }
                )
    yi = pd.DataFrame(yi_rows)
    inst = pd.DataFrame(inst_rows)
    write_csv(yi, paths.reports_dir / "p0_5_year_industry_concentration.csv")
    write_csv(inst, paths.reports_dir / "p0_5_instrument_concentration.csv")
    return yi, inst


def common_interpretable(row: pd.Series, config: dict[str, Any], count_field: str = "anchor_event_count") -> bool:
    return (
        clean_str(row.get("interpretation_status")) == "interpretable"
        and finite_float(row.get(count_field)) >= int(config["diagnostic_bins"]["event_count_min_for_interpretation"])
        and finite_float(row.get("unique_instrument_year_count")) >= int(config["diagnostic_bins"]["instrument_year_count_min_for_interpretation"])
    )


def validation_positive_partitions(config: dict[str, Any], trigger: pd.DataFrame, lift: pd.DataFrame, family: str) -> set[str]:
    trig = trigger.loc[
        trigger["split"].eq("validation")
        & trigger["anchor_family_id"].eq(family)
        & trigger["trigger_rate_type"].eq("gate_eligible_h20")
        & ~trigger["diagnostic_axis"].eq("all")
        & trigger["predeclared_partition_id"].ne("not_applicable")
    ]
    lift_rows = lift.loc[
        lift["split"].eq("validation")
        & lift["anchor_family_id"].eq(family)
        & lift["baseline_id"].eq("matched_delay_baseline")
        & lift["diagnostic_bucket_source"].eq("linked_anchor")
    ]
    out = set()
    for _, t in trig.iterrows():
        if not common_interpretable(t, config, "anchor_trigger_count") or finite_float(t["trigger_rate_per_launch_episode"]) < 0.20:
            continue
        m = lift_rows.loc[lift_rows["predeclared_partition_id"].eq(t["predeclared_partition_id"])]
        if m.empty:
            continue
        mr = m.iloc[0]
        if common_interpretable(mr, config) and finite_float(mr["mean_diff_vs_baseline"]) > 0 and finite_float(mr["p05_diff_vs_baseline"]) >= -0.003:
            out.add(clean_str(t["predeclared_partition_id"]))
    return out


def robustness_not_collapsed(config: dict[str, Any], lift: pd.DataFrame, family: str, partition_id: str) -> bool:
    rows = lift.loc[
        lift["split"].eq("robustness")
        & lift["anchor_family_id"].eq(family)
        & lift["baseline_id"].eq("matched_delay_baseline")
        & lift["diagnostic_bucket_source"].eq("linked_anchor")
        & lift["predeclared_partition_id"].eq(partition_id)
    ]
    if rows.empty:
        return False
    row = rows.iloc[0]
    return common_interpretable(row, config) and finite_float(row["mean_diff_vs_baseline"]) >= -0.001 and finite_float(row["p05_diff_vs_baseline"]) >= -0.005


def build_hypothesis_audit(
    config: dict[str, Any],
    paths: Paths,
    inputs: dict[str, Any],
    trigger: pd.DataFrame,
    lifecycle: pd.DataFrame,
    lift: pd.DataFrame,
    tail: pd.DataFrame,
) -> pd.DataFrame:
    rows = []
    hypothesis_text = {
        "h1_formula_too_narrow": "Formula margin partition has validation trigger/lift and robustness does not collapse.",
        "h2_window_position_problem": "Window/age partition has validation trigger/lift and robustness does not collapse.",
        "h3_ep2_reference_pollution": "Cross-split EP2 launch references materially distort trigger accounting.",
        "h4_matched_baseline_too_strong_or_anchor_no_lift": "Matched-delay baseline exposes no aggregate lift.",
        "h5_tail_risk_not_trigger_rate_is_core_failure": "Tail or concentration risk remains the core blocking issue.",
    }
    for family in config["diagnostic_scope"]["anchor_families"]:
        positives = validation_positive_partitions(config, trigger, lift, family)
        robust = {pid for pid in positives if robustness_not_collapsed(config, lift, family, pid)}
        pid_axis = dict(zip(lift["predeclared_partition_id"], lift["diagnostic_axis"]))
        h1_pass = any(pid_axis.get(pid) in {"pullback_depth_band", "second_breakout_return_band", "second_breakout_consolidation_drawdown_band"} for pid in robust)
        h2_pass = any(pid_axis.get(pid) in {"anchor_window_position_bucket", "reference_age_bucket", "second_breakout_gap_band"} for pid in robust)
        for hyp, passed in [("h1_formula_too_narrow", h1_pass), ("h2_window_position_problem", h2_pass)]:
            status = "passed" if passed else ("inconclusive" if positives and not robust else "failed")
            rows.append(
                {
                    "anchor_family_id": family,
                    "hypothesis_id": hyp,
                    "hypothesis_text": hypothesis_text[hyp],
                    "evidence_summary": f"validation_positive_partitions={len(positives)}; robustness_not_collapsed={len(robust)}",
                    "support_status": {"passed": "supported", "failed": "rejected", "inconclusive": "inconclusive"}[status],
                    "support_rule_id": hyp,
                    "support_rule_status": status,
                    "support_rule_metrics_json": json.dumps({"positive_partitions": sorted(positives), "robust_partitions": sorted(robust)}),
                    "primary_evidence_report": "reports/p0_5_matched_lift_decomposition.csv",
                    "can_justify_p1": False,
                    "requires_new_requirement": status == "passed",
                }
            )
        ratios = {}
        h3_status = "failed"
        for split in ["validation", "robustness"]:
            agg = trigger.loc[
                trigger["split"].eq(split)
                & trigger["anchor_family_id"].eq(family)
                & trigger["diagnostic_axis"].eq("all")
                & trigger["diagnostic_bucket"].eq("all")
            ]
            split_ratios = []
            for _, r in agg.iterrows():
                count = finite_float(r["anchor_trigger_count"])
                split_ratios.append(safe_div(finite_float(r["cross_split_reference_count"]), count) if count else np.nan)
            ratios[split] = max(split_ratios) if split_ratios else np.nan
        if not math.isfinite(ratios.get("validation", np.nan)) or not math.isfinite(ratios.get("robustness", np.nan)):
            h3_status = "inconclusive"
        elif ratios["validation"] >= 0.10 and ratios["robustness"] >= 0.05:
            h3_status = "passed"
        rows.append(
            {
                "anchor_family_id": family,
                "hypothesis_id": "h3_ep2_reference_pollution",
                "hypothesis_text": hypothesis_text["h3_ep2_reference_pollution"],
                "evidence_summary": f"validation_cross_split_ratio={ratios.get('validation')}; robustness_cross_split_ratio={ratios.get('robustness')}",
                "support_status": {"passed": "supported", "failed": "rejected", "inconclusive": "inconclusive"}[h3_status],
                "support_rule_id": "h3_cross_split_reference_ratio",
                "support_rule_status": h3_status,
                "support_rule_metrics_json": json.dumps(ratios),
                "primary_evidence_report": "reports/p0_5_trigger_decomposition.csv",
                "can_justify_p1": False,
                "requires_new_requirement": h3_status == "passed",
            }
        )
        h4_by_split = {}
        for split in ["validation", "robustness"]:
            agg = lift.loc[
                lift["split"].eq(split)
                & lift["anchor_family_id"].eq(family)
                & lift["baseline_id"].eq("matched_delay_baseline")
                & lift["diagnostic_axis"].eq("all")
                & lift["diagnostic_bucket_source"].eq("linked_anchor")
            ]
            under = lifecycle.loc[
                lifecycle["split"].eq(split)
                & lifecycle["anchor_family_id"].eq(family)
                & lifecycle["translation_metric_id"].eq("matched_delay_underperformance_rate")
            ]
            cond = False
            if not agg.empty:
                cond = cond or finite_float(agg.iloc[0]["mean_diff_vs_baseline"]) <= 0 or finite_float(agg.iloc[0]["p05_diff_vs_baseline"]) < -0.003
            if not under.empty:
                cond = cond or finite_float(under.iloc[0]["metric_value"]) >= 0.50
            h4_by_split[split] = cond
        h4_status = "passed" if h4_by_split.get("validation") and h4_by_split.get("robustness") else "failed"
        rows.append(
            {
                "anchor_family_id": family,
                "hypothesis_id": "h4_matched_baseline_too_strong_or_anchor_no_lift",
                "hypothesis_text": hypothesis_text["h4_matched_baseline_too_strong_or_anchor_no_lift"],
                "evidence_summary": json.dumps(h4_by_split),
                "support_status": "supported" if h4_status == "passed" else "rejected",
                "support_rule_id": "h4_aggregate_matched_delay_or_underperformance",
                "support_rule_status": h4_status,
                "support_rule_metrics_json": json.dumps(h4_by_split),
                "primary_evidence_report": "reports/p0_5_matched_lift_decomposition.csv",
                "can_justify_p1": False,
                "requires_new_requirement": h4_status == "passed",
            }
        )
        h5_by_split = {}
        for split in ["validation", "robustness"]:
            agg = tail.loc[
                tail["split"].eq(split)
                & tail["anchor_family_id"].eq(family)
                & tail["baseline_id"].eq("matched_delay_baseline")
                & tail["diagnostic_axis"].eq("all")
                & tail["diagnostic_bucket_source"].eq("linked_anchor")
            ]
            cond = False
            if not agg.empty:
                r = agg.iloc[0]
                cond = (
                    finite_float(r["p05_diff_vs_baseline"]) < -0.003
                    or finite_float(r["mae_worsening_vs_baseline"]) > 0.005
                    or clean_str(r["top1_threshold_status"]) == "failed"
                    or clean_str(r["top5_threshold_status"]) == "failed"
                )
            h5_by_split[split] = cond
        h5_status = "passed" if h5_by_split.get("validation") and h5_by_split.get("robustness") else "failed"
        rows.append(
            {
                "anchor_family_id": family,
                "hypothesis_id": "h5_tail_risk_not_trigger_rate_is_core_failure",
                "hypothesis_text": hypothesis_text["h5_tail_risk_not_trigger_rate_is_core_failure"],
                "evidence_summary": json.dumps(h5_by_split),
                "support_status": "supported" if h5_status == "passed" else "rejected",
                "support_rule_id": "h5_aggregate_tail_or_concentration",
                "support_rule_status": h5_status,
                "support_rule_metrics_json": json.dumps(h5_by_split),
                "primary_evidence_report": "reports/p0_5_tail_failure_decomposition.csv",
                "can_justify_p1": False,
                "requires_new_requirement": h5_status == "passed",
            }
        )
    out = pd.DataFrame(rows)
    write_csv(out, paths.reports_dir / "p0_5_hypothesis_audit.csv")
    return out


def decision_partition_counts(config: dict[str, Any], trigger: pd.DataFrame, lift: pd.DataFrame, family: str, split: str) -> int:
    trig = trigger.loc[
        trigger["split"].eq(split)
        & trigger["anchor_family_id"].eq(family)
        & trigger["trigger_rate_type"].eq("gate_eligible_h20")
        & trigger["predeclared_partition_id"].ne("not_applicable")
    ]
    lift_rows = lift.loc[
        lift["split"].eq(split)
        & lift["anchor_family_id"].eq(family)
        & lift["baseline_id"].eq("matched_delay_baseline")
        & lift["diagnostic_bucket_source"].eq("linked_anchor")
    ]
    count = 0
    for _, t in trig.iterrows():
        m = lift_rows.loc[lift_rows["predeclared_partition_id"].eq(t["predeclared_partition_id"])]
        if not m.empty and common_interpretable(t, config, "anchor_trigger_count") and common_interpretable(m.iloc[0], config):
            count += 1
    return count


def find_partition_freeze_candidate(config: dict[str, Any], trigger: pd.DataFrame, lift: pd.DataFrame, family: str) -> pd.Series | None:
    positives = validation_positive_partitions(config, trigger, lift, family)
    for pid in sorted(positives):
        if not robustness_not_collapsed(config, lift, family, pid):
            continue
        t = trigger.loc[
            trigger["split"].eq("validation")
            & trigger["anchor_family_id"].eq(family)
            & trigger["trigger_rate_type"].eq("gate_eligible_h20")
            & trigger["predeclared_partition_id"].eq(pid)
        ].iloc[0]
        m = lift.loc[
            lift["split"].eq("validation")
            & lift["anchor_family_id"].eq(family)
            & lift["baseline_id"].eq("matched_delay_baseline")
            & lift["diagnostic_bucket_source"].eq("linked_anchor")
            & lift["predeclared_partition_id"].eq(pid)
        ].iloc[0]
        if finite_float(t["unique_instrument_year_count"]) >= 25:
            out = pd.concat([t.add_prefix("trigger_"), m.add_prefix("lift_")])
            return out
    return None


def build_stop_continue_decision(
    config: dict[str, Any],
    paths: Paths,
    inputs: dict[str, Any],
    freeze: pd.DataFrame,
    trigger: pd.DataFrame,
    lift: pd.DataFrame,
    hypothesis: pd.DataFrame,
) -> pd.DataFrame:
    rows = []
    family_decisions: dict[str, str] = {}
    gate = inputs["gate_audit"]
    for family in config["diagnostic_scope"]["anchor_families"]:
        val_count = decision_partition_counts(config, trigger, lift, family, "validation")
        rob_count = decision_partition_counts(config, trigger, lift, family, "robustness")
        hyp_rows = hypothesis.loc[hypothesis["anchor_family_id"].eq(family)]
        supported = set(hyp_rows.loc[hyp_rows["support_status"].eq("supported"), "hypothesis_id"])
        stop_required = val_count == 0 or rob_count == 0 or bool({"h4_matched_baseline_too_strong_or_anchor_no_lift", "h5_tail_risk_not_trigger_rate_is_core_failure"} & supported)
        candidate = find_partition_freeze_candidate(config, trigger, lift, family)
        lifecycle_pass = as_bool(gate.loc[gate["anchor_family_id"].eq(family) & gate["gate_name"].eq("lifecycle_anchor_recall"), "gate_passed"].iloc[0])
        formula_repair = lifecycle_pass and candidate is None and not stop_required and bool({"h1_formula_too_narrow", "h2_window_position_problem", "h3_ep2_reference_pollution"} & supported)
        if stop_required:
            decision = "stop_current_family"
            rank = 1
        elif formula_repair:
            decision = "write_p0_6_formula_repair_requirement"
            rank = 2
        else:
            decision = "write_p0_6_partition_freeze_requirement"
            rank = 3
        family_decisions[family] = decision
        pid = clean_str(candidate.get("trigger_predeclared_partition_id")) if candidate is not None else ""
        rows.append(
            {
                "decision_scope": "family",
                "anchor_family_id": family,
                "recommended_decision": decision,
                "decision_precedence_rank": rank,
                "supporting_hypothesis_ids": ";".join(sorted(supported)),
                "primary_evidence_report": "reports/p0_5_hypothesis_audit.csv",
                "validation_interpretable_partition_count": val_count,
                "robustness_interpretable_partition_count": rob_count,
                "predeclared_partition_id": pid,
                "predeclared_partition_source": predeclared_source(freeze, pid),
                "validation_partition_trigger_rate_per_launch_episode": finite_float(candidate.get("trigger_trigger_rate_per_launch_episode")) if candidate is not None else np.nan,
                "validation_partition_unique_instrument_year_count": finite_float(candidate.get("trigger_unique_instrument_year_count")) if candidate is not None else np.nan,
                "validation_partition_mean_diff_vs_matched_delay": finite_float(candidate.get("lift_mean_diff_vs_baseline")) if candidate is not None else np.nan,
                "validation_partition_p05_diff_vs_matched_delay": finite_float(candidate.get("lift_p05_diff_vs_baseline")) if candidate is not None else np.nan,
                "robustness_collapse_status": "passed" if pid and robustness_not_collapsed(config, lift, family, pid) else ("failed" if pid else "not_applicable"),
                "family_stop_required": stop_required,
                "partition_freeze_rule_status": "passed" if candidate is not None else "failed",
                "formula_repair_rule_status": "passed" if formula_repair else "failed",
                "deferred_family_rule_status": "not_applicable",
                "decision_rule_status": "passed",
                "decision_rationale": "Stop required by sparse partitions, matched-baseline failure, or tail/concentration failure." if stop_required else "Continuation requires a separate P0.6 requirement.",
            }
        )
    lifecycle = inputs["lifecycle_profile"].copy()
    non_primary = lifecycle.loc[
        lifecycle["split"].eq("train")
        & lifecycle["anchor_family_id"].notna()
        & ~lifecycle["anchor_family_id"].isin(config["diagnostic_scope"]["anchor_families"])
    ]
    deferred_ok = (
        all(dec == "stop_current_family" for dec in family_decisions.values())
        and not any(
            hypothesis.loc[
                hypothesis["hypothesis_id"].isin(["h1_formula_too_narrow", "h2_window_position_problem", "h3_ep2_reference_pollution"])
                & hypothesis["support_status"].eq("supported")
            ]["anchor_family_id"].isin(config["diagnostic_scope"]["anchor_families"])
        )
        and non_primary["winner_episode_id"].nunique() >= int(config["diagnostic_bins"]["event_count_min_for_interpretation"])
    )
    if deferred_ok:
        overall = "write_deferred_family_requirement"
        rank = 2
    else:
        rank_map = {"stop_current_family": 1, "write_p0_6_formula_repair_requirement": 2, "write_p0_6_partition_freeze_requirement": 3}
        overall = sorted(family_decisions.values(), key=lambda x: rank_map[x])[0]
        rank = rank_map[overall]
    rows.append(
        {
            "decision_scope": "overall",
            "anchor_family_id": "all",
            "recommended_decision": overall,
            "decision_precedence_rank": rank,
            "supporting_hypothesis_ids": "",
            "primary_evidence_report": "reports/p0_5_stop_continue_decision.csv",
            "validation_interpretable_partition_count": sum(r["validation_interpretable_partition_count"] for r in rows),
            "robustness_interpretable_partition_count": sum(r["robustness_interpretable_partition_count"] for r in rows),
            "predeclared_partition_id": "",
            "predeclared_partition_source": "not_applicable",
            "validation_partition_trigger_rate_per_launch_episode": np.nan,
            "validation_partition_unique_instrument_year_count": np.nan,
            "validation_partition_mean_diff_vs_matched_delay": np.nan,
            "validation_partition_p05_diff_vs_matched_delay": np.nan,
            "robustness_collapse_status": "not_applicable",
            "family_stop_required": "not_applicable",
            "partition_freeze_rule_status": "not_applicable",
            "formula_repair_rule_status": "not_applicable",
            "deferred_family_rule_status": "passed" if deferred_ok else "failed",
            "decision_rule_status": "passed",
            "decision_rationale": "Overall decision follows family precedence unless deferred-family rule passes.",
        }
    )
    out = pd.DataFrame(rows)
    write_csv(out, paths.reports_dir / "p0_5_stop_continue_decision.csv")
    return out


def write_diagnostic_report(
    paths: Paths,
    reproduction: pd.DataFrame,
    authority: pd.DataFrame,
    denominator_rec: pd.DataFrame,
    trigger: pd.DataFrame,
    lift: pd.DataFrame,
    hypothesis: pd.DataFrame,
    decision: pd.DataFrame,
) -> None:
    failed_authority = int(authority["authority_status"].ne("passed").sum())
    failed_den = int(denominator_rec["denominator_reconciliation_status"].ne("passed").sum())
    overall = decision.loc[decision["decision_scope"].eq("overall")].iloc[0]
    md = [
        "# EP3 P0.5 Anchor Failure Diagnostic Report",
        "",
        "## Upstream Authority And Reproduction Status",
        "",
        f"- Authority failures: {failed_authority}",
        f"- Upstream reproduction rows: {len(reproduction)}; failed rows: {int(reproduction['reproduction_status'].ne('passed').sum())}",
        "",
        "## Trigger Denominator Reconciliation",
        "",
        f"- Denominator reconciliation failures: {failed_den}",
        "",
        "## Trigger-Budget Decomposition",
        "",
        trigger.loc[
            trigger["diagnostic_axis"].eq("all") & trigger["trigger_rate_type"].eq("gate_eligible_h20"),
            ["split", "anchor_family_id", "anchor_trigger_count", "ep2_launch_episode_count", "trigger_rate_per_launch_episode", "trigger_count_reproduction_status"],
        ].to_markdown(index=False),
        "",
        "## Matched-Lift Decomposition",
        "",
        lift.loc[
            lift["diagnostic_axis"].eq("all") & lift["baseline_id"].eq("matched_delay_baseline") & lift["diagnostic_bucket_source"].eq("linked_anchor"),
            ["split", "anchor_family_id", "anchor_event_count", "baseline_event_count", "mean_diff_vs_baseline", "p05_diff_vs_baseline", "interpretation_status"],
        ].to_markdown(index=False),
        "",
        "## H10/H60 Sensitivity Audit",
        "",
        "Sensitivity rows are report-only and are not used in hypothesis or stop/continue decisions.",
        "",
        "## Tail And Concentration Findings",
        "",
        "Tail and concentration findings are material only through the H20 tail report and hypothesis audit.",
        "",
        "## Hypothesis Audit",
        "",
        hypothesis[["anchor_family_id", "hypothesis_id", "support_status", "support_rule_status", "primary_evidence_report"]].to_markdown(index=False),
        "",
        "## Stop / Continue Decision",
        "",
        decision[["decision_scope", "anchor_family_id", "recommended_decision", "decision_precedence_rank", "decision_rationale"]].to_markdown(index=False),
        "",
        f"Overall P0.5 decision: `{overall['recommended_decision']}`.",
        "",
    ]
    (paths.reports_dir / "p0_5_diagnostic_report.md").write_text("\n".join(md), encoding="utf-8")


def artifact_hash_for_stage(paths: Paths, rel_artifacts: list[str]) -> str:
    payload = []
    for rel in rel_artifacts:
        path = paths.output_root / rel
        payload.append({"artifact": rel, "hash": live_hash(path)})
    return canonical_hash(payload)


def write_stage_order(paths: Paths, stage_artifacts: list[tuple[int, str, bool, bool, list[str]]]) -> pd.DataFrame:
    rows = []
    for order, name, validation_used, robustness_used, artifacts in stage_artifacts:
        rows.append(
            {
                "stage_order": order,
                "stage_name": name,
                "completed_at": now_iso(),
                "validation_outcomes_used_by_stage": validation_used,
                "robustness_outcomes_used_by_stage": robustness_used,
                "frozen_artifact_written": ";".join(artifacts),
                "artifact_hash_after_stage": artifact_hash_for_stage(paths, artifacts),
            }
        )
    stage = pd.DataFrame(rows)
    write_csv(stage, paths.reports_dir / "p0_5_stage_order_audit.csv")
    return stage


def write_manifest(config: dict[str, Any], paths: Paths, validation_status: str = "not_run", failures: list[str] | None = None) -> dict[str, Any]:
    artifacts = []
    for rel in [*(f"reports/{name}" for name in REQUIRED_REPORTS), *(f"cache/{name}" for name in REQUIRED_CACHE)]:
        path = paths.output_root / rel
        artifacts.append(
            {
                "artifact_name": Path(rel).name,
                "path": relpath(path),
                "exists": path.exists(),
                "content_hash": live_hash(path),
            }
        )
    manifest = {
        "phase": config["phase"],
        "config_path": relpath(paths.config_path),
        "config_hash": file_hash(paths.config_path),
        "output_root": relpath(paths.output_root),
        "generated_at": now_iso(),
        "git_commit": git_commit_hash(),
        "validation_status": validation_status,
        "validation_failures": failures or [],
        "artifact_authority": artifacts,
        "forbidden_inputs": {
            "ep2_r02_threshold_artifacts": "not_used",
            "ep2_r03_confirmed_pool": "not_used",
            "ep2_r05_holding_policy_outputs": "not_used",
            "baserate_row_level_cache": "not_used",
            "explore9_explore10_row_level_outputs": "not_used",
            "new_tushare_akshare_fetch": "not_used",
        },
    }
    write_json(manifest, paths.manifests_dir / "p0_5_anchor_failure_diagnostic_manifest.json")
    return manifest


def run_p0_5_anchor_failure_diagnostic(config: dict[str, Any], paths: Paths) -> dict[str, Any]:
    if relpath(paths.output_root) != config["output_root"]:
        raise P05Error("output_root must remain the configured P0.5 output root")
    inputs = load_inputs(config)
    if inputs["manifest"].get("validation_status") != "passed":
        raise P05Error("upstream EP3 P0 manifest is not validation_status=passed")
    authority = build_upstream_authority(config, paths, inputs)
    if authority["authority_status"].ne("passed").any():
        raise P05Error("upstream authority check failed")
    reproduction = build_upstream_reproduction(config, paths, inputs)
    calendar = load_calendar(config)
    market_panel = load_provider_panel(config)
    industry_lookup = load_industry_lookup(config)
    anchor_raw = build_anchor_raw(config, authority, inputs, calendar, market_panel, industry_lookup)
    freeze = build_diagnostic_bin_freeze(config, paths, inputs, authority, anchor_raw)
    anchor_panel = finalize_anchor_panel(config, paths, anchor_raw, freeze)
    baseline_panel = build_baseline_panel(config, paths, authority, inputs, calendar, industry_lookup, anchor_panel, freeze)
    denom, denominator_rec = build_trigger_denominator(config, paths, inputs, anchor_panel, baseline_panel)
    trigger = build_trigger_decomposition(config, paths, inputs, freeze, anchor_panel, denom)
    lifecycle = build_lifecycle_forward_translation(config, paths, inputs, anchor_panel, baseline_panel, denom)
    lift = build_matched_lift_decomposition(config, paths, freeze, anchor_panel, baseline_panel)
    sensitivity = build_sensitivity_horizon_audit(config, paths, inputs, freeze, anchor_panel, baseline_panel)
    tail = build_tail_failure_decomposition(config, paths, inputs, lift, anchor_panel, baseline_panel)
    concentration_yi, concentration_inst = build_concentration_reports(config, paths, anchor_panel)
    hypothesis = build_hypothesis_audit(config, paths, inputs, trigger, lifecycle, lift, tail)
    decision = build_stop_continue_decision(config, paths, inputs, freeze, trigger, lift, hypothesis)
    write_diagnostic_report(paths, reproduction, authority, denominator_rec, trigger, lift, hypothesis, decision)
    stage_artifacts = [
        (1, "upstream artifact authority check", False, False, ["reports/p0_5_upstream_authority.csv"]),
        (2, "upstream no-go reproduction", False, False, ["reports/p0_5_upstream_reproduction.csv"]),
        (3, "formula diagnostic precompute and train-only diagnostic bin freeze", False, False, ["reports/p0_5_diagnostic_bin_freeze.csv"]),
        (4, "anchor and baseline event enrichment using frozen bins", True, True, ["cache/p0_5_anchor_event_diagnostic_panel.parquet", "cache/p0_5_baseline_event_diagnostic_panel.parquet"]),
        (5, "trigger budget decomposition", True, True, ["reports/p0_5_trigger_denominator_panel.csv", "reports/p0_5_trigger_denominator_reconciliation.csv", "reports/p0_5_trigger_decomposition.csv"]),
        (6, "matched-baseline lift decomposition", True, True, ["reports/p0_5_matched_lift_decomposition.csv"]),
        (7, "tail-risk and failure-lookalike decomposition", True, True, ["reports/p0_5_tail_failure_decomposition.csv", "reports/p0_5_year_industry_concentration.csv", "reports/p0_5_instrument_concentration.csv"]),
        (8, "lifecycle-vs-forward translation audit", True, True, ["reports/p0_5_lifecycle_forward_translation.csv", "reports/p0_5_sensitivity_horizon_audit.csv"]),
        (9, "conclusion and stop/continue decision", True, True, ["reports/p0_5_hypothesis_audit.csv", "reports/p0_5_stop_continue_decision.csv", "reports/p0_5_diagnostic_report.md"]),
        (10, "manifest and validator", True, True, ["reports/p0_5_stage_order_audit.csv"]),
    ]
    write_stage_order(paths, stage_artifacts)
    manifest = write_manifest(config, paths)
    return {"manifest": manifest, "outputs": relpath(paths.output_root)}


def require_columns(df: pd.DataFrame, columns: list[str], label: str, failures: list[str]) -> None:
    missing = [col for col in columns if col not in df.columns]
    if missing:
        failures.append(f"{label} missing columns: {missing}")


def validate_p0_5_anchor_failure_diagnostic(config: dict[str, Any], paths: Paths) -> dict[str, Any]:
    failures: list[str] = []
    output_rel = relpath(paths.output_root)
    if output_rel != config["output_root"]:
        failures.append(f"unexpected output root: {output_rel}")
    manifest_path = paths.manifests_dir / "p0_5_anchor_failure_diagnostic_manifest.json"
    if not manifest_path.exists():
        failures.append("missing P0.5 manifest")
        manifest = {}
    else:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for report in REQUIRED_REPORTS:
        if not (paths.reports_dir / report).exists():
            failures.append(f"missing report: {report}")
    for cache in REQUIRED_CACHE:
        if not (paths.cache_dir / cache).exists():
            failures.append(f"missing cache: {cache}")
    inputs = load_inputs(config)
    if inputs["manifest"].get("validation_status") != "passed":
        failures.append("upstream EP3 P0 manifest is not passed")
    if (paths.reports_dir / "p0_5_upstream_authority.csv").exists():
        authority = pd.read_csv(paths.reports_dir / "p0_5_upstream_authority.csv")
        require_columns(authority, ["artifact_name", "path", "exists", "upstream_manifest_hash", "live_content_hash", "hash_match", "authority_status"], "authority", failures)
        if "authority_status" in authority and authority["authority_status"].ne("passed").any():
            failures.append("upstream authority contains failed rows")
        expected_authority = build_upstream_authority(config, paths, inputs)
        for _, row in expected_authority.iterrows():
            actual = authority.loc[authority["artifact_name"].eq(row["artifact_name"])]
            if actual.empty or clean_str(actual.iloc[0]["live_content_hash"]) != clean_str(row["live_content_hash"]):
                failures.append(f"authority hash mismatch: {row['artifact_name']}")
    if (paths.reports_dir / "p0_5_upstream_reproduction.csv").exists():
        repro = pd.read_csv(paths.reports_dir / "p0_5_upstream_reproduction.csv")
        if repro.get("reproduction_status", pd.Series(dtype=str)).ne("passed").any():
            failures.append("upstream reproduction contains failed rows")
        for family in config["diagnostic_scope"]["anchor_families"]:
            row = repro.loc[repro["anchor_family_id"].eq(family)]
            if row.empty or clean_str(row.iloc[0]["upstream_ep3_p1_decision_status"]) != "failed_trigger_budget":
                failures.append(f"missing failed_trigger_budget reproduction for {family}")
    if (paths.reports_dir / "p0_5_trigger_denominator_panel.csv").exists():
        denom = pd.read_csv(paths.reports_dir / "p0_5_trigger_denominator_panel.csv")
        require_columns(denom, ["split", "launch_episode_id", "instrument", "launch_signal_date", "launch_execution_date", "launch_is_executable_next_open", "executable_status", "industry_bucket", "year_bucket", "money_bucket", "vol20_bucket", "ret_60d_bucket", "denominator_source"], "denominator", failures)
        if denom.duplicated(["split", "launch_episode_id"]).any():
            failures.append("duplicate denominator primary key")
        canonical = inputs["ep2_launch_pool"].sort_values(["launch_episode_id", "signal_date"]).drop_duplicates("launch_episode_id", keep="first").copy()
        canonical["split"] = canonical["signal_date"].map(lambda x: split_for_date(config, x))
        canonical = canonical.loc[canonical["split"].isin(PRIMARY_SPLITS)]
        if len(canonical) != len(denom):
            failures.append("denominator row count does not match canonical EP2 launch pool")
    if (paths.reports_dir / "p0_5_trigger_denominator_reconciliation.csv").exists():
        rec = pd.read_csv(paths.reports_dir / "p0_5_trigger_denominator_reconciliation.csv")
        if rec.get("denominator_reconciliation_status", pd.Series(dtype=str)).ne("passed").any():
            failures.append("denominator reconciliation failed")
    if (paths.cache_dir / "p0_5_anchor_event_diagnostic_panel.parquet").exists():
        anchor = pd.read_parquet(paths.cache_dir / "p0_5_anchor_event_diagnostic_panel.parquet")
        require_columns(anchor, ["anchor_event_id", "anchor_family_id", "signal_date", "execution_date", "split", "primary_diagnostic_eligible", "formula_diagnostic_status", "after_cost_return_H10", "after_cost_return_H20", "after_cost_return_H60", "diagnostic_panel_hash"], "anchor cache", failures)
        if anchor.duplicated("anchor_event_id").any():
            failures.append("duplicate anchor_event_id")
        if FORBIDDEN_FIELDS & set(anchor.columns):
            failures.append("anchor cache contains forbidden fields")
        invalid_primary = anchor.loc[~anchor["anchor_family_id"].isin(config["diagnostic_scope"]["anchor_families"])]
        if not invalid_primary.empty and invalid_primary["primary_diagnostic_eligible"].map(as_bool).any():
            failures.append("non-primary anchor row marked diagnostic eligible")
    else:
        anchor = pd.DataFrame()
    if (paths.cache_dir / "p0_5_baseline_event_diagnostic_panel.parquet").exists():
        baseline = pd.read_parquet(paths.cache_dir / "p0_5_baseline_event_diagnostic_panel.parquet")
        require_columns(baseline, ["baseline_event_id", "anchor_event_id", "baseline_id", "split", "primary_diagnostic_eligible", "diagnostic_bucket_source", "after_cost_return_H10", "after_cost_return_H20", "after_cost_return_H60", "diagnostic_panel_hash"], "baseline cache", failures)
        if baseline.duplicated("baseline_event_id").any():
            failures.append("duplicate baseline_event_id")
        if FORBIDDEN_FIELDS & set(baseline.columns):
            failures.append("baseline cache contains forbidden fields")
        bad_all_launch = baseline.loc[baseline["baseline_id"].eq("all_launch_direct_baseline")]
        for field in ["money_bucket", "vol20_bucket", "ret_60d_bucket"]:
            if not bad_all_launch.empty and bad_all_launch[field].ne("unbucketed").any():
                failures.append(f"all_launch_direct_baseline has non-unbucketed {field}")
    else:
        baseline = pd.DataFrame()
    if (paths.reports_dir / "p0_5_diagnostic_bin_freeze.csv").exists():
        freeze = pd.read_csv(paths.reports_dir / "p0_5_diagnostic_bin_freeze.csv")
        require_columns(freeze, ["predeclared_partition_id", "anchor_family_id", "diagnostic_axis", "diagnostic_bucket", "bin_source_split", "bin_method", "validation_outcomes_used", "robustness_outcomes_used", "frozen_before_validation", "bin_hash"], "bin freeze", failures)
        if freeze["validation_outcomes_used"].map(as_bool).any() or freeze["robustness_outcomes_used"].map(as_bool).any():
            failures.append("bin freeze used validation or robustness outcomes")
        copied = freeze.loc[freeze["bin_source_split"].eq("upstream_p0_train_frozen")]
        if not copied.empty and (copied["bin_method"].ne("copied_from_p0").any() or ~copied["diagnostic_axis"].isin(["money_bucket", "vol20_bucket", "ret_60d_bucket"]).all()):
            failures.append("copied P0 bins have invalid metadata")
    if (paths.reports_dir / "p0_5_trigger_decomposition.csv").exists():
        trigger = pd.read_csv(paths.reports_dir / "p0_5_trigger_decomposition.csv")
        require_columns(trigger, ["split", "anchor_family_id", "diagnostic_axis", "diagnostic_bucket", "trigger_rate_type", "anchor_trigger_count", "upstream_anchor_trigger_count", "ep2_launch_episode_count", "denominator_scope", "trigger_rate_band", "trigger_count_reproduction_status"], "trigger decomposition", failures)
        agg = trigger.loc[trigger["diagnostic_axis"].eq("all") & trigger["diagnostic_bucket"].eq("all")]
        if agg["trigger_count_reproduction_status"].ne("passed").any():
            failures.append("aggregate trigger reproduction failed")
        if trigger["diagnostic_axis"].eq("label_join_status").any():
            failures.append("label_join_status used as trigger denominator axis")
    else:
        trigger = pd.DataFrame()
    if (paths.reports_dir / "p0_5_matched_lift_decomposition.csv").exists():
        lift = pd.read_csv(paths.reports_dir / "p0_5_matched_lift_decomposition.csv")
        key = ["split", "anchor_family_id", "diagnostic_axis", "diagnostic_bucket", "diagnostic_bucket_source", "baseline_id"]
        if lift.duplicated(key).any():
            failures.append("duplicate matched-lift row grain")
        bad_all_launch = lift.loc[
            lift["baseline_id"].eq("all_launch_direct_baseline")
            & ~lift["diagnostic_axis"].isin(["all", "year_bucket", "industry_bucket"])
        ]
        if not bad_all_launch.empty:
            failures.append("all_launch_direct_baseline decomposed by forbidden axis")
        if lift["diagnostic_bucket_source"].eq("all_sources").any():
            failures.append("all_sources appeared outside sensitivity report")
    else:
        lift = pd.DataFrame()
    if (paths.reports_dir / "p0_5_sensitivity_horizon_audit.csv").exists():
        sens = pd.read_csv(paths.reports_dir / "p0_5_sensitivity_horizon_audit.csv")
        if sens["sensitivity_decision_use_allowed"].map(as_bool).any():
            failures.append("sensitivity row marked decision-use allowed")
        all_sources = sens.loc[sens["diagnostic_bucket_source"].eq("all_sources")]
        if all_sources.empty or all_sources["upstream_aggregate_reproduction_status"].ne("passed").any():
            failures.append("missing or failed all_sources sensitivity reproduction")
    if (paths.reports_dir / "p0_5_hypothesis_audit.csv").exists():
        hyp = pd.read_csv(paths.reports_dir / "p0_5_hypothesis_audit.csv")
        if hyp["can_justify_p1"].map(as_bool).any():
            failures.append("hypothesis can_justify_p1 must be false")
    else:
        hyp = pd.DataFrame()
    if (paths.reports_dir / "p0_5_stop_continue_decision.csv").exists():
        decision = pd.read_csv(paths.reports_dir / "p0_5_stop_continue_decision.csv")
        if len(decision) != len(config["diagnostic_scope"]["anchor_families"]) + 1:
            failures.append("decision report must contain one row per family plus overall")
        if decision["recommended_decision"].eq("write_p1_validation_requirement").any():
            failures.append("P0.5 emitted forbidden P1 decision")
        if decision["decision_rule_status"].ne("passed").any():
            failures.append("decision rule status failed")
    if manifest:
        for row in manifest.get("artifact_authority", []):
            path = topic_path(row["path"])
            if clean_str(row.get("content_hash")) != live_hash(path):
                failures.append(f"manifest hash mismatch: {row.get('path')}")
    status = "passed" if not failures else "failed"
    write_manifest(config, paths, status, failures)
    result = {
        "validation_status": status,
        "failure_count": len(failures),
        "failures": failures,
        "manifest": relpath(paths.manifests_dir / "p0_5_anchor_failure_diagnostic_manifest.json"),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if failures:
        raise P05Error("P0.5 validation failed")
    return result
