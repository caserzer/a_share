from __future__ import annotations

import copy
import importlib.util
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from afml_big_winner.config import stable_hash
from afml_big_winner.manifest import file_sha256, git_revision


TOPN_TABLE_NAMES = {
    "big_winner_episode_reference_summary": "topn_big_winner_episode_reference_summary.csv",
    "frozen_anchor_profile_summary": "topn_frozen_anchor_profile_summary.csv",
    "winner_vs_matched_control_stats": "topn_winner_vs_matched_control_stats.csv",
    "near_winner_comparison_stats": "topn_near_winner_comparison_stats.csv",
    "false_repair_comparison_stats": "topn_false_repair_comparison_stats.csv",
    "shared_axis_market_regime_dominance": "topn_shared_axis_market_regime_dominance.csv",
    "shared_axis_factor_dominance": "topn_shared_axis_factor_dominance.csv",
    "shared_axis_sequence_dominance": "topn_shared_axis_sequence_dominance.csv",
    "sequence_family_test_count": "topn_sequence_family_test_count.csv",
    "sequence_examples_descriptive": "topn_sequence_examples_descriptive.csv",
    "winner_only_retrospective_stage_profile": "topn_winner_only_retrospective_stage_profile.csv",
    "unconditional_validation_readout": "topn_unconditional_validation_readout.csv",
    "regime_conditioned_validation_readout": "topn_regime_conditioned_validation_readout.csv",
    "validation_opportunity_audit": "topn_validation_opportunity_audit.csv",
}

LOCAL_OUTPUT_RENAMES = {
    "local_cache/big_winner_episode_reference.parquet": "local_cache/topn_big_winner_episode_reference.parquet",
    "local_cache/extraction_eligibility_audit.csv": "local_cache/topn_extraction_eligibility_audit.csv",
    "local_cache/cluster_boundary_overlap_audit.csv": "local_cache/topn_cluster_boundary_overlap_audit.csv",
    "local_cache/matched_control_panel.parquet": "local_cache/topn_matched_control_panel.parquet",
    "local_cache/episode_aligned_daily_panel.parquet": "large_raw/topn_episode_aligned_daily_panel.parquet",
    "large_raw/control_candidate_pool.parquet": "large_raw/topn_control_candidate_pool.parquet",
    "large_raw/anchor_aligned_daily_panel.parquet": "large_raw/topn_anchor_aligned_daily_panel.parquet",
    "large_raw/sequence_entity_panel.parquet": "large_raw/topn_sequence_entity_panel.parquet",
}

DECISION_MAP = {
    "reverse_lifecycle_profile_supported_universal_dominance": "topn_reverse_lifecycle_profile_supported_universal_dominance",
    "reverse_lifecycle_profile_regime_conditional_candidate": "topn_reverse_lifecycle_profile_regime_conditional_candidate",
    "reverse_lifecycle_profile_negative_beta_not_supported": "topn_reverse_lifecycle_profile_negative_beta_not_supported",
    "reverse_lifecycle_profile_validation_sample_blocked": "topn_reverse_lifecycle_profile_validation_sample_blocked",
    "reverse_lifecycle_profile_sample_blocked": "topn_reverse_lifecycle_profile_sample_blocked",
    "reverse_lifecycle_sequence_supported_universal_dominance": "topn_reverse_lifecycle_sequence_supported_universal_dominance",
    "reverse_lifecycle_sequence_conditional_candidate": "topn_reverse_lifecycle_sequence_conditional_candidate",
    "marginal_and_sequence_no_stable_dominance_found": "topn_reverse_lifecycle_marginal_and_sequence_no_stable_dominance_found",
    "descriptive_profile_only_no_control_adjusted_support": "topn_reverse_lifecycle_descriptive_profile_only_no_control_adjusted_support",
}


class TopNReverseLifecycleBlocked(RuntimeError):
    def __init__(self, decision: str, message: str):
        super().__init__(message)
        self.decision = decision


@dataclass(frozen=True)
class TopNInputStatus:
    universe_precision_status: str
    topn_universe_input_accepted: bool
    exact_topn_supported: bool
    topn_candidate_gap_accepted: bool
    active_source_gap_count: int
    source_gap_count: int
    missing_active_source_instrument_count: int
    missing_active_source_audit_count_reconciled: bool
    upstream_05_decision: str
    upstream_05_manifest_hash: str
    upstream_05_data_source_coverage_audit_hash: str
    validation_failures: list[str]


def topic_path(project_root: Path, relative_or_absolute: str | Path) -> Path:
    path = Path(relative_or_absolute)
    if path.is_absolute():
        return path
    return (project_root / path).resolve()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_csv(frame: pd.DataFrame, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, encoding="utf-8")
    return path


def load_02_runner(project_root: Path) -> Any:
    code_dir = (
        project_root
        / "experiments/pending/02_big_winner_reverse_lifecycle_profile_v0/code"
    )
    src_dir = project_root / "src"
    for import_path in (src_dir, code_dir):
        if str(import_path) not in sys.path:
            sys.path.insert(0, str(import_path))

    pipeline_path = code_dir / "pipeline.py"
    run_path = code_dir / "run.py"
    pipe_spec = importlib.util.spec_from_file_location(
        "_afml_bw_02_pipeline_for_06", pipeline_path
    )
    if pipe_spec is None or pipe_spec.loader is None:
        raise ImportError(f"Cannot load 02 pipeline from {pipeline_path}")
    pipe_module = importlib.util.module_from_spec(pipe_spec)
    sys.modules[pipe_spec.name] = pipe_module
    pipe_spec.loader.exec_module(pipe_module)

    old_pipeline = sys.modules.get("pipeline")
    sys.modules["pipeline"] = pipe_module
    try:
        run_spec = importlib.util.spec_from_file_location(
            "_afml_bw_02_run_for_06", run_path
        )
        if run_spec is None or run_spec.loader is None:
            raise ImportError(f"Cannot load 02 runner from {run_path}")
        run_module = importlib.util.module_from_spec(run_spec)
        sys.modules[run_spec.name] = run_module
        run_spec.loader.exec_module(run_module)
        run_module._pipeline_module = pipe_module
    finally:
        if old_pipeline is None:
            sys.modules.pop("pipeline", None)
        else:
            sys.modules["pipeline"] = old_pipeline
    return run_module


def build_replay_config(config: dict[str, Any]) -> dict[str, Any]:
    replay = copy.deepcopy(config)
    outputs = replay["outputs"]
    outputs["publishable_reports_dir"] = (
        f"{outputs['local_cache_dir'].rstrip('/')}/02_replay_reports"
    )
    replay["experiment"] = {
        **replay.get("experiment", {}),
        "name": "topn_reverse_lifecycle_profile_v0_02_rule_replay",
    }
    return replay


