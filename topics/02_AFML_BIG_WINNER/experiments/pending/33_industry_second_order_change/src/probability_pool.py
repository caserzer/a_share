"""R12 frozen chronological prediction then separately sealed evaluation."""
import argparse,json
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.special import expit,logit
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import HistGradientBoostingClassifier
from pool_evaluation import EP,KEY,HORIZONS,sha,calendar_dates

OUT=EP/'outputs/r12'
SOURCE=EP/'outputs/r11/coverage30/evaluation_panel.parquet'
PRICE=['rate5','rate20','rate60','breadth21','breadth63','volume_ratio','vol60','market126','market_breadth_up_fraction','coverage','members']
LEVELS=PRICE+['growth','finance_coverage']
SECOND=LEVELS+['rate_change','low_count_change','breadth_change5','breadth_change20','finance_acceleration']
ARMS={'matured_base':[], 'logit_price':PRICE,'logit_levels':LEVELS,'logit_second':SECOND,'tree_levels':LEVELS,'tree_second':SECOND}

def data():
    p=pd.read_parquet(SOURCE).copy();p['eligible']=p.price_eligible
    valid=p.finance_count.ge(3)&p.finance_coverage.ge(.3)
    p.loc[~valid,['growth','finance_acceleration']]=np.nan
    return p

def date_weights(p):
    a=1/p.groupby('date').date.transform('size').to_numpy();return a/a.mean()

def split(p,cut):
    cal_start=cut-pd.DateOffset(months=18)
    eligible=p.eligible & p.win126.notna() & p.end126.notna()
    train=p[eligible&p.end126.lt(cal_start)]
    cal=p[eligible&p.date.ge(cal_start)&p.end126.lt(cut)]
    test=p[p.eligible&p.date.ge(cut)&p.date.lt(cut+pd.DateOffset(months=3))]
    assert train.end126.lt(cal_start).all() and cal.end126.lt(cut).all()
    assert not set(train.index)&set(cal.index) and not set(cal.index)&set(test.index)
    return train,cal,test,cal_start

def calibrate(raw,y,w):
    x=logit(np.clip(raw,1e-6,1-1e-6));y=np.asarray(y,float);w=np.asarray(w,float);w=w/w.sum()
    def objective(ab):
        z=ab[0]*x+ab[1];loss=np.sum(w*(np.logaddexp(0,z)-y*z))+.001*ab[0]**2
        err=w*(expit(z)-y);grad=np.array([np.sum(err*x)+.002*ab[0],err.sum()])
        return loss,grad
    fit=minimize(objective,[1.,0.],jac=True,bounds=[(0,None),(None,None)],method='L-BFGS-B')
    if not fit.success:raise RuntimeError(f'Calibration failed: {fit.message}')
    return {'slope':float(fit.x[0]),'intercept':float(fit.x[1]),'loss':float(fit.fun)}

def calibrated(raw,cal):
    return expit(cal['slope']*logit(np.clip(raw,1e-6,1-1e-6))+cal['intercept'])

def gate(prob,reference):return (prob>=.60)&(prob-reference>=.05)

