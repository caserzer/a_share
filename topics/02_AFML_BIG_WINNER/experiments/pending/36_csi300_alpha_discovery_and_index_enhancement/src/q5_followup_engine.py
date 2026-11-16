"""Isolated copy of frozen execution engine; only A selection callback differs."""
import numpy as np
import pandas as pd
from common import protocol
from portfolio import rank_target,project,trade

def select_target(score,member,held,symbols,buffer=None):
    ix=np.where(np.isfinite(score)&member)[0]
    ix=ix[np.lexsort((np.asarray(symbols)[ix],score[ix]))]
    plain=ix[np.floor(5*np.arange(len(ix))/max(1,len(ix))).astype(int)==4]
    if buffer is None:return plain
    if buffer not in [.3,.4]:raise ValueError(buffer)
    k=len(plain);ranked=ix[::-1]
    eligible=ranked[:int(np.floor(len(ix)*buffer))]
    kept=[j for j in eligible if held[j]][:k]
    additions=[j for j in ranked if j not in kept][:k-len(kept)]
    return np.array(kept+additions,dtype=int)

def run_account(inp,scores,path,cost,scenario,model,scheme,buffer=None):
 delay=1 if scenario=='delay1' else 0;all_dates=sorted(scores.signal_date.unique());signal_map={};n=inp.n
 for ordinal,date in enumerate(all_dates):
  if scenario=='biweekly' and ordinal%2:continue
  si=inp.days.get_indexer([date])[0];ei=si+1+delay
  if ei<len(inp.days):signal_map[ei]=(si,scores.loc[scores.signal_date.eq(date)].set_index('instrument').score.reindex(inp.symbols).to_numpy())
 if not signal_map:return [],[],[],[]
 first=min(signal_map);units=np.zeros(n);cash=1.;daily=[];orders=[];holdings=[];fail=[];built=False
 buyfee,sellfee=np.array(protocol()['costs_bps'][cost])/10000
 key=f'{scheme}_{scenario}_{path}_{model}_{cost}'
 for i in range(first,len(inp.days)):
  day=inp.days[i];rec=dict(date=day,account=key,scheme=scheme,scenario=scenario,path=path,model=model,cost=cost,buy=0.,sell=0.,fees=0.,target_status='',solver='',relaxed=False,unknown_state_weight=0.,target_turnover=0.)
  if i in signal_map:
   si,score=signal_map[i];member,b,reason,snapshot,industry,buy,sell,known=inp.context(si,i)
   held=units>0
   if np.any(held&~np.isfinite(inp.o[i])):
    fail.append(dict(account=key,date=day,reason='HELD_OPEN_VALUATION_UNKNOWN',instruments='|'.join(inp.symbols[held&~np.isfinite(inp.o[i])])));break
   value=units*np.nan_to_num(inp.o[i]);nav=cash+value.sum();current=np.r_[value/nav,cash/nav];target=None
   buy=buy & member  # Hard execution gate: never add an off-universe security, including QP roundoff.
   rec['unknown_state_weight']=current[:-1][~known].sum();rec['legacy_weight']=current[:-1][~member].sum();rec['signal_date']=inp.days[si]
   if path=='A':
    ok=np.isfinite(score)&member
    if model=='EW':selected=np.where(member)[0]
    else:
     selected=select_target(score,member,units>0,inp.symbols,buffer)
    if len(selected):target=np.zeros(n+1);target[selected]=1/len(selected);rec['target_status']='Q5' if model!='EW' else 'CONSTITUENT_EW'
    else:rec['target_status']='NO_SCORES'
   else:
    rec['target_status']=reason;rec['weight_snapshot']=snapshot
    if b is not None:
     q=b if model=='B0' else rank_target(score,b)
     target,info=project(q,b,current,buy,sell,member,industry,initial=not built);rec.update(info)
     rec['unscored_active_deviation']=float(np.abs(target[:-1][~np.isfinite(score)]-b[~np.isfinite(score)]).sum());rec['unknown_industry_benchmark_weight']=b[industry=='UNKNOWN'].sum()
   if target is not None:
    old=units.copy();oldcash=cash;units,cash,info=trade(units,cash,inp.o[i],target,buy,sell,buyfee,sellfee);rec.update(info);built=True
    postvalue=units*np.nan_to_num(inp.o[i]);postnav=cash+postvalue.sum();post=np.r_[postvalue/postnav,cash/postnav]
    rec['executed_turnover']=.5*np.abs(post-current).sum()
    if b is not None and path=='B':
     rec['actual_active_share']=.5*(np.abs(post[:-1]-b).sum()+post[-1]);rec['actual_max_stock_deviation']=np.abs(post[:-1]-b).max();rec['actual_max_industry_deviation']=max(abs((post[:-1]-b)[industry==g].sum()) for g in set(industry))
    for j in np.where((abs(units-old)>1e-12)|(target[:-1]>0)|(old>1e-12))[0]:
     orders.append(dict(account=key,date=day,instrument=inp.symbols[j],units_before=old[j],units_after=units[j],qfq_open=inp.o[i,j],raw_open=inp.raw[i,j],target_weight=target[j],actual_weight=post[j],can_buy=buy[j],can_sell=sell[j],state_known=known[j],current_member=member[j],pretrade_nav=nav,cash_before=oldcash,cash_after=cash))
  held=units>0
  if np.any(held&~np.isfinite(inp.c[i])):
   fail.append(dict(account=key,date=day,reason='HELD_CLOSE_VALUATION_UNKNOWN',instruments='|'.join(inp.symbols[held&~np.isfinite(inp.c[i])])));break
  values=units*np.nan_to_num(inp.c[i]);nav=cash+values.sum();rec.update(nav=nav,cash_weight=cash/nav,holdings=int(held.sum()))
  daily.append(rec)
  for j in np.where(held)[0]:holdings.append((day,inp.symbols[j],units[j],inp.c[i,j],values[j]/nav))
 return daily,orders,holdings,fail
