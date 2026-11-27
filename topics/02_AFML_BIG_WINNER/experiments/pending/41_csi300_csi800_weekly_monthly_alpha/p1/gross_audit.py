"""Independent stock-level P&L on the archived EP40 engine and strict common dates."""
from engine import *
import importlib.util
def main():
    spec=importlib.util.spec_from_file_location('archived_ep40_800_book',OLD/'book.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    m=load();plans,_=selections(m)
    d=pd.read_parquet(RESULT/'daily.parquet').query('kind=="strict" and phase==-1 and model=="refit"').set_index(['bucket','segment','date'])
    checks=[];details=[]
    for bucket in ['head','runner','decile']:
        for segment,span in enumerate(RANGES,1):
            start,end,stop=m.days.get_indexer(pd.to_datetime(span))
            stock=[]
            try:module.simulate(m,m.planes[-1],plans['refit',bucket],start,end,True,stock)
            except module.MissingMark as err:
                assert err.day>stop
            detail=pd.concat(stock,ignore_index=True)
            detail=detail[detail.date<=m.days[stop]]
            agg=detail.groupby('date')[['gross','fee']].sum()
            ref=d.loc[bucket,segment]
            gross=(agg.gross.reindex(ref.index).fillna(0)-ref.gross_pnl).abs().max()
            fee=(agg.fee.reindex(ref.index).fillna(0)-ref.fee).abs().max()
            assert max(gross,fee)<1e-10,(gross,fee)
            checks.append(dict(bucket=bucket,segment=segment,dates=len(ref),max_daily_gross_error=gross,max_daily_fee_error=fee))
            details.append(detail.assign(bucket=bucket,segment=segment))
    pd.concat(details,ignore_index=True).to_parquet(RESULT/'actual_stock_pnl.parquet',index=False)
    pd.DataFrame(checks).to_csv(RESULT/'stock_pnl_parity.csv',index=False)
if __name__=='__main__':main()
