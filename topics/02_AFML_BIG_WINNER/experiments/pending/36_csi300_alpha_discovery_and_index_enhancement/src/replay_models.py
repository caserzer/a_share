import sys,pickle,__main__
import numpy as np,pandas as pd
from common import *
from train import TrainTransform
__main__.TrainTransform=TrainTransform
sys.path.insert(0,str(PRIVATE/'vendor'))
import lightgbm as lgb

def main():
 f=pd.read_parquet(PRIVATE/'features.parquet');dd=pd.read_csv(EP/'configs/feature_dictionary.csv');core=dd.loc[dd.group.eq('core'),'feature'].tolist();rows=[]
 for scheme in ['expanding','rolling36']:
  receipts=json.loads((OUT/'manifests'/f'{scheme}_predictions.json').read_text())
  for r in receipts:
   pred=pd.read_parquet(r['prediction_path']);test=f.loc[f.signal_date.dt.to_period('Q').astype(str).eq(r['fold']) & f.score_eligible]
   for m in r['models']:
    if m['model']=='E1':
     t,model=pickle.loads(Path(m['path']).read_bytes());values=model.predict(t.transform(test[core]));seed='fixed'
    else:
     model=lgb.Booster(model_file=m['path']);cols=core if m['model']=='E2' else dd.feature.tolist();values=model.predict(test[cols],num_threads=4);seed=str(m['seed'])
    old=pred.loc[pred.model_id.eq(m['model'])&pred.seed_or_ensemble.eq(seed)].set_index(['signal_date','instrument']).score.reindex(pd.MultiIndex.from_frame(test[['signal_date','instrument']]))
    diff=float(np.max(np.abs(old.to_numpy()-values)));rows.append(dict(scheme=scheme,fold=r['fold'],model=m['model'],seed=seed,rows=len(test),max_abs_difference=diff,pass_check=diff<1e-10))
 save_json(OUT/'manifests/model_replay.json',dict(status='PASS' if all(x['pass_check'] for x in rows) else 'FAIL',models=len(rows),checks=rows));print('model replay',len(rows),'max difference',max(x['max_abs_difference'] for x in rows))
if __name__=='__main__':main()
