"""P3: past-OOS, strictly mature offset calibration with preserved monthly ranks."""
from scipy.special import expit,logit
from scipy.optimize import minimize
from core import *


def fit_offset(p,y,states,frame_dates,state=False):
    probability=np.asarray(p,float);y=np.asarray(y,float);offset=logit(np.clip(probability,1e-8,1-1e-8));n=len(y)
    w=1/pd.Series(frame_dates).groupby(pd.Series(frame_dates)).transform('size').to_numpy(float)
    if state:
        values=np.asarray(states,float);med=np.nanmedian(values,axis=0);med=np.where(np.isfinite(med),med,0.)
        scale=np.nanquantile(values,.75,axis=0)-np.nanquantile(values,.25,axis=0);scale=np.where(np.isfinite(scale)&(scale>0),scale,1.)
        z=np.clip((np.where(np.isfinite(values),values,med)-med)/scale,-5,5);x=np.c_[np.ones(n),z]
    else:med=np.array([]);scale=np.array([]);x=np.ones((n,1))
    maximum=C['calibration']['maximum_absolute_logit_shift'];l2=C['calibration']['state_l2']
    def objective(beta):
        raw=x@beta;shift=np.clip(raw,-maximum,maximum);linear=offset+shift
        loss=np.sum(w*(np.logaddexp(0,linear)-y*linear))+.5*l2*np.dot(beta[1:],beta[1:])
        gradient=x.T@(w*(expit(linear)-y)*(np.abs(raw)<maximum));gradient[1:]+=l2*beta[1:]
        return float(loss),gradient
    result=minimize(objective,np.zeros(x.shape[1]),method='L-BFGS-B',jac=True,bounds=[(-maximum,maximum)]+[(-5,5)]*(x.shape[1]-1),options={'maxiter':1000,'ftol':1e-12,'gtol':1e-7})
    return dict(success=bool(result.success),message=str(result.message),coefficients=result.x.tolist(),median=med.tolist(),scale=scale.tolist(),objective=float(result.fun),iterations=int(result.nit),state=state)


def apply_offset(p,states,fit):
    n=len(p);beta=np.asarray(fit['coefficients'])
    if fit['state']:
        values=np.asarray(states,float);med=np.asarray(fit['median']);scale=np.asarray(fit['scale']);z=np.clip((np.where(np.isfinite(values),values,med)-med)/scale,-5,5);x=np.c_[np.ones(n),z]
    else:x=np.ones((n,1))
    shift=np.clip(x@beta,-C['calibration']['maximum_absolute_logit_shift'],C['calibration']['maximum_absolute_logit_shift'])
    return expit(logit(np.clip(p,1e-8,1-1e-8))+shift)


def mature_calibration_rows(raw,date):
    history=raw[(raw.date<date)&(raw.label_end<date)&raw.actual.notna()].copy()
    dates=sorted(history.date.unique())[-C['calibration']['lookback_origins']:]
    return history[history.date.isin(dates)].sort_values(['date','instrument'])


def main():
    gate=json.loads((OUT/'p2_gate.json').read_text());assert gate['passed']
    full=pd.read_parquet(CACHE/'all_predictions.parquet');main=full[full.horizon.eq(6)];rows=[];audit=[];statecols=C['calibration']['state_features']
    for name in C['calibration']['models']:
        raw=main[main.model.eq(name)].copy()
        for date,test in raw.groupby('date',sort=True):
            history=mature_calibration_rows(raw,date);events=int((history.actual<-.2).sum());neg=len(history)-events
            enough=history.date.nunique()>=C['calibration']['minimum_origins'] and min(events,neg)>=C['calibration']['minimum_events']
            for method in ['global','state']:
                result=test.copy();result['model']=name+'__'+method;fit=None;reason='too_few_mature_OOS_origins_or_events'
                if enough:
                    fit=fit_offset(history.probability,labels(history.actual),history[statecols],history.date,state=method=='state')
                    if fit['success']:
                        result['probability']=apply_offset(test.probability.to_numpy(),test[statecols],fit);reason='fitted'
                    else:reason='optimizer_failure_exact_raw_fallback'
                result['delta_b1']=result.probability-result.b1_probability;rows.append(result)
                audit.append(dict(base_model=name,method=method,date=str(date.date()),training_rows=len(history),training_origins=history.date.nunique(),events=events,reason=reason,
                    max_training_label=str(history.label_end.max()) if len(history) else None,train_keys_sha256=keys_hash(history),fit=fit))
    output=pd.concat(rows,ignore_index=True);output.to_parquet(CACHE/'calibrated_predictions.parquet',index=False);write_json(OUT/'calibration_fits.json',audit)
    allmain=pd.concat([main,output],ignore_index=True);allmain.to_parquet(CACHE/'main_with_calibration.parquet',index=False)
    monthly=[]
    for (model,date),g in allmain.groupby(['model','date']):
        flags={str(int(frac*100)):warning(g.probability,g.instrument,frac) for frac in [.1,.2]};r=metrics(g.probability,g.actual,flags)
        if r is not None:monthly.append(dict(model=model,date=date,**r))
    monthly=pd.DataFrame(monthly);monthly.to_csv(OUT/'calibration_monthly_scores.csv',index=False)
    comparisons=[]
    for name in C['calibration']['models']:
        for method in ['global','state']:
            a=monthly[monthly.model.eq(name+'__'+method)];b=monthly[monthly.model.eq(name)]
            for metric in ['brier','auc','bias','recall20','enrichment20']:
                d=paired(a,b,metric)
                if np.isfinite(d).any():
                    for block in [6,12]:comparisons.append(dict(candidate=name+'__'+method,baseline=name,metric=metric,**ci(d,block)))
    pd.DataFrame(comparisons).to_csv(OUT/'calibration_comparisons.csv',index=False)
    write_json(OUT/'p3_gate.json',dict(phase='P3',passed=True,strict_mature_OOS_history=True,methods_frozen=True,probability_level_not_ranking_experiment=True,comparison_rows=len(comparisons),
        fallback_count=sum(r['reason']!='fitted' for r in audit),optimizer_failures=sum(r['reason']=='optimizer_failure_exact_raw_fallback' for r in audit),performance_not_a_gate=True))
    print('P3 offset calibration complete',flush=True)

if __name__=='__main__':main()
