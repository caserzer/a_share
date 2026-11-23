from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import re,hashlib,json,time
import pandas as pd
import sys
try:
    import pymupdf
except ImportError:
    sys.path.append(str(next(Path("/home/xiaolv/anaconda3/envs/deep/lib").glob("python*/site-packages/pymupdf")).parent))
    import pymupdf
import requests
here=Path(__file__).resolve().parent
out=here/"results"
a=pd.read_csv(out/"catalog.csv",dtype={"announcementId":str}).query("selected")
def fetch(row):
    path=out/"pdf"/(row.announcementId+".pdf")
    if not path.exists():
        for attempt in range(3):
            try:
                r=requests.get(row.url,timeout=22)
                r.raise_for_status()
                assert r.content.startswith(b"%PDF")
                path.write_bytes(r.content)
                break
            except (AssertionError,requests.RequestException):
                if attempt==2:return dict(id=row.announcementId,status="unavailable")
                time.sleep(1)
    doc=pymupdf.open(path)
    hits=[]
    for i,page in enumerate(doc):
        t=re.sub(r"\s+","",page.get_text())
        expr=r"(?:本次[^。；，：:]{0,20}?(?:上市流通日期|上市流通时间|上市日期|上市日|上市流通日)|上市流通(?:的日期|的时间|日期|时间|日)|可上市流通日|解除限售股份的上市日期|上市流通安排[：:]?1[、.](?:本次)?(?:解除限售股份)?(?:上市时间|上市日期))[^。；，\d]{0,9}?(20\d{2})年(\d{1,2})月(\d{1,2})日"
        for m in re.finditer(expr,t):
            hits.append((pd.Timestamp(*map(int,m.groups())),i+1,m.group()))
        for m in re.finditer(r"(?:本次(?:解除限售|解禁|上市流通)[^。；]{0,24}?(?:将于|于))(20\d{2})年(\d{1,2})月(\d{1,2})日(?:起)?上市流通",t):
            hits.append((pd.Timestamp(*map(int,m.groups())),i+1,m.group()))
    dates=sorted({h[0] for h in hits})
    return dict(id=row.announcementId,status="unique" if len(dates)==1 else ("multiple" if dates else "unresolved"),
                unlock=str(dates[0].date()) if len(dates)==1 else "",page=hits[0][1] if hits else None,
                evidence=" | ".join(dict.fromkeys(h[2] for h in hits)),sha256=hashlib.sha256(path.read_bytes()).hexdigest())
with ThreadPoolExecutor(max_workers=4) as pool:
    records=list(pool.map(fetch,a.itertuples()))
a=a.merge(pd.DataFrame(records),left_on="announcementId",right_on="id",validate="1:1")
a.to_csv(out/"documents.csv",index=False)
print(a.status.value_counts().to_string())
