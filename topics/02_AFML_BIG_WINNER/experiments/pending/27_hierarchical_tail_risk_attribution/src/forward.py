"""Future prepared-data forecast freezer, separated from immutable later outcomes."""
import argparse,importlib.util
from scipy.special import logit
from core import *
from calibrate import fit_offset,apply_offset,mature_calibration_rows


def check_locks():
    for name in ['preregistration.json','prospective_protocol_lock.json']:
        lock=json.loads((OUT/name).read_text());assert all(digest(EP/k)==v for k,v in lock['files'].items())


def valid_origin(date,now,calendar):
    date=pd.Timestamp(date);now=pd.Timestamp(now);calendar=pd.DatetimeIndex(calendar)
    assert date>=pd.Timestamp('2026-10-30') and date==now.normalize(),'no future-dated or retrospective archive'
    assert now.hour>=16,'freeze after Shanghai 16:00'
    assert calendar.max().to_period('M')>date.to_period('M')
    month=calendar[calendar.to_period('M')==date.to_period('M')];assert len(month) and month.max()==date
    return date


def check_prepared(panel,date):
    assert not panel.duplicated(['date','instrument']).any() and panel.date.max()<=date
    p=panel.dropna(subset=C['eligibility_features']).copy().sort_values(['date','instrument']);test=p[p.date.eq(date)].reset_index(drop=True);assert len(test)
    assert test.y_6.isna().all()
    for name in C['candidates']:assert set(feature_names(name)).issubset(p.columns)
    finance=p.financial_available_date.notna();assert (p.loc[finance,'financial_available_date']<p.loc[finance,'date']).all()
    reported=[c for c in C['financial_features'] if c not in ['financial_available','financial_age_days']]
    assert (~p[reported].notna().any(axis=1)|finance).all(),'nonmissing financial values require an availability date'
    known=p.industry_id.ne('UNKNOWN');assert (p.loc[known,'industry_published']<p.loc[known,'date']).all()
    assert (p.yield_observation_date<p.date).all()
    assert test[C['market_features']].nunique(dropna=False).le(1).all(),'market state must be common within date'
    return p,test


def check_confirmation_gate(months,events,event_months,detectable_effect):
    if months not in C['prospective']['checkpoints']:return dict(ready=False,reason='not a fixed 36/48/60-origin checkpoint')
    if events<300 or event_months<24:return dict(ready=False,reason='insufficient event or event-month count')
    if detectable_effect>C['prospective']['important_brier_effect']:return dict(ready=False,reason='insufficient approximate power for 0.002 effect')
    return dict(ready=True,reason='quantity/power gate only; not a scientific success label')


def collect_history(forecast_root,label_root):
    history=pd.read_parquet(CACHE/'all_predictions.parquet');history=history[history.horizon.eq(6)].copy();parts=[history]
    if not forecast_root or not label_root:return history
    archives={}
    for p in Path(forecast_root).glob('*/manifest.json'):
        record=json.loads(p.read_text());assert all(digest(p.parent/k)==v for k,v in record['files'].items())
        assert pd.Timestamp(record['created_at_shanghai']).normalize()==pd.Timestamp(record['origin'])
        assert record['registration_sha256']==digest(OUT/'preregistration.json');archives[digest(p)]=p.parent
    for p in Path(label_root).glob('*/receipt.json'):
        record=json.loads(p.read_text());archive=archives[record['forecast_manifest_sha256']];labels_path=p.parent/'labels.parquet';assert digest(labels_path)==record['labels_sha256']
        outcome=pd.read_parquet(labels_path);pred=pd.read_parquet(archive/'predictions.parquet');pred=pred[pred.model.isin(list(C['candidates'])+['B0','B1'])]
        pred=pred.drop(columns=['actual','label_end'],errors='ignore').merge(outcome,on=['date','instrument'],how='left',validate='many_to_one');parts.append(pred)
    allrows=pd.concat(parts,ignore_index=True);assert not allrows.duplicated(['model','date','instrument']).any(),'duplicate/revised predictions or labels'
    return allrows


