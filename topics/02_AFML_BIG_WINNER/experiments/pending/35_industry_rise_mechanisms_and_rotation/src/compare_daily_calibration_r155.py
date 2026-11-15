"""Compare preserved original and corrected daily calibration evidence."""
import pandas as pd
from common import *

def run():
 out=ROOT/'outputs/r155';root=out/'evaluation';summary={}
 for name,rel,keys,values in [
  ('scores','data/r09_daily_scores.parquet',KEY+['date'],['score','y']),
  ('predictions','outputs/r97/predictions.parquet',KEY+['date'],['monthly_probability','daily_probability','y']),
  ('alerts','outputs/r98/alerts.parquet',KEY+['date','version','strategy'],[])]:
  a=pd.read_parquet(ROOT/rel);b=pd.read_parquet(root/rel);p=a.merge(b,on=keys,how='outer',suffixes=('_old','_new'),indicator=True,validate='one_to_one');common=p[p._merge.eq('both')];changes={}
  if name=='alerts':
   p['comparison_year']=p.date.dt.year
   p.groupby(['era','level','comparison_year','version','strategy','_merge'],observed=True).size().rename('rows').reset_index().to_csv(out/'alert_identity_counts.csv',index=False)
  for c in values:
   x=common[c+'_old'];y=common[c+'_new'];changes[c]=dict(changed=int((~np.isclose(x,y,atol=1e-12,rtol=1e-10,equal_nan=True)).sum()),max_abs=float((x-y).abs().max()),known_to_unknown=int((x.notna()&y.isna()).sum()),unknown_to_known=int((x.isna()&y.notna()).sum()))
  summary[name]=dict(old=len(a),new=len(b),added=int(p._merge.eq('right_only').sum()),removed=int(p._merge.eq('left_only').sum()),changes=changes)
 a=pd.DataFrame(json.loads((ROOT/'outputs/r99/summary.json').read_text()));b=pd.DataFrame(json.loads((root/'outputs/r99/summary.json').read_text()));p=a.merge(b,on=['era','level','year'],suffixes=('_old','_new'),validate='one_to_one')
 for side in ['old','new']:
  p['family_conclusion_'+side]=np.where(p['high_family_'+side]<0,'daily_better',np.where(p['low_family_'+side]>0,'daily_worse','inconclusive'))
 p.to_csv(out/'uncertainty_comparison.csv',index=False);summary['uncertainty']=dict(folds=len(p),family_conclusion_changes=int((p.family_conclusion_old!=p.family_conclusion_new).sum()),max_point_change=float((p.point_old-p.point_new).abs().max()),new_conclusions=p.groupby(['era','family_conclusion_new']).size().to_dict())
 summary['uncertainty']['new_conclusions']={str(k):v for k,v in summary['uncertainty']['new_conclusions'].items()}
 for round_ in [97,98]:
  a=pd.DataFrame(json.loads((ROOT/f'outputs/r{round_}/summary.json').read_text()));b=pd.DataFrame(json.loads((root/f'outputs/r{round_}/summary.json').read_text()));a.to_csv(out/f'r{round_}_original_summary.csv',index=False);b.to_csv(out/f'r{round_}_corrected_summary.csv',index=False)
 js(out/'comparison.json',summary);print(json.dumps(summary,default=str,indent=2))
if __name__=='__main__':run()