def validate_topn_inputs(config: dict[str, Any], project_root: Path) -> TopNInputStatus:
    paths = config["paths"]
    manifest_path = topic_path(project_root, paths["upstream_05_run_manifest_json"])
    audit_path = topic_path(
        project_root, paths["upstream_05_data_source_coverage_audit_csv"]
    )
    if not manifest_path.is_file():
        raise TopNReverseLifecycleBlocked(
            "topn_reverse_lifecycle_topn_universe_blocked",
            f"missing 05 manifest: {manifest_path}",
        )
    if not audit_path.is_file():
        raise TopNReverseLifecycleBlocked(
            "topn_reverse_lifecycle_topn_universe_blocked",
            f"missing 05 data source audit: {audit_path}",
        )

    manifest = load_json(manifest_path)
    gate = manifest.get("gate_summary", {})
    decision = str(manifest.get("decision", ""))
    validation_failures = list(gate.get("validation_failures", []) or [])
    active_source_gap_count = int(gate.get("active_source_gap_count", 0) or 0)
    source_gap_count = int(gate.get("source_gap_count", 0) or 0)

    output_paths = manifest.get("output_paths", {}) or {}
    output_hashes = manifest.get("output_hashes", {}) or {}
    referenced_audit = output_paths.get("data_source_coverage_audit")
    referenced_hash = output_hashes.get("data_source_coverage_audit")
    actual_audit_hash = file_sha256(audit_path)
    if referenced_audit and Path(referenced_audit).resolve() != audit_path.resolve():
        raise TopNReverseLifecycleBlocked(
            "topn_reverse_lifecycle_topn_universe_blocked",
            "05 data_source_coverage_audit path does not match the manifest",
        )
    if referenced_hash and referenced_hash != actual_audit_hash:
        raise TopNReverseLifecycleBlocked(
            "topn_reverse_lifecycle_topn_universe_blocked",
            "05 data_source_coverage_audit hash does not match the manifest",
        )

    audit = pd.read_csv(audit_path)
    required_audit_columns = {"support_state", "active_in_requested_window"}
    missing = required_audit_columns.difference(audit.columns)
    if missing:
        raise TopNReverseLifecycleBlocked(
            "topn_reverse_lifecycle_topn_universe_blocked",
            f"05 audit missing columns: {sorted(missing)}",
        )
    active_mask = audit["active_in_requested_window"].astype(bool)
    missing_active = int(
        ((audit["support_state"] == "missing_active_source") & active_mask).sum()
    )
    total_missing = int(
        audit["support_state"]
        .isin(["missing_active_source", "missing_inactive_source"])
        .sum()
    )
    reconciled = missing_active == active_source_gap_count and (
        not source_gap_count or total_missing == source_gap_count
    )
    if not reconciled:
        raise TopNReverseLifecycleBlocked(
            "topn_reverse_lifecycle_topn_universe_blocked",
            "05 audit missing-source counts do not reconcile to gate_summary",
        )

    if decision == "topn_universe_supported":
        if not bool(gate.get("validation_passed", False)):
            raise TopNReverseLifecycleBlocked(
                "topn_reverse_lifecycle_topn_universe_blocked",
                "05 supported decision has validation_passed != true",
            )
        if active_source_gap_count != 0:
            raise TopNReverseLifecycleBlocked(
                "topn_reverse_lifecycle_topn_universe_blocked",
                "05 exact top-N state has active source gaps",
            )
        precision = "exact_topn"
        exact = True
        candidate_gap = False
    elif decision == "topn_universe_candidate_panel_blocked":
        if validation_failures != ["active_source_gaps"]:
            raise TopNReverseLifecycleBlocked(
                "topn_reverse_lifecycle_topn_universe_blocked",
                "05 blocked decision has failures other than active_source_gaps",
            )
        required_gate_values = {
            "candidate_panel_source": "full_board_candidate_panel",
            "max_daily_member_count": 500,
            "max_main_board_count": 400,
            "max_chinext_count": 100,
        }
        for key, expected in required_gate_values.items():
            value = gate.get(key)
            if key.endswith("_count"):
                if int(value) > int(expected):
                    raise TopNReverseLifecycleBlocked(
                        "topn_reverse_lifecycle_topn_universe_blocked",
                        f"05 gate {key}={value} exceeds {expected}",
                    )
            elif value != expected:
                raise TopNReverseLifecycleBlocked(
                    "topn_reverse_lifecycle_topn_universe_blocked",
                    f"05 gate {key}={value!r} expected {expected!r}",
                )
        precision = "available_source_topn_candidate_gap"
        exact = False
        candidate_gap = True
    else:
        raise TopNReverseLifecycleBlocked(
            "topn_reverse_lifecycle_topn_universe_blocked",
            f"unsupported 05 decision: {decision}",
        )

    return TopNInputStatus(
        universe_precision_status=precision,
        topn_universe_input_accepted=True,
        exact_topn_supported=exact,
        topn_candidate_gap_accepted=candidate_gap,
        active_source_gap_count=active_source_gap_count,
        source_gap_count=source_gap_count,
        missing_active_source_instrument_count=missing_active,
        missing_active_source_audit_count_reconciled=True,
        upstream_05_decision=decision,
        upstream_05_manifest_hash=file_sha256(manifest_path),
        upstream_05_data_source_coverage_audit_hash=actual_audit_hash,
        validation_failures=validation_failures,
    )


def patch_02_runner_for_topn(legacy_runner: Any) -> None:
    legacy_runner.PUBLISHABLE_TABLES = dict(TOPN_TABLE_NAMES)
    fast_aligned_panel = make_fast_aligned_panel_builder(
        legacy_runner._pipeline_module
    )
    legacy_runner.build_aligned_panel = fast_aligned_panel
    legacy_runner._pipeline_module.build_aligned_panel = fast_aligned_panel
    fast_sequence_evaluator = make_fast_sequence_evaluator(
        legacy_runner._pipeline_module
    )
    legacy_runner.evaluate_sequences_for_entities = fast_sequence_evaluator
    legacy_runner._pipeline_module.evaluate_sequences_for_entities = (
        fast_sequence_evaluator
    )
    fast_continuous_dominance = make_fast_continuous_dominance_summarizer(
        legacy_runner._pipeline_module
    )
    legacy_runner.summarize_continuous_dominance = fast_continuous_dominance
    legacy_runner._pipeline_module.summarize_continuous_dominance = (
        fast_continuous_dominance
    )


