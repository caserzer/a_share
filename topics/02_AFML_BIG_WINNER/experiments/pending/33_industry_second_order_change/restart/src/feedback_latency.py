import sys,json
from pathlib import Path
import pandas as pd,numpy as np
EP=Path(__file__).resolve().parents[2];sys.path.insert(0,str(EP/'src'))
from pool_evaluation import sha
OUT=EP/'restart/p43';OUT.mkdir(exist_ok=True);assert not (OUT/'receipt.json').exists()
f=EP/'restart/p30/training_panel.parquet';ff=EP/'restart/p30/folds.csv';mf=Path('/home/xiaolv/.cache/a_share/ep32/forecast_v5/CSI_ALL.parquet')
p=pd.read_parquet(f,columns=['era','industry_code','date','eligible','new_win126','new_end126']);p=p[p.eligible];p['label_available']=p.new_win126.notna();p=p.drop(columns='new_win126');cal=pd.DatetimeIndex(pd.read_parquet(mf).index).sort_values();old=pd.read_csv(ff);rows=[];mix=[]
for _,o in old.iterrows():
 cut=pd.Timestamp(o.cutoff);tr=p[p.label_available&p.new_end126.lt(cut)];n=tr.groupby('date').date.transform('size');w=1/n;w=w/w.sum()
 assert len(tr)==o.train_rows and tr.date.nunique()==o.train_dates and tr.new_end126.max()==pd.Timestamp(o.last_end)
 rows.append(dict(cutoff=str(cut.date()),train_rows=len(tr),train_dates=tr.date.nunique(),latest_signal=str(tr.date.max().date()),latest_label_end=str(tr.new_end126.max().date()),latest_signal_age_sessions=int(cal.searchsorted(cut)-cal.searchsorted(tr.date.max())),same_year_signal_dates=int(tr.loc[tr.date.dt.year.eq(cut.year),'date'].nunique()),same_year_date_weight=float(w[tr.date.dt.year.eq(cut.year)].sum()),sw2021_weight=float(w[tr.era.eq('SW2021')].sum())))
 for year in sorted(tr.date.dt.year.unique()):mix.append(dict(cutoff=str(cut.date()),signal_year=int(year),date_weight=float(w[tr.date.dt.year.eq(year)].sum())))
r=pd.DataFrame(rows);r.to_csv(OUT/'quarterly_feedback.csv',index=False);pd.DataFrame(mix).to_csv(OUT/'training_year_weights.csv',index=False)
a=p[p.date.dt.year.eq(2023)&p.label_available].sort_values(['new_end126','date']);first=a.iloc[0];info=dict(first_2023_signal=str(first.date.date()),earliest_2023_label_end=str(first.new_end126.date()),first_quarter_cut_after_label=str(r.loc[pd.to_datetime(r.cutoff).gt(first.new_end126),'cutoff'].iloc[0]))
(OUT/'receipt.json').write_text(json.dumps(dict(status='PASS',reconciled_folds=len(rows),outcomes_not_used_beyond_availability=True,first_2023=info,inputs={str(x):sha(x) for x in [f,ff,mf,Path(__file__),EP/'restart/P43_feedback_latency_plan.md']},artifacts={x.name:sha(x) for x in OUT.iterdir() if x.is_file()}),indent=2)+'\n');print(r.to_string(index=False));print(info)
