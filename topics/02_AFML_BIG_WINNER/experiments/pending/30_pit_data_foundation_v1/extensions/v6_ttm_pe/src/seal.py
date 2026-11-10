"""Hash-verify, offline-check and seal an immutable, self-contained PE release."""
import json
from pathlib import Path
from unittest.mock import patch
import numpy as np
import pandas as pd
from pe_common import CACHE, OUT, sha, write_json, utc_now
from prepare_pe import BUILD
from ttm_pe_dataset import D2TTMPEDataset

def validate(root):
    checks=[]
    def check(name,passed,**details):
        checks.append(dict(check=name,passed=bool(passed),**details))
        if not passed:
            write_json(OUT/'validation.json',dict(status='FAIL',checks=checks))
            raise AssertionError(name)
    acq=json.loads((OUT/'eastmoney_acquisition.json').read_text())
    check('all_months_attempted',acq['status']=='COMPLETE_WITH_PROVIDER_GAPS' and len(acq['progress'])==118)
    check('no_unresolved_primary_queries',all(x['status'] in ('ACQUIRED','NO_PROVIDER_DATA') for x in acq['progress']))
    prior=json.loads((OUT/'predecessors.json').read_text())
    check('prior_research_unchanged',all(Path(p).is_file() and sha(p)==digest for p,digest in prior.items()),files=len(prior))
    manifest=json.loads((root/'FULL_MANIFEST.json').read_text())
    check('release_all_hashes_match',all(sha(root/r['relative_path'])==r['sha256'] for r in manifest),files=len(manifest))
    totals={}
    for provider in ['eastmoney','baostock']:
        rows=0;valid=True;unmapped=0;conflicts=0
        for path in sorted((root/'normalized'/provider).glob('*.parquet')):
            f=pd.read_parquet(path)
            date=pd.Timestamp(path.stem)
            valid &= bool(f.date.eq(date).all() and f.known_at.isna().all())
            valid &= bool(f.quality_tier.eq('Historical-proxy').all() and f.earnings_vintage_status.eq('UNPROVEN').all())
            valid &= bool((f.source_observed_at <= f.ingested_at).all())
            mapped=f[f.security_id.notna()]
            valid &= not mapped.security_id.duplicated().any()
            expected=f.vendor_pe_ttm.where(f.vendor_pe_ttm.gt(0))
            valid &= bool(np.allclose(f.pe_ttm,expected,equal_nan=True))
            valid &= bool(f.provider.eq(provider).all())
            rows+=len(f);unmapped+=int(f.security_id.isna().sum());conflicts+=int(f.pe_status.eq('ALIAS_VALUE_CONFLICT').sum())
        totals[provider]=dict(rows=rows,unmapped=unmapped,alias_conflicts=conflicts)
        check(provider+'_date_identity_provenance_and_values',valid,**totals[provider])
    with patch('socket.socket',side_effect=AssertionError('Network prohibited during release replay')):
        d=D2TTMPEDataset(root)
        check('strict_query_denies_vendor_pe',d.get_asof('SH600000','pe_ttm','2024-06-28 15:00').value is None)
        r=d.get_asof('SH600000','pe_ttm','2024-06-28 15:00',quality_tier='Historical-proxy')
        check('historical_proxy_readable_offline',r.value is not None,pe=r.value)
        r=d.get_asof('SH600000','pe_ttm','2024-06-28 15:00',quality_tier='Historical-proxy',mode='archived')
        check('historical_acquisition_not_backdated',r.value is None)
        for date in ['2017-01-03','2021-01-04','2024-06-28','2026-10-21']:
            u=d.universe_asof(date+' 15:00',quality_tier='Historical-proxy')
            check('universe_'+date,not u.security_id.duplicated().any() and len(u)>3000,
                members=len(u),positive=int(u.pe_ttm.notna().sum()))
    daily=pd.read_csv(OUT/'universe_daily_coverage.csv.gz')
    check('all_sessions_audited',all(g.date.nunique()==2377 for _,g in daily.groupby('provider')))
    tests=json.loads((OUT/'test_receipt.json').read_text())
    check('semantic_regression_tests_pass',tests['exit_code']==0)
    write_json(OUT/'validation.json',dict(status='PASS',checks=checks,totals=totals,at=utc_now()))
    return checks

def main():
    if not BUILD.exists():
        raise RuntimeError('No unsealed build')
    files=[dict(relative_path=str(p.relative_to(BUILD)),sha256=sha(p),bytes=p.stat().st_size)
        for p in sorted(BUILD.rglob('*')) if p.is_file() and p.name not in ('FULL_MANIFEST.json','COMPLETE.json')]
    write_json(BUILD/'FULL_MANIFEST.json',files)
    release_id=sha(BUILD/'FULL_MANIFEST.json')
    write_json(BUILD/'COMPLETE.json',dict(full_manifest_sha256=release_id,
        identity_snapshot_observed_at=utc_now(),status='COMPLETE_WITH_COVERAGE_GAPS',
        primary_provider='eastmoney',strict_pit='BLOCKED_DATA',
        known_at_policy='UNKNOWN_VENDOR_EARNINGS_VINTAGE',sealed_at=utc_now()))
    checks=validate(BUILD)
    release=CACHE/'releases'/release_id
    release.parent.mkdir(parents=True,exist_ok=True)
    if release.exists():raise FileExistsError('Immutable release already exists')
    BUILD.rename(release)
    write_json(OUT/'release.json',dict(path=str(release),release_id=release_id,
        status='COMPLETE_WITH_COVERAGE_GAPS',strict_pit='BLOCKED_DATA',
        files=len(files),bytes=sum(r['bytes'] for r in files),validation_checks=len(checks)))
    print('Sealed',release,flush=True)

if __name__=='__main__':main()
