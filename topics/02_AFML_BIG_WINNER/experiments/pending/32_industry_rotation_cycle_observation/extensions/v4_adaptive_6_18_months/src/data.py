"""Read-only full PIT-calendar inputs; valuation marks never become trade prices."""
import json
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from context import EP, V2, V3, OUT, CACHE, previous, sha, js, csv, detail, BENCHMARKS


def prepare():
    CACHE.mkdir(parents=True, exist_ok=True)
    source = json.loads((V2 / 'outputs/audits/inputs.json').read_text())
    assert sha(previous.CACHE / 'panel.parquet') == source['panel_sha256']
    prior_review = json.loads((V3 / 'outputs/audits/input_identity.json').read_text())
    assert sha(previous.CACHE / 'assignments.parquet') == prior_review['assignment_sha256']
    panel = pd.read_parquet(previous.CACHE / 'panel.parquet')
    joined = pd.read_parquet(previous.CACHE / 'assignments.parquet')
    release = previous.v1.Release('pit_v5')
    days = pd.DatetimeIndex(release.read('inputs/inputs/baseline/normalized/calendar.parquet').date).sort_values()
    tail_date = days.max()
    tail_month = tail_date.to_period('M')
    dates = pd.DataFrame({'month': sorted(panel.month.unique())})
    dates['date'] = dates.month.map(panel.groupby('month').date.first())
    all_dates = pd.DatetimeIndex(list(dates.date) + [tail_date])
    groups = {sid: g for sid, g in panel.groupby('security_id', sort=False)}
    tails, marks, problems = [], [], []
    columns = ['date', 'close', 'qfq_close', 'close_conflict', 'volume', 'factor_chain_id']
    for i, (sid, p) in enumerate(groups.items()):
        relative = f'normalized/prices_qfq/{sid}.parquet'
        present = set(pq.read_schema(release.root / relative).names)
        bars = release.read(relative, columns=[x for x in columns if x in present]).sort_values('date')
        bars['close'] = pd.to_numeric(bars.close, errors='raise').astype(float)
        bars['qfq_close'] = pd.to_numeric(bars.qfq_close, errors='raise').astype(float)
        valid = bars.close.gt(0) & bars.close_conflict.eq(False) & bars.volume.gt(0)
        known = bars.loc[valid, ['date', 'close']].rename(columns={'date': 'last_mark_date', 'close': 'last_mark_close'})
        left = pd.DataFrame({'date': all_dates})
        m = pd.merge_asof(left, known, left_on='date', right_on='last_mark_date', direction='backward')
        m['security_id'] = sid
        m['month'] = list(sorted(panel.month.unique())) + [tail_month]
        m['mark_age_days'] = (m.date - m.last_mark_date).dt.days
        marks.append(m)
        row = p.iloc[-1].copy()
        b = bars[bars.date.eq(tail_date)]
        close = chain = raw = np.nan
        if len(b) == 1 and b.close_conflict.iloc[0] == False:
            raw = b.close.iloc[0] if b.close.iloc[0] > 0 else np.nan
            close = b.qfq_close.iloc[0] if b.qfq_close.iloc[0] > 0 else np.nan
            chain = b.factor_chain_id.iloc[0]
        row['month'], row['date'], row['entry_date'] = tail_month, tail_date, pd.NaT
        row['raw_close'], row['qfq_close'], row['close_chain'] = raw, close, chain
        for field in ['entry_open', 'entry_chain', 'total_shares', 'share_effective_date', 'cap', 'next_return']:
            row[field] = pd.NaT if field == 'share_effective_date' else np.nan
        row['listed'] = False  # Tail is an endpoint only, never a new origin/universe.
        tails.append(row)
        if (i + 1) % 1000 == 0:
            print('V4 verified daily quote/mark partitions', i + 1, '/', len(groups), flush=True)
    tail = pd.DataFrame(tails)
    panel = pd.concat([panel, tail], ignore_index=True)
    last_full = tail_month - 1
    a = panel[panel.month.eq(last_full)].set_index('security_id')
    t = tail.set_index('security_id').reindex(a.index)
    ret = (t.qfq_close / a.qfq_close - 1).where(t.close_chain.eq(a.close_chain))
    panel.loc[panel.month.eq(last_full), 'next_return'] = panel.loc[panel.month.eq(last_full), 'security_id'].map(ret).values
    joined.loc[joined.month.eq(last_full), 'next_return'] = joined.loc[joined.month.eq(last_full), 'security_id'].map(ret).values
    marks = pd.concat(marks, ignore_index=True)
    marks = marks.merge(panel[['security_id', 'month', 'cap', 'total_shares', 'raw_close', 'share_effective_date']],
                        on=['security_id', 'month'], how='left', validate='one_to_one')
    marks['last_mark_cap'] = marks.last_mark_close * marks.total_shares
    for label, maxage in [('EXACT', 0), ('MARK_7D', 7), ('MARK_31D', 31)]:
        marks[label] = marks.cap
        if maxage:
            ok = marks.cap.isna() & marks.mark_age_days.le(maxage) & marks.mark_age_days.ge(0) & marks.total_shares.gt(0)
            marks.loc[ok, label] = marks.loc[ok, 'last_mark_cap']
    panel.to_parquet(CACHE / 'panel_with_tail.parquet', index=False)
    marks.to_parquet(CACHE / 'valuation_marks.parquet', index=False)
    joined.to_parquet(CACHE / 'assignments_with_tail_return.parquet', index=False)
    price_sources = dict(V2_input_identity=source, daily_read_files=release.reads,
        price_release=str(release.root), start_session=str(days.min().date()), end_session=str(tail_date.date()),
        complete_month_end=str(a.date.iloc[0].date()), tail_is_partial=True,
        panel_sha256=sha(CACHE / 'panel_with_tail.parquet'), marks_sha256=sha(CACHE / 'valuation_marks.parquet'),
        assignments_sha256=sha(CACHE / 'assignments_with_tail_return.parquet'),
        no_trade_price_imputation=True, strict_PIT='BLOCKED_DATA')
    js('audits/inputs', price_sources)
    print('V4 full calendar and separate marks ready', flush=True)
    return panel, joined, marks, price_sources


