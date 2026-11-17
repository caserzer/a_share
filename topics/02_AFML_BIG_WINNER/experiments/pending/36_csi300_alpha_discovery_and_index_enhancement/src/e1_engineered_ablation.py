"""Frozen full-model residual-group factorial; no fitting or outcome-based selection."""
import sys,json
from pathlib import Path
from datetime import datetime,timezone
import numpy as np,pandas as pd
from common import EP,OUT,PRIVATE,sha,save_json
from e1_mapping_drift import load,demean
from e1_past_style_copy import features_only
from e1_mechanism import standard,bootstrap
from alpha_falsification import project,rankcorr
from e1_style_channels import fixed_pick
from alpha_economics import STYLES,target_vector,run_account,event_path
from e1_return_attribution import daily_returns,absolute_components
from backtest import Inputs
from suspension_sensitivity import marks
RUN='e1_engineered_ablation_20261117';D=OUT/'diagnostics'/RUN;L=PRIVATE/RUN;R=EP/'reports'/RUN
END=pd.Timestamp('2025-03-03');START=pd.Timestamp('2021-10-08')
STRATEGIES=['NONE','POS','RISK','BOTH','STYLE','E1']
CONTRASTS={'position':{'BOTH':.5,'RISK':-.5,'POS':.5,'NONE':-.5},
'risk':{'BOTH':.5,'POS':-.5,'RISK':.5,'NONE':-.5},
'interaction':{'BOTH':1,'POS':-1,'RISK':-1,'NONE':1},
'joint':{'BOTH':1,'NONE':-1},'full_vs_style':{'BOTH':1,'STYLE':-1},
'pos_given_risk':{'BOTH':1,'RISK':-1},'risk_given_pos':{'BOTH':1,'POS':-1}}
PRIMARY=['position','risk','interaction']
def write(a,name,private=False):
 p=(L if private else D)/name;p.parent.mkdir(parents=True,exist_ok=True)
 if name.endswith('.parquet'):a.to_parquet(p,index=False)
 else:a.to_csv(p,index=False)
def record(paths):return [dict(path=str(p),sha256=sha(p)) for p in paths]
def verify(name='freeze'):
 for f in json.loads((D/(name+'.json')).read_text())['files']:assert sha(f['path'])==f['sha256'],f['path']
def factorial(y,p,v):
 return dict(NONE=y-p-v,POS=y-v,RISK=y-p,BOTH=y.copy())
def contrast(frame,weights):
 cols=list(weights);a=frame[cols]
 return a.mul(pd.Series(weights)).sum(axis=1,min_count=len(cols))
def holm(values):
 p=np.asarray(values,float);order=np.argsort(p);out=np.full(len(p),np.nan);mx=0.
 for i,j in enumerate(order):
  if np.isfinite(p[j]):mx=max(mx,min(1.,(len(p)-i)*p[j]));out[j]=mx
 return out
def daily_stat(series):
 a=series.to_numpy(float);assert np.isfinite(a).all();n=len(a);rng=np.random.default_rng(20261117)
 idx=((rng.integers(0,n,(5000,int(np.ceil(n/65))))[:,:,None]+np.arange(65))%n).reshape(5000,-1)[:,:n]
 b=a[idx].mean(axis=1)*252;m=a.mean()*252
 return dict(n=n,mean=m,ci_low=float(np.quantile(b,.025)),ci_high=float(np.quantile(b,.975)),p=float((1+np.sum(abs(b-m)>=abs(m)))/(len(b)+1)))
