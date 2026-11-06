"""Restricted feature compiler and evaluator; LLM cannot edit labels or splits."""
import json
import pickle
import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.metrics import average_precision_score
from lightgbm import LGBMClassifier
from common import CACHE, OUT, FEATURES, BENCHMARKS, THRESHOLDS, js, finite_json, sha

BASELINES = {
    'prior':dict(model='prior',features=FEATURES,engineered=[]),
    'logistic':dict(model='logistic',features=FEATURES,engineered=[],C=.1),
    'static_tree':dict(model='lightgbm',features=FEATURES,engineered=[],trees=120,
                       leaves=7,max_depth=3,min_child_samples=150,learning_rate=.03,reg_lambda=10.),
}
_SEARCH = {}


def validate_spec(s):
    assert isinstance(s,dict) and s['model'] in ['prior','logistic','lightgbm']
    assert set(s)<= {'model','features','engineered','C','trees','leaves','max_depth','min_child_samples','learning_rate','reg_lambda'}
    allowed=set(FEATURES)
    assert len(s.get('engineered',[]))<=8
    for e in s.get('engineered',[]):
        assert set(e)=={'name','op','left','right'}
        assert e['name'].isidentifier() and e['name'] not in allowed
        assert e['op'] in ['add','sub','mul','div','abs','square']
        for k in ['left','right']:
            assert (isinstance(e[k],str) and e[k] in allowed) or (isinstance(e[k],(float,int)) and abs(e[k])<=100)
        allowed.add(e['name'])
    assert 2<=len(s['features'])<=31 and set(s['features'])<=allowed and len(s['features'])==len(set(s['features']))
    for k,lo,hi,default in [('C',.001,10,.1),('trees',30,240,120),('leaves',3,15,7),
         ('max_depth',2,5,3),('min_child_samples',50,1000,150),('learning_rate',.01,.1,.03),('reg_lambda',0,100,10)]:
        assert lo<=s.get(k,default)<=hi,(k,s.get(k))
    return s


def compile_features(frame,spec):
    validate_spec(spec);f=frame[FEATURES].copy()
    for e in spec.get('engineered',[]):
        a=f[e['left']] if isinstance(e['left'],str) else e['left']
        b=f[e['right']] if isinstance(e['right'],str) else e['right']
        with np.errstate(divide='ignore',invalid='ignore',over='ignore'):
            v={'add':lambda:a+b,'sub':lambda:a-b,'mul':lambda:a*b,
               'div':lambda:a/(np.abs(b)+1e-4),'abs':lambda:np.abs(a),'square':lambda:a*a}[e['op']]()
        f[e['name']]=v
    return f[spec['features']].replace([np.inf,-np.inf],np.nan).clip(-100,100)


def date_weights(f):
    w=1/f.groupby(['date','level']).date.transform('size').to_numpy(float)
    return w/w.mean()


def fit_predict(train,test,spec):
    assert train.y.notna().all()
    weights=date_weights(train);prior=float(np.average(train.y,weights=weights))
    if spec['model']=='prior' or train.y.nunique()<2:
        return np.full(len(test),prior),prior
    x=compile_features(train,spec);z=compile_features(test,spec)
    if spec['model']=='logistic':
        m=make_pipeline(SimpleImputer(strategy='median',add_indicator=True,keep_empty_features=True),
            StandardScaler(),LogisticRegression(C=spec.get('C',.1),max_iter=600,random_state=32))
        m.fit(x,train.y,logisticregression__sample_weight=weights)
    else:
        m=LGBMClassifier(n_estimators=int(spec.get('trees',120)),num_leaves=int(spec.get('leaves',7)),
            max_depth=int(spec.get('max_depth',3)),min_child_samples=int(spec.get('min_child_samples',150)),
            learning_rate=spec.get('learning_rate',.03),reg_lambda=spec.get('reg_lambda',10),
            n_jobs=1,verbosity=-1,random_state=32,deterministic=True,force_col_wise=True)
        m.fit(x,train.y,sample_weight=weights)
    return np.clip(m.predict_proba(z)[:,1],1e-6,1-1e-6),prior


def task_frames(stage='a'):
    f=pd.read_parquet(CACHE/'features.parquet');f=f[f.features_ready].copy()
    path=CACHE/('labels.parquet' if stage=='a' else 'stage_b_labels.parquet')
    labels=pd.read_parquet(path)
    for bm in BENCHMARKS:
        b=pd.read_parquet(CACHE/f'{bm}.parquet').close
        g=f.copy()
        for w in [21,63,126,252]:
            ret=b/b.shift(w)-1
            g[f'excess{w}']=g[f'mom{w}']-g.date.map(ret)
            if w!=252:g[f'market{w}']=g.date.map(ret)
        for threshold in THRESHOLDS:
            lab=labels[labels.threshold.eq(threshold)&labels.benchmark.eq(bm)]
            h=g.merge(lab,on='row_id',validate='one_to_one')
            for frequency,sub in h.groupby('frequency'):
                yield (frequency,threshold,bm),sub.reset_index(drop=True)


