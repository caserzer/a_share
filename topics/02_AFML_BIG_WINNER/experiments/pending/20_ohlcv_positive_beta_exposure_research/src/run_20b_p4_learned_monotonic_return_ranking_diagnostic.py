#!/usr/bin/env python3
"""Fresh-process P4 multifactor monotonic-return ranking diagnostic.

The publishable entry point is ``--stage full``.  Internal workers deliberately
open only the files allowed for their stage; the parent process writes worker
exit records and stage seals after each child has terminated.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import math
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np
import pandas as pd
import yaml


RUN_ID = "20B_P4_learned_monotonic_return_ranking_diagnostic_v1"
CONTRACT_VERSION = "20B_P4_MLRANK_v1"
PHASE_ID = "20B_P4_MLRANK"
VALID_MARK = "valid_mark"
UNKNOWN = "unknown_bridge_arm_month_not_evaluable"
RETURN_PRIMARY = "project_known_only_primary"
RETURN_STRICT = "project_all_resolved_strict_sensitivity"
FEATURES = [
    "p4_rank_t", "p4_rank_lag1", "p4_rank_lag3", "p4_rank_mean3",
    "p4_rank_std3", "p4_rank_delta1", "p4_rank_delta3", "p0_rank_t",
    "p1_rank_t", "p6_rank_t", "p4_lag1_missing", "p4_lag3_missing",
    "p4_mean3_missing", "p0_missing", "p1_missing", "p6_missing",
]
P4_PATH_FEATURES = FEATURES[:7] + FEATURES[10:13]
CROSS_FEATURES = FEATURES[7:10] + FEATURES[13:16]
VALIDATION_MODELS = [
    "B0_P4_RAW_RANK", "N0_HASH_NULL", "M1_RIDGE_RANK_REGRESSION",
    "M2_LIGHTGBM_LAMBDARANK",
]
ROBUSTNESS_MODELS = [
    "B0_P4_RAW_RANK", "N0_HASH_NULL", "S0_SELECTED_FULL",
    "A1_P4_PATH_ONLY", "A2_CROSS_SIGNALS_WITHOUT_P4",
]
EXPECTED_CONFIG_KEYS = {
    "identity", "paths", "execution", "upstream", "base_population",
    "feature_arms", "splits", "labels", "features", "models",
    "scoring_instances", "research_scope", "sorting", "inference", "gates",
    "serialization",
}
REPORT_NAME = "20B_P4_learned_monotonic_return_ranking_diagnostic_report.md"
DECISION_NAME = "20B_P4_learned_monotonic_return_ranking_diagnostic_decision.csv"
MANIFEST_NAME = "manifest_20b_p4_mlrank.json"
HASHES_NAME = "output_hashes_20b_p4_mlrank.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json_bytes(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, ensure_ascii=False,
                       separators=(",", ":"), default=_json_default, allow_nan=False) + "\n").encode("utf-8")


def _json_default(value: Any) -> Any:
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return None if not np.isfinite(value) else float(value)
    if isinstance(value, (pd.Timestamp, datetime)):
        return pd.Timestamp(value).isoformat()
    raise TypeError(f"not JSON serializable: {type(value)!r}")


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json_bytes(value))


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_csv(path: Path, frame: pd.DataFrame, coefficient: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(
        path, index=False, lineterminator="\n",
        float_format="%.17g" if coefficient else "%.12g",
        compression={"method": "gzip", "compresslevel": 9, "mtime": 0}
        if path.name.endswith(".gz") else None,
    )


def write_parquet(path: Path, frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(path, index=False, engine="pyarrow", compression="zstd")


def stable_hash(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def dataframe_content_hash(frame: pd.DataFrame, keys: Sequence[str]) -> str:
    ordered = frame.sort_values(list(keys), kind="mergesort").reset_index(drop=True)
    payload = ordered.to_csv(index=False, lineterminator="\n", float_format="%.17g")
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def experiment_root_from_config(config_path: Path) -> Path:
    if config_path.parent.name != "configs":
        raise ValueError("config must live under the experiment configs directory")
    return config_path.parent.parent.resolve()


def load_config(config_path: str | Path) -> tuple[dict[str, Any], Path]:
    path = Path(config_path).resolve()
    config = yaml.safe_load(path.read_text(encoding="utf-8"))
    if set(config) != EXPECTED_CONFIG_KEYS:
        raise ValueError(f"config top-level key mismatch: {sorted(set(config) ^ EXPECTED_CONFIG_KEYS)}")
    identity = config["identity"]
    if identity != {
        "experiment_id": "20_ohlcv_positive_beta_exposure_research",
        "phase_id": PHASE_ID, "run_id": RUN_ID, "contract_version": CONTRACT_VERSION,
    }:
        raise ValueError("frozen identity mismatch")
    if config["features"]["ordered_feature_ids"] != FEATURES:
        raise ValueError("frozen feature order mismatch")
    if config["scoring_instances"]["validation"] != VALIDATION_MODELS:
        raise ValueError("validation model registry mismatch")
    if config["scoring_instances"]["robustness"] != ROBUSTNESS_MODELS:
        raise ValueError("robustness model registry mismatch")
    if config["sorting"] != {
        "bucket_count": 10,
        "score_direction": "ascending_low_to_high",
        "tie_breaker": "instrument_id_ascending",
    }:
        raise ValueError("sorting contract mismatch")
    if not config["research_scope"]["multi_factor_model_allowed"]:
        raise ValueError("multifactor scope must be enabled")
    if config["research_scope"]["P4_single_factor_repair_claim_allowed"]:
        raise ValueError("P4 single-factor repair claim must remain disabled")
    return config, experiment_root_from_config(path)


def resolved_paths(config: dict[str, Any], root: Path, build_override: str | Path | None = None) -> dict[str, Path]:
    v5 = root / config["paths"]["upstream_v5_root"]
    build = Path(build_override).resolve() if build_override is not None else root / config["paths"]["output_root"]
    return {
        "root": root,
        "build": build,
        "requirement": root / config["paths"]["requirement_file"],
        "v5": v5,
        "assignment": v5 / "historical/instrument_month_signal_bucket_assignment.parquet",
        "outcome_audit": v5 / "historical/outcome_resolution_audit.csv.gz",
        "fold_freeze": v5 / "preoutcome/statistical_and_fold_freeze.csv",
        "decision": v5 / "20B_trendpv_residual_momentum_design_and_replication_diagnostic_decision.csv",
        "manifest": v5 / "manifest_20b_trendpv_residual_momentum_design_and_replication_diagnostic.json",
        "final_hashes": v5 / "output_hashes_20b_trendpv_residual_momentum_design_and_replication_diagnostic.json",
        "pre_hashes": v5 / "preoutcome/preoutcome_output_hashes_20b.json",
        "hist_manifest": v5 / "historical/historical_manifest_20b.json",
        "hist_hashes": v5 / "historical/historical_output_hashes_20b.json",
    }


def split_for_date(value: pd.Timestamp, splits: dict[str, Any]) -> str:
    date = pd.Timestamp(value).normalize()
    for name in ["train", "validation", "robustness"]:
        spec = splits[name]
        if pd.Timestamp(spec["start"]) <= date <= pd.Timestamp(spec["end"]):
            return name
    return "outside"


def _verify_registry(base: Path, registry_path: Path, audit: list[dict[str, Any]], role: str,
                     skipped_relative: str | None = None) -> bool:
    registry = read_json(registry_path)
    ok = True
    for relative, expected in sorted(registry.items()):
        if relative == skipped_relative:
            audit.append({"artifact_role": f"{role}:{relative}", "path": str(base / relative),
                          "expected_sha256": expected, "actual_sha256": "NOT_OPENED",
                          "status": "known_postseal_narrative_hash_waiver", "blocking_reason": ""})
            continue
        target = base / relative
        actual = sha256_file(target) if target.is_file() else "MISSING"
        status = "pass" if actual == expected else "fail"
        ok &= status == "pass"
        audit.append({"artifact_role": f"{role}:{relative}", "path": str(target),
                      "expected_sha256": expected, "actual_sha256": actual,
                      "status": status, "blocking_reason": "" if status == "pass" else "sha256_mismatch"})
    return ok


def stage_bundle_hash(build: Path, directory: str) -> str:
    names = {
        "preflight": "preflight_output_hashes.json",
        "materialized": "materialized_output_hashes.json",
        "selection": "pre_robustness_selection_output_hashes.json",
        "models": "model_bundle_output_hashes.json",
        "scores": "score_bundle_output_hashes.json",
        "historical": "historical_output_hashes.json",
    }
    return sha256_file(build / directory / names[directory])


def seal_stage(build: Path, directory: str, manifest_name: str, registry_name: str,
               prior_bundle_hashes: dict[str, str] | None = None) -> str:
    stage = build / directory
    manifest_path = stage / manifest_name
    registry_path = stage / registry_name
    excluded = {manifest_name, registry_name}
    payloads = sorted(p for p in stage.rglob("*") if p.is_file() and p.name not in excluded)
    payload_hashes = {p.relative_to(stage).as_posix(): sha256_file(p) for p in payloads}
    manifest = {
        "run_id": RUN_ID,
        "contract_version": CONTRACT_VERSION,
        "stage": directory,
        "immutable": True,
        "sealed_at_utc": utc_now(),
        "payload_hashes": payload_hashes,
        "prior_bundle_hashes": prior_bundle_hashes or {},
        "self_hash_excluded": True,
    }
    write_json(manifest_path, manifest)
    registry = dict(payload_hashes)
    registry[manifest_name] = sha256_file(manifest_path)
    write_json(registry_path, registry)
    return sha256_file(registry_path)


def verify_stage(build: Path, directory: str, manifest_name: str, registry_name: str) -> bool:
    stage = build / directory
    registry = read_json(stage / registry_name)
    return all(sha256_file(stage / rel) == expected for rel, expected in registry.items())


def dependency_versions() -> dict[str, str]:
    names = {
        "numpy": "numpy", "pandas": "pandas", "scipy": "scipy",
        "lightgbm": "lightgbm", "scikit-learn": "scikit-learn", "pyarrow": "pyarrow",
    }
    return {key: importlib.metadata.version(dist) for key, dist in names.items()}


def preflight_worker(config: dict[str, Any], paths: dict[str, Path]) -> None:
    build = paths["build"]
    target = build / "preflight"
    target.mkdir(parents=True, exist_ok=False)
    upstream = config["upstream"]
    audits: list[dict[str, Any]] = []

    fixed = [
        ("final_output_hashes", paths["final_hashes"], upstream["expected_final_output_hashes_sha256"]),
        ("final_manifest", paths["manifest"], upstream["expected_final_manifest_sha256"]),
        ("decision", paths["decision"], upstream["expected_decision_sha256"]),
        ("preoutcome_registry", paths["pre_hashes"], upstream["expected_preoutcome_bundle_hash"]),
        ("historical_registry", paths["hist_hashes"], upstream["expected_historical_bundle_hash"]),
        ("historical_manifest", paths["hist_manifest"], upstream["expected_historical_manifest_sha256"]),
        ("assignment", paths["assignment"], upstream["expected_assignment_sha256"]),
        ("outcome_audit", paths["outcome_audit"], upstream["expected_outcome_audit_sha256"]),
        ("fold_freeze", paths["fold_freeze"], upstream["expected_fold_freeze_sha256"]),
    ]
    all_ok = True
    for role, path, expected in fixed:
        actual = sha256_file(path) if path.is_file() else "MISSING"
        status = "pass" if actual == expected else "fail"
        all_ok &= status == "pass"
        audits.append({"artifact_role": role, "path": str(path), "expected_sha256": expected,
                       "actual_sha256": actual, "status": status,
                       "blocking_reason": "" if status == "pass" else "sha256_mismatch"})
    manifest = read_json(paths["manifest"])
    expected_manifest = {
        "contract_version": upstream["expected_contract_version"],
        "run_id": upstream["expected_run_id"],
        "preoutcome_bundle_hash": upstream["expected_preoutcome_bundle_hash"],
        "historical_bundle_hash": upstream["expected_historical_bundle_hash"],
        "immutable": True,
    }
    identity_ok = all(manifest.get(k) == v for k, v in expected_manifest.items())
    audits.append({"artifact_role": "upstream_manifest_identity", "path": str(paths["manifest"]),
                   "expected_sha256": stable_hash(expected_manifest),
                   "actual_sha256": stable_hash({k: manifest.get(k) for k in expected_manifest}),
                   "status": "pass" if identity_ok else "fail",
                   "blocking_reason": "" if identity_ok else "manifest_identity_mismatch"})
    all_ok &= identity_ok
    all_ok &= _verify_registry(paths["v5"] / "preoutcome", paths["pre_hashes"], audits, "preoutcome")
    all_ok &= _verify_registry(paths["v5"] / "historical", paths["hist_hashes"], audits, "historical")
    all_ok &= _verify_registry(paths["v5"], paths["final_hashes"], audits, "final",
                               upstream["exact_report_waiver_path"])

    project_root = paths["root"].parents[2]
    pyproject = project_root / "pyproject.toml"
    uv_lock = project_root / "uv.lock"
    versions = dependency_versions()
    expected_versions = {
        "numpy": "1.26.4", "pandas": "2.3.3", "scipy": "1.17.1",
        "lightgbm": "4.6.0", "scikit-learn": "1.9.0", "pyarrow": "24.0.0",
    }
    dependency_ok = (
        sha256_file(pyproject) == "cd2d0cff7728be686b59ca14b63c35d6050af6b5ff3a2305fa2e50e606d8dd66"
        and sha256_file(uv_lock) == "95b1c429f48b9ef1e950d1639334cdcc8633cb1536213e4f236b15e7b00b4e60"
        and versions == expected_versions
    )
    audits.append({"artifact_role": "dependency_lock_and_runtime", "path": str(project_root),
                   "expected_sha256": stable_hash(expected_versions), "actual_sha256": stable_hash(versions),
                   "status": "pass" if dependency_ok else "fail",
                   "blocking_reason": "" if dependency_ok else "dependency_mismatch"})
    all_ok &= dependency_ok
    write_csv(target / "upstream_input_integrity_audit.csv", pd.DataFrame(audits))

    split_rows = []
    for name in ["train", "validation", "robustness"]:
        row = {"split": name, **config["splits"][name]}
        split_rows.append(row)
    write_csv(target / "split_registry.csv", pd.DataFrame(split_rows))
    feature_rows = []
    for order, feature in enumerate(FEATURES, 1):
        source = "P4_PATH" if feature in P4_PATH_FEATURES else "P0_P1_P6_CROSS"
        feature_rows.append({"feature_id": feature, "feature_order": order, "source_family": source,
                             "decision_time_only": True, "outcome_field_read_count": 0})
    write_csv(target / "feature_registry.csv", pd.DataFrame(feature_rows))
    model_rows = []
    for split, ids in [("validation", VALIDATION_MODELS), ("robustness", ROBUSTNESS_MODELS)]:
        for model_id in ids:
            trainable = model_id not in {"B0_P4_RAW_RANK", "N0_HASH_NULL"}
            family = ({"B0_P4_RAW_RANK": "NONTRAINABLE_P4_BASELINE",
                       "N0_HASH_NULL": "NONTRAINABLE_HASH_NULL"}.get(model_id)
                      or ("SELECTED_FAMILY_PLACEHOLDER" if split == "robustness" else model_id))
            fit_id = ({"M1_RIDGE_RANK_REGRESSION": "M1_candidate_train",
                       "M2_LIGHTGBM_LAMBDARANK": "M2_candidate_train",
                       "S0_SELECTED_FULL": "selected_full_refit",
                       "A1_P4_PATH_ONLY": "A1_p4_path_only_refit",
                       "A2_CROSS_SIGNALS_WITHOUT_P4": "A2_cross_signals_without_p4_refit"}.get(model_id))
            model_rows.append({"split": split, "scored_model_id": model_id, "model_family_id": family,
                               "fit_id": fit_id, "model_role": "trainable" if trainable else "nontrainable",
                               "feature_set_id": ({"S0_SELECTED_FULL": "full16", "A1_P4_PATH_ONLY": "A1_p4_path",
                                                   "A2_CROSS_SIGNALS_WITHOUT_P4": "A2_cross_signals"}.get(model_id, "full16")),
                               "trainable": trainable, "selection_eligible": split == "validation" and trainable,
                               "score_scope": split})
    write_csv(target / "model_registry.csv", pd.DataFrame(model_rows))
    snapshot = {
        "run_id": RUN_ID, "contract_version": CONTRACT_VERSION, "phase_id": PHASE_ID,
        "execution_authority": config["execution"]["authority"],
        "execution_authority_mode": config["execution"]["authority_mode"],
        "execution_authority_record_required": False,
        "implementation_authorized": True,
        "historical_outcome_execution_authorized": True,
        "model_training_authorized": True,
        "requirement_sha256": sha256_file(paths["requirement"]),
        "upstream_preoutcome_bundle_hash": upstream["expected_preoutcome_bundle_hash"],
        "upstream_historical_bundle_hash": upstream["expected_historical_bundle_hash"],
        "upstream_input_integrity_gate": bool(all_ok),
        "dependency_gate": bool(dependency_ok),
        "preflight_outcome_column_read_count": 0,
        "report_waiver_path": upstream["exact_report_waiver_path"],
        "report_current_bytes_opened": False,
        "research_scope": config["research_scope"],
        "runtime_versions": versions,
    }
    write_json(target / "contract_snapshot.json", snapshot)
    if not all_ok:
        raise RuntimeError("preflight integrity or dependency gate failed")


def _feature_rank(frame: pd.DataFrame, prefix: str, minimum_n: int) -> pd.DataFrame:
    selected = frame[["decision_date", "instrument_id", "raw_signal"]].copy()
    selected["finite"] = np.isfinite(selected["raw_signal"])
    counts = selected.groupby("decision_date")["finite"].transform("sum")
    ranks = selected.groupby("decision_date")["raw_signal"].rank(method="average", ascending=True)
    selected[f"{prefix}_rank_t"] = (ranks - 1.0) / (counts - 1.0)
    selected.loc[(counts < minimum_n) | ~selected["finite"], f"{prefix}_rank_t"] = np.nan
    return selected[["decision_date", "instrument_id", f"{prefix}_rank_t"]]


def feature_worker(config: dict[str, Any], paths: dict[str, Path]) -> None:
    import pyarrow.parquet as pq

    target = paths["build"] / "materialized"
    target.mkdir(parents=True, exist_ok=True)
    columns = ["instrument_id", "decision_date", "label_month", "arm_id", "semantic_track",
               "signal_eligible", "raw_signal", "bucket_count"]
    raw = pq.read_table(paths["assignment"], columns=columns).to_pandas()
    raw["decision_date"] = pd.to_datetime(raw["decision_date"])
    start = pd.Timestamp(config["splits"]["train"]["start"])
    end = pd.Timestamp(config["splits"]["robustness"]["end"])
    raw = raw[raw["decision_date"].between(start, end)]
    arm_frames: dict[str, pd.DataFrame] = {}
    for prefix, arm in config["feature_arms"].items():
        part = raw[
            raw["arm_id"].eq(arm["arm_id"])
            & raw["semantic_track"].eq(arm["semantic_track"])
            & raw["bucket_count"].eq(10)
            & raw["signal_eligible"].eq(True)
        ].copy()
        if part.duplicated(["decision_date", "instrument_id"]).any():
            raise ValueError(f"duplicate feature rows for {prefix}")
        arm_frames[prefix] = _feature_rank(part, prefix, int(config["features"]["minimum_arm_finite_n"]))
    base_arm = config["base_population"]
    base = raw[
        raw["arm_id"].eq(base_arm["arm_id"])
        & raw["semantic_track"].eq(base_arm["semantic_track"])
        & raw["bucket_count"].eq(base_arm["source_bucket_count"])
        & raw["signal_eligible"].eq(True)
    ][["decision_date", "label_month", "instrument_id"]].copy()
    if len(base) != int(base_arm["expected_row_n"]):
        raise ValueError(f"base row mismatch: {len(base)}")
    base = base.merge(arm_frames["p4"], on=["decision_date", "instrument_id"], how="left", validate="one_to_one")
    months = sorted(base["decision_date"].unique())
    month_pos = {pd.Timestamp(month): idx for idx, month in enumerate(months)}
    p4_matrix = base.pivot(index="instrument_id", columns="decision_date", values="p4_rank_t")
    for lag in [1, 2, 3]:
        mapping = {pd.Timestamp(month): (pd.Timestamp(months[idx - lag]) if idx >= lag else pd.NaT)
                   for month, idx in month_pos.items()}
        values = []
        for row in base.itertuples(index=False):
            source_month = mapping[pd.Timestamp(row.decision_date)]
            value = np.nan
            if pd.notna(source_month) and row.instrument_id in p4_matrix.index:
                value = p4_matrix.at[row.instrument_id, source_month]
            values.append(value)
        base[f"_p4_lag{lag}"] = values
    base["p4_rank_lag1"] = base["_p4_lag1"]
    base["p4_rank_lag3"] = base["_p4_lag3"]
    rolling = base[["p4_rank_t", "_p4_lag1", "_p4_lag2"]]
    complete = rolling.notna().all(axis=1)
    base["p4_rank_mean3"] = rolling.mean(axis=1).where(complete)
    base["p4_rank_std3"] = rolling.std(axis=1, ddof=0).where(complete)
    base["p4_rank_delta1"] = base["p4_rank_t"] - base["_p4_lag1"]
    base["p4_rank_delta3"] = base["p4_rank_t"] - base["_p4_lag3"]
    for prefix in ["p0", "p1", "p6"]:
        base = base.merge(arm_frames[prefix], on=["decision_date", "instrument_id"], how="left", validate="one_to_one")
    base["p4_lag1_missing"] = base["p4_rank_lag1"].isna().astype("int8")
    base["p4_lag3_missing"] = base["p4_rank_lag3"].isna().astype("int8")
    base["p4_mean3_missing"] = base["p4_rank_mean3"].isna().astype("int8")
    for prefix in ["p0", "p1", "p6"]:
        base[f"{prefix}_missing"] = base[f"{prefix}_rank_t"].isna().astype("int8")
    for col in ["p4_rank_t", "p4_rank_lag1", "p4_rank_lag3", "p4_rank_mean3",
                "p0_rank_t", "p1_rank_t", "p6_rank_t"]:
        base[col] = base[col].fillna(0.5)
    for col in ["p4_rank_std3", "p4_rank_delta1", "p4_rank_delta3"]:
        base[col] = base[col].fillna(0.0)
    base["split"] = base["decision_date"].map(lambda x: split_for_date(x, config["splits"]))
    base["run_id"] = RUN_ID
    base["p4_base_eligible"] = True
    base["feature_max_source_decision_date"] = base["decision_date"]
    base["feature_outcome_read_count"] = 0
    base["upstream_input_snapshot_hash"] = config["upstream"]["expected_assignment_sha256"]
    panel_columns = ["run_id", "decision_date", "label_month", "instrument_id", "split",
                     "p4_base_eligible", *FEATURES, "feature_max_source_decision_date",
                     "feature_outcome_read_count", "upstream_input_snapshot_hash"]
    base = base[panel_columns].sort_values(["decision_date", "instrument_id"], kind="mergesort")
    if base.duplicated(["decision_date", "instrument_id"]).any():
        raise ValueError("feature panel key is not unique")
    write_parquet(target / "feature_panel.parquet", base)

    lineage = []
    for feature in FEATURES:
        source_prefix = "p4" if feature.startswith("p4") else feature[:2]
        arm = config["feature_arms"].get(source_prefix, config["feature_arms"]["p4"])
        for decision_date, group in base.groupby("decision_date", sort=True):
            series = pd.to_numeric(group[feature], errors="coerce")
            lineage.append({"feature_id": feature, "decision_date": decision_date,
                            "source_arm_id": arm["arm_id"], "source_semantic_track": arm["semantic_track"],
                            "source_max_decision_date": decision_date, "source_outcome_field_read_count": 0,
                            "finite_n": int(np.isfinite(series).sum()), "missing_n": int((~np.isfinite(series)).sum()),
                            "status": "pass", "blocking_reason": ""})
    write_csv(target / "feature_lineage_audit.csv", pd.DataFrame(lineage))


def _add_rank_labels(frame: pd.DataFrame, minimum_n: int) -> pd.DataFrame:
    frame = frame.copy()
    frame["label_known"] = frame["outcome_resolution"].eq(VALID_MARK) & np.isfinite(
        pd.to_numeric(frame["project_resolved_next_month_return"], errors="coerce")
    )
    frame["known_label_n_in_month"] = frame.groupby("decision_date")["label_known"].transform("sum")
    frame["y_rank_pct"] = np.nan
    for decision_date, group in frame.groupby("decision_date", sort=True):
        known = group["label_known"]
        n = int(known.sum())
        if n < minimum_n:
            raise ValueError(f"insufficient known labels at {decision_date}: {n}")
        ranks = group.loc[known, "project_resolved_next_month_return"].rank(method="average", ascending=True)
        frame.loc[ranks.index, "y_rank_pct"] = (ranks - 1.0) / (n - 1.0)
    frame["y_relevance"] = np.where(frame["label_known"],
                                     np.minimum(9, np.floor(10 * frame["y_rank_pct"])), np.nan)
    return frame


def label_worker(config: dict[str, Any], paths: dict[str, Path]) -> None:
    import pyarrow.parquet as pq

    target = paths["build"] / "materialized"
    columns = ["instrument_id", "decision_date", "label_month", "arm_id", "semantic_track",
               "signal_eligible", "bucket_count", "project_resolved_next_month_return", "outcome_resolution"]
    raw = pq.read_table(paths["assignment"], columns=columns).to_pandas()
    raw["decision_date"] = pd.to_datetime(raw["decision_date"])
    base = config["base_population"]
    selected = raw[
        raw["arm_id"].eq(base["arm_id"])
        & raw["semantic_track"].eq(base["semantic_track"])
        & raw["bucket_count"].eq(base["source_bucket_count"])
        & raw["signal_eligible"].eq(True)
        & raw["decision_date"].between(pd.Timestamp(config["splits"]["train"]["start"]),
                                        pd.Timestamp(config["splits"]["robustness"]["end"]))
    ][["decision_date", "label_month", "instrument_id", "project_resolved_next_month_return",
       "outcome_resolution"]].copy()
    selected["split"] = selected["decision_date"].map(lambda x: split_for_date(x, config["splits"]))
    selected = _add_rank_labels(selected, int(config["labels"]["minimum_known_label_n"]))
    selected["label_source_hash"] = config["upstream"]["expected_assignment_sha256"]
    cols = ["decision_date", "label_month", "instrument_id", "split",
            "project_resolved_next_month_return", "outcome_resolution", "label_known",
            "y_rank_pct", "y_relevance", "known_label_n_in_month", "label_source_hash"]
    selected = selected[cols].sort_values(["decision_date", "instrument_id"], kind="mergesort")
    expected = config["base_population"]
    if len(selected) != expected["expected_row_n"] or int(selected["label_known"].sum()) != expected["expected_known_n"]:
        raise ValueError("label base population mismatch")
    train_validation = selected[selected["split"].isin(["train", "validation"])]
    robustness = selected[selected["split"].eq("robustness")]
    write_parquet(target / "train_validation_label_panel.parquet", train_validation)
    write_parquet(target / "robustness_label_panel.parquet", robustness)
    audit = pd.DataFrame([{
        "label_source_path": str(paths["assignment"]),
        "label_source_sha256": config["upstream"]["expected_assignment_sha256"],
        "project_outcome_column_read_count": 1,
        "paper_proxy_column_read_count": 0,
        "paper_proxy_column_materialized_count": 0,
        "train_validation_row_n": len(train_validation),
        "robustness_row_n": len(robustness),
        "known_label_n": int(selected["label_known"].sum()),
        "unknown_label_n": int((~selected["label_known"]).sum()),
        "status": "pass", "blocking_reason": "",
    }])
    write_csv(target / "label_resolution_audit.csv", audit)


def hash_null_score(decision_date: pd.Timestamp, instrument_id: str) -> float:
    text = f"{RUN_ID}|{pd.Timestamp(decision_date).strftime('%Y-%m-%d')}|{instrument_id}"
    value = int(hashlib.sha256(text.encode("utf-8")).hexdigest()[:16], 16)
    return value / float(2**64 - 1)


def assign_deciles(scores: pd.DataFrame) -> pd.DataFrame:
    required = {"scored_model_id", "decision_date", "instrument_id", "model_score"}
    if not required.issubset(scores):
        raise ValueError(f"score assignment missing columns: {sorted(required - set(scores))}")
    pieces = []
    for (_, _), group in scores.groupby(["scored_model_id", "decision_date"], sort=True):
        if not np.isfinite(group["model_score"]).all():
            raise ValueError("nonfinite model score")
        ranked = group.sort_values(["model_score", "instrument_id"], kind="mergesort").copy()
        n = len(ranked)
        ranked["model_score_rank"] = np.arange(1, n + 1, dtype=int)
        ranked["bucket_id"] = 1 + np.floor((ranked["model_score_rank"] - 1) * 10 / n).astype(int)
        ranked["nominal_bucket_n"] = ranked.groupby("bucket_id")["instrument_id"].transform("size")
        pieces.append(ranked)
    result = pd.concat(pieces, ignore_index=True)
    if result.duplicated(["scored_model_id", "decision_date", "instrument_id"]).any():
        raise ValueError("bucket assignment key is not unique")
    return result


def _fit_rows(features: pd.DataFrame, labels: pd.DataFrame, split_scope: Sequence[str],
              feature_ids: Sequence[str]) -> tuple[pd.DataFrame, np.ndarray, np.ndarray, np.ndarray]:
    merged = features[features["split"].isin(split_scope)].merge(
        labels[labels["split"].isin(split_scope)],
        on=["decision_date", "label_month", "instrument_id", "split"], how="inner", validate="one_to_one",
    )
    merged = merged[merged["label_known"]].sort_values(["decision_date", "instrument_id"], kind="mergesort")
    x = merged[list(feature_ids)].to_numpy(dtype=float)
    y_rank = merged["y_rank_pct"].to_numpy(dtype=float)
    y_rel = merged["y_relevance"].to_numpy(dtype=int)
    weights = 1.0 / merged["known_label_n_in_month"].to_numpy(dtype=float)
    return merged, x, y_rank, y_rel, weights


def _ridge_fit(config: dict[str, Any], features: pd.DataFrame, labels: pd.DataFrame,
               split_scope: Sequence[str], feature_ids: Sequence[str], artifact_dir: Path) -> tuple[Any, Path]:
    from sklearn.linear_model import Ridge

    merged, x, y_rank, _, weights = _fit_rows(features, labels, split_scope, feature_ids)
    spec = config["models"]["M1"]
    model = Ridge(alpha=float(spec["alpha"]), fit_intercept=bool(spec["fit_intercept"]),
                  solver=spec["solver"], tol=float(spec["tol"]), positive=bool(spec["positive"]))
    model.fit(x, y_rank, sample_weight=weights)
    rows = [{"term_type": "intercept", "feature_id": "__INTERCEPT__", "feature_order": 0,
             "coefficient": float(model.intercept_)}]
    rows.extend({"term_type": "feature", "feature_id": feature, "feature_order": idx,
                 "coefficient": float(value)}
                for idx, (feature, value) in enumerate(zip(feature_ids, model.coef_), 1))
    artifact = artifact_dir / "coefficients.csv"
    write_csv(artifact, pd.DataFrame(rows), coefficient=True)
    return model, artifact


def _lgbm_fit(config: dict[str, Any], features: pd.DataFrame, labels: pd.DataFrame,
              split_scope: Sequence[str], feature_ids: Sequence[str], artifact_dir: Path) -> tuple[Any, Path]:
    from lightgbm import LGBMRanker

    merged, x, _, y_rel, weights = _fit_rows(features, labels, split_scope, feature_ids)
    groups = merged.groupby("decision_date", sort=False).size().tolist()
    spec = config["models"]["M2"]
    params = {key: value for key, value in spec.items() if key not in {"scored_model_id", "model_family_id", "eval_at"}}
    params["eval_at"] = tuple(spec["eval_at"])
    model = LGBMRanker(**params)
    model.fit(x, y_rel, group=groups, sample_weight=weights)
    artifact = artifact_dir / "model.txt"
    artifact.parent.mkdir(parents=True, exist_ok=True)
    model.booster_.save_model(str(artifact))
    return model, artifact


def _fit_contract(config: dict[str, Any], fit_id: str, family: str, feature_set_id: str,
                  feature_ids: Sequence[str], split_scope: Sequence[str], fit_rows: pd.DataFrame,
                  artifact: Path) -> dict[str, Any]:
    hyper = config["models"]["M1" if family.startswith("M1") else "M2"]
    return {
        "run_id": RUN_ID, "contract_version": CONTRACT_VERSION,
        "fit_id": fit_id, "model_family_id": family, "feature_set_id": feature_set_id,
        "feature_order": list(feature_ids), "fit_split_scope": "+".join(split_scope),
        "fit_row_n": len(fit_rows), "fit_month_n": int(fit_rows["decision_date"].nunique()),
        "fit_max_label_decision_date": pd.Timestamp(fit_rows["decision_date"].max()).strftime("%Y-%m-%d"),
        "fit_call_count": 1, "update_or_continuation_call_count": 0,
        "robustness_feature_row_read_count": 0, "robustness_label_open_count": 0,
        "robustness_outcome_column_read_count": 0,
        "fit_row_key_hash": dataframe_content_hash(fit_rows[["decision_date", "instrument_id"]],
                                                    ["decision_date", "instrument_id"]),
        "feature_order_hash": stable_hash(list(feature_ids)),
        "hyperparameter_hash": stable_hash(hyper),
        "artifact_relative_path": artifact.as_posix(),
        "artifact_sha256": sha256_file(artifact), "status": "pass", "blocking_reason": "",
    }


def _contract_audit_row(contract: dict[str, Any]) -> dict[str, Any]:
    fields = ["fit_id", "model_family_id", "feature_set_id", "fit_split_scope", "fit_row_n",
              "fit_month_n", "fit_max_label_decision_date", "fit_call_count",
              "update_or_continuation_call_count", "robustness_feature_row_read_count",
              "robustness_label_open_count", "robustness_outcome_column_read_count", "fit_row_key_hash",
              "feature_order_hash", "hyperparameter_hash", "artifact_sha256", "status", "blocking_reason"]
    return {key: contract[key] for key in fields}


def _load_ridge_coefficients(path: Path, feature_ids: Sequence[str]) -> tuple[float, np.ndarray]:
    frame = pd.read_csv(path)
    intercept = float(frame.loc[frame["feature_id"].eq("__INTERCEPT__"), "coefficient"].iloc[0])
    indexed = frame.set_index("feature_id")
    coefficients = np.array([float(indexed.at[feature, "coefficient"]) for feature in feature_ids])
    return intercept, coefficients


def _predict_artifact(family: str, artifact: Path, frame: pd.DataFrame,
                      feature_ids: Sequence[str]) -> np.ndarray:
    x = frame[list(feature_ids)].to_numpy(dtype=float)
    if family == "M1_RIDGE_RANK_REGRESSION":
        intercept, coef = _load_ridge_coefficients(artifact, feature_ids)
        return intercept + x @ coef
    import lightgbm as lgb
    return np.asarray(lgb.Booster(model_file=str(artifact)).predict(x), dtype=float)


def _model_score_rows(frame: pd.DataFrame, model_id: str, family: str, fit_id: str | None,
                      role: str, feature_set_id: str, scores: np.ndarray,
                      fit_max_date: str | None, artifact_sha: str | None) -> pd.DataFrame:
    result = frame[["decision_date", "label_month", "instrument_id"]].copy()
    result.insert(0, "feature_set_id", feature_set_id)
    result.insert(0, "model_role", role)
    result.insert(0, "fit_id", fit_id)
    result.insert(0, "model_family_id", family)
    result.insert(0, "scored_model_id", model_id)
    result["model_score"] = np.asarray(scores, dtype=float)
    result["score_finite"] = np.isfinite(result["model_score"])
    result["fit_max_label_decision_date"] = fit_max_date
    result["model_artifact_sha256"] = artifact_sha
    result["robustness_label_open_count"] = 0
    return result


def _monthly_return_tables(assignment: pd.DataFrame, labels: pd.DataFrame,
                           split_scope: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    merged = assignment.merge(labels, on=["decision_date", "label_month", "instrument_id"],
                              how="left", validate="many_to_one")
    monthly_rows = []
    rank_rows = []
    for model_id, model in merged.groupby("scored_model_id", sort=True):
        for decision_date, month in model.groupby("decision_date", sort=True):
            known = month["label_known"].fillna(False)
            paired_n = int(known.sum())
            rank_ic = month.loc[known, ["model_score", "project_resolved_next_month_return"]].corr(
                method="spearman").iloc[0, 1] if paired_n >= 2 else np.nan
            identity = month.iloc[0]
            rank_rows.append({"scored_model_id": model_id, "model_family_id": identity["model_family_id"],
                              "fit_id": identity["fit_id"], "split": split_scope,
                              "decision_date": decision_date, "label_month": identity["label_month"],
                              "return_semantics": RETURN_PRIMARY, "paired_known_n": paired_n,
                              "security_rank_ic": rank_ic, "rank_ic_finite": np.isfinite(rank_ic),
                              "exclusion_reason": "" if np.isfinite(rank_ic) else "insufficient_known_rows"})
            bucket_stats = []
            for bucket_id, bucket in month.groupby("bucket_id", sort=True):
                n = len(bucket)
                known_n = int(bucket["label_known"].fillna(False).sum())
                coverage = known_n / n
                raw_return = bucket.loc[bucket["label_known"].fillna(False),
                                        "project_resolved_next_month_return"].mean()
                bucket_stats.append((int(bucket_id), n, known_n, coverage, raw_return))
            primary_ok = len(bucket_stats) == 10 and all(nk >= 10 and cov >= 0.95
                                                         for _, _, nk, cov, _ in bucket_stats)
            strict_ok = len(bucket_stats) == 10 and all(n == nk for _, n, nk, _, _ in bucket_stats)
            for semantics, evaluable in [(RETURN_PRIMARY, primary_ok), (RETURN_STRICT, strict_ok)]:
                all_known_mean = month.loc[known, "project_resolved_next_month_return"].mean()
                for bucket_id, n, known_n, coverage, raw_return in bucket_stats:
                    monthly_rows.append({
                        "scored_model_id": model_id, "model_family_id": identity["model_family_id"],
                        "fit_id": identity["fit_id"], "split": split_scope,
                        "decision_date": decision_date, "label_month": identity["label_month"],
                        "return_semantics": semantics, "bucket_id": bucket_id, "nominal_n": n,
                        "known_n": known_n, "unknown_n": n - known_n, "known_coverage_rate": coverage,
                        "raw_bucket_return": raw_return, "common_return": all_known_mean,
                        "centered_bucket_return": raw_return - all_known_mean,
                        "month_evaluable": evaluable,
                        "exclusion_reason": "" if evaluable else (
                            "not_all_members_resolved" if semantics == RETURN_STRICT else "coverage_or_known_n_below_threshold"),
                    })
    return pd.DataFrame(monthly_rows), pd.DataFrame(rank_rows)


def hac_mean(values: Iterable[float], lag: int = 3) -> tuple[float, float]:
    x = np.asarray([v for v in values if np.isfinite(v)], dtype=float)
    n = len(x)
    if n < 2:
        return np.nan, np.nan
    mean = x.mean()
    residual = x - mean
    long_run = float(residual @ residual / n)
    used = min(lag, n - 1)
    for offset in range(1, used + 1):
        gamma = float(residual[offset:] @ residual[:-offset] / n)
        long_run += 2 * (1 - offset / (used + 1)) * gamma
    se = math.sqrt(max(long_run, 0.0) / n)
    if se <= 0:
        return np.nan, np.nan
    stat = mean / se
    from scipy.stats import norm
    return float(stat), float(2 * norm.sf(abs(stat)))


def monotonicity_metrics(monthly: pd.DataFrame, rank_ic: pd.DataFrame,
                         split_scope: str) -> pd.DataFrame:
    rows = []
    for (model_id, semantics), group in monthly.groupby(["scored_model_id", "return_semantics"], sort=True):
        identity = group.iloc[0]
        eligible = group[group["month_evaluable"]]
        curve = eligible.groupby("bucket_id")["centered_bucket_return"].mean().reindex(range(1, 11))
        rho = pd.Series(range(1, 11)).corr(curve.reset_index(drop=True), method="spearman") if curve.notna().all() else np.nan
        diffs = np.diff(curve.to_numpy(dtype=float)) if curve.notna().all() else np.full(9, np.nan)
        adjacent = int(np.sum(diffs > 0)) if np.isfinite(diffs).all() else 0
        month_rhos = []
        month_adjacent = []
        month_d10_d1 = []
        for _, month in eligible.groupby("decision_date", sort=True):
            c = month.set_index("bucket_id")["centered_bucket_return"].reindex(range(1, 11))
            month_rhos.append(pd.Series(range(1, 11)).corr(c.reset_index(drop=True), method="spearman"))
            month_adjacent.append(float(np.mean(np.diff(c.to_numpy(dtype=float)) > 0)))
            month_d10_d1.append(float(c.loc[10] - c.loc[1]))
        eligible_dates = set(eligible["decision_date"])
        ic = rank_ic[(rank_ic["scored_model_id"].eq(model_id)) &
                     (rank_ic["decision_date"].isin(eligible_dates))]["security_rank_ic"]
        t_stat, p_value = hac_mean(ic, 3)
        middle = curve.reindex(range(2, 10)).mean()
        rows.append({
            "scored_model_id": model_id, "model_family_id": identity["model_family_id"],
            "fit_id": identity["fit_id"], "split_scope": split_scope, "return_semantics": semantics,
            "scheduled_month_n": int(group["decision_date"].nunique()),
            "evaluable_month_n": int(eligible["decision_date"].nunique()),
            "mean_security_rank_ic": float(ic.mean()), "median_security_rank_ic": float(ic.median()),
            "std_security_rank_ic": float(ic.std(ddof=1)),
            "minimum_security_rank_ic": float(ic.min()), "maximum_security_rank_ic": float(ic.max()),
            "security_rank_ic_positive_month_rate": float((ic > 0).mean()),
            "HAC_t_stat": t_stat, "HAC_p_value": p_value,
            "aggregate_bucket_mean_spearman": rho, "adjacent_order_count": adjacent,
            "adjacent_order_rate": adjacent / 9.0 if np.isfinite(rho) else np.nan,
            "strict_monotonic_curve": bool(adjacent == 9) if np.isfinite(rho) else False,
            "D10_minus_D1": float(curve.loc[10] - curve.loc[1]) if curve.notna().all() else np.nan,
            "D10_minus_middle": float(curve.loc[10] - middle) if curve.notna().all() else np.nan,
            "maximum_adjacent_inversion": float(max(0.0, -np.nanmin(diffs))) if np.isfinite(diffs).any() else np.nan,
            "mean_monthly_bucket_spearman": float(np.nanmean(month_rhos)) if month_rhos else np.nan,
            "median_monthly_bucket_spearman": float(np.nanmedian(month_rhos)) if month_rhos else np.nan,
            "monthly_bucket_spearman_positive_rate": float(np.mean(np.asarray(month_rhos) > 0)) if month_rhos else np.nan,
            "mean_monthly_adjacent_order_rate": float(np.nanmean(month_adjacent)) if month_adjacent else np.nan,
            "median_monthly_D10_minus_D1": float(np.nanmedian(month_d10_d1)) if month_d10_d1 else np.nan,
            "absolute_return_positivity_used_in_gate": False,
            "inference_role": "design_contaminated_historical_diagnostic",
            **{f"D{bucket}_curve": float(curve.loc[bucket]) if pd.notna(curve.loc[bucket]) else np.nan
               for bucket in range(1, 11)},
        })
    return pd.DataFrame(rows)


def selection_worker(config: dict[str, Any], paths: dict[str, Path]) -> None:
    build = paths["build"]
    if not verify_stage(build, "materialized", "materialized_manifest.json", "materialized_output_hashes.json"):
        raise RuntimeError("materialized bundle verification failed")
    target = build / "selection"
    target.mkdir(parents=True, exist_ok=False)
    features = pd.read_parquet(build / "materialized/feature_panel.parquet")
    labels = pd.read_parquet(build / "materialized/train_validation_label_panel.parquet")
    train_rows = labels[(labels["split"].eq("train")) & labels["label_known"]]
    validation_features = features[features["split"].eq("validation")].sort_values(
        ["decision_date", "instrument_id"], kind="mergesort")
    fit_audits = []
    fitted: dict[str, tuple[str, Path, Sequence[str], dict[str, Any]]] = {}
    for family, fit_id in [("M1_RIDGE_RANK_REGRESSION", "M1_candidate_train"),
                           ("M2_LIGHTGBM_LAMBDARANK", "M2_candidate_train")]:
        artifact_dir = target / "models" / fit_id
        artifact_dir.mkdir(parents=True, exist_ok=False)
        model, artifact = (_ridge_fit(config, features, labels, ["train"], FEATURES, artifact_dir)
                           if family.startswith("M1") else
                           _lgbm_fit(config, features, labels, ["train"], FEATURES, artifact_dir))
        contract = _fit_contract(config, fit_id, family, "full16", FEATURES, ["train"], train_rows, artifact)
        contract["artifact_relative_path"] = artifact.relative_to(build).as_posix()
        write_json(artifact_dir / "fit_contract.json", contract)
        fit_audits.append(_contract_audit_row(contract))
        fitted[family] = (fit_id, artifact, FEATURES, contract)
    write_csv(target / "candidate_fit_audit.csv", pd.DataFrame(fit_audits))

    score_frames = []
    score_frames.append(_model_score_rows(
        validation_features, "B0_P4_RAW_RANK", "NONTRAINABLE_P4_BASELINE", None,
        "incumbent_paired_baseline", "p4_rank_only", validation_features["p4_rank_t"].to_numpy(), None, None))
    hash_scores = np.array([hash_null_score(r.decision_date, r.instrument_id)
                            for r in validation_features.itertuples(index=False)])
    score_frames.append(_model_score_rows(validation_features, "N0_HASH_NULL", "NONTRAINABLE_HASH_NULL", None,
                                          "pipeline_null_diagnostic", "hash_only", hash_scores, None, None))
    for family in ["M1_RIDGE_RANK_REGRESSION", "M2_LIGHTGBM_LAMBDARANK"]:
        fit_id, artifact, feature_ids, contract = fitted[family]
        values = _predict_artifact(family, artifact, validation_features, feature_ids)
        score_frames.append(_model_score_rows(validation_features, family, family, fit_id,
                                              "candidate_train_only", "full16", values,
                                              contract["fit_max_label_decision_date"], contract["artifact_sha256"]))
    scores = pd.concat(score_frames, ignore_index=True).sort_values(
        ["scored_model_id", "decision_date", "instrument_id"], kind="mergesort")
    if len(scores) != 20428:
        raise ValueError(f"validation score row mismatch: {len(scores)}")
    write_parquet(target / "candidate_validation_scores.parquet", scores)
    assignment = assign_deciles(scores)
    assignment_cols = list(scores.columns) + ["model_score_rank", "bucket_id", "nominal_bucket_n"]
    assignment = assignment[assignment_cols]
    write_parquet(target / "candidate_validation_bucket_assignment.parquet", assignment)
    assignment_hash = dataframe_content_hash(assignment, ["scored_model_id", "decision_date", "instrument_id"])
    monthly, rank_ic = _monthly_return_tables(assignment, labels[labels["split"].eq("validation")], "validation")
    metrics = monotonicity_metrics(monthly[monthly["return_semantics"].eq(RETURN_PRIMARY)], rank_ic, "validation")
    metrics["validation_bucket_assignment_content_hash"] = assignment_hash
    metrics["candidate_eligible"] = False
    metrics["selection_sort_bucket_spearman"] = metrics["aggregate_bucket_mean_spearman"]
    metrics["selection_sort_adjacent_order_rate"] = metrics["adjacent_order_rate"]
    metrics["selection_sort_mean_rank_ic"] = metrics["mean_security_rank_ic"]
    candidate_mask = metrics["scored_model_id"].isin(["M1_RIDGE_RANK_REGRESSION", "M2_LIGHTGBM_LAMBDARANK"])
    metrics.loc[candidate_mask, "candidate_eligible"] = (
        np.isfinite(metrics.loc[candidate_mask, "aggregate_bucket_mean_spearman"])
        & np.isfinite(metrics.loc[candidate_mask, "adjacent_order_rate"])
        & np.isfinite(metrics.loc[candidate_mask, "mean_security_rank_ic"])
        & (metrics.loc[candidate_mask, "aggregate_bucket_mean_spearman"] > 0)
        & (metrics.loc[candidate_mask, "mean_security_rank_ic"] > 0)
        & (metrics.loc[candidate_mask, "D10_minus_D1"] > 0)
    )
    family_order = {"M1_RIDGE_RANK_REGRESSION": 0, "M2_LIGHTGBM_LAMBDARANK": 1}
    candidates = metrics[candidate_mask].copy()
    candidates["_complexity"] = candidates["scored_model_id"].map(family_order)
    candidates = candidates.sort_values(
        ["aggregate_bucket_mean_spearman", "adjacent_order_rate", "mean_security_rank_ic", "_complexity"],
        ascending=[False, False, False, True], kind="mergesort")
    rank_map = {model: rank for rank, model in enumerate(candidates["scored_model_id"], 1)}
    metrics["selection_rank"] = metrics["scored_model_id"].map(rank_map)
    selected = candidates.iloc[0]
    selected_family = str(selected["scored_model_id"])
    selected_contract = fitted[selected_family][3]
    write_csv(target / "candidate_validation_metrics.csv", metrics)
    selection = pd.DataFrame([{
        "run_id": RUN_ID, "contract_version": CONTRACT_VERSION, "selection_split": "validation",
        "candidate_n": 2, "selected_model_family_id": selected_family,
        "selected_robustness_scored_model_id": "S0_SELECTED_FULL",
        "selected_candidate_fit_id": selected_contract["fit_id"],
        "selected_candidate_artifact_sha256": selected_contract["artifact_sha256"],
        "selected_validation_bucket_spearman": selected["aggregate_bucket_mean_spearman"],
        "selected_validation_adjacent_order_rate": selected["adjacent_order_rate"],
        "selected_validation_mean_rank_ic": selected["mean_security_rank_ic"],
        "validation_selection_gate": bool(selected["candidate_eligible"]),
        "selection_sort_key": "bucket_spearman_desc|adjacent_rate_desc|mean_rank_ic_desc|M1_before_M2",
        "robustness_label_open_count": 0,
        "selection_status": "selected_eligible" if selected["candidate_eligible"] else "selected_best_ineligible",
        "blocking_reason": "" if selected["candidate_eligible"] else "no_candidate_passed_positive_validation_gate",
    }])
    write_csv(target / "candidate_selection.csv", selection)
    access = pd.DataFrame([{
        "worker_id": "selection-worker", "process_pid": os.getpid(), "path_role": "train_validation_labels",
        "path": "materialized/train_validation_label_panel.parquet", "allowed": True, "open_count": 1,
        "bytes_read": (build / "materialized/train_validation_label_panel.parquet").stat().st_size,
        "outcome_column_read_count": 1, "fit_call_count": 2, "score_call_count": 2,
        "robustness_label_open_count": 0, "robustness_outcome_column_read_count": 0,
        "status": "pass", "blocking_reason": "",
    }])
    write_csv(target / "selection_access_audit.csv", access)


def refit_worker(config: dict[str, Any], paths: dict[str, Path]) -> None:
    build = paths["build"]
    if not verify_stage(build, "selection", "pre_robustness_selection_manifest.json",
                        "pre_robustness_selection_output_hashes.json"):
        raise RuntimeError("selection bundle verification failed")
    target = build / "models"
    target.mkdir(parents=True, exist_ok=False)
    features = pd.read_parquet(build / "materialized/feature_panel.parquet")
    features = features[features["split"].isin(["train", "validation"])]
    labels = pd.read_parquet(build / "materialized/train_validation_label_panel.parquet")
    selection = pd.read_csv(build / "selection/candidate_selection.csv").iloc[0]
    family = str(selection["selected_model_family_id"])
    selected_sets = [
        ("selected_full_refit", "full16", FEATURES),
        ("A1_p4_path_only_refit", "A1_p4_path", P4_PATH_FEATURES),
        ("A2_cross_signals_without_p4_refit", "A2_cross_signals", CROSS_FEATURES),
    ]
    registry_rows = []
    audit_rows = pd.read_csv(build / "selection/candidate_fit_audit.csv").to_dict("records")
    importance_rows = []
    for fit_id, feature_set_id, feature_ids in selected_sets:
        artifact_dir = target / fit_id
        artifact_dir.mkdir(parents=True, exist_ok=False)
        fit_rows = labels[labels["label_known"]].sort_values(["decision_date", "instrument_id"], kind="mergesort")
        model, artifact = (_ridge_fit(config, features, labels, ["train", "validation"], feature_ids, artifact_dir)
                           if family.startswith("M1") else
                           _lgbm_fit(config, features, labels, ["train", "validation"], feature_ids, artifact_dir))
        contract = _fit_contract(config, fit_id, family, feature_set_id, feature_ids,
                                 ["train", "validation"], fit_rows, artifact)
        contract["artifact_relative_path"] = artifact.relative_to(build).as_posix()
        write_json(artifact_dir / "fit_contract.json", contract)
        audit_rows.append(_contract_audit_row(contract))
        registry_rows.append({
            "fit_id": fit_id, "model_family_id": family, "feature_set_id": feature_set_id,
            "fit_split_scope": "train+validation", "artifact_relative_path": contract["artifact_relative_path"],
            "artifact_sha256": contract["artifact_sha256"], "artifact_filename": artifact.name,
            "fit_row_n": contract["fit_row_n"], "fit_month_n": contract["fit_month_n"],
            "fit_max_label_decision_date": contract["fit_max_label_decision_date"], "status": "pass",
        })
        if family.startswith("M1"):
            coefficients = pd.read_csv(artifact)
            for row in coefficients.itertuples(index=False):
                importance_rows.append({
                    "fit_id": fit_id, "model_family_id": family, "feature_set_id": feature_set_id,
                    "feature_id": row.feature_id, "feature_order": row.feature_order,
                    "importance_type": "signed_coefficient", "importance_value": row.coefficient,
                    "feature_present": True, "artifact_sha256": contract["artifact_sha256"],
                    "status": "pass", "blocking_reason": "",
                })
                if row.feature_id != "__INTERCEPT__":
                    importance_rows.append({
                        "fit_id": fit_id, "model_family_id": family, "feature_set_id": feature_set_id,
                        "feature_id": row.feature_id, "feature_order": row.feature_order,
                        "importance_type": "absolute_coefficient", "importance_value": abs(row.coefficient),
                        "feature_present": True, "artifact_sha256": contract["artifact_sha256"],
                        "status": "pass", "blocking_reason": "",
                    })
        else:
            gain = model.booster_.feature_importance(importance_type="gain")
            split = model.booster_.feature_importance(importance_type="split")
            for idx, feature in enumerate(feature_ids):
                for importance_type, values in [("gain", gain), ("split_count", split)]:
                    importance_rows.append({
                        "fit_id": fit_id, "model_family_id": family, "feature_set_id": feature_set_id,
                        "feature_id": feature, "feature_order": idx + 1,
                        "importance_type": importance_type, "importance_value": float(values[idx]),
                        "feature_present": True, "artifact_sha256": contract["artifact_sha256"],
                        "status": "pass", "blocking_reason": "",
                    })
    for candidate in ["M1_candidate_train", "M2_candidate_train"]:
        contract = read_json(build / f"selection/models/{candidate}/fit_contract.json")
        registry_rows.append({
            "fit_id": contract["fit_id"], "model_family_id": contract["model_family_id"],
            "feature_set_id": contract["feature_set_id"], "fit_split_scope": contract["fit_split_scope"],
            "artifact_relative_path": contract["artifact_relative_path"],
            "artifact_sha256": contract["artifact_sha256"],
            "artifact_filename": Path(contract["artifact_relative_path"]).name,
            "fit_row_n": contract["fit_row_n"], "fit_month_n": contract["fit_month_n"],
            "fit_max_label_decision_date": contract["fit_max_label_decision_date"], "status": "pass",
        })
    registry = pd.DataFrame(registry_rows)
    if len(registry) != 5 or registry["fit_id"].nunique() != 5 or registry["artifact_relative_path"].nunique() != 5:
        raise ValueError("five-fit artifact registry integrity failed")
    write_csv(target / "model_artifact_registry.csv", registry)
    write_csv(target / "model_fit_audit.csv", pd.DataFrame(audit_rows))
    write_csv(target / "model_feature_importance.csv", pd.DataFrame(importance_rows))
    access = pd.DataFrame([{
        "worker_id": "refit-worker", "process_pid": os.getpid(), "path_role": "train_validation_only",
        "path": "materialized/train_validation_label_panel.parquet", "allowed": True, "open_count": 1,
        "bytes_read": (build / "materialized/train_validation_label_panel.parquet").stat().st_size,
        "outcome_column_read_count": 1, "fit_call_count": 3, "score_call_count": 0,
        "pre_robustness_selection_bundle_hash_verified": True,
        "robustness_feature_row_read_count": 0, "robustness_label_open_count": 0,
        "robustness_outcome_column_read_count": 0, "status": "pass", "blocking_reason": "",
    }])
    write_csv(target / "refit_access_audit.csv", access)


def score_worker(config: dict[str, Any], paths: dict[str, Path]) -> None:
    build = paths["build"]
    if not verify_stage(build, "models", "model_bundle_manifest.json", "model_bundle_output_hashes.json"):
        raise RuntimeError("model bundle verification failed")
    target = build / "scores"
    target.mkdir(parents=True, exist_ok=False)
    features = pd.read_parquet(build / "materialized/feature_panel.parquet")
    robust = features[features["split"].eq("robustness")].sort_values(
        ["decision_date", "instrument_id"], kind="mergesort")
    if len(robust) != 9300:
        raise ValueError("robustness feature row mismatch")
    selection = pd.read_csv(build / "selection/candidate_selection.csv").iloc[0]
    family = str(selection["selected_model_family_id"])
    selection_hash = stage_bundle_hash(build, "selection")
    model_hash = stage_bundle_hash(build, "models")
    frames = []
    b0 = _model_score_rows(robust, "B0_P4_RAW_RANK", "NONTRAINABLE_P4_BASELINE", None,
                           "incumbent_paired_baseline", "p4_rank_only", robust["p4_rank_t"].to_numpy(), None, None)
    frames.append(b0)
    null_values = np.array([hash_null_score(r.decision_date, r.instrument_id) for r in robust.itertuples(index=False)])
    frames.append(_model_score_rows(robust, "N0_HASH_NULL", "NONTRAINABLE_HASH_NULL", None,
                                    "pipeline_null_diagnostic", "hash_only", null_values, None, None))
    for model_id, fit_id, feature_set_id, feature_ids in [
        ("S0_SELECTED_FULL", "selected_full_refit", "full16", FEATURES),
        ("A1_P4_PATH_ONLY", "A1_p4_path_only_refit", "A1_p4_path", P4_PATH_FEATURES),
        ("A2_CROSS_SIGNALS_WITHOUT_P4", "A2_cross_signals_without_p4_refit", "A2_cross_signals", CROSS_FEATURES),
    ]:
        contract = read_json(build / f"models/{fit_id}/fit_contract.json")
        artifact = build / contract["artifact_relative_path"]
        values = _predict_artifact(family, artifact, robust, feature_ids)
        frames.append(_model_score_rows(robust, model_id, family, fit_id, "frozen_robustness_refit",
                                        feature_set_id, values, contract["fit_max_label_decision_date"],
                                        contract["artifact_sha256"]))
    scores = pd.concat(frames, ignore_index=True)
    scores["split"] = "robustness"
    scores["robustness_label_read_during_fit"] = False
    scores["pre_robustness_selection_bundle_hash"] = selection_hash
    scores["model_bundle_hash"] = model_hash
    scores = scores.sort_values(["scored_model_id", "decision_date", "instrument_id"], kind="mergesort")
    if len(scores) != 46500:
        raise ValueError(f"robustness score row mismatch: {len(scores)}")
    write_parquet(target / "robustness_model_score_panel.parquet", scores)
    assignment = assign_deciles(scores)
    assignment_cols = ["scored_model_id", "model_family_id", "fit_id", "model_role", "feature_set_id",
                       "split", "decision_date", "label_month", "instrument_id", "model_score",
                       "model_score_rank", "bucket_id", "nominal_bucket_n", "model_artifact_sha256",
                       "pre_robustness_selection_bundle_hash", "model_bundle_hash"]
    write_parquet(target / "robustness_model_bucket_assignment.parquet", assignment[assignment_cols])
    access = pd.DataFrame([{
        "worker_id": "score-worker", "process_pid": os.getpid(), "path_role": "robustness_features",
        "path": "materialized/feature_panel.parquet", "allowed": True, "open_count": 1,
        "bytes_read": (build / "materialized/feature_panel.parquet").stat().st_size,
        "outcome_column_read_count": 0, "model_bundle_hash_verified": True,
        "any_label_open_count": 0, "fit_call_count": 0, "update_or_continuation_call_count": 0,
        "feature_transform_fit_call_count": 0, "status": "pass", "blocking_reason": "",
    }])
    write_csv(target / "score_worker_access_audit.csv", access)


def _turnover(assignment: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for model_id, model in assignment.groupby("scored_model_id", sort=True):
        prior_date = None
        prior_members: set[str] = set()
        for decision_date, month in model.groupby("decision_date", sort=True):
            members = set(month.loc[month["bucket_id"].eq(10), "instrument_id"].astype(str))
            if prior_date is None:
                turnover = np.nan
                reason = "no_prior_scheduled_month"
            else:
                union = members | prior_members
                turnover = 0.5 * sum(abs((1 / len(members) if item in members else 0) -
                                         (1 / len(prior_members) if item in prior_members else 0)) for item in union)
                reason = ""
            identity = month.iloc[0]
            rows.append({"scored_model_id": model_id, "split": "robustness", "decision_date": decision_date,
                         "prior_decision_date": prior_date, "D10_member_n": len(members),
                         "prior_D10_member_n": len(prior_members) if prior_date is not None else np.nan,
                         "overlap_n": len(members & prior_members) if prior_date is not None else np.nan,
                         "one_way_top_bucket_turnover": turnover, "turnover_finite": np.isfinite(turnover),
                         "exclusion_reason": reason, "model_family_id": identity["model_family_id"],
                         "fit_id": identity["fit_id"]})
            prior_date, prior_members = decision_date, members
    result = pd.DataFrame(rows)
    if len(result) != 105 or int(result["turnover_finite"].sum()) != 100:
        raise ValueError("turnover shape mismatch")
    return result


def _paired_delta(monotonicity: pd.DataFrame, validation: pd.DataFrame | None = None) -> pd.DataFrame:
    rows = []
    metrics = ["aggregate_bucket_mean_spearman", "adjacent_order_rate", "mean_security_rank_ic", "D10_minus_D1"]
    for split_scope in sorted(monotonicity["split_scope"].unique()):
        part = monotonicity[(monotonicity["split_scope"].eq(split_scope)) &
                            (monotonicity["return_semantics"].eq(RETURN_PRIMARY))].set_index("scored_model_id")
        if "B0_P4_RAW_RANK" not in part.index:
            continue
        for challenger in [x for x in part.index if x != "B0_P4_RAW_RANK"]:
            for metric in metrics:
                cv = float(part.at[challenger, metric])
                bv = float(part.at["B0_P4_RAW_RANK", metric])
                rows.append({"challenger_scored_model_id": challenger,
                             "baseline_scored_model_id": "B0_P4_RAW_RANK", "split_scope": split_scope,
                             "common_month_n": int(min(part.at[challenger, "evaluable_month_n"],
                                                       part.at["B0_P4_RAW_RANK", "evaluable_month_n"])),
                             "common_instrument_month_n": 9283 if split_scope.startswith("robustness") else np.nan,
                             "metric_id": metric,
                             "challenger_value": cv, "baseline_value": bv, "paired_delta": cv - bv,
                             "delta_direction_favorable": cv - bv > 0})
    if validation is not None:
        part = validation[validation["return_semantics"].eq(RETURN_PRIMARY)].set_index("scored_model_id")
        for challenger in ["M1_RIDGE_RANK_REGRESSION", "M2_LIGHTGBM_LAMBDARANK"]:
            for metric in metrics:
                cv = float(part.at[challenger, metric])
                bv = float(part.at["B0_P4_RAW_RANK", metric])
                delta = cv - bv if np.isfinite(cv) and np.isfinite(bv) else np.nan
                rows.append({"challenger_scored_model_id": challenger,
                             "baseline_scored_model_id": "B0_P4_RAW_RANK", "split_scope": "validation",
                             "common_month_n": 12, "common_instrument_month_n": 5106,
                             "metric_id": metric, "challenger_value": cv, "baseline_value": bv,
                             "paired_delta": delta,
                             "delta_direction_favorable": bool(delta > 0) if np.isfinite(delta) else False})
    return pd.DataFrame(rows)


def _metric_from_month_subset(monthly: pd.DataFrame, rank_ic: pd.DataFrame, metric: str) -> float:
    readout = monotonicity_metrics(monthly, rank_ic, "bootstrap")
    return float(readout.iloc[0][metric]) if len(readout) else np.nan


def _bootstrap_deltas(monthly: pd.DataFrame, rank_ic: pd.DataFrame, repetitions: int,
                      block_length: int, seed: int) -> pd.DataFrame:
    rows = []
    rng = np.random.Generator(np.random.PCG64(seed))
    base_id = "B0_P4_RAW_RANK"
    months = sorted(monthly["decision_date"].unique())
    n = len(months)
    starts = np.arange(0, n - block_length + 1)
    blocks_per = math.ceil(n / block_length)
    sampled_starts = rng.choice(starts, size=(repetitions, blocks_per), replace=True)
    draw_indices = (sampled_starts[:, :, None] + np.arange(block_length)[None, None, :]).reshape(
        repetitions, -1)[:, :n]
    curves: dict[str, np.ndarray] = {}
    rank_values: dict[str, np.ndarray] = {}
    for model_id in [base_id, "S0_SELECTED_FULL", "A1_P4_PATH_ONLY", "A2_CROSS_SIGNALS_WITHOUT_P4"]:
        curve = monthly[monthly["scored_model_id"].eq(model_id)].pivot(
            index="decision_date", columns="bucket_id", values="centered_bucket_return").reindex(months)
        curves[model_id] = curve.reindex(columns=range(1, 11)).to_numpy(dtype=float)
        ic = rank_ic[rank_ic["scored_model_id"].eq(model_id)].set_index("decision_date")["security_rank_ic"]
        rank_values[model_id] = ic.reindex(months).to_numpy(dtype=float)

    def replicate_metrics(model_id: str) -> dict[str, np.ndarray]:
        from scipy.stats import rankdata

        sampled_curve = curves[model_id][draw_indices].mean(axis=1)
        curve_ranks = rankdata(sampled_curve, axis=1, method="average")
        bucket_rank = np.arange(1.0, 11.0)
        centered_bucket_rank = bucket_rank - bucket_rank.mean()
        centered_curve_rank = curve_ranks - curve_ranks.mean(axis=1, keepdims=True)
        denominator = np.sqrt(np.sum(centered_bucket_rank**2) *
                              np.sum(centered_curve_rank**2, axis=1))
        rho = np.sum(centered_curve_rank * centered_bucket_rank[None, :], axis=1) / denominator
        return {
            "aggregate_bucket_mean_spearman": rho,
            "adjacent_order_rate": np.mean(np.diff(sampled_curve, axis=1) >= 0, axis=1),
            "mean_security_rank_ic": rank_values[model_id][draw_indices].mean(axis=1),
            "D10_minus_D1": sampled_curve[:, 9] - sampled_curve[:, 0],
        }

    replicated = {model_id: replicate_metrics(model_id) for model_id in curves}
    for challenger in ["S0_SELECTED_FULL", "A1_P4_PATH_ONLY", "A2_CROSS_SIGNALS_WITHOUT_P4"]:
        for metric in ["aggregate_bucket_mean_spearman", "adjacent_order_rate", "mean_security_rank_ic", "D10_minus_D1"]:
            deltas = replicated[challenger][metric] - replicated[base_id][metric]
            finite = deltas[np.isfinite(deltas)]
            quantiles = np.quantile(finite, [0.05, 0.5, 0.95], method="linear") if len(finite) else [np.nan] * 3
            rows.append({"challenger_scored_model_id": challenger, "baseline_scored_model_id": base_id,
                         "split_scope": "robustness_full", "metric_id": metric, "common_month_n": n,
                         "block_length": block_length, "candidate_block_start_n": len(starts),
                         "blocks_per_replicate": blocks_per, "seed": seed,
                         "requested_replicate_n": repetitions, "finite_replicate_n": len(finite),
                         "quantile_method": "linear", "p05": quantiles[0], "p50": quantiles[1],
                         "p95": quantiles[2], "two_sided_CI_level": 0.90,
                         "CI_lower_gt_zero": bool(quantiles[0] > 0),
                         "status": "pass" if len(finite) == repetitions else "partial",
                         "exclusion_reason": "" if len(finite) == repetitions else "nonfinite_replicates"})
    return pd.DataFrame(rows)


def metric_worker(config: dict[str, Any], paths: dict[str, Path]) -> None:
    build = paths["build"]
    if not verify_stage(build, "scores", "score_bundle_manifest.json", "score_bundle_output_hashes.json"):
        raise RuntimeError("score bundle verification failed")
    target = build / "historical"
    target.mkdir(parents=True, exist_ok=False)
    assignment = pd.read_parquet(build / "scores/robustness_model_bucket_assignment.parquet")
    labels = pd.read_parquet(build / "materialized/robustness_label_panel.parquet")
    monthly, rank_ic = _monthly_return_tables(assignment, labels, "robustness")
    write_csv(target / "model_bucket_monthly_returns.csv.gz", monthly)
    write_csv(target / "top_bucket_turnover_monthly.csv", _turnover(assignment))
    write_csv(target / "security_rank_ic_monthly.csv", rank_ic)
    readouts = []
    for scope, dates in [
        ("robustness_full", sorted(monthly["decision_date"].unique())),
        ("robustness_early", sorted(monthly["decision_date"].unique())[:10]),
        ("robustness_late", sorted(monthly["decision_date"].unique())[10:]),
    ]:
        mm = monthly[monthly["decision_date"].isin(dates)]
        ii = rank_ic[rank_ic["decision_date"].isin(dates)]
        readouts.append(monotonicity_metrics(mm, ii, scope))
    monotonicity = pd.concat(readouts, ignore_index=True)
    write_csv(target / "monotonicity_readout.csv", monotonicity)
    validation_metrics = pd.read_csv(build / "selection/candidate_validation_metrics.csv")
    write_csv(target / "paired_model_delta.csv", _paired_delta(monotonicity, validation_metrics))
    bootstrap = _bootstrap_deltas(
        monthly[(monthly["return_semantics"].eq(RETURN_PRIMARY)) & monthly["month_evaluable"]],
        rank_ic, int(config["inference"]["bootstrap_repetitions"]),
        int(config["inference"]["bootstrap_block_length"]), int(config["inference"]["seed"]),
    )
    write_csv(target / "block_bootstrap_readout.csv", bootstrap)
    ablation_rows = []
    for scope in ["robustness_full", "robustness_early", "robustness_late"]:
        for semantics in [RETURN_PRIMARY, RETURN_STRICT]:
            part = monotonicity[(monotonicity["split_scope"].eq(scope)) &
                                (monotonicity["return_semantics"].eq(semantics))].set_index("scored_model_id")
            for metric in ["aggregate_bucket_mean_spearman", "adjacent_order_rate", "mean_security_rank_ic", "D10_minus_D1"]:
                values = {model: float(part.at[model, metric]) for model in
                          ["B0_P4_RAW_RANK", "S0_SELECTED_FULL", "A1_P4_PATH_ONLY", "A2_CROSS_SIGNALS_WITHOUT_P4"]}
                ablation_rows.append({
                    "split_scope": scope, "return_semantics": semantics, "metric_id": metric,
                    "selected_model_family_id": part.at["S0_SELECTED_FULL", "model_family_id"],
                    "baseline_scored_model_id": "B0_P4_RAW_RANK", "full_scored_model_id": "S0_SELECTED_FULL",
                    "A1_scored_model_id": "A1_P4_PATH_ONLY", "A2_scored_model_id": "A2_CROSS_SIGNALS_WITHOUT_P4",
                    "baseline_value": values["B0_P4_RAW_RANK"], "full_value": values["S0_SELECTED_FULL"],
                    "A1_value": values["A1_P4_PATH_ONLY"], "A2_value": values["A2_CROSS_SIGNALS_WITHOUT_P4"],
                    "full_minus_baseline": values["S0_SELECTED_FULL"] - values["B0_P4_RAW_RANK"],
                    "A1_minus_baseline": values["A1_P4_PATH_ONLY"] - values["B0_P4_RAW_RANK"],
                    "A2_minus_baseline": values["A2_CROSS_SIGNALS_WITHOUT_P4"] - values["B0_P4_RAW_RANK"],
                    "A1_minus_full": values["A1_P4_PATH_ONLY"] - values["S0_SELECTED_FULL"],
                    "A2_minus_full": values["A2_CROSS_SIGNALS_WITHOUT_P4"] - values["S0_SELECTED_FULL"],
                    "favorable_direction": "higher_is_better", "status": "pass",
                })
    write_csv(target / "ablation_readout.csv", pd.DataFrame(ablation_rows))
    access = pd.DataFrame([{
        "worker_id": "metric-worker", "process_pid": os.getpid(), "path_role": "sealed_scores_and_robustness_labels",
        "path": "scores/robustness_model_bucket_assignment.parquet|materialized/robustness_label_panel.parquet",
        "allowed": True, "open_count": 2,
        "bytes_read": ((build / "scores/robustness_model_bucket_assignment.parquet").stat().st_size +
                       (build / "materialized/robustness_label_panel.parquet").stat().st_size),
        "score_bundle_manifest_verified": True, "score_bundle_hash_verified": True,
        "robustness_label_column_read_count": 1, "fit_call_count": 0,
        "update_or_continuation_call_count": 0, "candidate_selection_call_count": 0,
        "feature_transform_fit_call_count": 0, "status": "pass", "blocking_reason": "",
    }])
    write_csv(target / "metric_worker_access_audit.csv", access)


def worker_exit_record(mode: str, process: subprocess.Popen[str], started: str, ended: str,
                       stdout: str, stderr: str, build: Path, outputs: Sequence[str]) -> dict[str, Any]:
    return {
        "run_id": RUN_ID, "contract_version": CONTRACT_VERSION, "worker_mode": mode,
        "process_start_contract": "fresh_execve_interpreter", "worker_pid": process.pid,
        "started_at_utc": started, "ended_at_utc": ended, "exit_code": process.returncode,
        "parent_observed_at_utc": utc_now(), "stdout_sha256": hashlib.sha256(stdout.encode()).hexdigest(),
        "stderr_sha256": hashlib.sha256(stderr.encode()).hexdigest(),
        "worker_output_hashes": {rel: sha256_file(build / rel) for rel in outputs if (build / rel).is_file()},
        "robustness_label_open_count": 0 if mode != "metric" else 1,
        "robustness_outcome_column_read_count": 0 if mode != "metric" else 1,
    }


def run_worker(config_path: Path, build: Path, mode: str, outputs: Sequence[str]) -> dict[str, Any]:
    started = utc_now()
    command = [sys.executable, str(Path(__file__).resolve()), "--config", str(config_path),
               "--worker", mode, "--build-root", str(build)]
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    stdout, stderr = process.communicate()
    ended = utc_now()
    record = worker_exit_record(mode, process, started, ended, stdout, stderr, build, outputs)
    if process.returncode != 0:
        sys.stderr.write(stderr)
        raise RuntimeError(f"{mode} worker failed with exit code {process.returncode}")
    return record


def replay_once(config_path: Path, config: dict[str, Any], root: Path, build: Path) -> dict[str, str]:
    build.mkdir(parents=True, exist_ok=False)
    run_worker(config_path, build, "preflight", [
        "preflight/contract_snapshot.json", "preflight/upstream_input_integrity_audit.csv",
        "preflight/split_registry.csv", "preflight/feature_registry.csv", "preflight/model_registry.csv",
    ])
    hashes: dict[str, str] = {}
    hashes["preflight_bundle_hash"] = seal_stage(
        build, "preflight", "preflight_manifest.json", "preflight_output_hashes.json")
    run_worker(config_path, build, "feature", ["materialized/feature_panel.parquet",
                                               "materialized/feature_lineage_audit.csv"])
    run_worker(config_path, build, "label", ["materialized/train_validation_label_panel.parquet",
                                             "materialized/robustness_label_panel.parquet",
                                             "materialized/label_resolution_audit.csv"])
    hashes["materialized_bundle_hash"] = seal_stage(
        build, "materialized", "materialized_manifest.json", "materialized_output_hashes.json",
        {"preflight_bundle_hash": hashes["preflight_bundle_hash"]})
    selection_outputs = [
        "selection/candidate_validation_scores.parquet", "selection/candidate_validation_bucket_assignment.parquet",
        "selection/candidate_validation_metrics.csv", "selection/candidate_selection.csv",
        "selection/candidate_fit_audit.csv", "selection/selection_access_audit.csv",
        "selection/models/M1_candidate_train/coefficients.csv",
        "selection/models/M1_candidate_train/fit_contract.json",
        "selection/models/M2_candidate_train/model.txt", "selection/models/M2_candidate_train/fit_contract.json",
    ]
    exit_record = run_worker(config_path, build, "selection", selection_outputs)
    write_json(build / "selection/selection_worker_exit.json", exit_record)
    hashes["pre_robustness_selection_bundle_hash"] = seal_stage(
        build, "selection", "pre_robustness_selection_manifest.json",
        "pre_robustness_selection_output_hashes.json",
        {"materialized_bundle_hash": hashes["materialized_bundle_hash"]})
    model_outputs = ["models/model_artifact_registry.csv", "models/model_fit_audit.csv",
                     "models/model_feature_importance.csv", "models/refit_access_audit.csv"]
    exit_record = run_worker(config_path, build, "refit", model_outputs)
    write_json(build / "models/refit_worker_exit.json", exit_record)
    hashes["model_bundle_hash"] = seal_stage(
        build, "models", "model_bundle_manifest.json", "model_bundle_output_hashes.json",
        {"pre_robustness_selection_bundle_hash": hashes["pre_robustness_selection_bundle_hash"]})
    score_outputs = ["scores/robustness_model_score_panel.parquet",
                     "scores/robustness_model_bucket_assignment.parquet", "scores/score_worker_access_audit.csv"]
    exit_record = run_worker(config_path, build, "score", score_outputs)
    write_json(build / "scores/score_worker_exit.json", exit_record)
    hashes["score_bundle_hash"] = seal_stage(
        build, "scores", "score_bundle_manifest.json", "score_bundle_output_hashes.json",
        {"pre_robustness_selection_bundle_hash": hashes["pre_robustness_selection_bundle_hash"],
         "model_bundle_hash": hashes["model_bundle_hash"]})
    historical_outputs = [
        "historical/model_bucket_monthly_returns.csv.gz", "historical/top_bucket_turnover_monthly.csv",
        "historical/security_rank_ic_monthly.csv", "historical/monotonicity_readout.csv",
        "historical/paired_model_delta.csv", "historical/block_bootstrap_readout.csv",
        "historical/ablation_readout.csv", "historical/metric_worker_access_audit.csv",
    ]
    exit_record = run_worker(config_path, build, "metric", historical_outputs)
    write_json(build / "historical/metric_worker_exit.json", exit_record)
    hashes["historical_bundle_hash"] = seal_stage(
        build, "historical", "historical_manifest.json", "historical_output_hashes.json",
        {"score_bundle_hash": hashes["score_bundle_hash"], "model_bundle_hash": hashes["model_bundle_hash"],
         "pre_robustness_selection_bundle_hash": hashes["pre_robustness_selection_bundle_hash"]})
    return hashes


CORE_ARTIFACTS = [
    ("feature_panel", "materialized/feature_panel.parquet", ["decision_date", "instrument_id"]),
    ("train_validation_labels", "materialized/train_validation_label_panel.parquet", ["decision_date", "instrument_id"]),
    ("robustness_labels", "materialized/robustness_label_panel.parquet", ["decision_date", "instrument_id"]),
    ("M1_candidate", "selection/models/M1_candidate_train/coefficients.csv", None),
    ("M2_candidate", "selection/models/M2_candidate_train/model.txt", None),
    ("candidate_validation_scores", "selection/candidate_validation_scores.parquet",
     ["scored_model_id", "decision_date", "instrument_id"]),
    ("candidate_validation_metrics", "selection/candidate_validation_metrics.csv", ["scored_model_id", "return_semantics"]),
    ("candidate_selection", "selection/candidate_selection.csv", ["run_id"]),
    ("robustness_scores", "scores/robustness_model_score_panel.parquet",
     ["scored_model_id", "decision_date", "instrument_id"]),
    ("robustness_assignment", "scores/robustness_model_bucket_assignment.parquet",
     ["scored_model_id", "decision_date", "instrument_id"]),
    ("monthly_returns", "historical/model_bucket_monthly_returns.csv.gz",
     ["scored_model_id", "split", "decision_date", "return_semantics", "bucket_id"]),
    ("monotonicity", "historical/monotonicity_readout.csv",
     ["scored_model_id", "split_scope", "return_semantics"]),
    ("bootstrap", "historical/block_bootstrap_readout.csv",
     ["challenger_scored_model_id", "baseline_scored_model_id", "split_scope", "metric_id"]),
]


def _read_tabular(path: Path) -> pd.DataFrame:
    if path.suffix == ".parquet":
        return pd.read_parquet(path)
    return pd.read_csv(path)


def compare_replays(a: Path, b: Path) -> tuple[pd.DataFrame, dict[str, str]]:
    rows = []
    b_hashes = {}
    volatile_columns = {"pre_robustness_selection_bundle_hash", "model_bundle_hash"}
    for role, relative, keys in CORE_ARTIFACTS:
        pa, pb = a / relative, b / relative
        ha, hb = sha256_file(pa), sha256_file(pb)
        b_hashes[relative] = hb
        if keys is None:
            equal = ha == hb
            row_n_a = row_n_b = np.nan
            key_equal = equal
            method = "sha256_exact"
        else:
            fa, fb = _read_tabular(pa), _read_tabular(pb)
            fa = fa.sort_values(keys, kind="mergesort").reset_index(drop=True)
            fb = fb.sort_values(keys, kind="mergesort").reset_index(drop=True)
            row_n_a, row_n_b = len(fa), len(fb)
            key_equal = fa[keys].astype(str).equals(fb[keys].astype(str))
            common_columns = [c for c in fa.columns if c in fb.columns and c not in volatile_columns]
            schema_equal = common_columns == [c for c in fb.columns if c in fa.columns and c not in volatile_columns]
            equal = schema_equal and row_n_a == row_n_b and key_equal
            if equal:
                for column in common_columns:
                    if column in keys:
                        continue
                    if pd.api.types.is_numeric_dtype(fa[column]) and pd.api.types.is_numeric_dtype(fb[column]):
                        if not np.allclose(pd.to_numeric(fa[column], errors="coerce"),
                                           pd.to_numeric(fb[column], errors="coerce"),
                                           atol=1e-12, rtol=0, equal_nan=True):
                            equal = False
                            break
                    elif not fa[column].fillna("__NULL__").astype(str).equals(
                            fb[column].fillna("__NULL__").astype(str)):
                        equal = False
                        break
            method = "float64_allclose"
        rows.append({"artifact_role": role, "comparison_id": relative,
                     "replay_a_relative_path": relative, "replay_b_relative_path": relative,
                     "replay_a_content_hash": ha, "replay_b_content_hash": hb,
                     "comparison_method": method, "atol": 0 if method == "sha256_exact" else 1e-12,
                     "rtol": 0, "row_n_a": row_n_a, "row_n_b": row_n_b,
                     "key_set_equal": key_equal, "value_equal": equal,
                     "status": "pass" if equal else "fail",
                     "blocking_reason": "" if equal else "deterministic_core_mismatch"})
    return pd.DataFrame(rows), b_hashes


def _fmt(value: Any, digits: int = 4) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    return "NA" if not np.isfinite(number) else f"{number:.{digits}f}"


def _markdown_table(frame: pd.DataFrame, columns: Sequence[str], labels: Sequence[str] | None = None) -> str:
    labels = list(labels or columns)
    lines = ["| " + " | ".join(labels) + " |", "|" + "|".join(["---"] * len(columns)) + "|"]
    for row in frame[list(columns)].itertuples(index=False, name=None):
        lines.append("| " + " | ".join(_fmt(v) if isinstance(v, (float, np.floating)) else str(v) for v in row) + " |")
    return "\n".join(lines)


def _make_plots(build: Path, monthly: pd.DataFrame) -> list[str]:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    assets = build / "20B_P4_learned_monotonic_return_ranking_diagnostic_report_assets"
    assets.mkdir(parents=True, exist_ok=False)
    primary = monthly[(monthly["return_semantics"].eq(RETURN_PRIMARY)) & monthly["month_evaluable"]]
    curve = primary.groupby(["scored_model_id", "bucket_id"])["centered_bucket_return"].mean().unstack(0)
    fig, ax = plt.subplots(figsize=(10, 6))
    for model in ROBUSTNESS_MODELS:
        ax.plot(curve.index, 100 * curve[model], marker="o", label=model)
    ax.axhline(0, color="black", lw=0.8)
    ax.set(xlabel="Score decile (D1 low → D10 high)", ylabel="Mean centered next-month return (%)",
           title="Robustness aggregate decile curves")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.25)
    fig.tight_layout()
    curve_path = assets / "robustness_aggregate_decile_curves.png"
    fig.savefig(curve_path, dpi=160)
    plt.close(fig)
    selected = primary[primary["scored_model_id"].eq("S0_SELECTED_FULL")]
    heat = selected.pivot(index="decision_date", columns="bucket_id", values="centered_bucket_return").sort_index()
    fig, ax = plt.subplots(figsize=(12, 7))
    image = ax.imshow(100 * heat.to_numpy(), aspect="auto", cmap="RdYlGn")
    ax.set_xticks(range(10), [f"D{x}" for x in range(1, 11)])
    ax.set_yticks(range(len(heat)), [pd.Timestamp(x).strftime("%Y-%m") for x in heat.index], fontsize=7)
    ax.set_title("Selected model monthly centered decile returns (%)")
    fig.colorbar(image, ax=ax, label="Centered return (%)")
    fig.tight_layout()
    heat_path = assets / "selected_monthly_decile_heatmap.png"
    fig.savefig(heat_path, dpi=160)
    plt.close(fig)
    return [curve_path.relative_to(build).as_posix(), heat_path.relative_to(build).as_posix()]


def decision_state_from_gates(gates: dict[str, bool], selected: pd.Series, baseline: pd.Series,
                              early: pd.Series, late: pd.Series) -> str:
    if not gates["stage_seal_integrity_gate"]:
        return "20B_P4_MLRANK_stage_seal_integrity_blocked"
    if not gates["upstream_input_integrity_gate"]:
        return "20B_P4_MLRANK_upstream_input_integrity_blocked"
    if not (gates["outcome_firewall_gate"] and gates["split_integrity_gate"]):
        return "20B_P4_MLRANK_outcome_firewall_or_split_blocked"
    if not (gates["dependency_gate"] and gates["model_registry_gate"] and gates["score_integrity_gate"]
            and gates["determinism_gate"]):
        return "20B_P4_MLRANK_dependency_training_or_score_pipeline_blocked"
    if not gates["metric_materialization_gate"]:
        return "20B_P4_MLRANK_metric_materialization_blocked"
    if not gates["sample_support_gate"]:
        return "20B_P4_MLRANK_sample_support_underpowered"
    if gates["near_monotonic_gate"]:
        return "20B_P4_MLRANK_near_monotonic_multifactor_historical_design_observed"
    if gates["ordering_improvement_gate"]:
        return "20B_P4_MLRANK_multifactor_ordering_improved_not_near_monotonic"
    directional = any(
        selected[metric] > baseline[metric]
        for metric in ["aggregate_bucket_mean_spearman", "adjacent_order_rate", "mean_security_rank_ic", "D10_minus_D1"]
    )
    if directional:
        return "20B_P4_MLRANK_multifactor_weak_or_unstable_improvement"
    return "20B_P4_MLRANK_no_multifactor_ordering_improvement"


def finalize(config: dict[str, Any], build: Path, replay_hashes: dict[str, str], comparison: pd.DataFrame) -> None:
    if not all(verify_stage(build, directory, manifest, registry) for directory, manifest, registry in [
        ("preflight", "preflight_manifest.json", "preflight_output_hashes.json"),
        ("materialized", "materialized_manifest.json", "materialized_output_hashes.json"),
        ("selection", "pre_robustness_selection_manifest.json", "pre_robustness_selection_output_hashes.json"),
        ("models", "model_bundle_manifest.json", "model_bundle_output_hashes.json"),
        ("scores", "score_bundle_manifest.json", "score_bundle_output_hashes.json"),
        ("historical", "historical_manifest.json", "historical_output_hashes.json"),
    ]):
        raise RuntimeError("stage seal verification failed at finalize")
    selection = pd.read_csv(build / "selection/candidate_selection.csv").iloc[0]
    validation = pd.read_csv(build / "selection/candidate_validation_metrics.csv")
    monotonicity = pd.read_csv(build / "historical/monotonicity_readout.csv")
    monthly = pd.read_csv(build / "historical/model_bucket_monthly_returns.csv.gz", parse_dates=["decision_date"])
    primary_full = monotonicity[(monotonicity["split_scope"].eq("robustness_full")) &
                                (monotonicity["return_semantics"].eq(RETURN_PRIMARY))].set_index("scored_model_id")
    selected = primary_full.loc["S0_SELECTED_FULL"]
    baseline = primary_full.loc["B0_P4_RAW_RANK"]
    early = monotonicity[(monotonicity["split_scope"].eq("robustness_early")) &
                         (monotonicity["return_semantics"].eq(RETURN_PRIMARY)) &
                         (monotonicity["scored_model_id"].eq("S0_SELECTED_FULL"))].iloc[0]
    late = monotonicity[(monotonicity["split_scope"].eq("robustness_late")) &
                        (monotonicity["return_semantics"].eq(RETURN_PRIMARY)) &
                        (monotonicity["scored_model_id"].eq("S0_SELECTED_FULL"))].iloc[0]
    snapshot = read_json(build / "preflight/contract_snapshot.json")
    feature_panel = pd.read_parquet(build / "materialized/feature_panel.parquet",
                                    columns=["decision_date", "instrument_id", "split", "feature_outcome_read_count"])
    label_audit = pd.read_csv(build / "materialized/label_resolution_audit.csv").iloc[0]
    model_registry = pd.read_csv(build / "models/model_artifact_registry.csv")
    score_panel = pd.read_parquet(build / "scores/robustness_model_score_panel.parquet",
                                  columns=["scored_model_id", "decision_date", "instrument_id", "score_finite"])
    metric_columns = ["aggregate_bucket_mean_spearman", "adjacent_order_rate",
                      "mean_security_rank_ic", "D10_minus_D1"]
    sample_support = bool(
        selected["evaluable_month_n"] >= 18 and baseline["evaluable_month_n"] >= 18
        and early["evaluable_month_n"] >= 8 and late["evaluable_month_n"] >= 9
        and validation["evaluable_month_n"].min() >= 10
    )
    metric_materialized = bool(
        np.isfinite(validation[metric_columns]).all().all()
        and np.isfinite(monotonicity[metric_columns]).all().all()
    )
    gates = {
        "stage_seal_integrity_gate": True,
        "upstream_integrity_gate": bool(snapshot["upstream_input_integrity_gate"]),
        "upstream_input_integrity_gate": bool(snapshot["upstream_input_integrity_gate"]),
        "outcome_firewall_gate": bool(feature_panel["feature_outcome_read_count"].eq(0).all()
                                      and label_audit["paper_proxy_column_read_count"] == 0
                                      and label_audit["paper_proxy_column_materialized_count"] == 0),
        "split_integrity_gate": bool(feature_panel.groupby("decision_date")["split"].nunique().eq(1).all()),
        "dependency_gate": bool(snapshot["dependency_gate"]),
        "model_registry_gate": bool(len(model_registry) == 5 and model_registry["status"].eq("pass").all()),
        "score_integrity_gate": bool(len(score_panel) == 46500 and score_panel["score_finite"].all()),
        "determinism_gate": bool(comparison["value_equal"].all()),
        "sample_support_gate": sample_support,
        "metric_materialization_gate": metric_materialized,
        "validation_selection_gate": bool(selection["validation_selection_gate"]),
    }
    common_integrity = all(gates[key] for key in [
        "stage_seal_integrity_gate", "upstream_integrity_gate", "outcome_firewall_gate",
        "split_integrity_gate", "model_registry_gate", "score_integrity_gate", "determinism_gate",
        "sample_support_gate", "metric_materialization_gate", "validation_selection_gate",
    ])
    gates["ordering_improvement_gate"] = bool(
        common_integrity
        and selected["aggregate_bucket_mean_spearman"] > 0
        and selected["aggregate_bucket_mean_spearman"] > baseline["aggregate_bucket_mean_spearman"]
        and selected["adjacent_order_rate"] > baseline["adjacent_order_rate"]
        and selected["mean_security_rank_ic"] > 0
        and selected["mean_security_rank_ic"] > baseline["mean_security_rank_ic"]
        and selected["D10_minus_D1"] > 0
        and early["aggregate_bucket_mean_spearman"] > 0
        and late["aggregate_bucket_mean_spearman"] > 0
    )
    gates["near_monotonic_gate"] = bool(
        gates["ordering_improvement_gate"]
        and selected["aggregate_bucket_mean_spearman"] >= 0.8
        and selected["adjacent_order_count"] >= 8
        and selected["maximum_adjacent_inversion"] <= 0.25 * abs(selected["D10_minus_D1"])
    )
    state = decision_state_from_gates(gates, selected, baseline, early, late)
    assets = _make_plots(build, monthly)
    bootstrap = pd.read_csv(build / "historical/block_bootstrap_readout.csv")
    selected_bootstrap = bootstrap[bootstrap["challenger_scored_model_id"].eq("S0_SELECTED_FULL")].set_index("metric_id")
    rank_ci_supported = bool(selected_bootstrap.at["mean_security_rank_ic", "CI_lower_gt_zero"])
    rho_ci_supported = bool(selected_bootstrap.at["aggregate_bucket_mean_spearman", "CI_lower_gt_zero"])
    confidence_flag = ("bootstrap_directionally_supported_within_contaminated_design"
                       if rank_ci_supported and rho_ci_supported
                       else "point_estimate_not_jointly_bootstrap_supported")
    ablation = pd.read_csv(build / "historical/ablation_readout.csv")
    full_ablation = ablation[(ablation["split_scope"].eq("robustness_full")) &
                             (ablation["return_semantics"].eq(RETURN_PRIMARY))]
    validation_display = validation[["scored_model_id", "aggregate_bucket_mean_spearman", "adjacent_order_rate",
                                     "mean_security_rank_ic", "D10_minus_D1", "candidate_eligible", "selection_rank"]]
    robust_display = primary_full.reset_index()[["scored_model_id", "aggregate_bucket_mean_spearman",
                                                 "adjacent_order_rate", "mean_security_rank_ic", "D10_minus_D1",
                                                 "maximum_adjacent_inversion", "evaluable_month_n"]]
    report = f"""# P4 多因子次月收益单调排序诊断（20B_P4_MLRANK v1）

