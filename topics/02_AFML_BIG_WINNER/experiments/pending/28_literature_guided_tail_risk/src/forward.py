"""Prospective archive coordinated with an immutable same-date EP27 archive."""
import argparse
from scipy.special import expit,logit
from core import *
from run import freeze
from calibrate import history_rows,offset_fit


def valid_origin(date,now,calendar):
    date=pd.Timestamp(date);now=pd.Timestamp(now);calendar=pd.DatetimeIndex(calendar)
    assert date>=pd.Timestamp('2026-10-30') and date==now.normalize(),'cannot predate or backfill a prospective forecast'
    assert now.hour>=16
    assert calendar.max().to_period('M')>date.to_period('M')
    month=calendar[calendar.to_period('M')==date.to_period('M')]
    assert len(month) and date==month.max()
    return date


def verify_archive(path):
    path=Path(path);r=json.loads((path/'manifest.json').read_text())
    assert all(digest(path/k)==v for k,v in r['files'].items())
    return r


def forecast(panel_path,receipts,calendar_path,date,ep27_archive,destination,forecast_root,label_root):
    freeze();lock=json.loads((EP/'outputs/manifests/prospective_lock.json').read_text())
    assert all(digest(EP/k)==v for k,v in lock['files'].items())
    now=pd.Timestamp.now(tz='Asia/Shanghai').tz_localize(None)
    date=valid_origin(date,now,pd.to_datetime(pd.read_csv(calendar_path,header=None)[0]))
    panel=pd.read_parquet(panel_path).sort_values(['date','instrument']).reset_index(drop=True)
    assert not panel.duplicated(['date','instrument']).any() and panel.date.max()==date
    assert (panel.feature_cutoff<=panel.date).all()
    receipt=json.loads(Path(receipts).read_text())
    assert receipt['panel_sha256']==digest(panel_path) and receipt['calendar_sha256']==digest(calendar_path) and receipt['asof']==str(date.date())
    for k in ['population_rule','source_response_files','tail_pool_rule','industry_release_sources','price_vintage_limitations','ST_delisting_limitations','corporate_action_limitations']:assert k in receipt
    for r in receipt['source_response_files']:
        assert digest(r['path'])==r['sha256']
        available=pd.Timestamp(r['available_at_shanghai'])
        if available.tzinfo is not None:available=available.tz_convert('Asia/Shanghai').tz_localize(None)
        assert available<=now
    assert len(receipt['source_response_files'])>0
    tr,te=split(panel,6,date.to_period('Q'));te=te[te.date.eq(date)].reset_index(drop=True)
    assert len(tr)>1000 and len(te)>0 and te.y_6.isna().all()
    assert (panel.loc[panel.industry_id.ne('UNKNOWN'),'industry_published']<panel.loc[panel.industry_id.ne('UNKNOWN'),'date']).all()
    assert (panel.yield_observation_date<panel.date).all()
    prior=verify_archive(ep27_archive);assert prior['origin']==str(date.date())
    assert prior['training_keys_sha256']==keys_hash(tr)
    ep27_receipt=json.loads((Path(ep27_archive)/'source_receipts.json').read_text())
    prior_panel_path=Path(receipt['ep27_prepared_panel_path'])
    assert digest(prior_panel_path)==ep27_receipt['panel_sha256']
    prior_panel=pd.read_parquet(prior_panel_path)
    compare_cols=list(dict.fromkeys(['date','instrument','y_6','end_6']+C['risk_features']+C['market_features']+C['industry_features']))
    prior_train=prior_panel.merge(tr[['date','instrument']],on=['date','instrument'],validate='one_to_one').sort_values(['date','instrument']).reset_index(drop=True)
    pd.testing.assert_frame_equal(prior_train[compare_cols],tr[compare_cols].reset_index(drop=True))
    old=pd.read_parquet(Path(ep27_archive)/'predictions.parquet')
    old=old[old.model.isin(['B0','B1','M_R','M_RMI'])].copy()
    template=old[old.model.eq('M_R')].sort_values('instrument').reset_index(drop=True)
    pd.testing.assert_frame_equal(template[['date','instrument']],te[['date','instrument']])
    for col in list(dict.fromkeys(C['risk_features']+C['market_features']+C['industry_features'])):
        pd.testing.assert_series_equal(template[col],te[col],check_names=False)
    # Replay same-origin M_R on the exact prepared risk fields before accepting shared baseline.
    model=CatBoostClassifier();model.load_model(str(Path(ep27_archive)/'M_R.cbm'))
    np.testing.assert_allclose(predict(model,te,'M_R'),template.probability,rtol=0,atol=1e-14)
    destination=Path(destination);assert destination.name==str(date.date());destination.mkdir(parents=True,exist_ok=False)
    rows=[old];models=[]
    for name in C['fitted_candidates']:
        model=fit_model(tr,name,6);z=template.copy();z['model']=name;z['probability']=predict(model,te,name)
        z['model_version']=digest(EP/'outputs/manifests/preregistration.json');z['data_version']=digest(panel_path)
        rows.append(z);model.save_model(str(destination/f'{name}.cbm'));models.append(name)
    raw=pd.concat(rows,ignore_index=True)
    history=pd.read_parquet(CACHE/'all_predictions.parquet')
    for receipt_path in Path(label_root).glob('*/receipt.json'):
        r=json.loads(receipt_path.read_text());archive=Path(forecast_root)/receipt_path.parent.name
        verify_archive(archive);assert digest(archive/'manifest.json')==r['forecast_manifest_sha256']
        labels_path=receipt_path.parent/'labels.parquet';assert digest(labels_path)==r['labels_sha256']
        pred=pd.read_parquet(archive/'predictions.parquet');pred=pred[~pred.model.str.endswith('__offset')]
        outcomes=pd.read_parquet(labels_path)
        pred=pred.drop(columns=['actual','label_end']).merge(outcomes,on=['date','instrument'],how='left',validate='many_to_one')
        history=pd.concat([history,pred],ignore_index=True)
    assert not history.duplicated(['model','date','instrument']).any()
    cal=[]
    for name in C['calibration']['models']:
        h=history_rows(history[history.model.eq(name)],date);e=int((h.actual<-.2).sum())
        enough=h.date.nunique()>=12 and min(e,len(h)-e)>=30
        shift=offset_fit(h.probability,labels(h.actual),h.date) if enough else 0.
        z=raw[raw.model.eq(name)].copy();z['model']=name+'__offset'
        if enough:z['probability']=expit(logit(np.clip(z.probability,1e-8,1-1e-8))+shift)
        rows.append(z);cal.append(dict(model=name,shift=shift,fitted=bool(enough),history_keys_sha256=keys_hash(h)))
    prediction=pd.concat(rows,ignore_index=True)
    prediction['actual']=np.nan;prediction['label_end']=pd.NaT
    prediction['confidence']='prospective_unconfirmed';prediction['delta_b1']=prediction.probability-prediction.b1_probability if 'b1_probability' in prediction else np.nan
    prediction.to_parquet(destination/'predictions.parquet',index=False)
    write_json(destination/'calibration.json',cal);write_json(destination/'source_receipts.json',receipt)
    write_json(destination/'manifest.json',dict(origin=str(date.date()),created_at_shanghai=now.isoformat(),
        ep27_manifest_sha256=digest(Path(ep27_archive)/'manifest.json'),registration_sha256=digest(EP/'outputs/manifests/preregistration.json'),
        protocol_sha256=digest(EP/'outputs/manifests/prospective_lock.json'),training_keys_sha256=keys_hash(tr),
        files={p.name:digest(p) for p in destination.iterdir() if p.is_file()},
        evidence='local commitments require independent timestamp and source-vintage audit'))


