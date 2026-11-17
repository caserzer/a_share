"""EP36 frozen-prediction full-style historical-proxy economic falsification.

Selection is persisted before any event/continuous-account return calculation.
No result-driven tolerance changes, model fitting, or source overwrite.
"""
from datetime import datetime, timezone
import sys,json
import numpy as np
import pandas as pd
from scipy.optimize import milp, Bounds, LinearConstraint
from scipy.stats import rankdata
from common import EP,OUT,PRIVATE,sha,save_json,protocol
from evaluate_ranking import predictions
from alpha_falsification import PRICE,EXTRA,project,corr,rankcorr,calendar_bootstrap,holm

RUN='alpha_economics_20261117'
DEST=OUT/'diagnostics'/RUN
LOCAL=PRIVATE/RUN
CONFIG=EP/'configs'/(RUN+'.json')
STYLES=PRICE+EXTRA+['log_total_mv','log_circ_mv']
MODELS=['E1','E2']
COSTS={'zero':(0.,0.),'main':(.001,.002),'stress':(.003,.008)}


def freeze():
 if CONFIG.exists():raise RuntimeError('Immutable registration exists')
 DEST.mkdir(parents=True,exist_ok=True);LOCAL.mkdir(parents=True,exist_ok=True)
 _,consumed=predictions('expanding')
 cfg=dict(run=RUN,created_at=datetime.now(timezone.utc).isoformat(),authorization='User continue execution of A2 B1 B2, including necessary historical capitalization audit',
 evidence='historical_simulated_oos_post_selection_exploration',forward='FORWARD_PENDING',prior_A1_results_seen=True,new_economic_results_seen=False,
 models=MODELS,scheme='expanding',primary_start='2021-01-08',primary_end='2025-03-03',
 caps='Tushare daily_basic previous market-session exact snapshot; total_mv and circ_mv in 10000 yuan; log of positive values; circ_mv means circulating, not free-float. No current-share-count reconstruction; retrospective proxy without known_at certification',
 cap_audit='Require positive close/share/mv; identity close*total_share=total_mv and close*float_share=circ_mv within 1e-4 relative; compare vendor raw close to sealed prior-day close within 0.01yuan+1e-5relative; reject conflicts, no fill',
 styles=STYLES,industry='Historical L1 as A1, UNKNOWN retained',
 sample='Common E1/E2 finite score and all13 style values; industry may UNKNOWN. All score projections same sample; at least100 stocks,50 residual df; labels excluded from target construction',
 decomposition='OLS SVD rcond1e-12, intercept+all13 standardized styles+industry dummies; no retraining. Original/explained/residual scores persist before reading labels',
 strategies=dict(S0='Q5 by projected style-copy score; not independent return-trained style baseline',S1='maximize original score ranks under exposures relative to S0',S2='maximize residual score ranks under same exposures relative to S0'),
 cardinality='k=n-sum(floor(5*j/n)<4); exactly k equal-weight positions per strategy; lexicographic instrument tie-break',
 matching=dict(numerical_max_abs_sd=.25,industry_max_abs_weight=.02,objective='mean within-signal score rank, unit interval; no realized return',solver='scipy milp HiGHS, binary equalweight selections, time_limit=2 sec, mip_rel_gap=.01',
 no_solver_fallback='S0 is a feasible witness. If no verified incumbent or any constraints fail: all strategies NO_TARGET for that model/date; no tolerance relaxation; gap/status recorded',
 account_risk='Constraints apply at signal target. Actual fills and drift can breach; report post-trade frozen-signal exposures and unmatched budget; label partial execution matching, not risk-certified account'),
 phases='month first and second original weekly signal; no four-phase common requirement',
 primary_A2='phase1 fixed H10 main-cost net event S1-S0 and S2-S0; paired events including failure rows; label partial identification when valuation/exit/matching unknown',
 primary_B1='monthly paired [(S1-S0)phase1-(S1-S0)phase2] at H10 main cost',
 test_family='E1 primary A2 two contrasts + B1 one contrast, Holm3; all E2/horizons/full/costs/continuous accounts auxiliary',
 events='Fixed list at signal; next open enter; endpoints open t+1+5/10/20; no retarget; entry gates and exit sell gates; if cannot fully exit net-return unknown, mark remaining budget; no future outcome selection. Marked path separately, never assumed liquidation',
 marginal='On same event units/common initial capital: entry-to5 includes entry fee; 5to10 and10to20 mark differences no repeat entry/exit fee; separate independent terminal liquidation fee by horizon; compare strategy-control on same observed paths',
 valuation='Reuse verified full-day suspension <=20-session flat mark proxy from earlier studies; raw opening gates unchanged; unknown held open/close stops account; no mergers/terminal payoff fabrication',
 costs_bps={'zero':[0,0],'main':[10,20],'stress':[30,80]},
 continuous='independent weekly, calendar biweekly anchored first week, monthly phase1; common initial first signal, cash if no target; days to original data end or first unsupported holding valuation; compare same scope common endpoint',
 placebo=dict(replicates=20,seed=20261117,groups='Industry x within-industry median log_total_mv x within-industry median mom20; exact S1 per-cell cardinality',draws_per_replicate=100,
 acceptance='Uniform no-replacement within each cell, accept first draw meeting same numeric/industry tolerance vs S0; draw failure retained, never expand bounds',
 analysis='phases1/2; same next-open and liquidation gates, main cost H10; S1 minus placebo relative to S0 phase difference; each replicate fixed in advance, no best-seed selection'),
 stats=dict(month_blocks=3,weekly_blocks=13,daily_blocks=65,replicates=2000,seed=20261117,calendar_gaps='preserve missing periods',min_valid_blocks=2,ci='percentile95',p='centered two-sided +1',selection='No equivalence claim from nonsignificance'),
 breakeven=dict(buy_bps_range=[0,100],sell_buy_ratio=2,grid_step_bps=10,bisection_steps=12,root='equal terminal NAV of 2w and phase1 monthly S1 on primary common endpoint',no_root='report no sign-changing crossing in audited range, not universal absence'),
 no_search='No model upgrade, phase optimization, risk-tolerance widening or best-horizon selection')
 save_json(CONFIG,cfg)
 files=[PRIVATE/'alpha_falsification_20261117/styles.parquet',PRIVATE/'style_caps_20261117/signal_caps.parquet',OUT/'data_audit/style_caps_20261117.json']
 files += [PRIVATE/(n+'.parquet') for n in ['labels','qfq_close','qfq_open','close','open','opening_trade_status_v2','daily_members','industry','market']]
 files += [PRIVATE/'limits/daily.parquet',PRIVATE/'suspensions/daily.parquet',PRIVATE/'weights/snapshots.parquet']
 sources=[EP/'src'/n for n in ['alpha_economics.py','alpha_falsification.py','backtest.py','portfolio.py','suspension_sensitivity.py','common.py']]
 save_json(DEST/'freeze.json',dict(config_sha256=sha(CONFIG),predictions=consumed,inputs=[dict(path=str(p),sha256=sha(p)) for p in files],sources=[dict(path=str(p),sha256=sha(p)) for p in sources],new_economic_outcomes_seen=False))
 print('frozen',RUN,flush=True)


