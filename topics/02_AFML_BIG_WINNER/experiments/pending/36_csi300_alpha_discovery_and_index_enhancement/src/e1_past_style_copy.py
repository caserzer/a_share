"""Past-only score distillation, quarterly expanding and first-fold locked."""
import sys,json
from pathlib import Path
from datetime import datetime,timezone
import numpy as np,pandas as pd
from common import EP,OUT,PRIVATE,sha,save_json
from alpha_economics import STYLES,target_vector,run_account,event_path
from e1_mechanism import standard,bootstrap
from e1_style_channels import fixed_pick
from alpha_falsification import rankcorr,project
from e1_return_attribution import daily_returns,paired_ci,absolute_components
from backtest import Inputs
from suspension_sensitivity import marks
RUN='e1_past_style_copy_20261117';D=OUT/'diagnostics'/RUN;L=PRIVATE/RUN;R=EP/'reports'/RUN;OLD='e1_alpha_mechanism_20261117';END=pd.Timestamp('2025-03-03')

def write(a,name,private=False):
 p=(L if private else D)/name;p.parent.mkdir(parents=True,exist_ok=True)
 if name.endswith('.parquet'):a.to_parquet(p,index=False)
 else:a.to_csv(p,index=False)
def record(paths):return [dict(path=str(p),sha256=sha(p)) for p in paths]
def verify(name='freeze'):
 r=json.loads((D/(name+'.json')).read_text())
 for p in r['files']:assert sha(p['path'])==p['sha256'],p['path']
 return r

def features_only(frame):
 assert set(frame.columns)<=set(STYLES+['industry','instrument','signal_date'])
 out=standard(frame[STYLES]);ind=frame.industry.to_numpy()
 for group in sorted(set(ind)):
  keep=ind==group;out[keep]-=out[keep].mean(axis=0)
 return out

def teacher_target(frame):
 y=standard(frame.E1);ind=frame.industry.to_numpy()
 for group in sorted(set(ind)):
  keep=ind==group;y[keep]-=y[keep].mean()
 return y

def fit_history(frame,cutoff,min_weeks=26,min_rows=2000):
 train=frame[frame.signal_date<cutoff];dates=sorted(train.signal_date.unique())
 if len(dates)<min_weeks or len(train)<min_rows:return None,dict(status='WARMUP',weeks=len(dates),rows=len(train))
 xx=[];yy=[]
 for date,g in train.groupby('signal_date'):
  weight=1/np.sqrt(len(g));xx.append(features_only(g[STYLES+['industry']])*weight);yy.append(teacher_target(g)*weight)
 coef,_,rank,svals=np.linalg.lstsq(np.vstack(xx),np.concatenate(yy),rcond=1e-12)
 return coef,dict(status='FIT',weeks=len(dates),rows=len(train),train_start=str(pd.Timestamp(dates[0])),train_end=str(pd.Timestamp(dates[-1])),cutoff=str(cutoff),rank=int(rank))

