from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parent
DEST = ROOT/'results'
sys.path.insert(0,str(ROOT.parent))
from fit_trees import COLS, KEY, LINEAR, OUT, PARAMS, lgb, prepare
from train import PRIVATE, TRACK, outer, predict, ridge
import ledger
import numpy as np
import pandas as pd
import json
SEAL = next(TRACK.parent.glob('rounds/38_*/results'))/'scores.parquet'
