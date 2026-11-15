"""Exact-scope R02 refits; all prior artifacts remain immutable."""
import pandas as pd
from scipy.special import expit
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge,LogisticRegression
from common import *
from train_r02 import F,EXTRA,target,train_masks,sample_weights
FK=['era','level','cohort','task','horizon','year'];PK=KEY+['date','cohort','method','task','horizon','year']


def prepare(panel,era,level,cohort,task,h):
    cols=F+EXTRA[cohort];g=panel[panel.era.eq(era)&panel.level.eq(level)&panel.price_ready].dropna(subset=cols).copy()
    ranks=g.groupby('date')[cols].transform(centered_rank);y,eligible=target(g,task,h);q=g[eligible].copy();q['y']=y[eligible]
    return q,ranks


def predict_saved(m,ranks):
    z=((ranks.to_numpy()-np.array(m['scaler_mean']))/np.array(m['scaler_scale']))@np.array(m['coefficient']).ravel()+np.asarray(m['intercept']).item()
    if m['task']=='return':return z,z
    return expit(z*np.asarray(m['calibration_coefficient']).item()+np.asarray(m['calibration_intercept']).item()),expit(z)


def run():
    out=ROOT/'outputs/r131';out.mkdir(exist_ok=True)
    pp=ROOT/'outputs/r130/monthly_panel.parquet';sp=ROOT/'outputs/r130/retrain_scope.json';mp=ROOT/'outputs/r02/model_parameters.json';op=ROOT/'outputs/r02/predictions.parquet';lp=ROOT/'outputs/r130/fold_ledger.csv'
    scope=json.loads(sp.read_text())['folds'];panel=pd.read_parquet(pp);panel['log_members']=np.log(panel.members.where(panel.members.gt(0)))
    models=json.loads(mp.read_text());modelmap={tuple(m[k] for k in FK)+(m['method'],):m for m in models}
    ledger=pd.read_csv(lp);ledger=ledger[ledger.version.eq('new')].set_index(FK)
    old=pd.read_parquet(op);changed_keys={tuple(s[k] for k in FK) for s in scope}
    keep=~old[FK].apply(tuple,axis=1).isin(changed_keys);parts=[old[keep].drop(columns='row_id')];updated={};actions=[]
    for s in scope:
        key=tuple(s[k] for k in FK);era,level,cohort,task,h,year=key;q,ranks=prepare(panel,era,level,cohort,task,h)
        fit,cal,test=train_masks(q,year,h,task);tr=q[fit];ca=q[cal];te=q[test];rec=ledger.loc[key];assert rec.status=='fit';w=sample_weights(tr)
        for method in s['methods']:
            mk=key+(method,);oldm=modelmap[mk];cols=oldm['columns'];m=oldm
            if s['action']=='refit_and_evaluate':
                scaler=StandardScaler().fit(ranks.loc[tr.index,cols]);x=scaler.transform(ranks.loc[tr.index,cols])
                if task=='return':model=Ridge(alpha=10).fit(x,tr.y,sample_weight=w);platt=None
                else:
                    model=LogisticRegression(C=1,max_iter=2000,random_state=3502).fit(x,tr.y,sample_weight=w)
                    xc=scaler.transform(ranks.loc[ca.index,cols]);ds=model.decision_function(xc).reshape(-1,1)
                    platt=LogisticRegression(C=1,max_iter=2000,random_state=3502).fit(ds,ca.y,sample_weight=sample_weights(ca))
                m=dict(oldm,**{k:rec[k] for k in ['n_fit','n_cal','n_test','train_months','cal_months','fit_max_maturity','cal_max_maturity']},scaler_mean=scaler.mean_.tolist(),scaler_scale=scaler.scale_.tolist(),coefficient=model.coef_.tolist(),intercept=np.asarray(model.intercept_).tolist(),calibration_coefficient=platt.coef_.tolist() if platt is not None else None,calibration_intercept=platt.intercept_.tolist() if platt is not None else None)
                updated[mk]=m
            prediction,raw=predict_saved(m,ranks.loc[te.index,cols])
            p=te[KEY+['date','entry_date',f'maturity{h}',f'excess{h}','y']].copy().rename(columns={f'maturity{h}':'maturity',f'excess{h}':'excess'})
            p=p.assign(cohort=cohort,method=method,task=task,horizon=h,year=year,prediction=prediction,raw_prediction=raw,training_mean=np.average(tr.y,weights=w));parts.append(p)
            actions.append(dict(s,method=method,n_predictions=len(p),fit_max_maturity=str(tr[f'maturity{h}'].max())))
    result=pd.concat(parts,ignore_index=True)
    ids=panel[KEY+['date']].copy();ids['row_id']=panel.index
    result=result.merge(ids,on=KEY+['date'],how='left',validate='many_to_one');assert result.row_id.notna().all();result=result[old.columns].sort_values(PK).reset_index(drop=True)
    assert not result.duplicated(PK).any();rp=out/'predictions.parquet';result.to_parquet(rp,index=False)
    saved=[updated.get(tuple(m[k] for k in FK)+(m['method'],),m) for m in models];js(out/'model_parameters.json',saved);js(out/'actions.json',actions)
    pair=old.drop(columns='row_id').merge(result.drop(columns='row_id'),on=PK,how='outer',suffixes=('_old','_new'),indicator=True,validate='one_to_one');pair.to_parquet(out/'prediction_pairs.parquet',index=False)
    known=pair._merge.eq('both');changed=known&~np.isclose(pair.prediction_old,pair.prediction_new,rtol=1e-12,atol=1e-12,equal_nan=True)
    reads={str(p):sha(p) for p in [pp,sp,mp,op,lp,Path(__file__),ROOT/'src/train_r02.py',ROOT/'src/common.py',ROOT/'protocols/r131.json']}
    js(out/'run_receipt.json',dict(reads=reads,prediction_sha256=sha(rp),models_sha256=sha(out/'model_parameters.json'),refit_models=len(updated),reevaluated_models=len(actions)-len(updated),preserved_prediction_rows=int(keep.sum()),rows=len(result),added=int(pair._merge.eq('right_only').sum()),removed=int(pair._merge.eq('left_only').sum()),changed_common_predictions=int(changed.sum()),max_prediction_change=float((pair.loc[known,'prediction_new']-pair.loc[known,'prediction_old']).abs().max()),quality='Historical-proxy, fixed parameters'))
    print('DONE',len(updated),'refits',len(actions)-len(updated),'fixed-model re-evaluations',len(result),'rows',int(changed.sum()),'changed',flush=True)

if __name__=='__main__':run()
