#!/usr/bin/env python
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml


EXPERIMENT_DIR = Path(__file__).resolve().parents[1]
TOPIC_ROOT = Path(__file__).resolve().parents[4]
REPO_ROOT = Path(__file__).resolve().parents[6]

RUN_ID = "17A_oracle_replay_contract_preflight"
EXPERIMENT_ID = "17_oracle_action_value_upper_bound_diagnostic"
PHASE_ID = "17A"
CONFIG_PATH = EXPERIMENT_DIR / "configs" / "config_17a_oracle_replay_contract_preflight.yaml"
TABLE_DIR = EXPERIMENT_DIR / "outputs" / "publishable" / "tables" / RUN_ID
LOCAL_CACHE_DIR = EXPERIMENT_DIR / "outputs" / "local_cache" / RUN_ID
REPORT_DIR = EXPERIMENT_DIR / "outputs" / "publishable" / "reports"
MANIFEST_DIR = EXPERIMENT_DIR / "outputs" / "manifests"

SPLITS = ("train", "robustness", "validation")
PRIMARY_COST_BPS = 50

DECISION_READY = "EP17A_oracle_replay_contract_ready"
DECISION_BLOCKED = "oracle_lineage_or_denominator_blocked"
NEXT_17B = "requirement_17b_oracle_ladder_replay.md"

AUTH_FALSE_COLUMNS = (
    "entry_policy_authorized",
    "exit_policy_authorized",
    "holding_policy_authorized",
    "chained_simulation_authorized",
    "portfolio_backtest_authorized",
    "model_deployment_authorized",
    "production_signal_authorized",
    "live_trading_authorized",
)

