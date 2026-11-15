"""Annual, maturity-purged Ridge/Logit with a separate past calibration window."""
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge, LogisticRegression
from common import *

F=['mom20','mom60','vol20','dd60','past_excess20','past_excess60','log_members']
EXTRA={'F':[], 'FD':['breadth21','breadth63'],'FC':['turn_rank504'],'FG':['pe_rank504'],'FDG':['breadth21','breadth63','pe_rank504']}


def target(g,task,h):
    valid=g[f'excess{h}'].notna()
    if task=='return':return g[f'excess{h}'],pd.Series(True,index=g.index)
    if task=='onset':
        y=((g[f'return{h}']>=(.05 if h==20 else .10))&(g[f'excess{h}']>=(.03 if h==20 else .05))).astype(float).where(valid)
        return y,g.past_excess20.le(0)
    y=g[f'rel_trough{h}'].le(-.08 if h==20 else -.12).astype(float).where(valid & g[f'rel_trough{h}'].notna())
    return y,g.past_excess60.gt(0)&g.mom60.gt(0)


def sample_weights(g):
    return len(g)/(g.date.nunique()*g.groupby('date').date.transform('size'))


def train_masks(g,year,h,task):
    test_start=pd.Timestamp(year,1,1);cal_start=pd.Timestamp(year-1,7,1)
    matured=g[f'maturity{h}'].lt(test_start)&g.y.notna()
    if task=='return':
        fit=matured & g.date.lt(test_start);cal=pd.Series(False,index=g.index)
    else:
        fit=g[f'maturity{h}'].lt(cal_start)&g.date.lt(cal_start)&g.y.notna()
        cal=matured&g.date.ge(cal_start)&g.date.lt(test_start)
    test=g.date.dt.year.eq(year)
    return fit,cal,test


def run():
    out=ROOT/'outputs/r02'; panel=pd.read_parquet(ROOT/'data/monthly_panel.parquet')
    assert sha(ROOT/'data/monthly_panel.parquet')==json.loads((ROOT/'outputs/r01/panel_receipt.json').read_text())['sha256']
    panel['log_members']=np.log(panel.members)
    preds=[];ledger=[];coeff=[]
    for (era,level),base in panel[panel.price_ready].groupby(['era','level']):
        for cohort,ext in EXTRA.items():
            columns=F+ext;g=base.dropna(subset=columns).copy()
            # Same-day cross-section is allowed; feature ranks never use target availability.
            rank=g.groupby('date')[columns].transform(centered_rank)
            for task in ['return','onset','reversal']:
                for h in [20,60]:
                    y,eligible=target(g,task,h);q=g[eligible].copy();q['y']=y[eligible]
                    for year in range(2020,2027):
                        fit,cal,test=train_masks(q,year,h,task)
                        if not test.any():continue
                        tr=q[fit];ca=q[cal];te=q[test]
                        reason=None
                        if tr.date.nunique()<18 or len(tr)<300:reason='insufficient_train_months_or_rows'
                        if not reason and task!='return':
                            if tr.y.value_counts().reindex([0.,1.],fill_value=0).min()<30:reason='insufficient_train_classes'
                            elif ca.date.nunique()<4 or len(ca)<100 or ca.y.value_counts().reindex([0.,1.],fill_value=0).min()<10:reason='insufficient_calibration'
                        rec=dict(era=era,level=level,cohort=cohort,task=task,horizon=h,year=year,n_fit=len(tr),n_cal=len(ca),n_test=len(te),
                            train_months=tr.date.nunique(),cal_months=ca.date.nunique(),fit_max_maturity=tr[f'maturity{h}'].max(),cal_max_maturity=ca[f'maturity{h}'].max())
                        if reason:ledger.append(dict(rec,status='skipped',reason=reason));continue
                        methods={'F':F} if cohort=='F' else {'F':F,cohort:columns}
                        for method,cols in methods.items():
                            scaler=StandardScaler().fit(rank.loc[tr.index,cols]);x=scaler.transform(rank.loc[tr.index,cols]);xt=scaler.transform(rank.loc[te.index,cols]);w=sample_weights(tr)
                            if task=='return':
                                model=Ridge(alpha=10).fit(x,tr.y,sample_weight=w);prediction=model.predict(xt);raw=prediction;platt=None
                            else:
                                model=LogisticRegression(C=1,max_iter=2000,random_state=3502).fit(x,tr.y,sample_weight=w)
                                xc=scaler.transform(rank.loc[ca.index,cols]);ds=model.decision_function(xc).reshape(-1,1)
                                platt=LogisticRegression(C=1,max_iter=2000,random_state=3502).fit(ds,ca.y,sample_weight=sample_weights(ca))
                                raw=model.predict_proba(xt)[:,1];prediction=platt.predict_proba(model.decision_function(xt).reshape(-1,1))[:,1]
                            p=te[KEY+['date','entry_date',f'maturity{h}',f'excess{h}','y']].copy().rename(columns={f'maturity{h}':'maturity',f'excess{h}':'excess'})
                            p['row_id']=te.index;p['cohort']=cohort;p['method']=method;p['task']=task;p['horizon']=h;p['year']=year
                            p['prediction']=prediction;p['raw_prediction']=raw;p['training_mean']=np.average(tr.y,weights=w)
                            preds.append(p)
                            coeff.append(dict(rec,method=method,columns=cols,scaler_mean=scaler.mean_.tolist(),scaler_scale=scaler.scale_.tolist(),
                                coefficient=model.coef_.tolist(),intercept=np.asarray(model.intercept_).tolist(),
                                calibration_coefficient=platt.coef_.tolist() if platt is not None else None,
                                calibration_intercept=platt.intercept_.tolist() if platt is not None else None))
                        ledger.append(dict(rec,status='fit',reason=''))
            print('FINISHED',era,level,cohort,flush=True)
    result=pd.concat(preds,ignore_index=True)
    result.to_parquet(out/'predictions.parquet',index=False)
    pd.DataFrame(ledger).to_csv(out/'fold_ledger.csv',index=False);js(out/'model_parameters.json',coeff)
    js(out/'run_receipt.json',dict(protocol_sha256=sha(ROOT/'protocols/r02.json'),panel_sha256=sha(ROOT/'data/monthly_panel.parquet'),
        code_sha256=sha(__file__),common_sha256=sha(ROOT/'src/common.py'),prediction_sha256=sha(out/'predictions.parquet'),rows=len(result),
        trained_folds=sum(x['status']=='fit' for x in ledger),skipped_folds=sum(x['status']=='skipped' for x in ledger)))
    print('DONE',len(result),'prediction rows',flush=True)

if __name__=='__main__':run()
