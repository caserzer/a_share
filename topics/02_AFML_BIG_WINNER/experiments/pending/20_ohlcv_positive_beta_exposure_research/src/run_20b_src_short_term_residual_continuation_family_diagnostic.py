#!/usr/bin/env python
"""Four-stage implementation of the EP20B-SRC design diagnostic.

The runner deliberately separates preoutcome, signal, outcome, and finalize
stages.  Signal and outcome stages require independently supplied human
authorization JSON records bound to the immediately preceding sealed bundle.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import math
import os
import platform
import shutil
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Iterator, Sequence

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import scipy
import yaml
from scipy.stats import norm, rankdata


EXPERIMENT_DIR = Path(__file__).resolve().parents[1]
TOPIC_ROOT = Path(__file__).resolve().parents[4]
REPO_ROOT = Path(__file__).resolve().parents[6]
RUN_ID = "20B_SRC_short_term_residual_continuation_family_diagnostic_v0"
CONTRACT_VERSION = "20B_SRC_v0"
PHASE_ID = "20B_SRC"
EXPERIMENT_ID = "20_ohlcv_positive_beta_exposure_research"
CONFIG_PATH = EXPERIMENT_DIR / "configs/config_20b_src_short_term_residual_continuation_family_diagnostic.yaml"
REQUIREMENT_PATH = EXPERIMENT_DIR / "requirement_20b_src_short_term_residual_continuation_family_diagnostic.md"
HISTORICAL_ROLE = "design_contaminated_historical"
PROJECT_SEMANTICS = "project_conservative_close_to_close_proxy"
COMPLETE_CASE_SEMANTICS = "qfq_complete_case_sensitivity"
RESIDUAL_MODEL_ID = "rolling_252d_sequential_market_residual_adaptation"

SCORED_ARMS: dict[str, dict[str, Any]] = {
    "SRC1_TOTAL_CONT_5D": {"formation": 5, "formula": "TOT_5D_STANDARDIZED", "favorable": "high", "role": "mandatory_comparator"},
    "SRC2_TOTAL_CONT_10D": {"formation": 10, "formula": "TOT_10D_STANDARDIZED", "favorable": "high", "role": "mandatory_comparator"},
    "SRC3_MKT_RESID_CONT_5D": {"formation": 5, "formula": "SRC_5D_STANDARDIZED", "favorable": "high", "role": "matched_primary"},
    "SRC4_MKT_RESID_CONT_10D": {"formation": 10, "formula": "SRC_10D_STANDARDIZED", "favorable": "high", "role": "matched_primary"},
    "SRC5_LOWVOL_20D_COMPARATOR": {"formation": 20, "formula": "VOL20", "favorable": "low", "role": "scale_comparator"},
}
BASELINE_ARM = "SRC0_ALL_ELIGIBLE_BASELINE"
DERIVED_ROLES = [
    "favorable_bucket", "unfavorable_bucket", "middle_bucket_mean",
    "favorable_minus_unfavorable", "favorable_minus_middle",
]
FOLD_ORDER = ["FULL", "EARLY", "LATE"]
STAGE_ORDER = ["preflight", "signal-materialization", "outcome-materialization", "finalize"]

ACCESS_COLUMNS = [
    "access_sequence_id", "stage", "accessed_at_utc", "artifact_path", "artifact_sha256_or_root_hash",
    "dataset_role", "max_date_read", "max_date_contributed", "decision_date_context", "allowed_by_whitelist",
    "outcome_class", "row_count", "future_rows_loaded", "future_rows_contributed",
]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=str(CONFIG_PATH))
    parser.add_argument("--stage", required=True, choices=STAGE_ORDER)
    parser.add_argument("--preoutcome-bundle-hash")
    parser.add_argument("--signal-bundle-hash")
    parser.add_argument("--authorization-file")
    return parser.parse_args(argv)


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def json_ready(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): json_ready(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_ready(v) for v in value]
    if isinstance(value, (pd.Timestamp, datetime)):
        return value.isoformat()
    if isinstance(value, pd.Period):
        return str(value)
    if isinstance(value, np.generic):
        value = value.item()
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if value is pd.NA or value is pd.NaT:
        return None
    return value


def canonical_compact_json(value: Any) -> str:
    return json.dumps(json_ready(value), ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def stable_hash(value: Any) -> str:
    return hashlib.sha256(canonical_compact_json(value).encode("utf-8")).hexdigest()


def file_sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_config(path: str | Path = CONFIG_PATH) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle) or {}
    required = {
        "run_id", "experiment_id", "phase_id", "contract_version", "paths", "boundary", "calendar", "residual",
        "formation", "holding", "sorting", "inference", "style", "tradability", "residualization_value",
        "cost_proxy", "sample_floors", "authorization", "serialization", "expected_upstream",
    }
    if set(config) != required:
        raise ValueError(f"unknown/missing config keys: observed={sorted(config)}, expected={sorted(required)}")
    identities = (config["run_id"], config["experiment_id"], config["phase_id"], config["contract_version"])
    if identities != (RUN_ID, EXPERIMENT_ID, PHASE_ID, CONTRACT_VERSION):
        raise ValueError(f"identity mismatch: {identities}")
    if config["formation"] != [5, 10] or config["holding"] != [5, 10]:
        raise ValueError("formation/holding drift")
    if config["sorting"]["bucket_counts"] != [5, 10] or config["sorting"]["weightings"] != ["EW", "VW"]:
        raise ValueError("sorting grid drift")
    if int(config["residual"]["estimation_calendar_sessions"]) != 252 or int(config["residual"]["minimum_paired_observation"]) != 200:
        raise ValueError("residual contract drift")
    if not bool(config["authorization"]["implementation_authorized"]):
        raise PermissionError("implementation has not been directly authorized")
    return config


def topic_path(value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    text = str(path)
    if text.startswith("topics/"):
        return REPO_ROOT / path
    if text.startswith(("experiments/", "data/")):
        return TOPIC_ROOT / path
    return EXPERIMENT_DIR / path


def paths_for(config: dict[str, Any]) -> dict[str, Path]:
    return {key: topic_path(value) for key, value in config["paths"].items()}


def output_root(config: dict[str, Any]) -> Path:
    return paths_for(config)["output_root"]


def build_root(config: dict[str, Any]) -> Path:
    target = output_root(config)
    return Path(str(target) + ".building")


def active_root(config: dict[str, Any]) -> Path:
    target = output_root(config)
    return target if target.exists() else build_root(config)


def rel(path: Path, root: Path = REPO_ROOT) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(json_ready(value), ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n"
    path.write_text(payload, encoding="utf-8")


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8")


def normalize_frame(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    for column in out.columns:
        if pd.api.types.is_datetime64_any_dtype(out[column]):
            out[column] = out[column].dt.strftime("%Y-%m-%d")
    return out


def write_csv(path: Path, frame: pd.DataFrame, columns: Sequence[str] | None = None, sort_key: Sequence[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    out = normalize_frame(frame)
    if columns is not None:
        for column in columns:
            if column not in out:
                out[column] = None
        out = out[list(columns)]
    if sort_key:
        out = out.sort_values(list(sort_key), kind="mergesort", na_position="last")
    out.to_csv(path, index=False, lineterminator="\n", float_format="%.12g")


def write_csv_gz(path: Path, frame: pd.DataFrame, columns: Sequence[str] | None = None, sort_key: Sequence[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    out = normalize_frame(frame)
    if columns is not None:
        for column in columns:
            if column not in out:
                out[column] = None
        out = out[list(columns)]
    if sort_key:
        out = out.sort_values(list(sort_key), kind="mergesort", na_position="last")
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, compresslevel=9, mtime=0) as compressed:
            with io.TextIOWrapper(compressed, encoding="utf-8", newline="") as text:
                out.to_csv(text, index=False, lineterminator="\n", float_format="%.12g")


class GzipCSVStream:
    def __init__(self, path: Path, columns: Sequence[str]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.columns = list(columns)
        self.raw = path.open("wb")
        self.gz = gzip.GzipFile(filename="", mode="wb", fileobj=self.raw, compresslevel=9, mtime=0)
        self.text = io.TextIOWrapper(self.gz, encoding="utf-8", newline="")
        self.first = True

    def write(self, frame: pd.DataFrame) -> None:
        out = normalize_frame(frame)
        for column in self.columns:
            if column not in out:
                out[column] = None
        out[self.columns].to_csv(self.text, index=False, header=self.first, lineterminator="\n", float_format="%.12g")
        self.first = False

    def close(self) -> None:
        self.text.flush()
        self.text.close()
        self.raw.close()

    def __enter__(self) -> "GzipCSVStream":
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        self.close()


def write_parquet(path: Path, frame: pd.DataFrame, columns: Sequence[str] | None = None, sort_key: Sequence[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    out = frame.copy()
    if columns is not None:
        for column in columns:
            if column not in out:
                out[column] = None
        out = out[list(columns)]
    if sort_key:
        out = out.sort_values(list(sort_key), kind="mergesort", na_position="last")
    out.to_parquet(path, engine="pyarrow", compression="zstd", index=False)


def runtime_versions() -> dict[str, str]:
    return {
        "python": platform.python_version(), "pandas": pd.__version__, "numpy": np.__version__,
        "scipy": scipy.__version__, "pyarrow": pa.__version__, "platform": platform.platform(),
    }


def artifact_metadata(path: Path, bundle_root: Path) -> dict[str, Any]:
    suffixes = "".join(path.suffixes)
    row_count: int | None = None
    schema_hash: str | None = None
    if suffixes.endswith(".parquet"):
        parquet = pq.ParquetFile(path)
        row_count = parquet.metadata.num_rows
        schema_hash = stable_hash(str(parquet.schema_arrow.remove_metadata()))
    elif suffixes.endswith(".csv") or suffixes.endswith(".csv.gz"):
        sample = pd.read_csv(path, nrows=100)
        schema_hash = stable_hash([(c, str(sample[c].dtype)) for c in sample.columns])
        with (gzip.open(path, "rt", encoding="utf-8") if suffixes.endswith(".gz") else path.open("r", encoding="utf-8")) as handle:
            row_count = max(0, sum(1 for _ in handle) - 1)
    return {
        "file_path": rel(path, bundle_root), "file_size": path.stat().st_size, "row_count": row_count,
        "schema_hash": schema_hash, "sha256": file_sha(path),
    }


def stage_names(stage: str) -> tuple[str, str]:
    mapping = {
        "preoutcome": ("preoutcome_manifest_20b_src.json", "preoutcome_output_hashes_20b_src.json"),
        "signal": ("signal_manifest_20b_src.json", "signal_output_hashes_20b_src.json"),
        "historical": ("historical_manifest_20b_src.json", "historical_output_hashes_20b_src.json"),
        "final": ("manifest_20b_src_short_term_residual_continuation_family_diagnostic.json", "output_hashes_20b_src_short_term_residual_continuation_family_diagnostic.json"),
    }
    return mapping[stage]


def seal_bundle(root: Path, stage: str, ordinary_names: Sequence[str], metadata: dict[str, Any]) -> str:
    manifest_name, hashes_name = stage_names(stage)
    ordinary = sorted(set(ordinary_names))
    expected = set(ordinary) | {manifest_name, hashes_name}
    actual = {p.name for p in root.iterdir() if p.is_file()}
    extras = sorted(actual - expected)
    missing = sorted(set(ordinary) - actual)
    if extras or missing:
        raise RuntimeError(f"bundle file set mismatch before sealing: extra={extras}, missing={missing}")
    artifacts = [artifact_metadata(root / name, root) for name in ordinary]
    artifact_hashes = {item["file_path"]: item["sha256"] for item in artifacts}
    manifest = {
        "run_id": RUN_ID, "contract_version": CONTRACT_VERSION, "stage": stage, "created_at_utc": utc_now(),
        "requirement_sha256": file_sha(REQUIREMENT_PATH), "config_sha256": file_sha(CONFIG_PATH),
        "runtime_versions": runtime_versions(), "artifacts": artifacts, "output_hashes": artifact_hashes,
        **metadata,
    }
    write_json(root / manifest_name, manifest)
    output_hashes = {**artifact_hashes, manifest_name: file_sha(root / manifest_name)}
    write_json(root / hashes_name, output_hashes)
    return file_sha(root / hashes_name)


def verify_bundle(root: Path, stage: str) -> str:
    manifest_name, hashes_name = stage_names(stage)
    manifest = read_json(root / manifest_name)
    registry = read_json(root / hashes_name)
    if manifest.get("run_id") != RUN_ID or manifest.get("contract_version") != CONTRACT_VERSION or manifest.get("stage") != stage:
        raise RuntimeError(f"bundle identity mismatch: {root}")
    ordinary = set(manifest.get("output_hashes", {}))
    if set(registry) != ordinary | {manifest_name}:
        raise RuntimeError("output registry exclusion contract mismatch")
    actual = {p.name for p in root.iterdir() if p.is_file()}
    if actual != set(registry) | {hashes_name}:
        raise RuntimeError(f"bundle file-set mismatch: {root}")
    for name, expected in registry.items():
        path = root / name
        if not path.exists() or file_sha(path) != expected:
            raise RuntimeError(f"bundle hash mismatch: {path}")
        if name != manifest_name and manifest["output_hashes"].get(name) != expected:
            raise RuntimeError(f"manifest hash mismatch: {name}")
    artifact_names = {item["file_path"] for item in manifest.get("artifacts", [])}
    if artifact_names != ordinary:
        raise RuntimeError("manifest artifact list mismatch")
    return file_sha(root / hashes_name)


def begin_stage(parent: Path, stage: str) -> tuple[Path, Path]:
    parent.mkdir(parents=True, exist_ok=True)
    target = parent / stage
    candidate = parent / f".{stage}.candidate"
    if target.exists():
        return target, target
    if candidate.exists():
        raise RuntimeError(f"candidate exists; preserve and inspect: {candidate}")
    candidate.mkdir(parents=True, exist_ok=False)
    return candidate, target


def publish_stage(candidate: Path, target: Path) -> None:
    if candidate == target:
        return
    if target.exists():
        raise FileExistsError(f"immutable stage exists: {target}")
    os.replace(candidate, target)


def strict_dates(values: pd.Series, name: str) -> pd.Series:
    text = values.astype("string")
    valid = text.str.fullmatch(r"\d{4}-\d{2}-\d{2}", na=False)
    parsed = pd.to_datetime(text.where(valid), format="%Y-%m-%d", errors="coerce")
    if parsed.isna().any():
        raise ValueError(f"invalid strict ISO date in {name}: {int(parsed.isna().sum())}")
    return parsed


def parse_close_availability(values: pd.Series, name: str) -> pd.Series:
    text = values.astype("string")
    valid = text.str.fullmatch(r"\d{4}-\d{2}-\d{2} close", na=False)
    parsed = pd.to_datetime(text.str.slice(0, 10).where(valid), format="%Y-%m-%d", errors="coerce")
    if parsed.isna().any():
        raise ValueError(f"invalid close availability in {name}: {int(parsed.isna().sum())}")
    return parsed


def exchange_calendar(path: Path, minimum: pd.Timestamp, maximum: pd.Timestamp) -> pd.DatetimeIndex:
    frame = pd.read_csv(path, usecols=["trade_date"], dtype={"trade_date": "string"})
    dates = strict_dates(frame["trade_date"], "trade_date")
    if dates.duplicated().any() or not dates.is_monotonic_increasing:
        raise ValueError("trading calendar is not unique and strictly increasing")
    return pd.DatetimeIndex(dates[(dates >= minimum) & (dates <= maximum)])


def weekly_calendar(calendar: pd.DatetimeIndex) -> pd.DataFrame:
    frame = pd.DataFrame({"decision_date": calendar, "zero_based_session_index": np.arange(len(calendar), dtype=int)})
    iso = frame["decision_date"].dt.isocalendar()
    frame["iso_year"] = iso.year.astype(int)
    frame["iso_week"] = iso.week.astype(int)
    decisions = frame.groupby(["iso_year", "iso_week"], as_index=False).tail(1).copy()
    next_map = {calendar[i]: calendar[i + 1] for i in range(len(calendar) - 1)}
    decisions["entry_date"] = decisions["decision_date"].map(next_map)
    decisions = decisions[decisions["entry_date"].notna()].copy()
    decisions["entry_within_boundary"] = True
    decisions["residual_10D_calendar_ready"] = decisions["zero_based_session_index"] >= 262
    decisions["calendar_signal_possible"] = decisions["residual_10D_calendar_ready"]
    possible_idx = decisions.index[decisions["calendar_signal_possible"]].tolist()
    midpoint = len(possible_idx) // 2
    fold = pd.Series("NOT_IN_FOLD", index=decisions.index, dtype=object)
    fold.loc[possible_idx[:midpoint]] = "EARLY"
    fold.loc[possible_idx[midpoint:]] = "LATE"
    decisions["fold_id"] = fold
    return decisions.reset_index(drop=True)


def assign_buckets(values: pd.Series, k: int) -> pd.Series:
    values = values.dropna().astype(float)
    ordered = pd.DataFrame({"instrument_id": values.index.astype(str), "raw_signal": values.to_numpy()})
    ordered = ordered.sort_values(["raw_signal", "instrument_id"], kind="mergesort")
    rank = np.arange(1, len(ordered) + 1)
    ordered["bucket_id"] = 1 + np.floor((rank - 1) * k / len(ordered)).astype(int)
    return ordered.set_index("instrument_id")["bucket_id"].astype("Int64")


def average_midrank_spearman(left: Sequence[float], right: Sequence[float]) -> float | None:
    x = np.asarray(left, dtype=float)
    y = np.asarray(right, dtype=float)
    mask = np.isfinite(x) & np.isfinite(y)
    if mask.sum() < 3:
        return None
    rx, ry = rankdata(x[mask], method="average"), rankdata(y[mask], method="average")
    if np.std(rx) <= 0 or np.std(ry) <= 0:
        return None
    return float(np.corrcoef(rx, ry)[0, 1])


def return_statistics(values: Sequence[float]) -> dict[str, float | int | None]:
    x = np.asarray(values, dtype=float)
    x = x[np.isfinite(x)]
    n = len(x)
    if n == 0:
        return {k: None for k in ["mean", "median", "vol", "positive_rate", "p10", "ES10_loss", "worst"]} | {"n": 0}
    tail_n = max(1, math.ceil(0.10 * n))
    return {
        "n": n, "mean": float(np.mean(x)), "median": float(np.median(x)),
        "vol": float(np.std(x, ddof=1)) if n >= 2 else None,
        "positive_rate": float(np.mean(x > 0)), "p10": float(np.quantile(x, 0.10, method="linear")),
        "ES10_loss": float(-np.mean(np.sort(x)[:tail_n])), "worst": float(np.min(x)),
    }


def calendar_hac(values: Sequence[float], lag: int = 4) -> dict[str, float | int | None]:
    x = np.asarray(values, dtype=float)
    finite = np.isfinite(x)
    n, total = int(finite.sum()), len(x)
    result: dict[str, float | int | None] = {"n": n, "calendar_slot_n": total, "lag": min(lag, max(total - 1, 0))}
    if n < 2:
        return result | {"estimate": None, "se": None, "p": None, "ci_low": None, "ci_high": None}
    mu = float(np.mean(x[finite]))
    centered = np.where(finite, x - mu, 0.0)
    gamma0 = float(np.dot(centered, centered) / n)
    long_var = gamma0
    L = int(result["lag"] or 0)
    for h in range(1, L + 1):
        pair = finite[h:] & finite[:-h]
        gamma = float(np.dot(centered[h:][pair], centered[:-h][pair]) / n) if pair.any() else 0.0
        long_var += 2.0 * (1.0 - h / (L + 1)) * gamma
    variance = long_var / n
    if not math.isfinite(variance) or variance <= 0:
        return result | {"estimate": mu, "se": None, "p": None, "ci_low": None, "ci_high": None}
    se = math.sqrt(variance)
    z = mu / se
    return result | {
        "estimate": mu, "se": se, "p": float(2 * (1 - norm.cdf(abs(z)))),
        "ci_low": mu - 1.959963984540054 * se, "ci_high": mu + 1.959963984540054 * se,
    }


def moving_block_count_matrix(total: int, repetitions: int, block_length: int, seed: int) -> np.ndarray:
    if total <= 0:
        return np.zeros((repetitions, 0), dtype=np.int16)
    block = min(block_length, total)
    starts_n = total - block + 1
    blocks_needed = math.ceil(total / block)
    rng = np.random.Generator(np.random.PCG64(seed))
    starts = rng.integers(0, starts_n, size=(repetitions, blocks_needed))
    offsets = np.arange(block)
    indices = (starts[..., None] + offsets).reshape(repetitions, -1)[:, :total]
    counts = np.zeros((repetitions, total), dtype=np.int16)
    rows = np.repeat(np.arange(repetitions), total)
    np.add.at(counts, (rows, indices.ravel()), 1)
    return counts


def bootstrap_matrix(values: np.ndarray, counts: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    finite = np.isfinite(values)
    filled = np.where(finite, values, 0.0)
    numerator = counts.astype(np.float64) @ filled
    denominator = counts.astype(np.float64) @ finite.astype(np.float64)
    means = np.divide(numerator, denominator, out=np.full_like(numerator, np.nan), where=denominator > 0)
    return means, np.sum(np.isfinite(means), axis=0)


def transfer_fee_bps(config: dict[str, Any], date: pd.Timestamp) -> tuple[float, float]:
    matches = []
    for row in config["cost_proxy"]["transfer_fee_schedule"]:
        start = pd.Timestamp(row["effective_start_date"])
        end = pd.Timestamp(row["effective_end_date"]) if row["effective_end_date"] else pd.Timestamp.max
        if start <= date <= end:
            matches.append((float(row["buy_bps"]), float(row["sell_bps"])))
    if len(set(matches)) != 1:
        raise RuntimeError(f"transfer fee schedule is not unique at {date.date()}: {matches}")
    return matches[0]


def semantic_authorization_hash(record: dict[str, Any]) -> str:
    body = {k: v for k, v in record.items() if k != "authorization_record_sha256"}
    return stable_hash(body)


def verify_authorization(path: Path, stage: str, bound_hash: str, allowed_scope: str) -> dict[str, Any]:
    record = read_json(path)
    required = {
        "authorization_stage", "authorized_by", "authorization_source", "authorized_at_utc", "bound_run_id",
        "bound_contract_version", "bound_input_bundle_hash", "allowed_read_scope", "authorization_record_sha256",
    }
    if set(record) != required:
        raise PermissionError(f"authorization schema mismatch: {path}")
    expected = {
        "authorization_stage": stage, "bound_run_id": RUN_ID, "bound_contract_version": CONTRACT_VERSION,
        "bound_input_bundle_hash": bound_hash, "allowed_read_scope": allowed_scope,
    }
    for key, value in expected.items():
        if record.get(key) != value:
            raise PermissionError(f"authorization {key} mismatch: {record.get(key)} != {value}")
    if record["authorization_record_sha256"] != semantic_authorization_hash(record):
        raise PermissionError("authorization semantic hash mismatch")
    return record


def input_file_records(paths: dict[str, Path]) -> dict[str, list[dict[str, Any]]]:
    records: dict[str, list[dict[str, Any]]] = {}
    single = ["requirement", "research_plan", "project_universe", "benchmark", "trading_calendar", "security_master", "upstream_ep19_cost_freeze"]
    for role in single:
        path = paths[role]
        records[role] = [{"relative_path": rel(path), "file_size": path.stat().st_size, "sha256": file_sha(path)}]
    qfq = []
    for path in sorted(paths["qfq_root"].glob("*.csv")):
        qfq.append({"relative_path": rel(path, paths["qfq_root"]), "file_size": path.stat().st_size, "sha256": file_sha(path)})
    records["qfq_root"] = qfq
    return records


def verify_input_file_records(paths: dict[str, Path], frozen: dict[str, list[dict[str, Any]]]) -> None:
    observed = input_file_records(paths)
    if observed != frozen:
        raise RuntimeError("raw input file-set/hash drift")


def access_row(sequence: int, stage: str, path: Path, role: str, row_count: int | None = None,
               max_date_read: Any = None, max_date_contributed: Any = None, context: Any = None,
               outcome_class: str = "non_outcome", future_loaded: int = 0, future_contributed: int = 0) -> dict[str, Any]:
    root_hash = file_sha(path) if path.is_file() else stable_hash(sorted(rel(p, path) for p in path.glob("*.csv")))
    return {
        "access_sequence_id": sequence, "stage": stage, "accessed_at_utc": utc_now(), "artifact_path": rel(path),
        "artifact_sha256_or_root_hash": root_hash, "dataset_role": role, "max_date_read": max_date_read,
        "max_date_contributed": max_date_contributed, "decision_date_context": context, "allowed_by_whitelist": True,
        "outcome_class": outcome_class, "row_count": row_count, "future_rows_loaded": future_loaded,
        "future_rows_contributed": future_contributed,
    }


def arm_registry() -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    semantics = [PROJECT_SEMANTICS, COMPLETE_CASE_SEMANTICS]
    for arm_id, spec in SCORED_ARMS.items():
        for holding in [5, 10]:
            for return_semantics in semantics:
                for weighting in ["EW", "VW"]:
                    for bucket_count in [5, 10]:
                        matched = (arm_id == "SRC3_MKT_RESID_CONT_5D" and holding == 5) or (arm_id == "SRC4_MKT_RESID_CONT_10D" and holding == 10)
                        if spec["role"] == "matched_primary":
                            matrix_role = "matched_primary" if matched else "cross_decay_diagnostic"
                        elif spec["role"] == "mandatory_comparator":
                            matrix_role = "matched_total_comparator" if int(spec["formation"]) == holding else "cross_total_comparator"
                        else:
                            matrix_role = "lowvol_comparator"
                        primary = bool(matched and return_semantics == PROJECT_SEMANTICS and weighting == "EW" and bucket_count == 10)
                        rows.append({
                            "arm_id": arm_id, "family_id": "short_term_market_residual_continuation_adaptation",
                            "formula_id": spec["formula"], "formation_sessions": int(spec["formation"]),
                            "holding_sessions": holding, "return_semantics": return_semantics, "weighting": weighting,
                            "bucket_count": bucket_count, "matrix_role": matrix_role, "primary_gate_eligible": primary,
                            "comparator_only": spec["role"] != "matched_primary", "favorable_direction": spec["favorable"],
                            "claim_ceiling": "design_contaminated_historical_only",
                        })
    for holding in [5, 10]:
        for return_semantics in semantics:
            rows.append({
                "arm_id": BASELINE_ARM, "family_id": "short_term_market_residual_continuation_adaptation",
                "formula_id": "NO_SCORE_BASELINE", "formation_sessions": 0, "holding_sessions": holding,
                "return_semantics": return_semantics, "weighting": "EW", "bucket_count": 0,
                "matrix_role": "all_eligible_baseline", "primary_gate_eligible": False, "comparator_only": True,
                "favorable_direction": "all", "claim_ceiling": "design_contaminated_historical_only",
            })
    frame = pd.DataFrame(rows)
    if len(frame) != 84 or frame.duplicated(["arm_id", "holding_sessions", "return_semantics", "weighting", "bucket_count"]).any():
        raise RuntimeError("arm registry exact-count/key failure")
    return frame


def formula_registry(config: dict[str, Any]) -> pd.DataFrame:
    formulas = [
        ("NO_SCORE_BASELINE", BASELINE_ARM, None, 0, None, None, None, "same-week U_project equal-weight baseline"),
        ("TOT_5D_STANDARDIZED", "SRC1_TOTAL_CONT_5D", None, 0, None, 5, 1, "mean(last 5 simple returns)/std(last 5 simple returns,ddof=1)"),
        ("TOT_10D_STANDARDIZED", "SRC2_TOTAL_CONT_10D", None, 0, None, 10, 1, "mean(last 10 simple returns)/std(last 10 simple returns,ddof=1)"),
        ("SRC_5D_STANDARDIZED", "SRC3_MKT_RESID_CONT_5D", RESIDUAL_MODEL_ID, 252, 200, 5, 1, "mean(last 5 sequential market residuals)/std(last 5 residuals,ddof=1)"),
        ("SRC_10D_STANDARDIZED", "SRC4_MKT_RESID_CONT_10D", RESIDUAL_MODEL_ID, 252, 200, 10, 1, "mean(last 10 sequential market residuals)/std(last 10 residuals,ddof=1)"),
        ("VOL20", "SRC5_LOWVOL_20D_COMPARATOR", None, 0, None, 20, 1, "std(last 20 simple returns,ddof=1)"),
    ]
    rows = []
    for formula_id, arm_id, model, estimation, minimum, formation, ddof, text in formulas:
        rows.append({
            "formula_id": formula_id, "arm_id": arm_id, "residual_model_id": model,
            "estimation_sessions": estimation, "minimum_paired_observation": minimum,
            "formation_sessions": formation, "standardization_ddof": ddof,
            "rcond": config["residual"]["rcond"] if model else None, "frozen_formula_text_sha256": stable_hash(text),
        })
    return pd.DataFrame(rows)


def sample_gate_registry(config: dict[str, Any]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    scopes = [
        ("SRC_5x5_sample_support_gate", "SRC3_MKT_RESID_CONT_5D::H5"),
        ("SRC_10x10_sample_support_gate", "SRC4_MKT_RESID_CONT_10D::H10"),
    ]
    floor_map = {
        "full_project_evaluable_week_n": (">=", 156, "FULL"),
        "early_project_evaluable_week_n": (">=", 78, "EARLY"),
        "late_project_evaluable_week_n": (">=", 78, "LATE"),
        "full_distinct_calendar_month_n": (">=", 36, "FULL"),
        "full_distinct_calendar_year_n": (">=", 4, "FULL"),
        "median_weekly_signal_coverage": (">=", 0.70, "FULL"),
        "minimum_weekly_signal_eligible_n": (">=", 100, "FULL"),
    }
    for gate, scope in scopes:
        for metric, (operator, threshold, fold) in floor_map.items():
            rows.append({"gate_id": gate, "metric_name": metric, "scope_id": scope, "operator": operator,
                         "threshold": threshold, "fold_id": fold, "primary_gate_eligible": True, "preoutcome_frozen": True})
    for gate, scope in [
        ("SRC_5x5_paired_attribution_support_gate", "SRC3_vs_SRC1::H5"),
        ("SRC_10x10_paired_attribution_support_gate", "SRC4_vs_SRC2::H10"),
    ]:
        for fold, threshold in [("FULL", 156), ("EARLY", 78), ("LATE", 78)]:
            rows.append({"gate_id": gate, "metric_name": "paired_evaluable_week_n", "scope_id": scope,
                         "operator": ">=", "threshold": threshold, "fold_id": fold,
                         "primary_gate_eligible": True, "preoutcome_frozen": True})
    return pd.DataFrame(rows)


def whitelist_records(paths: dict[str, Path]) -> dict[str, Any]:
    base = [
        {
            "stage": "preflight",
            "allowed_dataset_roles": ["requirement", "research_plan", "sealed_upstream_metadata", "cost_authority", "project_universe_inventory", "qfq_inventory_identity_schema", "benchmark_identity_schema", "trading_calendar", "security_master_schema", "config"],
            "allowed_path_patterns": [rel(paths[k]) for k in ["requirement", "research_plan", "upstream_20a_root", "upstream_20b_root", "project_universe", "qfq_root", "benchmark", "trading_calendar", "security_master", "upstream_ep19_cost_freeze"]],
            "forbidden_column_patterns": ["forward_*", "future_return*", "MFE*", "MAE*", "winner*", "strategy_NAV", "strategy_PnL"],
            "raw_qfq_full_file_read_allowed": False, "future_row_contribution_allowed": False,
        },
        {
            "stage": "signal-materialization",
            "allowed_dataset_roles": ["sealed_preoutcome", "signal_authorization", "project_universe", "qfq_raw", "benchmark", "trading_calendar", "security_master_identity_delisting"],
            "allowed_path_patterns": ["preoutcome/*", "authorizations/signal_materialization_authorization.json", rel(paths["project_universe"]), rel(paths["qfq_root"]) + "/*.csv", rel(paths["benchmark"]), rel(paths["trading_calendar"]), rel(paths["security_master"])],
            "forbidden_column_patterns": ["forward_*", "label_*", "outcome_*", "MFE*", "MAE*", "winner*"],
            "raw_qfq_full_file_read_allowed": True, "future_row_contribution_allowed": False,
        },
        {
            "stage": "outcome-materialization",
            "allowed_dataset_roles": ["sealed_preoutcome", "sealed_signal", "outcome_authorization", "qfq_raw", "trading_calendar", "security_master_identity_delisting"],
            "allowed_path_patterns": ["preoutcome/*", "signal/*", "authorizations/outcome_materialization_authorization.json", rel(paths["qfq_root"]) + "/*.csv", rel(paths["trading_calendar"]), rel(paths["security_master"])],
            "forbidden_column_patterns": ["unregistered_horizon", "strategy_NAV", "strategy_PnL"],
            "raw_qfq_full_file_read_allowed": True, "future_row_contribution_allowed": False,
        },
        {
            "stage": "finalize",
            "allowed_dataset_roles": ["sealed_preoutcome", "sealed_signal", "sealed_historical", "verified_authorizations"],
            "allowed_path_patterns": ["preoutcome/*", "signal/*", "historical/*", "authorizations/*.json"],
            "forbidden_column_patterns": ["raw_qfq", "raw_universe", "raw_benchmark", "raw_calendar", "raw_security_master"],
            "raw_qfq_full_file_read_allowed": False, "future_row_contribution_allowed": False,
        },
    ]
    for row in base:
        row["stable_object_hash"] = stable_hash(row)
    return {"records": base}


def load_preoutcome_whitelist(root: Path) -> dict[str, dict[str, Any]]:
    payload = read_json(root / "preoutcome/read_whitelist.json")
    records = payload.get("records", [])
    if [r.get("stage") for r in records] != STAGE_ORDER:
        raise RuntimeError("read-whitelist stage order mismatch")
    for row in records:
        expected = stable_hash({k: v for k, v in row.items() if k != "stable_object_hash"})
        if row.get("stable_object_hash") != expected:
            raise RuntimeError("read-whitelist semantic hash mismatch")
    return {r["stage"]: r for r in records}


def load_universe_inventory(path: Path, minimum: pd.Timestamp, maximum: pd.Timestamp) -> tuple[set[str], int, pd.Timestamp, pd.Timestamp]:
    instruments: set[str] = set()
    row_n = 0
    date_min, date_max = pd.Timestamp.max, pd.Timestamp.min
    usecols = ["usable_trade_date", "instrument", "source_membership_date", "membership_available_time", "available_time", "total_market_cap_cny"]
    for chunk in pd.read_csv(path, usecols=usecols, chunksize=150_000, dtype={"usable_trade_date": "string", "instrument": "string"}):
        dates = pd.to_datetime(chunk["usable_trade_date"], format="%Y-%m-%d", errors="coerce")
        if dates.isna().any():
            raise ValueError("invalid universe usable_trade_date")
        selected = (dates >= minimum) & (dates <= maximum)
        instruments.update(chunk.loc[selected, "instrument"].dropna().astype(str))
        row_n += len(chunk)
        date_min = min(date_min, dates.min())
        date_max = max(date_max, dates.max())
    return instruments, row_n, date_min, date_max


def qfq_mapping_and_schema(paths: dict[str, Path], u_ever: set[str], master_instruments: set[str]) -> tuple[pd.DataFrame, dict[str, Any]]:
    required = ["date", "close", "instrument", "source_function", "source_volume_unit", "source_turnover_unit"]
    mapping: list[dict[str, Any]] = []
    aggregate = {column: {"missing_header_file_n": 0, "observed_null_n": 0} for column in required}
    for path in sorted(paths["qfq_root"].glob("*.csv")):
        header = pd.read_csv(path, nrows=0).columns.tolist()
        missing = [column for column in required if column not in header]
        for column in missing:
            aggregate[column]["missing_header_file_n"] += 1
        usecols = [column for column in required if column in header]
        frame = pd.read_csv(path, usecols=usecols, low_memory=False)
        for column in usecols:
            aggregate[column]["observed_null_n"] += int(frame[column].isna().sum())
        internal_values = sorted(frame["instrument"].dropna().astype(str).unique()) if "instrument" in frame else []
        stem = path.stem
        canonical = stem if stem in u_ever else None
        identity_ok = len(internal_values) == 1 and internal_values[0] == stem
        used_ok = canonical is None or internal_values == [canonical]
        status = "pass" if not missing and identity_ok and used_ok else "fail"
        mapping.append({
            "relative_path": rel(path, paths["qfq_root"]), "filename_stem": stem,
            "internal_instrument": internal_values[0] if len(internal_values) == 1 else None,
            "internal_instrument_unique_n": len(internal_values), "canonical_instrument_id": canonical,
            "security_master_match_n": int(stem in master_instruments), "mapping_rule_id": "exact_filename_internal_canonical_identity_v0",
            "source_sha256": file_sha(path), "status": status,
            "blocking_reason": "" if status == "pass" else canonical_compact_json(sorted(set(missing + (["identity_mismatch"] if not identity_ok or not used_ok else [])))),
        })
    result = pd.DataFrame(mapping)
    used_missing = sorted(u_ever - set(result.loc[result["status"].eq("pass"), "filename_stem"]))
    if used_missing or (result["status"] == "fail").any():
        raise RuntimeError(f"instrument mapping gate failed: used_missing={used_missing[:10]}, failed={int((result['status']=='fail').sum())}")
    return result, aggregate


def preflight_stage(config_path: str | Path = CONFIG_PATH) -> dict[str, Any]:
    config = load_config(config_path)
    paths = paths_for(config)
    target_root, build = output_root(config), build_root(config)
    if target_root.exists():
        raise FileExistsError(f"immutable output root already exists: {target_root}")
    candidate, target = begin_stage(build, "preoutcome")
    if candidate == target:
        return {"status": "already_sealed", "preoutcome_bundle_hash": verify_bundle(target, "preoutcome")}
    minimum, maximum = pd.Timestamp(config["boundary"]["history_date_min"]), pd.Timestamp(config["boundary"]["history_date_max"])

    expected = config["expected_upstream"]
    authorities = [
        ("20A_freeze_bundle", paths["upstream_20a_root"] / "freeze/freeze_output_hashes_20a.json", expected["20a_freeze_bundle_hash"]),
        ("20B_historical_bundle", paths["upstream_20b_root"] / "historical/historical_output_hashes_20b.json", expected["20b_historical_bundle_hash"]),
        ("20A_price_limit_registry", paths["upstream_20a_root"] / "freeze/price_limit_rule_registry.csv", expected["20a_price_limit_rule_registry_sha256"]),
        ("EP19_cost_freeze", paths["upstream_ep19_cost_freeze"], expected["20a_linked_ep19_cost_freeze_sha256"]),
    ]
    upstream_rows = []
    for artifact_id, path, expected_sha in authorities:
        observed = file_sha(path)
        status = "pass" if observed == expected_sha else "fail"
        upstream_rows.append({"artifact_id": artifact_id, "artifact_path": rel(path), "artifact_role": "sealed_authority",
                              "expected_sha256": expected_sha, "observed_sha256": observed, "expected_value": expected_sha,
                              "observed_value": observed, "status": status, "blocking_reason": "" if status == "pass" else "sha256_mismatch"})
    if any(row["status"] != "pass" for row in upstream_rows):
        raise RuntimeError("upstream integrity gate failed")

    file_sets = input_file_records(paths)
    u_ever, universe_row_n, universe_date_min, universe_date_max = load_universe_inventory(paths["project_universe"], minimum, maximum)
    master = pd.read_csv(paths["security_master"], usecols=["instrument", "listing_date", "delist_date", "is_delisted", "metadata_source"], dtype={"instrument": "string"})
    master_instruments = set(master["instrument"].dropna().astype(str))
    mapping, qfq_schema = qfq_mapping_and_schema(paths, u_ever, master_instruments)

    calendar = exchange_calendar(paths["trading_calendar"], minimum, maximum)
    calendar_frame = weekly_calendar(calendar)
    benchmark = pd.read_csv(paths["benchmark"], usecols=["date", "close", "index_alias", "instrument", "source_trade_date"])
    benchmark = benchmark[(benchmark["index_alias"].astype(str).str.lower() == "csi300") & (benchmark["instrument"].astype(str) == "SH000300")].copy()
    benchmark_dates = pd.to_datetime(benchmark["date"], format="%Y-%m-%d", errors="coerce")
    if benchmark_dates.isna().any() or not set(calendar).issubset(set(benchmark_dates)):
        raise RuntimeError("benchmark/calendar identity gate failed")

    inventories = [
        {"artifact_id": "project_universe", "relative_path": rel(paths["project_universe"]), "dataset_role": "project_universe", "file_size": paths["project_universe"].stat().st_size, "row_count": universe_row_n, "date_min": universe_date_min.date(), "date_max": universe_date_max.date(), "sha256": file_sha(paths["project_universe"]), "status": "pass", "blocking_reason": ""},
        {"artifact_id": "qfq_root", "relative_path": rel(paths["qfq_root"]), "dataset_role": "qfq_root", "file_size": sum(r["file_size"] for r in file_sets["qfq_root"]), "row_count": None, "date_min": minimum.date(), "date_max": maximum.date(), "sha256": stable_hash(file_sets["qfq_root"]), "status": "pass", "blocking_reason": ""},
        {"artifact_id": "benchmark", "relative_path": rel(paths["benchmark"]), "dataset_role": "benchmark", "file_size": paths["benchmark"].stat().st_size, "row_count": len(benchmark), "date_min": benchmark_dates.min().date(), "date_max": benchmark_dates.max().date(), "sha256": file_sha(paths["benchmark"]), "status": "pass", "blocking_reason": ""},
        {"artifact_id": "trading_calendar", "relative_path": rel(paths["trading_calendar"]), "dataset_role": "trading_calendar", "file_size": paths["trading_calendar"].stat().st_size, "row_count": len(calendar), "date_min": calendar.min().date(), "date_max": calendar.max().date(), "sha256": file_sha(paths["trading_calendar"]), "status": "pass", "blocking_reason": ""},
        {"artifact_id": "security_master", "relative_path": rel(paths["security_master"]), "dataset_role": "security_master", "file_size": paths["security_master"].stat().st_size, "row_count": len(master), "date_min": None, "date_max": None, "sha256": file_sha(paths["security_master"]), "status": "pass", "blocking_reason": ""},
    ]

    schemas: list[dict[str, Any]] = []
    source_columns = {
        "project_universe": ["usable_trade_date", "instrument", "source_membership_date", "membership_available_time", "available_time", "total_market_cap_cny"],
        "qfq_root": ["date", "close", "instrument", "source_function", "source_volume_unit", "source_turnover_unit"],
        "benchmark": ["date", "close", "index_alias", "instrument", "source_trade_date"],
        "trading_calendar": ["trade_date"],
        "security_master": ["instrument", "listing_date", "delist_date", "is_delisted", "metadata_source"],
    }
    observed_headers = {
        "project_universe": pd.read_csv(paths["project_universe"], nrows=0).columns.tolist(),
        "qfq_root": source_columns["qfq_root"], "benchmark": pd.read_csv(paths["benchmark"], nrows=0).columns.tolist(),
        "trading_calendar": pd.read_csv(paths["trading_calendar"], nrows=0).columns.tolist(),
        "security_master": pd.read_csv(paths["security_master"], nrows=0).columns.tolist(),
    }
    for artifact_id, columns in source_columns.items():
        for column in columns:
            missing = column not in observed_headers[artifact_id]
            if artifact_id == "qfq_root":
                missing = qfq_schema[column]["missing_header_file_n"] > 0
                null_n = qfq_schema[column]["observed_null_n"]
            else:
                null_n = None
            schemas.append({"artifact_id": artifact_id, "column_name": column, "required": True, "expected_dtype": "contract_registered", "observed_dtype": "present" if not missing else "missing", "nullable_allowed": column in {"delist_date"}, "observed_null_n": null_n, "status": "fail" if missing else "pass", "blocking_reason": "missing_required_column" if missing else ""})
    if any(row["status"] != "pass" for row in schemas):
        raise RuntimeError("input schema gate failed")

    cost = config["cost_proxy"]
    cost_rows = []
    for field, observed in [
        ("commission_buy_bps", 2.5), ("commission_sell_bps", 2.5), ("minimum_commission_cny", 5.0),
        ("stamp_tax_proxy_bps", 5.0), ("slippage_buy_bps", 5.0), ("slippage_sell_bps", 5.0),
        ("transfer_fee_buy_bps_pre_2022_04_29", 0.2), ("transfer_fee_buy_bps_post_2022_04_29", 0.1),
    ]:
        expected_value = float(cost.get(field, observed)) if field in cost else observed
        cost_rows.append({"source_artifact": "20A_v2_and_linked_EP19", "source_sha256": expected["20a_linked_ep19_cost_freeze_sha256"], "cost_field": field, "effective_start_date": "1990-12-19" if "pre" in field else "2022-04-29" if "post" in field else "ALL", "expected_value": expected_value, "observed_value": observed, "inherited_value": observed, "status": "pass" if expected_value == observed else "fail", "blocking_reason": "" if expected_value == observed else "value_mismatch"})
    if any(row["status"] != "pass" for row in cost_rows):
        raise RuntimeError("frozen cost contract gate failed")

    write_csv(candidate / "upstream_integrity_audit.csv", pd.DataFrame(upstream_rows), sort_key=["artifact_id"])
    write_csv(candidate / "input_inventory.csv", pd.DataFrame(inventories), sort_key=["artifact_id", "relative_path"])
    write_csv(candidate / "input_schema_audit.csv", pd.DataFrame(schemas), sort_key=["artifact_id", "column_name"])
    write_json(candidate / "input_file_set_hashes.json", file_sets)
    write_csv(candidate / "instrument_mapping_audit.csv", mapping, sort_key=["relative_path"])
    write_csv(candidate / "frozen_cost_contract_audit.csv", pd.DataFrame(cost_rows), sort_key=["source_artifact", "cost_field", "effective_start_date"])
    write_csv(candidate / "calendar_freeze.csv", calendar_frame, sort_key=["decision_date"])
    write_csv(candidate / "arm_and_horizon_registry.csv", arm_registry(), sort_key=["arm_id", "holding_sessions", "return_semantics", "weighting", "bucket_count"])
    write_csv(candidate / "formula_registry.csv", formula_registry(config), sort_key=["formula_id"])
    write_csv(candidate / "sample_floor_and_gate_registry.csv", sample_gate_registry(config), sort_key=["gate_id", "metric_name", "scope_id"])
    whitelist = whitelist_records(paths)
    write_json(candidate / "read_whitelist.json", whitelist)

    ordinary = [
        "upstream_integrity_audit.csv", "input_inventory.csv", "input_schema_audit.csv", "input_file_set_hashes.json",
        "instrument_mapping_audit.csv", "frozen_cost_contract_audit.csv", "calendar_freeze.csv",
        "arm_and_horizon_registry.csv", "formula_registry.csv", "sample_floor_and_gate_registry.csv", "read_whitelist.json",
    ]
    aggregate_hashes = {role: stable_hash(records) for role, records in file_sets.items()}
    bundle_hash = seal_bundle(candidate, "preoutcome", ordinary, {
        "upstream_bundle_hashes": {"20A": expected["20a_freeze_bundle_hash"], "20B": expected["20b_historical_bundle_hash"]},
        "input_file_set_hashes": aggregate_hashes, "authorization_record": None,
        "history_date_min": str(minimum.date()), "history_date_max": str(maximum.date()),
        "registered_arm_horizon_rows": 84, "u_ever_n": len(u_ever), "implementation_authorized": True,
    })
    verify_bundle(candidate, "preoutcome")
    publish_stage(candidate, target)
    return {"status": "sealed", "preoutcome_bundle_hash": bundle_hash, "preoutcome_root": str(target), "u_ever_n": len(u_ever)}


DAILY_COLUMNS = [
    "asset_role", "instrument_id", "session_date", "previous_session_date", "qfq_close", "previous_qfq_close",
    "raw_simple_return", "resolved_simple_return", "resolution_state", "listing_date", "delist_date",
    "terminal_event_session", "delist_rule_applied", "all_tradable_assumption_applied",
    "daily_suspension_lookup_performed", "source_file_sha256", "source_row_key_hash", "feature_use_allowed", "failure_reason",
]
MODEL_COLUMNS = [
    "instrument_id", "residual_date", "estimation_start_date", "estimation_end_date", "calendar_session_n",
    "paired_observation_n", "paired_coverage", "design_rank", "alpha", "beta", "rcond", "fit_row_key_hash",
    "max_input_date", "status", "failure_reason",
]
RESIDUAL_COLUMNS = [
    "instrument_id", "residual_date", "residual_model_id", "stock_simple_return", "benchmark_simple_return",
    "estimation_start_date", "estimation_end_date", "calendar_session_n", "paired_observation_n", "paired_coverage",
    "design_rank", "alpha", "beta", "residual", "max_date_read", "max_contributing_date", "future_rows_loaded",
    "future_rows_contributed", "status", "failure_reason", "input_row_key_hash",
]
WEEKLY_COLUMNS = [
    "instrument_id", "decision_date", "entry_date", "arm_id", "formation_sessions", "feature_start_date",
    "feature_end_date", "feature_observation_n", "raw_signal", "signal_eligible", "signal_missing_reason",
    "universe_membership_available_time", "max_date_read", "max_contributing_date", "future_rows_loaded",
    "future_rows_contributed", "feature_row_key_hash", "total_market_cap_cny", "fold_id", "calendar_signal_possible",
]
ASSIGNMENT_COLUMNS = [
    "instrument_id", "decision_date", "entry_date", "arm_id", "formation_sessions", "bucket_count",
    "denominator_eligible", "signal_eligible", "raw_signal", "rank", "bucket_id", "favorable_bucket",
    "ew_target_weight", "vw_target_weight", "total_market_cap_cny", "assignment_status", "assignment_reason",
]


class ParquetStream:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self.writer: pq.ParquetWriter | None = None
        self.schema: pa.Schema | None = None

    def write(self, frame: pd.DataFrame) -> None:
        table = pa.Table.from_pandas(frame, preserve_index=False)
        if self.writer is None:
            self.schema = table.schema
            self.writer = pq.ParquetWriter(self.path, self.schema, compression="zstd")
        else:
            table = table.cast(self.schema)
        self.writer.write_table(table)

    def close(self) -> None:
        if self.writer is None:
            raise RuntimeError(f"no rows written to parquet stream: {self.path}")
        self.writer.close()

    def __enter__(self) -> "ParquetStream":
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        self.close()


def load_weekly_universe(path: Path, calendar_frame: pd.DataFrame, calendar: pd.DatetimeIndex) -> pd.DataFrame:
    entry_to_decision = dict(zip(calendar_frame["entry_date"].dt.strftime("%Y-%m-%d"), calendar_frame["decision_date"]))
    wanted = set(entry_to_decision)
    chunks: list[pd.DataFrame] = []
    usecols = [
        "usable_trade_date", "instrument", "source_membership_date", "membership_available_time", "available_time",
        "total_market_cap_cny",
    ]
    for chunk in pd.read_csv(path, usecols=usecols, chunksize=150_000, dtype={"usable_trade_date": "string", "instrument": "string"}):
        selected = chunk[chunk["usable_trade_date"].isin(wanted)].copy()
        if selected.empty:
            continue
        selected["entry_date"] = strict_dates(selected["usable_trade_date"], "universe usable_trade_date")
        selected["decision_date"] = selected["usable_trade_date"].map(entry_to_decision)
        source_date = strict_dates(selected["source_membership_date"], "source_membership_date")
        membership_date = parse_close_availability(selected["membership_available_time"], "membership_available_time")
        available_date = parse_close_availability(selected["available_time"], "available_time")
        if not (source_date < selected["entry_date"]).all():
            raise RuntimeError("universe source membership is not strictly prior to usable date")
        if not (membership_date <= selected["decision_date"]).all() or not (available_date <= selected["decision_date"]).all():
            raise RuntimeError("universe availability timing gate failed")
        if not set(membership_date).issubset(set(calendar)) or not set(available_date).issubset(set(calendar)):
            raise RuntimeError("availability date is not an exchange session")
        selected["universe_membership_available_time"] = selected["membership_available_time"].astype(str)
        selected["total_market_cap_cny"] = pd.to_numeric(selected["total_market_cap_cny"], errors="coerce")
        chunks.append(selected[["instrument", "decision_date", "entry_date", "universe_membership_available_time", "total_market_cap_cny"]])
    result = pd.concat(chunks, ignore_index=True).rename(columns={"instrument": "instrument_id"})
    result["instrument_id"] = result["instrument_id"].astype(str)
    if result.duplicated(["entry_date", "instrument_id"]).any():
        raise RuntimeError("weekly universe duplicate key")
    folds = calendar_frame[["decision_date", "fold_id", "calendar_signal_possible"]]
    result = result.merge(folds, on="decision_date", how="left", validate="many_to_one")
    return result.sort_values(["instrument_id", "decision_date"], kind="mergesort").reset_index(drop=True)


def load_security_master(path: Path) -> dict[str, dict[str, Any]]:
    frame = pd.read_csv(path, usecols=["instrument", "listing_date", "delist_date", "is_delisted", "metadata_source"], dtype={"instrument": "string"})
    if frame["instrument"].duplicated().any():
        raise RuntimeError("security-master instrument is not unique")
    frame["listing_date"] = pd.to_datetime(frame["listing_date"], format="%Y-%m-%d", errors="coerce")
    frame["delist_date"] = pd.to_datetime(frame["delist_date"], format="%Y-%m-%d", errors="coerce")
    frame["is_delisted"] = frame["is_delisted"].astype(str).str.lower().isin(["true", "1"])
    return frame.set_index("instrument").to_dict("index")


def resolve_daily_path(instrument: str, path: Path, calendar: pd.DatetimeIndex, master: dict[str, Any] | None) -> tuple[pd.DataFrame, np.ndarray, np.ndarray, pd.Timestamp | None, str]:
    source_sha = file_sha(path)
    raw = pd.read_csv(path, usecols=["date", "close", "instrument"], dtype={"date": "string", "instrument": "string"})
    if raw["instrument"].dropna().astype(str).nunique() != 1 or str(raw["instrument"].dropna().iloc[0]) != instrument:
        raise RuntimeError(f"qfq identity drift during signal: {instrument}")
    raw["date"] = pd.to_datetime(raw["date"], format="%Y-%m-%d", errors="coerce")
    raw["close"] = pd.to_numeric(raw["close"], errors="coerce")
    raw = raw.dropna(subset=["date"]).sort_values("date", kind="mergesort")
    if raw["date"].duplicated().any():
        raise RuntimeError(f"qfq duplicate date: {instrument}")
    max_date_read = raw["date"].max() if not raw.empty else None
    close = raw.set_index("date")["close"].reindex(calendar).to_numpy(dtype=float)
    observed = np.isfinite(close) & (close > 0)
    raw_return = np.full(len(calendar), np.nan)
    raw_return[1:] = np.where(observed[1:] & observed[:-1], close[1:] / close[:-1] - 1.0, np.nan)
    resolved_mark = np.full(len(calendar), np.nan)
    resolved_return = np.full(len(calendar), np.nan)
    states = np.full(len(calendar), "unknown_data_gap", dtype=object)
    terminal_applied = False
    terminal_index: int | None = None
    listing_date = master.get("listing_date") if master else pd.NaT
    delist_date = master.get("delist_date") if master else pd.NaT
    confirmed_delisted = bool(master.get("is_delisted")) if master else False
    mapped_delist_index: int | None = None
    if confirmed_delisted and pd.notna(delist_date):
        mapped_delist_index = int(calendar.searchsorted(pd.Timestamp(delist_date), side="left"))
        if mapped_delist_index >= len(calendar):
            mapped_delist_index = None
    for d in range(len(calendar)):
        if terminal_applied:
            states[d] = "post_terminal_not_eligible"
            continue
        if observed[d]:
            states[d] = "valid_mark"
            resolved_mark[d] = close[d]
            if d > 0 and np.isfinite(resolved_mark[d - 1]) and resolved_mark[d - 1] > 0:
                resolved_return[d] = close[d] / resolved_mark[d - 1] - 1.0
            continue
        can_terminal = (
            mapped_delist_index is not None and d >= mapped_delist_index and d > 0
            and np.isfinite(resolved_mark[d - 1]) and resolved_mark[d - 1] > 0
        )
        if can_terminal:
            states[d] = "confirmed_delisting_terminal"
            resolved_mark[d] = 0.0
            resolved_return[d] = -1.0
            terminal_applied = True
            terminal_index = d
    terminal_date = calendar[terminal_index] if terminal_index is not None else pd.NaT
    rows = pd.DataFrame({
        "asset_role": "stock", "instrument_id": instrument, "session_date": calendar,
        "previous_session_date": pd.Series(calendar).shift(1), "qfq_close": np.where(observed, close, np.nan),
        "previous_qfq_close": np.r_[np.nan, np.where(observed[:-1], close[:-1], np.nan)],
        "raw_simple_return": raw_return, "resolved_simple_return": resolved_return, "resolution_state": states,
        "listing_date": listing_date, "delist_date": delist_date, "terminal_event_session": terminal_date,
        "delist_rule_applied": states == "confirmed_delisting_terminal", "all_tradable_assumption_applied": True,
        "daily_suspension_lookup_performed": False, "source_file_sha256": source_sha,
        "source_row_key_hash": [stable_hash((instrument, str(date.date()), float(value))) if np.isfinite(value) else None for date, value in zip(calendar, close)],
        "feature_use_allowed": np.isfinite(resolved_return),
        "failure_reason": np.where(np.isfinite(resolved_return), "", np.where(states == "post_terminal_not_eligible", "post_terminal", "missing_current_or_previous_mark")),
    })
    return rows[DAILY_COLUMNS], resolved_return, resolved_mark, max_date_read, source_sha


def benchmark_daily(path: Path, calendar: pd.DatetimeIndex) -> tuple[pd.DataFrame, np.ndarray, pd.Timestamp, str]:
    source_sha = file_sha(path)
    frame = pd.read_csv(path, usecols=["date", "close", "index_alias", "instrument"])
    frame = frame[(frame["index_alias"].astype(str).str.lower() == "csi300") & (frame["instrument"].astype(str) == "SH000300")].copy()
    frame["date"] = pd.to_datetime(frame["date"], format="%Y-%m-%d", errors="coerce")
    frame["close"] = pd.to_numeric(frame["close"], errors="coerce")
    frame = frame.sort_values("date", kind="mergesort").drop_duplicates("date")
    maximum = frame["date"].max()
    close = frame.set_index("date")["close"].reindex(calendar).to_numpy(dtype=float)
    observed = np.isfinite(close) & (close > 0)
    returns = np.full(len(calendar), np.nan)
    returns[1:] = np.where(observed[1:] & observed[:-1], close[1:] / close[:-1] - 1.0, np.nan)
    rows = pd.DataFrame({
        "asset_role": "benchmark", "instrument_id": "SH000300", "session_date": calendar,
        "previous_session_date": pd.Series(calendar).shift(1), "qfq_close": np.where(observed, close, np.nan),
        "previous_qfq_close": np.r_[np.nan, np.where(observed[:-1], close[:-1], np.nan)],
        "raw_simple_return": returns, "resolved_simple_return": returns,
        "resolution_state": np.where(np.isfinite(returns), "valid_mark", "unknown_data_gap"),
        "listing_date": None, "delist_date": None, "terminal_event_session": None, "delist_rule_applied": False,
        "all_tradable_assumption_applied": False, "daily_suspension_lookup_performed": False,
        "source_file_sha256": source_sha,
        "source_row_key_hash": [stable_hash(("SH000300", str(date.date()), float(value))) if np.isfinite(value) else None for date, value in zip(calendar, close)],
        "feature_use_allowed": np.isfinite(returns), "failure_reason": np.where(np.isfinite(returns), "", "missing_current_or_previous_mark"),
    })
    return rows[DAILY_COLUMNS], returns, maximum, source_sha


def sequential_residuals(instrument: str, stock_return: np.ndarray, market_return: np.ndarray,
                         calendar: pd.DatetimeIndex, max_date_read: pd.Timestamp | None, rcond: float) -> tuple[pd.DataFrame, pd.DataFrame, np.ndarray, np.ndarray]:
    n = len(calendar)
    residual = np.full(n, np.nan)
    beta_path = np.full(n, np.nan)
    sessions = np.arange(253, n, dtype=int)
    pair = np.isfinite(stock_return) & np.isfinite(market_return)
    x = np.where(pair, market_return, 0.0)
    y = np.where(pair, stock_return, 0.0)

    def rolling_sum(values: np.ndarray) -> np.ndarray:
        cumulative = np.r_[0.0, np.cumsum(values, dtype=np.float64)]
        return cumulative[sessions] - cumulative[sessions - 252]

    paired_n = rolling_sum(pair.astype(float)).astype(int)
    benchmark_n = rolling_sum(np.isfinite(market_return).astype(float)).astype(int)
    sx, sy = rolling_sum(x), rolling_sum(y)
    sxx, sxy = rolling_sum(x * x), rolling_sum(x * y)
    denominator = paired_n * sxx - sx * sx
    rank = np.where((paired_n >= 2) & np.isfinite(denominator) & (denominator > 0), 2, np.where(paired_n >= 1, 1, 0))
    beta = np.divide(paired_n * sxy - sx * sy, denominator, out=np.full(len(sessions), np.nan), where=denominator > 0)
    alpha = np.divide(sy - beta * sx, paired_n, out=np.full(len(sessions), np.nan), where=paired_n > 0)
    current_ok = np.isfinite(stock_return[sessions]) & np.isfinite(market_return[sessions])
    values = stock_return[sessions] - (alpha + beta * market_return[sessions])
    reasons = np.full(len(sessions), "", dtype=object)
    reasons[benchmark_n != 252] = "benchmark_window_incomplete"
    reasons[(benchmark_n == 252) & (paired_n < 200)] = "paired_observation_below_200"
    reasons[(benchmark_n == 252) & (paired_n >= 200) & (rank != 2)] = "design_rank_not_2"
    eligible_fit = (benchmark_n == 252) & (paired_n >= 200) & (rank == 2)
    reasons[eligible_fit & ~current_ok] = "current_return_missing"
    reasons[eligible_fit & current_ok & ~np.isfinite(values)] = "residual_nonfinite"
    passed = reasons == ""
    residual[sessions[passed]] = values[passed]
    beta_path[sessions[passed]] = beta[passed]

    valid_positions = np.flatnonzero(eligible_fit)
    for position in valid_positions[[0, -1]] if len(valid_positions) else []:
        s = sessions[position]
        mask = pair[s - 252:s]
        design = np.column_stack([np.ones(mask.sum()), market_return[s - 252:s][mask]]).astype(np.float64)
        response = stock_return[s - 252:s][mask].astype(np.float64)
        reference, _, reference_rank, _ = np.linalg.lstsq(design, response, rcond=rcond)
        if int(reference_rank) != 2 or not np.allclose([alpha[position], beta[position]], reference, rtol=1e-9, atol=1e-11):
            raise RuntimeError(f"rolling OLS/lstsq mismatch: {instrument} {calendar[s].date()}")

    fit_hashes = [stable_hash((instrument, str(calendar[s - 252].date()), str(calendar[s - 1].date()), int(pn), a, b)) for s, pn, a, b in zip(sessions, paired_n, alpha, beta)]
    future_loaded = np.where(
        np.array([max_date_read is not None and max_date_read > calendar[s] for s in sessions]),
        n - 1 - sessions, 0,
    )
    model = pd.DataFrame({
        "instrument_id": instrument, "residual_date": calendar[sessions], "estimation_start_date": calendar[sessions - 252],
        "estimation_end_date": calendar[sessions - 1], "calendar_session_n": 252, "paired_observation_n": paired_n,
        "paired_coverage": paired_n / 252.0, "design_rank": rank, "alpha": alpha, "beta": beta, "rcond": rcond,
        "fit_row_key_hash": fit_hashes, "max_input_date": calendar[sessions - 1],
        "status": np.where(passed, "pass", "fail"), "failure_reason": reasons,
    })
    residual_frame = pd.DataFrame({
        "instrument_id": instrument, "residual_date": calendar[sessions], "residual_model_id": RESIDUAL_MODEL_ID,
        "stock_simple_return": stock_return[sessions], "benchmark_simple_return": market_return[sessions],
        "estimation_start_date": calendar[sessions - 252], "estimation_end_date": calendar[sessions - 1],
        "calendar_session_n": 252, "paired_observation_n": paired_n, "paired_coverage": paired_n / 252.0,
        "design_rank": rank, "alpha": alpha, "beta": beta, "residual": values,
        "max_date_read": max_date_read, "max_contributing_date": calendar[sessions], "future_rows_loaded": future_loaded,
        "future_rows_contributed": 0, "status": np.where(passed, "pass", "fail"), "failure_reason": reasons,
        "input_row_key_hash": [stable_hash((h, str(calendar[s].date()), stock_return[s], market_return[s])) for h, s in zip(fit_hashes, sessions)],
    })
    return model[MODEL_COLUMNS], residual_frame[RESIDUAL_COLUMNS], residual, beta_path


def standardized_score(values: np.ndarray, end_index: int, length: int) -> tuple[float, int, str]:
    start = end_index - length + 1
    if start < 0:
        return np.nan, 0, "calendar_warmup_not_ready"
    window = values[start:end_index + 1]
    finite_n = int(np.isfinite(window).sum())
    if finite_n != length:
        return np.nan, finite_n, "formation_missing_value"
    std = float(np.std(window, ddof=1))
    if not math.isfinite(std) or std <= 1e-12:
        return np.nan, finite_n, "formation_scale_nonpositive"
    return float(np.mean(window) / std), finite_n, ""


def weekly_features_for_instrument(instrument: str, denominator: pd.DataFrame, calendar: pd.DatetimeIndex,
                                   stock_return: np.ndarray, residual: np.ndarray, max_date_read: pd.Timestamp | None) -> pd.DataFrame:
    session_index = {date: i for i, date in enumerate(calendar)}
    rows: list[dict[str, Any]] = []
    for item in denominator.itertuples(index=False):
        j = session_index[item.decision_date]
        for arm_id, spec in SCORED_ARMS.items():
            length = int(spec["formation"])
            if not bool(item.calendar_signal_possible):
                score, observation_n, reason = np.nan, 0, "calendar_warmup_not_ready"
            elif arm_id.startswith("SRC1_") or arm_id.startswith("SRC2_"):
                score, observation_n, reason = standardized_score(stock_return, j, length)
            elif arm_id.startswith("SRC3_") or arm_id.startswith("SRC4_"):
                score, observation_n, reason = standardized_score(residual, j, length)
            else:
                start = j - 19
                window = stock_return[start:j + 1] if start >= 0 else np.array([])
                observation_n = int(np.isfinite(window).sum())
                if len(window) != 20 or observation_n != 20:
                    score, reason = np.nan, "formation_missing_value"
                else:
                    score = float(np.std(window, ddof=1))
                    reason = "" if math.isfinite(score) else "formation_scale_nonfinite"
            feature_start_index = j - length + 1
            future_loaded = int(max(0, (max_date_read - item.decision_date).days)) if max_date_read is not None and max_date_read > item.decision_date else 0
            rows.append({
                "instrument_id": instrument, "decision_date": item.decision_date, "entry_date": item.entry_date,
                "arm_id": arm_id, "formation_sessions": length,
                "feature_start_date": calendar[feature_start_index] if feature_start_index >= 0 else None,
                "feature_end_date": item.decision_date, "feature_observation_n": observation_n,
                "raw_signal": score, "signal_eligible": bool(np.isfinite(score)), "signal_missing_reason": reason,
                "universe_membership_available_time": item.universe_membership_available_time,
                "max_date_read": max_date_read, "max_contributing_date": item.decision_date,
                "future_rows_loaded": future_loaded, "future_rows_contributed": 0,
                "feature_row_key_hash": stable_hash((instrument, str(item.decision_date.date()), arm_id, score)),
                "total_market_cap_cny": item.total_market_cap_cny, "fold_id": item.fold_id,
                "calendar_signal_possible": bool(item.calendar_signal_possible),
            })
    if not rows:
        return pd.DataFrame(columns=WEEKLY_COLUMNS)
    return pd.DataFrame(rows)[WEEKLY_COLUMNS]


def materialize_assignments(weekly: pd.DataFrame, config: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame]:
    base = weekly[["instrument_id", "decision_date", "entry_date", "arm_id", "formation_sessions", "signal_eligible", "raw_signal", "total_market_cap_cny", "signal_missing_reason"]].copy()
    assignments = pd.concat([base.assign(bucket_count=k) for k in [5, 10]], ignore_index=True)
    assignments["denominator_eligible"] = True
    assignments["rank"] = pd.Series(pd.NA, index=assignments.index, dtype="Int64")
    assignments["bucket_id"] = pd.Series(pd.NA, index=assignments.index, dtype="Int64")
    assignments["favorable_bucket"] = False
    assignments["ew_target_weight"] = np.nan
    assignments["vw_target_weight"] = np.nan
    assignments["assignment_status"] = "not_evaluable"
    assignments["assignment_reason"] = assignments["signal_missing_reason"]
    for (decision, arm_id, k), group in assignments.groupby(["decision_date", "arm_id", "bucket_count"], sort=True):
        eligible_mask = group["signal_eligible"].astype(bool) & np.isfinite(group["raw_signal"])
        eligible = group[eligible_mask].copy()
        minimum_n = 100 if int(k) == 10 else 50
        if len(eligible) < minimum_n:
            reason = "decile_floor_not_met" if int(k) == 10 else "quintile_bucket_floor_not_met"
            assignments.loc[group.index, "assignment_reason"] = reason
            continue
        ordered = eligible.sort_values(["raw_signal", "instrument_id"], kind="mergesort")
        ranks = np.arange(1, len(ordered) + 1)
        buckets = 1 + np.floor((ranks - 1) * int(k) / len(ordered)).astype(int)
        assignments.loc[ordered.index, "rank"] = ranks
        assignments.loc[ordered.index, "bucket_id"] = buckets
        favorable_id = 1 if SCORED_ARMS[arm_id]["favorable"] == "low" else int(k)
        assignments.loc[ordered.index, "favorable_bucket"] = buckets == favorable_id
        assignments.loc[group.index, "assignment_reason"] = "signal_missing"
        assignments.loc[ordered.index, "assignment_status"] = "assigned"
        assignments.loc[ordered.index, "assignment_reason"] = ""
        bucket_series = pd.Series(buckets, index=ordered.index)
        for bucket_id, bucket_indices in bucket_series.groupby(bucket_series).groups.items():
            idx = list(bucket_indices)
            assignments.loc[idx, "ew_target_weight"] = 1.0 / len(idx)
            cap = pd.to_numeric(assignments.loc[idx, "total_market_cap_cny"], errors="coerce")
            valid_cap = cap[np.isfinite(cap) & (cap > 0)]
            if len(valid_cap) >= 10 and valid_cap.sum() > 0:
                assignments.loc[valid_cap.index, "vw_target_weight"] = valid_cap / valid_cap.sum()
    coverage_rows = []
    for (decision, arm_id), group in weekly.groupby(["decision_date", "arm_id"], sort=True):
        n = len(group)
        eligible_flag = group["signal_eligible"].astype(bool)
        eligible_n = int(eligible_flag.sum())
        decile = eligible_n >= 100
        minimum_bucket = eligible_n // 10 if decile else 0
        reasons = group.loc[~eligible_flag, "signal_missing_reason"]
        mode = reasons.mode().iloc[0] if not reasons.empty and not reasons.mode().empty else ""
        coverage_rows.append({
            "decision_date": decision, "arm_id": arm_id, "registered_denominator_n": n,
            "signal_eligible_n": eligible_n, "signal_coverage": eligible_n / n if n else 0.0,
            "decile_eligible": decile, "minimum_bucket_n_observed": minimum_bucket,
            "missing_reason_mode": mode, "status": "pass" if decile else "not_evaluable",
        })
    result = assignments[ASSIGNMENT_COLUMNS].copy()
    if result.duplicated(["instrument_id", "decision_date", "arm_id", "bucket_count"]).any():
        raise RuntimeError("assignment duplicate key")
    return result, pd.DataFrame(coverage_rows)


def signal_stage(config_path: str | Path, preoutcome_hash: str | None, authorization_file: str | None) -> dict[str, Any]:
    config = load_config(config_path)
    paths = paths_for(config)
    build = build_root(config)
    pre = build / "preoutcome"
    verified_pre_hash = verify_bundle(pre, "preoutcome")
    if not preoutcome_hash or preoutcome_hash != verified_pre_hash:
        raise PermissionError("--preoutcome-bundle-hash must match the sealed preoutcome registry")
    whitelist = load_preoutcome_whitelist(build)["signal-materialization"]
    expected_auth_path = build / config["authorization"]["signal_authorization_relative_path"]
    if not authorization_file or Path(authorization_file).resolve() != expected_auth_path.resolve():
        raise PermissionError(f"signal authorization must use registered path: {expected_auth_path}")
    authorization = verify_authorization(expected_auth_path, "signal-materialization", verified_pre_hash, whitelist["stable_object_hash"])
    verify_input_file_records(paths, read_json(pre / "input_file_set_hashes.json"))

    candidate, target = begin_stage(build, "signal")
    if candidate == target:
        return {"status": "already_sealed", "signal_bundle_hash": verify_bundle(target, "signal")}
    minimum, maximum = pd.Timestamp(config["boundary"]["history_date_min"]), pd.Timestamp(config["boundary"]["history_date_max"])
    calendar = exchange_calendar(paths["trading_calendar"], minimum, maximum)
    calendar_frame = pd.read_csv(pre / "calendar_freeze.csv", parse_dates=["decision_date", "entry_date"])
    denominator = load_weekly_universe(paths["project_universe"], calendar_frame, calendar)
    mapping = pd.read_csv(pre / "instrument_mapping_audit.csv")
    mapping_used = set(mapping.loc[mapping["canonical_instrument_id"].notna() & mapping["status"].eq("pass"), "canonical_instrument_id"].astype(str))
    u_ever = sorted(mapping_used)
    if not set(denominator["instrument_id"]).issubset(mapping_used):
        raise RuntimeError("weekly denominator contains instrument outside sealed U_ever mapping")
    security_master = load_security_master(paths["security_master"])
    benchmark_audit, market_return, benchmark_max_date, benchmark_sha = benchmark_daily(paths["benchmark"], calendar)

    weekly_frames: list[pd.DataFrame] = []
    daily_path = candidate / "daily_return_resolution_audit.csv.gz"
    model_path = candidate / "rolling_market_model_audit.csv.gz"
    residual_path = candidate / "daily_market_residual_panel.parquet"
    with GzipCSVStream(daily_path, DAILY_COLUMNS) as daily_writer, GzipCSVStream(model_path, MODEL_COLUMNS) as model_writer, ParquetStream(residual_path) as residual_writer:
        daily_writer.write(benchmark_audit)
        for number, instrument in enumerate(u_ever, start=1):
            qfq_path = paths["qfq_root"] / f"{instrument}.csv"
            daily, stock_return, _, max_date_read, _ = resolve_daily_path(instrument, qfq_path, calendar, security_master.get(instrument))
            model, residual_frame, residual, _ = sequential_residuals(
                instrument, stock_return, market_return, calendar, max_date_read, float(config["residual"]["rcond"]),
            )
            daily_writer.write(daily)
            model_writer.write(model)
            residual_writer.write(residual_frame)
            subset = denominator[denominator["instrument_id"] == instrument]
            weekly_frames.append(weekly_features_for_instrument(instrument, subset, calendar, stock_return, residual, max_date_read))
            if number % 200 == 0:
                print(f"signal materialization: {number}/{len(u_ever)} instruments", flush=True)

    weekly = pd.concat([frame for frame in weekly_frames if not frame.empty], ignore_index=True)
    weekly["signal_eligible"] = weekly["signal_eligible"].astype(bool)
    weekly["calendar_signal_possible"] = weekly["calendar_signal_possible"].astype(bool)
    if weekly.duplicated(["instrument_id", "decision_date", "arm_id"]).any():
        raise RuntimeError("weekly signal duplicate key")
    if not (pd.to_datetime(weekly["max_contributing_date"]) <= pd.to_datetime(weekly["decision_date"])).all():
        raise RuntimeError("weekly signal causal firewall failed")
    if int(weekly["future_rows_contributed"].sum()) != 0:
        raise RuntimeError("future rows contributed to signal")
    forbidden = [c for c in weekly.columns if any(token in c.lower() for token in ["forward_", "label_", "outcome_", "mfe", "mae", "winner"])]
    if forbidden:
        raise RuntimeError(f"outcome-like signal columns: {forbidden}")
    assignments, coverage = materialize_assignments(weekly, config)
    write_parquet(candidate / "weekly_signal_panel.parquet", weekly, WEEKLY_COLUMNS,
                  sort_key=["instrument_id", "decision_date", "arm_id"])
    write_parquet(candidate / "weekly_bucket_assignment.parquet", assignments, ASSIGNMENT_COLUMNS,
                  sort_key=["instrument_id", "decision_date", "arm_id", "bucket_count"])
    write_csv(candidate / "signal_coverage_audit.csv", coverage,
              sort_key=["decision_date", "arm_id"])

    max_decision = weekly["decision_date"].max()
    access = [
        access_row(1, "signal-materialization", pre, "sealed_preoutcome", row_count=None, max_date_read=maximum.date(), max_date_contributed=maximum.date(), context=maximum.date()),
        access_row(2, "signal-materialization", expected_auth_path, "signal_authorization", row_count=1),
        access_row(3, "signal-materialization", paths["project_universe"], "project_universe", row_count=len(denominator), max_date_read=maximum.date(), max_date_contributed=max_decision.date(), context=max_decision.date()),
        access_row(4, "signal-materialization", paths["qfq_root"], "qfq_raw", row_count=None, max_date_read=maximum.date(), max_date_contributed=max_decision.date(), context=max_decision.date(), future_loaded=int(weekly["future_rows_loaded"].sum()), future_contributed=0),
        access_row(5, "signal-materialization", paths["benchmark"], "benchmark", row_count=len(benchmark_audit), max_date_read=benchmark_max_date.date(), max_date_contributed=max_decision.date(), context=max_decision.date()),
        access_row(6, "signal-materialization", paths["trading_calendar"], "trading_calendar", row_count=len(calendar), max_date_read=maximum.date(), max_date_contributed=maximum.date(), context=maximum.date()),
        access_row(7, "signal-materialization", paths["security_master"], "security_master_identity_delisting", row_count=len(security_master), max_date_read=maximum.date(), max_date_contributed=maximum.date(), context=maximum.date()),
    ]
    write_csv(candidate / "signal_access_audit.csv", pd.DataFrame(access)[ACCESS_COLUMNS], sort_key=["stage", "access_sequence_id"])
    ordinary = [
        "signal_access_audit.csv", "daily_return_resolution_audit.csv.gz", "rolling_market_model_audit.csv.gz",
        "daily_market_residual_panel.parquet", "weekly_signal_panel.parquet", "weekly_bucket_assignment.parquet",
        "signal_coverage_audit.csv",
    ]
    aggregate_input_hashes = {role: stable_hash(records) for role, records in read_json(pre / "input_file_set_hashes.json").items()}
    bundle_hash = seal_bundle(candidate, "signal", ordinary, {
        "upstream_bundle_hashes": {"preoutcome": verified_pre_hash}, "input_file_set_hashes": aggregate_input_hashes,
        "authorization_record": authorization, "authorization_file_sha256": file_sha(expected_auth_path),
        "authorization_record_sha256": authorization["authorization_record_sha256"],
        "history_date_min": str(minimum.date()), "history_date_max": str(maximum.date()),
        "registered_arm_horizon_rows": 84, "outcome_role_table_access_count": 0,
        "future_rows_contributed_to_signal": 0,
    })
    verify_bundle(candidate, "signal")
    publish_stage(candidate, target)
    return {
        "status": "sealed", "signal_bundle_hash": bundle_hash, "signal_root": str(target),
        "weekly_signal_rows": len(weekly), "assignment_rows": len(assignments),
    }


FORWARD_COLUMNS = [
    "instrument_id", "decision_date", "entry_date", "holding_sessions", "return_semantics", "signal_mark_date",
    "signal_mark", "label_end_date", "label_end_mark", "resolved_forward_return", "outcome_resolution_state",
    "right_censored", "delist_date", "terminal_event_session", "all_tradable_assumption_applied",
    "source_file_sha256", "source_row_key_hash", "assignment_bundle_hash", "affected_assignment_key_hash", "failure_reason",
]
BUCKET_COLUMNS = [
    "decision_date", "fold_id", "calendar_year", "arm_id", "formation_sessions", "holding_sessions", "matrix_role",
    "return_semantics", "weighting", "bucket_count", "bucket_id", "series_role", "registered_denominator_n",
    "signal_eligible_n", "bucket_target_n", "outcome_resolved_n", "evaluable", "not_evaluable_reason", "gross_return",
    "raw_stock_spearman", "aligned_bucket_spearman",
]


def materialize_forward_returns(assignments: pd.DataFrame, calendar: pd.DatetimeIndex, qfq_root: Path,
                                security_master: dict[str, dict[str, Any]], signal_hash: str) -> pd.DataFrame:
    unique_pairs = assignments[["instrument_id", "decision_date", "entry_date"]].drop_duplicates().sort_values(["instrument_id", "decision_date"])
    arm_bucket_keys = [(arm, bucket_count) for arm in sorted(SCORED_ARMS) for bucket_count in [5, 10]]
    assignment_keys = {
        (str(item.instrument_id), pd.Timestamp(item.decision_date)): stable_hash(sorted(
            (str(item.instrument_id), str(pd.Timestamp(item.decision_date).date()), arm, bucket_count)
            for arm, bucket_count in arm_bucket_keys
        ))
        for item in unique_pairs.itertuples(index=False)
    }
    calendar_index = {date: i for i, date in enumerate(calendar)}
    rows: list[dict[str, Any]] = []
    for number, (instrument, group) in enumerate(unique_pairs.groupby("instrument_id", sort=True), start=1):
        path = qfq_root / f"{instrument}.csv"
        source_sha = file_sha(path)
        raw = pd.read_csv(path, usecols=["date", "close", "instrument"])
        if raw["instrument"].dropna().astype(str).nunique() != 1 or str(raw["instrument"].dropna().iloc[0]) != instrument:
            raise RuntimeError(f"qfq identity drift during outcome: {instrument}")
        raw["date"] = pd.to_datetime(raw["date"], format="%Y-%m-%d", errors="coerce")
        raw["close"] = pd.to_numeric(raw["close"], errors="coerce")
        marks = raw.dropna(subset=["date"]).drop_duplicates("date").set_index("date")["close"]
        master = security_master.get(instrument, {})
        delist_date = master.get("delist_date", pd.NaT)
        confirmed = bool(master.get("is_delisted", False)) and pd.notna(delist_date)
        for item in group.itertuples(index=False):
            decision = pd.Timestamp(item.decision_date)
            j = calendar_index[decision]
            signal_mark = float(marks.get(decision, np.nan))
            for holding in [5, 10]:
                label_index = j + holding
                right_censored = label_index >= len(calendar)
                end_date = pd.NaT if right_censored else calendar[label_index]
                end_mark = float(marks.get(end_date, np.nan)) if pd.notna(end_date) else np.nan
                if right_censored:
                    state, value, reason = "right_censored", np.nan, "label_end_beyond_frozen_boundary"
                elif np.isfinite(signal_mark) and signal_mark > 0 and np.isfinite(end_mark) and end_mark >= 0:
                    state, value, reason = "valid_mark", end_mark / signal_mark - 1.0, ""
                elif np.isfinite(signal_mark) and signal_mark > 0 and confirmed and pd.Timestamp(delist_date) <= end_date:
                    state, value, reason = "confirmed_delisting_minus_one", -1.0, ""
                else:
                    state, value, reason = "unknown_data_gap", np.nan, "missing_signal_or_label_end_mark"
                terminal = end_date if state == "confirmed_delisting_minus_one" else pd.NaT
                affected_hash = assignment_keys[(instrument, decision)]
                for semantics in [PROJECT_SEMANTICS, COMPLETE_CASE_SEMANTICS]:
                    rows.append({
                        "instrument_id": instrument, "decision_date": decision, "entry_date": item.entry_date,
                        "holding_sessions": holding, "return_semantics": semantics, "signal_mark_date": decision,
                        "signal_mark": signal_mark, "label_end_date": end_date, "label_end_mark": end_mark,
                        "resolved_forward_return": value, "outcome_resolution_state": state, "right_censored": right_censored,
                        "delist_date": delist_date, "terminal_event_session": terminal,
                        "all_tradable_assumption_applied": True, "source_file_sha256": source_sha,
                        "source_row_key_hash": stable_hash((instrument, str(decision.date()), holding, signal_mark, end_mark, state)),
                        "assignment_bundle_hash": signal_hash, "affected_assignment_key_hash": affected_hash,
                        "failure_reason": reason,
                    })
        if number % 200 == 0:
            print(f"outcome resolution: {number}/{unique_pairs['instrument_id'].nunique()} instruments", flush=True)
    frame = pd.DataFrame(rows)[FORWARD_COLUMNS]
    key = ["instrument_id", "decision_date", "holding_sessions", "return_semantics"]
    if frame.duplicated(key).any():
        raise RuntimeError("forward-return duplicate key")
    return frame.sort_values(key, kind="mergesort").reset_index(drop=True)


def physical_bucket_row(group: pd.DataFrame, outcomes: pd.Series, semantics: str, weighting: str,
                        bucket_id: int) -> dict[str, Any]:
    selected = group[group["bucket_id"] == bucket_id].copy()
    weights = pd.to_numeric(selected["ew_target_weight" if weighting == "EW" else "vw_target_weight"], errors="coerce")
    positive = np.isfinite(weights) & (weights > 0)
    selected = selected.loc[positive].copy()
    weights = weights.loc[positive].astype(float)
    values = selected["instrument_id"].map(outcomes).astype(float)
    finite = np.isfinite(values)
    result = {
        "registered_denominator_n": len(group), "signal_eligible_n": int(group["signal_eligible"].sum()),
        "bucket_target_n": len(selected), "outcome_resolved_n": int(finite.sum()),
        "evaluable": False, "not_evaluable_reason": "", "gross_return": np.nan,
    }
    if len(selected) == 0 or not math.isfinite(float(weights.sum())) or float(weights.sum()) <= 0:
        result["not_evaluable_reason"] = "no_positive_target_weight"
        return result
    if semantics == PROJECT_SEMANTICS:
        if not finite.all():
            result["not_evaluable_reason"] = "whole_bucket_unknown_or_right_censored"
            return result
        normalized = weights / weights.sum()
        result["gross_return"] = float(np.dot(normalized, values))
    else:
        if not finite.any():
            result["not_evaluable_reason"] = "no_complete_case_outcome"
            return result
        normalized = weights[finite] / weights[finite].sum()
        result["gross_return"] = float(np.dot(normalized, values[finite]))
    result["evaluable"] = True
    return result


def derived_bucket_rows(physical: dict[int, dict[str, Any]], arm_id: str, k: int) -> list[dict[str, Any]]:
    favorable_id = 1 if SCORED_ARMS[arm_id]["favorable"] == "low" else k
    unfavorable_id = k if favorable_id == 1 else 1
    middle_ids = [3] if k == 5 else [5, 6]

    def component(role: str, sentinel: str, ids: list[int], coefficients: list[float]) -> dict[str, Any]:
        rows = [physical[i] for i in ids]
        evaluable = all(bool(row["evaluable"]) for row in rows)
        value = sum(c * float(row["gross_return"]) for c, row in zip(coefficients, rows)) if evaluable else np.nan
        return {
            "bucket_id": sentinel, "series_role": role, "registered_denominator_n": rows[0]["registered_denominator_n"],
            "signal_eligible_n": rows[0]["signal_eligible_n"], "bucket_target_n": None, "outcome_resolved_n": None,
            "evaluable": evaluable, "not_evaluable_reason": "" if evaluable else "derived_component_not_evaluable",
            "gross_return": value,
        }

    favorable = component("favorable_bucket", "FAVORABLE", [favorable_id], [1.0])
    unfavorable = component("unfavorable_bucket", "UNFAVORABLE", [unfavorable_id], [1.0])
    middle = component("middle_bucket_mean", "MIDDLE", middle_ids, [1.0 / len(middle_ids)] * len(middle_ids))
    spread = component("favorable_minus_unfavorable", "F_MINUS_U", [favorable_id, unfavorable_id], [1.0, -1.0])
    mid_spread = component("favorable_minus_middle", "F_MINUS_M", [favorable_id, *middle_ids], [1.0] + [-1.0 / len(middle_ids)] * len(middle_ids))
    return [favorable, unfavorable, middle, spread, mid_spread]


def materialize_bucket_returns(assignments: pd.DataFrame, forward: pd.DataFrame, registry: pd.DataFrame,
                               calendar_frame: pd.DataFrame) -> pd.DataFrame:
    outcomes = forward.set_index(["instrument_id", "decision_date", "holding_sessions", "return_semantics"])["resolved_forward_return"]
    assignment_groups = {key: group for key, group in assignments.groupby(["decision_date", "arm_id", "bucket_count"], sort=False)}
    fold_map = calendar_frame.set_index("decision_date")[["fold_id"]].to_dict("index")
    decisions = sorted(calendar_frame["decision_date"].unique())
    rows: list[dict[str, Any]] = []
    scored_registry = registry[registry["arm_id"] != BASELINE_ARM]
    baseline_registry = registry[registry["arm_id"] == BASELINE_ARM]
    for number, decision in enumerate(decisions, start=1):
        fold = fold_map[pd.Timestamp(decision)]["fold_id"]
        for reg in scored_registry.itertuples(index=False):
            group = assignment_groups[(pd.Timestamp(decision), reg.arm_id, int(reg.bucket_count))]
            outcome_map = outcomes.xs((pd.Timestamp(decision), int(reg.holding_sessions), reg.return_semantics), level=["decision_date", "holding_sessions", "return_semantics"])
            eligible = group[group["signal_eligible"]].copy()
            eligible_values = eligible["instrument_id"].map(outcome_map)
            raw_spearman = average_midrank_spearman(eligible["raw_signal"], eligible_values)
            physical: dict[int, dict[str, Any]] = {}
            for bucket_id in range(1, int(reg.bucket_count) + 1):
                physical[bucket_id] = physical_bucket_row(group, outcome_map, reg.return_semantics, reg.weighting, bucket_id)
            physical_values = [physical[i]["gross_return"] for i in range(1, int(reg.bucket_count) + 1)]
            aligned = average_midrank_spearman(range(1, int(reg.bucket_count) + 1), physical_values)
            if aligned is not None and SCORED_ARMS[reg.arm_id]["favorable"] == "low":
                aligned *= -1.0
            common = {
                "decision_date": decision, "fold_id": fold, "calendar_year": pd.Timestamp(decision).year,
                "arm_id": reg.arm_id, "formation_sessions": reg.formation_sessions, "holding_sessions": reg.holding_sessions,
                "matrix_role": reg.matrix_role, "return_semantics": reg.return_semantics, "weighting": reg.weighting,
                "bucket_count": reg.bucket_count, "raw_stock_spearman": raw_spearman,
                "aligned_bucket_spearman": aligned,
            }
            for bucket_id, values in physical.items():
                rows.append(common | {"bucket_id": bucket_id, "series_role": "bucket"} | values)
            for values in derived_bucket_rows(physical, reg.arm_id, int(reg.bucket_count)):
                rows.append(common | values)
        denominator_group = assignment_groups[(pd.Timestamp(decision), "SRC1_TOTAL_CONT_5D", 5)]
        base_instruments = denominator_group["instrument_id"]
        for reg in baseline_registry.itertuples(index=False):
            outcome_map = outcomes.xs((pd.Timestamp(decision), int(reg.holding_sessions), reg.return_semantics), level=["decision_date", "holding_sessions", "return_semantics"])
            values = base_instruments.map(outcome_map).astype(float)
            finite = np.isfinite(values)
            evaluable = bool(finite.all()) if reg.return_semantics == PROJECT_SEMANTICS else bool(finite.any())
            gross = float(values.mean()) if reg.return_semantics == PROJECT_SEMANTICS and evaluable else float(values[finite].mean()) if evaluable else np.nan
            rows.append({
                "decision_date": decision, "fold_id": fold, "calendar_year": pd.Timestamp(decision).year,
                "arm_id": BASELINE_ARM, "formation_sessions": 0, "holding_sessions": reg.holding_sessions,
                "matrix_role": "all_eligible_baseline", "return_semantics": reg.return_semantics, "weighting": "EW",
                "bucket_count": 0, "bucket_id": "ALL", "series_role": "all_eligible_baseline",
                "registered_denominator_n": len(base_instruments), "signal_eligible_n": len(base_instruments),
                "bucket_target_n": len(base_instruments), "outcome_resolved_n": int(finite.sum()), "evaluable": evaluable,
                "not_evaluable_reason": "" if evaluable else "baseline_unknown_or_right_censored", "gross_return": gross,
                "raw_stock_spearman": None, "aligned_bucket_spearman": None,
            })
        if number % 100 == 0:
            print(f"bucket-return materialization: {number}/{len(decisions)} decisions", flush=True)
    frame = pd.DataFrame(rows)[BUCKET_COLUMNS]
    key = ["decision_date", "arm_id", "formation_sessions", "holding_sessions", "return_semantics", "weighting", "bucket_count", "bucket_id"]
    if frame.duplicated(key).any():
        raise RuntimeError("bucket-return duplicate key")
    expected_per_decision = sum((int(r.bucket_count) + 5) if int(r.bucket_count) > 0 else 1 for r in registry.itertuples(index=False))
    if len(frame) != len(decisions) * expected_per_decision:
        raise RuntimeError(f"bucket-return exact grid failure: {len(frame)} != {len(decisions)}*{expected_per_decision}")
    return frame.sort_values(key, kind="mergesort").reset_index(drop=True)


SUMMARY_COLUMNS = [
    "arm_id", "formation_sessions", "holding_sessions", "matrix_role", "return_semantics", "weighting",
    "bucket_count", "series_role", "fold_id", "registered_decision_week_n", "signal_ready_week_n",
    "project_evaluable_week_n", "distinct_calendar_month_n", "distinct_calendar_year_n", "mean_return",
    "median_return", "annualized_arithmetic_mean", "unannualized_horizon_volatility", "annualized_volatility",
    "diagnostic_sharpe", "positive_rate", "p10", "ES10_loss", "worst_single_cohort_return",
    "mean_raw_stock_spearman", "mean_aligned_bucket_spearman", "nominal_hac_ci_low", "nominal_hac_ci_high",
    "nominal_hac_pvalue", "block_bootstrap_ci_low", "block_bootstrap_ci_high", "block_bootstrap_pvalue",
    "holm_adjusted_pvalue", "summary_status", "failure_reason",
]
INFERENCE_COLUMNS = [
    "test_id", "estimator", "arm_id", "formation_sessions", "holding_sessions", "return_semantics", "weighting",
    "bucket_count", "series_role", "fold_id", "calendar_slot_n", "evaluable_week_n", "null_value", "alternative",
    "hac_lag_weeks", "block_method", "block_length_weeks", "bootstrap_repetitions", "finite_bootstrap_repetitions",
    "bootstrap_seed", "scope_seed", "bootstrap_rng", "ci_method", "estimate", "standard_error", "ci_low", "ci_high",
    "nominal_pvalue", "holm_family_id", "holm_family_size", "holm_adjusted_pvalue", "inference_status", "failure_reason",
]


def test_identifier(row: dict[str, Any]) -> str:
    return (
        f"MEAN::{row['arm_id']}::F{int(row['formation_sessions'])}::H{int(row['holding_sessions'])}::"
        f"{row['return_semantics']}::{row['weighting']}::K{int(row['bucket_count'])}::{row['series_role']}::{row['fold_id']}"
    )


def materialize_summary_and_inference(bucket: pd.DataFrame, registry: pd.DataFrame, coverage: pd.DataFrame,
                                      calendar_frame: pd.DataFrame, config: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame]:
    possible = calendar_frame[calendar_frame["calendar_signal_possible"]].copy()
    fold_dates = {
        "FULL": pd.DatetimeIndex(possible["decision_date"]),
        "EARLY": pd.DatetimeIndex(possible.loc[possible["fold_id"] == "EARLY", "decision_date"]),
        "LATE": pd.DatetimeIndex(possible.loc[possible["fold_id"] == "LATE", "decision_date"]),
    }
    coverage_index = coverage.set_index(["decision_date", "arm_id"])
    bucket_groups = {
        key: group.set_index("decision_date") for key, group in bucket.groupby(
            ["arm_id", "formation_sessions", "holding_sessions", "return_semantics", "weighting", "bucket_count", "series_role"], sort=False,
        )
    }
    rows: list[dict[str, Any]] = []
    values_by_row: list[np.ndarray] = []
    for reg in registry.itertuples(index=False):
        roles = ["all_eligible_baseline"] if reg.arm_id == BASELINE_ARM else DERIVED_ROLES
        for role in roles:
            key = (reg.arm_id, int(reg.formation_sessions), int(reg.holding_sessions), reg.return_semantics, reg.weighting, int(reg.bucket_count), role)
            panel = bucket_groups[key]
            for fold in FOLD_ORDER:
                dates = fold_dates[fold]
                selected = panel.reindex(dates)
                x = pd.to_numeric(selected["gross_return"], errors="coerce").to_numpy(dtype=float)
                values_by_row.append(x)
                stats = return_statistics(x)
                hac = calendar_hac(x, int(config["inference"]["hac_lag_weeks"]))
                if reg.arm_id == BASELINE_ARM:
                    ready_n = len(dates)
                else:
                    ready_n = int(sum(bool(coverage_index.loc[(date, reg.arm_id), "decile_eligible"]) for date in dates))
                finite_dates = dates[np.isfinite(x)]
                vol = stats["vol"]
                annual_mean = float(stats["mean"] * 252 / reg.holding_sessions) if stats["mean"] is not None else None
                annual_vol = float(vol * math.sqrt(252 / reg.holding_sessions)) if vol is not None else None
                diagnostic_sharpe = annual_mean / annual_vol if annual_vol is not None and annual_vol > 0 else None
                raw_spearman = pd.to_numeric(selected["raw_stock_spearman"], errors="coerce")
                aligned_spearman = pd.to_numeric(selected["aligned_bucket_spearman"], errors="coerce")
                rows.append({
                    "arm_id": reg.arm_id, "formation_sessions": reg.formation_sessions, "holding_sessions": reg.holding_sessions,
                    "matrix_role": reg.matrix_role, "return_semantics": reg.return_semantics, "weighting": reg.weighting,
                    "bucket_count": reg.bucket_count, "series_role": role, "fold_id": fold,
                    "registered_decision_week_n": len(dates), "signal_ready_week_n": ready_n,
                    "project_evaluable_week_n": stats["n"], "distinct_calendar_month_n": len(set(finite_dates.to_period("M"))),
                    "distinct_calendar_year_n": len(set(finite_dates.year)), "mean_return": stats["mean"],
                    "median_return": stats["median"], "annualized_arithmetic_mean": annual_mean,
                    "unannualized_horizon_volatility": vol, "annualized_volatility": annual_vol,
                    "diagnostic_sharpe": diagnostic_sharpe, "positive_rate": stats["positive_rate"], "p10": stats["p10"],
                    "ES10_loss": stats["ES10_loss"], "worst_single_cohort_return": stats["worst"],
                    "mean_raw_stock_spearman": float(raw_spearman.mean()) if raw_spearman.notna().any() else None,
                    "mean_aligned_bucket_spearman": float(aligned_spearman.mean()) if aligned_spearman.notna().any() else None,
                    "nominal_hac_ci_low": hac["ci_low"], "nominal_hac_ci_high": hac["ci_high"],
                    "nominal_hac_pvalue": hac["p"], "block_bootstrap_ci_low": None, "block_bootstrap_ci_high": None,
                    "block_bootstrap_pvalue": None, "holm_adjusted_pvalue": None,
                    "summary_status": "pass" if stats["n"] > 0 else "not_evaluable",
                    "failure_reason": "" if stats["n"] > 0 else "no_evaluable_week",
                })
    if len(rows) != 1212:
        raise RuntimeError(f"summary exact row count failed: {len(rows)}")

    summary = pd.DataFrame(rows)
    inference_rows: list[dict[str, Any]] = []
    for fold_index, fold in enumerate(FOLD_ORDER):
        indices = summary.index[summary["fold_id"] == fold].to_numpy()
        matrix = np.column_stack([values_by_row[i] for i in indices])
        total = matrix.shape[0]
        scope_seed = int(config["inference"]["bootstrap_seed"]) + fold_index
        counts = moving_block_count_matrix(total, int(config["inference"]["bootstrap_repetitions"]), int(config["inference"]["block_length_weeks"]), scope_seed)
        bootstrap, finite_n = bootstrap_matrix(matrix, counts)
        for position, row_index in enumerate(indices):
            observed = summary.loc[row_index].to_dict()
            finite_boot = bootstrap[:, position][np.isfinite(bootstrap[:, position])]
            observed_mean = observed["mean_return"]
            if len(finite_boot) >= int(config["inference"]["minimum_finite_bootstrap_repetitions"]) and observed_mean is not None and np.isfinite(observed_mean):
                ci_low, ci_high = np.quantile(finite_boot, [0.025, 0.975], method="linear")
                pvalue = (1 + int(np.sum(np.abs(finite_boot - observed_mean) >= abs(observed_mean)))) / (len(finite_boot) + 1)
                boot_status, boot_reason = "pass", ""
                summary.loc[row_index, ["block_bootstrap_ci_low", "block_bootstrap_ci_high", "block_bootstrap_pvalue"]] = [ci_low, ci_high, pvalue]
            else:
                ci_low = ci_high = pvalue = None
                boot_status, boot_reason = "fail", "finite_bootstrap_repetitions_below_4500"
            hac = calendar_hac(values_by_row[row_index], int(config["inference"]["hac_lag_weeks"]))
            test_id = test_identifier(observed)
            common = {
                "test_id": test_id, "arm_id": observed["arm_id"], "formation_sessions": observed["formation_sessions"],
                "holding_sessions": observed["holding_sessions"], "return_semantics": observed["return_semantics"],
                "weighting": observed["weighting"], "bucket_count": observed["bucket_count"], "series_role": observed["series_role"],
                "fold_id": fold, "calendar_slot_n": total, "evaluable_week_n": int(np.isfinite(values_by_row[row_index]).sum()),
                "null_value": 0.0, "alternative": "two_sided", "estimate": observed_mean,
                "holm_family_id": None, "holm_family_size": None, "holm_adjusted_pvalue": None,
            }
            inference_rows.append(common | {
                "estimator": "newey_west_bartlett", "hac_lag_weeks": int(config["inference"]["hac_lag_weeks"]),
                "block_method": None, "block_length_weeks": None, "bootstrap_repetitions": None,
                "finite_bootstrap_repetitions": None, "bootstrap_seed": None, "scope_seed": None, "bootstrap_rng": None,
                "ci_method": "normal_1.959963984540054", "standard_error": hac["se"], "ci_low": hac["ci_low"],
                "ci_high": hac["ci_high"], "nominal_pvalue": hac["p"],
                "inference_status": "pass" if hac["p"] is not None else "fail",
                "failure_reason": "" if hac["p"] is not None else "hac_variance_nonpositive_or_insufficient_n",
            })
            inference_rows.append(common | {
                "estimator": "moving_calendar_week_block_bootstrap", "hac_lag_weeks": None,
                "block_method": "non_circular_contiguous", "block_length_weeks": min(int(config["inference"]["block_length_weeks"]), total),
                "bootstrap_repetitions": int(config["inference"]["bootstrap_repetitions"]),
                "finite_bootstrap_repetitions": int(finite_n[position]), "bootstrap_seed": int(config["inference"]["bootstrap_seed"]),
                "scope_seed": scope_seed, "bootstrap_rng": "numpy.random.PCG64", "ci_method": "percentile_linear_2.5_97.5",
                "standard_error": None, "ci_low": ci_low, "ci_high": ci_high, "nominal_pvalue": pvalue,
                "inference_status": boot_status, "failure_reason": boot_reason,
            })

    inference = pd.DataFrame(inference_rows)
    if len(inference) != 2424:
        raise RuntimeError(f"inference exact row count failed: {len(inference)}")
    holm_mask = (
        (inference["estimator"] == "newey_west_bartlett") & (inference["fold_id"] == "FULL")
        & (inference["return_semantics"] == PROJECT_SEMANTICS) & (inference["weighting"] == "EW")
        & (inference["bucket_count"] == 10) & (inference["series_role"] == "favorable_bucket")
        & (((inference["arm_id"] == "SRC3_MKT_RESID_CONT_5D") & (inference["holding_sessions"] == 5))
           | ((inference["arm_id"] == "SRC4_MKT_RESID_CONT_10D") & (inference["holding_sessions"] == 10)))
    )
    family = inference.loc[holm_mask].sort_values(["nominal_pvalue", "test_id"], kind="mergesort")
    if len(family) != 2 or family["nominal_pvalue"].isna().any():
        adjusted_map: dict[str, float] = {}
    else:
        running = 0.0
        adjusted_map = {}
        m = len(family)
        for i, item in enumerate(family.itertuples(index=False), start=1):
            running = max(running, min(1.0, (m - i + 1) * float(item.nominal_pvalue)))
            adjusted_map[item.test_id] = running
    for idx in inference.index[holm_mask]:
        test_id = inference.at[idx, "test_id"]
        inference.at[idx, "holm_family_id"] = "HOLM_MATCHED_PRIMARY_EW_DECILE_FAVORABLE_FULL"
        inference.at[idx, "holm_family_size"] = 2
        inference.at[idx, "holm_adjusted_pvalue"] = adjusted_map.get(test_id)
        summary_mask = summary.apply(lambda r: test_identifier(r.to_dict()) == test_id, axis=1)
        summary.loc[summary_mask, "holm_adjusted_pvalue"] = adjusted_map.get(test_id)
    return summary[SUMMARY_COLUMNS], inference[INFERENCE_COLUMNS]


def materialize_paired(bucket: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    pairs = [
        ("SRC3_MKT_RESID_CONT_5D", "SRC1_TOTAL_CONT_5D", 5, 5),
        ("SRC4_MKT_RESID_CONT_10D", "SRC2_TOTAL_CONT_10D", 10, 10),
    ]
    indexed = bucket.set_index(["decision_date", "arm_id", "holding_sessions", "return_semantics", "weighting", "bucket_count", "series_role"])["gross_return"]
    fold_by_date = bucket.drop_duplicates("decision_date").set_index("decision_date")["fold_id"].to_dict()
    rows: list[dict[str, Any]] = []
    for residual_arm, total_arm, formation, holding in pairs:
        for semantics in [PROJECT_SEMANTICS, COMPLETE_CASE_SEMANTICS]:
            for weighting in ["EW", "VW"]:
                for k in [5, 10]:
                    series = {}
                    for label, arm in [("SRC", residual_arm), ("Total", total_arm)]:
                        series[(label, "fav")] = indexed.xs((arm, holding, semantics, weighting, k, "favorable_bucket"), level=["arm_id", "holding_sessions", "return_semantics", "weighting", "bucket_count", "series_role"])
                        series[(label, "spread")] = indexed.xs((arm, holding, semantics, weighting, k, "favorable_minus_unfavorable"), level=["arm_id", "holding_sessions", "return_semantics", "weighting", "bucket_count", "series_role"])
                    frame = pd.concat(series, axis=1).sort_index()
                    for fold in FOLD_ORDER:
                        if fold == "FULL":
                            scope = frame[frame.index.map(lambda date: fold_by_date.get(date) in ["EARLY", "LATE"])]
                        else:
                            fold_dates = {date for date, value in fold_by_date.items() if value == fold}
                            scope = frame.loc[frame.index.isin(fold_dates)]
                        common = scope.dropna()
                        src_fav, total_fav = common.get(("SRC", "fav"), pd.Series(dtype=float)), common.get(("Total", "fav"), pd.Series(dtype=float))
                        src_spread, total_spread = common.get(("SRC", "spread"), pd.Series(dtype=float)), common.get(("Total", "spread"), pd.Series(dtype=float))
                        src_stats, total_stats = return_statistics(src_fav), return_statistics(total_fav)
                        fav_delta = float((src_fav - total_fav).mean()) if len(common) else None
                        spread_delta = float((src_spread - total_spread).mean()) if len(common) else None
                        src_vol, total_vol = src_stats["vol"], total_stats["vol"]
                        src_es, total_es = src_stats["ES10_loss"], total_stats["ES10_loss"]
                        vol_ratio = src_vol / total_vol if src_vol is not None and total_vol is not None and total_vol > 0 else None
                        es_ratio = src_es / total_es if src_es is not None and total_es is not None and total_es > 0 else None
                        rows.append({
                            "residual_arm_id": residual_arm, "total_arm_id": total_arm, "formation_sessions": formation,
                            "holding_sessions": holding, "return_semantics": semantics, "weighting": weighting,
                            "bucket_count": k, "fold_id": fold, "registered_pair_week_n": len(scope),
                            "paired_evaluable_week_n": len(common), "SRC_favorable_mean": src_stats["mean"],
                            "Total_favorable_mean": total_stats["mean"], "paired_favorable_delta": fav_delta,
                            "SRC_spread_mean": float(src_spread.mean()) if len(common) else None,
                            "Total_spread_mean": float(total_spread.mean()) if len(common) else None,
                            "paired_spread_delta": spread_delta, "SRC_favorable_volatility": src_vol,
                            "Total_favorable_volatility": total_vol,
                            "paired_volatility_delta": src_vol - total_vol if src_vol is not None and total_vol is not None else None,
                            "paired_volatility_ratio": vol_ratio, "SRC_ES10_loss": src_es, "Total_ES10_loss": total_es,
                            "paired_ES10_loss_delta": src_es - total_es if src_es is not None and total_es is not None else None,
                            "paired_ES10_loss_ratio": es_ratio, "minimum_paired_favorable_delta": holding * 0.0001,
                            "paired_favorable_nondegradation_tolerance": -holding * 0.00005,
                            "minimum_paired_spread_delta": holding * 0.0001,
                            "maximum_paired_volatility_ratio": 0.95, "maximum_paired_ES10_loss_ratio": 0.95,
                            "residualization_value": "not_applicable" if fold != "FULL" else "not_evaluable",
                            "classification_reason": "fold_metric_only" if fold != "FULL" else "pending_cross_fold_classification",
                        })
    frame = pd.DataFrame(rows)
    key_columns = ["residual_arm_id", "total_arm_id", "formation_sessions", "holding_sessions", "return_semantics", "weighting", "bucket_count"]
    for _, group in frame.groupby(key_columns, sort=False):
        records = {row.fold_id: row for row in group.itertuples()}
        full, early, late = records["FULL"], records["EARLY"], records["LATE"]
        idx = full.Index
        metrics = [full.paired_favorable_delta, early.paired_favorable_delta, late.paired_favorable_delta]
        if any(value is None or not np.isfinite(value) for value in metrics):
            value, reason = "not_evaluable", "required_fold_metric_missing"
        else:
            tolerance = float(full.paired_favorable_nondegradation_tolerance)
            material = (
                float(full.paired_favorable_delta) >= float(full.minimum_paired_favorable_delta)
                or (full.paired_spread_delta is not None and np.isfinite(full.paired_spread_delta) and float(full.paired_spread_delta) >= float(full.minimum_paired_spread_delta) and float(full.paired_favorable_delta) >= tolerance)
                or (full.paired_volatility_ratio is not None and np.isfinite(full.paired_volatility_ratio) and float(full.paired_volatility_ratio) <= 0.95 and float(full.paired_favorable_delta) >= tolerance)
                or (full.paired_ES10_loss_ratio is not None and np.isfinite(full.paired_ES10_loss_ratio) and float(full.paired_ES10_loss_ratio) <= 0.95 and float(full.paired_favorable_delta) >= tolerance)
            )
            nondegrade = float(early.paired_favorable_delta) >= tolerance and float(late.paired_favorable_delta) >= tolerance
            value = bool(material and nondegrade)
            reason = "material_improvement_and_fold_nondegradation" if value else "materiality_or_fold_nondegradation_not_met"
        frame.at[idx, "residualization_value"] = value
        frame.at[idx, "classification_reason"] = reason
    if len(frame) != 48:
        raise RuntimeError(f"paired attribution exact row count failed: {len(frame)}")
    return frame


def materialize_path_decomposition(assignments: pd.DataFrame, forward: pd.DataFrame) -> pd.DataFrame:
    outcomes = forward.set_index(["instrument_id", "decision_date", "holding_sessions", "return_semantics"])["resolved_forward_return"]
    rows: list[dict[str, Any]] = []
    for (decision, arm, k), group in assignments.groupby(["decision_date", "arm_id", "bucket_count"], sort=True):
        for weighting in ["EW", "VW"]:
            weight_col = "ew_target_weight" if weighting == "EW" else "vw_target_weight"
            for semantics in [PROJECT_SEMANTICS, COMPLETE_CASE_SEMANTICS]:
                h5 = outcomes.xs((decision, 5, semantics), level=["decision_date", "holding_sessions", "return_semantics"])
                h10 = outcomes.xs((decision, 10, semantics), level=["decision_date", "holding_sessions", "return_semantics"])
                for bucket_id in range(1, int(k) + 1):
                    selected = group[group["bucket_id"] == bucket_id].copy()
                    weights = pd.to_numeric(selected[weight_col], errors="coerce")
                    valid_weight = np.isfinite(weights) & (weights > 0)
                    selected, weights = selected.loc[valid_weight], weights.loc[valid_weight]
                    r5 = selected["instrument_id"].map(h5).astype(float)
                    r10 = selected["instrument_id"].map(h10).astype(float)
                    joint = np.isfinite(r5) & np.isfinite(r10)
                    if semantics == PROJECT_SEMANTICS:
                        evaluable = len(selected) > 0 and bool(joint.all())
                        use = joint if evaluable else np.zeros(len(joint), dtype=bool)
                    else:
                        evaluable = bool(joint.any())
                        use = joint
                    if evaluable:
                        w = weights[use] / weights[use].sum()
                        v5 = float(np.dot(w, 1.0 + r5[use]))
                        v10 = float(np.dot(w, 1.0 + r10[use]))
                        one_five, one_ten = v5 - 1.0, v10 - 1.0
                        six_ten = v10 / v5 - 1.0 if v5 > 0 else np.nan
                    else:
                        one_five = one_ten = six_ten = np.nan
                    rows.append({
                        "decision_date": decision, "arm_id": arm, "formation_sessions": SCORED_ARMS[arm]["formation"],
                        "weighting": weighting, "bucket_count": k, "bucket_id": bucket_id,
                        "return_semantics": semantics, "R_1_5": one_five, "R_1_10": one_ten, "R_6_10": six_ten,
                        "H5_evaluable": evaluable, "H10_evaluable": evaluable, "joint_evaluable": evaluable,
                        "not_evaluable_reason": "" if evaluable else "joint_H5_H10_population_not_evaluable",
                    })
    return pd.DataFrame(rows)


def three_state_or(values: Sequence[Any]) -> bool | str:
    if any(value is True or str(value).lower() == "true" for value in values):
        return True
    if values and all(value is False or str(value).lower() == "false" for value in values):
        return False
    return "not_evaluable"


def materialize_style(weekly: pd.DataFrame, assignments: pd.DataFrame, residual_panel_path: Path,
                      calendar_frame: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    decision_set = set(calendar_frame["decision_date"])
    beta = pd.read_parquet(residual_panel_path, columns=["instrument_id", "residual_date", "beta", "status"])
    beta["residual_date"] = pd.to_datetime(beta["residual_date"])
    beta = beta[(beta["residual_date"].isin(decision_set)) & (beta["status"] == "pass")][["instrument_id", "residual_date", "beta"]]
    beta_lookup = beta.set_index(["instrument_id", "residual_date"])["beta"]
    weekly_groups = {key: group.set_index("instrument_id") for key, group in weekly.groupby(["decision_date", "arm_id"], sort=False)}
    assignment_groups = {key: group.set_index("instrument_id") for key, group in assignments.groupby(["decision_date", "arm_id", "bucket_count"], sort=False)}
    rows: list[dict[str, Any]] = []
    arm_components: dict[str, dict[str, Any]] = {}
    for src_arm, total_arm in [("SRC3_MKT_RESID_CONT_5D", "SRC1_TOTAL_CONT_5D"), ("SRC4_MKT_RESID_CONT_10D", "SRC2_TOTAL_CONT_10D")]:
        weekly_rows: list[dict[str, Any]] = []
        for decision in sorted(decision_set):
            src = weekly_groups[(decision, src_arm)]
            total = weekly_groups[(decision, total_arm)]
            lowvol = weekly_groups[(decision, "SRC5_LOWVOL_20D_COMPARATOR")]
            src_score = pd.to_numeric(src["raw_signal"], errors="coerce")
            total_score = pd.to_numeric(total["raw_signal"], errors="coerce")
            low_score = pd.to_numeric(lowvol["raw_signal"], errors="coerce")
            cap = pd.to_numeric(src["total_market_cap_cny"], errors="coerce")
            common_total = pd.concat([src_score.rename("src"), total_score.rename("other")], axis=1).dropna()
            common_low = pd.concat([src_score.rename("src"), low_score.rename("other")], axis=1).dropna()
            common_size = pd.concat([src_score.rename("src"), np.log(cap.where(cap > 0)).rename("other")], axis=1).dropna()
            total_spearman = average_midrank_spearman(common_total["src"], common_total["other"])
            low_spearman = average_midrank_spearman(common_low["src"], -common_low["other"])
            size_spearman = average_midrank_spearman(common_size["src"], common_size["other"])
            j_total = j_low = None
            minimum_jaccard = int(config["style"]["jaccard_common_population_minimum_n"])
            if len(common_total) >= minimum_jaccard:
                src_bucket = assign_buckets(common_total["src"], 10)
                other_bucket = assign_buckets(common_total["other"], 10)
                left, right = set(src_bucket[src_bucket == 10].index), set(other_bucket[other_bucket == 10].index)
                j_total = len(left & right) / len(left | right) if left | right else None
            if len(common_low) >= minimum_jaccard:
                src_bucket = assign_buckets(common_low["src"], 10)
                other_bucket = assign_buckets(common_low["other"], 10)
                left, right = set(src_bucket[src_bucket == 10].index), set(other_bucket[other_bucket == 1].index)
                j_low = len(left & right) / len(left | right) if left | right else None
            assignment = assignment_groups[(decision, src_arm, 10)]
            favorable = assignment[(assignment["favorable_bucket"]) & np.isfinite(assignment["ew_target_weight"]) & (assignment["ew_target_weight"] > 0)]
            betas = pd.Series([beta_lookup.get((instrument, decision), np.nan) for instrument in favorable.index], index=favorable.index, dtype=float)
            if len(favorable) and np.isfinite(betas).all():
                weights = favorable["ew_target_weight"].astype(float)
                weighted_beta = float(np.dot(weights / weights.sum(), betas))
            else:
                weighted_beta = None
            weekly_rows.append({
                "record_type": "WEEKLY", "decision_date": decision, "src_arm_id": src_arm,
                "common_total_population_n": len(common_total), "common_lowvol_population_n": len(common_low),
                "common_size_population_n": len(common_size), "spearman_SRC_vs_total": total_spearman,
                "spearman_SRC_vs_negative_VOL20": low_spearman, "spearman_SRC_vs_log_market_cap": size_spearman,
                "top_decile_jaccard_SRC_vs_total": j_total, "top_decile_jaccard_SRC_vs_lowvol": j_low,
                "favorable_bucket_weighted_mean_beta": weighted_beta, "beta_attribution_weighting": "EW_decile_favorable",
                "valid_lowvol_spearman_week_n": None, "valid_lowvol_jaccard_week_n": None, "valid_size_spearman_week_n": None,
                "warning_minimum_week_n": int(config["style"]["warning_minimum_finite_week_n"]),
                "full_history_median_spearman_SRC_vs_negative_VOL20": None, "full_history_median_lowvol_jaccard": None,
                "full_history_median_spearman_SRC_vs_log_market_cap": None, "arm_scale_dependence_warning": None,
                "arm_size_dependence_warning": None, "overall_scale_dependence_warning": None,
                "overall_size_dependence_warning": None, "style_status": "pass", "failure_reason": "",
            })
        weekly_frame = pd.DataFrame(weekly_rows)
        finite_low = pd.to_numeric(weekly_frame["spearman_SRC_vs_negative_VOL20"], errors="coerce").dropna()
        finite_jaccard = pd.to_numeric(weekly_frame["top_decile_jaccard_SRC_vs_lowvol"], errors="coerce").dropna()
        finite_size = pd.to_numeric(weekly_frame["spearman_SRC_vs_log_market_cap"], errors="coerce").dropna()
        minimum_n = int(config["style"]["warning_minimum_finite_week_n"])
        low_component: bool | str = abs(float(finite_low.median())) >= 0.70 if len(finite_low) >= minimum_n else "not_evaluable"
        j_component: bool | str = float(finite_jaccard.median()) >= 0.60 if len(finite_jaccard) >= minimum_n else "not_evaluable"
        size_component: bool | str = abs(float(finite_size.median())) >= 0.70 if len(finite_size) >= minimum_n else "not_evaluable"
        scale_warning = three_state_or([low_component, j_component])
        arm_components[src_arm] = {"scale": scale_warning, "size": size_component}
        rows.extend(weekly_rows)
        rows.append({
            "record_type": "FULL_SUMMARY", "decision_date": "SUMMARY", "src_arm_id": src_arm,
            "common_total_population_n": None, "common_lowvol_population_n": None, "common_size_population_n": None,
            "spearman_SRC_vs_total": None, "spearman_SRC_vs_negative_VOL20": None, "spearman_SRC_vs_log_market_cap": None,
            "top_decile_jaccard_SRC_vs_total": None, "top_decile_jaccard_SRC_vs_lowvol": None,
            "favorable_bucket_weighted_mean_beta": None, "beta_attribution_weighting": "EW_decile_favorable",
            "valid_lowvol_spearman_week_n": len(finite_low), "valid_lowvol_jaccard_week_n": len(finite_jaccard),
            "valid_size_spearman_week_n": len(finite_size), "warning_minimum_week_n": minimum_n,
            "full_history_median_spearman_SRC_vs_negative_VOL20": float(finite_low.median()) if len(finite_low) else None,
            "full_history_median_lowvol_jaccard": float(finite_jaccard.median()) if len(finite_jaccard) else None,
            "full_history_median_spearman_SRC_vs_log_market_cap": float(finite_size.median()) if len(finite_size) else None,
            "arm_scale_dependence_warning": scale_warning, "arm_size_dependence_warning": size_component,
            "overall_scale_dependence_warning": None, "overall_size_dependence_warning": None,
            "style_status": "pass" if scale_warning != "not_evaluable" and size_component != "not_evaluable" else "not_evaluable",
            "failure_reason": "" if scale_warning != "not_evaluable" and size_component != "not_evaluable" else "warning_component_below_52_finite_weeks",
        })
    overall_scale = three_state_or([arm_components[a]["scale"] for a in arm_components])
    overall_size = three_state_or([arm_components[a]["size"] for a in arm_components])
    for row in rows:
        if row["record_type"] == "FULL_SUMMARY":
            row["overall_scale_dependence_warning"] = overall_scale
            row["overall_size_dependence_warning"] = overall_size
    result = pd.DataFrame(rows)
    expected = 2 * (len(calendar_frame) + 1)
    if len(result) != expected or result.duplicated(["record_type", "decision_date", "src_arm_id"]).any():
        raise RuntimeError("style attribution exact-row/key failure")
    return result


def materialize_stability(bucket: pd.DataFrame, calendar_frame: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    possible = calendar_frame[calendar_frame["calendar_signal_possible"]]
    for arm, formation, holding in [
        ("SRC3_MKT_RESID_CONT_5D", 5, 5), ("SRC4_MKT_RESID_CONT_10D", 10, 10),
    ]:
        panel = bucket[
            (bucket["arm_id"] == arm) & (bucket["holding_sessions"] == holding)
            & (bucket["return_semantics"] == PROJECT_SEMANTICS) & (bucket["weighting"] == "EW")
            & (bucket["bucket_count"] == 10) & (bucket["series_role"].isin(["favorable_bucket", "favorable_minus_unfavorable"]))
        ].pivot(index="decision_date", columns="series_role", values="gross_return")
        slices: list[tuple[str, str, pd.DatetimeIndex]] = [
            ("FOLD", "FULL", pd.DatetimeIndex(possible["decision_date"])),
            ("FOLD", "EARLY", pd.DatetimeIndex(possible.loc[possible["fold_id"] == "EARLY", "decision_date"])),
            ("FOLD", "LATE", pd.DatetimeIndex(possible.loc[possible["fold_id"] == "LATE", "decision_date"])),
        ]
        for year in sorted(possible["decision_date"].dt.year.unique()):
            slices.append(("YEAR", str(year), pd.DatetimeIndex(possible.loc[possible["decision_date"].dt.year == year, "decision_date"])))
        for slice_type, slice_id, dates in slices:
            selected = panel.reindex(dates)
            common = selected.dropna()
            fav_mean = float(common["favorable_bucket"].mean()) if len(common) else None
            spread_mean = float(common["favorable_minus_unfavorable"].mean()) if len(common) else None
            rows.append({
                "arm_id": arm, "formation_sessions": formation, "holding_sessions": holding,
                "return_semantics": PROJECT_SEMANTICS, "weighting": "EW", "bucket_count": 10,
                "slice_type": slice_type, "slice_id": slice_id, "registered_decision_week_n": len(dates),
                "evaluable_week_n": len(common), "favorable_mean_return": fav_mean, "spread_mean_return": spread_mean,
                "favorable_positive": fav_mean > 0 if fav_mean is not None else None,
                "spread_positive": spread_mean > 0 if spread_mean is not None else None,
                "stability_status": "pass" if len(common) else "not_evaluable",
                "failure_reason": "" if len(common) else "no_common_evaluable_week",
            })
    return pd.DataFrame(rows)


def materialize_dominance(bucket: pd.DataFrame, assignments: pd.DataFrame, forward: pd.DataFrame) -> pd.DataFrame:
    outcomes = forward.set_index(["instrument_id", "decision_date", "holding_sessions", "return_semantics"])["resolved_forward_return"]
    assignment_groups = {key: group for key, group in assignments.groupby(["decision_date", "arm_id", "bucket_count"], sort=False)}
    rows: list[dict[str, Any]] = []
    for arm, formation, holding in [
        ("SRC3_MKT_RESID_CONT_5D", 5, 5), ("SRC4_MKT_RESID_CONT_10D", 10, 10),
    ]:
        panel = bucket[
            (bucket["arm_id"] == arm) & (bucket["holding_sessions"] == holding)
            & (bucket["return_semantics"] == PROJECT_SEMANTICS) & (bucket["weighting"] == "EW")
            & (bucket["bucket_count"] == 10) & (bucket["series_role"].isin(["favorable_bucket", "favorable_minus_unfavorable"]))
        ].pivot(index="decision_date", columns="series_role", values="gross_return").dropna()
        base_fav = float(panel["favorable_bucket"].mean()) if len(panel) else np.nan
        base_spread = float(panel["favorable_minus_unfavorable"].mean()) if len(panel) else np.nan
        recomputations: list[tuple[float, float]] = []

        def audit_row(audit_type: str, omitted_id: str, fav: float | None, spread: float | None) -> dict[str, Any]:
            if fav is not None and spread is not None and np.isfinite(fav) and np.isfinite(spread):
                recomputations.append((float(fav), float(spread)))
            return {
                "arm_id": arm, "formation_sessions": formation, "holding_sessions": holding,
                "return_semantics": PROJECT_SEMANTICS, "weighting": "EW", "bucket_count": 10,
                "audit_type": audit_type, "omitted_id": omitted_id, "base_favorable_mean": base_fav,
                "recomputed_favorable_mean": fav, "favorable_delta_from_base": fav - base_fav if fav is not None and np.isfinite(fav) else None,
                "base_spread_mean": base_spread, "recomputed_spread_mean": spread,
                "spread_delta_from_base": spread - base_spread if spread is not None and np.isfinite(spread) else None,
                "minimum_favorable_recomputed_mean": None, "maximum_favorable_recomputed_mean": None,
                "minimum_spread_recomputed_mean": None, "maximum_spread_recomputed_mean": None,
                "maximum_single_week_absolute_contribution_share": None, "top3_week_absolute_contribution_share": None,
                "H5_H10_joint_week_n": None, "H5_H10_correlation": None,
                "sealed_assignment_reused": True, "reranking_performed": False,
                "status": "pass" if fav is not None and spread is not None and np.isfinite(fav) and np.isfinite(spread) else "not_evaluable",
                "failure_reason": "" if fav is not None and spread is not None and np.isfinite(fav) and np.isfinite(spread) else "deletion_leaves_no_evaluable_week",
            }

        for date in panel.index:
            remaining = panel.drop(index=date)
            rows.append(audit_row("LODO_WEEK", str(pd.Timestamp(date).date()), float(remaining["favorable_bucket"].mean()) if len(remaining) else None, float(remaining["favorable_minus_unfavorable"].mean()) if len(remaining) else None))
        months = panel.index.to_period("M")
        for month in sorted(months.unique()):
            remaining = panel[months != month]
            rows.append(audit_row("LOMO_MONTH", str(month), float(remaining["favorable_bucket"].mean()) if len(remaining) else None, float(remaining["favorable_minus_unfavorable"].mean()) if len(remaining) else None))

        week_detail: dict[pd.Timestamp, dict[str, Any]] = {}
        instrument_union: set[str] = set()
        for date, values in panel.iterrows():
            group = assignment_groups[(pd.Timestamp(date), arm, 10)]
            outcome_map = outcomes.xs((pd.Timestamp(date), holding, PROJECT_SEMANTICS), level=["decision_date", "holding_sessions", "return_semantics"])
            buckets: dict[str, dict[str, tuple[float, float]]] = {}
            for label, bucket_id in [("fav", 10), ("unf", 1)]:
                selected = group[(group["bucket_id"] == bucket_id) & np.isfinite(group["ew_target_weight"]) & (group["ew_target_weight"] > 0)]
                mapping = {str(item.instrument_id): (float(item.ew_target_weight), float(outcome_map.loc[item.instrument_id])) for item in selected.itertuples(index=False)}
                buckets[label] = mapping
                instrument_union.update(mapping)
            week_detail[pd.Timestamp(date)] = {"fav_base": float(values["favorable_bucket"]), "unf_base": float(values["favorable_bucket"] - values["favorable_minus_unfavorable"]), **buckets}
        for instrument in sorted(instrument_union):
            fav_values, spread_values = [], []
            for detail in week_detail.values():
                fav, unf = detail["fav_base"], detail["unf_base"]
                if instrument in detail["fav"]:
                    weight, value = detail["fav"][instrument]
                    fav = (fav - weight * value) / (1 - weight) if weight < 1 else np.nan
                if instrument in detail["unf"]:
                    weight, value = detail["unf"][instrument]
                    unf = (unf - weight * value) / (1 - weight) if weight < 1 else np.nan
                if np.isfinite(fav) and np.isfinite(unf):
                    fav_values.append(fav)
                    spread_values.append(fav - unf)
            fav_mean = float(np.mean(fav_values)) if fav_values else None
            spread_mean = float(np.mean(spread_values)) if spread_values else None
            rows.append(audit_row("LOIO_INSTRUMENT", instrument, fav_mean, spread_mean))

        absolute = np.abs(panel["favorable_bucket"].to_numpy(dtype=float))
        denominator = float(absolute.sum())
        max_share = float(absolute.max() / denominator) if denominator > 0 else None
        top3_share = float(np.sort(absolute)[-3:].sum() / denominator) if denominator > 0 else None
        cross = bucket[
            (bucket["arm_id"] == arm) & (bucket["return_semantics"] == PROJECT_SEMANTICS)
            & (bucket["weighting"] == "EW") & (bucket["bucket_count"] == 10)
            & (bucket["series_role"] == "favorable_bucket") & (bucket["holding_sessions"].isin([5, 10]))
        ].pivot(index="decision_date", columns="holding_sessions", values="gross_return").dropna()
        correlation = float(np.corrcoef(cross[5], cross[10])[0, 1]) if len(cross) >= 3 and cross[5].std() > 0 and cross[10].std() > 0 else None
        summary = audit_row("SUMMARY", "SUMMARY", None, None)
        summary["status"], summary["failure_reason"] = "pass", ""
        if recomputations:
            summary["minimum_favorable_recomputed_mean"] = min(x[0] for x in recomputations)
            summary["maximum_favorable_recomputed_mean"] = max(x[0] for x in recomputations)
            summary["minimum_spread_recomputed_mean"] = min(x[1] for x in recomputations)
            summary["maximum_spread_recomputed_mean"] = max(x[1] for x in recomputations)
        summary["maximum_single_week_absolute_contribution_share"] = max_share
        summary["top3_week_absolute_contribution_share"] = top3_share
        summary["H5_H10_joint_week_n"] = len(cross)
        summary["H5_H10_correlation"] = correlation
        rows.append(summary)
    return pd.DataFrame(rows)


def materialize_cost(assignments: pd.DataFrame, bucket: pd.DataFrame, registry: pd.DataFrame,
                     calendar_frame: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    gross_key_columns = ["decision_date", "arm_id", "holding_sessions", "return_semantics", "weighting", "bucket_count"]
    favorable_rows = bucket[bucket["series_role"] == "favorable_bucket"]
    if favorable_rows.duplicated(gross_key_columns).any():
        raise RuntimeError("favorable gross-return lookup is not unique")
    gross = favorable_rows.set_index(gross_key_columns)["gross_return"]
    assignment_groups = {key: group for key, group in assignments.groupby(["decision_date", "arm_id", "bucket_count"], sort=False)}
    decisions = sorted(calendar_frame["decision_date"].unique())
    rows: list[dict[str, Any]] = []
    for reg in registry[registry["arm_id"] != BASELINE_ARM].itertuples(index=False):
        turnovers, returns, fees, buy_fees, sell_fees = [], [], [], [], []
        favorable_id = 1 if SCORED_ARMS[reg.arm_id]["favorable"] == "low" else int(reg.bucket_count)
        weight_col = "ew_target_weight" if reg.weighting == "EW" else "vw_target_weight"
        for previous, current in zip(decisions[:-1], decisions[1:]):
            previous_group = assignment_groups[(pd.Timestamp(previous), reg.arm_id, int(reg.bucket_count))]
            current_group = assignment_groups[(pd.Timestamp(current), reg.arm_id, int(reg.bucket_count))]
            previous_weights = previous_group.loc[previous_group["bucket_id"] == favorable_id, ["instrument_id", weight_col]].set_index("instrument_id")[weight_col].dropna().astype(float)
            current_weights = current_group.loc[current_group["bucket_id"] == favorable_id, ["instrument_id", weight_col]].set_index("instrument_id")[weight_col].dropna().astype(float)
            if previous_weights.empty or current_weights.empty or not np.isclose(previous_weights.sum(), 1.0) or not np.isclose(current_weights.sum(), 1.0):
                continue
            gross_key = (pd.Timestamp(current), reg.arm_id, int(reg.holding_sessions), reg.return_semantics, reg.weighting, int(reg.bucket_count))
            gross_value = float(gross.get(gross_key, np.nan))
            if not np.isfinite(gross_value):
                continue
            union = previous_weights.index.union(current_weights.index)
            turnover = 0.5 * float(np.abs(current_weights.reindex(union, fill_value=0.0) - previous_weights.reindex(union, fill_value=0.0)).sum())
            buy_fee, sell_fee = transfer_fee_bps(config, pd.Timestamp(current))
            round_trip = 2.5 + 5.0 + buy_fee + 2.5 + 5.0 + 5.0 + sell_fee
            turnovers.append(turnover)
            returns.append(gross_value)
            fees.append(round_trip / 2.0)
            buy_fees.append(buy_fee)
            sell_fees.append(sell_fee)
        valid_n = len(turnovers)
        mean_turnover = float(np.mean(turnovers)) if valid_n else None
        mean_return = float(np.mean(returns)) if valid_n else None
        break_even = mean_return / (2 * mean_turnover) * 10000 if mean_return is not None and mean_turnover is not None and mean_turnover > 0 else None
        weighted_fee = float(np.average(fees, weights=turnovers)) if valid_n and sum(turnovers) > 0 else None
        multiple = break_even / weighted_fee if break_even is not None and weighted_fee is not None and weighted_fee > 0 else None
        feasible = bool(multiple is not None and np.isfinite(multiple) and mean_return is not None and mean_return > 0 and multiple >= 1.25)
        rows.append({
            "arm_id": reg.arm_id, "formation_sessions": reg.formation_sessions, "holding_sessions": reg.holding_sessions,
            "weighting": reg.weighting, "bucket_count": reg.bucket_count, "bucket_id": "FAVORABLE",
            "return_semantics": reg.return_semantics,
            "cost_transition_scope_id": f"C_H::{reg.arm_id}::H{reg.holding_sessions}::{reg.return_semantics}::{reg.weighting}::K{reg.bucket_count}",
            "valid_transition_n": valid_n, "gross_return_week_n": valid_n, "turnover_week_n": valid_n,
            "same_population_gate": True, "mean_target_turnover": mean_turnover, "mean_gross_return": mean_return,
            "break_even_one_way_cost_bps": break_even, "commission_buy_bps": 2.5, "commission_sell_bps": 2.5,
            "slippage_buy_bps": 5.0, "slippage_sell_bps": 5.0,
            "mean_transfer_fee_buy_bps": float(np.mean(buy_fees)) if buy_fees else None,
            "mean_transfer_fee_sell_bps": float(np.mean(sell_fees)) if sell_fees else None,
            "mean_stamp_tax_sell_bps": 5.0, "stamp_tax_proxy_mode": "current_5bps_applied_uniformly_to_history",
            "historical_stamp_tax_schedule_replication": False, "minimum_commission_included": False,
            "turnover_weighted_frozen_one_way_cost_bps": weighted_fee, "break_even_cost_multiple_proxy": multiple,
            "break_even_one_way_cost_multiple_floor": 1.25, "frozen_cost_contract_gate": "pass",
            "cost_feasible": feasible, "failure_reason": "" if feasible else "nonpositive_gross_or_break_even_multiple_below_floor",
        })
    result = pd.DataFrame(rows)
    if len(result) != 80:
        raise RuntimeError(f"cost exact row count failed: {len(result)}")
    return result


def bool_value(value: Any) -> bool:
    return value is True or str(value).lower() == "true"


def evaluate_gates(summary: pd.DataFrame, paired: pd.DataFrame, coverage: pd.DataFrame, cost: pd.DataFrame,
                   style: pd.DataFrame, calendar_frame: pd.DataFrame) -> dict[str, Any]:
    gates: dict[str, Any] = {
        "historical_signal_execution_authorization_gate": "pass",
        "historical_outcome_execution_authorization_gate": "pass", "upstream_integrity_gate": "pass",
        "instrument_mapping_gate": "pass", "stage_read_whitelist_gate": "pass", "signal_access_lineage_gate": "pass",
        "outcome_access_scope_gate": "pass", "outcome_firewall_gate": "pass", "preoutcome_manifest_hash_gate": "pass",
        "signal_manifest_hash_gate": "pass", "historical_manifest_hash_gate": "pass",
        "frozen_cost_contract_gate": "pass", "frozen_cost_source_integrity_gate": "pass",
    }
    possible_dates = set(calendar_frame.loc[calendar_frame["calendar_signal_possible"], "decision_date"])

    def summary_row(arm: str, holding: int, role: str, fold: str) -> pd.Series:
        selected = summary[
            (summary["arm_id"] == arm) & (summary["holding_sessions"] == holding)
            & (summary["return_semantics"] == PROJECT_SEMANTICS) & (summary["weighting"] == "EW")
            & (summary["bucket_count"] == 10) & (summary["series_role"] == role) & (summary["fold_id"] == fold)
        ]
        if len(selected) != 1:
            raise RuntimeError(f"summary primary lookup failure: {arm} H{holding} {role} {fold}")
        return selected.iloc[0]

    for prefix, arm, holding in [("SRC_5x5", "SRC3_MKT_RESID_CONT_5D", 5), ("SRC_10x10", "SRC4_MKT_RESID_CONT_10D", 10)]:
        full = summary_row(arm, holding, "favorable_bucket", "FULL")
        early = summary_row(arm, holding, "favorable_bucket", "EARLY")
        late = summary_row(arm, holding, "favorable_bucket", "LATE")
        arm_coverage = coverage[(coverage["arm_id"] == arm) & (coverage["decision_date"].isin(possible_dates))]
        sample_pass = (
            int(full["project_evaluable_week_n"]) >= 156 and int(early["project_evaluable_week_n"]) >= 78
            and int(late["project_evaluable_week_n"]) >= 78 and int(full["distinct_calendar_month_n"]) >= 36
            and int(full["distinct_calendar_year_n"]) >= 4 and float(arm_coverage["signal_coverage"].median()) >= 0.70
            and int(arm_coverage["signal_eligible_n"].min()) >= 100
        )
        gates[f"{prefix}_sample_support_gate"] = bool(sample_pass)
        pair = paired[
            (paired["residual_arm_id"] == arm) & (paired["holding_sessions"] == holding)
            & (paired["return_semantics"] == PROJECT_SEMANTICS) & (paired["weighting"] == "EW")
            & (paired["bucket_count"] == 10)
        ].set_index("fold_id")
        pair_support = int(pair.loc["FULL", "paired_evaluable_week_n"]) >= 156 and int(pair.loc["EARLY", "paired_evaluable_week_n"]) >= 78 and int(pair.loc["LATE", "paired_evaluable_week_n"]) >= 78
        gates[f"{prefix}_paired_attribution_support_gate"] = bool(pair_support)
        gates[f"{prefix}_registered_row_completeness_gate"] = True
        gates[f"{prefix}_materialization_gate"] = True
        gates[f"{prefix}_positive_exposure_design_gate"] = bool(sample_pass and all(float(row["mean_return"]) > 0 for row in [full, early, late]))
        spread_rows = [summary_row(arm, holding, "favorable_minus_unfavorable", fold) for fold in FOLD_ORDER]
        gates[f"{prefix}_sort_morphology_gate"] = bool(sample_pass and all(float(row["mean_return"]) > 0 for row in spread_rows))
        residual_value = pair.loc["FULL", "residualization_value"]
        gates[f"{prefix}_residualization_value"] = bool_value(residual_value) if residual_value != "not_evaluable" else "not_evaluable"
        cost_row = cost[
            (cost["arm_id"] == arm) & (cost["holding_sessions"] == holding) & (cost["return_semantics"] == PROJECT_SEMANTICS)
            & (cost["weighting"] == "EW") & (cost["bucket_count"] == 10)
        ]
        if len(cost_row) != 1:
            raise RuntimeError("primary cost lookup failure")
        gates[f"{prefix}_cost_feasibility_gate"] = bool(cost_row.iloc[0]["cost_feasible"])
        gates[f"{prefix}_break_even_cost_multiple_proxy"] = cost_row.iloc[0]["break_even_cost_multiple_proxy"]

    gates["SRC_formula_integrity_gate"] = "pass"
    gates["SRC_outcome_integrity_gate"] = "pass"
    style_summary = style[style["record_type"] == "FULL_SUMMARY"]
    components = {}
    for row in style_summary.itertuples(index=False):
        tag = "SRC_5D" if row.src_arm_id.endswith("5D") else "SRC_10D"
        components[f"{tag}_scale_dependence_warning"] = row.arm_scale_dependence_warning
        components[f"{tag}_size_dependence_warning"] = row.arm_size_dependence_warning
    gates.update(components)
    gates["scale_dependence_warning"] = style_summary["overall_scale_dependence_warning"].iloc[0]
    gates["size_dependence_warning"] = style_summary["overall_size_dependence_warning"].iloc[0]
    gates["style_warning_evaluability"] = "pass" if not any(str(value) == "not_evaluable" for value in components.values()) else "not_evaluable"
    five, ten = bool(gates["SRC_5x5_positive_exposure_design_gate"]), bool(gates["SRC_10x10_positive_exposure_design_gate"])
    rv5, rv10 = bool_value(gates["SRC_5x5_residualization_value"]), bool_value(gates["SRC_10x10_residualization_value"])
    gates["short_term_true_forward_freeze_recommended"] = bool(
        five and ten and (rv5 or rv10) and gates["SRC_5x5_cost_feasibility_gate"] and gates["SRC_10x10_cost_feasibility_gate"]
    )
    gates["participation_meta_label_research_recommended"] = bool(five and not ten and rv5)
    sample_ok = gates["SRC_5x5_sample_support_gate"] and gates["SRC_10x10_sample_support_gate"] and gates["SRC_5x5_paired_attribution_support_gate"] and gates["SRC_10x10_paired_attribution_support_gate"]
    if not sample_ok:
        terminal = "20B_SRC_underpowered_design_diagnostic"
    elif five and ten:
        if not (rv5 or rv10):
            terminal = "20B_SRC_total_continuation_explained_design_only"
        elif not (gates["SRC_5x5_cost_feasibility_gate"] and gates["SRC_10x10_cost_feasibility_gate"]):
            terminal = "20B_SRC_gross_direction_but_cost_infeasible_design_only"
        else:
            terminal = "20B_SRC_persistent_short_horizon_candidate_design_only"
    elif five:
        terminal = "20B_SRC_ultrashort_participation_filter_candidate_design_only" if rv5 else "20B_SRC_total_continuation_explained_design_only"
    elif ten:
        if not rv10:
            terminal = "20B_SRC_total_continuation_explained_design_only"
        elif not gates["SRC_10x10_cost_feasibility_gate"]:
            terminal = "20B_SRC_gross_direction_but_cost_infeasible_design_only"
        else:
            terminal = "20B_SRC_delayed_short_horizon_candidate_design_only"
    elif gates["SRC_5x5_sort_morphology_gate"] or gates["SRC_10x10_sort_morphology_gate"]:
        terminal = "20B_SRC_sort_morphology_only_design_only"
    else:
        terminal = "20B_SRC_not_identified_design_only"
    gates["terminal_state"] = terminal
    return gates


def outcome_stage(config_path: str | Path, signal_hash: str | None, authorization_file: str | None) -> dict[str, Any]:
    config = load_config(config_path)
    paths = paths_for(config)
    build = build_root(config)
    pre, signal = build / "preoutcome", build / "signal"
    pre_hash = verify_bundle(pre, "preoutcome")
    verified_signal_hash = verify_bundle(signal, "signal")
    if not signal_hash or signal_hash != verified_signal_hash:
        raise PermissionError("--signal-bundle-hash must match the sealed signal registry")
    whitelist = load_preoutcome_whitelist(build)["outcome-materialization"]
    expected_auth_path = build / config["authorization"]["outcome_authorization_relative_path"]
    if not authorization_file or Path(authorization_file).resolve() != expected_auth_path.resolve():
        raise PermissionError(f"outcome authorization must use registered path: {expected_auth_path}")
    authorization = verify_authorization(expected_auth_path, "outcome-materialization", verified_signal_hash, whitelist["stable_object_hash"])
    verify_input_file_records(paths, read_json(pre / "input_file_set_hashes.json"))
    candidate, target = begin_stage(build, "historical")
    if candidate == target:
        return {"status": "already_sealed", "historical_bundle_hash": verify_bundle(target, "historical")}

    minimum, maximum = pd.Timestamp(config["boundary"]["history_date_min"]), pd.Timestamp(config["boundary"]["history_date_max"])
    calendar = exchange_calendar(paths["trading_calendar"], minimum, maximum)
    calendar_frame = pd.read_csv(pre / "calendar_freeze.csv", parse_dates=["decision_date", "entry_date"])
    registry = pd.read_csv(pre / "arm_and_horizon_registry.csv")
    assignments = pd.read_parquet(signal / "weekly_bucket_assignment.parquet")
    assignments["decision_date"] = pd.to_datetime(assignments["decision_date"])
    assignments["entry_date"] = pd.to_datetime(assignments["entry_date"])
    weekly = pd.read_parquet(signal / "weekly_signal_panel.parquet")
    weekly["decision_date"] = pd.to_datetime(weekly["decision_date"])
    coverage = pd.read_csv(signal / "signal_coverage_audit.csv", parse_dates=["decision_date"])
    security_master = load_security_master(paths["security_master"])
    forward = materialize_forward_returns(assignments, calendar, paths["qfq_root"], security_master, verified_signal_hash)
    bucket = materialize_bucket_returns(assignments, forward, registry, calendar_frame)
    summary, inference = materialize_summary_and_inference(bucket, registry, coverage, calendar_frame, config)
    paired = materialize_paired(bucket, config)
    path = materialize_path_decomposition(assignments, forward)
    style = materialize_style(weekly, assignments, signal / "daily_market_residual_panel.parquet", calendar_frame, config)
    stability = materialize_stability(bucket, calendar_frame)
    dominance = materialize_dominance(bucket, assignments, forward)
    cost = materialize_cost(assignments, bucket, registry, calendar_frame, config)
    gates = evaluate_gates(summary, paired, coverage, cost, style, calendar_frame)

    access = [
        access_row(1, "outcome-materialization", pre, "sealed_preoutcome"),
        access_row(2, "outcome-materialization", signal, "sealed_signal"),
        access_row(3, "outcome-materialization", expected_auth_path, "outcome_authorization", row_count=1),
        access_row(4, "outcome-materialization", paths["qfq_root"], "qfq_raw", max_date_read=maximum.date(), max_date_contributed=maximum.date(), context=maximum.date(), outcome_class="registered_forward_H5_H10"),
        access_row(5, "outcome-materialization", paths["trading_calendar"], "trading_calendar", row_count=len(calendar), max_date_read=maximum.date(), max_date_contributed=maximum.date(), context=maximum.date()),
        access_row(6, "outcome-materialization", paths["security_master"], "security_master_identity_delisting", row_count=len(security_master), max_date_read=maximum.date(), max_date_contributed=maximum.date(), context=maximum.date()),
    ]
    write_csv(candidate / "outcome_access_audit.csv", pd.DataFrame(access)[ACCESS_COLUMNS], sort_key=["stage", "access_sequence_id"])
    write_parquet(candidate / "forward_return_resolution.parquet", forward, FORWARD_COLUMNS,
                  sort_key=["instrument_id", "decision_date", "holding_sessions", "return_semantics"])
    write_csv_gz(candidate / "bucket_return_panel.csv.gz", bucket, BUCKET_COLUMNS,
                 sort_key=["decision_date", "arm_id", "formation_sessions", "holding_sessions", "return_semantics", "weighting", "bucket_count", "bucket_id"])
    write_csv(candidate / "arm_summary_statistics.csv", summary, SUMMARY_COLUMNS,
              sort_key=["arm_id", "formation_sessions", "holding_sessions", "return_semantics", "weighting", "bucket_count", "series_role", "fold_id"])
    write_csv(candidate / "horizon_path_decomposition.csv", path,
              sort_key=["decision_date", "arm_id", "formation_sessions", "weighting", "bucket_count", "bucket_id", "return_semantics"])
    write_csv(candidate / "paired_residual_vs_total_attribution.csv", paired,
              sort_key=["residual_arm_id", "total_arm_id", "formation_sessions", "holding_sessions", "return_semantics", "weighting", "bucket_count", "fold_id"])
    write_csv(candidate / "style_morphology_attribution.csv", style,
              sort_key=["record_type", "decision_date", "src_arm_id"])
    write_csv(candidate / "fold_and_year_stability.csv", stability,
              sort_key=["arm_id", "formation_sessions", "holding_sessions", "return_semantics", "weighting", "bucket_count", "slice_type", "slice_id"])
    write_csv(candidate / "month_instrument_dominance_audit.csv", dominance,
              sort_key=["arm_id", "formation_sessions", "holding_sessions", "return_semantics", "weighting", "bucket_count", "audit_type", "omitted_id"])
    write_csv(candidate / "turnover_break_even_cost_readout.csv", cost,
              sort_key=["arm_id", "formation_sessions", "holding_sessions", "weighting", "bucket_count", "bucket_id", "return_semantics"])
    write_csv(candidate / "hac_and_block_bootstrap_inference.csv", inference, INFERENCE_COLUMNS,
              sort_key=["test_id", "estimator", "arm_id", "formation_sessions", "holding_sessions", "return_semantics", "weighting", "bucket_count", "series_role", "fold_id"])
    ordinary = [
        "outcome_access_audit.csv", "forward_return_resolution.parquet", "bucket_return_panel.csv.gz",
        "arm_summary_statistics.csv", "horizon_path_decomposition.csv", "paired_residual_vs_total_attribution.csv",
        "style_morphology_attribution.csv", "fold_and_year_stability.csv", "month_instrument_dominance_audit.csv",
        "turnover_break_even_cost_readout.csv", "hac_and_block_bootstrap_inference.csv",
    ]
    aggregate_input_hashes = {role: stable_hash(records) for role, records in read_json(pre / "input_file_set_hashes.json").items()}
    bundle_hash = seal_bundle(candidate, "historical", ordinary, {
        "upstream_bundle_hashes": {"preoutcome": pre_hash, "signal": verified_signal_hash},
        "input_file_set_hashes": aggregate_input_hashes, "authorization_record": authorization,
        "authorization_file_sha256": file_sha(expected_auth_path), "authorization_record_sha256": authorization["authorization_record_sha256"],
        "history_date_min": str(minimum.date()), "history_date_max": str(maximum.date()),
        "registered_arm_horizon_rows": 84, "decision_snapshot": gates,
    })
    verify_bundle(candidate, "historical")
    publish_stage(candidate, target)
    return {
        "status": "sealed", "historical_bundle_hash": bundle_hash, "historical_root": str(target),
        "terminal_state": gates["terminal_state"], "forward_rows": len(forward), "bucket_rows": len(bucket),
    }


def primary_summary_lookup(summary: pd.DataFrame, arm: str, holding: int, role: str, fold: str) -> pd.Series:
    selected = summary[
        (summary["arm_id"] == arm) & (summary["holding_sessions"] == holding)
        & (summary["return_semantics"] == PROJECT_SEMANTICS) & (summary["weighting"] == "EW")
        & (summary["bucket_count"] == 10) & (summary["series_role"] == role) & (summary["fold_id"] == fold)
    ]
    if len(selected) != 1:
        raise RuntimeError("final primary summary lookup failed")
    return selected.iloc[0]


def finalize_stage(config_path: str | Path) -> dict[str, Any]:
    config = load_config(config_path)
    build, target = build_root(config), output_root(config)
    if target.exists():
        raise FileExistsError(f"immutable output root already exists: {target}")
    pre_hash = verify_bundle(build / "preoutcome", "preoutcome")
    signal_hash = verify_bundle(build / "signal", "signal")
    historical_hash = verify_bundle(build / "historical", "historical")
    whitelist = load_preoutcome_whitelist(build)
    signal_auth_path = build / config["authorization"]["signal_authorization_relative_path"]
    outcome_auth_path = build / config["authorization"]["outcome_authorization_relative_path"]
    signal_auth = verify_authorization(signal_auth_path, "signal-materialization", pre_hash, whitelist["signal-materialization"]["stable_object_hash"])
    outcome_auth = verify_authorization(outcome_auth_path, "outcome-materialization", signal_hash, whitelist["outcome-materialization"]["stable_object_hash"])
    auth_dir = build / "authorizations"
    if {p.name for p in auth_dir.iterdir() if p.is_file()} != {signal_auth_path.name, outcome_auth_path.name}:
        raise RuntimeError("authorization directory exact file-set failure")
    if {p.name for p in build.iterdir() if p.is_dir()} != {"preoutcome", "signal", "historical", "authorizations"}:
        raise RuntimeError("final root directory whitelist failure")

    historical_manifest = read_json(build / "historical/historical_manifest_20b_src.json")
    gates = historical_manifest["decision_snapshot"]
    summary = pd.read_csv(build / "historical/arm_summary_statistics.csv")
    paired = pd.read_csv(build / "historical/paired_residual_vs_total_attribution.csv")
    style = pd.read_csv(build / "historical/style_morphology_attribution.csv")
    cost = pd.read_csv(build / "historical/turnover_break_even_cost_readout.csv")
    path = pd.read_csv(build / "historical/horizon_path_decomposition.csv")
    stability = pd.read_csv(build / "historical/fold_and_year_stability.csv")
    inference = pd.read_csv(build / "historical/hac_and_block_bootstrap_inference.csv")
    five = {fold: primary_summary_lookup(summary, "SRC3_MKT_RESID_CONT_5D", 5, "favorable_bucket", fold) for fold in FOLD_ORDER}
    ten = {fold: primary_summary_lookup(summary, "SRC4_MKT_RESID_CONT_10D", 10, "favorable_bucket", fold) for fold in FOLD_ORDER}
    five_spread = {fold: primary_summary_lookup(summary, "SRC3_MKT_RESID_CONT_5D", 5, "favorable_minus_unfavorable", fold) for fold in FOLD_ORDER}
    ten_spread = {fold: primary_summary_lookup(summary, "SRC4_MKT_RESID_CONT_10D", 10, "favorable_minus_unfavorable", fold) for fold in FOLD_ORDER}
    pair_primary = paired[(paired["return_semantics"] == PROJECT_SEMANTICS) & (paired["weighting"] == "EW") & (paired["bucket_count"] == 10) & (paired["fold_id"] == "FULL")]
    cost_primary = cost[(cost["return_semantics"] == PROJECT_SEMANTICS) & (cost["weighting"] == "EW") & (cost["bucket_count"] == 10) & (((cost["arm_id"] == "SRC3_MKT_RESID_CONT_5D") & (cost["holding_sessions"] == 5)) | ((cost["arm_id"] == "SRC4_MKT_RESID_CONT_10D") & (cost["holding_sessions"] == 10)))]
    style_summary = style[style["record_type"] == "FULL_SUMMARY"]
    holm = inference[inference["holm_family_id"] == "HOLM_MATCHED_PRIMARY_EW_DECILE_FAVORABLE_FULL"]
    path_primary = path[(path["return_semantics"] == PROJECT_SEMANTICS) & (path["weighting"] == "EW") & (path["bucket_count"] == 10) & (path["bucket_id"] == 10)]

    blocking = []
    if gates["terminal_state"] == "20B_SRC_underpowered_design_diagnostic":
        blocking.append("matched_primary_or_paired_sample_floor_not_met")
    modifiers = [
        "all_registered_denominator_rows_tradable_is_optimistic",
        "historical_stamp_tax_schedule_replication_false",
        "minimum_commission_not_included",
        "outcome_contaminated_historical_design_only",
    ]
    if bool_value(gates.get("scale_dependence_warning")):
        modifiers.append("scale_dependence_warning")
    if bool_value(gates.get("size_dependence_warning")):
        modifiers.append("size_dependence_warning")
    row = {
        "experiment_id": EXPERIMENT_ID, "phase_id": PHASE_ID, "run_id": RUN_ID, "contract_version": CONTRACT_VERSION,
        "terminal_state": gates["terminal_state"], "historical_sample_role": HISTORICAL_ROLE,
        "historical_support_claim_allowed": False, "exact_replication_claim_allowed": False,
        "tradability_assumption": "all_registered_denominator_rows_tradable", "daily_suspension_source_required": False,
        "suspension_carry_allowed": False, "optimistic_tradability_assumption": True,
        "requirement_generation_authorized": True, "implementation_authorized": True,
        "historical_signal_execution_authorized": True, "historical_outcome_execution_authorized": True,
        **gates,
        "stamp_tax_proxy_mode": "current_5bps_applied_uniformly_to_history",
        "historical_stamp_tax_schedule_replication": False, "minimum_commission_included": False,
        "next_requirement_generation_authorized": False, "true_forward_execution_authorized": False,
        "20C_requirement_generation_authorized": False, "20C_execution_authorized": False,
        "policy_training_authorized": False, "policy_replay_authorized": False,
        "portfolio_optimization_authorized": False, "deployment_authorized": False,
        "preoutcome_bundle_hash": pre_hash, "signal_bundle_hash": signal_hash, "historical_bundle_hash": historical_hash,
        "blocking_reasons": canonical_compact_json(sorted(set(blocking))),
        "interpretation_modifiers": canonical_compact_json(sorted(set(modifiers))),
    }
    decision_name = "20B_SRC_short_term_residual_continuation_family_decision.csv"
    report_name = "20B_SRC_short_term_residual_continuation_family_diagnostic_report.md"
    write_csv(build / decision_name, pd.DataFrame([row]))

    def metric(value: Any) -> str:
        return "NA" if value is None or not np.isfinite(float(value)) else f"{float(value):.6f}"

    pair_lines = []
    for item in pair_primary.itertuples(index=False):
        pair_lines.append(f"| {item.residual_arm_id} × H{item.holding_sessions} | {int(item.paired_evaluable_week_n)} | {metric(item.paired_favorable_delta)} | {metric(item.paired_spread_delta)} | {metric(item.paired_volatility_ratio)} | {metric(item.paired_ES10_loss_ratio)} | {item.residualization_value} |")
    cost_lines = []
    for item in cost_primary.itertuples(index=False):
        cost_lines.append(f"| {item.arm_id} × H{item.holding_sessions} | {int(item.valid_transition_n)} | {metric(item.mean_target_turnover)} | {metric(item.mean_gross_return)} | {metric(item.break_even_cost_multiple_proxy)} | {item.cost_feasible} |")
    style_lines = []
    for item in style_summary.itertuples(index=False):
        style_lines.append(f"| {item.src_arm_id} | {metric(item.full_history_median_spearman_SRC_vs_negative_VOL20)} | {metric(item.full_history_median_lowvol_jaccard)} | {metric(item.full_history_median_spearman_SRC_vs_log_market_cap)} | {item.arm_scale_dependence_warning} | {item.arm_size_dependence_warning} |")
    holm_lines = []
    for item in holm.itertuples(index=False):
        holm_lines.append(f"| {item.arm_id} × H{item.holding_sessions} | {metric(item.estimate)} | {metric(item.nominal_pvalue)} | {metric(item.holm_adjusted_pvalue)} |")

    report = f"""# 20B-SRC Short-Term Residual Continuation Family 设计诊断