def make_fast_aligned_panel_builder(legacy_pipeline: Any) -> Any:
    snapshot_columns = list(legacy_pipeline.SNAPSHOT_COLUMNS)
    feature_missing_reason = legacy_pipeline.feature_missing_reason
    base_columns = [
        "entity_id",
        "instrument",
        "group",
        "shared_axis",
        "anchor_family",
        "axis_date",
        "date",
        "relative_day",
        "split",
        "duration_bucket",
        "axis_regime_bucket",
        "matched_winner_id",
        "match_id",
    ]
    feature_columns: list[str] = []
    for column in snapshot_columns:
        feature_columns.extend([column, f"{column}_missing_reason"])
    output_columns = base_columns + feature_columns

    def get_daily_cache(
        instrument: str,
        daily_by_instrument: dict[str, pd.DataFrame],
        cache: dict[str, dict[str, Any]],
    ) -> dict[str, Any] | None:
        if instrument in cache:
            return cache[instrument]
        if instrument not in daily_by_instrument:
            return None
        daily = daily_by_instrument[instrument].reset_index(drop=True)
        dates = daily["date"].astype(str).to_numpy(copy=False)
        item = {
            "dates": dates,
            "date_to_pos": {date: idx for idx, date in enumerate(dates)},
            "arrays": {
                column: daily[column].to_numpy(copy=False)
                if column in daily.columns
                else None
                for column in snapshot_columns
            },
            "vwap_reasons": daily["derived_daily_vwap_missing_reason"]
            .astype(str)
            .to_numpy(copy=False)
            if "derived_daily_vwap_missing_reason" in daily.columns
            else None,
            "length": len(daily),
        }
        cache[instrument] = item
        return item

    def build_aligned_panel_fast(
        entities: pd.DataFrame,
        daily_by_instrument: dict[str, pd.DataFrame],
        *,
        entity_id_col: str,
        axis_date_col: str,
        group_col: str,
        shared_axis: str,
        relative_start: int,
        relative_end: int,
    ) -> pd.DataFrame:
        records: list[list[Any]] = []
        daily_cache: dict[str, dict[str, Any]] = {}
        for entity in entities.itertuples(index=False):
            item = entity._asdict()
            instrument = item.get("instrument") or item.get("control_instrument")
            if not instrument:
                continue
            cached = get_daily_cache(str(instrument), daily_by_instrument, daily_cache)
            if cached is None:
                continue
            axis_date = str(item[axis_date_col])
            axis_pos = cached["date_to_pos"].get(axis_date)
            if axis_pos is None:
                continue
            base_prefix = [
                item[entity_id_col],
                str(instrument),
                item[group_col],
                shared_axis,
                "first_ema60_reclaim" if shared_axis == "shared_axis_ema60" else "",
                axis_date,
            ]
            base_suffix = [
                item.get("split", item.get("winner_split", "")),
                item.get("duration_bucket", item.get("winner_duration_bucket", "")),
                item.get("market_regime_bucket", ""),
                item.get("matched_winner_id", ""),
                item.get("match_id", ""),
            ]
            for relative_day in range(relative_start, relative_end + 1):
                pos = axis_pos + relative_day
                in_coverage = 0 <= pos < cached["length"]
                date_value = str(cached["dates"][pos]) if in_coverage else ""
                record = base_prefix + [date_value, relative_day] + base_suffix
                vwap_reasons = cached["vwap_reasons"]
                vwap_reason = (
                    str(vwap_reasons[pos])
                    if in_coverage and vwap_reasons is not None
                    else ""
                )
                for column in snapshot_columns:
                    values = cached["arrays"][column]
                    source_available = values is not None
                    value = values[pos] if in_coverage and source_available else np.nan
                    record.append(value)
                    record.append(
                        feature_missing_reason(
                            column,
                            value,
                            relative_day=relative_day,
                            in_coverage=in_coverage,
                            source_available=source_available,
                            vwap_missing_reason=vwap_reason,
                        )
                    )
                records.append(record)
        return pd.DataFrame.from_records(records, columns=output_columns)

    return build_aligned_panel_fast


def make_fast_sequence_evaluator(legacy_pipeline: Any) -> Any:
    sequence_definitions = list(legacy_pipeline.SEQUENCE_DEFINITIONS)
    evaluate_sequence = legacy_pipeline.evaluate_sequence
    output_columns = [
        "entity_id",
        "instrument",
        "group",
        "split",
        "duration_bucket",
        "axis_regime_bucket",
        "shared_axis",
        "anchor_family",
        "sequence_id",
        "sequence_family",
        "relative_window",
        "required_states",
        "forbidden_states",
        "order_constraints",
        "state_thresholds",
        "sequence_present",
        "sequence_completion_date",
        "missing_reason",
        "control_is_near_winner",
        "control_is_false_repair",
    ]

    def build_date_position_cache(
        instrument: str,
        daily_by_instrument: dict[str, pd.DataFrame],
        cache: dict[str, tuple[pd.DataFrame, dict[str, int]]],
    ) -> tuple[pd.DataFrame, dict[str, int]] | None:
        if instrument in cache:
            return cache[instrument]
        daily = daily_by_instrument.get(instrument)
        if daily is None or daily.empty:
            return None
        date_to_pos = {
            date: idx for idx, date in enumerate(daily["date"].astype(str))
        }
        item = (daily, date_to_pos)
        cache[instrument] = item
        return item

    def evaluate_sequences_for_entities_fast(
        entities: pd.DataFrame,
        daily_by_instrument: dict[str, pd.DataFrame],
        *,
        entity_id_col: str,
        axis_date_col: str,
        group_col: str,
        horizon_sessions: int,
    ) -> pd.DataFrame:
        records: list[list[Any]] = []
        daily_cache: dict[str, tuple[pd.DataFrame, dict[str, int]]] = {}
        for entity in entities.itertuples(index=False):
            item = entity._asdict()
            instrument = item.get("instrument") or item.get("control_instrument")
            if not instrument:
                continue
            cached = build_date_position_cache(
                str(instrument), daily_by_instrument, daily_cache
            )
            if cached is None:
                continue
            daily, date_to_pos = cached
            axis_date = str(item[axis_date_col])
            if axis_date not in date_to_pos:
                continue
            axis_pos = date_to_pos[axis_date]
            horizon_pos = min(axis_pos + horizon_sessions, len(daily) - 1)
            base_values = [
                item[entity_id_col],
                str(instrument),
                item[group_col],
                item.get("split", item.get("winner_split", "")),
                item.get("duration_bucket", item.get("winner_duration_bucket", "")),
                item.get("market_regime_bucket", ""),
            ]
            control_flags = [
                bool(item.get("control_is_near_winner", False)),
                bool(item.get("control_is_false_repair", False)),
            ]
            for definition in sequence_definitions:
                passed, completion_date, missing_reason = evaluate_sequence(
                    definition["sequence_id"],
                    daily,
                    axis_pos=axis_pos,
                    horizon_pos=horizon_pos,
                )
                records.append(
                    base_values
                    + [
                        definition["shared_axis"],
                        definition["anchor_family"],
                        definition["sequence_id"],
                        definition["sequence_family"],
                        definition["relative_window"],
                        definition["required_states"],
                        definition["forbidden_states"],
                        definition["order_constraints"],
                        definition["state_thresholds"],
                        bool(passed),
                        completion_date,
                        missing_reason,
                    ]
                    + control_flags
                )
        return pd.DataFrame.from_records(records, columns=output_columns)

    return evaluate_sequences_for_entities_fast


