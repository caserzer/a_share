"""Evaluation-only zero-support handling. Original frozen implementation and targets unchanged.
This copy adds explicit unsupported inference and empty-schema handling, not rule changes.
"""
import sys,json
from pathlib import Path
from datetime import datetime,timezone
import numpy as np,pandas as pd
from scipy.optimize import linprog
from common import EP,OUT,PRIVATE,sha,save_json
from alpha_economics import STYLES,target_vector,run_account,event_path
from e1_mechanism import standard,bootstrap
from e1_engineered_ablation import daily_stat,holm
from e1_return_attribution import daily_returns,absolute_components
from alpha_falsification import project,rankcorr
from backtest import Inputs
from suspension_sensitivity import marks
RUN='e1_excluded_styles_20261117';D=OUT/'diagnostics'/RUN;L=PRIVATE/RUN;R=EP/'reports'/RUN
PREV='e1_excluded_holdings_20261117';END=pd.Timestamp('2025-03-03')
BASES=['REV','MOM','LOWVOL','HIGHVOL','MIX'];ACCOUNTS=['O']+BASES+['SM']
STYLECOLS=['mom1','mom5','mom20','mom60','vol20','vol60']
def write(a,name,private=False):
 p=(L if private else D)/name;p.parent.mkdir(parents=True,exist_ok=True)
 if name.endswith('.parquet'):a.to_parquet(p,index=False)
 else:a.to_csv(p,index=False)
def record(paths):return [dict(path=str(p),sha256=sha(p)) for p in paths]
def verify(name='freeze'):
 for f in json.loads((D/(name+'.json')).read_text())['files']:assert sha(f['path'])==f['sha256'],f['path']
def baseline_scores(g):
 r=g[STYLECOLS].rank(pct=True,method='average')
 out=pd.DataFrame(index=g.index)
 out['REV']=-(r.mom1+r.mom5)/2;out['MOM']=(r.mom20+r.mom60)/2
 out['HIGHVOL']=(r.vol20+r.vol60)/2;out['LOWVOL']=-out.HIGHVOL
 # Re-rank component scores to equal marginal rank scale, no learned coefficients.
 out['MIX']=out[['REV','MOM','HIGHVOL']].rank(pct=True).mean(axis=1)
 return out
def match_styles(z,target,budget,cap,tol=.25):
 """Full thirteen-style bounds; feasible only, never relax or choose by returns."""
 z=np.asarray(z,float);target=np.asarray(target,float)
 if len(z)*cap<budget-1e-12:return None,dict(status='INSUFFICIENT_PEER_CAPACITY')
 cost=((z-target)**2).sum(axis=1)+np.arange(len(z))*1e-10
 result=linprog(cost,A_ub=np.vstack([z.T,-z.T]),b_ub=np.r_[(target+tol)*budget,(-target+tol)*budget],A_eq=np.ones((1,len(z))),b_eq=[budget],bounds=[(0,cap)]*len(z),method='highs')
 if not result.success:return None,dict(status='INFEASIBLE',solver_status=int(result.status))
 w=result.x;gap=np.max(abs(z.T@w/budget-target))
 if abs(w.sum()-budget)>1e-9 or gap>tol+1e-7 or w.max()>cap+1e-9:return None,dict(status='INVALID_SOLUTION')
 return w,dict(status='MATCHED',max_gap=float(gap))
