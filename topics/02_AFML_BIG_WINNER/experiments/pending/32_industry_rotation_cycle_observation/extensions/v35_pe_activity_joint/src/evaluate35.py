"""Full-label classification, matched-K economics, common-support ablations."""
from common35 import *
from evaluate31 import summarize
from evaluate34 import interval

def run():
    receipt=json.loads((OUT/'prediction_receipt.json').read_text())
    assert sha(CACHE/'scores.parquet')==receipt['scores_sha256']
    scores=pd.read_parquet(CACHE/'scores.parquet');labels=pd.read_parquet(OLD/'stage_b_labels.parquet')
    outcomes=pd.read_parquet(ECON/'outcomes.parquet')
    calendar=pd.DatetimeIndex(pd.read_parquet(OLD/'CSI_ALL.parquet').index).sort_values()
    phases=pd.read_parquet(OLD/'daily_phases.parquet').set_index('phase_id')
    classification=[];annual_class=[];economics=[];annual=[];daily=[];coverage=[];details=[];checks=[];frames=[]
    mechanism=[];mechanism_details=[];eligible_coverage=[]
    for path in sorted((ECON/'frames').glob('*.parquet')):
        task=path.stem;f=pd.read_parquet(path)
        f=f.merge(scores,on=IDENTITY,validate='many_to_one')
        eligible=f.state_eligible.eq(1)&f.market_up
        k=f.select_accepted.groupby([f.date,f.level]).transform('sum')
        methods=['baseline']+list(ACTIVITY)+list(MODELS)
        score_map={name:(f.diffusion_tree if name=='baseline' else f[name]) for name in methods}
        selected={'accepted':f.select_accepted,'momentum':f.select_momentum_matched}
        for name in methods:selected[name]=top_k(f,score_map[name],k,eligible)
        for family in ACTIVITY:
            mask=eligible&f[family+'_joint_complete']
            kc=(f.select_accepted&mask).groupby([f.date,f.level]).transform('sum')
            for name in ['baseline',family,'pe','joint_'+family,'missing_'+family]:
                key='complete_'+family+'_'+name
                selected[key]=top_k(f,score_map[name],kc,mask)
            target=selected['complete_'+family+'_baseline'].groupby([f.date,f.level]).sum()
            assert all(selected['complete_'+family+'_'+name].groupby([f.date,f.level]).sum().equals(target)
                for name in [family,'pe','joint_'+family,'missing_'+family])
        for name in methods:
            assert selected[name].groupby([f.date,f.level]).sum().equals(selected['baseline'].groupby([f.date,f.level]).sum())
        for name,mask in selected.items():
            f['selected_'+name]=mask;f['first_'+name]=False
            if f.threshold.iloc[0]==.15 and f.benchmark.iloc[0]=='CSI_ALL':
                s=f[mask&f.level.eq('L3')];f.loc[s.index,'first_'+name]=episode_starts(s,calendar)
        f['mechanism_first']=False
        known_sign=f.pe_change21.notna()&f.turn_short.notna()
        f['expansion_cell']=np.select([~known_sign,(f.pe_change21>0)&(f.turn_short>0),
            (f.pe_change21>0)&~(f.turn_short>0),~(f.pe_change21>0)&(f.turn_short>0)],
            ['UNKNOWN','BOTH','PE_ONLY','ACTIVITY_ONLY'],default='NEITHER')
        if f.threshold.iloc[0]==.15 and f.benchmark.iloc[0]=='CSI_ALL':
            s=f[eligible&f.level.eq('L3')];f.loc[s.index,'mechanism_first']=episode_starts(s,calendar)
        destination=CACHE/'evaluation_frames';destination.mkdir(exist_ok=True)
        f.to_parquet(destination/path.name,index=False);frames.append(dict(task=task,path=str(destination/path.name),sha256=sha(destination/path.name)))
        f=f.merge(labels,on=['row_id','threshold','benchmark'],validate='one_to_one')
        f.loc[f.label_available_at.gt(f.date+pd.DateOffset(months=24)),'y']=np.nan
        for level,g in f.groupby('level'):
            sig=dict(task=task,frequency=g.frequency.iloc[0],threshold=g.threshold.iloc[0],benchmark=g.benchmark.iloc[0],level=level)
            primary=level=='L3' and sig['threshold']==.15 and sig['benchmark']=='CSI_ALL'
            known=g[g.y.notna()];positive=known[known.y.eq(1)];events=positive.event_or_witness_id.nunique()
            def metrics(part,name,score=None):
                known=part[part.y.notna()];positive=known[known.y.eq(1)];events=positive.event_or_witness_id.nunique()
                hit=known[known['selected_'+name]]
                first=positive[positive['selected_'+name]].groupby('event_or_witness_id').date.min()
                delay=(first-phases.start_date.reindex(first.index)).dt.days
                return dict(known_observations=len(known),positive_observations=len(positive),
                    all_alerts=int(part['selected_'+name].sum()),known_alerts=len(hit),unknown_alerts=int(part['selected_'+name].sum())-len(hit),
                    precision=hit.groupby('date').y.mean().mean(),pooled_precision=hit.y.mean(),
                    point_recall=hit.y.sum()/len(positive) if len(positive) else np.nan,
                    cycle_recall=len(first)/events if events else np.nan,evaluable_cycles=events,detected_cycles=len(first),
                    mean_delay=delay.mean(),median_delay=delay.median(),
                    brier=np.mean((score.loc[known.index]-known.y)**2) if score is not None else np.nan)
            for name in selected:
                score=g.diffusion_tree if name=='baseline' else g[name] if name in list(ACTIVITY)+list(MODELS) else None
                classification.append(dict(**sig,method=name,**metrics(g,name,score)))
                if primary and name in ['accepted','baseline']+list(ACTIVITY)+list(MODELS):
                    for year,part in g.groupby(g.date.dt.year):annual_class.append(dict(**sig,method=name,year=year,**metrics(part,name,score)))
            if not primary:continue
            for year,part in [('ALL',g)]+list(g.groupby(g.date.dt.year)):
                eligible_part=part[part.state_eligible.eq(1)&part.market_up]
                for family in ACTIVITY:
                    complete=eligible_part[family+'_joint_complete']
                    eligible_coverage.append(dict(frequency=sig['frequency'],year=year,family=family,
                        eligible_rows=len(eligible_part),complete_rows=int(complete.sum()),
                        complete_fraction=complete.mean(),
                        accepted_alerts=int(part.selected_accepted.sum()),
                        complete_alerts=int(part['selected_complete_'+family+'_baseline'].sum())))
            g=g.merge(outcomes[outcomes.benchmark.eq(sig['benchmark'])].drop(columns='benchmark'),on='row_id',validate='one_to_many')
            for name in selected:
                for unit,prefix in [('all_alerts','selected_'),('six_month_launches','first_')]:
                    for months,h in g[g[prefix+name]].groupby('months'):
                        economics.append(dict(**sig,method=name,unit=unit,months=months,**summarize(h)))
                        for status,part in h.groupby('outcome_status'):coverage.append(dict(**sig,method=name,unit=unit,months=months,status=status,count=len(part)))
                        if months!=6:continue
                        for year,part in h.groupby(h.date.dt.year):annual.append(dict(**sig,method=name,unit=unit,year=year,**summarize(part)))
                        good=h[h.outcome_status.eq('OK')]
                        dates=good.groupby('date').excess_return.mean().rename('excess').reset_index()
                        dates['frequency']=sig['frequency'];dates['method']=name;dates['unit']=unit;daily.append(dates)
                        if unit=='six_month_launches' and not name.startswith('complete_'):
                            cols=['row_id','date','era','level','industry_code','industry_name','block','frequency','y','entry_date','end_date','outcome_status','industry_return','excess_return','max_drawdown']
                            details.append(h[cols].assign(method=name))
            h=g[g.mechanism_first&g.months.eq(6)]
            for cell,part in h.groupby('expansion_cell'):
                mechanism.append(dict(frequency=sig['frequency'],cell=cell,year='ALL',precision=part.y.mean(),**summarize(part)))
                for year,p in part.groupby(part.date.dt.year):mechanism.append(dict(frequency=sig['frequency'],cell=cell,year=year,precision=p.y.mean(),**summarize(p)))
            mechanism_details.append(h[['row_id','date','frequency','era','level','industry_code','block','pe_change21','turn_short','expansion_cell','y','outcome_status','industry_return','excess_return']])
            checks.append('full and common-support K matched '+task)
        print('joint evaluation',task,flush=True)
    c=pd.DataFrame(classification);c.to_csv(OUT/'classification_all_tasks.csv',index=False)
    c.query("level=='L3' and threshold==0.15 and benchmark=='CSI_ALL'").to_csv(OUT/'classification_primary.csv',index=False)
    pd.DataFrame(annual_class).to_csv(OUT/'annual_classification.csv',index=False)
    pd.DataFrame(eligible_coverage).to_csv(OUT/'eligible_coverage.csv',index=False)
    pd.DataFrame(economics).to_csv(OUT/'economics_primary.csv',index=False)
    pd.DataFrame(annual).to_csv(OUT/'annual_economics.csv',index=False)
    pd.DataFrame(coverage).to_csv(OUT/'outcome_coverage.csv',index=False)
    pd.concat(details).to_csv(OUT/'primary_six_month_launches.csv.gz',index=False,compression={'method':'gzip','mtime':0})
    pd.DataFrame(mechanism).to_csv(OUT/'four_cells.csv',index=False)
    pd.concat(mechanism_details).to_csv(OUT/'four_cell_launches.csv.gz',index=False,compression={'method':'gzip','mtime':0})
    dates=pd.concat(daily,ignore_index=True);dates.to_csv(OUT/'daily_excess.csv',index=False)
    intervals=[]
    for (frequency,unit),g in dates.groupby(['frequency','unit']):
        p=g.pivot(index='date',columns='method',values='excess')
        for family in ACTIVITY:
            for scope,left,right in [('full','joint_'+family,family),('missing_control','joint_'+family,'missing_'+family),
                ('baseline','joint_'+family,'baseline'),('complete','complete_'+family+'_joint_'+family,'complete_'+family+'_'+family),
                ('complete_missing','complete_'+family+'_joint_'+family,'complete_'+family+'_missing_'+family)]:
                pair=p.reindex(columns=[left,right]).dropna();diff=pair[left]-pair[right]
                intervals.append(dict(frequency=frequency,unit=unit,family=family,scope=scope,paired_dates=len(pair),**interval(pair.index,diff)))
    pd.DataFrame(intervals).to_csv(OUT/'paired_intervals.csv',index=False)
    js(OUT/'evaluation_receipt.json',dict(frames=frames,checks=checks,primary_comparisons=9,code_sha256=sha(__file__),
        primary_horizon_months=6,bootstrap_repeats=5000,block_months=12,strict_PIT='BLOCKED_DATA',independent_forward='FORWARD_PENDING'))
    print('JOINT EVALUATION COMPLETE',flush=True)

if __name__=='__main__':run()
