"""Original excluded-holdings audit with frozen same-industry replacement controls."""
import sys,json
from pathlib import Path
from datetime import datetime,timezone
import numpy as np,pandas as pd
from common import EP,OUT,PRIVATE,sha,save_json
from alpha_economics import STYLES,target_vector,run_account,event_path
from e1_mechanism import bootstrap,standard
from e1_engineered_ablation import daily_stat,holm
from e1_return_attribution import daily_returns,absolute_components
from alpha_falsification import rankcorr
from backtest import Inputs
from suspension_sensitivity import marks
RUN='e1_excluded_holdings_20261117';D=OUT/'diagnostics'/RUN;L=PRIVATE/RUN;R=EP/'reports'/RUN
OLD='e1_alpha_mechanism_20261117';BR='e1_advantage_bridge_20261117';END=pd.Timestamp('2025-03-03')
def write(a,name,private=False):
 p=(L if private else D)/name;p.parent.mkdir(parents=True,exist_ok=True)
 if name.endswith('.parquet'):a.to_parquet(p,index=False)
 else:a.to_csv(p,index=False)
def record(paths):return [dict(path=str(p),sha256=sha(p)) for p in paths]
def verify(name='freeze'):
 for f in json.loads((D/(name+'.json')).read_text())['files']:assert sha(f['path'])==f['sha256'],f['path']
def replacement(original,panel,mode):
 """Only known decision metadata; retain unmatchable original weights."""
 assert mode in ['P','PR']
 orig=original.set_index('instrument');pool=panel.set_index('instrument');weights=orig.weight.to_dict();matched={};peers={};audit=[]
 for code,row in orig.iterrows():
  reason=pool.loc[code,'exclusion_reason'] if code in pool.index else 'NO_SIGNAL_ROW'
  if reason=='IN_C':continue
  status='MATCHED';candidate=pool.iloc[:0]
  if code not in pool.index:status='NO_SIGNAL_ROW'
  elif pool.loc[code,'industry']=='UNKNOWN':status='INDUSTRY_UNKNOWN'
  elif pool.loc[code,'industry']!=row.industry:status='INDUSTRY_SOURCE_DISAGREEMENT'
  else:
   candidate=pool[(pool.industry==row.industry)&(~pool.index.isin(orig.index))&np.isfinite(pool.E1)]
   if mode=='PR':candidate=candidate[candidate.exclusion_reason==reason]
   if len(candidate)==0:status='NO_DISJOINT_PEER'
  if status=='MATCHED':
   weights[code]-=row.weight;matched[code]=row.weight
   for peer in candidate.index:
    w=row.weight/len(candidate);weights[peer]=weights.get(peer,0)+w;peers[peer]=peers.get(peer,0)+w
  audit.append(dict(instrument=code,mode=mode,industry=row.industry,reason=reason,budget=row.weight,status=status,n_peers=len(candidate),peer_codes='|'.join(candidate.index)))
 return {k:v for k,v in weights.items() if v>1e-14},matched,peers,audit
