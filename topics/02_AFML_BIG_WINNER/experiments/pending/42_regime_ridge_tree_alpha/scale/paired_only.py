"""Isolate disputed S5 tickets at original budget and on capital invested in these tickets alone."""
from replay import *
sys.path.insert(0,str(EP42/'state'))
import core42 as core

def main():
    m=load(False)
    cv=pd.read_csv(RES/'S5_coverage.csv',parse_dates=['signal_date'])
    pp=pd.read_parquet(RES/'S5_pairs.parquet')
    days=m.days.get_indexer(cv.signal_date)+1
    steps=dict(zip(cv.signal_date,days))
    daily=[];monthly=[];single=[]
    for side in ['live','fixed']:
        chosen={steps[d]:m.symbols.get_indexer(v[side]) for d,v in pp.groupby('signal_date')}
        for method,den in [('budget',cv.K),('invested',cv.matched)]:
            pk=pack(m,chosen,dict(zip(days,den)))
            for seg,ds,de in SEG:
                for fee in [1,2]:
                    d=simulate(m,pk,(ds,de,de),multiplier=fee)
                    daily.append(d.reset_index().assign(arm=side,segment=seg,method=method,fee_multiple=fee))
                    monthly.append(core.monthly(d,m.days).reset_index().assign(arm=side,segment=seg,method=method,fee_multiple=fee))
                single.append(single_periods(m,pk,seg,ds,de).assign(arm=side,method=method))
    mm=pd.concat(monthly); mm.to_csv(RES/'S5_paired_only_months.csv',index=False)
    pd.concat([core.contrast(g,'live','fixed').assign(method=meth,fee_multiple=fee) for (meth,fee),g in mm.groupby(['method','fee_multiple'])]).to_csv(RES/'S5_paired_only_contrasts.csv',index=False)
    atomic_parquet(pd.concat(daily),RES/'S5_paired_only_daily.parquet')
    atomic_parquet(pd.concat(single),RES/'S5_paired_only_h10.parquet')
if __name__=='__main__':main()
