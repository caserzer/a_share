"""Analysis of sealed EP36 economic targets, event paths and independent accounts."""
import json
import numpy as np
import pandas as pd
from common import EP,PRIVATE,sha,save_json
from alpha_economics import DEST,LOCAL,CONFIG,MODELS,STYLES,COSTS,verify,matrix,selected_inputs,target_vector,date_schedule,run_account
from alpha_falsification import project,rankcorr,corr,calendar_bootstrap,holm


def boot(series,freq='M',L=3):
 s=series.copy();s.index=pd.PeriodIndex(s.index,freq=freq)
 assert not s.index.duplicated().any()
 a=s.reindex(pd.period_range(s.index.min(),s.index.max(),freq=freq)).to_numpy(float)
 n=np.isfinite(a).sum();mu=float(np.nanmean(a)) if n else np.nan
 out=dict(n=int(n),planned_periods=len(a),mean=mu,ci_low=np.nan,ci_high=np.nan,p=np.nan)
 if n<2*L:return out
 rng=np.random.default_rng(20261117);length=len(a);starts=rng.integers(0,length,(2000,int(np.ceil(length/L))))
 idx=((starts[:,:,None]+np.arange(L))%length).reshape(2000,-1)[:,:length]
 count=np.isfinite(a[idx]).sum(axis=1);sums=np.nansum(a[idx],axis=1);means=np.divide(sums,count,out=np.full(2000,np.nan),where=count>0)
 lo,hi=np.nanquantile(means,[.025,.975]);p=(1+np.sum(np.abs(means-mu)>=abs(mu)))/(1+np.isfinite(means).sum())
 return out|dict(ci_low=float(lo),ci_high=float(hi),p=float(p))


def a1_caps():
 verify();scores=pd.read_parquet(LOCAL/'scores.parquet');labels=pd.read_parquet(PRIVATE/'labels.parquet')
 rows=[]
 for (model,date),g in scores.merge(labels,on=['signal_date','instrument'],validate='many_to_one').groupby(['model','signal_date']):
  for horizon in ['h5','h10','h20']:
   v=g.dropna(subset=[horizon]);r=dict(model=model,signal_date=date,horizon=horizon,n=len(v),mature=v[horizon+'_mature'].max())
   if len(v)>=100:
    _,_,x=matrix(v);s=v.S1.to_numpy();y=v[horizon].to_numpy();ss=(s-s.mean())/s.std()
    _,sr,_,_=project(x,ss);_,yr,_,_=project(x,y)
    from scipy.stats import rankdata
    _,rs,_,_=project(x,rankdata(s));_,ry,_,_=project(x,rankdata(y))
    r.update(original_ic=rankcorr(s,y),explained_ic=rankcorr(v.S0,y),residual_ic=rankcorr(v.S2,y),partial_rank_ic=corr(rs,ry),conditional_slope=float(sr@yr/(sr@sr)))
   rows.append(r)
 detail=pd.DataFrame(rows);detail.to_csv(DEST/'a1_caps_weekly.csv',index=False);result=[]
 for scope in ['primary','extended']:
  for (model,h),g in detail.groupby(['model','horizon']):
   if scope=='primary':g=g[g.signal_date.between('2021-01-08','2025-03-03')].copy();g.loc[g.mature>pd.Timestamp('2025-03-03'),['original_ic','explained_ic','residual_ic','partial_rank_ic','conditional_slope']]=np.nan
   for metric in ['original_ic','explained_ic','residual_ic','partial_rank_ic','conditional_slope']:
    result.append(dict(scope=scope,model=model,horizon=h,metric=metric,**calendar_bootstrap(g.set_index('signal_date')[metric])))
 pd.DataFrame(result).to_csv(DEST/'a1_caps_summary.csv',index=False)