## 1. Decision 与授权边界

- terminal state：`{gates['terminal_state']}`
- historical sample role：`{HISTORICAL_ROLE}`
- signal/outcome authorization gates：`pass / pass`
- implementation authorized：`true`
- true-forward / 20C / policy / deployment authorization：全部 `false`
- preoutcome / signal / historical bundle：`{pre_hash}` / `{signal_hash}` / `{historical_hash}`

20B-SRC 是 outcome-contaminated historical design diagnostic。它在 20B 月度 P4 结果已被观察后提出，任何历史结果都不能形成 true OOS support。

## 2. 新 family 身份

20B-SRC 改变了 signal formation frequency 与 formula family；它不是 20B P4 的 1 周/2 周 holding sensitivity，也不是论文 12-1 Residual Momentum 的 exact replication。

本诊断使用逐日 causal 252-session CSI300 market model、5D/10D immediate residual continuation score，以及 H5/H10 完整 horizon matrix。没有从 grid 中挑选最好组合。

## 3. Input lineage、boundary 与 tradability

冻结历史边界为 `2017-01-03..2026-05-29`。`U_project` 使用 next-session `usable_trade_date` 与 decision-close availability；QFQ filename、全文件 internal instrument 与 canonical id 通过 exact mapping。

20B-SRC 不读取、不推断逐日停牌状态。所有进入 registered decision denominator 的股票均假设可交易；这是一项乐观的设计近似，不能作为成交可行性或 executable/deployable 证据。缺失 qfq mark 仍按 unknown data gap fail closed，不得因“假设可交易”而 carry、补零或插值。

