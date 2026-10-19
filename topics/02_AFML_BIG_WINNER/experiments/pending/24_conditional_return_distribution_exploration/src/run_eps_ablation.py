"""R19 fixed models: original earnings-growth control and disclosed forecasts."""
import json
import numpy as np
import pandas as pd
from sklearn.neighbors import NearestNeighbors
from catboost import CatBoostClassifier
from prepare_panel import OUT
from fetch_eps_reports import DEST
from build_eps_panel import PANEL
from run_improvement_round1 import normalize_features,class_distribution
from run_prequential_search import load_distribution,combine_distributions
from run_direct_probability import classes,weighted_stats
from run_four_horizons import GRID

GROUPS={
    'eps_historical_control':('eps_positive','historical_log_growth','forward_log_anchor12'),
    'eps_forecast_capped':('eps_positive','eps_capped_log_growth','eps_capped_anchor'),
    'eps_forecast_raw':('eps_positive','eps_log_growth','eps_raw_anchor'),
    'earnings_forecast_raw':('earnings_positive','earnings_log_growth','earnings_raw_anchor'),
}
CLASS_COLS=['vol63','log_cap','pe_percentile','relative_mom63','credit_spread_3y','credit_change63',
            'earnings_log_growth','earnings_raw_anchor','forecast_age_days','forecast_next_loss','forecast_basis_profit']


def run():
    panel=pd.read_parquet(PANEL);panel=panel[panel.common_eligible]
    audits=[]
    for h in [1,3,6]:
        base=pd.read_parquet(OUT/f'r15_three_factor_ablation/predictions_{h}m.parquet')
        base=base[base.model=='B'];results=[]
        for date,test in panel[panel.date>='2021-01-01'].groupby('date',sort=True):
            test=test.reset_index(drop=True)
            train=panel[(panel[f'end_{h}']<date)&panel[f'y_{h}'].notna()]
            b=base[base.date==date].reset_index(drop=True)
            pd.testing.assert_frame_equal(b[['date','instrument']],test[['date','instrument']])
            atoms,weights=load_distribution(OUT/'local_cache/r15_distributions',h,date,'B',test[['date','instrument']])
            globalq=np.quantile(train[f'y_{h}'],GRID)
            for name,(available,growth,anchor) in GROUPS.items():
                fit=train[train[available]];mask=test[available].to_numpy()
                r=b.copy();r['model']=name;active=bool(len(fit)>=1000 and mask.any())
                if active:
                    cols=['vol63','log_cap',growth,anchor,'forecast_age_days']
                    x,z=normalize_features(fit,test.loc[mask],cols)
                    indices=NearestNeighbors(n_neighbors=min(1000,len(fit)),n_jobs=1).fit(x).kneighbors(z,return_distance=False)
                    y=fit[f'y_{h}'].to_numpy()
                    new=.75*np.quantile(y[indices],GRID,axis=1).T+.25*globalq
                    a,w=combine_distributions([(atoms[mask],weights[mask]),(new,np.full_like(new,1/len(GRID)))],[.5,.5])
                    stats=weighted_stats(a,w,r.loc[mask,'actual']);r.loc[mask,stats.columns]=stats.to_numpy()
                results.append(r)
                audits.append(dict(months=h,date=str(date.date()),model=name,training_rows=len(fit),
                    last_training_label=str(fit[f'end_{h}'].max()),test_rows=len(test),adjusted_rows=int(mask.sum()) if active else 0))
            name='earnings_forecast_classes';fit=train[train.earnings_pair_available];mask=test.earnings_pair_available.to_numpy()
            r=b.copy();r['model']=name;active=bool(len(fit)>=1000 and mask.any())
            if active:
                y=fit[f'y_{h}'].to_numpy();c=classes(y)
                model=CatBoostClassifier(loss_function='MultiClass',iterations=100,depth=2,learning_rate=.03,
                    l2_leaf_reg=20,random_seed=24,thread_count=4,verbose=False,allow_writing_files=False)
                model.fit(fit[CLASS_COLS],c)
                prob=np.zeros((int(mask.sum()),7));prob[:,model.classes_.astype(int)]=model.predict_proba(test.loc[mask,CLASS_COLS])
                a,w=class_distribution(y,c,prob)
                a,w=combine_distributions([(atoms[mask],weights[mask]),(a,w)],[.5,.5])
                stats=weighted_stats(a,w,r.loc[mask,'actual']);r.loc[mask,stats.columns]=stats.to_numpy()
            results.append(r)
            audits.append(dict(months=h,date=str(date.date()),model=name,training_rows=len(fit),
                last_training_label=str(fit[f'end_{h}'].max()),test_rows=len(test),adjusted_rows=int(mask.sum()) if active else 0))
            assert train[f'end_{h}'].max()<date
            print(h,date.date(),'earnings_train',len(fit),'test',int(mask.sum()),flush=True)
        pd.concat(results,ignore_index=True).to_parquet(DEST/f'predictions_{h}m.parquet',index=False)
    pd.DataFrame(audits).to_csv(DEST/'fit_audit.csv',index=False)
    (DEST/'spec.json').write_text(json.dumps(dict(groups=GROUPS,class_features=CLASS_COLS,
        baseline='unchanged frozen R15 B, same 27600 stock-date predictions per horizon',
        earnings_source='latest known original report, explicit fiscal-year forecast pairs',
        eps_comparison='first three variants use identical EPS-positive train/query rows; only growth/anchor inputs differ',
        raw_growth='no fixed 30 percent cap; peer inputs use training-only median/IQR and clip to 5 IQR units',
        fallback='exact B where no features or training rows <1000',prior_weight=.5,
        evidence='repeated retrospective exploration; not an independent holdout'),indent=2)+'\n')


if __name__=='__main__':run()
