#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import math
import platform
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


EXPERIMENT_DIR = Path(__file__).resolve().parents[1]
TOPIC_ROOT = Path(__file__).resolve().parents[4]
REPO_ROOT = Path(__file__).resolve().parents[6]
SRC_DIR = TOPIC_ROOT / "src"

for import_path in (SRC_DIR, Path(__file__).resolve().parent):
    if str(import_path) not in sys.path:
        sys.path.insert(0, str(import_path))

from afml_big_winner.config import load_yaml, stable_hash  # noqa: E402
from afml_big_winner.manifest import file_sha256  # noqa: E402


CONFIG_PATH = EXPERIMENT_DIR / "configs" / "config_11a0_regime_pit_availability_audit.yaml"

RUN_ID = "11A0_regime_pit_availability_audit"
TABLE_DIR = EXPERIMENT_DIR / "outputs" / "publishable" / "tables" / RUN_ID
LOCAL_CACHE_DIR = EXPERIMENT_DIR / "outputs" / "local_cache" / RUN_ID
REPORT_PATH = EXPERIMENT_DIR / "outputs" / "publishable" / "reports" / f"{RUN_ID}_report.md"
MANIFEST_PATH = EXPERIMENT_DIR / "outputs" / "publishable" / f"manifest_{RUN_ID}.json"

FINAL_STABLE = "11A0_regime_pit_available_stable_supported"
FINAL_UNSTABLE = "11A0_regime_pit_available_unstable_readout_only"
FINAL_INCOMPLETE = "11A0_regime_pit_statistics_incomplete"
FINAL_BLOCKED = "11A0_regime_pit_input_blocked"

VALID_BUCKETS = {"risk_on", "risk_off", "transition"}
ALLOWED_CONFIRMATION_TIMES = {"t0_close_next_open_executable", "t0_close"}
SPLITS = ["train", "validation", "robustness"]
USAGE_TARGETS = [
    "11A1_proxy_readout",
    "11A1_matched_base_axis",
    "11B_retention_readout",
    "11C_policy_context",
]


@dataclass(frozen=True)
class Thresholds:
    event_market_agreement_floor: float = 0.995
    event_vs_daily_match_floor: float = 0.995
    t0_regime_available_floor: float = 0.995
    calendar_mismatch_rate_cap: float = 0.005
    daily_conflict_rate_cap: float = 0.01
    date_level_min_n: int = 100
    date_forward_20d_eligible_floor: float = 0.90
    date_flip_end_5d_cap: float = 0.25
    date_flip_end_20d_cap: float = 0.45
    date_confirmation_lag_not_found_20d_cap: float = 0.25
    date_median_regime_age_min: float = 3.0
    ten_a_event_n_min: int = 500
    ten_a_split_event_n_min: int = 100
    ten_a_authority_regime_coverage_floor: float = 0.995

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> "Thresholds":
        raw = config.get("thresholds", {})
        return cls(**{field: raw.get(field, getattr(cls(), field)) for field in cls.__dataclass_fields__})


def git_revision(cwd: Path = REPO_ROOT) -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=cwd,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return result.stdout.strip()


def write_df(path: Path, frame: pd.DataFrame) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False)
    return path


def write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    return path


