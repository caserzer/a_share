#!/usr/bin/env python3
"""EP23 23F: frozen-score PIT execution and Big Winner utility bridge."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any, Iterable, Mapping

import numpy as np
import pandas as pd
import yaml


RUN_ID = "23F_pit_execution_big_winner_bridge"
EVIDENCE_CLASS = "design_contaminated_historical_real_market_evidence"


@dataclass
class Position:
    shares: float
    last_mark_qfq: float


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def find_topic_root(config_path: Path) -> Path:
    for parent in [config_path.parent, *config_path.parents]:
        if parent.name == "02_AFML_BIG_WINNER":
            return parent
    raise RuntimeError("cannot resolve topics/02_AFML_BIG_WINNER root")


def resolve_path(topic_root: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else topic_root / path


def round_half_up_to_tick(value: float, tick_size: float) -> float:
    ticks = (Decimal(str(value)) / Decimal(str(tick_size))).quantize(
        Decimal("1"), rounding=ROUND_HALF_UP
    )
    return float(ticks * Decimal(str(tick_size)))


def annualized_return(values: Iterable[float], annualization: int = 252) -> float:
    array = np.asarray(list(values), dtype=float)
    array = array[np.isfinite(array)]
    if not len(array):
        return math.nan
    wealth = float(np.prod(1.0 + array))
    return wealth ** (annualization / len(array)) - 1.0 if wealth > 0 else -1.0


def information_ratio(values: Iterable[float], annualization: int = 252) -> float:
    array = np.asarray(list(values), dtype=float)
    array = array[np.isfinite(array)]
    if len(array) < 2 or np.std(array, ddof=1) <= 0:
        return math.nan
    return float(np.mean(array) / np.std(array, ddof=1) * np.sqrt(annualization))


def max_drawdown(values: Iterable[float]) -> float:
    array = np.asarray(list(values), dtype=float)
    wealth = np.cumprod(1.0 + np.nan_to_num(array, nan=0.0))
    if not len(wealth):
        return math.nan
    peak = np.maximum.accumulate(np.r_[1.0, wealth])[1:]
    return float(np.min(wealth / peak - 1.0))


def bool_value(value: Any) -> bool:
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    return str(value).strip().lower() in {"1", "true", "yes", "pass"}


def order_costs(
    side: str,
    notional: float,
    transfer_fee_bps: float,
    config: Mapping[str, Any],
) -> dict[str, float]:
    commission_bps = float(
        config[
            "commission_buy_bps" if side == "buy" else "commission_sell_bps"
        ]
    )
    commission = (
        max(
            notional * commission_bps / 10000.0,
            float(config["minimum_commission_cny"]),
        )
        if notional > 0
        else 0.0
    )
    stamp = (
        notional * float(config["stamp_tax_sell_bps"]) / 10000.0
        if side == "sell"
        else 0.0
    )
    transfer = notional * transfer_fee_bps / 10000.0
    slippage = notional * float(config["reference_slippage_bps"]) / 10000.0
    return {
        "commission_cny": commission,
        "stamp_tax_cny": stamp,
        "transfer_fee_cny": transfer,
        "slippage_cny": slippage,
        "total_cost_cny": commission + stamp + transfer + slippage,
    }


def lot_floor(shares: float, minimum: int, increment: int) -> float:
    if shares < minimum:
        return 0.0
    return float(minimum + math.floor((shares - minimum) / increment) * increment)


def load_predictions(
    topic_root: Path,
    config: Mapping[str, Any],
) -> tuple[dict[int, pd.DataFrame], pd.DataFrame, int, Path]:
    formal_root = resolve_path(topic_root, config["outputs"]["model_attribution_formal"])
    seed_metrics = pd.read_csv(formal_root / "seed_metrics.csv")
    rows = seed_metrics[seed_metrics["variant"].eq("last_state_gru")].copy()
    metric = str(config["execution_bridge"]["primary_seed_selection_metric"])
    rows = rows.sort_values([metric, "seed"], ascending=[False, True])
    primary_seed = int(rows.iloc[0]["seed"])

    cache_root = resolve_path(topic_root, config["outputs"]["local_cache"])
    prediction_roots = sorted(cache_root.glob("23d1_*"))
    if len(prediction_roots) != 1:
        raise RuntimeError(f"expected one 23D1 cache root, found {len(prediction_roots)}")
    prediction_root = prediction_roots[0]
    predictions: dict[int, pd.DataFrame] = {}
    for seed in map(int, config["model_attribution"]["formal_seeds"]):
        path = prediction_root / f"last_state_gru_{seed}.predictions.parquet"
        frame = pd.read_parquet(path)
        frame = frame[frame["split"].eq("historical_test")][["prediction"]].copy()
        frame.index = frame.index.set_names(["datetime", "instrument"])
        predictions[seed] = frame.sort_index()
    return predictions, seed_metrics, primary_seed, prediction_root


def load_label_panel(
    topic_root: Path,
    config: Mapping[str, Any],
    prediction_index: pd.MultiIndex,
) -> pd.DataFrame:
    cache_root = resolve_path(topic_root, config["outputs"]["local_cache"])
    path = cache_root / "alpha20_dual_label_panel_model_attribution.parquet"
    frame = pd.read_parquet(path, columns=["paper_proxy", "executable_bridge"])
    return frame.reindex(prediction_index)


def topk_dropout_proxy(
    score: pd.Series,
    labels: pd.DataFrame,
    *,
    label_column: str,
    topk: int,
    n_drop: int,
    buy_cost: float,
    sell_cost: float,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    frame = labels[[label_column]].join(score.rename("prediction"), how="inner")
    holdings: set[str] = set()
    rows: list[dict[str, Any]] = []
    holding_rows: list[dict[str, Any]] = []
    for date, group in frame.groupby(level="datetime", sort=True):
        clean = group.dropna().reset_index("datetime", drop=True)
        clean = clean[~clean.index.duplicated(keep="last")]
        if len(clean) < topk:
            continue
        ranked = clean.sort_values(
            ["prediction"], ascending=False, kind="mergesort"
        )
        ranked = ranked.assign(_instrument=ranked.index.astype(str)).sort_values(
            ["prediction", "_instrument"],
            ascending=[False, True],
            kind="mergesort",
        )
        available = set(ranked.index.astype(str))
        prior = holdings & available
        forced_sells = holdings - available
        prior_ranked = [
            str(instrument)
            for instrument in ranked.index
            if str(instrument) in prior
        ]
        optional_drop = set(prior_ranked[-min(n_drop, len(prior_ranked)) :])
        retained = prior - optional_drop
        additions = [
            str(instrument)
            for instrument in ranked.index
            if str(instrument) not in retained
        ][: topk - len(retained)]
        new_holdings = retained | set(additions)
        sold = (holdings - new_holdings) | forced_sells
        bought = new_holdings - holdings
        gross_return = float(clean.loc[list(new_holdings), label_column].mean())
        buy_fraction = len(bought) / topk
        sell_fraction = len(sold) / topk
        cost = buy_fraction * buy_cost + sell_fraction * sell_cost
        rows.append(
            {
                "decision_date": pd.Timestamp(date),
                "gross_return": gross_return,
                "net_return": gross_return - cost,
                "universe_equal_weight_return": float(clean[label_column].mean()),
                "buy_fraction": buy_fraction,
                "sell_fraction": sell_fraction,
                "one_way_turnover": 0.5 * (buy_fraction + sell_fraction),
                "cost": cost,
                "holding_n": len(new_holdings),
            }
        )
        holding_rows.extend(
            {
                "decision_date": pd.Timestamp(date),
                "instrument": instrument,
            }
            for instrument in sorted(new_holdings)
        )
        holdings = new_holdings
    return pd.DataFrame(rows), pd.DataFrame(holding_rows)


def load_market_panel(
    topic_root: Path,
    config: Mapping[str, Any],
    instruments: Iterable[str],
    start: pd.Timestamp,
    end: pd.Timestamp,
) -> pd.DataFrame:
    bridge = config["execution_bridge"]
    raw_root = resolve_path(topic_root, bridge["raw_ohlcv_root"])
    qfq_root = resolve_path(topic_root, bridge["qfq_ohlcv_root"])
    rows: list[pd.DataFrame] = []
    columns = ["date", "open", "high", "low", "close"]
    for instrument in sorted(set(instruments)):
        raw_path = raw_root / f"{instrument}.csv"
        qfq_path = qfq_root / f"{instrument}.csv"
        if not raw_path.is_file() or not qfq_path.is_file():
            raise RuntimeError(f"missing raw/qfq pair: {instrument}")
        raw = pd.read_csv(raw_path, usecols=columns)
        qfq = pd.read_csv(qfq_path, usecols=columns)
        raw["date"] = pd.to_datetime(raw["date"])
        qfq["date"] = pd.to_datetime(qfq["date"])
        raw["previous_raw_close"] = pd.to_numeric(
            raw["close"], errors="coerce"
        ).shift(1)
        raw = raw[raw["date"].between(start - pd.Timedelta(days=15), end)]
        qfq = qfq[qfq["date"].between(start - pd.Timedelta(days=15), end)]
        raw = raw.rename(
            columns={name: f"raw_{name}" for name in columns[1:]}
        )
        qfq = qfq.rename(
            columns={name: f"qfq_{name}" for name in columns[1:]}
        )
        merged = raw.merge(qfq, on="date", how="outer", validate="one_to_one")
        merged["instrument"] = instrument
        rows.append(merged)
    panel = pd.concat(rows, ignore_index=True).rename(columns={"date": "trade_date"})
    price_columns = [
        f"{kind}_{field}"
        for kind in ("raw", "qfq")
        for field in ("open", "high", "low", "close")
    ]
    for column in [*price_columns, "previous_raw_close"]:
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
    panel["mapping_pass"] = (
        panel["raw_qfq_factor"].gt(0)
        & panel["relative_ratio_spread"].le(0.01)
    )
    return panel.set_index(["trade_date", "instrument"]).sort_index()


def compile_rules(path: Path) -> list[dict[str, Any]]:
    frame = pd.read_csv(path)
    rules: list[dict[str, Any]] = []
    for row in frame.to_dict("records"):
        item = dict(row)
        item["_start"] = pd.Timestamp(item["effective_start_date"])
        item["_end"] = pd.to_datetime(item["effective_end_date"], errors="coerce")
        item["_listing_min"] = int(item["listing_session_min"])
        item["_listing_max"] = pd.to_numeric(
            item["listing_session_max"], errors="coerce"
        )
        item["_is_st"] = bool_value(item["is_st"])
        rules.append(item)
    return rules


def st_status_builder(
    topic_root: Path,
    config: Mapping[str, Any],
    instruments: Iterable[str],
    master: pd.DataFrame,
):
    bridge = config["execution_bridge"]
    sh_root = resolve_path(topic_root, bridge["sh_name_history_root"])
    sz_path = resolve_path(topic_root, bridge["sz_name_history"])
    sz = pd.read_csv(sz_path, dtype=str).rename(
        columns={
            "变更日期": "change_date",
            "证券代码": "code",
            "变更前简称": "previous_name",
            "变更后简称": "next_name",
        }
    )
    sz["change_date"] = pd.to_datetime(sz["change_date"], errors="coerce")
    sz["code"] = sz["code"].astype(str).str.extract(r"(\d{6})", expand=False)
    sz = sz.dropna(subset=["change_date", "code"]).sort_values(
        ["code", "change_date"]
    )

    def has_st(value: Any) -> bool:
        text = str(value).upper().replace("＊", "*").replace("Ｓ", "S").replace("Ｔ", "T")
        return "ST" in text

    sh_lifetime: dict[str, bool] = {}
    sz_history: dict[str, tuple[np.ndarray, list[str], str]] = {}
    for instrument in sorted(set(instruments)):
        meta = master.loc[instrument]
        if str(meta["exchange"]) == "SH":
            path = sh_root / f"{instrument}.csv"
            value = False
            if path.is_file():
                frame = pd.read_csv(path, dtype=str)
                for column in ("name", "名称", "证券简称", "变更前简称", "变更后简称"):
                    if column in frame and frame[column].map(has_st).any():
                        value = True
            sh_lifetime[instrument] = value
        elif str(meta["exchange"]) == "SZ":
            local = sz[sz["code"].eq(instrument[-6:])]
            if len(local):
                dates = local["change_date"].to_numpy(dtype="datetime64[ns]")
                names = local["next_name"].fillna("").astype(str).tolist()
                first = str(local.iloc[0]["previous_name"])
                sz_history[instrument] = (dates, names, first)

    def status(instrument: str, date: pd.Timestamp) -> bool:
        exchange = str(master.loc[instrument, "exchange"])
        if exchange == "SH":
            return sh_lifetime.get(instrument, False)
        if exchange == "SZ" and instrument in sz_history:
            dates, names, first = sz_history[instrument]
            index = int(np.searchsorted(dates, np.datetime64(date), side="right") - 1)
            return has_st(first if index < 0 else names[index])
        return has_st(master.loc[instrument, "name"])

    return status


def match_rule(
    rules: list[dict[str, Any]],
    *,
    exchange: str,
    board_bucket: str,
    is_st: bool,
    trade_date: pd.Timestamp,
    listing_session: int,
) -> Mapping[str, Any]:
    matched = [
        rule
        for rule in rules
        if rule["exchange"] in {exchange, "ALL"}
        and rule["board_bucket"] == board_bucket
        and rule["_is_st"] == is_st
        and rule["_start"] <= trade_date
        and (pd.isna(rule["_end"]) or rule["_end"] >= trade_date)
        and rule["_listing_min"] <= listing_session
        and (
            pd.isna(rule["_listing_max"])
            or float(rule["_listing_max"]) >= listing_session
        )
        and bool_value(rule["human_verified"])
    ]
    if len(matched) != 1:
        raise RuntimeError(
            f"market rule unique-hit failed: {exchange}/{board_bucket}/"
            f"st={is_st}/{trade_date.date()}/session={listing_session}/n={len(matched)}"
        )
    return matched[0]


def simulate_executable(
    *,
    score: pd.Series,
    topk: int,
    n_drop: int,
    config: Mapping[str, Any],
    calendar: pd.DatetimeIndex,
    market: pd.DataFrame,
    master: pd.DataFrame,
    rules: list[dict[str, Any]],
    st_status,
    seed: int,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    bridge = config["execution_bridge"]
    initial_aum = float(bridge["initial_aum_cny"])
    cash = initial_aum
    positions: dict[str, Position] = {}
    events: list[dict[str, Any]] = []
    holdings: list[dict[str, Any]] = []
    daily: list[dict[str, Any]] = []

    scores_by_date = {
        pd.Timestamp(date): group.droplevel("datetime").iloc[:, 0]
        for date, group in score.to_frame("prediction").groupby(
            level="datetime", sort=True
        )
    }
    decisions = sorted(scores_by_date)
    decision_to_trade: dict[pd.Timestamp, pd.Timestamp] = {}
    for decision in decisions:
        index = int(calendar.searchsorted(decision, side="right"))
        if index >= len(calendar):
            raise RuntimeError(f"no next session after {decision}")
        decision_to_trade[decision] = pd.Timestamp(calendar[index])
    trade_to_decision = {trade: decision for decision, trade in decision_to_trade.items()}
    last_trade = max(trade_to_decision)
    terminal_index = int(calendar.get_loc(last_trade)) + 1
    if terminal_index >= len(calendar):
        raise RuntimeError("no terminal mark session")
    terminal = pd.Timestamp(calendar[terminal_index])
    simulation_dates = sorted([*trade_to_decision, terminal])

    calendar_positions = {pd.Timestamp(date): i for i, date in enumerate(calendar)}
    listing_indices = {
        instrument: int(calendar.searchsorted(master.loc[instrument, "listing_date"]))
        for instrument in master.index
    }

    def mark(trade_date: pd.Timestamp) -> tuple[float, dict[str, float]]:
        values: dict[str, float] = {}
        for instrument, position in positions.items():
            key = (trade_date, instrument)
            price = math.nan
            if key in market.index:
                price = float(market.loc[key]["qfq_open"])
            if np.isfinite(price) and price > 0:
                position.last_mark_qfq = price
            values[instrument] = position.shares * position.last_mark_qfq
        return cash + sum(values.values()), values

    event_sequence = 0

    def execute(
        trade_date: pd.Timestamp,
        instrument: str,
        side: str,
        requested_shares: float,
        reason: str,
    ) -> tuple[bool, float]:
        nonlocal cash, event_sequence
        event_sequence += 1
        before = positions.get(instrument)
        before_shares = before.shares if before else 0.0
        base = {
            "seed": seed,
            "topk": topk,
            "trade_date": trade_date,
            "event_sequence": event_sequence,
            "instrument": instrument,
            "side": side,
            "event_reason": reason,
            "requested_shares": float(requested_shares),
            "shares_before": float(before_shares),
            "cash_before": float(cash),
        }
        key = (trade_date, instrument)
        meta = master.loc[instrument]
        listed = (
            trade_date >= meta["listing_date"]
            and (pd.isna(meta["delist_date"]) or trade_date < meta["delist_date"])
        )
        blocking = ""
        rule: Mapping[str, Any] | None = None
        price: pd.Series | None = None
        if key not in market.index:
            blocking = "suspended_missing_daily_bar"
        elif not listed:
            blocking = "not_listed"
        else:
            price = market.loc[key]
            if not bool_value(price["mapping_pass"]):
                blocking = "raw_qfq_mapping_blocked"
            else:
                listing_session = calendar_positions[trade_date] - listing_indices[instrument] + 1
                rule = match_rule(
                    rules,
                    exchange=str(meta["exchange"]),
                    board_bucket=str(meta["board_bucket"]),
                    is_st=st_status(instrument, trade_date),
                    trade_date=trade_date,
                    listing_session=listing_session,
                )
                raw_open = float(price["raw_open"])
                if not bool_value(rule["no_limit_flag"]):
                    previous = float(price["previous_raw_close"])
                    if not np.isfinite(previous) or previous <= 0:
                        blocking = "missing_previous_raw_close"
                    else:
                        tick = float(rule["tick_size"])
                        upper = round_half_up_to_tick(
                            previous * (1.0 + float(rule["daily_limit_up_rate"])),
                            tick,
                        )
                        lower = round_half_up_to_tick(
                            previous * (1.0 - float(rule["daily_limit_down_rate"])),
                            tick,
                        )
                        if side == "buy" and raw_open >= upper - 0.5 * tick:
                            blocking = "limit_up_blocked"
                        if side == "sell" and raw_open <= lower + 0.5 * tick:
                            blocking = "limit_down_blocked"
        if blocking:
            events.append(
                {
                    **base,
                    "fill_status": "blocked_unfilled",
                    "blocking_reason": blocking,
                    "fill_price_qfq": math.nan,
                    "executed_shares": 0.0,
                    "executed_notional_cny": 0.0,
                    "total_cost_cny": 0.0,
                    "shares_after": float(before_shares),
                    "cash_after": float(cash),
                }
            )
            return False, 0.0

        assert price is not None and rule is not None
        fill = float(price["qfq_open"])
        minimum = int(rule["minimum_buy_order_shares"])
        increment = int(rule["buy_order_increment_shares"])
        transfer = float(
            rule[
                "transfer_fee_buy_bps" if side == "buy" else "transfer_fee_sell_bps"
            ]
        )
        if side == "buy":
            shares = lot_floor(requested_shares, minimum, increment)
            while shares > 0:
                costs = order_costs(side, shares * fill, transfer, bridge)
                if shares * fill + costs["total_cost_cny"] <= cash + 1e-8:
                    break
                shares = lot_floor(shares - increment, minimum, increment)
        else:
            shares = float(before_shares)
            costs = order_costs(side, shares * fill, transfer, bridge)
        if shares <= 0:
            events.append(
                {
                    **base,
                    "fill_status": "blocked_unfilled",
                    "blocking_reason": "cash_or_lot_constraint",
                    "fill_price_qfq": fill,
                    "executed_shares": 0.0,
                    "executed_notional_cny": 0.0,
                    "total_cost_cny": 0.0,
                    "shares_after": float(before_shares),
                    "cash_after": float(cash),
                }
            )
            return False, 0.0
        notional = shares * fill
        costs = order_costs(side, notional, transfer, bridge)
        if side == "buy":
            cash -= notional + costs["total_cost_cny"]
            if before is None:
                positions[instrument] = Position(shares, fill)
            else:
                before.shares += shares
                before.last_mark_qfq = fill
        else:
            cash += notional - costs["total_cost_cny"]
            del positions[instrument]
        events.append(
            {
                **base,
                "fill_status": "filled",
                "blocking_reason": "",
                "fill_price_qfq": fill,
                "executed_shares": float(shares),
                "executed_notional_cny": float(notional),
                **costs,
                "shares_after": float(positions[instrument].shares)
                if instrument in positions
                else 0.0,
                "cash_after": float(cash),
            }
        )
        return True, float(costs["total_cost_cny"])

    prior: dict[str, Any] | None = None
    for trade_date in simulation_dates:
        pre_nav, pre_values = mark(trade_date)
        if prior is not None:
            gross_return = (
                pre_nav + float(prior["trade_cost_cny"])
            ) / float(prior["pretrade_nav"]) - 1.0
            net_return = pre_nav / float(prior["pretrade_nav"]) - 1.0
            daily.append(
                {
                    "seed": seed,
                    "topk": topk,
                    "decision_date": prior["decision_date"],
                    "trade_date": prior["trade_date"],
                    "next_trade_date": trade_date,
                    "gross_return": gross_return,
                    "net_return": net_return,
                    "pretrade_nav": prior["pretrade_nav"],
                    "posttrade_nav": prior["posttrade_nav"],
                    "next_pretrade_nav": pre_nav,
                    "trade_cost_cny": prior["trade_cost_cny"],
                    "turnover_notional_cny": prior["turnover_notional_cny"],
                    "one_way_turnover": prior["turnover_notional_cny"]
                    / (2.0 * prior["pretrade_nav"]),
                    "blocked_order_n": prior["blocked_order_n"],
                    "filled_order_n": prior["filled_order_n"],
                    "holding_n": prior["holding_n"],
                    "cash_weight": prior["cash_weight"],
                }
            )
        if trade_date == terminal:
            break

        decision = trade_to_decision[trade_date]
        pred = scores_by_date[decision].copy()
        pred.index = pred.index.astype(str)
        pred = pred[~pred.index.duplicated(keep="last")]
        pred = pred.sort_index().sort_values(ascending=False, kind="mergesort")
        current = list(positions)
        last = pred.reindex(current).sort_values(
            ascending=False, kind="mergesort", na_position="last"
        ).index
        outside = pred[~pred.index.isin(last)]
        new_candidate_n = max(0, n_drop + topk - len(last))
        today = list(outside.index[:new_candidate_n])
        combined = pred.reindex(pd.Index(last).union(pd.Index(today))).sort_values(
            ascending=False, kind="mergesort", na_position="last"
        )
        bottom = set(combined.index[-min(n_drop, len(combined)) :])
        sells = [instrument for instrument in last if instrument in bottom]
        buy_n = max(0, len(sells) + topk - len(last))
        buys = today[:buy_n]

        event_start = len(events)
        for instrument in sells:
            execute(
                trade_date,
                str(instrument),
                "sell",
                positions[str(instrument)].shares,
                "topk_dropout_exit",
            )
        launch_cash = cash
        budget = launch_cash / len(buys) if buys else 0.0
        for instrument in buys:
            key = (trade_date, str(instrument))
            fill = (
                float(market.loc[key]["qfq_open"])
                if key in market.index
                else math.nan
            )
            requested = budget / fill if np.isfinite(fill) and fill > 0 else 0.0
            execute(
                trade_date,
                str(instrument),
                "buy",
                requested,
                "topk_dropout_entry",
            )
        current_events = events[event_start:]
        trade_cost = float(sum(row["total_cost_cny"] for row in current_events))
        turnover_notional = float(
            sum(row["executed_notional_cny"] for row in current_events)
        )
        post_nav, values = mark(trade_date)
        for instrument, value in values.items():
            holdings.append(
                {
                    "seed": seed,
                    "topk": topk,
                    "decision_date": decision,
                    "trade_date": trade_date,
                    "instrument": instrument,
                    "shares": positions[instrument].shares,
                    "position_value_cny": value,
                    "position_weight": value / post_nav if post_nav > 0 else math.nan,
                }
            )
        prior = {
            "decision_date": decision,
            "trade_date": trade_date,
            "pretrade_nav": pre_nav,
            "posttrade_nav": post_nav,
            "trade_cost_cny": trade_cost,
            "turnover_notional_cny": turnover_notional,
            "blocked_order_n": sum(
                row["fill_status"] != "filled" for row in current_events
            ),
            "filled_order_n": sum(row["fill_status"] == "filled" for row in current_events),
            "holding_n": len(positions),
            "cash_weight": cash / post_nav if post_nav > 0 else math.nan,
        }
    return pd.DataFrame(daily), pd.DataFrame(events), pd.DataFrame(holdings)


def summarize_returns(
    frame: pd.DataFrame,
    *,
    lane: str,
    seed: int,
    topk: int,
    annualization: int,
) -> dict[str, Any]:
    gross = frame["gross_return"]
    net = frame["net_return"]
    return {
        "lane": lane,
        "seed": seed,
        "topk": topk,
        "day_n": int(len(frame)),
        "gross_arr": annualized_return(gross, annualization),
        "net_arr": annualized_return(net, annualization),
        "net_ir": information_ratio(net, annualization),
        "net_mdd": max_drawdown(net),
        "mean_one_way_turnover": float(frame["one_way_turnover"].mean()),
        "total_cost_return": float(frame.get("cost", pd.Series(dtype=float)).sum())
        if "cost" in frame
        else float(frame["trade_cost_cny"].sum() / frame.iloc[0]["pretrade_nav"]),
        "mean_cash_weight": float(frame.get("cash_weight", pd.Series([0.0])).mean()),
        "blocked_order_n": int(frame.get("blocked_order_n", pd.Series([0])).sum()),
    }


def add_benchmarks(
    topic_root: Path,
    config: Mapping[str, Any],
    daily: pd.DataFrame,
    score: pd.Series,
    market: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    benchmark_path = resolve_path(
        topic_root, config["execution_bridge"]["benchmark_panel"]
    )
    benchmark = pd.read_csv(benchmark_path)
    benchmark["trade_date"] = pd.to_datetime(benchmark["trade_date"])
    index_open = {
        instrument: group.set_index("trade_date")["open"].astype(float)
        for instrument, group in benchmark[
            benchmark["instrument"].isin(["SH000300", "SH000985"])
        ].groupby("instrument")
    }
    result = daily.copy()
    for instrument, name in [
        ("SH000300", "sh000300_return"),
        ("SH000985", "all_a_return"),
    ]:
        series = index_open[instrument]
        result[name] = [
            series.get(pd.Timestamp(end), math.nan)
            / series.get(pd.Timestamp(start), math.nan)
            - 1.0
            for start, end in zip(result["trade_date"], result["next_trade_date"])
        ]

    score_frame = score.rename("prediction").reset_index()
    score_frame["trade_date"] = score_frame["datetime"].map(
        result.drop_duplicates("decision_date").set_index("decision_date")["trade_date"]
    )
    score_frame["next_trade_date"] = score_frame["datetime"].map(
        result.drop_duplicates("decision_date").set_index("decision_date")[
            "next_trade_date"
        ]
    )
    universe_rows = []
    for decision, group in score_frame.groupby("datetime", sort=True):
        values = []
        for row in group.itertuples():
            first = (pd.Timestamp(row.trade_date), str(row.instrument))
            second = (pd.Timestamp(row.next_trade_date), str(row.instrument))
            if first in market.index and second in market.index:
                start_open = float(market.loc[first]["qfq_open"])
                end_open = float(market.loc[second]["qfq_open"])
                if start_open > 0 and np.isfinite(end_open):
                    values.append(end_open / start_open - 1.0)
        universe_rows.append(
            {
                "decision_date": pd.Timestamp(decision),
                "universe_equal_weight_return": float(np.mean(values))
                if values
                else math.nan,
                "universe_return_n": len(values),
            }
        )
    universe = pd.DataFrame(universe_rows)
    result = result.merge(universe, on="decision_date", how="left", validate="one_to_one")
    comparison_rows = []
    for name, column in [
        ("last_state_gru_executable_net", "net_return"),
        ("SH000300", "sh000300_return"),
        ("all_A_SH000985", "all_a_return"),
        ("PIT_universe_equal_weight", "universe_equal_weight_return"),
    ]:
        values = result[column].dropna()
        comparison_rows.append(
            {
                "comparator": name,
                "day_n": len(values),
                "arr": annualized_return(values),
                "ir": information_ratio(values),
                "mdd": max_drawdown(values),
            }
        )
    return result, pd.DataFrame(comparison_rows)


def future_left_tail_panel(
    market: pd.DataFrame,
    horizon: int,
) -> pd.Series:
    rows: list[pd.Series] = []
    flat = market.reset_index()
    for instrument, group in flat.groupby("instrument", sort=False):
        local = group.sort_values("trade_date")
        base = local["qfq_open"].to_numpy(float)
        low = local["qfq_low"].to_numpy(float)
        values = np.full(len(local), np.nan)
        for index in range(len(local)):
            future = low[index + 1 : index + 1 + horizon]
            if len(future) == horizon and base[index] > 0:
                values[index] = np.nanmin(future) / base[index] - 1.0
        rows.append(
            pd.Series(
                values,
                index=pd.MultiIndex.from_arrays(
                    [
                        local["trade_date"],
                        np.repeat(instrument, len(local)),
                    ],
                    names=["trade_date", "instrument"],
                ),
            )
        )
    return pd.concat(rows).sort_index()


def big_winner_readout(
    topic_root: Path,
    config: Mapping[str, Any],
    score: pd.Series,
    daily: pd.DataFrame,
    holdings: pd.DataFrame,
    market: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, bool]]:
    bridge = config["execution_bridge"]
    threshold_id = str(bridge["right_tail_threshold_id"])
    episodes = pd.read_parquet(
        resolve_path(topic_root, bridge["winner_episode_panel"])
    )
    episodes = episodes[episodes["threshold_id"].eq(threshold_id)].copy()
    episodes["cluster_start_date"] = pd.to_datetime(episodes["cluster_start_date"])
    episodes["cluster_end_date"] = pd.to_datetime(episodes["cluster_end_date"])
    start, end = daily["trade_date"].min(), daily["next_trade_date"].max()
    score_instruments = set(score.index.get_level_values("instrument").astype(str))
    episodes = episodes[
        episodes["instrument"].isin(score_instruments)
        & episodes["cluster_end_date"].ge(start)
        & episodes["cluster_start_date"].le(end)
    ].copy()

    taxonomy = pd.read_parquet(
        resolve_path(topic_root, bridge["winner_taxonomy_panel"]),
        columns=["threshold_id", "episode_cluster_id", "path_type"],
    )
    taxonomy = taxonomy[taxonomy["threshold_id"].eq(threshold_id)]

    def stable_mode(series: pd.Series) -> str:
        counts = series.dropna().astype(str).value_counts()
        if counts.empty:
            return "unknown"
        return str(sorted(counts[counts.eq(counts.max())].index)[0])

    morphology = (
        taxonomy.groupby("episode_cluster_id")["path_type"]
        .agg(stable_mode)
        .rename("path_type")
    )
    episodes = episodes.join(morphology, on="episode_cluster_id")
    intervals: dict[str, list[tuple[pd.Timestamp, pd.Timestamp, str]]] = {}
    for row in episodes.itertuples():
        intervals.setdefault(str(row.instrument), []).append(
            (
                pd.Timestamp(row.cluster_start_date),
                pd.Timestamp(row.cluster_end_date),
                str(row.episode_cluster_id),
            )
        )

    def cluster_hits(date: pd.Timestamp, instrument: str) -> list[str]:
        return [
            cluster
            for first, last, cluster in intervals.get(instrument, [])
            if first <= date <= last
        ]

    held = holdings[["trade_date", "instrument", "position_weight"]].copy()
    held["cluster_ids"] = [
        cluster_hits(pd.Timestamp(date), str(instrument))
        for date, instrument in zip(held["trade_date"], held["instrument"])
    ]
    held["right_tail_exposure"] = held["cluster_ids"].map(bool)
    captured = set(
        cluster
        for values in held["cluster_ids"]
        for cluster in values
    )

    decision_trade = daily.set_index("decision_date")["trade_date"]
    eligible = score.rename("prediction").reset_index()
    eligible["trade_date"] = eligible["datetime"].map(decision_trade)
    eligible = eligible.dropna(subset=["trade_date"])
    eligible["right_tail_exposure"] = [
        bool(cluster_hits(pd.Timestamp(date), str(instrument)))
        for date, instrument in zip(eligible["trade_date"], eligible["instrument"])
    ]

    horizon = int(bridge["severe_left_tail_horizon_sessions"])
    tail = future_left_tail_panel(market, horizon)
    held_index = pd.MultiIndex.from_frame(held[["trade_date", "instrument"]])
    eligible_index = pd.MultiIndex.from_frame(eligible[["trade_date", "instrument"]])
    held["future_min_return"] = tail.reindex(held_index).to_numpy()
    eligible["future_min_return"] = tail.reindex(eligible_index).to_numpy()
    threshold = float(bridge["severe_left_tail_threshold"])
    held_left = held["future_min_return"].le(threshold)
    eligible_left = eligible["future_min_return"].le(threshold)
    held_right_rate = float(held["right_tail_exposure"].mean())
    eligible_right_rate = float(eligible["right_tail_exposure"].mean())
    enrichment = (
        held_right_rate / eligible_right_rate if eligible_right_rate > 0 else math.nan
    )
    held_left_rate = float(held_left[held["future_min_return"].notna()].mean())
    eligible_left_rate = float(
        eligible_left[eligible["future_min_return"].notna()].mean()
    )
    episode_recall = len(captured) / len(episodes) if len(episodes) else math.nan
    utility = pd.DataFrame(
        [
            {
                "threshold_id": threshold_id,
                "eligible_episode_n": int(len(episodes)),
                "captured_episode_n": int(len(captured)),
                "winner_episode_recall": episode_recall,
                "holding_exposure_day_n": int(len(held)),
                "right_tail_exposure_day_n": int(held["right_tail_exposure"].sum()),
                "false_positive_exposure_day_n": int(
                    (~held["right_tail_exposure"]).sum()
                ),
                "right_tail_exposure_rate": held_right_rate,
                "eligible_universe_right_tail_rate": eligible_right_rate,
                "right_tail_exposure_enrichment": enrichment,
                "severe_left_tail_exposure_rate": held_left_rate,
                "eligible_universe_severe_left_tail_rate": eligible_left_rate,
                "severe_left_tail_excess": held_left_rate - eligible_left_rate,
                "left_tail_threshold": threshold,
                "left_tail_horizon_sessions": horizon,
            }
        ]
    )

    episodes["captured"] = episodes["episode_cluster_id"].isin(captured)
    morphology_rows = []
    for path_type, group in episodes.groupby("path_type", dropna=False, sort=True):
        morphology_rows.append(
            {
                "path_type": str(path_type),
                "eligible_episode_n": int(len(group)),
                "captured_episode_n": int(group["captured"].sum()),
                "episode_recall": float(group["captured"].mean()),
                "captured_episode_share": float(group["captured"].sum())
                / max(1, len(captured)),
            }
        )
    morphology_readout = pd.DataFrame(morphology_rows)
    material = morphology_readout[
        morphology_readout["eligible_episode_n"].ge(
            int(bridge["minimum_material_morphology_episodes"])
        )
    ]
    material_capture_share = float(material["captured_episode_n"].gt(0).mean())
    largest_share = float(
        morphology_readout["captured_episode_share"].max()
        if len(morphology_readout)
        else 1.0
    )
    gates = {
        "right_tail_enrichment_gate": bool(
            enrichment > float(bridge["right_tail_enrichment_gate"])
        ),
        "left_tail_burden_gate": bool(
            held_left_rate - eligible_left_rate
            <= float(bridge["left_tail_excess_tolerance"])
        ),
        "episode_capture_gate": bool(len(captured) > 0),
        "morphology_coverage_gate": bool(
            material_capture_share
            >= float(bridge["minimum_morphology_capture_share"])
        ),
        "morphology_concentration_gate": bool(
            largest_share
            <= float(bridge["maximum_single_morphology_capture_share"])
        ),
    }
    utility["material_morphology_n"] = len(material)
    utility["material_morphology_capture_share"] = material_capture_share
    utility["largest_captured_morphology_share"] = largest_share
    return utility, morphology_readout, gates


def write_report(
    output_dir: Path,
    primary_seed: int,
    paper_summary: pd.DataFrame,
    execution_summary: pd.DataFrame,
    benchmarks: pd.DataFrame,
    utility: pd.DataFrame,
    morphology: pd.DataFrame,
    gates: pd.DataFrame,
    decision: str,
) -> None:
    paper = paper_summary[
        (paper_summary["seed"] == primary_seed) & (paper_summary["topk"] == 50)
    ].iloc[0]
    executable = execution_summary[
        (execution_summary["seed"] == primary_seed)
        & (execution_summary["topk"] == 50)
    ].iloc[0]
    top30 = execution_summary[
        (execution_summary["seed"] == primary_seed)
        & (execution_summary["topk"] == 30)
    ].iloc[0]
    u = utility.iloc[0]
    benchmark_lines = "\n".join(
        f"| {row.comparator} | {row.arr:.2%} | {row.ir:.3f} | {row.mdd:.2%} |"
        for row in benchmarks.itertuples()
    )
    morphology_lines = "\n".join(
        f"| {row.path_type} | {row.eligible_episode_n} | "
        f"{row.captured_episode_n} | {row.episode_recall:.2%} |"
        for row in morphology.itertuples()
    )
    gate_lines = "\n".join(
        f"| {row.gate} | {'PASS' if row.passed else 'FAIL'} | {row.observed} |"
        for row in gates.itertuples()
    )
    report = f"""# EP23 23F PIT Execution and Big Winner Bridge

