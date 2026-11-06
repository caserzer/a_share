"""Paths and auditable working outputs for the adaptive-stage redo."""
from pathlib import Path
import sys
import json
import gzip

EP = Path(__file__).resolve().parents[1]
OLD = EP.parents[1]
V2 = EP.parent / 'v2_full_history_benchmark'
V3 = EP.parent / 'v3_screening_review'
sys.path.insert(0, str(V2 / 'src'))
import core as previous

OUT = EP / 'outputs'
CACHE = Path.home() / '.cache/a_share/ep32/adaptive_v4'
THRESHOLDS = [.10, .15, .20]
POLICIES = [('EXACT', 0), ('MARK_7D', 7), ('MARK_31D', 31)]
BENCHMARKS = [('CSI300', '000300.SH'), ('CSI_ALL', '000985.CSI')]


def sha(path):
    return previous.v1.sha(path)


def js(name, value):
    previous.write_json(OUT / (name + '.json'), value)


def csv(name, frame):
    p = OUT / (name + '.csv')
    p.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(p, index=False, lineterminator='\n')


def detail(name, frame):
    CACHE.mkdir(parents=True, exist_ok=True)
    private = CACHE / (name + '.csv')
    frame.to_csv(private, index=False, lineterminator='\n')
    public = OUT / 'details' / (name + '.csv.gz')
    public.parent.mkdir(parents=True, exist_ok=True)
    public.write_bytes(gzip.compress(private.read_bytes(), mtime=0))


def baseline():
    items = {}
    for name, root in [('V1', OLD), ('V2', V2), ('V3', V3)]:
        m = json.loads((root / 'outputs/manifest.json').read_text())
        assert all(sha(root / f['path']) == f['sha256'] for f in m['files']), name
        items[name] = dict(root=str(root), manifest_sha256=sha(root / 'outputs/manifest.json'), files=m['files'])
    js('audits/predecessors', items)
    return items