def freeze():
 for p in [D,L,R]:p.mkdir(parents=True,exist_ok=True)
 assert not (D/'freeze.json').exists()
 cfg=dict(run=RUN,at=datetime.now(timezone.utc).isoformat(),prior_results_seen=True,new_control_outcomes_seen=False,scope='original E1 monthly 2021-01-08 through2025-03-03,50signals,1001accountdays',attribution='reuse sealed monthly-decision exclusion clock; full original active wealth ledger, no rewriting; separate excluded stock contribution from fees/cash and account replacement effect',
 controls={'O':'exact original','P':'replace each excluded known-industry target budget by equal weights across ALL same-industry original-scored nonselected stocks; >=1 peer; retained original for unknown/mismatch/no peers','PR':'same as P, but peers also same exact frozen exclusion reason'},selection='no return labels; no minimum10 restriction; no new missing-style restriction; exclude all original selected names from peers; aggregated peer weights may concentrate; no next-open lookahead',
 events='original matched sleeve and peer sleeve each normalized to1 for P only, matchedbudget fixed before returns; H10 maincost independent liquidation; no matched budget => missing; equal monthly event weights, not original equity weights',
 primary=['O minus P annualized paired mean daily net return','normalized original matched sleeve minus peer sleeve H10 net event return'],statistics='65trading-day circular blocks5000; monthly3blocks5000; seed20261117; Holm2 approximate two-sided tests, ordinary95% intervals; PR/cost sensitivity/weeklyIC auxiliary',
 fees={'main':[.001,.002],'zero':[0,0],'stress':[.003,.008]},auxiliary='weekly E1 within-industry RankIC among excluded candidates, >=3 labeled members per industry; weight by candidate count,13calendarweek blocks; H10 labels mature byend',
 identification='same target industry budget, not same stock count or other risks; unmatchable budget retains original; fractional multi-peer control is partial identification, not causal alpha; current historical industry/style known_at not certified',
 no_search=True,no_new_training=True,forward='FORWARD_PENDING')
 cp=EP/'configs'/(RUN+'.json');assert not cp.exists();save_json(cp,cfg)
 files=[cp]+list((EP/'src').glob('*.py'))+[PRIVATE/BR/'exclusion_definitions.parquet',PRIVATE/BR/'exclusion_daily.parquet',PRIVATE/OLD/'universe_audit.parquet',PRIVATE/OLD/'score_contributions.parquet',PRIVATE/'e1_return_attribution_20261117/control_targets.parquet',OUT/'diagnostics'/BR/'accounts/O.csv']
 files += [PRIVATE/(s+'.parquet') for s in ['qfq_open','qfq_close','open','opening_trade_status_v2','daily_members','industry','labels']]+[PRIVATE/'limits/daily.parquet',PRIVATE/'suspensions/daily.parquet',PRIVATE/'weights/snapshots.parquet']
 save_json(D/'freeze.json',dict(files=record(sorted(set(files))),future_labels_read=False))
 (R/'PROTOCOL.md').write_text('# 原E1被排除持仓追查：冻结协议\n\n'+json.dumps(cfg,ensure_ascii=False,indent=2)+'\n')
 print('FROZEN',flush=True)
def prepare():
 verify();assert not (D/'selection_complete.json').exists()
 panel=pd.read_parquet(PRIVATE/OLD/'universe_audit.parquet');defs=pd.read_parquet(PRIVATE/BR/'exclusion_definitions.parquet')
 panel=panel.merge(defs[['signal_date','instrument','exclusion_reason']],on=['signal_date','instrument'],validate='one_to_one');panel=panel[panel.signal_date<=END]
 orig=pd.read_parquet(PRIVATE/'e1_return_attribution_20261117/control_targets.parquet');orig=orig[orig.control=='E1_REPLAY'];rows=[];audits=[];coverage=[];profiles=[]
 for date,o in orig.groupby('signal_date'):
  g=panel[panel.signal_date==date].copy();maps={'O':o.set_index('instrument').weight.to_dict()};p=g.set_index('instrument')
  for mode in ['P','PR']:
   w,m,peers,a=replacement(o,g,mode);maps[mode]=w;audits.extend(dict(signal_date=date,**x) for x in a)
   budget=sum(m.values());excluded=sum(x['budget'] for x in a)
   coverage.append(dict(signal_date=date,mode=mode,excluded_budget=excluded,matched_budget=budget,excluded_coverage=budget/excluded if excluded else np.nan,original_count=len(o),control_count=len(w),max_control_weight=max(w.values()),matched_original_count=len(m),peer_count=len(peers)))
   if mode=='P' and budget>0:
    maps['SELECTED']={k:v/budget for k,v in m.items()};maps['PEERS']={k:v/budget for k,v in peers.items()}
   # Available-at-signal style means: report covered weight, do not zero fill unknown.
   for side,weights in [('selected',m),('peers',peers)]:
    for feature in STYLES+['E1']:
     keys=list(weights);vals=p.reindex(keys)[feature];ws=pd.Series(weights);known=vals.notna()&np.isfinite(vals);mass=ws[known].sum()
     profiles.append(dict(signal_date=date,mode=mode,side=side,feature=feature,matched_budget=budget,known_budget=mass,value=float((vals[known]*ws[known]).sum()/mass) if mass else np.nan))
  for st,w in maps.items():
   for code,weight in w.items():rows.append(dict(signal_date=date,strategy=st,instrument=code,weight=weight))
 write(panel,'panel.parquet',True);write(pd.DataFrame(rows),'targets.parquet',True);write(pd.DataFrame(audits),'matching.csv');write(pd.DataFrame(coverage),'coverage.csv');write(pd.DataFrame(profiles),'signal_profiles.csv')
 verify();save_json(D/'selection_complete.json',dict(files=record(list(L.glob('*.parquet'))+list(D.glob('*.csv'))),future_labels_read=False))
 print('SEALED',len(coverage),'coverage rows',flush=True)
