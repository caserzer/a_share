"""Independent relational verification of the bounded history lookup."""
import pandas as pd
from common import ROOT, Path, json, sha, js


def run():
    out = ROOT/'outputs/r177'
    receipt = json.loads((out/'receipt.json').read_text())
    for p, digest in receipt['reads'].items():
        assert sha(p) == digest
    gaps = pd.read_parquet(ROOT/'outputs/r176/stock_date_gaps.parquet').query('absent_date')
    aliases = json.loads((ROOT/'outputs/r176/observed_aliases.json').read_text())
    mapping = pd.DataFrame([(sid, code) for sid in gaps.security_id.unique() for code in aliases[sid]], columns=['security_id', 'instrument'])
    sources = json.loads((out/'sources.json').read_text())
    assert set(map(tuple, mapping.values)) == {(s['security_id'], s['instrument']) for s in sources}
    records, available = [], {}
    for s in sources:
        p = Path(s['path']); rp = Path(str(p)+'.receipt.json')
        assert p.exists() == s['present'] and rp.exists() == s['receipt_present']
        if p.exists() and rp.exists():
            df = pd.read_parquet(p, columns=['date'])
            df['security_id'] = s['security_id']
            records.append(df)
            available[s['security_id']] = available.get(s['security_id'], 0)+1
    history = pd.concat(records).drop_duplicates(['security_id', 'date'])
    history['expected_match'] = True
    expected = gaps.merge(history, on=['security_id', 'date'], how='left')
    actual = pd.read_parquet(out/'date_lookup.parquet')
    joined = expected.merge(actual, on=['security_id', 'date'], validate='one_to_one', suffixes=('_expected','_actual'))
    assert len(joined) == len(gaps) == len(actual)
    assert (joined.expected_match.notna() == joined.raw_date_match).all()
    assert (joined.security_id.map(available).fillna(0) == joined.available_alias_archives).all()
    for col in ['position', 'after_delist_proxy']:
        assert joined[col+'_expected'].equals(joined[col+'_actual'])
    js(out/'verification.json', dict(status='PASS', stock_dates=len(joined), archive_sources=len(records), matched_stock_dates=int(joined.expected_match.notna().sum()), source_hashes_checked=len(receipt['reads']), prices_repaired=0))
    print('PASS independent relational lookup', len(joined))


if __name__ == '__main__':
    run()