def predict():
    if (OUT/'prediction_seal.json').exists():raise RuntimeError('Predictions already sealed; use a new experiment version, do not overwrite.')
    OUT.mkdir(parents=True,exist_ok=True);(OUT/'models').mkdir(exist_ok=True)
    p=data();pred=[];folds=[];indices=[];parameters=[]
    for cut in pd.date_range('2024-01-01','2026-10-01',freq='QS'):
        train,cal,test,cal_start=split(p,cut);fold=cut.strftime('%YQ')+str(cut.quarter)
        ok=min(len(train),len(cal))>=500 and min(train.date.nunique(),cal.date.nunique())>=12 and train.win126.nunique()==2 and cal.win126.nunique()==2
        folds.append(dict(fold=fold,cutoff=cut,cal_start=cal_start,train_n=len(train),cal_n=len(cal),test_n=len(test),train_dates=train.date.nunique(),cal_dates=cal.date.nunique(),train_max_label_end=train.end126.max(),cal_max_label_end=cal.end126.max(),status='FIT' if ok else 'INSUFFICIENT'))
        for role,g in [('train',train),('calibration',cal),('test',test)]:indices.append(pd.DataFrame({'fold':fold,'role':role,'row_id':g.index}))
        if not ok:continue
        for name,features in ARMS.items():
            if name=='matured_base':
                history=p[p.eligible&p.end126.lt(cut)&p.win126.notna()]
                raw=np.repeat(np.average(history.win126,weights=date_weights(history)),len(test));prob=raw
                metadata={'matured_history_n':len(history),'max_label_end':str(history.end126.max())}
                model={'constant':float(raw[0])} if len(raw) else {}
                indices.append(pd.DataFrame({'fold':fold,'role':'base_history','row_id':history.index}))
            else:
                if name.startswith('logit'):
                    estimator=LogisticRegression(C=.1,max_iter=2000,random_state=3312)
                    model=make_pipeline(SimpleImputer(strategy='median',add_indicator=True,keep_empty_features=True),StandardScaler(),estimator)
                    fitarg={'logisticregression__sample_weight':date_weights(train)}
                else:
                    estimator=HistGradientBoostingClassifier(max_iter=100,learning_rate=.05,max_leaf_nodes=7,max_depth=3,min_samples_leaf=100,l2_regularization=10,early_stopping=False,random_state=3312)
                    model=make_pipeline(SimpleImputer(strategy='median',add_indicator=True,keep_empty_features=True),estimator)
                    fitarg={'histgradientboostingclassifier__sample_weight':date_weights(train)}
                model.fit(train[features],train.win126.astype(int),**fitarg)
                params=calibrate(model.predict_proba(cal[features])[:,1],cal.win126,date_weights(cal))
                raw=model.predict_proba(test[features])[:,1];prob=calibrated(raw,params);metadata={'calibration':params,'features':features}
            joblib.dump({'model':model,'metadata':metadata},OUT/f'models/{fold}_{name}.joblib',compress=3)
            parameters.append({'fold':fold,'model':name,**metadata})
            z=test[['date','era','industry_code','industry_name','block','week_i','day_i']].copy();z['row_id']=test.index
            z['model']=name;z['fold']=fold;z['fit_cutoff']=cut;z['raw_probability']=raw;z['probability']=prob;z['score']=100*prob
            pred.append(z.reset_index(drop=True))
        print(f'{fold}: training={len(train)}, calibration={len(cal)}, prediction={len(test)} x 6',flush=True)
    result=pd.concat(pred,ignore_index=True)
    result['reference_probability']=result.groupby(['model','date']).probability.transform('mean')
    result['predicted_uplift']=result.probability-result.reference_probability
    result['admitted']=gate(result.probability,result.reference_probability)
    result.to_parquet(OUT/'sealed_predictions.parquet',index=False)
    pd.DataFrame(folds).to_csv(OUT/'folds.csv',index=False);pd.concat(indices,ignore_index=True).to_csv(OUT/'split_indices.csv.gz',index=False)
    (OUT/'model_parameters.json').write_text(json.dumps(parameters,indent=2)+'\n')
    inputs=[SOURCE,Path(__file__),EP/'configs/pool_metric_v1.json',EP/'rounds/r12_probability_score_plan.md',EP/'rounds/r12_execution_contract.md']
    seal={'stage':'PREDICTIONS_SEALED_BEFORE_EVALUATION','inputs':{str(f):sha(f) for f in inputs},'artifacts':{str(f.relative_to(OUT)):sha(f) for f in OUT.rglob('*') if f.is_file()},'future_labels_in_prediction_file':False}
    (OUT/'prediction_seal.json').write_text(json.dumps(seal,indent=2)+'\n')

