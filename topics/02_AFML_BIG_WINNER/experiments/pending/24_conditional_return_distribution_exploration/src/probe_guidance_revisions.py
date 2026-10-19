"""Check known amended forecasts against official PDFs and the current public table."""
import json
import requests
import pandas as pd
import pymupdf
from prepare_panel import OUT
from build_margin_information import digest
from probe_company_guidance import DEST,URL
CACHE=OUT/'local_cache/r37_guidance_revision_checks'
CASES=[dict(code='300520',original_notice='2025-01-21',revised_notice='2025-04-22',
            original=[22000000,33000000],revised=[-10000000,-5000000],
            pdf='https://static.cninfo.com.cn/finalpage/2025-04-22/1223191491.PDF',tokens=['2,200','3,300','500','1,000']),
       dict(code='300663',original_notice='2025-01-24',revised_notice='2025-04-25',
            original=[-390000000,-290000000],revised=[-535000000,-435000000],
            pdf='https://static.cninfo.com.cn/finalpage/2025-04-25/1223301948.PDF',tokens=['29,000','39,000','43,500','53,500'])]


def run():
    CACHE.mkdir(exist_ok=True);results=[]
    for case in CASES:
        params=dict(reportName='RPT_PUBLIC_OP_NEWPREDICT',columns='ALL',
            filter=f'(SECURITY_CODE="{case["code"]}")(REPORT_DATE=\'2024-12-31\')',
            pageNumber=1,pageSize=500,sortColumns='NOTICE_DATE,SECURITY_CODE',sortTypes='-1,-1')
        path=CACHE/f'{case["code"]}.json';pdf=CACHE/f'{case["code"]}.pdf'
        if not path.exists():
            r=requests.get(URL,params=params,timeout=30);r.raise_for_status();path.write_bytes(r.content)
        if not pdf.exists():
            r=requests.get(case['pdf'],timeout=30);r.raise_for_status();assert r.content.startswith(b'%PDF');pdf.write_bytes(r.content)
        pages=[p.get_text() for p in pymupdf.open(pdf)]
        assert all(any(token in t for t in pages) for token in case['tokens'])
        payload=json.loads(path.read_text());assert payload['success'];rows=payload['result']['data']
        assert len(rows)==payload['result']['count']
        selected=[r for r in rows if r['PREDICT_FINANCE']=='归属于上市公司股东的净利润']
        current=[dict(notice=r['NOTICE_DATE'][:10],bounds=[r['PREDICT_AMT_LOWER'],r['PREDICT_AMT_UPPER']],latest=r['IS_LATEST']) for r in selected]
        results.append(dict(**case,public_table_rows=current,source_json=str(path),source_sha256=digest(path),pdf_path=str(pdf),pdf_sha256=digest(pdf),
            original_version_present=any(r['notice']==case['original_notice'] and sorted(r['bounds'])==case['original'] for r in current),
            revised_version_present=any(r['notice']==case['revised_notice'] and sorted(r['bounds'])==case['revised'] for r in current),
            revised_value_at_original_date=any(r['notice']==case['original_notice'] and sorted(r['bounds'])==case['revised'] for r in current)))
    (DEST/'revision_probe.json').write_text(json.dumps(dict(cases=results,
        scope='Two known amendments only. Does not certify the full source or any input readiness.'),indent=2)+'\n')
    print(json.dumps(results,indent=2,ensure_ascii=False))


if __name__=='__main__':run()
