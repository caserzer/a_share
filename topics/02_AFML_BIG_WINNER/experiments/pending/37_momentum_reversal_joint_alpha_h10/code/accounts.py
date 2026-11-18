"""Independent fixed-lot H10 engine. No fabricated fills or endpoint replacement."""
import sys
import numpy as np
import pandas as pd
from core import *

class Market:
    def __init__(self):
        c=pd.read_parquet(PRIVATE/'qfq_close.parquet');self.days=c.index;self.symbols=c.columns
        self.n=len(self.symbols);self.c=c.to_numpy(float)
        def read(n):return pd.read_parquet(PRIVATE/(n+'.parquet')).reindex_like(c).to_numpy(float)
        self.o=read('qfq_open');raw=read('open');status=read('opening_trade_status_v2')
        self.members=read('daily_members').astype(bool)
        lim=pd.read_parquet(PRIVATE/'limits/daily.parquet').copy()
        lim['instrument']=lim.ts_code.str[-2:]+lim.ts_code.str[:6];lim['date']=pd.to_datetime(lim.trade_date)
        assert not lim.duplicated(['date','instrument']).any()
        up=lim.pivot(index='date',columns='instrument',values='up_limit').reindex_like(c).to_numpy(float)
        down=lim.pivot(index='date',columns='instrument',values='down_limit').reindex_like(c).to_numpy(float)
        known=np.isfinite(raw)&(raw>0)&np.isfinite(self.o)&(self.o>0)&np.isfinite(up)&np.isfinite(down)&(up>down)&(status==1)
        self.buy=known&(raw<up-1e-6);self.sell=known&(raw>down+1e-6)
        ev=pd.read_parquet(PRIVATE/'suspensions/daily.parquet')
        ev=ev.loc[ev.suspend_type.eq('S')&(ev.suspend_timing.isna()|ev.suspend_timing.eq(''))]
        suspended=np.zeros_like(self.c,dtype=bool)
        for r in ev.itertuples():
            d=pd.Timestamp(r.trade_date);s=r.ts_code[-2:]+r.ts_code[:6]
            if d in self.days and s in self.symbols:suspended[self.days.get_loc(d),self.symbols.get_loc(s)]=True
        self.marks={};records=[]
        for mode,haircut in [('strict',None),('flat',0.),('haircut20',.2)]:
            cm=self.c.copy();om=self.o.copy()
            if haircut is not None:
                for j,symbol in enumerate(self.symbols):
                    last=np.nan;age=0
                    for i,d in enumerate(self.days):
                        if np.isfinite(self.c[i,j]):last=self.c[i,j];age=0;continue
                        age+=1
                        if suspended[i,j] and np.isfinite(last) and age<=20:
                            cm[i,j]=last*(1-haircut)
                            if not np.isfinite(om[i,j]):om[i,j]=cm[i,j]
                            records.append(dict(mode=mode,date=d,instrument=symbol,prior_close=last,age=age,mark=cm[i,j]))
            self.marks[mode]=(om,cm)
        pd.DataFrame(records).to_csv(OUT/'suspension_marks.csv',index=False)

def buy_amounts(weights,cash,locked_value,buy_fee):
    """Post-fee target fractions; cash shortage scales all permissible buys together."""
    total=float(np.sum(weights))
    if total<=0:return np.zeros_like(weights)
    value=total*(cash+locked_value)/(1+buy_fee*total)
    value=min(value,cash/(1+buy_fee))
    return weights*(value/total)

