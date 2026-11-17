"""Acquire historical daily_basic snapshots with immutable raw receipts; never PIT certify."""
from datetime import datetime,timezone
import json,time,sys
import numpy as np
import pandas as pd
import requests
from dotenv import dotenv_values
from common import EP,PRIVATE,OUT,sha,save_json
from evaluate_ranking import predictions
ROOT=PRIVATE/'style_caps_20261117'
FIELDS='ts_code,trade_date,close,total_share,float_share,free_share,total_mv,circ_mv'

def main(probe=False):
 ROOT.mkdir(parents=True,exist_ok=True)
 p,_=predictions('expanding');dates=sorted(p.signal_date.unique())
 days=pd.read_parquet(PRIVATE/'close.parquet').index
 plan=pd.DataFrame([dict(signal_date=d,source_date=days[days.get_loc(d)-1]) for d in dates])
 token=dotenv_values(EP.parents[4]/'topics/01_askhare_qlib/.env').get('TUSHARE_TOKEN')
 assert token,'No configured token'
 session=requests.Session();session.trust_env=False
 records=[];frames=[]
 for i,row in enumerate(plan.itertuples()):
  d=row.source_date.strftime('%Y%m%d');target=ROOT/(d+'.json');receipt=ROOT/(d+'.receipt.json')
  params=dict(trade_date=d)
  if target.exists() and receipt.exists():
   rec=json.loads(receipt.read_text());assert sha(target)==rec['sha256'];raw=json.loads(target.read_text())
  else:
   for attempt in range(3):
    try:
     response=session.post('https://api.tushare.pro',json=dict(api_name='daily_basic',token=token,params=params,fields=FIELDS),timeout=(10,40))
     response.raise_for_status();raw=response.json()
     if raw.get('code')!=0:raise RuntimeError('daily_basic provider code '+str(raw.get('code')))
     break
    except Exception as exc:
     if attempt==2:raise RuntimeError(type(exc).__name__+' acquiring '+d) from None
     time.sleep(2*(attempt+1))
   target.write_bytes(response.content)
   rec=dict(provider='Tushare',api='daily_basic',params=params,fields=FIELDS,path=str(target),sha256=sha(target),observed_at=datetime.now(timezone.utc).isoformat(),known_at=None,first_vintage_certified=False)
   save_json(receipt,rec);time.sleep(.35)
  data=raw['data'];f=pd.DataFrame(data['items'],columns=data['fields'])
  assert len(f)<6000,'Potential API truncation'
  assert not f.duplicated(['ts_code','trade_date']).any()
  if len(f):assert f.trade_date.astype(str).eq(d).all()
  records.append(rec|dict(rows=len(f)));f['signal_date']=row.signal_date;frames.append(f)
  if i%20==0:print('daily_basic',i+1,len(plan),'rows',len(f),flush=True)
  if probe:break
 if probe:return
 f=pd.concat(frames,ignore_index=True)
 f['instrument']=f.ts_code.str[-2:]+f.ts_code.str[:6]
 f['source_date']=pd.to_datetime(f.trade_date)
 f=f.merge(p[['signal_date','instrument']].drop_duplicates(),on=['signal_date','instrument'],validate='many_to_one')
 f.to_parquet(ROOT/'signal_caps.parquet',index=False)
 save_json(OUT/'data_audit/style_caps_20261117.json',dict(receipts=records,normalized_path=str(ROOT/'signal_caps.parquet'),normalized_sha256=sha(ROOT/'signal_caps.parquet'),rows=len(f),signal_dates=len(plan),quality='Historical-proxy, previous-market-session snapshot; no first vintage known_at',units='close yuan; shares 10000 shares; market values 10000 yuan',doc='https://tushare.pro/document/2?doc_id=32'))
 print('cap panel',f.shape,flush=True)
if __name__=='__main__':main('--probe' in sys.argv)
