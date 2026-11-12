import json,sys
from pathlib import Path
import pandas as pd,numpy as np,joblib
EP=Path(__file__).resolve().parents[2];sys.path.insert(0,str(EP/'src'))
from pool_evaluation import ID,KEY,sha
OUT=EP/'restart/p13';s=json.loads((OUT/'prediction_seal.json').read_text());assert all(sha(f)==h for f,h in s['inputs'].items());assert all(sha(OUT/f)==h for f,h in s['artifacts'].items())
p=pd.read_parquet(OUT/'training_panel.parquet');q=pd.read_parquet(OUT/'predictions.parquet');base=joblib.load(EP/'restart/p05/models/2024-01-01_B.joblib');n=0
for r in json.loads((OUT/'folds.json').read_text()):
 cut=pd.Timestamp(r['cutoff']);t=p[p.win126.notna()&p.end126.lt(cut)];assert len(t)==r['train_rows'] and t.date.nunique()==r['train_dates'];assert t.end126.max()==pd.Timestamp(r['latest_label_end'])
 b=joblib.load(OUT/'models'/f'{cut.date()}_B.joblib');assert b['features']==base['features'] and b['model'].get_params()==base['model'].get_params();z=q[q.fit_cutoff.eq(cut)].sample(20,random_state=13).merge(p[ID+b['features']],on=ID,validate='one_to_one');pred=b['model'].predict_proba(z[b['features']])[:,1];assert np.allclose(pred,z.raw_score,atol=1e-12,rtol=0);n+=len(z)
cache=Path('/home/xiaolv/.cache/a_share/ep32/forecast_v5');audit=json.loads((EP.parent/'32_industry_rotation_cycle_observation/extensions/v5_rdagent_onset_forecast/outputs/daily_input_audit.json').read_text());assert sha(cache/'daily_industries.parquet')==audit['daily_sha256']
d=pd.read_parquet(cache/'daily_industries.parquet');d=d[d.level.eq('L3')];groups={k:g.sort_values('date').set_index('date') for k,g in d.groupby(KEY)};m=pd.read_parquet(cache/'CSI_ALL.parquet').close
for _,r in p[p.date.lt('2021-01-01')&p.win126.notna()].sample(60,random_state=3313).iterrows():
 g=groups[tuple(r[k] for k in KEY)];i=g.index.get_loc(r.date);entry=i+1;end=i+127;assert g.index[end]==r.end126
 ret=g.nav.iloc[end]/g.nav.iloc[entry]-1;mr=m.loc[g.index[end]]/m.loc[g.index[entry]]-1;assert int(ret>0 and ret-mr>0)==r.win126
 x=np.log(g.nav.iloc[:i+1]/m.reindex(g.index[:i+1]));assert np.isclose(x.diff().tail(60).std(),r.vol60)
 for w in [5,20,60]:assert np.isclose((x.iloc[-1]-x.iloc[-1-w])*5/w,r[f'rate{w}'])
(OUT/'validation.json').write_text(json.dumps(dict(status='PASS',source_ep32_hash_verified=True,early_raw_feature_label_checks=60,quarter_maturity_checks=16,prediction_replay_rows=n,parameters_identical=True,all_seals_verified=True,efficacy_established=False),indent=2)+'\n');print('PASS',n,'prediction replays, 60 early raw paths');print(pd.read_csv(OUT/'comparisons.csv').to_string(index=False))
