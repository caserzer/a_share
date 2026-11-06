from pathlib import Path
import sys,json,hashlib,importlib.util
ROOT=Path(__file__).resolve().parents[1]
V5=ROOT.parent/'v5_rdagent_onset_forecast'
EP=ROOT.parents[1]
CACHE=Path.home()/'.cache/a_share/ep32/economic_v6'
OLD=CACHE.parent/'forecast_v5'
OUT=ROOT/'outputs'
KEY=['era','level','industry_code']
sys.path.insert(0,str(V5/'src'))
import engine as old_engine
from common import sha,js,finite_json
GROUPS={'H1':['leader_pos21','leader_neg21','peer21','peer63','leader_gap21'],
        'H2':['leader_gap_lag21','peer_breadth21','peer_breadth_change','diffusion_interaction'],
        'H3':['beta_residual21','down_resilience63']}


def freeze():
    OUT.mkdir(parents=True,exist_ok=True);CACHE.mkdir(parents=True,exist_ok=True)
    previous=json.loads((V5/'outputs/predecessors.json').read_text())
    manifest=json.loads((V5/'outputs/manifest.json').read_text())
    previous.update({str(V5/f['path']):f['sha256'] for f in manifest['files']})
    previous[str(V5/'outputs/manifest.json')]=sha(V5/'outputs/manifest.json')
    assert all(sha(p)==h for p,h in previous.items())
    js(OUT/'predecessors.json',previous)
    js(OUT/'protocol.json',dict(plan_sha256=sha(ROOT/'research_plan.md'),
        target='unchanged V5 stage B early price cycle',new_parameter_search=False,
        references=[{'title':'Hong and Stein (1999), A Unified Theory of Underreaction, Momentum Trading, and Overreaction',
          'url':'https://users.ssc.wisc.edu/~cengel/IMF/HongSteinJF1999.pdf'},
          {'title':'Hou (2007), Industry Information Diffusion and the Lead-Lag Effect in Stock Returns',
          'url':'https://papers.ssrn.com/abstract=463005'},
          {'title':'Hong, Lim, Stein (2000), Bad News Travels Slowly',
          'url':'https://www.nber.org/system/files/working_papers/w6553/w6553.pdf'}],
        source_limit='published research motivates hypotheses, not evidence of A-share positive-news diffusion'))


def unchanged():
    return all(sha(p)==h for p,h in json.loads((OUT/'predecessors.json').read_text()).items())
