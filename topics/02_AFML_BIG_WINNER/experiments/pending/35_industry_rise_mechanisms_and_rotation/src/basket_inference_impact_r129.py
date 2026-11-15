"""Frozen-model sensitivity to repaired feature inputs; no training claims."""
import pandas as pd
from common import *
from inference_bundle_r101 import INPUT,infer
from verify_basket_replay_r128 import differences

def run():
    out=ROOT/'outputs/r129';newp=out/'features_2026-10-21.parquet';oldp=ROOT/'data/monthly_panel.parquet';l1p=ROOT/'data/l1_monthly_panel.parquet'
    new=pd.read_parquet(newp);old=pd.read_parquet(oldp,columns=INPUT);keys=KEY+['date']
    # Rank changes can propagate to unaffected industries: retain whole date population.
    _,_,missing,extra,bad=differences(new[new.price_ready],old[old.price_ready],keys)
    changes=pd.concat([missing[keys],extra[keys],bad[keys]],ignore_index=True).drop_duplicates()
    changes.to_parquet(out/'ready_input_changes.parquet',index=False)
    dates=sorted(set(changes.loc[changes.era.eq('SW2021'),'date'])|{pd.Timestamp('2026-09-30')})
    l1=pd.read_parquet(l1p,columns=INPUT);old=pd.concat([old,l1],ignore_index=True);new=pd.concat([new,l1],ignore_index=True)
    catp=ROOT/'outputs/universe_current.csv';catalog=pd.read_csv(catp)
    foldpaths=[ROOT/f'outputs/{r}/fold_ledger.csv' for r in ['r02','r16']];modelpaths=[ROOT/f'outputs/{r}/model_parameters.json' for r in ['r02','r16']]
    folds=pd.concat([pd.read_csv(p) for p in foldpaths]);models=[]
    for p in modelpaths:models.extend(json.loads(p.read_text()))
    predictions=[];summaries=[]
    for date in dates:
        a=infer(catalog,old[old.date.eq(date)],folds,models,date);b=infer(catalog,new[new.date.eq(date)],folds,models,date)
        identity=KEY+['asof','cohort','method','task','horizon'];pairs=a.merge(b,on=identity,suffixes=('_old','_new'),validate='one_to_one')
        pairs['status_changed']=pairs.status_old.ne(pairs.status_new)
        pairs['prediction_changed']=~np.isclose(pairs.prediction_old,pairs.prediction_new,rtol=1e-12,atol=1e-12,equal_nan=True)
        predictions.append(pairs);summaries.append(dict(date=str(date.date()),rows=len(pairs),status_changed=int(pairs.status_changed.sum()),prediction_changed=int(pairs.prediction_changed.sum()),old_formal=int(pairs.prediction_old.notna().sum()),new_formal=int(pairs.prediction_new.notna().sum())))
    result=pd.concat(predictions,ignore_index=True);pp=out/'prediction_impact.parquet';result.to_parquet(pp,index=False)
    reads={str(p):sha(p) for p in [newp,oldp,l1p,catp,*foldpaths,*modelpaths,Path(__file__),ROOT/'src/inference_bundle_r101.py',ROOT/'src/verify_basket_replay_r128.py',ROOT/'src/common.py']}
    js(out/'inference_impact.json',dict(reads=reads,changed_ready_input_rows=len(changes),dates=summaries,predictions_sha256=sha(pp),limitation='Frozen old coefficients only; revised training/labels not assessed, no new performance claim'))
    print(summaries)

if __name__=='__main__':run()
