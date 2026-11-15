"""Independent all-status inference, rank arithmetic, terms and evidence checks."""
import pandas as pd
from scipy.special import expit
from common import *
from versioned_observations import verify_bundle,digest_json
KEYS=KEY+['asof','cohort','method','task','horizon'];F=['mom20','mom60','vol20','dd60','past_excess20','past_excess60','log_members'];MK=['era','level','cohort','task','horizon','year']
def run():
 out=ROOT/'outputs/r138';allp=[];formal=0;maxerr=0.;status_count=0
 for p,h in json.loads((out/'summary.json').read_text())['reads'].items():assert sha(p)==h
 for entry in json.loads((out/'bundles.json').read_text()):
  bundle=Path(entry['path']);m=verify_bundle(bundle);assert sha(bundle/'manifest.json')==entry['manifest_sha256'];p=pd.read_parquet(bundle/'predictions.parquet');allp.append(p);date=pd.Timestamp(entry['asof']);src=m['sources'];features=pd.read_parquet(src['features']['path']);assert features.date.eq(date).all();assert not any(c.startswith(('return','maturity','excess','rel_trough')) for c in features);features['log_members']=np.log(features.members.where(features.members.gt(0)));cat=pd.read_csv(src['catalog']['path']);cat=cat[cat.era.eq('SW2021')];assert len(p)==len(cat)*12
  assert not p.duplicated(KEYS).any();assert set(map(tuple,p[KEY].drop_duplicates().to_numpy()))==set(map(tuple,cat[KEY].to_numpy()))
  folds=pd.concat([pd.read_csv(v['path']) for k,v in src.items() if k.startswith('fold_')]);foldmap={tuple(r[k] for k in MK):r for r in folds.to_dict('records')};models=sum([json.loads(Path(v['path']).read_text()) for k,v in src.items() if k.startswith('model_')],[]);modelmap={tuple(r[k] for k in MK)+(r['method'],):r for r in models};fm=features.set_index(KEY);ranked={}
  for method in ['F','FD']:
   cols=F+(['breadth21','breadth63'] if method=='FD' else []);q=features[features.price_ready.eq(True)&np.isfinite(features[cols]).all(axis=1)].copy()
   for c in cols:q[c]=(q.groupby(['era','level'])[c].rank()-.5)/q.groupby(['era','level'])[c].transform('count')-.5
   ranked[method]=q.set_index(KEY)[cols]
  for row in p.to_dict('records'):
   ik=tuple(row[k] for k in KEY);fk=(row['era'],row['level'],row['cohort'],row['task'],row['horizon'],date.year);method=row['method'];rank=ranked[method];model=modelmap.get(fk+(method,));fold=foldmap.get(fk)
   if ik not in fm.index:expected='no_exact_date_feature_snapshot'
   elif ik not in rank.index:expected='missing_required_features'
   elif (row['task']=='onset' and not fm.loc[ik,'past_excess20']<=0) or (row['task']=='reversal' and not(fm.loc[ik,'past_excess60']>0 and fm.loc[ik,'mom60']>0)):expected='outside_task_population'
   elif fold is None:expected='absent_fold'
   elif fold['status']!='fit':expected='model_skipped'
   elif model is None:expected='missing_formal_model'
   else:
    expected='formal_historical_output';boundary=pd.Timestamp(date.year,1,1);fit_boundary=boundary if row['task']=='return' else pd.Timestamp(date.year-1,7,1);assert pd.Timestamp(model['fit_max_maturity'])<fit_boundary;assert model['n_fit']>=300 and model['train_months']>=18
    if row['task']!='return':assert pd.Timestamp(model['cal_max_maturity'])<boundary and model['n_cal']>=100 and model['cal_months']>=4
    cols=F+(['breadth21','breadth63'] if method=='FD' else []);assert model['columns']==cols;v=rank.loc[ik,cols].to_numpy(float);b=np.asarray(model['coefficient']).ravel();z=(v-np.array(model['scaler_mean']))/np.array(model['scaler_scale']);value=float(z@b+np.asarray(model['intercept']).item());assert np.isfinite(z).all()
    if row['task']!='return':value=float(expit(value*np.asarray(model['calibration_coefficient']).item()+np.asarray(model['calibration_intercept']).item()))
    err=abs(value-row['prediction']);assert err<1e-12;maxerr=max(maxerr,err);formal+=1;assert row['model_sha256']==digest_json(model)
   assert row['status']==expected,(ik,row['task'],row['status'],expected);assert pd.notna(row['prediction'])==(expected=='formal_historical_output');status_count+=1
 combined=pd.concat(allp,ignore_index=True);pd.testing.assert_frame_equal(combined,pd.read_parquet(out/'predictions.parquet'));ex=pd.read_parquet(out/'model_explanations.parquet');terms=pd.read_parquet(out/'model_terms.parquet');ex=ex.set_index(KEYS);termsgroup=terms.groupby(KEYS)
 for k,g in termsgroup:
  x=ex.loc[k];assert x.explanation_status=='algebraically_reconstructed';assert np.allclose((g.centered_rank-g.scaler_mean)/g.scaler_scale,g.standardized_rank);assert np.allclose(g.standardized_rank*g.coefficient,g.base_term);total=x.baseline+g.final_term.sum();assert np.isclose(total,x.additive_total,atol=1e-12);value=total if k[-2]=='return' else expit(total);assert np.isclose(value,x.prediction,atol=1e-12)
 assert len(termsgroup)==formal;assert ex.loc[ex.prediction.isna(),'explanation_status'].eq('no_formal_output').all()
 evidence=pd.read_parquet(ROOT/'outputs/r74/evidence_matrix.parquet');evidence=evidence[evidence.clock.eq('publication_proxy')].copy();evidence['asof']=pd.to_datetime(evidence['asof']);join=KEY+['asof'];ev=evidence.set_index(join);integrated=pd.read_parquet(out/'task_evidence.parquet');assert len(integrated)==len(combined);assert integrated.model_source_round.eq(np.where(integrated.level.eq('L1'),'R16','R131')).all()
 for row in integrated.to_dict('records'):
  k=tuple(row[c] for c in join);assert (row['evidence_join']=='both')==(k in ev.index)
  if k in ev.index:
   source=ev.loc[k]
   for c in evidence.columns:
    if c in join:continue
    a=row['evidence_'+c];b=source[c];assert (pd.isna(a) and pd.isna(b)) or a==b,(k,c)
 pair=pd.read_parquet(out/'comparison.parquet');assert pair.status_changed.equals(pair.status_old.ne(pair.status_new));assert np.array_equal(pair.prediction_changed,~np.isclose(pair.prediction_old,pair.prediction_new,rtol=1e-12,atol=1e-12,equal_nan=True))
 js(out/'verification.json',dict(status='PASS',status_rows=status_count,formal_predictions=formal,max_error=maxerr,explained_predictions=len(termsgroup),term_rows=len(terms),evidence_rows=len(integrated),verifier_sha256=sha(__file__)))
 print('MONITOR VERIFIED',status_count,formal,maxerr,flush=True)
if __name__=='__main__':run()
