"""Revalue common reference accounts on exactly the observed dated endpoints."""
from mixture import *
from engine import STORE

def main():
    dates=[];annual=[];gaps=[]
    for name,wide,pool in [('main',False,'300'),('d6',True,'800'),('g7_refit',True,'outside')]:
        m=market(wide)
        score=pd.read_parquet(OUT/('wide_scores.parquet' if wide else 'scores.parquet'))
        if pool=='outside':score=score[~score.in300]
        plans={e:m.symbols.get_indexer(g.instrument) for e,g in score.groupby('entry_idx')}
        eq=original.pack(m,plans)
        if wide:
            idx=pd.read_parquet(STORE/'index800.parquet')
            assert idx.ts_code.nunique()==1
            ticker=idx.ts_code.iloc[0]
            idx=idx.set_index(pd.to_datetime(idx.trade_date)).close.sort_index()
        else:idx=get_index();ticker='H00300.CSI'
        scopes=SEG800 if wide else SEG300
        for seg,span in enumerate(scopes,1):
            ef=replay(m,eq,span)
            gaps.append((pool,seg,'equal',span[0],span[2],ef.index[-1],ticker))
            em=monthly(ef,m.days).net
            groups=({'main','shallow','single_states'} if pool=='300' else {'d6'} if pool=='800' else {'g7_refit','g7_transfer'})
            for label in sorted(groups):
                dest=OUT/label
                data=pd.read_parquet(dest/'daily.parquet')
                for arm,g in data[data.segment.eq(seg)].groupby('arm'):
                    g=g.set_index('date').sort_index();mo=monthly(g,m.days)
                    for month,r in mo.iterrows():
                        period=pd.Period(month,'M')
                        a=m.days[m.days.to_period('M')==period-1][-1]
                        b=m.days[m.days.to_period('M')==period][-1]
                        bench=idx.at[b]/idx.at[a]-1
                        dates.append((label,pool,seg,arm,month,r.net,bench,em.get(month,np.nan),r.net-bench,r.net-em.get(month,np.nan)))
                    for year,sub in [('segment',g),*g.groupby(g.index.year)]:
                        lo=sub.index[0];hi=sub.index[-1]
                        before=g.index[g.index.get_loc(lo)-1] if lo!=g.index[0] else lo
                        startnav=g.at[before,'nav'] if lo!=g.index[0] else 1.
                        nav=sub.nav.iloc[-1]/startnav-1
                        dd=np.r_[startnav,sub.nav];dd=np.min(dd/np.maximum.accumulate(dd)-1)
                        ri=idx.at[hi]/idx.at[before]-1
                        re=(ef.at[hi,'nav']/(ef.at[before,'nav'] if lo!=g.index[0] else 1.)-1) if hi in ef.index and before in ef.index else np.nan
                        annual.append((label,pool,seg,arm,year,lo,hi,nav,dd,ri,nav-ri,re,nav-re,float((sub.cash/sub.nav).mean()),sub.buy.sum(),sub.sell.sum(),sub.fee.sum()))
    pd.DataFrame(dates,columns='group pool segment arm month net total_return_index pool_equal net_minus_index net_minus_equal'.split()).to_csv(OUT/'benchmark_months.csv',index=False)
    pd.DataFrame(annual,columns='group pool segment arm year first last net mdd total_return_index net_minus_index pool_equal net_minus_equal mean_cash_ratio buy sell fee'.split()).to_csv(OUT/'benchmark_years.csv',index=False)
    pd.DataFrame(gaps,columns='pool segment arm start scheduled_end last_strict index'.split()).to_csv(OUT/'benchmark_limits.csv',index=False)
if __name__=='__main__':main()

