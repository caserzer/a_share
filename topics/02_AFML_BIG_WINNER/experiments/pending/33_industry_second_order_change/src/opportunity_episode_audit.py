"""R14 event management audit; never change scores or frozen primary gates."""
import json
import numpy as np
import pandas as pd
from probability_pool import KEY,HORIZONS,data,block_interval
from pool_evaluation import EP,sha,calendar_dates
OUT=EP/'outputs/r14'

def episodes(g):
    g=g.sort_values(KEY+['date']).copy()
    g['cluster_first126']=False;g['repeat_within126']=False;g['rearm4']=False
    g['opportunity_id']=None;g['cluster_first_date']=pd.NaT
    for key,a in g.groupby(KEY):
        anchor=-100000;cluster=0;anchor_date=None
        previous_week=None;previous_flag=None;seen_episode=False;off_run=0
        for ix,r in a.iterrows():
            flag=bool(r.admitted);gap=previous_week is not None and r.week_i-previous_week!=1
            if previous_week is None:
                seen_episode=flag;off_run=0 if flag else 1
            elif gap:
                seen_episode=True;off_run=0 if flag else 1
            elif flag:
                if previous_flag is False and (not seen_episode or off_run>=4):g.loc[ix,'rearm4']=True
                seen_episode=True;off_run=0
            else:off_run+=1
            if r.entry:
                if r.day_i-anchor>=126:
                    cluster+=1;anchor=int(r.day_i);anchor_date=r.date;g.loc[ix,'cluster_first126']=True
                else:g.loc[ix,'repeat_within126']=True
                g.loc[ix,'opportunity_id']='|'.join(map(str,key))+f'|{cluster}'
                g.loc[ix,'cluster_first_date']=anchor_date
            previous_week=r.week_i;previous_flag=flag
    return g

def main():
    out=OUT;p=data();scores=pd.read_parquet(out/'scored_outcomes.parquet');dates=calendar_dates();dates=dates[dates>=pd.Timestamp('2024-01-01')]
    rows=[];annual=[];events=[];retention=[]
    for model,g in scores.groupby('model'):
        a=episodes(g);assert a.cluster_first126.equals(a.cooldown126)
        assert not (a.rearm4&~a.entry).any()
        assert (a.cluster_first126|a.repeat_within126).equals(a.entry)
        events.append(a[['row_id','date','era','industry_code','block','day_i','week_i','model','entry','refit_entry','boundary_unknown','cluster_first126','repeat_within126','rearm4','opportunity_id','cluster_first_date']])
        for policy in ['entry','cluster_first126','repeat_within126','rearm4']:
            z=a[a[policy]];counts=z.groupby('date').size().reindex(dates,fill_value=0)
            for h in HORIZONS:
                col=f'win{h}';k=z[z[col].notna()].copy();base=p[p.eligible].groupby('date')[col].mean();k['reference_rate']=k.date.map(base);k['delta']=k[col]-k.reference_rate
                lo,hi=block_interval(k,dates,26 if h==126 else round(h/5))
                win=k[col].mean();delta=k.delta.mean();gap=abs(k.probability.mean()-win) if h==126 else np.nan
                recall=a.loc[a.admitted,col].sum()/a[col].sum() if a[col].sum() else np.nan
                checks={'win60':win>=.6,'uplift5pp':delta>=.05,'recall10':recall>=.1,'known100':len(k)>=100,'ci_positive':lo>0,'calibration5pp':gap<=.05}
                rows.append(dict(model=model,policy=policy,horizon=h,total=len(z),known=len(k),wins=int(k[col].sum()),immature=int(z[f'status{h}'].eq('IMMATURE').sum()),missing=int(z[f'status{h}'].eq('MISSING_PATH').sum()),
                    win_rate=win,reference_rate=k.reference_rate.mean(),uplift=delta,uplift_lo=lo,uplift_hi=hi,calibration_gap=gap,success_week_recall=recall,
                    preserved_event_fraction=len(z)/int(a.entry.sum()) if a.entry.sum() else np.nan,entry_dates=k.date.nunique(),mean_events_per_week=counts.mean(),
                    refit_events=int(z.refit_entry.sum()),metric_pass=all(checks.values()) if h==126 else False,failed_gates=';'.join(key for key,value in checks.items() if not value) if h==126 else 'SENSITIVITY_NOT_PRIMARY'))
                for year,b in z.groupby(z.date.dt.year):
                    v=b[b[col].notna()];annual.append(dict(model=model,policy=policy,horizon=h,year=year,total=len(b),known=len(v),wins=v[col].sum(),win_rate=v[col].mean(),reference_rate=v.date.map(base).mean(),uplift=(v[col]-v.date.map(base)).mean()))
    pd.DataFrame(rows).to_csv(out/'episode_summary.csv',index=False);pd.DataFrame(annual).to_csv(out/'episode_annual.csv',index=False)
    pd.concat(events,ignore_index=True).to_csv(out/'opportunity_registry.csv.gz',index=False)
    (out/'episode_receipt.json').write_text(json.dumps({'inputs':{str(f):sha(f) for f in [out/'scored_outcomes.parquet',EP/'rounds/r14_conditional_calibration_plan.md',__file__]},'thresholds_unchanged':True,'primary_protocol_still_entry':True,'coverage_definition':'weekly state coverage unchanged across event policies; not event recall','cluster_first_matches_legacy_cooldown':True},indent=2)+'\n')
    print(pd.DataFrame(rows).query('horizon==126')[['model','policy','known','win_rate','reference_rate','uplift','calibration_gap','metric_pass']].to_string(index=False))
if __name__=='__main__':main()
