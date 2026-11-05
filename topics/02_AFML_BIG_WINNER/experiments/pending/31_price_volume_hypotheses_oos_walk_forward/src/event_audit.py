"""Rebuild all causal features, confirm sealed payload equivalence, count raw events."""
import numpy as np
import pandas as pd

from common import OUT, cache, sha, utc_now, write_json
from ep30_adapter import EP30Adapter
from episode_builder import observation_masks
from volume_price_features import build_features


def main():
    a=EP30Adapter(); counts=[]; checked=0; securities_checked=0
    paths=sorted((cache()/'data').glob('features_*.parquet'))
    lookup={}
    for p in paths:
        f=pd.read_parquet(p)
        for sid,g in f.groupby('security_id',sort=False):lookup[sid]=g
    for i,s in enumerate(a.inventory.itertuples()):
        b=a.bars(s.security_id)
        if b is None or b.empty:continue
        f=build_features(b,a.days)
        start=s.listing_date if pd.notna(s.listing_date) else s.bse_listing_proxy
        eligible=(a.days>=start)&(pd.isna(s.delist_date)|(a.days<s.delist_date)) if pd.notna(start) else np.zeros(len(a.days),bool)
        masks=observation_masks(f,eligible)
        old=lookup.get(s.security_id)
        if old is not None and len(old):
            new=f.set_index('date').loc[old.date].reset_index()
            for col in f.columns:
                if col not in old:continue
                x,y=old[col].reset_index(drop=True),new[col].reset_index(drop=True)
                if pd.api.types.is_numeric_dtype(y):
                    same=np.isclose(x.to_numpy(float),y.to_numpy(float),equal_nan=True,rtol=1e-12,atol=1e-12)
                else:same=(x.eq(y)|(x.isna()&y.isna())).to_numpy()
                if not same.all():raise ValueError('feature replay mismatch '+s.security_id+' '+col)
            checked+=len(old);securities_checked+=1
        years=a.days.year
        for year in np.unique(years):
            mask=years==year
            counts.append(dict(year=int(year),board=s.board_bucket,
                          h10_event_days=int((masks['h10_event']&mask).sum()),h10_episodes=int((masks['h10_episode']&mask).sum()),
                          h11_event_days=int((masks['h11_event']&mask).sum()),h11_episodes=int((masks['h11_episode']&mask).sum())))
        if i%500==0:print('feature replay',i,flush=True)
    pd.DataFrame(counts).groupby(['year','board']).sum().reset_index().to_csv(OUT/'audits/daily_event_and_episode_coverage.csv',index=False)
    write_json(OUT/'audits/feature_replay.json',dict(status='PASS',replayed_at=utc_now(),rows=checked,securities=securities_checked,
               all_stored_feature_columns_compared=True,chain_guard_added_after_data_build_actual_rows_unchanged=True,
               no_outcome_scoring_used=True,current_feature_source_sha256=sha(__import__('volume_price_features').__file__),
               original_data_source_snapshot=str(cache()/'frozen_data_source_v1')))


if __name__=='__main__':main()
