"""P1 then P2 with explicit phase gates; no performance-dependent model selection."""
import time
from core import *
from conditional import conditional_auc


def freeze():
    p0=json.loads((OUT/'p0_audit.json').read_text());assert p0['pass_for_limited_exploration']
    files=[EP/'research_plan.md',EP/'config.json']+sorted((EP/'src').glob('*.py'))+sorted((EP/'tests').glob('*.py'))
    value=dict(created_utc=pd.Timestamp.now(tz='UTC').isoformat(),files={str(p.relative_to(EP)):digest(p) for p in files},panel_sha256=digest(PANEL),p0_sha256=digest(OUT/'p0_audit.json'),source_receipts_sha256=digest(OUT/'source_receipts.csv'),evidence='historical exploration; no untouched holdout',base_candidates=6)
    path=OUT/'preregistration.json'
    if path.exists():
        old=json.loads(path.read_text());assert all(digest(EP/k)==v for k,v in old['files'].items());assert digest(PANEL)==old['panel_sha256']
    else:write_json(path,value)
    return digest(path)


def key_frame(train,test,h):
    keys=['date','instrument',f'y_{h}',f'end_{h}','log_cap','vol63','board','industry_id','industry_sector','industry_published','industry_age_days','industry_stale','regime','phase','age_group','financial_age_days','financial_available_date','yield_observation_date','log_money21']+C['market_features']
    frame=test[list(dict.fromkeys(keys))].rename(columns={f'y_{h}':'actual',f'end_{h}':'label_end'}).copy();frame['horizon']=h
    frame['data_version']=digest(PANEL);frame['confidence']='historical_exploratory_unconfirmed';frame['model_version']='EP27-fixed-v1'
    frame['vol_regime']=np.where(frame.market_vol63>train[['date','market_vol63']].drop_duplicates().market_vol63.median(),'high_vol','low_vol')
    return frame


def p1_summary(receipts):
    rows=[]
    for r in receipts:
        frame=pd.read_parquet(EP/r['prediction_path'])
        for (model,date),g in frame.groupby(['model','date']):
            result=metrics(g.probability,g.actual)
            if result is None:continue
            conditional,_=conditional_auc(g)
            rows.append(dict(horizon=r['horizon'],model=model,date=date,**result,industry_auc=conditional['conditional_auc'],industry_coverage=conditional['coverage']))
    monthly=pd.DataFrame(rows);monthly.to_csv(OUT/'p1_monthly_scores.csv',index=False)
    contrasts=[]
    for h,g in monthly.groupby('horizon'):
        for a,b in [('M_R','B0'),('M_RM','M_R'),('M_RMI','M_RM'),('B1','B0')]:
            for metric in ['brier','auc','industry_auc']:
                diff=paired(g[g.model.eq(a)],g[g.model.eq(b)],metric)
                if np.isfinite(diff).any():contrasts.append(dict(horizon=h,candidate=a,baseline=b,metric=metric,**ci(diff,6)))
    pd.DataFrame(contrasts).to_csv(OUT/'p1_comparisons.csv',index=False)
    assert monthly.brier.notna().all()
    write_json(OUT/'p1_gate.json',dict(phase='P1',passed=True,models=['B0','B1','M_R','M_RM','M_RMI'],scores_and_layer_comparisons_complete=True,
        training_and_source_dates_checked=True,decision='proceed to preregistered P2 regardless of effect sign; no new model selected'))


def main():
    lock=freeze();panel=load_panel();p1_records=[];all_audits=[]
    for phase,names in [('P1',['M_R','M_RM','M_RMI']),('P2',['M_RMIV','M_RMIF','M_RMIVF'])]:
        if phase=='P2':
            p1_summary(p1_records);assert json.loads((OUT/'p1_gate.json').read_text())['passed']
        for h in [6,1,3,12]:
            for quarter in pd.period_range('2021Q1','2026Q2',freq='Q'):
                receipt=OUT/f'checkpoints/{phase}_{h}_{quarter}.json'
                if receipt.exists():
                    r=json.loads(receipt.read_text());assert r['registration_sha256']==lock and digest(EP/r['prediction_path'])==r['prediction_sha256']
                    (p1_records if phase=='P1' else all_audits).append(r);continue
                train,test=split(panel,h,quarter);start=time.monotonic();frame=key_frame(train,test,h);rows=[]
                if phase=='P1':
                    old=pd.read_parquet(EP25/f'outputs/local_cache/{h}_{quarter}_predictions.parquet');original=old[old.model=='B1'].reset_index(drop=True)
                    pd.testing.assert_frame_equal(frame[['date','instrument']],original[['date','instrument']]);np.testing.assert_allclose(frame.actual,original.actual,rtol=0,atol=0,equal_nan=True)
                    with np.load(EP25/f'outputs/local_cache/{h}_{quarter}_atoms.npz') as saved:p_b1=(saved['B1']<C['threshold']).mean(axis=1)
                    preds={'B0':np.full(len(test),float((train[f'y_{h}']<C['threshold']).mean())),'B1':p_b1}
                else:
                    prior=pd.read_parquet(CACHE/f'P1_{h}_{quarter}_predictions.parquet');rows.append(prior);preds={}
                for name in names:
                    model=fit_model(train,name,h);p=predict(model,test,name);preds[name]=p;model.save_model(str(CACHE/f'{h}_{quarter}_{name}.cbm'))
                    if h==6 and name=='M_R':
                        frozen=pd.read_parquet(EP26/f'outputs/local_cache/{quarter}_predictions.parquet');frozen=frozen[frozen.model=='M_R'].reset_index(drop=True)
                        pd.testing.assert_frame_equal(frozen[['date','instrument']],test[['date','instrument']]);np.testing.assert_allclose(p,frozen.p_loss20,atol=1e-14,rtol=1e-14)
                b0=preds['B0'] if phase=='P1' else prior[prior.model=='B0'].probability.to_numpy();b1=preds['B1'] if phase=='P1' else prior[prior.model=='B1'].probability.to_numpy()
                for name,p in preds.items():
                    r=frame.copy();r['model']=name;r['probability']=p;r['b0_probability']=b0;r['b1_probability']=b1;r['delta_b1']=p-b1;rows.append(r)
                output=pd.concat(rows,ignore_index=True);path=CACHE/f'{phase}_{h}_{quarter}_predictions.parquet';output.to_parquet(path,index=False)
                audit=dict(phase=phase,horizon=h,quarter=str(quarter),train_rows=len(train),training_months=train.date.nunique(),train_events=int((train[f'y_{h}']<C['threshold']).sum()),predicted_rows=len(test),max_train_label=str(train[f'end_{h}'].max().date()),
                    train_keys_sha256=keys_hash(train),test_keys_sha256=keys_hash(test),prediction_path=str(path.relative_to(EP)),prediction_sha256=digest(path),registration_sha256=lock,models_fit=3,elapsed_seconds=time.monotonic()-start)
                receipt.parent.mkdir(exist_ok=True);write_json(receipt,audit);(p1_records if phase=='P1' else all_audits).append(audit)
                print('EP27',phase,h,quarter,'train',len(train),'predict',len(test),'seconds',round(audit['elapsed_seconds'],1),flush=True)
    write_json(OUT/'p1_fit_audit.json',p1_records);write_json(OUT/'fit_audit.json',all_audits)
    full=pd.concat([pd.read_parquet(EP/r['prediction_path']) for r in all_audits],ignore_index=True);full.to_parquet(CACHE/'all_predictions.parquet',index=False)
    print('All registered P1/P2 base candidates complete.',flush=True)

if __name__=='__main__':main()
