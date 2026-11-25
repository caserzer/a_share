"""Calendar challenge of the prespecified market-column ablation and X11 using that tree."""
from accounts_followup import *
from stagger import simulate
sys.path.append(str(PRIVATE.parent/'src'))
from features import compute
def main():
    data=prepare().sort_values(KEY);scores=pd.read_parquet(DEST/'daily_scores.parquet')
    raw=[pd.read_parquet(PRIVATE/(f+'.parquet')) for f in 'qfq_close qfq_open qfq_high qfq_low volume money turnover_rate daily_members'.split()]
    ff=compute(*raw,pd.read_parquet(PRIVATE/'market.parquet').close)
    cols=[c for c in COLS if not c.startswith('market_')]
    rows=[]
    for q,g in scores.groupby(scores.signal_date.dt.to_period('Q')):
        d=data[data.h10_mature<q.start_time];med=d[cols].median().fillna(0)
        y=d.target_rank.to_numpy();ds=lgb.Dataset(d[cols].fillna(med),label=y,free_raw_data=False)
        warm=lgb.train(dict(PARAMS,objective='regression'),ds,num_boost_round=20)
        def grad(p,data):return 2*(p-y),np.full(len(p),2.)
        tree=lgb.train(dict(PARAMS,objective=grad),ds,num_boost_round=60,init_model=warm)
        ix=raw[0].index.get_indexer(g.signal_date);j=raw[0].columns.get_indexer(g.instrument)
        x=pd.DataFrame({c:ff[c].to_numpy()[ix,j] for c in cols})
        rows.append(g[KEY+['R','entry_idx']].assign(T=tree.predict(x.fillna(med),num_threads=2)))
    s=pd.concat(rows)
    f=pd.concat([pd.read_parquet(f,columns=KEY+['T69']) for f in (DEST/'folds').glob('*.parquet')])
    test=s.merge(f,on=KEY,validate='1:1')
    np.testing.assert_allclose(test['T'],test.T69,atol=1e-10,rtol=0)
    ledger.accounts.OUT=DEST
    m,actions=ledger.setup('flat');plans=defaultdict(dict);monthly=[];win=[];positions=[];days=[];orders=[]
    for e,g in s.groupby('entry_idx'):
        t=picks(g)
        for a in ['T','X11']:plans[a][e]=m.symbols.get_indexer(t[a])
    for scope,start,end in [('primary','2021-01-11','2025-03-03'),('later','2025-03-03','2026-10-12')]:
        i,j=m.days.get_indexer([start,end])
        for a,plan in plans.items():
            for ph in range(10):
                rates=[0,1,2] if ph==0 else [1]
                for rate in rates:
                    w,d,p,o=replay(m,actions,{e:plan[e] for e in range(i+ph,j-9,10)},10,rate,ph==0 and rate==1)
                    meta=dict(scope=scope,phase=ph,arm=a+'69',mul=rate)
                    win.append(pd.DataFrame(w,columns='entry_idx net fee turnover'.split()).assign(**meta))
                    days.append(pd.DataFrame(d,columns='idx date nav cash buy sell fees'.split()).assign(**meta))
                    if p:
                        positions.append(pd.DataFrame(p,columns='entry_idx instrument target weight gross fee'.split()).assign(**meta))
                        orders.append(pd.DataFrame(o,columns='idx instrument net_amount pretrade_nav'.split()).assign(**meta))
            detail=[] if a=="X11" else None
            monthly.append(simulate(m,actions,plan,i,j,True,detail).assign(scope=scope,arm=a+'69'))
            if detail:pd.concat(detail).to_parquet(DEST/(scope+"_X1169_funded_pnl.parquet"),index=False)
    for rows,name in [(positions,'positions'),(orders,'orders'),(days,'daily')]:
        pd.concat(rows).to_parquet(DEST/('market_challenge_'+name+'.parquet'),index=False)
    pd.concat(monthly).to_parquet(DEST/'market_challenge_stagger.parquet',index=False)
    pd.concat(win).to_parquet(DEST/'market_challenge.parquet',index=False)
if __name__=='__main__':main()
