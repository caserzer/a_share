"""Rebuild every maturity/path outcome without the evaluation implementation."""
import pandas as pd
from common import *
from versioned_observations import verify_bundle


def run():
    out=ROOT/'outputs/r182';rec=json.loads((out/'receipt.json').read_text());runs=json.loads((out/'runs.json').read_text())
    for p,h in rec['reads'].items():assert sha(p)==h
    n=0;allframes=[]
    for r in runs:
        ep=Path(r['evaluation']);sp=Path(r['snapshot']);em=verify_bundle(ep);sm=verify_bundle(sp)
        assert sha(ep/'manifest.json')==r['evaluation_sha256'] and sha(sp/'manifest.json')==r['snapshot_sha256']
        parts=[pd.read_parquet(em['sources'][f'daily_{i}']['path']) for i in range(2)]
        cutoff=pd.Timestamp(r['evaluation_asof']);assert parts[0].known_at.le(cutoff).all() and parts[0].known_at.notna().all()
        assert all(p.date.le(cutoff).all() for p in parts)
        daily=pd.concat(parts,ignore_index=True);b=pd.read_parquet(em['sources']['market']['path']).close;assert b.index.max()<=cutoff
        cal=list(b.index);groups={k:g.set_index('date') for k,g in daily.groupby(KEY)}
        frame=pd.read_parquet(ep/'outcomes.parquet');obs=pd.read_parquet(sp/'observations.parquet').set_index(KEY)
        assert len(frame)==2*len(obs) and frame.evaluation_kind.eq('historical_replay').all()
        for row in frame.itertuples():
            key=tuple(getattr(row,k) for k in KEY);o=obs.loc[key]
            assert row.price_ready==o.price_ready and np.isclose(row.price_score,o.price_score,equal_nan=True)
            i=cal.index(row.origin);end=i+row.horizon+1
            if end>=len(cal):assert row.status=='pending_market_sessions' and pd.isna(row.excess)
            else:
                dates=cal[i+1:end+1];assert row.entry_date==dates[0] and row.maturity==dates[-1]
                g=groups.get(key)
                valid=g is not None and set(dates)<=set(g.index)
                if valid:
                    x=g.loc[dates];valid=bool(x.nav.notna().all() and x.nav.gt(0).all() and x.block.nunique()==1)
                if valid:
                    ret=x.nav.iloc[-1]/x.nav.iloc[0]-1;ex=ret-(b.loc[dates[-1]]/b.loc[dates[0]]-1)
                    assert row.status=='mature' and np.isclose(row.absolute_return,ret,rtol=1e-12,atol=1e-12) and np.isclose(row.excess,ex,rtol=1e-12,atol=1e-12)
                else:assert row.status==('missing_identity' if g is None else 'missing_or_discontinuous_price_path') and pd.isna(row.excess)
            n+=1
        frame['evaluation_asof']=r['evaluation_asof'];allframes.append(frame)
    got=pd.concat(allframes,ignore_index=True);pd.testing.assert_frame_equal(got,pd.read_parquet(out/'outcomes.parquet'))
    old=pd.read_parquet(ROOT/'outputs/r179/outcomes.parquet');old=old[old.version.eq('repaired')]
    current=got[got.evaluation_asof.eq('2026-10-21')]
    pair=old.merge(current,on=KEY+['origin','horizon'],suffixes=('_old','_new'),validate='one_to_one')
    assert len(pair)==2044
    changes=int((~np.isclose(pair.excess_old,pair.excess_new,rtol=1e-12,atol=1e-12,equal_nan=True)).sum());status_changes=int(pair.status_old.ne(pair.status_new).sum())
    js(out/'verification.json',dict(status='PASS',independent_outcome_rows=n,evaluation_versions=len(runs),comparison_rows=len(pair),excess_changes=changes,status_changes=status_changes,prospective_records=0));print('PASS',n,changes,status_changes)


if __name__=='__main__':run()
