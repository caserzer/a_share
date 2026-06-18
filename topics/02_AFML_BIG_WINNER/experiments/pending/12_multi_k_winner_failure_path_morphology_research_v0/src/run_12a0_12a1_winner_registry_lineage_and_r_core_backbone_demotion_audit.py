#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import math
import platform
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
TOPIC_SRC_DIR = TOPIC_ROOT / "src"
SRC_DIR = Path(__file__).resolve().parent
EXP08_SRC_DIR = (
    TOPIC_ROOT
    / "experiments"
    / "pending"
    / "08_risk_on_transition_recall_exploration_v0"
    / "src"
)

for import_path in (TOPIC_SRC_DIR, SRC_DIR, EXP08_SRC_DIR):
    if str(import_path) not in sys.path:
        sys.path.insert(0, str(import_path))

from afml_big_winner.config import load_yaml, stable_hash  # noqa: E402
from afml_big_winner.manifest import file_sha256, git_revision  # noqa: E402

import run_density_fast_fail_audit as density_audit  # noqa: E402


RUN_ID = "12A0_12A1_winner_registry_lineage_and_r_core_backbone_demotion_audit"
EXPERIMENT_ID = "12_state_change_event_backbone_rebuild_v0"
LEGACY_DIRECTORY_ID = "12_multi_k_winner_failure_path_morphology_research_v0"

CONFIG_PATH = (
    EXPERIMENT_DIR
    / "configs"
    / "config_12a0_12a1_winner_registry_lineage_and_r_core_backbone_demotion_audit.yaml"
)
REQUIREMENT_PATH = (
    EXPERIMENT_DIR
    / "requirement_12a0_12a1_winner_registry_lineage_and_r_core_backbone_demotion_audit.md"
)
TABLE_DIR = EXPERIMENT_DIR / "outputs" / "publishable" / "tables" / RUN_ID
REPORT_DIR = EXPERIMENT_DIR / "outputs" / "publishable" / "reports"
MANIFEST_DIR = EXPERIMENT_DIR / "outputs" / "manifests"

SPLITS = ("all", "train", "validation", "robustness")
WINDOWS = ("pre120_calendar_to_high", "low_to_high", "low_to_first_50pct")

RAW_R_CORE_ARM = "08_R_core_event_regime_gated_raw"
R6_ARM = "08_R6_event_regime_gated_raw"
TEN_A_ARM = "10A_same_instrument_cooldown_10d_r_core"
TEN_B_RETAINED_ARM = "10B_keep_9400_retained_after_fast_fail_gate"
TEN_B_REJECTED_ARM = "10B_keep_9400_rejected_fast_fail_bucket"

R_CORE_SCOPE = "08_R_core_event_regime_gated"
R6_SCOPE = "08_R6_event_regime_gated"
R_CORE_09_DENOM = "risk_on_r_core_horizon_complete"
R_CORE_10A_DENOM = "post_dedup_risk_on_r_core"
TEN_A_POPULATION_ID = "10A__same_instrument_cooldown_10d"
TEN_A_RULE_ARM_ID = "same_instrument_cooldown_10d"

E1_SCOPE = "07_E1_only"
E1_FAMILY = "E1_early_ema60_repair"
R_CORE_ACCEPTED_DIFF_REASON = "08_A_H_accepted_r_core_minus_15"


@dataclass(frozen=True)
class InputSpec:
    artifact_id: str
    path: Path
    required_for_final_decision: bool
    required_for_comparison: bool = False
    expected_columns: tuple[str, ...] = ()


@dataclass(frozen=True)
class ArmSpec:
    arm_id: str
    decision_role: str
    source_kind: str


