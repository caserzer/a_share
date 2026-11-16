"""Read-only source probes. Never persist credentials or request bodies."""
from pathlib import Path
import json
from datetime import datetime, timezone
import requests
from dotenv import dotenv_values
EP=Path(__file__).resolve().parents[1]
REPO=EP.parents[4]

def main():
    token=dotenv_values(REPO/'topics/01_askhare_qlib/.env').get('TUSHARE_TOKEN')
    result={'observed_at':datetime.now(timezone.utc).isoformat(),'token_available':bool(token),'probes':[]}
    for api,params in [('suspend_d',dict(ts_code='600000.SH',start_date='20210101',end_date='20261021'))]:
        record={'api':api,'params':params}
        try:
            r=requests.post('https://api.tushare.pro',json={'api_name':api,'token':token,'params':params,'fields':''},timeout=(10,30))
            d=r.json()
            record.update(http_status=r.status_code,provider_code=d.get('code'),message=d.get('msg'),rows=len((d.get('data') or {}).get('items',[])))
            if d.get('code')==0:
                dest=EP/'private/source_probe';dest.mkdir(parents=True,exist_ok=True)
                (dest/(api+'.json')).write_text(json.dumps(d,ensure_ascii=False))
        except Exception as e:
            record.update(error_type=type(e).__name__)
        result['probes'].append(record)
    (EP/'outputs/data_audit/suspension_probe.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False))
if __name__=='__main__':main()
