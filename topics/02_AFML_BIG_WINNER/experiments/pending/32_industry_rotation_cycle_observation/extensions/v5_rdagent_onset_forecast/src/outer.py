"""Freeze candidate, write untouched outer predictions, then score and apply gates."""
import json
import numpy as np
import pandas as pd
from common import CACHE, OUT, KEY, js, sha, finite_json
from engine import BASELINES, task_frames, fit_predict, metric_rows


def evaluate_rows(f):
    rows=metric_rows(f)
    for row in rows:
        g=f[f.level.eq(row['level'])]
        dates=g[g.alert].date.unique()
        base=g[g.date.isin(dates)].groupby('date').y.mean().mean()
        row['precision_comparable_base_rate']=float(base)
        row['precision_comparable_dates']=len(dates)
        row['top10_lift']=row['top10_precision']/base if base>0 else np.nan
    return rows


def freeze(stage):
    dest=OUT/f'stage_{stage}'
    complete=json.loads((dest/'run_complete.json').read_text())
    assert complete['completed_history']==30
    candidates=[]
    for p in sorted((dest/'candidates').glob('*/summary.json')):
        summary=json.loads(p.read_text());spec=json.loads((p.parent/'spec.json').read_text())
        candidates.append(dict(candidate=p.parent.name,objective=summary['objective'],spec=spec,
                               spec_sha256=sha(p.parent/'spec.json')))
    candidates.sort(key=lambda x:(-x['objective'],x['candidate']))
    winner=candidates[0]
    record=dict(winner=winner,all_candidates=candidates,selection_uses='2021-2022 feedback only',
        historical_outer_start='2024-01-01',quality='exploratory historical replay',independent_holdout=False,
        evaluation_code_sha256=sha(__file__))
    js(dest/'frozen_selection.json',record)
    return winner


def predict(stage):
    winner=freeze(stage);models=dict(BASELINES);models['rd_selected']=winner['spec']
    rows=[];audit=[]
    quarters=pd.date_range('2024-01-01','2026-10-01',freq='QS')
    for key,g in task_frames(stage):
        for q in quarters:
            z=q+pd.DateOffset(months=3)
            train=g[g.date.lt(q)&g.label_available_at.lt(q)&g.y.notna()]
            test=g[g.date.ge(q)&g.date.lt(z)].drop(columns=['y','label_available_at','event_or_witness_id','reason'])
            if test.empty:continue
            assert train.label_available_at.max()<q and train.date.max()<q
            for name,spec in models.items():
                p,prior=fit_predict(train,test,spec)
                r=test[['row_id','date','era','level','industry_code','frequency','threshold','benchmark']].copy()
                r['model']=name;r['prob']=p;r['prior']=prior;r['quarter']=str(q.date())
                rank=r.groupby(['date','level']).prob.rank(method='first',ascending=False)
                r['alert']=rank<=np.ceil(r.groupby(['date','level']).date.transform('size')*.1)
                rows.append(r)
            audit.append(dict(frequency=key[0],threshold=key[1],benchmark=key[2],quarter=str(q.date()),
                train_rows=len(train),train_positive=int(train.y.sum()),latest_train_label=str(train.label_available_at.max()),test_rows=len(test)))
        print('outer predictions',stage,key,flush=True)
    p=CACHE/f'stage_{stage}/outer_predictions.parquet';p.parent.mkdir(parents=True,exist_ok=True)
    predictions=pd.concat(rows,ignore_index=True);predictions.to_parquet(p,index=False)
    js(OUT/f'stage_{stage}/prediction_receipt.json',dict(path=str(p),sha256=sha(p),rows=len(predictions),
        outcome_columns_present=False,frozen_selection_sha256=sha(OUT/f'stage_{stage}/frozen_selection.json'),
        folds=audit))
    return p


