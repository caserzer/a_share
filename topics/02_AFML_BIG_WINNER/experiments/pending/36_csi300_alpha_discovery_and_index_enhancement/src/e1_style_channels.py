"""Fixed group-ablation and style-reconstruction diagnostics, no parameter search."""
import sys,json,math
from pathlib import Path
from datetime import datetime,timezone
import numpy as np,pandas as pd
from scipy.optimize import milp,Bounds,LinearConstraint
from scipy.stats import rankdata
from common import EP,OUT,PRIVATE,sha,save_json
from alpha_economics import STYLES,target_vector,run_account,event_path
from e1_mechanism import standard
from alpha_falsification import project,rankcorr
from e1_advantage_bridge import quotas
from e1_return_attribution import absolute_components,daily_returns,paired_ci
from backtest import Inputs
from suspension_sensitivity import marks
RUN='e1_style_channels_20261117';D=OUT/'diagnostics'/RUN;L=PRIVATE/RUN;R=EP/'reports'/RUN;OLD='e1_alpha_mechanism_20261117';BR='e1_advantage_bridge_20261117';END=pd.Timestamp('2025-03-03')
GROUPS={'price':['mom1','mom5','mom20','mom60'],'risk':['vol20','vol60','beta60','idio60'],'liquidity':['log_money20','turnover20','log_amihud20'],'size':['log_total_mv','log_circ_mv']}

def write(df,name,private=False):
 p=(L if private else D)/name;p.parent.mkdir(parents=True,exist_ok=True)
 if name.endswith('.parquet'):df.to_parquet(p,index=False)
 else:df.to_csv(p,index=False)
def record(paths):return [dict(path=str(p),sha256=sha(p)) for p in paths]
def verify(name='freeze'):
 r=json.loads((D/(name+'.json')).read_text())
 for p in r['files']:assert sha(p['path'])==p['sha256'],p['path']
 return r

def fixed_pick(g,k,score):
 mask=np.zeros(len(g));slots=quotas(g,k)
 for ind,n in slots.items():
  ids=np.flatnonzero(g.industry.to_numpy()==ind);order=np.lexsort((g.instrument.to_numpy()[ids],-np.asarray(score)[ids]));mask[ids[order[:n]]]=1
 return mask

def solve(g,k,base,styles):
 z=standard(g[STYLES]);idx=[STYLES.index(s) for s in styles];ind=pd.get_dummies(g.industry).to_numpy(float);a=np.column_stack([z[:,idx],ind]).T/k;tol=np.r_[np.full(len(idx),.25),np.zeros(ind.shape[1])];target=a@base
 r=milp(-rankdata(g.E1)/len(g),integrality=np.ones(len(g)),bounds=Bounds(0,1),constraints=LinearConstraint(a,target-tol,target+tol),options={'time_limit':2,'mip_rel_gap':.01})
 mask=None if r.x is None else (r.x>.5).astype(float);ok=mask is not None and mask.sum()==k and np.all(abs(a@mask-target)<=tol+1e-7)
 info=dict(status=int(r.status),gap=getattr(r,'mip_gap',None),accepted=bool(ok))
 return (mask if ok else None),info

