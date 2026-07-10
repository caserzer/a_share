#!/usr/bin/env python
"""Fail-closed staged runner for EP20A's pre-outcome research contract."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import subprocess
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlparse

import pandas as pd
import yaml


EXPERIMENT_DIR = Path(__file__).resolve().parents[1]
TOPIC_ROOT = Path(__file__).resolve().parents[4]
REPO_ROOT = Path(__file__).resolve().parents[6]
RUN_ID = "20A_paper_lineage_data_and_replication_contract"
EXPERIMENT_ID = "20_ohlcv_positive_beta_exposure_research"
PHASE_ID = "20A"
CONFIG_PATH = EXPERIMENT_DIR / "configs/config_20a_paper_lineage_data_and_replication_contract.yaml"
REQUIREMENT_PATH = EXPERIMENT_DIR / "requirement_20a_paper_lineage_data_and_replication_contract.md"
OUTPUT_ROOT = EXPERIMENT_DIR / "outputs" / RUN_ID

FORBIDDEN_OUTCOME_TOKENS = (
    "future_", "forward_return", "mfe", "mae", "winner", "first_hit", "hit_", "label", "pnl", "strategy_return",
)
AUTHORIZATION_COLUMNS = [
    "next_requirement_execution_authorized", "policy_training_authorized", "policy_replay_authorized",
    "portfolio_optimization_authorized", "deployment_authorized",
]
CRITICAL_GATES = [
    "human_restart_lineage_gate", "paper_contract_gate", "project_data_contract_gate",
    "qfq_unit_semantics_gate", "execution_contract_gate", "stateful_portfolio_accounting_gate",
    "cost_capacity_formula_gate", "residual_primary_selection_gate", "B2_lineage_gate",
    "tradability_source_gate", "label_censoring_freeze_gate", "project_adaptation_gate",
    "outcome_firewall_gate", "economic_gate_freeze_gate", "power_gate_freeze",
    "search_accounting_gate", "forward_contract_gate", "manifest_hash_gate",
    "implementation_readiness_gate",
]
FAIL_STATE_RULES = [
    ("20A_outcome_firewall_violated", ["outcome_firewall_gate"]),
    ("20A_manifest_or_hash_blocked", ["manifest_hash_gate"]),
    ("20A_human_restart_lineage_blocked", ["human_restart_lineage_gate"]),
    ("20A_paper_contract_blocked", ["paper_contract_gate"]),
    ("20A_project_data_contract_blocked", [
        "project_data_contract_gate", "qfq_unit_semantics_gate", "B2_lineage_gate", "project_adaptation_gate",
    ]),
    ("20A_execution_contract_blocked", [
        "execution_contract_gate", "stateful_portfolio_accounting_gate", "tradability_source_gate",
        "label_censoring_freeze_gate",
    ]),
    ("20A_residual_primary_contract_blocked", ["residual_primary_selection_gate"]),
    ("20A_forward_contract_blocked", ["forward_contract_gate"]),
    ("20A_economic_gate_not_frozen", ["economic_gate_freeze_gate", "cost_capacity_formula_gate", "power_gate_freeze"]),
    ("20A_search_accounting_blocked", ["search_accounting_gate"]),
    ("20A_contract_not_impl_ready", ["implementation_readiness_gate"]),
]

FORMULA_COLUMNS = [
    "formula_id", "family_id", "arm_id", "arm_role", "replication_role", "promotion_eligible",
    "source_id", "paper_section_or_equation", "formula_text", "input_fields", "input_frequency",
    "lag_rule", "warmup_rule", "universe_rule", "weighting_rule", "holding_rule", "missing_data_rule",
    "regression_intercept_rule", "cross_section_weighting_rule", "preprocessing_and_winsorization_rule",
    "coefficient_initialization_rule", "minimum_observation_rule", "zero_return_or_zero_volume_rule",
    "tie_and_breakpoint_rule", "score_standardization_rule", "exact_data_dependencies",
    "project_adaptation_changes", "outcome_independent", "frozen_before_outcome", "formula_gate",
]
SOURCE_COLUMNS = [
    "source_id", "requested_url", "resolved_url", "resolved_domain", "content_role", "http_status",
    "content_type", "local_path", "byte_size", "sha256", "acquired_at_utc", "allowlist_gate",
    "content_validation_gate", "acquisition_error",
]
OUTCOME_ACCESS_COLUMNS = [
    "run_id", "stage", "accessed_at", "artifact_path", "artifact_sha256_or_root_hash", "dataset_role",
    "columns_read", "derived_fields", "outcome_columns_detected", "outcome_access_authorized",
    "selection_or_tuning_allowed", "purpose", "access_gate",
]
FREEZE_ARTIFACT_NAMES = [
    "resolved_config.yaml", "human_restart_authorization.json", "upstream_scope_audit.csv",
    "input_artifact_audit.csv", "source_data_inventory.csv", "paper_source_registry.csv",
    "paper_formula_registry.csv", "paper_to_local_field_mapping.csv", "arm_role_registry.csv",
    "ep19_b2_preoutcome_lineage_audit.csv", "project_universe_schema_and_coverage_audit.csv",
    "qfq_schema_unit_and_coverage_audit.csv", "benchmark_schema_and_calendar_audit.csv",
    "execution_and_cost_inheritance_audit.csv", "tradability_source_and_schema_audit.csv",
    "price_limit_rule_registry.csv", "execution_fill_and_exit_rule_freeze.csv",
    "optional_exact_source_availability_audit.csv", "ep19_2025_static_board_proxy_audit.csv",
    "universe_role_and_denominator_freeze.csv", "return_and_cash_semantics_freeze.csv",
    "stateful_portfolio_accounting_and_nav_freeze.csv", "turnover_cost_capacity_formula_freeze.csv",
    "warmup_and_monthly_support_audit.csv", "ep20a_data_replication_go_no_go.csv",
    "multiple_testing_and_search_accounting_freeze.csv", "positive_beta_economic_and_risk_gate_freeze.csv",
    "forward_mde_and_power_freeze.csv", "cnn_training_support_preflight.csv",
    "forward_boundary_and_support_freeze.csv", "forward_evaluability_preflight.csv",
    "label_completion_and_censoring_rule_freeze.csv", "outcome_access_audit.csv",
    "contract_freeze_20a.json", "20A_contract_freeze.md",
]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run EP20A pre-outcome contract stages.")
    parser.add_argument("--config", default=str(CONFIG_PATH))
    parser.add_argument("--stage", required=True, choices=["acquire-sources", "freeze", "finalize"])
    parser.add_argument("--offline", action="store_true", help="Use already cached paper materials only.")
    return parser.parse_args(argv)


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def load_config(path: str | Path = CONFIG_PATH) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def topic_path(value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    text = str(path)
    if text.startswith("topics/"):
        return REPO_ROOT / path
    if text.startswith(("experiments/", "data/")):
        return TOPIC_ROOT / path
    return EXPERIMENT_DIR / path


def resolve_paths(config: dict[str, Any]) -> dict[str, Path]:
    return {key: topic_path(value) for key, value in config.get("paths", {}).items()}


def resolve_output_root(config: dict[str, Any]) -> Path:
    return topic_path(config.get("output", {}).get("output_root", str(OUTPUT_ROOT)))


def file_sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stable_hash(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path.resolve())


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2, default=str) + "\n", encoding="utf-8")


def write_csv(path: Path, frame: pd.DataFrame, columns: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    output = frame.copy()
    if columns is not None:
        for column in columns:
            if column not in output:
                output[column] = None
        output = output[columns]
    output.to_csv(path, index=False, lineterminator="\n", float_format="%.12g")


def write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8")


def bool_value(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "pass"}


def gate(condition: bool) -> str:
    return "pass" if bool(condition) else "fail"


def root_inventory(path: Path, pattern: str = "*.csv") -> tuple[str, int, int]:
    rows: list[str] = []
    total = 0
    for item in sorted(path.glob(pattern), key=lambda p: p.name):
        size = item.stat().st_size
        total += size
        rows.append(f"{item.name}|{size}|{file_sha(item)}")
    return hashlib.sha256("\n".join(rows).encode()).hexdigest(), len(rows), total


def forbid_outcome_columns(columns: Iterable[str]) -> list[str]:
    allowed_contract_columns = {"multi_label_semantics"}
    return [
        column for column in columns
        if str(column).lower() not in allowed_contract_columns
        and any(token in str(column).lower() for token in FORBIDDEN_OUTCOME_TOKENS)
    ]


def read_csv_audited(
    path: Path,
    access_log: list[dict[str, Any]],
    role: str,
    purpose: str,
    usecols: list[str] | None = None,
    **kwargs: Any,
) -> pd.DataFrame:
    header = pd.read_csv(path, nrows=0)
    selected = list(header.columns) if usecols is None else usecols
    forbidden = forbid_outcome_columns(selected)
    if forbidden:
        raise PermissionError(f"outcome columns forbidden in 20A: {path}: {forbidden}")
    frame = pd.read_csv(path, usecols=usecols, **kwargs)
    access_log.append({
        "run_id": RUN_ID, "stage": "freeze", "accessed_at": utc_now(), "artifact_path": rel(path),
        "artifact_sha256_or_root_hash": file_sha(path), "dataset_role": role,
        "columns_read": "|".join(selected), "derived_fields": "", "outcome_columns_detected": "",
        "outcome_access_authorized": False, "selection_or_tuning_allowed": False,
        "purpose": purpose, "access_gate": "pass",
    })
    return frame


def _download(url: str) -> tuple[bytes, str, str, int]:
    request = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/126 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/pdf;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.8", "Referer": f"https://{urlparse(url).hostname or ''}/",
    })
    with urllib.request.urlopen(request, timeout=90) as response:  # noqa: S310 - explicit allowlist checked by caller
        data = response.read()
        return data, response.geturl(), response.headers.get_content_type(), int(response.status)


def _download_curl(url: str) -> tuple[bytes, str, str, int]:
    completed = subprocess.run(  # noqa: S603 - URL is checked against the explicit domain allowlist first
        ["curl", "-L", "--fail", "--silent", "--show-error", "--max-time", "90", "-A", "Mozilla/5.0", url],
        check=True, capture_output=True,
    )
    data = completed.stdout
    content_type = "application/pdf" if data.startswith(b"%PDF") else "text/html"
    return data, url, content_type, 200


def _download_validated(url: str, expected: str) -> tuple[bytes, str, str, int]:
    first_error: Exception | None = None
    try:
        result = _download(url)
        if _content_is_valid(result[0], expected):
            return result
    except Exception as error:
        first_error = error
    try:
        result = _download_curl(url)
        if _content_is_valid(result[0], expected):
            return result
        raise ValueError("downloaded content failed magic/title/challenge validation")
    except Exception as error:
        if first_error is not None:
            raise RuntimeError(f"urllib={type(first_error).__name__}:{first_error};curl={type(error).__name__}:{error}") from error
        raise


def _material_extension(expected: str, content_type: str) -> str:
    if expected == "pdf" or content_type == "application/pdf":
        return ".pdf"
    return ".html"


def _content_is_valid(data: bytes, expected: str) -> bool:
    lower = data[:100_000].lower()
    if expected == "pdf":
        return len(data) >= 20_000 and data.startswith(b"%PDF")
    challenge_tokens = (b"client challenge", b"captcha", b"access denied", b"cf-chl-")
    html_magic = b"<html" in lower[:2_000] or b"<!doctype html" in lower[:2_000]
    return len(data) >= 20_000 and html_magic and not any(token in lower for token in challenge_tokens)


def build_formula_draft(config: dict[str, Any], source_manifest: pd.DataFrame) -> pd.DataFrame:
    source_hashes = dict(zip(source_manifest.get("source_id", []), source_manifest.get("sha256", []), strict=False))
    roles = {
        "C1_TMOM_12_1": "paper_comparator", "C2_TRENDPV_RAW_ADAPTATION": "project_primary_1",
        "C3_RESMOM_R3_BOARD_ADAPTATION": "preferred_project_primary_2",
        "C3A_RESMOM_R2_MARKET_ONLY": "fallback_project_primary_2", "P2_TREND_FULL_EXACT": "paper_diagnostic",
        "P3_RESMOM_CH3_EXACT": "paper_diagnostic", "C4_LOWVOL": "risk_comparator",
        "D1_FIP_INCREMENT": "deferred_challenger", "E2_MA20_OVERLAY": "risk_overlay",
        "F1_CNN_ORACLE": "representation_oracle",
    }
    rows: list[dict[str, Any]] = []
    for item in config.get("formula_rows", []):
        arm = item["arm_id"]
        is_project = "ADAPTATION" in arm or arm in {"C1_TMOM_12_1", "C4_LOWVOL"}
        row = {
            **item,
            "arm_role": roles.get(arm, "registered"),
            "replication_role": "project_adaptation" if is_project else "paper_exact_or_diagnostic",
            "promotion_eligible": arm in {"C2_TRENDPV_RAW_ADAPTATION", "C3_RESMOM_R3_BOARD_ADAPTATION", "C3A_RESMOM_R2_MARKET_ONLY"},
            "input_frequency": "daily_to_monthly" if item["family_id"] in {"TrendPV", "FIP", "CNN", "MAOverlay"} else "monthly",
            "universe_rule": "U_project" if is_project else "U_paper",
            "holding_rule": "one_calendar_month" if arm.startswith("C") else "paper_or_deferred",
            "missing_data_rule": "fail_closed_and_record_missing_reason",
            "regression_intercept_rule": "fit_intercept=true" if "REG" in item["formula_id"] or "RESMOM" in item["formula_id"] else "not_applicable",
            "cross_section_weighting_rule": "equal_stock_weight" if is_project else "paper_defined",
            "preprocessing_and_winsorization_rule": "no_winsorization_unless_human_reviewed_source_row_says_otherwise",
            "coefficient_initialization_rule": "human_review_required_from_source" if item["formula_id"] == "TRENDPV_MONTHLY_CS_REG" else "not_applicable",
            "minimum_observation_rule": item["warmup_rule"],
            "zero_return_or_zero_volume_rule": "zero return retained; zero current volume makes TrendPV volume signal missing",
            "tie_and_breakpoint_rule": "instrument_ascending_exact_count_for_project; paper_defined_for_exact",
            "score_standardization_rule": "mean_over_11_divided_by_sample_std_ddof1" if "RESMOM" in item["formula_id"] else "formula_specific",
            "exact_data_dependencies": "PIT_market_cap|PIT_EP|risk_free|CH3" if not is_project else "none_beyond_project_contract",
            "project_adaptation_changes": item["formula_text"] if is_project else "none",
            "outcome_independent": True,
            "frozen_before_outcome": True,
            "formula_gate": "pending_human_review",
            "source_local_sha256": source_hashes.get(item["source_id"], ""),
        }
        rows.append(row)
    return pd.DataFrame(rows)[FORMULA_COLUMNS]


def acquire_sources_stage(config_path: str | Path = CONFIG_PATH, offline: bool = False) -> dict[str, Path]:
    config = load_config(config_path)
    paths = resolve_paths(config)
    cache = paths["paper_cache_root"]
    material_root = cache / "source_materials"
    material_root.mkdir(parents=True, exist_ok=True)
    manifest_path = cache / "source_acquisition_manifest.csv"
    old = pd.read_csv(manifest_path) if manifest_path.exists() else pd.DataFrame(columns=SOURCE_COLUMNS)
    rows: list[dict[str, Any]] = []
    for source in config.get("paper_sources", []):
        source_id = source["source_id"]
        fetch_url = source.get("download_url", source["url"])
        reused = old.loc[old.get("source_id", pd.Series(dtype=str)).eq(source_id)] if not old.empty else pd.DataFrame()
        valid_reuse = False
        if not reused.empty:
            candidate = REPO_ROOT / str(reused.iloc[-1]["local_path"])
            valid_reuse = (
                candidate.exists() and file_sha(candidate) == str(reused.iloc[-1]["sha256"])
                and _content_is_valid(candidate.read_bytes(), source["expected_content"])
                and str(reused.iloc[-1].get("allowlist_gate", "")) == "pass"
            )
        if valid_reuse:
            rows.append(reused.iloc[-1].to_dict())
            continue
        if offline:
            rows.append({
                "source_id": source_id, "requested_url": source["url"], "resolved_url": "",
                "resolved_domain": "", "content_role": source["expected_content"], "http_status": 0,
                "content_type": "", "local_path": "", "byte_size": 0, "sha256": "",
                "acquired_at_utc": utc_now(), "allowlist_gate": "fail", "content_validation_gate": "fail",
                "acquisition_error": "offline_cache_miss",
            })
            continue
        requested_domain = urlparse(fetch_url).hostname or ""
        if requested_domain not in set(source["allowed_domains"]):
            raise PermissionError(f"paper URL outside allowlist: {fetch_url}")
        try:
            data, resolved_url, content_type, status = _download_validated(fetch_url, source["expected_content"])
        except Exception as error:  # Every failure is materialized; one source must not erase the audit trail.
            rows.append({
                "source_id": source_id, "requested_url": source["url"], "resolved_url": "",
                "resolved_domain": "", "content_role": f"official_{source['expected_content']}_full_text",
                "http_status": int(getattr(error, "code", 0) or 0), "content_type": "",
                "local_path": "", "byte_size": 0, "sha256": "", "acquired_at_utc": utc_now(),
                "allowlist_gate": "pass", "content_validation_gate": "fail",
                "acquisition_error": f"{type(error).__name__}:{str(error)[:300]}",
            })
            continue
        resolved_domain = urlparse(resolved_url).hostname or ""
        allow_gate = gate(resolved_domain in set(source["allowed_domains"]))
        expected = source["expected_content"]
        content_ok = _content_is_valid(data, expected)
        content_gate = gate(bool(data) and content_ok and allow_gate == "pass")
        digest = hashlib.sha256(data).hexdigest()
        extension = _material_extension(expected, content_type)
        local_path = material_root / f"{source_id}__{digest[:16]}{extension}"
        if not local_path.exists():
            local_path.write_bytes(data)
        rows.append({
            "source_id": source_id, "requested_url": source["url"], "resolved_url": resolved_url,
            "resolved_domain": resolved_domain, "content_role": f"official_{expected}_full_text",
            "http_status": status, "content_type": content_type, "local_path": rel(local_path),
            "byte_size": len(data), "sha256": digest, "acquired_at_utc": utc_now(),
            "allowlist_gate": allow_gate, "content_validation_gate": content_gate, "acquisition_error": "",
        })
    manifest = pd.DataFrame(rows)[SOURCE_COLUMNS].sort_values("source_id").reset_index(drop=True)
    write_csv(manifest_path, manifest, SOURCE_COLUMNS)
    draft_path = cache / "paper_formula_registry_draft.csv"
    draft = build_formula_draft(config, manifest)
    write_csv(draft_path, draft, FORMULA_COLUMNS)
    authorization_path = cache / "formula_review_authorization.json"
    existing_authorization = read_json(authorization_path) if authorization_path.exists() else {}
    if not bool_value(existing_authorization.get("authorization_granted")):
        write_json(authorization_path, {
            "authorization_type": "paper_formula_registry_human_review", "reviewed_at": "", "reviewer": "",
            "source_acquisition_manifest_sha256": file_sha(manifest_path),
            "reviewed_source_ids": [], "reviewed_formula_ids": [], "formula_registry_draft_sha256": file_sha(draft_path),
            "all_implementation_choices_resolved": False, "authorization_granted": False,
            "instructions": "Human reviewer must verify every source anchor and formula choice, then update this file.",
        })
    packet_path = cache / "formula_review_packet.md"
    lines = [
        "# EP20A Formula Review Packet", "", "This packet is pre-outcome. It does not authorize freeze.", "",
        f"- source manifest sha256: `{file_sha(manifest_path)}`", f"- formula draft sha256: `{file_sha(draft_path)}`", "",
        f"- acquired and validated sources: `{int(manifest['content_validation_gate'].eq('pass').sum())}/{len(manifest)}`", "",
        "## Source checklist", "",
        "| source_id | HTTP | bytes | material gate | local path / acquisition error |",
        "|---|---:|---:|---|---|",
    ]
    for _, row in manifest.iterrows():
        evidence = row["local_path"] if row["content_validation_gate"] == "pass" else row["acquisition_error"]
        lines.append(f"| {row['source_id']} | {row['http_status']} | {row['byte_size']} | {row['content_validation_gate']} | {str(evidence).replace('|', '/')} |")
    lines.extend([
        "", "## Formula checklist", "",
        "| formula_id | source_id | page/equation anchor | current gate |",
        "|---|---|---|---|",
    ])
    for _, row in draft.iterrows():
        lines.append(f"| {row['formula_id']} | {row['source_id']} | {str(row['paper_section_or_equation']).replace('|', '/')} | {row['formula_gate']} |")
    lines.extend([
        "", "## Authorization procedure", "",
        "Review every formula against the cached local material, resolve every implementation choice, then sign",
        "`formula_review_authorization.json`. Set each reviewed draft row's `formula_gate=pass`, then update both",
        "hash fields, the complete reviewed source/formula ID lists, reviewer, reviewed_at,",
        "all_implementation_choices_resolved=true and authorization_granted=true.", "",
        "Do not authorize while any source material gate is fail or while any formula choice remains implicit.", "",
    ])
    write_text(packet_path, "\n".join(lines))
    return {
        "source_acquisition_manifest": manifest_path, "paper_formula_registry_draft": draft_path,
        "formula_review_authorization": authorization_path, "formula_review_packet": packet_path,
    }


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def validate_formula_authorization(config: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    """Validate the external human restart token before any market-data read."""
    cache = resolve_paths(config)["paper_cache_root"]
    manifest_path = cache / "source_acquisition_manifest.csv"
    draft_path = cache / "paper_formula_registry_draft.csv"
    auth_path = cache / "formula_review_authorization.json"
    missing = [str(path) for path in (manifest_path, draft_path, auth_path) if not path.exists()]
    if missing:
        raise PermissionError(f"paper formula review inputs missing: {missing}")
    manifest = pd.read_csv(manifest_path, dtype=str, keep_default_na=False)
    draft = pd.read_csv(draft_path, dtype=str, keep_default_na=False)
    auth = read_json(auth_path)
    reasons: list[str] = []
    if not bool_value(auth.get("authorization_granted")):
        reasons.append("authorization_granted=false")
    if not bool_value(auth.get("all_implementation_choices_resolved")):
        reasons.append("all_implementation_choices_resolved=false")
    if not str(auth.get("reviewer", "")).strip() or not str(auth.get("reviewed_at", "")).strip():
        reasons.append("reviewer_or_reviewed_at_missing")
    if auth.get("source_acquisition_manifest_sha256") != file_sha(manifest_path):
        reasons.append("source_manifest_hash_mismatch")
    if auth.get("formula_registry_draft_sha256") != file_sha(draft_path):
        reasons.append("formula_registry_draft_hash_mismatch")
    if set(auth.get("reviewed_source_ids", [])) != set(manifest["source_id"]):
        reasons.append("reviewed_source_ids_incomplete")
    if set(auth.get("reviewed_formula_ids", [])) != set(draft["formula_id"]):
        reasons.append("reviewed_formula_ids_incomplete")
    waiver = config.get("paper_material_waiver", {})
    configured_waivers = set(waiver.get("waived_source_ids", []))
    authorized_waivers = set(auth.get("material_waiver_source_ids", []))
    failed_sources = set(manifest.loc[manifest["content_validation_gate"].ne("pass"), "source_id"])
    waiver_valid = (
        bool_value(waiver.get("authorized"))
        and not bool_value(waiver.get("local_full_text_claim_allowed_for_waived_sources"))
        and configured_waivers == authorized_waivers == failed_sources
        and bool_value(auth.get("material_waiver_authorized"))
    )
    if not manifest["allowlist_gate"].eq("pass").all():
        reasons.append("paper_source_allowlist_gate_failed")
    if failed_sources and not waiver_valid:
        reasons.append("paper_material_gate_failed_or_waiver_mismatch")
    fields = [
        "paper_section_or_equation", "formula_text", "lag_rule", "warmup_rule", "universe_rule",
        "weighting_rule", "holding_rule", "missing_data_rule", "regression_intercept_rule",
        "cross_section_weighting_rule", "preprocessing_and_winsorization_rule",
        "coefficient_initialization_rule", "minimum_observation_rule", "zero_return_or_zero_volume_rule",
        "tie_and_breakpoint_rule", "score_standardization_rule",
    ]
    for column in fields:
        if column not in draft or draft[column].str.strip().eq("").any():
            reasons.append(f"formula_field_incomplete:{column}")
    unresolved = draft.astype(str).apply(
        lambda column: column.str.contains(r"\bsee paper\b|unknown|tbd", case=False, regex=True)
    ).any().any()
    if unresolved:
        reasons.append("formula_contains_unresolved_placeholder")
    if "formula_gate" not in draft or not draft["formula_gate"].eq("pass").all():
        reasons.append("formula_gate_not_all_pass")
    if reasons:
        raise PermissionError("paper formula human authorization blocked: " + ";".join(sorted(set(reasons))))
    return manifest, draft, auth


def log_file_access(
    access_log: list[dict[str, Any]], path: Path, role: str, purpose: str, columns: Iterable[str] = (),
) -> None:
    access_log.append({
        "run_id": RUN_ID, "stage": "freeze", "accessed_at": utc_now(), "artifact_path": rel(path),
        "artifact_sha256_or_root_hash": file_sha(path), "dataset_role": role,
        "columns_read": "|".join(map(str, columns)), "derived_fields": "",
        "outcome_columns_detected": "", "outcome_access_authorized": False,
        "selection_or_tuning_allowed": False, "purpose": purpose, "access_gate": "pass",
    })


def normalize_instrument(value: Any) -> str:
    text = str(value).strip().upper()
    if re.fullmatch(r"\d{6}\.(SH|SZ|BJ)", text):
        code, exchange = text.split(".")
        return f"{exchange}{code}"
    if re.fullmatch(r"(SH|SZ|BJ)\d{6}", text):
        return text
    if re.fullmatch(r"\d{6}", text):
        if text.startswith(("6", "9")):
            return "SH" + text
        if text.startswith(("4", "8")):
            return "BJ" + text
        return "SZ" + text
    return ""


def artifact_row(path: Path, role: str, required: bool = True) -> dict[str, Any]:
    exists = path.exists()
    if exists and path.is_dir():
        digest, file_n, byte_size = root_inventory(path)
        kind = "directory_inventory"
    elif exists:
        digest, file_n, byte_size, kind = file_sha(path), 1, path.stat().st_size, "file"
    else:
        digest, file_n, byte_size, kind = "", 0, 0, "missing"
    return {
        "run_id": RUN_ID, "artifact_role": role, "artifact_path": rel(path), "artifact_kind": kind,
        "required": required, "exists": exists, "file_n": file_n, "byte_size": byte_size,
        "sha256_or_root_inventory_hash": digest, "input_gate": gate(exists or not required),
    }


def build_project_universe_audit(
    path: Path, config: dict[str, Any], access_log: list[dict[str, Any]],
) -> tuple[pd.DataFrame, dict[str, Any], pd.DataFrame]:
    columns = [
        "usable_trade_date", "instrument", "membership_date", "available_time", "board_bucket", "is_listed",
        "is_st", "is_suspended", "total_market_cap_cny", "market_cap_source", "source_asof_date",
        "history_ready_240d_flag",
    ]
    frame = read_csv_audited(path, access_log, "project_universe", "schema and PIT coverage", usecols=columns)
    frame["usable_trade_date"] = pd.to_datetime(frame["usable_trade_date"], errors="coerce")
    frame["instrument"] = frame["instrument"].map(normalize_instrument)
    valid = frame["usable_trade_date"].notna()
    key_unique = not frame.loc[valid, ["usable_trade_date", "instrument"]].duplicated().any()
    monthly_last = frame.loc[valid].groupby(frame.loc[valid, "usable_trade_date"].dt.to_period("M"))["usable_trade_date"].max()
    month_counts = (
        frame.merge(monthly_last.rename("month_last"), left_on="usable_trade_date", right_on="month_last")
        .groupby("month_last")["instrument"].nunique().sort_index()
    )
    threshold = config["project_contract"]
    stats = {
        "row_n": len(frame), "unique_instrument_n": frame["instrument"].replace("", pd.NA).nunique(),
        "date_min": frame["usable_trade_date"].min().date().isoformat(),
        "date_max": frame["usable_trade_date"].max().date().isoformat(), "primary_key_unique": key_unique,
        "market_cap_nonmissing_rate": float(frame["total_market_cap_cny"].notna().mean()),
        "membership_timing_nonmissing_rate": float(frame[["membership_date", "available_time"]].notna().all(axis=1).mean()),
        "monthly_eligible_p10": float(month_counts.quantile(0.10, interpolation="linear")),
        "monthly_eligible_median": float(month_counts.median()), "monthly_eligible_p90": float(month_counts.quantile(0.90)),
        "monthly_decision_n": int(len(month_counts)),
        "observed_board_buckets": "|".join(sorted(frame["board_bucket"].dropna().astype(str).unique())),
    }
    checks = [
        ("primary_key_unique", key_unique, True, key_unique),
        ("unique_instrument_n", stats["unique_instrument_n"], threshold["project_universe_unique_instrument_min"], stats["unique_instrument_n"] >= threshold["project_universe_unique_instrument_min"]),
        ("date_min", stats["date_min"], threshold["project_universe_date_min_max"], stats["date_min"] <= threshold["project_universe_date_min_max"]),
        ("market_cap_nonmissing_rate", stats["market_cap_nonmissing_rate"], threshold["project_market_cap_nonmissing_rate_min"], stats["market_cap_nonmissing_rate"] >= threshold["project_market_cap_nonmissing_rate_min"]),
        ("monthly_eligible_p10", stats["monthly_eligible_p10"], threshold["project_monthly_eligible_p10_min"], stats["monthly_eligible_p10"] >= threshold["project_monthly_eligible_p10_min"]),
        ("monthly_eligible_median", stats["monthly_eligible_median"], threshold["project_monthly_eligible_median_min"], stats["monthly_eligible_median"] >= threshold["project_monthly_eligible_median_min"]),
    ]
    audit = pd.DataFrame([
        {"run_id": RUN_ID, "check_id": name, "observed_value": observed, "required_value": required, "status": gate(ok)}
        for name, observed, required, ok in checks
    ])
    stats["project_data_contract_gate"] = gate(audit["status"].eq("pass").all())
    return audit, stats, frame


def build_qfq_audit(root: Path, instruments: set[str], config: dict[str, Any]) -> tuple[pd.DataFrame, dict[str, Any]]:
    digest, file_n, byte_size = root_inventory(root)
    files = sorted(root.glob("*.csv"))
    overlap = len({path.stem.upper() for path in files} & instruments) / max(1, len(instruments))
    required = {"date", "open", "high", "low", "close", "volume", "money", "instrument", "source_volume_unit"}
    units: list[str] = []
    schema_ok = True
    for path in files[: min(200, len(files))]:
        sample = pd.read_csv(path, nrows=1)
        schema_ok &= required.issubset(sample.columns)
        units.append(str(sample.iloc[0].get("source_volume_unit", "")).lower() if len(sample) else "")
    unit_ok = bool(units) and set(units).issubset({"shares", "hands"})
    threshold = config["project_contract"]
    checks = [
        ("root_inventory", digest, "nonempty", bool(digest)),
        ("file_n", file_n, threshold["qfq_file_n_min"], file_n >= threshold["qfq_file_n_min"]),
        ("U_project_filename_overlap", overlap, threshold["qfq_overlap_rate_min"], overlap >= threshold["qfq_overlap_rate_min"]),
        ("sample_schema", schema_ok, True, schema_ok),
        ("volume_unit_semantics", "|".join(sorted(set(units))), "shares_or_hands", unit_ok),
        ("turnover_normalization_contract", "detect percent or ratio then normalize", "frozen", True),
        ("qfq_corporate_action_semantics", "qfq price plus raw volume/money; not total return", "explicit", True),
    ]
    audit = pd.DataFrame([{
        "run_id": RUN_ID, "check_id": name, "observed_value": observed, "required_value": required,
        "status": gate(ok), "root_inventory_hash": digest, "file_n": file_n, "byte_size": byte_size,
    } for name, observed, required, ok in checks])
    all_ok = all(row[-1] for row in checks)
    return audit, {
        "qfq_unit_semantics_gate": gate(all_ok),
        "wide_qfq_status_gate": gate(file_n >= threshold["qfq_file_n_min"]),
        "qfq_file_n": file_n, "qfq_overlap_rate": overlap,
    }


def build_benchmark_audit(path: Path, access_log: list[dict[str, Any]]) -> tuple[pd.DataFrame, dict[str, Any]]:
    columns = ["date", "trade_date", "index_alias", "instrument", "close", "source_function", "source_volume_unit"]
    frame = read_csv_audited(path, access_log, "benchmark", "benchmark identity and calendar", usecols=columns)
    csi = frame.loc[frame["index_alias"].astype(str).str.lower().eq("csi300")].copy()
    csi["trade_date"] = pd.to_datetime(csi["trade_date"], errors="coerce")
    checks = [
        ("csi300_present", len(csi), ">0", len(csi) > 0),
        ("csi300_date_unique", not csi["trade_date"].duplicated().any(), True, not csi["trade_date"].duplicated().any()),
        ("csi300_close_complete", float(csi["close"].notna().mean()), 0.99, csi["close"].notna().mean() >= 0.99),
    ]
    audit = pd.DataFrame([{"run_id": RUN_ID, "check_id": n, "observed_value": o, "required_value": r, "status": gate(ok)} for n, o, r, ok in checks])
    return audit, {
        "benchmark_schema_and_calendar_gate": gate(all(row[-1] for row in checks)),
        "benchmark_month_n": int(csi["trade_date"].dt.to_period("M").nunique()),
    }


def build_b2_lineage(paths: dict[str, Path], access_log: list[dict[str, Any]]) -> tuple[pd.DataFrame, str]:
    selected = read_csv_audited(
        paths["ep19_b2_selected_manifest"], access_log, "EP19_preoutcome_rule", "B2 selected lineage",
        usecols=["family_id", "grid_cell_id", "parameter_hash", "selection_split", "selection_metric", "selection_track", "manifest_frozen_before_robustness_readout"],
    )
    grid = read_csv_audited(
        paths["ep19_b2_grid_manifest"], access_log, "EP19_preoutcome_rule", "B2 grid lineage",
        usecols=["family_id", "grid_cell_id", "parameter_json", "parameter_hash", "selection_split", "source_contract", "candidate_row_source", "feature_source_map_version"],
    )
    features = read_csv_audited(
        paths["ep19_b2_feature_map"], access_log, "EP19_preoutcome_rule", "B2 feature lineage",
        usecols=["feature_field", "source_type", "source_artifact", "source_columns", "asof_rule", "window_rule", "cross_section_universe", "reconstruction_formula", "baseline_rebuild_required", "pit_guard", "missing_policy", "materialization_status"],
    )
    budget = read_csv_audited(
        paths["ep19_b2_budget_registry"], access_log, "EP19_preoutcome_rule", "R2 trim lineage",
        usecols=["arm_id", "arm_role", "formula", "parameter_json", "parameter_source"],
    )
    hash_path = paths["ep19_b2_output_hashes"]
    hashes = read_json(hash_path)
    log_file_access(access_log, hash_path, "EP19_preoutcome_rule", "B2 hash verification", hashes.keys())
    expected_grid = "B2-relative-strength-breakout__182b3d0f30f5"
    selected_row = selected.loc[selected["grid_cell_id"].eq(expected_grid)]
    grid_row = grid.loc[grid["grid_cell_id"].eq(expected_grid)]
    r2 = budget.loc[budget["arm_id"].eq("R2_VOL60_TOP30_TRIM")]
    checks = [
        ("family_id", "B2_relative_strength_breakout", not selected_row.empty and selected_row.iloc[0]["family_id"] == "B2_relative_strength_breakout"),
        ("grid_cell_id", expected_grid, not grid_row.empty),
        ("parameter_hash", "182b3d0f30f5c407544f209b2597ca6959a1ad8e8f94d6957345c7931da6e1a2", not grid_row.empty and grid_row.iloc[0]["parameter_hash"] == "182b3d0f30f5c407544f209b2597ca6959a1ad8e8f94d6957345c7931da6e1a2"),
        ("grid_manifest_hash", hashes.get("grid_cell_manifest", ""), hashes.get("grid_cell_manifest") == file_sha(paths["ep19_b2_grid_manifest"])),
        ("feature_map_hash", hashes.get("simple_rule_feature_source_map", ""), hashes.get("simple_rule_feature_source_map") == file_sha(paths["ep19_b2_feature_map"])),
        ("feature_PIT_guard", "nonempty", len(features) > 0 and features["pit_guard"].fillna("").str.len().gt(0).all()),
        ("daily_reference_cooldown", "10 sessions", True),
        ("daily_reference_entry", "next executable open", True),
        ("R2_same_date_candidate_p70", "linear; remove_equal_threshold; no cross-date estimation", not r2.empty and "q_vol60 < candidate_p70" in str(r2.iloc[0]["formula"])),
        ("EP19_effect_size_transfer_allowed", False, True),
    ]
    audit = pd.DataFrame([{"run_id": RUN_ID, "check_id": n, "frozen_value": v, "status": gate(ok)} for n, v, ok in checks])
    return audit, gate(all(row[-1] for row in checks))


def build_board_audit(
    paths: dict[str, Path], instruments: set[str], config: dict[str, Any], access_log: list[dict[str, Any]],
) -> tuple[pd.DataFrame, dict[str, Any]]:
    index = read_csv_audited(paths["ep19_board_index"], access_log, "static_board_proxy", "board identity", usecols=["classification_year", "snapshot_trade_date", "board_ts_code", "board_name", "idx_type"])
    member = read_csv_audited(paths["ep19_board_member"], access_log, "static_board_proxy", "board membership", usecols=["classification_year", "snapshot_trade_date", "board_ts_code", "board_name", "con_code"])
    member["instrument"] = member["con_code"].map(normalize_instrument)
    invalid = int(member["instrument"].eq("").sum())
    overlap = member.loc[member["instrument"].isin(instruments)].drop_duplicates(["board_ts_code", "instrument"])
    eligible_counts = overlap.groupby("board_ts_code")["instrument"].nunique()
    eligible_boards = set(eligible_counts[eligible_counts >= 10].index.astype(str))
    signatures: set[str] = set()
    duplicate_n = 0
    for _, group in overlap.loc[overlap["board_ts_code"].astype(str).isin(eligible_boards)].groupby("board_ts_code"):
        signature = stable_hash(sorted(group["instrument"].unique()))
        if signature in signatures:
            duplicate_n += 1
        signatures.add(signature)
    eligible_after_dedup = len(eligible_boards) - duplicate_n
    overlap_rate = overlap["instrument"].nunique() / max(1, len(instruments))
    threshold = config["project_contract"]
    ok = (
        len(index) == 458 and len(member) == 43468 and member["board_ts_code"].nunique() == 314 and invalid == 0
        and overlap_rate >= threshold["board_overlap_rate_min"] and eligible_after_dedup >= threshold["board_column_n_min"]
    )
    row = {
        "run_id": RUN_ID, "proxy_id": "ep19_dc_2025_static_board_proxy", "snapshot_trade_date": "2025-01-02",
        "raw_index_row_n": len(index), "raw_member_row_n": len(member), "raw_board_n": index["board_ts_code"].nunique(),
        "boards_with_member_rows": member["board_ts_code"].nunique(), "invalid_instrument_row_n": invalid,
        "U_project_instrument_n": len(instruments), "overlap_instrument_n": overlap["instrument"].nunique(),
        "overlap_rate": overlap_rate, "eligible_board_column_n_before_dedup": len(eligible_boards),
        "duplicate_board_column_n": duplicate_n, "eligible_board_column_n": eligible_after_dedup,
        "multi_label_semantics": True, "historical_PIT_industry_claim_allowed": False,
        "membership_currentness_claim": False, "forward_control_allowed": ok,
        "board_snapshot_age_rule": "decision_month - 2025-01", "board_proxy_gate": gate(ok),
    }
    return pd.DataFrame([row]), row


def compute_mde_grid(config: dict[str, Any]) -> pd.DataFrame:
    rows = []
    for effect in (0.01, 0.02, 0.03):
        for volatility in (0.05, 0.08, 0.12):
            n = math.ceil(((1.9599639845 + 0.8416212336) * volatility / effect) ** 2)
            rows.append({
                "run_id": RUN_ID, "effect_monthly": effect, "monthly_volatility": volatility,
                "alpha": config["power"]["holm_worst_case_alpha"], "power": config["power"]["target_power"],
                "z_1_minus_alpha": 1.9599639845, "z_power": 0.8416212336, "n_required": n,
                "evidence_unit": "distinct_complete_decision_month", "serial_independence_claim": False,
                "newey_west_lag_rule": "max(1,floor(4*(N/100)^(2/9)))",
            })
    return pd.DataFrame(rows)


def key_value_rows(group: str, values: dict[str, Any]) -> pd.DataFrame:
    return pd.DataFrame([{
        "run_id": RUN_ID, "contract_group": group, "field": key, "frozen_value": value, "status": "pass",
    } for key, value in values.items()])


def fixed_arm_registry(residual_primary: str) -> pd.DataFrame:
    rows = [
        ("C0_ALL_ELIGIBLE", "all eligible comparator", "comparator"),
        ("C1_TMOM_12_1", "incumbent paper comparator", "comparator"),
        ("C2_TRENDPV_RAW_ADAPTATION", "project primary 1", "primary"),
        ("C3_RESMOM_R3_BOARD_ADAPTATION", "preferred residual arm when board passes", "primary" if residual_primary.startswith("C3_") else "comparator"),
        ("C3A_RESMOM_R2_MARKET_ONLY", "fallback residual arm", "primary" if residual_primary.startswith("C3A_") else "comparator"),
        ("C4_LOWVOL", "risk comparator", "comparator"),
        ("C5_EP19_B2_MONTH_END_ADAPTATION", "month-end adaptation of daily B2", "comparator"),
        ("C5R2_EP19_B2_MONTH_END_VOL60_TRIM", "same-date causal p70 trim", "comparator"),
        ("P2_TREND_FULL_EXACT", "paper exact diagnostic", "paper_diagnostic"),
        ("P3_RESMOM_CH3_EXACT", "paper exact diagnostic", "paper_diagnostic"),
        ("D1_FIP_INCREMENT", "ordered deferred challenger", "deferred"),
        ("E2_MA20_OVERLAY", "risk overlay", "overlay"),
        ("F1_CNN_ORACLE", "representation oracle", "diagnostic"),
    ]
    selection_rules = {
        "C0_ALL_ELIGIBLE": "all executable U_project rows",
        "C1_TMOM_12_1": "project top decile of frozen 12-1 total momentum",
        "C2_TRENDPV_RAW_ADAPTATION": "project top decile of frozen raw TrendPV score",
        "C3_RESMOM_R3_BOARD_ADAPTATION": "project top decile of two-stage market then size/board residual momentum",
        "C3A_RESMOM_R2_MARKET_ONLY": "project top decile of sequential 36-month market residual momentum",
        "C4_LOWVOL": "project lowest decile of preceding 36-month volatility",
        "C5_EP19_B2_MONTH_END_ADAPTATION": "frozen B2 rule applied once on each project month-end cross-section",
        "C5R2_EP19_B2_MONTH_END_VOL60_TRIM": "C5 rows with q_vol60 below same-date candidate linear p70; equality removed",
        "P2_TREND_FULL_EXACT": "paper exact only when exact gates pass",
        "P3_RESMOM_CH3_EXACT": "paper exact only when exact gates pass",
        "D1_FIP_INCREMENT": "deferred ordered challenger",
        "E2_MA20_OVERLAY": "prior sleeve close above prior MA20 else cash",
        "F1_CNN_ORACLE": "strict-time-split representation diagnostic",
    }
    return pd.DataFrame([{
        "run_id": RUN_ID, "arm_id": arm, "arm_description": description, "arm_role": role,
        "promotion_eligible": role == "primary", "initial_AUM_cny": 10_000_000,
        "portfolio_ledger_id": f"ledger_{arm}", "ledger_count_per_arm": 1,
        "accounting_mode": "continuous_no_injection_stateful_NAV", "active_weight_rescaling_allowed": False,
        "selection_rule": selection_rules[arm],
        "target_weight_rule": "equal selected-name target weight; C5R2 retains untrimmed weights; remainder cash",
        "tie_rule": "instrument ascending exact-count; C5R2 removes q_vol60 equal to p70",
        "entry_timing": "after-close decision; one next-open executable attempt",
        "cash_rule": "unselected, trimmed, blocked, and unfilled weight remains cash",
        "EP19_effect_size_transfer_allowed": False,
    } for arm, description, role in rows])


def decision_state(gates: dict[str, str], capabilities: dict[str, Any]) -> tuple[str, str]:
    reasons = [name for name in CRITICAL_GATES if gates.get(name) != "pass"]
    if not reasons and bool(capabilities.get("project_adaptation_reachable")) and bool(capabilities.get("forward_beta_test_reachable")):
        return "20A_preoutcome_contract_ready", ""
    for state, names in FAIL_STATE_RULES:
        if any(gates.get(name) != "pass" for name in names):
            return state, "|".join(reasons)
    return "20A_contract_not_impl_ready", "|".join(reasons or ["capability_not_reachable"])


def seal_bundle(directory: Path, manifest_name: str, hashes_name: str, names: list[str], metadata: dict[str, Any]) -> str:
    manifest_path = directory / manifest_name
    hashes_path = directory / hashes_name
    if manifest_path.exists() or hashes_path.exists():
        verify_bundle(directory, manifest_name, hashes_name, names)
        return file_sha(hashes_path)
    missing = [name for name in names if not (directory / name).is_file()]
    if missing:
        raise FileNotFoundError(f"cannot seal incomplete bundle: {missing}")
    material_hashes = {name: file_sha(directory / name) for name in sorted(names)}
    write_json(manifest_path, {
        **metadata, "sealed_at_utc": utc_now(), "immutable": True, "output_hashes": material_hashes,
        "manifest_hash_excluded": True, "output_hash_file_excluded": True,
    })
    write_json(hashes_path, {**material_hashes, manifest_name: file_sha(manifest_path)})
    verify_bundle(directory, manifest_name, hashes_name, names)
    return file_sha(hashes_path)


def verify_bundle(directory: Path, manifest_name: str, hashes_name: str, names: list[str]) -> None:
    manifest_path = directory / manifest_name
    hashes_path = directory / hashes_name
    if not manifest_path.exists() or not hashes_path.exists():
        raise FileNotFoundError("sealed manifest/hash file missing")
    manifest = read_json(manifest_path)
    hashes = read_json(hashes_path)
    if set(hashes) != set(names) | {manifest_name} or hashes.get(manifest_name) != file_sha(manifest_path):
        raise RuntimeError("sealed bundle file set or manifest hash mismatch")
    for name in names:
        path = directory / name
        digest = file_sha(path) if path.exists() else ""
        if hashes.get(name) != digest or manifest.get("output_hashes", {}).get(name) != digest:
            raise RuntimeError(f"sealed bundle hash mismatch: {name}")


def freeze_stage(config_path: str | Path = CONFIG_PATH) -> dict[str, str]:
    config = load_config(config_path)
    paths = resolve_paths(config)
    output_root = resolve_output_root(config)
    freeze_root = output_root / "freeze"
    manifest_path = freeze_root / "freeze_manifest_20a.json"
    hashes_path = freeze_root / "freeze_output_hashes_20a.json"
    if manifest_path.exists() or hashes_path.exists():
        verify_bundle(freeze_root, manifest_path.name, hashes_path.name, FREEZE_ARTIFACT_NAMES)
        return {"freeze_root": str(freeze_root), "freeze_bundle_hash": file_sha(hashes_path), "status": "already_sealed"}

    # Fail closed before mkdir, market data, or EP19 reads. A human must verify the cached papers/formulas.
    source_manifest, formula_registry, human_auth = validate_formula_authorization(config)
    if freeze_root.exists():
        raise RuntimeError(f"unsealed freeze directory exists and may not be resumed or overwritten: {freeze_root}")
    freeze_root.mkdir(parents=True)
    access_log: list[dict[str, Any]] = []
    try:
        for path, role in [
            (Path(config_path).resolve(), "resolved_config_source"),
            (paths["research_plan"], "planning_authority"),
            (paths["requirement"], "requirement_authority"),
        ]:
            log_file_access(access_log, path, role, "hash and lineage binding")
        cache = paths["paper_cache_root"]
        for path, role in [
            (cache / "source_acquisition_manifest.csv", "paper_source_manifest"),
            (cache / "paper_formula_registry_draft.csv", "human_reviewed_formula_registry"),
            (cache / "formula_review_authorization.json", "human_restart_authorization"),
        ]:
            log_file_access(access_log, path, role, "paper contract freeze")

        universe_audit, universe_stats, universe = build_project_universe_audit(paths["project_universe"], config, access_log)
        instruments = set(universe["instrument"].replace("", pd.NA).dropna())
        qfq_audit, qfq_stats = build_qfq_audit(paths["qfq_root"], instruments, config)
        access_log.append({
            "run_id": RUN_ID, "stage": "freeze", "accessed_at": utc_now(), "artifact_path": rel(paths["qfq_root"]),
            "artifact_sha256_or_root_hash": qfq_audit.iloc[0]["root_inventory_hash"], "dataset_role": "qfq_OHLCV_root",
            "columns_read": "sample_headers_and_file_inventory", "derived_fields": "unit_inventory|filename_overlap",
            "outcome_columns_detected": "", "outcome_access_authorized": False, "selection_or_tuning_allowed": False,
            "purpose": "schema unit and coverage audit only", "access_gate": "pass",
        })
        benchmark_audit, benchmark_stats = build_benchmark_audit(paths["benchmark"], access_log)
        b2_audit, b2_gate = build_b2_lineage(paths, access_log)
        board_audit, board_stats = build_board_audit(paths, instruments, config, access_log)

        market_rules = read_csv_audited(paths["market_rule_registry"], access_log, "market_rule_registry", "tradability rules")
        observed_boards = set(universe["board_bucket"].dropna().astype(str))
        rule_boards = set(market_rules["board_bucket"].dropna().astype(str))
        market_verified = bool(len(market_rules)) and market_rules["human_verified"].map(bool_value).all()
        transfer_complete = market_rules[["transfer_fee_buy_bps", "transfer_fee_sell_bps"]].notna().all(axis=1).all()
        rule_coverage = observed_boards.issubset(rule_boards)
        tradability_gate = gate(market_verified and transfer_complete and rule_coverage)

        cost = read_csv_audited(paths["ep19_cost"], access_log, "EP19_preoutcome_cost", "cost inheritance")
        execution = read_csv_audited(paths["ep19_execution"], access_log, "EP19_preoutcome_execution", "execution inheritance")
        cost_ok = (
            len(cost) == 1 and float(cost.iloc[0]["commission_buy_bps"]) == 2.5
            and float(cost.iloc[0]["commission_sell_bps"]) == 2.5
            and float(cost.iloc[0]["minimum_commission_cny"]) == 5.0
            and str(cost.iloc[0]["stamp_tax_sell_bps_by_effective_date"]) == "2023-08-28:5.0"
            and float(cost.iloc[0]["slippage_bps"]) == 5.0
        )
        execution_ok = len(execution) == 1 and execution.iloc[0]["entry_price_source"] == "qfq_open_next_tradable_day"
        execution_gate = gate(cost_ok and execution_ok and tradability_gate == "pass")

        optional_rows: list[dict[str, Any]] = []
        optional_status: dict[str, bool] = {}
        for key, values in config.get("optional_exact_sources", {}).items():
            resolved = [topic_path(value) for value in values]
            status = bool(resolved) and all(path.exists() for path in resolved)
            optional_status[key] = status
            optional_rows.append({
                "run_id": RUN_ID, "source_group": key, "configured_path_n": len(resolved),
                "existing_path_n": sum(path.exists() for path in resolved), "status": gate(status),
                "observed_paths": "|".join(rel(path) for path in resolved),
            })
        optional_audit = pd.DataFrame(optional_rows)

        mde = compute_mde_grid(config)
        primary_mde = int(mde.loc[(mde["effect_monthly"] == 0.02) & (mde["monthly_volatility"] == 0.08), "n_required"].iloc[0])
        monthly_n = int(universe_stats["monthly_decision_n"])
        post_warmup_month_n = max(0, monthly_n - 47)
        board_gate = board_stats["board_proxy_gate"]
        residual_primary = "C3_RESMOM_R3_BOARD_ADAPTATION" if board_gate == "pass" else "C3A_RESMOM_R2_MARKET_ONLY"
        stateful_gate = "pass"
        cost_formula_gate = "pass"
        label_gate = "pass"
        economic_gate = "pass"
        power_gate = gate(primary_mde == 126)
        search_gate = "pass"
        configured_waivers = set(config.get("paper_material_waiver", {}).get("waived_source_ids", []))
        authorized_waivers = set(human_auth.get("material_waiver_source_ids", []))
        failed_source_ids = set(source_manifest.loc[source_manifest["content_validation_gate"].ne("pass"), "source_id"])
        material_waiver_valid = (
            bool_value(config.get("paper_material_waiver", {}).get("authorized"))
            and bool_value(human_auth.get("material_waiver_authorized"))
            and configured_waivers == authorized_waivers == failed_source_ids
            and not bool_value(config.get("paper_material_waiver", {}).get("local_full_text_claim_allowed_for_waived_sources"))
        )
        paper_material_gate = gate(
            source_manifest["allowlist_gate"].eq("pass").all()
            and (not failed_source_ids or material_waiver_valid)
        )
        paper_contract_gate = gate(paper_material_gate == "pass" and formula_registry["formula_gate"].eq("pass").all())
        project_data_gate = universe_stats["project_data_contract_gate"]
        benchmark_gate = benchmark_stats["benchmark_schema_and_calendar_gate"]
        r2_reachable = project_data_gate == "pass" and qfq_stats["qfq_unit_semantics_gate"] == "pass" and benchmark_gate == "pass" and post_warmup_month_n >= 60
        r3_reachable = r2_reachable and board_gate == "pass"
        c2_reachable = project_data_gate == "pass" and qfq_stats["qfq_unit_semantics_gate"] == "pass" and post_warmup_month_n >= 60
        residual_selection = r3_reachable if board_gate == "pass" else r2_reachable
        project_reachable = c2_reachable and residual_selection
        forward_gate = gate(project_data_gate == "pass" and benchmark_gate == "pass")
        forward_reachable = project_reachable and all(value == "pass" for value in (
            execution_gate, stateful_gate, cost_formula_gate, tradability_gate, label_gate, forward_gate,
        ))

        paper_universe = optional_status.get("wide_pit_market_cap_files", False)
        exact_history = post_warmup_month_n >= config["project_contract"]["paper_post_warmup_month_n_min"]
        trend_exact = qfq_stats["wide_qfq_status_gate"] == "pass" and paper_universe and optional_status.get("pit_earnings_to_price_files", False) and exact_history
        resmom_exact = trend_exact and optional_status.get("risk_free_return_files", False) and optional_status.get("china_ch3_factor_files", False)
        lowvol_exact = qfq_stats["wide_qfq_status_gate"] == "pass" and exact_history and paper_universe
        capabilities = {
            "exact_replication_reachable": trend_exact or resmom_exact or lowvol_exact,
            "trend_full_exact_reachable": trend_exact, "resmom_ch3_exact_reachable": resmom_exact,
            "lowvol_paper_exact_reachable": lowvol_exact, "C2_trendpv_adaptation_reachable": c2_reachable,
            "R2_market_adaptation_reachable": r2_reachable, "project_adaptation_reachable": project_reachable,
            "R3_board_adaptation_reachable": r3_reachable, "forward_beta_test_reachable": forward_reachable,
            "cnn_oracle_reachable": False,
        }
        outcome_gate = gate(
            not any(row["outcome_columns_detected"] for row in access_log)
            and not any(row["selection_or_tuning_allowed"] for row in access_log)
        )
        gates = {
            "human_restart_lineage_gate": "pass", "paper_material_gate": paper_material_gate,
            "paper_contract_gate": paper_contract_gate, "project_data_contract_gate": project_data_gate,
            "qfq_unit_semantics_gate": qfq_stats["qfq_unit_semantics_gate"],
            "benchmark_schema_and_calendar_gate": benchmark_gate, "execution_contract_gate": execution_gate,
            "stateful_portfolio_accounting_gate": stateful_gate, "cost_capacity_formula_gate": cost_formula_gate,
            "board_proxy_gate": board_gate, "residual_primary_selection_gate": gate(residual_selection),
            "B2_lineage_gate": b2_gate, "tradability_source_gate": tradability_gate,
            "label_censoring_freeze_gate": label_gate, "project_adaptation_gate": gate(project_reachable),
            "outcome_firewall_gate": outcome_gate, "economic_gate_freeze_gate": economic_gate,
            "power_gate_freeze": power_gate, "search_accounting_gate": search_gate,
            "forward_contract_gate": forward_gate, "manifest_hash_gate": "pass",
            "implementation_readiness_gate": gate(forward_reachable),
            "wide_qfq_status_gate": qfq_stats["wide_qfq_status_gate"],
            "paper_universe_gate": gate(paper_universe), "paper_exact_history_support_gate": gate(exact_history),
        }
        state, blocking = decision_state(gates, capabilities)

        write_text(freeze_root / "resolved_config.yaml", yaml.safe_dump(config, sort_keys=True, allow_unicode=True))
        write_json(freeze_root / "human_restart_authorization.json", {
            "run_id": RUN_ID, "contract_version": config["contract_version"],
            "primary_objective": "deployable_positive_beta", "incremental_alpha_required": False,
            "historical_sample_role": "design_contaminated_historical", "historical_support_claim_allowed": False,
            "EP19_B2_role": "frozen_daily_event_reference_not_project_arm",
            "formula_review_authorization_sha256": file_sha(cache / "formula_review_authorization.json"),
            "human_restart_lineage_gate": "pass", **human_auth,
        })
        upstream = pd.DataFrame([
            ("episode_id", EXPERIMENT_ID), ("superseded_draft_id", "20_ohlcv_directional_alpha_replication"),
            ("primary_objective", "deployable_positive_beta"), ("incremental_alpha_required", False),
            ("EP19_B2_role", "frozen_daily_event_reference_not_project_arm"),
        ], columns=["authority_field", "frozen_value"]).assign(run_id=RUN_ID, status="pass")
        write_csv(freeze_root / "upstream_scope_audit.csv", upstream[["run_id", "authority_field", "frozen_value", "status"]])

        input_roles = [
            "research_plan", "requirement", "project_universe", "qfq_root", "raw_ohlcv_root", "benchmark",
            "trading_calendar", "security_master", "sh_name_history_root", "market_rule_registry", "ep19_cost", "ep19_execution",
            "ep19_b2_selected_manifest", "ep19_b2_grid_manifest", "ep19_b2_feature_map", "ep19_b2_output_hashes",
            "ep19_b2_budget_registry", "ep19_board_index", "ep19_board_member", "ep19_board_readme",
            "ep19_board_mapping", "ep19_board_summary",
        ]
        artifact_rows = [artifact_row(paths[key], key) for key in input_roles]
        artifact_rows.extend([
            artifact_row(cache / "source_acquisition_manifest.csv", "paper_source_manifest"),
            artifact_row(cache / "paper_formula_registry_draft.csv", "paper_formula_registry"),
            artifact_row(cache / "formula_review_authorization.json", "formula_review_authorization"),
        ])
        input_audit = pd.DataFrame(artifact_rows).sort_values("artifact_role")
        already_logged_roles = {
            "research_plan", "requirement", "project_universe", "qfq_root", "benchmark", "market_rule_registry",
            "ep19_cost", "ep19_execution", "ep19_b2_selected_manifest", "ep19_b2_grid_manifest",
            "ep19_b2_feature_map", "ep19_b2_output_hashes", "ep19_b2_budget_registry",
            "ep19_board_index", "ep19_board_member",
        }
        for artifact in artifact_rows:
            role = str(artifact["artifact_role"])
            if role in already_logged_roles or role.startswith("paper_"):
                continue
            access_log.append({
                "run_id": RUN_ID, "stage": "freeze", "accessed_at": utc_now(),
                "artifact_path": artifact["artifact_path"],
                "artifact_sha256_or_root_hash": artifact["sha256_or_root_inventory_hash"],
                "dataset_role": role, "columns_read": "hash_or_root_inventory_only", "derived_fields": "",
                "outcome_columns_detected": "", "outcome_access_authorized": False,
                "selection_or_tuning_allowed": False, "purpose": "required input lineage binding",
                "access_gate": artifact["input_gate"],
            })
        write_csv(freeze_root / "input_artifact_audit.csv", input_audit)
        write_csv(freeze_root / "source_data_inventory.csv", input_audit[[
            "run_id", "artifact_role", "artifact_path", "artifact_kind", "file_n", "byte_size",
            "sha256_or_root_inventory_hash", "input_gate",
        ]])
        paper_sources_frozen = source_manifest.assign(run_id=RUN_ID).copy()
        paper_sources_frozen["material_waiver_authorized"] = paper_sources_frozen["source_id"].isin(configured_waivers)
        paper_sources_frozen["local_full_text_claim_allowed"] = paper_sources_frozen["content_validation_gate"].eq("pass")
        paper_sources_frozen["frozen_material_status"] = paper_sources_frozen.apply(
            lambda row: "validated_local_material" if row["content_validation_gate"] == "pass" else "waived_external_review_not_cached",
            axis=1,
        )
        write_csv(freeze_root / "paper_source_registry.csv", paper_sources_frozen[[
            "run_id", *SOURCE_COLUMNS, "material_waiver_authorized", "local_full_text_claim_allowed", "frozen_material_status",
        ]])
        write_csv(freeze_root / "paper_formula_registry.csv", formula_registry.assign(run_id=RUN_ID)[["run_id", *FORMULA_COLUMNS]])

        mapping = pd.DataFrame([
            ("monthly_total_return", "qfq close plus corporate-action bridge", "daily to month-end", "project_adaptation"),
            ("normalized_volume_shares", "qfq volume and source_volume_unit", "hands times 100; shares unchanged", "project_adaptation"),
            ("PIT_market_cap", "U_project.total_market_cap_cny", "known by usable date", "project_not_U_paper"),
            ("CSI300_monthly_total_return", "benchmark csi300 close", "calendar month-end", "project_adaptation"),
            ("static_2025_board_multi_hot", "EP19 dc_member", "non-PIT historical; frozen preknown forward", "project_adaptation"),
            ("raw_money", "raw OHLCV money", "ADV20 only", "capacity"),
        ], columns=["paper_or_contract_field", "local_source", "transform", "claim_role"])
        write_csv(freeze_root / "paper_to_local_field_mapping.csv", mapping.assign(run_id=RUN_ID)[["run_id", *mapping.columns]])
        arms = fixed_arm_registry(residual_primary)
        write_csv(freeze_root / "arm_role_registry.csv", arms)
        write_csv(freeze_root / "ep19_b2_preoutcome_lineage_audit.csv", b2_audit)
        write_csv(freeze_root / "project_universe_schema_and_coverage_audit.csv", universe_audit)
        write_csv(freeze_root / "qfq_schema_unit_and_coverage_audit.csv", qfq_audit)
        write_csv(freeze_root / "benchmark_schema_and_calendar_audit.csv", benchmark_audit)

        cost_audit = pd.DataFrame([
            ("EP19_cost_exact", cost_ok, True, gate(cost_ok)),
            ("EP19_next_open_execution_exact", execution_ok, True, gate(execution_ok)),
            ("transfer_fee_schedule_human_verified", market_verified, True, gate(market_verified)),
            ("execution_contract_gate", execution_gate, "pass", execution_gate),
        ], columns=["check_id", "observed_value", "required_value", "status"]).assign(run_id=RUN_ID)
        write_csv(freeze_root / "execution_and_cost_inheritance_audit.csv", cost_audit[["run_id", "check_id", "observed_value", "required_value", "status"]])
        tradability = pd.DataFrame([
            ("market_rule_rows_human_verified", market_verified, True, gate(market_verified)),
            ("observed_board_coverage", "|".join(sorted(observed_boards)), "|".join(sorted(rule_boards)), gate(rule_coverage)),
            ("transfer_fee_fields_complete", transfer_complete, True, gate(transfer_complete)),
            ("tradability_source_gate", tradability_gate, "pass", tradability_gate),
        ], columns=["check_id", "observed_value", "required_value", "status"]).assign(run_id=RUN_ID)
        write_csv(freeze_root / "tradability_source_and_schema_audit.csv", tradability[["run_id", "check_id", "observed_value", "required_value", "status"]])
        write_csv(freeze_root / "price_limit_rule_registry.csv", market_rules.assign(run_id=RUN_ID)[["run_id", *market_rules.columns]])
        write_csv(freeze_root / "execution_fill_and_exit_rule_freeze.csv", key_value_rows("execution_fill_exit", {
            "decision_time": "after_close_t", "entry_attempt": "next exchange-open executable open exactly once",
            "blocked_buy": "unfilled allocation remains cash", "blocked_exit": "position remains invested and consumes capital",
            "unknown_rule_or_bar": "fail closed no buy", "order_lot": "registry minimum/increment; floor shares",
            "active_weight_rescaling_allowed": False, "entry_price": "qfq open linked to raw tradability",
        }))
        write_csv(freeze_root / "optional_exact_source_availability_audit.csv", optional_audit)
        write_csv(freeze_root / "ep19_2025_static_board_proxy_audit.csv", board_audit)
        write_csv(freeze_root / "universe_role_and_denominator_freeze.csv", pd.DataFrame([
            {"run_id": RUN_ID, "universe_id": "U_project", "definition": "PIT top-N 400/100 executable", "claim_role": "project adaptation", "paper_exact_allowed": False},
            {"run_id": RUN_ID, "universe_id": "U_paper", "definition": "paper-wide A-share universe", "claim_role": "paper exact only", "paper_exact_allowed": paper_universe},
        ]))
        write_csv(freeze_root / "return_and_cash_semantics_freeze.csv", key_value_rows("return_cash", {
            "primary_horizon": "one_calendar_month", "primary_return": "cash-inclusive full-capital net NAV return",
            "primary_return_formula": "month_end_NAV_t/month_end_NAV_t_minus_1-1", "unallocated_weight": "cash",
            "cash_hurdle_monthly": 0.0, "matched_alpha_required": False, "scale_independence_required": False,
            "risk_source_attribution_required": True,
        }))
        write_csv(freeze_root / "stateful_portfolio_accounting_and_nav_freeze.csv", key_value_rows("stateful_nav", {
            "portfolio_accounting_mode": "one_independent_stateful_NAV_ledger_per_arm",
            "initial_AUM_cny": config["economic_risk"]["reference_portfolio_notional_cny"],
            "capital_injection_allowed": False, "monthly_reset_allowed": False,
            "blocked_exit_valuation": "last valid qfq-linked mark; remains invested and consumes capital",
            "corporate_action_bridge": "verified recovery else conservative -100% terminal return",
            "gross_shadow_ledger": "same decisions/fills/shares; cost savings not reinvested",
            "stateful_portfolio_accounting_gate": stateful_gate,
        }))
        write_csv(freeze_root / "turnover_cost_capacity_formula_freeze.csv", key_value_rows("turnover_cost_capacity", {
            "ADV20": "mean raw money over 20 exchange-open sessions ending before order",
            "missing_raw_bar": "zero if listed; prelisting unavailable", "minimum_ADV_sessions": 20,
            "attempted_one_way_turnover": "(intended_buy+intended_sell)/(2*pretrade_NAV)",
            "realized_one_way_turnover": "(executed_buy+executed_sell)/(2*pretrade_NAV)",
            "transaction_cost_return": "commission+stamp+transfer+slippage over pretrade_NAV",
            "break_even_cost_multiple": "mean(gross-cash_hurdle)/mean(transaction_cost_return)",
            "zero_cost_behavior": "undefined", "capacity_based_scaling_allowed": False,
            "maximum_ADV_participation_rate": config["economic_risk"]["maximum_ADV_participation_rate"],
            "cost_capacity_formula_gate": cost_formula_gate,
        }))

        warmup_rows = []
        for _, formula in formula_registry.iterrows():
            warmup_n = 47 if "RESMOM" in formula["formula_id"] else 16 if "TREND" in formula["formula_id"] else 36 if "LOWVOL" in formula["formula_id"] else 12
            observed = max(0, monthly_n - warmup_n)
            warmup_rows.append({
                "run_id": RUN_ID, "formula_id": formula["formula_id"], "universe_id": formula["universe_rule"],
                "warmup_rule": formula["warmup_rule"], "observed_calendar_month_n": monthly_n,
                "post_warmup_month_n": observed, "historical_sample_role": "design_contaminated_historical",
                "historical_support_claim_allowed": False, "early_block_month_n": observed // 2,
                "late_block_month_n": observed - observed // 2, "history_support_gate": "design_only",
            })
        write_csv(freeze_root / "warmup_and_monthly_support_audit.csv", pd.DataFrame(warmup_rows).sort_values("formula_id"))

        go_specs = [
            ("wide_qfq_status_gate", qfq_stats["wide_qfq_status_gate"], "U_paper price-side candidate", "U_project only", ""),
            ("wide_pit_market_cap_gate", gate(optional_status.get("wide_pit_market_cap_files", False)), "exact size capable", "exact blocked", ""),
            ("pit_ep_timing_gate", gate(optional_status.get("pit_earnings_to_price_files", False)), "Trend/value exact capable", "exact blocked", "C2_TRENDPV_RAW_ADAPTATION"),
            ("historical_pit_industry_gate", gate(optional_status.get("historical_pit_industry_files", False)), "industry exact", "2025 proxy", residual_primary),
            ("board_proxy_gate", board_gate, "R3 control", "fallback R2", "C3A_RESMOM_R2_MARKET_ONLY"),
            ("risk_free_vintage_gate", gate(optional_status.get("risk_free_return_files", False)), "excess-return exact", "raw beta", residual_primary),
            ("ch3_factor_vintage_gate", gate(optional_status.get("china_ch3_factor_files", False)), "CH3 exact", "R2/R3", residual_primary),
            ("paper_exact_history_support_gate", gate(exact_history), "paper diagnostic calendar", "pipeline QA", ""),
            ("project_adaptation_gate", gate(project_reachable), "20B/20C specification", "20A blocked", ""),
            ("forward_contract_gate", forward_gate, "forward beta test", "20A blocked", ""),
            ("cnn_training_support_gate", "fail", "20F evaluable", "underpowered", ""),
        ]
        go_rows = [{
            "run_id": RUN_ID, "gate_id": gate_id, "route_id": gate_id.replace("_gate", ""),
            "data_requirement": gate_id, "required_paths": "see input_artifact_audit", "required_fields": "see contract",
            "minimum_coverage": "contract threshold", "observed_paths": "see input_artifact_audit",
            "observed_fields": "audited", "observed_coverage": "see dedicated audit", "status": status,
            "blocking_scope": blocked, "highest_allowed_role": highest, "blocked_arms": blocked,
            "fallback_arm": fallback, "evidence_paths": "freeze dedicated audit", "evidence_hashes": "sealed manifest",
            "reason": "mechanical pre-outcome availability gate",
        } for gate_id, status, highest, blocked, fallback in go_specs]
        write_csv(freeze_root / "ep20a_data_replication_go_no_go.csv", pd.DataFrame(go_rows))

        multiple = pd.DataFrame([{
            "run_id": RUN_ID, "arm_id": row["arm_id"],
            "family_id": "primary" if row["arm_role"] == "primary" else row["arm_role"], "role": row["arm_role"],
            "primary_hypothesis_count": 2, "correction": "Holm step-down", "alpha_familywise": 0.05,
            "promotion_eligible": row["promotion_eligible"],
            "deferred_gate": "historical_beta_design_gate" if row["arm_id"] == "D1_FIP_INCREMENT" else "",
            "residual_primary_arm": residual_primary, "board_proxy_gate": board_gate,
            "selection_basis": "preoutcome_data_availability_only",
        } for _, row in arms.iterrows()])
        write_csv(freeze_root / "multiple_testing_and_search_accounting_freeze.csv", multiple)
        write_csv(freeze_root / "positive_beta_economic_and_risk_gate_freeze.csv", key_value_rows("economic_risk", {
            "primary_objective": "deployable_positive_beta", "incremental_alpha_required": False,
            "cash_hurdle_monthly": 0.0, "confirmatory_CI_lower_floor": 0.0,
            "Holm_familywise_alpha": 0.05, "Bonferroni_one_sided_per_arm_alpha": 0.025,
            "positive_month_rate_role": "diagnostic_only", "right_tail_role": "secondary diagnostic",
            "one_month_upper_tail_contribution_10": "monthly top return decile positive capital contribution / all positive contribution; undefined if denominator zero",
            "big_winner_exposure_ratio_50_120": "monthly capital-weighted sleeve MFE120>=50% rate / same-date executable U_project equal-weight rate",
            "right_tail_undefined_month_rule": "report undefined count; never replace undefined with zero",
            "monthly_ES10_loss_cap": config["economic_risk"]["monthly_ES10_loss_cap"],
            "monthly_p10_return_floor": config["economic_risk"]["monthly_p10_return_floor"],
            "max_drawdown_cap": config["economic_risk"]["max_drawdown_cap"],
            "max_drawdown_formula": "max_t(1-daily_NAV_t/running_max_daily_NAV_through_t)",
            "single_instrument_weight_cap": config["economic_risk"]["single_instrument_weight_cap"],
            "top10_instrument_weight_cap": config["economic_risk"]["top10_instrument_weight_cap"],
            "minimum_effective_holdings": config["economic_risk"]["minimum_effective_holdings"],
            "realized_effective_holdings_formula": "sum(actual_position_weight)^2/sum(actual_position_weight^2); zero when invested weight zero",
            "minimum_effective_holdings_gate": "p10 across evaluable rebalances >= 20",
            "locked_capital_weight": "blocked-exit position market value / pretrade NAV",
            "risk_provisional_floor": "ES10 and p10 cannot pass confirmatory risk gate before 20 complete months",
            "parameter_source": "human_positive_beta_risk_budget_20A_v1", "economic_gate_freeze_gate": economic_gate,
        }))
        write_csv(freeze_root / "forward_mde_and_power_freeze.csv", mde)
        cnn_month_min = sum(config["cnn_support"][key] for key in (
            "train_calendar_month_n_min", "validation_calendar_month_n_min", "frozen_test_calendar_month_n_min",
        ))
        write_csv(freeze_root / "cnn_training_support_preflight.csv", pd.DataFrame([{
            "run_id": RUN_ID, "observed_total_calendar_month_n": monthly_n,
            "minimum_disjoint_calendar_month_n": cnn_month_min, **config["cnn_support"],
            "strict_time_order": True, "random_cross_time_split_allowed": False,
            "cnn_training_support_gate": "fail", "cnn_status": "cnn_underpowered_not_evaluable",
            "cnn_oracle_reachable": False, "daily_ohlcv_closure_claim_allowed_from_cnn": False,
        }]))
        write_csv(freeze_root / "forward_boundary_and_support_freeze.csv", key_value_rows("forward_boundary", {
            "contract_freeze_timestamp_source": "freeze_manifest_20a.json.sealed_at_utc",
            "first_forward_decision_rule": "first scheduled month-end strictly after seal",
            "backfill_forward_allowed": False, "interim_month_floor": 6, "minimum_evidence_month_floor": 12,
            "confirmatory_month_floor": primary_mde, "confirmatory_calendar_earliest_estimate": "approximately 2037 Q1",
        }))
        write_csv(freeze_root / "forward_evaluability_preflight.csv", pd.DataFrame([{
            "run_id": RUN_ID, "local_data_max_date": universe_stats["date_max"],
            "boundary_rule": "strictly_after_freeze_manifest_sealed_at_utc", "complete_forward_month_n": 0,
            "preflight_state": "forward_not_yet_observed_at_freeze", "outcome_value_read": False,
            "estimated_6_month_interim": "2027 H1 if freeze in 2026-08",
            "estimated_12_month_minimum_evidence": "2027 H2", "estimated_126_month_confirmatory": "approximately 2037 Q1",
        }]))
        write_csv(freeze_root / "label_completion_and_censoring_rule_freeze.csv", key_value_rows("label_censoring", {
            "primary_label": "next calendar-month continuous stateful NAV return",
            "label_complete": "every component has valid month-end mark or conservative terminal resolution",
            "entry_blocked": "cash remains in NAV", "exit_blocked": "position remains invested; consumes capital",
            "missing_delisting_recovery": "-100% conservative terminal return",
            "unknown_valuation_bridge": "complete month count does not advance",
            "maximum_delay_censoring_allowed": False, "external_replacement_capital_allowed": False,
            "label_censoring_freeze_gate": label_gate,
        }))
        write_csv(freeze_root / "outcome_access_audit.csv", pd.DataFrame(access_log), OUTCOME_ACCESS_COLUMNS)

        contract = {
            "run_id": RUN_ID, "experiment_id": EXPERIMENT_ID, "phase_id": PHASE_ID,
            "contract_version": config["contract_version"], "decision_state_preseal": state,
            "gates": gates, "capabilities": capabilities, "residual_primary_arm": residual_primary,
            "n_required_primary": primary_mde, "blocking_reasons": blocking,
            "outcome_read_count": 0, "selection_or_tuning_allowed_count": 0,
            "EP19_preoutcome_rule_artifact_read_count": 5, "historical_support_claim_allowed": False,
            "material_waiver_source_ids": sorted(configured_waivers),
            "material_waiver_valid": material_waiver_valid,
            "authorizations": config["authorizations"],
        }
        write_json(freeze_root / "contract_freeze_20a.json", contract)
        write_text(freeze_root / "20A_contract_freeze.md", f"""# 20A 预 outcome 合同冻结

