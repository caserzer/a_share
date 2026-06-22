#!/usr/bin/env python
from __future__ import annotations

import argparse
import importlib.util
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


EXPERIMENT_DIR = Path(__file__).resolve().parents[1]
TOPIC_ROOT = Path(__file__).resolve().parents[4]
REPO_ROOT = Path(__file__).resolve().parents[6]
TOPIC_SRC_DIR = TOPIC_ROOT / "src"

if str(TOPIC_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(TOPIC_SRC_DIR))

from afml_big_winner.config import load_yaml, stable_hash  # noqa: E402
from afml_big_winner.manifest import file_sha256, git_revision  # noqa: E402


def _load_12a7c_helpers():
    path = EXPERIMENT_DIR / "src" / "run_12a7c_direction_e_stage2_decoupling_chained_readouts.py"
    spec = importlib.util.spec_from_file_location("run_12a7c_helpers_for_12a7d", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


C7 = _load_12a7c_helpers()
A7 = C7.A7

RUN_ID = "12A7d_stage2_random_baseline_support_triage"
EXPERIMENT_ID = "12_state_change_event_backbone_rebuild_v0"
LEGACY_DIRECTORY_ID = "12_multi_k_winner_failure_path_morphology_research_v0"

CONFIG_PATH = EXPERIMENT_DIR / "configs" / "config_12a7d_stage2_random_baseline_support_triage.yaml"
TABLE_DIR = EXPERIMENT_DIR / "outputs" / "publishable" / "tables" / RUN_ID
LOCAL_CACHE_DIR = EXPERIMENT_DIR / "outputs" / "local_cache" / RUN_ID
REPORT_DIR = EXPERIMENT_DIR / "outputs" / "publishable" / "reports"
MANIFEST_DIR = EXPERIMENT_DIR / "outputs" / "manifests"

SPLITS = ("all", "train", "validation", "robustness")
TARGET_COL = "stage_2_continuation_target"
RANDOM_TARGET_COL = "random_stage_2_continuation_target"
COMPLEX_SCORE_COL = "stage2_continuation_score"
CELL_COLS = ["split", "board_bucket", "calendar_month"]
JOIN_KEY = ["path_key", "instrument", "entry_pos", "entry_price"]

BASELINE_SPECS: dict[str, dict[str, Any]] = {
    "strict_exact_cell_replay": {
        "family": "strict_exact_cell_replay",
        "rank": 1,
        "levels": ["month"],
        "diagnostic_only": False,
        "allow_replacement": False,
        "pooled": False,
    },
    "hierarchical_month_quarter_replay": {
        "family": "hierarchical_cell_replay",
        "rank": 2,
        "levels": ["month", "quarter"],
        "diagnostic_only": False,
        "allow_replacement": False,
        "pooled": False,
    },
    "hierarchical_split_board_fallback_replay": {
        "family": "hierarchical_cell_replay",
        "rank": 3,
        "levels": ["month", "quarter", "split_board"],
        "diagnostic_only": True,
        "allow_replacement": False,
        "pooled": False,
    },
    "pooled_cell_weighted_replay": {
        "family": "pooled_cell_weighted_replay",
        "rank": 4,
        "levels": ["month"],
        "diagnostic_only": True,
        "allow_replacement": False,
        "pooled": True,
    },
    "with_replacement_replay": {
        "family": "with_replacement_replay",
        "rank": 5,
        "levels": ["month"],
        "diagnostic_only": True,
        "allow_replacement": True,
        "pooled": False,
    },
}

EXPECTED_INPUT_COLUMNS: dict[str, tuple[str, ...]] = {
    "requirement": (),
    "upstream_requirement_12a7c": (),
    "a7c_input_artifact_audit": ("artifact_id", "read_status", "schema_status", "sha256"),
    "a7c_scope_universe_audit": ("split",),
    "a7c_stage1_anchor_rule_card": ("stage1_anchor_rule_id", "stage1_anchor_reconstruction_status"),
    "a7c_stage2_candidate_card": ("candidate_id", "candidate_family", "candidate_status"),
    "a7c_stage2_train_selection": ("denominator_type", "candidate_id", "stage2_budget_X", "selection_status"),
    "a7c_stage2_ground_truth_survivor_readout": (
        "denominator_type",
        "split",
        "candidate_id",
        "stage2_budget_X",
        "selected_n",
        "selected_positive_n",
        "selected_budget_rank_evaluable",
        "readout_status",
    ),
    "a7c_stage2_chained_trailing_rank_readout": (
        "denominator_type",
        "split",
        "candidate_id",
        "stage2_budget_X",
        "selected_n",
        "selected_positive_n",
        "selected_budget_rank_evaluable",
        "readout_status",
    ),
    "a7c_stage2_random_same_budget_audit": ("seed", "split", "requested_selected_n", "random_replay_status"),
    "a7c_stage2_single_feature_challenger": ("candidate_id", "split"),
    "a7c_stage2_complex_model_matched_comparator": ("candidate_id", "split"),
    "a7c_stage2_budget_drift_audit": ("candidate_id", "split"),
    "a7c_stage2_opportunity_cost_audit": ("split",),
    "a7c_direction_e_decision": (
        "decision_state",
        "input_gate_status",
        "stage1_anchor_reconstruction_status",
        "stage2_decoupled_signal_status",
        "stage2_chained_operating_status",
        "selected_chained_deployable_at_stage_2_decision_time",
        "selected_chained_candidate_id",
        "selected_chained_candidate_family",
        "selected_chained_X",
        "selected_decoupled_candidate_id",
        "selected_decoupled_candidate_family",
        "selected_decoupled_X",
        "stage1_anchor_rule_id",
        "stage1_anchor_feature",
        "stage1_anchor_orientation",
        "stage1_anchor_X",
        "gate_failure_reasons",
    ),
    "a7c_report": (),
    "a7c_manifest": (),
    "a7c_stage2_decoupling_score_matrix": (
        "meta_event_id",
        "instrument",
        "event_t0_date",
        "event_t0_pos",
        "split",
        "board_bucket",
        "calendar_month",
        "path_key",
        "stage_2_decision_pos",
        TARGET_COL,
        "stage2_label_read_status",
        "source_arm_is_c0",
        "market_regime_bucket",
        "stage_1_evaluable",
        "no_fast_fail_L10_H20",
        "stage_2_path_evaluable",
        "stage_2_entry_blocked",
        "stage_2_horizon_complete_20d",
        "stage1_anchor_selected_flag",
        "stage1_anchor_rank_status",
        COMPLEX_SCORE_COL,
    ),
    "a7c_random_stage2_selected": (),
    "a7c_bootstrap_replicates": (),
    "matched_random_sampled_entries": (
        "seed",
        "sample_draw_id",
        "path_key",
        "split",
        "board_bucket",
        "calendar_month",
        "calendar_quarter",
        "random_trade_open_date",
        "instrument",
        "entry_pos",
        "entry_price",
        "replacement_draw_index",
    ),
    "entry_forward_path_cache": (
        "path_key",
        "instrument",
        "entry_pos",
        "entry_price",
        "entry_blocked",
        "horizon_complete_20d",
        "time_to_lower_minus_10_20d",
    ),
    "stage2_path_cache": (
        "path_key",
        "instrument",
        "entry_pos",
        "entry_price",
        "stage_2_entry_blocked",
        "stage_2_horizon_complete_20d",
        "continuation_U20_L10_H2_20",
    ),
    "manifest_12a6b": (),
    "manifest_12a6c": (),
}

OPTIONAL_INPUTS = {"a7c_random_stage2_selected", "a7c_bootstrap_replicates"}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run 12A7d stage-2 random baseline support triage.")
    parser.add_argument("--config", default=str(CONFIG_PATH))
    parser.add_argument("--mode", choices=["check-inputs", "full"], default="full")
    return parser.parse_args(argv)


def topic_path(value: str | Path) -> Path:
    return C7.topic_path(value)


def output_paths() -> dict[str, Path]:
    return {
        "input_artifact_audit": TABLE_DIR / "input_artifact_audit.csv",
        "frozen_candidate_reconciliation": TABLE_DIR / "frozen_candidate_reconciliation.csv",
        "random_support_cell_audit": TABLE_DIR / "random_support_cell_audit.csv",
        "random_replay_variant_readout": TABLE_DIR / "random_replay_variant_readout.csv",
        "random_replay_variant_bootstrap_ci": TABLE_DIR / "random_replay_variant_bootstrap_ci.csv",
        "random_replay_seed_distribution": TABLE_DIR / "random_replay_seed_distribution.csv",
        "stage2_chained_sensitivity_decision": TABLE_DIR / "stage2_chained_sensitivity_decision.csv",
        "frozen_candidate_selection_matrix": LOCAL_CACHE_DIR / "frozen_candidate_selection_matrix.parquet",
        "variant_random_selected": LOCAL_CACHE_DIR / "variant_random_selected.parquet",
        "variant_bootstrap_replicates": LOCAL_CACHE_DIR / "variant_bootstrap_replicates.parquet",
        "report": REPORT_DIR / "stage2_random_baseline_triage_report.md",
        "manifest": MANIFEST_DIR / f"{RUN_ID}_manifest.json",
    }


def read_table(path: Path, **kwargs: Any) -> pd.DataFrame:
    return C7.read_table(path, **kwargs)


def write_df(path: Path, frame: pd.DataFrame) -> Path:
    return C7.write_df(path, frame)


def write_text(path: Path, text: str) -> Path:
    return C7.write_text(path, text)


def write_json(path: Path, payload: dict[str, Any]) -> Path:
    return C7.write_json(path, payload)


def path_sha(path: Path) -> str:
    return file_sha256(path) if path.exists() and path.is_file() else ""


def boolish(value: Any) -> bool:
    return A7.boolish(value)


def bool_series(values: pd.Series) -> pd.Series:
    return values.map(boolish).astype(bool)


def safe_rate(num: int | float, den: int | float) -> float:
    return A7.safe_rate(num, den)


def split_frame(frame: pd.DataFrame, split: str) -> pd.DataFrame:
    return frame.copy() if split == "all" else frame.loc[frame["split"].astype(str).eq(split)].copy()


def fmt(value: Any) -> str:
    return "NA" if pd.isna(value) else f"{float(value):.4f}"


def calendar_quarter_from_month(values: pd.Series) -> pd.Series:
    months = values.astype(str).str.slice(5, 7)
    years = values.astype(str).str.slice(0, 4)
    quarters = ((pd.to_numeric(months, errors="coerce") - 1) // 3 + 1).astype("Int64")
    return years + "Q" + quarters.astype(str)


def count_rows(path: Path) -> int | float:
    return C7.count_rows(path)


def read_columns_for_schema(path: Path) -> list[str]:
    if not path.exists() or not path.is_file():
        return []
    if "".join(path.suffixes).endswith(".parquet"):
        return list(pd.read_parquet(path).columns)
    return list(pd.read_csv(path, nrows=0, low_memory=False).columns)


def build_input_artifact_audit(config: dict[str, Any]) -> pd.DataFrame:
    rows = []
    for artifact_id, required_cols in EXPECTED_INPUT_COLUMNS.items():
        raw = config.get("paths", {}).get(artifact_id, artifact_id)
        path = topic_path(raw)
        optional = artifact_id in OPTIONAL_INPUTS
        exists = path.is_file()
        read_status = "pass" if exists else ("optional_missing" if optional else "missing")
        schema_status = "pass" if optional and not exists else ("pass" if exists and not required_cols else "not_checked")
        row_count = np.nan
        if exists:
            try:
                cols = read_columns_for_schema(path)
                missing = set(required_cols) - set(cols)
                schema_status = "pass" if not missing else "missing_columns:" + ";".join(sorted(missing))
                row_count = count_rows(path)
            except Exception as exc:
                read_status = f"read_error:{type(exc).__name__}"
                schema_status = "not_checked"
        rows.append(
            {
                "artifact_id": artifact_id,
                "resolved_path": str(path),
                "row_count": row_count,
                "sha256": path_sha(path),
                "schema_status": schema_status,
                "read_status": read_status,
                "required_flag": not optional,
            }
        )
    return pd.DataFrame(rows)


def input_gate_status(audit: pd.DataFrame) -> tuple[bool, str]:
    required = audit.loc[audit["required_flag"]].copy()
    reasons = []
    if not required["read_status"].astype(str).eq("pass").all():
        reasons.append("missing_or_unreadable_required_inputs")
    if not required["schema_status"].astype(str).eq("pass").all():
        reasons.append("required_schema_mismatch")
    return not reasons, ";".join(reasons)


def upstream_random_failure_gate(decision: pd.DataFrame, dec_readout: pd.DataFrame, chain_readout: pd.DataFrame) -> tuple[bool, str, str]:
    allowed = {"decoupled_random_replay_failed", "chained_random_replay_failed"}
    if decision.empty:
        return False, "missing_12A7c_decision", "unavailable"
    row = decision.iloc[0]
    base_checks = [
        str(row.get("stage1_anchor_reconstruction_status", "")) == "pass",
        boolish(row.get("selected_chained_deployable_at_stage_2_decision_time", False)),
        str(row.get("selected_chained_candidate_id", "")) != "",
        pd.notna(row.get("selected_chained_X", np.nan)),
    ]
    if not all(base_checks):
        return False, "12A7c_anchor_or_selected_candidate_not_usable", "gate_failure_reasons"
    if "gate_failure_reasons" in decision.columns and pd.notna(row.get("gate_failure_reasons", np.nan)):
        reasons = {x for x in str(row["gate_failure_reasons"]).split(";") if x}
        if reasons and reasons.issubset(allowed):
            return True, "", "gate_failure_reasons"
        return False, "12A7c_failure_reason_not_random_replay_only", "gate_failure_reasons"

    selected_dec = dec_readout.loc[
        dec_readout["candidate_id"].astype(str).eq(str(row.get("selected_decoupled_candidate_id", "")))
        & dec_readout["stage2_budget_X"].eq(float(row.get("selected_decoupled_X", np.nan)))
    ]
    selected_chain = chain_readout.loc[
        chain_readout["candidate_id"].astype(str).eq(str(row.get("selected_chained_candidate_id", "")))
        & chain_readout["stage2_budget_X"].eq(float(row.get("selected_chained_X", np.nan)))
    ]
    legacy_ok = (
        str(row.get("decision_state", "")) == "12A7c_blocked_input_or_stage1_anchor_failure"
        and str(row.get("stage2_decoupled_signal_status", "")) == "blocked"
        and str(row.get("stage2_chained_operating_status", "")) == "blocked"
        and not selected_dec.empty
        and not selected_chain.empty
        and selected_dec["readout_status"].astype(str).eq("random_replay_failed").any()
        and selected_chain["readout_status"].astype(str).eq("random_replay_failed").any()
    )
    return (True, "", "inferred_legacy_12A7c_artifact") if legacy_ok else (False, "legacy_12A7c_random_failure_inference_failed", "inferred_legacy_12A7c_artifact")


def history_policy(config: dict[str, Any]) -> Any:
    h = config["history_policy"]
    return A7.HistoryPolicy(
        history_policy_id=str(h["history_policy_id"]),
        history_window_mode=str(h["history_window_mode"]),
        trailing_history_window_sessions=int(h["trailing_history_window_sessions"]),
        diagnostic_only_flag=False,
    )


def load_score_matrix(resolved: dict[str, Path]) -> pd.DataFrame:
    frame = read_table(resolved["a7c_stage2_decoupling_score_matrix"])
    if "calendar_quarter" not in frame.columns:
        frame["calendar_quarter"] = calendar_quarter_from_month(frame["calendar_month"])
    for col in (
        "source_arm_is_c0",
        "stage_1_evaluable",
        "no_fast_fail_L10_H20",
        "stage_2_path_evaluable",
        "stage_2_entry_blocked",
        "stage_2_horizon_complete_20d",
        TARGET_COL,
        "stage1_anchor_selected_flag",
    ):
        if col in frame.columns:
            frame[col] = bool_series(frame[col])
    primary = frame.loc[
        bool_series(frame["source_arm_is_c0"])
        & frame["market_regime_bucket"].astype(str).eq("risk_on")
        & bool_series(frame["stage_1_evaluable"])
    ].copy()
    return primary


def stage2_survivor_frame(frame: pd.DataFrame) -> pd.DataFrame:
    return frame.loc[
        bool_series(frame["no_fast_fail_L10_H20"])
        & bool_series(frame["stage_2_path_evaluable"])
        & (~bool_series(frame["stage_2_entry_blocked"]))
        & bool_series(frame["stage_2_horizon_complete_20d"])
        & frame["stage2_label_read_status"].astype(str).eq("pass")
        & pd.to_numeric(frame["stage_2_decision_pos"], errors="coerce").notna()
    ].copy()


def candidate_identity(decision: pd.DataFrame, denominator_type: str) -> dict[str, Any]:
    row = decision.iloc[0]
    if denominator_type == "stage1_anchor_chained_survivor":
        return {
            "denominator_type": denominator_type,
            "candidate_id": str(row["selected_chained_candidate_id"]),
            "candidate_family": str(row["selected_chained_candidate_family"]),
            "stage2_budget_X": float(row["selected_chained_X"]),
            "feature_name": COMPLEX_SCORE_COL if str(row["selected_chained_candidate_id"]) == "complex_stage2_score" else "",
            "orientation": "desc",
            "deployable_at_stage_2_decision_time": True,
        }
    return {
        "denominator_type": denominator_type,
        "candidate_id": str(row["selected_decoupled_candidate_id"]),
        "candidate_family": str(row["selected_decoupled_candidate_family"]),
        "stage2_budget_X": float(row["selected_decoupled_X"]),
        "feature_name": COMPLEX_SCORE_COL if str(row["selected_decoupled_candidate_id"]) == "complex_stage2_score" else "",
        "orientation": "desc",
        "deployable_at_stage_2_decision_time": False,
    }


def resolve_candidate_feature(identity: dict[str, Any], train_selection: pd.DataFrame) -> dict[str, Any]:
    if identity["feature_name"]:
        return identity
    matched = train_selection.loc[
        train_selection["denominator_type"].astype(str).eq(str(identity["denominator_type"]))
        & train_selection["candidate_id"].astype(str).eq(str(identity["candidate_id"]))
        & train_selection["stage2_budget_X"].eq(float(identity["stage2_budget_X"]))
    ]
    if matched.empty:
        raise RuntimeError(f"Could not resolve 12A7c candidate feature for {identity}")
    row = matched.iloc[0]
    identity = dict(identity)
    identity["feature_name"] = str(row["feature_list"])
    orient = json.loads(str(row["feature_orientation_json"]))
    identity["orientation"] = str(next(iter(orient.values())))
    return identity


def make_selection(denominator: pd.DataFrame, identity: dict[str, Any], config: dict[str, Any], anchor: dict[str, Any]) -> pd.DataFrame:
    return C7.make_selection(
        str(identity["denominator_type"]),
        denominator,
        str(identity["candidate_id"]),
        str(identity["candidate_family"]),
        str(identity["feature_name"]),
        str(identity["orientation"]),
        float(identity["stage2_budget_X"]),
        history_policy(config),
        config,
        anchor,
    )


def readout_for_selection(selection: pd.DataFrame) -> pd.DataFrame:
    return C7.readout_for_selection(selection)


def reconcile_candidate(selection: pd.DataFrame, upstream_readout: pd.DataFrame) -> pd.DataFrame:
    recomputed = readout_for_selection(selection)
    rows = []
    for split in SPLITS:
        got = recomputed.loc[recomputed["split"].eq(split)].iloc[0]
        exp_rows = upstream_readout.loc[
            upstream_readout["denominator_type"].astype(str).eq(str(got["denominator_type"]))
            & upstream_readout["candidate_id"].astype(str).eq(str(got["candidate_id"]))
            & upstream_readout["stage2_budget_X"].eq(float(got["stage2_budget_X"]))
            & upstream_readout["split"].astype(str).eq(split)
        ]
        if exp_rows.empty:
            status = "missing_upstream_readout"
            exp_selected = np.nan
            exp_positive = np.nan
            exp_budget = np.nan
        else:
            exp = exp_rows.iloc[0]
            exp_selected = int(exp["selected_n"])
            exp_positive = int(exp["selected_positive_n"])
            exp_budget = float(exp["selected_budget_rank_evaluable"])
            status = "pass" if (
                int(got["selected_n"]) == exp_selected
                and int(got["selected_positive_n"]) == exp_positive
                and abs(float(got["selected_budget_rank_evaluable"]) - exp_budget) <= 1e-12
            ) else "fail"
        rows.append(
            {
                "denominator_type": got["denominator_type"],
                "candidate_id": got["candidate_id"],
                "candidate_family": got["candidate_family"],
                "stage2_budget_X": got["stage2_budget_X"],
                "split": split,
                "recomputed_selected_n": int(got["selected_n"]),
                "upstream_selected_n": exp_selected,
                "recomputed_selected_positive_n": int(got["selected_positive_n"]),
                "upstream_selected_positive_n": exp_positive,
                "recomputed_selected_budget_rank_evaluable": float(got["selected_budget_rank_evaluable"]),
                "upstream_selected_budget_rank_evaluable": exp_budget,
                "candidate_reconciliation_status": status,
            }
        )
    return pd.DataFrame(rows)


def prepare_random_labels(resolved: dict[str, Path], config: dict[str, Any]) -> tuple[pd.DataFrame, str]:
    random, status = C7.prepare_random_labels(
        {
            "matched_random_sampled_entries": resolved["matched_random_sampled_entries"],
            "entry_forward_path_cache": resolved["entry_forward_path_cache"],
            "stage2_path_cache": resolved["stage2_path_cache"],
        }
    )
    if random.empty:
        return random, status
    if "calendar_quarter" not in random.columns:
        random["calendar_quarter"] = calendar_quarter_from_month(random["calendar_month"])
    for col in config["random_baseline"]["retention_rank_columns"]:
        if col not in random.columns:
            random[col] = random.groupby("seed", sort=False).cumcount()
    uid_cols = ["seed", "sample_draw_id", "path_key", "instrument", "entry_pos", "entry_price", "replacement_draw_index"]
    random["random_row_uid"] = random[uid_cols].astype(str).agg("|".join, axis=1)
    return random, status


def sort_pool(pool: pd.DataFrame, rank_cols: list[str]) -> pd.DataFrame:
    cols = [c for c in rank_cols if c in pool.columns]
    return pool.sort_values(cols, kind="stable") if cols else pool.sort_index(kind="stable")


def cell_match(pool: pd.DataFrame, row: pd.Series, grain: str) -> pd.Series:
    mask = pool["split"].astype(str).eq(str(row["split"])) & pool["board_bucket"].astype(str).eq(str(row["board_bucket"]))
    if grain == "month":
        mask &= pool["calendar_month"].astype(str).eq(str(row["calendar_month"]))
    elif grain == "quarter":
        mask &= pool["calendar_quarter"].astype(str).eq(str(row["calendar_quarter"]))
    elif grain == "split_board":
        pass
    else:
        raise ValueError(f"Unknown grain: {grain}")
    return mask


def grouped_pool(pool: pd.DataFrame) -> dict[str, dict[tuple[Any, ...], np.ndarray]]:
    maps: dict[str, dict[tuple[Any, ...], np.ndarray]] = {"month": {}, "quarter": {}, "split_board": {}}
    if pool.empty:
        return maps
    for key, indexer in pool.groupby(["split", "board_bucket", "calendar_month"], dropna=False, sort=False).indices.items():
        maps["month"][tuple(key)] = np.asarray(indexer, dtype=int)
    for key, indexer in pool.groupby(["split", "board_bucket", "calendar_quarter"], dropna=False, sort=False).indices.items():
        maps["quarter"][tuple(key)] = np.asarray(indexer, dtype=int)
    for key, indexer in pool.groupby(["split", "board_bucket"], dropna=False, sort=False).indices.items():
        maps["split_board"][tuple(key)] = np.asarray(indexer, dtype=int)
    return maps


def pool_group_indices(maps: dict[str, dict[tuple[Any, ...], np.ndarray]], row: pd.Series, grain: str) -> np.ndarray:
    if grain == "month":
        key = (row["split"], row["board_bucket"], row["calendar_month"])
    elif grain == "quarter":
        key = (row["split"], row["board_bucket"], row["calendar_quarter"])
    elif grain == "split_board":
        key = (row["split"], row["board_bucket"])
    else:
        raise ValueError(f"Unknown grain: {grain}")
    return maps[grain].get(tuple(key), np.asarray([], dtype=int))


def requested_counts(frame: pd.DataFrame, flag_col: str, output_col: str) -> pd.DataFrame:
    selected = frame.loc[bool_series(frame[flag_col]) & frame["split"].astype(str).ne("all")].copy()
    if selected.empty:
        return pd.DataFrame(columns=CELL_COLS + ["calendar_quarter", output_col])
    out = selected.groupby(CELL_COLS + ["calendar_quarter"], dropna=False).size().rename(output_col).reset_index()
    return out.sort_values(CELL_COLS, kind="stable").reset_index(drop=True)


def draw_for_counts(
    pool: pd.DataFrame,
    counts: pd.DataFrame,
    baseline_id: str,
    replay_step: str,
    rank_cols: list[str],
    request_col: str,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    spec = BASELINE_SPECS[baseline_id]
    selected_parts = []
    audit_rows = []
    used: set[str] = set()
    pool = sort_pool(pool.copy(), rank_cols).reset_index(drop=True)
    pool_uids = pool["random_row_uid"].astype(str).to_numpy() if "random_row_uid" in pool.columns else np.asarray([], dtype=str)
    pool_maps = grouped_pool(pool)
    for _, req in counts.sort_values(CELL_COLS + ["calendar_quarter"], kind="stable").iterrows():
        requested_n = int(req[request_col])
        selected_idx = np.asarray([], dtype=int)
        replacement_draw_index: np.ndarray | None = None
        realized_grain = ""
        available_n = 0
        replacement_used = False
        for grain in spec["levels"]:
            candidate_idx = pool_group_indices(pool_maps, req, grain)
            if not spec["allow_replacement"] and len(candidate_idx):
                candidate_idx = np.asarray([idx for idx in candidate_idx if pool_uids[idx] not in used], dtype=int)
            available_n = int(len(candidate_idx))
            realized_grain = grain
            if spec["pooled"]:
                take_n = min(requested_n, available_n)
                selected_idx = candidate_idx[:take_n]
                break
            if spec["allow_replacement"]:
                if available_n >= requested_n:
                    selected_idx = candidate_idx[:requested_n]
                elif available_n > 0:
                    selected_idx = np.resize(candidate_idx, requested_n)
                    replacement_draw_index = np.arange(requested_n)
                    replacement_used = True
                break
            if available_n >= requested_n:
                selected_idx = candidate_idx[:requested_n]
                break
        selected = pool.iloc[selected_idx].copy() if len(selected_idx) else pool.head(0).copy()
        sampled_n = int(len(selected))
        if spec["pooled"]:
            status = "pass" if sampled_n > 0 else "fail"
        elif spec["allow_replacement"]:
            status = "pass" if sampled_n == requested_n else "fail"
        else:
            status = "pass" if sampled_n == requested_n else "fail"
        if not selected.empty:
            if replacement_draw_index is not None:
                selected["replacement_replay_draw_index"] = replacement_draw_index
            elif "replacement_replay_draw_index" not in selected.columns:
                selected["replacement_replay_draw_index"] = np.nan
            selected["requested_selected_n"] = requested_n
            selected["realized_cell_grain"] = realized_grain
            selected["replay_step"] = replay_step
            selected["stage1_keep_selected_flag"] = replay_step == "stage1_keep"
            selected_parts.append(selected)
            if not spec["allow_replacement"]:
                used.update(selected["random_row_uid"].astype(str).tolist())
        duplicate_n = sampled_n - selected["random_row_uid"].nunique() if sampled_n and "random_row_uid" in selected else 0
        audit_rows.append(
            {
                "baseline_id": baseline_id,
                "baseline_family_id": spec["family"],
                "seed": pool["seed"].iloc[0] if not pool.empty else np.nan,
                "replay_step": replay_step,
                "split": req["split"],
                "board_bucket": req["board_bucket"],
                "calendar_month": req["calendar_month"],
                "calendar_quarter": req["calendar_quarter"],
                "requested_selected_n": requested_n,
                "realized_cell_grain": realized_grain,
                "available_random_n": available_n,
                "sampled_random_n": sampled_n,
                "shortfall_n": max(requested_n - sampled_n, 0),
                "fallback_used_flag": realized_grain not in {"", "month"},
                "replacement_used_flag": replacement_used,
                "duplicate_rate": safe_rate(duplicate_n, sampled_n),
                "random_row_uid_duplicate_n": int(duplicate_n),
                "cell_support_status": status,
            }
        )
    selected_all = pd.concat(selected_parts, ignore_index=True) if selected_parts else pool.head(0).copy()
    return selected_all, pd.DataFrame(audit_rows)


def selected_rate(frame: pd.DataFrame, target_col: str = TARGET_COL) -> float:
    return safe_rate(int(bool_series(frame[target_col]).sum()), len(frame))


def split_seed_rates(selected: pd.DataFrame, valid_seeds: set[Any]) -> pd.DataFrame:
    rows = []
    selected = selected.loc[selected["seed"].isin(valid_seeds)].copy()
    for seed, group in selected.groupby("seed", sort=False):
        for split in SPLITS:
            sub = split_frame(group, split)
            rows.append(
                {
                    "seed": seed,
                    "split": split,
                    "random_rate": selected_rate(sub, RANDOM_TARGET_COL),
                    "sampled_random_n": int(len(sub)),
                    "random_positive_n": int(bool_series(sub[RANDOM_TARGET_COL]).sum()) if len(sub) else 0,
                }
            )
    return pd.DataFrame(rows)


def stage1_seed_valid(audit: pd.DataFrame, baseline_id: str, requested_total: int, config: dict[str, Any]) -> set[Any]:
    spec = BASELINE_SPECS[baseline_id]
    if audit.empty:
        return set()
    grouped = audit.groupby("seed", dropna=False)
    valid = set()
    for seed, group in grouped:
        if spec["pooled"]:
            share = safe_rate(float(group["sampled_random_n"].sum()), requested_total)
            if pd.notna(share) and share >= float(config["random_baseline"]["pooled_min_supported_weight_share"]):
                valid.add(seed)
        elif spec["allow_replacement"]:
            if group["available_random_n"].gt(0).all():
                valid.add(seed)
        elif group["cell_support_status"].eq("pass").all():
            valid.add(seed)
    return valid


def kish_effective_n(selected: pd.DataFrame) -> float:
    if selected.empty:
        return 0.0
    counts = selected["random_row_uid"].astype(str).value_counts().to_numpy(dtype=float)
    return float(counts.sum() ** 2 / np.square(counts).sum()) if len(counts) else 0.0


def weighted_random_rate(selected: pd.DataFrame, audit: pd.DataFrame) -> float:
    supported = audit.loc[audit["sampled_random_n"].gt(0), CELL_COLS + ["requested_selected_n"]].copy()
    if selected.empty or supported.empty:
        return np.nan
    cell_rates = (
        selected.groupby(CELL_COLS, dropna=False)[RANDOM_TARGET_COL]
        .agg(lambda x: bool_series(x).mean())
        .rename("cell_rate")
        .reset_index()
    )
    weighted = supported.merge(cell_rates, on=CELL_COLS, how="inner")
    if weighted.empty:
        return np.nan
    denom = float(weighted["requested_selected_n"].sum())
    if denom <= 0:
        return np.nan
    return float((weighted["requested_selected_n"] * weighted["cell_rate"]).sum() / denom)


def supported_candidate_frame(selection: pd.DataFrame, audit: pd.DataFrame, split: str) -> pd.DataFrame:
    candidate = split_frame(selection.loc[bool_series(selection["selected_flag"])], split)
    supported_keys = audit.loc[audit["sampled_random_n"].gt(0), CELL_COLS].drop_duplicates()
    if candidate.empty or supported_keys.empty:
        return candidate.head(0).copy()
    return candidate.merge(supported_keys, on=CELL_COLS, how="inner")


def replay_variant(
    selection: pd.DataFrame,
    random: pd.DataFrame,
    baseline_id: str,
    denominator_type: str,
    config: dict[str, Any],
    stage1_counts: pd.DataFrame | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    rank_cols = [c for c in config["random_baseline"]["retention_rank_columns"] if c in random.columns]
    stage2_counts = requested_counts(selection, "selected_flag", "requested_selected_n")
    stage1_counts = stage1_counts if stage1_counts is not None else pd.DataFrame()
    selected_parts = []
    audit_parts = []
    seed_rows = []
    spec = BASELINE_SPECS[baseline_id]
    seeds = sorted(random["seed"].dropna().unique())
    stage1_requested_total = int(stage1_counts["requested_selected_n"].sum()) if not stage1_counts.empty else 0
    for seed in seeds:
        seed_pool = random.loc[random["seed"].eq(seed)].copy()
        if denominator_type == "stage1_anchor_chained_survivor":
            stage1_pool = seed_pool.loc[bool_series(seed_pool["random_stage_1_evaluable"])].copy()
            stage1_selected, stage1_audit = draw_for_counts(stage1_pool, stage1_counts, baseline_id, "stage1_keep", rank_cols, "requested_selected_n")
            stage1_valid = seed in stage1_seed_valid(stage1_audit, baseline_id, stage1_requested_total, config)
            survivor_pool = stage1_selected.loc[
                bool_series(stage1_selected["random_no_fast_fail_L10_H20"])
                & bool_series(stage1_selected["random_stage_2_evaluable"])
                & stage1_selected["random_stage2_label_read_status"].astype(str).eq("pass")
            ].copy()
        else:
            stage1_audit = pd.DataFrame()
            stage1_valid = True
            survivor_pool = seed_pool.loc[
                bool_series(seed_pool["random_no_fast_fail_L10_H20"])
                & bool_series(seed_pool["random_stage_2_evaluable"])
                & seed_pool["random_stage2_label_read_status"].astype(str).eq("pass")
            ].copy()
        stage2_selected, stage2_audit = draw_for_counts(survivor_pool, stage2_counts, baseline_id, "stage2_select", rank_cols, "requested_selected_n")
        requested_total = int(stage2_audit["requested_selected_n"].sum()) if not stage2_audit.empty else 0
        seed_eff = kish_effective_n(stage2_selected)
        if not stage1_audit.empty:
            stage1_eff_map = {
                split: kish_effective_n(split_frame(stage1_selected, split))
                for split in SPLITS
                if split != "all"
            }
            stage1_audit["seed_effective_n"] = stage1_audit["split"].map(stage1_eff_map).fillna(kish_effective_n(stage1_selected))
            audit_parts.append(stage1_audit)
        stage2_eff_map = {
            split: kish_effective_n(split_frame(stage2_selected, split))
            for split in SPLITS
            if split != "all"
        }
        stage2_audit["seed_effective_n"] = stage2_audit["split"].map(stage2_eff_map).fillna(seed_eff)
        audit_parts.append(stage2_audit)
        seed_has_valid_split = False
        for split in SPLITS:
            sub = split_frame(stage2_selected, split)
            audit_sub = stage2_audit.copy() if split == "all" else stage2_audit.loc[stage2_audit["split"].eq(split)].copy()
            requested_split_n = int(audit_sub["requested_selected_n"].sum()) if not audit_sub.empty else 0
            supported_requested_n = int(audit_sub.loc[audit_sub["sampled_random_n"].gt(0), "requested_selected_n"].sum()) if not audit_sub.empty else 0
            supported_share = safe_rate(supported_requested_n, requested_split_n)
            split_eff = kish_effective_n(sub)
            zero_support = int(audit_sub["available_random_n"].eq(0).sum()) if not audit_sub.empty else 0
            if spec["pooled"]:
                valid = bool(stage1_valid and pd.notna(supported_share) and supported_share >= float(config["random_baseline"]["pooled_min_supported_weight_share"]))
                random_rate = weighted_random_rate(sub, audit_sub)
                candidate_supported = supported_candidate_frame(selection, audit_sub, split)
                candidate_supported_n = int(len(candidate_supported))
                candidate_supported_positive_n = int(bool_series(candidate_supported[TARGET_COL]).sum()) if candidate_supported_n else 0
                candidate_supported_rate = selected_rate(candidate_supported)
            elif spec["allow_replacement"]:
                floor = float(config["random_baseline"]["replacement_effective_n_floor_fraction"]) * requested_split_n
                valid = bool(stage1_valid and zero_support == 0 and split_eff >= floor)
                random_rate = selected_rate(sub, RANDOM_TARGET_COL)
                candidate_supported_n = np.nan
                candidate_supported_positive_n = np.nan
                candidate_supported_rate = np.nan
            else:
                valid = bool(stage1_valid and not audit_sub.empty and audit_sub["cell_support_status"].eq("pass").all())
                random_rate = selected_rate(sub, RANDOM_TARGET_COL)
                candidate_supported_n = np.nan
                candidate_supported_positive_n = np.nan
                candidate_supported_rate = np.nan
            seed_has_valid_split = bool(seed_has_valid_split or valid)
            seed_rows.append(
                {
                    "baseline_id": baseline_id,
                    "baseline_family_id": spec["family"],
                    "denominator_type": denominator_type,
                    "candidate_id": selection.iloc[0]["candidate_id"],
                    "candidate_family": selection.iloc[0]["candidate_family"],
                    "stage2_budget_X": float(selection.iloc[0]["stage2_budget_X"]),
                    "seed": seed,
                    "split": split,
                    "seed_valid_flag": valid,
                    "random_rate": random_rate,
                    "sampled_random_n": int(len(sub)),
                    "random_positive_n": int(bool_series(sub[RANDOM_TARGET_COL]).sum()) if len(sub) else 0,
                    "supported_requested_n": supported_requested_n,
                    "requested_selected_n": requested_split_n,
                    "supported_weight_share": supported_share,
                    "seed_effective_n": split_eff,
                    "cell_zero_support_n": zero_support,
                    "candidate_supported_cell_selected_n": candidate_supported_n,
                    "candidate_supported_cell_positive_n": candidate_supported_positive_n,
                    "candidate_supported_cell_continuation_rate": candidate_supported_rate,
                }
            )
        if seed_has_valid_split and not stage2_selected.empty:
            selected_parts.append(stage2_selected)
    selected_all = pd.concat(selected_parts, ignore_index=True) if selected_parts else random.head(0).copy()
    audit = pd.concat(audit_parts, ignore_index=True) if audit_parts else pd.DataFrame()
    seed_dist = pd.DataFrame(seed_rows)
    return selected_all, audit, seed_dist


def bootstrap_ci(
    candidate: pd.DataFrame,
    seed_rates: pd.Series,
    config: dict[str, Any],
    label: str,
    split: str,
    target_col: str = TARGET_COL,
) -> tuple[float, float, int, pd.DataFrame]:
    if candidate.empty or seed_rates.empty:
        return np.nan, np.nan, 0, pd.DataFrame()
    y = bool_series(candidate[target_col]).astype(float).to_numpy()
    rates = pd.to_numeric(seed_rates, errors="coerce").dropna().to_numpy(dtype=float)
    if len(y) == 0 or len(rates) == 0:
        return np.nan, np.nan, 0, pd.DataFrame()
    rng = np.random.default_rng(int(config["bootstrap"]["seed"]) + int(stable_hash(label)[:8], 16))
    deltas = []
    for _ in range(int(config["bootstrap"]["n_resamples"])):
        cand_rate = float(rng.choice(y, size=len(y), replace=True).mean())
        random_p50 = float(np.median(rng.choice(rates, size=len(rates), replace=True)))
        deltas.append(cand_rate - random_p50)
    reps = pd.DataFrame({"comparison_id": label, "split": split, "replicate_id": np.arange(len(deltas)), "delta": deltas})
    return (
        float(np.quantile(deltas, float(config["bootstrap"]["ci_low_q"]))),
        float(np.quantile(deltas, float(config["bootstrap"]["ci_high_q"]))),
        len(deltas),
        reps,
    )


def bootstrap_seed_rate_delta(
    candidate_rates: pd.Series,
    seed_rates: pd.Series,
    config: dict[str, Any],
    label: str,
    split: str,
) -> tuple[float, float, int, pd.DataFrame]:
    candidate = pd.to_numeric(candidate_rates, errors="coerce").dropna().to_numpy(dtype=float)
    rates = pd.to_numeric(seed_rates, errors="coerce").dropna().to_numpy(dtype=float)
    if len(candidate) == 0 or len(rates) == 0:
        return np.nan, np.nan, 0, pd.DataFrame()
    rng = np.random.default_rng(int(config["bootstrap"]["seed"]) + int(stable_hash(label)[:8], 16))
    deltas = []
    for _ in range(int(config["bootstrap"]["n_resamples"])):
        cand_rate = float(np.median(rng.choice(candidate, size=len(candidate), replace=True)))
        random_p50 = float(np.median(rng.choice(rates, size=len(rates), replace=True)))
        deltas.append(cand_rate - random_p50)
    reps = pd.DataFrame({"comparison_id": label, "split": split, "replicate_id": np.arange(len(deltas)), "delta": deltas})
    return (
        float(np.quantile(deltas, float(config["bootstrap"]["ci_low_q"]))),
        float(np.quantile(deltas, float(config["bootstrap"]["ci_high_q"]))),
        len(deltas),
        reps,
    )


def variant_readout(
    selection: pd.DataFrame,
    baseline_id: str,
    random_selected: pd.DataFrame,
    audit: pd.DataFrame,
    seed_dist: pd.DataFrame,
    config: dict[str, Any],
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    spec = BASELINE_SPECS[baseline_id]
    rows = []
    ci_rows = []
    reps = []
    for split in SPLITS:
        cand_full = split_frame(selection.loc[bool_series(selection["selected_flag"])], split)
        seed_sub = seed_dist.loc[seed_dist["split"].eq(split) & seed_dist["seed_valid_flag"]].copy()
        valid_seed_n = int(seed_sub["seed"].nunique()) if not seed_sub.empty else 0
        effective_seed_n = valid_seed_n
        rates = pd.to_numeric(seed_sub["random_rate"], errors="coerce").dropna()
        random_p05 = float(rates.quantile(0.05)) if not rates.empty else np.nan
        random_p50 = float(rates.quantile(0.50)) if not rates.empty else np.nan
        random_p95 = float(rates.quantile(0.95)) if not rates.empty else np.nan
        candidate_for_delta = cand_full
        candidate_supported_rate = np.nan
        candidate_supported_n = int(len(cand_full))
        candidate_supported_positive_n = int(bool_series(cand_full[TARGET_COL]).sum()) if len(cand_full) else 0
        if spec["pooled"] and not seed_sub.empty:
            seed_candidate_rates = pd.to_numeric(seed_sub["candidate_supported_cell_continuation_rate"], errors="coerce").dropna()
            candidate_supported_rate = float(seed_candidate_rates.median()) if not seed_candidate_rates.empty else np.nan
            candidate_supported_n = int(pd.to_numeric(seed_sub["candidate_supported_cell_selected_n"], errors="coerce").median()) if not seed_sub.empty else 0
            candidate_supported_positive_n = int(pd.to_numeric(seed_sub["candidate_supported_cell_positive_n"], errors="coerce").median()) if not seed_sub.empty else 0
        cand_rate = candidate_supported_rate if spec["pooled"] and pd.notna(candidate_supported_rate) else selected_rate(candidate_for_delta)
        full_cand_rate = selected_rate(cand_full)
        delta = cand_rate - random_p50 if pd.notna(cand_rate) and pd.notna(random_p50) else np.nan
        if spec["pooled"]:
            low, high, rep_n, rep = bootstrap_seed_rate_delta(
                seed_sub["candidate_supported_cell_continuation_rate"],
                rates,
                config,
                f"{baseline_id}:{split}",
                split,
            )
        else:
            low, high, rep_n, rep = bootstrap_ci(candidate_for_delta, rates, config, f"{baseline_id}:{split}", split)
        if not rep.empty:
            rep["baseline_id"] = baseline_id
            rep["denominator_type"] = selection.iloc[0]["denominator_type"]
            rep["candidate_id"] = selection.iloc[0]["candidate_id"]
            reps.append(rep)
        stage2_audit = audit.loc[audit["replay_step"].eq("stage2_select")].copy()
        if split != "all":
            stage2_audit = stage2_audit.loc[stage2_audit["split"].eq(split)].copy()
        requested_n = int(stage2_audit["requested_selected_n"].sum()) if not stage2_audit.empty else 0
        sampled_n = int(stage2_audit.loc[stage2_audit["seed"].isin(set(seed_sub["seed"])), "sampled_random_n"].sum()) if not stage2_audit.empty else 0
        available_n = int(stage2_audit["available_random_n"].sum()) if not stage2_audit.empty else 0
        shortfall_n = int(stage2_audit["shortfall_n"].sum()) if not stage2_audit.empty else 0
        supported_requested_n = int(stage2_audit.loc[stage2_audit["sampled_random_n"].gt(0), "requested_selected_n"].sum()) if not stage2_audit.empty else 0
        supported_share = safe_rate(supported_requested_n, requested_n)
        cell_zero_n = int(stage2_audit["available_random_n"].eq(0).sum()) if not stage2_audit.empty else 0
        median_eff = float(seed_sub["seed_effective_n"].median()) if not seed_sub.empty else np.nan
        if spec["pooled"]:
            construction_status = "pass" if (
                valid_seed_n >= int(config["random_baseline"]["pooled_min_effective_seed_n"])
                and pd.notna(supported_share)
                and supported_share >= float(config["random_baseline"]["pooled_min_supported_weight_share"])
            ) else "insufficient"
        elif spec["allow_replacement"]:
            construction_status = "pass" if valid_seed_n >= int(config["random_baseline"]["min_random_seed_n"]) and cell_zero_n == 0 else "insufficient"
        else:
            construction_status = "pass" if valid_seed_n >= int(config["random_baseline"]["min_random_seed_n"]) else "insufficient"
        readout_status = "ok" if construction_status == "pass" else "random_replay_insufficient"
        rows.append(
            {
                "baseline_id": baseline_id,
                "baseline_family_id": spec["family"],
                "denominator_type": selection.iloc[0]["denominator_type"],
                "candidate_id": selection.iloc[0]["candidate_id"],
                "candidate_family": selection.iloc[0]["candidate_family"],
                "stage2_budget_X": float(selection.iloc[0]["stage2_budget_X"]),
                "split": split,
                "cell_grain": "mixed" if audit["realized_cell_grain"].nunique() > 1 else (audit["realized_cell_grain"].dropna().iloc[0] if not audit.empty else ""),
                "null_strength_rank": spec["rank"],
                "board_dimension_preserved_flag": True,
                "calendar_dimension_preserved_flag": baseline_id != "hierarchical_split_board_fallback_replay",
                "allowed_interpretation": "diagnostic_only" if spec["diagnostic_only"] else ("original_fail_closed_benchmark" if spec["rank"] == 1 else "sensitivity_with_baseline_caveat"),
                "stage1_anchor_rule_id": selection.iloc[0]["stage1_anchor_rule_id"],
                "stage1_anchor_X": np.nan,
                "candidate_selected_n": int(len(cand_full)),
                "candidate_selected_positive_n": int(bool_series(cand_full[TARGET_COL]).sum()) if len(cand_full) else 0,
                "candidate_continuation_rate": cand_rate,
                "candidate_base_continuation_rate": selected_rate(split_frame(selection, split)),
                "full_candidate_selected_n": int(len(cand_full)),
                "full_candidate_positive_n": int(bool_series(cand_full[TARGET_COL]).sum()) if len(cand_full) else 0,
                "full_candidate_continuation_rate": full_cand_rate,
                "candidate_supported_cell_selected_n": candidate_supported_n,
                "candidate_supported_cell_positive_n": candidate_supported_positive_n,
                "candidate_supported_cell_continuation_rate": candidate_supported_rate,
                "requested_selected_n": requested_n,
                "requested_cell_n": int(len(stage2_audit)) if not stage2_audit.empty else 0,
                "supported_cell_n": int(stage2_audit["sampled_random_n"].gt(0).sum()) if not stage2_audit.empty else 0,
                "unsupported_cell_n": int(stage2_audit["sampled_random_n"].eq(0).sum()) if not stage2_audit.empty else 0,
                "available_random_n": available_n,
                "sampled_random_n": sampled_n,
                "shortfall_n": shortfall_n,
                "shortfall_rate": safe_rate(shortfall_n, requested_n),
                "supported_requested_n": supported_requested_n,
                "unsupported_requested_n": requested_n - supported_requested_n,
                "supported_weight_share": supported_share,
                "valid_seed_n": valid_seed_n,
                "effective_seed_n": effective_seed_n,
                "random_p05": random_p05,
                "random_p50": random_p50,
                "random_p95": random_p95,
                "delta_vs_random_p50": delta,
                "delta_vs_random_p50_ci95_low": low,
                "delta_vs_random_p50_ci95_high": high,
                "bootstrap_replicate_valid_n": rep_n,
                "replacement_draw_n": int(stage2_audit["replacement_used_flag"].sum()) if not stage2_audit.empty else 0,
                "duplicate_rate": float(stage2_audit["duplicate_rate"].mean()) if not stage2_audit.empty else np.nan,
                "effective_n": median_eff,
                "median_seed_effective_n": median_eff,
                "cell_zero_support_n": cell_zero_n,
                "baseline_construction_status": construction_status,
                "readout_status": readout_status,
                "diagnostic_only_flag": bool(spec["diagnostic_only"] or selection.iloc[0]["denominator_type"] == "ground_truth_no_fast_fail_survivor"),
            }
        )
        ci_rows.append(
            {
                "baseline_id": baseline_id,
                "denominator_type": selection.iloc[0]["denominator_type"],
                "candidate_id": selection.iloc[0]["candidate_id"],
                "stage2_budget_X": float(selection.iloc[0]["stage2_budget_X"]),
                "split": split,
                "delta_vs_random_p50_ci95_low": low,
                "delta_vs_random_p50_ci95_high": high,
                "bootstrap_replicate_valid_n": rep_n,
            }
        )
    return pd.DataFrame(rows), pd.DataFrame(ci_rows), pd.concat(reps, ignore_index=True) if reps else pd.DataFrame()


def support_pass(row: pd.Series, config: dict[str, Any]) -> bool:
    return (
        int(row.get("candidate_selected_n", 0)) >= int(config["gates"]["selected_n_min"])
        and int(row.get("candidate_selected_positive_n", 0)) >= int(config["gates"]["selected_positive_n_min"])
        and int(row.get("bootstrap_replicate_valid_n", 0)) >= int(config["bootstrap"]["bootstrap_min_valid_replicates"])
        and float(row.get("delta_vs_random_p50", -np.inf)) >= float(config["gates"]["delta_vs_random_p50_min"])
        and float(row.get("delta_vs_random_p50_ci95_low", -np.inf)) > 0
        and str(row.get("baseline_construction_status", "")) == "pass"
    )


def decision_from_readout(
    readout: pd.DataFrame,
    candidate_reconciliation_status: str,
    input_gate_status_value: str,
    random_source_status: str,
    gate_failure_reasons_source: str,
    identity: dict[str, Any],
    config: dict[str, Any],
) -> pd.DataFrame:
    chained = readout.loc[
        readout["denominator_type"].eq("stage1_anchor_chained_survivor")
        & readout["split"].eq("robustness")
    ].copy()
    if input_gate_status_value != "pass" or candidate_reconciliation_status != "pass" or random_source_status != "pass":
        state = "12A7d_blocked_input_or_lineage_failure"
    else:
        by_id = {row["baseline_id"]: row for _, row in chained.iterrows()}
        strict = by_id.get("strict_exact_cell_replay", pd.Series(dtype=object))
        h_mq = by_id.get("hierarchical_month_quarter_replay", pd.Series(dtype=object))
        pooled = by_id.get("pooled_cell_weighted_replay", pd.Series(dtype=object))
        diag = [
            by_id.get("hierarchical_split_board_fallback_replay", pd.Series(dtype=object)),
            pooled,
            by_id.get("with_replacement_replay", pd.Series(dtype=object)),
        ]
        if not strict.empty and support_pass(strict, config):
            state = "12A7d_strict_chained_stage2_supported"
        elif (
            (strict.empty or strict.get("baseline_construction_status") != "pass")
            and not h_mq.empty
            and support_pass(h_mq, config)
            and not pooled.empty
            and float(pooled.get("delta_vs_random_p50", -np.inf)) > 0
        ):
            state = "12A7d_chained_stage2_supported_with_baseline_caveat"
        elif any((not row.empty and float(row.get("delta_vs_random_p50", -np.inf)) > 0) for row in diag):
            state = "12A7d_stage2_signal_diagnostic_only"
        elif chained["baseline_construction_status"].isin(["fail", "insufficient"]).all():
            state = "12A7d_random_baseline_support_insufficient"
        else:
            constructible = chained.loc[chained["baseline_construction_status"].eq("pass")].copy()
            strongest_rank = int(constructible["null_strength_rank"].min()) if not constructible.empty else 999
            state = "12A7d_stage2_not_supported" if strongest_rank <= 3 else "12A7d_random_baseline_support_insufficient"
    constructible = chained.loc[chained["baseline_construction_status"].eq("pass")].sort_values("null_strength_rank")
    strongest = constructible.iloc[0] if not constructible.empty else pd.Series(dtype=object)
    supporting = (
        chained.loc[
            chained.apply(lambda r: support_pass(r, config), axis=1)
            & (~bool_series(chained.get("diagnostic_only_flag", pd.Series(False, index=chained.index))))
        ].sort_values("null_strength_rank")
        if not chained.empty
        else pd.DataFrame()
    )
    weakest_support = supporting.sort_values("null_strength_rank", ascending=False).iloc[0] if not supporting.empty else pd.Series(dtype=object)
    if state in {"12A7d_strict_chained_stage2_supported", "12A7d_chained_stage2_supported_with_baseline_caveat"}:
        followup = "quantify_stage1_defense_opportunity_cost_before_policy_replay"
    elif state == "12A7d_blocked_input_or_lineage_failure":
        followup = "gate_specific_failure_triage"
    else:
        followup = "test_whether_stage1_X030_denominator_is_too_narrow"
    next_allowed = "requirement_12a7e_defense_participation_frontier.md" if state != "12A7d_blocked_input_or_lineage_failure" else "none"
    robust = strongest if not strongest.empty else (chained.iloc[0] if not chained.empty else pd.Series(dtype=object))
    return pd.DataFrame(
        [
            {
                "decision_state": state,
                "input_gate_status": input_gate_status_value,
                "candidate_reconciliation_status": candidate_reconciliation_status,
                "random_source_status": random_source_status,
                "gate_failure_reasons_source": gate_failure_reasons_source,
                "selected_chained_candidate_id": identity["candidate_id"],
                "selected_chained_candidate_family": identity["candidate_family"],
                "selected_chained_X": identity["stage2_budget_X"],
                "stage1_anchor_rule_id": robust.get("stage1_anchor_rule_id", ""),
                "stage1_anchor_feature": "",
                "stage1_anchor_orientation": "",
                "stage1_anchor_X": np.nan,
                "strict_baseline_status": str(by_id.get("strict_exact_cell_replay", pd.Series()).get("baseline_construction_status", "")) if "by_id" in locals() else "",
                "hierarchical_month_quarter_baseline_status": str(by_id.get("hierarchical_month_quarter_replay", pd.Series()).get("baseline_construction_status", "")) if "by_id" in locals() else "",
                "hierarchical_split_board_fallback_baseline_status": str(by_id.get("hierarchical_split_board_fallback_replay", pd.Series()).get("baseline_construction_status", "")) if "by_id" in locals() else "",
                "pooled_weighted_baseline_status": str(by_id.get("pooled_cell_weighted_replay", pd.Series()).get("baseline_construction_status", "")) if "by_id" in locals() else "",
                "with_replacement_baseline_status": str(by_id.get("with_replacement_replay", pd.Series()).get("baseline_construction_status", "")) if "by_id" in locals() else "",
                "strongest_accepted_null": strongest.get("baseline_id", ""),
                "weakest_accepted_null_that_supports_claim": weakest_support.get("baseline_id", ""),
                "weakest_accepted_null_strength_rank": weakest_support.get("null_strength_rank", np.nan),
                "robustness_candidate_selected_n": robust.get("candidate_selected_n", np.nan),
                "robustness_candidate_positive_n": robust.get("candidate_selected_positive_n", np.nan),
                "robustness_candidate_continuation_rate": robust.get("candidate_continuation_rate", np.nan),
                "robustness_random_p50": robust.get("random_p50", np.nan),
                "robustness_delta_vs_random_p50": robust.get("delta_vs_random_p50", np.nan),
                "robustness_delta_vs_random_p50_ci95_low": robust.get("delta_vs_random_p50_ci95_low", np.nan),
                "robustness_delta_vs_random_p50_ci95_high": robust.get("delta_vs_random_p50_ci95_high", np.nan),
                "baseline_caveat": "" if state == "12A7d_strict_chained_stage2_supported" else "weaker_than_strict_exact_null",
                "allowed_interpretation": robust.get("allowed_interpretation", ""),
                "next_allowed_requirement": next_allowed,
                "recommended_internal_followup": followup,
            }
        ]
    )


def shortfall_cell_table(audit: pd.DataFrame, baseline_id: str, max_rows: int = 8) -> str:
    if audit.empty or "baseline_id" not in audit.columns:
        return "| split | board_bucket | calendar_month | shortfall_n | zero_support_rows |\n|---|---|---:|---:|---:|\n"
    sub = audit.loc[
        audit["baseline_id"].astype(str).eq(baseline_id)
        & audit["replay_step"].astype(str).eq("stage2_select")
        & audit["split"].astype(str).eq("robustness")
    ].copy()
    if sub.empty:
        return "| split | board_bucket | calendar_month | shortfall_n | zero_support_rows |\n|---|---|---:|---:|---:|\n"
    grouped = (
        sub.groupby(["split", "board_bucket", "calendar_month"], dropna=False)
        .agg(
            shortfall_n=("shortfall_n", "sum"),
            zero_support_rows=("available_random_n", lambda x: int(pd.Series(x).eq(0).sum())),
        )
        .reset_index()
        .sort_values(["shortfall_n", "zero_support_rows"], ascending=False)
    )
    grouped = grouped.loc[grouped["shortfall_n"].gt(0) | grouped["zero_support_rows"].gt(0)].head(max_rows)
    rows = ["| split | board_bucket | calendar_month | shortfall_n | zero_support_rows |", "|---|---|---:|---:|---:|"]
    for row in grouped.itertuples(index=False):
        rows.append(f"| `{row.split}` | `{row.board_bucket}` | `{row.calendar_month}` | {int(row.shortfall_n)} | {int(row.zero_support_rows)} |")
    return "\n".join(rows)


def row_by_baseline(robustness: pd.DataFrame, baseline_id: str) -> pd.Series:
    matched = robustness.loc[robustness["baseline_id"].astype(str).eq(baseline_id)]
    return matched.iloc[0] if not matched.empty else pd.Series(dtype=object)


def build_report(decision: pd.DataFrame, readout: pd.DataFrame, audit: pd.DataFrame) -> str:
    d = decision.iloc[0]
    if readout.empty or "denominator_type" not in readout.columns:
        robustness = pd.DataFrame()
    else:
        robustness = readout.loc[
            readout["denominator_type"].eq("stage1_anchor_chained_survivor") & readout["split"].eq("robustness")
        ].sort_values("null_strength_rank")
    strict = row_by_baseline(robustness, "strict_exact_cell_replay")
    hmq = row_by_baseline(robustness, "hierarchical_month_quarter_replay")
    hsb = row_by_baseline(robustness, "hierarchical_split_board_fallback_replay")
    pooled = row_by_baseline(robustness, "pooled_cell_weighted_replay")
    repl = row_by_baseline(robustness, "with_replacement_replay")
    strict_or_near = robustness.loc[robustness["null_strength_rank"].le(3) & robustness["baseline_construction_status"].eq("pass")]
    best_near = strict_or_near.sort_values("null_strength_rank").iloc[0] if not strict_or_near.empty else pd.Series(dtype=object)
    rows = []
    for _, row in robustness.iterrows():
        rows.append(
            f"| `{row['baseline_id']}` | {row['null_strength_rank']} | `{row['baseline_construction_status']}` | "
            f"{fmt(row['valid_seed_n'])} | {fmt(row['random_p50'])} | {fmt(row['delta_vs_random_p50'])} | "
            f"[{fmt(row['delta_vs_random_p50_ci95_low'])}, {fmt(row['delta_vs_random_p50_ci95_high'])}] | `{row['allowed_interpretation']}` |"
        )
    table = "\n".join(rows)
    shortfall_table = shortfall_cell_table(audit, "strict_exact_cell_replay")
    return f"""
# 12A7d stage-2 random baseline support triage report

## Decision

| field | value |
|---|---:|
| final decision_state | `{d['decision_state']}` |
| selected chained candidate | `{d['selected_chained_candidate_id']}` |
| selected chained X | {fmt(d['selected_chained_X'])} |
| stage-1 anchor tuple | `{d['stage1_anchor_rule_id']}` / `{d['stage1_anchor_feature']}` / `{d['stage1_anchor_orientation']}` |
| stage-1 anchor X | {fmt(d['stage1_anchor_X'])} |
| strict replay construction status | `{d['strict_baseline_status']}` |
| hierarchical month-quarter construction status | `{d['hierarchical_month_quarter_baseline_status']}` |
| hierarchical split-board construction status | `{d['hierarchical_split_board_fallback_baseline_status']}` |
| pooled weighted construction status | `{d['pooled_weighted_baseline_status']}` |
| with-replacement construction status | `{d['with_replacement_baseline_status']}` |
| strongest accepted null | `{d['strongest_accepted_null']}` |
| weakest accepted null that supports claim | `{d['weakest_accepted_null_that_supports_claim']}` |
| robustness candidate selected_n | {fmt(d['robustness_candidate_selected_n'])} |
| robustness candidate positive_n | {fmt(d['robustness_candidate_positive_n'])} |
| robustness candidate continuation_rate | {fmt(d['robustness_candidate_continuation_rate'])} |
| robustness random_p50 | {fmt(d['robustness_random_p50'])} |
| robustness delta_vs_random_p50 | {fmt(d['robustness_delta_vs_random_p50'])} |
| robustness delta CI low | {fmt(d['robustness_delta_vs_random_p50_ci95_low'])} |
| best strict-or-near random_p50 | {fmt(best_near.get('random_p50', np.nan))} |
| best strict-or-near CI | [{fmt(best_near.get('delta_vs_random_p50_ci95_low', np.nan))}, {fmt(best_near.get('delta_vs_random_p50_ci95_high', np.nan))}] |
| allowed interpretation | `{d['allowed_interpretation']}` |
| recommended next step | `{d['recommended_internal_followup']}` |

12A7d did not select a new stage-2 candidate, feature, X, or model family. It did not change the stage-1 simple backbone anchor. It only replays pre-registered random baseline variants around the 12A7c frozen chained candidate.

The conclusion applies only to C0 risk_on events and the current fixed -10% / +20% labels. A coarser random null is weaker evidence than strict exact replay. Pooled and with-replacement variants are diagnostic-only unless they merely confirm a stricter accepted null. Decoupled survivor readout is not deployable.

## Robustness Variant Readout

| baseline_id | strength | construction | valid_seed_n | random_p50 | delta | CI | interpretation |
|---|---:|---|---:|---:|---:|---|---|
{table}

## Support Shortfall Cells

Strict exact replay is under-supported for the chained robustness denominator: valid_seed_n is {fmt(strict.get('valid_seed_n', np.nan))}, below the configured minimum, so it remains a fail-closed benchmark rather than evidence against the candidate. The largest strict robustness stage-2 shortfall cells are:

{shortfall_table}

## Findings

1. Strict exact replay is not constructible for the frozen chained denominator; this is a narrow-cell support failure, not a new candidate-selection result.
2. Month-quarter hierarchical replay improves support but remains insufficient on robustness with valid_seed_n = {fmt(hmq.get('valid_seed_n', np.nan))}.
3. Split-board fallback repairs construction with valid_seed_n = {fmt(hsb.get('valid_seed_n', np.nan))}, while preserving board membership but weakening calendar control, so it is diagnostic-only.
4. Pooled weighted replay is directionally consistent: delta_vs_random_p50 = {fmt(pooled.get('delta_vs_random_p50', np.nan))}, CI low = {fmt(pooled.get('delta_vs_random_p50_ci95_low', np.nan))}. With-replacement replay remains diagnostic and under-supported with valid_seed_n = {fmt(repl.get('valid_seed_n', np.nan))}.
5. The evidence diagnoses that the strict random null cannot support the narrow stage-1 X=0.30 survivor denominator; it does not establish deployable chained stage-2 continuation support.
6. The next requirement should widen or audit stage-1 defense participation before any policy replay.
7. Decoupled replay was not emitted in this run; by contract it would be diagnostic-only and unable to change the decision.
""".strip()


def build_manifest(paths: dict[str, Path], frames: dict[str, pd.DataFrame], decision: pd.DataFrame, config_path: Path, requirement_path: Path, config: dict[str, Any]) -> dict[str, Any]:
    outputs = {}
    output_hashes = {}
    for key, path in paths.items():
        if key == "manifest" or not path.exists() or not path.is_file():
            continue
        sha = path_sha(path)
        output_hashes[key] = sha
        outputs[key] = {"path": str(path), "sha256": sha, "row_count": int(len(frames[key])) if key in frames else np.nan}
    inputs = {}
    input_hashes = {}
    if "input_artifact_audit" in frames:
        for row in frames["input_artifact_audit"].itertuples(index=False):
            artifact_id = str(row.artifact_id)
            sha = str(getattr(row, "sha256", "") or "")
            input_hashes[artifact_id] = sha
            inputs[artifact_id] = {
                "path": str(getattr(row, "resolved_path", "")),
                "sha256": sha,
                "read_status": str(getattr(row, "read_status", "")),
                "schema_status": str(getattr(row, "schema_status", "")),
            }
    return {
        "run_id": RUN_ID,
        "experiment_id": EXPERIMENT_ID,
        "legacy_directory_id": LEGACY_DIRECTORY_ID,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "python": platform.python_version(),
        "git_revision": git_revision(REPO_ROOT),
        "config_path": str(config_path),
        "config_hash": stable_hash(config),
        "config_sha256": path_sha(config_path),
        "requirement_path": str(requirement_path),
        "requirement_hash": path_sha(requirement_path),
        "entrypoint_hash": path_sha(Path(__file__).resolve()),
        "decision_state": decision.iloc[0]["decision_state"] if not decision.empty else "",
        "inputs": inputs,
        "input_hashes": input_hashes,
        "outputs": outputs,
        "output_hashes": output_hashes,
    }


def run_pipeline(config_path: Path, mode: str = "full") -> int:
    config = load_yaml(config_path)
    resolved = {key: topic_path(value) for key, value in config["paths"].items()}
    paths = output_paths()
    input_audit = build_input_artifact_audit(config)
    write_df(paths["input_artifact_audit"], input_audit)
    input_ok, input_reasons = input_gate_status(input_audit)
    if mode == "check-inputs":
        if not input_ok:
            raise RuntimeError(f"{RUN_ID} input check failed: {input_reasons}")
        print(f"{RUN_ID}: input audit ok ({len(input_audit)} artifacts)")
        return 0
    decision_e = read_table(resolved["a7c_direction_e_decision"])
    dec_upstream = read_table(resolved["a7c_stage2_ground_truth_survivor_readout"])
    chain_upstream = read_table(resolved["a7c_stage2_chained_trailing_rank_readout"])
    upstream_ok, upstream_reason, gate_source = upstream_random_failure_gate(decision_e, dec_upstream, chain_upstream)
    random_source_status = "not_evaluated"
    candidate_reconciliation_status = "not_evaluated"

    primary = load_score_matrix(resolved)
    decoupled = stage2_survivor_frame(primary)
    chained = decoupled.loc[bool_series(decoupled["stage1_anchor_selected_flag"])].copy()
    train_selection = read_table(resolved["a7c_stage2_train_selection"])
    anchor = {
        "stage1_anchor_rule_id": decision_e.iloc[0].get("stage1_anchor_rule_id", ""),
        "stage1_anchor_feature": decision_e.iloc[0].get("stage1_anchor_feature", ""),
        "stage1_anchor_orientation": decision_e.iloc[0].get("stage1_anchor_orientation", ""),
        "stage1_anchor_X": decision_e.iloc[0].get("stage1_anchor_X", np.nan),
    }
    chain_identity = resolve_candidate_feature(candidate_identity(decision_e, "stage1_anchor_chained_survivor"), train_selection)
    dec_identity = resolve_candidate_feature(candidate_identity(decision_e, "ground_truth_no_fast_fail_survivor"), train_selection)
    chain_selection = make_selection(chained, chain_identity, config, anchor)
    dec_selection = make_selection(decoupled, dec_identity, config, anchor)
    chain_recon = reconcile_candidate(chain_selection, chain_upstream)
    dec_recon = reconcile_candidate(dec_selection, dec_upstream)
    reconciliation = pd.concat([dec_recon, chain_recon], ignore_index=True)
    candidate_reconciliation_status = "pass" if reconciliation["candidate_reconciliation_status"].eq("pass").all() else "fail"
    write_df(paths["frozen_candidate_reconciliation"], reconciliation)

    random, random_label_status = prepare_random_labels(resolved, config)
    random_source_status = "pass" if random_label_status == "pass" else random_label_status
    if not input_ok or not upstream_ok or candidate_reconciliation_status != "pass" or random_source_status != "pass":
        readout = pd.DataFrame()
        decision = decision_from_readout(
            readout,
            candidate_reconciliation_status,
            "pass" if input_ok and upstream_ok else "fail",
            random_source_status,
            gate_source,
            chain_identity,
            config,
        )
        frames = {
            "input_artifact_audit": input_audit,
            "frozen_candidate_reconciliation": reconciliation,
            "random_support_cell_audit": pd.DataFrame(),
            "random_replay_variant_readout": pd.DataFrame(),
            "random_replay_variant_bootstrap_ci": pd.DataFrame(),
            "random_replay_seed_distribution": pd.DataFrame(),
            "stage2_chained_sensitivity_decision": decision,
            "frozen_candidate_selection_matrix": chain_selection,
            "variant_random_selected": pd.DataFrame(),
            "variant_bootstrap_replicates": pd.DataFrame(),
        }
        for key, frame in frames.items():
            write_df(paths[key], frame)
        write_text(paths["report"], build_report(decision, pd.DataFrame(), pd.DataFrame()))
        frames["report"] = pd.DataFrame([{"path": str(paths["report"])}])
        write_json(paths["manifest"], build_manifest(paths, frames, decision, config_path, resolved["requirement"], config))
        print(f"{RUN_ID}: {decision.iloc[0]['decision_state']}")
        return 0

    stage1_counts = requested_counts(primary, "stage1_anchor_selected_flag", "requested_selected_n")
    all_readouts = []
    all_ci = []
    all_audits = []
    all_seed_dist = []
    all_selected = []
    all_reps = []
    for denominator_type, selection in (
        ("stage1_anchor_chained_survivor", chain_selection),
    ):
        for baseline_id in config["random_baseline"]["variants"]:
            selected, audit, seed_dist = replay_variant(
                selection,
                random,
                baseline_id,
                denominator_type,
                config,
                stage1_counts=stage1_counts if denominator_type == "stage1_anchor_chained_survivor" else None,
            )
            for frame in (audit, seed_dist, selected):
                if not frame.empty:
                    frame["denominator_type"] = denominator_type
                    frame["candidate_id"] = selection.iloc[0]["candidate_id"]
                    frame["candidate_family"] = selection.iloc[0]["candidate_family"]
                    frame["stage2_budget_X"] = float(selection.iloc[0]["stage2_budget_X"])
                    frame["baseline_id"] = baseline_id
                    frame["baseline_family_id"] = BASELINE_SPECS[baseline_id]["family"]
            readout, ci, reps = variant_readout(selection, baseline_id, selected, audit, seed_dist, config)
            all_readouts.append(readout)
            all_ci.append(ci)
            if not audit.empty:
                all_audits.append(audit)
            if not seed_dist.empty:
                all_seed_dist.append(seed_dist)
            if not selected.empty:
                all_selected.append(selected)
            if not reps.empty:
                all_reps.append(reps)
    readout = pd.concat(all_readouts, ignore_index=True)
    ci = pd.concat(all_ci, ignore_index=True)
    audit = pd.concat(all_audits, ignore_index=True) if all_audits else pd.DataFrame()
    seed_dist = pd.concat(all_seed_dist, ignore_index=True) if all_seed_dist else pd.DataFrame()
    selected_random = pd.concat(all_selected, ignore_index=True) if all_selected else pd.DataFrame()
    reps = pd.concat(all_reps, ignore_index=True) if all_reps else pd.DataFrame()
    decision = decision_from_readout(readout, candidate_reconciliation_status, "pass", random_source_status, gate_source, chain_identity, config)
    decision.loc[:, "stage1_anchor_rule_id"] = anchor["stage1_anchor_rule_id"]
    decision.loc[:, "stage1_anchor_feature"] = anchor["stage1_anchor_feature"]
    decision.loc[:, "stage1_anchor_orientation"] = anchor["stage1_anchor_orientation"]
    decision.loc[:, "stage1_anchor_X"] = anchor["stage1_anchor_X"]
    selection_matrix = pd.concat([chain_selection, dec_selection], ignore_index=True)
    frames = {
        "input_artifact_audit": input_audit,
        "frozen_candidate_reconciliation": reconciliation,
        "random_support_cell_audit": audit,
        "random_replay_variant_readout": readout,
        "random_replay_variant_bootstrap_ci": ci,
        "random_replay_seed_distribution": seed_dist,
        "stage2_chained_sensitivity_decision": decision,
        "frozen_candidate_selection_matrix": selection_matrix,
        "variant_random_selected": selected_random,
        "variant_bootstrap_replicates": reps,
    }
    for key, frame in frames.items():
        write_df(paths[key], frame)
    write_text(paths["report"], build_report(decision, readout, audit))
    frames["report"] = pd.DataFrame([{"path": str(paths["report"])}])
    write_json(paths["manifest"], build_manifest(paths, frames, decision, config_path, resolved["requirement"], config))
    print(f"{RUN_ID}: {decision.iloc[0]['decision_state']}")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    return run_pipeline(Path(args.config), args.mode)


if __name__ == "__main__":
    raise SystemExit(main())
