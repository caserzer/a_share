"""Registered contrasts and held-state diagnostics for S1–S5 and G2–G3."""
from scale_common import *
sys.path.insert(0,str(EP42/'state'))
import core42 as core

PAIRS={'S2':[('S2_A','S2_C'),('S2_A','S2_B'),('S2_B','S2_C'),('S2_D','S2_A'),('S2_D','S2_B'),('S2_A_commonmask','S2_B_commonmask'),('S2_D_commonmask','S2_B_commonmask'),('S2_A_commonmask','S2_C_commonmask'),('S2_B_commonmask','S2_C_commonmask'),('S2_D_commonmask','S2_A_commonmask')], 'S3':[('vol_live','vol_fixed'),('vol_loc','vol_fixed'),('vol_width','vol_fixed'),('vol_live','vol_loc'),('vol_live','vol_width')],'S4':[('vol_live','vol_lag20'),('vol_live','vol_fixed'),('vol_live_supported','vol_lag20_supported'),('vol_live_supported','vol_fixed_supported')],'S5':[('paired_live','paired_fixed'),('paired_live_invested','paired_fixed_invested'),('sector_live','sector_fixed'),('vol_live','vol_fixed')],'G2':[('mse69','ridge69'),('S2_A','mse69'),('mse78','ridge78'),('original78tree','mse78'),('mse78','mse69'),('ridge78','ridge69'),('early','mse69'),('shallow','mse69'),('shallow_early','mse69'),('shallow_early','R')],'G3':[('G3_interaction','G3_main'),('G3_main','R'),('G3_interaction','R')]}

