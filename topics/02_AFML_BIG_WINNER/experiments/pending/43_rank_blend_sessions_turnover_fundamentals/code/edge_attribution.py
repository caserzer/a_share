from fund_fit import *
def run():
    ff=pd.concat(pd.read_parquet(p,columns=KEY+['R','pos60','dd60','industry']+N+H) for p in sorted(F.glob('scores_*.parquet')))
    total=ff.groupby('entry_idx');pos=total.pos60.rank(pct=True);dd=total.dd60.rank(pct=True)
    ff['low']=((pos+dd)/2).groupby(ff.entry_idx).rank(pct=True)<=.2
    ff['visible']=ff[H[2:]].sum(axis=1)<=1;ff['low_visible']=ff.low&ff.visible
    ff.groupby(['signal_date','industry'])[['low','visible','low_visible']].sum().to_parquet(F/'F5_low_support.parquet')
    m=book(True);ff['stock']=m.symbols.get_indexer(ff.instrument)
    stat=[];tails=[]
    for family in ['Fproxy','Fgate','Fstrict']:
        for marker in (O/f'accounts/800/{family}').glob('*/done'):
            root=marker.parent;arm=family+'/'+root.name
            for sg,span in enumerate(SEG800,1):
                f=root/str(sg)/'transactions.parquet';tx=pd.read_parquet(f)
                targets=tx[tx.target>0].merge(ff,left_on=['day','stock'],right_on=['entry_idx','stock'],how='left')
                for col in ['pos60','dd60']+N:
                    ok=targets[col].notna()
                    if col in N:ok&=targets[H[N.index(col)]].eq(0)
                    am=targets.loc[ok,'target'];val=targets.loc[ok,col]
                    stat.append((arm,sg,col,targets.target.sum(),am.sum(),(am*val).sum()/am.sum() if am.sum() else np.nan))
                if family=='Fgate' and root.name=='gate':
                    for base in ['W_R','Fgate_hash']:
                        z=pd.read_parquet(root/str(sg)/('capital_vs_'+base+'.parquet'))
                        for v in ['buy_extra','sell_extra']:
                            zz=z[z[v]>1e-12].dropna(subset=['IV']).sort_values('IV')
                            if zz.empty:continue
                            w=zz[v];y=np.expm1(zz.IV);t=np.searchsorted(w.cumsum(),.10*w.sum());tails.append((sg,base,v,w.sum(),np.average(y,weights=w),y.iloc[min(t,len(y)-1)],(w[y<0].sum()/w.sum())))
    pd.DataFrame(stat,columns='arm segment feature target_capital covered_capital weighted_target_exposure'.split()).to_csv(F/'F4_value_style.csv',index=False)
    pd.DataFrame(tails,columns='segment base side changed_capital weighted_H10 capital_weighted_p10 losing_capital_fraction'.split()).to_csv(F/'F5_tail_cash.csv',index=False)
if __name__=='__main__':run()
