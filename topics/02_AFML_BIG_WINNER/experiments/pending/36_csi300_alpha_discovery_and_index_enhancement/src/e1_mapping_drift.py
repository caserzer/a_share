"""Exact model/data mapping decomposition and engineered-feature residual audit.
Counterfactual future-model/old-data cells are descriptive, never trade signals.
"""
import sys,json,pickle,__main__
from pathlib import Path
from datetime import datetime,timezone
import numpy as np,pandas as pd
from common import EP,OUT,PRIVATE,sha,save_json
from e1_past_style_copy import features_only
from e1_mechanism import standard,bootstrap
from alpha_falsification import project,rankcorr
from train import TrainTransform
__main__.TrainTransform=TrainTransform
RUN='e1_mapping_drift_20261117';D=OUT/'diagnostics'/RUN;L=PRIVATE/RUN;R=EP/'reports'/RUN
OLD='e1_alpha_mechanism_20261117';PAST='e1_past_style_copy_20261117';END=pd.Timestamp('2025-03-03')
from alpha_economics import STYLES

def write(a,name,private=False):
 p=(L if private else D)/name;p.parent.mkdir(parents=True,exist_ok=True)
 if name.endswith('.parquet'):a.to_parquet(p,index=False)
 else:a.to_csv(p,index=False)
def record(paths):return [dict(path=str(p),sha256=sha(p)) for p in paths]
def verify(name='freeze'):
 r=json.loads((D/(name+'.json')).read_text())
 for p in r['files']:assert sha(p['path'])==p['sha256'],p['path']
 return r

def demean(y,industry):
 out=np.asarray(y,float).copy()
 for ind in sorted(set(industry)):
  ix=np.asarray(industry)==ind;out[ix]-=out[ix].mean(axis=0)
 return out

def split_change(g00,g10,g01,g11,xnew):
 """Two-factor symmetric allocation evaluated in new-data prediction space."""
 model=.5*((g10-g00)+(g11-g01));data=.5*((g01-g00)+(g11-g10))
 total=xnew@(g11-g00);m=xnew@model;d=xnew@data
 return total,m,d

def freeze():
 D.mkdir(parents=True,exist_ok=True);L.mkdir(parents=True,exist_ok=True);R.mkdir(parents=True,exist_ok=True);assert not (D/'freeze.json').exists()
 cfg=dict(run=RUN,at=datetime.now(timezone.utc).isoformat(),new_results_seen=False,old_results_seen=True,scope='same scored interval as past-style-copy, through2025-03-03',objects=['adjacent original weekly signals','fixed first scored date anchor'],universes=['native C each date','intersection of old and new C stocks'],mapping='industry-demeaned13 date-standardized styles X; teacher is global-standardized model score then industry-demeaned; gamma=lstsq(X,y,rcond1e-12)',cells='g00 old model old data;g10 new model old data;g01 old model new data;g11 new model new data',decomposition='symmetric two-factor allocation of gamma change, evaluated using Xnew; additive model and data score changes; signed projection share dot(component,total)/dot(total,total), not positive variance shares',model_factor='entire frozen Ridge bundle: coefficients, training mean/sd and median imputation',data_factor='features,style covariance,date standardization,industry composition and stock pool; common-stock sensitivity excludes entry/exit only',residual='original78 transformed feature contributions grouped by existing frozen mapping; divide by full score SD then industry demean, project on13-style X; residual group contributions sum to total unexplained score',anchor='first scored signal from prior past-copy experiment; fixed original Ridge bundle applied to later features, no refit',auxiliary='H10 RankIC original, frozen78-model, explained13 and residual13; no portfolio or new return model; historical descriptive blocks13weeks5000',prohibitions=['new training','window/threshold search','counterfactual new model on old data called tradable','coefficient Euclidean norms claimed economic shares','residual score attribution claimed profit attribution'])
 cp=EP/'configs'/(RUN+'.json');assert not cp.exists();save_json(cp,cfg)
 receipts=json.loads((OUT/'manifests/expanding_predictions.json').read_text())
 files=[cp,Path(__file__),PRIVATE/OLD/'scores.parquet',PRIVATE/PAST/'scores.parquet',PRIVATE/'features.parquet',PRIVATE/'labels.parquet',OUT/'diagnostics'/OLD/'feature_groups.csv',OUT/'manifests/expanding_predictions.json']
 files += [Path(m['path']) for rec in receipts for m in rec['models'] if m['model']=='E1']
 files += [EP/'src'/s for s in ['train.py','e1_past_style_copy.py','e1_mechanism.py','alpha_falsification.py','common.py']]
 save_json(D/'freeze.json',dict(files=record(files),future_returns_read=False));print('FROZEN',flush=True)