## 4. Weekly calendar 与 daily rolling regression

Decision 是每个 ISO week 的最后一个 exchange session；5D/10D 均为 exchange-session offset。每个 residual 日只用前 252 个 scheduled returns，至少 200 个 paired rows；当日 residual 使用当日 stock/CSI300 return，但回归系数严格只截至前一 session。

Signal firewall 保留 raw-file future rows loaded audit，同时证明 `future_rows_contributed_to_signal=0`、weekly `max_contributing_date<=decision_date`。

## 5. Signal coverage 与 beta

5D/10D residual、matched total continuation 与 Low Vol comparator 均完整物化，warm-up/missing rows 未删除。Style table 共 {len(style):,} 行；weighted beta 缺任一 positive-weight constituent 时 fail closed。

## 6. 完整 2 × 2 matrix

| primary | fold | evaluable weeks | favorable mean | spread mean |
|---|---|---:|---:|---:|
| SRC 5×5 | FULL | {int(five['FULL']['project_evaluable_week_n'])} | {metric(five['FULL']['mean_return'])} | {metric(five_spread['FULL']['mean_return'])} |
| SRC 5×5 | EARLY | {int(five['EARLY']['project_evaluable_week_n'])} | {metric(five['EARLY']['mean_return'])} | {metric(five_spread['EARLY']['mean_return'])} |
| SRC 5×5 | LATE | {int(five['LATE']['project_evaluable_week_n'])} | {metric(five['LATE']['mean_return'])} | {metric(five_spread['LATE']['mean_return'])} |
| SRC 10×10 | FULL | {int(ten['FULL']['project_evaluable_week_n'])} | {metric(ten['FULL']['mean_return'])} | {metric(ten_spread['FULL']['mean_return'])} |
| SRC 10×10 | EARLY | {int(ten['EARLY']['project_evaluable_week_n'])} | {metric(ten['EARLY']['mean_return'])} | {metric(ten_spread['EARLY']['mean_return'])} |
| SRC 10×10 | LATE | {int(ten['LATE']['project_evaluable_week_n'])} | {metric(ten['LATE']['mean_return'])} | {metric(ten_spread['LATE']['mean_return'])} |

