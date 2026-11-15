"""Fixed target ablation; no label or feature tuning after outcomes."""
import json
import warnings
from pathlib import Path
import numpy as np
import pandas as pd
import joblib
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.exceptions import ConvergenceWarning
from audit_local_inputs import EP,sha
from v3_m01_prepare import FEATURES_CHANGE


def main():
    root=EP/'outputs/v3_m02_targets';old=EP/'outputs/v3_m01_models';out=EP/'outputs/v3_m02_models'
    if out.exists():raise FileExistsError(out)
    for directory in [root,old]:
        rec=json.loads((directory/'receipt.json').read_text())
        for rel,digest in rec['artifacts'].items():assert sha(directory/rel)==digest,rel
    panel=pd.read_parquet(root/'training_panel.parquet')
    targets={'LR_COVER':['parent_coverage_target','child_coverage_target'],'LR_EARLY_UNION':['parent_early_target','child_early_target'],'LR_CHILD':['child_coverage_target']}
    for name,columns in targets.items():
        panel['target_'+name]=panel[columns].max(axis=1,skipna=False)
    prior=pd.read_parquet(old/'scored_catalog.parquet',columns=['date','era','industry_code','score_LR_CHANGE']).rename(columns={'score_LR_CHANGE':'score_PARENT_EARLY'})
    panel=panel.merge(prior,on=['date','era','industry_code'],how='left',validate='one_to_one')
    out.mkdir();sources=[root/'receipt.json',root/'training_panel.parquet',old/'receipt.json',old/'scored_catalog.parquet',EP/'protocols/v3_r00/m02_model_plan.md',Path(__file__)]
    (out/'started.json').write_text(json.dumps({str(p):sha(p) for p in sources},indent=2)+'\n')
    fits=[];coefficients=[];scored=[]
    for year in range(2020,2027):
        cut=pd.Timestamp(year=year,month=1,day=1);te=panel[panel.date.dt.year.eq(year)].copy()
        for name in targets:
            target='target_'+name
            tr=panel[panel.eligible&panel[target].notna()&panel.target_available_date.lt(cut)].copy()
            positive=int(tr[target].sum());negative=int(tr[target].eq(0).sum())
            assert len(tr)>=1000 and positive>=50 and negative>=50,(year,name,len(tr),positive,negative)
            assert tr.date.lt(cut).all() and tr.target_available_date.lt(cut).all()
            weights=1/tr.groupby('date').date.transform('size').to_numpy(float);weights*=len(weights)/weights.sum()
            model=make_pipeline(StandardScaler(),LogisticRegression(C=1,max_iter=2000,solver='lbfgs'))
            with warnings.catch_warnings():
                warnings.simplefilter('error',ConvergenceWarning)
                model.fit(tr[FEATURES_CHANGE],tr[target].astype(int),logisticregression__sample_weight=weights)
            te['score_'+name]=np.nan;mask=te.eligible
            te.loc[mask,'score_'+name]=model.predict_proba(te.loc[mask,FEATURES_CHANGE])[:,1]
            dest=out/str(year);dest.mkdir(exist_ok=True);joblib.dump(model,dest/(name+'.joblib'))
            for col,coef in zip(FEATURES_CHANGE,model[-1].coef_[0]):coefficients.append(dict(year=year,model=name,feature=col,standardized_coefficient=float(coef)))
            fits.append(dict(year=year,model=name,train_rows=len(tr),positive=positive,negative=negative,latest_label_available=str(tr.target_available_date.max().date()),fitted_before=str(cut.date()),predicted_rows=int(mask.sum())))
        # Date-local ranks only: no future score distribution or probability interpretation.
        ranks=te.groupby('date')[['score_LR_COVER','score_LR_EARLY_UNION']].rank(method='average',pct=True)
        te['score_BALANCED']=ranks.mean(axis=1,skipna=False)
        assert te.loc[te.eligible,['score_PARENT_EARLY','score_LR_COVER','score_LR_EARLY_UNION','score_LR_CHILD','score_BALANCED']].notna().all().all()
        scored.append(te);print('M02 fitted',year,flush=True)
    d=pd.concat(scored);pd.testing.assert_series_equal(d.set_index(['date','era','industry_code']).score_PARENT_EARLY.sort_index(),prior.set_index(['date','era','industry_code']).score_PARENT_EARLY.sort_index(),check_names=False)
    d.to_parquet(out/'scored_catalog.parquet',index=False);pd.DataFrame(fits).to_csv(out/'fit_audit.csv',index=False);pd.DataFrame(coefficients).to_csv(out/'coefficients.csv',index=False)
    (out/'receipt.json').write_text(json.dumps(dict(inputs={str(p):sha(p) for p in sources},artifacts={str(p.relative_to(out)):sha(p) for p in out.rglob('*') if p.is_file()}),indent=2)+'\n')


if __name__=='__main__':main()