def write_text(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def resolve_path(value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    text = str(path)
    if text.startswith("topics/"):
        return REPO_ROOT / path
    if text.startswith("../"):
        return (EXPERIMENT_DIR / path).resolve()
    return (EXPERIMENT_DIR / path).resolve()


def path_hash(path: Path) -> str:
    return file_sha256(path) if path.is_file() else ""


def file_mtime_utc(path: Path) -> str:
    if not path.exists():
        return ""
    return datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat()


def normalize_bucket(value: Any) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except TypeError:
        pass
    text = str(value).strip()
    if not text:
        return ""
    lowered = text.lower()
    if lowered in {"missing", "unknown", "nan", "none", "null"}:
        return ""
    return lowered if lowered in VALID_BUCKETS else ""


def normalize_bucket_series(series: pd.Series) -> pd.Series:
    return series.map(normalize_bucket).astype("string")


def boolish(value: Any) -> bool:
    if value is None:
        return False
    try:
        if pd.isna(value):
            return False
    except TypeError:
        pass
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    if isinstance(value, (int, float, np.integer, np.floating)):
        return bool(value)
    return str(value).strip().lower() in {"true", "1", "yes", "y", "t"}


def nonempty(value: Any) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except TypeError:
        pass
    return str(value).strip()


def coalesce_valid_values(*values: Any) -> str:
    for value in values:
        bucket = normalize_bucket(value)
        if bucket:
            return bucket
    return ""


def coalesce_valid_series(series_list: list[pd.Series]) -> pd.Series:
    if not series_list:
        return pd.Series(dtype="string")
    out = pd.Series([""] * len(series_list[0]), index=series_list[0].index, dtype="string")
    unresolved = out.eq("")
    for series in series_list:
        normalized = normalize_bucket_series(series)
        take = unresolved & normalized.ne("")
        out.loc[take] = normalized.loc[take]
        unresolved = out.eq("")
    return out


def first_valid_source(frame: pd.DataFrame, source_cols: list[tuple[str, str]]) -> pd.Series:
    out = pd.Series(["unresolved_missing"] * len(frame), index=frame.index, dtype="string")
    unresolved = out.eq("unresolved_missing")
    for source, col in source_cols:
        normalized = normalize_bucket_series(frame[col])
        take = unresolved & normalized.ne("")
        out.loc[take] = source
        unresolved = out.eq("unresolved_missing")
    return out


def stable_mode(values: pd.Series) -> str:
    normalized = values.map(normalize_bucket)
    counts = normalized.loc[normalized.ne("")].value_counts()
    if counts.empty:
        return ""
    max_count = counts.max()
    return sorted(counts.loc[counts.eq(max_count)].index)[0]


def safe_rate(numerator: int | float, denominator: int | float) -> float:
    if denominator == 0 or pd.isna(denominator):
        return float("nan")
    return float(numerator) / float(denominator)


def rate(series: pd.Series) -> float:
    if len(series) == 0:
        return float("nan")
    return float(series.fillna(False).mean())


def parse_canonical_from_pipe(value: Any) -> str:
    text = nonempty(value)
    if not text:
        return ""
    parts = text.split("|")
    return parts[3].strip() if len(parts) >= 4 and parts[3].strip() else ""


def required_columns_status(frame: pd.DataFrame, required: list[str]) -> tuple[str, str]:
    missing = sorted(set(required) - set(frame.columns))
    if missing:
        return "missing_columns", ",".join(missing)
    return "ok", ""


def read_frame(path: Path) -> pd.DataFrame:
    suffixes = "".join(path.suffixes)
    if suffixes.endswith(".parquet"):
        return pd.read_parquet(path)
    return pd.read_csv(path, low_memory=False)


def quick_row_count(path: Path) -> int | str:
    if not path.exists():
        return ""
    if path.is_dir():
        return len([item for item in path.iterdir() if item.is_file()])
    suffixes = "".join(path.suffixes)
    try:
        if suffixes.endswith(".parquet"):
            import pyarrow.parquet as pq

            return int(pq.ParquetFile(path).metadata.num_rows)
        if suffixes.endswith(".csv") or suffixes.endswith(".csv.gz"):
            return int(sum(len(chunk) for chunk in pd.read_csv(path, chunksize=250000, usecols=[0])))
    except Exception:
        return ""
    return ""


def input_artifact_audit(paths: dict[str, Path], required: set[str], schema: dict[str, list[str]]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for artifact_id, path in sorted(paths.items()):
        exists = path.exists()
        schema_status = "not_checked"
        failure_reason = ""
        row_count: int | str = ""
        if exists:
            row_count = quick_row_count(path)
        if artifact_id in schema and exists and path.is_file():
            try:
                if "".join(path.suffixes).endswith(".parquet"):
                    import pyarrow.parquet as pq

                    cols = pq.ParquetFile(path).schema.names
                    missing = sorted(set(schema[artifact_id]) - set(cols))
                else:
                    cols = pd.read_csv(path, nrows=0).columns.tolist()
                    missing = sorted(set(schema[artifact_id]) - set(cols))
                schema_status = "ok" if not missing else "missing_columns"
                failure_reason = ",".join(missing)
            except Exception as exc:  # pragma: no cover - defensive for corrupt inputs
                schema_status = "schema_read_failed"
                failure_reason = str(exc)
        elif artifact_id in schema and not exists:
            schema_status = "missing_file"
            failure_reason = "required_input_missing" if artifact_id in required else "optional_input_missing"
        rows.append(
            {
                "artifact_id": artifact_id,
                "relative_path": str(path.relative_to(REPO_ROOT)) if path.exists() and path.is_relative_to(REPO_ROOT) else str(path),
                "resolved_path": str(path),
                "required_flag": artifact_id in required,
                "exists_flag": exists,
                "content_hash": path_hash(path),
                "file_size_bytes": path.stat().st_size if path.exists() and path.is_file() else "",
                "mtime_utc": file_mtime_utc(path),
                "schema_status": schema_status,
                "row_count": row_count,
                "failure_reason": failure_reason,
            }
        )
    return pd.DataFrame(rows)


def build_daily_regime_series(panel: pd.DataFrame, daily_conflict_rate_cap: float = 0.01) -> pd.DataFrame:
    required = ["date", "market_regime_bucket"]
    status, missing = required_columns_status(panel, required)
    if status != "ok":
        raise ValueError(f"cross_section_feature_panel_missing_columns:{missing}")
    work = panel[required].copy()
    work["date"] = pd.to_datetime(work["date"]).dt.strftime("%Y-%m-%d")
    grouped_rows = []
    for date, group in work.groupby("date", sort=True):
        bucket = stable_mode(group["market_regime_bucket"])
        normalized = group["market_regime_bucket"].map(normalize_bucket)
        rows_total = int(len(group))
        conflict_n = int(normalized.ne(bucket).sum()) if bucket else rows_total
        grouped_rows.append(
            {
                "date": date,
                "date_pos": len(grouped_rows),
                "regime_t0": bucket,
                "daily_regime_bucket": bucket,
                "daily_regime_rows_total": rows_total,
                "daily_regime_conflict_n": conflict_n,
                "daily_regime_conflict_rate": safe_rate(conflict_n, rows_total),
                "daily_regime_conflict_flag": safe_rate(conflict_n, rows_total) > daily_conflict_rate_cap,
            }
        )
    daily = pd.DataFrame(grouped_rows)
    regimes = daily["regime_t0"].tolist()
    n = len(regimes)
    for offset in [5, 20]:
        plus: list[str] = []
        minus: list[str] = []
        eligible_plus: list[bool] = []
        for idx in range(n):
            plus_idx = idx + offset
            minus_idx = idx - offset
            eligible_plus.append(plus_idx < n)
            plus.append(regimes[plus_idx] if plus_idx < n else "")
            minus.append(regimes[minus_idx] if minus_idx >= 0 else "")
        daily[f"regime_t_plus_{offset}"] = plus
        daily[f"regime_t_minus_{offset}"] = minus
        daily[f"date_forward_{offset}d_eligible_flag"] = eligible_plus
        daily[f"date_flip_end_{offset}d_flag"] = [
            bool(eligible_plus[idx] and plus[idx] != regimes[idx]) for idx in range(n)
        ]
        any_flip: list[bool] = []
        pre_any_flip: list[bool] = []
        for idx in range(n):
            forward_window = regimes[idx + 1 : min(n, idx + offset + 1)]
            backward_window = regimes[max(0, idx - offset) : idx]
            any_flip.append(any(value != regimes[idx] for value in forward_window))
            pre_any_flip.append(any(value != regimes[idx] for value in backward_window))
        daily[f"date_flip_any_{offset}d_flag"] = any_flip
        daily[f"date_pre_flip_any_{offset}d_flag"] = pre_any_flip
    ages: list[int] = []
    confirmation_lags: list[int] = []
    stability_scores: list[float] = []
    for idx, regime in enumerate(regimes):
        age = 0
        cursor = idx
        while cursor >= 0 and regimes[cursor] == regime and age < 120:
            age += 1
            cursor -= 1
        ages.append(age)
        lag = -1
        for candidate in range(0, 21):
            end = idx + candidate + 3
            if end <= n and all(value == regime for value in regimes[idx + candidate : end]):
                lag = candidate
                break
        confirmation_lags.append(lag)
        forward = regimes[idx + 1 : min(n, idx + 21)]
        if not forward:
            stability_scores.append(float("nan"))
        else:
            mismatch_n = sum(value != regime for value in forward)
            stability_scores.append(1.0 - safe_rate(mismatch_n, len(forward)))
    daily["regime_age_sessions_t0"] = ages
    daily["confirmation_lag_sessions"] = confirmation_lags
    daily["confirmation_lag_not_found_20d_flag"] = daily["confirmation_lag_sessions"].eq(-1)
    daily["t0_regime_confidence_score"] = np.minimum(daily["regime_age_sessions_t0"], 20) / 20.0
    daily["ex_post_regime_stability_score_20d"] = stability_scores
    daily["date_forward_stability_horizon_incomplete"] = ~daily["date_forward_20d_eligible_flag"]
    return daily


def build_calendar_reconciliation(
    daily: pd.DataFrame,
    pit_universe: pd.DataFrame,
    qfq_dates: set[str],
    thresholds: Thresholds,
) -> pd.DataFrame:
    primary_dates = set(daily["date"].astype(str))
    min_date = min(primary_dates) if primary_dates else ""
    max_date = max(primary_dates) if primary_dates else ""
    external_dates: set[str] = set()
    if "usable_trade_date" in pit_universe.columns:
        pit_dates = set(pd.to_datetime(pit_universe["usable_trade_date"]).dt.strftime("%Y-%m-%d"))
        external_dates |= {date for date in pit_dates if (not min_date or min_date <= date <= max_date)}
    external_dates |= {date for date in qfq_dates if (not min_date or min_date <= date <= max_date)}
    primary_only = primary_dates - external_dates
    external_only = external_dates - primary_dates
    mismatch_n = len(primary_only) + len(external_only)
    mismatch_rate = safe_rate(mismatch_n, max(len(primary_dates), 1))
    return pd.DataFrame(
        [
            {
                "calendar_source": "cross_section_feature_panel_primary_vs_pit_qfq",
                "primary_date_n": len(primary_dates),
                "external_date_n": len(external_dates),
                "primary_only_date_n": len(primary_only),
                "external_only_date_n": len(external_only),
                "mismatch_date_n": mismatch_n,
                "mismatch_rate": mismatch_rate,
                "mismatch_rate_cap": thresholds.calendar_mismatch_rate_cap,
                "calendar_reconciliation_status": (
                    "pass" if mismatch_rate <= thresholds.calendar_mismatch_rate_cap else "calendar_reconciliation_failed"
                ),
                "primary_only_examples": ";".join(sorted(primary_only)[:10]),
                "external_only_examples": ";".join(sorted(external_only)[:10]),
            }
        ]
    )


def collect_qfq_dates(primary_dir: Path, fallback_dir: Path, max_files: int = 0) -> set[str]:
    chosen_dir = primary_dir if primary_dir.is_dir() and any(primary_dir.glob("*.csv")) else fallback_dir
    if not chosen_dir.is_dir():
        return set()
    paths = sorted(chosen_dir.glob("*.csv"))
    if max_files and max_files > 0:
        paths = paths[:max_files]
    dates: set[str] = set()
    for path in paths:
        try:
            chunk = pd.read_csv(path, usecols=["date"])
        except Exception:
            continue
        dates.update(pd.to_datetime(chunk["date"]).dt.strftime("%Y-%m-%d").tolist())
    return dates


def dedupe_first(frame: pd.DataFrame, key: str, cols: list[str]) -> tuple[pd.DataFrame, int, int]:
    if frame.empty:
        return pd.DataFrame(columns=[key, *cols]), 0, 0
    available_cols = [col for col in cols if col in frame.columns]
    subset = frame[[key, *available_cols]].copy()
    duplicate_n = int(subset.duplicated([key]).sum())
    conflict_n = 0
    for col in available_cols:
        nunique = subset.groupby(key, dropna=False)[col].nunique(dropna=True)
        conflict_n += int(nunique.gt(1).sum())
    deduped = subset.sort_values([key]).drop_duplicates([key], keep="first")
    return deduped, duplicate_n, conflict_n


def build_event_scored(
    canonical: pd.DataFrame,
    bindings_09a: pd.DataFrame,
    daily: pd.DataFrame,
    thresholds: Thresholds,
) -> tuple[pd.DataFrame, pd.DataFrame, list[str]]:
    required = [
        "canonical_event_id",
        "event_id",
        "instrument",
        "event_t0_date",
        "event_split",
        "event_regime_bucket",
        "market_regime_bucket",
        "event_regime_gating",
        "trade_open_date",
        "event_t0_confirmation_time",
    ]
    status, missing = required_columns_status(canonical, required)
    if status != "ok":
        return pd.DataFrame(), pd.DataFrame(), [f"canonical_events_missing_columns:{missing}"]

    base_cols = required + [col for col in ["primary_family_id"] if col in canonical.columns]
    base = canonical[base_cols].copy()
    base["event_t0_date"] = pd.to_datetime(base["event_t0_date"]).dt.strftime("%Y-%m-%d")
    base["event_regime_norm"] = normalize_bucket_series(base["event_regime_bucket"])
    base["market_regime_norm"] = normalize_bucket_series(base["market_regime_bucket"])

    cols_09a = ["instrument", "event_t0_date", "event_split", "event_regime_bucket", "episode_regime_bucket", "source_pool_id"]
    bind_dedup, bind_dup_n, bind_conflict_n = dedupe_first(bindings_09a, "canonical_event_id", cols_09a)
    bind_dedup = bind_dedup.rename(
        columns={
            "instrument": "instrument_09a",
            "event_t0_date": "event_t0_date_09a",
            "event_split": "event_split_09a",
            "event_regime_bucket": "event_regime_bucket_09a",
            "episode_regime_bucket": "episode_regime_bucket_09a",
        }
    )
    joined = base.merge(bind_dedup, on="canonical_event_id", how="left", indicator="join_09a_indicator", validate="m:1")
    joined["event_regime_09a_norm"] = normalize_bucket_series(joined.get("event_regime_bucket_09a", pd.Series("", index=joined.index)))
    joined["analysis_event_regime_bucket"] = coalesce_valid_series(
        [joined["event_regime_norm"], joined["market_regime_norm"], joined["event_regime_09a_norm"]]
    )
    joined["analysis_event_regime_source"] = first_valid_source(
        joined,
        [
            ("08_canonical.event_regime_bucket", "event_regime_bucket"),
            ("08_canonical.market_regime_bucket", "market_regime_bucket"),
            ("09A.event_regime_bucket", "event_regime_bucket_09a"),
        ],
    )
    daily_small = daily[
        [
            "date",
            "daily_regime_bucket",
            "daily_regime_conflict_rate",
            "daily_regime_conflict_flag",
            "date_pos",
            "regime_t0",
            "regime_t_minus_5",
            "regime_t_minus_20",
            "regime_t_plus_5",
            "regime_t_plus_20",
            "date_forward_5d_eligible_flag",
            "date_forward_20d_eligible_flag",
            "date_flip_end_5d_flag",
            "date_flip_end_20d_flag",
            "date_flip_any_5d_flag",
            "date_flip_any_20d_flag",
            "date_pre_flip_any_5d_flag",
            "date_pre_flip_any_20d_flag",
            "regime_age_sessions_t0",
            "confirmation_lag_sessions",
            "confirmation_lag_not_found_20d_flag",
            "t0_regime_confidence_score",
            "ex_post_regime_stability_score_20d",
        ]
    ].copy()
    scored = joined.merge(daily_small, left_on="event_t0_date", right_on="date", how="left", validate="m:1")
    scored["event_t0_not_in_primary_calendar_flag"] = scored["date"].isna()
    scored["event_vs_daily_regime_match_flag"] = (
        scored["analysis_event_regime_bucket"].ne("")
        & scored["daily_regime_bucket"].fillna("").astype(str).eq(scored["analysis_event_regime_bucket"].astype(str))
    )
    scored["t0_regime_available_flag"] = (
        scored["analysis_event_regime_bucket"].ne("")
        & scored["daily_regime_bucket"].fillna("").astype(str).ne("")
        & ~scored["daily_regime_conflict_flag"].fillna(True).map(boolish)
    )
    scored["t0_pit_status"] = np.select(
        [
            scored["event_t0_not_in_primary_calendar_flag"],
            scored["analysis_event_regime_bucket"].eq(""),
            scored["daily_regime_conflict_flag"].fillna(True).map(boolish),
            ~scored["event_vs_daily_regime_match_flag"],
        ],
        [
            "event_t0_not_in_primary_calendar",
            "invalid_or_missing_regime",
            "daily_regime_conflict",
            "event_vs_daily_regime_mismatch",
        ],
        default="pit_available",
    )
    scored["confirmation_time_status"] = np.select(
        [
            scored["event_t0_confirmation_time"].map(nonempty).eq(""),
            ~scored["event_t0_confirmation_time"].map(nonempty).isin(ALLOWED_CONFIRMATION_TIMES),
        ],
        ["confirmation_time_missing", "confirmation_time_unrecognized"],
        default="confirmation_time_ok",
    )
    scored["event_market_regime_match_flag"] = (
        scored["event_regime_norm"].ne("") & scored["event_regime_norm"].eq(scored["market_regime_norm"])
    )
    split_rates = scored.groupby("event_split")["event_vs_daily_regime_match_flag"].mean().to_dict()
    regime_rates = scored.groupby("analysis_event_regime_bucket")["event_vs_daily_regime_match_flag"].mean().to_dict()
    scored["event_vs_daily_regime_match_rate_global"] = rate(scored["event_vs_daily_regime_match_flag"])
    scored["t0_regime_available_rate_global"] = rate(scored["t0_regime_available_flag"])
    scored["invalid_or_missing_regime_rate_global"] = rate(scored["analysis_event_regime_bucket"].eq(""))
    scored["event_vs_daily_regime_match_rate_by_split"] = scored["event_split"].map(split_rates)
    scored["event_vs_daily_regime_match_rate_by_analysis_event_regime_bucket"] = scored[
        "analysis_event_regime_bucket"
    ].map(regime_rates)

    coverage = pd.DataFrame(
        [
            {
                "join_name": "08_canonical_to_09a_selected_bindings",
                "left_row_count": len(base),
                "matched_row_count": int(scored["join_09a_indicator"].eq("both").sum()),
                "match_rate": rate(scored["join_09a_indicator"].eq("both")),
                "duplicate_key_count": bind_dup_n,
                "conflict_count": bind_conflict_n
                + int(
                    (
                    scored["join_09a_indicator"].eq("both")
                    & (
                        scored["instrument"].astype(str).ne(scored["instrument_09a"].astype(str))
                        | scored["event_t0_date"].astype(str).ne(scored["event_t0_date_09a"].astype(str))
                        | scored["event_split"].astype(str).ne(scored["event_split_09a"].astype(str))
                    )
                    ).sum()
                ),
                "join_status": "statistics_incomplete_if_authority_unavailable",
            }
        ]
    )
    failures: list[str] = []
    return scored, coverage, failures


def build_membership_capture_readouts(
    event_scored: pd.DataFrame,
    membership: pd.DataFrame,
    capture: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    membership_cols = [
        "instrument",
        "event_t0_date",
        "event_split",
        "event_split_canonical",
        "episode_market_regime_bucket",
        "market_regime_bucket_episode",
        "target_episode_id",
        "episode_split",
    ]
    mem_dedup, mem_dup_n, mem_conflict_n = dedupe_first(membership, "canonical_event_id", membership_cols)
    mem_dedup = mem_dedup.rename(
        columns={
            "instrument": "membership_instrument",
            "event_t0_date": "membership_event_t0_date",
            "event_split": "membership_event_split",
        }
    )
    cap_cols = ["instrument", "episode_split", "market_regime_bucket", "first_event_t0_date", "candidate_scope_id"]
    cap_dedup, cap_dup_n, cap_conflict_n = dedupe_first(capture, "target_episode_id", cap_cols)
    joined = event_scored[
        ["canonical_event_id", "instrument", "event_t0_date", "event_split", "analysis_event_regime_bucket"]
    ].merge(mem_dedup, on="canonical_event_id", how="left", indicator="membership_indicator", validate="m:1")
    joined = joined.merge(
        cap_dedup.rename(columns={"instrument": "capture_instrument", "episode_split": "capture_episode_split", "market_regime_bucket": "capture_market_regime_bucket"}),
        on="target_episode_id",
        how="left",
        indicator="capture_indicator",
        validate="m:1",
    )
    joined["episode_regime_bucket"] = coalesce_valid_series(
        [
            joined.get("episode_market_regime_bucket", pd.Series("", index=joined.index)),
            joined.get("capture_market_regime_bucket", pd.Series("", index=joined.index)),
        ]
    )
    joined["episode_event_regime_divergence_flag"] = (
        joined["episode_regime_bucket"].ne("")
        & joined["analysis_event_regime_bucket"].ne("")
        & joined["episode_regime_bucket"].ne(joined["analysis_event_regime_bucket"])
    )
    divergence = (
        joined.groupby(["event_split", "analysis_event_regime_bucket", "episode_regime_bucket"], dropna=False)
        .agg(
            event_n=("canonical_event_id", "size"),
            membership_match_n=("membership_indicator", lambda x: int((x == "both").sum())),
            capture_match_n=("capture_indicator", lambda x: int((x == "both").sum())),
            divergence_n=("episode_event_regime_divergence_flag", "sum"),
        )
        .reset_index()
    )
    divergence["divergence_rate"] = divergence.apply(lambda row: safe_rate(row["divergence_n"], row["event_n"]), axis=1)
    coverage = pd.DataFrame(
        [
            {
                "join_name": "08_canonical_to_08_membership",
                "left_row_count": len(event_scored),
                "matched_row_count": int(joined["membership_indicator"].eq("both").sum()),
                "match_rate": rate(joined["membership_indicator"].eq("both")),
                "duplicate_key_count": mem_dup_n,
                "conflict_count": mem_conflict_n,
                "join_status": "episode_readout_only",
            },
            {
                "join_name": "08_membership_to_08_capture",
                "left_row_count": int(joined["membership_indicator"].eq("both").sum()),
                "matched_row_count": int(joined["capture_indicator"].eq("both").sum()),
                "match_rate": safe_rate(
                    int(joined["capture_indicator"].eq("both").sum()), int(joined["membership_indicator"].eq("both").sum())
                ),
                "duplicate_key_count": cap_dup_n,
                "conflict_count": cap_conflict_n,
                "join_status": "episode_readout_only",
            },
        ]
    )
    return divergence, coverage


def build_event_regime_gating_readout(event_scored: pd.DataFrame, event_instances_path: Path | None) -> pd.DataFrame:
    work = event_scored.copy()
    work["gated_event_flag"] = work["event_regime_gating"].map(nonempty).str.lower().ne("ungated")
    rows: list[dict[str, Any]] = []
    total = len(work)
    gated = int(work["gated_event_flag"].sum())
    rows.append(
        {
            "view": "all",
            "split": "all",
            "analysis_event_regime_bucket": "all",
            "event_n": total,
            "gated_event_count": gated,
            "gated_event_share": safe_rate(gated, total),
            "event_instance_reconciliation_status": (
                "available" if event_instances_path and event_instances_path.is_file() else "event_instance_gating_reconciliation_skipped"
            ),
        }
    )
    for split, group in work.groupby("event_split", dropna=False):
        rows.append(
            {
                "view": "split",
                "split": split,
                "analysis_event_regime_bucket": "all",
                "event_n": len(group),
                "gated_event_count": int(group["gated_event_flag"].sum()),
                "gated_event_share": rate(group["gated_event_flag"]),
                "event_instance_reconciliation_status": rows[0]["event_instance_reconciliation_status"],
            }
        )
    for regime, group in work.groupby("analysis_event_regime_bucket", dropna=False):
        rows.append(
            {
                "view": "analysis_event_regime_bucket",
                "split": "all",
                "analysis_event_regime_bucket": regime,
                "event_n": len(group),
                "gated_event_count": int(group["gated_event_flag"].sum()),
                "gated_event_share": rate(group["gated_event_flag"]),
                "event_instance_reconciliation_status": rows[0]["event_instance_reconciliation_status"],
            }
        )
    return pd.DataFrame(rows)


def summarize_date_level_stability(daily: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for regime, group in daily.groupby("regime_t0", dropna=False):
        for scope, label in [(group, str(regime)), (daily, "all")]:
            if label == "all" and regime != daily["regime_t0"].drop_duplicates().iloc[0]:
                continue
            eligible_5 = scope.loc[scope["date_forward_5d_eligible_flag"]]
            eligible_20 = scope.loc[scope["date_forward_20d_eligible_flag"]]
            rows.append(
                {
                    "population_scope": "date_level_unweighted",
                    "view": "regime_t0" if label != "all" else "all",
                    "split": "all",
                    "regime_bucket": label,
                    "date_n": len(scope),
                    "event_n": "",
                    "forward_5d_eligible_rate": rate(scope["date_forward_5d_eligible_flag"]),
                    "forward_20d_eligible_rate": rate(scope["date_forward_20d_eligible_flag"]),
                    "flip_end_5d_rate": rate(eligible_5["date_flip_end_5d_flag"]),
                    "flip_any_5d_rate": rate(eligible_5["date_flip_any_5d_flag"]),
                    "flip_end_20d_rate": rate(eligible_20["date_flip_end_20d_flag"]),
                    "flip_any_20d_rate": rate(eligible_20["date_flip_any_20d_flag"]),
                    "confirmation_lag_not_found_20d_rate": rate(scope["confirmation_lag_not_found_20d_flag"]),
                    "median_regime_age_sessions_t0": float(scope["regime_age_sessions_t0"].median()) if len(scope) else float("nan"),
                }
            )
    return pd.DataFrame(rows).drop_duplicates(["population_scope", "view", "regime_bucket"])


def summarize_event_weighted_stability(scored: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    views = [
        ("all", ["__all__"]),
        ("split", ["event_split"]),
        ("analysis_event_regime_bucket", ["analysis_event_regime_bucket"]),
        ("split_analysis_event_regime_bucket", ["event_split", "analysis_event_regime_bucket"]),
    ]
    work = scored.copy()
    work["__all__"] = "all"
    for view, keys in views:
        for values, group in work.groupby(keys, dropna=False):
            if not isinstance(values, tuple):
                values = (values,)
            key_map = dict(zip(keys, values))
            eligible_5 = group.loc[group["date_forward_5d_eligible_flag"].fillna(False)]
            eligible_20 = group.loc[group["date_forward_20d_eligible_flag"].fillna(False)]
            rows.append(
                {
                    "population_scope": "08_canonical_event_weighted",
                    "view": view,
                    "split": key_map.get("event_split", "all"),
                    "regime_bucket": key_map.get("analysis_event_regime_bucket", "all"),
                    "date_n": int(group["event_t0_date"].nunique(dropna=True)),
                    "event_n": len(group),
                    "forward_5d_eligible_rate": rate(group["date_forward_5d_eligible_flag"]),
                    "forward_20d_eligible_rate": rate(group["date_forward_20d_eligible_flag"]),
                    "flip_end_5d_rate": rate(eligible_5["date_flip_end_5d_flag"]),
                    "flip_any_5d_rate": rate(eligible_5["date_flip_any_5d_flag"]),
                    "flip_end_20d_rate": rate(eligible_20["date_flip_end_20d_flag"]),
                    "flip_any_20d_rate": rate(eligible_20["date_flip_any_20d_flag"]),
                    "confirmation_lag_not_found_20d_rate": rate(group["confirmation_lag_not_found_20d_flag"]),
                    "median_regime_age_sessions_t0": float(group["regime_age_sessions_t0"].median()) if len(group) else float("nan"),
                }
            )
    return pd.DataFrame(rows)


def quantile_rows(frame: pd.DataFrame, value_col: str, population_scope: str, bucket_col: str = "regime_t0") -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    work = frame.copy()
    work["all"] = "all"
    for view, col in [("all", "all"), ("regime_bucket", bucket_col)]:
        for bucket, group in work.groupby(col, dropna=False):
            values = pd.to_numeric(group[value_col], errors="coerce").dropna()
            rows.append(
                {
                    "population_scope": population_scope,
                    "metric": value_col,
                    "view": view,
                    "regime_bucket": bucket,
                    "row_n": len(group),
                    "p05": values.quantile(0.05) if len(values) else float("nan"),
                    "p25": values.quantile(0.25) if len(values) else float("nan"),
                    "median": values.quantile(0.50) if len(values) else float("nan"),
                    "p75": values.quantile(0.75) if len(values) else float("nan"),
                    "p95": values.quantile(0.95) if len(values) else float("nan"),
                    "share_age_lt_3": rate(values.lt(3)) if value_col == "regime_age_sessions_t0" else "",
                    "share_age_lt_5": rate(values.lt(5)) if value_col == "regime_age_sessions_t0" else "",
                    "share_age_ge_20": rate(values.ge(20)) if value_col == "regime_age_sessions_t0" else "",
                }
            )
    return rows


def build_regime_age_confidence_distribution(daily: pd.DataFrame, scored: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for metric in ["regime_age_sessions_t0", "confirmation_lag_sessions", "t0_regime_confidence_score", "ex_post_regime_stability_score_20d"]:
        rows.extend(quantile_rows(daily, metric, "date_level_unweighted", "regime_t0"))
        event_frame = scored.copy()
        event_frame["regime_t0"] = event_frame["analysis_event_regime_bucket"]
        rows.extend(quantile_rows(event_frame, metric, "08_canonical_event_weighted", "regime_t0"))
    return pd.DataFrame(rows)


def filter_10a_scope(bindings_10a: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    scope = config.get("scope", {})
    work = bindings_10a.copy()
    mask = pd.Series(True, index=work.index)
    for col, config_key in [
        ("population_id", "ten_a_population_id"),
        ("rule_arm_id", "ten_a_rule_arm_id"),
        ("denominator_id", "ten_a_denominator_id"),
        ("admission_status", "ten_a_admission_status"),
    ]:
        value = scope.get(config_key)
        if value is not None and col in work.columns:
            mask &= work[col].astype(str).eq(str(value))
    if "readout_only_flag" in work.columns and "ten_a_readout_only_flag" in scope:
        mask &= work["readout_only_flag"].map(boolish).eq(bool(scope["ten_a_readout_only_flag"]))
    return work.loc[mask].copy()


def build_10a_coverage(
    bindings_10a: pd.DataFrame,
    event_scored: pd.DataFrame,
    config: dict[str, Any],
    thresholds: Thresholds,
) -> tuple[pd.DataFrame, pd.DataFrame, bool]:
    scoped = filter_10a_scope(bindings_10a, config)
    if scoped.empty:
        empty = pd.DataFrame(
            [
                {
                    "ten_a_row_count": 0,
                    "ten_a_key_parse_success_rate": 0.0,
                    "ten_a_to_08_match_rate": 0.0,
                    "ten_a_regime_field_agreement_rate_readout_only": 0.0,
                    "authority_regime_coverage_rate_for_11A1": 0.0,
                    "coverage_status": "10A_scope_empty",
                    "ten_a_key_parse_conflict_n": 0,
                    "ten_a_key_parse_failed_n": 0,
                }
            ]
        )
        return empty, pd.DataFrame(), False
    work = scoped.copy()
    work["canonical_from_input_event_key"] = work["input_event_key"].map(parse_canonical_from_pipe)
    work["canonical_from_feature_matrix_join_key"] = work["feature_matrix_join_key"].map(parse_canonical_from_pipe)
    work["ten_a_key_parse_conflict_flag"] = (
        work["canonical_from_input_event_key"].ne("")
        & work["canonical_from_feature_matrix_join_key"].ne("")
        & work["canonical_from_input_event_key"].ne(work["canonical_from_feature_matrix_join_key"])
    )
    work["binding_canonical_event_id_for_audit"] = np.where(
        work["canonical_from_input_event_key"].ne(""),
        work["canonical_from_input_event_key"],
        work["canonical_from_feature_matrix_join_key"],
    )
    work["ten_a_key_parse_failed_flag"] = work["binding_canonical_event_id_for_audit"].eq("")
    right = event_scored[
        [
            "canonical_event_id",
            "instrument",
            "event_t0_date",
            "event_split",
            "analysis_event_regime_bucket",
        ]
    ].drop_duplicates(["canonical_event_id", "instrument", "event_t0_date", "event_split"])
    joined = work.merge(
        right,
        left_on=["binding_canonical_event_id_for_audit", "instrument", "event_t0_date", "split"],
        right_on=["canonical_event_id", "instrument", "event_t0_date", "event_split"],
        how="left",
        indicator=True,
        validate="m:1",
    )
    joined["authority_regime_covered_flag"] = joined["_merge"].eq("both") & joined["analysis_event_regime_bucket"].map(normalize_bucket).ne("")
    joined["ten_a_regime_agreement_flag"] = (
        joined["authority_regime_covered_flag"]
        & normalize_bucket_series(joined["event_regime_bucket"]).eq(joined["analysis_event_regime_bucket"].astype("string"))
    )
    key_parse_success_rate = rate(~joined["ten_a_key_parse_failed_flag"])
    match_rate = rate(joined["_merge"].eq("both"))
    agreement_rate = rate(joined.loc[joined["_merge"].eq("both"), "ten_a_regime_agreement_flag"])
    coverage_rate = rate(joined["authority_regime_covered_flag"])
    parse_failed_n = int(joined["ten_a_key_parse_failed_flag"].sum())
    parse_conflict_n = int(joined["ten_a_key_parse_conflict_flag"].sum())
    coverage = pd.DataFrame(
        [
            {
                "ten_a_row_count": len(joined),
                "ten_a_key_parse_success_rate": key_parse_success_rate,
                "ten_a_to_08_match_rate": match_rate,
                "ten_a_regime_field_agreement_rate_readout_only": agreement_rate,
                "authority_regime_coverage_rate_for_11A1": coverage_rate,
                "coverage_status": (
                    "pass"
                    if parse_failed_n == 0 and coverage_rate >= thresholds.ten_a_authority_regime_coverage_floor
                    else "statistics_incomplete"
                ),
                "ten_a_key_parse_conflict_n": parse_conflict_n,
                "ten_a_key_parse_failed_n": parse_failed_n,
            }
        ]
    )
    power_rows: list[dict[str, Any]] = []
    required_regimes = set(config.get("scope", {}).get("downstream_required_regimes", ["risk_on"]))
    global_flag = True
    for regime in sorted(VALID_BUCKETS):
        group = joined.loc[joined["analysis_event_regime_bucket"].fillna("").eq(regime)]
        split_counts = {split: int(group["split"].astype(str).eq(split).sum()) for split in SPLITS}
        row_flag = (
            len(group) >= thresholds.ten_a_event_n_min
            and all(split_counts[split] >= thresholds.ten_a_split_event_n_min for split in SPLITS)
            and rate(group["authority_regime_covered_flag"]) >= thresholds.ten_a_authority_regime_coverage_floor
        )
        if regime in required_regimes:
            global_flag = global_flag and row_flag
        power_rows.append(
            {
                "population_scope": "10A_post_dedup_downstream",
                "analysis_event_regime_bucket": regime,
                "ten_a_event_n": len(group),
                "ten_a_train_event_n": split_counts["train"],
                "ten_a_validation_event_n": split_counts["validation"],
                "ten_a_robustness_event_n": split_counts["robustness"],
                "ten_a_authority_regime_coverage_rate": rate(group["authority_regime_covered_flag"]),
                "ten_a_slice_power_flag": row_flag,
            }
        )
    return coverage, pd.DataFrame(power_rows), bool(global_flag)


def build_split_regime_sample_power(
    daily_stability: pd.DataFrame,
    event_stability: pd.DataFrame,
    ten_a_power: pd.DataFrame,
) -> pd.DataFrame:
    date_rows = daily_stability.loc[daily_stability["population_scope"].eq("date_level_unweighted")].copy()
    date_rows = date_rows.rename(columns={"regime_bucket": "analysis_event_regime_bucket"})
    date_rows["ten_a_event_n"] = ""
    event_rows = event_stability.loc[event_stability["population_scope"].eq("08_canonical_event_weighted")].copy()
    event_rows = event_rows.rename(columns={"regime_bucket": "analysis_event_regime_bucket"})
    for frame in [date_rows, event_rows]:
        for col in [
            "ten_a_event_n",
            "ten_a_train_event_n",
            "ten_a_validation_event_n",
            "ten_a_robustness_event_n",
            "ten_a_authority_regime_coverage_rate",
            "ten_a_slice_power_flag",
        ]:
            if col not in frame.columns:
                frame[col] = ""
    ten = ten_a_power.copy()
    for col in [
        "view",
        "split",
        "date_n",
        "event_n",
        "forward_5d_eligible_rate",
        "forward_20d_eligible_rate",
        "flip_end_5d_rate",
        "flip_any_5d_rate",
        "flip_end_20d_rate",
        "flip_any_20d_rate",
        "confirmation_lag_not_found_20d_rate",
        "median_regime_age_sessions_t0",
    ]:
        if col not in ten.columns:
            ten[col] = ""
    cols = [
        "population_scope",
        "view",
        "split",
        "analysis_event_regime_bucket",
        "date_n",
        "event_n",
        "forward_5d_eligible_rate",
        "forward_20d_eligible_rate",
        "flip_end_5d_rate",
        "flip_any_5d_rate",
        "flip_end_20d_rate",
        "flip_any_20d_rate",
        "confirmation_lag_not_found_20d_rate",
        "median_regime_age_sessions_t0",
        "ten_a_event_n",
        "ten_a_train_event_n",
        "ten_a_validation_event_n",
        "ten_a_robustness_event_n",
        "ten_a_authority_regime_coverage_rate",
        "ten_a_slice_power_flag",
    ]
    return pd.concat([date_rows[cols], event_rows[cols], ten[cols]], ignore_index=True)


def build_source_contract() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "source_layer": "event",
                "authority_priority": 1,
                "artifact": "08 candidate_family_canonical_events.csv.gz",
                "field": "event_regime_bucket",
                "usage": "event_regime_authority",
            },
            {
                "source_layer": "event",
                "authority_priority": 2,
                "artifact": "08 candidate_family_canonical_events.csv.gz",
                "field": "market_regime_bucket",
                "usage": "event_regime_authority_fallback",
            },
            {
                "source_layer": "event",
                "authority_priority": 3,
                "artifact": "09A selected_label_event_bindings.parquet",
                "field": "event_regime_bucket",
                "usage": "event_regime_authority_fallback",
            },
            {
                "source_layer": "event",
                "authority_priority": 0,
                "artifact": "10A post_dedup_event_bindings.parquet",
                "field": "event_regime_bucket",
                "usage": "downstream_coverage_readout_only_not_authority",
            },
            {
                "source_layer": "episode",
                "authority_priority": 1,
                "artifact": "09A selected_label_event_bindings.parquet",
                "field": "episode_regime_bucket",
                "usage": "episode_readout_only",
            },
            {
                "source_layer": "episode",
                "authority_priority": 2,
                "artifact": "08 post_replay_event_episode_membership.parquet",
                "field": "episode_market_regime_bucket",
                "usage": "episode_readout_only",
            },
            {
                "source_layer": "episode",
                "authority_priority": 3,
                "artifact": "08 candidate_family_capture.parquet",
                "field": "market_regime_bucket",
                "usage": "episode_readout_only",
            },
        ]
    )


def build_source_reconciliation(event_scored: pd.DataFrame, pit_audit: pd.DataFrame) -> pd.DataFrame:
    rows = [
        {
            "metric": "event_market_regime_agreement_rate",
            "value": rate(event_scored["event_market_regime_match_flag"]),
            "numerator": int(event_scored["event_market_regime_match_flag"].sum()),
            "denominator": len(event_scored),
            "status": "readout",
        },
        {
            "metric": "event_vs_daily_regime_match_rate",
            "value": rate(event_scored["event_vs_daily_regime_match_flag"]),
            "numerator": int(event_scored["event_vs_daily_regime_match_flag"].sum()),
            "denominator": len(event_scored),
            "status": "pit_gate",
        },
        {
            "metric": "t0_regime_available_rate",
            "value": rate(event_scored["t0_regime_available_flag"]),
            "numerator": int(event_scored["t0_regime_available_flag"].sum()),
            "denominator": len(event_scored),
            "status": "pit_gate",
        },
        {
            "metric": "invalid_or_missing_regime_rate",
            "value": rate(event_scored["analysis_event_regime_bucket"].eq("")),
            "numerator": int(event_scored["analysis_event_regime_bucket"].eq("").sum()),
            "denominator": len(event_scored),
            "status": "pit_gate",
        },
    ]
    for source, group in event_scored.groupby("analysis_event_regime_source", dropna=False):
        rows.append(
            {
                "metric": f"analysis_event_regime_source:{source}",
                "value": safe_rate(len(group), len(event_scored)),
                "numerator": len(group),
                "denominator": len(event_scored),
                "status": "source_readout",
            }
        )
    if not pit_audit.empty:
        for _, row in pit_audit.iterrows():
            rows.append(
                {
                    "metric": f"09A_source_pit_audit:{row.get('split', '')}",
                    "value": row.get("published_reconstructed_consistency", ""),
                    "numerator": "",
                    "denominator": "",
                    "status": "source_pit_audit",
                }
            )
    return pd.DataFrame(rows)


def validate_pit_audit(pit_audit: pd.DataFrame) -> list[str]:
    required = [
        "split",
        "t0_visible_flag",
        "future_join_count",
        "published_reconstructed_consistency",
        "risk_on_reconstructed_not_published_share",
        "published_risk_on_not_reconstructed_share",
        "feature_panel_market_wide_regime_check",
    ]
    status, missing = required_columns_status(pit_audit, required)
    if status != "ok":
        return [f"09a_regime_pit_audit_missing_columns:{missing}"]
    failures: list[str] = []
    for _, row in pit_audit.iterrows():
        split = row["split"]
        if not boolish(row["t0_visible_flag"]):
            failures.append(f"pit_audit_t0_not_visible:{split}")
        if float(row["future_join_count"]) > 0:
            failures.append(f"pit_audit_future_join_count:{split}")
        if float(row["published_reconstructed_consistency"]) < 0.995:
            failures.append(f"pit_audit_reconstruction_consistency:{split}")
        if float(row["risk_on_reconstructed_not_published_share"]) > 0.005:
            failures.append(f"pit_audit_risk_on_reconstructed_not_published:{split}")
        if float(row["published_risk_on_not_reconstructed_share"]) > 0.005:
            failures.append(f"pit_audit_published_risk_on_not_reconstructed:{split}")
        if str(row["feature_panel_market_wide_regime_check"]).strip() != "pass":
            failures.append(f"pit_audit_feature_panel_market_wide_check:{split}")
    return failures


def date_level_gate_status(daily_stability: pd.DataFrame, thresholds: Thresholds) -> tuple[bool, list[str], list[str]]:
    power_failures: list[str] = []
    stability_failures: list[str] = []
    date_level = daily_stability.loc[
        daily_stability["population_scope"].eq("date_level_unweighted")
        & daily_stability["view"].eq("regime_t0")
        & daily_stability["regime_bucket"].isin(["risk_on", "risk_off"])
    ]
    seen = set(date_level["regime_bucket"])
    for missing in {"risk_on", "risk_off"} - seen:
        power_failures.append(f"date_level_missing_regime:{missing}")
    for _, row in date_level.iterrows():
        regime = row["regime_bucket"]
        if int(row["date_n"]) < thresholds.date_level_min_n:
            power_failures.append(f"date_level_calendar_underpowered:{regime}")
        if float(row["forward_20d_eligible_rate"]) < thresholds.date_forward_20d_eligible_floor:
            power_failures.append(f"date_level_forward_20d_ineligible:{regime}")
        if float(row["flip_end_5d_rate"]) > thresholds.date_flip_end_5d_cap:
            stability_failures.append(f"date_flip_end_5d_rate_high:{regime}")
        if float(row["flip_end_20d_rate"]) > thresholds.date_flip_end_20d_cap:
            stability_failures.append(f"date_flip_end_20d_rate_high:{regime}")
        if float(row["confirmation_lag_not_found_20d_rate"]) > thresholds.date_confirmation_lag_not_found_20d_cap:
            stability_failures.append(f"date_confirmation_lag_not_found_20d_rate_high:{regime}")
        if float(row["median_regime_age_sessions_t0"]) < thresholds.date_median_regime_age_min:
            stability_failures.append(f"date_median_regime_age_low:{regime}")
    return not power_failures and not stability_failures, power_failures, stability_failures


def choose_final_status(
    input_failures: list[str],
    statistics_failures: list[str],
    power_failures: list[str],
    stability_failures: list[str],
) -> str:
    if input_failures:
        return FINAL_BLOCKED
    if statistics_failures or power_failures:
        return FINAL_INCOMPLETE
    if stability_failures:
        return FINAL_UNSTABLE
    return FINAL_STABLE


def build_downstream_usage_decision(final_status: str, ten_a_slice_power_flag: bool) -> pd.DataFrame:
    rows = []
    for target in USAGE_TARGETS:
        allowed = False
        scope = "blocked"
        reason = final_status
        if final_status == FINAL_STABLE:
            if target == "11A1_proxy_readout":
                allowed = True
                scope = "primary"
                reason = "regime_pit_available_and_date_level_stable"
            elif target == "11A1_matched_base_axis":
                allowed = bool(ten_a_slice_power_flag)
                scope = "diagnostic_only" if not ten_a_slice_power_flag else "primary"
                reason = (
                    "10A_downstream_slice_power_failed_requires_11A1_recheck"
                    if not ten_a_slice_power_flag
                    else "11A0_allows_axis_but_11A1_must_recheck_slice_power"
                )
            else:
                allowed = True
                scope = "diagnostic_only"
                reason = "regime_context_allowed_for_downstream_readout"
        elif final_status == FINAL_UNSTABLE:
            if target in {"11A1_proxy_readout", "11B_retention_readout", "11C_policy_context"}:
                allowed = True
                scope = "readout_only"
                reason = "pit_available_but_date_level_stability_gate_failed"
            else:
                allowed = False
                scope = "blocked"
                reason = "unstable_regime_not_allowed_as_hard_matched_base_axis"
        rows.append(
            {
                "usage_target": target,
                "allowed_flag": allowed,
                "allowed_regime_buckets": "risk_on;risk_off;transition" if allowed else "",
                "usage_scope": scope,
                "stability_gate_basis": "date_level_unweighted",
                "ten_a_slice_power_flag": ten_a_slice_power_flag,
                "11A1_must_recheck_slice_power_flag": True,
                "reason": reason,
            }
        )
    return pd.DataFrame(rows)


def build_acceptance_summary(
    final_status: str,
    input_failures: list[str],
    statistics_failures: list[str],
    power_failures: list[str],
    stability_failures: list[str],
    ten_a_slice_power_flag: bool,
) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "final_status": final_status,
                "input_blocked_reason_n": len(input_failures),
                "statistics_incomplete_reason_n": len(statistics_failures),
                "calendar_power_failure_n": len(power_failures),
                "date_level_stability_failure_n": len(stability_failures),
                "ten_a_slice_power_flag": ten_a_slice_power_flag,
                "input_blocked_reasons": ";".join(input_failures),
                "statistics_incomplete_reasons": ";".join(statistics_failures),
                "calendar_power_failures": ";".join(power_failures),
                "date_level_stability_failures": ";".join(stability_failures),
            }
        ]
    )


def build_report(
    final_status: str,
    input_audit: pd.DataFrame,
    source_recon: pd.DataFrame,
    daily_audit: pd.DataFrame,
    real_time_stability: pd.DataFrame,
    ten_a_coverage: pd.DataFrame,
    usage: pd.DataFrame,
    acceptance: pd.DataFrame,
) -> str:
    def metric_value(metric: str) -> Any:
        if "metric" not in source_recon.columns:
            return ""
        match = source_recon.loc[source_recon["metric"].eq(metric)]
        return "" if match.empty else match["value"].iloc[0]

    date_gate = real_time_stability.loc[
        real_time_stability["population_scope"].eq("date_level_unweighted")
        & real_time_stability["view"].eq("regime_t0")
        & real_time_stability["regime_bucket"].isin(["risk_on", "risk_off"])
    ]
    lines = [
        "# 11A0 Regime PIT Availability Audit Report",
        "",
        f"- final_status: `{final_status}`",
        f"- input artifacts audited: {len(input_audit)}",
        f"- event_vs_daily_regime_match_rate: {metric_value('event_vs_daily_regime_match_rate')}",
        f"- t0_regime_available_rate: {metric_value('t0_regime_available_rate')}",
        f"- invalid_or_missing_regime_rate: {metric_value('invalid_or_missing_regime_rate')}",
        "",
        "## Calendar Reconciliation",
        "",
        daily_audit.to_markdown(index=False),
        "",
        "## Date-Level Stability Gate Basis",
        "",
        "The hard stability gate is date-level unweighted. Event-weighted rates are diagnostic only.",
        "",
        date_gate.to_markdown(index=False),
        "",
        "## 10A Downstream Coverage",
        "",
        ten_a_coverage.to_markdown(index=False),
        "",
        "## Downstream Usage Decision",
        "",
        usage.to_markdown(index=False),
        "",
        "## Acceptance Summary",
        "",
        acceptance.to_markdown(index=False),
        "",
        "## Boundary",
        "",
        "11A0 does not prove alpha, does not define a buy signal, and does not authorize proxy or rejector overrides.",
    ]
    return "\n".join(lines) + "\n"


def build_manifest(
    config_path: Path,
    config: dict[str, Any],
    final_status: str,
    input_paths: dict[str, Path],
    output_paths: dict[str, Path],
) -> dict[str, Any]:
    return {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "experiment_id": config.get("run", {}).get("experiment_id", "11_archetype_proxy_validation_system_v0"),
        "primary_run_id": config.get("run", {}).get("primary_run_id", RUN_ID),
        "parent_experiment_id": config.get("run", {}).get("parent_experiment_id", ""),
        "final_status": final_status,
        "command": sys.argv,
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "git_revision": git_revision(),
        "config_path": str(config_path),
        "config_hash": stable_hash(config),
        "config_file_hash": path_hash(config_path),
        "input_artifacts": {key: {"path": str(path), "sha256": path_hash(path)} for key, path in sorted(input_paths.items())},
        "outputs": {key: str(path) for key, path in sorted(output_paths.items())},
        "output_hashes": {key: path_hash(path) for key, path in sorted(output_paths.items()) if path.is_file()},
    }


def get_output_paths() -> dict[str, Path]:
    return {
        "input_artifact_audit": TABLE_DIR / "input_artifact_audit.csv",
        "regime_source_contract": TABLE_DIR / "regime_source_contract.csv",
        "regime_daily_series_audit": TABLE_DIR / "regime_daily_series_audit.csv",
        "event_regime_join_coverage": TABLE_DIR / "event_regime_join_coverage.csv",
        "regime_source_reconciliation": TABLE_DIR / "regime_source_reconciliation.csv",
        "event_regime_gating_readout": TABLE_DIR / "event_regime_gating_readout.csv",
        "episode_event_regime_divergence": TABLE_DIR / "episode_event_regime_divergence.csv",
        "downstream_10a_regime_coverage_audit": TABLE_DIR / "downstream_10a_regime_coverage_audit.csv",
        "t0_causality_audit": TABLE_DIR / "t0_causality_audit.csv",
        "real_time_flip_stability": TABLE_DIR / "real_time_flip_stability.csv",
        "regime_age_confidence_distribution": TABLE_DIR / "regime_age_confidence_distribution.csv",
        "split_regime_sample_power": TABLE_DIR / "split_regime_sample_power.csv",
        "downstream_11a1_regime_usage_decision": TABLE_DIR / "downstream_11a1_regime_usage_decision.csv",
        "acceptance_summary": TABLE_DIR / "acceptance_summary.csv",
        "regime_scored_events": LOCAL_CACHE_DIR / "regime_scored_events.parquet",
        "daily_regime_series": LOCAL_CACHE_DIR / "daily_regime_series.parquet",
        "report": REPORT_PATH,
        "manifest": MANIFEST_PATH,
    }


def schema_requirements() -> dict[str, list[str]]:
    return {
        "upstream_09a_regime_pit_audit": [
            "split",
            "t0_visible_flag",
            "future_join_count",
            "published_reconstructed_consistency",
            "risk_on_reconstructed_not_published_share",
            "published_risk_on_not_reconstructed_share",
            "feature_panel_market_wide_regime_check",
        ],
        "upstream_09a_bindings": [
            "canonical_event_id",
            "instrument",
            "event_t0_date",
            "event_split",
            "event_regime_bucket",
            "episode_regime_bucket",
            "source_pool_id",
        ],
        "upstream_08_canonical_events": [
            "canonical_event_id",
            "event_id",
            "instrument",
            "event_t0_date",
            "event_split",
            "event_regime_bucket",
            "market_regime_bucket",
            "event_regime_gating",
            "trade_open_date",
            "event_t0_confirmation_time",
        ],
        "upstream_08_cross_section_feature_panel": ["date", "instrument", "market_regime_bucket"],
        "upstream_08_candidate_family_capture": ["target_episode_id", "episode_split", "market_regime_bucket"],
        "upstream_08_event_episode_membership": [
            "canonical_event_id",
            "instrument",
            "event_t0_date",
            "event_split",
            "episode_market_regime_bucket",
            "target_episode_id",
            "episode_split",
        ],
        "upstream_10a_event_bindings": [
            "input_event_key",
            "feature_matrix_join_key",
            "instrument",
            "event_t0_date",
            "split",
            "source_family_id",
            "event_regime_bucket",
        ],
        "pit_executable_universe": ["usable_trade_date", "instrument"],
    }


def run(config_path: Path = CONFIG_PATH) -> dict[str, Any]:
    config = load_yaml(config_path)
    thresholds = Thresholds.from_config(config)
    paths = {key: resolve_path(value) for key, value in config.get("paths", {}).items()}
    output_paths = get_output_paths()

    required_inputs = {
        "requirement_11a0",
        "requirement_11a1",
        "next_step_discussion",
        "upstream_09a_manifest",
        "upstream_09a_regime_pit_audit",
        "upstream_09a_regime_pit_report",
        "upstream_09a_selected_label_contract",
        "upstream_09a_bindings",
        "upstream_08_run_manifest",
        "upstream_08_canonical_events",
        "upstream_08_cross_section_feature_panel",
        "upstream_08_candidate_family_capture",
        "upstream_08_event_episode_membership",
        "upstream_10a_manifest",
        "upstream_10a_event_bindings",
        "pit_executable_universe",
        "qfq_primary_dir",
        "qfq_fallback_dir",
    }
    input_audit = input_artifact_audit(paths, required_inputs, schema_requirements())
    input_failures = input_audit.loc[
        input_audit["required_flag"]
        & (~input_audit["exists_flag"] | input_audit["schema_status"].isin(["missing_columns", "schema_read_failed"]))
    ]["artifact_id"].map(lambda x: f"input_blocked:{x}").tolist()

    for path in output_paths.values():
        path.parent.mkdir(parents=True, exist_ok=True)
    write_df(output_paths["input_artifact_audit"], input_audit)
    write_df(output_paths["regime_source_contract"], build_source_contract())

    if input_failures:
        empty = pd.DataFrame()
        for key, path in output_paths.items():
            if key in {"input_artifact_audit", "regime_source_contract", "report", "manifest", "regime_scored_events", "daily_regime_series"}:
                continue
            write_df(path, empty)
        acceptance = build_acceptance_summary(FINAL_BLOCKED, input_failures, [], [], [], False)
        usage = build_downstream_usage_decision(FINAL_BLOCKED, False)
        write_df(output_paths["acceptance_summary"], acceptance)
        write_df(output_paths["downstream_11a1_regime_usage_decision"], usage)
        report = build_report(FINAL_BLOCKED, input_audit, pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), usage, acceptance)
        write_text(output_paths["report"], report)
        write_json(output_paths["manifest"], build_manifest(config_path, config, FINAL_BLOCKED, paths, output_paths))
        return {"final_status": FINAL_BLOCKED, "manifest_path": str(output_paths["manifest"])}

    pit_audit = pd.read_csv(paths["upstream_09a_regime_pit_audit"])
    bindings_09a = pd.read_parquet(paths["upstream_09a_bindings"])
    canonical = pd.read_csv(paths["upstream_08_canonical_events"], low_memory=False)
    panel = pd.read_parquet(paths["upstream_08_cross_section_feature_panel"])
    membership = pd.read_parquet(paths["upstream_08_event_episode_membership"])
    capture = pd.read_parquet(paths["upstream_08_candidate_family_capture"])
    bindings_10a = pd.read_parquet(paths["upstream_10a_event_bindings"])
    pit_universe = pd.read_csv(paths["pit_executable_universe"], low_memory=False)

    qfq_dates = collect_qfq_dates(
        paths["qfq_primary_dir"],
        paths["qfq_fallback_dir"],
        int(config.get("calendar_reconciliation", {}).get("qfq_max_files", 0)),
    )
    daily = build_daily_regime_series(panel, thresholds.daily_conflict_rate_cap)
    calendar_audit = build_calendar_reconciliation(daily, pit_universe, qfq_dates, thresholds)
    daily_audit = pd.concat(
        [
            daily[
                [
                    "date",
                    "date_pos",
                    "daily_regime_bucket",
                    "daily_regime_rows_total",
                    "daily_regime_conflict_n",
                    "daily_regime_conflict_rate",
                    "daily_regime_conflict_flag",
                ]
            ],
            pd.DataFrame(
                [
                    {
                        "date": "__calendar_reconciliation__",
                        "date_pos": -1,
                        "daily_regime_bucket": calendar_audit["calendar_reconciliation_status"].iloc[0],
                        "daily_regime_rows_total": calendar_audit["primary_date_n"].iloc[0],
                        "daily_regime_conflict_n": calendar_audit["mismatch_date_n"].iloc[0],
                        "daily_regime_conflict_rate": calendar_audit["mismatch_rate"].iloc[0],
                        "daily_regime_conflict_flag": calendar_audit["calendar_reconciliation_status"].iloc[0]
                        != "pass",
                    }
                ]
            ),
        ],
        ignore_index=True,
    )
    event_scored, join_coverage_09a, event_failures = build_event_scored(canonical, bindings_09a, daily, thresholds)
    divergence, join_coverage_episode = build_membership_capture_readouts(event_scored, membership, capture)
    join_coverage = pd.concat([join_coverage_09a, join_coverage_episode], ignore_index=True)
    gating = build_event_regime_gating_readout(event_scored, paths.get("upstream_08_event_instances_optional"))
    source_recon = build_source_reconciliation(event_scored, pit_audit)
    ten_a_coverage, ten_a_power, ten_a_slice_power_flag = build_10a_coverage(bindings_10a, event_scored, config, thresholds)
    date_stability = summarize_date_level_stability(daily)
    event_stability = summarize_event_weighted_stability(event_scored)
    real_time_stability = pd.concat([date_stability, event_stability], ignore_index=True)
    age_conf = build_regime_age_confidence_distribution(daily, event_scored)
    sample_power = build_split_regime_sample_power(date_stability, event_stability, ten_a_power)

    statistics_failures: list[str] = []
    statistics_failures.extend(event_failures)
    statistics_failures.extend(validate_pit_audit(pit_audit))
    event_market_rate = rate(event_scored["event_market_regime_match_flag"])
    event_daily_rate = rate(event_scored["event_vs_daily_regime_match_flag"])
    available_rate = rate(event_scored["t0_regime_available_flag"])
    invalid_rate = rate(event_scored["analysis_event_regime_bucket"].eq(""))
    if event_market_rate < thresholds.event_market_agreement_floor:
        statistics_failures.append("event_market_regime_agreement_below_floor")
    if event_daily_rate < thresholds.event_vs_daily_match_floor:
        statistics_failures.append("event_vs_daily_regime_match_rate_below_floor")
    if available_rate < thresholds.t0_regime_available_floor:
        statistics_failures.append("t0_regime_available_rate_below_floor")
    if invalid_rate > 0:
        statistics_failures.append("residual_invalid_or_missing_regime")
    if int(event_scored["event_t0_not_in_primary_calendar_flag"].sum()) > 0:
        statistics_failures.append("event_t0_not_in_primary_calendar")
    if calendar_audit["calendar_reconciliation_status"].iloc[0] != "pass":
        statistics_failures.append("calendar_reconciliation_failed")
    if event_scored["confirmation_time_status"].isin(["confirmation_time_missing", "confirmation_time_unrecognized"]).any():
        statistics_failures.append("confirmation_time_missing_or_unrecognized")
    if int(ten_a_coverage["ten_a_key_parse_failed_n"].iloc[0]) > 0:
        statistics_failures.append("10A_key_parse_failed")

    _, power_failures, stability_failures = date_level_gate_status(date_stability, thresholds)
    final_status = choose_final_status(input_failures, statistics_failures, power_failures, stability_failures)
    usage = build_downstream_usage_decision(final_status, ten_a_slice_power_flag)
    acceptance = build_acceptance_summary(
        final_status, input_failures, statistics_failures, power_failures, stability_failures, ten_a_slice_power_flag
    )

    t0_cols = [
        "event_id",
        "canonical_event_id",
        "instrument",
        "event_t0_date",
        "event_split",
        "event_regime_bucket",
        "market_regime_bucket",
        "daily_regime_bucket",
        "daily_regime_conflict_rate",
        "event_vs_daily_regime_match_flag",
        "t0_regime_available_flag",
        "t0_pit_status",
        "analysis_event_regime_bucket",
        "analysis_event_regime_source",
        "event_vs_daily_regime_match_rate_global",
        "t0_regime_available_rate_global",
        "invalid_or_missing_regime_rate_global",
        "event_vs_daily_regime_match_rate_by_split",
        "event_vs_daily_regime_match_rate_by_analysis_event_regime_bucket",
        "confirmation_time_status",
    ]
    write_df(output_paths["regime_daily_series_audit"], daily_audit)
    write_df(output_paths["event_regime_join_coverage"], join_coverage)
    write_df(output_paths["regime_source_reconciliation"], source_recon)
    write_df(output_paths["event_regime_gating_readout"], gating)
    write_df(output_paths["episode_event_regime_divergence"], divergence)
    write_df(output_paths["downstream_10a_regime_coverage_audit"], ten_a_coverage)
    write_df(output_paths["t0_causality_audit"], event_scored[t0_cols])
    write_df(output_paths["real_time_flip_stability"], real_time_stability)
    write_df(output_paths["regime_age_confidence_distribution"], age_conf)
    write_df(output_paths["split_regime_sample_power"], sample_power)
    write_df(output_paths["downstream_11a1_regime_usage_decision"], usage)
    write_df(output_paths["acceptance_summary"], acceptance)
    LOCAL_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    event_scored.to_parquet(output_paths["regime_scored_events"], index=False)
    daily.to_parquet(output_paths["daily_regime_series"], index=False)
    report = build_report(
        final_status,
        input_audit,
        source_recon,
        calendar_audit,
        real_time_stability,
        ten_a_coverage,
        usage,
        acceptance,
    )
    write_text(output_paths["report"], report)
    write_json(output_paths["manifest"], build_manifest(config_path, config, final_status, paths, output_paths))
    return {"final_status": final_status, "manifest_path": str(output_paths["manifest"])}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run 11A0 regime PIT availability audit.")
    parser.add_argument("--config", default=str(CONFIG_PATH), help="Path to config YAML.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    result = run(Path(args.config))
    print(f"final_status={result['final_status']}")
    print(f"manifest={result['manifest_path']}")


if __name__ == "__main__":
    main()
