import sys
from pathlib import Path
import numpy as np
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from run_monthly_walk_forward import train_at,DEST
from run_four_horizons import OUT,BIN_NAMES
from score_newly_matured import check_frozen


def test_monthly_training_excludes_same_date_and_future_label():
    d=pd.DataFrame(dict(date=pd.to_datetime(['2019-01-31','2021-01-31','2021-02-28','2021-03-31']),
        end_3=pd.to_datetime(['2019-04-30','2021-04-30','2021-05-31','2021-06-30']),y_3=[.1,.2,.3,np.nan]))
    t=train_at(d,3,pd.Timestamp('2021-05-31'))
    assert list(t.y_3)==[.1,.2]
    assert list(train_at(d,3,pd.Timestamp('2021-05-31'),12).y_3)==[.2]


def test_monthly_audit_and_unchanged_prediction_population():
    audit=pd.read_csv(DEST/'fit_audit.csv')
    assert set(audit.months)=={1,3,6}
    assert (pd.to_datetime(audit.last_training_label)<pd.to_datetime(audit.date)).all()
    for h in [1,3,6]:
        new=pd.read_parquet(DEST/f'predictions_{h}m.parquet')
        old=pd.read_parquet(OUT/f'r10_four_horizons/predictions_{h}m.parquet')
        reference=set(map(tuple,old[old.model=='peers_risk_size'][['date','instrument']].to_numpy()))
        for _,g in new.groupby('model'):
            assert set(map(tuple,g[['date','instrument']].to_numpy()))==reference
        np.testing.assert_allclose(new[[f'p_{n}' for n in BIN_NAMES]].sum(axis=1),1)


def test_new_labels_preserve_frozen_forecasts_and_target_dates():
    check_frozen()
    new=pd.read_parquet(OUT/'r14_newly_matured/scored_frozen_predictions.parquet')
    for h in [1,3,6]:
        old=pd.read_parquet(OUT/f'r10_four_horizons/predictions_{h}m.parquet')
        joined=new[new.months==h].merge(old,on=['date','instrument','months','model'],suffixes=('_new','_old'),validate='one_to_one')
        assert len(joined)==len(new[new.months==h])
        for col in ['p_up','p_down','p_zero',*[f'p_{n}' for n in BIN_NAMES]]:
            np.testing.assert_array_equal(joined[col+'_new'],joined[col+'_old'])
        assert joined.actual_old.isna().all()
        assert (joined.target_date_new>'2026-05-29').all()
        assert (joined.label_end_new>=joined.target_date_new).all()
        assert (joined.label_end_new<='2026-10-19').all()
