"""Fixed annual expanding fits. Scores are uncalibrated observation ranks."""
import json
import warnings
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier, export_text
from sklearn.exceptions import ConvergenceWarning
from audit_local_inputs import EP, sha
from v3_m01_prepare import FEATURES_BASE, FEATURES_CHANGE


def training_rows(panel, year):
    cutoff=pd.Timestamp(year=year,month=1,day=1)
    tr=panel[panel.eligible&panel.label.notna()&panel.label_available_date.lt(cutoff)].copy()
    assert tr.date.lt(cutoff).all() and tr.label_available_date.lt(cutoff).all()
    return tr


def main():
    root=EP/'outputs/v3_m01_preparation';out=EP/'outputs/v3_m01_models'
    if out.exists():raise FileExistsError(out)
    rec=json.loads((root/'receipt.json').read_text())
    for p,h in rec['inputs'].items():assert sha(Path(p))==h,p
    for p,h in rec['artifacts'].items():assert sha(root/p)==h,p
    panel=pd.read_parquet(root/'training_panel.parquet')
    out.mkdir();rows=[];scored=[];coefficients=[]
    sources=[root/'receipt.json',root/'training_panel.parquet',EP/'protocols/v3_r00/m01_plan.md',Path(__file__)]
    (out/'started.json').write_text(json.dumps({str(p):sha(p) for p in sources},indent=2)+'\n')
    for year in range(2020,2027):
        tr=training_rows(panel,year)
        te=panel[panel.date.dt.year.eq(year)].copy()
        pos=int(tr.label.sum());neg=int(tr.label.eq(0).sum())
        adequate=len(tr)>=1000 and pos>=50 and neg>=50
        if not adequate:raise ValueError(f'Insufficient preregistered support {year}: {len(tr)} / {pos} / {neg}; no invented scores')
        weights=1/tr.groupby('date').date.transform('size').to_numpy(float)
        weights*=len(weights)/weights.sum()
        for name,cols,model in [
            ('LR_BASE',FEATURES_BASE,make_pipeline(StandardScaler(),LogisticRegression(C=1,max_iter=2000,solver='lbfgs'))),
            ('LR_CHANGE',FEATURES_CHANGE,make_pipeline(StandardScaler(),LogisticRegression(C=1,max_iter=2000,solver='lbfgs'))),
            ('TREE_CHANGE',FEATURES_CHANGE,DecisionTreeClassifier(max_depth=3,min_samples_leaf=100,random_state=34101))]:
            kwargs={'logisticregression__sample_weight':weights} if name.startswith('LR') else {'sample_weight':weights}
            with warnings.catch_warnings():
                warnings.simplefilter('error',ConvergenceWarning)
                model.fit(tr[cols],tr.label.astype(int),**kwargs)
            mask=te.eligible
            te['score_'+name]=np.nan
            te.loc[mask,'score_'+name]=model.predict_proba(te.loc[mask,cols])[:,1]
            # Same predictions when evaluation-only labels and identities are absent.
            np.testing.assert_array_equal(model.predict_proba(te.loc[mask,cols].copy())[:,1],te.loc[mask,'score_'+name])
            dest=out/str(year);dest.mkdir(exist_ok=True)
            joblib.dump(model,dest/(name+'.joblib'))
            if name.startswith('LR'):
                for col,coef in zip(cols,model[-1].coef_[0]):coefficients.append(dict(year=year,model=name,feature=col,standardized_coefficient=float(coef)))
            else:(dest/(name+'.txt')).write_text(export_text(model,feature_names=cols))
            rows.append(dict(year=year,model=name,train_rows=len(tr),positive=pos,negative=neg,
                train_latest_date=str(tr.date.max().date()),latest_label_available=str(tr.label_available_date.max().date()),
                fitted_before=str(pd.Timestamp(year=year,month=1,day=1).date()),predicted_rows=int(mask.sum()),
                interpretation='Historical walk-forward simulation on reused local data; score not calibrated probability'))
        scored.append(te)
        print('Fitted',year,'train',len(tr),'positive',pos,'scoreable',int(te.eligible.sum()),flush=True)
    pd.concat(scored).to_parquet(out/'scored_catalog.parquet',index=False)
    pd.DataFrame(rows).to_csv(out/'fit_audit.csv',index=False)
    pd.DataFrame(coefficients).to_csv(out/'coefficients.csv',index=False)
    (out/'receipt.json').write_text(json.dumps(dict(inputs={str(p):sha(p) for p in sources},artifacts={str(p.relative_to(out)):sha(p) for p in out.rglob('*') if p.is_file()}),indent=2)+'\n')


if __name__=='__main__':main()
