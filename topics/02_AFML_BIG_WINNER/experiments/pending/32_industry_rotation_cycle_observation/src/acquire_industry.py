"""Read existing Tushare permissions over TLS; retain raw historical membership.

No token is written to an artifact or command line. Both current and removed
members are queried. Effective intervals remain retrospective proxies.
"""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import time

import pandas as pd
import requests
from dotenv import dotenv_values

EP = Path(__file__).resolve().parents[1]
REPO = EP.parents[4]
CACHE = Path.home() / '.cache/a_share/ep32/industry_v1'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    CACHE.mkdir(parents=True, exist_ok=True)
    token = dotenv_values(REPO / 'topics/01_askhare_qlib/.env').get('TUSHARE_TOKEN')
    if not token:
        raise RuntimeError('Existing Tushare permission unavailable')
    session = requests.Session()
    receipts = []

    def query(api, params, name):
        target = CACHE / (name + '.json')
        receipt = CACHE / (name + '.receipt.json')
        if target.exists() and receipt.exists():
            record = json.loads(receipt.read_text())
            assert sha(target) == record['sha256']
            assert record['params'] == params
            data = json.loads(target.read_text())
        else:
            response = session.post('https://api.tushare.pro', json={
                'api_name': api, 'params': params, 'token': token, 'fields': ''},
                timeout=(10, 45))
            response.raise_for_status()
            target.write_bytes(response.content)
            data = response.json()
            record = dict(api=api, params=params, observed_at=datetime.now(timezone.utc).isoformat(),
                          url='https://api.tushare.pro', tls_verified=True,
                          path=str(target), sha256=sha(target), bytes=target.stat().st_size,
                          provider_code=data.get('code'), token_in_artifact=False)
            receipt.write_text(json.dumps(record, indent=2) + '\n')
            time.sleep(.36)
        receipts.append(record)
        if data.get('code') != 0:
            raise RuntimeError(f'{api} rejected with provider code {data.get("code")}')
        body = data['data']
        frame = pd.DataFrame(body['items'], columns=body['fields'])
        return frame

    catalog = {}
    for level in ['L1', 'L2', 'L3']:
        catalog[level] = query('index_classify', {'level': level, 'src': 'SW2021'}, level)
        catalog[level].to_parquet(CACHE / (level + '.parquet'), index=False)
    frames = []
    for i, row in enumerate(catalog['L1'].itertuples()):
        for is_new in ['Y', 'N']:
            params = dict(l1_code=row.index_code, is_new=is_new)
            frame = query('index_member_all', params, row.index_code + '_' + is_new)
            # Do not accept a truncated response. Split by L2 if needed.
            if len(frame) >= 2000:
                children = catalog['L2'][catalog['L2'].parent_code.eq(row.industry_code)]
                if children.empty:
                    raise RuntimeError('Cannot partition truncated L1 result')
                for child in children.itertuples():
                    sub = query('index_member_all', dict(l2_code=child.index_code, is_new=is_new),
                                child.index_code + '_' + is_new)
                    if len(sub) >= 2000:
                        raise RuntimeError('Truncated L2 result requires L3 partition')
                    frames.append(sub)
            else:
                frames.append(frame)
        if (i + 1) % 5 == 0:
            print('Industry source', i + 1, '/', len(catalog['L1']), flush=True)
    members = pd.concat(frames, ignore_index=True).drop_duplicates()
    members.to_parquet(CACHE / 'members.parquet', index=False)
    result = dict(status='PASS', observed_at=datetime.now(timezone.utc).isoformat(),
                  membership_rows=len(members), stocks=members.ts_code.nunique(),
                  levels={k: len(v) for k, v in catalog.items()},
                  current_and_removed=True, raw_receipts=receipts,
                  membership_path=str(CACHE / 'members.parquet'),
                  membership_sha256=sha(CACHE / 'members.parquet'),
                  first_vintage_attested=False, quality='Historical-proxy')
    (CACHE / 'manifest.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    dest = EP / 'outputs/audits'
    dest.mkdir(parents=True, exist_ok=True)
    (dest / 'industry_acquisition.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print('Source acquired:', len(members), 'rows;', members.ts_code.nunique(), 'stocks', flush=True)


if __name__ == '__main__':
    main()
