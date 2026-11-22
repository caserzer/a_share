"""Expanding, shared-date forecasts of the two sleeves and their return difference."""
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler
from settings import *


def history(f):
    f=f.copy()
    idx=pd.read_parquet(PRIVATE/'market.parquet').open
    f['index_h10']=f.exit_date.map(idx)/f.entry_date.map(idx)-1
    cols=['d10_ex','red_ex']
    f[cols[0]]=f.d10-f.index_h10
    f[cols[1]]=f.red-f.index_h10
    assert np.allclose(f.gap,f.d10_ex-f.red_ex,equal_nan=True)
    for date in f.index:
        past=f[f.exit_date.le(date)].tail(6)
        if len(past)==6:
            f.loc[date,['prev_d10','prev_red']]=past[cols].mean(skipna=False).values
            f.loc[date,'history_first_signal']=str(past.index[0].date())
            f.loc[date,'history_last_exit']=str(past.exit_date.max().date())
    return f


def predict(f):
    pred=[]
    folds=[]
    for quarter,g in f.groupby(f.index.to_period('Q')):
        cut=g.index.min()
        train=f[f.exit_date.le(cut)].dropna(subset=SPECS['both']+['d10_ex','red_ex'])
        test=g.dropna(subset=SPECS['both'])
        if len(train)<36 or test.empty:
            continue
        assert train.index.max()<cut
        y=train[['d10_ex','red_ex']]
        std=train.gap.std(ddof=1)
        for name,x in {'constant':[],**SPECS}.items():
            if x:
                scaler=StandardScaler().fit(train[x])
                X=scaler.transform(train[x])
                model=Ridge(alpha=1).fit(X,y)
                values=model.predict(scaler.transform(test[x]))
                direct=Ridge(alpha=1).fit(X,train.gap)
                np.testing.assert_allclose(values[:,0]-values[:,1],direct.predict(scaler.transform(test[x])),atol=1e-12)
                folds.append(dict(quarter=str(quarter),spec=name,cutoff=cut,n=len(train),latest_exit=train.exit_date.max(),
                    fields=x,center=scaler.mean_.tolist(),scale=scaler.scale_.tolist(),coef=model.coef_.tolist(),
                    intercept=model.intercept_.tolist(),train_gap_sd=std))
            else:
                values=np.tile(y.mean().values,(len(test),1))
            for (date,r),v in zip(test.iterrows(),values):
                estimate=v[0]-v[1]
                w=np.clip(.5+estimate/(2*std),0,1)
                pred.append(dict(signal_date=date,entry_date=r.entry_date,exit_date=r.exit_date,cutoff=cut,spec=name,
                    n=len(train),pred_d10=v[0],pred_red=v[1],estimate=estimate,weight=w,actual_d10=r.d10_ex,
                    actual_red=r.red_ex,gap=r.gap,gross_vs_half=(w-.5)*r.gap))
    return pd.DataFrame(pred),folds


def run():
    f=pd.read_csv(ALLOC/'results/signals.csv',parse_dates=['signal_date','entry_date','exit_date']).set_index('signal_date')
    f=history(f)
    f.to_csv(D/'features.csv')
    p,folds=predict(f)
    # Prefix replay discards any future labels including currently immature ones.
    for cut in p.cutoff.unique():
        prefix=f.loc[:cut].copy()
        prefix.loc[prefix.exit_date.gt(cut)|prefix.exit_date.isna(),['d10_ex','red_ex','gap']]=np.nan
        replay,_=predict(prefix)
        a=replay[replay.signal_date.eq(cut)].set_index('spec')
        b=p[p.signal_date.eq(cut)].set_index('spec')
        np.testing.assert_allclose(a.estimate,b.estimate,atol=1e-12)
    p.to_csv(D/'predictions.csv',index=False)
    dump(D/'folds.json',folds)
    rows=[]
    err_tests=[]
    start=p.signal_date.min()
    for scope,calendar in [('primary',f[(f.index>=start)&f.exit_date.le(MAIN)]),('later',f[f.entry_date.ge(MAIN)&f.exit_date.notna()])]:
        reference=p[p.spec.eq('market')].set_index('signal_date').reindex(calendar.index)
        ref_error=(reference.estimate-reference.gap).abs()
        for name,h in p.groupby('spec'):
            aligned=h.set_index('signal_date').reindex(calendar.index)
            z=aligned.dropna(subset=['estimate','gap'])
            diff=z.estimate-z.gap
            wrong=z.estimate.gt(0)!=z.gap.gt(0)
            low=z.weight.le(.35)
            advantage=z.gross_vs_half.sort_values(ascending=False)
            mae_gain=ref_error-(aligned.estimate-aligned.gap).abs()
            err_tests.append(dict(scope=scope,spec=name,**bootstrap(mae_gain.values)))
            rows.append(dict(scope=scope,spec=name,calendar=len(calendar),n=len(z),mae=diff.abs().mean(),rmse=np.sqrt((diff**2).mean()),
                d10_mae=(z.pred_d10-z.actual_d10).abs().mean(),red_mae=(z.pred_red-z.actual_red).abs().mean(),
                direction=(~wrong).mean(),wrong_n=wrong.sum(),wrong_abs=z.loc[wrong,'gap'].abs().mean(),
                strong_cut_n=low.sum(),strong_cut_red_lead=-z.loc[low,'gap'].mean(),strong_cut_red_wins=z.loc[low,'gap'].lt(0).sum(),
                strong_cut_saved=z.loc[low & z.gap.lt(0),'gross_vs_half'].sum(),strong_cut_missed=-z.loc[low & z.gap.gt(0),'gross_vs_half'].sum(),
                mae_gain=mae_gain.mean(),gross=z.gross_vs_half.mean(),ex_top2=advantage.iloc[2:].mean(),
                ex_top2_dates=','.join(advantage.head(2).index.strftime('%Y-%m-%d'))))
    summary=pd.DataFrame(rows)
    summary.to_csv(D/'forecast_summary.csv',index=False)
    pd.DataFrame(err_tests).to_csv(D/'mae_tests.csv',index=False)
    base=summary[(summary.scope=='primary')&summary.spec.isin(['plus_d10','plus_red','both'])].copy()
    base['passes']=(base.mae_gain>0)&(base.ex_top2>0)
    base['features']=base.spec.map(lambda x:len(SPECS[x]))
    winners=base[base.passes].sort_values(['features','mae','spec'])
    dump(D/'gate.json',clean(dict(selected=winners.spec.iloc[0] if len(winners) else None,
        rules=base[['spec','mae_gain','ex_top2','passes']].to_dict('records'))))
    print(summary[['scope','spec','n','mae','mae_gain','direction','gross','ex_top2']].to_string(index=False))


if __name__=='__main__':
    run()
