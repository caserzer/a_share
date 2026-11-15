"""Exact additive model terms in return or calibrated-logit units."""
import pandas as pd
from scipy.special import expit
from common import *
from versioned_observations import verify_bundle,digest_json
from inference_bundle_r101 import F
K=KEY+['asof','cohort','method','task','horizon']

def decompose(rank,model):
    rank=np.asarray(rank,dtype=float);mean=np.asarray(model['scaler_mean']);scale=np.asarray(model['scaler_scale'])
    coef=np.asarray(model['coefficient']).ravel();z=(rank-mean)/scale
    if len(rank)!=len(model['columns']) or not np.isfinite(z).all():raise ValueError('invalid rank inputs')
    intercept=float(np.asarray(model['intercept']).item())
    slope=1.;offset=0.
    if model['task']!='return':
        if model.get('calibration_coefficient') is None or model.get('calibration_intercept') is None:raise ValueError('uncalibrated model')
        slope=float(np.asarray(model['calibration_coefficient']).item());offset=float(np.asarray(model['calibration_intercept']).item())
    if not np.isfinite([slope,offset,intercept]).all():raise ValueError('invalid model')
    baseline=intercept*slope+offset;terms=z*coef*slope;total=baseline+terms.sum()
    return z,coef,z*coef,terms,baseline,total,float(total if model['task']=='return' else expit(total))

def explain(bundle):
    m=verify_bundle(bundle);p=pd.read_parquet(Path(bundle)/'predictions.parquet')
    f=pd.read_parquet(m['sources']['features']['path']);f['log_members']=np.log(f.members.where(f.members.gt(0)))
    models={}
    for name,s in m['sources'].items():
        if name.startswith('model_'):
            for model in json.loads(Path(s['path']).read_text()):models[digest_json(model)]=model
    ranked={}
    for method in ['F','FD']:
        cols=F+(['breadth21','breadth63'] if method=='FD' else [])
        g=f[f.price_ready.eq(True)&np.isfinite(f[cols]).all(axis=1)]
        ranks=g.groupby(['era','level'])[cols].transform(centered_rank) if len(g) else g[cols]
        for i,r in ranks.iterrows():ranked[(method,)+tuple(f.loc[i,KEY])]=(r,f.loc[i])
    summary=p.copy();summary['explanation_status']='no_formal_output';summary['baseline']=np.nan;summary['additive_total']=np.nan;summary['reconstructed_prediction']=np.nan;summary['additive_units']='unavailable'
    terms=[]
    for i,row in p[p.prediction.notna()].iterrows():
        model=models[row.model_sha256];r,raw=ranked[(row.method,)+tuple(row[k] for k in KEY)]
        z,coef,base_terms,final_terms,baseline,total,pred=decompose(r[model['columns']],model)
        units='expected_relative_return' if row.task=='return' else 'calibrated_logit'
        summary.loc[i,['explanation_status','baseline','additive_total','reconstructed_prediction','additive_units']]=['algebraically_reconstructed',baseline,total,pred,units]
        for j,col in enumerate(model['columns']):
            terms.append(dict(**{k:row[k] for k in K},feature=col,raw_value=raw[col],centered_rank=r[col],scaler_mean=model['scaler_mean'][j],scaler_scale=model['scaler_scale'][j],standardized_rank=z[j],coefficient=coef[j],base_term=base_terms[j],final_term=final_terms[j],additive_units=units,model_sha256=row.model_sha256,bundle_id=m['bundle_id']))
    return summary,pd.DataFrame(terms)

def run():
    out=ROOT/'outputs/r103';out.mkdir(exist_ok=True);summaries=[];terms=[];reads={}
    index=ROOT/'outputs/r102/bundles.json';reads[str(index)]=sha(index)
    for b in json.loads(index.read_text()):
        s,t=explain(b['path']);summaries.append(s)
        if len(t):terms.append(t)
        path=Path(b['path'])/'manifest.json';reads[str(path)]=sha(path)
    summaries=pd.concat(summaries,ignore_index=True);terms=pd.concat(terms,ignore_index=True)
    summaries.to_parquet(out/'task_explanations.parquet',index=False);terms.to_parquet(out/'feature_terms.parquet',index=False)
    summaries.groupby(['asof','level','task','additive_units','explanation_status']).size().rename('rows').reset_index().to_csv(out/'coverage.csv',index=False)
    ranked=terms.pivot(index=K,columns='feature',values='centered_rank')
    js(out/'rank_redundancy.json',{str(h):dict(formal_rows=len(ranked),equal_rank_rows=int(np.isclose(ranked[f'mom{h}'],ranked[f'past_excess{h}'],atol=1e-14,rtol=0).sum())) for h in [20,60]})
    for p in [Path(__file__),ROOT/'protocols/r103.json',ROOT/'src/common.py']:reads[str(p)]=sha(p)
    js(out/'receipt.json',dict(reads=reads,task_rows=len(summaries),explained=int(summaries.prediction.notna().sum()),feature_terms=len(terms),outputs={n:sha(out/n) for n in ['task_explanations.parquet','feature_terms.parquet','coverage.csv','rank_redundancy.json']},reference='zero standardized rank; frozen training scaler mean',prospective_records=0))
    print(len(summaries),'tasks',len(terms),'feature terms')

if __name__=='__main__':run()
