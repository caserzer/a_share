"""Cross-source values; PDF occurrences remain candidates until table review."""
import json,hashlib,re
from pathlib import Path
import pandas as pd
from cnequity_fundamental_review import ROOT,OUT,DATA,sample,dump
old=ROOT/'data/cnequity_probe_20261114/adapters/financials'
items=[]
for p in old.glob('*_parsed.json'):
 for x in json.loads(p.read_text()):items.append(dict(x,report=p.name.replace('_parsed.json','')))
f=pd.read_parquet(ROOT/'data/financial_archive_all_market.parquet');f=f[f.end_date.eq('2026-06-30')]
mapping={'revenue':('income_vip','total_revenue'),'net_profit':('income_vip','n_income_attr_p'),'operating_cost':('income_vip','oper_cost'),'net_cash_operate':('cashflow_vip','n_cashflow_act'),'capex':('cashflow_vip','c_pay_acq_const_fiolta'),'net_profit_deducted':('fina_indicator_vip','profit_dedt')}
comp=[];candidates=[]
for x in items:
 if x['item_code'] in mapping:
  api,field=mapping[x['item_code']];g=f[(f.ts_code==x['symbol'])&(f.api==api)];v=sorted(set(float(z) for z in g[field].dropna()));status='missing' if not v else ('match' if all(abs(z-x['item_value'])<=.02 for z in v) else 'difference_or_archive_conflict')
  comp.append(dict(**x,local_field=field,local_values=v,status=status,local_dates=sorted(set(str(d.date()) for d in g.ann_date.dropna())),local_rows=len(g)))
for s in sample:
 sym=s['symbol'];p=DATA/sym/'pages.json'
 if not p.exists():continue
 pages=json.loads(p.read_text())
 targets=[x for x in items if x['symbol']==sym and x['item_code'] in ['revenue','net_profit','total_assets','total_liabilities','total_equity','net_cash_operate','capex'] and x['report']!='RPT_LICO_FN_CPD']
 for x in targets:
  hits=[]
  for multiplier in [1,1000,10000,1000000]:
   v=x['item_value']/multiplier;formats={f'{v:,.2f}',f'{v:,.0f}' if abs(v-round(v))<1e-6 else f'{v:,.2f}'}
   for pg in pages:
    for val in formats:
     at=pg['text'].find(val)
     if at>=0:hits.append(dict(page=pg['page'],unit_multiplier=multiplier,number=val,context=pg['text'][max(0,at-100):at+150]))
  candidates.append(dict(**x,hits=hits[:20],state='text_occurrence_only_not_yet_verified'))
dump(OUT/'local_crosscheck.json',comp);dump(OUT/'pdf_candidates.json',candidates)
print('local comparisons',len(comp),pd.Series([x['status'] for x in comp]).value_counts().to_dict())
print('pdf candidates',len(candidates),'found',sum(bool(x['hits']) for x in candidates))
for s in sample:
 p=DATA/s['symbol']/'parsed_original.json'
 if p.exists():
  raw=json.loads(p.read_text());pairs=[]
  for x in raw:
   em=[y for y in items if all(x[k]==y[k] for k in ['symbol','statement_type','item_code'])]
   for y in em:pairs.append(dict(**x,report=y['report'],provider_value=y['item_value'],difference=y['item_value']-x['item_value']))
  dump(DATA/s['symbol']/'parser_crosscheck.json',pairs);print(s['symbol'],'parser pairs',len(pairs),'diff',sum(abs(x['difference'])>.02 for x in pairs))
