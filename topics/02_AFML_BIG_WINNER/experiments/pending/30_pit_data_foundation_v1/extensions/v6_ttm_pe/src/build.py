"""Normalize exact-day valuations and audit every frozen calendar/universe day."""
import argparse
import json
import shutil
from pathlib import Path
from collections import defaultdict
import pandas as pd
from pe_common import CACHE, OLD, OUT, sha, write_json, verified, daily_path, utc_now
from prepare_pe import BUILD
from pe_identity import Identity, normalize

def copy_checked(source, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        if sha(source)!=sha(target):
            raise ValueError('Changed immutable input: '+str(source))
    else:
        shutil.copyfile(source,target)

def preserve_source(path, provider):
    receipt_path = path.with_suffix(path.suffix+'.receipt.json')
    rec = json.loads(receipt_path.read_text())
    assert sha(path)==rec['parquet_sha256']
    copy_checked(path,BUILD/'sources'/provider/path.name)
    copy_checked(receipt_path,BUILD/'sources'/provider/receipt_path.name)
    for digest in rec['response_sha256']:
        candidates = [root/f'raw/sha256/{digest[:2]}/{digest}' for root in (CACHE,CACHE.parent,OLD)]
        raw = next((p for p in candidates if p.exists()),None)
        if raw is None or sha(raw)!=digest:
            raise ValueError('Missing or changed original response: '+digest)
        copy_checked(raw,BUILD/f'raw/sha256/{digest[:2]}/{digest}')
    return rec

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--allow-partial',action='store_true',help='For development only; seal still requires explicit audit status')
    args=parser.parse_args()
    status=json.loads((OUT/'eastmoney_acquisition.json').read_text())['status']
    if status=='RUNNING' and not args.allow_partial:
        raise RuntimeError('Acquisition is still active')
    identity=Identity(BUILD/'inputs')
    dates=pd.DatetimeIndex(pd.read_parquet(BUILD/'inputs/calendar.parquet').date)
    records=[]
    for provider in ['eastmoney','baostock']:
        if provider=='eastmoney':
            paths=sorted((CACHE/'acquired/eastmoney').glob('*.parquet'))
        else:
            paths=[p for d in dates if (p:=daily_path(str(d.date()))) is not None]
        for path in paths:
            if not verified(path):
                raise ValueError('Unverified source: '+str(path))
            rec=preserve_source(path,provider)
            source=pd.read_parquet(path)
            col='TRADE_DATE' if provider=='eastmoney' else 'date'
            source[col]=pd.to_datetime(source[col])
            for day,group in source.groupby(col,sort=True):
                if day not in dates:
                    raise ValueError('Source date outside frozen trading calendar: '+str(day))
                if provider=='baostock':
                    group=group.copy();group['date']=group.date.dt.strftime('%Y-%m-%d')
                f=normalize(group,str(day.date()),rec,identity,provider)
                target=BUILD/f'normalized/{provider}/{day.date()}.parquet'
                target.parent.mkdir(parents=True,exist_ok=True)
                f.to_parquet(target,index=False)
                records.append(dict(provider=provider,date=str(day.date()),rows=len(f),
                    source_rows_original=len(group),alias_rows_collapsed=int(f.alias_rows.sum()-len(f)),
                    alias_conflicts=int(f.pe_status.eq('ALIAS_VALUE_CONFLICT').sum()),
                    positive=int(f.pe_ttm.notna().sum()),negative=int(f.vendor_pe_ttm.lt(0).sum()),
                    zero=int(f.vendor_pe_ttm.eq(0).sum()),missing=int(f.vendor_pe_ttm.isna().sum()),
                    unmapped=int(f.security_id.isna().sum()),source=str(path),source_sha256=rec['parquet_sha256'],
                    normalized_sha256=sha(target)))
        print(provider,'normalized',len(paths),'source partitions',flush=True)
    pd.DataFrame(records).to_csv(OUT/'source_daily_coverage.csv',index=False)
    # Keep provider-empty receipts and the stopped-provider status, without converting them to rows.
    for p in sorted((CACHE/'acquired/eastmoney').glob('*.empty.json')):
        copy_checked(p,BUILD/'sources/eastmoney'/p.name)
        r=json.loads(p.read_text())['receipt'];raw=Path(r['archive_path'])
        assert sha(raw)==r['sha256']
        copy_checked(raw,BUILD/f"raw/sha256/{r['sha256'][:2]}/{r['sha256']}")
    if status=='COMPLETE_WITH_PROVIDER_GAPS':
        # Retain failed-request evidence as well as successful data, after all
        # append-only logs have stopped changing.
        for log in sorted((CACHE/'logs').rglob('*.jsonl')):
            copy_checked(log,BUILD/'audit/logs'/log.relative_to(CACHE/'logs'))
            for line in log.read_text().splitlines():
                rec=json.loads(line)
                if rec.get('archive_path') and rec.get('sha256'):
                    raw=Path(rec['archive_path']);assert sha(raw)==rec['sha256']
                    copy_checked(raw,BUILD/f"raw/sha256/{rec['sha256'][:2]}/{rec['sha256']}")
        copy_checked(CACHE/'BAOSTOCK_ACCESS_STOP.json',BUILD/'audit/BAOSTOCK_ACCESS_STOP.json')
    rows=[]
    for day in dates:
        u=identity.universe(day)[['security_id','exchange','board_bucket','is_delisted']]
        for provider in ['eastmoney','baostock']:
            path=BUILD/f'normalized/{provider}/{day.date()}.parquet'
            f=pd.read_parquet(path) if path.exists() else pd.DataFrame(columns=['security_id','vendor_pe_ttm','pe_ttm'])
            f=f[f.security_id.notna()]
            joined=u.merge(f[['security_id','vendor_pe_ttm','pe_ttm']],on='security_id',how='left',validate='one_to_one',indicator=True)
            for board,g in joined.groupby('board_bucket',dropna=False):
                rows.append(dict(provider=provider,date=str(day.date()),year=day.year,board=board,
                    universe=len(g),source_rows=int(g._merge.eq('both').sum()),
                    finite_pe=int(g.vendor_pe_ttm.notna().sum()),positive_pe=int(g.pe_ttm.notna().sum()),
                    negative_pe=int(g.vendor_pe_ttm.lt(0).sum()),zero_pe=int(g.vendor_pe_ttm.eq(0).sum())))
                rows[-1]['currently_delisted_members']=int(g.is_delisted.sum())
                rows[-1]['currently_delisted_with_pe']=int((g.is_delisted & g.vendor_pe_ttm.notna()).sum())
    coverage=pd.DataFrame(rows)
    coverage.to_csv(OUT/'universe_daily_coverage.csv.gz',index=False,compression={'method':'gzip','mtime':0})
    yearly=coverage.groupby(['provider','year'],as_index=False)[['universe','source_rows','finite_pe','positive_pe','negative_pe','zero_pe',
        'currently_delisted_members','currently_delisted_with_pe']].sum()
    yearly['finite_coverage']=yearly.finite_pe/yearly.universe
    yearly['positive_coverage']=yearly.positive_pe/yearly.universe
    yearly.to_csv(OUT/'universe_yearly_coverage.csv',index=False)
    board=coverage.groupby(['provider','board'],as_index=False)[['universe','source_rows','finite_pe','positive_pe']].sum()
    board['finite_coverage']=board.finite_pe/board.universe
    board.to_csv(OUT/'universe_board_coverage.csv',index=False)
    write_json(OUT/'build_receipt.json',dict(at=utc_now(),source_partitions=len(set(r['source'] for r in records)),
        normalized_partitions=len(records),rows=sum(r['rows'] for r in records),
        source_acquisition_status=status,strict_pit='BLOCKED_DATA',
        primary_provider='eastmoney',never_mix_providers=True))
    print(yearly.to_string(index=False),flush=True)

if __name__=='__main__':
    main()