def freeze():
 D.mkdir(parents=True,exist_ok=True);L.mkdir(parents=True,exist_ok=True);R.mkdir(parents=True,exist_ok=True);assert not (D/'freeze.json').exists()
 cfg=dict(run=RUN,at=datetime.now(timezone.utc).isoformat(),prior_results_seen=True,new_outcomes_seen=False,teacher='sealed historical E1 scores; timing simulated, actual publication timestamps not certified',models={'Q':'quarter-start expanding OLS of past scores','LOCK':'first eligible Q fit fixed forever','I':'same-date E1 reference','COPY':'same-date OLS diagnostic, not deployable'},features=STYLES,transform='per-date zscore then industry demean X; per-date zscore then industry demean E1; equal date weights 1/sqrt(n)',fit='OLS rcond1e-12 no intercept; min26 prior signal dates and2000 rows; no return labels, regularization or window search',cutoff='signal strictly earlier than quarter start',prediction='features-only API rejects E1/returns',universe='sealed C sample including E1 scoring eligibility metadata, not full original universe',economic='fresh cash at first common original phase1 date after warmup; same industry quotas and ceil(n/5); end2025-03-03',costs={'main':[.001,.002],'zero':[0,0]},statistics='descriptive weekly13/monthly3 calendar blocks5000; daily65-trading-day blocks2000; no equivalence or confirmatory claim',independence='Q still needs past E1 updates; LOCK no teacher refresh after first fit, but teacher-derived and C universe constrained',forward='FORWARD_PENDING')
 cp=EP/'configs'/(RUN+'.json');assert not cp.exists();save_json(cp,cfg)
 files=[cp,Path(__file__),PRIVATE/OLD/'scores.parquet',OUT/'diagnostics'/OLD/'schedule.csv']
 files += [EP/'src'/s for s in ['alpha_economics.py','e1_mechanism.py','e1_style_channels.py','e1_advantage_bridge.py','alpha_falsification.py','e1_return_attribution.py','portfolio.py','backtest.py','suspension_sensitivity.py','common.py']]
 files += [PRIVATE/(s+'.parquet') for s in ['qfq_open','qfq_close','open','opening_trade_status_v2','daily_members','industry','labels']]+[PRIVATE/'limits/daily.parquet',PRIVATE/'suspensions/daily.parquet',PRIVATE/'weights/snapshots.parquet']
 save_json(D/'freeze.json',dict(files=record(files),new_outcomes_read=False));print('FROZEN',flush=True)

def prepare():
 verify();assert not (D/'selection_complete.json').exists();frame=pd.read_parquet(PRIVATE/OLD/'scores.parquet');frame=frame[frame.signal_date<=END];schedule=pd.read_csv(OUT/'diagnostics'/OLD/'schedule.csv',parse_dates=['signal_date']);phase=schedule.set_index('signal_date').phase.to_dict();coefs=[];fits=[];scores=[];targets=[];audit=[];locked=None;lockcut=None
 for quarter in sorted(frame.signal_date.dt.to_period('Q').unique()):
  cutoff=quarter.start_time;coef,info=fit_history(frame,cutoff);fits.append(dict(quarter=str(quarter),**info))
  if coef is None:continue
  if locked is None:locked=coef.copy();lockcut=cutoff
  altered=frame.copy();altered.loc[altered.signal_date>=cutoff,'E1']=1e6;checkcoef,_=fit_history(altered,cutoff);assert np.array_equal(coef,checkcoef)
  for st,c in [('Q',coef),('LOCK',locked)]:
   for feature,value in zip(STYLES,c):coefs.append(dict(quarter=str(quarter),strategy=st,feature=feature,coefficient=float(value),fit_cutoff=cutoff if st=='Q' else lockcut))
  test=frame[frame.signal_date.dt.to_period('Q')==quarter]
  for date,g in test.groupby('signal_date'):
   g=g.sort_values('instrument').reset_index(drop=True);x=features_only(g[STYLES+['industry']]);pred={'Q':x@coef,'LOCK':x@locked,'I':g.E1.to_numpy(),'COPY':project(x,teacher_target(g))[0]}
   row=g[['signal_date','instrument','industry']+STYLES].copy()
   for st,values in pred.items():row[st]=values
   scores.append(row);audit.append(dict(signal_date=date,quarter=str(quarter),n=len(g),Q_train_end=info['train_end'],LOCK_cutoff=lockcut,current_teacher_used_Q=False,current_teacher_used_LOCK=False))
   if phase[date]==1:
    k=int(np.ceil(len(g)/5))
    for st,values in pred.items():
     mask=fixed_pick(g,k,values)
     for j in np.flatnonzero(mask):targets.append(dict(signal_date=date,strategy=st,instrument=g.instrument.iloc[j],weight=1/k))
 write(pd.DataFrame(fits),'fits.csv');write(pd.DataFrame(coefs),'coefficients.csv');write(pd.DataFrame(audit),'prediction_audit.csv');write(pd.concat(scores),'scores.parquet',True);write(pd.DataFrame(targets),'targets.parquet',True)
 verify();save_json(D/'selection_complete.json',dict(files=record(list(D.glob('*.csv'))+list(L.glob('*.parquet'))),future_labels_read=False,current_and_future_teacher_mutation_check=True,first_monthly_signal=str(pd.DataFrame(targets).signal_date.min())));print('SEALED',len(targets),flush=True)