def make_targets():
    pred=pd.read_parquet(CACHE/'predictions.parquet');rows=[];rankrows=[];availability=[]
    for (scheme,offset,date),g in pred.groupby(['scheme','offset','signal_date']):
        ids=SCORES if scheme=='expanding' and offset==0 else ['A_R','J_R']
        for model in ids:
            z=g.loc[g[model].notna()].copy()
            if len(z)<100:
                availability.append(dict(scheme=scheme,offset=offset,signal_date=date,model=model,available=False));continue
            z['decile']=assign_deciles(z,model);z['model']=model;z['score']=z[model]
            rankrows.append(z[['scheme','offset','signal_date','entry_date','exit_date','fold','fit_cutoff','instrument','state','model','score','decile']])
            availability.append(dict(scheme=scheme,offset=offset,signal_date=date,model=model,available=True))
            groups=range(1,11) if model in ['A_R','J_R'] and scheme=='expanding' and offset==0 else [10]
            specs=[('D'+str(d),z.loc[z.decile==d],None) for d in groups]
            if model in ['A_R','J_R'] and scheme=='expanding' and offset==0:
                specs.append(('TOP20',z.loc[z.decile>=9],None))
                count=int(z.decile.eq(10).sum());q,r=divmod(count,4);chosen=[]
                for k,state in enumerate(STATES):
                    eligible=z.loc[z.state.eq(state)].sort_values([model,'instrument'],ascending=[False,False])
                    chosen.append(eligible.head(q+(k<r)))
                specs.append(('BALANCED',pd.concat(chosen),count))
            for portfolio,chosen,denom in specs:
                budget=1/(denom if denom is not None else len(chosen))
                for r in chosen.itertuples():
                    rows.append(dict(scheme=scheme,offset=offset,signal_date=date,entry_date=r.entry_date,exit_date=r.exit_date,
                                     entry_idx=r.entry_idx,exit_idx=r.exit_idx,model=model,portfolio=portfolio,instrument=r.instrument,
                                     state=r.state,weight=budget,score=getattr(r,model),global_decile=r.decile))
        if scheme=='expanding' and offset==0:
            for r in g.itertuples():rows.append(dict(scheme=scheme,offset=offset,signal_date=date,entry_date=r.entry_date,exit_date=r.exit_date,
                entry_idx=r.entry_idx,exit_idx=r.exit_idx,model='EW',portfolio='EW',instrument=r.instrument,state=r.state,weight=1/len(g),score=np.nan,global_decile=np.nan))
    target=pd.DataFrame(rows);target.to_parquet(CACHE/'targets.parquet',index=False)
    target.to_csv(OUT/'all_target_holdings.csv.gz',index=False,compression='gzip')
    rankings=pd.concat(rankrows,ignore_index=True);rankings.to_parquet(CACHE/'rankings.parquet',index=False)
    rankings.to_csv(OUT/'all_rankings.csv.gz',index=False,compression='gzip')
    pd.DataFrame(availability).to_csv(OUT/'prediction_availability.csv',index=False)
    record_stage('selection_frozen',[CACHE/'targets.parquet',CACHE/'rankings.parquet',OUT/'prediction_availability.csv'],dict(selection_reads_labels=False))
    print('frozen selection',len(target),'rows',flush=True)

def event(market,selection,bf,sf):
    e=int(selection.entry_idx.iloc[0]);x=int(selection.exit_idx.iloc[0]);idx=market.symbols.get_indexer(selection.instrument)
    weights=selection.weight.to_numpy(float);buy=market.buy[e,idx]&market.members[e-1,idx]
    v=buy_amounts(weights*buy,1.,0.,bf);invested=v>0
    cash=1-float(v.sum())*(1+bf)
    can_exit=market.sell[x,idx];complete=bool(np.all(can_exit[invested]))
    net=np.nan
    if complete:net=cash+float(np.sum(v[invested]*market.o[x,idx[invested]]/market.o[e,idx[invested]]))*(1-sf)-1
    mark=np.nan
    if np.isfinite(market.o[x,idx[invested]]).all():mark=cash+float(np.sum(v[invested]*market.o[x,idx[invested]]/market.o[e,idx[invested]]))-1
    detail=selection[['instrument','state','weight']].copy()
    detail['buy_filled']=buy;detail['entry_value']=v;detail['exit_allowed']=can_exit
    detail['entry_price']=market.o[e,idx];detail['exit_price']=market.o[x,idx]
    detail['net_stock_profit']=np.where(invested&can_exit,v*(market.o[x,idx]/market.o[e,idx]*(1-sf)-1-bf),np.where(~invested,0.,np.nan))
    return dict(net_return=net,mark_return_before_exit_fee=mark,complete_exit=complete,
                any_entry=bool(invested.any()),full_entry=bool(buy.all()),planned_weight=float(weights.sum()),
                entry_weight=float(v.sum()),selected=len(idx),bought=int(invested.sum()),blocked_exit_count=int((invested&~can_exit).sum()),
                blocked_exit_entry_budget=float(v[invested&~can_exit].sum())),detail

