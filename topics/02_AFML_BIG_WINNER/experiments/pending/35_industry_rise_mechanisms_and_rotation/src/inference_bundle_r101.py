"""Feature-only immutable historical inference using frozen formal models."""
import tempfile
import pandas as pd
from scipy.special import expit
from common import *
from versioned_observations import source_copy, seal, verify_bundle, digest_json

F=['mom20','mom60','vol20','dd60','past_excess20','past_excess60','log_members']
INPUT=KEY+['date','price_ready']+F[:-1]+['members','breadth21','breadth63']
MK=['era','level','cohort','task','horizon','year']


def model_gate(m, date, cols):
    boundary=pd.Timestamp(date.year,1,1)
    fit_boundary=boundary if m['task']=='return' else pd.Timestamp(date.year-1,7,1)
    if not pd.Timestamp(m['fit_max_maturity'])<fit_boundary:
        return 'invalid_model_maturity'
    if m['train_months']<18 or m['n_fit']<300:return 'invalid_training_gate'
    if m['columns']!=cols:return 'invalid_model_features'
    for field in ['scaler_mean','scaler_scale','coefficient','intercept']:
        a=np.asarray(m[field],dtype=float).ravel()
        if len(a)!=(1 if field=='intercept' else len(cols)) or not np.isfinite(a).all():return 'invalid_model_parameters'
    if (np.asarray(m['scaler_scale'])<=0).any():return 'invalid_model_parameters'
    if m['task']!='return':
        if not pd.Timestamp(m['cal_max_maturity'])<boundary:return 'invalid_calibration_maturity'
        if m['cal_months']<4 or m['n_cal']<100:return 'uncalibrated_model'
        for field in ['calibration_coefficient','calibration_intercept']:
            a=np.asarray(m.get(field),dtype=float).ravel()
            if len(a)!=1 or not np.isfinite(a).all():return 'uncalibrated_model'
    return None


def infer(catalog,features,folds,models,asof):
    date=pd.Timestamp(asof)
    if list(features.columns)!=INPUT:raise ValueError('feature-only schema required')
    if features.duplicated(KEY+['date']).any():raise ValueError('duplicate feature identity')
    if not features.date.eq(date).all():raise ValueError('only exact-date features allowed')
    catalog=catalog[catalog.era.eq('SW2021')][KEY+['industry_name']].copy()
    if catalog.duplicated(KEY).any():raise ValueError('duplicate catalogue identity')
    if folds.duplicated(MK).any():raise ValueError('duplicate fold identity')
    modelmap={}
    for m in models:
        k=tuple(m[x] for x in MK)+(m['method'],)
        if k in modelmap:raise ValueError('duplicate model identity')
        modelmap[k]=m
    foldmap={tuple(r[k] for k in MK):r for r in folds.to_dict('records')}
    features=features.copy();features['log_members']=np.log(features.members.where(features.members.gt(0)))
    valid=set(map(tuple,catalog[KEY].to_numpy()))
    # Frozen training ranks used the full source population, including delisted identities.
    # Preserve that rank denominator; only catalogue identities receive output rows.
    featuremap={tuple(r[k] for k in KEY):r for r in features.to_dict('records')}
    ranked={}
    for method in ['F','FD']:
        cols=F+(['breadth21','breadth63'] if method=='FD' else [])
        ok=features.price_ready.eq(True)&np.isfinite(features[cols]).all(axis=1)
        eligible=features.loc[ok]
        ranks=eligible.groupby(['era','level'])[cols].transform(centered_rank) if len(eligible) else eligible[cols]
        ranked[method]={tuple(features.loc[i,KEY]):r.to_numpy() for i,r in ranks.iterrows()}
    rows=[]
    for c in catalog.to_dict('records'):
      ik=tuple(c[k] for k in KEY);f=featuremap.get(ik)
      for method in ['F','FD']:
       cols=F+(['breadth21','breadth63'] if method=='FD' else [])
       for task in ['return','onset','reversal']:
        for h in [20,60]:
          k=(c['era'],c['level'],method,task,h,date.year);fold=foldmap.get(k);m=modelmap.get(k+(method,))
          r=dict(**c,asof=date,cohort=method,method=method,task=task,horizon=h,prediction=np.nan,status='no_exact_date_feature_snapshot',model_sha256=None,capture_kind='historical_replay')
          if f is not None:
            if ik not in ranked[method]:r['status']='missing_required_features'
            elif (task=='onset' and not f['past_excess20']<=0) or (task=='reversal' and not(f['past_excess60']>0 and f['mom60']>0)):r['status']='outside_task_population'
            elif fold is None:r['status']='absent_fold'
            elif fold['status']!='fit':r['status']='model_skipped'
            elif m is None:r['status']='missing_formal_model'
            else:
              error=model_gate(m,date,cols)
              if error:r['status']=error
              else:
                x=(ranked[method][ik]-m['scaler_mean'])/m['scaler_scale']
                decision=float(x@np.asarray(m['coefficient']).ravel()+np.asarray(m['intercept']).ravel()[0])
                value=decision if task=='return' else float(expit(decision*np.asarray(m['calibration_coefficient']).item()+np.asarray(m['calibration_intercept']).item()))
                r.update(status='formal_historical_output',prediction=value,model_sha256=digest_json(m))
          rows.append(r)
    return pd.DataFrame(rows)