def run():
 verify();verify('selection_complete');assert not (D/'accounts_complete.json').exists();inp=Inputs();marks(inp,0.);targets=pd.read_parquet(L/'targets.parquet');dates=sorted(targets.signal_date.unique());events=[];receipts=[]
 for st,g in targets.groupby('strategy'):
  mapping={d:target_vector(inp,a) for d,a in g.groupby('signal_date')}
  for cost,fees in [('main',(.001,.002)),('zero',(0.,0.))]:
   a,o,fail=run_account(inp,mapping,dates,fees,end=END);key=st+'__'+cost;write(a,'accounts/'+key+'.csv');write(o,'orders/'+key+'.parquet',True);receipts.append(dict(strategy=st,cost=cost,failures=fail,days=len(a),start=str(a.date.min()),end=str(a.date.max())))
  for date,v in mapping.items():
   ev,_=event_path(inp,inp.days.get_loc(date),v,.001,.002);events.extend(dict(signal_date=date,strategy=st,**r) for r in ev if r['horizon']==10)
  print(st,flush=True)
 write(pd.DataFrame(events),'events.csv');save_json(D/'accounts_complete.json',dict(files=record(list((D/'accounts').glob('*.csv'))+list((L/'orders').glob('*.parquet'))+[D/'events.csv']),accounts=receipts))

