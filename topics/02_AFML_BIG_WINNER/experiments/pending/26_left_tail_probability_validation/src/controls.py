"""Known binary hazard positive control and real within-month label permutation."""
from core import *


def positive_control():
    rng=np.random.default_rng(2600);stocks=60;months=140
    dates=np.repeat(pd.date_range('2000-01-31',periods=months,freq='ME'),stocks)
    group=rng.integers(3,size=len(dates));truth=np.array([.05,.4,.75])[group]
    events=rng.random(len(truth))<truth
    f=pd.DataFrame(dict(date=dates,vol63=group,log_cap=rng.normal(size=len(dates)),y_6=np.where(events,-.25,.05),oracle=truth,group=group))
    train=f.iloc[:80*stocks].copy();test=f.iloc[80*stocks:].copy();model=fit_classifier(train,'M_R',-.2);p=predict(model,test,'M_R')
    test['p']=p;test['event']=(test.y_6<-.2).astype(float)
    base=float((train.y_6<-.2).mean())
    test['delta']=(p-test.event)**2-(base-test.event)**2
    monthly=test.groupby('date').delta.mean();a=ci(monthly,6)
    groups=test.groupby('group').agg(rows=('p','size'),predicted=('p','mean'),oracle=('oracle','mean'),observed=('event','mean')).reset_index()
    monthly_auc=test.groupby('date').apply(lambda g:roc_auc_score(g.event,g.p),include_groups=False)
    passed=bool((groups.predicted-groups.oracle).abs().mean()<.08 and a['high95']<-.02 and monthly_auc.mean()>.70)
    groups.to_csv(OUT/'positive_control_probability_recovery.csv',index=False)
    test.groupby('date').agg(brier=('delta',lambda x:0.)).drop(columns='brier').assign(delta=monthly).to_csv(OUT/'positive_control_monthly.csv')
    return dict(control='known_binary_probability',passed=passed,probability_recovery_mae=float((groups.predicted-groups.oracle).abs().mean()),monthly_auc=float(monthly_auc.mean()),**a)


def negative_control():
    panel=load_panel();allrows=[];training_audits=[]
    for quarter in pd.period_range('2021Q1','2026Q2',freq='Q'):
        train,test=train_test(panel,quarter);tr=shuffle_within_month(train);te=shuffle_within_month(test)
        for original,shuffled in [(train,tr),(test,te)]:
            for t in THRESHOLDS.values():
                before=original.assign(event=event_labels(original.y_6,t)).groupby('date').event.sum()
                after=shuffled.assign(event=event_labels(shuffled.y_6,t)).groupby('date').event.sum()
                pd.testing.assert_series_equal(before,after)
            np.testing.assert_array_equal(original.y_6.isna(),shuffled.y_6.isna())
        model=fit_classifier(tr,'M_VF',-.2);p=predict(model,te,'M_VF')
        model.save_model(str(CACHE/f'negative_{quarter}.cbm'))
        for date,g in te.assign(prediction=p).groupby('date'):
            result=point_metrics(g.prediction,g.y_6,-.2)
            if result is not None:allrows.append(dict(date=date,**result))
        training_audits.append(dict(quarter=str(quarter),train_rows=len(tr),last_train_label=str(tr.end_6.max().date()),
            original_events=int((train.y_6<-.2).sum()),permuted_events=int((tr.y_6<-.2).sum()),original_month_counts_preserved=True))
    monthly=pd.DataFrame(allrows);a=ci(monthly.sort_values('date').auc-.5,6)
    passed=bool(a['low95']<=0<=a['high95'] and abs(a['estimate'])<.05)
    monthly.to_csv(OUT/'negative_control_monthly.csv',index=False);write_json(OUT/'negative_control_fits.json',training_audits)
    return dict(control='real_labels_permuted_within_month',passed=passed,monthly_auc=float(monthly.auc.mean()),
        mean_brier=float(monthly.brier.mean()),all_month_event_rates_preserved=True,null='no individual discrimination; market rate variation preserved',**a)


def main():
    old=json.loads((PREV/'outputs/controls.json').read_text());assert old['all_passed']
    positive=positive_control();negative=negative_control()
    value=dict(ep25_original_controls_retained_and_passed=True,ep25_controls_sha256=digest(PREV/'outputs/controls.json'),controls=[positive,negative],all_passed=positive['passed'] and negative['passed'])
    write_json(OUT/'controls.json',value);print(value,flush=True)
    assert value['all_passed'],'control failed; audit before interpretation, do not retry with favorable seeds'

if __name__=='__main__':main()
