import json,sys
from pathlib import Path
import numpy as np,pandas as pd,joblib
EP=Path(__file__).resolve().parents[2];sys.path.insert(0,str(EP/'src'))
from pool_evaluation import ID,sha
OUT=EP/'restart/p11';s=json.loads((OUT/'prediction_seal.json').read_text());assert all(sha(f)==h for f,h in s['inputs'].items());assert all(sha(OUT/f)==h for f,h in s['artifacts'].items())
p=pd.read_parquet(EP/'outputs/r11/coverage30/evaluation_panel.parquet');p=p[p.price_eligible].reset_index(drop=True);q=pd.read_parquet(OUT/'combined_predictions.parquet');old=pd.read_parquet(EP/'restart/p05/predictions.parquet');old=old[old.model.eq('B')];cols=old.columns.tolist();pd.testing.assert_frame_equal(q[q.date.ge('2024-01-01')][cols].reset_index(drop=True),old.reset_index(drop=True))
base=joblib.load(EP/'restart/p05/models/2024-01-01_B.joblib');n=0
for r in json.loads((OUT/'folds.json').read_text()):
 cut=pd.Timestamp(r['cutoff']);tr=p[p.win126.notna()&p.end126.lt(cut)];assert len(tr)==r['train'] and tr.date.nunique()==r['train_dates'];assert tr.end126.max()==pd.Timestamp(r['max_label_end'])
 bundle=joblib.load(OUT/'models'/f'{cut.date()}_B.joblib');assert bundle['features']==base['features'] and bundle['model'].get_params()==base['model'].get_params()
 z=q[q.fit_cutoff.eq(cut)];pred=bundle['model'].predict_proba(p.loc[z.sample_id,bundle['features']])[:,1];assert np.allclose(pred,z.raw_score,rtol=0,atol=1e-12);n+=len(z)
f=pd.read_csv(OUT/'quarter_support.csv',parse_dates=['cutoff','max_label_end']);assert (f.max_label_end.isna()|f.max_label_end.lt(f.cutoff)).all()
g=pd.read_parquet(OUT/'evaluated.parquet');label=pd.read_parquet(EP/'outputs/r09/evaluation_panel.parquet');g=g.merge(label[ID+['win126']],on=ID,suffixes=('','_ref'),validate='one_to_one');assert np.allclose(g.win126,g.win126_ref,equal_nan=True)
rows=[]
for year,b in g[g.edge].groupby(g[g.edge].date.dt.year):
 k=b[b.win126.notna()];ref=g.groupby('date').win126.mean();rows.append(dict(year=int(year),known=len(k),win_rate=k.win126.mean(),same_date_base=k.date.map(ref).mean(),uplift=(k.win126-k.date.map(ref)).mean()))
pd.DataFrame(rows).to_csv(OUT/'annual_edge_uplift.csv',index=False)
for _,r in pd.read_csv(OUT/'coverage_ceiling.csv').iterrows():
 cuts=f[f.unit.eq(r.unit)&f.supported].cutoff;mask=g.date.dt.to_period('Q').isin(cuts.dt.to_period('Q'));scope=g.date.ge('2024-01-01' if r.period=='original_2024' else '2023-01-01');assert g.loc[scope&mask&g.candidate,'win126'].sum()==r.successful_candidate_weeks;assert g.loc[scope,'win126'].sum()==r.all_successful_weeks
(OUT/'validation.json').write_text(json.dumps(dict(status='PASS',earlier_prediction_replay_rows=n,earlier_quarters=4,original_predictions_unchanged=True,model_parameters_unchanged=True,strict_maturity_verified=True,coverage_ceiling_checks=6,raw_label_alignment_verified=True,efficacy_established=False),indent=2)+'\n');print(pd.DataFrame(rows).to_string(index=False));print('PASS replay',n)
