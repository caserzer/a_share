#!/usr/bin/env python3
"""Run the frozen 23L next-open execution and Big Winner bridge."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml

from ep23_phase2_common import sha256_file
from run_23b_alpha20_lgbm_baseline import (
    correlation_summary,
    daily_correlations,
)
from run_23f_pit_execution_big_winner_bridge import (
    add_benchmarks,
    annualized_return,
    big_winner_readout,
    compile_rules,
    future_left_tail_panel,
    information_ratio,
    load_market_panel,
    max_drawdown,
    resolve_path,
    simulate_executable,
    st_status_builder,
    summarize_returns,
    topk_dropout_proxy,
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def load_inventory(
    episode_root: Path, path: Path
) -> tuple[pd.DataFrame, dict[tuple[str, int], pd.DataFrame]]:
    inventory = pd.read_csv(path)
    predictions: dict[tuple[str, int], pd.DataFrame] = {}
    for row in inventory.itertuples(index=False):
        prediction_path = Path(str(row.prediction_path))
        if not prediction_path.is_absolute():
            prediction_path = episode_root / prediction_path
        frame = pd.read_parquet(prediction_path)
        frame.index = frame.index.set_names(["datetime", "instrument"])
        predictions[(str(row.state_id), int(row.seed))] = frame.sort_index()
    return inventory, predictions


def primary_seed_table(
    predictions: dict[tuple[str, int], pd.DataFrame],
    minimum_cross_section: int,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for (state_id, seed), frame in predictions.items():
        confirmation = frame[
            frame["split"].eq("selection_confirmation")
        ]
        daily = daily_correlations(
            confirmation,
            prediction_column="prediction",
            label_column="paper_proxy",
            minimum_cross_section=minimum_cross_section,
        )
        summary = correlation_summary(daily)
        rows.append(
            {
                "state_id": state_id,
                "seed": seed,
                "selection_confirmation_ic": summary["IC"],
                "selection_confirmation_rank_ic": summary["Rank IC"],
            }
        )
    result = pd.DataFrame(rows)
    result["selected_primary_seed"] = False
    for _, group in result.groupby("state_id"):
        selected = group.sort_values(
            ["selection_confirmation_ic", "seed"],
            ascending=[False, True],
        ).index[0]
        result.loc[selected, "selected_primary_seed"] = True
    result["selection_uses_historical_test"] = False
    return result


def state_pairs(states: set[str]) -> list[tuple[str, str, str]]:
    pairs: list[tuple[str, str, str]] = []
    for branch in ("a20", "a157"):
        base = f"{branch}_static"
        evolved = f"{branch}_evolved"
        if base in states and evolved in states:
            pairs.append((branch, base, evolved))
    if {"a20_model_baseline", "a20_model_evolved"}.issubset(states):
        pairs.append(
            (
                "a20_model",
                "a20_model_baseline",
                "a20_model_evolved",
            )
        )
    return pairs


def episode_diagnostics(
    *,
    topic_root: Path,
    config: dict[str, Any],
    state_id: str,
    score: pd.Series,
    daily: pd.DataFrame,
    holdings: pd.DataFrame,
    market: pd.DataFrame,
    future_tail: pd.Series,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    bridge = config["execution_bridge"]
    threshold_id = str(bridge["right_tail_threshold_id"])
    episodes = pd.read_parquet(
        resolve_path(topic_root, bridge["winner_episode_panel"])
    )
    episodes = episodes[episodes["threshold_id"].eq(threshold_id)].copy()
    episodes["cluster_start_date"] = pd.to_datetime(
        episodes["cluster_start_date"]
    )
    episodes["cluster_end_date"] = pd.to_datetime(
        episodes["cluster_end_date"]
    )
    instruments = set(score.index.get_level_values("instrument").astype(str))
    first_date = pd.Timestamp(daily["trade_date"].min())
    last_date = pd.Timestamp(daily["next_trade_date"].max())
    episodes = episodes[
        episodes["instrument"].astype(str).isin(instruments)
        & episodes["cluster_end_date"].ge(first_date)
        & episodes["cluster_start_date"].le(last_date)
    ].copy()

    holding_keys = {
        (pd.Timestamp(row.trade_date), str(row.instrument))
        for row in holdings.itertuples(index=False)
    }
    decision_to_trade = daily.drop_duplicates("decision_date").set_index(
        "decision_date"
    )["trade_date"]
    scored = score.rename("score").reset_index()
    scored["trade_date"] = scored["datetime"].map(decision_to_trade)
    scored = scored.dropna(subset=["trade_date"])
    interval_map: dict[
        str, list[tuple[pd.Timestamp, pd.Timestamp, str]]
    ] = {}
    for row in episodes.itertuples(index=False):
        interval_map.setdefault(str(row.instrument), []).append(
            (
                pd.Timestamp(row.cluster_start_date),
                pd.Timestamp(row.cluster_end_date),
                str(row.episode_cluster_id),
            )
        )

    def active_clusters(date: pd.Timestamp, instrument: str) -> list[str]:
        return [
            episode_id
            for start, end, episode_id in interval_map.get(instrument, [])
            if start <= date <= end
        ]

    scored["episode_ids"] = [
        active_clusters(pd.Timestamp(date), str(instrument))
        for date, instrument in zip(
            scored["trade_date"], scored["instrument"]
        )
    ]
    scored["winner_episode_active"] = scored["episode_ids"].map(bool)
    tail_index = pd.MultiIndex.from_frame(
        scored[["trade_date", "instrument"]]
    )
    scored["future_min_return"] = future_tail.reindex(tail_index).to_numpy()
    scored["severe_left_tail"] = scored["future_min_return"].le(
        float(bridge["severe_left_tail_threshold"])
    )
    scored["score_decile"] = (
        scored.groupby("datetime")["score"]
        .rank(pct=True, method="first")
        .mul(10)
        .clip(upper=9.999999)
        .astype(int)
        .add(1)
    )
    deciles = (
        scored.groupby("score_decile", as_index=False)
        .agg(
            row_count=("score", "size"),
            mean_score=("score", "mean"),
            winner_episode_rate=("winner_episode_active", "mean"),
            severe_left_tail_rate=("severe_left_tail", "mean"),
            mean_future_min_return=("future_min_return", "mean"),
        )
    )
    deciles.insert(0, "state_id", state_id)
    winner_score_mean = float(
        scored.loc[scored["winner_episode_active"], "score"].mean()
    )
    nonwinner_score_mean = float(
        scored.loc[~scored["winner_episode_active"], "score"].mean()
    )

    rows: list[dict[str, Any]] = []
    for episode in episodes.itertuples(index=False):
        start = pd.Timestamp(episode.cluster_start_date)
        end = pd.Timestamp(episode.cluster_end_date)
        instrument = str(episode.instrument)
        active_scores = scored[
            scored["instrument"].astype(str).eq(instrument)
            & scored["trade_date"].between(start, end)
        ]
        captured_dates = [
            date
            for date in pd.DatetimeIndex(active_scores["trade_date"].unique())
            if (pd.Timestamp(date), instrument) in holding_keys
        ]
        duration = max(1, (end - start).days)
        lifecycle = []
        for date in captured_dates:
            fraction = (pd.Timestamp(date) - start).days / duration
            lifecycle.append(
                "early"
                if fraction < 1 / 3
                else "middle"
                if fraction < 2 / 3
                else "late"
            )
        rows.append(
            {
                "state_id": state_id,
                "episode_cluster_id": str(episode.episode_cluster_id),
                "instrument": instrument,
                "cluster_start_date": start,
                "cluster_end_date": end,
                "captured": bool(captured_dates),
                "captured_trade_day_count": len(captured_dates),
                "early_captured": "early" in lifecycle,
                "middle_captured": "middle" in lifecycle,
                "late_captured": "late" in lifecycle,
                "mean_episode_score": (
                    float(active_scores["score"].mean())
                    if len(active_scores)
                    else np.nan
                ),
                "winner_mean_score_all_rows": winner_score_mean,
                "nonwinner_mean_score_all_rows": nonwinner_score_mean,
                "winner_minus_nonwinner_mean_score": (
                    winner_score_mean - nonwinner_score_mean
                ),
            }
        )
    held_scored = scored[
        [
            (pd.Timestamp(date), str(instrument)) in holding_keys
            for date, instrument in zip(
                scored["trade_date"], scored["instrument"]
            )
        ]
    ]
    false_positive = held_scored[
        ~held_scored["winner_episode_active"]
    ][
        [
            "datetime",
            "trade_date",
            "instrument",
            "score",
            "score_decile",
            "future_min_return",
            "severe_left_tail",
        ]
    ].copy()
    false_positive.insert(0, "state_id", state_id)
    return pd.DataFrame(rows), deciles, false_positive


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, type=Path)
    args = parser.parse_args()
    config_path = args.config.resolve()
    episode_root = config_path.parent
    phase2 = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    base_path = episode_root / phase2["base_config"]
    config = yaml.safe_load(base_path.read_text(encoding="utf-8"))
    topic_root = episode_root.parents[2]
    output_dir = episode_root / phase2["outputs"]["execution_bridge"]
    output_dir.mkdir(parents=True, exist_ok=True)

    inventory_parts: list[pd.DataFrame] = []
    predictions: dict[tuple[str, int], pd.DataFrame] = {}
    input_paths: list[Path] = [config_path, base_path]
    for output_key in ("factor_a20", "factor_a158", "model_a20"):
        inventory_path = (
            episode_root
            / phase2["outputs"][output_key]
            / "23l_prediction_inventory.csv"
        )
        if not inventory_path.exists():
            continue
        inventory, loaded = load_inventory(episode_root, inventory_path)
        inventory_parts.append(inventory)
        predictions.update(loaded)
        input_paths.append(inventory_path)
    if not predictions:
        raise RuntimeError("no frozen 23L prediction inventory")
    inventory = pd.concat(inventory_parts, ignore_index=True)
    states = sorted(inventory["state_id"].astype(str).unique())
    pairs = state_pairs(set(states))
    seed_selection = primary_seed_table(
        predictions,
        int(config["baseline"]["minimum_daily_cross_section"]),
    )

    historical_predictions = {
        key: frame[frame["split"].eq("historical_test")].copy()
        for key, frame in predictions.items()
    }
    score_instruments = sorted(
        {
            str(instrument)
            for frame in historical_predictions.values()
            for instrument in frame.index.get_level_values("instrument")
        }
    )
    bridge = config["execution_bridge"]
    calendar_path = resolve_path(topic_root, bridge["trading_calendar"])
    full_calendar = pd.DatetimeIndex(
        pd.to_datetime(pd.read_csv(calendar_path)["trade_date"])
        .sort_values()
        .unique()
    )
    decision_start = pd.Timestamp(
        phase2["evolution"]["nested_segments"]["historical_test"][0]
    )
    decision_end = pd.Timestamp(
        phase2["evolution"]["nested_segments"]["historical_test"][1]
    )
    start_index = int(full_calendar.searchsorted(decision_start, side="right"))
    end_index = int(full_calendar.searchsorted(decision_end, side="right")) + 1
    calendar = full_calendar[: end_index + 1]
    market = load_market_panel(
        topic_root,
        config,
        score_instruments,
        full_calendar[start_index],
        full_calendar[end_index],
    )
    master = pd.read_csv(resolve_path(topic_root, bridge["security_master"]))
    master = master[master["instrument"].isin(score_instruments)].copy()
    if master["instrument"].nunique() != len(score_instruments):
        raise RuntimeError("security master does not cover frozen score universe")
    master["listing_date"] = pd.to_datetime(master["listing_date"])
    master["delist_date"] = pd.to_datetime(
        master["delist_date"], errors="coerce"
    )
    master = master.drop_duplicates("instrument").set_index("instrument")
    rules = compile_rules(
        resolve_path(topic_root, bridge["market_rule_registry"])
    )
    st_status = st_status_builder(
        topic_root, config, score_instruments, master
    )

    seed_rows: list[dict[str, Any]] = []
    daily_parts: list[pd.DataFrame] = []
    event_parts: list[pd.DataFrame] = []
    holding_parts: list[pd.DataFrame] = []
    paper_parts: list[pd.DataFrame] = []
    topk = int(bridge["primary_topk"])
    n_drop = int(bridge["n_drop"])
    annualization = int(config["portfolio"]["annualization"])
    for (state_id, seed), frame in historical_predictions.items():
        labels = frame[["paper_proxy", "executable_bridge"]]
        score = frame["prediction"]
        paper_daily, _ = topk_dropout_proxy(
            score,
            labels,
            label_column="paper_proxy",
            topk=topk,
            n_drop=n_drop,
            buy_cost=float(config["portfolio"]["buy_cost"]),
            sell_cost=float(config["portfolio"]["sell_cost"]),
        )
        paper_daily["state_id"] = state_id
        paper_daily["seed"] = seed
        paper_parts.append(paper_daily)
        executable, events, holdings = simulate_executable(
            score=score,
            topk=topk,
            n_drop=n_drop,
            config=config,
            calendar=calendar,
            market=market,
            master=master,
            rules=rules,
            st_status=st_status,
            seed=seed,
        )
        for part in (executable, events, holdings):
            part["state_id"] = state_id
        daily_parts.append(executable)
        event_parts.append(events)
        holding_parts.append(holdings)
        paper_summary = summarize_returns(
            paper_daily,
            lane="paper_proxy",
            seed=seed,
            topk=topk,
            annualization=annualization,
        )
        execution_summary = summarize_returns(
            executable,
            lane="next_open_executable",
            seed=seed,
            topk=topk,
            annualization=annualization,
        )
        event_count = len(events)
        blocked = int(events["fill_status"].ne("filled").sum())
        row = {
            "state_id": state_id,
            "seed": seed,
            **{
                f"paper_{key}": value
                for key, value in paper_summary.items()
                if key not in {"lane", "seed", "topk"}
            },
            **{
                f"execution_{key}": value
                for key, value in execution_summary.items()
                if key not in {"lane", "seed", "topk"}
            },
            "filled_order_count": int(
                events["fill_status"].eq("filled").sum()
            ),
            "failed_order_count": blocked,
            "fill_rate": (
                float(events["fill_status"].eq("filled").mean())
                if event_count
                else np.nan
            ),
            "fail_rate": blocked / event_count if event_count else np.nan,
            "delay_rate": float(
                events["blocking_reason"]
                .isin(
                    [
                        "limit_up_blocked",
                        "limit_down_blocked",
                        "suspended_missing_daily_bar",
                    ]
                )
                .mean()
            )
            if event_count
            else np.nan,
            "daily_win_rate": float(executable["net_return"].gt(0).mean()),
        }
        seed_rows.append(row)

    seed_metrics = pd.DataFrame(seed_rows)
    portfolio_daily = pd.concat(daily_parts, ignore_index=True)
    events = pd.concat(event_parts, ignore_index=True)
    holdings = pd.concat(holding_parts, ignore_index=True)
    paper_daily_all = pd.concat(paper_parts, ignore_index=True)

    matched_rows: list[dict[str, Any]] = []
    metric_columns = [
        column
        for column in seed_metrics
        if column not in {"state_id", "seed"}
        and pd.api.types.is_numeric_dtype(seed_metrics[column])
    ]
    for branch, baseline_state, evolved_state in pairs:
        baseline = seed_metrics[
            seed_metrics["state_id"].eq(baseline_state)
        ].set_index("seed")
        evolved = seed_metrics[
            seed_metrics["state_id"].eq(evolved_state)
        ].set_index("seed")
        for seed in sorted(set(baseline.index) & set(evolved.index)):
            for metric in metric_columns:
                base_value = float(baseline.loc[seed, metric])
                evolved_value = float(evolved.loc[seed, metric])
                matched_rows.append(
                    {
                        "branch": branch,
                        "baseline_state_id": baseline_state,
                        "evolved_state_id": evolved_state,
                        "seed": seed,
                        "metric": metric,
                        "baseline_value": base_value,
                        "evolved_value": evolved_value,
                        "delta": evolved_value - base_value,
                    }
                )
    matched = pd.DataFrame(matched_rows)

    annual_rows: list[dict[str, Any]] = []
    portfolio_daily["year"] = pd.to_datetime(
        portfolio_daily["decision_date"]
    ).dt.year
    for (state_id, seed, year), group in portfolio_daily.groupby(
        ["state_id", "seed", "year"], sort=True
    ):
        annual_rows.append(
            {
                "state_id": state_id,
                "seed": seed,
                "year": year,
                "net_arr": annualized_return(
                    group["net_return"], annualization
                ),
                "gross_arr": annualized_return(
                    group["gross_return"], annualization
                ),
                "net_ir": information_ratio(
                    group["net_return"], annualization
                ),
                "net_mdd": max_drawdown(group["net_return"]),
                "mean_one_way_turnover": float(
                    group["one_way_turnover"].mean()
                ),
                "total_cost_cny": float(group["trade_cost_cny"].sum()),
            }
        )
    annual_metrics = pd.DataFrame(annual_rows)

    turnover_cost = (
        portfolio_daily.groupby(["state_id", "seed"], as_index=False)
        .agg(
            mean_one_way_turnover=("one_way_turnover", "mean"),
            turnover_notional_cny=("turnover_notional_cny", "sum"),
            total_trade_cost_cny=("trade_cost_cny", "sum"),
            blocked_order_count=("blocked_order_n", "sum"),
            filled_order_count=("filled_order_n", "sum"),
        )
    )

    future_tail = future_left_tail_panel(
        market,
        int(bridge["severe_left_tail_horizon_sessions"]),
    )
    winner_summary_parts: list[pd.DataFrame] = []
    morphology_parts: list[pd.DataFrame] = []
    episode_parts: list[pd.DataFrame] = []
    decile_parts: list[pd.DataFrame] = []
    false_positive_parts: list[pd.DataFrame] = []
    benchmark_parts: list[pd.DataFrame] = []
    for state_id in states:
        selected = seed_selection[
            seed_selection["state_id"].eq(state_id)
            & seed_selection["selected_primary_seed"]
        ]
        if selected.empty:
            continue
        seed = int(selected.iloc[0]["seed"])
        score = historical_predictions[(state_id, seed)]["prediction"]
        daily = portfolio_daily[
            portfolio_daily["state_id"].eq(state_id)
            & portfolio_daily["seed"].eq(seed)
        ].copy()
        state_holdings = holdings[
            holdings["state_id"].eq(state_id)
            & holdings["seed"].eq(seed)
        ].copy()
        enriched_daily, benchmarks = add_benchmarks(
            topic_root, config, daily, score, market
        )
        benchmarks["state_id"] = state_id
        benchmark_parts.append(benchmarks)
        utility, morphology, _ = big_winner_readout(
            topic_root,
            config,
            score,
            enriched_daily,
            state_holdings,
            market,
        )
        utility.insert(0, "state_id", state_id)
        utility["seed"] = seed
        morphology.insert(0, "state_id", state_id)
        morphology["seed"] = seed
        winner_summary_parts.append(utility)
        morphology_parts.append(morphology)
        episode_detail, deciles, false_positive = episode_diagnostics(
            topic_root=topic_root,
            config=config,
            state_id=state_id,
            score=score,
            daily=enriched_daily,
            holdings=state_holdings,
            market=market,
            future_tail=future_tail,
        )
        episode_detail["seed"] = seed
        deciles["seed"] = seed
        false_positive["seed"] = seed
        episode_parts.append(episode_detail)
        decile_parts.append(deciles)
        false_positive_parts.append(false_positive)

    winner_summary = pd.concat(winner_summary_parts, ignore_index=True)
    episode_details = pd.concat(episode_parts, ignore_index=True)
    false_positive_details = pd.concat(
        false_positive_parts, ignore_index=True
    )
    episode_concentration_rows = []
    for state_id, group in episode_details.groupby("state_id"):
        captured = group[group["captured"]]
        total_days = float(captured["captured_trade_day_count"].sum())
        episode_concentration_rows.append(
            {
                "state_id": state_id,
                "largest_episode_capture_day_share": (
                    float(
                        captured["captured_trade_day_count"].max()
                        / total_days
                    )
                    if total_days > 0
                    else np.nan
                ),
            }
        )
    episode_concentration = pd.DataFrame(episode_concentration_rows)
    big_winner_metrics = pd.concat(
        [
            winner_summary.assign(record_type="state_summary"),
            episode_details.assign(record_type="episode_detail"),
            false_positive_details.assign(
                record_type="false_positive_exposure"
            ),
        ],
        ignore_index=True,
        sort=False,
    )
    morphology_metrics = pd.concat(
        morphology_parts, ignore_index=True
    )
    score_deciles = pd.concat(decile_parts, ignore_index=True)
    benchmarks = pd.concat(benchmark_parts, ignore_index=True)

    concentration_rows: list[dict[str, Any]] = []
    for (state_id, seed), group in events[
        events["fill_status"].eq("filled")
    ].groupby(["state_id", "seed"]):
        by_instrument = (
            group.groupby("instrument")["executed_notional_cny"].sum().sort_values(
                ascending=False
            )
        )
        total = float(by_instrument.sum())
        state_daily = portfolio_daily[
            portfolio_daily["state_id"].eq(state_id)
            & portfolio_daily["seed"].eq(seed)
        ]
        next_date_lookup = state_daily.drop_duplicates(
            "trade_date"
        ).set_index("trade_date")["next_trade_date"]
        state_holdings = holdings[
            holdings["state_id"].eq(state_id)
            & holdings["seed"].eq(seed)
        ].copy()
        contribution_rows = []
        for holding in state_holdings.itertuples(index=False):
            trade_date = pd.Timestamp(holding.trade_date)
            next_date = next_date_lookup.get(trade_date)
            first_key = (trade_date, str(holding.instrument))
            second_key = (
                pd.Timestamp(next_date),
                str(holding.instrument),
            )
            if (
                next_date is None
                or first_key not in market.index
                or second_key not in market.index
            ):
                continue
            start_open = float(market.loc[first_key]["qfq_open"])
            end_open = float(market.loc[second_key]["qfq_open"])
            if start_open <= 0 or not np.isfinite(end_open):
                continue
            contribution_rows.append(
                {
                    "instrument": str(holding.instrument),
                    "contribution": float(holding.position_weight)
                    * (end_open / start_open - 1.0),
                }
            )
        contribution_frame = pd.DataFrame(contribution_rows)
        by_contribution = (
            contribution_frame.groupby("instrument")["contribution"].sum()
            if len(contribution_frame)
            else pd.Series(dtype=float)
        )
        positive_total = float(
            by_contribution[by_contribution > 0].sum()
        )
        negative_total = float(
            by_contribution[by_contribution < 0].abs().sum()
        )
        daily_abs_total = float(state_daily["net_return"].abs().sum())
        concentration_rows.append(
            {
                "state_id": state_id,
                "seed": seed,
                "instrument_count": len(by_instrument),
                "top1_trade_notional_share": (
                    float(by_instrument.iloc[0] / total)
                    if total > 0
                    else np.nan
                ),
                "top5_trade_notional_share": (
                    float(by_instrument.head(5).sum() / total)
                    if total > 0
                    else np.nan
                ),
                "single_instrument_dominance": bool(
                    total > 0 and by_instrument.iloc[0] / total > 0.20
                ),
                "top_positive_contribution_share": (
                    float(by_contribution.max() / positive_total)
                    if positive_total > 0 and len(by_contribution)
                    else np.nan
                ),
                "bottom_negative_contribution_share": (
                    float(
                        abs(by_contribution.min()) / negative_total
                    )
                    if negative_total > 0 and len(by_contribution)
                    else np.nan
                ),
                "max_abs_daily_net_return_share": (
                    float(
                        state_daily["net_return"].abs().max()
                        / daily_abs_total
                    )
                    if daily_abs_total > 0
                    else np.nan
                ),
            }
        )
    concentration = pd.DataFrame(concentration_rows)
    concentration = concentration.merge(
        episode_concentration, on="state_id", how="left"
    )

    branch_gates: dict[str, dict[str, Any]] = {}
    for branch, baseline_state, evolved_state in pairs:
        delta = matched[
            matched["branch"].eq(branch)
            & matched["metric"].eq("execution_net_arr")
        ]
        positive_seeds = int(delta["delta"].gt(0).sum())
        winner_base = winner_summary[
            winner_summary["state_id"].eq(baseline_state)
        ].iloc[0]
        winner_evolved = winner_summary[
            winner_summary["state_id"].eq(evolved_state)
        ].iloc[0]
        evolved_seed_metrics = seed_metrics[
            seed_metrics["state_id"].eq(evolved_state)
        ]
        sign_reversal_count = int(
            (
                np.sign(evolved_seed_metrics["paper_net_arr"])
                != np.sign(evolved_seed_metrics["execution_net_arr"])
            ).sum()
        )
        gate = {
            "right_tail_enrichment_gt_1": bool(
                winner_evolved["right_tail_exposure_enrichment"] > 1.0
            ),
            "winner_recall_increment_positive": bool(
                winner_evolved["winner_episode_recall"]
                > winner_base["winner_episode_recall"]
            ),
            "severe_left_tail_within_tolerance": bool(
                winner_evolved["severe_left_tail_excess"]
                <= float(bridge["left_tail_excess_tolerance"])
            ),
            "not_single_morphology": bool(
                winner_evolved["largest_captured_morphology_share"]
                <= float(bridge["maximum_single_morphology_capture_share"])
            ),
            "no_next_open_sign_reversal_all_seeds": sign_reversal_count == 0,
            "matched_net_arr_improves_4_of_5": positive_seeds >= 4,
            "not_single_instrument_dominated": not bool(
                (
                    concentration[
                        concentration["state_id"].eq(evolved_state)
                    ][
                        [
                            "single_instrument_dominance",
                        ]
                    ].any(axis=None)
                )
            ),
            "not_single_day_dominated": bool(
                concentration[
                    concentration["state_id"].eq(evolved_state)
                ]["max_abs_daily_net_return_share"].max()
                <= 0.20
            ),
            "not_single_performance_contributor": bool(
                max(
                    concentration[
                        concentration["state_id"].eq(evolved_state)
                    ]["top_positive_contribution_share"].max(),
                    concentration[
                        concentration["state_id"].eq(evolved_state)
                    ]["bottom_negative_contribution_share"].max(),
                )
                <= 0.20
            ),
            "not_single_episode_dominated": bool(
                concentration[
                    concentration["state_id"].eq(evolved_state)
                ]["largest_episode_capture_day_share"].max()
                <= 0.20
            ),
        }
        selector_supported = all(gate.values())
        economic_supported = bool(
            delta["delta"].median() > 0 and positive_seeds >= 4
        )
        branch_gates[branch] = {
            "baseline_state_id": baseline_state,
            "evolved_state_id": evolved_state,
            "checks": gate,
            "big_winner_selector_increment_supported": selector_supported,
            "economic_evolution_supported": economic_supported,
            "evolution_supported": selector_supported and economic_supported,
            "matched_net_arr_delta_median": float(delta["delta"].median()),
            "matched_net_arr_positive_seeds": positive_seeds,
        }

    factor_pass = any(
        value["evolution_supported"]
        for key, value in branch_gates.items()
        if key in {"a20", "a157"}
    )
    model_pass = any(
        value["evolution_supported"]
        for key, value in branch_gates.items()
        if key == "a20_model"
    )
    frozen_registry = {
        "generated_at_utc": utc_now(),
        "states": states,
        "pairs": [
            {
                "branch": branch,
                "baseline_state_id": baseline,
                "evolved_state_id": evolved,
            }
            for branch, baseline, evolved in pairs
        ],
        "prediction_artifacts": inventory.to_dict(orient="records"),
        "primary_seed_selection": seed_selection.to_dict(orient="records"),
        "factor_model_mutually_compatible": bool(
            factor_pass and model_pass
        ),
        "candidate_selection_uses_historical_test": False,
        "frozen_before_historical_test_read": True,
    }
    write_json(
        output_dir / "frozen_candidate_registry.json", frozen_registry
    )
    write_json(
        output_dir / "execution_reconciliation.json",
        {
            "phase1_state_machine_reused": True,
            "score_time": "close_t",
            "execution_time": "next_tradable_open",
            "dynamic_membership": True,
            "suspension_st_listing_delisting_and_price_limits": True,
            "topk": topk,
            "dropout": n_drop,
            "cost_and_slippage_config_sha256": sha256_file(base_path),
            "silent_approximations": [],
        },
    )
    (output_dir / "config.resolved.yaml").write_text(
        yaml.safe_dump(
            {
                "experiment_id": "23L_factor_library_execution_big_winner_bridge",
                "segments": phase2["evolution"]["nested_segments"],
                "states": states,
                "pairs": pairs,
                "evidence_class": "design_contaminated_historical_real_market_evidence",
                "deployment_authorized": False,
            },
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    write_json(
        output_dir / "input_manifest.json",
        {
            "generated_at_utc": utc_now(),
            "inputs": [
                {"path": str(path), "sha256": sha256_file(path)}
                for path in input_paths
            ],
            "prediction_artifact_count": len(inventory),
            "historical_test_first_read_in_23l": True,
        },
    )

    seed_metrics.to_csv(output_dir / "seed_metrics.csv", index=False)
    matched.to_csv(output_dir / "matched_seed_deltas.csv", index=False)
    annual_metrics.to_csv(output_dir / "annual_metrics.csv", index=False)
    portfolio_daily.to_csv(output_dir / "portfolio_daily.csv", index=False)
    events.to_csv(output_dir / "order_event_audit.csv", index=False)
    turnover_cost.to_csv(
        output_dir / "turnover_cost_decomposition.csv", index=False
    )
    big_winner_metrics.to_csv(
        output_dir / "big_winner_episode_metrics.csv", index=False
    )
    morphology_metrics.to_csv(
        output_dir / "big_winner_morphology_metrics.csv", index=False
    )
    score_deciles.to_csv(
        output_dir / "big_winner_score_deciles.csv", index=False
    )
    concentration.to_csv(output_dir / "concentration_audit.csv", index=False)
    benchmarks.to_csv(output_dir / "benchmark_comparison.csv", index=False)
    paper_daily_all.to_csv(output_dir / "paper_proxy_daily.csv", index=False)
    holdings.to_parquet(
        output_dir / "daily_holdings.parquet", index=False
    )
    seed_selection.to_csv(
        output_dir / "seed_selection_audit.csv", index=False
    )

    verdict = {
        "status": "execution_big_winner_bridge_complete",
        "evidence_class": "design_contaminated_historical_real_market_evidence",
        "deployment_authorized": False,
        "factor_branch_pass": factor_pass,
        "model_branch_pass": model_pass,
        "branch_gates": branch_gates,
        "candidate_selection_uses_historical_test": False,
        "historical_test_read": True,
    }
    write_json(output_dir / "verdict.json", verdict)
    report = f"""# EP23 23L 因子/模型进化的 Next-Open 与 Big Winner Bridge

## 裁决

```text
status = execution_big_winner_bridge_complete
factor_branch_pass = {str(factor_pass).lower()}
model_branch_pass = {str(model_pass).lower()}
evidence = design_contaminated_historical_real_market_evidence
deployment_authorized = false
```

23L 只接收在 2023 confirmation 后冻结的候选，并首次读取
2024-01-02..2026-05-27 historical test。每个 evolved state 只与自己的
static/model start 作 matched five-seed 比较。

## 分支 Gate

```json
{json.dumps(branch_gates, ensure_ascii=False, indent=2, sort_keys=True)}
```

完整的 seed 经济指标、next-open 订单事件、成本分解、winner episode 明细、
morphology、score decile 和集中度审计均保存在同目录结构化文件。结果不能
视为生产授权。
"""
    (output_dir / "report.md").write_text(report, encoding="utf-8")
    print(json.dumps(verdict, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
