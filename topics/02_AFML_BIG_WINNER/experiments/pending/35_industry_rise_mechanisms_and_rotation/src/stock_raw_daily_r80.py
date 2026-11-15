import zlib
import pandas as pd
from common import *
BASE=Path('/home/xiaolv/.cache/a_share/ep30_d2')

def decode(p):
 wire=p.read_bytes();header=wire[:21].decode();version,kind,length=header.split('\x01');assert kind=='99'
 body=zlib.decompress(wire[21:21+int(length)]).decode();parts=body.split('\x01');assert parts[:3]==['0','success','query_daily_history_k_AStock']
 return pd.DataFrame(json.loads(parts[4])['record'],columns=parts[5].split(','))

def run():
 out=ROOT/'outputs/r80';out.mkdir(exist_ok=True);gp=ROOT/'outputs/r79/missing_dates.json';ip=ROOT/'outputs/r79/intervals.json'
 d=pd.DataFrame(json.loads(gp.read_text())).drop_duplicates(['security_id','date']);d['day']=d.date.str[:10]
 instruments={}
 for x in json.loads(ip.read_text()):instruments.setdefault(x['security_id'],set()).update(x['instruments'])
 rows=[];reads={};sources=[]
 for date,g in d.groupby('day'):
  p=BASE/f'backfill_v2/acquired/daily/{date}.parquet';raw=None
  if p.exists():
   rp=Path(str(p)+'.receipt.json');r=json.loads(rp.read_text());assert sha(p)==r['parquet_sha256'];reads[str(p)]=sha(p);reads[str(rp)]=sha(rp);frames=[]
   for h in r['response_sha256']:
    src=BASE/'raw/sha256'/h[:2]/h;assert sha(src)==h;reads[str(src)]=h;frames.append(decode(src))
   raw=pd.concat(frames,ignore_index=True);saved=pd.read_parquet(p)
   pd.testing.assert_frame_equal(raw,saved,check_dtype=False)
   assert raw.date.eq(date).all();assert raw.adjustflag.eq('3').all()
   raw['instrument']=raw.code.str[:2].str.upper()+raw.code.str[3:]
   sources.append(dict(date=date,rows=len(raw),original_sha256=r['response_sha256'],observed_at=r['observed_at']))
  for x in g.to_dict('records'):
   aliases=sorted(instruments[x['security_id']]);match=[] if raw is None else raw[raw.instrument.isin(aliases)].to_dict('records')
   rows.append(dict(security_id=x['security_id'],date=date,position=x['position'],instruments=aliases,status='no_local_daily_archive' if raw is None else 'matching_raw_record' if match else 'no_record_for_observed_aliases',matches=match))
 js(out/'date_audit.json',rows);js(out/'sources.json',sources)
 summary=dict(unique_stock_dates=len(rows),status_counts=pd.Series([x['status'] for x in rows]).value_counts().to_dict(),covered_dates=len(sources),matched_trade_statuses=pd.Series([m['tradestatus'] for x in rows for m in x['matches']],dtype=str).value_counts().to_dict(),strict_PIT=False,prices_repaired=0)
 js(out/'summary.json',summary)
 for p in [gp,ip,ROOT/'protocols/r80.json',Path(__file__)]:reads[str(p)]=sha(p)
 js(out/'receipt.json',dict(reads=reads,scope='local original whole-market daily responses on available dates only'))
 print(json.dumps(clean(summary),ensure_ascii=False))
if __name__=='__main__':run()