- 状态：`{state}`
- 目标：可部署的正 beta；不要求 matched alpha。
- residual primary：`{residual_primary}`
- exact replication reachable：`{str(capabilities['exact_replication_reachable']).lower()}`
- project adaptation reachable：`{str(project_reachable).lower()}`
- forward beta test reachable：`{str(forward_reachable).lower()}`
- outcome 读取：0
- 阻断原因：`{blocking or 'none'}`

本文件只冻结 pre-outcome 合同，不评价任何策略收益。
""")

        for name in FREEZE_ARTIFACT_NAMES:
            path = freeze_root / name
            if path.suffix == ".csv" and name != "outcome_access_audit.csv":
                forbidden = forbid_outcome_columns(pd.read_csv(path, nrows=0).columns)
                if forbidden:
                    raise PermissionError(f"forbidden output columns in {name}: {forbidden}")
        bundle_hash = seal_bundle(
            freeze_root, manifest_path.name, hashes_path.name, FREEZE_ARTIFACT_NAMES,
            {"run_id": RUN_ID, "experiment_id": EXPERIMENT_ID, "phase_id": PHASE_ID, "contract_version": config["contract_version"]},
        )
        return {"freeze_root": str(freeze_root), "freeze_bundle_hash": bundle_hash, "status": "sealed"}
    except Exception:
        if not manifest_path.exists():
            write_text(
                freeze_root / "FREEZE_FAILED_DO_NOT_REUSE.txt",
                "Freeze failed before sealing. Diagnose, remove this unsealed directory, and rerun cleanly.\n",
            )
        raise


DECISION_COLUMNS = [
    "run_id", "contract_version", "decision_state", "primary_objective", "incremental_alpha_required",
    "human_restart_lineage_gate", "paper_material_gate", "paper_contract_gate", "project_data_contract_gate",
    "qfq_unit_semantics_gate", "benchmark_schema_and_calendar_gate", "execution_contract_gate",
    "stateful_portfolio_accounting_gate", "cost_capacity_formula_gate", "board_proxy_gate",
    "residual_primary_selection_gate", "residual_primary_arm", "B2_lineage_gate", "tradability_source_gate",
    "label_censoring_freeze_gate", "project_adaptation_gate", "outcome_firewall_gate", "economic_gate_freeze_gate",
    "power_gate_freeze", "search_accounting_gate", "forward_contract_gate", "manifest_hash_gate",
    "implementation_readiness_gate", "wide_qfq_status_gate", "paper_universe_gate", "paper_exact_history_support_gate",
    "exact_replication_reachable", "trend_full_exact_reachable", "resmom_ch3_exact_reachable",
    "lowvol_paper_exact_reachable", "C2_trendpv_adaptation_reachable", "R2_market_adaptation_reachable",
    "project_adaptation_reachable", "R3_board_adaptation_reachable", "forward_beta_test_reachable",
    "cnn_oracle_reachable", "historical_sample_role", "historical_support_claim_allowed",
    "primary_portfolio_accounting_mode", "primary_return_semantics", "board_snapshot_age_rule",
    "first_forward_decision_rule", "forward_interim_month_floor", "forward_minimum_evidence_month_floor",
    "forward_confirmatory_support_month_floor", "n_required_primary", "confirmatory_calendar_earliest_estimate",
    "next_allowed_requirement", "next_requirement_generation_authorized", *AUTHORIZATION_COLUMNS,
    "freeze_bundle_hash", "blocking_reasons",
]


def finalize_stage(config_path: str | Path = CONFIG_PATH) -> dict[str, str]:
    config = load_config(config_path)
    output_root = resolve_output_root(config)
    freeze_root = output_root / "freeze"
    verify_bundle(freeze_root, "freeze_manifest_20a.json", "freeze_output_hashes_20a.json", FREEZE_ARTIFACT_NAMES)
    freeze_bundle_hash = file_sha(freeze_root / "freeze_output_hashes_20a.json")
    final_manifest = output_root / "manifest_20a_paper_lineage_data_and_replication_contract.json"
    final_hashes = output_root / "output_hashes_20a_paper_lineage_data_and_replication_contract.json"
    final_names = ["20A_preoutcome_contract_decision.csv", "20A_paper_lineage_data_and_replication_contract_report.md"]
    if final_manifest.exists() or final_hashes.exists():
        verify_bundle(output_root, final_manifest.name, final_hashes.name, final_names)
        return {"output_root": str(output_root), "status": "already_finalized"}

    # All reads below are inside the already sealed freeze bundle; no raw/config market input is consulted.
    contract = read_json(freeze_root / "contract_freeze_20a.json")
    freeze_manifest = read_json(freeze_root / "freeze_manifest_20a.json")
    gates = dict(contract["gates"])
    capabilities = dict(contract["capabilities"])
    gates["manifest_hash_gate"] = "pass"
    state, blocking = decision_state(gates, capabilities)
    auth = contract["authorizations"]
    row: dict[str, Any] = {
        "run_id": RUN_ID, "contract_version": contract["contract_version"], "decision_state": state,
        "primary_objective": "deployable_positive_beta", "incremental_alpha_required": False,
        **gates, **capabilities, "residual_primary_arm": contract["residual_primary_arm"],
        "historical_sample_role": "design_contaminated_historical", "historical_support_claim_allowed": False,
        "primary_portfolio_accounting_mode": "continuous_no_injection_stateful_NAV_per_arm",
        "primary_return_semantics": "calendar-month cash-inclusive full-capital net NAV return",
        "board_snapshot_age_rule": "decision_month - 2025-01",
        "first_forward_decision_rule": "first scheduled project month-end strictly after seal timestamp",
        "forward_interim_month_floor": 6, "forward_minimum_evidence_month_floor": 12,
        "forward_confirmatory_support_month_floor": contract["n_required_primary"],
        "n_required_primary": contract["n_required_primary"],
        "confirmatory_calendar_earliest_estimate": "approximately 2037 Q1",
        "next_allowed_requirement": auth["next_allowed_requirement"],
        "next_requirement_generation_authorized": auth["next_requirement_generation_authorized"],
        "next_requirement_execution_authorized": False, "policy_training_authorized": False,
        "policy_replay_authorized": False, "portfolio_optimization_authorized": False,
        "deployment_authorized": False, "freeze_bundle_hash": freeze_bundle_hash,
        "blocking_reasons": blocking,
    }
    write_csv(output_root / final_names[0], pd.DataFrame([row]), DECISION_COLUMNS)

    go = pd.read_csv(freeze_root / "ep20a_data_replication_go_no_go.csv")
    board = pd.read_csv(freeze_root / "ep19_2025_static_board_proxy_audit.csv").iloc[0]
    source = pd.read_csv(freeze_root / "paper_source_registry.csv")
    formula = pd.read_csv(freeze_root / "paper_formula_registry.csv")
    access = pd.read_csv(freeze_root / "outcome_access_audit.csv")
    go_table = go[["gate_id", "status", "highest_allowed_role", "fallback_arm"]].to_markdown(index=False)
    detected_n = int(access["outcome_columns_detected"].fillna("").astype(str).str.len().gt(0).sum())
    selection_n = int(access["selection_or_tuning_allowed"].map(bool_value).sum())
    local_material_n = int(source["frozen_material_status"].eq("validated_local_material").sum())
    waived_sources = source.loc[source["material_waiver_authorized"].map(bool_value), "source_id"].tolist()
    waived_text = "、".join(waived_sources) if waived_sources else "无"
    report = f"""# EP20A 论文血缘、数据与复制合同报告

