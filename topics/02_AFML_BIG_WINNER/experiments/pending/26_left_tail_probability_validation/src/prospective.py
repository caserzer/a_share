"""Immutable future binary forecasts; separate labels and event/power-gated confirmation."""
import argparse
import importlib.util
from core import *


def frozen_check():
    lock=json.loads((OUT/'preregistration.json').read_text())
    assert all(digest(EP/k)==v for k,v in lock['files'].items())
    p=OUT/'prospective_protocol_lock.json'
    assert p.exists(),'seal prospective protocol before any future forecast'
    locked=json.loads(p.read_text());assert all(digest(EP/k)==v for k,v in locked['files'].items())


def validate_date(decision,now,calendar):
    d=pd.Timestamp(decision);now=pd.Timestamp(now)
    assert d>=pd.Timestamp('2026-10-30')
    assert d==now.normalize(),'forecast must be frozen on decision day; no future or late archive'
    assert now.hour>=16,'freeze only after Shanghai 16:00'
    calendar=pd.DatetimeIndex(calendar)
    assert calendar.is_monotonic_increasing and not calendar.duplicated().any()
    assert calendar.max().to_period('M')>d.to_period('M'),'calendar must cover beyond decision month'
    month=calendar[calendar.to_period('M')==d.to_period('M')]
    assert len(month) and month.max()==d,'must be the final actual market session of month'
    return d


def future_features(panel):
    p=panel.copy();p['financial_age_days']=(p.date-p.financial_report_date).dt.days
    p['state_turnover']=p.groupby('date').turnover21.transform('mean')
    p['vol_x_market_vol']=p.vol63*p.market_vol63;p['vol_x_credit']=p.vol63*p.credit_spread_3y
    return p