def score(stage):
    dest=OUT/f'stage_{stage}'
    receipt=json.loads((dest/'prediction_receipt.json').read_text());assert sha(receipt['path'])==receipt['sha256']
    p=pd.read_parquet(receipt['path'])
    labels=pd.read_parquet(CACHE/('labels.parquet' if stage=='a' else 'stage_b_labels.parquet'))
    merged=p.merge(labels,on=['row_id','threshold','benchmark'],validate='many_to_one')
    known=merged[merged.y.notna()].copy();known['year']=known.date.dt.year
    rows=[];annual=[]
    keys=['frequency','threshold','benchmark','model']
    for key,g in known.groupby(keys):
        for metric in evaluate_rows(g):metric.update(zip(keys,key));rows.append(metric)
    for key,g in known.groupby(keys+['year']):
        for metric in evaluate_rows(g):metric.update(zip(keys+['year'],key));annual.append(metric)
    results=pd.DataFrame(rows);years=pd.DataFrame(annual)
    results.to_csv(dest/'outer_metrics.csv',index=False);years.to_csv(dest/'annual_metrics.csv',index=False)
    cover=merged.groupby(keys+['level']).agg(predictions=('row_id','size'),known=('y','count'),
        alerts=('alert','sum')).reset_index()
    ka=merged[merged.alert].groupby(keys+['level']).agg(known_alerts=('y','count'),
        true_alerts=('y','sum')).reset_index()
    cover=cover.merge(ka,on=keys+['level'],how='left');cover['unknown']=cover.predictions-cover.known
    cover['unknown_alerts']=cover.alerts-cover.known_alerts
    cover.to_csv(dest/'outer_coverage.csv',index=False)
    # Both industry levels contribute equally; benchmark/threshold gates are never selected on their own.
    task=results.groupby(keys)[['brier','prior_brier','brier_skill','top10_precision','top10_lift','prevalence','pr_auc']].mean().reset_index()
    yearly=years.groupby(keys+['year']).agg(brier=('brier','mean'),dates=('dates','min'),positives=('positives','sum')).reset_index()
    gates=[]
    for key,g in task.groupby(['frequency','threshold','benchmark']):
        r=g.set_index('model');cand=r.loc['rd_selected']
        aggregate=bool(cand.brier<r.loc[['prior','logistic','static_tree'],'brier'].min() and cand.top10_lift>=2)
        yg=yearly[(yearly.frequency==key[0])&(yearly.threshold==key[1])&(yearly.benchmark==key[2])]
        eligible=[];year_pass=[]
        for year,y in yg.groupby('year'):
            y=y.set_index('model')
            if y.loc['rd_selected','dates']>=6 and y.loc['rd_selected','positives']>=10:
                eligible.append(int(year));year_pass.append(bool(y.loc['rd_selected','brier']<y.loc[['prior','logistic','static_tree'],'brier'].min()))
        stable=len(eligible)>=2 and all(year_pass)
        gates.append(dict(frequency=key[0],threshold=key[1],benchmark=key[2],aggregate_pass=aggregate,
            eligible_years=eligible,year_pass=year_pass,stable=stable,passed=bool(aggregate and stable)))
    frequency_gates={}
    for freq in ['W','BW','M']:
        passed=[t for t in [.1,.15,.2] if all(x['passed'] for x in gates if x['frequency']==freq and x['threshold']==t)]
        frequency_gates[freq]=dict(passed_thresholds=passed,passed=len(passed)>=2)
    accepted=any(x['passed'] for x in frequency_gates.values())
    js(dest/'verdict.json',dict(status='EXPLORATORY_GATE_PASS' if accepted else 'NO_SATISFACTORY_RESULT',
        frequency_gates=frequency_gates,task_gates=gates,advance_to_early_stage=bool(stage=='a' and not accepted),
        strict_PIT='BLOCKED_DATA',prospective='FORWARD_PENDING',independent_confirmation=False))
    task.to_csv(dest/'frequency_metrics.csv',index=False)
    # Event-level advance detection: repeated weekly hits count only once per event.
    eventrows=[]
    phases=pd.read_parquet(CACHE/'daily_phases.parquet').set_index('phase_id')
    selected=known[known.model.eq('rd_selected')]
    for key,g in selected.groupby(['frequency','threshold','benchmark','level']):
        events=g[g.y.eq(1)].event_or_witness_id.dropna().unique()
        hits=g[g.y.eq(1)&g.alert].groupby('event_or_witness_id').date.min()
        leads=[(phases.loc[e,'start_date']-date).days for e,date in hits.items()]
        eventrows.append(dict(frequency=key[0],threshold=key[1],benchmark=key[2],level=key[3],
            evaluable_events=len(events),detected_events=len(hits),event_recall=len(hits)/len(events) if len(events) else np.nan,
            median_lead_days=np.median(leads) if leads else np.nan,mean_lead_days=np.mean(leads) if leads else np.nan))
    pd.DataFrame(eventrows).to_csv(dest/'event_detection.csv',index=False)
    # Common monthly origins: compare W/BW predictions last issued on/before month-end with monthly forecasts.
    # We report issuance counts separately; do not pretend a denser series increases independent evidence.
    print('OUTER_VERDICT',stage,'PASS' if accepted else 'NO_SATISFACTORY_RESULT',frequency_gates,flush=True)
    return accepted


if __name__=='__main__':
    import sys
    stage='b' if '--stage-b' in sys.argv else 'a'
    if '--score-only' not in sys.argv:predict(stage)
    score(stage)
