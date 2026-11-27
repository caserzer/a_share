"""Read-only historical vendor probes. Receipts contain fields, counts and digests only."""
from pathlib import Path
import hashlib,json
from datetime import datetime,timezone
import requests
from dotenv import dotenv_values
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[5]
queries=[
 ('N1','stk_mins',dict(ts_code='600000.SH',freq='1min',start_date='2023-01-05 09:00:00',end_date='2023-01-05 15:00:00')),
 ('N6','etf_sh_cons',dict(ts_code='510300.SH',trade_date='20250605')),
 ('N6','etf_sz_cons',dict(ts_code='159919.SZ',trade_date='20250605')),
 ('N6','fund_share',dict(ts_code='510300.SH',trade_date='20250605')),
 ('N6','fund_nav',dict(ts_code='510300.SH',end_date='20250605',start_date='20250605')),
 ]
def main():
    token=dotenv_values(ROOT/'topics/01_askhare_qlib/.env')['TUSHARE_TOKEN']
    conn=requests.Session();conn.trust_env=False
    res=[]
    for family,api,q in queries:
        r=conn.post('https://api.tushare.pro',json=dict(api_name=api,token=token,params=q),timeout=(10,30))
        r.raise_for_status();raw=r.json()
        data=raw.get('data') or {}
        res.append(dict(family=family,api=api,query=q,asof=datetime.now(timezone.utc).isoformat(),status=raw['code'],
            message=(raw.get('msg') or '').replace(token,'[redacted]'),fields=data.get('fields'),rows=len(data.get('items') or []),sha256=hashlib.sha256(r.content).hexdigest()))
    (HERE/'provider_probes.json').write_text(json.dumps(res,ensure_ascii=False,indent=2)+'\n')
if __name__=='__main__':main()
