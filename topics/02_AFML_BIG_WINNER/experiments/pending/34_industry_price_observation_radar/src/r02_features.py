"""Price-only R02 features; reject labels and reuse audited history eligibility."""
import pandas as pd
from r01_features import features,PRICE_COLUMNS


def change_features(price_rows):
    base=features(price_rows)
    parts=[]
    for _,g in price_rows.groupby(['era','industry_code'],sort=True):
        g=g.sort_values('date');v=g.nav
        z=g[['era','industry_code','date']].copy()
        z['r5']=v/v.shift(5)-1
        z['previous20']=v.shift(20)/v.shift(40)-1
        parts.append(z)
    result=base.merge(pd.concat(parts,ignore_index=True),on=['era','industry_code','date'],validate='one_to_one')
    result=result.rename(columns={'score':'r20'})
    result['delta20']=result.r20-result.previous20
    result.loc[~result.eligible,['r5','r20','previous20','delta20']]=float('nan')
    return result
