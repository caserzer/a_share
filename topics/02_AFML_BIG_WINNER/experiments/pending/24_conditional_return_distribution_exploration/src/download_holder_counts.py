"""Public GET-only complete shareholder-count history for the existing universe."""
import concurrent.futures,json,time
from pathlib import Path
import pandas as pd
import requests
from prepare_panel import OUT
from build_margin_information import digest
from build_joint_information import SOURCE
CACHE=OUT/'local_cache/r36_holder_counts'
DEST=OUT/'r36_holder_counts'
URL='https://datacenter-web.eastmoney.com/api/data/v1/get'


def fetch(code):
    receipts=[];page=1;records=[];expected=None
    while True:
        params=dict(reportName='RPT_HOLDERNUM_DET',columns='ALL',filter=f'(SECURITY_CODE="{code}")',
                    pageNumber=page,pageSize=500,sortColumns='END_DATE',sortTypes=-1,source='WEB',client='WEB')
        path=CACHE/f'{code}_{page}.json'
        if not path.exists():
            for attempt in range(3):
                try:
                    response=requests.get(URL,params=params,timeout=30);response.raise_for_status();payload=response.json()
                    empty=(payload.get('code')==9201 and payload.get('message')=='返回数据为空' and payload.get('result') is None)
                    assert (payload['success'] and payload['result'] is not None) or empty,repr(payload)
                    path.write_bytes(response.content);break
                except (requests.RequestException,ValueError,AssertionError):
                    if attempt==2:raise
                    time.sleep(1)
        payload=json.loads(path.read_text())
        if payload.get('code')==9201 and payload.get('message')=='返回数据为空' and payload.get('result') is None:
            assert page==1
            return dict(code=code,status='source_no_records',rows=0,pages=[dict(path=str(path),sha256=digest(path),rows=0,params=params)],
                        meaning='No rows returned by this vendor query; unknown shareholder information, not zero holders')
        assert payload['success'];result=payload['result']
        if expected is None:expected=(result['count'],result['pages'])
        assert (result['count'],result['pages'])==expected
        rows=result['data'];assert all(r['SECURITY_CODE']==code for r in rows)
        records.extend(rows);receipts.append(dict(path=str(path),sha256=digest(path),rows=len(rows),params=params))
        if page>=result['pages']:break
        page+=1
    assert len(records)==expected[0]
    return dict(code=code,status='complete',rows=len(records),pages=receipts)


def run():
    CACHE.mkdir(exist_ok=True);DEST.mkdir(exist_ok=True)
    panel=pd.read_parquet(SOURCE);codes=sorted(panel.instrument.str[2:].unique());assert len(codes)==1242
    assert all(len(c)==6 and c.isdigit() for c in codes)
    results=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        futures={pool.submit(fetch,c):c for c in codes}
        for future in concurrent.futures.as_completed(futures):
            code=futures[future]
            try:results.append(future.result())
            except Exception as e:results.append(dict(code=code,status='failed',error=str(e)))
            if len(results)%50==0:print(len(results),'of',len(codes),'complete responses',sum(r['status']=='complete' for r in results),flush=True)
    result=dict(url=URL,method='Public GET only',source_panel_sha256=digest(SOURCE),stocks=len(codes),
                complete=sum(r['status']=='complete' for r in results),source_no_records=sum(r['status']=='source_no_records' for r in results),
                failed=sum(r['status']=='failed' for r in results),results=sorted(results,key=lambda r:r['code']))
    (DEST/'source_manifest.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='results'},indent=2),flush=True)
    assert result['failed']==0,'Keep transport failures explicit; do not interpret failed fetches as no holdings data'
    assert result['complete']+result['source_no_records']==len(codes)


if __name__=='__main__':run()