def run():
 verify();verify('selection_complete');assert not (D/'accounts_complete.json').exists()
 inp=Inputs();marks(inp,0.);t=pd.read_parquet(L/'targets.parquet');all_dates=sorted(t.signal_date.unique());events=[];receipts=[]
 for st,g in t.groupby('strategy'):
  maps={d:target_vector(inp,a) for d,a in g.groupby('signal_date')}
  if st in ['O','P','PR']:
   for cost,fees in [('main',(.001,.002)),('zero',(0.,0.)),('stress',(.003,.008))]:
    a,o,fail=run_account(inp,maps,all_dates,fees,end=END);key=st+'__'+cost
    write(a,'accounts/'+key+'.csv');write(o,'orders/'+key+'.parquet',True);receipts.append(dict(strategy=st,cost=cost,days=len(a),failures=fail))
  for date,vec in maps.items():
   ev,_=event_path(inp,inp.days.get_loc(date),vec,.001,.002);events.extend(dict(signal_date=date,strategy=st,**a) for a in ev if a['horizon']==10)
  print('executed',st,flush=True)
 write(pd.DataFrame(events),'events.csv');verify()
 save_json(D/'accounts_complete.json',dict(files=record(list((D/'accounts').glob('*.csv'))+list((L/'orders').glob('*.parquet'))+[D/'events.csv']),accounts=receipts))