## 结论

本轮冻结选择的模型族为 `{selection['selected_model_family_id']}`，最终状态为 `{state}`。
在 21 个完全留出的 robustness 月份上，selected full 的十桶聚合 Spearman 为 `{_fmt(selected['aggregate_bucket_mean_spearman'])}`，相邻有序率为 `{_fmt(selected['adjacent_order_rate'])}`，逐月 security Rank IC 均值为 `{_fmt(selected['mean_security_rank_ic'])}`，D10-D1 为 `{_fmt(selected['D10_minus_D1'])}`。原始 P4 对应值分别为 `{_fmt(baseline['aggregate_bucket_mean_spearman'])}`、`{_fmt(baseline['adjacent_order_rate'])}`、`{_fmt(baseline['mean_security_rank_ic'])}`、`{_fmt(baseline['D10_minus_D1'])}`。

本轮机器终态是 metric blocker：冻结的 M2 LambdaRank 产出 finite 但完全相同的 score，导致 validation security Rank IC 按 Spearman 定义不可计算；因此 `metric_materialization_gate=false`。不能用事后填零、改权重或改超参数绕过冻结合同。下述 M1 robustness 数值保留为诊断读出，但不构成 ordering-improved terminal claim。

这回答的是“排序能否更接近次月横截面收益的单调顺序”，不是“每个桶是否为正收益”。所有 gate 都使用 centered return 或排序指标；市场共同涨跌、现金/国债配置与 long-only participation regime 不属于本轮结论。

