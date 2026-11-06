from pathlib import Path
import sys,json
ROOT=Path(__file__).resolve().parents[1]
V5=ROOT.parent/'v5_rdagent_onset_forecast'
V6=ROOT.parent/'v6_economic_diffusion'
V7=ROOT.parent/'v7_online_stage'
V8=ROOT.parent/'v8_pooled_stage'
V9=ROOT.parent/'v9_market_context'
CACHE=Path.home()/'.cache/a_share/ep32/delay_v10'
OLD=CACHE.parent/'forecast_v5'
OUT=ROOT/'outputs'
sys.path.insert(0,str(V8/'src'))
from context8 import FEATURES,KEY,engine,sha,js,finite_json


def freeze():
    OUT.mkdir(parents=True,exist_ok=True);CACHE.mkdir(parents=True,exist_ok=True)
    previous=json.loads((V9/'outputs/predecessors.json').read_text())
    manifest=json.loads((V9/'outputs/manifest.json').read_text())
    previous.update({str(V9/f['path']):f['sha256'] for f in manifest['files']})
    previous[str(V9/'outputs/manifest.json')]=sha(V9/'outputs/manifest.json')
    assert all(sha(p)==h for p,h in previous.items())
    js(OUT/'predecessors.json',previous)
