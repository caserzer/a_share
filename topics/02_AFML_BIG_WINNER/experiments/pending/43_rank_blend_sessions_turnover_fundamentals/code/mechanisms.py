from accounts43 import *
from fund_panel import F
def run(pool):
    m=book(pool==800);op=m.planes[0];actions=m.planes[-1]
    labels=pd.read_parquet(O/f'diagnostics_{pool}/daily_labels_and_tree.parquet')
    models=pd.concat(pd.read_parquet(f,columns=KEY+['over','treeover'],filters=[('pool','=',pool)]) for f in (O/'models').glob('*.parquet'))
    g=labels.merge(models,on=KEY,validate='1:1')
    raw=LOCAL if pool==800 else PRIVATE;adv=pd.read_parquet(raw/'money.parquet').reindex(columns=m.symbols,index=m.days).rolling(20,min_periods=20).mean().to_numpy()
    j=m.symbols.get_indexer(g.instrument);g['stock']=j;g['adv20']=adv[g.entry_idx-1,j]
    for c in ['over','treeover']:
        gg=g.groupby('entry_idx')[c];g[c+'_bin']=(1+np.minimum(4,np.floor(5*(gg.rank(ascending=False)-1)/gg.transform('size')))).astype(int)
    risk=[];changed=[];sessions=[];impact=[]
    pairs=[('L/cal_over','L/total'),('B/D','W/R'),('W/LP','W/buf'),('W/QP','W/LP')]
    if pool==800:pairs+=[('Fgate/gate','W/R'),('Fgate/gate','Fgate/hash'),('Fproxy/neutral','W/R')]
    for seg,span in enumerate(SEG800 if pool==800 else SEG300,1):
        lo=m.days.get_loc(span[0])
        for arm,base in pairs:
            o=O/f'accounts/{pool}';pa=o/arm/str(seg);pb=o/base/str(seg)
            a=pd.read_parquet(pa/'transactions.parquet');b=pd.read_parquet(pb/'transactions.parquet');key=['day','phase','stock']
            z=a[key+['flow','fee','old_units','new_units','target']].merge(b[key+['flow','fee','old_units','new_units','target']],on=key,how='outer',suffixes=('_arm','_base')).fillna(0)
            delta=z.flow_arm-z.flow_base;tar=z.target_arm-z.target_base
            z['buy_extra']=delta.clip(lower=0);z['sell_extra']=(-delta).clip(lower=0);z['fee_delta']=z.fee_arm-z.fee_base;z['target_diff']=abs(tar)
            gg=z.groupby('day')[['buy_extra','sell_extra','fee_delta','target_diff']].sum()
            changed.append(gg.reset_index().assign(pool=pool,segment=seg,arm=arm,base=base))
            if arm.startswith('Fgate') or arm=='L/cal_over':
                changed_names=z[(abs(delta)>1e-12)].merge(g[['entry_idx','stock','instrument','IV','I','V']],left_on=['day','stock'],right_on=['entry_idx','stock'],how='left')
                changed_names[['day','phase','stock','flow_arm','flow_base','buy_extra','sell_extra','fee_delta','IV','I','V']].to_parquet(pa/('capital_vs_'+base.replace('/','_')+'.parquet'),index=False)
        for arm in ['L/cal_over','L/cal_treeover','W/R']:
            p=O/f'accounts/{pool}'/arm/str(seg);c='treeover' if arm=='L/cal_treeover' else 'over'
            t=pd.read_parquet(p/'transactions.parquet');t=t[(t.day-lo)%10==t.phase].copy();t['increase']=t.flow.clip(lower=0)
            h=t.merge(g[['entry_idx','stock','adv20',c+'_bin','I','V']],left_on=['day','stock'],right_on=['entry_idx','stock'])
            for b,gg in h.groupby(c+'_bin'):
                am=gg.increase;den=am.sum()
                if den:
                    risk.append((pool,seg,arm,b,den,*[np.average(gg.loc[gg[v].notna(),v],weights=am[gg[v].notna()]) if am[gg[v].notna()].sum() else np.nan for v in ['adv20','I','V']]))
            daily=pd.read_parquet(p.parent/'daily.parquet',filters=[('multiple','=',1),('segment','=',seg)]);terms=pd.read_parquet(p/'session.parquet')
            capital=(daily.nav-daily.cash).sum();sessions.append((pool,seg,arm,terms.intraday.sum(),terms.overnight.sum(),capital,terms.intraday.sum()/capital,terms.overnight.sum()/capital))
    pd.concat(changed).to_parquet(O/f'changed_capital_{pool}.parquet',index=False)
    pd.DataFrame(risk,columns='pool segment arm predicted_quintile new_capital ADV20 log_I log_V'.split()).to_csv(O/f'L4_funded_quintiles_{pool}.csv',index=False)
    pd.DataFrame(sessions,columns='pool segment arm intraday overnight invested_capital_days intra_per_invested_day over_per_invested_day'.split()).to_csv(O/f'L5_funded_{pool}.csv',index=False)
if __name__=='__main__':run(int(sys.argv[1]))
