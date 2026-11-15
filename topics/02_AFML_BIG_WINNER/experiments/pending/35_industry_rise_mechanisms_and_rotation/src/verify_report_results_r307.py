from common import *
import pandas as pd
from statistics import fmean,median
OUT=ROOT/'reports/results_asof_r307_20261114'
def close(a,b):return a is None and b is None or a is not None and b is not None and abs(a-b)<1e-12
rows=json.loads((OUT/'comparable_model_statistics.json').read_text());cache={};checked=0
for r in rows:
 n=int(r['source'][1:])
 if n not in cache:
  p=ROOT/f'outputs/r{n}';d=pd.read_parquet(p/'predictions.parquet') if n in [198,276,281] else pd.read_csv(p/'date_metrics.csv');cache[n]=d
 d=cache[n];q=d
 for k in ['family','era','level','cohort','task','horizon','objective','fy_offset','population','lag','target_type','industry_code']:
  if k in r:q=q[q[k].eq(r[k])]
 if n in [198,276,281]:q=q.copy();q['value']=(q.prediction-q.target)**2
 elif r['metric']=='Brier':q=q.assign(value=-q.utility)
 elif r['metric']=='RankIC':q=q.assign(value=q['utility'] if 'utility' in q else q['ic'])
 else:q=q.assign(value=q['mse'] if 'mse' in q else -q['negative_mse'])
 by={}
 for x in q.itertuples():
  c=str(x.method)+'/'+str(x.variant);by.setdefault(c,{})[str(x.date)]=x.value
 common=set.intersection(*(set(k for k,v in a.items() if pd.notna(v)) for a in by.values()))
 assert len(by)==r['candidate_count'] and len(common)==r['common_dates']
 values={c:fmean(a[t] for t in common) for c,a in by.items()} if common else {}
 assert set(values)==set(r['model_scores'])
 for c,v in values.items():assert close(v,r['model_scores'][c]);checked+=1
 assert close(median(values.values()) if values else None,r['median'])
 if values:assert close((min if r['better']=='min' else max)(values.values()),r['best_value']);assert close(values[r['best']],r['best_value'])
for r in json.loads((OUT/'portfolio_statistics.json').read_text()):
 d=pd.read_csv(ROOT/f"outputs/r{r['round']}/summary.csv")
 for k in ['era','level','cohort','horizon','cost']:d=d[d[k].eq(r[k])]
 q=d[d.method.isin(['base','state','interaction'])&d.whole_path_valid&d.cagr.notna()];assert len(q)==r['complete_models']
 if r['all_three_complete']:
  assert len(q)==3;assert close(median(q.cagr),r['median_cagr']);assert close(max(q.cagr),r['best_cagr']);assert close(median(q.mean_turnover),r['median_turnover'])
catalog=json.loads((OUT/'experiment_catalog.json').read_text());assert [x['round'] for x in catalog]==list(range(1,308))
for r in catalog:
 for p in r['reports']+r['result_files']+([r['protocol']] if r['protocol'] else []):assert Path(p).is_file(),p
receipt=json.loads((OUT/'calculation_receipt.json').read_text())
for p,h in receipt['inputs'].items():assert sha(ROOT/p)==h
js(OUT/'verification.json',dict(status='PASS',comparison_groups=len(rows),independent_candidate_means=checked,portfolio_groups=1164,catalog_rounds=307,scope='Reaggregated numbers and archive index; not fresh validation of every historical model',code_sha256=sha(__file__)))
print('PASS',len(rows),checked)
