"""Frozen EP36 mechanism experiment. prepare has no labels or outcome computations."""
import sys,json,pickle,__main__,math
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.optimize import milp,Bounds,LinearConstraint
from scipy.stats import rankdata,norm
from common import EP,OUT,PRIVATE,sha,save_json
from evaluate_ranking import predictions
from alpha_economics import STYLES,COSTS,event_path,target_vector,run_account
from alpha_falsification import project,rankcorr,corr,holm
RUN='e1_alpha_mechanism_20261117';D=OUT/'diagnostics'/RUN;L=PRIVATE/RUN;R=EP/'reports'/RUN
END=pd.Timestamp('2025-03-03');START=pd.Timestamp('2021-01-08')

def write(df,name,private=False):
 p=(L if private else D)/name;p.parent.mkdir(parents=True,exist_ok=True)
 if name.endswith('.parquet'):df.to_parquet(p,index=False)
 else:df.to_csv(p,index=False)

def records(paths):return [dict(path=str(p),sha256=sha(p)) for p in paths]
def verify(which='freeze'):
 f=json.loads((D/(which+'.json')).read_text())
 for r in f['files']:assert sha(r['path'])==r['sha256'],r['path']
 return f

def groupname(f):
 if f.startswith('market_'):return 'market_common'
 if f.startswith(('vol','amp','dd')) and not f.startswith('volume'):return 'volatility_drawdown'
 if f.startswith('pos'):return 'range_position'
 if f.startswith(('volume','money','turnover')):return 'volume_liquidity'
 return 'returns_trend'

def freeze():
 D.mkdir(parents=True,exist_ok=True);L.mkdir(parents=True,exist_ok=True)
 assert not (D/'freeze.json').exists()
 dd=pd.read_csv(EP/'configs/feature_dictionary.csv');dd=dd[dd.group=='core'].copy();dd['mechanism_group']=dd.feature.map(groupname);write(dd,'feature_groups.csv')
 _,consumed=predictions('expanding')
 files=[EP/'configs'/f'{RUN}.json',R/'PROTOCOL.md',D/'feature_groups.csv']
 files+=list((EP/'src').glob('*.py'))
 files+=[PRIVATE/(n+'.parquet') for n in ['features','labels','qfq_close','qfq_open','open','close','daily_members','industry','opening_trade_status_v2','market']]
 files += [PRIVATE/'alpha_falsification_20261117/styles.parquet',PRIVATE/'alpha_economics_20261117/cap_audit_rows.parquet',PRIVATE/'limits/daily.parquet',PRIVATE/'suspensions/daily.parquet',PRIVATE/'weights/snapshots.parquet',PRIVATE/'net_excess_20261116/H00300.CSI.json',PRIVATE/'e1_return_attribution_20261117/daily_active_stock_industry.parquet']
 receipts=json.loads((OUT/'manifests/expanding_predictions.json').read_text())
 files += [Path(m['path']) for r in receipts for m in r['models'] if m['model']=='E1']
 files += [OUT/'manifests/expanding_predictions.json']
 save_json(D/'freeze.json',dict(files=records(files)+consumed,at=datetime.now(timezone.utc).isoformat(),prior_outcomes_seen=True,new_outcomes_computed=False,implementation_clarifications={'regression':'standardize J and S on full signal sample before label join; styles standardized same full sample; missing labels do not define ranks','ties':'B ascending instrument among descending score; solver ties deterministic fixed input order, actual selections sealed','placebo':'independent SeedSequence [20261117, date YYYYMMDD, replicate]','matching':'raw original weekly Q5, not constrained sample Q5','evaluation':'gross open-open labels require finite endpoint prices; execution event labels separately gate entry and exit; dates must mature within scope','bootstrap':'circular blocks including calendar gaps','actual_risk':'daily frozen-signal exposures, disclose unknown legacy weights','statistical_rank':'require n-rank>=50 after label missingness','case_events':'stock and latest known weekly signal; contributions from original ledger'}))
 print('FROZEN',flush=True)

def standard(a):
 a=np.asarray(a,float);sd=a.std(axis=0);return (a-a.mean(axis=0))/np.where(sd<1e-12,1,sd)

def state_scores(g):
 g=g.copy()
 for col,out in [('T','u'),('P','v')]:
  rel=g[col]-g.groupby('industry')[col].transform(lambda s:(s.sum()-s)/(len(s)-1))
  g[out]=rel.groupby(g.industry).transform(lambda s:(s.rank(method='average')-.5)/len(s))
 g['B']=(g.u+g.v)/2;g['J']=np.minimum(g.u,g.v)
 g['state']=np.select([(g.u>.5)&(g.v>.5),(g.u>.5)&(g.v<=.5),(g.u<=.5)&(g.v>.5)],['strong_pullback','strong_no_pullback','weak_pullback'],default='weak_no_pullback')
 return g

