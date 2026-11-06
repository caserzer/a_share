from pathlib import Path
import sys,json
ROOT=Path(__file__).resolve().parents[1]
V5=ROOT.parent/'v5_rdagent_onset_forecast'
V6=ROOT.parent/'v6_economic_diffusion'
V7=ROOT.parent/'v7_online_stage'
V8=ROOT.parent/'v8_pooled_stage'
CACHE=Path.home()/'.cache/a_share/ep32/context_v9'
OLD=CACHE.parent/'forecast_v5'
OUT=ROOT/'outputs'
sys.path.insert(0,str(V8/'src'))
from context8 import FEATURES as BASE_FEATURES
sys.path.insert(0,str(V7/'src'))
from state7 import trace
from common import sha,js,finite_json,KEY
import engine
MARKET=['state_direction','state_age','state_confirm_age','state_drawup','state_drawdown','state_previous_decline']
ADDED=['market_'+s for s in MARKET]+['relative_low_age','cross_up','cross_eligible','cross_positive_excess',
    'cross_breadth','cross_excess_dispersion','excess21_rank','excess63_rank']
FEATURES=BASE_FEATURES+ADDED


def freeze():
    OUT.mkdir(parents=True,exist_ok=True);CACHE.mkdir(parents=True,exist_ok=True)
    previous=json.loads((V8/'outputs/predecessors.json').read_text())
    manifest=json.loads((V8/'outputs/manifest.json').read_text())
    previous.update({str(V8/f['path']):f['sha256'] for f in manifest['files']})
    previous[str(V8/'outputs/manifest.json')]=sha(V8/'outputs/manifest.json')
    assert all(sha(p)==h for p,h in previous.items())
    js(OUT/'predecessors.json',previous)
