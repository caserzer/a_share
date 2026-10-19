"""Official announcement catalog, retaining independent initial/amended documents."""
import argparse,json,math,time
from pathlib import Path
import requests
import pandas as pd
from prepare_panel import OUT
from build_joint_information import SOURCE
from build_margin_information import digest
DEST=OUT/'r37_company_guidance'
CACHE=OUT/'local_cache/r37_guidance_catalog'
DIRECTORY=OUT/'local_cache/r37_cninfo_guidance/stock_directory.json'
URL='https://www.cninfo.com.cn/new/hisAnnouncement/query'
START='2017-01-01';END='2026-04-30'


class CatalogAccessStopped(RuntimeError):
    """An access denial ends the batch; it is never retried as empty data."""


def fetch(code,org,cache_only=False):
    page=1;expected=None;all_rows=[];receipts=[]
    while True:
        params=dict(pageNum=page,pageSize=30,column='szse',tabName='fulltext',plate='',stock=f'{code},{org}',searchkey='',secid='',
                    category='category_yjygjxz_szsh',trade='',seDate=f'{START}~{END}',sortName='',sortType='',isHLtitle='false')
        path=CACHE/f'{code}_{page}.json'
        if not path.exists():
            if cache_only:
                return dict(code=code,status='unqueried',missing_page=page,pages=receipts)
            for attempt in range(3):
                try:
                    time.sleep(1)
                    response=requests.post(URL,data=params,timeout=40)
                    if response.status_code in (401,403,429):
                        receipt=dict(code=code,page=page,status=response.status_code,params=params,
                                     content_type=response.headers.get('Content-Type'),bytes=len(response.content),
                                     retry_after=response.headers.get('Retry-After'))
                        (DEST/'access_stop.json').write_text(json.dumps(receipt,indent=2)+'\n')
                        raise CatalogAccessStopped(f'HTTP {response.status_code}: batch stopped')
                    response.raise_for_status();payload=response.json()
                    assert isinstance(payload.get('totalAnnouncement'),int) and isinstance(payload.get('announcements'),(list,type(None)))
                    path.write_bytes(response.content);break
                except (requests.RequestException,ValueError,AssertionError):
                    if attempt==2:raise
                    time.sleep(1+attempt)
        payload=json.loads(path.read_text());total=payload['totalAnnouncement'];rows=payload['announcements'] or []
        if expected is None:expected=total
        assert total==expected
        assert all(r['secCode']==code for r in rows),f'Unexpected security codes: {sorted({r["secCode"] for r in rows})}'
        receipts.append(dict(path=str(path),sha256=digest(path),params=params,rows=len(rows)))
        all_rows.extend(rows)
        if page>=max(1,math.ceil(total/30)):break
        page+=1
    assert len(all_rows)==expected
    assert len({r['announcementId'] for r in all_rows})==len(all_rows)
    return dict(code=code,status='complete',announcements=len(all_rows),pages=receipts)


def run(cache_only=False):
    DEST.mkdir(exist_ok=True);CACHE.mkdir(exist_ok=True)
    panel=pd.read_parquet(SOURCE);codes=sorted(panel.instrument.str[2:].unique());assert len(codes)==1242
    mapping={r['code']:r['orgId'] for r in json.loads(DIRECTORY.read_text())['stockList']}
    assert set(codes).issubset(mapping)
    results=[];stopped=False;consecutive_failures=0
    checkpoint=DEST/'catalog_progress.jsonl'
    with checkpoint.open('w') as stream:
        for code in codes:
            try:
                result=fetch(code,mapping[code],cache_only=cache_only or stopped)
                consecutive_failures=0
            except CatalogAccessStopped as e:
                result=dict(code=code,status='failed',error=str(e));stopped=True
            except Exception as e:
                result=dict(code=code,status='failed',error=repr(e));consecutive_failures+=1
                if consecutive_failures>=3:stopped=True
            results.append(result);stream.write(json.dumps(result)+'\n');stream.flush()
            if len(results)%100==0:print(len(results),'/',len(codes),'checked; network stopped',stopped,flush=True)
    manifest=dict(url=URL,method='POST read-only disclosure search',start=START,end=END,category='category_yjygjxz_szsh',
        source_panel_sha256=digest(SOURCE),directory_sha256=digest(DIRECTORY),stocks=len(codes),
        complete=sum(r['status']=='complete' for r in results),failed=sum(r['status']=='failed' for r in results),
        unqueried=sum(r['status']=='unqueried' for r in results),cache_only=cache_only,network_stopped=stopped,
        results=sorted(results,key=lambda r:r['code']),
        limitation='Completeness of requested standalone guidance category only; forecasts embedded in other reports and withdrawn/unindexed documents are not certified.')
    (DEST/'catalog_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps({k:v for k,v in manifest.items() if k!='results'},indent=2),flush=True)
    if not cache_only:
        assert manifest['failed']==0 and manifest['unqueried']==0,'Partial catalog: failed/unqueried is not no guidance'


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--cache-only',action='store_true')
    run(parser.parse_args().cache_only)
