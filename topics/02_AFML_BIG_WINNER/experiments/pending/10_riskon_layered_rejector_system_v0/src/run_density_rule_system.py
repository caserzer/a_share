#!/usr/bin/env python
from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import re
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
REPO_ROOT = Path(__file__).resolve().parents[5]
SRC_DIR = TOPIC_ROOT / "src"

for import_path in (SRC_DIR, Path(__file__).resolve().parent):
    if str(import_path) not in sys.path:
        sys.path.insert(0, str(import_path))

from afml_big_winner.config import load_yaml, stable_hash  # noqa: E402
from afml_big_winner.manifest import file_sha256  # noqa: E402


CONFIG_PATH = EXPERIMENT_DIR / "config.yaml"
REQUIREMENT_PATH = EXPERIMENT_DIR / "requirement_10a_density_rule_system.md"

TABLE_DIR = EXPERIMENT_DIR / "outputs" / "publishable" / "tables" / "10A_density_rule_system"
REPORT_DIR = EXPERIMENT_DIR / "outputs" / "publishable" / "reports"
LOCAL_CACHE_DIR = EXPERIMENT_DIR / "outputs" / "local_cache" / "10A_density_rule_system"
MANIFEST_DIR = EXPERIMENT_DIR / "outputs" / "manifests"

DECISION_FROZEN = "10A_density_population_frozen"
DECISION_SOURCE_CAVEATED_FROZEN = "10A_density_population_source_caveated_frozen"
DECISION_DIAGNOSTIC = "10A_density_population_diagnostic_only"
DECISION_INPUT_BLOCKED = "10A_density_population_input_blocked"

R_CORE_SCOPE = "08_R_core_event_regime_gated"
R6_SCOPE = "08_R6_event_regime_gated"
E1_SCOPE = "07_E1_only"
R_CORE_INPUT_DENOM = "risk_on_r_core_horizon_complete"
R6_INPUT_DENOM = "risk_on_r6_horizon_complete"
E1_READONLY_INPUT_DENOM = "risk_off_e1_horizon_complete_readonly"
R_CORE_OUTPUT_DENOM = "post_dedup_risk_on_r_core"
R6_OUTPUT_DENOM = "post_dedup_risk_on_r6_readout"
E1_EXCLUDED_DENOM = "excluded_riskoff_e1_readonly"
FAST_FAIL_WEIGHT = "fast_fail_10d"
COST_BAD_WEIGHT = "cost_bad_10_20_20d"

EVENT_LEVEL_E1_STATUS = {
    "episode_level_proxy_from_08_membership",
    "no_episode_membership_for_event",
    "episode_membership_proxy_input_blocked",
}
AGG_E1_STATUS_BLOCKED = "episode_membership_proxy_input_blocked"
AGG_E1_STATUS_MIXED = "mixed_non_blocking"
AGG_E1_STATUS_ALL_MEMBERSHIP = "all_episode_level_proxy_from_08_membership"
AGG_E1_STATUS_ALL_NO_MEMBERSHIP = "all_no_episode_membership_for_event"

JOIN_KEY = ["sample_id", "selected_target_id", "input_denominator_id", "canonical_event_id"]
FEATURE_KEY_09B = ["sample_id", "selected_target_id", "denominator_id", "canonical_event_id"]

OUTPUT_BINDING_COLUMNS = [
    "population_id",
    "rule_arm_id",
    "input_event_key",
    "sample_id",
    "selected_target_id",
    "input_denominator_id",
    "denominator_id",
    "split",
    "instrument",
    "event_t0_date",
    "event_t0_pos",
    "event_window_anchor_date",
    "event_window_anchor_pos",
    "event_window_anchor_status",
    "source_pool_id",
    "source_family_id",
    "mechanism_id",
    "source_family_id_set",
    "event_regime_bucket",
    "raw_event_status",
    "admission_status",
    "readout_only_flag",
    "admitted_event_id",
    "representative_sample_id",
    "suppressed_by_sample_id",
    "suppression_reason",
    "selected_fast_fail_10_label",
    "frozen_false_repair_20d_label",
    "selected_cost_bad_10_20_target",
    "winner_120",
    "E1_missed_winner_flag",
    "e1_episode_hit_flag",
    "e1_missed_proxy_flag",
    "e1_missed_proxy_status",
    "feature_matrix_join_key",
    "fast_fail_sample_weight_join_key",
    "cost_bad_sample_weight_join_key",
]


@dataclass(frozen=True)
class RuleArm:
    rule_arm_id: str
    rule_arm_type: str
    window_sessions: int
    cap: int
    required_field: str | None

    @property
    def population_id(self) -> str:
        return f"10A__{self.rule_arm_id}"


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


def parse_arms(config: dict[str, Any]) -> list[RuleArm]:
    return [
        RuleArm(
            rule_arm_id=str(row["rule_arm_id"]),
            rule_arm_type=str(row["rule_arm_type"]),
            window_sessions=int(row["window_sessions"]),
            cap=int(row["cap"]),
            required_field=(
                str(row["required_field"]) if row.get("required_field") not in {None, ""} else None
            ),
        )
        for row in config["rule_arms"]
    ]


def boolish(value: Any) -> bool:
    if pd.isna(value):
        return False
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    if isinstance(value, (int, float, np.integer, np.floating)):
        return bool(value)
    return str(value).strip().lower() in {"true", "1", "yes", "y", "t"}


def stable_str(value: Any) -> str:
    if pd.isna(value):
        return ""
    return str(value)


def make_composite_key(frame: pd.DataFrame, cols: list[str]) -> pd.Series:
    return frame[cols].map(stable_str).agg("|".join, axis=1)


def random_tie_hash(input_event_key: str, capacity_id: str, random_seed: int) -> str:
    return hashlib.sha256(f"{input_event_key}{capacity_id}{random_seed}".encode("utf-8")).hexdigest()


def normalize_mechanism(value: Any) -> str | None:
    if pd.isna(value):
        return None
    tokens = [token.strip() for token in re.split(r"[;|,]", str(value)) if token.strip()]
    if not tokens:
        return None
    return ";".join(sorted(set(tokens)))


