import pandas as pd
from common import *
def run():
 out=ROOT/'outputs/r147';root=out/'evaluation';a=pd.DataFrame(json.loads((ROOT/'outputs/r71/summary.json').read_text()));b=pd.DataFrame(json.loads((root/'outputs/r71/summary.json').read_text()));keys=['level','period','outcome'];p=a.merge(b,on=keys,how='outer',suffixes=('_old','_new'),indicator=True,validate='one_to_one');assert p._merge.eq('both').all();p.to_csv(out/'r71_summary_comparison.csv',index=False);stats={}
 for c in a.select_dtypes(include='number').columns:
  x=p[c+'_old'];y=p[c+'_new'];stats[c]=dict(changed=int((~np.isclose(x,y,atol=1e-12,rtol=1e-10,equal_nan=True)).sum()),max_abs=float((x-y).abs().max()))
 a=pd.read_parquet(ROOT/'outputs/r74/evidence_matrix.parquet');b=pd.read_parquet(root/'outputs/r74/evidence_matrix.parquet');keys=KEY+['asof','clock'];p=a.merge(b,on=keys,how='outer',suffixes=('_old','_new'),indicator=True,validate='one_to_one');assert p._merge.eq('both').all();changed=p.operating_status_old.ne(p.operating_status_new);p[changed][keys+['operating_status_old','operating_status_new']].to_csv(out/'operating_status_changes.csv',index=False)
 counts=p[changed].groupby(['asof','clock','operating_status_old','operating_status_new']).size().reset_index(name='rows');counts.to_csv(out/'operating_status_transitions.csv',index=False)
 js(out/'impact.json',dict(r71_summary=stats,operating_status_changes=int(changed.sum()),new_current_available=int(b.operating_status.eq('historical_proxy_available').sum()),code_sha256=sha(__file__)))
 print('IMPACT',int(changed.sum()),stats['standardized_difference'],stats['pooled_up'])
if __name__=='__main__':run()
