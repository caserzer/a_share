import sys,json
from pathlib import Path
import numpy as np,pandas as pd
EP=Path(__file__).resolve().parents[2];sys.path.insert(0,str(EP/'src'))
from pool_evaluation import sha
OUT=EP/'restart/p07';s=json.loads((OUT/'prediction_seal.json').read_text());assert all(sha(f)==h for f,h in s['inputs'].items());assert sha(OUT/'sealed_date_predictions.csv')==s['predictions_sha256']
p=pd.read_parquet(EP/'outputs/r11/coverage30/evaluation_panel.parquet');p=p[p.price_eligible];d=pd.read_csv(OUT/'sealed_date_predictions.csv',parse_dates=['date','latest_history_date','latest_label_end']);assert (d.latest_label_end<d.date).all()
for _,r in d.iterrows():
 hist=p[p.end126.lt(r.date)&p.win126.notna()];v=hist.groupby('date').win126.mean().sort_index();assert len(hist)==r.history_rows and len(v)==r.history_dates;assert np.isclose(v.mean(),r.history_expanding);assert np.isclose(v.tail(26).mean(),r.history_recent26)
b=pd.read_csv(OUT/'brier_decomposition.csv');assert np.allclose(b.total,b.date_mean_error+b.centered_error)
(OUT/'validation.json').write_text(json.dumps(dict(status='PASS',date_history_checks=len(d),strict_maturity=True,decomposition_dates=len(b),seal_verified=True,event_source_sha256=sha(EP/'restart/p06/evaluated.parquet'),max_abs_known_vs_all_score_mean=float(b.known_vs_all_score_mean.abs().max()),efficacy_established=False),indent=2)+'\n')
print('PASS',len(d),'date-history reconstructions;',len(b),'decompositions');print(pd.read_csv(OUT/'event_components.csv').to_string(index=False))
