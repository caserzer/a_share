"""Market-state features from contemporaneous membership, not today's sector map."""
import json
import numpy as np
import pandas as pd
from build_improvement_features import FEATURE_PANEL
from prepare_panel import OUT

DEST = OUT / 'r17_market_information'
FEATURES = OUT / 'local_cache/market_breadth_features.parquet'
PRICE = ['csi300_mom21', 'csi300_mom63', 'csi300_mom126', 'csi300_vol63', 'all_a_mom21']
MACRO = ['credit_spread_3y', 'credit_change63', 'gov_3y', 'yield_slope',
         'market_earnings_yield', 'market_pe_percentile']
BREADTH = ['breadth21', 'breadth63', 'breadth126', 'above_ma20', 'dispersion21',
           'dispersion63', 'median_vol63', 'cap_concentration', 'small_large_mom63']


def fraction_positive(series):
    values = series.dropna()
    return (values > 0).mean() if len(values) else np.nan


def median_known(series):
    values = series.dropna()
    return values.median() if len(values) else np.nan


def aggregate_month(g):
    r = {col: median_known(g[col]) for col in PRICE + MACRO[:4]}
    for n in [21, 63, 126]:
        r[f'breadth{n}'] = fraction_positive(g[f'mom{n}'])
    r['above_ma20'] = fraction_positive(g.ma20_distance)
    r['dispersion21'] = g.mom21.std()
    r['dispersion63'] = g.mom63.std()
    r['median_vol63'] = median_known(g.vol63)
    cap = g.total_market_cap_cny.where(g.total_market_cap_cny > 0)
    r['cap_concentration'] = ((cap / cap.sum()) ** 2).sum()
    threshold = cap.median()
    r['small_large_mom63'] = median_known(g.loc[cap <= threshold, 'mom63']) - median_known(g.loc[cap > threshold, 'mom63'])
    r['market_earnings_yield'] = median_known(g.earnings_yield)
    r['market_pe_percentile'] = median_known(g.pe_percentile)
    r['members'] = len(g)
    r['breadth63_support'] = g.mom63.notna().sum()
    r['valuation_support'] = g.earnings_yield.notna().sum()
    return pd.Series(r)


def build():
    DEST.mkdir(exist_ok=True)
    d = pd.read_parquet(FEATURE_PANEL)
    columns = ['date', 'instrument', 'mom21', 'mom63', 'mom126', 'ma20_distance', 'vol63',
               'total_market_cap_cny', 'earnings_yield', 'pe_percentile'] + PRICE + MACRO[:4]
    known = d[list(dict.fromkeys(columns))]
    assert not any(c.startswith('y_') or 'label' in c or 'end_' in c for c in known)
    rows = []
    for date, g in known.groupby('date', sort=True):
        r = aggregate_month(g); r['date'] = date; rows.append(r)
    features = pd.DataFrame(rows).set_index('date')
    features.to_parquet(FEATURES)
    audit = dict(months=len(features), members=sorted(features.members.unique().tolist()),
                 min_breadth63_support_since2021=int(features.loc['2021':].breadth63_support.min()),
                 min_valuation_support_since2021=int(features.loc['2021':].valuation_support.min()),
                 missing_since2021=features.loc['2021':, PRICE + MACRO + BREADTH].isna().sum().to_dict(),
                 population='historical top400/main plus top100/ChiNext, not full A-share market',
                 original_ST_selection_bias='unchanged; not solved by these features')
    (DEST / 'feature_audit.json').write_text(json.dumps(audit, indent=2) + '\n')
    print(json.dumps(audit, indent=2))


if __name__ == '__main__':
    build()
