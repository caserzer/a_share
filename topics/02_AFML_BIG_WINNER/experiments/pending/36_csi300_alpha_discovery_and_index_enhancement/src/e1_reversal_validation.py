"""Frozen follow-up of already observed REV; historical replication, not new blind test."""
import sys,json
from pathlib import Path
from datetime import datetime,timezone
import numpy as np,pandas as pd
from common import EP,OUT,PRIVATE,sha,save_json
from alpha_economics import target_vector,event_path
from e1_mechanism import bootstrap
from e1_engineered_ablation import daily_stat
from e1_return_attribution import daily_returns,absolute_components
from backtest import Inputs
from suspension_sensitivity import marks
RUN='e1_reversal_validation_20261117';D=OUT/'diagnostics'/RUN;L=PRIVATE/RUN;R=EP/'reports'/RUN
PREV='e1_excluded_styles_20261117';END=pd.Timestamp('2025-03-03')
def write(a,name,private=False):
 p=(L if private else D)/name;p.parent.mkdir(parents=True,exist_ok=True)
 if name.endswith('.parquet'):a.to_parquet(p,index=False)
 else:a.to_csv(p,index=False)
def record(paths):return [dict(path=str(p),sha256=sha(p)) for p in paths]
def verify(stage='freeze'):
 for f in json.loads((D/(stage+'.json')).read_text())['files']:assert sha(f['path'])==f['sha256'],f['path']
def extract_sleeve(original,alternative,normalized_original,budget):
 ids=original.index.union(alternative.index).union(normalized_original.index)
 o=original.reindex(ids,fill_value=0);a=alternative.reindex(ids,fill_value=0);s=normalized_original.reindex(ids,fill_value=0)*budget
 retained=o-s;res=a-retained
 if retained.min()<-1e-10 or res.min()<-1e-10:raise ValueError('Cannot isolate fixed sleeve without changing retained holdings')
 res=res.clip(lower=0)
 assert np.isclose(res.sum(),budget)
 return (res[res>1e-14]/budget),retained
def forward_eligibility(record,frozen_signal_date,protocol_hash):
 """Metadata gate only: this is not independent known_at certification."""
 required=['signal_date','signal_decision_at','generated_at','entry_at','inputs_known_at','model_frozen_at','protocol_sha256','input_manifest_sha256','model_sha256','predictions_sha256','targets_sha256']
 missing=[k for k in required if k not in record]
 if missing:return False,'MISSING:'+','.join(missing)
 try:
  signal=pd.Timestamp(record['signal_date']).date();cutoff=pd.Timestamp(frozen_signal_date).date()
  decision=pd.Timestamp(record['signal_decision_at']);generated=pd.Timestamp(record['generated_at']);entry=pd.Timestamp(record['entry_at']);known=pd.Timestamp(record['inputs_known_at']);model=pd.Timestamp(record['model_frozen_at'])
  if any(x.tzinfo is None for x in [decision,generated,entry,known,model]):return False,'TIMEZONE_REQUIRED'
  if signal<=cutoff:return False,'HISTORICAL_SIGNAL'
  if not (model<=decision<=generated<entry and known<=decision):return False,'TIMING_INVALID'
  if record['protocol_sha256']!=protocol_hash:return False,'PROTOCOL_CHANGED'
  for name in ['input_manifest_sha256','model_sha256','predictions_sha256','targets_sha256']:
   if len(record[name])!=64 or any(c not in '0123456789abcdef' for c in record[name]):return False,'INVALID_HASH'
  if record.get('future_outcomes_seen',True):return False,'OUTCOME_VISIBILITY_NOT_ATTESTED'
  if record.get('phase')!=1:return False,'NOT_FIRST_MONTHLY_PHASE'
 except (ValueError,TypeError):return False,'INVALID_METADATA'
 return True,'METADATA_ELIGIBLE_NOT_PIT_CERTIFIED'
