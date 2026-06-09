from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from afml_big_winner.config import load_yaml, stable_hash
from afml_big_winner.manifest import file_sha256, git_revision

from pipeline import (
    ExtractionParams,
    MatchConfig,
    MISSING_EVENT_ABSENT,
    NOT_MISSING,
    SEQUENCE_DEFINITIONS,
    SplitConfig,
    add_market_features,
    assign_match_buckets,
    build_aligned_panel,
    build_control_pool_for_instrument,
    build_winner_reference_for_instrument,
    compute_market_features,
    compute_path_tolerance_features,
    compute_stock_features,
    date_str,
    evaluate_sequences_for_entities,
    extract_candidate_lows,
    false_repair_flag,
    false_repair_metrics,
    iter_dominance_slices,
    latest_complete_low_date,
    match_controls,
    safe_lift,
    sequence_family_test_counts,
    summarize_continuous_dominance,
    summarize_market_regime_dominance,
    summarize_sequence_dominance,
    winner_only_stage_profile,
    write_dataframe,
)


EXPERIMENT_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = Path(__file__).resolve().parents[4]


PUBLISHABLE_TABLES = {
    "big_winner_episode_reference_summary": "big_winner_episode_reference_summary.csv",
    "frozen_anchor_profile_summary": "frozen_anchor_profile_summary.csv",
    "winner_vs_matched_control_stats": "winner_vs_matched_control_stats.csv",
    "near_winner_comparison_stats": "near_winner_comparison_stats.csv",
    "false_repair_comparison_stats": "false_repair_comparison_stats.csv",
    "shared_axis_market_regime_dominance": "shared_axis_market_regime_dominance.csv",
    "shared_axis_factor_dominance": "shared_axis_factor_dominance.csv",
    "shared_axis_sequence_dominance": "shared_axis_sequence_dominance.csv",
    "sequence_family_test_count": "sequence_family_test_count.csv",
    "sequence_examples_descriptive": "sequence_examples_descriptive.csv",
    "winner_only_retrospective_stage_profile": "winner_only_retrospective_stage_profile.csv",
    "unconditional_validation_readout": "unconditional_validation_readout.csv",
    "regime_conditioned_validation_readout": "regime_conditioned_validation_readout.csv",
    "validation_opportunity_audit": "validation_opportunity_audit.csv",
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run reverse lifecycle profile v0.")
    parser.add_argument(
        "--config",
        default=str(EXPERIMENT_DIR / "config.yaml"),
        help="Experiment config path.",
    )
    parser.add_argument(
        "--max-instruments",
        type=int,
        default=None,
        help="Optional smoke-run cap. Full runs should omit this.",
    )
    args = parser.parse_args(argv)

    config_path = Path(args.config)
    config = load_yaml(config_path)
    result = run_pipeline(config, config_path=config_path, max_instruments=args.max_instruments)
    print(f"decision={result['decision']}")
    print(f"manifest={result['manifest_path']}")
    print(f"report={result['report_path']}")
    return 0


def run_pipeline(
    config: dict[str, Any], *, config_path: Path, max_instruments: int | None = None
) -> dict[str, Any]:
    paths = config["paths"]
    outputs = config["outputs"]
    params = ExtractionParams(**config["episode_extraction"])

    table_dir = PROJECT_ROOT / outputs["publishable_tables_dir"]
    report_dir = PROJECT_ROOT / outputs["publishable_reports_dir"]
    local_cache_dir = PROJECT_ROOT / outputs["local_cache_dir"]
    large_raw_dir = PROJECT_ROOT / outputs["large_raw_dir"]
    manifest_dir = PROJECT_ROOT / outputs["manifests_dir"]
    for directory in [table_dir, report_dir, local_cache_dir, large_raw_dir, manifest_dir]:
        directory.mkdir(parents=True, exist_ok=True)

    input_paths = {
        "stock_daily_csv_dir": PROJECT_ROOT / paths["stock_daily_csv_dir"],
        "benchmark_daily_csv": PROJECT_ROOT / paths["benchmark_daily_csv"],
        "executable_universe_csv": PROJECT_ROOT / paths["executable_universe_csv"],
        "data_cache_manifest_csv": PROJECT_ROOT / paths["data_cache_manifest_csv"],
        "data_prepare_run_manifest_json": PROJECT_ROOT / paths["data_prepare_run_manifest_json"],
        "data_prepare_source_coverage_audit_csv": PROJECT_ROOT
        / paths["data_prepare_source_coverage_audit_csv"],
    }
    validate_required_inputs(input_paths)
    source_coverage_audit = pd.read_csv(input_paths["data_prepare_source_coverage_audit_csv"])
    vwap_source_policy = resolve_vwap_source_policy(source_coverage_audit)

    benchmark_daily = pd.read_csv(input_paths["benchmark_daily_csv"])
    market_features = compute_market_features(benchmark_daily)
    calendar = (
        benchmark_daily.loc[benchmark_daily["index_alias"] == "all_a", "trade_date"]
        .dropna()
        .map(date_str)
        .drop_duplicates()
        .sort_values()
        .tolist()
    )
    latest_complete = latest_complete_low_date(calendar, params.forward_horizon_sessions)
    split_config = SplitConfig(
        latest_label_complete_low_date=latest_complete,
        **config["splits"],
    )

    universe = pd.read_csv(
        input_paths["executable_universe_csv"],
        usecols=[
            "instrument",
            "usable_trade_date",
            "board_bucket",
            "total_market_cap_cny",
        ],
    )
    universe["usable_trade_date"] = pd.to_datetime(
        universe["usable_trade_date"], errors="coerce"
    ).dt.strftime("%Y-%m-%d")
    universe = universe.dropna(subset=["instrument", "usable_trade_date"])
    instruments = sorted(universe["instrument"].unique())
    if max_instruments is not None:
        instruments = instruments[:max_instruments]

    daily_by_instrument: dict[str, pd.DataFrame] = {}
    winner_parts: list[pd.DataFrame] = []
    control_parts: list[pd.DataFrame] = []
    cluster_audit_parts: list[pd.DataFrame] = []
    extraction_audit_rows: list[dict[str, Any]] = []

    qlib_dir = input_paths["stock_daily_csv_dir"]
    grouped_universe = {
        instrument: group.sort_values("usable_trade_date").reset_index(drop=True)
        for instrument, group in universe.groupby("instrument", sort=False)
    }

    for index, instrument in enumerate(instruments, start=1):
        if index == 1 or index % 50 == 0 or index == len(instruments):
            print(f"processing {index}/{len(instruments)} {instrument}", flush=True)
        daily_path = qlib_dir / f"{instrument}.csv"
        if not daily_path.is_file():
            raise FileNotFoundError(f"Missing stock daily CSV for {instrument}: {daily_path}")
        daily = pd.read_csv(daily_path)
        daily["instrument"] = instrument
        membership = grouped_universe[instrument]
        board_bucket = most_common_text(membership["board_bucket"])
        features = compute_stock_features(
            daily,
            vwap_source_units_compatible=bool(vwap_source_policy["compatible"]),
        )
        features = add_market_features(features, market_features, board_bucket)
        daily_by_instrument[instrument] = features

        membership_dates = set(membership["usable_trade_date"].astype(str))
        candidates = extract_candidate_lows(
            features, membership_dates=membership_dates, params=params
        )
        extraction_audit_rows.append(
            instrument_extraction_audit(
                instrument=instrument,
                features=features,
                membership_dates=membership_dates,
                candidates=candidates,
                params=params,
                split_config=split_config,
            )
        )
        if candidates.empty:
            continue
        winners, cluster_audit = build_winner_reference_for_instrument(
            instrument,
            features,
            candidates,
            membership,
            params=params,
            split_config=split_config,
        )
        controls = build_control_pool_for_instrument(
            instrument,
            features,
            candidates,
            membership,
            params=params,
            split_config=split_config,
        )
        if not winners.empty:
            winner_parts.append(winners)
        if not controls.empty:
            control_parts.append(controls)
        if not cluster_audit.empty:
            cluster_audit_parts.append(cluster_audit)

    winners = concat_or_empty(winner_parts)
    controls = concat_or_empty(control_parts)
    cluster_audit = concat_or_empty(cluster_audit_parts)
    extraction_audit = pd.DataFrame(extraction_audit_rows)

    winners = winners.loc[winners["split"] != "outside_split"].reset_index(drop=True)
    controls = controls.loc[controls["split"] != "outside_split"].reset_index(drop=True)
    if not winners.empty and not controls.empty:
        winners, controls, bucket_values = assign_match_buckets(winners, controls)
    else:
        bucket_values = {}

    match_config = MatchConfig(
        max_controls_per_winner=int(config["matching"]["max_controls_per_winner"]),
        same_week_required=bool(config["matching"]["same_week_required"]),
        match_fields=tuple(config["matching"]["match_fields"]),
    )
    low_matches, low_match_audit = match_controls(
        winners,
        controls,
        winner_id_col="episode_id",
        control_id_col="control_candidate_id",
        winner_date_col="episode_low_date",
        control_date_col="candidate_low_date",
        match_axis="shared_axis_low",
        config=match_config,
    )
    anchor_winners = winners.loc[
        winners["first_ema60_reclaim_missing_reason"] == NOT_MISSING
    ].copy()
    anchor_controls = controls.loc[
        controls["first_ema60_reclaim_missing_reason"] == NOT_MISSING
    ].copy()
    anchor_matches, anchor_match_audit = match_controls(
        anchor_winners,
        anchor_controls,
        winner_id_col="episode_id",
        control_id_col="control_candidate_id",
        winner_date_col="first_ema60_reclaim_date",
        control_date_col="first_ema60_reclaim_date",
        match_axis="shared_axis_ema60",
        config=match_config,
    )

    winners = attach_match_counts(winners, low_match_audit, anchor_match_audit)
    low_winner_entities, low_control_entities = build_matched_entities(
        winners=winners,
        controls=controls,
        matches=low_matches,
        match_axis="shared_axis_low",
        daily_by_instrument=daily_by_instrument,
    )
    anchor_winner_entities, anchor_control_entities = build_matched_entities(
        winners=winners,
        controls=controls,
        matches=anchor_matches,
        match_axis="shared_axis_ema60",
        daily_by_instrument=daily_by_instrument,
    )

    low_entities = pd.concat([low_winner_entities, low_control_entities], ignore_index=True)
    anchor_entities = pd.concat(
        [anchor_winner_entities, anchor_control_entities], ignore_index=True
    )
    low_panel = build_aligned_panel(
        low_entities,
        daily_by_instrument,
        entity_id_col="entity_id",
        axis_date_col="axis_date",
        group_col="group",
        shared_axis="shared_axis_low",
        relative_start=int(config["alignment"]["low_panel_start_relative_day"]),
        relative_end=int(config["alignment"]["low_panel_end_relative_day"]),
    )
    anchor_panel = build_aligned_panel(
        anchor_entities,
        daily_by_instrument,
        entity_id_col="entity_id",
        axis_date_col="axis_date",
        group_col="group",
        shared_axis="shared_axis_ema60",
        relative_start=int(config["alignment"]["anchor_panel_start_relative_day"]),
        relative_end=int(config["alignment"]["anchor_panel_end_relative_day"]),
    )
    aligned_panel = pd.concat([low_panel, anchor_panel], ignore_index=True)

    thresholds = dominance_thresholds(config)
    low_factor_dominance = summarize_continuous_dominance(
        aligned_panel,
        shared_axis="shared_axis_low",
        relative_days=config["alignment"]["factor_relative_days"],
        thresholds=thresholds,
    )
    anchor_factor_dominance = summarize_continuous_dominance(
        aligned_panel,
        shared_axis="shared_axis_ema60",
        relative_days=config["alignment"]["anchor_factor_relative_days"],
        thresholds=thresholds,
    )
    path_dominance = summarize_path_dominance(
        low_entities, daily_by_instrument, thresholds=thresholds
    )
    factor_dominance = pd.concat(
        [low_factor_dominance, anchor_factor_dominance, path_dominance],
        ignore_index=True,
    )
    market_regime_dominance = summarize_market_regime_dominance(aligned_panel)

    sequence_entities = low_entities.copy()
    sequence_panel = evaluate_sequences_for_entities(
        sequence_entities,
        daily_by_instrument,
        entity_id_col="entity_id",
        axis_date_col="axis_date",
        group_col="group",
        horizon_sessions=params.forward_horizon_sessions,
    )
    sequence_dominance = summarize_sequence_dominance(
        sequence_panel, thresholds=thresholds
    )
    sequence_counts = sequence_family_test_counts()
    sequence_examples = build_sequence_examples(sequence_panel)
    stage_profile = winner_only_stage_profile(winners, daily_by_instrument, params)

    matched_control_panel = build_match_panel(low_matches, anchor_matches, controls)
    anchor_summary = build_anchor_summary(winners, controls, low_control_entities)
    matched_control_stats = build_matched_control_stats(
        winners=winners,
        low_matches=low_matches,
        anchor_matches=anchor_matches,
        low_match_audit=low_match_audit,
        anchor_match_audit=anchor_match_audit,
        total_controls=controls,
    )
    near_stats = build_near_winner_stats(winners, low_control_entities, sequence_panel)
    false_repair_stats = build_false_repair_stats(anchor_control_entities)
    unconditional_validation = build_unconditional_validation_readout(
        factor_dominance, sequence_dominance
    )
    regime_validation = build_regime_conditioned_validation_readout(
        factor_dominance, sequence_dominance
    )
    validate_validation_readouts(
        factor_dominance=factor_dominance,
        sequence_dominance=sequence_dominance,
        unconditional_validation=unconditional_validation,
        regime_validation=regime_validation,
    )
    validation_opportunity = build_validation_opportunity_audit(
        winners=winners,
        low_match_audit=low_match_audit,
        anchor_match_audit=anchor_match_audit,
        split_config=split_config,
    )

    gate_summary = evaluate_gates(
        winners=winners,
        low_match_audit=low_match_audit,
        factor_dominance=factor_dominance,
        sequence_dominance=sequence_dominance,
        thresholds=thresholds,
    )
    decision = gate_summary["decision"]

    publishable_outputs = {
        "big_winner_episode_reference_summary": winners,
        "frozen_anchor_profile_summary": anchor_summary,
        "winner_vs_matched_control_stats": matched_control_stats,
        "near_winner_comparison_stats": near_stats,
        "false_repair_comparison_stats": false_repair_stats,
        "shared_axis_market_regime_dominance": market_regime_dominance,
        "shared_axis_factor_dominance": factor_dominance,
        "shared_axis_sequence_dominance": sequence_dominance,
        "sequence_family_test_count": sequence_counts,
        "sequence_examples_descriptive": sequence_examples,
        "winner_only_retrospective_stage_profile": stage_profile,
        "unconditional_validation_readout": unconditional_validation,
        "regime_conditioned_validation_readout": regime_validation,
        "validation_opportunity_audit": validation_opportunity,
    }
    output_paths: dict[str, Path] = {}
    for name, frame in publishable_outputs.items():
        output_paths[f"publishable.tables.{name}"] = write_dataframe(
            table_dir / PUBLISHABLE_TABLES[name], ensure_frame(frame)
        )

    local_outputs = {
        "local_cache.big_winner_episode_reference": (local_cache_dir / "big_winner_episode_reference.parquet", winners),
        "local_cache.episode_aligned_daily_panel": (local_cache_dir / "episode_aligned_daily_panel.parquet", low_panel),
        "local_cache.matched_control_panel": (local_cache_dir / "matched_control_panel.parquet", matched_control_panel),
        "local_cache.extraction_eligibility_audit": (local_cache_dir / "extraction_eligibility_audit.csv", extraction_audit),
        "local_cache.cluster_boundary_overlap_audit": (local_cache_dir / "cluster_boundary_overlap_audit.csv", cluster_audit),
        "large_raw.control_candidate_pool": (large_raw_dir / "control_candidate_pool.parquet", controls),
        "large_raw.anchor_aligned_daily_panel": (large_raw_dir / "anchor_aligned_daily_panel.parquet", anchor_panel),
        "large_raw.sequence_entity_panel": (large_raw_dir / "sequence_entity_panel.parquet", sequence_panel),
    }
    for name, (path, frame) in local_outputs.items():
        output_paths[name] = write_dataframe(path, ensure_frame(frame))

    report_path = report_dir / "reverse_lifecycle_profile_report.md"
    report_text = build_report(
        config=config,
        split_config=split_config,
        extraction_audit=extraction_audit,
        cluster_audit=cluster_audit,
        winners=winners,
        controls=controls,
        low_match_audit=low_match_audit,
        anchor_match_audit=anchor_match_audit,
        matched_control_stats=matched_control_stats,
        anchor_summary=anchor_summary,
        market_regime_dominance=market_regime_dominance,
        factor_dominance=factor_dominance,
        sequence_dominance=sequence_dominance,
        sequence_counts=sequence_counts,
        stage_profile=stage_profile,
        gate_summary=gate_summary,
        input_paths=input_paths,
        bucket_values=bucket_values,
        output_paths=output_paths,
    )
    report_path.write_text(report_text, encoding="utf-8")
    output_paths["publishable.reports.reverse_lifecycle_profile_report"] = report_path

    manifest_path = manifest_dir / "run_manifest.json"
    write_manifest(
        manifest_path=manifest_path,
        config=config,
        config_path=config_path,
        input_paths=input_paths,
        output_paths=output_paths,
        decision=decision,
        gate_summary=gate_summary,
        split_config=split_config,
    )
    return {
        "decision": decision,
        "manifest_path": str(manifest_path),
        "report_path": str(report_path),
    }


def validate_required_inputs(paths: dict[str, Path]) -> None:
    for name, path in paths.items():
        if name.endswith("_dir"):
            if not path.is_dir():
                raise FileNotFoundError(f"Missing required input directory {name}: {path}")
        elif not path.is_file():
            raise FileNotFoundError(f"Missing required input file {name}: {path}")


def resolve_vwap_source_policy(source_coverage_audit: pd.DataFrame) -> dict[str, Any]:
    required_columns = {"category", "support_state", "units"}
    missing = required_columns.difference(source_coverage_audit.columns)
    if missing:
        return {
            "compatible": False,
            "reason": f"source_coverage_audit_missing_columns:{sorted(missing)}",
        }
    categories = source_coverage_audit.set_index("category", drop=False)
    required_categories = ["historical_raw_daily_bars", "historical_qfq_daily_bars"]
    rows = []
    for category in required_categories:
        if category not in categories.index:
            return {"compatible": False, "reason": f"missing_{category}"}
        row = categories.loc[category]
        if isinstance(row, pd.DataFrame):
            row = row.iloc[0]
        rows.append(row)
    raw_row, qfq_row = rows
    raw_supported = str(raw_row.get("support_state", "")) == "supported"
    qfq_supported = str(qfq_row.get("support_state", "")) == "supported"
    raw_units = str(raw_row.get("units", ""))
    qfq_units = str(qfq_row.get("units", ""))
    units_ok = (
        "volume=shares" in raw_units
        and "money=CNY" in raw_units
        and "volume=shares" in qfq_units
        and "money=CNY" in qfq_units
    )
    compatible = bool(raw_supported and qfq_supported and units_ok)
    return {
        "compatible": compatible,
        "reason": "raw_qfq_same_date_money_cny_volume_shares"
        if compatible
        else "raw_qfq_daily_or_units_not_supported",
        "raw_units": raw_units,
        "qfq_units": qfq_units,
    }


def most_common_text(values: pd.Series) -> str:
    clean = values.dropna().astype(str)
    if clean.empty:
        return ""
    return str(clean.mode().iloc[0])


def concat_or_empty(parts: list[pd.DataFrame]) -> pd.DataFrame:
    if not parts:
        return pd.DataFrame()
    return pd.concat(parts, ignore_index=True)


def instrument_extraction_audit(
    *,
    instrument: str,
    features: pd.DataFrame,
    membership_dates: set[str],
    candidates: pd.DataFrame,
    params: ExtractionParams,
    split_config: SplitConfig,
) -> dict[str, Any]:
    date_to_pos = {date: idx for idx, date in enumerate(features["date"].astype(str))}
    in_membership = [date for date in membership_dates if date in date_to_pos]
    otherwise_in_range = 0
    blocked_lookback = 0
    first_eligible = ""
    for date in sorted(in_membership):
        pos = date_to_pos[date]
        if pos + params.forward_horizon_sessions >= len(features):
            continue
        if date < split_config.train_start or date > split_config.latest_label_complete_low_date:
            continue
        otherwise_in_range += 1
        if pos < params.prior_lookback_sessions:
            blocked_lookback += 1
        elif not first_eligible:
            first_eligible = date
    return {
        "instrument": instrument,
        "membership_rows_with_price": len(in_membership),
        "otherwise_in_range_rows": otherwise_in_range,
        "blocked_by_insufficient_250d_lookback_rows": blocked_lookback,
        "effective_first_eligible_low_date": first_eligible,
        "candidate_low_count": len(candidates),
        "winner_candidate_count": int(
            (candidates["mfe_120"] >= params.big_winner_mfe_threshold).sum()
        )
        if not candidates.empty
        else 0,
    }


def dominance_thresholds(config: dict[str, Any]) -> dict[str, float]:
    dominance = config["dominance"]
    return {
        "min_total_winner_episodes": float(dominance["min_total_winner_episodes"]),
        "min_validation_winner_episodes": float(dominance["min_validation_winner_episodes"]),
        "min_robustness_winner_episodes": float(dominance["min_robustness_winner_episodes"]),
        "min_control_match_coverage": float(dominance["min_control_match_coverage"]),
        "min_average_controls_per_winner": float(dominance["min_average_controls_per_winner"]),
        "min_anchor_occurrences_for_claim": float(dominance["min_anchor_occurrences_for_claim"]),
        "min_sequence_occurrences_for_claim": float(dominance["min_sequence_occurrences_for_claim"]),
        "min_feature_non_missing_coverage_for_claim": float(
            dominance["min_feature_non_missing_coverage_for_claim"]
        ),
        "standardized_mean_difference_gate": float(
            dominance["standardized_mean_difference_gate"]
        ),
        "lift_gate": float(dominance["lift_gate"]),
        "absolute_rate_difference_gate": float(
            dominance["absolute_rate_difference_gate"]
        ),
    }


def attach_match_counts(
    winners: pd.DataFrame, low_match_audit: pd.DataFrame, anchor_match_audit: pd.DataFrame
) -> pd.DataFrame:
    out = winners.copy()
    for axis, audit in [
        ("low", low_match_audit),
        ("ema60", anchor_match_audit),
    ]:
        column = f"{axis}_matched_control_count"
        if audit.empty:
            out[column] = 0
            continue
        counts = audit.set_index("winner_id")["matched_control_count"]
        out[column] = out["episode_id"].map(counts).fillna(0).astype(int)
    return out


def build_matched_entities(
    *,
    winners: pd.DataFrame,
    controls: pd.DataFrame,
    matches: pd.DataFrame,
    match_axis: str,
    daily_by_instrument: dict[str, pd.DataFrame],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    if matches.empty:
        return empty_entities(), empty_entities()
    matched_winner_ids = sorted(matches["winner_id"].unique())
    if match_axis == "shared_axis_low":
        winner_axis_col = "episode_low_date"
        control_axis_col = "candidate_low_date"
    else:
        winner_axis_col = "first_ema60_reclaim_date"
        control_axis_col = "first_ema60_reclaim_date"

    winner_entities = winners.loc[winners["episode_id"].isin(matched_winner_ids)].copy()
    winner_entities["entity_id"] = winner_entities["episode_id"]
    winner_entities["group"] = "winner"
    winner_entities["axis_date"] = winner_entities[winner_axis_col]
    winner_entities["matched_winner_id"] = winner_entities["episode_id"]

    control_entities = matches.merge(
        controls,
        left_on="control_id",
        right_on="control_candidate_id",
        how="left",
        suffixes=("", "_control"),
    )
    if control_entities.empty:
        return winner_entities, empty_entities()
    control_entities["entity_id"] = control_entities["match_id"]
    control_entities["group"] = "control"
    control_entities["instrument"] = control_entities["control_instrument"]
    control_entities["axis_date"] = control_entities[control_axis_col]
    control_entities["split"] = control_entities["winner_split"]
    control_entities["duration_bucket"] = control_entities["winner_duration_bucket"]
    control_entities["matched_winner_id"] = control_entities["winner_id"]
    repair_metrics = [
        false_repair_metrics(
            daily_by_instrument.get(row.instrument, pd.DataFrame()),
            str(row.candidate_low_date),
            str(row.first_ema60_reclaim_date),
        )
        for row in control_entities.itertuples(index=False)
    ]
    if repair_metrics:
        metric_frame = pd.DataFrame(repair_metrics)
        for column in metric_frame.columns:
            control_entities[column] = metric_frame[column].to_numpy()
    return winner_entities, control_entities


def empty_entities() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "entity_id",
            "instrument",
            "group",
            "axis_date",
            "split",
            "duration_bucket",
            "matched_winner_id",
        ]
    )


