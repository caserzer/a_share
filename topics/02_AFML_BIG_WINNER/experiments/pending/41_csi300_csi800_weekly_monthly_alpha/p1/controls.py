from summarize import *
def main():
    cal=pd.read_parquet(LOCAL/'open.parquet',columns=[]).index
    m=pd.read_parquet(RESULT/'months.parquet').query('model=="refit" and bucket=="head" and kind=="strict" and phase==-1').set_index(['segment','month']).net
    d=pd.read_parquet(RESULT/'matched_daily.parquet')
    z=grouped(d,['segment','caliper','bucket'],cal).set_index(['caliper','bucket','segment','month'])
    det=[]
    for tol in [.1,.2]:
        for common in ['matched','shared','wide_only']:
            if (tol,common+'_head') not in z.index.droplevel(['segment','month']):continue
            pair=z.loc[tol,common+'_head']-z.loc[tol,common+'_runner']
            det.append(stats(pair.reset_index()).assign(caliper=tol,support=common))
    pd.concat(det).to_csv(RESULT/'matched_summary.csv',index=False)
    randoms=[]
    for tag in ['uniform','matched']:
        d=pd.read_parquet(RESULT/(tag+'_paths.parquet'))
        d['month']=d.date.dt.to_period('M').astype(str)
        keys=['seed','segment'];group=d.groupby(keys,sort=False)
        d['prior']=group.nav.shift().fillna(1)
        a=d.groupby(keys+['month']).agg(start=('date','min'),end=('date','max'),base=('prior','first'),nav=('nav','last'))
        y=pd.Series(cal,index=cal).groupby(cal.to_period('M').astype(str)).agg(['min','max'])
        a=a.join(y,on='month').query('start==min and end==max').reset_index()
        a['net']=a.nav/a.base-1
        if tag=='uniform':
            q=a.join(m.rename('head_net'),on=['segment','month'],how='inner')
        else:
            h=pd.read_parquet(RESULT/'matched_head_paths.parquet')
            h['month']=h.date.dt.to_period('M').astype(str)
            h['prior']=h.groupby(keys).nav.shift().fillna(1)
            hh=h.groupby(keys+['month']).agg(base=('prior','first'),last=('nav','last'),hstart=('date','first'),hend=('date','last'))
            hh['head_net']=hh['last']/hh.base-1
            q=a.join(hh[['head_net','hstart','hend']],on=keys+['month'],how='inner')
            q=q[q.start.eq(q.hstart)&q.end.eq(q.hend)]
        q['gap']=q.head_net-q.net
        q.to_parquet(RESULT/(tag+'_paired_months.parquet'),index=False)
        for (s,seg),g in q.groupby(['seed','segment']):
            randoms.append(dict(control=tag,seed=s,segment=seg,months=len(g),bp=g.gap.mean()*1e4))
    pd.DataFrame(randoms).to_csv(RESULT/'random_summary.csv',index=False)

if __name__=='__main__':main()
