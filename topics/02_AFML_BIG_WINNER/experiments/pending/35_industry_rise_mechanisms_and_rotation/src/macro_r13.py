"""Frozen macro exposure/state interaction with explicit causal windows."""
import pandas as pd
from sklearn.linear_model import Ridge
from common import *
from evaluate_r01 import bootstrap


def macro_states(raw,dates,lag):
    wide=raw.pivot(index='economic_month',columns='metric',values='value')
    wide.index=pd.PeriodIndex(wide.index,freq='M');wide=wide.reindex(pd.period_range(wide.index.min(),wide.index.max(),freq='M'))
    state=pd.DataFrame({'pmi':(wide.manufacturing_pmi-50)/100,'money':wide.m2_yoy.diff(3)/100})
    state['economic_month']=state.index.astype(str)
    state['available']=state.index.to_timestamp(how='end').normalize()+pd.Timedelta(days=lag)
    query=pd.DataFrame({'date':pd.to_datetime(sorted(dates))})
    return pd.merge_asof(query,state.reset_index(drop=True).sort_values('available'),left_on='date',right_on='available',allow_exact_matches=False)


def estimate_history(history,current):
    h=history.dropna(subset=['lag_pmi','lag_money','past_excess20'])
    if len(h)<24:return None
    x=h[['lag_pmi','lag_money']].to_numpy();mu=x.mean(axis=0);sd=x.std(axis=0)
    if (sd<=1e-10).any() or not np.isfinite(current).all():return None
    model=Ridge(alpha=1).fit((x-mu)/sd,h.past_excess20)
    return dict(exposure=float(model.coef_.mean()),conditioned=float(model.coef_@((np.asarray(current)-mu)/sd)),
        n_fit=len(h),fit_last_date=h.date.max(),mu=mu.tolist(),sd=sd.tolist(),coef=model.coef_.tolist())