## 裁决

```text
frozen_model = last_state_gru
primary_seed = {primary_seed}
seed_selection = validation_paper_proxy_ic max, seed ascending tie-break
decision = {decision}
evidence = {EVIDENCE_CLASS}
deployment_authorized = false
```

主 seed 只由 23D2 validation IC 选择；23F 没有用 test ARR、执行收益或
Big Winner 结果挑 seed。完整五 seed 都通过同一执行器，用于检查结论是否依赖
单个随机种子。

## PAPER_PROXY 与 next-open 执行

| lane | gross ARR | net ARR | IR | MDD | one-way turnover |
|---|---:|---:|---:|---:|---:|
| PAPER_PROXY Top50/drop5 | {paper.gross_arr:.2%} | {paper.net_arr:.2%} | {paper.net_ir:.3f} | {paper.net_mdd:.2%} | {paper.mean_one_way_turnover:.4f} |
| EXECUTABLE_BRIDGE Top50/drop5 | {executable.gross_arr:.2%} | {executable.net_arr:.2%} | {executable.net_ir:.3f} | {executable.net_mdd:.2%} | {executable.mean_one_way_turnover:.4f} |
| EXECUTABLE_BRIDGE Top30/drop5 | {top30.gross_arr:.2%} | {top30.net_arr:.2%} | {top30.net_ir:.3f} | {top30.net_mdd:.2%} | {top30.mean_one_way_turnover:.4f} |

