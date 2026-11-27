"""Fetch 2025-03 to 2026-10 baskets in sub-limit date batches for both exchanges."""
from fetch import *
DEST=OUT/'segment'
DEST.mkdir(exist_ok=True)
def main():
    days=pd.read_parquet(next(REG.parent.glob('36_*/private/market.parquet')),columns=[]).index
    days=days[(days>='2025-02-01')&(days<='2026-10-12')]
    t=dotenv_values(ROOT/'topics/01_askhare_qlib/.env')['TUSHARE_TOKEN']
    http=requests.Session();http.trust_env=False
    tables={};receipts=[]
    def get(api,params):
        for retry in range(4):
            try:
                r=http.post('https://api.tushare.pro',json=dict(api_name=api,token=t,params=params),timeout=(8,40))
                r.raise_for_status();x=r.json();break
            except (requests.RequestException,ValueError):
                if retry==3:raise
                time.sleep(retry+1)
        p=x.get('data') or {};items=p.get('items') or []
        receipts.append(dict(api=api,params=params,status=x.get('code'),message=str(x.get('msg') or '').replace(t,'[redacted]'),observed_at=datetime.now(timezone.utc).isoformat(),rows=len(items),fields=p.get('fields'),sha256=hashlib.sha256(r.content).hexdigest()))
        if items:tables.setdefault(api,[]).append(pd.DataFrame(items,columns=p['fields']))
    for fund,market in FUNDS.items():
        get('etf_share_size',dict(ts_code=fund,start_date='20250201',end_date='20261012'))
        for i in range(0,len(days),9):
            get('etf_'+market+'_cons',dict(ts_code=fund,start_date=days[i].strftime('%Y%m%d'),end_date=days[min(i+8,len(days)-1)].strftime('%Y%m%d')))
    for start in pd.date_range('2024-12-01','2026-10-01',freq='MS'):
        get('index_weight',dict(index_code='000300.SH',start_date=start.strftime('%Y%m%d'),end_date=(start+pd.offsets.MonthEnd(0)).strftime('%Y%m%d')))
    for api,parts in tables.items(): pd.concat(parts,ignore_index=True).drop_duplicates().to_parquet(DEST/(api+'.parquet'),index=False)
    (DEST/'receipts.json').write_text(json.dumps(receipts,ensure_ascii=False,indent=2)+'\n')
    print(pd.DataFrame(receipts).groupby(['api','status']).rows.agg(['size','sum']))
if __name__=='__main__':main()
