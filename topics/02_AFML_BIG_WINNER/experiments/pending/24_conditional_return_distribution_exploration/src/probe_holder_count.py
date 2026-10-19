"""Small public shareholder-count source probe; no model or full-universe claim."""
import json
import requests
import pandas as pd
from prepare_panel import OUT
from build_margin_information import digest
CACHE=OUT/'local_cache/r36_holder_count_probe'
DEST=OUT/'r36_holder_count_probe'
CODES=['000001','600519','300750','300469']


def run():
    CACHE.mkdir(exist_ok=True);DEST.mkdir(exist_ok=True);receipts=[];diagnostics=[]
    for code in CODES:
        url='https://datacenter-web.eastmoney.com/api/data/v1/get'
        params=dict(reportName='RPT_HOLDERNUM_DET',columns='ALL',filter=f'(SECURITY_CODE="{code}")',
                    pageNumber=1,pageSize=500,sortColumns='END_DATE',sortTypes=-1,source='WEB',client='WEB')
        path=CACHE/f'{code}.json'
        if not path.exists():
            r=requests.get(url,params=params,timeout=30);r.raise_for_status();path.write_bytes(r.content)
        payload=json.loads(path.read_text());assert payload['success']
        data=payload['result'];assert data['pages']==1 and len(data['data'])==data['count']
        df=pd.DataFrame(data['data']);assert df.SECURITY_CODE.eq(code).all()
        for col in ['END_DATE','HOLD_NOTICE_DATE','PRE_END_DATE']:df[col]=pd.to_datetime(df[col])
        diagnostics.append(dict(code=code,rows=len(df),first_period=str(df.END_DATE.min().date()),last_period=str(df.END_DATE.max().date()),
            missing_announcement=int(df.HOLD_NOTICE_DATE.isna().sum()),notice_before_period=int((df.HOLD_NOTICE_DATE<df.END_DATE).sum()),
            duplicate_periods=int(df.END_DATE.duplicated().sum()),positive_count=int(df.HOLDER_NUM.gt(0).sum()),
            pre2021_rows=int((df.END_DATE<'2021-01-01').sum()),
            announcement_lag_median=float((df.HOLD_NOTICE_DATE-df.END_DATE).dt.days.median()),
            date_fields=[c for c in df.columns if 'DATE' in c]))
        receipts.append(dict(code=code,url=url,params=params,path=str(path),sha256=digest(path),rows=len(df)))
    (DEST/'source_probe.json').write_text(json.dumps(dict(diagnostics=diagnostics,receipts=receipts,
        limitations='Small source feasibility probe only. Vendor historical announcement fields are not immutable original vintages; no full population coverage or predictive improvement demonstrated.'),indent=2)+'\n')
    print(json.dumps(diagnostics,indent=2))


if __name__=='__main__':run()