def make_fast_continuous_dominance_summarizer(legacy_pipeline: Any) -> Any:
    feature_families = legacy_pipeline.FEATURE_FAMILIES
    factor_claim_status = legacy_pipeline.factor_claim_status
    safe_lift = legacy_pipeline.safe_lift
    safe_odds_ratio = legacy_pipeline.safe_odds_ratio

    def feature_list(panel: pd.DataFrame) -> list[tuple[str, str]]:
        features: list[tuple[str, str]] = []
        for family, columns in feature_families.items():
            for column in columns:
                if column in panel.columns and column not in {
                    "gap_fade_flag",
                    "vwap_reclaim_flag",
                }:
                    features.append((family, column))
        return features

    def valid_values(values: np.ndarray) -> list[str]:
        out = sorted(
            {
                str(value)
                for value in values
                if str(value) and str(value) != "nan"
            }
        )
        return out

    def slice_specs(subset: pd.DataFrame) -> list[tuple[str, str, str, np.ndarray]]:
        size = len(subset)
        all_mask = np.ones(size, dtype=bool)
        specs: list[tuple[str, str, str, np.ndarray]] = [("all", "all", "all", all_mask)]
        split_values = (
            subset["split"].astype(str).to_numpy()
            if "split" in subset.columns
            else np.array([""] * size, dtype=object)
        )
        regime_values = (
            subset["axis_regime_bucket"].astype(str).to_numpy()
            if "axis_regime_bucket" in subset.columns
            else np.array([""] * size, dtype=object)
        )
        duration_values = (
            subset["duration_bucket"].astype(str).to_numpy()
            if "duration_bucket" in subset.columns
            else np.array([""] * size, dtype=object)
        )

        if "split" in subset.columns:
            for split in ["train", "validation", "robustness"]:
                mask = split_values == split
                if bool(mask.any()):
                    specs.append((split, "all", "all", mask))

        regimes = valid_values(regime_values) if "axis_regime_bucket" in subset else []
        for regime in regimes:
            mask = regime_values == regime
            if bool(mask.any()):
                specs.append(("all", regime, "all", mask))

        durations = valid_values(duration_values) if "duration_bucket" in subset else []
        for duration in durations:
            mask = duration_values == duration
            if bool(mask.any()):
                specs.append(("all", "all", duration, mask))

        splits_all = valid_values(split_values) if "split" in subset.columns else []
        if splits_all and regimes:
            for split in splits_all:
                for regime in regimes:
                    mask = (split_values == split) & (regime_values == regime)
                    if bool(mask.any()):
                        specs.append((split, regime, "all", mask))

        if splits_all and durations:
            for split in splits_all:
                for duration in durations:
                    mask = (split_values == split) & (duration_values == duration)
                    if bool(mask.any()):
                        specs.append((split, "all", duration, mask))

        if regimes and durations:
            for regime in regimes:
                for duration in durations:
                    mask = (regime_values == regime) & (duration_values == duration)
                    if bool(mask.any()):
                        specs.append(("all", regime, duration, mask))

        if splits_all and regimes and durations:
            for split in splits_all:
                for regime in regimes:
                    for duration in durations:
                        mask = (
                            (split_values == split)
                            & (regime_values == regime)
                            & (duration_values == duration)
                        )
                        if bool(mask.any()):
                            specs.append((split, regime, duration, mask))
        return specs

    def continuous_row(
        *,
        values: np.ndarray,
        group_values: np.ndarray,
        slice_mask: np.ndarray,
        family: str,
        feature: str,
        shared_axis: str,
        relative_day: int,
        thresholds: dict[str, float],
        split: str,
        regime_bucket: str,
        duration_bucket: str,
    ) -> dict[str, Any]:
        winner_total = int(((group_values == "winner") & slice_mask).sum())
        control_total = int(((group_values == "control") & slice_mask).sum())
        finite = ~np.isnan(values)
        winners = values[(group_values == "winner") & slice_mask & finite]
        controls = values[(group_values == "control") & slice_mask & finite]
        pooled_std = np.nan
        smd = np.nan
        if len(winners) > 1 and len(controls) > 1:
            pooled_std = float(
                np.sqrt(
                    (
                        (len(winners) - 1) * np.var(winners, ddof=1)
                        + (len(controls) - 1) * np.var(controls, ddof=1)
                    )
                    / max(len(winners) + len(controls) - 2, 1)
                )
            )
            if pooled_std > 0:
                smd = (float(np.mean(winners)) - float(np.mean(controls))) / pooled_std
        denominator = winner_total + control_total
        coverage = (len(winners) + len(controls)) / denominator if denominator else 0.0
        return {
            "dominance_id": (
                f"{shared_axis}_{relative_day}_{feature}_{split}_{regime_bucket}_{duration_bucket}"
            ),
            "factor_family": family,
            "feature": feature,
            "shared_axis": shared_axis,
            "anchor_family": "first_ema60_reclaim"
            if shared_axis == "shared_axis_ema60"
            else "",
            "relative_day": relative_day,
            "relative_window": f"{relative_day}",
            "split": split,
            "regime_bucket": regime_bucket,
            "duration_bucket": duration_bucket,
            "winner_count": len(winners),
            "control_count": len(controls),
            "winner_total": winner_total,
            "control_total": control_total,
            "winner_mean": float(np.mean(winners)) if len(winners) else np.nan,
            "control_mean": float(np.mean(controls)) if len(controls) else np.nan,
            "winner_std": float(np.std(winners, ddof=1)) if len(winners) > 1 else np.nan,
            "control_std": float(np.std(controls, ddof=1)) if len(controls) > 1 else np.nan,
            "standardized_mean_difference": smd,
            "winner_rate": np.nan,
            "control_rate": np.nan,
            "lift": np.nan,
            "odds_ratio": np.nan,
            "absolute_rate_difference": np.nan,
            "feature_non_missing_coverage": coverage,
            "claim_status": factor_claim_status(
                effect=smd,
                coverage=coverage,
                winner_count=len(winners),
                control_count=len(controls),
                thresholds=thresholds,
                continuous=True,
            ),
            "missing_reason_policy": "missing reasons retained in aligned panels",
            "multiple_test_family": family,
        }

    def binary_row(
        *,
        values: np.ndarray,
        group_values: np.ndarray,
        slice_mask: np.ndarray,
        family: str,
        feature: str,
        shared_axis: str,
        relative_day: int,
        thresholds: dict[str, float],
        split: str,
        regime_bucket: str,
        duration_bucket: str,
    ) -> dict[str, Any]:
        winner_total = int(((group_values == "winner") & slice_mask).sum())
        control_total = int(((group_values == "control") & slice_mask).sum())
        finite = ~np.isnan(values)
        winners = values[(group_values == "winner") & slice_mask & finite]
        controls = values[(group_values == "control") & slice_mask & finite]
        winner_rate = float(np.mean(winners)) if len(winners) else np.nan
        control_rate = float(np.mean(controls)) if len(controls) else np.nan
        lift = safe_lift(winner_rate, control_rate)
        odds = safe_odds_ratio(
            int(np.sum(winners)) if len(winners) else 0,
            len(winners),
            int(np.sum(controls)) if len(controls) else 0,
            len(controls),
        )
        diff = (
            winner_rate - control_rate
            if not pd.isna(winner_rate) and not pd.isna(control_rate)
            else np.nan
        )
        denominator = winner_total + control_total
        coverage = (len(winners) + len(controls)) / denominator if denominator else 0.0
        effect = max(
            abs(lift) if not pd.isna(lift) else 0.0,
            abs(diff) if not pd.isna(diff) else 0.0,
        )
        return {
            "dominance_id": (
                f"{shared_axis}_{relative_day}_{feature}_{split}_{regime_bucket}_{duration_bucket}"
            ),
            "factor_family": family,
            "feature": feature,
            "shared_axis": shared_axis,
            "anchor_family": "first_ema60_reclaim"
            if shared_axis == "shared_axis_ema60"
            else "",
            "relative_day": relative_day,
            "relative_window": f"{relative_day}",
            "split": split,
            "regime_bucket": regime_bucket,
            "duration_bucket": duration_bucket,
            "winner_count": len(winners),
            "control_count": len(controls),
            "winner_total": winner_total,
            "control_total": control_total,
            "winner_mean": np.nan,
            "control_mean": np.nan,
            "winner_std": np.nan,
            "control_std": np.nan,
            "standardized_mean_difference": np.nan,
            "winner_rate": winner_rate,
            "control_rate": control_rate,
            "lift": lift,
            "odds_ratio": odds,
            "absolute_rate_difference": diff,
            "feature_non_missing_coverage": coverage,
            "claim_status": factor_claim_status(
                effect=effect,
                coverage=coverage,
                winner_count=len(winners),
                control_count=len(controls),
                thresholds=thresholds,
                continuous=False,
                lift=lift,
                rate_diff=diff,
            ),
            "missing_reason_policy": "missing reasons retained in aligned panels",
            "multiple_test_family": family,
        }

    def summarize_continuous_dominance_fast(
        panel: pd.DataFrame,
        *,
        shared_axis: str,
        relative_days: Any,
        thresholds: dict[str, float],
    ) -> pd.DataFrame:
        rows: list[dict[str, Any]] = []
        if panel.empty:
            return pd.DataFrame()
        features = feature_list(panel)
        for relative_day in relative_days:
            mask = (panel["shared_axis"] == shared_axis) & (
                panel["relative_day"] == relative_day
            )
            if not bool(mask.any()):
                continue
            subset_columns = [
                column
                for column in [
                    "group",
                    "split",
                    "axis_regime_bucket",
                    "duration_bucket",
                ]
                if column in panel.columns
            ]
            subset = panel.loc[mask, subset_columns].copy()
            specs = slice_specs(subset)
            group_values = subset["group"].astype(str).to_numpy()
            for family, feature in features:
                values = pd.to_numeric(
                    panel.loc[mask, feature], errors="coerce"
                ).to_numpy(dtype=float)
                for split, regime_bucket, duration, slice_mask in specs:
                    rows.append(
                        continuous_row(
                            values=values,
                            group_values=group_values,
                            slice_mask=slice_mask,
                            family=family,
                            feature=feature,
                            shared_axis=shared_axis,
                            relative_day=relative_day,
                            thresholds=thresholds,
                            split=split,
                            regime_bucket=regime_bucket,
                            duration_bucket=duration,
                        )
                    )
            for binary_feature in ["gap_fade_flag", "vwap_reclaim_flag"]:
                if binary_feature not in panel.columns:
                    continue
                family = (
                    "volume_money_vwap_turnover"
                    if binary_feature == "vwap_reclaim_flag"
                    else "price_structure"
                )
                values = pd.to_numeric(
                    panel.loc[mask, binary_feature], errors="coerce"
                ).to_numpy(dtype=float)
                for split, regime_bucket, duration, slice_mask in specs:
                    rows.append(
                        binary_row(
                            values=values,
                            group_values=group_values,
                            slice_mask=slice_mask,
                            family=family,
                            feature=binary_feature,
                            shared_axis=shared_axis,
                            relative_day=relative_day,
                            thresholds=thresholds,
                            split=split,
                            regime_bucket=regime_bucket,
                            duration_bucket=duration,
                        )
                    )
        return pd.DataFrame(rows)

    return summarize_continuous_dominance_fast


