"""Original E1 accounting, fixed-state timing and residual diagnostics. No fitting/search."""
import json,sys
from datetime import datetime,timezone
import numpy as np
import pandas as pd
from common import EP,OUT,PRIVATE,sha,save_json
from backtest import Inputs
from suspension_sensitivity import marks
from portfolio import trade
from e1_return_attribution import ORIGINAL,END,benchmark,daily_returns,log_link,wealth_scale,industry_map
from alpha_economics import STYLES,matrix
from alpha_falsification import project,rankcorr
from e1_mechanism import bootstrap
from e1_engineered_ablation import holm

RUN='e1_timing_mechanism_20261117';D=OUT/'diagnostics'/RUN;L=PRIVATE/RUN;R=EP/'reports'/RUN
P=PRIVATE/'e1_alpha_mechanism_20261117/universe_audit.parquet'
T=PRIVATE/'e1_return_attribution_20261117/control_targets.parquet'
DELAY=OUT/'diagnostics/q5_phase_delay_control_20261116/accounts/E1__main'
SCHEDULE=OUT/'sensitivity/q5_controls_phases_buffers_20261116/schedule.csv'
COSTS={'main':(.001,.002),'zero':(0.,0.),'stress':(.003,.008)}
STATES=['UP_DOWN','UP_UP','DOWN_DOWN','DOWN_UP','ZERO','UNKNOWN']
CHECKS=[]
def check(name,ok):
 assert bool(ok),name
 CHECKS.append(dict(check=name,passed=True))
def dump(f,name,private=False):
 if private:f.to_parquet(L/(name+'.parquet'),index=False)
 else:f.to_csv(D/(name+'.csv'),index=False)
def state(t,s):
 t=np.asarray(t);s=np.asarray(s);v=np.full(t.shape,'UNKNOWN',dtype=object);ok=np.isfinite(t)&np.isfinite(s)
 v[ok&((t==0)|(s==0))]='ZERO'
 for a,b,label in [(1,-1,'UP_DOWN'),(1,1,'UP_UP'),(-1,-1,'DOWN_DOWN'),(-1,1,'DOWN_UP')]:v[ok&(a*t>0)&(b*s>0)]=label
 return v

def freeze():
 if (D/'freeze.json').exists():raise RuntimeError('Already frozen')
 D.mkdir(parents=True);L.mkdir(parents=True)
 files=[P,T,SCHEDULE,R/'PROTOCOL.md']
 for root in [ORIGINAL,DELAY]:
  rec=json.loads(root.with_suffix('.json').read_text());files += [root.with_suffix('.json'),root.with_suffix('.csv'),rec['orders_path'],rec['holdings_path']]
 files += [PRIVATE/(x+'.parquet') for x in ['qfq_close','qfq_open','open','opening_trade_status_v2','daily_members','industry','limits/daily','suspensions/daily','weights/snapshots']]
 files += [PRIVATE/'net_excess_20261116/H00300.CSI.json',PRIVATE/'net_excess_20261116/H00300.CSI.receipt.json']
 sources=[EP/'src'/x for x in ['e1_timing_mechanism.py','backtest.py','portfolio.py','suspension_sensitivity.py','e1_return_attribution.py','alpha_economics.py','alpha_falsification.py','e1_mechanism.py','e1_engineered_ablation.py']]
 save_json(D/'freeze.json',dict(created_at=datetime.now(timezone.utc).isoformat(),prior_results_seen=True,new_results_seen=False,files=[dict(path=str(x),sha256=sha(x)) for x in files+sources]))
 print('frozen',flush=True)
def verify(selection=False):
 for x in json.loads((D/'freeze.json').read_text())['files']:assert sha(x['path'])==x['sha256'],x['path']
 if selection:
  for x in json.loads((D/'selection.json').read_text())['files']:assert sha(x['path'])==x['sha256']

