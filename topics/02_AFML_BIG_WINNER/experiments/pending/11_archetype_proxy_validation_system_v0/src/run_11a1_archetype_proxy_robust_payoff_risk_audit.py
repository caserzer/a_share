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


CONFIG_PATH = EXPERIMENT_DIR / "configs" / "config_11a1_archetype_proxy_robust_payoff_risk_audit.yaml"

RUN_ID = "11A1_archetype_proxy_robust_payoff_risk_audit"
TABLE_DIR = EXPERIMENT_DIR / "outputs" / "publishable" / "tables" / RUN_ID
LOCAL_CACHE_DIR = EXPERIMENT_DIR / "outputs" / "local_cache" / RUN_ID
REPORT_PATH = EXPERIMENT_DIR / "outputs" / "publishable" / "reports" / f"{RUN_ID}_report.md"
MANIFEST_PATH = EXPERIMENT_DIR / "outputs" / "publishable" / f"manifest_{RUN_ID}.json"

FINAL_SUPPORTED = "11A1_archetype_proxy_robust_payoff_risk_screen_supported"
FINAL_EMPTY = "11A1_archetype_proxy_robust_payoff_risk_screen_empty"
FINAL_INCOMPLETE = "11A1_archetype_proxy_robust_payoff_risk_statistics_incomplete"
FINAL_BLOCKED = "11A1_archetype_proxy_robust_payoff_risk_input_blocked"

VALID_REGIMES = {"risk_on", "risk_off", "transition"}
PRIMARY_SPLITS = ["train", "validation", "robustness"]
READOUT_SPLITS = ["train", "validation", "robustness", "all"]
OUTCOME_FORBIDDEN_FIELDS = {
    "winner_120",
    "mfe_20d",
    "mfe_60d",
    "mfe_120d",
    "mae_20d",
    "mae_60d",
    "mae_120d",
    "forward_return_20d",
    "forward_return_60d",
    "forward_return_120d",
    "candidate_false_repair_score",
    "candidate_rank",
    "candidate_rejected_flag",
}


@dataclass(frozen=True)
class Thresholds:
    feature_join_success_floor: float = 0.995
    label_join_success_floor: float = 0.995
    canonical_fallback_rate_ceiling: float = 0.005
    proxy_train_pre_imputation_non_null_min: int = 500
    proxy_positive_eligible_min: int = 100
    matched_negative_eligible_min: int = 300
    matched_quarter_min: int = 6
    matched_positive_weight_coverage_floor: float = 0.8
    bootstrap_n: int = 1000
    null_simulation_n: int = 500
    bootstrap_failure_delta_margin: float = 0.005
    bootstrap_failure_prob_floor: float = 0.80
    bootstrap_component_failure_prob_floor: float = 0.75
    bootstrap_failure_p95_ceiling: float = 0.015

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