def capture(store,asof,feature_path,catalog_path,fold_paths,model_paths,provenance_path):
    store=Path(store)
    paths=dict(features=feature_path,catalog=catalog_path,provenance=provenance_path,protocol=ROOT/'protocols/r101.json',code=Path(__file__),common=ROOT/'src/common.py',seal_code=ROOT/'src/versioned_observations.py')
    paths.update({f'fold_{i}':p for i,p in enumerate(fold_paths)})
    paths.update({f'model_{i}':p for i,p in enumerate(model_paths)})
    sources={k:source_copy(p,store) for k,p in paths.items()}
    models=[]
    for i in range(len(model_paths)):models.extend(json.loads(Path(sources[f'model_{i}']['path']).read_text()))
    frame=infer(pd.read_csv(sources['catalog']['path']),pd.read_parquet(sources['features']['path']),pd.concat([pd.read_csv(sources[f'fold_{i}']['path']) for i in range(len(fold_paths))]),models,asof)
    identity=dict(asof=str(pd.Timestamp(asof).date()),kind='historical_three_task_inference',sources={k:v['sha256'] for k,v in sources.items()})
    catalog=pd.read_csv(sources['catalog']['path']);valid=set(map(tuple,catalog[catalog.era.eq('SW2021')][KEY].to_numpy()))
    features=pd.read_parquet(sources['features']['path'])
    outside=features[~features[KEY].apply(tuple,axis=1).isin(valid)]
    return seal(store,'inference',identity,sources,{'predictions.parquet':frame,'rank_only_outside_catalogue.parquet':outside},dict(capture_kind='historical_replay',rows=len(frame),formal_rows=int(frame.prediction.notna().sum()),quality='Historical-proxy; not strictPIT or forward validation'))


def run():
    out=ROOT/'outputs/r101';out.mkdir(exist_ok=True)
    protocol=json.loads((ROOT/'protocols/r101.json').read_text())
    panels=[ROOT/'data/monthly_panel.parquet',ROOT/'data/l1_monthly_panel.parquet']
    data=pd.concat([pd.read_parquet(p,columns=INPUT) for p in panels],ignore_index=True)
    data=data[data.era.eq('SW2021')]
    provenance=out/'feature_provenance.json'
    js(provenance,dict(reads={str(p):sha(p) for p in panels},selected_columns=INPUT,selection='SW2021 and exact asof; no target availability filtering',historical_proxy=True))
    bundles=[]
    with tempfile.TemporaryDirectory() as tmp:
      for asof in protocol['dates']:
        fp=Path(tmp)/'features.parquet';data[data.date.eq(pd.Timestamp(asof))].sort_values(KEY).reset_index(drop=True).to_parquet(fp,index=False)
        bundle=capture(ROOT/'data/inference_store_r101',asof,fp,ROOT/'outputs/universe_current.csv',[ROOT/f'outputs/{r}/fold_ledger.csv' for r in ['r02','r16']],[ROOT/f'outputs/{r}/model_parameters.json' for r in ['r02','r16']],provenance)
        manifest=verify_bundle(bundle)
        bundles.append(dict(asof=asof,path=str(bundle),bundle_id=manifest['bundle_id'],manifest_sha256=sha(bundle/'manifest.json')))
    js(out/'bundles.json',bundles)
    combined=pd.concat([pd.read_parquet(Path(b['path'])/'predictions.parquet') for b in bundles],ignore_index=True)
    combined.groupby(['asof','status']).size().rename('rows').reset_index().to_csv(out/'coverage.csv',index=False)
    print(combined.groupby(['asof','status']).size().to_string())

if __name__=='__main__':run()
