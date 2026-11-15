"""Check full historical feature equivalence and prefix isolation."""
import pandas as pd
from common import *
from cutoff_features_r102 import regenerate,DAILY
from inference_bundle_r101 import INPUT
from versioned_observations import verify_bundle

def run():
    out=ROOT/'outputs/r102';bundles=json.loads((out/'bundles.json').read_text())
    original=pd.concat([pd.read_parquet(ROOT/f'data/{p}.parquet',columns=INPUT) for p in ['monthly_panel','l1_monthly_panel']],ignore_index=True)
    daily=pd.concat([pd.read_parquet(p,columns=DAILY) for p in [CACHE/'forecast_v5/daily_industries.parquet',ROOT/'data/l1_daily.parquet']],ignore_index=True)
    daily=daily[daily.era.eq('SW2021')];market=pd.read_parquet(CACHE/'forecast_v5/CSI_ALL.parquet').close
    prior={b['asof']:b for b in json.loads((ROOT/'outputs/r101/bundles.json').read_text())}
    results=[]
    for b in bundles:
        date=b['cutoff'];p=out/f'features_{date}.parquet';assert sha(p)==b['feature_sha256']
        f=pd.read_parquet(p);expected=original[original.era.eq('SW2021')&original.date.le(date)].sort_values(KEY+['date']).reset_index(drop=True)
        pd.testing.assert_frame_equal(f,expected,check_exact=False,atol=1e-12,rtol=1e-12)
        pd.testing.assert_frame_equal(regenerate(daily,market,date),f)
        provenance=json.loads((out/f'provenance_{date}.json').read_text())
        for path,digest in provenance['reads'].items():assert sha(path)==digest
        for a in provenance['archived'].values():assert sha(a['path'])==a['sha256']
        archived=provenance['archived'];prefix=pd.read_parquet(archived['daily']['path']);bm=pd.read_parquet(archived['benchmark']['path']).close
        assert prefix.date.max()<=pd.Timestamp(date) and bm.index.max()<=pd.Timestamp(date)
        pd.testing.assert_frame_equal(prefix.reset_index(drop=True),daily[daily.date.le(date)].reset_index(drop=True))
        pd.testing.assert_series_equal(bm,market.loc[:date])
        pd.testing.assert_frame_equal(regenerate(prefix,bm,date),f)
        assert sha(Path(b['path'])/'manifest.json')==b['manifest_sha256'];m=verify_bundle(b['path'])
        assert m['sources']['provenance']['sha256']==sha(out/f'provenance_{date}.json')
        assert m['sources']['features']['sha256']==sha(out/f'exact_{date}.parquet')
        old=Path(prior[date]['path']);verify_bundle(old)
        new=pd.read_parquet(Path(b['path'])/'predictions.parquet');ref=pd.read_parquet(old/'predictions.parquet')
        pd.testing.assert_frame_equal(new,ref,check_exact=False,atol=1e-12,rtol=1e-12)
        results.append(dict(cutoff=date,feature_rows=len(f),exact_rows=b['exact_rows'],formal_rows=int(new.prediction.notna().sum()),status='PASS'))
    js(out/'verification.json',dict(status='PASS',comparisons=results,reference_panels={p:sha(ROOT/f'data/{p}.parquet') for p in ['monthly_panel','l1_monthly_panel']},prospective_records=0))
    print(results)

if __name__=='__main__':run()
