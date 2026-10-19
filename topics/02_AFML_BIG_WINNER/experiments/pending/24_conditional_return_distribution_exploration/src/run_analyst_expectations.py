"""R18: dated analyst targets and attention, evaluated on the unchanged population."""
import json
import numpy as np
import pandas as pd
from sklearn.neighbors import NearestNeighbors
from catboost import CatBoostClassifier
from prepare_panel import OUT
from fetch_historical_reports import DEST
from build_analyst_features import PANEL, FACTORS
from run_improvement_round1 import normalize_features, class_distribution
from run_prequential_search import load_distribution, combine_distributions
from run_direct_probability import classes, weighted_stats
from run_four_horizons import GRID

GROUPS = {
    'analyst_attention_peers': ('analyst_available', ['analyst_rating', 'analyst_attention', 'analyst_coverage']),
    'analyst_target_peers': ('target_available', ['target_upside']),
    'analyst_full_peers': ('target_available', FACTORS),
}


def run():
    panel = pd.read_parquet(PANEL); panel = panel[panel.common_eligible].copy()
    audits = []
    for h in [1, 3, 6]:
        b = pd.read_parquet(OUT / f'r15_three_factor_ablation/predictions_{h}m.parquet')
        b = b[b.model == 'B'].copy()
        rows = []
        for date, test in panel[panel.date >= '2021-01-01'].groupby('date', sort=True):
            test = test.reset_index(drop=True)
            train = panel[(panel[f'end_{h}'] < date) & panel[f'y_{h}'].notna()]
            base = b[b.date == date].reset_index(drop=True)
            pd.testing.assert_frame_equal(base[['date','instrument']],test[['date','instrument']])
            atoms, weights = load_distribution(OUT / 'local_cache/r15_distributions',h,date,'B',test[['date','instrument']])
            globalq = np.quantile(train[f'y_{h}'],GRID)
            for name,(available,extra) in GROUPS.items():
                fit = train[train[available]]
                mask = test[available].to_numpy()
                r = base.copy(); r['model'] = name
                active = bool(len(fit) >= 1000 and mask.any())
                if active:
                    cols = ['vol63','log_cap'] + extra
                    x,z = normalize_features(fit,test.loc[mask],cols)
                    neighbors = NearestNeighbors(n_neighbors=min(1000,len(fit)),n_jobs=1).fit(x).kneighbors(z,return_distance=False)
                    y = fit[f'y_{h}'].to_numpy()
                    peer = .75*np.quantile(y[neighbors],GRID,axis=1).T + .25*globalq
                    mixed_a,mixed_w = combine_distributions([(atoms[mask],weights[mask]),(peer,np.full_like(peer,1/len(GRID)))],[.5,.5])
                    stats = weighted_stats(mixed_a,mixed_w,r.loc[mask,'actual'])
                    r.loc[mask,stats.columns] = stats.to_numpy()
                rows.append(r)
                audits.append(dict(months=h,date=str(date.date()),model=name,training_rows=len(fit),
                    last_training_label=str(fit[f'end_{h}'].max()),predicted_rows=len(test),
                    adjusted_rows=int(mask.sum()) if active else 0,fallback_rows=len(test)-(int(mask.sum()) if active else 0)))
            name = 'analyst_target_classes'
            fit = train[train.target_available];mask = test.target_available.to_numpy()
            r = base.copy();r['model'] = name
            active = bool(len(fit)>=1000 and mask.any())
            if active:
                cols = ['vol63','log_cap','pe_percentile','relative_mom63']+FACTORS
                y = fit[f'y_{h}'].to_numpy();c = classes(y)
                # The same shallow fixed architecture as R16, now with dated analyst information.
                model = CatBoostClassifier(loss_function='MultiClass',iterations=100,depth=2,
                    learning_rate=.03,l2_leaf_reg=20,random_seed=24,thread_count=4,verbose=False,allow_writing_files=False)
                model.fit(fit[cols],c)
                prob = np.zeros((int(mask.sum()),7));prob[:,model.classes_.astype(int)] = model.predict_proba(test.loc[mask,cols])
                new_a,new_w = class_distribution(y,c,prob)
                mixed_a,mixed_w = combine_distributions([(atoms[mask],weights[mask]),(new_a,new_w)],[.5,.5])
                stats = weighted_stats(mixed_a,mixed_w,r.loc[mask,'actual'])
                r.loc[mask,stats.columns] = stats.to_numpy()
            rows.append(r)
            audits.append(dict(months=h,date=str(date.date()),model=name,training_rows=len(fit),
                last_training_label=str(fit[f'end_{h}'].max()),predicted_rows=len(test),
                adjusted_rows=int(mask.sum()) if active else 0,fallback_rows=len(test)-(int(mask.sum()) if active else 0)))
            assert train[f'end_{h}'].max()<date
            print(h,date.date(),'target_train',len(fit),'target_test',int(mask.sum()),flush=True)
        pd.concat(rows,ignore_index=True).to_parquet(DEST/f'predictions_{h}m.parquet',index=False)
    pd.DataFrame(audits).to_csv(DEST/'fit_audit.csv',index=False)
    (DEST/'spec.json').write_text(json.dumps(dict(groups=GROUPS,prior_weight=.5,minimum_training_rows=1000,
        horizon_months=[1,3,6],class_model='100 trees, depth2, learning rate .03, l2=20, seed24',
        fallback='exact frozen B predictions where unavailable; no stock-date dropped',
        source='historical report targets and ratings, not original EPS or complete consensus',
        evidence='retrospective repeated exploration on unchanged R16 target contract'),indent=2)+'\n')


if __name__=='__main__':run()
