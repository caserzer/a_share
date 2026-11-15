"""Independent preservation, evidence, routing and exact PE source checks."""
import pandas as pd
from common import *
def run():
    out=ROOT/'outputs/r112';rec=json.loads((out/'receipt.json').read_text())
    assert rec['code_sha256']==sha(ROOT/'src/reconcile_leader_r112.py')
    for p,h in rec['outputs'].items():assert sha(out/p)==h,p
    old=json.loads((ROOT/'outputs/r107/current_factor_dictionary.json').read_text());new=json.loads((out/'current_factor_dictionary.json').read_text())
    assert rec['prior_dictionary_sha256']==sha(ROOT/'outputs/r107/current_factor_dictionary.json') and new[:24]==old and len(new)==25 and len({x['factor'] for x in new})==25
    added=new[-1];assert added['factor']=='prior_ranked_leader_follower_return_spread' and not added['strict_pit_certified']
    for k in ['theory','formula','direction','applicable_industries','economic_date','publication_date','available_at','frequency','source','historical_revisions','aggregation','missing_rule','failure_condition','conclusion']:assert added[k]
    for item in new:
        for p,h in item['evidence_sha256'].items():assert sha(ROOT/p)==h
    oldreq=json.loads((ROOT/'outputs/r107/requirements_evidence.json').read_text());req=json.loads((out/'requirements_evidence.json').read_text())
    assert rec['prior_requirements_sha256']==sha(ROOT/'outputs/r107/requirements_evidence.json')
    assert len(req['items'])==16 and [x['requirement'] for x in req['items']]==[x['requirement'] for x in oldreq['items']] and not any(x['completion_proven'] for x in req['items'])
    for before,after in zip(oldreq['items'],req['items']):
        assert {e['path'] for e in before['evidence']}<={e['path'] for e in after['evidence']}
        for e in after['evidence']:assert e['exists'] and sha(ROOT/e['path'])==e['sha256']
    branch=json.loads((out/'branch_evidence.json').read_text());assert branch['status']=='stopped_parameter_search_not_adopted'
    for n,p in [('r109','outputs/r109/metric_verification.json'),('r110','outputs/r110/verification.json'),('r111','outputs/r111/verification.json')]:assert branch[n]==json.loads((ROOT/p).read_text())
    assert branch['r109']['support_groups']==branch['r111']['support_groups']==0
    a=json.loads((out/'valuation_source_audit.json').read_text());s=pd.read_parquet(out/'valuation_monthly_coverage.parquet')
    for p,h in a['sources'].items():assert sha(p)==h
    assert a['coverage_sha256']==sha(out/'valuation_monthly_coverage.parquet')
    source=pd.read_parquet(CACHE/'extension_v2/products/panel.parquet',columns=['month','date','security_id','raw_close','cap','total_shares','share_effective_date','listed']).sort_values(['security_id','month']).reset_index(drop=True)
    pd.testing.assert_frame_equal(s[source.columns],source)
    pe=pd.read_parquet(CACHE/'joint_pe_v35/stock_pe_panel.parquet');expected=np.full(len(s),np.nan);matched=np.zeros(len(s),bool)
    for date,g in s.groupby('date'):
        if date not in pe.index:continue
        expected[g.index]=pe.loc[date].reindex(g.security_id).to_numpy();matched[g.index]=g.security_id.isin(pe.columns)
    np.testing.assert_allclose(expected,s.vendor_pe_ttm,equal_nan=True);assert (matched==s.pe_exact_identity_date).all()
    valid=s.listed.eq(True)&np.isfinite(s.raw_close)&s.raw_close.gt(0)&np.isfinite(expected)&(expected>0);assert valid.equals(s.positive_pair_ready)
    known=set(zip(s.loc[valid,'security_id'],s.loc[valid,'month']))
    pair=[bool(v) and (sid,month-1) in known for sid,month,v in zip(s.security_id,s.month,valid)]
    assert np.array_equal(pair,s.consecutive_positive_pair)
    counts=dict(stock_rows=len(s),months=s.month.nunique(),pe_dates=len(pe),pe_securities=len(pe.columns),exact_identity_date=int(matched.sum()),finite_pe=int(np.isfinite(expected).sum()),nonpositive_pe=int((np.isfinite(expected)&(expected<=0)).sum()),positive_endpoint=int(valid.sum()),consecutive_positive_pairs=sum(pair))
    for k,v in counts.items():assert a[k]==v,(k,a[k],v)
    current=json.loads((ROOT/'outputs/current_sources.json').read_text())['selected']
    for k,p in rec['routes'].items():
        if k in ['current_factor_dictionary','current_requirements_evidence','latest_stage_requirements_audit'] and current[k]['path']==p.replace('/r112/','/r124/'):continue
        if k in ['current_factor_dictionary','current_requirements_evidence','latest_stage_requirements_audit'] and current[k]['path']==p.replace('/r112/','/r119/'):continue
        assert current[k]==dict(path=p,sha256=sha(ROOT/p))
    for x in current.values():assert sha(ROOT/x['path'])==x['sha256']
    js(out/'verification.json',dict(status='PASS',preserved_entries=24,entries=25,requirements=16,completed=0,monthly_stock_rows=len(s),consecutive_positive_pairs=sum(pair),interpretation='source pairing only, not reported earnings or predictive evidence'));print('PASS registry25 requirements16, PE paired endpoints',sum(pair))
if __name__=='__main__':run()