def event_exposures():
 inp,targets,schedule=selected_inputs();scores=pd.read_parquet(LOCAL/'scores.parquet');rows=[]
 lookup={key:g for key,g in targets.groupby(['model','signal_date','strategy'])}
 for (model,date),g in scores.groupby(['model','signal_date']):
  if int(schedule.set_index('signal_date').loc[date,'phase']) not in [1,2]:continue
  z,ind,_=matrix(g);si=inp.days.get_loc(date);ei=si+1
  member,_,_,_,_,buy,_,_=inp.context(si,ei)
  localids=inp.symbols.get_indexer(g.instrument);allowed=(buy&member)[localids]
  values={};cash={}
  for strategy in ['S0','S1','S2']:
   key=(model,date,strategy)
   if key not in lookup:continue
   weights=lookup[key].set_index('instrument').weight.reindex(g.instrument).fillna(0).to_numpy()
   # Fee-constrained entry from unit cash, exact same scaling as trade().
   purchased=weights*allowed;scale=min(1.,1/(purchased.sum()*1.001)) if purchased.sum()>0 else 1.
   value=purchased*scale;remaining=1-value.sum()*1.001;nav=remaining+value.sum()
   values[strategy]=value/nav;cash[strategy]=remaining/nav
  for strategy in ['S1','S2']:
   if strategy not in values or 'S0' not in values:continue
   delta=values[strategy]-values['S0'];num=z.T@delta;industry=ind.T@delta
   rows.append(dict(model=model,signal_date=date,strategy=strategy,numeric_gap=float(np.abs(num).max()),industry_gap=float(np.abs(industry).max()),cash_gap=cash[strategy]-cash['S0'],risk_within_target_bounds=bool(np.abs(num).max()<=.25+1e-7 and np.abs(industry).max()<=.02+1e-7),s0_cash=cash['S0'],strategy_cash=cash[strategy]))
 pd.DataFrame(rows).to_csv(DEST/'event_exposures.csv',index=False)


def event_stats():
 f=pd.read_csv(DEST/'events.csv',parse_dates=['signal_date','entry_date','exit_date'])
 schedule=pd.read_csv(DEST/'schedule.csv',parse_dates=['signal_date']);days=pd.read_parquet(PRIVATE/'qfq_close.parquet').index
 risk=pd.read_csv(DEST/'event_exposures.csv',parse_dates=['signal_date'])
 rows=[];monthly=[];yearly=[];coverage=[]
 for scope in ['primary','extended']:
  for h in [5,10,20]:
   cal=schedule[schedule.phase.isin([1,2])].copy()
   positions=days.get_indexer(cal.signal_date)+1+h
   cal['exit_date']=[days[i] if i<len(days) else pd.NaT for i in positions]
   end=pd.Timestamp('2025-03-03') if scope=='primary' else days[-1]
   cal=cal[cal.exit_date.notna()&cal.exit_date.le(end)];cal['month']=cal.signal_date.dt.to_period('M')
   for model in MODELS:
    for cost in COSTS:
     subset=f[(f.model==model)&(f.horizon==h)&(f.cost==cost)]
     pivot=subset.pivot(index='signal_date',columns='strategy',values='net_return').reindex(cal.signal_date)
     pivot.index=cal.index
     for strategy in ['S1','S2']:
      vals=cal.copy();vals['difference']=pivot[strategy]-pivot.S0
      for phase in [1,2]:
       v=vals[vals.phase==phase].set_index('month').difference
       result=dict(scope=scope,model=model,cost=cost,horizon=h,contrast=strategy+'-S0',experiment='A2_phase'+str(phase),**boot(v))
       rows.append(result)
      pair=vals.pivot(index='month',columns='phase',values='difference').reindex(columns=[1,2]);d=pair[1]-pair[2]
      rows.append(dict(scope=scope,model=model,cost=cost,horizon=h,contrast=strategy+'-S0',experiment='B1_phase1-phase2',**boot(d)))
      for month in pair.index:monthly.append(dict(scope=scope,model=model,cost=cost,horizon=h,contrast=strategy+'-S0',month=str(month),phase1=pair.loc[month,1],phase2=pair.loc[month,2],phase_difference=d.loc[month]))
      if scope=='primary' and h==10 and cost=='main':
       for yr,vg in vals.groupby(vals.signal_date.dt.year):
        yearly.append(dict(model=model,contrast=strategy+'-S0',year=yr,phase1_mean=vg.loc[vg.phase==1,'difference'].mean(),phase2_mean=vg.loc[vg.phase==2,'difference'].mean(),paired_months=int(d[d.index.year==yr].count()),phase_difference=d[d.index.year==yr].mean()))
       # Secondary executed-risk-restricted subset, never replaces frozen primary family.
       bounded=vals.merge(risk[(risk.model==model)&(risk.strategy==strategy)][['signal_date','risk_within_target_bounds']],on='signal_date',how='left')
       bounded.loc[~bounded.risk_within_target_bounds.fillna(False),'difference']=np.nan
       v=bounded[bounded.phase==1].set_index('month').difference
       rows.append(dict(scope=scope,model=model,cost=cost,horizon=h,contrast=strategy+'-S0',experiment='A2_executed_risk_subset',**boot(v)))
     planned=len(cal)
     for strategy in ['S0','S1','S2']:
      x=subset[subset.strategy==strategy].set_index('signal_date').reindex(cal.signal_date)
      coverage.append(dict(scope=scope,model=model,cost=cost,horizon=h,strategy=strategy,planned_events=planned,rows_present=int(x.horizon.notna().sum()),known_net=int(x.net_return.notna().sum()),mean_unfilled_buy=x.unfilled_buy.mean(),mean_unsold=x.unsold_weight.mean(),mean_entry_cash=x.entry_cash.mean(),mean_holdings=x.actual_holdings.mean()))
 s=pd.DataFrame(rows);s['holm_p']=np.nan
 family=(s.scope=='primary')&(s.model=='E1')&(s.horizon==10)&(s.cost=='main')&((s.experiment=='A2_phase1')|((s.experiment=='B1_phase1-phase2')&(s.contrast=='S1-S0')))
 assert family.sum()==3;s.loc[family,'holm_p']=holm(s.loc[family,'p'])
 s.to_csv(DEST/'event_summary.csv',index=False);pd.DataFrame(monthly).to_csv(DEST/'monthly_pairs.csv',index=False);pd.DataFrame(yearly).to_csv(DEST/'event_yearly.csv',index=False);pd.DataFrame(coverage).to_csv(DEST/'event_coverage.csv',index=False)
 print(s[family].to_string(index=False),flush=True)
 # Placebo replicates include unavailable draws as missing, not zeros.
 prows=[]
 cal=schedule[schedule.phase.isin([1,2])].copy();cal['month']=cal.signal_date.dt.to_period('M');pos=days.get_indexer(cal.signal_date)+11
 cal=cal[[i<len(days) and days[i]<=pd.Timestamp('2025-03-03') for i in pos]]
 for model in MODELS:
  g=f[(f.model==model)&(f.cost=='main')&(f.horizon==10)]
  v=g.pivot(index='signal_date',columns='strategy',values='net_return').reindex(cal.signal_date)
  for r in range(20):
   name=f'P{r:02}';d=cal.copy();d['difference']=v.S1.to_numpy()-v.get(name,pd.Series(np.nan,index=v.index)).to_numpy()
   pair=d.pivot(index='month',columns='phase',values='difference').reindex(columns=[1,2])
   prows.append(dict(model=model,replicate=r,**boot(pair[1]-pair[2])))
 pd.DataFrame(prows).to_csv(DEST/'placebo_summary.csv',index=False)


