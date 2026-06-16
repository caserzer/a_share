#!/usr/bin/env python
from __future__ import annotations

import argparse
import hashlib
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


CONFIG_PATH = EXPERIMENT_DIR / "configs" / "config_winner_archetype_profiling.yaml"
REQUIREMENT_PATH = EXPERIMENT_DIR / "requirement_big_winner_archetype_profiling.md"

OUTPUT_TABLE_DIR = EXPERIMENT_DIR / "outputs" / "publishable" / "tables" / "big_winner_archetype_profiling"
OUTPUT_REPORT = EXPERIMENT_DIR / "outputs" / "publishable" / "reports" / "big_winner_archetype_profiling_report.md"
OUTPUT_LOCAL_CACHE_DIR = EXPERIMENT_DIR / "outputs" / "local_cache" / "big_winner_archetype_profiling"
OUTPUT_MANIFEST = EXPERIMENT_DIR / "outputs" / "manifests" / "big_winner_archetype_profiling_manifest.json"

DECISION_COMPLETE = "big_winner_archetype_profiling_statistics_complete"
DECISION_INCOMPLETE = "big_winner_archetype_profiling_statistics_incomplete"
DECISION_INPUT_BLOCKED = "big_winner_archetype_profiling_input_blocked"

REGIME_MISSING = "regime_missing"
VALID_PATH_REGIME_STATES = {"risk_on", "risk_off", "transition"}
PATH_REGIME_SOURCE_EPISODE = "episode_regime_bucket"
PATH_REGIME_SOURCE_EVENT_FALLBACK = "event_regime_bucket_fallback"
PATH_REGIME_SOURCE_UNRESOLVED = "unresolved_missing"
PATH_OK = "ok"
PATH_MISSING = "input_blocked_missing_forward_path"
PATH_BASIS_MISMATCH = "winner_basis_mismatch"
PATH_METRIC_INCONSISTENCY = "input_blocked_metric_inconsistency"

SEED_FLAGS = [
    "seed_gap_or_event_driven_flag",
    "seed_shakeout_reversal_flag",
    "seed_volatile_chop_flag",
    "seed_early_momentum_flag",
    "seed_late_bloomer_flag",
]

PATH_METRICS = [
    "day_to_target",
    "day_to_confirm",
    "deepest_pre_target_ret_low",
    "day_to_deepest_pre_target_low",
    "max_drawdown_to_target",
    "deepest_ret_low_20",
    "day_to_deepest_low_20",
    "max_single_day_close_return_to_target",
    "max_gap_open_return_to_target",
    "limit_like_up_day_count_to_target",
    "mfe_20_recomputed",
    "mfe_60_recomputed",
    "mfe_120_recomputed",
    "mae_20_recomputed",
    "mae_60_recomputed",
    "mae_120_recomputed",
]

WINNER_PATH_METRIC_COLUMNS = [
    "instrument",
    "profiling_row_identity",
    "pit_universe_name",
    "pit_universe_member_flag",
    "pit_membership_date",
    "pit_usable_trade_date",
    "pit_available_time",
    "pit_membership_rule_version",
    "pit_board_bucket",
    "pit_status_source",
    "trade_open_date",
    "trade_open_price",
    "binding_canonical_event_id",
    "source_denominator_id",
    "injury_input_denominator_id",
    "input_event_key",
    "split",
    "event_regime_state",
    "episode_regime_state_raw",
    "path_regime_state",
    "path_regime_source",
    "injury_event_regime_state",
    "winner_120",
    "horizon_complete_120d",
    "E1_missed_winner_flag",
    "bridge_winner",
    "winner_path_status",
    "winner_mfe_threshold",
    "confirm_upper_barrier",
    "failure_lower_barrier",
    "failure_max_drawdown",
    "close_based_drawdown_policy",
    "hard_failure_first_blocks_winner",
    "day_to_target",
    "day_to_confirm",
    "pre_target_window_status",
    "deepest_pre_target_ret_low",
    "day_to_deepest_pre_target_low",
    "max_drawdown_to_target",
    "deepest_ret_low_20",
    "day_to_deepest_low_20",
    "pre_target_touch_failure_lower_flag",
    "pre_target_close_drawdown_failure_proxy_flag",
    "max_single_day_close_return_to_target",
    "max_gap_open_return_to_target",
    "limit_like_up_day_count_to_target",
    "board_limit_proxy_used",
    "board_bucket_used",
    "board_bucket_source",
    "limit_proxy_status",
    "st_status_source",
    "mfe_20_recomputed",
    "mfe_60_recomputed",
    "mfe_120_recomputed",
    "mae_20_recomputed",
    "mae_60_recomputed",
    "mae_120_recomputed",
    *SEED_FLAGS,
    "seed_flag_overlap_n",
    "winner_path_archetype_v0",
    "archetype_status",
    "tenc_full_keep9000_rejected_flag",
    "tenc_mfe_20d",
    "injury_scope_flag",
    "qfq_source_path",
    "qfq_source_kind",
]

INPUT_AUDIT_COLUMNS = [
    "artifact_id",
    "relative_path",
    "resolved_path",
    "required_flag",
    "exists_flag",
    "content_hash",
    "file_size_bytes",
    "mtime_utc",
    "schema_status",
    "row_count",
    "failure_reason",
]

PIT_UNIVERSE_AUDIT_COLUMNS = [
    "audit_section",
    "population_stage",
    "split",
    "path_regime_state",
    "path_regime_source",
    "row_count",
    "winner_n",
    "unique_instrument_n",
    "unique_trade_open_date_n",
    "pit_universe_row_n",
    "pit_universe_unique_key_n",
    "pit_universe_duplicate_key_n",
    "pit_universe_missing_key_n",
    "pit_universe_joined_n",
    "pit_universe_excluded_n",
    "pit_universe_excluded_rate",
    "exclusion_reason",
    "pit_universe_name",
    "pit_universe_date_key",
    "pit_membership_rule_version",
    "episode_regime_missing_event_fallback_n",
    "path_regime_unresolved_missing_n",
    "audit_status",
]


@dataclass(frozen=True)
class Thresholds:
    winner_mfe_threshold: float
    confirm_upper_barrier: float
    failure_lower_barrier: float
    failure_max_drawdown: float
    close_based_drawdown_policy: bool
    hard_failure_first_blocks_winner: bool
    continuation_60_min_mfe_pct: float
    confirm_20_horizon_days: int


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


def hash_or_empty(path: Path) -> str:
    return file_sha256(path) if path and path.is_file() else ""


def file_mtime_utc(path: Path) -> str:
    if not path.exists():
        return ""
    return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat()


def file_size(path: Path) -> int:
    if path.is_file():
        return int(path.stat().st_size)
    if path.is_dir():
        return sum(1 for _ in path.glob("*"))
    return 0


def resolve_path(path_value: str | Path) -> Path:
    path = Path(path_value)
    if path.is_absolute():
        return path
    text = str(path)
    if text.startswith("topics/"):
        return REPO_ROOT / path
    if text.startswith("../"):
        return (EXPERIMENT_DIR / path).resolve()
    return (EXPERIMENT_DIR / path).resolve()


def relative_to_repo(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def stable_str(value: Any) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except TypeError:
        pass
    return str(value)


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


def make_composite_key(frame: pd.DataFrame, cols: list[str]) -> pd.Series:
    return frame[cols].map(stable_str).agg("|".join, axis=1)


def normalize_regime_state(value: Any) -> str:
    text = stable_str(value).strip()
    return text if text in VALID_PATH_REGIME_STATES else ""


def normalize_path_regime(value: Any) -> str:
    text = normalize_regime_state(value)
    return text if text else REGIME_MISSING


def resolve_path_regime(episode_regime: Any, event_regime: Any) -> tuple[str, str]:
    episode = normalize_regime_state(episode_regime)
    if episode:
        return episode, PATH_REGIME_SOURCE_EPISODE
    event = normalize_regime_state(event_regime)
    if event:
        return event, PATH_REGIME_SOURCE_EVENT_FALLBACK
    return REGIME_MISSING, PATH_REGIME_SOURCE_UNRESOLVED


def date_string(value: Any) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return ""
    parsed = pd.to_datetime(value, errors="coerce")
    if pd.isna(parsed):
        return ""
    return parsed.strftime("%Y-%m-%d")


def nested_get(payload: dict[str, Any], dotted: str) -> Any:
    current: Any = payload
    for part in dotted.split("."):
        if not isinstance(current, dict) or part not in current:
            raise KeyError(dotted)
        current = current[part]
    return current


def read_thresholds(labels: dict[str, Any]) -> Thresholds:
    return Thresholds(
        winner_mfe_threshold=float(nested_get(labels, "labels.label_families.winner_120.right_tail_threshold_pct")),
        confirm_upper_barrier=float(nested_get(labels, "labels.label_families.confirm_20.upper_barrier_pct")),
        failure_lower_barrier=float(nested_get(labels, "labels.label_families.failure_10.lower_barrier_pct")),
        failure_max_drawdown=float(nested_get(labels, "labels.label_families.failure_10.max_drawdown_pct")),
        close_based_drawdown_policy=bool(nested_get(labels, "labels.barrier_observation.close_based_drawdown")),
        hard_failure_first_blocks_winner=bool(
            nested_get(labels, "labels.label_families.winner_120.hard_failure_first_blocks_winner")
        ),
        continuation_60_min_mfe_pct=float(
            nested_get(labels, "labels.label_families.continuation_60.min_mfe_pct")
        ),
        confirm_20_horizon_days=int(nested_get(labels, "labels.label_families.confirm_20.horizon_days")),
    )


def read_row_count(path: Path) -> int:
    if not path.exists():
        return 0
    if path.is_dir():
        return sum(1 for _ in path.glob("*.csv"))
    suffix = path.suffix.lower()
    try:
        if suffix == ".parquet":
            return int(pd.read_parquet(path).shape[0])
        if suffix == ".csv":
            return int(pd.read_csv(path).shape[0])
        if suffix == ".json":
            payload = json.loads(path.read_text(encoding="utf-8"))
            return len(payload) if isinstance(payload, list) else 1
    except Exception:
        return 0
    return 0


def directory_hash(paths: list[Path]) -> str:
    digest = hashlib.sha256()
    for path in sorted(paths, key=lambda p: str(p)):
        digest.update(relative_to_repo(path).encode("utf-8"))
        digest.update(hash_or_empty(path).encode("utf-8"))
    return digest.hexdigest()


def input_audit(paths: dict[str, Path], schema_status: dict[str, str] | None = None) -> pd.DataFrame:
    schema_status = schema_status or {}
    optional = {"sh_name_history_dir", "sz_name_history", "qfq_fallback_dir"}
    rows = []
    for artifact_id, path in paths.items():
        exists = path.exists()
        required = artifact_id not in optional
        status = schema_status.get(artifact_id, "pass" if exists else "missing_required")
        failure_reason = ""
        if not exists and not required:
            status = "optional_missing"
        elif not exists:
            status = "missing_required"
            failure_reason = "missing_required"
        rows.append(
            {
                "artifact_id": artifact_id,
                "relative_path": relative_to_repo(path),
                "resolved_path": str(path),
                "required_flag": bool(required),
                "exists_flag": bool(exists),
                "content_hash": hash_or_empty(path) if path.is_file() else "",
                "file_size_bytes": file_size(path),
                "mtime_utc": file_mtime_utc(path),
                "schema_status": status,
                "row_count": read_row_count(path),
                "failure_reason": failure_reason,
            }
        )
    return pd.DataFrame(rows, columns=INPUT_AUDIT_COLUMNS)


def missing_columns(frame: pd.DataFrame, required: set[str]) -> set[str]:
    return sorted(required - set(frame.columns))


def load_pit_universe(path: Path, config: dict[str, Any]) -> tuple[pd.DataFrame, dict[str, Any], list[str]]:
    required = {
        "instrument",
        "usable_trade_date",
        "membership_date",
        "available_time",
        "board_bucket",
        "is_listed",
        "is_st",
        "is_suspended",
        "membership_rule_version",
    }
    frame = pd.read_csv(path)
    failures = []
    missing = missing_columns(frame, required)
    audit = {
        "pit_universe_row_n": int(len(frame)),
        "pit_universe_unique_key_n": 0,
        "pit_universe_duplicate_key_n": 0,
        "pit_universe_missing_key_n": 0,
        "pit_universe_schema_missing_column_n": int(len(missing)),
    }
    if missing:
        failures.append(f"PIT_universe_schema_missing_columns:{','.join(missing)}")
        return pd.DataFrame(), audit, failures

    out = frame.copy()
    out["instrument"] = out["instrument"].map(stable_str)
    out["pit_usable_trade_date"] = out["usable_trade_date"].map(date_string)
    out["pit_membership_date"] = out["membership_date"].map(date_string)
    out["pit_available_time"] = out["available_time"].map(stable_str)
    out["pit_membership_rule_version"] = out["membership_rule_version"].map(stable_str)
    out["pit_board_bucket"] = out["board_bucket"].map(stable_str)
    out["pit_status_source"] = (
        out["status_source"].map(stable_str) if "status_source" in out.columns else "not_provided"
    )

    key_cols = ["instrument", "pit_usable_trade_date"]
    missing_key_n = int(out[key_cols].eq("").any(axis=1).sum())
    duplicate_key_n = int(out.duplicated(key_cols).sum())
    unique_key_n = int(out[key_cols].drop_duplicates().shape[0])
    audit.update(
        {
            "pit_universe_unique_key_n": unique_key_n,
            "pit_universe_duplicate_key_n": duplicate_key_n,
            "pit_universe_missing_key_n": missing_key_n,
        }
    )
    if missing_key_n:
        failures.append(f"PIT_universe_missing_join_key:{missing_key_n}")
    if duplicate_key_n:
        failures.append(f"PIT_universe_join_key_duplicate:{duplicate_key_n}")

    keep_cols = [
        "instrument",
        "pit_usable_trade_date",
        "pit_membership_date",
        "pit_available_time",
        "pit_membership_rule_version",
        "pit_board_bucket",
        "pit_status_source",
    ]
    out = out.loc[~out[key_cols].eq("").any(axis=1), keep_cols].drop_duplicates(key_cols, keep="first")
    audit["pit_universe_name"] = config["scope"]["pit_universe_name"]
    audit["pit_universe_date_key"] = config["scope"].get("pit_universe_date_key", "usable_trade_date")
    return out, audit, failures


def apply_pit_universe_filter(
    raw_base: pd.DataFrame,
    pit_universe: pd.DataFrame,
    config: dict[str, Any],
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any], list[str]]:
    failures = []
    audit: dict[str, Any] = {
        "raw_09a_winner_candidate_n": int(len(raw_base)),
        "pit_filtered_profiling_scope_winner_n": 0,
        "excluded_non_pit_winner_candidate_n": int(len(raw_base)),
        "excluded_non_pit_winner_candidate_rate": 1.0 if len(raw_base) else np.nan,
    }
    if raw_base.empty:
        failures.append("PIT_filter_raw_09A_winner_candidate_empty")
        return raw_base.copy(), raw_base.copy(), audit, failures
    if pit_universe.empty:
        failures.append("PIT_filter_universe_empty_or_invalid")
        return raw_base.iloc[0:0].copy(), raw_base.copy(), audit, failures

    merged = raw_base.merge(
        pit_universe,
        left_on=["instrument", "trade_open_date"],
        right_on=["instrument", "pit_usable_trade_date"],
        how="left",
        indicator=True,
    )
    merged["pit_universe_member_flag"] = merged["_merge"].eq("both")
    merged["pit_universe_name"] = config["scope"]["pit_universe_name"]

    pit_base = merged.loc[merged["pit_universe_member_flag"]].copy()
    excluded = merged.loc[~merged["pit_universe_member_flag"]].copy()
    for frame in (pit_base, excluded):
        if "_merge" in frame.columns:
            frame.drop(columns=["_merge"], inplace=True)
    for col in [
        "pit_membership_date",
        "pit_usable_trade_date",
        "pit_available_time",
        "pit_membership_rule_version",
        "pit_board_bucket",
        "pit_status_source",
    ]:
        if col not in pit_base:
            pit_base[col] = pd.NA
        if col not in excluded:
            excluded[col] = pd.NA

    audit.update(
        {
            "pit_filtered_profiling_scope_winner_n": int(len(pit_base)),
            "excluded_non_pit_winner_candidate_n": int(len(excluded)),
            "excluded_non_pit_winner_candidate_rate": float(len(excluded) / len(raw_base)) if len(raw_base) else np.nan,
            "pit_filter_unique_instrument_n": int(pit_base["instrument"].nunique()) if len(pit_base) else 0,
            "pit_filter_unique_trade_open_date_n": int(pit_base["trade_open_date"].nunique()) if len(pit_base) else 0,
        }
    )
    if pit_base.empty:
        failures.append("PIT_filter_no_09A_winner_candidate_in_universe")
    duplicate_identity_n = int(pit_base.duplicated(["sample_id", "selected_target_id", "source_denominator_id"]).sum())
    if duplicate_identity_n:
        failures.append(f"PIT_filtered_profiling_identity_duplicate:{duplicate_identity_n}")
    return pit_base, excluded, audit, failures