def admission_events(g):
    g=g.sort_values(KEY+['date']).copy();by=g.groupby(KEY)
    continuous=g.week_i.sub(by.week_i.shift()).eq(1)
    g['entry']=g.admitted&by.admitted.shift().eq(False)&continuous
    g['boundary_unknown']=g.admitted&~continuous
    g['refit_entry']=g.entry&g.fold.ne(by.fold.shift())
    g['cooldown126']=False
    for _,a in g[g.entry].groupby(KEY):
        last=-100000
        for ix,r in a.sort_values('date').iterrows():
            if r.day_i-last>=126:g.loc[ix,'cooldown126']=True;last=r.day_i
    return g

def block_interval(z,dates,block=26):
    # z already contains only evaluable entry events; numerator and denominator resampled together.
    agg=z.groupby('date').agg(n=('delta','count'),d=('delta','sum')).reindex(dates,fill_value=0)
    n=len(agg);rng=np.random.default_rng(3312);values=[]
    for _ in range(1000):
        starts=rng.integers(0,n,int(np.ceil(n/block)));ix=((starts[:,None]+np.arange(block))%n).ravel()[:n]
        d=agg.iloc[ix];den=d.n.sum()
        if den:values.append(d.d.sum()/den)
    return tuple(np.quantile(values,[.025,.975])) if values else (np.nan,np.nan)