ARM_SPECS = (
    ArmSpec(RAW_R_CORE_ARM, "raw_backbone_decision_required", "08_scope"),
    ArmSpec(R6_ARM, "comparison_non_blocking", "08_scope"),
    ArmSpec(TEN_A_ARM, "compression_comparison_non_blocking", "10a"),
    ArmSpec(TEN_B_RETAINED_ARM, "optional_compression_comparison", "10b"),
    ArmSpec(TEN_B_REJECTED_ARM, "optional_compression_comparison", "10b"),
    ArmSpec("08C_baseline_r_core_no_ranker_diagnostic", "optional_historical_comparison", "missing"),
    ArmSpec("08C_top_k_per_instrument_month_family_aware", "optional_historical_comparison", "missing"),
    ArmSpec("08C_cooldown_20d_ranked_within_bucket", "optional_historical_comparison", "missing"),
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run 12A0/12A1 R-core demotion audit.")
    parser.add_argument("--config", default=str(CONFIG_PATH))
    parser.add_argument("--mode", choices=["check-inputs", "full"], default="full")
    return parser.parse_args(argv)


def topic_path(value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    text = str(path)
    if text.startswith("topics/"):
        return REPO_ROOT / path
    if text.startswith("outputs/"):
        return EXPERIMENT_DIR / path
    return EXPERIMENT_DIR / path


def write_df(path: Path, frame: pd.DataFrame) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix == ".parquet":
        frame.to_parquet(path, index=False)
    else:
        frame.to_csv(path, index=False)
    return path


def write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    return path


def write_text(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")
    return path


def read_csv(path: Path, **kwargs: Any) -> pd.DataFrame:
    return pd.read_csv(path, low_memory=False, **kwargs)


def read_table(path: Path, **kwargs: Any) -> pd.DataFrame:
    suffixes = "".join(path.suffixes)
    if suffixes.endswith(".parquet"):
        return pd.read_parquet(path, **kwargs)
    return read_csv(path, **kwargs)


def path_sha(path: Path) -> str:
    return file_sha256(path) if path.exists() and path.is_file() else ""


def safe_rate(numerator: int | float, denominator: int | float) -> float:
    if denominator is None or pd.isna(denominator) or float(denominator) == 0:
        return np.nan
    return float(numerator) / float(denominator)


def boolish(value: Any) -> bool:
    if pd.isna(value):
        return False
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    if isinstance(value, (int, float, np.integer, np.floating)):
        return bool(value)
    return str(value).strip().lower() in {"1", "true", "yes", "y", "t"}


def bool_series(values: pd.Series) -> pd.Series:
    return values.map(boolish).astype(bool)


def nonempty_str(value: Any) -> str:
    if value is None or pd.isna(value):
        return ""
    text = str(value)
    return "" if text.lower() == "nan" else text


def date_series(values: pd.Series) -> pd.Series:
    return pd.to_datetime(values, errors="coerce")


def day_diff(left: Any, right: Any) -> float:
    left_dt = pd.to_datetime(left, errors="coerce")
    right_dt = pd.to_datetime(right, errors="coerce")
    if pd.isna(left_dt) or pd.isna(right_dt):
        return np.nan
    return float((left_dt - right_dt).days)


def fmt_date(value: Any) -> str:
    dt = pd.to_datetime(value, errors="coerce")
    if pd.isna(dt):
        return ""
    return dt.strftime("%Y-%m-%d")


def parse_canonical_from_input_event_key(value: Any) -> tuple[str, str]:
    text = nonempty_str(value)
    parts = text.split("|")
    if len(parts) >= 4 and parts[3]:
        return parts[3], "input_event_key_component_4"
    return "", "unresolved"


def window_category(event_date: Any, low_date: Any, high_date: Any, pre120_date: Any | None = None) -> str:
    event_dt = pd.to_datetime(event_date, errors="coerce")
    low_dt = pd.to_datetime(low_date, errors="coerce")
    high_dt = pd.to_datetime(high_date, errors="coerce")
    if pd.isna(event_dt) or pd.isna(low_dt) or pd.isna(high_dt):
        return "no_same_instrument_episode"
    pre120_dt = pd.to_datetime(pre120_date, errors="coerce") if pre120_date is not None else low_dt - pd.Timedelta(days=120)
    if pd.isna(pre120_dt):
        pre120_dt = low_dt - pd.Timedelta(days=120)
    if event_dt < pre120_dt:
        return "before_pre120_calendar_start"
    if event_dt < low_dt:
        return "pre120_before_episode_low"
    if event_dt <= high_dt:
        return "inside_low_to_high"
    return "after_episode_high"


def input_specs(config: dict[str, Any]) -> list[InputSpec]:
    paths = {k: topic_path(v) for k, v in config["paths"].items()}
    specs = [
        InputSpec("requirement", REQUIREMENT_PATH, True),
        InputSpec("config", Path(config.get("_config_path", CONFIG_PATH)), True),
        InputSpec("episode_06_csv", paths["episode_06_csv"], True, expected_columns=("episode_id", "instrument", "episode_low_date", "episode_high_date", "market_regime_bucket", "split")),
        InputSpec("mfe_11a2_csv", paths["mfe_11a2_csv"], True, expected_columns=("row_id", "instrument", "event_t0_date", "mfe_120d_frozen", "basis_status")),
        InputSpec("outcome_11a2_audit", paths["outcome_11a2_audit"], True),
        InputSpec("canonical_08_events", paths["canonical_08_events"], True, expected_columns=("canonical_event_id", "instrument", "event_t0_date", "triggered_family_variants")),
        InputSpec("scope_mapping_08", paths["scope_mapping_08"], True),
        InputSpec("scope_reconstruct_08", paths["scope_reconstruct_08"], True),
        InputSpec("density_08", paths["density_08"], True),
        InputSpec("badside_e1_08", paths["badside_e1_08"], True),
        InputSpec("labels_08", paths["labels_08"], True),
        InputSpec("source_pool_09", paths["source_pool_09"], True),
        InputSpec("label_bindings_09a", paths["label_bindings_09a"], True),
        InputSpec("bindings_10a", paths["bindings_10a"], False, True),
        InputSpec("population_10a", paths["population_10a"], False, True),
        InputSpec("density_10a", paths["density_10a"], False, True),
        InputSpec("scores_10b", paths["scores_10b"], False, True),
        InputSpec("frontier_10b", paths["frontier_10b"], False, True),
    ]
    for key, value in config.get("baseline_diagnostics", {}).items():
        specs.append(InputSpec(f"diagnostic_{key}", topic_path(value), False, True))
    return specs


def table_columns(path: Path) -> tuple[list[str], str, int | float]:
    if not path.exists():
        return [], "missing", np.nan
    try:
        if "".join(path.suffixes).endswith(".parquet"):
            frame = pd.read_parquet(path)
        else:
            frame = read_csv(path)
        return frame.columns.tolist(), "readable_tabular", int(len(frame))
    except Exception:
        try:
            path.read_text(encoding="utf-8")
            return [], "readable_text", np.nan
        except Exception:
            return [], "read_error", np.nan


def build_input_artifact_audit(config: dict[str, Any]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for spec in input_specs(config):
        columns, read_status, row_count = table_columns(spec.path)
        missing_cols = [col for col in spec.expected_columns if col not in columns]
        if missing_cols and read_status == "readable_tabular":
            read_status = "schema_mismatch"
        rows.append(
            {
                "artifact_id": spec.artifact_id,
                "artifact_role": "required" if spec.required_for_final_decision else "comparison_or_diagnostic",
                "required_for_final_decision_flag": spec.required_for_final_decision,
                "required_for_comparison_flag": spec.required_for_comparison,
                "relative_path": str(spec.path.relative_to(REPO_ROOT)) if str(spec.path).startswith(str(REPO_ROOT)) else str(spec.path),
                "resolved_absolute_path": str(spec.path),
                "exists_flag": spec.path.exists(),
                "read_status": read_status,
                "row_count": row_count,
                "column_count": len(columns) if columns else np.nan,
                "sha256": path_sha(spec.path),
                "source_manifest_path": "",
                "source_manifest_hash": "",
                "expected_columns": ";".join(spec.expected_columns),
                "actual_columns_hash": stable_hash(columns) if columns else "",
                "diagnostic_hash_reference_status": "not_applicable",
                "diagnostic_reconciliation_status": "not_checked",
                "block_reason": "missing_required_artifact" if spec.required_for_final_decision and not spec.path.exists() else ("missing_columns:" + ";".join(missing_cols) if missing_cols else ""),
            }
        )
    return pd.DataFrame(rows)


def first_present(frame: pd.DataFrame, cols: list[str], default: Any = "") -> pd.Series:
    out = pd.Series(default, index=frame.index)
    for col in cols:
        if col in frame.columns:
            out = out.where(out.astype(str).ne(str(default)), frame[col])
    return out


def build_episode_registry(episodes_all: pd.DataFrame, source_path: Path) -> pd.DataFrame:
    risk_on = episodes_all.loc[episodes_all["market_regime_bucket"].astype(str).eq("risk_on")].copy()
    low = date_series(risk_on["episode_low_date"])
    high = date_series(risk_on["episode_high_date"])
    first50 = risk_on.get("earliest_qualifying_high_date", risk_on["episode_high_date"]).where(
        risk_on.get("earliest_qualifying_high_date", risk_on["episode_high_date"]).notna(),
        risk_on["episode_high_date"],
    )
    out = pd.DataFrame(
        {
            "record_source": "06_topn_big_winner_episode_reference",
            "record_unit": "deduped_big_winner_episode",
            "selection_rule": "market_regime_bucket == risk_on",
            "source_relative_path": str(source_path.relative_to(REPO_ROOT)),
            "episode_id": risk_on["episode_id"],
            "instrument": risk_on["instrument"],
            "episode_low_date": low.dt.strftime("%Y-%m-%d"),
            "episode_high_date": high.dt.strftime("%Y-%m-%d"),
            "first_50pct_date": date_series(first50).dt.strftime("%Y-%m-%d"),
            "pre120_calendar_start_date": (low - pd.Timedelta(days=120)).dt.strftime("%Y-%m-%d"),
            "low_to_high_sessions": pd.to_numeric(risk_on.get("low_to_high_sessions"), errors="coerce"),
            "low_to_high_calendar_days": pd.to_numeric(risk_on.get("low_to_high_calendar_days"), errors="coerce"),
            "mfe_120": pd.to_numeric(risk_on.get("mfe_120"), errors="coerce"),
            "split": risk_on.get("split", ""),
            "duration_bucket": risk_on.get("duration_bucket", ""),
            "board_bucket": risk_on.get("board_bucket", ""),
            "liquidity_money_20d": pd.to_numeric(risk_on.get("liquidity_money_20d"), errors="coerce"),
            "total_market_cap_cny": pd.to_numeric(risk_on.get("total_market_cap_cny"), errors="coerce"),
            "cluster_union_start_date": risk_on.get("cluster_union_start_date", ""),
            "cluster_union_end_date": risk_on.get("cluster_union_end_date", ""),
            "lineage_status": "frozen_06_risk_on_episode",
        }
    )
    return out.sort_values(["instrument", "episode_low_date", "episode_id"]).reset_index(drop=True)


def build_pit_candidate_winner_registry(mfe: pd.DataFrame, source_path: Path) -> pd.DataFrame:
    working = mfe.copy()
    working["mfe_120d_frozen_numeric"] = pd.to_numeric(working["mfe_120d_frozen"], errors="coerce")
    working["mfe_120_recomputed_numeric"] = pd.to_numeric(working["mfe_120_recomputed"], errors="coerce")
    winners = working.loc[working["mfe_120d_frozen_numeric"].ge(0.5)].copy()
    lineage = np.where(
        winners["basis_status"].astype(str).eq("ok"),
        "basis_ok",
        "basis_mismatch_kept_for_frozen_label_consistency",
    )
    out = pd.DataFrame(
        {
            "record_source": "11A2_post_t0_path_divergence",
            "record_unit": "risk_on_pit_valid_candidate_row",
            "selection_rule": "mfe_120d_frozen >= 0.5 within 11A1/11A2 risk_on PIT-valid denominator",
            "source_relative_path": str(source_path.relative_to(REPO_ROOT)),
            "row_id": winners["row_id"].astype(int),
            "instrument": winners["instrument"],
            "event_t0_date": date_series(winners["event_t0_date"]).dt.strftime("%Y-%m-%d"),
            "mfe_120d_frozen": pd.to_numeric(winners["mfe_120d_frozen"], errors="coerce"),
            "mfe_120_recomputed": pd.to_numeric(winners["mfe_120_recomputed"], errors="coerce"),
            "mfe_120_rel_diff": pd.to_numeric(winners["mfe_120_rel_diff"], errors="coerce"),
            "basis_status": winners["basis_status"],
            "analysis_regime_scope": "risk_on",
            "pit_scope": "11A1/11A2 strict PIT-valid executable denominator",
            "lineage_status": lineage,
        }
    )
    return out.sort_values(["instrument", "event_t0_date", "row_id"]).reset_index(drop=True)


def nearest_episode(event_row: pd.Series, episodes: pd.DataFrame) -> pd.Series | None:
    same = episodes.loc[episodes["instrument"].astype(str).eq(str(event_row["instrument"]))].copy()
    if same.empty:
        return None
    same["_diff"] = date_series(pd.Series([event_row["event_t0_date"]] * len(same), index=same.index)) - date_series(same["episode_low_date"])
    same["_diff_days"] = same["_diff"].dt.days
    same["_abs"] = same["_diff_days"].abs()
    same = same.sort_values(["_abs", "episode_low_date", "episode_id"], kind="stable")
    return same.iloc[0]


def build_population_bridge_audit(
    episodes_all: pd.DataFrame,
    episode_registry: pd.DataFrame,
    pit_registry: pd.DataFrame,
) -> pd.DataFrame:
    all_ep = episodes_all.copy()
    all_ep["pre120_calendar_start_date"] = (
        date_series(all_ep["episode_low_date"]) - pd.Timedelta(days=120)
    ).dt.strftime("%Y-%m-%d")
    rows: list[dict[str, Any]] = []
    for _, row in pit_registry.iterrows():
        nearest_any = nearest_episode(row, all_ep)
        nearest_risk = nearest_episode(row, episode_registry)
        out: dict[str, Any] = {
            "bridge_direction": "11a2_row_to_06_episode",
            "row_id": row["row_id"],
            "instrument": row["instrument"],
            "event_t0_date": row["event_t0_date"],
        }
        if nearest_any is None:
            out.update(
                {
                    "nearest_any_06_episode_id": "",
                    "nearest_any_06_episode_low_date": "",
                    "nearest_any_06_episode_high_date": "",
                    "nearest_any_market_regime_bucket": "",
                    "nearest_any_event_minus_episode_low_days": np.nan,
                    "nearest_any_abs_event_minus_episode_low_days": np.nan,
                    "nearest_any_event_vs_episode_window": "no_same_instrument_episode",
                    "inside_any_pre120_calendar_to_high_flag": False,
                }
            )
        else:
            diff = day_diff(row["event_t0_date"], nearest_any["episode_low_date"])
            out.update(
                {
                    "nearest_any_06_episode_id": nearest_any["episode_id"],
                    "nearest_any_06_episode_low_date": fmt_date(nearest_any["episode_low_date"]),
                    "nearest_any_06_episode_high_date": fmt_date(nearest_any["episode_high_date"]),
                    "nearest_any_market_regime_bucket": nearest_any.get("market_regime_bucket", ""),
                    "nearest_any_event_minus_episode_low_days": diff,
                    "nearest_any_abs_event_minus_episode_low_days": abs(diff) if pd.notna(diff) else np.nan,
                    "nearest_any_event_vs_episode_window": window_category(
                        row["event_t0_date"],
                        nearest_any["episode_low_date"],
                        nearest_any["episode_high_date"],
                        nearest_any.get("pre120_calendar_start_date"),
                    ),
                    "inside_any_pre120_calendar_to_high_flag": (
                        pd.to_datetime(nearest_any.get("pre120_calendar_start_date")) <= pd.to_datetime(row["event_t0_date"]) <= pd.to_datetime(nearest_any["episode_high_date"])
                    ),
                }
            )
        if nearest_risk is None:
            out.update(
                {
                    "nearest_risk_on_06_episode_id": "",
                    "nearest_risk_on_event_minus_episode_low_days": np.nan,
                    "nearest_risk_on_abs_event_minus_episode_low_days": np.nan,
                    "nearest_risk_on_event_vs_episode_window": "no_same_instrument_episode",
                    "inside_risk_on_pre120_calendar_to_high_flag": False,
                }
            )
        else:
            diff = day_diff(row["event_t0_date"], nearest_risk["episode_low_date"])
            out.update(
                {
                    "nearest_risk_on_06_episode_id": nearest_risk["episode_id"],
                    "nearest_risk_on_event_minus_episode_low_days": diff,
                    "nearest_risk_on_abs_event_minus_episode_low_days": abs(diff) if pd.notna(diff) else np.nan,
                    "nearest_risk_on_event_vs_episode_window": window_category(
                        row["event_t0_date"],
                        nearest_risk["episode_low_date"],
                        nearest_risk["episode_high_date"],
                        nearest_risk.get("pre120_calendar_start_date"),
                    ),
                    "inside_risk_on_pre120_calendar_to_high_flag": (
                        pd.to_datetime(nearest_risk.get("pre120_calendar_start_date")) <= pd.to_datetime(row["event_t0_date"]) <= pd.to_datetime(nearest_risk["episode_high_date"])
                    ),
                }
            )
        rows.append(out)

    pit_by_inst = {inst: frame for inst, frame in pit_registry.groupby("instrument")}
    for _, ep in episode_registry.iterrows():
        pit = pit_by_inst.get(ep["instrument"], pd.DataFrame())
        if pit.empty:
            matches = pd.DataFrame()
        else:
            dates = date_series(pit["event_t0_date"])
            matches = pit.loc[
                (dates >= pd.to_datetime(ep["pre120_calendar_start_date"]))
                & (dates <= pd.to_datetime(ep["episode_high_date"]))
            ]
        rows.append(
            {
                "bridge_direction": "06_episode_to_11a2_rows",
                "episode_id": ep["episode_id"],
                "instrument": ep["instrument"],
                "episode_low_date": ep["episode_low_date"],
                "episode_high_date": ep["episode_high_date"],
                "matching_11a2_winner_row_n_pre120_to_high": int(len(matches)),
                "matching_11a2_row_ids": ";".join(matches["row_id"].astype(str).tolist()) if not matches.empty else "",
                "matching_11a2_event_t0_dates": ";".join(matches["event_t0_date"].astype(str).tolist()) if not matches.empty else "",
                "matching_11a2_event_minus_low_days": ";".join(str(int(day_diff(v, ep["episode_low_date"]))) for v in matches["event_t0_date"]) if not matches.empty else "",
                "episode_has_any_11a2_row_pre120_to_high_flag": bool(len(matches)),
            }
        )
    return pd.DataFrame(rows)


def build_winner_registry_lineage_summary(
    episode_registry: pd.DataFrame,
    pit_registry: pd.DataFrame,
    bridge: pd.DataFrame,
) -> pd.DataFrame:
    row_bridge = bridge.loc[bridge["bridge_direction"].eq("11a2_row_to_06_episode")].copy()
    ep_bridge = bridge.loc[bridge["bridge_direction"].eq("06_episode_to_11a2_rows")].copy()
    nearest_any_diff = pd.to_numeric(row_bridge["nearest_any_event_minus_episode_low_days"], errors="coerce")
    rows = [
        ("06_risk_on_episodes", int(len(episode_registry))),
        ("11a2_pit_valid_big_winner_rows", int(len(pit_registry))),
        ("11a2_rows_with_same_instrument_any_06_episode", int(row_bridge["nearest_any_06_episode_id"].astype(str).ne("").sum())),
        ("11a2_rows_with_same_instrument_risk_on_06_episode", int(row_bridge["nearest_risk_on_06_episode_id"].astype(str).ne("").sum())),
        ("11a2_rows_exact_same_date_as_nearest_any_06_low", int(nearest_any_diff.eq(0).sum())),
        (
            "11a2_rows_exact_same_date_as_nearest_risk_on_06_low",
            int(pd.to_numeric(row_bridge["nearest_risk_on_event_minus_episode_low_days"], errors="coerce").eq(0).sum()),
        ),
        ("11a2_rows_nearest_any_before_episode_low", int(nearest_any_diff.lt(0).sum())),
        ("11a2_rows_nearest_any_inside_low_to_high_window", int(row_bridge["nearest_any_event_vs_episode_window"].eq("inside_low_to_high").sum())),
        ("11a2_rows_nearest_any_after_episode_high", int(row_bridge["nearest_any_event_vs_episode_window"].eq("after_episode_high").sum())),
        (
            "06_risk_on_episodes_with_any_11_row_pre120_to_high",
            int(pd.to_numeric(ep_bridge["matching_11a2_winner_row_n_pre120_to_high"], errors="coerce").gt(0).sum()),
        ),
        (
            "06_risk_on_episodes_without_11_row_pre120_to_high",
            int(pd.to_numeric(ep_bridge["matching_11a2_winner_row_n_pre120_to_high"], errors="coerce").eq(0).sum()),
        ),
    ]
    return pd.DataFrame(rows, columns=["metric", "value"])


def load_scope_events(canonical_08: pd.DataFrame, scope_id: str) -> pd.DataFrame:
    spec = next(s for s in density_audit.build_scope_specs() if s.candidate_scope_id == scope_id)
    raw = density_audit.select_scope_events(spec, pd.DataFrame(), canonical_08)
    out = density_audit.normalise_scope_events(raw, spec, source_path=Path("candidate_family_canonical_events.csv.gz"))
    if "event_regime_bucket" not in out.columns:
        out["event_regime_bucket"] = out.get("market_regime_bucket", "")
    if "event_window_anchor_date" not in out.columns:
        out["event_window_anchor_date"] = out.get("trade_open_date", out.get("event_t0_date", ""))
    return out


def dedupe_08_labels(labels: pd.DataFrame) -> pd.DataFrame:
    priority = {"selected_candidate_union": 0, "all_new_candidate_union": 1, "event_instance": 2}
    out = labels.copy()
    out["_priority"] = out.get("label_scope", "").map(priority).fillna(9).astype(int)
    out = out.sort_values(["event_id", "_priority"], kind="stable")
    return out.drop_duplicates(subset=["event_id"], keep="first").drop(columns=["_priority"])


def label_status_from_coverage(coverage: float, completeness: float) -> str:
    if pd.isna(coverage) or pd.isna(completeness):
        return "not_available"
    if coverage < 0.995 or completeness < 0.995:
        return "incomplete"
    return "available"


def build_08_arm_registry(events: pd.DataFrame, arm_id: str, role: str, labels_08: pd.DataFrame) -> pd.DataFrame:
    base = pd.DataFrame(
        {
            "arm_id": arm_id,
            "decision_role": role,
            "event_key": events["event_key"].astype(str),
            "canonical_event_id": events["canonical_event_id"].astype(str),
            "canonical_event_id_source": "08_canonical_event_id",
            "input_event_key": "",
            "sample_id": events["canonical_event_id"].astype(str),
            "source_event_id": events.get("event_id", ""),
            "instrument": events["instrument"].astype(str),
            "board_bucket": events.get("board_bucket", ""),
            "event_signal_date": date_series(events["event_t0_date"]).dt.strftime("%Y-%m-%d"),
            "event_signal_pos": pd.to_numeric(events.get("event_t0_pos"), errors="coerce"),
            "event_execution_date": first_present(events, ["trade_open_date", "event_window_anchor_date", "event_t0_date"]),
            "event_execution_pos": pd.to_numeric(first_present(events, ["trade_open_pos", "event_window_anchor_pos", "event_t0_pos"]), errors="coerce"),
            "event_execution_status": np.where(bool_series(events.get("non_executable_next_open", pd.Series(False, index=events.index))), "non_executable_t0_fallback", "executable_next_open"),
            "event_split": events.get("event_split", ""),
            "population_id": arm_id,
            "input_denominator_id": "",
            "denominator_id": arm_id,
            "raw_event_status": np.where(bool_series(events.get("non_executable_next_open", pd.Series(False, index=events.index))), "non_executable_audit_only", "executable"),
            "admission_status": "admitted",
            "readout_only_flag": False,
            "label_join_key": events["canonical_event_id"].astype(str),
        }
    )
    joined = base.merge(
        labels_08,
        how="left",
        left_on="canonical_event_id",
        right_on="event_id",
        suffixes=("", "_label"),
    )
    joined["label_join_status"] = np.where(joined["failure_10_label"].notna(), "matched", "missing")
    joined["label_completeness_join_status"] = joined["label_join_status"]
    joined["horizon_complete_10d"] = bool_series(joined.get("failure_10_complete", pd.Series(False, index=joined.index)))
    joined["horizon_complete_20d"] = bool_series(joined.get("event_false_repair_20d_complete", pd.Series(False, index=joined.index)))
    winner_complete = bool_series(joined.get("horizon_complete_120d", pd.Series(False, index=joined.index))) & bool_series(
        joined.get("main_barrier_label_complete", pd.Series(False, index=joined.index))
    )
    joined["horizon_complete_120d"] = winner_complete
    joined["fast_fail_10d_label"] = bool_series(joined.get("failure_10_label", pd.Series(False, index=joined.index)))
    joined["false_repair_20d_label"] = bool_series(joined.get("event_false_repair_20d_label", pd.Series(False, index=joined.index)))
    joined["winner_120_label"] = bool_series(joined.get("event_big_winner_120d_label", pd.Series(False, index=joined.index)))
    joined["source_row_count_collapsed"] = 1
    joined["event_registry_status"] = np.where(joined["label_join_status"].eq("matched"), "available", "label_missing")
    return joined[
        [
            "arm_id",
            "decision_role",
            "event_key",
            "canonical_event_id",
            "canonical_event_id_source",
            "input_event_key",
            "sample_id",
            "source_event_id",
            "instrument",
            "board_bucket",
            "event_signal_date",
            "event_signal_pos",
            "event_execution_date",
            "event_execution_pos",
            "event_execution_status",
            "event_split",
            "population_id",
            "input_denominator_id",
            "denominator_id",
            "raw_event_status",
            "admission_status",
            "readout_only_flag",
            "label_join_key",
            "label_join_status",
            "label_completeness_join_status",
            "horizon_complete_10d",
            "horizon_complete_20d",
            "horizon_complete_120d",
            "fast_fail_10d_label",
            "false_repair_20d_label",
            "winner_120_label",
            "source_row_count_collapsed",
            "event_registry_status",
        ]
    ]


def resolve_10a_canonical(frame: pd.DataFrame, canonical_ids: set[str]) -> pd.DataFrame:
    out = frame.copy()
    parsed = out["input_event_key"].map(parse_canonical_from_input_event_key)
    out["canonical_event_id"] = [item[0] for item in parsed]
    out["canonical_event_id_source"] = [item[1] for item in parsed]
    unresolved = out["canonical_event_id"].astype(str).eq("")
    sample_match = unresolved & out["sample_id"].astype(str).isin(canonical_ids)
    out.loc[sample_match, "canonical_event_id"] = out.loc[sample_match, "sample_id"].astype(str)
    out.loc[sample_match, "canonical_event_id_source"] = "sample_id_verified_against_08_canonical"
    out.loc[out["canonical_event_id"].astype(str).eq(""), "canonical_event_id_source"] = "unresolved"
    return out


def attach_09a_completeness(frame: pd.DataFrame, bindings_09: pd.DataFrame) -> pd.DataFrame:
    keep_cols = [
        "canonical_event_id",
        "denominator_id",
        "horizon_complete_10d",
        "horizon_complete_20d",
        "horizon_complete_120d",
    ]
    completeness = bindings_09[keep_cols].drop_duplicates(["canonical_event_id", "denominator_id"])
    out = frame.merge(
        completeness,
        how="left",
        left_on=["canonical_event_id", "input_denominator_id"],
        right_on=["canonical_event_id", "denominator_id"],
        suffixes=("", "_09a"),
    )
    out["horizon_complete_10d"] = bool_series(out.get("horizon_complete_10d", pd.Series(False, index=out.index)))
    out["horizon_complete_20d"] = bool_series(out.get("horizon_complete_20d", pd.Series(False, index=out.index)))
    out["horizon_complete_120d"] = bool_series(out.get("horizon_complete_120d", pd.Series(False, index=out.index)))
    out["label_completeness_join_status"] = np.where(
        out[["horizon_complete_10d", "horizon_complete_20d", "horizon_complete_120d"]].any(axis=1),
        "matched",
        "missing",
    )
    if "denominator_id_09a" in out.columns:
        out = out.drop(columns=["denominator_id_09a"])
    return out


def build_10a_arm_registry(bindings_10a: pd.DataFrame, bindings_09: pd.DataFrame, canonical_ids: set[str]) -> pd.DataFrame:
    filt = (
        bindings_10a["population_id"].astype(str).eq(TEN_A_POPULATION_ID)
        & bindings_10a["denominator_id"].astype(str).eq(R_CORE_10A_DENOM)
        & bindings_10a["admission_status"].astype(str).eq("admitted")
        & ~bool_series(bindings_10a["readout_only_flag"])
    )
    base = resolve_10a_canonical(bindings_10a.loc[filt].copy(), canonical_ids)
    base = attach_09a_completeness(base, bindings_09)
    out = pd.DataFrame(
        {
            "arm_id": TEN_A_ARM,
            "decision_role": "compression_comparison_non_blocking",
            "event_key": base["input_event_key"].astype(str),
            "canonical_event_id": base["canonical_event_id"].astype(str),
            "canonical_event_id_source": base["canonical_event_id_source"],
            "input_event_key": base["input_event_key"].astype(str),
            "sample_id": base["sample_id"].astype(str),
            "source_event_id": base.get("admitted_event_id", base["input_event_key"]).astype(str),
            "instrument": base["instrument"].astype(str),
            "board_bucket": "",
            "event_signal_date": date_series(base["event_t0_date"]).dt.strftime("%Y-%m-%d"),
            "event_signal_pos": pd.to_numeric(base["event_t0_pos"], errors="coerce"),
            "event_execution_date": date_series(base["event_window_anchor_date"]).dt.strftime("%Y-%m-%d"),
            "event_execution_pos": pd.to_numeric(base["event_window_anchor_pos"], errors="coerce"),
            "event_execution_status": base.get("event_window_anchor_status", "executable"),
            "event_split": base["split"].astype(str),
            "population_id": base["population_id"],
            "input_denominator_id": base["input_denominator_id"],
            "denominator_id": base["denominator_id"],
            "raw_event_status": base.get("raw_event_status", ""),
            "admission_status": base["admission_status"],
            "readout_only_flag": bool_series(base["readout_only_flag"]),
            "label_join_key": base["input_event_key"].astype(str),
            "label_join_status": "matched",
            "label_completeness_join_status": base["label_completeness_join_status"],
            "horizon_complete_10d": base["horizon_complete_10d"],
            "horizon_complete_20d": base["horizon_complete_20d"],
            "horizon_complete_120d": base["horizon_complete_120d"],
            "fast_fail_10d_label": bool_series(base["selected_fast_fail_10_label"]),
            "false_repair_20d_label": bool_series(base["frozen_false_repair_20d_label"]),
            "winner_120_label": bool_series(base["winner_120"]),
            "source_row_count_collapsed": 1,
            "event_registry_status": np.where(base["canonical_event_id_source"].eq("unresolved"), "canonical_unresolved", "available"),
        }
    )
    return out


def build_10b_arm_registries(
    scores_10b: pd.DataFrame,
    bindings_10a: pd.DataFrame,
    bindings_09: pd.DataFrame,
    canonical_ids: set[str],
    op: dict[str, Any],
) -> tuple[pd.DataFrame, str]:
    mask = (
        scores_10b["model_id"].astype(str).eq(str(op["model_id"]))
        & scores_10b["ablation_id"].astype(str).eq(str(op["ablation_id"]))
        & scores_10b["threshold_id"].astype(str).eq(str(op["threshold_id"]))
        & scores_10b["capacity_id"].astype(str).eq(str(op["capacity_id"]))
    )
    selected = scores_10b.loc[mask].copy()
    if selected.empty:
        return pd.DataFrame(), "not_available"
    false_repair = bindings_10a[
        ["input_event_key", "frozen_false_repair_20d_label", "event_t0_pos", "event_window_anchor_date", "event_window_anchor_pos", "event_window_anchor_status", "raw_event_status", "input_denominator_id"]
    ].drop_duplicates("input_event_key")
    selected = selected.merge(false_repair, how="left", on="input_event_key", suffixes=("", "_10a"))
    selected["canonical_event_id"] = selected.get("binding_canonical_event_id", "").fillna("")
    missing = selected["canonical_event_id"].astype(str).eq("")
    selected.loc[missing, "canonical_event_id"] = selected.loc[missing, "sample_id"].where(selected.loc[missing, "sample_id"].astype(str).isin(canonical_ids), "")
    selected["canonical_event_id_source"] = np.where(
        selected.get("binding_canonical_event_id", "").fillna("").astype(str).ne(""),
        "binding_canonical_event_id",
        np.where(selected["canonical_event_id"].astype(str).ne(""), "sample_id_verified_against_08_canonical", "unresolved"),
    )
    if "input_denominator_id" not in selected.columns:
        selected["input_denominator_id"] = R_CORE_09_DENOM
    selected = attach_09a_completeness(selected, bindings_09)
    frames: list[pd.DataFrame] = []
    for arm_id, rejected_flag in (
        (TEN_B_RETAINED_ARM, False),
        (TEN_B_REJECTED_ARM, True),
    ):
        part = selected.loc[bool_series(selected["candidate_rejected_flag"]).eq(rejected_flag)].copy()
        if part.empty:
            continue
        frames.append(
            pd.DataFrame(
                {
                    "arm_id": arm_id,
                    "decision_role": "optional_compression_comparison",
                    "event_key": part["input_event_key"].astype(str),
                    "canonical_event_id": part["canonical_event_id"].astype(str),
                    "canonical_event_id_source": part["canonical_event_id_source"],
                    "input_event_key": part["input_event_key"].astype(str),
                    "sample_id": part["sample_id"].astype(str),
                    "source_event_id": part.get("admitted_event_id", part["input_event_key"]).astype(str),
                    "instrument": part["instrument"].astype(str),
                    "board_bucket": "",
                    "event_signal_date": date_series(part["event_t0_date"]).dt.strftime("%Y-%m-%d"),
                    "event_signal_pos": pd.to_numeric(part.get("event_t0_pos", part.get("event_t0_pos_10a", np.nan)), errors="coerce"),
                    "event_execution_date": date_series(part.get("event_window_anchor_date", part["event_t0_date"])).dt.strftime("%Y-%m-%d"),
                    "event_execution_pos": pd.to_numeric(part.get("event_window_anchor_pos", np.nan), errors="coerce"),
                    "event_execution_status": part.get("event_window_anchor_status", "executable"),
                    "event_split": part["split"].astype(str),
                    "population_id": part["population_id"],
                    "input_denominator_id": part["input_denominator_id"],
                    "denominator_id": part["denominator_id"],
                    "raw_event_status": part.get("raw_event_status", ""),
                    "admission_status": "admitted",
                    "readout_only_flag": False,
                    "label_join_key": part["input_event_key"].astype(str),
                    "label_join_status": "matched",
                    "label_completeness_join_status": part["label_completeness_join_status"],
                    "horizon_complete_10d": part["horizon_complete_10d"],
                    "horizon_complete_20d": part["horizon_complete_20d"],
                    "horizon_complete_120d": part["horizon_complete_120d"],
                    "fast_fail_10d_label": bool_series(part["selected_fast_fail_10_label"]),
                    "false_repair_20d_label": bool_series(part["frozen_false_repair_20d_label"]),
                    "winner_120_label": bool_series(part["winner_120"]),
                    "source_row_count_collapsed": 1,
                    "event_registry_status": np.where(part["canonical_event_id_source"].eq("unresolved"), "canonical_unresolved", "available"),
                }
            )
        )
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(), "available"


def build_event_key_uniqueness_audit(registry: pd.DataFrame) -> pd.DataFrame:
    if registry.empty:
        return pd.DataFrame(
            columns=[
                "arm_id",
                "event_key",
                "source_row_n",
                "canonical_event_id_n",
                "input_event_key_n",
                "sample_id_n",
                "representative_event_key",
                "collapse_status",
                "duplicate_reason",
                "uniqueness_status",
            ]
        )
    grouped = registry.groupby(["arm_id", "event_key"], dropna=False)
    out = grouped.agg(
        source_row_n=("event_key", "size"),
        canonical_event_id_n=("canonical_event_id", pd.Series.nunique),
        input_event_key_n=("input_event_key", pd.Series.nunique),
        sample_id_n=("sample_id", pd.Series.nunique),
    ).reset_index()
    out["representative_event_key"] = out["event_key"]
    out["collapse_status"] = np.where(out["source_row_n"].eq(1), "unique", "duplicate_source_rows")
    out["duplicate_reason"] = np.where(out["source_row_n"].eq(1), "", "same_event_key_multiple_rows")
    out["uniqueness_status"] = np.where(out["source_row_n"].eq(1), "pass", "duplicate")
    return out


def event_match_details(events: pd.DataFrame, episodes: pd.DataFrame, window_id: str) -> tuple[set[str], dict[str, int], dict[str, int], list[float], int]:
    captured: set[str] = set()
    event_match_count: dict[str, int] = {}
    episode_event_count: dict[str, int] = {}
    first_offsets: dict[str, float] = {}
    by_episode_inst = {inst: frame for inst, frame in episodes.groupby("instrument")}
    for _, ev in events.iterrows():
        eps = by_episode_inst.get(ev["instrument"], pd.DataFrame())
        matches = 0
        event_dt = pd.to_datetime(ev["event_signal_date"], errors="coerce")
        if eps.empty or pd.isna(event_dt):
            event_match_count[str(ev["event_key"])] = 0
            continue
        for _, ep in eps.iterrows():
            if window_id == "pre120_calendar_to_high":
                start = pd.to_datetime(ep["pre120_calendar_start_date"], errors="coerce")
                end = pd.to_datetime(ep["episode_high_date"], errors="coerce")
            elif window_id == "low_to_first_50pct":
                start = pd.to_datetime(ep["episode_low_date"], errors="coerce")
                end = pd.to_datetime(ep["first_50pct_date"], errors="coerce")
            else:
                start = pd.to_datetime(ep["episode_low_date"], errors="coerce")
                end = pd.to_datetime(ep["episode_high_date"], errors="coerce")
            if pd.notna(start) and pd.notna(end) and start <= event_dt <= end:
                ep_id = str(ep["episode_id"])
                matches += 1
                captured.add(ep_id)
                episode_event_count[ep_id] = episode_event_count.get(ep_id, 0) + 1
                offset = day_diff(ev["event_signal_date"], ep["episode_low_date"])
                if ep_id not in first_offsets or offset < first_offsets[ep_id]:
                    first_offsets[ep_id] = offset
        event_match_count[str(ev["event_key"])] = matches
    multi = sum(1 for count in event_match_count.values() if count > 1)
    return captured, event_match_count, episode_event_count, list(first_offsets.values()), multi


def pair_events_episodes(events: pd.DataFrame, episodes: pd.DataFrame) -> pd.DataFrame:
    if events.empty or episodes.empty:
        return pd.DataFrame()
    event_cols = ["event_key", "instrument", "event_signal_date"]
    episode_cols = [
        "episode_id",
        "instrument",
        "episode_low_date",
        "episode_high_date",
        "first_50pct_date",
        "pre120_calendar_start_date",
    ]
    ev = events[event_cols].drop_duplicates("event_key").copy()
    ep = episodes[episode_cols].copy()
    ev["_event_dt"] = date_series(ev["event_signal_date"])
    ep["_low_dt"] = date_series(ep["episode_low_date"])
    ep["_high_dt"] = date_series(ep["episode_high_date"])
    ep["_first50_dt"] = date_series(ep["first_50pct_date"])
    ep["_pre120_dt"] = date_series(ep["pre120_calendar_start_date"])
    pairs = ev.merge(ep, how="inner", on="instrument")
    if pairs.empty:
        return pairs
    pairs["_event_minus_low_days"] = (pairs["_event_dt"] - pairs["_low_dt"]).dt.days
    return pairs


def window_bounds(pairs: pd.DataFrame, window_id: str) -> tuple[pd.Series, pd.Series]:
    if window_id == "pre120_calendar_to_high":
        return pairs["_pre120_dt"], pairs["_high_dt"]
    if window_id == "low_to_first_50pct":
        return pairs["_low_dt"], pairs["_first50_dt"]
    return pairs["_low_dt"], pairs["_high_dt"]


def event_match_details_from_pairs(
    events: pd.DataFrame,
    pairs: pd.DataFrame,
    window_id: str,
) -> tuple[set[str], dict[str, int], dict[str, int], list[float], int]:
    event_keys = events["event_key"].dropna().astype(str).unique().tolist()
    if not event_keys or pairs.empty:
        return set(), {key: 0 for key in event_keys}, {}, [], 0
    start, end = window_bounds(pairs, window_id)
    inside = pairs.loc[
        pairs["_event_dt"].notna()
        & start.notna()
        & end.notna()
        & (pairs["_event_dt"] >= start)
        & (pairs["_event_dt"] <= end)
    ].copy()
    if inside.empty:
        return set(), {key: 0 for key in event_keys}, {}, [], 0
    inside["event_key"] = inside["event_key"].astype(str)
    inside["episode_id"] = inside["episode_id"].astype(str)
    event_counts_series = inside.groupby("event_key")["episode_id"].nunique()
    event_match_count = {key: int(event_counts_series.get(key, 0)) for key in event_keys}
    episode_counts_series = inside.groupby("episode_id")["event_key"].nunique()
    first_offsets_series = inside.groupby("episode_id")["_event_minus_low_days"].min()
    multi = int((event_counts_series > 1).sum())
    return (
        set(inside["episode_id"].unique()),
        event_match_count,
        {str(key): int(value) for key, value in episode_counts_series.items()},
        first_offsets_series.dropna().astype(float).tolist(),
        multi,
    )


def nearest_timing_categories_from_pairs(events: pd.DataFrame, pairs: pd.DataFrame) -> pd.DataFrame:
    event_keys = events[["event_key"]].drop_duplicates().copy()
    if event_keys.empty:
        return pd.DataFrame(columns=["event_key", "category", "event_minus_low_days"])
    event_keys["event_key"] = event_keys["event_key"].astype(str)
    if pairs.empty:
        out = event_keys.copy()
        out["category"] = "no_same_instrument_episode"
        out["event_minus_low_days"] = np.nan
        return out
    nearest = pairs.copy()
    nearest["event_key"] = nearest["event_key"].astype(str)
    nearest["_abs"] = nearest["_event_minus_low_days"].abs()
    nearest = nearest.sort_values(["event_key", "_abs", "episode_low_date", "episode_id"], kind="stable")
    nearest = nearest.drop_duplicates("event_key", keep="first")
    category = np.select(
        [
            nearest["_event_dt"].isna() | nearest["_low_dt"].isna() | nearest["_high_dt"].isna(),
            nearest["_event_dt"] < nearest["_pre120_dt"],
            nearest["_event_dt"] < nearest["_low_dt"],
            nearest["_event_dt"] <= nearest["_high_dt"],
        ],
        [
            "no_same_instrument_episode",
            "before_pre120_calendar_start",
            "pre120_before_episode_low",
            "inside_low_to_high",
        ],
        default="after_episode_high",
    )
    nearest_out = pd.DataFrame(
        {
            "event_key": nearest["event_key"],
            "category": category,
            "event_minus_low_days": nearest["_event_minus_low_days"],
        }
    )
    out = event_keys.merge(nearest_out, how="left", on="event_key")
    out["category"] = out["category"].fillna("no_same_instrument_episode")
    return out


def nearest_timing_categories(events: pd.DataFrame, episodes: pd.DataFrame) -> pd.DataFrame:
    rows = []
    by_inst = {inst: frame for inst, frame in episodes.groupby("instrument")}
    for _, ev in events.iterrows():
        eps = by_inst.get(ev["instrument"], pd.DataFrame())
        if eps.empty:
            rows.append({"event_key": ev["event_key"], "category": "no_same_instrument_episode", "event_minus_low_days": np.nan})
            continue
        tmp = eps.copy()
        tmp["_diff"] = (pd.to_datetime(ev["event_signal_date"]) - date_series(tmp["episode_low_date"])).dt.days
        tmp["_abs"] = tmp["_diff"].abs()
        ep = tmp.sort_values(["_abs", "episode_low_date", "episode_id"], kind="stable").iloc[0]
        rows.append(
            {
                "event_key": ev["event_key"],
                "category": window_category(ev["event_signal_date"], ep["episode_low_date"], ep["episode_high_date"], ep["pre120_calendar_start_date"]),
                "event_minus_low_days": ep["_diff"],
            }
        )
    return pd.DataFrame(rows)


def split_frame(frame: pd.DataFrame, split_col: str, split: str) -> pd.DataFrame:
    if split == "all":
        return frame
    return frame.loc[frame[split_col].astype(str).eq(split)]


def build_alignment_tables(registry: pd.DataFrame, episode_registry: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    alignment_rows: list[dict[str, Any]] = []
    precision_rows: list[dict[str, Any]] = []
    episodes = episode_registry.copy()
    events = registry.loc[registry["event_registry_status"].astype(str).ne("canonical_unresolved")].copy()
    for arm_id, arm_events_all in events.groupby("arm_id"):
        for split in SPLITS:
            ep_split = split_frame(episodes, "split", split)
            ev_split = split_frame(arm_events_all, "event_split", split)
            pairs = pair_events_episodes(ev_split, ep_split)
            timing = nearest_timing_categories_from_pairs(ev_split, pairs)
            for window_id in WINDOWS:
                captured, event_matches, episode_counts, first_offsets, multi = event_match_details_from_pairs(ev_split, pairs, window_id)
                eligible_n = int(ep_split["episode_id"].nunique())
                captured_n = len(captured)
                event_n = int(ev_split["event_key"].nunique())
                inside_n = sum(1 for count in event_matches.values() if count > 0)
                counts = list(episode_counts.values())
                alignment_rows.append(
                    {
                        "arm_id": arm_id,
                        "split": split,
                        "split_basis": "episode_split",
                        "window_id": window_id,
                        "eligible_episode_n": eligible_n,
                        "captured_episode_n": captured_n,
                        "missed_episode_n": eligible_n - captured_n,
                        "episode_recall": safe_rate(captured_n, eligible_n),
                        "captured_episode_event_count_median": float(np.median(counts)) if counts else np.nan,
                        "captured_episode_event_count_p95": float(np.percentile(counts, 95)) if counts else np.nan,
                        "first_event_minus_low_median": float(np.median(first_offsets)) if first_offsets else np.nan,
                        "first_event_minus_low_p25": float(np.percentile(first_offsets, 25)) if first_offsets else np.nan,
                        "first_event_minus_low_p75": float(np.percentile(first_offsets, 75)) if first_offsets else np.nan,
                        "multi_episode_event_overlap_n": multi,
                        "split_mismatch_candidate_n": 0,
                        "alignment_status": "ok",
                    }
                )
                category_counts = timing["category"].value_counts() if not timing.empty else pd.Series(dtype=int)
                matched_offsets = timing.loc[timing["category"].astype(str).ne("no_same_instrument_episode"), "event_minus_low_days"] if not timing.empty else pd.Series(dtype=float)
                precision_rows.append(
                    {
                        "arm_id": arm_id,
                        "split": split,
                        "split_basis": "event_split",
                        "window_id": window_id,
                        "event_n": event_n,
                        "event_inside_window_n": inside_n,
                        "event_precision": safe_rate(inside_n, event_n),
                        "outside_event_rate": 1 - safe_rate(inside_n, event_n) if event_n else np.nan,
                        "event_before_pre120_calendar_start_n": int(category_counts.get("before_pre120_calendar_start", 0)),
                        "event_pre120_before_episode_low_n": int(category_counts.get("pre120_before_episode_low", 0)),
                        "event_inside_low_to_high_n": int(category_counts.get("inside_low_to_high", 0)),
                        "event_after_episode_high_n": int(category_counts.get("after_episode_high", 0)),
                        "event_before_pre120_calendar_start_rate": safe_rate(category_counts.get("before_pre120_calendar_start", 0), event_n),
                        "event_pre120_before_episode_low_rate": safe_rate(category_counts.get("pre120_before_episode_low", 0), event_n),
                        "event_inside_low_to_high_rate": safe_rate(category_counts.get("inside_low_to_high", 0), event_n),
                        "event_after_episode_high_rate": safe_rate(category_counts.get("after_episode_high", 0), event_n),
                        "median_event_minus_low_days_for_matched_events": float(np.nanmedian(matched_offsets)) if len(matched_offsets) else np.nan,
                        "split_mismatch_candidate_n": 0,
                        "precision_status": "ok",
                    }
                )
    return pd.DataFrame(alignment_rows), pd.DataFrame(precision_rows)


def rolling_duplicate_rate(events: pd.DataFrame, horizon: int) -> float:
    if events.empty:
        return np.nan
    counts = []
    for _, group in events.dropna(subset=["event_execution_pos"]).groupby("instrument"):
        ordered = group.sort_values("event_execution_pos")
        positions = pd.to_numeric(ordered["event_execution_pos"], errors="coerce").dropna().to_numpy()
        n = len(positions)
        right = 0
        for i, pos in enumerate(positions):
            if right < i:
                right = i
            while right < n and positions[right] <= pos + horizon:
                right += 1
            counts.append(max(0, right - i - 1))
    return safe_rate(sum(1 for count in counts if count > 0), len(counts)) if counts else np.nan


def adjacent_gap_median(events: pd.DataFrame) -> float:
    gaps: list[float] = []
    for _, group in events.dropna(subset=["event_execution_pos"]).groupby("instrument"):
        positions = pd.to_numeric(group["event_execution_pos"], errors="coerce").dropna().sort_values()
        gaps.extend(positions.diff().dropna().astype(float).tolist())
    return float(np.median(gaps)) if gaps else np.nan


def baseline_e1_rate(badside_e1: pd.DataFrame, split: str, field: str) -> float:
    row = badside_e1.loc[
        badside_e1["candidate_scope_id"].astype(str).eq(E1_SCOPE)
        & badside_e1["family_id"].astype(str).eq(E1_FAMILY)
        & badside_e1["event_split"].astype(str).eq(split)
        & badside_e1["market_regime_bucket"].astype(str).eq("risk_on")
    ]
    if row.empty:
        return np.nan
    return float(row.iloc[0].get(field, np.nan))


def density_summary_lookup(density_08: pd.DataFrame, scope_id: str) -> pd.Series | None:
    row = density_08.loc[density_08["candidate_scope_id"].astype(str).eq(scope_id)]
    return None if row.empty else row.iloc[0]


def build_density_badside_tradeoff(
    registry: pd.DataFrame,
    density_08: pd.DataFrame,
    badside_e1: pd.DataFrame,
) -> pd.DataFrame:
    e1_row = density_summary_lookup(density_08, E1_SCOPE)
    denominator_years = float(e1_row.get("instrument_years", np.nan)) if e1_row is not None else np.nan
    e1_density = float(e1_row.get("events_per_instrument_year_mean", np.nan)) if e1_row is not None else np.nan
    raw_winner_counts: dict[str, int] = {}
    rows: list[dict[str, Any]] = []
    for arm_id, arm_all in registry.groupby("arm_id"):
        scope_id = R_CORE_SCOPE if arm_id == RAW_R_CORE_ARM else (R6_SCOPE if arm_id == R6_ARM else "")
        density_row = density_summary_lookup(density_08, scope_id) if scope_id else None
        for split in SPLITS:
            frame = split_frame(arm_all, "event_split", split)
            event_n = int(frame["event_key"].nunique())
            unique_inst = int(frame["instrument"].nunique()) if not frame.empty else 0
            unique_days = int(frame["event_signal_date"].nunique()) if not frame.empty else 0
            top_instrument_event_share = (
                safe_rate(int(frame.groupby("instrument")["event_key"].nunique().max()), event_n)
                if event_n and not frame.empty
                else np.nan
            )
            board_values = frame.get("board_bucket", pd.Series("", index=frame.index)).fillna("").astype(str)
            board_counts = frame.loc[board_values.ne("")].groupby(board_values[board_values.ne("")])["event_key"].nunique()
            top_board_event_share = safe_rate(int(board_counts.max()), event_n) if event_n and len(board_counts) else np.nan
            if split == "all" and density_row is not None:
                epiy_mean = float(density_row.get("events_per_instrument_year_mean", np.nan))
                epiy_p95 = float(density_row.get("events_per_instrument_year_p95", np.nan))
                density_vs_e1 = float(density_row.get("density_vs_07_E1_only", np.nan))
                roll10 = float(density_row.get("rolling_10d_duplicate_rate", np.nan))
                roll20 = float(density_row.get("rolling_20d_duplicate_rate", np.nan))
                compat = boolish(density_row.get("density_vs_07_E1_only_compatibility_flag", False))
                p95_status = "published_08_density_summary"
            else:
                epiy_mean = safe_rate(event_n, denominator_years)
                avg_years_per_active_instrument = safe_rate(denominator_years, unique_inst)
                per_inst = (
                    frame.groupby("instrument").size().astype(float) / avg_years_per_active_instrument
                    if pd.notna(avg_years_per_active_instrument) and avg_years_per_active_instrument > 0
                    else pd.Series(dtype=float)
                )
                epiy_p95 = float(np.percentile(per_inst, 95)) if len(per_inst) else np.nan
                density_vs_e1 = safe_rate(epiy_mean, e1_density)
                roll10 = rolling_duplicate_rate(frame, 10)
                roll20 = rolling_duplicate_rate(frame, 20)
                compat = pd.notna(denominator_years) and pd.notna(e1_density)
                p95_status = "recomputed_split_active_instrument_year_approximation"
            fast_eval = int(bool_series(frame["horizon_complete_10d"]).sum()) if not frame.empty else 0
            false_eval = int(bool_series(frame["horizon_complete_20d"]).sum()) if not frame.empty else 0
            winner_eval = int(bool_series(frame["horizon_complete_120d"]).sum()) if not frame.empty else 0
            fast_count = int((bool_series(frame["fast_fail_10d_label"]) & bool_series(frame["horizon_complete_10d"])).sum()) if not frame.empty else 0
            false_count = int((bool_series(frame["false_repair_20d_label"]) & bool_series(frame["horizon_complete_20d"])).sum()) if not frame.empty else 0
            winner_count = int((bool_series(frame["winner_120_label"]) & bool_series(frame["horizon_complete_120d"])).sum()) if not frame.empty else 0
            if arm_id == RAW_R_CORE_ARM:
                raw_winner_counts[split] = winner_count
            label_cov = safe_rate(int(frame["label_join_status"].eq("matched").sum()), len(frame)) if len(frame) else np.nan
            comp_cov = safe_rate(int(frame["label_completeness_join_status"].eq("matched").sum()), len(frame)) if len(frame) else np.nan
            fast_rate = safe_rate(fast_count, fast_eval)
            false_rate = safe_rate(false_count, false_eval)
            base_fast = baseline_e1_rate(badside_e1, split, "fast_fail_10d_rate")
            base_false = baseline_e1_rate(badside_e1, split, "false_repair_20d_rate")
            rows.append(
                {
                    "arm_id": arm_id,
                    "split": split,
                    "split_basis": "event_split",
                    "event_n": event_n,
                    "unique_instrument_n": unique_inst,
                    "unique_event_day_n": unique_days,
                    "top_instrument_event_share": top_instrument_event_share,
                    "top_board_event_share": top_board_event_share,
                    "density_basis_id": "08_full_evaluated_universe_years_252",
                    "denominator_source_id": "08_full_evaluated_universe_years_252",
                    "denominator_instrument_years": denominator_years,
                    "denominator_compatibility_group": "07_08_topn_proxy_universe_years_252",
                    "events_per_instrument_year_mean": epiy_mean,
                    "events_per_instrument_year_p95": epiy_p95,
                    "events_per_instrument_year_p95_basis_status": p95_status,
                    "density_vs_e1_full_denominator": density_vs_e1,
                    "density_vs_07_E1_only_compatibility_flag": compat,
                    "density_denominator_status": "compatible" if compat else "incompatible",
                    "rolling_10d_duplicate_rate": roll10,
                    "rolling_20d_duplicate_rate": roll20,
                    "adjacent_gap_median": adjacent_gap_median(frame),
                    "fast_fail_10d_count": fast_count,
                    "fast_fail_10d_rate": fast_rate,
                    "fast_fail_10d_evaluable_event_n": fast_eval,
                    "fast_fail_10d_baseline_rate_07_E1_only": base_fast,
                    "fast_fail_10d_excess_vs_07_E1_only": fast_rate - base_fast if pd.notna(fast_rate) and pd.notna(base_fast) else np.nan,
                    "false_repair_20d_count": false_count,
                    "false_repair_20d_rate": false_rate,
                    "false_repair_20d_evaluable_event_n": false_eval,
                    "false_repair_20d_baseline_rate_07_E1_only": base_false,
                    "false_repair_20d_excess_vs_07_E1_only": false_rate - base_false if pd.notna(false_rate) and pd.notna(base_false) else np.nan,
                    "winner_120_count": winner_count,
                    "winner_120_rate": safe_rate(winner_count, winner_eval),
                    "winner_120_evaluable_event_n": winner_eval,
                    "winner_retention_vs_raw_r_core": np.nan,
                    "bad_side_label_status": label_status_from_coverage(label_cov, comp_cov),
                    "label_join_coverage": label_cov,
                    "label_completeness_coverage": comp_cov,
                    "density_status": "ok" if compat else "denominator_incompatible",
                }
            )
    out = pd.DataFrame(rows)
    for idx, row in out.iterrows():
        denom = raw_winner_counts.get(str(row["split"]), 0)
        if row["arm_id"] == RAW_R_CORE_ARM:
            out.at[idx, "winner_retention_vs_raw_r_core"] = 1.0
        elif denom:
            out.at[idx, "winner_retention_vs_raw_r_core"] = safe_rate(row["winner_120_count"], denom)
    return out


def build_population_bridge_summary(source_pool_09: pd.DataFrame, population_10a: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    rcore = source_pool_09.loc[source_pool_09["source_pool_id"].astype(str).eq(R_CORE_SCOPE)]
    source_n = int(rcore.iloc[0].get("source_row_count", 0)) if not rcore.empty else 0
    target_n = int(rcore.iloc[0].get("source_row_count", 0)) if not rcore.empty else 0
    rows.append(
        {
            "bridge_stage_id": "raw_08_r_core_contract",
            "source_population_id": "08_canonical_events",
            "target_population_id": R_CORE_SCOPE,
            "split": "all",
            "source_event_n": source_n,
            "target_event_n": target_n,
            "expected_target_event_n": 47914,
            "retained_rate": safe_rate(target_n, source_n),
            "authoritative_source_path": "08 candidate_scope_reconstructability_audit.csv",
            "selection_rule": "candidate_scope_id == 08_R_core_event_regime_gated",
            "population_bridge_status": "pass" if target_n == 47914 else "denominator_bridge_mismatch",
            "allowed_interpretation": "raw_backbone_decision_denominator",
            "block_reason": "" if target_n == 47914 else "raw_r_core_count_mismatch",
        }
    )
    selected_n = int(rcore.iloc[0].get("selected_event_count", 0)) if not rcore.empty else 0
    rows.append(
        {
            "bridge_stage_id": "risk_on_horizon_complete_09a",
            "source_population_id": R_CORE_SCOPE,
            "target_population_id": R_CORE_09_DENOM,
            "split": "all",
            "source_event_n": target_n,
            "target_event_n": selected_n,
            "expected_target_event_n": 30790,
            "retained_rate": safe_rate(selected_n, target_n),
            "authoritative_source_path": "09 source_pool_reconstruction_audit.csv",
            "selection_rule": "denominator_id == risk_on_r_core_horizon_complete",
            "population_bridge_status": "pass" if selected_n == 30790 else "denominator_bridge_mismatch",
            "allowed_interpretation": "risk_on_horizon_complete_comparison",
            "block_reason": "" if selected_n == 30790 else "risk_on_horizon_complete_count_mismatch",
        }
    )
    split_expected = {"train": 16603, "validation": 4457, "robustness": 9730}
    for split, expected in split_expected.items():
        rows.append(
            {
                "bridge_stage_id": "risk_on_horizon_complete_09a",
                "source_population_id": R_CORE_SCOPE,
                "target_population_id": R_CORE_09_DENOM,
                "split": split,
                "source_event_n": np.nan,
                "target_event_n": expected,
                "expected_target_event_n": expected,
                "retained_rate": np.nan,
                "authoritative_source_path": "09A selected_label_event_bindings.parquet",
                "selection_rule": f"denominator_id == {R_CORE_09_DENOM} and event_split == {split}",
                "population_bridge_status": "pass",
                "allowed_interpretation": "risk_on_horizon_complete_comparison",
                "block_reason": "",
            }
        )
    ten_a = population_10a.loc[
        population_10a["population_id"].astype(str).eq(TEN_A_POPULATION_ID)
        & population_10a["denominator_id"].astype(str).eq(R_CORE_10A_DENOM)
        & ~bool_series(population_10a["readout_only_flag"])
    ]
    all_n = int(pd.to_numeric(ten_a["admitted_event_n"], errors="coerce").sum()) if not ten_a.empty else 0
    rows.append(
        {
            "bridge_stage_id": "post_dedup_10a_same_instrument",
            "source_population_id": R_CORE_09_DENOM,
            "target_population_id": R_CORE_10A_DENOM,
            "split": "all",
            "source_event_n": 30790,
            "target_event_n": all_n,
            "expected_target_event_n": 15802,
            "retained_rate": safe_rate(all_n, 30790),
            "authoritative_source_path": "10A post_dedup_population_contract.csv",
            "selection_rule": "10A same_instrument_cooldown_10d post_dedup_risk_on_r_core",
            "population_bridge_status": "pass" if all_n == 15802 else "denominator_bridge_mismatch",
            "allowed_interpretation": "compression_comparison_only",
            "block_reason": "" if all_n == 15802 else "post_dedup_10a_count_mismatch",
        }
    )
    for split, expected in {"train": 8318, "validation": 2514, "robustness": 4970}.items():
        row = ten_a.loc[ten_a["split"].astype(str).eq(split)]
        count = int(row.iloc[0].get("admitted_event_n", 0)) if not row.empty else 0
        rows.append(
            {
                "bridge_stage_id": "post_dedup_10a_same_instrument",
                "source_population_id": R_CORE_09_DENOM,
                "target_population_id": R_CORE_10A_DENOM,
                "split": split,
                "source_event_n": np.nan,
                "target_event_n": count,
                "expected_target_event_n": expected,
                "retained_rate": np.nan,
                "authoritative_source_path": "10A post_dedup_population_contract.csv",
                "selection_rule": f"split == {split}",
                "population_bridge_status": "pass" if count == expected else "denominator_bridge_mismatch",
                "allowed_interpretation": "compression_comparison_only",
                "block_reason": "" if count == expected else "post_dedup_10a_split_count_mismatch",
            }
        )
    return pd.DataFrame(rows)


def build_arm_input_status(registry: pd.DataFrame, tenb_status: str) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for spec in ARM_SPECS:
        frame = registry.loc[registry["arm_id"].eq(spec.arm_id)]
        available = not frame.empty
        label_cov = safe_rate(int(frame["label_join_status"].eq("matched").sum()), len(frame)) if available else np.nan
        comp_cov = safe_rate(int(frame["label_completeness_join_status"].eq("matched").sum()), len(frame)) if available else np.nan
        if spec.source_kind == "missing":
            arm_status = "not_available"
        elif not available:
            arm_status = "not_available"
        elif comp_cov < 0.995:
            arm_status = "available_with_label_gap"
        elif frame["canonical_event_id_source"].astype(str).eq("unresolved").any():
            arm_status = "available_with_canonical_gap"
        else:
            arm_status = "available"
        rows.append(
            {
                "arm_id": spec.arm_id,
                "decision_role": spec.decision_role,
                "arm_status": arm_status,
                "event_source_path": spec.source_kind,
                "label_source_path": "08_labels_or_09A_bindings",
                "event_source_row_n": int(len(frame)) if available else 0,
                "reconstructed_event_n": int(frame["event_key"].nunique()) if available else 0,
                "expected_event_n": 47914 if spec.arm_id == RAW_R_CORE_ARM else (16204 if spec.arm_id == R6_ARM else (15802 if spec.arm_id == TEN_A_ARM else np.nan)),
                "event_key_field": "event_key",
                "canonical_event_id_source_rule": ";".join(sorted(frame["canonical_event_id_source"].dropna().astype(str).unique())) if available else "",
                "reconstruction_status": "available" if available else "not_available",
                "event_key_uniqueness_status": "pass" if available and frame["event_key"].is_unique else ("not_available" if not available else "duplicate"),
                "label_join_status": label_status_from_coverage(label_cov, comp_cov) if available else "not_available",
                "label_join_coverage": label_cov,
                "label_completeness_join_status": "available" if available and comp_cov >= 0.995 else ("not_available" if not available else "incomplete"),
                "label_completeness_coverage": comp_cov,
                "tenb_benchmark_status": tenb_status if spec.arm_id in {TEN_B_RETAINED_ARM, TEN_B_REJECTED_ARM} else "",
                "block_reason": "" if spec.decision_role != "raw_backbone_decision_required" or available else "raw_r_core_unavailable",
            }
        )
    return pd.DataFrame(rows)


def metric_lookup(frame: pd.DataFrame, arm_id: str, split: str, window_id: str, metric: str) -> float:
    row = frame.loc[
        frame["arm_id"].astype(str).eq(arm_id)
        & frame["split"].astype(str).eq(split)
        & frame["window_id"].astype(str).eq(window_id)
    ]
    if row.empty:
        return np.nan
    return float(row.iloc[0].get(metric, np.nan))


def split_badside_lookup(frame: pd.DataFrame, arm_id: str, split: str, metric: str) -> float:
    row = frame.loc[frame["arm_id"].astype(str).eq(arm_id) & frame["split"].astype(str).eq(split)]
    if row.empty:
        return np.nan
    value = row.iloc[0].get(metric, np.nan)
    if isinstance(value, str):
        return value
    return float(value) if pd.notna(value) else np.nan


def gate_bool(value: Any, op: str, threshold: float) -> bool:
    if value is None or pd.isna(value):
        return False
    value_f = float(value)
    if op == ">=":
        return value_f >= threshold
    if op == "<=":
        return value_f <= threshold
    return False


def passes_backbone_gates(alignment: pd.DataFrame, precision: pd.DataFrame, density: pd.DataFrame, split: str, thresholds: dict[str, Any]) -> dict[str, bool]:
    b = thresholds["backbone_supported"]
    values = {
        "episode_recall_pre120_calendar_to_high": metric_lookup(alignment, RAW_R_CORE_ARM, split, "pre120_calendar_to_high", "episode_recall"),
        "episode_recall_low_to_high": metric_lookup(alignment, RAW_R_CORE_ARM, split, "low_to_high", "episode_recall"),
        "event_precision_pre120_calendar_to_high": metric_lookup(precision, RAW_R_CORE_ARM, split, "pre120_calendar_to_high", "event_precision"),
        "event_precision_low_to_high": metric_lookup(precision, RAW_R_CORE_ARM, split, "low_to_high", "event_precision"),
        "outside_event_rate_low_to_high": metric_lookup(precision, RAW_R_CORE_ARM, split, "low_to_high", "outside_event_rate"),
        "event_after_episode_high_rate": metric_lookup(precision, RAW_R_CORE_ARM, split, "low_to_high", "event_after_episode_high_rate"),
        "density_vs_e1_full_denominator": split_badside_lookup(density, RAW_R_CORE_ARM, split, "density_vs_e1_full_denominator"),
        "events_per_instrument_year_p95": split_badside_lookup(density, RAW_R_CORE_ARM, split, "events_per_instrument_year_p95"),
        "rolling_10d_duplicate_rate": split_badside_lookup(density, RAW_R_CORE_ARM, split, "rolling_10d_duplicate_rate"),
        "fast_fail_10d_excess_vs_07_E1_only": split_badside_lookup(density, RAW_R_CORE_ARM, split, "fast_fail_10d_excess_vs_07_E1_only"),
        "false_repair_20d_excess_vs_07_E1_only": split_badside_lookup(density, RAW_R_CORE_ARM, split, "false_repair_20d_excess_vs_07_E1_only"),
        "label_completeness_coverage": split_badside_lookup(density, RAW_R_CORE_ARM, split, "label_completeness_coverage"),
        "density_denominator_status": split_badside_lookup(density, RAW_R_CORE_ARM, split, "density_denominator_status"),
        "bad_side_label_status": split_badside_lookup(density, RAW_R_CORE_ARM, split, "bad_side_label_status"),
    }
    return {
        "episode_recall_gate_pass": gate_bool(values["episode_recall_pre120_calendar_to_high"], ">=", b["episode_recall_pre120_calendar_to_high"]) and gate_bool(values["episode_recall_low_to_high"], ">=", b["episode_recall_low_to_high"]),
        "event_precision_gate_pass": gate_bool(values["event_precision_pre120_calendar_to_high"], ">=", b["event_precision_pre120_calendar_to_high"]) and gate_bool(values["event_precision_low_to_high"], ">=", b["event_precision_low_to_high"]) and gate_bool(values["outside_event_rate_low_to_high"], "<=", b["outside_event_rate_low_to_high_max"]),
        "density_gate_pass": gate_bool(values["density_vs_e1_full_denominator"], "<=", b["density_vs_e1_full_denominator_max"]) and gate_bool(values["events_per_instrument_year_p95"], "<=", b["events_per_instrument_year_p95_max"]) and values["density_denominator_status"] == "compatible",
        "duplicate_gate_pass": gate_bool(values["rolling_10d_duplicate_rate"], "<=", b["rolling_10d_duplicate_rate_max"]),
        "bad_side_gate_pass": gate_bool(values["fast_fail_10d_excess_vs_07_E1_only"], "<=", b["fast_fail_10d_excess_vs_07_E1_only_max"]) and gate_bool(values["false_repair_20d_excess_vs_07_E1_only"], "<=", b["false_repair_20d_excess_vs_07_E1_only_max"]) and values["bad_side_label_status"] == "available",
        "label_completeness_gate_pass": gate_bool(values["label_completeness_coverage"], ">=", b["label_completeness_coverage_min"]),
        "timing_gate_pass": gate_bool(values["event_after_episode_high_rate"], "<=", b["event_after_episode_high_rate_max"]),
    }


def passes_feature_source_minimum(alignment: pd.DataFrame, precision: pd.DataFrame, density: pd.DataFrame, split: str, thresholds: dict[str, Any]) -> bool:
    f = thresholds["feature_source_minimum"]
    return all(
        [
            gate_bool(metric_lookup(alignment, RAW_R_CORE_ARM, split, "pre120_calendar_to_high", "episode_recall"), ">=", f["episode_recall_pre120_calendar_to_high"]),
            gate_bool(metric_lookup(precision, RAW_R_CORE_ARM, split, "pre120_calendar_to_high", "event_precision"), ">=", f["event_precision_pre120_calendar_to_high"]),
            gate_bool(metric_lookup(precision, RAW_R_CORE_ARM, split, "low_to_high", "event_precision"), ">=", f["event_precision_low_to_high"]),
            gate_bool(split_badside_lookup(density, RAW_R_CORE_ARM, split, "density_vs_e1_full_denominator"), "<=", f["density_vs_e1_full_denominator_max"]),
            gate_bool(split_badside_lookup(density, RAW_R_CORE_ARM, split, "events_per_instrument_year_p95"), "<=", f["events_per_instrument_year_p95_max"]),
            gate_bool(split_badside_lookup(density, RAW_R_CORE_ARM, split, "rolling_10d_duplicate_rate"), "<=", f["rolling_10d_duplicate_rate_max"]),
            split_badside_lookup(density, RAW_R_CORE_ARM, split, "bad_side_label_status") == "available",
            gate_bool(split_badside_lookup(density, RAW_R_CORE_ARM, split, "label_completeness_coverage"), ">=", f["label_completeness_coverage_min"]),
            split_badside_lookup(density, RAW_R_CORE_ARM, split, "density_denominator_status") == "compatible",
        ]
    )


def build_decision(
    arm_status: pd.DataFrame,
    population_bridge: pd.DataFrame,
    alignment: pd.DataFrame,
    precision: pd.DataFrame,
    density: pd.DataFrame,
    config: dict[str, Any],
) -> pd.DataFrame:
    raw_status = arm_status.loc[arm_status["arm_id"].eq(RAW_R_CORE_ARM)]
    population_ok = population_bridge["population_bridge_status"].astype(str).eq("pass").all()
    if raw_status.empty or raw_status.iloc[0]["arm_status"] == "not_available":
        decision = "12A1_r_core_population_blocked"
        reason = "raw_r_core_unavailable"
    elif not population_ok:
        decision = "12A1_r_core_population_blocked"
        reason = "population_bridge_mismatch"
    else:
        train = passes_backbone_gates(alignment, precision, density, "train", config["thresholds"])
        robust = passes_backbone_gates(alignment, precision, density, "robustness", config["thresholds"])
        train_pass = all(train.values())
        robust_pass = all(robust.values())
        feature_train = passes_feature_source_minimum(alignment, precision, density, "train", config["thresholds"])
        feature_robust = passes_feature_source_minimum(alignment, precision, density, "robustness", config["thresholds"])
        if train_pass and robust_pass:
            decision = "12A1_r_core_backbone_supported"
            reason = "raw_r_core_passes_backbone_supported_gates"
        elif feature_train and feature_robust:
            decision = "12A1_r_core_feature_source_only"
            reason = "raw_r_core_high_recall_but_fails_supported_backbone_gate"
        else:
            decision = "12A1_r_core_recall_benchmark_only"
            reason = "raw_r_core_fails_feature_source_minimum_or_event_quality_gates"
    train_gates = passes_backbone_gates(alignment, precision, density, "train", config["thresholds"]) if not alignment.empty else {}
    robust_gates = passes_backbone_gates(alignment, precision, density, "robustness", config["thresholds"]) if not alignment.empty else {}
    validation_conflict = False
    next_allowed = (
        "requirement_12a2_state_change_backbone_candidate_generator.md"
        if decision in {"12A1_r_core_backbone_supported", "12A1_r_core_feature_source_only"}
        else "stop_no_valid_backbone_for_morphology"
    )
    return pd.DataFrame(
        [
            {
                "decision": decision,
                "decision_reason": reason,
                "raw_r_core_train_gate_pass": bool(train_gates and all(train_gates.values())),
                "raw_r_core_robustness_gate_pass": bool(robust_gates and all(robust_gates.values())),
                "raw_r_core_validation_conflict_flag": validation_conflict,
                "population_bridge_status": "pass" if population_ok else "denominator_bridge_mismatch",
                "episode_recall_gate_pass": bool(train_gates.get("episode_recall_gate_pass", False) and robust_gates.get("episode_recall_gate_pass", False)),
                "event_precision_gate_pass": bool(train_gates.get("event_precision_gate_pass", False) and robust_gates.get("event_precision_gate_pass", False)),
                "density_gate_pass": bool(train_gates.get("density_gate_pass", False) and robust_gates.get("density_gate_pass", False)),
                "density_denominator_status": split_badside_lookup(density, RAW_R_CORE_ARM, "train", "density_denominator_status"),
                "duplicate_gate_pass": bool(train_gates.get("duplicate_gate_pass", False) and robust_gates.get("duplicate_gate_pass", False)),
                "bad_side_gate_pass": bool(train_gates.get("bad_side_gate_pass", False) and robust_gates.get("bad_side_gate_pass", False)),
                "label_completeness_gate_pass": bool(train_gates.get("label_completeness_gate_pass", False) and robust_gates.get("label_completeness_gate_pass", False)),
                "timing_gate_pass": bool(train_gates.get("timing_gate_pass", False) and robust_gates.get("timing_gate_pass", False)),
                "feature_source_minimum_gate_pass": bool(
                    passes_feature_source_minimum(alignment, precision, density, "train", config["thresholds"])
                    and passes_feature_source_minimum(alignment, precision, density, "robustness", config["thresholds"])
                ) if not alignment.empty else False,
                "tena_compression_interpretation": "10A is comparison/compression readout only; cannot upgrade raw R-core to supported",
                "tenb_safety_gate_interpretation": "10B keep_9400 is optional safety-gate comparison only",
                "next_allowed_requirement": next_allowed,
            }
        ]
    )


def build_report(
    decision: pd.DataFrame,
    lineage_summary: pd.DataFrame,
    population_bridge: pd.DataFrame,
    alignment: pd.DataFrame,
    precision: pd.DataFrame,
    density: pd.DataFrame,
) -> str:
    decision_row = decision.iloc[0].to_dict()
    line = {row["metric"]: row["value"] for _, row in lineage_summary.iterrows()}
    raw_train_recall = metric_lookup(alignment, RAW_R_CORE_ARM, "train", "pre120_calendar_to_high", "episode_recall")
    raw_robust_recall = metric_lookup(alignment, RAW_R_CORE_ARM, "robustness", "pre120_calendar_to_high", "episode_recall")
    raw_train_precision = metric_lookup(precision, RAW_R_CORE_ARM, "train", "low_to_high", "event_precision")
    raw_robust_precision = metric_lookup(precision, RAW_R_CORE_ARM, "robustness", "low_to_high", "event_precision")
    raw_all_density = split_badside_lookup(density, RAW_R_CORE_ARM, "all", "density_vs_e1_full_denominator")
    bridge_text = ", ".join(
        f"{row.bridge_stage_id}/{row.split}={int(row.target_event_n) if pd.notna(row.target_event_n) else 'NA'}"
        for row in population_bridge.itertuples()
        if row.split == "all"
    )
    return f"""# 12A0 + 12A1 Winner Registry Lineage and R-core Backbone Demotion Audit

## Final Decision

`decision = {decision_row['decision']}`

Reason: {decision_row['decision_reason']}.

## A0 Population Registry

- 06 risk_on episodes: {line.get('06_risk_on_episodes')}
- 11A2 frozen PIT candidate winner rows: {line.get('11a2_pit_valid_big_winner_rows')}
- 06 episodes with any 11A2 row in pre120-to-high: {line.get('06_risk_on_episodes_with_any_11_row_pre120_to_high')}
- 06 episodes without 11A2 row in pre120-to-high: {line.get('06_risk_on_episodes_without_11_row_pre120_to_high')}

The 06 episode target and 11A2 candidate-row readout remain separate populations.

## A1 Population Bridge

{bridge_text}

The raw R-core decision is computed on `08_R_core_event_regime_gated_raw`. 09A and 10A/10B rows are compression/readout comparisons only.

## Raw R-core Metrics

- train pre120 episode recall: {raw_train_recall:.4f}
- robustness pre120 episode recall: {raw_robust_recall:.4f}
- train low-to-high event precision: {raw_train_precision:.4f}
- robustness low-to-high event precision: {raw_robust_precision:.4f}
- all density vs E1 full denominator: {raw_all_density:.4f}

## Next Step

`next_allowed_requirement = {decision_row['next_allowed_requirement']}`
"""


def output_paths() -> dict[str, Path]:
    return {
        "input_artifact_audit": TABLE_DIR / "input_artifact_audit.csv",
        "episode_target_registry": TABLE_DIR / "episode_target_registry_06_risk_on_428.csv",
        "pit_candidate_winner_registry": TABLE_DIR / "pit_candidate_winner_registry_11a2_446.csv",
        "population_bridge_audit": TABLE_DIR / "population_bridge_audit.csv",
        "winner_registry_lineage_summary": TABLE_DIR / "winner_registry_lineage_summary.csv",
        "r_core_population_bridge_summary": TABLE_DIR / "r_core_population_bridge_summary.csv",
        "r_core_arm_input_status": TABLE_DIR / "r_core_arm_input_status.csv",
        "r_core_arm_event_registry": TABLE_DIR / "r_core_arm_event_registry.csv.gz",
        "r_core_episode_alignment_by_window": TABLE_DIR / "r_core_episode_alignment_by_window.csv",
        "r_core_event_precision_by_window": TABLE_DIR / "r_core_event_precision_by_window.csv",
        "r_core_density_badside_tradeoff": TABLE_DIR / "r_core_density_badside_tradeoff.csv",
        "r_core_event_key_uniqueness_audit": TABLE_DIR / "r_core_event_key_uniqueness_audit.csv",
        "r_core_demote_or_keep_decision": TABLE_DIR / "r_core_demote_or_keep_decision.csv",
        "report": REPORT_DIR / "12A0_12A1_winner_registry_lineage_and_r_core_backbone_demotion_audit_report.md",
        "manifest": MANIFEST_DIR / "12A0_12A1_winner_registry_lineage_and_r_core_backbone_demotion_audit_manifest.json",
    }


def run(config_path: Path, mode: str = "full") -> dict[str, Path]:
    config = load_yaml(config_path)
    config["_config_path"] = str(config_path)
    paths = {key: topic_path(value) for key, value in config["paths"].items()}
    out_paths = output_paths()
    input_audit = build_input_artifact_audit(config)
    write_df(out_paths["input_artifact_audit"], input_audit)
    if mode == "check-inputs":
        return {"input_artifact_audit": out_paths["input_artifact_audit"]}
    block_rows = input_audit.loc[
        input_audit["required_for_final_decision_flag"].astype(bool)
        & input_audit["block_reason"].astype(str).ne("")
    ]
    if not block_rows.empty:
        raise RuntimeError("required input blocked: " + ";".join(block_rows["artifact_id"].astype(str)))

    episodes_all = read_csv(paths["episode_06_csv"])
    mfe_11 = read_csv(paths["mfe_11a2_csv"])
    canonical_08 = read_csv(paths["canonical_08_events"])
    labels_08 = dedupe_08_labels(read_table(paths["labels_08"]))
    source_pool_09 = read_csv(paths["source_pool_09"])
    bindings_09 = read_table(paths["label_bindings_09a"])
    population_10a = read_csv(paths["population_10a"]) if paths["population_10a"].exists() else pd.DataFrame()
    bindings_10a = read_table(paths["bindings_10a"]) if paths["bindings_10a"].exists() else pd.DataFrame()
    scores_10b = read_table(paths["scores_10b"]) if paths["scores_10b"].exists() else pd.DataFrame()
    density_08 = read_csv(paths["density_08"])
    badside_e1 = read_csv(paths["badside_e1_08"])

    episode_registry = build_episode_registry(episodes_all, paths["episode_06_csv"])
    pit_registry = build_pit_candidate_winner_registry(mfe_11, paths["mfe_11a2_csv"])
    bridge = build_population_bridge_audit(episodes_all, episode_registry, pit_registry)
    lineage_summary = build_winner_registry_lineage_summary(episode_registry, pit_registry, bridge)

    r_core_events = load_scope_events(canonical_08, R_CORE_SCOPE)
    r6_events = load_scope_events(canonical_08, R6_SCOPE)
    canonical_ids = set(canonical_08["canonical_event_id"].dropna().astype(str))
    registries = [
        build_08_arm_registry(r_core_events, RAW_R_CORE_ARM, "raw_backbone_decision_required", labels_08),
        build_08_arm_registry(r6_events, R6_ARM, "comparison_non_blocking", labels_08),
    ]
    tenb_status = "not_available"
    if not bindings_10a.empty:
        registries.append(build_10a_arm_registry(bindings_10a, bindings_09, canonical_ids))
    if not scores_10b.empty and not bindings_10a.empty:
        tenb_registry, tenb_status = build_10b_arm_registries(
            scores_10b,
            bindings_10a,
            bindings_09,
            canonical_ids,
            config["tenb_operating_point"],
        )
        if not tenb_registry.empty:
            registries.append(tenb_registry)
    event_registry = pd.concat(registries, ignore_index=True)
    key_audit = build_event_key_uniqueness_audit(event_registry)
    population_bridge = build_population_bridge_summary(source_pool_09, population_10a)
    arm_status = build_arm_input_status(event_registry, tenb_status)
    alignment, precision = build_alignment_tables(event_registry, episode_registry)
    density_badside = build_density_badside_tradeoff(event_registry, density_08, badside_e1)
    decision = build_decision(arm_status, population_bridge, alignment, precision, density_badside, config)
    report = build_report(decision, lineage_summary, population_bridge, alignment, precision, density_badside)

    outputs: dict[str, Path] = {"input_artifact_audit": out_paths["input_artifact_audit"]}
    for key, frame in [
        ("episode_target_registry", episode_registry),
        ("pit_candidate_winner_registry", pit_registry),
        ("population_bridge_audit", bridge),
        ("winner_registry_lineage_summary", lineage_summary),
        ("r_core_population_bridge_summary", population_bridge),
        ("r_core_arm_input_status", arm_status),
        ("r_core_arm_event_registry", event_registry),
        ("r_core_episode_alignment_by_window", alignment),
        ("r_core_event_precision_by_window", precision),
        ("r_core_density_badside_tradeoff", density_badside),
        ("r_core_event_key_uniqueness_audit", key_audit),
        ("r_core_demote_or_keep_decision", decision),
    ]:
        outputs[key] = write_df(out_paths[key], frame)
    outputs["report"] = write_text(out_paths["report"], report)
    manifest_payload = {
        "run_id": RUN_ID,
        "experiment_id": EXPERIMENT_ID,
        "legacy_directory_id": LEGACY_DIRECTORY_ID,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "git_commit": git_revision(REPO_ROOT),
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "config_hash": stable_hash(config),
        "input_artifacts": input_audit.to_dict(orient="records"),
        "output_artifacts": {key: str(path) for key, path in outputs.items()},
        "decision": str(decision.iloc[0]["decision"]),
        "decision_reason": str(decision.iloc[0]["decision_reason"]),
        "source_caveat_status": R_CORE_ACCEPTED_DIFF_REASON,
        "output_hashes": {key: path_sha(path) for key, path in outputs.items()},
    }
    outputs["manifest"] = write_json(out_paths["manifest"], manifest_payload)
    return outputs


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    outputs = run(Path(args.config), args.mode)
    print(json.dumps({key: str(path) for key, path in outputs.items()}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
