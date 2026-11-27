"""Pre-decision regime learning months and actual funded-switch months on the main books."""
from core42 import *
def main():
    dest=OUT/'main';m=market();w=pd.read_parquet(dest/'weights_daily.parquet')
    mo=pd.read_csv(dest/'monthly.csv').pivot(index=['segment','month'],columns='arm',values='net')
    table=pd.read_csv(dest/'weights_quarterly.csv').set_index('q')
    out=[]
    for (seg,month),g in mo.iterrows():
        begin,end,_=SEG300[seg-1];lo,hi=m.days.get_indexer([begin,end])
        e=w.entry_idx.to_numpy()
        q=w[(e>=lo)&(e<=hi-10)&(m.days[e].strftime('%Y-%m')==month)]
        changed=(q.dynamic-q.static).abs()>1e-12
        eligible=[not table.at[p,'fallback'] for p in q.index.to_period('Q').astype(str)]
        out.append((seg,month,len(q),sum(eligible),int(changed.sum()),(g.dynamic-g.static)*1e4))
    d=pd.DataFrame(out,columns='segment month order_dates calibrated_dates date_weight_diff net_bp'.split())
    d.to_csv(dest/'d5_active_months.csv',index=False)
    print(d[d.date_weight_diff>0].groupby('segment').net_bp.agg(['size','mean']))
if __name__=='__main__':main()

