"""Full denominator candidate-window audit and all discordant successful processes."""
import json
import pandas as pd
from audit_local_inputs import EP,PRIOR,sha
from member_volume_math import score_candidates


def main():
    out=EP/'outputs/r04'
    if (out/'failure_boundary.json').exists():raise FileExistsError('audit exists')
    pfile=EP/'outputs/r00_metric_denominators/full_process_registry.parquet'
    p=pd.read_parquet(pfile);p=p[p.mature & ~p.left_origin_uncertain]
    w=pd.read_parquet(out/'full_catalog.parquet');groups={k:g for k,g in w.groupby(['era','industry_code'])}
    f={a:pd.read_parquet(out/f'{a}_evaluated.parquet') for a in ['A','B']}
    hits={a:set(g.loc[g.recall_credit,'process_id']) for a,g in f.items()}
    windowrows=[]
    for r in p.itertuples():
        g=groups.get((r.era,r.industry_code),w.iloc[:0]);g=g[g.day_i.between(r.start_day_i-5,r.start_day_i+10)]
        tickets=g[g.ticket_id.notna() & g.supported]
        row=dict(process_id=r.process_id,era=r.era,industry_code=r.industry_code,origin=r.start_date,kind=r.kind,
                 reviews=len(g),ticket_count=len(tickets),window_reasons=g.reason.value_counts().to_dict())
        for arm in ['A','B']:
            assigned=f[arm][f[arm].process_id.eq(r.process_id)]
            if r.process_id in hits[arm]:category='SUCCESS'
            elif assigned.outcome.str.startswith('UNKNOWN').any():category='UNRESOLVED'
            elif len(assigned):category='ASSIGNED_FAILURE'
            elif len(tickets):category='CANDIDATE_NOT_SUCCESSFULLY_ASSIGNED'
            else:category='NO_COMMON_CANDIDATE_IN_WINDOW'
            row[f'{arm}_category']=category
        windowrows.append(row)
    census=pd.DataFrame(windowrows);census.to_parquet(out/'full_process_candidate_audit.parquet',index=False)
    candidates=w[w.ticket_id.notna() & w.supported].copy()
    candidates=pd.concat([score_candidates(g) for _,g in candidates.groupby(['era','date'])])
    for arm,score in [('A','score_A'),('B','score_B')]:
        ranked=candidates.sort_values(['era','date',score,'industry_code'],ascending=[True,True,False,True])
        rank=ranked.groupby(['era','date']).cumcount()+1
        candidates[f'{arm}_rank']=rank.reindex(candidates.index)
    byticket=candidates.set_index('ticket_id');pred=pd.read_parquet(out/'predictions.parquet').set_index('observation_id')
    raw=pd.read_parquet(PRIOR/'daily_industries.parquet',columns=['era','industry_code','industry_name'])
    names=raw.drop_duplicates(['era','industry_code']).set_index(['era','industry_code']).industry_name
    discordant=[]
    for direction,win,lose in [('B_ADDED','B','A'),('B_LOST','A','B')]:
        for pid in sorted(hits[win]-hits[lose]):
            success=f[win][f[win].process_id.eq(pid)&f[win].recall_credit].iloc[0]
            ticket=pred.loc[success.alert_id].ticket_id;candidate=byticket.loc[ticket]
            other=f[lose][f[lose].process_id.eq(pid)]
            counterpart=pred[(pred.arm.eq(lose)) & pred.ticket_id.eq(ticket)]
            reason='OTHER_ARM_SELECTED_BUT_FAILED_OR_UNKNOWN' if len(other) else 'OTHER_ARM_NO_TIMELY_ASSIGNMENT'
            assert candidate[f'{win}_rank']<=5
            if not len(counterpart):assert candidate[f'{lose}_rank']>5
            else:reason='SAME_TICKET_DIFFERENT_FIRST_OWNERSHIP'
            truth=p[p.process_id.eq(pid)].iloc[0]
            discordant.append(dict(direction=direction,process_id=pid,era=truth.era,industry_code=truth.industry_code,
                                    industry_name=names.loc[(truth.era,truth.industry_code)],kind=truth.kind,origin=str(truth.start_date.date()),
                                    winner_alert=str(success.date.date()),winner_delta=float(success.delta_from_origin),
                                    r20=float(candidate.r20),volume_ratio=float(candidate.volume_ratio),coverage=float(candidate.coverage),score_A=float(candidate.score_A),score_B=float(candidate.score_B),
                                    A_rank=int(candidate.A_rank),B_rank=int(candidate.B_rank),reason=reason,
                                    other_outcomes=other.outcome.tolist(),other_alert_dates=[str(x.date()) for x in other.date]))
    assert len(discordant)==len(hits['A']^hits['B']) and len(census)==2411
    (out/'discordant_processes.json').write_text(json.dumps(discordant,ensure_ascii=False,indent=2)+'\n')
    result=dict(scope='Descriptive boundary accounting; no rule changes or causal attribution beyond fixed same-date rankings',
                full_processes=len(census),common_candidate_available=int(census.ticket_count.gt(0).sum()),
                counts={a:census[f'{a}_category'].value_counts().to_dict() for a in ['A','B']},
                discordant_counts=pd.DataFrame(discordant).groupby(['direction','reason']).size().rename('n').reset_index().to_dict('records'),
                inputs={str(x):sha(x) for x in [pfile,out/'full_catalog.parquet',out/'predictions.parquet',out/'A_evaluated.parquet',out/'B_evaluated.parquet',EP/'src/r04_failure_boundary.py']})
    (out/'failure_boundary.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='inputs'},ensure_ascii=False))


if __name__=='__main__':main()
