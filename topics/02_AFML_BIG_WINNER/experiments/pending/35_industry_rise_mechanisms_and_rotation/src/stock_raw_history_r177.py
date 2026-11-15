"""Exact bounded lookup of R176 gaps in existing per-security histories."""
import pandas as pd
from common import ROOT, Path, json, sha, js


def run():
    out = ROOT / 'outputs/r177'
    gp = ROOT / 'outputs/r176/stock_date_gaps.parquet'
    ap = ROOT / 'outputs/r176/observed_aliases.json'
    gaps = pd.read_parquet(gp).query('absent_date')
    aliases = json.loads(ap.read_text())
    base = Path('/home/xiaolv/.cache/a_share/ep30_d2/backfill_v2/acquired/sina')
    reads = {str(p): sha(p) for p in [gp, ap, Path(__file__), ROOT/'protocols/r177.json']}
    sources, rows = [], []
    for sid, group in gaps.groupby('security_id'):
        covered = set()
        available = 0
        for code in aliases[sid]:
            p = base / f'{code}.parquet'
            rp = Path(str(p) + '.receipt.json')
            source = dict(security_id=sid, instrument=code, path=str(p), present=p.exists(), receipt_present=rp.exists())
            if p.exists() and rp.exists():
                rec = json.loads(rp.read_text())
                raw = Path(rec['archive_path'])
                assert sha(p) == rec['parquet_sha256'] and sha(raw) == rec['sha256']
                df = pd.read_parquet(p)
                assert len(df) == rec['rows'] and df.date.is_unique
                assert set(df.instrument.dropna()) == {code}
                assert set(df.source_sha256.dropna()) == {rec['sha256']}
                available += 1
                dates = set(pd.to_datetime(df.date))
                matches = set(group.date) & dates
                covered |= matches
                source.update(rows=len(df), matches=len(matches), first_date=str(df.date.min()), last_date=str(df.date.max()), historical_known_at=rec.get('historical_known_at'), observed_at=rec.get('source_observed_at'))
                for q in [p, rp, raw]:
                    reads[str(q)] = sha(q)
            sources.append(source)
        for item in group.itertuples():
            rows.append(dict(security_id=sid, date=item.date, available_alias_archives=available, raw_date_match=item.date in covered, position=item.position, after_delist_proxy=item.after_delist_proxy))
    result = pd.DataFrame(rows)
    assert len(result) == len(gaps) and not result.duplicated(['security_id', 'date']).any()
    result.to_parquet(out/'date_lookup.parquet', index=False)
    js(out/'sources.json', sources)
    js(out/'receipt.json', dict(reads=reads))
    summary = dict(status='PASS', stock_dates=len(result), securities=result.security_id.nunique(), alias_sources=len(sources), present_sources=sum(s['present'] and s['receipt_present'] for s in sources), matched_stock_dates=int(result.raw_date_match.sum()), unmatched_with_archive=int((~result.raw_date_match & result.available_alias_archives.gt(0)).sum()), dates_without_archive=int(result.available_alias_archives.eq(0).sum()), prices_repaired=0, quality='Historical-proxy')
    js(out/'summary.json', summary)
    print(summary)


if __name__ == '__main__':
    run()
