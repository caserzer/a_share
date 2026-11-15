from common import *
import pandas as pd

def run():
    out=ROOT/'outputs/r288';out.mkdir(exist_ok=True)
    o=pd.read_parquet(ROOT/'outputs/r287/origins.parquet');a=pd.read_parquet(ROOT/'outputs/r287/alerts.parquet');m=pd.read_csv(ROOT/'outputs/r287/metrics.csv')
    o['n']=o.groupby(['era','level','date']).date.transform('size');o['k']=np.ceil(o.n/5).astype(int);o['p']=o.k/o.n
    cal=pd.DatetimeIndex(pd.read_parquet(CACHE/'forecast_v5/CSI_ALL.parquet').index);ends=pd.Series(cal,index=cal).groupby(cal.to_period('M')).max();ends=ends[[p.end_time.normalize()<=cal.max() for p in ends.index]]
    rows=[];eventrows=[]
    for (era,level),whole in o.groupby(['era','level']):
        ids=sorted(whole.episode_id.dropna().unique())
        for strategy,g in [('daily',whole),('monthly',whole[whole.date.isin(ends.values)])]:
            events=g[g.episode_id.notna()];assert not events.duplicated(['episode_id','date']).any()
            probabilities={eid:1-float(np.prod(1-group.p)) for eid,group in events.groupby('episode_id')}
            for eid in ids:eventrows.append(dict(era=era,level=level,strategy=strategy,episode_id=int(eid),opportunities=int(events.episode_id.eq(eid).sum()),detection_probability=probabilities.get(eid,0.)))
            expected=sum(probabilities.values());matched=float(events.p.sum());total=int(g.groupby('date').k.first().sum())
            assert np.isclose(g.p.sum(),total)
            for variant in ['base','state','interaction']:
                actual=a[a.era.eq(era)&a.level.eq(level)&a.strategy.eq(strategy)&a.variant.eq(variant)].groupby('date').size()
                pd.testing.assert_series_equal(actual.sort_index(),g.groupby('date').k.first().sort_index(),check_names=False)
            rows.append(dict(era=era,level=level,strategy=strategy,observable_events=len(ids),opportunity_events=len(probabilities),alerts=total,expected_detected=expected,expected_recall=expected/len(ids),expected_matched_alerts=matched,expected_duplicate_alerts=matched-expected,expected_unknown_alerts=float(g.loc[~g.complete_path,'p'].sum()),expected_unmatched_known_alerts=float(g.loc[g.complete_path&g.episode_id.isna(),'p'].sum())))
    ref=pd.DataFrame(rows);ref.to_csv(out/'random_reference.csv',index=False);pd.DataFrame(eventrows).to_csv(out/'event_probabilities.csv',index=False)
    comparisons=m[m.strategy.isin(['daily','monthly'])].merge(ref,on=['era','level','strategy'],suffixes=('','_reference'),validate='many_to_one')
    assert comparisons.alerts.eq(comparisons.alerts_reference).all() and comparisons.observable_episodes.eq(comparisons.observable_events).all()
    comparisons['detected_minus_random']=comparisons.detected_episodes-comparisons.expected_detected;comparisons['recall_minus_random']=comparisons.recall-comparisons.expected_recall
    comparisons.to_csv(out/'comparisons.csv',index=False)
    summary=dict(status='PASS',reference_groups=len(ref),event_probabilities=len(eventrows),comparisons=len(comparisons),above_random=int(comparisons.detected_minus_random.gt(0).sum()),below_random=int(comparisons.detected_minus_random.lt(0).sum()),adoption=False,no_refit=True,cooldown_included=False)
    js(out/'summary.json',summary)
    reads=json.loads((ROOT/'protocols/r288.json').read_text())['inputs']+['protocols/r288.json','src/reversal_random_r288.py']
    js(out/'receipt.json',dict(inputs={p:sha(ROOT/p) for p in reads},benchmark_sha256=sha(CACHE/'forecast_v5/CSI_ALL.parquet'),outputs={p.name:sha(p) for p in out.iterdir() if p.name!='receipt.json'}));print(summary);print(comparisons[['era','level','strategy','variant','recall_minus_random']].to_string(index=False))
if __name__=='__main__':run()