def analyze():
 verify();verify('selection_complete');verify('accounts_complete');assert not (D/'analysis_complete.json').exists();s=pd.read_parquet(L/'scores.parquet');labels=pd.read_parquet(PRIVATE/'labels.parquet')[['signal_date','instrument','h10','h10_mature']];data=s.merge(labels,on=['signal_date','instrument'],validate='one_to_one');write(data,'labeled_scores.parquet',True);rows=[];recons=[];target=pd.read_parquet(L/'targets.parquet');overlap=[];checks=[]
 def check(name,ok):assert bool(ok),name;checks.append(dict(name=name,passed=True))
 for date,g in data.groupby('signal_date'):
  for st in ['Q','LOCK','COPY']:
   a=standard(g[st]);b=standard(g.I);recons.append(dict(signal_date=date,strategy=st,rank_correlation=rankcorr(g[st],g.I),standardized_MSE=float(np.mean((a-b)**2))))
  known=g[g.h10.notna()&(g.h10_mature<=END)]
  for st in ['I','Q','LOCK','COPY']:rows.append(dict(signal_date=date,strategy=st,n=len(known),rank_ic=rankcorr(known[st],known.h10) if len(known)>2 else np.nan))
 for date,g in target.groupby('signal_date'):
  base=set(g[g.strategy=='I'].instrument)
  for st,a in g.groupby('strategy'):
   names=set(a.instrument);overlap.append(dict(signal_date=date,strategy=st,overlap_with_I=len(names&base)/len(base),k=len(names)));check(str(date)+st+' cardinality',len(names)==len(base) and np.allclose(a.weight,1/len(base)))
 write(pd.DataFrame(recons),'score_reconstruction.csv');write(pd.DataFrame(rows),'rank_ic.csv');write(pd.DataFrame(overlap),'target_overlap.csv');ics=pd.DataFrame(rows).pivot(index='signal_date',columns='strategy',values='rank_ic');stats=[]
 for st in ['I','Q','LOCK','COPY']:stats.append(dict(metric='H10_RankIC',strategy=st,**bootstrap(ics[st],'W-FRI',13)))
 for st in ['Q','LOCK','COPY']:stats.append(dict(metric='H10_RankIC_minus_I',strategy=st,**bootstrap(ics[st]-ics.I,'W-FRI',13)))
 metrics=[];frames={};periods=[]
 for p in (D/'accounts').glob('*.csv'):
  st,cost=p.stem.split('__');a=pd.read_csv(p,parse_dates=['date']).set_index('date');frames[(st,cost)]=a;prev=a.nav.shift(fill_value=1);metrics.append(dict(strategy=st,cost=cost,start=str(a.index[0].date()),end=str(a.index[-1].date()),days=len(a),cagr=a.nav.iloc[-1]**(252/len(a))-1,nav=a.nav.iloc[-1],fees=a.fees.sum(),annual_oneway_turnover=float(((a.buy+a.sell)/(2*prev)).sum()*252/len(a))))
  for freq in ['Y','M']:
   for period,r in daily_returns(a.nav).groupby(a.index.to_period(freq)):periods.append(dict(strategy=st,cost=cost,freq=freq,period=str(period),return_value=np.prod(1+r)-1))
 write(pd.DataFrame(metrics),'metrics.csv');write(pd.DataFrame(periods),'periods.csv');compare=[]
 for st in ['Q','LOCK','COPY']:
  for cost in ['main','zero']:
   a=frames[(st,cost)];b=frames[('I',cost)];check(st+cost+' same fresh-start calendar',a.index.equals(b.index));r=daily_returns(a.nav)-daily_returns(b.nav);lo,hi=paired_ci(r);compare.append(dict(strategy=st,cost=cost,cagr_difference=a.nav.iloc[-1]**(252/len(a))-b.nav.iloc[-1]**(252/len(b)),annual_daily_difference=r.mean()*252,ci_low=lo,ci_high=hi))
 ev=pd.read_csv(D/'events.csv',parse_dates=['signal_date','exit_date']);ev=ev[ev.exit_date<=END].pivot(index='signal_date',columns='strategy',values='net_return');months=pd.DatetimeIndex(sorted(target.signal_date.unique()))
 for st in ['Q','LOCK','COPY']:stats.append(dict(metric='net_H10_minus_I',strategy=st,**bootstrap((ev[st]-ev.I).reindex(months),'M',3)))
 write(pd.DataFrame(compare),'account_comparisons.csv');write(pd.DataFrame(stats),'statistics.csv')
 fits=pd.read_csv(D/'fits.csv');fit=fits[fits.status=='FIT'];check('all fits strictly past',(pd.to_datetime(fit.train_end)<pd.to_datetime(fit.cutoff)).all());check('warmup',(fit.weeks>=26).all() and (fit['rows']>=2000).all())
 co=pd.read_csv(D/'coefficients.csv');check('LOCK coefficients unchanged',co[co.strategy=='LOCK'].groupby('feature').coefficient.nunique().eq(1).all())
 for date,t in target.groupby('signal_date'):
  g=s[s.signal_date==date].set_index('instrument');baseline=None
  for st,a in t.groupby('strategy'):
   counts=g.loc[a.instrument].industry.value_counts().sort_index()
   if baseline is None:baseline=counts
   else:check(str(date)+st+' same industry slots',counts.equals(baseline))
 inp=Inputs();marks(inp,0.)
 for (st,cost),a in frames.items():
  o=pd.read_parquet(L/'orders'/(st+'__'+cost+'.parquet'));comp=absolute_components(inp,a,o);check(st+cost+' daily ledger',np.allclose(comp.sum(axis=1),daily_returns(a.nav),atol=1e-10))
 save_json(D/'validation.json',dict(status='PASS',count=len(checks),checks=checks));verify();verify('selection_complete');verify('accounts_complete');save_json(D/'analysis_complete.json',dict(files=record(list(D.glob('*.csv'))+[D/'validation.json',L/'labeled_scores.parquet']),status='HISTORICAL_PAST_ONLY_COMPLETE',forward='FORWARD_PENDING'))
 print(pd.DataFrame(metrics).query("cost=='main'").to_string(index=False));print(pd.DataFrame(compare).query("cost=='main'").to_string(index=False))

if __name__=='__main__':globals()[sys.argv[1]]()
