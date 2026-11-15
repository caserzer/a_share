"""Explicit user-authorized bounded public document acquisition; not a scheduler."""
import urllib.request
from datetime import datetime,timezone
from common import *

def download(url):
 out=ROOT/'outputs/r38';raw=ROOT/'data/r38_battery_originals';out.mkdir(exist_ok=True);raw.mkdir(exist_ok=True)
 auth=json.loads((ROOT/'outputs/r37/external_data_request.json').read_text());assert auth['status']=='explicitly_authorized'
 ledger=out/'download_ledger.json';rows=json.loads(ledger.read_text()) if ledger.exists() else []
 if any(x['url']==url and x['status']=='saved' for x in rows):return
 used=sum(x.get('bytes_read',0) for x in rows);assert len(rows)<100 and used<100000000
 record=dict(url=url,retrieved_at=datetime.now(timezone.utc).isoformat(),bytes_read=0,status='attempt')
 try:
  req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0 EP35-public-research'})
  with urllib.request.urlopen(req,timeout=45) as response:
   record['http_status']=response.status;record['final_url']=response.url;record['content_type']=response.headers.get('Content-Type');chunks=[]
   while True:
    b=response.read(min(65536,100000000-used-record['bytes_read']))
    if not b:break
    chunks.append(b);record['bytes_read']+=len(b)
    if used+record['bytes_read']>=100000000:raise ValueError('authorized byte limit reached')
   data=b''.join(chunks);digest=hashlib.sha256(data).hexdigest();path=raw/(digest+('.pdf' if data.startswith(b'%PDF') else '.html'));path.write_bytes(data);record.update(status='saved',sha256=digest,path=str(path))
 except Exception as e:record.update(status='failed',error=type(e).__name__+': '+str(e))
 rows.append(record);js(ledger,rows);print(json.dumps(record,ensure_ascii=False),flush=True)
if __name__=='__main__':
 import sys
 for url in sys.argv[1:]:download(url)