def account(market,targets,end_idx,mode,bf,sf,key,store_holdings=True):
    """One synthetic lot per instrument; a blocked expired lot cannot be topped up."""
    om,cm=market.marks[mode];n=market.n
    plans={int(e):g for e,g in targets.groupby('entry_idx') if e<end_idx}
    if not plans:return [],[],[],dict(account=key,reason='NO_TARGETS',valuation_complete=False)
    first=min(plans);units=np.zeros(n);due=np.full(n,-1);origin=np.full(n,-1);cash=1.
    prev_nav=1.;prev_mark=np.zeros(n);daily=[];orders=[];holdings=[];failed=None
    for i in range(first,end_idx+1):
        old=units.copy();cash_before=cash;buy_value=0.;sell_value=0.;fees=0.;blocked_sells=0;blocked_buys=0
        expired=(units>0)&(due<=i)
        if expired.any() or i in plans or i==end_idx:
            held=units>0
            if np.any(held&~np.isfinite(om[i])):
                failed=dict(date=market.days[i],reason='HELD_OPEN_VALUATION_UNKNOWN',instruments='|'.join(market.symbols[held&~np.isfinite(om[i])]))
                break
            sold=expired&market.sell[i];blocked_sells=int((expired&~market.sell[i]).sum())
            for j in np.flatnonzero(expired):
                value=units[j]*market.o[i,j] if sold[j] else 0.
                orders.append(dict(date=market.days[i],instrument=market.symbols[j],side='SELL' if sold[j] else 'SELL_BLOCKED',
                                   value=value,fee=value*sf,units=units[j] if sold[j] else 0.,entry_date=market.days[origin[j]],
                                   planned_exit=market.days[due[j]],actual_age=i-origin[j],quote=market.o[i,j]))
            sell_value=float(np.sum(units[sold]*market.o[i,sold]));fees+=sell_value*sf
            cash+=sell_value*(1-sf);units[sold]=0;due[sold]=-1;origin[sold]=-1
            if i in plans:
                g=plans[i];idx=market.symbols.get_indexer(g.instrument);w=np.zeros(n);w[idx]=g.weight.to_numpy(float)
                allowed=market.buy[i]&market.members[i-1]&(units==0)
                blocked_buys=int(((w>0)&~allowed).sum())
                locked=float(np.sum(units[units>0]*om[i,units>0]))
                values=buy_amounts(w*allowed,cash,locked,bf)
                for j in np.flatnonzero(w>0):
                    ok=values[j]>0
                    orders.append(dict(date=market.days[i],instrument=market.symbols[j],side='BUY' if ok else 'BUY_BLOCKED',
                                       value=values[j],fee=values[j]*bf,units=values[j]/market.o[i,j] if ok else 0.,
                                       entry_date=market.days[i],planned_exit=market.days[i+10],actual_age=0,quote=market.o[i,j]))
                bought=values>0;units[bought]=values[bought]/market.o[i,bought];due[bought]=i+10;origin[bought]=i
                buy_value=float(values.sum());fees+=buy_value*bf;cash-=buy_value*(1+bf)
                if abs(cash)<1e-12:cash=0.
                assert cash>=-1e-10
        mark=om[i] if i==end_idx else cm[i]
        held=units>0
        if np.any(held&~np.isfinite(mark)):
            failed=dict(date=market.days[i],reason='HELD_CLOSE_VALUATION_UNKNOWN',instruments='|'.join(market.symbols[held&~np.isfinite(mark)]));break
        values=np.zeros(n);values[held]=units[held]*mark[held]
        nav=cash+float(values.sum())
        oldvalue=float(np.sum(old[old>0]*prev_mark[old>0]))
        pnl=float(values.sum())-oldvalue+sell_value-buy_value
        residual=(nav-prev_nav)-(pnl-fees)
        assert abs(residual)<1e-9
        daily.append(dict(date=market.days[i],nav=nav,return_=nav/prev_nav-1,cash=cash,stock_weight=float(values.sum()/nav),
                          buy=buy_value,sell=sell_value,fees=fees,pnl=pnl,accounting_residual=residual,holdings=int(held.sum()),
                          max_stock_weight=float(values.max()/nav),hhi=float(np.sum((values/nav)**2)),
                          overdue_count=int((held&(due<=i)).sum()),overdue_weight=float(values[held&(due<=i)].sum()/nav),
                          blocked_buys=blocked_buys,blocked_sells=blocked_sells,terminal_open=i==end_idx))
        if store_holdings:
            for j in np.flatnonzero(held):holdings.append((market.days[i],market.symbols[j],units[j],mark[j],values[j]/nav,market.days[origin[j]],market.days[due[j]],i-origin[j]))
        prev_nav=nav;prev_mark=np.where(np.isfinite(mark),mark,0.)
    info=dict(account=key,start=market.days[first],planned_end=market.days[end_idx],actual_end=daily[-1]['date'] if daily else None,
              valuation_complete=failed is None,terminal_liquidated=bool(not (units>0).any()) if failed is None else False,
              failure=failed,days=len(daily))
    return daily,orders,holdings,info