def base_mask(g):
 n=len(g);k=int(np.ceil(n/5));counts=g.industry.value_counts().sort_index();q=counts*k/n;slots=np.floor(q).astype(int)
 order=sorted(counts.index,key=lambda a:(-(q[a]-slots[a]),a))
 for a in order[:k-int(slots.sum())]:slots[a]+=1
 base=np.zeros(n)
 for a,c in slots.items():
  ids=np.flatnonzero(g.industry.to_numpy()==a);order=np.lexsort((g.instrument.to_numpy()[ids],-g.B.to_numpy()[ids]));base[ids[order[:c]]]=1
 return base,k

def solve(g,base,k,score):
 z=standard(g[STYLES]);ind=pd.get_dummies(g.industry).to_numpy(float);a=np.column_stack([z,ind]).T/k
 tol=np.r_[np.full(len(STYLES),.25),np.zeros(ind.shape[1])];center=a@base
 res=milp(-rankdata(g[score])/len(g),integrality=np.ones(len(g)),bounds=Bounds(0,1),constraints=LinearConstraint(a,center-tol,center+tol),options={'time_limit':2,'mip_rel_gap':.01})
 info=dict(status=int(res.status),gap=getattr(res,'mip_gap',None),bound=getattr(res,'mip_dual_bound',None),accepted=False)
 if res.x is None:return None,info
 mask=(res.x>.5).astype(float);delta=a@(mask-base)
 good=mask.sum()==k and np.all(np.abs(delta)<=tol+1e-7)
 info.update(accepted=bool(good),numeric_gap=float(np.max(abs(delta[:13]))),industry_gap=float(np.max(abs(delta[13:]))))
 return (mask if good else None),info

