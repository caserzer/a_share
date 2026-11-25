"""Exploratory frozen 300-to-800 transfer. Restart all paired accounts after a failed window."""
from accounts_followup import *
import account

def main():
    local=Path.home()/'.cache/a_share/ep38_three_track/market'
    narrow=pd.read_parquet(OUT/'scores.parquet')
    ds=pd.read_parquet(local/'wide_features.parquet',filters=[('signal_date','in',list(narrow.signal_date.unique())),('outer_ok','=',True)])
    panels=[]
    for q,g in ds.groupby(ds.signal_date.dt.to_period('Q').astype(str)):
        x=g[COLS]
        booster=lgb.Booster(model_file=str(OUT/'models'/q/'tree_rank.txt'))
        med=pd.Series(json.loads((OUT/'models'/q/'medians.json').read_text()))
        model=json.loads((LINEAR/'models'/(q+'.json')).read_text())['baseline']
        panels.append(g[KEY+['entry_idx','in300']].assign(R=predict(x,model),T=booster.predict(x.fillna(med),num_threads=2)))
    panel=pd.concat(panels)
    overlap=panel.merge(narrow,on=KEY,validate='1:1')
    for a,b in [('R','baseline'),('T','tree_rank')]:np.testing.assert_allclose(overlap[a],overlap[b],atol=1e-10,rtol=0)
    account.PRIVATE=local;ledger.accounts.PRIVATE=local;ledger.accounts.OUT=DEST/'wide'
    ledger.accounts.OUT.mkdir(exist_ok=True)
    m,actions=ledger.setup('flat')
    fixed=narrow.groupby('entry_idx').size()//10
    rows=[];coverage=[];fail=[];daily=[]
    for pool,f in [('CSI800',panel),('outside300',panel[~panel.in300])]:
        for size in ['D10','fixed300']:
            arms=defaultdict(dict)
            for e,g in f.groupby('entry_idx'):
                k=len(g)//10 if size=='D10' else fixed[e]
                r=g.sort_values(['R','instrument'],ascending=False).instrument;t=g.sort_values(['T','instrument'],ascending=False).instrument
                budget=r.iloc[:2*k]
                for a,ids in {'R':r.iloc[:k],'T':t.iloc[:k],'B':t[t.isin(budget)].iloc[:k],'U':r}.items():
                    arms[a][e]=m.symbols.get_indexer(ids)
                coverage.append(dict(pool=pool,size=size,entry_idx=e,eligible=len(g),overlap=g.in300.sum(),seats=k))
            def segment(es,scope):
                if not es:return
                outputs={};bad=[]
                for a,plans in arms.items():
                    try:outputs[a]=replay(m,actions,{e:plans[e] for e in es},10,1,False)
                    except ValueError as ex:
                        kind,date,names=ex.args[0]
                        bad.append(m.days.get_loc(date))
                        fail.append(dict(pool=pool,size=size,scope=scope,arm=a,kind=kind,date=date,names=','.join(names)))
                if bad:
                    day=min(bad);left=[e for e in es if e+10<day];right=[e for e in es if e>day]
                    segment(left,scope+'_prefix');segment(right,scope+'_restart')
                    return
                for a,(w,d,_,_) in outputs.items():
                    meta=dict(pool=pool,size=size,scope=scope,arm=a)
                    rows.append(pd.DataFrame(w,columns='entry_idx net fee turnover'.split()).assign(**meta))
                    daily.append(pd.DataFrame(d,columns='idx date nav cash buy sell fees'.split()).assign(**meta))
            for scope,main in [('primary',True),('later',False)]:
                segment([e for e in sorted(arms['R']) if (m.days[e]<pd.Timestamp('2025-03-03'))==main],scope)
    pd.concat(rows).to_parquet(DEST/'wide/windows.parquet',index=False)
    pd.concat(daily).to_parquet(DEST/'wide/daily.parquet',index=False)
    pd.DataFrame(coverage).to_csv(DEST/'wide/coverage.csv',index=False);pd.DataFrame(fail).to_csv(DEST/'wide/gaps.csv',index=False)
if __name__=='__main__':main()
