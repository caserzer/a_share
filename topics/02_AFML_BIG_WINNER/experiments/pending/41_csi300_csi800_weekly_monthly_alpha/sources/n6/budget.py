"""Trace executed budget and actual H10 tails of genuinely different purchases."""
import sys
from pathlib import Path
HERE6=Path(__file__).resolve().parent
REG=HERE6.parents[1];sys.path.insert(0,str(REG/'p2'))
from inputs import market,targets,np,pd
from book import funded
from book import State,step
import hashlib,json
DEST=HERE6/'results/segment'
def main():
    m,actions=market();plans,books=targets(m)
    choice=pd.read_parquet(DEST/'marginal_decisions.parquet')
    source=pd.read_parquet(REG/'p2/results/scores.parquet',columns=['entry_idx','instrument'])
    out=[];arch=pd.read_parquet(DEST/'daily.parquet').set_index(['arm','date'])
    first,last=m.days.get_indexer(['2025-03-03','2026-10-12'])
    for arm,group in choice.groupby('arm'):
        state=State.empty(m.n)
        dates={d:g for d,g in group.groupby('signal_date')}
        for i in range(first,last+1):
            plan=None
            if i+10<=last:
                g=dates[m.days[i-1]]
                old=m.symbols.get_indexer(g.original);new=m.symbols.get_indexer(g.chosen)
                plan=np.r_[plans['rank'][i][~np.isin(plans['rank'][i],old)],new]
                assert len(np.unique(plan))==len(plan)
            row,info=step(m,actions,state,first,last,i,plan,1,True)
            assert abs(row['nav']-arch.loc[(arm,m.days[i]),'nav'])<1e-10
            if plan is None:continue
            _,_,bought,ticket,_=info
            diff=~np.isin(new,old)
            out.append(dict(arm=arm,signal_date=m.days[i-1],candidate_count=len(old),new_unique=diff.sum(),
                planned_budget=len(old)*ticket,filled_budget=bought[new].sum(),changed_planned=diff.sum()*ticket,
                changed_filled=bought[new[diff]].sum(),scored_filled=bought[new[np.isfinite(g.score_new)]].sum(),
                h10_known=bought[new[g.realized_rank_new.notna()]].sum(),d10_bought=bought[new[g.realized_rank_new>.9]].sum(),
                d1_bought=bought[new[g.realized_rank_new<=.1]].sum()))
    d=pd.DataFrame(out);d.to_csv(DEST/'funded_budget.csv',index=False)
    print(d.groupby('arm').sum(numeric_only=True).to_string())
    f=DEST/'verification.json';z=json.loads(f.read_text())
    for p in [Path(__file__),DEST/'funded_budget.csv',REG/'p2/book.py']:
        z[str(p)]=hashlib.file_digest(open(p,'rb'),'sha256').hexdigest()
    f.write_text(json.dumps(z,indent=2)+'\n')
if __name__=='__main__':main()
