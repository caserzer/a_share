from pathlib import Path
import sys,json
ROOT=Path(__file__).resolve().parents[1]
V5=ROOT.parent/'v5_rdagent_onset_forecast'
V6=ROOT.parent/'v6_economic_diffusion'
V7=ROOT.parent/'v7_online_stage'
V8=ROOT.parent/'v8_pooled_stage'
V9=ROOT.parent/'v9_market_context'
V10=ROOT.parent/'v10_label_delay'
V12=ROOT.parent/'v12_duration_risk'
V13=ROOT.parent/'v13_completed_history'
V14=ROOT.parent/'v14_relative_baseline_audit'
CACHE=Path.home()/'.cache/a_share/ep32/rank_v15'
OLD=CACHE.parent/'forecast_v5'
OUT=ROOT/'outputs'
sys.path.insert(0,str(V13/'src'))
from context13 import FEATURES,KEY,engine,sha,js,finite_json


def freeze():
    OUT.mkdir(parents=True,exist_ok=True);CACHE.mkdir(parents=True,exist_ok=True)
    previous=json.loads((V14/'outputs/predecessors.json').read_text())
    manifest=json.loads((V14/'outputs/manifest.json').read_text())
    previous.update({str(V14/f['path']):f['sha256'] for f in manifest['files']})
    previous[str(V14/'outputs/manifest.json')]=sha(V14/'outputs/manifest.json')
    assert all(sha(p)==h for p,h in previous.items());js(OUT/'predecessors.json',previous)
