"""Keep every original uncovered Ridge seat fixed to isolate the funded covered slice."""
from event_account import *
def main():
    s=Study(False);f=OUT/'fusion'
    data=pd.read_parquet(f/'daily_sources_and_increments.parquet')
    model=pd.read_csv(f/'folds.csv').set_index(['quarter','arm']).gamma
    data=data.merge(pd.read_parquet(engine.OUT800/'scores.parquet',columns=['signal_date','instrument','entry_idx']),on=['signal_date','instrument'],validate='1:1')
    plans={'ridge':s.top};observations=[]
    for e,g in data.groupby('entry_idx'):
        ids=s.m.symbols.get_indexer(g.instrument);top=s.top[e];q=str(g.signal_date.iat[0].to_period('Q'))
        for n in ['eps20','eps60','target20','coverage_delta','sue20','mixed']:
            mask=(g[n].notna() if n!='mixed' else (g.eps20.notna()|g.sue20.notna())).to_numpy()
            core=top[~np.isin(top,ids[mask])];k=len(top)-len(core)
            score=g.R.to_numpy()+model.get((q,n),0.)*g['inc_'+n].to_numpy()
            arr=ids[mask][np.lexsort((ids[mask],score[mask]))[::-1][:k]]
            act=np.r_[core,arr];plans.setdefault(n,{})[e]=act
            observations.append((n,e,len(ids),sum(mask),len(top),k,len(set(act)-set(top))))
    out=OUT/'same_coverage';out.mkdir(exist_ok=True)
    pd.DataFrame(observations,columns='arm entry_idx pool covered head covered_head changed'.split()).to_parquet(out/'support.parquet',index=False)
    s.run('same_coverage',plans,[(n,'ridge') for n in plans if n!='ridge'])
if __name__=='__main__':main()
