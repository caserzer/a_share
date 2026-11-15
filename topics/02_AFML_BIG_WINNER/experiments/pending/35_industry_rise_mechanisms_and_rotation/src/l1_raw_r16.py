"""Separate uncalibrated binary diagnostic; never fills calibrated output gaps."""
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score,average_precision_score,brier_score_loss
from common import *
from train_r02 import F,target,train_masks,sample_weights

def run():
    out=ROOT/'outputs/r16';panel=pd.read_parquet(ROOT/'data/l1_monthly_panel.parquet');panel['log_members']=np.log(panel.members)
    rows=[];parameters=[];ledger=[]
    for cohort,extra in {'F':[],'FD':['breadth21','breadth63']}.items():
        g=panel[panel.price_ready].dropna(subset=F+extra).copy();rank=g.groupby('date')[F+extra].transform(centered_rank)
        for task in ['onset','reversal']:
            for h in [20,60]:
                y,eligible=target(g,task,h);q=g[eligible].copy();q['y']=y[eligible]
                for year in range(2020,2027):
                    fit,cal,test=train_masks(q,year,h,task);tr=q[fit];ca=q[cal];te=q[test]
                    if te.empty:continue
                    reason=None
                    if len(tr)<300 or tr.date.nunique()<18:reason='train_size'
                    elif tr.y.value_counts().reindex([0.,1.],fill_value=0).min()<30:reason='train_classes'
                    cal_ok=bool(len(ca)>=100 and ca.date.nunique()>=4 and ca.y.value_counts().reindex([0.,1.],fill_value=0).min()>=10)
                    rec=dict(cohort=cohort,task=task,horizon=h,year=year,train_rows=len(tr),train_months=tr.date.nunique(),cal_rows=len(ca),cal_months=ca.date.nunique(),calibration_eligible=cal_ok,fit_max_maturity=tr[f'maturity{h}'].max(),status=reason or 'fit')
                    ledger.append(rec)
                    if reason:continue
                    methods={'F':F} if cohort=='F' else {'F':F,'FD':F+extra}
                    for method,cols in methods.items():
                        scaler=StandardScaler().fit(rank.loc[tr.index,cols]);model=LogisticRegression(C=1,max_iter=2000,random_state=3502).fit(scaler.transform(rank.loc[tr.index,cols]),tr.y,sample_weight=sample_weights(tr))
                        p=te[KEY+['date','y',f'excess{h}']].copy().rename(columns={f'excess{h}':'excess'});p['raw_score']=model.predict_proba(scaler.transform(rank.loc[te.index,cols]))[:,1]
                        p['row_id']=te.index;p['method']=method;p['training_mean']=np.average(tr.y,weights=sample_weights(tr));p['score_type']='uncalibrated_logit'
                        for name in ['cohort','task','horizon','year','calibration_eligible']:p[name]=rec[name]
                        rows.append(p);parameters.append(dict(rec,method=method,columns=cols,scaler_mean=scaler.mean_.tolist(),scaler_scale=scaler.scale_.tolist(),coef=model.coef_.ravel().tolist(),intercept=float(model.intercept_[0])))
    d=pd.concat(rows,ignore_index=True) if rows else pd.DataFrame();d.to_parquet(out/'raw_predictions.parquet',index=False)
    js(out/'raw_parameters.json',parameters);pd.DataFrame(ledger).to_csv(out/'raw_fold_ledger.csv',index=False)
    summaries=[]
    for key,g in d.groupby(['cohort','method','task','horizon']):
        v=g[g.y.notna()];summaries.append(dict(zip(['cohort','method','task','horizon'],key),rows=len(g),known=len(v),unknown=len(g)-len(v),months=v.date.nunique(),prevalence=v.y.mean(),
            raw_brier=brier_score_loss(v.y,v.raw_score),baseline_brier=brier_score_loss(v.y,v.training_mean),
            auc=roc_auc_score(v.y,v.raw_score) if v.y.nunique()==2 else np.nan,pr_auc=average_precision_score(v.y,v.raw_score) if v.y.sum()>0 else np.nan))
    pd.DataFrame(summaries).to_csv(out/'raw_summary.csv',index=False)
    js(out/'raw_receipt.json',dict(protocol_sha256=sha(ROOT/'protocols/r16.json'),code_sha256=sha(__file__),panel_sha256=sha(ROOT/'data/l1_monthly_panel.parquet'),rows=len(d),score_meaning='uncalibrated Logit research score; not substituted for missing calibrated predictions'))
    print('R16 raw diagnostic',len(d),'rows')
if __name__=='__main__':run()
