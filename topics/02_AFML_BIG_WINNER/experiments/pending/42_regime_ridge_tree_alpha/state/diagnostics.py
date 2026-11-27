"""One-window conditional performance and funded contribution by the signal that opened each lot."""
from core42 import *

def trace_by_signal(m,tr):
    # A blocked outgoing sleeve keeps its decision timestamp until an actual renewal.
    day=tr.day.to_numpy();j=tr.stock.to_numpy();ph=tr.phase.to_numpy()
    out=tr.copy()
    renewed=(tr.new_units>0)&(tr.target>0)&m.planes[2][day,j]&((tr.old_units==0)|m.sell[day,j])
    key=[out.phase,out.stock]
    current=out.day.where(renewed).groupby(key,sort=False).ffill()
    previous=current.groupby(key,sort=False).shift()
    assert previous[tr.old_units>0].notna().all()
    assert current[tr.new_units>0].notna().all()
    out['old_origin']=previous
    out['origin']=current
    return out

def signal_lots(m,tr):
    data=trace_by_signal(m,tr)
    # Cash flow due to a substituted security may be recorded on the successor symbol.
    sell_origin=data.old_origin.fillna(data.day)
    buy_origin=data.origin.fillna(data.day)
    before=pd.DataFrame(dict(origin=sell_origin.astype(int),day=data.day,stock=data.stock,overnight=data.overnight,
                             fee=data.fee.where(data.flow<0,0),sell=data.fee.where(data.flow<0,0)/.002))
    after=pd.DataFrame(dict(origin=buy_origin.astype(int),day=data.day,stock=data.stock,intraday=data.intraday,
                            fee=data.fee.where(data.flow>=0,0),buy=data.fee.where(data.flow>0,0)/.001))
    combined=pd.concat([before,after],ignore_index=True)
    return combined.groupby(['origin','day','stock'],sort=False).sum().reset_index()

