import gzip
from bs4 import BeautifulSoup
from common import *
def run():
 out=ROOT/'outputs/r38';ledger=json.loads((out/'download_ledger.json').read_text());saved=[x for x in ledger if x['status']=='saved'];total=sum(x['bytes_read'] for x in ledger)
 assert len(saved)<=100 and total<=100000000 and len({x['url'] for x in saved})==len(saved)
 extracted=json.loads((out/'extractions.json').read_text());assert len(extracted)==len(saved);lookup={x['url']:x for x in extracted}
 for x in saved:
  p=Path(x['path']);assert p.stat().st_size==x['bytes_read'] and sha(p)==x['sha256'];raw=p.read_bytes();decoded=gzip.decompress(raw) if raw[:2]==b'\x1f\x8b' else raw;r=lookup[x['url']];assert hashlib.sha256(decoded).hexdigest()==r['decoded_sha256'] and r['raw_sha256']==x['sha256']
  assert r['economic_month'] is None or '2020-01'<=r['economic_month']<='2026-09'
  assert (r['value_gwh'] is not None)==(len(r['values'])==1)
 grid=json.loads((out/'month_coverage.json').read_text());assert len(grid)==81 and len({x['month'] for x in grid})==81
 reviewed=json.loads((out/'reviewed_publication_dates.json').read_text());saved_lookup={x['url']:x for x in saved}
 for r in reviewed:
  x=saved_lookup[r['url']];assert r['raw_sha256']==x['sha256'];raw=Path(x['path']).read_bytes();decoded=gzip.decompress(raw) if raw[:2]==b'\x1f\x8b' else raw;soup=BeautifulSoup(decoded,'html.parser')
  assert r['evidence'] in soup.get_text(' ',strip=True)
  if r['metadata_published_time']:assert soup.find('meta',attrs={'property':'article:published_time'})['content']==r['metadata_published_time']
 js(out/'download_verification.json',dict(status='PASS',saved_documents=len(saved),bytes_read=total,attempts=len(ledger),remaining_document_allowance=100-len(saved),remaining_bytes=100000000-total,checks=['authorization limits','unique saved URL','every raw byte hash and length','gzip decoded hash','economic-month range','full81month coverage grid'],limitation='transport and extraction consistency only, not primary-source truth or PIT'))
 print('R38 DOWNLOAD VERIFIED',len(saved),total)
if __name__=='__main__':run()
