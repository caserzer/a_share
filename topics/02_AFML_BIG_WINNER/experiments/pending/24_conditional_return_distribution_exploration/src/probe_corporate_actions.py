"""Bounded probe for reconstructing a cash-dividend/split return sensitivity."""
import json
import requests
import pandas as pd
from run_price_pilot import OUT

if __name__=='__main__':
    session=requests.Session()
    session.trust_env=False
    folder=OUT/'local_cache/corporate_actions'
    folder.mkdir(exist_ok=True)
    summaries=[]
    for report,sort,filter_ in [('RPT_SHAREBONUS_DET','REPORT_DATE','(SECURITY_CODE="600000")'),
                              ('RPT_IPO_ALLOTMENT','EQUITY_RECORD_DATE','')]:
        response=session.get('https://datacenter-web.eastmoney.com/api/data/v1/get',params={
            'sortColumns':sort,'sortTypes':'-1','pageSize':'5000','pageNumber':'1',
            'reportName':report,'columns':'ALL','source':'WEB','client':'WEB','filter':filter_},timeout=25)
        response.raise_for_status()
        result=response.json().get('result') or {}
        f=pd.DataFrame(result.get('data') or [])
        f.to_parquet(folder/f'{report}_probe.parquet',index=False)
        summaries.append({'report':report,'rows':len(f),'pages':result.get('pages'),'columns':list(f.columns)})
        print(report,len(f),'pages',result.get('pages'),flush=True)
        print(f.head(1).to_dict('records'),flush=True)
    (OUT/'corporate_action_probe.json').write_text(json.dumps(summaries,indent=2,ensure_ascii=False)+'\n')
