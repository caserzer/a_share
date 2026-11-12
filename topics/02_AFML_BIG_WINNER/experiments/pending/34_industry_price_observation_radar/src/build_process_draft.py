"""Offline v0.1 label feasibility only. Never import into online signal code."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from audit_local_inputs import EP, sha


def main():
    source = EP / 'outputs/r00_coverage/evaluation_coverage.parquet'
    definition = EP / 'rounds/R00_process_definition_draft.md'
    q = pd.read_parquet(source).sort_values(['era', 'industry_code', 'date'])
    ledger, anchors = [], []
    for (era, code), g in q.groupby(['era', 'industry_code'], sort=True):
        g = g.reset_index(drop=True)
        nav = g.nav.to_numpy(float)
        n = len(g)
        state = np.full(n, 'UNKNOWN_BOUNDARY_OR_PATH', dtype=object)
        blocks = g.block.to_numpy(float, na_value=np.nan)
        if n >= 121:
            w = np.lib.stride_tricks.sliding_window_view(nav, 121)
            centers = np.arange(60, n-60)
            valid = np.isfinite(w).all(axis=1) & (w > 0).all(axis=1)
            valid &= np.isfinite(blocks[:-120]) & (blocks[:-120] == blocks[120:])
            state[centers[valid]] = 'EVALUABLE_NOT_LOCAL_ORIGIN'
            local = np.argmin(np.where(np.isfinite(w[:, 55:66]), w[:, 55:66], np.inf), axis=1) == 5
            selected = np.flatnonzero(valid & local)
            for k in selected:
                i = int(centers[k]); v = w[k]; base = v[60]; f = v[61:]/base-1
                pre60 = base/v[0]-1; pre20 = base/v[40]-1
                predd = base/v[:61].max()-1
                weak = pre60 <= 0 or predd <= -.10
                enhanced = f[19]-pre20 >= .03
                kind = 'WARMING' if weak else 'HEATING' if enhanced else 'ORDINARY_CONTINUATION'
                drawdown = float(np.min(v[60:]/np.maximum.accumulate(v[60:])-1))
                conditions = dict(amplitude=bool(f[:20].max() >= .08), retained=bool(f[59] >= .05),
                                  persistence=bool((f >= .02).sum() >= 40), floor=bool(f.min() >= -.05),
                                  drawdown=bool(drawdown >= -.12))
                passed = all(conditions.values()) and kind != 'ORDINARY_CONTINUATION'
                status = 'VALID_CANDIDATE' if passed else ('ORDINARY_CONTINUATION' if kind == 'ORDINARY_CONTINUATION' else
                          'REBOUND_OR_INTERRUPTED' if conditions['amplitude'] else 'INSUFFICIENT_AMPLITUDE')
                state[i] = status
                aid = f'v0.1|{era}|{code}|{g.date.iloc[i].date()}'
                quality = g.iloc[i-60:i+61]
                anchors.append(dict(anchor_id=aid, era=era, industry_code=code, industry_name=g.industry_name.iloc[0],
                                    date=g.date.iloc[i], end_date=g.date.iloc[i+60], day_i=int(g.day_i.iloc[i]),
                                    end_day_i=int(g.day_i.iloc[i+60]), block=int(blocks[i]), kind=kind, status=status,
                                    pre60=pre60, pre20=pre20, pre_drawdown=predd, gain20_max=float(f[:20].max()),
                                    gain20=float(f[19]), gain60=float(f[59]), retained_days=int((f>=.02).sum()),
                                    worst_from_start=float(f.min()), max_drawdown=drawdown,
                                    proxy_in_121=bool((quality.stale_members.gt(0)|quality.boundary_proxy.eq(True)).any()),
                                    failed_conditions='|'.join(c for c, ok in conditions.items() if not ok)))
        z = g[['era', 'industry_code', 'date', 'status']].rename(columns={'status':'price_status'}).copy()
        z['label_support'] = state
        ledger.append(z)
    a = pd.DataFrame(anchors)
    assert not a.anchor_id.duplicated().any()
    processes = []
    a['process_id'] = None
    for key, group in a[a.status.eq('VALID_CANDIDATE')].groupby(['era', 'industry_code', 'block'], sort=True):
        current = None
        for ix, r in group.sort_values('day_i').iterrows():
            if current is None or r.day_i > current['end_day_i']+1:
                current = dict(process_id='process|'+r.anchor_id, era=r.era, industry_code=r.industry_code,
                               industry_name=r.industry_name, block=int(r.block), start_date=r.date, end_date=r.end_date,
                               start_day_i=int(r.day_i), end_day_i=int(r.end_day_i), kind=r.kind,
                               mixed_kind=False, anchors=0, proxy=False)
                processes.append(current)
            current['end_day_i'] = max(current['end_day_i'], int(r.end_day_i))
            current['end_date'] = max(current['end_date'], r.end_date)
            current['anchors'] += 1
            current['mixed_kind'] |= r.kind != current['kind']
            current['proxy'] |= bool(r.proxy_in_121)
            a.loc[ix, 'process_id'] = current['process_id']
    p = pd.DataFrame(processes)
    p['duration'] = p.end_day_i-p.start_day_i
    support = pd.concat(ledger, ignore_index=True)
    assert len(support) == len(q)
    assert a.process_id.notna().sum() == a.status.eq('VALID_CANDIDATE').sum()
    out = EP / 'outputs/r00_process_draft_v01'
    out.mkdir(parents=True, exist_ok=True)
    for name, frame in [('date_support',support),('anchors',a),('processes',p)]:
        frame.to_parquet(out/f'{name}.parquet', index=False)
    summary = dict(status='DRAFT_LABELS_NOT_FROZEN_NOT_SIGNAL_VALIDATION',
                   inputs={str(f):sha(f) for f in [source,definition,Path(__file__)]},
                   date_support=support.label_support.value_counts().to_dict(),
                   anchor_status=a.status.value_counts().to_dict(), processes=len(p),
                   kinds=p.kind.value_counts().to_dict(), duration=p.duration.describe(percentiles=[.5,.9,.95,.99]).to_dict(),
                   over252=int(p.duration.gt(252).sum()),mixed_kind=int(p.mixed_kind.sum()),
                   annual=[dict(era=era,year=int(year),kind=kind,count=len(g)) for (era,year,kind),g in p.groupby(['era',p.start_date.dt.year,'kind'])],
                   artifacts={f.name:sha(f) for f in sorted(out.glob('*.parquet'))})
    (out/'receipt.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:summary[k] for k in ['date_support','anchor_status','processes','kinds','duration','over252','mixed_kind']},ensure_ascii=False))


if __name__ == '__main__':
    main()
