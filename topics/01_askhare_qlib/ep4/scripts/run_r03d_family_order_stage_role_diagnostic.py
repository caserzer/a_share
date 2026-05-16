#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml

SCRIPT_DIR = Path(__file__).resolve().parent
EP4_DIR = SCRIPT_DIR.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from r01_high_recall_probe_fail_fast_common import relpath, topic_path, write_json  # noqa: E402


DEFAULT_CONFIG = EP4_DIR / "configs" / "r03d_family_order_stage_role_diagnostic_v1.yaml"
SPLITS = ["train", "validation", "robustness"]
ALL_SPLITS = SPLITS + ["all"]
PATH_LABELS = {"good_path", "bad_path", "neutral_path"}
PRICE_BUCKETS = {
    "seed_anchor",
    "not_observed",
    "down_or_flat",
    "up_0_5pct",
    "up_5_10pct",
    "up_10_20pct",
    "up_gt_20pct",
    "missing_or_invalid",
}
FINAL_DECISIONS = {
    "supported_order_incremental_edge",
    "stage_role_only_no_order_increment",
    "price_state_proxy_only",
    "insufficient_denominator",
    "blocked_missing_required_input",
    "blocked_upstream_validation_failed",
    "blocked_validation_failed",
}


def _read_yaml(path: Path) -> dict[str, Any]:
    with topic_path(path).open("r", encoding="utf-8") as file:
        return yaml.safe_load(file) or {}


def _read_json(path: str | Path) -> dict[str, Any]:
    p = topic_path(Path(path))
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def _write_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)


def _write_parquet(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False)


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _bool_scalar(value: Any) -> bool:
    if pd.isna(value):
        return False
    return str(value).strip().lower() in {"true", "1", "yes"}


def _boolish(series: pd.Series) -> pd.Series:
    return series.astype(str).str.lower().isin({"true", "1", "yes"})


def _num(value: Any) -> float:
    out = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    return float(out) if pd.notna(out) else np.nan


def _safe_div(num: float, den: float) -> float:
    return float(num) / float(den) if den else np.nan


def _quantile(series: pd.Series, q: float) -> float:
    vals = pd.to_numeric(series, errors="coerce").dropna()
    return float(vals.quantile(q)) if len(vals) else np.nan


def _family_list(value: Any) -> list[str]:
    if pd.isna(value):
        return []
    text = str(value)
    if not text or text == "none":
        return []
    return sorted([part for part in text.split("|") if part and part != "none"])


def _family_key(values: list[str] | set[str]) -> str:
    vals = sorted(str(v) for v in values if str(v) and str(v) != "none")
    return "|".join(vals) if vals else "none"


def _stage_bucket(kth: Any) -> str:
    if pd.isna(kth):
        return "not_observed"
    kth_int = int(kth)
    if kth_int <= 3:
        return f"fresh_{kth_int}"
    return "fresh_4plus"


def _count_bucket(value: Any) -> str:
    if pd.isna(value):
        return "missing"
    val = int(value)
    return str(val) if val <= 3 else "4plus"


def _sample_status(den: int, min_count: int) -> str:
    return "sufficient" if int(den) >= int(min_count) else "thin_episode_denominator"


def _path_flags(label: Any) -> tuple[bool, bool]:
    return str(label) == "good_path", str(label) == "bad_path"


def _presence_signature(family_set: Any, family_universe: list[str]) -> str:
    families = set(_family_list(family_set))
    return "|".join(f"contains_{family}={1 if family in families else 0}" for family in family_universe)


