import pandas as pd
from common import *

def run():
    a=pd.read_parquet(ROOT/'data/r10_alert_followup.parquet')
    p=pd.read_parquet(ROOT/'data/r10_risk_followup.parquet')
    for _,g in p.groupby(['era','level','date','horizon']):
        expected=g.sort_values(['prediction','industry_code'],ascending=[False,True]).head(int(np.ceil(.2*len(g)))).index
        assert set(g.index[g.alert])==set(expected)
    for h in [5,20,60]:
        v=a[a[f'return{h}'].notna()]
        assert (v.entry_date>v.date).all() and (v[f'maturity{h}']>v.entry_date).all()
        assert (v[f'drawdown{h}']<=v[f'min_from_entry{h}']+1e-12).all()
    s=pd.read_csv(ROOT/'outputs/r10/followup_summary.csv')
    assert (s.complete+s.unknown==s.alerts).all()
    d=pd.read_csv(ROOT/'outputs/r10/exit_date_metrics.csv')
    expected=d.groupby(['era','level','horizon','cohort','cost']).cash_improvement.mean().sort_index()
    actual=pd.read_csv(ROOT/'outputs/r10/exit_summary_dates.csv').set_index(['era','level','horizon','cohort','cost']).cash_improvement.sort_index()
    assert np.allclose(expected,actual)
    js(ROOT/'outputs/r10/verification.json',dict(status='PASS',alert_rows=len(a),risk_rows=len(p),
        checks=['selection before outcomes','next-close and maturity order','running-high drawdown vs entry loss','unknown denominators','date equal aggregation']))
    print('R10 verification PASS')
if __name__=='__main__':run()
