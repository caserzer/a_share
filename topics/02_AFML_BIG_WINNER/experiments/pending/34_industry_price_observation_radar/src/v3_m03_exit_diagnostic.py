"""Observed local-improvement exits; not an alternative exit-rule experiment."""
import json
from pathlib import Path
import pandas as pd
from audit_local_inputs import EP,sha


def main():
    root=EP/'outputs/v3_m03_replay';out=EP/'outputs/v3_m03_decisions';source=EP/'outputs/v3_m02_models/scored_catalog.parquet'
    d=pd.read_parquet(source,columns=['date','era','industry_code','r5','block','week']).sort_values(['era','industry_code','week'])
    prev=d.groupby(['era','industry_code'])[['r5','block','week']].shift()
    d['previous_r5_positive']=d.r5.gt(0)&prev.r5.gt(0)&d.block.eq(prev.block)&d.week.sub(prev.week).eq(1)
    rows=[];events=[]
    for run in pd.read_csv(root/'run_inventory.csv').itertuples():
        e=pd.read_parquet(root/run.run_id/'events.parquet').merge(d[['date','era','industry_code','previous_r5_positive']],on=['date','era','industry_code'],how='left',validate='one_to_one')
        new=e[e.kind.eq('NEW')];ex=e[e.kind.eq('EXIT')];weak=ex[ex.reason.eq('TWO_WEAK_REVIEWS')];conflict=weak[weak.previous_r5_positive.eq(True)]
        rows.append(dict(run_id=run.run_id,new=len(new),new_r20_nonpositive=int(new.r20.le(0).sum()),exits=len(ex),two_weak_exits=len(weak),two_weak_exit_current_r5_positive=int(weak.r5.gt(0).sum()),two_weak_exit_two_positive_r5=len(conflict)))
        for r in conflict.itertuples():events.append(dict(run_id=run.run_id,event_id=r.event_id,date=r.date,era=r.era,industry_code=r.industry_code,r5=r.r5,r20=r.r20))
    frames={'exit_conflict_counts.csv':pd.DataFrame(rows),'exit_conflict_events.csv':pd.DataFrame(events)}
    for name,frame in frames.items():
        file=out/name
        if file.exists():
            parsed=pd.read_csv(file,parse_dates=['date'] if 'date' in frame else None)
            pd.testing.assert_frame_equal(parsed,frame)
        else:frame.to_csv(file,index=False)
    sources=[source,root/'receipt.json',Path(__file__)]
    (out/'exit_diagnostic_receipt.json').write_text(json.dumps(dict(inputs={str(p):sha(p) for p in sources},artifacts={name:sha(out/name) for name in frames},limits='Observed exit conditions only, not counterfactual performance or proof of causation.'),indent=2)+'\n')
    print(pd.DataFrame(rows).to_string(index=False))


if __name__=='__main__':main()
