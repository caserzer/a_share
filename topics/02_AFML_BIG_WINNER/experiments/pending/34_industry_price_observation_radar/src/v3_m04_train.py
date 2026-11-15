"""Class-mass-preserving positive prefix-reference weighting; fixed models."""
import json
import warnings
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.exceptions import ConvergenceWarning
from audit_local_inputs import EP,sha
from v3_m01_prepare import FEATURES_CHANGE


def training_weights(panel,year,target):
    cols=['parent_coverage_target','child_coverage_target'] if target=='COVER' else ['parent_early_target','child_early_target']
    label=panel[cols].max(axis=1,skipna=False)
    cut=pd.Timestamp(year=year,month=1,day=1)
    tr=panel[panel.eligible&label.notna()&panel.target_available_date.lt(cut)].copy()
    y=label.loc[tr.index].astype(int)
    old=1/tr.groupby('date').date.transform('size').astype(float);old*=len(old)/old.sum()
    pref=tr.parent_reference.map(lambda x:None if pd.isna(x) else 'P|'+x)
    cref=tr.child_reference.map(lambda x:None if pd.isna(x) else 'C|'+x)
    refs=pref.where(pref.notna(),cref) if target=='COVER' else pref.where(~tr.child_early_target.eq(1),cref)
    pos=y.eq(1);assert refs[pos].notna().all()
    group_mass=old[pos].groupby(refs[pos]).transform('sum');groups=refs[pos].nunique()
    new=old.copy();new.loc[pos]=old[pos]/group_mass*(old[pos].sum()/groups)
    assert np.allclose(new[pos].sum(),old[pos].sum(),rtol=1e-12)
    np.testing.assert_array_equal(new[~pos],old[~pos])
    masses=new[pos].groupby(refs[pos]).sum()
    assert np.allclose(masses,masses.iloc[0],rtol=1e-12)
    assert tr.date.lt(cut).all() and tr.target_available_date.lt(cut).all()
    return tr,y,refs,old,new


def main():
    root=EP/'outputs/v3_m02_targets';baseline=EP/'outputs/v3_m02_models';out=EP/'outputs/v3_m04_models'
    if out.exists():raise FileExistsError(out)
    for directory in [root,baseline]:
        rec=json.loads((directory/'receipt.json').read_text())
        for rel,digest in rec['artifacts'].items():assert sha(directory/rel)==digest,rel
    panel=pd.read_parquet(root/'training_panel.parquet')
    rename={'score_LR_COVER':'score_DATE_COVER','score_LR_EARLY_UNION':'score_DATE_EARLY','score_BALANCED':'score_DATE_BALANCED'}
    prior=pd.read_parquet(baseline/'scored_catalog.parquet',columns=['date','era','industry_code']+list(rename)).rename(columns=rename)
    panel=panel.merge(prior,on=['date','era','industry_code'],how='left',validate='one_to_one')
    sources=[root/'receipt.json',root/'training_panel.parquet',baseline/'receipt.json',baseline/'scored_catalog.parquet',EP/'protocols/v3_r00/m04_process_weight_plan.md',Path(__file__)]
    out.mkdir();(out/'started.json').write_text(json.dumps({str(p):sha(p) for p in sources},indent=2)+'\n')
    fits=[];scored=[];weights=[];coefficients=[]
    for year in range(2020,2027):
        te=panel[panel.date.dt.year.eq(year)].copy()
        for target,oldname in [('COVER','LR_COVER'),('EARLY','LR_EARLY_UNION')]:
            tr,y,refs,old,new=training_weights(panel,year,target);positive=int(y.sum());negative=int(y.eq(0).sum())
            assert len(tr)>=1000 and positive>=50 and negative>=50
            model=make_pipeline(StandardScaler(),LogisticRegression(C=1,max_iter=2000,solver='lbfgs'))
            with warnings.catch_warnings():
                warnings.simplefilter('error',ConvergenceWarning)
                model.fit(tr[FEATURES_CHANGE],y,logisticregression__sample_weight=new)
            original=joblib.load(baseline/str(year)/(oldname+'.joblib'))
            np.testing.assert_array_equal(model[0].mean_,original[0].mean_)
            np.testing.assert_array_equal(model[0].scale_,original[0].scale_)
            mask=te.eligible;score='score_PROCESS_'+target;te[score]=np.nan
            te.loc[mask,score]=model.predict_proba(te.loc[mask,FEATURES_CHANGE])[:,1]
            np.testing.assert_allclose(original.predict_proba(te.loc[mask,FEATURES_CHANGE])[:,1],te.loc[mask,'score_DATE_'+target],rtol=0,atol=1e-15)
            dest=out/str(year);dest.mkdir(exist_ok=True);joblib.dump(model,dest/('PROCESS_'+target+'.joblib'))
            for f,v in zip(FEATURES_CHANGE,model[-1].coef_[0]):coefficients.append(dict(year=year,target=target,feature=f,standardized_coefficient=float(v)))
            audit=tr[['date','era','industry_code','target_available_date']].copy();audit['year']=year;audit['target']=target;audit['label']=y;audit['prefix_group']=refs;audit['old_weight']=old;audit['new_weight']=new;weights.append(audit)
            newdates=new.groupby(tr.date).sum();olddates=old.groupby(tr.date).sum();pos=y.eq(1)
            fits.append(dict(year=year,target=target,train_rows=len(tr),positive=positive,negative=negative,positive_prefix_groups=refs[pos].nunique(),
                latest_label_available=str(tr.target_available_date.max().date()),fitted_before=f'{year}-01-01',positive_old_mass=old[pos].sum(),positive_new_mass=new[pos].sum(),
                negative_old_mass=old[~pos].sum(),negative_new_mass=new[~pos].sum(),weight_ratio_p01=(new[pos]/old[pos]).quantile(.01),weight_ratio_p99=(new[pos]/old[pos]).quantile(.99),
                date_mass_ratio_p10=(newdates/olddates).quantile(.1),date_mass_ratio_p90=(newdates/olddates).quantile(.9),date_mass_ratio_max=(newdates/olddates).max(),scaler_identical=True))
        ranks=te.groupby('date')[['score_PROCESS_COVER','score_PROCESS_EARLY']].rank(method='average',pct=True)
        te['score_PROCESS_BALANCED']=ranks.mean(axis=1,skipna=False)
        scored.append(te);print('M04 fitted',year,flush=True)
    pd.concat(scored).to_parquet(out/'scored_catalog.parquet',index=False);pd.concat(weights).to_parquet(out/'training_weights.parquet',index=False)
    pd.DataFrame(fits).to_csv(out/'fit_audit.csv',index=False);pd.DataFrame(coefficients).to_csv(out/'coefficients.csv',index=False)
    (out/'receipt.json').write_text(json.dumps(dict(inputs={str(p):sha(p) for p in sources},artifacts={str(p.relative_to(out)):sha(p) for p in out.rglob('*') if p.is_file()}),indent=2)+'\n')


if __name__=='__main__':main()