def prepare():
 verify();assert not (D/'selection.json').exists()
 inp=Inputs();raw=inp.c.copy();targets=pd.read_parquet(T);targets=targets[targets.control.eq('E1_REPLAY')].drop(columns='control')
 dates=sorted(targets.signal_date.unique());panel=pd.read_parquet(P);panel=panel[panel.signal_date.isin(dates)].copy();allstates=[];peers=[]
 for date in dates:
  date=pd.Timestamp(date);si=inp.days.get_loc(date)
  trend=raw[si-5]/raw[si-60]-1;short=raw[si]/raw[si-5]-1;one=raw[si]/raw[si-1]-1
  a=pd.DataFrame(dict(signal_date=date,instrument=inp.symbols,trend=trend,short=short,one=one,state=state(trend,short),industry=industry_map(inp,date).to_numpy()))
  a['REV']=-(a.groupby('industry').one.rank(pct=True)+a.groupby('industry').short.rank(pct=True))/2
  g=panel[panel.signal_date.eq(date)].copy();g=g.merge(a[['instrument','trend','short','state','REV']],on='instrument',validate='one_to_one')
  g['score_residual']=np.nan;complete=np.isfinite(g[STYLES+['E1']]).all(axis=1)&g.industry.ne('UNKNOWN')
  c=g[complete]
  if len(c)>=100:
   _,_,x=matrix(c);fit,res,_,rank=project(x,c.E1.to_numpy())
   if len(c)-rank>=50:g.loc[c.index,'score_residual']=res
  a=a.merge(g[['instrument','E1','score_residual']+STYLES],on='instrument',how='left',validate='one_to_one')
  target=targets[targets.signal_date.eq(date)].set_index('instrument').weight
  a['target_weight']=a.instrument.map(target).fillna(0)
  a['raw_q5']=a.target_weight>0
  # Freeze all peer memberships before future prices are read by evaluation.
  for ind,h in a[a.E1.notna()&a.industry.ne('UNKNOWN')].groupby('industry'):
   selected=h[h.raw_q5];pool=h[~h.raw_q5]
   sd=h[['short','trend']+STYLES].std(ddof=0).replace(0,1)
   for row in selected.itertuples():
    for tier,cols in [('industry',[]),('price',['short','trend']),('all13',['short','trend']+STYLES)]:
     ok=pd.Series(True,index=pool.index)
     for col in cols:ok &= (pool[col]-getattr(row,col)).abs().le(.25*sd[col])
     match=pool[ok]
     peers.append(dict(signal_date=date,instrument=row.instrument,tier=tier,weight=row.target_weight,n_peers=len(match),peers='|'.join(match.instrument),status='OK' if len(match) else 'NO_SUPPORT'))
  allstates.append(a)
 full=pd.concat(allstates,ignore_index=True);dump(full,'states',True);dump(targets,'targets',True);dump(pd.DataFrame(peers),'peers',True)
 schedule=pd.read_csv(SCHEDULE,parse_dates=['signal_date','execution_date']);schedule=schedule[schedule.frequency.eq('1m')&schedule.phase.eq(2)];phase2=schedule.assign(month=schedule.signal_date.dt.to_period('M').astype(str)).set_index('month')
 events=[]
 for date in dates:
  date=pd.Timestamp(date);ei=inp.days.get_loc(date)+1;m=str(date.to_period('M'))
  events.append(dict(signal_date=date,entry_date=inp.days[ei],month=m,phase2_date=phase2.loc[m,'execution_date'] if m in phase2.index else pd.NaT))
 dump(pd.DataFrame(events),'schedule')
 files=[L/(x+'.parquet') for x in ['states','targets','peers']]+[D/'schedule.csv']
 save_json(D/'selection.json',dict(created_at=datetime.now(timezone.utc).isoformat(),outcomes_seen=False,files=[dict(path=str(x),sha256=sha(x)) for x in files]))
 print('selection sealed',len(events),len(full),flush=True)

def load_account(root):
 rec=json.loads(root.with_suffix('.json').read_text());f=pd.read_csv(root.with_suffix('.csv'),parse_dates=['date']).set_index('date').loc[:END]
 o=pd.read_parquet(rec['orders_path']);o=o[o.date<=END].copy();h=pd.read_parquet(rec['holdings_path']);h=h[h.date<=END].copy()
 return f,o,h

def account_parts(root):
 a,o,h=load_account(root);h['value']=h.synthetic_units*h.valuation_close
 v=h.pivot(index='date',columns='instrument',values='value').reindex(a.index).fillna(0)
 o['trade_cash']=(o.units_after-o.units_before)*o.qfq_open
 traded=o.groupby(['date','instrument']).trade_cash.sum().unstack().reindex(index=a.index,columns=v.columns).fillna(0)
 pnl=v-v.shift(fill_value=0)-traded;prev=a.nav.shift(fill_value=1.);gross=pnl.div(prev,axis=0);gross['__FEES__']=-a.fees/prev
 check(str(root.name)+'_absolute_reconcile',np.allclose(gross.sum(axis=1),daily_returns(a.nav),atol=1e-10))
 weights=v.shift(fill_value=0).div(prev,axis=0);weights['__CASH__']=1-weights.sum(axis=1)
 return a,o,h,pnl,gross,weights