def normalize_date_series(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, errors="coerce").dt.strftime("%Y-%m-%d")


def split_for_date_text(date_text: str, split_config: dict[str, str]) -> str:
    if split_config["train_start"] <= date_text <= split_config["train_end"]:
        return "train"
    if split_config["validation_start"] <= date_text <= split_config["validation_end"]:
        return "validation"
    latest = split_config["latest_label_complete_low_date"]
    if split_config["robustness_start"] <= date_text <= latest:
        return "robustness"
    return "outside_split"


def latest_complete_low_date_from_benchmark(
    benchmark_daily: pd.DataFrame, horizon_sessions: int
) -> str:
    sessions = (
        benchmark_daily.loc[benchmark_daily["index_alias"] == "all_a", "trade_date"]
        .dropna()
        .map(lambda value: pd.Timestamp(value).strftime("%Y-%m-%d"))
        .drop_duplicates()
        .sort_values()
        .tolist()
    )
    if len(sessions) <= horizon_sessions:
        raise ValueError("Benchmark calendar shorter than forward horizon")
    return sessions[-horizon_sessions - 1]


def load_topn_denominator(
    config: dict[str, Any],
    project_root: Path,
    *,
    topn_status: TopNInputStatus,
) -> pd.DataFrame:
    path = topic_path(project_root, config["paths"]["executable_universe_csv"])
    usecols = [
        "usable_trade_date",
        "instrument",
        "board_bucket",
        "source_membership_date",
        "membership_available_time",
        "history_observed_sessions_before_usable_date",
        "history_ready_240d_flag",
    ]
    frame = pd.read_csv(path, usecols=usecols)
    frame["usable_trade_date"] = normalize_date_series(frame["usable_trade_date"])
    frame["source_membership_date"] = normalize_date_series(
        frame["source_membership_date"]
    )
    frame = frame.dropna(subset=["usable_trade_date", "source_membership_date"])
    expected_available = frame["source_membership_date"] + " close"
    frame["pit_clock_valid"] = (
        frame["source_membership_date"] < frame["usable_trade_date"]
    ) & (frame["membership_available_time"].astype(str) == expected_available)
    if not bool(frame["pit_clock_valid"].all()):
        bad = int((~frame["pit_clock_valid"]).sum())
        raise TopNReverseLifecycleBlocked(
            "topn_reverse_lifecycle_topn_universe_blocked",
            f"top-N executable has {bad} PIT clock violations",
        )
    observed = pd.to_numeric(
        frame["history_observed_sessions_before_usable_date"], errors="coerce"
    )
    frame["upstream_history_ready_240d_flag"] = frame[
        "history_ready_240d_flag"
    ].astype(bool)
    frame["history_ready_250d_flag"] = observed >= int(
        config["episode_extraction"]["prior_lookback_sessions"]
    )
    frame["universe_precision_status"] = topn_status.universe_precision_status
    frame["active_source_gap_count"] = topn_status.active_source_gap_count
    return frame


def add_denominator_context(
    denominator: pd.DataFrame,
    config: dict[str, Any],
    project_root: Path,
    legacy_runner: Any,
) -> tuple[pd.DataFrame, dict[str, str]]:
    benchmark = pd.read_csv(topic_path(project_root, config["paths"]["benchmark_daily_csv"]))
    latest_complete = latest_complete_low_date_from_benchmark(
        benchmark, int(config["episode_extraction"]["forward_horizon_sessions"])
    )
    split_cfg = {**config["splits"], "latest_label_complete_low_date": latest_complete}
    out = denominator.copy()
    out["label_complete_120d_flag"] = out["usable_trade_date"] <= latest_complete
    out["split"] = out["usable_trade_date"].map(
        lambda value: split_for_date_text(str(value), split_cfg)
    )
    out["year"] = pd.to_datetime(out["usable_trade_date"], errors="coerce").dt.year

    market_features = legacy_runner.compute_market_features(benchmark)
    regime = market_features.loc[
        market_features["benchmark_alias"] == "all_a",
        ["trade_date", "market_regime_bucket"],
    ].drop_duplicates()
    out = out.merge(
        regime,
        left_on="usable_trade_date",
        right_on="trade_date",
        how="left",
    ).drop(columns=["trade_date"])
    out["market_regime_bucket"] = out["market_regime_bucket"].fillna(
        "missing_insufficient_lookback"
    )
    out["evaluated_flag"] = (
        out["pit_clock_valid"]
        & out["history_ready_250d_flag"]
        & out["label_complete_120d_flag"]
        & (out["split"] != "outside_split")
    )
    return out, split_cfg


