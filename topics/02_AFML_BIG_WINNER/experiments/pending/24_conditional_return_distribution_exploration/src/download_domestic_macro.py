"""Public monthly macro responses and official source cross-check references."""
import json
from pathlib import Path
import requests
from prepare_panel import OUT
from build_margin_information import digest
CACHE=OUT/'local_cache/r33_domestic_macro'
DEST=OUT/'r33_domestic_macro'
REPORTS=['RPT_ECONOMY_PMI','RPT_ECONOMY_CURRENCY_SUPPLY','RPT_ECONOMY_CPI','RPT_ECONOMY_PPI']
SOURCES={
 'pmi2020':'https://www.stats.gov.cn/xxgk/sjfb/zxfb2020/202012/t20201231_1811956.html',
 'pmi2025':'https://www.stats.gov.cn/sj/zxfb/202512/t20251231_1962218.html',
 'cpi2025':'https://www.stats.gov.cn/sj/zxfb/202601/t20260109_1962273.html',
 'ppi2025':'https://www.stats.gov.cn/sj/zxfb/202601/t20260109_1962272.html',
 'money2020':'https://app.www.gov.cn/govdata/gov/202101/13/466933/article.html',
 'money2025':'https://www.pbc.gov.cn/en/3688247/3688978/3709137/5838983/index.html',
 'tsf2020':'https://www.ndrc.gov.cn/fggz/fgzh/gnjjjc/hbjr/202101/t20210128_1266089.html',
 'tsf2021':'https://www.ndrc.gov.cn/fggz/fgzh/gnjjjc/hbjr/202201/t20220125_1313247.html'}

def run():
    CACHE.mkdir(exist_ok=True);DEST.mkdir(exist_ok=True);receipts=[]
    for name in REPORTS:
        url='https://datacenter-web.eastmoney.com/api/data/v1/get'
        params=dict(reportName=name,columns='ALL',pageNumber=1,pageSize=2000,sortColumns='REPORT_DATE',sortTypes=-1,source='WEB',client='WEB')
        path=CACHE/f'{name}.json'
        if not path.exists():
            r=requests.get(url,params=params,timeout=30);r.raise_for_status();path.write_bytes(r.content)
        data=json.loads(path.read_text());assert data['success'] and len(data['result']['data'])==data['result']['count']
        receipts.append(dict(name=name,path=str(path),sha256=digest(path),url=url,params=params,rows=len(data['result']['data'])))
    path=CACHE/'mofcom_social_financing.json';url='https://data.mofcom.gov.cn/datamofcom/front/gnmy/shrzgmQuery'
    if not path.exists():
        r=requests.post(url,timeout=30);r.raise_for_status();path.write_bytes(r.content)
    rows=json.loads(path.read_text());assert isinstance(rows,list) and len(rows)>100
    receipts.append(dict(name='tsf',path=str(path),sha256=digest(path),url=url,method='POST read-only query',rows=len(rows)))
    official=[]
    for name,url in SOURCES.items():
        path=CACHE/f'{name}.html'
        try:
            if not path.exists():
                r=requests.get(url,timeout=25);r.raise_for_status();path.write_bytes(r.content)
            official.append(dict(name=name,url=url,path=str(path),sha256=digest(path),status='downloaded'))
        except requests.RequestException as e:official.append(dict(name=name,url=url,status='web_search_verified_download_failed',error=str(e)))
    (DEST/'source_manifest.json').write_text(json.dumps(dict(series=receipts,official=official),indent=2)+'\n')
    print(json.dumps(dict(series=len(receipts),official=official),indent=2),flush=True)

if __name__=='__main__':run()
