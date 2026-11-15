"""Fixed ten-stock original disclosure review. New directory, preserved first probe."""
import json,time,hashlib,sys,concurrent.futures
from datetime import datetime,timezone
from pathlib import Path
import httpx
from pypdf import PdfReader
from cnequity.adapters.cninfo.payment_notices import _stock_directory
from cnequity.adapters.cninfo.financial_originals import original_report_notice,parse_report_pdf
from cnequity.adapters.cninfo.announcements import post_with_retry
from cnequity.adapters.eastmoney.datacenter import fetch_datacenter
from cnequity.adapters.eastmoney.em_auth import EastMoneyClient
from cnequity.adapters.eastmoney import shareholders as sh
from cnequity_probe import ROOT
OUT=ROOT/'outputs/cnequity_fundamental_review_20261114';DATA=ROOT/'data/cnequity_fundamental_review_20261114'
OUT.mkdir(exist_ok=True);DATA.mkdir(exist_ok=True)
sample=json.loads((ROOT/'outputs/cnequity_probe_20261114/sample.json').read_text())['sample']
def dump(p,o):p.write_text(json.dumps(o,ensure_ascii=False,indent=2,default=str))
def originals():
 with httpx.Client(timeout=30,headers={'User-Agent':'Mozilla/5.0'}) as c:directory=_stock_directory(c,config=None)[0]
 dump(DATA/'directory_subset.json',{s['symbol']:directory.get(s['symbol'][:6]) for s in sample})
 def one(s):
  sym=s['symbol'];d=DATA/sym;d.mkdir(exist_ok=True);r=dict(**s,fetched_at=datetime.now(timezone.utc).isoformat());records=[];t=time.monotonic()
  try:
   with httpx.Client(timeout=30,headers={'User-Agent':'Mozilla/5.0'}) as c:
    for page in range(1,11):
     body=dict(pageNum=page,pageSize=30,column='szse',tabName='fulltext',plate='',stock=f'{sym[:6]},{directory[sym[:6]]}',searchkey='',secid='',category='',trade='',seDate='2026-07-01~2026-09-30')
     def capture(resp,*args): (d/f'query_{page}.json').write_bytes(resp.content)
     obj=post_with_retry(c,'https://www.cninfo.com.cn/new/hisAnnouncement/query',data=body,on_response=capture)
     records.extend(obj.get('announcements') or []);total=obj.get('totalRecordNum')
     if total is None:raise ValueError('no declared query count')
     if len(records)>=total:break
    assert len(records)==total
    assert all(x.get('secCode')==sym[:6] for x in records)
    notice=original_report_notice(records,sym[:6],2026,quarter=2);r['notice']=notice;r['query_records']=total
    url='https://static.cninfo.com.cn/'+notice['adjunctUrl'];resp=c.get(url);resp.raise_for_status();payload=resp.content
    assert payload.startswith(b'%PDF');p=d/'2026H1.pdf';p.write_bytes(payload);r.update(pdf_url=url,pdf_sha256=hashlib.sha256(payload).hexdigest())
   reader=PdfReader(p);pages=[]
   for i,pg in enumerate(reader.pages):pages.append(dict(page=i+1,text=pg.extract_text() or ''))
   dump(d/'pages.json',pages)
   (d/'text.txt').write_text('\n'.join(f"\n---PAGE {x['page']}---\n{x['text']}" for x in pages))
   try:
    parsed=parse_report_pdf(payload,sym,2026,quarter=2);dump(d/'parsed_original.json',parsed);r['parsed_rows']=len(parsed)
   except Exception as e:r['parser_error']=str(e)
   r.update(status='downloaded',pages=len(pages))
  except Exception as e:r.update(status='error',error=f'{type(e).__name__}: {e}')
  r['seconds']=round(time.monotonic()-t,2);dump(d/'receipt.json',r);print(sym,r['status'],r.get('parsed_rows'),r.get('error'),r.get('parser_error'),flush=True);return r
 with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:r=list(pool.map(one,sample))
 dump(OUT/'original_receipts.json',r)
def holders():
 syms=[s['symbol'] for s in sample];c=EastMoneyClient(timeout_sec=15);r=[]
 try:
  for name,cols in [(sh._HOLDERNUM_REPORT,sh._HOLDERNUM_COLUMNS),(sh._HOLDERS_REPORT,sh._HOLDERS_COLUMNS),(sh._FREEHOLDERS_REPORT,sh._FREEHOLDERS_COLUMNS)]:
   expr='(SECUCODE in ('+','.join('"'+s+'"' for s in syms)+'))(END_DATE=\'2026-06-30\')'
   captures=[]
   def hook(resp):
    resp.read();p=DATA/f'{name}_http_{len(captures)}.bin';p.write_bytes(resp.content);captures.append(dict(url=str(resp.request.url),status=resp.status_code,path=str(p.relative_to(ROOT)),sha256=hashlib.sha256(resp.content).hexdigest()))
   c._client.event_hooks['response']=[hook]
   try:
    raw=fetch_datacenter(c,name,cols,filter_expr=expr,page_size=500,max_retries=1);dump(DATA/f'{name}.json',raw);rr=dict(report=name,rows=len(raw),counts={s:sum(x.get('SECUCODE')==s for x in raw) for s in syms},http=captures)
   except Exception as e:rr=dict(report=name,error=str(e),http=captures)
   r.append(rr);print(name,rr.get('rows'),rr.get('error'),flush=True)
 finally:c.close()
 dump(OUT/'holder_receipts.json',r)
if __name__=='__main__':
 dump(OUT/'protocol.json',dict(sample=sample,report_period='2026H1',original_query_window=['2026-07-01','2026-09-30'],scope='financial statement values and disclosure dates; shareholder counts and top holders; no price tests',strict_pit_certified=False))
 if len(sys.argv)>1 and sys.argv[1]=='holders':holders()
 else:originals()