def freeze():
 for p in [D,L,R]:p.mkdir(parents=True,exist_ok=True)
 assert not (D/'freeze.json').exists()
 cfg=dict(run=RUN,at=datetime.now(timezone.utc).isoformat(),old_results_seen=True,new_outcomes_seen=False,
 model='original 2021Q4 full78 Ridge bundle fixed throughout; no new fit',sample='same C universe as past-style-copy; 2021-10-08 signals through 2025-02-28; terminal2025-03-03',
 scores='y global-standardized fixed78 then industry demean; p/v are original feature-group contributions after same13style projection. NONE=y-p-v;POS=y-v;RISK=y-p;BOTH=y; STYLE=projection13(y); E1=original changing reference',
 groups=['range_position','volatility_drawdown'],selection='same original phase1 dates, proportional industry quotas, ceil(n/5) equal weights, score tie by instrument; no ranking/weight tuning',
 costs={'main':[.001,.002],'zero':[0,0],'stress':[.003,.008]},
 primary={'metric':'annualized mean paired daily net-return contrast, not CAGR difference','contrasts':{k:CONTRASTS[k] for k in PRIMARY},'inference':'65day circular block5000 fixedseed; Holm3 two-sided approximate bootstrap p, intervals ordinary descriptive95%'},
 auxiliary='joint/full-vs-style/simple conditional differences; same-date H10 monthly3block5000; weekly H10 RankIC13block5000; no winner promotion',
 boundary='score residualization does not neutralize selected holdings; exact industry quotas only, report style exposure gaps; interaction is nonlinear selection/holding pathway not learned Ridge interaction; Historical-proxy and repeatedly used history, not blind confirmation',
 attribution='FULL versus NONE log-linked stock and calendar contributions, accounting not causality',forward='FORWARD_PENDING')
 cp=EP/'configs'/(RUN+'.json');assert not cp.exists();save_json(cp,cfg)
 files=[cp,Path(__file__)]+list((EP/'src').glob('*.py'))
 previous=OUT/'diagnostics/e1_mapping_drift_20261117/freeze.json'
 files += [Path(x['path']) for x in json.loads(previous.read_text())['files']]+[previous]
 files += [OUT/'diagnostics/e1_alpha_mechanism_20261117/schedule.csv']
 files += [PRIVATE/(s+'.parquet') for s in ['qfq_open','qfq_close','open','opening_trade_status_v2','daily_members','industry','labels']]+[PRIVATE/'limits/daily.parquet',PRIVATE/'suspensions/daily.parquet',PRIVATE/'weights/snapshots.parquet']
 save_json(D/'freeze.json',dict(files=record(sorted(set(files))),future_labels_read=False))
 (R/'PROTOCOL.md').write_text('# 冻结实验口径\n\n冻结时间：'+cfg['at']+'\n\n'+json.dumps(cfg,ensure_ascii=False,indent=2)+'\n')
 print('FROZEN',flush=True)
def prepare():
 verify();assert not (D/'selection_complete.json').exists()
 days,models,dictionary=load();bundle=models['2021Q4'];transform,model=bundle
 schedule=pd.read_csv(OUT/'diagnostics/e1_alpha_mechanism_20261117/schedule.csv',parse_dates=['signal_date']).set_index('signal_date').phase
 rows=[];targets=[];exposures=[];checks=[]
 for date,(g,raw) in days.items():
  if date<START or date>END:continue
  x=features_only(g[STYLES+['industry']]);transformed=transform.transform(raw);score=model.predict(transformed)
  y=demean(standard(score),g.industry);contrib=transformed*model.coef_;parts={}
  for group in ['range_position','volatility_drawdown']:
   a=demean(contrib[:,dictionary.mechanism_group.eq(group)].sum(axis=1)/score.std(),g.industry);parts[group]=project(x,a)[1]
  p,v=parts.values();sc=factorial(y,p,v);sc['STYLE']=project(x,y)[0];sc['E1']=g.E1.to_numpy()
  assert np.allclose(sc['BOTH']-sc['POS']-sc['RISK']+sc['NONE'],0,atol=1e-10)
  assert np.max(abs(x.T@p))<1e-8 and np.max(abs(x.T@v))<1e-8
  checks.append(dict(signal_date=date,orthogonal_error=float(max(np.max(abs(x.T@p)),np.max(abs(x.T@v))))))
  a=g[['signal_date','instrument','industry']].copy()
  for st,value in sc.items():a[st]=value
  rows.append(a)
  if schedule.loc[date]!=1:continue
  k=int(np.ceil(len(g)/5));z=standard(g[STYLES])
  for st,value in sc.items():
   mask=fixed_pick(g,k,value)
   for j in np.flatnonzero(mask):targets.append(dict(signal_date=date,strategy=st,instrument=g.instrument.iloc[j],weight=1/k))
   for j,s in enumerate(STYLES):exposures.append(dict(signal_date=date,strategy=st,style=s,exposure=float(z[:,j]@mask/k)))
 write(pd.concat(rows),'scores.parquet',True);write(pd.DataFrame(targets),'targets.parquet',True);write(pd.DataFrame(exposures),'target_exposures.csv');write(pd.DataFrame(checks),'score_checks.csv')
 verify();save_json(D/'selection_complete.json',dict(files=record(list(L.glob('*.parquet'))+list(D.glob('*.csv'))),future_labels_read=False))
 print('SEALED',len(rows),'signals',flush=True)