def prepare():
 verify();assert not (D/'selection_complete.json').exists()
 p,_=predictions('expanding');p=p[(p.model_id=='E1')&(p.seed_or_ensemble=='fixed')&p.score.notna()].copy()
 p=p.rename(columns={'score':'E1'});p=p[['signal_date','instrument','E1']].sort_values(['signal_date','instrument'])
 p['raw_q5']=False
 for date,g in p.groupby('signal_date'):
  ids=g.sort_values(['E1','instrument']).index;n=len(g);p.loc[ids[np.floor(5*np.arange(n)/n)==4],'raw_q5']=True
 dates=pd.DatetimeIndex(sorted(p.signal_date.unique()));schedule=pd.DataFrame({'signal_date':dates});schedule['phase']=schedule.groupby(schedule.signal_date.dt.to_period('M')).cumcount()+1;write(schedule,'schedule.csv')
 close=pd.read_parquet(PRIVATE/'qfq_close.parquet');styles=pd.read_parquet(PRIVATE/'alpha_falsification_20261117/styles.parquet');caps=pd.read_parquet(PRIVATE/'alpha_economics_20261117/cap_audit_rows.parquet')
 g=p.merge(styles,on=['signal_date','instrument'],validate='one_to_one').merge(caps[['signal_date','instrument','source_date','log_total_mv','log_circ_mv']],on=['signal_date','instrument'],how='left',validate='one_to_one')
 ii=close.index.get_indexer(g.signal_date);jj=close.columns.get_indexer(g.instrument);arr=close.to_numpy();assert (ii>=60).all() and (jj>=0).all()
 g['T']=np.log(arr[ii-5,jj]/arr[ii-60,jj]);g['P']=-np.log(arr[ii,jj]/arr[ii-5,jj])
 complete=np.isfinite(g[STYLES+['T','P','E1']]).all(axis=1)&g.industry.ne('UNKNOWN');g['eligible']=False;g['reason']='MISSING_STYLE_PRICE_OR_INDUSTRY'
 count=g.loc[complete].groupby(['signal_date','industry']).instrument.transform('size');valid=g.loc[complete].index[count>=10];g.loc[valid,'eligible']=True;g.loc[valid,'reason']='OK';g.loc[g.index[complete].difference(valid),'reason']='INDUSTRY_LT10'
 common=g[g.eligible].copy();common=state_scores(common.groupby('signal_date',group_keys=False).apply(lambda a:a)) if False else pd.concat([state_scores(a) for _,a in common.groupby('signal_date')])
 for col in ['J','E1']:
  common['std_'+col]=common.groupby('signal_date')[col].transform(lambda s:standard(rankdata(s) if col=='E1' else s))
 zparts=[]
 for date,a in common.groupby('signal_date'):
  a=a.copy();z=standard(a[STYLES]);
  for j,col in enumerate(STYLES):a['z_'+col]=z[:,j]
  zparts.append(a)
 common=pd.concat(zparts)
 write(g,'universe_audit.parquet',True);write(common,'scores.parquet',True)
 coverage=g.groupby('signal_date').agg(original=('instrument','size'),original_q5=('raw_q5','sum'),common=('eligible','sum'))
 coverage['q5_covered']=g[g.eligible].groupby('signal_date').raw_q5.sum();coverage['q5_budget_coverage']=coverage.q5_covered/coverage.original_q5;write(coverage.reset_index(),'coverage.csv')
 # E0 exact original transform and coefficient decomposition, before labels.
 from train import TrainTransform
 __main__.TrainTransform=TrainTransform
 f=pd.read_parquet(PRIVATE/'features.parquet');dd=pd.read_csv(D/'feature_groups.csv');cols=dd.feature.tolist();groups=dd.mechanism_group.unique();replays=[];coef=[];contributions=[]
 receipts=json.loads((OUT/'manifests/expanding_predictions.json').read_text())
 for rec in receipts:
  m=next(m for m in rec['models'] if m['model']=='E1');assert sha(m['path'])==m['sha256'];transform,model=pickle.loads(Path(m['path']).read_bytes())
  a=f[(f.signal_date.dt.to_period('Q').astype(str)==rec['fold'])&f.score_eligible].copy();x=transform.transform(a[cols]);values=x*model.coef_;pred=values.sum(axis=1)+model.intercept_
  keys=a[['signal_date','instrument']];old=keys.merge(p,on=['signal_date','instrument'],validate='one_to_one');err=float(np.max(abs(old.E1.to_numpy()-pred)));assert err<1e-10
  replays.append(dict(fold=rec['fold'],rows=len(a),max_error=err))
  for j,col in enumerate(cols):coef.append(dict(fold=rec['fold'],feature=col,group=dd.mechanism_group.iloc[j],coefficient=model.coef_[j],train_mean=transform.mean[j],train_sd=transform.sd[j]))
  out=old.copy();out['intercept']=float(model.intercept_)
  for gr in groups:out[gr]=values[:,dd.mechanism_group.eq(gr)].sum(axis=1)
  contributions.append(out)
 write(pd.DataFrame(replays),'model_replay.csv');write(pd.DataFrame(coef),'coefficients.csv');contrib=pd.concat(contributions);write(contrib,'score_contributions.parquet',True)
 write(contrib.groupby(['signal_date','raw_q5'])[list(groups)].mean().reset_index(),'score_group_means.csv');write(contrib[list(groups)].corr().reset_index(),'score_group_correlations.csv')
 # Fixed target and placebo construction. No prices after signal accessed here.
 targets=[];solvers=[];placebos=[];matches=[]
 phases=schedule.set_index('signal_date').phase.to_dict()
 for num,(date,a) in enumerate(common.groupby('signal_date')):
  a=a.sort_values('instrument').reset_index(drop=True)
  if len(a)<100:solvers.append(dict(signal_date=date,strategy='ALL',accepted=False,reason='N_LT100'));continue
  base,k=base_mask(a);masks={'B':base}
  for strategy in ['J','E1']:
   mask,info=solve(a,base,k,strategy);solvers.append(dict(signal_date=date,strategy=strategy,n=len(a),k=k,**info))
   if mask is not None:masks[strategy]=mask
  z=standard(a[STYLES]);inds=a.industry.to_numpy();codes=a.instrument.to_numpy()
  for strategy,mask in masks.items():
   for j in np.flatnonzero(mask):targets.append(dict(signal_date=date,strategy=strategy,instrument=codes[j],weight=1/k))
  for j in np.flatnonzero(a.raw_q5.to_numpy()):
   candidates=np.flatnonzero((inds==inds[j])&~a.raw_q5.to_numpy());delta=z[candidates]-z[j];ok=np.max(abs(delta),axis=1)<=.5;cs=candidates[ok]
   selected=None;distance=np.nan
   if len(cs):dist=np.sum((z[cs]-z[j])**2,axis=1);selected=cs[np.lexsort((codes[cs],dist))[0]];distance=float(np.sum((z[selected]-z[j])**2))
   matches.append(dict(signal_date=date,instrument=codes[j],control=codes[selected] if selected is not None else None,distance=distance,matched=selected is not None))
  if phases[date] in [1,2]:
   cells=[(np.flatnonzero(inds==ind),int(base[inds==ind].sum())) for ind in sorted(set(inds))]
   for rep in range(100):
    rng=np.random.default_rng(np.random.SeedSequence([20261117,int(date.strftime('%Y%m%d')),rep]));pick=None
    for attempt in range(100):
     candidate=np.zeros(len(a))
     for ids,c in cells:
      if c:candidate[rng.choice(ids,c,replace=False)]=1
     gap=np.max(abs(z.T@(candidate-base)/k))
     if gap<=.25+1e-7:pick=candidate;break
    placebos.append(dict(signal_date=date,replicate=rep,accepted=pick is not None,attempts=attempt+1,gap=float(gap)))
    if pick is not None:
     for j in np.flatnonzero(pick):targets.append(dict(signal_date=date,strategy=f'P{rep:03}',instrument=codes[j],weight=1/k))
  if num%20==0:print('prepare',num,len(dates),date.date(),flush=True)
 write(pd.DataFrame(targets),'targets.parquet',True);write(pd.DataFrame(solvers),'solver.csv');write(pd.DataFrame(placebos),'placebo_coverage.csv');write(pd.DataFrame(matches),'matched_pairs.csv')
 verify();save_json(D/'selection_complete.json',dict(at=datetime.now(timezone.utc).isoformat(),files=records(list(L.glob('*.parquet'))+list(D.glob('*.csv'))),labels_read=False,new_outcomes_computed=False))
 print('SELECTION SEALED',flush=True)

