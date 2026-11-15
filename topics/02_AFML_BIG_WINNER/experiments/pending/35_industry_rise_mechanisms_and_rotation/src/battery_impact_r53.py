import pandas as pd
from common import *
def run():
 out=ROOT/'outputs/r53';paths=[ROOT/f'outputs/{r}/predictions.json' for r in ['r41','r53']]
 a,b=[pd.DataFrame(json.loads(p.read_text())) for p in paths];keys=KEY+['horizon','date','method'];m=a.merge(b,on=keys,how='outer',suffixes=('_old','_new'),indicator=True,validate='one_to_one');assert not m['_merge'].eq('left_only').any()
 m['prediction_change']=m.prediction_new-m.prediction_old;m.to_parquet(out/'source_version_comparison.parquet',index=False)
 rows=[]
 for key,g in m.groupby(['level','horizon','method']):
  common=g[g['_merge'].eq('both')&g.target_new.notna()];assert np.allclose(common.target_old,common.target_new)
  rows.append(dict(zip(['level','horizon','method'],key),common_evaluated=len(common),new_evaluated=int((g['_merge'].eq('right_only')&g.target_new.notna()).sum()),changed_predictions=int((g.prediction_change.abs()>1e-12).sum()),common_mse_old=float(((common.prediction_old-common.target_old)**2).mean()),common_mse_new=float(((common.prediction_new-common.target_new)**2).mean())))
 js(out/'source_impact.json',rows)
 js(out/'impact_receipt.json',dict(reads={str(p):sha(p) for p in paths},comparison_sha256=sha(out/'source_version_comparison.parquet'),code_sha256=sha(__file__),no_removed_predictions=True))
 print(pd.DataFrame(rows).to_string(index=False))
if __name__=='__main__':run()
