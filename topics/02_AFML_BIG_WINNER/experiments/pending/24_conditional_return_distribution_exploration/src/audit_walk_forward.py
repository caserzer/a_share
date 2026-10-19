"""Requirement-specific audit of both user-approved R14 workstreams."""
import gzip
import hashlib
import json
import numpy as np
import pandas as pd
from run_four_horizons import OUT,EP,TECH,BIN_NAMES
from run_monthly_walk_forward import DEST as A
from fetch_walk_forward_extension import DEST as B,CACHE
from score_newly_matured import check_frozen


def audit():
    panel=pd.read_parquet(OUT/'local_cache/four_horizon_panel.parquet').dropna(subset=TECH+['earnings_yield','book_yield'])
    fits=pd.read_csv(A/'fit_audit.csv')
    assert set(fits.months)=={1,3,6} and len(fits)==3*64*2
    for _,f in fits.iterrows():
        date=pd.Timestamp(f.date);h=f.months
        eligible=panel[(panel[f'end_{h}']<date)&panel[f'y_{h}'].notna()&(panel.date<date)]
        if f.window=='rolling36':eligible=eligible[eligible.date>=date-pd.DateOffset(months=36)]
        assert len(eligible)==f.training_rows
        assert eligible[f'end_{h}'].max()==pd.Timestamp(f.last_training_label)
        assert f.predicted_rows==len(panel[panel.date==date])
    for h in [1,3,6]:
        d=pd.read_parquet(A/f'predictions_{h}m.parquet')
        assert not d.duplicated(['date','instrument','model']).any()
        assert d.model.nunique()==4 and d.date.nunique()==64
        assert len(d)==29596*4
        np.testing.assert_allclose(d[[f'p_{n}' for n in BIN_NAMES]].sum(axis=1),1)
        np.testing.assert_allclose(d[['p_up','p_down','p_zero']].sum(axis=1),1)
        assert d.loc[d.actual.isna(),'brier'].isna().all()
    check_frozen()
    source=pd.read_csv(B/'fetch_audit.csv');assert len(source)==545 and (source.status=='ok').all()
    for _,r in source.iterrows():
        with gzip.open(CACHE/f'{r.instrument}.json.gz','rb') as f:raw=f.read()
        assert hashlib.sha256(raw).hexdigest()==r.sha256
    labels=pd.read_parquet(B/'new_labels.parquet')
    assert labels.groupby('months').date.nunique().to_dict()=={1:1,3:2,6:4}
    assert labels.status.isin(['valid','source_unstable']).all()
    calendar=pd.DatetimeIndex(pd.read_parquet(CACHE/'SH000001.parquet').date).sort_values()
    for _,r in labels.sample(60,random_state=24).iterrows():
        bars=pd.read_parquet(CACHE/f'{r.instrument}.parquet').set_index('date')
        expected_end=calendar[calendar>=r.target_date][0]
        assert expected_end==r.label_end
        np.testing.assert_allclose(r.actual,bars.loc[expected_end,'close']/bars.loc[r.date,'close']-1)
    new=pd.read_parquet(B/'scored_frozen_predictions.parquet')
    for h in [1,3,6]:
        old=pd.read_parquet(OUT/f'r10_four_horizons/predictions_{h}m.parquet')
        j=new[new.months==h].merge(old,on=['date','instrument','months','model'],suffixes=('_new','_old'),validate='one_to_one')
        assert len(j)==len(new[new.months==h])
        for col in ['p_up','p_down','p_zero',*[f'p_{n}' for n in BIN_NAMES]]:
            np.testing.assert_array_equal(j[col+'_new'],j[col+'_old'])
        assert j.actual_old.isna().all()
    for folder in [A,B]:
        cal=pd.read_csv(folder/'probability_calibration.csv')
        assert set(cal.months)=={1,3,6} and set(cal.event)=={'up','down',*BIN_NAMES}
    comparisons=pd.read_csv(A/'baseline_comparisons.csv')
    assert set(comparisons.block_months)=={6,12} and set(comparisons.phase)=={'all','2021_2023','2024_plus'}
    assert (EP/'walk_forward_report.md').exists()
    result=dict(status='complete',horizons=[1,3,6],monthly_refit_origin_months=64,stock_dates_per_horizon=29596,
        strict_mature_label_training_verified=True,rolling_and_expanding_baselines_verified=True,
        unchanged_frozen_probabilities_verified=True,new_label_target_and_price_checks=60,public_source_receipts_verified=545,
        newly_matured_origin_months={1:1,3:2,6:4},calibration_events=['up','down',*BIN_NAMES],
        conclusions=['Amplitude-bin improvement replicated, no stable direction advantage',
            'New-label downside tails undercovered; only 1/2/4 new origins, not proof of stability'],
        limitations=['Retrospective exploration, not independent prospective test',
            'Source-discrepant stocks separately reported; source revision and selection bias remain'],
        report='walk_forward_report.md')
    (OUT/'r14_completion_audit.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':audit()
