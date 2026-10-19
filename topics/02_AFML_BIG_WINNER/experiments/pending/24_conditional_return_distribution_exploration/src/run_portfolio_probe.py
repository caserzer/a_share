"""R06: next-open monthly allocation proxy with cash and blocked-order accounting.

Uses adjusted units, not live executable broker lots. Cost and participation are
explicit scenario assumptions. No next-day/next-month outcomes select forecasts.
"""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from run_price_pilot import OUT

TOPIC = OUT.parents[3]
STYLES = ['all_equal', 'selected_equal', 'selected_inverse_vol', 'distribution_full', 'distribution_dynamic']


def capped_weights(raw, cap=.10):
    raw = np.maximum(np.asarray(raw, dtype=float), 0)
    if raw.sum() == 0:
        raw = np.ones_like(raw)
    target = min(1., len(raw)*cap)
    weights = np.zeros_like(raw)
    free = np.ones(len(raw), dtype=bool)
    for _ in range(len(raw)+1):
        remaining = target - weights.sum()
        if remaining < 1e-12 or not free.any():
            break
        denominator = raw[free].sum()
        proposal = raw[free] / denominator * remaining if denominator > 0 else np.full(free.sum(), remaining/free.sum())
        indices = np.flatnonzero(free)
        too_large = proposal > cap + 1e-12
        if not too_large.any():
            weights[indices] = proposal
            break
        weights[indices[too_large]] = cap
        free[indices[too_large]] = False
    return weights


def targets(predictions, instruments):
    mapping = {x: i for i, x in enumerate(instruments)}
    schedules, selections = {}, []
    for model in ['peers_risk_size', 'peers_valuation']:
        p = predictions[(predictions.horizon == 252) & (predictions.model == model)]
        for style in STYLES:
            schedule = {}
            for date, g in p.groupby('date'):
                g = g.copy()
                g['odds_score'] = g.q50 / np.maximum(-g.q05, .10)
                chosen = g.sort_values(['odds_score', 'instrument'], ascending=[False, True]).head(20)
                vector = np.zeros(len(instruments))
                if style == 'all_equal':
                    vector[[mapping[x] for x in g.instrument]] = 1/len(g)
                else:
                    if style == 'selected_equal':
                        raw = np.ones(len(chosen))
                    elif style == 'selected_inverse_vol':
                        raw = 1 / chosen.vol63.clip(lower=.05).to_numpy()
                    else:
                        raw = np.maximum(chosen.p_up.to_numpy()-.5, 0) / np.maximum(-chosen.q05.to_numpy(), .10)
                    gross = np.clip((chosen.p_up.mean()-.5)/.2, 0, 1) if style == 'distribution_dynamic' else 1.
                    weights = capped_weights(raw) * gross
                    vector[[mapping[x] for x in chosen.instrument]] = weights
                    if style == 'selected_equal':
                        selections.extend({'model': model, 'date': str(date.date()), 'instrument': r.instrument,
                                           'odds_score': r.odds_score, 'p_up': r.p_up} for r in chosen.itertuples())
                schedule[date] = vector
            schedules[(model, style)] = schedule
    return schedules, pd.DataFrame(selections)


def load_market(instruments):
    data = TOPIC / 'data'
    calendar = pd.DatetimeIndex(pd.to_datetime(pd.read_csv(data / 'qlib/cn_data_pit_largecap/calendars/day.txt', header=None)[0]))
    columns = {k: [] for k in ['open', 'close', 'raw_open', 'reference', 'prior_volume']}
    for instrument in instruments:
        q = pd.read_csv(data / f'raw/akshare/day/qfq/{instrument}.csv', parse_dates=['date']).set_index('date').reindex(calendar)
        raw = pd.read_csv(data / f'raw/akshare/day/raw/{instrument}.csv', parse_dates=['date']).set_index('date').reindex(calendar)
        columns['open'].append(q.open.to_numpy())
        columns['close'].append(q.close.to_numpy())
        columns['raw_open'].append(raw.open.to_numpy())
        # Previous adjusted close converted into today's raw-price scale; no future high/low or volume.
        reference = q.close.ffill().shift(1) * raw.open / q.open
        columns['reference'].append(reference.to_numpy())
        columns['prior_volume'].append(raw.volume.rolling(20, min_periods=5).mean().shift(1).to_numpy())
    market = {k: np.asarray(v, dtype=float).T for k, v in columns.items()}
    market['mark'] = pd.DataFrame(market['close'], index=calendar).ffill().to_numpy()
    return calendar, market