def load_winner_base(path: Path, config: dict[str, Any]) -> tuple[pd.DataFrame, dict[str, Any], list[str]]:
    required = {
        "sample_id",
        "selected_target_id",
        "canonical_event_id",
        "instrument",
        "trade_time",
        "event_split",
        "event_regime_bucket",
        "episode_regime_bucket",
        "denominator_id",
        "horizon_complete_120d",
        config["run"]["winner_label_column"],
    }
    frame = pd.read_parquet(path)
    failures = []
    missing = missing_columns(frame, required)
    if missing:
        failures.append(f"09A_schema_missing_columns:{','.join(missing)}")
        return pd.DataFrame(), {"09a_row_n": len(frame)}, failures

    winner_col = config["run"]["winner_label_column"]
    out = frame.loc[frame[winner_col].map(boolish) & frame["horizon_complete_120d"].map(boolish)].copy()
    out["trade_open_date"] = out["trade_time"].map(date_string)
    out["split"] = out["event_split"].map(stable_str)
    out["event_regime_state"] = out["event_regime_bucket"].map(normalize_regime_state)
    out["episode_regime_state_raw"] = out["episode_regime_bucket"].map(stable_str)
    resolved = pd.DataFrame(
        [resolve_path_regime(row.episode_regime_bucket, row.event_regime_bucket) for row in out.itertuples()],
        index=out.index,
        columns=["path_regime_state", "path_regime_source"],
    )
    out[["path_regime_state", "path_regime_source"]] = resolved
    out["binding_canonical_event_id"] = out["canonical_event_id"].map(stable_str)
    out["source_denominator_id"] = out["denominator_id"].map(stable_str)
    out["profiling_row_identity"] = make_composite_key(out, ["sample_id", "selected_target_id", "denominator_id"])
    out["winner_120"] = out[winner_col].map(boolish)
    out["horizon_complete_120d"] = out["horizon_complete_120d"].map(boolish)

    duplicate_identity_n = int(out.duplicated(["sample_id", "selected_target_id", "denominator_id"]).sum())
    if duplicate_identity_n:
        failures.append(f"09A_profiling_identity_duplicate:{duplicate_identity_n}")
    empty_trade_date_n = int(out["trade_open_date"].eq("").sum())
    if empty_trade_date_n:
        failures.append(f"09A_trade_open_date_unparseable:{empty_trade_date_n}")

    keep_cols = [
        "sample_id",
        "selected_target_id",
        "instrument",
        "trade_open_date",
        "split",
        "event_regime_state",
        "episode_regime_state_raw",
        "path_regime_state",
        "path_regime_source",
        "binding_canonical_event_id",
        "source_denominator_id",
        "profiling_row_identity",
        "winner_120",
        "horizon_complete_120d",
    ]
    audit = {
        "09a_row_n": int(len(frame)),
        "raw_09a_winner_candidate_n": int(len(out)),
        "profiling_identity_duplicate_n": duplicate_identity_n,
        "profiling_trade_open_date_unparseable_n": empty_trade_date_n,
        "raw_episode_regime_missing_event_fallback_n": int(
            out["path_regime_source"].eq(PATH_REGIME_SOURCE_EVENT_FALLBACK).sum()
        ),
        "raw_episode_regime_missing_event_fallback_rate": float(
            out["path_regime_source"].eq(PATH_REGIME_SOURCE_EVENT_FALLBACK).mean()
        )
        if len(out)
        else np.nan,
        "raw_path_regime_unresolved_missing_n": int(out["path_regime_source"].eq(PATH_REGIME_SOURCE_UNRESOLVED).sum()),
        "raw_path_regime_source_counts": out["path_regime_source"].value_counts(dropna=False).to_dict(),
    }
    return out[keep_cols].copy(), audit, failures


def load_injury_scope(path: Path, config: dict[str, Any]) -> tuple[pd.DataFrame, dict[str, Any], list[str]]:
    required = {
        "population_id",
        "input_event_key",
        "sample_id",
        "selected_target_id",
        "input_denominator_id",
        "denominator_id",
        "split",
        "event_regime_bucket",
        "admission_status",
        "winner_120",
        "E1_missed_winner_flag",
    }
    frame = pd.read_parquet(path)
    failures = []
    missing = missing_columns(frame, required)
    if missing:
        failures.append(f"10A_schema_missing_columns:{','.join(missing)}")
        return pd.DataFrame(), {"10a_row_n": len(frame)}, failures
    scope = config["scope"]
    out = frame.loc[
        frame["population_id"].eq(scope["injury_population_id"])
        & frame["denominator_id"].eq(scope["injury_denominator_id"])
        & frame["admission_status"].eq(scope.get("injury_admission_status", "admitted"))
    ].copy()
    out["injury_input_denominator_id"] = out["input_denominator_id"].map(stable_str)
    out["injury_event_regime_state"] = out["event_regime_bucket"].map(stable_str)
    out["E1_missed_winner_flag"] = out["E1_missed_winner_flag"].map(boolish)
    out["winner_120"] = out["winner_120"].map(boolish)
    duplicate_join_key_n = int(out.duplicated(["sample_id", "selected_target_id", "input_denominator_id"]).sum())
    if duplicate_join_key_n:
        failures.append(f"10A_injury_to_09A_join_key_duplicate:{duplicate_join_key_n}")
    audit = {
        "10a_row_n": int(len(frame)),
        "injury_scope_row_n": int(len(out)),
        "injury_scope_winner_n": int(out["winner_120"].sum()),
        "injury_join_key_duplicate_n": duplicate_join_key_n,
    }
    keep_cols = [
        "sample_id",
        "selected_target_id",
        "input_denominator_id",
        "injury_input_denominator_id",
        "input_event_key",
        "split",
        "injury_event_regime_state",
        "winner_120",
        "E1_missed_winner_flag",
    ]
    return out[keep_cols].copy(), audit, failures


def load_10c_reference(path: Path, config: dict[str, Any]) -> tuple[pd.DataFrame, dict[str, Any], list[str]]:
    required = {
        "model_id",
        "ablation_id",
        "capacity_id",
        "threshold_id",
        "population_id",
        "denominator_id",
        "split",
        "input_event_key",
        "candidate_rejected_flag",
        "bridge_positive_flag",
        "mfe_20d",
    }
    frame = pd.read_parquet(path)
    failures = []
    missing = missing_columns(frame, required)
    if missing:
        failures.append(f"10C_schema_missing_columns:{','.join(missing)}")
        return pd.DataFrame(), {"10c_row_n": len(frame)}, failures
    ref = config["injury"]
    scope = config["scope"]
    out = frame.loc[
        frame["model_id"].eq(ref["reference_10c_model_id"])
        & frame["ablation_id"].eq(ref["reference_10c_ablation_id"])
        & frame["capacity_id"].eq(ref["reference_10c_capacity_id"])
        & frame["threshold_id"].eq(ref["reference_10c_threshold_id"])
        & frame["population_id"].eq(scope["injury_population_id"])
        & frame["denominator_id"].eq(scope["injury_denominator_id"])
    ].copy()
    duplicate_ref_key_n = int(out.duplicated(["input_event_key", "split"]).sum())
    if duplicate_ref_key_n:
        failures.append(f"10C_reference_input_event_key_split_duplicate:{duplicate_ref_key_n}")
    out["tenc_full_keep9000_rejected_flag"] = out["candidate_rejected_flag"].map(boolish)
    out["bridge_winner"] = out["bridge_positive_flag"].map(boolish)
    out["tenc_mfe_20d"] = pd.to_numeric(out["mfe_20d"], errors="coerce")
    keep_cols = [
        "input_event_key",
        "split",
        "tenc_full_keep9000_rejected_flag",
        "bridge_winner",
        "tenc_mfe_20d",
    ]
    audit = {
        "10c_row_n": int(len(frame)),
        "10c_reference_row_n": int(len(out)),
        "10c_reference_duplicate_key_n": duplicate_ref_key_n,
    }
    return out[keep_cols].copy(), audit, failures


def load_board_metadata(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path)
    cols = [col for col in ["instrument", "board_bucket", "name"] if col in frame.columns]
    out = frame[cols].copy()
    for col in cols:
        out[col] = out[col].map(stable_str)
    return out.drop_duplicates("instrument")


def board_bucket_from_code(instrument: str) -> str:
    text = stable_str(instrument).upper()
    code = text[2:] if text.startswith(("SH", "SZ")) else text
    if text.startswith("SZ300") or text.startswith("SH688") or code.startswith("300") or code.startswith("688"):
        return "chinext_star"
    if text.startswith(("SH", "SZ")):
        return "main_board"
    return "unknown"


def canonical_board_bucket(value: Any) -> str:
    text = stable_str(value).strip().lower()
    if text in {"chinext", "star", "star_market", "sci_tech", "sci_tech_board", "chinext_star"}:
        return "chinext_star"
    if text in {"main_board", "main", "sme", "small_mid_board"}:
        return "main_board"
    return text if text else "unknown"


def is_st_like_name(value: Any) -> bool:
    text = stable_str(value).upper().replace(" ", "")
    return any(token in text for token in ["*ST", "ST", "退市"])


def board_limit_for_row(
    instrument: str,
    trade_open_date: str,
    board_by_instrument: dict[str, dict[str, str]],
    paths: dict[str, Path],
    config: dict[str, Any],
) -> dict[str, Any]:
    meta = board_by_instrument.get(instrument, {})
    raw_board = meta.get("board_bucket", "")
    board_bucket = canonical_board_bucket(raw_board)
    board_source = "instrument_metadata_target_universe.board_bucket" if board_bucket != "unknown" else ""
    if board_bucket == "unknown":
        board_bucket = board_bucket_from_code(instrument)
        board_source = "code_prefix_fallback" if board_bucket != "unknown" else "unknown"

    proxy_cfg = config["board_limit_proxy"]
    if is_st_like_name(meta.get("name", "")):
        return {
            "board_limit_proxy_used": float(proxy_cfg["st"]),
            "board_bucket_used": "st",
            "board_bucket_source": board_source or "instrument_metadata_target_universe.name",
            "limit_proxy_status": "ok",
            "st_status_source": "instrument_metadata_target_universe.name",
        }

    sh_history = paths["sh_name_history_dir"] / f"{instrument}.csv"
    if sh_history.is_file():
        try:
            sh_frame = pd.read_csv(sh_history)
            if "name" in sh_frame.columns and sh_frame["name"].map(is_st_like_name).any():
                return {
                    "board_limit_proxy_used": float(proxy_cfg.get(board_bucket, proxy_cfg["unknown_fallback"])),
                    "board_bucket_used": board_bucket,
                    "board_bucket_source": board_source,
                    "limit_proxy_status": "st_status_not_evaluable",
                    "st_status_source": "sh_name_history_without_date_non_blocking",
                }
        except Exception:
            pass

    proxy_key = board_bucket if board_bucket in {"main_board", "chinext_star"} else "unknown_fallback"
    status = "ok" if board_bucket in {"main_board", "chinext_star"} else "board_unknown"
    return {
        "board_limit_proxy_used": float(proxy_cfg[proxy_key]),
        "board_bucket_used": board_bucket,
        "board_bucket_source": board_source,
        "limit_proxy_status": status,
        "st_status_source": "not_evaluable_non_blocking",
    }