def denominator_summary(frame: pd.DataFrame, group_cols: list[str]) -> pd.DataFrame:
    raw = frame.groupby(group_cols, dropna=False).size().reset_index(
        name="raw_topn_instrument_days"
    )
    evaluated = (
        frame.loc[frame["evaluated_flag"]]
        .groupby(group_cols, dropna=False)
        .size()
        .reset_index(name="evaluated_instrument_days")
    )
    out = raw.merge(evaluated, on=group_cols, how="left")
    out["evaluated_instrument_days"] = (
        out["evaluated_instrument_days"].fillna(0).astype(int)
    )
    out["instrument_days"] = out["evaluated_instrument_days"]
    out["universe_years_252"] = out["instrument_days"] / 252.0
    return out


def add_episode_rates(denom: pd.DataFrame, episodes: pd.DataFrame, group_cols: list[str]) -> pd.DataFrame:
    if episodes.empty:
        counts = pd.DataFrame(columns=group_cols + ["episode_count"])
    else:
        counts = episodes.groupby(group_cols, dropna=False).size().reset_index(
            name="episode_count"
        )
    out = denom.merge(counts, on=group_cols, how="left")
    out["episode_count"] = out["episode_count"].fillna(0).astype(int)
    out["episodes_per_100_universe_years"] = np.where(
        out["universe_years_252"] > 0,
        out["episode_count"] / out["universe_years_252"] * 100.0,
        np.nan,
    )
    return out


def build_denominator_outputs(
    denominator: pd.DataFrame, winners: pd.DataFrame
) -> dict[str, pd.DataFrame]:
    evaluated = denominator.loc[denominator["evaluated_flag"]].copy()
    winners = winners.copy()
    if "year" not in winners.columns and "episode_low_date" in winners.columns:
        winners["year"] = pd.to_datetime(
            winners["episode_low_date"], errors="coerce"
        ).dt.year
    all_summary = pd.DataFrame(
        [
            {
                "scope": "all",
                "raw_topn_instrument_days": int(len(denominator)),
                "evaluated_instrument_days": int(len(evaluated)),
                "instrument_days": int(len(evaluated)),
                "universe_years_252": len(evaluated) / 252.0,
                "episode_count": int(len(winners)),
                "episodes_per_100_universe_years": (
                    len(winners) / (len(evaluated) / 252.0) * 100.0
                    if len(evaluated)
                    else np.nan
                ),
            }
        ]
    )

    yearly_denom = denominator_summary(denominator, ["year"])
    split_denom = denominator_summary(denominator, ["split"])
    board_denom = denominator_summary(denominator, ["board_bucket"])
    regime_denom = denominator_summary(denominator, ["market_regime_bucket"])

    yearly_rate = add_episode_rates(yearly_denom, winners, ["year"])
    split_rate = add_episode_rates(split_denom, winners, ["split"])
    board_rate = add_episode_rates(board_denom, winners, ["board_bucket"])
    regime_rate = add_episode_rates(regime_denom, winners, ["market_regime_bucket"])

    rows = []
    for scope, table in [
        ("all", all_summary),
        ("year", yearly_rate),
        ("split", split_rate),
        ("board_bucket", board_rate),
        ("market_regime_bucket", regime_rate),
    ]:
        table = table.copy()
        table["scope"] = scope
        for column in [
            "year",
            "split",
            "board_bucket",
            "duration_bucket",
            "market_regime_bucket",
        ]:
            if column not in table:
                table[column] = "all"
        table["denominator_scope"] = "evaluated_topn_instrument_days"
        rows.append(table)

    if not winners.empty and "duration_bucket" in winners:
        duration = winners.groupby("duration_bucket", dropna=False).size().reset_index(
            name="episode_count"
        )
        duration["scope"] = "duration_bucket"
        duration["raw_topn_instrument_days"] = np.nan
        duration["evaluated_instrument_days"] = np.nan
        duration["instrument_days"] = np.nan
        duration["universe_years_252"] = np.nan
        duration["episodes_per_100_universe_years"] = np.nan
        duration["denominator_scope"] = "not_applicable_duration_episode_attribute"
        for column in ["year", "split", "board_bucket", "market_regime_bucket"]:
            duration[column] = "all"
        rows.append(duration)

    episode_summary = pd.concat(rows, ignore_index=True, sort=False)
    ordered_columns = [
        "scope",
        "year",
        "split",
        "board_bucket",
        "duration_bucket",
        "market_regime_bucket",
        "episode_count",
        "raw_topn_instrument_days",
        "evaluated_instrument_days",
        "instrument_days",
        "universe_years_252",
        "episodes_per_100_universe_years",
        "denominator_scope",
    ]
    episode_summary = episode_summary[ordered_columns]

    return {
        "topn_denominator_summary": all_summary,
        "topn_yearly_denominator_summary": yearly_denom,
        "topn_split_denominator_summary": split_denom,
        "topn_episode_count_summary": episode_summary,
        "topn_episode_rate_by_year": yearly_rate,
        "topn_episode_rate_by_split": split_rate,
        "topn_episode_rate_by_board": board_rate,
        "topn_episode_rate_by_regime": regime_rate,
    }