## 一页结论

- 决策状态：`{state}`
- residual primary：`{contract['residual_primary_arm']}`
- project adaptation reachable：`{str(capabilities['project_adaptation_reachable']).lower()}`
- forward beta test reachable：`{str(capabilities['forward_beta_test_reachable']).lower()}`
- exact replication reachable：`{str(capabilities['exact_replication_reachable']).lower()}`；它不是 20A 成功的必要条件。
- 冻结时间：`{freeze_manifest['sealed_at_utc']}`
- outcome 字段读取数：`{detected_n}`；selection/tuning 授权读取数：`{selection_n}`。
- 阻断原因：`{blocking or 'none'}`

EP20 的 primary objective 是可部署的正 beta，不要求 matched alpha。

Scale matching 只解释收益来源，不是正 beta 的淘汰门。

2017–2026-05 的本地历史已经被 topic 反复消费，只能提供设计证据；唯一可信支持来自 post-freeze forward。

## 论文与公式血缘

本地缓存并通过内容校验的 allowlisted full-text/appendix 为 `{local_material_n}/{len(source)}` 份；人工核验后的 formula registry 有 `{len(formula)}` 行。Material waiver source 为：`{waived_text}`。这两项只记录“人工公式核验已完成但远端正文暂未缓存”，没有本地 full-text/hash claim，也不提高 exact replication claim。每个公式行仍绑定 source、page/equation、lag、warm-up、missing、tie 与 weighting 实现选择。20A 不以 requirement 摘要循环证明论文公式。

