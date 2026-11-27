"""Fetch the early total-return index closes missing from the local EP36 vintage."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json
import requests
import pandas as pd
from dotenv import dotenv_values

here=Path(__file__).resolve().parent
repo=next(x for x in here.parents if (x/'topics/01_askhare_qlib').is_dir())
token=dotenv_values(repo/'topics/01_askhare_qlib/.env')['TUSHARE_TOKEN']
session=requests.Session()
session.trust_env=False
res=session.post('https://api.tushare.pro',json={'api_name':'index_daily','token':token,
    'params':{'ts_code':'H00300.CSI','start_date':'20170101','end_date':'20210115'},'fields':'trade_date,close'},timeout=(5,20))
res.raise_for_status()
data=res.json()
if data.get('code')!=0: raise ValueError('provider code '+str(data.get('code')))
frame=pd.DataFrame(data['data']['items'],columns=data['data']['fields']).rename(columns={'trade_date':'date'})
assert len(frame)>900 and not frame.date.duplicated().any()
out=here/'results'
frame.date=pd.to_datetime(frame.date)
frame.sort_values('date').to_csv(out/'index_history.csv',index=False)
(out/'index_receipt.json').write_text(json.dumps(dict(source='Tushare index_daily H00300.CSI',retrieved=datetime.now(timezone.utc).isoformat(),
                   start='20170101',end='20210115',rows=len(frame),response_sha256=hashlib.sha256(res.content).hexdigest()),indent=2))
print('retrieved',len(frame))

