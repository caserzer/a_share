from common import *
from fractions import Fraction
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import gzip,re

def interval(s):
 v=Fraction(s);precision=10**len(s.split('.')[1]) if '.' in s else 1;half=Fraction(1,2*precision);return v-half,v+half

def run():
 o=ROOT/'outputs/r278';rows=json.loads((o/'comparisons.json').read_text());reg=json.loads((ROOT/'outputs/r276/export_registry.json').read_text());lookup={r['month']:r for r in reg};selectors=json.loads((ROOT/'protocols/r274.json').read_text())['selectors'];sourcechecks=0;paired=0;counts={}
 for row in rows:
  r=lookup[row['month']];path=ROOT/'data/r38_battery_originals'/f"{r['raw_sha256']}.html";assert sha(path)==r['raw_sha256'];raw=path.read_bytes();soup=BeautifulSoup(gzip.decompress(raw) if raw[:2]==b'\x1f\x8b' else raw,'html.parser');host=urlparse(r['url']).netloc;nodes=soup.select('.News-Content > div:first-child' if host=='www.aqsiqauto.com' else selectors[host]);assert len(nodes)==1;body=''.join(nodes[0].get_text(' ',strip=True).split())
  for quote in row['quotes']:
   assert quote['sentence'] in body
   token=row['reported_rate_token']
   if token is not None:
    sign='下降|减少' if token.startswith('-') else '增长|上升|增加';assert re.search('同比('+sign+')'+re.escape(token.lstrip('-'))+'%',quote['sentence'])
  sourcechecks+=1
  if row['status'] in ['rounding_compatible','inconsistent_beyond_rounding']:
   c0,c1=interval(row['current_amount_token']);p0,p1=interval(row['prior_amount_token']);r0,r1=[x/100 for x in interval(row['reported_rate_token'])]
   # Solve for prior rather than comparing derived growth bounds.
   implied0=c0/(1+r1);implied1=c1/(1+r0);compatible=max(implied0,p0)<=min(implied1,p1)
   assert compatible==(row['status']=='rounding_compatible')
   for field,value in [('implied_prior_low',implied0),('implied_prior_high',implied1),('derived_yoy_low',c0/p1-1),('derived_yoy_high',c1/p0-1)]:assert abs(Fraction(row[field])-value)<Fraction(1,10**35)
   q=lookup[row['prior_month']];assert q['raw_sha256']==row['prior_sha256'];assert str(q['export_gwh'])==row['prior_amount_token'];assert row['audit_available_at']==max(r['available_at'],q['available_at']);paired+=1
  counts[row['status']]=counts.get(row['status'],0)+1
 # Fixed arithmetic examples include decrease and conservative endpoint contact.
 assert interval('-5.0')==(Fraction(-101,20),Fraction(-99,20));assert interval('11.8')==(Fraction(47,4),Fraction(237,20));assert max(Fraction(0),Fraction(1))<=min(Fraction(1),Fraction(2))
 receipt=json.loads((o/'receipt.json').read_text())
 for f,h in receipt['inputs'].items():assert sha(ROOT/f)==h
 for f,h in receipt['outputs'].items():assert sha(o/f)==h
 js(o/'independent_verification.json',dict(status='PASS',original_source_documents=sourcechecks,independent_rational_interval_pairs=paired,classification_counts=counts,scope='Original source quotes and signed percent; exact rational implied-denominator interval verification; not revision-cause identification'))
 print('PASS',sourcechecks,paired,counts)
if __name__=='__main__':run()
