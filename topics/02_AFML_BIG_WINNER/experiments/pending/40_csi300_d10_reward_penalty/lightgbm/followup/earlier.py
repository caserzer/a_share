"""Historical backward replication on 2019 and 2020, keeping the registered X11 rule."""
from accounts_followup import *
from industry_trial import within
sys.path.append(str(PRIVATE.parent/'src'))
from features import compute
def main():
    src=next(TRACK.parent.glob('rounds/51_*/results'))
    archived=pd.read_parquet(src/'scores.parquet').sort_values(KEY)
    fields='qfq_close qfq_open qfq_high qfq_low volume money turnover_rate daily_members'.split()
    raw=[pd.read_parquet(PRIVATE/(f+'.parquet')) for f in fields]
    days=raw[0].index
    features=compute(*raw,pd.read_parquet(PRIVATE/'market.parquet').close)
    train=prepare().sort_values(KEY)
    ledger.accounts.OUT=DEST
    m,actions=ledger.setup('flat');audit=[];output=[]
    industry=industries(archived.signal_date.unique())
    groups=defaultdict(lambda:defaultdict(dict))
    for q,g in archived.groupby(archived.signal_date.dt.to_period('Q')):
        d=train[train.h10_mature<q.start_time]
        assert d.h10_mature.max()<g.signal_date.min()
        med=d[COLS].median().fillna(0);y=d.target_rank.to_numpy()
        ds=lgb.Dataset(d[COLS].fillna(med),label=y,free_raw_data=False)
        warm=lgb.train(dict(PARAMS,objective='regression'),ds,num_boost_round=20)
        def grad(p,data):return 2*(p-y),np.full(len(p),2.)
        tree=lgb.train(dict(PARAMS,objective=grad),ds,num_boost_round=60,init_model=warm)
        cols=[c for c in COLS if not c.startswith("market_")]
        reduced=lgb.Dataset(d[cols].fillna(med),label=y,free_raw_data=False)
        warm69=lgb.train(dict(PARAMS,objective="regression"),reduced,num_boost_round=20)
        tree69=lgb.train(dict(PARAMS,objective=grad),reduced,num_boost_round=60,init_model=warm69)
        audit.append(dict(fold=str(q),rows=len(d),latest_maturity=d.h10_mature.max(),first=g.signal_date.min()))
        for dt,h in g.groupby('signal_date'):
            i=days.get_loc(dt)
            f=pd.DataFrame({c:features[c].iloc[i].reindex(h.instrument).values for c in COLS})
            board=h.assign(R=h.RANK_MSE_78,T=tree.predict(f.fillna(med),num_threads=2),industry=h.instrument.map(industry[dt]).fillna('未知'))
            targets=picks(board)
            cut=picks(board.assign(T=tree69.predict(f[cols].fillna(med),num_threads=2)))
            targets["X1169"]=cut["X11"]
            targets["T69"]=cut["T"]
            targets['sector_swap']=within(board)
            for a,ids in targets.items():groups[(dt.year,h.phase.iloc[0])][a][i+1]=m.symbols.get_indexer(ids)
    for (year,phase),arms in groups.items():
        for a,plan in arms.items():
            w,_,_,_=replay(m,actions,plan,10,1,False)
            output.append(pd.DataFrame(w,columns='entry_idx net fee turnover'.split()).assign(year=year,phase=phase,arm=a))
    m_half,actions_half=ledger.setup('half');stress=[]
    for (year,phase),arms in groups.items():
        if year!=2020:continue
        for a,plan in arms.items():
            w,_,_,_=replay(m_half,actions_half,plan,10,1,False)
            stress.append(pd.DataFrame(w,columns='entry_idx net fee turnover'.split()).assign(year=year,phase=phase,arm=a))
    pd.concat(stress).to_parquet(DEST/'earlier_half.parquet',index=False)
    pd.concat(output).to_parquet(DEST/'earlier.parquet',index=False)
    pd.DataFrame(audit).to_csv(DEST/'earlier_folds.csv',index=False)
if __name__=='__main__':main()
