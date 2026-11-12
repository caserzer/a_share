"""Full-process window audit, descriptive multi-reason attribution only."""
import json
import pandas as pd
from audit_local_inputs import EP,sha


def main():
    out=EP/'outputs/r01'
    if (out/'omissions.json').exists():raise FileExistsError('omission audit exists')
    pfile=EP/'outputs/r00_metric_denominators/full_process_registry.parquet'
    wfile=out/'weekly_catalog.parquet';afile=out/'evaluated_new_observations.parquet'
    p=pd.read_parquet(pfile);w=pd.read_parquet(wfile);a=pd.read_parquet(afile)
    groups={k:g for k,g in w.groupby(['era','industry_code'])}
    hits=set(a.loc[a.recall_credit,'process_id'])
    unresolved=set(a.loc[a.outcome.eq('UNKNOWN') & a.process_id.notna(),'process_id'])-hits
    results=[];windows=[]
    for r in p[p.mature & ~p.left_origin_uncertain].itertuples():
        g=groups.get((r.era,r.industry_code),w.iloc[:0])
        g=g[g.day_i.between(r.start_day_i-5,r.start_day_i+10)]
        for z in g.to_dict('records'):
            windows.append(dict(process_id=r.process_id,process_origin=r.start_date,**z))
        reasons=g.reason.value_counts().to_dict()
        owned=a[a.process_id.eq(r.process_id)]
        positive=g.score.gt(0)&g.eligible.eq(True)
        # Ordered descriptive partition; multi-reason counters below retain overlap.
        if r.process_id in hits:category='TIMELY_SUCCESS'
        elif r.process_id in unresolved:category='UNRESOLVED'
        elif len(owned):category='ASSIGNED_ALERT_FAILED'
        elif g.state.eq('NEW').any():category='NEW_ASSIGNED_ELSEWHERE'
        elif g.reason.eq('CAPACITY_NOT_SELECTED').any():category='POSITIVE_CAPACITY_EXCLUDED'
        elif (g.in_pool & positive).any():category='ALREADY_TRACKING'
        elif g.reason.eq('COOLDOWN').any():category='COOLDOWN'
        elif positive.any():category='POSITIVE_EXIT_OR_OTHER'
        elif g.eligible.eq(True).any():category='NO_POSITIVE_REVIEW'
        elif len(g):category='ALL_REVIEWS_DATA_UNKNOWN'
        else:category='NO_REVIEW_IN_WINDOW'
        results.append(dict(process_id=r.process_id,era=r.era,industry_code=r.industry_code,
                            kind=r.kind,origin=r.start_date,category=category,reviews=len(g),
                            positive_reviews=int(positive.sum()),best_score=None if g.score.notna().sum()==0 else float(g.score.max()),
                            **{f'reason_{key}':int(reasons.get(key,0)) for key in sorted(w.reason.unique())}))
    f=pd.DataFrame(results);window=pd.DataFrame(windows)
    assert len(f)==2411 and f.process_id.nunique()==len(f)
    assert int(f.category.eq('TIMELY_SUCCESS').sum())==37
    assert int(f.category.eq('UNRESOLVED').sum())==1
    f.to_parquet(out/'process_window_audit.parquet',index=False)
    window.to_parquet(out/'process_window_catalog_rows.parquet',index=False)
    misses=f[~f.category.isin(['TIMELY_SUCCESS','UNRESOLVED'])]
    examples=misses.sort_values(['origin','process_id']).groupby(['era','category'],sort=True).head(1)
    examples.to_json(out/'omission_examples.json',orient='records',date_format='iso',indent=2,force_ascii=False)
    result=dict(scope='Post-result descriptive partition; not causal counterfactual or new labels',
                partition_order=['TIMELY_SUCCESS','UNRESOLVED','ASSIGNED_ALERT_FAILED','NEW_ASSIGNED_ELSEWHERE','POSITIVE_CAPACITY_EXCLUDED','ALREADY_TRACKING','COOLDOWN','POSITIVE_EXIT_OR_OTHER','NO_POSITIVE_REVIEW','ALL_REVIEWS_DATA_UNKNOWN','NO_REVIEW_IN_WINDOW'],
                mature_known=len(f),known_missed=len(misses),categories=f.category.value_counts().to_dict(),
                multi_reason_missed={c.removeprefix('reason_'):int(misses[c].gt(0).sum()) for c in f if c.startswith('reason_')},
                window_rows=len(window),example_selection='Earliest origin per era and omission category; examples do not establish effectiveness',
                examples=len(examples),inputs={str(x):sha(x) for x in [pfile,wfile,afile,EP/'src/r01_omissions.py']})
    (out/'omissions.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='inputs'},ensure_ascii=False))


if __name__=='__main__':main()
