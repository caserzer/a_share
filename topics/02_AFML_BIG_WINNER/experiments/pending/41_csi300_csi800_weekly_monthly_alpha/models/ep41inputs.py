from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
PENDING = HERE.parents[1]
FOLLOW = next(PENDING.glob('40_*')) / 'lightgbm/followup'
sys.path.insert(0, str(FOLLOW))
import accounts_followup as ep
from stagger import simulate
import numpy as np
import pandas as pd

OUT = HERE / 'results'
CACHE = Path('/tmp') / 'ep41_model_inputs_v1'
COLS = ep.COLS
STOCK = [c for c in COLS if not c.startswith('market_')]
KEY = ep.KEY
SEG = [('primary','2021-01-11','2025-03-03'),('later','2025-03-03','2026-10-12')]
TAIL = ['ncskew20','duvol20','down_gap','down_amount20','amihud20']

def pct(frame, keys):
    groups = frame.groupby(keys, observed=True)
    return groups.rank(method='average').div(groups.transform('count') + 1) - .5

def read(name):
    return pd.read_parquet(ep.PRIVATE / (name + '.parquet'))
