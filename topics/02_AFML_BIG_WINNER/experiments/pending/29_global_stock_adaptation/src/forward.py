"""Prospective EP29 adapter; no global refitting or historical forecast backfill."""
import argparse
from common import *
from global_model import freeze
from hierarchical_model import one_origin
from diagnostics import calibration_context


def valid_origin(date,now,calendar):
    date=pd.Timestamp(date);now=pd.Timestamp(now)
    if now.tzinfo is not None:now=now.tz_convert('Asia/Shanghai').tz_localize(None)
    cal=pd.DatetimeIndex(calendar)
    assert date>=pd.Timestamp('2026-10-30') and date==now.normalize(),'future or backdated origin'
    assert now.hour>=16 and cal.max().to_period('M')>date.to_period('M')
    month=cal[cal.to_period('M')==date.to_period('M')]
    assert len(month) and date==month.max(),'not actual trading month end'
    return date


def verify_archive(path):
    path=Path(path);r=json.loads((path/'manifest.json').read_text())
    for name,h in r['files'].items():
        assert Path(name).name==name and digest(path/name)==h
    return r


def verify_lock():
    freeze();lock=json.loads((MANIFEST/'prospective_lock.json').read_text())
    for path,h in lock['files'].items():assert digest(EP/path)==h,path


def history_for(foundation,date,forecast_root,label_root):
    history=pd.read_parquet(CACHE/f'real_{foundation}_all.parquet')
    for path in sorted(Path(forecast_root).glob('*/manifest.json')):
        archive=path.parent;r=verify_archive(archive)
        assert pd.Timestamp(r['origin'])<date
        assert r['registration_sha256']==digest(MANIFEST/'preregistration.json')
        assert r['protocol_sha256']==digest(MANIFEST/'prospective_lock.json')
        pred=pd.read_parquet(archive/f'{foundation}_predictions.parquet')
        receipt_path=Path(label_root)/archive.name/'receipt.json'
        if receipt_path.exists():
            receipt=json.loads(receipt_path.read_text());lp=receipt_path.parent/'labels.parquet'
            assert receipt['forecast_manifest_sha256']==digest(path) and receipt['labels_sha256']==digest(lp)
            outcomes=pd.read_parquet(lp)
            assert (outcomes.label_end<date).all(),'unmatured attached labels'
            pred=pred.drop(columns=['actual','label_end']).merge(outcomes[['date','instrument','actual','label_end']],
                on=['date','instrument'],how='left',validate='one_to_one')
        history=pd.concat([history,pred],ignore_index=True)
    assert not history.duplicated(['date','instrument']).any()
    return history


def forecast(panel_path,receipts,calendar_path,date,ep28_archive,destination,forecast_root,label_root):
    verify_lock();now=pd.Timestamp.now(tz='Asia/Shanghai')
    date=valid_origin(date,now,pd.to_datetime(pd.read_csv(calendar_path,header=None)[0]))
    prior=verify_archive(ep28_archive);assert prior['origin']==str(date.date())
    assert prior['protocol_sha256']==digest(EP28/'outputs/manifests/prospective_lock.json')
    receipt=json.loads(Path(receipts).read_text())
    assert receipt['asof']==str(date.date()) and receipt['panel_sha256']==digest(panel_path)
    assert receipt['calendar_sha256']==digest(calendar_path)
    base_receipt=json.loads((Path(ep28_archive)/'source_receipts.json').read_text())
    base_path=Path(receipt['ep28_prepared_panel_path']);assert digest(base_path)==base_receipt['panel_sha256']
    for key in ['listing_metadata_source','industry_release_sources','price_vintage_limitations','ST_delisting_limitations',
                'corporate_action_limitations','source_response_files']:assert key in receipt
    assert receipt['source_response_files']
    for source in receipt['source_response_files']:
        assert digest(source['path'])==source['sha256']
        available=pd.Timestamp(source['available_at_shanghai'])
        if available.tzinfo is None:available=available.tz_localize('Asia/Shanghai')
        assert available<=now
    panel=pd.read_parquet(panel_path).sort_values(['date','instrument']).reset_index(drop=True)
    base=pd.read_parquet(base_path).sort_values(['date','instrument']).reset_index(drop=True)
    assert not panel.duplicated(['date','instrument']).any()
    assert panel.date.max()==date and (panel.feature_cutoff<=panel.date).all()
    # Every original EP28 field, including training rows and outcome vintage, must match.
    pd.testing.assert_frame_equal(panel[base.columns],base,check_exact=True)
    current=panel[panel.date==date].copy().reset_index(drop=True)
    assert len(current) and current.y_6.isna().all() and current.listing_date.notna().all()
    known=current.industry_id.ne('UNKNOWN')
    assert (current.loc[known,'industry_published']<date).all()
    old=pd.read_parquet(Path(ep28_archive)/'predictions.parquet')
    destination=Path(destination);assert destination.name==str(date.date())
    assert destination.parent.resolve()==Path(forecast_root).resolve()
    assert not destination.exists(),'immutable forecast already exists'
    staged=[];audits=[]
    template=pd.read_parquet(CACHE/'global_oos_M_R.parquet')
    rawcols=[c for c in template.columns if c not in ['actual','label_end','G','global_training_max_label',
        'global_training_cutoff','foundation','oos']]
    train=panel[(panel.date<date.to_period('Q').start_time)&(panel.end_6<date.to_period('Q').start_time)&panel.y_6.notna()]
    assert keyhash(train)==prior['training_keys_sha256']
    for foundation in ['M_R','L2']:
        p=old[old.model.eq(foundation)].sort_values('instrument').reset_index(drop=True)
        pd.testing.assert_frame_equal(p[['date','instrument']],current[['date','instrument']])
        z=current[rawcols].copy();z['G']=p.probability.to_numpy();z['actual']=np.nan;z['label_end']=pd.NaT
        assert z.G.between(0,1,inclusive='neither').all()
        z['global_training_max_label']=train.end_6.max();z['global_training_cutoff']=date.to_period('Q').start_time
        z['foundation']=foundation;z['oos']=True
        history=history_for(foundation,date,forecast_root,label_root)
        out,peers,audit=one_origin(z,history)
        out=out.merge(calibration_context(out,history),on=['date','instrument'],validate='one_to_one')
        staged.append((foundation,out,peers));audits.append(dict(foundation=foundation,**audit))
    destination.mkdir(parents=True,exist_ok=False)
    for foundation,out,peers in staged:
        out.to_parquet(destination/f'{foundation}_predictions.parquet',index=False)
        peers.to_parquet(destination/f'{foundation}_peers.parquet',index=False)
    write_json(destination/'adaptation.json',audits);write_json(destination/'source_receipts.json',receipt)
    write_json(destination/'manifest.json',dict(origin=str(date.date()),created_at_shanghai=now.isoformat(),
        ep28_manifest_sha256=digest(Path(ep28_archive)/'manifest.json'),
        registration_sha256=digest(MANIFEST/'preregistration.json'),protocol_sha256=digest(MANIFEST/'prospective_lock.json'),
        files={p.name:digest(p) for p in destination.iterdir() if p.is_file()},
        evidence='local hash commitment; no independent timestamp or source-vintage certification'))


