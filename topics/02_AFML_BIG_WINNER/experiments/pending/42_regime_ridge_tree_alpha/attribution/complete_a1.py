"""Capital and monthly concentration on the two original books and the matched counterfactuals."""
from matching42 import *
def main():
    m=market(True)
    labels=pd.read_parquet(DEST/'a1_targets.parquet')
    numerator=[];seats=[]
    for seg,span in enumerate(SEG800,1):
        start,end,stop=m.days.get_indexer(pd.to_datetime(span))
        for arm in ['head','runner']:
            trace=pd.read_parquet(DEST/f'a1_trace_{arm}_{seg}.parquet')
            for lim in [.1,.2]:
                table=labels[(labels.caliper==lim)&(labels.arm==arm)]
                reason={(int(t.entry),int(t.stock)):t.reason for t in table.itertuples(index=False)}
                for label,g in table[table.entry.between(start,min(end-10,stop))].groupby('reason'):
                    seats.append((seg,arm,lim,label,len(g),g.symbol.nunique()))
                holdings={}; cash={}
                for t in trace.itertuples(index=False):
                    lot=holdings.setdefault((t.phase,t.stock),{})
                    ratio=min(1.,t.new_units/t.old_units) if t.old_units else 0.
                    add=max(0.,t.new_units-t.old_units)
                    if add:
                        lab=reason[t.day,t.stock]
                        c=cash.setdefault(lab,np.zeros(4))
                        c[0]+=add*m.planes[0][t.day,t.stock]
                        c[1]+=t.fee/.001 if t.flow>0 else 0
                    for l,u in list(lot.items()):
                        if ratio:lot[l]=u*ratio
                        else:del lot[l]
                    if add:lot[lab]=lot.get(lab,0)+add
                    for l,u in lot.items():
                        c=cash.setdefault(l,np.zeros(4))
                        price=m.planes[0 if t.day==end else 1][t.day,t.stock]
                        c[2]+=u*price
                        if t.day==trace.day.iat[-1]:c[3]+=u*price
                numerator.extend((seg,arm,lim,l,*v) for l,v in cash.items())
    df=pd.DataFrame(numerator,columns=['segment','arm','caliper','reason','new_position_value','actual_broker_buy','sum_daily_marked_capital','ending_position'])
    counts=pd.DataFrame(seats,columns=['segment','arm','caliper','reason','target_seats','distinct_names'])
    counts.merge(df,on=['segment','arm','caliper','reason'],how='outer').to_csv(DEST/'a1_funded_capital.csv',index=False)
    mo=pd.read_csv(DEST/'a1_monthly.csv')
    z=mo.pivot_table(index=['caliper','segment','month'],columns=['arm','reason'],values='net',fill_value=0)
    delta=(z['head']-z['runner']).fillna(0)*1e4
    delta['total']=delta.sum(axis=1)
    delta.to_csv(DEST/'a1_month_gap.csv')
    highlighted=['2024-01','2024-12','2026-08']
    rows=[]
    for (lim,reason),df in delta.stack(future_stack=True).rename('bp').reset_index().groupby(['caliper','reason']):
        parts=[]
        for s,g in df.groupby('segment'):
            v=g.bp.to_numpy();parts.append(v)
            mean,lo,hi=intervals([v]);ex=g.loc[~g.month.isin(highlighted),'bp']
            rows.append((lim,s,reason,len(g),mean,lo,hi,np.sort(v)[:-3].mean(),len(ex),ex.mean()))
        mean,lo,hi=intervals(parts);ex=df.loc[~df.month.isin(highlighted),'bp']
        rows.append((lim,'all',reason,len(df),mean,lo,hi,np.concatenate([np.sort(v)[:-3] for v in parts]).mean(),len(ex),ex.mean()))
    pd.DataFrame(rows,columns=['caliper','segment','reason','months','bp','lo','hi','drop_best3_each_segment','excluding_named_n','excluding_named_bp']).to_csv(DEST/'a1_concentration.csv',index=False)
if __name__=='__main__':main()

