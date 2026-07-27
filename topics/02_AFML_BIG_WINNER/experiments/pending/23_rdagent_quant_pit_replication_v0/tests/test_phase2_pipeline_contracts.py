from __future__ import annotations

import json

import pandas as pd

from run_23i_collect_rdagent_trace import (
    RAW_FALLBACK_DECISION_RE,
    RAW_REPLACE_DECISION_RE,
)
from run_23k_matched_model_confirmation import training_config
from run_23l_execution_big_winner_bridge import state_pairs
from run_23m_joint_scheduler_gate import first_truth, truth


def test_factor_feedback_decision_regex_excludes_prompt_placeholder() -> None:
    text = (
        '"Replace Best Result": "yes or no"\n'
        '"Replace Best Result": "yes"\n'
        '"Replace Best Result": "no"\n'
    )
    assert [
        match.group("value")
        for match in RAW_REPLACE_DECISION_RE.finditer(text)
    ] == ["yes", "no"]


def test_fallback_feedback_decision_regex_accepts_bool_and_string() -> None:
    text = '"Decision": true\n"Decision": "no"\n'
    assert [
        match.group("value").strip('"')
        for match in RAW_FALLBACK_DECISION_RE.finditer(text)
    ] == ["true", "no"]


def test_model_training_config_matches_runner_override_contract() -> None:
    base = {
        "model_attribution": {
            "n_epochs": 100,
            "learning_rate": 0.001,
            "early_stop": 12,
            "batch_size": 256,
            "weight_decay": 0.0001,
        }
    }
    candidate = pd.Series(
        {
            "training_hyperparameters_json": json.dumps(
                {
                    "n_epochs": 25,
                    "lr": 0.0005,
                    "early_stop": 8,
                    "batch_size": 128,
                    "weight_decay": 0.002,
                }
            )
        }
    )
    assert training_config(base, candidate) == {
        "n_epochs": 25,
        "lr": 0.0005,
        "early_stop": 8,
        "batch_size": 128,
        "weight_decay": 0.002,
    }


def test_23l_pairs_only_matched_own_start() -> None:
    states = {
        "a20_static",
        "a20_evolved",
        "a157_static",
        "a20_model_baseline",
        "a20_model_evolved",
    }
    assert state_pairs(states) == [
        ("a20", "a20_static", "a20_evolved"),
        (
            "a20_model",
            "a20_model_baseline",
            "a20_model_evolved",
        ),
    ]


def test_joint_gate_truth_does_not_infer_missing_key() -> None:
    assert truth("supported")
    assert truth("YES")
    assert not truth("blocked")
    assert first_truth({"b": True}, ["a", "b"])
    assert not first_truth({}, ["a", "b"])