def summarize_path_dominance(
    entities: pd.DataFrame,
    daily_by_instrument: dict[str, pd.DataFrame],
    *,
    thresholds: dict[str, float],
) -> pd.DataFrame:
    if entities.empty:
        return pd.DataFrame()
    path_features = compute_path_tolerance_features(
        entities,
        daily_by_instrument,
        entity_id_col="entity_id",
        axis_date_col="axis_date",
        group_col="group",
    )
    rows: list[dict[str, Any]] = []
    for feature in [
        "max_drawdown_axis_to_plus_20d",
        "max_drawdown_axis_to_plus_60d",
        "max_runup_axis_to_plus_20d",
        "max_runup_axis_to_plus_60d",
    ]:
        if feature not in path_features.columns:
            continue
        from pipeline import continuous_dominance_row

        for split, regime_bucket, duration, stratum in iter_dominance_slices(path_features):
            row = continuous_dominance_row(
                stratum,
                family="path_tolerance",
                feature=feature,
                shared_axis="shared_axis_low",
                relative_day=0,
                thresholds=thresholds,
                split=split,
                regime_bucket=regime_bucket,
                duration_bucket=duration,
            )
            row["dominance_id"] = (
                f"shared_axis_low_path_{feature}_{split}_{regime_bucket}_{duration}"
            )
            rows.append(row)
    return pd.DataFrame(rows)


