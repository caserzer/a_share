"""Refit only the frozen R134 scope; preserve untouched results."""
import copy
import pandas as pd
from sklearn.linear_model import Ridge,LogisticRegression
from sklearn.preprocessing import StandardScaler
from common import *
from train_r02 import target,train_masks,sample_weights
from style_models_r55 import METHODS
FK=['era','level','task','horizon','year']; PK=KEY+['date','method','horizon','year']

def prepared(panel,f):
    q=panel[panel.era.eq(f['era'])&panel.level.eq(f['level'])].copy();y,ok=target(q,f['task'],f['horizon']);q=q[ok].copy();q['y']=y[ok]
    return [q[m] for m in train_masks(q,f['year'],f['horizon'],f['task'])]

def run():
    out=ROOT/'outputs/r135';sp=ROOT/'outputs/r134/retrain_scope.json';pp=ROOT/'outputs/r134/common_panel_new.parquet';panel=pd.read_parquet(pp);scope=json.loads(sp.read_text());reads=[sp,pp,ROOT/'protocols/r135.json',Path(__file__),ROOT/'src/train_r02.py',ROOT/'src/style_models_r55.py'];changes=[]
    for family in ['r55','r56']:
        dest=out/family;dest.mkdir(exist_ok=True);oldp=ROOT/f'outputs/{family}/predictions.parquet';oldm=ROOT/f'outputs/{family}/model_parameters.json';reads += [oldp,oldm]
        original=pd.read_parquet(oldp);models=json.loads(oldm.read_text());newmodels=copy.deepcopy(models);pieces=[];remove=np.zeros(len(original),bool)
        for f in scope['folds']:
            if f['family']!=family:continue
            tr,ca,te=prepared(panel,f);h=f['horizon'];w=sample_weights(tr)
            for method in f['methods']:
                cols=METHODS[method];xc=['rank_'+c for c in cols];sc=StandardScaler().fit(tr[xc]);x=sc.transform(tr[xc]);xt=sc.transform(te[xc]);platt=None
                if family=='r55':model=Ridge(alpha=10).fit(x,tr.y,sample_weight=w);pred=model.predict(xt)
                else:
                    model=LogisticRegression(C=1,max_iter=2000,random_state=3502).fit(x,tr.y,sample_weight=w)
                    platt=LogisticRegression(C=1,max_iter=2000,random_state=3502).fit(model.decision_function(sc.transform(ca[xc])).reshape(-1,1),ca.y,sample_weight=sample_weights(ca));pred=platt.predict_proba(model.decision_function(xt).reshape(-1,1))[:,1]
                idx=[i for i,m in enumerate(models) if m['method']==method and all(m.get(k,'return' if k=='task' else None)==f[k] for k in FK)];assert len(idx)==1;rec=newmodels[idx[0]]
                mask=original.method.eq(method)
                for k in FK:
                    if k in original:mask &= original[k].eq(f[k])
                assert mask.sum()==len(te);remove|=mask.to_numpy();q=original.loc[mask].copy();keys=KEY+['date'];t=te.set_index(keys);indices=pd.MultiIndex.from_frame(q[keys]);assert set(indices)==set(t.index)
                predmap=pd.Series(pred,index=pd.MultiIndex.from_frame(te[keys]));q['prediction']=predmap.loc[indices].to_numpy()
                if family=='r55':rec.update(train_rows=len(tr),train_months=tr.date.nunique(),test_rows=len(te),max_maturity=tr[f'maturity{h}'].max(),mean=sc.mean_.tolist(),scale=sc.scale_.tolist(),coef=model.coef_.tolist(),intercept=float(model.intercept_))
                else:
                    q['raw_prediction']=pd.Series(model.predict_proba(xt)[:,1],index=pd.MultiIndex.from_frame(te[keys])).loc[indices].to_numpy();q['training_mean']=np.average(tr.y,weights=w)
                    rec.update(n_fit=len(tr),n_cal=len(ca),n_test=len(te),train_months=tr.date.nunique(),cal_months=ca.date.nunique(),fit_max_maturity=tr[f'maturity{h}'].max(),cal_max_maturity=ca[f'maturity{h}'].max(),scaler_mean=sc.mean_.tolist(),scaler_scale=sc.scale_.tolist(),coefficient=model.coef_.tolist(),intercept=np.asarray(model.intercept_).tolist(),calibration_coefficient=platt.coef_.tolist(),calibration_intercept=platt.intercept_.tolist())
                pieces.append(q);changes.append(dict(**{k:f[k] for k in FK},method=method,rows=len(q),max_prediction_change=float(np.max(np.abs(q.prediction.to_numpy()-original.loc[mask,'prediction'].to_numpy())))))
        result=pd.concat([original.loc[~remove]]+pieces).sort_index();assert result.index.equals(original.index);result.to_parquet(dest/'predictions.parquet',index=False);js(dest/'model_parameters.json',newmodels)
        pd.testing.assert_frame_equal(result.loc[~remove],original.loc[~remove]);js(dest/'preservation.json',dict(rows=len(result),untouched_rows=int((~remove).sum()),refitted_rows=int(remove.sum()),row_id='legacy identity retained; join by era/level/industry/date only'))
    js(out/'changes.json',changes);js(out/'receipt.json',dict(reads={str(p):sha(p) for p in reads},refits=len(changes),required_models=scope['required_models'],quality='Historical-proxy fixed-parameter repair'));assert len(changes)==60
    print('REFIT',len(changes),flush=True)
if __name__=='__main__':run()
