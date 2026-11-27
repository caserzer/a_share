from fund_fit import *
def main():
    z=frozen(True);pp=pd.read_parquet(F/'scoring_panel.parquet',columns=KEY[:2]+N+['industry']);frames=[]
    for q in pd.period_range('2021Q1','2026Q3',freq='Q'):
        ref=z[z.signal_date.dt.to_period('Q')==q]
        f=read_features(q,True).merge(ref[KEY+['refit_R']],on=KEY,validate='1:1').rename(columns={'refit_R':'R'}).merge(pp,on=KEY[:2],validate='1:1')
        for date,g in f.groupby('signal_date'):
            for a,v in zip(A,N):
                obs=g[g[v].notna()];groups=obs.industry
                x=obs[COL+['R']];y=pd.DataFrame(np.broadcast_to(obs[v].to_numpy()[:,None],x.shape),index=x.index,columns=x.columns).where(x.notna())
                x=x.groupby(groups).rank();y=y.groupby(groups).rank()
                xx=x-x.groupby(groups).transform('mean');yy=y-y.groupby(groups).transform('mean')
                xy=(xx*yy).groupby(groups).sum()
                norm=((xx*xx).groupby(groups).sum()*(yy*yy).groupby(groups).sum())**.5
                corr=(xy/norm.where(norm>0)).astype('float32').reset_index().assign(date=date,anchor=a)
                frames.append(corr)
    df=pd.concat(frames,ignore_index=True)
    df.to_parquet(F/'F3_sector_all_features.parquet',index=False)
    g=df.groupby(['anchor','industry',df.date.dt.year])[COL+['R']]
    pd.concat([g.median(),g.min(),g.max()],keys=['median','min','max']).to_parquet(F/'F3_sector_year_extrema.parquet')
if __name__=='__main__':main()