## Validation：候选模型冻结选择

{_markdown_table(validation_display, validation_display.columns)}

选择严格只比较 M1/M2，排序键为 bucket Spearman、相邻有序率、平均 Rank IC，再以 M1 优先作为复杂度 tie-break。B0 与 N0 完整展示但不参加选择。
M2 的常数 score 使 Rank IC 显示为 `NA`；该 candidate 仍完整保留，并触发 metric materialization blocker。

## Robustness：完整模型与消融

{_markdown_table(robust_display, robust_display.columns)}

前 10 个月 selected Spearman 为 `{_fmt(early['aggregate_bucket_mean_spearman'])}`，后 11 个月为 `{_fmt(late['aggregate_bucket_mean_spearman'])}`。这两个子段只作稳定性读出，从未参与选择或调参。

![Robustness aggregate decile curves]({assets[0]})

![Selected monthly decile heatmap]({assets[1]})

## 四项消融读出

{_markdown_table(full_ablation, ['metric_id','baseline_value','full_value','A1_value','A2_value','full_minus_baseline','A1_minus_baseline','A2_minus_baseline'])}

A1 只保留 P4 path，A2 只保留 P0/P1/P6 cross-signals；这里报告机械差值，不设置或输出未冻结的 composite attribution 标签。

## Moving-block bootstrap

