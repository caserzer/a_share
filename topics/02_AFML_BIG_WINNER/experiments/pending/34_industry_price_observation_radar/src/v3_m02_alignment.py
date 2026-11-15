"""Audit bounded prefix targets against final versions; never used for fitting."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from audit_local_inputs import EP,PRIOR,sha


def main():
    out=EP/'outputs/v3_m02_maturity_audit'
    tp=EP/'outputs/v3_m02_targets/training_panel.parquet';rp=PRIOR/'daily_industries.parquet'
    pp=EP/'outputs/v2_s12_full_directory_duration/processes.parquet';cp=EP/'outputs/v2_s13_duration_enhancements/children.parquet'
    d=pd.read_parquet(tp);raw=pd.read_parquet(rp,columns=['era','industry_code','block','date','nav'])
    raw=raw[raw.nav.gt(0)&raw.block.notna()];raw['week']=raw.date.dt.to_period('W-SUN');raw['lognav']=np.log(raw.nav)
    weekly=raw.groupby(['era','industry_code','block','week']).lognav.median().to_dict()
    parents=pd.read_parquet(pp).set_index('process_id');children=pd.read_parquet(cp)
    known=set(parents.index[parents.status.eq('CONFIRMED')&~parents.left_context_unknown]);ch=children[children.status.eq('PATH_SUPPORTED')&children.parent_id.isin(known)]
    d['final_child_coverage_at_same_horizon']=False;d['final_child_early_at_same_horizon']=False
    for c in ch.itertuples():
        mask=d.eligible&d.child_coverage_target.notna()&d.era.eq(c.era)&d.industry_code.eq(c.industry_code)&d.block.eq(c.block)&d.date.between(pd.Timestamp(c.start_date),pd.Timestamp(c.end_date))&d.target_available_date.ge(pd.Timestamp(c.confirm_date))&d.target_available_date.ge(pd.Timestamp(parents.loc[c.parent_id,'confirm_date']))
        baseline=weekly[(c.era,c.industry_code,c.block,pd.Timestamp(c.start_date).to_period('W-SUN'))]
        for ix,r in d[mask].iterrows():
            high=weekly[(c.era,c.industry_code,c.block,r.date.to_period('W-SUN'))]>baseline
            if high:
                d.loc[ix,'final_child_coverage_at_same_horizon']=True
                d.loc[ix,'final_child_early_at_same_horizon']=r.date.to_period('W-SUN').ordinal<=pd.Timestamp(c.start_date).to_period('W-SUN').ordinal+1
    rows=[]
    for kind in ['coverage','early']:
        a=d[f'child_{kind}_target'];b=d[f'final_child_{kind}_at_same_horizon']
        for x in [0,1]:
            for y in [False,True]:rows.append(dict(target=kind,prefix_positive=x,final_positive=y,rows=int(((a==x)&(b==y)&d.eligible&a.notna()).sum())))
    result=pd.DataFrame(rows);dest=out/'prefix_final_training_alignment.csv'
    if dest.exists():pd.testing.assert_frame_equal(pd.read_csv(dest),result)
    else:result.to_csv(dest,index=False)
    inputs=[tp,rp,pp,cp,Path(__file__)]
    (out/'alignment_receipt.json').write_text(json.dumps(dict(inputs={str(p):sha(p) for p in inputs},artifacts={dest.name:sha(dest)},scope='Label version diagnostic only; no model scores or prediction outcomes used'),indent=2)+'\n')
    print(result.to_string(index=False))


if __name__=='__main__':main()
