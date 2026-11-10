"""Additive TTM PE extension; never write to a previous D2 release."""
import json
import sys
from pathlib import Path

EXT = Path(__file__).resolve().parents[1]
EP = EXT.parents[1]
sys.path.append(str(EP / 'src'))
from archive import sha, write_json, utc_now, archive_bytes

CACHE = Path.home() / '.cache/a_share/ep30_d2/ttm_pe_v6'
OLD = Path.home() / '.cache/a_share/ep30_d2/backfill_v2'
V5 = Path(json.loads((EP / 'outputs/pit_v5/release.json').read_text())['path'])
OUT = EXT / 'outputs'

def verified(path):
    receipt = path.with_suffix(path.suffix + '.receipt.json')
    if not path.exists() or not receipt.exists():
        return False
    if sha(path) != json.loads(receipt.read_text())['parquet_sha256']:
        raise ValueError(f'Acquired partition changed: {path}')
    return True

def daily_path(day):
    for root in (CACHE, OLD):
        p = root / f'acquired/daily/{day}.parquet'
        if verified(p):
            return p
    return None