def freeze():
 for p in [D,L,R]:p.mkdir(parents=True,exist_ok=True)
 assert not (D/'freeze.json').exists()
 cfg=dict(run=RUN,at=datetime.now(timezone.utc).isoformat(),previous_REV_account_seen=True,new_horizon_results_seen=False,
 selection='reuse exact sealed O/REV full targets and BASE_O normalized support; isolate REV sleeve by subtracting unchanged O budget; no rerank, no new features, no thresholds',
 scope='50 original monthly signals; primary historical2021-01-08 to2025-03-03',
 primary='normalized O sleeve minus REV sleeve H10 net event return, main10/20bps, monthly3block5000; single main endpoint, no equivalence claim',
 auxiliary='H5/H20; zero/stress30/80bps; endpoint marks when liquidation unavailable; original continuous account daymean, yearly/monthly paths and linked stock contributions; no winner selection',
 horizon='next trading-day open entry, t+1+h open attempted full liquidation; maturity<=2025-03-03; missing outcomes not zero; same-month intersection for main paired comparisons',
 cohorts='same supported ~31.6% original budget; rest remains original E1; normalized events not full standalone REV strategy',
 prospective='only first-monthly-phase signals strictly after2026-11-17 and recorded before entry; zero new prospective observations in this run; protocol alone is not forward evidence',
 prohibition='no retuning REV, selecting a favorable year/horizon or equivalence band, relabeling used history as forward',forward='FORWARD_PENDING')
 cp=EP/'configs'/(RUN+'.json');assert not cp.exists();save_json(cp,cfg)
 paths=[cp]+list((EP/'src').glob('*.py'))+[PRIVATE/PREV/'targets.parquet',OUT/'diagnostics'/PREV/'coverage.csv',OUT/'diagnostics'/PREV/'events.csv']
 paths += [OUT/'diagnostics'/PREV/'accounts'/(st+'__'+cost+'.csv') for st in ['O','REV'] for cost in ['main','zero','stress']]
 paths += [PRIVATE/PREV/'orders'/(st+'__main.parquet') for st in ['O','REV']]
 paths += [PRIVATE/(s+'.parquet') for s in ['qfq_open','qfq_close','open','opening_trade_status_v2','daily_members','industry']]+[PRIVATE/'limits/daily.parquet',PRIVATE/'suspensions/daily.parquet',PRIVATE/'weights/snapshots.parquet']
 forward=dict(status='FORWARD_PENDING',at=cfg['at'],new_observations=0,exclude_signals_through='2026-11-17',selection_contract_sha256=sha(EP/'configs'/(PREV+'.json')),
 model_policy='original E1 expanding recipe unchanged; each actual checkpoint must be archived and available before signal decision; no new model trained or automatically scheduled by this run; missing model receipt blocks registration',
 phase='original first completed weekly signal of each calendar month; calendar verified at runtime, not guessed here',
 primary='equal-date normalized excluded-support O minus REV H10 executable net return; same10/20bps; paired monthly3block5000; no repeated significance-based stopping',
 review='record all monthly signals and missingness continuously; first fixed confirmatory review after24 scheduled monthly events, regardless of observed returns; fewer than6 executable pairs => insufficient inference;24events do not guarantee power',
 no_equivalence='no equivalence margin was set before historical REV result; do not assert equivalence from nonsignificance',
 receipts='timestamped source/model/prediction/target hashes sealed before next-session entry; known_at provenance separately reviewed; metadata gate not PIT certification',
 pending=['future inputs and genuine arrival timestamps','future E1 predictions with checkpoint receipts','next-session entry and actual tradeability','mature H10 returns'],automation='none; no scheduler, deployment, order or message created')
 save_json(D/'forward_contract.json',forward)
 save_json(D/'freeze.json',dict(files=record(sorted(set(paths))+[D/'forward_contract.json']),new_outcomes_read=False))
 (R/'PROTOCOL.md').write_text('# E1与固定REV的期限及路径检验\n\n'+json.dumps(cfg,ensure_ascii=False,indent=2)+'\n')
 print('FROZEN',flush=True)