def load_ep25_core():
    spec=importlib.util.spec_from_file_location('ep25_frozen_core',PREV/'src/core.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def forecast(panel_path,receipts_path,calendar_path,date,destination):
    frozen_check();now=pd.Timestamp.now(tz='Asia/Shanghai').tz_localize(None)
    calendar=pd.DatetimeIndex(pd.to_datetime(pd.read_csv(calendar_path,header=None)[0]));date=validate_date(date,now,calendar)
    raw=pd.read_parquet(panel_path);assert not raw.duplicated(['date','instrument']).any() and raw.date.max()<=date
    panel=future_features(raw.dropna(subset=PREVC['eligibility_features'])).sort_values(['date','instrument']).reset_index(drop=True)
    test=panel[panel.date.eq(date)].reset_index(drop=True);assert len(test)
    assert test.y_6.isna().all(),'no attached future outcome; future target dates may already be known'
    available=panel.financial_available_date.notna();assert (panel.loc[available,'financial_available_date']<panel.loc[available,'date']).all()
    assert (panel.yield_observation_date<panel.date).all()
    source=json.loads(Path(receipts_path).read_text())
    assert source['panel_sha256']==digest(panel_path) and source['calendar_sha256']==digest(calendar_path) and source['asof']==str(date.date())
    for name in ['price_source','universe_source','financial_vintage_evidence','valuation_vintage_evidence','corporate_action_limitations','calendar_source']:
        assert name in source
    cutoff=date.to_period('Q').start_time
    train=panel[(panel.date<cutoff)&(panel.end_6<cutoff)&panel.y_6.notna()].copy();assert len(train)>1000
    destination=Path(destination);destination.mkdir(parents=True,exist_ok=False)
    old=load_ep25_core();oldbaselines=old.baselines(train,test,6);probs={};quantiles={}
    probs['B0']={k:np.full(len(test),float((train.y_6<t).mean())) for k,t in THRESHOLDS.items()}
    b0q=np.quantile(train.y_6,[.05,.1]);quantiles['B0']=np.tile(b0q,(len(test),1)).T
    probs['B1']={k:(oldbaselines['B1']<t).mean(axis=1) for k,t in THRESHOLDS.items()};quantiles['B1']=np.quantile(oldbaselines['B1'],[.05,.1],axis=1)
    for name,oldname in OLD_MODELS.items():
        if name=='B1':continue
        model=old.fit_model(train,6,oldname);atoms,_=old.predict_atoms(model,test,oldname)
        model.save_model(str(destination/f'{name}.cbm'))
        probs[name]={k:(atoms<t).mean(axis=1) for k,t in THRESHOLDS.items()};quantiles[name]=np.quantile(atoms,[.05,.1],axis=1)
    for name in C['candidates']:
        p={}
        for k,t in THRESHOLDS.items():
            model=fit_classifier(train,name,t);p[k]=predict(model,test,name);model.save_model(str(destination/f'{name}_{k}.cbm'))
        p10,p20,p30=coherence(p[10],p[20],p[30]);probs[name]={10:p10,20:p20,30:p30}
    targets=pd.DatetimeIndex([d+pd.DateOffset(months=6) for d in test.date]);idx=calendar.searchsorted(targets)
    ends=np.full(len(test),np.datetime64('NaT'),dtype='datetime64[ns]');known=idx<len(calendar)
    ends[known]=calendar[idx[known]].to_numpy()
    records=[]
    for name in ALL_MODELS:
        r=test[['date','instrument','financial_available_date','financial_report_date','yield_observation_date','financial_age_days','financial_available']].copy()
        r['target_date']=targets;r['label_target']=ends;r['model']=name;r['model_version']='EP26-fixed-v1';r['data_version']=digest(panel_path);r['confidence']='prospective_unconfirmed';r['calibration_version']='none-v1'
        cols=feature_names(name) if name in C['candidates'] else C['risk_features']
        r['feature_available_fraction']=test[cols].notna().mean(axis=1) if name!='B0' else 1.
        for k in THRESHOLDS:r[f'p_loss{k}']=probs[name][k];r[f'b0_loss{k}']=probs['B0'][k];r[f'b1_loss{k}']=probs['B1'][k];r[f'delta_b1_loss{k}']=probs[name][k]-probs['B1'][k]
        r['q05']=quantiles[name][0] if name in quantiles else np.nan;r['q10']=quantiles[name][1] if name in quantiles else np.nan
        records.append(r)
    pd.concat(records,ignore_index=True).to_parquet(destination/'predictions.parquet',index=False)
    test[['date','instrument']].to_parquet(destination/'keys.parquet',index=False)
    write_json(destination/'input_receipts.json',source)
    write_json(destination/'manifest.json',dict(decision_date=str(date.date()),created_at_shanghai=now.isoformat(),preregistration_sha256=digest(OUT/'preregistration.json'),
        prospective_protocol_sha256=digest(OUT/'prospective_protocol_lock.json'),max_training_label=str(train.end_6.max().date()),
        train_keys_sha256=hashlib.sha256(train[['date','instrument']].to_csv(index=False).encode()).hexdigest(),
        files={p.name:digest(p) for p in destination.iterdir() if p.is_file()},evidence='requires externally credible timestamps and historical-vintage source audit; local hashes alone are insufficient'))


def attach_labels(archive,labels_path,receipts_path,asof,destination):
    archive=Path(archive);manifest=json.loads((archive/'manifest.json').read_text())
    assert all(digest(archive/k)==v for k,v in manifest['files'].items())
    labels=pd.read_parquet(labels_path);assert not labels.duplicated(['date','instrument']).any()
    assert labels.actual.notna().all() and np.isfinite(labels.actual).all() and (labels.actual>=-1).all()
    assert (labels.label_end<=pd.Timestamp(asof)).all();assert pd.Timestamp(asof)<=pd.Timestamp.now(tz='Asia/Shanghai').tz_localize(None)
    predictions=pd.read_parquet(archive/'predictions.parquet');keys=predictions[predictions.model=='B1'][['date','instrument','target_date','label_target']]
    checked=labels.merge(keys,on=['date','instrument'],validate='one_to_one',how='left',indicator=True)
    assert checked._merge.eq('both').all()
    receipts=json.loads(Path(receipts_path).read_text());assert receipts['labels_sha256']==digest(labels_path)
    calendar_path=Path(receipts['calendar_path']);assert digest(calendar_path)==receipts['calendar_sha256']
    calendar=pd.DatetimeIndex(pd.to_datetime(pd.read_csv(calendar_path,header=None)[0]))
    target_idx=calendar.searchsorted(pd.DatetimeIndex(checked.target_date));assert (target_idx<len(calendar)).all()
    np.testing.assert_array_equal(checked.label_end.to_numpy(),calendar[target_idx].to_numpy())
    available=checked.label_target.notna()
    assert (checked.loc[available,'label_end']==checked.loc[available,'label_target']).all()
    for name in ['price_source','origin_price_snapshot_sha256','endpoint_source_sha256','corporate_action_limitations','missing_outcomes']:
        assert name in receipts
    destination=Path(destination);destination.mkdir(parents=True,exist_ok=False);labels.to_parquet(destination/'labels.parquet',index=False)
    write_json(destination/'source_receipts.json',receipts)
    write_json(destination/'receipt.json',dict(forecast_manifest_sha256=digest(archive/'manifest.json'),labels_sha256=digest(destination/'labels.parquet'),asof=asof,rows=len(labels),
        note='append labels once per origin; no duplicate or revised keys accepted by confirmation'))


def confirmation_gate(monthly,events,event_months):
    dates=pd.DatetimeIndex(sorted(monthly.date.unique()));periods=dates.to_period('M')
    if len(dates)<36:return dict(ready=False,reason='fewer than 36 mature origins')
    assert not periods.duplicated().any() and (np.diff(periods.asi8)==1).all(),'origin months must be consecutive'
    gate={36,48,60}
    if len(dates) not in gate:return dict(ready=False,reason='not a predeclared gate: 36/48/60 origins')
    if events<300 or event_months<24:return dict(ready=False,reason='insufficient events or event-bearing months')
    a=monthly[monthly.model.eq('M_VF')];b=monthly[monthly.model.eq('M_R')]
    delta=paired(a,b,'brier');uncertainty=ci(delta,6);important=C['prospective']['important_absolute_brier_improvement']
    enough=important>=uncertainty['detectable_80pct_effect_approx']
    return dict(ready=bool(enough),reason='power gate passed' if enough else 'insufficient approximate power for fixed 0.002 effect',events=events,event_months=event_months,months=len(dates),
        detectable_80pct_effect_approx=uncertainty['detectable_80pct_effect_approx'])


def confirmation(forecasts,labels,destination):
    frozen_check();archives={};marker=Path(forecasts)/'.ep26_confirmation_once.json'
    assert not marker.exists(),'planned confirmation already executed; no repeated testing after results'
    for p in sorted(Path(forecasts).glob('*/manifest.json')):
        manifest=json.loads(p.read_text());assert manifest['preregistration_sha256']==digest(OUT/'preregistration.json')
        assert manifest['prospective_protocol_sha256']==digest(OUT/'prospective_protocol_lock.json')
        assert all(digest(p.parent/k)==v for k,v in manifest['files'].items());archives[digest(p)]=p.parent
    records=[];events=0;event_dates=set();seen=set();all_labels=[]
    for rp in sorted(Path(labels).glob('*/receipt.json')):
        receipt=json.loads(rp.read_text());archive=archives[receipt['forecast_manifest_sha256']]
        labels_path=rp.parent/'labels.parquet';assert digest(labels_path)==receipt['labels_sha256']
        y=pd.read_parquet(labels_path)
        all_labels.append(y)
        for row in y.itertuples():
            key=(row.date,row.instrument);assert key not in seen,'duplicate or revised labels';seen.add(key)
            if row.actual<-.2:events+=1;event_dates.add(row.date)
        pred=pd.read_parquet(archive/'predictions.parquet').merge(y,on=['date','instrument'],how='left',validate='many_to_one')
        for (name,date),g in pred.groupby(['model','date']):
            result=point_metrics(g.p_loss20,g.actual,-.2)
            if result is not None:records.append(dict(model=name,date=date,**result))
    monthly=pd.DataFrame(records);assert len(monthly)
    labels_frame=pd.concat(all_labels,ignore_index=True)
    dates=sorted(monthly.date.unique());gate=dict(ready=False,reason='fewer than 36 mature origins');checks=[]
    # Inspect fixed gates in order; direction of the estimated effect never selects a window.
    for window in [36,48,60]:
        if len(dates)<window:break
        origins=dates[:window];sub=monthly[monthly.date.isin(origins)]
        labels_sub=labels_frame[labels_frame.date.isin(origins)]
        event=labels_sub.actual<-.2
        gate=confirmation_gate(sub,int(event.sum()),labels_sub.loc[event,'date'].nunique());checks.append(gate)
        if gate['ready']:monthly=sub;break
    destination=Path(destination);destination.mkdir(parents=True,exist_ok=False);write_json(destination/'gate.json',dict(selected=gate,checks=checks))
    if not gate['ready']:return
    # One planned confirmation: caller uses an immutable destination, never retries after an unfavorable result.
    monthly.to_csv(destination/'monthly_scores.csv',index=False)
    a=monthly[monthly.model.eq('M_VF')];b=monthly[monthly.model.eq('M_R')]
    write_json(destination/'primary_brier_intervals.json',{str(block):ci(paired(a,b,'brier'),block) for block in [6,12]})
    write_json(destination/'limitations.json',dict(independent_confirmation='requires source/vintage audit, calibration, risk ranking, ablation and state robustness before scientific support; no automatic success label'))
    with marker.open('x') as f:
        f.write(json.dumps(dict(destination=str(destination),gate=gate,primary_intervals_sha256=digest(destination/'primary_brier_intervals.json')))+'\n')


def main():
    p=argparse.ArgumentParser(description=__doc__);subs=p.add_subparsers(dest='command',required=True)
    f=subs.add_parser('forecast')
    for name in ['panel','receipts','calendar','date','destination']:f.add_argument('--'+name,required=True)
    a=subs.add_parser('attach-labels')
    for name in ['archive','labels','receipts','asof','destination']:a.add_argument('--'+name,required=True)
    c=subs.add_parser('confirmation')
    for name in ['forecasts','labels','destination']:c.add_argument('--'+name,required=True)
    x=p.parse_args()
    if x.command=='forecast':forecast(x.panel,x.receipts,x.calendar,x.date,x.destination)
    elif x.command=='attach-labels':attach_labels(x.archive,x.labels,x.receipts,x.asof,x.destination)
    else:confirmation(x.forecasts,x.labels,x.destination)

if __name__=='__main__':main()
