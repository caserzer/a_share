"""Separate feature-only from coefficient propagation at frozen dates."""
import pandas as pd
from common import *
from inference_bundle_r101 import infer
from versioned_observations import verify_bundle
K=KEY+['asof','cohort','method','task','horizon']
def run():
 out=ROOT/'outputs/r138';foldpaths=[ROOT/f'outputs/{r}/fold_ledger.csv' for r in ['r02','r16']];modelpaths=[ROOT/f'outputs/{r}/model_parameters.json' for r in ['r02','r16']];folds=pd.concat([pd.read_csv(p) for p in foldpaths]);models=sum([json.loads(p.read_text()) for p in modelpaths],[]);pieces=[];summaries=[];pair=pd.read_parquet(out/'comparison.parquet')
 for entry in json.loads((out/'bundles.json').read_text()):
  m=verify_bundle(entry['path']);f=pd.read_parquet(m['sources']['features']['path']);c=pd.read_csv(m['sources']['catalog']['path']);middle=infer(c,f,folds,models,entry['asof']);q=pair[pair['asof'].eq(entry['asof'])].merge(middle[K+['prediction','status']],on=K,validate='one_to_one');q=q.rename(columns={'prediction':'prediction_features_only','status':'status_features_only'});pieces.append(q)
  summaries.append(dict(asof=entry['asof'],feature_prediction_changes=int((~np.isclose(q.prediction_old,q.prediction_features_only,atol=1e-12,rtol=1e-12,equal_nan=True)).sum()),coefficient_prediction_changes=int((~np.isclose(q.prediction_features_only,q.prediction_new,atol=1e-12,rtol=1e-12,equal_nan=True)).sum()),feature_status_changes=int(q.status_old.ne(q.status_features_only).sum()),coefficient_status_changes=int(q.status_features_only.ne(q.status_new).sum())))
 pd.concat(pieces,ignore_index=True).to_parquet(out/'attribution.parquet',index=False);js(out/'attribution.json',dict(dates=summaries,reads={str(p):sha(p) for p in foldpaths+modelpaths+[Path(__file__),out/'comparison.parquet']},boundary='Sequential frozen decomposition, no causal economic interpretation'))
 print(summaries,flush=True)
if __name__=='__main__':run()
