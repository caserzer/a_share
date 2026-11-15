"""Independent rank and cohort checks of the fixed early financial replay."""
import pandas as pd
from common import *

def rank(x):
    return (x.rank(method='average')-.5)/x.notna().sum()-.5

def check(g, row):
    if len(g)<20:
        assert pd.isna(row.get('method'))
        return
    f=((rank(g.mom20)+rank(g.mom60))/2-rank(g.vol20)+rank(g.dd60))/3
    c=(rank(g.dedt_change)+rank(g.margin_delta))/2
    s={'F':f,'C':c,'FCfund':(f+c)/2}[row['method']]
    y=g['excess'+str(int(row['horizon']))];v=y.notna()
    assert int(v.sum())==row.get('n_outcome',row.get('outcome_n'))
    expected=s[v].rank().corr(y[v].rank()) if v.sum()>=20 else np.nan
    assert np.isclose(expected,row['ic'],equal_nan=True,atol=1e-12)

def run():
    out=ROOT/'outputs/r165';e=out/'evaluation'
    receipt=json.loads((out/'receipt.json').read_text())
    for p,h in receipt['reads'].items():assert sha(p)==h,p
    panel=pd.read_parquet(ROOT/'outputs/r130/monthly_panel.parquet')
    panel=panel[panel.era.eq('SW2021')&panel.date.between('2026-04-01','2026-09-30')]
    fin=pd.read_parquet(ROOT/'data/industry_financial_factors.parquet')
    expected=panel.merge(fin,on=KEY+['date'],how='left',suffixes=('','_financial'),validate='one_to_one')
    actual=pd.read_parquet(e/'data/financial_monthly_panel.parquet')
    pd.testing.assert_frame_equal(expected,actual)
    a=pd.read_csv(e/'outputs/r03/date_metrics.csv',parse_dates=['date'])
    for row in a.to_dict('records'):
        g=actual[actual.level.eq(row['level'])&actual.date.eq(row['date'])]
        assert int(g.price_ready.sum())==row['price_ready']
        g=g[g.price_ready].dropna(subset=['dedt_change','margin_delta'])
        assert len(g)==row['paired_n'];check(g,row)
    factors=pd.read_parquet(e/'data/r07_industry_factors.parquet')
    pd.testing.assert_frame_equal(factors,pd.read_parquet(ROOT/'data/r07_industry_factors.parquet'))
    joint=panel.merge(factors,on=KEY+['date'],suffixes=('','_financial'),how='left',validate='one_to_many')
    b=pd.read_csv(e/'outputs/r07/date_metrics.csv',parse_dates=['date'])
    coverage=pd.read_csv(e/'outputs/r07/coverage.csv',parse_dates=['date'])
    for row in b.to_dict('records'):
        full=joint[joint.level.eq(row['level'])&joint.date.eq(row['date'])]
        ready=full[full.price_ready].dropna(subset=['dedt_change','margin_delta'])
        sets=[set(ready.loc[ready.delay.eq(d),'industry_code']) for d in [0,5,20]]
        common=set.intersection(*sets)
        g=ready[ready.delay.eq(row['delay'])]
        if row['cohort']=='matched_all_delays':g=g[g.industry_code.isin(common)]
        assert len(g)==row['n_signal'];check(g,row)
    for row in coverage.to_dict('records'):
        full=joint[joint.level.eq(row['level'])&joint.date.eq(row['date'])]
        ready=full[full.price_ready].dropna(subset=['dedt_change','margin_delta'])
        common=set.intersection(*[set(ready.loc[ready.delay.eq(d),'industry_code']) for d in [0,5,20]])
        assert int(full.loc[full.delay.eq(row['delay']),'price_ready'].sum())==row['price_ready']
        assert len(ready[ready.delay.eq(row['delay'])])==row['available']
        assert len(common)==row['common_all_delays']
    for sub in ['r03/date_metrics.csv','r07/date_metrics.csv','r07/coverage.csv','r07/field_conflicts.csv','r07/archive_clock_coverage.csv','r07/profit_sign_regimes.csv']:
        pd.testing.assert_frame_equal(pd.read_csv(ROOT/'outputs'/sub),pd.read_csv(e/'outputs'/sub))
    archived=pd.read_csv(e/'outputs/r07/archive_clock_coverage.csv')
    assert archived.archived_records.eq(0).all()
    js(out/'verification.json',dict(status='PASS',r03_rows=len(a),r07_rows=len(b),coverage_rows=len(coverage),independent_rank_recalculation=True,factors_unchanged=True,archive_historical_records=0,adoption=False,strict_pit=False))
    print('PASS: independent early financial rank and coverage checks',len(a),len(b),len(coverage))
if __name__=='__main__':run()