def paths():
 f=pd.read_csv(DEST/'event_paths.csv',parse_dates=['signal_date']);cal=pd.read_csv(DEST/'schedule.csv',parse_dates=['signal_date']);days=pd.read_parquet(PRIVATE/'qfq_close.parquet').index
 rows=[];windows=[]
 for scope in ['primary','extended']:
  end=pd.Timestamp('2025-03-03') if scope=='primary' else days[-1]
  eligible=cal[cal.phase.isin([1,2])].copy();pos=days.get_indexer(eligible.signal_date)+21
  eligible=eligible[[i<len(days) and days[i]<=end for i in pos]]
  for model in MODELS:
   for phase in [1,2]:
    planned=eligible[eligible.phase==phase].signal_date
    for strategy in ['S1','S2']:
     v=f[(f.model==model)&f.strategy.isin(['S0',strategy])].pivot(index='signal_date',columns=['strategy','horizon'],values='mark').reindex(planned)
     own=v[strategy].reindex(columns=range(21));base=v['S0'].reindex(columns=range(21))
     common=own.notna().all(axis=1)&base.notna().all(axis=1)
     delta=(own-base).where(common,axis=0);delta.index=pd.DatetimeIndex(delta.index).to_period('M')
     for h in range(21):rows.append(dict(scope=scope,model=model,phase=phase,contrast=strategy+'-S0',horizon=h,**boot(delta[h])))
     # Start at initial capital, so 1-5 contains actual entry fee difference.
     for name,x in [('1-5',delta[5]),('6-10',delta[10]-delta[5]),('11-20',delta[20]-delta[10])]:windows.append(dict(scope=scope,model=model,phase=phase,contrast=strategy+'-S0',window=name,**boot(x)))
 pd.DataFrame(rows).to_csv(DEST/'event_curve.csv',index=False);pd.DataFrame(windows).to_csv(DEST/'marginal_windows.csv',index=False)


