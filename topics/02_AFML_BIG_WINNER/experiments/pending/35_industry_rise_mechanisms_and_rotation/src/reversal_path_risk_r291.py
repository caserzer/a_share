from common import *
import pandas as pd

def run():
    out=ROOT/'outputs/r291';out.mkdir(exist_ok=True)
    o=pd.read_parquet(ROOT/'outputs/r287/origins.parquet');o['n']=o.groupby(['era','level','date']).date.transform('size');o['p']=np.ceil(o.n/5)/o.n
    v=o[o.complete_path].copy().reset_index(drop=True);v['path_id']=np.arange(len(v))
    raw=pd.read_parquet(ROOT/'outputs/r129/daily_2026-10-21.parquet').set_index(KEY+['date']).nav;b=pd.read_parquet(CACHE/'forecast_v5/CSI_ALL.parquet').close;cal=pd.DatetimeIndex(b.index)
    nav=[];market=[]
    for step in range(21):
        dates=cal[v.day_i.to_numpy()+1+step];index=v[KEY].copy();index['date']=dates
        nav.append(raw.reindex(pd.MultiIndex.from_frame(index)).to_numpy());market.append(b.reindex(dates).to_numpy())
    nav=np.array(nav).T;market=np.array(market).T;assert np.isfinite(nav).all() and np.isfinite(market).all()
    stock=nav/nav[:,0,None];bench=market/market[:,0,None]
    assert np.allclose(stock[:,-1]-1,v.return20) and np.allclose(bench[:,-1]-1,v.market_return20)
    np.savez_compressed(out/'normalized_paths.npz',stock=stock,market=bench)
    v[KEY+['date','day_i','path_id']].to_parquet(out/'path_keys.parquet',index=False)
    primitives=[]
    for c in [0,.002,.005]:
        hold=(1-c)*stock[:,1:];holdloss=np.maximum(1-hold,0)
        for policy,replacement in [('cash',np.full_like(hold,1-c)),('market',(1-c)**3*bench[:,1:])]:
            loss=np.maximum(1-replacement,0);gain=replacement[:,-1]-hold[:,-1]
            p=v[KEY+['date','path_id']].copy();p['cost']=c;p['policy']=policy
            p['worst_relief']=holdloss.max(axis=1)-loss.max(axis=1);p['mean_relief']=holdloss.mean(axis=1)-loss.mean(axis=1)
            p['missed_positive']=np.maximum(-gain,0);p['avoided_negative']=np.maximum(gain,0);primitives.append(p)
    primitive=pd.concat(primitives,ignore_index=True);primitive.to_parquet(out/'primitive_risks.parquet',index=False)
    a=pd.read_parquet(ROOT/'outputs/r287/alerts.parquet');old=pd.read_parquet(ROOT/'outputs/r290/date_metrics.parquet');parts=[]
    for (strategy,variant,c),calendar in old.groupby(['strategy','variant','cost']):
        dates=calendar[['era','level','date','complete_date']];g=o.merge(dates,on=['era','level','date'],validate='many_to_one');g=g[g.complete_date]
        selected=a[a.strategy.eq(strategy)&a.variant.eq(variant)][KEY+['date']].assign(alert=True);g=g.merge(selected,on=KEY+['date'],how='left',validate='one_to_one');g['alert']=g.alert.eq(True)
        for policy in ['cash','market']:
            q=g.merge(primitive[primitive.cost.eq(c)&primitive.policy.eq(policy)][KEY+['date','worst_relief','mean_relief','missed_positive','avoided_negative']],on=KEY+['date'],validate='one_to_one')
            assert len(q)==len(g)
            for field in ['worst_relief','mean_relief','missed_positive','avoided_negative']:
                q[field+'_selected']=q[field]*q.alert;q[field+'_random']=q[field]*q.p
            cols=[x+'_'+z for x in ['worst_relief','mean_relief','missed_positive','avoided_negative'] for z in ['selected','random']]
            rows=q.groupby(['era','level','date'])[cols].mean().reset_index();rows['strategy']=strategy;rows['variant']=variant;rows['cost']=c;rows['policy']=policy;parts.append(rows)
    d=pd.concat(parts,ignore_index=True);d.to_parquet(out/'date_metrics.parquet',index=False)
    for policy in ['cash','market']:
        z=d[d.policy.eq(policy)].merge(old,on=['era','level','date','strategy','variant','cost'],validate='one_to_one')
        for kind in ['selected','random']:assert np.allclose(z['avoided_negative_'+kind]-z['missed_positive_'+kind],z[policy+'_'+kind+'_known_conditional'],atol=1e-12)
    summary=d.groupby(['era','level','strategy','variant','cost','policy']).agg(dates=('date','size'),**{c:(c,'mean') for c in cols}).reset_index()
    summary['worst_relief_vs_random']=summary.worst_relief_selected-summary.worst_relief_random;summary['mean_relief_vs_random']=summary.mean_relief_selected-summary.mean_relief_random
    summary.to_csv(out/'summary.csv',index=False)
    paired=summary[summary.variant.ne('base')].merge(summary[summary.variant.eq('base')],on=['era','level','strategy','cost','policy'],suffixes=('','_base'),validate='many_to_one')
    for field in ['worst_relief_selected','mean_relief_selected','missed_positive_selected','avoided_negative_selected']:paired[field+'_delta']=paired[field]-paired[field+'_base']
    paired.to_csv(out/'regime_comparisons.csv',index=False)
    result=dict(status='PASS',paths=len(v),path_points=len(v)*21,policy_cost_groups=len(summary),date_policy_cost_rows=len(d),worst_relief_positive=int(summary.worst_relief_selected.gt(0).sum()),worst_relief_above_random=int(summary.worst_relief_vs_random.gt(0).sum()),adoption=False,portfolio_risk_certified=False)
    js(out/'result.json',result);reads=json.loads((ROOT/'protocols/r291.json').read_text())['inputs']+['protocols/r291.json','src/reversal_path_risk_r291.py']
    js(out/'receipt.json',dict(inputs={p:sha(ROOT/p) for p in reads},benchmark_sha256=sha(CACHE/'forecast_v5/CSI_ALL.parquet'),outputs={p.name:sha(p) for p in out.iterdir() if p.name!='receipt.json'}));print(result)
if __name__=='__main__':run()
