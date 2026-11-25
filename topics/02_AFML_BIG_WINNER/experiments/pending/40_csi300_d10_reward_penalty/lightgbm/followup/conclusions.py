from accounts_followup import *
sys.path.insert(0,str(ROOT))
from summarize import read,save,interval
from attribution import original
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

def main():
    w=read('windows');o=original(w)
    scores=read('daily_scores')
    rr=w.query('h==10 and delay==0 and arm=="R"')
    add=read('market_challenge');early=read('earlier')
    Phase=[];risk=[];byyear=[];tail=[];money=[];fund=[];learning=[]
    mc=add.merge(rr,on=['scope','phase','entry_idx','mul'],suffixes=('','_r'),validate='m:1')
    e=early.merge(early[early.arm=='R'][['year','phase','entry_idx','net']].rename(columns={'net':'ref'}),on=['year','phase','entry_idx'])
    for (year,phase,arm),g in e.groupby(['year','phase','arm']):
        byyear.append(dict(year=year,phase=phase,arm=arm,n=len(g),bp=1e4*(g.net-g.ref).mean()))
    save('earlier_scores',byyear)
    ii=read('industry_trial').assign(arm='sector_swap',mul=1).merge(rr,on=['scope','phase','entry_idx','mul'],suffixes=('','_r'))
    for (scope,ph,a,mul),g in pd.concat([mc,ii]).groupby(['scope','phase','arm','mul']):
        x=(g.net-g.net_r)*1e4;lo,hi,_=interval(x,3)
        Phase.append(dict(scope=scope,phase=ph,arm=a,mul=mul,bp=x.mean(),lo=lo,hi=hi,wins=(x>0).sum(),n=len(x)))
    save('challenge_phase',Phase)
    base=read('stagger').query('netting')
    data=pd.concat([base,read('market_challenge_stagger'),read('industry_trial_stagger').assign(arm='sector_swap')])
    fig,axs=plt.subplots(2,1,figsize=(10,6),constrained_layout=True)
    for (scope,g),ax in zip(data.groupby('scope',sort=False),axs):
        nav=g.pivot(index='date',columns='arm',values='nav').sort_index()
        for a in ['T','B','X11','X1169']:
            ax.plot(nav.index,100*(nav[a]/nav.R-1),label={'X1169':'5 swaps, 69 features','X11':'5 swaps, 78 features','T':'Tree only','B':'Tree picks from Ridge top 2K'}[a],linewidth=1.4)
        ax.axhline(0,color='grey',linewidth=.7);ax.grid(alpha=.2)
        ax.set_title(f'{scope.capitalize()}  |  {nav.index[0].date()} to {nav.index[-1].date()}',loc='left')
        ax.set_ylabel('Relative wealth (%)')
        monthly=nav.groupby(nav.index.to_period('M')).last().pct_change()
        monthly.iloc[0]=nav.groupby(nav.index.to_period('M')).last().iloc[0]-1
        for a in nav:
            dif=monthly[a]-monthly.R
            common=dif.iloc[1:-1]*1e4;lo,hi,_=interval(common,3)
            rest=(1+monthly.drop(dif.nlargest(3).index)[[a,'R']]).prod().values
            risk.append(dict(scope=scope,arm=a,terminal=nav[a].iloc[-1],mdd=(nav[a]/nav[a].cummax().clip(lower=1)-1).min(),terminal_pp=100*(nav[a].iloc[-1]-nav.R.iloc[-1]),full_months=len(common),monthly_bp=common.mean(),lo=lo,hi=hi,excluding_best3_pp=100*(rest[0]-rest[1])))
        for a in ['R','X1169']:
            h=read(scope+'_'+a+'_funded_pnl')
            sums=h.groupby('instrument')[['gross','fee']].sum()*100
            sums['net']=sums.gross-sums.fee
            np.testing.assert_allclose(sums.net.sum(),100*(nav[a].iloc[-1]-1),atol=1e-8)
            fund.append(sums.reset_index().assign(scope=scope,arm=a))
    axs[0].legend(loc='best',fontsize=8,ncol=2)
    fig.savefig(DEST/'funded_relative_wealth.png',dpi=160)
    save('funded',risk);save('funded_pnl_per_100',pd.concat(fund))
    pos=original(read('positions'));maxerr=0
    folds=read('market_challenge_positions').query('arm=="X1169"')
    ref=pd.read_parquet(OUT/'rankings.parquet').query('arm=="baseline"')
    for scope,g in folds.groupby('scope'):
        r=pos[(pos.scope==scope)&(pos.arm=='R')]
        z=g.merge(r,on=['entry_idx','instrument'],how='outer',suffixes=('','_r'))
        for c in ['weight','gross','fee']:
            z[c+'_delta']=z[c].fillna(0)-z[c+'_r'].fillna(0)
        z['group']=np.select([z.target.eq(True)&z.target_r.eq(True),z.target.eq(True),z.target_r.eq(True)],['common','incoming','outgoing'],default='legacy')
        z=z.merge(ref[['entry_idx','instrument','decile']],on=['entry_idx','instrument'],how='left')
        z['bucket']=z.decile.fillna(0).astype(int)
        n=z.entry_idx.nunique()
        tail.append((z.groupby(['group','bucket'])[['gross_delta','fee_delta','weight_delta']].sum()/n).reset_index().assign(scope=scope))
        diff=z.groupby('entry_idx')[['gross_delta','fee_delta']].sum()
        target=mc.query('scope==@scope and arm=="X1169" and phase==0 and mul==1').set_index('entry_idx')
        maxerr=max(maxerr,(diff.gross_delta-diff.fee_delta-target.net+target.net_r).abs().max())
    assert maxerr<1e-9
    save('candidate_bridge',pd.concat(tail))
    learn=read('learning')
    day_to_scope=ref.groupby('signal_date').scope.first()
    for scope,dates in day_to_scope.groupby(day_to_scope):
        test=learn[learn['sample'].eq('test')&learn.date.isin(dates.index)].pivot(index='date',columns='trees',values='rankic')
        for name,x in [('20',test[20]),('80',test[80]),('80-20',test[80]-test[20])]:
            lo,hi,_=interval(x,3)
            learning.append(dict(scope=scope,trees=name,n=len(x),mean_rankic=x.mean(),lo=lo,hi=hi))
    save('learning_oos',learning)
    # Benchmark and per-account absolute profit are separate from the paired model comparisons.
    ed=read('wide/daily')
    bench=pd.read_parquet(TRACK/'results/index800.parquet');bench=bench.set_index(pd.to_datetime(bench.trade_date)).close
    ww=read('wide/windows')
    g=ed.groupby(['pool','size','scope','arm'])
    out=g.agg(start=('date','min'),end=('date','max'),nav=('nav','last')).reset_index()
    out['index800_return']=[bench.at[b]/bench.at[a]-1 if pool=='CSI800' else np.nan for pool,a,b in zip(out.pool,out.start,out.end)]
    save('wide/summary',out.merge(ww.groupby(['pool','size','scope','arm']).agg(n=('net','size'),net_bp=('net',lambda x:x.mean()*1e4)).reset_index()))
if __name__=='__main__':main()
