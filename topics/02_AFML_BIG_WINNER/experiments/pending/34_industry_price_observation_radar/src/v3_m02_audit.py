"""Independent ledger/support audit; does not assert business success."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from audit_local_inputs import EP,sha


def main():
    directories=[EP/'outputs'/x for x in ['v3_m02_targets','v3_m02_models','v3_m02_replay','evaluation_versions/v3_m02','v3_m02_comparison']]
    count=0
    for root in directories:
        rec=json.loads((root/'receipt.json').read_text())
        for name,digest in rec['inputs'].items():
            assert sha(Path(name))==digest,name;count+=1
        for name,digest in rec['artifacts'].items():
            assert sha(root/name)==digest,name;count+=1
    fits=pd.read_csv(directories[1]/'fit_audit.csv',parse_dates=['latest_label_available','fitted_before'])
    assert len(fits)==21 and fits.latest_label_available.lt(fits.fitted_before).all()
    training=pd.read_parquet(directories[0]/'training_panel.parquet')
    targets={'LR_COVER':['parent_coverage_target','child_coverage_target'],'LR_EARLY_UNION':['parent_early_target','child_early_target'],'LR_CHILD':['child_coverage_target']}
    for row in fits.itertuples():
        label=training[targets[row.model]].max(axis=1,skipna=False)
        mask=training.eligible&label.notna()&training.target_available_date.lt(row.fitted_before)
        assert int(mask.sum())==row.train_rows
        assert int(label[mask].sum())==row.positive
        assert training.loc[mask,'date'].lt(row.fitted_before).all()
    evroot=directories[3];summary=pd.read_csv(evroot/'all_run_summary.csv')
    parents=pd.read_parquet(EP/'outputs/v2_s12_full_directory_duration/processes.parquet')
    scope=json.loads((evroot/'version.json').read_text())
    mask=parents.status.eq('CONFIRMED')&~parents.left_context_unknown&parents.start_date.le(scope['observation_scope_end'])&parents.end_date.ge(scope['observation_scope_start'])
    parent_ids=set(parents.loc[mask,'process_id']);assert len(parent_ids)==4540
    admissions={};events_checked=0
    for r in summary.itertuples():
        ev=pd.read_parquet(directories[2]/r.run_id/'events.parquet');pc=pd.read_parquet(evroot/'runs'/r.run_id/'parent_coverage.parquet');eq=pd.read_parquet(evroot/'runs'/r.run_id/'event_quality.parquet')
        assert ev.event_id.is_unique and eq.event_id.is_unique
        assert set(pc.process_id)==parent_ids and pc.process_id.is_unique
        assert set(eq.event_id)==set(ev.loc[ev.kind.isin(['NEW','UPDATE']),'event_id'])
        assert eq.loc[eq.status.eq('COVERED'),'primary_id'].is_unique
        new=eq[eq.kind.eq('NEW')];unk=new.status.str.contains('UNKNOWN')
        assert len(new)==r.new_total and int(unk.sum())==r.new_unknown
        assert int(pc.covered.sum())==r.parent_covered and int(pc.timing.eq('TIMELY').sum())==r.parent_timely
        assert int(new.status.eq('COVERED').sum())==r.new_effective
        burden=ev.groupby('date').kind.value_counts().unstack(fill_value=0)
        new_count=burden.get('NEW',pd.Series(0,index=burden.index));exit_count=burden.get('EXIT',pd.Series(0,index=burden.index))
        pool=(new_count-exit_count).cumsum();assert pool.between(0,20).all()
        quota=int(r.run_id[1]);assert new_count.le(quota).all()
        key='_'.join(r.run_id.split('_')[:2]);adm=ev[ev.kind.eq('NEW')].groupby('date').size().to_dict()
        if key in admissions:assert adm==admissions[key]
        else:admissions[key]=adm
        events_checked+=len(ev)
    # Retained observations cannot be credited twice by the reporting adapter.
    paths=pd.read_parquet(directories[4]/'all_main_new_paths.parquet')
    for (run,h),g in paths.groupby(['run_id','horizon']):
        expected=set(pd.read_parquet(directories[2]/run/'events.parquet').query("kind=='NEW'").event_id)
        assert set(g.event_id)==expected and g.event_id.is_unique
        assert len(g)==len(expected)
    result=dict(result='PASS_TECHNICAL_ACCOUNTING_NOT_BUSINESS_ACCEPTANCE',hash_references=count,annual_fits=len(fits),replay_runs=len(summary),events_checked=events_checked,
        parent_denominator=len(parent_ids),all_admissions_paired=True,all_5_20_caps_pass=True,no_future_training_label_dates=True,all_main_followup_event_ids_retained=True,
        limitations=['Bounded prefix training targets differ from final enhancement labels','Same historical data reused; no independent validation','Paired six-arm scheduling is not an independently deployable rule','Technical verification cannot decide business acceptance'])
    (EP/'outputs/v3_m02_comparison/independent_audit.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
