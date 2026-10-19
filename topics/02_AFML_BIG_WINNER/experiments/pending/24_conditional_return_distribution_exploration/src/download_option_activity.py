"""Fixed ETF option activity snapshots two trading sessions before each origin."""
import json
import time
import pandas as pd
import requests
from prepare_panel import EP,OUT,DATA
from build_joint_information import SOURCE
from build_margin_information import digest
from probe_domestic_option_activity import URL,number

DEST=OUT/'r38_option_activity'
CACHE=OUT/'local_cache/r38_option_activity'
CALENDAR=DATA/'qlib/cn_data_pit_largecap/calendars/day.txt'
MONTHS=OUT/'local_cache/improvement_panel.parquet'
LAUNCH_300=pd.Timestamp('2019-12-23')


def dates_and_panel():
    panel=pd.read_parquet(SOURCE)
    dates=sorted(pd.read_parquet(MONTHS,columns=['date']).date.unique())
    first=dates.index(panel.date.min());assert first>=3
    origins=pd.DatetimeIndex(dates[first-3:])
    periods=origins.to_period('M').astype('int64')
    assert (periods[1:]-periods[:-1]==1).all()
    calendar=pd.DatetimeIndex(pd.read_csv(CALENDAR,header=None)[0])
    assert not calendar.duplicated().any() and calendar.is_monotonic_increasing
    snapshots={date:calendar[calendar.get_loc(date)-2] for date in origins}
    assert set(panel.date.unique())==set(origins[3:])
    return panel,snapshots


def parse(payload,date):
    rows=payload['result'];assert rows,'Empty is not zero activity'
    assert len({row['SECURITY_CODE'] for row in rows})==len(rows)
    output=[]
    for row in rows:
        assert pd.Timestamp(row['TRADE_DATE'])==date
        c,p,total=[number(row[k]) for k in ('CALL_VOLUME','PUT_VOLUME','TOTAL_VOLUME')]
        oc,op,oi=[number(row[k]) for k in ('LEAVES_CALL_QTY','LEAVES_PUT_QTY','LEAVES_QTY')]
        assert min(c,p,oc,op)>0 and c+p==total and oc+op==oi
        assert abs(100*p/c-number(row['CP_RATE']))<=.011
        if row['SECURITY_CODE'] in ('510050','510300'):
            output.append(dict(code=row['SECURITY_CODE'],call_volume=c,put_volume=p,call_oi=oc,put_oi=op))
    codes={r['code'] for r in output};assert '510050' in codes
    assert ('510300' in codes)==(date>=LAUNCH_300),'Unexpected missing or prelaunch 300ETF record'
    return output


def run():
    DEST.mkdir(exist_ok=True);CACHE.mkdir(exist_ok=True)
    panel,snapshots=dates_and_panel();results=[];normalized=[]
    manifest=dict(source_panel_sha256=digest(SOURCE),month_panel_sha256=digest(MONTHS),calendar_sha256=digest(CALENDAR),
                  plan_sha256=digest(EP/'notes/r38_option_activity.md'),lag_trading_sessions=2,expected_snapshots=len(snapshots),
                  results=results,complete=False,url=URL)
    path=DEST/'source_manifest.json'
    for origin,date in snapshots.items():
        params=dict(isPagination='false',sqlId='COMMON_SSE_ZQPZ_YSP_QQ_SJTJ_MRTJ_CX',tradeDate=date.strftime('%Y%m%d'))
        file=CACHE/f'{date.date()}.json'
        try:
            if not file.exists():
                time.sleep(1)
                response=requests.get(URL,params=params,headers={'Referer':'https://www.sse.com.cn/assortment/options/date/'},timeout=30)
                response.raise_for_status();payload=response.json();parse(payload,date)
                file.write_bytes(response.content)
            payload=json.loads(file.read_text());rows=parse(payload,date)
            normalized.extend(dict(date=origin,snapshot_date=date,**row) for row in rows)
            results.append(dict(origin=str(origin.date()),snapshot=str(date.date()),path=str(file),sha256=digest(file),params=params,status='complete',assets=len(rows)))
        except Exception as error:
            results.append(dict(origin=str(origin.date()),snapshot=str(date.date()),params=params,status='failed',error=repr(error)))
            path.write_text(json.dumps(manifest,indent=2)+'\n');raise
        path.write_text(json.dumps(manifest,indent=2)+'\n')
        if len(results)%10==0:print(len(results),'/',len(snapshots),'snapshots complete',flush=True)
    normalized=pd.DataFrame(normalized);assert not normalized.duplicated(['date','code']).any()
    normalized.to_parquet(CACHE/'normalized.parquet',index=False)
    manifest.update(complete=True,normalized_sha256=digest(CACHE/'normalized.parquet'))
    path.write_text(json.dumps(manifest,indent=2)+'\n')
    print('complete',len(results),'snapshots;',len(normalized),'asset-date rows',flush=True)


if __name__=='__main__':run()
