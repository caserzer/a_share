import pandas as pd
from common import *


def run():
 out=ROOT/'outputs/r25'
 old=pd.read_parquet(ROOT/'data/r15_revision_coverage.parquet');new=pd.read_parquet(ROOT/'data/r25_revision_coverage.parquet')
 keys=KEY+['date','fy_offset'];c=old.merge(new,on=keys,suffixes=('_old','_new'),validate='one_to_one')
 value_changed=~np.isclose(c.covered_member_median_old,c.covered_member_median_new,equal_nan=True)
 affected=c[(c.known_old!=c.known_new)|value_changed|(c.eligible_old!=c.eligible_new)]
 affected.to_csv(out/'industry_changes_vs_r15.csv',index=False)
 pk=KEY+['date','population','fy_offset','horizon','method','year']
 a=pd.read_parquet(ROOT/'outputs/r15/predictions.parquet');b=pd.read_parquet(out/'predictions.parquet')
 q=a.merge(b,on=pk,how='outer',suffixes=('_old','_new'),indicator=True,validate='one_to_one')
 both=q._merge.eq('both');changed=both&~np.isclose(q.prediction_old,q.prediction_new,equal_nan=True)
 q.to_csv(out/'predictions_vs_r15.csv',index=False)
 summaries=pd.read_csv(ROOT/'outputs/r15/summary.csv').merge(pd.read_csv(out/'summary.csv'),on=['era','level','fy_offset','population','horizon','method'],how='outer',suffixes=('_old','_new'),validate='one_to_one')
 summaries.to_csv(out/'summary_vs_r15.csv',index=False)
 js(out/'impact_receipt.json',dict(industry_rows=len(c),changed_industry_rows=len(affected),changed_medians=int(value_changed.sum()),strict_gate_changes=int(c.eligible_old.ne(c.eligible_new).sum()),changed_member_counts=int(c.members_old.ne(c.members_new).sum()),old_predictions=len(a),new_predictions=len(b),prediction_membership=q._merge.value_counts().to_dict(),changed_common_predictions=int(changed.sum()),max_prediction_delta=float((q.loc[both,'prediction_old']-q.loc[both,'prediction_new']).abs().max()),old_model_parameters_sha256=sha(ROOT/'outputs/r15/model_parameters.json'),new_model_parameters_sha256=sha(out/'model_parameters.json'),baseline_prediction_sha256=sha(ROOT/'outputs/r15/predictions.parquet'),new_prediction_sha256=sha(out/'predictions.parquet'),accepted_increment=False))
 print(json.dumps(json.loads((out/'impact_receipt.json').read_text()),ensure_ascii=False))

if __name__=='__main__':run()
