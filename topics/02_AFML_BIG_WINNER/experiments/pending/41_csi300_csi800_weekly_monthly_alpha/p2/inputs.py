"""Reconstruct the frozen CSI300 tree using EP40's serialized boosters."""
from pathlib import Path
import sys
import hashlib
import json
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
OUT = HERE / 'results'
FOLLOW = next(HERE.parent.parent.glob('40_*/lightgbm/followup'))
sys.path.insert(0, str(FOLLOW))
from common_inputs import PRIVATE, COLS, ledger, lgb
from accounts_followup import industries
sys.path.append(str(PRIVATE.parent / 'src'))
from features import compute

SEGMENTS = [('primary','2021-01-11','2025-03-03'), ('later','2025-03-03','2026-10-12')]
ARMS = ['tree','rank','hold']
def market():
    OUT.mkdir(exist_ok=True)
    ledger.accounts.OUT = OUT
    return ledger.setup('flat')

def prepare():
    f = FOLLOW/'results/daily_scores.parquet'
    scores = pd.read_parquet(f,columns=['entry_idx','signal_date','instrument','R'])
    scores = scores[scores.signal_date <= pd.Timestamp('2026-09-30')].copy()
    raw = [pd.read_parquet(PRIVATE/(k+'.parquet')) for k in
           'qfq_close qfq_open qfq_high qfq_low volume money turnover_rate daily_members'.split()]
    ff = compute(*raw, pd.read_parquet(PRIVATE/'market.parquet').close)
    cols = [c for c in COLS if not c.startswith('market_')]
    close = raw[0]
    rows = []
    for q,g in scores.groupby(scores.signal_date.dt.to_period('Q')):
        model = FOLLOW/'csi800_69/results/models/transfer'/str(q)
        med = pd.Series(json.loads((model/'medians.json').read_text()))
        tree = lgb.Booster(model_file=str(model/'tree.txt'))
        i = close.index.get_indexer(g.signal_date)
        j = close.columns.get_indexer(g.instrument)
        x = pd.DataFrame({k:ff[k].to_numpy()[i,j] for k in cols})
        rows.append(g.assign(T=tree.predict(x.fillna(med),num_threads=2)))
    s = pd.concat(rows)
    compare = pd.read_parquet(FOLLOW/'csi800_69/results/scores.parquet',
                              columns=['signal_date','instrument','transfer_T'])
    check = s.merge(compare,on=['signal_date','instrument'],validate='1:1')
    np.testing.assert_allclose(check['T'],check.transfer_T,atol=1e-12,rtol=0)
    s.to_parquet(OUT/'scores.parquet',index=False)
    return s

def targets(m):
    s = pd.read_parquet(OUT/'scores.parquet')
    plans = {a:{} for a in ARMS + ['equal']}
    books = {}
    for e,g in s.groupby('entry_idx'):
        ordered = g.sort_values(['R','instrument'],ascending=False)
        ids = m.symbols.get_indexer(ordered.instrument)
        assert (ids>=0).all()
        tree = ordered['T'].to_numpy()
        k = len(g)//10
        n = k//5
        r = ids[:k]
        pool = ids[k:2*k]
        tree_ids = m.symbols.get_indexer(g.sort_values(['T','instrument'],ascending=False).instrument)
        removed = tree_ids[np.isin(tree_ids,r)][-n:]
        adds = tree_ids[np.isin(tree_ids,pool)][:n]
        core = r[~np.isin(r,removed)]
        plans['tree'][e] = np.r_[core,adds]
        plans['rank'][e] = np.r_[core,pool[:n]]
        plans['hold'][e] = r
        plans['equal'][e] = ids
        books[e] = (ids,r,pool,removed,adds,tree_ids)
    return plans,books

if __name__=='__main__':
    prepare()
