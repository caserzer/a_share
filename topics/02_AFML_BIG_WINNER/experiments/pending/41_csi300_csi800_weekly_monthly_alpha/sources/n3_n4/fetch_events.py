"""Read-only provider queries for first and revised annual disclosures, with raw receipts."""
from pathlib import Path
from dotenv import dotenv_values
import requests, json, gzip, hashlib, time
from datetime import datetime,timezone
HERE=Path(__file__).resolve().parent
ROOT=next(p for p in HERE.parents if (p/'topics/01_askhare_qlib').is_dir())
key=dotenv_values(ROOT/'topics/01_askhare_qlib/.env').get('TUSHARE_TOKEN')
assert key
spec={'forecast_vip':'ts_code,ann_date,end_date,type,net_profit_min,net_profit_max,first_ann_date',
      'express_vip':'ts_code,ann_date,end_date,n_income,diluted_eps',
      'income_vip':'ts_code,ann_date,f_ann_date,end_date,report_type,basic_eps,n_income_attr_p,update_flag'}
dest=HERE/'raw/events'
dest.mkdir(exist_ok=True,parents=True)
session=requests.Session()
session.trust_env=False
receipts=[]
for name,fields in spec.items():
    for yr in range(2018,2026):
        for offset in range(0,24000,2000):
            p=dest/f'{name}_{yr}_{offset}.json.gz'
            params={'period':f'{yr}1231','limit':2000,'offset':offset}
            if p.exists():b=gzip.decompress(p.read_bytes())
            else:
                response=session.post('https://api.tushare.pro',json={'api_name':name,'token':key,'params':params,'fields':fields},timeout=(10,45))
                response.raise_for_status()
                b=response.content
            data=json.loads(b)
            if data.get('code')!=0:
                receipts.append(dict(api=name,year=yr,status='unavailable',provider_code=data.get('code'),msg=data.get('msg','')[:200]))
                break
            if not p.exists():p.write_bytes(gzip.compress(b,mtime=0))
            n=len(data['data']['items'])
            receipts.append(dict(file=p.name,api=name,year=yr,rows=n,sha256=hashlib.sha256(b).hexdigest(),params=params,observed_at=datetime.now(timezone.utc).isoformat()))
            if n<2000:break
            time.sleep(.25)
        print(name,yr,receipts[-1].get('status','ok'),flush=True)
        if receipts[-1].get('status')=='unavailable': break
(HERE/'results/event_source_receipts.json').write_text(json.dumps(receipts,indent=2,ensure_ascii=False))