def verify():
 f=json.loads((DEST/'freeze.json').read_text());assert sha(CONFIG)==f['config_sha256']
 for r in f['inputs']+f['sources']+f['predictions']:assert sha(r['path'])==r['sha256'],r['path']
 return json.loads(CONFIG.read_text()),f


def topk(scores,k,instruments):
 return np.lexsort((np.asarray(instruments),np.asarray(scores)))[-k:]


def matrix(g):
 z=g[STYLES].to_numpy(float);sd=z.std(axis=0);sd[sd<1e-12]=1.
 z=(z-z.mean(axis=0))/sd
 ind=pd.get_dummies(g.industry).to_numpy(float)
 return z,ind,np.column_stack([np.ones(len(g)),z,ind[:,1:]])


def matched_selection(score,z,ind,base,k,seconds=2):
 n=len(score);a=np.column_stack([z,ind]).T/k
 target=a@base
 tol=np.r_[np.full(z.shape[1],.25),np.full(ind.shape[1],.02)]
 constraints=LinearConstraint(np.vstack([np.ones(n),a]),np.r_[k,target-tol],np.r_[k,target+tol])
 objective=-rankdata(score)/n
 result=milp(objective,integrality=np.ones(n),bounds=Bounds(np.zeros(n),np.ones(n)),constraints=constraints,options={'time_limit':seconds,'mip_rel_gap':.01})
 info=dict(solver_status=int(result.status),solver_message=result.message,mip_gap=float(getattr(result,'mip_gap',np.nan)),nodes=int(getattr(result,'mip_node_count',0) or 0))
 if result.x is None:return None,info
 selected=(result.x>.5).astype(float)
 delta=a@(selected-base)
 valid=selected.sum()==k and np.all(np.abs(delta)<=tol+1e-7)
 info.update(numeric_gap=float(np.max(np.abs(delta[:z.shape[1]]))),industry_gap=float(np.max(np.abs(delta[z.shape[1]:]))))
 return (selected if valid else None),info


