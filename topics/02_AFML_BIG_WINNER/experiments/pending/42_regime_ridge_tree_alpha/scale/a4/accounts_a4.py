"""Sector-family masked accounts, exact session traces and overlap with the original targets."""
from scores import *
import tempfile
sys.path.insert(0,str(EP42/'state'))
import core42 as core
from engine import pack

def main():
    k300=pd.read_parquet(SCORES,columns=['entry_idx']).groupby('entry_idx').size()//10
    dv=[];av=[];mv=[];holdings=[];coverage=[]
    for pool in ['300','800']:
        m=core.market(pool=='800')
        spans=core.SEG300 if pool=='300' else core.SEG800
        fs=list((OUT/('scores_'+pool)).glob('*.parquet'))
        assert len(fs)==23
        cols=[a for a in pd.read_parquet(fs[0]).columns if 'mask_' in a]+['R','T']
        f=pd.concat([pd.read_parquet(a,columns=['entry_idx','instrument']+cols) for a in fs],ignore_index=True)
        baseline={}
        for arm in ['R','T']+[c for c in cols if '_mask_' in c]:
            h=f.sort_values(['entry_idx',arm,'instrument'],ascending=[True,False,False])
            h=h[h.groupby('entry_idx').cumcount()<h.entry_idx.map(k300)].copy()
            h['id']=m.symbols.get_indexer(h.instrument)
            plan=h.groupby('entry_idx').id.agg(list).to_dict()
            pk=pack(m,plan)
            if arm in ['R','T']:baseline[arm]=plan
            else:
                base=baseline[arm[0]]
                for e,ids in plan.items():
                    coverage.append((pool,arm,m.days[e-1],len(ids),len(set(ids)-set(base[e]))))
            for e,ids in plan.items():holdings.append((pool,arm,m.days[e-1],m.symbols[ids].tolist()))
            for idx,span in enumerate(spans,1):
                for fee in [1,2]:
                    need_trace=arm in ['R','T'] and fee==1
                    with tempfile.NamedTemporaryFile() as temp:
                        d=core.replay(m,pk,span,fee=fee,trace=temp.name if need_trace else None)
                        if need_trace:
                            tr=core.read_trace(temp.name)
                            tr=tr[tr.day<=m.days.get_loc(d.index[-1])]
                            if pool=='300':
                                orig=pd.read_parquet(EP42/'state/results/main'/f'trace_{arm}_{idx}.parquet')
                                assert len(tr)==len(orig)
                                np.testing.assert_allclose(tr.to_numpy(),orig.to_numpy(),rtol=0,atol=1e-11)
                            else:
                                atomic_parquet(tr,OUT/f'trace_{pool}_{arm}_{idx}.parquet')
                            trsum=tr.groupby('day')[['overnight','intraday','fee']].sum().reindex(m.days.get_indexer(d.index),fill_value=0)
                            np.testing.assert_allclose(trsum.overnight+trsum.intraday,d.gross_pnl.to_numpy(),atol=1e-10)
                            np.testing.assert_allclose(trsum.fee,d.fee.to_numpy(),atol=1e-10)
                    meta=dict(pool=pool,arm=arm,segment=idx,fee_multiple=fee)
                    dd=d.reset_index().assign(**meta)
                    dd['prev']=dd.nav.shift(fill_value=1.)
                    dv.append(dd)
                    for y,g in dd.groupby(dd.date.dt.year):
                        av.append((*meta.values(),y,g.date.iloc[0],g.date.iloc[-1],g.nav.iloc[-1]/g.prev.iloc[0]-1))
                    mv.append(core.monthly(d,m.days).reset_index().assign(**meta))
        del f
    atomic_parquet(pd.concat(dv,ignore_index=True),OUT/'daily.parquet')
    pd.concat(mv,ignore_index=True).to_csv(OUT/'monthly.csv',index=False)
    pd.DataFrame(av,columns='pool arm segment fee_multiple year start end net'.split()).to_csv(OUT/'annual.csv',index=False)
    atomic_parquet(pd.DataFrame(holdings,columns='pool arm signal_date names'.split()),OUT/'targets.parquet')
    atomic_parquet(pd.DataFrame(coverage,columns='pool arm signal_date seats changes'.split()),OUT/'changed_seats.parquet')
if __name__=='__main__':main()