def build_match_panel(
    low_matches: pd.DataFrame, anchor_matches: pd.DataFrame, controls: pd.DataFrame
) -> pd.DataFrame:
    matches = pd.concat([low_matches, anchor_matches], ignore_index=True)
    if matches.empty:
        return matches
    return matches.merge(
        controls,
        left_on="control_id",
        right_on="control_candidate_id",
        how="left",
        suffixes=("", "_control"),
    )


def build_anchor_summary(
    winners: pd.DataFrame, controls: pd.DataFrame, matched_controls: pd.DataFrame
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    sources = [
        ("winner_reference", winners),
        ("control_candidate_pool", controls),
        ("matched_low_controls", matched_controls),
    ]
    for group_name, frame in sources:
        if frame.empty:
            continue
        for split, split_frame in frame.groupby("split", dropna=False):
            present = split_frame["first_ema60_reclaim_missing_reason"] == NOT_MISSING
            years = (
                pd.to_datetime(
                    split_frame.loc[present, "first_ema60_reclaim_date"],
                    errors="coerce",
                )
                .dt.year.dropna()
                .astype(int)
                .nunique()
            )
            rows.append(
                {
                    "anchor_family": "first_ema60_reclaim",
                    "source_group": group_name,
                    "split": split,
                    "row_count": len(split_frame),
                    "anchor_present_count": int(present.sum()),
                    "missing_event_absent_count": int(
                        (split_frame["first_ema60_reclaim_missing_reason"] == MISSING_EVENT_ABSENT).sum()
                    ),
                    "anchor_occurrence_rate": float(present.mean()) if len(split_frame) else np.nan,
                    "anchor_year_coverage": years,
                    "claim_status": "sample_blocked"
                    if int(present.sum()) < 50
                    else "diagnostic_candidate",
                }
            )
    return pd.DataFrame(rows)


def build_matched_control_stats(
    *,
    winners: pd.DataFrame,
    low_matches: pd.DataFrame,
    anchor_matches: pd.DataFrame,
    low_match_audit: pd.DataFrame,
    anchor_match_audit: pd.DataFrame,
    total_controls: pd.DataFrame,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for axis, audit, matches in [
        ("shared_axis_low", low_match_audit, low_matches),
        ("shared_axis_ema60", anchor_match_audit, anchor_matches),
    ]:
        if audit.empty:
            rows.append(
                {
                    "match_axis": axis,
                    "split": "all",
                    "winner_count": len(winners),
                    "matched_winner_count": 0,
                    "control_match_count": 0,
                    "match_coverage": 0.0,
                    "average_controls_per_winner": 0.0,
                    "cross_split_boundary_unusable_count": 0,
                    "unmatched_winner_count": len(winners),
                    "match_anchor_date_min": "",
                    "match_anchor_date_max": "",
                    "match_fields": "",
                    "match_distance_mean": np.nan,
                    "match_distance_p95": np.nan,
                    "unmatched_reason_counts": "{}",
                    "future_label_used_for_profile_only": True,
                }
            )
            continue
        for split in ["all", "train", "validation", "robustness"]:
            split_winners = winners if split == "all" else winners.loc[winners["split"] == split]
            split_audit = audit
            if split != "all" and not split_winners.empty:
                split_audit = audit.loc[audit["winner_id"].isin(split_winners["episode_id"])]
            elif split != "all":
                split_audit = audit.iloc[0:0]
            split_matches = matches
            if split != "all" and not split_winners.empty and not matches.empty:
                split_matches = matches.loc[matches["winner_id"].isin(split_winners["episode_id"])]
            elif split != "all":
                split_matches = matches.iloc[0:0]
            matched = split_audit.loc[split_audit["matched_control_count"] > 0]
            control_count = int(split_audit["matched_control_count"].sum()) if not split_audit.empty else 0
            unmatched_reasons = (
                split_audit.loc[
                    split_audit["unmatched_reason"].astype(str) != "", "unmatched_reason"
                ]
                .astype(str)
                .value_counts()
                .to_dict()
                if not split_audit.empty and "unmatched_reason" in split_audit
                else {}
            )
            match_fields = (
                "|".join(sorted(split_matches["match_fields"].dropna().astype(str).unique()))
                if not split_matches.empty and "match_fields" in split_matches
                else ""
            )
            distances = (
                pd.to_numeric(split_matches["match_distance"], errors="coerce").dropna()
                if not split_matches.empty and "match_distance" in split_matches
                else pd.Series(dtype=float)
            )
            anchor_dates = (
                split_matches["match_anchor_date"].dropna().astype(str)
                if not split_matches.empty and "match_anchor_date" in split_matches
                else pd.Series(dtype=str)
            )
            rows.append(
                {
                    "match_axis": axis,
                    "split": split,
                    "winner_count": len(split_winners),
                    "matched_winner_count": len(matched),
                    "control_match_count": control_count,
                    "available_control_candidate_count": len(total_controls),
                    "match_coverage": len(matched) / len(split_winners)
                    if len(split_winners)
                    else 0.0,
                    "average_controls_per_winner": control_count / len(split_winners)
                    if len(split_winners)
                    else 0.0,
                    "cross_split_boundary_unusable_count": int(
                        split_audit["cross_split_boundary_unusable_count"].sum()
                    )
                    if not split_audit.empty
                    else 0,
                    "unmatched_winner_count": len(split_winners) - len(matched),
                    "match_anchor_date_min": anchor_dates.min() if len(anchor_dates) else "",
                    "match_anchor_date_max": anchor_dates.max() if len(anchor_dates) else "",
                    "match_fields": match_fields,
                    "match_distance_mean": distances.mean() if len(distances) else np.nan,
                    "match_distance_p95": distances.quantile(0.95) if len(distances) else np.nan,
                    "unmatched_reason_counts": json.dumps(
                        unmatched_reasons, sort_keys=True, ensure_ascii=False
                    ),
                    "future_label_used_for_profile_only": bool(
                        split_matches["future_label_used_for_profile_only"].all()
                    )
                    if not split_matches.empty and "future_label_used_for_profile_only" in split_matches
                    else True,
                }
            )
    return pd.DataFrame(rows)


def build_near_winner_stats(
    winners: pd.DataFrame, matched_controls: pd.DataFrame, sequence_panel: pd.DataFrame
) -> pd.DataFrame:
    if matched_controls.empty:
        return pd.DataFrame(
            [
                {
                    "comparison": "winner_vs_near_winner_control",
                    "winner_count": len(winners),
                    "near_winner_control_count": 0,
                    "claim_status": "sample_blocked",
                }
            ]
        )
    near = matched_controls.loc[matched_controls["control_is_near_winner"]].copy()
    rows = []
    for split in ["all", "train", "validation", "robustness"]:
        split_winners = winners if split == "all" else winners.loc[winners["split"] == split]
        split_near = near if split == "all" else near.loc[near["split"] == split]
        rows.append(
            {
                "comparison": "winner_vs_near_winner_control",
                "split": split,
                "winner_count": len(split_winners),
                "near_winner_control_count": len(split_near),
                "winner_mfe_120_mean": pd.to_numeric(split_winners["mfe_120"], errors="coerce").mean()
                if not split_winners.empty
                else np.nan,
                "near_winner_mfe_120_mean": pd.to_numeric(split_near["mfe_120"], errors="coerce").mean()
                if not split_near.empty
                else np.nan,
                "claim_status": "diagnostic"
                if len(split_near) >= 30
                else "sample_blocked",
            }
        )
    if not sequence_panel.empty:
        for sequence_id, group in sequence_panel.groupby("sequence_id", sort=False):
            for split in ["all", "train", "validation", "robustness"]:
                subset = group if split == "all" else group.loc[group["split"] == split]
                winner = subset.loc[subset["group"] == "winner"]
                near_control = subset.loc[
                    (subset["group"] == "control") & (subset["control_is_near_winner"])
                ]
                winner_rate = (
                    float(winner["sequence_present"].mean()) if len(winner) else np.nan
                )
                near_rate = (
                    float(near_control["sequence_present"].mean())
                    if len(near_control)
                    else np.nan
                )
                rows.append(
                    {
                        "comparison": "winner_vs_near_winner_sequence",
                        "split": split,
                        "sequence_id": sequence_id,
                        "winner_count": len(winner),
                        "near_winner_control_count": len(near_control),
                        "winner_sequence_rate": winner_rate,
                        "near_winner_sequence_rate": near_rate,
                        "lift": safe_lift(winner_rate, near_rate),
                        "absolute_rate_difference": (
                            winner_rate - near_rate
                            if not pd.isna(winner_rate) and not pd.isna(near_rate)
                            else np.nan
                        ),
                        "claim_status": "diagnostic"
                        if len(near_control) >= 30
                        else "sample_blocked",
                    }
                )
    return pd.DataFrame(rows)


def build_false_repair_stats(matched_controls: pd.DataFrame) -> pd.DataFrame:
    if matched_controls.empty:
        return pd.DataFrame(
            [
                {
                    "comparison": "false_repair_controls",
                    "control_count": 0,
                    "false_repair_count": 0,
                    "claim_status": "sample_blocked",
                }
            ]
        )
    rows = []
    for split in ["all", "train", "validation", "robustness"]:
        subset = matched_controls if split == "all" else matched_controls.loc[matched_controls["split"] == split]
        false_count = int(subset["control_is_false_repair"].sum()) if "control_is_false_repair" in subset else 0
        false_10d = (
            int(subset["control_is_false_repair_10d"].sum())
            if "control_is_false_repair_10d" in subset
            else 0
        )
        false_20d = (
            int(subset["control_is_false_repair_20d"].sum())
            if "control_is_false_repair_20d" in subset
            else 0
        )
        regimes = (
            subset["market_regime_bucket"].dropna().astype(str).value_counts().to_dict()
            if "market_regime_bucket" in subset
            else {}
        )
        rows.append(
            {
                "comparison": "false_repair_controls",
                "split": split,
                "match_basis": "same_ema60_anchor_week_same_split",
                "control_count": len(subset),
                "false_repair_count": false_count,
                "false_repair_10d_count": false_10d,
                "false_repair_20d_count": false_20d,
                "false_repair_rate": false_count / len(subset) if len(subset) else np.nan,
                "drawdown_anchor_to_plus_10d_mean": pd.to_numeric(
                    subset.get("false_repair_drawdown_anchor_to_plus_10d", pd.Series(dtype=float)),
                    errors="coerce",
                ).mean()
                if len(subset)
                else np.nan,
                "drawdown_anchor_to_plus_20d_mean": pd.to_numeric(
                    subset.get("false_repair_drawdown_anchor_to_plus_20d", pd.Series(dtype=float)),
                    errors="coerce",
                ).mean()
                if len(subset)
                else np.nan,
                "runup_axis_low_to_anchor_plus_20d_mean": pd.to_numeric(
                    subset.get(
                        "false_repair_runup_axis_low_to_anchor_plus_20d",
                        pd.Series(dtype=float),
                    ),
                    errors="coerce",
                ).mean()
                if len(subset)
                else np.nan,
                "regime_bucket_counts": json.dumps(regimes, sort_keys=True, ensure_ascii=False),
                "claim_status": "diagnostic" if false_count >= 30 else "sample_blocked",
            }
        )
    return pd.DataFrame(rows)


def build_unconditional_validation_readout(
    factor_dominance: pd.DataFrame, sequence_dominance: pd.DataFrame
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    if not factor_dominance.empty:
        subset = factor_dominance.loc[
            (factor_dominance["split"] == "validation")
            & (factor_dominance["regime_bucket"] == "all")
            & (factor_dominance["duration_bucket"] == "all")
        ].copy()
        for row in subset.itertuples(index=False):
            item = row._asdict()
            rows.append(
                {
                    "readout_type": "factor_unconditional_validation",
                    "id": item.get("dominance_id", ""),
                    "feature_or_sequence": item.get("feature", ""),
                    "shared_axis": item.get("shared_axis", ""),
                    "winner_count": item.get("winner_count", np.nan),
                    "control_count": item.get("control_count", np.nan),
                    "effect": item.get("standardized_mean_difference", np.nan),
                    "lift": item.get("lift", np.nan),
                    "absolute_rate_difference": item.get("absolute_rate_difference", np.nan),
                    "claim_status": item.get("claim_status", ""),
                }
            )
    if not sequence_dominance.empty:
        subset = sequence_dominance.loc[
            (sequence_dominance["split"] == "validation")
            & (sequence_dominance["regime_bucket"] == "all")
            & (sequence_dominance["duration_bucket"] == "all")
        ].copy()
        for row in subset.itertuples(index=False):
            item = row._asdict()
            rows.append(
                {
                    "readout_type": "sequence_unconditional_validation",
                    "id": item.get("sequence_id", ""),
                    "feature_or_sequence": item.get("sequence_family", ""),
                    "shared_axis": item.get("shared_axis", ""),
                    "winner_count": item.get("winner_count", np.nan),
                    "control_count": item.get("control_count", np.nan),
                    "effect": item.get("absolute_rate_difference", np.nan),
                    "lift": item.get("lift", np.nan),
                    "absolute_rate_difference": item.get("absolute_rate_difference", np.nan),
                    "claim_status": item.get("claim_status", ""),
                }
            )
    return pd.DataFrame(rows)


def build_regime_conditioned_validation_readout(
    factor_dominance: pd.DataFrame, sequence_dominance: pd.DataFrame
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    if not factor_dominance.empty:
        subset = factor_dominance.loc[
            (factor_dominance["split"] == "validation")
            & (factor_dominance["regime_bucket"] != "all")
            & (factor_dominance["duration_bucket"] == "all")
        ].copy()
        for row in subset.itertuples(index=False):
            item = row._asdict()
            rows.append(
                {
                    "readout_type": "factor_regime_conditioned_validation",
                    "id": item.get("dominance_id", ""),
                    "regime_bucket": item.get("regime_bucket", ""),
                    "duration_bucket": item.get("duration_bucket", ""),
                    "feature_or_sequence": item.get("feature", ""),
                    "shared_axis": item.get("shared_axis", ""),
                    "winner_count": item.get("winner_count", np.nan),
                    "control_count": item.get("control_count", np.nan),
                    "effect": item.get("standardized_mean_difference", np.nan),
                    "lift": item.get("lift", np.nan),
                    "absolute_rate_difference": item.get("absolute_rate_difference", np.nan),
                    "claim_status": item.get("claim_status", ""),
                }
            )
    if not sequence_dominance.empty:
        subset = sequence_dominance.loc[
            (sequence_dominance["split"] == "validation")
            & (sequence_dominance["regime_bucket"] != "all")
            & (sequence_dominance["duration_bucket"] == "all")
        ].copy()
        for row in subset.itertuples(index=False):
            item = row._asdict()
            rows.append(
                {
                    "readout_type": "sequence_regime_conditioned_validation",
                    "id": item.get("sequence_id", ""),
                    "regime_bucket": item.get("regime_bucket", ""),
                    "duration_bucket": item.get("duration_bucket", ""),
                    "feature_or_sequence": item.get("sequence_family", ""),
                    "shared_axis": item.get("shared_axis", ""),
                    "winner_count": item.get("winner_count", np.nan),
                    "control_count": item.get("control_count", np.nan),
                    "effect": item.get("absolute_rate_difference", np.nan),
                    "lift": item.get("lift", np.nan),
                    "absolute_rate_difference": item.get("absolute_rate_difference", np.nan),
                    "claim_status": item.get("claim_status", ""),
                }
            )
    return pd.DataFrame(rows)


def validate_validation_readouts(
    *,
    factor_dominance: pd.DataFrame,
    sequence_dominance: pd.DataFrame,
    unconditional_validation: pd.DataFrame,
    regime_validation: pd.DataFrame,
) -> None:
    expected_unconditional = expected_validation_rows(
        factor_dominance, sequence_dominance, regime_conditioned=False
    )
    expected_regime = expected_validation_rows(
        factor_dominance, sequence_dominance, regime_conditioned=True
    )
    if expected_unconditional and unconditional_validation.empty:
        raise RuntimeError(
            "unconditional_validation_readout is empty despite validation dominance rows"
        )
    if expected_regime and regime_validation.empty:
        raise RuntimeError(
            "regime_conditioned_validation_readout is empty despite validation-regime dominance rows"
        )


def expected_validation_rows(
    factor_dominance: pd.DataFrame,
    sequence_dominance: pd.DataFrame,
    *,
    regime_conditioned: bool,
) -> int:
    total = 0
    for frame in [factor_dominance, sequence_dominance]:
        if frame.empty or not {"split", "regime_bucket", "duration_bucket"}.issubset(frame.columns):
            continue
        mask = frame["split"] == "validation"
        if regime_conditioned:
            mask &= (frame["regime_bucket"] != "all") & (frame["duration_bucket"] == "all")
        else:
            mask &= (frame["regime_bucket"] == "all") & (frame["duration_bucket"] == "all")
        total += int(mask.sum())
    return total


def build_validation_opportunity_audit(
    *,
    winners: pd.DataFrame,
    low_match_audit: pd.DataFrame,
    anchor_match_audit: pd.DataFrame,
    split_config: SplitConfig,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for split in ["train", "validation", "robustness"]:
        split_winners = winners.loc[winners["split"] == split] if not winners.empty else winners
        for axis, audit in [
            ("shared_axis_low", low_match_audit),
            ("shared_axis_ema60", anchor_match_audit),
        ]:
            split_audit = (
                audit.loc[audit["winner_id"].isin(split_winners["episode_id"])]
                if not audit.empty and not split_winners.empty
                else audit.iloc[0:0]
                if not audit.empty
                else pd.DataFrame()
            )
            rows.append(
                {
                    "split": split,
                    "match_axis": axis,
                    "split_start": getattr(split_config, f"{split}_start", ""),
                    "split_end": getattr(split_config, f"{split}_end", "")
                    if split != "robustness"
                    else split_config.latest_label_complete_low_date,
                    "winner_episode_count": len(split_winners),
                    "matched_winner_count": int(
                        (split_audit["matched_control_count"] > 0).sum()
                    )
                    if not split_audit.empty
                    else 0,
                    "control_match_count": int(split_audit["matched_control_count"].sum())
                    if not split_audit.empty
                    else 0,
                    "cross_split_boundary_unusable_count": int(
                        split_audit["cross_split_boundary_unusable_count"].sum()
                    )
                    if not split_audit.empty
                    else 0,
                    "opportunity_status": "available" if len(split_winners) else "sample_blocked",
                }
            )
    return pd.DataFrame(rows)


def build_sequence_examples(sequence_panel: pd.DataFrame) -> pd.DataFrame:
    if sequence_panel.empty:
        return pd.DataFrame()
    examples = sequence_panel.loc[
        (sequence_panel["group"] == "winner") & (sequence_panel["sequence_present"])
    ].copy()
    if examples.empty:
        return examples
    examples = examples.sort_values(["sequence_family", "split", "entity_id"]).groupby(
        "sequence_id", as_index=False
    ).head(20)
    examples["example_status"] = "winner_only_descriptive"
    return examples[
        [
            "sequence_id",
            "sequence_family",
            "entity_id",
            "instrument",
            "split",
            "duration_bucket",
            "sequence_completion_date",
            "required_states",
            "forbidden_states",
            "order_constraints",
            "example_status",
        ]
    ]


def evaluate_gates(
    *,
    winners: pd.DataFrame,
    low_match_audit: pd.DataFrame,
    factor_dominance: pd.DataFrame,
    sequence_dominance: pd.DataFrame,
    thresholds: dict[str, float],
) -> dict[str, Any]:
    split_counts = winners.groupby("split").size().to_dict() if not winners.empty else {}
    total_winners = len(winners)
    validation_winners = int(split_counts.get("validation", 0))
    robustness_winners = int(split_counts.get("robustness", 0))
    anchor_present_count = (
        int((winners["first_ema60_reclaim_missing_reason"] == NOT_MISSING).sum())
        if not winners.empty and "first_ema60_reclaim_missing_reason" in winners
        else 0
    )
    years = (
        pd.to_datetime(winners["episode_low_date"], errors="coerce").dt.year
        if not winners.empty and "episode_low_date" in winners
        else pd.Series(dtype=float)
    )
    year_counts = years.dropna().astype(int).value_counts()
    instrument_counts = (
        winners["instrument"].astype(str).value_counts()
        if not winners.empty and "instrument" in winners
        else pd.Series(dtype=int)
    )
    winner_year_max_share = (
        float(year_counts.max() / total_winners) if total_winners and len(year_counts) else 0.0
    )
    winner_instrument_max_share = (
        float(instrument_counts.max() / total_winners)
        if total_winners and len(instrument_counts)
        else 0.0
    )
    if low_match_audit.empty:
        coverage = 0.0
        avg_controls = 0.0
    else:
        matched = low_match_audit["matched_control_count"] > 0
        coverage = float(matched.mean()) if len(matched) else 0.0
        avg_controls = float(low_match_audit["matched_control_count"].sum() / len(low_match_audit))

    blocked_reasons: list[str] = []
    if total_winners < thresholds["min_total_winner_episodes"]:
        blocked_reasons.append("min_total_winner_episodes")
    if validation_winners < thresholds["min_validation_winner_episodes"]:
        blocked_reasons.append("min_validation_winner_episodes")
    if robustness_winners < thresholds["min_robustness_winner_episodes"]:
        blocked_reasons.append("min_robustness_winner_episodes")
    if coverage < thresholds["min_control_match_coverage"]:
        blocked_reasons.append("min_control_match_coverage")
    if avg_controls < thresholds["min_average_controls_per_winner"]:
        blocked_reasons.append("min_average_controls_per_winner")
    if anchor_present_count < thresholds["min_anchor_occurrences_for_claim"]:
        blocked_reasons.append("min_anchor_occurrences_for_claim")
    if winner_year_max_share > 0.50:
        blocked_reasons.append("single_year_majority")
    if winner_instrument_max_share > 0.50:
        blocked_reasons.append("single_instrument_majority")
    if not has_conditioned_rows(factor_dominance):
        blocked_reasons.append("factor_regime_duration_conditioning_missing")
    if not has_conditioned_rows(sequence_dominance):
        blocked_reasons.append("sequence_regime_duration_conditioning_missing")

    headline_factor = headline_scope(factor_dominance)
    headline_sequence = headline_scope(sequence_dominance)
    factor_candidates = (
        headline_factor["claim_status"].astype(str).str.contains("candidate").sum()
        if not headline_factor.empty and "claim_status" in headline_factor
        else 0
    )
    sequence_supported = (
        headline_sequence["claim_status"].astype(str).str.contains("sequence_supported").sum()
        if not headline_sequence.empty and "claim_status" in headline_sequence
        else 0
    )
    sequence_candidates = (
        headline_sequence["claim_status"].astype(str).str.contains("candidate").sum()
        if not headline_sequence.empty and "claim_status" in headline_sequence
        else 0
    )

    if blocked_reasons:
        if (
            "min_validation_winner_episodes" in blocked_reasons
            or "min_robustness_winner_episodes" in blocked_reasons
        ):
            decision = "reverse_lifecycle_profile_validation_sample_blocked"
        else:
            decision = "reverse_lifecycle_profile_sample_blocked"
    elif sequence_supported:
        decision = "reverse_lifecycle_sequence_supported_universal_dominance"
    elif sequence_candidates:
        decision = "reverse_lifecycle_sequence_conditional_candidate"
    elif factor_candidates:
        decision = "reverse_lifecycle_profile_regime_conditional_candidate"
    else:
        decision = "marginal_and_sequence_no_stable_dominance_found"

    return {
        "decision": decision,
        "blocked_reasons": blocked_reasons,
        "total_winner_episodes": total_winners,
        "train_winner_episodes": int(split_counts.get("train", 0)),
        "validation_winner_episodes": validation_winners,
        "robustness_winner_episodes": robustness_winners,
        "low_match_coverage": coverage,
        "average_controls_per_winner": avg_controls,
        "anchor_present_count": anchor_present_count,
        "winner_year_max_share": winner_year_max_share,
        "winner_instrument_max_share": winner_instrument_max_share,
        "conditioned_factor_row_count": conditioned_row_count(factor_dominance),
        "conditioned_sequence_row_count": conditioned_row_count(sequence_dominance),
        "factor_candidate_count": int(factor_candidates),
        "sequence_supported_count": int(sequence_supported),
        "sequence_candidate_count": int(sequence_candidates),
    }


def headline_scope(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return frame
    required = {"split", "regime_bucket", "duration_bucket"}
    if not required.issubset(frame.columns):
        return frame
    return frame.loc[
        (frame["split"] == "all")
        & (frame["regime_bucket"] == "all")
        & (frame["duration_bucket"] == "all")
    ]


def conditioned_row_count(frame: pd.DataFrame) -> int:
    if frame.empty or not {"regime_bucket", "duration_bucket"}.issubset(frame.columns):
        return 0
    conditioned = (frame["regime_bucket"] != "all") | (frame["duration_bucket"] != "all")
    return int(conditioned.sum())


def has_conditioned_rows(frame: pd.DataFrame) -> bool:
    return conditioned_row_count(frame) > 0


def ensure_frame(frame: pd.DataFrame) -> pd.DataFrame:
    if isinstance(frame, pd.DataFrame):
        return frame
    return pd.DataFrame(frame)


def build_report(
    *,
    config: dict[str, Any],
    split_config: SplitConfig,
    extraction_audit: pd.DataFrame,
    cluster_audit: pd.DataFrame,
    winners: pd.DataFrame,
    controls: pd.DataFrame,
    low_match_audit: pd.DataFrame,
    anchor_match_audit: pd.DataFrame,
    matched_control_stats: pd.DataFrame,
    anchor_summary: pd.DataFrame,
    market_regime_dominance: pd.DataFrame,
    factor_dominance: pd.DataFrame,
    sequence_dominance: pd.DataFrame,
    sequence_counts: pd.DataFrame,
    stage_profile: pd.DataFrame,
    gate_summary: dict[str, Any],
    input_paths: dict[str, Path],
    bucket_values: dict[str, list[str]],
    output_paths: dict[str, Path],
) -> str:
    lines: list[str] = []
    lines.append("# Big Winner Reverse Lifecycle Profile V0")
    lines.append("")
    lines.append(f"Final decision: `{gate_summary['decision']}`")
    lines.append("")
    lines.append("This run is a retrospective profile/diagnostic report. It does not train a model, run a backtest, or authorize an event contract.")
    lines.append("")

    lines.append("## Input Data and Hashes")
    lines.append("")
    for name, path in input_paths.items():
        digest = file_sha256(path) if path.is_file() else "directory"
        lines.append(f"- `{name}`: `{path}`; hash: `{digest}`")
    lines.append(f"- source git revision: `{git_revision(PROJECT_ROOT)}`")
    lines.append(f"- latest label-complete low date: `{split_config.latest_label_complete_low_date}`")
    lines.append("")

    lines.append("## Industry Data Status")
    lines.append("")
    industry = config.get("industry", {})
    lines.append(f"`industry_data_status = {industry.get('status', 'unavailable')}`.")
    lines.append(industry.get("caveat", "Industry diagnostics were skipped."))
    lines.append("Industry-relative rows are excluded from shared-axis dominance outputs.")
    lines.append("")

    lines.append("## Reference Episode Counts")
    lines.append("")
    lines.append(frame_to_markdown(count_by(winners, ["split"]), empty="No winner episodes."))
    lines.append("")
    lines.append("- Effective first eligible low date: `" + effective_first_date(extraction_audit) + "`")
    lines.append(
        "- Otherwise in-range rows blocked by insufficient 250-session lookback: "
        + str(int(extraction_audit.get("blocked_by_insufficient_250d_lookback_rows", pd.Series(dtype=int)).sum()))
    )
    lines.append("")

    lines.append("## Cluster and Horizon Audits")
    lines.append("")
    boundary_overlaps = (
        int(cluster_audit["boundary_overlaps"].sum())
        if not cluster_audit.empty and "boundary_overlaps" in cluster_audit
        else 0
    )
    lines.append(f"- Cluster-boundary overlap rows: `{boundary_overlaps}`")
    high_boundary = (
        int(winners["high_at_horizon_boundary"].sum())
        if not winners.empty
        else 0
    )
    lines.append(f"- Episodes with high at horizon boundary: `{high_boundary}`")
    lines.append("- Post-high exhaustion rows exclude or separately mark boundary-high episodes.")
    lines.append("")

    lines.append("## Lookback and VWAP Audits")
    lines.append("")
    if winners.empty:
        lines.append("No winner rows available for lookback/VWAP audits.")
    else:
        lookback_cols = ["lookback_60_complete", "lookback_120_complete", "lookback_250_complete"]
        lines.append(frame_to_markdown(winners[lookback_cols].mean().rename("coverage").reset_index()))
    vwap_rows = (
        factor_dominance.loc[
            factor_dominance["feature"].astype(str).str.contains("vwap", case=False, na=False),
            ["feature", "shared_axis", "relative_day", "feature_non_missing_coverage", "claim_status"],
        ].head(20)
        if not factor_dominance.empty
        else pd.DataFrame()
    )
    lines.append(frame_to_markdown(vwap_rows, empty="No VWAP dominance rows."))
    lines.append("")

    lines.append("## Control Matching")
    lines.append("")
    lines.append(frame_to_markdown(matched_control_stats))
    cross_split = (
        int(low_match_audit["cross_split_boundary_unusable_count"].sum())
        if not low_match_audit.empty
        else 0
    )
    lines.append(f"- Cross-split-boundary low-match candidates rejected/marked unusable: `{cross_split}`")
    lines.append(f"- Match bucket values: `{json.dumps(bucket_values, sort_keys=True)}`")
    lines.append("")

    lines.append("## Validation Opportunity Audit")
    lines.append("")
    validation_rows = winners.loc[winners["split"] == "validation"]
    lines.append(f"- Validation winner episodes: `{len(validation_rows)}`")
    lines.append("- The 2022-2023 split is treated as the fixed negative-beta stress validation window.")
    if "min_validation_winner_episodes" in gate_summary["blocked_reasons"]:
        lines.append("- Validation sample gate is blocked; split boundaries and thresholds were not moved.")
    lines.append("")

    lines.append("## Market Regime Counts")
    lines.append("")
    lines.append("Winner episode low-date regime counts:")
    lines.append(frame_to_markdown(count_by(winners, ["split", "market_regime_bucket"])))
    lines.append("")
    lines.append("Control candidate low-date regime counts:")
    lines.append(
        frame_to_markdown(
            count_by(controls, ["split", "market_regime_bucket"])
            if "market_regime_bucket" in controls
            else pd.DataFrame()
        )
    )
    lines.append("")

    lines.append("## Frozen Anchor Profile")
    lines.append("")
    lines.append(frame_to_markdown(anchor_summary))
    lines.append("")

    lines.append("## Shared-Axis Dominance Results")
    lines.append("")
    factor_preview = factor_dominance.sort_values(
        "claim_status", ascending=False
    ).head(20) if not factor_dominance.empty else pd.DataFrame()
    lines.append(frame_to_markdown(factor_preview))
    lines.append("")
    lines.append(frame_to_markdown(market_regime_dominance))
    lines.append("")

    lines.append("## Shared-Axis Sequence Dominance")
    lines.append("")
    lines.append(frame_to_markdown(sequence_dominance))
    lines.append("")
    lines.append("Frozen sequence definitions:")
    for definition in SEQUENCE_DEFINITIONS:
        lines.append(
            f"- `{definition['sequence_id']}`: {definition['required_states']}; window `{definition['relative_window']}`."
        )
    lines.append("")
    lines.append("Sequence family test counts:")
    lines.append(frame_to_markdown(sequence_counts))
    lines.append("")

    lines.append("## Winner-Only Descriptive Profile")
    lines.append("")
    lines.append("Winner-only stages are descriptive only and are not control-adjusted dominance evidence.")
    lines.append(frame_to_markdown(stage_profile.head(30) if not stage_profile.empty else stage_profile))
    lines.append("")

    lines.append("## Multiple Testing and Claim Families")
    lines.append("")
    if not factor_dominance.empty:
        lines.append(frame_to_markdown(count_by(factor_dominance, ["multiple_test_family", "claim_status"])))
    if not sequence_dominance.empty:
        lines.append(frame_to_markdown(count_by(sequence_dominance, ["multiple_test_family", "claim_status"])))
    lines.append("")

    lines.append("## Final Decision Replay")
    lines.append("")
    for key, value in gate_summary.items():
        lines.append(f"- `{key}`: `{value}`")
    lines.append("")

    lines.append("## Output Paths")
    lines.append("")
    for name, path in sorted(output_paths.items()):
        lines.append(f"- `{name}`: `{path}`")
    lines.append("")
    return "\n".join(lines)


def effective_first_date(extraction_audit: pd.DataFrame) -> str:
    if extraction_audit.empty or "effective_first_eligible_low_date" not in extraction_audit:
        return ""
    values = extraction_audit["effective_first_eligible_low_date"].replace("", np.nan).dropna()
    return str(values.min()) if len(values) else ""


def count_by(frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame(columns=columns + ["count"])
    return frame.groupby(columns, dropna=False).size().reset_index(name="count")


def frame_to_markdown(frame: pd.DataFrame, *, empty: str = "No rows.") -> str:
    if frame.empty:
        return empty
    display = frame.copy()
    if len(display) > 30:
        display = display.head(30)
    try:
        return display.to_markdown(index=False)
    except Exception:
        return display.to_csv(index=False)


def write_manifest(
    *,
    manifest_path: Path,
    config: dict[str, Any],
    config_path: Path,
    input_paths: dict[str, Path],
    output_paths: dict[str, Path],
    decision: str,
    gate_summary: dict[str, Any],
    split_config: SplitConfig,
) -> None:
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
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
    data_prepare_manifest_path = input_paths["data_prepare_run_manifest_json"]
    data_prepare_manifest = {}
    if data_prepare_manifest_path.is_file():
        data_prepare_manifest = json.loads(data_prepare_manifest_path.read_text(encoding="utf-8"))
    manifest = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "command": sys.argv,
        "project_root": str(PROJECT_ROOT),
        "source_git_revision": git_revision(PROJECT_ROOT),
        "config_path": str(config_path),
        "config_hash": stable_hash(config),
        "config_file_hash": file_sha256(config_path),
        "decision": decision,
        "gate_summary": gate_summary,
        "split_config": split_config.__dict__,
        "input_paths": {name: str(path) for name, path in input_paths.items()},
        "input_hashes": input_hashes,
        "data_layer_manifest_hashes": {
            "data_prepare_run_manifest_hash": input_hashes.get("data_prepare_run_manifest_json"),
            "data_prepare_git_revision": data_prepare_manifest.get("git_revision"),
            "data_prepare_decision": data_prepare_manifest.get("decision"),
            "data_prepare_output_hashes": data_prepare_manifest.get("output_hashes", {}),
        },
        "outputs": {name: str(path) for name, path in output_paths.items()},
        "output_hashes": output_hashes,
    }
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    raise SystemExit(main())