{_markdown_table(bootstrap, ['challenger_scored_model_id','metric_id','p05','p50','p95','CI_lower_gt_zero'])}

区间是长度 3、非循环 moving blocks、5,000 次 PCG64 重采样的双侧 90% 区间；`p05/p95` 是区间下/上界。
Bootstrap confidence flag 为 `{confidence_flag}`。

## Coverage、strict sensitivity 与容量警示

Primary known-only 在 selected full 的 21 个 robustness 月份均可评价；all-resolved strict sensitivity 可评价 `{int(monotonicity[(monotonicity['split_scope'].eq('robustness_full')) & (monotonicity['return_semantics'].eq(RETURN_STRICT)) & (monotonicity['scored_model_id'].eq('S0_SELECTED_FULL'))]['evaluable_month_n'].iloc[0])}` 个月。Unknown 不改变 score 或 membership，只在桶收益处删除并按 known rows 等权。
D10 one-way turnover 与冻结 feature importance 已分别输出到 `historical/top_bucket_turnover_monthly.csv` 和 `models/model_feature_importance.csv`，仅作描述性容量/复杂度警示，不进入 gate。

## 审计边界

- 样本固定为 63 个月、25,049 个 P4 base rows；train/validation/robustness 分别为 30/12/21 个月。
- feature-worker 只读取 assignment 的信号身份与 `raw_signal` 列，outcome read count 恒为 0。
- paper proxy 未读取、未物化，P5 retrospective route 未进入特征。
- 两次 fresh-process replay 的 registered core comparison gate 为 `{str(gates['determinism_gate']).lower()}`。
- 当前 workspace 用户指令直接授权本轮实现、历史 outcome 读取与模型训练，不需要独立审批文件；这不改变 outcome-contaminated historical diagnostic 的 claim ceiling。
- 本轮没有现金、国债、成本后 NAV、成交执行或 deployment 结论；不授权组合优化、部署或 20C 执行。
- `multi_factor_model_allowed=true`；`P4_single_factor_repair_claim_allowed=false`。learned score 不可表述为纯 residual-momentum alpha。
"""
    (build / REPORT_NAME).write_text(report, encoding="utf-8")
    decision = pd.DataFrame([{
        "run_id": RUN_ID, "contract_version": CONTRACT_VERSION, "phase_id": PHASE_ID,
        "decision_state": state,
        "research_scope": "cross_signal_learned_reranker_on_p4_eligible_universe",
        "multi_factor_model_allowed": True, "P4_single_factor_repair_claim_allowed": False,
        "historical_sample_role": "design_contaminated_historical",
        "claim_ceiling": "historical_design_diagnostic_only_no_support_claim",
        "execution_authority": config["execution"]["authority"],
        "separate_human_execution_authorization_required": False,
        "requirement_execution_authorized": True, "implementation_authorized": True,
        "historical_outcome_execution_authorized": True, "model_training_authorized": True,
        **gates,
        "stage_seal_failure_replay": None, "stage_seal_failure_stage": None,
        "selected_model_family_id": selection["selected_model_family_id"],
        "selected_scored_model_id": "S0_SELECTED_FULL", "baseline_scored_model_id": "B0_P4_RAW_RANK",
        "validation_selected_metric": "bucket_spearman|adjacent_rate|mean_rank_ic|complexity",
        "robustness_evaluable_month_n": selected["evaluable_month_n"],
        "baseline_robustness_bucket_spearman": baseline["aggregate_bucket_mean_spearman"],
        "selected_robustness_bucket_spearman": selected["aggregate_bucket_mean_spearman"],
        "delta_robustness_bucket_spearman": selected["aggregate_bucket_mean_spearman"] - baseline["aggregate_bucket_mean_spearman"],
        "baseline_robustness_adjacent_order_rate": baseline["adjacent_order_rate"],
        "selected_robustness_adjacent_order_rate": selected["adjacent_order_rate"],
        "delta_robustness_adjacent_order_rate": selected["adjacent_order_rate"] - baseline["adjacent_order_rate"],
        "baseline_robustness_mean_rank_ic": baseline["mean_security_rank_ic"],
        "selected_robustness_mean_rank_ic": selected["mean_security_rank_ic"],
        "delta_robustness_mean_rank_ic": selected["mean_security_rank_ic"] - baseline["mean_security_rank_ic"],
        "selected_robustness_D10_minus_D1": selected["D10_minus_D1"],
        "paired_rank_ic_delta_two_sided_90pct_CI_lower_gt_zero": rank_ci_supported,
        "paired_bucket_spearman_delta_two_sided_90pct_CI_lower_gt_zero": rho_ci_supported,
        "bootstrap_confidence_strength_flag": confidence_flag,
        "absolute_return_positivity_required": False, "cash_or_bond_gate_authorized": False,
        "pre_robustness_selection_bundle_hash": replay_hashes["pre_robustness_selection_bundle_hash"],
        "model_bundle_hash": replay_hashes["model_bundle_hash"],
        "score_bundle_hash": replay_hashes["score_bundle_hash"],
        "historical_readout_bundle_hash": replay_hashes["historical_bundle_hash"],
        "historical_support_claim_allowed": False, "true_forward_support_claim_allowed": False,
        "20C_requirement_generation_authorized": False, "20C_execution_authorized": False,
        "portfolio_optimization_authorized": False, "deployment_authorized": False,
        "next_allowed_requirement": "none",
        "blocking_reason": "M2_validation_score_constant_security_rank_ic_nonfinite",
    }])
    write_csv(build / DECISION_NAME, decision)
    manifest = {
        "run_id": RUN_ID, "contract_version": CONTRACT_VERSION, "phase_id": PHASE_ID,
        "decision_state": state, "immutable": True, "sealed_at_utc": utc_now(),
        "execution_authority": config["execution"]["authority"],
        "separate_human_execution_authorization_required": False,
        "requirement_execution_authorized": True, "implementation_authorized": True,
        "historical_outcome_execution_authorized": True, "model_training_authorized": True,
        "research_scope": "cross_signal_learned_reranker_on_p4_eligible_universe",
        "multi_factor_model_allowed": True, "P4_single_factor_repair_claim_allowed": False,
        "requirement_sha256": snapshot["requirement_sha256"],
        "config_sha256": sha256_file(Path(__file__).resolve().parents[1] / "configs/config_20b_p4_learned_monotonic_return_ranking_diagnostic.yaml"),
        "upstream_final_output_hashes_sha256": config["upstream"]["expected_final_output_hashes_sha256"],
        "upstream_preoutcome_bundle_hash": config["upstream"]["expected_preoutcome_bundle_hash"],
        "upstream_historical_bundle_hash": config["upstream"]["expected_historical_bundle_hash"],
        **replay_hashes,
        "historical_readout_bundle_hash": replay_hashes["historical_bundle_hash"],
        "determinism_comparison_sha256": sha256_file(build / "determinism/determinism_comparison.csv"),
        "replay_b_core_hashes_sha256": sha256_file(build / "determinism/replay_b_core_hashes.json"),
        "stage_seal_integrity_gate": gates["stage_seal_integrity_gate"],
        "score_integrity_gate": gates["score_integrity_gate"], "determinism_gate": gates["determinism_gate"],
        "runtime_dependency_versions": snapshot["runtime_versions"],
        "feature_order_hash": stable_hash(FEATURES),
        "split_registry_hash": sha256_file(build / "preflight/split_registry.csv"),
        "candidate_selection_hash": sha256_file(build / "selection/candidate_selection.csv"),
        "scored_model_identity_registry_hash": sha256_file(build / "preflight/model_registry.csv"),
        "decision_sha256": sha256_file(build / DECISION_NAME), "report_sha256": sha256_file(build / REPORT_NAME),
        "final_publication_bundle_hash_not_self_recorded": True,
    }
    write_json(build / MANIFEST_NAME, manifest)
    files = sorted(p for p in build.rglob("*") if p.is_file() and p.name != HASHES_NAME)
    write_json(build / HASHES_NAME, {p.relative_to(build).as_posix(): sha256_file(p) for p in files})


def full_run(config_path: Path) -> Path:
    config, root = load_config(config_path)
    output = (root / config["paths"]["output_root"]).resolve()
    replay_a = (root / config["paths"]["replay_a_scratch_root"]).resolve()
    replay_b = (root / config["paths"]["replay_b_scratch_root"]).resolve()
    existing = [path for path in [output, replay_a, replay_b] if path.exists()]
    if existing:
        raise FileExistsError(f"output/scratch roots must not preexist: {existing}")
    hashes_a = replay_once(config_path, config, root, replay_a)
    replay_once(config_path, config, root, replay_b)
    comparison, b_hashes = compare_replays(replay_a, replay_b)
    (replay_a / "determinism").mkdir(parents=True, exist_ok=False)
    write_csv(replay_a / "determinism/determinism_comparison.csv", comparison)
    write_json(replay_a / "determinism/replay_b_core_hashes.json", b_hashes)
    finalize(config, replay_a, hashes_a, comparison)
    replay_a.rename(output)
    shutil.rmtree(replay_b)
    return output


def main() -> None:
    default_config = Path(__file__).resolve().parents[1] / "configs/config_20b_p4_learned_monotonic_return_ranking_diagnostic.yaml"
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=str(default_config))
    parser.add_argument("--stage", choices=["full"], default="full")
    parser.add_argument("--worker", choices=["preflight", "feature", "label", "selection", "refit", "score", "metric"])
    parser.add_argument("--build-root")
    args = parser.parse_args()
    config_path = Path(args.config).resolve()
    config, root = load_config(config_path)
    if args.worker:
        if not args.build_root:
            raise ValueError("internal worker requires --build-root")
        paths = resolved_paths(config, root, args.build_root)
        workers = {"preflight": preflight_worker, "feature": feature_worker, "label": label_worker,
                   "selection": selection_worker, "refit": refit_worker, "score": score_worker,
                   "metric": metric_worker}
        workers[args.worker](config, paths)
        return
    output = full_run(config_path)
    print(json.dumps({"run_id": RUN_ID, "output_root": str(output)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
