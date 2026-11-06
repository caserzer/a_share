"""Independent stage, duration, valuation and arithmetic checks for V4."""
from pathlib import Path
import json
import gzip
import re
import subprocess
import numpy as np
import pandas as pd
from context import EP, OLD, V2, V3, OUT, CACHE, THRESHOLDS, POLICIES, BENCHMARKS, previous, sha, js
from turns import upswings
from data import benchmarks


def main():
    checks=[]
    def check(name,valid,**details):
        checks.append(dict(name=name,passed=bool(valid),**details))
        if not valid:
            js('audits/validation_failed',dict(status='FAIL',checks=checks))
            raise AssertionError(name)
    source=json.loads((OUT/'audits/inputs.json').read_text())
    prior=json.loads((OUT/'audits/predecessors.json').read_text())
    for name,item in prior.items():
        root=Path(item['root'])
        check(name+'_bytes_preserved',sha(root/'outputs/manifest.json')==item['manifest_sha256'] and
              all(sha(root/r['path'])==r['sha256'] for r in item['files']),files=len(item['files']))
    for name,field in [('panel_with_tail.parquet','panel_sha256'),('valuation_marks.parquet','marks_sha256'),
                       ('assignments_with_tail_return.parquet','assignments_sha256')]:
        check(name+'_identity',sha(CACHE/name)==source[field])
    root=Path(source['price_release'])
    check('all_consumed_daily_quote_partitions_unchanged',all(sha(root/name)==digest for name,digest in source['daily_read_files'].items()),
          files=len(source['daily_read_files']))
    panel=pd.read_parquet(CACHE/'panel_with_tail.parquet')
    marks=pd.read_parquet(CACHE/'valuation_marks.parquet')
    joined=pd.read_parquet(CACHE/'assignments_with_tail_return.parquet')
    paths=pd.read_parquet(CACHE/'industry_paths.parquet')
    phases=pd.read_csv(OUT/'details/all_natural_stages.csv.gz')
    scores=pd.concat([pd.read_csv(OUT/f'details/stage_scores_T{int(t*100)}.csv.gz') for t in THRESHOLDS],ignore_index=True)
    stocks=pd.concat([pd.read_csv(OUT/f'details/stock_scores_T{int(t*100)}.csv.gz') for t in THRESHOLDS],ignore_index=True)
    check('full_calendar_and_partial_tail',source['start_session']=='2017-01-03' and source['end_session']=='2026-10-21' and
          panel.date.max()==pd.Timestamp('2026-10-21') and panel.month.min()==pd.Period('2017-01'))
    oldpanel=pd.read_parquet(previous.CACHE/'panel.parquet')
    earlier=panel[panel.month.lt(pd.Period('2026-10'))].copy()
    columns=[x for x in oldpanel.columns if x!='next_return']
    pd.testing.assert_frame_equal(oldpanel[columns].reset_index(drop=True),earlier[columns].reset_index(drop=True),check_dtype=False)
    check('every_original_quote_entry_share_cap_preserved',True,rows=len(oldpanel))
    check('no_future_valuation_marks',(marks.last_mark_date.isna()|marks.last_mark_date.le(marks.date)).all())
    check('exact_policy_matches_original_cap',np.allclose(marks.EXACT,marks.cap,equal_nan=True))
    for policy,age in POLICIES[1:]:
        changed=marks.cap.isna()&marks[policy].notna()
        check(policy+'_uses_only_bounded_last_known_mark',
              marks.loc[changed,'mark_age_days'].between(0,age).all() and
              np.allclose(marks.loc[changed,policy],marks.loc[changed,'last_mark_close']*marks.loc[changed,'total_shares']))
    check('valuation_policy_coverage_nested',(~marks.EXACT.notna()|marks.MARK_7D.notna()).all() and
          (~marks.MARK_7D.notna()|marks.MARK_31D.notna()).all())
    check('industry_blocks_do_not_cross_taxonomy',all(previous.era_for_month(m)==e for m,e in
          paths[['month','era']].drop_duplicates().itertuples(index=False,name=None)))
    check('no_imputed_return_inside_price_blocks',paths.loc[~paths.anchor,'monthly_return'].notna().all() and
          paths.nav.gt(0).all() and paths.loc[~paths.anchor,'coverage'].ge(.8).all())
    check('phase_ids_unique',not phases.phase_id.duplicated().any())
    start=pd.PeriodIndex(phases.start_month,freq='M');end=pd.PeriodIndex(phases.end_month,freq='M')
    months=end.asi8-start.asi8
    check('duration_uses_actual_phase_endpoints',np.array_equal(months,phases.duration_months))
    expected=np.where(months<6,'SHORT_LT6',np.where(months<=18,'IN_RANGE_6_18','LONG_GT18'))
    check('six_and_eighteen_bounds_are_inclusive',np.array_equal(expected,phases.length_class))
    check('long_stages_remain_present_not_cut_to_18',phases.duration_months.gt(18).any() and
          phases.loc[phases.duration_months.gt(18),'length_class'].eq('LONG_GT18').all(),max_months=int(phases.duration_months.max()))
    c=phases[phases.status.eq('CONFIRMED')]
    check('confirmed_end_is_peak_and_confirmation_is_later',
          c.end_date.eq(c.peak_date).all() and (pd.to_datetime(c.end_confirmed_at)>pd.to_datetime(c.peak_date)).all() and
          (pd.to_datetime(c.start_confirmed_at)>pd.to_datetime(c.start_date)).all() and
          (pd.to_datetime(c.start_confirmed_at)<=pd.to_datetime(c.peak_date)).all())
    opened=phases[phases.status.eq('OPEN')]
    check('unconfirmed_tail_is_never_presented_as_completed',opened.right_censored.all() and opened.end_confirmed_at.isna().all())
    check('partial_tail_never_a_confirmed_peak',not c.end_is_partial.any())
    # Independent price and drawdown properties, using the saved full price blocks.
    lookup={k:g.sort_values('date').set_index('month') for k,g in paths.groupby(['era','level','industry_code','block'])}
    failures=[]
    for s in phases.itertuples():
        g=lookup[(s.era,s.level,s.industry_code,s.block)]
        a,p,z=[pd.Period(x) for x in [s.start_month,s.peak_month,s.end_month]]
        value=g.loc[z,'nav']/g.loc[a,'nav']-1
        if not np.isclose(value,s.industry_return,rtol=1e-10,atol=1e-10):failures.append(s.phase_id+':return')
        confirm_month=pd.Timestamp(s.start_confirmed_at).to_period('M')
        if g.loc[confirm_month,'nav']/g.loc[a,'nav']-1 < s.drawdown_threshold-1e-10:failures.append(s.phase_id+':start_confirm')
        if s.status=='CONFIRMED':
            cm=pd.Timestamp(s.end_confirmed_at).to_period('M')
            peak=g.loc[p,'nav'];value=g.loc[cm,'nav']
            if 1-value/peak < s.drawdown_threshold-1e-10:failures.append(s.phase_id+':drawdown')
            before=g[(g.index>p)&(g.index<cm)].nav
            if ((1-before/peak)>=s.drawdown_threshold+1e-10).any():failures.append(s.phase_id+':late_confirm')
    check('all_stage_gain_and_turn_confirmation_properties',not failures,phases=len(phases),failures=failures[:10])
    # A completed price reversal cannot be changed by appending future observations.
    count=0
    for (_,_,_,_),g in paths.groupby(['era','level','industry_code','block']):
        g=g.sort_values('date').reset_index(drop=True)
        if len(g)<24:continue
        for t in THRESHOLDS:
            prefix=upswings(g.nav.iloc[:24],t)
            full=upswings(g.nav,t)
            a=[x for x in prefix if x['status']=='CONFIRMED']
            b=[x for x in full if x['status']=='CONFIRMED' and x['end_confirm_i']<24]
            if a!=b:raise AssertionError('Confirmed prefix changed')
            count+=1
    check('all_confirmed_price_prefixes_stable',True,comparisons=count)
    check('every_phase_retained_under_every_policy_and_benchmark',scores.groupby('phase_id').size().eq(6).all() and
          len(scores)==len(phases)*6)
    primary=(scores.phase_status.eq('CONFIRMED')&~scores.left_censored&scores.duration_months.between(6,18)&
             scores.industry_return.gt(0)&scores.industry_excess.gt(0))
    check('candidate_filter_only_duration_up_and_excess',np.array_equal(primary,scores.primary_stage))
    check('unranked_industry_candidates_retained',(scores.primary_stage&~scores.rank_complete).any())
    # Compare origin rank against separate archived mark policies, not any future return.
    group={k:g for k,g in joined.groupby(['era','level','industry_code','month'],sort=False)}
    mark=marks.set_index(['security_id','month'])
    rank_keys=scores[['era','level','industry_code','start_month','policy','rank_complete','top3']].drop_duplicates()
    bad=[]
    for s in rank_keys.itertuples():
        month=pd.Period(s.start_month);g=group.get((s.era,s.level,s.industry_code,month))
        expected_rank=None
        if g is not None and len(g)>=3 and g.unresolved.eq(0).all():
            idx=pd.MultiIndex.from_arrays([g.security_id,[month]*len(g)])
            values=mark[s.policy].reindex(idx).to_numpy(float)
            if np.isfinite(values).all():
                x=g.assign(rank_cap=values).sort_values(['rank_cap','security_id'],ascending=[False,True]).head(3)
                expected_rank=';'.join(x.instrument)
        if (expected_rank is not None)!=s.rank_complete or (expected_rank is not None and expected_rank!=s.top3):
            bad.append((s.industry_code,s.start_month,s.policy))
    check('all_rankings_frozen_at_natural_start',not bad,unique_rank_keys=len(rank_keys),failures=bad[:10])
    q=panel.set_index(['security_id','month'])
    starts=pd.PeriodIndex(stocks.start_month,freq='M');ends=pd.PeriodIndex(stocks.end_month,freq='M')
    origin_idx=pd.MultiIndex.from_arrays([stocks.security_id,starts]);end_idx=pd.MultiIndex.from_arrays([stocks.security_id,ends])
    op=q.entry_open.reindex(origin_idx).to_numpy(float);cl=q.qfq_close.reindex(end_idx).to_numpy(float)
    chain0=q.entry_chain.reindex(origin_idx).to_numpy();chain1=q.close_chain.reindex(end_idx).to_numpy()
    expected_return=np.where(chain0==chain1,cl/op-1,np.nan)
    check('all_stock_returns_use_original_open_and_stage_endpoint',np.allclose(expected_return,stocks.return_value,equal_nan=True,rtol=1e-10,atol=1e-10),rows=len(stocks))
    check('no_valuation_price_used_as_trade_entry',stocks.trade_price_imputed.eq(False).all())
    indices=benchmarks()
    for label,index in indices.items():
        s=scores[scores.benchmark.eq(label)]
        a=pd.to_datetime(s.start_date);b=pd.to_datetime(s.end_date);entry=pd.to_datetime(s.entry_date)
        phase=index.close.reindex(b).to_numpy(float)/index.close.reindex(a).to_numpy(float)-1
        holding=index.close.reindex(b).to_numpy(float)/index.open.reindex(entry).to_numpy(float)-1
        check(label+'_phase_and_holding_benchmarks_same_dates',np.allclose(phase,s.industry_benchmark_return,equal_nan=True) and
              np.allclose(holding,s.holding_benchmark_return,equal_nan=True))
    check('every_portfolio_excess_is_a_return_difference',np.allclose(scores.portfolio_return-scores.holding_benchmark_return,
          scores.portfolio_excess,equal_nan=True))
    values=np.vstack([scores[f'stock{i}_return'].to_numpy(float) for i in [1,2,3]])
    complete=scores.complete.to_numpy(bool)
    expected=((values[:,complete]>0).all(axis=0)&(values[:,complete]>scores.loc[complete,'holding_benchmark_return'].to_numpy()[None,:]).all(axis=0))
    check('three_joint_success_distinct_from_average',np.array_equal(expected,scores.loc[complete,'all_positive_and_beat'].to_numpy(bool)))
    check('unknown_rank_or_trade_not_failed_success',scores.loc[~scores.complete,['portfolio_excess','all_beat','all_positive_and_beat']].isna().all().all())
    check('unknown_paths_not_zero_duration',scores.loc[~scores.path_complete,['joint_excess_longest','joint_excess_from_first']].isna().all().all())
    for threshold in THRESHOLDS:
        t=str(int(threshold*100));passing=pd.read_csv(OUT/f'screens/all_three_positive_and_beat_T{t}.csv')
        check('screen_T'+t+'_only_confirmed_inrange_joint_success',passing.primary_stage.all() and passing.complete.all() and
              passing.all_positive_and_beat.eq(True).all() and passing.duration_months.between(6,18).all())
        detail_stock=pd.read_csv(OUT/f'details/screened_stocks_T{t}.csv.gz')
        selected=set(passing[['phase_id','policy','benchmark']].itertuples(index=False,name=None))
        check('screened_stock_T'+t+'_matches_exact_selection_keys',all(k in selected for k in
              detail_stock[['phase_id','policy','benchmark']].itertuples(index=False,name=None)) and
              detail_stock.return_value.gt(0).all() and detail_stock.excess.gt(0).all())
    for file in (OUT/'details').glob('*.csv.gz'):
        check('gzip_'+file.stem,gzip.decompress(file.read_bytes())==(CACHE/file.name[:-3]).read_bytes())
    missing=[];links=0
    for p in EP.rglob('*.md'):
        for target in re.findall(r'\[[^\]]*\]\(([^)]+)\)',p.read_text()):
            if '://' in target or target.startswith('#'):continue
            links+=1
            if not (p.parent/target.split('#')[0]).exists():missing.append((str(p),target))
    check('all_local_report_links_valid',not missing,links=links,missing=missing)
    test=subprocess.run([str(OLD.parents[2]/'.venv/bin/python'),'-m','pytest','-q',str(EP/'tests')],capture_output=True,text=True)
    check('natural_turn_and_valuation_contract_tests',test.returncode==0,output=test.stdout.strip())
    check('tracked_predecessors_unchanged',subprocess.run(['git','diff','--quiet'],cwd=OLD.parents[4]).returncode==0)
    js('audits/validation',dict(status='PASS',checks=checks,validates='historical_stage_measurement_not_prediction'))
    files=[dict(path=str(p.relative_to(EP)),bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(EP.rglob('*'))
           if p.is_file() and '__pycache__' not in p.parts and '.pytest_cache' not in p.parts and p!=OUT/'manifest.json']
    js('manifest',dict(status='validated_working_result',files=files,sealed=False,strict_PIT='BLOCKED_DATA',
                       duration_bounds=[6,18],long_stages_split=False))
    print('V4 validation PASS:',len(checks),'checks;',len(phases),'natural stages')


if __name__=='__main__':main()
