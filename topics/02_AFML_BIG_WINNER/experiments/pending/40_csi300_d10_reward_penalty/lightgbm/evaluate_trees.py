"""Run the EP40 ledger and compare models on paired contiguous H10 windows."""
import hashlib
import importlib.util
import json

import numpy as np
import pandas as pd
from fit_trees import HERE, OUT, LINEAR, TREE_ARMS, KEY
import ledger

# Prior rounds also ship modules called analyze.py on the shared research path.
spec = importlib.util.spec_from_file_location('ep40_analysis', HERE.parent/'analyze.py')
analyze = importlib.util.module_from_spec(spec)
spec.loader.exec_module(analyze)

LINEAR_ARMS = ['baseline','penalty','reward','both']
PAIRS = [('tree_both','both'),('tree_both','tree_penalty'),('tree_both','tree_rank'),
         ('tree_both','baseline'),('tree_rank','baseline'),('tree_penalty','tree_rank'),
         ('tree_reward','tree_rank'),('tree_both','tree_reward')]


def verify():
    read = lambda name: pd.read_parquet(OUT/f'{name}.parquet')
    windows,rank,pos = map(read,['windows','rankings','positions'])
    keys = ['scope','cost','entry_idx','arm']
    old = pd.read_parquet(LINEAR/'windows.parquet')
    old = old[old.arm.isin(LINEAR_ARMS)].set_index(keys).sort_index()
    new = windows[windows.arm.isin(LINEAR_ARMS)].set_index(keys).sort_index()
    pd.testing.assert_frame_equal(old,new,check_exact=True)
    original = pd.read_parquet(LINEAR/'rankings.parquet',columns=KEY+['arm','selected','score'])
    rkeys = KEY+['arm']
    pd.testing.assert_frame_equal(original[original.arm.isin(LINEAR_ARMS)].set_index(rkeys).sort_index(),
        rank.loc[rank.arm.isin(LINEAR_ARMS),original.columns].set_index(rkeys).sort_index(),check_exact=True)
    assert len(rank)==40756*8 and not rank.duplicated(rkeys).any()
    assert len(windows)==139*3*8 and not windows.duplicated(keys).any()
    size=rank.groupby(['arm','signal_date']).score.transform('size')
    assert (rank.selected==(rank['rank']<=size//10)).all()
    scores=read('scores')
    pnl=pos.groupby(['scope','arm','signal_date'])[['gross','fee']].sum().reset_index()
    pnl=pnl.merge(scores[['signal_date','entry_idx']].drop_duplicates(),on='signal_date',validate='m:1')
    actual=pnl.merge(windows.query('cost=="base"'),on=['scope','arm','entry_idx'],validate='1:1')
    assert len(actual)==139*8
    err=abs(actual.gross-actual.fee_x-actual.net).max()
    assert err<1e-9
    # Descriptive check on fixed cross-sectional volatility quintiles.
    pool=rank[rank.arm.eq('baseline')].copy()
    pool['vol_group']=pool.groupby('signal_date').vol20.transform(lambda s:pd.qcut(s.rank(method='first'),5,labels=False))
    assert pool.vol_group.notna().all()
    for col,dec in [('winner',10),('loser',1)]:
        pool[col]=pool.decile.eq(dec).astype(float).where(pool.decile.notna())
        pool['peer_'+col]=pool.groupby(['signal_date','vol_group'])[col].transform('mean')
    top=rank[rank.selected].merge(pool[KEY+['winner','loser','peer_winner','peer_loser']],on=KEY,validate='m:1')
    vol=top.groupby(['scope','arm','signal_date'])[['winner','loser','peer_winner','peer_loser']].mean()
    vol.groupby(['scope','arm']).mean().to_csv(OUT/'volatility_peers.csv')
    # Interactions are paired per window before resampling.
    interactions=[]
    for (scope,cost),g in windows.groupby(['scope','cost']):
        net=g.pivot(index='entry_idx',columns='arm',values='net')*10000
        effects={'tree_add_reward_minus_linear_add_reward':(net.tree_both-net.tree_penalty)-(net.both-net.penalty),
                 'tree_factorial_interaction':(net.tree_both-net.tree_penalty)-(net.tree_reward-net.tree_rank)}
        for name,d in effects.items():
            lo,hi=analyze.interval(d.to_numpy())
            interactions.append(dict(scope=scope,cost=cost,contrast=name,net_bp=d.mean(),ci_low=lo,ci_high=hi))
    pd.DataFrame(interactions).to_csv(OUT/'interactions.csv',index=False)
    folds=pd.read_csv(OUT/'folds.csv')
    assert len(folds)==92 and folds.trees.eq(80).all() and (folds.latest_maturity<folds.first_signal).all()
    assert (folds.final_loss<folds.initial_loss).all()
    # Link the exact parent input manifest to this extension without changing it.
    files=[LINEAR/'verification.json',LINEAR/'scores.parquet',LINEAR/'rankings.parquet',LINEAR/'windows.parquet',
           *(HERE.parent/f for f in ['train.py','ledger.py','analyze.py']),*HERE.glob('*.py'),*OUT.rglob('*')]
    hashes={str(f.relative_to(HERE.parent)):hashlib.sha256(f.read_bytes()).hexdigest() for f in files
            if f.is_file() and f!=OUT/'verification.json'}
    receipt=dict(quarterly_tree_models=len(folds),eligible_rows=len(scores),windows=len(windows),
                 sealed_linear_windows=len(old),max_attribution_error=err,warm_start_max_error=folds.warm_score_error.max(),
                 training_loss_fell=int((folds.final_loss<folds.initial_loss).sum()),sha256=hashes)
    (OUT/'verification.json').write_text(json.dumps(receipt,indent=2)+'\n')


if __name__=='__main__':
    ledger.OUT=OUT
    ledger.ARMS=LINEAR_ARMS+TREE_ARMS
    ledger.main()
    analyze.OUT=OUT
    analyze.PAIRS=PAIRS
    analyze.main()
    verify()
