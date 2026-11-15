"""Bounded, isolated 10-stock source probe; no research panel mutations."""
import sys,json,time,hashlib,subprocess,concurrent.futures
from pathlib import Path
from datetime import date,datetime,timezone
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs/cnequity_probe_20261114'
DATA=ROOT/'data/cnequity_probe_20261114/adapters'

def worker(dataset,symbol):
 import httpx
 from cnequity.adapters.sina.bars import fetch_daily_bars_sina
 from cnequity.adapters.sina.adj_factors import fetch_adj_factor_series
 from cnequity.adapters.eastmoney.shareholders import fetch_share_structure
 from cnequity.adapters.eastmoney.em_auth import EastMoneyClient
 dest=DATA/dataset/symbol;dest.mkdir(parents=True,exist_ok=True)
 receipt=dict(dataset=dataset,symbol=symbol,started_at=datetime.now(timezone.utc).isoformat(),scope='adapter probe, not pipeline acceptance')
 begin=time.monotonic();raw=[]
 def hook(response):
  response.read();i=len(raw);p=dest/f'http_{i}.bin';p.write_bytes(response.content)
  raw.append(dict(url=str(response.request.url),status=response.status_code,path=str(p.relative_to(ROOT)),sha256=hashlib.sha256(response.content).hexdigest()))
 try:
  if dataset=='share_structure':
   c=EastMoneyClient(timeout_sec=12);c._client.event_hooks['response']=[hook]
   try:f=fetch_share_structure(date(2020,1,1),date(2026,11,13),symbols=[symbol],client=c)
   finally:c.close()
  else:
   with httpx.Client(timeout=12,event_hooks={'response':[hook]}) as c:
    f=fetch_daily_bars_sina(symbol,start=date(2026,9,1),end=date(2026,11,13),datalen=100,client=c) if dataset=='daily_bars_sina' else fetch_adj_factor_series(symbol,'hfq',client=c)
  p=dest/'response.parquet';f.write_parquet(p)
  receipt.update(status='nonempty' if f.height else 'empty',rows=f.height,columns=f.columns,sha256=hashlib.sha256(p.read_bytes()).hexdigest(),data_path=str(p.relative_to(ROOT)))
  for col in ['trade_date','effective_date','change_date','announce_date']:
   if col in f.columns:receipt[col+'_min']=str(f[col].min());receipt[col+'_max']=str(f[col].max())
  if 'symbol' in f.columns:receipt['returned_symbols']=f['symbol'].unique().to_list()
  if dataset=='daily_bars_sina' and f.height:
   receipt['duplicate_symbol_dates']=f.height-f.unique(subset=['symbol','trade_date']).height
   receipt['invalid_ohlc']=f.filter((__import__('polars').col('low')>__import__('polars').col('high'))|(__import__('polars').col('close')<=0)).height
 except Exception as e:receipt.update(status='error',error_type=type(e).__name__,error=str(e))
 receipt.update(elapsed_seconds=round(time.monotonic()-begin,3),raw=raw)
 (dest/'receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2))
 print(json.dumps(receipt,ensure_ascii=False))

def main():
 sample=json.loads((OUT/'sample.json').read_text())['sample']
 jobs=[(d,r['symbol']) for r in sample for d in ['daily_bars_sina','hfq_factors_sina','share_structure']]
 (OUT/'protocol.json').write_text(json.dumps(dict(datasets=['daily_bars_sina','hfq_factors_sina','share_structure'],bars_window=['2026-09-01','2026-11-13'],shares_window=['2020-01-01','2026-11-13'],factor_window='source available full series; inspect dates before use',worker_timeout_seconds=65,workers=2,mock=False,scope='10 fixed random stocks; no all-market acquisition; no financial statement all-market endpoint'),indent=2))
 def run(job):
  d,s=job
  try:
   p=subprocess.run([sys.executable,__file__,d,s],capture_output=True,text=True,timeout=65)
   (OUT/f'{s}_{d}.log').write_text(p.stdout+p.stderr)
   rp=DATA/d/s/'receipt.json'
   r=json.loads(rp.read_text()) if rp.exists() else dict(dataset=d,symbol=s,status='worker_error',returncode=p.returncode)
  except subprocess.TimeoutExpired as e:
   r=dict(dataset=d,symbol=s,status='timeout',timeout_seconds=65)
   (OUT/f'{s}_{d}.log').write_text(str(e))
  print(s,d,r['status'],r.get('rows'),flush=True);return r
 with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(run,jobs))
 (OUT/'results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2))
if __name__=='__main__':
 if len(sys.argv)==3:worker(*sys.argv[1:])
 else:main()