def account_stats():
 frames={};metas={}
 for rp in sorted((DEST/'accounts').glob('*.json')):
  r=json.loads(rp.read_text());path=rp.with_suffix('.csv');assert sha(path)==r['nav_sha256'];assert sha(r['orders_path'])==r['orders_sha256']
  frames[r['key']]=pd.read_csv(path,parse_dates=['date']).set_index('date');metas[r['key']]=r
 assert len(frames)==54
 global_end=min(f.index.max() for f in frames.values());primary_end=min(global_end,pd.Timestamp('2025-03-03'))
 results=[];pairs=[];monthly=[]
 for scope,end in [('primary_common',primary_end),('extended_common',global_end)]:
  for key,f in frames.items():
   r=metas[key];g=f.loc[:end];n=len(g);daily=g.daily_return;terminal=g.nav.iloc[-1]
   peak=np.maximum.accumulate(np.r_[1,g.nav.to_numpy()]);dd=np.min(np.r_[1,g.nav.to_numpy()]/peak-1)
   results.append(dict(scope=scope,model=r['model'],strategy=r['strategy'],frequency=r['frequency'],cost=r['cost'],start=g.index[0],end=g.index[-1],days=n,cagr=terminal**(252/n)-1,total_return=terminal-1,max_drawdown=dd,annual_oneway_turnover=.5*(g.buy.sum()+g.sell.sum())*252/n,annual_buy=g.buy.sum()*252/n,annual_sell=g.sell.sum()*252/n,mean_cash=g.cash_weight.mean(),mean_holdings=g.holdings.mean(),mean_unfilled_buy=g.unfilled_buy.mean(),blocked_before_planned_end=g.index[-1]<pd.Timestamp('2025-03-03'),native_end=f.index[-1]))
   m=(1+daily).groupby(daily.index.to_period('M')).prod()-1
   for period,value in m.items():monthly.append(dict(scope=scope,model=r['model'],strategy=r['strategy'],frequency=r['frequency'],cost=r['cost'],month=str(period),return_value=value))
  for model in MODELS:
   for freq in ['1w','2w','1m']:
    for cost in COSTS:
     base=frames[f'{model}_S0_{freq}_{cost}'].loc[:end]
     for strategy in ['S1','S2']:
      own=frames[f'{model}_{strategy}_{freq}_{cost}'].loc[:end]
      assert own.index.equals(base.index)
      active=own.daily_return-base.daily_return;relative=own.nav/base.nav
      # Trading-day blocks on ordered market calendar, no synthetic weekends.
      B=2000;L=65;n=len(active);rng=np.random.default_rng(20261117);idx=((rng.integers(0,n,(B,int(np.ceil(n/L))))[:,:,None]+np.arange(L))%n).reshape(B,-1)[:,:n]
      means=active.to_numpy()[idx].mean(axis=1)*252
      lo,hi=np.quantile(means,[.025,.975]) if n>=130 else (np.nan,np.nan)
      curve=np.r_[1,relative.to_numpy()]
      pairs.append(dict(scope=scope,model=model,frequency=freq,cost=cost,contrast=strategy+'-S0',end=end,days=n,cagr_difference=own.nav.iloc[-1]**(252/n)-base.nav.iloc[-1]**(252/n),relative_cagr=relative.iloc[-1]**(252/n)-1,annual_mean_active=active.mean()*252,ci_low=lo,ci_high=hi,tracking_error=active.std(ddof=1)*np.sqrt(252),relative_max_drawdown=np.min(curve/np.maximum.accumulate(curve)-1)))
 pd.DataFrame(results).to_csv(DEST/'account_metrics.csv',index=False);pd.DataFrame(pairs).to_csv(DEST/'account_contrasts.csv',index=False);pd.DataFrame(monthly).to_csv(DEST/'account_monthly.csv',index=False)
 save_json(DEST/'account_endpoints.json',dict(global_common_end=str(global_end),primary_common_end=str(primary_end),planned_primary_end='2025-03-03',failures=[dict(key=k,failures=r['failures']) for k,r in metas.items() if r['failures']]))


def account_exposures():
 scores=pd.read_parquet(LOCAL/'scores.parquet');lookup={k:g for k,g in scores.groupby(['model','signal_date'])};rows=[]
 for model in MODELS:
  for freq in ['1w','2w','1m']:
   orders={}
   for strategy in ['S0','S1','S2']:
    orders[strategy]=pd.read_parquet(LOCAL/'accounts'/f'{model}_{strategy}_{freq}_main.parquet')
   dates=set.intersection(*[set(f.signal_date) for f in orders.values()])
   for date in sorted(dates):
    if (model,date) not in lookup:continue
    g=lookup[(model,date)];z,ind,_=matrix(g);weights={};unknown={};cash={}
    for strategy,f in orders.items():
     v=f[f.signal_date==date].set_index('instrument');weights[strategy]=v.actual_weight.reindex(g.instrument).fillna(0).to_numpy()
     unknown[strategy]=float(v.loc[~v.index.isin(g.instrument),'actual_weight'].sum());cash[strategy]=float(v.cash_weight.iloc[0])
    for strategy in ['S1','S2']:
     d=weights[strategy]-weights['S0'];num=float(np.max(np.abs(z.T@d)));igap=float(np.max(np.abs(ind.T@d)))
     rows.append(dict(model=model,frequency=freq,signal_date=date,contrast=strategy+'-S0',numeric_gap=num,industry_gap=igap,cash_gap=cash[strategy]-cash['S0'],unmapped_weight=unknown[strategy]+unknown['S0'],within_bounds=num<=.25+1e-7 and igap<=.02+1e-7 and unknown[strategy]+unknown['S0']<1e-8))
 pd.DataFrame(rows).to_csv(DEST/'account_exposures.csv',index=False)