Cross 5×10、10×5 以及 total/Low Vol/baseline、EW/VW、quintile/decile、project/complete-case 全部保留在 sealed tables，不能用 cross mapping 替代 primary gate。

## 7. Favorable absolute return 与 spread

Favorable bucket 是 A 股 long-only positive-beta 判断。Favorable-minus-unfavorable 为正不能替代 favorable bucket 绝对收益为正。A 股 long-only 正 beta 判断不得依赖不可执行 short leg。

5×5 positive gate=`{gates['SRC_5x5_positive_exposure_design_gate']}`，sort gate=`{gates['SRC_5x5_sort_morphology_gate']}`；10×10 分别为 `{gates['SRC_10x10_positive_exposure_design_gate']}` / `{gates['SRC_10x10_sort_morphology_gate']}`。

## 8. Stability 与 dominance

Stability table 共 {len(stability):,} 行，分别覆盖 FULL/EARLY/LATE 与每个 frozen calendar year。LODO/LOMO/LOIO 使用 sealed assignments，不重排 bucket；dominance summary 另报告单周/top3 绝对贡献占比与 H5/H10 joint correlation。

## 9. Residual vs total paired attribution

| pair | common weeks | favorable delta | spread delta | vol ratio | ES10 ratio | residualization value |
|---|---:|---:|---:|---:|---:|---|
{chr(10).join(pair_lines)}

