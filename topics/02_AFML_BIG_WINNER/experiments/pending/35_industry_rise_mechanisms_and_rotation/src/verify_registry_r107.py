"""Verify preserved definitions, full requirements and local source audit."""
import pandas as pd
from common import *

def run():
    out=ROOT/'outputs/r107';r=json.loads((out/'receipt.json').read_text());old=json.loads((ROOT/'outputs/r92/current_factor_dictionary.json').read_text());rows=json.loads((out/'current_factor_dictionary.json').read_text())
    assert r['prior_dictionary_sha256']==sha(ROOT/'outputs/r92/current_factor_dictionary.json') and r['prior_requirements_sha256']==sha(ROOT/'outputs/r100/requirements_evidence.json') and r['code_sha256']==sha(ROOT/'src/reconcile_models_r107.py')
    assert r['dictionary_sha256']==sha(out/'current_factor_dictionary.json') and r['requirements_sha256']==sha(out/'requirements_evidence.json')
    assert len(rows)==24 and [x['factor'] for x in rows]==[x['factor'] for x in old]
    for before,after in zip(old,rows):
        if before['factor'] not in r['amended']:assert before==after
        else:
            for k,v in before.items():
                if k not in ['evidence_refs','evidence_sha256']:assert after[k]==v
            assert set(before['evidence_refs'])<=set(after['evidence_refs']) and after['model_application_limit'] and after['numerical_research_rule']
        assert not after['strict_pit_certified']
        for p,h in after['evidence_sha256'].items():assert sha(ROOT/p)==h
    prior=json.loads((ROOT/'outputs/r100/requirements_evidence.json').read_text());req=json.loads((out/'requirements_evidence.json').read_text())
    assert len(req['items'])==16 and [x['requirement'] for x in req['items']]==[x['requirement'] for x in prior['items']] and not any(x['completion_proven'] for x in req['items'])
    for before,after in zip(prior['items'],req['items']):
        assert {e['path'] for e in before['evidence']}<={e['path'] for e in after['evidence']}
        for e in after['evidence']:assert e['exists'] and sha(ROOT/e['path'])==e['sha256']
    audit=json.loads((out/'next_path_source_audit.json').read_text());coverage=pd.read_parquet(out/'leader_source_coverage.parquet')
    for p,h in audit['source_hashes'].items():assert sha(p)==h
    assert 'next_return' not in audit['source_columns'] and 'entry_open' not in audit['source_columns']
    stocks=pd.read_parquet(CACHE/'extension_v2/products/panel.parquet',columns=audit['source_columns'])
    assert len(stocks)==audit['stock_rows'] and stocks.month.nunique()==audit['stock_months']
    np.testing.assert_allclose(stocks.cap,stocks.raw_close*stocks.total_shares,equal_nan=True)
    valid=(stocks.listed&np.isfinite(stocks.cap)&stocks.cap.gt(0)&stocks.raw_close.gt(0)&stocks.total_shares.gt(0)&stocks.share_effective_date.notna()&stocks.share_effective_date.le(stocks.date))
    prices=np.isfinite(stocks.qfq_close)&stocks.qfq_close.gt(0)&stocks.close_chain.notna()
    assert valid.sum()==audit['valid_cap_rows'] and prices.sum()==audit['valid_price_rows']
    assert str(stocks.date.min().date())==audit['first_date'] and str(stocks.date.max().date())==audit['last_date']
    capset=set(zip(stocks.loc[valid,'month'],stocks.loc[valid,'security_id']));priceset=set(zip(stocks.loc[prices,'month'],stocks.loc[prices,'security_id']))
    members=pd.concat([pd.read_parquet(p,columns=['month']+KEY+['security_id','unresolved']) for p in [CACHE/'extension_v2/products/assignments.parquet',ROOT/'data/l1_assignments.parquet']],ignore_index=True)
    expected=[]
    for key,g in members.groupby(['month']+KEY):
        assert g.security_id.is_unique
        n=len(g);capcount=sum((key[0],sid) in capset for sid in g.security_id);pc=sum((key[0],sid) in priceset for sid in g.security_id);u=g.unresolved.max()
        expected.append(dict(zip(['month']+KEY,key),members=n,cap_known=capcount,price_known=pc,unresolved=u,ranking_candidate=n>=5 and capcount==n and u==0))
    pd.testing.assert_frame_equal(coverage,pd.DataFrame(expected),check_dtype=False)
    counts=coverage.groupby(['era','level']).agg(industry_months=('month','size'),ranking_candidates=('ranking_candidate','sum')).reset_index().to_dict('records');assert counts==audit['coverage']
    current=json.loads((ROOT/'outputs/current_sources.json').read_text())
    for key,path in r['routes'].items():
        successors={'current_factor_dictionary':'outputs/r112/current_factor_dictionary.json','current_requirements_evidence':'outputs/r112/requirements_evidence.json','latest_stage_requirements_audit':'outputs/r112/requirements_evidence.json','next_local_mechanism_source_audit':'outputs/r112/valuation_source_audit.json'}
        if key in ['current_factor_dictionary','current_requirements_evidence','latest_stage_requirements_audit'] and current['selected'][key]['path']==successors[key].replace('/r112/','/r119/'):continue
        if key in ['current_factor_dictionary','current_requirements_evidence','latest_stage_requirements_audit'] and current['selected'][key]['path']==successors[key].replace('/r112/','/r124/'):continue
        if key in successors and current['selected'][key]['path']==successors[key]:continue
        assert current['selected'][key]==dict(path=path,sha256=sha(ROOT/path))
    for pointer in current['selected'].values():assert sha(ROOT/pointer['path'])==pointer['sha256']
    assert json.loads((ROOT/'outputs/r106/drift_summary.json').read_text())['mean_sign_changes']==3
    assert json.loads((ROOT/'outputs/r104/verification.json').read_text())['models']==76
    js(out/'verification.json',dict(status='PASS',entries=24,unchanged=18,amended=6,requirements=16,completed=0,source_industry_months=len(coverage),ranking_candidates=int(coverage.ranking_candidate.sum()),source_scope='ranking feasibility only; lagged return coverage and mechanism not validated'))
    print('PASS registry24 requirements16, source ranking candidates',int(coverage.ranking_candidate.sum()))

if __name__=='__main__':run()
