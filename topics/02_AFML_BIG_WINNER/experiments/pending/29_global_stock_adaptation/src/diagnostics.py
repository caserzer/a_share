"""Past-only calibration context and descriptive adaptation/fallback accounting."""
from common import *
from hierarchical_model import mature_history


def calibration_context(current,previous):
    date=current.date.iloc[0];h=mature_history(previous,date);by={s:g for s,g in h.groupby('instrument')};rows=[]
    for stock in current.instrument:
        g=by.get(stock);r=dict(date=date,instrument=stock,calibration_history_months=0 if g is None else g.date.nunique(),
            calibration_history_first=g.date.min() if g is not None else pd.NaT,
            calibration_history_last=g.date.max() if g is not None else pd.NaT,
            issuer_max_mature_label=g.label_end.max() if g is not None else pd.NaT,
            calibration_context_status='historical_only_not_validated_odds')
        for name in C['formal_models']:
            if g is not None and len(g):
                y=labels(g.actual);p=g[name].to_numpy();bins=np.minimum((p*10).astype(int),9);ece=0.
                for b in np.unique(bins):
                    mask=bins==b;ece+=mask.mean()*abs(p[mask].mean()-y[mask].mean())
                r['past_'+name+'_bias']=float(np.mean(p-y));r['past_'+name+'_brier']=float(np.mean((p-y)**2));r['past_'+name+'_ece']=float(ece)
            else:
                for metric in ['bias','brier','ece']:r['past_'+name+'_'+metric]=np.nan
        rows.append(r)
    return pd.DataFrame(rows)


def main():
    cohort=json.loads((EP/'configs/target_cohort.yaml').read_text());single=cohort['single_stock'];fallback=[];coverage=[]
    for foundation in ['M_R','L2']:
        full=pd.read_parquet(CACHE/f'real_{foundation}_all.parquet');contexts=[]
        for date,current in full[full.date>=C['prediction_start']].groupby('date'):
            contexts.append(calibration_context(current,full))
        context=pd.concat(contexts,ignore_index=True);context.to_parquet(CACHE/f'calibration_context_{foundation}.parquet',index=False)
        g=full[full.date>=C['prediction_start']].merge(context,on=['date','instrument'],validate='one_to_one')
        g.to_parquet(CACHE/f'annotated_predictions_{foundation}.parquet',index=False)
        g[g.instrument==single].to_csv(EP/f'outputs/predictions/single_stock_{foundation}.csv',index=False)
        for column in ['peer_reason','GI_reason','individual_reason','adaptability_group']:
            for reason,z in g.groupby(column):
                known=z.actual.notna();y=labels(z.loc[known,'actual'])
                fallback.append(dict(foundation=foundation,dimension=column,reason=reason,predictions=len(z),known=int(known.sum()),
                    events=int(np.nansum(y)),mean_abs_probability_change=float(abs(z.delta_G).mean()),
                    mean_history_months=float(z.individual_months.mean()),mean_effective_months=float(z.individual_effective_months.mean()),
                    G_brier=float(np.mean((z.loc[known,'G']-y)**2)) if known.any() else np.nan,
                    GPI_brier=float(np.mean((z.loc[known,'GPI']-y)**2)) if known.any() else np.nan))
        for stock,z in g.groupby('instrument'):
            coverage.append(dict(foundation=foundation,instrument=stock,prediction_months=len(z),known_labels=int(z.actual.notna().sum()),
                individual_adapted_months=int(z.individual_reason.eq('adapted').sum()),
                peer_adapted_months=int(z.peer_reason.str.startswith('adapted').sum()),
                posterior_interval_available=int(z.individual_sd.notna().sum()),
                average_conditional_interval_width=float((z.GPI_upper-z.GPI_lower).mean())))
    pd.DataFrame(fallback).to_csv(OUT/'fallback_accounting.csv',index=False)
    pd.DataFrame(coverage).to_csv(OUT/'issuer_adaptation_coverage.csv',index=False)
    synthetic=[]
    for world in ['positive','zero']:
        full=pd.read_parquet(CACHE/f'synthetic_{world}_all.parquet')
        dates=sorted(full.date.unique());g=full[full.date>=dates[C['controls']['warmup_months']]]
        active=g.individual_reason.eq('adapted')
        low=np.maximum(-1,g.individual_offset_GP-1.96*g.individual_sd);high=np.minimum(1,g.individual_offset_GP+1.96*g.individual_sd)
        synthetic.append(dict(world=world,rows=len(g),adapted=int(active.sum()),
            approximate_latent_individual_coverage=float(((g.true_individual>=low)&(g.true_individual<=high))[active].mean()) if active.any() else np.nan,
            conditional_interval_note='model approximation; random-effects hyperparameter/global/peer uncertainty omitted',
            zero_events=int(g.individual_events.eq(0).sum()),zero_event_individual_nonzero=int((g.individual_events.eq(0)&g.individual_offset_GP.ne(0)).sum())))
    pd.DataFrame(synthetic).to_csv(OUT/'synthetic_uncertainty.csv',index=False)
    print('Past-only per-prediction calibration contexts and fallback diagnostics complete',flush=True)


if __name__=='__main__':main()
