"""Public, dated risk/size snapshot. No silent carry-forward or credential use."""
import argparse
import json
import hashlib
from datetime import datetime, timezone
import requests
import pandas as pd
import numpy as np
from prepare_panel import OUT, DATA


def fetch(stock, asof):
    date=pd.Timestamp(asof)
    symbol=stock.lower()
    folder=OUT/'local_cache/current_snapshots'/f'{stock}_{asof}'
    folder.mkdir(parents=True,exist_ok=True)
    session=requests.Session();session.trust_env=False
    receipts=[]
    def get(name,url,params):
        response=session.get(url,params=params,timeout=25);response.raise_for_status()
        payload=response.json()
        raw=response.content
        (folder/f'{name}.json').write_bytes(raw)
        receipts.append(dict(name=name,url=response.url,sha256=hashlib.sha256(raw).hexdigest(),retrieved_utc=datetime.now(timezone.utc).isoformat()))
        return payload
    url='https://proxy.finance.qq.com/ifzqgtimg/appstock/app/newfqkline/get'
    frames={}
    for key in [symbol,'sh000001']:
        data=get(key,url,{'param':f'{key},day,{date-pd.DateOffset(years=1):%Y-%m-%d},{asof},640,qfq'})['data'][key]
        rows=data.get('qfqday',data.get('day'))
        frame=pd.DataFrame([row[:6] for row in rows],columns=['date','open','close','high','low','volume'])
        frame['date']=pd.to_datetime(frame.date)
        frame['close']=pd.to_numeric(frame.close)
        frame=frame.set_index('date').sort_index()
        if frame.index.duplicated().any():raise ValueError('Duplicate daily bars')
        frames[key]=frame.loc[:date]
    calendar=frames['sh000001'].index
    if calendar.max()!=date or frames[symbol].index.max()!=date:raise ValueError('Requested session is not available; no stale substitution')
    closes=frames[symbol].close.reindex(calendar)
    returns=closes.pct_change(fill_method=None)
    if returns.tail(63).isna().any() or (closes.tail(64)<=0).any():raise ValueError('Missing/nonpositive recent prices; risk feature unavailable')
    vol=float(returns.tail(63).std()*np.sqrt(252))
    payload=get('valuation','https://datacenter-web.eastmoney.com/api/data/v1/get',dict(
        reportName='RPT_VALUEANALYSIS_DET',columns='ALL',pageSize=10,pageNumber=1,sortColumns='TRADE_DATE',sortTypes='-1',
        filter=f'(SECURITY_CODE="{stock[2:]}")(TRADE_DATE=\'{asof}\')'))
    records=(payload.get('result') or {}).get('data') or []
    valid=[r for r in records if pd.Timestamp(r['TRADE_DATE'])==date and str(r['SECURITY_CODE'])==stock[2:]]
    if len(valid)!=1:raise ValueError('Exact-date market capitalization unavailable')
    value=valid[0];cap=float(value['TOTAL_MARKET_CAP'])
    shares=float(value['TOTAL_SHARES']);close=float(value['CLOSE_PRICE'])
    if cap<=0 or abs(cap/(shares*close)-1)>.01:raise ValueError('Market cap units or consistency failed')
    if abs(closes.iloc[-1]/close-1)>.001:raise ValueError('Latest prices disagree between sources')
    old=pd.read_csv(DATA/f'raw/akshare/day/qfq/{stock}.csv',parse_dates=['date']).set_index('date').close
    overlap=pd.concat([old.pct_change(fill_method=None).rename('old'),returns.rename('public')],axis=1).dropna().tail(60)
    overlap_error=float((overlap.old-overlap.public).abs().max()) if len(overlap) else None
    # Rounding/adjustment revisions can change historical returns. Preserve the measured discrepancy.
    result=dict(instrument=stock,asof=asof,feature_available_at=max(r['retrieved_utc'] for r in receipts),
        features=dict(vol63=vol,log_cap=float(np.log(cap))),market_cap_cny=cap,
        source_price_end=str(calendar.max().date()),recent_return_observations=63,
        overlap_rows=len(overlap),max_overlap_daily_return_difference=overlap_error,
        source_status='consistent' if len(overlap)>=20 and overlap_error<.003 else 'source_change_requires_review',
        receipts=receipts,semantics='qfq daily-return volatility; total market cap CNY; public end-of-day snapshot')
    (folder/'snapshot.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--stock',required=True);p.add_argument('--asof',required=True)
    a=p.parse_args();fetch(a.stock,a.asof)