def freeze():
 for p in [D,L,R]:p.mkdir(parents=True,exist_ok=True)
 assert not (D/'freeze.json').exists()
 cfg=dict(run=RUN,at=datetime.now(timezone.utc).isoformat(),prior_results_seen=True,new_results_seen=False,
 universe='exact prior P matched excluded targets and original same-industry disjoint peers; original50dates and1001days',
 baselines='REV=-mean rank(mom1,mom5);MOM=mean rank(mom20,mom60);HIGHVOL=mean rank(vol20,vol60);LOWVOL=-HIGHVOL; MIX=equal mean component ranks REV,MOM,HIGHVOL. Highvol direction informed by already-observed profiles; exploratory not independent.',
 selection='per-industry eligible union of prior matched original names and disjoint peers; all6 baseline inputs finite; original matched industry group with any missing input retained for ALL baselines; top original count, equal original industry budget; exclude other original retained names; missing candidate inputs dropped; score tie instrument ascending; no >=10 restriction',
 style_match='per-industry prior matched original group ALL13 finite; disjoint original-scored peers ALL13 finite; whole group retained if unsupported. zscore all same-date ALL13 complete scored stocks, no >=10 restriction. LP min sum w*squared-distance-to-original-stylemean; sumw=originalgroupbudget;0<=w<=max original stock weight; each13 gap<=.25SD; no relaxation.',
 main_tests=['O-MIX annual daily net mean','normalized baseline-supported original sleeve minus MIX sleeve netH10','O-SM annual daily net mean','normalized style-matched original sleeve minus disjoint stylematched sleeve netH10'],
 statistics='daily65blocks5000/monthly3blocks5000seed20261117; Holm4, ordinary95%CI; unsupported events remain missing; matching coverage reported not screened by performance',
 conditional='auxiliary weekly excluded candidate ALL13 complete, known industry, finite matureH10; residualize ranks of E1 and H10 on rank13styles plus industry indicators+intercept; require n-rank>=30; no >=10 industry minimum; weekly13blocks5000; linear conditional association not causal',
 costs={'main':[.001,.002],'zero':[0,0],'stress':[.003,.008]},
 limits='SM only supports matched portion; complete styles not PIT-certified; scores/risk controls use original E1 pool and exclusion metadata; baselines not globally independent models; no equivalence conclusion from nonsignificance',forward='FORWARD_PENDING')
 cp=EP/'configs'/(RUN+'.json');assert not cp.exists();save_json(cp,cfg)
 files=[cp]+list((EP/'src').glob('*.py'))+[PRIVATE/PREV/'panel.parquet',PRIVATE/PREV/'targets.parquet',OUT/'diagnostics'/PREV/'matching.csv',OUT/'diagnostics'/PREV/'accounts/O__main.csv']
 files += [PRIVATE/(s+'.parquet') for s in ['qfq_open','qfq_close','open','opening_trade_status_v2','daily_members','industry','labels']]+[PRIVATE/'limits/daily.parquet',PRIVATE/'suspensions/daily.parquet',PRIVATE/'weights/snapshots.parquet']
 save_json(D/'freeze.json',dict(files=record(sorted(set(files))),future_returns_read=False))
 (R/'PROTOCOL.md').write_text('# 被排除持仓风格检验冻结协议\n\n'+json.dumps(cfg,ensure_ascii=False,indent=2)+'\n');print('FROZEN',flush=True)
def prepare():
 verify();assert not (D/'selection_complete.json').exists()
 panel=pd.read_parquet(PRIVATE/PREV/'panel.parquet');old=pd.read_parquet(PRIVATE/PREV/'targets.parquet');orig=old[old.strategy=='O']
 audit=pd.read_csv(OUT/'diagnostics'/PREV/'matching.csv',parse_dates=['signal_date'])
 audit=audit[(audit['mode']=='P')&(audit.status=='MATCHED')]
 rows=[];support=[];risk=[];cohorts=[]
 for date,o in orig.groupby('signal_date'):
  g=panel[panel.signal_date==date].set_index('instrument').sort_index();ow=o.set_index('instrument').weight;maps={st:ow.to_dict() for st in ACCOUNTS}
  complete=np.isfinite(g[STYLES]).all(axis=1);z=pd.DataFrame(standard(g.loc[complete,STYLES]),index=g.index[complete],columns=STYLES)
  sleeves={'BASE_O':{},'BASE_MIX':{},'SM_O':{},'SM_PEER':{}}
  ma=audit[audit.signal_date==date]
  for industry,grp in ma.groupby('industry'):
   chosen=sorted(grp.instrument);budget=ow.loc[chosen].sum();k=len(chosen)
   peer=sorted(set('|'.join(grp.peer_codes).split('|')));union=sorted(set(peer)|set(chosen))
   pool=g.loc[union];valid=np.isfinite(pool[STYLECOLS]).all(axis=1);candidates=pool[valid]
   baseok=set(chosen)<=set(candidates.index)
   support.append(dict(signal_date=date,industry=industry,test='BASE',budget=budget,status='MATCHED' if baseok else 'ORIGINAL_INPUT_MISSING',original_count=k,peer_count=len(peer)))
   if baseok:
    sc=baseline_scores(candidates)
    for st in BASES:
     pick=sc[st].sort_values(ascending=False,kind='stable').index[:k]
     for code in chosen:maps[st].pop(code)
     for code in pick:maps[st][code]=budget/k
     if st=='MIX':
      sleeves['BASE_MIX'].update({code:budget/k for code in pick})
     cohorts.append(dict(signal_date=date,industry=industry,strategy=st,k=k,overlap=len(set(pick)&set(chosen))/k))
    sleeves['BASE_O'].update(ow.loc[chosen].to_dict())
   known_orig=set(chosen)<=set(z.index);pvalid=sorted(set(peer)&set(z.index));info={'status':'ORIGINAL_STYLE_MISSING'};weights=None
   if known_orig:
    target=z.loc[chosen].T@ow.loc[chosen]/budget
    weights,info=match_styles(z.loc[pvalid].to_numpy(),target.to_numpy(),budget,ow.loc[chosen].max())
   support.append(dict(signal_date=date,industry=industry,test='SM',budget=budget,original_count=k,peer_count=len(pvalid),**info))
   if weights is not None:
    for code in chosen:maps['SM'].pop(code)
    w={code:float(w) for code,w in zip(pvalid,weights) if w>1e-14};maps['SM'].update(w)
    sleeves['SM_O'].update(ow.loc[chosen].to_dict());sleeves['SM_PEER'].update(w)
    gap=z.loc[list(w)].T@pd.Series(w)/budget-target
    for feature in STYLES:risk.append(dict(signal_date=date,industry=industry,style=feature,gap=gap[feature],budget=budget))
  for st,w in sleeves.items():
   if sum(w.values())>0:maps[st]={k:v/sum(w.values()) for k,v in w.items()}
  for st,w in maps.items():
   for code,weight in w.items():rows.append(dict(signal_date=date,strategy=st,instrument=code,weight=weight))
 write(pd.DataFrame(rows),'targets.parquet',True);write(pd.DataFrame(support),'support.csv');write(pd.DataFrame(risk),'matched_risk.csv');write(pd.DataFrame(cohorts),'baseline_overlap.csv')
 verify();save_json(D/'selection_complete.json',dict(files=record(list(L.glob('*.parquet'))+list(D.glob('*.csv'))),future_returns_read=False));print('SEALED',flush=True)
