"""Descriptive original E1 to constrained E1 bridge; no return-based selection."""
import json,sys,math
from datetime import datetime,timezone
import numpy as np,pandas as pd
from scipy.optimize import milp,Bounds,LinearConstraint
from scipy.stats import rankdata
from common import EP,OUT,PRIVATE,sha,save_json
from alpha_economics import STYLES,target_vector,run_account
from e1_mechanism import standard,base_mask
from e1_return_attribution import ORIGINAL,absolute_components,daily_returns,paired_ci,industry_map,benchmark
from backtest import Inputs
from suspension_sensitivity import marks
RUN='e1_advantage_bridge_20261117';D=OUT/'diagnostics'/RUN;L=PRIVATE/RUN;R=EP/'reports'/RUN;END=pd.Timestamp('2025-03-03');OLD='e1_alpha_mechanism_20261117'
MAIN=[('O','U','universe'),('U','K','count'),('K','I','industry'),('I','F','style')]
EXTRA=[('U','UI','industry_before_count'),('UI','I','count_after_industry'),('K','KF','style_before_industry'),('KF','F','industry_after_style'),('O','X','drop_excluded_to_cash'),('X','U','refill_excluded_budget')]

def write(a,name,private=False):
 p=(L if private else D)/name;p.parent.mkdir(parents=True,exist_ok=True)
 if name.endswith('.parquet'):a.to_parquet(p,index=False)
 else:a.to_csv(p,index=False)

def record(paths):return [dict(path=str(p),sha256=sha(p)) for p in paths]
def verify(name='freeze'):
 r=json.loads((D/(name+'.json')).read_text())
 for p in r['files']:assert sha(p['path'])==p['sha256'],p['path']
 return r

def quotas(g,k):
 counts=g.industry.value_counts().sort_index();q=counts*k/len(g);slots=np.floor(q).astype(int)
 for a in sorted(counts.index,key=lambda a:(-(q[a]-slots[a]),a))[:k-int(slots.sum())]:slots[a]+=1
 return slots

def choose(g,k,industry=False):
 mask=np.zeros(len(g));groups=quotas(g,k).items() if industry else [('ALL',k)]
 for a,count in groups:
  ids=np.flatnonzero(g.industry.to_numpy()==a) if industry else np.arange(len(g));order=np.lexsort((g.instrument.to_numpy()[ids],-g.E1.to_numpy()[ids]));mask[ids[order[:count]]]=1
 assert mask.sum()==k
 return mask

def risk_only(g,k,base):
 z=standard(g[STYLES]);a=np.vstack([np.ones(len(g)),z.T/k]);target=np.r_[k,z.T@base/k];tol=np.r_[0,np.full(len(STYLES),.25)]
 r=milp(-rankdata(g.E1)/len(g),integrality=np.ones(len(g)),bounds=Bounds(0,1),constraints=LinearConstraint(a,target-tol,target+tol),options={'time_limit':2,'mip_rel_gap':.01})
 mask=None if r.x is None else (r.x>.5).astype(float);ok=mask is not None and mask.sum()==k and np.all(abs(a@mask-target)<=tol+1e-7)
 if not ok:raise RuntimeError('Fixed reverse-order solve has no verified target; no relaxation')
 return mask,dict(status=int(r.status),gap=float(r.mip_gap),bound=float(r.mip_dual_bound),max_style_gap=float(np.max(abs(z.T@(mask-base)/k))))

