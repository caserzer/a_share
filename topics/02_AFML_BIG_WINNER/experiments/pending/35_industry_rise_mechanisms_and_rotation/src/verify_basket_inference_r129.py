"""Verify every formal sensitivity prediction with direct ranks and arithmetic."""
import pandas as pd
from scipy.special import expit
from common import *
from inference_bundle_r101 import INPUT,MK,F
from versioned_observations import digest_json

def run():
    out=ROOT/'outputs/r129';receipt=json.loads((out/'inference_impact.json').read_text())
    for p,digest in receipt['reads'].items():assert sha(p)==digest,p
    pp=out/'prediction_impact.parquet';assert sha(pp)==receipt['predictions_sha256'];pairs=pd.read_parquet(pp)
    models=[]
    for r in ['r02','r16']:models.extend(json.loads((ROOT/f'outputs/{r}/model_parameters.json').read_text()))
    modelmap={digest_json(m):m for m in models};l1=pd.read_parquet(ROOT/'data/l1_monthly_panel.parquet',columns=INPUT)
    sources={'old':ROOT/'data/monthly_panel.parquet','new':out/'features_2026-10-21.parquet'};maxerr=0.;checked=0
    for side,p in sources.items():
        f=pd.concat([pd.read_parquet(p,columns=INPUT),l1],ignore_index=True);f['log_members']=np.log(f.members.where(f.members.gt(0)))
        for date,g in pairs.groupby('asof'):
            for method in ['F','FD']:
                cols=F+(['breadth21','breadth63'] if method=='FD' else [])
                x=f[f.date.eq(date)&f.price_ready&np.isfinite(f[cols]).all(axis=1)].copy()
                for c in cols:
                    by=x.groupby(['era','level'])[c];x[c]=(by.rank(method='average')-.5)/by.transform('count')-.5
                x=x.set_index(KEY)
                selected=g[g.method.eq(method)&g[f'prediction_{side}'].notna()]
                for row in selected.to_dict('records'):
                    m=modelmap[row[f'model_sha256_{side}']];v=x.loc[tuple(row[k] for k in KEY),cols].to_numpy(float)
                    z=sum((v[i]-m['scaler_mean'][i])/m['scaler_scale'][i]*np.asarray(m['coefficient']).ravel()[i] for i in range(len(cols)))+np.asarray(m['intercept']).item()
                    value=z if row['task']=='return' else expit(z*np.asarray(m['calibration_coefficient']).item()+np.asarray(m['calibration_intercept']).item())
                    error=abs(value-row[f'prediction_{side}']);assert error<1e-12;maxerr=max(maxerr,error);checked+=1
    for item in receipt['dates']:
        g=pairs[pairs['asof'].eq(item['date'])];status=g.status_old.ne(g.status_new);changed=~np.isclose(g.prediction_old,g.prediction_new,atol=1e-12,rtol=1e-12,equal_nan=True)
        assert len(g)==item['rows'] and int(status.sum())==item['status_changed'] and int(changed.sum())==item['prediction_changed']
        assert status.equals(g.status_changed);assert np.array_equal(changed,g.prediction_changed)
    js(out/'inference_verification.json',dict(status='PASS',formal_predictions_checked=checked,max_absolute_error=maxerr,scope='Fixed coefficients; no retraining assurance'))
    print('PASS',checked,maxerr)

if __name__=='__main__':run()
