"""Freeze one boosting schedule and compare four utilities from a shared warm start."""
from concurrent.futures import ProcessPoolExecutor
import json
import multiprocessing
from pathlib import Path
import sys

import lightgbm as lgb
import numpy as np
import pandas as pd
from scipy.optimize import brentq
from scipy.special import expit

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from train import COLS, KEY, OUT as LINEAR, outer, prepare, utility_scores

OUT = HERE/'results'
TREE_ARMS = ['tree_rank','tree_penalty','tree_reward','tree_both']
PARAMS = dict(learning_rate=.04,num_leaves=15,min_data_in_leaf=300,
              lambda_l2=10.,max_bin=63,feature_fraction=1.,bagging_fraction=1.,
              deterministic=True,force_col_wise=True,seed=4002,num_threads=2,
              verbosity=-1,boost_from_average=False)
WARM_ROUNDS, UTILITY_ROUNDS = 20,60


def topk_utility(scores, utility, starts, sizes):
    try:
        return utility_scores(scores, utility, starts, sizes)
    except ArithmeticError:
        # Some tree-score distributions give very small sigmoid slopes.
        # Bracket the identical seat-count constraint separately on each date.
        grad = np.empty_like(scores)
        value = 0.
        for start,n in zip(starts,sizes):
            sl = slice(start,start+n)
            score, u = scores[sl],utility[sl]
            sd = score.std()
            assert sd>1e-10
            z = (score-score.mean())/sd
            k = n//10
            h = brentq(lambda h: expit((z-h)/.1).sum()-k,z.min()-5,z.max()+5,xtol=1e-14)
            p = expit((z-h)/.1)
            assert abs(p.sum()-k)<1e-9
            dp = p*(1-p)/.1
            dz = dp*(u-dp@u/dp.sum())/k
            grad[sl] = (dz-dz.mean()-z*(dz*z).mean())/sd
            value += p@u/k
        return value/len(sizes),grad/len(sizes)


def fit(q):
    cutoff = pd.Period(q).start_time
    d = DATA[(DATA.signal_date<cutoff)&(DATA.h10_mature<cutoff)]
    test = OUTER[OUTER.fold==q].sort_values(KEY)
    assert len(d)==REF.loc[q,'rows'] and d.h10_mature.max()<cutoff<=test.signal_date.min()
    # Replicate EP40's fold-specific median imputation. Trees need no rescaling.
    med = d[COLS].median().fillna(0.)
    x = d[COLS].fillna(med)
    tx = test[COLS].fillna(med)
    y = d.target_rank.to_numpy()
    ds = lgb.Dataset(x,label=y,free_raw_data=False)
    warm = lgb.train(dict(PARAMS,objective='regression'),ds,num_boost_round=WARM_ROUNDS)
    size = d.groupby('signal_date').size().to_numpy()
    starts = np.r_[0,size.cumsum()[:-1]]
    bad = d.decile.le(5).to_numpy(float)
    win = d.decile.eq(10).to_numpy(float)
    scored = test[KEY].copy()
    audit = []
    model_dir = OUT/'models'/q
    model_dir.mkdir(parents=True,exist_ok=True)
    (model_dir/'medians.json').write_text(med.to_json(double_precision=15))
    warm_pred = warm.predict(x,num_threads=2)
    for arm,u in zip(TREE_ARMS,[0*bad,bad,-win,bad-win]):
        initial_error = []
        def objective(pred,dataset):
            if not initial_error:
                initial_error.append(float(np.max(abs(warm_pred-pred))))
                assert initial_error[0]<1e-10
            grad = 2*(pred-y)
            if arm!='tree_rank':
                _,extra = topk_utility(pred,u,starts,size)
                grad += len(y)*.02*extra
            # Full cross-stock second derivatives are not representable by LightGBM.
            return grad, np.full(len(y),2.)
        booster = lgb.train(dict(PARAMS,objective=objective),ds,num_boost_round=UTILITY_ROUNDS,init_model=warm)
        assert booster.num_trees()==WARM_ROUNDS+UTILITY_ROUNDS
        path = model_dir/(arm+'.txt')
        booster.save_model(str(path))
        scored[arm] = booster.predict(tx,num_threads=2)
        np.testing.assert_allclose(lgb.Booster(model_file=str(path)).predict(tx,num_threads=2),scored[arm],atol=1e-12)
        def loss(pred):
            return np.mean((pred-y)**2)+.02*topk_utility(pred,u,starts,size)[0]
        audit.append(dict(fold=q,arm=arm,rows=len(d),dates=len(size),latest_maturity=d.h10_mature.max(),
                          first_signal=test.signal_date.min(),outer_rows=len(test),trees=booster.num_trees(),
                          warm_score_error=initial_error[0],initial_loss=loss(warm_pred),
                          final_loss=loss(booster.predict(x,num_threads=2))))
    print(q,flush=True)
    return scored,audit


if __name__=='__main__':
    OUT.mkdir(exist_ok=True)
    (OUT/'config.json').write_text(json.dumps(dict(version=lgb.__version__,parameters=PARAMS,
        warm_rounds=WARM_ROUNDS,utility_rounds=UTILITY_ROUNDS,eta=.02,temperature=.1,columns=COLS),indent=2))
    DATA=prepare().sort_values(KEY)
    OUTER=outer()
    REF=pd.read_csv(LINEAR/'folds.csv').query('arm=="both"').set_index('quarter')
    with ProcessPoolExecutor(4,mp_context=multiprocessing.get_context('fork')) as pool:
        fits=list(pool.map(fit,sorted(OUTER.fold.unique())))
    trees=pd.concat([z for z,_ in fits])
    linear=pd.read_parquet(LINEAR/'scores.parquet',columns=KEY+['entry_idx','exit_idx','vol20','baseline','penalty','reward','both'])
    scores=linear.merge(trees,on=KEY,validate='1:1')
    assert len(scores)==len(trees)==len(linear)==40756 and np.isfinite(scores[TREE_ARMS]).all().all()
    scores.to_parquet(OUT/'scores.parquet',index=False)
    pd.DataFrame([row for _,rows in fits for row in rows]).to_csv(OUT/'folds.csv',index=False)
