import json
from pathlib import Path
import numpy as np
import pandas as pd
from price_experiment import EP,SOURCE,digest
from conditional_experiment import interval


def main():
    panel=pd.read_parquet('/tmp/ep33_r01_panel.parquet')
    n=len(pd.read_parquet(SOURCE/'CSI_ALL.parquet'))
    policy=pd.read_csv(EP/'outputs/r03/selected.csv.gz',parse_dates=['date'],low_memory=False)
    policy=policy[policy.pool.eq('accelerating_improvement')&policy.strategy.eq('joint_velocity')]
    out=EP/'outputs/final';out.mkdir(exist_ok=True,parents=True)
    records=[];selections=[]
    for date,g in panel.groupby('date'):
        a=policy[policy.date.eq(date)].sort_values('rank')
        base=g[g.coverage.ge(.8)&g.members.ge(5)].dropna(subset=['velocity','acceleration','prior63','vol63'])
        k=min(10,len(a),len(base));a=a.head(k)
        b=base.sort_values(['velocity','industry_code'],ascending=[False,True]).head(k)
        for arm,s in [('policy',a),('global_velocity',b)]:
            s=s.copy();s['arm']=arm;selections.append(s)
        if not k:
            records.append(dict(date=date,k=0,complete=False,calendar_mature=False,eligible=len(base),reason='NO_63D_ELIGIBLE_INPUT' if base.empty else 'NO_POLICY_CANDIDATE_OR_SMALL_STATE_POOL'));continue
        ka=int(a.excess126.notna().sum());kb=int(b.excess126.notna().sum())
        mature=bool((a.day_i+127<n).all()&(b.day_i+127<n).all())
        na,nb=k-ka,k-kb
        sa=a.excess126.sum();sb=b.excess126.sum()
        records.append(dict(date=date,k=k,complete=bool(ka==k and kb==k),calendar_mature=mature,
            known_policy=ka,known_control=kb,delta=a.excess126.mean()-b.excess126.mean(),
            policy_return=a.return126.mean(),control_return=b.return126.mean(),
            policy_excess=a.excess126.mean(),control_excess=b.excess126.mean(),
            stress_low=(sa-.5*na-sb-.5*nb)/k,stress_high=(sa+.5*na-sb+.5*nb)/k,
            adverse_delta=a.adverse126.mean()-b.adverse126.mean()))
    f=pd.DataFrame(records);f.to_csv(out/'global_date_pairs.csv',index=False)
    pd.concat(selections,ignore_index=True).to_csv(out/'global_selected.csv.gz',index=False)
    c=f[f.complete].set_index('date');m=c.delta.groupby(c.index.to_period('M')).mean();ci=interval(m,12)
    stress=f[f.calendar_mature].set_index('date')
    summary={'dates':len(f),'signal_dates':int(f.k.gt(0).sum()),'empty_dates':int(f.k.eq(0).sum()),'complete_dates':len(c),'months':len(m),
        'delta':m.mean(),'ci_low':ci[0],'ci_high':ci[1],'policy_excess_date_equal':c.policy_excess.mean(),
        'control_excess_date_equal':c.control_excess.mean(),'adverse_delta':c.adverse_delta.mean(),
        'mature_stress_dates':len(stress),
        'stress_low':stress.stress_low.groupby(stress.index.to_period('M')).mean().mean(),
        'stress_high':stress.stress_high.groupby(stress.index.to_period('M')).mean().mean(),
        'stress_note':'assumed +/-50pp unknown outcomes, not statistical bounds or estimates'}
    (out/'global_summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    c.groupby(c.index.year).agg(dates=('delta','size'),delta=('delta','mean')).rename_axis('year').reset_index().to_csv(out/'global_annual.csv',index=False)
    (out/'global_receipt.json').write_text(json.dumps({'inputs':{str(p):digest(p) for p in [Path('/tmp/ep33_r01_panel.parquet'),EP/'outputs/r03/selected.csv.gz',EP/'rounds/final_comparison_plan.md',Path(__file__)]}},indent=2)+'\n')
    print(json.dumps(summary,indent=2))

if __name__=='__main__':main()