def build_rule_invariant_audit(
    config: dict[str, Any],
    upstream_02_config: dict[str, Any],
    topn_status: TopNInputStatus,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []

    def add(
        family: str,
        name: str,
        value_02: Any,
        value_06: Any,
        *,
        allowed_difference: bool = False,
        blocking: bool = True,
        notes: str = "",
    ) -> None:
        status = "allowed_difference" if allowed_difference else "pass"
        if not allowed_difference and value_02 != value_06:
            status = "fail"
        rows.append(
            {
                "rule_family": family,
                "rule_name": name,
                "02_value": json.dumps(value_02, sort_keys=True, default=str),
                "06_value": json.dumps(value_06, sort_keys=True, default=str),
                "allowed_difference": bool(allowed_difference),
                "status": status,
                "blocking": bool(blocking),
                "notes": notes,
            }
        )

    for section in ["episode_extraction", "splits", "alignment", "matching"]:
        add(section, section, upstream_02_config.get(section), config.get(section))
    add(
        "dominance",
        "sample_and_claim_gates",
        upstream_02_config.get("dominance"),
        {
            key: value
            for key, value in config.get("dominance", {}).items()
            if key in upstream_02_config.get("dominance", {})
        },
    )
    add("industry", "industry_status", upstream_02_config.get("industry"), config.get("industry"))
    add(
        "universe",
        "target_universe_input",
        upstream_02_config.get("paths", {}).get("executable_universe_csv"),
        config.get("paths", {}).get("executable_universe_csv"),
        allowed_difference=True,
        notes="Controlled 06 universe replacement.",
    )
    add(
        "universe",
        "universe_precision_status",
        "exact fixed-cap universe from 02 contract",
        topn_status.universe_precision_status,
        allowed_difference=True,
        blocking=False,
        notes="06-specific exact/proxy caveat.",
    )
    return pd.DataFrame(rows)


def invariant_audit_passed(audit: pd.DataFrame) -> bool:
    if audit.empty:
        return False
    blocking_fail = (audit["status"] == "fail") & audit["blocking"].astype(bool)
    return not bool(blocking_fail.any())


def rename_local_outputs(project_root: Path, config: dict[str, Any]) -> dict[str, Path]:
    outputs = config["outputs"]
    base = topic_path(project_root, "experiments/pending/06_rerun_02_reverse_lifecycle_on_topn_universe_v0/outputs")
    paths: dict[str, Path] = {}
    for source_rel, dest_rel in LOCAL_OUTPUT_RENAMES.items():
        source = base / source_rel
        dest = base / dest_rel
        if source.exists():
            dest.parent.mkdir(parents=True, exist_ok=True)
            if dest.exists():
                dest.unlink()
            source.rename(dest)
        if dest.exists():
            key = dest_rel.replace("/", ".").rsplit(".", 1)[0]
            paths[key] = dest
    # Keep the 02 replay report local-only; the 06 report is written separately.
    replay_report = topic_path(project_root, outputs["local_cache_dir"]) / (
        "02_replay_reports/reverse_lifecycle_profile_report.md"
    )
    if replay_report.exists():
        paths["local_cache.02_replay_report"] = replay_report
    return paths


def build_baseline_comparison(
    config: dict[str, Any],
    project_root: Path,
    topn_winners: pd.DataFrame,
    topn_match_stats: pd.DataFrame,
    topn_denominator_summary: pd.DataFrame,
    topn_decision: str,
) -> pd.DataFrame:
    paths = config["upstream_02_publishable_tables"]
    manifest = load_json(topic_path(project_root, config["paths"]["upstream_02_run_manifest_json"]))
    fixed_winners = pd.read_csv(topic_path(project_root, paths["big_winner_episode_reference_summary"]))
    fixed_match = pd.read_csv(topic_path(project_root, paths["winner_vs_matched_control_stats"]))

    topn_all = topn_denominator_summary.iloc[0].to_dict()
    fixed_gate = manifest.get("gate_summary", {})
    fixed_low_match = fixed_match.loc[
        (fixed_match["match_axis"] == "shared_axis_low")
        & (fixed_match["split"] == "all")
    ]
    topn_low_match = topn_match_stats.loc[
        (topn_match_stats["match_axis"] == "shared_axis_low")
        & (topn_match_stats["split"] == "all")
    ] if not topn_match_stats.empty else pd.DataFrame()

    def first_value(frame: pd.DataFrame, column: str) -> Any:
        if frame.empty or column not in frame:
            return np.nan
        return frame[column].iloc[0]

    rows = [
        {
            "metric": "decision",
            "fixed_cap_02": manifest.get("decision", ""),
            "topn_06": topn_decision,
            "delta": "",
            "notes": "Decision comparison only; 06 decision is based on top-N denominator.",
        },
        {
            "metric": "target_episode_count",
            "fixed_cap_02": len(fixed_winners),
            "topn_06": len(topn_winners),
            "delta": len(topn_winners) - len(fixed_winners),
            "notes": "",
        },
        {
            "metric": "universe_years_252",
            "fixed_cap_02": "",
            "topn_06": topn_all.get("universe_years_252", np.nan),
            "delta": "",
            "notes": "02 did not publish an executable universe-year denominator.",
        },
        {
            "metric": "episodes_per_100_universe_years",
            "fixed_cap_02": "",
            "topn_06": topn_all.get("episodes_per_100_universe_years", np.nan),
            "delta": "",
            "notes": "Top-N rate uses evaluated available-source Top-N denominator.",
        },
        {
            "metric": "train_winner_episodes",
            "fixed_cap_02": fixed_gate.get("train_winner_episodes", np.nan),
            "topn_06": int((topn_winners.get("split", pd.Series(dtype=str)) == "train").sum())
            if not topn_winners.empty
            else 0,
            "delta": "",
            "notes": "",
        },
        {
            "metric": "validation_winner_episodes",
            "fixed_cap_02": fixed_gate.get("validation_winner_episodes", np.nan),
            "topn_06": int(
                (topn_winners.get("split", pd.Series(dtype=str)) == "validation").sum()
            )
            if not topn_winners.empty
            else 0,
            "delta": "",
            "notes": "",
        },
        {
            "metric": "robustness_winner_episodes",
            "fixed_cap_02": fixed_gate.get("robustness_winner_episodes", np.nan),
            "topn_06": int(
                (topn_winners.get("split", pd.Series(dtype=str)) == "robustness").sum()
            )
            if not topn_winners.empty
            else 0,
            "delta": "",
            "notes": "",
        },
        {
            "metric": "low_match_coverage",
            "fixed_cap_02": first_value(fixed_low_match, "match_coverage"),
            "topn_06": first_value(topn_low_match, "match_coverage"),
            "delta": "",
            "notes": "",
        },
        {
            "metric": "average_controls_per_winner",
            "fixed_cap_02": first_value(fixed_low_match, "average_controls_per_winner"),
            "topn_06": first_value(topn_low_match, "average_controls_per_winner"),
            "delta": "",
            "notes": "",
        },
    ]
    return pd.DataFrame(rows)


def collect_output_paths(config: dict[str, Any], project_root: Path) -> dict[str, Path]:
    outputs = config["outputs"]
    table_dir = topic_path(project_root, outputs["publishable_tables_dir"])
    report_dir = topic_path(project_root, outputs["publishable_reports_dir"])
    manifest_dir = topic_path(project_root, outputs["manifests_dir"])
    paths: dict[str, Path] = {}
    for path in sorted(table_dir.glob("*.csv")):
        paths[f"publishable.tables.{path.stem}"] = path
    for path in sorted(report_dir.glob("*.md")):
        paths[f"publishable.reports.{path.stem}"] = path
    paths.update(rename_local_outputs(project_root, config))
    return paths


def write_topn_manifest(
    *,
    config: dict[str, Any],
    config_path: Path,
    project_root: Path,
    topn_status: TopNInputStatus,
    topn_decision: str,
    semantic_02_decision: str,
    gate_summary: dict[str, Any],
    split_config: dict[str, str],
    output_paths: dict[str, Path],
) -> Path:
    manifest_path = topic_path(project_root, config["outputs"]["manifests_dir"]) / "run_manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    input_paths = {
        "stock_daily_csv_dir": topic_path(project_root, config["paths"]["stock_daily_csv_dir"]),
        "benchmark_daily_csv": topic_path(project_root, config["paths"]["benchmark_daily_csv"]),
        "executable_universe_csv": topic_path(project_root, config["paths"]["executable_universe_csv"]),
        "membership_universe_csv": topic_path(project_root, config["paths"]["membership_universe_csv"]),
        "data_prepare_run_manifest_json": topic_path(project_root, config["paths"]["data_prepare_run_manifest_json"]),
        "data_prepare_source_coverage_audit_csv": topic_path(project_root, config["paths"]["data_prepare_source_coverage_audit_csv"]),
        "upstream_02_run_manifest_json": topic_path(project_root, config["paths"]["upstream_02_run_manifest_json"]),
        "upstream_05_run_manifest_json": topic_path(project_root, config["paths"]["upstream_05_run_manifest_json"]),
        "upstream_05_data_source_coverage_audit_csv": topic_path(project_root, config["paths"]["upstream_05_data_source_coverage_audit_csv"]),
    }
    input_hashes = {
        name: file_sha256(path)
        for name, path in input_paths.items()
        if path.is_file()
    }
    output_hashes = {
        name: file_sha256(path)
        for name, path in output_paths.items()
        if path.is_file()
    }
    upstream_02_manifest = load_json(input_paths["upstream_02_run_manifest_json"])
    denominator = pd.read_csv(
        topic_path(project_root, config["outputs"]["publishable_tables_dir"])
        / "topn_denominator_summary.csv"
    )
    top_row = denominator.iloc[0].to_dict() if not denominator.empty else {}
    manifest = {
        "experiment_name": config["experiment"]["name"],
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_git_revision": git_revision(project_root),
        "config_path": str(config_path),
        "config_hash": stable_hash(config),
        "config_file_hash": file_sha256(config_path),
        "input_paths": {name: str(path) for name, path in input_paths.items()},
        "input_hashes": input_hashes,
        "output_paths": {name: str(path) for name, path in output_paths.items()},
        "output_hashes": output_hashes,
        "upstream_01_manifest_hash": input_hashes.get("data_prepare_run_manifest_json"),
        "upstream_02_manifest_hash": input_hashes.get("upstream_02_run_manifest_json"),
        "upstream_05_manifest_hash": topn_status.upstream_05_manifest_hash,
        "upstream_05_data_source_coverage_audit_hash": topn_status.upstream_05_data_source_coverage_audit_hash,
        "upstream_05_decision": topn_status.upstream_05_decision,
        "topn_universe_input_accepted": topn_status.topn_universe_input_accepted,
        "exact_topn_supported": topn_status.exact_topn_supported,
        "universe_precision_status": topn_status.universe_precision_status,
        "topn_candidate_gap_accepted": topn_status.topn_candidate_gap_accepted,
        "active_source_gap_count": topn_status.active_source_gap_count,
        "source_gap_count": topn_status.source_gap_count,
        "missing_active_source_instrument_count": topn_status.missing_active_source_instrument_count,
        "missing_active_source_audit_count_reconciled": topn_status.missing_active_source_audit_count_reconciled,
        "resolved_start_trading_date": split_config.get("train_start"),
        "resolved_end_trading_date": split_config.get("latest_label_complete_low_date"),
        "effective_first_eligible_low_date": gate_summary.get("effective_first_eligible_low_date", ""),
        "latest_label_complete_low_date": split_config.get("latest_label_complete_low_date"),
        "episode_definition_version": "02_v0_mfe_120_ge_50pct",
        "universe_definition_version": "pit_topn_400_100_available_source_proxy_v0",
        "inherited_02_config_hash": upstream_02_manifest.get("config_hash"),
        "inherited_02_rule_invariant_status": gate_summary.get("inherited_02_rule_invariant_status"),
        "industry_data_status": config.get("industry", {}).get("status", "unavailable"),
        "target_episode_count": gate_summary.get("total_winner_episodes"),
        "raw_topn_instrument_days": int(top_row.get("raw_topn_instrument_days", 0) or 0),
        "evaluated_instrument_days": int(top_row.get("evaluated_instrument_days", 0) or 0),
        "instrument_days": int(top_row.get("instrument_days", 0) or 0),
        "universe_years_252": float(top_row.get("universe_years_252", np.nan)),
        "episodes_per_100_universe_years": float(
            top_row.get("episodes_per_100_universe_years", np.nan)
        ),
        "semantic_02_decision": semantic_02_decision,
        "topn_decision_mapping_version": "prefix_02_semantic_decision_v1",
        "decision": topn_decision,
        "gate_summary": gate_summary,
    }
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    return manifest_path