def read_bars_for_instrument(
    instrument: str,
    paths: dict[str, Path],
    bars_cache: dict[str, tuple[pd.DataFrame | None, str, str]],
) -> tuple[pd.DataFrame | None, str, str]:
    if instrument in bars_cache:
        return bars_cache[instrument]
    candidates = [
        (paths["qfq_dir"] / f"{instrument}.csv", "qfq_dir"),
        (paths["qfq_fallback_dir"] / f"{instrument}.csv", "qfq_fallback_dir"),
    ]
    required = {"date", "open", "high", "low", "close"}
    for path, source_kind in candidates:
        if not path.is_file():
            continue
        try:
            frame = pd.read_csv(path)
        except Exception:
            continue
        if required - set(frame.columns):
            continue
        out = frame[["date", "open", "high", "low", "close"]].copy()
        out["date"] = out["date"].map(date_string)
        for col in ["open", "high", "low", "close"]:
            out[col] = pd.to_numeric(out[col], errors="coerce")
        out = out.sort_values("date").drop_duplicates("date", keep="last").reset_index(drop=True)
        bars_cache[instrument] = (out, str(path), source_kind)
        return bars_cache[instrument]
    bars_cache[instrument] = (None, "", "missing")
    return bars_cache[instrument]


def finite_positive(values: np.ndarray) -> bool:
    return bool(np.isfinite(values).all() and (values > 0).all())


def recompute_window_extreme(values: np.ndarray, window: int, agg: str) -> float:
    part = values[: min(window, len(values))]
    if len(part) == 0:
        return float("nan")
    return float(np.nanmax(part) if agg == "max" else np.nanmin(part))


def compute_path_metrics_for_event(
    bars: pd.DataFrame | None,
    trade_open_date: str,
    thresholds: Thresholds,
    forward_sessions: int,
    board_limit_proxy: float,
) -> dict[str, Any]:
    base = {
        "winner_path_status": PATH_MISSING,
        "trade_open_price": np.nan,
        "day_to_target": np.nan,
        "day_to_confirm": np.nan,
        "pre_target_window_status": "",
        "deepest_pre_target_ret_low": np.nan,
        "day_to_deepest_pre_target_low": np.nan,
        "max_drawdown_to_target": np.nan,
        "deepest_ret_low_20": np.nan,
        "day_to_deepest_low_20": np.nan,
        "pre_target_touch_failure_lower_flag": False,
        "pre_target_close_drawdown_failure_proxy_flag": False,
        "max_single_day_close_return_to_target": np.nan,
        "max_gap_open_return_to_target": np.nan,
        "limit_like_up_day_count_to_target": np.nan,
        "mfe_20_recomputed": np.nan,
        "mfe_60_recomputed": np.nan,
        "mfe_120_recomputed": np.nan,
        "mae_20_recomputed": np.nan,
        "mae_60_recomputed": np.nan,
        "mae_120_recomputed": np.nan,
    }
    if bars is None or not trade_open_date:
        return base
    date_to_pos = {date: pos for pos, date in enumerate(bars["date"].tolist())}
    if trade_open_date not in date_to_pos:
        return base
    pos = date_to_pos[trade_open_date]
    end = pos + 1 + forward_sessions
    if end > len(bars):
        return base

    trade_open_price = float(bars.loc[pos, "open"])
    forward = bars.iloc[pos + 1 : end]
    open_v = forward["open"].to_numpy(dtype=float)
    high_v = forward["high"].to_numpy(dtype=float)
    low_v = forward["low"].to_numpy(dtype=float)
    close_v = forward["close"].to_numpy(dtype=float)
    if not finite_positive(np.r_[trade_open_price, open_v, high_v, low_v, close_v]):
        base["winner_path_status"] = PATH_METRIC_INCONSISTENCY
        base["trade_open_price"] = trade_open_price
        return base

    ret_high = high_v / trade_open_price - 1.0
    ret_low = low_v / trade_open_price - 1.0
    mfe_120 = recompute_window_extreme(ret_high, 120, "max")
    base.update(
        {
            "trade_open_price": trade_open_price,
            "mfe_20_recomputed": recompute_window_extreme(ret_high, 20, "max"),
            "mfe_60_recomputed": recompute_window_extreme(ret_high, 60, "max"),
            "mfe_120_recomputed": mfe_120,
            "mae_20_recomputed": recompute_window_extreme(ret_low, 20, "min"),
            "mae_60_recomputed": recompute_window_extreme(ret_low, 60, "min"),
            "mae_120_recomputed": recompute_window_extreme(ret_low, 120, "min"),
        }
    )

    target_hits = np.flatnonzero(ret_high >= thresholds.winner_mfe_threshold)
    if len(target_hits) == 0:
        base["winner_path_status"] = PATH_BASIS_MISMATCH
        return base
    target_idx = int(target_hits[0])
    day_to_target = target_idx + 1
    base["winner_path_status"] = PATH_OK
    base["day_to_target"] = float(day_to_target)

    confirm_hits = np.flatnonzero(ret_high >= thresholds.confirm_upper_barrier)
    if len(confirm_hits):
        base["day_to_confirm"] = float(int(confirm_hits[0]) + 1)

    target_slice = slice(0, day_to_target)
    low_to_target = ret_low[target_slice]
    low20_len = min(20, day_to_target)
    if low20_len > 0:
        low20 = ret_low[:low20_len]
        low20_arg = int(np.nanargmin(low20))
        base["deepest_ret_low_20"] = float(low20[low20_arg])
        base["day_to_deepest_low_20"] = float(low20_arg + 1)

    prev_close = np.r_[trade_open_price, close_v[: max(day_to_target - 1, 0)]]
    close_ret = close_v[target_slice] / prev_close - 1.0
    open_gap = open_v[target_slice] / prev_close - 1.0
    base["max_single_day_close_return_to_target"] = float(np.nanmax(close_ret))
    base["max_gap_open_return_to_target"] = float(np.nanmax(open_gap))
    base["limit_like_up_day_count_to_target"] = int(np.sum(close_ret >= board_limit_proxy))

    if day_to_target == 1:
        base["pre_target_window_status"] = "empty_pre_target_window"
        base["pre_target_touch_failure_lower_flag"] = False
        base["pre_target_close_drawdown_failure_proxy_flag"] = False
        return base

    pre_len = day_to_target - 1
    pre_low_ret = ret_low[:pre_len]
    pre_low_arg = int(np.nanargmin(pre_low_ret))
    running_high = np.maximum.accumulate(high_v[:pre_len])
    drawdown = low_v[:pre_len] / running_high - 1.0
    running_close = np.maximum.accumulate(np.r_[trade_open_price, close_v[:pre_len]])[1:]
    close_drawdown = close_v[:pre_len] / running_close - 1.0
    base["pre_target_window_status"] = "ok"
    base["deepest_pre_target_ret_low"] = float(pre_low_ret[pre_low_arg])
    base["day_to_deepest_pre_target_low"] = float(pre_low_arg + 1)
    base["max_drawdown_to_target"] = float(np.nanmin(drawdown))
    base["pre_target_touch_failure_lower_flag"] = bool(
        base["deepest_pre_target_ret_low"] <= thresholds.failure_lower_barrier
    )
    base["pre_target_close_drawdown_failure_proxy_flag"] = bool(
        np.nanmin(close_drawdown) <= thresholds.failure_max_drawdown
    )
    return base


def add_path_metrics(
    base: pd.DataFrame,
    paths: dict[str, Path],
    config: dict[str, Any],
    thresholds: Thresholds,
) -> tuple[pd.DataFrame, dict[str, str], dict[str, Any]]:
    board_meta = load_board_metadata(paths["board_metadata"])
    board_by_instrument = board_meta.set_index("instrument")[["board_bucket", "name"]].to_dict("index")
    bars_cache: dict[str, tuple[pd.DataFrame | None, str, str]] = {}
    path_cache: dict[tuple[str, str], dict[str, Any]] = {}
    rows = []
    qfq_used_files: dict[str, str] = {}
    forward_sessions = int(config["forward_path"]["forward_sessions"])

    for row in base.itertuples(index=False):
        instrument = row.instrument
        trade_open_date = row.trade_open_date
        board = board_limit_for_row(instrument, trade_open_date, board_by_instrument, paths, config)
        cache_key = (instrument, trade_open_date)
        if cache_key not in path_cache:
            bars, qfq_source_path, qfq_source_kind = read_bars_for_instrument(instrument, paths, bars_cache)
            metrics = compute_path_metrics_for_event(
                bars,
                trade_open_date,
                thresholds,
                forward_sessions,
                float(board["board_limit_proxy_used"]),
            )
            metrics["qfq_source_path"] = qfq_source_path
            metrics["qfq_source_kind"] = qfq_source_kind
            path_cache[cache_key] = metrics
            if qfq_source_path:
                qfq_used_files[relative_to_repo(Path(qfq_source_path))] = hash_or_empty(Path(qfq_source_path))
        else:
            metrics = path_cache[cache_key].copy()
        record = row._asdict()
        record.update(board)
        record.update(metrics)
        rows.append(record)

    out = pd.DataFrame(rows)
    out["winner_mfe_threshold"] = thresholds.winner_mfe_threshold
    out["confirm_upper_barrier"] = thresholds.confirm_upper_barrier
    out["failure_lower_barrier"] = thresholds.failure_lower_barrier
    out["failure_max_drawdown"] = thresholds.failure_max_drawdown
    out["close_based_drawdown_policy"] = thresholds.close_based_drawdown_policy
    out["hard_failure_first_blocks_winner"] = thresholds.hard_failure_first_blocks_winner
    audit = {
        "qfq_used_file_count": int(len(qfq_used_files)),
        "unique_forward_lookup_count": int(len(path_cache)),
        "qfq_used_files_hash": directory_hash([REPO_ROOT / rel for rel in qfq_used_files]),
    }
    return out, qfq_used_files, audit


def join_injury_and_10c(
    path_df: pd.DataFrame,
    injury: pd.DataFrame,
    tenc_ref: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, Any], list[str]]:
    failures = []
    audit: dict[str, Any] = {}
    injury_keys = ["sample_id", "selected_target_id", "input_denominator_id"]
    base_keys = ["sample_id", "selected_target_id", "source_denominator_id"]

    injury_winners = injury.loc[injury["winner_120"].map(boolish)].copy()
    base_key_frame = path_df[base_keys + ["profiling_row_identity", "path_regime_state"]].copy()
    base_duplicate_key_n = int(base_key_frame.duplicated(base_keys).sum())
    match = injury_winners.merge(
        base_key_frame,
        left_on=injury_keys,
        right_on=base_keys,
        how="left",
        indicator=True,
    )
    missing_pit_profile_n = int(match["_merge"].eq("left_only").sum())
    duplicate_match_n = int(match.loc[match["_merge"].eq("both")].duplicated(injury_keys).sum())
    audit["raw_injury_scope_winner_n"] = int(len(injury_winners))
    audit["injury_winner_to_pit_profile_row_n"] = int(len(match))
    audit["injury_winner_to_pit_profile_missing_n"] = missing_pit_profile_n
    audit["injury_winner_to_pit_profile_duplicate_n"] = duplicate_match_n
    audit["pit_profile_injury_join_key_duplicate_n"] = base_duplicate_key_n
    audit["injury_excluded_non_pit_universe_n"] = missing_pit_profile_n
    audit["injury_excluded_non_pit_universe_rate"] = (
        float(missing_pit_profile_n / len(injury_winners)) if len(injury_winners) else np.nan
    )
    audit["injury_excluded_unmatched_pit_profile_n"] = missing_pit_profile_n
    audit["injury_winner_to_09a_row_n"] = int(len(match))
    audit["injury_winner_to_09a_missing_n"] = missing_pit_profile_n
    audit["injury_winner_to_09a_duplicate_n"] = duplicate_match_n
    if duplicate_match_n:
        failures.append(f"injury_to_PIT_filtered_09A_duplicate:{duplicate_match_n}")
    if base_duplicate_key_n:
        failures.append(f"PIT_filtered_09A_injury_join_key_duplicate:{base_duplicate_key_n}")

    injury_keep = injury[
        [
            "sample_id",
            "selected_target_id",
            "input_denominator_id",
            "injury_input_denominator_id",
            "input_event_key",
            "split",
            "injury_event_regime_state",
            "E1_missed_winner_flag",
        ]
    ].copy()
    merged = path_df.merge(
        injury_keep,
        left_on=base_keys + ["split"],
        right_on=injury_keys + ["split"],
        how="left",
        suffixes=("", "_injury"),
    )
    merged["injury_scope_flag"] = merged["input_event_key"].notna()
    audit["pit_filtered_injury_scope_winner_n"] = int(merged["injury_scope_flag"].map(boolish).sum())
    if "input_denominator_id" in merged.columns:
        merged = merged.drop(columns=["input_denominator_id"])

    tenc_join = injury.merge(tenc_ref, on=["input_event_key", "split"], how="left", indicator=True)
    audit["injury_scope_to_10c_row_n"] = int(len(tenc_join))
    audit["injury_scope_to_10c_missing_n"] = int(tenc_join["_merge"].eq("left_only").sum())
    audit["injury_scope_to_10c_duplicate_n"] = int(tenc_ref.duplicated(["input_event_key", "split"]).sum())
    if audit["injury_scope_to_10c_missing_n"]:
        failures.append(f"injury_scope_to_10C_missing:{audit['injury_scope_to_10c_missing_n']}")
    if audit["injury_scope_to_10c_duplicate_n"]:
        failures.append(f"injury_scope_to_10C_duplicate:{audit['injury_scope_to_10c_duplicate_n']}")

    merged = merged.merge(tenc_ref, on=["input_event_key", "split"], how="left")
    merged["E1_missed_winner_flag"] = merged["E1_missed_winner_flag"].where(
        merged["injury_scope_flag"], False
    ).map(boolish)
    merged["bridge_winner"] = merged["bridge_winner"].where(merged["injury_scope_flag"], False).map(boolish)
    merged["tenc_full_keep9000_rejected_flag"] = merged["tenc_full_keep9000_rejected_flag"].where(
        merged["injury_scope_flag"], False
    ).map(boolish)
    return merged, audit, failures