def analyze():
 verify();verify('selection_complete');verify('accounts_complete');assert not (D/'analysis_complete.json').exists()
 checks=[]
 def check(name,ok):assert bool(ok),name;checks.append(dict(name=name,passed=True))
 inp=Inputs();marks(inp,0.);metrics=[];frames={};comp={};periods=[]
 for p in sorted((D/'accounts').glob('*.csv')):
  st,cost=p.stem.split('__');a=pd.read_csv(p,parse_dates=['date']).set_index('date');frames[(st,cost)]=a;r=daily_returns(a.nav);prev=a.nav.shift(fill_value=1)
  check(p.stem+' fullcalendar',len(a)==1001 and a.index[-1]==END and a.index[0]==pd.Timestamp('2021-01-11'))
  o=pd.read_parquet(L/'orders'/(p.stem+'.parquet'));c=absolute_components(inp,a,o);check(p.stem+' ledger closure',np.allclose(c.sum(axis=1),r,atol=1e-10))
  if cost=='main':comp[st]=c.mul(np.divide(np.log1p(r),r,out=np.ones(len(r)),where=abs(r)>1e-12),axis=0)
  metrics.append(dict(strategy=st,cost=cost,cagr=a.nav.iloc[-1]**(252/len(a))-1,nav=a.nav.iloc[-1],annual_oneway_turnover=((a.buy+a.sell)/(2*prev)).sum()*252/len(a),cash=a.cash_weight.mean(),holdings=a.holdings.mean()))
  for freq in ['Y','M']:
   for per,s in r.groupby(r.index.to_period(freq)):periods.append(dict(strategy=st,cost=cost,freq=freq,period=str(per),return_value=np.prod(1+s)-1))
 old=pd.read_csv(OUT/'diagnostics'/BR/'accounts/O.csv',parse_dates=['date']).set_index('date')
 check('exact original replay',old.index.equals(frames[('O','main')].index) and np.allclose(old.nav,frames[('O','main')].nav,atol=1e-12))
 write(pd.DataFrame(metrics),'metrics.csv');write(pd.DataFrame(periods),'periods.csv')
 stats=[]
 for cost in ['main','zero','stress']:
  for st in ['P','PR']:
   delta=daily_returns(frames[('O',cost)].nav)-daily_returns(frames[(st,cost)].nav)
   stats.append(dict(metric='annual_daily',comparison='O-'+st,cost=cost,primary=cost=='main' and st=='P',**daily_stat(delta)))
 ev=pd.read_csv(D/'events.csv',parse_dates=['signal_date','exit_date']);valid=ev[ev.exit_date<=END].pivot(index='signal_date',columns='strategy',values='net_return')
 t=pd.read_parquet(L/'targets.parquet');dates=pd.DatetimeIndex(sorted(t.signal_date.unique()))
 for left,right in [('SELECTED','PEERS'),('O','P'),('O','PR')]:
  stats.append(dict(metric='H10_event',comparison=left+'-'+right,cost='main',primary=left=='SELECTED',**bootstrap((valid[left]-valid[right]).reindex(dates),'M',3)))
 stats=pd.DataFrame(stats);stats['p_holm']=np.nan;ix=stats.primary;stats.loc[ix,'p_holm']=holm(stats.loc[ix,'p'].to_numpy());write(stats,'statistics.csv')
 panel=pd.read_parquet(L/'panel.parquet');allmap=panel.set_index(['signal_date','instrument']);audit=pd.read_csv(D/'matching.csv',parse_dates=['signal_date'])
 for date,targets in t.groupby('signal_date'):
  g=panel[panel.signal_date==date].set_index('instrument');o=targets[targets.strategy=='O'].set_index('instrument').weight
  base=o.groupby(g.industry.reindex(o.index).fillna('UNKNOWN')).sum()
  for st,a in targets.groupby('strategy'):
   check(str(date)+st+' weights',a.instrument.is_unique and np.isclose(a.weight.sum(),1) and a.weight.gt(0).all())
   if st in ['P','PR']:
    w=a.set_index('instrument').weight;sect=w.groupby(g.industry.reindex(w.index).fillna('UNKNOWN')).sum()
    check(str(date)+st+' industry capital',np.allclose(sect.reindex(base.index,fill_value=0),base,atol=1e-12) and sect.index.difference(base.index).empty)
  for mode,a in audit[audit.signal_date==date].groupby('mode'):
   w=targets[targets.strategy==mode].set_index('instrument').weight
   for row in a.itertuples():
    if row.status!='MATCHED':check(str(date)+mode+row.instrument+' unmatched retained',np.isclose(w[row.instrument],o[row.instrument]))
    else:check(str(date)+mode+row.instrument+' disjoint peers',set(row.peer_codes.split('|')).isdisjoint(o.index))
 # Original active ledger remains separate from replacement-account differences.
 ledger=pd.read_parquet(PRIVATE/BR/'exclusion_daily.parquet');ledger=ledger[ledger.clock=='monthly_decision'].copy()
 ledger['excluded']=~ledger.exclusion_reason.isin(['IN_C','__FEES__','__CASH__'])
 excluded=ledger[ledger.excluded].copy();check('full original wealth closure',abs(ledger.wealth_contribution.sum()-42.631274)<1e-5)
 write(excluded,'excluded_daily.parquet',True)
 for keys,name in [(['exclusion_reason'],'reasons'),(['instrument','industry','exclusion_reason'],'stocks'),(['month','exclusion_reason'],'months'),(['industry','exclusion_reason'],'industries')]:
  write(excluded.groupby(keys).wealth_contribution.sum().reset_index(),'original_excluded_'+name+'.csv')
 excluded['year']=pd.to_datetime(excluded.date).dt.year
 write(excluded.groupby('year').wealth_contribution.sum().reset_index(),'original_excluded_years.csv')
 # Decision-time status budget plus contribution split; never infer forecastability from winners.
 d=audit[audit['mode']=='P'][['signal_date','instrument','status']];mapped=excluded.merge(d,on=['signal_date','instrument'],how='left',validate='many_to_one');mapped.status=mapped.status.fillna('NOT_CURRENT_TARGET_LEGACY')
 write(mapped.groupby('status').wealth_contribution.sum().reset_index(),'original_excluded_by_matching.csv')
 outstock=[];outperiod=[]
 for st in ['P','PR']:
  delta=comp['O'].subtract(comp[st],fill_value=0);lg=delta.to_numpy().sum();gap=100*(frames[('O','main')].nav.iloc[-1]-frames[(st,'main')].nav.iloc[-1]);scale=gap/lg if abs(lg)>1e-12 else 100*frames[(st,'main')].nav.iloc[-1]
  check(st+' replacement log closure',abs(lg-np.log(frames[('O','main')].nav.iloc[-1]/frames[(st,'main')].nav.iloc[-1]))<1e-10)
  for code,value in delta.sum().items():outstock.append(dict(comparison='O-'+st,instrument=code,wealth_contribution=value*scale))
  for freq in ['Y','M']:
   for per,g in delta.groupby(delta.index.to_period(freq)):outperiod.append(dict(comparison='O-'+st,freq=freq,period=str(per),wealth_contribution=g.to_numpy().sum()*scale))
 write(pd.DataFrame(outstock),'replacement_stocks.csv');write(pd.DataFrame(outperiod),'replacement_periods.csv')
 # Weekly ranking in excluded groups; >=3 contemporaneous labelled candidates, never require10.
 labels=pd.read_parquet(PRIVATE/'labels.parquet')[['signal_date','instrument','h10','h10_mature']]
 data=panel.merge(labels,on=['signal_date','instrument'],validate='one_to_one');rows=[]
 for date,g in data.groupby('signal_date'):
  g=g[(g.exclusion_reason!='IN_C')&g.industry.ne('UNKNOWN')&g.h10.notna()&(g.h10_mature<=END)]
  values=[];counts=[]
  for ind,a in g.groupby('industry'):
   if len(a)<3:continue
   ic=rankcorr(a.E1,a.h10)
   if np.isfinite(ic):values.append(ic);counts.append(len(a))
  rows.append(dict(signal_date=date,rank_ic=np.average(values,weights=counts) if counts else np.nan,n=int(sum(counts)),groups=len(counts)))
 ic=pd.DataFrame(rows);write(ic,'excluded_rank_ic.csv');save_json(D/'excluded_rank_statistics.json',bootstrap(ic.set_index('signal_date').rank_ic,'W-FRI',13))
 save_json(D/'validation.json',dict(status='PASS',count=len(checks),checks=checks))
 verify();verify('selection_complete');verify('accounts_complete')
 save_json(D/'analysis_complete.json',dict(files=record(list(D.glob('*.csv'))+[D/'excluded_rank_statistics.json',D/'validation.json',L/'excluded_daily.parquet']),status='HISTORICAL_PARTIAL_IDENTIFICATION',forward='FORWARD_PENDING'))
 print(pd.DataFrame(metrics).query("cost=='main'").to_string(index=False));print(stats.to_string(index=False),flush=True)
if __name__=='__main__':globals()[sys.argv[1]]()
