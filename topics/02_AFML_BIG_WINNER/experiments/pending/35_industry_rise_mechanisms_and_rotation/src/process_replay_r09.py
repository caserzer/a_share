"""Daily vs monthly alert burden using frozen monthly-trained onset models."""
import pandas as pd
from scipy.special import expit
from sklearn.metrics import brier_score_loss,roc_auc_score,average_precision_score
from common import *
from build_panel import price_features,delayed_labels
from train_r02 import F


def cooldown_alerts(frame, cooldown=20):
    emitted=[];last={}
    for row in frame.sort_values(['date','industry_code']).itertuples():
        key=(row.era,row.level,row.industry_code)
        if row.day_i-last.get(key,-10**9)>cooldown:
            emitted.append(row.Index);last[key]=row.day_i
    return frame.loc[emitted].copy()


def run():
    out=ROOT/'outputs/r09';source=CACHE/'forecast_v5/daily_industries.parquet';d=pd.read_parquet(source)
    bench=pd.read_parquet(CACHE/'forecast_v5/CSI_ALL.parquet').close
    parts=[]
    for _,g in d.groupby(KEY+['block'],sort=False):
        f=delayed_labels(price_features(g),bench,horizons=(20,));f['log_members']=np.log(f.members)
        f['price_ready']=f[F].notna().all(axis=1)&f.coverage.ge(.8)&f.members.ge(5)
        parts.append(f)
    daily=pd.concat(parts,ignore_index=True)
    # Existing daily input rows retain gap blocks, so no feature or event can cross missing history.
    models=json.loads((ROOT/'outputs/r02/model_parameters.json').read_text())
    models=[m for m in models if m['cohort']=='F' and m['method']=='F' and m['task']=='onset' and m['horizon']==20]
    ready=daily[daily.price_ready].copy();ready['year']=ready.date.dt.year
    rank=ready.groupby(['era','level','date'])[F].transform(centered_rank)
    scored=[]
    for model in models:
        g=ready[ready.era.eq(model['era'])&ready.level.eq(model['level'])&ready.year.eq(model['year'])].copy()
        x=rank.loc[g.index,model['columns']].to_numpy();x=(x-np.array(model['scaler_mean']))/np.array(model['scaler_scale'])
        linear=x@np.array(model['coefficient']).reshape(-1)+np.array(model['intercept']).reshape(-1)[0]
        g['score']=expit(linear*np.array(model['calibration_coefficient']).reshape(-1)[0]+np.array(model['calibration_intercept']).reshape(-1)[0])
        g['eligible']=g.past_excess20.le(0)
        g['y']=((g.return20>=.05)&(g.excess20>=.03)).astype(float).where(g.excess20.notna())
        scored.append(g)
    scored=pd.concat(scored).sort_values(KEY+['date']);assert not scored.duplicated(KEY+['date']).any()
    old=pd.read_parquet(ROOT/'outputs/r02/predictions.parquet');old=old[(old.cohort=='F')&(old.method=='F')&(old.task=='onset')&(old.horizon==20)]
    cmp=old.merge(scored[scored.eligible][KEY+['date','score']],on=KEY+['date'],how='outer',indicator=True)
    observed=cmp[cmp.prediction.notna()];assert observed._merge.eq('both').all()
    error=float((observed.prediction-observed.score).abs().max());assert error<1e-10
    scored.to_parquet(ROOT/'data/r09_daily_scores.parquet',index=False)
    eligible=scored[scored.eligible].copy()
    selected=[]
    for _,g in eligible.groupby(['era','level','date']):
        selected.append(g.sort_values(['score','industry_code'],ascending=[False,True]).head(int(np.ceil(.2*len(g)))))
    raw=pd.concat(selected)
    calendar=pd.DatetimeIndex(bench.index);monthends=pd.Series(calendar,index=calendar).groupby(calendar.to_period('M')).max()
    monthends=monthends[[p.end_time.normalize()<=calendar.max() for p in monthends.index]]
    alerts={ 'daily':raw,'monthly':raw[raw.date.isin(monthends.values)],'daily_cooldown20':cooldown_alerts(raw)}
    # Form confirmation starts on full causal price history before filtering for model availability.
    starts=[]
    for key,g in daily[daily.price_ready].groupby(KEY+['block']):
        qualified=g[g.mom20.ge(.05)&g.past_excess20.ge(.03)].sort_values('date')
        events=qualified[qualified.day_i.diff().gt(20)|qualified.day_i.diff().isna()]
        for r in events.itertuples():starts.append(dict(zip(KEY+['block'],key),date=r.date,day_i=r.day_i))
    starts=pd.DataFrame(starts);sc_lookup={k:g for k,g in scored.groupby(KEY+['block'])};events=[];hits=[]
    alert_lookup={name:{k:g for k,g in frame.groupby(KEY+['block'])} for name,frame in alerts.items()}
    for event in starts.itertuples():
        key=(event.era,event.level,event.industry_code,event.block);g=sc_lookup.get(key)
        if g is None or event.date not in set(g.date):continue
        preceding=g[g.day_i.between(event.day_i-20,event.day_i-1)]
        valid_window=len(preceding)==20 and preceding.day_i.nunique()==20
        base=dict(era=event.era,level=event.level,industry_code=event.industry_code,block=event.block,date=event.date,day_i=event.day_i,
            evaluable=valid_window,prior_scored_days=len(preceding),weak_eligible_days=int(preceding.eligible.sum()))
        events.append(base)
        for name,lookup in alert_lookup.items():
            a=lookup.get(key)
            window=a[a.day_i.between(event.day_i-20,event.day_i-1)] if a is not None else pd.DataFrame()
            hit=valid_window and len(window)>0
            record=dict(base,strategy=name,hit=hit,matched_alerts=len(window))
            if hit:
                first=window.sort_values('day_i').iloc[0]
                record.update(first_alert=first.date,lead_sessions=event.day_i-first.day_i,past_gain_at_alert=first.mom20,
                    new20_return_after_next_close=first.return20,new20_excess_after_next_close=first.excess20)
            hits.append(record)
    pd.DataFrame(events).to_csv(out/'confirmation_events.csv',index=False);hitdf=pd.DataFrame(hits);hitdf.to_csv(out/'event_hits.csv',index=False)
    alert_parts=[];summaries=[]
    for name,frame in alerts.items():
        f=frame.copy();f['strategy']=name;alert_parts.append(f[KEY+['block','date','day_i','score','entry_date','maturity20','y','mom20','return20','excess20','strategy']])
        for (era,level),g in f.groupby(['era','level']):
            h=hitdf[(hitdf.strategy==name)&(hitdf.era==era)&(hitdf.level==level)];v=h[h.evaluable]
            mature=g[g.y.notna()];n_hit=int(v.hit.sum());n_events=len(v)
            months=eligible[(eligible.era==era)&(eligible.level==level)].date.dt.to_period('M').nunique()
            unique=g.assign(month=g.date.dt.to_period('M')).drop_duplicates(['industry_code','month'])
            summaries.append(dict(era=era,level=level,strategy=name,events=n_events,left_censored_events=int((~h.evaluable).sum()),
                zero_eligible_events=int(v.weak_eligible_days.eq(0).sum()),hit_events=n_hit,process_recall=n_hit/n_events if n_events else np.nan,
                median_lead_sessions=v.loc[v.hit,'lead_sessions'].median(),alerts=len(g),alerts_per_month=len(g)/months,
                unique_industry_months=len(unique),repeat_alerts_beyond_first_in_month=len(g)-len(unique),
                mature_alerts=len(mature),unknown_alert_outcomes=int(g.y.isna().sum()),fixed_horizon_precision=mature.y.mean(),
                events_per100_alerts=100*n_hit/len(g)))
    pd.concat(alert_parts,ignore_index=True).to_parquet(out/'alerts.parquet',index=False);pd.DataFrame(summaries).to_csv(out/'summary.csv',index=False)
    cal=[]
    for (era,level),g in eligible[eligible.y.notna()].groupby(['era','level']):
        cal.append(dict(era=era,level=level,rows=len(g),prevalence=g.y.mean(),brier=brier_score_loss(g.y,g.score),
            roc_auc=roc_auc_score(g.y,g.score),pr_auc=average_precision_score(g.y,g.score),probability_calibration_not_recertified=True))
    pd.DataFrame(cal).to_csv(out/'daily_score_diagnostic.csv',index=False)
    js(out/'receipt.json',dict(protocol_sha256=sha(ROOT/'protocols/r09.json'),code_sha256=sha(__file__),
        source_hashes={str(p):sha(p) for p in [source,ROOT/'outputs/r02/model_parameters.json',ROOT/'outputs/r02/predictions.parquet',ROOT/'src/build_panel.py',ROOT/'src/train_r02.py']},
        frozen_models=len(models),daily_scored_rows=len(scored),monthly_prediction_comparisons=len(observed),monthly_max_error=error,
        no_refit=True,score_quality='monthly-trained score applied daily; historical replay, not forward probability claim'))
    print(pd.DataFrame(summaries).to_string(index=False),flush=True)

if __name__=='__main__':run()
