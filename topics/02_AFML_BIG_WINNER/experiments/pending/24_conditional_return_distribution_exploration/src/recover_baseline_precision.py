"""R30 restore R15 B float64 atoms without changing frozen predictions or labels."""
import hashlib
import json
import numpy as np
import pandas as pd
from sklearn.neighbors import NearestNeighbors
from prepare_panel import OUT
from build_margin_information import digest
from build_three_factor_panel import PANEL,BASE
from run_three_factor_ablation import scaled_features
from run_four_horizons import GRID,probability_stats,BIN_NAMES

DEST=OUT/'r30_diverse_ensemble'
RECOVERED=OUT/'local_cache/r30_baseline_float64'


def recover():
    DEST.mkdir(exist_ok=True);RECOVERED.mkdir(exist_ok=True)
    source=OUT/'r15_three_factor_ablation';spec=json.loads((source/'run_spec.json').read_text())
    assert digest(PANEL)==spec['panel_sha256']
    panel=pd.read_parquet(PANEL);panel=panel[panel.common_eligible].copy()
    fits=pd.read_csv(source/'fit_audit.csv');differences=[];receipts=[];maximum=0.;months=[]
    for h in [1,3,6]:
        path=source/f'predictions_{h}m.parquet';frozen=pd.read_parquet(path);frozen=frozen[frozen.model.eq('B')]
        receipts.append(dict(path=str(path),sha256=digest(path)))
        for date,test in panel[panel.date.ge('2021-01-01')].groupby('date',sort=True):
            test=test.reset_index(drop=True);keys=test[['date','instrument']]
            original=frozen[frozen.date.eq(date)].reset_index(drop=True)
            pd.testing.assert_frame_equal(original[['date','instrument']],keys)
            train=panel[(panel.date<date)&(panel[f'end_{h}']<date)&panel[f'y_{h}'].notna()]
            record=fits[fits.months.eq(h)&fits.date.eq(str(date.date()))].iloc[0]
            assert len(train)==record.training_rows
            train_hash=hashlib.sha256(train[['date','instrument']].sort_values(['date','instrument']).to_csv(index=False).encode()).hexdigest()
            assert train_hash==record.train_key_sha256
            y=train[f'y_{h}'].to_numpy();globalq=np.quantile(y,GRID);x,z=scaled_features(train,test)
            idx=NearestNeighbors(n_neighbors=min(1000,len(train)),n_jobs=1).fit(x[BASE]).kneighbors(z[BASE],return_distance=False)
            atoms=.75*np.quantile(y[idx],GRID,axis=1).T+.25*globalq
            old=OUT/f'local_cache/r15_distributions/{h}_{date.date()}_B.npz'
            with np.load(old) as payload:cached=payload['atoms']
            np.testing.assert_array_equal(atoms.astype(np.float32),cached)
            stats=probability_stats(atoms,original.actual)
            np.testing.assert_allclose(stats,original[stats.columns],atol=1e-12,rtol=1e-12,equal_nan=True)
            maximum=max(maximum,float((stats-original[stats.columns]).abs().max().max()))
            rounded=probability_stats(cached.astype(float),original.actual)
            pcols=['p_up','p_down','p_zero']+['p_'+n for n in BIN_NAMES]
            error=(rounded[pcols]-stats[pcols]).abs().max(axis=1)
            for i in np.flatnonzero(error.to_numpy()>1e-10):
                differences.append(dict(months=h,date=str(date.date()),instrument=original.instrument.iloc[i],max_probability_difference=float(error.iloc[i]),
                    up_difference=float(rounded.p_up.iloc[i]-stats.p_up.iloc[i]),five_bin_score_difference=float(rounded.multiclass_brier.iloc[i]-stats.multiclass_brier.iloc[i])))
            observed=original.actual.notna();nonzero=observed&original.actual.ne(0)
            months.append(dict(months=h,date=str(date.date()),affected_rows=int((error>1e-10).sum()),
                brier_difference=float((rounded.brier-stats.brier)[observed].mean()),
                five_bin_difference=float((rounded.multiclass_brier-stats.multiclass_brier)[observed].mean()),
                crps_difference=float((rounded.crps-stats.crps)[observed].mean()),
                direction_changes=int(((rounded.p_up>rounded.p_down)!=(stats.p_up>stats.p_down))[nonzero].sum())))
            new=RECOVERED/f'{h}_{date.date()}_B.npz';kp=RECOVERED/f'{h}_{date.date()}_keys.parquet'
            np.savez_compressed(new,atoms=atoms);keys.to_parquet(kp,index=False)
            receipts.extend([dict(path=str(p),sha256=digest(p)) for p in [old,new,kp]])
            print('baseline recovered',h,date.date(),flush=True)
    pd.DataFrame(differences).to_csv(DEST/'baseline_float32_affected_rows.csv',index=False)
    monthly=pd.DataFrame(months);monthly.to_csv(DEST/'baseline_float32_monthly_effect.csv',index=False)
    summary=monthly.groupby('months')[['brier_difference','five_bin_difference','crps_difference']].mean()
    summary.to_csv(DEST/'baseline_float32_score_effect.csv')
    audit=dict(recovery_matches_all_frozen_baseline_scores=True,max_frozen_score_difference=maximum,
        all_float32_atoms_bitwise_matched=True,panel_sha256=digest(PANEL),affected_probability_rows=len(differences),
        directional_decision_changes=int(monthly.direction_changes.sum()),receipts=receipts,
        scope='Frozen original B files unchanged. New component uses recovered float64 atoms; prior mixed-source provenance checked against original float32 cache. Historical score impacts descriptive, not a new candidate.')
    (DEST/'baseline_precision_audit.json').write_text(json.dumps(audit,indent=2)+'\n')
    print(json.dumps({k:v for k,v in audit.items() if k!='receipts'},indent=2))


if __name__=='__main__':recover()
