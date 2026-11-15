"""Independent scalar term reconstruction and full-grid preservation checks."""
import math
import pandas as pd
from scipy.stats import rankdata
from scipy.special import expit
from common import *
from versioned_observations import verify_bundle,digest_json
K=KEY+['asof','cohort','method','task','horizon']

def run():
    out=ROOT/'outputs/r103';receipt=json.loads((out/'receipt.json').read_text())
    for path,digest in receipt['reads'].items():assert sha(path)==digest
    for name,digest in receipt['outputs'].items():assert sha(out/name)==digest
    s=pd.read_parquet(out/'task_explanations.parquet');t=pd.read_parquet(out/'feature_terms.parquet')
    assert not s.duplicated(K).any() and not t.duplicated(K+['feature']).any()
    modelmap={};rankmap={};rawmap={};original=[];bundle_ids={}
    for b in json.loads((ROOT/'outputs/r102/bundles.json').read_text()):
        m=verify_bundle(b['path']);bundle_ids[pd.Timestamp(b['cutoff'])]=m['bundle_id'];original.append(pd.read_parquet(Path(b['path'])/'predictions.parquet'))
        f=pd.read_parquet(m['sources']['features']['path']);f['log_members']=np.log(f.members.where(f.members.gt(0)))
        for k,src in m['sources'].items():
            if k.startswith('model_'):
                for model in json.loads(Path(src['path']).read_text()):modelmap[digest_json(model)]=model
        for method in ['F','FD']:
            cols=['mom20','mom60','vol20','dd60','past_excess20','past_excess60','log_members']+(['breadth21','breadth63'] if method=='FD' else [])
            g=f[f.price_ready.eq(True)&np.isfinite(f[cols]).all(axis=1)]
            for _,group in g.groupby(['era','level']):
                for col in cols:
                    ranks=(rankdata(group[col].to_numpy(),method='average')-.5)/len(group)-.5
                    for (_,row),rank in zip(group.iterrows(),ranks):
                        key=tuple(row[k] for k in KEY)+(pd.Timestamp(b['cutoff']),method,col)
                        rankmap[key]=float(rank);rawmap[key]=float(row[col])
    original=pd.concat(original,ignore_index=True)
    pd.testing.assert_frame_equal(s[list(original)],original)
    formal=s.prediction.notna();known=set(map(tuple,s.loc[formal,K].to_numpy()))
    assert set(map(tuple,t[K].to_numpy()))==known
    unknown=s[~formal]
    assert unknown.explanation_status.eq('no_formal_output').all() and unknown[['baseline','additive_total','reconstructed_prediction']].isna().all().all()
    assert unknown.additive_units.eq('unavailable').all()
    lookup={tuple(row[k] for k in K):row for row in s.to_dict('records')}
    for key,g in t.groupby(K,sort=False):
        summary=lookup[key];model=modelmap[summary['model_sha256']]
        cols=model['columns'];assert set(g.feature)==set(cols) and len(g)==len(cols)
        binary=model['task']!='return'
        slope=float(np.asarray(model['calibration_coefficient']).item()) if binary else 1.
        offset=float(np.asarray(model['calibration_intercept']).item()) if binary else 0.
        terms=[]
        units='calibrated_logit' if binary else 'expected_relative_return'
        assert summary['additive_units']==units and summary['explanation_status']=='algebraically_reconstructed'
        for row in g.to_dict('records'):
            j=cols.index(row['feature']);rk=tuple(row[k] for k in KEY)+(row['asof'],row['method'],row['feature'])
            rank=rankmap[rk];mean=model['scaler_mean'][j];scale=model['scaler_scale'][j]
            z=(rank-mean)/scale;coef=float(np.asarray(model['coefficient']).ravel()[j]);base=z*coef;final=base*slope
            expected=[rawmap[rk],rank,mean,scale,z,coef,base,final]
            names=['raw_value','centered_rank','scaler_mean','scaler_scale','standardized_rank','coefficient','base_term','final_term']
            np.testing.assert_allclose([row[n] for n in names],expected,atol=1e-13,rtol=1e-13)
            assert row['model_sha256']==summary['model_sha256'] and row['additive_units']==units
            assert row['bundle_id']==bundle_ids[row['asof']]
            terms.append(final)
        baseline=float(np.asarray(model['intercept']).item())*slope+offset
        total=baseline+math.fsum(terms);prediction=float(expit(total)) if binary else total
        np.testing.assert_allclose([summary['baseline'],summary['additive_total'],summary['reconstructed_prediction'],summary['prediction']],[baseline,total,prediction,prediction],atol=1e-12,rtol=1e-12)
    redundant=json.loads((out/'rank_redundancy.json').read_text());pivot=t.pivot(index=K,columns='feature',values='centered_rank')
    for h in [20,60]:
        assert redundant[str(h)]==dict(formal_rows=len(pivot),equal_rank_rows=int(np.isclose(pivot[f'mom{h}'],pivot[f'past_excess{h}'],atol=1e-14,rtol=0).sum()))
    result=dict(status='PASS',task_rows=len(s),explained=int(formal.sum()),feature_terms=len(t),unknown=int((~formal).sum()),maximum_prediction_error=float((s.prediction-s.reconstructed_prediction).abs().max()),units=s.loc[formal].groupby('additive_units').size().to_dict(),prospective_records=0)
    js(out/'verification.json',result);print(result)

if __name__=='__main__':run()
