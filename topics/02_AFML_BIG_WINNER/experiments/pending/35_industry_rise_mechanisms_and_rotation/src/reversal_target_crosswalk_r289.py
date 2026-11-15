from common import *
import pandas as pd
from itertools import product

def classify(g):
    g=g.copy();g['label_class']=np.where(g.y.isna(),'unknown',np.where(g.y.eq(1),'1','0'))
    g['event_class']=np.where(~g.complete_path,'unknown',np.where(g.episode_id.notna(),'1','0'));return g

def run():
    out=ROOT/'outputs/r289';out.mkdir(exist_ok=True)
    o=classify(pd.read_parquet(ROOT/'outputs/r287/origins.parquet'));a=classify(pd.read_parquet(ROOT/'outputs/r287/alerts.parquet'))
    o['n']=o.groupby(['era','level','date']).date.transform('size');o['p']=np.ceil(o.n/5)/o.n
    cal=pd.DatetimeIndex(pd.read_parquet(CACHE/'forecast_v5/CSI_ALL.parquet').index);ends=pd.Series(cal,index=cal).groupby(cal.to_period('M')).max();ends=ends[[p.end_time.normalize()<=cal.max() for p in ends.index]]
    cells=[];metrics=[]
    def collect(g,era,level,strategy,policy,weights):
        weights=pd.Series(np.asarray(weights),index=g.index)
        for label,event in product(['0','1','unknown'],repeat=2):cells.append(dict(era=era,level=level,strategy=strategy,policy=policy,label=label,event=event,count=float(weights[g.label_class.eq(label)&g.event_class.eq(event)].sum())))
        known=float(weights[g.y.notna()].sum());positive=float(weights[g.y.eq(1)].sum());complete=float(weights[g.complete_path].sum());complete_pos=float(weights[g.complete_path&g.y.eq(1)].sum())
        metrics.append(dict(era=era,level=level,strategy=strategy,policy=policy,count=float(weights.sum()),known_label=known,positive_label=positive,unknown_label=float(weights[g.y.isna()].sum()),unknown_event=float(weights[~g.complete_path].sum()),label_rate=positive/known if known else np.nan,complete_label_rate=complete_pos/complete if complete else np.nan,interpretation='ratio_of_expected_counts' if policy=='random' else 'observed_count_ratio'))
    for (era,level),whole in o.groupby(['era','level']):
        for strategy,g in [('daily',whole),('monthly',whole[whole.date.isin(ends.values)])]:
            collect(g,era,level,strategy,'population',np.ones(len(g)));collect(g,era,level,strategy,'random',g.p)
            for variant in ['base','state','interaction']:
                q=a[a.era.eq(era)&a.level.eq(level)&a.strategy.eq(strategy)&a.variant.eq(variant)];collect(q,era,level,strategy,variant,np.ones(len(q)))
    c=pd.DataFrame(cells);m=pd.DataFrame(metrics);c.to_csv(out/'cells.csv',index=False);m.to_csv(out/'metrics.csv',index=False)
    ref=m[m.policy.eq('random')];cmp=m[m.policy.isin(['base','state','interaction'])].merge(ref,on=['era','level','strategy'],suffixes=('','_random'),validate='many_to_one');assert np.allclose(cmp['count'],cmp.count_random)
    cmp['label_rate_minus_random']=cmp.label_rate-cmp.label_rate_random;cmp['complete_label_rate_minus_random']=cmp.complete_label_rate-cmp.complete_label_rate_random;cmp.to_csv(out/'comparisons.csv',index=False)
    summary=dict(status='PASS',groups=len(m),cells=len(c),comparisons=len(cmp),label_rate_above_random=int(cmp.label_rate_minus_random.gt(0).sum()),label_rate_below_random=int(cmp.label_rate_minus_random.lt(0).sum()),adoption=False,no_refit=True)
    js(out/'summary.json',summary);reads=json.loads((ROOT/'protocols/r289.json').read_text())['inputs']+['protocols/r289.json','src/reversal_target_crosswalk_r289.py']
    js(out/'receipt.json',dict(inputs={p:sha(ROOT/p) for p in reads},benchmark_sha256=sha(CACHE/'forecast_v5/CSI_ALL.parquet'),outputs={p.name:sha(p) for p in out.iterdir() if p.name!='receipt.json'}));print(summary);print(cmp[['era','level','strategy','policy','label_rate','label_rate_random','label_rate_minus_random']].to_string(index=False))
if __name__=='__main__':run()
