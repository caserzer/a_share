import gzip
import pandas as pd
from common import *


def run():
 out=ROOT/'outputs/r27';r=json.loads((out/'receipt.json').read_text())
 for p,h in r['reads'].items():assert sha(p)==h
 for p,h in r['outputs'].items():assert sha(p)==h
 source=pd.read_parquet(ROOT/'data/r11_analyst_forecasts.parquet');supported=pd.read_parquet(ROOT/'data/r27_value_support.parquet')
 keys=['infoCode','basis','fiscal_year'];q=source.merge(supported,on=keys,how='outer',suffixes=('_source','_check'),indicator=True,validate='one_to_one')
 assert len(q)==len(source) and q._merge.eq('both').all()
 assert np.array_equal(q.value_source,q.value_check) and q.raw_sha256_source.eq(q.raw_sha256_check).all()
 assert supported.supported.eq(np.isclose(supported.value,supported.reparsed_value,rtol=1e-12,atol=1e-8)).all()
 files=pd.read_csv(out/'source_files.csv');assert len(files)==14571 and files.infoCode.is_unique
 flags=json.loads((out/'review_flags.json').read_text());lookup=files.set_index('infoCode')
 for code in {x['infoCode'] for x in flags}:
  row=lookup.loc[code];assert hashlib.sha256(gzip.decompress(Path(row.path).read_bytes())).hexdigest()==row.raw_sha256
 assert 'AP202505161673950688' in {x['infoCode'] for x in flags if x['kind']=='profit_noncurrency_dimension'}
 assert 'AP202405141633046370' in {x['infoCode'] for x in flags if x['kind']=='cross_basis_year_sets'}
 reviewed=json.loads((out/'report_level_year_sets.json').read_text())
 assert len(reviewed)==4
 for row in reviewed:
  assert hashlib.sha256(gzip.decompress(Path(row['source_path']).read_bytes())).hexdigest()==row['raw_sha256']
 assert sum(x['review']=='confirmed_explicit_year_conflict_already_quarantined_r24' for x in reviewed)==1
 js(out/'verification.json',dict(status='PASS_SCREEN_COVERAGE_AND_PROVENANCE',reports=len(files),values=len(supported),flagged_sources_verified=len({x['infoCode'] for x in flags}),unsupported_values=int((~supported.supported).sum()),code_sha256=sha(__file__),limitation='checks screen provenance and arithmetic support; unflagged does not mean error-free'))
 print('R27 screen verified',len(files),'reports and',len(supported),'values')

if __name__=='__main__':run()
