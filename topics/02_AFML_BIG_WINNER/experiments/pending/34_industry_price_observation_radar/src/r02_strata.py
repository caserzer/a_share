"""R02 exhaustive strata and original omission cohort accounting."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from audit_local_inputs import EP,PRIOR,CACHE,sha
from post_alert_evaluation import registered_rules


def main():
    out=EP/'outputs/r02'
    if (out/'strata.json').exists():raise FileExistsError('strata exists')
    rawfile=PRIOR/'daily_industries.parquet';raw=pd.read_parquet(rawfile)
    pfile=EP/'outputs/r00_metric_denominators/full_process_registry.parquet';p=pd.read_parquet(pfile)
    hfile=out/'past_only_features.parquet';h=pd.read_parquet(hfile)
    calendarfile=Path(next(x for x in json.loads((PRIOR/'receipt.json').read_text())['inputs'] if x.endswith('/calendar.parquet')))
    cal=pd.read_parquet(calendarfile).sort_values('date').reset_index(drop=True);cal['day_i']=cal.index
    mfile=CACHE/'forecast_v5/CSI_ALL.parquet';m=pd.read_parquet(mfile).close.reindex(pd.DatetimeIndex(cal.date))
    known=m.gt(0).rolling(127,min_periods=127).sum().eq(127)
    regimes=pd.Series(np.where(known,np.where(m/m.shift(126)-1>0,'UP','NONUP'),'UNKNOWN'),index=m.index)
    quality=h.set_index(['era','industry_code','date']).history_proxy
    def attach(frame,datecol):
        frame=frame.copy();frame['market_regime']=frame[datecol].map(regimes).fillna('UNKNOWN')
        idx=pd.MultiIndex.from_arrays([frame.era,frame.industry_code,frame[datecol]])
        q=quality.reindex(idx).to_numpy();frame['history_quality']=np.where(pd.isna(q),'UNKNOWN',np.where(q>0,'PROXY_FLAG','NO_PRICE_PROXY_FLAG'))
        frame['year']=frame[datecol].dt.year.astype(str)
        return frame
    p=attach(p,'start_date');eligible=p[p.mature & ~p.left_origin_uncertain]
    c=registered_rules();groups={k:g.set_index('day_i').sort_index() for k,g in raw.groupby(['era','industry_code'])}
    marketday=pd.Series(m.to_numpy(),index=cal.day_i)
    omissionfile=EP/'outputs/r01/process_window_audit.parquet';omissions=pd.read_parquet(omissionfile)
    oldcohort=set(omissions.loc[omissions.category.eq('NO_POSITIVE_REVIEW'),'process_id'])
    tables=[];secondary=[];hits={};paths=[]
    for arm in ['A','B']:
        f=attach(pd.read_parquet(out/f'{arm}_evaluated.parquet'),'date')
        f.to_parquet(out/f'{arm}_strata.parquet',index=False)
        hits[arm]=set(f.loc[f.recall_credit,'process_id'])
        for ac,pc,gate in [('hint_kind','kind','type'),('year','year','year'),('market_regime','market_regime','regime'),('history_quality','history_quality',None),('era','era',None)]:
            rows=[]
            for value in sorted(set(f[ac])|set(p[pc])):
                x=f[f[ac].eq(value)];y=eligible[eligible[pc].eq(value)]
                n=int(x.new_observation_denominator.sum());s=int(x.recall_credit.sum());k=int(y.process_id.isin(hits[arm]).sum())
                precision=None if not n else s/n;recall=None if not len(y) else k/len(y)
                status='DESCRIPTIVE'
                if gate:
                    status='INSUFFICIENT_SUPPORT' if n<c[f'{gate}_minimum_alerts'] or len(y)<c[f'{gate}_minimum_processes'] else 'FAIL_FLOORS' if precision<c[f'{gate}_precision_floor'] or recall<c[f'{gate}_recall_floor'] else 'POINT_FLOORS_ONLY'
                    if value=='UNKNOWN':status='UNKNOWN_SEPARATE'
                rows.append(dict(arm=arm,dimension=pc,stratum=value,new_alerts=len(x),evaluable=n,successes=s,precision=precision,
                                 known_processes=len(y),recalled=k,recall=recall,gate_status=status,outcomes=x.outcome.value_counts().to_dict()))
            assert sum(x['new_alerts'] for x in rows)==len(f)
            assert sum(x['known_processes'] for x in rows)==len(eligible)
            assert sum(x['successes'] for x in rows)==int(f.recall_credit.sum())
            tables.extend(rows)
        for r in f.itertuples():
            g=groups[(r.era,r.industry_code)].reindex(range(r.day,r.day+61));b=marketday.reindex(range(r.day,r.day+61))
            valid=(g.nav.notna().all() and g.nav.gt(0).all() and g.block.notna().all() and g.block.nunique()==1 and b.notna().all() and b.gt(0).all())
            ir=float(g.nav.iloc[-1]/g.nav.iloc[0]-1) if valid else None;br=float(b.iloc[-1]/b.iloc[0]-1) if valid else None
            paths.append(dict(arm=arm,alert_id=r.alert_id,path_known=bool(valid),industry_return60=ir,market_return60=br,excess_return60=None if not valid else ir-br))
        z=pd.DataFrame([x for x in paths if x['arm']==arm])
        secondary.append(dict(arm=arm,total=len(z),known=int(z.path_known.sum()),unknown=int((~z.path_known).sum()),
                              absolute_positive=int(z.industry_return60.gt(0).sum()),excess_positive=int(z.excess_return60.gt(0).sum()),
                              both_positive=int((z.industry_return60.gt(0)&z.excess_return60.gt(0)).sum())))
    pd.DataFrame(paths).to_parquet(out/'secondary_market_paths.parquet',index=False)
    cohort=dict(known_original_omissions=len(oldcohort),A_recalled=len(hits['A']&oldcohort),B_recalled=len(hits['B']&oldcohort),
                common_recalled=len(hits['A']&hits['B']&oldcohort),B_added=len((hits['B']-hits['A'])&oldcohort),B_lost=len((hits['A']-hits['B'])&oldcohort))
    inputs=[rawfile,pfile,hfile,calendarfile,mfile,omissionfile,out/'A_evaluated.parquet',out/'B_evaluated.parquet',Path(__file__)]
    result=dict(tables=tables,secondary=secondary,original_no_positive_cohort=cohort,
                scope='Descriptive strata, no subset selection; precision at alert and recall at process origin',
                quality_scope='Past 61 sessions price flags; no flags does not prove strict PIT',
                inputs={str(x):sha(x) for x in inputs})
    (out/'strata.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(dict(tables=[{k:v for k,v in x.items() if k!='outcomes'} for x in tables if x['dimension'] in ['kind','market_regime']],cohort=cohort,secondary=secondary),ensure_ascii=False))


if __name__=='__main__':main()