def stability():
 scores=pd.read_parquet(LOCAL/'scores.parquet');targets=pd.read_parquet(LOCAL/'targets.parquet');rows=[]
 for model in MODELS:
  dates=sorted(scores.loc[scores.model==model,'signal_date'].unique())
  for left,right in zip(dates[:-1],dates[1:]):
   a=scores[(scores.model==model)&(scores.signal_date==left)].set_index('instrument');b=scores[(scores.model==model)&(scores.signal_date==right)].set_index('instrument');common=a.index.intersection(b.index)
   for strategy in ['S0','S1','S2']:
    h=targets[(targets.model==model)&(targets.strategy==strategy)]
    u=set(h.loc[h.signal_date==left,'instrument']);v=set(h.loc[h.signal_date==right,'instrument'])
    rows.append(dict(model=model,strategy=strategy,previous=left,signal_date=right,rank_stability=rankcorr(a.loc[common,strategy],b.loc[common,strategy]),retained_fraction=len(u&v)/len(u) if u else np.nan))
 pd.DataFrame(rows).to_csv(DEST/'stability.csv',index=False)


def breakeven():
 inp,targets,schedule=selected_inputs();ends=json.loads((DEST/'account_endpoints.json').read_text());end=pd.Timestamp(ends['primary_common_end']);rows=[];result=[]
 for model in MODELS:
  g=targets[(targets.model==model)&(targets.strategy=='S1')];mapping={d:target_vector(inp,x) for d,x in g.groupby('signal_date')}
  cache={}
  def gap(bps):
   if bps in cache:return cache[bps]
   navs=[]
   for freq in ['2w','1m']:
    f,_,fail=run_account(inp,mapping,date_schedule(schedule.signal_date,freq),(bps/10000,2*bps/10000),end=end,keep_orders=False)
    value=float(f.nav.iloc[-1]) if len(f) and f.date.iloc[-1]==end else np.nan
    navs.append(value);rows.append(dict(model=model,frequency=freq,buy_bps=bps,sell_bps=2*bps,end=end,terminal_nav=value,failures=json.dumps(fail,default=str)))
   cache[bps]=navs[0]-navs[1];return cache[bps]
  grid=np.arange(0,101,10);values=[gap(float(x)) for x in grid];roots=[]
  for i in range(len(grid)-1):
   if not np.isfinite(values[i:i+2]).all():continue
   if values[i]==0:roots.append(float(grid[i]));continue
   if values[i]*values[i+1]>=0:continue
   lo=float(grid[i]);hi=float(grid[i+1]);left=values[i]
   for _ in range(12):
    mid=(lo+hi)/2;value=gap(mid)
    if not np.isfinite(value):break
    if left*value<=0:hi=mid
    else:lo=mid;left=value
   roots.append((lo+hi)/2)
  result.append(dict(model=model,end=str(end),buy_bps_roots=roots,sell_bps_roots=[2*x for x in roots],zero_cost_terminal_gap=values[0],at100bps_terminal_gap=values[-1],status='BRACKETED_CROSSING' if roots else 'NO_SIGN_CHANGING_GRID_BRACKET_0_TO_100_BUY_BPS',note='Finite grid can miss tangencies/multiple crossings inside one cell; not a global no-root proof'))
 pd.DataFrame(rows).to_csv(DEST/'breakeven_replays.csv',index=False);save_json(DEST/'breakeven.json',result)


if __name__=='__main__':
 import sys
 functions={'a1':a1_caps,'exposures':event_exposures,'events':event_stats,'paths':paths,'accounts':account_stats,'account_exposures':account_exposures,'stability':stability,'breakeven':breakeven}
 if sys.argv[1]=='all':
  for name,fn in functions.items():print('analyze',name,flush=True);fn()
 else:functions[sys.argv[1]]()
