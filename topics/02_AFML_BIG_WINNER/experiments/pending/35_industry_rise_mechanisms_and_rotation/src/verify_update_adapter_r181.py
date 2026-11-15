"""Verify adapter rows, source lineage, clocks and frozen independent cutoffs."""
import pandas as pd
from common import *
from versioned_observations import verify_bundle


def run():
    out=ROOT/'outputs/r181';rec=json.loads((out/'receipt.json').read_text())
    for p,h in {**rec['reads'],**rec['prior_snapshots']}.items():assert sha(p)==h
    source=pd.read_parquet(ROOT/'outputs/r129/daily_2026-10-21.parquet')
    a=pd.read_parquet(CACHE/'extension_v2/products/assignments.parquet',columns=KEY+['month','date','security_id'])
    lineage=a.groupby(KEY+['month']).agg(date=('date','first'),n=('security_id','size'))
    cal=pd.read_parquet(CACHE/'forecast_v5/CSI_ALL.parquet').index;checked=0;frozen=[]
    for r in json.loads((out/'runs.json').read_text()):
        date=pd.Timestamp(r['asof']);d=pd.read_parquet(r['daily_path']);assert sha(r['daily_path'])==r['daily_sha256']
        expected=source[(source.date<=date)&(source.known_at<=date)].sort_values(KEY+['date']).reset_index(drop=True)
        pd.testing.assert_frame_equal(d[source.columns.drop('block')],expected[source.columns.drop('block')],check_dtype=False)
        assert d.known_at.le(date).all() and d.date.le(date).all()
        assert (cal.get_indexer(d.date)==d.day_i).all()
        for _,g in d.groupby(KEY):
            ords=cal.get_indexer(g.date);start=np.r_[True,np.diff(ords)!=1]|g.source_kind.eq('anchor').to_numpy()
            want=pd.Series(g.date.to_numpy()).where(start).ffill().dt.strftime('%Y%m%d').astype(int).to_numpy()
            assert np.array_equal(want,g.block.to_numpy())
        # Unique member-source groups, independently derive month from row kind.
        group=d.groupby(KEY+['source_kind','membership_month','membership_asof','source_members'],dropna=False)
        for key,g in group:
            era,level,code,kind,month,asof,n=key
            inferred=g.date.dt.to_period('M')-(1 if kind=='observed' else 0)
            assert inferred.eq(month).all();row=lineage.loc[(era,level,code,month)]
            assert row['date']==asof and row.n==n and g.members.eq(n).all()
        if r['asof'] in ['2026-09-30','2026-10-21']:
            p=ROOT/f"outputs/r129/daily_{r['asof']}.parquet"
            truth=pd.read_parquet(p).sort_values(KEY+['date']).reset_index(drop=True)
            pd.testing.assert_frame_equal(d[truth.columns],truth,check_dtype=False)
            frozen.append(dict(asof=r['asof'],path=str(p),sha256=sha(p),rows=len(truth)))
        m=verify_bundle(r['snapshot']);assert sha(Path(r['snapshot'])/'manifest.json')==r['snapshot_sha256']
        obs=pd.read_parquet(Path(r['snapshot'])/'observations.parquet');sub=obs[obs.level.isin(['L2','L3'])]
        assert sub.membership_asof.notna().equals(sub.date.notna())
        assert m['capture_kind']=='historical_replay';checked+=len(d)
    p=pd.read_parquet(out/'comparison.parquet');stats=[]
    for date,g in p.groupby('asof'):
        stats.append(dict(asof=date,status_changes=int(g.status_old.ne(g.status_new).sum()),score_changes=int((~np.isclose(g.price_score_old,g.price_score_new,atol=1e-12,rtol=1e-12,equal_nan=True)).sum()),rank_changes=int((~np.isclose(g.price_rank_old,g.price_rank_new,equal_nan=True)).sum())))
    js(out/'verification.json',dict(status='PASS',daily_rows_checked=checked,frozen_prefixes=frozen,comparison=stats,prospective_records=0));print('PASS',checked,stats)


if __name__=='__main__':run()
