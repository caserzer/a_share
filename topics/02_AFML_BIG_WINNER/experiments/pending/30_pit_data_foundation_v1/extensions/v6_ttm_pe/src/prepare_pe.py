"""Freeze predecessors and copy hash-verified identity/calendar dependencies."""
import json
import shutil
from pe_common import EP, EXT, CACHE, OUT, V5, sha, write_json, utc_now

BUILD = CACHE / 'building'
DEPENDENCIES = {
    'securities.parquet': 'inputs/normalized/securities.parquet',
    'continuous_intervals.parquet': 'inputs/normalized/code_intervals.parquet',
    'bse_intervals.parquet': 'inputs/inputs/baseline/normalized/code_intervals.parquet',
    'calendar.parquet': 'inputs/inputs/baseline/normalized/calendar.parquet',
}

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    if not (OUT/'predecessors.json').exists():
        files = {}
        ep32 = EP.parent/'32_industry_rotation_cycle_observation'
        for root in [EP, ep32]:
            for p in root.rglob('*'):
                if not p.is_file() or EXT in p.parents or '__pycache__' in p.parts or '.pytest_cache' in p.parts:
                    continue
                # Private caches are not part of these public research releases.
                if 'local_cache' in p.parts:
                    continue
                files[str(p.resolve())] = sha(p)
        write_json(OUT/'predecessors.json',files)
    manifest = {r['relative_path']:r['sha256'] for r in json.loads((V5/'FULL_MANIFEST.json').read_text())}
    complete = json.loads((V5/'COMPLETE.json').read_text())
    assert sha(V5/'FULL_MANIFEST.json') == complete['full_manifest_sha256']
    (BUILD/'inputs').mkdir(parents=True,exist_ok=True)
    records = []
    for name, rel in DEPENDENCIES.items():
        assert sha(V5/rel) == manifest[rel]
        target = BUILD/'inputs'/name
        if target.exists():
            assert sha(target) == manifest[rel]
        else:
            shutil.copyfile(V5/rel,target)
        records.append(dict(source=str(V5/rel),target=name,sha256=manifest[rel]))
    write_json(OUT/'input_receipt.json', dict(at=utc_now(),inputs=records,
        primary_provider='eastmoney',secondary_provider='baostock',
        source_switching_allowed=False,strict_pit='BLOCKED_DATA',
        source_choice_reason='Broad historical coverage; fixed before any PE outcome analysis'))
    print('Prepared',len(records),'verified dependencies',flush=True)

if __name__ == '__main__':
    main()