def run():
    out=ROOT/'outputs/r13';raw=pd.read_parquet(ROOT/'data/r11_macro_observations.parquet')
    panel=pd.concat([pd.read_parquet(ROOT/'data/monthly_panel.parquet'),pd.read_parquet(ROOT/'data/l1_monthly_panel.parquet')],ignore_index=True)
    panel['row_id']=panel.index;dates=sorted(panel.date.unique());features=[];states=[]
    for lag in [45,75]:
        state=macro_states(raw,dates,lag);state['lag_pmi']=state.pmi.shift(1);state['lag_money']=state.money.shift(1)
        state['lag']=lag;states.append(state)
        merged=panel.merge(state,on='date',validate='many_to_one')
        for key,g in merged.groupby(KEY):
            g=g.sort_values('date')
            for row in g.itertuples():
                history=g[(g.date<row.date)&(g.date>=row.date-pd.DateOffset(months=36))]
                result=estimate_history(history,[row.pmi,row.money])
                if result:
                    features.append(dict(zip(KEY,key),row_id=row.row_id,date=row.date,lag=lag,**result))
    feature=pd.DataFrame(features);feature.to_parquet(ROOT/'data/r13_sensitivities.parquet',index=False)
    pd.concat(states,ignore_index=True).to_parquet(ROOT/'data/r13_macro_states.parquet',index=False)
    both=feature.groupby('row_id').lag.nunique();common=set(both[both==2].index)
    coverage=[];metrics=[];selection=[]
    for key,full in panel.groupby(['era','level','date']):
        ready=full[full.price_ready];g=ready[ready.row_id.isin(common)]
        coverage.append(dict(zip(['era','level','date'],key),all_rows=len(full),price_ready=len(ready),paired=len(g),
            lag45=len(ready[ready.row_id.isin(set(feature.loc[feature.lag==45,'row_id']))]),lag75=len(ready[ready.row_id.isin(set(feature.loc[feature.lag==75,'row_id']))])))
        if len(g)<20:continue
        rank=g[['mom20','mom60','vol20','dd60']].apply(centered_rank);f=((rank.mom20+rank.mom60)/2-rank.vol20+rank.dd60)/3
        for lag in [45,75]:
            z=g.join(feature[feature.lag==lag].set_index('row_id')[['exposure','conditioned']],on='row_id',validate='one_to_one')
            scores={'F':f,'F_exposure':(f+centered_rank(z.exposure))/2,'F_macro':(f+centered_rank(z.conditioned))/2}
            for method,score in scores.items():
                ordered=z.assign(score=score).sort_values(['score','industry_code'],ascending=[False,True]);top=ordered.head(int(np.ceil(.2*len(z))))
                for code in top.industry_code:selection.append(dict(zip(['era','level','date'],key),lag=lag,method=method,industry_code=code))
                for h in [20,60]:
                    valid=z[f'excess{h}'].notna();complete=top[f'excess{h}'].notna().all()
                    ic=score[valid].corr(z.loc[valid,f'excess{h}'],method='spearman') if valid.sum()>=20 and score[valid].nunique()>1 and z.loc[valid,f'excess{h}'].nunique()>1 else np.nan
                    top_x=top[f'excess{h}'].mean() if complete else np.nan
                    metrics.append(dict(zip(['era','level','date'],key),lag=lag,method=method,horizon=h,origins=len(z),known=int(valid.sum()),unknown=len(z)-int(valid.sum()),ic=ic,top_n=len(top),top_complete=complete,top_excess=top_x,top_cost20=top_x-.004,top_cost50=top_x-.01))
    pd.DataFrame(coverage).to_csv(out/'coverage.csv',index=False)
    pd.DataFrame(selection).to_parquet(out/'selections.parquet',index=False)
    m=pd.DataFrame(metrics);m.to_csv(out/'date_metrics.csv',index=False)
    keys=['era','level','lag','method','horizon'];agg=dict(months=('ic','count'),ic=('ic','mean'),top_months=('top_excess','count'),top_excess=('top_excess','mean'),top_cost20=('top_cost20','mean'),top_cost50=('top_cost50','mean'))
    m.groupby(keys).agg(**agg).to_csv(out/'summary.csv');m.assign(year=m.date.dt.year).groupby(keys+['year']).agg(**agg).to_csv(out/'annual.csv')
    increments=[]
    for key,g in m.groupby(['era','level','lag','horizon']):
        pivot=g.pivot(index='date',columns='method',values='ic').dropna()
        for baseline in ['F','F_exposure']:
            delta=pivot.F_macro-pivot[baseline];lo,hi=bootstrap(delta,.05/10);years=delta.groupby(delta.index.year).mean()
            increments.append(dict(zip(['era','level','lag','horizon'],key),baseline=baseline,months=len(delta),delta_ic=delta.mean(),adjusted_low=lo,adjusted_high=hi,years=len(years),positive_year_fraction=(years>0).mean(),preliminary_pass=bool(len(delta)>=24 and lo>0 and (years>0).mean()>=2/3)))
    inc=pd.DataFrame(increments);inc['accepted_historical_increment']=False
    for i,row in inc.iterrows():
        if row.lag!=45 or row.horizon!=20:continue
        other=inc[(inc.era==row.era)&(inc.level==row.level)&(inc.lag==75)&(inc.horizon==20)&(inc.baseline==row.baseline)]
        inc.loc[i,'accepted_historical_increment']=bool(row.preliminary_pass and len(other)==1 and other.delta_ic.iloc[0]>0)
    inc.to_csv(out/'increments.csv',index=False)
    js(out/'receipt.json',dict(protocol_sha256=sha(ROOT/'protocols/r13.json'),code_sha256=sha(__file__),
        sources={str(p):sha(p) for p in [ROOT/'data/monthly_panel.parquet',ROOT/'data/l1_monthly_panel.parquet',ROOT/'data/r11_macro_observations.parquet']},
        sensitivity_rows=len(feature),common_origins=len(common),date_metric_rows=len(m),quality='Historical-proxy; no verified macro release-vintage archive'))
    print(inc.query('lag==45 and horizon==20').to_string(index=False),flush=True)
if __name__=='__main__':run()
