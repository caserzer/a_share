"""One planned confirmation after 36 consecutive mature 6m forecast origins."""
import argparse
import json
from pathlib import Path
import numpy as np
import pandas as pd
from core import *
from prospective import assert_frozen


def require_confirmation_origins(dates):
    origins=pd.DatetimeIndex(sorted(set(pd.to_datetime(dates))))
    assert len(origins)>=CONFIG['minimum_prospective_months'],'no performance scoring before 36 mature origin months'
    periods=origins.to_period('M')
    assert not periods.duplicated().any()
    assert np.diff(periods.asi8).max()==1,'confirmation requires consecutive origin months'
    # Single planned test: first 36 origins, never extend sample until a positive result.
    return origins[:CONFIG['minimum_prospective_months']]


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--forecasts',required=True);p.add_argument('--labels',required=True);p.add_argument('--destination',required=True)
    a=p.parse_args();assert_frozen()
    archives={}
    for path in sorted(Path(a.forecasts).glob('*/manifest.json')):
        m=json.loads(path.read_text())
        assert m['preregistration_sha256']==digest(OUT/'preregistration.json')
        for name,value in m['files'].items():assert digest(path.parent/name)==value
        assert pd.Timestamp(m['created_at']).date()==pd.Timestamp(m['decision_date']).date()
        archives[digest(path)]=path.parent
    labels=[];receipts=[]
    for path in sorted(Path(a.labels).glob('*/receipt.json')):
        r=json.loads(path.read_text());key=r['forecast_manifest_sha256']
        assert key in archives
        lp=path.parent/'labels.parquet';assert digest(lp)==r['labels_sha256']
        frame=pd.read_parquet(lp);frame['archive_hash']=key
        labels.append(frame);receipts.append(dict(path=str(path),sha256=digest(path)))
    assert labels,'no archived labels'
    labels=pd.concat(labels,ignore_index=True)
    assert not labels.duplicated(['date','instrument','horizon']).any(),'duplicate or revised archived labels require explicit audit'
    mature6=labels[labels.horizon==6]
    dates=require_confirmation_origins(mature6.date)
    # Gate above prevents early performance inspection; all 36 origin months are kept.
    rows=[];coverage=[]
    for date in dates:
        for h in CONFIG['horizons']:
            subset=labels[labels.date.eq(date)&labels.horizon.eq(h)]
            if subset.empty:continue
            assert subset.archive_hash.nunique()==1
            archive=archives[subset.archive_hash.iloc[0]]
            keys=pd.read_parquet(archive/'keys.parquet')
            outcomes=keys.merge(subset[['date','instrument','actual','label_end']],on=['date','instrument'],how='left',validate='one_to_one')
            coverage.append(dict(date=str(date.date()),horizon=h,forecast_rows=len(keys),observed=int(outcomes.actual.notna().sum()),missing=int(outcomes.actual.isna().sum())))
            with np.load(archive/f'{h}_atoms.npz') as atoms:
                for model in ['B0','B1']+list(CONFIG['candidates']):
                    scores=score(atoms[model],outcomes.actual)
                    rows.append(dict(date=date,horizon=h,model=model,**{c:float(scores[c].mean()) for c in ['crps','brier','tail_brier','cover05','cover10','cover50','cover90','cover95','coverage90']}))
    destination=Path(a.destination);destination.mkdir(parents=True,exist_ok=False)
    monthly=pd.DataFrame(rows);monthly.to_csv(destination/'monthly_scores.csv',index=False)
    pd.DataFrame(coverage).to_csv(destination/'outcome_coverage.csv',index=False)
    monthly.groupby(['horizon','model']).mean(numeric_only=True).to_csv(destination/'summary.csv')
    contrasts=[]
    for h,g in monthly.groupby('horizon'):
        for model in CONFIG['candidates']:
            for baseline in ['B0','B1']:
                for metric in ['crps','brier','tail_brier']:
                    d=paired(g[g.model.eq(model)],g[g.model.eq(baseline)],metric)
                    contrasts.append(dict(horizon=h,candidate=model,baseline=baseline,metric=metric,**interval(d,h)))
    pd.DataFrame(contrasts).to_csv(destination/'paired_intervals.csv',index=False)
    write_json(destination/'confirmation_receipt.json',dict(forecast_manifests=list(archives),label_receipts=receipts,first_origin=str(dates.min().date()),last_origin=str(dates.max().date()),months=len(dates),
        preregistration_sha256=digest(OUT/'preregistration.json'),result='requires calibration, tail, ablation and state robustness review before preliminary support; CI alone is insufficient',
        population='legacy selection/vintage limitations still apply; source receipts must be audited',files={p.name:digest(p) for p in destination.iterdir() if p.is_file()}))

if __name__=='__main__':main()
