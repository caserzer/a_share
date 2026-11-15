"""Replay immutable observations with original and corrected historical baskets."""
import pandas as pd
from common import *
from versioned_observations import capture, evaluate, verify_bundle, FEATURES


def run():
    out=ROOT/'outputs/r179';store=ROOT/'data/update_store_r179'
    protocol=ROOT/'protocols/r179.json';cfg=json.loads(protocol.read_text())
    daily={'legacy':CACHE/'forecast_v5/daily_industries.parquet','repaired':ROOT/'outputs/r129/daily_2026-10-21.parquet'}
    l1=ROOT/'data/l1_daily.parquet';market=CACHE/'forecast_v5/CSI_ALL.parquet';catalog=ROOT/'outputs/universe_current.csv'
    prior=json.loads((ROOT/'outputs/r18/replay_receipt.json').read_text())
    prior_hashes={str(Path(x[k])/'manifest.json'):sha(Path(x[k])/'manifest.json') for x in prior['runs'] for k in ['snapshot','evaluation']}
    runs=[];comparisons=[];outcomes=[]
    for date in cfg['dates']:
        bundles={};frames={}
        for version,p in daily.items():
            bundle=capture(store,[p,l1],market,catalog,date)
            digest=sha(bundle/'manifest.json')
            assert capture(store,[p,l1],market,catalog,date)==bundle and sha(bundle/'manifest.json')==digest
            bundles[version]=bundle;frames[version]=pd.read_parquet(bundle/'observations.parquet')
        pair=frames['legacy'].merge(frames['repaired'],on=KEY,how='outer',suffixes=('_old','_new'),indicator=True,validate='one_to_one')
        assert pair._merge.eq('both').all();pair['asof']=date
        comparisons.append(pair)
        for name,snapshot,source in [('legacy','legacy','legacy'),('source_revision','legacy','repaired'),('repaired','repaired','repaired')]:
            bundle=bundles[snapshot];before=sha(bundle/'manifest.json')
            ev=evaluate(store,bundle,[daily[source],l1],market,cfg['evaluation_asof'])
            assert sha(bundle/'manifest.json')==before
            manifest=verify_bundle(ev);frame=pd.read_parquet(ev/'outcomes.parquet');assert frame.evaluation_kind.eq('historical_replay').all()
            frame['version']=name;frame['asof']=date;outcomes.append(frame)
            runs.append(dict(asof=date,version=name,snapshot=str(bundle),snapshot_sha256=before,evaluation=str(ev),evaluation_sha256=sha(ev/'manifest.json'),historical_price_prefix_changed_rows=manifest['historical_price_prefix_changed_rows'],market_prefix_changed_rows=manifest['market_prefix_changed_rows']))
    pair=pd.concat(comparisons,ignore_index=True);result=pd.concat(outcomes,ignore_index=True)
    pair.to_parquet(out/'observation_comparison.parquet',index=False);result.to_parquet(out/'outcomes.parquet',index=False)
    stats=[]
    for (date,level),g in pair.groupby(['asof','level']):
        stats.append(dict(asof=date,level=level,rows=len(g),ready_old=int(g.price_ready_old.sum()),ready_new=int(g.price_ready_new.sum()),status_changes=int(g.status_old.ne(g.status_new).sum()),score_changes=int((~np.isclose(g.price_score_old,g.price_score_new,rtol=1e-12,atol=1e-12,equal_nan=True)).sum()),rank_changes=int((~np.isclose(g.price_rank_old,g.price_rank_new,equal_nan=True)).sum())))
    assert all(sha(p)==h for p,h in prior_hashes.items())
    js(out/'runs.json',runs);js(out/'summary.json',dict(observations=stats,outcome_statuses=result.groupby(['asof','version','horizon','status']).size().rename('rows').reset_index().to_dict('records'),prospective_records=0,old_bundles_unchanged=True))
    js(out/'receipt.json',dict(reads={str(p):sha(p) for p in [protocol,Path(__file__),ROOT/'src/versioned_observations.py',ROOT/'src/build_panel.py',*daily.values(),l1,market,catalog]},prior_manifest_hashes=prior_hashes))
    print(stats,flush=True)


if __name__=='__main__':run()
