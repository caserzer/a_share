"""Independent discrepancy audit; PASS means audit verified, not append safety."""
import pandas as pd
from common import *
from cutoff_features_r102 import DAILY


def differences(a,b,keys):
    left=a.set_index(keys).sort_index();right=b.set_index(keys).sort_index();common=left.index.intersection(right.index)
    missing=right.loc[~right.index.isin(left.index)].reset_index();extra=left.loc[~left.index.isin(right.index)].reset_index()
    fields={};mask=np.zeros(len(common),bool)
    for c in left.columns:
        x=left.loc[common,c].to_numpy(float);y=right.loc[common,c].to_numpy(float)
        bad=~np.isclose(x,y,rtol=1e-12,atol=1e-12,equal_nan=True);fields[c]=int(bad.sum());mask|=bad
    bad=common[mask].to_frame(index=False)
    return dict(shared=len(common),missing=len(missing),extra=len(extra),different_shared_rows=len(bad)),fields,missing,extra,bad


def run():
    out=ROOT/'outputs/r128';receipt=json.loads((out/'receipt.json').read_text())
    for p,digest in receipt['reads'].items():assert sha(p)==digest,p
    ref=pd.read_parquet(CACHE/'forecast_v5/daily_industries.parquet',columns=DAILY)
    monthly=pd.read_parquet(ROOT/'data/monthly_panel.parquet');results=[];previous=None;previous_date=None;keys=KEY+['date']
    for x in receipt['results']:
        cutoff=x['cutoff'];dp=out/f'daily_{cutoff}.parquet';fp=out/f'features_{cutoff}.parquet'
        assert sha(dp)==x['sha256'] and sha(fp)==x['feature_sha256']
        d=pd.read_parquet(dp);r=ref[ref.date.le(cutoff)]
        assert not d.duplicated(keys).any() and d.date.le(cutoff).all()
        stats,fields,missing,extra,bad=differences(d,r,keys);assert stats==x['comparison']
        for name,f in [('missing',missing),('extra',extra),('different',bad)]:
            pd.testing.assert_frame_equal(pd.read_parquet(out/f'{name}_{cutoff}.parquet'),f,check_dtype=bool(len(f)))
        # Characterize, do not conceal non-equivalence.
        assert all(n==0 for c,n in fields.items() if c!='block')
        for f in [missing,extra]:assert f.nav.eq(1).all() and f.coverage.isna().all()
        features=pd.read_parquet(fp);mr=monthly[monthly.date.le(cutoff)][features.columns]
        fs,ff,fm,fe,fb=differences(features,mr,keys)
        for name,f in [('missing',fm),('extra',fe),('different',fb)]:f.to_parquet(out/f'feature_{name}_{cutoff}.parquet',index=False)
        ready_a=features[features.price_ready].copy();ready_b=mr[mr.price_ready].copy()
        ready_stats,ready_fields,ready_missing,ready_extra,ready_bad=differences(ready_a,ready_b,keys)
        for name,frame in [('missing',ready_missing),('extra',ready_extra),('different',ready_bad)]:frame.to_parquet(out/f'ready_{name}_{cutoff}.parquet',index=False)
        if len(ready_missing):
            a=features.set_index(keys);b=mr.set_index(keys);changes=[]
            for key in ready_missing.set_index(keys).index:
                changes.append(dict(zip(keys,key),cutoff=a.loc[key].to_dict() if key in a.index else None,full_history=b.loc[key].to_dict()))
            js(out/f'ready_feature_changes_{cutoff}.json',changes)
        transition=None
        if previous is not None:
            transition,_,ins,deleted,changed=differences(previous,d[d.date.le(previous_date)],keys)
            assert transition==x['transition']
            for name,f in [('inserted',ins),('deleted',deleted),('changed',changed)]:pd.testing.assert_frame_equal(f,pd.read_parquet(out/f'transition_{name}_{cutoff}.parquet'),check_dtype=bool(len(f)))
        results.append(dict(cutoff=cutoff,rows=len(d),daily=stats,field_differences=fields,features=fs,feature_field_differences=ff,ready_features=ready_stats,ready_field_differences=ready_fields,transition=transition))
        previous=d;previous_date=cutoff
    js(out/'verification.json',dict(status='PASS',append_safety='NOT_ESTABLISHED',results=results,reference_monthly_sha256=sha(ROOT/'data/monthly_panel.parquet'),meaning='Independent counts and values verified; historical identity/block changes remain unresolved'))
    print(json.dumps(results,default=str))

if __name__=='__main__':run()
