from common import *
from decimal import Decimal, getcontext
import gzip
from bs4 import BeautifulSoup

def bounds(s):
    x=Decimal(s);half=Decimal(5).scaleb(x.as_tuple().exponent-1)
    return x-half,x+half

def run():
    getcontext().prec=40
    out=ROOT/'outputs/r284';rows=json.loads((out/'comparisons.json').read_text())
    summary=json.loads((out/'summary.json').read_text())
    ledger=json.loads((ROOT/'outputs/r38/download_ledger.json').read_text());texts=[]
    for doc in summary['documents']:
        source=next(x for x in ledger if x['url']==doc['url'] and x['status']=='saved')
        p=Path(source['path']);assert sha(p)==doc['raw_sha256'];b=p.read_bytes()
        if b[:2]==b'\x1f\x8b':b=gzip.decompress(b)
        body=BeautifulSoup(b,'html.parser').select_one('.content-wrapper #content')
        texts.append(''.join(body.get_text(' ',strip=True).split()))
        assert len(body.select('a[href]'))==len(doc['body_anchors'])==0
    assert {r['key'] for r in rows}=={p+'_'+k for p in ['month','year'] for k in ['total','ternary','lfp']}
    for r in rows:
        assert r['prior']['quote'] in texts[0] and r['current']['quote'] in texts[1]
        p0,p1=bounds(r['prior']['amount']);c0,c1=bounds(r['current']['amount']);a,b=bounds(r['current']['rate'])
        # Reverse the current amount and reported growth to bound the implied prior amount.
        low=c0/(1+b/100);high=c1/(1+a/100)
        assert (max(low,p0)<=min(high,p1))==r['rounding_compatible']
    assert summary['inconsistent']==['month_total','month_ternary','month_lfp']
    assert summary['compatible']==['year_total','year_ternary','year_lfp']
    receipt=json.loads((out/'receipt.json').read_text())
    for path,h in receipt['inputs'].items():assert sha(ROOT/path)==h
    for path,h in receipt['outputs'].items():assert sha(out/path)==h
    js(out/'independent_verification.json',dict(status='PASS',source_pages=2,verbatim_contexts=12,reverse_decimal_interval_checks=6,limitation='No first-release, revision cause or model benefit certification',verifier_sha256=sha(Path(__file__))))
    print('R284 VERIFIED: 2 source bodies, 12 contexts, 6 reverse intervals')
if __name__=='__main__':run()
