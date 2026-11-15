"""Only the five explicitly authorized R08 public original reports."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
import requests
from common import *

def run():
    request=ROOT/'outputs/r08/external_document_request.json'
    docs=json.loads(request.read_text())['documents']
    dest=ROOT/'data/primary_documents';dest.mkdir(parents=True,exist_ok=True)
    def fetch(d):
        rec=dict(ts_code=d['ts_code'],url=d['url'],expected_sha256=d['expected_sha256'],fetched_at=datetime.now(timezone.utc).isoformat())
        try:
            response=requests.get(d['url'],timeout=(15,60));response.raise_for_status();data=response.content
            if not data.startswith(b'%PDF-'):raise ValueError('response is not PDF')
            digest=hashlib.sha256(data).hexdigest();path=dest/f"{d['ts_code']}_{digest}.pdf"
            if not path.exists():path.write_bytes(data)
            rec.update(status='downloaded',path=str(path),sha256=digest,bytes=len(data),matches_expected=digest==d['expected_sha256'],final_url=response.url)
        except Exception as e:rec.update(status='failed',error=str(e))
        return rec
    with ThreadPoolExecutor(max_workers=5) as pool:records=list(pool.map(fetch,docs))
    js(ROOT/'outputs/r08/authorized_download_receipt.json',dict(authorization='User explicitly allowed these five public reports in current chat; no other collection authorized',request_sha256=sha(request),documents=records))
    for rec in records:print(rec['ts_code'],rec['status'],rec.get('matches_expected'),rec.get('error',''),flush=True)
if __name__=='__main__':run()
