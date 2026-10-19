"""Retrieve the four separately archived original/amended forecast PDFs."""
import json
from pathlib import Path
import requests
import pymupdf
from prepare_panel import OUT
from build_margin_information import digest
DEST=OUT/'r37_company_guidance_probe'
CACHE=OUT/'local_cache/r37_guidance_archive_pdfs'
EXPECTED={'AN202501201642370882':['2,200','3,300'],
          'AN202504211660034958':['2,200','3,300','500','1,000'],
          'AN202501241642526614':['29,000','39,000'],
          'AN202504251662223707':['29,000','39,000','43,500','53,500']}


def run():
    CACHE.mkdir(exist_ok=True);catalog=json.loads((DEST/'announcement_archive_probe.json').read_text());results=[]
    official=json.loads((DEST/'cninfo_archive_probe.json').read_text())
    documents=[r for g in official['results'] for r in g['announcements']]
    for item in catalog['records']:
        code=item['art_code']
        matched=[r for r in documents if r['secCode']==item['query_stock'] and r['adjunctUrl'].split('/')[1]==item['notice_date'][:10]
                 and ('修正' in r['announcementTitle'])==('修正' in item['title'])]
        assert len(matched)==1;document=matched[0]
        url='https://static.cninfo.com.cn/'+document['adjunctUrl'];path=CACHE/f'{document["announcementId"]}.pdf'
        if not path.exists():
            response=requests.get(url,timeout=40);response.raise_for_status();assert response.content.startswith(b'%PDF');path.write_bytes(response.content)
        pages=[page.get_text() for page in pymupdf.open(path)];text='\n'.join(pages)
        assert item['query_stock'] in text and all(token in text for token in EXPECTED[code])
        (CACHE/f'{code}.txt').write_text(text)
        results.append(dict(stock=item['query_stock'],art_code=code,title=item['title'],notice_date=item['notice_date'],
            official_announcement_id=document['announcementId'],official_announcement_time=document['announcementTime'],
            url=url,path=str(path),sha256=digest(path),pages=len(pages),expected_numbers_present=True,
            revised_title='修正' in item['title']))
        print(code,item['title'],len(pages),'pages',text[:650].replace('\n',' '),flush=True)
    (DEST/'original_and_revised_pdf_receipts.json').write_text(json.dumps(dict(records=results,
        limitation='Four-case archive recovery and expected number check; not a general-purpose numeric parser or full-universe validation.'),indent=2)+'\n')


if __name__=='__main__':run()
