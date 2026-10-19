"""Retrieve a dated four-horizon forecast and its retrospective reliability evidence.

Only cached historical dates are supported; never silently substitutes stale data.
"""
import argparse
import json
import numpy as np
import pandas as pd
from run_four_horizons import DEST, CACHE, BIN_NAMES
from probability_credibility import assess


def predict(stock, asof, model):
    date = pd.Timestamp(asof)
    result = dict(instrument=stock, asof=str(date.date()), data_cutoff='2026-05-29',
        status='historical_research_only', model=model,
        target='calendar-month qfq price change from decision close; not verified total return', horizons=[])
    calibration = pd.read_csv(DEST/'probability_calibration.csv')
    for h in [1,3,6,12]:
        data = pd.read_parquet(DEST/f'predictions_{h}m.parquet')
        row = data[(data.instrument==stock)&(data.date==date)&(data.model==model)]
        if len(row)!=1:
            raise ValueError(f'No exact forecast for {stock} on {asof}, {h} months; no stale substitution')
        row = row.iloc[0]
        quarter = str(date.to_period('Q'))
        keys = pd.read_parquet(CACHE/f'{h}_{quarter}_keys.parquet')
        pos = np.flatnonzero(((keys.instrument==stock)&(keys.date==date)).to_numpy())
        assert len(pos)==1
        distribution = np.load(CACHE/f'{h}_{quarter}_{model}.npz')
        atoms = distribution['atoms'][pos[0]]
        weights = distribution['weights'][pos[0]] if 'weights' in distribution.files else np.full(len(atoms),1/len(atoms))
        evidence = calibration[(calibration.months==h)&(calibration.model==model)&(calibration.event=='up')&
            (calibration.bin==min(9,int(np.floor(row.p_up*10))))]
        item = dict(months=h,target_date=str(row.target_date.date()),p_up=row.p_up,p_down=row.p_down,p_zero=row.p_zero,
            intervals={name:row[f'p_{name}'] for name in BIN_NAMES},
            distribution=dict(atoms=atoms.tolist(),weights=weights.tolist()),
            reliability_evidence=evidence.to_dict(orient='records'),
            credibility=assess(model,h,{f'p_{e}':float(row[f'p_{e}']) for e in ['up','down','zero',*BIN_NAMES]},'2026-05-30'),
            reliability_scope='retrospective population-bin calibration, not stock-specific guarantee; may use outcomes after forecast date')
        result['horizons'].append(item)
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--stock',required=True)
    p.add_argument('--asof',required=True)
    p.add_argument('--model',default='peers_risk_size',choices=['expanding_empirical','recent24_empirical','peers_risk_size','peers_full','catboost_full','logistic_bins','peers_risk_size_pitcal','peers_full_pitcal','catboost_full_pitcal'])
    a=p.parse_args()
    print(json.dumps(predict(a.stock,a.asof,a.model),ensure_ascii=False,indent=2))
