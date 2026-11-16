"""Daily synthetic-unit accounts, raw opening-state gates and constrained proxy B."""
import sys
import numpy as np,pandas as pd
from common import *
from portfolio import rank_target,project,trade
from evaluate_ranking import predictions

class Inputs:
 def __init__(self):
  self.close=pd.read_parquet(PRIVATE/'qfq_close.parquet');self.days=self.close.index;self.symbols=self.close.columns;self.n=len(self.symbols)
  def read(k):return pd.read_parquet(PRIVATE/(k+'.parquet')).reindex(index=self.days,columns=self.symbols).to_numpy(float)
  self.c=self.close.to_numpy(float);self.o=read('qfq_open');self.raw=read('open');self.status=read('opening_trade_status_v2')
  lim=pd.read_parquet(PRIVATE/'limits/daily.parquet');lim['instrument']=lim.ts_code.str[-2:]+lim.ts_code.str[:6];lim['date']=pd.to_datetime(lim.trade_date)
  assert not lim.duplicated(['date','instrument']).any()
  def limit(k):return lim.pivot(index='date',columns='instrument',values=k).reindex(index=self.days,columns=self.symbols).to_numpy(float)
  self.up=limit('up_limit');self.down=limit('down_limit')
  self.members=pd.read_parquet(PRIVATE/'daily_members.parquet').reindex(index=self.days,columns=self.symbols).to_numpy(bool)
  self.weight=pd.read_parquet(PRIVATE/'weights/snapshots.parquet');self.weight['date']=pd.to_datetime(self.weight.trade_date);self.weight['instrument']=self.weight.con_code.str[-2:]+self.weight.con_code.str[:6]
  self.weight=self.weight.pivot(index='date',columns='instrument',values='weight').reindex(columns=self.symbols)/100
  self.ind=pd.read_parquet(PRIVATE/'industry.parquet');self.ind['instrument']=self.ind.ts_code.str[-2:]+self.ind.ts_code.str[:6];self.ind['start']=pd.to_datetime(self.ind.in_date);self.ind['end']=pd.to_datetime(self.ind.out_date).fillna(pd.Timestamp('2100-01-01'))
  self.cache={}
 def context(self,signal_idx,execution_idx):
  key=(signal_idx,execution_idx)
  if key in self.cache:return self.cache[key]
  s=self.days[signal_idx];d=self.days[execution_idx];member=self.members[signal_idx];b=None;reason='NO_AVAILABLE_WEIGHT_SNAPSHOT';snapshot=None
  # Snapshot must precede at least one market close before signal generation.
  dates=self.weight.index[self.weight.index<self.days[max(0,signal_idx)]]
  if len(dates):
   snapshot=dates[-1];w=self.weight.loc[snapshot];wp=w.notna().to_numpy()
   if not np.array_equal(wp,member):reason='SNAPSHOT_MEMBERSHIP_MISMATCH'
   else:
    wi=self.days.get_indexer([snapshot])[0]
    if wi<0:reason='WEIGHT_BASE_PRICE_OUTSIDE_CALENDAR'
    elif not np.isfinite(self.c[wi,wp]).all() or not np.isfinite(self.o[execution_idx,wp]).all():reason='WEIGHT_DRIFT_PRICE_UNKNOWN'
    else:
     b=np.zeros(self.n);b[wp]=w.to_numpy()[wp]*self.o[execution_idx,wp]/self.c[wi,wp];b/=b.sum();reason='RECONSTRUCTED_PROXY'
  h=self.ind.loc[(self.ind.start<=s)&(self.ind.end>s)].groupby('instrument').l1_code.agg(lambda x:next(iter(set(x))) if len(set(x))==1 else 'UNKNOWN')
  industry=h.reindex(self.symbols).fillna('UNKNOWN').to_numpy()
  known=np.isfinite(self.raw[execution_idx])&np.isfinite(self.o[execution_idx])&np.isfinite(self.up[execution_idx])&np.isfinite(self.down[execution_idx])&(self.status[execution_idx]==1)&(self.up[execution_idx]>self.down[execution_idx])
  buy=known&(self.raw[execution_idx]<self.up[execution_idx]-1e-6);sell=known&(self.raw[execution_idx]>self.down[execution_idx]+1e-6)
  value=(member,b,reason,snapshot,industry,buy,sell,known);self.cache[key]=value;return value

def run_account(inp,scores,path,cost,scenario,model,scheme):
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
     ix=np.where(ok)[0];ix=ix[np.lexsort((inp.symbols[ix],score[ix]))];selected=ix[np.floor(5*np.arange(len(ix))/max(1,len(ix))).astype(int)==4]
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

def main(scheme,scenario):
 inp=Inputs();p,consumption=predictions(scheme);p=p.loc[p.seed_or_ensemble.isin(['fixed','equal_seed_ensemble'])];dest=OUT/'accounts';dest.mkdir(parents=True,exist_ok=True);ledger=PRIVATE/'ledgers';ledger.mkdir(parents=True,exist_ok=True)
 # EW and B0 share the same signal calendar and source prediction consumption.
 sample=p.loc[p.model_id.eq('E2')].copy();all_fail=[]
 for path in ['A','B']:
  for model in ['E0-MOM','E0-REV','E0-RES','E0-MIX','E1','E2','E3',('EW' if path=='A' else 'B0')]:
   scores=sample if model in ['EW','B0'] else p.loc[p.model_id.eq(model)]
   for cost in ['zero','main','stress']:
    key=f'{scheme}_{scenario}_{path}_{model}_{cost}';target=dest/(key+'.csv');receipt=OUT/'manifests'/(key+'.json')
    if target.exists() and receipt.exists() and json.loads(receipt.read_text()).get('execution_version')=='v2_2_membership_execution_gate':continue
    daily,orders,holdings,fail=run_account(inp,scores,path,cost,scenario,model,scheme)
    pd.DataFrame(daily).to_csv(target,index=False);pd.DataFrame(orders).to_parquet(ledger/(key+'_orders.parquet'),index=False)
    pd.DataFrame(holdings,columns=['date','instrument','synthetic_units','qfq_close','weight']).to_parquet(ledger/(key+'_holdings.parquet'),index=False)
    save_json(receipt,dict(account=key,execution_version='v2_2_membership_execution_gate',execution_state_sha256=sha(PRIVATE/'opening_trade_status_v2.parquet'),nav_sha256=sha(target),orders_sha256=sha(ledger/(key+'_orders.parquet')),holdings_sha256=sha(ledger/(key+'_holdings.parquet')),failures=fail,prediction_consumption=consumption,quality='qfq_synthetic_account_and_reconstructed_weight_proxy',formal_B=False,completed_to_data_end=not fail))
    all_fail.extend(fail);print('account',key,'days',len(daily),'failures',len(fail),flush=True)
 save_json(OUT/'manifests'/f'path_b_{scheme}_consumption.json',consumption)
if __name__=='__main__':main(sys.argv[1] if len(sys.argv)>1 else 'expanding',sys.argv[2] if len(sys.argv)>2 else 'weekly')
