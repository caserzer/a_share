"""Acquire historical weights using existing permissions, resumable hashed receipts."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,time
import pandas as pd
import requests
from dotenv import dotenv_values
EP=Path(__file__).resolve().parents[1]; REPO=EP.parents[4]
def main():
 root=EP/'private/weights';root.mkdir(parents=True,exist_ok=True)
 token=dotenv_values(REPO/'topics/01_askhare_qlib/.env').get('TUSHARE_TOKEN')
 session=requests.Session();receipts=[];frames=[]
 for month in pd.period_range('2016-12','2026-10',freq='M'):
  params=dict(index_code='000300.SH',start_date=month.start_time.strftime('%Y%m%d'),end_date=month.end_time.strftime('%Y%m%d'))
  p=root/(str(month)+'.json'); rp=p.with_suffix('.receipt.json')
  if p.exists() and rp.exists():
   receipt=json.loads(rp.read_text());assert hashlib.sha256(p.read_bytes()).hexdigest()==receipt['sha256'];d=json.loads(p.read_text())
  else:
   r=session.post('https://api.tushare.pro',json=dict(api_name='index_weight',params=params,token=token,fields=''),timeout=(10,40));r.raise_for_status();d=r.json()
   if d.get('code')!=0:raise RuntimeError('Provider rejected index_weight: '+str(d.get('code')))
   p.write_bytes(r.content);receipt=dict(params=params,sha256=hashlib.sha256(p.read_bytes()).hexdigest(),observed_at=datetime.now(timezone.utc).isoformat(),path=str(p),provider='Tushare',publication_time_attested=False)
   rp.write_text(json.dumps(receipt,indent=2));time.sleep(.4)
  b=d['data'];f=pd.DataFrame(b['items'],columns=b['fields'])
  if len(f)>=5000:raise RuntimeError('Possible truncation: '+str(month))
  receipt['rows']=len(f);receipts.append(receipt);frames.append(f)
  print(month,len(f),flush=True)
 f=pd.concat(frames,ignore_index=True).drop_duplicates(); f.to_parquet(root/'snapshots.parquet',index=False)
 (EP/'outputs/data_audit/weight_acquisition.json').write_text(json.dumps(dict(rows=len(f),snapshots=f.trade_date.nunique(),receipts=receipts),indent=2)+'\n')
if __name__=='__main__':main()