def load():
 frame=pd.read_parquet(PRIVATE/OLD/'scores.parquet');frame=frame[frame.signal_date<=END].sort_values(['signal_date','instrument'])
 f=pd.read_parquet(PRIVATE/'features.parquet').set_index(['signal_date','instrument']);dictionary=pd.read_csv(OUT/'diagnostics'/OLD/'feature_groups.csv');cols=dictionary.feature.tolist()
 models={}
 for rec in json.loads((OUT/'manifests/expanding_predictions.json').read_text()):
  m=next(m for m in rec['models'] if m['model']=='E1');assert sha(m['path'])==m['sha256'];models[rec['fold']]=pickle.loads(Path(m['path']).read_bytes())
 days={}
 for date,g in frame.groupby('signal_date'):
  g=g.reset_index(drop=True);raw=f.loc[pd.MultiIndex.from_frame(g[['signal_date','instrument']]),cols].reset_index(drop=True);days[date]=(g,raw)
 return days,models,dictionary

def cell(bundle,g,raw):
 transform,model=bundle;score=model.predict(transform.transform(raw));sd=score.std()
 if sd<1e-12:raise ValueError('unidentifiable constant teacher')
 x=features_only(g[STYLES+['industry']]);y=demean(standard(score),g.industry)
 gamma=np.linalg.lstsq(x,y,rcond=1e-12)[0]
 return gamma,x,y,score

def prepare():
 verify();assert not (D/'structure_complete.json').exists();days,models,dictionary=load();all_dates=sorted(days);start=pd.read_parquet(PRIVATE/PAST/'scores.parquet').signal_date.min();dates=[d for d in all_dates if d>=start];anchor=dates[0];anchor_model=models[str(anchor.to_period('Q'))];pairrows=[];vectors=[];score_rows=[];group_rows=[];replay=[];coefrows=[]
 for date in dates:
  g,raw=days[date];bundle=models[str(date.to_period('Q'))];gamma,x,y,score=cell(bundle,g,raw);error=float(np.max(abs(score-g.E1.to_numpy())));assert error<1e-10
  transform,model=bundle;contrib=transform.transform(raw)*model.coef_;sd=score.std();explained=x@gamma;residual=y-explained;energy=float(residual@residual);total=float(y@y)
  locked=anchor_model[1].predict(anchor_model[0].transform(raw))
  row=g[['signal_date','instrument','industry']].copy();row['E1']=score;row['FIXED78']=locked;row['EXPLAINED13']=explained;row['RESIDUAL13']=residual;row['industry_teacher']=y;score_rows.append(row)
  replay.append(dict(signal_date=date,max_error=error,n=len(g),industry_score_energy=total,residual_energy=energy,r2=1-energy/total,raw_rank_fixed78=rankcorr(score,locked),industry_rank_fixed78=rankcorr(demean(standard(score),g.industry),demean(standard(locked),g.industry))))
  summed=np.zeros(len(g));groupdetails=[]
  for group in dictionary.mechanism_group.unique():
   yg=demean(contrib[:,dictionary.mechanism_group.eq(group)].sum(axis=1)/sd,g.industry);rg=yg-project(x,yg)[0];summed+=rg
   group_rows.append(dict(signal_date=date,group=group,residual_energy=float(rg@rg),signed_residual_allocation=float(rg@residual),total_residual_energy=energy,share=float(rg@residual/energy) if energy else np.nan))
   groupdetails.append((group,rg))
  assert np.allclose(summed,residual,atol=1e-10)
  for group,rg in groupdetails:row['residual_'+group]=rg
  for j,s in enumerate(STYLES):coefrows.append(dict(signal_date=date,style=s,projection_coefficient=gamma[j]))
  comparisons=[('adjacent',all_dates[all_dates.index(date)-1])]
  if date>anchor:comparisons.append(('anchor',anchor))
  for clock,old in comparisons:
   oldg,oldraw=days[old];oldmodel=models[str(old.to_period('Q'))]
   for scope in ['native','common']:
    a,b=oldg, g;ar,br=oldraw,raw
    if scope=='common':
     common=set(oldg.instrument)&set(g.instrument);ix=oldg.instrument.isin(common);jx=g.instrument.isin(common);a=oldg.loc[ix].reset_index(drop=True);ar=oldraw.loc[ix].reset_index(drop=True);b=g.loc[jx].reset_index(drop=True);br=raw.loc[jx].reset_index(drop=True)
    g00,_,_,_=cell(oldmodel,a,ar);g10,_,_,_=cell(bundle,a,ar);g01,xnew,_,_=cell(oldmodel,b,br);g11,_,_,_=cell(bundle,b,br)
    delta,mc,dc=split_change(g00,g10,g01,g11,xnew);err=float(np.max(abs(delta-mc-dc)));assert err<1e-10;en=float(np.mean(delta**2));ma=float(np.mean(mc*delta));da=float(np.mean(dc*delta));same=str(old.to_period('Q'))==str(date.to_period('Q'))
    if same:assert np.max(abs(mc))<1e-10
    pairrows.append(dict(clock=clock,scope=scope,old_date=old,new_date=date,n_old=len(a),n_new=len(b),model_changed=not same,change_energy=en,model_allocation=ma,data_allocation=da,model_component_energy=float(np.mean(mc**2)),data_component_energy=float(np.mean(dc**2)),reconciliation_error=err))
    for j,s in enumerate(STYLES):vectors.append(dict(clock=clock,scope=scope,old_date=old,new_date=date,style=s,g00=g00[j],g10=g10[j],g01=g01[j],g11=g11[j]))
  if len(replay)%30==0:print('structure',len(replay),len(dates),flush=True)
 write(pd.concat(score_rows),'score_components.parquet',True);write(pd.DataFrame(pairrows),'mapping_decomposition.csv');write(pd.DataFrame(vectors),'mapping_cells.csv');write(pd.DataFrame(group_rows),'residual_groups.csv');write(pd.DataFrame(replay),'replay.csv');write(pd.DataFrame(coefrows),'projection_coefficients.csv')
 verify();save_json(D/'structure_complete.json',dict(files=record(list(D.glob('*.csv'))+[L/'score_components.parquet']),anchor_signal=str(anchor),future_returns_read=False));print('STRUCTURE SEALED',flush=True)