def run():
 verify();verify('selection_complete');assert not (D/'accounts_complete.json').exists()
 inp=Inputs();marks(inp,0.);t=pd.read_parquet(L/'targets.parquet');dates=sorted(t.signal_date.unique());receipts=[];events=[]
 for st,g in t.groupby('strategy'):
  maps={d:target_vector(inp,a) for d,a in g.groupby('signal_date')}
  if st in ACCOUNTS:
   for cost,fees in [('main',(.001,.002)),('zero',(0.,0.)),('stress',(.003,.008))]:
    a,o,fail=run_account(inp,maps,dates,fees,end=END);key=st+'__'+cost;write(a,'accounts/'+key+'.csv');write(o,'orders/'+key+'.parquet',True);receipts.append(dict(strategy=st,cost=cost,days=len(a),failures=fail))
  if st in ['BASE_O','BASE_MIX','SM_O','SM_PEER']:
   for date,vec in maps.items():
    ev,_=event_path(inp,inp.days.get_loc(date),vec,.001,.002);events.extend(dict(signal_date=date,strategy=st,**a) for a in ev if a['horizon']==10)
  print(st,flush=True)
 write(pd.DataFrame(events),'events.csv');verify();save_json(D/'accounts_complete.json',dict(files=record(list((D/'accounts').glob('*.csv'))+list((L/'orders').glob('*.parquet'))+[D/'events.csv']),accounts=receipts))