def bootstrap(series,freq,Lblock,B=5000):
 s=series.copy();s.index=pd.DatetimeIndex(s.index).to_period(freq);assert not s.index.duplicated().any()
 grid=pd.period_range(s.index.min(),s.index.max(),freq=freq);a=s.reindex(grid).to_numpy(float);n=len(a);known=np.isfinite(a).sum();mean=float(np.nanmean(a)) if known else np.nan
 result=dict(n=int(known),periods=n,mean=mean,ci_low=np.nan,ci_high=np.nan,p=np.nan,bootstrap_failed=0)
 if known<2*Lblock:return result
 rng=np.random.default_rng(20261117);starts=rng.integers(0,n,(B,math.ceil(n/Lblock)));idx=((starts[:,:,None]+np.arange(Lblock))%n).reshape(B,-1)[:,:n]
 sums=np.nansum(a[idx],axis=1);counts=np.isfinite(a[idx]).sum(axis=1);means=np.divide(sums,counts,out=np.full(B,np.nan),where=counts>0);valid=means[np.isfinite(means)]
 result.update(ci_low=float(np.quantile(valid,.025)),ci_high=float(np.quantile(valid,.975)),p=float((1+np.sum(abs(valid-mean)>=abs(mean)))/(1+len(valid))),bootstrap_failed=int(B-len(valid)),bootstrap_sd=float(np.std(valid,ddof=1)))
 return result

def controls(a):
 z=a[['z_'+s for s in STYLES]].to_numpy();ind=pd.get_dummies(a.industry,drop_first=True).to_numpy(float);parts=[np.ones((len(a),1)),z,ind]
 for name in ['u','v']:
  v=a[name].to_numpy();parts.append(np.column_stack([v]+[np.maximum(v-k,0) for k in [.25,.5,.75]]))
 return np.column_stack(parts)

def conditional(a):
 x=controls(a);y=a.y.to_numpy();j=a.std_J.to_numpy();s=a.std_E1.to_numpy();rows={}
 for name,target,xx in [('P1',j,x),('P3',s,np.column_stack([x,j]))]:
  _,tr,_,r=project(xx,target);_,yr,_,_=project(xx,y);df=len(a)-r-1;variance=float(np.var(tr));ok=len(a)>=100 and df>=50 and variance>=1e-12
  _,rr,_,_=project(xx,rankdata(target));_,ry,_,_=project(xx,rankdata(y))
  rows[name]=dict(value=float(tr@yr/(tr@tr)) if ok else np.nan,n=len(a),rank=r,df=df,residual_variance=variance,reason='OK' if ok else 'N_DF_OR_IDENTIFICATION',partial_rank_ic=corr(rr,ry) if ok else np.nan)
 return rows

