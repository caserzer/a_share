"""Replay every admitted frozen model's complete output from feature-only input."""
import json
import pickle

import pandas as pd
import numpy as np

from common import OUT, config, sha, utc_now, write_json
from walk_forward import append_lagged_features, cohort, load_features, predict_pair


def main():
    features=append_lagged_features(load_features());checked=0;rows=0
    for h,spec in config()['primary'].items():
        if h=='H09':continue
        f=cohort(features,h)
        valid=(f.relative_turnover.notna()&f.eff.notna()) if h=='H10' else f[spec['feature']].notna()
        f=f.loc[valid]
        for r in json.loads((OUT/f'manifests/{h}_folds.json').read_text())['folds']:
            if sha(r['model_path'])!=r['model_sha256']:raise ValueError('changed model')
            model=pickle.loads(__import__('pathlib').Path(r['model_path']).read_bytes())
            test=f.loc[f.date.dt.to_period('Q').astype(str).eq(r['fold'])]
            replay=predict_pair(model,test,h).reset_index(drop=True)
            stored=pd.read_parquet(r['predictions_path'])[replay.columns].reset_index(drop=True)
            # Arrow stores an object column containing only booleans as bool.
            # Validate its values before matching this lossless serialization type.
            for col in replay:
                if stored[col].dtype==bool and replay[col].dtype!=bool:
                    if not replay[col].map(lambda x:isinstance(x,(bool,np.bool_))).all():raise AssertionError('nonboolean mask in replay')
                    replay[col]=replay[col].astype(bool)
            pd.testing.assert_frame_equal(replay,stored,check_exact=True)
            checked+=1;rows+=len(replay)
        print('all-column model replay',h,flush=True)
    write_json(OUT/'audits/all_prediction_columns_replay.json',dict(status='PASS',checked_at=utc_now(),folds=checked,rows=rows,
               all_columns_exact=True,includes_placebo_lag_partial_factor_masks_and_primary_predictions=True,
               arrow_boolean_serialization_type_canonicalized=True,
               inputs='feature-only; no outcome table read'))


if __name__=='__main__':main()
