from pathlib import Path
import json
import sys
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parent
D=ROOT/'results'
EP=ROOT.parents[1]
WEAK=ROOT.parent/'weak_stock_underweight_20261122'
ALLOC=ROOT.parent/'d10_dividend_allocation'
sys.path.insert(0,str(EP/'code'))
from core import PRIVATE, sha, dump, bootstrap, clean

MAIN=pd.Timestamp('2025-03-03')
SPECS={'market':['trend20','breadth','relative20']}
for name,extra in [('plus_d10',['prev_d10']),('plus_red',['prev_red']),('both',['prev_d10','prev_red'])]:
    SPECS[name]=SPECS['market']+extra


def freeze():
    files=[ROOT/'PROTOCOL.md',EP/'code/core.py', EP/'code/accounts.py',EP/'config.yaml',PRIVATE/'market.parquet']
    files += [WEAK/'results'/n for n in ['schedule.csv','targets.parquet','bridge.csv','selection.json','accounts.csv','turnover.csv','tests.csv']]
    files += [ALLOC/'results/signals.csv',ALLOC/'simulate.py',ALLOC/'prepare.py']
    for path in [WEAK/'results/inputs.json',ALLOC/'results/inputs.json']:
        files.append(path)
        for name,v in json.loads(path.read_text()).items():
            assert sha(name)==v,name
            files.append(Path(name))
    files+=list((ROOT.parent/'rank_change_20261122/results').glob('ranks_targets.parquet'))
    receipt={str(p):sha(p) for p in files}
    dest=D/'inputs.json'
    if dest.exists():
        assert json.loads(dest.read_text())==receipt
    else:
        dump(dest,receipt)


def section(d):
    return 'primary' if d<=MAIN else 'later'
