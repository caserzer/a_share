"""Inspect fixed training-unit concentration; no model fits or performance search."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from audit_local_inputs import EP,sha


def main():
    source=EP/'outputs/v3_m02_targets/training_panel.parquet';out=EP/'outputs/v3_m03_decisions'
    d=pd.read_parquet(source);rows=[]
    for year in [2020,2026]:
        t=d[d.eligible&d.parent_coverage_target.notna()&d.target_available_date.lt(pd.Timestamp(year=year,month=1,day=1))].copy()
        t['date_weight']=1/t.groupby('date').date.transform('size')
        for target in ['parent_coverage_target','parent_early_target','child_early_target']:
            pos=t[t[target].eq(1)];key='child_reference' if target.startswith('child') else 'parent_reference'
            g=pos.groupby(key).agg(rows=('date','size'),mass=('date_weight','sum'));k=max(1,int(np.ceil(len(g)*.1)))
            rows.append(dict(year=year,target=target,positive_rows=len(pos),prefix_references=len(g),rows_p50=g.rows.median(),rows_p90=g.rows.quantile(.9),rows_max=int(g.rows.max()),top_decile_row_share=float(g.nlargest(k,'rows').rows.sum()/len(pos)),top_decile_weight_share=float(g.nlargest(k,'mass').mass.sum()/g.mass.sum())))
    r=pd.DataFrame(rows);file=out/'training_unit_concentration.csv'
    if file.exists():pd.testing.assert_frame_equal(pd.read_csv(file),r)
    else:r.to_csv(file,index=False)
    sources=[source,EP/'protocols/v3_r00/m01_plan.md',Path(__file__)]
    (out/'training_unit_receipt.json').write_text(json.dumps(dict(inputs={str(p):sha(p) for p in sources},artifacts={file.name:sha(file)},limits='Descriptive concentration in first/latest annual training sets; prefix references are not certified independent final opportunities. No new model or alternative weight tested.'),indent=2)+'\n')
    print(r.to_string(index=False))


if __name__=='__main__':main()
