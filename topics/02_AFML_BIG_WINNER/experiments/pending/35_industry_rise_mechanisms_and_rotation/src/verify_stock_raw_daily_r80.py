import zlib
from collections import Counter
from common import *

def run():
 out=ROOT/'outputs/r80';rec=json.loads((out/'receipt.json').read_text())
 for p,h in rec['reads'].items():assert sha(p)==h,p
 prior=json.loads((ROOT/'outputs/r79/missing_dates.json').read_text());wanted={(x['security_id'],x['date'][:10]):x for x in prior}
 aliases={}
 for x in json.loads((ROOT/'outputs/r79/intervals.json').read_text()):aliases.setdefault(x['security_id'],set()).update(x['instruments'])
 sources=json.loads((out/'sources.json').read_text());bydate={x['date']:x for x in sources};assert len(sources)==len(bydate)
 records={}
 for x in sources:
  items=[]
  for h in x['original_sha256']:
   p=next(Path(p) for p in rec['reads'] if Path(p).name==h)
   wire=p.read_bytes();body=zlib.decompress(wire[21:]).decode();fields=body.split('\x01');assert fields[0]=='0'
   names=fields[-1].split(',');data=json.loads(fields[-2])['record'];items.extend(dict(zip(names,row)) for row in data)
  assert len(items)==x['rows']
  for item in items:
   assert item['date']==x['date'];code=item['code'];instrument=code[:2].upper()+code[3:];records.setdefault((x['date'],instrument),[]).append(item)
 actual=json.loads((out/'date_audit.json').read_text());assert len(actual)==len(wanted);seen=set();counts=Counter();trade=Counter()
 for row in actual:
  key=(row['security_id'],row['date']);assert key not in seen;seen.add(key);assert key in wanted
  assert row['position']==wanted[key]['position'];assert set(row['instruments'])==aliases[key[0]]
  expected=[]
  for alias in sorted(aliases[key[0]]):expected.extend(dict(**v,instrument=alias) for v in records.get((key[1],alias),[]))
  status='no_local_daily_archive' if key[1] not in bydate else 'matching_raw_record' if expected else 'no_record_for_observed_aliases'
  assert row['status']==status;assert sorted(row['matches'],key=lambda x:x['code'])==sorted(expected,key=lambda x:x['code'])
  counts[status]+=1;trade.update(x['tradestatus'] for x in expected)
 assert seen==set(wanted)
 s=json.loads((out/'summary.json').read_text());assert s['status_counts']==dict(counts) and s['matched_trade_statuses']==dict(trade)
 assert s['unique_stock_dates']==len(wanted) and s['covered_dates']==len(sources)
 js(out/'verification.json',dict(status='PASS',scope='all target stock dates and all covered original response records',stock_dates=len(wanted),covered_dates=len(sources),receipt_sha256=sha(out/'receipt.json'),verifier_sha256=sha(Path(__file__))))
 print('R80 VERIFIED',len(wanted),len(sources))
if __name__=='__main__':run()