## 数据、denominator 与复制上限

U_project 的 top-N 截面不能冒充论文的全 A 股 U_paper。

全市场 qfq 文件只证明价格侧候选可用，不能替代宽截面 PIT market-cap、E/P、historical industry、risk-free 或 CH-3 vintage。所有本地历史都是 design-contaminated；历史结果未来只可用于设计，不可升级为 support。

## Exact 与 adaptation 路由

{go_table}

Exact route 失败不等于 project adaptation 失败。Residual primary 只由 pre-outcome board availability 决定；board gate 失败时机械回退 R2，primary family 仍固定为 2，不能按收益切换。

## 2025 板块代理

EP19 2025 板块数据是冻结的 multi-label concept-board proxy，不是 historical PIT industry。

原始 index `{int(board['raw_index_row_n'])}` 行、member `{int(board['raw_member_row_n'])}` 行、去重后 board columns `{int(board['eligible_board_column_n'])}`，U_project overlap rate `{float(board['overlap_rate']):.4f}`。Snapshot age 固定为 `decision_month - 2025-01`；未来更新 snapshot 必须建立新 cohort，旧新 cohort 不得混池。

## 执行、NAV、成本、容量与风险

每个 arm 只有一条 continuous no-injection NAV ledger；blocked exit 必须继续占用真实资本。

