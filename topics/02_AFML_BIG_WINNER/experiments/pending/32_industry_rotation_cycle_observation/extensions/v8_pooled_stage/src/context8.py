from pathlib import Path
import sys,json
ROOT=Path(__file__).resolve().parents[1]
V5=ROOT.parent/'v5_rdagent_onset_forecast'
V6=ROOT.parent/'v6_economic_diffusion'
V7=ROOT.parent/'v7_online_stage'
CACHE=Path.home()/'.cache/a_share/ep32/pooled_v8'
OLD=CACHE.parent/'forecast_v5'
STATECACHE=CACHE.parent/'online_v7'
OUT=ROOT/'outputs'
sys.path.insert(0,str(V5/'src'))
import engine
from common import sha,js,finite_json,KEY
FEATURES=['state_direction','state_age','state_confirm_age','state_drawup','state_drawdown',
          'state_previous_decline','state_excess','mom21','mom63','excess21','excess63','market21','market63',
          'vol63','breadth21','breadth63','volume_ratio','threshold','benchmark_code']


def freeze():
    OUT.mkdir(parents=True,exist_ok=True);CACHE.mkdir(parents=True,exist_ok=True)
    old=json.loads((V7/'outputs/predecessors.json').read_text())
    manifest=json.loads((V7/'outputs/manifest.json').read_text())
    old.update({str(V7/f['path']):f['sha256'] for f in manifest['files']})
    old[str(V7/'outputs/manifest.json')]=sha(V7/'outputs/manifest.json')
    assert all(sha(p)==h for p,h in old.items())
    js(OUT/'predecessors.json',old)