def summary():
    m=pd.read_csv(RES/'months.csv')
    m['turnover']=m.buy+m.sell
    comp=[]
    for tag,pairs in PAIRS.items():
        for a,b in pairs:
            for mul in [1,2]:
                g=core.contrast(m[m.fee_multiple.eq(mul)],a,b)
                comp.append(g.assign(id=tag,fee_multiple=mul))
    ct=pd.concat(comp,ignore_index=True)
    ct.to_csv(RES/'comparisons.csv',index=False)
    mm=m[m.fee_multiple.eq(1)].pivot(index=['segment','month'],columns='arm',values='net')*1e4
    loc=(mm.vol_loc-mm.vol_fixed+mm.vol_live-mm.vol_width)/2
    scale=(mm.vol_width-mm.vol_fixed+mm.vol_live-mm.vol_loc)/2
    both=mm.vol_live-mm.vol_loc-mm.vol_width+mm.vol_fixed
    np.testing.assert_allclose(loc+scale,mm.vol_live-mm.vol_fixed,atol=1e-12)
    pd.DataFrame({'level':loc,'spread':scale,'interaction':both,'joint':loc+scale}).to_csv(RES/'S3_four_cells.csv')
    placebo=[]
    for suffix in ['','_supported']:
        for j in range(1,21):
            x=mm['vol_live'+suffix]-mm[f'vol_block{j:02d}'+suffix]
            for seg,g in x.groupby(level=0):placebo.append((suffix or 'full',j,seg,g.mean()))
    pd.DataFrame(placebo,columns='universe seed segment net_bp'.split()).to_csv(RES/'S4_placebo_spread.csv',index=False)
    branch=pd.read_parquet(RES/'S1_daily.parquet')
    state=pd.read_parquet(EP42/'state/results/states.parquet').set_index('signal_date').Z1
    branch['segment']=np.where(branch.signal_date<'2025-03-03','primary','later')
    design=[]
    for (seg,cohort,path),g in branch.dropna(subset=['Z1']).groupby(['segment','cohort','path']):
        x=g.Z1-g.groupby('fold').Z1.transform('mean')
        y=g.structure-g.groupby('fold').structure.transform('mean')
        monthly=pd.DataFrame({'xx':x*x,'xy':x*y,'date':g.signal_date}).groupby(g.signal_date.dt.to_period('M'))[['xx','xy']].sum()
        rng=np.random.default_rng(4201);n=len(monthly)
        draw=(rng.integers(0,n-2,(10000,(n+2)//3))[:,:,None]+np.arange(3)).reshape(10000,-1)[:,:n]
        vals=monthly.to_numpy()[draw].sum(axis=1);bs=vals[:,1]/vals[:,0]
        design.append((seg,cohort,path,len(g),y.dot(x)/x.dot(x),*np.percentile(bs,[2.5,97.5]),g.transitions.sum()/g.same_parent.sum(),g.structure.mean()))
    pd.DataFrame(design,columns='segment cohort path dates slope lo hi switch_rate mean_structure'.split()).to_csv(RES/'S1_structure.csv',index=False)
    periods=pd.read_parquet(RES/'common_h10.parquet');periods=pd.concat([periods,periods[periods.arm.eq('ridge78')].assign(arm='R')],ignore_index=True);periods['Z1']=periods.signal_date.map(state)
    periods['state']=np.select([periods.Z1.lt(1/3),periods.Z1.gt(2/3),periods.Z1.notna()],['low','high','mid'],default='unknown')
    periods['month']=periods.signal_date.dt.to_period('M')
    g2pairs=[('mse69','ridge69'),('mse78','ridge78'),('S2_A','R'),('original78tree','R'),('S2_A','mse69'),('original78tree','mse78'),('ridge78','ridge69'),('mse78','mse69'),('early','mse69'),('shallow','mse69'),('shallow_early','mse69'),('G3_interaction','G3_main'),('vol_live','vol_fixed'),('vol_live','vol_lag20'),('sector_live','sector_fixed'),('paired_live','paired_fixed')]
    gd=[];stats=[];byoffset=[]
    for arm,base in g2pairs:
        u=periods[periods.arm.eq(arm)].merge(periods[periods.arm.eq(base)],on=['segment','signal_date','month','state','offset'],validate='1:1',suffixes=('','_base'))
        u['diff_net']=u.net-u.net_base;u['diff_gross']=u.gross-u.gross_base;u['diff_fee']=u.fee-u.fee_base
        for (sg,s),g in u.groupby(['segment','state']):
            gd.append((arm,base,sg,s,len(g),g.month.nunique(),g.diff_net.mean()*1e4,g.diff_gross.mean()*1e4,g.diff_fee.mean()*1e4))
            for off,gg in g.groupby('offset'):byoffset.append((arm,base,sg,s,off,len(gg),gg.diff_net.mean()*1e4))
        for seg,g in u.groupby('segment'):
            data=[]
            for month,part in g.groupby('month'):
                h=part.loc[part.state=='high','diff_net'].dropna();l=part.loc[part.state=='low','diff_net'].dropna()
                data.append([h.sum(),len(h),l.sum(),len(l)])
            v=np.asarray(data);n=len(v);rng=np.random.default_rng(4201)
            draw=(rng.integers(0,n-2,(10000,(n+2)//3))[:,:,None]+np.arange(3)).reshape(10000,-1)[:,:n]
            b=v[draw].sum(axis=1)
            def calc(b):return ((b[...,0]/b[...,1])-(b[...,2]/b[...,3]))*1e4
            valid=(b[:,1]>0)&(b[:,3]>0)
            stats.append((arm,base,seg,calc(v.sum(axis=0)),*np.quantile(calc(b[valid]),[.025,.975]),valid.sum(),v.sum(axis=0)[1],v.sum(axis=0)[3]))
    pd.DataFrame(gd,columns='arm base segment state signals months net_bp_h10 gross_bp_h10 fee_bp_h10'.split()).to_csv(RES/'state_conditional.csv',index=False)
    pd.DataFrame(byoffset,columns='arm base segment state offset signals net_bp_h10'.split()).to_csv(RES/'state_offsets.csv',index=False)
    pd.DataFrame(stats,columns='arm base segment high_minus_low_bp_h10 lo hi identifiable_draws high_dates low_dates'.split()).to_csv(RES/'state_spreads.csv',index=False)
    targets=pd.read_parquet(RES/'target_lists.parquet')
    dates=targets[['signal_date','arm','instruments','denominator']]
    changes=[]
    for tag,pairs in PAIRS.items():
        for arm,base in pairs:
            x=dates[dates.arm.eq(arm)].merge(dates[dates.arm.eq(base)],on='signal_date',suffixes=('','_base'),validate='1:1')
            for row in x.itertuples():
                h,t=set(row.instruments),set(row.instruments_base)
                changes.append((tag,arm,base,row.signal_date,len(h),len(t),len(h&t),row.denominator,row.denominator_base))
    atomic_parquet(pd.DataFrame(changes,columns='id arm base signal_date seats base_seats shared denominator base_denominator'.split()),RES/'decision_changes.parquet')
    oc=pd.read_parquet(RES/'cohort_pnl.parquet')
    oc['state']=np.select([oc.Z1.lt(1/3),oc.Z1.gt(2/3),oc.Z1.notna()],['low','high','mid'],default='unknown')
    oc['net']=oc.overnight+oc.intraday-oc.fee
    oc.groupby(['arm','segment','state'])[['overnight','intraday','fee','net','gross_buy_flow','ticket_target']].sum().to_csv(RES/'state_funded.csv')
if __name__=='__main__':summary()
