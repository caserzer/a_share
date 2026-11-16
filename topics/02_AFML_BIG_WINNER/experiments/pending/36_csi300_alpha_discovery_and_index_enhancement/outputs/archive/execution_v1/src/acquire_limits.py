from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,time
import pandas as pd
import requests
from dotenv import dotenv_values
from common import EP,PRIVATE,save_json,sha

def main():
 root=PRIVATE/'limits';root.mkdir(parents=True,exist_ok=True)
 symbols=set(pd.read_parquet(PRIVATE/'weights/snapshots.parquet').con_code)
 mp=PRIVATE/'members/weekly.parquet'
 if mp.exists():symbols.update(pd.read_parquet(mp).code.map(lambda x:x[3:]+'.'+x[:2].upper()))
 token=dotenv_values(EP.parents[4]/'topics/01_askhare_qlib/.env').get('TUSHARE_TOKEN');session=requests.Session();receipts=[];frames=[]
 for i,symbol in enumerate(sorted(symbols)):
  params=dict(ts_code=symbol,start_date='20170101',end_date='20261021');p=root/(symbol+'.json');rp=p.with_suffix('.receipt.json')
  if p.exists() and rp.exists():
   receipt=json.loads(rp.read_text());assert sha(p)==receipt['sha256'];d=json.loads(p.read_text())
  else:
   r=session.post('https://api.tushare.pro',json=dict(api_name='stk_limit',params=params,token=token,fields=''),timeout=(10,40));r.raise_for_status();d=r.json()
   if d.get('code')!=0:raise RuntimeError('Provider rejected stk_limit: '+str(d.get('code')))
   p.write_bytes(r.content);receipt=dict(params=params,sha256=sha(p),observed_at=datetime.now(timezone.utc).isoformat());save_json(rp,receipt);time.sleep(.4)
  b=d['data'];f=pd.DataFrame(b['items'],columns=b['fields'])
  if len(f)>=6000:raise RuntimeError('Potential truncation')
  receipt['rows']=len(f);receipts.append(receipt);frames.append(f)
  if i%25==0:print('limits',i,len(symbols),symbol,len(f),flush=True)
 pd.concat(frames,ignore_index=True).to_parquet(root/'daily.parquet',index=False)
 save_json(EP/'outputs/data_audit/limit_acquisition.json',dict(receipts=receipts,quality='Historical-proxy; no order-book fill guarantee'))
if __name__=='__main__':main()