def write_report(
    *,
    config: dict[str, Any],
    project_root: Path,
    topn_status: TopNInputStatus,
    decision: str,
    semantic_02_decision: str,
    gate_summary: dict[str, Any],
    denominator_summary: pd.DataFrame,
    episode_summary: pd.DataFrame,
    baseline_comparison: pd.DataFrame,
    invariant_audit: pd.DataFrame,
) -> Path:
    report_dir = topic_path(project_root, config["outputs"]["publishable_reports_dir"])
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / "topn_reverse_lifecycle_profile_report.md"
    lines = [
        "# PIT Top-N Reverse Lifecycle Profile Report",
        "",
        f"Final decision: `{decision}`",
        f"Semantic 02 replay decision: `{semantic_02_decision}`",
        f"Universe precision status: `{topn_status.universe_precision_status}`",
        "",
        "This run replays the 02 reverse lifecycle contract on the 05 PIT Top-N 400/100 universe/proxy. The controlled scientific difference is the target universe.",
        "",
        "## 05 Universe Input",
        "",
        f"- upstream 05 decision: `{topn_status.upstream_05_decision}`",
        f"- active source gaps accepted: `{topn_status.active_source_gap_count}`",
        f"- source gaps total: `{topn_status.source_gap_count}`",
        f"- missing active source audit reconciled: `{topn_status.missing_active_source_audit_count_reconciled}`",
        "",
        "## Denominator",
        "",
        dataframe_to_markdown(denominator_summary),
        "",
        "## Episode Rate Summary",
        "",
        dataframe_to_markdown(episode_summary.head(20)),
        "",
        "## Fixed-Cap 02 Baseline Comparison",
        "",
        dataframe_to_markdown(baseline_comparison),
        "",
        "## 02 Rule Invariant Replay",
        "",
        dataframe_to_markdown(invariant_audit),
        "",
        "## Gate Summary",
        "",
    ]
    for key, value in gate_summary.items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(
        [
            "",
            "## Downstream 04 Handoff",
            "",
            "04 must not rerun until this manifest is frozen. If this run uses `available_source_topn_candidate_gap`, downstream recall denominators must carry the same available-source proxy caveat.",
            "",
        ]
    )
    report_path.write_text("\n".join(lines), encoding="utf-8")
    return report_path


def dataframe_to_markdown(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "No rows."
    display = frame.copy()
    if len(display) > 30:
        display = display.head(30)
    try:
        return display.to_markdown(index=False)
    except Exception:
        return display.to_csv(index=False)


def topn_decision_from_semantic(semantic_decision: str, invariant_ok: bool) -> str:
    if not invariant_ok:
        return "topn_reverse_lifecycle_invariant_replay_blocked"
    return DECISION_MAP.get(semantic_decision, "topn_reverse_lifecycle_diagnostic_only")
