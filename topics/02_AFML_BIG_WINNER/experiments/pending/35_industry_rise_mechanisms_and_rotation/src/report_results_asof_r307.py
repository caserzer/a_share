"""Read-only reaggregation of archived experiments, not new model research."""
from common import *
import pandas as pd,re
OUT=ROOT/'reports/results_asof_r307_20261114'
SOURCES={};ROWS=[];MODEL=[]
def readcsv(n,file):
 p=ROOT/f'outputs/r{n}/{file}';SOURCES[str(p.relative_to(ROOT))]=sha(p);return pd.read_csv(p)
def aggregate(d,keys,value,label,better,source):
 d=d.copy();d['candidate']=d['method'].astype(str)+'/'+d['variant'].astype(str)
 for ident,g in d.groupby(keys,dropna=False):
  ident=ident if isinstance(ident,tuple) else (ident,);meta=dict(zip(keys,ident));candidates=sorted(g.candidate.unique());assert not g.duplicated(['date','candidate']).any(),(source,meta)
  w=g.pivot(index='date',columns='candidate',values=value).reindex(columns=candidates);w=w.dropna();n=len(w)
  scores=w.mean() if n else pd.Series(dtype=float);ordered=scores.sort_values(ascending=better=='min',kind='stable');best=ordered.index[0] if n else None
  rec=dict(source=source,metric=label,better=better,**meta,candidate_count=len(candidates),common_dates=n,start=str(w.index.min()) if n else None,end=str(w.index.max()) if n else None,best=best,best_value=float(ordered.iloc[0]) if n else None,median=float(scores.median()) if n else None,worst=float(ordered.iloc[-1]) if n else None,model_scores=scores.to_dict())
  ROWS.append(rec)
  for c,v in scores.items():MODEL.append(dict(source=source,metric=label,**meta,candidate=c,value=v,dates=n))
