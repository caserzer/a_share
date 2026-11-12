"""R15 unique opportunity admission on second known gate edge, then updates only."""
import argparse,json
from pathlib import Path
import numpy as np
import pandas as pd
import probability_pool as engine
from pool_evaluation import EP,KEY,sha
OUT=EP/'outputs/r15'

def reconfirm(g):
    g=engine.admission_events(g)
    g['raw_gate']=g.admitted;g['raw_entry']=g.entry
    g['admitted']=False;g['formal_entry']=False;g['opportunity_id']=None;g['anchor_row_id']=np.nan;g['anchor_day_i']=np.nan
    for key,a in g.groupby(KEY):
        anchor_day=None;anchor_row=None;cluster=0;hits=0;confirmed=False;prev_week=None
        for ix,r in a.iterrows():
            gap=prev_week is not None and r.week_i-prev_week!=1
            if gap:anchor_day=None;anchor_row=None;hits=0;confirmed=False
            if anchor_day is not None and r.day_i-anchor_day>=126:anchor_day=None;anchor_row=None;hits=0;confirmed=False
            if r.raw_entry:
                if anchor_day is None:
                    cluster+=1;anchor_day=int(r.day_i);anchor_row=int(r.row_id);hits=1;confirmed=False
                else:
                    hits+=1
                    if hits==2:confirmed=True;g.loc[ix,'formal_entry']=True
            if anchor_day is not None:
                g.loc[ix,'opportunity_id']='|'.join(map(str,key))+f'|{cluster}'
                g.loc[ix,'anchor_row_id']=anchor_row;g.loc[ix,'anchor_day_i']=anchor_day
                g.loc[ix,'admitted']=bool(confirmed and r.raw_gate)
            prev_week=r.week_i
    g['state_edge']=g.admitted&g.groupby(KEY).admitted.shift().eq(False)&g.week_i.sub(g.groupby(KEY).week_i.shift()).eq(1)
    assert not (g.formal_entry&~g.state_edge).any()
    # Primary unit is one formal entry per opportunity, not each later state edge.
    g['entry']=g.formal_entry
    g['refit_entry']=g.entry&g.fold.ne(g.groupby(KEY).fold.shift())
    g['boundary_unknown']=g.raw_gate&~g.week_i.sub(g.groupby(KEY).week_i.shift()).eq(1)
    g['cooldown126']=False
    for _,a in g[g.entry].groupby(KEY):
        last=-100000
        for ix,r in a.iterrows():
            if r.day_i-last>=126:g.loc[ix,'cooldown126']=True;last=r.day_i
    return g

def predict():
    if (OUT/'prediction_seal.json').exists():raise RuntimeError('R15 already sealed')
    OUT.mkdir(parents=True,exist_ok=True)
    raw=pd.read_parquet(EP/'outputs/r14/sealed_predictions.parquet');parts=[]
    for model,g in raw.groupby('model'):
        parts.append(reconfirm(g))
    result=pd.concat(parts,ignore_index=True)
    result.to_parquet(OUT/'sealed_predictions.parquet',index=False)
    inputs=[EP/'outputs/r14/sealed_predictions.parquet',EP/'rounds/r15_single_reconfirmation_plan.md',EP/'rounds/r14_reflection.md',EP/'configs/pool_metric_v1.json',Path(engine.__file__),Path(__file__)]
    seal={'stage':'PREDICTIONS_AND_ADMISSION_POLICY_SEALED_BEFORE_EVALUATION','inputs':{str(f):sha(f) for f in inputs},'artifacts':{'sealed_predictions.parquet':sha(OUT/'sealed_predictions.parquet')},'adaptive_exploration':True,'primary_entry':'one second confirmation per prefix-defined opportunity; later updates never count again','future_labels_in_prediction_file':False}
    (OUT/'prediction_seal.json').write_text(json.dumps(seal,indent=2)+'\n')
    print('R15 policy sealed; raw scores and thresholds unchanged.')

def evaluate():
    original=engine.block_interval
    engine.block_interval=lambda z,dates,block=26:original(z,dates,26 if block==25 else block)
    engine.OUT=OUT
    # Input contains prefix-only policy state; do not let legacy edge counter recount updates.
    engine.admission_events=lambda g:g.sort_values(KEY+['date']).copy()
    engine.evaluate()
    receipt=json.loads((OUT/'evaluation_receipt.json').read_text());receipt.update(policy_wrapper=str(Path(__file__).resolve()),wrapper_sha256=sha(__file__),primary_bootstrap_weeks=26,unique_opportunity_entry=True)
    (OUT/'evaluation_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('stage',choices=['predict','evaluate']);a=p.parse_args();predict() if a.stage=='predict' else evaluate()
