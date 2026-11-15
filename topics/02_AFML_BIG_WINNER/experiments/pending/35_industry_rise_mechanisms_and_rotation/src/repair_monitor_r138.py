"""Immutable corrected inference snapshots, explanation and evidence joins."""
import pandas as pd
from common import *
from inference_bundle_r101 import INPUT,infer
from versioned_observations import source_copy,seal,verify_bundle
from model_terms_r103 import explain
from integrated_monitor_r93 import build
K=KEY+['asof','cohort','method','task','horizon']
def run():
 out=ROOT/'outputs/r138';store=ROOT/'data/inference_store_r138';protocol=ROOT/'protocols/r138.json';dates=json.loads(protocol.read_text())['dates'];catalog=ROOT/'outputs/universe_current.csv';l1=ROOT/'data/l1_monthly_panel.parquet';foldsource=ROOT/'outputs/r130/fold_ledger.csv';fp=out/'fold_ledger.csv';fold=pd.read_csv(foldsource);fold[fold.version.eq('new')].drop(columns='version').to_csv(fp,index=False)
 foldpaths=[fp,ROOT/'outputs/r16/fold_ledger.csv'];modelpaths=[ROOT/'outputs/r131/model_parameters.json',ROOT/'outputs/r16/model_parameters.json'];models=sum([json.loads(p.read_text()) for p in modelpaths],[]);folds=pd.concat([pd.read_csv(p) for p in foldpaths]);bundles=[];preds=[];terms=[];expl=[]
 for date in dates:
  feature_source=ROOT/f'outputs/r129/features_{date}.parquet';features=pd.concat([pd.read_parquet(feature_source,columns=INPUT),pd.read_parquet(l1,columns=INPUT)],ignore_index=True);features=features[features.date.eq(date)&features.era.eq('SW2021')].sort_values(KEY).reset_index(drop=True);ep=out/f'features_{date}.parquet';features.to_parquet(ep,index=False)
  prov=out/f'provenance_{date}.json';js(prov,dict(reads={str(p):sha(p) for p in [feature_source,l1,foldsource]},selected_columns=INPUT,cutoff=date,quality='Historical-proxy, corrected basket origins; no outcomes in inference input'))
  paths=dict(features=ep,catalog=catalog,provenance=prov,protocol=protocol,code=Path(__file__),inference_code=ROOT/'src/inference_bundle_r101.py',common=ROOT/'src/common.py',seal_code=ROOT/'src/versioned_observations.py')
  paths.update({f'fold_{i}':p for i,p in enumerate(foldpaths)});paths.update({f'model_{i}':p for i,p in enumerate(modelpaths)});sources={k:source_copy(p,store) for k,p in paths.items()}
  frame=infer(pd.read_csv(catalog),features,folds,models,date);identity=dict(asof=date,kind='repaired_historical_three_task_inference',sources={k:v['sha256'] for k,v in sources.items()});bundle=seal(store,'inference',identity,sources,{'predictions.parquet':frame},dict(capture_kind='historical_replay',rows=len(frame),formal_rows=int(frame.prediction.notna().sum()),quality='Historical-proxy repair, not forward validation'));m=verify_bundle(bundle);bundles.append(dict(asof=date,path=str(bundle),bundle_id=m['bundle_id'],manifest_sha256=sha(bundle/'manifest.json')));preds.append(frame);a,b=explain(bundle);expl.append(a);terms.append(b)
 js(out/'bundles.json',bundles);pred=pd.concat(preds,ignore_index=True);pred.to_parquet(out/'predictions.parquet',index=False);pd.concat(expl,ignore_index=True).to_parquet(out/'model_explanations.parquet',index=False);pd.concat(terms,ignore_index=True).to_parquet(out/'model_terms.parquet',index=False)
 oldbundles=json.loads((ROOT/'outputs/r101/bundles.json').read_text());old=pd.concat([pd.read_parquet(Path(x['path'])/'predictions.parquet') for x in oldbundles],ignore_index=True);pair=old.merge(pred,on=K,how='outer',suffixes=('_old','_new'),indicator=True,validate='one_to_one');assert pair._merge.eq('both').all();pair['status_changed']=pair.status_old.ne(pair.status_new);pair['prediction_changed']=~np.isclose(pair.prediction_old,pair.prediction_new,rtol=1e-12,atol=1e-12,equal_nan=True);pair.to_parquet(out/'comparison.parquet',index=False)
 evp=ROOT/'outputs/r74/evidence_matrix.parquet';integrated,e,extra=build(pred,pd.read_parquet(evp));integrated['model_source_round']=np.where(integrated.level.eq('L1'),'R16','R131');integrated['integration_scope']='repaired_historical_display_no_evidence_in_model';integrated['model_clock_scope']='corrected_basket_historical_proxy_not_forward';integrated.to_parquet(out/'task_evidence.parquet',index=False);extra.to_parquet(out/'evidence_without_task_key.parquet',index=False)
 stats=[]
 for date,g in pair.groupby('asof'):stats.append(dict(asof=str(date.date()),rows=len(g),formal_old=int(g.prediction_old.notna().sum()),formal_new=int(g.prediction_new.notna().sum()),status_changes=int(g.status_changed.sum()),prediction_changes=int(g.prediction_changed.sum()),max_prediction_change=float((g.prediction_new-g.prediction_old).abs().max())))
 js(out/'summary.json',dict(dates=stats,evidence_matches=int(integrated.evidence_join.eq('both').sum()),reads={str(p):sha(p) for p in [protocol,Path(__file__),ROOT/'src/model_terms_r103.py',ROOT/'src/integrated_monitor_r93.py',evp,*modelpaths,*foldpaths]},prospective_records=0,current_source_pointer_changed=False))
 print(stats,flush=True)
if __name__=='__main__':run()
