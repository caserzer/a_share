"""Collect legacy industry intervals and exact broad-index prices using existing access."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import time
import pandas as pd
import requests
from dotenv import dotenv_values

EP = Path(__file__).resolve().parents[1]
OLD = EP.parents[1]
REPO = OLD.parents[4]
CACHE = Path.home() / '.cache/a_share/ep32/extension_v2/sources'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    CACHE.mkdir(parents=True, exist_ok=True)
    token = dotenv_values(REPO / 'topics/01_askhare_qlib/.env').get('TUSHARE_TOKEN')
    if not token:
        raise RuntimeError('Existing data permission unavailable')
    session = requests.Session()
    receipts = []

    def query(api, params, name):
        path = CACHE / (name + '.json')
        receipt = CACHE / (name + '.receipt.json')
        if path.exists() and receipt.exists():
            rec = json.loads(receipt.read_text())
            assert rec['params'] == params and sha(path) == rec['sha256']
            data = json.loads(path.read_text())
        else:
            response = session.post('https://api.tushare.pro', json=dict(
                api_name=api, token=token, params=params, fields=''), timeout=(10, 45))
            response.raise_for_status()
            path.write_bytes(response.content)
            data = response.json()
            rec = dict(api=api, params=params, path=str(path), sha256=sha(path),
                       bytes=path.stat().st_size, observed_at=datetime.now(timezone.utc).isoformat(),
                       provider_code=data.get('code'), tls_verified=True, token_in_artifact=False)
            receipt.write_text(json.dumps(rec, indent=2) + '\n')
            time.sleep(.36)
        receipts.append(rec)
        if data.get('code') != 0:
            raise RuntimeError(f'{api}: provider code {data.get("code")}')
        f = pd.DataFrame(data['data']['items'], columns=data['data']['fields'])
        return f

    catalogs = []
    for level in ['L2', 'L3']:
        f = query('index_classify', dict(level=level, src='SW2014'), level + '_SW2014')
        catalogs.append(f)
    catalog = pd.concat(catalogs, ignore_index=True)
    catalog.to_parquet(CACHE / 'legacy_catalog.parquet', index=False)
    frames = []
    page_audits = []
    for flag in ['Y']:
        seen = set()
        for offset in range(0, 200000, 2000):
            params = dict(is_new=flag, limit=2000, offset=offset)
            f = query('index_member', params, f'members_{flag}_{offset:06d}')
            keys = set(map(tuple, f.fillna('').to_numpy()))
            if keys & seen:
                raise RuntimeError('Unstable pagination: duplicate membership intervals')
            seen |= keys
            page_audits.append(dict(is_new=flag, offset=offset, rows=len(f)))
            frames.append(f)
            if offset % 10000 == 0:
                print('Legacy source', flag, 'offset', offset, 'rows', len(f), flush=True)
            if len(f) < 2000:
                break
        else:
            raise RuntimeError('Membership pagination did not terminate')
    # The unfiltered removed-member table exceeds the provider's offset ceiling.
    # Partition by the exact legacy index universe rather than accept a partial bulk.
    for i, code in enumerate(sorted(catalog.index_code.unique())):
        for offset in range(0, 100000, 2000):
            params = dict(index_code=code, is_new='N', limit=2000, offset=offset)
            f = query('index_member', params, f'target_{code}_N_{offset:06d}')
            frames.append(f)
            page_audits.append(dict(index_code=code, is_new='N', offset=offset, rows=len(f)))
            if len(f) < 2000:
                break
        else:
            raise RuntimeError('Per-index pagination did not terminate')
        if (i + 1) % 40 == 0:
            print('Legacy removed-member indexes', i + 1, '/', catalog.index_code.nunique(), flush=True)
    all_members = pd.concat(frames, ignore_index=True)
    legacy = all_members.merge(catalog[['index_code', 'industry_name', 'level']], on='index_code', how='inner')
    legacy.to_parquet(CACHE / 'legacy_members.parquet', index=False)
    # Independent per-index spot checks detect a falsely short aggregate response.
    spots = []
    for code in ['801732.SI', '801083.SI', '851911.SI']:
        for flag in ['Y', 'N']:
            f = query('index_member', dict(index_code=code, is_new=flag), 'spot_' + code + '_' + flag)
            a = set(map(tuple, f.fillna('').to_numpy()))
            b = set(map(tuple, all_members[all_members.index_code.eq(code) & all_members.is_new.eq(flag)].fillna('').to_numpy()))
            if a != b:
                raise RuntimeError('Bulk/per-index mismatch: ' + code)
            spots.append(dict(index_code=code, is_new=flag, rows=len(f), matched=True))
    benchmarks = []
    for code, expected_name in [('000300.SH', '沪深300'), ('000985.CSI', '中证全指')]:
        identity = query('index_basic', dict(ts_code=code), 'identity_' + code)
        if len(identity) != 1 or identity.iloc[0].ts_code != code or identity.iloc[0]['name'] != expected_name:
            raise RuntimeError('Index identity mismatch: ' + code)
        f = query('index_daily', dict(ts_code=code, start_date='20170101', end_date='20261021'), code)
        if len(f) < 2000 or len(f) >= 8000 or f.trade_date.duplicated().any():
            raise RuntimeError('Incomplete or duplicate index response')
        if not f.ts_code.eq(code).all() or not f[['open', 'close']].gt(0).all().all():
            raise RuntimeError('Invalid index identity or prices')
        f['date'] = pd.to_datetime(f.trade_date)
        f = f.sort_values('date')
        if f.date.min() > pd.Timestamp('2017-01-03') or f.date.max() < pd.Timestamp('2026-10-21'):
            raise RuntimeError('Index dates do not cover the required window')
        f.to_parquet(CACHE / (code + '.parquet'), index=False)
        benchmarks.append(dict(code=code, name=expected_name, rows=len(f), start=str(f.date.min().date()),
                               end=str(f.date.max().date()), sha256=sha(CACHE / (code + '.parquet'))))
    result = dict(status='PASS', quality='Historical-proxy', receipts=receipts,
                  legacy_catalog_rows=len(catalog), legacy_membership_rows=len(legacy),
                  legacy_members_sha256=sha(CACHE / 'legacy_members.parquet'),
                  catalog_sha256=sha(CACHE / 'legacy_catalog.parquet'),
                  bulk_rows=len(all_members), pagination=page_audits, spot_checks=spots,
                  benchmarks=benchmarks, first_vintage_attested=False)
    rejected = CACHE / 'members_N_102000.json'
    if rejected.exists():
        problem = json.loads(rejected.read_text())
        result['superseded_bulk_attempt'] = dict(path=str(rejected), sha256=sha(rejected),
            provider_code=problem.get('code'), provider_message=problem.get('msg'),
            recovery='all removed records partitioned by every legacy catalog index; partial bulk not used')
    (CACHE / 'manifest.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    dest = EP / 'outputs/audits'
    dest.mkdir(parents=True, exist_ok=True)
    (dest / 'acquisition.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print('V2 sources ready:', len(legacy), 'legacy interval rows;', len(all_members), 'bulk rows', flush=True)


if __name__ == '__main__':
    main()
