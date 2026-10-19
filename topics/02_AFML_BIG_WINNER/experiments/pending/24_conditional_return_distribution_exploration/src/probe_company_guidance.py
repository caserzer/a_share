"""Public management-guidance schema/history probe; not a model input yet."""
import json
import requests
import pandas as pd
from prepare_panel import OUT
from build_margin_information import digest
DEST=OUT/'r37_company_guidance_probe'
CACHE=OUT/'local_cache/r37_company_guidance_probe'
URL='https://datacenter.eastmoney.com/securities/api/data/v1/get'
CODES=['600519','300750','000002','002455']


def run():
    DEST.mkdir(exist_ok=True);CACHE.mkdir(exist_ok=True);receipts=[];summaries=[]
    for code in CODES:
        rows=[];page=1;count=None
        while True:
            params=dict(reportName='RPT_PUBLIC_OP_NEWPREDICT',columns='ALL',filter=f'(SECURITY_CODE="{code}")',
                        pageNumber=page,pageSize=500,sortColumns='NOTICE_DATE,SECURITY_CODE',sortTypes='-1,-1')
            path=CACHE/f'{code}_{page}.json'
            if not path.exists():
                r=requests.get(URL,params=params,timeout=30);r.raise_for_status();path.write_bytes(r.content)
            payload=json.loads(path.read_text());assert payload['success'];result=payload['result']
            if count is None:count=result['count']
            assert result['count']==count
            rows.extend(result['data']);receipts.append(dict(path=str(path),sha256=digest(path),params=params,rows=len(result['data'])))
            if page>=result['pages']:break
            page+=1
        assert len(rows)==count;d=pd.DataFrame(rows);assert d.SECURITY_CODE.eq(code).all()
        dates=pd.to_datetime(d.NOTICE_DATE)
        summaries.append(dict(code=code,rows=len(d),first_notice=str(dates.min()),last_notice=str(dates.max()),
                              missing_notice=int(dates.isna().sum()),columns=list(d.columns),sample=d.iloc[0].to_dict()))
    (DEST/'source_probe.json').write_text(json.dumps(dict(url=URL,receipts=receipts,summaries=summaries,
        status='Schema/history probe only; no original announcement or revision-vintage validation yet; not a prediction candidate.'),indent=2)+'\n')
    print(json.dumps(summaries,indent=2,ensure_ascii=False))


if __name__=='__main__':run()