def read_required_inputs(config: dict[str, Any]) -> tuple[dict[str, Path], dict[str, Any]]:
    paths = {key: resolve_path(value) for key, value in config["paths"].items()}
    hard_inputs = [
        "upstream_09a_manifest",
        "upstream_09b_manifest",
        "upstream_09c_manifest",
        "upstream_09a_bindings",
        "upstream_09b_feature_matrix",
        "upstream_09b_sample_weights",
        "upstream_08_canonical_events",
        "upstream_08_event_instances",
        "upstream_08_density_caliber_contract",
        "upstream_08_scope_mapping_contract",
        "upstream_08_scope_reconstructability_audit",
        "upstream_08_post_replay_label_leakage_audit",
    ]
    missing = [name for name in hard_inputs if not paths[name].is_file()]
    if missing:
        raise FileNotFoundError(f"missing hard inputs: {missing}")

    loaded: dict[str, Any] = {
        "manifest_09a": json.loads(paths["upstream_09a_manifest"].read_text(encoding="utf-8")),
        "manifest_09b": json.loads(paths["upstream_09b_manifest"].read_text(encoding="utf-8")),
        "manifest_09c": json.loads(paths["upstream_09c_manifest"].read_text(encoding="utf-8")),
        "binding_09a": pd.read_parquet(paths["upstream_09a_bindings"]),
        "feature_matrix": pd.read_parquet(paths["upstream_09b_feature_matrix"]),
        "sample_weights": pd.read_parquet(paths["upstream_09b_sample_weights"]),
        "canonical_events": pd.read_csv(paths["upstream_08_canonical_events"], low_memory=False),
    }
    loaded["event_instances_head"] = pd.read_csv(paths["upstream_08_event_instances"], nrows=1, low_memory=False)
    loaded["scope_mapping_head"] = pd.read_csv(paths["upstream_08_scope_mapping_contract"], nrows=1)
    loaded["scope_reconstructability_head"] = pd.read_csv(
        paths["upstream_08_scope_reconstructability_audit"], nrows=1
    )
    loaded["post_replay_label_leakage_head"] = pd.read_csv(
        paths["upstream_08_post_replay_label_leakage_audit"], nrows=1
    )
    loaded["density_caliber_contract_text"] = paths["upstream_08_density_caliber_contract"].read_text(
        encoding="utf-8"
    )
    if paths.get("upstream_09b_feature_contract", Path()).is_file():
        loaded["feature_contract"] = pd.read_csv(paths["upstream_09b_feature_contract"])
    else:
        loaded["feature_contract"] = pd.DataFrame()
    return paths, loaded


def source_caveated(manifest_09a: dict[str, Any]) -> bool:
    return str(manifest_09a.get("decision", "")) == "09A_label_frontier_candidate_source_caveated_selected"


def manifest_expected_hash(manifest: dict[str, Any], field_name: str, output_key: str) -> str | None:
    value = manifest.get(field_name)
    if value:
        return str(value)
    output_hashes = manifest.get("output_hashes", {})
    if isinstance(output_hashes, dict) and output_hashes.get(output_key):
        return str(output_hashes[output_key])
    return None


def validate_upstream_hashes(paths: dict[str, Path], loaded: dict[str, Any]) -> list[str]:
    checks = [
        (
            "09a_selected_label_event_bindings",
            loaded["manifest_09a"],
            "selected_label_event_bindings_hash",
            "selected_label_event_bindings",
            paths["upstream_09a_bindings"],
        ),
        (
            "09b_feature_matrix",
            loaded["manifest_09b"],
            "feature_matrix_hash",
            "feature_matrix",
            paths["upstream_09b_feature_matrix"],
        ),
        (
            "09b_sample_uniqueness_weights",
            loaded["manifest_09b"],
            "sample_uniqueness_weights_hash",
            "sample_uniqueness_weights",
            paths["upstream_09b_sample_weights"],
        ),
        (
            "09b_feature_contract",
            loaded["manifest_09b"],
            "selected_feature_contract_hash",
            "feature_contract",
            paths["upstream_09b_feature_contract"],
        ),
    ]
    failures: list[str] = []
    for label, manifest, field_name, output_key, path in checks:
        expected = manifest_expected_hash(manifest, field_name, output_key)
        if not expected:
            failures.append(f"missing_manifest_hash:{label}")
            continue
        actual = file_sha256(path)
        if actual != expected:
            failures.append(f"manifest_hash_mismatch:{label}")
    return failures


def scope_treatment(binding: pd.DataFrame) -> pd.DataFrame:
    scoped = binding.copy()
    scoped["input_denominator_id"] = scoped["denominator_id"].astype(str)
    scoped["split"] = scoped["event_split"].astype(str)

    conditions = [
        (
            scoped["event_regime_bucket"].eq("risk_on")
            & scoped["source_pool_id"].eq(R_CORE_SCOPE)
            & scoped["input_denominator_id"].eq(R_CORE_INPUT_DENOM)
        ),
        (
            scoped["event_regime_bucket"].eq("risk_on")
            & scoped["source_pool_id"].eq(R6_SCOPE)
            & scoped["input_denominator_id"].eq(R6_INPUT_DENOM)
        ),
        (
            scoped["event_regime_bucket"].eq("risk_off")
            & scoped["source_pool_id"].eq(E1_SCOPE)
            & scoped["input_denominator_id"].eq(E1_READONLY_INPUT_DENOM)
        ),
    ]
    scoped["scope_treatment"] = np.select(
        conditions,
        ["materialize", "materialize_readout_only", "exclude_riskoff_e1_readonly"],
        default="input_blocked_unexpected_scope",
    )
    scoped["output_denominator_id"] = np.select(
        conditions,
        [R_CORE_OUTPUT_DENOM, R6_OUTPUT_DENOM, E1_EXCLUDED_DENOM],
        default="n/a",
    )
    scoped["readout_only_flag"] = np.select(conditions, [False, True, True], default=True)
    return scoped


def build_input_scope_exclusion_audit(scoped: pd.DataFrame) -> pd.DataFrame:
    excluded = scoped.loc[scoped["scope_treatment"].ne("materialize") & scoped["scope_treatment"].ne("materialize_readout_only")]
    if excluded.empty:
        return pd.DataFrame(
            columns=[
                "input_denominator_id",
                "source_pool_id",
                "event_regime_bucket",
                "excluded_row_n",
                "excluded_unique_sample_n",
                "exclusion_reason",
                "feature_matrix_join_attempted_flag",
                "sample_weight_join_attempted_flag",
                "post_dedup_materialized_flag",
            ]
        )
    rows = []
    for keys, group in excluded.groupby(["input_denominator_id", "source_pool_id", "event_regime_bucket"], dropna=False):
        reason = (
            "excluded_riskoff_e1_readonly"
            if group["scope_treatment"].eq("exclude_riskoff_e1_readonly").all()
            else "input_blocked_unexpected_scope"
        )
        rows.append(
            {
                "input_denominator_id": keys[0],
                "source_pool_id": keys[1],
                "event_regime_bucket": keys[2],
                "excluded_row_n": int(len(group)),
                "excluded_unique_sample_n": int(group["sample_id"].nunique(dropna=True)),
                "exclusion_reason": reason,
                "feature_matrix_join_attempted_flag": False,
                "sample_weight_join_attempted_flag": False,
                "post_dedup_materialized_flag": False,
            }
        )
    return pd.DataFrame(rows)


def validate_scope(scoped: pd.DataFrame) -> list[str]:
    if scoped["scope_treatment"].eq("input_blocked_unexpected_scope").any():
        return ["unexpected_scope_combination"]
    return []


