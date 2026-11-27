"""Probe the regulator disclosure index and verify response completeness before admitting original versions."""
import os,json,requests,time,hashlib
from pathlib import Path
import pandas as pd
from concurrent.futures import ThreadPoolExecutor
O=Path(__file__).resolve().parents[1]/'outputs/fundamental/originals';O.mkdir(exist_ok=True,parents=True)
URL='https://www.cninfo.com.cn/new/hisAnnouncement/query'
def query(stock,org):
    s=requests.Session();s.trust_env=False
    out=O/(stock+'.json')
    body=dict(pageNum=1,pageSize=30,tabName='fulltext',column='szse',stock=stock+','+org,
             category='category_ndbg_szsh;category_bndbg_szsh;category_yjdbg_szsh;category_sjdbg_szsh',searchkey='',seDate='2013-01-01~2026-10-12',sortName='time',sortType='desc',isHLtitle='true')
    ans=[];status=''
    try:
        for page in range(1,51):
            body['pageNum']=page
            r=s.post(URL,data=body,timeout=(7,15),headers={'User-Agent':'Mozilla/5.0','Referer':'https://www.cninfo.com.cn/'})
            r.raise_for_status();res=r.json();a=res.get('announcements') or []
            if not a or any(i['secCode']!=stock for i in a):raise ValueError('empty or mismatched issuer')
            ans.extend(a)
            if len(ans)>=res['totalAnnouncement']:break
        if len({i['announcementId'] for i in ans})!=res['totalAnnouncement']:raise ValueError('pagination counts')
        status='complete_index'
    except Exception as e:status=type(e).__name__+' '+str(e)
    out.write_text(json.dumps(dict(source=URL,issuer=stock,status=status,observed_at=pd.Timestamp.now(tz='UTC').isoformat(),items=ans),ensure_ascii=False))
    print(stock,status,len(ans),flush=True)
if __name__=='__main__':
    with ThreadPoolExecutor(3) as ex:list(ex.map(lambda v:query(*v),[('600036','gssh0600036'),('000001','gssz0000001'),('600236','gssh0600236')]))
