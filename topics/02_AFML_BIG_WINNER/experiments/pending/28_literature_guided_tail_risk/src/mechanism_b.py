"""Separate shape/expected-return target transfers, never treated as loss-event replication."""
from catboost import CatBoostRegressor
from core import *
from run import freeze


def main():
    freeze();panel=load_panel();allrows=[];audits=[]
    for quarter in pd.period_range('2021Q1','2026Q2',freq='Q'):
        output=CACHE/f'shape_{quarter}.parquet';receipt=EP/f'outputs/audits/shape_{quarter}.json'
        if receipt.exists():
            r=json.loads(receipt.read_text());assert digest(output)==r['sha256'];allrows.append(pd.read_parquet(output));audits.append(r);continue
        tr,te=split(panel,6,quarter);rows=[]
        for target,lag in [('future_ncskew6','past_ncskew6'),('future_duvol6','past_duvol6')]:
            train=tr[tr[target].notna()];base=C['risk_features']+[lag]
            for name,cols in [('shape_base',base),('shape_disagreement',list(dict.fromkeys(base+C['disagreement_features'])))]:
                params=dict(C['catboost']);params['loss_function']='RMSE';model=CatBoostRegressor(**params)
                model.fit(train[cols],train[target],sample_weight=weights(train));p=model.predict(te[cols])
                model.save_model(str(CACHE/f'shape_{quarter}_{target}_{name}.cbm'))
                z=te[['date','instrument',target,'end_6']].rename(columns={target:'actual', 'end_6':'label_end'})
                z['prediction']=p;z['model']=name;z['target']=target;rows.append(z)
        z=pd.concat(rows,ignore_index=True);z.to_parquet(output,index=False);allrows.append(z)
        r=dict(quarter=str(quarter),models_fit=4,max_training_label=str(tr.end_6.max()),sha256=digest(output));write_json(receipt,r);audits.append(r);print('shape',quarter,flush=True)
    full=pd.concat(allrows,ignore_index=True);full.to_parquet(CACHE/'shape_predictions.parquet',index=False)
    rows=[]
    for (target,name,date),g in full[full.actual.notna()].groupby(['target','model','date']):
        e=g.prediction-g.actual;rows.append(dict(target=target,model=name,date=date,rows=len(g),mse=float(np.mean(e*e)),mae=float(np.mean(abs(e)))))
    m=pd.DataFrame(rows);m.to_csv(OUT/'shape_monthly.csv',index=False);intervals=[]
    for target,g in m.groupby('target'):
        for metric in ['mse','mae']:
            d=paired(g[g.model.eq('shape_disagreement')],g[g.model.eq('shape_base')],metric)
            for block in C['bootstrap']['blocks']:intervals.append(dict(target=target,metric=metric,**ci(d,block)))
    pd.DataFrame(intervals).to_csv(OUT/'shape_intervals.csv',index=False)
    assert sum(r['models_fit'] for r in audits)==C['maximum_shape_regression_fits']
    write_json(EP/'outputs/audits/shape_fit_audit.json',audits)
    tail=pd.read_csv(OUT/'tail_history.csv',parse_dates=['date']);tail['target']=tail.market_month_return.shift(-1);tail['target_end']=tail.date.shift(-1)
    market=[]
    for row in tail.itertuples():
        tr=tail[(tail.target_end<=row.date)&tail.target.notna()&tail.tail_hill.notna()]
        if len(tr)<C['mechanism_B']['KJ_initial_months'] or pd.isna(row.target) or pd.isna(row.tail_hill):continue
        x=np.c_[np.ones(len(tr)),tr.tail_hill];beta=np.linalg.lstsq(x,tr.target,rcond=None)[0]
        market.append(dict(date=row.date,target_end=row.target_end,training_months=len(tr),max_train_label=tr.target_end.max(),
            actual=row.target,base=float(tr.target.mean()),prediction=float(beta[0]+beta[1]*row.tail_hill)))
    m=pd.DataFrame(market);m['base_se']=(m.base-m.actual)**2;m['model_se']=(m.prediction-m.actual)**2;m.to_csv(OUT/'market_mechanism.csv',index=False)
    write_json(OUT/'market_mechanism.json',dict(months=len(m),initial_months=36,original_initial_months=120,
        oos_r2=float(1-m.model_se.sum()/m.base_se.sum()),mse_differences=[ci(m.model_se-m.base_se,b) for b in C['bootstrap']['blocks']],
        label='next-month index price return; neither stock crash nor six-month loss probability'))
    print('B mechanism transfers complete',flush=True)


if __name__=='__main__':main()
