"""Independent ranks, chronology, labels, optimization and prediction validation."""
import pandas as pd
from scipy.stats import rankdata
from scipy.special import expit
from common import *
from versioned_observations import digest_json
K=KEY+['date','cohort','method','task','horizon','year']
F=['mom20','mom60','vol20','dd60','past_excess20','past_excess60','log_members']

def run():
    out=ROOT/'outputs/r105';receipt=json.loads((out/'receipt.json').read_text())
    for path,h in receipt['reads'].items():assert sha(path)==h
    for path,h in receipt['outputs'].items():assert sha(out/path)==h
    p=pd.read_parquet(out/'paired_predictions.parquet');models=json.loads((out/'model_parameters.json').read_text());old=[];panels=[];ledgers=[];original_models={}
    for rnd,panelname in [('r02','monthly_panel'),('r16','l1_monthly_panel')]:
        panels.append(pd.read_parquet(ROOT/f'data/{panelname}.parquet'))
        pred=pd.read_parquet(ROOT/f'outputs/{rnd}/predictions.parquet');old.append(pred[pred.method.eq(pred.cohort)&pred.cohort.isin(['F','FD'])])
        ledger=pd.read_csv(ROOT/f'outputs/{rnd}/fold_ledger.csv');ledgers.append(ledger[ledger.cohort.isin(['F','FD'])])
        for m in json.loads((ROOT/f'outputs/{rnd}/model_parameters.json').read_text()):
            if m['method']==m['cohort'] and m['cohort'] in ['F','FD']:original_models[digest_json(m)]=m
    old=pd.concat(old,ignore_index=True);panel=pd.concat(panels,ignore_index=True);panel['log_members']=np.log(panel.members)
    pd.testing.assert_frame_equal(p[list(old)].sort_values(K).reset_index(drop=True),old.sort_values(K).reset_index(drop=True))
    pd.testing.assert_frame_equal(pd.read_csv(out/'original_fold_ledger.csv'),pd.concat(ledgers,ignore_index=True))
    assert {m['baseline_model_sha256'] for m in models}==set(original_models) and len(models)==len(original_models)
    cache={};max_gradient=0.;verified=0
    for m in models:
        oldm=original_models[m['baseline_model_sha256']];key=(m['era'],m['level'],m['cohort'])
        if key not in cache:
            cols=F+(['breadth21','breadth63'] if m['cohort']=='FD' else [])
            g=panel[panel.era.eq(m['era'])&panel.level.eq(m['level'])&panel.price_ready].dropna(subset=cols).copy();rank=pd.DataFrame(index=g.index,columns=cols,dtype=float)
            for _,v in g.groupby('date'):
                for col in cols:rank.loc[v.index,col]=(rankdata(v[col],method='average')-.5)/len(v)-.5
            cache[key]=(g,rank)
        g,rank=cache[key];h=m['horizon'];task=m['task'];year=m['year'];valid=g[f'excess{h}'].notna()
        if task=='return':y=g[f'excess{h}'];eligible=pd.Series(True,index=g.index)
        elif task=='onset':y=((g[f'return{h}']>=(.05 if h==20 else .10))&(g[f'excess{h}']>=(.03 if h==20 else .05))).astype(float).where(valid);eligible=g.past_excess20.le(0)
        else:y=g[f'rel_trough{h}'].le(-.08 if h==20 else -.12).astype(float).where(valid&g[f'rel_trough{h}'].notna());eligible=g.past_excess60.gt(0)&g.mom60.gt(0)
        q=g[eligible].copy();q['y']=y[eligible];boundary=pd.Timestamp(year,1,1);calstart=pd.Timestamp(year-1,7,1)
        fitboundary=boundary if task=='return' else calstart
        tr=q[q.date.lt(fitboundary)&q[f'maturity{h}'].lt(fitboundary)&q.y.notna()]
        ca=q.iloc[:0] if task=='return' else q[q.date.ge(calstart)&q.date.lt(boundary)&q[f'maturity{h}'].lt(boundary)&q.y.notna()]
        te=q[q.date.dt.year.eq(year)]
        assert len(tr)==m['n_fit']==oldm['n_fit'] and len(ca)==m['n_cal']==oldm['n_cal'] and len(te)==m['n_test']==oldm['n_test']
        assert len(tr)>=300 and tr.date.nunique()>=18
        assert digest_json(tr[KEY+['date']].astype(str).to_dict('records'))==m['fit_identity_sha256']
        assert digest_json(ca[KEY+['date']].astype(str).to_dict('records'))==m['cal_identity_sha256']
        if task!='return':assert len(ca)>=100 and ca.date.nunique()>=4 and tr.y.value_counts().min()>=30 and ca.y.value_counts().min()>=10
        cols=[c for c in oldm['columns'] if c not in ['past_excess20','past_excess60']];assert m['columns']==cols
        means=rank.loc[tr.index,cols].mean().to_numpy();scales=rank.loc[tr.index,cols].std(ddof=0).to_numpy();scales=np.where(scales==0,1,scales)
        np.testing.assert_allclose(m['scaler_mean'],means,atol=1e-14);np.testing.assert_allclose(m['scaler_scale'],scales,atol=1e-14)
        x=(rank.loc[tr.index,cols].to_numpy()-means)/scales;xt=(rank.loc[te.index,cols].to_numpy()-means)/scales
        beta=np.asarray(m['coefficient']).ravel();intercept=np.asarray(m['intercept']).item();w=len(tr)/(tr.date.nunique()*tr.groupby('date').date.transform('size').to_numpy())
        residual=(x@beta+intercept if task=='return' else expit(x@beta+intercept))-tr.y.to_numpy()
        grad=np.r_[x.T@(w*residual)+(10 if task=='return' else 1)*beta,np.sum(w*residual)]/len(tr)
        assert np.max(abs(grad))<.0005;max_gradient=max(max_gradient,float(np.max(abs(grad))))
        decision=xt@beta+intercept
        if task=='return':prediction=decision;frozen=decision
        else:
            xc=(rank.loc[ca.index,cols].to_numpy()-means)/scales;caldecision=xc@beta+intercept;a=np.asarray(m['calibration_coefficient']).item();b=np.asarray(m['calibration_intercept']).item()
            wc=len(ca)/(ca.date.nunique()*ca.groupby('date').date.transform('size').to_numpy());err=expit(caldecision*a+b)-ca.y.to_numpy()
            grad=np.array([np.sum(wc*err*caldecision)+a,np.sum(wc*err)])/len(ca)
            assert np.max(abs(grad))<.0005;max_gradient=max(max_gradient,float(np.max(abs(grad))))
            prediction=expit(decision*a+b);frozen=expit(decision*np.asarray(oldm['calibration_coefficient']).item()+np.asarray(oldm['calibration_intercept']).item())
        expected=te[KEY+['date','y',f'maturity{h}',f'excess{h}']].copy();expected['decision']=decision;expected['pred']=prediction;expected['frozen']=frozen
        actual=p
        for col in ['era','level','cohort','method','task','horizon','year']:actual=actual[actual[col].eq(m[col])]
        j=actual.merge(expected,on=KEY+['date'],suffixes=('_stored','_rebuild'),how='outer',indicator=True,validate='one_to_one');assert j._merge.eq('both').all()
        np.testing.assert_allclose(j.y_stored,j.y_rebuild,equal_nan=True)
        assert (j.maturity.fillna(pd.Timestamp('1900-01-01'))==j[f'maturity{h}'].fillna(pd.Timestamp('1900-01-01'))).all()
        np.testing.assert_allclose(j.excess,j[f'excess{h}'],equal_nan=True)
        np.testing.assert_allclose(j.unique_decision,j.decision,atol=1e-12);np.testing.assert_allclose(j.unique_prediction,j.pred,atol=1e-12);np.testing.assert_allclose(j.unique_frozen_calibration_prediction,j.frozen,atol=1e-12);verified+=len(j)
    js(out/'model_verification.json',dict(status='PASS',models=len(models),test_rows=verified,max_normalized_gradient=max_gradient,source_rank_and_label_reconstruction=True,adopted=False));print('PASS',len(models),verified,'gradient',max_gradient)

if __name__=='__main__':run()
