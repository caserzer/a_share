import gzip,importlib.util
import pandas as pd
from common import *

def run():
    ep=ROOT.parent/'24_conditional_return_distribution_exploration'
    dest=ep/'outputs/r19_eps_expectations';cache=ep/'outputs/local_cache/r19_eps_html'
    spec=importlib.util.spec_from_file_location('original_parser',ep/'src/parse_eps_forecasts.py');parser=importlib.util.module_from_spec(spec);spec.loader.exec_module(parser)
    raw=pd.read_parquet(dest/'validated_extractions.parquet')
    # Deterministic source sample, independent of return labels and parsed values.
    sample=raw.assign(order=raw.infoCode.map(lambda v:hashlib.sha256(v.encode()).hexdigest())).sort_values('order').head(64)
    exclusions=json.loads((dest/'extraction_validation.json').read_text())['source_exclusions']
    for row in sample.itertuples():
        body=gzip.decompress((cache/f'{row.infoCode}.html.gz').read_bytes())
        parsed=parser.parse_report(body.decode('utf-8'),row.publishDate,row.stockCode)
        if row.infoCode in exclusions:parsed[exclusions[row.infoCode]['field']]={}
        for field in ['forecasts','profit_forecasts']:
            assert {str(k):v for k,v in parsed.get(field,{}).items()}==json.loads(getattr(row,field))
    values=pd.read_parquet(ROOT/'data/r11_analyst_forecasts.parquet')
    assert not values.duplicated(['infoCode','basis','fiscal_year']).any()
    assert values.publication_proxy_date.notna().all()
    assert (values.publication_proxy_date>=pd.to_datetime(values.published_date)).all()
    assert (values.publication_proxy_date>=pd.to_datetime(values.body_date)).all()
    macro=pd.read_parquet(ROOT/'data/r11_macro_observations.parquet')
    assert not macro.duplicated(['metric','economic_month']).any()
    assert macro.verified_release_date.isna().all()
    coverage=pd.read_parquet(ROOT/'data/r11_revision_coverage.parquet')
    assert (coverage.eligible==((coverage.known>=5)&(coverage.coverage>=.8))).all()
    assert coverage.loc[~coverage.eligible,'full_factor'].isna().all()
    assert np.allclose(coverage.coverage,coverage.known/coverage.members)
    revisions=pd.read_parquet(ROOT/'data/r11_company_broker_revisions.parquet')
    assert (revisions.latest_publication<revisions.date).all()
    assert (revisions.previous_publication<revisions.latest_publication).all()
    assert (revisions.date-revisions.latest_publication).dt.days.le(180).all()
    assert revisions.revision.between(-1,1).all()
    js(ROOT/'outputs/r11/coverage_receipt.json',dict(status='PASS',code_sha256=sha(ROOT/'src/coverage_r11.py'),
        sources={str(p):sha(p) for p in [ROOT/'data/r11_analyst_forecasts.parquet',ROOT/'data/monthly_panel.parquet',CACHE/'extension_v2/products/assignments.parquet']},
        output_sha256=sha(ROOT/'data/r11_revision_coverage.parquet'),rows=len(coverage),
        checks=['full membership denominator','80 percent and five member gate','strict publication dates','revision bounded by signed symmetric difference']))
    js(ROOT/'outputs/r11/verification.json' ,dict(status='PASS',reparsed_source_sample=64,
        checks=['original-body parser sample matches extraction','unique explicit fiscal-year keys','publication proxy no earlier than list or body date','macro unique periods; release dates not invented'],
        limitation='sample reparsing verifies implementation consistency, not full manual semantic validation'))
    print('R11 source verification PASS')
if __name__=='__main__':run()
