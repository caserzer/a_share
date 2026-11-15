from common import *
import pandas as pd
from fractions import Fraction
from collections import defaultdict

def run():
    out=ROOT/'outputs/r289';cells=pd.read_csv(out/'cells.csv',dtype={'label':str,'event':str});metrics=pd.read_csv(out/'metrics.csv')
    o=pd.read_parquet(ROOT/'outputs/r287/origins.parquet');a=pd.read_parquet(ROOT/'outputs/r287/alerts.parquet')
    n=o.groupby(['era','level','date']).size().to_dict()
    cal=pd.DatetimeIndex(pd.read_parquet(CACHE/'forecast_v5/CSI_ALL.parquet').index);end={}
    for d in cal:
        if d.to_period('M').end_time.normalize()<=cal.max():end[d.to_period('M')]=d
    label=((o.rel_trough20<=-.08).astype(float)).where(o.excess20.notna()&o.rel_trough20.notna());np.testing.assert_equal(label.to_numpy(),o.y.to_numpy())
    expected=defaultdict(Fraction)
    def add(r,policy,strategy,weight):
        lc='unknown' if pd.isna(r.y) else str(int(r.y))
        ec='unknown' if not r.complete_path else '0' if pd.isna(r.episode_id) else '1'
        expected[(r.era,r.level,strategy,policy,lc,ec)]+=weight
    for r in o.itertuples():
        count=int(n[(r.era,r.level,r.date)]);weight=Fraction((count+4)//5,count)
        for strategy in ['daily']+(['monthly'] if r.date in end.values() else []):
            add(r,'population',strategy,Fraction(1));add(r,'random',strategy,weight)
    for r in a[a.strategy.isin(['daily','monthly'])].itertuples():add(r,r.variant,r.strategy,Fraction(1))
    keys=['era','level','strategy','policy','label','event'];assert not cells.duplicated(keys).any() and len(cells)==360
    for r in cells.itertuples():assert abs(float(expected[tuple(getattr(r,k) for k in keys)])-r.count)<1e-9
    assert set(expected).issubset(set(map(tuple,cells[keys].to_numpy())))
    for r in metrics.itertuples():
        v=cells[cells.era.eq(r.era)&cells.level.eq(r.level)&cells.strategy.eq(r.strategy)&cells.policy.eq(r.policy)]
        assert len(v)==9 and np.isclose(v['count'].sum(),r.count)
        known=v[v.label.ne('unknown')]['count'].sum();pos=v[v.label.eq('1')]['count'].sum();unknown=v[v.label.eq('unknown')]['count'].sum()
        assert np.isclose(known,r.known_label) and np.isclose(pos,r.positive_label) and np.isclose(unknown,r.unknown_label)
        assert np.isclose(v[v.event.eq('unknown')]['count'].sum(),r.unknown_event)
        assert np.isclose(pos/known,r.label_rate)
        complete=v[v.event.ne('unknown')];assert np.isclose(complete[complete.label.eq('1')]['count'].sum()/complete['count'].sum(),r.complete_label_rate)
    old=pd.read_csv(ROOT/'outputs/r287/metrics.csv');ref=pd.read_csv(ROOT/'outputs/r288/random_reference.csv')
    for r in pd.read_csv(out/'comparisons.csv').itertuples():
        row=old[old.era.eq(r.era)&old.level.eq(r.level)&old.strategy.eq(r.strategy)&old.variant.eq(r.policy)].iloc[0]
        baseline=ref[ref.era.eq(r.era)&ref.level.eq(r.level)&ref.strategy.eq(r.strategy)].iloc[0]
        assert row.alerts==r.count and np.isclose(row.fixed_label_precision,r.complete_label_rate)
        assert np.isclose(r.count_random,baseline.alerts) and np.isclose(r.unknown_event_random,baseline.expected_unknown_alerts)
        assert np.isclose(r.label_rate-r.label_rate_random,r.label_rate_minus_random)
    receipt=json.loads((out/'receipt.json').read_text())
    for p,h in receipt['inputs'].items():assert sha(ROOT/p)==h
    for p,h in receipt['outputs'].items():assert sha(out/p)==h
    assert sha(CACHE/'forecast_v5/CSI_ALL.parquet')==receipt['benchmark_sha256']
    js(out/'independent_verification.json',dict(status='PASS',source_label_rows=len(o),exact_rational_cells=len(cells),metric_groups=len(metrics),comparisons=24,verifier_sha256=sha(Path(__file__)),scope='Independent row classification and rational expected counts; historical descriptive evidence only'))
    print('R289 VERIFIED',len(o),len(cells),len(metrics))
if __name__=='__main__':run()
