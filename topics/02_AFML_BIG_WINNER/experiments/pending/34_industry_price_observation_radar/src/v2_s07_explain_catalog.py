"""Explain frozen primary observations using contemporaneous inputs only."""
import json
from pathlib import Path
import pandas as pd
import numpy as np
from audit_local_inputs import EP, sha
from v2_b06_replay import prepare


def main():
    root = EP / 'outputs/refresh/s02_chain_safe_v2_20261112'
    source = root / 'delivery/A/all_observations.parquet'
    events_path = root / 'A/events.parquet'
    out = EP / 'outputs/v2_s07_explained_primary'
    out.mkdir(exist_ok=False)
    original = pd.read_parquet(source)
    events = pd.read_parquet(events_path)
    c = prepare()
    keys = ['date', 'era', 'industry_code']
    base = original.merge(c[keys + ['week', 'r40', 'eligible']], on=keys, validate='one_to_one')
    exits = {}
    rows = []
    checked_new = 0
    for date, g in base.groupby('date', sort=True):
        week = int(g.week.iloc[0])
        ev = events[events.date.eq(date)]
        for r in ev[ev.kind.eq('EXIT')].itertuples():
            exits[(r.era, r.industry_code)] = week
        retained = set(zip(g.loc[g.state.eq('TRACKING'), 'era'], g.loc[g.state.eq('TRACKING'), 'industry_code']))
        free = 20 - len(retained)
        cooldown = {(r.era, r.industry_code): max(0, 4 - (week - exits.get((r.era, r.industry_code), -100))) for r in g.itertuples()}
        eligible = g[g.eligible].sort_values(['r20', 'industry_code'], ascending=[False, True])
        candidates = [(r.era, r.industry_code) for r in eligible.itertuples() if (r.era, r.industry_code) not in retained and cooldown[(r.era, r.industry_code)] == 0]
        ranks = {key: i + 1 for i, key in enumerate(candidates)}
        quota = min(5, free, len(candidates))
        actual = set(zip(ev.loc[ev.kind.eq('NEW'), 'era'], ev.loc[ev.kind.eq('NEW'), 'industry_code']))
        assert set(candidates[:quota]) == actual, str(date)
        assert actual == set(zip(g.loc[g.state.eq('NEW'), 'era'], g.loc[g.state.eq('NEW'), 'industry_code']))
        checked_new += len(actual)
        for r in g.itertuples():
            key = (r.era, r.industry_code)
            rank = ranks.get(key)
            causes = []
            if not np.isfinite(r.r40) or not np.isfinite(r.r5) or not np.isfinite(r.r20):
                causes.append('DATA_INSUFFICIENT')
            else:
                if r.r5 <= 0: causes.append('NONPOSITIVE_5D')
                if r.r20 <= 0: causes.append('NONPOSITIVE_20D')
            if cooldown[key] > 0: causes.append('COOLDOWN')
            if rank is not None:
                if rank > 5: causes.append('WEEKLY_NEW_LIMIT')
                if rank > free: causes.append('POOL_SPACE_LIMIT')
            if r.state == 'NOT_TRIGGERED':
                assert causes, (date, key)
            risk = r.state == 'TRACKING' and r.r5 <= 0
            rows.append(dict(date=date, era=r.era, industry_code=r.industry_code,
                admission_price_eligible=bool(r.eligible), cooldown_reviews_remaining=cooldown[key],
                admission_candidate_rank=rank, free_slots_after_updates=free,
                weekly_admission_quota=quota, non_admission_constraints='|'.join(causes) if r.state not in ('NEW', 'TRACKING') else '',
                tracking_evidence='RISK_OR_NO_IMPROVEMENT' if risk else 'POSITIVE_5D' if r.state in ('NEW', 'TRACKING') else 'NOT_ACTIVE',
                reviews_to_age_limit=max(0, 8-int(r.age_weeks)) if r.state in ('NEW', 'TRACKING') else None))
    extra = pd.DataFrame(rows)
    enriched = original.merge(extra, on=keys, validate='one_to_one', sort=False)
    pd.testing.assert_frame_equal(enriched[original.columns], original)
    assert len(enriched) == len(original) and not enriched.duplicated(keys).any()
    enriched.to_parquet(out / 'all_observations.parquet', index=False)
    latest = enriched[enriched.date.eq(enriched.date.max())]
    latest.to_csv(out / 'latest_full_catalog.csv', index=False)
    counts = enriched[enriched.state.eq('NOT_TRIGGERED')].groupby('non_admission_constraints').size().rename('industry_weeks').reset_index()
    counts.to_csv(out / 'non_admission_counts.csv', index=False)
    summary = dict(rows=len(enriched), original_columns_preserved=len(original.columns),
        verified_new_events=checked_new, supported_weeks=int(enriched.date.nunique()),
        not_triggered_rows=int(enriched.state.eq('NOT_TRIGGERED').sum()),
        latest_date=str(latest.date.max().date()), latest_state_counts=latest.state.value_counts().to_dict(),
        latest_tracking_evidence=latest[latest.state.isin(['NEW','TRACKING'])].tracking_evidence.value_counts().to_dict(),
        interpretation='Delivery explanations only; no signal, process, evaluation or event changes. Constraint overlap is not counterfactual performance.')
    (out/'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2)+'\n')
    inputs = [source, events_path, EP/'src/v2_b06_replay.py', EP/'protocols/v2_s07/plan.md', Path(__file__)]
    from audit_local_inputs import PRIOR
    inputs += [PRIOR/'daily_industries.parquet', EP/'outputs/r01/weekly_catalog.parquet']
    (out/'receipt.json').write_text(json.dumps(dict(inputs={str(p):sha(p) for p in inputs}, artifacts={p.name:sha(p) for p in out.iterdir() if p.is_file()}, verification=summary),ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == '__main__':
    main()
