from pathlib import Path
import sys
import json
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
OUT = HERE / 'results'
ROUNDS = HERE.parent / 'rounds'
EP = next(HERE.parents[1].glob('37_*'))
OLD = EP / 'extensions/original78_rankic_20261118'
PRIVATE = next(HERE.parents[1].glob('36_*')) / 'private'
sys.path[:0] = [str(ROUNDS/'64_mature_group_switch'), str(OLD), str(EP/'code')]
from account import setup, replay, accounts
from core import assign_deciles
from model import ridge, predict

COLS = pd.read_csv(OLD/'outputs/original_78_features.csv').feature.tolist()
KEY = ['signal_date','instrument']
BASE = 'RANK_MSE_78'

def outer():
    return pd.read_parquet(OLD/'local_cache/h10_features.parquet').dropna(subset=['exit_date'])

def labels():
    return pd.read_parquet(EP/'outputs/local_cache/labels.parquet', filters=[('offset','=',0)])[KEY+['h10']]

def market():
    accounts.OUT = OUT
    return setup('flat')
