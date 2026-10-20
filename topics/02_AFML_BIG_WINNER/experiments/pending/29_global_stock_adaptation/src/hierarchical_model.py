"""One forward origin, learned only from mature historical OOS global/peer errors."""
from common import *
from issuer_adaptation import common_offsets,estimate_tau,issuer_fit
from peer_prior import peer_sets,peer_fit
from local_baseline import local_probability


def mature_history(previous,date):
    g=previous[(previous.date<date)&(previous.label_end<date)&previous.actual.notna()&
               (previous.date>=date-pd.DateOffset(months=C['lookback_months']))].copy()
    if len(g):assert g.label_end.max()<date
    g['event']=labels(g.actual)
    return g


def one_origin(current,previous):
    date=current.date.iloc[0];assert current.date.nunique()==1
    history=mature_history(previous,date)
    history['offset_G']=common_offsets(history,'G');history['offset_GP']=common_offsets(history,'GP')
    bystock={s:g.sort_values('date') for s,g in history.groupby('instrument')}
    tg=estimate_tau(bystock,'offset_G');tp=estimate_tau(bystock,'offset_GP')
    memberships=peer_sets(current);rows=[];peerrows=[]
    for row in current.to_dict('records'):
        stock=row['instrument'];g=bystock.get(stock);member=memberships[stock]
        peer=peer_fit(row,member,history);ind=issuer_fit(g,'offset_G',tg['tau'])
        joint=issuer_fit(g,'offset_GP',tp['tau']);strong=issuer_fit(g,'offset_GP',C['individual']['fixed_strong_sd'])
        base=float(row['G']);a=peer['a'];b=joint['b'];z=float(logodds(base))
        loc=local_probability(g,base);weak=local_probability(g,base,True)
        out={**row,'GP':float(expit(z+a)),'GI':float(expit(z+ind['b'])),'GPI':float(expit(z+a+b)),
            'L':loc['probability'],'GPI_strong':float(expit(z+a+strong['b'])),'L_unshrunk':weak['probability'],
            'peer_offset':a,'individual_offset_G':ind['b'],'individual_offset_GP':b,'strong_individual_offset':strong['b'],
            'peer_sd':peer['posterior_sd'],'individual_sd':joint['posterior_sd'],'peer_shrinkage':peer['shrinkage'],'individual_shrinkage':joint['shrinkage'],
            'tau_G':tg['tau'],'tau_GP':tp['tau'],'peer_route':member['route'],'peer_reason':peer['reason'],'individual_reason':joint['reason'],
            'GI_reason':ind['reason'],'peer_count':len(member['peers']),'peer_history_rows':peer['history_rows'],'peer_history_months':peer['history_months'],
            'individual_months':joint['months'],'individual_effective_months':joint['effective_months'],'individual_events':joint['events'],
            'nonoverlap_labels':joint['nonoverlap_labels'],'nonoverlap_events':joint['nonoverlap_events'],'nonoverlap_nonevents':joint['nonoverlap_nonevents'],
            'event_stages':joint['event_stages'],'temporal_first':joint['temporal_first'],'temporal_last':joint['temporal_last'],
            'L_lower':loc['lower'],'L_upper':loc['upper'],'fit_cutoff':date,'history_max_label':history.label_end.max() if len(history) else pd.NaT,
            'uncertainty_scope':'conditional issuer interval; fixed global/peer; hyperparameter uncertainty omitted; not validated real-world odds'}
        sd=joint['posterior_sd']
        out['GPI_lower']=float(expit(z+a+max(-1.,b-1.96*sd))) if np.isfinite(sd) else 0.
        out['GPI_upper']=float(expit(z+a+min(1.,b+1.96*sd))) if np.isfinite(sd) else 1.
        out['delta_G']=out['GPI']-base;out['delta_GP']=out['GPI']-out['GP']
        out['listing_age_years']=(date-pd.Timestamp(row['listing_date'])).days/365.25
        out['known_industry_stability']=float(g.industry_id.eq(row['industry_id']).mean()) if g is not None and len(g) else np.nan
        out['history_group']='short' if joint['months']<24 else 'medium' if joint['months']<48 else 'long'
        out['event_group']='none' if joint['nonoverlap_events']==0 else 'one' if joint['nonoverlap_events']==1 else 'two_plus'
        out['adaptability_group']='individual_adapted' if joint['reason']=='adapted' else 'peer_only' if peer['reason'].startswith('adapted') else 'global_fallback'
        rows.append(out)
        for rank,(peerstock,distance) in enumerate(zip(member['peers'],member['distances']),1):
            peerrows.append(dict(date=date,instrument=stock,peer=peerstock,rank=rank,distance=distance,route=member['route'],
                formed_at=date,history_max_label=out['history_max_label']))
    audit=dict(date=str(date.date()),history_rows=len(history),history_origins=history.date.nunique(),max_history_label=str(history.label_end.max()) if len(history) else None,
        tau_G=tg,tau_GP=tp,current_rows=len(current),current_or_future_outcomes_used=False)
    return pd.DataFrame(rows),pd.DataFrame(peerrows),audit
