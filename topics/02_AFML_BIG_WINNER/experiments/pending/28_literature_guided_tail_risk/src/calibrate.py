"""One registered, rank-preserving, strictly matured-OOS intercept calibration."""
from scipy.special import expit,logit
from scipy.optimize import brentq
from core import *
from evaluate import calibration
from run import freeze


def history_rows(raw,date):
    z=raw[(raw.date<date)&(raw.label_end<date)&raw.actual.notna()]
    return z[z.date.isin(sorted(z.date.unique())[-C['calibration']['lookback_origins']:])]


def offset_fit(p,y,dates):
    v=logit(np.clip(p,1e-8,1-1e-8));w=weights(pd.DataFrame(dict(date=dates)));y=np.asarray(y)
    def fn(a):return float(np.sum(w*(expit(v+a)-y)))
    m=C['calibration']['max_shift']
    return -m if fn(-m)>=0 else m if fn(m)<=0 else brentq(fn,-m,m,xtol=1e-12)


def main():
    freeze();full=pd.read_parquet(CACHE/'all_predictions.parquet');rows=[];audits=[]
    for name in C['calibration']['models']:
        raw=full[full.model.eq(name)]
        for date,g in raw.groupby('date',sort=True):
            z=history_rows(raw,date);e=int((z.actual<-.2).sum())
            enough=z.date.nunique()>=C['calibration']['minimum_origins'] and min(e,len(z)-e)>=C['calibration']['minimum_events']
            shift=offset_fit(z.probability,labels(z.actual),z.date) if enough else 0.
            out=g.copy();out['model']=name+'__offset'
            out['probability']=expit(logit(np.clip(g.probability,1e-8,1-1e-8))+shift) if enough else g.probability
            rows.append(out);audits.append(dict(model=name,date=str(date.date()),shift=shift,fitted=bool(enough),
                train_rows=len(z),train_months=z.date.nunique(),events=e,max_label=str(z.label_end.max()) if len(z) else None,keys_sha256=keys_hash(z)))
    cal=pd.concat(rows,ignore_index=True);cal.to_parquet(CACHE/'calibrated_predictions.parquet',index=False)
    write_json(EP/'outputs/audits/calibration_fits.json',audits);allmain=pd.concat([full[full.model.isin(C['calibration']['models'])],cal],ignore_index=True)
    monthly=[];rel=[];conditions=[]
    for (name,date),g in allmain.groupby(['model','date']):
        r=metrics(g.probability,g.actual,{str(int(f*100)):warning(g.probability,g.instrument,f) for f in [.05,.1,.2]})
        if r is not None:
            e,t=calibration(g);monthly.append(dict(model=name,date=date,ece=e,**r));rel.extend(t.assign(model=name,date=date).to_dict('records'))
    m=pd.DataFrame(monthly);m.to_csv(OUT/'calibration_monthly.csv',index=False);pd.DataFrame(rel).to_csv(OUT/'calibration_reliability.csv',index=False)
    intervals=[]
    for name in C['calibration']['models']:
        for metric in ['brier','bias','ece','auc','recall5','recall20']:
            d=paired(m[m.model.eq(name+'__offset')],m[m.model.eq(name)],metric)
            for block in C['bootstrap']['blocks']:intervals.append(dict(candidate=name+'__offset',baseline=name,metric=metric,**ci(d,block)))
    pd.DataFrame(intervals).to_csv(OUT/'calibration_intervals.csv',index=False)
    for dimension in ['year','regime','industry_id']:
        sub=allmain.assign(condition=allmain.date.dt.year.astype(str) if dimension=='year' else allmain[dimension])
        for (name,date,condition),g in sub.groupby(['model','date','condition']):
            r=metrics(g.probability,g.actual)
            if r is not None:
                e,_=calibration(g);conditions.append(dict(model=name,date=date,dimension=dimension,condition=condition,ece=e,**r))
    pd.DataFrame(conditions).to_csv(OUT/'calibration_conditional.csv',index=False)
    print('offset calibration complete',flush=True)


if __name__=='__main__':main()
