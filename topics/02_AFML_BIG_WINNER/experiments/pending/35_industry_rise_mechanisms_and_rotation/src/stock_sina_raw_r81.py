import pandas as pd
from py_mini_racer import py_mini_racer
from akshare.stock.stock_zh_a_sina import hk_js_decode
from common import *
BASE=Path('/home/xiaolv/.cache/a_share/ep30_d2/backfill_v2/acquired/sina')
def run():
 out=ROOT/'outputs/r81';out.mkdir(exist_ok=True)
 gp=ROOT/'outputs/r79/missing_dates.json';ip=ROOT/'outputs/r79/intervals.json'
 d=pd.DataFrame(json.loads(gp.read_text())).drop_duplicates(['security_id','date']);aliases={}
 for x in json.loads(ip.read_text()):aliases.setdefault(x['security_id'],set()).update(x['instruments'])
 engine=py_mini_racer.MiniRacer();engine.eval(hk_js_decode);sources=[];available={};reads={};missing=[]
 for alias in sorted(set.union(*aliases.values())):
  p=BASE/f'{alias}.parquet'
  if not p.exists():missing.append(str(p));continue
  rp=Path(str(p)+'.receipt.json');r=json.loads(rp.read_text());src=Path(r['archive_path']);assert sha(src)==r['sha256'] and sha(p)==r['parquet_sha256']
  for q in [p,rp,src]:reads[str(q)]=sha(q)
  text=src.read_text(encoding='utf-8-sig');encoded=text.split('=',1)[1].split(';',1)[0].strip().strip('"');raw=pd.DataFrame(engine.call('d',encoded));assert not raw.empty
  raw['date']=pd.to_datetime(raw.date,utc=True).dt.tz_convert('Asia/Shanghai').dt.tz_localize(None).dt.normalize();assert not raw.date.duplicated().any()
  saved=pd.read_parquet(p);window=raw[raw.date.between('2017-01-03','2026-10-21')].sort_values('date').reset_index(drop=True)
  fields=[c for c in ['date','open','high','low','close','volume','amount'] if c in raw]
  for c in fields[1:]:window[c]=pd.to_numeric(window[c],errors='coerce')
  pd.testing.assert_frame_equal(window[fields],saved[fields],check_dtype=False)
  available[alias]=raw.set_index('date');sources.append(dict(instrument=alias,archive_path=str(src),sha256=r['sha256'],full_decoded_rows=len(raw),saved_rows=len(saved),first_date=raw.date.min(),last_date=raw.date.max(),source_observed_at=r['source_observed_at']))
 rows=[]
 for x in d.to_dict('records'):
  aa=sorted(aliases[x['security_id']]);present=[a for a in aa if a in available];matches=[]
  for a in present:
   f=available[a];dt=pd.Timestamp(x['date'])
   if dt in f.index:matches.append(dict(instrument=a,**f.loc[dt].to_dict()))
  rows.append(dict(security_id=x['security_id'],date=x['date'][:10],position=x['position'],instruments=aa,available_instruments=present,status='no_local_security_archive' if not present else 'matching_raw_record' if matches else 'date_absent_from_available_archives',matches=matches))
 js(out/'date_audit.json',rows);js(out/'sources.json',sources)
 summary=dict(unique_stock_dates=len(rows),affected_securities=d.security_id.nunique(),available_archives=len(sources),missing_archives=len(missing),status_counts=pd.Series([x['status'] for x in rows]).value_counts().to_dict(),decoded_original_rows=sum(x['full_decoded_rows'] for x in sources),strict_PIT=False,prices_repaired=0)
 js(out/'summary.json',summary)
 for p in [gp,ip,ROOT/'protocols/r81.json',Path(__file__)]:reads[str(p)]=sha(p)
 js(out/'receipt.json',dict(reads=reads,missing_archives=missing,decoder_sha256=hashlib.sha256(hk_js_decode.encode()).hexdigest()))
 print(json.dumps(clean(summary),ensure_ascii=False))
if __name__=='__main__':run()