def attach(archive,ep28_label_archive,destination):
    own=verify_archive(archive);other=Path(ep28_label_archive)
    r=json.loads((other/'receipt.json').read_text());path=other/'labels.parquet'
    assert r['forecast_manifest_sha256']==own['ep28_manifest_sha256'] and digest(path)==r['labels_sha256']
    y=pd.read_parquet(path);assert not y.duplicated(['date','instrument']).any()
    now=pd.Timestamp.now(tz='Asia/Shanghai').tz_localize(None)
    assert y.actual.notna().all() and np.isfinite(y.actual).all()
    assert (y.label_end<=now).all() and (y.label_end>=y.date+pd.DateOffset(months=6)).all()
    keys=pd.read_parquet(Path(archive)/'M_R_predictions.parquet')[['date','instrument']]
    check=y.merge(keys,on=['date','instrument'],how='left',indicator=True,validate='one_to_one')
    assert check._merge.eq('both').all()
    destination=Path(destination);assert destination.name==Path(archive).name
    destination.mkdir(parents=True,exist_ok=False);(destination/'labels.parquet').write_bytes(path.read_bytes())
    write_json(destination/'receipt.json',dict(forecast_manifest_sha256=digest(Path(archive)/'manifest.json'),
        labels_sha256=digest(path),ep28_receipt_sha256=digest(other/'receipt.json'),independent_confirmation=False))


def main():
    parser=argparse.ArgumentParser();sub=parser.add_subparsers(dest='command',required=True)
    f=sub.add_parser('forecast')
    for name in ['panel','receipts','calendar','date','ep28-archive','destination','forecast-root','label-root']:f.add_argument('--'+name,required=True)
    a=sub.add_parser('attach-labels')
    for name in ['archive','ep28-label-archive','destination']:a.add_argument('--'+name,required=True)
    failure=sub.add_parser('record-failure')
    for name in ['origin','reason','destination']:failure.add_argument('--'+name,required=True)
    args=parser.parse_args()
    if args.command=='forecast':forecast(args.panel,args.receipts,args.calendar,args.date,args.ep28_archive,args.destination,args.forecast_root,args.label_root)
    elif args.command=='attach-labels':attach(args.archive,args.ep28_label_archive,args.destination)
    else:
        path=Path(args.destination);path.parent.mkdir(parents=True,exist_ok=True)
        with path.open('x') as f:
            json.dump(dict(origin=args.origin,reason=args.reason,recorded_at_shanghai=pd.Timestamp.now(tz='Asia/Shanghai').isoformat(),
                forecast_created=False,backfill_permitted=False),f,ensure_ascii=False,indent=2)


if __name__=='__main__':main()
