"""Matched controls versus leader spread; fixed three-task and coverage protocols."""
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge,LogisticRegression
from common import *
from train_r02 import target,train_masks,sample_weights
from versioned_observations import digest_json
BASE=['mom20','mom60','vol20','dd60','log_members','size_control','market_beta126','residual_vol126','breadth21','breadth63']
ALL=BASE+['leader_spread']

def run():
    out=ROOT/'outputs/r109';out.mkdir(exist_ok=True)
    paths=[ROOT/'data/monthly_panel.parquet',ROOT/'data/l1_monthly_panel.parquet',ROOT/'data/r30_size_control.parquet',ROOT/'data/r54_market_controls.parquet',ROOT/'outputs/r108/industry_features.parquet']
    p=pd.concat([pd.read_parquet(x) for x in paths[:2]],ignore_index=True);p['log_members']=np.log(p.members)
    p=p.merge(pd.read_parquet(paths[2])[KEY+['date','size_control']],on=KEY+['date'],how='left',validate='one_to_one')
    p=p.merge(pd.read_parquet(paths[3])[KEY+['date','market_beta126','residual_vol126']],on=KEY+['date'],how='left',validate='one_to_one')
    source=pd.read_parquet(paths[4]);p=p.merge(source[KEY+['date','leader_spread','strict_complete']],on=KEY+['date'],how='left',validate='one_to_one')
    p['baseline_ready']=p.price_ready&np.isfinite(p[BASE]).all(axis=1);p['main80']=p.baseline_ready&np.isfinite(p.leader_spread);p['strict100']=p.main80&p.strict_complete.eq(True)
    p.to_parquet(out/'joined_panel.parquet',index=False)
    coverage=source[KEY+['date','catalogue_identity','observed_panel_row','status']].merge(p[KEY+['date','baseline_ready','main80','strict100']],on=KEY+['date'],how='left',validate='one_to_one')
    for c in ['baseline_ready','main80','strict100']:coverage[c]=coverage[c].eq(True)
    coverage.to_parquet(out/'coverage.parquet',index=False)
    preds=[];models=[];folds=[]
    for (era,level),base in p.groupby(['era','level']):
      for cohort in ['main80','strict100']:
        g=base[base[cohort]];rank=g.groupby('date')[ALL].transform(centered_rank)
        for task in ['return','onset','reversal']:
          for h in [20,60]:
            y,eligible=target(g,task,h);q=g[eligible].copy();q['y']=y[eligible]
            for year in range(2020,2027):
              fit,cal,test=train_masks(q,year,h,task);tr=q[fit];ca=q[cal];te=q[test]
              if te.empty:continue
              reason=None
              if tr.date.nunique()<18 or len(tr)<300:reason='insufficient_train_months_or_rows'
              elif task!='return':
                if tr.y.value_counts().reindex([0.,1.],fill_value=0).min()<30:reason='insufficient_train_classes'
                elif ca.date.nunique()<4 or len(ca)<100 or ca.y.value_counts().reindex([0.,1.],fill_value=0).min()<10:reason='insufficient_calibration'
              rec=dict(era=era,level=level,cohort=cohort,task=task,horizon=h,year=year,n_fit=len(tr),n_cal=len(ca),n_test=len(te),train_months=tr.date.nunique(),cal_months=ca.date.nunique(),fit_max_maturity=tr[f'maturity{h}'].max(),cal_max_maturity=ca[f'maturity{h}'].max(),fit_identity_sha256=digest_json(tr[KEY+['date']].astype(str).to_dict('records')),cal_identity_sha256=digest_json(ca[KEY+['date']].astype(str).to_dict('records')))
              folds.append(dict(rec,status='skipped' if reason else 'fit',reason=reason))
              if reason:continue
              for method,cols in [('controls',BASE),('with_leader',ALL)]:
                scaler=StandardScaler().fit(rank.loc[tr.index,cols]);x=scaler.transform(rank.loc[tr.index,cols]);xt=scaler.transform(rank.loc[te.index,cols]);w=sample_weights(tr)
                if task=='return':
                    model=Ridge(alpha=10).fit(x,tr.y,sample_weight=w);decision=model.predict(xt);prediction=decision;platt=None
                else:
                    model=LogisticRegression(C=1,tol=1e-10,max_iter=10000,random_state=3502).fit(x,tr.y,sample_weight=w)
                    xc=scaler.transform(rank.loc[ca.index,cols]);platt=LogisticRegression(C=1,tol=1e-10,max_iter=10000,random_state=3502).fit(model.decision_function(xc).reshape(-1,1),ca.y,sample_weight=sample_weights(ca));decision=model.decision_function(xt);prediction=platt.predict_proba(decision.reshape(-1,1))[:,1]
                f=te[KEY+['date','entry_date',f'maturity{h}',f'excess{h}','y','strict_complete']].rename(columns={f'maturity{h}':'maturity',f'excess{h}':'excess'}).copy()
                for k in ['cohort','task','horizon','year']:f[k]=rec[k]
                f['method']=method;f['prediction']=prediction;f['decision']=decision;preds.append(f)
                models.append(dict(rec,method=method,columns=cols,scaler_mean=scaler.mean_.tolist(),scaler_scale=scaler.scale_.tolist(),coefficient=model.coef_.tolist(),intercept=np.asarray(model.intercept_).tolist(),calibration_coefficient=platt.coef_.tolist() if platt is not None else None,calibration_intercept=platt.intercept_.tolist() if platt is not None else None))
        print(era,level,cohort,len(g),flush=True)
    pd.concat(preds,ignore_index=True).to_parquet(out/'predictions.parquet',index=False);pd.DataFrame(folds).to_csv(out/'fold_ledger.csv',index=False);js(out/'model_parameters.json',models)
    paths += [Path(__file__),ROOT/'protocols/r109.json',ROOT/'src/train_r02.py',ROOT/'src/common.py']
    js(out/'receipt.json',dict(reads={str(x):sha(x) for x in paths},models=len(models),outputs={n:sha(out/n) for n in ['joined_panel.parquet','coverage.parquet','predictions.parquet','fold_ledger.csv','model_parameters.json']},adopted=False));print('models',len(models))

if __name__=='__main__':run()