def validate_and_join_features(base: pd.DataFrame, feature_matrix: pd.DataFrame, feature_cols: list[str]) -> tuple[pd.DataFrame, list[str]]:
    failures: list[str] = []
    required = set(FEATURE_KEY_09B + ["event_split", *feature_cols])
    missing_cols = sorted(required - set(feature_matrix.columns))
    if missing_cols:
        return base, [f"feature_matrix_missing_columns:{','.join(missing_cols)}"]

    dupes = int(feature_matrix.duplicated(FEATURE_KEY_09B).sum())
    if dupes:
        failures.append(f"feature_matrix_duplicate_join_key:{dupes}")

    right_cols = FEATURE_KEY_09B + ["event_split", *feature_cols]
    right = feature_matrix[right_cols].rename(
        columns={"denominator_id": "input_denominator_id", "event_split": "event_split_09b"}
    )
    joined = base.merge(right, on=JOIN_KEY, how="left", indicator=True, validate="m:1")
    joined["feature_matrix_joined_flag"] = joined["_merge"].eq("both")
    missing = int(joined["_merge"].ne("both").sum())
    if missing:
        failures.append(f"feature_matrix_missing_join:{missing}")
    split_mismatch = int(
        joined["feature_matrix_joined_flag"].sum()
        - joined.loc[joined["feature_matrix_joined_flag"], "split"].eq(
            joined.loc[joined["feature_matrix_joined_flag"], "event_split_09b"].astype(str)
        ).sum()
    )
    if split_mismatch:
        failures.append(f"feature_matrix_event_split_mismatch:{split_mismatch}")
    joined = joined.drop(columns=["_merge"])
    return joined, failures


def validate_and_join_weights(base: pd.DataFrame, weights: pd.DataFrame, horizon_id: str, flag_col: str) -> tuple[pd.DataFrame, list[str]]:
    required = set(FEATURE_KEY_09B + ["weight_horizon_id"])
    missing_cols = sorted(required - set(weights.columns))
    if missing_cols:
        return base, [f"sample_weights_missing_columns:{','.join(missing_cols)}"]

    part = weights.loc[weights["weight_horizon_id"].eq(horizon_id)].copy()
    failures: list[str] = []
    dupes = int(part.duplicated(FEATURE_KEY_09B + ["weight_horizon_id"]).sum())
    if dupes:
        failures.append(f"sample_weight_duplicate_join_key:{horizon_id}:{dupes}")
    right = part[FEATURE_KEY_09B + ["weight_horizon_id"]].rename(columns={"denominator_id": "input_denominator_id"})
    joined = base.merge(right, on=JOIN_KEY, how="left", indicator=True, validate="m:1")
    joined[flag_col] = joined["_merge"].eq("both")
    missing = int(joined["_merge"].ne("both").sum())
    if missing:
        failures.append(f"sample_weight_missing_join:{horizon_id}:{missing}")
    joined = joined.drop(columns=["_merge", "weight_horizon_id"])
    return joined, failures


def build_base_events(
    scoped: pd.DataFrame,
    canonical_events: pd.DataFrame,
    feature_matrix: pd.DataFrame,
    weights: pd.DataFrame,
    membership_path: Path,
    feature_cols: list[str],
) -> tuple[pd.DataFrame, list[str], str]:
    materializable = scoped.loc[scoped["scope_treatment"].isin(["materialize", "materialize_readout_only"])].copy()
    materializable["denominator_id"] = materializable["output_denominator_id"].astype(str)
    materializable["readout_only_flag"] = materializable["readout_only_flag"].map(bool)
    for col in ["sample_id", "selected_target_id", "input_denominator_id", "canonical_event_id"]:
        if col not in materializable.columns:
            return materializable, [f"binding_missing_required_column:{col}"], "not_run"
        if materializable[col].isna().any() or materializable[col].astype(str).eq("").any():
            return materializable, [f"binding_null_required_column:{col}"], "not_run"
    materializable["input_event_key"] = make_composite_key(materializable, JOIN_KEY)
    if materializable["input_event_key"].duplicated().any():
        return materializable, ["input_event_key_not_unique"], "not_run"

    canonical_required = [
        "canonical_event_id",
        "event_t0_pos",
        "trade_open_pos",
        "trade_open_date",
        "non_executable_next_open",
        "primary_family_id",
        "triggered_family_ids",
        "triggered_mechanism_clusters",
    ]
    missing_can = sorted(set(canonical_required) - set(canonical_events.columns))
    if missing_can:
        return materializable, [f"canonical_events_missing_columns:{','.join(missing_can)}"], "not_run"
    if canonical_events["canonical_event_id"].duplicated().any():
        return materializable, ["canonical_event_id_not_unique"], "not_run"

    can = canonical_events[canonical_required].copy()
    can = can.rename(
        columns={
            "primary_family_id": "source_family_id",
            "triggered_family_ids": "source_family_id_set",
        }
    )
    base = materializable.merge(can, on="canonical_event_id", how="left", indicator=True, validate="m:1")
    missing_can_join = int(base["_merge"].ne("both").sum())
    if missing_can_join:
        return base.drop(columns=["_merge"]), [f"canonical_events_missing_join:{missing_can_join}"], "not_run"
    base = base.drop(columns=["_merge"])

    base["mechanism_id"] = base["triggered_mechanism_clusters"].map(normalize_mechanism)
    base["non_executable_next_open_bool"] = base["non_executable_next_open"].map(boolish)
    executable = (~base["non_executable_next_open_bool"]) & base["trade_open_pos"].notna()
    base["event_window_anchor_pos"] = np.where(executable, base["trade_open_pos"], base["event_t0_pos"])
    base["event_window_anchor_date"] = np.where(executable, base["trade_open_date"], base["event_t0_date"])
    base["event_window_anchor_status"] = np.where(
        executable, "executable_trade_open", "non_executable_t0_fallback"
    )
    base["raw_event_status"] = np.where(executable, "executable", "non_executable_audit_only")
    base["winner_120"] = base["event_big_winner_120d_label"].map(boolish)
    base["feature_matrix_join_key"] = make_composite_key(base, JOIN_KEY)
    base["fast_fail_sample_weight_join_key"] = base["feature_matrix_join_key"] + f"|{FAST_FAIL_WEIGHT}"
    base["cost_bad_sample_weight_join_key"] = base["feature_matrix_join_key"] + f"|{COST_BAD_WEIGHT}"

    base, failures = validate_and_join_features(base, feature_matrix, feature_cols)
    base, weight_failures = validate_and_join_weights(base, weights, FAST_FAIL_WEIGHT, "fast_fail_weight_joined_flag")
    failures.extend(weight_failures)
    base, weight_failures = validate_and_join_weights(base, weights, COST_BAD_WEIGHT, "cost_bad_weight_joined_flag")
    failures.extend(weight_failures)
    if failures:
        return base, failures, "not_run"

    base, e1_status = attach_e1_readout(base, membership_path)
    base["selected_fast_fail_10_label_bool"] = base["selected_fast_fail_10_label"].map(boolish)
    base["frozen_false_repair_20d_label_bool"] = base["frozen_false_repair_20d_label"].map(boolish)
    base["selected_cost_bad_10_20_target_bool"] = base["selected_cost_bad_10_20_target"].map(boolish)
    return base, [], e1_status


