"""Score saved forecasts using fixed follow-up and unchanged acceptance gates."""
import json,sys
import numpy as np
import pandas as pd
from context13 import ROOT,V5,V6,V7,V8,V9,V10,V12,CACHE,OLD,OUT,sha,js,finite_json
from outer import evaluate_rows
sys.path.insert(0,str(V6/'src'))
from statistics6 import block_summary,bh

CANDIDATES=['history_tree','history_blend','history_prior_blend']
BASELINES=['prior','logistic','static_tree','rd_selected','rd_gate']


def score():
    receipt=json.loads((OUT/'prediction_receipt.json').read_text())
    assert receipt['frozen_sha256']==sha(OUT/'frozen_candidates.json')
    labels=pd.read_parquet(OLD/'stage_b_labels.parquet')
    phases=pd.read_parquet(OLD/'daily_phases.parquet').set_index('phase_id')
    metrics=[];annual=[];coverage=[];daily_losses=[];eventrows=[];audits=[];bounds=[]
    for artifact in receipt['tasks']:
        assert sha(artifact['path'])==artifact['sha256']
        p=pd.read_parquet(artifact['path'])
        assert not any(c in p for c in ['y','label_available_at','event_or_witness_id'])
        p=p.merge(labels,on=['row_id','threshold','benchmark'],validate='many_to_one')
        assert not ((p.y==1)&(p.state_eligible==0)).any()
        for cohort,mask in [('fixed24',p.date.ge('2021-01-01')&p.date.le('2024-09-30')),
                            ('legacy_current',p.date.ge('2024-01-01'))]:
            g=p[mask].copy()
            if cohort=='fixed24':g.loc[g.label_available_at.gt(g.date+pd.DateOffset(months=24)),'y']=np.nan
            g['year']=g.date.dt.year
            g['known_alert']=g.alert&g.y.notna();g['unknown_alert']=g.alert&g.y.isna()
            g['zero_alert']=g.alert&g.prob.eq(0)
            keys=['frequency','threshold','benchmark','model','level']
            for key,sub in g.groupby(keys+['year']):
                coverage.append(dict(zip(keys+['year'],key),cohort=cohort,observations=len(sub),
                    known=int(sub.y.notna().sum()),unknown=int(sub.y.isna().sum()),positives=int(sub.y.sum()),
                    alerts=int(sub.alert.sum()),known_alerts=int(sub.known_alert.sum()),unknown_alerts=int(sub.unknown_alert.sum()),
                    true_alerts=int(sub.loc[sub.alert,'y'].sum()),
                    zero_alerts=int(sub.zero_alert.sum()),eligible=int(sub.state_eligible.sum())))
            for key,sub in g.groupby(keys+['date']):
                alerts=sub[sub.alert];n=len(sub);k=len(alerts)
                if not k:continue
                bounds.append(dict(zip(keys+['date'],key),cohort=cohort,
                    precision_lower=float(alerts.y.sum()/k),precision_upper=float((alerts.y.sum()+alerts.y.isna().sum())/k),
                    prevalence_lower=float(sub.y.sum()/n),prevalence_upper=float((sub.y.sum()+sub.y.isna().sum())/n)))
            known=g[g.y.notna()].copy();known['loss']=(known.prob-known.y)**2
            for key,sub in known.groupby(keys[:-1]):
                for r in evaluate_rows(sub):r.update(zip(keys[:-1],key));r['cohort']=cohort;metrics.append(r)
            for key,sub in known.groupby(keys[:-1]+['year']):
                for r in evaluate_rows(sub):r.update(zip(keys[:-1]+['year'],key));r['cohort']=cohort;annual.append(r)
            losses=known.groupby(['frequency','threshold','benchmark','level','date','model']).loss.mean().unstack('model').reset_index()
            losses['cohort']=cohort;daily_losses.append(losses)
            for key,sub in known.groupby(keys):
                events=sub[sub.y.eq(1)].event_or_witness_id.dropna().unique()
                hits=sub[sub.y.eq(1)&sub.alert].groupby('event_or_witness_id').date.min()
                delay=[(t-phases.loc[e,'start_date']).days for e,t in hits.items()]
                eventrows.append(dict(zip(keys,key),cohort=cohort,evaluable_events=len(events),detected_events=len(hits),
                    event_recall=len(hits)/len(events) if len(events) else np.nan,
                    median_delay_days=np.median(delay) if delay else np.nan,mean_delay_days=np.mean(delay) if delay else np.nan))
            audits.append(dict(task=artifact['task'],cohort=cohort,rows=len(g),known=len(known)))
    m=pd.DataFrame(metrics);a=pd.DataFrame(annual);c=pd.DataFrame(coverage);e=pd.DataFrame(eventrows)
    m.to_csv(OUT/'metrics.csv',index=False);a.to_csv(OUT/'annual_metrics.csv',index=False)
    c.to_csv(OUT/'coverage.csv',index=False);e.to_csv(OUT/'event_detection.csv',index=False)
    bounds=pd.DataFrame(bounds)
    bounds.groupby(['cohort','frequency','threshold','benchmark','level','model'])[['precision_lower','precision_upper','prevalence_lower','prevalence_upper']].mean().reset_index().to_csv(OUT/'unknown_label_bounds.csv',index=False)
    loss=pd.concat(daily_losses,ignore_index=True)
    loss['month']=loss.date.dt.to_period('M').astype(str)
    for name in CANDIDATES:loss[name+'_gain']=loss.rd_gate-loss[name]
    gains=[n+'_gain' for n in CANDIDATES]
    monthly=loss.groupby(['cohort','frequency','threshold','benchmark','level','month'])[gains].mean().reset_index()
    overall=monthly.groupby(['cohort','month'])[gains].mean().reset_index()
    overall.to_csv(OUT/'monthly_brier_gains.csv',index=False)
    monthly.to_csv(OUT/'monthly_task_gains.csv',index=False)
    tests=[]
    for name in CANDIDATES:
        r=block_summary(overall.loc[overall.cohort.eq('fixed24'),name+'_gain'])
        r['candidate']=name;tests.append(r)
    tests=pd.DataFrame(tests)
    historical=np.r_[pd.read_csv(V6/'outputs/primary_tests.csv').p_one_sided,pd.read_csv(V7/'outputs/primary_tests.csv').p_one_sided,pd.read_csv(V8/'outputs/primary_tests.csv').p_one_sided,pd.read_csv(V9/'outputs/primary_tests.csv').p_one_sided,pd.read_csv(V10/'outputs/primary_tests.csv').p_one_sided,pd.read_csv(V12/'outputs/primary_tests.csv').p_one_sided]
    tests['q_bh']=bh(np.r_[historical,tests.p_one_sided])[-len(tests):]
    tests['family_size']=len(historical)+len(tests)
    tests['supported']=tests.effect.gt(0)&tests.ci_low.gt(0)&tests.q_bh.lt(.05)
    tests.to_csv(OUT/'primary_tests.csv',index=False)
    keys=['cohort','frequency','threshold','benchmark','model']
    task=m.groupby(keys)[['brier','brier_skill','top10_precision','top10_lift','pr_auc']].mean().reset_index()
    task.to_csv(OUT/'task_metrics.csv',index=False)
    yearly=a.groupby(keys+['year']).agg(brier=('brier','mean'),dates=('dates','min'),positives=('positives','sum')).reset_index()
    taskgates=[]
    for key,sub in task[task.cohort.eq('fixed24')].groupby(['frequency','threshold','benchmark']):
        scores=sub.set_index('model');best=scores.loc[BASELINES,'brier'].min()
        yg=yearly[yearly.cohort.eq('fixed24')&yearly.frequency.eq(key[0])&yearly.threshold.eq(key[1])&yearly.benchmark.eq(key[2])]
        for name in CANDIDATES:
            candidate=scores.loc[name];years=[];passes=[]
            for year,y in yg.groupby('year'):
                y=y.set_index('model')
                if y.loc[name,'dates']>=6 and y.loc[name,'positives']>=10:
                    years.append(int(year));passes.append(bool(y.loc[name,'brier']<y.loc[BASELINES,'brier'].min()))
            aggregate=bool(candidate.brier<best and candidate.top10_lift>=2)
            stable=len(years)>=2 and all(passes)
            taskgates.append(dict(frequency=key[0],threshold=key[1],benchmark=key[2],candidate=name,
                aggregate_pass=aggregate,stable=bool(stable),eligible_years=years,year_pass=passes,
                passed=bool(aggregate and stable)))
    freqgates={}
    for name in CANDIDATES:
        freqgates[name]={}
        for freq in ['W','BW','M']:
            passed=[t for t in [.1,.15,.2] if all(r['passed'] for r in taskgates if r['candidate']==name and r['frequency']==freq and r['threshold']==t)]
            stats=bool(tests.set_index('candidate').loc[name,'supported'])
            freqgates[name][freq]=dict(passed_thresholds=passed,passed=len(passed)>=2 and stats)
    accepted=any(r['passed'] for v in freqgates.values() for r in v.values())
    js(OUT/'verdict.json',dict(status='EXPLORATORY_GATE_PASS' if accepted else 'NO_SATISFACTORY_RESULT',
        frequency_gates=freqgates,task_gates=taskgates,strict_PIT='BLOCKED_DATA',independent_confirmation=False,
        primary_followup_months=24,prospective='FORWARD_PENDING'))
    js(OUT/'score_audit.json',dict(prediction_receipt_sha256=sha(OUT/'prediction_receipt.json'),cohorts=audits,
        original_labels_sha256=sha(OLD/'stage_b_labels.parquet'),all_positive_labels_pass_state_gate=True))
    print(tests.to_string(index=False),flush=True)
    print('V13 verdict',json.dumps(freqgates),flush=True)


if __name__=='__main__':score()
