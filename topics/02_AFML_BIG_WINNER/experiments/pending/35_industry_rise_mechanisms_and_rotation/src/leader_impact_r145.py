import pandas as pd
from common import *
from leader_models_r109 import ALL

def run():
 out=ROOT/'outputs/r145';root=out/'evaluation';keys=KEY+['date'];a=pd.read_parquet(ROOT/'outputs/r109/joined_panel.parquet');b=pd.read_parquet(root/'outputs/r109/joined_panel.parquet');rows=[]
 for cohort in ['main80','strict100']:
  x=a[a[cohort]];y=b[b[cohort]];p=x.merge(y,on=keys,how='outer',suffixes=('_old','_new'),indicator=True,validate='one_to_one');p[p._merge.ne('both')].to_csv(out/f'{cohort}_cohort_changes.csv',index=False);g=p[p._merge.eq('both')];changes={c:int((~np.isclose(g[c+'_old'],g[c+'_new'],equal_nan=True,atol=1e-12,rtol=1e-10)).sum()) for c in ALL}
  xr=x.groupby('date')[ALL].transform(centered_rank);yr=y.groupby('date')[ALL].transform(centered_rank);xp=x[keys].join(xr).merge(y[keys].join(yr),on=keys,suffixes=('_old','_new'),validate='one_to_one');rank_changes={c:int((~np.isclose(xp[c+'_old'],xp[c+'_new'],atol=1e-12,rtol=1e-10)).sum()) for c in ALL}
  rows.append(dict(cohort=cohort,old=len(x),new=len(y),added=int(p._merge.eq('right_only').sum()),removed=int(p._merge.eq('left_only').sum()),common_input_changes=changes,common_rank_changes=rank_changes))
 af=pd.read_parquet(ROOT/'outputs/r108/industry_features.parquet');bf=pd.read_parquet(root/'outputs/r108/industry_features.parquet');pd.testing.assert_frame_equal(af.drop(columns='observed_panel_row'),bf.drop(columns='observed_panel_row'))
 ao=pd.read_parquet(ROOT/'outputs/r110/industry_outcomes.parquet');bo=pd.read_parquet(root/'outputs/r110/industry_outcomes.parquet');pd.testing.assert_frame_equal(ao.drop(columns='observed_panel_row'),bo.drop(columns='observed_panel_row'))
 js(out/'cohort_impact.json',dict(cohorts=rows,changed_observed_flags=int(af.observed_panel_row.ne(bf.observed_panel_row).sum()),feature_values_and_fixed_member_outcomes_unchanged=True,code_sha256=sha(__file__)))
 print(json.dumps(rows,default=str))
if __name__=='__main__':run()
