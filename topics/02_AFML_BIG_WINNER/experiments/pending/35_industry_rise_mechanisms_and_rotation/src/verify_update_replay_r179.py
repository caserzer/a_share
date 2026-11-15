"""Independent calendar-path verification plus sealed snapshot checks."""
import pandas as pd
from common import *
from versioned_observations import verify_bundle


def run():
    out=ROOT/'outputs/r179';receipt=json.loads((out/'receipt.json').read_text())
    for p,h in {**receipt['reads'],**receipt['prior_manifest_hashes']}.items():assert sha(p)==h
    runs=json.loads((out/'runs.json').read_text());checked=0;snapshots=set();frames=[]
    for run in runs:
        sp=Path(run['snapshot']);ep=Path(run['evaluation'])
        assert sha(sp/'manifest.json')==run['snapshot_sha256'] and sha(ep/'manifest.json')==run['evaluation_sha256']
        sm=verify_bundle(sp);em=verify_bundle(ep);snapshots.add(str(sp))
        obs=pd.read_parquet(sp/'observations.parquet');got=pd.read_parquet(ep/'outcomes.parquet')
        assert sm['capture_kind']=='historical_replay' and got.evaluation_kind.eq('historical_replay').all()
        assert not {'return20','excess20','entry_date','maturity20','y'}&set(obs.columns)
        daily=pd.concat([pd.read_parquet(v['path']) for k,v in em['sources'].items() if k.startswith('daily_')])
        market=pd.read_parquet(em['sources']['market']['path']).close
        cal=list(market.index[market.index<=pd.Timestamp(em['identity']['asof'])])
        lookup={k:g.set_index('date') for k,g in daily.groupby(KEY)}
        original=obs.set_index(KEY)
        for row in got.itertuples():
            key=tuple(getattr(row,k) for k in KEY);o=original.loc[key]
            assert row.price_ready==o.price_ready and np.isclose(row.price_score,o.price_score,equal_nan=True)
            i=cal.index(row.origin);end=i+row.horizon+1
            if end>=len(cal):
                assert row.status=='pending_market_sessions' and pd.isna(row.excess)
            else:
                dates=cal[i+1:end+1];assert row.entry_date==dates[0] and row.maturity==dates[-1]
                g=lookup.get(key)
                valid=g is not None and all(d in g.index for d in dates)
                if valid:
                    path=g.loc[dates];valid=bool(path.nav.notna().all() and path.nav.gt(0).all() and path.block.nunique()==1)
                if valid:
                    ret=float(path.nav.iloc[-1]/path.nav.iloc[0]-1);bm=float(market.loc[dates[-1]]/market.loc[dates[0]]-1)
                    assert row.status=='mature' and np.isclose(row.absolute_return,ret,rtol=1e-12,atol=1e-12) and np.isclose(row.excess,ret-bm,rtol=1e-12,atol=1e-12)
                else:assert row.status in ['missing_identity','missing_or_discontinuous_price_path'] and pd.isna(row.excess)
            checked+=1
        got['version']=run['version'];got['asof']=run['asof'];frames.append(got)
    pd.testing.assert_frame_equal(pd.concat(frames,ignore_index=True),pd.read_parquet(out/'outcomes.parquet'))
    pair=pd.read_parquet(out/'observation_comparison.parquet')
    rebuilt=[]
    for date in sorted({r['asof'] for r in runs}):
        selected={r['version']:r for r in runs if r['asof']==date}
        a=pd.read_parquet(Path(selected['legacy']['snapshot'])/'observations.parquet')
        b=pd.read_parquet(Path(selected['repaired']['snapshot'])/'observations.parquet')
        p=a.merge(b,on=KEY,how='outer',suffixes=('_old','_new'),indicator=True,validate='one_to_one');p['asof']=date;rebuilt.append(p)
    pd.testing.assert_frame_equal(pd.concat(rebuilt,ignore_index=True),pair)
    assert len(pair)==1022 and pair[pair.level.eq('L1')].status_old.equals(pair[pair.level.eq('L1')].status_new)
    for run in runs:
        if run['version']=='source_revision':assert run['historical_price_prefix_changed_rows']>0
        else:assert run['historical_price_prefix_changed_rows']==0
        assert run['market_prefix_changed_rows']==0
    js(out/'verification.json',dict(status='PASS',snapshots=len(snapshots),evaluation_versions=len(runs),outcome_rows_independently_verified=checked,old_bundles_unchanged=True,prospective_records=0))
    print('PASS',len(snapshots),len(runs),checked)


if __name__=='__main__':run()
