from wide_sources import *
from bs4 import BeautifulSoup
import re
from urllib.parse import urlsplit
api='https://www.csindex.com.cn/csindex-home/announcement/'
def get_period(m):
    p=dict(lang='cn',searchInput='沪深300',startDate=str(m.start_time.date()),endDate=str((m.end_time+pd.Timedelta(days=8)).date()),page=dict(key='',page=1,rows=100),classList=[],indexList=[],typeList=[],relatedTopics=[])
    candidates=requests.post(api+'queryAnnouncementByVo',json=p,timeout=20).json()['data']
    rows=[]
    for item in candidates:
        title=item['title']
        if item['noticeType']!='announcement' or '调整' not in title or not re.search('中证香港100|中证500|沪深300和中证|沪深300等指数样本',title): continue
        doc=requests.get(api+'queryAnnouncementById',params={'id':item['id']},timeout=20).json()['data']
        soup=BeautifulSoup(doc['content'],'html.parser')
        txt=soup.get_text(' ',strip=True)
        if not re.search(r'定期|更换\s*\d+\s*只',txt[:350]): continue
        path=CACHE/f"notice_{item['id']}.json";path.write_text(json.dumps(doc,ensure_ascii=False))
        urls=[a.get('href','') for a in soup.select('a[href]')]+[a.get('fileUrl','') for a in doc['enclosureList']]
        for j,url in enumerate(dict.fromkeys(urls)):
            ext=Path(urlsplit(url).path).suffix.lower()
            if ext not in ['.xls','.xlsx','.pdf'] or not url.startswith('https://oss-ch.csindex.com.cn/'):continue
            name=f"notice_{item['id']}_{j}{ext}";f=CACHE/name
            if not f.exists():
                r=requests.get(url,timeout=30)
                if r.status_code!=200:continue
                f.write_bytes(r.content)
            rows.append(dict(period=str(m),id=item['id'],published=item['publishDate'],title=title,body=txt[:400],url=url,attachment=name,sha256=hashlib.sha256(f.read_bytes()).hexdigest()))
    return rows
if __name__=='__main__':
    months=[m for m in pd.period_range('2017-05','2026-05',freq='M') if m.month in [5,11]]
    with ThreadPoolExecutor(4) as ex:r=[v for group in ex.map(get_period,months) for v in group]
    pd.DataFrame(r).to_csv(OUT/'official_notices.csv',index=False)