def ledger():
 verify(True);inp=Inputs();s=pd.read_parquet(L/'states.parquet').set_index(['signal_date','instrument']);sched=pd.read_csv(D/'schedule.csv',parse_dates=['signal_date','entry_date']);dates=sched.entry_date.to_numpy();signals=sched.signal_date.to_numpy()
 a,o,h,pnl,gross,w=account_parts(ORIGINAL);b=benchmark(a.index);rp=daily_returns(a.nav);rb=daily_returns(b)
 active=gross.subtract(w.mul(rb,axis=0),fill_value=0);linked=active.mul(log_link(rp,rb),axis=0)*wealth_scale(a.nav.iloc[-1],b.iloc[-1]);abslinked=gross.mul(log_link(rp,np.zeros(len(rp))),axis=0)*wealth_scale(a.nav.iloc[-1],1.)
 check('original_active_terminal',np.isclose(linked.to_numpy().sum(),100*(a.nav.iloc[-1]-b.iloc[-1]),atol=1e-9))
 # Actions describe actual latest decision, carried through the monthly interval.
 actions={};buydates={};rows=[]
 ordergroups={d:g for d,g in o.groupby('date')}
 for date in a.index:
  signal=pd.Timestamp(signals[np.searchsorted(dates,np.datetime64(date),side='right')-1])
  if date in ordergroups:
   for r in ordergroups[date].itertuples():
    d=r.units_after-r.units_before
    cat=('entry' if r.units_before<=1e-12 else 'top_up') if d>1e-12 else (('exit' if r.units_after<=1e-12 else 'trim') if d< -1e-12 else 'unchanged')
    actions[r.instrument]=cat
    if cat=='entry':buydates[r.instrument]=date
  for code in linked.columns:
   value=linked.at[date,code];capital=w.at[date,code] if code in w else 0.;absolute=float(abslinked.at[date,code]) if code in abslinked else 0.
   if value==0 and capital==0 and absolute==0:continue
   meta=s.loc[(signal,code)] if (signal,code) in s.index else None
   rows.append(dict(date=date,month=str(date.to_period('M')),year=date.year,signal_date=signal,instrument=code,state=code if code.startswith('__') else (meta.state if meta is not None else 'UNKNOWN'),industry=code if code.startswith('__') else (meta.industry if meta is not None else 'UNKNOWN'),action=actions.get(code,'none'),original_buy_date=buydates.get(code,pd.NaT),wealth_contribution=value,absolute_linked_contribution=absolute,absolute_cash_pnl_per100=(pnl.at[date,code]*100 if code in pnl else (-a.at[date,'fees']*100 if code=='__FEES__' else 0)),capital_days=capital,absolute_daily_return=float(gross.at[date,code]) if code in gross else 0.))
 detail=pd.DataFrame(rows);dump(detail,'ledger_detail',True)
 for keys,name in [(['state'],'01_original_state'),(['year','state'],'original_year_state'),(['month','state'],'original_month_state'),(['industry','state'],'original_industry_state'),(['instrument','state'],'original_stock_state'),(['action','state'],'original_action_state')]:
  z=detail.groupby(keys,as_index=False)[['wealth_contribution','absolute_linked_contribution','absolute_cash_pnl_per100','capital_days','absolute_daily_return']].sum();z['mean_daily_absolute_per_capital']=z.absolute_daily_return/z.capital_days.replace(0,np.nan);dump(z,name)
 # The above capital-normalization must use return components rather than varying account units.
 # Preserve cash pnl and capital-days separately; normalized metric corrected to additive daily returns.
 k=s.reset_index();budget=k[k.target_weight>0].groupby('state').agg(total_target_budget=('target_weight','sum'),target_positions=('instrument','size')).reset_index();budget['mean_target_budget']=budget.total_target_budget/len(sched);dump(budget,'target_budget')
 da,do,dh,dp,dg,dw=account_parts(DELAY);check('continuous_dates_equal',a.index.equals(da.index))
 dr=daily_returns(da.nav);delta=gross.subtract(dg,fill_value=0);gap=delta.mul(log_link(rp,dr),axis=0)*wealth_scale(a.nav.iloc[-1],da.nav.iloc[-1])
 check('timing_gap_terminal',np.isclose(gap.to_numpy().sum(),100*(a.nav.iloc[-1]-da.nav.iloc[-1]),atol=1e-9))
 rows=[]
 for date,row in gap.iterrows():
  signal=pd.Timestamp(signals[np.searchsorted(dates,np.datetime64(date),side='right')-1])
  for code,val in row.items():
   if val==0:continue
   meta=s.loc[(signal,code)] if (signal,code) in s.index else None
   rows.append(dict(date=date,month=str(date.to_period('M')),instrument=code,state=code if code.startswith('__') else (meta.state if meta is not None else 'UNKNOWN'),wealth_gap=val))
 g=pd.DataFrame(rows);dump(g,'continuous_gap_detail',True);dump(g.groupby('state',as_index=False).wealth_gap.sum(),'continuous_gap_state');dump(g.groupby(['month','state'],as_index=False).wealth_gap.sum(),'continuous_gap_month_state')
 save_json(D/'ledger_validation.json',dict(checks=CHECKS,status='PASS',original_terminal=float(a.nav.iloc[-1]),index_terminal=float(b.iloc[-1]),delayed_terminal=float(da.nav.iloc[-1]),note='Existing delayed account drops later nonmembers and reweights; exact fixed weights event differs explicitly'))
 print('ledger done',flush=True)

