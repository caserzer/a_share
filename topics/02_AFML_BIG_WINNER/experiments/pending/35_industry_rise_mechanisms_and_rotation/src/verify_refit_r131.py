"""Saved prediction checks plus independent Ridge / Logit fit diagnostics."""
import pandas as pd
from scipy.special import expit
from common import *
from verify_label_fold_r130 import prepared
from train_r02 import F

FK=['era','level','cohort','task','horizon','year'];PK=KEY+['date','cohort','method','task','horizon','year']

def run():
    out=ROOT/'outputs/r131';receipt=json.loads((out/'run_receipt.json').read_text())
    for p,h in receipt['reads'].items():assert sha(p)==h,p
    assert sha(out/'predictions.parquet')==receipt['prediction_sha256'] and sha(out/'model_parameters.json')==receipt['models_sha256']
    old_models=json.loads((ROOT/'outputs/r02/model_parameters.json').read_text());models=json.loads((out/'model_parameters.json').read_text());scope=json.loads((ROOT/'outputs/r130/retrain_scope.json').read_text())['folds'];scope_map={tuple(s[k] for k in FK):s for s in scope}
    panel=pd.read_parquet(ROOT/'outputs/r130/monthly_panel.parquet');pred=pd.read_parquet(out/'predictions.parquet');oldpred=pd.read_parquet(ROOT/'outputs/r02/predictions.parquet')
    changed_keys=set(scope_map);keep_old=~oldpred[FK].apply(tuple,axis=1).isin(changed_keys);keep_new=~pred[FK].apply(tuple,axis=1).isin(changed_keys)
    cols=[c for c in pred if c!='row_id'];pd.testing.assert_frame_equal(oldpred.loc[keep_old,cols].sort_values(PK).reset_index(drop=True),pred.loc[keep_new,cols].sort_values(PK).reset_index(drop=True),check_exact=True)
    modelmap={tuple(m[k] for k in FK)+(m['method'],):m for m in models};cache={};checks=[];maxerr=0.
    for oldm in old_models:
        key=tuple(oldm[k] for k in FK);mk=key+(oldm['method'],);m=modelmap[mk];scope_entry=scope_map.get(key)
        if scope_entry is None or scope_entry['action']!='refit_and_evaluate':assert m==oldm
        if scope_entry is None:continue
        era,level,cohort,task,h,year=key;ck=key[:-1]
        if ck not in cache:cache[ck]=prepared(panel,era,level,cohort,task,h)
        q,_=cache[ck];columns=m['columns'];cols=['rank_'+c for c in columns];jan=pd.Timestamp(year,1,1);jul=pd.Timestamp(year-1,7,1);boundary=jan if task=='return' else jul
        tr=q[(q.date<boundary)&(q[f'maturity{h}']<boundary)&q.y.notna()];ca=q[(q.date>=jul)&(q.date<jan)&(q[f'maturity{h}']<jan)&q.y.notna()] if task!='return' else q.iloc[:0];te=q[q.date.dt.year.eq(year)]
        w=len(tr)/(tr.date.nunique()*tr.groupby('date').date.transform('size')).to_numpy();raw=tr[cols].to_numpy();mean=np.array(m['scaler_mean']);scale=np.array(m['scaler_scale']);x=(raw-mean)/scale
        diag=dict(zip(FK,key),method=m['method'],action=scope_entry['action'])
        if scope_entry['action']=='refit_and_evaluate':
            assert np.allclose(raw.mean(axis=0),mean,rtol=1e-12,atol=1e-12);std=raw.std(axis=0);std[std==0]=1;assert np.allclose(std,scale,rtol=1e-12,atol=1e-12)
            coef=np.array(m['coefficient']).ravel();intercept=np.asarray(m['intercept']).item();z=x@coef+intercept
            if task=='return':
                a=np.column_stack([x,np.ones(len(x))]);penalty=np.diag([10.]*len(coef)+[0.]);solution=np.linalg.solve((a.T*w)@a+penalty,(a.T*w)@tr.y.to_numpy())
                error=float(np.max(np.abs(solution-np.r_[coef,intercept])));assert error<1e-8;diag['normal_equation_error']=error
            else:
                residual=w*(expit(z)-tr.y.to_numpy());gradient=np.r_[(x.T@residual+coef)/w.sum(),residual.sum()/w.sum()];norm=float(np.max(np.abs(gradient)));assert norm<1e-3;diag['fit_gradient_max']=norm
                cw=len(ca)/(ca.date.nunique()*ca.groupby('date').date.transform('size')).to_numpy();score=((ca[cols].to_numpy()-mean)/scale)@coef+intercept;cc=np.asarray(m['calibration_coefficient']).item();ci=np.asarray(m['calibration_intercept']).item();cr=cw*(expit(score*cc+ci)-ca.y.to_numpy());cg=max(abs((score@cr+cc)/cw.sum()),abs(cr.sum()/cw.sum()));assert cg<1e-3;diag['calibration_gradient_max']=float(cg)
        z=((te[cols].to_numpy()-mean)/scale)@np.array(m['coefficient']).ravel()+np.asarray(m['intercept']).item();expected=z if task=='return' else expit(z*np.asarray(m['calibration_coefficient']).item()+np.asarray(m['calibration_intercept']).item())
        selected=pred
        for k,value in zip(FK,key):selected=selected[selected[k].eq(value)]
        selected=selected[selected.method.eq(m['method'])].set_index(KEY+['date']);ix=pd.MultiIndex.from_frame(te[KEY+['date']]);assert set(ix)==set(selected.index)
        ordered=selected.loc[ix]
        for a,b in [('y','y'),('excess',f'excess{h}')]:assert np.allclose(ordered[a],te[b],atol=1e-12,rtol=1e-12,equal_nan=True)
        for a,b in [('entry_date','entry_date'),('maturity',f'maturity{h}')]:
            left=ordered[a].to_numpy();right=te[b].to_numpy();assert np.all((left==right)|(pd.isna(left)&pd.isna(right)))
        assert np.allclose(ordered.raw_prediction,z if task=='return' else expit(z),atol=1e-12,rtol=1e-12)
        assert np.allclose(ordered.training_mean,np.average(tr.y,weights=w),atol=1e-12,rtol=1e-12)
        error=float(np.max(np.abs(selected.loc[ix,'prediction'].to_numpy()-expected)));assert error<1e-12;maxerr=max(maxerr,error);diag['predictions']=len(te);checks.append(diag)
    assert sum(d['action']=='refit_and_evaluate' for d in checks)==80
    js(out/'verification.json',dict(status='PASS',models_checked=len(checks),refit_models=80,unchanged_prediction_rows=int(keep_old.sum()),max_prediction_error=maxerr,diagnostics=checks))
    print('PASS',len(checks),maxerr)

if __name__=='__main__':run()
