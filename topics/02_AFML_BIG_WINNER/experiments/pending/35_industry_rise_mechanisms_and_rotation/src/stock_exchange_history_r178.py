"""Raw-response verified local exchange-history lookup; no imputation."""
import numpy as np
import pandas as pd
from common import ROOT, Path, json, sha, js


def run():
    out = ROOT/'outputs/r178'
    gp = ROOT/'outputs/r176/stock_date_gaps.parquet'
    ap = ROOT/'outputs/r176/observed_aliases.json'
    gaps = pd.read_parquet(gp).query('absent_date')
    aliases = json.loads(ap.read_text())
    base = Path('/home/xiaolv/.cache/a_share/ep30_d2/pit_v3/acquired/exchange_quotes')
    reads = {str(p): sha(p) for p in [gp, ap, Path(__file__), ROOT/'protocols/r178.json']}
    sources, results, candidates = [], [], []
    for sid, g in gaps.groupby('security_id'):
        matched, available = set(), 0
        for code in aliases[sid]:
            p = base/f'{code}.parquet'; rp = Path(str(p)+'.receipt.json')
            s = dict(security_id=sid, instrument=code, path=str(p), present=p.exists(), receipt_present=rp.exists())
            if p.exists() and rp.exists():
                rec = json.loads(rp.read_text()); raw = Path(rec['archive_path'])
                assert sha(p) == rec['parquet_sha256'] and sha(raw) == rec['sha256']
                obj = json.loads(raw.read_bytes()); assert obj['code'] == code[2:]
                df = pd.read_parquet(p)
                rebuilt = pd.DataFrame(obj['kline'], columns=['date','open','high','low','close','volume','money'])
                rebuilt['date'] = pd.to_datetime(rebuilt.date.astype(str), format='%Y%m%d')
                pd.testing.assert_frame_equal(df.reset_index(drop=True), rebuilt, check_dtype=False)
                assert df.date.is_unique and len(df) == rec['rows']
                hits = df[df.date.isin(g.date)].copy()
                hits['security_id'] = sid; hits['instrument'] = code
                candidates.append(hits); matched |= set(hits.date); available += 1
                s.update(rows=len(df), matches=len(hits), observed_at=rec['source_observed_at'], historical_first_version_certified=rec['historical_first_version_certified'])
                for q in [p,rp,raw]: reads[str(q)] = sha(q)
            sources.append(s)
        for date in g.date:
            results.append(dict(security_id=sid,date=date,available_alias_archives=available,raw_date_match=date in matched))
    df = pd.DataFrame(results); df.to_parquet(out/'date_lookup.parquet',index=False)
    pd.concat(candidates,ignore_index=True).to_parquet(out/'candidate_records.parquet',index=False)
    js(out/'sources.json', sources);js(out/'receipt.json',dict(reads=reads))
    summary = dict(status='PASS',stock_dates=len(df),securities=gaps.security_id.nunique(),alias_sources=len(sources),verified_sources=sum(s['present'] and s['receipt_present'] for s in sources),decoded_rows=sum(s.get('rows',0) for s in sources),matched_stock_dates=int(df.raw_date_match.sum()),unmatched_with_archive=int((~df.raw_date_match & df.available_alias_archives.gt(0)).sum()),dates_without_archive=int(df.available_alias_archives.eq(0).sum()),prices_repaired=0)
    js(out/'summary.json',summary); print(summary)


if __name__ == '__main__': run()
