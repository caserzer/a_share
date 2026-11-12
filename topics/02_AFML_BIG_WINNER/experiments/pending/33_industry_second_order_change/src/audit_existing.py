"""Offline, read-only source audit; writes only EP33 evidence, not source data."""
import hashlib
import json
import sys
from pathlib import Path

import pandas as pd

EP = Path(__file__).resolve().parents[1]
D2 = EP.parent / '30_pit_data_foundation_v1'
CACHE = Path('/home/xiaolv/.cache/a_share')


def sha(p):
    h = hashlib.sha256()
    with p.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def main():
    evidence = []

    def record(p, expected=None):
        digest = sha(p)
        if expected is not None and digest != expected:
            raise ValueError(f'Sealed input changed: {p}')
        evidence.append({'path': str(p), 'sha256': digest,
                         'sealed_hash_verified': expected is not None})

    pointer = D2 / 'outputs/pit_v4/release.json'
    record(pointer)
    release = json.loads(pointer.read_text())
    root = Path(release['path'])
    complete = json.loads((root / 'COMPLETE.json').read_text())
    record(root / 'COMPLETE.json')
    manifest = root / 'FULL_MANIFEST.json'
    record(manifest, complete['full_manifest_sha256'])
    sealed = {r['relative_path']: r['sha256'] for r in json.loads(manifest.read_text())}

    def read(name):
        p = root / name
        record(p, sealed[name])
        return pd.read_parquet(p)

    finance = pd.concat([read('normalized/financial_reviewed_facts.parquet'),
                         read('inputs/normalized/financial_reviewed_facts.parquet')],
                        ignore_index=True).drop_duplicates('record_id')
    finance['metric'] = finance.field.str.rsplit(':', n=1).str[0]
    finance['period'] = finance.field.str.rsplit(':', n=1).str[1]
    periods = finance.groupby(['security_id', 'metric']).period.nunique()
    chains = read('normalized/financial_version_chains.parquet')
    member_path = CACHE / 'ep32/industry_v1/members.parquet'
    record(member_path)
    members = pd.read_parquet(member_path)
    sys.path.insert(0, str(D2 / 'src'))
    from v4_dataset import D2V4Dataset
    dataset = D2V4Dataset(root)
    strict = dataset.get_asof('SH600000', 'close', '2020-12-31 15:00')
    proxy = dataset.get_asof('SH600000', 'close', '2020-12-31 15:00',
                             quality_tier='Historical-proxy')
    for p in [D2 / 'src/v4_dataset.py', D2 / 'src/pit.py',
              D2 / 'outputs/pit_v4/domain_quality_gates.csv',
              D2 / 'outputs/pit_v5/release.json',
              D2 / 'extensions/v6_ttm_pe/reports/ttm_pe_coverage.md',
              EP / 'GOAL.md', EP / 'rounds/r00_plan.md', Path(__file__)]:
        record(p)
    result = {
        'round_id': 'r00', 'scope': 'v4 sealed reviewed finance and reader; EP32 industry_v1 members',
        'release_path': str(root),
        'strict_quote': {'value': strict.value, 'status': strict.status, 'reason': strict.reason},
        'proxy_quote': {'value': proxy.value, 'status': proxy.status, 'reason': proxy.reason},
        'membership': {'rows': len(members), 'columns': list(members.columns),
                       'has_known_at': 'known_at' in members,
                       'note': 'in/out effective dates do not establish vendor revision availability'},
        'reviewed_finance': {'records': len(finance), 'securities': finance.security_id.nunique(),
                             'quality_counts': finance.quality_tier.value_counts().to_dict(),
                             'missing_known_at': int(finance.known_at.isna().sum()),
                             'max_distinct_periods_per_security_metric': int(periods.max()),
                             'series_with_at_least_three_periods': int((periods >= 3).sum()),
                             'period_count_distribution': periods.value_counts().sort_index().to_dict()},
        'report_index': {'rows': len(chains), 'numeric_fields_unattested_rows':
                         int(chains.source_index_does_not_certify_numeric_fields.sum())},
        'decision': 'STRICT_PIT_GATE_FAILED_PROXY_RESEARCH_AUTHORIZED',
        'limits': 'Not a census of every archived PDF or older release; no return hypothesis tested.',
        'evidence': evidence,
    }
    target = EP / 'outputs/audits/r00_existing_data.json'
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2, default=str) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'evidence'}, ensure_ascii=False, indent=2, default=str))


if __name__ == '__main__':
    main()
