import sys,json
from pathlib import Path
import numpy as np
import pandas as pd
EP=Path(__file__).resolve().parents[2];sys.path.insert(0,str(EP/'src'))
from pool_evaluation import KEY,ID,HORIZONS,calendar_dates,sha,block_ci
from probability_pool import block_interval
OUT=EP/'restart/p01';CACHE=Path('/home/xiaolv/.cache/a_share/ep32/forecast_v5')

def features(g,m):
    g=g.sort_values('date').copy();assert g.day_i.diff().dropna().eq(1).all()
    logp=np.log(g.nav);x=logp-np.log(m.reindex(g.date).to_numpy());ret=logp.diff()
    g['rel21']=x-x.shift(21);g['rel63']=x-x.shift(63);g['abs63']=logp-logp.shift(63)
    g['eff63']=g.abs63/ret.abs().rolling(63).sum();g['risk63']=ret.rolling(63).std()
    return g

def bins(g,col,n):
    rank=g.sort_values([col,'industry_code']).groupby(lambda _:0).cumcount()
    return (rank*n/len(g)).astype(int).clip(upper=n-1).reindex(g.index)

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    d=pd.read_parquet(CACHE/'daily_industries.parquet');d=d[d.level.eq('L3')]
    m=pd.read_parquet(CACHE/'CSI_ALL.parquet').close.sort_index();dates=calendar_dates();chunks=[]
    for _,g in d.groupby(KEY):
        f=features(g,m);chunks.append(f[f.date.isin(dates)])
    p=pd.concat(chunks,ignore_index=True);p['eligible']=p.coverage.ge(.8)&p.members.ge(5)&p[['rel21','rel63','abs63','eff63','risk63']].notna().all(axis=1)
    for col in ['h1_pullback','h1_continuation','h2_smooth','h2_jumpy']:p[col]=False
    matches=[];coverage=[]
    for date,g in p[p.eligible].groupby('date'):
        a=g[g.rel63.gt(0)&g.abs63.gt(0)].copy();p.loc[a.index,'h1_pullback']=a.rel21.lt(0);p.loc[a.index,'h1_continuation']=a.rel21.ge(0)
        if len(a):
            a['cell']=bins(a,'rel63',5)*2+bins(a,'risk63',2)
            for cell,b in a.groupby('cell'):
                left=b[b.rel21.lt(0)];right=b[b.rel21.ge(0)]
                if min(len(left),len(right))>=3:
                    for arm,z in [('pullback',left),('continuation',right)]:
                        matches.extend(dict(hypothesis='H1',date=date,cell=int(cell),arm=arm,row_id=int(i)) for i in z.index)
        a=g[g.abs63.gt(0)].copy()
        if len(a):
            a['cell']=bins(a,'rel63',3)*6+bins(a,'abs63',3)*2+bins(a,'risk63',2)
            for cell,b in a.groupby('cell'):
                if len(b)<6:continue
                rank=b.sort_values(['eff63','industry_code']);k=len(b)//3
                left=rank.tail(k);right=rank.head(k)
                p.loc[left.index,'h2_smooth']=True;p.loc[right.index,'h2_jumpy']=True
                for arm,z in [('smooth',left),('jumpy',right)]:matches.extend(dict(hypothesis='H2',date=date,cell=int(cell),arm=arm,row_id=int(i)) for i in z.index)
        coverage.append(dict(date=date,eligible=len(g),h1=int(p.loc[g.index,['h1_pullback','h1_continuation']].any(axis=1).sum()),h2=int(p.loc[g.index,['h2_smooth','h2_jumpy']].any(axis=1).sum())))
    p.to_parquet(OUT/'feature_panel.parquet',index=True);pairs=pd.DataFrame(matches);pairs.to_csv(OUT/'matched_members.csv.gz',index=False);pd.DataFrame(coverage).to_csv(OUT/'coverage.csv',index=False)
    (OUT/'feature_seal.json').write_text(json.dumps({'stage':'FEATURES_AND_MEMBERS_FIXED_BEFORE_OUTCOME_JOIN','inputs':{str(f):sha(f) for f in [CACHE/'daily_industries.parquet',CACHE/'CSI_ALL.parquet',Path(__file__),EP/'restart/P01_price_information_plan.md']},'features_sha256':sha(OUT/'feature_panel.parquet'),'members_sha256':sha(OUT/'matched_members.csv.gz')},indent=2)+'\n')
    labels=pd.read_parquet(EP/'outputs/r09/evaluation_panel.parquet')
    p=p.merge(labels[ID+[f'{x}{h}' for h in HORIZONS for x in ['win','status']]],on=ID,how='left',validate='one_to_one')
    summaries=[];annual=[];selections=[]
    for method in ['h1_pullback','h1_continuation','h2_smooth','h2_jumpy']:
        q=p.sort_values(KEY+['date']);prior=q.groupby(KEY)[method].shift();cont=q.week_i.diff() if 'week_i' in q else None
        weekmap={dt:i for i,dt in enumerate(dates)};q['week']=q.date.map(weekmap)
        contiguous=q.week.sub(q.groupby(KEY).week.shift()).eq(1)
        for unit,mask in [('state',q[method]),('entry',q[method]&prior.eq(False)&contiguous)]:
            z=q[mask];counts=z.groupby('date').size();base=p[p.eligible&p.date.isin(counts.index)]
            ranked=base.sort_values(['date','rel63','industry_code'],ascending=[True,False,True]);mom=ranked[ranked.groupby('date').cumcount().lt(ranked.date.map(counts))]
            selections.extend(dict(method=method,unit=unit,row_id=int(i)) for i in z.index)
            for h in HORIZONS:
                col=f'win{h}';known=z[z[col].notna()].copy();ref=base.groupby('date')[col].mean();known['delta']=known[col]-known.date.map(ref)
                lo,hi=block_interval(known,dates,26 if h==126 else round(h/5));mr=mom.groupby('date')[col].mean()
                summaries.append(dict(method=method,unit=unit,horizon=h,total=len(z),known=len(known),wins=known[col].sum(),win_rate=known[col].mean(),uplift=known.delta.mean(),lo=lo,hi=hi,momentum_delta=(known[col]-known.date.map(mr)).mean(),unknown=len(z)-len(known),
                    success_week_coverage=z[col].sum()/p.loc[p.eligible,col].sum() if unit=='state' else np.nan,mean_pool=len(z)/len(dates),median_prior63=z.abs63.median()))
                for year,b in known.groupby(known.date.dt.year):annual.append(dict(method=method,unit=unit,horizon=h,year=int(year),known=len(b),win_rate=b[col].mean(),uplift=b.delta.mean()))
    pd.DataFrame(summaries).to_csv(OUT/'summary.csv',index=False);pd.DataFrame(annual).to_csv(OUT/'annual.csv',index=False);pd.DataFrame(selections).to_csv(OUT/'selected.csv.gz',index=False)
    paired=pairs.merge(p.reset_index(names='row_id'),on=['row_id','date'],validate='many_to_one');pairresults=[];balances=[]
    for hypothesis,g in paired.groupby('hypothesis'):
        left,right=('pullback','continuation') if hypothesis=='H1' else ('smooth','jumpy')
        for col in ['rel21','rel63','abs63','risk63','eff63']:
            b=g.groupby(['date','cell','arm'])[col].mean().unstack('arm');balances.append(dict(hypothesis=hypothesis,feature=col,mean_cell_difference=(b[left]-b[right]).mean()))
        for h in HORIZONS:
            t=g.groupby(['date','cell','arm'])[f'win{h}'].mean().unstack('arm');t['delta']=t[left]-t[right];series=t.delta.groupby('date').mean().reindex(dates);lo,hi=block_ci(series,26 if h==126 else round(h/5))
            pairresults.append(dict(hypothesis=hypothesis,horizon=h,matched_dates=series.notna().sum(),mean_date_cell_delta=series.mean(),lo=lo,hi=hi))
            series.rename('delta').to_csv(OUT/f'{hypothesis}_{h}_date_pairs.csv')
    pd.DataFrame(pairresults).to_csv(OUT/'matched_summary.csv',index=False);pd.DataFrame(balances).to_csv(OUT/'matching_balance.csv',index=False)
    p.to_parquet(OUT/'evaluated_panel.parquet',index=False)
    print(pd.DataFrame(summaries).query('horizon==126').to_string(index=False));print(pd.DataFrame(pairresults).to_string(index=False))
if __name__=='__main__':main()