def evaluate():
    seal=json.loads((OUT/'prediction_seal.json').read_text())
    for f,h in seal['artifacts'].items():assert sha(OUT/f)==h,f
    for f,h in seal['inputs'].items():assert sha(f)==h,f
    p=data();pred=pd.read_parquet(OUT/'sealed_predictions.parquet');dates=calendar_dates();dates=dates[dates>=pd.Timestamp('2024-01-01')]
    labelcols=[f'{x}{h}' for h in HORIZONS for x in ['win','status','return','excess','end']]
    labelcols+=['rate20','rate60','finance_coverage']
    summary=[];annual=[];calbins=[];allrows=[];momlist=[];weekly=[];latencies=[]
    # Most recent rising early-change hint, available at the observation time only.
    history=p.sort_values(KEY+['date']).copy();hint=history.slowdown|history.improvement_acceleration
    prev=hint.groupby([history[k] for k in KEY]).shift()
    history['hint_i']=history.week_i.where(hint&prev.eq(False))
    history['hint_i']=history.groupby(KEY).hint_i.ffill();hintmap=history.hint_i
    for name,g in pred.groupby('model'):
        g=admission_events(g);g=g.merge(p[labelcols],left_on='row_id',right_index=True,how='left',validate='one_to_one')
        g['hint_delay_weeks']=g.week_i-g.row_id.map(hintmap)
        allrows.append(g)
        known=g[g.win126.notna()];brier=((known.probability-known.win126)**2).mean()
        for b,z in known.groupby(pd.cut(known.probability,np.linspace(0,1,11),include_lowest=True),observed=True):
            calbins.append(dict(model=name,scope='all_scores',bin=str(b),n=len(z),predicted=z.probability.mean(),actual=z.win126.mean()))
        for unit,flag in [('state','admitted'),('entry','entry'),('cooldown126','cooldown126')]:
            z=g[g[flag]];counts=z.groupby('date').size();countsall=counts.reindex(dates,fill_value=0)
            controls=p[p.eligible&p.date.isin(counts.index)].sort_values(['date','rate20','era','industry_code'],ascending=[True,False,True,True])
            rank=controls.groupby('date').cumcount();mom=controls[rank.lt(controls.date.map(counts))]
            momlist.append(pd.DataFrame({'model':name,'unit':unit,'row_id':mom.index}))
            for h in HORIZONS:
                col=f'win{h}';k=z[z[col].notna()].copy();base=p[p.eligible].groupby('date')[col].mean();k['reference_rate']=k.date.map(base);k['delta']=k[col]-k.reference_rate
                lo,hi=block_interval(k,dates,round(h/5))
                win=k[col].mean();delta=k.delta.mean();gap=abs(k.probability.mean()-win) if h==126 else np.nan
                recall=g.loc[g.admitted,col].sum()/g[col].sum() if g[col].sum() else np.nan
                mr=mom.groupby('date')[col].mean();mk=k.date.map(mr);momentum_delta=(k[col]-mk.to_numpy()).mean()
                row=dict(model=name,unit=unit,horizon=h,total=len(z),known=len(k),wins=int(k[col].sum()),immature=int(z[f'status{h}'].eq('IMMATURE').sum()),missing=int(z[f'status{h}'].eq('MISSING_PATH').sum()),
                    win_rate=win,reference_rate=k.reference_rate.mean(),uplift=delta,uplift_lo=lo,uplift_hi=hi,momentum_delta=momentum_delta,
                    predicted_mean=k.probability.mean() if h==126 else np.nan,calibration_gap=gap,success_week_recall=recall,brier126=brier,
                    mean_weekly_count=countsall.mean(),empty_week_fraction=countsall.eq(0).mean(),entry_dates=k.date.nunique(),
                    boundary_unknown=int(g.boundary_unknown.sum()),refit_entries=int((z.refit_entry).sum()),median_hint_delay_weeks=z.hint_delay_weeks.median(),median_rate20=z.rate20.median(),
                    unknown_lower=k[col].sum()/len(z) if len(z) else np.nan,unknown_upper=(k[col].sum()+len(z)-len(k))/len(z) if len(z) else np.nan)
                if unit=='entry' and h==126:
                    gates={'win60':win>=.60,'uplift5pp':delta>=.05,'recall10':recall>=.10,'known100':len(k)>=100,'ci_positive':lo>0,'calibration5pp':gap<=.05}
                    row['accepted']=all(gates.values());row['failed_gates']=';'.join(key for key,value in gates.items() if not value)
                summary.append(row)
                for year,a in z.groupby(z.date.dt.year):
                    q=a[a[col].notna()];annual.append(dict(model=name,unit=unit,horizon=h,year=year,total=len(a),known=len(q),wins=q[col].sum(),win_rate=q[col].mean(),uplift=(q[col]-q.date.map(base)).mean(),predicted_mean=q.probability.mean() if h==126 else np.nan))
                w=k.groupby('date').agg(known=(col,'size'),wins=(col,'sum'),reference=('reference_rate','mean'),delta=('delta','mean')).reindex(dates)
                w['pool_n']=countsall;w=w.reset_index(names='date');w['model']=name;w['unit']=unit;w['horizon']=h;weekly.append(w)
            for b,a in z[z.win126.notna()].groupby(pd.cut(z.loc[z.win126.notna(),'probability'],np.linspace(0,1,11),include_lowest=True),observed=True):
                calbins.append(dict(model=name,scope=unit,bin=str(b),n=len(a),predicted=a.probability.mean(),actual=a.win126.mean()))
    pd.DataFrame(summary).to_csv(OUT/'summary.csv',index=False);pd.DataFrame(annual).to_csv(OUT/'annual.csv',index=False)
    pd.DataFrame(calbins).to_csv(OUT/'calibration_bins.csv',index=False);pd.concat(allrows,ignore_index=True).to_parquet(OUT/'scored_outcomes.parquet',index=False)
    pd.concat(momlist,ignore_index=True).to_csv(OUT/'momentum_controls.csv.gz',index=False);pd.concat(weekly,ignore_index=True).to_csv(OUT/'weekly_metrics.csv.gz',index=False)
    (OUT/'evaluation_receipt.json').write_text(json.dumps({'stage':'EVALUATED_AFTER_PREDICTION_SEAL','prediction_seal_sha256':sha(OUT/'prediction_seal.json'),'prediction_sha256':sha(OUT/'sealed_predictions.parquet'),'code_sha256':sha(__file__),'input_sha256':sha(SOURCE),'primary_horizon':126,'independent_forward_validation':False},indent=2)+'\n')
    print(pd.DataFrame(summary).query('unit=="entry" and horizon==126')[['model','total','known','win_rate','uplift','uplift_lo','uplift_hi','success_week_recall','calibration_gap','accepted','failed_gates']].to_string(index=False))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('stage',choices=['predict','evaluate']);args=parser.parse_args()
    predict() if args.stage=='predict' else evaluate()