def evaluate():
 verify();verify('selection_complete');assert not (D/'evaluation_complete.json').exists()
 from backtest import Inputs
 from suspension_sensitivity import marks
 inp=Inputs();rawopen=inp.o.copy();marks(inp,0.)
 scores=pd.read_parquet(L/'scores.parquet');targets=pd.read_parquet(L/'targets.parquet');schedule=pd.read_csv(D/'schedule.csv',parse_dates=['signal_date']);phase=schedule.set_index('signal_date').phase.to_dict()
 # Raw endpoint labels, not executable events and not filled suspension marks.
 ii=inp.days.get_indexer(scores.signal_date);jj=inp.symbols.get_indexer(scores.instrument);labelrows=[];reg=[];ics=[]
 for h in [5,10,20]:
  entry=ii+1;exit=entry+h;valid=exit<len(inp.days);y=np.full(len(scores),np.nan);y[valid]=rawopen[exit[valid],jj[valid]]/rawopen[entry[valid],jj[valid]]-1;y[~np.isfinite(y)]=np.nan
  scores['h'+str(h)]=y;scores['exit'+str(h)]=[inp.days[e] if e<len(inp.days) else pd.NaT for e in exit]
  for date,a in scores.groupby('signal_date'):
   known=a[np.isfinite(a['h'+str(h)])].copy();known['y']=known['h'+str(h)]
   if len(known)>=3:
    vals=conditional(known)
    for name,v in vals.items():reg.append(dict(signal_date=date,horizon=h,test=name,exit_date=a['exit'+str(h)].iloc[0],label_coverage=len(known)/len(a),**v))
    for s in ['u','v','B','J','E1']:ics.append(dict(signal_date=date,horizon=h,score=s,ic=rankcorr(known[s],known.y),n=len(known),exit_date=a['exit'+str(h)].iloc[0]))
 write(scores,'labeled_events.parquet',True);write(pd.DataFrame(reg),'conditional.csv');write(pd.DataFrame(ics),'rank_ic.csv')
 print('conditional complete',flush=True)
 # Event engine; accelerated input context cached by original engine.
 events=[];paths=[];delays=[]
 for num,((date,strategy),a) in enumerate(targets.groupby(['signal_date','strategy'])):
  if phase[date] not in [1,2]:continue
  si=inp.days.get_loc(date);v=target_vector(inp,a);costs=['main'] if strategy.startswith('P') else COSTS.keys()
  for cost in costs:
   ev,pa=event_path(inp,si,v,*COSTS[cost]);key=dict(signal_date=date,phase=phase[date],strategy=strategy,cost=cost)
   events.extend(key|r for r in ev)
   if cost=='main' and not strategy.startswith('P'):paths.extend(key|r for r in pa)
  if phase[date]==1 and not strategy.startswith('P'):
   later=schedule[(schedule.signal_date.dt.to_period('M')==date.to_period('M'))&(schedule.phase==2)]
   if len(later):
    delay=later.signal_date.iloc[0];ev,_=event_path(inp,inp.days.get_loc(delay),v,*COSTS['main']);delays.extend(dict(signal_date=date,execution_signal=delay,strategy=strategy,**r) for r in ev)
  if num%1000==0:print('events',num,flush=True)
 write(pd.DataFrame(events),'events.csv');write(pd.DataFrame(paths),'paths.csv');write(pd.DataFrame(delays),'delayed_events.csv')
 # Continuous accounts, exact original monthly calendar including NO_TARGET dates.
 dates=pd.DatetimeIndex(schedule.loc[schedule.phase==1,'signal_date']);receipts=[]
 for strategy in ['B','J','E1']:
  t=targets[targets.strategy==strategy];mapping={d:target_vector(inp,a) for d,a in t.groupby('signal_date')}
  for cost,fees in COSTS.items():
   daily,orders,fail=run_account(inp,mapping,dates,fees);key=f'{strategy}_{cost}';write(daily,'accounts/'+key+'.csv');write(orders,'orders/'+key+'.parquet',True);receipts.append(dict(strategy=strategy,cost=cost,failures=fail,days=len(daily),end=str(daily.date.max())))
   print('account',key,len(daily),flush=True)
 save_json(D/'accounts.json',receipts)
 verify();verify('selection_complete');save_json(D/'evaluation_complete.json',dict(at=datetime.now(timezone.utc).isoformat(),files=records([L/'labeled_events.parquet']+list(D.glob('*.csv'))+list((D/'accounts').glob('*.csv'))+list((L/'orders').glob('*.parquet')))))
 print('EVALUATION SEALED',flush=True)

if __name__=='__main__':globals()[sys.argv[1]]()
