"""Fit a dated risk/size conditional distribution from a verified feature snapshot."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.neighbors import NearestNeighbors
from run_four_horizons import OUT, TECH, GRID, BIN_NAMES, probability_stats
from probability_credibility import assess


def validate_snapshot(snapshot):
    date=pd.Timestamp(snapshot['asof'])
    available=pd.Timestamp(snapshot['feature_available_at'])
    decision=date.tz_localize('Asia/Shanghai')+pd.Timedelta(hours=23,minutes=59,seconds=59)
    if available.tzinfo is None:raise ValueError('Feature timestamp must include timezone')
    if available>decision:raise ValueError('Features not available at requested decision time')
    if snapshot['source_price_end']!=snapshot['asof']:raise ValueError('Stale price snapshot')
    f=snapshot['features']
    if not all(np.isfinite(f[c]) for c in ['vol63','log_cap']):raise ValueError('Missing/nonfinite required features')
    if f['vol63']<0 or f['log_cap']<=0:raise ValueError('Invalid risk/size features')
    if snapshot.get('source_status')!='consistent':raise ValueError('Unverified source consistency')
    return date


def predict(snapshot):
    date=validate_snapshot(snapshot)
    panel=pd.read_parquet(OUT/'local_cache/four_horizon_panel.parquet')
    eligible=panel.dropna(subset=TECH+['earnings_yield','book_yield'])
    output=dict(instrument=snapshot['instrument'],asof=snapshot['asof'],model='peers_risk_size',
        status='exploratory_prediction_not_validated_for_current_use',features=snapshot['features'],
        input_sha256=hashlib.sha256(json.dumps(snapshot,sort_keys=True).encode()).hexdigest(),
        historical_data_cutoff='2026-05-29',current_input_receipts=snapshot.get('receipts',[]),
        price_semantics='qfq close-to-close price change proxy, not verified total return',
        bin_definitions={'loss_over20':'R < -0.20','loss5_20':'-0.20 <= R < -0.05','near_flat':'-0.05 <= R < 0.05','gain5_20':'0.05 <= R < 0.20','gain_over20':'R >= 0.20'},
        horizons=[],limitations=['Current features are dated; the training label panel is not fully refreshed beyond 2026-05-29',
            'Historical validation used month-end predictions and quarterly fitting; arbitrary current dates and full-date refitting are not independently validated',
            'This model conditions only on volatility and size, not all currently known information'])
    for h in [1,3,6,12]:
        train=eligible[(eligible[f'end_{h}']<date)&eligible[f'y_{h}'].notna()]
        cols=['vol63','log_cap'];median=train[cols].median();scale=(train[cols].quantile(.75)-train[cols].quantile(.25)).replace(0,1)
        raw=(train[cols]-median)/scale
        query=pd.DataFrame([snapshot['features']])[cols]
        scaled=(query-median)/scale
        x=raw.clip(-5,5);z=scaled.clip(-5,5)
        distances,idx=NearestNeighbors(n_neighbors=min(1000,len(train)),n_jobs=1).fit(x).kneighbors(z)
        y=train[f'y_{h}'].to_numpy();globalq=np.quantile(y,GRID)
        atoms=.75*np.quantile(y[idx[0]],GRID)+.25*globalq
        stats=probability_stats(atoms[None,:],np.array([np.nan])).iloc[0]
        probabilities={f'p_{e}':float(stats[f'p_{e}']) for e in ['up','down','zero',*BIN_NAMES]}
        support={c:dict(value=float(query[c].iloc[0]),train_min=float(train[c].min()),train_max=float(train[c].max()),
            within_training_range=bool(train[c].min()<=query[c].iloc[0]<=train[c].max())) for c in cols}
        credibility=assess('peers_risk_size',h,probabilities,date)
        credibility['current_applicability']='not_established_due_to_training_gap_and_prediction_schedule_change'
        output['horizons'].append(dict(months=h,nominal_target_date=str((date+pd.DateOffset(months=h)).date()),
            target_session_rule='first market session on or after nominal target; calendar date not yet asserted',
            **probabilities,distribution=dict(atoms=atoms.tolist(),weights=[1/len(atoms)]*len(atoms)),
            training=dict(rows=len(train),last_observed_label=str(train[f'end_{h}'].max().date()),neighbors=len(idx[0]),
                feature_support=support,nearest_distance=float(distances[0,0]),farthest_neighbor_distance=float(distances[0,-1])),
            credibility=credibility))
    return output


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--snapshot',required=True);p.add_argument('--output',required=True)
    a=p.parse_args();result=predict(json.loads(Path(a.snapshot).read_text()))
    Path(a.output).parent.mkdir(parents=True,exist_ok=True)
    Path(a.output).write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    print(json.dumps(dict(instrument=result['instrument'],asof=result['asof'],status=result['status'],
        probabilities=[dict(months=h['months'],p_up=h['p_up'],p_down=h['p_down'],credibility=h['credibility']['status']) for h in result['horizons']]),indent=2))