def attach(archive,ep27_label_archive,destination):
    own=verify_archive(archive);other=Path(ep27_label_archive);receipt=json.loads((other/'receipt.json').read_text())
    assert receipt['forecast_manifest_sha256']==own['ep27_manifest_sha256']
    path=other/'labels.parquet';assert digest(path)==receipt['labels_sha256']
    y=pd.read_parquet(path);assert not y.duplicated(['date','instrument']).any()
    assert (y.label_end<=pd.Timestamp.now(tz='Asia/Shanghai').tz_localize(None)).all()
    pred=pd.read_parquet(Path(archive)/'predictions.parquet');keys=pred[pred.model.eq('M_R')][['date','instrument']]
    check=y.merge(keys,on=['date','instrument'],how='left',indicator=True,validate='one_to_one');assert check._merge.eq('both').all()
    destination=Path(destination);destination.mkdir(parents=True,exist_ok=False)
    (destination/'labels.parquet').write_bytes(path.read_bytes())
    write_json(destination/'receipt.json',dict(forecast_manifest_sha256=digest(Path(archive)/'manifest.json'),
        labels_sha256=digest(path),ep27_receipt_sha256=digest(other/'receipt.json'),independent_confirmation=False))


def main():
    parser=argparse.ArgumentParser();s=parser.add_subparsers(dest='command',required=True)
    f=s.add_parser('forecast')
    for name in ['panel','receipts','calendar','date','ep27-archive','destination','forecast-root','label-root']:f.add_argument('--'+name,required=True)
    a=s.add_parser('attach-labels')
    for name in ['archive','ep27-label-archive','destination']:a.add_argument('--'+name,required=True)
    args=parser.parse_args()
    if args.command=='forecast':forecast(args.panel,args.receipts,args.calendar,args.date,args.ep27_archive,args.destination,args.forecast_root,args.label_root)
    else:attach(args.archive,args.ep27_label_archive,args.destination)


if __name__=='__main__':main()
