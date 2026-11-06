from pathlib import Path
import sys,json
ROOT=Path(__file__).resolve().parents[1]
V5=ROOT.parent/'v5_rdagent_onset_forecast'
V6=ROOT.parent/'v6_economic_diffusion'
V7=ROOT.parent/'v7_online_stage'
V8=ROOT.parent/'v8_pooled_stage'
V9=ROOT.parent/'v9_market_context'
V10=ROOT.parent/'v10_label_delay'
V11=ROOT.parent/'v11_error_audit'
CACHE=Path.home()/'.cache/a_share/ep32/duration_v12'
OLD=CACHE.parent/'forecast_v5'
OUT=ROOT/'outputs'
sys.path.insert(0,str(V8/'src'))
from context8 import FEATURES as BASE_FEATURES,KEY,engine,sha,js,finite_json
ADDED=['risk_clock21','risk_clock63','risk_vol_accel','risk_drift','risk_distance',
       'risk_progress','risk_excess','risk_age']
FEATURES=BASE_FEATURES+ADDED


def freeze():
    OUT.mkdir(parents=True,exist_ok=True);CACHE.mkdir(parents=True,exist_ok=True)
    previous=json.loads((V11/'outputs/predecessors.json').read_text())
    manifest=json.loads((V11/'outputs/manifest.json').read_text())
    previous.update({str(V11/f['path']):f['sha256'] for f in manifest['files']})
    previous[str(V11/'outputs/manifest.json')]=sha(V11/'outputs/manifest.json')
    assert all(sha(p)==h for p,h in previous.items())
    js(OUT/'predecessors.json',previous)
