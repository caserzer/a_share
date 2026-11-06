from pathlib import Path
import sys,json
ROOT=Path(__file__).resolve().parents[1]
V5=ROOT.parent/'v5_rdagent_onset_forecast'
V6=ROOT.parent/'v6_economic_diffusion'
CACHE=Path.home()/'.cache/a_share/ep32/online_v7'
OLD=CACHE.parent/'forecast_v5'
OUT=ROOT/'outputs'
sys.path.insert(0,str(V5/'src'))
import engine
from common import sha,js,finite_json,KEY,THRESHOLDS,BENCHMARKS
STATE=['state_direction','state_left','state_age','state_confirm_age','state_drawup',
       'state_drawdown','state_previous_decline','state_excess','state_eligible']


def freeze():
    OUT.mkdir(parents=True,exist_ok=True);CACHE.mkdir(parents=True,exist_ok=True)
    previous=json.loads((V6/'outputs/predecessors.json').read_text())
    manifest=json.loads((V6/'outputs/manifest.json').read_text())
    previous.update({str(V6/f['path']):f['sha256'] for f in manifest['files']})
    previous[str(V6/'outputs/manifest.json')]=sha(V6/'outputs/manifest.json')
    assert all(sha(p)==h for p,h in previous.items())
    js(OUT/'predecessors.json',previous)
    js(OUT/'protocol.json',dict(plan_sha256=sha(ROOT/'research_plan.md'),
        primary_origin_start='2021-01-01',primary_origin_end='2024-09-30',label_followup_months=24,
        target='unchanged V5 stage B',strict_PIT='BLOCKED_DATA',independent_holdout=False))