def prepare():
 cfg,frozen=verify()
 if (DEST/'selection_complete.json').exists():raise RuntimeError('Selection already sealed')
 cap=pd.read_parquet(PRIVATE/'style_caps_20261117/signal_caps.parquet')
 raw=pd.read_parquet(PRIVATE/'close.parquet')
 ix=raw.index.get_indexer(cap.source_date);jx=raw.columns.get_indexer(cap.instrument)
 old=np.full(len(cap),np.nan);valid=(ix>=0)&(jx>=0);old[valid]=raw.to_numpy()[ix[valid],jx[valid]]
 cap['vendor_close_conflict']=~np.isfinite(old)|(np.abs(cap.close-old)>(.01+1e-5*np.abs(old)))
 cap['identity_conflict']=False
 for mv,shares in [('total_mv','total_share'),('circ_mv','float_share')]:
  lhs=cap.close*cap[shares];cap['identity_conflict']|=~(cap[mv]>0)|~(cap[shares]>0)|(np.abs(lhs-cap[mv])>np.maximum(.01,cap[mv].abs()*1e-4))
 cap['accepted']=~cap.vendor_close_conflict&~cap.identity_conflict&(cap.source_date<cap.signal_date)
 for col in ['total_mv','circ_mv']:cap['log_'+col]=np.log(cap[col].where(cap.accepted))
 cap.to_parquet(LOCAL/'cap_audit_rows.parquet',index=False)
 styles=pd.read_parquet(PRIVATE/'alpha_falsification_20261117/styles.parquet')
 p,_=predictions('expanding');p=p[p.model_id.isin(MODELS)&p.seed_or_ensemble.isin(['fixed','equal_seed_ensemble'])]
 wide=p.pivot(index=['signal_date','instrument'],columns='model_id',values='score').reset_index()
 g=styles.merge(wide,on=['signal_date','instrument'],validate='one_to_one').merge(cap[['signal_date','instrument','source_date','log_total_mv','log_circ_mv']],on=['signal_date','instrument'],how='left',validate='one_to_one')
 audit=g.groupby('signal_date').size().rename('original').to_frame()
 common=g.dropna(subset=STYLES+MODELS).sort_values(['signal_date','instrument'])
 audit['common']=common.groupby('signal_date').size();audit['cap_source_rows']=cap.groupby('signal_date').size();audit['cap_rejected']=cap.loc[~cap.accepted].groupby('signal_date').size().reindex(audit.index,fill_value=0)
 audit.to_csv(DEST/'coverage.csv')
 save_json(DEST/'cap_audit.json',dict(rows=len(cap),accepted=int(cap.accepted.sum()),close_conflicts=int(cap.vendor_close_conflict.sum()),identity_conflicts=int(cap.identity_conflict.sum()),source_lag='one market session',strict_PIT=False,quality='Historical-proxy',first_vintage_known_at=None,field_semantics='circ_mv circulating market value, not free-float',source_doc='https://tushare.pro/document/2?doc_id=32'))
 dates=pd.DatetimeIndex(sorted(wide.signal_date.unique()));phases=pd.Series(dates).groupby(dates.to_period('M')).cumcount()+1
 schedule=pd.DataFrame(dict(signal_date=dates,phase=phases.to_numpy()));schedule.to_csv(DEST/'schedule.csv',index=False)
 score_rows=[];target_rows=[];solver_rows=[];recon=[];placebo_rows=[];overlap=[]
 rng=np.random.default_rng(20261117)
 for number,(date,day) in enumerate(common.groupby('signal_date')):
  phase=int(schedule.loc[schedule.signal_date.eq(date),'phase'].iloc[0]);n=len(day);k=n-int(np.sum(np.floor(5*np.arange(n)/n)<4))
  if n<100:continue
  z,ind,x=matrix(day)
  for model in MODELS:
   score=day[model].to_numpy();fitted,res,q,rank=project(x,score)
   if n-rank<50:continue
   row=day[['signal_date','instrument','industry','source_date']+STYLES].copy();row['model']=model;row['S0']=fitted;row['S1']=score;row['S2']=res
   score_rows.append(row)
   r2=1-np.sum(res**2)/np.sum((score-score.mean())**2)
   recon.append(dict(model=model,signal_date=date,n=n,rank=rank,r2=r2,rank_correlation=rankcorr(score,fitted)))
   base=np.zeros(n);base[topk(fitted,k,day.instrument)]=1
   selected={'S0':base};infos=[]
   for strategy,sc in [('S1',score),('S2',res)]:
    picked,info=matched_selection(sc,z,ind,base,k)
    infos.append(dict(model=model,signal_date=date,strategy=strategy,n=n,k=k,accepted=picked is not None,**info))
    if picked is not None:selected[strategy]=picked
   solver_rows.extend(infos)
   if len(selected)!=3:continue
   rawq=np.zeros(n);rawq[topk(score,k,day.instrument)]=1
   overlap.append(dict(model=model,signal_date=date,q5_overlap=float(rawq@selected['S1']/k),s1_s0_overlap=float(base@selected['S1']/k),s2_s0_overlap=float(base@selected['S2']/k)))
   for strategy,mask in selected.items():
    for j in np.flatnonzero(mask):target_rows.append(dict(model=model,signal_date=date,strategy=strategy,instrument=day.instrument.iloc[j],weight=1/k,k=k))
   if phase in [1,2]:
    # Exact cell quotas from S1; median splits fixed ex ante, no outcome-dependent bins.
    size=day.groupby('industry').log_total_mv.transform(lambda a:(a>a.median()).astype(int)).to_numpy()
    mom=day.groupby('industry').mom20.transform(lambda a:(a>a.median()).astype(int)).to_numpy()
    groups=day.industry.astype(str).to_numpy()+'|'+size.astype(str)+'|'+mom.astype(str)
    cells=[(np.flatnonzero(groups==v),int(selected['S1'][groups==v].sum())) for v in sorted(set(groups))]
    for replicate in range(20):
     pick=None;maxgap=np.nan
     for attempt in range(100):
      candidate=np.zeros(n)
      for ids,count in cells:
       if count:candidate[rng.choice(ids,count,replace=False)]=1
      delta=z.T@(candidate-base)/k;maxgap=float(np.max(np.abs(delta)))
      if maxgap<=.25+1e-7 and np.max(np.abs(ind.T@(candidate-base)/k))<=.02+1e-7:pick=candidate;break
     placebo_rows.append(dict(model=model,signal_date=date,replicate=replicate,accepted=pick is not None,attempts=attempt+1,numeric_gap=maxgap))
     if pick is not None:
      for j in np.flatnonzero(pick):target_rows.append(dict(model=model,signal_date=date,strategy=f'P{replicate:02}',instrument=day.instrument.iloc[j],weight=1/k,k=k))
  if number%20==0:print('selection',number+1,len(dates),str(date.date()),flush=True)
 pd.concat(score_rows,ignore_index=True).to_parquet(LOCAL/'scores.parquet',index=False)
 pd.DataFrame(target_rows).to_parquet(LOCAL/'targets.parquet',index=False)
 pd.DataFrame(solver_rows).to_csv(DEST/'solver.csv',index=False)
 pd.DataFrame(recon).to_csv(DEST/'reconstruction.csv',index=False)
 pd.DataFrame(placebo_rows).to_csv(DEST/'placebo_coverage.csv',index=False)
 pd.DataFrame(overlap).to_csv(DEST/'selection_overlap.csv',index=False)
 verify()
 files=[LOCAL/'scores.parquet',LOCAL/'targets.parquet',LOCAL/'cap_audit_rows.parquet',DEST/'solver.csv',DEST/'coverage.csv',DEST/'schedule.csv',DEST/'reconstruction.csv',DEST/'placebo_coverage.csv',DEST/'selection_overlap.csv',DEST/'cap_audit.json']
 save_json(DEST/'selection_complete.json',dict(files=[dict(path=str(p),sha256=sha(p)) for p in files],labels_read=False,economic_outcomes_read=False,config_sha256=frozen['config_sha256']))
 print('selection sealed',flush=True)


