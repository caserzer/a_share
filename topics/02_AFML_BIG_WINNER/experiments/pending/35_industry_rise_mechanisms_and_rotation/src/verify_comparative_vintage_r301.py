from common import *
import pandas as pd
import subprocess,re,fitz
from decimal import Decimal

def run():
 out=ROOT/'outputs/r301';rows=json.loads((out/'comparative_cells.json').read_text());source=pd.read_parquet(ROOT/'data/financial_archive_all_market.parquet');cache={};headers=[];count=0
 for row in rows:
  key=(row['symbol'],row['pdf_page']);pdf=ROOT/'data/cnequity_fundamental_review_20261114'/row['symbol']/'2026H1.pdf'
  if key not in cache:cache[key]=fitz.open(pdf)[key[1]-1].get_text()
  assert row['reported_number'] in cache[key]
  value=Decimal(row['reported_number'].replace(',','').strip('()'))
  if row['reported_number'].startswith('(') and row['item_code']!='capex':value=-value
  value*=row['unit_multiplier'];assert value==Decimal(row['normalized_value'])
  api='income_vip' if row['item_code']=='net_profit' else 'cashflow_vip';g=source[(source.ts_code==row['symbol'])&(source.api==api)&(source.end_date==pd.Timestamp('2025-06-30'))];values={Decimal(str(x)) for x in g[row['archive_field']].dropna()};assert values=={Decimal(v) for v in row['archive_values']};count+=len(g)
  unit=Decimal(row['unit_multiplier']);assert all(abs(x-value)<=unit/2 if unit>1 else abs(x-value)<=Decimal('.005') for x in values)
  assert row['announce_date'][:4]=='2026' and row['observed_at'][:10]>=row['announce_date'] and row['strict_pit'] is False
  if row['item_code']=='capex':
   text='\n'.join(fitz.open(pdf)[i].get_text() for i in range(max(0,key[1]-3),key[1]))
   assert '合并' in text and '现金流量表' in text and '2025' in text and '2026' in text
   headers.append(dict(symbol=key[0],pages=[max(1,key[1]-2),key[1]],text=text))
 rec=json.loads((out/'receipt.json').read_text())
 for p,h in rec['inputs'].items():assert sha(ROOT/p)==h
 for p,h in rec['outputs'].items():assert sha(out/p)==h
 js(out/'statement_header_evidence.json',headers);js(out/'independent_verification.json',dict(status='PASS',cells=len(rows),archive_records=count,pdf_pages=len(cache),statement_header_ranges=len(headers),scope='Fresh PDF text extraction, Decimal unit/sign, archived versions and hashes; column semantics manually reviewed with bank visual check, not full historical revision certification',verifier_sha256=sha(__file__)));print('VERIFIED',len(rows),count,len(cache))
if __name__=='__main__':run()