def main():
    dest=OUT/'main'
    m=market();st=pd.read_parquet(OUT/'states.parquet').set_index('signal_date')
    data=pd.read_parquet(OUT/'scores.parquet')
    board=Board(m,data)
    plans={a:board.pack(w) for a,w in [('R',0.),('T',1.)]}
    weights=pd.read_parquet(dest/'weights_daily.parquet')
    daily=pd.read_parquet(dest/'daily.parquet')
    rows=[];holdst=[];capital=[]
    target=pd.read_parquet(dest/'targets.parquet')
    target={a:dict(zip(g.entry_idx,map(set,g.stock_indices))) for a,g in target.groupby('arm')}
    for seg,span in enumerate(SEG300,1):
        lo,end=m.days.get_indexer([span[0],span[1]])
        for e in range(lo,end-9):
            ind=np.searchsorted(board.entries,e);z=weights.loc[m.days[e-1]]
            band='low' if z.Z1<1/3 else 'high' if z.Z1>2/3 else 'mid'
            joined=dict(segment=seg,entry=e,signal_date=m.days[e-1],phase=(e-lo)%10,Z1=z.Z1,band=band)
            a,b=[p[0][e,:p[1][e]] for p in plans.values()]
            joined['overlap']=len(set(a)&set(b))/len(a)
            for arm,plan in plans.items():
                f=replay(m,plan,(e,e+10,e+10),phase=0)
                joined.update({arm+'_net':f.nav.iloc[-1]-1,arm+'_gross':f.gross_pnl.sum(),arm+'_fee':f.fee.sum(),arm+'_turn':(f.buy+f.sell).sum()})
            rows.append(joined)
        for arm in ['R','T','static','dynamic','lag20','confirm5','plus_Z2','plus_Z3','plus_Z4','budget_static','budget_dynamic','budgetK_static','budgetK_dynamic']:
            tr=pd.read_parquet(dest/f'trace_{arm}_{seg}.parquet')
            lots=signal_lots(m,tr)
            lots=lots[(lots.buy+lots.sell+lots.fee+lots.overnight.abs()+lots.intraday.abs())>0].copy()
            lots['origin_date']=m.days[lots.origin-1]
            for z in ['Z1','Z2','Z3','Z4','state_age']:
                lots[z]=lots.origin_date.map(weights[z])
            lots['band']=pd.cut(lots.Z1,[-1,1/3,2/3,2],labels=['low','mid','high']).astype('string')
            lots.loc[lots.Z1.eq(1/3),'band']='mid'
            dates=m.days[lots.day]
            lots['month']=dates.strftime('%Y-%m')
            ref=daily.query('arm==@arm and segment==@seg').set_index('date')
            opening=ref.nav.groupby(ref.index.to_period('M')).last().shift()
            lots['monthly_denominator']=pd.PeriodIndex(lots.month,freq='M').map(opening)
            comparable={'dynamic':'static','static':'dynamic','R':'T','T':'R','lag20':'dynamic','confirm5':'dynamic'}.get(arm,'dynamic')
            if arm.startswith('budget'):comparable=arm.rsplit('_',1)[0]+('_static' if arm.endswith('_dynamic') else '_dynamic')
            lots['unique_target']=[j not in target[comparable].get(e,set()) for e,j in zip(lots.origin,lots.stock)]
            lots['transition']=pd.cut(lots.state_age,[0,5,10,np.inf],labels=['1-5','6-10','stable'])
            for col in ['buy','sell','fee','overnight','intraday']:
                lots[col+'_monthly']=lots[col]/lots.monthly_denominator
            group=['origin','origin_date','month','band','transition','unique_target']
            pooled=lots.groupby(group,observed=True,dropna=False)[['buy','sell','fee','overnight','intraday','buy_monthly','sell_monthly','fee_monthly','overnight_monthly','intraday_monthly']].sum().reset_index()
            holdst.append(pooled.assign(arm=arm,segment=seg))
            sums=lots.groupby('day')[['fee','overnight','intraday']].sum().reindex(range(lo,end+1),fill_value=0)
            assert abs(sums.overnight.to_numpy()+sums.intraday.to_numpy()-ref.gross_pnl.to_numpy()).max()<1e-10
            assert abs(sums.fee.to_numpy()-ref.fee.to_numpy()).max()<1e-10
    one=pd.DataFrame(rows)
    for c in ['net','fee','gross','turn']:one[c+'_gap']=one['T_'+c]-one['R_'+c]
    one['month']=one.signal_date.dt.strftime('%Y-%m')
    one.to_csv(dest/'g1_windows.csv',index=False)
    summary=one.groupby(['segment','band']).agg(dates=('entry','size'),months=('month','nunique'),net=('net_gap','mean'),gross=('gross_gap','mean'),fee=('fee_gap','mean'),turnover=('turn_gap','mean'),overlap=('overlap','mean'))
    summary.to_csv(dest/'g1_states.csv')
    one.groupby(['segment','band','phase']).net_gap.agg(['mean','size']).to_csv(dest/'g1_offsets.csv')
    # Resample contiguous decision-month blocks jointly across the state bins.
    rng=np.random.default_rng(4201);ci=[]
    for seg,g in one.groupby('segment'):
        monthly=g.pivot_table(index='month',columns='band',values='net_gap',aggfunc=['sum','count']).fillna(0)
        n=len(monthly);starts=rng.integers(n-2,size=(10000,(n+2)//3))
        idx=(starts[:,:,None]+np.arange(3)).reshape(10000,-1)[:,:n]
        def meanband(b):
            total=monthly['sum',b].to_numpy()[idx].sum(axis=1)
            count=monthly['count',b].to_numpy()[idx].sum(axis=1)
            return np.divide(total,count,out=np.full(len(count),np.nan),where=count>0)
        vals=meanband('high')-meanband('low')
        point=summary.at[(seg,'high'),'net']-summary.at[(seg,'low'),'net']
        ci.append(dict(segment=seg,gap_bp=point*1e4,lo=np.nanpercentile(vals,2.5)*1e4,hi=np.nanpercentile(vals,97.5)*1e4))
    pd.DataFrame(ci).to_csv(dest/'g1_high_low.csv',index=False)
    funded=pd.concat(holdst);funded.to_parquet(dest/'funded_by_signal.parquet',index=False)
    complete=pd.read_csv(dest/'monthly.csv').query('arm=="dynamic"')[['segment','month']]
    funded=funded.merge(complete,on=['segment','month'])
    funded['net']=funded.overnight+funded.intraday-funded.fee
    funded['net_monthly']=funded.overnight_monthly+funded.intraday_monthly-funded.fee_monthly
    c=funded.groupby(['segment','arm','unique_target'],observed=True)[['buy','sell','fee','net','net_monthly']].sum()
    c['net_per_paid_buy']=c.net/c.buy.replace(0,np.nan)
    c.to_csv(dest/'capital_overlap.csv')
    funded.groupby(['segment','arm','band','transition'],observed=True)[['net_monthly','fee_monthly','overnight_monthly','intraday_monthly','buy_monthly','sell_monthly']].sum().to_csv(dest/'state_contributions.csv')
    cov=weights.dropna(subset=['s']).loc['2021-01-08':].copy()
    for z in ['Z1','Z2','Z3','Z4']:
        cov[z+'_bin']=np.select([cov[z].isna(),cov[z]<1/3,cov[z]>2/3],['unknown','low','high'],default='mid')
    cov['month']=cov.index.strftime('%Y-%m')
    cov['segment']=np.where(m.days[cov.entry_idx]<pd.Timestamp(SEG300[1][0]),1,2)
    cross=[]
    for z in ['Z2','Z3','Z4']:
        for key,sub in cov.groupby(['segment','Z1_bin',z+'_bin']):
            entries=sub.entry_idx
            changed=sum(len(target['plus_'+z][e]-target['dynamic'][e]) for e in entries)
            paid=funded[(funded.arm=='plus_'+z)&funded.origin.isin(entries)&funded.unique_target].buy.sum()
            cross.append((*key,z,len(sub),sub.month.nunique(),sub['plus_'+z].mean(),changed,paid))
    pd.DataFrame(cross,columns=['segment','Z1_band','other_band','state','days','months','mean_tree_weight','changed_target_seats','extra_paid_buy']).to_csv(dest/'g5_cross_state.csv',index=False)
    rankic=[]
    for e,ids,r,t,k in board.rows:
        if e<board.m.days.get_loc('2021-01-11') or e+10>=len(m.days):continue
        y=m.o[e+10,ids]/m.o[e,ids]-1
        w=weights.loc[m.days[e-1]]
        order=np.argsort(-r,kind='stable')
        for name,x in [('R',r),('T',t),('static',(1-w.static)*r+w.static*t),('dynamic',(1-w.dynamic)*r+w.dynamic*t)]:
            for group,sel in [('all',order),('boundary',order[k//2:2*k])]:
                a=pd.Series(x[sel]);b=pd.Series(y[sel]).replace([np.inf,-np.inf],np.nan)
                rankic.append((m.days[e-1],name,group,a.corr(b,method='spearman'),b.count()))
    pd.DataFrame(rankic,columns=['signal_date','arm','range','rankic','labeled']).to_parquet(dest/'rankic.parquet',index=False)

if __name__=='__main__':main()