def freeze():
 D.mkdir(parents=True,exist_ok=True);L.mkdir(parents=True,exist_ok=True);R.mkdir(parents=True,exist_ok=True);assert not (D/'freeze.json').exists()
 cfg=dict(run=RUN,at=datetime.now(timezone.utc).isoformat(),prior_results_seen=True,new_results_seen=False,scope='2021-01-08 through 2025-03-03; original 50 monthly signals',groups=GROUPS,ablation='each group alone versus I, each group removed versus F; no best subset selection; interactions not additive',bounds='same B reference, .25 SD, exact old industry slots, 2sec MILP gap .01; failure retained no relaxed bounds',baselines={'REV':'negative average cross-sectional rank(mom1),rank(mom5)','MOM':'average rank(mom20),rank(mom60)','MIX':'equal weight REV+MOM; no learned weights','COPY':'same-date OLS E1 score on all13 styles and industry; teacher-dependent, not independent deployable baseline'},baseline_selection='same C universe,k,industry slots; top baseline score; no further numerical style bounds',main_cost=[.001,.002],zero_cost='all accounts auxiliary to distinguish turnover from gross opportunity, not tuning',statistics='paired daily65-trading-day circular blocks2000seed20261117, descriptive CI only; fixed H10 event differences auxiliary; no confirmatory claims',clock='features at each original signal, monthly signal exposure attribution; no future labels in selection',forbidden=['new return-model training','threshold search','selecting a winning ablation as alpha','style-copy claimed independent model'])
 cp=EP/'configs'/(RUN+'.json');assert not cp.exists();save_json(cp,cfg)
 files=[cp,Path(__file__),PRIVATE/OLD/'scores.parquet',PRIVATE/OLD/'targets.parquet',PRIVATE/BR/'targets.parquet']
 files += [EP/'src'/s for s in ['alpha_economics.py','e1_mechanism.py','e1_advantage_bridge.py','e1_return_attribution.py','alpha_falsification.py','portfolio.py','backtest.py','suspension_sensitivity.py','common.py']]
 files += [PRIVATE/(s+'.parquet') for s in ['qfq_close','qfq_open','open','opening_trade_status_v2','daily_members','industry']]+[PRIVATE/'limits/daily.parquet',PRIVATE/'suspensions/daily.parquet',PRIVATE/'weights/snapshots.parquet']
 files += [OUT/'diagnostics'/BR/'accounts'/f'{s}.csv' for s in ['I','F']]
 save_json(D/'freeze.json',dict(files=record(files),outcomes_read=False));print('FROZEN',flush=True)

def prepare():
 verify();assert not (D/'selection_complete.json').exists();scores=pd.read_parquet(PRIVATE/OLD/'scores.parquet');old=pd.read_parquet(PRIVATE/OLD/'targets.parquet');bridge=pd.read_parquet(PRIVATE/BR/'targets.parquet');dates=sorted(bridge.signal_date.unique());rows=[];solver=[];exposures=[];changed=[];reconstruction=[];allscore=[]
 for date in dates:
  g=scores[scores.signal_date==date].sort_values('instrument').reset_index(drop=True);k=int(np.ceil(len(g)/5));base=g.instrument.isin(old[(old.signal_date==date)&(old.strategy=='B')].instrument).to_numpy(float);masks={'B':base}
  for st in ['I','F']:masks[st]=g.instrument.isin(bridge[(bridge.signal_date==date)&(bridge.strategy==st)].instrument).to_numpy(float)
  for group,cols in GROUPS.items():
   for mode in ['only','without']:
    active=cols if mode=='only' else [c for c in STYLES if c not in cols];st=mode+'_'+group;mask,info=solve(g,k,base,active);solver.append(dict(signal_date=date,strategy=st,active='|'.join(active),**info))
    if mask is not None:masks[st]=mask
  rank=lambda c:rankdata(g[c])/len(g)
  sc={'REV':-(rank('mom1')+rank('mom5'))/2,'MOM':(rank('mom20')+rank('mom60'))/2};sc['MIX']=(sc['REV']+sc['MOM'])/2
  z=standard(g[STYLES]);x=np.column_stack([np.ones(len(g)),z,pd.get_dummies(g.industry,drop_first=True).to_numpy(float)]);f,res,q,r=project(x,g.E1.to_numpy());sc['COPY']=f;lev=np.sum(q*q,axis=1);tss=np.sum((g.E1-g.E1.mean())**2);loo=res/(1-lev)
  reconstruction.append(dict(signal_date=date,n=len(g),rank=r,r2=1-res@res/tss,loo_Q2=1-loo@loo/tss,rankcorr=rankcorr(f,g.E1)))
  for st,values in sc.items():masks[st]=fixed_pick(g,k,values)
  a=g[['signal_date','instrument','industry','E1']+STYLES].copy()
  for st,values in sc.items():a[st]=values
  allscore.append(a)
  for st,mask in masks.items():
   assert mask.sum()==k
   for j in np.flatnonzero(mask):rows.append(dict(signal_date=date,strategy=st,instrument=g.instrument.iloc[j],weight=1/k))
   delta=z.T@(mask-base)/k
   for j,c in enumerate(STYLES):exposures.append(dict(signal_date=date,strategy=st,style=c,exposure=float(z[:,j]@mask/k),B_exposure=float(z[:,j]@base/k),difference=float(delta[j]),outside_bound=bool(abs(delta[j])>.25+1e-7),near_bound=bool(abs(abs(delta[j])-.25)<=.01)))
   if st=='B':continue
   for j in np.flatnonzero(mask!=masks['I']):changed.append(dict(signal_date=date,strategy=st,instrument=g.instrument.iloc[j],industry=g.industry.iloc[j],direction='ADDED' if mask[j] else 'REMOVED',E1_score=float(g.E1.iloc[j]),**{c:float(z[j,h]) for h,c in enumerate(STYLES)}))
 write(pd.DataFrame(rows),'targets.parquet',True);write(pd.concat(allscore),'scores.parquet',True);write(pd.DataFrame(solver),'solver.csv');write(pd.DataFrame(exposures),'target_exposures.csv');write(pd.DataFrame(changed),'replacement_stocks.csv');write(pd.DataFrame(reconstruction),'score_reconstruction.csv')
 save_json(D/'selection_complete.json',dict(files=record(list(D.glob('*.csv'))+list(L.glob('*.parquet'))),future_labels_read=False));print('SEALED',len(rows),flush=True)

