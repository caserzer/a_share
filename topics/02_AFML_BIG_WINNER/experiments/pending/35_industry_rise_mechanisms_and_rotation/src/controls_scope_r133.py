"""Explicit identities for market-control coverage and common-cohort changes."""
import pandas as pd
from common import *
K=KEY+['date']

def run():
    out=ROOT/'outputs/r133';cp=out/'control_pairs.parquet';ap=out/'cohort_old.parquet';bp=out/'cohort_new.parquet'
    a=pd.read_parquet(ap).set_index(K);b=pd.read_parquet(bp).set_index(K);added=b.loc[~b.index.isin(a.index)].reset_index();removed=a.loc[~a.index.isin(b.index)].reset_index()
    added.to_parquet(out/'cohort_added.parquet',index=False);removed.to_parquet(out/'cohort_removed.parquet',index=False)
    p=pd.read_parquet(cp);v=p[p._merge.eq('both')].copy();changed=~np.isclose(v.market_beta126_old,v.market_beta126_new,equal_nan=True,atol=1e-12,rtol=1e-12);v.loc[changed].to_parquet(out/'changed_controls.parquet',index=False)
    known_old=v.market_controls_complete_old.eq(True);known_new=v.market_controls_complete_new.eq(True)
    common=a.index.intersection(b.index);cols=[c for c in a if c.startswith('rank_')];mask=~np.isclose(a.loc[common,cols],b.loc[common,cols],atol=1e-12,rtol=1e-12,equal_nan=True).all(axis=1);rankids=common[mask].to_frame(index=False);rankids.to_parquet(out/'changed_rank_identities.parquet',index=False)
    js(out/'scope_summary.json',dict(reads={str(p):sha(p) for p in [cp,ap,bp,Path(__file__)]},controls_became_known=int((~known_old&known_new).sum()),controls_became_unknown=int((known_old&~known_new).sum()),changed_both_known=int((changed&known_old&known_new).sum()),cohort_added=added[K].to_dict('records'),cohort_removed=removed[K].to_dict('records'),rank_changes_by_era_level=rankids.groupby(['era','level']).size().rename('rows').reset_index().to_dict('records'),state='downstream_fit_scope_not_yet_audited'))
    print('SCOPE',len(added),len(removed),len(rankids))

if __name__=='__main__':run()
