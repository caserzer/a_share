from __future__ import annotations

import functools
import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[6]
EXP = ROOT / "topics/02_AFML_BIG_WINNER/experiments/pending/18_payoff_state_representation_research"
SCRIPT = EXP / "src/run_18c_refresh_payoff_state_separability_diagnostic.py"
CONFIG = EXP / "configs/config_18c_refresh_payoff_state_separability_diagnostic.yaml"
REQ = EXP / "requirement_18c_refresh_payoff_state_separability_diagnostic.md"


def load_runner():
    spec = importlib.util.spec_from_file_location("run_18c_refresh_test_module", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


r = load_runner()


@functools.lru_cache(maxsize=1)
def context():
    return r.run(CONFIG, mode="full")


def test_18c_refresh_fails_closed_when_18e_local_cache_matrix_is_missing():
    result = context()
    decision = result["decision"].iloc[0]
    input_audit = result["input_artifact_audit"]

    matrix_row = input_audit.loc[input_audit["artifact_key"].eq("eighteen_e_refreshed_matrix")].iloc[0]
    if matrix_row["read_status"] == "missing":
        assert decision["decision_state"] == "18C_refresh_upstream_18e_contract_blocked"
        assert decision["next_allowed_requirement"] == "none"
        assert "missing_local_cache_refreshed_matrix" in matrix_row["blocking_reason"]
        assert "rerun_18e_full_to_regenerate" in matrix_row["blocking_reason"]
    else:
        assert matrix_row["cache_hash_validated"] == "exact_match"

    for col in r.AUTH_FALSE_COLUMNS:
        assert bool(decision[col]) is False


def test_18c_refresh_uses_distinct_output_namespace_and_does_not_overwrite_initial_18c():
    context()
    outputs = r.output_paths()
    assert "18C_refresh_payoff_state_separability_diagnostic" in str(outputs["decision"])
    assert outputs["report"].name == "payoff_state_separability_refresh_report.md"
    assert outputs["manifest"].name == "18C_refresh_payoff_state_separability_diagnostic_manifest.json"
    assert outputs["decision"].exists()
    assert outputs["input_artifact_audit"].exists()
    assert outputs["upstream_18e_handoff_audit"].exists()
    assert outputs["decile_curve"].stat().st_size > 0
    assert outputs["score_surface"].stat().st_size > 0


def test_18c_refresh_family_removal_sensitivity_schema_is_explicit():
    result = context()
    family = result["family_removal_sensitivity"]
    required = {
        "sensitivity_id",
        "split_bucket",
        "model_id",
        "removal_type",
        "removed_feature_family_id",
        "removed_feature_n",
        "removed_feature_names",
        "base_rank_ic_spearman",
        "sensitivity_rank_ic_spearman",
        "rank_ic_retention_rate",
        "family_role",
        "refresh_family_flag",
        "risk_only_focus_flag",
        "sensitivity_status",
        "blocking_reason",
    }
    assert required.issubset(set(family.columns))

    requirement_text = REQ.read_text(encoding="utf-8")
    assert "### 9.1 `family_removal_sensitivity.csv`" in requirement_text
    assert "family_M1_removed" in requirement_text
    assert "family_M5_removed" in requirement_text
