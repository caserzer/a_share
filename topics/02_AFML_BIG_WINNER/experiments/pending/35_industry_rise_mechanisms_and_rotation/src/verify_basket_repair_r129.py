"""Independent prefix, observation and ready-feature invariants for repair."""
import pandas as pd
from common import *
from cutoff_features_r102 import DAILY
from verify_basket_replay_r128 import differences

def run():
    out=ROOT/'outputs/r129';receipt=json.loads((out/'receipt.json').read_text())
    for p,digest in receipt['reads'].items():assert sha(p)==digest,p
    ref=pd.read_parquet(CACHE/'forecast_v5/daily_industries.parquet',columns=DAILY)
    calendar=pd.read_parquet(CACHE/'forecast_v5/CSI_ALL.parquet').index
    monthly=pd.read_parquet(ROOT/'data/monthly_panel.parquet');keys=KEY+['date'];prev=None;prev_features=None;previous_date=None;results=[]
    for x in receipt['results']:
        cutoff=x['cutoff'];dp=out/f'daily_{cutoff}.parquet';fp=out/f'features_{cutoff}.parquet';assert sha(dp)==x['sha256'] and sha(fp)==x['feature_sha256']
        d=pd.read_parquet(dp);f=pd.read_parquet(fp);assert not d.duplicated(keys).any();assert d.known_at.le(cutoff).all()
        for _,g in d.groupby(KEY):
            positions=pd.Series(calendar.get_indexer(g.date),index=g.index)
            start=positions.diff().ne(1)|g.source_kind.eq('anchor')
            expected=g.date.where(start).ffill().dt.strftime('%Y%m%d').astype('int64')
            assert np.array_equal(g.block,expected)
        anchors=d[d.source_kind.eq('anchor')];assert anchors.nav.eq(1).all() and anchors.coverage.isna().all();assert anchors.known_at.gt(anchors.date).all()
        # Numeric market payload on shared rows must match legacy source; block identifiers intentionally changed.
        cols=[c for c in DAILY if c!='block'];ds,fields,missing,extra,bad=differences(d[cols],ref[ref.date.le(cutoff)][cols],keys)
        assert ds['different_shared_rows']==0
        assert extra.nav.eq(1).all() and extra.coverage.isna().all()
        assert missing.nav.eq(1).all() and missing.coverage.isna().all()
        if len(missing):
            final=pd.read_parquet(out/'daily_2026-10-21.parquet').set_index(keys)
            absent=final.loc[missing.set_index(keys).index]
            assert absent.source_kind.eq('anchor').all() and absent.known_at.gt(cutoff).all()
        fs,ff,fm,fe,fb=differences(f,monthly[monthly.date.le(cutoff)][f.columns],keys)
        for name,frame in [('missing',fm),('extra',fe),('different',fb)]:frame.to_parquet(out/f'legacy_feature_{name}_{cutoff}.parquet',index=False)
        transition=None
        if prev is not None:
            a=prev.set_index(keys).sort_index();b=d[d.date.le(previous_date)].set_index(keys).sort_index();common=a.index.intersection(b.index)
            assert len(common)==len(a)
            pd.testing.assert_frame_equal(a.loc[common].reset_index(),b.loc[common].reset_index(),check_exact=True)
            inserts=b.loc[~b.index.isin(a.index)].reset_index()
            assert inserts.source_kind.eq('anchor').all() and inserts.known_at.gt(previous_date).all()
            before=prev_features[prev_features.price_ready];after=f[f.date.le(previous_date)&f.price_ready]
            pd.testing.assert_frame_equal(before.reset_index(drop=True),after.reset_index(drop=True),check_exact=True)
            transition=dict(unchanged_prior_rows=len(a),inserted_anchors=len(inserts),unchanged_ready_features=len(before))
        results.append(dict(cutoff=cutoff,rows=len(d),anchors=len(anchors),ready=int(f.price_ready.sum()),legacy_daily=ds,legacy_features=fs,legacy_feature_fields=ff,transition=transition))
        prev=d;prev_features=f;previous_date=cutoff
    js(out/'verification.json',dict(status='PASS',results=results,scope='five local cutoffs; no silent market-row rewrite; documented new anchors allowed',legacy_monthly_sha256=sha(ROOT/'data/monthly_panel.parquet')))
    print(results)

if __name__=='__main__':run()
