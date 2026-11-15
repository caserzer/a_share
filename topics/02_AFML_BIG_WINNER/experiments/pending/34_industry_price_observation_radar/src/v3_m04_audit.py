"""Independent checks for standalone and two-arm paired frozen-signal replays."""
import json
from pathlib import Path
import pandas as pd
from audit_local_inputs import EP,sha


def main():
    replay=EP/'outputs/v3_m04_replay';evaluation=EP/'outputs/evaluation_versions/v3_m04';decisions=EP/'outputs/v3_m04_decisions';comparison=EP/'outputs/v3_m04_comparison'
    refs=0
    for root in [EP/'outputs/v3_m04_models',replay,evaluation,decisions,comparison]:
        rec=json.loads((root/'receipt.json').read_text())
        for file,digest in rec['inputs'].items():assert sha(Path(file))==digest,file;refs+=1
        for file,digest in rec['artifacts'].items():assert sha(root/file)==digest,file;refs+=1
    inv=pd.read_csv(replay/'run_inventory.csv');summary=pd.read_csv(evaluation/'all_run_summary.csv').set_index('run_id')
    misses=pd.read_parquet(decisions/'all_missed_processes.parquet');transitions=pd.read_parquet(decisions/'all_coverage_transitions.parquet')
    paths=pd.read_parquet(comparison/'all_main_new_paths.parquet');pairs={};total=0
    for run in inv.itertuples():
        ev=pd.read_parquet(replay/run.run_id/'events.parquet');q=pd.read_parquet(evaluation/'runs'/run.run_id/'event_quality.parquet');pc=pd.read_parquet(evaluation/'runs'/run.run_id/'parent_coverage.parquet');d=pd.read_parquet(decisions/(run.run_id+'_online_decisions.parquet'))
        assert ev.event_id.is_unique and q.event_id.is_unique
        assert set(q.event_id)==set(ev.loc[ev.kind.isin(['NEW','UPDATE']),'event_id'])
        assert q.loc[q.status.eq('COVERED'),'primary_id'].is_unique
        count=ev.groupby('date').kind.value_counts().unstack(fill_value=0);pool=(count.NEW-count.EXIT).cumsum()
        assert count.NEW.le(run.quota).all() and pool.between(0,20).all()
        if run.mode=='paired':
            new=count.NEW.to_dict()
            key=(run.quota,run.delay)
            if key in pairs:assert pairs[key]==new
            else:pairs[key]=new
        else:assert d.actual_quota.eq(d.own_quota).all()
        assert len(pc)==4540 and pc.process_id.is_unique
        mm=misses[misses.run_id.eq(run.run_id)];assert set(mm.process_id)==set(pc.loc[~pc.covered,'process_id']) and mm.process_id.is_unique
        tt=transitions[transitions.run_id.eq(run.run_id)];assert len(tt)==4540 and tt.process_id.is_unique
        assert len(d)==pd.read_parquet(replay/run.run_id/'catalog_states.parquet').shape[0]
        newids=set(ev.loc[ev.kind.eq('NEW'),'event_id'])
        for h in ([20,60,90,180] if run.mode=='solo' else []):
            f=paths[paths.run_id.eq(run.run_id)&paths.horizon.eq(h)];assert f.event_id.is_unique and set(f.event_id)==newids
        assert summary.loc[run.run_id,'parent_missed']==len(mm)
        total+=len(ev)
    import numpy as np
    weights=pd.read_parquet(EP/'outputs/v3_m04_models/training_weights.parquet')
    count=0
    for (year,target),g in weights.groupby(['year','target']):
        assert g.target_available_date.lt(pd.Timestamp(year=year,month=1,day=1)).all()
        pos=g.label.eq(1);negative=g[~pos]
        np.testing.assert_array_equal(negative.old_weight,negative.new_weight)
        assert np.isclose(g.loc[pos,'old_weight'].sum(),g.loc[pos,'new_weight'].sum())
        masses=g[pos].groupby('prefix_group').new_weight.sum()
        assert g.loc[pos,'prefix_group'].notna().all() and np.allclose(masses,masses.iloc[0])
        count+=1
    assert count==14 and len(inv)==49 and len(pairs)==6
    result=dict(result='PASS_FROZEN_SIGNAL_AND_DECISION_ACCOUNTING_NOT_BUSINESS_ACCEPTANCE',hash_references=refs,runs=len(inv),events=total,
        paired_designs=len(pairs),standalone_designs=int(inv['mode'].eq('solo').sum()),parent_denominator=4540,all_missed_processes_audited=True,
        all_new_followups_retained=True,annual_fits=14,all_capacity_checks_pass=True,limits='Observed constraints do not prove capture under alternative rules; no joint-objective success established.')
    (comparison/'independent_audit.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))


if __name__=='__main__':main()