def attach_e1_readout(base: pd.DataFrame, membership_path: Path) -> tuple[pd.DataFrame, str]:
    required = {
        "canonical_event_id",
        "candidate_scope_id",
        "target_episode_id",
        "bridge_positive_denominator_included",
    }
    out = base.copy()
    try:
        membership = pd.read_parquet(membership_path)
    except Exception:
        out["e1_episode_hit_flag"] = pd.NA
        out["e1_missed_proxy_flag"] = pd.NA
        out["E1_missed_winner_flag"] = pd.NA
        out["e1_missed_proxy_status"] = AGG_E1_STATUS_BLOCKED
        return out, "episode_membership_proxy_input_blocked"
    if not required.issubset(set(membership.columns)):
        out["e1_episode_hit_flag"] = pd.NA
        out["e1_missed_proxy_flag"] = pd.NA
        out["E1_missed_winner_flag"] = pd.NA
        out["e1_missed_proxy_status"] = AGG_E1_STATUS_BLOCKED
        return out, "episode_membership_proxy_input_blocked"

    mem = membership[list(required)].copy()
    mem["canonical_event_id"] = mem["canonical_event_id"].astype(str)
    e1_ref = set(
        mem.loc[
            mem["candidate_scope_id"].astype(str).eq(E1_SCOPE)
            & mem["target_episode_id"].notna()
            & mem["bridge_positive_denominator_included"].map(boolish),
            "target_episode_id",
        ].astype(str)
    )
    has_membership = set(mem["canonical_event_id"].dropna().astype(str))
    hit_events = set(
        mem.loc[mem["target_episode_id"].astype(str).isin(e1_ref), "canonical_event_id"]
        .dropna()
        .astype(str)
    )
    canonical = out["canonical_event_id"].astype(str)
    has_mem = canonical.isin(has_membership)
    hit = canonical.isin(hit_events)
    out["e1_episode_hit_flag"] = np.where(has_mem, hit, False)
    out["e1_missed_proxy_flag"] = ~out["e1_episode_hit_flag"].map(boolish)
    out["E1_missed_winner_flag"] = out["winner_120"].map(boolish) & out["e1_missed_proxy_flag"].map(boolish)
    out["e1_missed_proxy_status"] = np.where(
        has_mem,
        "episode_level_proxy_from_08_membership",
        "no_episode_membership_for_event",
    )
    return out, "episode_level_proxy_from_08_membership"


def arm_block_reason(base: pd.DataFrame, arm: RuleArm) -> tuple[str, str]:
    if arm.required_field is None:
        return "materialized", ""
    missing = base[arm.required_field].isna() | base[arm.required_field].astype(str).eq("")
    if missing.any():
        return "input_blocked", f"missing_{arm.required_field}_row_n={int(missing.sum())}"
    return "materialized", ""


def materialize_arm(base: pd.DataFrame, arm: RuleArm, arm_status: str) -> pd.DataFrame:
    rows = base.copy()
    rows["population_id"] = arm.population_id
    rows["rule_arm_id"] = arm.rule_arm_id
    if arm_status != "materialized":
        rows["admission_status"] = "arm_input_blocked"
        rows["admitted_event_id"] = pd.NA
        rows["representative_sample_id"] = pd.NA
        rows["suppressed_by_sample_id"] = pd.NA
        rows["suppression_reason"] = "arm_input_blocked"
        return rows

    rows["admission_status"] = np.where(
        rows["raw_event_status"].eq("non_executable_audit_only"),
        "non_executable_audit_only",
        "pending",
    )
    rows["admitted_event_id"] = pd.NA
    rows["representative_sample_id"] = pd.NA
    rows["suppressed_by_sample_id"] = pd.NA
    rows["suppression_reason"] = np.where(
        rows["admission_status"].eq("non_executable_audit_only"),
        "non_executable_next_open",
        "",
    )

    group_cols = ["split", "denominator_id", "instrument"]
    if arm.rule_arm_type == "same_family_dedup":
        group_cols.append("source_family_id")
    elif arm.rule_arm_type == "same_mechanism_dedup":
        group_cols.append("mechanism_id")

    sort_cols = group_cols + ["event_window_anchor_pos", "event_t0_date", "sample_id", "input_event_key"]
    sorted_rows = rows.sort_values(sort_cols, kind="mergesort")

    for _, group in sorted_rows.groupby(group_cols, dropna=False, sort=False):
        admitted: list[tuple[float, str, str]] = []
        for idx, row in group.iterrows():
            if row["admission_status"] == "non_executable_audit_only":
                continue
            anchor = float(row["event_window_anchor_pos"])
            inside_window = [item for item in admitted if anchor <= item[0] + arm.window_sessions]
            if inside_window:
                representative = inside_window[0]
                rows.at[idx, "admission_status"] = "suppressed_by_density_rule"
                rows.at[idx, "admitted_event_id"] = representative[1]
                rows.at[idx, "representative_sample_id"] = representative[2]
                rows.at[idx, "suppressed_by_sample_id"] = representative[2]
                rows.at[idx, "suppression_reason"] = f"{arm.rule_arm_id}_window"
            else:
                event_key = str(row["input_event_key"])
                sample_id = str(row["sample_id"])
                admitted.append((anchor, event_key, sample_id))
                rows.at[idx, "admission_status"] = "admitted"
                rows.at[idx, "admitted_event_id"] = event_key
                rows.at[idx, "representative_sample_id"] = sample_id
                rows.at[idx, "suppression_reason"] = "not_suppressed"
    return rows


def build_rule_arm_contract(base: pd.DataFrame, arms: list[RuleArm], statuses: dict[str, tuple[str, str]]) -> pd.DataFrame:
    rows = []
    for arm in arms:
        status, reason = statuses[arm.rule_arm_id]
        rows.append(
            {
                "population_id": arm.population_id,
                "rule_arm_id": arm.rule_arm_id,
                "rule_arm_type": arm.rule_arm_type,
                "window_sessions": arm.window_sessions,
                "cap": arm.cap,
                "uses_score_flag": False,
                "admission_order_key": "event_window_anchor_pos,event_t0_date,sample_id,input_event_key",
                "tie_break_key": "input_event_key",
                "execution_anchor_policy": "trade_open_pos_else_event_t0_pos",
                "non_executable_policy": "audit_only_not_admitted",
                "arm_status": status,
                "arm_block_reason": reason,
            }
        )
    return pd.DataFrame(rows)


def build_event_bindings(base: pd.DataFrame, arms: list[RuleArm]) -> tuple[pd.DataFrame, pd.DataFrame]:
    statuses = {arm.rule_arm_id: arm_block_reason(base, arm) for arm in arms}
    materialized = [materialize_arm(base, arm, statuses[arm.rule_arm_id][0]) for arm in arms]
    all_rows = pd.concat(materialized, ignore_index=True)
    contract = build_rule_arm_contract(base, arms, statuses)
    return all_rows, contract


def group_keys() -> list[str]:
    return [
        "population_id",
        "rule_arm_id",
        "input_denominator_id",
        "denominator_id",
        "split",
        "readout_only_flag",
    ]


def aggregate_e1_status(statuses: pd.Series) -> str:
    values = set(statuses.dropna().astype(str))
    if not values:
        return AGG_E1_STATUS_MIXED
    if AGG_E1_STATUS_BLOCKED in values:
        return AGG_E1_STATUS_BLOCKED
    if values == {"episode_level_proxy_from_08_membership"}:
        return AGG_E1_STATUS_ALL_MEMBERSHIP
    if values == {"no_episode_membership_for_event"}:
        return AGG_E1_STATUS_ALL_NO_MEMBERSHIP
    return AGG_E1_STATUS_MIXED


