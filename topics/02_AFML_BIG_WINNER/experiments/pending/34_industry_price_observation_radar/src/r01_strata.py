"""Fixed-baseline descriptive strata; never filter or regenerate observations."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from audit_local_inputs import EP, PRIOR, CACHE, sha


def main():
    out = EP/'outputs/r01'
    if (out/'strata.json').exists():
        raise FileExistsError('strata already exists')
    afile = out/'evaluated_new_observations.parquet'
    pfile = EP/'outputs/r00_metric_denominators/full_process_registry.parquet'
    hfile = out/'past_only_features.parquet'
    mfile = CACHE/'forecast_v5/CSI_ALL.parquet'
    rawfile = PRIOR/'daily_industries.parquet'
    a = pd.read_parquet(afile)
    p = pd.read_parquet(pfile)
    h = pd.read_parquet(hfile)
    raw = pd.read_parquet(rawfile)
    calendarfile=Path(next(x for x in json.loads((PRIOR/'receipt.json').read_text())['inputs'] if x.endswith('/calendar.parquet')))
    dates=pd.read_parquet(calendarfile).sort_values('date').reset_index(drop=True)
    dates['day_i']=np.arange(len(dates))
    dates=dates[dates.day_i<=raw.day_i.max()]
    observed=raw[['day_i','date']].drop_duplicates()
    joined=observed.merge(dates,on='day_i',validate='one_to_one')
    assert len(joined)==len(observed) and joined.date_x.equals(joined.date_y)
    m = pd.read_parquet(mfile).close.reindex(pd.DatetimeIndex(dates.date))
    known = m.gt(0).rolling(127,min_periods=127).sum().eq(127)
    regime = pd.Series(np.where(known, np.where(m/m.shift(126)-1>0,'UP','NONUP'),'UNKNOWN'),index=m.index)
    for frame, date_col in [(a,'date'),(p,'start_date')]:
        frame['market_regime'] = frame[date_col].map(regime).fillna('UNKNOWN')
    quality = h.set_index(['era','industry_code','date']).history_proxy
    for frame,date_col in [(a,'date'),(p,'start_date')]:
        idx = pd.MultiIndex.from_arrays([frame.era,frame.industry_code,frame[date_col]])
        values = quality.reindex(idx).to_numpy()
        frame['history_quality'] = np.where(pd.isna(values),'UNKNOWN',np.where(values>0,'PROXY_FLAG','NO_PRICE_PROXY_FLAG'))
    hits = set(a.loc[a.recall_credit,'process_id'])
    p['hit'] = p.process_id.isin(hits)
    eligible = p[p.mature & ~p.left_origin_uncertain]
    tables = {}
    for column in ['market_regime','history_quality','era']:
        rows = []
        for value in sorted(set(a[column])|set(p[column])):
            x=a[a[column].eq(value)]; y=eligible[eligible[column].eq(value)]
            n=int(x.new_observation_denominator.sum()); s=int(x.recall_credit.sum()); k=int(y.hit.sum())
            rows.append(dict(stratum=value,new_alerts=len(x),evaluable_alerts=n,successes=s,
                             precision=None if not n else s/n,known_processes=len(y),recalled=k,
                             recall=None if not len(y) else k/len(y),outcomes=x.outcome.value_counts().to_dict()))
        assert sum(r['new_alerts'] for r in rows)==len(a)
        assert sum(r['evaluable_alerts'] for r in rows)==int(a.new_observation_denominator.sum())
        assert sum(r['known_processes'] for r in rows)==len(eligible)
        assert sum(r['recalled'] for r in rows)==int(eligible.hit.sum())
        tables[column]=rows
    # Ex-post market-relative observation is secondary, never part of the main label.
    market_byday=pd.Series(m.to_numpy(),index=dates.day_i)
    groups={key:g.set_index('day_i') for key,g in raw.groupby(['era','industry_code'])}
    secondary=[]
    for r in a.itertuples():
        g=groups[(r.era,r.industry_code)].reindex(range(r.day,r.day+61))
        b=market_byday.reindex(range(r.day,r.day+61))
        valid=(len(g)==61 and g.nav.notna().all() and g.nav.gt(0).all() and g.block.notna().all()
               and g.block.nunique()==1 and b.notna().all() and b.gt(0).all())
        industry=float(g.nav.iloc[-1]/g.nav.iloc[0]-1) if valid else None
        benchmark=float(b.iloc[-1]/b.iloc[0]-1) if valid else None
        secondary.append(dict(alert_id=r.alert_id,path_known=bool(valid),industry_return60=industry,
                              market_return60=benchmark,excess_return60=None if not valid else industry-benchmark,
                              main_outcome=r.outcome))
    secondary=pd.DataFrame(secondary)
    secondary.to_parquet(out/'secondary_market_returns.parquet',index=False)
    a.to_parquet(out/'alert_strata.parquet',index=False)
    p.to_parquet(out/'process_strata.parquet',index=False)
    result=dict(tables=tables,quality_scope='Prior 61 sessions only at alert/origin; no price proxy flag does not establish strict PIT',
                market_scope='Prior 126 sessions, all 127 closes required; precision at alert, recall at process origin',
                secondary_scope='60-session industry minus market return; descriptive only, not a success label or 63/126/252 investment tracking',
                secondary=dict(total=len(secondary),known=int(secondary.path_known.sum()),unknown=int((~secondary.path_known).sum()),
                               positive_absolute=int(secondary.industry_return60.gt(0).sum()),
                               positive_excess=int(secondary.excess_return60.gt(0).sum()),
                               positive_both=int((secondary.industry_return60.gt(0)&secondary.excess_return60.gt(0)).sum())),
                inputs={str(x):sha(x) for x in [afile,pfile,hfile,mfile,rawfile,calendarfile,EP/'src/r01_strata.py']})
    (out/'strata.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='inputs'},ensure_ascii=False))


if __name__=='__main__':
    main()
