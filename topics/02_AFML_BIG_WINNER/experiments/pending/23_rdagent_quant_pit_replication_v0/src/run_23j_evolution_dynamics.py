#!/usr/bin/env python3
"""Analyze EP23 A20/A157 RD-Factor search dynamics and hypothesis geometry."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import requests
import yaml
from dotenv import dotenv_values
from sklearn.cluster import AgglomerativeClustering

from ep23_phase2_common import canonical_json_sha256, load_configs, sha256_file


BRANCHES = {
    "a20": "factor_a20",
    "a157": "factor_a158",
}

FAMILY_TERMS = {
    "momentum": ("momentum", "trend", "roc", "persistence"),
    "reversal": ("reversal", "reverse", "contrarian", "mean revert"),
    "volatility": ("volatility", "variance", "std", "range", "parkinson"),
    "volume": ("volume", "turnover", "liquidity", "attention", "money"),
    "intraday": ("intraday", "close location", "clv", "open-to-close"),
    "overnight": ("overnight", "gap", "close-to-open"),
    "correlation": ("correlation", "corr", "co-movement"),
    "interaction": ("interaction", "conditional", "confirmation", "multiply"),
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def cosine(left: np.ndarray, right: np.ndarray) -> float:
    denominator = float(np.linalg.norm(left) * np.linalg.norm(right))
    return float(np.dot(left, right) / denominator) if denominator else np.nan


def families(text: str) -> list[str]:
    lowered = text.lower()
    result = [
        family
        for family, terms in FAMILY_TERMS.items()
        if any(term in lowered for term in terms)
    ]
    return result or ["other"]


def fetch_embeddings(
    *,
    texts: list[str],
    api_key: str,
    proxy_url: str,
    model: str,
    batch_size: int = 50,
) -> np.ndarray:
    vectors: list[list[float]] = []
    proxies = {"http": proxy_url, "https": proxy_url}
    for start in range(0, len(texts), batch_size):
        batch = texts[start : start + batch_size]
        last_error: Exception | None = None
        for attempt in range(1, 6):
            try:
                response = requests.post(
                    "https://openrouter.ai/api/v1/embeddings",
                    headers={"Authorization": f"Bearer {api_key}"},
                    json={"model": model, "input": batch},
                    proxies=proxies,
                    timeout=120,
                )
                response.raise_for_status()
                payload = response.json()
                ordered = sorted(payload["data"], key=lambda row: int(row["index"]))
                vectors.extend(row["embedding"] for row in ordered)
                last_error = None
                break
            except (requests.RequestException, KeyError, TypeError, ValueError) as error:
                last_error = error
                if attempt < 5:
                    time.sleep(2**attempt)
        if last_error is not None:
            raise RuntimeError(
                f"embedding batch {start // batch_size} failed after retries"
            ) from last_error
    result = np.asarray(vectors, dtype="float32")
    if result.shape[0] != len(texts):
        raise RuntimeError("embedding response row count mismatch")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--proxy-url", required=True)
    args = parser.parse_args()

    config_path = args.config.resolve()
    episode_root = config_path.parent
    phase2, _ = load_configs(config_path)
    output_dir = episode_root / phase2["outputs"]["evolution_dynamics"]
    output_dir.mkdir(parents=True, exist_ok=True)

    loop_parts: list[pd.DataFrame] = []
    candidate_parts: list[pd.DataFrame] = []
    hypothesis_rows: list[dict[str, Any]] = []
    confirmation_parts: list[pd.DataFrame] = []
    state_summary_parts: list[pd.DataFrame] = []
    library_quality_parts: list[pd.DataFrame] = []
    decision_parts: list[pd.DataFrame] = []
    accounting_parts: list[pd.DataFrame] = []
    attempt_parts: list[pd.DataFrame] = []
    input_files: list[dict[str, str]] = []
    branch_cost_rows: list[dict[str, Any]] = []
    for branch, output_key in BRANCHES.items():
        branch_dir = episode_root / phase2["outputs"][output_key]
        required = [
            branch_dir / "loop_trace.csv",
            branch_dir / "candidate_inventory.csv",
            branch_dir / "hypothesis_trace.jsonl",
            branch_dir / "search_accounting.csv",
            branch_dir / "run_manifest.json",
            branch_dir / "confirmation_verdict.json",
            branch_dir / "decision_reconciliation.csv",
            branch_dir / "library_state_summary.csv",
            branch_dir / "implementation_attempts.csv",
        ]
        missing = [str(path) for path in required if not path.exists()]
        if missing:
            raise FileNotFoundError(f"{branch} missing 23I artifacts: {missing}")
        for path in required:
            input_files.append({"path": str(path), "sha256": sha256_file(path)})
        loops = pd.read_csv(branch_dir / "loop_trace.csv")
        loops["branch"] = branch
        loop_parts.append(loops)
        candidates = pd.read_csv(branch_dir / "candidate_inventory.csv")
        candidates["branch"] = branch
        candidate_parts.append(candidates)
        for row in load_jsonl(branch_dir / "hypothesis_trace.jsonl"):
            row["branch"] = branch
            hypothesis_rows.append(row)
        decisions = pd.read_csv(branch_dir / "decision_reconciliation.csv")
        decisions["branch"] = branch
        decision_parts.append(decisions)
        accounting = pd.read_csv(branch_dir / "search_accounting.csv")
        accounting["branch"] = branch
        accounting_parts.append(accounting)
        attempts = pd.read_csv(branch_dir / "implementation_attempts.csv")
        attempts["branch"] = branch
        attempt_parts.append(attempts)
        state_summary = pd.read_csv(branch_dir / "library_state_summary.csv")
        state_summary["branch"] = branch
        state_summary_parts.append(state_summary)
        quality_path = branch_dir / "library_quality_metrics.csv"
        if quality_path.exists():
            quality = pd.read_csv(quality_path)
            quality["branch"] = branch
            library_quality_parts.append(quality)
            input_files.append(
                {"path": str(quality_path), "sha256": sha256_file(quality_path)}
            )
        attribution_path = branch_dir / "matched_marginal_attribution.csv"
        if attribution_path.exists():
            confirmation = pd.read_csv(attribution_path)
            confirmation["branch"] = branch
            confirmation_parts.append(confirmation)
            input_files.append(
                {"path": str(attribution_path), "sha256": sha256_file(attribution_path)}
            )
        run_manifest = json.loads(
            (branch_dir / "run_manifest.json").read_text(encoding="utf-8")
        )
        branch_cost_rows.append(
            {
                "branch": branch,
                "provider_cost_usd": run_manifest.get(
                    "openrouter_key_usage_delta_usd"
                ),
                "raw_status": run_manifest.get("status"),
            }
        )

    loops = pd.concat(loop_parts, ignore_index=True)
    candidates = pd.concat(candidate_parts, ignore_index=True)
    hypotheses = pd.DataFrame(hypothesis_rows).sort_values(
        ["branch", "loop_index"]
    )
    confirmations = (
        pd.concat(confirmation_parts, ignore_index=True)
        if confirmation_parts
        else pd.DataFrame()
    )
    decisions = pd.concat(decision_parts, ignore_index=True)
    accountings = pd.concat(accounting_parts, ignore_index=True)
    attempts = pd.concat(attempt_parts, ignore_index=True)
    state_summaries = pd.concat(state_summary_parts, ignore_index=True)

    rdagent_path = Path(phase2["runtime"]["rdagent_checkout"]).resolve()
    dotenv = dotenv_values(rdagent_path / ".env")
    api_key = str(
        dotenv.get("OPENAI_API_KEY") or dotenv.get("OPENROUTER_API_KEY") or ""
    )
    if not api_key:
        raise RuntimeError("OpenRouter credential not configured")
    embedding_model = phase2["runtime"]["embedding_model"]
    embedding_texts = [
        f"{row.hypothesis or ''}\nReason: {row.reason or ''}"
        for row in hypotheses.itertuples(index=False)
    ]
    vectors = fetch_embeddings(
        texts=embedding_texts,
        api_key=api_key,
        proxy_url=args.proxy_url,
        model=embedding_model,
    )
    if len(vectors) == 1:
        labels = np.zeros(1, dtype=int)
    else:
        labels = AgglomerativeClustering(
            n_clusters=None,
            metric="cosine",
            linkage="average",
            distance_threshold=0.20,
        ).fit_predict(vectors)

    embedding_frame = hypotheses[["branch", "loop_index"]].reset_index(drop=True)
    embedding_frame["text_sha256"] = [
        sha256_bytes(text.encode("utf-8")) for text in embedding_texts
    ]
    embedding_frame["cluster_id"] = labels
    vector_columns = [f"embedding_{index}" for index in range(vectors.shape[1])]
    embedding_frame = pd.concat(
        [
            embedding_frame,
            pd.DataFrame(vectors, columns=vector_columns),
        ],
        axis=1,
    )
    embedding_frame.to_parquet(output_dir / "hypothesis_embeddings.parquet")

    cluster_rows = []
    for cluster_id, group in embedding_frame.groupby("cluster_id"):
        keys = group[["branch", "loop_index"]]
        joined = hypotheses.merge(keys, on=["branch", "loop_index"], how="inner")
        loop_joined = loops.merge(keys, on=["branch", "loop_index"], how="inner")
        if len(confirmations):
            loop_joined = loop_joined.merge(
                confirmations[
                    [
                        "branch",
                        "loop_index",
                        "predictive_confirmation_pass",
                    ]
                ],
                on=["branch", "loop_index"],
                how="left",
            )
        cluster_rows.append(
            {
                "cluster_id": int(cluster_id),
                "loop_count": len(group),
                "branch_count": group["branch"].nunique(),
                "accepted_loops": int(loop_joined["decision"].sum()),
                "valid_loops": int(loop_joined["current_ic"].notna().sum()),
                "agent_accept_rate": float(
                    loop_joined["decision"].mean()
                ),
                "confirmed_loops": int(
                    loop_joined.get(
                        "predictive_confirmation_pass",
                        pd.Series(False, index=loop_joined.index),
                    )
                    .fillna(False)
                    .sum()
                ),
                "confirmation_success_rate": float(
                    loop_joined.get(
                        "predictive_confirmation_pass",
                        pd.Series(False, index=loop_joined.index),
                    )
                    .fillna(False)
                    .mean()
                ),
                "representative_hypothesis": joined.iloc[0]["hypothesis"],
            }
        )
    pd.DataFrame(cluster_rows).to_csv(
        output_dir / "hypothesis_clusters.csv", index=False
    )

    transition_rows: list[dict[str, Any]] = []
    factor_names_seen: dict[str, set[str]] = {branch: set() for branch in BRANCHES}
    factor_formulas_seen: dict[str, set[str]] = {
        branch: set() for branch in BRANCHES
    }
    factor_code_hashes_seen: dict[str, set[str]] = {
        branch: set() for branch in BRANCHES
    }
    vector_lookup = {
        (row.branch, int(row.loop_index)): vectors[index]
        for index, row in enumerate(hypotheses.itertuples(index=False))
    }
    for branch, group in hypotheses.groupby("branch", sort=True):
        group = group.sort_values("loop_index")
        previous_row = None
        for row in group.itertuples(index=False):
            names = {
                str(name).lower()
                for name in (row.factor_names or [])
                if name is not None
            }
            loop_candidates = candidates[
                candidates["branch"].eq(branch)
                & candidates["loop_index"].eq(int(row.loop_index))
            ]
            formulas = {
                str(value).strip()
                for value in loop_candidates["formulation"].dropna()
                if str(value).strip()
            }
            code_hashes = {
                str(value).strip()
                for value in loop_candidates["code_sha256"].dropna()
                if str(value).strip()
            }
            repeated_name = bool(names & factor_names_seen[branch])
            repeated_formula = bool(
                formulas & factor_formulas_seen[branch]
            )
            repeated_code_hash = bool(
                code_hashes & factor_code_hashes_seen[branch]
            )
            text = " ".join(
                [
                    str(row.hypothesis or ""),
                    str(row.reason or ""),
                    " ".join(names),
                    " ".join(formulas),
                    " ".join(
                        loop_candidates["description"]
                        .dropna()
                        .astype(str)
                        .tolist()
                    ),
                ]
            )
            current_families = set(families(text))
            if previous_row is None:
                similarity = np.nan
                transition = "root"
                previous_families: set[str] = set()
            else:
                similarity = cosine(
                    vector_lookup[(branch, int(previous_row.loop_index))],
                    vector_lookup[(branch, int(row.loop_index))],
                )
                previous_text = (
                    f"{previous_row.hypothesis or ''} {previous_row.reason or ''}"
                )
                previous_families = set(families(previous_text))
                if (
                    repeated_name
                    or repeated_formula
                    or repeated_code_hash
                    or similarity >= 0.95
                ):
                    transition = "reuse"
                elif similarity >= 0.80 and bool(
                    current_families & previous_families
                ):
                    transition = "refine"
                else:
                    transition = "shift"
            sensitivity: dict[str, str] = {}
            for threshold in (0.75, 0.80, 0.85):
                column = f"transition_at_refine_{str(threshold).replace('.', '_')}"
                if previous_row is None:
                    sensitivity[column] = "root"
                elif (
                    repeated_name
                    or repeated_formula
                    or repeated_code_hash
                    or similarity >= 0.95
                ):
                    sensitivity[column] = "reuse"
                elif similarity >= threshold and bool(
                    current_families & previous_families
                ):
                    sensitivity[column] = "refine"
                else:
                    sensitivity[column] = "shift"
            transition_rows.append(
                {
                    "branch": branch,
                    "loop_index": int(row.loop_index),
                    "previous_loop_index": (
                        int(previous_row.loop_index) if previous_row else None
                    ),
                    "cosine_to_previous": similarity,
                    "transition": transition,
                    "factor_families": ",".join(sorted(current_families)),
                    "previous_factor_families": ",".join(
                        sorted(previous_families)
                    ),
                    "repeated_factor_name": repeated_name,
                    "repeated_factor_formula": repeated_formula,
                    "repeated_factor_code_hash": repeated_code_hash,
                    **sensitivity,
                }
            )
            factor_names_seen[branch].update(names)
            factor_formulas_seen[branch].update(formulas)
            factor_code_hashes_seen[branch].update(code_hashes)
            previous_row = row
    transitions = pd.DataFrame(transition_rows)
    transitions.to_csv(output_dir / "transition_classification.csv", index=False)

    candidate_summary = (
        candidates.groupby(["branch", "loop_index"])
        .agg(
            generated_factors=("factor_name", "size"),
            implemented_factors=("factor_implementation", "sum"),
            result_available_factors=("result_h5_exists", "sum"),
        )
        .reset_index()
    )
    loop_funnel = loops.merge(
        candidate_summary, on=["branch", "loop_index"], how="left"
    ).merge(
        transitions[
            ["branch", "loop_index", "transition", "factor_families"]
        ],
        on=["branch", "loop_index"],
        how="left",
    )
    if len(confirmations):
        loop_funnel = loop_funnel.merge(
            confirmations[
                [
                    "branch",
                    "loop_index",
                    "predictive_confirmation_pass",
                ]
            ],
            on=["branch", "loop_index"],
            how="left",
        )
    else:
        loop_funnel["predictive_confirmation_pass"] = False
    loop_funnel.to_csv(output_dir / "loop_funnel.csv", index=False)

    family_rows = []
    for branch, group in transitions.groupby("branch"):
        exploded = group.assign(
            factor_family=group["factor_families"].str.split(",")
        ).explode("factor_family")
        for family, family_group in exploded.groupby("factor_family"):
            loop_ids = family_group["loop_index"].unique()
            selected = loop_funnel[
                (loop_funnel["branch"] == branch)
                & loop_funnel["loop_index"].isin(loop_ids)
            ]
            family_rows.append(
                {
                    "branch": branch,
                    "factor_family": family,
                    "loop_count": len(loop_ids),
                    "valid_loops": int(selected["current_ic"].notna().sum()),
                    "accepted_loops": int(selected["decision"].sum()),
                    "confirmed_loops": int(
                        selected["predictive_confirmation_pass"]
                        .fillna(False)
                        .sum()
                    ),
                }
            )
    pd.DataFrame(family_rows).to_csv(
        output_dir / "family_coverage.csv", index=False
    )

    failure_rows = []
    for row in loop_funnel.itertuples(index=False):
        if pd.isna(row.current_ic):
            taxonomy = "runtime_or_result_missing"
        elif not bool(row.decision):
            taxonomy = "valid_but_agent_rejected"
        elif not bool(getattr(row, "predictive_confirmation_pass", False)):
            taxonomy = "agent_accepted_confirmation_failed"
        else:
            taxonomy = "confirmed"
        failure_rows.append(
            {
                "branch": row.branch,
                "loop_index": int(row.loop_index),
                "taxonomy": taxonomy,
            }
        )
    pd.DataFrame(failure_rows).to_csv(
        output_dir / "failure_taxonomy.csv", index=False
    )

    cost_lookup = {row["branch"]: row for row in branch_cost_rows}
    efficiency_rows = []
    for branch, group in loop_funnel.groupby("branch"):
        valid = int(group["current_ic"].notna().sum())
        accepted_count = int(group["decision"].sum())
        confirmed = int(
            group["predictive_confirmation_pass"].fillna(False).sum()
        )
        cost = cost_lookup[branch]["provider_cost_usd"]
        branch_candidates = candidates[candidates["branch"].eq(branch)]
        confirmed_loop_ids = set(
            group.loc[
                group["predictive_confirmation_pass"].fillna(False),
                "loop_index",
            ].astype(int)
        )
        accepted_factor_count = int(
            branch_candidates["decision"].fillna(False).astype(bool).sum()
        )
        confirmed_factor_count = int(
            branch_candidates["loop_index"]
            .astype(int)
            .isin(confirmed_loop_ids)
            .sum()
        )
        efficiency_rows.append(
            {
                "branch": branch,
                "total_loops": len(group),
                "valid_loops": valid,
                "accepted_loops": accepted_count,
                "confirmed_loops": confirmed,
                "generated_factors": int(group["generated_factors"].sum()),
                "implemented_factors": int(group["implemented_factors"].sum()),
                "accepted_factors": accepted_factor_count,
                "confirmed_factors": confirmed_factor_count,
                "implementation_attempt_artifacts": int(
                    attempts.loc[
                        attempts["branch"].eq(branch),
                        "observed_coding_evo_loop_directories",
                    ].sum()
                ),
                "wall_seconds": float(group["wall_seconds"].sum()),
                "wall_seconds_per_valid_loop": (
                    float(group["wall_seconds"].sum()) / valid
                    if valid
                    else np.nan
                ),
                "provider_cost_usd": cost,
                "usd_per_valid_loop": (
                    cost / valid if cost is not None and valid else np.nan
                ),
                "usd_per_accepted_loop": (
                    cost / accepted_count
                    if cost is not None and accepted_count
                    else np.nan
                ),
                "usd_per_accepted_factor": (
                    cost / accepted_factor_count
                    if cost is not None and accepted_factor_count
                    else np.nan
                ),
                "usd_per_confirmed_loop": (
                    cost / confirmed if cost is not None and confirmed else np.nan
                ),
                "usd_per_confirmed_factor": (
                    cost / confirmed_factor_count
                    if cost is not None and confirmed_factor_count
                    else np.nan
                ),
            }
        )
    search_efficiency = pd.DataFrame(efficiency_rows)
    for row_index, row in search_efficiency.iterrows():
        branch = str(row["branch"])
        branch_funnel = loop_funnel[
            loop_funnel["branch"] == branch
        ].sort_values("loop_index")
        branch_accounting = accountings[
            accountings["branch"] == branch
        ].iloc[0]
        for horizon in (1, 3, 5, 10):
            prefix = branch_funnel.head(horizon)
            search_efficiency.loc[row_index, f"implementation_pass_at_{horizon}"] = bool(
                len(prefix)
                and (
                    prefix["result_available_factors"]
                    >= prefix["generated_factors"]
                ).all()
            )
            search_efficiency.loc[row_index, f"agent_accept_pass_at_{horizon}"] = bool(
                prefix["decision"].fillna(False).any()
            )
            search_efficiency.loc[row_index, f"confirmation_pass_at_{horizon}"] = bool(
                prefix["predictive_confirmation_pass"].fillna(False).any()
            )
        prompt_tokens = branch_accounting.get("logged_prompt_tokens_sum")
        search_efficiency.loc[row_index, "prompt_tokens"] = prompt_tokens
        search_efficiency.loc[row_index, "prompt_tokens_per_valid_loop"] = (
            float(prompt_tokens) / float(row["valid_loops"])
            if pd.notna(prompt_tokens) and row["valid_loops"]
            else np.nan
        )
        search_efficiency.loc[row_index, "checkpoint_completeness"] = (
            float(branch_funnel["five_step_checkpoint_complete"].sum())
            / len(branch_funnel)
            if len(branch_funnel)
            else np.nan
        )
        branch_decisions = decisions[decisions["branch"] == branch]
        search_efficiency.loc[row_index, "decision_reconciliation_rate"] = (
            float(branch_decisions["decision_reconciled"].sum())
            / len(branch_decisions)
            if len(branch_decisions)
            else np.nan
        )
    search_efficiency.to_csv(output_dir / "search_efficiency.csv", index=False)

    factor_lifecycle = candidates[
        [
            "branch",
            "loop_index",
            "factor_name",
            "decision",
            "factor_implementation",
            "code_sha256",
            "result_h5_sha256",
        ]
    ].copy()
    if len(confirmations):
        factor_lifecycle = factor_lifecycle.merge(
            confirmations[
                ["branch", "loop_index", "predictive_confirmation_pass"]
            ],
            on=["branch", "loop_index"],
            how="left",
        )
    factor_lifecycle.to_csv(output_dir / "factor_lifecycle.csv", index=False)

    static_summary_path = (
        episode_root
        / phase2["outputs"]["benchmark"]
        / "library_summary.csv"
    )
    static_summary = pd.read_csv(static_summary_path)
    input_files.append(
        {
            "path": str(static_summary_path),
            "sha256": sha256_file(static_summary_path),
        }
    )
    static_lookup = {
        "a20": "A20_RDAGENT_PINNED",
        "a157": "A157_QLIB_NO_VWAP_REGISTERED_ADAPTATION",
    }
    library_rows: list[dict[str, Any]] = []
    for branch, library_id in static_lookup.items():
        static = static_summary[
            static_summary["library_id"] == library_id
        ].iloc[0]
        for _, state in state_summaries[
            state_summaries["branch"] == branch
        ].iterrows():
            row = {
                "branch": branch,
                "state_id": state["state_id"],
                "nominal_factor_count": int(state["feature_count"]),
                "usable_factor_count": int(state["feature_count"]),
                "agent_feedback_ic": state[
                    "agent_feedback_IC_median"
                ],
                "agent_feedback_rank_ic": state[
                    "agent_feedback_Rank IC_median"
                ],
                "selection_confirmation_ic": state[
                    "selection_confirmation_IC_median"
                ],
                "selection_confirmation_rank_ic": state[
                    "selection_confirmation_Rank IC_median"
                ],
                "selection_confirmation_icir": state[
                    "selection_confirmation_ICIR_median"
                ],
                "selection_confirmation_rank_icir": state[
                    "selection_confirmation_Rank ICIR_median"
                ],
                "selection_confirmation_ic_per_factor": (
                    state["selection_confirmation_IC_median"]
                    / int(state["feature_count"])
                ),
                "selection_confirmation_rank_ic_per_factor": (
                    state["selection_confirmation_Rank IC_median"]
                    / int(state["feature_count"])
                ),
                "historical_test_net_arr_per_factor": np.nan,
                "historical_test_read": False,
                "effective_rank": (
                    static["effective_rank"]
                    if state["state_id"] == "static_base"
                    else np.nan
                ),
                "effective_rank_per_factor": (
                    static["effective_rank_per_feature"]
                    if state["state_id"] == "static_base"
                    else np.nan
                ),
                "median_abs_pairwise_corr": (
                    static["median_abs_pairwise_corr"]
                    if state["state_id"] == "static_base"
                    else np.nan
                ),
                "max_abs_pairwise_corr": (
                    static["max_abs_pairwise_corr"]
                    if state["state_id"] == "static_base"
                    else np.nan
                ),
                "abs_corr_ge_0_99_pairs": (
                    static["abs_corr_ge_0_99_pairs"]
                    if state["state_id"] == "static_base"
                    else np.nan
                ),
                "correlation_cluster_count": np.nan,
            }
            library_rows.append(row)
    library_efficiency = pd.DataFrame(library_rows)
    if library_quality_parts:
        evolved_quality = pd.concat(
            library_quality_parts, ignore_index=True
        )
        quality_columns = [
            "branch",
            "state_id",
            "usable_feature_count",
            "effective_rank",
            "effective_rank_per_feature",
            "median_abs_pairwise_corr",
            "max_abs_pairwise_corr",
            "abs_corr_ge_0_99_pairs",
            "correlation_cluster_count",
        ]
        evolved_quality = evolved_quality[
            [column for column in quality_columns if column in evolved_quality]
        ]
        library_efficiency = library_efficiency.drop(
            columns=[
                "usable_factor_count",
                "effective_rank",
                "effective_rank_per_factor",
                "median_abs_pairwise_corr",
                "max_abs_pairwise_corr",
                "abs_corr_ge_0_99_pairs",
                "correlation_cluster_count",
            ]
        ).merge(
            evolved_quality.rename(
                columns={
                    "usable_feature_count": "usable_factor_count",
                    "effective_rank_per_feature": "effective_rank_per_factor",
                }
            ),
            on=["branch", "state_id"],
            how="left",
        )
    library_efficiency.to_csv(
        output_dir / "library_efficiency.csv", index=False
    )

    branch_comparison = search_efficiency.merge(
        library_efficiency[
            library_efficiency["state_id"].eq("ep23_retained")
        ][
            [
                "branch",
                "state_id",
                "nominal_factor_count",
                "selection_confirmation_ic",
                "selection_confirmation_rank_ic",
            ]
        ],
        on="branch",
        how="left",
    )
    branch_comparison.to_csv(
        output_dir / "branch_comparison.csv", index=False
    )

    invalid_dir = (
        episode_root
        / "outputs/23I1_rdfactor_a20_solpro_6h_invalidated_feedback_schema_20260728"
    )
    invalidation = (
        json.loads((invalid_dir / "invalidation.json").read_text(encoding="utf-8"))
        if (invalid_dir / "invalidation.json").exists()
        else {}
    )
    invalid_run = (
        json.loads((invalid_dir / "run_manifest.json").read_text(encoding="utf-8"))
        if (invalid_dir / "run_manifest.json").exists()
        else {}
    )

    embedding_manifest = {
        "generated_at_utc": utc_now(),
        "provider": "openrouter",
        "model": embedding_model,
        "dimension": int(vectors.shape[1]),
        "row_count": int(vectors.shape[0]),
        "proxy_used": True,
        "proxy_url_recorded": False,
        "credential_recorded": False,
        "texts_sha256": canonical_json_sha256(embedding_texts),
        "vectors_sha256": sha256_bytes(vectors.tobytes()),
        "cluster_method": "agglomerative_average_cosine",
        "cluster_distance_threshold": 0.20,
    }
    (output_dir / "embedding_manifest.json").write_text(
        json.dumps(embedding_manifest, ensure_ascii=False, indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    input_manifest = {
        "generated_at_utc": utc_now(),
        "config": {"path": str(config_path), "sha256": sha256_file(config_path)},
        "inputs": input_files,
    }
    (output_dir / "input_manifest.json").write_text(
        json.dumps(input_manifest, ensure_ascii=False, indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    resolved = {
        "experiment_id": "23J_evolution_dynamics",
        "branches": list(BRANCHES),
        "embedding_model": embedding_model,
        "cluster_distance_threshold": 0.20,
        "reuse_cosine_threshold": 0.95,
        "refine_cosine_threshold": 0.80,
        "historical_test_read": False,
    }
    (output_dir / "config.resolved.yaml").write_text(
        yaml.safe_dump(resolved, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    all_decisions_reconciled = bool(
        len(decisions) and decisions["decision_reconciled"].fillna(False).all()
    )
    all_checkpoints_complete = bool(
        loops["five_step_checkpoint_complete"].fillna(False).all()
    )
    all_formal_loops_accounted = all(
        int(cost_lookup[branch].get("raw_status") == "raw_run_complete") == 1
        for branch in BRANCHES
    ) and all_checkpoints_complete
    total_cost = float(
        search_efficiency["provider_cost_usd"].dropna().sum()
    )
    invalidated_cost = invalid_run.get("openrouter_key_usage_delta_usd")
    verdict = {
        "status": (
            "evolution_dynamics_complete_with_cost_caveat"
            if invalidated_cost
            else "evolution_dynamics_complete"
        ),
        "all_formal_loops_accounted_for": all_formal_loops_accounted,
        "all_checkpoint_decisions_reconciled": all_decisions_reconciled,
        "all_five_step_checkpoints_complete": all_checkpoints_complete,
        "loop_count": int(len(loop_funnel)),
        "cluster_count": int(embedding_frame["cluster_id"].nunique()),
        "historical_test_read": False,
        "embedding_model": embedding_model,
        "credential_recorded": False,
        "formal_provider_cost_usd": total_cost,
        "invalidated_schema_bug_run": invalidation,
        "invalidated_schema_bug_cost_usd": invalidated_cost,
        "invalidated_loop_excluded_from_success_denominators": True,
    }
    (output_dir / "verdict.json").write_text(
        json.dumps(verdict, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    report = f"""# EP23 23J 进化路径、搜索效率与因子效率