def simulate(calendar, market, schedule, fee, initial_cash=1_000_000.):
    events = {}
    for decision, weights in schedule.items():
        pos = calendar.searchsorted(decision, side='right')
        if pos < len(calendar):
            events[pos] = weights
    first = min(events)
    units = np.zeros(market['open'].shape[1])
    cash = initial_cash
    daily, orders = [], []
    cumulative_cost = 0.
    for i in range(first, len(calendar)):
        op = market['open'][i]
        mark = market['mark'][i]
        # At the open only yesterday's close is known if today's opening quote is missing.
        trade_price = np.where(np.isfinite(op) & (op > 0), op, market['mark'][i-1])
        held = units > 1e-12
        if np.any(held & ~np.isfinite(trade_price)):
            raise ValueError('Held asset lacks any known mark')
        values = np.zeros_like(units)
        values[held] = units[held] * trade_price[held]
        nav_open = cash + values.sum()
        turnover = cost = 0.
        blocked_buy = blocked_sell = 0
        if i in events:
            target = events[i]
            desired = target * nav_open
            delta = desired - values
            valid = np.isfinite(op) & (op > 0) & np.isfinite(market['raw_open'][i])
            gap = market['raw_open'][i] / market['reference'][i] - 1
            # Conservative 4.8% opening-gap restriction for all boards, not exact statutory limits.
            can_buy = valid & np.isfinite(gap) & (gap < .048)
            can_sell = valid & np.isfinite(gap) & (gap > -.048)
            liquidity_cap = market['prior_volume'][i] * market['raw_open'][i] * .01
            liquidity_cap = np.where(np.isfinite(liquidity_cap) & (liquidity_cap > 0), liquidity_cap, 0)
            sell_request = np.maximum(-delta, 0)
            buy_request = np.maximum(delta, 0)
            blocked_sell = int(((sell_request > 1e-6) & ~can_sell).sum())
            blocked_buy = int(((buy_request > 1e-6) & ~can_buy).sum())
            sells = np.minimum(sell_request, liquidity_cap) * can_sell
            sell_indices = sells > 0
            units[sell_indices] -= sells[sell_indices] / op[sell_indices]
            cash += sells.sum() * (1-fee)
            buys = np.minimum(buy_request, liquidity_cap) * can_buy
            if buys.sum() * (1+fee) > cash:
                buys *= cash / (buys.sum() * (1+fee))
            buy_indices = buys > 0
            units[buy_indices] += buys[buy_indices] / op[buy_indices]
            cash -= buys.sum() * (1+fee)
            cost = (sells.sum() + buys.sum()) * fee
            turnover = (sells.sum() + buys.sum()) / nav_open
            cumulative_cost += cost
            assert cash >= -1e-7 and units.min() >= -1e-7
            units = np.maximum(units, 0)
            cash = max(cash, 0)
            after_values = np.zeros_like(units)
            held_after = units > 1e-12
            after_values[held_after] = units[held_after] * trade_price[held_after]
            assert np.isclose(cash + after_values.sum(), nav_open-cost, rtol=1e-9, atol=1e-6)
            orders.append({'date': str(calendar[i].date()), 'nav_before': nav_open, 'target_gross': target.sum(),
                'actual_gross_after': after_values.sum() / (nav_open-cost), 'turnover': turnover,
                'cost': cost, 'blocked_buys': blocked_buy, 'blocked_sells': blocked_sell,
                'cash_after': cash, 'max_weight_after': after_values.max() / (nav_open-cost)})
        held = units > 1e-12
        marked_values = units[held] * mark[held]
        nav_close = cash + marked_values.sum()
        stale = held & ~np.isfinite(market['close'][i])
        stale_value = float(np.dot(units[stale], mark[stale])) if stale.any() else 0.
        daily.append({'date': calendar[i], 'nav': nav_close, 'cash': cash, 'gross': marked_values.sum()/nav_close,
                      'turnover': turnover, 'cost': cost, 'stale_positions': int(stale.sum()),
                      'stale_value': stale_value, 'holdings': int(held.sum())})
    daily = pd.DataFrame(daily)
    returns = daily.nav.pct_change()
    returns.iloc[0] = daily.nav.iloc[0]/initial_cash-1
    wealth = np.r_[initial_cash, daily.nav.to_numpy()]
    drawdown = wealth / np.maximum.accumulate(wealth) - 1
    years = len(daily) / 252
    summary = {'total_return': daily.nav.iloc[-1]/initial_cash-1,
        'annualized_return': (daily.nav.iloc[-1]/initial_cash)**(1/years)-1,
        'annualized_volatility': returns.std()*np.sqrt(252), 'max_drawdown': drawdown.min(),
        'average_gross': daily.gross.mean(), 'one_way_turnover_per_year': daily.turnover.sum()/years,
        'cost_fraction_initial': cumulative_cost/initial_cash, 'stale_position_days': int(daily.stale_positions.sum()),
        'terminal_stale_value': daily.stale_value.iloc[-1], 'days': len(daily),
        'start': str(daily.date.min().date()), 'end': str(daily.date.max().date()),
        'blocked_buy_orders': sum(x['blocked_buys'] for x in orders),
        'blocked_sell_orders': sum(x['blocked_sells'] for x in orders)}
    return daily, pd.DataFrame(orders), summary


