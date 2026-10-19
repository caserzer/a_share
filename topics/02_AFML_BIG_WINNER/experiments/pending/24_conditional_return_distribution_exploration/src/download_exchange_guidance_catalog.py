"""Independent exchange disclosure catalogs. Titles, not latest financial tables."""
import argparse
import hashlib
import json
import math
import time
from pathlib import Path
import pandas as pd
import requests
from prepare_panel import OUT
from build_joint_information import SOURCE
from build_margin_information import digest

DEST=OUT/'r37_exchange_guidance'
CACHE=OUT/'local_cache/r37_exchange_catalog'
START='2017-01-01'; END='2026-04-30'
ALIAS={'000043':'001914'}
ALIAS_EVIDENCE='https://www.szse.cn/disclosure/notice/general/t20191211_572534.html'
SZ_URL='https://www.szse.cn/api/disc/announcement/annList'
SH_URL='https://query.sse.com.cn/security/stock/queryCompanyBulletinNew.do'


def quarters(start=START,end=END):
    end=pd.Timestamp(end)
    for left in pd.date_range(start,end,freq='QS'):
        yield str(left.date()),str(min(left+pd.offsets.QuarterEnd(),end).date())


def flatten_sse(payload):
    groups=payload['result']
    assert isinstance(groups,list)
    assert groups==payload['pageHelp']['data']
    assert all(isinstance(group,list) and group for group in groups)
    return [row for group in groups for row in group]


def request_page(exchange,params):
    url=SZ_URL if exchange=='SZ' else SH_URL
    key=hashlib.sha256(json.dumps(params,sort_keys=True,ensure_ascii=False).encode()).hexdigest()[:20]
    path=CACHE/f'{exchange}_{key}.json'
    if not path.exists():
        time.sleep(1)
        if exchange=='SZ':response=requests.post(url,json=params,timeout=40)
        else:response=requests.get(url,params=params,headers={'Referer':'https://www.sse.com.cn/disclosure/listedinfo/announcement/'},timeout=40)
        if not response.ok:
            failure=dict(exchange=exchange,url=url,params=params,http_status=response.status_code,
                         content_type=response.headers.get('Content-Type'),bytes=len(response.content))
            (DEST/'last_http_failure.json').write_text(json.dumps(failure,ensure_ascii=False,indent=2)+'\n')
        response.raise_for_status()
        payload=response.json()
        if exchange=='SZ':assert isinstance(payload.get('announceCount'),int) and isinstance(payload.get('data'),list)
        else:assert isinstance(payload.get('pageHelp',{}).get('total'),int) and isinstance(payload.get('result'),list)
        path.write_bytes(response.content)
    return json.loads(path.read_text()),dict(path=str(path),sha256=digest(path),params=params)


