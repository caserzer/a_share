"""Public implemented dividend/split and rights history, with all pages retained."""
import json
import time
import requests
import pandas as pd
from run_price_pilot import OUT


def run():
    folder=OUT/'local_cache/corporate_actions'
    folder.mkdir(exist_ok=True)
    session=requests.Session()
    session.trust_env=False
    audit=[]
    for report,columns in [
        ('RPT_SHAREBONUS_DET','SECURITY_CODE,EX_DIVIDEND_DATE,REPORT_DATE,BONUS_IT_RATIO,PRETAX_BONUS_RMB,NOTICE_DATE,ASSIGN_PROGRESS,IMPL_PLAN_PROFILE'),
        ('RPT_IPO_ALLOTMENT','SECURITY_CODE,EX_DIVIDEND_DATE,EQUITY_RECORD_DATE,PLACING_RATIO,ISSUE_PRICE,LISTING_DATE')]:
        page,total=1,1
        frames=[]
        while page<=total:
            cache=folder/f'{report}_{page:03}.parquet'
            meta=folder/f'{report}_{page:03}.json'
            if cache.exists() and meta.exists():
                frame=pd.read_parquet(cache)
                payload=json.loads(meta.read_text())
            else:
                params={'reportName':report,'columns':columns,'pageSize':'500','pageNumber':str(page),
                        'sortColumns':'EX_DIVIDEND_DATE,SECURITY_CODE','sortTypes':'-1,1','source':'WEB','client':'WEB',
                        'filter':"(EX_DIVIDEND_DATE>='2017-01-01')(EX_DIVIDEND_DATE<='2026-05-29')"}
                response=session.get('https://datacenter-web.eastmoney.com/api/data/v1/get',params=params,timeout=25)
                response.raise_for_status()
                result=response.json().get('result')
                if not result:
                    raise ValueError(f'No result: {report} page {page}')
                frame=pd.DataFrame(result['data'])
                payload={'pages':result['pages'],'count':result.get('count'),'page':page}
                frame.to_parquet(cache,index=False)
                meta.write_text(json.dumps(payload)+'\n')
                time.sleep(.15)
            total=int(payload['pages'])
            frames.append(frame)
            if page%10==0 or page==total:
                print(report,page,'/',total,flush=True)
            page+=1
        combined=pd.concat(frames,ignore_index=True)
        combined.to_parquet(folder/f'{report}_all.parquet',index=False)
        audit.append({'report':report,'pages':total,'rows':len(combined),'reported_count':payload['count'],
                      'start':str(combined.EX_DIVIDEND_DATE.min()),'end':str(combined.EX_DIVIDEND_DATE.max())})
    (OUT/'corporate_action_fetch_audit.json').write_text(json.dumps(audit,indent=2)+'\n')
    print(audit)


if __name__=='__main__':
    run()