def vector(inp,g):
 v=np.zeros(inp.n+1);v[inp.symbols.get_indexer(g.instrument)]=g.weight;return v

def enter(inp,ei,target,bf,sf):
 # At delayed date membership is known as of the previous market close.
 member,_,_,_,_,buy,sell,_=inp.context(ei-1,ei)
 return trade(np.zeros(inp.n),1.,inp.o[ei],target,buy&member,sell,bf,sf)

def endpoint(inp,ei,j,u,c,bf,sf):
 held=u>1e-12
 if j>=len(inp.days) or inp.days[j]>END:return dict(mark=np.nan,net=np.nan,reason='END_OUTSIDE_PRIMARY'),None,None
 if np.any(held&~np.isfinite(inp.o[j])) or np.any(~np.isfinite(inp.c[ei:j,held])):return dict(mark=np.nan,net=np.nan,reason='HELD_VALUATION_UNKNOWN'),None,None
 value=u*np.nan_to_num(inp.o[j]);mark=c+value.sum();_,_,_,_,_,_,sell,_=inp.context(j-1,j)
 left,terminal,info=trade(u.copy(),c,inp.o[j],np.r_[np.zeros(inp.n),1.],np.zeros(inp.n,bool),sell,bf,sf)
 ok=not np.any(left>1e-12)
 return dict(mark=mark-1,net=terminal-1 if ok else np.nan,reason='OK' if ok else 'EXIT_BLOCKED',unsold=float(left@np.nan_to_num(inp.o[j]))),value,sell

