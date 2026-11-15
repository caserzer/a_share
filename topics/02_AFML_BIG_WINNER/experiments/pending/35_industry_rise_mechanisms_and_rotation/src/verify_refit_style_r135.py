"""Verify scope preservation, independent matrix predictions and fit stationarity."""
import pandas as pd
from scipy.special import expit
from common import *
K=KEY+['date'];FK=['era','level','task','horizon','year']
def ident(m):return tuple(m.get(k,'return' if k=='task' else None) for k in FK)+(m['method'],)
def run():
 out=ROOT/'outputs/r135';panel=pd.read_parquet(ROOT/'outputs/r134/common_panel_new.parquet');scope=json.loads((ROOT/'outputs/r134/retrain_scope.json').read_text());wanted={tuple(f[k] for k in FK)+(method,) for f in scope['folds'] for method in f['methods']};error=0.;ridgeerr=0.;graderr=0.;rows=0;changed=set();untouched=0
 for p,h in json.loads((out/'receipt.json').read_text())['reads'].items():assert sha(p)==h
 for family in ['r55','r56']:
  old=json.loads((ROOT/f'outputs/{family}/model_parameters.json').read_text());new=json.loads((out/family/'model_parameters.json').read_text());om={ident(m):m for m in old};nm={ident(m):m for m in new};assert om.keys()==nm.keys()
  op=pd.read_parquet(ROOT/f'outputs/{family}/predictions.parquet');p=pd.read_parquet(out/family/'predictions.parquet');assert p.shape==op.shape
  for key,m in nm.items():
   mask=p.method.eq(m['method'])
   for k in FK:
    if k in p:mask &= p[k].eq(m[k])
   z=p[mask];o=op[mask]
   if key not in wanted:assert m==om[key];pd.testing.assert_frame_equal(z,o);untouched+=len(z)
   else:changed.add(key)
   g=panel[panel.era.eq(m['era'])&panel.level.eq(m['level'])].copy();h=m['horizon'];task=m.get('task','return');valid=g[f'excess{h}'].notna()
   if task=='return':g['y']=g[f'excess{h}']
   elif task=='onset':g['y']=((g[f'return{h}']>=(.05 if h==20 else .10))&(g[f'excess{h}']>=(.03 if h==20 else .05))).astype(float).where(valid);g=g[g.past_excess20.le(0)]
   else:g['y']=g[f'rel_trough{h}'].le(-.08 if h==20 else -.12).astype(float).where(valid&g[f'rel_trough{h}'].notna());g=g[g.mom60.gt(0)&g.past_excess60.gt(0)]
   start=pd.Timestamp(m['year'],1,1);cut=start if task=='return' else pd.Timestamp(m['year']-1,7,1);tr=g[g.date.lt(cut)&g[f'maturity{h}'].lt(cut)&g.y.notna()];ca=g[g.date.ge(cut)&g.date.lt(start)&g[f'maturity{h}'].lt(start)&g.y.notna()];te=g[g.date.dt.year.eq(m['year'])].set_index(K);ix=pd.MultiIndex.from_frame(z[K]);assert set(ix)==set(te.index);te=te.loc[ix]
   cols=['rank_'+c for c in m['columns']];mean=np.array(m['mean' if family=='r55' else 'scaler_mean']);scale=np.array(m['scale' if family=='r55' else 'scaler_scale']);b=np.array(m['coef' if family=='r55' else 'coefficient']).reshape(-1);inter=float(np.array(m['intercept']).ravel()[0]);x=(tr[cols].to_numpy()-mean)/scale;xt=(te[cols].to_numpy()-mean)/scale;score=xt@b+inter
   assert np.allclose(tr[cols].mean(),mean,atol=1e-12);assert np.allclose(tr[cols].std(ddof=0),scale,atol=1e-12)
   w=(len(tr)/(tr.date.nunique()*tr.groupby('date').date.transform('size'))).to_numpy();f=x@b+inter
   if family=='r55':
    pred=score;assert np.allclose(z.target,te.y,equal_nan=True)
    if key in wanted:err=np.max(np.abs(np.r_[x.T@(w*(f-tr.y))+10*b,np.sum(w*(f-tr.y))]))/w.sum();ridgeerr=max(ridgeerr,float(err));assert err<1e-10
   else:
    a=float(np.array(m['calibration_coefficient']).ravel()[0]);c=float(np.array(m['calibration_intercept']).ravel()[0]);pred=expit(score*a+c);assert np.allclose(z.raw_prediction,expit(score),atol=1e-12);assert np.allclose(z.y,te.y,equal_nan=True);assert np.allclose(z.excess,te[f'excess{h}'],equal_nan=True);assert np.allclose(z.training_mean,np.average(tr.y,weights=w))
    if key in wanted:
     residual=w*(expit(f)-tr.y);err=np.max(np.abs(np.r_[x.T@residual+b,residual.sum()]))/w.sum();graderr=max(graderr,float(err));assert err<1e-3
     ds=((ca[cols].to_numpy()-mean)/scale)@b+inter;cw=(len(ca)/(ca.date.nunique()*ca.groupby('date').date.transform('size'))).to_numpy();res=cw*(expit(ds*a+c)-ca.y);err=max(abs(ds@res+a),abs(res.sum()))/cw.sum();graderr=max(graderr,float(err));assert err<1e-3
   assert np.all((z.maturity.to_numpy()==te[f'maturity{h}'].to_numpy())|(z.maturity.isna().to_numpy()&te[f'maturity{h}'].isna().to_numpy()))
   e=float(np.max(np.abs(pred-z.prediction)));error=max(error,e);assert e<1e-12;rows+=len(z)
 assert changed==wanted
 js(out/'refit_verification.json',dict(status='PASS',refits=len(changed),prediction_rows=rows,untouched_rows=untouched,max_prediction_error=error,max_ridge_stationarity=ridgeerr,max_logit_stationarity=graderr,verifier_sha256=sha(__file__)))
 print('VERIFIED',rows,len(changed),error,flush=True)
if __name__=='__main__':run()
