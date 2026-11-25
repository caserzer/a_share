from inputs import *
from concurrent.futures import ProcessPoolExecutor
import multiprocessing
sys.path.append(str(PRIVATE.parent/'src'))
from features import compute
C69=[c for c in COLS if not c.startswith('market_')]
def build():
    fields='qfq_close qfq_open qfq_high qfq_low volume money turnover_rate'.split()
    data=[pd.read_parquet(LOCAL/(f+'.parquet')) for f in fields]
    c=data[0];days=c.index
    mem=membership(days,c.columns)
    member300=pd.read_parquet(PRIVATE/'daily_members.parquet')
    market=pd.read_parquet(PRIVATE/'market.parquet').close
    returns=c[member300.columns].pct_change(fill_method=None).where(member300)
    mu=returns.mean(axis=1);sd=returns.std(axis=1,ddof=0).where(returns.count(axis=1)>=100)
    first=days.get_loc('2021-01-11')-1;last=days.get_loc('2026-10-12')-11
    boards=[]
    for offset in range(0,len(c.columns),120):
        names=c.columns[offset:offset+120]
        close=c[names]
        m300=member300.reindex(columns=names,fill_value=False)
        ff=compute(*[f[names] for f in data],m300,market)
        eligible=mem[names] & close.gt(0).rolling(61).sum().eq(61) & (close.shift(5)/close.shift(60)).ne(1) & (close/close.shift(5)).ne(1)
        i,j=np.where(eligible.iloc[first:last+1]);i+=first
        xs=close.pct_change(fill_method=None).sub(mu,axis=0).div(sd,axis=0)
        vals={}
        for k in COLS:
            if k.startswith('xsret_lag'):
                lag=int(k[9:]);v=xs.shift(lag).to_numpy()[i,j]
                v[m300.to_numpy()[i,j]&~m300.shift(lag,fill_value=False).to_numpy()[i,j]]=np.nan
            else:v=ff[k].to_numpy()[i,j]
            vals[k]=v
        g=pd.DataFrame(vals);ok=g.notna().mean(axis=1)>=.8
        boards.append(g.assign(signal_date=days[i],entry_idx=i+1,instrument=names[j]).loc[ok])
    return pd.concat(boards,ignore_index=True).sort_values(KEY)

def tree(d):
    med=d[C69].median().fillna(0)
    y=d.target_rank.to_numpy()
    ds=lgb.Dataset(d[C69].fillna(med),label=y,free_raw_data=False)
    warm=lgb.train(dict(PARAMS,objective='regression'),ds,num_boost_round=20)
    def grad(p,_):return 2*(p-y),np.full(len(p),2.)
    return lgb.train(dict(PARAMS,objective=grad),ds,num_boost_round=60,init_model=warm),med

def fit(q):
    q=str(q);cut=pd.Period(q).start_time
    t=NARROW[NARROW.h10_mature<cut];wide=WIDE[WIDE.exit_idx<DAYS.searchsorted(cut)].copy()
    wide['target_rank']=wide.groupby('signal_date').h10.transform(lambda x:x.rank()/(len(x)+1)-.5)
    g=TEST[TEST.signal_date.dt.to_period('Q').astype(str)==q]
    s=g[KEY+['entry_idx']].copy()
    metadata=[]
    for name,d in [('transfer',t),('refit',wide)]:
        r=(json.loads((LINEAR/'models'/(q+'.json')).read_text())['baseline'] if name=='transfer' else ridge(d,COLS,'target_rank'))
        model,med=tree(d)
        folder=OUT800/'models'/name/q;folder.mkdir(parents=True,exist_ok=True)
        model.save_model(str(folder/'tree.txt'));(folder/'ridge.json').write_text(json.dumps(r))
        med.to_json(folder/'medians.json',double_precision=15)
        s[name+'_R']=predict(g[COLS],r);s[name+'_T']=model.predict(g[C69].fillna(med),num_threads=2)
        latest=t.h10_mature.max() if name=='transfer' else DAYS[wide.exit_idx.max()]
        assert latest<cut
        metadata.append(dict(mode=name,fold=q,rows=len(d),train_dates=d.signal_date.nunique(),latest_maturity=latest,first_signal=g.signal_date.min()))
    return s,metadata
if __name__=='__main__':
    DAYS=pd.read_parquet(PRIVATE/'market.parquet',columns=[]).index
    TEST=build()
    print('daily features',len(TEST),flush=True)
    NARROW=prepare().sort_values(KEY)
    weeks=pd.read_parquet(PRIVATE/'features.parquet',columns=['signal_date']).signal_date.unique()
    wide=pd.read_parquet(LOCAL/'wide_features.parquet')
    expected=wide[wide.outer_ok & wide.signal_date.isin(TEST.signal_date.unique())].set_index(KEY).sort_index()
    actual=TEST[TEST.signal_date.isin(expected.index.get_level_values(0))].set_index(KEY).sort_index()
    pd.testing.assert_index_equal(expected.index,actual.index)
    np.testing.assert_allclose(expected[COLS],actual[COLS],atol=1e-12,rtol=0,equal_nan=True)
    WIDE=wide[wide.weekly_ok & wide.signal_date.isin(weeks)&wide.h10.notna()].sort_values(KEY)
    del expected,actual,wide
    with ProcessPoolExecutor(3,mp_context=multiprocessing.get_context('fork')) as ex:
        fits=list(ex.map(fit,sorted(TEST.signal_date.dt.to_period('Q').unique())))
    s=pd.concat([x for x,_ in fits])
    ref=pd.concat([pd.read_parquet(f,columns=KEY+['T69']) for f in (DEST/'folds').glob('*.parquet')])
    match=s.merge(ref,on=KEY,validate='1:1');assert len(match)==40700
    np.testing.assert_allclose(match.transfer_T,match.T69,rtol=0,atol=1e-10)
    r=pd.read_parquet(STORE/'wide_scores.parquet')
    match=s.merge(r,on=KEY,validate='1:1');assert len(match)==len(r)
    for a,b in [('transfer_R','transfer'),('refit_R','wide_train')]:
        np.testing.assert_allclose(match[a],match[b],rtol=0,atol=1e-10)
    pd.DataFrame([row for _,m in fits for row in m]).to_csv(OUT800/'folds.csv',index=False)
    s.to_parquet(OUT800/'scores.parquet',index=False)