## 裁决

```text
status = {verdict["status"]}
formal_loop_count = {len(loop_funnel)}
all_formal_loops_accounted_for = {str(all_formal_loops_accounted).lower()}
decision_reconciliation_complete = {str(all_decisions_reconciled).lower()}
historical_test_read = false
formal_provider_cost_usd = {total_cost:.6f}
invalidated_schema_bug_cost_usd = {float(invalidated_cost or 0):.6f}
```

两条正式分支的每个 hypothesis、实现产物、2022 feedback、checkpoint
decision、2023 五 seed confirmation 和去冗余状态均已进入 funnel。被 schema
bug 污染的早期 A20 run 保留成本与故障机制，但明确排除在成功率分母之外。

## 搜索效率

{search_efficiency.to_markdown(index=False)}

## 分支终态比较

{branch_comparison.to_markdown(index=False)}

## 解释边界

- hypothesis embedding 固定为 `{embedding_model}`，只发送 hypothesis/reason；
- transition headline 使用 reuse `0.95`、refine `0.80`，并保留阈值敏感性字段；
- 23J 没有读取 2024–2026 historical test，经济效率由 23L 回填；
- Agent 接受不是 EP23 接受，后者以 2023 matched five-seed gate 为准。
"""
    (output_dir / "report.md").write_text(report, encoding="utf-8")
    print(json.dumps(verdict, indent=2))


if __name__ == "__main__":
    main()
