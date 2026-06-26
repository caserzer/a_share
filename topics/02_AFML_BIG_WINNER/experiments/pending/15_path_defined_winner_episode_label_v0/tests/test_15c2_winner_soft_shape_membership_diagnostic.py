from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd


EXPERIMENT_DIR = Path(__file__).resolve().parents[1]
RUNNER_PATH = EXPERIMENT_DIR / "src" / "run_15c2_winner_soft_shape_membership_diagnostic.py"
CONFIG_PATH = EXPERIMENT_DIR / "configs" / "config_15c2_winner_soft_shape_membership_diagnostic.yaml"


def load_runner():
    spec = importlib.util.spec_from_file_location("run_15c2_for_tests", RUNNER_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


m = load_runner()


def config() -> dict:
    cfg = m.load_config(CONFIG_PATH)
    cfg["bootstrap_repeat_n"] = 3
    cfg["random_baseline_repeat_n"] = 3
    return cfg


def shape_row(i: int, proto: str, threshold: str = "up50pct", split: str = "train") -> dict:
    base = {
        "source_row_key": f"S{i}|2020-01-{i % 28 + 1:02d}|{i}|{threshold}",
        "threshold_id": threshold,
        "instrument": f"S{i}",
        "reference_date": f"2020-01-{i % 28 + 1:02d}",
        "row_id": i,
        "split_bucket": split,
        "episode_cluster_id": f"{threshold}::S{i}::000000",
        "path_winner": True,
        "is_censored": False,
        "cluster_split_bucket": split,
        "touches_multiple_split_buckets": False,
        "touches_multiple_calendar_split_buckets": False,
        "max_drawdown_20d": -0.01,
        "vol_compression_20d_60d": -0.10,
        "path_shape_quality": "pass",
        "path_type": proto,
        "entry_phase_pit": "early_base_pit",
        "entry_phase_outcome": "early_cluster_entry",
        "phase_assignment_status": "pass",
        "primary_gate_eligible": threshold == "up50pct" and split == "train",
        "eligible_primary_anchor": True,
        "segment_start_pos": i,
        "segment_end_pos": i + 20,
        "segment_sessions": 20,
        "entry_price": 10.0,
        "shape_close_start": 10.0,
        "shape_close_end": 15.0,
        "max_drawdown_before_hit": -0.05,
        "time_to_threshold_sessions": 20.0,
        "large_up_day_count": 0,
    }
    proto_shift = {
        "smooth_trend_winner": 0.0,
        "stair_step_winner": 2.0,
        "jump_repricing_winner": 4.0,
        "choppy_reversal_winner": 6.0,
        "slow_grind_winner": 8.0,
        "late_rescue_winner": 10.0,
    }[proto]
    for j, feature in enumerate(m.SHAPE_FEATURES_15C2):
        base[feature] = proto_shift + j * 0.01 + i * 0.001
    return base


def synthetic_panel(n_per_proto: int = 4) -> pd.DataFrame:
    rows = []
    i = 0
    for proto in m.PROTOTYPE_TYPES:
        for _ in range(n_per_proto):
            rows.append(shape_row(i, proto))
            i += 1
    return pd.DataFrame(rows)


def fit_membership(panel: pd.DataFrame):
    cfg = config()
    cfg["min_prototype_anchor_n"] = 2
    cfg["drop_prototype_anchor_n"] = 1
    scaler, _ = m.fit_scaler(panel, cfg["shape_features"])
    centers, meta = m.fit_prototypes(panel, scaler, cfg)
    membership = m.build_membership_panel(panel, panel, scaler, centers, cfg, cfg["temperature_primary"])
    return cfg, scaler, centers, meta, membership


def test_membership_vector_sums_to_one_and_excludes_unclassified():
    _, _, _, _, membership = fit_membership(synthetic_panel())
    cols = [f"membership_{proto}" for proto in m.PROTOTYPE_TYPES]
    assert np.allclose(membership[cols].sum(axis=1), 1.0)
    assert not any("unclassified" in col for col in membership.columns if col.startswith("membership_"))


def test_output_schema_uses_episode_cluster_id_only():
    cfg, _, _, _, membership = fit_membership(synthetic_panel())
    cluster = m.build_cluster_mixture(membership, cfg)
    assert "episode_cluster_id" in cluster.columns
    assert "winner_episode_cluster_id" not in cluster.columns


def test_top1_distance_percentile_flags_out_of_prototype_residual():
    panel = synthetic_panel()
    far = shape_row(999, "smooth_trend_winner")
    for feature in m.SHAPE_FEATURES_15C2:
        far[feature] = 1000.0
    panel = pd.concat([panel, pd.DataFrame([far])], ignore_index=True)
    _, _, _, _, membership = fit_membership(panel)
    far_row = membership.loc[membership["source_row_key"].eq(far["source_row_key"])].iloc[0]
    assert bool(far_row["out_of_prototype_residual"])
    assert not bool(far_row["sharp_episode"])


def test_known_failed_overlap_gate_uses_positive_delta_direction():
    cfg, _, _, _, membership = fit_membership(synthetic_panel(10))
    proto = "smooth_trend_winner"
    membership.loc[:, f"membership_{proto}"] = 0.0
    membership.loc[:19, f"membership_{proto}"] = 0.90
    membership.loc[:19, "vol_compression_20d_60d"] = -10.0
    membership.loc[20:, "vol_compression_20d_60d"] = 10.0
    cfg["known_failed_high_membership_min_n"] = 1
    overlap = m.build_known_failed_overlap(membership, cfg)
    row = overlap.loc[
        overlap["prototype_type"].eq(proto)
        & overlap["state"].eq("compression_state")
        & overlap["cluster_split_bucket"].eq("train")
    ].iloc[0]
    assert row["share_delta"] > 0
    assert row["overlap_status"] == "rediscovered_known_failure"


def test_random_baseline_seed_equals_20260626():
    cfg = config()
    search = m.build_search_accounting(cfg)
    assert int(cfg["random_baseline_seed"]) == 20260626
    assert int(search["random_baseline_seed"].iloc[0]) == 20260626


def test_rule_audit_contains_global_scaler_temperature_seed_row():
    panel = synthetic_panel(40)
    cfg = config()
    cfg["min_prototype_anchor_n"] = 2
    cfg["drop_prototype_anchor_n"] = 1
    scaler, missing_rates = m.fit_scaler(panel, cfg["shape_features"])
    centers, meta = m.fit_prototypes(panel, scaler, cfg)
    audit = m.build_rule_audit(panel, scaler, missing_rates, centers, meta, cfg)
    global_row = audit.loc[audit["prototype_type"].eq("__global_scaler_temperature_seed__")]
    assert len(global_row) == 1
    assert bool(global_row["prototype_dropped"].iloc[0])
    assert set(audit["membership_rule_fit_status"]) == {"pass"}


def test_multirow_hard_fail_gate_requires_all_required_rows_pass():
    good = pd.DataFrame({"status": ["pass", "pass"]})
    bad = pd.DataFrame({"status": ["pass", "fail"]})
    assert not m.hard_fail_present((good, "status", {"pass"}))
    assert m.hard_fail_present((bad, "status", {"pass"}))


def test_authoritative_join_graph_uses_cluster_membership_for_eligibility(tmp_path):
    cfg = config()
    base = synthetic_panel(1)[
        [
            "source_row_key",
            "threshold_id",
            "instrument",
            "reference_date",
            "row_id",
            "split_bucket",
            "episode_cluster_id",
            "path_winner",
            "is_censored",
            "cluster_split_bucket",
            "touches_multiple_split_buckets",
            "touches_multiple_calendar_split_buckets",
            "max_drawdown_20d",
            "vol_compression_20d_60d",
        ]
    ]
    feature_cols = [
        *m.FEATURE_PANEL_REQUIRED_COLUMNS,
        "segment_start_pos",
        "segment_end_pos",
        "segment_sessions",
        "entry_price",
        "shape_close_start",
        "shape_close_end",
        "max_drawdown_before_hit",
        "time_to_threshold_sessions",
        "large_up_day_count",
    ]
    shape = synthetic_panel(1)[feature_cols].copy()
    phase = synthetic_panel(1)[m.PHASE_REQUIRED_COLUMNS].copy()
    rule = pd.DataFrame({"rule_type": ["taxonomy_quantile"], "feature_id": ["x"], "quantile_name": ["q_efficiency_30"], "value": [0.0], "scale": [np.nan], "train_rule_fit_status": ["pass"]})
    paths = {
        "winner_episode_cluster_membership_15b": tmp_path / "base.csv",
        "taxonomy_assignment_panel_15b": tmp_path / "missing.parquet",
        "path_shape_feature_panel_15b": tmp_path / "shape.parquet",
        "entry_phase_assignment_15c": tmp_path / "phase.csv",
    }
    base.to_csv(paths["winner_episode_cluster_membership_15b"], index=False)
    shape.to_parquet(paths["path_shape_feature_panel_15b"], index=False)
    phase.to_csv(paths["entry_phase_assignment_15c"], index=False)
    panel, adapter, _ = m.load_authoritative_panel(paths, rule)
    assert adapter["adapter_status"].iloc[0] == "pass"
    assert "path_winner" in panel.columns
    assert bool(panel["eligible_primary_anchor"].all())


def test_taxonomy_adapter_filters_anchor_path_and_uses_priority1(tmp_path, monkeypatch):
    shape = synthetic_panel(1)[
        [
            *m.SHAPE_REQUIRED_COLUMNS,
            "segment_start_pos",
            "segment_end_pos",
            "segment_sessions",
            "entry_price",
            "shape_close_start",
            "shape_close_end",
            "max_drawdown_before_hit",
            "time_to_threshold_sessions",
            "large_up_day_count",
        ]
    ].copy()
    taxonomy = shape.copy()
    taxonomy["assignment_unit"] = "anchor_path"
    episode_row = taxonomy.iloc[[0]].copy()
    episode_row["assignment_unit"] = "episode_cluster"
    taxonomy = pd.concat([taxonomy, episode_row], ignore_index=True)
    label_map = taxonomy.drop_duplicates(["source_row_key", "threshold_id"]).set_index(
        ["source_row_key", "threshold_id"]
    )["path_type"]

    def fake_apply(frame, _rule):
        out = frame.copy()
        keys = list(zip(out["source_row_key"], out["threshold_id"]))
        out["path_type"] = [label_map.loc[key] for key in keys]
        return out

    monkeypatch.setattr(m, "apply_frozen_taxonomy", fake_apply)
    paths = {
        "taxonomy_assignment_panel_15b": tmp_path / "taxonomy.parquet",
        "path_shape_feature_panel_15b": tmp_path / "fallback.parquet",
    }
    taxonomy.to_parquet(paths["taxonomy_assignment_panel_15b"], index=False)
    shape.drop(columns=["path_type"]).to_parquet(paths["path_shape_feature_panel_15b"], index=False)
    out, adapter, _ = m.read_shape_source(paths, pd.DataFrame())
    assert int(adapter["adapter_source_priority"].iloc[0]) == 1
    assert adapter["adapter_status"].iloc[0] == "pass"
    assert int(adapter["adapter_duplicate_source_row_key_n"].iloc[0]) == 0
    assert len(out) == len(shape)


def test_taxonomy_priority1_hard_failure_does_not_silent_fallback(tmp_path, monkeypatch):
    shape = synthetic_panel(1)[m.SHAPE_REQUIRED_COLUMNS].copy()
    taxonomy = shape.copy()
    taxonomy["assignment_unit"] = "anchor_path"
    taxonomy = pd.concat([taxonomy, taxonomy.iloc[[0]]], ignore_index=True)
    fallback = shape.drop(columns=["path_type"]).copy()

    def fake_apply(frame, _rule):
        out = frame.copy()
        out["path_type"] = shape["path_type"].iloc[0]
        return out

    monkeypatch.setattr(m, "apply_frozen_taxonomy", fake_apply)
    paths = {
        "taxonomy_assignment_panel_15b": tmp_path / "taxonomy.parquet",
        "path_shape_feature_panel_15b": tmp_path / "fallback.parquet",
    }
    taxonomy.to_parquet(paths["taxonomy_assignment_panel_15b"], index=False)
    fallback.to_parquet(paths["path_shape_feature_panel_15b"], index=False)
    _, adapter, _ = m.read_shape_source(paths, pd.DataFrame())
    assert int(adapter["adapter_source_priority"].iloc[0]) == 0
    assert adapter["adapter_status"].iloc[0] == "fail"


def test_entry_phase_stratification_role_is_descriptive_only_not_t0_feature():
    cfg, _, _, _, membership = fit_membership(synthetic_panel())
    entry = m.build_entry_phase_readout(membership, cfg)
    assert "phase_stratification_role" in entry.columns
    assert set(entry["phase_stratification_role"]) == {"descriptive_only_not_t0_feature"}


def test_temperature_sensitivity_outputs_full_decision_enum():
    panel = synthetic_panel()
    cfg, scaler, centers, _, _ = fit_membership(panel)
    context = {
        "prototype_fit_population_anchor_n": 200,
        "prototype_population_ok": True,
        "sharpness_real": False,
        "morphology_not_all_rediscovered": True,
    }
    readout, status = m.build_temperature_sensitivity(panel, panel, scaler, centers, cfg, context)
    selected = readout.loc[
        readout["threshold_id"].eq(m.SELECTED_THRESHOLD_ID)
        & readout["cluster_split_bucket"].eq("train")
    ]
    assert status == "pass"
    assert selected["decision_state_under_temperature"].str.startswith("15C2_").all()
    assert not selected["decision_state_under_temperature"].isin({"material_sharp", "not_material_sharp"}).any()


def test_temperature_instability_downgrades_stability_gate():
    split = pd.DataFrame({"threshold_id": ["up50pct"], "cluster_split_bucket": ["train"]})
    threshold = pd.DataFrame({"threshold_id": ["up50pct", "up100pct", "up150pct"], "cluster_split_bucket": ["train", "train", "train"]})
    gate = m.build_stability_gate(split, threshold, "fail", 123)
    assert int(gate["prototype_fit_population_anchor_n"].iloc[0]) == 123
    assert gate["temperature_stability_status"].iloc[0] == "fail"
    assert gate["stability_gate_status"].iloc[0] == "fail"
