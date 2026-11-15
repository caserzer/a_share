import pandas as pd
from common import *
from margin_inventory_r44 import SOURCE

def run():
 out=ROOT/'outputs/r44';receipt=json.loads((out/'receipt.json').read_text())
 for path,h in receipt['inputs'].items():assert sha(Path(path))==h
 raw=json.loads((out/'source_receipts.json').read_text());assert len(raw)==receipt['raw_receipts']
 for item in raw:assert sha(Path(item['path']))==item['receipt_sha256'] and sha(Path(item['body']))==item['body_sha256'] and Path(item['body']).stat().st_size==item['bytes']
 coverage=pd.read_parquet(out/'industry_coverage.parquet');assert sha(out/'industry_coverage.parquet')==receipt['coverage_sha256']
 assert not coverage.duplicated(KEY+['date']).any();assert coverage.observed.le(coverage.members).all() and coverage.disclosed_zero.le(coverage.observed).all()
 assert np.array_equal(coverage.coverage_ready,coverage.observed.ge(5)&coverage.fraction.ge(.8))
 detail=pd.read_parquet(SOURCE/'normalized_detail.parquet');cols=['month']+KEY+['security_id','instrument'];members=pd.concat([pd.read_parquet(CACHE/'extension_v2/products/assignments.parquet',columns=cols),pd.read_parquet(ROOT/'data/l1_assignments.parquet',columns=cols)])
 samples=pd.concat([g.iloc[np.linspace(0,len(g)-1,10,dtype=int)] for _,g in coverage.groupby(['era','level'])])
 for x in samples.to_dict('records'):
  m=members[members.month.eq(x['date'].to_period('M')-1)]
  for k in KEY:m=m[m[k].eq(x[k])]
  source=detail[detail.date.eq(x['date'])].set_index('instrument');known=[i for i in m.instrument if i in source.index and pd.notna(source.loc[i,'financing'])]
  assert len(m)==x['members'] and len(known)==x['observed'];assert sum(source.loc[i,'financing']==0 for i in known)==x['disclosed_zero']
 dates=pd.read_parquet(CACHE/'forecast_v5/CSI_ALL.parquet',columns=[]).index
 for row in json.loads((out/'calendar_lags.json').read_text()):assert sum((dates>pd.Timestamp(row['snapshot_date']))&(dates<=pd.Timestamp(row['date'])))==2
 js(out/'verification.json',dict(status='PASS',direct_industry_checks=len(samples),calendar_checks=receipt['months'],raw_receipt_count=receipt['raw_receipts'],scope='source hashes and coverage consistency; not strict PIT or predictive evidence'))
 print('R44 VERIFIED',len(samples),'direct membership checks')

if __name__=='__main__':run()
