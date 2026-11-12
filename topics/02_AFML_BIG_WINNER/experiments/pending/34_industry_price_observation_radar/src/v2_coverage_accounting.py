"""Draft R00 accounting, not a price labeler or signal model.

Input edges must be independently adjudicated, without post-alert return tests.
Unknown edges remain unknown. No inferred edges from an industry's pool presence.
"""


def evaluate(processes, events, edges):
    ps = {p['id']: p for p in processes}
    es = {e['id']: e for e in events}
    if len(ps) != len(processes) or len(es) != len(events):
        raise ValueError('IDs must be unique')
    links = {e: [] for e in es}
    for edge in edges:
        p, e = ps[edge['process']], es[edge['event']]
        if p['industry'] != e['industry']:
            raise ValueError('Cross-industry edge')
        if edge['relation'] not in ('ALIGNED', 'UNKNOWN', 'UNRELATED'):
            raise ValueError('Invalid relation')
        links[e['id']].append(edge)
    covered, ledger = {}, []
    for e in sorted(events, key=lambda x: (x['day'], x['id'])):
        if e['kind'] not in ('NEW', 'UPDATE'):
            raise ValueError('Only NEW and UPDATE enter this accounting view')
        if e['evidence'] not in ('SUPPORTED', 'UNSUPPORTED', 'UNKNOWN'):
            raise ValueError('Invalid evidence state')
        candidates, uncertain = [], e['evidence'] == 'UNKNOWN'
        outside = False
        for edge in links[e['id']]:
            p = ps[edge['process']]
            if edge['relation'] == 'UNRELATED':
                continue
            if edge['relation'] == 'UNKNOWN' or p['status'] != 'QUALIFIED':
                uncertain = True
                continue
            if not p['useful_start'] <= e['day'] <= p['useful_end']:
                outside = True
                continue
            candidates.append(p)
        # A duplicate edge is a data error, not an extra opportunity.
        if len({p['id'] for p in candidates}) != len(candidates):
            raise ValueError('Duplicate edge')
        assigned = None
        if e['evidence'] == 'UNSUPPORTED':
            status = 'UNSUPPORTED'
        elif uncertain or len(candidates) > 1:
            # Do not select whichever overlapping process yields better results.
            status = 'UNKNOWN'
        elif candidates:
            p = candidates[0]
            assigned = p['id']
            if assigned in covered:
                status = 'REPEAT'
            else:
                status = 'TIMELY' if e['day'] <= p['timely_end'] else 'LATE'
                covered[assigned] = {'event': e['id'], 'source': e['kind'],
                                     'day': e['day'], 'timing': status}
        elif not e['evaluation_complete']:
            status = 'IMMATURE'
        else:
            status = 'OUTSIDE_USEFUL_WINDOW' if outside else 'NO_MATCH'
        ledger.append({'event': e['id'], 'kind': e['kind'], 'status': status,
                       'process': assigned})
    qualified = [p['id'] for p in processes if p['status'] == 'QUALIFIED']
    unknown_events = [es[r['event']] for r in ledger if r['status'] in ('UNKNOWN', 'IMMATURE')]
    unresolved = set()
    for e in unknown_events:
        for edge in links[e['id']]:
            p = ps[edge['process']]
            if (edge['relation'] != 'UNRELATED' and p['status'] == 'QUALIFIED'
                    and p['useful_start'] <= e['day'] <= p['useful_end']):
                unresolved.add(p['id'])
    unresolved -= covered.keys()
    missed = set(qualified) - covered.keys() - unresolved
    return {'qualified_processes': len(qualified), 'covered': covered,
            'coverage_unknown': sorted(unresolved), 'missed': sorted(missed),
            'coverage_lower': len(covered) / len(qualified) if qualified else None,
            'coverage_upper': (len(covered) + len(unresolved)) / len(qualified) if qualified else None,
            'processes_pending': [p['id'] for p in processes if p['status'] != 'QUALIFIED'],
            'events': ledger}
