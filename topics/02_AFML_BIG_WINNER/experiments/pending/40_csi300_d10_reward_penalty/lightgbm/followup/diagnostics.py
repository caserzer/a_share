"""Coverage and identification details for the registered portfolio and feature comparisons."""
from accounts_followup import *
sys.path.insert(0,str(ROOT))
from summarize import read,save
from attribution import original

def main():
    ref=pd.read_parquet(OUT/'rankings.parquet').query('arm=="baseline"')
    s=read('daily_scores').merge(ref[KEY+['h10','decile','scope']],on=KEY,validate='1:1')
    s=s.sort_values(['signal_date','R','instrument'],ascending=[True,False,False])
    s['R_rank']=s.groupby('signal_date').cumcount()+1;s['K']=s.groupby('signal_date').R.transform('size')//10
    s['R_tier']=np.select([s.R_rank<=s.K,s.R_rank<=2*s.K],['top_K','second_K'],default='outside_2K')
    ind=industries(s.signal_date.unique())
    s['industry']=pd.concat([g.instrument.map(ind[dt]) for dt,g in s.groupby('signal_date')]).fillna('未知')
    p=original(read('positions'))
    main=p[p.arm=='T'].merge(s[['entry_idx','instrument','R_tier','industry','h10']],on=['entry_idx','instrument'],how='left')
    main[['R_tier','industry']]=main[['R_tier','industry']].fillna({'R_tier':'legacy','industry':'未知'})
    tiers=main.groupby(['scope','R_tier','industry']).agg(held_windows=('entry_idx','nunique'),target_seats=('target','sum'),capital=('weight','sum'),gross=('gross','sum'),fee=('fee','sum')).reset_index()
    n=main.groupby('scope').entry_idx.nunique()
    tiers['weight']=tiers.capital/tiers.scope.map(n);tiers['net_bp']=(tiers.gross-tiers.fee)*1e4/tiers.scope.map(n)
    save('tree_tier_industry',tiers)
    z=p.merge(s[['entry_idx','instrument','h10','decile','mom5','vol20']],on=['entry_idx','instrument'],how='left')
    rows=[]
    for (scope,a),g in z.groupby(['scope','arm']):
        t=g[g.target]
        rows.append(dict(scope=scope,arm=a,seats=len(t),label_known=t.h10.count(),known_weight=g.weight[g.h10.notna()].sum()/g.weight.sum(),V_fill=(t.vol20.isna()).sum() if a=='V' else None,J_fill=(t.mom5.isna()).sum() if a=='J' else None))
    save('selection_coverage',rows)
    win=original(read('windows'));dy=original(read('daily'));rows=[]
    for scope,g in dy[dy.arm=='R'].groupby('scope'):
        v=g.set_index('date').nav.sort_index()
        trough=(v/v.cummax().clip(lower=1)-1).idxmin();peak=v.loc[:trough].idxmax()
        panel=dy[dy.scope==scope].pivot(index='date',columns='arm',values='nav')
        rr=panel.loc[trough]/panel.loc[peak]-1
        for a in ['R','T','B','A','X11']:
            rows.append(dict(scope=scope,arm=a,R_peak=peak,R_trough=trough,net=rr[a],delta_vs_R=rr[a]-rr.R))
    save('baseline_drawdown_period',rows)
    windows=original(read('windows'))
    p0=read('placebo_windows');pics=read('placebo_ic')
    tab=p0.groupby(['scope','seed'])[['net','fee','turnover']].mean().join(pics.groupby(['scope','seed']).rankic.mean())
    save('placebos',tab.reset_index())
    # Inputs to the transfer are compared feature by feature including missing masks.
    loc=Path.home()/'.cache/a_share/ep38_three_track/market'
    within=outer()
    wide=pd.read_parquet(loc/'wide_features.parquet',filters=[('signal_date','in',list(within.signal_date.unique())),('outer_ok','=',True)])
    both=within[KEY+COLS].merge(wide[KEY+COLS],on=KEY,validate='1:1',suffixes=('','_wide'))
    for c in COLS:np.testing.assert_allclose(both[c],both[c+'_wide'],equal_nan=True,atol=1e-12,rtol=0)
    left=within.groupby('signal_date').instrument.nunique();right=wide.groupby('signal_date').instrument.nunique();common=both.groupby('signal_date').instrument.nunique()
    save('wide/overlap',pd.concat([left.rename('eligible300'),right.rename('eligible800'),common.rename('both')],axis=1).reset_index())
if __name__=='__main__':main()
