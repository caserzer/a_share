"""Diagnose frozen return models without refitting or selecting parameters."""
from common import *
import pandas as pd
from refit_r131 import prepare, predict_saved, FK
from train_r02 import train_masks, sample_weights

def run():
    out=ROOT/'outputs/r186';out.mkdir(exist_ok=True)
    panel=pd.read_parquet(ROOT/'outputs/r130/monthly_panel.parquet')
    panel['log_members']=np.log(panel.members.where(panel.members.gt(0)))
    models=json.loads((ROOT/'outputs/r131/model_parameters.json').read_text())
    saved=pd.read_parquet(ROOT/'outputs/r131/predictions.parquet')
    rows=[];dates=[];checked=0;maxerr=0.
    for m in models:
        if m['task']!='return':continue
        q,ranks=prepare(panel,m['era'],m['level'],m['cohort'],'return',m['horizon'])
        fit,_,test=train_masks(q,m['year'],m['horizon'],'return')
        mean=float(np.average(q.loc[fit,'y'],weights=sample_weights(q[fit])))
        ident={k:m[k] for k in FK+['method']}
        for split,mask in [('train',fit),('test',test)]:
            g=q[mask].copy();pred,_=predict_saved(m,ranks.loc[g.index,m['columns']])
            g['prediction']=pred
            if split=='test':
                old=saved.copy()
                for k,v in ident.items():old=old[old[k].eq(v)]
                pair=g.merge(old,on=KEY+['date'],suffixes=('_calc','_saved'),validate='one_to_one')
                assert len(pair)==len(g)==len(old)
                error=np.max(np.abs(pair.prediction_calc-pair.prediction_saved))
                assert error<1e-12;maxerr=max(maxerr,float(error));checked+=len(pair)
                assert np.allclose(pair.training_mean,mean,rtol=0,atol=1e-12)
            valid=g.y.notna();v=g[valid].copy()
            v['se_model']=(v.y-v.prediction)**2;v['se_mean']=(v.y-mean)**2
            daily=v.groupby('date')[['se_model','se_mean']].mean()
            mm=float(daily.se_model.mean());bm=float(daily.se_mean.mean())
            # Independent row weighting must recover the date-equal calculation.
            w=1/v.groupby('date').date.transform('size')
            assert np.isclose(mm,np.average(v.se_model,weights=w),rtol=1e-12)
            assert np.isclose(bm,np.average(v.se_mean,weights=w),rtol=1e-12)
            rows.append(dict(ident,split=split,rows=len(g),mature=int(valid.sum()),unknown=int((~valid).sum()),months=len(daily),mse=mm,baseline_mse=bm,skill=1-mm/bm if bm>0 else None))
            for date,x in daily.iterrows():dates.append(dict(ident,split=split,date=str(date.date()),mse=x.se_model,baseline_mse=x.se_mean))
    df=pd.DataFrame(rows);df.to_csv(out/'fold_metrics.csv',index=False)
    pd.DataFrame(dates).to_csv(out/'date_metrics.csv',index=False)
    pair=df[df.split.eq('train')].merge(df[df.split.eq('test')],on=FK+['method'],suffixes=('_train','_test'),validate='one_to_one')
    pair.to_csv(out/'paired_metrics.csv',index=False)
    summary=[]
    for (h,cohort,method),g in pair.groupby(['horizon','cohort','method']):
        summary.append(dict(horizon=h,cohort=cohort,method=method,folds=len(g),train_positive=int(g.skill_train.gt(0).sum()),test_positive=int(g.skill_test.gt(0).sum()),train_positive_test_nonpositive=int((g.skill_train.gt(0)&g.skill_test.le(0)).sum()),median_train_skill=g.skill_train.median(),median_test_skill=g.skill_test.median()))
    js(out/'summary.json',summary)
    inputs=['outputs/r130/monthly_panel.parquet','outputs/r131/model_parameters.json','outputs/r131/predictions.parquet','protocols/r186.json','src/fit_transfer_r186.py','src/refit_r131.py','src/train_r02.py','src/common.py']
    js(out/'verification.json',dict(status='PASS',scope='Saved test predictions and training means matched; independent row/date MSE aggregation checked',models=len(pair),test_predictions_checked=checked,max_prediction_error=maxerr,inputs={p:sha(ROOT/p) for p in inputs},outputs={p:sha(out/p) for p in ['fold_metrics.csv','date_metrics.csv','paired_metrics.csv','summary.json']}))
    print((out/'summary.json').read_text())
if __name__=='__main__':run()
