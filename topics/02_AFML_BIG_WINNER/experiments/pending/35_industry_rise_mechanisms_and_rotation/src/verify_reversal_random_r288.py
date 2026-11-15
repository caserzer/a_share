from common import *
import pandas as pd
from decimal import Decimal,getcontext
from itertools import combinations,product
from fractions import Fraction

def run():
    getcontext().prec=45
    out=ROOT/'outputs/r288';o=pd.read_parquet(ROOT/'outputs/r287/origins.parquet');events=pd.read_csv(out/'event_probabilities.csv');refs=pd.read_csv(out/'random_reference.csv')
    o['n']=o.groupby(['era','level','date']).date.transform('size');o['k']=(o.n+4)//5
    cal=pd.DatetimeIndex(pd.read_parquet(CACHE/'forecast_v5/CSI_ALL.parquet').index);ends={}
    for d in cal:
        if d.to_period('M').end_time.normalize()<=cal.max():ends[d.to_period('M')]=d
    checks=0
    for ref in refs.itertuples():
        whole=o[o.era.eq(ref.era)&o.level.eq(ref.level)];g=whole if ref.strategy=='daily' else whole[whole.date.isin(ends.values())]
        ids=set(whole.episode_id.dropna().astype(int));ev=events[events.era.eq(ref.era)&events.level.eq(ref.level)&events.strategy.eq(ref.strategy)]
        assert set(ev.episode_id)==ids and len(ev)==len(ids)
        expected=Decimal(0)
        for r in ev.itertuples():
            matches=g[g.episode_id.eq(r.episode_id)].sort_values('date');prob=Decimal(0)
            assert len(matches)==r.opportunities and matches.date.nunique()==len(matches)
            for v in matches.itertuples():prob+=(1-prob)*Decimal(v.k)/Decimal(v.n)
            assert abs(float(prob)-r.detection_probability)<1e-12;expected+=prob;checks+=1
        assert abs(float(expected)-ref.expected_detected)<1e-10 and abs(float(expected)/len(ids)-ref.expected_recall)<1e-12
        assert g.groupby('date').k.first().sum()==ref.alerts
        marginal=g.k/g.n
        matched=marginal[g.episode_id.notna()].sum();unknown=marginal[~g.complete_path].sum();unmatched=marginal[g.complete_path&g.episode_id.isna()].sum()
        assert np.isclose(matched,ref.expected_matched_alerts) and np.isclose(unknown,ref.expected_unknown_alerts) and np.isclose(unmatched,ref.expected_unmatched_known_alerts)
        assert np.isclose(matched+unknown+unmatched,ref.alerts)
        assert np.isclose(matched-float(expected),ref.expected_duplicate_alerts)
    cmp=pd.read_csv(out/'comparisons.csv');old=pd.read_csv(ROOT/'outputs/r287/metrics.csv')
    for r in cmp.itertuples():
        actual=old[old.era.eq(r.era)&old.level.eq(r.level)&old.strategy.eq(r.strategy)&old.variant.eq(r.variant)].iloc[0]
        assert actual.alerts==r.alerts==r.alerts_reference and actual.detected_episodes==r.detected_episodes
        assert np.isclose(r.recall_minus_random,actual.recall-r.expected_recall)
        assert np.isclose(r.detected_minus_random,actual.detected_episodes-r.expected_detected)
    # Enumerate actual fixed-size subsets; events share each day's finite capacity.
    fixture_states=0
    for n1,k1,n2,k2 in [(3,1,2,1),(4,2,3,1),(6,2,5,1),(3,3,4,2)]:
        total=0;detections=0;duplicates=0;matched=0
        for first,second in product(combinations(range(n1),k1),combinations(range(n2),k2)):
            labels=[i for i in first if i<2]+[i for i in second if i<2]
            total+=1;detections+=len(set(labels));matched+=len(labels);duplicates+=len(labels)-len(set(labels))
        expected=2*(1-(1-Fraction(k1,n1))*(1-Fraction(k2,n2)))
        assert Fraction(detections,total)==expected
        assert Fraction(matched,total)==2*(Fraction(k1,n1)+Fraction(k2,n2))
        assert Fraction(duplicates,total)==2*(Fraction(k1,n1)+Fraction(k2,n2))-expected
        fixture_states+=total
    rec=json.loads((out/'receipt.json').read_text())
    for p,h in rec['inputs'].items():assert sha(ROOT/p)==h
    for p,h in rec['outputs'].items():assert sha(out/p)==h
    assert sha(CACHE/'forecast_v5/CSI_ALL.parquet')==rec['benchmark_sha256']
    js(out/'independent_verification.json',dict(status='PASS',decimal_event_checks=checks,reference_groups=len(refs),model_comparisons=len(cmp),exhaustive_fixtures=4,enumerated_subset_pairs=fixture_states,scope='Expectation and capacity verification, not uncertainty or independence certification',verifier_sha256=sha(Path(__file__))))
    print('R288 VERIFIED',checks,len(cmp),fixture_states)
if __name__=='__main__':run()