def run():
 verify();verify('selection_complete');assert not (D/'accounts_complete.json').exists()
 inp=Inputs();marks(inp,0.);targets=pd.read_parquet(L/'targets.parquet');dates=sorted(targets.signal_date.unique());events=[];receipts=[]
 for st,g in targets.groupby('strategy'):
  maps={d:target_vector(inp,a) for d,a in g.groupby('signal_date')}
  for cost,fees in [('main',(.001,.002)),('zero',(0.,0.)),('stress',(.003,.008))]:
   a,o,fail=run_account(inp,maps,dates,fees,end=END);key=st+'__'+cost
   write(a,'accounts/'+key+'.csv');write(o,'orders/'+key+'.parquet',True);receipts.append(dict(strategy=st,cost=cost,failures=fail,days=len(a)))
  for date,v in maps.items():
   ev,_=event_path(inp,inp.days.get_loc(date),v,.001,.002)
   events.extend(dict(signal_date=date,strategy=st,**r) for r in ev if r['horizon']==10)
  print('accounts',st,flush=True)
 write(pd.DataFrame(events),'events.csv')
 verify();save_json(D/'accounts_complete.json',dict(files=record(list((D/'accounts').glob('*.csv'))+list((L/'orders').glob('*.parquet'))+[D/'events.csv']),accounts=receipts))