def run():
    verify_freeze();market=Market();target=pd.read_parquet(CACHE/'targets.parquet')
    plans=pd.read_csv(OUT/'calendar.csv',parse_dates=['signal_date','entry_date','exit_date'])
    event_rows=[];event_details=[]
    for key,g in target.groupby(['scheme','offset','model','portfolio','entry_idx']):
        scheme,offset,model,portfolio,e=key;x=int(g.exit_idx.iloc[0])
        if x>=len(market.days) or g.entry_date.iloc[0]<pd.Timestamp('2021-01-11'):continue
        costs=['main','zero','stress'] if portfolio in ['D10','EW'] else ['main']
        for cost in costs:
            cf=config()['accounts']['costs_bps'][cost];bf=cf['buy']/10000;sf=cf['sell']/10000
            r,details=event(market,g,bf,sf)
            meta=dict(scheme=scheme,offset=offset,model=model,portfolio=portfolio,cost=cost,signal_date=g.signal_date.iloc[0],entry_date=g.entry_date.iloc[0],exit_date=g.exit_date.iloc[0])
            event_rows.append(meta|r)
            if cost=='main':
                for k,v in meta.items():details[k]=v
                event_details.append(details)
    events=pd.DataFrame(event_rows);events.to_csv(OUT/'events.csv',index=False)
    pd.concat(event_details,ignore_index=True).to_parquet(CACHE/'event_stock_details.parquet',index=False)
    pd.concat(event_details,ignore_index=True).to_csv(OUT/'event_stock_details.csv.gz',index=False,compression='gzip')
    infos=[];summaries=[];periods=[];all_daily=[]
    ledger=CACHE/'ledgers';ledger.mkdir(exist_ok=True)
    for (scheme,offset,model,portfolio),g in target.groupby(['scheme','offset','model','portfolio']):
        complete=plans.loc[(plans.offset==offset)&plans.exit_date.notna()&(plans.entry_date>='2021-01-11')]
        costs=['main','zero','stress'] if portfolio in ['D10','EW'] else ['main']
        for scope,limit in [('primary',pd.Timestamp('2025-03-03')),('extended',pd.Timestamp('2026-10-21'))]:
            endpoint=int(complete.loc[complete.exit_date<=limit,'exit_idx'].max())
            for cost in costs:
                # Full strict/flat branches for all registered accounts; haircut for main top portfolios.
                modes=['strict','flat']+(['haircut20'] if cost=='main' and portfolio in ['D10','EW'] else [])
                for mode in modes:
                    name=f'{scheme}_o{offset}_{model}_{portfolio}_{scope}_{cost}_{mode}'
                    cf=config()['accounts']['costs_bps'][cost]
                    detail=(cost=='main' and mode=='flat')
                    daily,orders,holds,info=account(market,g,endpoint,mode,cf['buy']/10000,cf['sell']/10000,name,detail)
                    meta=dict(account=name,scheme=scheme,offset=offset,model=model,portfolio=portfolio,scope=scope,cost=cost,valuation=mode)
                    info.update(meta);infos.append(info)
                    df=pd.DataFrame(daily)
                    if df.empty:continue
                    for k,v in meta.items():df[k]=v
                    all_daily.append(df)
                    if detail:
                        pd.DataFrame(orders).to_parquet(ledger/(name+'_orders.parquet'),index=False)
                        pd.DataFrame(holds,columns=['date','instrument','units','mark','weight','entry_date','planned_exit','age']).to_parquet(ledger/(name+'_holdings.parquet'),index=False)
                    nav=df.nav.to_numpy();ret=df.return_.to_numpy();dd=nav/np.maximum.accumulate(np.r_[1.,nav])[1:]-1
                    summaries.append(meta|dict(valuation_complete=info['valuation_complete'],terminal_liquidated=info['terminal_liquidated'],
                        start=info['start'],end=info['actual_end'],days=len(df),total_return=nav[-1]-1,
                        cagr=nav[-1]**(252/max(1,endpoint-market.days.get_loc(pd.Timestamp(info['start']))))-1 if info['valuation_complete'] else np.nan,
                        max_drawdown=float(dd.min()),annual_vol=float(np.std(ret,ddof=1)*np.sqrt(252)) if len(ret)>1 else np.nan,
                        average_stock_weight=df.stock_weight.mean(),max_stock_weight=df.max_stock_weight.max(),average_hhi=df.hhi.mean(),
                        fees=float(df.fees.sum()),buy_value=float(df.buy.sum()),sell_value=float(df.sell.sum()),overdue_days=int(df.overdue_count.gt(0).sum()),
                        blocked_buys=int(df.blocked_buys.sum()),blocked_sells=int(df.blocked_sells.sum())))
                    if detail:
                        for freq in ['Y','M']:
                            for period,h in df.groupby(pd.to_datetime(df.date).dt.to_period(freq)):
                                periods.append(meta|dict(frequency=freq,period=str(period),net_return=float(np.prod(1+h.return_)-1),
                                                        average_stock_weight=h.stock_weight.mean(),fees=h.fees.sum(),days=len(h)))
        print('accounts',scheme,offset,model,portfolio,flush=True)
    pd.DataFrame(summaries).to_csv(OUT/'accounts.csv',index=False)
    pd.DataFrame(periods).to_csv(OUT/'periods.csv',index=False)
    combined=pd.concat(all_daily,ignore_index=True);combined.to_parquet(CACHE/'daily_accounts.parquet',index=False)
    combined.to_csv(OUT/'daily_accounts.csv.gz',index=False,compression='gzip')
    dump(MAN/'account_status.json',clean(infos))
    record_stage('accounts',[OUT/'accounts.csv',OUT/'events.csv',OUT/'periods.csv',CACHE/'daily_accounts.parquet',MAN/'account_status.json'],
                 dict(branches=len(infos),event_rows=len(events)))
    print('all accounts',len(infos),'events',len(events),flush=True)

if __name__=='__main__': {'select':make_targets,'run':run}[sys.argv[1]]()
