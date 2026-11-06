from pathlib import Path
import hashlib
import json
import sys
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
EP = ROOT.parents[1]
V4 = ROOT.parent / 'v4_adaptive_6_18_months'
V2 = ROOT.parent / 'v2_full_history_benchmark'
CACHE = Path.home() / '.cache/a_share/ep32/forecast_v5'
OUT = ROOT / 'outputs'
RD = Path('/home/xiaolv/code/RD-Agent')
KEY = ['era', 'level', 'industry_code']
THRESHOLDS = [.1, .15, .2]
BENCHMARKS = {'CSI300': '000300.SH', 'CSI_ALL': '000985.CSI'}
FEATURES = ['mom5','mom21','mom63','mom126','mom252','dd21','dd63','dd126','dd252',
            'vol21','vol63','breadth21','breadth63','volume_ratio','coverage','log_members',
            'excess21','excess63','excess126','excess252','market21','market63','market126']


def sha(p):
    h = hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def js(path, obj):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, default=str, allow_nan=False)+'\n')


def freeze_inputs():
    roots = [EP, V2, ROOT.parent/'v3_screening_review', V4, ROOT.parent/'v4_all_industry_review']
    manifest = {}
    for root in roots:
        p = root/'outputs/manifest.json'
        m = json.loads(p.read_text())
        for item in m['files']:
            f = root/item['path']
            assert sha(f) == item['sha256'], f
            manifest[str(f)] = item['sha256']
        manifest[str(p)] = sha(p)
    js(OUT/'predecessors.json', manifest)
    js(OUT/'protocol_identity.json', {'research_plan_sha256':sha(ROOT/'research_plan.md'),
         'horizon':'one_calendar_month', 'quality':'Historical-proxy', 'strict_PIT':'BLOCKED_DATA'})


def verify_predecessors():
    return all(sha(p) == h for p,h in json.loads((OUT/'predecessors.json').read_text()).items())


def load_turns():
    import importlib.util
    spec = importlib.util.spec_from_file_location('frozen_turns', V4/'src/turns.py')
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod.upswings


def finite_json(obj):
    if isinstance(obj, dict): return {str(k):finite_json(v) for k,v in obj.items()}
    if isinstance(obj, list): return [finite_json(v) for v in obj]
    if isinstance(obj, (float,np.floating)) and not np.isfinite(obj): return None
    if isinstance(obj, np.generic): return obj.item()
    return obj
