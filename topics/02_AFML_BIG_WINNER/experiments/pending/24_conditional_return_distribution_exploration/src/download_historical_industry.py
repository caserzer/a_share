"""Download public CAPCO dated classification releases, without evaluating remote code."""
import json,re,time
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup
from prepare_panel import OUT
from build_margin_information import digest
CACHE=OUT/'local_cache/r32_industry'

def discover():
    CACHE.mkdir(exist_ok=True)
    source=CACHE/'capco.js'
    if not source.exists():
        r=requests.get('https://www.capco.org.cn/',timeout=40);r.raise_for_status()
        soup=BeautifulSoup(r.content,'html.parser');script=soup.find('script',src=re.compile(r'assets/index-'))
        assert script is not None
        url=urljoin('https://www.capco.org.cn/',script['src']);r=requests.get(url,timeout=40);r.raise_for_status();source.write_bytes(r.content)
    items=[]
    for m in re.finditer(r'\{title:"([^"]+)",articleUrl:"(zsxfb/hyfl/hyfljg/[^"]+)",date:"([^"]+)"',source.read_text()):
        title,path,date=m.groups()
        if '2018'<=date<'2026-05-01':items.append(dict(title=title,path=path,date=date))
    (CACHE/'capco_links.json').write_text(json.dumps(items,ensure_ascii=False,indent=2)+'\n')
    (CACHE/'discovery_receipt.json').write_text(json.dumps(dict(source_url='https://www.capco.org.cn/',script_path=str(source),script_sha256=digest(source)),indent=2)+'\n')
    return items


def run():
    items=discover();records=[]
    session=requests.Session()
    for item in items:
        if item['date']<'2018-09-01':continue
        name=item['path'].split('/')[-1];url='https://www.capco.org.cn/dataFile/'+item['path'];path=CACHE/name
        if not path.exists():
            r=session.get(url,timeout=40);r.raise_for_status();assert r.text.startswith('export const allData = ');path.write_bytes(r.content)
        raw=path.read_text().split('=',1)[1].strip().rstrip(';');article=json.loads(raw)
        assert article['date']==item['date'] and article['title']==item['title']
        soup=BeautifulSoup(article['text'],'html.parser');links=[a for a in soup.find_all('a',href=True) if '.pdf' in a['href'].lower() and '对照' not in a.get_text()]
        assert links,item
        # Stock-code sorted releases are easiest to audit; older releases provide one industry-sorted table.
        preferred=[a for a in links if '代码排序' in a.get_text()];a=(preferred or links)[0]
        pdfurl=urljoin('https://www.capco.org.cn/',a['href']);pdf=CACHE/(name[:-3]+'.pdf')
        record=dict(**item,article_url=url,article_path=str(path),article_sha256=digest(path),pdf_url=pdfurl,pdf_title=a.get_text(),pdf_path=str(pdf))
        try:
            if not pdf.exists():
                r=session.get(pdfurl,timeout=40);r.raise_for_status();assert r.content.startswith(b'%PDF'),r.text[:70];pdf.write_bytes(r.content)
            record.update(status='ok',pdf_sha256=digest(pdf),pdf_bytes=pdf.stat().st_size)
        except Exception as e:record.update(status='failed',error=type(e).__name__+': '+str(e))
        records.append(record);(CACHE/'download_manifest.json').write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n')
        print(item['title'],item['date'],record['status'],record.get('pdf_bytes',record.get('error')),flush=True);time.sleep(.2)

if __name__=='__main__':run()
