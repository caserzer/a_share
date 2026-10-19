"""Public SSE option activity feasibility probe; not implied volatility or net flows."""
import json
import time
import requests
from prepare_panel import OUT
from build_margin_information import digest

DEST=OUT/'r38_option_activity_probe'
CACHE=OUT/'local_cache/r38_option_activity_probe'
URL='https://query.sse.com.cn/commonQuery.do'
DATES=['20181228','20210401','20260429']


def number(value):
    return float(str(value).replace(',',''))


def run():
    DEST.mkdir(exist_ok=True);CACHE.mkdir(exist_ok=True);receipts=[]
    for date in DATES:
        params=dict(isPagination='false',sqlId='COMMON_SSE_ZQPZ_YSP_QQ_SJTJ_MRTJ_CX',tradeDate=date)
        path=CACHE/f'{date}.json'
        if not path.exists():
            time.sleep(1)
            response=requests.get(URL,params=params,headers={'Referer':'https://www.sse.com.cn/assortment/options/date/'},timeout=30)
            response.raise_for_status();payload=response.json();assert isinstance(payload.get('result'),list)
            path.write_bytes(response.content)
        payload=json.loads(path.read_text());rows=payload['result'];checks=[]
        assert rows,'Empty response is not an observed zero'
        for row in rows:
            assert row['TRADE_DATE'].replace('-','')[:8]==date
            c,p,total=[number(row[k]) for k in ('CALL_VOLUME','PUT_VOLUME','TOTAL_VOLUME')]
            oc,op,oi=[number(row[k]) for k in ('LEAVES_CALL_QTY','LEAVES_PUT_QTY','LEAVES_QTY')]
            assert c>0 and p>0 and oc>0 and op>0
            assert c+p==total and oc+op==oi
            ratio=100*p/c;assert abs(ratio-number(row['CP_RATE']))<=.011
            checks.append(dict(code=row['SECURITY_CODE'],name=row['SECURITY_ABBR'],call_volume=c,put_volume=p,
                               call_open_interest=oc,put_open_interest=op,volume_put_call=p/c,oi_put_call=op/oc))
        receipts.append(dict(date=date,path=str(path),sha256=digest(path),params=params,checks=checks))
        print(date,checks,flush=True)
    result=dict(url=URL,source_page='https://www.sse.com.cn/assortment/options/date/',receipts=receipts,
                limitation='Three dates only; sums and published ratios checked. Activity counts are neither implied volatility nor signed hedging demand. Not used in a model.')
    (DEST/'source_probe.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')


if __name__=='__main__':run()
