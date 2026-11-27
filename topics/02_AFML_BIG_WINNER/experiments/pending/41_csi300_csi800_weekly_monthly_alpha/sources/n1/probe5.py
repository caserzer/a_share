"""Query a 5-minute sample from BaoStock separately from 1-minute results."""
from pathlib import Path
import hashlib,json,sys
import socket
import pandas as pd
import baostock as bs
HERE=Path(__file__).resolve().parent
def run():
    socket.setdefaulttimeout(10)
    p=pd.read_csv(HERE/'pilot_design.csv')
    row=p.iloc[0];code=row.original
    meta=dict(provider='BaoStock',version=bs.__version__,observed_at=pd.Timestamp.now(tz='UTC').isoformat(),api='query_history_k_data_plus',frequency='5',code=code,date=row.start)
    try:
        login=bs.login()
        meta.update(login_code=login.error_code,login_msg=login.error_msg)
        if login.error_code=='0':
            r=bs.query_history_k_data_plus(code[:2].lower()+'.'+code[2:],'date,time,code,open,high,low,close,volume,amount',start_date=row.start,end_date=row.start,frequency='5',adjustflag='3')
            meta.update(code_status=r.error_code,msg=r.error_msg)
            ds=[]
            while r.error_code=='0' and r.next():ds.append(r.get_row_data())
            meta.update(rows=len(ds),sha256=hashlib.sha256(json.dumps(ds).encode()).hexdigest())
            bs.logout()
    except Exception as ex:meta.update(error=type(ex).__name__,reason=str(ex))
    (HERE/'baostock_probe.json').write_text(json.dumps(meta,indent=2,ensure_ascii=False)+'\n')
    print(meta,flush=True)
if __name__=='__main__':run()