def _normalize_dates(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    for col in cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")
    return df


def _readiness(config: dict[str, Any]) -> tuple[pd.DataFrame, bool, str]:
    rows: list[dict[str, Any]] = []

    def add(role: str, path_value: str, validation_status: str = "exists_only", row_count: Any = np.nan) -> None:
        path = topic_path(Path(path_value))
        exists = path.exists()
        ready = exists and validation_status not in {"failed", "missing"}
        rows.append(
            {
                "artifact_role": role,
                "artifact_path": path_value,
                "exists": bool(exists),
                "validation_status": validation_status,
                "row_count": row_count,
                "readiness_status": "ready" if ready else "blocked",
                "failure_reason": "" if ready else ("missing" if not exists else validation_status),
            }
        )

    validations = [
        ("r03b_validation", config["upstream_r03b"]["validation"]),
        ("r03c_validation", config["upstream_r03c"]["validation"]),
    ]
    statuses = {}
    for role, path in validations:
        status = _read_json(path).get("validation_status", "missing")
        statuses[role] = status
        add(role, path, status)

    for role, path in [
        ("r03b_manifest", config["upstream_r03b"]["manifest"]),
        ("r03b_seed_episode_panel", config["upstream_r03b"]["seed_episode_panel"]),
        ("r03b_sequence_step_panel", config["upstream_r03b"]["sequence_step_panel"]),
        ("r03b_signal_timeline_panel", config["upstream_r03b"]["signal_timeline_panel"]),
        ("r03c_manifest", config["upstream_r03c"]["manifest"]),
        ("r03c_fresh_step_price_panel", config["upstream_r03c"]["fresh_step_price_panel"]),
        ("r03c_checkpoint_price_state_panel", config["upstream_r03c"]["checkpoint_price_state_panel"]),
        ("r03c_grouping_explanatory_power_comparison", config["upstream_r03c"]["grouping_explanatory_power_comparison"]),
        ("r03c_survival_price_bias_audit", config["upstream_r03c"]["survival_price_bias_audit"]),
    ]:
        p = topic_path(Path(path))
        row_count = np.nan
        if p.exists() and p.suffix == ".parquet":
            row_count = len(pd.read_parquet(p, columns=[]))
        elif p.exists() and p.suffix == ".csv":
            row_count = sum(1 for _ in p.open("r", encoding="utf-8")) - 1
        add(role, path, "exists_only", row_count)

    df = pd.DataFrame(rows)
    if not bool(df["exists"].all()):
        return df, False, "blocked_missing_required_input"
    if any(status != "passed" for status in statuses.values()):
        return df, False, "blocked_upstream_validation_failed"
    return df, True, "ready"


def _load_inputs(config: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    seeds = pd.read_parquet(topic_path(Path(config["upstream_r03b"]["seed_episode_panel"])))
    step = pd.read_parquet(topic_path(Path(config["upstream_r03b"]["sequence_step_panel"])))
    fresh = pd.read_parquet(topic_path(Path(config["upstream_r03c"]["fresh_step_price_panel"])))
    seeds = _normalize_dates(seeds, ["signal_date", "entry_date", "seed_trade_date", "seed_entry_date"])
    step = _normalize_dates(step, ["step_signal_date"])
    fresh = _normalize_dates(fresh, ["seed_trade_date", "seed_entry_date", "step_signal_date", "fresh_entry_date"])
    return seeds, step, fresh


def _validate_family_tokens(frames: list[pd.DataFrame], cols: list[str], family_universe: list[str]) -> None:
    allowed = set(family_universe)
    bad: set[str] = set()
    for frame in frames:
        for col in cols:
            if col not in frame.columns:
                continue
            for value in frame[col].dropna().astype(str).unique():
                for family in _family_list(value):
                    if family not in allowed:
                        bad.add(family)
    if bad:
        raise ValueError(f"unknown family tokens: {sorted(bad)}")


def _build_order_step_panel(fresh: pd.DataFrame, family_universe: list[str]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    sort_cols = ["seed_episode_id", "step_offset", "step_signal_date", "added_family_set"]
    for _, group in fresh.sort_values(sort_cols).groupby("seed_episode_id", sort=False):
        prior = set(_family_list(group.iloc[0]["seed_family_set"]))
        first_added = group.iloc[0]["added_family_set"] if len(group) else "none"
        for _, row in group.iterrows():
            added = set(_family_list(row["added_family_set"]))
            payload = row.to_dict()
            before = set(prior)
            after = before | added
            payload.update(
                {
                    "family_presence_signature_before_step": _family_key(before),
                    "family_presence_signature_after_step": _family_key(after),
                    "family_presence_signature_after_step_bucket": _family_key(after),
                    "new_family_stage_position": len(after),
                    "stage_position_bucket": _stage_bucket(row["kth_fresh_step_index_raw"]),
                    "last_added_family_set": _family_key(added),
                    "last_added_family_count": len(added),
                    "first_added_family_set": first_added,
                    "prefix_family_set_before_step": _family_key(before),
                    "prefix_family_count_before_step": len(before),
                    "is_seed_family_reappearing": bool(added & set(_family_list(row["seed_family_set"]))),
                    "is_new_distinct_family_step": bool(added - before),
                    "is_single_family_step": len(added) == 1,
                    "is_multi_family_step": len(added) > 1,
                    "price_state_bucket": row.get("wait_return_bucket", "missing_or_invalid"),
                    "fresh_count_so_far": int(row["kth_fresh_step_index_raw"]),
                    "seed_P_good_flag": str(row.get("seed_path_label")) == "good_path",
                    "seed_P_bad_flag": str(row.get("seed_path_label")) == "bad_path",
                    "fresh_anchor_big_winner": row.get("fresh_big_winner_forward_h120_close_anchor"),
                    "fresh_P_good_flag": str(row.get("fresh_path_label")) == "good_path",
                    "fresh_P_bad_flag": str(row.get("fresh_path_label")) == "bad_path",
                }
            )
            rows.append(payload)
            prior = after
    out = pd.DataFrame(rows)
    if not out.empty:
        train_counts = out.loc[out["split"].eq("train")].groupby("last_added_family_set").size()
        exact = set(train_counts.loc[train_counts >= 80].index)
        out["last_added_family_set_bucket"] = out["last_added_family_set"].where(
            out["last_added_family_set"].isin(exact),
            "other_sparse_last_added_family",
        )
        presence_counts = out.loc[out["split"].eq("train")].groupby("family_presence_signature_after_step").size()
        exact_presence = set(presence_counts.loc[presence_counts >= 80].index)
        out["family_presence_signature_after_step_bucket"] = out["family_presence_signature_after_step"].where(
            out["family_presence_signature_after_step"].isin(exact_presence),
            "other_sparse_family_presence",
        )
    return out


def _seed_base_dict(seeds: pd.DataFrame) -> dict[Any, dict[str, Any]]:
    return seeds.set_index("seed_episode_id", drop=False).to_dict(orient="index")


def _build_stage_role_panel(seeds: pd.DataFrame, order_step: pd.DataFrame, family_universe: list[str]) -> pd.DataFrame:
    fresh_by_seed = {sid: group.copy() for sid, group in order_step.groupby("seed_episode_id", sort=False)}
    rows: list[dict[str, Any]] = []
    for seed in seeds.itertuples(index=False):
        seed_dict = seed._asdict()
        seed_families = set(_family_list(seed_dict["seed_family_set"]))
        steps = fresh_by_seed.get(seed_dict["seed_episode_id"], pd.DataFrame())
        for family in family_universe:
            payload = {
                "seed_episode_id": seed_dict["seed_episode_id"],
                "instrument_id": seed_dict["instrument_id"],
                "split": seed_dict["split"],
                "family": family,
                "seed_complete_h120_close_anchor_flag": seed_dict.get("complete_h120_close_anchor_flag"),
                "seed_anchor_big_winner": seed_dict.get("big_winner_forward_h120_close_anchor"),
                "seed_path_label": seed_dict.get("label"),
            }
            if family in seed_families:
                payload.update(
                    {
                        "first_observed_stage": "seed",
                        "first_observed_offset": 0,
                        "first_observed_signal_date": seed_dict["seed_trade_date"],
                        "first_observed_as_seed": True,
                        "first_observed_as_fresh": False,
                        "first_observed_after_wait_return_bucket": "seed_anchor",
                        "first_observed_price_state_bucket": "seed_anchor",
                        "first_observed_wait_return_to_entry": 0.0,
                        "fresh_complete_h120_close_anchor_flag_if_observed_as_fresh": np.nan,
                        "fresh_anchor_big_winner_if_observed_as_fresh": np.nan,
                        "fresh_path_label_if_observed_as_fresh": np.nan,
                    }
                )
            else:
                observed = pd.DataFrame()
                if not steps.empty:
                    observed = steps.loc[steps["added_family_set"].map(lambda value: family in _family_list(value))]
                if observed.empty:
                    payload.update(
                        {
                            "first_observed_stage": "not_observed",
                            "first_observed_offset": np.nan,
                            "first_observed_signal_date": pd.NaT,
                            "first_observed_as_seed": False,
                            "first_observed_as_fresh": False,
                            "first_observed_after_wait_return_bucket": "not_observed",
                            "first_observed_price_state_bucket": "not_observed",
                            "first_observed_wait_return_to_entry": np.nan,
                            "fresh_complete_h120_close_anchor_flag_if_observed_as_fresh": np.nan,
                            "fresh_anchor_big_winner_if_observed_as_fresh": np.nan,
                            "fresh_path_label_if_observed_as_fresh": np.nan,
                        }
                    )
                else:
                    first = observed.sort_values(["step_offset", "step_signal_date"]).iloc[0]
                    payload.update(
                        {
                            "first_observed_stage": _stage_bucket(first["kth_fresh_step_index_raw"]),
                            "first_observed_offset": first["step_offset"],
                            "first_observed_signal_date": first["step_signal_date"],
                            "first_observed_as_seed": False,
                            "first_observed_as_fresh": True,
                            "first_observed_after_wait_return_bucket": first["wait_return_bucket"],
                            "first_observed_price_state_bucket": first["price_state_bucket"],
                            "first_observed_wait_return_to_entry": first["wait_return_to_fresh_entry"],
                            "fresh_complete_h120_close_anchor_flag_if_observed_as_fresh": first[
                                "fresh_complete_h120_close_anchor_flag"
                            ],
                            "fresh_anchor_big_winner_if_observed_as_fresh": first["fresh_big_winner_forward_h120_close_anchor"],
                            "fresh_path_label_if_observed_as_fresh": first["fresh_path_label"],
                        }
                    )
            rows.append(payload)
    out = pd.DataFrame(rows)
    out["seed_P_good_flag"] = out["seed_path_label"].eq("good_path")
    out["seed_P_bad_flag"] = out["seed_path_label"].eq("bad_path")
    out["fresh_P_good_flag"] = out["fresh_path_label_if_observed_as_fresh"].eq("good_path")
    out["fresh_P_bad_flag"] = out["fresh_path_label_if_observed_as_fresh"].eq("bad_path")
    return out


def _terminal_reason(seed: dict[str, Any], prefix_index: int, prefix_offset: float, has_steps: bool, next_step: pd.Series | None) -> str:
    failure = _num(seed.get("observable_failure_offset"))
    if prefix_index == 0 and not has_steps:
        return "no_clean_fresh"
    next_offset = _num(next_step.get("step_offset")) if next_step is not None else np.nan
    if pd.notna(failure) and failure > prefix_offset and (pd.isna(next_offset) or failure < next_offset):
        return "failed_before_next_clean_fresh"
    if next_step is None:
        return "no_more_clean_fresh_before_t30"
    return "complete_after_prefix"


def _build_transition_candidate_panel(
    seeds: pd.DataFrame,
    order_step: pd.DataFrame,
    family_universe: list[str],
) -> tuple[pd.DataFrame, int]:
    fresh_by_seed = {sid: group.sort_values(["kth_fresh_step_index_raw"]).copy() for sid, group in order_step.groupby("seed_episode_id")}
    rows: list[dict[str, Any]] = []
    exhausted_prefix_count = 0
    universe = set(family_universe)
    for seed in seeds.itertuples(index=False):
        seed_dict = seed._asdict()
        steps = fresh_by_seed.get(seed_dict["seed_episode_id"], pd.DataFrame())
        prefix_states: list[tuple[int, set[str], pd.Series | None]] = [(0, set(_family_list(seed_dict["seed_family_set"])), None)]
        for _, step in steps.iterrows():
            prefix_states.append((int(step["kth_fresh_step_index_raw"]), set(_family_list(step["cumulative_distinct_family_set_after_step"])), step))
        for prefix_index, prefix_set, prefix_row in prefix_states:
            candidates = sorted(universe - prefix_set)
            if not candidates:
                exhausted_prefix_count += 1
                continue
            if prefix_row is None:
                prefix_signal_date = seed_dict["seed_trade_date"]
                prefix_offset = 0
                prefix_offset_bucket = "seed"
                wait_bucket = "seed_anchor"
                price_state_bucket = "seed_anchor"
            else:
                prefix_signal_date = prefix_row["step_signal_date"]
                prefix_offset = int(prefix_row["step_offset"])
                prefix_offset_bucket = prefix_row["kth_fresh_offset_bucket"]
                wait_bucket = prefix_row["wait_return_bucket"]
                price_state_bucket = prefix_row["price_state_bucket"]
            future = steps.loc[pd.to_numeric(steps["step_offset"], errors="coerce") > prefix_offset] if not steps.empty else pd.DataFrame()
            next_step = None if future.empty else future.iloc[0]
            terminal = next_step is None
            terminal_reason = _terminal_reason(seed_dict, prefix_index, float(prefix_offset), not steps.empty, next_step)
            candidate_count = len(candidates)
            for candidate in candidates:
                occurs_next = bool(next_step is not None and candidate in _family_list(next_step["added_family_set"]))
                within_5 = bool(
                    not future.empty
                    and future.loc[
                        pd.to_numeric(future["step_offset"], errors="coerce").sub(prefix_offset).between(1, 5),
                        "added_family_set",
                    ].map(lambda value: candidate in _family_list(value)).any()
                )
                within_10 = bool(
                    not future.empty
                    and future.loc[
                        pd.to_numeric(future["step_offset"], errors="coerce").sub(prefix_offset).between(1, 10),
                        "added_family_set",
                    ].map(lambda value: candidate in _family_list(value)).any()
                )
                payload = {
                    "seed_episode_id": seed_dict["seed_episode_id"],
                    "instrument_id": seed_dict["instrument_id"],
                    "split": seed_dict["split"],
                    "prefix_step_index": prefix_index,
                    "prefix_signal_date": prefix_signal_date,
                    "prefix_offset": prefix_offset,
                    "prefix_offset_bucket": prefix_offset_bucket,
                    "prefix_family_set": _family_key(prefix_set),
                    "prefix_family_count": len(prefix_set),
                    "prefix_family_count_bucket": _count_bucket(len(prefix_set)),
                    "candidate_next_family": candidate,
                    "candidate_family_count_at_prefix": candidate_count,
                    "candidate_weight": 1.0 / candidate_count,
                    "candidate_occurs_at_next_step": occurs_next,
                    "candidate_occurs_within_next_5td": within_5,
                    "candidate_occurs_within_next_10td": within_10,
                    "terminal_after_prefix": terminal,
                    "terminal_reason": terminal_reason if terminal else "",
                    "next_step_signal_date": pd.NaT if next_step is None else next_step["step_signal_date"],
                    "next_step_offset": np.nan if next_step is None else next_step["step_offset"],
                    "next_step_added_family_set": "none" if next_step is None else next_step["added_family_set"],
                    "fresh_count_so_far": prefix_index,
                    "wait_return_bucket": wait_bucket,
                    "price_state_bucket": price_state_bucket,
                    "seed_complete_h120_close_anchor_flag": seed_dict.get("complete_h120_close_anchor_flag"),
                    "seed_anchor_big_winner": seed_dict.get("big_winner_forward_h120_close_anchor"),
                    "seed_path_label": seed_dict.get("label"),
                    "next_step_fresh_complete_h120_close_anchor_flag": np.nan
                    if next_step is None
                    else next_step["fresh_complete_h120_close_anchor_flag"],
                    "next_step_fresh_anchor_big_winner": np.nan
                    if next_step is None
                    else next_step["fresh_big_winner_forward_h120_close_anchor"],
                    "next_step_fresh_path_label": np.nan if next_step is None else next_step["fresh_path_label"],
                    "candidate_fresh_complete_h120_close_anchor_flag": np.nan,
                    "candidate_fresh_anchor_big_winner": np.nan,
                    "candidate_fresh_path_label": np.nan,
                }
                if occurs_next and next_step is not None:
                    payload["candidate_fresh_complete_h120_close_anchor_flag"] = next_step[
                        "fresh_complete_h120_close_anchor_flag"
                    ]
                    payload["candidate_fresh_anchor_big_winner"] = next_step["fresh_big_winner_forward_h120_close_anchor"]
                    payload["candidate_fresh_path_label"] = next_step["fresh_path_label"]
                rows.append(payload)
    out = pd.DataFrame(rows)
    if not out.empty:
        out["seed_P_good_flag"] = out["seed_path_label"].eq("good_path")
        out["seed_P_bad_flag"] = out["seed_path_label"].eq("bad_path")
        out["next_step_fresh_P_good_flag"] = out["next_step_fresh_path_label"].eq("good_path")
        out["next_step_fresh_P_bad_flag"] = out["next_step_fresh_path_label"].eq("bad_path")
        out["candidate_fresh_P_good_flag"] = out["candidate_fresh_path_label"].eq("good_path")
        out["candidate_fresh_P_bad_flag"] = out["candidate_fresh_path_label"].eq("bad_path")
    return out, exhausted_prefix_count


def _build_pair_order_panel(
    seeds: pd.DataFrame,
    stage: pd.DataFrame,
    order_step: pd.DataFrame,
    family_universe: list[str],
) -> pd.DataFrame:
    seed_map = _seed_base_dict(seeds)
    step_by_seed = {sid: group.copy() for sid, group in order_step.groupby("seed_episode_id", sort=False)}
    rows: list[dict[str, Any]] = []
    observed = stage.loc[~stage["first_observed_stage"].eq("not_observed")].copy()
    for seed_id, group in observed.groupby("seed_episode_id", sort=False):
        if len(group) < 2:
            continue
        by_family = {row.family: row for row in group.itertuples(index=False)}
        for fam_a, fam_b in combinations(sorted(by_family), 2):
            a = by_family[fam_a]
            b = by_family[fam_b]
            a_offset = _num(a.first_observed_offset)
            b_offset = _num(b.first_observed_offset)
            same_offset = pd.notna(a_offset) and pd.notna(b_offset) and a_offset == b_offset
            if same_offset:
                order_key = "same_offset_unordered"
            elif a_offset < b_offset:
                order_key = "A_before_B"
            else:
                order_key = "B_before_A"
            completion_offset = max(a_offset, b_offset)
            completion_step = None
            if completion_offset > 0:
                steps = step_by_seed.get(seed_id, pd.DataFrame())
                comp_family = fam_a if a_offset == completion_offset else fam_b
                match = steps.loc[
                    pd.to_numeric(steps["step_offset"], errors="coerce").eq(completion_offset)
                    & steps["added_family_set"].map(lambda value: comp_family in _family_list(value))
                ]
                completion_step = None if match.empty else match.iloc[0]
            seed = seed_map[seed_id]
            rows.append(
                {
                    "seed_episode_id": seed_id,
                    "instrument_id": seed["instrument_id"],
                    "split": seed["split"],
                    "family_a": fam_a,
                    "family_b": fam_b,
                    "unordered_pair_key": f"{fam_a}|{fam_b}",
                    "pair_order_key": order_key,
                    "family_a_first_stage": a.first_observed_stage,
                    "family_b_first_stage": b.first_observed_stage,
                    "family_a_first_offset": a_offset,
                    "family_b_first_offset": b_offset,
                    "same_offset_pair_flag": same_offset,
                    "pair_order_observable": not same_offset,
                    "pair_completion_offset": completion_offset,
                    "pair_completion_wait_return_bucket": "seed_anchor"
                    if completion_step is None
                    else completion_step["wait_return_bucket"],
                    "seed_complete_h120_close_anchor_flag": seed.get("complete_h120_close_anchor_flag"),
                    "seed_anchor_big_winner": seed.get("big_winner_forward_h120_close_anchor"),
                    "seed_path_label": seed.get("label"),
                    "pair_completion_fresh_complete_h120_close_anchor_flag": np.nan
                    if completion_step is None
                    else completion_step["fresh_complete_h120_close_anchor_flag"],
                    "pair_completion_fresh_anchor_big_winner": np.nan
                    if completion_step is None
                    else completion_step["fresh_big_winner_forward_h120_close_anchor"],
                    "pair_completion_fresh_path_label": np.nan if completion_step is None else completion_step["fresh_path_label"],
                }
            )
    out = pd.DataFrame(rows)
    if not out.empty:
        out["seed_P_good_flag"] = out["seed_path_label"].eq("good_path")
        out["seed_P_bad_flag"] = out["seed_path_label"].eq("bad_path")
        out["fresh_P_good_flag"] = out["pair_completion_fresh_path_label"].eq("good_path")
        out["fresh_P_bad_flag"] = out["pair_completion_fresh_path_label"].eq("bad_path")
        train_counts = out.loc[out["split"].eq("train")].groupby("unordered_pair_key").size()
        exact_pairs = set(train_counts.loc[train_counts >= 60].index)
        out["unordered_pair_key_bucket"] = out["unordered_pair_key"].where(out["unordered_pair_key"].isin(exact_pairs), "other_sparse_pair")
    return out


def _freeze_prefix_buckets(transition: pd.DataFrame, min_exact: int) -> pd.DataFrame:
    if transition.empty:
        return transition
    states = transition[["split", "seed_episode_id", "prefix_step_index", "prefix_family_set"]].drop_duplicates()
    counts = states.loc[states["split"].eq("train")].groupby("prefix_family_set").size()
    exact = set(counts.loc[counts >= int(min_exact)].index)
    out = transition.copy()
    out["prefix_family_set_bucket"] = out["prefix_family_set"].where(out["prefix_family_set"].isin(exact), "other_sparse_prefix")
    return out


def _seed_metrics(df: pd.DataFrame, complete_col: str, bw_col: str, label_col: str, weight_col: str | None = None) -> dict[str, Any]:
    if df.empty:
        return {
            "seed_anchor_big_winner_denominator": 0.0,
            "seed_anchor_big_winner_rate": np.nan,
            "seed_path_denominator": 0.0,
            "seed_P_good": np.nan,
            "seed_P_bad": np.nan,
        }
    weights = pd.to_numeric(df[weight_col], errors="coerce").fillna(0.0) if weight_col else pd.Series(1.0, index=df.index)
    complete = _boolish(df[complete_col]) if complete_col in df.columns else pd.Series(False, index=df.index)
    bw = _boolish(df[bw_col]) if bw_col in df.columns else pd.Series(False, index=df.index)
    label = df[label_col].astype(str) if label_col in df.columns else pd.Series("", index=df.index)
    bw_den = float(weights[complete].sum())
    bw_count = float(weights[complete & bw].sum())
    path_mask = label.isin(PATH_LABELS)
    path_den = float(weights[path_mask].sum())
    return {
        "seed_anchor_big_winner_denominator": bw_den,
        "seed_anchor_big_winner_rate": _safe_div(bw_count, bw_den),
        "seed_path_denominator": path_den,
        "seed_P_good": _safe_div(float(weights[path_mask & label.eq("good_path")].sum()), path_den),
        "seed_P_bad": _safe_div(float(weights[path_mask & label.eq("bad_path")].sum()), path_den),
    }


def _fresh_metrics(df: pd.DataFrame, complete_col: str, bw_col: str, label_col: str, weight_col: str | None = None) -> dict[str, Any]:
    if df.empty or complete_col not in df.columns:
        return {
            "fresh_anchor_big_winner_denominator": 0.0,
            "fresh_anchor_big_winner_rate": np.nan,
            "fresh_path_denominator": 0.0,
            "fresh_P_good": np.nan,
            "fresh_P_bad": np.nan,
        }
    weights = pd.to_numeric(df[weight_col], errors="coerce").fillna(0.0) if weight_col else pd.Series(1.0, index=df.index)
    complete = _boolish(df[complete_col])
    bw = _boolish(df[bw_col]) if bw_col in df.columns else pd.Series(False, index=df.index)
    label = df[label_col].astype(str) if label_col in df.columns else pd.Series("", index=df.index)
    bw_den = float(weights[complete].sum())
    bw_count = float(weights[complete & bw].sum())
    path_mask = label.isin(PATH_LABELS)
    path_den = float(weights[path_mask].sum())
    return {
        "fresh_anchor_big_winner_denominator": bw_den,
        "fresh_anchor_big_winner_rate": _safe_div(bw_count, bw_den),
        "fresh_path_denominator": path_den,
        "fresh_P_good": _safe_div(float(weights[path_mask & label.eq("good_path")].sum()), path_den),
        "fresh_P_bad": _safe_div(float(weights[path_mask & label.eq("bad_path")].sum()), path_den),
    }


def _fresh_path_stats(df: pd.DataFrame, gain_col: str = "fresh_max_gain_120d", drawdown_col: str = "fresh_max_drawdown_120d") -> dict[str, Any]:
    return {
        "fresh_max_gain_120d_p50": _quantile(df[gain_col], 0.50) if gain_col in df.columns else np.nan,
        "fresh_max_drawdown_120d_p50": _quantile(df[drawdown_col], 0.50) if drawdown_col in df.columns else np.nan,
    }


def _family_position_summary(stage: pd.DataFrame, thresholds: dict[str, Any]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for split in ALL_SPLITS:
        base = stage if split == "all" else stage.loc[stage["split"].eq(split)]
        if base.empty:
            continue
        for keys, group in base.groupby(["family", "first_observed_stage"], dropna=False, sort=True):
            family, observed_stage = keys
            seed = _seed_metrics(group, "seed_complete_h120_close_anchor_flag", "seed_anchor_big_winner", "seed_path_label")
            fresh = _fresh_metrics(
                group,
                "fresh_complete_h120_close_anchor_flag_if_observed_as_fresh",
                "fresh_anchor_big_winner_if_observed_as_fresh",
                "fresh_path_label_if_observed_as_fresh",
            )
            den = int(len(group))
            rows.append(
                {
                    "split": split,
                    "family": family,
                    "first_observed_stage": observed_stage,
                    "episode_count": den,
                    "unique_instrument_count": int(group["instrument_id"].nunique()),
                    "unique_signal_date_count": int(group["first_observed_signal_date"].nunique())
                    if observed_stage != "not_observed"
                    else int(group["seed_episode_id"].nunique()),
                    **seed,
                    **fresh,
                    "wait_return_p50": _quantile(group["first_observed_wait_return_to_entry"], 0.50),
                    "fresh_max_gain_120d_p50": np.nan,
                    "fresh_max_drawdown_120d_p50": np.nan,
                    "sample_sufficiency_status": _sample_status(den, thresholds["min_seed_episode_count"]),
                }
            )
    return pd.DataFrame(rows)


def _stage_role_for_group(group: pd.DataFrame, thresholds: dict[str, Any]) -> str:
    stage = str(group["first_observed_stage"].iloc[0])
    wait = pd.to_numeric(group["first_observed_wait_return_to_entry"], errors="coerce")
    median_wait = float(wait.dropna().median()) if wait.notna().any() else np.nan
    price_share = _safe_div(
        int(group["first_observed_price_state_bucket"].isin(["up_10_20pct", "up_gt_20pct"]).sum()),
        len(group),
    )
    if (pd.notna(median_wait) and median_wait > 0.10) or price_share >= float(thresholds["stage_role_dominant_price_bucket_share"]):
        return "lagging_price_state_proxy"
    if stage in {"fresh_2", "fresh_3", "fresh_4plus"} and pd.notna(median_wait) and median_wait > 0.05:
        return "late_continuation"
    if stage in {"fresh_1", "fresh_2"} and pd.notna(median_wait) and 0 <= median_wait <= 0.10:
        return "early_confirmation"
    if stage == "seed" or (stage == "fresh_1" and pd.notna(median_wait) and median_wait <= 0.05):
        return "probe_candidate"
    return "not_supported"


def _stage_role_summary(stage: pd.DataFrame, thresholds: dict[str, Any]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    role_rows = []
    for split in ALL_SPLITS:
        base = stage if split == "all" else stage.loc[stage["split"].eq(split)]
        if base.empty:
            continue
        for keys, group in base.groupby(["family", "first_observed_stage"], dropna=False, sort=True):
            role = _stage_role_for_group(group, thresholds)
            role_group = group.copy()
            role_group["stage_role_candidate"] = role
            role_rows.append(role_group)
    if not role_rows:
        return pd.DataFrame()
    role_panel = pd.concat(role_rows, ignore_index=True)
    for split in ALL_SPLITS:
        base = role_panel if split == "all" else role_panel.loc[role_panel["split"].eq(split)]
        if base.empty:
            continue
        for keys, group in base.groupby(["family", "stage_role_candidate"], dropna=False, sort=True):
            family, role = keys
            seed = _seed_metrics(group, "seed_complete_h120_close_anchor_flag", "seed_anchor_big_winner", "seed_path_label")
            fresh = _fresh_metrics(
                group,
                "fresh_complete_h120_close_anchor_flag_if_observed_as_fresh",
                "fresh_anchor_big_winner_if_observed_as_fresh",
                "fresh_path_label_if_observed_as_fresh",
            )
            den = int(len(group))
            rows.append(
                {
                    "split": split,
                    "family": family,
                    "stage_role_candidate": role,
                    "episode_count": den,
                    "stage_count": int(group["first_observed_stage"].nunique()),
                    "median_wait_return": _quantile(group["first_observed_wait_return_to_entry"], 0.50),
                    "up_10pct_plus_price_state_share": _safe_div(
                        int(group["first_observed_price_state_bucket"].isin(["up_10_20pct", "up_gt_20pct"]).sum()),
                        den,
                    ),
                    **seed,
                    **fresh,
                    "sample_sufficiency_status": _sample_status(den, thresholds["min_seed_episode_count"]),
                }
            )
    return pd.DataFrame(rows)


def _transition_summary(transition: pd.DataFrame, thresholds: dict[str, Any]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    group_cols = ["prefix_family_count_bucket", "prefix_family_set_bucket", "candidate_next_family", "candidate_occurs_at_next_step"]
    for split in ALL_SPLITS:
        base = transition if split == "all" else transition.loc[transition["split"].eq(split)]
        if base.empty:
            continue
        for keys, group in base.groupby(group_cols, dropna=False, sort=True):
            payload = {"split": split, **dict(zip(group_cols, keys))}
            seed = _seed_metrics(group, "seed_complete_h120_close_anchor_flag", "seed_anchor_big_winner", "seed_path_label", "candidate_weight")
            next_fresh = _fresh_metrics(
                group,
                "next_step_fresh_complete_h120_close_anchor_flag",
                "next_step_fresh_anchor_big_winner",
                "next_step_fresh_path_label",
                "candidate_weight",
            )
            candidate_fresh = _fresh_metrics(
                group,
                "candidate_fresh_complete_h120_close_anchor_flag",
                "candidate_fresh_anchor_big_winner",
                "candidate_fresh_path_label",
                "candidate_weight",
            )
            weight_sum = float(pd.to_numeric(group["candidate_weight"], errors="coerce").fillna(0).sum())
            payload.update(
                {
                    "candidate_row_count": int(len(group)),
                    "candidate_weight_sum": weight_sum,
                    "seed_episode_count": int(group["seed_episode_id"].nunique()),
                    "candidate_occurrence_rate": _safe_div(
                        float((pd.to_numeric(group["candidate_weight"], errors="coerce").fillna(0) * group["candidate_occurs_at_next_step"].astype(float)).sum()),
                        weight_sum,
                    ),
                    "seed_anchor_big_winner_rate": seed["seed_anchor_big_winner_rate"],
                    "seed_P_good": seed["seed_P_good"],
                    "seed_P_bad": seed["seed_P_bad"],
                    "next_step_fresh_anchor_big_winner_rate_weighted": next_fresh["fresh_anchor_big_winner_rate"],
                    "next_step_fresh_P_good_weighted": next_fresh["fresh_P_good"],
                    "next_step_fresh_P_bad_weighted": next_fresh["fresh_P_bad"],
                    "candidate_fresh_anchor_big_winner_rate": candidate_fresh["fresh_anchor_big_winner_rate"],
                    "candidate_fresh_P_good": candidate_fresh["fresh_P_good"],
                    "candidate_fresh_P_bad": candidate_fresh["fresh_P_bad"],
                    "wait_return_p50": np.nan,
                    "sample_sufficiency_status": _sample_status(int(weight_sum), thresholds["min_split_denominator"]),
                }
            )
            rows.append(payload)
    return pd.DataFrame(rows)


def _pair_summary(pair: pd.DataFrame, thresholds: dict[str, Any]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    if pair.empty:
        return pd.DataFrame()
    for split in ALL_SPLITS:
        base = pair if split == "all" else pair.loc[pair["split"].eq(split)]
        if base.empty:
            continue
        for keys, group in base.groupby(["unordered_pair_key", "pair_order_key"], dropna=False, sort=True):
            pair_key, order_key = keys
            opposite = base.loc[base["unordered_pair_key"].eq(pair_key) & ~base["pair_order_key"].eq(order_key)]
            seed = _seed_metrics(group, "seed_complete_h120_close_anchor_flag", "seed_anchor_big_winner", "seed_path_label")
            fresh = _fresh_metrics(
                group,
                "pair_completion_fresh_complete_h120_close_anchor_flag",
                "pair_completion_fresh_anchor_big_winner",
                "pair_completion_fresh_path_label",
            )
            opp_seed = _seed_metrics(opposite, "seed_complete_h120_close_anchor_flag", "seed_anchor_big_winner", "seed_path_label")
            opp_fresh = _fresh_metrics(
                opposite,
                "pair_completion_fresh_complete_h120_close_anchor_flag",
                "pair_completion_fresh_anchor_big_winner",
                "pair_completion_fresh_path_label",
            )
            den = int(len(group))
            opposite_count = int(len(opposite))
            material = abs(_num(fresh["fresh_anchor_big_winner_rate"]) - _num(opp_fresh["fresh_anchor_big_winner_rate"]))
            if den < thresholds["min_pair_episode_count"] or opposite_count < thresholds["min_pair_episode_count"]:
                status = "insufficient_pair_denominator"
            elif order_key == "same_offset_unordered":
                status = "same_offset_only"
            elif pd.notna(material) and material >= thresholds["min_material_rate_lift_pp"]:
                status = "candidate_order_asymmetry"
            else:
                status = "no_material_asymmetry"
            rows.append(
                {
                    "split": split,
                    "unordered_pair_key": pair_key,
                    "pair_order_key": order_key,
                    "episode_count": den,
                    "pair_completion_count": den,
                    "same_offset_pair_count": int(group["same_offset_pair_flag"].sum()),
                    "seed_anchor_big_winner_rate": seed["seed_anchor_big_winner_rate"],
                    "seed_P_good": seed["seed_P_good"],
                    "seed_P_bad": seed["seed_P_bad"],
                    "pair_completion_fresh_anchor_big_winner_rate": fresh["fresh_anchor_big_winner_rate"],
                    "pair_completion_fresh_P_good": fresh["fresh_P_good"],
                    "pair_completion_fresh_P_bad": fresh["fresh_P_bad"],
                    "pair_completion_wait_return_p50": np.nan,
                    "sample_sufficiency_status": _sample_status(den, thresholds["min_pair_episode_count"]),
                    "opposite_order_episode_count": opposite_count,
                    "seed_anchor_big_winner_rate_diff_vs_opposite_order": _num(seed["seed_anchor_big_winner_rate"])
                    - _num(opp_seed["seed_anchor_big_winner_rate"]),
                    "seed_P_good_diff_vs_opposite_order": _num(seed["seed_P_good"]) - _num(opp_seed["seed_P_good"]),
                    "fresh_anchor_big_winner_rate_diff_vs_opposite_order": _num(fresh["fresh_anchor_big_winner_rate"])
                    - _num(opp_fresh["fresh_anchor_big_winner_rate"]),
                    "fresh_P_good_diff_vs_opposite_order": _num(fresh["fresh_P_good"]) - _num(opp_fresh["fresh_P_good"]),
                    "asymmetry_status": status,
                }
            )
    return pd.DataFrame(rows)


def _last_added_summary(order_step: pd.DataFrame, thresholds: dict[str, Any]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    group_cols = ["kth_fresh_step_bucket", "kth_fresh_offset_bucket", "wait_return_bucket", "last_added_family_set"]
    for split in ALL_SPLITS:
        base = order_step if split == "all" else order_step.loc[order_step["split"].eq(split)]
        if base.empty:
            continue
        for keys, group in base.groupby(group_cols, dropna=False, sort=True):
            payload = {"split": split, **dict(zip(group_cols, keys))}
            seed = _seed_metrics(group, "seed_complete_h120_close_anchor_flag", "seed_anchor_big_winner", "seed_path_label")
            fresh = _fresh_metrics(
                group,
                "fresh_complete_h120_close_anchor_flag",
                "fresh_big_winner_forward_h120_close_anchor",
                "fresh_path_label",
            )
            den = int(len(group))
            payload.update(
                {
                    "fresh_step_count": den,
                    "seed_episode_count": int(group["seed_episode_id"].nunique()),
                    "unique_instrument_count": int(group["instrument_id"].nunique()),
                    "unique_signal_date_count": int(group["step_signal_date"].nunique()),
                    "seed_anchor_big_winner_rate": seed["seed_anchor_big_winner_rate"],
                    "seed_P_good": seed["seed_P_good"],
                    "seed_P_bad": seed["seed_P_bad"],
                    "fresh_anchor_big_winner_rate": fresh["fresh_anchor_big_winner_rate"],
                    "fresh_P_good": fresh["fresh_P_good"],
                    "fresh_P_bad": fresh["fresh_P_bad"],
                    **_fresh_path_stats(group),
                    "sample_sufficiency_status": _sample_status(den, thresholds["min_fresh_step_count"]),
                }
            )
            rows.append(payload)
    return pd.DataFrame(rows)


SCHEMES: dict[str, dict[str, Any]] = {
    "fresh_step_base": {"grain": "fresh_step", "group": [], "parent": "none", "parent_group": []},
    "fresh_count": {"grain": "fresh_step", "group": ["kth_fresh_step_bucket"], "parent": "fresh_step_base", "parent_group": []},
    "kth_offset": {
        "grain": "fresh_step",
        "group": ["kth_fresh_step_bucket", "kth_fresh_offset_bucket"],
        "parent": "fresh_count",
        "parent_group": ["kth_fresh_step_bucket"],
    },
    "kth_offset_price_state": {
        "grain": "fresh_step",
        "group": ["kth_fresh_step_bucket", "kth_fresh_offset_bucket", "wait_return_bucket"],
        "parent": "kth_offset",
        "parent_group": ["kth_fresh_step_bucket", "kth_fresh_offset_bucket"],
    },
    "family_presence_after_step": {
        "grain": "fresh_step",
        "group": ["family_presence_signature_after_step_bucket"],
        "parent": "fresh_step_base",
        "parent_group": [],
    },
    "kth_offset_price_state_plus_family_presence": {
        "grain": "fresh_step",
        "group": [
            "kth_fresh_step_bucket",
            "kth_fresh_offset_bucket",
            "wait_return_bucket",
            "family_presence_signature_after_step_bucket",
        ],
        "parent": "kth_offset_price_state",
        "parent_group": ["kth_fresh_step_bucket", "kth_fresh_offset_bucket", "wait_return_bucket"],
    },
    "kth_offset_price_state_plus_last_added_family": {
        "grain": "fresh_step",
        "group": ["kth_fresh_step_bucket", "kth_fresh_offset_bucket", "wait_return_bucket", "last_added_family_set_bucket"],
        "parent": "kth_offset_price_state",
        "parent_group": ["kth_fresh_step_bucket", "kth_fresh_offset_bucket", "wait_return_bucket"],
    },
    "seed_family_position_base": {"grain": "seed_episode_family", "group": ["family"], "parent": "none", "parent_group": []},
    "family_position": {
        "grain": "seed_episode_family",
        "group": ["family", "first_observed_stage"],
        "parent": "seed_family_position_base",
        "parent_group": ["family"],
    },
    "completed_pair_base": {"grain": "completed_pair", "group": [], "parent": "none", "parent_group": []},
    "unordered_pair": {
        "grain": "completed_pair",
        "group": ["unordered_pair_key_bucket"],
        "parent": "completed_pair_base",
        "parent_group": [],
    },
    "pair_order": {
        "grain": "completed_pair",
        "group": ["unordered_pair_key_bucket", "pair_order_key"],
        "parent": "unordered_pair",
        "parent_group": ["unordered_pair_key_bucket"],
    },
    "pair_wait_state": {
        "grain": "completed_pair",
        "group": ["unordered_pair_key_bucket", "pair_completion_wait_return_bucket"],
        "parent": "unordered_pair",
        "parent_group": ["unordered_pair_key_bucket"],
    },
    "pair_wait_state_plus_order": {
        "grain": "completed_pair",
        "group": ["unordered_pair_key_bucket", "pair_completion_wait_return_bucket", "pair_order_key"],
        "parent": "pair_wait_state",
        "parent_group": ["unordered_pair_key_bucket", "pair_completion_wait_return_bucket"],
    },
    "transition_prefix_base": {
        "grain": "transition_candidate",
        "group": ["prefix_family_count_bucket"],
        "parent": "none",
        "parent_group": [],
    },
    "unordered_prefix_presence": {
        "grain": "transition_candidate",
        "group": ["prefix_family_count_bucket", "prefix_family_set_bucket"],
        "parent": "transition_prefix_base",
        "parent_group": ["prefix_family_count_bucket"],
    },
    "ordered_prefix": {
        "grain": "transition_candidate",
        "group": ["prefix_family_count_bucket", "prefix_family_set_bucket", "candidate_next_family", "candidate_occurs_at_next_step"],
        "parent": "unordered_prefix_presence",
        "parent_group": ["prefix_family_count_bucket", "prefix_family_set_bucket"],
    },
    "price_state_plus_unordered_prefix": {
        "grain": "transition_candidate",
        "group": ["price_state_bucket", "prefix_family_count_bucket", "prefix_family_set_bucket"],
        "parent": "unordered_prefix_presence",
        "parent_group": ["prefix_family_count_bucket", "prefix_family_set_bucket"],
    },
    "price_state_plus_ordered_prefix": {
        "grain": "transition_candidate",
        "group": [
            "price_state_bucket",
            "prefix_family_count_bucket",
            "prefix_family_set_bucket",
            "candidate_next_family",
            "candidate_occurs_at_next_step",
        ],
        "parent": "price_state_plus_unordered_prefix",
        "parent_group": ["price_state_bucket", "prefix_family_count_bucket", "prefix_family_set_bucket"],
    },
}


def _grain_source(grain: str, order_step: pd.DataFrame, stage: pd.DataFrame, pair: pd.DataFrame, transition: pd.DataFrame) -> pd.DataFrame:
    if grain == "fresh_step":
        return order_step
    if grain == "seed_episode_family":
        return stage
    if grain == "completed_pair":
        return pair
    if grain == "transition_candidate":
        return transition
    raise ValueError(grain)


def _bucket_key(row: pd.Series, cols: list[str]) -> str:
    if not cols:
        return "all"
    return "||".join(str(row.get(col)) for col in cols)


def _metric_for_group(group: pd.DataFrame, grain: str) -> dict[str, Any]:
    weight_col = "candidate_weight" if grain == "transition_candidate" else None
    if grain == "transition_candidate":
        seed = _seed_metrics(group, "seed_complete_h120_close_anchor_flag", "seed_anchor_big_winner", "seed_path_label", weight_col)
        fresh = _fresh_metrics(
            group,
            "next_step_fresh_complete_h120_close_anchor_flag",
            "next_step_fresh_anchor_big_winner",
            "next_step_fresh_path_label",
            weight_col,
        )
        row_den = float(pd.to_numeric(group["candidate_weight"], errors="coerce").fillna(0).sum())
        episode_count = int(group["seed_episode_id"].nunique())
        fresh_step_count = np.nan
    elif grain == "completed_pair":
        seed = _seed_metrics(group, "seed_complete_h120_close_anchor_flag", "seed_anchor_big_winner", "seed_path_label")
        fresh = _fresh_metrics(
            group,
            "pair_completion_fresh_complete_h120_close_anchor_flag",
            "pair_completion_fresh_anchor_big_winner",
            "pair_completion_fresh_path_label",
        )
        row_den = float(len(group))
        episode_count = int(group["seed_episode_id"].nunique())
        fresh_step_count = np.nan
    elif grain == "seed_episode_family":
        seed = _seed_metrics(group, "seed_complete_h120_close_anchor_flag", "seed_anchor_big_winner", "seed_path_label")
        fresh = _fresh_metrics(
            group,
            "fresh_complete_h120_close_anchor_flag_if_observed_as_fresh",
            "fresh_anchor_big_winner_if_observed_as_fresh",
            "fresh_path_label_if_observed_as_fresh",
        )
        row_den = float(len(group))
        episode_count = int(group["seed_episode_id"].nunique())
        fresh_step_count = np.nan
    else:
        seed = _seed_metrics(group, "seed_complete_h120_close_anchor_flag", "seed_anchor_big_winner", "seed_path_label")
        fresh = _fresh_metrics(
            group,
            "fresh_complete_h120_close_anchor_flag",
            "fresh_big_winner_forward_h120_close_anchor",
            "fresh_path_label",
        )
        row_den = float(len(group))
        episode_count = int(group["seed_episode_id"].nunique())
        fresh_step_count = int(len(group))
    return {
        "row_denominator": row_den,
        "covered_episode_count": episode_count,
        "covered_fresh_step_count": fresh_step_count,
        "seed_anchor_big_winner_rate": seed["seed_anchor_big_winner_rate"],
        "seed_anchor_big_winner_denominator": seed["seed_anchor_big_winner_denominator"],
        "seed_P_good_minus_P_bad": _num(seed["seed_P_good"]) - _num(seed["seed_P_bad"]),
        "seed_path_denominator": seed["seed_path_denominator"],
        "fresh_anchor_big_winner_rate": fresh["fresh_anchor_big_winner_rate"],
        "fresh_anchor_big_winner_denominator": fresh["fresh_anchor_big_winner_denominator"],
        "fresh_P_good_minus_P_bad": _num(fresh["fresh_P_good"]) - _num(fresh["fresh_P_bad"]),
        "fresh_path_denominator": fresh["fresh_path_denominator"],
        **_fresh_path_stats(group),
    }


def _scheme_bucket_summary(source: pd.DataFrame, scheme: str, thresholds: dict[str, Any]) -> pd.DataFrame:
    spec = SCHEMES[scheme]
    group_cols = spec["group"]
    parent_cols = spec["parent_group"]
    grain = spec["grain"]
    rows: list[dict[str, Any]] = []
    for split in ALL_SPLITS:
        base = source if split == "all" else source.loc[source["split"].eq(split)]
        if base.empty:
            continue
        grouped = [((), base)] if not group_cols else base.groupby(group_cols, dropna=False, sort=True)
        for keys, group in grouped:
            if group_cols and not isinstance(keys, tuple):
                keys = (keys,)
            payload = {"split": split, "grouping_scheme": scheme, "row_grain": grain}
            if group_cols:
                payload.update(dict(zip(group_cols, keys)))
            payload["grouping_key"] = _bucket_key(pd.Series(payload), group_cols)
            payload["parent_key"] = _bucket_key(pd.Series(payload), parent_cols)
            payload.update(_metric_for_group(group, grain))
            min_den = thresholds["min_fresh_step_count"]
            if grain == "completed_pair":
                min_den = thresholds["min_pair_episode_count"]
            elif grain in {"transition_candidate", "seed_episode_family"}:
                min_den = thresholds["min_split_denominator"]
            payload["sample_sufficiency_status"] = _sample_status(payload["row_denominator"], min_den)
            rows.append(payload)
    return pd.DataFrame(rows)


def _outcome_cols(outcome: str) -> tuple[str, str]:
    if outcome == "seed_anchor_big_winner_rate":
        return "seed_anchor_big_winner_rate", "seed_anchor_big_winner_denominator"
    if outcome == "seed_P_good_minus_P_bad":
        return "seed_P_good_minus_P_bad", "seed_path_denominator"
    if outcome == "fresh_anchor_big_winner_rate":
        return "fresh_anchor_big_winner_rate", "fresh_anchor_big_winner_denominator"
    if outcome == "fresh_P_good_minus_P_bad":
        return "fresh_P_good_minus_P_bad", "fresh_path_denominator"
    if outcome == "fresh_max_gain_120d_p50":
        return "fresh_max_gain_120d_p50", "row_denominator"
    if outcome == "fresh_max_drawdown_120d_p50":
        return "fresh_max_drawdown_120d_p50", "row_denominator"
    raise ValueError(outcome)


def _comparison_for_scheme(scheme_summary: pd.DataFrame, parent_summary: pd.DataFrame, scheme: str, thresholds: dict[str, Any]) -> list[dict[str, Any]]:
    spec = SCHEMES[scheme]
    rows: list[dict[str, Any]] = []
    outcomes = [
        "seed_anchor_big_winner_rate",
        "seed_P_good_minus_P_bad",
        "fresh_anchor_big_winner_rate",
        "fresh_P_good_minus_P_bad",
        "fresh_max_gain_120d_p50",
        "fresh_max_drawdown_120d_p50",
    ]
    for split in ALL_SPLITS:
        child = scheme_summary.loc[scheme_summary["split"].eq(split)]
        parent = parent_summary.loc[parent_summary["split"].eq(split)]
        if child.empty:
            continue
        parent_map = parent.set_index("grouping_key").to_dict(orient="index") if not parent.empty else {}
        for outcome in outcomes:
            value_col, den_col = _outcome_cols(outcome)
            lifts = []
            den_total = 0.0
            signed = 0.0
            absolute = 0.0
            comparable = 0
            for row in child.itertuples(index=False):
                parent_key = getattr(row, "parent_key")
                parent_row = parent_map.get(parent_key)
                if parent_row is None:
                    continue
                value = _num(getattr(row, value_col, np.nan))
                parent_value = _num(parent_row.get(value_col))
                den = _num(getattr(row, den_col, np.nan))
                if pd.isna(value) or pd.isna(parent_value) or pd.isna(den) or den <= 0:
                    continue
                lift = value - parent_value
                lifts.append(lift)
                den_total += den
                signed += den * lift
                absolute += den * abs(lift)
                comparable += 1
            bucket_count = int(len(child))
            sufficient_count = int(child["sample_sufficiency_status"].eq("sufficient").sum())
            rows.append(
                {
                    "split": split,
                    "grouping_scheme": scheme,
                    "row_grain": spec["grain"],
                    "outcome": outcome,
                    "bucket_count": bucket_count,
                    "sufficient_bucket_count": sufficient_count,
                    "sufficient_bucket_ratio": _safe_div(sufficient_count, bucket_count),
                    "covered_episode_count": int(child["covered_episode_count"].sum()),
                    "covered_fresh_step_count": child["covered_fresh_step_count"].sum(),
                    "parent_grouping_scheme": spec["parent"],
                    "weighted_abs_lift_vs_parent": _safe_div(absolute, den_total),
                    "weighted_signed_lift_vs_parent": _safe_div(signed, den_total),
                    "max_abs_lift_vs_parent": max([abs(x) for x in lifts]) if lifts else np.nan,
                    "median_abs_lift_vs_parent": float(np.median([abs(x) for x in lifts])) if lifts else np.nan,
                    "sample_sufficiency_status": "sufficient"
                    if sufficient_count / bucket_count >= thresholds["min_sufficient_bucket_ratio"]
                    else "thin_episode_denominator",
                    "interpretability_status": "comparable" if comparable else "non_comparable_grain",
                }
            )
    return rows


def _explanatory_power(
    order_step: pd.DataFrame,
    stage: pd.DataFrame,
    pair: pd.DataFrame,
    transition: pd.DataFrame,
    thresholds: dict[str, Any],
) -> tuple[pd.DataFrame, dict[str, pd.DataFrame]]:
    bucket_summaries: dict[str, pd.DataFrame] = {}
    rows: list[dict[str, Any]] = []
    for scheme, spec in SCHEMES.items():
        source = _grain_source(spec["grain"], order_step, stage, pair, transition)
        bucket_summaries[scheme] = _scheme_bucket_summary(source, scheme, thresholds)
    for scheme, spec in SCHEMES.items():
        if spec["parent"] == "none":
            for split in ALL_SPLITS:
                child = bucket_summaries[scheme].loc[bucket_summaries[scheme]["split"].eq(split)]
                if child.empty:
                    continue
                for outcome in [
                    "seed_anchor_big_winner_rate",
                    "seed_P_good_minus_P_bad",
                    "fresh_anchor_big_winner_rate",
                    "fresh_P_good_minus_P_bad",
                    "fresh_max_gain_120d_p50",
                    "fresh_max_drawdown_120d_p50",
                ]:
                    rows.append(
                        {
                            "split": split,
                            "grouping_scheme": scheme,
                            "row_grain": spec["grain"],
                            "outcome": outcome,
                            "bucket_count": int(len(child)),
                            "sufficient_bucket_count": int(child["sample_sufficiency_status"].eq("sufficient").sum()),
                            "sufficient_bucket_ratio": _safe_div(
                                int(child["sample_sufficiency_status"].eq("sufficient").sum()), len(child)
                            ),
                            "covered_episode_count": int(child["covered_episode_count"].sum()),
                            "covered_fresh_step_count": child["covered_fresh_step_count"].sum(),
                            "parent_grouping_scheme": "none",
                            "weighted_abs_lift_vs_parent": np.nan,
                            "weighted_signed_lift_vs_parent": np.nan,
                            "max_abs_lift_vs_parent": np.nan,
                            "median_abs_lift_vs_parent": np.nan,
                            "sample_sufficiency_status": "base",
                            "interpretability_status": "base_parent",
                        }
                    )
        else:
            rows.extend(_comparison_for_scheme(bucket_summaries[scheme], bucket_summaries[spec["parent"]], scheme, thresholds))
    return pd.DataFrame(rows), bucket_summaries


def _split_stability_audit(bucket_summaries: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for scheme, summary in bucket_summaries.items():
        if summary.empty:
            continue
        for outcome in [
            "seed_anchor_big_winner_rate",
            "seed_P_good_minus_P_bad",
            "fresh_anchor_big_winner_rate",
            "fresh_P_good_minus_P_bad",
        ]:
            value_col, den_col = _outcome_cols(outcome)
            source = summary.loc[summary["split"].isin(SPLITS)].copy()
            for key, group in source.groupby("grouping_key", dropna=False, sort=True):
                payload = {"grouping_scheme": scheme, "grouping_key": key, "outcome": outcome}
                values = []
                signs = []
                missing = False
                thin = False
                for split in SPLITS:
                    part = group.loc[group["split"].eq(split)]
                    if part.empty:
                        payload[f"{split}_denominator"] = 0
                        payload[f"{split}_value"] = np.nan
                        missing = True
                        continue
                    row = part.iloc[0]
                    den = _num(row.get(den_col))
                    val = _num(row.get(value_col))
                    payload[f"{split}_denominator"] = den
                    payload[f"{split}_value"] = val
                    values.append(val)
                    signs.append(0 if pd.isna(val) or abs(val) < 1e-12 else (1 if val > 0 else -1))
                    if den < 30:
                        thin = True
                payload["validation_lift_vs_parent"] = np.nan
                payload["robustness_lift_vs_parent"] = np.nan
                nonzero = [s for s in signs if s != 0]
                payload["lift_sign_consistent"] = bool(nonzero and len(set(nonzero)) == 1)
                vals = pd.to_numeric(pd.Series(values), errors="coerce").dropna()
                payload["lift_magnitude_stable"] = bool(len(vals) >= 2 and vals.max() - vals.min() <= 0.10)
                if missing:
                    status = "split_missing"
                elif thin:
                    status = "denominator_thin"
                elif payload["lift_sign_consistent"]:
                    status = "stable_descriptive"
                else:
                    status = "unstable"
                payload["sample_sufficiency_status"] = "sufficient" if status == "stable_descriptive" else "thin_episode_denominator"
                payload["stability_status"] = status
                rows.append(payload)
    return pd.DataFrame(rows)


def _denominator_audit(seeds: pd.DataFrame, order_step: pd.DataFrame, stage: pd.DataFrame, transition: pd.DataFrame, pair: pd.DataFrame, exhausted_prefix_count: int) -> pd.DataFrame:
    first = order_step.sort_values(["seed_episode_id", "step_offset"]).drop_duplicates("seed_episode_id")
    first_offset = first.set_index("seed_episode_id")["step_offset"].to_dict()
    rows = []
    for split in ALL_SPLITS:
        seed_part = seeds if split == "all" else seeds.loc[seeds["split"].eq(split)]
        step_part = order_step if split == "all" else order_step.loc[order_step["split"].eq(split)]
        stage_part = stage if split == "all" else stage.loc[stage["split"].eq(split)]
        transition_part = transition if split == "all" else transition.loc[transition["split"].eq(split)]
        pair_part = pair if split == "all" else pair.loc[pair["split"].eq(split)]
        failure = pd.to_numeric(seed_part["observable_failure_offset"], errors="coerce")
        mapped_first = seed_part["seed_episode_id"].map(first_offset)
        rows.append(
            {
                "split": split,
                "seed_episode_count": int(len(seed_part)),
                "no_clean_fresh_episode_count": int(mapped_first.isna().sum()),
                "failed_before_first_clean_fresh_count": int((failure.notna() & (mapped_first.isna() | (failure < mapped_first))).sum()),
                "first_clean_fresh_episode_count": int(mapped_first.notna().sum()),
                "stage_role_not_observed_row_count": int(stage_part["first_observed_stage"].eq("not_observed").sum())
                if not stage_part.empty
                else 0,
                "transition_candidate_row_count": int(len(transition_part)),
                "actual_transition_row_count": int(transition_part["candidate_occurs_at_next_step"].sum()) if not transition_part.empty else 0,
                "same_offset_multi_family_step_count": int(step_part["is_same_offset_multi_family_step"].sum()) if not step_part.empty else 0,
                "same_offset_multi_family_step_rate": _safe_div(
                    int(step_part["is_same_offset_multi_family_step"].sum()) if not step_part.empty else 0,
                    len(step_part),
                ),
                "ordered_pair_observable_count": int(pair_part["pair_order_observable"].sum()) if not pair_part.empty else 0,
                "same_offset_pair_count": int(pair_part["same_offset_pair_flag"].sum()) if not pair_part.empty else 0,
                "terminal_after_prefix_count": int(transition_part["terminal_after_prefix"].sum()) if not transition_part.empty else 0,
                "exhausted_prefix_count": exhausted_prefix_count if split == "all" else np.nan,
            }
        )
    return pd.DataFrame(rows)


def _decision_component(comparison: pd.DataFrame, raw_scheme: str, controlled_scheme: str, thresholds: dict[str, Any]) -> str:
    val = comparison.loc[
        comparison["split"].isin(["validation", "robustness"])
        & comparison["outcome"].isin(["fresh_anchor_big_winner_rate", "fresh_P_good_minus_P_bad"])
    ].copy()
    if val.empty:
        return "insufficient_denominator"
    raw = val.loc[val["grouping_scheme"].eq(raw_scheme)]
    controlled = val.loc[val["grouping_scheme"].eq(controlled_scheme)]
    if raw.empty or controlled.empty:
        return "insufficient_denominator"
    min_ratio = float(thresholds["min_sufficient_bucket_ratio"])
    if raw["sufficient_bucket_ratio"].min() < min_ratio or controlled["sufficient_bucket_ratio"].min() < min_ratio:
        return "insufficient_denominator"
    raw_lift = raw.groupby("split")["weighted_signed_lift_vs_parent"].max()
    ctl_lift = controlled.groupby("split")["weighted_signed_lift_vs_parent"].max()
    material = min(float(thresholds["min_material_rate_lift_pp"]), float(thresholds["min_material_pgood_minus_pbad_lift_pp"]))
    if (raw_lift >= material).all() and (ctl_lift >= material).all():
        return "supported"
    if (raw_lift >= material).any() and not (ctl_lift >= material).any():
        return "price_state_proxy"
    return "no_increment"


def _final_decision(comparison: pd.DataFrame, family_position: pd.DataFrame, thresholds: dict[str, Any]) -> tuple[str, dict[str, str]]:
    components = {
        "prefix_order_incremental": _decision_component(comparison, "ordered_prefix", "price_state_plus_ordered_prefix", thresholds),
        "pair_order_incremental": _decision_component(comparison, "pair_order", "pair_wait_state_plus_order", thresholds),
        "last_added_family_incremental": _decision_component(
            comparison,
            "kth_offset_price_state_plus_last_added_family",
            "kth_offset_price_state_plus_last_added_family",
            thresholds,
        ),
    }
    if all(v == "insufficient_denominator" for v in components.values()):
        return "insufficient_denominator", components
    if components["prefix_order_incremental"] == "supported" or components["pair_order_incremental"] == "supported":
        return "supported_order_incremental_edge", components
    non_insufficient = [v for v in components.values() if v != "insufficient_denominator"]
    if non_insufficient and all(v == "price_state_proxy" for v in non_insufficient):
        return "price_state_proxy_only", components
    stable_stage = False
    if not family_position.empty:
        stable_stage = bool(
            family_position.loc[
                family_position["split"].isin(["validation", "robustness"])
                & family_position["sample_sufficiency_status"].eq("sufficient")
            ].shape[0]
            > 0
        )
    return ("stage_role_only_no_order_increment" if stable_stage else "insufficient_denominator"), components


def _fmt_pct(value: Any) -> str:
    num = _num(value)
    return "NA" if pd.isna(num) else f"{num:.1%}"


def _fmt_num(value: Any) -> str:
    num = _num(value)
    return "NA" if pd.isna(num) else f"{num:.4f}"


def _report_table(df: pd.DataFrame, cols: list[str], max_rows: int = 10) -> str:
    if df.empty:
        return "_无数据_"
    view = df.loc[:, [c for c in cols if c in df.columns]].head(max_rows).copy()
    return view.to_markdown(index=False)


def _final_report(
    family_position: pd.DataFrame,
    stage_role: pd.DataFrame,
    transition_summary: pd.DataFrame,
    pair_summary: pd.DataFrame,
    last_added: pd.DataFrame,
    comparison: pd.DataFrame,
    denom: pd.DataFrame,
    final_decision: str,
    components: dict[str, str],
) -> str:
    all_denom = denom.loc[denom["split"].eq("all")].iloc[0] if not denom.loc[denom["split"].eq("all")].empty else pd.Series(dtype=object)
    comp_view = comparison.loc[
        comparison["split"].isin(["validation", "robustness"])
        & comparison["grouping_scheme"].isin(
            [
                "ordered_prefix",
                "price_state_plus_ordered_prefix",
                "pair_order",
                "pair_wait_state_plus_order",
                "kth_offset_price_state_plus_last_added_family",
            ]
        )
        & comparison["outcome"].isin(["fresh_anchor_big_winner_rate", "fresh_P_good_minus_P_bad"])
    ].copy()
    lines = [
        "# R03d Family 出现顺序与 Stage Role 诊断最终报告",
        "",
        "## 1. 结论",
        "",
        f"- final_decision: `{final_decision}`",
        f"- prefix_order_incremental: `{components.get('prefix_order_incremental')}`",
        f"- pair_order_incremental: `{components.get('pair_order_incremental')}`",
        f"- last_added_family_incremental: `{components.get('last_added_family_incremental')}`",
        "",
        "本实验只评估 family 出现顺序与 stage role 的描述性和增量解释力，不输出 entry / add / position sizing 规则。",
        "",
        "## 2. Denominator 与 Survival 口径",
        "",
        f"- seed episodes: `{int(all_denom.get('seed_episode_count', 0)):,}`",
        f"- first clean fresh episodes: `{int(all_denom.get('first_clean_fresh_episode_count', 0)):,}`",
        f"- no clean fresh episodes: `{int(all_denom.get('no_clean_fresh_episode_count', 0)):,}`",
        f"- failed before first clean fresh: `{int(all_denom.get('failed_before_first_clean_fresh_count', 0)):,}`",
        f"- transition candidate rows: `{int(all_denom.get('transition_candidate_row_count', 0)):,}`",
        f"- exhausted prefixes: `{int(all_denom.get('exhausted_prefix_count', 0)):,}`",
        "",
        "survival conditioning 可以是 probe lifecycle 的一部分；但 order/family edge 必须在 survived 条件下提供 fresh-anchor 或 remaining-path 增量，才可被视作升级信息。",
        "",
        "## 3. Family Stage Role",
        "",
        _report_table(
            stage_role.loc[stage_role["split"].eq("all")].sort_values(["family", "stage_role_candidate"]),
            [
                "family",
                "stage_role_candidate",
                "episode_count",
                "median_wait_return",
                "up_10pct_plus_price_state_share",
                "seed_P_good",
                "seed_P_bad",
                "fresh_P_good",
                "fresh_P_bad",
                "sample_sufficiency_status",
            ],
            20,
        ),
        "",
        "## 4. Order Explanatory Power",
        "",
        _report_table(
            comp_view.sort_values(["split", "grouping_scheme", "outcome"]),
            [
                "split",
                "grouping_scheme",
                "outcome",
                "bucket_count",
                "sufficient_bucket_count",
                "sufficient_bucket_ratio",
                "weighted_abs_lift_vs_parent",
                "weighted_signed_lift_vs_parent",
                "interpretability_status",
            ],
            40,
        ),
        "",
        "## 5. Prefix / Pair / Last-Added 摘要",
        "",
        "### Prefix",
        "",
        _report_table(
            transition_summary.loc[transition_summary["split"].eq("all")].sort_values(
                ["candidate_occurrence_rate"], ascending=False
            ),
            [
                "prefix_family_count_bucket",
                "prefix_family_set_bucket",
                "candidate_next_family",
                "candidate_occurs_at_next_step",
                "candidate_weight_sum",
                "candidate_occurrence_rate",
                "next_step_fresh_anchor_big_winner_rate_weighted",
                "next_step_fresh_P_good_weighted",
                "next_step_fresh_P_bad_weighted",
                "sample_sufficiency_status",
            ],
            20,
        ),
        "",
        "### Pair Order",
        "",
        _report_table(
            pair_summary.loc[pair_summary["split"].eq("all")].sort_values(["episode_count"], ascending=False),
            [
                "unordered_pair_key",
                "pair_order_key",
                "episode_count",
                "pair_completion_fresh_anchor_big_winner_rate",
                "pair_completion_fresh_P_good",
                "pair_completion_fresh_P_bad",
                "asymmetry_status",
            ],
            20,
        ),
        "",
        "### Last Added Family",
        "",
        _report_table(
            last_added.loc[last_added["split"].eq("all")].sort_values(["fresh_step_count"], ascending=False),
            [
                "kth_fresh_step_bucket",
                "kth_fresh_offset_bucket",
                "wait_return_bucket",
                "last_added_family_set",
                "fresh_step_count",
                "fresh_anchor_big_winner_rate",
                "fresh_P_good",
                "fresh_P_bad",
            ],
            20,
        ),
        "",
        "## 6. 解释边界",
        "",
        "- seed-anchor improvement = episode selection / survival / state evidence。",
        "- fresh-anchor improvement = possible remaining-path information。",
        "- ordered <= unordered 表示没有顺序信息。",
        "- ordered <= kth_offset_price_state / pair_wait_state / price_state_plus_unordered_prefix 表示 price-state proxy。",
        "- 除非 `supported_order_incremental_edge` 成立，否则不得把 family order 写成可交易 alpha。",
    ]
    return "\n".join(lines) + "\n"


def _write_validation_audit(
    reports_dir: Path,
    validation_path: Path,
    final_decision: str,
    rows: list[dict[str, Any]],
) -> dict[str, Any]:
    audit = pd.DataFrame(rows)
    audit_path = reports_dir / "r03d_family_order_stage_role_validation_audit.csv"
    _write_csv(audit, audit_path)
    failed = audit.loc[audit["status"].eq("failed") & audit["severity"].isin(["fatal", "error"])]
    validation = {
        "validation_status": "failed" if len(failed) else "passed",
        "final_decision": final_decision,
        "failed_checks": failed["check_id"].tolist(),
        "audit_path": relpath(audit_path),
    }
    write_json(validation, validation_path)
    return validation


def _blocked_manifest(config: dict[str, Any], decision: str, reports_dir: Path, manifests_dir: Path, readiness: pd.DataFrame) -> dict[str, Any]:
    reports_dir.mkdir(parents=True, exist_ok=True)
    manifests_dir.mkdir(parents=True, exist_ok=True)
    _write_csv(readiness, reports_dir / "r03d_input_readiness_audit.csv")
    manifest = {
        "phase": config["phase"],
        "requirement_id": config["requirement_id"],
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "output_root": config["output_root"],
        "final_decision": decision,
        "decision_components": {},
        "artifact_hashes": {},
    }
    write_json(manifest, manifests_dir / "r03d_family_order_stage_role_manifest.json")
    return manifest


def run(config_path: Path) -> dict[str, Any]:
    config = _read_yaml(config_path)
    output_root = topic_path(Path(config["output_root"]))
    cache_dir = output_root / "cache"
    reports_dir = output_root / "reports"
    manifests_dir = output_root / "manifests"
    cache_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)
    manifests_dir.mkdir(parents=True, exist_ok=True)

    readiness, ready, decision = _readiness(config)
    _write_csv(readiness, reports_dir / "r03d_input_readiness_audit.csv")
    validation_path = manifests_dir / "r03d_family_order_stage_role_validation.json"
    if not ready:
        manifest = _blocked_manifest(config, decision, reports_dir, manifests_dir, readiness)
        _write_validation_audit(reports_dir, validation_path, decision, [])
        return manifest

    thresholds = config["sample_sufficiency"]
    family_universe = list(config["family_universe"])
    seeds, step, fresh = _load_inputs(config)
    _validate_family_tokens([seeds, step, fresh], ["seed_family_set", "same_day_family_set", "added_family_set"], family_universe)
    print(f"r03d: loaded seeds={len(seeds):,} fresh_steps={len(fresh):,}", file=sys.stderr, flush=True)

    order_step = _build_order_step_panel(fresh, family_universe)
    stage = _build_stage_role_panel(seeds, order_step, family_universe)
    transition, exhausted_prefix_count = _build_transition_candidate_panel(seeds, order_step, family_universe)
    transition = _freeze_prefix_buckets(transition, thresholds["min_exact_prefix_denominator"])
    pair = _build_pair_order_panel(seeds, stage, order_step, family_universe)
    print(
        f"r03d: panels step={len(order_step):,} stage={len(stage):,} transition={len(transition):,} pair={len(pair):,}",
        file=sys.stderr,
        flush=True,
    )

    family_position = _family_position_summary(stage, thresholds)
    stage_role = _stage_role_summary(stage, thresholds)
    transition_summary = _transition_summary(transition, thresholds)
    pair_summary = _pair_summary(pair, thresholds)
    last_added = _last_added_summary(order_step, thresholds)
    comparison, bucket_summaries = _explanatory_power(order_step, stage, pair, transition, thresholds)
    stability = _split_stability_audit(bucket_summaries)
    denom = _denominator_audit(seeds, order_step, stage, transition, pair, exhausted_prefix_count)
    final_decision, components = _final_decision(comparison, family_position, thresholds)

    _write_parquet(order_step, cache_dir / "r03d_family_order_step_panel.parquet")
    _write_parquet(transition, cache_dir / "r03d_order_transition_candidate_panel.parquet")
    _write_parquet(pair, cache_dir / "r03d_pair_order_panel.parquet")
    _write_parquet(stage, cache_dir / "r03d_stage_role_panel.parquet")
    _write_csv(family_position, reports_dir / "r03d_family_position_summary.csv")
    _write_csv(stage_role, reports_dir / "r03d_stage_role_summary.csv")
    _write_csv(transition_summary, reports_dir / "r03d_next_family_given_prefix_summary.csv")
    _write_csv(pair_summary, reports_dir / "r03d_pair_order_asymmetry_summary.csv")
    _write_csv(last_added, reports_dir / "r03d_last_added_family_price_conditioned_summary.csv")
    _write_csv(comparison, reports_dir / "r03d_order_explanatory_power_comparison.csv")
    _write_csv(stability, reports_dir / "r03d_order_split_stability_audit.csv")
    _write_csv(denom, reports_dir / "r03d_denominator_and_survival_audit.csv")
    report = _final_report(
        family_position,
        stage_role,
        transition_summary,
        pair_summary,
        last_added,
        comparison,
        denom,
        final_decision,
        components,
    )
    (reports_dir / "r03d_family_order_stage_role_final_report.md").write_text(report, encoding="utf-8")

    artifacts = [
        cache_dir / "r03d_family_order_step_panel.parquet",
        cache_dir / "r03d_order_transition_candidate_panel.parquet",
        cache_dir / "r03d_pair_order_panel.parquet",
        cache_dir / "r03d_stage_role_panel.parquet",
        reports_dir / "r03d_input_readiness_audit.csv",
        reports_dir / "r03d_family_position_summary.csv",
        reports_dir / "r03d_stage_role_summary.csv",
        reports_dir / "r03d_next_family_given_prefix_summary.csv",
        reports_dir / "r03d_pair_order_asymmetry_summary.csv",
        reports_dir / "r03d_last_added_family_price_conditioned_summary.csv",
        reports_dir / "r03d_order_explanatory_power_comparison.csv",
        reports_dir / "r03d_order_split_stability_audit.csv",
        reports_dir / "r03d_denominator_and_survival_audit.csv",
        reports_dir / "r03d_family_order_stage_role_final_report.md",
    ]
    manifest = {
        "phase": config["phase"],
        "requirement_id": config["requirement_id"],
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "output_root": config["output_root"],
        "upstream": {
            "r03b_manifest": config["upstream_r03b"]["manifest"],
            "r03b_validation": config["upstream_r03b"]["validation"],
            "r03c_manifest": config["upstream_r03c"]["manifest"],
            "r03c_validation": config["upstream_r03c"]["validation"],
        },
        "row_counts": {
            "seed_episode_count": int(len(seeds)),
            "fresh_step_count": int(len(order_step)),
            "stage_role_rows": int(len(stage)),
            "transition_candidate_rows": int(len(transition)),
            "pair_order_rows": int(len(pair)),
        },
        "final_decision": final_decision,
        "decision_components": components,
        "artifact_hashes": {relpath(path): _hash_file(path) for path in artifacts if path.exists()},
    }
    manifest_path = manifests_dir / "r03d_family_order_stage_role_manifest.json"
    write_json(manifest, manifest_path)

    validation_rows = [
        {
            "check_id": "runner_completed",
            "check_category": "runner",
            "status": "passed",
            "severity": "info",
            "failure_reason": "",
            "affected_rows": 0,
            "artifact_path": relpath(manifest_path),
        }
    ]
    _write_validation_audit(reports_dir, validation_path, final_decision, validation_rows)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Run EP4 R03d family order stage-role diagnostic")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    manifest = run(args.config)
    print(json.dumps({"final_decision": manifest.get("final_decision"), "output_root": manifest.get("output_root")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