def events():
 verify(True);inp=Inputs();marks(inp,0.);targets=pd.read_parquet(L/'targets.parquet');states=pd.read_parquet(L/'states.parquet');sched=pd.read_csv(D/'schedule.csv',parse_dates=['signal_date','entry_date','phase2_date']);rows=[];sr=[];paths=[]
 for ev in sched.itertuples():
  ei=inp.days.get_loc(ev.entry_date);tar=vector(inp,targets[targets.signal_date.eq(ev.signal_date)]);meta=states[states.signal_date.eq(ev.signal_date)].set_index('instrument').reindex(inp.symbols)
  delays={'immediate':ei,'plus1':ei+1,'plus3':ei+3,'plus5':ei+5,'phase2':inp.days.get_loc(ev.phase2_date) if pd.notna(ev.phase2_date) else None}
  for cost,(bf,sf) in COSTS.items():
   for tag,di in delays.items():
    if di is None:
     for clock in ['equal_horizon','common_exit']:
      for horizon in [5,10,20]:rows.append(dict(signal_date=ev.signal_date,month=ev.month,cost=cost,delay=tag,clock=clock,horizon=horizon,mark=np.nan,net=np.nan,reason='NO_PHASE2'))
     continue
    u,c,info=enter(inp,di,tar,bf,sf);entrypx=np.nan_to_num(inp.o[di]);spent=u*entrypx;entryfees=spent*bf
    check(f'{ev.month}_{cost}_{tag}_self_finance',abs(c+spent.sum()+entryfees.sum()-1)<1e-10)
    if cost=='main':
     for j in range(di,min(di+21,len(inp.days))):
      out,_,_=endpoint(inp,di,j,u,c,bf,sf);paths.append(dict(signal_date=ev.signal_date,delay=tag,age=j-di,**out))
    for clock in ['equal_horizon','common_exit']:
     for horizon in [5,10,20]:
      j=(di if clock=='equal_horizon' else ei)+horizon
      base=dict(signal_date=ev.signal_date,month=ev.month,cost=cost,delay=tag,clock=clock,horizon=horizon,entry_date=inp.days[di],exit_date=inp.days[j] if j<len(inp.days) else pd.NaT,entry_fees=info['fees'],unfilled_buy=info['unfilled_buy'],entry_cash=c)
      if j<=di:rows.append(base|dict(mark=np.nan,net=np.nan,reason='EXIT_NOT_AFTER_ENTRY'));continue
      out,value,sell=endpoint(inp,di,j,u,c,bf,sf);rows.append(base|out)
      if value is None:continue
      effects=value-spent-entryfees;neteffects=effects-value*sf
      check(f'{ev.month}_{cost}_{tag}_{clock}_{horizon}_pnl',np.isclose(effects.sum(),out['mark'],atol=1e-10))
      for st in STATES:
       ids=meta.state.eq(st).to_numpy();known=np.isfinite(out['net'])
       sr.append(base|dict(state=st,budget=float(tar[:-1][ids].sum()),mark=float(effects[ids].sum()),net=float(neteffects[ids].sum()) if known else np.nan))
      # Frozen state split of immediate vs delayed: exact shared-endpoint accounting.
      if cost=='main' and tag!='immediate' and clock=='common_exit':
       u0,c0,_=enter(inp,ei,tar,bf,sf);early,ev0,_=endpoint(inp,ei,di,u0,c0,bf,sf);last,v0,_=endpoint(inp,ei,j,u0,c0,bf,sf)
       if ev0 is not None and v0 is not None:
        spent0=u0*np.nan_to_num(inp.o[ei]);earlyeff=ev0-spent0*(1+bf);shared=(v0-ev0)-(value-spent);gap=(v0-spent0*(1+bf))-effects
        check(f'{ev.month}_{tag}_{horizon}_segments',np.allclose(earlyeff+shared+entryfees,gap,atol=1e-10))
        for st in STATES:
         ids=meta.state.eq(st).to_numpy();paths.append(dict(signal_date=ev.signal_date,delay=tag,horizon=horizon,state=st,early=float(earlyeff[ids].sum()),shared=float(shared[ids].sum()),delayed_entry_fees=float(entryfees[ids].sum()),gap=float(gap[ids].sum())))
  print('events',ev.month,flush=True)
 dump(pd.DataFrame(rows),'events');dump(pd.DataFrame(sr),'event_states');dump(pd.DataFrame(paths),'event_paths');save_json(D/'event_validation.json',dict(status='PASS',checks=CHECKS))

