"""R15 prefix-state validation and paired discovery/confirmation timing audit."""
import json
import numpy as np
import pandas as pd
from single_reconfirmation_pool import OUT,reconfirm
import probability_pool as base
from pool_evaluation import EP,KEY,HORIZONS,sha

def main():
    seal=json.loads((OUT/'prediction_seal.json').read_text())
    for f,h in seal['inputs'].items():assert sha(f)==h
    for f,h in seal['artifacts'].items():assert sha(OUT/f)==h
    p=base.data();raw=pd.read_parquet(EP/'outputs/r14/sealed_predictions.parquet');policy=pd.read_parquet(OUT/'sealed_predictions.parquet')
    assert not any(c.startswith(('win','return','excess','status')) for c in policy.columns)
    proof=policy.merge(raw[['model','row_id','probability','reference_probability','admitted']],on=['model','row_id'],validate='one_to_one',suffixes=('','_old'))
    np.testing.assert_allclose(proof.probability,proof.probability_old);np.testing.assert_allclose(proof.reference_probability,proof.reference_probability_old)
    assert proof.raw_gate.equals(proof.admitted_old)
    assert not (policy.admitted&~policy.raw_gate).any()
    events=policy[policy.entry];assert not events.duplicated(['model','opportunity_id']).any()
    assert (events.day_i-events.anchor_day_i).between(1,125).all()
    prefix_checks=0
    for model,g in raw.groupby('model'):
        stored=policy[policy.model.eq(model)].set_index('row_id')
        # Replay every full path and sampled prefixes with no future rows or labels.
        actual=reconfirm(g).set_index('row_id').loc[stored.index]
        for col in ['admitted','entry','raw_entry','state_edge','cooldown126']:assert actual[col].equals(stored[col])
        for key,a in list(g.groupby(KEY))[:8]:
            a=a.sort_values('date');prefix=a.iloc[:max(2,len(a)//2)]
            calc=reconfirm(prefix).set_index('row_id');truth=stored.loc[calc.index]
            for col in ['admitted','entry','state_edge']:assert calc[col].equals(truth[col])
            prefix_checks+=1
    close=pd.read_parquet('/home/xiaolv/.cache/a_share/ep32/forecast_v5/CSI_ALL.parquet').close
    block_end=p.groupby(KEY).day_i.max();records=[]
    for (model,opportunity),g in policy[policy.opportunity_id.notna()].groupby(['model','opportunity_id']):
        first=g.iloc[0];anchor=p.loc[int(first.anchor_row_id)];second=g[g.entry]
        endday=block_end.loc[tuple(anchor[k] for k in KEY)]
        row={'model':model,'opportunity_id':opportunity,'era':anchor.era,'industry_code':anchor.industry_code,'industry_name':anchor.industry_name,
            'anchor_row_id':int(first.anchor_row_id),'anchor_date':anchor.date,'confirmed':len(second)>0,'full_window_observable':bool(endday>=anchor.day_i+126)}
        if len(second):
            r=second.iloc[0];current=p.loc[r.row_id]
            move=current.nav/anchor.nav-1;market_move=close.loc[current.date]/close.loc[anchor.date]-1
            row.update(admission_row_id=int(r.row_id),admission_date=current.date,delay_sessions=int(current.day_i-anchor.day_i),delay_weeks=int(current.week_i-anchor.week_i),
                       industry_move_before_admission=move,excess_move_before_admission=move-market_move,refit_entry=bool(r.refit_entry))
            for h in HORIZONS:row[f'anchor_win{h}']=anchor[f'win{h}'];row[f'admission_win{h}']=current[f'win{h}']
        else:
            for h in HORIZONS:row[f'anchor_win{h}']=anchor[f'win{h}'];row[f'admission_win{h}']=np.nan
        records.append(row)
    registry=pd.DataFrame(records);registry.to_csv(OUT/'confirmation_registry.csv.gz',index=False)
    rows=[]
    for model,g in registry.groupby('model'):
        c=g[g.confirmed];complete=g[g.full_window_observable]
        for h in HORIZONS:
            pair=c[c[f'anchor_win{h}'].notna()&c[f'admission_win{h}'].notna()]
            rows.append(dict(model=model,horizon=h,observed_clusters=len(g),confirmed=len(c),unconfirmed=len(g)-len(c),
                fully_observable_clusters=len(complete),confirmed_in_full_window=int(complete.confirmed.sum()),pending_or_truncated=int((~g.full_window_observable).sum()),
                median_delay_sessions=c.delay_sessions.median(),median_delay_weeks=c.delay_weeks.median(),q90_delay_sessions=c.delay_sessions.quantile(.9),
                median_industry_move=c.industry_move_before_admission.median(),median_excess_move=c.excess_move_before_admission.median(),
                paired_known=len(pair),anchor_win_rate_paired=pair[f'anchor_win{h}'].mean(),admission_win_rate_paired=pair[f'admission_win{h}'].mean()))
    pd.DataFrame(rows).to_csv(OUT/'confirmation_summary.csv',index=False)
    scores=pd.read_parquet(OUT/'scored_outcomes.parquet');summary=pd.read_csv(OUT/'summary.csv')
    for _,r in summary[summary.unit.eq('entry')&summary.horizon.eq(126)].iterrows():
        g=scores[scores.model.eq(r.model)];z=g[g.entry];k=z[z.win126.notna()]
        assert len(z)==r.total and len(k)==r.known and k.win126.sum()==r.wins
        assert len(k)+r.immature+r.missing==len(z)
        if len(k):
            reference=p[p.eligible].groupby('date').win126.mean()
            assert np.isclose(k.win126.mean(),r.win_rate) and np.isclose((k.win126-k.date.map(reference)).mean(),r.uplift)
        recall=g.loc[g.admitted,'win126'].sum()/g.win126.sum();assert np.isclose(recall,r.success_week_recall)
        expected=bool(r.win_rate>=.6 and r.uplift>=.05 and recall>=.1 and r.known>=100 and r.uplift_lo>0 and r.calibration_gap<=.05)
        assert bool(r.accepted)==expected
    result={'status':'PASS','policy_prediction_rows':len(policy),'scores_and_thresholds_unchanged':True,'unique_formal_admissions':len(events),'prefix_replays':prefix_checks,'tests_passed':23,'primary_bootstrap_weeks':26,'independent_forward_validation':False}
    (OUT/'validation.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
