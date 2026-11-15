"""Validate saved probe outputs and compare TDX/Sina overlap."""
import json,hashlib,subprocess
import polars as pl
from cnequity.query import load
from cnequity_probe import ROOT,OUT,DATA
sample=json.loads((OUT/'sample.json').read_text())['sample'];symbols=[r['symbol'] for r in sample]
f=load('daily_bars',symbols=symbols,data_root=ROOT/'data/cnequity_probe_20261114/lake')
assert not f.filter(pl.col('source')=='mock').height
assert f.height==f.unique(['symbol','trade_date']).height
rows=[]
for s in sample:
 sym=s['symbol'];a=pl.read_parquet(DATA/'daily_bars_sina'/sym/'response.parquet');b=f.filter(pl.col('symbol')==sym);j=a.join(b,on=['symbol','trade_date'],suffix='_tdx')
 diffs={k:float((j[k]-j[k+'_tdx']).abs().max() or 0) if j.height else None for k in ['open','high','low','close','volume']}
 fac=pl.read_parquet(DATA/'hfq_factors_sina'/sym/'response.parquet')
 rows.append(dict(**s,tdx_rows=b.height,sina_rows=a.height,overlap=j.height,max_abs_difference=diffs,sina_null_amount=a['amount'].null_count(),tdx_null_amount=b['amount'].null_count(),factor_rows=fac.height,factor_columns=fac.columns,bar_min=str(a['trade_date'].min()),bar_max=str(a['trade_date'].max()),invalid_ohlc=a.filter((pl.col('low')>pl.min_horizontal('open','close'))|(pl.col('high')<pl.max_horizontal('open','close'))|(pl.col('low')<=0)|(pl.col('volume')<0)).height))
assert sum(x['invalid_ohlc'] for x in rows)==0
results=json.loads((OUT/'results.json').read_text())
for r in results:
 if 'sha256' in r:assert hashlib.sha256((ROOT/r['data_path']).read_bytes()).hexdigest()==r['sha256']
 for h in r.get('raw',[]):assert hashlib.sha256((ROOT/h['path']).read_bytes()).hexdigest()==h['sha256']
fin=json.loads((OUT/'financial_results.json').read_text())
for h in fin['http']:assert hashlib.sha256((ROOT/h['path']).read_bytes()).hexdigest()==h['sha256']
v=dict(rows=rows,tdx_total=f.height,tdx_sources=f['source'].unique().to_list(),unique_sample=len(set(symbols)),hash_checks='passed',scope='structural and cross-source agreement; not independent issuer validation or PIT certification')
(OUT/'audit.json').write_text(json.dumps(v,ensure_ascii=False,indent=2));print(json.dumps(v,ensure_ascii=False,indent=2))