def actions():
 verify(True);inp=Inputs();marks(inp,0.);targets=pd.read_parquet(L/'targets.parquet');states=pd.read_parquet(L/'states.parquet');sched=pd.read_csv(D/'schedule.csv',parse_dates=['signal_date','entry_date','phase2_date']);a,o,h=load_account(ORIGINAL);rows=[];chains=[]
 for ev in sched.itertuples():
  ei=inp.days.get_loc(ev.entry_date);prev=inp.days[ei-1];old=np.zeros(inp.n);cash=1.
  if prev in a.index:
   hp=h[h.date.eq(prev)];old[inp.symbols.get_indexer(hp.instrument)]=hp.synthetic_units;cash=float(a.loc[prev,'nav']*a.loc[prev,'cash_weight'])
  px=np.nan_to_num(inp.o[ei]);initial=cash+old@px;target=vector(inp,targets[targets.signal_date.eq(ev.signal_date)]);member,_,_,_,_,buy,sell,_=inp.context(ei-1,ei)
  full,fc,info=trade(old.copy(),cash,inp.o[ei],target,buy&member,sell,.001,.002);delta=full-old
  actual=o[o.date.eq(ev.entry_date)].set_index('instrument').units_after.reindex(inp.symbols,fill_value=0).to_numpy();check(ev.month+'_original_trade_replay',np.allclose(full,actual,atol=1e-10))
  cats=np.full(inp.n,'unchanged',object);cats[(delta>1e-12)&(old<=1e-12)]='entry';cats[(delta>1e-12)&(old>1e-12)]='top_up';cats[(delta< -1e-12)&(full<=1e-12)]='exit';cats[(delta< -1e-12)&(full>1e-12)]='trim'
  # Exact F quantities, not separately reoptimized interventions. Sell-first chains self-finance.
  for order in [('exit','trim','top_up','entry'),('trim','exit','entry','top_up')]:
   u=old.copy();cc=cash
   for cat in order:
    ids=cats==cat;dq=delta[ids];v=dq*px[ids];cc-=v.sum()+np.maximum(v,0).sum()*.001+np.maximum(-v,0).sum()*.002;u[ids]+=dq
    check(ev.month+'_'+str(order)+'_'+cat,cc>=-1e-9 and u.min()>=-1e-10)
    chains.append(dict(signal_date=ev.signal_date,order='>'.join(order),step=cat,cash=cc/initial))
   check(ev.month+'_chain_end',np.allclose(u,full) and abs(cc-fc)<1e-9)
  meta=states[states.signal_date.eq(ev.signal_date)].set_index('instrument').reindex(inp.symbols)
  windows={str(h):ei+h for h in [5,10,20]}
  if pd.notna(ev.phase2_date):windows['phase2']=inp.days.get_loc(ev.phase2_date)
  union=(old>1e-12)|(full>1e-12)
  fees=np.maximum(delta,0)*px*.001+np.maximum(-delta,0)*px*.002
  for window,j in windows.items():
   reason='OK'
   if inp.days[j]>END:reason='END_OUTSIDE_PRIMARY'
   elif np.any(union&~np.isfinite(inp.o[j])) or np.any(~np.isfinite(inp.c[ei:j,union])):reason='VALUATION_UNKNOWN'
   if reason!='OK':
    rows.append(dict(signal_date=ev.signal_date,window=window,state='UNKNOWN',category='BLOCKED_EVENT',increment=np.nan,reason=reason));continue
   effect=(delta*(np.nan_to_num(inp.o[j])-px)-fees)/initial
   check(ev.month+window+'_action_additivity',np.isclose(effect.sum(),(fc+full@np.nan_to_num(inp.o[j])-cash-old@np.nan_to_num(inp.o[j]))/initial,atol=1e-10))
   for cat in ['exit','trim','top_up','entry']:
    for st in STATES:
     ids=(cats==cat)&meta.state.eq(st).to_numpy();rows.append(dict(signal_date=ev.signal_date,window=window,state=st,category=cat,increment=float(effect[ids].sum()),trade_fraction=float((abs(delta[ids])*px[ids]).sum()/initial),fees=float(fees[ids].sum()/initial),reason='OK'))
 dump(pd.DataFrame(rows),'actions');dump(pd.DataFrame(chains),'action_chains');save_json(D/'action_validation.json',dict(status='PASS',checks=CHECKS,interpretation='fixed full-trade quantities, self-financing sell-first chains; not standalone action reoptimization'))
 print('actions done',flush=True)

def stock_returns(inp,ei,j):
 n=inp.n;out=np.full(n,np.nan)
 if j>=len(inp.days) or inp.days[j]>END or j<=ei:return out
 member,_,_,_,_,buy,_,_=inp.context(ei-1,ei);_,_,_,_,_,_,sell,_=inp.context(j-1,j)
 ok=member&buy&sell&np.isfinite(inp.o[ei])&np.isfinite(inp.o[j])&(inp.o[ei]>0)&np.isfinite(inp.c[ei:j]).all(axis=0)
 out[ok]=inp.o[j,ok]/inp.o[ei,ok]*(1-.002)/(1+.001)-1
 return out

