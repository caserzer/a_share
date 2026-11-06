from pathlib import Path
import json,sys
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
V10=ROOT.parent/'v10_label_delay'
V7=ROOT.parent/'v7_online_stage'
V5=ROOT.parent/'v5_rdagent_onset_forecast'
OUT=ROOT/'outputs';CACHE=Path.home()/'.cache/a_share/ep32/error_v11';OLD=CACHE.parent/'forecast_v5'
sys.path.insert(0,str(V5/'src'))
from common import KEY,sha,js


def run():
    OUT.mkdir(parents=True,exist_ok=True);CACHE.mkdir(parents=True,exist_ok=True)
    previous=json.loads((V10/'outputs/predecessors.json').read_text())
    manifest=json.loads((V10/'outputs/manifest.json').read_text())
    previous.update({str(V10/r['path']):r['sha256'] for r in manifest['files']})
    previous[str(V10/'outputs/manifest.json')]=sha(V10/'outputs/manifest.json')
    assert all(sha(p)==h for p,h in previous.items());js(OUT/'predecessors.json',previous)
    states=pd.read_parquet(CACHE.parent/'online_v7/state_features.parquet',columns=['row_id','threshold','block','candidate_low_date','state_direction'])
    labels=pd.read_parquet(OLD/'stage_b_labels.parquet')
    phase=pd.read_parquet(OLD/'daily_phases.parquet').rename(columns={'start_date':'candidate_low_date'})
    key=KEY+['block','threshold','candidate_low_date']
    fields=key+['phase_id','status','left_censored','in_range_6_18','duration_days','industry_return','benchmark_return_CSI300','benchmark_return_CSI_ALL']
    phase=phase[fields];assert not phase.duplicated(key).any()
    receipt=json.loads((V10/'outputs/prediction_receipt.json').read_text());rows=[]
    for artifact in receipt['tasks']:
        assert sha(artifact['path'])==artifact['sha256']
        p=pd.read_parquet(artifact['path']);p=p[p.model.isin(['rd_selected','rd_gate','rd_conditional','pool_tree'])&p.alert&p.date.between('2021-01-01','2024-09-30')]
        p=p.merge(labels,on=['row_id','threshold','benchmark'],validate='many_to_one')
        p.loc[p.label_available_at.gt(p.date+pd.DateOffset(months=24)),'y']=np.nan
        p=p.merge(states,on=['row_id','threshold'],validate='many_to_one').merge(phase,on=key,how='left',validate='many_to_one')
        p['category']='OTHER_KNOWN_FALSE'
        false=p.y.eq(0);early=false&p.state_eligible.eq(1)
        p.loc[false&p.state_eligible.eq(0),'category']='OUTSIDE_EARLY_STATE'
        p.loc[early&p.phase_id.isna(),'category']='CANDIDATE_LOW_NOT_FINAL'
        matched=early&p.phase_id.notna()
        p.loc[matched&p.duration_days.lt(182),'category']='SHORT_PHASE'
        # Calendar duration from the phase table is authoritative; days only distinguish which side of range.
        p.loc[matched&~p.in_range_6_18.fillna(False).astype(bool)&p.duration_days.gt(365),'category']='LONG_PHASE'
        p.loc[matched&~p.in_range_6_18.fillna(False).astype(bool)&p.duration_days.le(365),'category']='SHORT_PHASE'
        benchmark=np.where(p.benchmark.eq('CSI300'),p.benchmark_return_CSI300,p.benchmark_return_CSI_ALL)
        p.loc[matched&p.in_range_6_18.fillna(False).astype(bool)&p.industry_return.le(benchmark),'category']='NOT_OUTPERFORMING'
        p.loc[false&p.prob.eq(0),'category']='ZERO_PROBABILITY_BUDGET_FILL'
        p.loc[p.y.eq(1),'category']='TRUE_EARLY';p.loc[p.y.isna(),'category']='UNKNOWN'
        p['year']=p.date.dt.year;rows.append(p)
    allrows=pd.concat(rows,ignore_index=True)
    allrows.to_parquet(CACHE/'alert_attribution.parquet',index=False)
    groups=['model','frequency','threshold','benchmark','level','year','category']
    allrows.groupby(groups).size().rename('observations').reset_index().to_csv(OUT/'attribution_counts.csv',index=False)
    summary=allrows.groupby(['model','category']).size().rename('observations').reset_index()
    summary['fraction_of_all_alerts']=summary.observations/summary.groupby('model').observations.transform('sum')
    summary.to_csv(OUT/'summary.csv',index=False)
    allrows.groupby(['model','year','category']).size().rename('observations').reset_index().to_csv(OUT/'annual_counts.csv',index=False)
    js(OUT/'audit.json',dict(plan_sha256=sha(ROOT/'research_plan.md'),code_sha256=sha(__file__),rows=len(allrows),
        saved_attribution_sha256=sha(CACHE/'alert_attribution.parquet'),prediction_receipt_sha256=sha(V10/'outputs/prediction_receipt.json'),
        unknown_retained=int(allrows.y.isna().sum()),unexplained_known_false=int(allrows.category.eq('OTHER_KNOWN_FALSE').sum()),
        ex_post_diagnostic_only=True,new_predictor=False))
    print(summary.to_string(index=False),flush=True)


if __name__=='__main__':run()