def selected_inputs():
 cfg,fr=verify();sel=json.loads((DEST/'selection_complete.json').read_text())
 for r in sel['files']:assert sha(r['path'])==r['sha256']
 from backtest import Inputs
 from suspension_sensitivity import marks
 inp=Inputs();marks(inp,0.)
 targets=pd.read_parquet(LOCAL/'targets.parquet')
 return inp,targets,pd.read_csv(DEST/'schedule.csv',parse_dates=['signal_date'])


def target_vector(inp,rows):
 v=np.zeros(inp.n+1);v[inp.symbols.get_indexer(rows.instrument)]=rows.weight.to_numpy();return v


def event_path(inp,si,target,bf,sf):
 """One entry, fixed units; separate marked paths and independently liquidated endpoints."""
 from portfolio import trade
 ei=si+1;rows=[];path=[]
 if ei>=len(inp.days):return rows,path
 member,_,_,_,_,buy,_,_=inp.context(si,ei)
 units,cash,entry=trade(np.zeros(inp.n),1.,inp.o[ei],target,buy&member,np.zeros(inp.n,bool),bf,sf)
 held=units>0
 for h in range(21):
  j=ei+h;reason='';mark=np.nan
  if j>=len(inp.days):reason='END_OUTSIDE_DATA'
  elif np.any(held&~np.isfinite(inp.o[j])) or np.any(~np.isfinite(inp.c[ei:j,held])):reason='HELD_VALUATION_UNKNOWN'
  else:mark=float(cash+units@np.nan_to_num(inp.o[j]))
  path.append(dict(horizon=h,mark=mark,reason=reason))
  if h not in [5,10,20]:continue
  base=dict(horizon=h,entry_date=inp.days[ei],exit_date=inp.days[j] if j<len(inp.days) else pd.NaT,marked_return=mark-1,entry_fees=entry['fees'],unfilled_buy=entry['unfilled_buy'],entry_cash=cash,actual_holdings=int(held.sum()),reason=reason,net_return=np.nan,exit_fees=np.nan,unsold_weight=np.nan)
  if not reason:
   _,_,_,_,_,_,sell,_=inp.context(si,j)
   new,terminal,info=trade(units.copy(),cash,inp.o[j],np.r_[np.zeros(inp.n),1.],np.zeros(inp.n,bool),sell,bf,sf)
   unsold=float(new@np.nan_to_num(inp.o[j]))
   base.update(exit_fees=info['fees'],unsold_weight=unsold/mark)
   if np.any(new>1e-12):base['reason']='EXIT_NOT_FULLY_TRADEABLE'
   else:base['net_return']=terminal-1
  rows.append(base)
 return rows,path