def residuals():
 verify(True);inp=Inputs();marks(inp,0.);s=pd.read_parquet(L/'states.parquet');peers=pd.read_parquet(L/'peers.parquet');sched=pd.read_csv(D/'schedule.csv',parse_dates=['signal_date','entry_date','phase2_date']);rows=[];cor=[];coverage=[]
 for ev in sched.itertuples():
  ei=inp.days.get_loc(ev.entry_date);di=inp.days.get_loc(ev.phase2_date) if pd.notna(ev.phase2_date) else None
  immediate=stock_returns(inp,ei,ei+10);delayed=stock_returns(inp,di,di+10) if di is not None else np.full(inp.n,np.nan)
  g=s[s.signal_date.eq(ev.signal_date)].copy();ids=inp.symbols.get_indexer(g.instrument);g['immediate']=immediate[ids];g['date_gap']=immediate[ids]-delayed[ids]
  # Conditional association uses contemporaneous original scored universe, not only selected names.
  for group,h in [('ALL',g)]+list(g.groupby('state')):
   for outcome in ['immediate','date_gap']:
    valid=h.dropna(subset=['score_residual',outcome,'trend','REV']);value=np.nan;conditional=np.nan
    if len(valid)>=10:
     value=rankcorr(valid.score_residual,valid[outcome]);x=np.column_stack([np.ones(len(valid)),valid[['trend','REV']].rank(pct=True).to_numpy()]);_,rx,_,rank=project(x,valid.score_residual.rank().to_numpy());_,ry,_,_=project(x,valid[outcome].rank().to_numpy());conditional=float(np.corrcoef(rx,ry)[0,1]) if len(valid)-rank>=5 else np.nan
    cor.append(dict(signal_date=ev.signal_date,state=group,outcome=outcome,n_stocks=len(valid),rank_ic=value,conditional_rank_ic=conditional))
  pp=peers[peers.signal_date.eq(ev.signal_date)];meta=g.set_index('instrument')
  for r in pp.itertuples():
   row=meta.loc[r.instrument];i=inp.symbols.get_loc(r.instrument);peerids=inp.symbols.get_indexer(r.peers.split('|')) if r.n_peers else np.array([],int)
   # Require all frozen peers; do not silently drop failed names after outcomes.
   y=immediate[i]-immediate[peerids].mean() if len(peerids) and np.isfinite(immediate[peerids]).all() and np.isfinite(immediate[i]) else np.nan
   dg=(immediate[i]-delayed[i])-(immediate[peerids]-delayed[peerids]).mean() if len(peerids) and np.isfinite(immediate[peerids]).all() and np.isfinite(delayed[peerids]).all() and np.isfinite(immediate[i]) and np.isfinite(delayed[i]) else np.nan
   rows.append(dict(signal_date=ev.signal_date,instrument=r.instrument,tier=r.tier,state=row.state,weight=r.weight,n_peers=r.n_peers,score_residual=row.score_residual,immediate_excess=y,date_gap_excess=dg,selected_immediate=immediate[i],selected_date_gap=immediate[i]-delayed[i],status=r.status))
  for tier in ['industry','price','all13']:
   z=pp[pp.tier.eq(tier)];coverage.append(dict(signal_date=ev.signal_date,tier=tier,planned_budget=float(g.target_weight.sum()),recorded_budget=float(z.weight.sum()),supported_budget=float(z.loc[z.n_peers>0,'weight'].sum()),residual_scored_budget=float(g.loc[g.score_residual.notna(),'target_weight'].sum())))
 dump(pd.DataFrame(rows),'residual_matches');dump(pd.DataFrame(cor),'residual_correlations');dump(pd.DataFrame(coverage),'residual_coverage')
 print('residuals done',flush=True)

def stats(series):
 return bootstrap(series,'M',3) if len(series) else dict(n=0,mean=np.nan,ci_low=np.nan,ci_high=np.nan,p=np.nan)

