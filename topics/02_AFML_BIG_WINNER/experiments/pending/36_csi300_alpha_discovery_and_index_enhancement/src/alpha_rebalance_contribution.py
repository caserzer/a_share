"""Descriptive ledger counterfactual: trade now vs keep the exact pretrade holdings.

Defined after headline economic results; never used for parameter selection or primary tests.
No hypothetical fills: observed trades only, counterfactual no trade, common next rebalance open.
"""
import json
import numpy as np
import pandas as pd
from common import save_json,sha,EP
from alpha_economics import DEST,LOCAL,MODELS,selected_inputs,date_schedule


def main():
 inp,_,schedule=selected_inputs();rows=[];checks=0
 save_json(DEST/'rebalance_contribution_registration.json',dict(primary_economic_results_seen=True,status='DESCRIPTIVE_REQUESTED_MECHANISM_DECOMPOSITION',formula='actual trade vs unchanged pretrade units/cash until next scheduled open; buys*(exit/entry-1)-sells*(exit/entry-1)-fees over pretradeNAV',no_parameters_selected=True,source_sha256=sha(EP/'src/alpha_rebalance_contribution.py')))
 for model in MODELS:
  for freq in ['1w','2w','1m']:
   dates=date_schedule(schedule.signal_date,freq);nextdate=dict(zip(dates[:-1],dates[1:]))
   for strategy in ['S0','S1','S2']:
    key=f'{model}_{strategy}_{freq}_main';orders=pd.read_parquet(LOCAL/'accounts'/(key+'.parquet'))
    daily=pd.read_csv(DEST/'accounts'/(key+'.csv'),parse_dates=['date']).set_index('date')
    for signal,g in orders.groupby('signal_date'):
     if signal not in nextdate:continue
     entry=inp.days.get_loc(signal)+1;end=inp.days.get_loc(nextdate[signal])+1
     if end>=len(inp.days):continue
     ids=inp.symbols.get_indexer(g.instrument);held=(g.units_before.to_numpy()>0)|(g.units_after.to_numpy()>0)
     row=dict(model=model,strategy=strategy,frequency=freq,signal_date=signal,entry_date=inp.days[entry],exit_date=inp.days[end],sessions=end-entry,primary=inp.days[end]<=pd.Timestamp('2025-03-03'),status='OBSERVED',buy_contribution=np.nan,sell_contribution=np.nan,fee_contribution=np.nan,total=np.nan)
     if np.any(~np.isfinite(inp.o[end,ids[held]])) or np.any(~np.isfinite(inp.c[entry:end,ids[held]])):
      row['status']='COUNTERFACTUAL_HELD_VALUATION_UNKNOWN';rows.append(row);continue
     prices=g.price.to_numpy();delta=g.units_after.to_numpy()-g.units_before.to_numpy();nav=float(g.pretrade_nav.iloc[0]);trade_value=np.nan_to_num(delta*prices)
     ratio=np.divide(inp.o[end,ids],prices,out=np.ones(len(prices)),where=np.isfinite(prices)&(prices>0))-1
     buy=float(np.sum(np.maximum(trade_value,0)*ratio)/nav);sell=float(-np.sum(np.maximum(-trade_value,0)*ratio)/nav)
     fees=float(daily.loc[inp.days[entry],'fees'])/nav
     direct=float(np.sum(delta*np.nan_to_num(inp.o[end,ids])-trade_value)/nav-fees)
     assert np.isclose(buy+sell-fees,direct,atol=1e-10);checks+=1
     row.update(buy_contribution=buy,sell_contribution=sell,fee_contribution=-fees,total=direct);rows.append(row)
 f=pd.DataFrame(rows);f.to_csv(DEST/'rebalance_contributions.csv',index=False)
 known=f[f.primary&f.status.eq('OBSERVED')]
 summary=known.groupby(['model','strategy','frequency']).agg(known_windows=('total','count'),mean_buy=('buy_contribution','mean'),mean_sell=('sell_contribution','mean'),mean_fees=('fee_contribution','mean'),mean_total=('total','mean')).reset_index()
 summary.to_csv(DEST/'rebalance_contribution_summary.csv',index=False)
 save_json(DEST/'rebalance_contribution_validation.json',dict(status='PASS',reconciled_windows=checks,planned=len(f),unknown=int(f.status.ne('OBSERVED').sum()),warning='Overlapping differently funded counterfactual windows; do not sum into NAV or annualize as strategy return'))
 print('rebalance contribution checks',checks)
if __name__=='__main__':main()
