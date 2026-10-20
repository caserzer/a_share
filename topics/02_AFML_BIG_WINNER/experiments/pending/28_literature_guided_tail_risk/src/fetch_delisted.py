"""Recover historical quote evidence without changing D0 or inventing settlement prices."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import argparse
import ast
import hashlib
import json
import requests
import pandas as pd
from functools import partial
from py_mini_racer import py_mini_racer
from akshare.stock.stock_zh_a_sina import hk_js_decode

EP = Path(__file__).resolve().parents[1]
EP27 = EP.parent / '27_hierarchical_tail_risk_attribution'
CACHE = EP / 'outputs/local_cache/recovered_prices'


def recover(stock, offline=False):
    symbol = stock.lower()
    records = []
    payloads = {}
    for kind, suffix in [('raw', 'hisdata_klc2/klc_kl.js'), ('factor', 'qfq.js')]:
        p = CACHE / f'{stock}_{kind}.body'
        if offline:
            payloads[kind] = p.read_text()
            continue
        url = f'https://finance.sina.com.cn/realstock/company/{symbol}/{suffix}'
        record = dict(instrument=stock, kind=kind, url=url, accessed_utc=datetime.now(timezone.utc).isoformat())
        try:
            r = requests.get(url, timeout=25, headers={'User-Agent': 'Mozilla/5.0'})
            p.write_bytes(r.content)
            record.update(status=r.status_code, bytes=len(r.content), sha256=hashlib.sha256(r.content).hexdigest(),
                          path=str(p.relative_to(EP)))
            if r.status_code == 200:
                payloads[kind] = r.text
        except Exception as exc:
            record['error'] = type(exc).__name__ + ': ' + str(exc)[:200]
        records.append(record)
    audit = dict(instrument=stock, status='unresolved')
    try:
        raw = payloads['raw'].split('=', 1)[1].split(';', 1)[0].strip().strip('"')
        engine = py_mini_racer.MiniRacer()
        engine.eval(hk_js_decode)
        frame = pd.DataFrame(engine.call('d', raw))
        frame['date'] = pd.to_datetime(frame.date, utc=True).dt.tz_localize(None).dt.normalize()
        frame = frame.sort_values('date')
        assert not frame.date.duplicated().any()
        frame = frame[(frame.date >= '2017-01-01') & (frame.date <= '2026-05-29')].copy()
        assert len(frame) and pd.to_numeric(frame.close).gt(0).all()
        frame.to_parquet(CACHE / f'{stock}_raw.parquet', index=False)
        data = ast.literal_eval(payloads['factor'].split('=', 1)[1].split('\n', 1)[0].strip().rstrip(';'))
        factor = pd.DataFrame(data['data']).rename(columns={'d': 'date', 'f': 'qfq_factor'})
        factor['date'] = pd.to_datetime(factor.date)
        factor['qfq_factor'] = pd.to_numeric(factor.qfq_factor)
        assert len(factor) and factor.qfq_factor.gt(0).all()
        factor = factor.sort_values('date')
        assert not factor.date.duplicated().any()
        merged = pd.merge_asof(frame, factor, on='date', direction='backward')
        assert merged.qfq_factor.notna().all()
        merged['qfq_close'] = pd.to_numeric(merged.close) / merged.qfq_factor
        merged.to_parquet(CACHE / f'{stock}_qfq.parquet', index=False)
        audit.update(status='quote_proxy_recovered', rows=len(merged),
                     first_date=str(merged.date.min().date()), last_date=str(merged.date.max().date()),
                     final_close=float(merged.qfq_close.iloc[-1]),
                     settlement_verified=False, original_vintage_verified=False)
    except Exception as exc:
        audit['error'] = type(exc).__name__ + ': ' + str(exc)[:200]
    return records, audit


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--all', action='store_true')
    parser.add_argument('--offline', action='store_true')
    args = parser.parse_args()
    CACHE.mkdir(parents=True, exist_ok=True)
    stocks = pd.read_csv(EP27 / 'outputs/listing_st_delisting_audit.csv')
    missing = stocks[stocks.is_delisted & stocks.source.eq('missing_price_file')]
    selected = missing.instrument.tolist() if args.all else missing.groupby('exchange').head(3).instrument.tolist() + ['SH600000', 'SH600519', 'SZ000001']
    done = {p.stem[:-4] for p in CACHE.glob('*_qfq.parquet')}
    selected = [s for s in selected if s not in done]
    with ThreadPoolExecutor(max_workers=3) as pool:
        for records, audit in pool.map(partial(recover, offline=args.offline), selected):
            with (EP / 'outputs/audits/delisted_source_attempts.jsonl').open('a') as f:
                for record in records:
                    f.write(json.dumps(record, ensure_ascii=False) + '\n')
            with (EP / 'outputs/audits/delisted_recovery.jsonl').open('a') as f:
                f.write(json.dumps(audit, ensure_ascii=False) + '\n')
            print(json.dumps(audit, ensure_ascii=False), flush=True)
