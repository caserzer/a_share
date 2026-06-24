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
RUNNER_13C_PATH = EXPERIMENT_DIR / "src" / "run_13c_morphology_orthogonal_residual_importance_diagnostic.py"


def load_runner(path: Path, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


r13c = load_runner(RUNNER_13C_PATH, "run_13c_morphology_orthogonal_residual_importance_diagnostic")
r13a = r13c.r13a
r13a3 = r13c.r13a3


RUN_ID = "13G_event_survival_opportunity_and_defense_overlay_diagnostic"
EXPERIMENT_ID = "13_full_pit_native_event_discovery_v0"
PHASE_ID = "13G"
CONFIG_PATH = EXPERIMENT_DIR / "configs" / "config_13g_event_survival_opportunity_and_defense_overlay_diagnostic.yaml"
CONFIG_13C_PATH = EXPERIMENT_DIR / "configs" / "config_13c_morphology_orthogonal_residual_importance_diagnostic.yaml"
TABLE_DIR = EXPERIMENT_DIR / "outputs" / "publishable" / "tables" / RUN_ID
LOCAL_CACHE_DIR = EXPERIMENT_DIR / "outputs" / "local_cache" / RUN_ID
REPORT_DIR = EXPERIMENT_DIR / "outputs" / "publishable" / "reports"
MANIFEST_DIR = EXPERIMENT_DIR / "outputs" / "manifests"
SPLITS = ("train", "validation", "robustness")
EVAL_SPLITS = ("validation", "robustness")
REPORT_INPUT_KEYS = {"upstream_report_13c", "upstream_report_13e", "upstream_report_13f"}
NOT_EVALUABLE_REASONS = (
    "entry_not_executable",
    "entry_price_missing",
    "max_horizon_path_incomplete",
    "split_lineage_missing",
    "qfq_bar_mapping_missing",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run 13G event survival opportunity and defense overlay diagnostic."
    )
    parser.add_argument("--config", default=str(CONFIG_PATH))
    parser.add_argument("--check-inputs-only", action="store_true")
    parser.add_argument("--mode", choices=["check-inputs", "full"], default="full")
    return parser.parse_args(argv)


def topic_path(value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    text = str(path)
    if text.startswith("topics/"):
        return REPO_ROOT / path
    if text.startswith(("data/", "experiments/")):
        return TOPIC_ROOT / path
    if text.startswith(("outputs/", "configs/", "src/", "tests/")):
        return EXPERIMENT_DIR / path
    return EXPERIMENT_DIR / path


def resolve_paths(config: dict[str, Any]) -> dict[str, Path]:
    return {key: topic_path(value) for key, value in config.get("paths", {}).items()}


def output_paths() -> dict[str, Path]:
    return {
        "input_artifact_audit": TABLE_DIR / "input_artifact_audit.csv",
        "upstream_lineage_audit": TABLE_DIR / "upstream_lineage_audit.csv",
        "row_level_rebuild_audit": TABLE_DIR / "row_level_rebuild_audit.csv",
        "survival_opportunity_label_grid_readout": TABLE_DIR / "survival_opportunity_label_grid_readout.csv",
        "time_to_hit_distribution": TABLE_DIR / "time_to_hit_distribution.csv",
        "event_uniqueness_density_audit": TABLE_DIR / "event_uniqueness_density_audit.csv",
        "rule_overlay_dictionary": TABLE_DIR / "rule_overlay_dictionary.csv",
        "rule_overlay_action_distribution": TABLE_DIR / "rule_overlay_action_distribution.csv",
        "rule_overlay_utility_readout": TABLE_DIR / "rule_overlay_utility_readout.csv",
        "rule_overlay_winner_retention_audit": TABLE_DIR / "rule_overlay_winner_retention_audit.csv",
        "search_multiplicity_audit": TABLE_DIR / "search_multiplicity_audit.csv",
        "event_survival_opportunity_overlay_decision": TABLE_DIR / "event_survival_opportunity_overlay_decision.csv",
        "survival_opportunity_label_panel": LOCAL_CACHE_DIR / "survival_opportunity_label_panel.parquet",
        "rule_overlay_event_panel": LOCAL_CACHE_DIR / "rule_overlay_event_panel.parquet",
        "report": REPORT_DIR / "event_survival_opportunity_and_defense_overlay_diagnostic_report.md",
        "manifest": MANIFEST_DIR / f"{RUN_ID}_manifest.json",
    }


def read_table(path: Path, **kwargs: Any) -> pd.DataFrame:
    return r13c.read_table(path, **kwargs)


def write_df(path: Path, frame: pd.DataFrame) -> Path:
    return r13c.write_df(path, frame)


def write_text(path: Path, text: str) -> Path:
    return r13c.write_text(path, text)


def write_json(path: Path, payload: dict[str, Any]) -> Path:
    return r13c.write_json(path, payload)


def file_sha(path: Path) -> str:
    return r13c.file_sha(path)


def count_rows(path: Path) -> int | float:
    return r13c.count_rows(path)


def stable_hash(value: Any) -> str:
    return r13c.stable_hash(value)


def schema_hash(path: Path) -> str:
    return r13c.schema_hash(path)


def boolish(value: Any) -> bool:
    return r13c.boolish(value)


def bool_series(series: pd.Series) -> pd.Series:
    return r13c.bool_series(series)


def finite_numeric(series: pd.Series) -> pd.Series:
    return r13c.finite_numeric(series)


def input_expected_columns() -> dict[str, tuple[str, ...]]:
    return {
        "requirement": (),
        "upstream_requirement_13a3": (),
        "upstream_requirement_13c": (),
        "upstream_requirement_13e": (),
        "upstream_requirement_13f": (),
        "upstream_13c_config": (),
        "upstream_report_13c": (),
        "upstream_report_13e": (),
        "upstream_report_13f": (),
        "upstream_13c_manifest": (),
        "upstream_13a3_decision": ("decision_state", "selected_state_id", "sequence_mining_authorized"),
        "upstream_13c_decision": (
            "decision_state",
            "selected_state_id",
            "meta_labeling_authorized",
            "bet_sizing_authorized",
        ),
        "upstream_13c_feature_cluster_dictionary": ("cluster_id", "feature_id", "feature_status"),
        "upstream_13c_sample_uniqueness_audit": ("state_id", "split_bucket"),
        "upstream_13c_row_level_rebuild_audit": (),
        "upstream_13c_morphology_residual_panel_cache": (
            "row_id",
            "instrument",
            "reference_date",
            "split_bucket",
            "native_scope",
        ),
        "upstream_13e_decision": (
            "decision_state",
            "selected_state_id",
            "meta_labeling_authorized",
            "bet_sizing_authorized",
        ),
        "upstream_13f_decision": (
            "decision_state",
            "selected_state_id",
            "meta_labeling_authorized",
            "bet_sizing_authorized",
        ),
        "pit_topn_400_100_executable_daily": ("usable_trade_date", "instrument"),
        "pit_topn_400_100_membership_daily": ("membership_date", "instrument"),
        "stock_daily_qfq_dir": (),
        "global_regime_calendar": ("date", "daily_regime_bucket"),
    }


def lineage_role_for_artifact(artifact_id: str) -> str:
    if artifact_id in REPORT_INPUT_KEYS:
        return "lineage_report_only_not_row_truth"
    if artifact_id.startswith("upstream_13f"):
        return "negative_decision_lineage_only_not_row_truth"
    if artifact_id.startswith("upstream_13"):
        return "upstream_13_lineage"
    if artifact_id.startswith("pit_") or artifact_id in {"stock_daily_qfq_dir", "global_regime_calendar"}:
        return "raw_pit_lineage_guard"
    return "run_config_input"


def build_input_audit(resolved: dict[str, Path]) -> pd.DataFrame:
    expected = input_expected_columns()
    rows: list[dict[str, Any]] = []
    for artifact_id, path in resolved.items():
        required_cols = expected.get(artifact_id, ())
        read_status = "pass" if path.exists() else "missing"
        schema_status = "not_checked"
        column_count: int | float = np.nan
        row_count: int | float = np.nan
        if path.exists():
            try:
                if path.is_dir():
                    schema_status = "directory"
                    row_count = count_rows(path)
                else:
                    frame = pd.read_parquet(path) if path.suffix.lower() == ".parquet" else read_table(path, nrows=5)
                    column_count = len(frame.columns)
                    row_count = count_rows(path)
                    missing = sorted(set(required_cols) - set(frame.columns))
                    schema_status = "pass" if not missing else "missing_columns:" + ";".join(missing)
            except Exception as exc:  # pragma: no cover - defensive audit path.
                read_status = f"read_error:{type(exc).__name__}"
                schema_status = "read_error"
        rows.append(
            {
                "artifact_id": artifact_id,
                "resolved_path": str(path),
                "required_flag": True,
                "lineage_role": lineage_role_for_artifact(artifact_id),
                "row_count": row_count,
                "column_count": column_count,
                "sha256": file_sha(path) if path.exists() and path.is_file() else "",
                "read_status": read_status,
                "schema_status": schema_status,
            }
        )
    return pd.DataFrame(rows)


def load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def manifest_local_cache_schema(manifest: dict[str, Any], artifact_id: str) -> str:
    for row in manifest.get("local_cache_audit", []) or []:
        if str(row.get("artifact_id", "")) == artifact_id:
            return str(row.get("schema_hash", ""))
    return ""


def manifest_output_sha(manifest: dict[str, Any], output_id: str) -> str:
    return str((manifest.get("output_hashes", {}) or {}).get(output_id, ""))


def build_13c_manifest_audit(resolved: dict[str, Path]) -> pd.DataFrame:
    manifest_path = resolved.get("upstream_13c_manifest", EXPERIMENT_DIR / "outputs" / "manifests" / "13C_morphology_orthogonal_residual_importance_diagnostic_manifest.json")
    rows: list[dict[str, Any]] = []
    manifest = load_json(manifest_path)
    rows.append(
        audit_row(
            "13c_manifest.readable",
            "readable" if manifest else "missing_or_unreadable",
            "readable",
            bool(manifest),
            "upstream_13c_manifest",
        )
    )
    if not manifest:
        return pd.DataFrame(rows)

    cache_path = resolved["upstream_13c_morphology_residual_panel_cache"]
    expected_schema = manifest_local_cache_schema(manifest, "morphology_residual_panel")
    observed_schema = schema_hash(cache_path)
    rows.append(
        audit_row(
            "13c_cache.morphology_residual_panel.manifest_schema_hash",
            observed_schema,
            expected_schema if expected_schema else "not_declared",
            (not expected_schema) or observed_schema == expected_schema,
            "upstream_13c_manifest",
        )
    )

    output_map = {
        "upstream_13c_decision": "morphology_orthogonal_residual_importance_decision",
        "upstream_13c_feature_cluster_dictionary": "feature_cluster_dictionary",
        "upstream_13c_sample_uniqueness_audit": "sample_uniqueness_audit",
        "upstream_13c_row_level_rebuild_audit": "row_level_rebuild_audit",
    }
    for path_key, output_id in output_map.items():
        expected_sha = manifest_output_sha(manifest, output_id)
        observed_sha = file_sha(resolved[path_key])
        rows.append(
            audit_row(
                f"13c_output.{output_id}.manifest_sha256",
                observed_sha,
                expected_sha if expected_sha else "not_declared",
                (not expected_sha) or observed_sha == expected_sha,
                "upstream_13c_manifest",
            )
        )
    return pd.DataFrame(rows)


def rebuild_13c_outputs(resolved: dict[str, Path]) -> None:
    config_path = resolved.get("upstream_13c_config", CONFIG_13C_PATH)
    r13c.run(config_path, mode="full")


def input_gate_status(audit: pd.DataFrame) -> tuple[str, str]:
    bad = audit.loc[
        audit["required_flag"].astype(bool)
        & (
            audit["read_status"].astype(str).ne("pass")
            | audit["schema_status"].astype(str).str.startswith("missing_columns")
            | audit["schema_status"].astype(str).eq("read_error")
        )
    ]
    if bad.empty:
        return "pass", ""
    return "fail", ";".join(bad["artifact_id"].astype(str).tolist())


def audit_row(check_id: str, observed: Any, expected: Any, ok: bool, source: str) -> dict[str, Any]:
    return {
        "lineage_check_id": check_id,
        "observed_value": observed,
        "expected_value": expected,
        "status": "pass" if ok else "fail",
        "source_artifact": source,
    }


def first_row_value(frame: pd.DataFrame, column: str, default: Any = "") -> Any:
    if frame.empty or column not in frame.columns:
        return default
    return frame.iloc[0].get(column, default)


def build_upstream_lineage_audit(
    resolved: dict[str, Path],
    config: dict[str, Any],
    allow_rebuild: bool = False,
) -> tuple[pd.DataFrame, str, str]:
    selected = str(config.get("selected_state_id", "repair_range_participation_core_30"))
    rows: list[dict[str, Any]] = []
    expected = [
        ("13a3", "upstream_13a3_decision", "13A3_selected_composite_state_not_supported", {"sequence_mining_authorized": False}),
        ("13c", "upstream_13c_decision", "13C_stop_residual_probability_only_no_utility", {"meta_labeling_authorized": False, "bet_sizing_authorized": False}),
        ("13e", "upstream_13e_decision", "13E_stop_no_nonlinear_auc_improvement", {"meta_labeling_authorized": False, "bet_sizing_authorized": False}),
        ("13f", "upstream_13f_decision", "13F_stop_no_delayed_utility_improvement", {"meta_labeling_authorized": False, "bet_sizing_authorized": False}),
    ]
    for prefix, artifact, decision_state, flags in expected:
        try:
            frame = read_table(resolved[artifact])
            rows.append(audit_row(f"{prefix}.decision_state", first_row_value(frame, "decision_state"), decision_state, first_row_value(frame, "decision_state") == decision_state, artifact))
            rows.append(audit_row(f"{prefix}.selected_state_id", first_row_value(frame, "selected_state_id"), selected, first_row_value(frame, "selected_state_id") == selected, artifact))
            for flag, expected_value in flags.items():
                rows.append(audit_row(f"{prefix}.{flag}", boolish(first_row_value(frame, flag)), expected_value, boolish(first_row_value(frame, flag)) == expected_value, artifact))
        except Exception as exc:
            rows.append(audit_row(f"{prefix}.decision_readable", f"{type(exc).__name__}:{exc}", "readable", False, artifact))

    try:
        panel = pd.read_parquet(resolved["upstream_13c_morphology_residual_panel_cache"])
        split_ok = "split_bucket" in panel.columns and set(SPLITS) <= set(panel["split_bucket"].astype(str))
        selected_ok = selected in panel.columns and bool_series(panel[selected]).any()
        row_key_ok = "row_id" in panel.columns and not panel["row_id"].duplicated().any()
        no_13f_rows_used = True
        rows.extend(
            [
                audit_row("13c_panel.full_split_coverage", ";".join(sorted(set(panel.get("split_bucket", pd.Series(dtype=str)).astype(str)))), "train;validation;robustness", split_ok, "upstream_13c_morphology_residual_panel_cache"),
                audit_row("13c_panel.selected_membership_available", selected if selected_ok else f"missing_or_empty:{selected}", selected, selected_ok, "upstream_13c_morphology_residual_panel_cache"),
                audit_row("13c_panel.row_id_unique", "unique" if row_key_ok else "duplicate_or_missing", "unique", row_key_ok, "upstream_13c_morphology_residual_panel_cache"),
                audit_row("13f.row_membership_used", False, False, no_13f_rows_used, "upstream_13f_decision"),
            ]
        )
    except Exception as exc:
        rows.append(audit_row("13c_panel.readable", f"{type(exc).__name__}:{exc}", "readable", False, "upstream_13c_morphology_residual_panel_cache"))

    try:
        row_audit = read_table(resolved["upstream_13c_row_level_rebuild_audit"])
        status_col = "status" if "status" in row_audit.columns else "row_level_rebuild_gate_status"
        ok = bool(not row_audit.empty and status_col in row_audit.columns and row_audit[status_col].astype(str).eq("pass").all())
        rows.append(audit_row("13c.row_level_rebuild_audit_all_pass", int(row_audit[status_col].astype(str).ne("pass").sum()) if status_col in row_audit.columns else "missing_status_column", 0, ok, "upstream_13c_row_level_rebuild_audit"))
    except Exception as exc:
        rows.append(audit_row("13c.row_level_rebuild_audit_readable", f"{type(exc).__name__}:{exc}", "readable", False, "upstream_13c_row_level_rebuild_audit"))

    rows.extend(build_13c_manifest_audit(resolved).to_dict(orient="records"))
    audit = pd.DataFrame(rows)
    bad = audit.loc[audit["status"].astype(str).ne("pass")]
    cache_bad = bad["lineage_check_id"].astype(str).str.startswith(("13c_manifest.", "13c_cache.", "13c_output.")).any() if len(bad) else False
    if allow_rebuild and cache_bad:
        rebuild_13c_outputs(resolved)
        retry, status, reason = build_upstream_lineage_audit(resolved, config, allow_rebuild=False)
        retry = retry.copy()
        retry["lineage_check_id"] = "post_rebuild." + retry["lineage_check_id"].astype(str)
        rebuild_row = pd.DataFrame(
            [
                audit_row(
                    "13c_cache.rebuild_triggered",
                    "13c_runner_full",
                    "13c_runner_full",
                    True,
                    "upstream_13c_config",
                )
            ]
        )
        retry = pd.concat([rebuild_row, retry], ignore_index=True)
        return retry, status, reason
    return audit, "pass" if bad.empty else "fail", ";".join(bad["lineage_check_id"].astype(str).tolist())


def qfq_path(qfq_dir: Path, instrument: str) -> Path:
    return qfq_dir / f"{instrument}.csv"


def load_qfq_bars(path: Path) -> pd.DataFrame | None:
    if not path.exists():
        return None
    frame = pd.read_csv(path)
    if "date" not in frame.columns:
        return None
    frame = frame.sort_values("date", kind="mergesort").reset_index(drop=True)
    frame["date"] = frame["date"].map(r13a.date_text)
    for col in ["open", "high", "low", "close", "volume", "money", "turnover_rate"]:
        if col in frame.columns:
            frame[col] = finite_numeric(frame[col])
    return frame


def finite_price(value: Any) -> bool:
    try:
        x = float(value)
    except Exception:
        return False
    return bool(np.isfinite(x) and x > 0)


def analysis_exclusion_reason(row: pd.Series, bars: pd.DataFrame | None, max_horizon: int) -> str:
    split = str(row.get("split_bucket", ""))
    if split not in SPLITS:
        return "split_lineage_missing"
    entry_pos_value = row.get("entry_pos")
    entry_pos = int(float(entry_pos_value)) if pd.notna(entry_pos_value) else -1
    if entry_pos < 0:
        return "entry_not_executable"
    if not finite_price(row.get("entry_price", np.nan)):
        return "entry_price_missing"
    if bars is None:
        return "qfq_bar_mapping_missing"
    if entry_pos + max_horizon - 1 >= len(bars):
        return "max_horizon_path_incomplete"
    window = bars.iloc[entry_pos : entry_pos + max_horizon]
    needed = {"high", "low", "close"}
    if window.empty or not needed <= set(window.columns):
        return "qfq_bar_mapping_missing"
    for col in needed:
        if finite_numeric(window[col]).isna().any():
            return "qfq_bar_mapping_missing"
    return ""


def selected_event_mask(panel: pd.DataFrame, selected: str) -> pd.Series:
    native = bool_series(panel["native_scope"]) if "native_scope" in panel.columns else pd.Series(True, index=panel.index)
    selected_mask = bool_series(panel[selected]) if selected in panel.columns else pd.Series(False, index=panel.index)
    entry_executable = bool_series(panel["entry_executable"]) if "entry_executable" in panel.columns else pd.Series(True, index=panel.index)
    return native & selected_mask & entry_executable


def load_raw_event_panel(panel_path: Path, config: dict[str, Any]) -> pd.DataFrame:
    selected = str(config.get("selected_state_id", "repair_range_participation_core_30"))
    panel = pd.read_parquet(panel_path)
    if "split_bucket" not in panel.columns and "split" in panel.columns:
        panel["split_bucket"] = panel["split"].astype(str)
    if selected not in panel.columns:
        raise KeyError(f"missing selected state column: {selected}")
    raw = panel.loc[selected_event_mask(panel, selected)].copy()
    raw["selected_state_id"] = selected
    raw["reference_date"] = raw["reference_date"].map(r13a.date_text)
    raw["entry_date"] = raw["entry_date"].map(r13a.date_text)
    raw["event_id"] = raw["instrument"].astype(str) + "|" + raw["reference_date"].astype(str) + "|" + selected
    raw["entry_pos"] = finite_numeric(raw["entry_pos"])
    raw["entry_price"] = finite_numeric(raw["entry_price"])
    raw = raw.sort_values(["instrument", "entry_pos", "reference_date"], kind="mergesort").reset_index(drop=True)
    return raw


def label_grid(config: dict[str, Any]) -> list[tuple[float, float, int]]:
    grid = config.get("label_grid", {})
    ups = [float(x) for x in grid.get("up_mfe_threshold_grid", [0.20, 0.30, 0.50])]
    downs = [float(x) for x in grid.get("down_mae_threshold_grid", [-0.10, -0.15, -0.20])]
    horizons = [int(x) for x in grid.get("horizon_sessions_grid", [20, 60, 120])]
    return [(u, d, h) for u in ups for d in downs for h in horizons]


def primary_endpoint(config: dict[str, Any]) -> tuple[float, float, int, str]:
    grid = config.get("label_grid", {})
    up = float(grid.get("primary_up_threshold", 0.30))
    down = float(grid.get("primary_down_threshold", -0.15))
    horizon = int(grid.get("primary_horizon_sessions", 60))
    return up, down, horizon, endpoint_id(up, down, horizon)


def endpoint_id(up: float, down: float, horizon: int) -> str:
    up_text = str(up).replace(".", "p")
    down_text = str(abs(down)).replace(".", "p")
    return f"up_{up_text}_before_down_m{down_text}_H{horizon}"


def compute_one_label(row: pd.Series, bars: pd.DataFrame | None, up: float, down: float, horizon: int) -> dict[str, Any]:
    entry_pos = int(float(row.get("entry_pos"))) if pd.notna(row.get("entry_pos")) else -1
    entry_price = float(row.get("entry_price", np.nan))
    base = {
        "mfe_return": np.nan,
        "mae_return": np.nan,
        "terminal_return": np.nan,
        "upper_hit": False,
        "lower_hit": False,
        "time_to_upper_sessions": np.nan,
        "time_to_lower_sessions": np.nan,
        "first_touch_side": "not_evaluable",
        "winner_before_fail": False,
        "fail_before_winner": False,
        "survive_without_fail": False,
        "opportunity_without_fail": False,
        "upper_first_winner_before_fail": False,
        "upper_first_fail_before_winner": False,
        "upper_first_opportunity_without_fail": False,
        "same_bar_ambiguous": False,
        "evaluable_flag": False,
        "not_evaluable_reason": "",
    }
    if bars is None:
        base["not_evaluable_reason"] = "qfq_bar_mapping_missing"
        return base
    if entry_pos < 0:
        base["not_evaluable_reason"] = "entry_not_executable"
        return base
    if not finite_price(entry_price):
        base["not_evaluable_reason"] = "entry_price_missing"
        return base
    if entry_pos + horizon - 1 >= len(bars):
        base["not_evaluable_reason"] = "max_horizon_path_incomplete"
        return base
    window = bars.iloc[entry_pos : entry_pos + horizon]
    needed = {"high", "low", "close"}
    if window.empty or not needed <= set(window.columns):
        base["not_evaluable_reason"] = "qfq_bar_mapping_missing"
        return base
    highs = finite_numeric(window["high"])
    lows = finite_numeric(window["low"])
    closes = finite_numeric(window["close"])
    if highs.isna().any() or lows.isna().any() or closes.isna().any():
        base["not_evaluable_reason"] = "qfq_bar_mapping_missing"
        return base
    upper_price = entry_price * (1.0 + up)
    lower_price = entry_price * (1.0 + down)
    upper_hits = highs.ge(upper_price).to_numpy()
    lower_hits = lows.le(lower_price).to_numpy()
    upper_hit = bool(upper_hits.any())
    lower_hit = bool(lower_hits.any())
    upper_t = int(np.argmax(upper_hits) + 1) if upper_hit else np.nan
    lower_t = int(np.argmax(lower_hits) + 1) if lower_hit else np.nan
    same_bar = bool(upper_hit and lower_hit and upper_t == lower_t)
    if lower_hit and (not upper_hit or lower_t <= upper_t):
        side = "lower"
    elif upper_hit:
        side = "upper"
    else:
        side = "vertical"
    winner_before_fail = bool(upper_hit and (not lower_hit or upper_t < lower_t))
    fail_before_winner = bool(lower_hit and (not upper_hit or lower_t <= upper_t))
    upper_first_winner_before_fail = bool(upper_hit and (not lower_hit or upper_t <= lower_t))
    upper_first_fail_before_winner = bool(lower_hit and (not upper_hit or lower_t < upper_t))
    base.update(
        {
            "mfe_return": float(highs.max() / entry_price - 1.0),
            "mae_return": float(lows.min() / entry_price - 1.0),
            "terminal_return": float(closes.iloc[-1] / entry_price - 1.0),
            "upper_hit": upper_hit,
            "lower_hit": lower_hit,
            "time_to_upper_sessions": float(upper_t) if upper_hit else np.nan,
            "time_to_lower_sessions": float(lower_t) if lower_hit else np.nan,
            "first_touch_side": side,
            "winner_before_fail": winner_before_fail,
            "fail_before_winner": fail_before_winner,
            "survive_without_fail": not lower_hit,
            "opportunity_without_fail": bool(upper_hit and not fail_before_winner),
            "upper_first_winner_before_fail": upper_first_winner_before_fail,
            "upper_first_fail_before_winner": upper_first_fail_before_winner,
            "upper_first_opportunity_without_fail": bool(upper_hit and not upper_first_fail_before_winner),
            "same_bar_ambiguous": same_bar,
            "evaluable_flag": True,
            "not_evaluable_reason": "",
        }
    )
    return base


def reconstruct_label_panel(
    raw_events: pd.DataFrame,
    qfq_dir: Path,
    config: dict[str, Any],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    max_h = int(config.get("label_grid", {}).get("max_horizon_sessions", 120))
    rows: list[dict[str, Any]] = []
    analysis_flags: dict[str, bool] = {}
    exclusion: dict[str, str] = {}
    bar_cache: dict[str, pd.DataFrame | None] = {}
    for inst, sub in raw_events.groupby(raw_events["instrument"].astype(str), sort=False):
        bars = load_qfq_bars(qfq_path(qfq_dir, inst))
        bar_cache[inst] = bars
        for _, row in sub.iterrows():
            event_id = str(row["event_id"])
            reason = analysis_exclusion_reason(row, bars, max_h)
            complete = reason == ""
            analysis_flags[event_id] = complete
            if not complete:
                exclusion[event_id] = reason
            for up, down, horizon in label_grid(config):
                payload = compute_one_label(row, bars, up, down, horizon)
                rows.append(
                    {
                        "event_id": event_id,
                        "row_id": row.get("row_id", np.nan),
                        "instrument": row.get("instrument"),
                        "reference_date": row.get("reference_date"),
                        "entry_date": row.get("entry_date"),
                        "entry_pos": row.get("entry_pos"),
                        "entry_price": row.get("entry_price"),
                        "split_bucket": row.get("split_bucket"),
                        "selected_state_id": row.get("selected_state_id"),
                        "up_threshold": up,
                        "down_threshold": down,
                        "horizon_sessions": horizon,
                        "endpoint_id": endpoint_id(up, down, horizon),
                        "analysis_denominator_flag": complete,
                        **payload,
                    }
                )
    panel = pd.DataFrame(rows)
    event_status = raw_events[["event_id", "instrument", "reference_date", "entry_date", "entry_pos", "entry_price", "split_bucket", "selected_state_id"]].copy()
    event_status["analysis_denominator_flag"] = event_status["event_id"].map(analysis_flags).fillna(False).astype(bool)
    event_status["analysis_exclusion_reason"] = event_status["event_id"].map(exclusion).fillna("")
    return panel, event_status


def build_row_level_rebuild_audit(raw_events: pd.DataFrame, event_status: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    selected = str(config.get("selected_state_id", "repair_range_participation_core_30"))
    rows = []
    for split in SPLITS:
        raw_n = int(raw_events["split_bucket"].astype(str).eq(split).sum())
        split_status = event_status.loc[event_status["split_bucket"].astype(str).eq(split)]
        analysis_n = int(split_status["analysis_denominator_flag"].sum())
        frac = analysis_n / raw_n if raw_n else 0.0
        row = {
            "selected_state_id": selected,
            "split_bucket": split,
            "raw_event_n": raw_n,
            "analysis_event_n": analysis_n,
            "analysis_event_fraction": frac,
        }
        row.update(
            {
                f"{reason}_n": int(split_status["analysis_exclusion_reason"].astype(str).eq(reason).sum())
                for reason in NOT_EVALUABLE_REASONS
            }
        )
        row.update(
            {
                "selected_membership_source": "13C_full_split_morphology_residual_panel",
                "13f_row_level_used": False,
                "row_level_rebuild_gate_status": "pass",
            }
        )
        rows.append(row)
    return pd.DataFrame(rows)


def denominator_gate_status(row_audit: pd.DataFrame, config: dict[str, Any]) -> tuple[str, str]:
    label_cfg = config.get("label_grid", {})
    min_frac = float(label_cfg.get("min_analysis_event_fraction_by_split", 0.80))
    min_n_cfg = label_cfg.get("min_analysis_event_n_by_split", {})
    reasons = []
    for _, row in row_audit.iterrows():
        split = str(row["split_bucket"])
        min_n = int(min_n_cfg.get(split, 100))
        if float(row["analysis_event_fraction"]) < min_frac:
            reasons.append(f"{split}.analysis_event_fraction_below_min")
        if int(row["analysis_event_n"]) < min_n:
            reasons.append(f"{split}.analysis_event_n_below_min")
    return ("pass", "") if not reasons else ("fail", ";".join(reasons))


def split_counts(raw_events: pd.DataFrame, event_status: pd.DataFrame, split: str) -> tuple[int, int]:
    raw_n = int(raw_events["split_bucket"].astype(str).eq(split).sum())
    analysis_n = int((event_status["split_bucket"].astype(str).eq(split) & event_status["analysis_denominator_flag"]).sum())
    return raw_n, analysis_n


def build_label_grid_readout(label_panel: pd.DataFrame, raw_events: pd.DataFrame, event_status: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for split in SPLITS:
        raw_n, analysis_n = split_counts(raw_events, event_status, split)
        split_status = event_status.loc[event_status["split_bucket"].astype(str).eq(split)]
        reason_counts = {
            f"{reason}_n": int(split_status["analysis_exclusion_reason"].astype(str).eq(reason).sum())
            for reason in NOT_EVALUABLE_REASONS
        }
        for (up, down, horizon), sub in label_panel.loc[label_panel["split_bucket"].astype(str).eq(split)].groupby(
            ["up_threshold", "down_threshold", "horizon_sessions"],
            sort=True,
        ):
            analysis = sub.loc[sub["analysis_denominator_flag"].astype(bool) & sub["evaluable_flag"].astype(bool)]
            denom = analysis_n
            upper_hit_n = int(bool_series(analysis["upper_hit"]).sum()) if len(analysis) else 0
            lower_hit_n = int(bool_series(analysis["lower_hit"]).sum()) if len(analysis) else 0
            winner_n = int(bool_series(analysis["winner_before_fail"]).sum()) if len(analysis) else 0
            fail_n = int(bool_series(analysis["fail_before_winner"]).sum()) if len(analysis) else 0
            survive_n = int(bool_series(analysis["survive_without_fail"]).sum()) if len(analysis) else 0
            opportunity_n = int(bool_series(analysis["opportunity_without_fail"]).sum()) if len(analysis) else 0
            upper_first_winner_n = int(bool_series(analysis["upper_first_winner_before_fail"]).sum()) if len(analysis) else 0
            upper_first_fail_n = int(bool_series(analysis["upper_first_fail_before_winner"]).sum()) if len(analysis) else 0
            same_bar_n = int(bool_series(analysis["same_bar_ambiguous"]).sum()) if len(analysis) else 0
            winner_rate = winner_n / denom if denom else np.nan
            fail_rate = fail_n / denom if denom else np.nan
            upper_first_winner_rate = upper_first_winner_n / denom if denom else np.nan
            upper_first_fail_rate = upper_first_fail_n / denom if denom else np.nan
            rows.append(
                {
                    "split_bucket": split,
                    "up_threshold": up,
                    "down_threshold": down,
                    "horizon_sessions": horizon,
                    "endpoint_id": endpoint_id(float(up), float(down), int(horizon)),
                    "raw_event_n": raw_n,
                    "analysis_event_n": analysis_n,
                    "analysis_event_fraction": analysis_n / raw_n if raw_n else 0.0,
                    "evaluable_n": int(len(analysis)),
                    "not_evaluable_n": int(raw_n - analysis_n),
                    **reason_counts,
                    "rate_denominator": denom,
                    "upper_hit_rate": upper_hit_n / denom if denom else np.nan,
                    "lower_hit_rate": lower_hit_n / denom if denom else np.nan,
                    "winner_before_fail_rate": winner_rate,
                    "fail_before_winner_rate": fail_rate,
                    "survive_without_fail_rate": survive_n / denom if denom else np.nan,
                    "opportunity_without_fail_rate": opportunity_n / denom if denom else np.nan,
                    "upper_first_winner_before_fail_rate": upper_first_winner_rate,
                    "upper_first_fail_before_winner_rate": upper_first_fail_rate,
                    "upper_first_minus_lower_first_winner_rate_delta": upper_first_winner_rate - winner_rate if denom else np.nan,
                    "upper_first_minus_lower_first_fail_rate_delta": upper_first_fail_rate - fail_rate if denom else np.nan,
                    "median_time_to_upper": float(finite_numeric(analysis["time_to_upper_sessions"]).median()) if len(analysis) else np.nan,
                    "median_time_to_lower": float(finite_numeric(analysis["time_to_lower_sessions"]).median()) if len(analysis) else np.nan,
                    "terminal_return_mean": float(finite_numeric(analysis["terminal_return"]).mean()) if len(analysis) else np.nan,
                    "mfe_return_mean": float(finite_numeric(analysis["mfe_return"]).mean()) if len(analysis) else np.nan,
                    "mae_return_mean": float(finite_numeric(analysis["mae_return"]).mean()) if len(analysis) else np.nan,
                    "same_bar_ambiguous_rate": same_bar_n / denom if denom else np.nan,
                }
            )
    return pd.DataFrame(rows)


def build_time_to_hit_distribution(label_panel: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for keys, sub in label_panel.loc[label_panel["analysis_denominator_flag"].astype(bool)].groupby(
        ["split_bucket", "up_threshold", "down_threshold", "horizon_sessions"],
        sort=True,
    ):
        split, up, down, horizon = keys
        for side, col in [("upper", "time_to_upper_sessions"), ("lower", "time_to_lower_sessions")]:
            vals = finite_numeric(sub[col]).dropna()
            rows.append(
                {
                    "split_bucket": split,
                    "up_threshold": up,
                    "down_threshold": down,
                    "horizon_sessions": horizon,
                    "touch_side": side,
                    "touch_n": int(len(vals)),
                    "median_time_to_hit": float(vals.median()) if len(vals) else np.nan,
                    "p25_time_to_hit": float(vals.quantile(0.25)) if len(vals) else np.nan,
                    "p75_time_to_hit": float(vals.quantile(0.75)) if len(vals) else np.nan,
                }
            )
    return pd.DataFrame(rows)


def assign_bucket(values: pd.Series, train_values: pd.Series, labels: tuple[str, str, str], high_direction: str = "high") -> tuple[pd.Series, dict[str, Any]]:
    train = finite_numeric(train_values).dropna()
    result = pd.Series("missing", index=values.index, dtype=object)
    if train.empty:
        return result, {"q33": np.nan, "q66": np.nan, "direction": high_direction}
    q33 = float(train.quantile(1 / 3))
    q66 = float(train.quantile(2 / 3))
    vals = finite_numeric(values)
    if high_direction == "low":
        result.loc[vals <= q33] = labels[2]
        result.loc[(vals > q33) & (vals <= q66)] = labels[1]
        result.loc[vals > q66] = labels[0]
    else:
        result.loc[vals <= q33] = labels[0]
        result.loc[(vals > q33) & (vals <= q66)] = labels[1]
        result.loc[vals > q66] = labels[2]
    result.loc[vals.isna()] = "missing"
    return result, {"q33": q33, "q66": q66, "direction": high_direction}


def assign_count_bucket(values: pd.Series, train_values: pd.Series) -> tuple[pd.Series, dict[str, Any]]:
    train = finite_numeric(train_values).dropna()
    vals = finite_numeric(values)
    out = pd.Series("missing", index=values.index, dtype=object)
    if train.empty:
        return out, {"q33": np.nan, "p80": np.nan, "direction": "high"}
    q33 = float(train.quantile(1 / 3))
    p80 = float(train.quantile(0.80))
    out.loc[vals < q33] = "low"
    out.loc[(vals >= q33) & (vals < p80)] = "medium"
    out.loc[vals >= p80] = "high"
    out.loc[vals.isna()] = "missing"
    return out, {"q33": q33, "p80": p80, "direction": "high"}


def liquidity_or_turnover_source(frame: pd.DataFrame) -> str:
    for col in [
        "turnover_zscore_20d",
        "amount_ratio_5d_20d",
        "turnover_rate_median_20d",
        "liquidity_metric_decile",
    ]:
        if col in frame.columns:
            return col
    return ""


def add_t0_known_crowding(raw_events: pd.DataFrame, events: pd.DataFrame) -> pd.DataFrame:
    raw = raw_events[["event_id", "instrument", "reference_date", "entry_pos"]].copy()
    raw["entry_pos"] = finite_numeric(raw["entry_pos"])
    counts: dict[str, dict[str, float]] = {}
    market_counts = raw.groupby(raw["reference_date"].astype(str))["event_id"].count().to_dict()
    for inst, sub in raw.sort_values(["instrument", "entry_pos"], kind="mergesort").groupby("instrument", sort=False):
        prior_positions: list[float] = []
        prior_end_positions: list[float] = []
        prior_event_ids: list[str] = []
        for _, row in sub.iterrows():
            pos = float(row["entry_pos"])
            prior20 = sum(1 for p in prior_positions if pos - p <= 20 and p < pos)
            active120 = sum(1 for p, end in zip(prior_positions, prior_end_positions) if p < pos <= end)
            counts[str(row["event_id"])] = {
                "t0_prior_selected_event_count_20d": float(prior20),
                "t0_active_selected_event_count_120d": float(active120),
                "t0_market_selected_event_count_today": float(market_counts.get(str(row["reference_date"]), 0)),
            }
            prior_positions.append(pos)
            prior_end_positions.append(pos + 119)
            prior_event_ids.append(str(row["event_id"]))
    out = events.copy()
    for col in [
        "t0_prior_selected_event_count_20d",
        "t0_active_selected_event_count_120d",
        "t0_market_selected_event_count_today",
    ]:
        out[col] = out["event_id"].map({k: v[col] for k, v in counts.items()})
    return out


def build_rule_overlay(events: pd.DataFrame, raw_events: pd.DataFrame, config: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame, str, str]:
    analysis = events.loc[events["analysis_denominator_flag"].astype(bool)].copy()
    analysis = add_t0_known_crowding(raw_events, analysis)
    train_mask = analysis["split_bucket"].astype(str).eq("train")
    dictionary_rows: list[dict[str, Any]] = []

    feature_specs = [
        ("ret_20d", "t0_ret_20d_bucket", ("weak", "flat", "positive"), "high", "13C_column_train_frozen"),
        ("max_drawdown_20d", "t0_max_drawdown_20d_bucket", ("mild", "moderate", "severe"), "low", "13C_column_train_frozen"),
        ("distance_from_20d_low", "t0_distance_to_20d_low_bucket", ("near_low", "mid", "far_from_low"), "high", "13C_column_train_frozen"),
        ("volatility_20d", "t0_volatility_20d_bucket", ("low", "medium", "high"), "high", "13C_column_train_frozen"),
    ]
    liquidity_source = liquidity_or_turnover_source(analysis)
    if liquidity_source:
        feature_specs.append(
            (
                liquidity_source,
                "t0_liquidity_or_turnover_bucket",
                ("low", "medium", "high"),
                "high",
                "13C_liquidity_or_turnover_train_frozen",
            )
        )
    for source, bucket_col, labels, direction, threshold_source in feature_specs:
        source_values = analysis[source] if source in analysis.columns else pd.Series(np.nan, index=analysis.index)
        bucket, meta = assign_bucket(source_values, source_values.loc[train_mask], labels, direction)
        analysis[bucket_col] = bucket
        dictionary_rows.append(
            {
                "rule_feature_id": bucket_col,
                "source_column": source,
                "bucket_labels": "|".join(labels),
                "threshold_q33": meta.get("q33"),
                "threshold_q66_or_p80": meta.get("q66"),
                "direction": meta.get("direction"),
                "train_row_count": int(source_values.loc[train_mask].notna().sum()),
                "threshold_source": threshold_source,
            }
        )

    for source, bucket_col in [
        ("t0_prior_selected_event_count_20d", "t0_prior_selected_event_count_20d_bucket"),
        ("t0_active_selected_event_count_120d", "t0_active_selected_event_count_120d_bucket"),
        ("t0_market_selected_event_count_today", "t0_market_selected_event_count_today_bucket"),
    ]:
        bucket, meta = assign_count_bucket(analysis[source], analysis.loc[train_mask, source])
        analysis[bucket_col] = bucket
        dictionary_rows.append(
            {
                "rule_feature_id": bucket_col,
                "source_column": source,
                "bucket_labels": "low|medium|high",
                "threshold_q33": meta.get("q33"),
                "threshold_q66_or_p80": meta.get("p80"),
                "direction": "high",
                "train_row_count": int(analysis.loc[train_mask, source].notna().sum()),
                "threshold_source": "train_frozen_p80",
            }
        )

    analysis["t0_compression_repair_feature_cluster_status"] = "neutral"
    dictionary_rows.append(
        {
            "rule_feature_id": "t0_compression_repair_feature_cluster_status",
            "source_column": "13C_feature_cluster_dictionary",
            "bucket_labels": "neutral",
            "threshold_q33": np.nan,
            "threshold_q66_or_p80": np.nan,
            "direction": "neutral_fallback",
            "train_row_count": int(train_mask.sum()),
            "threshold_source": "neutral_fallback_no_non_outcome_direction",
        }
    )

    required_buckets = [
        "t0_ret_20d_bucket",
        "t0_max_drawdown_20d_bucket",
        "t0_distance_to_20d_low_bucket",
        "t0_volatility_20d_bucket",
        "t0_prior_selected_event_count_20d_bucket",
        "t0_active_selected_event_count_120d_bucket",
        "t0_market_selected_event_count_today_bucket",
    ]
    if liquidity_source:
        required_buckets.append("t0_liquidity_or_turnover_bucket")
    missing_mask = analysis[required_buckets].eq("missing").any(axis=1)
    badside_points = (
        analysis["t0_max_drawdown_20d_bucket"].eq("severe").astype(int)
        + analysis["t0_distance_to_20d_low_bucket"].eq("near_low").astype(int)
        + analysis["t0_volatility_20d_bucket"].eq("high").astype(int)
        + analysis["t0_ret_20d_bucket"].eq("weak").astype(int)
    )
    analysis["badside_risk_context"] = np.select(
        [badside_points >= 2, badside_points.eq(1)],
        ["high", "medium"],
        default="low",
    )
    opportunity_high = (
        analysis["t0_ret_20d_bucket"].isin(["flat", "positive"])
        & analysis["t0_distance_to_20d_low_bucket"].isin(["mid", "far_from_low"])
        & ~analysis["t0_max_drawdown_20d_bucket"].eq("severe")
        & ~analysis["t0_compression_repair_feature_cluster_status"].eq("unfavorable")
    )
    opportunity_medium = analysis["t0_ret_20d_bucket"].isin(["flat", "positive"]) | analysis[
        "t0_distance_to_20d_low_bucket"
    ].isin(["mid", "far_from_low"])
    analysis["opportunity_context"] = np.select(
        [opportunity_high, opportunity_medium],
        ["high", "medium"],
        default="low",
    )
    crowded = (
        analysis["t0_prior_selected_event_count_20d_bucket"].eq("high")
        | analysis["t0_active_selected_event_count_120d_bucket"].eq("high")
        | analysis["t0_market_selected_event_count_today_bucket"].eq("high")
    )
    analysis["t0_known_crowding_context"] = np.where(crowded, "crowded", "normal")
    action = pd.Series("keep", index=analysis.index, dtype=object)
    action.loc[analysis["badside_risk_context"].eq("high") & ~analysis["opportunity_context"].eq("high")] = "skip"
    action.loc[action.eq("keep") & (analysis["badside_risk_context"].eq("medium") | analysis["t0_known_crowding_context"].eq("crowded"))] = "reduce"
    action.loc[action.eq("keep") & analysis["opportunity_context"].eq("high") & analysis["badside_risk_context"].eq("low") & ~analysis["t0_known_crowding_context"].eq("crowded")] = "increase"
    action.loc[missing_mask] = "keep"
    analysis["action"] = action
    multipliers = {str(k): float(v) for k, v in config.get("overlay", {}).get("risk_budget_multiplier", {}).items()}
    if not multipliers:
        multipliers = {"increase": 1.5, "keep": 1.0, "reduce": 0.5, "skip": 0.0}
    analysis["risk_budget_multiplier"] = analysis["action"].map(multipliers).astype(float)
    analysis["rule_feature_missing_caveat"] = missing_mask
    feature_missing_fraction = float(missing_mask.mean()) if len(analysis) else 1.0
    max_missing = float(config.get("overlay", {}).get("rule_feature_missing_max_fraction", 0.05))
    status = "pass" if feature_missing_fraction <= max_missing else "fail"
    reason = "" if status == "pass" else "rule_feature_missing_fraction_exceeds_max"
    dictionary = pd.DataFrame(dictionary_rows)
    dictionary["validation_used_for_rule_freeze"] = False
    dictionary["robustness_used_for_rule_freeze"] = False
    dictionary["ml_model_used"] = False
    dictionary["hyperparameter_search_used"] = False
    dictionary["rule_feature_missing_fraction"] = feature_missing_fraction
    dictionary["rule_freeze_gate_status"] = status
    return analysis, dictionary, status, reason


def label_primary(label_panel: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    up, down, horizon, _endpoint = primary_endpoint(config)
    return label_panel.loc[
        label_panel["analysis_denominator_flag"].astype(bool)
        & np.isclose(finite_numeric(label_panel["up_threshold"]), up)
        & np.isclose(finite_numeric(label_panel["down_threshold"]), down)
        & finite_numeric(label_panel["horizon_sessions"]).eq(horizon)
    ].copy()


def attach_primary_labels(overlay: pd.DataFrame, label_panel: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    primary = label_primary(label_panel, config)
    cols = [
        "event_id",
        "up_threshold",
        "down_threshold",
        "horizon_sessions",
        "mfe_return",
        "mae_return",
        "terminal_return",
        "upper_hit",
        "lower_hit",
        "time_to_upper_sessions",
        "time_to_lower_sessions",
        "first_touch_side",
        "winner_before_fail",
        "fail_before_winner",
        "survive_without_fail",
        "opportunity_without_fail",
        "same_bar_ambiguous",
    ]
    return overlay.merge(primary[cols], on="event_id", how="left", validate="one_to_one")


def event_density_per_instrument_year(events: pd.DataFrame) -> float:
    if events.empty:
        return np.nan
    reference_dates = pd.to_datetime(events["reference_date"], errors="coerce")
    if reference_dates.notna().sum() == 0:
        return np.nan
    years = max(1e-9, (reference_dates.max() - reference_dates.min()).days / 365.25)
    instrument_n = max(1, int(events["instrument"].nunique()))
    return float(len(events) / (instrument_n * years))


def compute_event_uniqueness(overlay: pd.DataFrame, config: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame]:
    max_h = int(config.get("label_grid", {}).get("max_horizon_sessions", 120))
    out = overlay.copy()
    out["event_span_start_pos"] = finite_numeric(out["entry_pos"])
    out["event_span_end_pos"] = out["event_span_start_pos"] + max_h - 1
    uniqueness_values: dict[str, float] = {}
    duplicate_flags: dict[str, bool] = {}
    concurrency_p90_by_split: dict[str, float] = {}
    for inst, sub in out.sort_values(["instrument", "event_span_start_pos"], kind="mergesort").groupby("instrument", sort=False):
        counts: dict[int, int] = {}
        intervals = []
        for _, row in sub.iterrows():
            start = int(row["event_span_start_pos"])
            end = int(row["event_span_end_pos"])
            intervals.append((str(row["event_id"]), start, end))
            for pos in range(start, end + 1):
                counts[pos] = counts.get(pos, 0) + 1
        prior_ends: list[int] = []
        for event_id, start, end in intervals:
            vals = [1.0 / counts[pos] for pos in range(start, end + 1) if counts.get(pos, 0) > 0]
            uniqueness_values[event_id] = float(np.mean(vals)) if vals else np.nan
            duplicate_flags[event_id] = any(prior_end >= start for prior_end in prior_ends)
            prior_ends.append(end)
    out["average_uniqueness"] = out["event_id"].map(uniqueness_values)
    out["ex_post_duplicate_episode_flag"] = out["event_id"].map(duplicate_flags).fillna(False).astype(bool)

    rows = []
    for split in SPLITS:
        sub = out.loc[out["split_bucket"].astype(str).eq(split)]
        if sub.empty:
            rows.append({"split_bucket": split, "event_n": 0, "event_uniqueness_gate_status": "fail"})
            continue
        rows.append(
            {
                "split_bucket": split,
                "event_n": int(len(sub)),
                "average_uniqueness": float(finite_numeric(sub["average_uniqueness"]).mean()),
                "median_uniqueness": float(finite_numeric(sub["average_uniqueness"]).median()),
                "p10_uniqueness": float(finite_numeric(sub["average_uniqueness"]).quantile(0.10)),
                "p90_concurrency": float((1.0 / finite_numeric(sub["average_uniqueness"]).replace(0, np.nan)).quantile(0.90)),
                "event_density_per_instrument_year": event_density_per_instrument_year(sub),
                "rolling_20d_event_count_mean": float(finite_numeric(sub["t0_prior_selected_event_count_20d"]).mean()),
                "rolling_20d_event_count_p95": float(finite_numeric(sub["t0_prior_selected_event_count_20d"]).quantile(0.95)),
                "duplicate_episode_event_count": int(sub["ex_post_duplicate_episode_flag"].sum()),
                "duplicate_episode_fraction": float(sub["ex_post_duplicate_episode_flag"].mean()),
                "event_uniqueness_gate_status": "pass" if finite_numeric(sub["average_uniqueness"]).notna().all() else "fail",
            }
        )
    audit = pd.DataFrame(rows)
    status = "pass" if audit["event_uniqueness_gate_status"].astype(str).eq("pass").all() else "fail"
    return out, audit.assign(event_uniqueness_overall_gate_status=status)


def path_utility(row: pd.Series, cost: float) -> float:
    if bool(row.get("winner_before_fail", False)):
        return float(row.get("up_threshold", np.nan)) - cost
    if bool(row.get("fail_before_winner", False)):
        return float(row.get("down_threshold", np.nan)) - cost
    terminal = float(row.get("terminal_return", np.nan))
    return terminal - cost if np.isfinite(terminal) else np.nan


def horizon_exposure_days(row: pd.Series, primary_horizon: int) -> float:
    side = str(row.get("first_touch_side", "vertical"))
    if side == "upper" and pd.notna(row.get("time_to_upper_sessions")):
        return float(np.clip(float(row["time_to_upper_sessions"]), 1, primary_horizon))
    if side == "lower" and pd.notna(row.get("time_to_lower_sessions")):
        return float(np.clip(float(row["time_to_lower_sessions"]), 1, primary_horizon))
    return float(primary_horizon)


def build_overlay_utility(overlay_with_labels: pd.DataFrame, config: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, str, str, str, str]:
    out = overlay_with_labels.copy()
    overlay_cfg = config.get("overlay", {})
    cost_tiers = [int(x) for x in overlay_cfg.get("cost_tier_bps", [0, 50, 100])]
    cost_buffer = {int(k): float(v) for k, v in overlay_cfg.get("cost_buffer_return_by_tier", {0: 0.0, 50: 0.005, 100: 0.01}).items()}
    adjust_cost = {int(k): float(v) for k, v in overlay_cfg.get("overlay_adjustment_cost_buffer_by_tier", cost_buffer).items()}
    primary_h = int(config.get("label_grid", {}).get("primary_horizon_sessions", 60))
    out["horizon_exposure_days"] = out.apply(lambda row: horizon_exposure_days(row, primary_h), axis=1)
    for tier in cost_tiers:
        c = cost_buffer.get(tier, tier / 10000.0)
        ac = adjust_cost.get(tier, c)
        base_col = f"baseline_per_event_utility_{tier}bps"
        over_col = f"overlay_per_event_utility_{tier}bps"
        path_col = f"primary_path_utility_component_{tier}bps"
        adjust_col = f"overlay_adjustment_cost_component_{tier}bps"
        out[path_col] = out.apply(lambda row: path_utility(row, c), axis=1)
        out[base_col] = out[path_col]
        out[adjust_col] = (out["risk_budget_multiplier"] - 1.0).abs() * ac
        out[over_col] = out["risk_budget_multiplier"] * out[path_col] - out[adjust_col]

    rows = []
    retention_rows = []
    for split in SPLITS:
        sub = out.loc[out["split_bucket"].astype(str).eq(split)]
        event_n = int(len(sub))
        winner_n = int(bool_series(sub["winner_before_fail"]).sum()) if event_n else 0
        badside_n = int(bool_series(sub["fail_before_winner"]).sum()) if event_n else 0
        winner_retained = int((bool_series(sub["winner_before_fail"]) & sub["action"].isin(["increase", "keep"])).sum()) if event_n else 0
        badside_avoided = int((bool_series(sub["fail_before_winner"]) & sub["action"].isin(["reduce", "skip"])).sum()) if event_n else 0
        min_badside = int(overlay_cfg.get("min_badside_event_n_by_split", 30))
        badside_caveat = badside_n < min_badside
        winner_caveat = winner_n == 0
        base_days = float((1.0 * finite_numeric(sub["horizon_exposure_days"])).sum()) if event_n else np.nan
        overlay_days = float((finite_numeric(sub["risk_budget_multiplier"]) * finite_numeric(sub["horizon_exposure_days"])).sum()) if event_n else np.nan
        row = {
            "split_bucket": split,
            "raw_event_n": event_n,
            "analysis_event_n": event_n,
            "analysis_event_fraction": 1.0,
            "rate_denominator": event_n,
            "baseline_exposure_mean": 1.0,
            "overlay_exposure_mean": float(finite_numeric(sub["risk_budget_multiplier"]).mean()) if event_n else np.nan,
            "badside_avoided_rate": badside_avoided / badside_n if badside_n else np.nan,
            "winner_opportunity_retained_rate": winner_retained / winner_n if winner_n else np.nan,
            "badside_support_caveat": badside_caveat,
            "winner_retention_support_caveat": winner_caveat,
            "increase_fraction": float(sub["action"].eq("increase").mean()) if event_n else np.nan,
            "keep_fraction": float(sub["action"].eq("keep").mean()) if event_n else np.nan,
            "reduce_fraction": float(sub["action"].eq("reduce").mean()) if event_n else np.nan,
            "skip_fraction": float(sub["action"].eq("skip").mean()) if event_n else np.nan,
            "average_uniqueness": float(finite_numeric(sub["average_uniqueness"]).mean()) if event_n else np.nan,
            "event_density_per_instrument_year": event_density_per_instrument_year(sub),
        }
        for tier in cost_tiers:
            base_col = f"baseline_per_event_utility_{tier}bps"
            over_col = f"overlay_per_event_utility_{tier}bps"
            row[f"baseline_utility_per_event_mean_{tier}bps"] = float(finite_numeric(sub[base_col]).mean()) if event_n else np.nan
            row[f"overlay_utility_per_event_mean_{tier}bps"] = float(finite_numeric(sub[over_col]).mean()) if event_n else np.nan
            row[f"delta_overlay_vs_baseline_{tier}bps"] = row[f"overlay_utility_per_event_mean_{tier}bps"] - row[f"baseline_utility_per_event_mean_{tier}bps"]
        row["baseline_exposure_day_return_50bps"] = float(finite_numeric(sub["baseline_per_event_utility_50bps"]).sum() / base_days) if base_days and base_days > 0 else np.nan
        row["overlay_exposure_day_return_50bps"] = float(finite_numeric(sub["overlay_per_event_utility_50bps"]).sum() / overlay_days) if overlay_days and overlay_days > 0 else np.nan
        rows.append(row)
        retention_rows.append(
            {
                "split_bucket": split,
                "winner_before_fail_n": winner_n,
                "winner_retained_n": winner_retained,
                "winner_opportunity_retained_rate": row["winner_opportunity_retained_rate"],
                "fail_before_winner_n": badside_n,
                "badside_avoided_n": badside_avoided,
                "badside_avoided_rate": row["badside_avoided_rate"],
                "badside_support_caveat": badside_caveat,
                "winner_retention_support_caveat": winner_caveat,
            }
        )
    readout = pd.DataFrame(rows)
    retention = pd.DataFrame(retention_rows)

    def row_for(split: str) -> pd.Series:
        rows_for_split = readout.loc[readout["split_bucket"].astype(str).eq(split)]
        return rows_for_split.iloc[0] if not rows_for_split.empty else pd.Series(dtype=object)

    train = row_for("train")
    val = row_for("validation")
    rob = row_for("robustness")
    overlay_status = "pass" if (
        float(train.get("delta_overlay_vs_baseline_50bps", np.nan)) > 0
        and float(val.get("delta_overlay_vs_baseline_50bps", np.nan)) > 0
        and float(rob.get("delta_overlay_vs_baseline_50bps", np.nan)) >= 0
        and float(val.get("overlay_exposure_day_return_50bps", np.nan)) > float(val.get("baseline_exposure_day_return_50bps", np.nan))
        and float(rob.get("overlay_exposure_day_return_50bps", np.nan)) >= float(rob.get("baseline_exposure_day_return_50bps", np.nan))
    ) else "fail"
    winner_status = "pass" if (
        float(val.get("winner_opportunity_retained_rate", np.nan)) >= float(overlay_cfg.get("winner_retention_min_validation", 0.80))
        and float(rob.get("winner_opportunity_retained_rate", np.nan)) >= float(overlay_cfg.get("winner_retention_min_robustness", 0.75))
        and not bool(val.get("badside_support_caveat", True))
        and not bool(rob.get("badside_support_caveat", True))
        and not bool(val.get("winner_retention_support_caveat", True))
        and not bool(rob.get("winner_retention_support_caveat", True))
    ) else "fail"
    total_delta = float(finite_numeric(out["overlay_per_event_utility_50bps"]).sum() - finite_numeric(out["baseline_per_event_utility_50bps"]).sum())
    dup = out.loc[bool_series(out.get("ex_post_duplicate_episode_flag", pd.Series(False, index=out.index)))]
    dup_delta = float(finite_numeric(dup["overlay_per_event_utility_50bps"]).sum() - finite_numeric(dup["baseline_per_event_utility_50bps"]).sum()) if len(dup) else 0.0
    duplicate_delta_share = dup_delta / total_delta if total_delta > 0 else 0.0
    density_status = "pass" if duplicate_delta_share <= float(overlay_cfg.get("duplicate_delta_share_max", 0.80)) else "fail"
    readout["duplicate_delta_share"] = duplicate_delta_share
    return out, readout, retention, overlay_status, winner_status, density_status, "duplicate_delta_share_exceeds_max" if density_status != "pass" else ""


def build_action_distribution(overlay: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for split in SPLITS:
        sub = overlay.loc[overlay["split_bucket"].astype(str).eq(split)]
        event_n = int(len(sub))
        for action in ["increase", "keep", "reduce", "skip"]:
            a = sub.loc[sub["action"].astype(str).eq(action)]
            rows.append(
                {
                    "split_bucket": split,
                    "action": action,
                    "event_n": event_n,
                    "action_n": int(len(a)),
                    "action_fraction": len(a) / event_n if event_n else np.nan,
                    "ex_post_duplicate_action_n": int(bool_series(a.get("ex_post_duplicate_episode_flag", pd.Series(False, index=a.index))).sum()) if len(a) else 0,
                    "t0_known_crowded_action_n": int(a["t0_known_crowding_context"].astype(str).eq("crowded").sum()) if len(a) else 0,
                }
            )
    return pd.DataFrame(rows)


def search_multiplicity_audit(config: dict[str, Any]) -> pd.DataFrame:
    grid = config.get("label_grid", {})
    up_n = len(grid.get("up_mfe_threshold_grid", [0.2, 0.3, 0.5]))
    down_n = len(grid.get("down_mae_threshold_grid", [-0.1, -0.15, -0.2]))
    horizon_n = len(grid.get("horizon_sessions_grid", [20, 60, 120]))
    _up, _down, _h, endpoint = primary_endpoint(config)
    search = config.get("search_accounting", {})
    return pd.DataFrame(
        [
            {
                "selected_state_id": str(config.get("selected_state_id", "repair_range_participation_core_30")),
                "up_threshold_n": up_n,
                "down_threshold_n": down_n,
                "horizon_n": horizon_n,
                "label_endpoint_n": up_n * down_n * horizon_n,
                "primary_endpoint": endpoint,
                "action_n": int(search.get("action_n", 4)),
                "rule_family_n": int(search.get("rule_family_n", 1)),
                "ml_model_used": False,
                "hyperparameter_search_used": False,
                "validation_used_for_rule_freeze": False,
                "robustness_used_for_rule_freeze": False,
                "effective_search_space_n": up_n * down_n * horizon_n,
                "confirmatory_status": False,
                "search_accounting_status": "diagnostic_pre_registered_primary_endpoint",
            }
        ]
    )


def build_decision(
    input_status: str,
    upstream_status: str,
    row_status: str,
    label_status: str,
    denominator_status: str,
    uniqueness_status: str,
    rule_status: str,
    overlay_status: str,
    winner_status: str,
    density_status: str,
    row_audit: pd.DataFrame,
    rule_dictionary: pd.DataFrame,
    utility_readout: pd.DataFrame,
    search: pd.DataFrame,
    config: dict[str, Any],
    primary_failure_reason: str = "",
) -> pd.DataFrame:
    selected = str(config.get("selected_state_id", "repair_range_participation_core_30"))
    _up, _down, _h, endpoint = primary_endpoint(config)
    precedence = [
        (input_status != "pass", "13G_blocked_input_or_lineage_failure", "input_or_lineage_failure"),
        (upstream_status != "pass", "13G_blocked_upstream_lineage_failure", "upstream_lineage_failure"),
        (row_status != "pass", "13G_blocked_row_level_rebuild_failure", "row_level_rebuild_failure"),
        (label_status != "pass", "13G_blocked_label_panel_failure", "label_panel_failure"),
        (denominator_status != "pass", "13G_blocked_event_denominator_failure", "event_denominator_failure"),
        (uniqueness_status != "pass", "13G_stop_uniqueness_unavailable_for_overlay", "uniqueness_unavailable"),
        (rule_status != "pass", "13G_blocked_rule_freeze_failure", "rule_freeze_failure"),
        (overlay_status != "pass", "13G_stop_label_panel_only_no_overlay_utility", "overlay_utility_gate_failed"),
        (winner_status != "pass", "13G_stop_overlay_improves_by_winner_sacrifice", "winner_or_badside_support_gate_failed"),
        (density_status != "pass", "13G_stop_overlay_improvement_density_artifact", "density_artifact_gate_failed"),
    ]
    decision_state = "13G_diagnostic_survival_overlay_signal_present"
    reason = primary_failure_reason
    for condition, state, failure in precedence:
        if condition:
            decision_state = state
            reason = reason or failure
            break
    if decision_state == "13G_diagnostic_survival_overlay_signal_present":
        readout = "rule_based_overlay_utility_signal_present"
        next_allowed = "manual_review_only"
    elif decision_state == "13G_stop_overlay_improves_by_winner_sacrifice":
        readout = "overlay_improves_by_winner_sacrifice"
        next_allowed = "none"
    elif decision_state == "13G_stop_overlay_improvement_density_artifact":
        readout = "overlay_improvement_density_artifact"
        next_allowed = "none"
    elif decision_state.startswith("13G_blocked"):
        readout = "blocked_or_not_evaluable"
        next_allowed = "none"
    else:
        readout = "label_panel_only_no_overlay_utility"
        next_allowed = "none"
    raw_event_n = int(row_audit["raw_event_n"].sum()) if "raw_event_n" in row_audit else 0
    analysis_event_n = int(row_audit["analysis_event_n"].sum()) if "analysis_event_n" in row_audit else 0
    rule_missing = float(rule_dictionary["rule_feature_missing_fraction"].iloc[0]) if "rule_feature_missing_fraction" in rule_dictionary and len(rule_dictionary) else np.nan
    badside_caveat = bool(utility_readout["badside_support_caveat"].astype(bool).any()) if "badside_support_caveat" in utility_readout else True
    winner_caveat = bool(utility_readout["winner_retention_support_caveat"].astype(bool).any()) if "winner_retention_support_caveat" in utility_readout else True
    return pd.DataFrame(
        [
            {
                "decision_state": decision_state,
                "next_allowed_requirement": next_allowed,
                "sequence_mining_authorized": False,
                "meta_labeling_authorized": False,
                "bet_sizing_authorized": False,
                "selected_state_id": selected,
                "primary_endpoint": endpoint,
                "effect_interpretation": "event_survival_opportunity_rule_overlay_diagnostic",
                "confirmatory_status": False,
                "raw_event_n": raw_event_n,
                "analysis_event_n": analysis_event_n,
                "analysis_event_fraction": analysis_event_n / raw_event_n if raw_event_n else 0.0,
                "rule_feature_missing_fraction": rule_missing,
                "badside_support_caveat": badside_caveat,
                "winner_retention_support_caveat": winner_caveat,
                "input_gate_status": input_status,
                "upstream_lineage_gate_status": upstream_status,
                "row_level_rebuild_gate_status": row_status,
                "label_panel_gate_status": label_status,
                "event_denominator_gate_status": denominator_status,
                "event_uniqueness_gate_status": uniqueness_status,
                "rule_freeze_gate_status": rule_status,
                "overlay_utility_gate_status": overlay_status,
                "winner_retention_gate_status": winner_status,
                "density_adjustment_gate_status": density_status,
                "validation_used_for_rule_freeze": False,
                "robustness_used_for_rule_freeze": False,
                "ml_model_used": False,
                "hyperparameter_search_used": False,
                "search_accounting_status": first_row_value(search, "search_accounting_status", "diagnostic_pre_registered_primary_endpoint"),
                "primary_failure_reason": reason,
                "survival_opportunity_readout": "fixed_event_denominator_label_panel",
                "overlay_capacity_readout": readout,
            }
        ]
    )


def md_table(df: pd.DataFrame, cols: list[str], max_rows: int = 20) -> str:
    if df.empty:
        return "_无记录_"
    existing = [c for c in cols if c in df.columns]
    return df[existing].head(max_rows).to_markdown(index=False)


def render_report(
    decision: pd.DataFrame,
    label_readout: pd.DataFrame,
    utility_readout: pd.DataFrame,
    retention: pd.DataFrame,
    uniqueness: pd.DataFrame,
    action_dist: pd.DataFrame,
    rule_dict: pd.DataFrame,
    row_audit: pd.DataFrame,
    search: pd.DataFrame,
) -> str:
    dec = decision.iloc[0]
    primary = label_readout.loc[label_readout["endpoint_id"].astype(str).eq(str(dec["primary_endpoint"]))]
    lines = [
        "# 13G Event Survival Opportunity and Defense Overlay Diagnostic Report",
        "",
        "## 裁决",
        "",
        f"单行裁决：`decision_state = {dec['decision_state']}`；`overlay_capacity_readout = {dec['overlay_capacity_readout']}`。本轮只评估 event-level survival / opportunity label panel 与 rule-based defense / participation overlay，不授权 sequence mining、meta-labeling、bet sizing 或 entry policy。",
        "",
        f"- selected_state_id: `{dec['selected_state_id']}`",
        f"- primary_endpoint: `{dec['primary_endpoint']}`",
        f"- next_allowed_requirement: `{dec['next_allowed_requirement']}`",
        f"- primary_failure_reason: `{dec['primary_failure_reason']}`",
        "",
        "13G 不推翻 13C / 13E / 13F。13C/13E/13F 否决的是 t0 winner entry、非线性 winner 模型与 delayed entry；13G 只把 event 降级为 survival/opportunity carrier 与 risk-budget overlay state。",
        "",
        "## Denominator / Coverage",
        "",
        md_table(row_audit, ["split_bucket", "raw_event_n", "analysis_event_n", "analysis_event_fraction", "entry_not_executable_n", "entry_price_missing_n", "max_horizon_path_incomplete_n", "split_lineage_missing_n", "qfq_bar_mapping_missing_n", "selected_membership_source", "13f_row_level_used"], 10),
        "",
        "主读数使用同一 max-120d complete analysis denominator；shorter horizon 不扩大分母。若 coverage gate fail，结果只能解释为可评价性不足。",
        "",
        "## Survival / Opportunity Label Panel",
        "",
        md_table(primary, ["split_bucket", "raw_event_n", "analysis_event_n", "upper_hit_rate", "lower_hit_rate", "winner_before_fail_rate", "fail_before_winner_rate", "survive_without_fail_rate", "opportunity_without_fail_rate", "same_bar_ambiguous_rate", "upper_first_minus_lower_first_winner_rate_delta", "upper_first_minus_lower_first_fail_rate_delta", "median_time_to_upper", "median_time_to_lower", "mfe_return_mean", "mae_return_mean"], 10),
        "",
        "完整 27 endpoint sensitivity 只作机制解释，不得覆盖主端点裁决。",
        "",
        md_table(label_readout, ["split_bucket", "endpoint_id", "analysis_event_n", "not_evaluable_n", "entry_not_executable_n", "entry_price_missing_n", "max_horizon_path_incomplete_n", "split_lineage_missing_n", "qfq_bar_mapping_missing_n", "winner_before_fail_rate", "fail_before_winner_rate", "survive_without_fail_rate", "same_bar_ambiguous_rate", "upper_first_minus_lower_first_winner_rate_delta", "upper_first_minus_lower_first_fail_rate_delta", "mfe_return_mean", "mae_return_mean"], 100),
        "",
        "## Rule Overlay",
        "",
        "规则仅使用 t0 context 与 t0-known crowding；future overlap / ex-post duplicate episode / time-to-hit 不进入 action rule。",
        "",
        md_table(rule_dict, ["rule_feature_id", "source_column", "bucket_labels", "threshold_q33", "threshold_q66_or_p80", "direction", "threshold_source", "rule_feature_missing_fraction", "rule_freeze_gate_status"], 20),
        "",
        md_table(action_dist, ["split_bucket", "action", "event_n", "action_n", "action_fraction", "ex_post_duplicate_action_n", "t0_known_crowded_action_n"], 20),
        "",
        "## Overlay Utility / Support",
        "",
        "主 gate 使用 50bps；0bps / 100bps 作为 cost robustness readout。Skip 不删除分母，path exposure 为 0，但扣对应 cost-tier adjustment cost。",
        "",
        md_table(utility_readout, ["split_bucket", "analysis_event_n", "baseline_utility_per_event_mean_50bps", "overlay_utility_per_event_mean_50bps", "delta_overlay_vs_baseline_50bps", "baseline_exposure_day_return_50bps", "overlay_exposure_day_return_50bps", "badside_avoided_rate", "winner_opportunity_retained_rate", "badside_support_caveat", "winner_retention_support_caveat", "duplicate_delta_share"], 10),
        "",
        md_table(retention, ["split_bucket", "winner_before_fail_n", "winner_retained_n", "winner_opportunity_retained_rate", "fail_before_winner_n", "badside_avoided_n", "badside_avoided_rate", "badside_support_caveat", "winner_retention_support_caveat"], 10),
        "",
        "## Uniqueness / Density",
        "",
        md_table(uniqueness, ["split_bucket", "event_n", "average_uniqueness", "median_uniqueness", "p90_concurrency", "event_density_per_instrument_year", "rolling_20d_event_count_p95", "duplicate_episode_event_count", "duplicate_episode_fraction", "event_uniqueness_gate_status"], 10),
        "",
        "## Search Accounting",
        "",
        md_table(search, ["label_endpoint_n", "primary_endpoint", "action_n", "rule_family_n", "ml_model_used", "hyperparameter_search_used", "validation_used_for_rule_freeze", "robustness_used_for_rule_freeze", "effective_search_space_n", "search_accounting_status"], 5),
        "",
        "## Boundary",
        "",
        "本报告不得写成 alpha discovered、deployable strategy、confirmed edge、meta-labeling ready、bet sizing ready 或 position sizing validated。若 diagnostic positive，也只是 manual review 线索。",
    ]
    return "\n".join(lines)


def publishable_manifest_outputs(outputs: dict[str, Path]) -> dict[str, Path]:
    return {key: path for key, path in outputs.items() if "local_cache" not in path.parts and key != "manifest"}


def build_manifest(config_path: Path, config: dict[str, Any], outputs: dict[str, Path], input_audit: pd.DataFrame) -> dict[str, Any]:
    publishable = publishable_manifest_outputs(outputs)
    return {
        "run_id": RUN_ID,
        "experiment_id": EXPERIMENT_ID,
        "phase_id": PHASE_ID,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "git_revision": r13a.git_revision(REPO_ROOT),
        "python": sys.version,
        "platform": platform.platform(),
        "config_path": str(config_path),
        "config_sha256": file_sha(config_path),
        "config_hash": stable_hash(config),
        "input_artifacts": input_audit.to_dict(orient="records"),
        "output_hashes": {key: file_sha(path) for key, path in publishable.items()},
        "publishable_outputs": {key: str(path) for key, path in publishable.items()},
        "local_cache_outputs_excluded": [str(path) for key, path in outputs.items() if "local_cache" in path.parts],
        "local_cache_audit": [
            {
                "artifact_id": key,
                "path": str(path),
                "exists": path.exists(),
                "row_count": count_rows(path) if path.exists() else np.nan,
                "schema_hash": schema_hash(path) if path.exists() else "",
                "cache_used_as_input": False,
            }
            for key, path in outputs.items()
            if "local_cache" in path.parts
        ],
    }


def run(config_path: Path, mode: str = "full", check_inputs_only: bool = False) -> dict[str, Path]:
    config = r13a.load_yaml(config_path)
    resolved = resolve_paths(config)
    outputs = output_paths()
    input_audit = build_input_audit(resolved)
    write_df(outputs["input_artifact_audit"], input_audit)
    input_status, input_reason = input_gate_status(input_audit)
    upstream, upstream_status, upstream_reason = build_upstream_lineage_audit(
        resolved,
        config,
        allow_rebuild=not (check_inputs_only or mode == "check-inputs"),
    )
    write_df(outputs["upstream_lineage_audit"], upstream)
    if check_inputs_only or mode == "check-inputs":
        write_json(outputs["manifest"], build_manifest(config_path, config, outputs, input_audit))
        return outputs

    raw_events = load_raw_event_panel(resolved["upstream_13c_morphology_residual_panel_cache"], config)
    label_panel, event_status = reconstruct_label_panel(raw_events, resolved["stock_daily_qfq_dir"], config)
    row_audit = build_row_level_rebuild_audit(raw_events, event_status, config)
    denominator_status, denominator_reason = denominator_gate_status(row_audit, config)
    label_status = "pass" if label_panel.groupby(["up_threshold", "down_threshold", "horizon_sessions"]).ngroups == len(label_grid(config)) else "fail"
    row_status = "pass" if not raw_events.empty else "fail"
    event_core = event_status.merge(
        raw_events.drop(columns=[c for c in ["selected_state_id"] if c in raw_events.columns]),
        on=["event_id", "instrument", "reference_date", "entry_date", "entry_pos", "entry_price", "split_bucket"],
        how="left",
    )
    overlay, rule_dict, rule_status, rule_reason = build_rule_overlay(event_core, raw_events, config)
    overlay = attach_primary_labels(overlay, label_panel, config)
    overlay, uniqueness = compute_event_uniqueness(overlay, config)
    uniqueness_status = "pass" if uniqueness["event_uniqueness_gate_status"].astype(str).eq("pass").all() else "fail"
    overlay, utility, retention, overlay_status, winner_status, density_status, density_reason = build_overlay_utility(overlay, config)
    action_dist = build_action_distribution(overlay)
    label_readout = build_label_grid_readout(label_panel, raw_events, event_status)
    time_dist = build_time_to_hit_distribution(label_panel)
    search = search_multiplicity_audit(config)
    primary_failure = input_reason or upstream_reason or denominator_reason or rule_reason or density_reason
    decision = build_decision(
        input_status,
        upstream_status,
        row_status,
        label_status,
        denominator_status,
        uniqueness_status,
        rule_status,
        overlay_status,
        winner_status,
        density_status,
        row_audit,
        rule_dict,
        utility,
        search,
        config,
        primary_failure_reason=primary_failure,
    )

    write_df(outputs["row_level_rebuild_audit"], row_audit)
    write_df(outputs["survival_opportunity_label_grid_readout"], label_readout)
    write_df(outputs["time_to_hit_distribution"], time_dist)
    write_df(outputs["event_uniqueness_density_audit"], uniqueness)
    write_df(outputs["rule_overlay_dictionary"], rule_dict)
    write_df(outputs["rule_overlay_action_distribution"], action_dist)
    write_df(outputs["rule_overlay_utility_readout"], utility)
    write_df(outputs["rule_overlay_winner_retention_audit"], retention)
    write_df(outputs["search_multiplicity_audit"], search)
    write_df(outputs["event_survival_opportunity_overlay_decision"], decision)
    write_df(outputs["survival_opportunity_label_panel"], label_panel)
    write_df(outputs["rule_overlay_event_panel"], overlay)
    write_text(outputs["report"], render_report(decision, label_readout, utility, retention, uniqueness, action_dist, rule_dict, row_audit, search))
    write_json(outputs["manifest"], build_manifest(config_path, config, outputs, input_audit))
    return outputs


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    run(Path(args.config), mode=args.mode, check_inputs_only=args.check_inputs_only)


if __name__ == "__main__":
    main()
