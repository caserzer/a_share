"""Check default/tight lineage and every drift aggregation."""
import pandas as pd
from common import *
G=['era','level','cohort','task','horizon']

def run():
    out=ROOT/'outputs/r106';r=json.loads((out/'drift_receipt.json').read_text())
    for p,h in r['reads'].items():assert sha(p)==h
    for p,h in r['outputs'].items():assert sha(out/p)==h
    p=pd.read_parquet(out/'paired_predictions.parquet');drift=pd.read_csv(out/'prediction_drift.csv');comparison=pd.read_csv(out/'precision_comparison.csv');summary=json.loads((out/'drift_summary.json').read_text())
    assert len(drift)==2*p.groupby(G+['year']).ngroups
    for row in drift.to_dict('records'):
        g=p
        for k in G+['year']:g=g[g[k].eq(row[k])]
        a,b=('default_prediction','prediction') if row['variant']=='duplicate' else ('default_unique_prediction','unique_prediction')
        change=np.abs(g[b].to_numpy()-g[a].to_numpy())
        assert row['rows']==len(g);np.testing.assert_allclose([row['maximum_absolute_drift'],row['mean_absolute_drift']],[max(change),sum(change)/len(change)],atol=1e-14)
    old=pd.read_csv(ROOT/'outputs/r105/summary.csv');new=pd.read_csv(out/'summary.csv')
    expected=old.merge(new,on=G,suffixes=('_default','_tight'),validate='one_to_one');expected['mean_sign_changed']=np.sign(expected.mean_delta_default)!=np.sign(expected.mean_delta_tight);expected['mean_delta_change']=expected.mean_delta_tight-expected.mean_delta_default
    pd.testing.assert_frame_equal(comparison,expected,check_exact=False,atol=1e-14,rtol=1e-12)
    assert summary['groups']==len(expected) and summary['mean_sign_changes']==expected.mean_sign_changed.sum()
    for version,table in [('default',old),('tight',new)]:
        assert summary[version+'_positive_family']==table.family60_low.gt(0).sum() and summary[version+'_negative_family']==table.family60_high.lt(0).sum()
    for variant in ['duplicate','unique']:
        np.testing.assert_allclose(summary['classification_max_abs_drift'][variant],drift[drift.variant.eq(variant)&drift.task.ne('return')].maximum_absolute_drift.max(),atol=1e-14)
    assert summary['regression_max_abs_drift']==drift[drift.task.eq('return')].maximum_absolute_drift.max()==0
    js(out/'drift_verification.json',dict(status='PASS',fold_variant_rows=len(drift),comparison_groups=len(comparison),mean_sign_changes=summary['mean_sign_changes'],adopted=False));print('PASS precision drift',summary['mean_sign_changes'],'sign changes')

if __name__=='__main__':run()