def analyze():
 verify();verify('selection_complete');verify('accounts_complete');assert not (D/'analysis_complete.json').exists()
 checks=[]
 def check(name,ok):assert bool(ok),name;checks.append(dict(name=name,passed=True))
 inp=Inputs();marks(inp,0.);frames={};metrics=[];periods=[];components={}
 for p in sorted((D/'accounts').glob('*.csv')):
  st,cost=p.stem.split('__');a=pd.read_csv(p,parse_dates=['date']).set_index('date');frames[(st,cost)]=a;r=daily_returns(a.nav);prev=a.nav.shift(fill_value=1)
  check(p.stem+' calendar',len(a)==823 and a.index[0]==pd.Timestamp('2021-10-11') and a.index[-1]==END)
  check(p.stem+' ledger finite',np.isfinite(a.nav).all() and a.nav.gt(0).all())
  o=pd.read_parquet(L/'orders'/(p.stem+'.parquet'));c=absolute_components(inp,a,o)
  check(p.stem+' daily reconciliation',np.allclose(c.sum(axis=1),r,atol=1e-10))
  if cost=='main':
   factor=np.divide(np.log1p(r),r,out=np.ones(len(r)),where=abs(r)>1e-12);components[st]=c.mul(factor,axis=0)
  metrics.append(dict(strategy=st,cost=cost,nav=a.nav.iloc[-1],cagr=a.nav.iloc[-1]**(252/len(a))-1,annual_oneway_turnover=((a.buy+a.sell)/(2*prev)).sum()*252/len(a),max_drawdown=(a.nav/a.nav.cummax().clip(lower=1)-1).min()))
  for freq in ['Y','M']:
   for period,rr in r.groupby(r.index.to_period(freq)):periods.append(dict(strategy=st,cost=cost,freq=freq,period=str(period),return_value=np.prod(1+rr)-1))
 write(pd.DataFrame(metrics),'metrics.csv');write(pd.DataFrame(periods),'periods.csv')
 comparisons=[]
 for cost in ['main','zero','stress']:
  panel=pd.DataFrame({st:daily_returns(frames[(st,cost)].nav) for st in STRATEGIES})
  for name,weights in CONTRASTS.items():
   s=contrast(panel,weights);comparisons.append(dict(cost=cost,comparison=name,primary=cost=='main' and name in PRIMARY,**daily_stat(s)))
 comp=pd.DataFrame(comparisons);comp['p_holm']=np.nan;ix=comp.primary;comp.loc[ix,'p_holm']=holm(comp.loc[ix,'p'].to_numpy());write(comp,'comparisons.csv')
 events=pd.read_csv(D/'events.csv',parse_dates=['signal_date','exit_date']);ev=events[events.exit_date<=END].pivot(index='signal_date',columns='strategy',values='net_return')
 targets=pd.read_parquet(L/'targets.parquet');months=pd.DatetimeIndex(sorted(targets.signal_date.unique()));stats=[]
 for name,w in CONTRASTS.items():stats.append(dict(comparison=name,**bootstrap(contrast(ev,w).reindex(months),'M',3)))
 write(pd.DataFrame(stats),'event_statistics.csv')
 scores=pd.read_parquet(L/'scores.parquet');lab=pd.read_parquet(PRIVATE/'labels.parquet')[['signal_date','instrument','h10','h10_mature']]
 data=scores.merge(lab,on=['signal_date','instrument'],validate='one_to_one');ics=[]
 for date,g in data.groupby('signal_date'):
  g=g[g.h10.notna()&(g.h10_mature<=END)]
  for st in STRATEGIES:ics.append(dict(signal_date=date,strategy=st,rank_ic=rankcorr(g[st],g.h10) if len(g)>2 else np.nan))
 ic=pd.DataFrame(ics);write(ic,'rank_ic.csv');write(pd.DataFrame([dict(strategy=st,**bootstrap(g.set_index('signal_date').rank_ic,'W-FRI',13)) for st,g in ic.groupby('strategy')]),'ic_statistics.csv')
 for date,t in targets.groupby('signal_date'):
  g=scores[scores.signal_date==date].set_index('instrument');base=None
  for st,a in t.groupby('strategy'):
   counts=g.loc[a.instrument].industry.value_counts().sort_index()
   check(str(date)+st+' weights',a.instrument.is_unique and np.allclose(a.weight,1/len(a)) and len(a)==int(np.ceil(len(g)/5)))
   if base is None:base=counts
   else:check(str(date)+st+' industry slots',counts.equals(base))
 old=pd.read_csv(OUT/'diagnostics/e1_past_style_copy_20261117/accounts/I__main.csv',parse_dates=['date']).set_index('date')
 check('E1 original reference replay',np.allclose(old.nav,frames[('E1','main')].nav,atol=1e-12))
 prior=pd.read_parquet(PRIVATE/'e1_mapping_drift_20261117/score_components.parquet')
 for date,g in scores.groupby('signal_date'):
  b=prior[prior.signal_date==date].set_index('instrument').loc[g.instrument]
  check(str(date)+' fixed model rank replay',abs(rankcorr(g.BOTH,demean(standard(b.FIXED78),g.industry))-1)<1e-10)
 ex=pd.read_csv(D/'target_exposures.csv');ep=ex.pivot(index=['signal_date','style'],columns='strategy',values='exposure');er=[]
 for st in ['NONE','POS','RISK','STYLE','E1']:
  delta=ep.BOTH-ep[st]
  for style,g in delta.groupby(level='style'):er.append(dict(comparator=st,style=style,mean_gap=g.mean(),mean_abs_gap=g.abs().mean(),max_abs_gap=g.abs().max()))
 write(pd.DataFrame(er),'exposure_gaps.csv')
 delta=components['BOTH'].subtract(components['NONE'],fill_value=0);gap=100*(frames[('BOTH','main')].nav.iloc[-1]-frames[('NONE','main')].nav.iloc[-1]);lg=delta.to_numpy().sum()
 check('joint log bridge',abs(lg-np.log(frames[('BOTH','main')].nav.iloc[-1]/frames[('NONE','main')].nav.iloc[-1]))<1e-10)
 scale=gap/lg if abs(lg)>1e-12 else 100*frames[('NONE','main')].nav.iloc[-1]
 stocks=delta.sum()*scale;write(stocks.rename_axis('instrument').reset_index(name='wealth_gap_contribution'),'joint_stock_contributions.csv')
 pr=[]
 for freq in ['Y','M']:
  for period,g in delta.groupby(delta.index.to_period(freq)):pr.append(dict(freq=freq,period=str(period),wealth_gap_contribution=g.to_numpy().sum()*scale))
 write(pd.DataFrame(pr),'joint_period_contributions.csv');check('joint stock closure',abs(stocks.sum()-gap)<1e-9)
 save_json(D/'validation.json',dict(status='PASS',count=len(checks),checks=checks))
 verify();verify('selection_complete');verify('accounts_complete')
 save_json(D/'analysis_complete.json',dict(files=record(list(D.glob('*.csv'))+[D/'validation.json']),status='HISTORICAL_EXPLORATORY_COMPLETE',forward='FORWARD_PENDING'))
 print(pd.DataFrame(metrics).query("cost=='main'").to_string(index=False));print(comp[comp.cost=='main'].to_string(index=False),flush=True)
if __name__=='__main__':globals()[sys.argv[1]]()
