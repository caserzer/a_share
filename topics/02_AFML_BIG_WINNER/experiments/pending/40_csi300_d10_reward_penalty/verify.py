"""Reproduce the input, model, selection and accounting checks without fitting again."""
from hashlib import sha256
import json
from pathlib import Path

import numpy as np
import pandas as pd
from train import HERE, OUT, OLD, PRIVATE, TRACK, ARMS, COLS, KEY, BASE, outer, predict, prepare, utility_scores
from shared import EP, ROUNDS


def main():
    p = pd.read_parquet(OUT/'scores.parquet')
    h = outer().sort_values(KEY)
    frozen = pd.read_parquet(OLD/'local_cache/predictions.parquet',columns=KEY+[BASE])
    paired = p.merge(frozen,on=KEY,validate='1:1')
    assert len(h)==len(p)==len(paired)
    maxerr = abs(paired.baseline-paired[BASE]).max()
    assert maxerr<1e-10
    folds = pd.read_csv(OUT/'folds.csv')
    d = prepare()
    maxscale = 0
    for quarter,g in h.groupby('fold'):
        model = json.loads((OUT/'models'/f'{quarter}.json').read_text())
        scored = p.set_index(KEY).loc[pd.MultiIndex.from_frame(g[KEY])]
        for arm in ARMS:
            np.testing.assert_allclose(predict(g[COLS],model[arm]),scored[arm],atol=1e-12)
        sub = d[(d.signal_date<pd.Period(quarter).start_time)&(d.h10_mature<pd.Period(quarter).start_time)].copy()
        records = folds[folds.quarter.eq(quarter)]
        assert len(records)==7 and records.rows.eq(len(sub)).all() and sub.h10_mature.max()<g.signal_date.min()
        audit = records.iloc[0]
        win = sub.decile.eq(10)
        cap = sub.loc[win,'above_median'].quantile(.95)
        np.testing.assert_allclose(cap,audit.magnitude_cap)
        rewards = pd.DataFrame(dict(binary=win, graded=sub.decile.map({8:.25,9:.5,10:1}).fillna(0)*audit.graded_scale,
                                    magnitude=win*sub.above_median.clip(upper=cap)*audit.magnitude_scale))
        mean = rewards.groupby(sub.signal_date).mean().mean()
        maxscale = max(maxscale,max(abs(mean-mean.binary)))
    assert maxscale<1e-12
    rng = np.random.default_rng(401)
    n = np.array([37,59,46])
    s,u,v = rng.normal(size=(3,n.sum()))
    args = (u,np.r_[0,n.cumsum()[:-1]],n)
    val,grad = utility_scores(s,*args)
    fd = (utility_scores(s+1e-6*v,*args)[0]-utility_scores(s-1e-6*v,*args)[0])/2e-6
    grad_err = abs(fd-grad@v)
    assert grad_err<1e-7
    rank = pd.read_parquet(OUT/'rankings.parquet')
    nn = rank.groupby(['arm','signal_date']).score.transform('size')
    assert (rank.selected==(rank['rank']<=nn//10)).all()
    assert len(rank)==len(p)*7 and not rank.duplicated(['arm',*KEY]).any()
    original = pd.read_parquet(TRACK/'results/rankings.parquet',filters=[('model','=','original'),('cost','=','base')])
    chk = rank.query('arm=="baseline"').merge(original,on=KEY,how='outer',validate='1:1',indicator=True)
    assert chk._merge.eq('both').all() and (chk.selected_x==chk.selected_y).all()
    w = pd.read_parquet(OUT/'windows.parquet')
    a = pd.read_csv(OUT/'accounts.csv')
    keys = ['scope','cost','entry_idx']
    frozen_windows = pd.read_parquet(TRACK/'results/windows.parquet',filters=[('model','=','original')])
    check = w.query('arm=="baseline"').merge(frozen_windows,on=keys,how='outer',validate='1:1',indicator=True)
    assert len(check)==417 and check._merge.eq('both').all()
    window_error = max(abs(check[k+'_x']-check[k+'_y']).max() for k in ['net','fee','turnover'])
    assert window_error<1e-10
    assert len(a)==42 and a.n.eq(a.scope.map({'primary':100,'later':39})).all()
    pos = pd.read_parquet(OUT/'positions.parquet')
    dates = p[['signal_date','entry_idx']].drop_duplicates()
    money = pos.groupby(['scope','arm','signal_date'])[['gross','fee']].sum().reset_index()
    actual = money.merge(dates,on='signal_date').merge(w.query('cost=="base"'),on=['scope','arm','entry_idx'],validate='1:1')
    assert len(actual)==973
    attribution_error = abs(actual.gross-actual.fee_x-actual.net).max()
    assert attribution_error<1e-9
    # Fingerprint the data, original code and external frozen controls needed for replay.
    inputs = [PRIVATE/(k+'.parquet') for k in ['features','labels','qfq_open','qfq_close','open','close',
              'daily_members','opening_trade_status_v2','market','industry','limits/daily','suspensions/daily']]
    inputs += [PRIVATE/'net_excess_20261116/H00300.CSI.json',EP/'outputs/local_cache/labels.parquet',
               *(OLD/'local_cache'/f for f in ['predictions.parquet','h10_features.parquet']),
               *(OLD/'outputs'/f for f in ['folds.csv','original_78_features.csv']),OLD/'model.py',
               EP/'code/core.py',EP/'code/accounts.py',TRACK/'experiment.py',TRACK/'shared.py',
               ROUNDS/'64_mature_group_switch/account.py',TRACK/'results/rankings.parquet',TRACK/'results/windows.parquet']
    receipt = dict(folds=folds.quarter.nunique(), eligible_rows=len(p), windows=len(w), replayed_positions_windows=len(actual),
                   frozen_score_error=maxerr, frozen_window_error=window_error, attribution_error=attribution_error,
                   scaled_reward_mean_error=maxscale, gradient_error=grad_err,
                   iterations_at_cap=int(folds.iterations.eq(40).sum()),nonzero_fits=int(folds.arm.ne('baseline').sum()))
    files = [*inputs,HERE/'GOAL.md',*HERE.glob('*.py'),*sorted(OUT.rglob('*'))]
    receipt['sha256'] = {str(f.relative_to(HERE.parent)):sha256(f.read_bytes()).hexdigest() for f in files
                         if f.is_file() and f.name!='verification.json'}
    (OUT/'verification.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print({k:v for k,v in receipt.items() if k!='sha256'})


if __name__=='__main__':
    main()