def events():
 inp,targets,schedule=selected_inputs()
 if (DEST/'events_complete.json').exists():raise RuntimeError('Events already sealed')
 phase=schedule.set_index('signal_date').phase.to_dict();rows=[];paths=[]
 for number,((model,date,strategy),g) in enumerate(targets.groupby(['model','signal_date','strategy'])):
  if phase[date] not in [1,2]:continue
  si=inp.days.get_loc(date);v=target_vector(inp,g)
  costs=['main'] if strategy.startswith('P') else list(COSTS)
  for cost in costs:
   r,path=event_path(inp,si,v,*COSTS[cost]);key=dict(model=model,signal_date=date,phase=phase[date],strategy=strategy,cost=cost)
   rows.extend(key|row for row in r)
   if cost=='main':paths.extend(key|row for row in path)
  if number%300==0:print('events group',number,flush=True)
 pd.DataFrame(rows).to_csv(DEST/'events.csv',index=False)
 pd.DataFrame(paths).to_csv(DEST/'event_paths.csv',index=False)
 save_json(DEST/'events_complete.json',dict(files=[dict(path=str(DEST/name),sha256=sha(DEST/name)) for name in ['events.csv','event_paths.csv']],selection_sha256=sha(DEST/'selection_complete.json')))
 print('event rows',len(rows),flush=True)


