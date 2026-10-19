"""R29 public raw-source retrieval, cache first; no credentials."""
import json
import time
from datetime import datetime, timezone
import requests
from prepare_panel import OUT
from build_margin_information import digest

CACHE=OUT/'local_cache/r29_global_risk'
URLS={'VIX.csv':'https://cdn.cboe.com/api/global/us_indices/daily_prices/VIX_History.csv',
      'VIX3M.body':'https://cdn.cboe.com/api/global/us_indices/daily_prices/VIX3M_History.csv',
      'NASDAQ_SINA.body':'https://finance.sina.com.cn/staticdata/us/.IXIC',
      'FX_FED_HTML.body':'https://www.federalreserve.gov/releases/h10/hist/dat00_ch.htm'}
URLS.update({f'TREASURY_{year}.body':f'https://home.treasury.gov/resource-center/data-chart-center/interest-rates/pages/xml?data=daily_treasury_yield_curve&field_tdr_date_value={year}' for year in range(2016,2027)})


def download():
    CACHE.mkdir(exist_ok=True)
    for name,url in URLS.items():
        path=CACHE/name;rp=path.with_suffix('.receipt.json')
        if path.exists() and rp.exists():
            r=json.loads(rp.read_text());assert r['status']==200 and digest(path)==r['sha256']
            continue
        for attempt in range(3):
            try:
                r=requests.get(url,headers={'User-Agent':'Mozilla/5.0'},timeout=25);r.raise_for_status()
                path.write_bytes(r.content)
                rp.write_text(json.dumps(dict(url=r.url,status=r.status_code,fetched_at=datetime.now(timezone.utc).isoformat(),
                    bytes=len(r.content),sha256=digest(path)),indent=2)+'\n')
                print(name,len(r.content),flush=True);break
            except requests.RequestException:
                if attempt==2:raise RuntimeError(f'Public source unavailable: {name}') from None
                time.sleep(2*(attempt+1))


if __name__=='__main__':download()
