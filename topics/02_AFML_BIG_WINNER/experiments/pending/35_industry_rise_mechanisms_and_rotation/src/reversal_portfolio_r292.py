from common import *
import pandas as pd

def run():
    out=ROOT/'outputs/r292';out.mkdir(exist_ok=True)
    paths=np.load(ROOT/'outputs/r291/normalized_paths.npz');keys=pd.read_parquet(ROOT/'outputs/r291/path_keys.parquet');o=pd.read_parquet(ROOT/'outputs/r287/origins.parquet');a=pd.read_parquet(ROOT/'outputs/r287/alerts.parquet');old=pd.read_parquet(ROOT/'outputs/r290/date_metrics.parquet')
    complete=old[old.strategy.eq('daily')&old.variant.eq('base')&old.cost.eq(0)&old.complete_date][['era','level','date']]
    d=o.merge(complete,on=['era','level','date'],validate='many_to_one').merge(keys[KEY+['date','path_id']],on=KEY+['date'],validate='one_to_one')
    monthly=set(map(tuple,old[old.strategy.eq('monthly')&old.complete_date][['era','level','date']].to_numpy()))
    selections={k:set(g.industry_code) for k,g in a[a.strategy.eq('daily')].groupby(['era','level','date','variant'])}
    rows=[];ledger=[]
    for (era,level,date),g in d.groupby(['era','level','date']):
        g=g.sort_values('industry_code');n=len(g);k=(n+4)//5;x=paths['stock'][g.path_id,1:];b=paths['market'][g.path_id,1:];assert np.allclose(b,b[0])
        seed=int.from_bytes(hashlib.sha256(f'R292|{era}|{level}|{date:%Y-%m-%d}'.encode()).digest()[:8],'big');rng=np.random.Generator(np.random.PCG64(seed));u=rng.random((1024,n));idx=np.argpartition(u,k-1,axis=1)[:,:k]
        chosen=np.zeros((1024,n));np.put_along_axis(chosen,idx,1,axis=1);assert np.all(chosen.sum(axis=1)==k)
        random_left=(x.sum(axis=0)-chosen@x)/n
        ledger.append(dict(era=era,level=level,date=date,seed=str(seed),n=n,k=k,draws=1024,selection_sha256=hashlib.sha256(np.sort(idx,axis=1).astype('<i4').tobytes()).hexdigest()))
        for c in [0,.002,.005]:
            hold=(1-c)*x.mean(axis=0);hl=np.maximum(1-hold,0)
            for policy,alt in [('cash',np.full(20,1-c)),('market',(1-c)**3*b[0])]:
                random=(1-c)*random_left+(k/n)*alt;loss=np.maximum(1-random,0);worst=loss.max(axis=1);mean=loss.mean(axis=1);meanpath=np.maximum(1-random.mean(axis=0),0)
                assert worst.mean()+1e-12>=meanpath.max() and mean.mean()+1e-12>=meanpath.mean()
                for variant in ['base','state','interaction']:
                    mask=g.industry_code.isin(selections[(era,level,date,variant)]).to_numpy();assert mask.sum()==k
                    wealth=(1-c)*x[~mask].sum(axis=0)/n+(k/n)*alt;l=np.maximum(1-wealth,0)
                    for strategy in ['daily']+(['monthly'] if (era,level,date) in monthly else []):
                        rows.append(dict(era=era,level=level,date=date,strategy=strategy,variant=variant,cost=c,policy=policy,hold_worst=float(hl.max()),hold_mean=float(hl.mean()),model_worst=float(l.max()),model_mean=float(l.mean()),random_worst=float(worst.mean()),random_mean=float(mean.mean()),random_worst_mc_variance=float(worst.var(ddof=1)/1024),random_mean_mc_variance=float(mean.var(ddof=1)/1024),jensen_worst=float(worst.mean()-meanpath.max()),jensen_mean=float(mean.mean()-meanpath.mean()),terminal_gain=float(wealth[-1]-hold[-1]),**{f'w{i+1}':float(v) for i,v in enumerate(wealth)}))
    dates=pd.DataFrame(rows);dates.to_parquet(out/'date_metrics.parquet',index=False);pd.DataFrame(ledger).to_csv(out/'sampling_ledger.csv',index=False)
    for policy in ['cash','market']:
        q=dates[dates.policy.eq(policy)].merge(old,on=['era','level','date','strategy','variant','cost'],validate='one_to_one');assert q.complete_date.all() and len(q)==old.complete_date.sum();assert np.allclose(q.terminal_gain,q[policy+'_selected_known_conditional'],atol=1e-12)
    summaries=[]
    for key,g in dates.groupby(['era','level','strategy','variant','cost','policy']):
        r=dict(zip(['era','level','strategy','variant','cost','policy'],key),dates=len(g))
        for metric in ['worst','mean']:
            r[metric+'_relief_vs_hold']=float((g['hold_'+metric]-g['model_'+metric]).mean());r[metric+'_relief_vs_random']=float((g['random_'+metric]-g['model_'+metric]).mean());r[metric+'_random_mc_se']=float(np.sqrt(g['random_'+metric+'_mc_variance'].sum())/len(g));r[metric+'_jensen_gap']=float(g['jensen_'+metric].mean())
        r['terminal_gain']=g.terminal_gain.mean();summaries.append(r)
    summary=pd.DataFrame(summaries);summary.to_csv(out/'summary.csv',index=False)
    result=dict(status='PASS',origin_dates=len(ledger),draws_per_date=1024,draws_total=len(ledger)*1024,groups=len(summary),worst_better_hold=int(summary.worst_relief_vs_hold.gt(0).sum()),worst_better_random_point_estimate=int(summary.worst_relief_vs_random.gt(0).sum()),mean_better_random_point_estimate=int(summary.mean_relief_vs_random.gt(0).sum()),max_mc_standard_error=float(summary.worst_random_mc_se.max()),adoption=False)
    js(out/'result.json',result);reads=json.loads((ROOT/'protocols/r292.json').read_text())['inputs']+['protocols/r292.json','src/reversal_portfolio_r292.py'];js(out/'receipt.json',dict(inputs={p:sha(ROOT/p) for p in reads},outputs={p.name:sha(p) for p in out.iterdir() if p.name!='receipt.json'}));print(result)
if __name__=='__main__':run()
