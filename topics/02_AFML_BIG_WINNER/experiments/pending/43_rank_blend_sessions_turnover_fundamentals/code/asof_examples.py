from fund_fit import *
def run():
    version=pd.read_parquet(F/'versions.parquet')
    panel=pd.read_parquet(F/'scoring_panel.parquet',columns=KEY[:2]+['period','disclosure','stale','capital']+A)
    strict=pd.read_parquet(F/'strict/qualified_panel.parquet',columns=KEY[:2]+['checked_cap']+A)
    panel=panel.merge(strict,on=KEY[:2],validate='1:1',suffixes=('_proxy','_strict'));res=[]
    def sample(reason,sym,dt):
        f=panel[panel.instrument.eq(sym)].sort_values('signal_date')
        ix=f.signal_date.searchsorted(dt)
        for _,r in f.iloc[max(0,ix-1):ix+2].iterrows():res.append(dict(test=reason,anchor_date=dt,**r.to_dict()))
    for sym,g in panel.groupby('instrument'):
        if g.stale.any() and (~g.stale).any():
            sample('过期临界日',sym,g.loc[g.stale,'signal_date'].min());break
    pc=version.dropna(subset=['n_income_attr_p'])
    counts=pc.groupby(['ts_code','end_date']).n_income_attr_p.nunique();seen=0
    for k in counts[counts>1].index:
        x=pc[(pc.ts_code==k[0])&(pc.end_date==k[1])].sort_values('date')
        dt=x.date.max();sym=k[0][-2:]+k[0][:6]
        if dt>=pd.Timestamp('2021-01-08') and dt<pd.Timestamp('2026-09-20') and panel[(panel.instrument==sym)&(panel.signal_date>=dt)].shape[0]:
            sample('供应商同财期数值变动',sym,dt);seen+=1
            if seen==4:break
    for sym,g in panel[panel.checked_cap.notna()].groupby('instrument'):
        allg=panel[panel.instrument.eq(sym)].sort_values('signal_date').copy()
        change=allg.checked_cap.notna().astype(int).diff()
        if (change==-1).any():sample('已核股数逐日市值比对退出支持',sym,allg.loc[change==-1,'signal_date'].min());break
    close=pd.read_parquet(LOCAL/'close.parquet')
    for sym,g in panel.groupby('instrument'):
        first=close[sym].first_valid_index()
        if first is not None and pd.Timestamp('2021-01-08')<=first<g.signal_date.min() and (g.signal_date.min()-first).days<365:
            sample('新上市首次达到评分资格',sym,g.signal_date.min());break
    for sym,g in panel.groupby('instrument'):
        bad=g.ROE_proxy.isna()&g.BM_proxy.notna()&~g.stale
        if bad.any():sample('权益存在而TTM质量缺失',sym,g.loc[bad,'signal_date'].min());break
    pd.DataFrame(res).to_csv(F/'F1_asof_examples.csv',index=False)
if __name__=='__main__':run()
