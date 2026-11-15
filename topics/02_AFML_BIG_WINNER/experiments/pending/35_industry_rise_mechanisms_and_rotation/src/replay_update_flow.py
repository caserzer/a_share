"""Exercise actual existing sources as historical replays, never prospective records."""
from common import *
import pandas as pd
from versioned_observations import capture,evaluate,verify_bundle

def run():
    store=ROOT/'data/update_store'
    inputs=[CACHE/'forecast_v5/daily_industries.parquet',ROOT/'data/l1_daily.parquet']
    market=CACHE/'forecast_v5/CSI_ALL.parquet';catalog=ROOT/'outputs/universe_current.csv'
    records=[]
    for asof in ['2026-06-30','2026-09-30']:
        bundle=capture(store,inputs,market,catalog,asof)
        manifest=verify_bundle(bundle);digest=sha(bundle/'manifest.json')
        assert capture(store,inputs,market,catalog,asof)==bundle
        assert sha(bundle/'manifest.json')==digest
        evaluation=evaluate(store,bundle,inputs,market,'2026-10-21')
        result=pd.read_parquet(evaluation/'outcomes.parquet')
        observed=pd.read_parquet(bundle/'observations.parquet')
        assert manifest['capture_kind']=='historical_replay'
        assert result.evaluation_kind.eq('historical_replay').all()
        assert not set(['return20','excess20','maturity20','y','entry_date'])&set(observed)
        records.append(dict(asof=asof,snapshot=str(bundle),evaluation=str(evaluation),snapshot_sha256=digest,
            rows=len(observed),ready=int(observed.price_ready.sum()),quarantined=manifest['quarantined_rows'],
            statuses=result.groupby(['horizon','status']).size().rename('rows').reset_index().to_dict('records')))
    js(ROOT/'outputs/r18/replay_receipt.json',dict(status='PASS',runs=records,prospective_records=0,
        code_sha256=sha(__file__),limitation='historical sources exercise engineering only; no actual new-market update or deployment'))
    print([(x['asof'],x['rows'],x['ready']) for x in records])

if __name__=='__main__':run()
