"""Verify exact gap lookup directly against archived JSON dates."""
import pandas as pd
from common import ROOT, Path, json, sha, js


def run():
    out = ROOT/'outputs/r178'
    receipt = json.loads((out/'receipt.json').read_text())
    for p,h in receipt['reads'].items(): assert sha(p) == h
    g = pd.read_parquet(ROOT/'outputs/r176/stock_date_gaps.parquet').query('absent_date')
    aliases = json.loads((ROOT/'outputs/r176/observed_aliases.json').read_text())
    sources = json.loads((out/'sources.json').read_text())
    assert {(s['security_id'],s['instrument']) for s in sources} == {(sid,c) for sid in g.security_id.unique() for c in aliases[sid]}
    pairs,counts = set(),{}
    for s in sources:
        p = Path(s['path']); rp = Path(str(p)+'.receipt.json')
        assert p.exists() == s['present'] and rp.exists() == s['receipt_present']
        if p.exists() and rp.exists():
            rec = json.loads(rp.read_text()); data = json.loads(Path(rec['archive_path']).read_bytes())
            pairs.update((s['security_id'],pd.Timestamp(str(row[0]))) for row in data['kline'])
            counts[s['security_id']] = counts.get(s['security_id'],0)+1
    actual = pd.read_parquet(out/'date_lookup.parquet').set_index(['security_id','date'])
    assert set(actual.index) == set(zip(g.security_id,g.date)) and actual.index.is_unique
    for key,row in actual.iterrows():
        assert bool(row.raw_date_match) == (key in pairs)
        assert row.available_alias_archives == counts.get(key[0],0)
    candidates = pd.read_parquet(out/'candidate_records.parquet')
    assert set(zip(candidates.security_id,candidates.date)) == set(actual[actual.raw_date_match].index)
    rpc = Path('/home/xiaolv/.cache/a_share/ep30_d2/pit_v3/acquired/rpc')
    codes = {p.stem for p in rpc.glob('*.parquet')}
    affected = {c for sid in g.security_id.unique() for c in aliases[sid]}
    assert not codes & affected
    js(out/'verification.json', dict(status='PASS',stock_dates=len(actual),raw_source_keys=len(pairs),matches=int(actual.raw_date_match.sum()),rpc_codes=sorted(codes),rpc_affected_codes=[],prices_repaired=0))
    print('PASS archived JSON date verification',len(actual))


if __name__ == '__main__': run()
