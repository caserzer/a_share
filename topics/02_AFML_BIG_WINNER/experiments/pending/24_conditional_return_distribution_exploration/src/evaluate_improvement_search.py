"""R16 target scoreboard: same keys, coherent direction rule, all metrics/horizons."""
import argparse
import hashlib
import json
import numpy as np
import pandas as pd
from diagnose_prediction_target import DEST
METRICS=['brier','multiclass_brier','crps','accuracy']


def paired_margin_interval(new,base,metric,block=12):
    new=np.asarray(new);base=np.asarray(base);n=len(new)
    rng=np.random.default_rng(24);starts=rng.integers(0,n,size=(2000,int(np.ceil(n/block))))
    ix=((starts[:,:,None]+np.arange(block))%n).reshape(2000,-1)[:,:n]
    margin=new-1.2*base if metric=='accuracy' else .8*base-new
    return np.quantile(margin[ix].mean(axis=1),[.025,.975])


def evaluate(folder):
    manifest=json.loads((DEST/'target_contract.json').read_text())
    monthly=[];coverage=[]
    for source in manifest['files']:
        assert hashlib.sha256(open(source['path'],'rb').read()).hexdigest()==source['sha256']
        h=source['months'];path=folder/f'predictions_{h}m.parquet'
        if not path.exists():continue
        base=pd.read_parquet(source['path']);base=base[base.model=='B'].copy();base['model']='frozen_B'
        candidates=pd.read_parquet(path)
        expected=base[['date','instrument','actual']].rename(columns={'actual':'baseline_actual'})
        for name,g in candidates.groupby('model'):
            j=g.merge(expected,on=['date','instrument'],validate='one_to_one')
            assert len(j)==len(expected)==len(g),f'Population changed: {h} {name}'
            np.testing.assert_allclose(j.actual,j.baseline_actual,equal_nan=True)
        d=pd.concat([base,candidates],ignore_index=True);d=d[d.actual.notna()].copy()
        d['accuracy']=np.where(d.actual!=0,((d.p_up>d.p_down)==(d.actual>0)).astype(float),np.nan)
        m=d.groupby(['date','model'])[METRICS].mean().reset_index();m['months']=h;monthly.append(m)
        coverage.append(dict(months=h,models=candidates.model.nunique(),stock_dates=len(expected),observed=len(d[d.model=='frozen_B'])))
    if not monthly:raise RuntimeError('No completed horizon yet')
    m=pd.concat(monthly,ignore_index=True);m.to_csv(folder/'monthly_scores.csv',index=False)
    m.groupby(['months','model'])[METRICS].mean().to_csv(folder/'summary.csv')
    m['phase']=np.where(m.date<'2024-01-01','2021_2023','2024_plus')
    m.groupby(['months','phase','model'])[METRICS].mean().to_csv(folder/'phase_scores.csv')
    scores=[]
    for h,g in m.groupby('months'):
        for metric in METRICS:
            w=g.pivot(index='date',columns='model',values=metric)
            for model in w.columns:
                if model=='frozen_B':continue
                base=w.frozen_B.mean();value=w[model].mean()
                relative=value/base-1 if metric=='accuracy' else 1-value/base
                lo,hi=paired_margin_interval(w[model],w.frozen_B,metric)
                scores.append(dict(months=h,model=model,metric=metric,baseline=base,value=value,
                    relative_improvement=relative,target_relative=.2,point_target_met=bool(relative>=.2),
                    target_margin_lower95=lo,target_margin_upper95=hi,confidence_target_met=bool(lo>=0),origin_months=len(w)))
    score=pd.DataFrame(scores);score.to_csv(folder/'target_scoreboard.csv',index=False)
    decisions=[]
    for model,g in score.groupby('model'):
        complete=set(g.months)=={1,3,6} and len(g)==12
        decisions.append(dict(model=model,all_horizons_present=complete,all_point_targets_met=bool(complete and g.point_target_met.all()),
            all_confidence_targets_met=bool(complete and g.confidence_target_met.all())))
    result=dict(coverage=coverage,candidate_results=decisions,goal_achieved=False,
        note='A round is not the goal. Require all 12 gates, integrity audit and validation review before claiming achievement.')
    (folder/'target_audit.json').write_text(json.dumps(result,indent=2)+'\n')
    print(score[['months','model','metric','relative_improvement','point_target_met']].to_string(index=False))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--round',default='round1');a=p.parse_args();evaluate(DEST/a.round)
