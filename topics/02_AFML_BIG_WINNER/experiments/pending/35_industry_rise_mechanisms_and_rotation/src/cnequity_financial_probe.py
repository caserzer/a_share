"""Narrow financial source probe using CNEquity's report schema and parser."""
import json,time,hashlib
from datetime import datetime,timezone
from cnequity_probe import ROOT,OUT,DATA
from cnequity.adapters.eastmoney.fundamentals import _REPORTS,_parse_rows
from cnequity.adapters.eastmoney.datacenter import fetch_datacenter
from cnequity.adapters.eastmoney.em_auth import EastMoneyClient
symbols=[r['symbol'] for r in json.loads((OUT/'sample.json').read_text())['sample']]
dest=DATA/'financials';dest.mkdir(exist_ok=True,parents=True);rawlog=[]
def hook(r):
 r.read();p=dest/f'http_{len(rawlog)}.bin';p.write_bytes(r.content);rawlog.append(dict(url=str(r.request.url),status=r.status_code,path=str(p.relative_to(ROOT)),sha256=hashlib.sha256(r.content).hexdigest()))
c=EastMoneyClient(timeout_sec=15);c._client.event_hooks['response']=[hook];results=[]
protocol=dict(symbols=symbols,period='2026-06-30',reports=[r.name for r in _REPORTS[:4]],scope='CNEquity datacenter adapter and private schema/parser; not full financial pipeline or strict PIT',collected_at=datetime.now(timezone.utc).isoformat())
(OUT/'financial_protocol.json').write_text(json.dumps(protocol,indent=2))
try:
 for report in _REPORTS[:4]:
  expr='(SECUCODE in ('+','.join('"'+s+'"' for s in symbols)+'))('+report.report_date_field+"='2026-06-30')"
  t=time.monotonic();r=dict(report=report.name,filter=expr)
  try:
   raw=fetch_datacenter(c,report.name,report.columns,filter_expr=expr,page_size=100,max_retries=1)
   (dest/(report.name+'_raw.json')).write_text(json.dumps(raw,ensure_ascii=False,indent=2))
   rows,_=_parse_rows(raw,report,default_notice='')
   (dest/(report.name+'_parsed.json')).write_text(json.dumps(rows,ensure_ascii=False,indent=2,default=str))
   r.update(status='nonempty' if rows else 'empty',raw_rows=len(raw),parsed_rows=len(rows),counts={s:sum(x['symbol']==s for x in rows) for s in symbols},notice_dates=sorted(set(str(x['announce_date']) for x in rows)))
  except Exception as e:r.update(status='error',error=str(e))
  r['elapsed_seconds']=round(time.monotonic()-t,3);results.append(r);print(r,flush=True)
finally:c.close()
(OUT/'financial_results.json').write_text(json.dumps(dict(results=results,http=rawlog),ensure_ascii=False,indent=2))
