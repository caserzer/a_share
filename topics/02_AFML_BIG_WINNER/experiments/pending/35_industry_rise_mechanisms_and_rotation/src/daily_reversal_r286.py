from common import *
import pandas as pd
from scipy.special import expit
from regime_core_r196 import arrays
from train_r02 import target

def run():
    out=ROOT/'outputs/r286';out.mkdir(exist_ok=True)
    protocol=json.loads((ROOT/'protocols/r286.json').read_text())
    allmodels=json.loads((ROOT/'outputs/r196/models.json').read_text())
    models=[m for m in allmodels if m['family']=='core' and m['cohort']=='F' and m['method']=='F' and m['task']=='reversal']
    assert models and all(m['horizon']==20 and m['converged'] for m in models)
    d=pd.read_parquet(ROOT/'outputs/r155/evaluation/data/r09_daily_scores.parquet').drop(columns=['score','eligible','y'])
    assert d.price_ready.all() and not d.duplicated(KEY+['date']).any()
    states=pd.read_parquet(ROOT/'outputs/r195/market_regimes.parquet').regime
    d['regime']=d.date.map(states);assert d.regime.notna().all()
    d['y'],d['eligible']=target(d,'reversal',20)
    cols=models[0]['columns'];ranks=d.groupby(['era','level','date'])[cols].transform(centered_rank);parts=[];folds=[]
    for m in models:
        assert m['columns']==cols
        g=d[d.era.eq(m['era'])&d.level.eq(m['level'])&d.year.eq(m['year'])].copy()
        assert len(g)
        x=(ranks.loc[g.index,cols].to_numpy()-m['scaler_mean'])/m['scaler_scale'];x=arrays(x,g.regime)[m['variant']]
        z=x@np.asarray(m['coefficient']).ravel()+np.asarray(m['intercept']).item()
        g['score']=expit(z*np.asarray(m['calibration_coefficient']).item()+np.asarray(m['calibration_intercept']).item())
        g['variant']=m['variant'];g['horizon']=20;parts.append(g)
        e=g[g.eligible];folds.append(dict(era=m['era'],level=m['level'],year=m['year'],variant=m['variant'],horizon=20,price_rows=len(g),eligible_rows=len(e),dates=e.date.nunique(),known=int(e.y.notna().sum()),unknown=int(e.y.isna().sum())))
    scored=pd.concat(parts,ignore_index=True)
    old=pd.read_parquet(ROOT/'outputs/r196/predictions.parquet');old=old[(old.family=='core')&(old.cohort=='F')&(old.method=='F')&(old.task=='reversal')]
    matched=old.merge(scored[scored.eligible][KEY+['date','variant','horizon','score','y']],on=KEY+['date','variant','horizon'],how='left',suffixes=('_old','_daily'),validate='one_to_one')
    assert matched.score.notna().all()
    error=float((matched.prediction-matched.score).abs().max());assert error<1e-10
    assert ((matched.y_old==matched.y_daily)|(matched.y_old.isna()&matched.y_daily.isna())).all()
    scored.to_parquet(out/'scores.parquet',index=False);pd.DataFrame(folds).to_csv(out/'fold_coverage.csv',index=False)
    e=scored[scored.eligible & scored.y.notna()].copy();e['brier']=(e.score-e.y)**2
    daily=e.groupby(['era','level','year','date','variant']).agg(brier=('brier','mean'),rows=('y','size'),prevalence=('y','mean')).reset_index();daily.to_csv(out/'date_metrics.csv',index=False)
    wide=daily.pivot(index=['era','level','year','date'],columns='variant',values='brier');assert wide.notna().all().all()
    rows=[]
    for key,g in wide.groupby(level=['era','level','year']):
        for variant in ['state','interaction']:rows.append(dict(zip(['era','level','year'],key),variant=variant,dates=len(g),brier_reduction=float((g['base']-g[variant]).mean())))
    pd.DataFrame(rows).to_csv(out/'comparisons.csv',index=False)
    summary=dict(status='PASS',models=len(models),annual_folds=len(models)//3,daily_prediction_rows=len(scored),unique_price_rows=len(scored)//3,eligible_prediction_rows=int(scored.eligible.sum()),unknown_eligible=int((scored.eligible&scored.y.isna()).sum()),monthly_matched_rows=len(matched),monthly_max_error=error,horizons_with_parameters=sorted(set(m['horizon'] for m in models)),no_refit=True,adoption=False,daily_calibration_certified=False)
    js(out/'summary.json',summary)
    reads=protocol['inputs']+['protocols/r286.json','src/daily_reversal_r286.py','src/train_r02.py','src/regime_core_r196.py']
    js(out/'receipt.json',dict(inputs={p:sha(ROOT/p) for p in reads},outputs={p.name:sha(p) for p in out.iterdir() if p.name!='receipt.json'}))
    print(summary)
if __name__=='__main__':run()