def forecast(panel_path,receipt_path,calendar_path,date,destination,forecast_root=None,label_root=None):
    check_locks();calendar=pd.DatetimeIndex(pd.to_datetime(pd.read_csv(calendar_path,header=None)[0]));now=pd.Timestamp.now(tz='Asia/Shanghai').tz_localize(None);date=valid_origin(date,now,calendar)
    panel,test=check_prepared(pd.read_parquet(panel_path),date);receipt=json.loads(Path(receipt_path).read_text());assert receipt['panel_sha256']==digest(panel_path) and receipt['calendar_sha256']==digest(calendar_path) and receipt['asof']==str(date.date())
    for key in ['population_rule','market_state_sources','industry_release_sources','financial_vintage_limitations','valuation_vintage_limitations','ST_delisting_limitations','corporate_action_limitations']:
        assert key in receipt
    cutoff=date.to_period('Q').start_time;train=panel[(panel.date<cutoff)&(panel.end_6<cutoff)&panel.y_6.notna()].copy();assert len(train)>1000
    assert train.industry_id.nunique()<=255
    destination=Path(destination);assert destination.name==str(date.date());destination.mkdir(parents=True,exist_ok=False)
    spec=importlib.util.spec_from_file_location('frozen_ep25_core',EP25/'src/core.py');old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
    b1=(old.baselines(train,test,6)['B1']<-.2).mean(axis=1);prob={'B0':np.full(len(test),float((train.y_6<-.2).mean())),'B1':b1}
    for name in C['candidates']:
        model=fit_model(train,name,6);prob[name]=predict(model,test,name);model.save_model(str(destination/f'{name}.cbm'))
    history=collect_history(forecast_root,label_root);calibration=[]
    for name in C['calibration']['models']:
        h=mature_calibration_rows(history[history.model.eq(name)],date);events=int((h.actual<-.2).sum());enough=h.date.nunique()>=12 and min(events,len(h)-events)>=30
        for method in ['global','state']:
            fit=fit_offset(h.probability,labels(h.actual),h[C['calibration']['state_features']],h.date,state=method=='state') if enough else None
            valid=fit is not None and fit['success'];prob[name+'__'+method]=apply_offset(prob[name],test[C['calibration']['state_features']],fit) if valid else prob[name].copy()
            calibration.append(dict(model=name,method=method,fit=fit,raw_fallback=not valid,history_keys_sha256=keys_hash(h),max_label=str(h.label_end.max()) if len(h) else None))
    rows=[]
    for name,p in prob.items():
        r=test.drop(columns=[c for c in test if c.startswith('y_') or c.startswith('end_') or c.startswith('target_')]).copy();r['model']=name;r['probability']=p;r['actual']=np.nan;r['label_end']=pd.NaT;r['target_date']=date+pd.DateOffset(months=6);r['horizon']=6
        r['data_version']=digest(panel_path);r['model_version']=digest(OUT/'preregistration.json');r['confidence']='prospective_unconfirmed';rows.append(r)
    pd.concat(rows,ignore_index=True).to_parquet(destination/'predictions.parquet',index=False);write_json(destination/'calibration.json',calibration);write_json(destination/'source_receipts.json',receipt)
    write_json(destination/'manifest.json',dict(origin=str(date.date()),created_at_shanghai=now.isoformat(),registration_sha256=digest(OUT/'preregistration.json'),protocol_sha256=digest(OUT/'prospective_protocol_lock.json'),
        training_keys_sha256=keys_hash(train),max_training_label=str(train.end_6.max().date()),files={p.name:digest(p) for p in destination.iterdir() if p.is_file()},
        evidence='requires independent timestamp and original-vintage/source audit; local hashes do not certify those facts'))


def attach(archive,labels_path,receipt_path,asof,destination):
    archive=Path(archive);manifest=json.loads((archive/'manifest.json').read_text());assert all(digest(archive/k)==v for k,v in manifest['files'].items())
    y=pd.read_parquet(labels_path);assert not y.duplicated(['date','instrument']).any() and np.isfinite(y.actual).all() and y.actual.ge(-1).all()
    assert np.isfinite(y[['start_close','end_close']].to_numpy()).all() and y.start_close.gt(0).all() and y.end_close.gt(0).all()
    assert (y.label_end<=pd.Timestamp(asof)).all() and pd.Timestamp(asof)<=pd.Timestamp.now(tz='Asia/Shanghai').tz_localize(None)
    receipt=json.loads(Path(receipt_path).read_text());assert receipt['labels_sha256']==digest(labels_path)
    for field in ['same_source_same_vintage_price_response_sha256','corporate_action_limitations','missing_outcomes','calendar_path','calendar_sha256']:assert field in receipt
    np.testing.assert_allclose(y.end_close/y.start_close-1,y.actual,atol=1e-12,rtol=0)
    calendar_path=Path(receipt['calendar_path']);assert digest(calendar_path)==receipt['calendar_sha256'];calendar=pd.DatetimeIndex(pd.to_datetime(pd.read_csv(calendar_path,header=None)[0]))
    pred=pd.read_parquet(archive/'predictions.parquet');keys=pred[pred.model.eq('B1')][['date','instrument','target_date']]
    joined=y.merge(keys,on=['date','instrument'],how='left',validate='one_to_one',indicator=True);assert joined._merge.eq('both').all()
    idx=calendar.searchsorted(pd.DatetimeIndex(joined.target_date));assert (idx<len(calendar)).all();np.testing.assert_array_equal(joined.label_end,calendar[idx].to_numpy())
    destination=Path(destination);destination.mkdir(parents=True,exist_ok=False);y[['date','instrument','actual','label_end']].to_parquet(destination/'labels.parquet',index=False);write_json(destination/'source_receipts.json',receipt)
    write_json(destination/'receipt.json',dict(forecast_manifest_sha256=digest(archive/'manifest.json'),labels_sha256=digest(destination/'labels.parquet'),asof=asof,independent_confirmation=False))


def main():
    p=argparse.ArgumentParser(description=__doc__);s=p.add_subparsers(dest='command',required=True)
    f=s.add_parser('forecast')
    for key in ['panel','receipts','calendar','date','destination']:f.add_argument('--'+key,required=True)
    f.add_argument('--forecast-root');f.add_argument('--label-root')
    a=s.add_parser('attach-labels')
    for key in ['archive','labels','receipts','asof','destination']:a.add_argument('--'+key,required=True)
    args=p.parse_args()
    if args.command=='forecast':forecast(args.panel,args.receipts,args.calendar,args.date,args.destination,args.forecast_root,args.label_root)
    else:attach(args.archive,args.labels,args.receipts,args.asof,args.destination)

if __name__=='__main__':main()