def evaluate():
 verify();verify('structure_complete');assert not (D/'analysis_complete.json').exists();pairs=pd.read_csv(D/'mapping_decomposition.csv');groups=pd.read_csv(D/'residual_groups.csv');scores=pd.read_parquet(L/'score_components.parquet');labels=pd.read_parquet(PRIVATE/'labels.parquet')[['signal_date','instrument','h10','h10_mature']];scores=scores.merge(labels,on=['signal_date','instrument'],validate='one_to_one');rows=[]
 cols=['E1','FIXED78','EXPLAINED13','RESIDUAL13']+[c for c in scores if c.startswith('residual_')]
 for date,g in scores.groupby('signal_date'):
  g=g[g.h10.notna()&(g.h10_mature<=END)]
  for s in cols:
   raw_ic=rankcorr(g[s],g.h10) if len(g)>2 else np.nan
   sector=[];weights=[]
   for ind,a in g.groupby('industry'):
    ic=rankcorr(a[s],a.h10) if len(a)>=3 else np.nan
    if np.isfinite(ic):sector.append(ic);weights.append(len(a))
   rows.append(dict(signal_date=date,score=s,n=len(g),rank_ic=raw_ic,industry_ic=np.average(sector,weights=weights) if weights else np.nan))
 write(pd.DataFrame(rows),'rank_ic.csv');stats=[]
 for s,g in pd.DataFrame(rows).groupby('score'):
  for metric in ['rank_ic','industry_ic']:stats.append(dict(score=s,metric=metric,**bootstrap(g.set_index('signal_date')[metric],'W-FRI',13)))
 write(pd.DataFrame(stats),'ranking_statistics.csv');summ=[]
 for (clock,scope),g in pairs.groupby(['clock','scope']):
  for sample,a in [('all',g),('model_change_only',g[g.model_changed])]:
   total=a.change_energy.sum();summ.append(dict(clock=clock,scope=scope,sample=sample,pairs=len(a),change_energy_sum=total,model_share=a.model_allocation.sum()/total if total else np.nan,data_share=a.data_allocation.sum()/total if total else np.nan))
 write(pd.DataFrame(summ),'decomposition_summary.csv');gr=groups.groupby('group').agg(signed_allocation=('signed_residual_allocation','sum'),own_energy=('residual_energy','sum'),total_residual_energy=('total_residual_energy','sum')).reset_index();gr['signed_share']=gr.signed_allocation/gr.total_residual_energy;write(gr,'residual_group_summary.csv')
 checks=[]
 def check(n,ok):assert bool(ok),n;checks.append(dict(name=n,passed=True))
 for row in pairs.itertuples():check(str(row.clock)+str(row.scope)+str(row.new_date)+' mapping closure',abs(row.model_allocation+row.data_allocation-row.change_energy)<1e-10 and row.reconciliation_error<1e-10)
 check('residual group allocation sum',abs(gr.signed_share.sum()-1)<1e-10);check('model constant within quarters',pairs.loc[~pairs.model_changed,'model_component_energy'].max()<1e-20);check('all original score replay',pd.read_csv(D/'replay.csv').max_error.max()<1e-10)
 save_json(D/'validation.json',dict(status='PASS',count=len(checks),checks=checks));verify();verify('structure_complete');save_json(D/'analysis_complete.json',dict(files=record(list(D.glob('*.csv'))+[D/'validation.json']),status='DESCRIPTIVE_MAPPING_DIAGNOSTIC_COMPLETE',no_returns_model_fitted=True));print(pd.DataFrame(summ).to_string(index=False));print(gr.to_string(index=False));print(pd.DataFrame(stats).query("score in ['E1','FIXED78','EXPLAINED13','RESIDUAL13'] and metric=='rank_ic'").to_string(index=False))

if __name__=='__main__':globals()[sys.argv[1]]()