def run():
    dest = OUT / 'r06_portfolio_probe'
    dest.mkdir(exist_ok=True)
    predictions = pd.read_parquet(OUT / 'r05_holdout/predictions.parquet')
    instruments = sorted(predictions.instrument.unique())
    schedules, selections = targets(predictions, instruments)
    selections.to_csv(dest / 'selected_candidates.csv', index=False)
    calendar, market = load_market(instruments)
    summaries, histories, orders = [], [], []
    for fee in [.001, .003]:
        for (model, style), schedule in schedules.items():
            daily, fills, summary = simulate(calendar, market, schedule, fee)
            for obj in [summary, daily, fills]:
                obj['model'], obj['style'], obj['fee'] = model, style, fee
            summaries.append(summary)
            histories.append(daily)
            orders.append(fills)
            print(model, style, fee, round(summary['total_return'], 4), flush=True)
    pd.DataFrame(summaries).to_csv(dest / 'summary.csv', index=False)
    pd.concat(histories, ignore_index=True).to_parquet(dest / 'daily_nav.parquet', index=False)
    pd.concat(orders, ignore_index=True).to_csv(dest / 'rebalance_audit.csv', index=False)
    (dest / 'execution_assumptions.json').write_text(json.dumps({
        'initial_account': 1_000_000, 'cash_return': 0, 'units': 'synthetic adjusted-price units; no broker lot-rounding claim',
        'decision': 'month-end known forecasts; execute next market session open',
        'restriction': 'buy blocked above +4.8% opening gap, sell below -4.8%; conservative proxy, not exact daily price limits',
        'participation': '1% of trailing 20-session mean raw volume, known prior to execution day',
        'marking': 'last known adjusted close on missing-quote days; terminal stale exposure explicitly reported',
        'corporate_actions': 'inherited qfq price proxy; not independently reconstructed total return',
        'endpoint': 'mark-to-market at 2026-05-29; no forced terminal liquidation',
        'caveat': 'exploratory allocation simulation, not verified executable broker orders or portfolio joint-tail optimization',
    }, indent=2) + '\n')


if __name__ == '__main__':
    run()
