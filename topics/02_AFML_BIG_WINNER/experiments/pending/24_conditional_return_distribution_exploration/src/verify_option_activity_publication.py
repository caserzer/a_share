"""Check one dated official monthly publication against raw daily activity fields."""
import json
import re
import pymupdf
from prepare_panel import OUT
from build_margin_information import digest
from probe_domestic_option_activity import number


def run():
    cache=OUT/'local_cache/r38_option_activity_probe';dest=OUT/'r38_option_activity_probe'
    path=cache/'sse_202104_monthly_option.pdf';raw=cache/'20210401.json'
    rows=json.loads(raw.read_text())['result'];checks=[]
    with pymupdf.open(path) as document:
        pages=[(i+1,page.get_text()) for i,page in enumerate(document) if '期权成交概况' in page.get_text() and '2021-04-01' in page.get_text()]
    assert len(pages)==1;page,text=pages[0]
    assert '成交量（万张）' in text and '持仓量（万张）' in text
    for side,volume,oi in [('认购','CALL_VOLUME','LEAVES_CALL_QTY'),('认沽','PUT_VOLUME','LEAVES_PUT_QTY')]:
        match=re.search(r'2021-04-01\s+'+side+r'\s+(\d+)\s+(\d+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)',text)
        assert match and int(match[1])==len(rows)==2
        for field,expected in [(volume,float(match[3])),(oi,float(match[5]))]:
            observed=sum(number(row[field]) for row in rows)/10000
            assert abs(observed-expected)<=.005001
            checks.append(dict(side=side,field=field,api_in_10000_contracts=observed,published_in_10000_contracts=expected))
    receipt=dict(pdf=str(path),pdf_sha256=digest(path),pdf_page=page,daily_source=str(raw),daily_source_sha256=digest(raw),
                 checks=checks,all_four_match_published_precision=True,
                 url='https://www.sse.com.cn/aboutus/publication/monthly/documents/c/10061126/files/b7af8896606a4e069b543eb176dcef15.pdf',
                 limitation='One-date field/unit crosscheck, not proof of point-in-time publication for every historical daily response.')
    (dest/'publication_crosscheck.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n');print(json.dumps(checks,ensure_ascii=False))


if __name__=='__main__':run()
