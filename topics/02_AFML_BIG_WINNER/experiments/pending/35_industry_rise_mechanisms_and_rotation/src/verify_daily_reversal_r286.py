from common import *
import pandas as pd
from scipy.stats import rankdata

def run():
    out=ROOT/'outputs/r286';s=pd.read_parquet(out/'scores.parquet');d=pd.read_parquet(ROOT/'outputs/r155/evaluation/data/r09_daily_scores.parquet')
    models=[m for m in json.loads((ROOT/'outputs/r196/models.json').read_text()) if m['family']=='core' and m['cohort']=='F' and m['method']=='F' and m['task']=='reversal']
    cols=models[0]['columns'];ranks=pd.DataFrame(index=d.index,columns=cols,dtype=float)
    for _,g in d.groupby(['era','level','date']):
        for c in cols:ranks.loc[g.index,c]=(rankdata(g[c],method='average')-.5)/len(g)-.5
    maxerr=0.;checked=0
    states=pd.read_parquet(ROOT/'outputs/r195/market_regimes.parquet').regime
    for m in models:
        g=d[d.era.eq(m['era'])&d.level.eq(m['level'])&d.year.eq(m['year'])]
        z=s[s.era.eq(m['era'])&s.level.eq(m['level'])&s.year.eq(m['year'])&s.variant.eq(m['variant'])].set_index(KEY+['date']).loc[g.set_index(KEY+['date']).index]
        expected_eligible=g.mom60.gt(0)&g.past_excess60.gt(0)
        assert np.array_equal(expected_eligible,z.eligible)
        labels=(g.rel_trough20<=-.08).astype(float).where(g.excess20.notna()&g.rel_trough20.notna())
        np.testing.assert_equal(labels.to_numpy(),z.y.to_numpy())
        state=g.date.map(states);assert np.array_equal(state,z.regime)
        x=(ranks.loc[g.index,cols].to_numpy()-m['scaler_mean'])/m['scaler_scale'];coef=np.array(m['coefficient']).ravel()
        linear=np.sum(x*coef[:len(cols)],axis=1)+np.asarray(m['intercept']).item()
        if m['variant']!='base':
            for j,name in enumerate(['down_high','up_low','up_high']):
                mask=state.eq(name).to_numpy();linear+=mask*coef[len(cols)+j]
                if m['variant']=='interaction':linear+=mask*np.sum(x*coef[len(cols)+3+j*len(cols):len(cols)+3+(j+1)*len(cols)],axis=1)
        pred=1/(1+np.exp(-(linear*np.asarray(m['calibration_coefficient']).item()+np.asarray(m['calibration_intercept']).item())))
        error=float(np.max(np.abs(pred-z.score.to_numpy())));assert error<1e-12;maxerr=max(maxerr,error);checked+=len(z)
    assert checked==len(s) and not s.duplicated(KEY+['date','variant']).any()
    for _,g in s.groupby(['era','level','year']):
        assert g.groupby('variant').size().nunique()==1 and g.groupby('variant').eligible.sum().nunique()==1
    old=pd.read_parquet(ROOT/'outputs/r196/predictions.parquet');old=old[(old.family=='core')&(old.cohort=='F')&(old.method=='F')&(old.task=='reversal')]
    q=old.merge(s[s.eligible][KEY+['date','variant','score']],on=KEY+['date','variant'],validate='one_to_one');assert len(q)==len(old)
    assert (q.prediction-q.score).abs().max()<1e-12
    for r in pd.read_csv(out/'comparisons.csv').itertuples():
        g=s[s.era.eq(r.era)&s.level.eq(r.level)&s.year.eq(r.year)&s.eligible&s.y.notna()]
        v=g.assign(error=(g.score-g.y)**2).groupby(['date','variant']).error.mean().unstack()
        assert len(v)==r.dates and abs((v['base']-v[r.variant]).mean()-r.brier_reduction)<1e-12
    receipt=json.loads((out/'receipt.json').read_text())
    for p,h in receipt['inputs'].items():assert sha(ROOT/p)==h
    for p,h in receipt['outputs'].items():assert sha(out/p)==h
    js(out/'independent_verification.json',dict(status='PASS',prediction_rows=checked,models=len(models),monthly_rows=len(q),maximum_error=maxerr,scope='Independent rankdata and component-wise inference, target and eligibility, shared population, monthly identity and daily Brier; no forecast certification',verifier_sha256=sha(Path(__file__))))
    print('R286 VERIFIED',checked,len(q),maxerr)
if __name__=='__main__':run()
