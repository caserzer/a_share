"""Collect dated vendor snapshots for comparison against the publisher."""
import socket
from shared import *
sys.path.insert(0,str(Path.home()/'.cache/a_share/ep30_d2/backfill_v2/vendor'))
import baostock as bs
import requests,hashlib

def main():
    from wide_sources import CACHE
    dst=CACHE/'membership_cache';dst.mkdir(exist_ok=True)
    url='https://oss-ch.csindex.com.cn/static/html/csindex/public/uploads/file/autofile/cons/000906cons.xls'
    path=dst/'official_800.xls'
    if not path.exists():
        r=requests.get(url,timeout=15);r.raise_for_status();path.write_bytes(r.content)
    # Even when the date in the download changes, query both providers for that exact date.
    sheet=pd.read_excel(path);anchor=pd.Timestamp(str(sheet.iloc[0,0]))
    daily=pd.read_parquet(PRIVATE/'daily_members.parquet')
    weekly=pd.read_parquet(PRIVATE/'features.parquet',columns=['signal_date']).signal_date.unique()
    dates=sorted(set(pd.to_datetime(weekly))|set(outer().signal_date)|{anchor})
    # BaoStock serves the latest provider update at or before the query.
    socket.setdefaulttimeout(18);assert bs.login().error_code=='0'
    rows=[]; snap=[]
    try:
        for d in dates:
            date=d.strftime('%Y-%m-%d'); f=dst/(date+'.csv')
            if not f.exists():
                r=bs.query_zz500_stocks(date=date);assert r.error_code=='0'
                z=r.get_data();z.to_csv(f,index=False)
            z=pd.read_csv(f);names=set(z.code.str[3:]); assert z.code.nunique()==len(z)
            if d==anchor:
                r=bs.query_hs300_stocks(date=date);assert r.error_code=='0'
                base=set(r.get_data().code.str[3:])
            else:
                base=set(daily.columns[daily.loc[d]].str[2:])
            both=base|names
            rows.append(dict(query_date=date,update_date=','.join(z.updateDate.astype(str).unique()),n300=len(base),n500=len(names),overlap=len(base&names),union=len(both),file_sha256=hashlib.sha256(f.read_bytes()).hexdigest()))
            snap.extend((d,x) for x in sorted(both))
            if d==anchor:
                official=set(sheet.iloc[:,4].astype(str).str.zfill(6))
                (OUT/'official_anchor.json').write_text(json.dumps(dict(date=date,source=url,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),official=len(official),only_official=sorted(official-both),only_union=sorted(both-official)),indent=2))
    finally:
        bs.logout()
        pd.DataFrame(rows).to_csv(OUT/'membership_queries.csv',index=False)
        pd.DataFrame(snap,columns=['signal_date','code']).to_parquet(OUT/'membership_proxy.parquet',index=False)
if __name__=='__main__': main()