def run():
 OUT.mkdir(exist_ok=True)
 for n in [196,199,200,201]:
  d=readcsv(n,'date_metrics.csv');keys=['family','era','level','cohort','task','horizon','objective']
  for task,g in d.groupby('task'):
   if task in ['return','catchup']:aggregate(g,keys,'utility','RankIC','max',f'r{n}')
   else:g=g.copy();g['brier']=-g.utility;aggregate(g,keys,'brier','Brier','min',f'r{n}')
  if 'negative_mse' in d:
   g=d[d.task.isin(['return','catchup'])].copy();g['mse']=-g.negative_mse;aggregate(g,keys,'mse','MSE','min',f'r{n}')
 d=readcsv(197,'date_metrics.csv');aggregate(d,['family','era','level','fy_offset','population','horizon'],'mse','MSE','min','r197');aggregate(d,['family','era','level','fy_offset','population','horizon'],'ic','RankIC','max','r197')
 for n,keys,metrics in [(202,['era','level','lag','horizon'],[('ic','RankIC','max')]),(204,['era','level','cohort','horizon'],[('ic','RankIC','max'),('mse','MSE','min')]),(205,['family','era','level','target_type','horizon'],[('mse','MSE','min')])]:
  d=readcsv(n,'date_metrics.csv')
  for col,metric,direction in metrics:aggregate(d,keys,col,metric,direction,f'r{n}')
 for n in [198,276,281]:
  p=ROOT/f'outputs/r{n}/predictions.parquet';SOURCES[str(p.relative_to(ROOT))]=sha(p);d=pd.read_parquet(p);d['mse']=(d.prediction-d.target)**2;aggregate(d,['era','level','industry_code','horizon'],'mse','MSE','min',f'r{n}')
 js(OUT/'comparable_model_statistics.json',ROWS);js(OUT/'candidate_metrics.json',MODEL)
 # Daily calibration: compare variants within each exact era/level/year/calibration frequency.
 calibration=[]
 for n in [256,295]:
  d=readcsv(n,'summary.csv')
  for key,g in d.groupby(['era','level','year','method']):
   assert len(g)==3;best=g.sort_values('brier').iloc[0];calibration.append(dict(round=n,task='onset' if n==256 else 'reversal',**dict(zip(['era','level','year','calibration'],key)),best=best['variant'],best_brier=best.brier,median_brier=g.brier.median(),worst_brier=g.brier.max(),mature_min=int(g.mature.min()),unknown_max=int(g.unknown.max()),dates=int(g.dates.min())))
 js(OUT/'daily_calibration_statistics.json',calibration)
 # Portfolio comparisons: only complete model paths within same frozen identity, all available metrics retained.
 portfolios=[]
 for n in [210,211,212,214,215,216,217]:
  d=readcsv(n,'summary.csv')
  for key,g in d.groupby(['era','level','cohort','horizon','cost']):
   candidates=g[g.method.isin(['base','state','interaction'])];valid=candidates[candidates.whole_path_valid&candidates.cagr.notna()];complete=len(valid)==3
   rec=dict(round=n,**dict(zip(['era','level','cohort','horizon','cost'],key)),all_three_complete=complete,complete_models=len(valid),scheduled=int(candidates.scheduled.max()) if len(candidates) else 0)
   if complete:
    b=valid.sort_values('cagr',ascending=False).iloc[0];rec.update(best=b.method,best_cagr=b.cagr,median_cagr=valid.cagr.median(),best_drawdown=b.drawdown,median_drawdown=valid.drawdown.median(),best_turnover=b.mean_turnover,median_turnover=valid.mean_turnover.median(),best_total_return=b.total_return)
    for name in ['equal','momentum','fixed']:
     q=g[g.method.eq(name)&g.whole_path_valid]
     if len(q)==1:rec[name+'_cagr']=float(q.cagr.iloc[0]);rec[name+'_drawdown']=float(q.drawdown.iloc[0])
   portfolios.append(rec)
 js(OUT/'portfolio_statistics.json',portfolios)
 # Complete experiment catalogue through requested cutoff; original archived results stay authoritative.
 reports={};protocols={}
 for p in (ROOT/'reports').glob('*.md'):
  m=re.match(r'r(\d+)[_\.]',p.name)
  if m and int(m[1])<=307:reports.setdefault(int(m[1]),[]).append(p)
 for p in (ROOT/'protocols').glob('r*.json'):
  m=re.fullmatch(r'r(\d+)\.json',p.name)
  if m and int(m[1])<=307:protocols[int(m[1])]=p
 dirs={int(m[1]):p for p in (ROOT/'outputs').iterdir() if p.is_dir() and (m:=re.fullmatch(r'r(\d+)',p.name)) and int(m[1])<=307}
 catalog=[]
 for n in sorted(set(dirs)|set(protocols)|set(reports)):
  p=protocols.get(n);definition=json.loads(p.read_text()) if p else {};title=next((definition[k] for k in ['question','hypothesis','objective','purpose'] if k in definition),None);rr=reports.get(n,[])
  if not title and rr:title=rr[0].read_text().splitlines()[0].lstrip('# ')
  files=sorted(dirs[n].glob('*')) if n in dirs else [];keyfiles=[x for x in files if x.is_file() and (any(t in x.name for t in ['summary','metrics','result','verification','failure','fold_ledger','comparison','audit']) or x.name=='receipt.json')]
  catalog.append(dict(round=n,title=title,protocol=str(p) if p else None,reports=[str(x) for x in rr],output_directory=str(dirs[n]) if n in dirs else None,result_files=[str(x) for x in keyfiles]))
 js(OUT/'experiment_catalog.json',catalog)
 js(OUT/'calculation_receipt.json',dict(cutoff='R307',goal_remains_paused=True,no_training=True,inputs=SOURCES,code_sha256=sha(__file__),comparison_groups=len(ROWS),candidate_metrics=len(MODEL),portfolio_groups=len(portfolios),catalog_rounds=len(catalog)))
 print(json.dumps(dict(groups=len(ROWS),candidates=len(MODEL),portfolio_groups=len(portfolios),rounds=len(catalog))))
 for x in ROWS:
  if x['source']=='r196' and x.get('cohort')=='F' and x.get('era')=='SW2021' and x.get('horizon')==20:print(json.dumps(clean(x),ensure_ascii=False))
if __name__=='__main__':run()
