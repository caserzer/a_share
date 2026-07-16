#!/usr/bin/env python3
"""Materialize the 20B-P4 portfolio-sensitivity diagnostic.

The module deliberately separates pure portfolio mechanics from historical
materialization.  Importing it is safe: no history is read and no output path
is created.  The CLI refuses historical replay unless both historical outcome
and portfolio replay authority are true in the exact resolved config.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
import os
import shutil
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import yaml


REPO_ROOT = Path(__file__).resolve().parents[6]
EXPERIMENT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = (
    EXPERIMENT_ROOT
    / "configs/config_20b_p4_d8_d10_sector_crowding_cost_stoploss_sensitivity.yaml"
)

RUN_ID = "20B_P4_d8_d10_sector_crowding_cost_stoploss_sensitivity_v6"
CONTRACT_VERSION = "20B_P4_PORTSENS_v6"
SCHEMA_VERSION = "20B_P4_PORTSENS_OUTPUT_v1"
NO_BOARD = "__NO_BOARD__"
REFERENCE_COST_SCENARIO = "SLIP005"
EVENT_MONTHS = frozenset({"2024-10", "2025-02", "2025-08", "2025-09", "2026-04"})
MODEL_IDS = ("S0_SELECTED_FULL", "B0_P4_RAW_RANK")
BUCKET_IDS = (8, 9, 10)
LAMBDA_GRID = (0.0, 0.5, 1.0)
STOP_GRID: tuple[float | None, ...] = (None, 0.05, 0.10, 0.15, 0.20)
COST_IDS = ("GROSS", "SLIP000", "SLIP005", "SLIP010", "SLIP020", "SLIP040")
DECISION_NAME = "20B_P4_d8_d10_sector_crowding_cost_stoploss_sensitivity_decision.csv"
REPORT_NAME = "20B_P4_d8_d10_sector_crowding_cost_stoploss_sensitivity_report_cn.md"
MANIFEST_NAME = "manifest_20b_p4_portsens.json"
HASHES_NAME = "output_hashes_20b_p4_portsens.json"


class ContractError(RuntimeError):
    """Raised when a frozen contract condition is not met."""


class AuthorizationError(ContractError):
    """Raised before output creation when historical replay lacks authority."""


class SealError(ContractError):
    """Raised when candidate bytes cannot be published as an immutable bundle."""


class ReplayStageError(ContractError):
    """Raised with the highest completed artifact profile for a replay failure."""

    def __init__(
        self,
        message: str,
        *,
        profile_id: str,
        reached_stage: str,
        stage_results: Sequence[StageResult],
        scratch_root: Path,
    ) -> None:
        super().__init__(message)
        self.profile_id = profile_id
        self.reached_stage = reached_stage
        self.stage_results = tuple(stage_results)
        self.scratch_root = scratch_root


@dataclass(frozen=True)
class StageResult:
    gate: bool
    stage_id: str
    check_id: str
    expected: str
    observed: str
    affected_artifacts: str
    blocking_reason: str


@dataclass
class Position:
    shares: float
    basis_qfq: float
    last_mark_qfq: float
    holding_spell_id: str
    pending_exit_reason: str = ""
    stop_latched_date: pd.Timestamp | None = None


@dataclass(frozen=True)
class MappingResult:
    factor: float
    relative_spread: float
    warning: bool
    factor_mapping_pass: bool
    raw_trigger_tick: float
    raw_fill_domain_lower: float
    raw_fill_domain_upper: float
    fill_domain_pass: bool
    mapping_pass: bool
    qfq_fill: float


EXPECTED_SECTION_KEYS: dict[str, set[str]] = {
    "identity": {"experiment_id", "phase_id", "run_id", "contract_version"},
    "authorization": {
        "requirement_generation_authorized",
        "requirement_execution_authorized",
        "implementation_authorized",
        "historical_outcome_execution_authorized",
        "portfolio_replay_authorized",
        "deployment_authorized",
    },
    "paths": {
        "requirement_file",
        "MLRANK_ROOT",
        "CONTRACT20A_ROOT",
        "BOARD_MEMBER",
        "RAW_OHLCV_ROOT",
        "QFQ_ROOT",
        "TRADING_CALENDAR_FILE",
        "PROJECT_UNIVERSE_FILE",
        "SECURITY_MASTER_FILE",
        "SH_NAME_HISTORY_ROOT",
        "SZ_NAME_HISTORY_FILE",
        "MARKET_RULE_REGISTRY_FILE",
        "output_root",
        "replay_a_scratch_root",
        "replay_b_scratch_root",
    },
    "upstream_hashes": {
        "MLRANK_REGISTRY_sha256",
        "MLRANK_MANIFEST_sha256",
        "MLRANK_DECISION_sha256",
        "BUCKET_ASSIGNMENT_sha256",
        "CONTRACT20A_REGISTRY_sha256",
        "CONTRACT20A_MANIFEST_sha256",
        "CONTRACT20A_FREEZE_REGISTRY_sha256",
        "BOARD_MEMBER_sha256",
        "RAW_OHLCV_ROOT_hash",
        "QFQ_ROOT_hash",
        "TRADING_CALENDAR_FILE_sha256",
        "PROJECT_UNIVERSE_FILE_sha256",
        "SECURITY_MASTER_FILE_sha256",
        "SH_NAME_HISTORY_ROOT_hash",
        "SZ_NAME_HISTORY_FILE_sha256",
        "MARKET_RULE_REGISTRY_FILE_sha256",
    },
    "population": {
        "scored_model_ids",
        "bucket_ids",
        "split",
        "decision_date_min",
        "decision_date_max",
        "decision_month_n",
        "ledger_start_date",
        "ledger_end_date",
        "ledger_trade_date_n",
        "event_label_months",
    },
    "board_concentration": {
        "proxy_id",
        "snapshot_trade_date",
        "reference_universe_rule",
        "reference_universe_dependency",
        "minimum_reference_member_n",
        "duplicate_column_rule",
        "no_board_id",
        "fractional_membership_rule",
        "no_board_tilt_rule",
        "percentile_formula",
        "lambda_grid",
        "target_weight_formula",
        "single_instrument_weight_cap",
        "classified_concentration_formula",
        "concentration_observation_timing",
    },
    "stop": {
        "threshold_grid",
        "basis_formula",
        "trigger_order",
        "tick_mapping",
        "mapping_warning_spread",
        "mapping_block_spread",
        "raw_fill_domain_rule",
        "blocked_exit_latch",
        "reentry_rule",
        "event_attribution_horizon",
    },
    "execution": {
        "initial_AUM_cny",
        "decision_timing",
        "rebalance_timing",
        "lot_rule",
        "entry_limit_up_rule",
        "exit_limit_down_rule",
        "no_borrowing",
        "leverage_allowed",
        "short_allowed",
        "capital_injection_allowed",
        "monthly_reset_allowed",
        "suspension_mark_rule",
        "corporate_action_rule",
        "terminal_liquidation_shadow_rule",
    },
    "cost": {
        "commission_buy_bps",
        "commission_sell_bps",
        "minimum_commission_cny",
        "stamp_tax_sell_bps",
        "stamp_tax_effective_start",
        "transfer_fee_source",
        "slippage_bps_grid",
        "reference_slippage_bps",
        "cost_scenario_ids",
        "cost_shadow_accounting",
        "target_turnover_formula",
        "break_even_terminal_wealth_formula",
        "break_even_root_status_precedence",
        "break_even_root_bracket_bps",
        "break_even_root_tolerance_bps",
        "break_even_root_max_iterations",
    },
    "statistics": {
        "month_scopes",
        "paired_comparison_n",
        "bootstrap_method",
        "block_length_months",
        "repetitions",
        "rng",
        "seed",
        "random_consumption_order",
        "incomplete_calendar_rule",
        "sampled_block_count",
        "quantiles",
        "quantile_method",
    },
    "serialization": {
        "csv_encoding",
        "csv_newline",
        "csv_na_rep",
        "csv_float_format",
        "gzip_compresslevel",
        "gzip_mtime",
        "json_ensure_ascii",
        "json_sort_keys",
        "json_indent",
        "json_final_newline",
        "parquet_engine",
        "parquet_version",
        "parquet_compression",
        "parquet_compression_level",
        "parquet_use_dictionary",
        "parquet_write_statistics",
        "parquet_data_page_version",
        "parquet_row_group_size",
    },
    "output_contract": {
        "schema_version",
        "profile_ids",
        "artifact_groups",
        "profiles",
        "manifest_name",
        "output_hashes_name",
        "decision_name",
        "report_name",
        "schema_registry_id",
        "seal_failure_exit_code",
    },
}


POLICY_COLUMNS = [
    "policy_id",
    "scored_model_id",
    "bucket_id",
    "sector_tilt_lambda",
    "stop_threshold",
    "board_semantics_role",
    "execution_role",
    "claim_ceiling",
    "run_id",
    "contract_version",
]
COST_COLUMNS = [
    "cost_scenario_id",
    "slippage_bps_per_side",
    "statutory_costs_enabled",
    "commission_enabled",
    "gross_scenario",
    "reference_execution_scenario",
    "counterfactual_cost_shadow",
    "deployment_interpretation_allowed",
    "run_id",
    "contract_version",
]
COMPARISON_COLUMNS = [
    "comparison_id",
    "comparison_family",
    "lhs_policy_id",
    "lhs_cost_scenario_id",
    "rhs_policy_id",
    "rhs_cost_scenario_id",
    "changed_dimension",
    "only_one_dimension_changed",
    "primary_OFAT",
    "favorable_direction",
    "run_id",
    "contract_version",
]
TARGET_COLUMNS = [
    "policy_id",
    "decision_date",
    "instrument_id",
    "scored_model_id",
    "bucket_id",
    "sector_tilt_lambda",
    "stop_threshold",
    "nominal_bucket_n",
    "board_membership_n",
    "stock_concentration_tilt_score",
    "raw_weight_multiplier",
    "target_weight",
    "target_weight_sum",
    "target_concentration_pass",
    "source_bucket_assignment_sha256",
    "board_member_sha256",
    "run_id",
    "contract_version",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json_bytes(value: Any, *, compact: bool = False) -> bytes:
    kwargs: dict[str, Any] = {
        "ensure_ascii": False,
        "sort_keys": True,
        "allow_nan": False,
    }
    if compact:
        kwargs["separators"] = (",", ":")
    else:
        kwargs["indent"] = 2
        kwargs["separators"] = (",", ": ")
    return (json.dumps(value, **kwargs) + "\n").encode("utf-8")


def stable_hash(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value, compact=True)).hexdigest()


def _normalize_float(value: Any) -> Any:
    if isinstance(value, float) and value == 0.0:
        return 0.0
    return value


def normalize_frame(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    for column in result.select_dtypes(include=["float"]).columns:
        values = result[column].to_numpy(copy=True)
        values[values == 0.0] = 0.0
        result[column] = values
    return result


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json_bytes(value))


def write_yaml(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = yaml.safe_dump(
        value,
        allow_unicode=True,
        sort_keys=False,
        default_flow_style=False,
    )
    path.write_text(payload, encoding="utf-8", newline="\n")


def write_csv(path: Path, frame: pd.DataFrame, columns: Sequence[str]) -> None:
    missing = [column for column in columns if column not in frame.columns]
    extra = [column for column in frame.columns if column not in columns]
    if missing or extra:
        raise ContractError(
            f"schema mismatch for {path}: missing={missing}, extra={extra}"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = (
        normalize_frame(frame.loc[:, list(columns)])
        .to_csv(
            None,
            index=False,
            na_rep="",
            float_format="%.12g",
            lineterminator="\n",
        )
        .encode("utf-8")
    )
    if path.suffix == ".gz":
        with path.open("wb") as raw:
            with gzip.GzipFile(
                filename="",
                mode="wb",
                fileobj=raw,
                compresslevel=9,
                mtime=0,
            ) as handle:
                handle.write(payload)
    else:
        path.write_bytes(payload)


def write_parquet(path: Path, frame: pd.DataFrame, columns: Sequence[str]) -> None:
    missing = [column for column in columns if column not in frame.columns]
    extra = [column for column in frame.columns if column not in columns]
    if missing or extra:
        raise ContractError(
            f"schema mismatch for {path}: missing={missing}, extra={extra}"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    table = pa.Table.from_pandas(
        normalize_frame(frame.loc[:, list(columns)]),
        preserve_index=False,
    )
    pq.write_table(
        table,
        path,
        version="2.6",
        compression="zstd",
        compression_level=9,
        use_dictionary=False,
        write_statistics=True,
        data_page_version="2.0",
        row_group_size=65536,
    )


def root_inventory_hash(path: Path) -> tuple[str, int, int]:
    rows: list[str] = []
    total = 0
    files = sorted(path.glob("*.csv"), key=lambda item: item.name)
    for item in files:
        size = item.stat().st_size
        total += size
        rows.append(f"{item.name}|{size}|{sha256_file(item)}")
    digest = hashlib.sha256("\n".join(rows).encode("utf-8")).hexdigest()
    return digest, len(files), total


def resolve_repo_path(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else (REPO_ROOT / path).resolve()


def validate_config(config: Mapping[str, Any]) -> None:
    expected_top = set(EXPECTED_SECTION_KEYS)
    actual_top = set(config)
    if actual_top != expected_top:
        raise ContractError(
            f"config top-level keys differ: missing={sorted(expected_top - actual_top)}, "
            f"extra={sorted(actual_top - expected_top)}"
        )
    for section, expected in EXPECTED_SECTION_KEYS.items():
        node = config[section]
        if not isinstance(node, Mapping):
            raise ContractError(f"config section is not a mapping: {section}")
        actual = set(node)
        if actual != expected:
            raise ContractError(
                f"config keys differ for {section}: "
                f"missing={sorted(expected - actual)}, extra={sorted(actual - expected)}"
            )
    identity = config["identity"]
    if identity["run_id"] != RUN_ID or identity["contract_version"] != CONTRACT_VERSION:
        raise ContractError("run or contract identity mismatch")
    if tuple(config["population"]["scored_model_ids"]) != MODEL_IDS:
        raise ContractError("scored_model_ids mismatch")
    if tuple(config["population"]["bucket_ids"]) != BUCKET_IDS:
        raise ContractError("bucket_ids mismatch")
    if (
        tuple(float(x) for x in config["board_concentration"]["lambda_grid"])
        != LAMBDA_GRID
    ):
        raise ContractError("lambda grid mismatch")
    stops = tuple(
        None if value is None else float(value)
        for value in config["stop"]["threshold_grid"]
    )
    if stops != STOP_GRID:
        raise ContractError("stop grid mismatch")
    if tuple(config["cost"]["cost_scenario_ids"]) != COST_IDS:
        raise ContractError("cost scenario ids mismatch")
    if int(config["statistics"]["paired_comparison_n"]) != 284:
        raise ContractError("paired comparison count mismatch")
    if config["board_concentration"]["reference_universe_dependency"] != (
        "retrospective_full_sample_universe_dependency"
    ):
        raise ContractError("board reference-universe dependency mismatch")
    if config["board_concentration"]["no_board_tilt_rule"] != (
        "neutral_0_5_excluded_from_rank_and_concentration"
    ):
        raise ContractError("no-board semantics mismatch")
    if config["authorization"]["deployment_authorized"] is not False:
        raise ContractError("deployment must remain unauthorized")
    output = config["output_contract"]
    if output["schema_version"] != SCHEMA_VERSION:
        raise ContractError("output schema version mismatch")
    if output["manifest_name"] != MANIFEST_NAME:
        raise ContractError("manifest name mismatch")
    if output["output_hashes_name"] != HASHES_NAME:
        raise ContractError("hash registry name mismatch")
    validate_profile_contract(output)


def load_config(path: str | Path = DEFAULT_CONFIG) -> tuple[dict[str, Any], Path]:
    config_path = Path(path).resolve()
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if not isinstance(config, dict):
        raise ContractError("config root must be a mapping")
    validate_config(config)
    return config, config_path


def resolved_paths(config: Mapping[str, Any]) -> dict[str, Path]:
    return {key: resolve_repo_path(value) for key, value in config["paths"].items()}


def require_historical_authority(config: Mapping[str, Any]) -> None:
    authority = config["authorization"]
    if not authority["implementation_authorized"]:
        raise AuthorizationError("implementation_authorized=false")
    if not authority["historical_outcome_execution_authorized"]:
        raise AuthorizationError("historical_outcome_execution_authorized=false")
    if not authority["portfolio_replay_authorized"]:
        raise AuthorizationError("portfolio_replay_authorized=false")


def normalize_instrument(value: Any) -> str:
    text = str(value).strip().upper()
    if text.startswith(("SH", "SZ", "BJ")) and len(text) == 8:
        return text
    if "." in text:
        code, exchange = text.split(".", 1)
        return f"{exchange}{code}"
    if text.isdigit() and len(text) == 6:
        if text.startswith(("4", "8")):
            return f"BJ{text}"
        if text.startswith(("5", "6", "9")):
            return f"SH{text}"
        return f"SZ{text}"
    raise ContractError(f"cannot normalize instrument: {value!r}")


def lambda_token(value: float) -> str:
    mapping = {0.0: "000", 0.5: "050", 1.0: "100"}
    try:
        return mapping[float(value)]
    except KeyError as exc:
        raise ContractError(f"unknown lambda: {value}") from exc


def stop_token(value: float | None) -> str:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return "NONE"
    mapping = {0.05: "05", 0.10: "10", 0.15: "15", 0.20: "20"}
    try:
        return mapping[float(value)]
    except KeyError as exc:
        raise ContractError(f"unknown stop threshold: {value}") from exc


def make_policy_id(
    scored_model_id: str,
    bucket_id: int,
    sector_tilt_lambda: float,
    stop_threshold: float | None,
) -> str:
    return (
        f"{scored_model_id}__D{int(bucket_id)}__L{lambda_token(sector_tilt_lambda)}"
        f"__STOP{stop_token(stop_threshold)}"
    )


def build_policy_arm_registry() -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for model in MODEL_IDS:
        for bucket in BUCKET_IDS:
            for lam in LAMBDA_GRID:
                for stop in STOP_GRID:
                    rows.append(
                        {
                            "policy_id": make_policy_id(model, bucket, lam, stop),
                            "scored_model_id": model,
                            "bucket_id": bucket,
                            "sector_tilt_lambda": lam,
                            "stop_threshold": stop,
                            "board_semantics_role": (
                                "equal_weight_no_board_decision"
                                if lam == 0.0
                                else "retrospective_non_pit_concentration_tilt"
                            ),
                            "execution_role": "stateful_reference_5bps_path",
                            "claim_ceiling": (
                                "design_contaminated_posthoc_portfolio_sensitivity_only"
                            ),
                            "run_id": RUN_ID,
                            "contract_version": CONTRACT_VERSION,
                        }
                    )
    frame = pd.DataFrame(rows).sort_values(
        ["scored_model_id", "bucket_id", "sector_tilt_lambda", "stop_threshold"],
        na_position="first",
        kind="mergesort",
    )
    frame = frame.reset_index(drop=True)
    if len(frame) != 90 or frame["policy_id"].duplicated().any():
        raise ContractError("policy arm registry is not exact-set 90")
    return frame.loc[:, POLICY_COLUMNS]


def build_cost_scenario_registry() -> pd.DataFrame:
    slip = {
        "GROSS": 0.0,
        "SLIP000": 0.0,
        "SLIP005": 5.0,
        "SLIP010": 10.0,
        "SLIP020": 20.0,
        "SLIP040": 40.0,
    }
    rows = []
    for scenario in COST_IDS:
        gross = scenario == "GROSS"
        rows.append(
            {
                "cost_scenario_id": scenario,
                "slippage_bps_per_side": slip[scenario],
                "statutory_costs_enabled": not gross,
                "commission_enabled": not gross,
                "gross_scenario": gross,
                "reference_execution_scenario": scenario == REFERENCE_COST_SCENARIO,
                "counterfactual_cost_shadow": scenario != REFERENCE_COST_SCENARIO,
                "deployment_interpretation_allowed": False,
                "run_id": RUN_ID,
                "contract_version": CONTRACT_VERSION,
            }
        )
    return pd.DataFrame(rows).loc[:, COST_COLUMNS]


def _comparison_row(
    comparison_id: str,
    family: str,
    lhs_policy: str,
    lhs_cost: str,
    rhs_policy: str,
    rhs_cost: str,
    changed: str,
    primary: bool,
) -> dict[str, Any]:
    return {
        "comparison_id": comparison_id,
        "comparison_family": family,
        "lhs_policy_id": lhs_policy,
        "lhs_cost_scenario_id": lhs_cost,
        "rhs_policy_id": rhs_policy,
        "rhs_cost_scenario_id": rhs_cost,
        "changed_dimension": changed,
        "only_one_dimension_changed": True,
        "primary_OFAT": primary,
        "favorable_direction": "lhs_minus_rhs_higher_is_better",
        "run_id": RUN_ID,
        "contract_version": CONTRACT_VERSION,
    }


def build_paired_comparison_registry() -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    reference = REFERENCE_COST_SCENARIO
    base = lambda bucket, lam, stop: make_policy_id(  # noqa: E731
        "S0_SELECTED_FULL", bucket, lam, stop
    )
    for lhs_bucket, rhs_bucket in ((9, 8), (10, 9), (10, 8)):
        rows.append(
            _comparison_row(
                f"OFAT_BUCKET__D{lhs_bucket}_MINUS_D{rhs_bucket}",
                "OFAT_BUCKET",
                base(lhs_bucket, 0.0, None),
                reference,
                base(rhs_bucket, 0.0, None),
                reference,
                "bucket_id",
                True,
            )
        )
    for lam in (0.5, 1.0):
        rows.append(
            _comparison_row(
                f"OFAT_SECTOR__L{lambda_token(lam)}_MINUS_L000",
                "OFAT_SECTOR_CONCENTRATION",
                base(10, lam, None),
                reference,
                base(10, 0.0, None),
                reference,
                "sector_tilt_lambda",
                True,
            )
        )
    for stop in (0.05, 0.10, 0.15, 0.20):
        rows.append(
            _comparison_row(
                f"OFAT_STOP__STOP{stop_token(stop)}_MINUS_NONE",
                "OFAT_STOP",
                base(10, 0.0, stop),
                reference,
                base(10, 0.0, None),
                reference,
                "stop_threshold",
                True,
            )
        )
    for cost in ("GROSS", "SLIP000", "SLIP010", "SLIP020", "SLIP040"):
        rows.append(
            _comparison_row(
                f"OFAT_COST__{cost}_MINUS_SLIP005",
                "OFAT_COST",
                base(10, 0.0, None),
                cost,
                base(10, 0.0, None),
                reference,
                "cost_scenario_id",
                True,
            )
        )
    for bucket in BUCKET_IDS:
        for lam in LAMBDA_GRID:
            for stop in STOP_GRID:
                for cost in COST_IDS:
                    lhs = make_policy_id("S0_SELECTED_FULL", bucket, lam, stop)
                    rhs = make_policy_id("B0_P4_RAW_RANK", bucket, lam, stop)
                    rows.append(
                        _comparison_row(
                            (
                                f"MODEL__D{bucket}__L{lambda_token(lam)}"
                                f"__STOP{stop_token(stop)}__{cost}"
                            ),
                            "MODEL_S0_VS_B0_FULL_GRID",
                            lhs,
                            cost,
                            rhs,
                            cost,
                            "scored_model_id",
                            False,
                        )
                    )
    frame = pd.DataFrame(rows)
    if len(frame) != 284 or frame["comparison_id"].duplicated().any():
        raise ContractError("paired comparison registry is not exact-set 284")
    return frame.loc[:, COMPARISON_COLUMNS]


def _member_vector_hash(members: Iterable[str], reference: Sequence[str]) -> str:
    member_set = set(members)
    payload = "".join("1" if item in member_set else "0" for item in reference)
    return hashlib.sha256(payload.encode("ascii")).hexdigest()


def build_board_dictionary(
    reference_universe: Sequence[str],
    board_members: pd.DataFrame,
    minimum_member_n: int = 10,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Return registry, fractional membership and one-row source audit."""
    reference = tuple(
        sorted({normalize_instrument(item) for item in reference_universe})
    )
    if not reference:
        raise ContractError("empty board reference universe")
    required = {"board_ts_code", "con_code"}
    if not required.issubset(board_members.columns):
        raise ContractError(
            f"board source missing columns: {sorted(required - set(board_members))}"
        )
    normalized = board_members.loc[:, ["board_ts_code", "con_code"]].copy()
    normalized["board_ts_code"] = normalized["board_ts_code"].astype(str)
    normalized["instrument_id"] = normalized["con_code"].map(normalize_instrument)
    normalized = normalized.drop_duplicates(["board_ts_code", "instrument_id"])
    normalized = normalized[normalized["instrument_id"].isin(reference)]

    board_sets = {
        board: set(group["instrument_id"])
        for board, group in normalized.groupby("board_ts_code", sort=True)
    }
    vector_hashes = {
        board: _member_vector_hash(members, reference)
        for board, members in board_sets.items()
    }
    duplicate_groups: dict[str, list[str]] = {}
    for board, vector_hash in vector_hashes.items():
        duplicate_groups.setdefault(vector_hash, []).append(board)
    retained_sources = {
        min(boards)
        for vector_hash, boards in duplicate_groups.items()
        if len(board_sets[boards[0]]) >= minimum_member_n
    }
    duplicate_n = sum(max(0, len(boards) - 1) for boards in duplicate_groups.values())
    registry_rows: list[dict[str, Any]] = []
    for board in sorted(board_sets):
        vector_hash = vector_hashes[board]
        kept = min(duplicate_groups[vector_hash])
        minimum_pass = len(board_sets[board]) >= minimum_member_n
        registry_rows.append(
            {
                "source_board_ts_code": board,
                "reference_member_n": len(board_sets[board]),
                "minimum_member_pass": minimum_pass,
                "duplicate_group_id": vector_hash,
                "retained_board_id": kept if minimum_pass else "",
                "retained": minimum_pass and board == kept,
                "synthetic": False,
                "board_member_sha256": vector_hash,
                "run_id": RUN_ID,
                "contract_version": CONTRACT_VERSION,
            }
        )
    no_board_hash = stable_hash({"reference": reference, "synthetic": NO_BOARD})
    registry_rows.append(
        {
            "source_board_ts_code": NO_BOARD,
            "reference_member_n": 0,
            "minimum_member_pass": False,
            "duplicate_group_id": NO_BOARD,
            "retained_board_id": NO_BOARD,
            "retained": True,
            "synthetic": True,
            "board_member_sha256": no_board_hash,
            "run_id": RUN_ID,
            "contract_version": CONTRACT_VERSION,
        }
    )
    registry = pd.DataFrame(registry_rows).sort_values("source_board_ts_code")

    retained = sorted(retained_sources)
    retained_map: dict[str, list[str]] = {instrument: [] for instrument in reference}
    for board in retained:
        for instrument in board_sets[board]:
            retained_map[instrument].append(board)
    membership_rows: list[dict[str, Any]] = []
    for instrument in reference:
        boards = retained_map[instrument]
        if not boards:
            membership_rows.append(
                {
                    "instrument_id": instrument,
                    "retained_board_id": NO_BOARD,
                    "membership_weight": 1.0,
                    "board_membership_n": 0,
                }
            )
            continue
        weight = 1.0 / len(boards)
        for board in boards:
            membership_rows.append(
                {
                    "instrument_id": instrument,
                    "retained_board_id": board,
                    "membership_weight": weight,
                    "board_membership_n": len(boards),
                }
            )
    membership = pd.DataFrame(membership_rows).sort_values(
        ["instrument_id", "retained_board_id"]
    )
    sums = membership.groupby("instrument_id")["membership_weight"].sum()
    if not np.allclose(sums.to_numpy(), 1.0, atol=1e-12, rtol=0.0):
        raise ContractError("fractional board memberships do not sum to one")
    audit = pd.DataFrame(
        [
            {
                "proxy_id": "ep19_dc_2025_static_board_proxy",
                "snapshot_trade_date": "2025-01-02",
                "source_path": "",
                "source_sha256": "",
                "raw_member_row_n": len(board_members),
                "normalized_member_row_n": len(normalized),
                "invalid_instrument_row_n": 0,
                "reference_universe_instrument_n": len(reference),
                "reference_overlap_instrument_n": normalized["instrument_id"].nunique(),
                "retained_board_n": len(retained),
                "duplicate_board_n": duplicate_n,
                "no_board_instrument_n": int(
                    membership["retained_board_id"].eq(NO_BOARD).sum()
                ),
                "board_reference_universe_dependency": (
                    "retrospective_full_sample_universe_dependency"
                ),
                "historical_PIT_industry_claim_allowed": False,
                "board_membership_currentness_claim": False,
                "board_formula_gate": True,
                "blocking_reason": "",
                "run_id": RUN_ID,
                "contract_version": CONTRACT_VERSION,
            }
        ]
    )
    return registry.reset_index(drop=True), membership.reset_index(drop=True), audit


