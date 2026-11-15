"""Local mechanism definitions supplement; never promote unobserved values."""
import pandas as pd
from common import ROOT,sha,js

def run():
    base=__import__('pathlib').Path('/home/xiaolv/code/golden_loop_artifacts/a_share_market_radar/reports')
    specs=[('industry_validation/20260924-pilot-v1/baseline/expectation_baselines.csv','D','research hypotheses, not analyst estimates'),
           ('industry_validation/20260924-pilot-v1/baseline/operating_drivers.csv','B','definitions, not operating time series'),
           ('fixed_industry_pool/20261010-data-v1/macro_links.csv','A','transmission hypotheses, not macro observations')]
    out=ROOT/'outputs/data_supplement';out.mkdir(exist_ok=True)
    rows=[]
    for relative,module,boundary in specs:
        path=base/relative;d=pd.read_csv(path);digest=sha(path)
        rows.append(dict(module=module,source=str(path),sha256=digest,rows=len(d),columns=list(d),boundary=boundary,
            nonmissing={c:int(d[c].notna().sum()) for c in d.columns}))
        d['ep35_source_path']=str(path);d['ep35_source_sha256']=digest
        d['ep35_use']='mechanism_definition_only';d['ep35_numeric_factor_eligible']=False
        d.to_parquet(ROOT/f'data/mechanism_definitions_{module}.parquet',index=False)
    js(out/'local_mechanism_inventory.json',dict(sources=rows,
        scope='three explicitly inspected local tables; not an exhaustive absence claim',
        mapping='Dongcai industry identifiers are not Shenwan identifiers; no automatic mapping',
        new_predictive_series=0))
    print([(x['module'],x['rows']) for x in rows])
if __name__=='__main__':run()
