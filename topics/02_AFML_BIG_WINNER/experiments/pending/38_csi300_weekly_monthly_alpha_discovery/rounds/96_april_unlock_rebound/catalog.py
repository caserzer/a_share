from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import json,time,math,re,requests,sys
import pandas as pd
here=Path(__file__).resolve().parent
out=here/"results"
sys.path.insert(0,str(here.parent/"02_adaptive_revision"))
from evaluate import PRIVATE
from core import sha,dump
member_file=PRIVATE/"daily_members.parquet"
members=pd.read_parquet(member_file)
url="https://www.cninfo.com.cn/new/hisAnnouncement/query"
def query(window):
    year,word,*interval=window
    start,end=(interval[:2] or [1,30])
    plate=interval[2] if len(interval)>2 else ""
    order=interval[3] if len(interval)>3 else "asc"
    tag=('' if not interval else f'_{start:02}_{end:02}')+plate+('desc' if order=='desc' else '')
    rows=[];pages=[]
    for i in range(1,100):
        file=out/"catalog"/f"{year}_{word}{tag}_{i}.json"
        params=dict(pageNum=i,pageSize=30,column="szse",plate=plate,tabName="fulltext",stock="",searchkey=word,seDate=f"{year}-04-{start:02}~{year}-04-{end:02}",isHLtitle="false",sortName="time",sortType=order)
        if not file.exists():
            r=requests.post(url,data=params,timeout=25)
            r.raise_for_status()
            obj=r.json()
            assert isinstance(obj.get("totalAnnouncement"),int)
            file.write_bytes(r.content)
            time.sleep(.14)
        obj=json.loads(file.read_bytes())
        if i==1:total=obj["totalAnnouncement"]
        assert obj["totalAnnouncement"]==total
        rows.extend(obj["announcements"] or [])
        pages.append(file)
        if i>=max(1,math.ceil(total/30)):break
    assert len(rows)==total
    if len({(x["announcementId"],x["secCode"]) for x in rows})!=total:
        if start==end and not plate:
            sh,sp=query((year,word,start,end,"sh"))
            sz,zp=query((year,word,start,end,"sz"))
            bj,bp=query((year,word,start,end,"bj"))
            # The original query can also include issuers outside these two boards.
            merged={(x["announcementId"],x["secCode"]):x for x in rows+sh+sz+bj}
            assert len(merged)==total,(year,word,start,total,len(merged))
            return list(merged.values()),pages+sp+zp+bp
        if start==end and plate:
            if order=="desc":return rows,pages
            desc,dp=query((year,word,start,end,plate,"desc"))
            merged={(x["announcementId"],x["secCode"]):x for x in rows+desc}
            if len(merged)!=total and plate in ("sz","sh"):
                for sub in (["szmb","szcy"] if plate=="sz" else ["shmb","shkcp"]):
                    extra,ep=query((year,word,start,end,sub))
                    dp+=ep
                    merged.update({(x["announcementId"],x["secCode"]):x for x in extra})
            assert len(merged)==total,(year,word,start,plate,total,len(merged))
            return list(merged.values()),pages+dp
        mid=(start+end)//2
        left,lp=query((year,word,start,mid))
        right,rp=query((year,word,mid+1,end))
        assert len(left)+len(right)==total
        return left+right,pages+lp+rp
    return rows,pages
jobs=[(y,w) for y in range(2018,2027) for w in ["上市流通","解除限售"]]
allrows=[];files=[];counts=[]
with ThreadPoolExecutor(max_workers=3) as pool:
    for job,(records,pages) in zip(jobs,pool.map(query,jobs)):
        counts.append(dict(year=job[0],query=job[1],documents=len(records),pages=len(pages)))
        allrows.extend(records);files.extend(pages)
a=pd.DataFrame(allrows).drop_duplicates(["announcementId","secCode"])
a["title"]=a.announcementTitle.map(lambda v:re.sub("<[^>]+>","",v))
a["notice"]=pd.to_datetime(a.announcementTime,unit="ms",utc=True).dt.tz_convert("Asia/Shanghai").dt.tz_localize(None).dt.normalize()
a["filedate"]=pd.to_datetime(a.adjunctUrl.str.extract(r"(\d{4}-\d{2}-\d{2})")[0])
a["known"]=a[["notice","filedate"]].max(axis=1)
assert a.notice.dt.month.eq(4).all()
a["instrument"]=a.secCode.map(lambda x:("SH" if x.startswith("6") else "SZ")+x)
a["member"]=[bool(members.at[members.index[members.index.searchsorted(d,side="right")-1],c]) if c in members.columns else False for c,d in zip(a.instrument,a.known)]
a["selected"]=a.member & a.title.str.contains("限售|上市流通|解锁") & a.title.str.contains("公告") & ~a.title.str.contains("法律意见|核查意见|独立意见|董事会决议|监事会决议|律师事务所")
a["url"]="https://static.cninfo.com.cn/"+a.adjunctUrl.str.lstrip("/")
a[["announcementId","instrument","title","notice","filedate","known","member","selected","url"]].sort_values(["known","instrument"]).to_csv(out/"catalog.csv",index=False)
pd.DataFrame(counts).to_csv(out/"counts.csv",index=False)
dump(out/"catalog_receipt.json",{str(f):sha(f) for f in [here/"PROTOCOL.md",Path(__file__),member_file,*files,out/"counts.csv",out/"catalog.csv"]})
