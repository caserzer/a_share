"""R13 fixed calibration ablation using R12 sealed raw scores."""
import argparse,json
from pathlib import Path
import pandas as pd
import probability_pool as engine
from pool_evaluation import EP,sha
OUT=EP/'outputs/r13'

def predict():
    if (OUT/'prediction_seal.json').exists():raise RuntimeError('R13 already sealed')
    OUT.mkdir(parents=True,exist_ok=True)
    original=EP/'outputs/r12/sealed_predictions.parquet';old=pd.read_parquet(original)
    rows=[]
    for method,g in old[old.model.ne('matured_base')].groupby('model'):
        for variant,weight in [('identity',0.),('shrink50',.5)]:
            z=g.copy();z['probability']=(1-weight)*g.raw_probability+weight*g.probability
            z['model']=method+'__'+variant;z['score']=100*z.probability
            z['reference_probability']=z.groupby('date').probability.transform('mean')
            z['predicted_uplift']=z.probability-z.reference_probability
            z['admitted']=engine.gate(z.probability,z.reference_probability)
            rows.append(z)
    pd.concat(rows,ignore_index=True).to_parquet(OUT/'sealed_predictions.parquet',index=False)
    inputs=[original,EP/'outputs/r12/prediction_seal.json',EP/'rounds/r12_reflection.md',EP/'rounds/r13_calibration_ablation_plan.md',EP/'configs/pool_metric_v1.json',Path(engine.__file__),Path(__file__)]
    seal={'stage':'PREDICTIONS_SEALED_BEFORE_EVALUATION','inputs':{str(f):sha(f) for f in inputs},'artifacts':{'sealed_predictions.parquet':sha(OUT/'sealed_predictions.parquet')},'adaptive_exploration_after_r12':True,'future_labels_in_prediction_file':False}
    (OUT/'prediction_seal.json').write_text(json.dumps(seal,indent=2)+'\n')
    print('R13 scores sealed: 10 fixed model/mapping combinations.')

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('stage',choices=['predict','evaluate']);args=parser.parse_args()
    if args.stage=='predict':predict()
    else:engine.OUT=OUT;engine.evaluate()