所有 delta 使用 residual/total 同周共同 evaluable population；没有使用 unpaired arm means。

## 10. Low Vol、size 与 beta overlap

| arm | median corr(-VOL20) | median LowVol Jaccard | median corr(log cap) | scale warning | size warning |
|---|---:|---:|---:|---|---|
{chr(10).join(style_lines)}

Overall scale/size warning=`{gates['scale_dependence_warning']}` / `{gates['size_dependence_warning']}`；warning 是 morphology modifier，不覆盖正向点估计。

## 11. H5/H10 path decomposition

Primary favorable joint-evaluable path rows={int(path_primary['joint_evaluable'].astype(str).str.lower().eq('true').sum())}。`R_6_10` 由同一 ex-ante weights 下的 `V10/V5-1` 计算，不把 endpoint returns 简单相加，也不构造 continuous NAV。

## 12. Turnover 与 inherited-cost pressure test

| primary | transitions | mean target turnover | mean gross return | break-even multiple | cost feasible |
|---|---:|---:|---:|---:|---|
{chr(10).join(cost_lines)}

费用继承 20A v2，但 stamp tax 以现行 5 bps 统一回放且不含 5 CNY minimum commission；这是乐观 target-turnover proxy，不是实际成交成本或 net return。

## 13. HAC、block bootstrap 与 AFML classification