def prepare_search(stage='a'):
    tasks={};audit=[]
    for key,g in task_frames(stage):
        train=g[g.date.lt('2021-01-01')&g.label_available_at.lt('2021-01-01')&g.y.notna()].copy()
        feedback=g[g.date.ge('2021-01-01')&g.date.lt('2023-01-01')&g.label_available_at.lt('2024-01-01')&g.y.notna()].copy()
        assert train.label_available_at.max()<pd.Timestamp('2021-01-01')
        assert not set(train.row_id)&set(feedback.row_id)
        tasks[key]=(train,feedback)
        audit.append(dict(frequency=key[0],threshold=key[1],benchmark=key[2],train=len(train),
            train_positive=int(train.y.sum()),feedback=len(feedback),feedback_positive=int(feedback.y.sum()),
            train_latest_label=str(train.label_available_at.max()),feedback_latest_origin=str(feedback.date.max())))
    p=CACHE/f'stage_{stage}_search.pkl'
    with p.open('wb') as handle:pickle.dump(tasks,handle)
    js(OUT/f'stage_{stage}/search_audit.json',dict(tasks=audit,search_data_sha256=sha(p),
        training_label_cutoff='2021-01-01 exclusive',feedback_origin_end='2022-12-31',feedback_maturity_cutoff='2024-01-01 exclusive'))


def metric_rows(f):
    rows=[]
    for level,g in f.groupby('level'):
        w=date_weights(g);y=g.y.to_numpy(float);p=g.prob.to_numpy(float)
        bs=float(np.average((y-p)**2,weights=w));null=float(np.average((y-g.prior)**2,weights=w))
        # Alert ranking is determined before dropping unknown outcomes in outer evaluation.
        if 'alert' not in g:
            g=g.copy();rank=g.groupby('date').prob.rank(method='first',ascending=False)
            g['alert']=rank<=np.ceil(g.groupby('date').date.transform('size')*.1)
        rates=g.groupby('date').y.mean()
        selected=g[g.alert].groupby('date').y.mean()
        precision=float(selected.mean()) if len(selected) else np.nan
        base=float(rates.mean())
        rows.append(dict(level=level,n=len(g),dates=g.date.nunique(),positives=int(y.sum()),
            prevalence=base,brier=bs,prior_brier=null,brier_skill=1-bs/null if null else np.nan,
            pr_auc=float(average_precision_score(y,p,sample_weight=w)) if y.sum()>0 else np.nan,
            top10_precision=precision,top10_lift=precision/base if base else np.nan,
            top10_recall=float(g.loc[g.alert,'y'].sum()/y.sum()) if y.sum()>0 else np.nan))
    return rows


def search_evaluate(spec,stage='a',candidate_id=None):
    validate_spec(spec)
    if stage not in _SEARCH:
        with (CACHE/f'stage_{stage}_search.pkl').open('rb') as h:_SEARCH[stage]=pickle.load(h)
    rows=[]
    for key,(train,feedback) in _SEARCH[stage].items():
        if train.y.sum()<5 or feedback.y.sum()<5:continue
        p,prior=fit_predict(train,feedback,spec)
        v=feedback[['date','level','y']].copy();v['prob']=p;v['prior']=prior
        for row in metric_rows(v):
            row.update(frequency=key[0],threshold=key[1],benchmark=key[2]);rows.append(row)
    result=pd.DataFrame(rows)
    objective=float(result.brier_skill.mean()) if len(result) else -1e9
    summary=dict(objective=objective,metric='equal_task_mean_Brier_skill',tasks=len(result),
        by_frequency=result.groupby('frequency')[['brier_skill','top10_lift','pr_auc']].mean().reset_index().to_dict('records'))
    if candidate_id:
        dest=OUT/f'stage_{stage}/candidates'/candidate_id;dest.mkdir(parents=True,exist_ok=True)
        js(dest/'spec.json',spec);result.to_csv(dest/'feedback.csv',index=False);js(dest/'summary.json',finite_json(summary))
    return finite_json(summary)


def baselines(stage='a'):
    prepare_search(stage)
    results={name:search_evaluate(spec,stage,name) for name,spec in BASELINES.items()}
    js(OUT/f'stage_{stage}/baseline_feedback.json',results)
    print('baseline feedback',stage,json.dumps(results),flush=True)


if __name__=='__main__':
    import sys
    baselines('b' if '--stage-b' in sys.argv else 'a')
