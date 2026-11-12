import json
from pathlib import Path
import pandas as pd
from price_experiment import EP,digest
from conditional_experiment import interval


def main():
    panel=pd.read_parquet('/tmp/ep33_r01_panel.parquet')
    agg=pd.read_csv(EP/'outputs/r04/industry_coverage.csv.gz',parse_dates=['date'])
    panel=panel.merge(agg,on=['date','era','industry_code'],how='left',validate='one_to_one')
    out=EP/'outputs/r05';out.mkdir(parents=True,exist_ok=True)
    rows=[];selections=[];coverage=[]
    for date,g in panel.groupby('date'):
        base=g[g.acceleration.notna()&g.coverage.ge(.8)&g.members.ge(5)&g.finance_count.ge(3)&g.finance_coverage.ge(.3)].copy()
        for kind,pool in [('all_finance',base),('joint_improvement',base[base.velocity.ge(0)&base.acceleration.gt(0)&base.persistence.ge(.8)&base.breadth_change.gt(0)&base.breadth_acceleration.gt(0)])]:
            pool=pool.copy();pool['blend']=(pool.velocity.rank(pct=True)+pool.finance_acceleration.rank(pct=True))/2
            k=min(10,len(pool));coverage.append(dict(date=date,pool=kind,pool_n=len(pool),k=k))
            if not k:continue
            arms={a:pool.sort_values([a,'industry_code'],ascending=[False,True]).head(k) for a in ['blend','velocity']}
            for arm,s in arms.items():
                s=s.copy();s['strategy']=arm;s['pool']=kind;selections.append(s)
            a,b=arms['blend'],arms['velocity']
            rows.append(dict(date=date,pool=kind,k=k,complete=bool(a.excess126.notna().all()&b.excess126.notna().all()),
                delta=a.excess126.mean()-b.excess126.mean(),known_a=int(a.excess126.notna().sum()),known_b=int(b.excess126.notna().sum())))
    pd.concat(selections,ignore_index=True).to_csv(out/'selected.csv.gz',index=False)
    pd.DataFrame(coverage).to_csv(out/'coverage.csv',index=False)
    f=pd.DataFrame(rows);f.to_csv(out/'date_pairs.csv',index=False)
    summary=[]
    for kind,g in f.groupby('pool'):
        c=g[g.complete].set_index('date');m=c.delta.groupby(c.index.to_period('M')).mean();ci=interval(m,12) if len(m)>=12 else [None,None]
        summary.append(dict(pool=kind,dates=len(g),complete_dates=len(c),months=len(m),delta=m.mean(),ci_low=ci[0],ci_high=ci[1]))
    pd.DataFrame(summary).to_csv(out/'summary.csv',index=False)
    (out/'receipt.json').write_text(json.dumps({'round':'r05','inputs':{str(p):digest(p) for p in [Path('/tmp/ep33_r01_panel.parquet'),EP/'outputs/r04/industry_coverage.csv.gz',EP/'rounds/r05_plan.md',Path(__file__)]}},indent=2)+'\n')
    print(pd.DataFrame(summary).to_string(index=False))

if __name__=='__main__':main()