def analyze():
 verify(True);ev=pd.read_csv(D/'events.csv',parse_dates=['signal_date']);st=pd.read_csv(D/'event_states.csv',parse_dates=['signal_date']);sched=pd.read_csv(D/'schedule.csv',parse_dates=['signal_date']);grid=pd.DatetimeIndex(sched.signal_date)
 rows=[]
 for cost in COSTS:
  for clock in ['equal_horizon','common_exit']:
   for horizon in [5,10,20]:
    for delay in ['phase2','plus1','plus3','plus5']:
     g=ev[ev.cost.eq(cost)&ev.clock.eq(clock)&ev.horizon.eq(horizon)]
     p=g.pivot(index='signal_date',columns='delay',values='net');m=g.pivot(index='signal_date',columns='delay',values='mark')
     diff=(p.immediate-p[delay]).reindex(grid)
     rows.append(dict(cost=cost,clock=clock,horizon=horizon,delay=delay,metric='net',**stats(diff)))
     rows.append(dict(cost=cost,clock=clock,horizon=horizon,delay=delay,metric='mark',**stats((m.immediate-m[delay]).reindex(grid))))
 dump(pd.DataFrame(rows),'event_summary')
 rows=[]
 for clock in ['equal_horizon','common_exit']:
  for horizon in [5,10,20]:
   for state_ in STATES:
    g=st[st.cost.eq('main')&st.clock.eq(clock)&st.horizon.eq(horizon)&st.state.eq(state_)]
    p=g.pivot(index='signal_date',columns='delay',values='net');m=g.pivot(index='signal_date',columns='delay',values='mark');v=(p.immediate-p.phase2).reindex(grid)
    rows.append(dict(clock=clock,horizon=horizon,state=state_,immediate_mean=p.immediate.mean(),delayed_mean=p.phase2.mean(),marked_gap=(m.immediate-m.phase2).mean(),**stats(v)))
 z=pd.DataFrame(rows);z['holm_p']=np.nan;fam=z.clock.eq('equal_horizon')&z.horizon.eq(10)&z.state.isin(STATES[:4]);z.loc[fam,'holm_p']=holm(z.loc[fam,'p'].to_numpy());dump(z,'02_state_timing')
 # Joint-month sample across all three horizons, no comparing incompatible samples.
 g=ev[ev.cost.eq('main')&ev.clock.eq('equal_horizon')&ev.delay.isin(['immediate','phase2'])];p=g.pivot(index='signal_date',columns=['horizon','delay'],values='net');valid=p.notna().all(axis=1);joint=[]
 for horizon in [5,10,20]:joint.append(dict(horizon=horizon,**stats((p[(horizon,'immediate')]-p[(horizon,'phase2')]).where(valid).reindex(grid))))
 dump(pd.DataFrame(joint),'joint_horizon_summary')
 ac=pd.read_csv(D/'actions.csv',parse_dates=['signal_date']);rows=[]
 for (window,cat,state_),h in ac[ac.reason.eq('OK')].groupby(['window','category','state']):rows.append(dict(window=window,category=cat,state=state_,**stats(h.set_index('signal_date').increment.reindex(grid))))
 dump(pd.DataFrame(rows),'03_actions_state')
 co=pd.read_csv(D/'residual_correlations.csv',parse_dates=['signal_date']);rows=[]
 for (state_,outcome),h in co.groupby(['state','outcome']):
  for metric in ['rank_ic','conditional_rank_ic']:rows.append(dict(state=state_,outcome=outcome,metric=metric,**stats(h.set_index('signal_date')[metric].reindex(grid))))
 dump(pd.DataFrame(rows),'04_residual_association')
 ma=pd.read_csv(D/'residual_matches.csv',parse_dates=['signal_date']);rows=[]
 for (tier,state_),h in ma.groupby(['tier','state']):
  for metric in ['immediate_excess','date_gap_excess']:
   vals=[]
   for date,k in h.groupby('signal_date'):
    v=k[k[metric].notna()];vals.append(dict(signal_date=date,value=np.average(v[metric],weights=v.weight) if len(v) else np.nan,budget=v.weight.sum()))
   v=pd.DataFrame(vals).set_index('signal_date');rows.append(dict(tier=tier,state=state_,metric=metric,mean_supported_budget=v.budget.reindex(grid,fill_value=0).mean(),**stats(v.value.reindex(grid))))
 dump(pd.DataFrame(rows),'residual_excess_summary')
 cov=pd.read_csv(D/'residual_coverage.csv');z=cov.groupby('tier',as_index=False)[['planned_budget','recorded_budget','supported_budget','residual_scored_budget']].mean();dump(z,'05_coverage')
 checks=[]
 for name in ['ledger','event','action']:
  r=json.loads((D/(name+'_validation.json')).read_text());checks.extend(r['checks'])
 check('events_complete',len(ev)==len(grid)*3*5*2*3)
 save_json(D/'validation.json',dict(status='PASS',checks=checks+CHECKS,events=len(ev),planned_months=len(grid),joint_months=int(valid.sum()),historical_proxy=True))
 print('analysis done',flush=True)

if __name__=='__main__':globals()[sys.argv[1]]()
