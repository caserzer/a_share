"""Independent invariants, economic ledger reconciliation and H20 net path decomposition."""
import json
import numpy as np
import pandas as pd
from common import EP,PRIVATE,sha,save_json
from alpha_economics import DEST,LOCAL,STYLES,MODELS,COSTS,verify,matrix,topk
from alpha_economics_analyze import boot


def main():
 cfg,receipt=verify();checks=[]
 def check(name,ok,detail=None):
  assert bool(ok),name
  checks.append(dict(check=name,passed=True,detail=detail))
 for manifest in ['selection_complete.json','events_complete.json']:
  for r in json.loads((DEST/manifest).read_text())['files']:check('hash '+r['path'],sha(r['path'])==r['sha256'])
 reg=json.loads((DEST/'analysis_registration.json').read_text());check('analysis source frozen',sha(reg['source']['path'])==reg['source']['sha256'])
 scores=pd.read_parquet(LOCAL/'scores.parquet');targets=pd.read_parquet(LOCAL/'targets.parquet');caps=pd.read_parquet(LOCAL/'cap_audit_rows.parquet')
 check('cap source predates signal',(caps.source_date<caps.signal_date).all())
 check('score decomposition identity',np.allclose(scores.S1,scores.S0+scores.S2,atol=1e-12))
 check('finite style predictors',np.isfinite(scores[STYLES]).all().all())
 check('unique score keys',not scores.duplicated(['model','signal_date','instrument']).any())
 check('unique target keys',not targets.duplicated(['model','signal_date','strategy','instrument']).any())
 check('targets weights sum one',np.allclose(targets.groupby(['model','signal_date','strategy']).weight.sum(),1))
 check('targets exactly k',bool(targets.groupby(['model','signal_date','strategy']).apply(lambda g:len(g)==g.k.iloc[0],include_groups=False).all()))
 lookup={k:g for k,g in targets.groupby(['model','signal_date','strategy'])}
 for (model,date),g in scores.groupby(['model','signal_date']):
  z,ind,x=matrix(g);k=int(lookup[(model,date,'S0')].k.iloc[0]);base=lookup[(model,date,'S0')].set_index('instrument').weight.reindex(g.instrument).fillna(0).to_numpy()
  check('S0 top projected '+str((model,date)),set(g.instrument.iloc[topk(g.S0,k,g.instrument)])==set(lookup[(model,date,'S0')].instrument))
  check('score projection orthogonality '+str((model,date)),np.max(np.abs(x.T@g.S2.to_numpy()))<1e-7)
  for strategy in ['S1','S2']:
   v=lookup[(model,date,strategy)].set_index('instrument').weight.reindex(g.instrument).fillna(0).to_numpy();d=v-base
   check('target risk '+str((model,date,strategy)),np.max(np.abs(z.T@d))<=.25+1e-7 and np.max(np.abs(ind.T@d))<=.02+1e-7)
 # Entries/exit may be blocked: validate only the declared fully sold observations.
 events=pd.read_csv(DEST/'events.csv',parse_dates=['signal_date','entry_date','exit_date']);paths=pd.read_csv(DEST/'event_paths.csv',parse_dates=['signal_date'])
 known=events[events.net_return.notna()]
 check('net exit fee reconciliation',np.allclose(known.net_return,known.marked_return-known.exit_fees,atol=1e-12))
 check('no forced exit',bool(events.loc[events.reason.eq('EXIT_NOT_FULLY_TRADEABLE'),'net_return'].isna().all()))
 check('no valuation unknown net',bool(events.loc[events.reason.eq('HELD_VALUATION_UNKNOWN'),'net_return'].isna().all()))
 m0=paths[paths.horizon==0].merge(events[events.horizon==10],on=['model','signal_date','phase','strategy','cost'])
 check('entry fee once',np.allclose(m0.mark,1-m0.entry_fees,atol=1e-12))
 days=pd.read_parquet(PRIVATE/'qfq_close.parquet').index
 knownend=events[events.exit_date.notna()]
 check('fixed market endpoints',np.array_equal(days.get_indexer(knownend.exit_date)-days.get_indexer(knownend.entry_date),knownend.horizon.to_numpy()))
 for rp in sorted((DEST/'accounts').glob('*.json')):
  r=json.loads(rp.read_text());d=pd.read_csv(rp.with_suffix('.csv'),parse_dates=['date']);o=pd.read_parquet(r['orders_path']);bf,sf=COSTS[r['cost']]
  check('account files '+r['key'],sha(rp.with_suffix('.csv'))==r['nav_sha256'] and sha(r['orders_path'])==r['orders_sha256'])
  check('daily nav returns '+r['key'],np.allclose(d.nav.to_numpy()/np.r_[1,d.nav.to_numpy()[:-1]]-1,d.daily_return,atol=1e-12))
  amount=(o.units_after-o.units_before)*o.price
  # Zero units/unknown price rows occur for blocked target buys; they are zero cashflow.
  amount=amount.fillna(0);fees=np.maximum(amount,0)*bf+np.maximum(-amount,0)*sf
  fee_by_day=fees.groupby(o.date).sum().reindex(d.date,fill_value=0).to_numpy()
  check('actual ledger fees '+r['key'],np.allclose(fee_by_day,d.fees,atol=1e-10))
  check('buy gates '+r['key'],not ((o.units_after-o.units_before>1e-10)&~o.can_buy).any())
  check('sell gates '+r['key'],not ((o.units_before-o.units_after>1e-10)&~o.can_sell).any())
  check('cash nonnegative '+r['key'],bool(d.cash_weight.ge(-1e-10).all()))
  check('entry no leverage '+r['key'],bool(o.groupby('date').actual_weight.sum().le(1+1e-8).all()))
 summary=pd.read_csv(DEST/'event_summary.csv');check('Holm3 family',summary.holm_p.notna().sum()==3)
 # A fixed H20 liquidation path: all three windows use identical fully observed event pairs.
 # First window includes entry fee, final window includes actual H20 exit fee, none at day5/10.
 cal=pd.read_csv(DEST/'schedule.csv',parse_dates=['signal_date']);rows=[];details=[]
 for scope in ['primary','extended']:
  end=pd.Timestamp('2025-03-03') if scope=='primary' else days[-1]
  for model in MODELS:
   for phase in [1,2]:
    planned=cal[cal.phase==phase].copy();positions=days.get_indexer(planned.signal_date)+21
    planned=planned[[i<len(days) and days[i]<=end for i in positions]]
    for strategy in ['S1','S2']:
     masks=(paths.model==model)&paths.strategy.isin(['S0',strategy])
     p=paths[masks].pivot(index='signal_date',columns=['strategy','horizon'],values='mark').reindex(planned.signal_date)
     n=events[(events.model==model)&events.strategy.isin(['S0',strategy])&(events.cost=='main')&(events.horizon==20)].pivot(index='signal_date',columns='strategy',values='net_return').reindex(planned.signal_date)
     valid=p.notna().all(axis=1)&n.notna().all(axis=1)
     d5=(p[(strategy,5)]-p[('S0',5)]).where(valid);d10=(p[(strategy,10)]-p[('S0',10)]).where(valid);net=(n[strategy]-n.S0).where(valid)
     pieces={'1-5_entry_net':d5,'6-10_no_trade':d10-d5,'11-20_exit_net':net-d10}
     check('H20 marginal sum '+str((scope,model,phase,strategy)),np.allclose(sum(pieces.values()).dropna(),net.dropna(),atol=1e-12))
     for name,v in pieces.items():
      v.index=pd.DatetimeIndex(v.index).to_period('M');rows.append(dict(scope=scope,model=model,phase=phase,contrast=strategy+'-S0',window=name,**boot(v)))
     for date in n.index:details.append(dict(scope=scope,model=model,phase=phase,contrast=strategy+'-S0',signal_date=date,known=bool(valid.loc[date]),first=d5.loc[date],middle=(d10-d5).loc[date],last=(net-d10).loc[date],total=net.loc[date]))
 pd.DataFrame(rows).to_csv(DEST/'marginal_net_windows.csv',index=False);pd.DataFrame(details).to_csv(DEST/'marginal_net_events.csv',index=False)
 save_json(DEST/'validation.json',dict(status='PASS',check_count=len(checks),checks=checks,original_sources_and_predictions_unchanged=True))
 print('validation PASS',len(checks),flush=True)

if __name__=='__main__':main()
