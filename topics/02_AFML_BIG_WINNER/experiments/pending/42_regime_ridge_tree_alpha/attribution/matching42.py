"""Label both original P1 books, then allocate the actual holdings, flows and paid fees."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'state'))
from core42 import *
from engine import selections, pack
from matching import covariates,assign
DEST=Path(__file__).resolve().parent/'results'
DEST.mkdir(exist_ok=True)
OLD=EP41/'p1/results'
CATEGORIES=['matched','same_edges_competed','no_industry','cap_gap','adv_gap','unknown','unallocated_fee']

def explain(group,peer,ia,ib,edge,sector,cap,adv,limit):
    chosen=set(ia)
    out=[]
    for a,j in enumerate(group):
        eligible=sector[peer]==sector[j]
        c=np.abs(cap[peer]-cap[j])<=limit
        v=np.abs(adv[peer]-adv[j])<=limit
        if a in chosen: reason=0
        elif edge[a].any():reason=1
        elif sector[j]=='未知':reason=5
        elif not eligible.any():reason=5 if (sector[peer]=='未知').any() else 2
        elif not np.isfinite(cap[j]) or not np.isfinite(adv[j]):reason=5
        elif not (eligible&c).any():reason=5 if np.any(eligible&~np.isfinite(cap[peer])) else 3
        elif np.any(eligible&c&~np.isfinite(adv[peer])):reason=5
        else:reason=4
        out.append(reason)
    return out

def main():
    m=market(True);plans,_=selections(m)
    cap,adv,vol,industry,_=covariates(m)
    narrow=pd.read_parquet(original.PRIVATE/'daily_members.parquet').reindex(index=m.days,columns=m.symbols,fill_value=False)
    matched=pd.read_parquet(OLD/'pairs.parquet')
    prior={(lim,int(e)):set(zip(g['head'],g.runner)) for (lim,e),g in matched.groupby(['caliper','entry_idx'])}
    rows=[]
    for e,univ in plans['refit','pool'].items():
        i=e-1;h=plans['refit','head'][e];r=plans['refit','runner'][e]
        info=np.array([cap[i],adv[i],vol[i]]).T
        info[univ]=pd.DataFrame(info[univ]).rank(pct=True).to_numpy()
        c,v,volq=info.T;sec=industry(i)
        ds=np.abs(c[h,None]-c[r]);da=np.abs(v[h,None]-v[r])
        for lim in [.10,.20]:
            edge=(sec[h,None]==sec[r])&(ds<=lim)&(da<=lim)
            a,b=assign(edge,ds+da)
            assert set(zip(m.symbols[h[a]],m.symbols[r[b]]))==prior.get((lim,e),set())
            for arm,g,other,x,y,mask in [('head',h,r,a,b,edge),('runner',r,h,b,a,edge.T)]:
                labels=explain(g,other,x,y,mask,sec,c,v,lim)
                rows.extend((e,j,arm,lim,label,bool(narrow.iat[i,j]),sec[j],c[j],v[j],volq[j]) for j,label in zip(g,labels))
    labels=pd.DataFrame(rows,columns=['entry','stock','arm','caliper','category','in300','sector','cap_pct','adv_pct','vol_pct'])
    labels['symbol']=m.symbols[labels.stock]
    labels['reason']=labels.category.map(dict(enumerate(CATEGORIES)))
    labels.to_parquet(DEST/'a1_targets.parquet',index=False)
    archived=pd.read_parquet(OLD/'daily.parquet').query('model=="refit" and phase==-1 and kind=="strict"')
    ref_stock=pd.read_parquet(OLD/'actual_stock_pnl.parquet')
    monthly_contrib=[];checks=[];group_stats=[]
    for arm in ['head','runner']:
        data=labels.query('arm==@arm')
        for seg,span in enumerate(SEG800,1):
            trace=DEST/f'a1_trace_{arm}_{seg}.parquet'
            with tempfile.NamedTemporaryFile() as temp:
                day=replay(m,pack(m,plans['refit',arm]),span,trace=temp.name)
                tr=read_trace(temp.name);tr.to_parquet(trace,index=False)
            ref=archived.query('bucket==@arm and segment==@seg').set_index('date')
            np.testing.assert_allclose(day[['nav','cash','fee','crossed']],ref.loc[day.index,['nav','cash','fee','crossed']],atol=1e-10,rtol=0)
            # Retained units keep their originating signal. Reductions prorate the old share cohorts.
            buckets={};records=[]
            for t in tr.itertuples(index=False):
                key=t.phase,t.stock
                holdings=buckets.setdefault(key,{})
                actual=sum(holdings.values())
                if abs(actual-t.old_units)>1e-10: raise ArithmeticError((key,actual,t.old_units))
                ratio=min(t.new_units/t.old_units,1.) if t.old_units>0 else 0.
                add=max(t.new_units-t.old_units,0.)
                directed={}
                for orig,units in list(holdings.items()):
                    new=units*ratio
                    overnight=t.overnight*units/t.old_units if t.old_units else 0.
                    intraday=t.intraday*new/t.new_units if t.new_units else 0.
                    fee=(t.fee*units/t.old_units if t.flow<0 and t.old_units else 0.)
                    directed[orig]=[overnight,intraday,fee]
                    if new>0:holdings[orig]=new
                    else:del holdings[orig]
                if add:
                    holdings[t.day]=add
                    vals=directed.setdefault(t.day,[0.,0.,0.])
                    vals[1]+=t.intraday*add/t.new_units
                if t.fee>0 and (t.flow>=0 or not t.old_units):
                    orig=t.day if add else -1
                    directed.setdefault(orig,[0.,0.,0.])[2]+=t.fee
                for orig,(ov,di,fee) in directed.items():
                    if ov or di or fee:records.append((t.day,t.phase,t.stock,orig,ov,di,fee))
            lots=pd.DataFrame(records,columns=['day','sleeve','stock','entry','overnight','intraday','fee'])
            lots['gross']=lots.overnight+lots.intraday
            lots['date']=m.days[lots.day];lots['instrument']=m.symbols[lots.stock]
            ag=lots.groupby(['date','instrument'])[['gross','fee']].sum()
            # Corporate-action aliases can charge a successor; the existing P1 ledger uses the same broker symbols.
            sr=ref_stock.query('bucket==@arm and segment==@seg').groupby(['date','instrument'])[['gross','fee']].sum()
            bysec=ag.subtract(sr,fill_value=0).abs().max()
            y=ag.groupby(level=0).sum().reindex(day.index).fillna(0)
            residual=np.max(abs(y.gross-day.gross_pnl))
            np.testing.assert_allclose(y.gross,day.gross_pnl,atol=1e-10,rtol=0)
            np.testing.assert_allclose(y.fee,day.fee,atol=1e-10,rtol=0)
            checks.append(dict(arm=arm,segment=seg,days=len(day),max_daily_gross_error=residual,stock_gross_error=bysec.gross,stock_fee_error=bysec.fee))
            mo=monthly(day,m.days)
            prev=day.nav.groupby(day.index.to_period('M')).last().shift()
            lots['month']=lots.date.dt.strftime('%Y-%m')
            lots['denominator']=pd.PeriodIndex(lots.month,freq='M').map(prev)
            lots['net']=lots.gross-lots.fee
            lots.to_parquet(DEST/f'a1_cohorts_{arm}_{seg}.parquet',index=False)
            for lim in [.1,.2]:
                a=lots.merge(data.query('caliper==@lim')[['entry','stock','reason','in300','sector','cap_pct','adv_pct']],on=['entry','stock'],how='left',validate='m:1')
                assert (a.reason.notna()|a.entry.eq(-1)).all()
                a['reason']=a.reason.fillna('unallocated_fee')
                a=a[a.month.isin(mo.index)].copy()
                for k in ['gross','net','fee']:a[k]=a[k]/a.denominator
                total=a.groupby(['month','reason'],as_index=False)[['gross','net','fee']].sum()
                np.testing.assert_allclose(total.groupby('month').net.sum(),mo.net,rtol=0,atol=1e-10)
                monthly_contrib.append(total.assign(arm=arm,segment=seg,caliper=lim))
                a['cap_decile']=np.minimum(10,np.ceil(a.cap_pct*10))
                a['adv_decile']=np.minimum(10,np.ceil(a.adv_pct*10))
                group_stats.append(a.groupby(['month','reason','in300','sector','cap_decile','adv_decile'],dropna=False,as_index=False)[['gross','net','fee']].sum().assign(arm=arm,segment=seg,caliper=lim))
    pd.concat(group_stats).to_parquet(DEST/'a1_style_by_month.parquet',index=False)
    mo=pd.concat(monthly_contrib)
    mo.to_csv(DEST/'a1_monthly.csv',index=False)
    both=mo.pivot_table(index=['caliper','segment','month','reason'],columns='arm',values=['net','gross','fee'],fill_value=0)
    diff=(both.xs('head',axis=1,level=1)-both.xs('runner',axis=1,level=1))*1e4
    count=mo.groupby('segment').month.nunique()
    core=diff.groupby(level=['caliper','segment','reason']).sum().div(diff.groupby(level=['caliper','segment','reason']).size().reset_index().segment.map(count).to_numpy(),axis=0)
    core.to_csv(DEST/'a1_summary.csv')
    pd.DataFrame(checks).to_csv(DEST/'a1_checks.csv',index=False)
    print(core,flush=True)
if __name__=='__main__':main()