def freeze():
 D.mkdir(parents=True,exist_ok=True);L.mkdir(parents=True,exist_ok=True);R.mkdir(parents=True,exist_ok=True);assert not (D/'freeze.json').exists()
 cfg=dict(run=RUN,created_at=datetime.now(timezone.utc).isoformat(),status='REGISTERED',historical_results_seen=True,new_bridge_results_seen=False,primary_start='2021-01-08',primary_end=str(END.date()),fees=[.001,.002],main_chain={'O':'exact original target','U':'C universe top original k by original E1, equal weights; excluded capital refilled','K':'same C top ceil(n/5) original E1','I':'same C and k, universe-proportional industry slots, top E1 within each','F':'exact sealed previous constrained E1 targets; risk <=.25 SD vs previous B, same industry slots'},auxiliary={'UI':'U with proportional industry slots at original k','KF':'K with 13 style bounds against old B, without industry slots','X':'original targets drop excluded stocks; original weights retained, removed budget cash'},main_comparisons=MAIN,reverse_and_cash=EXTRA,tie='score descending, instrument ascending',stat='descriptive 65-trading-day circular bootstrap, 2000 draws, seed20261117; no confirmatory p claim; CAGR difference separate from annual mean daily difference CI',attribution='difference of separately log-linked stock pnl and fees, common scale maps to final F minus O wealth; not unique causal decomposition',exclusions='reason per latest monthly rebalance signal; exact old latest-stock-weekly state bridge retained separately, global weekly stale-state audit added',no_search=True,no_new_training=True)
 cp=EP/'configs'/(RUN+'.json');assert not cp.exists();save_json(cp,cfg)
 files=[cp,Path(__file__)]+[EP/'src'/s for s in ['alpha_economics.py','e1_mechanism.py','e1_return_attribution.py','backtest.py','portfolio.py','suspension_sensitivity.py','common.py']]
 files += [PRIVATE/OLD/s for s in ['scores.parquet','targets.parquet','universe_audit.parquet','state_daily_attribution.parquet']]
 files += [PRIVATE/'e1_return_attribution_20261117/control_targets.parquet',PRIVATE/'e1_return_attribution_20261117/daily_active_stock_industry.parquet']
 files += [OUT/'diagnostics'/OLD/'selection_complete.json',OUT/'diagnostics'/OLD/'accounts/E1_main.csv']
 files += [PRIVATE/(s+'.parquet') for s in ['qfq_close','qfq_open','open','opening_trade_status_v2','daily_members','industry']]
 files += [PRIVATE/'limits/daily.parquet',PRIVATE/'suspensions/daily.parquet',PRIVATE/'weights/snapshots.parquet',PRIVATE/'net_excess_20261116/H00300.CSI.json']
 receipt=json.loads(ORIGINAL.with_suffix('.json').read_text());files += [ORIGINAL.with_suffix('.json'),ORIGINAL.with_suffix('.csv')]+[__import__('pathlib').Path(receipt[x+'_path']) for x in ['orders','holdings']]
 save_json(D/'freeze.json',dict(files=record(files),new_bridge_outcomes_computed=False));print('FROZEN',flush=True)

def prepare():
 verify();assert not (D/'selection_complete.json').exists()
 orig=pd.read_parquet(PRIVATE/'e1_return_attribution_20261117/control_targets.parquet');orig=orig[orig.control=='E1_REPLAY'];scores=pd.read_parquet(PRIVATE/OLD/'scores.parquet');previous=pd.read_parquet(PRIVATE/OLD/'targets.parquet');rows=[];audits=[];solvers=[]
 for date,o in orig.groupby('signal_date'):
  g=scores[scores.signal_date==date].sort_values('instrument').reset_index(drop=True);k0=len(o);k=int(np.ceil(len(g)/5));assert len(g)>=k0
  masks={'U':choose(g,k0),'K':choose(g,k),'I':choose(g,k,True),'UI':choose(g,k0,True)}
  b=previous[(previous.signal_date==date)&(previous.strategy=='B')];base=g.instrument.isin(b.instrument).to_numpy(float);assert base.sum()==k
  masks['KF'],info=risk_only(g,k,base);solvers.append(dict(signal_date=date,**info))
  f=previous[(previous.signal_date==date)&(previous.strategy=='E1')];assert len(f)==k
  for st,mask in masks.items():
   for j in np.flatnonzero(mask):rows.append(dict(signal_date=date,strategy=st,instrument=g.instrument.iloc[j],weight=1/int(mask.sum())))
  for st,frame in [('O',o),('F',f),('X',o[o.instrument.isin(g.instrument)])]:
   for r in frame.itertuples():rows.append(dict(signal_date=date,strategy=st,instrument=r.instrument,weight=r.weight))
  audits.append(dict(signal_date=date,n_C=len(g),original_k=k0,new_k=k,excluded_original_count=int((~o.instrument.isin(g.instrument)).sum()),excluded_original_budget=float(o.loc[~o.instrument.isin(g.instrument),'weight'].sum()),target_cash_X=float(o.loc[~o.instrument.isin(g.instrument),'weight'].sum())))
 write(pd.DataFrame(rows),'targets.parquet',True);write(pd.DataFrame(audits),'selection_audit.csv');write(pd.DataFrame(solvers),'reverse_solver.csv')
 save_json(D/'selection_complete.json',dict(files=record([L/'targets.parquet',D/'selection_audit.csv',D/'reverse_solver.csv']),new_bridge_outcomes_computed=False));print('SEALED targets',len(rows),flush=True)

