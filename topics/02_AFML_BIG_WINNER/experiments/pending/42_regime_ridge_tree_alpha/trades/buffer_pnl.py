"""Follow observed buffer-band holdings across actual open and close marks."""
from collections import defaultdict
from pathlib import Path
import sys,tempfile
import numpy as np,pandas as pd
HERE=Path(__file__).resolve().parent;OUT=HERE/'results';OLD=next(HERE.parents[1].glob('41_*'))
sys.path.remove(str(HERE))
sys.path.insert(0,str(OLD/'p2'))
from inputs import ledger,SEGMENTS
from book import State,step
def main():
    with tempfile.TemporaryDirectory() as tmp:
        ledger.accounts.OUT=Path(tmp);m,actions=ledger.setup('flat')
    sel=pd.read_parquet(OUT/'buffer_paths.parquet')
    agg=[]
    for scope,a,b in SEGMENTS:
        lo,hi=m.days.get_indexer([a,b])
        for arm,occ in sel[sel.scope==scope].groupby('arm'):
            cuts=defaultdict(dict)
            for t in occ.itertuples():
                cuts[t.entry_idx][m.symbols.get_loc(t.instrument)]=(t.entry_idx,t.category,t.status,t.instrument)
            d=OUT/'books'/scope/arm;tgt=pd.read_parquet(d/'decisions.parquet').set_index('entry_idx')
            ref=pd.read_parquet(d/'daily.parquet')
            st=State.empty(m.n);tags=[{} for _ in range(10)];prior=np.zeros(m.n)
            sums=defaultdict(lambda:np.zeros(5))
            for i in range(lo,hi+1):
                ph=(i-lo)%10;op=np.nan_to_num(m.marks['flat'][0][i]);cl=np.nan_to_num(m.marks['flat'][0 if i==hi else 1][i])
                before=st.units
                for p,active in enumerate(tags):
                    for j,key in active.items():sums[key][0]+=before[p,j]*(op[j]-prior[j])
                replaced=tags[ph];inc=cuts[i]
                for j,key in inc.items():sums[key][2]+=before[ph,j]*op[j]
                if i+10<=hi:
                    row=tgt.loc[i];target=m.symbols.get_indexer(row.target)
                    valid=m.buy[i]&m.members[i-1]
                    dummy=np.flatnonzero(~valid)[0]
                    target=np.r_[target,np.repeat(dummy,row.k-len(target))].astype(int)
                    tags[ph]=inc.copy()
                else:target=None
                acct,detail=step(m,actions,st,lo,hi,i,target,1,True)
                assert abs(acct['nav']-ref.nav.iloc[i-lo])<1.e-10,(scope,arm,i,acct['nav'],ref.nav.iloc[i-lo])
                od,fee=detail[:2]
                for p,active in enumerate(tags):
                    for j,key in active.items():
                        sums[key][0]+=st.units[p,j]*(cl[j]-op[j])
                        sums[key][1]+=fee[p,j]
                        if i==key[0]:sums[key][3]+=st.units[p,j]*op[j]
                    if p==ph and target is not None:
                        for j,key in replaced.items():
                            if j not in active:sums[key][1]+=fee[p,j]
                if target is None and i>=hi-9:
                    tags[ph]={j:key for j,key in tags[ph].items() if st.units[ph,j]>0}
                prior=cl
            for (e,category,status,stock),r in sums.items():
                agg.append((scope,arm,e,category,status,stock,*r[:4]))
    t=pd.DataFrame(agg,columns='scope arm entry_idx category status instrument gross fee old_open_value rebalance_value'.split())
    t['net']=t.gross-t.fee
    t.to_parquet(OUT/'buffer_actual_lots.parquet',index=False)
    t.groupby(['scope','arm','category','status']).agg(seats=('instrument','size'),actual_gross=('gross','sum'),actual_fees=('fee','sum'),actual_net=('net','sum'),pre_value=('old_open_value','sum'),initial_held=('rebalance_value','sum')).to_csv(OUT/'buffer_actual_pnl.csv')
if __name__=='__main__':main()
