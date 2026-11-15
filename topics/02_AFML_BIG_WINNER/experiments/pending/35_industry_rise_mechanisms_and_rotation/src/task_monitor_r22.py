"""Expose independent frozen tasks without stale/current or score/probability conflation."""
import pandas as pd
from common import *
from versioned_observations import digest_json
from train_r02 import F
PKEY=KEY+['cohort','method','task','horizon']
PCOLS=PKEY+['date','year','prediction']
FCOLS=KEY+['date','price_ready']+F[:-1]+['members','breadth21','breadth63']


def build(catalog,predictions,folds,models,panel,dates):
    catalogue=catalog[catalog.era.eq('SW2021')][KEY+['industry_name']]
    valid=set(map(tuple,catalogue[KEY].to_numpy()))
    p=predictions[predictions.era.eq('SW2021')&predictions.method.isin(['F','FD'])&predictions.cohort.eq(predictions.method)].copy()
    if p.duplicated(PKEY+['date']).any():raise ValueError('duplicate prediction')
    records=[]
    for date in map(pd.Timestamp,dates):
      for industry in catalogue.to_dict('records'):
       ik=tuple(industry[k] for k in KEY)
       features=panel[(panel.era==ik[0])&(panel.level==ik[1])&(panel.industry_code==ik[2])&panel.date.eq(date)]
       if len(features)>1:raise ValueError('duplicate features')
       for method in ['F','FD']:
        for task in ['return','onset','reversal']:
         for h in [20,60]:
          q=p[(p.era==ik[0])&(p.level==ik[1])&(p.industry_code==ik[2])&p.method.eq(method)&p.task.eq(task)&p.horizon.eq(h)&p.date.le(date)].sort_values('date')
          fold=folds[(folds.era==ik[0])&(folds.level==ik[1])&folds.cohort.eq(method)&folds.task.eq(task)&folds.horizon.eq(h)&folds.year.eq(date.year)]
          if len(fold)>1:raise ValueError('duplicate fold')
          model=[m for m in models if (m['era'],m['level'],m['cohort'],m['method'],m['task'],m['horizon'],m['year'])==(ik[0],ik[1],method,method,task,h,date.year)]
          if len(model)>1:raise ValueError('duplicate model')
          r=dict(**industry,asof=date,task=task,horizon=h,method=method,cohort=method,prediction=np.nan,last_prediction=np.nan,last_prediction_date=pd.NaT,last_prediction_age_days=np.nan,
              status='no_exact_date_feature_snapshot',model_status='absent_fold',fold_reason='',model_sha256=None,calibration_status='no_current_output',value_meaning='expected_relative_return' if task=='return' else 'task_probability_if_calibrated',capture_kind='historical_replay')
          if len(fold):r.update(model_status=fold.iloc[0].status,fold_reason=fold.iloc[0].reason)
          if not q.empty:
           last=q.iloc[-1];r.update(last_prediction=last.prediction,last_prediction_date=last.date,last_prediction_age_days=(date-last.date).days)
          if len(features):
           f=features.iloc[0];cols=F[:-1]+['members']+(['breadth21','breadth63'] if method=='FD' else [])
           if not f.price_ready or f[cols].isna().any():r['status']='missing_required_features'
           elif (task=='onset' and not f.past_excess20<=0) or (task=='reversal' and not (f.past_excess60>0 and f.mom60>0)):r['status']='outside_task_population'
           elif len(fold)==0:r['status']='absent_fold'
           elif fold.iloc[0].status!='fit':r['status']='model_skipped'
           else:
            current=q[q.date.eq(date)]
            if len(current)!=1 or len(model)!=1:raise ValueError('qualified fold missing formal prediction/model')
            m=model[0];boundary=pd.Timestamp(date.year,1,1)
            assert pd.Timestamp(m['fit_max_maturity'])<boundary
            if task!='return':
             assert m['calibration_coefficient'] is not None and m['calibration_intercept'] is not None
             assert pd.Timestamp(m['cal_max_maturity'])<boundary
             assert m['cal_months']>=4 and m['n_cal']>=100
             assert 0<=current.iloc[0].prediction<=1
            r.update(prediction=current.iloc[0].prediction,status='formal_historical_output',model_sha256=digest_json(m),calibration_status='not_applicable_regression' if task=='return' else 'past_window_platt_not_forward_validated')
          records.append(r)
    outside=p[~p[KEY].apply(tuple,axis=1).isin(valid)&p.date.ge(min(map(pd.Timestamp,dates)))].copy()
    return pd.DataFrame(records),outside


def run():
    out=ROOT/'outputs/r22';out.mkdir(exist_ok=True)
    paths=[ROOT/'protocols/r22.json',ROOT/'outputs/universe_current.csv',Path(__file__)];preds=[];folds=[];models=[];panels=[]
    for round_,panel in [('r02','monthly_panel'),('r16','l1_monthly_panel')]:
      for name in ['predictions.parquet','fold_ledger.csv','model_parameters.json']:paths.append(ROOT/f'outputs/{round_}/{name}')
      paths.append(ROOT/f'data/{panel}.parquet')
      preds.append(pd.read_parquet(paths[-4],columns=PCOLS));folds.append(pd.read_csv(paths[-3]));models.extend(json.loads(paths[-2].read_text()));panels.append(pd.read_parquet(paths[-1],columns=FCOLS))
    protocol=json.loads(paths[0].read_text())
    data,quarantine=build(pd.read_csv(paths[1]),pd.concat(preds),pd.concat(folds),models,pd.concat(panels),protocol['dates'])
    data.to_csv(out/'task_monitor.csv',index=False);quarantine.to_csv(out/'quarantined_predictions.csv',index=False)
    summary=data.groupby(['asof','level','task','horizon','method','status']).size().rename('rows').reset_index();summary.to_csv(out/'summary.csv',index=False)
    js(out/'receipt.json',dict(reads={str(p):sha(p) for p in paths},rows=len(data),formal_current=int(data.prediction.notna().sum()),quarantined=len(quarantine),outputs={f:sha(out/f) for f in ['task_monitor.csv','quarantined_predictions.csv','summary.csv']},prospective_records=0))
    print(data.groupby(['asof','status']).size().to_string())

if __name__=='__main__':run()