def fetch_window(exchange,start,end,codes,title_query=None):
    if exchange=='SZ':
        params=dict(stock=sorted(set(codes)|set(ALIAS)),channelCode=['listedNotice_disc'],searchKey=[title_query or '业绩预告'],
                    pageSize=50,pageNum=1,seDate=[start,end])
        size=50
    else:
        assert pd.Timestamp(end)<pd.Timestamp(start)+pd.DateOffset(months=3)
        size=25
        params={'isPagination':'true','pageHelp.pageSize':size,'pageHelp.cacheSize':1,'pageHelp.pageNo':1,
                'START_DATE':start,'END_DATE':end,'SECURITY_CODE':'','TITLE':'业绩预','BULLETIN_TYPE':'','stockType':''}
    records=[];receipts=[];expected=None;groups_seen=0;seen=set()
    page=1
    while True:
        params['pageNum' if exchange=='SZ' else 'pageHelp.pageNo']=page
        if exchange=='SH':
            params['pageHelp.beginPage']=page
            params['pageHelp.endPage']=page
        payload,receipt=request_page(exchange,dict(params))
        if exchange=='SZ':total=payload['announceCount'];rows=payload['data'];count=len(rows)
        else:
            total=payload['pageHelp']['total'];rows=flatten_sse(payload);count=len(payload['result'])
            assert payload['pageHelp']['pageNo']==page and payload['pageHelp']['pageSize']==size
            assert payload['START_DATE']==start and payload['END_DATE']==end
        if expected is None:expected=total
        assert total==expected,'Catalog count changed during pagination'
        assert count==min(size,max(expected-(page-1)*size,0)),'Missing or truncated page'
        for row in rows:
            date=(row['publishTime'] if exchange=='SZ' else row['SSEDATE'])[:10]
            assert start<=date<=end
            raw_codes=row['secCode'] if exchange=='SZ' else [row['SECURITY_CODE']]
            mapped={ALIAS.get(code,code) for code in raw_codes}
            if exchange=='SZ':assert mapped & set(codes),'Unexpected security'
            matched=sorted(mapped & set(codes))
            if not matched:continue
            title=row['title'] if exchange=='SZ' else row['TITLE']
            url=('https://disc.static.szse.cn'+row['attachPath']) if exchange=='SZ' else ('https://www.sse.com.cn'+row['URL'])
            identity=str(row['annId'] if exchange=='SZ' else row['ORG_BULLETIN_ID'])
            assert (identity,url) not in seen,'Repeated selected document across pages'
            seen.add((identity,url))
            records.append(dict(exchange=exchange,announcement_id=identity,stocks=matched,raw_codes=raw_codes,
                                title=title,publish_date=date,url=url,source_page=receipt['path']))
        receipt.update(groups=count,documents=len(rows));receipts.append(receipt);groups_seen+=count
        if page>=max(1,math.ceil(expected/size)):break
        page+=1
        if page%20==0:print(exchange,start,'page',page,'of',math.ceil(expected/size),flush=True)
    assert groups_seen==expected
    identities=[(r['announcement_id'],r['url']) for r in records]
    assert len(identities)==len(set(identities)),'Duplicate announcement across pages'
    return dict(exchange=exchange,start=start,end=end,status='complete',query_groups=expected,
                selected_documents=len(records),pages=receipts,records=records)


def run(exchange):
    DEST.mkdir(exist_ok=True);CACHE.mkdir(exist_ok=True)
    panel=pd.read_parquet(SOURCE);codes=sorted({x[2:] for x in panel.instrument if x.startswith(exchange)})
    assert len(codes)==(709 if exchange=='SZ' else 533)
    windows=[(START,END)] if exchange=='SZ' else list(quarters())
    manifest=dict(exchange=exchange,source_panel_sha256=digest(SOURCE),stocks=len(codes),stock_codes=codes,
                  title_query='业绩预告' if exchange=='SZ' else '业绩预',category=None,
                  alias_mapping=ALIAS,alias_evidence=ALIAS_EVIDENCE,windows=[],complete=False,
                  limitation='Title-search catalog only (SZ 业绩预告; SH 业绩预 including 预增/预减/预亏). Embedded guidance and differently titled forecasts are not certified; no model input yet.')
    path=DEST/f'{exchange}_manifest.json'
    for start,end in windows:
        try:
            result=fetch_window(exchange,start,end,codes)
            catalog=DEST/f'{exchange}_{start}_{end}.json'
            catalog.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
            manifest['windows'].append(dict(start=start,end=end,status='complete',path=str(catalog),sha256=digest(catalog),
                                           query_groups=result['query_groups'],selected_documents=result['selected_documents']))
            print(exchange,start,end,'complete',result['selected_documents'],'selected documents',flush=True)
        except Exception as error:
            manifest['windows'].append(dict(start=start,end=end,status='failed',error=repr(error)))
            path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
            raise
        path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    manifest['complete']=True
    path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    print(exchange,'catalog complete',sum(x['selected_documents'] for x in manifest['windows']),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--exchange',choices=['SZ','SH'],required=True)
    run(parser.parse_args().exchange)
