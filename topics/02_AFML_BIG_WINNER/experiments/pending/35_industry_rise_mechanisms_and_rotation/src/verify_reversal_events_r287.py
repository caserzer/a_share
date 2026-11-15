from common import *
import pandas as pd

def keys(d):return set(map(tuple,d[KEY+['date']].to_numpy()))
def run():
    out=ROOT/'outputs/r287';o=pd.read_parquet(out/'origins.parquet');a=pd.read_parquet(out/'alerts.parquet');h=pd.read_parquet(out/'first_alerts.parquet')
    s=pd.read_parquet(ROOT/'outputs/r286/scores.parquet');s=s[s.eligible]
    e=pd.read_parquet(ROOT/'outputs/r242/episodes.parquet');seg=pd.read_parquet(ROOT/'outputs/r242/segments.parquet')
    cal=pd.DatetimeIndex(pd.read_parquet(CACHE/'forecast_v5/CSI_ALL.parquet').index);day={d:i for i,d in enumerate(cal)}
    segments={k:list(g.itertuples()) for k,g in seg.groupby(KEY)}
    episodes={k:list(g.sort_values('breach_i').itertuples()) for k,g in e[~e.left_boundary].groupby(KEY+['segment'])}
    assert keys(o)==keys(s[s.variant.eq('base')]) and not o.duplicated(KEY+['date']).any()
    for r in o.itertuples():
        key=(r.era,r.level,r.industry_code);z=[v for v in segments[key] if v.start_i<=r.day_i<=v.end_i];assert len(z)==1 and z[0].segment==r.segment
        valid=(r.day_i+21<=z[0].end_i and day.get(r.entry_date)==r.day_i+1 and day.get(r.maturity20)==r.day_i+21 and pd.notna(r.y))
        assert valid==r.complete_path
        candidates=[v for v in episodes.get(key+(r.segment,),[]) if r.day_i+2<=v.breach_i<=r.day_i+21] if valid else []
        if candidates:assert candidates[0].episode_id==r.episode_id and candidates[0].breach_i-r.day_i==r.signal_lead
        else:assert pd.isna(r.episode_id) and pd.isna(r.signal_lead)
    monthlast={}
    for d in cal:
        if d.to_period('M').end_time.normalize()<=cal.max():monthlast[d.to_period('M')]=d
    for variant,g in s.groupby('variant'):
        chosen=[]
        for _,group in g.groupby(['era','level','date']):chosen.extend(group.sort_values(['score','industry_code'],ascending=[False,True]).index[:int(np.ceil(len(group)/5))])
        raw=g.loc[chosen];assert keys(raw)==keys(a[a.variant.eq(variant)&a.strategy.eq('daily')])
        monthly=raw[raw.date.isin(monthlast.values())];assert keys(monthly)==keys(a[a.variant.eq(variant)&a.strategy.eq('monthly')])
        keep=[]
        for _,group in raw.groupby(KEY):
            last=-10**9
            for r in group.sort_values('date').itertuples():
                if r.day_i-last>20:keep.append(r.Index);last=r.day_i
        assert keys(raw.loc[keep])==keys(a[a.variant.eq(variant)&a.strategy.eq('daily_cooldown20')])
    joined=a.merge(o[KEY+['date','complete_path','episode_id','signal_lead']],on=KEY+['date'],suffixes=('','_check'),validate='many_to_one')
    for c in ['complete_path','episode_id','signal_lead']:np.testing.assert_equal(joined[c].to_numpy(),joined[c+'_check'].to_numpy())
    expected=a[a.episode_id.notna()].groupby(['era','level','variant','strategy','episode_id']).date.min()
    actual=h.set_index(['era','level','variant','strategy','episode_id']).date
    pd.testing.assert_series_equal(expected.sort_index(),actual.sort_index())
    metrics=pd.read_csv(out/'metrics.csv')
    for r in metrics.itertuples():
        g=a[a.era.eq(r.era)&a.level.eq(r.level)&a.variant.eq(r.variant)&a.strategy.eq(r.strategy)];orig=o[o.era.eq(r.era)&o.level.eq(r.level)]
        assert len(g)==r.alerts and orig.episode_id.nunique()==r.observable_episodes and g.episode_id.nunique()==r.detected_episodes
        assert g.complete_path.sum()==r.known_alerts and (~g.complete_path).sum()==r.unknown_alerts
        assert g.episode_id.notna().sum()-g.episode_id.nunique()==r.duplicate_episode_alerts
        assert (g.complete_path&g.episode_id.isna()).sum()==r.unmatched_known_alerts
        assert np.isclose(g[g.complete_path].y.mean(),r.fixed_label_precision)
        assert np.isclose(r.detected_episodes/r.observable_episodes,r.recall)
    for r in pd.read_csv(out/'comparisons.csv').itertuples():
        g=h[h.era.eq(r.era)&h.level.eq(r.level)&h.strategy.eq(r.strategy)];base=g[g.variant.eq('base')].set_index('episode_id');other=g[g.variant.eq(r.variant)].set_index('episode_id');common=base.index.intersection(other.index)
        delta=other.loc[common,'signal_lead']-base.loc[common,'signal_lead']
        assert len(delta)==r.joint_events and (delta>0).sum()==r.earlier and (delta==0).sum()==r.same and (delta<0).sum()==r.later
        assert np.isclose(delta.mean(),r.mean_paired_lead,equal_nan=True) and np.isclose(delta.median(),r.median_paired_lead,equal_nan=True)
        m=metrics[metrics.era.eq(r.era)&metrics.level.eq(r.level)&metrics.strategy.eq(r.strategy)].set_index('variant')
        assert np.isclose(m.loc[r.variant,'recall']-m.loc['base','recall'],r.recall_delta)
        assert m.loc[r.variant,'alerts']-m.loc['base','alerts']==r.alert_delta
    rec=json.loads((out/'receipt.json').read_text())
    for p,v in rec['inputs'].items():assert sha(ROOT/p)==v
    for p,v in rec['outputs'].items():assert sha(out/p)==v
    assert sha(CACHE/'forecast_v5/CSI_ALL.parquet')==rec['benchmark_sha256']
    js(out/'independent_verification.json',dict(status='PASS',origin_matches=len(o),alert_rows=len(a),metrics=len(metrics),paired_comparisons=24,scope='Source episode matching and path coverage, independent selection/cooldown, unique first alerts, metrics and paired lead; catalogue retained from R242',verifier_sha256=sha(Path(__file__))))
    print('R287 VERIFIED',len(o),len(a),len(metrics))
if __name__=='__main__':run()
