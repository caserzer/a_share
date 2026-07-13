from __future__ import annotations

import copy
import csv
import importlib.util
import inspect
import json
import math
import shutil
from pathlib import Path

import numpy as np
import pytest


EPISODE = Path(__file__).resolve().parents[1]
RUNNER_PATH = (
    EPISODE / "src/run_21a_paper_lineage_pit_data_and_architecture_contract.py"
)
SPEC = importlib.util.spec_from_file_location("ep21a_runner", RUNNER_PATH)
assert SPEC and SPEC.loader
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


@pytest.fixture()
def config() -> dict:
    return copy.deepcopy(runner.load_config())


def _allowed_source_rows(config: dict) -> list[dict]:
    return [
        {
            "inside_allowlist": True,
            "identity_status": "pass",
            "source_id": source["source_id"],
        }
        for source in config["source_allowlist"]["acquisition_sources"]
    ]


def _all_true_contract() -> dict:
    return {
        "schema_version": "21A_schema_v2",
        "run_id": runner.RUN_ID,
        "contract_version": runner.CONTRACT_VERSION,
        "paper_sha256": "a" * 64,
        "primary_feature_route_id": "ALPHA158_NO_VWAP_REGISTERED_ADAPTATION",
        "primary_feature_route_class": "registered_primary_route_adaptation",
        "feature_expression_sha256": "b" * 64,
        "selected_batch_size": 16,
        "historical_sample_role": "design_contaminated_historical",
        "historical_support_claim_allowed": False,
        "forward_confirmatory_required_complete_days": 291,
        "next_allowed_requirement": "requirement_21b_alpha158_sequence_baseline_benchmark.md",
        "official_code_status": "not_disclosed_in_allowlisted_sources",
        "preoutcome_hard_counts": {
            "outcome_columns_detected_count": 0,
            "outcome_formula_executed_count": 0,
            "real_label_materialization_count": 0,
            "real_model_score_count": 0,
            "selection_or_tuning_allowed_count": 0,
            "historical_holdout_outcome_access_count": 0,
        },
        "capabilities": {
            "official_code_available": False,
            "paper_appendix_available": False,
            "alpha158_exact_local_materialization": False,
            "confirmed_terminal_price_resolution_available": False,
            "gpu_batch_size_mechanically_reduced": True,
            "exact_replication_reachable": False,
        },
        "gate_check_statuses": {
            gate_id: {check_id: True for check_id in check_ids}
            for gate_id, check_ids in runner.GATE_CHECKS.items()
        },
    }


def _make_freeze_bundle(root: Path, config: dict) -> str:
    freeze = root / "freeze"
    freeze.mkdir(parents=True)
    for relative in runner.FREEZE_RELATIVE_PATHS:
        if relative.endswith(
            ("freeze_bundle_manifest.json", "freeze_output_hashes_21a.json")
        ):
            continue
        path = root / relative
        filename = path.name
        if filename in runner.TABLE_SCHEMAS:
            runner.write_csv(path, [], runner.TABLE_SCHEMAS[filename])
        elif filename == "contract_freeze_21a.json":
            runner.write_json(path, _all_true_contract())
        elif path.suffix == ".json":
            runner.write_json(
                path,
                {"run_id": runner.RUN_ID, "contract_version": runner.CONTRACT_VERSION},
            )
        elif path.suffix == ".yaml":
            runner.write_text(path, "identity:\n  run_id: fixture")
        else:
            runner.write_text(path, "fixture")
    return runner.seal_freeze_bundle(root, config, "2026-07-13T00:00:00.000000Z")


def test_identity_paths_and_config_contract(config: dict) -> None:
    assert config["identity"]["run_id"] == runner.RUN_ID
    assert config["identity"]["contract_version"] == runner.CONTRACT_VERSION
    assert list(config) == runner.RESOLVED_CONFIG_TOP_LEVEL_KEYS
    assert config["paths"]["runner"].endswith(RUNNER_PATH.name)
    assert config["paths"]["test"].endswith(Path(__file__).name)
    assert runner.resolve_output_root(config) == runner.OUTPUT_ROOT
    assert len(runner.CRITICAL_GATES) == 28
    assert set(runner.CRITICAL_GATES) == set(runner.GATE_CHECKS)


def test_all_aliases_are_repository_relative(config: dict) -> None:
    aliases = list(config["paths"].values()) + [config["output"]["output_root"]]
    assert all(not Path(value).is_absolute() for value in aliases)
    assert all(
        "/home/xiaolv" not in value and not value.startswith("file://")
        for value in aliases
    )
    assert config["source_allowlist"]["official_code_candidate_urls"] == []
    assert config["source_allowlist"]["official_appendix_candidate_urls"] == []


def test_research_plan_and_paper_hash_page_contract(config: dict) -> None:
    paths = runner.resolve_paths(config)
    expected = config["input_hash_expectations"]
    assert runner.file_sha(paths["research_plan"]) == expected["research_plan_sha256"]
    assert runner.file_sha(paths["paper"]) == expected["paper_sha256"]
    assert runner.pdf_page_count(paths["paper"]) == expected["paper_page_count"] == 5


@pytest.mark.parametrize(
    "field,bad_value",
    [
        ("doi", "10.0/bad"),
        ("publication_year", 2025),
        ("authors", ["Lei Liao"]),
        ("authors", ["Wrong"] * 5),
        ("title", "Wrong title"),
    ],
)
def test_paper_identity_mismatch_fails(
    config: dict, field: str, bad_value: object
) -> None:
    assert runner._paper_source_checks(config, _allowed_source_rows(config))
    config["paper_contract"][field] = bad_value
    assert not runner._paper_source_checks(config, _allowed_source_rows(config))


