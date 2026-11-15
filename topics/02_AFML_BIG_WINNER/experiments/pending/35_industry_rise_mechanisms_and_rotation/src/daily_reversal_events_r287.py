from common import *
import pandas as pd
from process_replay_r09 import cooldown_alerts

def run():
    out=ROOT/'outputs/r287';out.mkdir(exist_ok=True)
    s=pd.read_parquet(ROOT/'outputs/r286/scores.parquet');s=s[s.eligible].copy()
    e=pd.read_parquet(ROOT/'outputs/r242/episodes.parquet');seg=pd.read_parquet(ROOT/'outputs/r242/segments.parquet')
    cal=pd.DatetimeIndex(pd.read_parquet(CACHE/'forecast_v5/CSI_ALL.parquet').index)
    ends=pd.Series(cal,index=cal).groupby(cal.to_period('M')).max();ends=ends[[p.end_time.normalize()<=cal.max() for p in ends.index]]
    origins=s[s.variant.eq('base')].drop(columns=['score','variant']).copy().reset_index(drop=True)
    origins['segment']=-1;origins['complete_path']=False;origins['episode_id']=np.nan;origins['signal_lead']=np.nan
    segments={k:g for k,g in seg.groupby(KEY)};episodes={k:g.sort_values('breach_i') for k,g in e[~e.left_boundary].groupby(KEY+['segment'])}
    for key,g in origins.groupby(KEY):
        for z in segments[key].itertuples():
            ix=g.index[g.day_i.between(z.start_i,z.end_i)];origins.loc[ix,'segment']=z.segment
            q=origins.loc[ix];entry=cal.get_indexer(q.entry_date);maturity=cal.get_indexer(q.maturity20)
            valid=(q.day_i+21<=z.end_i)&(entry==q.day_i+1)&(maturity==q.day_i+21)&q.y.notna()
            vi=q.index[valid];origins.loc[vi,'complete_path']=True
            pool=episodes.get(key+(z.segment,))
            if pool is None:continue
            days=pool.breach_i.to_numpy();indices=np.searchsorted(days,origins.loc[vi,'day_i'].to_numpy()+2)
            for idx,pos in zip(vi,indices):
                if pos<len(pool) and days[pos]<=origins.at[idx,'day_i']+21:
                    hit=pool.iloc[pos];origins.at[idx,'episode_id']=hit.episode_id;origins.at[idx,'signal_lead']=days[pos]-origins.at[idx,'day_i']
    assert origins.segment.ge(0).all();origins.to_parquet(out/'origins.parquet',index=False)
    s=s.merge(origins[KEY+['date','segment','complete_path','episode_id','signal_lead']],on=KEY+['date'],validate='many_to_one')
    allalerts=[]
    for variant,g in s.groupby('variant'):
        ordered=g.sort_values(['era','level','date','score','industry_code'],ascending=[True,True,True,False,True]);grp=ordered.groupby(['era','level','date']);raw=ordered[grp.cumcount()<np.ceil(.2*grp.score.transform('size'))]
        for strategy,a in [('daily',raw),('monthly',raw[raw.date.isin(ends.values)]),('daily_cooldown20',cooldown_alerts(raw))]:
            allalerts.append(a.assign(strategy=strategy))
    alerts=pd.concat(allalerts,ignore_index=True);alerts.to_parquet(out/'alerts.parquet',index=False)
    hits=alerts[alerts.episode_id.notna()].sort_values('date').drop_duplicates(['era','level','variant','strategy','episode_id'])
    hits.to_parquet(out/'first_alerts.parquet',index=False);rows=[];coverage=[]
    for (era,level),g in origins.groupby(['era','level']):
        catalogue=e[e.era.eq(era)&e.level.eq(level)&~e.left_boundary];observable=g.episode_id.nunique();monthly=g[g.date.isin(ends.values)].episode_id.nunique()
        coverage.append(dict(era=era,level=level,all_catalogue_nonleft=len(catalogue),daily_observable=observable,monthly_observable=monthly,not_daily_observable=len(catalogue)-observable,candidate_origins=len(g),incomplete_origins=int((~g.complete_path).sum())))
        for (variant,strategy),a in alerts[alerts.era.eq(era)&alerts.level.eq(level)].groupby(['variant','strategy']):
            found=a.episode_id.nunique();matched=a.episode_id.notna().sum();known=a[a.complete_path]
            rows.append(dict(era=era,level=level,variant=variant,strategy=strategy,observable_episodes=observable,detected_episodes=found,recall=found/observable if observable else np.nan,alerts=len(a),known_alerts=len(known),unknown_alerts=int((~a.complete_path).sum()),matched_alerts=int(matched),duplicate_episode_alerts=int(matched-found),unmatched_known_alerts=int((known.episode_id.isna()).sum()),fixed_label_precision=known.y.mean(),events_per100_alerts=100*found/len(a)))
    metrics=pd.DataFrame(rows);metrics.to_csv(out/'metrics.csv',index=False);pd.DataFrame(coverage).to_csv(out/'coverage.csv',index=False)
    comparisons=[]
    for (era,level,strategy),g in metrics.groupby(['era','level','strategy']):
        base=g[g.variant.eq('base')].iloc[0];hh=hits[hits.era.eq(era)&hits.level.eq(level)&hits.strategy.eq(strategy)]
        for variant in ['state','interaction']:
            a=g[g.variant.eq(variant)].iloc[0];q=hh[hh.variant.eq(variant)].merge(hh[hh.variant.eq('base')],on='episode_id',suffixes=('_new','_base'),validate='one_to_one');delta=q.signal_lead_new-q.signal_lead_base
            comparisons.append(dict(era=era,level=level,strategy=strategy,variant=variant,recall_delta=a.recall-base.recall,alert_delta=int(a.alerts-base.alerts),joint_events=len(q),earlier=int((delta>0).sum()),same=int((delta==0).sum()),later=int((delta<0).sum()),mean_paired_lead=delta.mean(),median_paired_lead=delta.median()))
    pd.DataFrame(comparisons).to_csv(out/'comparisons.csv',index=False)
    summary=dict(status='PASS',unique_origins=len(origins),incomplete_origins=int((~origins.complete_path).sum()),matched_origins=int(origins.episode_id.notna().sum()),observed_unique_episodes=int(origins.episode_id.nunique()),alert_rows=len(alerts),model_strategy_groups=len(metrics),comparisons=len(comparisons),adoption=False,no_refit=True)
    js(out/'summary.json',summary)
    protocol=json.loads((ROOT/'protocols/r287.json').read_text());reads=protocol['inputs']+['protocols/r287.json','src/daily_reversal_events_r287.py','src/process_replay_r09.py']
    js(out/'receipt.json',dict(inputs={p:sha(ROOT/p) for p in reads},benchmark_sha256=sha(CACHE/'forecast_v5/CSI_ALL.parquet'),outputs={p.name:sha(p) for p in out.iterdir() if p.name!='receipt.json'}));print(summary)
if __name__=='__main__':run()
