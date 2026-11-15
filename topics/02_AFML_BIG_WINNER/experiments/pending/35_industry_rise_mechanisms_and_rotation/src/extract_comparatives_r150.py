from pathlib import Path
import json,re,subprocess
from common import ROOT
r=ROOT;base=r/'data/cnequity_fundamental_review_20261114';out=r/'outputs/r150';ranges={'002406.SZ':(34,36),'002832.SZ':(52,54),'002948.SZ':(93,95),'003021.SZ':(56,59),'300411.SZ':(38,40),'300693.SZ':(69,71),'600236.SH':(46,48),'600955.SH':(28,30),'605123.SH':(36,38),'920407.BJ':(37,39)};facts=json.loads((r/'outputs/r149/candidate_facts.json').read_text());rows=[]
for sym,(lo,hi) in ranges.items():
 pages=[x for x in json.loads((base/sym/'pages.json').read_text()) if lo<=x['page']<=hi];(out/f'{sym}_table.txt').write_text('\n\n'.join('PAGE '+str(x['page'])+'\n'+x['text'] for x in pages));print(sym,[(x['page'],x['text'][:55]) for x in pages])
 for f in [x for x in facts if x['symbol']==sym and x['statement_type']=='balance']:
  number=f['source_reported_number'];found=[]
  for p in pages:
   for match in re.finditer(re.escape(number)+r'\s+([\d,]+(?:\.\d+)?)',p['text']):
    context=p['text'][max(0,match.start()-65):match.end()+10];found.append((p['page'],match.group(1),context))
  assert found,(sym,f['item_code']);first=found[0];rows.append(dict(symbol=sym,item_code=f['item_code'],current=f['amount_cny'],prior_reported=first[1],unit=f['source_unit_multiplier'],page=first[0],header_page=lo,context=first[2],all_matches=found,source_pdf=f['source_pdf'],source_pdf_sha256=f['source_pdf_sha256'],announce_date=f['announce_date'],fetched_at=f['original_pdf_fetched_at']))
(out/'extraction_candidates.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
print('CANDIDATES',len(rows))