def test_formula_draft_is_complete_and_non_placeholder(config: dict) -> None:
    rows = runner.build_formula_draft(config, "1" * 64)
    assert [row["formula_id"] for row in rows] == config["paper_contract"][
        "required_formula_ids"
    ]
    assert len(rows) == 23 == len({row["formula_id"] for row in rows})
    for row in rows:
        assert row["paper_page"] in {1, 2, 3, 4, 5}
        assert row["equation_figure_table_anchor"]
        assert row["project_formula_canonical"]
        assert "see paper" not in json.dumps(row).lower()
        assert row["human_verified"] is False


def test_acquire_offline_and_human_authorization_chain(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, config: dict
) -> None:
    paper_source = runner.resolve_paths(config)["paper"]
    monkeypatch.setattr(runner, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(runner, "TOPIC_ROOT", tmp_path)
    monkeypatch.setattr(runner, "EXPERIMENT_DIR", tmp_path)
    shutil.copy2(paper_source, tmp_path / "paper.pdf")
    config["paths"]["paper"] = "paper.pdf"
    config["paths"]["reference_root"] = "references/21a"
    config_path = tmp_path / "config.yaml"
    runner.write_yaml(config_path, config)

    result = runner.acquire_sources_stage(config_path, offline=True)
    reference = tmp_path / "references/21a"
    assert result["authorization_required"] is True
    assert sorted(path.name for path in reference.iterdir()) == [
        "formula_review_packet.md",
        "paper_formula_registry_draft.csv",
        "source_availability_manifest.csv",
    ]
    with (reference / "source_availability_manifest.csv").open(
        encoding="utf-8"
    ) as handle:
        source_rows = list(csv.DictReader(handle))
    assert len(source_rows) == 4
    assert all(row["inside_allowlist"] == "true" for row in source_rows)
    assert all(
        row["availability_status"] in {"available", "not_evaluable_network_unavailable"}
        for row in source_rows
    )

    auth = {
        "paper_sha256": runner.file_sha(tmp_path / "paper.pdf"),
        "formula_registry_draft_sha256": runner.file_sha(
            reference / "paper_formula_registry_draft.csv"
        ),
        "review_packet_sha256": runner.file_sha(reference / "formula_review_packet.md"),
        "reviewed_source_id": "reaka_icassp_2026_vor",
        "reviewed_formula_ids": config["paper_contract"]["required_formula_ids"],
        "page_anchor_verified": True,
        "equation_or_figure_anchor_verified": True,
        "reviewer_role": "human",
        "reviewed_at_utc": "2026-07-13T00:00:00Z",
        "authorization_status": "approved",
    }
    runner.write_json(reference / "formula_review_authorization.json", auth)
    formula_rows, _, checks = runner.validate_formula_authorization(config)
    assert all(checks.values())
    assert len(formula_rows) == 23 and all(
        row["human_verified"] for row in formula_rows
    )
    auth["unknown_key"] = "forbidden"
    runner.write_json(reference / "formula_review_authorization.json", auth)
    _, _, rejected_checks = runner.validate_formula_authorization(config)
    assert not rejected_checks["hash_chain"] and not rejected_checks["approved_human"]


@pytest.mark.parametrize(
    "column",
    [
        "LABEL",
        "prefix_Target_Value_suffix",
        "nested.FORWARD_RETURN.1d",
        "my_RankIC_metric",
        "PnL_net",
    ],
)
def test_forbidden_column_scanner_is_case_insensitive(column: str) -> None:
    assert runner.forbid_outcome_columns([column]) == [column]


def test_metadata_exception_is_narrow() -> None:
    assert runner.forbid_outcome_columns(["label_id"], metadata_exception=True) == []
    assert runner.forbid_outcome_columns(
        ["real_label_value"], metadata_exception=True
    ) == ["real_label_value"]
    assert runner.expression_has_future_offset("Ref($close, -1)")
    assert not runner.expression_has_future_offset("Ref($close, 1)")


def test_alpha158_feature_only_registry_is_canonical() -> None:
    rows, expression_hash, meta = runner.extract_alpha158_registry()
    assert meta["version"] == "0.9.7"
    assert meta["count"] == 158
    assert [row["feature_index"] for row in rows] == list(range(158))
    assert len({row["feature_name"] for row in rows}) == 158
    assert not any(row["uses_future_offset"] for row in rows)
    import hashlib

    hash_lines = [
        f"{row['feature_index']}|{row['feature_name']}|{row['expression']}"
        for row in rows
    ]
    recomputed = hashlib.sha256("\n".join(hash_lines).encode("utf-8")).hexdigest()
    assert expression_hash == recomputed
    assert sum(not row["uses_vwap"] for row in rows) > 0


def test_field_routes_are_mechanical_and_shared(config: dict) -> None:
    rows, _, _ = runner.extract_alpha158_registry()
    mapping = runner.build_field_mapping(rows, config)
    assert {row["qlib_field"] for row in mapping} >= {
        "$open",
        "$high",
        "$low",
        "$close",
        "$volume",
        "$vwap",
    }
    no_vwap_count = sum(bool(row["route_inclusion_no_vwap"]) for row in rows)
    tables = runner.build_static_contract_tables(
        config, config["feature_contract"]["no_vwap_route_id"], no_vwap_count
    )
    arm_rows = tables["model_arm_registry.csv"]
    assert len(arm_rows) == 10
    assert {row["input_feature_route"] for row in arm_rows} == {
        config["feature_contract"]["no_vwap_route_id"]
    }
    assert (
        next(row for row in arm_rows if row["arm_id"] == "M0_HASH_NULL_SCORE")[
            "loss_terms"
        ]
        == "none"
    )


def test_volume_hands_to_shares_exactly_once() -> None:
    import pandas as pd

    frame = pd.DataFrame(
        {"volume": [1.0, 2.5], "source_volume_unit": ["hands", "hands"]}
    )
    shares = runner._volume_in_shares(frame)
    assert shares.tolist() == [100.0, 250.0]
    frame["source_volume_unit"] = "shares"
    assert runner._volume_in_shares(frame).tolist() == [1.0, 2.5]
    assert runner._volume_in_shares(pd.DataFrame({"volume": [1.0]})).isna().all()


def test_synthetic_vwap_factor_and_thresholds(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, config: dict
) -> None:
    import pandas as pd

    monkeypatch.setattr(runner, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(runner, "TOPIC_ROOT", tmp_path)
    monkeypatch.setattr(runner, "EXPERIMENT_DIR", tmp_path)
    config["paths"]["membership"] = "membership.csv"
    config["paths"]["qfq_root"] = "qfq"
    config["paths"]["raw_ohlcv_root"] = "raw"
    pd.DataFrame({"instrument": ["SH600000"], "board_bucket": ["main"]}).to_csv(
        tmp_path / "membership.csv", index=False
    )
    (tmp_path / "qfq").mkdir()
    (tmp_path / "raw").mkdir()
    dates = ["2026-01-05", "2026-01-06", "2026-01-07"]
    raw = pd.DataFrame(
        {
            "date": dates,
            "open": [10.0, 10.0, 10.0],
            "high": [12.0, 12.0, 12.0],
            "low": [9.0, 9.0, 9.0],
            "close": [11.0, 11.0, 11.0],
            "volume": [1000.0] * 3,
            "money": [10500.0] * 3,
            "instrument": ["SH600000"] * 3,
            "source_volume_unit": ["shares"] * 3,
        }
    )
    qfq = raw.copy()
    for field in ["open", "high", "low", "close"]:
        qfq[field] *= 0.5
    raw.to_csv(tmp_path / "raw/SH600000.csv", index=False)
    qfq.to_csv(tmp_path / "qfq/SH600000.csv", index=False)
    rows, jumps, date_sets, meta = runner.build_vwap_audit(config, [])
    global_row = next(row for row in rows if row["scope"] == "global")
    assert meta["audit_complete"] and meta["full_route_reachable"]
    assert global_row["overlap_rate"] == global_row["factor_pass_rate"] == 1.0
    assert global_row["auditable_row_rate"] == global_row["range_pass_rate"] == 1.0
    assert jumps == [] and date_sets["SH600000"] == set(dates)


def test_u_decision_is_invariant_to_t_plus_one_presence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, config: dict
) -> None:
    import pandas as pd

    monkeypatch.setattr(runner, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(runner, "TOPIC_ROOT", tmp_path)
    monkeypatch.setattr(runner, "EXPERIMENT_DIR", tmp_path)
    config["paths"]["membership"] = "membership.csv"
    config["paths"]["trading_calendar"] = "calendar.csv"
    config["universe_contract"]["minimum_primary_cross_section_n"] = 1
    dates = [f"2018-01-{day:02d}" for day in range(2, 14)]
    decision_date, next_date = dates[-2], dates[-1]
    pd.DataFrame({"trade_date": dates}).to_csv(tmp_path / "calendar.csv", index=False)
    pd.DataFrame(
        {
            "membership_date": [decision_date],
            "usable_trade_date": [next_date],
            "instrument": ["SH600000"],
            "is_listed": [True],
            "is_st": [False],
            "history_ready_240d_flag": [True],
            "available_time": [f"{decision_date} 15:00:00"],
            "membership_available_time": [f"{decision_date} 15:00:00"],
        }
    ).to_csv(tmp_path / "membership.csv", index=False)
    through_t = {"SH600000": set(dates[:-1])}
    with_t_plus_one = {"SH600000": set(dates)}
    first, timing, _, _ = runner.build_membership_support(
        config, through_t, "ROUTE", []
    )
    second, _, _, _ = runner.build_membership_support(
        config, with_t_plus_one, "ROUTE", []
    )
    assert first[0]["U_decision_n"] == second[0]["U_decision_n"] == 1
    assert all(row["status"] == "pass" for row in timing)


def test_terminal_data_cutoff_is_right_censored_not_timing_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, config: dict
) -> None:
    import pandas as pd

    monkeypatch.setattr(runner, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(runner, "TOPIC_ROOT", tmp_path)
    monkeypatch.setattr(runner, "EXPERIMENT_DIR", tmp_path)
    config["paths"]["membership"] = "membership.csv"
    config["paths"]["trading_calendar"] = "calendar.csv"
    config["universe_contract"]["minimum_primary_cross_section_n"] = 1
    dates = [f"2018-01-{day:02d}" for day in range(2, 14)]
    decision_date, next_date = dates[-2], dates[-1]
    pd.DataFrame({"trade_date": dates}).to_csv(tmp_path / "calendar.csv", index=False)
    pd.DataFrame(
        {
            "membership_date": [decision_date],
            "usable_trade_date": [""],
            "instrument": ["SH600000"],
            "is_listed": [True],
            "is_st": [False],
            "history_ready_240d_flag": [True],
            "available_time": [f"{decision_date} 15:00:00"],
            "membership_available_time": [f"{decision_date} 15:00:00"],
        }
    ).to_csv(tmp_path / "membership.csv", index=False)
    through_cutoff = {"SH600000": set(dates[:-1])}
    support, timing, _, meta = runner.build_membership_support(
        config, through_cutoff, "ROUTE", []
    )
    assert support[0]["membership_integrity_n"] == 1
    assert support[0]["U_decision_n"] == 1
    assert all(row["status"] == "pass" for row in timing)
    assert meta["market_data_max_date"] == decision_date
    assert meta["right_censored_membership_n"] == 1
    assert runner.decision_eligibility_predicate(
        is_listed=True,
        is_st=False,
        usable_trade_date="",
        expected_next_session=next_date,
        history_ready=True,
        sequence_ready=True,
        feature_ready=True,
        right_censored_data_cutoff=True,
    )


def test_nonterminal_blank_usable_date_still_fails_timing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, config: dict
) -> None:
    import pandas as pd

    monkeypatch.setattr(runner, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(runner, "TOPIC_ROOT", tmp_path)
    monkeypatch.setattr(runner, "EXPERIMENT_DIR", tmp_path)
    config["paths"]["membership"] = "membership.csv"
    config["paths"]["trading_calendar"] = "calendar.csv"
    config["universe_contract"]["minimum_primary_cross_section_n"] = 1
    dates = [f"2018-01-{day:02d}" for day in range(2, 15)]
    decision_date = dates[-3]
    pd.DataFrame({"trade_date": dates}).to_csv(tmp_path / "calendar.csv", index=False)
    pd.DataFrame(
        {
            "membership_date": [decision_date],
            "usable_trade_date": [""],
            "instrument": ["SH600000"],
            "is_listed": [True],
            "is_st": [False],
            "history_ready_240d_flag": [True],
            "available_time": [f"{decision_date} 15:00:00"],
            "membership_available_time": [f"{decision_date} 15:00:00"],
        }
    ).to_csv(tmp_path / "membership.csv", index=False)
    observed_beyond_next = {"SH600000": set(dates)}
    support, timing, _, meta = runner.build_membership_support(
        config, observed_beyond_next, "ROUTE", []
    )
    assert support[0]["membership_integrity_n"] == 1
    assert support[0]["U_decision_n"] == 0
    assert next(row for row in timing if row["check_id"] == "U02")["status"] == "pass"
    assert next(row for row in timing if row["check_id"] == "U03")["status"] == "fail"
    assert meta["right_censored_membership_n"] == 0


def test_static_graph_shape_label_and_resolution_contract(config: dict) -> None:
    tables = runner.build_static_contract_tables(config, "ROUTE", 158)
    graph = tables["train_teacher_inference_graph_contract.csv"]
    assert any(
        row["node_id"] == "Z_teacher_shifted" and row["train_only"] for row in graph
    )
    inference = [row for row in graph if row["inference_present"]]
    assert all("teacher" not in row["input_nodes"].lower() for row in inference)
    assert len(tables["model_arm_registry.csv"]) == 10
    assert {row["tensor_id"] for row in tables["tensor_shape_contract.csv"]} == {
        "y_source",
        "x_source",
        "H_y_source",
        "H_x_source",
        "Z_source",
        "Z_t",
        "y_teacher_shifted",
        "x_teacher_shifted",
        "Z_teacher_shifted",
        "selector_source",
        "K_codebook",
        "K_selected",
        "Z_hat_shifted",
        "R_target_shifted",
        "ddpm_x_s",
        "ddpm_epsilon",
        "ddpm_epsilon_hat",
        "R_hat_train_shifted",
        "Z_tilde_train_shifted",
        "R_hat_inference_draws",
        "Z_tilde_inference_draws",
        "R_hat_mlp_shifted",
        "Z_tilde_mlp_shifted",
        "decoded_source",
        "decoded_shifted_train",
        "decoded_shifted_draws",
        "direct_score_M2",
        "direct_score_M3",
        "direct_score_A0",
        "score_draws_R2",
        "score_next",
    }
    assert all(
        not row["materialized_in_21a"] for row in tables["label_semantics_freeze.csv"]
    )
    resolution = tables["decision_universe_and_label_resolution_contract.csv"]
    assert {row["status_id"] for row in resolution} == {
        "NORMAL_NEXT_SESSION_CLOSE",
        "LISTED_SUSPENDED_CARRY",
        "CONFIRMED_TERMINAL_PRICE",
        "UNKNOWN_DATA_GAP",
        "RIGHT_CENSORED_DATA_CUTOFF",
    }
    assert {
        row["row_or_day_action"]
        for row in resolution
        if not row["primary_denominator_allowed"]
    } == {"whole_day_not_evaluable"}


def test_synthetic_graph_shapes_gradient_isolation_and_global_k1c(config: dict) -> None:
    import torch

    config["architecture"]["latent_dim"] = 8
    config["architecture"]["diffusion_steps"] = 3
    model = runner.create_reaka_model(4, config, device="cpu")
    generator = torch.Generator().manual_seed(7)
    y = torch.randn((3, 10, 1), generator=generator)
    x = torch.randn((3, 10, 4), generator=generator)
    y_teacher = torch.randn((3, 10, 1), generator=generator)
    x_teacher = torch.randn((3, 10, 4), generator=generator)
    output = model.train_graph(y, x, y_teacher, x_teacher, 11)
    assert output["Z_source"].shape == (3, 10, 8)
    assert output["K_selected"].shape == (3, 10, 8, 8)
    explicit = torch.einsum("btij,btj->bti", output["K_selected"], output["Z_source"])
    assert torch.allclose(explicit, output["Z_hat_shifted"], atol=1e-7, rtol=0)
    r1_reference = (
        (output["R_hat_mlp_shifted"] - output["R_target_shifted"]).square().mean()
    )
    assert torch.equal(r1_reference, output["L_residual_mlp"])
    assert torch.equal(
        output["L_rec_mlp"] + output["L_koop"] + output["L_residual_mlp"],
        output["L_total_R1"],
    )
    output["L_koop"].backward()
    assert (
        sum(
            parameter.grad.abs().sum().item()
            for parameter in model.return_encoder.parameters()
            if parameter.grad is not None
        )
        > 0
    )

    with torch.no_grad():
        row_keys = [
            ("SH600000", "2026-07-13"),
            ("SZ000001", "2026-07-14"),
            ("BJ430047", "2026-07-15"),
        ]
        score_a = model.inference(y, x, 13, row_keys, draws=2)
        score_b = model.inference(y, x, 13, row_keys, draws=2)
        assert torch.equal(score_a, score_b)
        k1c = model.k1c_selector(3, 10, 0.5, torch.Generator().manual_seed(17), True)
        assert torch.equal(k1c, k1c[0, 0].view(1, 1, -1).expand_as(k1c))
    assert inspect.getsource(type(model).encode).count("torch.sigmoid") == 1


def test_cpu_full_graph_audit(config: dict) -> None:
    config["architecture"]["diffusion_steps"] = 2
    config["architecture"]["inference_residual_draws"] = 2
    rows, runtime_rows, meta = runner.run_synthetic_graph_audit(
        config, feature_dim=4, device_override="cpu"
    )
    assert len(rows) == 12 and all(row["status"] == "pass" for row in rows)
    assert meta["teacher_delta"] == 0.0
    assert meta["k1c_train_delta"] == meta["k1c_inference_delta"] == 0.0
    assert meta["all_transition_shape"][1] == 10
    assert meta["batch_reorder_delta"] <= 1e-7
    assert meta["gpu_gate"] is False
    assert any(
        row["check_id"] == "batch_candidate_full_graph" and row["status"] == "pass"
        for row in runtime_rows
    )


def test_rtx4070_full_graph_eight_draw(config: dict) -> None:
    import torch

    if not torch.cuda.is_available():
        pytest.skip("CUDA is required for the contract GPU test")
    rows, runtime_rows, meta = runner.run_synthetic_graph_audit(config, feature_dim=157)
    assert len(rows) == 12 and all(row["status"] == "pass" for row in rows)
    assert "RTX 4070 SUPER" in meta["device_name"]
    assert meta["selected_batch_size"] == 256
    assert meta["score_draw_shape"] == [256, 8]
    assert meta["batch_reorder_delta"] <= 1e-7
    assert meta["gpu_gate"] is True
    assert any(
        row["check_id"] == "batch_candidate_full_graph" and row["status"] == "pass"
        for row in runtime_rows
    )


def test_robust_normalizer_constant_clip_and_invalid_fill() -> None:
    values = np.array(
        [
            [1.0, 5.0, -1000.0],
            [2.0, 5.0, 0.0],
            [3.0, 5.0, 1000.0],
            [math.nan, 5.0, math.inf],
        ]
    )
    normalizer = runner.fit_robust_normalizer(values)
    transformed = runner.apply_robust_normalizer(values, normalizer)
    assert transformed.dtype == np.float32
    assert np.isfinite(transformed).all()
    assert np.equal(transformed[:, 1], 0.0).all()
    assert transformed.min() >= -10.0 and transformed.max() <= 10.0
    assert transformed[-1, 0] == 0.0 and transformed[-1, 2] == 0.0


def test_alpha158_feature_only_materialization_is_trailing(config: dict) -> None:
    import pandas as pd

    alpha_rows, _, _ = runner.extract_alpha158_registry()
    selected = [row for row in alpha_rows if not row["uses_vwap"]]
    dates = pd.date_range("2025-01-01", periods=80, freq="D")
    frame = pd.DataFrame(
        {
            "open": np.linspace(10, 20, 80),
            "high": np.linspace(10.5, 20.5, 80),
            "low": np.linspace(9.5, 19.5, 80),
            "close": np.linspace(10.2, 20.2, 80),
            "volume": np.linspace(1000, 2000, 80),
        },
        index=dates.astype(str),
    )
    first = runner.compute_alpha158_features(frame, selected)
    perturbed = frame.copy()
    perturbed.iloc[-1] = [1000, 1001, 999, 1000, 1_000_000]
    second = runner.compute_alpha158_features(perturbed, selected)
    assert first.shape == second.shape == (80, 157)
    assert np.allclose(first.iloc[:-1], second.iloc[:-1], equal_nan=True)


def test_feature_cache_binds_materialized_bytes(
    config: dict, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import pandas as pd

    qfq_root = tmp_path / "qfq"
    raw_root = tmp_path / "raw"
    qfq_root.mkdir()
    raw_root.mkdir()
    dates = pd.bdate_range("2018-01-02", periods=100).strftime("%Y-%m-%d")
    price = np.linspace(10.0, 20.0, len(dates))
    bars = pd.DataFrame(
        {
            "date": dates,
            "open": price,
            "high": price + 0.5,
            "low": price - 0.5,
            "close": price + 0.1,
            "volume": np.linspace(100_000, 200_000, len(dates)),
            "money": np.linspace(1_000_000, 3_000_000, len(dates)),
            "instrument": "SH600000",
            "source_volume_unit": "shares",
        }
    )
    bars.to_csv(qfq_root / "SH600000.csv", index=False)
    bars.to_csv(raw_root / "SH600000.csv", index=False)
    membership = pd.DataFrame(
        {
            "membership_date": dates[-5:],
            "instrument": "SH600000",
            "is_suspended": False,
            "history_ready_240d_flag": True,
        }
    )
    membership_path = tmp_path / "membership.csv"
    calendar_path = tmp_path / "calendar.csv"
    membership.to_csv(membership_path, index=False)
    pd.DataFrame({"trade_date": dates}).to_csv(calendar_path, index=False)
    monkeypatch.setattr(
        runner,
        "resolve_paths",
        lambda _: {
            "membership": membership_path,
            "trading_calendar": calendar_path,
            "qfq_root": qfq_root,
            "raw_ohlcv_root": raw_root,
        },
    )
    alpha_rows, _, _ = runner.extract_alpha158_registry()
    result = runner.materialize_feature_cache(
        config,
        alpha_rows,
        config["feature_contract"]["no_vwap_route_id"],
        [],
        cache_root=tmp_path / "feature_cache",
    )
    assert result["status"] == "pass"
    assert result["materialized_expression_count"] == 157
    assert result["cache_file_n"] == 4
    assert result["cache_size_bytes"] > 0 and len(result["cache_content_hash"]) == 64
    assert len(result["ready_keys"]) == 5


def test_row_key_ddpm_is_batch_order_invariant(config: dict) -> None:
    import torch

    config["architecture"]["latent_dim"] = 8
    config["architecture"]["diffusion_steps"] = 3
    model = runner.create_reaka_model(4, config, "cpu").eval()
    generator = torch.Generator().manual_seed(31)
    y = torch.randn((3, 10, 1), generator=generator)
    x = torch.randn((3, 10, 4), generator=generator)
    keys = [
        ("SH600000", "2026-07-13"),
        ("SZ000001", "2026-07-14"),
        ("BJ430047", "2026-07-15"),
    ]
    permutation = torch.tensor([2, 0, 1])
    inverse = torch.argsort(permutation)
    with torch.no_grad():
        original = model.inference(y, x, 20260713, keys, draws=2)
        reordered = model.inference(
            y[permutation],
            x[permutation],
            20260713,
            [keys[index] for index in permutation.tolist()],
            draws=2,
        )[inverse]
    assert torch.equal(original, reordered)
    assert runner.inference_draw_seed(
        runner.RUN_ID, "R2_REAKA_DIFFUSION", 20260713, *keys[0], 0
    ) == runner.inference_draw_seed(
        runner.RUN_ID, "R2_REAKA_DIFFUSION", 20260713, *keys[0], 0
    )


def test_timestep_embedding_and_r1_width_are_exact(config: dict) -> None:
    import torch

    model = runner.create_reaka_model(4, config, "cpu")
    observed = model.timestep_embedding(torch.tensor([[1]]), torch.float32)[0, 0]
    expected = []
    for index in range(16):
        angle = 1.0 / (10000.0 ** (2 * index / 32))
        expected.extend([math.sin(angle), math.cos(angle)])
    assert torch.allclose(observed, torch.tensor(expected), atol=1e-7, rtol=0)
    width, r1_n, denoiser_n, relative_delta = runner.select_r1_hidden_width(config)
    assert width == 160 and r1_n == 46464 and denoiser_n == 45376
    assert relative_delta == pytest.approx(1088 / 45376)


def test_rankic_ties_full_denominator_and_undefined_days() -> None:
    scores = [1.0, 1.0, 3.0, 4.0]
    labels = [1.0, 2.0, 3.0, 4.0]
    observed = runner.average_rank_rankic(scores, labels, minimum_n=4)
    expected = np.corrcoef([1.5, 1.5, 3.0, 4.0], [1.0, 2.0, 3.0, 4.0])[0, 1]
    assert observed == pytest.approx(expected)
    assert runner.average_rank_rankic([1.0] * 4, labels, minimum_n=4) is None
    assert (
        runner.average_rank_rankic([1.0, 2.0, math.nan, 4.0], labels, minimum_n=4)
        is None
    )
    assert runner.average_rank_rankic(scores[:3], labels[:3], minimum_n=4) is None


def test_bootstrap_and_hash_score_are_deterministic() -> None:
    first = runner.stationary_bootstrap_indices(31, 5, 20260713, 20)
    second = runner.stationary_bootstrap_indices(31, 5, 20260713, 20)
    assert np.array_equal(first, second)
    assert first.shape == (5, 31) and ((0 <= first) & (first < 31)).all()
    score = runner.m0_hash_score("600000.SH", "2026-07-13")
    assert score == runner.m0_hash_score("SH600000", "2026-07-13")
    assert 0 <= score < 1


def test_stationary_bootstrap_holm_exact(config: dict) -> None:
    margins = {
        contrast_id: float(spec["margin"])
        for contrast_id, spec in config["metrics"]["contrasts"].items()
    }
    base = np.linspace(-0.002, 0.002, 252)
    deltas = {
        contrast_id: base + margin + 0.02 + index * 0.001
        for index, (contrast_id, margin) in enumerate(sorted(margins.items()))
    }
    first = runner.stationary_bootstrap_holm(deltas, margins)
    second = runner.stationary_bootstrap_holm(deltas, margins)
    assert first == second
    assert [row["holm_rank"] for row in first] == list(range(1, 8))
    assert all(
        row["family_size"] == 7 and row["complete_day_n"] == 252 for row in first
    )
    assert all(row["raw_one_sided_p"] == pytest.approx(1 / 5001) for row in first)
    assert all(row["holm_step_pass"] for row in first)

    not_evaluable = runner.stationary_bootstrap_holm(
        {key: values[:251] for key, values in deltas.items()}, margins
    )
    assert all(
        row["status"] == "not_evaluable" and row["raw_one_sided_p"] == 1.0
        for row in not_evaluable
    )


def test_search_seed_metric_and_forward_freezes(config: dict) -> None:
    hyper, seeds = runner.build_search_seed_tables(config)
    assert {
        row["config_id"]
        for row in hyper
        if row["role"] == "scheduled_one_factor_sensitivity"
    } == {f"S0{i}" for i in range(1, 7)}
    assert {row["model_seed"] for row in seeds} == {20260713, 20260714, 20260715}
    metrics = runner.build_metric_table(config)
    contrasts = [row for row in metrics if row["record_type"] == "contrast"]
    assert {row["contrast_id"] for row in contrasts} == set(
        config["metrics"]["contrasts"]
    )
    assert len(contrasts) == 7
    assert any(
        row["record_type"] == "confirmatory_power" and row["n_required"] == 291
        for row in metrics
    )
    forward = {
        row["field"]: row["frozen_value"] for row in runner.build_forward_table(config)
    }
    assert (
        forward["comparators"]
        == "R2_REAKA_DIFFUSION|M1_LIGHTGBM_ALPHA158|M3_GATED_DUAL_PATH_LSTM"
    )
    assert (
        forward["rolling_retrain"] is False and forward["minimum_complete_days"] == 291
    )


def test_dependency_lock_and_runtime_match(config: dict) -> None:
    rows, meta = runner.build_dependency_table(config)
    versions = {row["dependency"]: row for row in rows}
    assert versions["torch"]["lock_resolved_version"] == "2.8.0"
    assert versions["pyqlib"]["lock_resolved_version"] == "0.9.7"
    assert versions["lightgbm"]["lock_resolved_version"] == "4.6.0"
    assert meta["declarations_ok"] and meta["interpreter_ok"] and meta["all_match"]
    assert "torch==2.8.0" in runner.resolve_paths(config)["requirements"].read_text(
        encoding="utf-8"
    )


def test_ep19_ep20_upstream_hash_chains_close(config: dict) -> None:
    rows, verified = runner.build_upstream_audit(config)
    assert verified
    assert rows and all(
        row["manifest_verified"] is True and row["status"] == "pass" for row in rows
    )


def test_gate_check_sets_and_missing_check_fail_closed() -> None:
    contract = _all_true_contract()
    rows, gates = runner._gate_evidence_rows(contract, True, [])
    assert len(rows) == sum(len(checks) for checks in runner.GATE_CHECKS.values())
    assert len({(row["gate_id"], row["check_id"]) for row in rows}) == len(rows)
    assert all(status == "pass" for status in gates.values())
    del contract["gate_check_statuses"]["architecture_shape_gate"]["S04"]
    _, failed = runner._gate_evidence_rows(contract, True, [])
    assert failed["architecture_shape_gate"] == "fail"


def test_independent_gate_builder_has_exact_truth_table(config: dict) -> None:
    config["architecture"]["diffusion_steps"] = 2
    config["architecture"]["inference_residual_draws"] = 2
    alpha_rows, expression_hash, alpha_meta = runner.extract_alpha158_registry()
    field_mapping = runner.build_field_mapping(alpha_rows, config)
    static_tables = runner.build_static_contract_tables(
        config,
        config["feature_contract"]["no_vwap_route_id"],
        alpha_meta["no_vwap_count"],
    )
    graph_rows, _, graph_meta = runner.run_synthetic_graph_audit(
        config, alpha_meta["no_vwap_count"], "cpu"
    )
    dependency_rows, dependency_meta = runner.build_dependency_table(config)
    hyper_rows, seed_rows = runner.build_search_seed_tables(config)
    metric_rows = runner.build_metric_table(config)
    forward_rows = runner.build_forward_table(config)
    access_log = [
        {
            "access_gate": "pass",
            "outcome_columns_detected": "",
            "outcome_formula_executed": False,
            "selection_or_tuning_allowed": False,
            "purpose": "feature_only_materialization",
            "artifact_path_or_resource": "fixture",
            "dataset_role": "fixture",
        }
    ]
    feature_cache = {
        "status": "pass",
        "materialized_expression_count": alpha_meta["no_vwap_count"],
        "cache_content_hash": "a" * 64,
        "cache_file_n": 4,
        "cache_row_n": 10,
        "ready_keys": {("SH600000", "2020-01-02")},
        "sequence_ready_keys": {("SH600000", "2020-01-02")},
    }
    support_row = {
        "U_decision_n": 100,
        "feature_ready_n": 100,
        "layer_count_reconciled": True,
        "support_status": "ready",
    }
    context = {
        "config": config,
        "paths": runner.resolve_paths(config),
        "source_rows": _allowed_source_rows(config),
        "formula_rows": [],
        "formula_auth": None,
        "formula_checks": {
            "hash_chain": False,
            "approved_human": False,
            "formula_set": False,
            "rows_complete": False,
        },
        "alpha_rows": alpha_rows,
        "alpha_meta": alpha_meta,
        "field_mapping": field_mapping,
        "expression_hash": expression_hash,
        "vwap_rows": [{"scope": "global"}, {"scope": "board_year"}],
        "jump_rows": [],
        "vwap_meta": {"audit_complete": True, "global": {"factor_pass_rate": 1.0}},
        "feature_cache": feature_cache,
        "cache_manifest": {"cache_content_hash": "a" * 64},
        "support_rows": [support_row],
        "timing_rows": [
            {"check_id": check_id, "status": "pass"}
            for check_id in runner.GATE_CHECKS["pit_membership_timing_gate"]
        ],
        "split_rows": [
            {
                "split_id": "train",
                "effective_start": "2018-01-02",
                "purge_sessions": 12,
                "dropped_day_n": 12,
            },
            {
                "split_id": "validation",
                "effective_start": "2023-01-03",
                "purge_sessions": 12,
                "dropped_day_n": 12,
            },
            {
                "split_id": "historical_design_holdout",
                "effective_start": "2024-01-02",
                "purge_sessions": 0,
                "dropped_day_n": 0,
            },
        ],
        "support_meta": {
            "feature_predicate_exact": True,
            "complete_by_split": {
                "train": 750,
                "validation": 200,
                "historical_design_holdout": 400,
            },
        },
        "static_tables": static_tables,
        "graph_rows": graph_rows,
        "graph_meta": graph_meta,
        "hyper_rows": hyper_rows,
        "seed_rows": seed_rows,
        "dependency_rows": dependency_rows,
        "dependency_meta": dependency_meta,
        "metric_rows": metric_rows,
        "metric_meta": runner.metric_algorithm_self_audit(config),
        "forward_rows": forward_rows,
        "upstream_ok": True,
        "input_rows": [{"artifact_id": "fixture", "status": "pass"}],
        "access_log": access_log,
        "paper_tables": runner.build_paper_tables(config, []),
        "feature_route_id": config["feature_contract"]["no_vwap_route_id"],
        "feature_dim": alpha_meta["no_vwap_count"],
        "exact_local": False,
        "requirement_sha256": runner.file_sha(
            runner.resolve_paths(config)["requirement"]
        ),
        "preoutcome_hard_counts": {
            "outcome_columns_detected_count": 0,
            "outcome_formula_executed_count": 0,
            "real_label_materialization_count": 0,
            "real_model_score_count": 0,
            "selection_or_tuning_allowed_count": 0,
            "historical_holdout_outcome_access_count": 0,
        },
        "expected_freeze_paths": runner.FREEZE_RELATIVE_PATHS,
        "sealed_at_utc": "2026-07-13T00:00:00Z",
        "synthetic_t_plus_one_invariant": True,
    }
    statuses = runner.build_gate_check_statuses(context)
    assert set(statuses) == set(runner.CRITICAL_GATES)
    assert all(
        set(statuses[gate_id]) == set(check_ids)
        for gate_id, check_ids in runner.GATE_CHECKS.items()
    )
    assert statuses["gpu_dry_run_gate"]["GPU01"] is False
    assert statuses["gradient_teacher_isolation_gate"]["GI14"] is True


def test_decision_precedence_and_success_authorization() -> None:
    gates = {gate_id: "pass" for gate_id in runner.CRITICAL_GATES}
    assert runner._decision_state(gates) == "21A_preoutcome_architecture_contract_ready"
    gates["gpu_dry_run_gate"] = "fail"
    gates["paper_formula_contract_gate"] = "fail"
    assert runner._decision_state(gates) == "21A_paper_source_lineage_blocked"
    gates["outcome_firewall_gate"] = "fail"
    assert runner._decision_state(gates) == "21A_outcome_firewall_violated"

    ready_gates = {gate_id: "pass" for gate_id in runner.CRITICAL_GATES}
    decision = runner._build_decision_row(
        _all_true_contract(), ready_gates, "c" * 64, "d" * 64
    )
    assert decision["next_requirement_generation_authorized"] is True
    assert decision["next_requirement_execution_authorized"] is False
    assert decision["exact_replication_reachable"] is False
    for field in [
        "outcome_model_training_authorized",
        "policy_training_authorized",
        "portfolio_optimization_authorized",
        "deployment_authorized",
    ]:
        assert decision[field] is False


def test_freeze_manifest_hashes_and_finalize_are_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, config: dict
) -> None:
    output = tmp_path / "out"
    bundle_hash = _make_freeze_bundle(output, config)
    verified = runner.verify_freeze_bundle(output, [])
    assert verified["freeze_bundle_hash"] == bundle_hash
    assert verified["manifest"]["expected_paths"] == runner.FREEZE_RELATIVE_PATHS

    monkeypatch.setattr(runner, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(runner, "TOPIC_ROOT", tmp_path)
    monkeypatch.setattr(runner, "EXPERIMENT_DIR", tmp_path)
    result = runner.finalize_stage("out")
    assert result["decision_state"] == "21A_preoutcome_architecture_contract_ready"
    manifest = runner.read_json(
        output / "manifest_21a_paper_lineage_pit_data_and_architecture_contract.json"
    )
    hashes = runner.read_json(
        output
        / "output_hashes_21a_paper_lineage_pit_data_and_architecture_contract.json"
    )
    assert manifest["expected_paths"] == runner.FINAL_RELATIVE_PATHS
    assert set(hashes["hashes"]) == set(runner.FINAL_RELATIVE_PATHS) - {
        "output_hashes_21a_paper_lineage_pit_data_and_architecture_contract.json"
    }
    with (output / "finalize_access_audit.csv").open(encoding="utf-8") as handle:
        access_rows = list(csv.DictReader(handle))
    assert access_rows and all(
        row["freeze_manifest_listed"] == "true"
        and row["raw_input"] == "false"
        and row["allowed"] == "true"
        for row in access_rows
    )
    report = (
        output / "21A_paper_lineage_pit_data_and_architecture_contract_report.md"
    ).read_text(encoding="utf-8")
    required_phrases = [
        "21A 没有训练或评价任何真实 outcome model，也没有生成真实股票 score、RankIC 或策略 PnL。",
        "EP21 只能声明 paper_architecture_grounded_project_adaptation，不能声明 exact_replication 或 paper_result_reproduced。",
        "U_t_decision 在 outcome 前固定",
        "Primary REAKA 对全部 T 个 shifted transitions",
        "Teacher tensors 只允许构造 train-only Koopman/residual target",
        "Official code 或 appendix 未披露不阻断 project adaptation",
        "21F 只前瞻确认 R2 相对预冻结 M1/M3",
        "21A 成功只允许生成并人工评审 21B requirement",
    ]
    assert all(phrase in report for phrase in required_phrases)
    with pytest.raises(FileExistsError):
        runner.finalize_stage("out")


def test_corrupted_freeze_maps_to_manifest_hash_blocked(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, config: dict
) -> None:
    output = tmp_path / "out"
    _make_freeze_bundle(output, config)
    runner.write_text(output / "freeze/21A_contract_freeze.md", "tampered")
    monkeypatch.setattr(runner, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(runner, "TOPIC_ROOT", tmp_path)
    monkeypatch.setattr(runner, "EXPERIMENT_DIR", tmp_path)
    result = runner.finalize_stage("out")
    assert result["decision_state"] == "21A_manifest_or_hash_blocked"
    with (output / "21A_contract_decision.csv").open(encoding="utf-8") as handle:
        decision = next(csv.DictReader(handle))
    assert decision["freeze_bundle_hash_gate"] == "fail"
    assert decision["outcome_firewall_gate"] == "pass"


def test_finalize_cli_forbids_config_and_absolute_output() -> None:
    with pytest.raises(SystemExit):
        runner.parse_args(
            ["--stage", "finalize", "--config", "x", "--output-root", "y"]
        )
    with pytest.raises(ValueError):
        runner.finalize_stage("/tmp/forbidden")
