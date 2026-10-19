"""Read-only official disclosure searches for original and amended guidance."""
import json
import requests
from prepare_panel import OUT
from build_margin_information import digest
DEST=OUT/'r37_company_guidance_probe'
CACHE=OUT/'local_cache/r37_cninfo_guidance'


def run():
    CACHE.mkdir(exist_ok=True);receipts=[]
    path=CACHE/'stock_directory.json';url='https://www.cninfo.com.cn/new/data/szse_stock.json'
    if not path.exists():
        r=requests.get(url,timeout=30);r.raise_for_status();path.write_bytes(r.content)
    directory=json.loads(path.read_text());codes={r['code']:r['orgId'] for r in directory['stockList']}
    receipts.append(dict(url=url,method='GET',path=str(path),sha256=digest(path)))
    results=[]
    for code in ['300520','300663']:
        params=dict(pageNum=1,pageSize=30,column='szse',tabName='fulltext',plate='',stock=f'{code},{codes[code]}',
                    searchkey='',secid='',category='category_yjygjxz_szsh',trade='',seDate='2025-01-01~2025-04-30',
                    sortName='',sortType='',isHLtitle='false')
        path=CACHE/f'{code}_2025.json';url='https://www.cninfo.com.cn/new/hisAnnouncement/query'
        if not path.exists():
            r=requests.post(url,data=params,timeout=30);r.raise_for_status();path.write_bytes(r.content)
        data=json.loads(path.read_text());assert len(data['announcements'])==data['totalAnnouncement']
        receipts.append(dict(url=url,method='POST read-only search',params=params,path=str(path),sha256=digest(path)))
        results.append(dict(code=code,total=data['totalAnnouncement'],announcements=data['announcements']))
    (DEST/'cninfo_archive_probe.json').write_text(json.dumps(dict(receipts=receipts,results=results),indent=2)+'\n')
    print(json.dumps(results,indent=2,ensure_ascii=False))


if __name__=='__main__':run()