def industry_paths(panel, joined):
    agg = joined.groupby(['era', 'level', 'industry_code', 'industry_name', 'month']).agg(
        members=('security_id', 'size'), observed=('next_return', 'count'),
        unresolved=('unresolved', 'max'), return_value=('next_return', 'mean')).reset_index()
    agg['coverage'] = agg.observed / (agg.members + agg.unresolved)
    agg['month'] = agg.month + 1
    # The tail October observation belongs to SW2021 and may confirm an earlier peak.
    agg = agg[agg.apply(lambda r: previous.era_for_month(r.month) == r.era, axis=1)]
    agg = agg[agg.month.le(panel.month.max())]
    agg.loc[agg.members.lt(5) | agg.coverage.lt(.8), 'return_value'] = np.nan
    dates = panel.groupby('month').date.first()
    agg['date'] = agg.month.map(dates)
    agg['is_partial'] = agg.month.eq(panel.month.max())
    detail('industry_monthly_returns', agg)
    # Consecutive valid returns create a normalized price block, with a prior-month anchor.
    paths = []
    for (era, level, code), g in agg.groupby(['era', 'level', 'industry_code']):
        lookup = g.set_index('month')
        era_months = [m for m in sorted(panel.month.unique()) if previous.era_for_month(m) == era]
        active, nav, block, rows = False, 1., 0, []
        for month in era_months:
            valid = month in lookup.index and pd.notna(lookup.loc[month, 'return_value'])
            if not valid:
                active = False
                continue
            r = lookup.loc[month]
            if not active:
                block += 1
                nav = 1.
                prior = month - 1
                if prior not in dates.index or previous.era_for_month(prior) != era:
                    continue
                rows.append(dict(era=era, level=level, industry_code=code, industry_name=r.industry_name,
                    block=block, month=prior, date=dates.loc[prior], nav=1., monthly_return=np.nan,
                    members=r.members, coverage=np.nan, anchor=True, is_partial=False))
                active = True
            nav *= 1 + float(r.return_value)
            rows.append(dict(era=era, level=level, industry_code=code, industry_name=r.industry_name,
                block=block, month=month, date=r.date, nav=nav, monthly_return=r.return_value,
                members=r.members, coverage=r.coverage, anchor=False, is_partial=bool(r.is_partial)))
        paths.extend(rows)
    paths = pd.DataFrame(paths)
    paths.to_parquet(CACHE / 'industry_paths.parquet', index=False)
    detail('industry_price_paths', paths)
    return paths


def benchmarks():
    meta = json.loads((previous.SOURCES / 'manifest.json').read_text())
    bycode = {r['code']: r for r in meta['benchmarks']}
    result = {}
    for label, code in BENCHMARKS:
        file = previous.SOURCES / (code + '.parquet')
        assert sha(file) == bycode[code]['sha256']
        f = pd.read_parquet(file).sort_values('date').set_index('date')
        assert len(f) == 2377 and f[['open', 'close']].gt(0).all().all()
        result[label] = f
    return result
