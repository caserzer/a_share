from pathlib import Path
import sys,json
import pandas as pd
import numpy as np
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'outputs';E=ROOT.parent
V6=E/'v6_economic_diffusion';V7=E/'v7_online_stage';V13=E/'v13_completed_history'
sys.path.insert(0,str(V6/'src'))
from statistics6 import block_summary,bh
from context6 import sha,js


def run():
    OUT.mkdir(exist_ok=True,parents=True)
    previous=json.loads((V13/'outputs/predecessors.json').read_text())
    m=json.loads((V13/'outputs/manifest.json').read_text())
    previous.update({str(V13/f['path']):f['sha256'] for f in m['files']});previous[str(V13/'outputs/manifest.json')]=sha(V13/'outputs/manifest.json')
    assert all(sha(p)==h for p,h in previous.items());js(OUT/'predecessors.json',previous)
    base=pd.read_csv(V7/'outputs/monthly_brier_gains.csv').query("cohort=='fixed24'").set_index('month')
    models={'rd_gate':base.rd_gate_gain,'rd_state':base.rd_state_gain,'rd_conditional':base.rd_conditional_gain}
    roots=['v8_pooled_stage','v9_market_context','v10_label_delay','v12_duration_risk','v13_completed_history']
    historical=list(pd.read_csv(V6/'outputs/primary_tests.csv').p_one_sided)
    inputs={str(V7/'outputs/monthly_brier_gains.csv'):sha(V7/'outputs/monthly_brier_gains.csv')}
    for root in roots:
        path=E/root/'outputs/monthly_brier_gains.csv';g=pd.read_csv(path).query("cohort=='fixed24'").set_index('month')
        assert g.index.equals(base.index)
        for col in g.columns:
            if col.endswith('_gain'):models[col[:-5]]=g[col]+base.rd_gate_gain
        historical.extend(pd.read_csv(E/root/'outputs/primary_tests.csv').p_one_sided)
        inputs[str(path)]=sha(path)
    assert len(models)==18 and len(historical)==21
    rows=[]
    for name,g in models.items():
        r=block_summary(g);r['model']=name;rows.append(r)
    tests=pd.DataFrame(rows);tests['q_bh_39']=bh(np.r_[historical,tests.p_one_sided])[-18:]
    tests['supported']=tests.effect.gt(0)&tests.ci_low.gt(0)&tests.q_bh_39.lt(.05)
    tests.to_csv(OUT/'relative_rd_tests.csv',index=False)
    pd.DataFrame(models).reset_index().to_csv(OUT/'monthly_relative_rd.csv',index=False)
    annual=pd.read_csv(V13/'outputs/annual_metrics.csv').query("cohort=='fixed24'")
    keys=['frequency','threshold','benchmark','year','model']
    tasks=annual.groupby(keys).agg(brier=('brier','mean'),dates=('dates','min'),positives=('positives','sum')).reset_index()
    baseline=tasks[tasks.model.eq('rd_selected')].drop(columns='model').rename(columns={'brier':'rd_brier','dates':'rd_dates','positives':'rd_positives'})
    matched=tasks.merge(baseline,on=keys[:-1],validate='many_to_one')
    matched['relative_gain']=1-matched.brier/matched.rd_brier
    matched['evaluable']=matched.dates.ge(6)&matched.positives.ge(10)
    matched.to_csv(OUT/'task_year_comparisons.csv',index=False)
    summary=[]
    for name,g in matched[matched.model.isin(models)].groupby('model'):
        good=g[g.evaluable]
        summary.append(dict(model=name,evaluable_task_years=len(good),improved_task_years=int(good.relative_gain.gt(0).sum()),
            fraction_improved=float(good.relative_gain.gt(0).mean()),worst_relative_gain=float(good.relative_gain.min())))
    summary=pd.DataFrame(summary).merge(tests,on='model')
    overall=pd.read_csv(V13/'outputs/overall.csv').query("cohort=='fixed24'")
    summary=summary.merge(overall[['model','rd_gain','top10_precision','top10_lift']],on='model',validate='one_to_one')
    summary.to_csv(OUT/'summary.csv',index=False)
    annualsummary=pd.read_csv(V13/'outputs/annual_summary.csv').query("cohort=='fixed24'")
    annualsummary[annualsummary.model.isin(models)].to_csv(OUT/'year_frequency_comparisons.csv',index=False)
    js(OUT/'audit.json',dict(plan_sha256=sha(ROOT/'research_plan.md'),code_sha256=sha(__file__),inputs=inputs,
        candidates=18,total_comparisons=39,independent_holdout=False,does_not_replace_original_gate=True))
    print(summary[['model','rd_gain','top10_precision','top10_lift','fraction_improved','worst_relative_gain','q_bh_39','supported']].to_string(index=False),flush=True)


if __name__=='__main__':run()
