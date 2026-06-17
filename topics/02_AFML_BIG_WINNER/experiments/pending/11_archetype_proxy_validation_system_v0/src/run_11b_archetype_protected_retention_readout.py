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


RUN_ID = "11B_archetype_protected_retention_readout"
CONFIG_PATH = EXPERIMENT_DIR / "configs" / "config_11b_archetype_protected_retention_readout.yaml"
TABLE_DIR = EXPERIMENT_DIR / "outputs" / "publishable" / "tables" / RUN_ID
LOCAL_CACHE_DIR = EXPERIMENT_DIR / "outputs" / "local_cache" / RUN_ID
REPORT_PATH = EXPERIMENT_DIR / "outputs" / "publishable" / "reports" / f"{RUN_ID}_report.md"
MANIFEST_PATH = EXPERIMENT_DIR / "outputs" / "publishable" / f"manifest_{RUN_ID}.json"

FINAL_NON_DISCRIMINATORY = "11B_archetype_protected_retention_non_discriminatory"
FINAL_DISCRIMINATORY = "11B_archetype_protected_retention_discriminatory"
FINAL_AMBIGUOUS = "11B_archetype_protected_retention_ambiguous"
FINAL_UNDERPOWERED = "11B_archetype_protected_retention_inconclusive_underpowered"
FINAL_MIXED_POWER = "11B_archetype_protected_retention_inconclusive_mixed_power"
FINAL_INCOMPLETE = "11B_archetype_protected_retention_statistics_incomplete"
FINAL_BLOCKED = "11B_archetype_protected_retention_input_blocked"

PRIMARY_SPLITS = ["train", "validation", "robustness"]
READOUT_SPLITS = ["all", "train", "validation", "robustness"]
GATE_SPLITS = ["train", "robustness"]
VALID_REGIMES = {"risk_on", "risk_off", "transition"}
REJECT_JOIN_KEY = ["sample_id", "selected_target_id", "denominator_id", "input_event_key"]
SLICE_FIELDS = ["model_id", "ablation_id", "capacity_id", "threshold_id", "population_id", "denominator_id"]
CONFIG_PARAM_DEFAULTS: dict[str, Any] = {
    "relative_retention_floor": 0.90,
    "retention_min_winner_n": 60,
    "retention_min_winner_instrument_n": 30,
    "validation_min_class_n": 30,
    "validation_min_instrument_n": 20,
    "denominator_drift_ceiling": 0.005,
    "retention_recon_abs_diff_ceiling": 0.02,
    "class_unresolved_ceiling": 0.30,
    "bootstrap_n": 1000,
    "bootstrap_seed": 20260617,
    "multiple_comparison_null_n": 500,
    "multiple_comparison_null_seed": 20260617,
}


@dataclass(frozen=True)
class Params:
    relative_retention_floor: float = 0.90
    retention_min_winner_n: int = 60
    retention_min_winner_instrument_n: int = 30
    validation_min_class_n: int = 30
    validation_min_instrument_n: int = 20
    denominator_drift_ceiling: float = 0.005
    retention_recon_abs_diff_ceiling: float = 0.02
    class_unresolved_ceiling: float = 0.30
    bootstrap_n: int = 1000
    bootstrap_seed: int = 20260617
    multiple_comparison_null_n: int = 500
    multiple_comparison_null_seed: int = 20260617

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> "Params":
        raw = config.get("parameters", {})
        values = {field: raw.get(field, getattr(cls(), field)) for field in cls.__dataclass_fields__}
        return cls(**values)


def git_revision(cwd: Path = REPO_ROOT) -> str | None:
    try:
        result = subprocess.run(["git", "rev-parse", "HEAD"], cwd=cwd, check=True, capture_output=True, text=True)
    except (OSError, subprocess.CalledProcessError):
        return None
    return result.stdout.strip()


def write_df(path: Path, frame: pd.DataFrame) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False)
    return path


def write_parquet(path: Path, frame: pd.DataFrame) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(path, index=False)
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
    except Exception:
        return ""
    return ""


def nonempty(value: Any) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except TypeError:
        pass
    return str(value).strip()


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


def safe_rate(numerator: int | float, denominator: int | float) -> float:
    if denominator == 0 or pd.isna(denominator):
        return float("nan")
    return float(numerator) / float(denominator)


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


def parse_canonical_from_pipe(value: Any) -> str:
    parts = nonempty(value).split("|")
    if len(parts) >= 4:
        return parts[3].strip()
    return ""


def make_09a_join_key(frame: pd.DataFrame, denominator_col: str, canonical_col: str) -> pd.Series:
    return (
        frame["sample_id"].astype(str)
        + "|"
        + frame["selected_target_id"].astype(str)
        + "|"
        + frame[denominator_col].astype(str)
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


def split_frame(frame: pd.DataFrame, split: str) -> pd.DataFrame:
    if split == "all":
        return frame
    return frame.loc[frame["split"].astype(str).eq(split)]


def build_paths(config: dict[str, Any]) -> dict[str, Path]:
    return {key: resolve_path(value) for key, value in config.get("inputs", {}).items()}


def required_inputs() -> set[str]:
    return {
        "discussion_next_step",
        "requirement_11a1",
        "requirement_11a2",
        "report_11a1",
        "report_11a2",
        "eleven_a1_scope_risk_on",
        "eleven_a1_scope_pit",
        "eleven_a1_acceptance_summary",
        "eleven_a1_denominator_contract",
        "eleven_a1_denominator_completeness",
        "eleven_a2_scope_reconciliation",
        "eleven_a2_outcome_class_count",
        "ten_a_manifest",
        "ten_a_bindings",
        "ten_a_population_contract",
        "nine_b_feature_contract",
        "nine_b_feature_matrix",
        "nine_b_sample_weights",
        "eight_labels",
        "eight_manifest",
        "nine_a_bindings",
        "labels_yaml",
        "ten_c_manifest",
        "ten_c_scores",
        "ten_c_threshold_frontier",
        "ten_c_winner_retention_audit",
        "pit_universe",
        "board_metadata",
        "sh_name_history_dir",
        "sz_name_history",
    }


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
            "sample_id",
            "selected_target_id",
            "instrument",
            "event_t0_date",
            "split",
            "feature_matrix_join_key",
        ],
        "ten_c_scores": [
            "model_id",
            "ablation_id",
            "capacity_id",
            "threshold_id",
            "population_id",
            "denominator_id",
            "input_event_key",
            "sample_id",
            "selected_target_id",
        ],
        "ten_c_threshold_frontier": [
            "model_id",
            "ablation_id",
            "capacity_id",
            "threshold_id",
            "train_winner_retention",
            "validation_winner_retention",
            "robustness_winner_retention",
        ],
        "eleven_a1_proxy_scored_denominator": [
            *REJECT_JOIN_KEY,
            "split",
            "instrument",
            "event_t0_date",
            "binding_canonical_event_id",
            "winner_120",
            "horizon_complete_120d",
            "final_sample_weight",
        ],
        "eleven_a1_scope_risk_on": ["split", "pre_scope_primary_denominator_row_n", "risk_on_evaluated_row_n"],
        "eleven_a1_scope_pit": ["split", "pre_pit_risk_on_row_n", "pit_valid_evaluated_row_n"],
        "eleven_a2_scope_reconciliation": ["split", "a2_risk_on_pre_pit_row_n", "a2_pit_valid_evaluated_row_n"],
    }


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
        elif artifact_id in required and not exists:
            failure_reason = "required_input_missing"
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
                "row_count": row_count,
                "schema_status": schema_status,
                "failure_reason": failure_reason,
            }
        )
    return pd.DataFrame(rows)


def validate_config_contract(config: dict[str, Any]) -> pd.DataFrame:
    params = config.get("parameters", {})
    rows = []
    for key, default in CONFIG_PARAM_DEFAULTS.items():
        exists = key in params
        value = params.get(key, "")
        rows.append(
            {
                "config_key": key,
                "expected_default": default,
                "configured_value": value,
                "present_flag": exists,
                "matches_preregistered_default_flag": exists and value == default,
                "config_contract_status": "ok" if exists else "missing_config_key",
            }
        )
    return pd.DataFrame(rows)


