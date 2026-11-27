"""Realized S5 holdings and G3 comparisons on the frozen D5 monthly ledger."""
from trace_origins import *
from matching import covariates

def main():
    m=core.market()
    cap,adv,_,sector,_=covariates(m)
    eligibility=pd.read_parquet(RES/'eligible.parquet').reindex(index=m.days,columns=m.symbols).fillna(False).to_numpy()
    cap_pct=pd.DataFrame(np.where(eligibility,cap,np.nan)).rank(axis=1,pct=True).to_numpy()
    adv_pct=pd.DataFrame(np.where(eligibility,adv,np.nan)).rank(axis=1,pct=True).to_numpy()
    targets=pd.read_parquet(RES/'target_lists.parquet')
    out=[]
    for arm in ['vol_live','vol_fixed','sector_live','sector_fixed','paired_live','paired_fixed']:
        g=targets[targets.arm.eq(arm)]
        plan={r.entry_idx:m.symbols.get_indexer(r.instruments) for r in g.itertuples()}
        pk=pack(m,plan,g.set_index('entry_idx').denominator.to_dict())
        for n,span in enumerate(core.SEG300,1):
            with tempfile.NamedTemporaryFile() as temp:
                d=core.replay(m,pk,span,trace=temp.name)
                tr=core.read_trace(temp.name)
            for day,h in tr.groupby('day'):
                ids=h.stock.to_numpy()
                vals=h.new_units.to_numpy()*np.nan_to_num(m.planes[0][day,ids]); cv,av=cap_pct[day-1,ids],adv_pct[day-1,ids]; sect=sector(day-1)[ids]
                for s in set(sect):
                    keep=sect==s
                    out.append((arm,n,m.days[day],s,d.at[m.days[day],'nav'],vals[keep].sum(),np.nansum((cv*vals)[keep]),np.nansum((av*vals)[keep]),vals[keep&~np.isfinite(cv)].sum(),vals[keep&~np.isfinite(av)].sum()))
    atomic_parquet(pd.DataFrame(out,columns='arm segment date sector close_nav open_holding_amount cap_percentile_amount adv_percentile_amount cap_unknown_amount adv_unknown_amount'.split()),RES/'S5_real_holdings.parquet')
    mm=pd.read_csv(RES/'months.csv');mm['turnover']=mm.buy+mm.sell
    d5=pd.read_csv(EP42/'state/results/main/monthly.csv')
    d5['segment']=d5.segment.map({1:'primary',2:'later'})
    d5['fee_multiple']=np.where(d5.arm.str.endswith('_2fee'),2,1)
    d5['arm']=d5.arm.str.replace('_2fee','',regex=False)
    allrows=[]
    for fee in [1,2]:
        joint=pd.concat([mm[mm.arm.isin(['G3_main','G3_interaction']) & mm.fee_multiple.eq(fee)],d5[(d5.arm=='dynamic') & (d5.fee_multiple==fee)]])
        for arm in ['G3_main','G3_interaction']:allrows.append(core.contrast(joint,arm,'dynamic').assign(fee_multiple=fee))
    pd.concat(allrows).to_csv(RES/'G3_D5.csv',index=False)
if __name__=='__main__':main()
