"""Historical weekly provider snapshots; not certified first-vintage membership."""
from pathlib import Path
import sys,socket,json,hashlib,time
from datetime import datetime,timezone
import pandas as pd
EP=Path(__file__).resolve().parents[1]
sys.path.insert(0,'/home/xiaolv/.cache/a_share/ep30_d2/backfill_v2/vendor')
import baostock as bs

def main():
 root=EP/'private/members';root.mkdir(parents=True,exist_ok=True)
 release=json.loads((EP.parent/'30_pit_data_foundation_v1/outputs/pit_v5/release.json').read_text())
 days=pd.DatetimeIndex(pd.read_parquet(Path(release['path'])/'inputs/inputs/baseline/normalized/calendar.parquet').date)
 # Friday is the scheduled signal except holidays, when the last actual session is used.
 signals=pd.Series(days,index=days).groupby(days.to_period('W-FRI')).max()
 socket.setdefaulttimeout(20);r=bs.login();assert r.error_code=='0'
 frames=[];receipts=[]
 try:
  for i,day in enumerate(signals):
   date=day.strftime('%Y-%m-%d');p=root/(date+'.csv');rp=p.with_suffix('.receipt.json')
   if p.exists() and rp.exists():
    receipt=json.loads(rp.read_text());assert hashlib.sha256(p.read_bytes()).hexdigest()==receipt['sha256'];f=pd.read_csv(p)
   else:
    result=bs.query_hs300_stocks(date=date)
    if result.error_code!='0':raise RuntimeError('membership provider code '+result.error_code)
    f=result.get_data(); f.to_csv(p,index=False)
    receipt=dict(query_date=date,rows=len(f),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),observed_at=datetime.now(timezone.utc).isoformat(),publication_time_attested=False)
    rp.write_text(json.dumps(receipt,indent=2));time.sleep(.3)
   f['signal_date']=day;frames.append(f);receipts.append(receipt)
   if i%25==0:print('membership',i,len(signals),date,len(f),flush=True)
 finally:bs.logout()
 pd.concat(frames,ignore_index=True).to_parquet(root/'weekly.parquet',index=False)
 (EP/'outputs/data_audit/membership_acquisition.json').write_text(json.dumps(dict(receipts=receipts,quality='Historical-proxy; weekly retrospective provider snapshot'),indent=2)+'\n')
if __name__=='__main__':main()
