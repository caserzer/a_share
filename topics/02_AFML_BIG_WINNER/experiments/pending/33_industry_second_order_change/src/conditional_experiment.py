"""R03 contemporaneous feature-only residualization and fixed policy contrasts."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from price_experiment import EP, digest


def interval(s, width):
    # Preserve calendar gaps; sample 6/12-month blocks, not compressed observed months.
    if s.empty:
        return [None, None]
    a=s.reindex(pd.period_range(s.index.min(),s.index.max(),freq='M')).to_numpy(float)
    rng=np.random.default_rng(33)
    starts=rng.integers(0,len(a),size=(2000,int(np.ceil(len(a)/width))))
    ix=(starts[...,None]+np.arange(width))%len(a)
    with np.errstate(invalid='ignore'):
        means=np.nanmean(a[ix.reshape(2000,-1)[:,:len(a)]],axis=1)
    return np.nanquantile(means,[.025,.975]).tolist()


def main():
    panel=pd.read_parquet('/tmp/ep33_r01_panel.parquet')
    out=EP/'outputs/r03';out.mkdir(parents=True,exist_ok=True)
    selections=[]; coverage=[]; rows=[]
    for date,g in panel.groupby('date',sort=True):
        base=g[g.coverage.ge(.8)&g.members.ge(5)].dropna(subset=['velocity','acceleration','prior63','vol63']).copy()
        for kind,pool in [('decelerating_decline',base[base.velocity.lt(0)&base.acceleration.gt(0)]),('accelerating_improvement',base[base.velocity.ge(0)&base.acceleration.gt(0)])]:
            pool=pool.copy(); n=len(pool)
            if n<20:
                coverage.append(dict(date=date,pool=kind,pool_n=n,joint_n=0,reason='less_than_20_for_controls'));continue
            x=pool[['velocity','prior63','vol63']].to_numpy();x=(x-x.mean(0))/np.where(x.std(0)>0,x.std(0),1)
            x=np.column_stack([np.ones(n),x]);y=pool.acceleration.to_numpy()
            pool['residual']=y-x@np.linalg.lstsq(x,y,rcond=None)[0]
            joint=pool[pool.persistence.ge(.8)&pool.breadth_change.gt(0)&pool.breadth_acceleration.gt(0)]
            coverage.append(dict(date=date,pool=kind,pool_n=n,joint_n=len(joint),reason='eligible'))
            arms={a:pool.sort_values([a,'industry_code'],ascending=[False,True]).head(10) for a in ['velocity','acceleration','residual']}
            for score in ['velocity','acceleration']:
                arms['joint_'+score]=joint.sort_values([score,'industry_code'],ascending=[False,True]).head(10)
            for arm,s in arms.items():
                s=s.copy();s['pool']=kind;s['strategy']=arm;s['rank']=np.arange(1,len(s)+1);selections.append(s)
            for a,b in [('residual','velocity'),('acceleration','velocity'),('joint_velocity','velocity'),('joint_acceleration','velocity'),('joint_acceleration','joint_velocity')]:
                k=min(len(arms[a]),len(arms[b]));ga=arms[a].head(k);gb=arms[b].head(k)
                if not k:continue
                knowna=ga.excess126.notna();knownb=gb.excess126.notna()
                rows.append(dict(date=date,pool=kind,treatment=a,control=b,k=k,
                    complete=bool(knowna.all()&knownb.all()),known_treatment=int(knowna.sum()),known_control=int(knownb.sum()),
                    excess_treatment=ga.excess126.mean(),excess_control=gb.excess126.mean(),
                    delta=ga.excess126.mean()-gb.excess126.mean(),
                    adverse_delta=ga.adverse126.mean()-gb.adverse126.mean(),
                    overlap=len(set(ga.industry_code)&set(gb.industry_code))/k))
    selected=pd.concat(selections,ignore_index=True);selected.to_csv(out/'selected.csv.gz',index=False)
    coverage=pd.DataFrame(coverage);coverage.to_csv(out/'coverage.csv',index=False)
    metrics=pd.DataFrame(rows);metrics.to_csv(out/'date_pairs.csv',index=False)
    summary=[];annual=[]
    for keys,g in metrics.groupby(['pool','treatment','control']):
        c=g[g.complete].set_index('date');monthly=c.delta.groupby(c.index.to_period('M')).mean()
        ci6=interval(monthly,6);ci12=interval(monthly,12)
        summary.append(dict(zip(['pool','treatment','control'],keys))|dict(dates=len(g),complete_dates=len(c),months=len(monthly),
            delta_complete=monthly.mean(),delta_available=g.delta.mean(),ci6_low=ci6[0],ci6_high=ci6[1],ci12_low=ci12[0],ci12_high=ci12[1],
            unknown_treatment=1-g.known_treatment.sum()/g.k.sum(),unknown_control=1-g.known_control.sum()/g.k.sum(),
            mean_k=g.k.mean(),mean_overlap=g.overlap.mean(),adverse_delta=c.adverse_delta.mean()))
        for year,z in c.groupby(c.index.year):
            annual.append(dict(zip(['pool','treatment','control'],keys))|dict(year=year,dates=len(z),delta=z.delta.mean()))
    pd.DataFrame(summary).to_csv(out/'summary.csv',index=False);pd.DataFrame(annual).to_csv(out/'annual.csv',index=False)
    (out/'receipt.json').write_text(json.dumps({'round':'r03','uses_future_in_residualization':False,
        'inputs':{str(p):digest(p) for p in [Path('/tmp/ep33_r01_panel.parquet'),EP/'rounds/r03_plan.md',Path(__file__)]}},indent=2)+'\n')
    print(pd.DataFrame(summary).to_string(index=False))

if __name__=='__main__':main()