def prepare():
 verify();assert not (D/'selection_complete.json').exists()
 t=pd.read_parquet(PRIVATE/PREV/'targets.parquet');cov=pd.read_csv(OUT/'diagnostics'/PREV/'coverage.csv',parse_dates=['signal_date']);cov=cov[cov.test=='BASE'].set_index('signal_date')
 rows=[];checks=[]
 for date,g in t.groupby('signal_date'):
  o=g[g.strategy=='O'].set_index('instrument').weight;rev=g[g.strategy=='REV'].set_index('instrument').weight;s=g[g.strategy=='BASE_O'].set_index('instrument').weight;budget=cov.loc[date,'covered_budget']
  r,retained=extract_sleeve(o,rev,s,budget)
  union=s.index.union(r.index);overlap=np.minimum(s.reindex(union,fill_value=0),r.reindex(union,fill_value=0)).sum()
  checks.append(dict(signal_date=date,budget=budget,overlap=overlap,O_count=len(s),REV_count=len(r),retained_budget=retained.sum()))
  for st,weights in [('O',s),('REV',r)]:
   for code,w in weights.items():rows.append(dict(signal_date=date,strategy=st,instrument=code,weight=w))
 write(pd.DataFrame(rows),'sleeves.parquet',True);write(pd.DataFrame(checks),'selection_checks.csv')
 verify();save_json(D/'selection_complete.json',dict(files=record([L/'sleeves.parquet',D/'selection_checks.csv']),new_returns_read=False));print('SEALED',flush=True)
def run():
 verify();verify('selection_complete');assert not (D/'events_complete.json').exists()
 inp=Inputs();marks(inp,0.);t=pd.read_parquet(L/'sleeves.parquet');events=[];paths=[]
 for st,g in t.groupby('strategy'):
  for date,a in g.groupby('signal_date'):
   vec=target_vector(inp,a)
   for cost,fees in [('main',(.001,.002)),('zero',(0.,0.)),('stress',(.003,.008))]:
    ev,pa=event_path(inp,inp.days.get_loc(date),vec,*fees);events.extend(dict(signal_date=date,strategy=st,cost=cost,**r) for r in ev)
    if cost=='main':paths.extend(dict(signal_date=date,strategy=st,**r) for r in pa)
  print(st,flush=True)
 write(pd.DataFrame(events),'events.csv');write(pd.DataFrame(paths),'event_paths.csv')
 verify();save_json(D/'events_complete.json',dict(files=record([D/'events.csv',D/'event_paths.csv']),status='COMPLETE'))