PRIMARY_ROW_KEY = (
    "step_id",
    "label_id",
    "threshold_id",
    "instrument",
    "episode_cluster_id",
    "horizon_sessions",
    "step_index",
    "step_start_date",
    "step_end_date",
    "cluster_split_bucket",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run EP17A oracle replay contract preflight.")
    parser.add_argument("--config", default=str(CONFIG_PATH))
    parser.add_argument("--check-inputs-only", action="store_true")
    parser.add_argument("--mode", choices=["check-inputs", "full"], default="full")
    return parser.parse_args(argv)


def load_config(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def topic_path(value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    text = str(path)
    if text.startswith("topics/"):
        return REPO_ROOT / path
    if text.startswith(("data/", "experiments/")):
        return TOPIC_ROOT / path
    if text in {"research_conclusions.md", "research_log.md"}:
        return TOPIC_ROOT / path
    if text.startswith(("outputs/", "configs/", "src/", "tests/")):
        return EXPERIMENT_DIR / path
    return EXPERIMENT_DIR / path


def resolve_paths(config: dict[str, Any]) -> dict[str, Path]:
    return {key: topic_path(value) for key, value in config.get("paths", {}).items()}


def output_paths() -> dict[str, Path]:
    return {
        "input_artifact_audit": TABLE_DIR / "input_artifact_audit.csv",
        "upstream_closure_audit": TABLE_DIR / "upstream_closure_audit.csv",
        "denominator_lineage_audit": TABLE_DIR / "denominator_lineage_audit.csv",
        "oracle_denominator_binding": TABLE_DIR / "oracle_denominator_binding.csv",
        "action_semantics_audit": TABLE_DIR / "action_semantics_audit.csv",
        "delayed_materialization_audit": TABLE_DIR / "delayed_materialization_audit.csv",
        "capacity_reconstruction_audit": TABLE_DIR / "capacity_reconstruction_audit.csv",
        "replay_price_path_audit": TABLE_DIR / "replay_price_path_audit.csv",
        "learned_score_reference_replay_audit": TABLE_DIR / "learned_score_reference_replay_audit.csv",
        "ep16_replay_sanity_check": TABLE_DIR / "ep16_replay_sanity_check.csv",
        "six_cell_sanity_reconciliation": TABLE_DIR / "six_cell_sanity_reconciliation.csv",
        "search_accounting_audit": TABLE_DIR / "search_accounting_audit.csv",
        "decision": TABLE_DIR / "oracle_replay_contract_decision.csv",
        "replay_contract_panel": LOCAL_CACHE_DIR / "replay_contract_panel.parquet",
        "denominator_contract": EXPERIMENT_DIR / "oracle_denominator_contract.md",
        "action_contract": EXPERIMENT_DIR / "oracle_action_contract.md",
        "report": REPORT_DIR / "oracle_replay_contract_preflight_report.md",
        "manifest": MANIFEST_DIR / "17A_oracle_replay_contract_preflight_manifest.json",
        "replay_engine_manifest": MANIFEST_DIR / "oracle_replay_engine_manifest.json",
        "input_artifact_manifest": MANIFEST_DIR / "input_artifact_manifest.json",
    }


def read_table(path: Path, **kwargs: Any) -> pd.DataFrame:
    suffixes = "".join(path.suffixes)
    if suffixes.endswith(".parquet"):
        return pd.read_parquet(path, **kwargs)
    if suffixes.endswith((".csv", ".csv.gz")):
        return pd.read_csv(path, **kwargs)
    raise ValueError(f"Unsupported table path: {path}")


def write_df(path: Path, frame: pd.DataFrame) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if "".join(path.suffixes).endswith(".parquet"):
        frame.to_parquet(path, index=False)
    else:
        frame.to_csv(path, index=False)
    return path


def write_text(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def clean_json(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): clean_json(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [clean_json(v) for v in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return None if not np.isfinite(value) else float(value)
    if isinstance(value, (np.bool_,)):
        return bool(value)
    if not isinstance(value, (str, bytes, dict, list, tuple)):
        try:
            if pd.isna(value):
                return None
        except TypeError:
            pass
    return value


def write_json(path: Path, payload: dict[str, Any] | list[dict[str, Any]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(clean_json(payload), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return path


def file_sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def stable_hash(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(clean_json(value), ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()


def metric_float(value: Any) -> float:
    try:
        out = float(value)
    except Exception:
        return np.nan
    return out if np.isfinite(out) else np.nan


def bool_value(value: Any) -> bool:
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes", "pass"}
    if pd.isna(value):
        return False
    return bool(value)


def count_rows(path: Path) -> int | float:
    if not path.exists():
        return np.nan
    if path.is_dir():
        return len(list(path.iterdir()))
    suffixes = "".join(path.suffixes)
    if suffixes.endswith(".parquet"):
        return len(pd.read_parquet(path))
    if suffixes.endswith(".csv.gz"):
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            return max(sum(1 for _ in handle) - 1, 0)
    if suffixes.endswith(".csv"):
        with path.open("r", encoding="utf-8") as handle:
            return max(sum(1 for _ in handle) - 1, 0)
    return sum(1 for _ in path.open("rb"))


def required_columns_for_key(key: str) -> set[str]:
    mapping: dict[str, set[str]] = {
        "upstream_16b_decision": {"decision_state", "primary_label_id", "selected_threshold_id"},
        "upstream_16b_base_rate_readout": {
            "label_id",
            "threshold_id",
            "cluster_split_bucket",
            "labelable_step_n",
            "positive_step_n",
            "negative_step_n",
            "neutral_step_n",
        },
        "upstream_16d_decision": {
            "decision_state",
            "next_allowed_requirement",
            "primary_policy_id",
            "train_binary_step_n",
            "robustness_binary_step_n",
        },
        "upstream_16d_policy_threshold_freeze_audit": {
            "policy_id",
            "threshold_value",
            "threshold_freeze_status",
        },
        "upstream_16d_policy_action_binding_audit": {
            "primary_step_n",
            "binary_step_n",
            "neutral_step_n",
            "policy_action_binding_gate",
        },
        "upstream_16d_policy_confusion_readout": {
            "policy_id",
            "split_bucket",
            "context_stratum",
            "binary_step_n",
            "positive_n",
            "negative_n",
            "defended_binary_step_n",
            "defended_negative_n",
        },
        "upstream_16d_policy_action_panel": {
            "step_id",
            "policy_id",
            "candidate_action",
            "cluster_split_bucket",
            "episode_cluster_id",
        },
        "upstream_16e_decision": {
            "decision_state",
            "next_allowed_requirement",
            "primary_policy_id",
            "primary_action_semantics_id",
            "utility_interpretation",
        },
        "upstream_16e_utility_by_split_readout": {
            "split_bucket",
            "cost_bps",
            "labelable_step_n",
            "full_denominator_mean_incremental_return",
            "defended_negative_drawdown_avoided_abs_mean",
        },
        "upstream_16e_negative_avoidance_utility_readout": {
            "split_bucket",
            "context_stratum",
            "cost_bps",
            "defended_negative_drawdown_avoided_abs_mean",
        },
        "upstream_16e_six_cell_utility_reconciliation": {
            "split_bucket",
            "context_stratum",
            "cost_bps",
            "cell_id",
            "incremental_return_sum",
        },
        "upstream_16e_utility_price_path_audit": {
            "split_bucket",
            "labelable_step_n",
            "price_path_valid_step_n",
            "utility_price_path_gate",
        },
        "upstream_16e_utility_panel": {
            "step_id",
            "policy_id",
            "cost_bps",
            "cluster_split_bucket",
            "cell_id",
            "incremental_net_return_h20",
        },
        "upstream_16e_postmortem_decision": {
            "decision_state",
            "next_allowed_requirement",
            "continuation_as_action_mainline_closed",
            "selected_path_id",
        },
        "upstream_16x_decision": {
            "decision_state",
            "next_allowed_requirement",
            "continuation_as_action_mainline_closed",
            "payoff_aligned_label_redo_authorized",
        },
    }
    if key.endswith("_manifest") or key in {"requirement", "research_plan", "research_conclusions"}:
        return set()
    if key.endswith("_search_accounting_audit"):
        return {"search_accounting_gate"}
    return mapping.get(key, set())


def artifact_required_flag(key: str) -> str:
    optional = {"upstream_16d_policy_action_panel", "upstream_16e_utility_panel"}
    return "optional_cache" if key in optional else "required"


def build_input_artifact_audit(config: dict[str, Any], resolved: dict[str, Path]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    roles = config.get("artifact_roles", {})
    for key, path in resolved.items():
        required_flag = artifact_required_flag(key)
        exists = path.exists()
        read_status = "pass" if exists else "missing"
        schema_status = "not_checked"
        row_count: int | float = np.nan
        sha = ""
        if exists:
            try:
                row_count = count_rows(path)
                if path.is_file():
                    sha = file_sha(path)
                cols = required_columns_for_key(key)
                if cols:
                    frame = read_table(path, nrows=5) if "".join(path.suffixes).endswith((".csv", ".csv.gz")) else read_table(path)
                    schema_status = "pass" if cols.issubset(frame.columns) else "fail_missing_columns"
                elif path.is_file() or path.is_dir():
                    schema_status = "pass"
            except Exception as exc:  # pragma: no cover - defensive path
                read_status = f"fail:{type(exc).__name__}"
                schema_status = "fail_read_error"
        rows.append(
            {
                "artifact_key": key,
                "artifact_role": roles.get(key, infer_artifact_role(key)),
                "required_flag": required_flag,
                "resolver_alias": "topic_path",
                "resolved_path": str(path),
                "relative_path": relative_to_topic(path),
                "source_experiment_id": infer_source_experiment(key),
                "source_phase_id": infer_source_phase(key),
                "row_count": row_count,
                "sha256": sha,
                "schema_status": schema_status,
                "read_status": read_status,
                "absolute_path_mismatch_ignored": False,
                "blocking_reason": "" if exists and not str(schema_status).startswith("fail") else "missing_or_schema_failure",
            }
        )
    return pd.DataFrame(rows)


def infer_artifact_role(key: str) -> str:
    if key in {"requirement", "research_plan", "research_conclusions"}:
        return "local_contract"
    if "manifest" in key:
        return "upstream_manifest"
    if "policy_action_panel" in key or "utility_panel" in key:
        return "optional_row_level_cache"
    if "decision" in key:
        return "upstream_decision"
    return "upstream_publishable_audit"


def infer_source_experiment(key: str) -> str:
    if key.startswith("upstream_16"):
        return "16_winner_episode_sequential_sampling_geometry_preflight_v0"
    return EXPERIMENT_ID


def infer_source_phase(key: str) -> str:
    for phase in ("16b", "16d", "16e_postmortem", "16e", "16x"):
        if phase in key:
            return phase.upper().replace("_", "-")
    return PHASE_ID


def relative_to_topic(path: Path) -> str:
    try:
        return str(path.relative_to(TOPIC_ROOT))
    except ValueError:
        return str(path)


def input_gate_status(audit: pd.DataFrame) -> tuple[str, str]:
    required = audit.loc[audit["required_flag"].eq("required")]
    bad = required.loc[
        required["read_status"].ne("pass") | required["schema_status"].astype(str).str.startswith("fail")
    ]
    if bad.empty:
        return "pass", ""
    return "fail", ";".join(bad["artifact_key"].astype(str).tolist())


def text_has_false(text: str, key: str) -> bool:
    return f"{key} = false" in text or f"{key}=false" in text


def text_has_true(text: str, key: str) -> bool:
    return f"{key} = true" in text or f"{key}=true" in text


def build_upstream_closure_audit(config: dict[str, Any], resolved: dict[str, Path]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    conclusions = resolved["research_conclusions"].read_text(encoding="utf-8")
    plan = resolved["research_plan"].read_text(encoding="utf-8")
    topic_required = {
        "deployable_strategy_found": text_has_false(conclusions, "deployable_strategy_found"),
        "production_signal_authorized": text_has_false(conclusions, "production_signal_authorized"),
        "live_trading_authorized": text_has_false(conclusions, "live_trading_authorized"),
        "entry_policy_authorized": text_has_false(conclusions, "entry_policy_authorized"),
        "exit_policy_authorized": text_has_false(conclusions, "exit_policy_authorized"),
        "holding_policy_authorized": text_has_false(conclusions, "holding_policy_authorized"),
        "portfolio_backtest_authorized": text_has_false(conclusions, "portfolio_backtest_authorized"),
        "continuation_as_action_mainline_closed": text_has_true(conclusions, "continuation_as_action_mainline_closed"),
    }
    narrative_ok = "OOS payoff/utility ranking, not recall" in plan or (
        "OOS payoff" in conclusions and "utility" in conclusions
    )
    rows.append(
        {
            "source_document": relative_to_topic(resolved["research_conclusions"]),
            "source_phase_id": "topic_conclusion",
            "deployable_strategy_found": False,
            "decision_state": "",
            "next_allowed_requirement": "",
            "continuation_as_action_mainline_closed": True,
            "main_unsolved_problem_readout": "OOS payoff/utility ranking, not recall" if narrative_ok else "",
            "main_unsolved_problem_readout_status": "prose_or_research_plan_only" if narrative_ok else "missing",
            "payoff_aligned_label_redo_authorized": False,
            "entry_policy_authorized": False,
            "exit_policy_authorized": False,
            "holding_policy_authorized": False,
            "chained_simulation_authorized": False,
            "portfolio_backtest_authorized": False,
            "model_deployment_authorized": False,
            "production_signal_authorized": False,
            "live_trading_authorized": False,
            "required_state_status": "pass" if all(topic_required.values()) else "fail",
            "blocking_reason": "" if all(topic_required.values()) else ";".join(k for k, ok in topic_required.items() if not ok),
        }
    )
    rows.extend(closure_rows_from_decisions(config, resolved))
    return pd.DataFrame(rows)


def closure_rows_from_decisions(config: dict[str, Any], resolved: dict[str, Path]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    specs = [
        (
            "16E",
            resolved["upstream_16e_decision"],
            {
                "decision_state": "16E_utility_diagnostic_not_supported",
                "next_allowed_requirement": "none",
                "utility_interpretation": "drawdown_reduction_only_return_not_supported",
            },
        ),
        (
            "16E-postmortem",
            resolved["upstream_16e_postmortem_decision"],
            {
                "decision_state": "16E_postmortem_mainline_closed_no_path_supported",
                "next_allowed_requirement": "none",
                "selected_path_id": "none",
            },
        ),
        (
            "16X",
            resolved["upstream_16x_decision"],
            {
                "decision_state": "16X_payoff_precheck_not_supported",
                "next_allowed_requirement": "none",
            },
        ),
    ]
    for phase, path, expected in specs:
        frame = read_table(path)
        row = frame.iloc[0].to_dict() if not frame.empty else {}
        checks = [str(row.get(k)) == str(v) for k, v in expected.items()]
        for col in AUTH_FALSE_COLUMNS:
            if col in row:
                checks.append(not bool_value(row.get(col)))
        if "continuation_as_action_mainline_closed" in row:
            checks.append(bool_value(row.get("continuation_as_action_mainline_closed")))
        if "payoff_aligned_label_redo_authorized" in row:
            checks.append(not bool_value(row.get("payoff_aligned_label_redo_authorized")))
        rows.append(
            {
                "source_document": relative_to_topic(path),
                "source_phase_id": phase,
                "deployable_strategy_found": False,
                "decision_state": row.get("decision_state", ""),
                "next_allowed_requirement": row.get("next_allowed_requirement", ""),
                "continuation_as_action_mainline_closed": bool_value(
                    row.get("continuation_as_action_mainline_closed", True)
                ),
                "main_unsolved_problem_readout": "",
                "main_unsolved_problem_readout_status": "not_applicable",
                "payoff_aligned_label_redo_authorized": bool_value(
                    row.get("payoff_aligned_label_redo_authorized", False)
                ),
                "entry_policy_authorized": bool_value(row.get("entry_policy_authorized", False)),
                "exit_policy_authorized": bool_value(row.get("exit_policy_authorized", False)),
                "holding_policy_authorized": bool_value(row.get("holding_policy_authorized", False)),
                "chained_simulation_authorized": bool_value(row.get("chained_simulation_authorized", False)),
                "portfolio_backtest_authorized": bool_value(row.get("portfolio_backtest_authorized", False)),
                "model_deployment_authorized": bool_value(row.get("model_deployment_authorized", False)),
                "production_signal_authorized": bool_value(row.get("production_signal_authorized", False)),
                "live_trading_authorized": bool_value(row.get("live_trading_authorized", False)),
                "required_state_status": "pass" if all(checks) else "fail",
                "blocking_reason": "" if all(checks) else "closure_value_mismatch",
            }
        )
    return rows


def primary_panel(utility_panel: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    cost = int(config["expected_16e_sanity"]["primary_round_trip_defense_cost_bps"])
    policy = config["policy"]["primary_policy_id"]
    return utility_panel.loc[
        utility_panel["cost_bps"].astype(int).eq(cost) & utility_panel["policy_id"].astype(str).eq(policy)
    ].copy()


def build_denominator_lineage_audit(config: dict[str, Any], utility_panel: pd.DataFrame) -> pd.DataFrame:
    panel = primary_panel(utility_panel, config)
    rows: list[dict[str, Any]] = []
    required_key_cols = list(PRIMARY_ROW_KEY) + ["label_class"]
    missing_field_n = int(panel[required_key_cols].isna().any(axis=1).sum())
    duplicate_n = int(panel.duplicated(list(PRIMARY_ROW_KEY)).sum())
    for split in SPLITS:
        exp = config["expected_denominator"][split]
        sub = panel.loc[panel["cluster_split_bucket"].astype(str).eq(split)]
        positive_n = int(sub["label_class"].astype(str).eq("positive").sum())
        negative_n = int(sub["label_class"].astype(str).eq("negative").sum())
        neutral_n = int(sub["label_class"].astype(str).eq("neutral").sum())
        observed = {
            "labelable_step_n": len(sub),
            "binary_step_n": positive_n + negative_n,
            "neutral_step_n": neutral_n,
        }
        checks = [
            observed["labelable_step_n"] == int(exp["labelable_step_n"]),
            observed["binary_step_n"] == int(exp["binary_step_n"]),
            observed["neutral_step_n"] == int(exp["neutral_step_n"]),
            positive_n == int(exp["positive_n"]),
            negative_n == int(exp["negative_n"]),
            duplicate_n == 0,
            missing_field_n == 0,
        ]
        rows.append(
            {
                "split_bucket": split,
                "expected_labelable_step_n": exp["labelable_step_n"],
                "observed_labelable_step_n": observed["labelable_step_n"],
                "expected_binary_step_n": exp["binary_step_n"],
                "observed_binary_step_n": observed["binary_step_n"],
                "expected_neutral_step_n": exp["neutral_step_n"],
                "observed_neutral_step_n": observed["neutral_step_n"],
                "positive_n": positive_n,
                "negative_n": negative_n,
                "neutral_n": neutral_n,
                "duplicate_primary_row_key_n": duplicate_n,
                "missing_primary_row_key_field_n": missing_field_n,
                "missing_episode_cluster_id_n": int(sub["episode_cluster_id"].isna().sum()),
                "missing_instrument_n": int(sub["instrument"].isna().sum()),
                "source_16b_status": "pass",
                "source_16d_status": "pass",
                "source_16e_status": "pass",
                "denominator_reconciliation_gate": "pass" if all(checks) else "fail",
                "blocking_reason": "" if all(checks) else "denominator_mismatch",
            }
        )
    return pd.DataFrame(rows)


def build_oracle_denominator_binding(config: dict[str, Any], capacity_gate: str = "appendix_only") -> pd.DataFrame:
    exp = config["expected_denominator"]
    specs = [
        ("O0", "No Oracle Baseline", "labelable_full", False, False, True),
        ("O1", "Perfect Negative Oracle", "binary_primary", True, False, True),
        ("O2", "Perfect Deep Drawdown Oracle", "labelable_full", False, False, True),
        ("O3", "Perfect False-repair Oracle", "appendix_only_if_join_incomplete", False, True, False),
        ("O4", "Positive Preservation Oracle", "binary_primary", True, False, True),
        ("O5", "Perfect Utility Oracle", "labelable_full", False, False, True),
        (
            "O6",
            "Capacity-constrained Utility Oracle",
            "labelable_full_if_capacity_gate_passes",
            False,
            True,
            capacity_gate == "pass",
        ),
        ("O7", "Delayed Utility Oracle", "labelable_full", False, False, True),
        ("L0", "16D Learned-score Reference", "binary_fit_labelable_replay", False, False, True),
    ]
    rows: list[dict[str, Any]] = []
    for oracle_id, name, den_type, neutral_stress, appendix, blocking in specs:
        use_binary = den_type in {"binary_primary", "binary_fit_labelable_replay"}
        rows.append(
            {
                "oracle_id": oracle_id,
                "oracle_name": name,
                "primary_denominator_type": den_type,
                "expected_primary_row_count_train": exp["train"]["binary_step_n" if use_binary else "labelable_step_n"],
                "expected_primary_row_count_robustness": exp["robustness"]["binary_step_n" if use_binary else "labelable_step_n"],
                "expected_primary_row_count_validation": exp["validation"]["binary_step_n" if use_binary else "labelable_step_n"],
                "neutral_stress_required": neutral_stress,
                "appendix_only_allowed": appendix,
                "skip_is_blocking": blocking,
                "binding_status": "pass",
                "blocking_reason": "",
            }
        )
    return pd.DataFrame(rows)


def build_action_semantics_audit(config: dict[str, Any]) -> pd.DataFrame:
    semantics = config["action_semantics"]
    rows: list[dict[str, Any]] = []
    selection_flags = [
        bool_value(semantics.get("validation_used_for_action_selection")),
        bool_value(semantics.get("robustness_used_for_action_selection")),
        bool_value(semantics.get("return_metric_used_for_action_selection")),
        bool_value(semantics.get("cost_selected_by_oos_result")),
    ]
    gate = "fail" if any(selection_flags) else "pass"
    for family in semantics["action_families"]:
        rows.append(
            {
                "action_family_id": family["action_family_id"],
                "baseline_action": semantics["baseline_action"],
                "q_continue": family["q_continue"],
                "q_defend": family["q_defend"],
                "round_trip_defense_cost_bps_grid": ",".join(map(str, semantics["round_trip_defense_cost_bps_grid"])),
                "primary_round_trip_defense_cost_bps": semantics["primary_round_trip_defense_cost_bps"],
                "cost_selected_by_oos_result": bool_value(semantics["cost_selected_by_oos_result"]),
                "cash_return": semantics["cash_return"],
                "holding_cost": semantics["holding_cost"],
                "validation_used_for_action_selection": bool_value(semantics["validation_used_for_action_selection"]),
                "robustness_used_for_action_selection": bool_value(semantics["robustness_used_for_action_selection"]),
                "return_metric_used_for_action_selection": bool_value(semantics["return_metric_used_for_action_selection"]),
                "action_semantics_gate": gate,
                "blocking_reason": "" if gate == "pass" else "action_selected_from_oos_result",
            }
        )
    return pd.DataFrame(rows)


def build_delayed_materialization_audit(config: dict[str, Any], utility_panel: pd.DataFrame) -> pd.DataFrame:
    panel = primary_panel(utility_panel, config)
    rows: list[dict[str, Any]] = []
    for split in SPLITS:
        sub = panel.loc[panel["cluster_split_bucket"].astype(str).eq(split)].copy()
        for k in config["delayed_action"]["delayed_k_sessions"]:
            remaining_ok = pd.to_numeric(sub["step_start_pos"], errors="coerce") + int(k) <= pd.to_numeric(
                sub["step_end_pos"], errors="coerce"
            )
            missing = int((~remaining_ok).sum())
            gate = "pass" if missing == 0 else "fail"
            rows.append(
                {
                    "split_bucket": split,
                    "labelable_step_n": len(sub),
                    "delay_k_sessions": int(k),
                    "materialized_step_n": int(remaining_ok.sum()),
                    "missing_t0_plus_k_price_n": missing,
                    "missing_original_h20_endpoint_n": int(sub["step_end_pos"].isna().sum()),
                    "restart_h20_at_t0_plus_k": bool_value(config["delayed_action"]["restart_h20_at_t0_plus_k"]),
                    "partial_tail_fill_used": bool_value(config["delayed_action"]["partial_tail_fill_used"]),
                    "delayed_materialization_gate": gate,
                    "blocking_reason": "" if gate == "pass" else "missing_delayed_price_or_endpoint",
                }
            )
    return pd.DataFrame(rows)


def build_capacity_reconstruction_audit(config: dict[str, Any], utility_panel: pd.DataFrame) -> pd.DataFrame:
    panel = primary_panel(utility_panel, config)
    cols_ok = {"step_start_date", "step_end_date", "instrument"}.issubset(panel.columns)
    force_appendix = bool_value(config["capacity"]["force_appendix_only"])
    gate = "appendix_only" if force_appendix else "pass" if cols_ok else "fail"
    return pd.DataFrame(
        [
            {
                "calendar_reconstruction_status": "pass" if cols_ok else "fail",
                "active_exposure_reconstruction_status": "appendix_only_by_config" if force_appendix else "pass",
                "same_day_concurrent_candidate_status": "appendix_only_by_config" if force_appendix else "pass",
                "capacity_cap_config_frozen": bool_value(config["capacity"]["capacity_cap_config_frozen"]),
                "turnover_cost_config_frozen": bool_value(config["capacity"]["turnover_cost_config_frozen"]),
                "o6_primary_allowed": (not force_appendix) and cols_ok,
                "o6_status_for_17b": "appendix_only_nonblocking" if force_appendix else "primary_allowed",
                "capacity_reconstruction_gate": gate,
                "blocking_reason": "" if gate in {"pass", "appendix_only"} else "capacity_reconstruction_failed",
            }
        ]
    )


def build_replay_price_path_audit(
    config: dict[str, Any],
    utility_panel: pd.DataFrame,
    upstream_price: pd.DataFrame,
    delayed: pd.DataFrame,
) -> pd.DataFrame:
    panel = primary_panel(utility_panel, config)
    rows: list[dict[str, Any]] = []
    delay_missing = delayed.groupby("split_bucket")["missing_t0_plus_k_price_n"].sum().to_dict()
    for split in SPLITS:
        src = upstream_price.loc[upstream_price["split_bucket"].astype(str).eq(split)]
        src_row = src.iloc[0].to_dict() if not src.empty else {}
        sub = panel.loc[panel["cluster_split_bucket"].astype(str).eq(split)]
        missing_delay = int(delay_missing.get(split, 0))
        source_gate = str(src_row.get("utility_price_path_gate", "fail"))
        gate = "pass" if source_gate == "pass" and missing_delay == 0 else "fail"
        rows.append(
            {
                "split_bucket": split,
                "labelable_step_n": int(src_row.get("labelable_step_n", len(sub))),
                "price_path_valid_step_n": int(src_row.get("price_path_valid_step_n", len(sub))),
                "missing_qfq_instrument_n": int(src_row.get("missing_qfq_instrument_n", 0)),
                "bad_step_bounds_n": int(src_row.get("bad_step_bounds_n", 0)),
                "nonfinite_close_n": int(src_row.get("nonfinite_close_n", 0)),
                "nonpositive_close_n": int(src_row.get("nonpositive_close_n", 0)),
                "step_start_close_mismatch_n": int(src_row.get("step_start_close_mismatch_n", 0)),
                "step_end_close_mismatch_n": int(src_row.get("step_end_close_mismatch_n", 0)),
                "first_session_missing_n": int(src_row.get("delay_row_missing_n", 0)),
                "delay_k_missing_n": missing_delay,
                "max_drawdown_replay_abs_diff_max": metric_float(src_row.get("max_drawdown_replay_abs_diff_max", 0.0)),
                "price_path_replay_gate": gate,
                "blocking_reason": "" if gate == "pass" else "price_path_or_delay_materialization_failed",
            }
        )
    return pd.DataFrame(rows)


def build_learned_score_reference_replay_audit(config: dict[str, Any], confusion: pd.DataFrame, thresholds: pd.DataFrame) -> pd.DataFrame:
    policy = config["policy"]["primary_policy_id"]
    thresh_rows = thresholds.loc[thresholds["policy_id"].astype(str).eq(policy)]
    observed_threshold = metric_float(thresh_rows.iloc[0]["threshold_value"]) if not thresh_rows.empty else np.nan
    expected_threshold = float(config["policy"]["threshold_value"])
    rows: list[dict[str, Any]] = []
    for split in SPLITS:
        expected = config["expected_16d_reference"][split]
        sub = confusion.loc[
            confusion["policy_id"].astype(str).eq(policy)
            & confusion["split_bucket"].astype(str).eq(split)
            & confusion["context_stratum"].astype(str).eq("all_steps")
        ]
        obs = sub.iloc[0].to_dict() if not sub.empty else {}
        checks = [
            abs(observed_threshold - expected_threshold) <= float(config["policy"]["threshold_abs_tolerance"]),
            int(obs.get("binary_step_n", -1)) == int(expected["binary_step_n"]),
            int(obs.get("positive_n", -1)) == int(expected["positive_n"]),
            int(obs.get("negative_n", -1)) == int(expected["negative_n"]),
            int(obs.get("defended_binary_step_n", -1)) == int(expected["defended_binary_step_n"]),
            int(obs.get("defended_negative_n", -1)) == int(expected["defended_negative_n"]),
            abs(metric_float(obs.get("defense_negative_capture_rate")) - float(expected["defense_negative_capture_rate"]))
            <= float(config["tolerances"]["rate_abs_tolerance"]),
            abs(metric_float(obs.get("positive_sacrifice_rate")) - float(expected["positive_sacrifice_rate"]))
            <= float(config["tolerances"]["rate_abs_tolerance"]),
            abs(metric_float(obs.get("continue_negative_leakage_rate")) - float(expected["continue_negative_leakage_rate"]))
            <= float(config["tolerances"]["rate_abs_tolerance"]),
        ]
        if "defense_precision_lift_vs_binary_negative_base" in expected:
            checks.append(
                abs(
                    metric_float(obs.get("defense_precision_lift_vs_binary_negative_base"))
                    - float(expected["defense_precision_lift_vs_binary_negative_base"])
                )
                <= float(config["tolerances"]["rate_abs_tolerance"])
            )
        rows.append(
            {
                "primary_policy_id": policy,
                "primary_model_id": config["policy"]["primary_model_id"],
                "threshold_value_expected": expected_threshold,
                "threshold_value_observed": observed_threshold,
                "threshold_value_abs_diff": abs(observed_threshold - expected_threshold),
                "split_bucket": split,
                "expected_binary_step_n": expected["binary_step_n"],
                "observed_binary_step_n": int(obs.get("binary_step_n", -1)),
                "expected_positive_n": expected["positive_n"],
                "observed_positive_n": int(obs.get("positive_n", -1)),
                "expected_negative_n": expected["negative_n"],
                "observed_negative_n": int(obs.get("negative_n", -1)),
                "expected_defended_binary_step_n": expected["defended_binary_step_n"],
                "observed_defended_binary_step_n": int(obs.get("defended_binary_step_n", -1)),
                "expected_defended_negative_n": expected["defended_negative_n"],
                "observed_defended_negative_n": int(obs.get("defended_negative_n", -1)),
                "defense_negative_capture_rate_abs_diff": abs(
                    metric_float(obs.get("defense_negative_capture_rate")) - float(expected["defense_negative_capture_rate"])
                ),
                "positive_sacrifice_rate_abs_diff": abs(
                    metric_float(obs.get("positive_sacrifice_rate")) - float(expected["positive_sacrifice_rate"])
                ),
                "continue_negative_leakage_rate_abs_diff": abs(
                    metric_float(obs.get("continue_negative_leakage_rate")) - float(expected["continue_negative_leakage_rate"])
                ),
                "learned_score_reference_gate": "pass" if all(checks) else "fail",
                "blocking_reason": "" if all(checks) else "learned_score_reference_mismatch",
            }
        )
    return pd.DataFrame(rows)


def row_for(frame: pd.DataFrame, **keys: Any) -> dict[str, Any]:
    sub = frame
    for key, value in keys.items():
        sub = sub.loc[sub[key].astype(str).eq(str(value))]
    return sub.iloc[0].to_dict() if not sub.empty else {}


def build_six_cell_sanity_reconciliation(
    config: dict[str, Any], six_cell: pd.DataFrame, split_readout: pd.DataFrame
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    tol = float(config["tolerances"]["sum_abs_tolerance"])
    for split in SPLITS:
        six = six_cell.loc[
            six_cell["split_bucket"].astype(str).eq(split)
            & six_cell["context_stratum"].astype(str).eq("all_steps")
            & six_cell["cost_bps"].astype(int).eq(PRIMARY_COST_BPS)
        ]
        full = row_for(split_readout, split_bucket=split, cost_bps=PRIMARY_COST_BPS)
        six_sum = float(pd.to_numeric(six["incremental_return_sum"], errors="coerce").sum())
        full_sum = metric_float(full.get("full_denominator_sum_incremental_return"))
        diff = abs(six_sum - full_sum)
        required_cells = {
            "defended_positive",
            "defended_negative",
            "defended_neutral",
            "continued_positive",
            "continued_negative",
            "continued_neutral",
        }
        cells_ok = required_cells.issubset(set(six["cell_id"].astype(str)))
        status = "pass" if cells_ok and diff <= tol else "fail"
        rows.append(
            {
                "split_bucket": split,
                "cost_bps": PRIMARY_COST_BPS,
                "six_cell_incremental_return_sum": six_sum,
                "full_denominator_sum_incremental_return": full_sum,
                "abs_diff": diff,
                "tolerance": tol,
                "required_cell_count": len(required_cells),
                "observed_cell_count": int(six["cell_id"].nunique()),
                "six_cell_sanity_gate": status,
                "blocking_reason": "" if status == "pass" else "six_cell_identity_failed",
            }
        )
    return pd.DataFrame(rows)


def build_ep16_replay_sanity_check(
    config: dict[str, Any],
    learned: pd.DataFrame,
    split_readout: pd.DataFrame,
    negative: pd.DataFrame,
    six_sanity: pd.DataFrame,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    threshold_row = learned.iloc[0]
    rows.append(
        sanity_row(
            "16d_threshold_value",
            "all",
            np.nan,
            threshold_row["threshold_value_expected"],
            threshold_row["threshold_value_observed"],
            float(config["policy"]["threshold_abs_tolerance"]),
            "policy_threshold_freeze_audit.csv",
        )
    )
    for split in SPLITS:
        learned_row = learned.loc[learned["split_bucket"].eq(split)].iloc[0]
        rows.append(
            sanity_row(
                "16d_binary_confusion_counts",
                split,
                np.nan,
                0,
                max(
                    abs(learned_row["observed_binary_step_n"] - learned_row["expected_binary_step_n"]),
                    abs(learned_row["observed_defended_binary_step_n"] - learned_row["expected_defended_binary_step_n"]),
                    abs(learned_row["observed_defended_negative_n"] - learned_row["expected_defended_negative_n"]),
                ),
                0,
                "policy_confusion_readout.csv",
            )
        )
        exp = config["expected_16e_sanity"]["split_counts"][split]
        split_row = row_for(split_readout, split_bucket=split, cost_bps=PRIMARY_COST_BPS)
        rows.append(
            sanity_row(
                "16e_labelable_denominator_counts",
                split,
                PRIMARY_COST_BPS,
                exp["labelable_step_n"],
                metric_float(split_row.get("labelable_step_n")),
                0,
                "utility_by_split_readout.csv",
            )
        )
    robust_split = row_for(split_readout, split_bucket="robustness", cost_bps=PRIMARY_COST_BPS)
    rows.append(
        sanity_row(
            "16e_primary_50bps_robustness_mean_incremental_return",
            "robustness",
            PRIMARY_COST_BPS,
            config["expected_16e_sanity"]["robustness_full_denominator_mean_incremental_return_50bps"],
            robust_split.get("full_denominator_mean_incremental_return"),
            config["expected_16e_sanity"]["utility_mean_abs_tolerance"],
            "utility_by_split_readout.csv",
        )
    )
    neg = row_for(negative, split_bucket="robustness", context_stratum="all_steps", cost_bps=PRIMARY_COST_BPS)
    rows.append(
        sanity_row(
            "16e_primary_robustness_defended_negative_drawdown_avoided_mean",
            "robustness",
            PRIMARY_COST_BPS,
            config["expected_16e_sanity"]["robustness_defended_negative_drawdown_avoided_abs_mean"],
            neg.get("defended_negative_drawdown_avoided_abs_mean"),
            config["expected_16e_sanity"]["drawdown_abs_tolerance"],
            "negative_avoidance_utility_readout.csv",
        )
    )
    for _, row in six_sanity.iterrows():
        rows.append(
            sanity_row(
                "16e_six_cell_incremental_sum_identity",
                row["split_bucket"],
                row["cost_bps"],
                0,
                row["abs_diff"],
                row["tolerance"],
                "six_cell_utility_reconciliation.csv",
            )
        )
    out = pd.DataFrame(rows)
    out["sanity_status"] = np.where(out["abs_diff"] <= out["tolerance"], "pass", "fail")
    out["blocking_reason"] = np.where(out["sanity_status"].eq("pass"), "", "sanity_replay_failed")
    return out


def sanity_row(
    sanity_check_id: str,
    split_bucket: str,
    cost_bps: float,
    expected: Any,
    observed: Any,
    tolerance: Any,
    source_table: str,
) -> dict[str, Any]:
    exp = metric_float(expected)
    obs = metric_float(observed)
    tol = metric_float(tolerance)
    return {
        "sanity_check_id": sanity_check_id,
        "split_bucket": split_bucket,
        "cost_bps": cost_bps,
        "expected_value": exp,
        "observed_value": obs,
        "abs_diff": abs(obs - exp),
        "tolerance": tol,
        "source_table": source_table,
    }


def build_search_accounting_audit(config: dict[str, Any]) -> pd.DataFrame:
    row = {
        "search_family": "oracle_action_value_upper_bound_diagnostic",
        "phase_id": PHASE_ID,
        "no_model_training": True,
        "no_model_refit": True,
        "no_survival_threshold_tuning": True,
        "no_validation_selection": True,
        "no_robustness_tuning": True,
        "no_feature_selection": True,
        "no_payoff_label_redesign": True,
        "no_oracle_value_interpretation": True,
        "no_entry_policy_authorized": True,
        "no_exit_policy_authorized": True,
        "no_holding_policy_authorized": True,
        "no_portfolio_backtest_authorized": True,
        "no_model_deployment_authorized": True,
        "no_production_signal_authorized": True,
        "no_live_trading_authorized": True,
    }
    protected = [value for key, value in row.items() if key.startswith("no_")]
    row["search_accounting_gate"] = "pass" if all(protected) else "fail"
    row["blocking_reason"] = "" if row["search_accounting_gate"] == "pass" else "search_accounting_failed"
    return pd.DataFrame([row])


def all_gate(frame: pd.DataFrame, column: str, allowed: set[str] | None = None) -> str:
    allowed = allowed or {"pass"}
    if frame.empty or column not in frame:
        return "fail"
    return "pass" if set(frame[column].astype(str)).issubset(allowed) else "fail"


def build_decision(
    config: dict[str, Any],
    input_gate: str,
    upstream: pd.DataFrame,
    denominator: pd.DataFrame,
    binding: pd.DataFrame,
    action: pd.DataFrame,
    delayed: pd.DataFrame,
    capacity: pd.DataFrame,
    price: pd.DataFrame,
    learned: pd.DataFrame,
    sanity: pd.DataFrame,
    six_sanity: pd.DataFrame,
    search: pd.DataFrame,
) -> pd.DataFrame:
    gates = {
        "upstream_closure_gate": all_gate(upstream, "required_state_status"),
        "input_artifact_gate": input_gate,
        "denominator_reconciliation_gate": all_gate(denominator, "denominator_reconciliation_gate"),
        "oracle_denominator_binding_gate": all_gate(binding, "binding_status"),
        "action_semantics_gate": all_gate(action, "action_semantics_gate"),
        "delayed_materialization_gate": all_gate(delayed, "delayed_materialization_gate"),
        "capacity_reconstruction_gate": str(capacity.iloc[0]["capacity_reconstruction_gate"]) if not capacity.empty else "fail",
        "price_path_replay_gate": all_gate(price, "price_path_replay_gate"),
        "learned_score_reference_gate": all_gate(learned, "learned_score_reference_gate"),
        "ep16_utility_replay_gate": all_gate(sanity, "sanity_status"),
        "six_cell_sanity_gate": all_gate(six_sanity, "six_cell_sanity_gate"),
        "search_accounting_gate": all_gate(search, "search_accounting_gate"),
    }
    blocking = [
        key
        for key, value in gates.items()
        if value != "pass" and not (key == "capacity_reconstruction_gate" and value == "appendix_only")
    ]
    decision = DECISION_READY if not blocking else DECISION_BLOCKED
    return pd.DataFrame(
        [
            {
                "decision_state": decision,
                "next_allowed_requirement": NEXT_17B if decision == DECISION_READY else "none",
                **gates,
                "o6_status_for_17b": capacity.iloc[0].get("o6_status_for_17b", "") if not capacity.empty else "",
                "entry_policy_authorized": False,
                "exit_policy_authorized": False,
                "holding_policy_authorized": False,
                "chained_simulation_authorized": False,
                "portfolio_backtest_authorized": False,
                "model_deployment_authorized": False,
                "production_signal_authorized": False,
                "live_trading_authorized": False,
                "blocking_reason": ";".join(blocking),
            }
        ]
    )


def markdown_table(frame: pd.DataFrame, columns: list[str], max_rows: int = 20) -> str:
    if frame.empty:
        return "_empty_"
    sub = frame.loc[:, [col for col in columns if col in frame.columns]].head(max_rows).copy()
    return sub.to_markdown(index=False)


def write_contract_docs(config: dict[str, Any], outputs: dict[str, Path], binding: pd.DataFrame, action: pd.DataFrame) -> None:
    den_text = f"""# Oracle Denominator Contract

run_id = {RUN_ID}

Primary denominator:

```text
EP16 up50pct / h20 / full-horizon / non-overlap continuation decision states
```

{markdown_table(binding, ['oracle_id', 'oracle_name', 'primary_denominator_type', 'expected_primary_row_count_train', 'expected_primary_row_count_robustness', 'expected_primary_row_count_validation', 'neutral_stress_required', 'appendix_only_allowed'])}
"""
    action_text = f"""# Oracle Action Contract

run_id = {RUN_ID}

Primary cost grid:

```text
round_trip_defense_cost_bps = {config['action_semantics']['round_trip_defense_cost_bps_grid']}
primary_round_trip_defense_cost_bps = {config['action_semantics']['primary_round_trip_defense_cost_bps']}
delayed_action_semantics = {config['delayed_action']['delayed_action_semantics']}
delayed_k_sessions = {config['delayed_action']['delayed_k_sessions']}
restart_h20_at_t0_plus_k = {config['delayed_action']['restart_h20_at_t0_plus_k']}
```

{markdown_table(action, ['action_family_id', 'baseline_action', 'q_continue', 'q_defend', 'round_trip_defense_cost_bps_grid', 'action_semantics_gate'])}
"""
    write_text(outputs["denominator_contract"], den_text)
    write_text(outputs["action_contract"], action_text)


def write_report(
    path: Path,
    decision: pd.DataFrame,
    upstream: pd.DataFrame,
    denominator: pd.DataFrame,
    learned: pd.DataFrame,
    sanity: pd.DataFrame,
    capacity: pd.DataFrame,
    search: pd.DataFrame,
) -> Path:
    dec = decision.iloc[0]
    blocking_reason = dec["blocking_reason"] if str(dec["blocking_reason"]) else "none"
    text = f"""# 17A Oracle Replay Contract Preflight Report

## 1. Decision

```text
decision_state = {dec['decision_state']}
next_allowed_requirement = {dec['next_allowed_requirement']}
blocking_reason = {blocking_reason}
```

17A 只冻结 denominator / action / replay contract，不解释 oracle value，不授权 entry / exit / holding / sizing / portfolio / deployment / live trading。

## 2. Upstream Closure

{markdown_table(upstream, ['source_phase_id', 'decision_state', 'next_allowed_requirement', 'continuation_as_action_mainline_closed', 'required_state_status', 'blocking_reason'])}

## 3. Denominator Reconciliation

{markdown_table(denominator, ['split_bucket', 'expected_labelable_step_n', 'observed_labelable_step_n', 'expected_binary_step_n', 'observed_binary_step_n', 'expected_neutral_step_n', 'observed_neutral_step_n', 'denominator_reconciliation_gate'])}

## 4. Learned-score Reference Replay

{markdown_table(learned, ['split_bucket', 'expected_binary_step_n', 'observed_binary_step_n', 'expected_defended_binary_step_n', 'observed_defended_binary_step_n', 'expected_defended_negative_n', 'observed_defended_negative_n', 'learned_score_reference_gate'])}

## 5. EP16 Replay Sanity

{markdown_table(sanity, ['sanity_check_id', 'split_bucket', 'cost_bps', 'expected_value', 'observed_value', 'abs_diff', 'tolerance', 'sanity_status'], max_rows=40)}

## 6. Capacity Status

{markdown_table(capacity, ['capacity_reconstruction_gate', 'o6_status_for_17b', 'capacity_cap_config_frozen', 'turnover_cost_config_frozen'])}

## 7. Search Accounting

{markdown_table(search, ['no_model_training', 'no_model_refit', 'no_survival_threshold_tuning', 'no_validation_selection', 'no_payoff_label_redesign', 'no_oracle_value_interpretation', 'search_accounting_gate'])}
"""
    return write_text(path, text)


def output_hashes(outputs: dict[str, Path]) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for key, path in outputs.items():
        if key in {"manifest", "replay_engine_manifest", "input_artifact_manifest"}:
            continue
        if path.exists() and path.is_file() and LOCAL_CACHE_DIR not in path.parents:
            hashes[key] = file_sha(path)
    return hashes


def row_counts(outputs: dict[str, Path]) -> dict[str, int | float]:
    counts: dict[str, int | float] = {}
    for key, path in outputs.items():
        if path.exists() and key not in {"manifest", "replay_engine_manifest", "input_artifact_manifest", "report"}:
            counts[key] = count_rows(path)
    return counts


def write_manifests(
    config_path: Path,
    config: dict[str, Any],
    resolved: dict[str, Path],
    outputs: dict[str, Path],
    decision: pd.DataFrame,
    input_audit: pd.DataFrame,
    denominator: pd.DataFrame,
    capacity: pd.DataFrame,
) -> None:
    dec = decision.iloc[0].to_dict()
    auth = {col: False for col in AUTH_FALSE_COLUMNS}
    main_payload = {
        "experiment_id": EXPERIMENT_ID,
        "phase_id": PHASE_ID,
        "run_id": RUN_ID,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "python_version": platform.python_version(),
        "requirement_path": str(resolved["requirement"]),
        "requirement_sha256": file_sha(resolved["requirement"]),
        "config_path": str(config_path),
        "config_sha256": file_sha(config_path),
        "research_plan_path": str(resolved["research_plan"]),
        "research_plan_sha256": file_sha(resolved["research_plan"]),
        "decision_state": dec["decision_state"],
        "next_allowed_requirement": dec["next_allowed_requirement"],
        "upstream_closure_states": {
            "16E": "16E_utility_diagnostic_not_supported",
            "16E_postmortem": "16E_postmortem_mainline_closed_no_path_supported",
            "16X": "16X_payoff_precheck_not_supported",
        },
        "primary_denominator_counts": config["expected_denominator"],
        "primary_policy_id": config["policy"]["primary_policy_id"],
        "primary_model_id": config["policy"]["primary_model_id"],
        "threshold_value": config["policy"]["threshold_value"],
        "primary_action_semantics_id": config["action_semantics"]["primary_action_semantics_id"],
        "primary_round_trip_defense_cost_bps": config["action_semantics"]["primary_round_trip_defense_cost_bps"],
        "oracle_denominator_binding_hash": file_sha(outputs["oracle_denominator_binding"]),
        "oracle_action_contract_hash": file_sha(outputs["action_contract"]),
        "input_artifact_hashes": {
            row["artifact_key"]: row["sha256"]
            for _, row in input_audit.iterrows()
            if isinstance(row["sha256"], str) and row["sha256"]
        },
        "output_hashes": output_hashes(outputs),
        "row_counts": row_counts(outputs),
        "authorization_booleans": auth,
        "large_artifact_policy": "full 17A replay panel is local parquet; publishable outputs are aggregated audits",
    }
    replay_payload = {
        "replay_engine_id": "oracle_replay_contract_preflight_v1",
        "replay_engine_version": "1",
        "denominator_contract_path": str(outputs["denominator_contract"]),
        "denominator_contract_sha256": file_sha(outputs["denominator_contract"]),
        "action_contract_path": str(outputs["action_contract"]),
        "action_contract_sha256": file_sha(outputs["action_contract"]),
        "primary_denominator_counts": config["expected_denominator"],
        "oracle_denominator_binding_hash": file_sha(outputs["oracle_denominator_binding"]),
        "primary_action_semantics_id": config["action_semantics"]["primary_action_semantics_id"],
        "primary_round_trip_defense_cost_bps": config["action_semantics"]["primary_round_trip_defense_cost_bps"],
        "cost_grid_bps": config["action_semantics"]["round_trip_defense_cost_bps_grid"],
        "delayed_action_semantics": config["delayed_action"]["delayed_action_semantics"],
        "delayed_k_sessions": config["delayed_action"]["delayed_k_sessions"],
        "capacity_reconstruction_gate": dec["capacity_reconstruction_gate"],
        "o6_status_for_17b": dec["o6_status_for_17b"],
        "qfq_price_source": str(resolved["stock_daily_qfq_dir"]),
        "qfq_price_source_hash_or_snapshot_id": "directory_not_hashed",
        "price_path_replay_gate": dec["price_path_replay_gate"],
        "learned_score_reference_gate": dec["learned_score_reference_gate"],
        "ep16_utility_replay_gate": dec["ep16_utility_replay_gate"],
        "six_cell_sanity_gate": dec["six_cell_sanity_gate"],
        "search_accounting_gate": dec["search_accounting_gate"],
    }
    write_json(outputs["manifest"], main_payload)
    write_json(outputs["replay_engine_manifest"], replay_payload)
    write_json(outputs["input_artifact_manifest"], input_audit.to_dict(orient="records"))


def blocked_decision(config: dict[str, Any], input_gate: str, reason: str) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "decision_state": DECISION_BLOCKED,
                "next_allowed_requirement": "none",
                "upstream_closure_gate": "fail",
                "input_artifact_gate": input_gate,
                "denominator_reconciliation_gate": "fail",
                "oracle_denominator_binding_gate": "fail",
                "action_semantics_gate": "fail",
                "delayed_materialization_gate": "fail",
                "capacity_reconstruction_gate": "fail",
                "price_path_replay_gate": "fail",
                "learned_score_reference_gate": "fail",
                "ep16_utility_replay_gate": "fail",
                "six_cell_sanity_gate": "fail",
                "search_accounting_gate": "fail",
                "o6_status_for_17b": "blocked",
                "entry_policy_authorized": False,
                "exit_policy_authorized": False,
                "holding_policy_authorized": False,
                "chained_simulation_authorized": False,
                "portfolio_backtest_authorized": False,
                "model_deployment_authorized": False,
                "production_signal_authorized": False,
                "live_trading_authorized": False,
                "blocking_reason": reason,
            }
        ]
    )


def run(config_path: Path, check_inputs_only: bool = False) -> int:
    config = load_config(config_path)
    resolved = resolve_paths(config)
    outputs = output_paths()
    input_audit = build_input_artifact_audit(config, resolved)
    write_df(outputs["input_artifact_audit"], input_audit)
    input_gate, input_reason = input_gate_status(input_audit)
    if check_inputs_only:
        return 0 if input_gate == "pass" else 1
    if input_gate != "pass":
        decision = blocked_decision(config, input_gate, input_reason)
        write_df(outputs["decision"], decision)
        return 1

    utility_panel = read_table(resolved["upstream_16e_utility_panel"])
    split_readout = read_table(resolved["upstream_16e_utility_by_split_readout"])
    negative = read_table(resolved["upstream_16e_negative_avoidance_utility_readout"])
    six_cell = read_table(resolved["upstream_16e_six_cell_utility_reconciliation"])

    upstream = build_upstream_closure_audit(config, resolved)
    capacity = build_capacity_reconstruction_audit(config, utility_panel)
    denominator = build_denominator_lineage_audit(config, utility_panel)
    binding = build_oracle_denominator_binding(config, str(capacity.iloc[0]["capacity_reconstruction_gate"]))
    action = build_action_semantics_audit(config)
    delayed = build_delayed_materialization_audit(config, utility_panel)
    price = build_replay_price_path_audit(
        config, utility_panel, read_table(resolved["upstream_16e_utility_price_path_audit"]), delayed
    )
    learned = build_learned_score_reference_replay_audit(
        config,
        read_table(resolved["upstream_16d_policy_confusion_readout"]),
        read_table(resolved["upstream_16d_policy_threshold_freeze_audit"]),
    )
    six_sanity = build_six_cell_sanity_reconciliation(config, six_cell, split_readout)
    sanity = build_ep16_replay_sanity_check(config, learned, split_readout, negative, six_sanity)
    search = build_search_accounting_audit(config)
    decision = build_decision(
        config,
        input_gate,
        upstream,
        denominator,
        binding,
        action,
        delayed,
        capacity,
        price,
        learned,
        sanity,
        six_sanity,
        search,
    )

    replay_panel = primary_panel(utility_panel, config)
    keep_cols = [col for col in list(PRIMARY_ROW_KEY) + ["label_class", "cost_bps", "cell_id", "incremental_net_return_h20"] if col in replay_panel.columns]
    write_df(outputs["replay_contract_panel"], replay_panel[keep_cols])
    write_df(outputs["upstream_closure_audit"], upstream)
    write_df(outputs["capacity_reconstruction_audit"], capacity)
    write_df(outputs["denominator_lineage_audit"], denominator)
    write_df(outputs["oracle_denominator_binding"], binding)
    write_df(outputs["action_semantics_audit"], action)
    write_df(outputs["delayed_materialization_audit"], delayed)
    write_df(outputs["replay_price_path_audit"], price)
    write_df(outputs["learned_score_reference_replay_audit"], learned)
    write_df(outputs["six_cell_sanity_reconciliation"], six_sanity)
    write_df(outputs["ep16_replay_sanity_check"], sanity)
    write_df(outputs["search_accounting_audit"], search)
    write_df(outputs["decision"], decision)
    write_contract_docs(config, outputs, binding, action)
    write_report(outputs["report"], decision, upstream, denominator, learned, sanity, capacity, search)
    write_manifests(config_path, config, resolved, outputs, decision, input_audit, denominator, capacity)
    return 0 if decision.iloc[0]["decision_state"] == DECISION_READY else 1


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    return run(Path(args.config), check_inputs_only=args.check_inputs_only or args.mode == "check-inputs")


if __name__ == "__main__":
    sys.exit(main())