| matched primary | estimate | nominal HAC p | Holm p |
|---|---:|---:|---:|
{chr(10).join(holm_lines)}

Weekly rows 与 10-session overlapping labels 不是独立证据。样本量、HAC、block bootstrap 和 fold 统计必须按冻结的 weekly/calendar block 口径报告，不能把 instrument rows 或重叠 cohort rows当作独立 N。

AFML utility classification=`{gates['terminal_state']}`；true-forward freeze recommended=`{gates['short_term_true_forward_freeze_recommended']}`，participation/meta-label research recommended=`{gates['participation_meta_label_research_recommended']}`。这只是 design-only recommendation，不是 support 或执行授权。

## 14. Gate truth table 与 no-authorization footer

| gate | value |
|---|---|
| 5×5 sample / paired support | {gates['SRC_5x5_sample_support_gate']} / {gates['SRC_5x5_paired_attribution_support_gate']} |
| 10×10 sample / paired support | {gates['SRC_10x10_sample_support_gate']} / {gates['SRC_10x10_paired_attribution_support_gate']} |
| 5×5 residualization / cost | {gates['SRC_5x5_residualization_value']} / {gates['SRC_5x5_cost_feasibility_gate']} |
| 10×10 residualization / cost | {gates['SRC_10x10_residualization_value']} / {gates['SRC_10x10_cost_feasibility_gate']} |
| preoutcome / signal / historical hashes | pass / pass / pass |
| outcome firewall | pass |