def run():
 verify();verify('selection_complete');assert not (D/'accounts_complete.json').exists();inp=Inputs();marks(inp,0.);targets=pd.read_parquet(L/'targets.parquet');receipts=[]
 for st,g in targets.groupby('strategy'):
  maps={d:target_vector(inp,a) for d,a in g.groupby('signal_date')}
  for v in maps.values():v[-1]=max(0,1-v[:-1].sum())
  daily,orders,fail=run_account(inp,maps,sorted(maps),(.001,.002),end=END)
  write(daily,'accounts/'+st+'.csv');write(orders,'orders/'+st+'.parquet',True);receipts.append(dict(strategy=st,failures=fail,end=str(daily.date.max()),days=len(daily)));print(st,len(daily),fail,flush=True)
 save_json(D/'accounts_complete.json',dict(files=record(list((D/'accounts').glob('*.csv'))+list((L/'orders').glob('*.parquet'))),accounts=receipts))

def analyze():
 verify();verify('selection_complete');verify('accounts_complete');assert not (D/'analysis_complete.json').exists();inp=Inputs();marks(inp,0.);checks=[]
 def check(name,yes):assert bool(yes),name;checks.append(dict(name=name,passed=True))
 frames={p.stem:pd.read_csv(p,parse_dates=['date']).set_index('date') for p in (D/'accounts').glob('*.csv')};ids=frames['O'].index;n=len(ids)
 old=pd.read_csv(ORIGINAL.with_suffix('.csv'),parse_dates=['date']).set_index('date').loc[:END];new=pd.read_csv(OUT/'diagnostics'/OLD/'accounts/E1_main.csv',parse_dates=['date']).set_index('date').loc[:END]
 check('original O replay',ids.equals(old.index) and np.allclose(frames['O'].nav,old.nav,atol=1e-12,rtol=1e-12));check('final F replay',ids.equals(new.index) and np.allclose(frames['F'].nav,new.nav,atol=1e-12,rtol=1e-12))
 nav=pd.DataFrame({st:a.nav for st,a in frames.items()});write(nav.reset_index(),'navs.csv');components={};metrics=[];periods=[]
 for st,a in frames.items():
  check(st+' full common calendar',a.index.equals(ids));orders=pd.read_parquet(L/'orders'/(st+'.parquet'));c=absolute_components(inp,a,orders);r=daily_returns(a.nav);factor=np.divide(np.log1p(r),r,out=np.ones(n),where=abs(r)>1e-12);components[st]=c.mul(factor,axis=0);prev=a.nav.shift(fill_value=1)
  check(st+' stock components reconcile',np.isclose(components[st].to_numpy().sum(),np.log(a.nav.iloc[-1]),atol=1e-10))
  metrics.append(dict(strategy=st,days=n,cagr=a.nav.iloc[-1]**(252/n)-1,end_nav=a.nav.iloc[-1],cash=a.cash_weight.mean(),holdings=a.holdings.mean(),fees=a.fees.sum(),annual_oneway_turnover=float(((a.buy+a.sell)/(2*prev)).sum()*252/n)))
  for freq in ['Y','M']:
   for period,g in r.groupby(r.index.to_period(freq)):periods.append(dict(strategy=st,freq=freq,period=str(period),return_value=np.prod(1+g)-1))
 write(pd.DataFrame(metrics),'metrics.csv');write(pd.DataFrame(periods),'period_returns.csv')
 total=np.log(nav.F.iloc[-1]/nav.O.iloc[-1]);wealth=100*(nav.F.iloc[-1]-nav.O.iloc[-1]);scale=wealth/total
 stages=[];byperiod=[];bystock=[];byindustry=[]
 # Same original historical L1 mapping for every comparison date.
 indmaps={d:industry_map(inp,inp.days[inp.days.get_loc(d)-1]).to_dict() for d in ids}
 for before,after,name in MAIN+EXTRA:
  delta=components[after].subtract(components[before],fill_value=0);r=daily_returns(nav[after])-daily_returns(nav[before]);lo,hi=paired_ci(r);log=float(delta.to_numpy().sum());check(name+' component difference',np.isclose(log,np.log(nav[after].iloc[-1]/nav[before].iloc[-1]),atol=1e-10))
  stages.append(dict(stage=name,before=before,after=after,cagr_difference=nav[after].iloc[-1]**(252/n)-nav[before].iloc[-1]**(252/n),log_difference=log,wealth_contribution=log*scale,mean_daily_annual=r.mean()*252,ci_low=lo,ci_high=hi,main=(before,after,name) in MAIN))
  for freq in ['Y','M']:
   for period,g in delta.groupby(delta.index.to_period(freq)):byperiod.append(dict(stage=name,freq=freq,period=str(period),wealth_contribution=g.to_numpy().sum()*scale))
  for code,val in delta.sum().items():bystock.append(dict(stage=name,instrument=code,wealth_contribution=val*scale))
  buckets={}
  for d,row in delta.iterrows():
   for code,val in row.items():
    if val==0:continue
    industry=code if code.startswith('__') else indmaps[d].get(code,'UNKNOWN');key=(str(d.to_period('M')),industry);buckets[key]=buckets.get(key,0)+val*scale
  for (month,industry),v in buckets.items():byindustry.append(dict(stage=name,month=month,industry=industry,wealth_contribution=v))
 st=pd.DataFrame(stages);check('main wealth telescope',np.isclose(st.loc[st.main,'wealth_contribution'].sum(),wealth,atol=1e-9));check('main CAGR telescope',np.isclose(st.loc[st.main,'cagr_difference'].sum(),nav.F.iloc[-1]**(252/n)-nav.O.iloc[-1]**(252/n),atol=1e-12))
 write(st,'bridge.csv');write(pd.DataFrame(byperiod),'bridge_periods.csv');write(pd.DataFrame(bystock),'bridge_stocks.csv');write(pd.DataFrame(byindustry),'bridge_industry_months.csv')
 # Target and actual rebalance differences, transparent count/sector/risk interactions.
 targets=pd.read_parquet(L/'targets.parquet');overlaps=[]
 for before,after,name in MAIN+EXTRA:
  for date,g in targets.groupby('signal_date'):
   a=g[g.strategy==before].set_index('instrument').weight;b=g[g.strategy==after].set_index('instrument').weight;union=a.index.union(b.index);overlaps.append(dict(stage=name,signal_date=date,overlap_count=len(a.index.intersection(b.index)),before_count=len(a),after_count=len(b),half_L1_with_cash=.5*(abs(a.reindex(union,fill_value=0)-b.reindex(union,fill_value=0)).sum()+abs(a.sum()-b.sum()))))
 write(pd.DataFrame(overlaps),'target_changes.csv')
 # Reasons do not depend on outcomes. Map all original historical scored rows.
 audit=pd.read_parquet(PRIVATE/OLD/'universe_audit.parquet')
 def reason(row):
  if row.eligible:return 'IN_C'
  missing=[x for x in STYLES+['T','P'] if not np.isfinite(row[x])]
  if missing:return 'MISSING:'+','.join(missing)
  if row.industry=='UNKNOWN':return 'INDUSTRY_UNKNOWN'
  return str(row.reason)
 audit['exclusion_reason']=audit.apply(reason,axis=1);write(audit[['signal_date','instrument','eligible','industry','exclusion_reason']],'exclusion_definitions.parquet',True)
 ledger=pd.read_parquet(PRIVATE/'e1_return_attribution_20261117/daily_active_stock_industry.parquet');prev=pd.read_parquet(PRIVATE/OLD/'state_daily_attribution.parquet')
 joined=prev.merge(audit[['signal_date','instrument','exclusion_reason']],on=['signal_date','instrument'],how='left');joined.exclusion_reason=joined.exclusion_reason.fillna('NO_AVAILABLE_SIGNAL_ROW');joined.loc[joined.instrument.str.startswith('__'),'exclusion_reason']=joined.instrument
 oldunknown=joined[joined.state=='UNKNOWN'];check('old UNKNOWN exact bridge',np.isclose(oldunknown.wealth_contribution.sum(),19.389937,atol=1e-5));write(oldunknown.groupby('exclusion_reason').wealth_contribution.sum().reset_index(),'old_unknown_reasons.csv');write(oldunknown.groupby(['instrument','industry','exclusion_reason']).wealth_contribution.sum().reset_index(),'old_unknown_stocks.csv');write(oldunknown.groupby(['month','exclusion_reason']).wealth_contribution.sum().reset_index(),'old_unknown_months.csv')
 # Primary causal-description clock: latest monthly decision, strictly prior to PnL day.
 monthly=pd.DatetimeIndex(sorted(targets.signal_date.unique()));weekly=pd.DatetimeIndex(sorted(audit.signal_date.unique()));excluded=[]
 for clock,dates in [('monthly_decision',monthly),('weekly_global',weekly)]:
  a=ledger.copy();ix=dates.searchsorted(pd.DatetimeIndex(a.date),side='left')-1;check(clock+' prior signal exists',(ix>=0).all());a['signal_date']=dates[ix];a=a.merge(audit[['signal_date','instrument','exclusion_reason']],on=['signal_date','instrument'],how='left');a.exclusion_reason=a.exclusion_reason.fillna('OFF_SCORED_UNIVERSE_OR_NO_SIGNAL_ROW');a.loc[a.instrument.str.startswith('__'),'exclusion_reason']=a.instrument;a['clock']=clock;excluded.append(a)
 ex=pd.concat(excluded);write(ex,'exclusion_daily.parquet',True);write(ex.groupby(['clock','exclusion_reason']).wealth_contribution.sum().reset_index(),'exclusion_reasons.csv');write(ex.groupby(['clock','month','exclusion_reason']).wealth_contribution.sum().reset_index(),'exclusion_months.csv');write(ex.groupby(['clock','instrument','industry','exclusion_reason']).wealth_contribution.sum().reset_index(),'exclusion_stocks.csv')
 for clock,a in ex.groupby('clock'):check(clock+' original full wealth',np.isclose(a.wealth_contribution.sum(),ledger.wealth_contribution.sum(),atol=1e-10))
 # Stale weekly states in the previous study are identified rather than silently reused.
 codes=prev[~prev.instrument.str.startswith('__')].copy();ix=weekly.searchsorted(pd.DatetimeIndex(codes.date),side='left')-1;codes['global_signal']=weekly[ix];codes['stale_signal']=codes.signal_date!=codes.global_signal;write(codes.groupby('stale_signal').agg(rows=('instrument','size'),wealth_contribution=('wealth_contribution','sum')).reset_index(),'prior_state_staleness.csv')
 # Absolute stock pnl vs index opportunity charge for excluded holdings.
 receipt=json.loads(ORIGINAL.with_suffix('.json').read_text());h=pd.read_parquet(receipt['holdings_path']);h=h[h.date<=END];o=pd.read_parquet(receipt['orders_path']);o=o[o.date<=END].copy();o['trade_cash']=(o.units_after-o.units_before)*o.qfq_open
 values=h.assign(value=h.synthetic_units*h.valuation_close).pivot(index='date',columns='instrument',values='value').reindex(ids).fillna(0);tr=o.groupby(['date','instrument']).trade_cash.sum().unstack().reindex(index=ids,columns=values.columns).fillna(0);pnl=values-values.shift(fill_value=0)-tr;prevnav=frames['O'].nav.shift(fill_value=1);br=daily_returns(benchmark(ids));opportunity=values.shift(fill_value=0).div(prevnav,axis=0).mul(br,axis=0)
 raw=pnl.stack().rename('absolute_pnl').reset_index();raw['index_opportunity_return']=opportunity.stack().to_numpy();rows=ex[ex.clock=='monthly_decision'].merge(raw,on=['date','instrument'],how='left');write(rows.groupby('exclusion_reason').agg(absolute_pnl=('absolute_pnl','sum'),index_opportunity_return=('index_opportunity_return','sum'),linked_wealth_contribution=('wealth_contribution','sum')).reset_index(),'exclusion_pnl_vs_index.csv')
 save_json(D/'validation.json',dict(status='PASS',count=len(checks),checks=checks,original_to_final_wealth=wealth,original_to_final_cagr=nav.F.iloc[-1]**(252/n)-nav.O.iloc[-1]**(252/n)))
 verify();verify('selection_complete');verify('accounts_complete');save_json(D/'analysis_complete.json',dict(files=record(list(D.glob('*.csv'))+[D/'validation.json']+list(L.glob('*.parquet'))),status='DESCRIPTIVE_COMPLETE',no_causal_claim=True));print(st.to_string(index=False),flush=True)

from pathlib import Path
if __name__=='__main__':globals()[sys.argv[1]]()
