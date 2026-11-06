"""Actual stage endpoints, frozen origin rankings, and same-period benchmark gains."""
import numpy as np
import pandas as pd
from context import POLICIES, detail, csv, previous


def stage_scores(phases, panel, joined, marks, benchmarks):
    grouped = {k: g for k, g in joined.groupby(['era', 'level', 'industry_code', 'month'], sort=False)}
    mark_lookup = marks.set_index(['security_id', 'month'])
    quote = panel.set_index(['security_id', 'month'])
    dates = panel.groupby('month').agg(date=('date', 'first'), entry_date=('entry_date', 'first'))
    result, stock_rows, path_rows = [], [], []
    for i, s in enumerate(phases.itertuples()):
        start, end = pd.Period(s.start_month), pd.Period(s.end_month)
        g = grouped.get((s.era, s.level, s.industry_code, start))
        industry_available = g is not None and len(g) >= 3
        entry_date = dates.loc[start, 'entry_date'] if start in dates.index else pd.NaT
        path_months = pd.period_range(start + 1, end, freq='M')
        for policy, age_limit in POLICIES:
            top = None
            rank_complete = False
            missing = unresolved = None
            if industry_available:
                g = g.copy()
                idx = pd.MultiIndex.from_arrays([g.security_id, [start] * len(g)])
                origin_marks = mark_lookup.reindex(idx)
                g['rank_cap'] = origin_marks[policy].to_numpy(float)
                g['mark_age_days'] = origin_marks.mark_age_days.to_numpy(float)
                g['used_stale_mark'] = g.cap.isna() & g.rank_cap.notna()
                missing = int(g.rank_cap.isna().sum())
                unresolved = int(g.unresolved.max())
                rank_complete = missing == 0 and unresolved == 0
                if rank_complete:
                    top = g.sort_values(['rank_cap', 'security_id'], ascending=[False, True]).head(3)
            returns = np.full((3, len(path_months)), np.nan)
            if top is not None:
                for j, r in enumerate(top.itertuples()):
                    origin = quote.loc[(r.security_id, start)]
                    target = quote.reindex(pd.MultiIndex.from_arrays([[r.security_id] * len(path_months), path_months]))
                    values = target.qfq_close.to_numpy(float)
                    same = target.close_chain.eq(origin.entry_chain).to_numpy()
                    if pd.notna(origin.entry_open) and origin.entry_open > 0:
                        returns[j] = np.where(same, values/origin.entry_open-1, np.nan)
            terminal = returns[:, -1] if len(path_months) else np.full(3, np.nan)
            stocks_known = bool(np.isfinite(terminal).all())
            paths_known = bool(np.isfinite(returns).all())
            for benchmark, index in benchmarks.items():
                b0 = float(index.loc[pd.Timestamp(s.start_date), 'close'])
                b1 = float(index.loc[pd.Timestamp(s.end_date), 'close'])
                industry_benchmark = b1/b0-1
                # This benchmark starts at the same assumed market opening as the stocks.
                bpath = (index.close.reindex(dates.date.reindex(path_months)).to_numpy(float) /
                         float(index.loc[entry_date, 'open']) - 1) if pd.notna(entry_date) else np.full(len(path_months), np.nan)
                bh = float(bpath[-1]) if len(bpath) and np.isfinite(bpath[-1]) else np.nan
                complete = stocks_known and np.isfinite(bh)
                path_complete = paths_known and np.isfinite(bpath).all()
                joint = (returns > bpath[None, :]).all(axis=0) if path_complete else None
                prefix = 0
                if path_complete:
                    for value in joint:
                        if not value:
                            break
                        prefix += 1
                candidate = bool(s.industry_return > 0 and s.industry_return > industry_benchmark)
                row = dict(phase_id=s.phase_id, era=s.era, level=s.level, industry_code=s.industry_code,
                    industry_name=s.industry_name, threshold=s.drawdown_threshold, policy=policy, benchmark=benchmark,
                    start_month=s.start_month, end_month=s.end_month, start_date=s.start_date, end_date=s.end_date,
                    duration_months=s.duration_months, length_class=s.length_class, phase_status=s.status,
                    left_censored=s.left_censored, right_censored=s.right_censored, end_is_partial=s.end_is_partial,
                    industry_return=s.industry_return, industry_benchmark_return=industry_benchmark,
                    industry_excess=s.industry_return-industry_benchmark, industry_candidate=candidate,
                    primary_stage=bool(s.status == 'CONFIRMED' and not s.left_censored and s.length_class == 'IN_RANGE_6_18' and candidate),
                    origin_members=len(g) if g is not None else 0,
                    missing_valuation_members=missing, unresolved_members=unresolved,
                    rank_complete=rank_complete, rank_quality='EXACT_ARCHIVED_MARKS' if policy == 'EXACT' else 'LAST_OBSERVED_MARK_DIAGNOSTIC',
                    top3=';'.join(top.instrument) if top is not None else None,
                    current_names=';'.join(top['name']) if top is not None else None,
                    selected_stale_marks=int(top.used_stale_mark.sum()) if top is not None else None,
                    any_member_stale_marks=int(g.used_stale_mark.sum()) if industry_available else None,
                    entry_date=entry_date, holding_benchmark_return=bh,
                    known_terminal_stocks=int(np.isfinite(terminal).sum()), complete=bool(complete), path_complete=bool(path_complete),
                    portfolio_return=float(terminal.mean()) if stocks_known else None,
                    portfolio_excess=float(terminal.mean()-bh) if complete else None,
                    worst_stock_excess=float(terminal.min()-bh) if complete else None,
                    all_positive=bool((terminal > 0).all()) if stocks_known else None,
                    all_beat=bool((terminal > bh).all()) if complete else None,
                    all_positive_and_beat=bool((terminal > 0).all() and (terminal > bh).all()) if complete else None,
                    joint_excess_longest=previous.v1.longest_true(joint) if path_complete else None,
                    joint_excess_from_first=prefix if path_complete else None,
                    joint_excess_months=int(joint.sum()) if path_complete else None,
                    all_months_joint_excess=bool(joint.all()) if path_complete else None,
                    status='KNOWN_INFERRED' if complete else 'UNKNOWN_RANK' if not rank_complete else 'UNKNOWN_TRADE_ENDPOINT',
                    selection_uses_future_turns=True)
                for j in range(3):
                    row[f'stock{j+1}_return'] = float(terminal[j]) if np.isfinite(terminal[j]) else None
                    row[f'stock{j+1}_excess'] = float(terminal[j]-bh) if np.isfinite(terminal[j]) and np.isfinite(bh) else None
                result.append(row)
                if top is not None:
                    for j, r in enumerate(top.itertuples()):
                        stock_rows.append(dict(phase_id=s.phase_id, threshold=s.drawdown_threshold, policy=policy,
                            benchmark=benchmark, era=s.era, level=s.level, industry_name=s.industry_name,
                            start_month=s.start_month, end_month=s.end_month, duration_months=s.duration_months,
                            phase_status=s.status, length_class=s.length_class, primary_stage=row['primary_stage'],
                            rank=j+1, security_id=r.security_id, instrument=r.instrument, current_name=r.name,
                            origin_rank_cap=r.rank_cap, origin_exact_cap=r.cap, mark_age_days=r.mark_age_days,
                            stale_mark_used=r.used_stale_mark, entry_date=entry_date,
                            return_value=row[f'stock{j+1}_return'], benchmark_return=bh,
                            excess=row[f'stock{j+1}_excess'], trade_price_imputed=False))
                    if row['primary_stage'] or s.industry_code in ['801081.SI', '801102.SI', '851024.SI', '850818.SI']:
                        for j, r in enumerate(top.itertuples()):
                            for h, month in enumerate(path_months):
                                path_rows.append(dict(phase_id=s.phase_id, threshold=s.drawdown_threshold,
                                    policy=policy, benchmark=benchmark, instrument=r.instrument, rank=j+1,
                                    holding_month=h+1, month=str(month), date=dates.loc[month, 'date'],
                                    return_value=returns[j, h], benchmark_return=bpath[h], excess=returns[j, h]-bpath[h]))
        if (i+1) % 500 == 0:
            print('V4 scored natural stages', i+1, '/', len(phases), flush=True)
    scores, stocks, paths = pd.DataFrame(result), pd.DataFrame(stock_rows), pd.DataFrame(path_rows)
    for threshold in [.1, .15, .2]:
        tag = str(int(threshold*100))
        detail('stage_scores_T'+tag, scores[scores.threshold.eq(threshold)])
        detail('stock_scores_T'+tag, stocks[stocks.threshold.eq(threshold)])
        detail('monthly_stock_paths_T'+tag, paths[paths.threshold.eq(threshold)])
    return scores, stocks, paths
