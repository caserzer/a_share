"""Verify accounting, report annual reference returns, and count executable changed capital."""
from event_account import *
import json,sys
def main(folders):
    s=Study(False);m=s.m
    idx=pd.read_parquet(engine.STORE/'index800.parquet')
    ix=idx.set_index(pd.to_datetime(idx.trade_date)).close.sort_index()
    ledger=pd.read_parquet(EP41/'p1/results/daily.parquet').query('phase==-1 and kind=="strict" and model=="refit"')
    orders_map=pd.DataFrame({'security_idx':range(m.n),'instrument':m.symbols});orders_map.to_csv(OUT/'instrument_map.csv',index=False)
    pd.Series(m.days,name='trade_date').to_csv(OUT/'trading_calendar.csv',index_label='entry_idx')
    for folder in folders:
        f=OUT/folder;d=pd.read_parquet(f/'daily.parquet')
        comparisons=pd.read_csv(f/'comparisons.csv').query("stage=='all'")
        annual=[];summ=[];checks=[]
        for (stage,arm),g in d.groupby(['stage','arm']):
            g=g.set_index('date').sort_index()
            nav=g.nav.shift().fillna(1)
            for label,v in [('all',g),*g.groupby(g.index.year)]:
                st,ed=v.index[[0,-1]];start=g.index[g.index.get_loc(st)-1] if st!=g.index[0] else st
                eq=ledger[(ledger.segment==stage)&(ledger.bucket=='pool')].set_index('date').nav
                eqgain=eq.at[ed]/(1 if st==g.index[0] else eq.get(start,np.nan))-1 if ed in eq else np.nan
                gain=v.nav.iloc[-1]/nav.loc[st]-1
                rr=d[(d.stage==stage)&(d.arm.isin(['ridge','original_ridge']))].set_index('date').nav
                if rr.empty and folder=='supply':rr=ledger[(ledger.segment==stage)&(ledger.bucket=='head')].set_index('date').nav
                rret=rr.get(ed,np.nan)/(1 if st==g.index[0] else rr.get(start,np.nan))-1
                ref=ix.loc[ed]/ix.loc[start]-1
                annual.append((stage,arm,label,st,ed,gain,ref,gain-ref,eqgain,rret,gain-rret,v.fee.sum()/nav.loc[st],v.buy.sum()/nav.loc[st],v.sell.sum()/nav.loc[st]))
            fe=np.max(np.abs(g.fee-.001*g.buy-.002*g.sell))
            identity=np.max(np.abs(g.nav-nav+g.fee-g.gross_pnl))
            assert fe<1e-10 and identity<1e-10 and g.cash.min()>-1e-10
            parity=np.nan
            if arm in ('ridge','original_ridge') and folder!='events_h20':
                orig=ledger[(ledger.segment==stage)&(ledger.bucket=='head')].set_index('date')
                parity=np.max(np.abs(g[['nav','cash','fee']]-orig.loc[g.index,['nav','cash','fee']]).to_numpy());assert parity<1e-10
            checks.append((stage,arm,len(g),g.index[-1],fe,identity,parity))
        yearly=pd.DataFrame(annual,columns='stage arm year start end net csi800_tr excess_index equal_pool ridge excess_ridge fee buy sell'.split())
        yearly.to_csv(f/'annual.csv',index=False)
        pd.DataFrame(checks,columns='stage arm days last_valued fee_error identity_error ep41_ridge_parity'.split()).to_csv(f/'verification.csv',index=False)
        for stage,stage_daily in d.groupby('stage'):
            cache={}
            def read(arm):
                if arm not in cache:
                    file=f/'orders'/f'{arm}_s{stage}.parquet'
                    if not file.exists():
                        cache[arm]=pd.DataFrame(columns=['target','buy'],index=pd.MultiIndex.from_arrays([[],[]],names=['entry_idx','security_idx']))
                    else:
                        a=pd.read_parquet(file)
                        a=a[a.entry_idx<=m.days.get_loc(stage_daily[stage_daily.arm==arm].date.max())]
                        a=a.groupby(['entry_idx','security_idx'])[['target','net']].sum()
                        a['buy']=a.net.clip(lower=0)
                        cache[arm]=a[['target','buy']]
                return cache[arm]
            for c in comparisons.itertuples():
                a,b=read(c.arm),read(c.comparator)
                last=m.days.get_loc(min(stage_daily[stage_daily.arm==c.arm].date.max(),stage_daily[stage_daily.arm==c.comparator].date.max()))
                a=a[a.index.get_level_values('entry_idx')<=last];b=b[b.index.get_level_values('entry_idx')<=last]
                delta=a.subtract(b,fill_value=0).clip(lower=0).sum()
                v=stage_daily[stage_daily.arm==c.arm].set_index('date')
                bb=b.sum()
                new_names=a[['target','buy']].join(b[['target','buy']],how='left',rsuffix='_b')
                new_names=new_names[new_names.target_b.fillna(0).le(1e-12)]
                new_buy=new_names.buy.sum()
                summ.append((stage,c.arm,c.comparator,last,delta.target,delta.buy,a.target.sum(),a.buy.sum(),bb.buy,new_names.target.sum(),new_buy,delta.buy/a.buy.sum() if a.buy.sum()>0 else np.nan))
        pd.DataFrame(summ,columns='stage arm comparator last_common_idx positive_target_delta positive_netbuy_delta total_target total_netbuy control_netbuy new_name_target new_name_buy positive_delta_fraction_all_buy'.split()).to_csv(f/'capital.csv',index=False)
        print('verified',folder,flush=True)
if __name__=='__main__':main(sys.argv[1:] or ['fusion','same_coverage','events_h10','events_h20','supply','etf'])