def analyze():
 for n in ['freeze','selection_complete','events_complete']:verify(n)
 assert not (D/'analysis_complete.json').exists()
 checks=[]
 def ck(name,ok):assert bool(ok),name;checks.append(dict(name=name,passed=True))
 events=pd.read_csv(D/'events.csv',parse_dates=['signal_date','entry_date','exit_date']);dates=pd.DatetimeIndex(sorted(events.signal_date.unique()))
 stats=[];pairs=[];valid=events[events.exit_date<=END]
 for (cost,h),a in valid.groupby(['cost','horizon']):
  for field in ['net_return','marked_return']:
   p=a.pivot(index='signal_date',columns='strategy',values=field);s=(p.O-p.REV).reindex(dates)
   stats.append(dict(cost=cost,horizon=h,field=field,primary=cost=='main' and h==10 and field=='net_return',**bootstrap(s,'M',3)))
   if cost=='main' and field=='net_return':
    for date,v in s.items():pairs.append(dict(signal_date=date,horizon=h,difference=v))
 write(pd.DataFrame(stats),'event_statistics.csv');write(pd.DataFrame(pairs),'event_pairs.csv')
 # Horizon-independent entry receipts and exact prior O H10 replay.
 old=pd.read_csv(OUT/'diagnostics'/PREV/'events.csv',parse_dates=['signal_date'])
 old=old[old.strategy=='BASE_O'].set_index('signal_date')
 now=events[(events.strategy=='O')&(events.cost=='main')&(events.horizon==10)].set_index('signal_date')
 ck('original sleeve H10 replay',np.allclose(old.net_return,now.net_return,equal_nan=True,atol=1e-12))
 for (date,st,cost),a in events.groupby(['signal_date','strategy','cost']):
  ck(str(date)+st+cost+' horizons same entry',a.entry_date.nunique()==1 and a.actual_holdings.nunique()==1 and a.entry_fees.nunique()==1)
 # Continuous accounts are immutable prior results, not reoptimized in this run.
 frames={};metrics=[];comp={};annual=[];dailycomparisons=[];inp=Inputs();marks(inp,0.)
 for cost in ['main','zero','stress']:
  for st in ['O','REV']:
   a=pd.read_csv(OUT/'diagnostics'/PREV/'accounts'/(st+'__'+cost+'.csv'),parse_dates=['date']).set_index('date');frames[(st,cost)]=a
   ck(st+cost+' account length',len(a)==1001 and a.index[-1]==END)
   metrics.append(dict(strategy=st,cost=cost,cagr=a.nav.iloc[-1]**(252/len(a))-1,nav=a.nav.iloc[-1]))
   if cost=='main':
    r=daily_returns(a.nav);o=pd.read_parquet(PRIVATE/PREV/'orders'/(st+'__main.parquet'));c=absolute_components(inp,a,o)
    ck(st+' daily ledger',np.allclose(c.sum(axis=1),r,atol=1e-10));comp[st]=c.mul(np.divide(np.log1p(r),r,out=np.ones(len(r)),where=abs(r)>1e-12),axis=0)
  s=daily_returns(frames[('O',cost)].nav)-daily_returns(frames[('REV',cost)].nav);dailycomparisons.append(dict(cost=cost,**daily_stat(s)))
 for freq in ['Y','M']:
  rr=pd.DataFrame({st:daily_returns(frames[(st,'main')].nav) for st in ['O','REV']})
  for per,a in rr.groupby(rr.index.to_period(freq)):
   annual.append(dict(freq=freq,period=str(per),days=len(a),O_return=np.prod(1+a.O)-1,REV_return=np.prod(1+a.REV)-1,return_difference=np.prod(1+a.O)-np.prod(1+a.REV),mean_daily_difference=(a.O-a.REV).mean(),positive_days=int((a.O>a.REV).sum())))
 write(pd.DataFrame(metrics),'account_metrics.csv');write(pd.DataFrame(dailycomparisons),'account_comparison.csv');write(pd.DataFrame(annual),'period_returns.csv')
 delta=comp['O'].subtract(comp['REV'],fill_value=0);lg=delta.to_numpy().sum();gap=100*(frames[('O','main')].nav.iloc[-1]-frames[('REV','main')].nav.iloc[-1]);scale=gap/lg if abs(lg)>1e-12 else 100*frames[('REV','main')].nav.iloc[-1]
 ck('linked log gap',abs(lg-np.log(frames[('O','main')].nav.iloc[-1]/frames[('REV','main')].nav.iloc[-1]))<1e-10)
 stocks=delta.sum()*scale;write(stocks.rename_axis('instrument').reset_index(name='wealth_contribution'),'stock_contributions.csv');pr=[]
 for freq in ['Y','M']:
  for per,a in delta.groupby(delta.index.to_period(freq)):pr.append(dict(freq=freq,period=str(per),wealth_contribution=a.to_numpy().sum()*scale))
 write(pd.DataFrame(pr),'period_contributions.csv');ck('wealth closure',abs(stocks.sum()-gap)<1e-9)
 # Event yearly means on their own available paired samples, no new hypothesis selection.
 pairs=pd.DataFrame(pairs);pairs['year']=pairs.signal_date.dt.year
 write(pairs.groupby(['year','horizon']).difference.agg(['count','mean','median']).reset_index(),'event_years.csv')
 # Fixed-event marked path: same stock set, entry cost only, no fabricated exits.
 pa=pd.read_csv(D/'event_paths.csv',parse_dates=['signal_date'])
 calendar=pd.read_parquet(PRIVATE/'qfq_open.parquet').index;curve=[]
 for h,g in pa.groupby('horizon'):
  mature={d for d in dates if calendar.get_loc(d)+1+h<len(calendar) and calendar[calendar.get_loc(d)+1+h]<=END}
  p=g[g.signal_date.isin(mature)].pivot(index='signal_date',columns='strategy',values='mark');s=(p.O-p.REV).reindex(dates)
  curve.append(dict(horizon=h,**bootstrap(s,'M',3)))
 write(pd.DataFrame(curve),'marked_curve.csv')
 save_json(D/'validation.json',dict(status='PASS',count=len(checks),checks=checks))
 for n in ['freeze','selection_complete','events_complete']:verify(n)
 save_json(D/'analysis_complete.json',dict(files=record(list(D.glob('*.csv'))+[D/'validation.json']),status='HISTORICAL_POST_SELECTION_DIAGNOSTIC',forward='FORWARD_PENDING',new_prospective_observations=0))
 print(pd.DataFrame(stats).query("cost=='main'").to_string(index=False));print(pd.DataFrame(annual).query("freq=='Y'").to_string(index=False),flush=True)
if __name__=='__main__':globals()[sys.argv[1]]()
