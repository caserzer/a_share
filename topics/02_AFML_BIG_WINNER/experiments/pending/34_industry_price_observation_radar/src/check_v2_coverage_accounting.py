"""Synthetic counterexamples for semantic regressions; no method performance."""
import copy
import json
from pathlib import Path
from v2_coverage_accounting import evaluate


def run():
    p = dict(id='p1', industry='SW2021:example', status='QUALIFIED',
             useful_start=10, timely_end=20, useful_end=40)
    def event(i, day, kind='NEW', evidence='SUPPORTED'):
        return dict(id=i, day=day, kind=kind, evidence=evidence,
                    industry=p['industry'], evaluation_complete=True)
    def assess(events, processes=None):
        processes = processes or [p]
        edges = [dict(event=e['id'], process=q['id'], relation='ALIGNED')
                 for e in events for q in processes]
        return evaluate(processes, events, edges)
    checks = []
    e = event('early', 12, evidence='UNSUPPORTED')
    u = event('update', 16, 'UPDATE')
    a = assess([e, u])
    assert a['covered']['p1']['event'] == 'update'
    assert [r['status'] for r in a['events']] == ['UNSUPPORTED', 'TIMELY']
    checks.append('False NEW retained; later UPDATE can cover without NEW success')
    a = assess([event('a', 12), event('b', 15)])
    assert len(a['covered']) == 1 and a['events'][1]['status'] == 'REPEAT'
    checks.append('Repeat does not add success')
    a = assess([event('late', 30)])
    assert a['covered']['p1']['timing'] == 'LATE'
    checks.append('Late useful coverage is not timely')
    assert assess([])['missed'] == ['p1']
    checks.append('Pool presence without event cannot cover')
    q = dict(p, status='UNKNOWN')
    assert assess([event('a', 12)], [q])['qualified_processes'] == 0
    checks.append('Unknown process is not a failed qualified process')
    a = assess([event('a', 12, evidence='UNKNOWN')])
    assert a['coverage_unknown'] == ['p1'] and not a['missed']
    assert a['coverage_lower'] == 0 and a['coverage_upper'] == 1
    checks.append('Unknown coverage retained in full denominator with bounds')
    original = event('a', 12)
    changed = copy.deepcopy(original)
    changed.update(post_return=-0.9, post_maturity='IMMATURE')
    assert assess([original]) == assess([changed])
    checks.append('Post-alert outcome cannot alter qualified process coverage')
    a = assess([event('a', 12)], [p, dict(p, id='p2')])
    assert not a['covered'] and a['events'][0]['status'] == 'UNKNOWN'
    checks.append('Ambiguous overlap cannot select hindsight-best match')
    return checks


if __name__ == '__main__':
    checks = run()
    out = Path(__file__).resolve().parents[1] / 'outputs/r00_v2_accounting'
    out.mkdir(parents=True, exist_ok=True)
    (out / 'semantic_checks.json').write_text(json.dumps({
        'scope': 'Synthetic accounting checks only; not validation of labels or methods',
        'passed': len(checks), 'checks': checks}, ensure_ascii=False, indent=2) + '\n')
    print(f'{len(checks)} semantic counterexample checks passed')
