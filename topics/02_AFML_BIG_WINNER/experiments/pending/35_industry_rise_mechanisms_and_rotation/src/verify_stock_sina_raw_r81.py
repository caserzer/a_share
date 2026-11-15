from datetime import datetime
from zoneinfo import ZoneInfo
from collections import Counter
from py_mini_racer import py_mini_racer
from akshare.stock.stock_zh_a_sina import hk_js_decode
from common import *
def run():
 out=ROOT/'outputs/r81';rec=json.loads((out/'receipt.json').read_text())
 for p,h in rec['reads'].items():assert sha(p)==h,p
 for p in rec['missing_archives']:assert not Path(p).exists(),p
 assert hashlib.sha256(hk_js_decode.encode()).hexdigest()==rec['decoder_sha256']
 engine=py_mini_racer.MiniRacer();engine.eval(hk_js_decode);lookup={};rowcount=0
 for source in json.loads((out/'sources.json').read_text()):
  text=Path(source['archive_path']).read_text(encoding='utf-8-sig');encoded=text[text.index('=')+1:text.index(';')].strip().strip('"');records=engine.call('d',encoded);bydate={}
  for x in records:
   dt=datetime.fromisoformat(x['date'].replace('Z','+00:00')).astimezone(ZoneInfo('Asia/Shanghai')).date().isoformat();assert dt not in bydate
   bydate[dt]={k:v for k,v in x.items() if k!='date'}
  assert len(records)==source['full_decoded_rows'];lookup[source['instrument']]=bydate;rowcount+=len(records)
 aliases={}
 for x in json.loads((ROOT/'outputs/r79/intervals.json').read_text()):aliases.setdefault(x['security_id'],set()).update(x['instruments'])
 wanted={(x['security_id'],x['date'][:10]):x for x in json.loads((ROOT/'outputs/r79/missing_dates.json').read_text())}
 actual=json.loads((out/'date_audit.json').read_text());seen=set();counts=Counter()
 for x in actual:
  key=(x['security_id'],x['date']);assert key in wanted and key not in seen;seen.add(key)
  assert set(x['instruments'])==aliases[key[0]] and x['position']==wanted[key]['position']
  avail=sorted(a for a in aliases[key[0]] if a in lookup);assert avail==x['available_instruments'];matches=[]
  for a in avail:
   if key[1] in lookup[a]:matches.append(dict(instrument=a,**lookup[a][key[1]]))
  assert matches==x['matches'];status='no_local_security_archive' if not avail else 'matching_raw_record' if matches else 'date_absent_from_available_archives';assert x['status']==status;counts[status]+=1
 assert seen==set(wanted)
 s=json.loads((out/'summary.json').read_text());assert s['status_counts']==dict(counts) and s['decoded_original_rows']==rowcount and s['unique_stock_dates']==len(wanted)
 assert s['affected_securities']==len(aliases) and s['available_archives']==len(lookup) and s['missing_archives']==len(rec['missing_archives'])
 js(out/'verification.json',dict(status='PASS',stock_dates=len(wanted),original_rows=rowcount,scope='all target dates; original response dates independently normalized; same pinned vendor decoder',verifier_sha256=sha(Path(__file__)),receipt_sha256=sha(out/'receipt.json')))
 print('R81 VERIFIED',len(wanted),rowcount)
if __name__=='__main__':run()