def add_seed_flags(frame: pd.DataFrame, thresholds: Thresholds, config: dict[str, Any]) -> pd.DataFrame:
    out = frame.copy()
    ok = out["winner_path_status"].eq(PATH_OK)
    out["seed_gap_or_event_driven_flag"] = ok & (
        (out["limit_like_up_day_count_to_target"].fillna(0) >= 2)
        | (out["max_gap_open_return_to_target"] >= 0.08)
        | (out["max_single_day_close_return_to_target"] >= 0.18)
    )
    out["seed_shakeout_reversal_flag"] = ok & (
        (out["deepest_ret_low_20"] <= thresholds.failure_lower_barrier)
        & (out["day_to_deepest_low_20"] < out["day_to_target"])
    )
    out["seed_volatile_chop_flag"] = ok & (
        (out["max_drawdown_to_target"] <= -0.15)
        & (out["mfe_60_recomputed"] >= thresholds.continuation_60_min_mfe_pct)
        & (out["mae_60_recomputed"] <= -0.12)
    )
    out["seed_early_momentum_flag"] = ok & (
        (out["day_to_confirm"] <= thresholds.confirm_20_horizon_days)
        & (out["day_to_target"] <= 60)
        & (out["deepest_ret_low_20"] > thresholds.failure_lower_barrier)
        & (out["max_drawdown_to_target"] > -0.12)
    )
    out["seed_late_bloomer_flag"] = ok & (
        (out["day_to_target"] > 60) & (out["mfe_20_recomputed"] < thresholds.confirm_upper_barrier)
    )
    out["seed_flag_overlap_n"] = out[SEED_FLAGS].sum(axis=1).astype(int)
    precedence = config["seed_hypothesis"].get("precedence", SEED_FLAGS)
    labels = []
    for row in out[precedence].itertuples(index=False, name=None):
        assigned = ""
        for flag, active in zip(precedence, row, strict=False):
            if bool(active):
                assigned = flag.replace("seed_", "").replace("_flag", "")
                break
        labels.append(assigned)
    out["winner_path_archetype_v0"] = labels
    out.loc[out["winner_path_archetype_v0"].eq(""), "winner_path_archetype_v0"] = pd.NA
    out["archetype_status"] = np.where(out["winner_path_archetype_v0"].notna(), "seed_non_binding", "not_assigned")
    return out


def reporting_views(config: dict[str, Any]) -> list[dict[str, str]]:
    splits = config["distribution_audit"]["split_levels"]
    regimes = config["distribution_audit"]["path_regime_levels"]
    views: list[dict[str, str]] = []
    for split in splits:
        views.append({"reporting_view": "split_only", "split": split, "path_regime_state": "all"})
    for regime in regimes:
        views.append({"reporting_view": "regime_only", "split": "all", "path_regime_state": regime})
    for split in splits:
        for regime in regimes:
            views.append({"reporting_view": "split_regime", "split": split, "path_regime_state": regime})
    return views


def filter_view(frame: pd.DataFrame, split: str, path_regime_state: str) -> pd.DataFrame:
    mask = pd.Series(True, index=frame.index)
    if split != "all":
        mask &= frame["split"].eq(split)
    if path_regime_state != "all":
        mask &= frame["path_regime_state"].eq(path_regime_state)
    return frame.loc[mask]


def min_commentary_n(config: dict[str, Any], regime: str) -> int:
    style = config["style_migration"]
    if regime != "all":
        return int(style["min_regime_n_for_commentary"])
    return int(style["min_split_n_for_commentary"])


def view_power_flag(winner_n: int, config: dict[str, Any], regime: str = "all") -> str:
    return "low_power" if winner_n < min_commentary_n(config, regime) else "ok"


def quantile_name(q: float) -> str:
    return f"p{int(round(q * 100)):02d}"


