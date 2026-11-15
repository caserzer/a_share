from common import *
import pandas as pd
from itertools import combinations

def run():
    out=ROOT/'outputs/r292';z=np.load(ROOT/'outputs/r291/normalized_paths.npz');stock=z['stock'];market=z['market'];keys=pd.read_parquet(ROOT/'outputs/r291/path_keys.parquet');a=pd.read_parquet(ROOT/'outputs/r287/alerts.parquet')
    d=pd.read_parquet(out/'date_metrics.parquet');ledger=pd.read_csv(out/'sampling_ledger.csv',dtype={'seed':str},parse_dates=['date']);keysby={k:g.sort_values('industry_code') for k,g in keys.groupby(['era','level','date'])};actual={k:g for k,g in d.groupby(['era','level','date'])};alerts={k:set(g.industry_code) for k,g in a[a.strategy.eq('daily')].groupby(['era','level','date','variant'])}
    checks=0
    for r in ledger.itertuples():
        key=(r.era,r.level,r.date);g=keysby[key];assert len(g)==r.n and r.k==(r.n+4)//5 and r.draws==1024
        seed=int.from_bytes(hashlib.sha256(f'R292|{r.era}|{r.level}|{r.date:%Y-%m-%d}'.encode()).digest()[:8],'big');assert seed==int(r.seed)
        numbers=np.random.Generator(np.random.PCG64(seed)).random((1024,r.n));selected=np.argsort(numbers,axis=1)[:,:r.k]
        assert hashlib.sha256(np.sort(selected,axis=1).astype('<i4').tobytes()).hexdigest()==r.selection_sha256
        x=stock[g.path_id,1:];b=market[g.path_id,1:];assert np.allclose(b,b[0])
        # Explicit sum of selected industry paths instead of the producer's selection matrix product.
        removed=x[selected].sum(axis=1);total=x.sum(axis=0)
        for (cost,policy),rows in actual[key].groupby(['cost','policy']):
            alt=np.full(20,1-cost) if policy=='cash' else (1-cost)*(1-cost)*b[0]*(1-cost)
            hold=(1-cost)*total/r.n;random=((1-cost)*(total-removed)+r.k*alt)/r.n
            short=np.clip(1-random,0,None);rw=np.max(short,axis=1);rm=np.sum(short,axis=1)/20
            jp=np.clip(1-np.sum(random,axis=0)/1024,0,None);hl=np.clip(1-hold,0,None)
            for row in rows.itertuples():
                mask=g.industry_code.isin(alerts[key+(row.variant,)]).to_numpy();assert mask.sum()==r.k
                positions=(1-cost)*x.copy();positions[mask]=alt;wealth=positions.sum(axis=0)/r.n
                got=np.array([getattr(row,f'w{i}') for i in range(1,21)]);assert np.allclose(wealth,got,atol=1e-12)
                loss=np.clip(1-wealth,0,None)
                for f,value in [('hold_worst',hl.max()),('hold_mean',hl.mean()),('model_worst',loss.max()),('model_mean',loss.mean()),('random_worst',rw.mean()),('random_mean',rm.mean()),('random_worst_mc_variance',rw.var(ddof=1)/1024),('random_mean_mc_variance',rm.var(ddof=1)/1024),('jensen_worst',rw.mean()-jp.max()),('jensen_mean',rm.mean()-jp.mean()),('terminal_gain',wealth[-1]-hold[-1])]:assert np.isclose(value,getattr(row,f),atol=1e-12,rtol=0),(f,key)
                checks+=1
    assert checks==len(d)
    old=pd.read_parquet(ROOT/'outputs/r290/date_metrics.parquet')
    for policy in ['cash','market']:
        v=d[d.policy.eq(policy)].merge(old,on=['era','level','date','strategy','variant','cost'],validate='one_to_one');assert len(v)==old.complete_date.sum() and v.complete_date.all()
        assert np.allclose(v.terminal_gain,v[policy+'_selected_known_conditional'])
    summary=pd.read_csv(out/'summary.csv')
    for row in summary.itertuples():
        g=d
        for k in ['era','level','strategy','variant','cost','policy']:g=g[g[k].eq(getattr(row,k))]
        assert len(g)==row.dates
        for metric in ['worst','mean']:
            assert np.isclose((g['hold_'+metric]-g['model_'+metric]).mean(),getattr(row,metric+'_relief_vs_hold'))
            assert np.isclose((g['random_'+metric]-g['model_'+metric]).mean(),getattr(row,metric+'_relief_vs_random'))
            assert np.isclose(np.sqrt(g['random_'+metric+'_mc_variance'].sum())/len(g),getattr(row,metric+'_random_mc_se'))
    # All fixed-size choices in a crossed-path fixture: E[risk] differs from risk(E[path]).
    fixture=np.array([[.5,1.5],[1.5,.5],[1.,1.]])
    portfolios=[]
    for chosen in combinations(range(3),1):
        positions=fixture.copy();positions[list(chosen)]=1.;portfolios.append(positions.mean(axis=0))
    portfolios=np.array(portfolios);meanrisk=np.maximum(1-portfolios,0).max(axis=1).mean();riskmean=np.maximum(1-portfolios.mean(axis=0),0).max()
    assert np.isclose(meanrisk,1/9) and np.isclose(riskmean,0)
    rec=json.loads((out/'receipt.json').read_text())
    for p,h in rec['inputs'].items():assert sha(ROOT/p)==h
    for p,h in rec['outputs'].items():assert sha(out/p)==h
    js(out/'independent_verification.json',dict(status='PASS',sampling_origins=len(ledger),draws=len(ledger)*1024,portfolio_rows=checks,summary_groups=len(summary),enumerated_fixture_choices=3,verifier_sha256=sha(Path(__file__)),scope='Sorted selection reconstruction, explicit position aggregation, nonlinear risk and MC arithmetic; no historical statistical or execution certification'))
    print('R292 VERIFIED',len(ledger)*1024,checks,len(summary))
if __name__=='__main__':run()
