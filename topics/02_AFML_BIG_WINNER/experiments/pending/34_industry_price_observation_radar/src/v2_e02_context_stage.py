"""Descriptive confirmation stage, without changing frozen outcomes."""
import json
from pathlib import Path
import pandas as pd
import numpy as np
from audit_local_inputs import EP, PRIOR, sha


def main():
    inputs = [EP/'outputs/v2_revaluation02/runs/refresh/s02_chain_safe_v2_20261112/A/event_quality.parquet', EP/'outputs/v2_s12_full_directory_duration/processes.parquet', EP/'outputs/v2_s13_duration_enhancements/children.parquet', EP/'outputs/followup_versions/s04_20261021/all_new_paths.parquet', EP/'protocols/v2_e02_context/plan.md', Path(__file__)]
    rec=json.loads((PRIOR/'receipt.json').read_text())
    calendar=Path(next(k for k in rec['inputs'] if k.endswith('/calendar.parquet')))
    inputs += [calendar]
    out=EP/'outputs/v2_e02_context/stage';out.mkdir(exist_ok=False)
    new=pd.read_parquet(inputs[0]).query("kind == 'NEW'").copy()
    assert len(new)==1459 and new.event_id.is_unique
    parents=pd.read_parquet(inputs[1]).rename(columns={'process_id':'primary_id'})
    children=pd.read_parquet(inputs[2]).rename(columns={'child_id':'primary_id'})
    labels=pd.concat([parents[['primary_id','confirm_date']],children[['primary_id','confirm_date']]])
    assert labels.primary_id.is_unique
    new=new.merge(labels,on='primary_id',how='left',validate='many_to_one')
    dates=pd.DatetimeIndex(pd.to_datetime(pd.read_parquet(calendar).date)); day={d:i for i,d in enumerate(dates)}
    new['date']=pd.to_datetime(new.date);new['confirm_date']=pd.to_datetime(new.confirm_date)
    valid=new.status.eq('COVERED');assert valid.sum()==1262 and new.loc[valid,'confirm_date'].notna().all()
    new['signed_confirmation_days']=new.confirm_date.map(day)-new.date.map(day)
    delta=new.loc[valid,'signed_confirmation_days'];assert delta.notna().all()
    assert np.array_equal(delta.clip(lower=0).values,new.loc[valid,'confirmation_delay'].values)
    new['stage']=new.status
    new.loc[valid,'stage']=np.select([delta.gt(0),delta.eq(0)],['BEFORE_REFERENCE_CONFIRMATION','ON_REFERENCE_CONFIRMATION'],default='AFTER_REFERENCE_CONFIRMATION')
    new.to_parquet(out/'all_new_stages.parquet',index=False)
    stage=[]
    for name,g in new.groupby('stage'):
        row={'stage':name,'new_count':len(g)}
        for col in ['signed_confirmation_days','lag_days','pre_gain']:
            x=g[col].dropna(); row[col+'_n']=len(x)
            for q in [.1,.5,.9]:row[col+f'_p{int(q*100)}']=float(x.quantile(q)) if len(x) else None
        stage.append(row)
    pd.DataFrame(stage).to_csv(out/'stage_summary.csv',index=False)
    paths=pd.read_parquet(inputs[3]).query("arm == 'A' and horizon in [20,60]").copy()
    assert not paths.duplicated(['event_id','horizon']).any()
    joined=paths.merge(new[['event_id','stage']],on='event_id',validate='many_to_one')
    assert len(joined)==2918 and joined.groupby('horizon').size().eq(1459).all()
    joined.to_parquet(out/'staged_followup.parquet',index=False)
    summaries=[]
    for (h,s),g in joined.groupby(['horizon','stage']):
        m=g[g.status.eq('MATURE')]
        row={'horizon':int(h),'stage':s,'new_count':len(g),'mature':len(m),'other_status_counts':json.dumps(g[~g.status.eq('MATURE')].status.value_counts().to_dict())}
        row['positive_fraction']=float(m.absolute_return.gt(0).mean()) if len(m) else None
        for col in ['absolute_return','relative_return','max_drawdown']:
            for q in [.1,.5,.9]:row[col+f'_p{int(q*100)}']=float(m[col].quantile(q)) if len(m) else None
        summaries.append(row)
    pd.DataFrame(summaries).to_csv(out/'followup_summary.csv',index=False)
    summary={'new_total':len(new),'covered_total':int(valid.sum()),'stage_counts':new.stage.value_counts().to_dict(),'confirmation_delay_verified':int(valid.sum()),'followup_rows':len(joined),'limits':'Historical descriptive partition. Reference confirmation is retrospective, not online availability. No method or label change.'}
    (out/'receipt.json').write_text(json.dumps({'inputs':{str(p):sha(p) for p in inputs},'artifacts':{p.name:sha(p) for p in out.iterdir() if p.is_file()},'verification':summary},ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(summary,ensure_ascii=False))

if __name__=='__main__':main()