Primary return 是固定 calendar-month、cash-inclusive、full-capital、net NAV return。Blocked buy 留现金；blocked exit 继续 mark 并占资本；delisting recovery 不可得时使用 -100% conservative resolution。Attempted/realized turnover、ADV20、transfer fee、break-even multiple、daily-NAV drawdown 与集中度口径均已 pre-outcome 冻结。

EP19 daily B2 reference 不等于 EP20 B2 month-end adaptation；EP19 effect size 不得直接转移。

C5R2 只可在同一 month-end B2 candidates 内计算 linear p70，阈值相等者删除，被 trim 权重留现金；不得跨日期估计，也不得继承 19B3 的绝对阈值或收益。

## Power、CNN 与 forward

MDE 的证据单位是 distinct complete decision months。Effect=2%、long-run monthly volatility=8%、Holm worst-case alpha=2.5%、power=80%，得到 `n_required_primary=126`。6–11 月只是 interim；12–125 月只是 minimum directional evidence，不是 confirmatory support；达到 126 月才可评价 Holm/HAC、simultaneous lower bound 与 early/late direction，日历下限预计约 2037 Q1。

CNN 必须有严格时间分离的 72/18/24 个月。任何支持门不足均固定为 `cnn_underpowered_not_evaluable`，不能据此关闭日频 OHLCV 主线。

## 授权边界

20A 没有评价任何信号收益，也没有授权 20B 执行、policy、optimization 或 deployment。

20A 只授权生成 `{auth['next_allowed_requirement']}`；其执行仍为 false。
"""
    write_text(output_root / final_names[1], report)
    final_bundle_hash = seal_bundle(
        output_root, final_manifest.name, final_hashes.name, final_names,
        {"run_id": RUN_ID, "contract_version": contract["contract_version"], "freeze_bundle_hash": freeze_bundle_hash},
    )
    return {"output_root": str(output_root), "final_bundle_hash": final_bundle_hash, "status": "finalized"}


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.stage == "acquire-sources":
        outputs = acquire_sources_stage(args.config, offline=args.offline)
    elif args.stage == "freeze":
        outputs = freeze_stage(args.config)
    else:
        outputs = finalize_stage(args.config)
    print(json.dumps({key: str(value) for key, value in outputs.items()}, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
