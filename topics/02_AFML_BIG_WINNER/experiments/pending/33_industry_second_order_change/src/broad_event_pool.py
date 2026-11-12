"""R18 broaden discovery only; final probability and validation gates unchanged."""
import argparse,json
from pathlib import Path
import pandas as pd
import probability_pool as engine
import event_context_pool as contextual
from single_reconfirmation_pool import reconfirm
from pool_evaluation import EP,sha
OUT=EP/'outputs/r18'

def build_candidates():
    p=engine.data();old=pd.read_parquet(EP/'outputs/r12/sealed_predictions.parquet');parts=[]
    for model,g in old[old.model.isin(['logit_levels','logit_second'])].groupby('model'):
        z=g.copy();z['model']=model+'__identity';z['probability']=z.raw_probability;z['score']=100*z.probability
        z['reference_probability']=z.groupby('date').probability.transform('mean');z['predicted_uplift']=z.probability-z.reference_probability
        z['discovery_hint']=z.row_id.map(p.rate_change.gt(0)&p.eligible)
        z['admitted']=z.discovery_hint
        q=reconfirm(z);q['candidate_stage_only']=True;parts.append(q)
    return pd.concat(parts,ignore_index=True)

def predict():
    if (OUT/'prediction_seal.json').exists():raise RuntimeError('R18 already sealed')
    OUT.mkdir(parents=True,exist_ok=True);parent=OUT/'candidate_parent.parquet';build_candidates().to_parquet(parent,index=False)
    contextual.PARENT=parent;contextual.OUT=OUT;contextual.predict()
    path=OUT/'prediction_seal.json';seal=json.loads(path.read_text())
    extra=[Path(__file__),EP/'src/single_reconfirmation_pool.py',EP/'rounds/r18_broad_event_plan.md',EP/'rounds/r17_reflection.md',EP/'outputs/r12/sealed_predictions.parquet']
    seal['inputs'].update({str(f):sha(f) for f in extra});seal['candidate_source']=str(parent.resolve());seal['discovery_rule']='price_eligible AND rate_change > 0; second known pulse per 126-session cluster';seal['formal_probability_thresholds_unchanged']=True
    path.write_text(json.dumps(seal,indent=2)+'\n')

def evaluate():
    contextual.OUT=OUT;contextual.evaluate()
    f=OUT/'evaluation_receipt.json';r=json.loads(f.read_text());r.update(round_wrapper=str(Path(__file__).resolve()),round_wrapper_sha256=sha(__file__));f.write_text(json.dumps(r,indent=2)+'\n')

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('stage',choices=['predict','evaluate']);args=a.parse_args();predict() if args.stage=='predict' else evaluate()
