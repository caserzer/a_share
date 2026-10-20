"""Immutable prospective forecasts and label-only receipts. No scheduling or trading."""
import argparse
import json
from pathlib import Path
import numpy as np
import pandas as pd
from core import *


def assert_frozen():
    lock=json.loads((OUT/'preregistration.json').read_text())
    assert all(digest(EP/k)==v for k,v in lock['files'].items()),'research source changed'


def validate_future_panel(panel, decision, now):
    decision=pd.Timestamp(decision);now=pd.Timestamp(now)
    assert decision>=pd.Timestamp('2026-10-30'),'must be post-freeze prospective date'
    assert decision<=now,'cannot create a future-dated forecast'
    assert not panel.duplicated(['date','instrument']).any()
    # A historical backfill after outcome realization cannot become prospective evidence.
    assert decision==now.normalize(),'freeze on decision date; late archives are retrospective'
    assert panel.date.max()<=decision
    test=panel[panel.date.eq(decision)].dropna(subset=CONFIG['eligibility_features']).copy()
    assert len(test)>0
    known=test.financial_available_date.notna()
    assert (test.loc[known,'financial_available_date']<decision).all()
    for h in CONFIG['horizons']:
        assert test[f'y_{h}'].isna().all(),'future labels must not be attached to forecast rows'
    return test


def forecast(panel_path, receipts_path, decision, destination):
    assert_frozen()
    now=pd.Timestamp.now(tz='Asia/Shanghai').tz_localize(None)
    panel=pd.read_parquet(panel_path)
    test=validate_future_panel(panel,decision,now)
    # Closing features require a completed market session; no pre-close snapshot accepted.
    assert now.hour>=16,'archive after close (16:00 Asia/Shanghai or later)'
    receipts=json.loads(Path(receipts_path).read_text())
    assert receipts['panel_sha256']==digest(panel_path)
    assert receipts['asof']==str(pd.Timestamp(decision).date())
    for field in ['price_source','universe_source','valuation_source','financial_source','vintage_limitations','corporate_action_limitations']:
        assert field in receipts and receipts[field] is not None
    destination=Path(destination)
    destination.mkdir(parents=True,exist_ok=False)
    test=test.sort_values(['date','instrument']).reset_index(drop=True)
    panel=panel.dropna(subset=CONFIG['eligibility_features']).sort_values(['date','instrument'])
    fit_cutoff=pd.Timestamp(decision).to_period('Q').start_time
    records=[];fit_receipts=[]
    for h in CONFIG['horizons']:
        train=panel[(panel.date<fit_cutoff)&(panel[f'end_{h}']<fit_cutoff)&panel[f'y_{h}'].notna()].copy()
        assert len(train)>1000 and train[f'end_{h}'].max()<fit_cutoff
        preds=baselines(train,test,h)
        for name in CONFIG['candidates']:
            model=fit_model(train,h,name)
            preds[name],_=predict_atoms(model,test,name)
            model.save_model(str(destination/f'{h}_{name}.cbm'))
        np.savez_compressed(destination/f'{h}_atoms.npz',**preds)
        fit_receipts.append(dict(horizon=h,train_rows=len(train),max_training_label=str(train[f'end_{h}'].max().date()),train_keys_sha256=hashlib.sha256(train[['date','instrument']].to_csv(index=False).encode()).hexdigest()))
        for name,atoms in preds.items():
            r=test[['date','instrument']].copy();r['horizon']=h;r['model']=name
            records.append(pd.concat([r,score(atoms,np.full(len(r),np.nan))],axis=1))
    test[['date','instrument']].to_parquet(destination/'keys.parquet',index=False)
    pd.concat(records,ignore_index=True).to_parquet(destination/'predictions.parquet',index=False)
    write_json(destination/'input_receipts.json',receipts)
    write_json(destination/'fit_receipts.json',fit_receipts)
    write_json(destination/'manifest.json',dict(created_at=now.isoformat(),decision_date=decision,
        preregistration_sha256=digest(OUT/'preregistration.json'),panel_sha256=digest(panel_path),
        files={p.name:digest(p) for p in sorted(destination.iterdir()) if p.is_file()},
        evidence='prospective only if external timestamp/source-vintage and population evidence hold; local hashes alone do not prove historical availability'))


def attach_labels(archive, labels_path, source_receipts, destination, asof):
    archive=Path(archive);m=json.loads((archive/'manifest.json').read_text())
    for name,value in m['files'].items():assert digest(archive/name)==value,'forecast modified'
    label=pd.read_parquet(labels_path)
    assert not label.duplicated(['date','instrument','horizon']).any()
    assert set(label.horizon).issubset(set(CONFIG['horizons']))
    assert label.actual.notna().all() and (label.actual>=-1).all()
    assert (label.label_end<=pd.Timestamp(asof)).all()
    assert pd.Timestamp(asof)<=pd.Timestamp.now(tz='Asia/Shanghai').tz_localize(None)
    for row in label.itertuples():
        assert row.label_end>=row.date+pd.DateOffset(months=row.horizon)
    keys=pd.read_parquet(archive/'keys.parquet')
    joined=label.merge(keys,on=['date','instrument'],how='left',indicator=True,validate='many_to_one')
    assert joined._merge.eq('both').all()
    sources=json.loads(Path(source_receipts).read_text())
    assert sources['labels_sha256']==digest(labels_path)
    destination=Path(destination);destination.mkdir(parents=True,exist_ok=False)
    label.to_parquet(destination/'labels.parquet',index=False)
    write_json(destination/'source_receipts.json',sources)
    write_json(destination/'receipt.json',dict(forecast_manifest_sha256=digest(archive/'manifest.json'),labels_sha256=digest(destination/'labels.parquet'),asof=asof,rows=len(label),
        scoring='labels archived without model selection; combine >=36 consecutive mature 6m origin months for one scheduled confirmation',
        source_limit='provide same-source origin/end prices, market calendar target and corporate-action/vintage receipts; API does not independently certify those claims'))


def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    f=sub.add_parser('forecast');f.add_argument('--panel',required=True);f.add_argument('--receipts',required=True);f.add_argument('--date',required=True);f.add_argument('--destination',required=True)
    l=sub.add_parser('attach-labels');l.add_argument('--archive',required=True);l.add_argument('--labels',required=True);l.add_argument('--receipts',required=True);l.add_argument('--destination',required=True);l.add_argument('--asof',required=True)
    a=p.parse_args()
    if a.command=='forecast':forecast(a.panel,a.receipts,a.date,a.destination)
    else:attach_labels(a.archive,a.labels,a.receipts,a.destination,a.asof)

if __name__=='__main__':main()