def compute_overrepresentation(
    universe_assignment: pd.DataFrame,
    membership: pd.DataFrame,
    target_bucket_ids: Sequence[int] = BUCKET_IDS,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Compute board readout and stock tilt scores for every model/month/bucket."""
    required = {"scored_model_id", "decision_date", "bucket_id", "instrument_id"}
    if not required.issubset(universe_assignment.columns):
        raise ContractError("assignment lacks board-formula columns")
    if universe_assignment.duplicated(
        ["scored_model_id", "decision_date", "instrument_id"]
    ).any():
        raise ContractError("duplicate model-month instrument assignment")
    weights = membership.loc[
        :,
        [
            "instrument_id",
            "retained_board_id",
            "membership_weight",
            "board_membership_n",
        ],
    ]
    all_boards = sorted(set(weights["retained_board_id"].astype(str)) - {NO_BOARD})
    board_rows: list[dict[str, Any]] = []
    score_rows: list[dict[str, Any]] = []
    grouped = universe_assignment.groupby(
        ["scored_model_id", "decision_date"], sort=True
    )
    for (model, decision_date), universe in grouped:
        universe = universe.merge(
            weights, on="instrument_id", how="left", validate="one_to_many"
        )
        if universe["membership_weight"].isna().any():
            raise ContractError(
                "assignment instrument missing from board reference universe"
            )
        universe_share = universe.groupby("retained_board_id")[
            "membership_weight"
        ].sum()
        universe_share = universe_share / universe["instrument_id"].nunique()
        for bucket in target_bucket_ids:
            target_ids = set(
                universe.loc[universe["bucket_id"].eq(bucket), "instrument_id"]
            )
            target = universe[universe["instrument_id"].isin(target_ids)]
            if not target_ids:
                raise ContractError(
                    f"empty target bucket: {model} {decision_date} D{bucket}"
                )
            bucket_share = target.groupby("retained_board_id")[
                "membership_weight"
            ].sum()
            bucket_share = bucket_share / len(target_ids)
            records: list[dict[str, Any]] = []
            for board in [*all_boards, NO_BOARD]:
                u_share = float(universe_share.get(board, 0.0))
                b_share = float(bucket_share.get(board, 0.0))
                ratio = (b_share + 1e-12) / (u_share + 1e-12) if u_share > 0 else np.nan
                records.append(
                    {
                        "retained_board_id": board,
                        "universe_member_fraction": u_share,
                        "bucket_member_fraction": b_share,
                        "overrepresentation_ratio": ratio,
                    }
                )
            local = pd.DataFrame(records)
            valid = local["retained_board_id"].ne(NO_BOARD) & local[
                "universe_member_fraction"
            ].gt(0)
            valid_count = int(valid.sum())
            local["percentile_evaluable"] = valid
            local["average_tie_rank"] = np.nan
            local["board_overrepresentation_pct"] = np.nan
            if valid_count == 1:
                local.loc[valid, "average_tie_rank"] = 1.0
                local.loc[valid, "board_overrepresentation_pct"] = 0.5
            elif valid_count > 1:
                ranks = local.loc[valid, "overrepresentation_ratio"].rank(
                    method="average", ascending=True
                )
                local.loc[valid, "average_tie_rank"] = ranks
                local.loc[valid, "board_overrepresentation_pct"] = (ranks - 1.0) / (
                    valid_count - 1.0
                )
            no_mask = local["retained_board_id"].eq(NO_BOARD)
            local.loc[no_mask, "percentile_evaluable"] = False
            local.loc[no_mask, "average_tie_rank"] = np.nan
            local.loc[no_mask, "board_overrepresentation_pct"] = 0.5
            local["scored_model_id"] = model
            local["decision_date"] = pd.Timestamp(decision_date)
            local["bucket_id"] = int(bucket)
            local["retained_board_n_global"] = len(all_boards)
            local["valid_board_n_this_month"] = valid_count
            local["run_id"] = RUN_ID
            local["contract_version"] = CONTRACT_VERSION
            board_rows.extend(local.to_dict("records"))

            pct_map = dict(
                zip(
                    local["retained_board_id"],
                    local["board_overrepresentation_pct"],
                    strict=True,
                )
            )
            target_membership = weights[
                weights["instrument_id"].isin(target_ids)
            ].copy()
            target_membership["pct"] = target_membership["retained_board_id"].map(
                pct_map
            )
            target_membership["component"] = (
                target_membership["membership_weight"] * target_membership["pct"]
            )
            scores = target_membership.groupby("instrument_id", sort=True).agg(
                stock_concentration_tilt_score=("component", "sum"),
                board_membership_n=("board_membership_n", "max"),
            )
            for instrument, row in scores.iterrows():
                score_rows.append(
                    {
                        "scored_model_id": model,
                        "decision_date": pd.Timestamp(decision_date),
                        "bucket_id": int(bucket),
                        "instrument_id": instrument,
                        "stock_concentration_tilt_score": float(
                            row.stock_concentration_tilt_score
                        ),
                        "board_membership_n": int(row.board_membership_n),
                    }
                )
    board_frame = pd.DataFrame(board_rows).sort_values(
        ["scored_model_id", "decision_date", "bucket_id", "retained_board_id"]
    )
    score_frame = pd.DataFrame(score_rows).sort_values(
        ["scored_model_id", "decision_date", "bucket_id", "instrument_id"]
    )
    no_scores = score_frame[
        score_frame["instrument_id"].isin(
            membership.loc[
                membership["retained_board_id"].eq(NO_BOARD), "instrument_id"
            ]
        )
    ]["stock_concentration_tilt_score"]
    if len(no_scores) and not np.allclose(no_scores, 0.5, atol=0.0, rtol=0.0):
        raise ContractError("no-board stock score is not exact neutral 0.5")
    return (
        board_frame.loc[:, BOARD_OVERREP_COLUMNS].reset_index(drop=True),
        score_frame.reset_index(drop=True),
    )


def build_target_weights(
    assignment: pd.DataFrame,
    scores: pd.DataFrame,
    assignment_sha256: str,
    board_member_sha256: str,
    cap: float = 0.10,
) -> pd.DataFrame:
    base = assignment[
        assignment["bucket_id"].isin(BUCKET_IDS)
        & assignment["scored_model_id"].isin(MODEL_IDS)
    ].copy()
    keys = ["scored_model_id", "decision_date", "bucket_id", "instrument_id"]
    merged = base.merge(scores, on=keys, how="left", validate="one_to_one")
    if merged["stock_concentration_tilt_score"].isna().any():
        raise ContractError("missing concentration score for target stock")
    rows: list[pd.DataFrame] = []
    for (model, date, bucket), group in merged.groupby(
        ["scored_model_id", "decision_date", "bucket_id"], sort=True
    ):
        group = group.sort_values("instrument_id").copy()
        nominal = int(group["nominal_bucket_n"].iloc[0])
        for lam in LAMBDA_GRID:
            if lam == 0.0:
                multiplier = np.ones(len(group), dtype=float)
                target = np.full(len(group), 1.0 / len(group), dtype=float)
            else:
                multiplier = np.exp(
                    lam * (group["stock_concentration_tilt_score"].to_numpy() - 0.5)
                )
                target = multiplier / multiplier.sum()
            weight_sum = float(target.sum())
            concentration_pass = bool(float(target.max()) <= cap + 1e-15)
            for stop in STOP_GRID:
                part = pd.DataFrame(
                    {
                        "policy_id": make_policy_id(model, int(bucket), lam, stop),
                        "decision_date": pd.Timestamp(date),
                        "instrument_id": group["instrument_id"].to_numpy(),
                        "scored_model_id": model,
                        "bucket_id": int(bucket),
                        "sector_tilt_lambda": lam,
                        "stop_threshold": pd.array(
                            [stop] * len(group), dtype="Float64"
                        ),
                        "nominal_bucket_n": nominal,
                        "board_membership_n": group["board_membership_n"].to_numpy(),
                        "stock_concentration_tilt_score": group[
                            "stock_concentration_tilt_score"
                        ].to_numpy(),
                        "raw_weight_multiplier": multiplier,
                        "target_weight": target,
                        "target_weight_sum": weight_sum,
                        "target_concentration_pass": concentration_pass,
                        "source_bucket_assignment_sha256": assignment_sha256,
                        "board_member_sha256": board_member_sha256,
                        "run_id": RUN_ID,
                        "contract_version": CONTRACT_VERSION,
                    }
                )
                rows.append(part)
    result = pd.concat(rows, ignore_index=True)
    result = result.sort_values(["policy_id", "decision_date", "instrument_id"])
    if not result["target_concentration_pass"].all():
        raise ContractError("target single-instrument cap exceeded")
    sums = result.groupby(["policy_id", "decision_date"])["target_weight"].sum()
    if not np.allclose(sums, 1.0, atol=1e-12, rtol=0.0):
        raise ContractError("target weights do not sum to one")
    return result.loc[:, TARGET_COLUMNS].reset_index(drop=True)


def target_turnover_series(targets: pd.DataFrame) -> pd.DataFrame:
    required = {"policy_id", "decision_date", "instrument_id", "target_weight"}
    if not required.issubset(targets.columns):
        raise ContractError("target turnover input schema mismatch")
    rows: list[dict[str, Any]] = []
    for policy_id, policy in targets.groupby("policy_id", sort=True):
        previous: dict[str, float] = {}
        for decision_date, current_frame in policy.groupby("decision_date", sort=True):
            current = dict(
                zip(
                    current_frame["instrument_id"],
                    current_frame["target_weight"].astype(float),
                    strict=True,
                )
            )
            union = set(previous) | set(current)
            turnover = 0.5 * sum(
                abs(current.get(item, 0.0) - previous.get(item, 0.0)) for item in union
            )
            rows.append(
                {
                    "policy_id": policy_id,
                    "decision_date": pd.Timestamp(decision_date),
                    "target_one_way_turnover": float(turnover),
                }
            )
            previous = current
    return pd.DataFrame(rows)


def round_half_up_to_tick(value: float, tick_size: float) -> float:
    if not np.isfinite(value) or not np.isfinite(tick_size) or tick_size <= 0:
        raise ContractError("invalid value/tick for rounding")
    ticks = (Decimal(str(value)) / Decimal(str(tick_size))).quantize(
        Decimal("1"), rounding=ROUND_HALF_UP
    )
    return float(ticks * Decimal(str(tick_size)))


def map_intraday_stop(
    qfq_trigger: float,
    raw_ohlc: Mapping[str, float],
    qfq_ohlc: Mapping[str, float],
    tick_size: float,
    warning_spread: float = 0.002,
    block_spread: float = 0.01,
) -> MappingResult:
    ratios: list[float] = []
    for field in ("open", "high", "low", "close"):
        raw = float(raw_ohlc[field])
        qfq = float(qfq_ohlc[field])
        if not np.isfinite(raw) or not np.isfinite(qfq) or raw <= 0 or qfq <= 0:
            raise ContractError("raw/qfq mapping requires four finite positive prices")
        ratios.append(qfq / raw)
    factor = float(np.median(np.asarray(ratios, dtype=float)))
    spread = (max(ratios) - min(ratios)) / factor
    factor_pass = bool(factor > 0 and spread <= block_spread)
    raw_unrounded = float(qfq_trigger) / factor
    raw_tick = math.floor(raw_unrounded / tick_size + 1e-12) * tick_size
    lower = float(raw_ohlc["low"]) - 0.5 * tick_size
    upper = float(raw_ohlc["high"]) + 0.5 * tick_size
    domain_pass = bool(lower <= raw_tick <= upper)
    return MappingResult(
        factor=factor,
        relative_spread=float(spread),
        warning=bool(spread > warning_spread),
        factor_mapping_pass=factor_pass,
        raw_trigger_tick=float(raw_tick),
        raw_fill_domain_lower=lower,
        raw_fill_domain_upper=upper,
        fill_domain_pass=domain_pass,
        mapping_pass=factor_pass and domain_pass,
        qfq_fill=float(raw_tick * factor),
    )


def update_cost_basis(
    old_shares: float,
    old_basis: float | None,
    bought_shares: float,
    buy_price_qfq: float,
) -> float:
    if bought_shares <= 0:
        if old_basis is None:
            raise ContractError("missing basis without a buy")
        return float(old_basis)
    if old_shares <= 0 or old_basis is None:
        return float(buy_price_qfq)
    return float(
        (old_shares * old_basis + bought_shares * buy_price_qfq)
        / (old_shares + bought_shares)
    )


def order_costs(
    side: str,
    notional: float,
    slippage_bps: float,
    transfer_fee_bps: float,
    *,
    statutory_enabled: bool = True,
    commission_enabled: bool = True,
    commission_bps: float = 2.5,
    minimum_commission: float = 5.0,
    stamp_tax_sell_bps: float = 5.0,
) -> dict[str, float]:
    if side not in {"buy", "sell"} or notional < 0:
        raise ContractError("invalid order cost input")
    commission = (
        max(notional * commission_bps / 10000.0, minimum_commission)
        if commission_enabled and notional > 0
        else 0.0
    )
    stamp = (
        notional * stamp_tax_sell_bps / 10000.0
        if statutory_enabled and side == "sell"
        else 0.0
    )
    transfer = notional * transfer_fee_bps / 10000.0 if statutory_enabled else 0.0
    slippage = notional * float(slippage_bps) / 10000.0
    total = commission + stamp + transfer + slippage
    return {
        "commission_cny": float(commission),
        "stamp_tax_cny": float(stamp),
        "transfer_fee_cny": float(transfer),
        "slippage_cny": float(slippage),
        "total_event_cost_cny": float(total),
    }


def break_even_bisection(
    gross_final_nav: float,
    initial_aum: float,
    fixed_cost: float,
    bps_sensitive_notional: float,
    *,
    bracket: tuple[float, float] = (0.0, 2000.0),
    tolerance: float = 1e-8,
    max_iterations: int = 200,
) -> tuple[float, str]:
    if bps_sensitive_notional <= 0:
        return np.nan, "undefined_no_turnover"

    def root_value(bps: float) -> float:
        wealth = gross_final_nav - fixed_cost - bps_sensitive_notional * bps / 10000.0
        return wealth / initial_aum - 1.0

    low, high = map(float, bracket)
    if root_value(low) <= 0:
        return 0.0, "not_positive_at_zero_slippage"
    if root_value(high) > 0:
        return np.nan, "above_registered_bracket"
    for _ in range(int(max_iterations)):
        if high - low <= tolerance:
            break
        mid = (low + high) / 2.0
        if root_value(mid) > 0:
            low = mid
        else:
            high = mid
    return (low + high) / 2.0, "root_found"


def circular_moving_block_bootstrap(
    deltas: Sequence[float],
    rng: np.random.Generator,
    *,
    block_length: int = 3,
    repetitions: int = 20000,
) -> np.ndarray:
    values = np.asarray(deltas, dtype=float)
    if len(values) != 21 or not np.isfinite(values).all():
        raise ContractError("bootstrap requires all 21 finite calendar months")
    block_n = math.ceil(len(values) / block_length)
    result = np.empty(repetitions, dtype=float)
    offsets = np.arange(block_length, dtype=np.int64)
    for repetition in range(repetitions):
        starts = rng.integers(0, len(values), size=block_n)
        indices = ((starts[:, None] + offsets[None, :]) % len(values)).ravel()
        sample = values[indices[: len(values)]]
        result[repetition] = float(np.mean(sample))
    return result


def concentration_metrics(
    position_weights: Mapping[str, float],
    membership: pd.DataFrame,
    score_by_instrument: Mapping[str, float] | None = None,
) -> dict[str, Any]:
    weights = pd.Series(position_weights, dtype=float)
    invested = float(weights.sum())
    if invested <= 0:
        return {
            "board_HHI": np.nan,
            "top1_board_weight": np.nan,
            "top3_board_weight": np.nan,
            "no_board_position_weight": 0.0,
            "classified_position_weight": 0.0,
            "classified_board_coverage_ratio": np.nan,
            "concentration_status": "not_evaluable_no_invested_weight",
            "mean_stock_concentration_tilt_score": np.nan,
            "effective_holdings": np.nan,
        }
    local = membership[membership["instrument_id"].isin(weights.index)].copy()
    local["position_weight"] = local["instrument_id"].map(weights)
    local["board_weight"] = local["position_weight"] * local["membership_weight"]
    board = local.groupby("retained_board_id")["board_weight"].sum()
    no_board = float(board.get(NO_BOARD, 0.0))
    real = board.drop(labels=[NO_BOARD], errors="ignore")
    classified = float(real.sum())
    coverage = classified / invested
    if classified <= 0:
        hhi = top1 = top3 = np.nan
        status = "not_evaluable_no_classified_board_weight"
    else:
        normalized = (real / classified).sort_values(ascending=False)
        hhi = float(np.square(normalized).sum())
        top1 = float(normalized.iloc[0])
        top3 = float(normalized.iloc[: min(3, len(normalized))].sum())
        status = "evaluable"
    normalized_instrument = weights / invested
    effective = float(1.0 / np.square(normalized_instrument).sum())
    mean_score = np.nan
    if score_by_instrument is not None:
        score = pd.Series(score_by_instrument, dtype=float).reindex(weights.index)
        if score.notna().all():
            mean_score = float((normalized_instrument * score).sum())
    return {
        "board_HHI": hhi,
        "top1_board_weight": top1,
        "top3_board_weight": top3,
        "no_board_position_weight": no_board,
        "classified_position_weight": classified,
        "classified_board_coverage_ratio": coverage,
        "concentration_status": status,
        "mean_stock_concentration_tilt_score": mean_score,
        "effective_holdings": effective,
    }


def validate_profile_contract(output_contract: Mapping[str, Any]) -> None:
    groups = output_contract["artifact_groups"]
    profiles = output_contract["profiles"]
    expected_profiles = {
        "P0_PREFLIGHT_BLOCKED",
        "P1_BOARD_BLOCKED",
        "P2_EXECUTION_BLOCKED",
        "P3_METRIC_BLOCKED",
        "P4_DETERMINISM_BLOCKED",
        "P5_SENSITIVITY_MATERIALIZED",
    }
    if set(profiles) != expected_profiles:
        raise ContractError("profile id set mismatch")
    if set(output_contract["profile_ids"]) != expected_profiles:
        raise ContractError("profile registry mismatch")
    all_paths: set[str] = set()
    for group, paths in groups.items():
        if not group.startswith("G") or not isinstance(paths, list):
            raise ContractError("invalid artifact group")
        overlap = all_paths & set(paths)
        if overlap:
            raise ContractError(
                f"artifact appears in multiple groups: {sorted(overlap)}"
            )
        all_paths.update(paths)
    for profile, group_names in profiles.items():
        unknown = set(group_names) - set(groups)
        if unknown:
            raise ContractError(f"unknown groups in {profile}: {sorted(unknown)}")
    if groups["G2_BOARD_TARGETS"][:2] != [
        "preflight/board_membership_audit.csv",
        "preflight/retained_board_registry.csv",
    ]:
        raise ContractError("board registries are not atomic with board targets")


def profile_file_set(config: Mapping[str, Any], profile_id: str) -> set[str]:
    output = config["output_contract"]
    if profile_id not in output["profiles"]:
        raise ContractError(f"unknown profile: {profile_id}")
    paths: set[str] = set()
    for group in output["profiles"][profile_id]:
        paths.update(output["artifact_groups"][group])
    return paths


def regular_files(root: Path) -> set[str]:
    paths: set[str] = set()
    for item in root.rglob("*"):
        if item.is_symlink():
            raise SealError(f"symlink forbidden in bundle: {item}")
        if item.is_file():
            relative = item.relative_to(root).as_posix()
            if relative.startswith("../") or relative.startswith("/"):
                raise SealError(f"path escape: {relative}")
            paths.add(relative)
    return paths


def manifest_payload(
    build: Path,
    config: Mapping[str, Any],
    profile_id: str,
    decision_state: str,
    reached_stage: str,
) -> dict[str, Any]:
    manifest_name = config["output_contract"]["manifest_name"]
    hashes_name = config["output_contract"]["output_hashes_name"]
    payload_paths = sorted(regular_files(build) - {manifest_name, hashes_name})
    payload_files = [
        {
            "path": relative,
            "byte_size": (build / relative).stat().st_size,
            "sha256": sha256_file(build / relative),
            "artifact_role": relative.split("/", 1)[0] if "/" in relative else "final",
        }
        for relative in payload_paths
    ]
    paths = resolved_paths(config)
    return {
        "schema_version": SCHEMA_VERSION,
        "run_id": RUN_ID,
        "contract_version": CONTRACT_VERSION,
        "artifact_profile_id": profile_id,
        "decision_state": decision_state,
        "reached_stage": reached_stage,
        "immutable": True,
        "requirement_sha256": sha256_file(paths["requirement_file"]),
        "resolved_config_sha256": sha256_file(build / "preflight/resolved_config.yaml"),
        "upstream_bindings": dict(config["upstream_hashes"]),
        "claim_flags": {
            "historical_support_claim_allowed": False,
            "model_repair_claim_allowed": False,
            "parameter_selection_authorized": False,
            "deployment_authorized": False,
            "market_trading_crowding_claim_allowed": False,
            "historical_PIT_sector_claim_allowed": False,
        },
        "payload_files": payload_files,
    }


def verify_candidate_seal(
    build: Path,
    config: Mapping[str, Any],
    profile_id: str,
) -> str:
    output = config["output_contract"]
    manifest_name = output["manifest_name"]
    hashes_name = output["output_hashes_name"]
    actual = regular_files(build)
    expected = profile_file_set(config, profile_id)
    if actual != expected:
        raise SealError(
            f"profile file set mismatch: missing={sorted(expected - actual)}, "
            f"extra={sorted(actual - expected)}"
        )
    registry = json.loads((build / hashes_name).read_text(encoding="utf-8"))
    expected_registry_paths = sorted(actual - {hashes_name})
    if sorted(registry) != expected_registry_paths:
        raise SealError("output-hashes path set mismatch")
    if manifest_name not in registry or hashes_name in registry:
        raise SealError("manifest/registry self-reference contract violated")
    for relative, expected_hash in registry.items():
        if sha256_file(build / relative) != expected_hash:
            raise SealError(f"hash mismatch: {relative}")
    manifest = json.loads((build / manifest_name).read_text(encoding="utf-8"))
    if set(manifest) != {
        "schema_version",
        "run_id",
        "contract_version",
        "artifact_profile_id",
        "decision_state",
        "reached_stage",
        "immutable",
        "requirement_sha256",
        "resolved_config_sha256",
        "upstream_bindings",
        "claim_flags",
        "payload_files",
    }:
        raise SealError("manifest top-level key set mismatch")
    return hashlib.sha256((build / hashes_name).read_bytes()).hexdigest()


def seal_candidate(
    build: Path,
    output_root: Path,
    config: Mapping[str, Any],
    profile_id: str,
    decision_state: str,
    reached_stage: str,
) -> str:
    output = config["output_contract"]
    manifest_name = output["manifest_name"]
    hashes_name = output["output_hashes_name"]
    if output_root.exists():
        raise SealError(f"output root already exists: {output_root}")
    write_json(
        build / manifest_name,
        manifest_payload(build, config, profile_id, decision_state, reached_stage),
    )
    hashes = {
        relative: sha256_file(build / relative)
        for relative in sorted(regular_files(build) - {hashes_name})
    }
    write_json(build / hashes_name, hashes)
    bundle_hash = verify_candidate_seal(build, config, profile_id)
    os.replace(build, output_root)
    return bundle_hash


INPUT_AUDIT_COLUMNS = [
    "artifact_role",
    "artifact_path",
    "expected_sha256_or_root_hash",
    "observed_sha256_or_root_hash",
    "byte_size",
    "mtime_utc",
    "hash_match",
    "schema_match",
    "status",
    "blocking_reason",
    "run_id",
    "contract_version",
]
BOARD_REGISTRY_COLUMNS = [
    "source_board_ts_code",
    "reference_member_n",
    "minimum_member_pass",
    "duplicate_group_id",
    "retained_board_id",
    "retained",
    "synthetic",
    "board_member_sha256",
    "run_id",
    "contract_version",
]
BOARD_AUDIT_COLUMNS = [
    "proxy_id",
    "snapshot_trade_date",
    "source_path",
    "source_sha256",
    "raw_member_row_n",
    "normalized_member_row_n",
    "invalid_instrument_row_n",
    "reference_universe_instrument_n",
    "reference_overlap_instrument_n",
    "retained_board_n",
    "duplicate_board_n",
    "no_board_instrument_n",
    "board_reference_universe_dependency",
    "historical_PIT_industry_claim_allowed",
    "board_membership_currentness_claim",
    "board_formula_gate",
    "blocking_reason",
    "run_id",
    "contract_version",
]
BOARD_OVERREP_COLUMNS = [
    "scored_model_id",
    "decision_date",
    "bucket_id",
    "retained_board_id",
    "universe_member_fraction",
    "bucket_member_fraction",
    "overrepresentation_ratio",
    "percentile_evaluable",
    "average_tie_rank",
    "board_overrepresentation_pct",
    "retained_board_n_global",
    "valid_board_n_this_month",
    "run_id",
    "contract_version",
]
EXECUTION_COLUMNS = [
    "policy_id",
    "trade_date",
    "event_sequence",
    "instrument_id",
    "event_type",
    "intended_side",
    "intended_shares",
    "intended_notional",
    "fill_status",
    "blocking_reason",
    "executed_shares",
    "raw_proxy_fill_price",
    "qfq_linked_gross_fill_price",
    "raw_qfq_factor",
    "relative_ratio_spread",
    "mapping_warning",
    "factor_mapping_pass",
    "raw_session_low",
    "raw_session_high",
    "raw_trigger_tick",
    "raw_fill_domain_lower",
    "raw_fill_domain_upper",
    "fill_domain_pass",
    "mapping_pass",
    "position_shares_before",
    "position_shares_after",
    "cost_basis_before",
    "cost_basis_after",
    "trigger_price",
    "cash_before",
    "cash_after",
    "NAV_before",
    "NAV_after",
    "locked_capital_weight",
    "daily_bar_execution_proxy",
    "run_id",
    "contract_version",
]
COST_SHADOW_COLUMNS = [
    "policy_id",
    "cost_scenario_id",
    "trade_date",
    "event_sequence",
    "instrument_id",
    "side",
    "executed_shares",
    "executed_notional",
    "commission_cny",
    "stamp_tax_cny",
    "transfer_fee_cny",
    "slippage_cny",
    "total_event_cost_cny",
    "cumulative_cost_liability_cny",
    "counterfactual_cost_shadow",
    "deployment_interpretation_allowed",
    "run_id",
    "contract_version",
]
DAILY_NAV_COLUMNS = [
    "policy_id",
    "cost_scenario_id",
    "trade_date",
    "gross_shadow_cash",
    "scenario_cost_liability",
    "scenario_cash_after_cost",
    "marked_position_value",
    "scenario_NAV",
    "daily_return",
    "shadow_cash_deficit_cny",
    "shadow_self_financing",
    "locked_capital_weight",
    "invested_weight",
    "scenario_evaluable",
    "exclusion_reason",
    "run_id",
    "contract_version",
]
STOP_EVENT_COLUMNS = [
    "policy_id",
    "holding_spell_id",
    "stop_event_id",
    "instrument_id",
    "configured_stop_threshold",
    "basis_qfq",
    "trigger_price_qfq",
    "trigger_date",
    "trigger_type",
    "gap_through",
    "daily_bar_execution_proxy",
    "fill_date",
    "fill_status",
    "blocking_reason",
    "trigger_to_fill_delay_sessions",
    "shares_stopped",
    "gross_fill_price_qfq",
    "raw_trigger_tick",
    "fill_domain_pass",
    "gross_loss_at_fill_vs_basis",
    "reference_net_loss_at_fill_vs_basis",
    "stop_overshoot",
    "counterfactual_horizon_date",
    "counterfactual_horizon_truncated",
    "counterfactual_exit_is_cost_estimate",
    "stop_proceeds_at_horizon_cny",
    "no_stop_value_at_horizon_cny",
    "stop_exit_vs_hold_delta_cny",
    "stop_avoided_loss_cny",
    "stop_missed_rebound_cny",
    "attribution_evaluable",
    "attribution_missing_reason",
    "attribution_cost_scenario_id",
    "attribution_role",
    "run_id",
    "contract_version",
]


def _audit_row(
    role: str,
    path: Path,
    expected: str,
    observed: str,
    schema_match: bool = True,
) -> dict[str, Any]:
    match = expected == observed
    return {
        "artifact_role": role,
        "artifact_path": path.relative_to(REPO_ROOT).as_posix(),
        "expected_sha256_or_root_hash": expected,
        "observed_sha256_or_root_hash": observed,
        "byte_size": path.stat().st_size
        if path.is_file()
        else sum(item.stat().st_size for item in path.glob("*.csv")),
        "mtime_utc": datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
        .isoformat()
        .replace("+00:00", "Z"),
        "hash_match": match,
        "schema_match": schema_match,
        "status": "pass" if match and schema_match else "fail",
        "blocking_reason": "" if match and schema_match else "input_integrity_mismatch",
        "run_id": RUN_ID,
        "contract_version": CONTRACT_VERSION,
    }


def verify_hash_registry(root: Path, registry_path: Path) -> list[str]:
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    if not isinstance(registry, dict):
        raise ContractError(f"hash registry is not an object: {registry_path}")
    failures: list[str] = []
    for relative, expected in registry.items():
        path = root / relative
        if not path.is_file() or sha256_file(path) != expected:
            failures.append(relative)
    return failures


def validate_assignment_population(
    assignment: pd.DataFrame,
    config: Mapping[str, Any],
) -> pd.DataFrame:
    required = {
        "scored_model_id",
        "split",
        "decision_date",
        "label_month",
        "instrument_id",
        "bucket_id",
        "nominal_bucket_n",
    }
    if not required.issubset(assignment.columns):
        raise ContractError(
            f"assignment missing columns: {sorted(required - set(assignment))}"
        )
    forbidden_tokens = ("return", "label_value", "outcome", "future", "realized")
    forbidden = [
        column
        for column in assignment.columns
        if any(token in column.lower() for token in forbidden_tokens)
        and column != "label_month"
    ]
    if forbidden:
        raise ContractError(f"outcome columns in assignment: {forbidden}")
    frame = assignment.copy()
    frame["decision_date"] = pd.to_datetime(frame["decision_date"]).dt.normalize()
    population = config["population"]
    start = pd.Timestamp(population["decision_date_min"])
    end = pd.Timestamp(population["decision_date_max"])
    frame = frame[
        frame["split"].eq(population["split"])
        & frame["scored_model_id"].isin(MODEL_IDS)
        & frame["decision_date"].between(start, end)
    ].copy()
    if frame.duplicated(["scored_model_id", "decision_date", "instrument_id"]).any():
        raise ContractError("assignment stable key duplicate")
    if frame["decision_date"].nunique() != int(population["decision_month_n"]):
        raise ContractError("assignment does not contain exact 21 decision dates")
    for decision_date, month in frame.groupby("decision_date", sort=True):
        populations = {
            model: set(group["instrument_id"])
            for model, group in month.groupby("scored_model_id")
        }
        if set(populations) != set(MODEL_IDS):
            raise ContractError(f"missing model population at {decision_date}")
        if populations[MODEL_IDS[0]] != populations[MODEL_IDS[1]]:
            raise ContractError(f"S0/B0 population mismatch at {decision_date}")
        for model, group in month.groupby("scored_model_id"):
            if set(group["bucket_id"].astype(int)) != set(range(1, 11)):
                raise ContractError(f"bucket set mismatch: {model} {decision_date}")
            counts = group.groupby("bucket_id").size()
            declared = group.groupby("bucket_id")["nominal_bucket_n"].first()
            if not counts.astype(int).equals(declared.astype(int)):
                raise ContractError(
                    f"nominal bucket count mismatch: {model} {decision_date}"
                )
    return frame.sort_values(
        ["scored_model_id", "decision_date", "bucket_id", "instrument_id"]
    ).reset_index(drop=True)


def run_preflight(
    config: Mapping[str, Any],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    paths = resolved_paths(config)
    mlrank = paths["MLRANK_ROOT"]
    contract20a = paths["CONTRACT20A_ROOT"]
    artifacts = [
        (
            "MLRANK_REGISTRY",
            mlrank / "output_hashes_20b_p4_mlrank.json",
            "MLRANK_REGISTRY_sha256",
            False,
        ),
        (
            "MLRANK_MANIFEST",
            mlrank / "manifest_20b_p4_mlrank.json",
            "MLRANK_MANIFEST_sha256",
            False,
        ),
        (
            "MLRANK_DECISION",
            mlrank / "20B_P4_learned_monotonic_return_ranking_diagnostic_decision.csv",
            "MLRANK_DECISION_sha256",
            False,
        ),
        (
            "BUCKET_ASSIGNMENT",
            mlrank / "scores/robustness_model_bucket_assignment.parquet",
            "BUCKET_ASSIGNMENT_sha256",
            False,
        ),
        (
            "CONTRACT20A_REGISTRY",
            contract20a
            / "output_hashes_20a_paper_lineage_data_and_replication_contract.json",
            "CONTRACT20A_REGISTRY_sha256",
            False,
        ),
        (
            "CONTRACT20A_MANIFEST",
            contract20a
            / "manifest_20a_paper_lineage_data_and_replication_contract.json",
            "CONTRACT20A_MANIFEST_sha256",
            False,
        ),
        (
            "CONTRACT20A_FREEZE_REGISTRY",
            contract20a / "freeze/freeze_output_hashes_20a.json",
            "CONTRACT20A_FREEZE_REGISTRY_sha256",
            False,
        ),
        ("BOARD_MEMBER", paths["BOARD_MEMBER"], "BOARD_MEMBER_sha256", False),
        ("RAW_OHLCV_ROOT", paths["RAW_OHLCV_ROOT"], "RAW_OHLCV_ROOT_hash", True),
        ("QFQ_ROOT", paths["QFQ_ROOT"], "QFQ_ROOT_hash", True),
        (
            "TRADING_CALENDAR_FILE",
            paths["TRADING_CALENDAR_FILE"],
            "TRADING_CALENDAR_FILE_sha256",
            False,
        ),
        (
            "PROJECT_UNIVERSE_FILE",
            paths["PROJECT_UNIVERSE_FILE"],
            "PROJECT_UNIVERSE_FILE_sha256",
            False,
        ),
        (
            "SECURITY_MASTER_FILE",
            paths["SECURITY_MASTER_FILE"],
            "SECURITY_MASTER_FILE_sha256",
            False,
        ),
        (
            "SH_NAME_HISTORY_ROOT",
            paths["SH_NAME_HISTORY_ROOT"],
            "SH_NAME_HISTORY_ROOT_hash",
            True,
        ),
        (
            "SZ_NAME_HISTORY_FILE",
            paths["SZ_NAME_HISTORY_FILE"],
            "SZ_NAME_HISTORY_FILE_sha256",
            False,
        ),
        (
            "MARKET_RULE_REGISTRY_FILE",
            paths["MARKET_RULE_REGISTRY_FILE"],
            "MARKET_RULE_REGISTRY_FILE_sha256",
            False,
        ),
    ]
    rows = []
    for role, path, hash_key, is_root in artifacts:
        if not path.exists():
            raise ContractError(f"missing upstream artifact: {path}")
        observed = root_inventory_hash(path)[0] if is_root else sha256_file(path)
        rows.append(
            _audit_row(role, path, config["upstream_hashes"][hash_key], observed)
        )
    audit = pd.DataFrame(rows).loc[:, INPUT_AUDIT_COLUMNS]
    if not audit["status"].eq("pass").all():
        raise ContractError("upstream input integrity blocked")
    failures = verify_hash_registry(mlrank, mlrank / "output_hashes_20b_p4_mlrank.json")
    failures += verify_hash_registry(
        contract20a / "freeze", contract20a / "freeze/freeze_output_hashes_20a.json"
    )
    if failures:
        raise ContractError(f"nested upstream registry mismatch: {failures[:10]}")
    manifest = json.loads((mlrank / "manifest_20b_p4_mlrank.json").read_text())
    if manifest.get("immutable") is not True or manifest.get("decision_state") != (
        "20B_P4_MLRANK_metric_materialization_blocked"
    ):
        raise ContractError("MLRANK manifest identity/state mismatch")
    decision = pd.read_csv(
        mlrank / "20B_P4_learned_monotonic_return_ranking_diagnostic_decision.csv"
    )
    if len(decision) != 1:
        raise ContractError("MLRANK decision must contain one row")
    expected_decision = {
        "decision_state": "20B_P4_MLRANK_metric_materialization_blocked",
        "selected_scored_model_id": "S0_SELECTED_FULL",
        "baseline_scored_model_id": "B0_P4_RAW_RANK",
        "robustness_evaluable_month_n": 21,
        "portfolio_optimization_authorized": False,
        "20C_requirement_generation_authorized": False,
        "20C_execution_authorized": False,
        "deployment_authorized": False,
    }
    for key, expected in expected_decision.items():
        observed = decision.iloc[0][key]
        if isinstance(expected, bool):
            observed = str(observed).strip().lower() in {"true", "1"}
        if observed != expected:
            raise ContractError(f"MLRANK decision mismatch: {key}")
    assignment = pd.read_parquet(
        mlrank / "scores/robustness_model_bucket_assignment.parquet"
    )
    return audit, validate_assignment_population(assignment, config)


def load_trading_calendar(config: Mapping[str, Any]) -> pd.DatetimeIndex:
    path = resolved_paths(config)["TRADING_CALENDAR_FILE"]
    calendar = pd.to_datetime(pd.read_csv(path)["trade_date"]).sort_values().unique()
    start = pd.Timestamp(config["population"]["ledger_start_date"])
    end = pd.Timestamp(config["population"]["ledger_end_date"])
    selected = pd.DatetimeIndex(calendar[(calendar >= start) & (calendar <= end)])
    if len(selected) != int(config["population"]["ledger_trade_date_n"]):
        raise ContractError(f"ledger calendar count mismatch: {len(selected)}")
    return selected


def load_status_panel(
    config: Mapping[str, Any],
    instruments: set[str],
    calendar: pd.DatetimeIndex,
) -> pd.DataFrame:
    paths = resolved_paths(config)
    project_columns = [
        "usable_trade_date",
        "source_trade_date",
        "instrument",
        "board_bucket",
        "is_listed",
        "is_st",
        "is_suspended",
    ]
    frames: list[pd.DataFrame] = []
    start, end = calendar.min(), calendar.max()
    for chunk in pd.read_csv(
        paths["PROJECT_UNIVERSE_FILE"],
        usecols=project_columns,
        chunksize=500_000,
    ):
        chunk["usable_trade_date"] = pd.to_datetime(chunk["usable_trade_date"])
        selected = chunk[
            chunk["instrument"].isin(instruments)
            & chunk["usable_trade_date"].between(start, end)
        ]
        if len(selected):
            frames.append(selected)
    if not frames:
        raise ContractError("empty project-universe status panel")
    observed = pd.concat(frames, ignore_index=True).rename(
        columns={"instrument": "instrument_id"}
    )
    if observed.duplicated(["usable_trade_date", "instrument_id"]).any():
        raise ContractError("duplicate status rows")

    master = pd.read_csv(paths["SECURITY_MASTER_FILE"])
    master = master[master["instrument"].isin(instruments)].copy()
    if master["instrument"].nunique() != len(instruments):
        raise ContractError("security master does not cover status reconstruction")
    master = master.drop_duplicates("instrument").set_index("instrument")
    master["listing_date"] = pd.to_datetime(master["listing_date"], errors="coerce")
    master["delist_date"] = pd.to_datetime(master["delist_date"], errors="coerce")

    sz_changes = pd.read_csv(paths["SZ_NAME_HISTORY_FILE"], dtype=str).rename(
        columns={
            "变更日期": "change_date",
            "证券代码": "code",
            "变更前简称": "previous_name",
            "变更后简称": "next_name",
        }
    )
    required_changes = {"change_date", "code", "previous_name", "next_name"}
    if not required_changes.issubset(sz_changes.columns):
        raise ContractError("SZ name-history schema mismatch")
    sz_changes["code"] = (
        sz_changes["code"].astype(str).str.extract(r"(\d{6})", expand=False)
    )
    sz_changes["change_date"] = pd.to_datetime(
        sz_changes["change_date"], errors="coerce"
    )
    sz_changes = sz_changes.dropna(subset=["code", "change_date"]).sort_values(
        ["code", "change_date"]
    )

    def has_st_marker(value: Any) -> bool:
        text = (
            str(value).upper().replace("＊", "*").replace("Ｓ", "S").replace("Ｔ", "T")
        )
        return "ST" in text

    def sh_lifetime_st(instrument: str) -> bool:
        path = paths["SH_NAME_HISTORY_ROOT"] / f"{instrument}.csv"
        if not path.is_file():
            raise ContractError(f"missing SH name history: {instrument}")
        history = pd.read_csv(path, dtype=str)
        marker_columns = [
            column
            for column in ("name", "名称", "证券简称", "变更前简称", "变更后简称")
            if column in history.columns
        ]
        if not marker_columns:
            return False
        return any(
            history[column].map(has_st_marker).any() for column in marker_columns
        )

    rows: list[pd.DataFrame] = []
    calendar_frame = pd.DataFrame({"trade_date": calendar})
    for instrument in sorted(instruments):
        meta = master.loc[instrument]
        local = calendar_frame.copy()
        local["instrument_id"] = instrument
        local["board_bucket"] = str(meta["board_bucket"])
        listed = local["trade_date"].ge(meta["listing_date"])
        if pd.notna(meta["delist_date"]):
            listed &= local["trade_date"].lt(meta["delist_date"])
        local["is_listed"] = listed.fillna(False)
        exchange = str(meta["exchange"])
        if exchange == "SH":
            local["is_st"] = sh_lifetime_st(instrument)
        elif exchange == "SZ":
            changes = sz_changes[sz_changes["code"].eq(instrument[-6:])]
            if changes.empty:
                local["is_st"] = False
            else:
                names = pd.merge_asof(
                    local[["trade_date"]].sort_values("trade_date"),
                    changes[["change_date", "previous_name", "next_name"]].sort_values(
                        "change_date"
                    ),
                    left_on="trade_date",
                    right_on="change_date",
                    direction="backward",
                )
                first_previous = str(changes.iloc[0]["previous_name"])
                status_name = names["next_name"].copy()
                status_name.loc[names["change_date"].isna()] = first_previous
                local["is_st"] = status_name.map(has_st_marker).fillna(False).to_numpy()
        else:
            local["is_st"] = True
        raw_dates = pd.to_datetime(
            pd.read_csv(
                paths["RAW_OHLCV_ROOT"] / f"{instrument}.csv", usecols=["date"]
            )["date"],
            errors="coerce",
        ).dt.normalize()
        local["is_suspended"] = local["is_listed"] & ~local["trade_date"].isin(
            set(raw_dates.dropna())
        )
        rows.append(local)
    status = pd.concat(rows, ignore_index=True)
    if len(status) != len(instruments) * len(calendar):
        raise ContractError("reconstructed security-state grid is incomplete")

    observed["source_trade_date"] = pd.to_datetime(
        observed["source_trade_date"], errors="coerce"
    )
    comparable = observed[observed["source_trade_date"].between(start, end)].merge(
        status,
        left_on=["source_trade_date", "instrument_id"],
        right_on=["trade_date", "instrument_id"],
        how="left",
        suffixes=("_observed", "_reconstructed"),
        validate="many_to_one",
    )
    if comparable["trade_date"].isna().any():
        raise ContractError(
            "project-universe status cross-check missing reconstruction"
        )
    for field in ("board_bucket", "is_listed", "is_st", "is_suspended"):
        observed_values = (
            comparable[f"{field}_observed"].map(_bool_value)
            if field != "board_bucket"
            else comparable[f"{field}_observed"].astype(str)
        )
        reconstructed_values = (
            comparable[f"{field}_reconstructed"].map(_bool_value)
            if field != "board_bucket"
            else comparable[f"{field}_reconstructed"].astype(str)
        )
        if not observed_values.equals(reconstructed_values):
            mismatch_n = int((observed_values != reconstructed_values).sum())
            raise ContractError(
                f"project-universe status reconstruction mismatch: {field}/n={mismatch_n}"
            )
    return status.sort_values(["trade_date", "instrument_id"]).reset_index(drop=True)


def load_market_panel(
    config: Mapping[str, Any],
    instruments: set[str],
    calendar: pd.DatetimeIndex,
) -> pd.DataFrame:
    paths = resolved_paths(config)
    rows: list[pd.DataFrame] = []
    start, end = calendar.min(), calendar.max()
    usecols = ["date", "open", "high", "low", "close"]
    for instrument in sorted(instruments):
        raw_path = paths["RAW_OHLCV_ROOT"] / f"{instrument}.csv"
        qfq_path = paths["QFQ_ROOT"] / f"{instrument}.csv"
        if not raw_path.is_file() or not qfq_path.is_file():
            raise ContractError(f"missing raw/qfq pair: {instrument}")
        raw = pd.read_csv(raw_path, usecols=usecols)
        qfq = pd.read_csv(qfq_path, usecols=usecols)
        raw["date"] = pd.to_datetime(raw["date"])
        qfq["date"] = pd.to_datetime(qfq["date"])
        raw = raw[raw["date"].between(start, end)]
        qfq = qfq[qfq["date"].between(start, end)]
        raw = raw.rename(columns={column: f"raw_{column}" for column in usecols[1:]})
        qfq = qfq.rename(columns={column: f"qfq_{column}" for column in usecols[1:]})
        merged = raw.merge(qfq, on="date", how="outer", validate="one_to_one")
        merged["instrument_id"] = instrument
        rows.append(merged)
    panel = pd.concat(rows, ignore_index=True).rename(columns={"date": "trade_date"})
    panel = panel.sort_values(["trade_date", "instrument_id"])
    price_columns = [
        f"{kind}_{field}"
        for kind in ("raw", "qfq")
        for field in ("open", "high", "low", "close")
    ]
    for column in price_columns:
        panel[column] = pd.to_numeric(panel[column], errors="coerce")
    ratios = np.column_stack(
        [
            panel[f"qfq_{field}"] / panel[f"raw_{field}"]
            for field in ("open", "high", "low", "close")
        ]
    )
    panel["raw_qfq_factor"] = np.nanmedian(ratios, axis=1)
    panel["relative_ratio_spread"] = (
        np.nanmax(ratios, axis=1) - np.nanmin(ratios, axis=1)
    ) / panel["raw_qfq_factor"]
    panel["mapping_warning"] = panel["relative_ratio_spread"].gt(
        float(config["stop"]["mapping_warning_spread"])
    )
    panel["factor_mapping_pass"] = panel["raw_qfq_factor"].gt(0) & panel[
        "relative_ratio_spread"
    ].le(float(config["stop"]["mapping_block_spread"]))
    panel["previous_raw_close"] = panel.groupby("instrument_id")["raw_close"].shift(1)
    return panel.set_index(["trade_date", "instrument_id"]).sort_index()


def _bool_value(value: Any) -> bool:
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    return str(value).strip().lower() in {"1", "true", "yes", "pass"}


def compile_market_rules(rules: pd.DataFrame) -> list[dict[str, Any]]:
    compiled: list[dict[str, Any]] = []
    for row in rules.to_dict("records"):
        item = dict(row)
        item["_effective_start"] = pd.Timestamp(row["effective_start_date"])
        item["_effective_end"] = pd.to_datetime(
            row["effective_end_date"], errors="coerce"
        )
        item["_listing_min"] = float(row["listing_session_min"])
        item["_listing_max"] = pd.to_numeric(
            row["listing_session_max"], errors="coerce"
        )
        item["_is_st"] = _bool_value(row["is_st"])
        item["_human_verified"] = _bool_value(row["human_verified"])
        compiled.append(item)
    return compiled


def match_compiled_market_rule(
    compiled: Sequence[Mapping[str, Any]],
    *,
    exchange: str,
    board_bucket: str,
    is_st: bool,
    trade_date: pd.Timestamp,
    listing_session: int,
) -> Mapping[str, Any]:
    matched = [
        row
        for row in compiled
        if row["exchange"] in {exchange, "ALL"}
        and row["board_bucket"] == board_bucket
        and row["_is_st"] == bool(is_st)
        and row["_effective_start"] <= trade_date
        and (pd.isna(row["_effective_end"]) or row["_effective_end"] >= trade_date)
        and row["_listing_min"] <= listing_session
        and (pd.isna(row["_listing_max"]) or row["_listing_max"] >= listing_session)
        and row["_human_verified"]
    ]
    if len(matched) != 1:
        raise ContractError(
            f"market rule unique-hit failed: {exchange}/{board_bucket}/st={is_st}/"
            f"{trade_date.date()}/session={listing_session}/n={len(matched)}"
        )
    return matched[0]


def match_market_rule(
    rules: pd.DataFrame,
    *,
    exchange: str,
    board_bucket: str,
    is_st: bool,
    trade_date: pd.Timestamp,
    listing_session: int,
) -> pd.Series:
    matched = match_compiled_market_rule(
        compile_market_rules(rules),
        exchange=exchange,
        board_bucket=board_bucket,
        is_st=is_st,
        trade_date=trade_date,
        listing_session=listing_session,
    )
    return pd.Series(
        {key: value for key, value in matched.items() if not key.startswith("_")}
    )


def build_execution_context(
    config: Mapping[str, Any],
    instruments: set[str],
    calendar: pd.DatetimeIndex,
    status: pd.DataFrame,
) -> pd.DataFrame:
    paths = resolved_paths(config)
    master = pd.read_csv(paths["SECURITY_MASTER_FILE"])
    master = master[master["instrument"].isin(instruments)].copy()
    if master["instrument"].nunique() != len(instruments):
        raise ContractError("security master does not cover target union")
    master = master.drop_duplicates("instrument").set_index("instrument")
    master["listing_date"] = pd.to_datetime(master["listing_date"])
    rules = pd.read_csv(paths["MARKET_RULE_REGISTRY_FILE"])
    compiled_rules = compile_market_rules(rules)
    full_calendar = pd.DatetimeIndex(
        pd.to_datetime(pd.read_csv(paths["TRADING_CALENDAR_FILE"])["trade_date"])
        .sort_values()
        .unique()
    )
    rows: list[dict[str, Any]] = []
    status_map = status.set_index(["trade_date", "instrument_id"])
    for instrument in sorted(instruments):
        meta = master.loc[instrument]
        listing_index = int(
            full_calendar.searchsorted(meta["listing_date"], side="left")
        )
        for trade_date in calendar:
            key = (trade_date, instrument)
            if key not in status_map.index:
                raise ContractError(f"missing status row: {trade_date} {instrument}")
            state = status_map.loc[key]
            full_date_index = int(full_calendar.searchsorted(trade_date, side="left"))
            if (
                full_date_index >= len(full_calendar)
                or full_calendar[full_date_index] != trade_date
            ):
                raise ContractError(
                    f"ledger date absent from full calendar: {trade_date}"
                )
            listing_session = full_date_index - listing_index + 1
            rule = match_compiled_market_rule(
                compiled_rules,
                exchange=str(meta["exchange"]),
                board_bucket=str(state["board_bucket"]),
                is_st=_bool_value(state["is_st"]),
                trade_date=trade_date,
                listing_session=listing_session,
            )
            rows.append(
                {
                    "trade_date": trade_date,
                    "instrument_id": instrument,
                    "is_listed": _bool_value(state["is_listed"]),
                    "is_st": _bool_value(state["is_st"]),
                    "is_suspended": _bool_value(state["is_suspended"]),
                    "listing_session": listing_session,
                    "rule_id": rule["rule_id"],
                    "no_limit_flag": _bool_value(rule["no_limit_flag"]),
                    "daily_limit_up_rate": pd.to_numeric(
                        rule["daily_limit_up_rate"], errors="coerce"
                    ),
                    "daily_limit_down_rate": pd.to_numeric(
                        rule["daily_limit_down_rate"], errors="coerce"
                    ),
                    "tick_size": float(rule["tick_size"]),
                    "minimum_buy_order_shares": int(rule["minimum_buy_order_shares"]),
                    "buy_order_increment_shares": int(
                        rule["buy_order_increment_shares"]
                    ),
                    "sell_remainder_rule": rule["sell_remainder_rule"],
                    "transfer_fee_buy_bps": float(rule["transfer_fee_buy_bps"]),
                    "transfer_fee_sell_bps": float(rule["transfer_fee_sell_bps"]),
                }
            )
    return pd.DataFrame(rows).set_index(["trade_date", "instrument_id"]).sort_index()


def price_limit_bounds(
    previous_raw_close: float,
    context_row: pd.Series,
) -> tuple[float, float]:
    if _bool_value(context_row["no_limit_flag"]):
        return -np.inf, np.inf
    if not np.isfinite(previous_raw_close) or previous_raw_close <= 0:
        raise ContractError("missing previous raw close for price limit")
    tick = float(context_row["tick_size"])
    up = round_half_up_to_tick(
        previous_raw_close * (1.0 + float(context_row["daily_limit_up_rate"])),
        tick,
    )
    down = round_half_up_to_tick(
        previous_raw_close * (1.0 - float(context_row["daily_limit_down_rate"])),
        tick,
    )
    return down, up


def _lot_floor(shares: float, minimum: int, increment: int) -> float:
    if shares < minimum:
        return 0.0
    return float(minimum + math.floor((shares - minimum) / increment) * increment)


def preserve_pending_stop_reason(current: str, fallback: str) -> str:
    """Keep the stop-event identity while a latched exit retries."""
    return current if current.startswith("stop:") else fallback


def _mark_positions(
    positions: Mapping[str, Position],
    market: pd.DataFrame,
    trade_date: pd.Timestamp,
    field: str,
) -> tuple[float, dict[str, float]]:
    values: dict[str, float] = {}
    total = 0.0
    for instrument, position in positions.items():
        price = np.nan
        key = (trade_date, instrument)
        if key in market.index:
            price = float(market.loc[key].get(f"qfq_{field}", np.nan))
        if not np.isfinite(price) or price <= 0:
            price = position.last_mark_qfq
        else:
            position.last_mark_qfq = price
        value = position.shares * price
        values[instrument] = float(value)
        total += value
    return float(total), values


def _mapping_fields_for_open(price: pd.Series, tick_size: float) -> dict[str, Any]:
    factor = float(price["raw_qfq_factor"])
    raw_open = float(price["raw_open"])
    lower = float(price["raw_low"]) - 0.5 * tick_size
    upper = float(price["raw_high"]) + 0.5 * tick_size
    domain = bool(lower <= raw_open <= upper)
    factor_pass = bool(price["factor_mapping_pass"])
    return {
        "raw_proxy_fill_price": raw_open,
        "qfq_linked_gross_fill_price": float(price["qfq_open"]),
        "raw_qfq_factor": factor,
        "relative_ratio_spread": float(price["relative_ratio_spread"]),
        "mapping_warning": bool(price["mapping_warning"]),
        "factor_mapping_pass": factor_pass,
        "raw_session_low": float(price["raw_low"]),
        "raw_session_high": float(price["raw_high"]),
        "raw_trigger_tick": np.nan,
        "raw_fill_domain_lower": lower,
        "raw_fill_domain_upper": upper,
        "fill_domain_pass": domain,
        "mapping_pass": factor_pass and domain,
    }


def _scenario_slippage(scenario_id: str) -> float:
    return {
        "GROSS": 0.0,
        "SLIP000": 0.0,
        "SLIP005": 5.0,
        "SLIP010": 10.0,
        "SLIP020": 20.0,
        "SLIP040": 40.0,
    }[scenario_id]


def _event_cost_for_scenario(
    event: Mapping[str, Any], scenario_id: str
) -> dict[str, float]:
    gross = scenario_id == "GROSS"
    return order_costs(
        str(event["side"]),
        float(event["executed_notional"]),
        _scenario_slippage(scenario_id),
        float(event["transfer_fee_bps"]),
        statutory_enabled=not gross,
        commission_enabled=not gross,
    )


def simulate_policy(
    policy: Mapping[str, Any],
    targets: pd.DataFrame,
    calendar: pd.DatetimeIndex,
    market: pd.DataFrame,
    context: pd.DataFrame,
    config: Mapping[str, Any],
) -> dict[str, Any]:
    """Run one reference-5bps stateful path and retain fixed fill quantities."""
    policy_id = str(policy["policy_id"])
    stop_threshold = policy.get("stop_threshold")
    stop_threshold = None if pd.isna(stop_threshold) else float(stop_threshold)
    initial_aum = float(config["execution"]["initial_AUM_cny"])
    decision_dates = sorted(pd.to_datetime(targets["decision_date"]).unique())
    trade_for_decision: dict[pd.Timestamp, pd.Timestamp] = {}
    for decision in decision_dates:
        index = int(calendar.searchsorted(pd.Timestamp(decision), side="right"))
        if index >= len(calendar):
            raise ContractError(f"no next-open rebalance for {decision}")
        trade_for_decision[pd.Timestamp(decision)] = pd.Timestamp(calendar[index])
    decision_for_trade = {
        trade: decision for decision, trade in trade_for_decision.items()
    }
    target_maps = {
        pd.Timestamp(decision): dict(
            zip(
                group["instrument_id"],
                group["target_weight"].astype(float),
                strict=True,
            )
        )
        for decision, group in targets.groupby("decision_date", sort=True)
    }
    score_maps = {
        pd.Timestamp(decision): dict(
            zip(
                group["instrument_id"],
                group["stock_concentration_tilt_score"].astype(float),
                strict=True,
            )
        )
        for decision, group in targets.groupby("decision_date", sort=True)
    }
    cash = initial_aum
    positions: dict[str, Position] = {}
    last_stop_fill: dict[str, pd.Timestamp] = {}
    spell_counter: dict[str, int] = {}
    event_rows: list[dict[str, Any]] = []
    cost_events: list[dict[str, Any]] = []
    daily_rows: list[dict[str, Any]] = []
    snapshots: list[dict[str, Any]] = []
    stop_events: dict[str, dict[str, Any]] = {}
    event_sequence: dict[pd.Timestamp, int] = {}
    reference_cost_cumulative = 0.0
    pretrade_nav_by_decision: dict[pd.Timestamp, float] = {}

    def next_sequence(trade_date: pd.Timestamp) -> int:
        event_sequence[trade_date] = event_sequence.get(trade_date, 0) + 1
        return event_sequence[trade_date]

    def current_nav(trade_date: pd.Timestamp, field: str = "open") -> float:
        marked, _ = _mark_positions(positions, market, trade_date, field)
        return cash + marked

    def blocked_event(
        *,
        trade_date: pd.Timestamp,
        instrument: str,
        event_type: str,
        side: str,
        intended_shares: float,
        intended_notional: float,
        reason: str,
        trigger: float | None = None,
        mapping: Mapping[str, Any] | None = None,
        before_shares: float = 0.0,
        before_basis: float | None = None,
        nav_before: float,
    ) -> dict[str, Any]:
        sequence = next_sequence(trade_date)
        fields = mapping or {
            "raw_proxy_fill_price": np.nan,
            "qfq_linked_gross_fill_price": np.nan,
            "raw_qfq_factor": np.nan,
            "relative_ratio_spread": np.nan,
            "mapping_warning": False,
            "factor_mapping_pass": False,
            "raw_session_low": np.nan,
            "raw_session_high": np.nan,
            "raw_trigger_tick": np.nan,
            "raw_fill_domain_lower": np.nan,
            "raw_fill_domain_upper": np.nan,
            "fill_domain_pass": False,
            "mapping_pass": False,
        }
        row = {
            "policy_id": policy_id,
            "trade_date": trade_date,
            "event_sequence": sequence,
            "instrument_id": instrument,
            "event_type": event_type,
            "intended_side": side,
            "intended_shares": float(intended_shares),
            "intended_notional": float(intended_notional),
            "fill_status": "blocked_unfilled",
            "blocking_reason": reason,
            "executed_shares": 0.0,
            **fields,
            "position_shares_before": float(before_shares),
            "position_shares_after": float(before_shares),
            "cost_basis_before": before_basis,
            "cost_basis_after": before_basis,
            "trigger_price": trigger,
            "cash_before": float(cash),
            "cash_after": float(cash),
            "NAV_before": float(nav_before),
            "NAV_after": float(nav_before),
            "locked_capital_weight": 0.0,
            "daily_bar_execution_proxy": event_type == "stop_trigger",
            "run_id": RUN_ID,
            "contract_version": CONTRACT_VERSION,
        }
        event_rows.append(row)
        return row

    def execute_order(
        *,
        trade_date: pd.Timestamp,
        instrument: str,
        side: str,
        requested_shares: float,
        event_type: str,
        trigger: float | None = None,
        stop_mapping: MappingResult | None = None,
    ) -> dict[str, Any]:
        nonlocal cash, reference_cost_cumulative
        key = (trade_date, instrument)
        before = positions.get(instrument)
        before_shares = before.shares if before else 0.0
        before_basis = before.basis_qfq if before else None
        nav_before = current_nav(trade_date, "open")
        if key not in market.index or key not in context.index:
            if side == "sell" and before:
                before.pending_exit_reason = preserve_pending_stop_reason(
                    before.pending_exit_reason, "missing_market_or_rule"
                )
            return blocked_event(
                trade_date=trade_date,
                instrument=instrument,
                event_type=event_type,
                side=side,
                intended_shares=requested_shares,
                intended_notional=0.0,
                reason="missing_market_or_rule",
                trigger=trigger,
                before_shares=before_shares,
                before_basis=before_basis,
                nav_before=nav_before,
            )
        price = market.loc[key]
        state = context.loc[key]
        tick = float(state["tick_size"])
        if stop_mapping is None:
            mapping = _mapping_fields_for_open(price, tick)
            fill_qfq = float(price["qfq_open"])
            fill_raw = float(price["raw_open"])
        else:
            mapping = {
                "raw_proxy_fill_price": stop_mapping.raw_trigger_tick,
                "qfq_linked_gross_fill_price": stop_mapping.qfq_fill,
                "raw_qfq_factor": stop_mapping.factor,
                "relative_ratio_spread": stop_mapping.relative_spread,
                "mapping_warning": stop_mapping.warning,
                "factor_mapping_pass": stop_mapping.factor_mapping_pass,
                "raw_session_low": float(price["raw_low"]),
                "raw_session_high": float(price["raw_high"]),
                "raw_trigger_tick": stop_mapping.raw_trigger_tick,
                "raw_fill_domain_lower": stop_mapping.raw_fill_domain_lower,
                "raw_fill_domain_upper": stop_mapping.raw_fill_domain_upper,
                "fill_domain_pass": stop_mapping.fill_domain_pass,
                "mapping_pass": stop_mapping.mapping_pass,
            }
            fill_qfq = stop_mapping.qfq_fill
            fill_raw = stop_mapping.raw_trigger_tick
        intended_notional = max(0.0, requested_shares * fill_qfq)
        if not mapping["mapping_pass"]:
            if side == "sell" and before:
                before.pending_exit_reason = preserve_pending_stop_reason(
                    before.pending_exit_reason, "raw_qfq_or_fill_domain_blocked"
                )
            return blocked_event(
                trade_date=trade_date,
                instrument=instrument,
                event_type=event_type,
                side=side,
                intended_shares=requested_shares,
                intended_notional=intended_notional,
                reason="raw_qfq_or_fill_domain_blocked",
                trigger=trigger,
                mapping=mapping,
                before_shares=before_shares,
                before_basis=before_basis,
                nav_before=nav_before,
            )
        if _bool_value(state["is_suspended"]) or not _bool_value(state["is_listed"]):
            if side == "sell" and before:
                before.pending_exit_reason = preserve_pending_stop_reason(
                    before.pending_exit_reason, "suspended_or_not_listed"
                )
            return blocked_event(
                trade_date=trade_date,
                instrument=instrument,
                event_type=event_type,
                side=side,
                intended_shares=requested_shares,
                intended_notional=intended_notional,
                reason="suspended_or_not_listed",
                trigger=trigger,
                mapping=mapping,
                before_shares=before_shares,
                before_basis=before_basis,
                nav_before=nav_before,
            )
        down, up = price_limit_bounds(float(price["previous_raw_close"]), state)
        at_upper = fill_raw >= up - 0.5 * tick
        at_lower = fill_raw <= down + 0.5 * tick
        full_locked_lower = (
            float(price["raw_open"]) <= down + 0.5 * tick
            and float(price["raw_low"]) <= down + 0.5 * tick
            and float(price["raw_high"]) <= down + 0.5 * tick
        )
        limit_blocked = side == "buy" and at_upper
        limit_blocked |= side == "sell" and (
            full_locked_lower if event_type == "stop_trigger" else at_lower
        )
        if limit_blocked:
            if side == "sell" and before:
                before.pending_exit_reason = preserve_pending_stop_reason(
                    before.pending_exit_reason, "limit_down_blocked"
                )
            return blocked_event(
                trade_date=trade_date,
                instrument=instrument,
                event_type=event_type,
                side=side,
                intended_shares=requested_shares,
                intended_notional=intended_notional,
                reason="limit_up_blocked" if side == "buy" else "limit_down_blocked",
                trigger=trigger,
                mapping=mapping,
                before_shares=before_shares,
                before_basis=before_basis,
                nav_before=nav_before,
            )
        minimum = int(state["minimum_buy_order_shares"])
        increment = int(state["buy_order_increment_shares"])
        if side == "buy":
            shares = _lot_floor(requested_shares, minimum, increment)
            transfer_bps = float(state["transfer_fee_buy_bps"])
            while shares > 0:
                costs = order_costs(
                    "buy",
                    shares * fill_qfq,
                    float(config["cost"]["reference_slippage_bps"]),
                    transfer_bps,
                )
                if shares * fill_qfq + costs["total_event_cost_cny"] <= cash + 1e-9:
                    break
                shares = _lot_floor(shares - increment, minimum, increment)
        else:
            if before is None:
                shares = 0.0
            elif requested_shares >= before.shares - 1e-12:
                shares = before.shares
            else:
                shares = float(math.floor(requested_shares / increment) * increment)
            transfer_bps = float(state["transfer_fee_sell_bps"])
        if shares <= 0:
            return blocked_event(
                trade_date=trade_date,
                instrument=instrument,
                event_type=event_type,
                side=side,
                intended_shares=requested_shares,
                intended_notional=intended_notional,
                reason="cash_or_lot_constraint",
                trigger=trigger,
                mapping=mapping,
                before_shares=before_shares,
                before_basis=before_basis,
                nav_before=nav_before,
            )
        notional = float(shares * fill_qfq)
        costs = order_costs(
            side,
            notional,
            float(config["cost"]["reference_slippage_bps"]),
            transfer_bps,
        )
        cash_before = cash
        if side == "buy":
            cash -= notional + costs["total_event_cost_cny"]
            if before is None:
                spell_counter[instrument] = spell_counter.get(instrument, 0) + 1
                before = Position(
                    shares=0.0,
                    basis_qfq=fill_qfq,
                    last_mark_qfq=fill_qfq,
                    holding_spell_id=(
                        f"{policy_id}__{instrument}__SPELL{spell_counter[instrument]:04d}"
                    ),
                )
                positions[instrument] = before
            before.basis_qfq = update_cost_basis(
                before.shares, before.basis_qfq, shares, fill_qfq
            )
            before.shares += shares
            before.last_mark_qfq = fill_qfq
            before.pending_exit_reason = ""
        else:
            cash += notional - costs["total_event_cost_cny"]
            if before is None:
                raise ContractError("sell fill without position")
            before.shares -= shares
            before.last_mark_qfq = fill_qfq
            if before.shares <= 1e-12:
                del positions[instrument]
            else:
                before.pending_exit_reason = ""
        reference_cost_cumulative += costs["total_event_cost_cny"]
        sequence = next_sequence(trade_date)
        after = positions.get(instrument)
        nav_after = current_nav(trade_date, "open")
        row = {
            "policy_id": policy_id,
            "trade_date": trade_date,
            "event_sequence": sequence,
            "instrument_id": instrument,
            "event_type": event_type,
            "intended_side": side,
            "intended_shares": float(requested_shares),
            "intended_notional": intended_notional,
            "fill_status": "filled",
            "blocking_reason": "",
            "executed_shares": float(shares),
            **mapping,
            "position_shares_before": float(before_shares),
            "position_shares_after": float(after.shares if after else 0.0),
            "cost_basis_before": before_basis,
            "cost_basis_after": after.basis_qfq if after else np.nan,
            "trigger_price": trigger,
            "cash_before": float(cash_before),
            "cash_after": float(cash),
            "NAV_before": float(nav_before),
            "NAV_after": float(nav_after),
            "locked_capital_weight": 0.0,
            "daily_bar_execution_proxy": event_type == "stop_trigger",
            "run_id": RUN_ID,
            "contract_version": CONTRACT_VERSION,
        }
        event_rows.append(row)
        cost_events.append(
            {
                "policy_id": policy_id,
                "trade_date": trade_date,
                "event_sequence": sequence,
                "instrument_id": instrument,
                "side": side,
                "executed_shares": float(shares),
                "executed_notional": notional,
                "transfer_fee_bps": transfer_bps,
            }
        )
        return row

    for trade_date in calendar:
        trade_date = pd.Timestamp(trade_date)
        pending = sorted(
            instrument
            for instrument, position in positions.items()
            if position.pending_exit_reason
        )
        for instrument in pending:
            if instrument not in positions:
                continue
            position = positions[instrument]
            reason = position.pending_exit_reason
            result = execute_order(
                trade_date=trade_date,
                instrument=instrument,
                side="sell",
                requested_shares=position.shares,
                event_type="pending_exit_retry",
            )
            if result["fill_status"] == "filled" and reason.startswith("stop:"):
                stop_id = reason.split(":", 1)[1]
                stop_event = stop_events[stop_id]
                costs = _event_cost_for_scenario(
                    cost_events[-1], REFERENCE_COST_SCENARIO
                )
                basis = float(stop_event["basis_qfq"])
                gross_fill = float(result["qfq_linked_gross_fill_price"])
                shares_filled = float(result["executed_shares"])
                gross_loss = gross_fill / basis - 1.0
                net_proceeds = (
                    shares_filled * gross_fill - costs["total_event_cost_cny"]
                )
                net_loss = net_proceeds / (shares_filled * basis) - 1.0
                stop_event["fill_date"] = trade_date
                stop_event["fill_status"] = "filled_after_delay"
                stop_event["blocking_reason"] = ""
                stop_event["trigger_to_fill_delay_sessions"] = int(
                    calendar.get_loc(trade_date)
                    - calendar.get_loc(pd.Timestamp(stop_event["trigger_date"]))
                )
                stop_event["shares_stopped"] = result["executed_shares"]
                stop_event["gross_fill_price_qfq"] = result[
                    "qfq_linked_gross_fill_price"
                ]
                stop_event["raw_trigger_tick"] = result["raw_trigger_tick"]
                stop_event["fill_domain_pass"] = result["fill_domain_pass"]
                stop_event["gross_loss_at_fill_vs_basis"] = gross_loss
                stop_event["reference_net_loss_at_fill_vs_basis"] = net_loss
                stop_event["stop_overshoot"] = max(
                    0.0,
                    -gross_loss - float(stop_event["configured_stop_threshold"]),
                )
                stop_event["stop_proceeds_at_horizon_cny"] = net_proceeds
                last_stop_fill[instrument] = trade_date

        decision = decision_for_trade.get(trade_date)
        if decision is not None:
            pretrade_nav = current_nav(trade_date, "open")
            pretrade_nav_by_decision[decision] = pretrade_nav
            target = target_maps[decision]
            desired: dict[str, float] = {}
            for instrument, weight in target.items():
                key = (trade_date, instrument)
                if key not in market.index or key not in context.index:
                    desired[instrument] = 0.0
                    continue
                qfq_open = float(market.loc[key]["qfq_open"])
                minimum = int(context.loc[key]["minimum_buy_order_shares"])
                increment = int(context.loc[key]["buy_order_increment_shares"])
                desired[instrument] = _lot_floor(
                    pretrade_nav * weight / qfq_open, minimum, increment
                )
            for instrument in sorted(set(positions) | set(desired)):
                current = (
                    positions[instrument].shares if instrument in positions else 0.0
                )
                wanted = desired.get(instrument, 0.0)
                if current > wanted + 1e-12:
                    execute_order(
                        trade_date=trade_date,
                        instrument=instrument,
                        side="sell",
                        requested_shares=current - wanted,
                        event_type="scheduled_rebalance",
                    )
            for instrument in sorted(desired):
                current = (
                    positions[instrument].shares if instrument in positions else 0.0
                )
                wanted = desired[instrument]
                if wanted <= current + 1e-12:
                    continue
                if (
                    instrument in positions
                    and positions[instrument].pending_exit_reason
                ):
                    continue
                stopped = last_stop_fill.get(instrument)
                if stopped is not None and decision <= stopped:
                    continue
                execute_order(
                    trade_date=trade_date,
                    instrument=instrument,
                    side="buy",
                    requested_shares=wanted - current,
                    event_type="scheduled_rebalance",
                )
            marked_open, values_open = _mark_positions(
                positions, market, trade_date, "open"
            )
            snapshots.append(
                {
                    "policy_id": policy_id,
                    "decision_date": decision,
                    "trade_date": trade_date,
                    "position_values": values_open,
                    "marked_position_value": marked_open,
                    "reference_nav_posttrade": cash + marked_open,
                    "reference_cost_cumulative": reference_cost_cumulative,
                    "score_map": score_maps[decision],
                }
            )

        if stop_threshold is not None:
            for instrument in sorted(list(positions)):
                if instrument not in positions:
                    continue
                position = positions[instrument]
                if position.stop_latched_date is not None:
                    continue
                key = (trade_date, instrument)
                if key not in market.index:
                    continue
                price = market.loc[key]
                trigger = position.basis_qfq * (1.0 - stop_threshold)
                qfq_open = float(price["qfq_open"])
                qfq_low = float(price["qfq_low"])
                if not np.isfinite(qfq_open) or not np.isfinite(qfq_low):
                    continue
                trigger_type = ""
                mapping: MappingResult | None = None
                if qfq_open <= trigger:
                    trigger_type = "gap_through_stop"
                elif qfq_low <= trigger:
                    trigger_type = "intraday_touch_stop"
                    raw = {
                        field: float(price[f"raw_{field}"])
                        for field in ("open", "high", "low", "close")
                    }
                    qfq = {
                        field: float(price[f"qfq_{field}"])
                        for field in ("open", "high", "low", "close")
                    }
                    tick = float(context.loc[key]["tick_size"])
                    mapping = map_intraday_stop(
                        trigger,
                        raw,
                        qfq,
                        tick,
                        float(config["stop"]["mapping_warning_spread"]),
                        float(config["stop"]["mapping_block_spread"]),
                    )
                if not trigger_type:
                    continue
                stop_id = f"{position.holding_spell_id}__STOP0001"
                position.stop_latched_date = trade_date
                position.pending_exit_reason = f"stop:{stop_id}"
                stop_row = {
                    "policy_id": policy_id,
                    "holding_spell_id": position.holding_spell_id,
                    "stop_event_id": stop_id,
                    "instrument_id": instrument,
                    "configured_stop_threshold": stop_threshold,
                    "basis_qfq": position.basis_qfq,
                    "trigger_price_qfq": trigger,
                    "trigger_date": trade_date,
                    "trigger_type": trigger_type,
                    "gap_through": trigger_type == "gap_through_stop",
                    "daily_bar_execution_proxy": True,
                    "fill_date": pd.NaT,
                    "fill_status": "latched_blocked",
                    "blocking_reason": "",
                    "trigger_to_fill_delay_sessions": np.nan,
                    "shares_stopped": np.nan,
                    "gross_fill_price_qfq": np.nan,
                    "raw_trigger_tick": np.nan,
                    "fill_domain_pass": False,
                    "gross_loss_at_fill_vs_basis": np.nan,
                    "reference_net_loss_at_fill_vs_basis": np.nan,
                    "stop_overshoot": np.nan,
                    "counterfactual_horizon_date": pd.NaT,
                    "counterfactual_horizon_truncated": False,
                    "counterfactual_exit_is_cost_estimate": True,
                    "stop_proceeds_at_horizon_cny": np.nan,
                    "no_stop_value_at_horizon_cny": np.nan,
                    "stop_exit_vs_hold_delta_cny": np.nan,
                    "stop_avoided_loss_cny": np.nan,
                    "stop_missed_rebound_cny": np.nan,
                    "attribution_evaluable": False,
                    "attribution_missing_reason": "stop_not_filled",
                    "attribution_cost_scenario_id": REFERENCE_COST_SCENARIO,
                    "attribution_role": "ex_post_counterfactual_attribution_only",
                    "run_id": RUN_ID,
                    "contract_version": CONTRACT_VERSION,
                }
                stop_events[stop_id] = stop_row
                result = execute_order(
                    trade_date=trade_date,
                    instrument=instrument,
                    side="sell",
                    requested_shares=position.shares,
                    event_type="stop_trigger",
                    trigger=trigger,
                    stop_mapping=mapping,
                )
                if result["fill_status"] == "filled":
                    costs = _event_cost_for_scenario(
                        cost_events[-1], REFERENCE_COST_SCENARIO
                    )
                    gross_loss = (
                        result["qfq_linked_gross_fill_price"] / position.basis_qfq - 1.0
                    )
                    net_proceeds = (
                        result["executed_shares"]
                        * result["qfq_linked_gross_fill_price"]
                        - costs["total_event_cost_cny"]
                    )
                    net_loss = (
                        net_proceeds / (result["executed_shares"] * position.basis_qfq)
                        - 1.0
                    )
                    stop_row.update(
                        {
                            "fill_date": trade_date,
                            "fill_status": "filled_same_day",
                            "trigger_to_fill_delay_sessions": 0,
                            "shares_stopped": result["executed_shares"],
                            "gross_fill_price_qfq": result[
                                "qfq_linked_gross_fill_price"
                            ],
                            "raw_trigger_tick": result["raw_trigger_tick"],
                            "fill_domain_pass": result["fill_domain_pass"],
                            "gross_loss_at_fill_vs_basis": gross_loss,
                            "reference_net_loss_at_fill_vs_basis": net_loss,
                            "stop_overshoot": max(
                                0.0, -gross_loss - float(stop_threshold)
                            ),
                            "stop_proceeds_at_horizon_cny": net_proceeds,
                        }
                    )
                    last_stop_fill[instrument] = trade_date
                else:
                    if instrument in positions:
                        positions[instrument].pending_exit_reason = f"stop:{stop_id}"
                    stop_row["blocking_reason"] = result["blocking_reason"]

        marked_close, values_close = _mark_positions(
            positions, market, trade_date, "close"
        )
        reference_nav = cash + marked_close
        locked_value = sum(
            values_close.get(instrument, 0.0)
            for instrument, position in positions.items()
            if position.pending_exit_reason
        )
        daily_rows.append(
            {
                "policy_id": policy_id,
                "trade_date": trade_date,
                "reference_net_cash": float(cash),
                "reference_cost_cumulative": float(reference_cost_cumulative),
                "marked_position_value": marked_close,
                "reference_net_NAV": reference_nav,
                "locked_capital_weight": (
                    locked_value / reference_nav if reference_nav > 0 else np.nan
                ),
            }
        )

    stop_frame = pd.DataFrame(list(stop_events.values()))
    if not stop_frame.empty:
        _finalize_stop_attribution(
            stop_frame,
            trade_for_decision,
            calendar,
            market,
            context,
            config,
        )
    else:
        stop_frame = pd.DataFrame(columns=STOP_EVENT_COLUMNS)
    return {
        "execution": pd.DataFrame(event_rows),
        "cost_events": pd.DataFrame(cost_events),
        "reference_daily": pd.DataFrame(daily_rows),
        "snapshots": snapshots,
        "stop_events": stop_frame,
        "pretrade_nav_by_decision": pretrade_nav_by_decision,
        "trade_for_decision": trade_for_decision,
        "final_positions": {
            instrument: Position(
                shares=position.shares,
                basis_qfq=position.basis_qfq,
                last_mark_qfq=position.last_mark_qfq,
                holding_spell_id=position.holding_spell_id,
                pending_exit_reason=position.pending_exit_reason,
                stop_latched_date=position.stop_latched_date,
            )
            for instrument, position in positions.items()
        },
    }


def _finalize_stop_attribution(
    stop_frame: pd.DataFrame,
    trade_for_decision: Mapping[pd.Timestamp, pd.Timestamp],
    calendar: pd.DatetimeIndex,
    market: pd.DataFrame,
    context: pd.DataFrame,
    config: Mapping[str, Any],
) -> None:
    scheduled = sorted(trade_for_decision.values())
    terminal = pd.Timestamp(config["population"]["ledger_end_date"])
    for index, row in stop_frame.iterrows():
        if pd.isna(row["fill_date"]):
            continue
        fill_date = pd.Timestamp(row["fill_date"])
        later = [date for date in scheduled if date > fill_date]
        horizon = later[0] if later else terminal
        truncated = not later
        instrument = str(row["instrument_id"])
        key = (horizon, instrument)
        if key not in market.index or key not in context.index:
            stop_frame.loc[index, "attribution_missing_reason"] = (
                "missing_horizon_mark_or_rule"
            )
            continue
        price = market.loc[key]
        mark = float(price["qfq_open"] if not truncated else price["qfq_close"])
        if not np.isfinite(mark) or mark <= 0:
            stop_frame.loc[index, "attribution_missing_reason"] = "invalid_horizon_mark"
            continue
        shares = float(row["shares_stopped"])
        gross_value = shares * mark
        state = context.loc[key]
        exit_cost = order_costs(
            "sell",
            gross_value,
            float(config["cost"]["reference_slippage_bps"]),
            float(state["transfer_fee_sell_bps"]),
        )["total_event_cost_cny"]
        no_stop_value = gross_value - exit_cost
        proceeds = float(row["stop_proceeds_at_horizon_cny"])
        delta = proceeds - no_stop_value
        stop_frame.loc[index, "counterfactual_horizon_date"] = horizon
        stop_frame.loc[index, "counterfactual_horizon_truncated"] = truncated
        stop_frame.loc[index, "no_stop_value_at_horizon_cny"] = no_stop_value
        stop_frame.loc[index, "stop_exit_vs_hold_delta_cny"] = delta
        stop_frame.loc[index, "stop_avoided_loss_cny"] = max(delta, 0.0)
        stop_frame.loc[index, "stop_missed_rebound_cny"] = max(-delta, 0.0)
        stop_frame.loc[index, "attribution_evaluable"] = True
        stop_frame.loc[index, "attribution_missing_reason"] = ""


def build_cost_shadows(
    simulation: Mapping[str, Any],
    config: Mapping[str, Any],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    events = simulation["cost_events"].copy()
    reference_daily = simulation["reference_daily"].copy()
    cost_rows: list[dict[str, Any]] = []
    cumulative = {scenario: 0.0 for scenario in COST_IDS}
    if len(events):
        events = events.sort_values(["trade_date", "event_sequence", "instrument_id"])
        for event in events.to_dict("records"):
            for scenario in COST_IDS:
                costs = _event_cost_for_scenario(event, scenario)
                cumulative[scenario] += costs["total_event_cost_cny"]
                cost_rows.append(
                    {
                        "policy_id": event["policy_id"],
                        "cost_scenario_id": scenario,
                        "trade_date": event["trade_date"],
                        "event_sequence": event["event_sequence"],
                        "instrument_id": event["instrument_id"],
                        "side": event["side"],
                        "executed_shares": event["executed_shares"],
                        "executed_notional": event["executed_notional"],
                        **costs,
                        "cumulative_cost_liability_cny": cumulative[scenario],
                        "counterfactual_cost_shadow": scenario
                        != REFERENCE_COST_SCENARIO,
                        "deployment_interpretation_allowed": False,
                        "run_id": RUN_ID,
                        "contract_version": CONTRACT_VERSION,
                    }
                )
    cost_frame = pd.DataFrame(cost_rows, columns=COST_SHADOW_COLUMNS)
    if len(cost_frame) != 6 * len(events):
        raise ContractError("cost shadow row count mismatch")

    cumulative_by_day: dict[str, pd.Series] = {}
    component_by_day: dict[tuple[str, str], pd.Series] = {}
    if len(cost_frame):
        for scenario, group in cost_frame.groupby("cost_scenario_id"):
            daily = group.groupby("trade_date")["total_event_cost_cny"].sum().cumsum()
            cumulative_by_day[scenario] = daily
            for component in (
                "commission_cny",
                "stamp_tax_cny",
                "transfer_fee_cny",
                "slippage_cny",
            ):
                component_by_day[(scenario, component)] = group.groupby("trade_date")[
                    component
                ].sum()
    nav_rows: list[dict[str, Any]] = []
    for scenario in COST_IDS:
        previous_nav = np.nan
        evaluable = True
        for row in reference_daily.sort_values("trade_date").to_dict("records"):
            trade_date = pd.Timestamp(row["trade_date"])
            liability = 0.0
            if scenario in cumulative_by_day:
                prior = cumulative_by_day[scenario]
                liability = (
                    float(prior.loc[prior.index <= trade_date].iloc[-1])
                    if (prior.index <= trade_date).any()
                    else 0.0
                )
            gross_cash = float(
                row["reference_net_cash"] + row["reference_cost_cumulative"]
            )
            gross_nav = gross_cash + float(row["marked_position_value"])
            scenario_cash = gross_cash - liability
            scenario_nav = gross_nav - liability
            if scenario_nav <= 0:
                evaluable = False
            daily_return = (
                scenario_nav / previous_nav - 1.0
                if evaluable and np.isfinite(previous_nav) and previous_nav > 0
                else np.nan
            )
            invested_weight = (
                float(row["marked_position_value"]) / scenario_nav
                if scenario_nav > 0
                else np.nan
            )
            nav_rows.append(
                {
                    "policy_id": row["policy_id"],
                    "cost_scenario_id": scenario,
                    "trade_date": trade_date,
                    "gross_shadow_cash": gross_cash,
                    "scenario_cost_liability": liability,
                    "scenario_cash_after_cost": scenario_cash,
                    "marked_position_value": row["marked_position_value"],
                    "scenario_NAV": scenario_nav,
                    "daily_return": daily_return,
                    "shadow_cash_deficit_cny": max(-scenario_cash, 0.0),
                    "shadow_self_financing": scenario_cash >= 0,
                    "locked_capital_weight": row["locked_capital_weight"],
                    "invested_weight": invested_weight,
                    "scenario_evaluable": evaluable,
                    "exclusion_reason": "" if evaluable else "shadow_nav_nonpositive",
                    "run_id": RUN_ID,
                    "contract_version": CONTRACT_VERSION,
                }
            )
            previous_nav = scenario_nav
    nav_frame = pd.DataFrame(nav_rows).loc[:, DAILY_NAV_COLUMNS]
    reference = nav_frame[nav_frame["cost_scenario_id"].eq(REFERENCE_COST_SCENARIO)]
    expected = reference_daily.sort_values("trade_date")["reference_net_NAV"].to_numpy()
    if not np.allclose(reference["scenario_NAV"], expected, atol=1e-8, rtol=0.0):
        raise ContractError("SLIP005 shadow differs from reference stateful NAV")
    gross = nav_frame[nav_frame["cost_scenario_id"].eq("GROSS")]
    if not np.allclose(gross["scenario_cost_liability"], 0.0, atol=0.0, rtol=0.0):
        raise ContractError("GROSS liability is not zero")
    return cost_frame, nav_frame


MONTHLY_COLUMNS = [
    "policy_id",
    "cost_scenario_id",
    "decision_date",
    "label_month",
    "gross_return",
    "net_return",
    "commission_return",
    "stamp_tax_return",
    "transfer_fee_return",
    "slippage_return",
    "target_one_way_turnover",
    "attempted_one_way_turnover",
    "realized_one_way_turnover",
    "invested_weight",
    "cash_weight",
    "locked_capital_weight",
    "effective_holdings",
    "board_HHI",
    "top1_board_weight",
    "top3_board_weight",
    "no_board_position_weight",
    "classified_board_coverage_ratio",
    "stop_trigger_n",
    "stop_fill_n",
    "stop_blocked_n",
    "shadow_cash_deficit_cny",
    "shadow_self_financing",
    "month_evaluable",
    "exclusion_reason",
    "event_month_posthoc",
    "run_id",
    "contract_version",
]
BOARD_CONCENTRATION_COLUMNS = [
    "policy_id",
    "cost_scenario_id",
    "decision_date",
    "concentration_scope",
    "board_HHI",
    "top1_board_weight",
    "top3_board_weight",
    "no_board_position_weight",
    "classified_position_weight",
    "classified_board_coverage_ratio",
    "concentration_status",
    "mean_stock_concentration_tilt_score",
    "effective_holdings",
    "source_table_content_hash",
    "historical_PIT_sector_claim_allowed",
    "market_trading_crowding_claim_allowed",
    "run_id",
    "contract_version",
]
PAIRED_DELTA_COLUMNS = [
    "comparison_id",
    "decision_date",
    "lhs_monthly_return",
    "rhs_monthly_return",
    "paired_delta",
    "lhs_evaluable",
    "rhs_evaluable",
    "paired_evaluable",
    "event_month_posthoc",
    "missing_reason",
    "run_id",
    "contract_version",
]
BOOTSTRAP_COLUMNS = [
    "comparison_id",
    "month_scope",
    "paired_month_n",
    "required_calendar_month_n",
    "mean_delta",
    "median_delta",
    "win_month_rate",
    "worst_delta",
    "bootstrap_method",
    "rng_bit_generator",
    "seed",
    "block_length_months",
    "sampled_block_n",
    "repetitions",
    "bootstrap_statistic",
    "quantile_method",
    "CI_lower",
    "CI_median",
    "CI_upper",
    "status",
    "missing_reason",
    "run_id",
    "contract_version",
]
TURNOVER_COST_COLUMNS = [
    "policy_id",
    "cost_scenario_id",
    "mean_target_one_way_turnover",
    "mean_attempted_one_way_turnover",
    "mean_realized_one_way_turnover",
    "total_commission_cny",
    "total_stamp_tax_cny",
    "total_transfer_fee_cny",
    "total_slippage_cny",
    "total_cost_return",
    "maximum_shadow_cash_deficit_cny",
    "shadow_self_financing",
    "live_nav_break_even_slippage_bps",
    "live_nav_break_even_status",
    "liquidation_adjusted_break_even_slippage_bps",
    "liquidation_adjusted_break_even_status",
    "raw_qfq_mapping_warning_n",
    "max_relative_ratio_spread",
    "source_table_content_hash",
    "historical_support_claim_allowed",
    "deployment_authorized",
    "run_id",
    "contract_version",
]
STOP_READOUT_COLUMNS = [
    "policy_id",
    "aggregation_scope",
    "stop_trigger_n",
    "stop_fill_n",
    "stop_blocked_n",
    "mean_trigger_to_fill_delay_sessions",
    "mean_stop_overshoot",
    "stopped_capital_weight",
    "stop_exit_vs_hold_delta_cny",
    "stop_avoided_loss_cny",
    "stop_missed_rebound_cny",
    "stop_attribution_missing_n",
    "source_table_content_hash",
    "ex_post_counterfactual_attribution_only",
    "status",
    "missing_reason",
    "run_id",
    "contract_version",
]
EVENT_SLICE_COLUMNS = [
    "policy_id",
    "cost_scenario_id",
    "event_scope",
    "month_n",
    "mean_monthly_return",
    "median_monthly_return",
    "compound_return",
    "positive_month_rate",
    "worst_month_return",
    "source_table_content_hash",
    "posthoc_slice_only",
    "parameter_selection_authorized",
    "run_id",
    "contract_version",
]
TERMINAL_COLUMNS = [
    "policy_id",
    "cost_scenario_id",
    "terminal_mark_date",
    "open_position_n",
    "open_position_weight",
    "open_position_notional_cny",
    "sell_commission_cny",
    "sell_stamp_tax_cny",
    "sell_transfer_fee_cny",
    "sell_slippage_cny",
    "total_shadow_cost_cny",
    "live_final_NAV",
    "liquidation_adjusted_final_NAV",
    "live_nav_compound_return",
    "liquidation_adjusted_compound_return",
    "live_nav_break_even_slippage_bps",
    "live_nav_break_even_status",
    "liquidation_adjusted_break_even_slippage_bps",
    "liquidation_adjusted_break_even_status",
    "historical_support_claim_allowed",
    "deployment_authorized",
    "source_table_content_hash",
    "run_id",
    "contract_version",
]


SUMMARY_METRICS = [
    "month_n",
    "mean_monthly_return",
    "median_monthly_return",
    "compound_return",
    "annualized_return",
    "annualized_volatility",
    "zero_hurdle_sharpe",
    "positive_month_rate",
    "worst_month_return",
    "empirical_p10_monthly_return",
    "ES10_loss",
    "max_drawdown_from_daily_NAV",
    "event_month_mean_return",
    "non_event_month_mean_return",
    "mean_target_one_way_turnover",
    "mean_attempted_one_way_turnover",
    "mean_realized_one_way_turnover",
    "total_commission_cny",
    "total_stamp_tax_cny",
    "total_transfer_fee_cny",
    "total_slippage_cny",
    "total_cost_return",
    "live_nav_break_even_slippage_bps",
    "liquidation_adjusted_break_even_slippage_bps",
    "mean_invested_weight",
    "mean_cash_weight",
    "mean_locked_capital_weight",
    "minimum_effective_holdings",
    "maximum_single_instrument_weight",
    "terminal_open_position_weight",
    "terminal_liquidation_cost_shadow_cny",
    "live_nav_compound_return",
    "liquidation_adjusted_compound_return",
    "maximum_shadow_cash_deficit_cny",
    "shadow_self_financing",
    "raw_qfq_mapping_warning_n",
    "max_relative_ratio_spread",
    "mean_target_board_HHI",
    "mean_realized_board_HHI",
    "max_top1_board_weight",
    "max_top3_board_weight",
    "mean_target_no_board_position_weight",
    "mean_realized_no_board_position_weight",
    "minimum_target_classified_board_coverage_ratio",
    "minimum_realized_classified_board_coverage_ratio",
    "mean_stock_concentration_tilt_score",
    "stop_trigger_n",
    "stop_fill_n",
    "stop_blocked_n",
    "mean_trigger_to_fill_delay_sessions",
    "mean_stop_overshoot",
    "stopped_capital_weight",
    "stop_exit_vs_hold_delta_cny",
    "stop_avoided_loss_cny",
    "stop_missed_rebound_cny",
    "stop_attribution_missing_n",
]
SUMMARY_COLUMNS = [
    "policy_id",
    "cost_scenario_id",
    "month_scope",
    *SUMMARY_METRICS,
    "status",
    "missing_reason",
    "historical_support_claim_allowed",
    "model_repair_claim_allowed",
    "parameter_selection_authorized",
    "deployment_authorized",
    "run_id",
    "contract_version",
]


def build_board_concentration_readout(
    simulation: Mapping[str, Any],
    nav: pd.DataFrame,
    targets: pd.DataFrame,
    membership: pd.DataFrame,
) -> pd.DataFrame:
    policy_id = str(targets["policy_id"].iloc[0])
    cost_liability = nav.set_index(["cost_scenario_id", "trade_date"])[
        "scenario_cost_liability"
    ]
    rows: list[dict[str, Any]] = []
    for snapshot in simulation["snapshots"]:
        decision = pd.Timestamp(snapshot["decision_date"])
        trade_date = pd.Timestamp(snapshot["trade_date"])
        target_group = targets[pd.to_datetime(targets["decision_date"]).eq(decision)]
        target_weights = dict(
            zip(
                target_group["instrument_id"],
                target_group["target_weight"].astype(float),
                strict=True,
            )
        )
        score_map = snapshot["score_map"]
        target_metrics = concentration_metrics(target_weights, membership, score_map)
        for scenario in COST_IDS:
            target_row = {
                "policy_id": policy_id,
                "cost_scenario_id": scenario,
                "decision_date": decision,
                "concentration_scope": "target",
                **target_metrics,
            }
            target_row["source_table_content_hash"] = stable_hash(
                {"weights": target_weights, "scope": "target"}
            )
            target_row["historical_PIT_sector_claim_allowed"] = False
            target_row["market_trading_crowding_claim_allowed"] = False
            target_row["run_id"] = RUN_ID
            target_row["contract_version"] = CONTRACT_VERSION
            rows.append(target_row)

            liability = float(cost_liability.get((scenario, trade_date), 0.0))
            gross_nav = float(snapshot["reference_nav_posttrade"]) + float(
                snapshot["reference_cost_cumulative"]
            )
            scenario_nav = gross_nav - liability
            if scenario_nav <= 0:
                realized_metrics = concentration_metrics({}, membership, score_map)
                realized_metrics["concentration_status"] = (
                    "not_evaluable_shadow_nav_nonpositive"
                )
            else:
                realized_weights = {
                    instrument: value / scenario_nav
                    for instrument, value in snapshot["position_values"].items()
                }
                realized_metrics = concentration_metrics(
                    realized_weights, membership, score_map
                )
            realized_row = {
                "policy_id": policy_id,
                "cost_scenario_id": scenario,
                "decision_date": decision,
                "concentration_scope": "realized_posttrade",
                **realized_metrics,
                "source_table_content_hash": stable_hash(
                    {
                        "positions": snapshot["position_values"],
                        "scenario_nav": scenario_nav,
                        "scope": "realized_posttrade",
                    }
                ),
                "historical_PIT_sector_claim_allowed": False,
                "market_trading_crowding_claim_allowed": False,
                "run_id": RUN_ID,
                "contract_version": CONTRACT_VERSION,
            }
            rows.append(realized_row)
    return pd.DataFrame(rows).loc[:, BOARD_CONCENTRATION_COLUMNS]


def _component_costs_by_month(cost_frame: pd.DataFrame) -> pd.DataFrame:
    if cost_frame.empty:
        return pd.DataFrame()
    frame = cost_frame.copy()
    frame["label_month"] = (
        pd.to_datetime(frame["trade_date"]).dt.to_period("M").astype(str)
    )
    columns = [
        "commission_cny",
        "stamp_tax_cny",
        "transfer_fee_cny",
        "slippage_cny",
    ]
    return frame.groupby(["cost_scenario_id", "label_month"])[columns].sum()


def build_monthly_returns(
    simulation: Mapping[str, Any],
    nav: pd.DataFrame,
    cost_frame: pd.DataFrame,
    targets: pd.DataFrame,
    board_readout: pd.DataFrame,
    config: Mapping[str, Any],
) -> pd.DataFrame:
    policy_id = str(targets["policy_id"].iloc[0])
    turnover = target_turnover_series(targets).set_index("decision_date")
    events = simulation["execution"].copy()
    if len(events):
        events["label_month"] = (
            pd.to_datetime(events["trade_date"]).dt.to_period("M").astype(str)
        )
    costs_month = _component_costs_by_month(cost_frame)
    nav = nav.copy()
    nav["trade_date"] = pd.to_datetime(nav["trade_date"])
    nav["label_month"] = nav["trade_date"].dt.to_period("M").astype(str)
    gross_nav = nav[nav["cost_scenario_id"].eq("GROSS")]
    gross_end = (
        gross_nav.groupby("label_month", sort=True).tail(1).set_index("label_month")
    )
    rows: list[dict[str, Any]] = []
    decisions = sorted(pd.to_datetime(targets["decision_date"]).unique())
    stop_frame = simulation["stop_events"]
    realized_board = board_readout[
        board_readout["concentration_scope"].eq("realized_posttrade")
    ].set_index(["cost_scenario_id", "decision_date"])
    for scenario in COST_IDS:
        scenario_nav = nav[nav["cost_scenario_id"].eq(scenario)]
        month_end = (
            scenario_nav.groupby("label_month", sort=True)
            .tail(1)
            .set_index("label_month")
        )
        for decision_index, decision in enumerate(decisions):
            decision = pd.Timestamp(decision)
            label_month = str(decision.to_period("M") + 1)
            current = month_end.loc[label_month]
            gross_current = gross_end.loc[label_month]
            if decision_index == 0:
                prior_nav = float(config["execution"]["initial_AUM_cny"])
                prior_gross = prior_nav
            else:
                prior_month = str(decisions[decision_index - 1].to_period("M") + 1)
                prior_nav = float(month_end.loc[prior_month, "scenario_NAV"])
                prior_gross = float(gross_end.loc[prior_month, "scenario_NAV"])
            evaluable = bool(current["scenario_evaluable"]) and prior_nav > 0
            net_return = (
                float(current["scenario_NAV"] / prior_nav - 1.0)
                if evaluable
                else np.nan
            )
            gross_return = float(gross_current["scenario_NAV"] / prior_gross - 1.0)
            monthly_events = (
                events[events["label_month"].eq(label_month)]
                if len(events)
                else pd.DataFrame()
            )
            intended = float(
                monthly_events.get("intended_notional", pd.Series(dtype=float)).sum()
            )
            realized = (
                float(
                    monthly_events.loc[
                        monthly_events.get("fill_status", pd.Series(dtype=str)).eq(
                            "filled"
                        ),
                        "executed_shares",
                    ]
                    .mul(
                        monthly_events.loc[
                            monthly_events.get("fill_status", pd.Series(dtype=str)).eq(
                                "filled"
                            ),
                            "qfq_linked_gross_fill_price",
                        ]
                    )
                    .sum()
                )
                if len(monthly_events)
                else 0.0
            )
            pretrade = float(simulation["pretrade_nav_by_decision"][decision])
            target_turn = float(turnover.loc[decision, "target_one_way_turnover"])
            attempted_turn = intended / (2.0 * pretrade) if pretrade > 0 else np.nan
            realized_turn = realized / (2.0 * pretrade) if pretrade > 0 else np.nan
            component = {
                name: 0.0
                for name in (
                    "commission_cny",
                    "stamp_tax_cny",
                    "transfer_fee_cny",
                    "slippage_cny",
                )
            }
            key = (scenario, label_month)
            if len(costs_month) and key in costs_month.index:
                component.update(costs_month.loc[key].to_dict())
            board_key = (scenario, decision)
            board = realized_board.loc[board_key]
            stops = pd.DataFrame()
            if len(stop_frame):
                stops = stop_frame[
                    pd.to_datetime(stop_frame["trigger_date"])
                    .dt.to_period("M")
                    .astype(str)
                    .eq(label_month)
                ]
            row = {
                "policy_id": policy_id,
                "cost_scenario_id": scenario,
                "decision_date": decision,
                "label_month": label_month,
                "gross_return": gross_return,
                "net_return": net_return,
                "commission_return": component["commission_cny"] / prior_nav,
                "stamp_tax_return": component["stamp_tax_cny"] / prior_nav,
                "transfer_fee_return": component["transfer_fee_cny"] / prior_nav,
                "slippage_return": component["slippage_cny"] / prior_nav,
                "target_one_way_turnover": target_turn,
                "attempted_one_way_turnover": attempted_turn,
                "realized_one_way_turnover": realized_turn,
                "invested_weight": current["invested_weight"],
                "cash_weight": 1.0 - float(current["invested_weight"])
                if np.isfinite(current["invested_weight"])
                else np.nan,
                "locked_capital_weight": current["locked_capital_weight"],
                "effective_holdings": board["effective_holdings"],
                "board_HHI": board["board_HHI"],
                "top1_board_weight": board["top1_board_weight"],
                "top3_board_weight": board["top3_board_weight"],
                "no_board_position_weight": board["no_board_position_weight"],
                "classified_board_coverage_ratio": board[
                    "classified_board_coverage_ratio"
                ],
                "stop_trigger_n": len(stops),
                "stop_fill_n": int(stops["fill_date"].notna().sum())
                if len(stops)
                else 0,
                "stop_blocked_n": int(stops["fill_date"].isna().sum())
                if len(stops)
                else 0,
                "shadow_cash_deficit_cny": current["shadow_cash_deficit_cny"],
                "shadow_self_financing": current["shadow_self_financing"],
                "month_evaluable": evaluable,
                "exclusion_reason": "" if evaluable else current["exclusion_reason"],
                "event_month_posthoc": label_month in EVENT_MONTHS,
                "run_id": RUN_ID,
                "contract_version": CONTRACT_VERSION,
            }
            rows.append(row)
    return pd.DataFrame(rows).loc[:, MONTHLY_COLUMNS]


def build_paired_outputs(
    monthly: pd.DataFrame,
    comparisons: pd.DataFrame,
    config: Mapping[str, Any],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    lookup = monthly.set_index(["policy_id", "cost_scenario_id", "decision_date"])
    delta_rows: list[dict[str, Any]] = []
    for comparison in comparisons.sort_values("comparison_id").to_dict("records"):
        lhs = lookup.loc[
            (comparison["lhs_policy_id"], comparison["lhs_cost_scenario_id"])
        ].sort_index()
        rhs = lookup.loc[
            (comparison["rhs_policy_id"], comparison["rhs_cost_scenario_id"])
        ].sort_index()
        dates = sorted(set(lhs.index) | set(rhs.index))
        for decision in dates:
            lhs_row = lhs.loc[decision]
            rhs_row = rhs.loc[decision]
            lhs_ok = bool(lhs_row["month_evaluable"])
            rhs_ok = bool(rhs_row["month_evaluable"])
            paired_ok = lhs_ok and rhs_ok
            delta_rows.append(
                {
                    "comparison_id": comparison["comparison_id"],
                    "decision_date": pd.Timestamp(decision),
                    "lhs_monthly_return": lhs_row["net_return"],
                    "rhs_monthly_return": rhs_row["net_return"],
                    "paired_delta": (
                        float(lhs_row["net_return"] - rhs_row["net_return"])
                        if paired_ok
                        else np.nan
                    ),
                    "lhs_evaluable": lhs_ok,
                    "rhs_evaluable": rhs_ok,
                    "paired_evaluable": paired_ok,
                    "event_month_posthoc": bool(lhs_row["event_month_posthoc"]),
                    "missing_reason": "" if paired_ok else "lhs_or_rhs_not_evaluable",
                    "run_id": RUN_ID,
                    "contract_version": CONTRACT_VERSION,
                }
            )
    deltas = pd.DataFrame(delta_rows).loc[:, PAIRED_DELTA_COLUMNS]
    expected = int(config["statistics"]["paired_comparison_n"]) * 21
    if len(deltas) != expected:
        raise ContractError(f"paired delta row count mismatch: {len(deltas)}")
    rng = np.random.Generator(np.random.PCG64(int(config["statistics"]["seed"])))
    bootstrap_rows: list[dict[str, Any]] = []
    for comparison_id, group in deltas.groupby("comparison_id", sort=True):
        group = group.sort_values("decision_date")
        usable = group[group["paired_evaluable"]]
        values = usable["paired_delta"].to_numpy(dtype=float)
        complete = len(usable) == 21 and np.isfinite(values).all()
        ci = np.full(3, np.nan)
        if complete:
            draws = circular_moving_block_bootstrap(
                values,
                rng,
                block_length=int(config["statistics"]["block_length_months"]),
                repetitions=int(config["statistics"]["repetitions"]),
            )
            ci = np.quantile(
                draws,
                config["statistics"]["quantiles"],
                method=config["statistics"]["quantile_method"],
            )
        bootstrap_rows.append(
            {
                "comparison_id": comparison_id,
                "month_scope": "all",
                "paired_month_n": len(usable),
                "required_calendar_month_n": 21,
                "mean_delta": float(np.mean(values)) if len(values) else np.nan,
                "median_delta": float(np.median(values)) if len(values) else np.nan,
                "win_month_rate": float(np.mean(values > 0)) if len(values) else np.nan,
                "worst_delta": float(np.min(values)) if len(values) else np.nan,
                "bootstrap_method": config["statistics"]["bootstrap_method"],
                "rng_bit_generator": "PCG64",
                "seed": int(config["statistics"]["seed"]),
                "block_length_months": int(config["statistics"]["block_length_months"]),
                "sampled_block_n": int(config["statistics"]["sampled_block_count"]),
                "repetitions": int(config["statistics"]["repetitions"]),
                "bootstrap_statistic": "paired_mean_monthly_delta",
                "quantile_method": config["statistics"]["quantile_method"],
                "CI_lower": ci[0],
                "CI_median": ci[1],
                "CI_upper": ci[2],
                "status": "evaluable"
                if complete
                else "not_evaluable_incomplete_calendar",
                "missing_reason": "" if complete else "incomplete_21_month_calendar",
                "run_id": RUN_ID,
                "contract_version": CONTRACT_VERSION,
            }
        )
    bootstrap = pd.DataFrame(bootstrap_rows).loc[:, BOOTSTRAP_COLUMNS]
    return deltas, bootstrap


def build_terminal_readout(
    simulation: Mapping[str, Any],
    nav: pd.DataFrame,
    cost_frame: pd.DataFrame,
    market: pd.DataFrame,
    context: pd.DataFrame,
    config: Mapping[str, Any],
) -> pd.DataFrame:
    policy_id = str(nav["policy_id"].iloc[0])
    terminal_date = pd.Timestamp(config["population"]["ledger_end_date"])
    positions: Mapping[str, Position] = simulation["final_positions"]
    terminal_items: list[tuple[str, float, pd.Series]] = []
    for instrument, position in sorted(positions.items()):
        key = (terminal_date, instrument)
        if key not in market.index or key not in context.index:
            raise ContractError(f"missing terminal mark/rule: {instrument}")
        mark = float(market.loc[key]["qfq_close"])
        if not np.isfinite(mark) or mark <= 0:
            mark = position.last_mark_qfq
        terminal_items.append((instrument, position.shares * mark, context.loc[key]))
    terminal_notional = float(sum(item[1] for item in terminal_items))
    gross_final_nav = float(
        nav[nav["cost_scenario_id"].eq("GROSS")]
        .sort_values("trade_date")
        .iloc[-1]["scenario_NAV"]
    )
    executed_notional = float(
        simulation["cost_events"].get("executed_notional", pd.Series(dtype=float)).sum()
    )
    fixed_live = {"commission_cny": 0.0, "stamp_tax_cny": 0.0, "transfer_fee_cny": 0.0}
    if len(cost_frame):
        zero = cost_frame[cost_frame["cost_scenario_id"].eq("SLIP000")]
        for component in fixed_live:
            fixed_live[component] = float(zero[component].sum())
    fixed_live_total = float(sum(fixed_live.values()))
    initial_aum = float(config["execution"]["initial_AUM_cny"])
    root_kwargs = {
        "bracket": tuple(config["cost"]["break_even_root_bracket_bps"]),
        "tolerance": float(config["cost"]["break_even_root_tolerance_bps"]),
        "max_iterations": int(config["cost"]["break_even_root_max_iterations"]),
    }
    live_root, live_status = break_even_bisection(
        gross_final_nav,
        initial_aum,
        fixed_live_total,
        executed_notional,
        **root_kwargs,
    )
    terminal_fixed_total = 0.0
    for _, notional, state in terminal_items:
        costs = order_costs(
            "sell",
            notional,
            0.0,
            float(state["transfer_fee_sell_bps"]),
        )
        terminal_fixed_total += costs["total_event_cost_cny"]
    liquidation_root, liquidation_status = break_even_bisection(
        gross_final_nav,
        initial_aum,
        fixed_live_total + terminal_fixed_total,
        executed_notional + terminal_notional,
        **root_kwargs,
    )
    rows: list[dict[str, Any]] = []
    for scenario in COST_IDS:
        live_final = float(
            nav[nav["cost_scenario_id"].eq(scenario)]
            .sort_values("trade_date")
            .iloc[-1]["scenario_NAV"]
        )
        components = {
            "sell_commission_cny": 0.0,
            "sell_stamp_tax_cny": 0.0,
            "sell_transfer_fee_cny": 0.0,
            "sell_slippage_cny": 0.0,
        }
        for _, notional, state in terminal_items:
            costs = order_costs(
                "sell",
                notional,
                _scenario_slippage(scenario),
                float(state["transfer_fee_sell_bps"]),
                statutory_enabled=scenario != "GROSS",
                commission_enabled=scenario != "GROSS",
            )
            components["sell_commission_cny"] += costs["commission_cny"]
            components["sell_stamp_tax_cny"] += costs["stamp_tax_cny"]
            components["sell_transfer_fee_cny"] += costs["transfer_fee_cny"]
            components["sell_slippage_cny"] += costs["slippage_cny"]
        terminal_cost = float(sum(components.values()))
        adjusted = live_final - terminal_cost
        rows.append(
            {
                "policy_id": policy_id,
                "cost_scenario_id": scenario,
                "terminal_mark_date": terminal_date,
                "open_position_n": len(terminal_items),
                "open_position_weight": terminal_notional / live_final
                if live_final > 0
                else np.nan,
                "open_position_notional_cny": terminal_notional,
                **components,
                "total_shadow_cost_cny": terminal_cost,
                "live_final_NAV": live_final,
                "liquidation_adjusted_final_NAV": adjusted,
                "live_nav_compound_return": live_final / initial_aum - 1.0,
                "liquidation_adjusted_compound_return": adjusted / initial_aum - 1.0,
                "live_nav_break_even_slippage_bps": live_root,
                "live_nav_break_even_status": live_status,
                "liquidation_adjusted_break_even_slippage_bps": liquidation_root,
                "liquidation_adjusted_break_even_status": liquidation_status,
                "historical_support_claim_allowed": False,
                "deployment_authorized": False,
                "source_table_content_hash": stable_hash(
                    {
                        "policy_id": policy_id,
                        "scenario": scenario,
                        "terminal_notional": terminal_notional,
                        "live_final": live_final,
                    }
                ),
                "run_id": RUN_ID,
                "contract_version": CONTRACT_VERSION,
            }
        )
    return pd.DataFrame(rows).loc[:, TERMINAL_COLUMNS]


def build_turnover_cost_readout(
    simulation: Mapping[str, Any],
    monthly: pd.DataFrame,
    nav: pd.DataFrame,
    cost_frame: pd.DataFrame,
    terminal: pd.DataFrame,
) -> pd.DataFrame:
    policy_id = str(monthly["policy_id"].iloc[0])
    rows: list[dict[str, Any]] = []
    execution = simulation["execution"]
    for scenario in COST_IDS:
        subset = monthly[monthly["cost_scenario_id"].eq(scenario)]
        costs = cost_frame[cost_frame["cost_scenario_id"].eq(scenario)]
        terminal_row = terminal[terminal["cost_scenario_id"].eq(scenario)].iloc[0]
        nav_subset = nav[nav["cost_scenario_id"].eq(scenario)]
        rows.append(
            {
                "policy_id": policy_id,
                "cost_scenario_id": scenario,
                "mean_target_one_way_turnover": subset[
                    "target_one_way_turnover"
                ].mean(),
                "mean_attempted_one_way_turnover": subset[
                    "attempted_one_way_turnover"
                ].mean(),
                "mean_realized_one_way_turnover": subset[
                    "realized_one_way_turnover"
                ].mean(),
                "total_commission_cny": costs.get(
                    "commission_cny", pd.Series(dtype=float)
                ).sum(),
                "total_stamp_tax_cny": costs.get(
                    "stamp_tax_cny", pd.Series(dtype=float)
                ).sum(),
                "total_transfer_fee_cny": costs.get(
                    "transfer_fee_cny", pd.Series(dtype=float)
                ).sum(),
                "total_slippage_cny": costs.get(
                    "slippage_cny", pd.Series(dtype=float)
                ).sum(),
                "total_cost_return": subset[
                    [
                        "commission_return",
                        "stamp_tax_return",
                        "transfer_fee_return",
                        "slippage_return",
                    ]
                ]
                .sum(axis=1)
                .sum(),
                "maximum_shadow_cash_deficit_cny": nav_subset[
                    "shadow_cash_deficit_cny"
                ].max(),
                "shadow_self_financing": nav_subset["shadow_self_financing"].all(),
                "live_nav_break_even_slippage_bps": terminal_row[
                    "live_nav_break_even_slippage_bps"
                ],
                "live_nav_break_even_status": terminal_row[
                    "live_nav_break_even_status"
                ],
                "liquidation_adjusted_break_even_slippage_bps": terminal_row[
                    "liquidation_adjusted_break_even_slippage_bps"
                ],
                "liquidation_adjusted_break_even_status": terminal_row[
                    "liquidation_adjusted_break_even_status"
                ],
                "raw_qfq_mapping_warning_n": int(
                    execution.get("mapping_warning", pd.Series(dtype=bool)).sum()
                ),
                "max_relative_ratio_spread": execution.get(
                    "relative_ratio_spread", pd.Series(dtype=float)
                ).max(),
                "source_table_content_hash": stable_hash(
                    {
                        "policy": policy_id,
                        "scenario": scenario,
                        "monthly": len(subset),
                        "cost_rows": len(costs),
                    }
                ),
                "historical_support_claim_allowed": False,
                "deployment_authorized": False,
                "run_id": RUN_ID,
                "contract_version": CONTRACT_VERSION,
            }
        )
    return pd.DataFrame(rows).loc[:, TURNOVER_COST_COLUMNS]


def _scope_mask(frame: pd.DataFrame, scope: str) -> pd.Series:
    if scope == "all":
        return pd.Series(True, index=frame.index)
    if scope == "event_posthoc":
        return frame["event_month_posthoc"].astype(bool)
    if scope == "non_event_posthoc":
        return ~frame["event_month_posthoc"].astype(bool)
    raise ContractError(f"unknown month scope: {scope}")


def build_stop_readout(
    policy_id: str,
    stop_events: pd.DataFrame,
    monthly: pd.DataFrame,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    is_no_stop = "__STOPNONE" in policy_id
    for scope in ("all", "event_posthoc", "non_event_posthoc"):
        month_subset = monthly[_scope_mask(monthly, scope)]
        allowed_months = set(month_subset["label_month"])
        if len(stop_events):
            events = stop_events[
                pd.to_datetime(stop_events["trigger_date"])
                .dt.to_period("M")
                .astype(str)
                .isin(allowed_months)
            ]
        else:
            events = stop_events
        if is_no_stop:
            status = "not_applicable_no_stop"
            reason = "stop_threshold_none"
        elif len(events) == 0:
            status = "not_evaluable_no_trigger"
            reason = "no_stop_trigger"
        else:
            status = "evaluable"
            reason = ""
        filled = (
            events[events.get("fill_date", pd.Series(dtype=object)).notna()]
            if len(events)
            else events
        )
        evaluable = (
            events[
                events.get("attribution_evaluable", pd.Series(dtype=bool)).astype(bool)
            ]
            if len(events)
            else events
        )
        unique_month_n = month_subset["label_month"].nunique()
        stopped_capital = (
            float(
                (filled["shares_stopped"] * filled["basis_qfq"]).sum()
                / float(unique_month_n * 10_000_000.0)
            )
            if len(filled) and unique_month_n
            else 0.0
        )
        rows.append(
            {
                "policy_id": policy_id,
                "aggregation_scope": scope,
                "stop_trigger_n": len(events),
                "stop_fill_n": len(filled),
                "stop_blocked_n": int(events["fill_date"].isna().sum())
                if len(events)
                else 0,
                "mean_trigger_to_fill_delay_sessions": filled[
                    "trigger_to_fill_delay_sessions"
                ].mean()
                if len(filled)
                else np.nan,
                "mean_stop_overshoot": filled["stop_overshoot"].mean()
                if len(filled)
                else np.nan,
                "stopped_capital_weight": stopped_capital,
                "stop_exit_vs_hold_delta_cny": evaluable[
                    "stop_exit_vs_hold_delta_cny"
                ].sum(min_count=1)
                if len(evaluable)
                else np.nan,
                "stop_avoided_loss_cny": evaluable["stop_avoided_loss_cny"].sum(
                    min_count=1
                )
                if len(evaluable)
                else np.nan,
                "stop_missed_rebound_cny": evaluable["stop_missed_rebound_cny"].sum(
                    min_count=1
                )
                if len(evaluable)
                else np.nan,
                "stop_attribution_missing_n": int(
                    (~events["attribution_evaluable"].astype(bool)).sum()
                )
                if len(events)
                else 0,
                "source_table_content_hash": stable_hash(
                    {"policy": policy_id, "scope": scope, "event_n": len(events)}
                ),
                "ex_post_counterfactual_attribution_only": True,
                "status": status,
                "missing_reason": reason,
                "run_id": RUN_ID,
                "contract_version": CONTRACT_VERSION,
            }
        )
    return pd.DataFrame(rows).loc[:, STOP_READOUT_COLUMNS]


def build_event_slice_readout(monthly: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for (policy_id, scenario), group in monthly.groupby(
        ["policy_id", "cost_scenario_id"], sort=True
    ):
        for scope, event_flag in (
            ("event_posthoc", True),
            ("non_event_posthoc", False),
        ):
            subset = group[
                group["event_month_posthoc"].eq(event_flag) & group["month_evaluable"]
            ]
            values = subset["net_return"].to_numpy(dtype=float)
            rows.append(
                {
                    "policy_id": policy_id,
                    "cost_scenario_id": scenario,
                    "event_scope": scope,
                    "month_n": len(values),
                    "mean_monthly_return": np.mean(values) if len(values) else np.nan,
                    "median_monthly_return": np.median(values)
                    if len(values)
                    else np.nan,
                    "compound_return": np.prod(1.0 + values) - 1.0
                    if len(values)
                    else np.nan,
                    "positive_month_rate": np.mean(values > 0)
                    if len(values)
                    else np.nan,
                    "worst_month_return": np.min(values) if len(values) else np.nan,
                    "source_table_content_hash": stable_hash(
                        {"policy": policy_id, "scenario": scenario, "scope": scope}
                    ),
                    "posthoc_slice_only": True,
                    "parameter_selection_authorized": False,
                    "run_id": RUN_ID,
                    "contract_version": CONTRACT_VERSION,
                }
            )
    return pd.DataFrame(rows).loc[:, EVENT_SLICE_COLUMNS]


def _max_drawdown(values: Sequence[float]) -> float:
    array = np.asarray(values, dtype=float)
    array = array[np.isfinite(array)]
    if len(array) == 0:
        return np.nan
    peaks = np.maximum.accumulate(array)
    return float(np.min(array / peaks - 1.0))


def build_portfolio_summary(
    monthly: pd.DataFrame,
    daily_nav: pd.DataFrame,
    turnover_cost: pd.DataFrame,
    board: pd.DataFrame,
    stop_readout: pd.DataFrame,
    terminal: pd.DataFrame,
    maximum_single_weight: Mapping[tuple[str, str], float] | None = None,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for (policy_id, scenario), group in monthly.groupby(
        ["policy_id", "cost_scenario_id"], sort=True
    ):
        tc = turnover_cost[
            turnover_cost["policy_id"].eq(policy_id)
            & turnover_cost["cost_scenario_id"].eq(scenario)
        ].iloc[0]
        term = terminal[
            terminal["policy_id"].eq(policy_id)
            & terminal["cost_scenario_id"].eq(scenario)
        ].iloc[0]
        board_local = board[
            board["policy_id"].eq(policy_id) & board["cost_scenario_id"].eq(scenario)
        ]
        stop_all = stop_readout[
            stop_readout["policy_id"].eq(policy_id)
            & stop_readout["aggregation_scope"].eq("all")
        ].iloc[0]
        nav_local = daily_nav[
            daily_nav["policy_id"].eq(policy_id)
            & daily_nav["cost_scenario_id"].eq(scenario)
        ].sort_values("trade_date")
        for scope in ("all", "event_posthoc", "non_event_posthoc"):
            subset = group[_scope_mask(group, scope) & group["month_evaluable"]]
            scope_months = set(subset["label_month"].astype(str))
            scoped_nav = nav_local[
                nav_local["trade_date"].dt.to_period("M").astype(str).isin(scope_months)
            ]
            values = subset["net_return"].to_numpy(dtype=float)
            month_n = len(values)
            mean = float(np.mean(values)) if month_n else np.nan
            std = float(np.std(values, ddof=1)) if month_n > 1 else np.nan
            compound = float(np.prod(1.0 + values) - 1.0) if month_n else np.nan
            p10 = (
                float(np.quantile(values, 0.10, method="linear")) if month_n else np.nan
            )
            tail = values[values <= p10] if month_n else np.array([])
            board_label_month = (
                pd.to_datetime(board_local["decision_date"]).dt.to_period("M") + 1
            ).astype(str)
            board_scope_mask = board_label_month.isin(scope_months)
            target_board = board_local[
                board_local["concentration_scope"].eq("target") & board_scope_mask
            ]
            realized_board = board_local[
                board_local["concentration_scope"].eq("realized_posttrade")
                & board_scope_mask
            ]
            row = {metric: np.nan for metric in SUMMARY_METRICS}
            row.update(
                {
                    "policy_id": policy_id,
                    "cost_scenario_id": scenario,
                    "month_scope": scope,
                    "month_n": month_n,
                    "mean_monthly_return": mean,
                    "median_monthly_return": float(np.median(values))
                    if month_n
                    else np.nan,
                    "compound_return": compound,
                    "annualized_return": (1.0 + compound) ** (12.0 / month_n) - 1.0
                    if month_n and compound > -1.0
                    else np.nan,
                    "annualized_volatility": std * math.sqrt(12.0)
                    if np.isfinite(std)
                    else np.nan,
                    "zero_hurdle_sharpe": mean / std * math.sqrt(12.0)
                    if np.isfinite(std) and std > 0
                    else np.nan,
                    "positive_month_rate": float(np.mean(values > 0))
                    if month_n
                    else np.nan,
                    "worst_month_return": float(np.min(values)) if month_n else np.nan,
                    "empirical_p10_monthly_return": p10,
                    "ES10_loss": float(np.mean(tail)) if len(tail) else np.nan,
                    "max_drawdown_from_daily_NAV": _max_drawdown(
                        scoped_nav["scenario_NAV"]
                    ),
                    "event_month_mean_return": group.loc[
                        group["event_month_posthoc"] & group["month_evaluable"],
                        "net_return",
                    ].mean(),
                    "non_event_month_mean_return": group.loc[
                        ~group["event_month_posthoc"] & group["month_evaluable"],
                        "net_return",
                    ].mean(),
                    "mean_target_one_way_turnover": tc["mean_target_one_way_turnover"],
                    "mean_attempted_one_way_turnover": tc[
                        "mean_attempted_one_way_turnover"
                    ],
                    "mean_realized_one_way_turnover": tc[
                        "mean_realized_one_way_turnover"
                    ],
                    "total_commission_cny": tc["total_commission_cny"],
                    "total_stamp_tax_cny": tc["total_stamp_tax_cny"],
                    "total_transfer_fee_cny": tc["total_transfer_fee_cny"],
                    "total_slippage_cny": tc["total_slippage_cny"],
                    "total_cost_return": tc["total_cost_return"],
                    "live_nav_break_even_slippage_bps": tc[
                        "live_nav_break_even_slippage_bps"
                    ],
                    "liquidation_adjusted_break_even_slippage_bps": tc[
                        "liquidation_adjusted_break_even_slippage_bps"
                    ],
                    "mean_invested_weight": subset["invested_weight"].mean(),
                    "mean_cash_weight": subset["cash_weight"].mean(),
                    "mean_locked_capital_weight": subset[
                        "locked_capital_weight"
                    ].mean(),
                    "minimum_effective_holdings": subset["effective_holdings"].min(),
                    "maximum_single_instrument_weight": (
                        maximum_single_weight.get((policy_id, scenario), np.nan)
                        if maximum_single_weight is not None
                        else np.nan
                    ),
                    "terminal_open_position_weight": term["open_position_weight"],
                    "terminal_liquidation_cost_shadow_cny": term[
                        "total_shadow_cost_cny"
                    ],
                    "live_nav_compound_return": term["live_nav_compound_return"],
                    "liquidation_adjusted_compound_return": term[
                        "liquidation_adjusted_compound_return"
                    ],
                    "maximum_shadow_cash_deficit_cny": tc[
                        "maximum_shadow_cash_deficit_cny"
                    ],
                    "shadow_self_financing": tc["shadow_self_financing"],
                    "raw_qfq_mapping_warning_n": tc["raw_qfq_mapping_warning_n"],
                    "max_relative_ratio_spread": tc["max_relative_ratio_spread"],
                    "mean_target_board_HHI": target_board["board_HHI"].mean(),
                    "mean_realized_board_HHI": realized_board["board_HHI"].mean(),
                    "max_top1_board_weight": realized_board["top1_board_weight"].max(),
                    "max_top3_board_weight": realized_board["top3_board_weight"].max(),
                    "mean_target_no_board_position_weight": target_board[
                        "no_board_position_weight"
                    ].mean(),
                    "mean_realized_no_board_position_weight": realized_board[
                        "no_board_position_weight"
                    ].mean(),
                    "minimum_target_classified_board_coverage_ratio": target_board[
                        "classified_board_coverage_ratio"
                    ].min(),
                    "minimum_realized_classified_board_coverage_ratio": realized_board[
                        "classified_board_coverage_ratio"
                    ].min(),
                    "mean_stock_concentration_tilt_score": realized_board[
                        "mean_stock_concentration_tilt_score"
                    ].mean(),
                    "stop_trigger_n": stop_all["stop_trigger_n"],
                    "stop_fill_n": stop_all["stop_fill_n"],
                    "stop_blocked_n": stop_all["stop_blocked_n"],
                    "mean_trigger_to_fill_delay_sessions": stop_all[
                        "mean_trigger_to_fill_delay_sessions"
                    ],
                    "mean_stop_overshoot": stop_all["mean_stop_overshoot"],
                    "stopped_capital_weight": stop_all["stopped_capital_weight"],
                    "stop_exit_vs_hold_delta_cny": stop_all[
                        "stop_exit_vs_hold_delta_cny"
                    ],
                    "stop_avoided_loss_cny": stop_all["stop_avoided_loss_cny"],
                    "stop_missed_rebound_cny": stop_all["stop_missed_rebound_cny"],
                    "stop_attribution_missing_n": stop_all[
                        "stop_attribution_missing_n"
                    ],
                    "status": "evaluable" if month_n else "not_evaluable",
                    "missing_reason": "" if month_n else "no_evaluable_month",
                    "historical_support_claim_allowed": False,
                    "model_repair_claim_allowed": False,
                    "parameter_selection_authorized": False,
                    "deployment_authorized": False,
                    "run_id": RUN_ID,
                    "contract_version": CONTRACT_VERSION,
                }
            )
            rows.append(row)
    return pd.DataFrame(rows).loc[:, SUMMARY_COLUMNS]


STAGE_AUDIT_COLUMNS = [
    "stage_id",
    "check_id",
    "status",
    "expected",
    "observed",
    "affected_artifacts",
    "blocking_reason",
    "run_id",
    "contract_version",
]
DECISION_COLUMNS = [
    "run_id",
    "contract_version",
    "decision_state",
    "artifact_profile_id",
    "reached_stage",
    "upstream_integrity_gate",
    "arm_registry_gate",
    "board_formula_gate",
    "execution_contract_gate",
    "stop_path_gate",
    "cost_shadow_gate",
    "metric_completeness_gate",
    "determinism_gate",
    "seal_integrity_gate",
    "execution_path_n",
    "economic_series_n",
    "decision_month_n",
    "sector_weighting_semantics",
    "board_reference_universe_dependency",
    "market_trading_crowding_claim_allowed",
    "historical_PIT_sector_claim_allowed",
    "historical_support_claim_allowed",
    "model_repair_claim_allowed",
    "parameter_selection_authorized",
    "deployment_authorized",
    "blocking_reason",
]
DETERMINISM_COLUMNS = [
    "artifact_path",
    "replay_a_sha256",
    "replay_b_sha256",
    "hash_match",
    "run_id",
    "contract_version",
]
CORE_PATHS = [
    "preflight/resolved_config.yaml",
    "preflight/policy_arm_registry.csv",
    "preflight/cost_scenario_registry.csv",
    "preflight/paired_comparison_registry.csv",
    "preflight/retained_board_registry.csv",
    "materialized/monthly_target_weights.parquet",
    "materialized/board_overrepresentation_monthly.csv.gz",
    "materialized/daily_execution_ledger.parquet",
    "materialized/daily_nav.parquet",
    "materialized/stop_event_ledger.csv.gz",
    "materialized/cost_shadow_ledger.parquet",
    "historical/monthly_portfolio_returns.csv.gz",
    "historical/portfolio_summary.csv",
    "historical/paired_sensitivity_delta.csv",
    "historical/block_bootstrap_readout.csv",
    "historical/turnover_cost_readout.csv",
    "historical/board_concentration_readout.csv",
    "historical/stoploss_attribution_readout.csv",
    "historical/terminal_liquidation_shadow.csv",
    DECISION_NAME,
]


def resolved_config_payload(config: Mapping[str, Any]) -> dict[str, Any]:
    """Return the closed config with deterministic group and inner-key ordering."""
    return {
        section: {
            key: config[section][key] for key in sorted(EXPECTED_SECTION_KEYS[section])
        }
        for section in EXPECTED_SECTION_KEYS
    }


def contract_snapshot(
    config: Mapping[str, Any],
    config_path: Path,
    resolved_config_path: Path,
) -> dict[str, Any]:
    authority = config["authorization"]
    replay_authorized = bool(
        authority["historical_outcome_execution_authorized"]
        and authority["portfolio_replay_authorized"]
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "run_id": RUN_ID,
        "contract_version": CONTRACT_VERSION,
        "requirement_sha256": sha256_file(resolved_paths(config)["requirement_file"]),
        "config_sha256": sha256_file(config_path),
        "resolved_config_sha256": sha256_file(resolved_config_path),
        "execution_authority": (
            "historical_portfolio_replay_authorized"
            if replay_authorized
            else "implementation_only_execution_not_authorized"
        ),
        "implementation_authorized": bool(authority["implementation_authorized"]),
        "historical_outcome_execution_authorized": bool(
            authority["historical_outcome_execution_authorized"]
        ),
        "portfolio_replay_authorized": bool(authority["portfolio_replay_authorized"]),
        "frozen_upstream_hashes": dict(config["upstream_hashes"]),
        "sector_weighting_semantics": "bucket_overrepresentation_sector_concentration_tilt",
        "board_reference_universe_dependency": config["board_concentration"][
            "reference_universe_dependency"
        ],
        "claim_flags": {
            "market_trading_crowding_claim_allowed": False,
            "historical_PIT_sector_claim_allowed": False,
            "historical_support_claim_allowed": False,
            "model_repair_claim_allowed": False,
            "parameter_selection_authorized": False,
            "deployment_authorized": False,
        },
    }


def stage_result_row(result: StageResult) -> dict[str, Any]:
    return {
        "stage_id": result.stage_id,
        "check_id": result.check_id,
        "status": "pass" if result.gate else "fail",
        "expected": result.expected,
        "observed": result.observed,
        "affected_artifacts": result.affected_artifacts,
        "blocking_reason": result.blocking_reason,
        "run_id": RUN_ID,
        "contract_version": CONTRACT_VERSION,
    }


def pass_result(
    stage_id: str,
    check_id: str,
    expected: str,
    observed: str,
    affected: str,
) -> StageResult:
    return StageResult(True, stage_id, check_id, expected, observed, affected, "")


def fail_result(
    stage_id: str,
    check_id: str,
    expected: str,
    observed: str,
    affected: str,
    reason: str,
) -> StageResult:
    return StageResult(False, stage_id, check_id, expected, observed, affected, reason)


def validate_stable_frame(
    frame: pd.DataFrame,
    *,
    columns: Sequence[str],
    keys: Sequence[str],
    expected_rows: int | None = None,
    name: str,
) -> None:
    if list(frame.columns) != list(columns):
        raise ContractError(f"{name} closed schema mismatch")
    if frame.duplicated(list(keys)).any():
        raise ContractError(f"{name} stable-key duplicate")
    if expected_rows is not None and len(frame) != expected_rows:
        raise ContractError(
            f"{name} cardinality mismatch: expected={expected_rows}, observed={len(frame)}"
        )


def decision_frame(
    profile_id: str,
    reached_stage: str,
    blocking_reason: str = "",
) -> pd.DataFrame:
    order = {
        "P0_PREFLIGHT_BLOCKED": 0,
        "P1_BOARD_BLOCKED": 1,
        "P2_EXECUTION_BLOCKED": 2,
        "P3_METRIC_BLOCKED": 3,
        "P4_DETERMINISM_BLOCKED": 4,
        "P5_SENSITIVITY_MATERIALIZED": 5,
    }
    level = order[profile_id]
    states = {
        "P0_PREFLIGHT_BLOCKED": "20B_P4_PORTSENS_preflight_blocked",
        "P1_BOARD_BLOCKED": "20B_P4_PORTSENS_board_formula_blocked",
        "P2_EXECUTION_BLOCKED": "20B_P4_PORTSENS_execution_materialization_blocked",
        "P3_METRIC_BLOCKED": "20B_P4_PORTSENS_metric_materialization_blocked",
        "P4_DETERMINISM_BLOCKED": "20B_P4_PORTSENS_determinism_blocked",
        "P5_SENSITIVITY_MATERIALIZED": "20B_P4_PORTSENS_sensitivity_materialized",
    }
    row = {
        "run_id": RUN_ID,
        "contract_version": CONTRACT_VERSION,
        "decision_state": states[profile_id],
        "artifact_profile_id": profile_id,
        "reached_stage": reached_stage,
        "upstream_integrity_gate": level >= 1,
        "arm_registry_gate": level >= 1,
        "board_formula_gate": level >= 2,
        "execution_contract_gate": level >= 3,
        "stop_path_gate": level >= 3,
        "cost_shadow_gate": level >= 3,
        "metric_completeness_gate": level >= 4,
        "determinism_gate": level >= 5,
        "seal_integrity_gate": True,
        "execution_path_n": 90,
        "economic_series_n": 540,
        "decision_month_n": 21,
        "sector_weighting_semantics": "bucket_overrepresentation_sector_concentration_tilt",
        "board_reference_universe_dependency": (
            "retrospective_full_sample_universe_dependency"
        ),
        "market_trading_crowding_claim_allowed": False,
        "historical_PIT_sector_claim_allowed": False,
        "historical_support_claim_allowed": False,
        "model_repair_claim_allowed": False,
        "parameter_selection_authorized": False,
        "deployment_authorized": False,
        "blocking_reason": blocking_reason,
    }
    return pd.DataFrame([row]).loc[:, DECISION_COLUMNS]


def _report_number(value: Any, *, percent: bool = False) -> str:
    numeric = pd.to_numeric(value, errors="coerce")
    if not np.isfinite(numeric):
        return "NA"
    return f"{numeric:.2%}" if percent else f"{numeric:.4f}"


def report_text(
    profile_id: str,
    blocking_reason: str = "",
    source_root: Path | None = None,
) -> str:
    materialized = profile_id == "P5_SENSITIVITY_MATERIALIZED"
    state = "已完整物化" if materialized else f"未完整物化（{blocking_reason}）"
    result_section = ""
    if materialized:
        if source_root is None:
            raise ContractError("materialized report requires a source root")
        summary = pd.read_csv(source_root / "historical/portfolio_summary.csv")
        summary = summary[summary["month_scope"].eq("all")].set_index(
            ["policy_id", "cost_scenario_id"]
        )

        def row(
            model: str, bucket: int, lam: float, stop: float | None, cost: str
        ) -> pd.Series:
            return summary.loc[(make_policy_id(model, bucket, lam, stop), cost)]

        bucket_lines = []
        for bucket in BUCKET_IDS:
            item = row("S0_SELECTED_FULL", bucket, 0.0, None, "SLIP005")
            bucket_lines.append(
                f"| D{bucket} | {_report_number(item['compound_return'], percent=True)} | "
                f"{_report_number(item['mean_monthly_return'], percent=True)} | "
                f"{_report_number(item['max_drawdown_from_daily_NAV'], percent=True)} | "
                f"{_report_number(item['mean_realized_one_way_turnover'], percent=True)} |"
            )
        sector_lines = []
        for lam in LAMBDA_GRID:
            item = row("S0_SELECTED_FULL", 10, lam, None, "SLIP005")
            sector_lines.append(
                f"| {lam:g} | {_report_number(item['compound_return'], percent=True)} | "
                f"{_report_number(item['mean_realized_board_HHI'])} | "
                f"{_report_number(item['max_top1_board_weight'], percent=True)} |"
            )
        cost_lines = []
        for cost in COST_IDS:
            item = row("S0_SELECTED_FULL", 10, 0.0, None, cost)
            cost_lines.append(
                f"| {cost} | {_report_number(item['compound_return'], percent=True)} | "
                f"{_report_number(item['total_cost_return'], percent=True)} | "
                f"{_report_number(item['maximum_shadow_cash_deficit_cny'])} |"
            )
        stop_lines = []
        for stop in STOP_GRID:
            item = row("S0_SELECTED_FULL", 10, 0.0, stop, "SLIP005")
            label = "none" if stop is None else f"{stop:.0%}"
            stop_lines.append(
                f"| {label} | {_report_number(item['compound_return'], percent=True)} | "
                f"{int(item['stop_fill_n'])} | "
                f"{_report_number(item['stop_exit_vs_hold_delta_cny'])} |"
            )
        result_section = (
            """
## 已物化结果：四个问题

### 1. D8 / D9 / D10（S0、lambda=0、无止损、SLIP005）

| 单桶 | 复合收益 | 月均收益 | 日 NAV 最大回撤 | 月均实际单边换手 |
|---|---:|---:|---:|---:|
"""
            + "\n".join(bucket_lines)
            + """

### 2. 板块集中度（S0、D10、无止损、SLIP005）

| lambda | 复合收益 | 实际板块 HHI 均值 | 最大 Top1 板块权重 |
|---:|---:|---:|---:|
"""
            + "\n".join(sector_lines)
            + """

### 3. 成本 shadow（S0、D10、lambda=0、无止损）

| 成本情景 | 复合收益 | 累计成本收益占比 | 最大 shadow 现金缺口（元） |
|---|---:|---:|---:|
"""
            + "\n".join(cost_lines)
            + """

### 4. 硬止损（S0、D10、lambda=0、SLIP005）

| 止损阈值 | 复合收益 | stop fills | stop 相对持有反事实差额（元） |
|---|---:|---:|---:|
"""
            + "\n".join(stop_lines)
            + "\n"
        )
    return f"""# 20B-P4 D8/D9/D10 板块集中度、成本与止损敏感性报告

## 结论边界

本次组合敏感性诊断{state}。它只回答固定 S0/B0、D8/D9/D10 路径的描述性敏感性，不能据此选择参数、修复模型或部署策略。

## 四个问题

1. **交易成本敏感性**：固定同一成交股数与价格路径，对 GROSS、0、5、10、20、40 bps 单边滑点成本 shadow 逐一核算；成本 shadow 不反向改变成交路径。
2. **板块集中度敏感性**：lambda=0、0.5、1 只放大目标 bucket 相对全 universe 的静态概念板块 overrepresentation；这不是市场交易拥挤度。全样本板块字典依赖明确标记为 `retrospective_full_sample_universe_dependency`。
3. **D8/D9/D10**：三者是互斥单桶持仓路径，不是 D8-D10 累计组合；S0 与 B0 同月同股票 population 配对。
4. **硬止损敏感性**：比较 none、5%、10%、15%、20%，使用 qfq-linked basis、gap-first/intraday-low daily-bar proxy、跌停/停牌延迟退出和下次调仓前禁止再入场。

## 必须披露

- 样本为 21 个 robustness decision months；事件月仅作 post-hoc 描述。
- 板块来源是静态 2025 snapshot，非历史 PIT；`__NO_BOARD__` 固定中性 0.5，且不进入板块排名、HHI 或 Top exposure。
- 止损成交是 daily-bar proxy，不等于真实逐笔可成交性。
- 上游 S0 仍处于机器 gate blocked 状态；本诊断不产生 historical support、model repair、parameter selection 或 deployment 标签。

## 网格

完整网格为 2 models × 3 buckets × 3 lambdas × 5 stops = 90 execution paths；每条路径含 6 个成本情景，共 540 条经济序列。OFAT comparison registry 固定 284 行。
{result_section}"""


def core_hashes(root: Path) -> dict[str, str]:
    missing = [relative for relative in CORE_PATHS if not (root / relative).is_file()]
    if missing:
        raise ContractError(f"core determinism files missing: {missing}")
    return {relative: sha256_file(root / relative) for relative in CORE_PATHS}


def maximum_single_weights(
    simulations: Mapping[str, Mapping[str, Any]],
    nav: pd.DataFrame,
) -> dict[tuple[str, str], float]:
    result: dict[tuple[str, str], float] = {}
    liability = nav.set_index(["policy_id", "cost_scenario_id", "trade_date"])[
        "scenario_cost_liability"
    ]
    for policy_id, simulation in simulations.items():
        for scenario in COST_IDS:
            maximum = 0.0
            for snapshot in simulation["snapshots"]:
                trade_date = pd.Timestamp(snapshot["trade_date"])
                cost = float(liability.get((policy_id, scenario, trade_date), 0.0))
                gross_nav = float(snapshot["reference_nav_posttrade"]) + float(
                    snapshot["reference_cost_cumulative"]
                )
                scenario_nav = gross_nav - cost
                if scenario_nav > 0 and snapshot["position_values"]:
                    maximum = max(
                        maximum,
                        max(snapshot["position_values"].values()) / scenario_nav,
                    )
            result[(policy_id, scenario)] = float(maximum)
    return result


def _write_replay_prelude(
    scratch: Path,
    config: Mapping[str, Any],
    config_path: Path,
) -> None:
    resolved = scratch / "preflight/resolved_config.yaml"
    write_yaml(resolved, resolved_config_payload(config))
    write_json(
        scratch / "preflight/contract_snapshot.json",
        contract_snapshot(config, config_path, resolved),
    )


def _raise_stage(
    error: Exception,
    *,
    profile_id: str,
    reached_stage: str,
    stage_id: str,
    check_id: str,
    affected: str,
    results: list[StageResult],
    scratch: Path,
) -> None:
    reason = f"{type(error).__name__}: {error}"
    results.append(fail_result(stage_id, check_id, "pass", "fail", affected, reason))
    raise ReplayStageError(
        reason,
        profile_id=profile_id,
        reached_stage=reached_stage,
        stage_results=results,
        scratch_root=scratch,
    ) from error


def materialize_replay(
    config: Mapping[str, Any],
    config_path: Path,
    scratch: Path,
) -> list[StageResult]:
    """Materialize one independent historical replay into an unpublished root."""
    if scratch.exists():
        raise ContractError(f"replay scratch root already exists: {scratch}")
    scratch.mkdir(parents=True)
    _write_replay_prelude(scratch, config, config_path)
    results: list[StageResult] = []

    try:
        input_audit, assignment = run_preflight(config)
        policies = build_policy_arm_registry()
        costs = build_cost_scenario_registry()
        comparisons = build_paired_comparison_registry()
        validate_stable_frame(
            policies,
            columns=POLICY_COLUMNS,
            keys=["policy_id"],
            expected_rows=90,
            name="policy_arm_registry",
        )
        validate_stable_frame(
            costs,
            columns=COST_COLUMNS,
            keys=["cost_scenario_id"],
            expected_rows=6,
            name="cost_scenario_registry",
        )
        validate_stable_frame(
            comparisons,
            columns=COMPARISON_COLUMNS,
            keys=["comparison_id"],
            expected_rows=284,
            name="paired_comparison_registry",
        )
        write_csv(
            scratch / "preflight/input_integrity_audit.csv",
            input_audit,
            INPUT_AUDIT_COLUMNS,
        )
        write_csv(
            scratch / "preflight/policy_arm_registry.csv", policies, POLICY_COLUMNS
        )
        write_csv(scratch / "preflight/cost_scenario_registry.csv", costs, COST_COLUMNS)
        write_csv(
            scratch / "preflight/paired_comparison_registry.csv",
            comparisons,
            COMPARISON_COLUMNS,
        )
        results.append(
            pass_result(
                "S0_PREFLIGHT",
                "upstream_and_arm_registry",
                "16 hashes; 90 arms; 6 costs; 284 comparisons",
                f"{len(input_audit)} hashes; {len(policies)} arms; {len(costs)} costs; {len(comparisons)} comparisons",
                "G0_FINAL_AUDIT,G1_BASE_REGISTRIES",
            )
        )
    except Exception as error:
        _raise_stage(
            error,
            profile_id="P0_PREFLIGHT_BLOCKED",
            reached_stage="preflight",
            stage_id="S0_PREFLIGHT",
            check_id="upstream_and_arm_registry",
            affected="G0_FINAL_AUDIT,G1_BASE_REGISTRIES",
            results=results,
            scratch=scratch,
        )

    try:
        paths = resolved_paths(config)
        reference_universe = sorted(
            set(assignment["instrument_id"].map(normalize_instrument))
        )
        board_members = pd.read_csv(paths["BOARD_MEMBER"])
        board_registry, membership, board_audit = build_board_dictionary(
            reference_universe,
            board_members,
            int(config["board_concentration"]["minimum_reference_member_n"]),
        )
        board_audit.loc[:, "source_path"] = (
            paths["BOARD_MEMBER"].relative_to(REPO_ROOT).as_posix()
        )
        board_audit.loc[:, "source_sha256"] = sha256_file(paths["BOARD_MEMBER"])
        overrepresentation, scores = compute_overrepresentation(assignment, membership)
        targets = build_target_weights(
            assignment,
            scores,
            config["upstream_hashes"]["BUCKET_ASSIGNMENT_sha256"],
            config["upstream_hashes"]["BOARD_MEMBER_sha256"],
            float(config["board_concentration"]["single_instrument_weight_cap"]),
        )
        validate_stable_frame(
            targets,
            columns=TARGET_COLUMNS,
            keys=["policy_id", "decision_date", "instrument_id"],
            name="monthly_target_weights",
        )
        validate_stable_frame(
            overrepresentation.loc[:, BOARD_OVERREP_COLUMNS],
            columns=BOARD_OVERREP_COLUMNS,
            keys=["scored_model_id", "decision_date", "bucket_id", "retained_board_id"],
            name="board_overrepresentation_monthly",
        )
        write_csv(
            scratch / "preflight/board_membership_audit.csv",
            board_audit.loc[:, BOARD_AUDIT_COLUMNS],
            BOARD_AUDIT_COLUMNS,
        )
        write_csv(
            scratch / "preflight/retained_board_registry.csv",
            board_registry.loc[:, BOARD_REGISTRY_COLUMNS],
            BOARD_REGISTRY_COLUMNS,
        )
        write_parquet(
            scratch / "materialized/monthly_target_weights.parquet",
            targets,
            TARGET_COLUMNS,
        )
        write_csv(
            scratch / "materialized/board_overrepresentation_monthly.csv.gz",
            overrepresentation.loc[:, BOARD_OVERREP_COLUMNS],
            BOARD_OVERREP_COLUMNS,
        )
        results.append(
            pass_result(
                "S1_BOARD",
                "retrospective_board_dictionary_and_targets",
                "fixed dictionary; 90 paths; weights sum one; cap <= 10%",
                f"retained={int(board_registry['retained'].sum())}; paths={targets['policy_id'].nunique()}",
                "G2_BOARD_TARGETS",
            )
        )
    except Exception as error:
        for relative in config["output_contract"]["artifact_groups"][
            "G2_BOARD_TARGETS"
        ]:
            (scratch / relative).unlink(missing_ok=True)
        _raise_stage(
            error,
            profile_id="P1_BOARD_BLOCKED",
            reached_stage="board",
            stage_id="S1_BOARD",
            check_id="retrospective_board_dictionary_and_targets",
            affected="G2_BOARD_TARGETS",
            results=results,
            scratch=scratch,
        )

    try:
        calendar = load_trading_calendar(config)
        instruments = set(targets["instrument_id"])
        status = load_status_panel(config, instruments, calendar)
        market = load_market_panel(config, instruments, calendar)
        context = build_execution_context(config, instruments, calendar, status)
        simulations: dict[str, Mapping[str, Any]] = {}
        execution_parts: list[pd.DataFrame] = []
        cost_parts: list[pd.DataFrame] = []
        nav_parts: list[pd.DataFrame] = []
        stop_parts: list[pd.DataFrame] = []
        policy_lookup = policies.set_index("policy_id")
        for policy_id, policy_targets in targets.groupby("policy_id", sort=True):
            simulation = simulate_policy(
                {
                    "policy_id": policy_id,
                    **policy_lookup.loc[policy_id].to_dict(),
                },
                policy_targets,
                calendar,
                market,
                context,
                config,
            )
            cost_shadow, daily_nav = build_cost_shadows(simulation, config)
            simulations[str(policy_id)] = simulation
            execution_parts.append(simulation["execution"].loc[:, EXECUTION_COLUMNS])
            cost_parts.append(cost_shadow)
            nav_parts.append(daily_nav)
            stop_parts.append(simulation["stop_events"].loc[:, STOP_EVENT_COLUMNS])
        execution_concat_parts = [
            part.dropna(axis=1, how="all")
            for part in execution_parts
            if not part.empty
        ]
        execution_all = (
            pd.concat(execution_concat_parts, ignore_index=True)
            .reindex(columns=EXECUTION_COLUMNS)
            .sort_values(
                ["policy_id", "trade_date", "event_sequence", "instrument_id"]
            )
        )
        cost_all = pd.concat(cost_parts, ignore_index=True).sort_values(
            [
                "policy_id",
                "cost_scenario_id",
                "trade_date",
                "event_sequence",
                "instrument_id",
            ]
        )
        nav_all = pd.concat(nav_parts, ignore_index=True).sort_values(
            ["policy_id", "cost_scenario_id", "trade_date"]
        )
        stop_concat_parts = [
            part.dropna(axis=1, how="all") for part in stop_parts if not part.empty
        ]
        stop_all = (
            pd.concat(stop_concat_parts, ignore_index=True)
            .reindex(columns=STOP_EVENT_COLUMNS)
            .sort_values(["policy_id", "holding_spell_id", "stop_event_id"])
        )
        validate_stable_frame(
            execution_all,
            columns=EXECUTION_COLUMNS,
            keys=["policy_id", "trade_date", "event_sequence", "instrument_id"],
            name="daily_execution_ledger",
        )
        validate_stable_frame(
            nav_all,
            columns=DAILY_NAV_COLUMNS,
            keys=["policy_id", "cost_scenario_id", "trade_date"],
            expected_rows=90 * 6 * 423,
            name="daily_nav",
        )
        validate_stable_frame(
            cost_all,
            columns=COST_SHADOW_COLUMNS,
            keys=[
                "policy_id",
                "cost_scenario_id",
                "trade_date",
                "event_sequence",
                "instrument_id",
            ],
            expected_rows=6
            * len(execution_all[execution_all["fill_status"].eq("filled")]),
            name="cost_shadow_ledger",
        )
        validate_stable_frame(
            stop_all,
            columns=STOP_EVENT_COLUMNS,
            keys=["policy_id", "holding_spell_id", "stop_event_id"],
            name="stop_event_ledger",
        )
        write_parquet(
            scratch / "materialized/daily_execution_ledger.parquet",
            execution_all,
            EXECUTION_COLUMNS,
        )
        write_parquet(
            scratch / "materialized/daily_nav.parquet", nav_all, DAILY_NAV_COLUMNS
        )
        write_csv(
            scratch / "materialized/stop_event_ledger.csv.gz",
            stop_all,
            STOP_EVENT_COLUMNS,
        )
        write_parquet(
            scratch / "materialized/cost_shadow_ledger.parquet",
            cost_all,
            COST_SHADOW_COLUMNS,
        )
        results.append(
            pass_result(
                "S2_EXECUTION",
                "stateful_execution_stop_and_cost_shadow",
                "90 paths; 540 daily NAV series; fixed reference fills",
                f"paths={len(simulations)}; nav_rows={len(nav_all)}; fills={len(cost_all) // 6}",
                "G3_LEDGERS",
            )
        )
    except Exception as error:
        for relative in config["output_contract"]["artifact_groups"]["G3_LEDGERS"]:
            (scratch / relative).unlink(missing_ok=True)
        _raise_stage(
            error,
            profile_id="P2_EXECUTION_BLOCKED",
            reached_stage="execution",
            stage_id="S2_EXECUTION",
            check_id="stateful_execution_stop_and_cost_shadow",
            affected="G3_LEDGERS",
            results=results,
            scratch=scratch,
        )

    try:
        monthly_parts: list[pd.DataFrame] = []
        board_parts: list[pd.DataFrame] = []
        terminal_parts: list[pd.DataFrame] = []
        turnover_parts: list[pd.DataFrame] = []
        stop_readout_parts: list[pd.DataFrame] = []
        for policy_id, policy_targets in targets.groupby("policy_id", sort=True):
            simulation = simulations[str(policy_id)]
            policy_nav = nav_all[nav_all["policy_id"].eq(policy_id)]
            policy_cost = cost_all[cost_all["policy_id"].eq(policy_id)]
            board_readout = build_board_concentration_readout(
                simulation, policy_nav, policy_targets, membership
            )
            monthly = build_monthly_returns(
                simulation,
                policy_nav,
                policy_cost,
                policy_targets,
                board_readout,
                config,
            )
            terminal = build_terminal_readout(
                simulation, policy_nav, policy_cost, market, context, config
            )
            turnover = build_turnover_cost_readout(
                simulation, monthly, policy_nav, policy_cost, terminal
            )
            stop_readout = build_stop_readout(
                str(policy_id), simulation["stop_events"], monthly
            )
            monthly_parts.append(monthly)
            board_parts.append(board_readout)
            terminal_parts.append(terminal)
            turnover_parts.append(turnover)
            stop_readout_parts.append(stop_readout)
        monthly_all = pd.concat(monthly_parts, ignore_index=True).sort_values(
            ["policy_id", "cost_scenario_id", "decision_date"]
        )
        board_all = pd.concat(board_parts, ignore_index=True).sort_values(
            ["policy_id", "cost_scenario_id", "decision_date", "concentration_scope"]
        )
        terminal_all = pd.concat(terminal_parts, ignore_index=True).sort_values(
            ["policy_id", "cost_scenario_id"]
        )
        turnover_all = pd.concat(turnover_parts, ignore_index=True).sort_values(
            ["policy_id", "cost_scenario_id"]
        )
        stop_readout_all = pd.concat(stop_readout_parts, ignore_index=True).sort_values(
            ["policy_id", "aggregation_scope"]
        )
        paired, bootstrap = build_paired_outputs(monthly_all, comparisons, config)
        event_readout = build_event_slice_readout(monthly_all)
        summary = build_portfolio_summary(
            monthly_all,
            nav_all,
            turnover_all,
            board_all,
            stop_readout_all,
            terminal_all,
            maximum_single_weights(simulations, nav_all),
        )
        checks = [
            (
                monthly_all,
                MONTHLY_COLUMNS,
                ["policy_id", "cost_scenario_id", "decision_date"],
                11_340,
                "monthly_portfolio_returns",
            ),
            (
                summary,
                SUMMARY_COLUMNS,
                ["policy_id", "cost_scenario_id", "month_scope"],
                1_620,
                "portfolio_summary",
            ),
            (
                paired,
                PAIRED_DELTA_COLUMNS,
                ["comparison_id", "decision_date"],
                5_964,
                "paired_sensitivity_delta",
            ),
            (
                bootstrap,
                BOOTSTRAP_COLUMNS,
                ["comparison_id", "month_scope"],
                284,
                "block_bootstrap_readout",
            ),
            (
                turnover_all,
                TURNOVER_COST_COLUMNS,
                ["policy_id", "cost_scenario_id"],
                540,
                "turnover_cost_readout",
            ),
            (
                board_all,
                BOARD_CONCENTRATION_COLUMNS,
                [
                    "policy_id",
                    "cost_scenario_id",
                    "decision_date",
                    "concentration_scope",
                ],
                22_680,
                "board_concentration_readout",
            ),
            (
                stop_readout_all,
                STOP_READOUT_COLUMNS,
                ["policy_id", "aggregation_scope"],
                270,
                "stoploss_attribution_readout",
            ),
            (
                event_readout,
                EVENT_SLICE_COLUMNS,
                ["policy_id", "cost_scenario_id", "event_scope"],
                1_080,
                "event_regime_slice_readout",
            ),
            (
                terminal_all,
                TERMINAL_COLUMNS,
                ["policy_id", "cost_scenario_id"],
                540,
                "terminal_liquidation_shadow",
            ),
        ]
        for frame, columns, keys, rows, name in checks:
            validate_stable_frame(
                frame,
                columns=columns,
                keys=keys,
                expected_rows=rows,
                name=name,
            )
        write_csv(
            scratch / "historical/monthly_portfolio_returns.csv.gz",
            monthly_all,
            MONTHLY_COLUMNS,
        )
        write_csv(
            scratch / "historical/portfolio_summary.csv", summary, SUMMARY_COLUMNS
        )
        write_csv(
            scratch / "historical/paired_sensitivity_delta.csv",
            paired,
            PAIRED_DELTA_COLUMNS,
        )
        write_csv(
            scratch / "historical/block_bootstrap_readout.csv",
            bootstrap,
            BOOTSTRAP_COLUMNS,
        )
        write_csv(
            scratch / "historical/turnover_cost_readout.csv",
            turnover_all,
            TURNOVER_COST_COLUMNS,
        )
        write_csv(
            scratch / "historical/board_concentration_readout.csv",
            board_all,
            BOARD_CONCENTRATION_COLUMNS,
        )
        write_csv(
            scratch / "historical/stoploss_attribution_readout.csv",
            stop_readout_all,
            STOP_READOUT_COLUMNS,
        )
        write_csv(
            scratch / "historical/event_regime_slice_readout.csv",
            event_readout,
            EVENT_SLICE_COLUMNS,
        )
        write_csv(
            scratch / "historical/terminal_liquidation_shadow.csv",
            terminal_all,
            TERMINAL_COLUMNS,
        )
        results.append(
            pass_result(
                "S3_METRICS",
                "closed_schema_and_cardinality",
                "11340 monthly; 1620 summary; 5964 paired; 284 bootstrap",
                f"{len(monthly_all)} monthly; {len(summary)} summary; {len(paired)} paired; {len(bootstrap)} bootstrap",
                "G4_METRICS",
            )
        )
    except Exception as error:
        for relative in config["output_contract"]["artifact_groups"]["G4_METRICS"]:
            (scratch / relative).unlink(missing_ok=True)
        _raise_stage(
            error,
            profile_id="P3_METRIC_BLOCKED",
            reached_stage="metrics",
            stage_id="S3_METRICS",
            check_id="closed_schema_and_cardinality",
            affected="G4_METRICS",
            results=results,
            scratch=scratch,
        )

    write_csv(
        scratch / DECISION_NAME,
        decision_frame("P5_SENSITIVITY_MATERIALIZED", "metrics"),
        DECISION_COLUMNS,
    )
    return results


def _copy_profile_payload(
    source: Path,
    destination: Path,
    config: Mapping[str, Any],
    profile_id: str,
) -> None:
    generated = {
        "stage_failure_audit.csv",
        REPORT_NAME,
        MANIFEST_NAME,
        HASHES_NAME,
        "determinism/determinism_comparison.csv",
        "determinism/replay_b_core_hashes.json",
        DECISION_NAME,
    }
    for relative in sorted(profile_file_set(config, profile_id) - generated):
        target = destination / relative
        source_path = source / relative
        if not source_path.is_file():
            if relative == "preflight/input_integrity_audit.csv":
                write_csv(
                    target,
                    pd.DataFrame(columns=INPUT_AUDIT_COLUMNS),
                    INPUT_AUDIT_COLUMNS,
                )
                continue
            raise ContractError(f"completed-profile source missing: {relative}")
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source_path, target)


def publish_profile(
    *,
    source: Path,
    output_root: Path,
    config: Mapping[str, Any],
    profile_id: str,
    reached_stage: str,
    results: Sequence[StageResult],
    blocking_reason: str = "",
    determinism: pd.DataFrame | None = None,
    replay_b_hashes: Mapping[str, str] | None = None,
) -> str:
    build = output_root.with_name(output_root.name + ".building")
    if output_root.exists() or build.exists():
        raise SealError("output root or .building already exists")
    build.mkdir(parents=True)
    try:
        _copy_profile_payload(source, build, config, profile_id)
        if profile_id in {"P4_DETERMINISM_BLOCKED", "P5_SENSITIVITY_MATERIALIZED"}:
            if determinism is None or replay_b_hashes is None:
                raise ContractError("determinism profile lacks G5 payload")
            write_csv(
                build / "determinism/determinism_comparison.csv",
                determinism,
                DETERMINISM_COLUMNS,
            )
            write_json(
                build / "determinism/replay_b_core_hashes.json",
                dict(replay_b_hashes),
            )
        write_csv(
            build / "stage_failure_audit.csv",
            pd.DataFrame(
                [stage_result_row(item) for item in results],
                columns=STAGE_AUDIT_COLUMNS,
            ),
            STAGE_AUDIT_COLUMNS,
        )
        write_csv(
            build / DECISION_NAME,
            decision_frame(profile_id, reached_stage, blocking_reason),
            DECISION_COLUMNS,
        )
        report_path = build / REPORT_NAME
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(
            report_text(profile_id, blocking_reason, source),
            encoding="utf-8",
            newline="\n",
        )
        return seal_candidate(
            build,
            output_root,
            config,
            profile_id,
            decision_frame(profile_id, reached_stage).iloc[0]["decision_state"],
            reached_stage,
        )
    except Exception:
        shutil.rmtree(build, ignore_errors=True)
        raise


def compare_replays(
    replay_a: Path,
    replay_b: Path,
) -> tuple[pd.DataFrame, dict[str, str], bool]:
    a_hashes = core_hashes(replay_a)
    b_hashes = core_hashes(replay_b)
    rows = [
        {
            "artifact_path": relative,
            "replay_a_sha256": a_hashes[relative],
            "replay_b_sha256": b_hashes[relative],
            "hash_match": a_hashes[relative] == b_hashes[relative],
            "run_id": RUN_ID,
            "contract_version": CONTRACT_VERSION,
        }
        for relative in CORE_PATHS
    ]
    frame = pd.DataFrame(rows).loc[:, DETERMINISM_COLUMNS]
    return frame, b_hashes, bool(frame["hash_match"].all())


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True)
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--replay-id", required=True, choices=("replay_a", "replay_b"))
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    config, config_path = load_config(args.config)
    output_root = Path(args.output_root).resolve()
    configured_output = resolved_paths(config)["output_root"]
    if output_root != configured_output:
        raise ContractError("--output-root differs from frozen config")
    unknown_env = sorted(key for key in os.environ if key.startswith("PORTSENS_"))
    if unknown_env:
        raise ContractError(f"environment overrides forbidden: {unknown_env}")
    require_historical_authority(config)
    if output_root.exists():
        raise ContractError(f"output root already exists: {output_root}")
    paths = resolved_paths(config)
    scratch = paths[f"{args.replay_id}_scratch_root"]
    try:
        results = materialize_replay(config, config_path, scratch)
    except ReplayStageError as error:
        bundle_hash = publish_profile(
            source=error.scratch_root,
            output_root=output_root,
            config=config,
            profile_id=error.profile_id,
            reached_stage=error.reached_stage,
            results=error.stage_results,
            blocking_reason=str(error),
        )
        print(
            canonical_json_bytes(
                {
                    "decision_state": decision_frame(
                        error.profile_id, error.reached_stage
                    ).iloc[0]["decision_state"],
                    "bundle_hash": bundle_hash,
                }
            )
            .decode()
            .strip()
        )
        return 1
    if args.replay_id == "replay_a":
        print(
            canonical_json_bytes(
                {
                    "state": "REPLAY_A_MATERIALIZED_UNPUBLISHED",
                    "scratch_root": str(scratch),
                }
            )
            .decode()
            .strip()
        )
        return 0
    replay_a = paths["replay_a_scratch_root"]
    if not replay_a.is_dir():
        raise ContractError("replay_a scratch root is required before replay_b")
    determinism, replay_b_hashes, matches = compare_replays(replay_a, scratch)
    determinism_result = (
        pass_result(
            "S4_DETERMINISM",
            "replay_a_b_core_hashes",
            "all exact",
            "all exact",
            "G5_DETERMINISM",
        )
        if matches
        else fail_result(
            "S4_DETERMINISM",
            "replay_a_b_core_hashes",
            "all exact",
            "mismatch",
            "G5_DETERMINISM",
            "replay_a_b_core_hash_mismatch",
        )
    )
    results = [*results, determinism_result]
    profile_id = "P5_SENSITIVITY_MATERIALIZED" if matches else "P4_DETERMINISM_BLOCKED"
    reason = "" if matches else "replay_a_b_core_hash_mismatch"
    bundle_hash = publish_profile(
        source=scratch,
        output_root=output_root,
        config=config,
        profile_id=profile_id,
        reached_stage="determinism",
        results=results,
        blocking_reason=reason,
        determinism=determinism,
        replay_b_hashes=replay_b_hashes,
    )
    print(
        canonical_json_bytes(
            {
                "decision_state": decision_frame(profile_id, "determinism").iloc[0][
                    "decision_state"
                ],
                "bundle_hash": bundle_hash,
            }
        )
        .decode()
        .strip()
    )
    return 0 if matches else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AuthorizationError as error:
        print(
            canonical_json_bytes(
                {
                    "decision_state": "20B_P4_PORTSENS_execution_not_authorized",
                    "publication_state": "NO_PUBLISHED_BUNDLE",
                    "blocking_reason": str(error),
                }
            )
            .decode()
            .strip(),
            file=sys.stderr,
        )
        raise SystemExit(2) from None
    except SealError as error:
        print(
            canonical_json_bytes(
                {
                    "decision_state": "20B_P4_PORTSENS_seal_integrity_blocked",
                    "publication_state": "NO_PUBLISHED_BUNDLE",
                    "blocking_reason": str(error),
                }
            )
            .decode()
            .strip(),
            file=sys.stderr,
        )
        raise SystemExit(74) from None
    except ContractError as error:
        print(
            canonical_json_bytes(
                {
                    "decision_state": "20B_P4_PORTSENS_launch_blocked",
                    "publication_state": "NO_PUBLISHED_BUNDLE",
                    "blocking_reason": str(error),
                }
            )
            .decode()
            .strip(),
            file=sys.stderr,
        )
        raise SystemExit(2) from None
