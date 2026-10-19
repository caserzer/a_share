"""Four count observations checked against two original official report PDFs."""
import json
from pathlib import Path
import pymupdf
import requests
from prepare_panel import OUT
from build_margin_information import digest
from download_holder_counts import CACHE,DEST
CASES=[dict(code='300750',url='https://static.cninfo.com.cn/finalpage/2021-04-28/1209834847.PDF',archive_date='2021-04-28',
            values={'2020-12-31':133060,'2021-03-31':182794}),
       dict(code='600519',url='https://big5.sse.com.cn/site/cht/www.sse.com.cn/disclosure/listedinfo/announcement/c/new/2026-04-17/600519_20260417_9QS4.pdf',
            archive_date='2026-04-17',values={'2025-12-31':255892,'2026-03-31':243159})]


def run():
    folder=OUT/'local_cache/r36_holder_filing_checks';folder.mkdir(exist_ok=True);checks=[]
    for case in CASES:
        path=folder/f'{case["code"]}_{case["archive_date"]}.pdf'
        if not path.exists():
            r=requests.get(case['url'],timeout=40);r.raise_for_status();assert r.content.startswith(b'%PDF');path.write_bytes(r.content)
        doc=pymupdf.open(path);pages=[page.get_text() for page in doc]
        matching=[i+1 for i,t in enumerate(pages) if all(f'{v:,}' in t for v in case['values'].values())]
        assert matching,'Both count observations must be found on the same original report page'
        records=json.loads((CACHE/f'{case["code"]}_1.json').read_text())['result']['data']
        for end,value in case['values'].items():
            row=next(r for r in records if r['END_DATE'][:10]==end);assert row['HOLDER_NUM']==value
            notice=row['HOLD_NOTICE_DATE'][:10]
            checks.append(dict(code=case['code'],period=end,count=value,url=case['url'],pdf_path=str(path),pdf_sha256=digest(path),
                report_pages_1based=matching,archive_date=case['archive_date'],vendor_notice_date=notice,
                vendor_date_later_than_report_archive=notice>case['archive_date'],count_matched=True))
    (DEST/'filing_crosschecks.json').write_text(json.dumps(dict(checks=checks,
        all_four_counts_match=True,all_dates_verified_as_earliest_publication=False,
        policy='Preserve vendor notice dates even when a dated official annual report already contains the observation. No backdating or full-vintage certification.'),indent=2)+'\n')
    print(json.dumps(checks,indent=2))


if __name__=='__main__':run()
