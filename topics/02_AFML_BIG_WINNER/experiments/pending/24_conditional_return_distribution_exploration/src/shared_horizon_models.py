"""Pool only separately mature labels, with balanced horizon and origin mass."""
import numpy as np
import pandas as pd
from run_market_time_models import select_training


def stack_training(panel, date, horizons, features):
    parts=[]
    for h in horizons:
        train = select_training(panel, h, date, None)
        part = train[['date', 'instrument']+features].copy()
        part['horizon_months'] = h
        part['label'] = train[f'y_{h}'].to_numpy()
        part['label_end'] = train[f'end_{h}'].to_numpy()
        parts.append(part)
    result = pd.concat(parts, ignore_index=True)
    if set(result.horizon_months) != set(horizons): raise ValueError('Every training horizon needs mature rows')
    if result.duplicated(['date', 'instrument', 'horizon_months']).any(): raise ValueError('Duplicate origin/issuer/horizon')
    assert result.date.lt(date).all() and result.label_end.lt(date).all() and result.label.notna().all()
    return result


def pooled_weights(train, total_mass):
    if total_mass <= 0: raise ValueError('Positive effective training mass required')
    k = train.horizon_months.nunique()
    origins = train.groupby('horizon_months').date.transform('nunique').to_numpy()
    rows = train.groupby(['horizon_months', 'date']).date.transform('size').to_numpy()
    weights = total_mass/(k*origins*rows)
    np.testing.assert_allclose(weights.sum(), total_mass, rtol=1e-12)
    return weights


def queries(test, features, horizons=(1, 3, 6)):
    return pd.concat([test[features].assign(horizon_months=h) for h in horizons], ignore_index=True)
