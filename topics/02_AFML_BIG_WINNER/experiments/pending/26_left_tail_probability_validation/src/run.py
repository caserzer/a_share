"""Frozen direct event classifiers and exact inherited distribution comparators."""
import time
from core import *


def freeze():
    files=[EP/'config.json',EP/'research_plan.md',EP/'tail_event_definition.md']+sorted((EP/'src').glob('*.py'))+sorted((EP/'tests').glob('*.py'))
    value=dict(created_utc=pd.Timestamp.now(tz='UTC').isoformat(),files={str(p.relative_to(EP)):digest(p) for p in files},source_receipts_sha256=digest(OUT/'source_receipts.csv'),
        candidate_count=5,thresholds=C['thresholds'],evidence='retrospective preregistration before EP26 scoring; no independent holdout')
    path=OUT/'preregistration.json'
    if path.exists():
        locked=json.loads(path.read_text());assert all(digest(EP/k)==v for k,v in locked['files'].items());assert digest(OUT/'source_receipts.csv')==locked['source_receipts_sha256']
    else:write_json(path,value)
    return digest(path)


def main():
    CACHE.mkdir(parents=True,exist_ok=True);lock=freeze();panel=load_panel();receipts=[]
    for quarter in pd.period_range('2021Q1','2026Q2',freq='Q'):
        rp=OUT/f'checkpoints/{quarter}.json'
        if rp.exists():
            r=json.loads(rp.read_text());assert r['preregistration_sha256']==lock;assert digest(EP/r['prediction_path'])==r['prediction_sha256'];receipts.append(r);continue
        train,test=train_test(panel,quarter);start=time.monotonic();records=[];crossings={};trainhash=digest(OLD/'outputs/local_cache/four_horizon_panel.parquet')
        keys=['date','instrument','target_6','end_6','y_6','vol63','log_cap','board','regime','phase','financial_age_days','age_group','financial_available_date','financial_report_date','yield_observation_date','industry_sector','industry_stale','industry_published','market_mom126','market_vol63']
        frame=test[keys].copy().rename(columns={'y_6':'actual','end_6':'label_end','target_6':'target_date'})
        frame['vol_regime']=np.where(test.market_vol63>train[['date','market_vol63']].drop_duplicates().market_vol63.median(),'high_vol','low_vol')
        frame['model_version']='EP26-fixed-v1';frame['data_version']=trainhash
        frame['feature_available_fraction']=test[PREVC['risk_features']+C['valuation_features']+C['financial_features']].notna().mean(axis=1)
        frame['confidence']='exploratory_unconfirmed'
        frame['financial_stale']=frame.financial_age_days>365
        # True historical rate from exactly the same mature rows, no atomic approximation.
        base={k:float((train.y_6<t).mean()) for k,t in THRESHOLDS.items()}
        baseq=np.quantile(train.y_6,[.05,.1])
        priorpred=pd.read_parquet(PREV/f'outputs/local_cache/6_{quarter}_predictions.parquet')
        priorreference=priorpred[priorpred.model=='B1'].reset_index(drop=True)
        pd.testing.assert_frame_equal(frame[['date','instrument']].reset_index(drop=True),priorreference[['date','instrument']])
        np.testing.assert_allclose(frame.actual,priorreference.actual,equal_nan=True,atol=0,rtol=0)
        indirect={}
        with np.load(PREV/f'outputs/local_cache/6_{quarter}_atoms.npz') as atoms:
            for name,oldname in OLD_MODELS.items():
                a=atoms[oldname]
                indirect[name]={f'p_loss{k}':(a<t).mean(axis=1) for k,t in THRESHOLDS.items()}
                q=np.quantile(a,[.05,.1],axis=1)
                indirect[name].update(q05=q[0],q10=q[1])
                old=priorpred[priorpred.model.eq(oldname)].reset_index(drop=True)
                np.testing.assert_array_equal(indirect[name]['p_loss20'],old.p_tail.to_numpy())
        indirect['B0']={f'p_loss{k}':np.full(len(test),v) for k,v in base.items()}
        indirect['B0'].update(q05=np.full(len(test),baseq[0]),q10=np.full(len(test),baseq[1]))
        for name,values in indirect.items():
            r=frame.copy();r['model']=name;r['model_version']='EP25-frozen' if name!='B0' else 'EP26-historical-rate'
            for k,v in values.items():r[k]=v
            records.append(r)
        for name in C['candidates']:
            prob={}
            for k,t in THRESHOLDS.items():
                model=fit_classifier(train,name,t);prob[k]=predict(model,test,name)
                model.save_model(str(CACHE/f'{quarter}_{name}_{k}.cbm'))
            p10,p20,p30=coherence(prob[10],prob[20],prob[30])
            r=frame.copy();r['model']=name
            for k,a in [(10,p10),(20,p20),(30,p30)]:r[f'p_loss{k}']=a;r[f'raw_loss{k}']=prob[k]
            r['q05']=np.nan;r['q10']=np.nan
            r['feature_available_fraction']=test[feature_names(name)].notna().mean(axis=1)
            crossings[name]=dict(p10_below_p20=int((prob[10]<prob[20]).sum()),p30_above_p20=int((prob[30]>prob[20]).sum()))
            records.append(r)
        result=pd.concat(records,ignore_index=True)
        for k in THRESHOLDS:
            b1=indirect['B1'][f'p_loss{k}'];dr=indirect['D_R'][f'p_loss{k}']
            result[f'b0_loss{k}']=np.tile(np.full(len(test),base[k]),len(ALL_MODELS))
            result[f'b1_loss{k}']=np.tile(b1,len(ALL_MODELS));result[f'dr_loss{k}']=np.tile(dr,len(ALL_MODELS))
            result[f'delta_b1_loss{k}']=result[f'p_loss{k}']-result[f'b1_loss{k}']
        path=CACHE/f'{quarter}_predictions.parquet';result.to_parquet(path,index=False)
        r=dict(quarter=str(quarter),train_rows=len(train),training_months=train.date.nunique(),training_events=int((train.y_6<-.2).sum()),prediction_rows=len(test),
            last_training_label=str(train.end_6.max().date()),first_prediction=str(test.date.min().date()),
            train_key_sha256=hashlib.sha256(train[['date','instrument']].to_csv(index=False).encode()).hexdigest(),
            test_key_sha256=hashlib.sha256(test[['date','instrument']].to_csv(index=False).encode()).hexdigest(),
            prediction_path=str(path.relative_to(EP)),prediction_sha256=digest(path),preregistration_sha256=lock,auxiliary_crossings=crossings,
            elapsed_seconds=time.monotonic()-start,models_fit=15)
        rp.parent.mkdir(exist_ok=True);write_json(rp,r);receipts.append(r)
        print('EP26',quarter,'training',len(train),'predicted',len(test),'seconds',round(r['elapsed_seconds'],1),flush=True)
    write_json(OUT/'fit_audit.json',receipts)
    print('All 5 fixed candidates and 3 thresholds complete.',flush=True)

if __name__=='__main__':main()
