"""Rebuild the eligible daily universe and the vintage-specific 2019–20 inner predictions."""
from pathlib import Path
import sys
import hashlib
import json
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

HERE = Path(__file__).resolve().parent
EP42 = HERE.parent
PENDING = EP42.parent
EP41 = next(PENDING.glob('41_*'))
EP40 = next(PENDING.glob('40_*'))
PRIVATE = next(PENDING.glob('36_*/private'))
OUT = HERE / 'results'
CACHE = Path('/tmp/ep42_regime_r1_inputs')
CACHE.mkdir(exist_ok=True)
OUT.mkdir(exist_ok=True)
sys.path.insert(0,str(EP40/'lightgbm/followup'))
import common_inputs as ci
sys.path.append(str(PRIVATE.parent/'src'))
from features import compute

def pct_history(series):
    values=series.to_numpy()
    result=np.full(len(values),np.nan)
    for i in range(252,len(values)):
        window=values[i-252:i]
        if np.isfinite(values[i]) and np.isfinite(window).all():
            result[i]=((window<values[i]).sum()+0.5*(window==values[i]).sum())/252
    return pd.Series(result,index=series.index)

def get_index():
    raw=json.loads((PRIVATE/'net_excess_20261116/H00300.CSI.json').read_text())['data']
    idx=pd.DataFrame(raw['items'],columns=raw['fields']).set_index('trade_date').close
    idx.index=pd.to_datetime(idx.index)
    extra=OUT/'index_history.csv'
    if extra.exists():
        older=pd.read_csv(extra,parse_dates=['date']).set_index('date').close
        common=idx.index.intersection(older.index)
        np.testing.assert_allclose(idx.loc[common],older.loc[common],rtol=1e-6)
        idx=idx.combine_first(older)
    return idx.sort_index()

def make_inputs():
    names='qfq_close qfq_open qfq_high qfq_low volume money turnover_rate daily_members'.split()
    raw=[pd.read_parquet(PRIVATE/(x+'.parquet')).loc[:'2026-10-12'] for x in names]
    close=raw[0];member=raw[-1];dates=close.index
    market=pd.read_parquet(PRIVATE/'market.parquet').close.reindex(dates)
    ret=close.pct_change(fill_method=None)
    valid_r=ret.where(member)
    xs=valid_r.sub(valid_r.mean(axis=1),axis=0).div(valid_r.std(axis=1,ddof=0).where(valid_r.count(axis=1)>=100),axis=0)
    eligible=member & (close.gt(0)&np.isfinite(close)).rolling(61).sum().eq(61)&(close.shift(5)/close.shift(60)).ne(1)&(close/close.shift(5)).ne(1)
    core=ci.COLS
    for block in range(0,len(close.columns),100):
        stocks=close.columns[block:block+100]
        mats=compute(*[x[stocks] for x in raw],market)
        daily_xs=xs[stocks]
        for k in range(20):
            mats[f'xsret_lag{k}']=daily_xs.shift(k)
        i,j=np.where(eligible[stocks])
        board=pd.DataFrame({c:mats[c].to_numpy()[i,j] for c in core})
        keep=board.notna().sum(axis=1)>=0.8*len(core)
        eligible.values[i[~keep],j[~keep]+block]=False
        board=board.loc[keep].assign(signal_date=dates[i[keep]],instrument=stocks[j[keep]],entry_idx=i[keep]+1)
        board.to_parquet(CACHE/f'block_{block:04}.parquet',index=False)
    # Build the eligibility mask from the written keys (independent of Pandas Copy-on-Write).
    flags=np.zeros(close.shape,dtype=bool)
    for f in sorted(CACHE.glob('block_*.parquet')):
        k=pd.read_parquet(f,columns=['entry_idx','instrument'])
        flags[k.entry_idx.to_numpy()-1,close.columns.get_indexer(k.instrument)]=True
    mask=pd.DataFrame(flags,index=dates,columns=close.columns)
    eligible_r=ret.where(mask)
    obs=eligible_r.count(axis=1)
    iqr=(eligible_r.quantile(.75,axis=1)-eligible_r.quantile(.25,axis=1)).where(obs>=100)
    v=raw[5]/raw[5].shift(1).rolling(60).mean()
    v=v.where(mask).replace([np.inf,-np.inf],np.nan)
    idx=get_index().reindex(dates)
    s=pd.DataFrame({'eligible':mask.sum(axis=1),'return_count':obs,'value_count':v.count(axis=1),'iqr':iqr,
                    'Z1_raw':iqr.rolling(20).mean(),'Z2_raw':v.median(axis=1).where(v.count(axis=1)>=100).rolling(5).mean(),
                    'Z3_raw':idx/idx.shift(60)-1,'Z4_raw':idx/idx.rolling(60).max()-1},index=dates)
    for z in ['Z1','Z2','Z3','Z4']:
        s[z]=pct_history(s[z+'_raw'])
    s['reference_start']=dates.to_series().shift(252)
    s['reference_end']=dates.to_series().shift(1)
    s['known_at_close']=dates
    s.index.name='signal_date'
    s.reset_index().to_parquet(OUT/'states.parquet',index=False)
    mask.to_parquet(CACHE/'eligible.parquet')
    observed=pd.read_parquet(EP41/'p2/results/scores.parquet',columns=['entry_idx','instrument'])
    for e,g in observed.groupby('entry_idx'):
        np.testing.assert_array_equal(np.sort(close.columns[flags[e-1]]),np.sort(g.instrument))
    audits=[]
    for z in ['Z1','Z2','Z3','Z4']:
        cuts=((s[z]<1/3).astype(int)-(s[z]>2/3).astype(int)).diff().ne(0)
        subset=s.index[(cuts | (np.arange(len(s))%53==0)) & s[z].notna()]
        errors=[]
        for t in subset:
            h=s.loc[:t,z+'_raw'].iloc[-253:-1]
            errors.append(abs((h.lt(s.at[t,z+'_raw']).sum()+.5*h.eq(s.at[t,z+'_raw']).sum())/252-s.at[t,z]))
        audits.append(dict(state=z,dates=len(subset),max_error=max(errors,default=0),available=int(s[z].notna().sum()),first=s[z].first_valid_index()))
    pd.DataFrame(audits).to_csv(OUT/'state_audit.csv',index=False)
    print('state complete',len(s),flush=True)