def run():
 verify();verify('selection_complete');assert not (D/'accounts_complete.json').exists();inp=Inputs();marks(inp,0.);t=pd.read_parquet(L/'targets.parquet');dates=sorted(t.signal_date.unique());events=[];receipts=[]
 for st,g in t.groupby('strategy'):
  maps={d:target_vector(inp,a) for d,a in g.groupby('signal_date')}
  for cost,fees in [('main',(.001,.002)),('zero',(0.,0.))]:
   a,o,fail=run_account(inp,maps,dates,fees,end=END);key=st+'__'+cost;write(a,'accounts/'+key+'.csv');write(o,'orders/'+key+'.parquet',True);receipts.append(dict(strategy=st,cost=cost,failures=fail,days=len(a),end=str(a.date.max())))
  for d in dates:
   if d not in maps:events.append(dict(signal_date=d,strategy=st,horizon=10,net_return=np.nan,reason='NO_TARGET'));continue
   ev,_=event_path(inp,inp.days.get_loc(d),maps[d],.001,.002);events.extend(dict(signal_date=d,strategy=st,**r) for r in ev if r['horizon']==10)
  print('accounts',st,flush=True)
 write(pd.DataFrame(events),'events.csv');save_json(D/'accounts_complete.json',dict(files=record(list((D/'accounts').glob('*.csv'))+list((L/'orders').glob('*.parquet'))+[D/'events.csv']),accounts=receipts))