EXECUTABLE_BRIDGE 在 decision close 后的下一交易日开盘成交；使用 raw price
判断涨跌停、qfq price 连续计值，并逐单处理停牌/缺 bar、整手、佣金最低额、
卖出印花税、过户费、5bps 单边滑点、未成交现金和延迟退出。它不是把
`open-to-open` label 直接当作可成交收益。

## 同期基准

| comparator | ARR | IR | MDD |
|---|---:|---:|---:|
{benchmark_lines}

## Big Winner utility

- eligible up50 episode：{int(u.eligible_episode_n)}；
- captured episode：{int(u.captured_episode_n)}，recall `{u.winner_episode_recall:.2%}`；
- right-tail exposure days：{int(u.right_tail_exposure_day_n)}；
- false-positive exposure days：{int(u.false_positive_exposure_day_n)}；
- right-tail exposure enrichment：`{u.right_tail_exposure_enrichment:.3f}x`；
- severe-left-tail exposure：策略 `{u.severe_left_tail_exposure_rate:.2%}`，
  eligible universe `{u.eligible_universe_severe_left_tail_rate:.2%}`。

right-tail exposure 是实际持仓日落在 EP15 path-defined up50 episode interval
内；false-positive exposure 是其补集。二者是 ex-post utility attribution，
不能回灌为交易时标签。左尾以持仓开盘后 20 个交易日内最低 qfq low 相对当前
qfq open 不高于 -20% 定义。

