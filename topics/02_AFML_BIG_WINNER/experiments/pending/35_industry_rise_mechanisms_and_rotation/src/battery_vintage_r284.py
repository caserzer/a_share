from common import *
from bs4 import BeautifulSoup
from fractions import Fraction
import gzip,re

def interval(token):
    step=Fraction(1,2*10**(len(token.split('.')[1]) if '.' in token else 0))
    return Fraction(token)-step,Fraction(token)+step

def run():
    out=ROOT/'outputs/r284';out.mkdir(exist_ok=True)
    ledger=json.loads((ROOT/'outputs/r38/download_ledger.json').read_text())
    saved=[r for r in ledger if r['status']=='saved']
    for r in saved:
        p=Path(r['path']);assert sha(p)==r['sha256'] and p.stat().st_size==r['bytes_read']
    total=sum(r['bytes_read'] for r in ledger)
    assert len(saved)<=100 and total<=100000000
    urls=json.loads((ROOT/'protocols/r284.json').read_text())['source_scope']
    docs=[];values=[]
    for url in urls:
        r=next(x for x in saved if x['url']==url)
        raw=Path(r['path']).read_bytes();decoded=gzip.decompress(raw) if raw[:2]==b'\x1f\x8b' else raw
        soup=BeautifulSoup(decoded,'html.parser');body=soup.select_one('.content-wrapper #content');assert body
        text=''.join(body.get_text(' ',strip=True).split()).split('装车量方面：',1)[1]
        anchors=[dict(text=a.get_text(' ',strip=True),href=a['href']) for a in body.select('a[href]')]
        docs.append(dict(url=url,raw_sha256=r['sha256'],body_anchors=anchors))
        doc={}
        for period,chunk in [('month',text.split('1-12月')[0]),('year',text.split('1-12月')[1])]:
            for kind,pattern in [('total',r'(?:我国|国内)动力电池(?:累计)?装车量'),('ternary',r'三元电池(?:累计)?装车量'),('lfp',r'磷酸铁锂电池(?:累计)?装车量')]:
                matches=list(re.finditer(pattern+r'(\d+(?:\.\d+)?)GWh[^。；]*?(?:累计)?同比增长(\d+(?:\.\d+)?)%',chunk))
                # The 2024 monthly ternary rate is a decline; it is not the target rate.
                if not matches:
                    matches=list(re.finditer(pattern+r'(\d+(?:\.\d+)?)GWh[^。；]*?同比下降(\d+(?:\.\d+)?)%',chunk))
                assert len(matches)==1,(url,period,kind)
                m=matches[0];doc[period+'_'+kind]=dict(amount=m[1],rate=m[2],quote=m[0])
        values.append(doc)
    comparisons=[]
    for key,c in values[1].items():
        p=values[0][key];c0,c1=interval(c['amount']);p0,p1=interval(p['amount']);r0,r1=[x/100 for x in interval(c['rate'])]
        lo=c0/p1-1;hi=c1/p0-1;ok=max(lo,r0)<=min(hi,r1)
        comparisons.append(dict(key=key,prior=p,current=c,derived_interval=[float(lo),float(hi)],reported_interval=[float(r0),float(r1)],rounding_compatible=ok))
    js(out/'comparisons.json',comparisons)
    js(out/'summary.json',dict(status='PASS',documents=docs,comparisons=len(comparisons),inconsistent=[x['key'] for x in comparisons if not x['rounding_compatible']],compatible=[x['key'] for x in comparisons if x['rounding_compatible']],saved_documents=len(saved),bytes_read=total,remaining_documents=100-len(saved),remaining_bytes=100000000-total,new_raw_downloads=0,models_refit=0,cause='unresolved',strict_pit=False))
    reads=['protocols/r284.json','src/battery_vintage_r284.py','outputs/r38/download_ledger.json','outputs/r284/search_response.json']
    js(out/'receipt.json',dict(inputs={s:sha(ROOT/s) for s in reads},outputs={s:sha(out/s) for s in ['comparisons.json','summary.json']}))
    print([(r['key'],r['rounding_compatible']) for r in comparisons])
if __name__=='__main__':run()
