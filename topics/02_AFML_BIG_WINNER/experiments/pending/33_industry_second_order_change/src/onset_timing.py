"""R08 same-endpoint timing comparisons and nuisance diagnostics."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from onset_replay import EP,KEY,sha
from onset_panel import valid_window
OUT=EP/'outputs/r08'


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    p=pd.read_parquet('/tmp/ep33_onset_panel.parquet')
    episodes=pd.read_csv(EP/'outputs/r07/episodes.csv.gz',parse_dates=['date'])
    refs=pd.read_csv(EP/'outputs/r07/references.csv.gz',parse_dates=['date'])
    groups={k:g.sort_values('date').reset_index(drop=True) for k,g in p.groupby(KEY)}
    short=[];paired=[]
    for k,g in groups.items():
        flag=g.eligible&g.rate20.lt(0)&g.rate5.gt(0)&g.rate5.shift(1).le(0)&g.week_i.diff().eq(1)
        last=-1000
        for i in np.flatnonzero(flag):
            r=g.iloc[i]
            if not (pd.Timestamp('2021-01-01')<=r.date<=pd.Timestamp('2025-12-31')) or r.week_i-last<8:continue
            last=r.week_i
            short.append({q:r[q] for q in ['era','industry_code','industry_name','block','date','week_i','sample_case']}|{'method':'short_reversal','position':i,'followup_known':valid_window(g,i,1,8)})
    short=pd.DataFrame(short);short.to_csv(OUT/'short_reversal_episodes.csv.gz',index=False)
    all_e=pd.concat([episodes,short],ignore_index=True)
    lookup={k:g for k,g in all_e.groupby(KEY)}
    matches=[]
    for _,r in refs.iterrows():
        g=lookup.get(tuple(r[q] for q in KEY),all_e.iloc[:0]);g=g[g.method.eq('short_reversal')&g.week_i.between(r.week_i-4,r.week_i+4)].sort_values('date')
        matches.append(dict(reference=r.reference,matched=len(g)>0,delay=np.nan if g.empty else g.week_i.iloc[0]-r.week_i))
    mat=pd.DataFrame(matches);shortsummary=mat.groupby('reference').agg(references=('matched','size'),matched=('matched','sum'),median_delay=('delay','median')).reset_index();shortsummary['recall']=shortsummary.matched/shortsummary.references
    shortsummary.to_csv(OUT/'short_reference_summary.csv',index=False)
    # Reference association diagnostic, not a one-to-one independent precision estimate.
    unmatched=[];rl={k:g for k,g in refs[refs.reference.eq('trough_w4')].groupby(KEY)}
    for method,g in all_e[all_e.followup_known].groupby('method'):
        matched=0;total=0
        for _,r in g.iterrows():
            block=groups[tuple(r[q] for q in KEY)];i=int(r.position)
            if not valid_window(block,i,-4,8):continue
            total+=1;rr=rl.get(tuple(r[q] for q in KEY),refs.iloc[:0]);matched+=int(rr.week_i.between(r.week_i-4,r.week_i+4).any())
        unmatched.append(dict(method=method,evaluable_prompts=total,matched_reference=matched,unmatched=total-matched,unmatched_fraction=(total-matched)/total if total else np.nan))
    pd.DataFrame(unmatched).to_csv(OUT/'unmatched_prompt_diagnostic.csv',index=False)
    pressure=episodes[episodes.method.eq('pressure_easing')]
    for _,r in pressure.iterrows():
        g=groups[tuple(r[q] for q in KEY)];i=int(r.position)
        if not valid_window(g,i,1,8):continue
        final=g.iloc[i+5:i+9];y=int(final.rate20.gt(0).sum())>=3
        row={q:r[q] for q in ['era','industry_code','date','week_i','sample_case']};row['sustained_final4']=y
        for method in ['broad_confirmation','long_confirmation','old_top10']:
            delay=r[method+'_delay'];row[method+'_accepted']=bool(pd.notna(delay) and delay<=4);row[method+'_delay']=delay if row[method+'_accepted'] else np.nan
        paired.append(row)
    pairs=pd.DataFrame(paired);pairs.to_csv(OUT/'common_endpoint_episodes.csv.gz',index=False)
    summaries=[]
    for scope,g in [('all',pairs),('outside_sample',pairs[~pairs.sample_case])]:
        y=g.sustained_final4;total_pos=int(y.sum())
        for method in ['early_all','broad_confirmation','long_confirmation','old_top10']:
            accept=pd.Series(True,index=g.index) if method=='early_all' else g[method+'_accepted']
            a=g[accept];pos=int(a.sustained_final4.sum())
            summaries.append(dict(scope=scope,method=method,episodes=len(g),accepted=len(a),not_accepted=int((~accept).sum()),
                positive_retained=pos,positive_missed=total_pos-pos,total_positive=total_pos,
                retained_fraction=pos/total_pos,non_sustained_fraction=1-pos/len(a) if len(a) else np.nan,
                median_wait=0 if method=='early_all' else a[method+'_delay'].median()))
    pd.DataFrame(summaries).to_csv(OUT/'common_endpoint_summary.csv',index=False)
    annual=[]
    for year,g in pairs.groupby(pairs.date.dt.year):
        for method in ['early_all','broad_confirmation','long_confirmation','old_top10']:
            a=g if method=='early_all' else g[g[method+'_accepted']]
            annual.append(dict(year=year,method=method,episodes=len(g),accepted=len(a),positive=int(a.sustained_final4.sum()),non_sustained_fraction=1-a.sustained_final4.mean()))
    pd.DataFrame(annual).to_csv(OUT/'common_endpoint_annual.csv',index=False)
    eligible=p[p.eligible&p.date.between('2021-01-01','2025-12-31')]
    relative=eligible[eligible.rate20.gt(0)&eligible.breadth21.notna()]
    market_fraction=eligible.groupby('date').market_breadth_up_fraction.first()
    confirm_common=[]
    for _,r in pressure.iterrows():
        if pd.isna(r.broad_confirmation_delay):continue
        g=groups[tuple(r[q] for q in KEY)];j=int(r.position+r.broad_confirmation_delay)
        frac=market_fraction.get(g.date.iloc[j],np.nan)
        confirm_common.append(dict(date=g.date.iloc[j],common_up_fraction=frac))
    cc=pd.DataFrame(confirm_common);cc.to_csv(OUT/'confirmation_market_context.csv',index=False)
    finance=pd.read_csv(EP/'outputs/r04/industry_coverage.csv.gz',parse_dates=['date']).sort_values(['era','industry_code','date'])
    fg=finance.groupby(['era','industry_code']);prev=fg.finance_acceleration.shift(1);dc=finance.finance_coverage-fg.finance_coverage.shift(1)
    gap=finance.date-fg.date.shift(1)
    flip=finance.finance_acceleration.gt(0)&prev.le(0)&gap.le(pd.Timedelta(days=14))
    diagnostics={'positive_relative_weeks':len(relative),'positive_relative_breadth_below_half':int(relative.breadth21.lt(.5).sum()),
        'relative_breadth_conflict_fraction':relative.breadth21.lt(.5).mean(),
        'observed_broad_confirmations':len(cc),'market_context_known':int(cc.common_up_fraction.notna().sum()),
        'confirmations_in_common_expansion_fraction':cc.common_up_fraction.dropna().ge(.7).mean(),
        'financial_acceleration_positive_crossings':int(flip.sum()),'with_10pp_coverage_change':int((flip&dc.abs().ge(.1)).sum()),
        'finance_note':'sign changes in partial vendor aggregates; not a causal financial onset label'}
    (OUT/'nuisance_diagnostics.json').write_text(json.dumps(diagnostics,indent=2)+'\n')
    inputs=[EP/'rounds/r08_timing_discrimination_plan.md',Path(__file__),EP/'src/onset_panel.py',Path('/tmp/ep33_onset_panel.parquet'),EP/'outputs/r07/episodes.csv.gz',EP/'outputs/r07/references.csv.gz',EP/'outputs/r04/industry_coverage.csv.gz']
    (OUT/'receipt.json').write_text(json.dumps({'inputs':{str(q):sha(q) for q in inputs},'evaluation':'same final 4 weeks for all policies; no payoff optimization'},indent=2)+'\n')
    print(shortsummary.to_string(index=False));print(pd.DataFrame(summaries).query('scope=="all"').to_string(index=False));print(json.dumps(diagnostics,indent=2))

if __name__=='__main__':main()
