"""Explicit noncertified suspension marks; never alter features, labels or fills."""
import sys,numpy as np,pandas as pd
from common import *
from backtest import Inputs,run_account
from evaluate_ranking import predictions

def marks(inp,haircut):
 events=pd.read_parquet(PRIVATE/'suspensions/daily.parquet');events=events.loc[events.suspend_type.eq('S') & (events.suspend_timing.isna()|events.suspend_timing.eq(''))]
 suspended=np.zeros_like(inp.c,dtype=bool)
 for row in events.itertuples():
  d=pd.Timestamp(row.trade_date);s=row.ts_code[-2:]+row.ts_code[:6]
  if d in inp.days and s in inp.symbols:suspended[inp.days.get_loc(d),inp.symbols.get_loc(s)]=True
 records=[]
 for j,symbol in enumerate(inp.symbols):
  last=np.nan;age=0
  for i,day in enumerate(inp.days):
   if np.isfinite(inp.c[i,j]):last=inp.c[i,j];age=0;continue
   age+=1
   if suspended[i,j] and np.isfinite(last) and age<=20:
    mark=last*(1-haircut);inp.c[i,j]=mark
    if not np.isfinite(inp.o[i,j]):inp.o[i,j]=mark
    records.append(dict(date=day,instrument=symbol,mark=mark,prior_observed_qfq_close=last,age_sessions=age,haircut=haircut,full_day_suspension_verified=True,actual_quote=False))
 inp.cache={}
 return pd.DataFrame(records)

def main(haircut):
 scenario='suspend_flat' if haircut==0 else 'suspend_haircut20';dest=OUT/'sensitivity'/scenario;dest.mkdir(parents=True,exist_ok=True);ledger=PRIVATE/'sensitivity'/scenario;ledger.mkdir(parents=True,exist_ok=True)
 inp=Inputs();mark=marks(inp,haircut);mark.to_csv(dest/'marks.csv',index=False)
 p,consumption=predictions('expanding');p=p.loc[p.seed_or_ensemble.isin(['fixed','equal_seed_ensemble'])];sample=p.loc[p.model_id.eq('E2')]
 for path in ['A','B']:
  for model in ['E0-MOM','E0-REV','E0-RES','E0-MIX','E1','E2','E3',('EW' if path=='A' else 'B0')]:
   scores=sample if model in ['EW','B0'] else p.loc[p.model_id.eq(model)]
   daily,orders,holdings,fail=run_account(inp,scores,path,'main',scenario,model,'expanding');key=path+'_'+model
   pd.DataFrame(daily).to_csv(dest/(key+'.csv'),index=False);pd.DataFrame(orders).to_parquet(ledger/(key+'_orders.parquet'),index=False);pd.DataFrame(holdings,columns=['date','instrument','synthetic_units','proxy_close','weight']).to_parquet(ledger/(key+'_holdings.parquet'),index=False)
   save_json(dest/(key+'.json'),dict(prediction_consumption=consumption,days=len(daily),failures=fail,nav_sha256=sha(dest/(key+'.csv')),orders_sha256=sha(ledger/(key+'_orders.parquet')),holdings_sha256=sha(ledger/(key+'_holdings.parquet')),quality='UNVERIFIED_VALUATION_SENSITIVITY_NOT_PRIMARY',haircut=haircut))
   print(scenario,key,len(daily),fail,flush=True)
if __name__=='__main__':main(float(sys.argv[1]) if len(sys.argv)>1 else 0.)