def date_schedule(dates,freq):
 dates=pd.DatetimeIndex(sorted(dates))
 if freq=='1w':return dates
 if freq=='2w':return dates[(dates.to_period('W-FRI').asi8-dates[0].to_period('W-FRI').ordinal)%2==0]
 return dates[~dates.to_period('M').duplicated()]


def run_account(inp,targetmap,dates,fees,end=None,keep_orders=True):
 from portfolio import trade
 units=np.zeros(inp.n);cash=1.;daily=[];orders=[];fail=[];previous=1.
 signals={inp.days.get_loc(d)+1:inp.days.get_loc(d) for d in dates if inp.days.get_loc(d)+1<len(inp.days)}
 for i in range(min(signals),len(inp.days)):
  if end is not None and inp.days[i]>pd.Timestamp(end):break
  day=inp.days[i];row=dict(date=day,buy=0.,sell=0.,fees=0.,unfilled_buy=0.,unfilled_sell=0.,target_status='')
  if i in signals:
   si=signals[i];date=inp.days[si];target=targetmap.get(date)
   if target is None:row['target_status']='NO_VERIFIED_TARGET'
   else:
    member,_,_,_,_,buy,sell,_=inp.context(si,i)
    if np.any((units>0)&~np.isfinite(inp.o[i])):fail.append(dict(date=day,reason='HELD_OPEN_VALUATION_UNKNOWN'));break
    old=units.copy();units,cash,info=trade(units,cash,inp.o[i],target,buy&member,sell,*fees)
    row.update(info);row['target_status']='EXECUTED';row['signal_date']=date
    value=units*np.nan_to_num(inp.o[i]);nav=cash+value.sum()
    if keep_orders:
     for j in np.flatnonzero((old>0)|(units>0)|(target[:-1]>0)):
      orders.append(dict(date=day,signal_date=date,instrument=inp.symbols[j],units_before=old[j],units_after=units[j],target_weight=target[j],actual_weight=value[j]/nav,can_buy=bool(buy[j]&member[j]),can_sell=bool(sell[j]),pretrade_nav=info['pretrade_nav'],price=inp.o[i,j],cash_weight=cash/nav))
  if np.any((units>0)&~np.isfinite(inp.c[i])):fail.append(dict(date=day,reason='HELD_CLOSE_VALUATION_UNKNOWN'));break
  nav=cash+units@np.nan_to_num(inp.c[i]);row.update(nav=float(nav),daily_return=float(nav/previous-1),cash_weight=float(cash/nav),holdings=int((units>0).sum()));previous=nav;daily.append(row)
 return pd.DataFrame(daily),pd.DataFrame(orders),fail


def accounts():
 inp,targets,schedule=selected_inputs();dest=DEST/'accounts';dest.mkdir(exist_ok=True);local=LOCAL/'accounts';local.mkdir(exist_ok=True)
 for model in MODELS:
  for freq in ['1w','2w','1m']:
   dates=date_schedule(schedule.signal_date,freq)
   for strategy in ['S0','S1','S2']:
    g=targets[(targets.model==model)&(targets.strategy==strategy)]
    mapping={d:target_vector(inp,x) for d,x in g.groupby('signal_date')}
    for cost,fees in COSTS.items():
     key=f'{model}_{strategy}_{freq}_{cost}';receipt=dest/(key+'.json')
     if receipt.exists():
      rec=json.loads(receipt.read_text());assert sha(dest/(key+'.csv'))==rec['nav_sha256'];continue
     daily,orders,fail=run_account(inp,mapping,dates,fees)
     daily.to_csv(dest/(key+'.csv'),index=False);orders.to_parquet(local/(key+'.parquet'),index=False)
     save_json(receipt,dict(key=key,model=model,strategy=strategy,frequency=freq,cost=cost,failures=fail,nav_sha256=sha(dest/(key+'.csv')),orders_path=str(local/(key+'.parquet')),orders_sha256=sha(local/(key+'.parquet')),selection_sha256=sha(DEST/'selection_complete.json')))
     print('account',key,len(daily),fail,flush=True)


if __name__=='__main__':
 {'freeze':freeze,'prepare':prepare,'events':events,'accounts':accounts,'verify':verify}[sys.argv[1]]()
