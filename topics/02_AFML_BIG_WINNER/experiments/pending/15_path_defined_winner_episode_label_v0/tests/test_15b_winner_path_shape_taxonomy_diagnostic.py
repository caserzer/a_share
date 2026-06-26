from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd


EXPERIMENT_DIR = Path(__file__).resolve().parents[1]
RUNNER_PATH = EXPERIMENT_DIR / "src" / "run_15b_winner_path_shape_taxonomy_diagnostic.py"


def load_runner():
    spec = importlib.util.spec_from_file_location("run_15b_winner_path_shape_taxonomy_diagnostic", RUNNER_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def base_label(rows: list[dict[str, object]]) -> pd.DataFrame:
    defaults = {
        "threshold_id": "up50pct",
        "threshold_return": 0.50,
        "split_bucket": "train",
        "path_winner": True,
        "is_censored": False,
        "entry_date": "2020-01-02",
        "entry_price": 10.0,
        "time_to_threshold_sessions": 10,
        "volatility_20d": 0.02,
        "fast_winner_flag": False,
        "slow_winner_flag": True,
    }
    return pd.DataFrame([{**defaults, **row} for row in rows])


def quantiles() -> dict[str, float]:
    return {
        "q_efficiency_30": 0.40,
        "q_efficiency_50": 0.60,
        "q_efficiency_70": 0.80,
        "q_max_drawdown_abs_30": 0.05,
        "q_max_drawdown_abs_50": 0.10,
        "q_max_drawdown_abs_70": 0.20,
        "q_underwater_share_50": 0.10,
        "q_underwater_share_70": 0.40,
        "q_entropy_30": 0.30,
        "q_entropy_50": 0.50,
        "q_entropy_70": 0.70,
        "q_trend_r2_50": 0.50,
        "q_trend_r2_70": 0.80,
        "q_top1_gain_share_70": 0.40,
        "q_top1_gain_share_85": 0.60,
        "q_top3_gain_share_70": 0.60,
        "q_top3_gain_share_85": 0.80,
        "q_large_up_day_count_70": 3.0,
        "q_time_to_threshold_75": 100.0,
        "q_pullback_5pct_count_50": 1.0,
        "q_pullback_5pct_count_70": 3.0,
    }


def metric_row(**overrides: object) -> dict[str, object]:
    base = {
        "source_row_key": "S1|2020-01-01|r1|up50pct",
        "instrument": "S1",
        "reference_date": "2020-01-01",
        "row_id": "r1",
        "split_bucket": "train",
        "threshold_id": "up50pct",
        "episode_cluster_id": "up50pct::S1::000000",
        "segment_start_pos": 1,
        "segment_end_pos": 20,
        "segment_sessions": 20,
        "entry_price": 10.0,
        "shape_close_start": 10.0,
        "shape_close_end": 15.0,
        "path_shape_quality": "pass",
        "path_efficiency": 0.60,
        "max_drawdown_before_hit": -0.10,
        "max_drawdown_before_hit_abs": 0.10,
        "underwater_days_share": 0.20,
        "directional_entropy_5state": 0.50,
        "trend_line_r2": 0.60,
        "top1_positive_gain_share": 0.30,
        "top3_positive_gain_share": 0.50,
        "large_up_day_count": 0,
        "time_to_threshold_sessions": 20,
        "pullback_5pct_count": 0,
    }
    base.update(overrides)
    return base


def test_global_episode_cluster_does_not_split_by_bucket():
    runner = load_runner()
    label = base_label(
        [
            {
                "instrument": "S1",
                "reference_date": "2020-01-01",
                "row_id": "r1",
                "entry_pos": 10,
                "episode_threshold_pos": 20,
                "split_bucket": "train",
            },
            {
                "instrument": "S1",
                "reference_date": "2020-01-02",
                "row_id": "r2",
                "entry_pos": 18,
                "episode_threshold_pos": 25,
                "split_bucket": "validation",
            },
            {
                "instrument": "S1",
                "reference_date": "2020-01-03",
                "row_id": "r3",
                "entry_pos": 40,
                "episode_threshold_pos": 45,
                "split_bucket": "train",
            },
            {
                "instrument": "S1",
                "reference_date": "2020-01-04",
                "row_id": "r4",
                "entry_pos": 50,
                "episode_threshold_pos": pd.NA,
                "path_winner": False,
                "is_censored": True,
            },
        ]
    )

    membership, clusters = runner.build_winner_episode_clusters(label)

    assert len(clusters) == 2
    first_two = membership.loc[membership["row_id"].isin(["r1", "r2"]), "episode_cluster_id"]
    assert first_two.nunique() == 1
    assert "r4" not in set(membership["row_id"])


def test_15a_adapter_accepts_frozen_episode_threshold_pos(tmp_path):
    runner = load_runner()
    qfq_dir = tmp_path / "qfq"
    qfq_dir.mkdir()
    pd.DataFrame({"date": pd.bdate_range("2020-01-01", periods=5).strftime("%Y-%m-%d")}).to_csv(
        qfq_dir / "S1.csv", index=False
    )
    label = base_label(
        [
            {
                "instrument": "S1",
                "reference_date": "2020-01-01",
                "row_id": "r1",
                "entry_pos": 1,
                "episode_threshold_pos": 3,
            }
        ]
    )

    audit = runner.path_defined_label_adapter_audit(label, tmp_path / "path_defined_label_panel.parquet", qfq_dir)
    row = audit.iloc[0]

    assert row["source_row_key"] == "instrument,reference_date,row_id,threshold_id"
    assert row["adapter_status"] == "pass"
    assert int(row["adapter_duplicate_source_row_key_n"]) == 0


def test_input_schema_accepts_15a_selected_threshold_recommendation(tmp_path):
    runner = load_runner()
    audit_path = tmp_path / "search_accounting_audit.csv"
    pd.DataFrame({"selected_threshold_recommendation": ["up50pct"]}).to_csv(audit_path, index=False)

    audit = runner.build_input_artifact_audit(
        {"paths": {"upstream_15a_search_accounting": str(audit_path)}},
        {"upstream_15a_search_accounting": audit_path},
    )

    row = audit.iloc[0]
    assert row["schema_status"] == "pass"
    assert row["input_gate_status"] == "pass"


def test_short_path_missing_class_specific_features_is_not_data_quality_blocked():
    runner = load_runner()
    frame = pd.DataFrame(
        [
            metric_row(
                segment_sessions=5,
                path_shape_quality="too_short_for_stable_shape",
                directional_entropy_5state=np.nan,
                trend_line_r2=np.nan,
                top1_positive_gain_share=np.nan,
                top3_positive_gain_share=np.nan,
            )
        ]
    )

    assigned = runner.assign_taxonomy(frame, quantiles())
    row = assigned.iloc[0]

    assert row["path_type"] == "unclassified_short_path"
    assert row["path_type"] != "data_quality_blocked"
    assert "directional_entropy_5state" in row["path_type_missing_feature_flags"]


def test_large_up_day_count_alone_does_not_force_jump_repricing():
    runner = load_runner()
    frame = pd.DataFrame(
        [
            metric_row(
                path_efficiency=0.90,
                max_drawdown_before_hit=-0.03,
                max_drawdown_before_hit_abs=0.03,
                underwater_days_share=0.05,
                directional_entropy_5state=0.40,
                trend_line_r2=0.95,
                top1_positive_gain_share=0.30,
                top3_positive_gain_share=0.50,
                large_up_day_count=4,
            )
        ]
    )

    assigned = runner.assign_taxonomy(frame, quantiles())

    assert assigned.iloc[0]["path_type"] == "smooth_trend_winner"


def test_smooth_overrides_jump_routes_high_efficiency_path_to_smooth_trend():
    runner = load_runner()
    frame = pd.DataFrame(
        [
            metric_row(
                path_efficiency=0.90,
                max_drawdown_before_hit=-0.03,
                max_drawdown_before_hit_abs=0.03,
                underwater_days_share=0.05,
                directional_entropy_5state=0.40,
                trend_line_r2=0.95,
                top1_positive_gain_share=0.70,
                top3_positive_gain_share=0.85,
                large_up_day_count=4,
            )
        ]
    )

    assigned = runner.assign_taxonomy(frame, quantiles())
    row = assigned.iloc[0]

    assert row["path_type"] == "smooth_trend_winner"
    assert "predicate_smooth_overrides_jump" in row["path_type_conflict_flags"]
    assert bool(row["predicate_high_gain_concentration"])
    assert bool(row["predicate_smooth_trend_winner"])


def test_split_overlap_audit_populates_cluster_start_and_end_dates(tmp_path):
    runner = load_runner()
    qfq_dir = tmp_path / "qfq"
    qfq_dir.mkdir()
    pd.DataFrame(
        {
            "date": pd.bdate_range("2020-01-01", periods=30).strftime("%Y-%m-%d"),
            "open": [10.0] * 30,
            "high": [10.0] * 30,
            "close": [10.0] * 30,
        }
    ).to_csv(qfq_dir / "S1.csv", index=False)
    label = base_label(
        [
            {
                "instrument": "S1",
                "reference_date": "2020-01-01",
                "row_id": "r1",
                "entry_pos": 2,
                "episode_threshold_pos": 10,
                "reference_pos": 1,
                "split_bucket": "train",
            },
            {
                "instrument": "S1",
                "reference_date": "2020-01-02",
                "row_id": "r2",
                "entry_pos": 9,
                "episode_threshold_pos": 15,
                "reference_pos": 8,
                "split_bucket": "validation",
            },
        ]
    )
    membership, clusters = runner.build_winner_episode_clusters(label)

    audit, _cluster_panel = runner.split_overlap_audit(membership, clusters, label, qfq_dir)
    row = audit.iloc[0]

    assert row["cluster_start_date"] == "2020-01-03"
    assert row["cluster_end_date"] == "2020-01-22"
    assert row["split_overlap_status"] == "pass"


def test_transitive_interval_merge_not_greedy_adjacent_only():
    runner = load_runner()
    label = base_label(
        [
            {"instrument": "S1", "reference_date": "2020-01-01", "row_id": "r1", "entry_pos": 1, "episode_threshold_pos": 4},
            {"instrument": "S1", "reference_date": "2020-01-02", "row_id": "r2", "entry_pos": 4, "episode_threshold_pos": 8},
            {"instrument": "S1", "reference_date": "2020-01-03", "row_id": "r3", "entry_pos": 8, "episode_threshold_pos": 10},
            {"instrument": "S1", "reference_date": "2020-01-04", "row_id": "r4", "entry_pos": 20, "episode_threshold_pos": 22},
        ]
    )

    membership, clusters = runner.build_winner_episode_clusters(label)

    assert len(clusters) == 2
    assert membership.loc[membership["row_id"].isin(["r1", "r2", "r3"]), "episode_cluster_id"].nunique() == 1


def taxonomy_fit_frame(extra_rows: list[dict[str, object]] | None = None) -> pd.DataFrame:
    rows = []
    for i, eff in enumerate([0.10, 0.20, 0.30, 0.40, 0.50], start=1):
        rows.append(
            metric_row(
                source_row_key=f"S1|2020-01-{i:02d}|r{i}|up50pct",
                row_id=f"r{i}",
                episode_cluster_id=f"c{i}",
                cluster_split_bucket="train",
                touches_multiple_split_buckets=False,
                touches_multiple_calendar_split_buckets=False,
                path_efficiency=eff,
                max_drawdown_before_hit_abs=0.01 * i,
                underwater_days_share=0.02 * i,
                directional_entropy_5state=0.10 * i,
                trend_line_r2=0.20 + 0.10 * i,
                top1_positive_gain_share=0.10 * i,
                top3_positive_gain_share=0.12 * i,
                large_up_day_count=i,
                time_to_threshold_sessions=20 + i,
                pullback_5pct_count=i % 3,
            )
        )
    if extra_rows:
        rows.extend(extra_rows)
    return pd.DataFrame(rows)


def test_train_only_quantiles_do_not_use_validation_or_robustness():
    runner = load_runner()
    extra = [
        metric_row(
            source_row_key="S2|2020-02-01|v1|up50pct",
            row_id="v1",
            split_bucket="validation",
            episode_cluster_id="cv",
            cluster_split_bucket="validation",
            touches_multiple_split_buckets=False,
            touches_multiple_calendar_split_buckets=False,
            path_efficiency=99.0,
            max_drawdown_before_hit_abs=99.0,
            underwater_days_share=0.99,
            directional_entropy_5state=0.99,
            trend_line_r2=0.99,
            top1_positive_gain_share=0.99,
            top3_positive_gain_share=0.99,
            large_up_day_count=99,
            time_to_threshold_sessions=999,
            pullback_5pct_count=99,
        )
    ]

    quantile_values, fit_pop, _rules = runner.fit_taxonomy_quantiles(taxonomy_fit_frame(extra))

    assert len(fit_pop) == 5
    assert quantile_values["q_efficiency_70"] < 1.0


def test_split_overlap_clusters_excluded_from_rule_fit():
    runner = load_runner()
    extra = [
        metric_row(
            source_row_key="S3|2020-03-01|x1|up50pct",
            row_id="x1",
            episode_cluster_id="cx",
            cluster_split_bucket="cross_split",
            touches_multiple_split_buckets=True,
            touches_multiple_calendar_split_buckets=True,
            path_efficiency=99.0,
            max_drawdown_before_hit_abs=99.0,
            underwater_days_share=0.99,
            directional_entropy_5state=0.99,
            trend_line_r2=0.99,
            top1_positive_gain_share=0.99,
            top3_positive_gain_share=0.99,
            large_up_day_count=99,
            time_to_threshold_sessions=999,
            pullback_5pct_count=99,
        )
    ]

    quantile_values, fit_pop, _rules = runner.fit_taxonomy_quantiles(taxonomy_fit_frame(extra))

    assert len(fit_pop) == 5
    assert quantile_values["q_time_to_threshold_75"] < 100


def test_path_efficiency_handles_zero_total_variation_fail_closed():
    runner = load_runner()
    qfq = pd.DataFrame(
        {
            "date": pd.bdate_range("2020-01-01", periods=6).strftime("%Y-%m-%d"),
            "high": [15.0] * 6,
            "close": [10.0] * 6,
            "ma20_close": [np.nan] * 6,
        }
    )
    row = SimpleNamespace(
        instrument="S1",
        reference_date="2020-01-01",
        row_id="r1",
        split_bucket="train",
        threshold_id="up50pct",
        threshold_return=0.50,
        episode_cluster_id="c1",
        cluster_split_bucket="train",
        touches_multiple_split_buckets=False,
        touches_multiple_calendar_split_buckets=False,
        entry_pos=0,
        episode_threshold_pos=5,
        entry_price=10.0,
        time_to_threshold_sessions=5,
        fast_winner_flag=True,
        slow_winner_flag=False,
        volatility_20d=0.02,
    )

    metrics = runner._metric_row(row, runner.qfq_arrays(qfq))

    assert np.isnan(metrics["path_efficiency"])
    assert metrics["zero_variation_path"] is True


def test_large_up_day_share_uses_segment_session_denominator():
    runner = load_runner()
    qfq = pd.DataFrame(
        {
            "date": pd.bdate_range("2020-01-01", periods=5).strftime("%Y-%m-%d"),
            "high": [10.0, 11.0, 12.2, 12.0, 13.5],
            "close": [10.0, 11.0, 12.2, 12.0, 13.5],
            "ma20_close": [np.nan] * 5,
        }
    )
    row = SimpleNamespace(
        instrument="S1",
        reference_date="2020-01-01",
        row_id="r1",
        split_bucket="train",
        threshold_id="up50pct",
        threshold_return=0.50,
        episode_cluster_id="c1",
        cluster_split_bucket="train",
        touches_multiple_split_buckets=False,
        touches_multiple_calendar_split_buckets=False,
        entry_pos=0,
        episode_threshold_pos=4,
        entry_price=10.0,
        time_to_threshold_sessions=4,
        fast_winner_flag=True,
        slow_winner_flag=False,
        volatility_20d=0.02,
    )

    metrics = runner._metric_row(row, runner.qfq_arrays(qfq))

    assert metrics["large_up_day_count"] == 3
    assert metrics["large_up_day_share"] == 3 / 5


def test_entropy_5state_formula_and_zero_vol_fallback():
    runner = load_runner()
    qfq = pd.DataFrame(
        {
            "date": pd.bdate_range("2020-01-01", periods=11).strftime("%Y-%m-%d"),
            "high": [10.2, 10.3, 10.1, 10.4, 10.5, 10.8, 11.0, 11.2, 11.4, 11.7, 15.1],
            "close": [10.0, 10.1, 9.9, 10.2, 10.0, 10.4, 10.6, 10.3, 10.7, 11.0, 15.0],
            "ma20_close": [np.nan] * 11,
        }
    )
    row = SimpleNamespace(
        instrument="S1",
        reference_date="2020-01-01",
        row_id="r1",
        split_bucket="train",
        threshold_id="up50pct",
        threshold_return=0.50,
        episode_cluster_id="c1",
        cluster_split_bucket="train",
        touches_multiple_split_buckets=False,
        touches_multiple_calendar_split_buckets=False,
        entry_pos=0,
        episode_threshold_pos=10,
        entry_price=10.0,
        time_to_threshold_sessions=10,
        fast_winner_flag=True,
        slow_winner_flag=False,
        volatility_20d=0.0,
    )

    metrics = runner._metric_row(row, runner.qfq_arrays(qfq))

    assert metrics["entropy_volatility_source"] == "realized_segment_fallback"
    assert np.isfinite(metrics["directional_entropy_5state"])


def test_jump_repricing_precedence_over_smooth_trend():
    runner = load_runner()
    frame = pd.DataFrame(
        [
            metric_row(
                path_efficiency=0.50,
                max_drawdown_before_hit_abs=0.15,
                underwater_days_share=0.20,
                directional_entropy_5state=0.80,
                trend_line_r2=0.40,
                top1_positive_gain_share=0.90,
                top3_positive_gain_share=0.95,
            )
        ]
    )

    assigned = runner.assign_taxonomy(frame, quantiles())

    assert assigned.iloc[0]["path_type"] == "jump_repricing_winner"


def test_short_jump_path_classified_as_jump_not_short_unknown():
    runner = load_runner()
    frame = pd.DataFrame(
        [
            metric_row(
                segment_sessions=5,
                path_shape_quality="too_short_for_stable_shape",
                top1_positive_gain_share=0.90,
                top3_positive_gain_share=0.95,
            )
        ]
    )

    assigned = runner.assign_taxonomy(frame, quantiles())

    assert assigned.iloc[0]["path_type"] == "jump_repricing_winner"


def test_late_rescue_precedence_over_slow_grind():
    runner = load_runner()
    frame = pd.DataFrame(
        [
            metric_row(
                time_to_threshold_sessions=200,
                path_efficiency=0.60,
                max_drawdown_before_hit=-0.30,
                max_drawdown_before_hit_abs=0.30,
                underwater_days_share=0.20,
                trend_line_r2=0.80,
                top1_positive_gain_share=0.20,
                top3_positive_gain_share=0.40,
            )
        ]
    )

    assigned = runner.assign_taxonomy(frame, quantiles())

    assert assigned.iloc[0]["path_type"] == "late_rescue_winner"
    assert "predicate_late_rescue_winner" in assigned.iloc[0]["path_type_conflict_flags"]


def test_short_path_cannot_be_smooth_trend():
    runner = load_runner()
    frame = pd.DataFrame(
        [
            metric_row(
                segment_sessions=5,
                path_shape_quality="too_short_for_stable_shape",
                path_efficiency=0.90,
                max_drawdown_before_hit=-0.03,
                max_drawdown_before_hit_abs=0.03,
                underwater_days_share=0.05,
                directional_entropy_5state=0.40,
                trend_line_r2=0.95,
                top1_positive_gain_share=0.20,
                top3_positive_gain_share=0.40,
            )
        ]
    )

    assigned = runner.assign_taxonomy(frame, quantiles())

    assert assigned.iloc[0]["path_type"] == "unclassified_short_path"


def test_representative_anchor_medoid_is_deterministic():
    runner = load_runner()
    rows = []
    for i, eff in enumerate([0.20, 0.40, 0.90], start=1):
        rows.append(
            metric_row(
                source_row_key=f"S1|2020-01-0{i}|r{i}|up50pct",
                row_id=f"r{i}",
                episode_cluster_id="c1",
                cluster_split_bucket="train",
                touches_multiple_split_buckets=False,
                touches_multiple_calendar_split_buckets=False,
                entry_pos=i,
                time_to_threshold_sessions=10 + i,
                path_efficiency=eff,
                log_time_to_threshold=np.log1p(10 + i),
            )
        )
    anchor_metrics = pd.DataFrame(rows)

    reps1, _episodes1, _rules1 = runner.select_representatives(anchor_metrics, pd.DataFrame())
    reps2, _episodes2, _rules2 = runner.select_representatives(anchor_metrics, pd.DataFrame())

    assert reps1.iloc[0]["medoid_anchor_row_id"] == reps2.iloc[0]["medoid_anchor_row_id"]


def test_hard_fail_gate_sources_exist_and_fail_closed_when_missing():
    runner = load_runner()

    assert runner.gate_from_status(pd.DataFrame(), "status") == "fail"
    assert runner.gate_from_status(pd.DataFrame({"other": ["pass"]}), "status") == "fail"
    assert runner.gate_from_status(pd.DataFrame({"status": ["pass", "fail"]}), "status") == "fail"


def test_decision_support_gates_include_validation_and_robustness_materiality():
    runner = load_runner()
    assignments = pd.DataFrame(
        {
            "threshold_id": ["up50pct"] * 270,
            "split_bucket": ["train"] * 210 + ["validation"] * 30 + ["robustness"] * 30,
            "path_type": ["smooth_trend_winner"] * 70
            + ["stair_step_winner"] * 70
            + ["late_rescue_winner"] * 70
            + ["smooth_trend_winner"] * 30
            + ["smooth_trend_winner"] * 30,
        }
    )
    stability = pd.DataFrame({"stability_extreme_failure": [False], "representative_taxonomy_disagreement_share": [0.10]})
    gates = {
        "input_artifact": "pass",
        "upstream_lineage": "pass",
        "price_path_completeness": "pass",
        "path_defined_label_adapter": "pass",
        "path_defined_label_rebuild": "pass",
        "episode_cluster": "pass",
        "train_rule_fit": "pass",
        "search_accounting": "pass",
    }

    decision = runner.decision_row(gates, assignments, stability, {"taxonomy": {}}, "incremental_shape_descriptor")
    row = decision.iloc[0]

    assert row["decision_state"] == "15B_no_stable_path_shape_taxonomy"
    assert not bool(row["validation_material_path_type_support_gate"])
    assert not bool(row["robustness_material_path_type_support_gate"])


def test_search_accounting_records_startup_authorization_override():
    runner = load_runner()

    audit = runner.search_accounting_audit(
        {
            "taxonomy": {
                "startup_authorization_basis": "15A_material_censoring_finding_not_15A_morphology_verdict",
                "manual_research_plan_override": True,
            }
        }
    )
    row = audit.iloc[0]

    assert row["startup_authorization_basis"] == "15A_material_censoring_finding_not_15A_morphology_verdict"
    assert bool(row["manual_research_plan_override"])
    assert row["search_accounting_status"] == "pass"


def test_decision_never_authorizes_deployment_or_signal_search():
    runner = load_runner()
    assignments = pd.DataFrame(
        {
            "threshold_id": ["up50pct"],
            "split_bucket": ["train"],
            "path_type": ["smooth_trend_winner"],
        }
    )
    stability = pd.DataFrame({"stability_extreme_failure": [False]})
    gates = {
        "input_artifact": "pass",
        "upstream_lineage": "pass",
        "price_path_completeness": "pass",
        "path_defined_label_adapter": "pass",
        "path_defined_label_rebuild": "pass",
        "episode_cluster": "pass",
        "train_rule_fit": "pass",
        "search_accounting": "pass",
    }

    decision = runner.decision_row(gates, assignments, stability, {"taxonomy": {}})
    row = decision.iloc[0]

    assert not bool(row["label_deployment_authorized"])
    assert not bool(row["signal_search_authorized"])
    assert not bool(row["model_training_authorized"])
    assert not bool(row["entry_policy_authorized"])