def build_sample_count(bindings: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for keys, group in bindings.groupby(group_keys(), dropna=False):
        admitted = group.loc[group["admission_status"].eq("admitted")]
        rows.append(
            {
                **dict(zip(group_keys(), keys, strict=True)),
                "input_row_n": int(len(group)),
                "eligible_risk_on_row_n": int(len(group)),
                "admitted_event_n": int(len(admitted)),
                "suppressed_event_n": int(group["admission_status"].eq("suppressed_by_density_rule").sum()),
                "non_executable_audit_only_n": int(group["admission_status"].eq("non_executable_audit_only").sum()),
                "unique_sample_n": int(admitted["sample_id"].nunique(dropna=True)),
                "unique_instrument_n": int(admitted["instrument"].nunique(dropna=True)),
                "feature_matrix_joined_n": int(group["feature_matrix_joined_flag"].map(boolish).sum()),
                "fast_fail_weight_joined_n": int(group["fast_fail_weight_joined_flag"].map(boolish).sum()),
                "cost_bad_weight_joined_n": int(group["cost_bad_weight_joined_flag"].map(boolish).sum()),
                "sample_count_status": "pass"
                if not group["admission_status"].eq("arm_input_blocked").all()
                else "arm_input_blocked",
            }
        )
    return pd.DataFrame(rows)


def label_nonnull_count(series: pd.Series) -> int:
    return int(series.notna().sum())


def build_label_coverage(bindings: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for keys, group in bindings.groupby(group_keys(), dropna=False):
        admitted = group.loc[group["admission_status"].eq("admitted")]
        admitted_n = int(len(admitted))
        required_counts = {
            "selected_fast_fail_10_label_nonnull_n": label_nonnull_count(admitted["selected_fast_fail_10_label"]),
            "frozen_false_repair_20d_label_nonnull_n": label_nonnull_count(admitted["frozen_false_repair_20d_label"]),
            "selected_cost_bad_10_20_target_nonnull_n": label_nonnull_count(admitted["selected_cost_bad_10_20_target"]),
            "winner_120_nonnull_n": label_nonnull_count(admitted["winner_120"]),
            "E1_missed_winner_flag_nonnull_n": label_nonnull_count(admitted["E1_missed_winner_flag"]),
        }
        status = "pass" if all(value == admitted_n for value in required_counts.values()) else "partial"
        rows.append(
            {
                **dict(zip(group_keys(), keys, strict=True)),
                "admitted_event_n": admitted_n,
                "horizon_complete_10d_n": int(admitted["horizon_complete_10d"].map(boolish).sum()),
                "horizon_complete_20d_n": int(admitted["horizon_complete_20d"].map(boolish).sum()),
                "horizon_complete_120d_n": int(admitted["horizon_complete_120d"].map(boolish).sum()),
                **required_counts,
                "e1_missed_proxy_status": aggregate_e1_status(admitted["e1_missed_proxy_status"]),
                "e1_status_episode_level_proxy_from_08_membership_n": int(
                    admitted["e1_missed_proxy_status"].astype(str).eq("episode_level_proxy_from_08_membership").sum()
                ),
                "e1_status_no_episode_membership_for_event_n": int(
                    admitted["e1_missed_proxy_status"].astype(str).eq("no_episode_membership_for_event").sum()
                ),
                "e1_status_episode_membership_proxy_input_blocked_n": int(
                    admitted["e1_missed_proxy_status"].astype(str).eq(AGG_E1_STATUS_BLOCKED).sum()
                ),
                "label_coverage_status": status,
            }
        )
    return pd.DataFrame(rows)


def rolling_density(positions: pd.Series, window: int) -> float:
    vals = sorted(pd.to_numeric(positions, errors="coerce").dropna().astype(float).tolist())
    if not vals:
        return 0.0
    left = 0
    max_count = 0
    for right, value in enumerate(vals):
        while vals[left] < value - window:
            left += 1
        max_count = max(max_count, right - left + 1)
    return float(max_count / window)


def build_density_audit(bindings: pd.DataFrame) -> pd.DataFrame:
    keys = group_keys() + ["instrument"]
    rows = []
    for key_values, group in bindings.groupby(keys, dropna=False):
        admitted = group.loc[group["admission_status"].eq("admitted")]
        daily_counts = admitted.groupby("event_window_anchor_date", dropna=False).size()
        event_day_n = int(admitted["event_window_anchor_date"].nunique(dropna=True))
        admitted_n = int(len(admitted))
        rows.append(
            {
                **dict(zip(keys, key_values, strict=True)),
                "event_day_n": event_day_n,
                "admitted_event_n": admitted_n,
                "suppressed_event_n": int(group["admission_status"].eq("suppressed_by_density_rule").sum()),
                "formal_event_day_density": float(admitted_n / event_day_n) if event_day_n else 0.0,
                "p50_density": float(daily_counts.quantile(0.50)) if not daily_counts.empty else 0.0,
                "p95_density": float(daily_counts.quantile(0.95)) if not daily_counts.empty else 0.0,
                "max_density": float(daily_counts.max()) if not daily_counts.empty else 0.0,
                "rolling_10d_executable_event_day_density": rolling_density(
                    admitted["event_window_anchor_pos"], 10
                ),
                "rolling_20d_executable_event_day_density": rolling_density(
                    admitted["event_window_anchor_pos"], 20
                ),
                "density_audit_status": "pass",
            }
        )
    return pd.DataFrame(rows)


def build_population_contract(bindings: pd.DataFrame, density: pd.DataFrame) -> pd.DataFrame:
    density_group = (
        density.groupby(group_keys(), dropna=False)
        .agg(
            formal_event_day_density=("formal_event_day_density", "mean"),
            p95_density=("p95_density", "max"),
            rolling_10d_executable_event_day_density=("rolling_10d_executable_event_day_density", "max"),
            rolling_20d_executable_event_day_density=("rolling_20d_executable_event_day_density", "max"),
        )
        .reset_index()
    )
    rows = []
    for keys, group in bindings.groupby(group_keys(), dropna=False):
        admitted = group.loc[group["admission_status"].eq("admitted")]
        fast_fail = admitted["selected_fast_fail_10_label_bool"].map(boolish)
        winner = admitted["winner_120"].map(boolish)
        row = {
            **dict(zip(group_keys(), keys, strict=True)),
            "sample_n": int(len(admitted)),
            "evaluable_event_n": int(len(admitted)),
            "admitted_event_n": int(len(admitted)),
            "suppressed_event_n": int(group["admission_status"].eq("suppressed_by_density_rule").sum()),
            "non_executable_audit_only_n": int(group["admission_status"].eq("non_executable_audit_only").sum()),
            "winner_n": int(winner.sum()),
            "E1_missed_winner_n": int(admitted["E1_missed_winner_flag"].map(boolish).sum()),
            "fast_fail_positive_n": int(fast_fail.sum()),
            "fast_fail_winner_n": int((fast_fail & winner).sum()),
            "false_repair_positive_n": int(admitted["frozen_false_repair_20d_label_bool"].map(boolish).sum()),
            "hybrid_positive_n": int(admitted["selected_cost_bad_10_20_target_bool"].map(boolish).sum()),
            "unique_instrument_n": int(admitted["instrument"].nunique(dropna=True)),
            "unique_event_day_n": int(admitted["event_window_anchor_date"].nunique(dropna=True)),
        }
        rows.append(row)
    out = pd.DataFrame(rows)
    return out.merge(density_group, on=group_keys(), how="left")


def power_audit_config(config: dict[str, Any]) -> pd.DataFrame:
    seed = int(config.get("defaults", {}).get("random_seed", 20260615))
    features = ";".join(config["structural_swing_low_rank_v1_required_features"])
    rows = []
    for keep in [9000, 9250, 9300, 9400, 9500, 9600, 9700]:
        rows.append(
            {
                "component_id": "fast_fail_10d",
                "capacity_id": f"keep_{keep}",
                "threshold_id": f"keep_{keep}",
                "reject_fraction": round((10000 - keep) / 10000, 4),
                "random_seed": seed,
                "random_tie_break_key": "sha256_input_event_key_capacity_seed",
                "rule_baseline_id": "structural_swing_low_rank_v1",
                "rule_baseline_owner": "10B",
                "rule_baseline_required_features": features,
                "min_positive_count": 100,
                "min_winner_count": 20,
                "min_rule_positive_count": 10,
                "min_rule_winner_count": 3,
                "capture_lift_margin": 0.0200,
                "winner_retention_floor": 0.9400,
                "wrong_kill_rate_cap": 0.0600,
            }
        )
    for keep in [8000, 8250, 8500, 8750, 9000]:
        rows.append(
            {
                "component_id": "false_repair_20d_component",
                "capacity_id": f"keep_{keep}",
                "threshold_id": f"keep_{keep}",
                "reject_fraction": round((10000 - keep) / 10000, 4),
                "random_seed": seed,
                "random_tie_break_key": "sha256_input_event_key_capacity_seed",
                "rule_baseline_id": "none",
                "rule_baseline_owner": "10C",
                "rule_baseline_required_features": "none",
                "min_positive_count": 300,
                "min_winner_count": 100,
                "min_rule_positive_count": 0,
                "min_rule_winner_count": 0,
                "capture_lift_margin": 0.0000,
                "winner_retention_floor": 0.8500,
                "wrong_kill_rate_cap": 0.1500,
            }
        )
    return pd.DataFrame(rows)


def feature_contract_status(feature_contract: pd.DataFrame, required_features: list[str], bindings: pd.DataFrame) -> str:
    if feature_contract.empty:
        return "input_blocked"
    for feature in required_features:
        matches = feature_contract.loc[feature_contract["feature_id"].astype(str).eq(feature)]
        if len(matches) != 1:
            return "input_blocked"
        if not boolish(matches["allowed_for_09C_flag"].iloc[0]):
            return "input_blocked"
        if feature not in bindings.columns:
            return "input_blocked"
    return "pass"


def rejected_by_random(admitted: pd.DataFrame, row: pd.Series) -> pd.DataFrame:
    if admitted.empty:
        return admitted
    n = int(math.ceil(len(admitted) * float(row["reject_fraction"])))
    temp = admitted.copy()
    seed = int(row["random_seed"])
    cap = str(row["capacity_id"])
    temp["_random_rank_key"] = temp["input_event_key"].map(lambda key: random_tie_hash(str(key), cap, seed))
    temp = temp.sort_values(["_random_rank_key", "input_event_key"], kind="mergesort")
    return temp.head(n)


def rejected_by_structural(admitted: pd.DataFrame, row: pd.Series, rule_status: str, required_features: list[str]) -> pd.DataFrame:
    if admitted.empty or rule_status != "pass":
        return admitted.head(0)
    n = int(math.ceil(len(admitted) * float(row["reject_fraction"])))
    sort_cols = required_features + ["input_event_key"]
    ascending = [True, True, True, True, False, True]
    return admitted.sort_values(sort_cols, ascending=ascending, na_position="last", kind="mergesort").head(n)


def build_fast_fail_power_audit(
    bindings: pd.DataFrame,
    config_df: pd.DataFrame,
    feature_contract: pd.DataFrame,
    required_features: list[str],
) -> pd.DataFrame:
    cfg = config_df.loc[config_df["component_id"].eq("fast_fail_10d")]
    rule_status = feature_contract_status(feature_contract, required_features, bindings)
    rows = []
    for keys, group in bindings.groupby(group_keys(), dropna=False):
        admitted = group.loc[group["admission_status"].eq("admitted")].copy()
        post_positive = int(admitted["selected_fast_fail_10_label_bool"].map(boolish).sum())
        post_winner = int(admitted["winner_120"].map(boolish).sum())
        post_fast_fail_winner = int(
            (admitted["selected_fast_fail_10_label_bool"].map(boolish) & admitted["winner_120"].map(boolish)).sum()
        )
        for _, cfg_row in cfg.iterrows():
            rand = rejected_by_random(admitted, cfg_row)
            rule = rejected_by_structural(admitted, cfg_row, rule_status, required_features)
            rand_ff = rand["selected_fast_fail_10_label_bool"].map(boolish)
            rand_winner = rand["winner_120"].map(boolish)
            rule_ff = rule["selected_fast_fail_10_label_bool"].map(boolish)
            rule_winner = rule["winner_120"].map(boolish)
            capture_status = (
                "pass"
                if post_positive >= int(cfg_row["min_positive_count"])
                and int(rand_ff.sum()) >= int(cfg_row["min_rule_positive_count"])
                and int(rule_ff.sum()) >= int(cfg_row["min_rule_positive_count"])
                and rule_status == "pass"
                else ("rule_baseline_input_blocked" if rule_status != "pass" else "fail_low_count")
            )
            injury_status = (
                "pass"
                if post_winner >= int(cfg_row["min_winner_count"])
                and int((rand_ff & rand_winner).sum()) >= int(cfg_row["min_rule_winner_count"])
                and int((rule_ff & rule_winner).sum()) >= int(cfg_row["min_rule_winner_count"])
                and rule_status == "pass"
                else ("rule_baseline_input_blocked" if rule_status != "pass" else "fail_low_count")
            )
            key_dict = dict(zip(group_keys(), keys, strict=True))
            rows.append(
                {
                    **key_dict,
                    "threshold_id": cfg_row["threshold_id"],
                    "capacity_id": cfg_row["capacity_id"],
                    "post_dedup_sample_n": int(len(admitted)),
                    "post_dedup_fast_fail_positive_n": post_positive,
                    "post_dedup_fast_fail_winner_n": post_fast_fail_winner,
                    "post_dedup_winner_n": post_winner,
                    "random_rejected_fast_fail_positive_n": int(rand_ff.sum()),
                    "random_rejected_fast_fail_winner_n": int((rand_ff & rand_winner).sum()),
                    "random_rejected_fast_fail_non_winner_n": int((rand_ff & ~rand_winner).sum()),
                    "rule_baseline_rejected_fast_fail_positive_n": int(rule_ff.sum()),
                    "rule_baseline_rejected_fast_fail_winner_n": int((rule_ff & rule_winner).sum()),
                    "rule_baseline_rejected_fast_fail_non_winner_n": int((rule_ff & ~rule_winner).sum()),
                    "rule_baseline_status": rule_status,
                    "capture_lift_power_status": capture_status,
                    "winner_injury_power_status": injury_status,
                    "fast_fail_ml_supported_gate_allowed": bool(
                        key_dict["denominator_id"] == R_CORE_OUTPUT_DENOM
                        and not boolish(key_dict["readout_only_flag"])
                        and capture_status == "pass"
                        and injury_status == "pass"
                        and rule_status == "pass"
                    ),
                }
            )
    return pd.DataFrame(rows)


def build_false_repair_power_audit(bindings: pd.DataFrame, config_df: pd.DataFrame) -> pd.DataFrame:
    cfg = config_df.loc[config_df["component_id"].eq("false_repair_20d_component")]
    rows = []
    for keys, group in bindings.groupby(group_keys(), dropna=False):
        admitted = group.loc[group["admission_status"].eq("admitted")].copy()
        e1_status = aggregate_e1_status(admitted["e1_missed_proxy_status"])
        post_positive = int(admitted["frozen_false_repair_20d_label_bool"].map(boolish).sum())
        post_winner = int(admitted["winner_120"].map(boolish).sum())
        post_e1 = int(admitted["E1_missed_winner_flag"].map(boolish).sum())
        for _, cfg_row in cfg.iterrows():
            rand = rejected_by_random(admitted, cfg_row)
            rand_fr = rand["frozen_false_repair_20d_label_bool"].map(boolish)
            rand_winner = rand["winner_120"].map(boolish)
            rand_e1 = rand["E1_missed_winner_flag"].map(boolish)
            false_repair_status = (
                "pass" if post_positive >= int(cfg_row["min_positive_count"]) else "fail_low_count"
            )
            winner_status = "pass" if post_winner >= int(cfg_row["min_winner_count"]) else "fail_low_count"
            key_dict = dict(zip(group_keys(), keys, strict=True))
            allowed = bool(
                key_dict["denominator_id"] == R_CORE_OUTPUT_DENOM
                and not boolish(key_dict["readout_only_flag"])
                and false_repair_status == "pass"
                and winner_status == "pass"
                and e1_status != AGG_E1_STATUS_BLOCKED
            )
            rows.append(
                {
                    **key_dict,
                    "threshold_id": cfg_row["threshold_id"],
                    "capacity_id": cfg_row["capacity_id"],
                    "post_dedup_sample_n": int(len(admitted)),
                    "post_dedup_false_repair_positive_n": post_positive,
                    "post_dedup_winner_n": post_winner,
                    "post_dedup_E1_missed_winner_n": post_e1,
                    "e1_missed_proxy_status": e1_status,
                    "post_dedup_e1_status_episode_level_proxy_from_08_membership_n": int(
                        admitted["e1_missed_proxy_status"].astype(str).eq("episode_level_proxy_from_08_membership").sum()
                    ),
                    "post_dedup_e1_status_no_episode_membership_for_event_n": int(
                        admitted["e1_missed_proxy_status"].astype(str).eq("no_episode_membership_for_event").sum()
                    ),
                    "post_dedup_e1_status_episode_membership_proxy_input_blocked_n": int(
                        admitted["e1_missed_proxy_status"].astype(str).eq(AGG_E1_STATUS_BLOCKED).sum()
                    ),
                    "random_rejected_false_repair_positive_n": int(rand_fr.sum()),
                    "random_rejected_false_repair_winner_n": int((rand_fr & rand_winner).sum()),
                    "random_rejected_E1_missed_winner_n": int(rand_e1.sum()),
                    "random_rejected_false_repair_non_winner_n": int((rand_fr & ~rand_winner).sum()),
                    "false_repair_power_status": false_repair_status,
                    "winner_retention_power_status": winner_status,
                    "false_repair_ml_supported_gate_allowed": allowed,
                }
            )
    return pd.DataFrame(rows)


def output_paths() -> dict[str, Path]:
    return {
        "rule_arm_contract": TABLE_DIR / "rule_arm_contract.csv",
        "post_dedup_population_contract": TABLE_DIR / "post_dedup_population_contract.csv",
        "post_dedup_sample_count_by_split": TABLE_DIR / "post_dedup_sample_count_by_split.csv",
        "post_dedup_label_coverage_audit": TABLE_DIR / "post_dedup_label_coverage_audit.csv",
        "post_dedup_fast_fail_power_audit": TABLE_DIR / "post_dedup_fast_fail_power_audit.csv",
        "post_dedup_false_repair_power_audit": TABLE_DIR / "post_dedup_false_repair_power_audit.csv",
        "post_dedup_density_audit": TABLE_DIR / "post_dedup_density_audit.csv",
        "power_audit_config": TABLE_DIR / "power_audit_config.csv",
        "input_scope_exclusion_audit": TABLE_DIR / "input_scope_exclusion_audit.csv",
        "post_dedup_event_bindings": LOCAL_CACHE_DIR / "post_dedup_event_bindings.parquet",
        "manifest": MANIFEST_DIR / "10A_density_rule_system_manifest.json",
        "report": REPORT_DIR / "10A_density_rule_system_report.md",
    }


def write_outputs(outputs: dict[str, Path], artifacts: dict[str, pd.DataFrame], report: str, manifest: dict[str, Any]) -> None:
    write_df(outputs["rule_arm_contract"], artifacts["rule_arm_contract"])
    write_df(outputs["post_dedup_population_contract"], artifacts["population_contract"])
    write_df(outputs["post_dedup_sample_count_by_split"], artifacts["sample_count"])
    write_df(outputs["post_dedup_label_coverage_audit"], artifacts["label_coverage"])
    write_df(outputs["post_dedup_fast_fail_power_audit"], artifacts["fast_fail_power"])
    write_df(outputs["post_dedup_false_repair_power_audit"], artifacts["false_repair_power"])
    write_df(outputs["post_dedup_density_audit"], artifacts["density_audit"])
    write_df(outputs["power_audit_config"], artifacts["power_config"])
    write_df(outputs["input_scope_exclusion_audit"], artifacts["input_scope_exclusion"])
    outputs["post_dedup_event_bindings"].parent.mkdir(parents=True, exist_ok=True)
    artifacts["event_bindings"][OUTPUT_BINDING_COLUMNS].to_parquet(outputs["post_dedup_event_bindings"], index=False)
    write_text(outputs["report"], report)
    manifest["output_hashes"] = {
        key: file_sha256(path)
        for key, path in outputs.items()
        if key != "manifest" and path.is_file()
    }
    manifest["outputs"] = {key: str(path) for key, path in outputs.items()}
    write_json(outputs["manifest"], manifest)


def build_manifest(
    config: dict[str, Any],
    input_paths: dict[str, Path],
    decision: str,
    statuses: dict[str, Any],
) -> dict[str, Any]:
    return {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "experiment_id": "10_riskon_layered_rejector_system_v0",
        "component_id": "10A_density_rule_system",
        "decision": decision,
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "git_revision": git_revision(),
        "config_path": str(CONFIG_PATH),
        "config_hash": stable_hash(config),
        "config_file_hash": file_sha256(CONFIG_PATH) if CONFIG_PATH.is_file() else None,
        "requirement_path": str(REQUIREMENT_PATH),
        "requirement_hash": file_sha256(REQUIREMENT_PATH) if REQUIREMENT_PATH.is_file() else None,
        "input_paths": {key: str(path) for key, path in input_paths.items()},
        "input_hashes": {key: file_sha256(path) for key, path in input_paths.items() if path.is_file()},
        "statuses": statuses,
    }


def report_text(decision: str, artifacts: dict[str, pd.DataFrame], statuses: dict[str, Any]) -> str:
    population = artifacts.get("population_contract", pd.DataFrame())
    sample = artifacts.get("sample_count", pd.DataFrame())
    power = artifacts.get("fast_fail_power", pd.DataFrame())
    false_power = artifacts.get("false_repair_power", pd.DataFrame())
    lines = [
        "# 10A Density Rule System Report",
        "",
        f"- decision: `{decision}`",
        f"- source caveated: `{statuses.get('source_caveated')}`",
        f"- e1 proxy status: `{statuses.get('e1_proxy_status')}`",
        f"- materialized arm count: `{statuses.get('materialized_arm_n')}`",
        "",
        "## Population Summary",
        "",
    ]
    if not population.empty:
        summary = (
            population.groupby(["rule_arm_id", "denominator_id"], dropna=False)
            .agg(
                sample_n=("sample_n", "sum"),
                admitted_event_n=("admitted_event_n", "sum"),
                suppressed_event_n=("suppressed_event_n", "sum"),
                winner_n=("winner_n", "sum"),
                fast_fail_positive_n=("fast_fail_positive_n", "sum"),
                false_repair_positive_n=("false_repair_positive_n", "sum"),
            )
            .reset_index()
        )
        lines.append(summary.to_markdown(index=False))
    else:
        lines.append("No population was materialized.")
    lines.extend(["", "## Power Gate Readiness", ""])
    if not power.empty:
        lines.append(
            f"- fast-fail supported rows: `{int(power['fast_fail_ml_supported_gate_allowed'].map(boolish).sum())}`"
        )
    if not false_power.empty:
        lines.append(
            f"- false-repair supported rows: `{int(false_power['false_repair_ml_supported_gate_allowed'].map(boolish).sum())}`"
        )
    if not sample.empty:
        lines.append(
            f"- admitted events across all arms/scopes: `{int(sample['admitted_event_n'].sum())}`"
        )
    lines.extend(["", "This component does not train models or select thresholds."])
    return "\n".join(lines) + "\n"


def build_all(config: dict[str, Any]) -> tuple[str, dict[str, pd.DataFrame], dict[str, Any], dict[str, Path]]:
    paths, loaded = read_required_inputs(config)
    arms = parse_arms(config)
    scoped = scope_treatment(loaded["binding_09a"])
    input_scope_exclusion = build_input_scope_exclusion_audit(scoped)
    failures = validate_upstream_hashes(paths, loaded)
    failures.extend(validate_scope(scoped))
    feature_cols = list(config["structural_swing_low_rank_v1_required_features"])
    e1_status = "not_run"

    if failures:
        decision = DECISION_INPUT_BLOCKED
        artifacts = {
            "input_scope_exclusion": input_scope_exclusion,
            "rule_arm_contract": pd.DataFrame(),
            "event_bindings": pd.DataFrame(columns=OUTPUT_BINDING_COLUMNS),
            "sample_count": pd.DataFrame(),
            "label_coverage": pd.DataFrame(),
            "density_audit": pd.DataFrame(),
            "population_contract": pd.DataFrame(),
            "power_config": power_audit_config(config),
            "fast_fail_power": pd.DataFrame(),
            "false_repair_power": pd.DataFrame(),
        }
    else:
        base, failures, e1_status = build_base_events(
            scoped,
            loaded["canonical_events"],
            loaded["feature_matrix"],
            loaded["sample_weights"],
            paths["upstream_08_episode_membership"],
            feature_cols,
        )
        if failures:
            decision = DECISION_INPUT_BLOCKED
            artifacts = {
                "input_scope_exclusion": input_scope_exclusion,
                "rule_arm_contract": pd.DataFrame(),
                "event_bindings": pd.DataFrame(columns=OUTPUT_BINDING_COLUMNS),
                "sample_count": pd.DataFrame(),
                "label_coverage": pd.DataFrame(),
                "density_audit": pd.DataFrame(),
                "population_contract": pd.DataFrame(),
                "power_config": power_audit_config(config),
                "fast_fail_power": pd.DataFrame(),
                "false_repair_power": pd.DataFrame(),
            }
        else:
            event_bindings, arm_contract = build_event_bindings(base, arms)
            materialized_arm_n = int(arm_contract["arm_status"].eq("materialized").sum())
            if materialized_arm_n == 0:
                decision = DECISION_INPUT_BLOCKED
            else:
                decision = DECISION_SOURCE_CAVEATED_FROZEN if source_caveated(loaded["manifest_09a"]) else DECISION_FROZEN
            power_config_df = power_audit_config(config)
            sample_count = build_sample_count(event_bindings)
            label_coverage = build_label_coverage(event_bindings)
            density = build_density_audit(event_bindings)
            population = build_population_contract(event_bindings, density)
            fast_fail_power = build_fast_fail_power_audit(
                event_bindings,
                power_config_df,
                loaded["feature_contract"],
                feature_cols,
            )
            false_repair_power = build_false_repair_power_audit(event_bindings, power_config_df)
            artifacts = {
                "input_scope_exclusion": input_scope_exclusion,
                "rule_arm_contract": arm_contract,
                "event_bindings": event_bindings,
                "sample_count": sample_count,
                "label_coverage": label_coverage,
                "density_audit": density,
                "population_contract": population,
                "power_config": power_config_df,
                "fast_fail_power": fast_fail_power,
                "false_repair_power": false_repair_power,
            }

    statuses = {
        "input_failures": failures,
        "source_caveated": source_caveated(loaded["manifest_09a"]),
        "e1_proxy_status": e1_status,
        "materialized_arm_n": int(
            artifacts["rule_arm_contract"]["arm_status"].eq("materialized").sum()
            if not artifacts["rule_arm_contract"].empty
            else 0
        ),
        "input_scope_exclusion_row_n": int(len(input_scope_exclusion)),
        "input_row_n": int(len(loaded["binding_09a"])),
        "eligible_risk_on_row_n": int(
            scoped["scope_treatment"].isin(["materialize", "materialize_readout_only"]).sum()
        ),
    }
    return decision, artifacts, statuses, paths


def run(config_path: Path = CONFIG_PATH) -> dict[str, Any]:
    config = load_yaml(config_path)
    decision, artifacts, statuses, input_paths = build_all(config)
    outputs = output_paths()
    manifest = build_manifest(config, input_paths, decision, statuses)
    report = report_text(decision, artifacts, statuses)
    write_outputs(outputs, artifacts, report, manifest)
    return {
        "decision": decision,
        "manifest_path": str(outputs["manifest"]),
        "report_path": str(outputs["report"]),
        "event_bindings_path": str(outputs["post_dedup_event_bindings"]),
        "statuses": statuses,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run 10A density rule system.")
    parser.add_argument("--config", default=str(CONFIG_PATH), help="Path to 10A config.yaml")
    args = parser.parse_args(argv)
    result = run(Path(args.config))
    print(json.dumps(result, indent=2, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