def make_scores():
    files=sorted(CACHE.glob('block_*.parquet'))
    bounds=(pd.Timestamp('2019-01-01'),pd.Timestamp('2021-01-08'))
    early=pd.concat([pd.read_parquet(f,filters=[('signal_date','>=',bounds[0]),('signal_date','<',bounds[1])]) for f in files]).sort_values(ci.KEY)
    source=ci.prepare().sort_values(ci.KEY)
    stocks=[k for k in ci.COLS if not k.startswith('market_')]
    rows=[];audits=[]
    for q,g in early.groupby(early.signal_date.dt.to_period('Q')):
        fit=source[source.h10_mature<q.start_time]
        r=ci.ridge(fit,ci.COLS,'target_rank')
        x=fit[stocks];med=x.median().fillna(0);y=fit.target_rank.to_numpy()
        ds=ci.lgb.Dataset(x.fillna(med),label=y,free_raw_data=False)
        params=dict(ci.PARAMS,num_threads=2)
        warm=ci.lgb.train(dict(params,objective='regression'),ds,num_boost_round=20)
        def grad(pred,data): return 2*(pred-y),np.full(len(pred),2.)
        model=ci.lgb.train(dict(params,objective=grad),ds,num_boost_round=60,init_model=warm)
        rows.append(g[ci.KEY+['entry_idx']].assign(R=ci.predict(g[ci.COLS],r),T=model.predict(g[stocks].fillna(med),num_threads=2)))
        audits.append(dict(quarter=str(q),train_rows=len(fit),last_maturity=fit.h10_mature.max(),test_first=g.signal_date.min(),test_last=g.signal_date.max()))
    scores=pd.concat([*rows,pd.read_parquet(EP41/'p2/results/scores.parquet')]).sort_values(ci.KEY)
    assert not scores.duplicated(ci.KEY).any()
    scores.to_parquet(OUT/'scores.parquet',index=False)
    pd.DataFrame(audits).to_csv(OUT/'inner_score_folds.csv',index=False)
    print('scores',len(scores),flush=True)

if __name__=='__main__':
    make_inputs()
    make_scores()