## Morphology independence

| morphology | eligible episodes | captured | recall |
|---|---:|---:|---:|
{morphology_lines}

independence gate 要求：material morphology（至少 10 episodes）中至少 80%
有捕获，且任一 morphology 不得占全部 captured episodes 的 70% 以上。这只
排除“收益完全由单一路径形态驱动”的解释，不声称各形态收益同质。

## Gates

| gate | result | observed |
|---|---|---|
{gate_lines}

## 解释边界

- historical test 已反复观察，是 design-contaminated historical evidence；
- 正 ARR 本身不授权策略，必须同时通过 executable sign、seed、Big Winner
  utility 与 morphology gates；
- SH000985 使用项目冻结的全 A 指数日线；universe equal-weight 只对当日
  frozen score 可用股票计算；
- 本阶段不包含容量冲击、盘口排队、分钟级涨跌停打开概率或 live forward；
- `deployment_authorized=false`，即使达到 historical freeze candidate，
  也只能进入独立 true-forward freeze。
"""
    (output_dir / "23F_pit_execution_big_winner_bridge_report.md").write_text(
        report, encoding="utf-8"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args()
    config_path = Path(args.config).resolve()
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    topic_root = find_topic_root(config_path)
    output_dir = resolve_path(topic_root, config["outputs"]["execution_bridge"])
    output_dir.mkdir(parents=True, exist_ok=True)

    predictions, seed_metrics, primary_seed, prediction_root = load_predictions(
        topic_root, config
    )
    seed_selection = seed_metrics[
        seed_metrics["variant"].eq("last_state_gru")
    ][
        [
            "variant",
            "seed",
            "validation_paper_proxy_ic",
            "validation_paper_proxy_rank_ic",
            "historical_test_paper_proxy_ic",
            "historical_test_paper_proxy_net_arr",
        ]
    ].copy()
    seed_selection["selected_primary_seed"] = seed_selection["seed"].eq(primary_seed)
    seed_selection["selection_uses_historical_test"] = False
    seed_selection.to_csv(output_dir / "seed_selection_audit.csv", index=False)

    primary_prediction = predictions[primary_seed]
    paper_rows: list[dict[str, Any]] = []
    paper_daily_parts: list[pd.DataFrame] = []
    annualization = int(config["portfolio"]["annualization"])
    for seed, prediction in predictions.items():
        aligned_labels = load_label_panel(topic_root, config, prediction.index)
        paper_daily, _ = topk_dropout_proxy(
            prediction["prediction"],
            aligned_labels,
            label_column="paper_proxy",
            topk=int(config["execution_bridge"]["primary_topk"]),
            n_drop=int(config["execution_bridge"]["n_drop"]),
            buy_cost=float(config["portfolio"]["buy_cost"]),
            sell_cost=float(config["portfolio"]["sell_cost"]),
        )
        paper_daily["lane"] = "PAPER_PROXY"
        paper_daily["seed"] = seed
        paper_daily["topk"] = int(config["execution_bridge"]["primary_topk"])
        paper_daily_parts.append(paper_daily)
        paper_rows.append(
            summarize_returns(
                paper_daily,
                lane="PAPER_PROXY",
                seed=seed,
                topk=int(config["execution_bridge"]["primary_topk"]),
                annualization=annualization,
            )
        )
    paper_summary = pd.DataFrame(paper_rows)
    paper_summary.to_csv(output_dir / "paper_proxy_summary.csv", index=False)

    score_instruments = sorted(
        set(primary_prediction.index.get_level_values("instrument").astype(str))
    )
    bridge = config["execution_bridge"]
    calendar_path = resolve_path(topic_root, bridge["trading_calendar"])
    full_calendar = pd.DatetimeIndex(
        pd.to_datetime(pd.read_csv(calendar_path)["trade_date"]).sort_values().unique()
    )
    decision_start = pd.Timestamp(config["split"]["historical_test"][0])
    decision_end = pd.Timestamp(config["split"]["historical_test"][1])
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
    master["delist_date"] = pd.to_datetime(master["delist_date"], errors="coerce")
    master = master.drop_duplicates("instrument").set_index("instrument")
    rules = compile_rules(resolve_path(topic_root, bridge["market_rule_registry"]))
    st_status = st_status_builder(
        topic_root, config, score_instruments, master
    )

    execution_daily_parts: list[pd.DataFrame] = []
    event_parts: list[pd.DataFrame] = []
    holding_parts: list[pd.DataFrame] = []
    execution_rows: list[dict[str, Any]] = []
    primary_topk = int(bridge["primary_topk"])
    sensitivity_topk = int(bridge["sensitivity_topk"])
    for seed, prediction in predictions.items():
        topks = [primary_topk]
        if seed == primary_seed:
            topks.append(sensitivity_topk)
        for topk in topks:
            daily, events, holdings = simulate_executable(
                score=prediction["prediction"],
                topk=topk,
                n_drop=int(bridge["n_drop"]),
                config=config,
                calendar=calendar,
                market=market,
                master=master,
                rules=rules,
                st_status=st_status,
                seed=seed,
            )
            daily["lane"] = "EXECUTABLE_BRIDGE"
            execution_daily_parts.append(daily)
            event_parts.append(events)
            holding_parts.append(holdings)
            execution_rows.append(
                summarize_returns(
                    daily,
                    lane="EXECUTABLE_BRIDGE",
                    seed=seed,
                    topk=topk,
                    annualization=annualization,
                )
            )
    execution_daily = pd.concat(execution_daily_parts, ignore_index=True)
    events = pd.concat(event_parts, ignore_index=True)
    all_holdings = pd.concat(holding_parts, ignore_index=True)
    execution_summary = pd.DataFrame(execution_rows)

    primary_daily = execution_daily[
        execution_daily["seed"].eq(primary_seed)
        & execution_daily["topk"].eq(primary_topk)
    ].copy()
    primary_daily, benchmarks = add_benchmarks(
        topic_root,
        config,
        primary_daily,
        primary_prediction["prediction"],
        market,
    )
    execution_daily = execution_daily.merge(
        primary_daily[
            [
                "seed",
                "topk",
                "decision_date",
                "sh000300_return",
                "all_a_return",
                "universe_equal_weight_return",
                "universe_return_n",
            ]
        ],
        on=["seed", "topk", "decision_date"],
        how="left",
    )
    execution_summary.to_csv(output_dir / "executable_summary.csv", index=False)
    benchmarks.to_csv(output_dir / "benchmark_comparison.csv", index=False)
    pd.concat(paper_daily_parts, ignore_index=True).to_csv(
        output_dir / "paper_proxy_daily.csv", index=False
    )
    execution_daily.to_csv(output_dir / "executable_daily.csv", index=False)
    events.to_parquet(output_dir / "execution_event_ledger.parquet", index=False)
    all_holdings.to_parquet(output_dir / "daily_holdings.parquet", index=False)

    primary_holdings = all_holdings[
        all_holdings["seed"].eq(primary_seed)
        & all_holdings["topk"].eq(primary_topk)
    ].copy()
    utility, morphology, winner_gates = big_winner_readout(
        topic_root,
        config,
        primary_prediction["prediction"],
        primary_daily,
        primary_holdings,
        market,
    )
    utility.to_csv(output_dir / "big_winner_utility_readout.csv", index=False)
    morphology.to_csv(output_dir / "morphology_independence_readout.csv", index=False)

    primary_paper = paper_summary[
        paper_summary["seed"].eq(primary_seed)
        & paper_summary["topk"].eq(primary_topk)
    ].iloc[0]
    primary_execution = execution_summary[
        execution_summary["seed"].eq(primary_seed)
        & execution_summary["topk"].eq(primary_topk)
    ].iloc[0]
    top50 = execution_summary[execution_summary["topk"].eq(primary_topk)]
    primary_events = events[
        events["seed"].eq(primary_seed) & events["topk"].eq(primary_topk)
    ]
    strategy_arr = float(
        benchmarks.loc[
            benchmarks["comparator"].eq("last_state_gru_executable_net"), "arr"
        ].iloc[0]
    )
    universe_arr = float(
        benchmarks.loc[
            benchmarks["comparator"].eq("PIT_universe_equal_weight"), "arr"
        ].iloc[0]
    )
    gates = {
        "paper_proxy_positive_gate": bool(primary_paper["net_arr"] > 0),
        "executable_no_sign_reversal_gate": bool(
            primary_execution["net_arr"] > 0
            and np.sign(primary_execution["net_arr"]) == np.sign(primary_paper["net_arr"])
        ),
        "five_seed_executable_direction_gate": bool(
            int(top50["net_arr"].gt(0).sum()) >= 3
        ),
        "universe_equal_weight_increment_gate": bool(strategy_arr > universe_arr),
        "blocked_fill_materialization_gate": bool(
            len(primary_events) > 0
            and {
                "limit_up_blocked",
                "limit_down_blocked",
                "suspended_missing_daily_bar",
            }.issubset(set(primary_events["blocking_reason"]))
        ),
        **winner_gates,
    }
    observed = {
        "paper_proxy_positive_gate": f"net_arr={primary_paper['net_arr']:.6f}",
        "executable_no_sign_reversal_gate": (
            f"paper_net_arr={primary_paper['net_arr']:.6f};"
            f"executable_net_arr={primary_execution['net_arr']:.6f}"
        ),
        "five_seed_executable_direction_gate": (
            f"positive_seeds={int(top50['net_arr'].gt(0).sum())}/5"
        ),
        "universe_equal_weight_increment_gate": (
            f"strategy_net_arr={strategy_arr:.6f};universe_arr={universe_arr:.6f}"
        ),
        "blocked_fill_materialization_gate": (
            f"primary_blocked_orders="
            f"{int(primary_events['fill_status'].ne('filled').sum())};"
            f"reasons={';'.join(sorted(set(primary_events.loc[primary_events['fill_status'].ne('filled'), 'blocking_reason'])))}"
        ),
        "right_tail_enrichment_gate": (
            f"enrichment={utility.iloc[0]['right_tail_exposure_enrichment']:.6f}"
        ),
        "left_tail_burden_gate": (
            f"excess={utility.iloc[0]['severe_left_tail_excess']:.6f}"
        ),
        "episode_capture_gate": (
            f"captured={int(utility.iloc[0]['captured_episode_n'])}/"
            f"{int(utility.iloc[0]['eligible_episode_n'])}"
        ),
        "morphology_coverage_gate": (
            f"material_capture_share="
            f"{utility.iloc[0]['material_morphology_capture_share']:.6f}"
        ),
        "morphology_concentration_gate": (
            f"largest_captured_share="
            f"{utility.iloc[0]['largest_captured_morphology_share']:.6f}"
        ),
    }
    gate_frame = pd.DataFrame(
        [
            {"gate": name, "passed": passed, "observed": observed[name]}
            for name, passed in gates.items()
        ]
    )
    gate_frame.to_csv(output_dir / "gate_audit.csv", index=False)
    if all(gates.values()):
        decision = "historical_forward_freeze_candidate"
    elif (
        gates["paper_proxy_positive_gate"]
        and not gates["executable_no_sign_reversal_gate"]
    ):
        decision = "paper_proxy_only"
    else:
        decision = "model_branch_only_supported"

    write_report(
        output_dir,
        primary_seed,
        paper_summary,
        execution_summary,
        benchmarks,
        utility,
        morphology,
        gate_frame,
        decision,
    )
    input_paths = {
        "config": config_path,
        "formal_seed_metrics": resolve_path(
            topic_root, config["outputs"]["model_attribution_formal"]
        )
        / "seed_metrics.csv",
        "primary_prediction": prediction_root
        / f"last_state_gru_{primary_seed}.predictions.parquet",
        "label_panel": resolve_path(topic_root, config["outputs"]["local_cache"])
        / "alpha20_dual_label_panel_model_attribution.parquet",
        "market_rules": resolve_path(topic_root, bridge["market_rule_registry"]),
        "security_master": resolve_path(topic_root, bridge["security_master"]),
        "winner_episode_panel": resolve_path(topic_root, bridge["winner_episode_panel"]),
        "winner_taxonomy_panel": resolve_path(
            topic_root, bridge["winner_taxonomy_panel"]
        ),
    }
    output_hashes = {
        path.name: sha256_file(path)
        for path in sorted(output_dir.iterdir())
        if path.is_file()
        and path.name not in {"manifest.json", "output_hashes.json"}
    }
    (output_dir / "output_hashes.json").write_text(
        json.dumps(output_hashes, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    manifest = {
        "run_id": RUN_ID,
        "generated_at_utc": utc_now(),
        "decision": decision,
        "evidence_class": EVIDENCE_CLASS,
        "primary_seed": primary_seed,
        "seed_selection_uses_historical_test": False,
        "formal_seeds": list(map(int, config["model_attribution"]["formal_seeds"])),
        "input_hashes": {name: sha256_file(path) for name, path in input_paths.items()},
        "output_hashes_sha256": sha256_file(output_dir / "output_hashes.json"),
        "gates": gates,
        "deployment_authorized": False,
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": "completed",
                "decision": decision,
                "primary_seed": primary_seed,
                "output_dir": str(output_dir),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
