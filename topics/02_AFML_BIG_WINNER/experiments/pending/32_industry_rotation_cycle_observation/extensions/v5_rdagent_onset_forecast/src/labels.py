"""Ex-post daily onsets and conservative event-by-event label maturity."""
import json
import numpy as np
import pandas as pd
from common import CACHE, OUT, KEY, THRESHOLDS, BENCHMARKS, load_turns, js, sha


def label_one(t, horizon, stages, block_end, benchmark):
    inside=[s for s in stages if t < s['start_date'] <= horizon]
    positive=[s for s in inside if s['qualified_'+benchmark]]
    if positive:
        event=min(positive,key=lambda s:s['end_confirmed_at'])
        return 1.,event['end_confirmed_at'],event['phase_id'],'POSITIVE_CONFIRMED'
    if horizon>block_end:
        return np.nan,pd.NaT,None,'HORIZON_CROSSES_BLOCK_END'
    if any(s['left_censored'] or s['status']!='CONFIRMED' for s in inside):
        return np.nan,pd.NaT,None,'UNRESOLVED_WINDOW_STAGE'
    witnesses=[s for s in stages if s['start_date']>horizon and not s['left_censored']]
    if not witnesses:
        return np.nan,pd.NaT,None,'NO_LATER_CONFIRMED_TROUGH'
    witness=min(witnesses,key=lambda s:s['start_confirmed_at'])
    mature=max([witness['start_confirmed_at']]+[s['end_confirmed_at'] for s in inside])
    return 0.,mature,witness['phase_id'],'NEGATIVE_WITH_LATER_TROUGH_WITNESS'


def run():
    daily=pd.read_parquet(CACHE/'daily_industries.parquet')
    f=pd.read_parquet(CACHE/'features.parquet')
    benchmarks={k:pd.read_parquet(CACHE/f'{k}.parquet').close for k in BENCHMARKS}
    upswings=load_turns(); rows=[]; blocks={}
    for key,g in daily.groupby(KEY+['block'],sort=False):
        g=g.sort_values('date').reset_index(drop=True);blocks[key]=g.date.max()
        for threshold in THRESHOLDS:
            for s in upswings(g.nav,threshold):
                a,p,z=[g.iloc[s[k]] for k in ['start_i','peak_i','evaluation_i']]
                end_confirm=g.iloc[s['end_confirm_i']].date if s['end_confirm_i'] is not None else pd.NaT
                bounded=(z.date>=a.date+pd.DateOffset(months=6)) and (z.date<=a.date+pd.DateOffset(months=18))
                r=dict(zip(KEY+['block'],key));r.update(threshold=threshold,
                    phase_id=f'{key[0]}_{key[1]}_{key[2]}_{key[3]}_{threshold}_{a.date.date()}',
                    industry_name=a.industry_name,start_date=a.date,peak_date=p.date,end_date=z.date,
                    start_confirmed_at=g.iloc[s['start_confirm_i']].date,end_confirmed_at=end_confirm,
                    status=s['status'],left_censored=bool(s['left_censored']),
                    duration_days=(z.date-a.date).days,in_range_6_18=bool(bounded),
                    industry_return=float(z.nav/a.nav-1))
                for bm,b in benchmarks.items():
                    r['benchmark_return_'+bm]=float(b.loc[z.date]/b.loc[a.date]-1)
                    r['qualified_'+bm]=bool(s['status']=='CONFIRMED' and not s['left_censored'] and bounded
                        and r['industry_return']>0 and r['industry_return']>r['benchmark_return_'+bm])
                rows.append(r)
    phases=pd.DataFrame(rows)
    phases.to_parquet(CACHE/'daily_phases.parquet',index=False)
    phases.to_csv(OUT/'daily_phases.csv.gz',index=False,compression={'method':'gzip','mtime':0})
    labels=[]; groups={k:g.to_dict('records') for k,g in phases.groupby(KEY+['block','threshold'])}
    for key,g in f.groupby(KEY+['block'],sort=False):
        for threshold in THRESHOLDS:
            stages=groups.get((*key,threshold),[])
            for row in g.itertuples():
                horizon=row.date+pd.DateOffset(months=1)
                for bm in BENCHMARKS:
                    value,available,event,reason=label_one(row.date,horizon,stages,blocks[key],bm)
                    labels.append(dict(row_id=row.row_id,threshold=threshold,benchmark=bm,y=value,
                        label_available_at=available,horizon_end=horizon,event_or_witness_id=event,reason=reason))
    labels=pd.DataFrame(labels)
    labels.to_parquet(CACHE/'labels.parquet',index=False)
    assert (labels.loc[labels.y.notna(),'label_available_at']>f.set_index('row_id').date.reindex(
        labels.loc[labels.y.notna(),'row_id']).to_numpy()).all()
    view=labels.merge(f[['row_id','frequency','date','level']],on='row_id',validate='many_to_one')
    summary=view.groupby(['frequency','level','threshold','benchmark']).agg(rows=('row_id','size'),
        mature=('y','count'),positives=('y','sum')).reset_index()
    summary['unknown']=summary.rows-summary.mature
    summary.to_csv(OUT/'label_coverage.csv',index=False)
    js(OUT/'label_audit.json',dict(phases=len(phases),label_rows=len(labels),known=int(labels.y.notna().sum()),
        phases_sha256=sha(CACHE/'daily_phases.parquet'),labels_sha256=sha(CACHE/'labels.parquet'),
        negative_policy='later-confirmed-trough witness; never absent-from-winner-list = 0',
        label_resolution='daily; distinct from V4 monthly turns',features_separate=True))
    print('daily phases',len(phases),'labels',len(labels),'known',int(labels.y.notna().sum()),flush=True)


if __name__=='__main__':run()
