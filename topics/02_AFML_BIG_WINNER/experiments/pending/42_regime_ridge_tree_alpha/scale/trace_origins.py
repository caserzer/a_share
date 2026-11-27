"""Trace booked gross and fees to decision dates, including retained legacy and net orders."""
import tempfile
from scale_common import *
sys.path.insert(0,str(EP42/'state'))
import core42 as core
from engine import pack

ARMS=['R','S2_A','S2_B','S2_C','S2_D','S2_A_commonmask','S2_C_commonmask','vol_fixed','vol_live','vol_lag20','vol_live_supported','vol_lag20_supported','vol_loc','vol_width','sector_live','sector_fixed','paired_live','paired_fixed','ridge69','mse69','G3_main','G3_interaction','shallow_early']

def main():
    m=core.market()
    targets=pd.read_parquet(RES/'target_lists.parquet')
    z=pd.read_parquet(EP42/'state/results/states.parquet').set_index('signal_date').Z1
    outputs=[]
    for arm in ARMS:
        g=targets[targets.arm.eq(arm)]
        plan={r.entry_idx:m.symbols.get_indexer(r.instruments) for r in g.itertuples()}
        pk=pack(m,plan,g.set_index('entry_idx').denominator.to_dict())
        for segment,span in enumerate(core.SEG300,1):
            with tempfile.NamedTemporaryFile() as temp:
                d=core.replay(m,pk,span,trace=temp.name)
                tr=core.read_trace(temp.name)
            start=m.days.get_loc(span[0])
            last={};book={}
            for day,p,j,old,new,on,intra,fee,tgt,flow in tr.itertuples(index=False,name=None):
                prior=last.get((p,j))
                if old>0:assert prior is not None
                now=prior
                if new>0 and (old<=0 or (tgt>0 and (day-start)%10==p and day-prior>=10 and m.sell[day,j])):now=day
                if new>0:last[p,j]=now
                else:last.pop((p,j),None)
                fee_key=(now if now is not None else day) if flow>0 else (prior if prior is not None else day)
                for e,idx,amt in [(prior,0,on),(now,1,intra),(fee_key,2,fee),(now if now is not None else day,3,max(flow,0)),(day,4,tgt)]:
                    if not amt:continue
                    assert e is not None
                    if e not in book:book[e]=np.zeros(5)
                    book[e][idx]+=amt
            rows=[]
            for e,v in book.items():rows.append((arm,segment,m.days[e-1],z.get(m.days[e-1],np.nan),*v))
            v=np.asarray(list(book.values())).sum(axis=0)
            assert abs(v[:2].sum()-d.gross_pnl.sum())<1e-10 and abs(v[2]-d.fee.sum())<1e-10
            outputs.extend(rows)
        print(arm,flush=True)
    atomic_parquet(pd.DataFrame(outputs,columns='arm segment signal_date Z1 overnight intraday fee gross_buy_flow ticket_target'.split()),RES/'cohort_pnl.parquet')
if __name__=='__main__':main()