def select_rejector_slice_mode(manifest: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    scope = config["scope"]
    reference = scope["reference_slice"]
    selected_supported = (
        nonempty(manifest.get("selected_capacity_id")) != ""
        and nonempty(manifest.get("selected_threshold_id")) != ""
        and nonempty(manifest.get("selected_cascade_status")) == "supported"
    )
    if selected_supported:
        return {
            "rejector_slice_mode": "selected_gate",
            "model_id": nonempty(manifest.get("selected_model_id")) or reference["model_id"],
            "ablation_id": nonempty(manifest.get("selected_ablation_id")) or reference["ablation_id"],
            "capacity_id": nonempty(manifest.get("selected_capacity_id")),
            "threshold_id": nonempty(manifest.get("selected_threshold_id")),
            "population_id": nonempty(manifest.get("selected_population_id")) or reference["population_id"],
            "denominator_id": nonempty(manifest.get("selected_denominator_id")) or reference["denominator_id"],
        }
    return {"rejector_slice_mode": "keep_9000_reference_slice", **reference}


def filter_rejector_slice(scores: pd.DataFrame, slice_spec: dict[str, Any]) -> pd.DataFrame:
    mask = pd.Series(True, index=scores.index)
    for field in SLICE_FIELDS:
        mask &= scores[field].astype(str).eq(str(slice_spec[field]))
    out = scores.loc[mask].copy()
    if "event_t0_date" in out.columns:
        out["event_t0_date"] = pd.to_datetime(out["event_t0_date"], errors="coerce").dt.strftime("%Y-%m-%d")
    return out


def materialize_reject_decision(reject_slice: pd.DataFrame) -> tuple[pd.DataFrame, str, float]:
    out = reject_slice.copy()
    if out.empty:
        out["reject_decision_flag"] = pd.Series(dtype=object)
        out["reject_flag_reconstructed_from_threshold"] = pd.Series(dtype=bool)
        return out, "unavailable_empty_slice", 0.0

    if "candidate_rejected_flag" in out.columns and out["candidate_rejected_flag"].notna().any():
        available = out["candidate_rejected_flag"].notna()
        out["reject_decision_flag"] = bool_series(out["candidate_rejected_flag"]).where(available, np.nan)
        out["reject_flag_reconstructed_from_threshold"] = False
        return out, "10C_candidate_rejected_flag", safe_rate(int(available.sum()), len(out))

    if {"candidate_rank", "reject_fraction", "split"}.issubset(out.columns):
        reconstructed = pd.Series(False, index=out.index, dtype=bool)
        usable = pd.Series(False, index=out.index, dtype=bool)
        for _, group in out.groupby("split", dropna=False):
            reject_fraction = pd.to_numeric(group["reject_fraction"], errors="coerce").dropna()
            ranks = pd.to_numeric(group["candidate_rank"], errors="coerce")
            if reject_fraction.empty or ranks.notna().sum() == 0:
                continue
            reject_n = int(math.ceil(len(group) * float(reject_fraction.iloc[0])))
            idx = group.index[ranks.notna()]
            reconstructed.loc[idx] = ranks.loc[idx].le(reject_n)
            usable.loc[idx] = True
        out["reject_decision_flag"] = reconstructed.where(usable, np.nan)
        out["reject_flag_reconstructed_from_threshold"] = usable
        return out, "reject_flag_reconstructed_from_rank_reject_fraction", safe_rate(int(usable.sum()), len(out))

    out["reject_decision_flag"] = np.nan
    out["reject_flag_reconstructed_from_threshold"] = False
    return out, "reject_decision_unavailable", 0.0


def frontier_slice_row(frontier: pd.DataFrame, slice_spec: dict[str, Any]) -> pd.Series | None:
    mask = pd.Series(True, index=frontier.index)
    for field in ["model_id", "ablation_id", "capacity_id", "threshold_id"]:
        if field in frontier.columns:
            mask &= frontier[field].astype(str).eq(str(slice_spec[field]))
    subset = frontier.loc[mask]
    if subset.empty:
        return None
    return subset.iloc[0]


def build_primary_denominator(config: dict[str, Any], paths: dict[str, Path], reject_slice: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
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
    primary["event_t0_date"] = pd.to_datetime(primary["event_t0_date"], errors="coerce").dt.strftime("%Y-%m-%d")
    primary["row_id"] = np.arange(len(primary), dtype=np.int64)

    ref_cols = [
        "input_event_key",
        "sample_id",
        "selected_target_id",
        "instrument",
        "event_t0_date",
        "binding_canonical_event_id",
    ]
    ref_cols = [col for col in ref_cols if col in reject_slice.columns]
    if ref_cols:
        ref = reject_slice[ref_cols].drop_duplicates(ref_cols)
        primary = primary.merge(
            ref,
            on=["input_event_key", "sample_id", "selected_target_id", "instrument", "event_t0_date"],
            how="left",
            validate="1:1",
        )
    else:
        primary["binding_canonical_event_id"] = ""

    parsed = primary["feature_matrix_join_key"].map(parse_canonical_from_pipe) if "feature_matrix_join_key" in primary.columns else pd.Series([""] * len(primary), index=primary.index)
    from_10c = primary.get("binding_canonical_event_id", pd.Series([""] * len(primary), index=primary.index)).map(nonempty)
    primary["binding_canonical_event_id"] = from_10c.mask(from_10c.eq(""), parsed)
    primary["canonical_id_source"] = np.select(
        [from_10c.ne(""), parsed.ne("")],
        ["10C.reference_slice_join", "feature_matrix_join_key_parse_fallback"],
        default="missing",
    )

    primary = attach_08_labels(primary, paths)
    primary = attach_09a_regime(primary, paths, config["scope"]["analysis_regime_bucket"])

    audit = pd.DataFrame(
        [
            {
                "denominator_layer": "score_cache_primary_denominator",
                "population_id": scope["population_id"],
                "rule_arm_id": scope["rule_arm_id"],
                "input_denominator_id": scope["input_denominator_id"],
                "denominator_id": scope["denominator_id"],
                "admission_status": scope["admission_status"],
                "readout_only_flag": scope["readout_only_flag"],
                "row_n": len(primary),
                "train_row_n": int(primary["split"].astype(str).eq("train").sum()),
                "validation_row_n": int(primary["split"].astype(str).eq("validation").sum()),
                "robustness_row_n": int(primary["split"].astype(str).eq("robustness").sum()),
                "canonical_id_missing_n": int(primary["binding_canonical_event_id"].map(nonempty).eq("").sum()),
                "denominator_status": "ok" if len(primary) > 0 else "primary_denominator_empty",
            }
        ]
    )
    return primary, audit


def attach_08_labels(frame: pd.DataFrame, paths: dict[str, Path]) -> pd.DataFrame:
    labels = read_parquet_columns(
        paths["eight_labels"],
        [
            "event_id",
            "instrument",
            "event_t0_date",
            "event_split",
            "winner_120",
            "horizon_complete_120d",
            "event_big_winner_120d_label",
        ],
    ).copy()
    if labels.empty:
        return frame
    labels["event_t0_date"] = pd.to_datetime(labels["event_t0_date"], errors="coerce").dt.strftime("%Y-%m-%d")
    labels = labels.sort_values("event_id").drop_duplicates("event_id", keep="first")
    labels = labels.rename(
        columns={
            "instrument": "label_instrument_08",
            "event_t0_date": "label_event_t0_date_08",
            "event_split": "label_event_split_08",
            "winner_120": "winner_120_08",
            "horizon_complete_120d": "horizon_complete_120d_08",
        }
    )
    joined = frame.merge(labels, left_on="binding_canonical_event_id", right_on="event_id", how="left", validate="m:1")
    if "horizon_complete_120d" not in joined.columns:
        joined["horizon_complete_120d"] = joined.get("horizon_complete_120d_08", True)
    else:
        joined["horizon_complete_120d"] = joined["horizon_complete_120d"].where(
            joined["horizon_complete_120d"].notna(), joined.get("horizon_complete_120d_08", True)
        )
    if "winner_120" not in joined.columns:
        joined["winner_120"] = joined.get("winner_120_08", False)
    else:
        joined["winner_120"] = joined["winner_120"].where(joined["winner_120"].notna(), joined.get("winner_120_08", False))
    return joined


def attach_09a_regime(frame: pd.DataFrame, paths: dict[str, Path], scope_regime: str) -> pd.DataFrame:
    bindings = read_parquet_columns(
        paths["nine_a_bindings"],
        [
            "sample_id",
            "selected_target_id",
            "denominator_id",
            "canonical_event_id",
            "instrument",
            "event_t0_date",
            "event_split",
            "event_regime_bucket",
            "episode_regime_bucket",
        ],
    ).copy()
    if bindings.empty:
        work = frame.copy()
        work["analysis_regime_bucket"], work["analysis_regime_source"] = coalesce_regime(work, ["event_regime_bucket"])
        work["analysis_regime_bucket"] = work["analysis_regime_bucket"].replace("", "regime_missing_after_backfill")
        work["risk_on_scope_flag"] = work["analysis_regime_bucket"].eq(scope_regime)
        return work
    bindings["event_t0_date"] = pd.to_datetime(bindings["event_t0_date"], errors="coerce").dt.strftime("%Y-%m-%d")
    bindings["_09a_join_key"] = make_09a_join_key(bindings, "denominator_id", "canonical_event_id")
    bindings = bindings.sort_values("_09a_join_key").drop_duplicates("_09a_join_key", keep="first")
    bindings = bindings.rename(
        columns={
            "instrument": "instrument_09a",
            "event_t0_date": "event_t0_date_09a",
            "event_split": "event_split_09a",
            "event_regime_bucket": "event_regime_bucket_09a",
            "episode_regime_bucket": "episode_regime_bucket_09a",
        }
    )
    work = frame.copy()
    work["_09a_join_key"] = make_09a_join_key(work, "input_denominator_id", "binding_canonical_event_id")
    joined = work.merge(bindings, on="_09a_join_key", how="left", validate="m:1", suffixes=("", "_09a_raw"))
    joined["analysis_regime_bucket"], joined["analysis_regime_source"] = coalesce_regime(
        joined, ["episode_regime_bucket_09a", "event_regime_bucket", "event_regime_bucket_09a"]
    )
    joined["analysis_regime_bucket"] = joined["analysis_regime_bucket"].replace("", "regime_missing_after_backfill")
    joined["risk_on_scope_flag"] = joined["analysis_regime_bucket"].eq(scope_regime)
    return joined


def load_evaluated_denominator(paths: dict[str, Path], risk_on_pre_pit: pd.DataFrame) -> pd.DataFrame:
    cache = paths.get("eleven_a1_proxy_scored_denominator")
    if cache and cache.exists():
        evaluated = pd.read_parquet(cache).copy()
        evaluated["event_t0_date"] = pd.to_datetime(evaluated["event_t0_date"], errors="coerce").dt.strftime("%Y-%m-%d")
        return evaluated
    return apply_strict_pit_filter(risk_on_pre_pit, paths)


def apply_strict_pit_filter(frame: pd.DataFrame, paths: dict[str, Path]) -> pd.DataFrame:
    pit = pd.read_csv(
        paths["pit_universe"],
        usecols=lambda col: col
        in {"membership_date", "instrument", "is_listed", "is_st", "is_suspended", "board_bucket", "usable_trade_date"},
        dtype={"instrument": str},
        low_memory=False,
    )
    pit["membership_date"] = pd.to_datetime(pit["membership_date"], errors="coerce").dt.strftime("%Y-%m-%d")
    pit = pit.drop_duplicates(["instrument", "membership_date"], keep="first")
    join = frame.merge(
        pit.rename(columns={"instrument": "pit_instrument", "membership_date": "pit_membership_date"}),
        left_on=["instrument", "event_t0_date"],
        right_on=["pit_instrument", "pit_membership_date"],
        how="left",
        validate="m:1",
    )
    valid = bool_series(join["is_listed"]) & ~bool_series(join["is_st"]) & ~bool_series(join["is_suspended"])
    out = join.loc[valid].copy()
    out["pit_valid_executable_flag"] = True
    return out


def attach_reject_decision(frame: pd.DataFrame, reject_slice: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    if "reject_decision_flag" not in reject_slice.columns:
        reject_slice, _, _ = materialize_reject_decision(reject_slice)
    right_cols = [
        *REJECT_JOIN_KEY,
        "instrument",
        "event_t0_date",
        "split",
        "binding_canonical_event_id",
        "reject_decision_flag",
        "reject_flag_reconstructed_from_threshold",
        "candidate_false_repair_score",
        "candidate_rank",
        "cascade_bucket",
        "winner_120",
    ]
    right_cols = [col for col in right_cols if col in reject_slice.columns]
    right = reject_slice[right_cols].copy()
    rename = {col: f"{col}_10c" for col in right.columns if col not in REJECT_JOIN_KEY}
    right = right.rename(columns=rename)
    joined = frame.merge(right, on=REJECT_JOIN_KEY, how="left", validate="1:1", indicator="_reject_merge")

    decision_col = "reject_decision_flag_10c"
    available = joined[decision_col].notna() if decision_col in joined.columns else pd.Series(False, index=joined.index)
    rejected = bool_series(joined[decision_col]) if decision_col in joined.columns else pd.Series(False, index=joined.index)
    joined["reject_decision_available_flag"] = available
    joined["rejected_flag"] = rejected & available
    joined["retained_flag"] = (~joined["rejected_flag"]) & available
    reconstructed_col = "reject_flag_reconstructed_from_threshold_10c"
    reconstructed = bool_series(joined[reconstructed_col]) if reconstructed_col in joined.columns else pd.Series(False, index=joined.index)
    joined["reject_flag_reconstructed_from_threshold"] = reconstructed & available
    joined["reject_decision_source"] = np.select(
        [available & joined["reject_flag_reconstructed_from_threshold"], available],
        ["reject_flag_reconstructed_from_threshold", "10C_candidate_rejected_flag"],
        default="missing",
    )

    mismatch = {
        "instrument_mismatch_n": int(
            (available & joined.get("instrument_10c", joined["instrument"]).astype(str).ne(joined["instrument"].astype(str))).sum()
        ),
        "event_t0_date_mismatch_n": int(
            (
                available
                & pd.to_datetime(joined.get("event_t0_date_10c", joined["event_t0_date"]), errors="coerce")
                .dt.strftime("%Y-%m-%d")
                .ne(pd.to_datetime(joined["event_t0_date"], errors="coerce").dt.strftime("%Y-%m-%d"))
            ).sum()
        ),
        "split_mismatch_n": int(
            (available & joined.get("split_10c", joined["split"]).astype(str).ne(joined["split"].astype(str))).sum()
        ),
    }
    return joined, mismatch


def build_rejector_decision_reconstruction_audit(
    manifest: dict[str, Any],
    slice_spec: dict[str, Any],
    frontier_row: pd.Series | None,
    reject_slice: pd.DataFrame,
    reject_decision_derivation: str,
    reject_decision_materialization_hit_rate: float,
    primary: pd.DataFrame,
    risk_on_pre_pit: pd.DataFrame,
    risk_joined: pd.DataFrame,
    pit_valid: pd.DataFrame,
    pit_joined: pd.DataFrame,
    mismatch_risk: dict[str, Any],
    mismatch_pit: dict[str, Any],
) -> pd.DataFrame:
    duplicate_n = int(reject_slice.duplicated(REJECT_JOIN_KEY).sum()) if not reject_slice.empty else 0
    risk_unmatched = int((~risk_joined["reject_decision_available_flag"]).sum()) if "reject_decision_available_flag" in risk_joined.columns else len(risk_joined)
    pit_unmatched = int((~pit_joined["reject_decision_available_flag"]).sum()) if "reject_decision_available_flag" in pit_joined.columns else len(pit_joined)
    slice_selected_flag = False
    slice_decision_block_reason = ""
    if frontier_row is not None:
        slice_selected_flag = boolish(frontier_row.get("selected_flag", False))
        slice_decision_block_reason = nonempty(frontier_row.get("decision_block_reason"))
    return pd.DataFrame(
        [
            {
                "rejector_slice_mode": slice_spec["rejector_slice_mode"],
                "model_id": slice_spec["model_id"],
                "ablation_id": slice_spec["ablation_id"],
                "capacity_id": slice_spec["capacity_id"],
                "threshold_id": slice_spec["threshold_id"],
                "population_id": slice_spec["population_id"],
                "denominator_id": slice_spec["denominator_id"],
                "ten_c_manifest_decision": nonempty(manifest.get("decision")),
                "ten_c_manifest_selected_capacity_id": nonempty(manifest.get("selected_capacity_id")),
                "ten_c_manifest_selected_threshold_id": nonempty(manifest.get("selected_threshold_id")),
                "ten_c_manifest_selected_cascade_status": nonempty(manifest.get("selected_cascade_status")),
                "ten_c_manifest_source_caveated": boolish(manifest.get("source_caveated")),
                "slice_selected_flag": slice_selected_flag,
                "slice_decision_block_reason": slice_decision_block_reason,
                "reject_join_key": "|".join(REJECT_JOIN_KEY),
                "reject_join_key_uses_instrument_date_flag": False,
                "reject_decision_derivation": reject_decision_derivation,
                "reject_decision_materialization_hit_rate": reject_decision_materialization_hit_rate,
                "slice_filtered_primary_denominator_row_n": len(reject_slice),
                "pre_scope_primary_denominator_row_n": len(primary),
                "slice_joined_risk_on_pre_pit_row_n": int(risk_joined["reject_decision_available_flag"].sum()),
                "risk_on_pre_pit_row_n": len(risk_on_pre_pit),
                "slice_joined_pit_valid_row_n": int(pit_joined["reject_decision_available_flag"].sum()),
                "evaluated_denominator_row_n": len(pit_valid),
                "duplicate_reject_join_key_n": duplicate_n,
                "risk_on_pre_pit_reject_join_unmatched_n": risk_unmatched,
                "pit_valid_reject_join_unmatched_n": pit_unmatched,
                "risk_on_pre_pit_reject_join_hit_rate": safe_rate(int(risk_joined["reject_decision_available_flag"].sum()), len(risk_joined)),
                "pit_valid_reject_join_hit_rate": safe_rate(int(pit_joined["reject_decision_available_flag"].sum()), len(pit_joined)),
                "risk_on_pre_pit_instrument_mismatch_n": mismatch_risk["instrument_mismatch_n"],
                "risk_on_pre_pit_event_t0_date_mismatch_n": mismatch_risk["event_t0_date_mismatch_n"],
                "risk_on_pre_pit_split_mismatch_n": mismatch_risk["split_mismatch_n"],
                "pit_valid_instrument_mismatch_n": mismatch_pit["instrument_mismatch_n"],
                "pit_valid_event_t0_date_mismatch_n": mismatch_pit["event_t0_date_mismatch_n"],
                "pit_valid_split_mismatch_n": mismatch_pit["split_mismatch_n"],
                "reconstruction_status": "ok"
                if len(reject_slice) > 0
                and duplicate_n == 0
                and len(reject_slice) == len(primary)
                and risk_unmatched == 0
                and pit_unmatched == 0
                and sum(mismatch_risk.values()) == 0
                and sum(mismatch_pit.values()) == 0
                else "reconstruction_mismatch",
            }
        ]
    )


def add_subgroup_flags(frame: pd.DataFrame) -> pd.DataFrame:
    work = frame.copy()
    if "final_sample_weight" not in work.columns:
        work["final_sample_weight"] = 1.0
        work["weight_missing_fallback_flag"] = True
    else:
        work["weight_missing_fallback_flag"] = work["final_sample_weight"].isna()
        work["final_sample_weight"] = pd.to_numeric(work["final_sample_weight"], errors="coerce").fillna(1.0)
    if "horizon_complete_120d" not in work.columns:
        work["horizon_complete_120d"] = pd.NA
    if "winner_120" not in work.columns:
        work["winner_120"] = pd.NA
    work["winner_120_label_available_flag"] = work["winner_120"].notna()
    work["horizon_complete_120d_bool"] = bool_series(work["horizon_complete_120d"])
    work["winner_120_bool"] = bool_series(work["winner_120"])
    work["winner_120_protected_flag"] = work["winner_120_label_available_flag"] & work["winner_120_bool"] & work["horizon_complete_120d_bool"]
    work["nonwinner_reference_flag"] = work["winner_120_label_available_flag"] & (~work["winner_120_bool"]) & work["horizon_complete_120d_bool"]
    work["class_unresolved_flag"] = ~work["horizon_complete_120d_bool"]
    seed_map = {
        "winner_shakeout_seed": "P2_shakeout_prior_path_proxy",
        "winner_volatile_chop_seed": "P3_volatility_expansion_proxy",
        "winner_gap_event_seed": "P1_gap_event_proxy",
    }
    for subgroup_id, col in seed_map.items():
        if col in work.columns:
            work[f"{subgroup_id}_flag"] = work["winner_120_protected_flag"] & bool_series(work[col])
            work[f"{subgroup_id}_source_col"] = col
            work[f"{subgroup_id}_category"] = "A_t0_visible"
        else:
            work[f"{subgroup_id}_flag"] = False
            work[f"{subgroup_id}_source_col"] = col
            work[f"{subgroup_id}_category"] = "missing_seed_definition"
    return work


def subgroup_definitions(frame: pd.DataFrame | None = None) -> list[dict[str, Any]]:
    def category(seed_id: str) -> str:
        if frame is None:
            return "A_t0_visible"
        return str(frame.get(f"{seed_id}_category", pd.Series(["A_t0_visible"])).iloc[0])

    return [
        {"subgroup_id": "winner_120_protected", "flag_col": "winner_120_protected_flag", "category": "primary"},
        {"subgroup_id": "nonwinner_reference", "flag_col": "nonwinner_reference_flag", "category": "reference"},
        {"subgroup_id": "class_unresolved", "flag_col": "class_unresolved_flag", "category": "unresolved"},
        {"subgroup_id": "winner_shakeout_seed", "flag_col": "winner_shakeout_seed_flag", "category": category("winner_shakeout_seed")},
        {"subgroup_id": "winner_volatile_chop_seed", "flag_col": "winner_volatile_chop_seed_flag", "category": category("winner_volatile_chop_seed")},
        {"subgroup_id": "winner_gap_event_seed", "flag_col": "winner_gap_event_seed_flag", "category": category("winner_gap_event_seed")},
    ]


def build_protected_subgroup_count_audit(frame: pd.DataFrame) -> pd.DataFrame:
    rows = []
    total_all = len(frame)
    for split in READOUT_SPLITS:
        group = split_frame(frame, split)
        total = len(group)
        for item in subgroup_definitions(group if not group.empty else frame):
            mask = bool_series(group[item["flag_col"]]) if item["flag_col"] in group.columns else pd.Series(False, index=group.index)
            cell = group.loc[mask]
            rows.append(
                {
                    "split": split,
                    "subgroup_id": item["subgroup_id"],
                    "category": item["category"],
                    "row_n": len(cell),
                    "weight_sum": float(cell["final_sample_weight"].sum()) if "final_sample_weight" in cell.columns else float(len(cell)),
                    "unique_instrument_n": int(cell["instrument"].nunique()) if "instrument" in cell.columns else 0,
                    "subgroup_rate": safe_rate(len(cell), total if split != "all" else total_all),
                    "weight_missing_fallback_n": int(cell.get("weight_missing_fallback_flag", pd.Series(False, index=cell.index)).sum()),
                }
            )
    return pd.DataFrame(rows)


def retention_for_mask(group: pd.DataFrame, mask: pd.Series) -> dict[str, Any]:
    mask = mask.reindex(group.index, fill_value=False).astype(bool)
    unresolved = group.loc[mask & group["class_unresolved_flag"]]
    eligible_mask = mask & group["horizon_complete_120d_bool"] & group["reject_decision_available_flag"]
    eligible = group.loc[eligible_mask]
    retained = eligible.loc[eligible["retained_flag"]]
    weight_sum = float(eligible["final_sample_weight"].sum())
    retained_weight_sum = float(retained["final_sample_weight"].sum())
    return {
        "eligible_n": len(eligible),
        "retained_n": len(retained),
        "retention_rate": safe_rate(len(retained), len(eligible)),
        "weighted_retention_rate": safe_rate(retained_weight_sum, weight_sum),
        "unique_instrument_n": int(eligible["instrument"].nunique()) if "instrument" in eligible.columns else 0,
        "unresolved_excluded_n": len(unresolved),
        "eligible_weight_sum": weight_sum,
        "retained_weight_sum": retained_weight_sum,
    }


def build_retention_rate_readout(pit_valid: pd.DataFrame, pre_pit: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for scope_name, frame in [("pit_valid", pit_valid), ("pre_pit", pre_pit)]:
        work = add_subgroup_flags(frame)
        for split in READOUT_SPLITS:
            group = split_frame(work, split)
            for item in subgroup_definitions(group if not group.empty else work):
                mask = bool_series(group[item["flag_col"]]) if item["flag_col"] in group.columns else pd.Series(False, index=group.index)
                values = retention_for_mask(group, mask)
                rows.append({"split": split, "scope": scope_name, "subgroup_id": item["subgroup_id"], "category": item["category"], **values})
    return pd.DataFrame(rows)


def compute_primary_metrics(frame: pd.DataFrame, split: str) -> dict[str, Any]:
    group = split_frame(frame, split)
    available = group["horizon_complete_120d_bool"] & group["reject_decision_available_flag"]
    overall = retention_for_mask(group, available)
    winner = retention_for_mask(group, group["winner_120_protected_flag"])
    nonwinner = retention_for_mask(group, group["nonwinner_reference_flag"])
    winner_retention = winner["retention_rate"]
    nonwinner_retention = nonwinner["retention_rate"]
    overall_retention = overall["retention_rate"]
    return {
        "split": split,
        "overall_eligible_n": overall["eligible_n"],
        "overall_retained_n": overall["retained_n"],
        "overall_retention": overall_retention,
        "winner_n": winner["eligible_n"],
        "winner_retained_n": winner["retained_n"],
        "winner_retention": winner_retention,
        "unique_winner_instrument_n": winner["unique_instrument_n"],
        "nonwinner_n": nonwinner["eligible_n"],
        "nonwinner_retained_n": nonwinner["retained_n"],
        "nonwinner_retention": nonwinner_retention,
        "unique_nonwinner_instrument_n": nonwinner["unique_instrument_n"],
        "relative_retention_winner_vs_nonwinner": safe_rate(winner_retention, nonwinner_retention),
        "relative_retention_winner_vs_overall": safe_rate(winner_retention, overall_retention),
        "retention_gap_winner_minus_nonwinner": winner_retention - nonwinner_retention
        if not pd.isna(winner_retention) and not pd.isna(nonwinner_retention)
        else float("nan"),
    }


def sample_metric(sample: pd.DataFrame) -> tuple[float, float]:
    winner = retention_for_mask(sample, sample["winner_120_protected_flag"])
    nonwinner = retention_for_mask(sample, sample["nonwinner_reference_flag"])
    wr = winner["retention_rate"]
    nr = nonwinner["retention_rate"]
    rel = safe_rate(wr, nr)
    gap = wr - nr if not pd.isna(wr) and not pd.isna(nr) else float("nan")
    return rel, gap


def bootstrap_seed_relative_ci(group: pd.DataFrame, seed_flag_col: str, params: Params) -> dict[str, float]:
    if group.empty or "instrument" not in group.columns or seed_flag_col not in group.columns:
        return {
            "relative_retention_median": float("nan"),
            "relative_retention_ci_low_p05": float("nan"),
            "relative_retention_ci_high_p95": float("nan"),
            "prob_relative_retention_lt_floor": float("nan"),
        }
    blocks = [block for block in group["instrument"].dropna().astype(str).unique().tolist() if block != ""]
    if not blocks:
        return {
            "relative_retention_median": float("nan"),
            "relative_retention_ci_low_p05": float("nan"),
            "relative_retention_ci_high_p95": float("nan"),
            "prob_relative_retention_lt_floor": float("nan"),
        }
    seed_offset = sum(ord(ch) for ch in seed_flag_col) + len(group) * 17
    rng = np.random.default_rng(params.bootstrap_seed + seed_offset)
    index_by_block = {block: group.index[group["instrument"].astype(str).eq(block)].to_numpy() for block in blocks}
    rel_values = []
    for _ in range(params.bootstrap_n):
        sampled_blocks = rng.choice(blocks, size=len(blocks), replace=True)
        sampled_index = np.concatenate([index_by_block[block] for block in sampled_blocks])
        sample = group.loc[sampled_index]
        seed = retention_for_mask(sample, sample[seed_flag_col])
        nonwinner = retention_for_mask(sample, sample["nonwinner_reference_flag"])
        rel_values.append(safe_rate(seed["retention_rate"], nonwinner["retention_rate"]))
    rel_arr = np.asarray(rel_values, dtype=float)
    rel_valid = rel_arr[~np.isnan(rel_arr)]
    if len(rel_valid) == 0:
        return {
            "relative_retention_median": float("nan"),
            "relative_retention_ci_low_p05": float("nan"),
            "relative_retention_ci_high_p95": float("nan"),
            "prob_relative_retention_lt_floor": float("nan"),
        }
    return {
        "relative_retention_median": float(np.nanmedian(rel_arr)),
        "relative_retention_ci_low_p05": float(np.quantile(rel_valid, 0.05)),
        "relative_retention_ci_high_p95": float(np.quantile(rel_valid, 0.95)),
        "prob_relative_retention_lt_floor": float(np.nanmean(rel_arr < params.relative_retention_floor)),
    }


def direction_from_ci(ci_low: float, ci_high: float, floor: float) -> str:
    if pd.isna(ci_low) or pd.isna(ci_high):
        return "undetermined"
    if ci_low >= floor:
        return "non_discriminatory_direction"
    if ci_high < floor:
        return "discriminatory_direction"
    return "ambiguous_direction"


def bootstrap_retention(frame: pd.DataFrame, params: Params) -> tuple[pd.DataFrame, pd.DataFrame]:
    rng = np.random.default_rng(params.bootstrap_seed)
    raw_rows: list[dict[str, Any]] = []
    summary_rows: list[dict[str, Any]] = []
    for split in READOUT_SPLITS:
        group = split_frame(frame, split).copy()
        if group.empty:
            continue
        for block_col in ["instrument", "binding_canonical_event_id"]:
            block_level = "instrument" if block_col == "instrument" else "binding_canonical_event_id"
            if block_col not in group.columns:
                continue
            blocks = [block for block in group[block_col].dropna().astype(str).unique().tolist() if block != ""]
            if not blocks:
                continue
            index_by_block = {block: group.index[group[block_col].astype(str).eq(block)].to_numpy() for block in blocks}
            rel_values: list[float] = []
            gap_values: list[float] = []
            for iteration in range(params.bootstrap_n):
                sampled_blocks = rng.choice(blocks, size=len(blocks), replace=True)
                sampled_index = np.concatenate([index_by_block[block] for block in sampled_blocks])
                sample = group.loc[sampled_index]
                rel, gap = sample_metric(sample)
                rel_values.append(rel)
                gap_values.append(gap)
                raw_rows.append(
                    {
                        "split": split,
                        "block_level": block_level,
                        "bootstrap_iter": iteration,
                        "relative_retention_winner_vs_nonwinner": rel,
                        "retention_gap_winner_minus_nonwinner": gap,
                    }
                )
            rel_arr = np.asarray(rel_values, dtype=float)
            gap_arr = np.asarray(gap_values, dtype=float)
            rel_valid = rel_arr[~np.isnan(rel_arr)]
            gap_valid = gap_arr[~np.isnan(gap_arr)]
            ci_low = float(np.quantile(rel_valid, 0.05)) if len(rel_valid) else float("nan")
            ci_high = float(np.quantile(rel_valid, 0.95)) if len(rel_valid) else float("nan")
            gap_ci_low = float(np.quantile(gap_valid, 0.05)) if len(gap_valid) else float("nan")
            gap_ci_high = float(np.quantile(gap_valid, 0.95)) if len(gap_valid) else float("nan")
            summary_rows.append(
                {
                    "split": split,
                    "block_level": block_level,
                    "bootstrap_n": params.bootstrap_n,
                    "relative_retention_median": float(np.nanmedian(rel_arr)) if len(rel_arr) else float("nan"),
                    "relative_retention_ci_low_p05": ci_low,
                    "relative_retention_ci_high_p95": ci_high,
                    "retention_gap_median": float(np.nanmedian(gap_arr)) if len(gap_arr) else float("nan"),
                    "retention_gap_ci_low_p05": gap_ci_low,
                    "retention_gap_ci_high_p95": gap_ci_high,
                    "prob_relative_retention_lt_floor": float(np.nanmean(rel_arr < params.relative_retention_floor))
                    if len(rel_arr)
                    else float("nan"),
                    "prob_relative_retention_ge_1": float(np.nanmean(rel_arr >= 1.0)) if len(rel_arr) else float("nan"),
                    "bootstrap_direction": direction_from_ci(ci_low, ci_high, params.relative_retention_floor),
                }
            )
    return pd.DataFrame(summary_rows), pd.DataFrame(raw_rows)


def split_retention_status(row: pd.Series, params: Params) -> str:
    split = str(row["split"])
    ci_low = row.get("relative_retention_ci_low_p05", float("nan"))
    ci_high = row.get("relative_retention_ci_high_p95", float("nan"))
    if split == "validation":
        if (
            row["winner_n"] < params.validation_min_class_n
            or row["nonwinner_n"] < params.validation_min_class_n
            or row["unique_winner_instrument_n"] < params.validation_min_instrument_n
            or row["unique_nonwinner_instrument_n"] < params.validation_min_instrument_n
        ):
            return "validation_low_power"
    elif split in GATE_SPLITS:
        if row["winner_n"] < params.retention_min_winner_n or row["unique_winner_instrument_n"] < params.retention_min_winner_instrument_n:
            return "retention_underpowered"
    else:
        return "readout_only"

    if pd.isna(ci_low) or pd.isna(ci_high):
        return "retention_underpowered" if split in GATE_SPLITS else "validation_low_power"
    if ci_low >= params.relative_retention_floor:
        return "non_discriminatory"
    if ci_high < params.relative_retention_floor:
        return "discriminatory"
    return "ambiguous"


def overall_gate(split_status: dict[str, str]) -> str:
    train = split_status.get("train", "retention_underpowered")
    robustness = split_status.get("robustness", "retention_underpowered")
    statuses = [train, robustness]
    if "discriminatory" in statuses:
        return "discriminatory"
    if "ambiguous" in statuses:
        return "ambiguous"
    if statuses.count("retention_underpowered") == 2:
        return "inconclusive_underpowered"
    if statuses.count("retention_underpowered") == 1:
        return "inconclusive_mixed_power"
    if train == "non_discriminatory" and robustness == "non_discriminatory":
        return "non_discriminatory"
    return "ambiguous"


def build_non_discrimination_metrics(frame: pd.DataFrame, bootstrap_summary: pd.DataFrame, params: Params) -> tuple[pd.DataFrame, str, bool]:
    rows = []
    for split in READOUT_SPLITS:
        rows.append(compute_primary_metrics(frame, split))
    metrics = pd.DataFrame(rows)
    primary_boot = bootstrap_summary.loc[bootstrap_summary["block_level"].eq("instrument")].copy()
    primary_boot = primary_boot.rename(
        columns={
            "relative_retention_median": "bootstrap_relative_retention_median",
            "relative_retention_ci_low_p05": "relative_retention_ci_low_p05",
            "relative_retention_ci_high_p95": "relative_retention_ci_high_p95",
            "retention_gap_median": "bootstrap_retention_gap_median",
            "retention_gap_ci_low_p05": "retention_gap_ci_low_p05",
            "retention_gap_ci_high_p95": "retention_gap_ci_high_p95",
        }
    )
    metrics = metrics.merge(
        primary_boot[
            [
                "split",
                "bootstrap_relative_retention_median",
                "relative_retention_ci_low_p05",
                "relative_retention_ci_high_p95",
                "bootstrap_retention_gap_median",
                "retention_gap_ci_low_p05",
                "retention_gap_ci_high_p95",
                "prob_relative_retention_lt_floor",
                "prob_relative_retention_ge_1",
                "bootstrap_direction",
            ]
        ],
        on="split",
        how="left",
    )
    metrics["split_retention_status"] = metrics.apply(lambda row: split_retention_status(row, params), axis=1)

    directions = bootstrap_summary.pivot(index="split", columns="block_level", values="bootstrap_direction").reset_index()
    conflict = False
    if {"instrument", "binding_canonical_event_id"}.issubset(directions.columns):
        conflict_rows = directions.loc[
            directions["split"].isin(GATE_SPLITS)
            & (
                (
                    directions["instrument"].eq("non_discriminatory_direction")
                    & directions["binding_canonical_event_id"].eq("discriminatory_direction")
                )
                | (
                    directions["instrument"].eq("discriminatory_direction")
                    & directions["binding_canonical_event_id"].eq("non_discriminatory_direction")
                )
            )
        ]
        conflict = not conflict_rows.empty
    metrics["episode_block_retention_conflict_flag"] = bool(conflict)
    split_status = dict(zip(metrics["split"], metrics["split_retention_status"]))
    return metrics, overall_gate(split_status), conflict


def build_scope_reconciliation(primary: pd.DataFrame, risk_on: pd.DataFrame, pit_valid: pd.DataFrame, paths: dict[str, Path], params: Params) -> pd.DataFrame:
    a1_risk = pd.read_csv(paths["eleven_a1_scope_risk_on"])
    a1_pit = pd.read_csv(paths["eleven_a1_scope_pit"])
    a2_scope = pd.read_csv(paths["eleven_a2_scope_reconciliation"])
    rows = []
    for split in READOUT_SPLITS:
        p = split_frame(primary, split)
        r = split_frame(risk_on, split)
        pit = split_frame(pit_valid, split)
        a1r = a1_risk.loc[a1_risk["split"].astype(str).eq(split)]
        a1p = a1_pit.loc[a1_pit["split"].astype(str).eq(split)]
        a2 = a2_scope.loc[a2_scope["split"].astype(str).eq(split)]
        a1_pre = int(a1r["pre_scope_primary_denominator_row_n"].iloc[0]) if not a1r.empty else 0
        a1_risk_n = int(a1r["risk_on_evaluated_row_n"].iloc[0]) if not a1r.empty else 0
        a1_pit_n = int(a1p["pit_valid_evaluated_row_n"].iloc[0]) if not a1p.empty else 0
        a2_pit_n = int(a2["a2_pit_valid_evaluated_row_n"].iloc[0]) if not a2.empty else 0
        pre_drift = abs(len(p) - a1_pre) / a1_pre if a1_pre else 1.0
        risk_drift = abs(len(r) - a1_risk_n) / a1_risk_n if a1_risk_n else 1.0
        pit_drift = abs(len(pit) - a1_pit_n) / a1_pit_n if a1_pit_n else 1.0
        max_drift = max(pre_drift, risk_drift, pit_drift)
        rows.append(
            {
                "split": split,
                "b_pre_scope_primary_denominator_row_n": len(p),
                "a1_pre_scope_primary_denominator_row_n": a1_pre,
                "b_risk_on_pre_pit_row_n": len(r),
                "a1_risk_on_pre_pit_row_n": a1_risk_n,
                "b_pit_valid_evaluated_row_n": len(pit),
                "a1_pit_valid_evaluated_row_n": a1_pit_n,
                "a2_pit_valid_evaluated_row_n": a2_pit_n,
                "primary_denominator_row_n_match_flag": len(p) == a1_pre,
                "pre_pit_row_n_match_flag": len(r) == a1_risk_n,
                "pit_valid_row_n_match_flag": len(pit) == a1_pit_n == a2_pit_n,
                "denominator_drift_rate": max_drift,
                "reconciliation_status": "ok" if max_drift <= params.denominator_drift_ceiling else "denominator_drift",
            }
        )
    return pd.DataFrame(rows)


def retention_reconciliation_vs_10c(
    primary_joined: pd.DataFrame,
    risk_on_joined: pd.DataFrame,
    frontier_row: pd.Series | None,
    params: Params,
) -> pd.DataFrame:
    rows = []
    for comparison_scope, frame in [("score_cache_primary", primary_joined), ("risk_on_pre_pit", risk_on_joined)]:
        work = add_subgroup_flags(frame)
        for split in PRIMARY_SPLITS:
            group = split_frame(work, split)
            winner = group.loc[group["winner_120_protected_flag"] & group["reject_decision_available_flag"]]
            retention = safe_rate(int(winner["retained_flag"].sum()), len(winner))
            published = float(frontier_row.get(f"{split}_winner_retention", float("nan"))) if frontier_row is not None else float("nan")
            diff = abs(retention - published) if not pd.isna(retention) and not pd.isna(published) else float("nan")
            status = "ok" if comparison_scope == "score_cache_primary" and diff <= params.retention_recon_abs_diff_ceiling else "readout_only"
            if comparison_scope == "risk_on_pre_pit":
                status = "ok" if diff <= params.retention_recon_abs_diff_ceiling else "retention_reconciliation_diff_gt_ceiling"
            rows.append(
                {
                    "comparison_scope": comparison_scope,
                    "split": split,
                    "b_recomputed_winner_n": len(winner),
                    "b_recomputed_winner_retention": retention,
                    "c10c_published_winner_retention": published,
                    "winner_retention_abs_diff": diff,
                    "retention_reconciliation_status": status,
                }
            )
    return pd.DataFrame(rows)


def build_protected_subgroup_retention_readout(frame: pd.DataFrame, params: Params) -> pd.DataFrame:
    rows = []
    seed_ids = ["winner_shakeout_seed", "winner_volatile_chop_seed", "winner_gap_event_seed"]
    for split in READOUT_SPLITS:
        group = split_frame(frame, split)
        nonwinner = retention_for_mask(group, group["nonwinner_reference_flag"])
        for seed_id in seed_ids:
            flag_col = f"{seed_id}_flag"
            seed = retention_for_mask(group, bool_series(group[flag_col]) if flag_col in group.columns else pd.Series(False, index=group.index))
            relative = safe_rate(seed["retention_rate"], nonwinner["retention_rate"])
            category = str(group.get(f"{seed_id}_category", pd.Series(["missing_seed_definition"])).iloc[0]) if not group.empty else "missing_seed_definition"
            ci = bootstrap_seed_relative_ci(group, flag_col, params)
            subgroup_status = "ok" if seed["eligible_n"] >= 30 and seed["unique_instrument_n"] >= 20 else "subgroup_underpowered"
            rows.append(
                {
                    "split": split,
                    "subgroup_id": seed_id,
                    "category": category,
                    **seed,
                    "reference_nonwinner_retention": nonwinner["retention_rate"],
                    "relative_retention_vs_nonwinner": relative,
                    "relative_retention_median": ci["relative_retention_median"],
                    "relative_retention_ci_low_p05": ci["relative_retention_ci_low_p05"],
                    "relative_retention_ci_high_p95": ci["relative_retention_ci_high_p95"],
                    "prob_relative_retention_lt_floor": ci["prob_relative_retention_lt_floor"],
                    "ci_below_floor_flag": bool(
                        subgroup_status == "ok"
                        and not pd.isna(ci["relative_retention_ci_high_p95"])
                        and ci["relative_retention_ci_high_p95"] < params.relative_retention_floor
                    ),
                    "subgroup_status": subgroup_status,
                }
            )
    return pd.DataFrame(rows)


def count_seed_significant_cells(frame: pd.DataFrame, floor: float) -> int:
    count = 0
    for split in PRIMARY_SPLITS:
        group = split_frame(frame, split)
        nonwinner = retention_for_mask(group, group["nonwinner_reference_flag"])
        for seed_id in ["winner_shakeout_seed", "winner_volatile_chop_seed", "winner_gap_event_seed"]:
            seed = retention_for_mask(group, group[f"{seed_id}_flag"] if f"{seed_id}_flag" in group.columns else pd.Series(False, index=group.index))
            relative = safe_rate(seed["retention_rate"], nonwinner["retention_rate"])
            if seed["eligible_n"] >= 10 and not pd.isna(relative) and relative < floor:
                count += 1
    return count


def build_subgroup_multiple_comparison_audit(frame: pd.DataFrame, seed_readout: pd.DataFrame, params: Params) -> pd.DataFrame:
    rng = np.random.default_rng(params.multiple_comparison_null_seed)
    tested_cells = len(PRIMARY_SPLITS) * 3
    actual = int(
        seed_readout.loc[
            seed_readout["split"].isin(PRIMARY_SPLITS)
            & seed_readout["subgroup_status"].eq("ok")
            & seed_readout["ci_below_floor_flag"].map(boolish)
        ].shape[0]
    )
    null_counts: list[int] = []
    eligible_base = frame["horizon_complete_120d_bool"] & frame["reject_decision_available_flag"]
    for _ in range(params.multiple_comparison_null_n):
        shuffled = frame.copy()
        for split in PRIMARY_SPLITS:
            idx = shuffled.index[shuffled["split"].astype(str).eq(split) & eligible_base]
            values = shuffled.loc[idx, "retained_flag"].to_numpy()
            if len(values):
                rng.shuffle(values)
                shuffled.loc[idx, "retained_flag"] = values
        null_counts.append(count_seed_significant_cells(shuffled, params.relative_retention_floor))
    p95 = float(np.quantile(null_counts, 0.95)) if null_counts else float("nan")
    return pd.DataFrame(
        [
            {
                "total_tested_subgroup_cells": tested_cells,
                "significant_cells_n": actual,
                "null_simulation_n": params.multiple_comparison_null_n,
                "null_expected_significant_cells_n": float(np.mean(null_counts)) if null_counts else float("nan"),
                "null_significant_cells_p95": p95,
                "actual_exceeds_null_p95_flag": actual > p95 if not pd.isna(p95) else False,
                "multiple_comparison_status": "actual_exceeds_null_p95" if actual > p95 else "ok",
            }
        ]
    )


def copy_or_build_denominator_completeness(paths: dict[str, Path], pit_valid: pd.DataFrame) -> pd.DataFrame:
    source = paths.get("eleven_a1_denominator_completeness")
    if source and source.exists():
        out = pd.read_csv(source).copy()
        out["source_artifact"] = relative_path(source)
        return out
    return pd.DataFrame(
        [
            {
                "population_scope": "risk_on_evaluated",
                "row_count": len(pit_valid),
                "pit_membership_match_rate": 1.0 if len(pit_valid) else float("nan"),
                "st_row_n": 0,
                "suspended_row_n": 0,
                "not_listed_row_n": 0,
                "left_tail_status_audit_status": "ok" if len(pit_valid) else "left_tail_status_audit_incomplete",
            }
        ]
    )


def final_status_from_gate(
    blockers: list[str],
    incomplete: list[str],
    overall_retention_gate: str,
    episode_conflict: bool,
) -> str:
    if blockers:
        return FINAL_BLOCKED
    if incomplete:
        return FINAL_INCOMPLETE
    if episode_conflict and overall_retention_gate == "non_discriminatory":
        return FINAL_AMBIGUOUS
    return {
        "non_discriminatory": FINAL_NON_DISCRIMINATORY,
        "discriminatory": FINAL_DISCRIMINATORY,
        "ambiguous": FINAL_AMBIGUOUS,
        "inconclusive_underpowered": FINAL_UNDERPOWERED,
        "inconclusive_mixed_power": FINAL_MIXED_POWER,
    }.get(overall_retention_gate, FINAL_AMBIGUOUS)


def build_retention_summary(
    final_status: str,
    blockers: list[str],
    incomplete: list[str],
    overall_gate_value: str,
    metrics: pd.DataFrame,
    recon: pd.DataFrame,
    reject_audit: pd.DataFrame,
) -> pd.DataFrame:
    all_metrics = metrics.loc[metrics["split"].eq("all")].iloc[0] if not metrics.loc[metrics["split"].eq("all")].empty else pd.Series(dtype=object)
    risk_recon_bad = int(
        recon.loc[
            recon["comparison_scope"].eq("risk_on_pre_pit")
            & recon["retention_reconciliation_status"].eq("retention_reconciliation_diff_gt_ceiling")
        ].shape[0]
    )
    return pd.DataFrame(
        [
            {
                "run_id": RUN_ID,
                "final_status": final_status,
                "overall_retention_gate": overall_gate_value,
                "blocker_reasons": "|".join(blockers),
                "statistics_incomplete_reasons": "|".join(incomplete),
                "evaluated_denominator_row_n": int(reject_audit["evaluated_denominator_row_n"].iloc[0]) if not reject_audit.empty else 0,
                "winner_120_protected_n": int(all_metrics.get("winner_n", 0)),
                "nonwinner_reference_n": int(all_metrics.get("nonwinner_n", 0)),
                "winner_retention": float(all_metrics.get("winner_retention", float("nan"))),
                "nonwinner_retention": float(all_metrics.get("nonwinner_retention", float("nan"))),
                "relative_retention_winner_vs_nonwinner": float(all_metrics.get("relative_retention_winner_vs_nonwinner", float("nan"))),
                "risk_on_pre_pit_frontier_recon_bad_split_n": risk_recon_bad,
                "diagnostic_only_flag": True,
            }
        ]
    )


def format_float(value: Any, digits: int = 4) -> str:
    try:
        if pd.isna(value):
            return "NA"
        return f"{float(value):.{digits}f}"
    except Exception:
        return "NA"


def build_report(
    final_status: str,
    summary: pd.DataFrame,
    scope_recon: pd.DataFrame,
    retention_recon: pd.DataFrame,
    subgroup_counts: pd.DataFrame,
    metrics: pd.DataFrame,
    seed_readout: pd.DataFrame,
    multiple_audit: pd.DataFrame,
    reject_audit: pd.DataFrame,
) -> str:
    all_scope = scope_recon.loc[scope_recon["split"].eq("all")].iloc[0]
    all_summary = summary.iloc[0]
    ra = reject_audit.iloc[0]
    lines = [
        f"# 11B Archetype Protected Retention Readout Report",
        "",
        "## 结论",
        "",
        f"- final_status: `{final_status}`",
        f"- overall_retention_gate: `{all_summary['overall_retention_gate']}`",
        f"- evaluated denominator: {int(all_summary['evaluated_denominator_row_n']):,} 行；winner_120 protected: {int(all_summary['winner_120_protected_n']):,}；nonwinner reference: {int(all_summary['nonwinner_reference_n']):,}。",
        f"- 全样本 winner retention / nonwinner retention / relative retention: {format_float(all_summary['winner_retention'])} / {format_float(all_summary['nonwinner_retention'])} / {format_float(all_summary['relative_retention_winner_vs_nonwinner'])}。",
        "",
        "本报告只度量 10C `keep_9000` diagnostic reference slice 的 protected retention readout；不输出 routing、entry、exit、sizing 或策略 EV，也不放宽 10C。",
        "",
        "## 数据来源",
        "",
        "- PIT-valid evaluated denominator 优先来自 11A1 `proxy_scored_denominator.parquet`，并与 11A1/11A2 scope audit 对账。",
        "- reject decision 来自 10C `post_dedup_false_repair_scores.parquet` 的 `keep_9000` diagnostic reference slice。",
        "- 10C frontier 对账来自 `false_repair_threshold_frontier.csv`；PIT/status 完整性沿用 11A1 denominator completeness audit。",
        "",
        "## Scope 对账",
        "",
        f"- score-cache primary denominator: 11B {int(all_scope['b_pre_scope_primary_denominator_row_n']):,} vs 11A1 {int(all_scope['a1_pre_scope_primary_denominator_row_n']):,}。",
        f"- risk_on pre-PIT: 11B {int(all_scope['b_risk_on_pre_pit_row_n']):,} vs 11A1 {int(all_scope['a1_risk_on_pre_pit_row_n']):,}。",
        f"- PIT-valid evaluated: 11B {int(all_scope['b_pit_valid_evaluated_row_n']):,} vs 11A1 {int(all_scope['a1_pit_valid_evaluated_row_n']):,} vs 11A2 {int(all_scope['a2_pit_valid_evaluated_row_n']):,}。",
        f"- scope reconciliation status: `{all_scope['reconciliation_status']}`。",
        "",
        "### Split Scope Counts",
        "",
    ]
    for _, row in scope_recon.iterrows():
        lines.append(
            f"- {row['split']}: primary={int(row['b_pre_scope_primary_denominator_row_n']):,}, risk_on_pre_pit={int(row['b_risk_on_pre_pit_row_n']):,}, pit_valid={int(row['b_pit_valid_evaluated_row_n']):,}, status=`{row['reconciliation_status']}`。"
        )
    lines.extend(
        [
            "",
            "### Split Protected Counts",
            "",
        ]
    )
    count_split_view = subgroup_counts.loc[
        subgroup_counts["split"].isin(["train", "validation", "robustness"])
        & subgroup_counts["subgroup_id"].isin(["winner_120_protected", "nonwinner_reference", "class_unresolved"])
    ]
    for _, row in count_split_view.iterrows():
        lines.append(
            f"- {row['split']} / {row['subgroup_id']}: row_n={int(row['row_n'])}, unique_instrument_n={int(row['unique_instrument_n'])}, rate={format_float(row['subgroup_rate'])}。"
        )
    lines.extend(
        [
            "",
        "## 10C Slice 还原",
        "",
        f"- rejector_slice_mode: `{ra['rejector_slice_mode']}`；slice_selected_flag: `{ra['slice_selected_flag']}`；decision_block_reason: `{ra['slice_decision_block_reason']}`。",
        f"- reject_decision_derivation: `{ra['reject_decision_derivation']}`；materialization_hit_rate: {format_float(ra['reject_decision_materialization_hit_rate'])}。",
        f"- composite join key: `{ra['reject_join_key']}`；duplicate key: {int(ra['duplicate_reject_join_key_n'])}。",
        f"- score-cache slice rows: {int(ra['slice_filtered_primary_denominator_row_n']):,}；risk_on pre-PIT hit rate: {format_float(ra['risk_on_pre_pit_reject_join_hit_rate'])}；PIT-valid hit rate: {format_float(ra['pit_valid_reject_join_hit_rate'])}。",
        "",
        "## 10C Frontier Retention 对账",
        "",
        ]
    )
    for _, row in retention_recon.iterrows():
        lines.append(
            f"- {row['comparison_scope']} / {row['split']}: recomputed={format_float(row['b_recomputed_winner_retention'])}, published={format_float(row['c10c_published_winner_retention'])}, diff={format_float(row['winner_retention_abs_diff'])}, status=`{row['retention_reconciliation_status']}`。"
        )
    lines.extend(["", "## Primary Retention Gate", ""])
    for _, row in metrics.iterrows():
        lines.append(
            f"- {row['split']}: winner_n={int(row['winner_n'])}, nonwinner_n={int(row['nonwinner_n'])}, winner_ret={format_float(row['winner_retention'])}, nonwinner_ret={format_float(row['nonwinner_retention'])}, relative={format_float(row['relative_retention_winner_vs_nonwinner'])}, CI5/95=[{format_float(row['relative_retention_ci_low_p05'])}, {format_float(row['relative_retention_ci_high_p95'])}], status=`{row['split_retention_status']}`。"
        )
    lines.extend(["", "## Protected Subgroup Counts", ""])
    count_view = subgroup_counts.loc[subgroup_counts["split"].eq("all")]
    for _, row in count_view.iterrows():
        lines.append(
            f"- {row['subgroup_id']}: row_n={int(row['row_n'])}, unique_instrument_n={int(row['unique_instrument_n'])}, rate={format_float(row['subgroup_rate'])}。"
        )
    lines.extend(["", "## Seed 子群 Readout", ""])
    seed_all = seed_readout.loc[seed_readout["split"].eq("all")]
    for _, row in seed_all.iterrows():
        lines.append(
            f"- {row['subgroup_id']} ({row['category']}): eligible_n={int(row['eligible_n'])}, retention={format_float(row['retention_rate'])}, relative_vs_nonwinner={format_float(row['relative_retention_vs_nonwinner'])}, CI5/95=[{format_float(row['relative_retention_ci_low_p05'])}, {format_float(row['relative_retention_ci_high_p95'])}], status=`{row['subgroup_status']}`。"
        )
    ma = multiple_audit.iloc[0]
    lines.extend(
        [
            "",
            "## Multiple Comparison Audit",
            "",
            f"- tested_cells={int(ma['total_tested_subgroup_cells'])}, significant_cells={int(ma['significant_cells_n'])}, null_expected={format_float(ma['null_expected_significant_cells_n'])}, null_p95={format_float(ma['null_significant_cells_p95'])}, status=`{ma['multiple_comparison_status']}`。",
            "",
            "## 预注册解释",
            "",
        ]
    )
    if final_status == FINAL_INCOMPLETE:
        lines.append(
            f"- 本轮输入可读，但存在 statistics_incomplete ceiling：`{all_summary['statistics_incomplete_reasons']}`。在该状态下 retention 维度只能作为 readout，不做策略化解释。"
        )
    elif final_status == FINAL_NON_DISCRIMINATORY:
        lines.append("- 在当前 PIT-valid 数据与 reference slice 上，winner 子群相对非 winner 未显示显著 retention 受损；11C 仍需重新计算带成本与容量的策略 EV。")
    elif final_status == FINAL_DISCRIMINATORY:
        lines.append("- reference slice 在 winner 子群上 retention 显著偏低；11C 必须把 winner retention 损失作为显式成本纳入 replay。")
    else:
        lines.append("- 当前证据不足以给出非歧视性定性，retention 维度暂作 readout-only。")
    lines.append("")
    return "\n".join(lines)


def artifact_record(path: Path) -> dict[str, Any]:
    record = {
        "path": relative_path(path),
        "sha256": file_sha256(path) if path.is_file() else "",
        "row_count": quick_row_count(path),
    }
    if path.exists() and "".join(path.suffixes).endswith(".parquet"):
        try:
            import pyarrow.parquet as pq

            record["schema"] = pq.ParquetFile(path).schema.names
        except Exception:
            record["schema"] = []
    elif path.exists() and "".join(path.suffixes).endswith(".csv"):
        try:
            record["schema"] = pd.read_csv(path, nrows=0).columns.tolist()
        except Exception:
            record["schema"] = []
    return record


def build_manifest(config: dict[str, Any], outputs: dict[str, Path], cache_artifacts: dict[str, Path], final_status: str, command: str) -> dict[str, Any]:
    return {
        "run_id": RUN_ID,
        "final_status": final_status,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "git_revision": git_revision(),
        "python": sys.version,
        "platform": platform.platform(),
        "command": command,
        "config_path": relative_path(CONFIG_PATH),
        "config_hash": stable_hash(config),
        "config_sha256": file_sha256(CONFIG_PATH),
        "outputs": {key: relative_path(path) for key, path in sorted(outputs.items())},
        "output_hashes": {key: file_sha256(path) for key, path in sorted(outputs.items()) if path.is_file()},
        "output_artifacts": {key: artifact_record(path) for key, path in sorted(outputs.items())},
        "cache_artifacts": {key: artifact_record(path) for key, path in sorted(cache_artifacts.items())},
    }


def write_blocked_outputs(
    config: dict[str, Any],
    outputs: dict[str, Path],
    cache_outputs: dict[str, Path],
    blockers: list[str],
    command: str,
) -> dict[str, Any]:
    summary = pd.DataFrame(
        [
            {
                "run_id": RUN_ID,
                "final_status": FINAL_BLOCKED,
                "overall_retention_gate": "",
                "blocker_reasons": "|".join(blockers),
                "statistics_incomplete_reasons": "",
                "evaluated_denominator_row_n": 0,
                "winner_120_protected_n": 0,
                "nonwinner_reference_n": 0,
                "winner_retention": np.nan,
                "nonwinner_retention": np.nan,
                "relative_retention_winner_vs_nonwinner": np.nan,
                "risk_on_pre_pit_frontier_recon_bad_split_n": 0,
                "diagnostic_only_flag": True,
            }
        ]
    )
    outputs["retention_summary"] = write_df(TABLE_DIR / "retention_summary.csv", summary)
    outputs["report"] = write_text(
        REPORT_PATH,
        "# 11B Archetype Protected Retention Readout Report\n\n"
        f"- final_status: `{FINAL_BLOCKED}`\n"
        f"- blocker_reasons: `{summary['blocker_reasons'].iloc[0]}`\n\n"
        "本报告只度量 diagnostic reference slice；input gate 失败时不计算 retention gate。\n",
    )
    manifest = build_manifest(config, outputs, cache_outputs, FINAL_BLOCKED, command)
    write_json(MANIFEST_PATH, manifest)
    return manifest


def run(config_path: Path = CONFIG_PATH) -> dict[str, Any]:
    config = load_yaml(config_path)
    params = Params.from_config(config)
    paths = build_paths(config)
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    LOCAL_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

    outputs: dict[str, Path] = {}
    cache_outputs: dict[str, Path] = {}
    blockers: list[str] = []
    incomplete: list[str] = []

    input_audit = input_artifact_audit(paths, required_inputs(), required_schema())
    outputs["input_artifact_audit"] = write_df(TABLE_DIR / "input_artifact_audit.csv", input_audit)
    missing_required = input_audit.loc[input_audit["required_flag"] & ~input_audit["exists_flag"], "artifact_id"].tolist()
    bad_schema = input_audit.loc[input_audit["schema_status"].isin(["missing_columns", "schema_read_failed"]), "artifact_id"].tolist()
    if missing_required:
        blockers.append("required_input_missing:" + ",".join(missing_required))
    if bad_schema:
        blockers.append("required_schema_invalid:" + ",".join(bad_schema))

    config_contract = validate_config_contract(config)
    outputs["config_contract_audit"] = write_df(TABLE_DIR / "config_contract_audit.csv", config_contract)
    if not config_contract["present_flag"].all():
        incomplete.append("config_contract_missing_keys")

    if blockers:
        return write_blocked_outputs(config, outputs, cache_outputs, blockers, " ".join(sys.argv))

    manifest_10c = read_json(paths["ten_c_manifest"])
    slice_spec = select_rejector_slice_mode(manifest_10c, config)
    scores = pd.read_parquet(paths["ten_c_scores"])
    reject_slice = filter_rejector_slice(scores, slice_spec)
    reject_slice, reject_decision_derivation, reject_decision_hit_rate = materialize_reject_decision(reject_slice)
    frontier = pd.read_csv(paths["ten_c_threshold_frontier"])
    frontier_row = frontier_slice_row(frontier, slice_spec)
    if reject_slice.empty:
        blockers.append("10c_reference_slice_empty")
    if reject_decision_hit_rate == 0:
        blockers.append("reject_decision_unavailable")

    primary, denom_contract = build_primary_denominator(config, paths, reject_slice)
    risk_on_pre_pit = primary.loc[primary["risk_on_scope_flag"]].copy()
    evaluated = load_evaluated_denominator(paths, risk_on_pre_pit)
    if evaluated.empty:
        blockers.append("evaluated_denominator_empty")
    required_evaluated_cols = {"winner_120", "horizon_complete_120d", "final_sample_weight"}
    missing_evaluated_cols = sorted(required_evaluated_cols - set(evaluated.columns))
    if missing_evaluated_cols:
        blockers.append("evaluated_label_horizon_columns_missing:" + ",".join(missing_evaluated_cols))

    if blockers:
        return write_blocked_outputs(config, outputs, cache_outputs, blockers, " ".join(sys.argv))

    primary_joined, mismatch_primary = attach_reject_decision(primary, reject_slice)
    risk_joined, mismatch_risk = attach_reject_decision(risk_on_pre_pit, reject_slice)
    pit_joined, mismatch_pit = attach_reject_decision(evaluated, reject_slice)
    primary_joined = add_subgroup_flags(primary_joined)
    risk_joined = add_subgroup_flags(risk_joined)
    pit_joined = add_subgroup_flags(pit_joined)

    reject_audit = build_rejector_decision_reconstruction_audit(
        manifest_10c,
        slice_spec,
        frontier_row,
        reject_slice,
        reject_decision_derivation,
        reject_decision_hit_rate,
        primary,
        risk_on_pre_pit,
        risk_joined,
        evaluated,
        pit_joined,
        mismatch_risk,
        mismatch_pit,
    )
    outputs["rejector_decision_reconstruction_audit"] = write_df(TABLE_DIR / "rejector_decision_reconstruction_audit.csv", reject_audit)

    if reject_audit["risk_on_pre_pit_reject_join_hit_rate"].iloc[0] == 0 or reject_audit["pit_valid_reject_join_hit_rate"].iloc[0] == 0:
        blockers.append("reject_decision_join_hit_rate_zero")
    if blockers:
        return write_blocked_outputs(config, outputs, cache_outputs, blockers, " ".join(sys.argv))

    if reject_audit["duplicate_reject_join_key_n"].iloc[0] > 0:
        incomplete.append("duplicate_reject_join_key")
    if reject_audit["slice_filtered_primary_denominator_row_n"].iloc[0] != reject_audit["pre_scope_primary_denominator_row_n"].iloc[0]:
        incomplete.append("slice_primary_denominator_row_mismatch")
    if reject_audit["risk_on_pre_pit_reject_join_unmatched_n"].iloc[0] > 0:
        incomplete.append("risk_on_pre_pit_reject_join_unmatched")
    if reject_audit["pit_valid_reject_join_unmatched_n"].iloc[0] > 0:
        incomplete.append("pit_valid_reject_join_unmatched")
    mismatch_cols = [col for col in reject_audit.columns if col.endswith("_mismatch_n")]
    if int(reject_audit[mismatch_cols].sum(axis=1).iloc[0]) > 0:
        incomplete.append("reject_join_identity_mismatch")

    scope_recon = build_scope_reconciliation(primary, risk_on_pre_pit, evaluated, paths, params)
    outputs["scope_reconciliation_vs_upstream"] = write_df(TABLE_DIR / "scope_reconciliation_vs_upstream.csv", scope_recon)
    if scope_recon["reconciliation_status"].ne("ok").any():
        incomplete.append("denominator_drift_vs_upstream")

    denom_rows = [
        denom_contract.iloc[0].to_dict(),
        {
            "denominator_layer": "risk_on_pre_pit",
            "population_id": config["scope"]["population_id"],
            "rule_arm_id": config["scope"]["rule_arm_id"],
            "input_denominator_id": config["scope"]["input_denominator_id"],
            "denominator_id": config["scope"]["denominator_id"],
            "admission_status": config["scope"]["admission_status"],
            "readout_only_flag": config["scope"]["readout_only_flag"],
            "row_n": len(risk_on_pre_pit),
            "train_row_n": int(risk_on_pre_pit["split"].astype(str).eq("train").sum()),
            "validation_row_n": int(risk_on_pre_pit["split"].astype(str).eq("validation").sum()),
            "robustness_row_n": int(risk_on_pre_pit["split"].astype(str).eq("robustness").sum()),
            "canonical_id_missing_n": int(risk_on_pre_pit["binding_canonical_event_id"].map(nonempty).eq("").sum()),
            "denominator_status": "ok" if len(risk_on_pre_pit) > 0 else "risk_on_pre_pit_empty",
        },
        {
            "denominator_layer": "pit_valid_primary",
            "population_id": config["scope"]["population_id"],
            "rule_arm_id": config["scope"]["rule_arm_id"],
            "input_denominator_id": config["scope"]["input_denominator_id"],
            "denominator_id": config["scope"]["denominator_id"],
            "admission_status": config["scope"]["admission_status"],
            "readout_only_flag": config["scope"]["readout_only_flag"],
            "row_n": len(evaluated),
            "train_row_n": int(evaluated["split"].astype(str).eq("train").sum()),
            "validation_row_n": int(evaluated["split"].astype(str).eq("validation").sum()),
            "robustness_row_n": int(evaluated["split"].astype(str).eq("robustness").sum()),
            "canonical_id_missing_n": int(evaluated["binding_canonical_event_id"].map(nonempty).eq("").sum()),
            "denominator_status": "ok" if len(evaluated) > 0 else "pit_valid_empty",
        },
    ]
    outputs["denominator_contract_audit"] = write_df(TABLE_DIR / "denominator_contract_audit.csv", pd.DataFrame(denom_rows))

    denom_completeness = copy_or_build_denominator_completeness(paths, evaluated)
    outputs["denominator_completeness_st_delist_audit"] = write_df(
        TABLE_DIR / "denominator_completeness_st_delist_audit.csv", denom_completeness
    )
    if "left_tail_status_audit_status" in denom_completeness.columns and not denom_completeness["left_tail_status_audit_status"].astype(str).eq("ok").all():
        incomplete.append("left_tail_status_audit_incomplete")

    retention_recon = retention_reconciliation_vs_10c(primary_joined, risk_joined, frontier_row, params)
    outputs["rejector_retention_reconciliation_vs_10c"] = write_df(
        TABLE_DIR / "rejector_retention_reconciliation_vs_10c.csv", retention_recon
    )
    if retention_recon.loc[retention_recon["comparison_scope"].eq("risk_on_pre_pit"), "retention_reconciliation_status"].ne("ok").any():
        incomplete.append("risk_on_pre_pit_retention_recon_diff_gt_ceiling")

    unresolved_rate = safe_rate(int(pit_joined["class_unresolved_flag"].sum()), len(pit_joined))
    if unresolved_rate > params.class_unresolved_ceiling:
        incomplete.append("class_unresolved_rate_gt_ceiling")

    subgroup_counts = build_protected_subgroup_count_audit(pit_joined)
    outputs["protected_subgroup_count_audit"] = write_df(TABLE_DIR / "protected_subgroup_count_audit.csv", subgroup_counts)

    retention_rate = build_retention_rate_readout(pit_joined, risk_joined)
    outputs["retention_rate_readout"] = write_df(TABLE_DIR / "retention_rate_readout.csv", retention_rate)

    bootstrap_summary, bootstrap_raw = bootstrap_retention(pit_joined, params)
    outputs["bootstrap_retention_readout"] = write_df(TABLE_DIR / "bootstrap_retention_readout.csv", bootstrap_summary)
    cache_outputs["bootstrap_samples"] = write_parquet(LOCAL_CACHE_DIR / "bootstrap_samples.parquet", bootstrap_raw)

    metrics, gate_value, episode_conflict = build_non_discrimination_metrics(pit_joined, bootstrap_summary, params)
    outputs["non_discrimination_metric_readout"] = write_df(TABLE_DIR / "non_discrimination_metric_readout.csv", metrics)

    seed_readout = build_protected_subgroup_retention_readout(pit_joined, params)
    outputs["protected_subgroup_retention_readout"] = write_df(TABLE_DIR / "protected_subgroup_retention_readout.csv", seed_readout)

    multiple_audit = build_subgroup_multiple_comparison_audit(pit_joined, seed_readout, params)
    outputs["subgroup_multiple_comparison_audit"] = write_df(TABLE_DIR / "subgroup_multiple_comparison_audit.csv", multiple_audit)

    cache_outputs["retention_evaluated_denominator"] = write_parquet(
        LOCAL_CACHE_DIR / "retention_evaluated_denominator.parquet", pit_joined
    )

    final_status = final_status_from_gate(blockers, incomplete, gate_value, episode_conflict)
    summary = build_retention_summary(final_status, blockers, incomplete, gate_value, metrics, retention_recon, reject_audit)
    outputs["retention_summary"] = write_df(TABLE_DIR / "retention_summary.csv", summary)
    report = build_report(final_status, summary, scope_recon, retention_recon, subgroup_counts, metrics, seed_readout, multiple_audit, reject_audit)
    outputs["report"] = write_text(REPORT_PATH, report)

    manifest = build_manifest(config, outputs, cache_outputs, final_status, " ".join(sys.argv))
    write_json(MANIFEST_PATH, manifest)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Run 11B archetype protected retention readout.")
    parser.add_argument("--config", type=Path, default=CONFIG_PATH)
    args = parser.parse_args()
    manifest = run(args.config)
    print(json.dumps({"run_id": manifest["run_id"], "final_status": manifest["final_status"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
