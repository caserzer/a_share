"""Complete monthly suspension partitions, recursively split before accepting row limits."""
from pathlib import Path
from datetime import datetime,timezone
import json,time
import pandas as pd,requests
from dotenv import dotenv_values
from common import *

def main():
 root=PRIVATE/'suspensions';root.mkdir(exist_ok=True);session=requests.Session();token=dotenv_values(EP.parents[4]/'topics/01_askhare_qlib/.env').get('TUSHARE_TOKEN');receipts=[]
 def query(start,end):
  params=dict(start_date=start.strftime('%Y%m%d'),end_date=end.strftime('%Y%m%d'));p=root/(params['start_date']+'_'+params['end_date']+'.json');rp=p.with_suffix('.receipt.json')
  if p.exists() and rp.exists():
   r=json.loads(rp.read_text());assert sha(p)==r['sha256'];d=json.loads(p.read_text())
  else:
   response=session.post('https://api.tushare.pro',json=dict(api_name='suspend_d',params=params,token=token,fields=''),timeout=(10,40));response.raise_for_status();d=response.json()
   if d.get('code')!=0:raise RuntimeError('suspend_d rejected: '+str(d.get('code')))
   p.write_bytes(response.content);r=dict(params=params,sha256=sha(p),observed_at=datetime.now(timezone.utc).isoformat());save_json(rp,r);time.sleep(.4)
  body=d['data'];f=pd.DataFrame(body['items'],columns=body['fields']);r['rows']=len(f);receipts.append(r)
  if len(f)>=5000:
   if start==end:raise RuntimeError('Daily partition truncated')
   mid=start+(end-start)//2;mid=mid.normalize();return pd.concat([query(start,mid),query(mid+pd.Timedelta(days=1),end)])
  return f
 frames=[]
 for month in pd.period_range('2017-01','2026-10',freq='M'):
  f=query(month.start_time,min(month.end_time.normalize(),pd.Timestamp('2026-10-21')));frames.append(f);print('suspensions',month,len(f),flush=True)
 f=pd.concat(frames,ignore_index=True).drop_duplicates();f.to_parquet(root/'daily.parquet',index=False)
 save_json(OUT/'data_audit/suspension_acquisition.json',dict(rows=len(f),start='2017-01-01',end='2026-10-21',complete_partition_query=True,sha256=sha(root/'daily.parquet'),receipts=receipts,documentation='https://tushare.pro/document/2?doc_id=214',quality='retrospective vendor proxy'))
if __name__=='__main__':main()