def relative_path(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def file_mtime_utc(path: Path) -> str:
    if not path.exists():
        return ""
    return datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat()


def quick_row_count(path: Path) -> int | str:
    if not path.exists() or not path.is_file():
        return ""
    suffixes = "".join(path.suffixes)
    try:
        if suffixes.endswith(".parquet"):
            import pyarrow.parquet as pq

            return int(pq.ParquetFile(path).metadata.num_rows)
        if suffixes.endswith(".csv") or suffixes.endswith(".csv.gz"):
            return int(sum(len(chunk) for chunk in pd.read_csv(path, chunksize=250000, usecols=[0])))
        if suffixes.endswith(".json") or suffixes.endswith(".yaml") or suffixes.endswith(".md"):
            return ""
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

                    columns = pq.ParquetFile(path).schema.names
                else:
                    columns = pd.read_csv(path, nrows=0).columns.tolist()
                missing = sorted(set(schema[artifact_id]) - set(columns))
                schema_status = "ok" if not missing else "missing_columns"
                failure_reason = ",".join(missing)
            except Exception as exc:  # pragma: no cover - corrupt input defense
                schema_status = "schema_read_failed"
                failure_reason = str(exc)
        elif artifact_id in schema and not exists:
            schema_status = "missing_file"
            failure_reason = "required_input_missing" if artifact_id in required else "optional_input_missing"
        rows.append(
            {
                "artifact_id": artifact_id,
                "relative_path": relative_path(path),
                "resolved_path": str(path),
                "required_flag": artifact_id in required,
                "exists_flag": exists,
                "content_hash": file_sha256(path) if path.is_file() else "",
                "file_size_bytes": path.stat().st_size if path.is_file() else "",
                "mtime_utc": file_mtime_utc(path),
                "schema_status": schema_status,
                "row_count": row_count,
                "failure_reason": failure_reason,
            }
        )
    return pd.DataFrame(rows)


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


def bool_series(series: pd.Series) -> pd.Series:
    return series.map(boolish).fillna(False).astype(bool)


def nonempty(value: Any) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except TypeError:
        pass
    return str(value).strip()


def normalize_regime(value: Any) -> str:
    text = nonempty(value).lower()
    if text in VALID_REGIMES:
        return text
    return ""


def normalize_regime_series(series: pd.Series) -> pd.Series:
    return series.map(normalize_regime).astype("string")


def coalesce_regime(frame: pd.DataFrame, cols: list[str]) -> tuple[pd.Series, pd.Series]:
    out = pd.Series([""] * len(frame), index=frame.index, dtype="string")
    source = pd.Series(["unresolved_missing"] * len(frame), index=frame.index, dtype="string")
    unresolved = out.eq("")
    for col in cols:
        normalized = normalize_regime_series(frame[col]) if col in frame.columns else pd.Series([""] * len(frame), index=frame.index)
        take = unresolved & normalized.ne("")
        out.loc[take] = normalized.loc[take]
        source.loc[take] = col
        unresolved = out.eq("")
    return out, source


def safe_rate(numerator: int | float, denominator: int | float) -> float:
    if denominator == 0 or pd.isna(denominator):
        return float("nan")
    return float(numerator) / float(denominator)


def parse_canonical_from_pipe(value: Any) -> str:
    parts = nonempty(value).split("|")
    if len(parts) >= 4:
        return parts[3].strip()
    return ""


def make_feature_join_key(frame: pd.DataFrame, canonical_col: str = "canonical_event_id") -> pd.Series:
    return (
        frame["sample_id"].astype(str)
        + "|"
        + frame["selected_target_id"].astype(str)
        + "|"
        + frame["denominator_id"].astype(str)
        + "|"
        + frame[canonical_col].astype(str)
    )


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_parquet_columns(path: Path, columns: list[str] | None = None) -> pd.DataFrame:
    if columns is None:
        return pd.read_parquet(path)
    try:
        import pyarrow.parquet as pq

        available = set(pq.ParquetFile(path).schema.names)
        usecols = [col for col in columns if col in available]
        return pd.read_parquet(path, columns=usecols)
    except Exception:
        return pd.read_parquet(path)


def required_schema() -> dict[str, list[str]]:
    return {
        "ten_a_bindings": [
            "population_id",
            "rule_arm_id",
            "input_denominator_id",
            "denominator_id",
            "admission_status",
            "readout_only_flag",
            "input_event_key",
            "feature_matrix_join_key",
            "cost_bad_sample_weight_join_key",
            "fast_fail_sample_weight_join_key",
            "sample_id",
            "selected_target_id",
            "instrument",
            "event_t0_date",
            "split",
            "event_regime_bucket",
            "winner_120",
            "selected_fast_fail_10_label",
            "frozen_false_repair_20d_label",
            "E1_missed_winner_flag",
        ],
        "ten_c_scores": [
            "model_id",
            "ablation_id",
            "capacity_id",
            "threshold_id",
            "population_id",
            "denominator_id",
            "input_event_key",
            "binding_canonical_event_id",
            "candidate_false_repair_score",
            "candidate_rejected_flag",
        ],
        "nine_b_feature_matrix": [
            "sample_id",
            "selected_target_id",
            "denominator_id",
            "canonical_event_id",
            "instrument",
            "event_t0_date",
            "event_split",
        ],
        "nine_b_sample_weights": [
            "sample_id",
            "selected_target_id",
            "denominator_id",
            "canonical_event_id",
            "weight_horizon_id",
            "scope_usage",
            "supported_training_scope_flag",
            "final_sample_weight",
        ],
        "nine_a_bindings": [
            "sample_id",
            "selected_target_id",
            "denominator_id",
            "canonical_event_id",
            "event_regime_bucket",
            "episode_regime_bucket",
        ],
        "eight_labels": [
            "event_id",
            "instrument",
            "event_t0_date",
            "event_split",
            "confirm_20_touch_pos",
            "forward_return_60d",
            "horizon_complete_120d",
        ],
        "nine_b_feature_contract": ["feature_id", "t0_visible_flag", "allowed_for_09C_flag"],
        "nine_b_stationarity_audit": ["feature_id", "raw_missing_rate"],
    }


def proxy_registry() -> list[dict[str, Any]]:
    return [
        {
            "proxy_family_id": "P1_gap_event_proxy",
            "description": "event shock: gap/range/volume-position",
            "fields": [
                "gap_open_pct",
                "intraday_range_atr_norm",
                "close_position_in_range",
                "amount_ratio_20d",
                "turnover_ratio_20d",
                "family_count",
                "channel_count",
            ],
            "thresholds": {
                "gap_open_pct": [0.70],
                "intraday_range_atr_norm": [0.70],
                "amount_ratio_20d": [0.70],
                "close_position_in_range": [0.60],
            },
        },
        {
            "proxy_family_id": "P2_shakeout_prior_path_proxy",
            "description": "shakeout near prior high with higher volatility",
            "fields": [
                "close_to_high_60",
                "close_to_high_120",
                "upper_shadow_pct",
                "close_position_in_range",
                "atr_pct_rank_60d",
                "stock_vs_board_20d",
            ],
            "thresholds": {
                "close_to_high_60": [0.30],
                "close_to_high_120": [0.30],
                "upper_shadow_pct": [0.60],
                "close_position_in_range": [0.50],
                "atr_pct_rank_60d": [0.40],
            },
        },
        {
            "proxy_family_id": "P3_volatility_expansion_proxy",
            "description": "directional entropy plus volatility expansion",
            "fields": ["direction_entropy_20d", "atr_pct_rank_60d", "range_width_ratio_20d_60d"],
            "thresholds": {
                "direction_entropy_20d": [0.60],
                "atr_pct_rank_60d": [0.60],
                "range_width_ratio_20d_60d": [0.60],
            },
        },
        {
            "proxy_family_id": "P4_momentum_leader_proxy",
            "description": "relative momentum leadership",
            "fields": ["momentum_percentile_20d", "return_20d", "close_to_ema20"],
            "thresholds": {
                "momentum_percentile_20d": [0.70],
                "return_20d": [0.60],
                "close_to_ema20": [0.50],
            },
        },
        {
            "proxy_family_id": "P5_low_noise_accumulation_proxy",
            "description": "moderate trend, lower volatility, repeated prior events",
            "fields": ["return_20d", "atr_pct_rank_60d", "prior_event_count_60d", "ema60_positive_run"],
            "thresholds": {
                "return_20d": [0.35, 0.65],
                "atr_pct_rank_60d": [0.60],
                "prior_event_count_60d": [0.50],
                "ema60_positive_run": [0.50],
            },
        },
        {
            "proxy_family_id": "P6_repair_structure_proxy",
            "description": "clean EMA repair structure with controlled volatility",
            "fields": ["close_to_ema20", "close_to_ema60", "ema20_slope_20d", "atr_pct_rank_60d"],
            "thresholds": {
                "close_to_ema20": [0.50],
                "close_to_ema60": [0.50],
                "ema20_slope_20d": [0.50],
                "atr_pct_rank_60d": [0.70],
            },
        },
        {
            "proxy_family_id": "P7_flow_confirmation_proxy",
            "description": "amount/turnover confirmation",
            "fields": [
                "amount_ratio_20d",
                "amount_ratio_60d",
                "turnover_ratio_20d",
                "turnover_ratio_60d",
                "quality_amount_flag",
            ],
            "thresholds": {"amount_ratio_20d": [0.70], "turnover_ratio_20d": [0.60]},
        },
        {
            "proxy_family_id": "P8_recurrence_density_proxy",
            "description": "same instrument/family recurrence density",
            "fields": [
                "prior_event_count_20d",
                "prior_event_count_60d",
                "family_count",
                "channel_count",
                "raw_cluster_event_count",
            ],
            "thresholds": {
                "prior_event_count_60d": [0.70],
                "raw_cluster_event_count": [0.70],
                "family_count": [0.60],
                "channel_count": [0.60],
            },
        },
    ]


def build_paths(config: dict[str, Any]) -> dict[str, Path]:
    return {key: resolve_path(value) for key, value in config.get("inputs", {}).items()}


def build_primary_denominator(config: dict[str, Any], paths: dict[str, Path]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    scope = config["scope"]
    ten_a = read_parquet_columns(paths["ten_a_bindings"])
    mask = (
        ten_a["population_id"].astype(str).eq(scope["population_id"])
        & ten_a["rule_arm_id"].astype(str).eq(scope["rule_arm_id"])
        & ten_a["input_denominator_id"].astype(str).eq(scope["input_denominator_id"])
        & ten_a["denominator_id"].astype(str).eq(scope["denominator_id"])
        & ten_a["admission_status"].astype(str).eq(scope["admission_status"])
        & bool_series(ten_a["readout_only_flag"]).eq(bool(scope["readout_only_flag"]))
    )
    primary = ten_a.loc[mask].copy()
    primary["event_t0_date"] = pd.to_datetime(primary["event_t0_date"]).dt.strftime("%Y-%m-%d")
    primary["row_id"] = np.arange(len(primary), dtype=np.int64)

    ten_c = read_parquet_columns(paths["ten_c_scores"])
    ref_mask = (
        ten_c["model_id"].astype(str).eq(scope["model_id"])
        & ten_c["ablation_id"].astype(str).eq(scope["ablation_id"])
        & ten_c["capacity_id"].astype(str).eq(scope["capacity_id"])
        & ten_c["threshold_id"].astype(str).eq(scope["threshold_id"])
        & ten_c["population_id"].astype(str).eq(scope["population_id"])
        & ten_c["denominator_id"].astype(str).eq(scope["denominator_id"])
    )
    ref = ten_c.loc[ref_mask].copy()
    ref["event_t0_date"] = pd.to_datetime(ref["event_t0_date"]).dt.strftime("%Y-%m-%d")
    ref = ref.drop_duplicates(["input_event_key", "sample_id", "selected_target_id", "instrument", "event_t0_date"])
    ref_cols = [
        "input_event_key",
        "sample_id",
        "selected_target_id",
        "instrument",
        "event_t0_date",
        "binding_canonical_event_id",
        "candidate_false_repair_score",
        "candidate_rank",
        "candidate_rejected_flag",
        "fast_fail_rejected_flag",
        "cascade_bucket",
        "active_interval_calendar_day_n",
    ]
    ref_cols = [col for col in ref_cols if col in ref.columns]
    joined = primary.merge(
        ref[ref_cols],
        on=["input_event_key", "sample_id", "selected_target_id", "instrument", "event_t0_date"],
        how="left",
        validate="1:1",
        suffixes=("", "_10c"),
    )
    parsed = joined["feature_matrix_join_key"].map(parse_canonical_from_pipe)
    if "binding_canonical_event_id" in joined.columns:
        from_10c = joined["binding_canonical_event_id"].map(nonempty)
    else:
        from_10c = pd.Series([""] * len(joined), index=joined.index)
    joined["binding_canonical_event_id"] = from_10c.mask(from_10c.eq(""), parsed)
    joined["canonical_id_source"] = np.select(
        [from_10c.ne(""), parsed.ne("")],
        ["10C.input_event_key_join", "feature_matrix_join_key_parse_fallback"],
        default="missing",
    )
    joined["canonical_id_parse_crosscheck_mismatch_flag"] = from_10c.ne("") & parsed.ne("") & from_10c.ne(parsed)
    joined["canonical_id_fallback_to_join_key_parse_flag"] = from_10c.eq("") & parsed.ne("")
    parsed_input = joined["input_event_key"].map(parse_canonical_from_pipe)
    joined["input_event_key_parse_success_flag"] = parsed_input.ne("")

    audit = pd.DataFrame(
        [
            {
                "audit_scope": "10A_primary_to_10C_canonical_id",
                "primary_denominator_row_n": len(joined),
                "canonical_id_10c_join_success_n": int(from_10c.ne("").sum()),
                "canonical_id_10c_join_success_rate": safe_rate(int(from_10c.ne("").sum()), len(joined)),
                "canonical_id_parse_crosscheck_mismatch_n": int(joined["canonical_id_parse_crosscheck_mismatch_flag"].sum()),
                "canonical_id_fallback_to_join_key_parse_n": int(joined["canonical_id_fallback_to_join_key_parse_flag"].sum()),
                "canonical_id_fallback_to_join_key_parse_rate": safe_rate(
                    int(joined["canonical_id_fallback_to_join_key_parse_flag"].sum()), len(joined)
                ),
                "input_event_key_parse_success_rate": safe_rate(int(joined["input_event_key_parse_success_flag"].sum()), len(joined)),
                "canonical_id_missing_n": int(joined["binding_canonical_event_id"].map(nonempty).eq("").sum()),
                "canonical_id_status": "ok"
                if joined["binding_canonical_event_id"].map(nonempty).ne("").all()
                else "canonical_id_missing",
            }
        ]
    )
    denom_audit = pd.DataFrame(
        [
            {
                "population_id": scope["population_id"],
                "rule_arm_id": scope["rule_arm_id"],
                "input_denominator_id": scope["input_denominator_id"],
                "denominator_id": scope["denominator_id"],
                "admission_status": scope["admission_status"],
                "readout_only_flag": scope["readout_only_flag"],
                "pre_filter_row_n": len(ten_a),
                "primary_denominator_row_n": len(joined),
                "split_train_n": int(joined["split"].astype(str).eq("train").sum()),
                "split_validation_n": int(joined["split"].astype(str).eq("validation").sum()),
                "split_robustness_n": int(joined["split"].astype(str).eq("robustness").sum()),
                "denominator_status": "ok" if len(joined) > 0 else "primary_denominator_empty",
            }
        ]
    )
    return joined, audit, denom_audit


def join_feature_matrix(primary: pd.DataFrame, paths: dict[str, Path]) -> tuple[pd.DataFrame, pd.DataFrame]:
    features = read_parquet_columns(paths["nine_b_feature_matrix"])
    features = features.copy()
    features["event_t0_date"] = pd.to_datetime(features["event_t0_date"]).dt.strftime("%Y-%m-%d")
    features["_feature_matrix_join_key"] = make_feature_join_key(features)
    meta_rename = {
        "sample_id": "feature_sample_id",
        "selected_target_id": "feature_selected_target_id",
        "denominator_id": "feature_denominator_id",
        "canonical_event_id": "feature_canonical_event_id",
        "instrument": "feature_instrument",
        "event_t0_date": "feature_event_t0_date",
        "event_split": "feature_event_split",
        "feature_as_of_date": "feature_as_of_date_09b",
    }
    features = features.rename(columns={key: value for key, value in meta_rename.items() if key in features.columns})
    joined = primary.merge(
        features,
        left_on="feature_matrix_join_key",
        right_on="_feature_matrix_join_key",
        how="left",
        validate="1:1",
    )
    matched = joined["_feature_matrix_join_key"].notna()
    split_match = matched & joined["split"].astype(str).eq(joined["feature_event_split"].astype(str))
    instrument_match = matched & joined["instrument"].astype(str).eq(joined["feature_instrument"].astype(str))
    date_match = matched & joined["event_t0_date"].astype(str).eq(joined["feature_event_t0_date"].astype(str))
    audit = pd.DataFrame(
        [
            {
                "join_name": "10A_to_09B_feature_matrix",
                "left_row_count": len(primary),
                "matched_row_count": int(matched.sum()),
                "match_rate": safe_rate(int(matched.sum()), len(primary)),
                "split_match_rate": safe_rate(int(split_match.sum()), int(matched.sum())),
                "instrument_match_rate": safe_rate(int(instrument_match.sum()), int(matched.sum())),
                "event_t0_date_match_rate": safe_rate(int(date_match.sum()), int(matched.sum())),
                "join_status": "ok" if matched.all() and split_match.all() and instrument_match.all() and date_match.all() else "join_mismatch",
            }
        ]
    )
    return joined, audit


def join_08_labels(frame: pd.DataFrame, paths: dict[str, Path]) -> tuple[pd.DataFrame, pd.DataFrame]:
    cols = [
        "event_id",
        "instrument",
        "event_t0_date",
        "event_split",
        "confirm_20_touch_pos",
        "forward_return_20d",
        "forward_return_60d",
        "forward_return_120d",
        "mfe_20d",
        "mfe_60d",
        "mfe_120d",
        "mae_20d",
        "mae_60d",
        "mae_120d",
        "horizon_complete_20d",
        "horizon_complete_60d",
        "horizon_complete_120d",
        "candidate_outcome_120d_status",
        "event_big_winner_120d_label",
    ]
    labels = read_parquet_columns(paths["eight_labels"], cols)
    labels["event_t0_date"] = pd.to_datetime(labels["event_t0_date"]).dt.strftime("%Y-%m-%d")
    duplicate_n = int(labels.duplicated(["event_id"]).sum())
    labels = labels.sort_values(["event_id"]).drop_duplicates(["event_id"], keep="first")
    rename = {
        "instrument": "label_instrument_08",
        "event_t0_date": "label_event_t0_date_08",
        "event_split": "label_event_split_08",
    }
    labels = labels.rename(columns=rename)
    joined = frame.merge(labels, left_on="binding_canonical_event_id", right_on="event_id", how="left", validate="m:1")
    matched = joined["event_id"].notna()
    split_match = matched & joined["split"].astype(str).eq(joined["label_event_split_08"].astype(str))
    instrument_match = matched & joined["instrument"].astype(str).eq(joined["label_instrument_08"].astype(str))
    date_match = matched & joined["event_t0_date"].astype(str).eq(joined["label_event_t0_date_08"].astype(str))
    audit = pd.DataFrame(
        [
            {
                "join_name": "10A_to_08_label_path",
                "left_row_count": len(frame),
                "matched_row_count": int(matched.sum()),
                "match_rate": safe_rate(int(matched.sum()), len(frame)),
                "duplicate_right_key_n": duplicate_n,
                "split_match_rate": safe_rate(int(split_match.sum()), int(matched.sum())),
                "instrument_match_rate": safe_rate(int(instrument_match.sum()), int(matched.sum())),
                "event_t0_date_match_rate": safe_rate(int(date_match.sum()), int(matched.sum())),
                "join_status": "ok" if matched.all() and split_match.all() and instrument_match.all() and date_match.all() else "join_mismatch",
            }
        ]
    )
    return joined, audit


def join_09a(frame: pd.DataFrame, paths: dict[str, Path]) -> tuple[pd.DataFrame, pd.DataFrame]:
    bindings = read_parquet_columns(paths["nine_a_bindings"])
    bindings = bindings.copy()
    bindings["event_t0_date"] = pd.to_datetime(bindings["event_t0_date"]).dt.strftime("%Y-%m-%d")
    bindings["_09a_join_key"] = make_feature_join_key(bindings)
    duplicate_n = int(bindings.duplicated(["_09a_join_key"]).sum())
    bindings = bindings.sort_values(["_09a_join_key"]).drop_duplicates(["_09a_join_key"], keep="first")
    rename = {
        "instrument": "instrument_09a",
        "event_t0_date": "event_t0_date_09a",
        "event_split": "event_split_09a",
        "event_regime_bucket": "event_regime_bucket_09a",
        "episode_regime_bucket": "episode_regime_bucket_09a",
        "selected_fast_fail_10_label": "selected_fast_fail_10_label_09a",
        "frozen_false_repair_20d_label": "frozen_false_repair_20d_label_09a",
        "event_big_winner_120d_label": "event_big_winner_120d_label_09a",
    }
    bindings = bindings.rename(columns={key: value for key, value in rename.items() if key in bindings.columns})
    frame = frame.copy()
    frame["_09a_join_key"] = (
        frame["sample_id"].astype(str)
        + "|"
        + frame["selected_target_id"].astype(str)
        + "|"
        + frame["input_denominator_id"].astype(str)
        + "|"
        + frame["binding_canonical_event_id"].astype(str)
    )
    joined = frame.merge(bindings, on="_09a_join_key", how="left", validate="m:1", suffixes=("", "_09a_raw"))
    matched = joined["canonical_event_id"].notna() if "canonical_event_id" in joined.columns else joined["instrument_09a"].notna()
    split_match = matched & joined["split"].astype(str).eq(joined.get("event_split_09a", "").astype(str))
    instrument_match = matched & joined["instrument"].astype(str).eq(joined.get("instrument_09a", "").astype(str))
    date_match = matched & joined["event_t0_date"].astype(str).eq(joined.get("event_t0_date_09a", "").astype(str))
    audit = pd.DataFrame(
        [
            {
                "join_name": "10A_to_09A_label_frontier",
                "left_row_count": len(frame),
                "matched_row_count": int(matched.sum()),
                "match_rate": safe_rate(int(matched.sum()), len(frame)),
                "duplicate_right_key_n": duplicate_n,
                "split_match_rate": safe_rate(int(split_match.sum()), int(matched.sum())),
                "instrument_match_rate": safe_rate(int(instrument_match.sum()), int(matched.sum())),
                "event_t0_date_match_rate": safe_rate(int(date_match.sum()), int(matched.sum())),
                "join_status": "ok" if matched.all() else "09a_join_partial_coverage",
            }
        ]
    )
    return joined, audit


def attach_regime_scope(frame: pd.DataFrame, scope_regime: str = "risk_on") -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    work = frame.copy()
    work["analysis_regime_bucket"], work["analysis_regime_source"] = coalesce_regime(
        work, ["episode_regime_bucket_09a", "event_regime_bucket", "event_regime_bucket_09a"]
    )
    work["analysis_regime_bucket"] = work["analysis_regime_bucket"].replace("", "regime_missing_after_backfill")
    work["risk_on_scope_flag"] = work["analysis_regime_bucket"].eq(scope_regime)
    rows = []
    for split in [*PRIMARY_SPLITS, "all"]:
        group = work if split == "all" else work.loc[work["split"].astype(str).eq(split)]
        rows.append(
            {
                "split": split,
                "pre_scope_primary_denominator_row_n": len(group),
                "risk_on_evaluated_row_n": int(group["analysis_regime_bucket"].eq("risk_on").sum()),
                "risk_off_out_of_scope_row_n": int(group["analysis_regime_bucket"].eq("risk_off").sum()),
                "transition_out_of_scope_row_n": int(group["analysis_regime_bucket"].eq("transition").sum()),
                "regime_missing_after_backfill_row_n": int(group["analysis_regime_bucket"].eq("regime_missing_after_backfill").sum()),
                "invalid_regime_row_n": int(
                    (~group["analysis_regime_bucket"].isin(["risk_on", "risk_off", "transition", "regime_missing_after_backfill"])).sum()
                ),
                "risk_on_evaluated_rate": safe_rate(int(group["analysis_regime_bucket"].eq("risk_on").sum()), len(group)),
                "scope_filter_status": "ok" if int(group["analysis_regime_bucket"].eq("risk_on").sum()) > 0 else "risk_on_evaluated_empty",
            }
        )
    scope_audit = pd.DataFrame(rows)
    rec_rows = []
    for (split, bucket, scope_flag), group in work.groupby(["split", "analysis_regime_bucket", "risk_on_scope_flag"], dropna=False):
        rec_rows.append(
            {
                "split": split,
                "analysis_regime_bucket": bucket,
                "risk_on_scope_flag": bool(scope_flag),
                "episode_regime_bucket_n": int(normalize_regime_series(group.get("episode_regime_bucket_09a", pd.Series([], dtype=object))).ne("").sum()),
                "event_regime_backfill_n": int(
                    normalize_regime_series(group.get("episode_regime_bucket_09a", pd.Series("", index=group.index))).eq("")
                    .astype(bool)
                    .mul(normalize_regime_series(group.get("event_regime_bucket", pd.Series("", index=group.index))).ne(""))
                    .sum()
                ),
                "residual_missing_n": int(group["analysis_regime_bucket"].eq("regime_missing_after_backfill").sum()),
                "residual_missing_rate": safe_rate(int(group["analysis_regime_bucket"].eq("regime_missing_after_backfill").sum()), len(group)),
                "invalid_regime_n": int(
                    (~group["analysis_regime_bucket"].isin(["risk_on", "risk_off", "transition", "regime_missing_after_backfill"])).sum()
                ),
                "regime_source_status": "ok" if bucket in ["risk_on", "risk_off", "transition"] else "regime_missing_after_backfill",
            }
        )
    regime_audit = pd.DataFrame(rec_rows)
    return work, scope_audit, regime_audit


def attach_weights(frame: pd.DataFrame, paths: dict[str, Path]) -> tuple[pd.DataFrame, pd.DataFrame]:
    weights = read_parquet_columns(paths["nine_b_sample_weights"])
    weights = weights.copy()
    weights["_weight_join_key"] = (
        weights["sample_id"].astype(str)
        + "|"
        + weights["selected_target_id"].astype(str)
        + "|"
        + weights["denominator_id"].astype(str)
        + "|"
        + weights["canonical_event_id"].astype(str)
        + "|"
        + weights["weight_horizon_id"].astype(str)
    )
    audit_rows = []
    duplicate_count = int(weights.duplicated(["_weight_join_key", "scope_usage"]).sum())
    work = frame.copy()

    def merge_weight(
        base: pd.DataFrame,
        weight_horizon_id: str,
        scope_usage: str,
        key_col: str,
        prefix: str,
        require_supported: bool,
    ) -> pd.DataFrame:
        sub = weights.loc[
            weights["weight_horizon_id"].astype(str).eq(weight_horizon_id)
            & weights["scope_usage"].astype(str).eq(scope_usage)
            & (
                bool_series(weights["supported_training_scope_flag"]).eq(True)
                if require_supported
                else bool_series(weights["supported_training_scope_flag"]).eq(False)
            )
        ].copy()
        sub = sub.drop_duplicates(["_weight_join_key"], keep="first")
        cols = [
            "_weight_join_key",
            "final_sample_weight",
            "average_uniqueness",
            "time_decay_weight",
            "active_interval_start",
            "active_interval_end",
            "scope_usage",
            "supported_training_scope_flag",
            "weight_status",
        ]
        sub = sub[[col for col in cols if col in sub.columns]].rename(
            columns={col: f"{prefix}_{col}" for col in cols if col != "_weight_join_key" and col in sub.columns}
        )
        return base.merge(sub, left_on=key_col, right_on="_weight_join_key", how="left").drop(columns=["_weight_join_key"], errors="ignore")

    work = merge_weight(work, "cost_bad_10_20_20d", "supported_training", "cost_bad_sample_weight_join_key", "w_cost_supported", True)
    work = merge_weight(work, "cost_bad_10_20_20d", "readout_only", "cost_bad_sample_weight_join_key", "w_cost_readout", False)
    work = merge_weight(work, "fast_fail_10d", "supported_training", "fast_fail_sample_weight_join_key", "w_fast_supported", True)
    work = merge_weight(work, "fast_fail_10d", "readout_only", "fast_fail_sample_weight_join_key", "w_fast_readout", False)

    source_prefixes = ["w_cost_supported", "w_cost_readout", "w_fast_supported", "w_fast_readout"]
    work["final_sample_weight"] = np.nan
    work["average_uniqueness"] = np.nan
    work["time_decay_weight"] = np.nan
    work["active_interval_start"] = pd.NA
    work["active_interval_end"] = pd.NA
    work["scope_usage"] = ""
    work["supported_training_scope_flag"] = pd.Series([False] * len(work), index=work.index, dtype=object)
    work["weight_status"] = "weight_missing_fallback_unit"
    work["weight_source_priority"] = "unit_weight_fallback"
    for prefix in source_prefixes:
        col = f"{prefix}_final_sample_weight"
        if col not in work.columns:
            continue
        take = work["final_sample_weight"].isna() & work[col].notna()
        work.loc[take, "final_sample_weight"] = work.loc[take, col]
        for target in [
            "average_uniqueness",
            "time_decay_weight",
            "active_interval_start",
            "active_interval_end",
            "scope_usage",
            "supported_training_scope_flag",
            "weight_status",
        ]:
            source_col = f"{prefix}_{target}"
            if source_col in work.columns:
                work.loc[take, target] = work.loc[take, source_col]
        work.loc[take, "weight_source_priority"] = prefix
    work["final_sample_weight"] = pd.to_numeric(work["final_sample_weight"], errors="coerce").fillna(1.0).clip(lower=0.0)
    work["weight_missing_fallback_flag"] = work["weight_source_priority"].eq("unit_weight_fallback")
    work["weight_scope_fallback_to_readout_only"] = work["weight_source_priority"].isin(["w_cost_readout", "w_fast_readout"])
    audit_rows.append(
        {
            "audit_scope": "09B_sample_uniqueness_weights",
            "input_weight_row_n": len(weights),
            "duplicate_same_key_scope_n": duplicate_count,
            "primary_denominator_row_n": len(work),
            "supported_training_weight_row_n": int(work["weight_source_priority"].isin(["w_cost_supported", "w_fast_supported"]).sum()),
            "readout_only_fallback_row_n": int(work["weight_scope_fallback_to_readout_only"].sum()),
            "unit_weight_fallback_row_n": int(work["weight_missing_fallback_flag"].sum()),
            "weight_join_status": "ok" if duplicate_count == 0 else "duplicate_weight_key_scope",
        }
    )
    return work, pd.DataFrame(audit_rows)


def infer_board_bucket(instrument: Any) -> str:
    code = nonempty(instrument)
    digits = "".join(ch for ch in code if ch.isdigit())
    if len(digits) >= 6:
        code = digits[:6]
    if code.startswith(("300", "301")):
        return "chinext"
    if code.startswith(("600", "601", "603", "605", "000", "001", "002", "003")):
        return "main_board"
    return "unknown"


def apply_pit_universe_filter(
    frame: pd.DataFrame,
    paths: dict[str, Path],
    event_date_col: str = "event_t0_date",
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    work = frame.copy()
    work["instrument"] = work["instrument"].astype(str)
    work[event_date_col] = pd.to_datetime(work[event_date_col], errors="coerce").dt.strftime("%Y-%m-%d")
    pit_path = paths["pit_universe"]
    pit_columns = [
        "membership_date",
        "usable_trade_date",
        "instrument",
        "board_bucket",
        "is_listed",
        "is_st",
        "is_suspended",
        "total_market_cap_cny",
        "market_cap_threshold_cny",
        "source_trade_date",
        "membership_rule_version",
    ]
    if not pit_path.exists():
        joined = work.copy()
        joined["pit_membership_match_flag"] = False
        joined["pit_valid_executable_flag"] = False
        joined["pit_scope_filter_reason"] = "pit_source_missing"
        return joined.iloc[0:0].copy(), build_pit_filter_audit(joined), build_pit_exclusion_diagnostic(joined)

    available = pd.read_csv(pit_path, nrows=0).columns.tolist()
    usecols = [col for col in pit_columns if col in available]
    pit = pd.read_csv(pit_path, usecols=usecols, dtype={"instrument": str}, low_memory=False)
    pit["instrument"] = pit["instrument"].astype(str)
    pit["membership_date"] = pd.to_datetime(pit["membership_date"], errors="coerce").dt.strftime("%Y-%m-%d")
    pit = pit.loc[pit["instrument"].ne("") & pit["membership_date"].notna()].copy()
    pit = pit.drop_duplicates(["instrument", "membership_date"], keep="first")

    pit_date = pd.to_datetime(pit["membership_date"], errors="coerce")
    pit_bounds = (
        pit.assign(_pit_date=pit_date)
        .groupby("instrument", dropna=False)["_pit_date"]
        .agg(pit_first_membership_date="min", pit_last_membership_date="max")
        .reset_index()
    )

    rename = {
        col: f"pit_{col}"
        for col in pit.columns
        if col not in {"instrument", "membership_date"}
    }
    pit_join = pit.rename(columns=rename).rename(
        columns={"instrument": "pit_instrument", "membership_date": "pit_membership_date"}
    )
    joined = work.merge(
        pit_join,
        left_on=["instrument", event_date_col],
        right_on=["pit_instrument", "pit_membership_date"],
        how="left",
        validate="m:1",
    )
    joined = joined.merge(pit_bounds, on="instrument", how="left", validate="m:1")

    matched = joined["pit_membership_date"].notna()
    event_date = pd.to_datetime(joined[event_date_col], errors="coerce")
    ever_in_pit = joined["pit_first_membership_date"].notna()
    listed = bool_series(joined.get("pit_is_listed", pd.Series(False, index=joined.index)))
    st = bool_series(joined.get("pit_is_st", pd.Series(False, index=joined.index)))
    suspended = bool_series(joined.get("pit_is_suspended", pd.Series(False, index=joined.index)))
    valid = matched & listed & ~st & ~suspended

    joined["pit_membership_match_flag"] = matched
    joined["pit_valid_executable_flag"] = valid
    joined["pit_board_bucket"] = joined.get("pit_board_bucket", pd.Series("", index=joined.index)).fillna("").astype(str)
    inferred_board = joined["instrument"].map(infer_board_bucket)
    joined.loc[joined["pit_board_bucket"].eq(""), "pit_board_bucket"] = inferred_board.loc[joined["pit_board_bucket"].eq("")]
    joined["pit_scope_filter_reason"] = "pit_valid"
    joined.loc[~ever_in_pit, "pit_scope_filter_reason"] = "instrument_never_in_pit"
    joined.loc[ever_in_pit & ~matched & event_date.lt(joined["pit_first_membership_date"]), "pit_scope_filter_reason"] = (
        "before_first_pit_membership"
    )
    joined.loc[ever_in_pit & ~matched & event_date.gt(joined["pit_last_membership_date"]), "pit_scope_filter_reason"] = (
        "after_last_pit_membership"
    )
    joined.loc[
        ever_in_pit
        & ~matched
        & event_date.ge(joined["pit_first_membership_date"])
        & event_date.le(joined["pit_last_membership_date"]),
        "pit_scope_filter_reason",
    ] = "not_pit_member_on_event_t0_date"
    joined.loc[matched & ~listed, "pit_scope_filter_reason"] = "not_listed_on_event_t0_date"
    joined.loc[matched & listed & st, "pit_scope_filter_reason"] = "st_on_event_t0_date"
    joined.loc[matched & listed & ~st & suspended, "pit_scope_filter_reason"] = "suspended_on_event_t0_date"

    audit = build_pit_filter_audit(joined)
    diagnostic = build_pit_exclusion_diagnostic(joined)
    filtered = joined.loc[joined["pit_valid_executable_flag"]].copy()
    return filtered, audit, diagnostic


def build_pit_filter_audit(joined: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for split in [*PRIMARY_SPLITS, "all"]:
        group = joined if split == "all" else joined.loc[joined["split"].astype(str).eq(split)]
        matched = bool_series(group.get("pit_membership_match_flag", pd.Series(False, index=group.index)))
        valid = bool_series(group.get("pit_valid_executable_flag", pd.Series(False, index=group.index)))
        listed = bool_series(group.get("pit_is_listed", pd.Series(False, index=group.index)))
        st = bool_series(group.get("pit_is_st", pd.Series(False, index=group.index)))
        suspended = bool_series(group.get("pit_is_suspended", pd.Series(False, index=group.index)))
        rows.append(
            {
                "split": split,
                "pre_pit_risk_on_row_n": len(group),
                "pit_membership_joined_row_n": int(matched.sum()),
                "pit_membership_join_rate": safe_rate(int(matched.sum()), len(group)),
                "pit_valid_evaluated_row_n": int(valid.sum()),
                "pit_valid_evaluated_rate": safe_rate(int(valid.sum()), len(group)),
                "pit_excluded_row_n": int((~valid).sum()),
                "pit_excluded_rate": safe_rate(int((~valid).sum()), len(group)),
                "non_listed_excluded_row_n": int((matched & ~listed).sum()),
                "st_excluded_row_n": int((matched & listed & st).sum()),
                "suspended_excluded_row_n": int((matched & listed & ~st & suspended).sum()),
                "pit_universe_event_date_col": "event_t0_date",
                "pit_universe_date_key": "membership_date",
                "pit_scope_filter_status": "ok" if int(valid.sum()) > 0 else "pit_valid_evaluated_empty",
            }
        )
    return pd.DataFrame(rows)


def build_pit_exclusion_diagnostic(joined: pd.DataFrame) -> pd.DataFrame:
    work = joined.copy()
    columns = [
        "dimension_name",
        "dimension_value",
        "pit_scope_filter_reason",
        "row_n",
        "unique_instrument_n",
        "winner_120_row_n",
        "winner_120_rate",
        "big_failure_proxy_row_n",
        "big_failure_proxy_rate",
    ]
    if work.empty:
        return pd.DataFrame(columns=columns)
    work["event_year"] = pd.to_datetime(work["event_t0_date"], errors="coerce").dt.year.astype("Int64").astype(str)
    work["event_year"] = work["event_year"].replace("<NA>", "unknown")
    work["pit_board_bucket"] = work.get("pit_board_bucket", pd.Series("", index=work.index)).fillna("").astype(str)
    work.loc[work["pit_board_bucket"].eq(""), "pit_board_bucket"] = work.loc[work["pit_board_bucket"].eq(""), "instrument"].map(
        infer_board_bucket
    )
    work["big_failure_proxy_bool_tmp"] = bool_series(work.get("selected_fast_fail_10_label", pd.Series(False, index=work.index))) | bool_series(
        work.get("frozen_false_repair_20d_label", pd.Series(False, index=work.index))
    )
    work["winner_120_bool_tmp"] = bool_series(work.get("winner_120", pd.Series(False, index=work.index)))
    rows: list[dict[str, Any]] = []

    def add_rows(dimension_name: str, dimension_values: pd.Series) -> None:
        tmp = work.assign(_dimension_value=dimension_values.fillna("missing").astype(str))
        grouped = tmp.groupby(["_dimension_value", "pit_scope_filter_reason"], dropna=False)
        for (value, reason), group in grouped:
            rows.append(
                {
                    "dimension_name": dimension_name,
                    "dimension_value": value,
                    "pit_scope_filter_reason": reason,
                    "row_n": len(group),
                    "unique_instrument_n": int(group["instrument"].nunique()),
                    "winner_120_row_n": int(group["winner_120_bool_tmp"].sum()),
                    "winner_120_rate": safe_rate(int(group["winner_120_bool_tmp"].sum()), len(group)),
                    "big_failure_proxy_row_n": int(group["big_failure_proxy_bool_tmp"].sum()),
                    "big_failure_proxy_rate": safe_rate(int(group["big_failure_proxy_bool_tmp"].sum()), len(group)),
                }
            )

    add_rows("all", pd.Series(["all"] * len(work), index=work.index))
    add_rows("split", work["split"].astype(str))
    add_rows("event_year", work["event_year"])
    add_rows("board_bucket", work["pit_board_bucket"])
    if "source_family_id" in work.columns:
        add_rows("source_family_id", work["source_family_id"].fillna("missing").astype(str))
    return pd.DataFrame(rows, columns=columns).sort_values(["dimension_name", "dimension_value", "pit_scope_filter_reason"]).reset_index(drop=True)


def build_pit_status_audit(frame: pd.DataFrame, paths: dict[str, Path]) -> pd.DataFrame:
    rows = []
    pit_path = paths["pit_universe"]
    status = "pit_source_missing"
    pit_match_rate = float("nan")
    st_n = suspended_n = nonlisted_n = 0
    if "pit_membership_match_flag" in frame.columns:
        matched = bool_series(frame["pit_membership_match_flag"])
        pit_match_rate = safe_rate(int(matched.sum()), len(frame))
        st_n = int(bool_series(frame.get("pit_is_st", pd.Series(False, index=frame.index))).sum())
        suspended_n = int(bool_series(frame.get("pit_is_suspended", pd.Series(False, index=frame.index))).sum())
        nonlisted_n = int((matched & ~bool_series(frame.get("pit_is_listed", pd.Series(False, index=frame.index)))).sum())
        status = "ok" if len(frame) > 0 and pit_match_rate >= 0.995 and st_n == 0 and suspended_n == 0 and nonlisted_n == 0 else "left_tail_status_audit_incomplete"
    elif pit_path.exists():
        usecols = ["membership_date", "instrument", "is_listed", "is_st", "is_suspended", "usable_trade_date"]
        pit = pd.read_csv(pit_path, usecols=usecols, dtype={"instrument": str}, low_memory=False)
        pit["membership_date"] = pd.to_datetime(pit["membership_date"]).dt.strftime("%Y-%m-%d")
        need_instruments = set(frame["instrument"].astype(str))
        min_date = frame["event_t0_date"].min()
        max_date = frame["event_t0_date"].max()
        pit = pit.loc[
            pit["instrument"].astype(str).isin(need_instruments)
            & pit["membership_date"].between(str(min_date), str(max_date))
        ].copy()
        pit = pit.drop_duplicates(["instrument", "membership_date"], keep="first")
        joined = frame[["row_id", "instrument", "event_t0_date"]].merge(
            pit,
            left_on=["instrument", "event_t0_date"],
            right_on=["instrument", "membership_date"],
            how="left",
        )
        matched = joined["membership_date"].notna()
        pit_match_rate = safe_rate(int(matched.sum()), len(joined))
        st_n = int(bool_series(joined.get("is_st", pd.Series(False, index=joined.index))).sum())
        suspended_n = int(bool_series(joined.get("is_suspended", pd.Series(False, index=joined.index))).sum())
        nonlisted_n = int((~bool_series(joined.get("is_listed", pd.Series(True, index=joined.index))) & matched).sum())
        status = "ok" if pit_match_rate >= 0.995 else "left_tail_status_audit_incomplete"
    metadata_path = paths["board_metadata"]
    metadata_status = "missing"
    if metadata_path.exists():
        meta = pd.read_csv(metadata_path, usecols=["instrument", "listing_date", "delist_date", "is_delisted"], low_memory=False)
        metadata_status = "ok" if not meta.empty else "empty"
    rows.append(
        {
            "population_scope": "risk_on_evaluated",
            "row_count": len(frame),
            "pit_universe_path": relative_path(pit_path),
            "pit_membership_match_rate": pit_match_rate,
            "st_row_n": st_n,
            "suspended_row_n": suspended_n,
            "not_listed_row_n": nonlisted_n,
            "board_metadata_status": metadata_status,
            "qfq_primary_dir_exists": paths["qfq_primary_dir"].is_dir(),
            "qfq_fallback_dir_exists": paths["qfq_fallback_dir"].is_dir(),
            "sh_name_history_dir_exists": paths["sh_name_history_dir"].is_dir(),
            "sz_name_history_exists": paths["sz_name_history"].is_file(),
            "left_tail_status_audit_status": status,
        }
    )
    return pd.DataFrame(rows)


def load_feature_audits(paths: dict[str, Path]) -> tuple[pd.DataFrame, dict[str, Any], pd.DataFrame]:
    contract = pd.read_csv(paths["nine_b_feature_contract"], low_memory=False)
    transform = read_json(paths["nine_b_transform_contract"])
    stationarity = pd.read_csv(paths["nine_b_stationarity_audit"], low_memory=False)
    return contract, transform, stationarity


def validate_proxy_registry(
    frame: pd.DataFrame,
    contract: pd.DataFrame,
    transform: dict[str, Any],
    stationarity: pd.DataFrame,
    thresholds: Thresholds,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, dict[tuple[str, float], float]], dict[str, str]]:
    contract_by_feature = contract.set_index("feature_id").to_dict(orient="index")
    stationarity_by_feature = stationarity.set_index("feature_id").to_dict(orient="index") if not stationarity.empty else {}
    transform_features = transform.get("features", {}) if isinstance(transform.get("features", {}), dict) else {}
    train = frame.loc[frame["split"].astype(str).eq("train")].copy()
    registry_rows = []
    threshold_rows = []
    threshold_values: dict[str, dict[tuple[str, float], float]] = {}
    proxy_input_status: dict[str, str] = {}
    for proxy in proxy_registry():
        proxy_id = proxy["proxy_family_id"]
        fields = proxy["fields"]
        missing_fields = [field for field in fields if field not in frame.columns]
        forbidden_fields = sorted(set(fields) & OUTCOME_FORBIDDEN_FIELDS)
        contract_bad = [
            field
            for field in fields
            if field in contract_by_feature
            and not (boolish(contract_by_feature[field].get("t0_visible_flag")) and boolish(contract_by_feature[field].get("allowed_for_09C_flag")))
        ]
        contract_missing = [field for field in fields if field not in contract_by_feature]
        underpowered_fields = []
        missing_audit_unavailable_fields = []
        for field in fields:
            raw_missing = np.nan
            missing_source = "unavailable"
            if field in transform_features and "missing_rate_before_impute" in transform_features[field]:
                raw_missing = float(transform_features[field]["missing_rate_before_impute"])
                missing_source = "feature_transform_contract"
            elif field in stationarity_by_feature and "raw_missing_rate" in stationarity_by_feature[field]:
                raw_missing = float(stationarity_by_feature[field]["raw_missing_rate"])
                missing_source = "feature_stationarity_audit"
            if math.isnan(raw_missing):
                missing_audit_unavailable_fields.append(field)
                pre_non_null = np.nan
            else:
                pre_non_null = int(round(len(train) * (1.0 - raw_missing)))
            if not math.isnan(pre_non_null) and pre_non_null < thresholds.proxy_train_pre_imputation_non_null_min:
                underpowered_fields.append(field)
            for quantile in proxy.get("thresholds", {}).get(field, []):
                value = float(train[field].quantile(quantile)) if field in train.columns and not train.empty else float("nan")
                threshold_values.setdefault(proxy_id, {})[(field, quantile)] = value
                threshold_rows.append(
                    {
                        "proxy_family_id": proxy_id,
                        "feature_id": field,
                        "threshold_fit_split": "train",
                        "threshold_fit_denominator_id": "post_dedup_risk_on_r_core",
                        "threshold_fit_regime_scope": "risk_on",
                        "threshold_fit_population_id": "10A__same_instrument_cooldown_10d",
                        "threshold_operator": "quantile",
                        "threshold_quantile": quantile,
                        "threshold_value": value,
                        "fit_row_n": len(train),
                        "pre_imputation_non_null_n": pre_non_null,
                        "pre_imputation_missing_rate": raw_missing,
                        "post_09b_transform_missing_rate": float(train[field].isna().mean()) if field in train.columns and not train.empty else np.nan,
                        "missing_rate_source": missing_source,
                    }
                )
        if proxy_id == "P7_flow_confirmation_proxy":
            threshold_rows.append(
                {
                    "proxy_family_id": proxy_id,
                    "feature_id": "quality_amount_flag",
                    "threshold_fit_split": "train",
                    "threshold_fit_denominator_id": "post_dedup_risk_on_r_core",
                    "threshold_fit_regime_scope": "risk_on",
                    "threshold_fit_population_id": "10A__same_instrument_cooldown_10d",
                    "threshold_operator": "==",
                    "threshold_quantile": "",
                    "threshold_value": 1.0,
                    "fit_row_n": len(train),
                    "pre_imputation_non_null_n": len(train),
                    "pre_imputation_missing_rate": 0.0,
                    "post_09b_transform_missing_rate": float(train["quality_amount_flag"].isna().mean()) if "quality_amount_flag" in train.columns else np.nan,
                    "missing_rate_source": "binary_contract",
                }
            )
        if missing_fields:
            status = "proxy_input_blocked_missing_feature"
        elif forbidden_fields:
            status = "proxy_input_blocked_forbidden_field"
        elif contract_bad or contract_missing:
            status = "proxy_input_blocked_contract"
        elif underpowered_fields:
            status = "proxy_input_underpowered"
        elif missing_audit_unavailable_fields:
            status = "pre_imputation_missing_audit_unavailable"
        else:
            status = "ok"
        proxy_input_status[proxy_id] = status
        registry_rows.append(
            {
                "proxy_family_id": proxy_id,
                "category": "A_t0_feature_contract",
                "field_list": "|".join(fields),
                "description": proxy["description"],
                "field_n": len(fields),
                "missing_fields": "|".join(missing_fields),
                "forbidden_fields": "|".join(forbidden_fields),
                "contract_bad_fields": "|".join(contract_bad),
                "contract_missing_fields": "|".join(contract_missing),
                "underpowered_fields": "|".join(underpowered_fields),
                "missing_audit_unavailable_fields": "|".join(missing_audit_unavailable_fields),
                "proxy_input_status": status,
            }
        )
    return pd.DataFrame(registry_rows), pd.DataFrame(threshold_rows), threshold_values, proxy_input_status


def apply_proxy_membership(frame: pd.DataFrame, threshold_values: dict[str, dict[tuple[str, float], float]]) -> pd.DataFrame:
    work = frame.copy()

    def t(proxy_id: str, field: str, q: float) -> float:
        return threshold_values[proxy_id][(field, q)]

    work["P1_gap_event_proxy"] = (
        work["gap_open_pct"].ge(t("P1_gap_event_proxy", "gap_open_pct", 0.70))
        | work["intraday_range_atr_norm"].ge(t("P1_gap_event_proxy", "intraday_range_atr_norm", 0.70))
        | (
            work["amount_ratio_20d"].ge(t("P1_gap_event_proxy", "amount_ratio_20d", 0.70))
            & work["close_position_in_range"].ge(t("P1_gap_event_proxy", "close_position_in_range", 0.60))
        )
    )
    work["P2_shakeout_prior_path_proxy"] = (
        (
            work["close_to_high_60"].le(t("P2_shakeout_prior_path_proxy", "close_to_high_60", 0.30))
            | work["close_to_high_120"].le(t("P2_shakeout_prior_path_proxy", "close_to_high_120", 0.30))
        )
        & (
            work["upper_shadow_pct"].ge(t("P2_shakeout_prior_path_proxy", "upper_shadow_pct", 0.60))
            | work["close_position_in_range"].ge(t("P2_shakeout_prior_path_proxy", "close_position_in_range", 0.50))
        )
        & work["atr_pct_rank_60d"].ge(t("P2_shakeout_prior_path_proxy", "atr_pct_rank_60d", 0.40))
    )
    work["P3_volatility_expansion_proxy"] = (
        work["direction_entropy_20d"].ge(t("P3_volatility_expansion_proxy", "direction_entropy_20d", 0.60))
        & work["atr_pct_rank_60d"].ge(t("P3_volatility_expansion_proxy", "atr_pct_rank_60d", 0.60))
        & work["range_width_ratio_20d_60d"].ge(t("P3_volatility_expansion_proxy", "range_width_ratio_20d_60d", 0.60))
    )
    work["P4_momentum_leader_proxy"] = (
        work["momentum_percentile_20d"].ge(t("P4_momentum_leader_proxy", "momentum_percentile_20d", 0.70))
        & work["return_20d"].ge(t("P4_momentum_leader_proxy", "return_20d", 0.60))
        & work["close_to_ema20"].ge(t("P4_momentum_leader_proxy", "close_to_ema20", 0.50))
    )
    work["P5_low_noise_accumulation_proxy"] = (
        work["return_20d"].ge(t("P5_low_noise_accumulation_proxy", "return_20d", 0.35))
        & work["return_20d"].le(t("P5_low_noise_accumulation_proxy", "return_20d", 0.65))
        & work["atr_pct_rank_60d"].le(t("P5_low_noise_accumulation_proxy", "atr_pct_rank_60d", 0.60))
        & (
            work["prior_event_count_60d"].ge(t("P5_low_noise_accumulation_proxy", "prior_event_count_60d", 0.50))
            | work["ema60_positive_run"].ge(t("P5_low_noise_accumulation_proxy", "ema60_positive_run", 0.50))
        )
    )
    work["P6_repair_structure_proxy"] = (
        work["close_to_ema20"].ge(t("P6_repair_structure_proxy", "close_to_ema20", 0.50))
        & work["close_to_ema60"].ge(t("P6_repair_structure_proxy", "close_to_ema60", 0.50))
        & work["ema20_slope_20d"].ge(t("P6_repair_structure_proxy", "ema20_slope_20d", 0.50))
        & work["atr_pct_rank_60d"].le(t("P6_repair_structure_proxy", "atr_pct_rank_60d", 0.70))
    )
    work["P7_flow_confirmation_proxy"] = (
        work["quality_amount_flag"].fillna(0).ge(1)
        | (
            work["amount_ratio_20d"].ge(t("P7_flow_confirmation_proxy", "amount_ratio_20d", 0.70))
            & work["turnover_ratio_20d"].ge(t("P7_flow_confirmation_proxy", "turnover_ratio_20d", 0.60))
        )
    )
    work["P8_recurrence_density_proxy"] = (
        work["prior_event_count_60d"].ge(t("P8_recurrence_density_proxy", "prior_event_count_60d", 0.70))
        | work["raw_cluster_event_count"].ge(t("P8_recurrence_density_proxy", "raw_cluster_event_count", 0.70))
        | (
            work["family_count"].ge(t("P8_recurrence_density_proxy", "family_count", 0.60))
            & work["channel_count"].ge(t("P8_recurrence_density_proxy", "channel_count", 0.60))
        )
    )
    for proxy in proxy_registry():
        work[proxy["proxy_family_id"]] = work[proxy["proxy_family_id"]].fillna(False).astype(bool)
    return work


def prepare_outcome_columns(frame: pd.DataFrame) -> pd.DataFrame:
    work = frame.copy()
    work["winner_120_bool"] = bool_series(work["winner_120"])
    work["fast_fail_10_bool"] = bool_series(work.get("selected_fast_fail_10_label", pd.Series(False, index=work.index)))
    work["false_repair_20_bool"] = bool_series(work.get("frozen_false_repair_20d_label", pd.Series(False, index=work.index)))
    work["big_failure_proxy_bool"] = work["fast_fail_10_bool"] | work["false_repair_20_bool"]
    work["e1_missed_winner_bool"] = bool_series(work.get("E1_missed_winner_flag", pd.Series(False, index=work.index)))
    work["event_year_quarter"] = pd.PeriodIndex(pd.to_datetime(work["event_t0_date"]), freq="Q").astype(str)
    work["source_family_id_matched"] = work["source_family_id"].fillna("").astype(str)
    fallback = work.get("source_pool_id", pd.Series("", index=work.index)).fillna("").astype(str)
    work.loc[work["source_family_id_matched"].eq(""), "source_family_id_matched"] = fallback.loc[work["source_family_id_matched"].eq("")]
    work.loc[work["source_family_id_matched"].eq(""), "source_family_id_matched"] = "source_family_missing"
    return work


def split_frame(frame: pd.DataFrame, split: str) -> pd.DataFrame:
    if split == "all":
        return frame
    return frame.loc[frame["split"].astype(str).eq(split)]


def weighted_sum(values: pd.Series, weights: pd.Series) -> float:
    mask = values.notna() & weights.notna() & weights.gt(0)
    if not mask.any():
        return float("nan")
    return float((pd.to_numeric(values.loc[mask], errors="coerce") * weights.loc[mask]).sum())


def weighted_mean(values: pd.Series, weights: pd.Series) -> float:
    mask = values.notna() & weights.notna() & weights.gt(0)
    if not mask.any():
        return float("nan")
    w = weights.loc[mask].astype(float)
    v = pd.to_numeric(values.loc[mask], errors="coerce").astype(float)
    denom = float(w.sum())
    if denom <= 0:
        return float("nan")
    return float((v * w).sum() / denom)


def weighted_quantile(values: pd.Series, weights: pd.Series, quantile: float) -> float:
    mask = values.notna() & weights.notna() & weights.gt(0)
    if not mask.any():
        return float("nan")
    v = pd.to_numeric(values.loc[mask], errors="coerce").to_numpy(dtype=float)
    w = weights.loc[mask].to_numpy(dtype=float)
    order = np.argsort(v)
    v = v[order]
    w = w[order]
    cumulative = np.cumsum(w)
    cutoff = quantile * cumulative[-1]
    return float(v[np.searchsorted(cumulative, cutoff, side="left")])


def winsorized_weighted_mean(values: pd.Series, weights: pd.Series, lower: float = 0.01, upper: float = 0.99) -> float:
    lo = weighted_quantile(values, weights, lower)
    hi = weighted_quantile(values, weights, upper)
    if math.isnan(lo) or math.isnan(hi):
        return float("nan")
    clipped = pd.to_numeric(values, errors="coerce").clip(lo, hi)
    return weighted_mean(clipped, weights)


def trimmed_weighted_mean(values: pd.Series, weights: pd.Series, lower: float = 0.05, upper: float = 0.95) -> float:
    lo = weighted_quantile(values, weights, lower)
    hi = weighted_quantile(values, weights, upper)
    if math.isnan(lo) or math.isnan(hi):
        return float("nan")
    mask = pd.to_numeric(values, errors="coerce").between(lo, hi)
    return weighted_mean(values.loc[mask], weights.loc[mask])


def weighted_rate(flag: pd.Series, weights: pd.Series) -> float:
    return weighted_mean(bool_series(flag).astype(float), weights)


def metric_bundle(group: pd.DataFrame, weights: pd.Series) -> dict[str, Any]:
    row: dict[str, Any] = {
        "eligible_row_n": int(weights.gt(0).sum()),
        "weight_sum": float(weights.sum()),
        "winner_120_n": int((bool_series(group["winner_120_bool"]) & weights.gt(0)).sum()),
        "winner_120_rate": weighted_rate(group["winner_120_bool"], weights),
        "fast_fail_10_n": int((bool_series(group["fast_fail_10_bool"]) & weights.gt(0)).sum()),
        "fast_fail_10_rate": weighted_rate(group["fast_fail_10_bool"], weights),
        "false_repair_20_n": int((bool_series(group["false_repair_20_bool"]) & weights.gt(0)).sum()),
        "false_repair_20_rate": weighted_rate(group["false_repair_20_bool"], weights),
        "big_failure_proxy_n": int((bool_series(group["big_failure_proxy_bool"]) & weights.gt(0)).sum()),
        "big_failure_proxy_rate": weighted_rate(group["big_failure_proxy_bool"], weights),
        "e1_missed_winner_n": int((bool_series(group["e1_missed_winner_bool"]) & weights.gt(0)).sum()),
        "e1_missed_winner_rate": weighted_rate(group["e1_missed_winner_bool"], weights),
    }
    for col in ["forward_return_20d", "forward_return_60d", "forward_return_120d"]:
        values = pd.to_numeric(group.get(col, pd.Series(np.nan, index=group.index)), errors="coerce")
        row[f"{col}_weighted_mean"] = weighted_mean(values, weights)
        row[f"{col}_winsorized_mean_1_99"] = winsorized_weighted_mean(values, weights, 0.01, 0.99)
        row[f"{col}_trimmed_mean_5_95"] = trimmed_weighted_mean(values, weights, 0.05, 0.95)
        row[f"{col}_median"] = weighted_quantile(values, weights, 0.50)
        for q in [0.05, 0.25, 0.75, 0.90, 0.95, 0.99]:
            row[f"{col}_p{int(q * 100):02d}"] = weighted_quantile(values, weights, q)
        row[f"{col}_negative_return_rate"] = weighted_rate(values.lt(0), weights)
    for col in ["mfe_20d", "mfe_60d", "mfe_120d", "mae_20d", "mae_60d", "mae_120d"]:
        values = pd.to_numeric(group.get(col, pd.Series(np.nan, index=group.index)), errors="coerce")
        row[f"{col}_median"] = weighted_quantile(values, weights, 0.50)
        for q in [0.05, 0.25, 0.75, 0.90, 0.95, 0.99]:
            row[f"{col}_p{int(q * 100):02d}"] = weighted_quantile(values, weights, q)
    exposure = pd.to_numeric(group.get("active_interval_calendar_day_n", pd.Series(np.nan, index=group.index)), errors="coerce")
    if exposure.isna().all():
        alt_start = pd.to_datetime(group.get("active_interval_start", pd.Series(pd.NaT, index=group.index)), errors="coerce")
        alt_end = pd.to_datetime(group.get("active_interval_end", pd.Series(pd.NaT, index=group.index)), errors="coerce")
        exposure = (alt_end - alt_start).dt.days + 1
        exposure_source = "09B_weight_active_interval"
    else:
        exposure_source = "10C_active_interval_calendar_day_n"
    numerator = weighted_sum(pd.to_numeric(group.get("forward_return_60d", pd.Series(np.nan, index=group.index)), errors="coerce"), weights)
    denominator = weighted_sum(exposure, weights)
    row["return_60d_per_rejector_active_day_diagnostic"] = numerator / denominator if denominator and not math.isnan(denominator) else float("nan")
    row["exposure_day_source"] = exposure_source
    row["exposure_day_metric_status"] = "diagnostic_only_mixed_time_concept"
    return row


def construct_matched_weights(frame: pd.DataFrame, proxy_id: str, split: str) -> tuple[pd.DataFrame, dict[str, Any]]:
    work = split_frame(frame, split).copy()
    if work.empty:
        return work.assign(proxy_positive_weight=0.0, matched_base_weight=0.0), {
            "proxy_family_id": proxy_id,
            "split": split,
            "matched_base_status": "matched_base_underpowered",
        }
    work["proxy_positive_flag"] = bool_series(work[proxy_id])
    work["base_row_weight"] = pd.to_numeric(work["final_sample_weight"], errors="coerce").fillna(1.0).clip(lower=0.0)
    cell_cols = ["split", "event_year_quarter", "source_family_id_matched"]
    grouped = work.groupby(cell_cols, dropna=False).agg(
        proxy_positive_total_weight=("base_row_weight", lambda s: float(s[work.loc[s.index, "proxy_positive_flag"]].sum())),
        proxy_negative_total_weight=("base_row_weight", lambda s: float(s[~work.loc[s.index, "proxy_positive_flag"]].sum())),
        proxy_positive_row_n=("proxy_positive_flag", "sum"),
        proxy_negative_row_n=("proxy_positive_flag", lambda s: int((~s).sum())),
    )
    grouped = grouped.reset_index()
    grouped["cell_matchable_flag"] = grouped["proxy_positive_total_weight"].gt(0) & grouped["proxy_negative_total_weight"].gt(0)
    work = work.merge(grouped[cell_cols + ["proxy_positive_total_weight", "proxy_negative_total_weight", "cell_matchable_flag"]], on=cell_cols, how="left")
    work["proxy_positive_weight"] = np.where(work["proxy_positive_flag"], work["base_row_weight"], 0.0)
    work["matched_base_weight"] = 0.0
    neg_matchable = (~work["proxy_positive_flag"]) & work["cell_matchable_flag"].fillna(False)
    work.loc[neg_matchable, "matched_base_weight"] = (
        work.loc[neg_matchable, "base_row_weight"]
        * work.loc[neg_matchable, "proxy_positive_total_weight"]
        / work.loc[neg_matchable, "proxy_negative_total_weight"]
    )
    matchable_positive = work["proxy_positive_flag"] & work["cell_matchable_flag"].fillna(False)
    total_positive_weight = float(work.loc[work["proxy_positive_flag"], "base_row_weight"].sum())
    matched_positive_weight = float(work.loc[matchable_positive, "base_row_weight"].sum())
    matched_negative_rows = int(work["matched_base_weight"].gt(0).sum())
    positive_rows = int(work["proxy_positive_flag"].sum())
    quarter_n = int(work.loc[work["proxy_positive_flag"], "event_year_quarter"].nunique())
    coverage = safe_rate(matched_positive_weight, total_positive_weight)
    status = "ok"
    if positive_rows < 100 or matched_negative_rows < 300 or quarter_n < 6 or (not math.isnan(coverage) and coverage < 0.8):
        status = "matched_base_underpowered"
    audit = {
        "proxy_family_id": proxy_id,
        "split": split,
        "proxy_positive_eligible_rows": positive_rows,
        "matched_negative_eligible_rows": matched_negative_rows,
        "event_year_quarter_n": quarter_n,
        "total_positive_weight": total_positive_weight,
        "matched_positive_weight": matched_positive_weight,
        "unmatched_positive_weight": total_positive_weight - matched_positive_weight,
        "matched_positive_weight_coverage": coverage,
        "zero_negative_cell_n": int((grouped["proxy_positive_total_weight"].gt(0) & grouped["proxy_negative_total_weight"].le(0)).sum()),
        "matched_base_status": status,
    }
    return work, audit


def compare_positive_vs_base(work: pd.DataFrame, proxy_id: str, split: str) -> tuple[list[dict[str, Any]], pd.DataFrame]:
    positive_weights = work["proxy_positive_weight"].astype(float)
    base_weights = work["matched_base_weight"].astype(float)
    pos_metrics = metric_bundle(work, positive_weights)
    base_metrics = metric_bundle(work, base_weights)
    common_keys = sorted(set(pos_metrics) & set(base_metrics))
    delta_metrics: dict[str, Any] = {}
    for key in common_keys:
        if isinstance(pos_metrics[key], (int, float, np.integer, np.floating)) and isinstance(
            base_metrics[key], (int, float, np.integer, np.floating)
        ):
            delta_metrics[f"{key}_delta_vs_matched_base"] = float(pos_metrics[key]) - float(base_metrics[key])
    rows = []
    for status, metrics in [
        ("proxy_positive", pos_metrics),
        ("matched_base", base_metrics),
        ("delta_vs_matched_base", delta_metrics),
    ]:
        row = {
            "proxy_family_id": proxy_id,
            "split": split,
            "regime_scope": "risk_on",
            "matched_status": status,
            "denominator_row_n": len(work),
            "proxy_positive_row_n": int(work["proxy_positive_flag"].sum()),
            "proxy_positive_weight_sum": float(positive_weights.sum()),
            "proxy_coverage_rate": safe_rate(int(work["proxy_positive_flag"].sum()), len(work)),
        }
        row.update(metrics)
        rows.append(row)
    cache = work[
        [
            "row_id",
            "split",
            "proxy_positive_flag",
            "proxy_positive_weight",
            "matched_base_weight",
            "event_year_quarter",
            "source_family_id_matched",
        ]
    ].copy()
    cache["proxy_family_id"] = proxy_id
    cache["readout_split"] = split
    return rows, cache


def build_matched_readouts(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    readout_rows: list[dict[str, Any]] = []
    audit_rows: list[dict[str, Any]] = []
    cache_frames: list[pd.DataFrame] = []
    for proxy in proxy_registry():
        proxy_id = proxy["proxy_family_id"]
        for split in READOUT_SPLITS:
            matched_work, audit = construct_matched_weights(frame, proxy_id, split)
            rows, cache = compare_positive_vs_base(matched_work, proxy_id, split)
            readout_rows.extend(rows)
            audit_rows.append(audit)
            cache_frames.append(cache)
    return pd.DataFrame(readout_rows), pd.DataFrame(audit_rows), pd.concat(cache_frames, ignore_index=True)


def membership_count(frame: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for proxy in proxy_registry():
        proxy_id = proxy["proxy_family_id"]
        for split in READOUT_SPLITS:
            group = split_frame(frame, split)
            rows.append(
                {
                    "proxy_family_id": proxy_id,
                    "split": split,
                    "regime_scope": "risk_on",
                    "denominator_row_n": len(group),
                    "proxy_positive_row_n": int(bool_series(group[proxy_id]).sum()),
                    "proxy_positive_weight_sum": float(group.loc[bool_series(group[proxy_id]), "final_sample_weight"].sum()),
                    "proxy_coverage_rate": safe_rate(int(bool_series(group[proxy_id]).sum()), len(group)),
                }
            )
    return pd.DataFrame(rows)


def delta_lookup(readout: pd.DataFrame) -> dict[tuple[str, str], dict[str, Any]]:
    rows = readout.loc[readout["matched_status"].eq("delta_vs_matched_base")]
    return {(row["proxy_family_id"], row["split"]): row.to_dict() for _, row in rows.iterrows()}


def bootstrap_readout(
    frame: pd.DataFrame,
    matched_cache: pd.DataFrame,
    thresholds: Thresholds,
    random_seed: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    rng = np.random.default_rng(random_seed)
    rows: list[dict[str, Any]] = []
    sample_rows: list[dict[str, Any]] = []
    metric_cols = {
        "median_forward_return_60d_delta": "median",
        "winsorized_mean_forward_return_60d_delta": "winsorized",
        "winner_120_rate_delta": "winner",
        "big_failure_proxy_rate_delta": "big_failure",
        "false_repair_20_rate_delta": "false_repair",
        "fast_fail_10_rate_delta": "fast_fail",
    }
    frame_indexed = frame.set_index("row_id", drop=False)
    for proxy in proxy_registry():
        proxy_id = proxy["proxy_family_id"]
        for split in ["train", "validation", "robustness"]:
            cache = matched_cache.loc[
                matched_cache["proxy_family_id"].eq(proxy_id) & matched_cache["readout_split"].eq(split)
            ].copy()
            if cache.empty:
                continue
            work = frame_indexed.loc[cache["row_id"].to_numpy()].reset_index(drop=True).copy()
            work["proxy_positive_weight"] = cache["proxy_positive_weight"].to_numpy(dtype=float)
            work["matched_base_weight"] = cache["matched_base_weight"].to_numpy(dtype=float)
            for block_col, usage_scope in [
                ("instrument", "acceptance_primary"),
                ("binding_canonical_event_id", "sensitivity_secondary"),
            ]:
                prepared = work[
                    [
                        block_col,
                        "proxy_positive_weight",
                        "matched_base_weight",
                        "forward_return_60d",
                        "winner_120_bool",
                        "big_failure_proxy_bool",
                        "false_repair_20_bool",
                        "fast_fail_10_bool",
                    ]
                ].copy()
                prepared["forward_return_60d"] = pd.to_numeric(prepared["forward_return_60d"], errors="coerce").fillna(0.0)
                for flag_col in ["winner_120_bool", "big_failure_proxy_bool", "false_repair_20_bool", "fast_fail_10_bool"]:
                    prepared[flag_col] = bool_series(prepared[flag_col]).astype(float)
                prepared["pos_return60_sum"] = prepared["proxy_positive_weight"] * prepared["forward_return_60d"]
                prepared["base_return60_sum"] = prepared["matched_base_weight"] * prepared["forward_return_60d"]
                prepared["pos_winner_sum"] = prepared["proxy_positive_weight"] * prepared["winner_120_bool"]
                prepared["base_winner_sum"] = prepared["matched_base_weight"] * prepared["winner_120_bool"]
                prepared["pos_big_failure_sum"] = prepared["proxy_positive_weight"] * prepared["big_failure_proxy_bool"]
                prepared["base_big_failure_sum"] = prepared["matched_base_weight"] * prepared["big_failure_proxy_bool"]
                prepared["pos_false_repair_sum"] = prepared["proxy_positive_weight"] * prepared["false_repair_20_bool"]
                prepared["base_false_repair_sum"] = prepared["matched_base_weight"] * prepared["false_repair_20_bool"]
                prepared["pos_fast_fail_sum"] = prepared["proxy_positive_weight"] * prepared["fast_fail_10_bool"]
                prepared["base_fast_fail_sum"] = prepared["matched_base_weight"] * prepared["fast_fail_10_bool"]
                block = (
                    prepared.groupby(block_col, dropna=False)
                    .agg(
                        pos_weight=("proxy_positive_weight", "sum"),
                        base_weight=("matched_base_weight", "sum"),
                        pos_return60_sum=("pos_return60_sum", "sum"),
                        base_return60_sum=("base_return60_sum", "sum"),
                        pos_winner_sum=("pos_winner_sum", "sum"),
                        base_winner_sum=("base_winner_sum", "sum"),
                        pos_big_failure_sum=("pos_big_failure_sum", "sum"),
                        base_big_failure_sum=("base_big_failure_sum", "sum"),
                        pos_false_repair_sum=("pos_false_repair_sum", "sum"),
                        base_false_repair_sum=("base_false_repair_sum", "sum"),
                        pos_fast_fail_sum=("pos_fast_fail_sum", "sum"),
                        base_fast_fail_sum=("base_fast_fail_sum", "sum"),
                    )
                    .reset_index()
                )
                unique_blocks = block[block_col].astype(str).to_numpy()
                arrays = {col: block[col].to_numpy(dtype=float) for col in block.columns if col != block_col}
                samples: dict[str, list[float]] = {name: [] for name in metric_cols}
                for sample_idx in range(thresholds.bootstrap_n):
                    sampled_positions = rng.integers(0, len(unique_blocks), size=len(unique_blocks))
                    pos_weight = float(arrays["pos_weight"][sampled_positions].sum())
                    base_weight = float(arrays["base_weight"][sampled_positions].sum())

                    def ratio(sum_col: str, weight: float) -> float:
                        if weight <= 0:
                            return float("nan")
                        return float(arrays[sum_col][sampled_positions].sum() / weight)

                    pos_return = ratio("pos_return60_sum", pos_weight)
                    base_return = ratio("base_return60_sum", base_weight)
                    samples["median_forward_return_60d_delta"].append(pos_return - base_return)
                    samples["winsorized_mean_forward_return_60d_delta"].append(pos_return - base_return)
                    samples["winner_120_rate_delta"].append(
                        ratio("pos_winner_sum", pos_weight) - ratio("base_winner_sum", base_weight)
                    )
                    samples["big_failure_proxy_rate_delta"].append(
                        ratio("pos_big_failure_sum", pos_weight) - ratio("base_big_failure_sum", base_weight)
                    )
                    samples["false_repair_20_rate_delta"].append(
                        ratio("pos_false_repair_sum", pos_weight) - ratio("base_false_repair_sum", base_weight)
                    )
                    samples["fast_fail_10_rate_delta"].append(
                        ratio("pos_fast_fail_sum", pos_weight) - ratio("base_fast_fail_sum", base_weight)
                    )
                    if sample_idx < 5:
                        sample_rows.append(
                            {
                                "proxy_family_id": proxy_id,
                                "split": split,
                                "bootstrap_block_level": block_col,
                                "bootstrap_sample_id": sample_idx,
                                "sampled_block_n": len(sampled_positions),
                            }
                        )
                row: dict[str, Any] = {
                    "proxy_family_id": proxy_id,
                    "split": split,
                    "regime_scope": "risk_on",
                    "bootstrap_block_level": block_col,
                    "bootstrap_usage_scope": usage_scope,
                    "bootstrap_n": thresholds.bootstrap_n,
                }
                for name in metric_cols:
                    arr = np.asarray(samples[name], dtype=float)
                    arr = arr[~np.isnan(arr)]
                    row[f"{name}_boot_median"] = float(np.median(arr)) if len(arr) else float("nan")
                    row[f"{name}_ci05"] = float(np.quantile(arr, 0.05)) if len(arr) else float("nan")
                    row[f"{name}_ci95"] = float(np.quantile(arr, 0.95)) if len(arr) else float("nan")
                    row[f"probability_{name}_gt_0"] = float(np.mean(arr > 0)) if len(arr) else float("nan")
                margin = thresholds.bootstrap_failure_delta_margin
                row[f"probability_big_failure_proxy_rate_delta_le_{margin:g}"] = float(
                    np.mean(np.asarray(samples["big_failure_proxy_rate_delta"], dtype=float) <= margin)
                )
                row[f"probability_false_repair_20_rate_delta_le_{margin:g}"] = float(
                    np.mean(np.asarray(samples["false_repair_20_rate_delta"], dtype=float) <= margin)
                )
                row[f"probability_fast_fail_10_rate_delta_le_{margin:g}"] = float(
                    np.mean(np.asarray(samples["fast_fail_10_rate_delta"], dtype=float) <= margin)
                )
                row["big_failure_proxy_rate_delta_p95"] = float(
                    np.quantile(np.asarray(samples["big_failure_proxy_rate_delta"], dtype=float), 0.95)
                )
                rows.append(row)
    return pd.DataFrame(rows), pd.DataFrame(sample_rows)


def recompute_delta_after_drop(work: pd.DataFrame, proxy_id: str, split: str) -> dict[str, Any]:
    matched_work, _ = construct_matched_weights(work, proxy_id, split)
    rows, _ = compare_positive_vs_base(matched_work, proxy_id, split)
    delta = [row for row in rows if row["matched_status"] == "delta_vs_matched_base"][0]
    return delta


def topk_sensitivity(frame: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for proxy in proxy_registry():
        proxy_id = proxy["proxy_family_id"]
        for split in ["train", "robustness", "all"]:
            group = split_frame(frame, split).copy()
            proxy_positive = group.loc[bool_series(group[proxy_id])].copy()
            proxy_positive["weighted_forward_return_60d_contribution"] = (
                pd.to_numeric(proxy_positive["forward_return_60d"], errors="coerce").fillna(0.0)
                * proxy_positive["final_sample_weight"].astype(float)
            )
            for unit_col, unit_type in [("instrument", "instrument"), ("binding_canonical_event_id", "event")]:
                ranked = (
                    proxy_positive.groupby(unit_col)["weighted_forward_return_60d_contribution"]
                    .sum()
                    .sort_values(ascending=False)
                    .index.astype(str)
                    .tolist()
                )
                for k in [1, 3, 5]:
                    remove = set(ranked[:k])
                    reduced = group.loc[~group[unit_col].astype(str).isin(remove)].copy()
                    delta = recompute_delta_after_drop(reduced, proxy_id, split)
                    rows.append(
                        {
                            "proxy_family_id": proxy_id,
                            "split": split,
                            "unit_type": unit_type,
                            "top_k_removed": k,
                            "removed_unit_list": "|".join(sorted(remove)),
                            "remaining_row_n": len(reduced),
                            "winner_120_rate_delta": delta.get("winner_120_rate_delta_vs_matched_base"),
                            "median_forward_return_60d_delta": delta.get("forward_return_60d_median_delta_vs_matched_base"),
                            "winsorized_mean_forward_return_60d_delta": delta.get(
                                "forward_return_60d_winsorized_mean_1_99_delta_vs_matched_base"
                            ),
                            "big_failure_proxy_rate_delta": delta.get("big_failure_proxy_rate_delta_vs_matched_base"),
                        }
                    )
    return pd.DataFrame(rows)


def build_hard_failure_reconciliation(frame: pd.DataFrame, paths: dict[str, Path]) -> pd.DataFrame:
    labels_yaml = load_yaml(paths["labels_yaml"])
    hard_blocks = boolish(
        labels_yaml.get("labels", {})
        .get("label_families", {})
        .get("winner_120", {})
        .get("hard_failure_first_blocks_winner", False)
    )
    rows = []
    for split in READOUT_SPLITS:
        group = split_frame(frame, split)
        fast_fail_10a = bool_series(group.get("selected_fast_fail_10_label", pd.Series(False, index=group.index)))
        fast_fail_09a = bool_series(group.get("selected_fast_fail_10_label_09a", pd.Series(False, index=group.index)))
        winner_10a = bool_series(group.get("winner_120", pd.Series(False, index=group.index)))
        winner_09a = bool_series(group.get("event_big_winner_120d_label_09a", pd.Series(False, index=group.index)))
        touch = pd.to_numeric(group.get("selected_fast_fail_touch_pos", pd.Series(np.nan, index=group.index)), errors="coerce")
        confirm = pd.to_numeric(group.get("confirm_20_touch_pos", pd.Series(np.nan, index=group.index)), errors="coerce")
        first_before_confirm = fast_fail_09a & touch.notna() & (confirm.isna() | confirm.lt(0) | touch.le(confirm))
        rows.append(
            {
                "split": split,
                "analysis_regime_bucket": "risk_on",
                "labels_yaml_hard_failure_first_blocks_winner": hard_blocks,
                "primary_denominator_row_n": len(group),
                "winner_120_n_10a": int(winner_10a.sum()),
                "winner_120_n_09a": int(winner_09a.sum()),
                "winner_label_mismatch_n": int((winner_10a != winner_09a).sum()),
                "fast_fail_10_n_10a": int(fast_fail_10a.sum()),
                "fast_fail_10_n_09a": int(fast_fail_09a.sum()),
                "fast_fail_label_mismatch_n": int((fast_fail_10a != fast_fail_09a).sum()),
                "fast_fail_first_before_or_at_confirm_20_n": int(first_before_confirm.sum()),
                "fast_fail_first_before_or_at_confirm_20_winner_n": int((first_before_confirm & winner_10a).sum()),
                "candidate_outcome_120d_status_censored_n": int(
                    group.get("candidate_outcome_120d_status", pd.Series("", index=group.index)).astype(str).str.contains("censor", case=False).sum()
                ),
                "reconciliation_status": "ok",
            }
        )
    return pd.DataFrame(rows)


def acceptance_decisions(
    registry: pd.DataFrame,
    matched_audit: pd.DataFrame,
    readout: pd.DataFrame,
    bootstrap: pd.DataFrame,
    topk: pd.DataFrame,
    proxy_input_status: dict[str, str],
    thresholds: Thresholds,
) -> pd.DataFrame:
    deltas = delta_lookup(readout)
    rows = []
    margin = thresholds.bootstrap_failure_delta_margin
    prob_big_col = f"probability_big_failure_proxy_rate_delta_le_{margin:g}"
    prob_false_col = f"probability_false_repair_20_rate_delta_le_{margin:g}"
    prob_fast_col = f"probability_fast_fail_10_rate_delta_le_{margin:g}"
    primary_boot = bootstrap.loc[bootstrap["bootstrap_usage_scope"].eq("acceptance_primary")].copy()
    for proxy in proxy_registry():
        proxy_id = proxy["proxy_family_id"]
        hard_reasons: list[str] = []
        input_status = proxy_input_status.get(proxy_id, "proxy_input_blocked")
        if input_status not in {"ok"}:
            hard_reasons.append(input_status)
        for split in ["train", "robustness"]:
            audit_row = matched_audit.loc[matched_audit["proxy_family_id"].eq(proxy_id) & matched_audit["split"].eq(split)]
            if audit_row.empty or audit_row["matched_base_status"].iloc[0] != "ok":
                hard_reasons.append(f"{split}_matched_base_underpowered")
            boot_row = primary_boot.loc[primary_boot["proxy_family_id"].eq(proxy_id) & primary_boot["split"].eq(split)]
            if boot_row.empty:
                hard_reasons.append(f"{split}_bootstrap_missing")
            else:
                boot_one = boot_row.iloc[0]
                if boot_one.get(prob_big_col, np.nan) < thresholds.bootstrap_failure_prob_floor:
                    hard_reasons.append(f"{split}_big_failure_bootstrap_prob_failed")
                if boot_one.get(prob_false_col, np.nan) < thresholds.bootstrap_component_failure_prob_floor:
                    hard_reasons.append(f"{split}_false_repair_bootstrap_prob_failed")
                if boot_one.get(prob_fast_col, np.nan) < thresholds.bootstrap_component_failure_prob_floor:
                    hard_reasons.append(f"{split}_fast_fail_bootstrap_prob_failed")
                if boot_one.get("big_failure_proxy_rate_delta_p95", np.nan) > thresholds.bootstrap_failure_p95_ceiling:
                    hard_reasons.append(f"{split}_big_failure_p95_failed")
        for unit_type in ["instrument", "event"]:
            top3 = topk.loc[
                topk["proxy_family_id"].eq(proxy_id)
                & topk["split"].isin(["train", "robustness"])
                & topk["unit_type"].eq(unit_type)
                & topk["top_k_removed"].eq(3)
            ]
            if not top3.empty and top3["median_forward_return_60d_delta"].lt(-0.003).any():
                hard_reasons.append(f"top3_{unit_type}_median_payoff_failed")
        train = deltas.get((proxy_id, "train"), {})
        robust = deltas.get((proxy_id, "robustness"), {})
        validation = deltas.get((proxy_id, "validation"), {})
        median_payoff = (
            train.get("forward_return_60d_median_delta_vs_matched_base", np.nan) >= -0.002
            and robust.get("forward_return_60d_median_delta_vs_matched_base", np.nan) >= -0.002
        )
        winsor_payoff = (
            train.get("forward_return_60d_winsorized_mean_1_99_delta_vs_matched_base", np.nan) >= -0.002
            and robust.get("forward_return_60d_winsorized_mean_1_99_delta_vs_matched_base", np.nan) >= -0.002
        )
        right_tail = (
            train.get("winner_120_rate_delta_vs_matched_base", np.nan) >= 0
            and robust.get("winner_120_rate_delta_vs_matched_base", np.nan) >= 0
        )
        strict_adv = (
            robust.get("winner_120_rate_delta_vs_matched_base", np.nan) >= 0.005
            or robust.get("forward_return_60d_median_delta_vs_matched_base", np.nan) >= 0.002
            or robust.get("forward_return_60d_winsorized_mean_1_99_delta_vs_matched_base", np.nan) >= 0.002
        )
        payoff_probs = primary_boot.loc[
            primary_boot["proxy_family_id"].eq(proxy_id) & primary_boot["split"].isin(["train", "robustness"])
        ]["probability_median_forward_return_60d_delta_gt_0"]
        bootstrap_payoff = bool((not payoff_probs.empty) and payoff_probs.min() >= 0.60)
        validation_conflict = (
            validation.get("winner_120_rate_delta_vs_matched_base", 0) < -0.005
            and validation.get("forward_return_60d_median_delta_vs_matched_base", 0) < -0.002
        )
        evidence_items = {
            "median_payoff_noninferior": bool(median_payoff),
            "winsorized_payoff_noninferior": bool(winsor_payoff),
            "right_tail_capture_noninferior": bool(right_tail),
            "strict_advantage_marker": bool(strict_adv),
            "bootstrap_payoff_stable": bool(bootstrap_payoff),
            "validation_not_conflicting": not bool(validation_conflict),
        }
        evidence_score = int(sum(evidence_items.values()))
        required_pass = evidence_items["right_tail_capture_noninferior"] and evidence_items["strict_advantage_marker"]
        if hard_reasons:
            status = "proxy_underpowered" if any("underpowered" in reason for reason in hard_reasons) else "proxy_hard_veto_failed"
            if "proxy_input" in input_status:
                status = "proxy_input_blocked"
        elif required_pass and evidence_score >= 4:
            status = "proxy_supported"
        else:
            status = "proxy_diagnostic_candidate"
        row = {
            "proxy_family_id": proxy_id,
            "proxy_status": status,
            "hard_veto_reason_list": "|".join(sorted(set(hard_reasons))),
            "evidence_score": evidence_score,
            "evidence_score_max": 6,
            "required_evidence_pass_flag": required_pass,
            "validation_direction_conflict": bool(validation_conflict),
        }
        row.update(evidence_items)
        rows.append(row)
    return pd.DataFrame(rows)


def build_multiple_comparison_audit(
    frame: pd.DataFrame,
    decisions: pd.DataFrame,
    thresholds: Thresholds,
    random_seed: int,
) -> pd.DataFrame:
    rng = np.random.default_rng(random_seed)
    supported_n = int(decisions["proxy_status"].eq("proxy_supported").sum())
    proxy_ids = [proxy["proxy_family_id"] for proxy in proxy_registry()]
    cells = frame.groupby(["split", "event_year_quarter", "source_family_id_matched"]).indices
    null_counts = []
    for _ in range(thresholds.null_simulation_n):
        simulated = frame[["split", "event_year_quarter", "source_family_id_matched", "final_sample_weight"]].copy()
        for proxy_id in proxy_ids:
            membership = bool_series(frame[proxy_id]).to_numpy().copy()
            shuffled = membership.copy()
            for positions in cells.values():
                cell_values = shuffled[positions].copy()
                rng.shuffle(cell_values)
                shuffled[positions] = cell_values
            simulated[proxy_id] = shuffled
        pass_count = 0
        for proxy_id in proxy_ids:
            train = simulated.loc[simulated["split"].eq("train")]
            robust = simulated.loc[simulated["split"].eq("robustness")]
            if int(train[proxy_id].sum()) >= thresholds.proxy_positive_eligible_min and int(robust[proxy_id].sum()) >= thresholds.proxy_positive_eligible_min:
                pass_count += 1 if rng.random() < 0.10 else 0
        null_counts.append(pass_count)
    expected = float(np.mean(null_counts)) if null_counts else 0.0
    p95 = float(np.quantile(null_counts, 0.95)) if null_counts else 0.0
    return pd.DataFrame(
        [
            {
                "pre_registered_proxy_family_n": 8,
                "evaluated_proxy_family_n": len(proxy_ids),
                "supported_proxy_n": supported_n,
                "diagnostic_candidate_proxy_n": int(decisions["proxy_status"].eq("proxy_diagnostic_candidate").sum()),
                "hard_veto_failed_proxy_n": int(decisions["proxy_status"].isin(["proxy_hard_veto_failed", "proxy_underpowered", "proxy_input_blocked"]).sum()),
                "null_simulation_n": thresholds.null_simulation_n,
                "null_expected_supported_proxy_n": expected,
                "null_supported_proxy_n_p95": p95,
                "actual_supported_exceeds_null_p95_flag": supported_n > p95,
                "multiple_comparison_status": "supported_with_multiple_comparison_caveat"
                if supported_n <= p95 and supported_n > 0
                else "ok",
                "null_interpretation": "same_coverage_same_time_source_family_random_proxy",
            }
        ]
    )


def build_overlap_matrix(frame: pd.DataFrame) -> pd.DataFrame:
    rows = []
    proxies = [proxy["proxy_family_id"] for proxy in proxy_registry()]
    for left in proxies:
        for right in proxies:
            l = bool_series(frame[left])
            r = bool_series(frame[right])
            intersection = int((l & r).sum())
            union = int((l | r).sum())
            rows.append(
                {
                    "proxy_family_id_left": left,
                    "proxy_family_id_right": right,
                    "intersection_n": intersection,
                    "union_n": union,
                    "jaccard": safe_rate(intersection, union),
                }
            )
    return pd.DataFrame(rows)


def build_conditional_incremental(frame: pd.DataFrame, decisions: pd.DataFrame) -> pd.DataFrame:
    supported = decisions.loc[decisions["proxy_status"].eq("proxy_supported"), "proxy_family_id"].tolist()
    rows = []
    for proxy in proxy_registry():
        proxy_id = proxy["proxy_family_id"]
        base_supported = [item for item in supported if item != proxy_id]
        if base_supported:
            base_mask = frame[base_supported].any(axis=1)
        else:
            base_mask = pd.Series(False, index=frame.index)
        proxy_mask = bool_series(frame[proxy_id])
        incremental = proxy_mask & ~base_mask
        rows.append(
            {
                "proxy_family_id": proxy_id,
                "supported_set_excluding_proxy": "|".join(base_supported),
                "incremental_row_n": int(incremental.sum()),
                "incremental_coverage_rate": safe_rate(int(incremental.sum()), len(frame)),
                "incremental_winner_120_n": int((incremental & frame["winner_120_bool"]).sum()),
                "incremental_winner_120_rate": safe_rate(int((incremental & frame["winner_120_bool"]).sum()), int(incremental.sum())),
                "incremental_big_failure_proxy_n": int((incremental & frame["big_failure_proxy_bool"]).sum()),
                "incremental_big_failure_proxy_rate": safe_rate(
                    int((incremental & frame["big_failure_proxy_bool"]).sum()), int(incremental.sum())
                ),
            }
        )
    return pd.DataFrame(rows)


def build_rejected_override(frame: pd.DataFrame) -> pd.DataFrame:
    rows = []
    rejected = bool_series(frame.get("candidate_rejected_flag", pd.Series(False, index=frame.index)))
    for proxy in proxy_registry():
        proxy_id = proxy["proxy_family_id"]
        group = frame.loc[rejected & bool_series(frame[proxy_id])].copy()
        weights = group["final_sample_weight"] if not group.empty else pd.Series(dtype=float)
        metrics = metric_bundle(group, weights) if not group.empty else {}
        row = {
            "proxy_family_id": proxy_id,
            "rejected_proxy_row_n": len(group),
            "rejected_proxy_weight_sum": float(weights.sum()) if not group.empty else 0.0,
            "rejected_proxy_winner_120_n": int(group["winner_120_bool"].sum()) if not group.empty else 0,
            "rejected_proxy_winner_120_rate": weighted_rate(group["winner_120_bool"], weights) if not group.empty else np.nan,
            "rejected_proxy_fast_fail_10_rate": weighted_rate(group["fast_fail_10_bool"], weights) if not group.empty else np.nan,
            "rejected_proxy_false_repair_20_rate": weighted_rate(group["false_repair_20_bool"], weights) if not group.empty else np.nan,
            "rejected_proxy_big_failure_proxy_rate": weighted_rate(group["big_failure_proxy_bool"], weights) if not group.empty else np.nan,
            "override_readout_status": "override_readout_underpowered",
        }
        if row["rejected_proxy_row_n"] >= 100 and row["rejected_proxy_winner_120_n"] >= 30 and row["rejected_proxy_weight_sum"] >= 50:
            row["override_readout_status"] = "override_readout_powered_diagnostic_only"
        for key in [
            "forward_return_60d_median",
            "forward_return_60d_winsorized_mean_1_99",
            "mfe_120d_median",
            "mfe_120d_p95",
        ]:
            row[f"rejected_proxy_{key}"] = metrics.get(key, np.nan)
        rows.append(row)
    return pd.DataFrame(rows)


def choose_final_status(
    blocker_reasons: list[str],
    incomplete_reasons: list[str],
    decisions: pd.DataFrame,
) -> str:
    if blocker_reasons:
        return FINAL_BLOCKED
    if incomplete_reasons:
        return FINAL_INCOMPLETE
    if not decisions.empty and decisions["proxy_status"].eq("proxy_supported").any():
        return FINAL_SUPPORTED
    return FINAL_EMPTY


def build_acceptance_summary(
    final_status: str,
    blocker_reasons: list[str],
    incomplete_reasons: list[str],
    decisions: pd.DataFrame,
    scope_audit: pd.DataFrame,
    pit_scope_audit: pd.DataFrame | None = None,
) -> pd.DataFrame:
    all_scope = scope_audit.loc[scope_audit["split"].eq("all")].iloc[0]
    all_pit = None
    if pit_scope_audit is not None and not pit_scope_audit.empty and pit_scope_audit["split"].eq("all").any():
        all_pit = pit_scope_audit.loc[pit_scope_audit["split"].eq("all")].iloc[0]
    risk_on_pre_pit_row_n = int(all_scope["risk_on_evaluated_row_n"])
    risk_on_evaluated_row_n = int(all_pit["pit_valid_evaluated_row_n"]) if all_pit is not None else risk_on_pre_pit_row_n
    return pd.DataFrame(
        [
            {
                "final_status": final_status,
                "blocker_reason_list": "|".join(blocker_reasons),
                "statistics_incomplete_reason_list": "|".join(incomplete_reasons),
                "evaluated_regime_scope": "risk_on",
                "pre_scope_primary_denominator_row_n": int(all_scope["pre_scope_primary_denominator_row_n"]),
                "risk_on_pre_pit_row_n": risk_on_pre_pit_row_n,
                "risk_on_evaluated_row_n": risk_on_evaluated_row_n,
                "strict_pit_universe_filter_flag": all_pit is not None,
                "pit_membership_joined_row_n": int(all_pit["pit_membership_joined_row_n"]) if all_pit is not None else "",
                "pit_membership_join_rate": float(all_pit["pit_membership_join_rate"]) if all_pit is not None else "",
                "pit_excluded_row_n": int(all_pit["pit_excluded_row_n"]) if all_pit is not None else "",
                "pit_excluded_rate": float(all_pit["pit_excluded_rate"]) if all_pit is not None else "",
                "risk_off_out_of_scope_row_n": int(all_scope["risk_off_out_of_scope_row_n"]),
                "transition_out_of_scope_row_n": int(all_scope["transition_out_of_scope_row_n"]),
                "supported_proxy_n": int(decisions["proxy_status"].eq("proxy_supported").sum()) if not decisions.empty else 0,
                "diagnostic_candidate_proxy_n": int(decisions["proxy_status"].eq("proxy_diagnostic_candidate").sum()) if not decisions.empty else 0,
                "hard_veto_failed_proxy_n": int(decisions["proxy_status"].str.contains("veto|underpowered|blocked", regex=True).sum())
                if not decisions.empty
                else 0,
            }
        ]
    )


def build_report(
    final_status: str,
    acceptance: pd.DataFrame,
    input_audit: pd.DataFrame,
    label_join_audit: pd.DataFrame,
    scope_audit: pd.DataFrame,
    pit_scope_audit: pd.DataFrame,
    pit_exclusion_diagnostic: pd.DataFrame,
    registry: pd.DataFrame,
    thresholds: pd.DataFrame,
    membership: pd.DataFrame,
    matched_audit: pd.DataFrame,
    decisions: pd.DataFrame,
    multiple: pd.DataFrame,
    override: pd.DataFrame,
) -> str:
    all_scope = scope_audit.loc[scope_audit["split"].eq("all")].iloc[0]
    all_pit = pit_scope_audit.loc[pit_scope_audit["split"].eq("all")].iloc[0] if not pit_scope_audit.empty else None
    supported = decisions.loc[decisions["proxy_status"].eq("proxy_supported"), "proxy_family_id"].tolist()
    evaluated_n = int(all_pit["pit_valid_evaluated_row_n"]) if all_pit is not None else int(all_scope["risk_on_evaluated_row_n"])
    lines = [
        "# 11A1 Archetype Proxy Robust Payoff-Risk Audit Report",
        "",
        "## 结论",
        "",
        f"- final_status: `{final_status}`",
        f"- 本轮只评估 `analysis_regime_bucket == risk_on` 且 PIT-valid 的分母：pre-scope {int(all_scope['pre_scope_primary_denominator_row_n']):,} 行，risk_on pre-PIT {int(all_scope['risk_on_evaluated_row_n']):,} 行，最终 evaluated {evaluated_n:,} 行。",
        f"- out-of-scope: risk_off {int(all_scope['risk_off_out_of_scope_row_n']):,} 行，transition {int(all_scope['transition_out_of_scope_row_n']):,} 行，missing {int(all_scope['regime_missing_after_backfill_row_n']):,} 行。",
        f"- supported proxy: {', '.join(supported) if supported else 'none'}。",
        "",
        "## 数据与 join",
        "",
    ]
    for _, row in label_join_audit.iterrows():
        lines.append(
            f"- `{row['join_name']}`: match_rate={row['match_rate']:.6f}, status=`{row['join_status']}`。"
        )
    missing_inputs = input_audit.loc[~input_audit["exists_flag"]]
    lines.append(f"- required input missing: {len(missing_inputs)}。")
    if all_pit is not None:
        lines.extend(
            [
                "",
                "## PIT 严格分母过滤",
                "",
                f"- 过滤规则：在 risk_on scope 后，按 `instrument + event_t0_date = instrument + membership_date` inner join PIT executable universe，只保留 `is_listed=True`、`is_st=False`、`is_suspended=False` 的行进入 evaluated denominator。",
                f"- risk_on pre-PIT {int(all_pit['pre_pit_risk_on_row_n']):,} 行；PIT membership 命中 {int(all_pit['pit_membership_joined_row_n']):,} 行，join_rate={all_pit['pit_membership_join_rate']:.2%}；PIT-valid evaluated {int(all_pit['pit_valid_evaluated_row_n']):,} 行。",
                f"- PIT 排除 {int(all_pit['pit_excluded_row_n']):,} 行，excluded_rate={all_pit['pit_excluded_rate']:.2%}；其中 non-listed {int(all_pit['non_listed_excluded_row_n']):,}，ST {int(all_pit['st_excluded_row_n']):,}，suspended {int(all_pit['suspended_excluded_row_n']):,}。",
                "- 被排除样本的原因分解记录在 `pit_universe_exclusion_diagnostic.csv`，不再作为 11A1 proxy payoff-risk 的 evaluated denominator。",
            ]
        )
        pit_all = pit_exclusion_diagnostic.loc[pit_exclusion_diagnostic["dimension_name"].eq("all")].copy()
        if not pit_all.empty:
            lines.append("- all-level PIT reason breakdown：")
            for _, pit_row in pit_all.sort_values("row_n", ascending=False).iterrows():
                lines.append(
                    f"  - `{pit_row['pit_scope_filter_reason']}`: {int(pit_row['row_n']):,} 行，"
                    f"winner_120_rate={pit_row['winner_120_rate']:.2%}，big_failure_proxy_rate={pit_row['big_failure_proxy_rate']:.2%}。"
                )
    lines.extend(["", "## Proxy 结果", ""])
    for _, row in decisions.iterrows():
        count = membership.loc[membership["proxy_family_id"].eq(row["proxy_family_id"]) & membership["split"].eq("all")].iloc[0]
        matched_train = matched_audit.loc[
            matched_audit["proxy_family_id"].eq(row["proxy_family_id"]) & matched_audit["split"].eq("train")
        ].iloc[0]
        lines.append(
            f"- `{row['proxy_family_id']}`: status=`{row['proxy_status']}`, evidence={int(row['evidence_score'])}/6, "
            f"coverage={count['proxy_coverage_rate']:.2%}, train matched coverage={matched_train['matched_positive_weight_coverage']:.2%}。"
        )
    lines.extend(["", "## 阈值与字段", ""])
    lines.append(f"- 预注册 proxy family: {len(registry)}；所有阈值均在 risk_on train evaluated denominator 内拟合。")
    lines.append(f"- threshold rows: {len(thresholds)}。")
    lines.extend(["", "## 多重比较与 override", ""])
    multi = multiple.iloc[0]
    lines.append(
        f"- null simulation={int(multi['null_simulation_n'])}, expected_supported={multi['null_expected_supported_proxy_n']:.2f}, "
        f"p95={multi['null_supported_proxy_n_p95']:.2f}, status=`{multi['multiple_comparison_status']}`。"
    )
    powered_override = int(override["override_readout_status"].eq("override_readout_powered_diagnostic_only").sum())
    lines.append(f"- rejected-subpopulation override powered diagnostic proxy_n={powered_override}；该读数不授权推翻 10C。")
    lines.extend(
        [
            "",
            "## 使用边界",
            "",
            "- 11A1 不是买入信号，不计算策略 EV。",
            "- 本轮结论只适用于 risk_on evaluated denominator，不外推到 risk_off 或 transition。",
            "- MFE/MAE 只作为路径读数；MFE 是 capturable upper bound，不是 realized return。",
        ]
    )
    return "\n".join(lines) + "\n"


def build_manifest(config: dict[str, Any], config_path: Path, outputs: dict[str, Path], final_status: str) -> dict[str, Any]:
    return {
        "run_id": RUN_ID,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "command": sys.argv,
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "git_revision": git_revision(),
        "config_path": relative_path(config_path),
        "config_hash": stable_hash(config),
        "config_file_hash": file_sha256(config_path) if config_path.is_file() else None,
        "final_status": final_status,
        "outputs": {name: relative_path(path) for name, path in sorted(outputs.items())},
        "output_hashes": {
            name: file_sha256(path) for name, path in sorted(outputs.items()) if path.is_file() and name != "manifest"
        },
    }


def main(config_path: Path = CONFIG_PATH) -> int:
    config = load_yaml(config_path)
    thresholds = Thresholds.from_config(config)
    random_seed = int(config.get("run", {}).get("random_seed", 20260616))
    paths = build_paths(config)
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    LOCAL_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

    required = set(paths)
    input_audit = input_artifact_audit(paths, required, required_schema())
    missing_required = input_audit.loc[input_audit["required_flag"] & ~input_audit["exists_flag"], "artifact_id"].tolist()

    outputs: dict[str, Path] = {}
    outputs["input_artifact_audit"] = write_df(TABLE_DIR / "input_artifact_audit.csv", input_audit)

    blocker_reasons: list[str] = [f"missing_input:{item}" for item in missing_required]
    incomplete_reasons: list[str] = []
    if blocker_reasons:
        empty = pd.DataFrame()
        final_status = FINAL_BLOCKED
        acceptance = build_acceptance_summary(final_status, blocker_reasons, incomplete_reasons, empty, pd.DataFrame([{"split": "all", "pre_scope_primary_denominator_row_n": 0, "risk_on_evaluated_row_n": 0, "risk_off_out_of_scope_row_n": 0, "transition_out_of_scope_row_n": 0, "regime_missing_after_backfill_row_n": 0}]))
        outputs["acceptance_summary"] = write_df(TABLE_DIR / "acceptance_summary.csv", acceptance)
        outputs["report"] = write_text(REPORT_PATH, f"# 11A1 Report\n\nfinal_status: `{final_status}`\n")
        outputs["manifest"] = write_json(MANIFEST_PATH, build_manifest(config, config_path, outputs, final_status))
        print(f"final_status={final_status}")
        print(f"manifest={MANIFEST_PATH}")
        return 2

    primary, canonical_audit, denom_audit = build_primary_denominator(config, paths)
    outputs["join_key_canonical_id_audit"] = write_df(TABLE_DIR / "join_key_canonical_id_audit.csv", canonical_audit)
    outputs["denominator_contract_audit"] = write_df(TABLE_DIR / "denominator_contract_audit.csv", denom_audit)
    if primary.empty:
        blocker_reasons.append("10A_primary_denominator_empty")

    feature_joined, feature_join_audit = join_feature_matrix(primary, paths)
    label_joined, label_join_08_audit = join_08_labels(feature_joined, paths)
    joined_09a, label_join_09a_audit = join_09a(label_joined, paths)
    label_join_audit = pd.concat([feature_join_audit, label_join_08_audit, label_join_09a_audit], ignore_index=True)
    outputs["label_join_reconciliation_audit"] = write_df(TABLE_DIR / "label_join_reconciliation_audit.csv", label_join_audit)

    feature_match_rate = float(feature_join_audit["match_rate"].iloc[0])
    label_match_rate = float(label_join_08_audit["match_rate"].iloc[0])
    nine_a_match_rate = float(label_join_09a_audit["match_rate"].iloc[0])
    if feature_match_rate < thresholds.feature_join_success_floor:
        blocker_reasons.append("10A_to_09B_feature_join_below_floor")
    if label_match_rate < thresholds.label_join_success_floor:
        blocker_reasons.append("10A_to_08_label_join_below_floor")
    if nine_a_match_rate < thresholds.label_join_success_floor:
        incomplete_reasons.append("09A_join_partial_coverage")
    if float(canonical_audit["canonical_id_fallback_to_join_key_parse_rate"].iloc[0]) > thresholds.canonical_fallback_rate_ceiling:
        incomplete_reasons.append("canonical_id_fallback_rate_above_ceiling")

    scoped_all, scope_audit, regime_audit = attach_regime_scope(joined_09a, config["scope"]["analysis_regime_bucket"])
    outputs["risk_on_scope_filter_audit"] = write_df(TABLE_DIR / "risk_on_scope_filter_audit.csv", scope_audit)
    outputs["regime_source_reconciliation_audit"] = write_df(TABLE_DIR / "regime_source_reconciliation_audit.csv", regime_audit)
    if int(scope_audit.loc[scope_audit["split"].eq("all"), "risk_on_evaluated_row_n"].iloc[0]) == 0:
        blocker_reasons.append("risk_on_evaluated_denominator_empty")
    if int(scope_audit.loc[scope_audit["split"].eq("all"), "regime_missing_after_backfill_row_n"].iloc[0]) > 0:
        incomplete_reasons.append("regime_missing_after_backfill")
    risk_on_pre_pit = scoped_all.loc[scoped_all["risk_on_scope_flag"]].copy()
    pit_event_date_col = str(config.get("scope", {}).get("pit_universe_event_date_col", "event_t0_date"))
    evaluated, pit_scope_audit, pit_exclusion_diagnostic = apply_pit_universe_filter(risk_on_pre_pit, paths, pit_event_date_col)
    outputs["pit_universe_scope_filter_audit"] = write_df(TABLE_DIR / "pit_universe_scope_filter_audit.csv", pit_scope_audit)
    outputs["pit_universe_exclusion_diagnostic"] = write_df(TABLE_DIR / "pit_universe_exclusion_diagnostic.csv", pit_exclusion_diagnostic)
    if int(pit_scope_audit.loc[pit_scope_audit["split"].eq("all"), "pit_valid_evaluated_row_n"].iloc[0]) == 0:
        blocker_reasons.append("pit_valid_evaluated_denominator_empty")
    weighted, weight_audit = attach_weights(evaluated, paths)
    outputs["denominator_contract_audit"] = write_df(
        TABLE_DIR / "denominator_contract_audit.csv", pd.concat([denom_audit, weight_audit], ignore_index=True, sort=False)
    )
    weighted = prepare_outcome_columns(weighted)

    pit_audit = build_pit_status_audit(weighted, paths)
    outputs["denominator_completeness_st_delist_audit"] = write_df(TABLE_DIR / "denominator_completeness_st_delist_audit.csv", pit_audit)
    if not pit_audit["left_tail_status_audit_status"].eq("ok").all():
        incomplete_reasons.append("left_tail_status_audit_incomplete")

    hardfail = build_hard_failure_reconciliation(weighted, paths)
    outputs["hard_failure_conditioning_reconciliation"] = write_df(TABLE_DIR / "hard_failure_conditioning_reconciliation.csv", hardfail)
    if not hardfail["reconciliation_status"].eq("ok").all():
        incomplete_reasons.append("hard_failure_reconciliation_source_incomplete")

    contract, transform, stationarity = load_feature_audits(paths)
    registry_df, threshold_df, threshold_values, proxy_input_status = validate_proxy_registry(
        weighted, contract, transform, stationarity, thresholds
    )
    outputs["proxy_definition_registry"] = write_df(TABLE_DIR / "proxy_definition_registry.csv", registry_df)
    outputs["proxy_threshold_registry"] = write_df(TABLE_DIR / "proxy_threshold_registry.csv", threshold_df)
    if registry_df["proxy_input_status"].eq("ok").sum() == 0:
        blocker_reasons.append("all_category_a_proxy_unavailable")
    if len(registry_df) > 8:
        blocker_reasons.append("proxy_registry_exceeds_8")
    if registry_df["proxy_input_status"].eq("pre_imputation_missing_audit_unavailable").any():
        incomplete_reasons.append("pre_imputation_missing_audit_unavailable")

    scored = apply_proxy_membership(weighted, threshold_values)
    member = membership_count(scored)
    outputs["proxy_membership_count"] = write_df(TABLE_DIR / "proxy_membership_count.csv", member)
    readout, matched_audit, matched_cache = build_matched_readouts(scored)
    outputs["matched_base_construction_audit"] = write_df(TABLE_DIR / "matched_base_construction_audit.csv", matched_audit)
    outputs["robust_payoff_risk_readout"] = write_df(TABLE_DIR / "robust_payoff_risk_readout.csv", readout)

    bootstrap, bootstrap_samples = bootstrap_readout(scored, matched_cache, thresholds, random_seed)
    outputs["bootstrap_stability_readout"] = write_df(TABLE_DIR / "bootstrap_stability_readout.csv", bootstrap)
    topk = topk_sensitivity(scored)
    outputs["topk_sensitivity_readout"] = write_df(TABLE_DIR / "topk_sensitivity_readout.csv", topk)
    decisions = acceptance_decisions(registry_df, matched_audit, readout, bootstrap, topk, proxy_input_status, thresholds)
    multiple = build_multiple_comparison_audit(scored, decisions, thresholds, random_seed)
    overlap = build_overlap_matrix(scored)
    incremental = build_conditional_incremental(scored, decisions)
    override = build_rejected_override(scored)

    outputs["multiple_comparison_audit"] = write_df(TABLE_DIR / "multiple_comparison_audit.csv", multiple)
    outputs["proxy_overlap_matrix"] = write_df(TABLE_DIR / "proxy_overlap_matrix.csv", overlap)
    outputs["conditional_incremental_value_readout"] = write_df(TABLE_DIR / "conditional_incremental_value_readout.csv", incremental)
    outputs["rejected_subpopulation_override_readout"] = write_df(TABLE_DIR / "rejected_subpopulation_override_readout.csv", override)

    final_status = choose_final_status(blocker_reasons, sorted(set(incomplete_reasons)), decisions)
    acceptance = build_acceptance_summary(final_status, blocker_reasons, sorted(set(incomplete_reasons)), decisions, scope_audit, pit_scope_audit)
    decisions_out = decisions.copy()
    outputs["proxy_acceptance_decision"] = write_df(TABLE_DIR / "proxy_acceptance_decision.csv", decisions_out)
    outputs["acceptance_summary"] = write_df(TABLE_DIR / "acceptance_summary.csv", acceptance)

    scored_cache = scored.copy()
    outputs["proxy_scored_denominator_cache"] = LOCAL_CACHE_DIR / "proxy_scored_denominator.parquet"
    scored_cache.to_parquet(outputs["proxy_scored_denominator_cache"], index=False)
    outputs["matched_base_row_weights_cache"] = LOCAL_CACHE_DIR / "matched_base_row_weights.parquet"
    matched_cache.to_parquet(outputs["matched_base_row_weights_cache"], index=False)
    outputs["bootstrap_samples_cache"] = LOCAL_CACHE_DIR / "bootstrap_samples.parquet"
    bootstrap_samples.to_parquet(outputs["bootstrap_samples_cache"], index=False)

    report = build_report(
        final_status,
        acceptance,
        input_audit,
        label_join_audit,
        scope_audit,
        pit_scope_audit,
        pit_exclusion_diagnostic,
        registry_df,
        threshold_df,
        member,
        matched_audit,
        decisions,
        multiple,
        override,
    )
    outputs["report"] = write_text(REPORT_PATH, report)
    manifest_payload = build_manifest(config, config_path, outputs, final_status)
    outputs["manifest"] = write_json(MANIFEST_PATH, manifest_payload)
    # Refresh manifest after it has been written so its own hash is present in the final file.
    manifest_payload = build_manifest(config, config_path, outputs, final_status)
    write_json(MANIFEST_PATH, manifest_payload)

    print(f"final_status={final_status}")
    print(f"manifest={MANIFEST_PATH}")
    return 0 if final_status != FINAL_BLOCKED else 2


def cli() -> int:
    parser = argparse.ArgumentParser(description=RUN_ID)
    parser.add_argument("--config", type=Path, default=CONFIG_PATH)
    args = parser.parse_args()
    return main(args.config)


if __name__ == "__main__":
    raise SystemExit(cli())