def analyze():
 verify();verify('selection_complete');verify('accounts_complete');assert not (D/'analysis_complete.json').exists();inp=Inputs();marks(inp,0.);checks=[];metrics=[];frames={};components={};periods=[];risk=[]
 def check(name,ok):assert bool(ok),name;checks.append(dict(name=name,passed=True))
 scores=pd.read_parquet(PRIVATE/OLD/'scores.parquet');targets=pd.read_parquet(L/'targets.parquet');ex=pd.read_csv(D/'target_exposures.csv',parse_dates=['signal_date']);Iex=ex[ex.strategy=='I'].groupby('style').agg(mean_I_minus_B=('difference','mean'),outside_fraction=('outside_bound','mean')).reset_index();write(Iex,'I_exposure_summary.csv')
 for path in (D/'accounts').glob('*.csv'):
  key=path.stem;st,cost=key.split('__');a=pd.read_csv(path,parse_dates=['date']).set_index('date');frames[key]=a;check(key+' full primary',len(a)==1001 and a.index[-1]==END);r=daily_returns(a.nav);prev=a.nav.shift(fill_value=1);metrics.append(dict(strategy=st,cost=cost,cagr=a.nav.iloc[-1]**(252/len(a))-1,nav=a.nav.iloc[-1],fees=a.fees.sum(),annual_oneway_turnover=float(((a.buy+a.sell)/(2*prev)).sum()*252/len(a))))
  for freq in ['Y','M']:
   for period,rr in r.groupby(r.index.to_period(freq)):periods.append(dict(strategy=st,cost=cost,freq=freq,period=str(period),return_value=np.prod(1+rr)-1))
  if cost=='main':
   o=pd.read_parquet(L/'orders'/(key+'.parquet'));c=absolute_components(inp,a,o);factor=np.divide(np.log1p(r),r,out=np.ones(len(r)),where=abs(r)>1e-12);components[st]=c.mul(factor,axis=0);check(key+' components',np.isclose(components[st].to_numpy().sum(),np.log(a.nav.iloc[-1]),atol=1e-10))
   for d,g in o.groupby('date'):
    sd=g.signal_date.iloc[0];panel=scores[scores.signal_date==sd].set_index('instrument');w=g.set_index('instrument').actual_weight;known=w.index.intersection(panel.index);z=pd.DataFrame(standard(panel[STYLES]),index=panel.index,columns=STYLES);b=targets[(targets.signal_date==sd)&(targets.strategy=='B')].set_index('instrument').weight;delta=z.loc[known].mul(w.reindex(known),axis=0).sum()-z.reindex(b.index).mul(b,axis=0).sum();risk.append(dict(strategy=st,date=d,unknown_weight=float(w.loc[w.index.difference(known)].sum()),max_style_gap=float(abs(delta).max()),cash=g.cash_weight.iloc[0]))
 for st in ['I','F']:
  old=pd.read_csv(OUT/'diagnostics'/BR/'accounts'/(st+'.csv'),parse_dates=['date']).set_index('date');check(st+' endpoint replay',np.allclose(old.nav,frames[st+'__main'].nav,atol=1e-12,rtol=1e-12))
 write(pd.DataFrame(metrics),'metrics.csv');write(pd.DataFrame(periods),'periods.csv');write(pd.DataFrame(risk),'actual_rebalance_risk.csv')
 comparisons=[('I','F','all_styles')]+[('I','only_'+g,'only_'+g) for g in GROUPS]+[('F','without_'+g,'remove_'+g) for g in GROUPS]+[('I',b,'replicate_'+b) for b in ['REV','MOM','MIX','COPY','B']]
 rows=[];stockrows=[];periodrows=[];pairs=[]
 for before,after,name in comparisons:
  for cost in ['main','zero']:
   aa=frames[after+'__'+cost];bb=frames[before+'__'+cost];r=daily_returns(aa.nav)-daily_returns(bb.nav);lo,hi=paired_ci(r);rows.append(dict(comparison=name,before=before,after=after,cost=cost,cagr_difference=aa.nav.iloc[-1]**(252/len(aa))-bb.nav.iloc[-1]**(252/len(bb)),annual_daily_difference=r.mean()*252,ci_low=lo,ci_high=hi))
  aa=frames[after+'__main'];bb=frames[before+'__main'];delta=components[after].subtract(components[before],fill_value=0);log=delta.to_numpy().sum();scale=100*(aa.nav.iloc[-1]-bb.nav.iloc[-1])/log if abs(log)>1e-12 else 100*bb.nav.iloc[-1];check(name+' stock bridge',np.isclose(log,np.log(aa.nav.iloc[-1]/bb.nav.iloc[-1]),atol=1e-10))
  for code,value in delta.sum().items():stockrows.append(dict(comparison=name,instrument=code,wealth_difference_contribution=value*scale))
  for freq in ['Y','M']:
   for period,g in delta.groupby(delta.index.to_period(freq)):periodrows.append(dict(comparison=name,freq=freq,period=str(period),wealth_difference_contribution=g.to_numpy().sum()*scale))
  # Target overlap and paired H10, no causal one-to-one matching of added/removed names.
  for date,g in targets.groupby('signal_date'):
   a=set(g[g.strategy==after].instrument);b=set(g[g.strategy==before].instrument);pairs.append(dict(comparison=name,signal_date=date,n_after=len(a),n_before=len(b),overlap_fraction=len(a&b)/len(b) if b else np.nan))
 write(pd.DataFrame(rows),'comparisons.csv');write(pd.DataFrame(stockrows),'stock_contributions.csv');write(pd.DataFrame(periodrows),'period_contributions.csv');write(pd.DataFrame(pairs),'target_overlap.csv')
 ev=pd.read_csv(D/'events.csv',parse_dates=['signal_date','exit_date']);ev=ev[ev.exit_date<=END];p=ev.pivot(index='signal_date',columns='strategy',values='net_return');er=[]
 for before,after,name in comparisons:
  delta=p[after]-p[before];er.append(dict(comparison=name,n=int(delta.notna().sum()),mean_net_H10=delta.mean()))
 write(pd.DataFrame(er),'event_comparisons.csv')
 # Replacement outcomes explain what changed, not why it was predictably profitable.
 replacements=pd.read_csv(D/'replacement_stocks.csv',parse_dates=['signal_date']);op=pd.read_parquet(PRIVATE/'qfq_open.parquet');ii=op.index.get_indexer(replacements.signal_date);jj=op.columns.get_indexer(replacements.instrument);valid=ii+11<len(op);y=np.full(len(ii),np.nan);y[valid]=op.to_numpy()[ii[valid]+11,jj[valid]]/op.to_numpy()[ii[valid]+1,jj[valid]]-1;replacements['gross_H10']=y;write(replacements,'replacement_outcomes.csv');write(replacements.groupby(['strategy','direction']).agg(rows=('instrument','size'),mean_E1_score=('E1_score','mean'),mean_gross_H10=('gross_H10','mean')).reset_index(),'replacement_summary.csv')
 # Full label-free target contracts and source preservation.
 for date,t in targets.groupby('signal_date'):
  g=scores[scores.signal_date==date].sort_values('instrument').reset_index(drop=True);k=int(np.ceil(len(g)/5));q=quotas(g,k);z=pd.DataFrame(standard(g[STYLES]),index=g.instrument,columns=STYLES);b=t[t.strategy=='B'].set_index('instrument').weight
  for st,a in t.groupby('strategy'):
   w=a.set_index('instrument').weight;counts=g.set_index('instrument').loc[w.index].industry.value_counts().reindex(q.index,fill_value=0);check(str(date)+st+' quota',len(w)==k and np.allclose(w,1/k) and np.array_equal(q,counts));active=[]
   if st=='F':active=STYLES
   if st.startswith('only_'):active=GROUPS[st[5:]]
   if st.startswith('without_'):active=[x for x in STYLES if x not in GROUPS[st[8:]]]
   if active:check(str(date)+st+' bound',abs(z.loc[w.index,active].mul(w,axis=0).sum()-z.loc[b.index,active].mul(b,axis=0).sum()).max()<=.2500001)
 save_json(D/'validation.json',dict(status='PASS',count=len(checks),checks=checks));verify();verify('selection_complete');verify('accounts_complete');save_json(D/'analysis_complete.json',dict(files=record(list(D.glob('*.csv'))+[D/'validation.json']),status='DESCRIPTIVE_COMPLETE'))
 print(pd.DataFrame(metrics).query("cost=='main'").sort_values('strategy').to_string(index=False),flush=True)

if __name__=='__main__':globals()[sys.argv[1]]()