def metric_distribution(frame: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    quantiles = [float(q) for q in config["distribution_audit"]["quantiles"]]
    rows = []
    for view in reporting_views(config):
        part = filter_view(frame, view["split"], view["path_regime_state"])
        winner_n = int(len(part))
        for metric in PATH_METRICS:
            series = pd.to_numeric(part[metric], errors="coerce") if metric in part else pd.Series(dtype=float)
            clean = series.dropna()
            row = {
                **view,
                "metric": metric,
                "winner_n": winner_n,
                "non_null_metric_n": int(clean.shape[0]),
                "missing_rate": float(1.0 - clean.shape[0] / winner_n) if winner_n else np.nan,
                "mean": float(clean.mean()) if len(clean) else np.nan,
                "std": float(clean.std(ddof=1)) if len(clean) > 1 else np.nan,
                "min": float(clean.min()) if len(clean) else np.nan,
                "max": float(clean.max()) if len(clean) else np.nan,
                "power_flag": view_power_flag(winner_n, config, view["path_regime_state"]),
            }
            for q in quantiles:
                row[quantile_name(q)] = float(clean.quantile(q)) if len(clean) else np.nan
            rows.append(row)
    out = pd.DataFrame(rows)
    return out.sort_values(["reporting_view", "split", "path_regime_state", "metric"]).reset_index(drop=True)


def metric_correlation(frame: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    rows = []
    for view in reporting_views(config):
        part = filter_view(frame, view["split"], view["path_regime_state"])
        winner_n = int(len(part))
        metric_frame = part[PATH_METRICS].apply(pd.to_numeric, errors="coerce")
        for i, metric_x in enumerate(PATH_METRICS):
            for metric_y in PATH_METRICS[i + 1 :]:
                clean = metric_frame[[metric_x, metric_y]].dropna()
                corr = float(clean[metric_x].corr(clean[metric_y], method="spearman")) if len(clean) > 1 else np.nan
                rows.append(
                    {
                        **view,
                        "metric_x": metric_x,
                        "metric_y": metric_y,
                        "winner_n": winner_n,
                        "non_null_metric_n": int(len(clean)),
                        "spearman_corr": corr,
                        "power_flag": view_power_flag(winner_n, config, view["path_regime_state"]),
                    }
                )
    return pd.DataFrame(rows).sort_values(["reporting_view", "split", "path_regime_state", "metric_x", "metric_y"])


def histogram_table(frame: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    rows = []
    bins_cfg = config["distribution_audit"]["histogram_bins"]
    min_bin_count = int(config["style_migration"]["min_bin_count"])
    for view in reporting_views(config):
        part = filter_view(frame, view["split"], view["path_regime_state"])
        winner_n = int(len(part))
        for metric, bins in bins_cfg.items():
            series = pd.to_numeric(part[metric], errors="coerce").dropna()
            counts, edges = np.histogram(series.to_numpy(dtype=float), bins=np.array(bins, dtype=float))
            non_null_n = int(len(series))
            for idx, count in enumerate(counts):
                bin_left = float(edges[idx])
                bin_right = float(edges[idx + 1])
                rows.append(
                    {
                        **view,
                        "metric": metric,
                        "bin_left": bin_left,
                        "bin_right": bin_right,
                        "bin_label": f"[{bin_left:g},{bin_right:g})",
                        "winner_n": winner_n,
                        "non_null_metric_n": non_null_n,
                        "bin_count": int(count),
                        "bin_rate": float(count / non_null_n) if non_null_n else np.nan,
                        "bin_power_flag": "low_power" if count < min_bin_count else "ok",
                        "power_flag": view_power_flag(winner_n, config, view["path_regime_state"]),
                    }
                )
    return pd.DataFrame(rows).sort_values(["reporting_view", "split", "path_regime_state", "metric", "bin_left"])


def ks_statistic(a: pd.Series, b: pd.Series) -> float:
    a_values = np.sort(pd.to_numeric(a, errors="coerce").dropna().to_numpy(dtype=float))
    b_values = np.sort(pd.to_numeric(b, errors="coerce").dropna().to_numpy(dtype=float))
    if len(a_values) == 0 or len(b_values) == 0:
        return float("nan")
    values = np.sort(np.unique(np.concatenate([a_values, b_values])))
    cdf_a = np.searchsorted(a_values, values, side="right") / len(a_values)
    cdf_b = np.searchsorted(b_values, values, side="right") / len(b_values)
    return float(np.max(np.abs(cdf_a - cdf_b)))


def psi_statistic(comp: pd.Series, base: pd.Series, bins: list[float], min_bin_count: int) -> tuple[float, str]:
    comp_clean = pd.to_numeric(comp, errors="coerce").dropna().to_numpy(dtype=float)
    base_clean = pd.to_numeric(base, errors="coerce").dropna().to_numpy(dtype=float)
    if len(comp_clean) == 0 or len(base_clean) == 0:
        return float("nan"), "low_power"
    comp_counts, _ = np.histogram(comp_clean, bins=np.array(bins, dtype=float))
    base_counts, _ = np.histogram(base_clean, bins=np.array(bins, dtype=float))
    low_power = bool(((comp_counts < min_bin_count) | (base_counts < min_bin_count)).any())
    valid = (comp_counts >= min_bin_count) & (base_counts >= min_bin_count)
    if not valid.any():
        return float("nan"), "low_power"
    comp_pct = comp_counts[valid] / len(comp_clean)
    base_pct = base_counts[valid] / len(base_clean)
    eps = 1e-12
    psi = np.sum((comp_pct - base_pct) * np.log((comp_pct + eps) / (base_pct + eps)))
    return float(psi), "low_power" if low_power else "ok"


def style_row(
    frame: pd.DataFrame,
    config: dict[str, Any],
    metric: str,
    comp: pd.DataFrame,
    base: pd.DataFrame,
    view: dict[str, str],
    comparison_axis: str,
    comparison_id: str,
    baseline_split: str,
    baseline_path_regime_state: str,
) -> dict[str, Any]:
    quantiles = [float(q) for q in config["distribution_audit"]["quantiles"]]
    comp_series = pd.to_numeric(comp[metric], errors="coerce").dropna()
    base_series = pd.to_numeric(base[metric], errors="coerce").dropna()
    row = {
        **view,
        "comparison_axis": comparison_axis,
        "comparison_id": comparison_id,
        "baseline_split": baseline_split,
        "baseline_path_regime_state": baseline_path_regime_state,
        "metric": metric,
        "winner_n": int(len(comp)),
        "non_null_metric_n": int(len(comp_series)),
        "baseline_winner_n": int(len(base)),
        "baseline_non_null_metric_n": int(len(base_series)),
        "standardized_mean_delta": np.nan,
        "ks_statistic": ks_statistic(comp_series, base_series),
        "psi": np.nan,
        "psi_bin_power_flag": "not_configured",
        "power_flag": view_power_flag(int(len(comp)), config, view["path_regime_state"]),
    }
    if len(comp_series) and len(base_series):
        base_std = float(base_series.std(ddof=1)) if len(base_series) > 1 else np.nan
        row["standardized_mean_delta"] = (
            float((comp_series.mean() - base_series.mean()) / base_std)
            if base_std and not math.isnan(base_std)
            else np.nan
        )
    for q in quantiles:
        row[f"{quantile_name(q)}_delta"] = (
            float(comp_series.quantile(q) - base_series.quantile(q)) if len(comp_series) and len(base_series) else np.nan
        )
    bins = config["distribution_audit"]["histogram_bins"].get(metric)
    if bins is not None:
        psi, psi_power = psi_statistic(comp_series, base_series, bins, int(config["style_migration"]["min_bin_count"]))
        row["psi"] = psi
        row["psi_bin_power_flag"] = psi_power
    return row


def style_migration(frame: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    metrics = list(config["distribution_audit"]["histogram_bins"].keys())
    rows = []
    all_base = filter_view(frame, "all", "all")
    splits = [s for s in config["distribution_audit"]["split_levels"] if s != "all"]
    regimes = [r for r in config["distribution_audit"]["path_regime_levels"] if r != "all"]
    for metric in metrics:
        for split in splits:
            comp = filter_view(frame, split, "all")
            rows.append(
                style_row(
                    frame,
                    config,
                    metric,
                    comp,
                    all_base,
                    {"reporting_view": "split_only", "split": split, "path_regime_state": "all"},
                    "split_vs_all",
                    f"{split}_vs_all",
                    "all",
                    "all",
                )
            )
        for regime in regimes:
            comp = filter_view(frame, "all", regime)
            rows.append(
                style_row(
                    frame,
                    config,
                    metric,
                    comp,
                    all_base,
                    {"reporting_view": "regime_only", "split": "all", "path_regime_state": regime},
                    "regime_vs_all",
                    f"{regime}_vs_all",
                    "all",
                    "all",
                )
            )
        for left, right in [("train", "validation"), ("train", "robustness"), ("validation", "robustness")]:
            rows.append(
                style_row(
                    frame,
                    config,
                    metric,
                    filter_view(frame, left, "all"),
                    filter_view(frame, right, "all"),
                    {"reporting_view": "split_only", "split": left, "path_regime_state": "all"},
                    "split_pairwise",
                    f"{left}_vs_{right}",
                    right,
                    "all",
                )
            )
        for left, right in [("risk_on", "risk_off"), ("risk_on", "transition"), ("risk_off", "transition")]:
            rows.append(
                style_row(
                    frame,
                    config,
                    metric,
                    filter_view(frame, "all", left),
                    filter_view(frame, "all", right),
                    {"reporting_view": "regime_only", "split": "all", "path_regime_state": left},
                    "regime_pairwise",
                    f"{left}_vs_{right}",
                    "all",
                    right,
                )
            )
        for split in config["distribution_audit"]["split_levels"]:
            for regime in regimes:
                comp = filter_view(frame, split, regime)
                rows.append(
                    style_row(
                        frame,
                        config,
                        metric,
                        comp,
                        all_base,
                        {"reporting_view": "split_regime", "split": split, "path_regime_state": regime},
                        "split_regime_vs_all",
                        f"{split}_{regime}_vs_all",
                        "all",
                        "all",
                    )
                )
    return pd.DataFrame(rows).sort_values(
        ["metric", "comparison_axis", "comparison_id", "reporting_view", "split", "path_regime_state"]
    )


def hard_failure_calibration(frame: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    rows = []
    for population_scope, scope_frame in [
        ("profiling_scope", frame),
        ("injury_scope", frame.loc[frame["injury_scope_flag"].map(boolish)]),
    ]:
        for view in reporting_views(config):
            part = filter_view(scope_frame, view["split"], view["path_regime_state"])
            winner_n = int(len(part))
            path_available_n = int(part["winner_path_status"].eq(PATH_OK).sum())
            parsed_n = int(part["day_to_target"].notna().sum())
            basis_mismatch_n = int(part["winner_path_status"].eq(PATH_BASIS_MISMATCH).sum())
            touch_n = int(part["pre_target_touch_failure_lower_flag"].map(boolish).sum())
            close_proxy_n = int(part["pre_target_close_drawdown_failure_proxy_flag"].map(boolish).sum())
            rows.append(
                {
                    **view,
                    "population_scope": population_scope,
                    "winner_n": winner_n,
                    "path_available_winner_n": path_available_n,
                    "day_to_target_parsed_n": parsed_n,
                    "day_to_target_parsed_rate": float(parsed_n / winner_n) if winner_n else np.nan,
                    "winner_basis_mismatch_n": basis_mismatch_n,
                    "winner_basis_mismatch_rate": float(basis_mismatch_n / winner_n) if winner_n else np.nan,
                    "pre_target_touch_failure_lower_n": touch_n,
                    "pre_target_touch_failure_lower_rate": float(touch_n / path_available_n) if path_available_n else np.nan,
                    "pre_target_close_drawdown_failure_proxy_n": close_proxy_n,
                    "pre_target_close_drawdown_failure_proxy_rate": (
                        float(close_proxy_n / path_available_n) if path_available_n else np.nan
                    ),
                    "power_flag": view_power_flag(winner_n, config, view["path_regime_state"]),
                }
            )
    return pd.DataFrame(rows).sort_values(["population_scope", "reporting_view", "split", "path_regime_state"])


def seed_hypothesis_readout(frame: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    rows = []
    for view in reporting_views(config):
        part = filter_view(frame, view["split"], view["path_regime_state"])
        winner_n = int(len(part))
        for flag in SEED_FLAGS:
            true_n = int(part[flag].map(boolish).sum())
            rows.append(
                {
                    **view,
                    "seed_flag": flag,
                    "winner_n": winner_n,
                    "non_null_metric_n": int(part["winner_path_status"].eq(PATH_OK).sum()),
                    "seed_true_n": true_n,
                    "seed_true_rate": float(true_n / winner_n) if winner_n else np.nan,
                    "seed_status": "non_binding",
                    "power_flag": view_power_flag(winner_n, config, view["path_regime_state"]),
                }
            )
    return pd.DataFrame(rows).sort_values(["reporting_view", "split", "path_regime_state", "seed_flag"])


def seed_overlap(frame: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    rows = []
    for view in reporting_views(config):
        part = filter_view(frame, view["split"], view["path_regime_state"])
        winner_n = int(len(part))
        counts = part["seed_flag_overlap_n"].value_counts().to_dict()
        for overlap_n in range(0, len(SEED_FLAGS) + 1):
            count = int(counts.get(overlap_n, 0))
            rows.append(
                {
                    **view,
                    "overlap_type": "overlap_n",
                    "seed_flag_a": "",
                    "seed_flag_b": "",
                    "seed_flag_overlap_n": overlap_n,
                    "winner_n": winner_n,
                    "overlap_count": count,
                    "overlap_rate": float(count / winner_n) if winner_n else np.nan,
                    "power_flag": view_power_flag(winner_n, config, view["path_regime_state"]),
                }
            )
        for i, flag_a in enumerate(SEED_FLAGS):
            for flag_b in SEED_FLAGS[i + 1 :]:
                count = int((part[flag_a].map(boolish) & part[flag_b].map(boolish)).sum())
                rows.append(
                    {
                        **view,
                        "overlap_type": "pairwise",
                        "seed_flag_a": flag_a,
                        "seed_flag_b": flag_b,
                        "seed_flag_overlap_n": 2,
                        "winner_n": winner_n,
                        "overlap_count": count,
                        "overlap_rate": float(count / winner_n) if winner_n else np.nan,
                        "power_flag": view_power_flag(winner_n, config, view["path_regime_state"]),
                    }
                )
    return pd.DataFrame(rows).sort_values(
        ["reporting_view", "split", "path_regime_state", "overlap_type", "seed_flag_overlap_n", "seed_flag_a"]
    )


def bin_membership(series: pd.Series, left: float, right: float, is_last: bool) -> pd.Series:
    values = pd.to_numeric(series, errors="coerce")
    if is_last:
        return (values >= left) & (values <= right)
    return (values >= left) & (values < right)


def injury_concentration(frame: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    rows = []
    bins_cfg = config["distribution_audit"]["histogram_bins"]
    for view in reporting_views(config):
        part = filter_view(frame.loc[frame["injury_scope_flag"].map(boolish)], view["split"], view["path_regime_state"])
        winner_n_total = int(len(part))
        injured_total = int(part["tenc_full_keep9000_rejected_flag"].map(boolish).sum())
        bucket_specs: list[tuple[str, str, str, pd.Series]] = []
        for flag in SEED_FLAGS:
            bucket_specs.append(("seed_flag", flag, "true", part[flag].map(boolish)))
        for metric, bins in bins_cfg.items():
            for idx, (left, right) in enumerate(zip(bins[:-1], bins[1:], strict=False)):
                label = f"[{left:g},{right:g}{']' if idx == len(bins) - 2 else ')'}"
                bucket_specs.append(
                    ("metric_bin", metric, label, bin_membership(part[metric], float(left), float(right), idx == len(bins) - 2))
                )
        for bucket_type, bucket_name, bucket_value, mask in bucket_specs:
            bucket_winner_n = int(mask.sum())
            injured_n = int((mask & part["tenc_full_keep9000_rejected_flag"].map(boolish)).sum())
            share_injury = float(injured_n / injured_total) if injured_total else np.nan
            share_winner = float(bucket_winner_n / winner_n_total) if winner_n_total else np.nan
            rows.append(
                {
                    **view,
                    "bucket_type": bucket_type,
                    "bucket_name": bucket_name,
                    "bucket_value": bucket_value,
                    "winner_n": bucket_winner_n,
                    "injury_scope_winner_n": winner_n_total,
                    "injured_winner_n": injured_n,
                    "injury_rate": float(injured_n / bucket_winner_n) if bucket_winner_n else np.nan,
                    "share_of_injury": share_injury,
                    "share_of_winner": share_winner,
                    "injury_concentration_lift": (
                        float(share_injury - share_winner)
                        if not (pd.isna(share_injury) or pd.isna(share_winner))
                        else np.nan
                    ),
                    "non_null_metric_n": bucket_winner_n,
                    "power_flag": view_power_flag(bucket_winner_n, config, view["path_regime_state"]),
                }
            )
    return pd.DataFrame(rows).sort_values(
        ["reporting_view", "split", "path_regime_state", "bucket_type", "bucket_name", "bucket_value"]
    )


def phi_coefficient(n11: int, n10: int, n01: int, n00: int) -> float:
    denom = math.sqrt((n11 + n10) * (n01 + n00) * (n11 + n01) * (n10 + n00))
    return float((n11 * n00 - n10 * n01) / denom) if denom else np.nan


def bucket_alignment_2x2(frame: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    rows = []
    for view in reporting_views(config):
        part = filter_view(frame.loc[frame["injury_scope_flag"].map(boolish)], view["split"], view["path_regime_state"])
        for target in ["E1_missed_winner_flag", "bridge_winner"]:
            target_true = part[target].map(boolish)
            for flag in SEED_FLAGS:
                bucket_true = part[flag].map(boolish)
                n11 = int((bucket_true & target_true).sum())
                n10 = int((bucket_true & ~target_true).sum())
                n01 = int((~bucket_true & target_true).sum())
                n00 = int((~bucket_true & ~target_true).sum())
                union = n11 + n10 + n01
                rows.append(
                    {
                        **view,
                        "alignment_target": target,
                        "bucket_type": "seed_flag",
                        "bucket_name": flag,
                        "winner_n": int(len(part)),
                        "non_null_metric_n": int(len(part)),
                        "n11_bucket_and_target": n11,
                        "n10_bucket_only": n10,
                        "n01_target_only": n01,
                        "n00_neither": n00,
                        "jaccard": float(n11 / union) if union else np.nan,
                        "phi": phi_coefficient(n11, n10, n01, n00),
                        "p_target_given_bucket": float(n11 / (n11 + n10)) if (n11 + n10) else np.nan,
                        "p_bucket_given_target": float(n11 / (n11 + n01)) if (n11 + n01) else np.nan,
                        "power_flag": view_power_flag(int(len(part)), config, view["path_regime_state"]),
                    }
                )
    return pd.DataFrame(rows).sort_values(
        ["reporting_view", "split", "path_regime_state", "alignment_target", "bucket_name"]
    )


def seed_hypothesis_comparison(frame: pd.DataFrame) -> pd.DataFrame:
    definitions = {
        "seed_gap_or_event_driven_flag": "limit_like_up_day_count_to_target >= 2 OR max_gap_open_return_to_target >= 0.08 OR max_single_day_close_return_to_target >= 0.18",
        "seed_shakeout_reversal_flag": "deepest_ret_low_20 <= failure_lower_barrier AND day_to_deepest_low_20 < day_to_target",
        "seed_volatile_chop_flag": "max_drawdown_to_target <= -0.15 AND mfe_60_recomputed >= continuation_60.min_mfe_pct AND mae_60_recomputed <= -0.12",
        "seed_early_momentum_flag": "day_to_confirm <= confirm_20.horizon_days AND day_to_target <= 60 AND shallow drawdown filters",
        "seed_late_bloomer_flag": "day_to_target > 60 AND mfe_20_recomputed < confirm_upper_barrier",
    }
    rows = []
    winner_n = int(len(frame))
    for flag in SEED_FLAGS:
        true_n = int(frame[flag].map(boolish).sum())
        rows.append(
            {
                "seed_flag": flag,
                "appendix_a_definition": definitions[flag],
                "winner_n": winner_n,
                "seed_true_n": true_n,
                "seed_true_rate": float(true_n / winner_n) if winner_n else np.nan,
                "use_appendix_a_as_binding": False,
                "seed_status": "non_binding_readout_only",
                "known_issue_note": "Appendix A thresholds are priors; no archetype threshold is frozen in this run.",
            }
        )
    return pd.DataFrame(rows)


def path_coverage_audit(frame: pd.DataFrame, join_audit: dict[str, Any], config: dict[str, Any]) -> pd.DataFrame:
    rows = []
    total = int(len(frame))
    status_counts = frame["winner_path_status"].value_counts().to_dict()
    for status, count in sorted(status_counts.items()):
        rows.append(
            {
                "audit_section": "path_status_overall",
                "reporting_view": "all",
                "split": "all",
                "path_regime_state": "all",
                "status": status,
                "row_count": int(count),
                "denominator_count": total,
                "rate": float(count / total) if total else np.nan,
                "detail": "",
            }
        )
    for view in reporting_views(config):
        part = filter_view(frame, view["split"], view["path_regime_state"])
        denom = int(len(part))
        for status, count in part["winner_path_status"].value_counts().to_dict().items():
            rows.append(
                {
                    "audit_section": "path_status_by_reporting_view",
                    "reporting_view": view["reporting_view"],
                    "split": view["split"],
                    "path_regime_state": view["path_regime_state"],
                    "status": status,
                    "row_count": int(count),
                    "denominator_count": denom,
                    "rate": float(count / denom) if denom else np.nan,
                    "detail": "",
                }
            )
    for key, value in sorted(join_audit.items()):
        rows.append(
            {
                "audit_section": "join_audit",
                "reporting_view": "all",
                "split": "all",
                "path_regime_state": "all",
                "status": key,
                "row_count": int(value) if isinstance(value, (int, np.integer)) else 0,
                "denominator_count": 0,
                "rate": np.nan,
                "detail": str(value),
            }
        )
    return pd.DataFrame(rows).sort_values(["audit_section", "reporting_view", "split", "path_regime_state", "status"])


def pit_scope_row(
    *,
    audit_section: str,
    population_stage: str,
    split: str,
    path_regime_state: str,
    path_regime_source: str,
    frame: pd.DataFrame,
    pit_audit: dict[str, Any],
    pit_joined_n: int,
    pit_excluded_n: int,
    pit_excluded_denom: int,
    exclusion_reason: str,
    config: dict[str, Any],
    audit_status: str = "pass",
) -> dict[str, Any]:
    version = ""
    if "pit_membership_rule_version" in frame and len(frame):
        version = ";".join(sorted(frame["pit_membership_rule_version"].dropna().map(stable_str).unique()))
    if not version:
        version = stable_str(pit_audit.get("pit_membership_rule_version", ""))
    source = frame["path_regime_source"] if "path_regime_source" in frame else pd.Series(dtype=str)
    fallback_n = int(source.eq(PATH_REGIME_SOURCE_EVENT_FALLBACK).sum())
    unresolved_n = int(source.eq(PATH_REGIME_SOURCE_UNRESOLVED).sum())
    if "path_regime_state" in frame:
        unresolved_n = max(unresolved_n, int(frame["path_regime_state"].eq(REGIME_MISSING).sum()))
    return {
        "audit_section": audit_section,
        "population_stage": population_stage,
        "split": split,
        "path_regime_state": path_regime_state,
        "path_regime_source": path_regime_source,
        "row_count": int(len(frame)),
        "winner_n": int(len(frame)),
        "unique_instrument_n": int(frame["instrument"].nunique()) if "instrument" in frame and len(frame) else 0,
        "unique_trade_open_date_n": int(frame["trade_open_date"].nunique())
        if "trade_open_date" in frame and len(frame)
        else 0,
        "pit_universe_row_n": int(pit_audit.get("pit_universe_row_n", 0)),
        "pit_universe_unique_key_n": int(pit_audit.get("pit_universe_unique_key_n", 0)),
        "pit_universe_duplicate_key_n": int(pit_audit.get("pit_universe_duplicate_key_n", 0)),
        "pit_universe_missing_key_n": int(pit_audit.get("pit_universe_missing_key_n", 0)),
        "pit_universe_joined_n": int(pit_joined_n),
        "pit_universe_excluded_n": int(pit_excluded_n),
        "pit_universe_excluded_rate": float(pit_excluded_n / pit_excluded_denom) if pit_excluded_denom else np.nan,
        "exclusion_reason": exclusion_reason,
        "pit_universe_name": config["scope"]["pit_universe_name"],
        "pit_universe_date_key": config["scope"].get("pit_universe_date_key", "usable_trade_date"),
        "pit_membership_rule_version": version,
        "episode_regime_missing_event_fallback_n": fallback_n,
        "path_regime_unresolved_missing_n": unresolved_n,
        "audit_status": audit_status,
    }


def add_pit_population_rows(
    rows: list[dict[str, Any]],
    *,
    audit_section: str,
    population_stage: str,
    frame: pd.DataFrame,
    pit_audit: dict[str, Any],
    pit_joined_n: int,
    pit_excluded_n: int,
    pit_excluded_denom: int,
    exclusion_reason: str,
    config: dict[str, Any],
    audit_status: str = "pass",
    use_reporting_views: bool = True,
) -> None:
    if use_reporting_views and {"split", "path_regime_state"} <= set(frame.columns):
        unique_views = [
            {"split": split, "path_regime_state": regime}
            for split, regime in sorted({(view["split"], view["path_regime_state"]) for view in reporting_views(config)})
        ]
        for view in unique_views:
            part = filter_view(frame, view["split"], view["path_regime_state"])
            rows.append(
                pit_scope_row(
                    audit_section=audit_section,
                    population_stage=population_stage,
                    split=view["split"],
                    path_regime_state=view["path_regime_state"],
                    path_regime_source="all",
                    frame=part,
                    pit_audit=pit_audit,
                    pit_joined_n=pit_joined_n,
                    pit_excluded_n=pit_excluded_n,
                    pit_excluded_denom=pit_excluded_denom,
                    exclusion_reason=exclusion_reason,
                    config=config,
                    audit_status=audit_status,
                )
            )
        return

    rows.append(
        pit_scope_row(
            audit_section=audit_section,
            population_stage=population_stage,
            split="all",
            path_regime_state="all",
            path_regime_source="all",
            frame=frame,
            pit_audit=pit_audit,
            pit_joined_n=pit_joined_n,
            pit_excluded_n=pit_excluded_n,
            pit_excluded_denom=pit_excluded_denom,
            exclusion_reason=exclusion_reason,
            config=config,
            audit_status=audit_status,
        )
    )
    if "split" in frame.columns:
        for split, part in frame.groupby("split", dropna=False):
            rows.append(
                pit_scope_row(
                    audit_section=audit_section,
                    population_stage=population_stage,
                    split=stable_str(split) or "missing_split",
                    path_regime_state="all",
                    path_regime_source="all",
                    frame=part,
                    pit_audit=pit_audit,
                    pit_joined_n=pit_joined_n,
                    pit_excluded_n=pit_excluded_n,
                    pit_excluded_denom=pit_excluded_denom,
                    exclusion_reason=exclusion_reason,
                    config=config,
                    audit_status=audit_status,
                )
            )


def add_path_regime_source_rows(
    rows: list[dict[str, Any]],
    *,
    population_stage: str,
    frame: pd.DataFrame,
    pit_audit: dict[str, Any],
    pit_joined_n: int,
    pit_excluded_n: int,
    pit_excluded_denom: int,
    exclusion_reason: str,
    config: dict[str, Any],
    audit_status: str = "pass",
) -> None:
    required = {"split", "path_regime_state", "path_regime_source"}
    if frame.empty or not required <= set(frame.columns):
        return
    work = frame.copy()
    work["split"] = work["split"].map(stable_str).replace("", "missing_split")
    work["path_regime_state"] = work["path_regime_state"].map(stable_str).replace("", REGIME_MISSING)
    work["path_regime_source"] = work["path_regime_source"].map(stable_str).replace("", PATH_REGIME_SOURCE_UNRESOLVED)
    split_frames: list[tuple[str, pd.DataFrame]] = [("all", work)]
    split_frames.extend((stable_str(split) or "missing_split", part) for split, part in work.groupby("split", dropna=False))
    for split_label, split_frame in split_frames:
        for (regime, source), part in split_frame.groupby(["path_regime_state", "path_regime_source"], dropna=False):
            rows.append(
                pit_scope_row(
                    audit_section="path_regime_source_distribution",
                    population_stage=population_stage,
                    split=split_label,
                    path_regime_state=stable_str(regime) or REGIME_MISSING,
                    path_regime_source=stable_str(source) or PATH_REGIME_SOURCE_UNRESOLVED,
                    frame=part,
                    pit_audit=pit_audit,
                    pit_joined_n=pit_joined_n,
                    pit_excluded_n=pit_excluded_n,
                    pit_excluded_denom=pit_excluded_denom,
                    exclusion_reason=exclusion_reason,
                    config=config,
                    audit_status=audit_status,
                )
            )


def build_pit_universe_scope_audit(
    raw_base: pd.DataFrame,
    pit_base: pd.DataFrame,
    excluded_base: pd.DataFrame,
    pit_audit: dict[str, Any],
    injury_scope: pd.DataFrame,
    final: pd.DataFrame,
    join_audit: dict[str, Any],
    config: dict[str, Any],
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    schema_status = "pass"
    if int(pit_audit.get("pit_universe_schema_missing_column_n", 0)):
        schema_status = "schema_missing_columns"
    elif int(pit_audit.get("pit_universe_duplicate_key_n", 0)) or int(pit_audit.get("pit_universe_missing_key_n", 0)):
        schema_status = "key_failure"
    rows.append(
        pit_scope_row(
            audit_section="pit_universe_schema",
            population_stage="pit_executable_universe",
            split="all",
            path_regime_state="all",
            path_regime_source="all",
            frame=pd.DataFrame(),
            pit_audit=pit_audit,
            pit_joined_n=int(len(pit_base)),
            pit_excluded_n=int(len(excluded_base)),
            pit_excluded_denom=int(len(raw_base)),
            exclusion_reason="",
            config=config,
            audit_status=schema_status,
        )
    )
    add_pit_population_rows(
        rows,
        audit_section="profiling_scope",
        population_stage="raw_09a_winner_candidate",
        frame=raw_base,
        pit_audit=pit_audit,
        pit_joined_n=int(len(pit_base)),
        pit_excluded_n=int(len(excluded_base)),
        pit_excluded_denom=int(len(raw_base)),
        exclusion_reason="pre_pit_candidate",
        config=config,
    )
    add_path_regime_source_rows(
        rows,
        population_stage="raw_09a_winner_candidate",
        frame=raw_base,
        pit_audit=pit_audit,
        pit_joined_n=int(len(pit_base)),
        pit_excluded_n=int(len(excluded_base)),
        pit_excluded_denom=int(len(raw_base)),
        exclusion_reason="pre_pit_candidate",
        config=config,
    )
    add_pit_population_rows(
        rows,
        audit_section="profiling_scope",
        population_stage="pit_filtered_profiling_scope",
        frame=pit_base,
        pit_audit=pit_audit,
        pit_joined_n=int(len(pit_base)),
        pit_excluded_n=int(len(excluded_base)),
        pit_excluded_denom=int(len(raw_base)),
        exclusion_reason="",
        config=config,
    )
    add_path_regime_source_rows(
        rows,
        population_stage="pit_filtered_profiling_scope",
        frame=pit_base,
        pit_audit=pit_audit,
        pit_joined_n=int(len(pit_base)),
        pit_excluded_n=int(len(excluded_base)),
        pit_excluded_denom=int(len(raw_base)),
        exclusion_reason="",
        config=config,
    )
    add_pit_population_rows(
        rows,
        audit_section="profiling_scope",
        population_stage="non_pit_winner_candidate",
        frame=excluded_base,
        pit_audit=pit_audit,
        pit_joined_n=int(len(pit_base)),
        pit_excluded_n=int(len(excluded_base)),
        pit_excluded_denom=int(len(raw_base)),
        exclusion_reason="not_in_pit_executable_universe_on_trade_open_date",
        config=config,
        audit_status="excluded_non_pit",
    )
    add_path_regime_source_rows(
        rows,
        population_stage="non_pit_winner_candidate",
        frame=excluded_base,
        pit_audit=pit_audit,
        pit_joined_n=int(len(pit_base)),
        pit_excluded_n=int(len(excluded_base)),
        pit_excluded_denom=int(len(raw_base)),
        exclusion_reason="not_in_pit_executable_universe_on_trade_open_date",
        config=config,
        audit_status="excluded_non_pit",
    )

    injury_winners = injury_scope.loc[injury_scope["winner_120"].map(boolish)].copy()
    if "path_regime_state" not in injury_winners:
        injury_winners["path_regime_state"] = "all"
    injury_keys = ["sample_id", "selected_target_id", "input_denominator_id"]
    base_keys = ["sample_id", "selected_target_id", "source_denominator_id"]
    matched_injury = final.loc[final["injury_scope_flag"].map(boolish)].copy()
    injury_match = injury_winners.merge(
        pit_base[base_keys + ["profiling_row_identity", "path_regime_state"]],
        left_on=injury_keys,
        right_on=base_keys,
        how="left",
        indicator=True,
    )
    excluded_injury = injury_match.loc[injury_match["_merge"].eq("left_only")].copy()
    add_pit_population_rows(
        rows,
        audit_section="injury_scope",
        population_stage="raw_injury_scope_winner",
        frame=injury_winners,
        pit_audit=pit_audit,
        pit_joined_n=int(len(matched_injury)),
        pit_excluded_n=int(len(excluded_injury)),
        pit_excluded_denom=int(len(injury_winners)),
        exclusion_reason="pre_pit_injury_candidate",
        config=config,
        use_reporting_views=False,
    )
    add_pit_population_rows(
        rows,
        audit_section="injury_scope",
        population_stage="pit_filtered_injury_scope_winner",
        frame=matched_injury,
        pit_audit=pit_audit,
        pit_joined_n=int(join_audit.get("pit_filtered_injury_scope_winner_n", len(matched_injury))),
        pit_excluded_n=int(join_audit.get("injury_excluded_non_pit_universe_n", len(excluded_injury))),
        pit_excluded_denom=int(len(injury_winners)),
        exclusion_reason="",
        config=config,
    )
    add_path_regime_source_rows(
        rows,
        population_stage="pit_filtered_injury_scope_winner",
        frame=matched_injury,
        pit_audit=pit_audit,
        pit_joined_n=int(join_audit.get("pit_filtered_injury_scope_winner_n", len(matched_injury))),
        pit_excluded_n=int(join_audit.get("injury_excluded_non_pit_universe_n", len(excluded_injury))),
        pit_excluded_denom=int(len(injury_winners)),
        exclusion_reason="",
        config=config,
    )
    add_pit_population_rows(
        rows,
        audit_section="injury_scope",
        population_stage="injury_excluded_non_pit_universe",
        frame=excluded_injury,
        pit_audit=pit_audit,
        pit_joined_n=int(join_audit.get("pit_filtered_injury_scope_winner_n", len(matched_injury))),
        pit_excluded_n=int(join_audit.get("injury_excluded_non_pit_universe_n", len(excluded_injury))),
        pit_excluded_denom=int(len(injury_winners)),
        exclusion_reason="injury_winner_not_matched_to_pit_filtered_profiling_scope",
        config=config,
        audit_status="excluded_non_pit",
        use_reporting_views=False,
    )
    return pd.DataFrame(rows, columns=PIT_UNIVERSE_AUDIT_COLUMNS).sort_values(
        ["audit_section", "population_stage", "split", "path_regime_state"]
    )


def path_basis_reconciliation(frame: pd.DataFrame, source_cols: dict[str, set[str]], config: dict[str, Any]) -> pd.DataFrame:
    rows = []
    scalars = ["mfe_20d", "mae_20d", "mfe_60d", "mae_60d", "mfe_120d", "mae_120d"]
    tol = float(config["forward_path"]["agg_path_mismatch_tol"])
    for source, cols in source_cols.items():
        for scalar in scalars:
            if scalar not in cols:
                rows.append(
                    {
                        "source_artifact": source,
                        "aggregate_scalar": scalar,
                        "provided_flag": False,
                        "provided_row_n": 0,
                        "comparable_row_n": 0,
                        "abs_diff_mean": np.nan,
                        "abs_diff_p95": np.nan,
                        "mismatch_tol": tol,
                        "mismatch_n": 0,
                        "mismatch_rate": np.nan,
                        "blocking_flag": False,
                        "reconciliation_status": "not_provided_non_blocking",
                    }
                )
                continue
            if source == "10C_scores" and scalar == "mfe_20d":
                comparable = frame.loc[frame["tenc_mfe_20d"].notna() & frame["mfe_20_recomputed"].notna()]
                diff = (comparable["tenc_mfe_20d"] - comparable["mfe_20_recomputed"]).abs()
                mismatch_n = int((diff > tol).sum())
                rows.append(
                    {
                        "source_artifact": source,
                        "aggregate_scalar": scalar,
                        "provided_flag": True,
                        "provided_row_n": int(frame["tenc_mfe_20d"].notna().sum()),
                        "comparable_row_n": int(len(comparable)),
                        "abs_diff_mean": float(diff.mean()) if len(diff) else np.nan,
                        "abs_diff_p95": float(diff.quantile(0.95)) if len(diff) else np.nan,
                        "mismatch_tol": tol,
                        "mismatch_n": mismatch_n,
                        "mismatch_rate": float(mismatch_n / len(comparable)) if len(comparable) else np.nan,
                        "blocking_flag": False,
                        "reconciliation_status": "non_blocking_downstream_scalar_readout",
                    }
                )
            else:
                rows.append(
                    {
                        "source_artifact": source,
                        "aggregate_scalar": scalar,
                        "provided_flag": True,
                        "provided_row_n": 0,
                        "comparable_row_n": 0,
                        "abs_diff_mean": np.nan,
                        "abs_diff_p95": np.nan,
                        "mismatch_tol": tol,
                        "mismatch_n": 0,
                        "mismatch_rate": np.nan,
                        "blocking_flag": False,
                        "reconciliation_status": "provided_but_not_comparable_non_blocking",
                    }
                )
    return pd.DataFrame(rows).sort_values(["source_artifact", "aggregate_scalar"])


def top_rows(frame: pd.DataFrame, sort_col: str, n: int = 5) -> list[dict[str, Any]]:
    if frame.empty or sort_col not in frame:
        return []
    part = frame.replace([np.inf, -np.inf], np.nan).dropna(subset=[sort_col])
    return part.sort_values(sort_col, ascending=False).head(n).to_dict("records")


def build_report(
    frame: pd.DataFrame,
    distribution: pd.DataFrame,
    style: pd.DataFrame,
    injury: pd.DataFrame,
    alignment: pd.DataFrame,
    calibration: pd.DataFrame,
    decision: str,
    block_reasons: list[str],
    thresholds: Thresholds,
    join_audit: dict[str, Any],
) -> str:
    total = int(len(frame))
    raw_candidate_n = int(join_audit.get("raw_09a_winner_candidate_n", total))
    pit_excluded_n = int(join_audit.get("excluded_non_pit_winner_candidate_n", max(raw_candidate_n - total, 0)))
    pit_excluded_rate = float(join_audit.get("excluded_non_pit_winner_candidate_rate", np.nan))
    raw_injury_winner_n = int(join_audit.get("raw_injury_scope_winner_n", 0))
    pit_injury_winner_n = int(join_audit.get("pit_filtered_injury_scope_winner_n", 0))
    injury_excluded_n = int(join_audit.get("injury_excluded_non_pit_universe_n", 0))
    injury_excluded_rate = float(join_audit.get("injury_excluded_non_pit_universe_rate", np.nan))
    ok_n = int(frame["winner_path_status"].eq(PATH_OK).sum())
    coverage = ok_n / total if total else float("nan")
    parsed_rate = float(frame["day_to_target"].notna().mean()) if total else float("nan")
    basis_mismatch_rate = float(frame["winner_path_status"].eq(PATH_BASIS_MISMATCH).mean()) if total else float("nan")
    source_counts = frame["path_regime_source"].value_counts(dropna=False).to_dict() if "path_regime_source" in frame else {}
    fallback_n = int(source_counts.get(PATH_REGIME_SOURCE_EVENT_FALLBACK, 0))
    fallback_rate = float(fallback_n / total) if total else float("nan")
    unresolved_missing_n = int(source_counts.get(PATH_REGIME_SOURCE_UNRESOLVED, 0))
    all_dist = distribution.loc[
        (distribution["reporting_view"].eq("split_only"))
        & (distribution["split"].eq("all"))
        & (distribution["path_regime_state"].eq("all"))
    ]
    day_row = all_dist.loc[all_dist["metric"].eq("day_to_target")]
    dd_row = all_dist.loc[all_dist["metric"].eq("deepest_pre_target_ret_low")]
    median_day = float(day_row["p50"].iloc[0]) if not day_row.empty else np.nan
    p90_day = float(day_row["p90"].iloc[0]) if not day_row.empty else np.nan
    median_dd = float(dd_row["p50"].iloc[0]) if not dd_row.empty else np.nan
    touch_all = calibration.loc[
        (calibration["population_scope"].eq("profiling_scope"))
        & (calibration["reporting_view"].eq("split_only"))
        & (calibration["split"].eq("all"))
        & (calibration["path_regime_state"].eq("all"))
    ]
    touch_rate = float(touch_all["pre_target_touch_failure_lower_rate"].iloc[0]) if not touch_all.empty else np.nan
    inj_top = top_rows(
        injury.loc[
            injury["bucket_type"].eq("seed_flag")
            & injury["reporting_view"].eq("split_only")
            & injury["split"].eq("all")
            & injury["path_regime_state"].eq("all")
        ],
        "injury_concentration_lift",
        3,
    )
    e1_top = top_rows(
        alignment.loc[
            (alignment["alignment_target"].eq("E1_missed_winner_flag"))
            & (alignment["reporting_view"].eq("split_only"))
            & (alignment["split"].eq("all"))
        ],
        "jaccard",
        3,
    )
    bridge_top = top_rows(
        alignment.loc[
            (alignment["alignment_target"].eq("bridge_winner"))
            & (alignment["reporting_view"].eq("split_only"))
            & (alignment["split"].eq("all"))
        ],
        "jaccard",
        3,
    )
    style_top = top_rows(style.loc[style["comparison_axis"].isin(["split_vs_all", "regime_vs_all"])], "ks_statistic", 5)
    count_pivot = (
        frame.groupby(["split", "path_regime_state"], dropna=False)
        .size()
        .unstack(fill_value=0)
        .reindex(index=["train", "validation", "robustness"], fill_value=0)
        .reindex(columns=["risk_on", "risk_off", "transition"], fill_value=0)
    )
    rejected_pivot = (
        frame.loc[frame["injury_scope_flag"].map(boolish) & frame["tenc_full_keep9000_rejected_flag"].map(boolish)]
        .groupby(["split", "path_regime_state"], dropna=False)
        .size()
        .unstack(fill_value=0)
        .reindex(index=["train", "validation", "robustness"], fill_value=0)
        .reindex(columns=["risk_on", "risk_off", "transition"], fill_value=0)
    )
    split_day = distribution.loc[
        (distribution["reporting_view"].eq("split_only"))
        & (distribution["path_regime_state"].eq("all"))
        & (distribution["metric"].eq("day_to_target"))
    ][["split", "winner_n", "p50", "p90", "power_flag"]]
    regime_day = distribution.loc[
        (distribution["reporting_view"].eq("regime_only"))
        & (distribution["split"].eq("all"))
        & (distribution["metric"].eq("day_to_target"))
    ][["path_regime_state", "winner_n", "p50", "p90", "power_flag"]]

    lines = [
        "# Big Winner Path-Archetype 只读统计 Profiling 报告",
        "",
        f"decision: `{decision}`",
        "",
        "## 1. 覆盖与口径",
        "",
        f"- raw 09A winner candidate 数：{raw_candidate_n}；PIT-filtered profiling_scope winner 数：{total}；非 PIT 排除：{pit_excluded_n}（{pit_excluded_rate:.4f}）。",
        f"- raw 10A injury winner 数：{raw_injury_winner_n}；PIT-filtered injury winner 数：{pit_injury_winner_n}；injury 非 PIT 排除：{injury_excluded_n}（{injury_excluded_rate:.4f}）。",
        "- PIT universe join key：`09A.instrument + trade_open_date == pit_universe.instrument + usable_trade_date`；`instrument_metadata_target_universe.csv` 仅作 board/listing metadata，不作 universe membership。",
        f"- qfq forward path 可解析 winner 数：{ok_n}，覆盖率：{coverage:.4f}",
        f"- day_to_target parsed rate：{parsed_rate:.4f}；winner_basis_mismatch_rate：{basis_mismatch_rate:.4f}",
        f"- path_regime_state 来源：episode={int(source_counts.get(PATH_REGIME_SOURCE_EPISODE, 0))}；event fallback={fallback_n}（{fallback_rate:.4f}）；unresolved_missing={unresolved_missing_n}。",
        "- `event_regime_bucket_fallback` 只表示 source provenance，不是新的 regime；常规 regime 表只展示 `risk_on / risk_off / transition`。",
        f"- winner 阈值来自 labels.yaml：{thresholds.winner_mfe_threshold:.4f}；confirm upper：{thresholds.confirm_upper_barrier:.4f}；failure lower：{thresholds.failure_lower_barrier:.4f}",
        f"- hard_failure_first_blocks_winner = {thresholds.hard_failure_first_blocks_winner}。因此 early-shakeout 占比必须理解为在 winner 定义已先验裁掉 hard-failure-first path 之后的条件化读数。",
        "",
        "## 2. 全量 path 形态",
        "",
        f"- `day_to_target` 中位数：{median_day:.2f}，p90：{p90_day:.2f}。",
        f"- `deepest_pre_target_ret_low` 中位数：{median_dd:.4f}。",
        f"- target 前触及 failure lower barrier 的比例：{touch_rate:.4f}。",
        "",
        "## 3. Split / Regime 迁移读数",
        "",
        "split × path_regime_state winner_n：",
        "",
        "| split | risk_on | risk_off | transition |",
        "|---|---:|---:|---:|",
    ]
    for split, row in count_pivot.iterrows():
        lines.append(
            f"| {split} | {int(row['risk_on'])} | {int(row['risk_off'])} | {int(row['transition'])} |"
        )
    lines.extend(["", "split-only `day_to_target`：", ""])
    for row in split_day.itertuples(index=False):
        lines.append(f"- {row.split}: winner_n={int(row.winner_n)}，p50={row.p50:.2f}，p90={row.p90:.2f}，power={row.power_flag}。")
    lines.extend(["", "regime-only `day_to_target`：", ""])
    for row in regime_day.itertuples(index=False):
        lines.append(
            f"- {row.path_regime_state}: winner_n={int(row.winner_n)}，p50={row.p50:.2f}，p90={row.p90:.2f}，power={row.power_flag}。"
        )
    lines.extend(["", "最大 KS 读数："])
    if style_top:
        for row in style_top:
            lines.append(
                f"- {row['comparison_id']} / {row['metric']}：KS={row['ks_statistic']:.4f}，n={row['non_null_metric_n']}，power={row['power_flag']}。"
            )
    else:
        lines.append("- 无可排序迁移读数。")
    lines.extend(
        [
            "",
            "低样本 split × regime cell 只作为观察，不能解释为结构性迁移结论。",
            "",
            "## 4. Seed 假设与 10C injury",
            "",
            "Appendix A seed flags 是 non-binding 对照，不是冻结 archetype，也不能进入 t0 entry/rejector predictor。",
        ]
    )
    lines.extend(
        [
            "",
            "10C rejected injury winner_n by split × path_regime_state：",
            "",
            "| split | risk_on | risk_off | transition |",
            "|---|---:|---:|---:|",
        ]
    )
    for split, row in rejected_pivot.iterrows():
        lines.append(
            f"| {split} | {int(row['risk_on'])} | {int(row['risk_off'])} | {int(row['transition'])} |"
        )
    if inj_top:
        for row in inj_top:
            lines.append(
                f"- {row['bucket_name']}：injury lift={row['injury_concentration_lift']:.4f}，bucket winner n={row['winner_n']}，injured n={row['injured_winner_n']}。"
            )
    else:
        lines.append("- 无可排序 injury concentration 读数。")
    lines.extend(["", "## 5. E1 / Bridge 对齐", ""])
    if e1_top:
        for row in e1_top:
            lines.append(
                f"- {row['bucket_name']} × E1_missed：Jaccard={row['jaccard']:.4f}，P(E1|bucket)={row['p_target_given_bucket']:.4f}，n={row['winner_n']}。"
            )
    else:
        lines.append("- 无可排序 E1 对齐读数。")
    if bridge_top:
        for row in bridge_top:
            lines.append(
                f"- {row['bucket_name']} × bridge_winner：Jaccard={row['jaccard']:.4f}，P(bridge|bucket)={row['p_target_given_bucket']:.4f}，n={row['winner_n']}。"
            )
    lines.extend(
        [
            "",
            "## 6. 结论边界",
            "",
            "- 本阶段只完成 winner path profiling 与 injury concentration readout，不产出 supported gate、不冻结 archetype v1。",
            "- qfq daily bars 是逐日 path 权威来源；10C `mfe_20d` 仅作为 non-blocking 标量对账。",
            "- 后续若要进入 10D / Gate-0 或 exit-layer 设计，应先基于这些表单独冻结 winner-safe label / bucket 定义，再讨论可见时点与 leakage 边界。",
        ]
    )
    if block_reasons:
        lines.extend(["", "## 7. Block / Incomplete Reasons", ""])
        lines.extend([f"- {reason}" for reason in block_reasons])
    return "\n".join(lines) + "\n"


def build_manifest(
    config: dict[str, Any],
    paths: dict[str, Path],
    outputs: dict[str, Path],
    qfq_used_hashes: dict[str, str],
    decision: str,
    frame: pd.DataFrame,
    thresholds: Thresholds,
    join_audit: dict[str, Any],
    input_failures: list[str],
    block_reasons: list[str],
    style: pd.DataFrame,
    injury: pd.DataFrame,
    alignment: pd.DataFrame,
) -> dict[str, Any]:
    publishable = {
        key: path
        for key, path in outputs.items()
        if key not in {"manifest", "winner_path_metrics"} and path.is_file()
    }
    local_cache = {key: path for key, path in outputs.items() if key == "winner_path_metrics" and path.is_file()}
    total = int(len(frame))
    ok_n = int(frame["winner_path_status"].eq(PATH_OK).sum())
    injury_scope = frame.loc[frame["injury_scope_flag"].map(boolish)]
    path_regime_source_counts = (
        {stable_str(key): int(value) for key, value in frame["path_regime_source"].value_counts(dropna=False).to_dict().items()}
        if "path_regime_source" in frame
        else {}
    )
    fallback_n = int(path_regime_source_counts.get(PATH_REGIME_SOURCE_EVENT_FALLBACK, 0))
    unresolved_missing_n = int(path_regime_source_counts.get(PATH_REGIME_SOURCE_UNRESOLVED, 0))
    style_top = top_rows(style.loc[style["comparison_axis"].isin(["split_vs_all", "regime_vs_all"])], "ks_statistic", 5)
    injury_top = top_rows(injury, "injury_concentration_lift", 5)
    e1_rows = alignment.loc[alignment["alignment_target"].eq("E1_missed_winner_flag")]
    return {
        "component_id": "big_winner_archetype_profiling",
        "decision": decision,
        "profiling_population": config["scope"]["profiling_population"],
        "pit_universe_name": config["scope"]["pit_universe_name"],
        "pit_universe_source_path": str(paths["pit_executable_universe"]),
        "pit_universe_hash": hash_or_empty(paths["pit_executable_universe"]),
        "pit_universe_join_key": config["scope"].get("pit_universe_join_key", ["instrument", "usable_trade_date"]),
        "pit_universe_date_key": config["scope"].get("pit_universe_date_key", "usable_trade_date"),
        "pit_universe_filter_policy": config["scope"].get(
            "pit_universe_filter_policy",
            "require_instrument_trade_open_date_in_executable_universe",
        ),
        "injury_non_pit_policy": config["scope"].get("injury_non_pit_policy", "exclude_from_main_readout_and_audit"),
        "raw_09a_winner_candidate_n": int(join_audit.get("raw_09a_winner_candidate_n", total)),
        "profiling_scope_winner_n": total,
        "pit_filtered_profiling_scope_winner_n": total,
        "excluded_non_pit_winner_candidate_n": int(
            join_audit.get("excluded_non_pit_winner_candidate_n", max(int(join_audit.get("raw_09a_winner_candidate_n", total)) - total, 0))
        ),
        "excluded_non_pit_winner_candidate_rate": float(
            join_audit.get("excluded_non_pit_winner_candidate_rate", np.nan)
        ),
        "raw_injury_scope_winner_n": int(join_audit.get("raw_injury_scope_winner_n", 0)),
        "injury_scope_winner_n": int(len(injury_scope)),
        "pit_filtered_injury_scope_winner_n": int(join_audit.get("pit_filtered_injury_scope_winner_n", len(injury_scope))),
        "excluded_injury_non_pit_winner_n": int(join_audit.get("injury_excluded_non_pit_universe_n", 0)),
        "excluded_injury_non_pit_winner_rate": float(join_audit.get("injury_excluded_non_pit_universe_rate", np.nan)),
        "path_coverage_rate": float(ok_n / total) if total else np.nan,
        "split_levels": config["distribution_audit"]["split_levels"],
        "path_regime_levels": config["distribution_audit"]["path_regime_levels"],
        "regime_state_source": config["distribution_audit"].get("regime_state_source", ""),
        "regime_source_precedence": config["distribution_audit"].get(
            "regime_source_precedence", ["episode_regime_bucket", "event_regime_bucket"]
        ),
        "episode_regime_missing_policy": config["distribution_audit"].get("episode_regime_missing_policy", ""),
        "residual_regime_missing_policy": config["distribution_audit"].get("residual_regime_missing_policy", ""),
        "episode_regime_missing_event_fallback_n": fallback_n,
        "episode_regime_missing_event_fallback_rate": float(fallback_n / total) if total else np.nan,
        "path_regime_source_counts": path_regime_source_counts,
        "path_regime_unresolved_missing_n": unresolved_missing_n,
        "style_migration_summary": style_top,
        "regime_migration_summary": [
            row for row in style_top if row.get("comparison_axis") in {"regime_vs_all", "regime_pairwise"}
        ],
        "winner_basis_mismatch_rate": float(frame["winner_path_status"].eq(PATH_BASIS_MISMATCH).sum() / total)
        if total
        else np.nan,
        "hard_failure_conditioning_summary": {
            "pre_target_touch_failure_lower_n": int(frame["pre_target_touch_failure_lower_flag"].map(boolish).sum()),
            "pre_target_close_drawdown_failure_proxy_n": int(
                frame["pre_target_close_drawdown_failure_proxy_flag"].map(boolish).sum()
            ),
        },
        "injury_scope_day_to_target_parsed_rate": float(injury_scope["day_to_target"].notna().mean())
        if len(injury_scope)
        else np.nan,
        "top_injury_concentration_buckets": injury_top,
        "injury_concentration_lift_by_split": top_rows(injury.loc[injury["reporting_view"].eq("split_only")], "injury_concentration_lift", 10),
        "injury_concentration_lift_by_regime": top_rows(
            injury.loc[injury["reporting_view"].eq("regime_only")], "injury_concentration_lift", 10
        ),
        "bucket_e1_jaccard_by_split": top_rows(e1_rows.loc[e1_rows["reporting_view"].eq("split_only")], "jaccard", 10),
        "bucket_e1_jaccard_by_regime": top_rows(e1_rows.loc[e1_rows["reporting_view"].eq("regime_only")], "jaccard", 10),
        "winner_mfe_threshold": thresholds.winner_mfe_threshold,
        "confirm_upper_barrier": thresholds.confirm_upper_barrier,
        "failure_lower_barrier": thresholds.failure_lower_barrier,
        "failure_max_drawdown": thresholds.failure_max_drawdown,
        "close_based_drawdown_policy": thresholds.close_based_drawdown_policy,
        "hard_failure_first_blocks_winner": thresholds.hard_failure_first_blocks_winner,
        "forward_path_source_dir": str(paths["qfq_dir"]),
        "forward_session_alignment": "d=1 is first trading session strictly after trade_open_date; trade_open_price is qfq open on trade_open_date",
        "fallback_forward_path_source_dir": str(paths["qfq_fallback_dir"]),
        "board_metadata_source": str(paths["board_metadata"]),
        "st_status_source_summary": frame["st_status_source"].value_counts(dropna=False).to_dict(),
        "board_limit_proxy": config["board_limit_proxy"],
        "input_hashes": {
            **{key: hash_or_empty(path) for key, path in paths.items() if path.is_file()},
            "qfq_used_files_hash": directory_hash([REPO_ROOT / rel for rel in qfq_used_hashes]),
        },
        "qfq_used_file_count": len(qfq_used_hashes),
        "qfq_used_file_hashes": qfq_used_hashes,
        "config_hash": stable_hash(config),
        "config_file_hash": file_sha256(CONFIG_PATH),
        "publishable_table_hashes": {key: file_sha256(path) for key, path in publishable.items()},
        "local_cache_hashes": {key: file_sha256(path) for key, path in local_cache.items()},
        "input_failures": input_failures,
        "decision_block_reasons": block_reasons,
        "join_audit": join_audit,
        "requirement_hash": file_sha256(REQUIREMENT_PATH),
        "git_revision": git_revision(),
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "python_version": platform.python_version(),
        "numpy_version": np.__version__,
        "pandas_version": pd.__version__,
    }


def determine_decision(
    frame: pd.DataFrame,
    config: dict[str, Any],
    failures: list[str],
    produced_outputs: dict[str, Path],
) -> tuple[str, list[str]]:
    block_reasons: list[str] = []
    incomplete_reasons: list[str] = []
    total = int(len(frame))
    coverage = float(frame["winner_path_status"].eq(PATH_OK).sum() / total) if total else 0.0
    if failures:
        block_reasons.extend(failures)
    if coverage < float(config["forward_path"]["min_path_coverage"]):
        block_reasons.append(f"path_coverage_below_min:{coverage:.6f}")
    required_output_keys = [
        "input_artifact_audit",
        "pit_universe_scope_audit",
        "path_coverage_audit",
        "path_basis_reconciliation_audit",
        "hard_failure_conditioning_calibration",
        "path_metric_distribution",
        "path_metric_correlation",
        "path_metric_histogram",
        "path_style_migration_readout",
        "seed_hypothesis_readout",
        "seed_flag_overlap_by_reporting_view",
        "injury_concentration_by_bucket",
        "bucket_e1_alignment_2x2",
        "seed_hypothesis_comparison",
        "winner_path_metrics",
    ]
    missing_outputs = [key for key in required_output_keys if not produced_outputs.get(key, Path()).is_file()]
    if missing_outputs:
        block_reasons.append(f"missing_outputs:{','.join(missing_outputs)}")
    if "path_regime_source" in frame:
        unresolved_missing_n = int(frame["path_regime_source"].eq(PATH_REGIME_SOURCE_UNRESOLVED).sum())
    else:
        unresolved_missing_n = int(frame["path_regime_state"].eq(REGIME_MISSING).sum()) if "path_regime_state" in frame else 0
    if unresolved_missing_n:
        incomplete_reasons.append(f"path_regime_unresolved_missing:{unresolved_missing_n}")
    if block_reasons:
        return DECISION_INPUT_BLOCKED, block_reasons + incomplete_reasons
    if incomplete_reasons:
        return DECISION_INCOMPLETE, incomplete_reasons
    return DECISION_COMPLETE, []


def run(config_path: Path = CONFIG_PATH) -> dict[str, Any]:
    config = load_yaml(config_path)
    paths = {key: resolve_path(value) for key, value in config["paths"].items()}
    labels = load_yaml(paths["labels_config"])
    thresholds = read_thresholds(labels)

    pit_universe, pit_universe_audit, pit_universe_failures = load_pit_universe(paths["pit_executable_universe"], config)
    raw_base, base_audit, base_failures = load_winner_base(paths["upstream_09a_bindings"], config)
    base, excluded_base, pit_filter_audit, pit_filter_failures = apply_pit_universe_filter(
        raw_base,
        pit_universe,
        config,
    )
    injury_scope, injury_audit, injury_failures = load_injury_scope(paths["upstream_10a_bindings"], config)
    tenc_ref, tenc_audit, tenc_failures = load_10c_reference(paths["upstream_10c_scores"], config)

    with_paths, qfq_used_hashes, path_audit = add_path_metrics(base, paths, config, thresholds)
    merged, join_audit, join_failures = join_injury_and_10c(with_paths, injury_scope, tenc_ref)
    final = add_seed_flags(merged, thresholds, config)
    for col in WINNER_PATH_METRIC_COLUMNS:
        if col not in final.columns:
            final[col] = pd.NA
    final = final[WINNER_PATH_METRIC_COLUMNS].sort_values("profiling_row_identity").reset_index(drop=True)

    source_cols = {
        "09A_selected_label_event_bindings": set(pd.read_parquet(paths["upstream_09a_bindings"]).columns),
        "10A_post_dedup_event_bindings": set(pd.read_parquet(paths["upstream_10a_bindings"]).columns),
        "10C_scores": set(pd.read_parquet(paths["upstream_10c_scores"]).columns),
    }

    schema_status = {
        "pit_executable_universe": "pass" if not pit_universe_failures else "schema_or_key_failure",
        "upstream_09a_bindings": "pass" if not base_failures else "schema_or_key_failure",
        "upstream_10a_bindings": "pass" if not injury_failures else "schema_or_key_failure",
        "upstream_10c_scores": "pass" if not tenc_failures else "schema_or_key_failure",
        "labels_config": "pass",
        "qfq_dir": "pass",
        "qfq_fallback_dir": "fallback_available" if paths["qfq_fallback_dir"].exists() else "optional_missing",
        "board_metadata": "pass",
        "sh_name_history_dir": "optional_st_history_without_date",
        "sz_name_history": "optional_st_history",
    }
    input_audit_df = input_audit(paths, schema_status)
    qfq_aggregate_row = pd.DataFrame(
        [
            {
                "artifact_id": "qfq_used_files",
                "relative_path": "topics/02_AFML_BIG_WINNER/data/raw/akshare/day/qfq/{instrument}.csv",
                "resolved_path": str(paths["qfq_dir"]),
                "required_flag": True,
                "exists_flag": True,
                "content_hash": directory_hash([REPO_ROOT / rel for rel in qfq_used_hashes]),
                "file_size_bytes": len(qfq_used_hashes),
                "mtime_utc": "",
                "schema_status": "pass",
                "row_count": len(qfq_used_hashes),
                "failure_reason": "",
            }
        ]
    )
    input_audit_df = pd.concat([input_audit_df, qfq_aggregate_row], ignore_index=True)

    join_audit_all = {
        **base_audit,
        **pit_universe_audit,
        **pit_filter_audit,
        **injury_audit,
        **tenc_audit,
        **path_audit,
        **join_audit,
    }
    join_audit_all.update(
        {
            "episode_regime_missing_event_fallback_n": int(
                final["path_regime_source"].eq(PATH_REGIME_SOURCE_EVENT_FALLBACK).sum()
            ),
            "episode_regime_missing_event_fallback_rate": float(
                final["path_regime_source"].eq(PATH_REGIME_SOURCE_EVENT_FALLBACK).mean()
            )
            if len(final)
            else np.nan,
            "path_regime_unresolved_missing_n": int(final["path_regime_source"].eq(PATH_REGIME_SOURCE_UNRESOLVED).sum()),
            "path_regime_source_counts": final["path_regime_source"].value_counts(dropna=False).to_dict(),
        }
    )
    failures = (
        pit_universe_failures
        + base_failures
        + pit_filter_failures
        + injury_failures
        + tenc_failures
        + join_failures
    )

    OUTPUT_TABLE_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_LOCAL_CACHE_DIR.mkdir(parents=True, exist_ok=True)

    outputs = {
        "input_artifact_audit": OUTPUT_TABLE_DIR / "input_artifact_audit.csv",
        "pit_universe_scope_audit": OUTPUT_TABLE_DIR / "pit_universe_scope_audit.csv",
        "path_coverage_audit": OUTPUT_TABLE_DIR / "path_coverage_audit.csv",
        "path_basis_reconciliation_audit": OUTPUT_TABLE_DIR / "path_basis_reconciliation_audit.csv",
        "hard_failure_conditioning_calibration": OUTPUT_TABLE_DIR / "hard_failure_conditioning_calibration.csv",
        "path_metric_distribution": OUTPUT_TABLE_DIR / "path_metric_distribution.csv",
        "path_metric_correlation": OUTPUT_TABLE_DIR / "path_metric_correlation.csv",
        "path_metric_histogram": OUTPUT_TABLE_DIR / "path_metric_histogram.csv",
        "path_style_migration_readout": OUTPUT_TABLE_DIR / "path_style_migration_readout.csv",
        "seed_hypothesis_readout": OUTPUT_TABLE_DIR / "seed_hypothesis_readout.csv",
        "seed_flag_overlap_by_reporting_view": OUTPUT_TABLE_DIR / "seed_flag_overlap_by_reporting_view.csv",
        "injury_concentration_by_bucket": OUTPUT_TABLE_DIR / "injury_concentration_by_bucket.csv",
        "bucket_e1_alignment_2x2": OUTPUT_TABLE_DIR / "bucket_e1_alignment_2x2.csv",
        "seed_hypothesis_comparison": OUTPUT_TABLE_DIR / "seed_hypothesis_comparison.csv",
        "winner_path_metrics": OUTPUT_LOCAL_CACHE_DIR / "winner_path_metrics.parquet",
        "report": OUTPUT_REPORT,
        "manifest": OUTPUT_MANIFEST,
    }

    final.to_parquet(outputs["winner_path_metrics"], index=False)
    write_df(outputs["input_artifact_audit"], input_audit_df)
    pit_scope_audit = build_pit_universe_scope_audit(
        raw_base,
        base,
        excluded_base,
        pit_universe_audit,
        injury_scope,
        final,
        join_audit_all,
        config,
    )
    coverage = path_coverage_audit(final, join_audit_all, config)
    reconciliation = path_basis_reconciliation(final, source_cols, config)
    calibration = hard_failure_calibration(final, config)
    distribution = metric_distribution(final, config)
    correlation = metric_correlation(final, config)
    histogram = histogram_table(final, config)
    style = style_migration(final, config)
    seed_readout = seed_hypothesis_readout(final, config)
    overlap = seed_overlap(final, config)
    injury_conc = injury_concentration(final, config)
    alignment = bucket_alignment_2x2(final, config)
    seed_comparison = seed_hypothesis_comparison(final)

    write_df(outputs["pit_universe_scope_audit"], pit_scope_audit)
    write_df(outputs["path_coverage_audit"], coverage)
    write_df(outputs["path_basis_reconciliation_audit"], reconciliation)
    write_df(outputs["hard_failure_conditioning_calibration"], calibration)
    write_df(outputs["path_metric_distribution"], distribution)
    write_df(outputs["path_metric_correlation"], correlation)
    write_df(outputs["path_metric_histogram"], histogram)
    write_df(outputs["path_style_migration_readout"], style)
    write_df(outputs["seed_hypothesis_readout"], seed_readout)
    write_df(outputs["seed_flag_overlap_by_reporting_view"], overlap)
    write_df(outputs["injury_concentration_by_bucket"], injury_conc)
    write_df(outputs["bucket_e1_alignment_2x2"], alignment)
    write_df(outputs["seed_hypothesis_comparison"], seed_comparison)

    decision, block_reasons = determine_decision(final, config, failures, outputs)
    report = build_report(
        final,
        distribution,
        style,
        injury_conc,
        alignment,
        calibration,
        decision,
        block_reasons,
        thresholds,
        join_audit_all,
    )
    write_text(outputs["report"], report)

    manifest = build_manifest(
        config,
        paths,
        outputs,
        qfq_used_hashes,
        decision,
        final,
        thresholds,
        join_audit_all,
        failures,
        block_reasons,
        style,
        injury_conc,
        alignment,
    )
    write_json(outputs["manifest"], manifest)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Run big-winner path archetype profiling.")
    parser.add_argument("--config", type=Path, default=CONFIG_PATH)
    args = parser.parse_args()
    manifest = run(args.config)
    print(json.dumps({"decision": manifest["decision"], "path_coverage_rate": manifest["path_coverage_rate"]}, indent=2))


if __name__ == "__main__":
    main()