def analyze():
 verify();verify('selection_complete');verify('accounts_complete');assert not (D/'analysis_complete.json').exists()
 checks=[]
 def ck(name,ok):assert bool(ok),name;checks.append(dict(name=name,passed=True))
 inp=Inputs();marks(inp,0.);frames={};metrics=[];periods=[];components={}
 for p in sorted((D/'accounts').glob('*.csv')):
  st,cost=p.stem.split('__');a=pd.read_csv(p,parse_dates=['date']).set_index('date');frames[(st,cost)]=a;r=daily_returns(a.nav);prev=a.nav.shift(fill_value=1)
  ck(p.stem+' calendar',len(a)==1001 and a.index[0]==pd.Timestamp('2021-01-11') and a.index[-1]==END)
  c=absolute_components(inp,a,pd.read_parquet(L/'orders'/(p.stem+'.parquet')));ck(p.stem+' ledger',np.allclose(c.sum(axis=1),r,atol=1e-10))
  if cost=='main':components[st]=c.mul(np.divide(np.log1p(r),r,out=np.ones(len(r)),where=abs(r)>1e-12),axis=0)
  metrics.append(dict(strategy=st,cost=cost,cagr=a.nav.iloc[-1]**(252/len(a))-1,nav=a.nav.iloc[-1],annual_oneway_turnover=((a.buy+a.sell)/(2*prev)).sum()*252/len(a),holdings=a.holdings.mean()))
  for freq in ['Y','M']:
   for per,s in r.groupby(r.index.to_period(freq)):periods.append(dict(strategy=st,cost=cost,freq=freq,period=str(per),return_value=np.prod(1+s)-1))
 old=pd.read_csv(OUT/'diagnostics'/PREV/'accounts/O__main.csv',parse_dates=['date']).set_index('date');ck('original replay',np.allclose(old.nav,frames[('O','main')].nav,atol=1e-12))
 write(pd.DataFrame(metrics),'metrics.csv');write(pd.DataFrame(periods),'periods.csv')
 stats=[]
 for cost in ['main','zero','stress']:
  for st in BASES+['SM']:
   s=daily_returns(frames[('O',cost)].nav)-daily_returns(frames[(st,cost)].nav)
   supported=st!='SM' or (pd.read_csv(D/'support.csv').query("test=='SM'").status=='MATCHED').any()
   result=daily_stat(s) if supported else dict(n=0,mean=np.nan,ci_low=np.nan,ci_high=np.nan,p=np.nan)
   stats.append(dict(metric='annual_daily',comparison='O-'+st,cost=cost,primary=cost=='main' and st in ['MIX','SM'],status='ESTIMATED' if supported else 'NO_MATCHING_SUPPORT',**result))
 t=pd.read_parquet(L/'targets.parquet');dates=pd.DatetimeIndex(sorted(t.signal_date.unique()))
 events=pd.read_csv(D/'events.csv',parse_dates=['signal_date','exit_date']);events=events[events.exit_date<=END]
 ev=events.pivot(index='signal_date',columns='strategy',values='net_return').reindex(columns=['BASE_O','BASE_MIX','SM_O','SM_PEER'])
 for left,right in [('BASE_O','BASE_MIX'),('SM_O','SM_PEER')]:
  s=(ev[left]-ev[right]).reindex(dates);stats.append(dict(metric='H10_event',comparison=left+'-'+right,cost='main',primary=True,status='ESTIMATED' if s.notna().any() else 'NO_MATCHING_SUPPORT',**bootstrap(s,'M',3)))
 stats=pd.DataFrame(stats);stats['p_holm']=np.nan;ix=stats.primary;stats.loc[ix,'p_holm']=holm(stats.loc[ix,'p'].to_numpy());write(stats,'statistics.csv')
 panel=pd.read_parquet(PRIVATE/PREV/'panel.parquet')
 sup=pd.read_csv(D/'support.csv',parse_dates=['signal_date']);risks=pd.read_csv(D/'matched_risk.csv') if (D/'matched_risk.csv').stat().st_size>1 else pd.DataFrame(columns=['gap'])
 if len(risks):ck('all matched risk gaps bounded',risks.gap.abs().max()<=.2500001)
 else:
  ck('zero risk rows imply zero matched groups',not ((sup.test=='SM')&(sup.status=='MATCHED')).any())
  for cost in ['main','zero','stress']:ck(cost+' SM unsupported exact fallback',np.allclose(frames[('SM',cost)].nav,frames[('O',cost)].nav,atol=1e-12))
 prior_match=pd.read_csv(OUT/'diagnostics'/PREV/'matching.csv',parse_dates=['signal_date']);prior_match=prior_match[prior_match['mode']=='P']
 coverage=[]
 for date,a in sup.groupby('signal_date'):
  oldm=prior_match[prior_match.signal_date==date]
  for test,b in a.groupby('test'):
   covered=b.loc[b.status=='MATCHED','budget'].sum();coverage.append(dict(signal_date=date,test=test,excluded_budget=oldm.budget.sum(),prior_P_budget=a[a.test=='BASE'].budget.sum(),covered_budget=covered,groups=int((b.status=='MATCHED').sum())))
 write(pd.DataFrame(coverage),'coverage.csv')
 for date,a in t.groupby('signal_date'):
  g=panel[panel.signal_date==date].set_index('instrument');o=a[a.strategy=='O'].set_index('instrument').weight
  origsector=o.groupby(g.industry.reindex(o.index).fillna('UNKNOWN')).sum()
  for st,b in a.groupby('strategy'):
   w=b.set_index('instrument').weight;ck(str(date)+st+' weights',w.index.is_unique and np.isclose(w.sum(),1) and w.gt(0).all())
   if st in ACCOUNTS:
    sectors=w.groupby(g.industry.reindex(w.index).fillna('UNKNOWN')).sum()
    ck(str(date)+st+' industry',sectors.index.equals(origsector.index) and np.allclose(sectors,origsector,atol=1e-10))
   if st in BASES:ck(str(date)+st+' same count',len(w)==len(o))
  for row in sup[(sup.signal_date==date)&(sup.status!='MATCHED')].itertuples():
   oldnames=prior_match[(prior_match.signal_date==date)&(prior_match.industry==row.industry)&(prior_match.status=='MATCHED')].instrument
   for st in (BASES if row.test=='BASE' else ['SM']):
    w=a[a.strategy==st].set_index('instrument').weight
    ck(str(date)+str(row.industry)+st+' unsupported retained',np.allclose(w.reindex(oldnames),o.reindex(oldnames)))
 # Conditional ranking on excluded stocks with full styles; no size10 filter.
 labels=pd.read_parquet(PRIVATE/'labels.parquet')[['signal_date','instrument','h10','h10_mature']]
 data=panel.merge(labels,on=['signal_date','instrument'],validate='one_to_one');conditional=[]
 for date,g in data.groupby('signal_date'):
  excluded=g[(g.exclusion_reason!='IN_C')&g.industry.ne('UNKNOWN')]
  g=excluded[np.isfinite(excluded[STYLES+['E1']]).all(axis=1)&excluded.h10.notna()&(excluded.h10_mature<=END)].copy()
  n=len(g);value=np.nan;rank=0
  if n>0:
   x=np.column_stack([np.ones(n),g[STYLES].rank(pct=True).to_numpy(),pd.get_dummies(g.industry,drop_first=True).to_numpy(float)])
   _,rs,_,rank=project(x,g.E1.rank(pct=True).to_numpy());_,ry,_,_=project(x,g.h10.rank(pct=True).to_numpy())
   if n-rank>=30 and rs.std()>1e-12 and ry.std()>1e-12:value=float(np.corrcoef(rs,ry)[0,1])
  conditional.append(dict(signal_date=date,n=n,total_excluded=len(excluded),rank=rank,df=n-rank,conditional_rank_ic=value))
 cond=pd.DataFrame(conditional);write(cond,'conditional_ic.csv');save_json(D/'conditional_statistics.json',bootstrap(cond.set_index('signal_date').conditional_rank_ic,'W-FRI',13))
 # Account differences by stock and time; they are not mechanism causality.
 stockrows=[];prows=[]
 for st in ['MIX','SM']:
  delta=components['O'].subtract(components[st],fill_value=0);lg=delta.to_numpy().sum();gap=100*(frames[('O','main')].nav.iloc[-1]-frames[(st,'main')].nav.iloc[-1]);scale=gap/lg if abs(lg)>1e-12 else 100*frames[(st,'main')].nav.iloc[-1]
  ck(st+' log closure',abs(lg-np.log(frames[('O','main')].nav.iloc[-1]/frames[(st,'main')].nav.iloc[-1]))<1e-10)
  for code,v in delta.sum().items():stockrows.append(dict(comparison='O-'+st,instrument=code,wealth_contribution=v*scale))
  for freq in ['Y','M']:
   for per,b in delta.groupby(delta.index.to_period(freq)):prows.append(dict(comparison='O-'+st,freq=freq,period=str(per),wealth_contribution=b.to_numpy().sum()*scale))
 write(pd.DataFrame(stockrows),'stock_contributions.csv');write(pd.DataFrame(prows),'period_contributions.csv')
 save_json(D/'validation.json',dict(status='PASS',count=len(checks),checks=checks))
 for stage in ['freeze','selection_complete','accounts_complete']:verify(stage)
 save_json(D/'analysis_complete.json',dict(files=record(list(D.glob('*.csv'))+[D/'validation.json',D/'conditional_statistics.json']),status='EXPLORATORY_PARTIAL_IDENTIFICATION',forward='FORWARD_PENDING'))
 print(pd.DataFrame(metrics).query("cost=='main'").to_string(index=False));print(stats[stats.primary].to_string(index=False),flush=True)
if __name__=='__main__':analyze()
