from pathlib import Path
import requests, json
from dotenv import dotenv_values
here=Path(__file__).resolve().parent
repo=next(p for p in here.parents if (p/'topics/01_askhare_qlib/.env').is_file())
token=dotenv_values(repo/'topics/01_askhare_qlib/.env').get('TUSHARE_TOKEN')
audit=[]
for code in ['000906.SH','000905.SH']:
    params=dict(index_code=code,start_date='20210601',end_date='20210630')
    row=dict(provider='Tushare',api='index_weight',params=params)
    try:
        res=requests.post('https://api.tushare.pro',json=dict(api_name='index_weight',token=token,params=params,fields=''),timeout=(5,12))
        data=res.json();rows=(data.get('data') or {}).get('items',[])
        row.update(status=res.status_code,provider_code=data.get('code'),rows=len(rows),snapshot_dates=sorted(set(r[2] for r in rows)))
    except requests.RequestException as e: row['error']=type(e).__name__
    audit.append(row)
(here/'results/source_probes.json').write_text(json.dumps(audit,indent=2))