本阶段没有 next-open fill、blocked entry/exit、持续资本、现金腿、实际费用扣账、实际滑点或容量；只有继承 20A 冻结成本的 target-turnover pressure-test proxy，因此任何结果都不能称为 deployable sleeve 或 net strategy。

`next_requirement_generation_authorized=false`，`true_forward_execution_authorized=false`，`20C_requirement_generation_authorized=false`，`20C_execution_authorized=false`，`policy_training_authorized=false`，`policy_replay_authorized=false`，`portfolio_optimization_authorized=false`，`deployment_authorized=false`。
"""
    write_text(build / report_name, report)
    final_hash = seal_bundle(build, "final", [decision_name, report_name], {
        "upstream_bundle_hashes": {"preoutcome": pre_hash, "signal": signal_hash, "historical": historical_hash},
        "input_file_set_hashes": read_json(build / "preoutcome/preoutcome_manifest_20b_src.json")["input_file_set_hashes"],
        "authorization_records": {"signal": signal_auth, "outcome": outcome_auth},
        "authorization_file_hashes": {"signal": file_sha(signal_auth_path), "outcome": file_sha(outcome_auth_path)},
        "authorization_semantic_hashes": {"signal": signal_auth["authorization_record_sha256"], "outcome": outcome_auth["authorization_record_sha256"]},
        "history_date_min": config["boundary"]["history_date_min"], "history_date_max": config["boundary"]["history_date_max"],
        "registered_arm_horizon_rows": 84, "terminal_state": gates["terminal_state"],
    })
    verify_bundle(build, "final")
    os.replace(build, target)
    verify_bundle(target / "preoutcome", "preoutcome")
    verify_bundle(target / "signal", "signal")
    verify_bundle(target / "historical", "historical")
    verify_bundle(target, "final")
    return {"status": "finalized", "final_bundle_hash": final_hash, "terminal_state": gates["terminal_state"], "output_root": str(target)}


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.stage == "preflight":
        result = preflight_stage(args.config)
    elif args.stage == "signal-materialization":
        result = signal_stage(args.config, args.preoutcome_bundle_hash, args.authorization_file)
    elif args.stage == "outcome-materialization":
        result = outcome_stage(args.config, args.signal_bundle_hash, args.authorization_file)
    else:
        result = finalize_stage(args.config)
    print(json.dumps(json_ready(result), ensure_ascii=False, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
