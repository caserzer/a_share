from fund_fit import *
from score_audit import labels_daily
def run():
    panel=pd.read_parquet(F/'scoring_panel.parquet')
    outer=pd.concat(pd.read_parquet(p) for p in sorted(F.glob('scores_*.parquet'))).reset_index(drop=True)
    panel=outer[KEY+['R']].merge(panel,on=KEY[:2],validate='1:1')
    cols=A+N;groups=[]
    from scipy.stats import spearmanr
    for date,g in panel.groupby('signal_date'):
        flags=g[cols].notna();flags['joint_raw']=flags[A].all(axis=1);flags['joint_neutral']=flags[N].all(axis=1)
        k=len(g)//10;head=g.R.nlargest(k).index
        for field in flags.columns:
            groups.append((date,field,len(g),flags[field].sum(),len(head),flags.loc[head,field].sum(),g.stale.sum()))
    cov=pd.DataFrame(groups,columns='date field rows valid top valid_top stale'.split());cov.to_parquet(F/'F2_daily.parquet',index=False)
    for col in cols:
        panel['v_'+col]=panel[col].notna().astype(int)
    panel['v_joint']=panel[N].notna().all(axis=1).astype(int)
    vcols=['v_'+c for c in cols]+['v_joint'];pd.concat([panel.groupby(['industry',panel.signal_date.dt.year])[vcols].sum(),panel.groupby(['industry',panel.signal_date.dt.year]).size().rename('N')],axis=1).to_csv(F/'F2_industry_year.csv')
    label=labels_daily(outer[KEY].copy(),True)
    rows=[];cross=[];ref=frozen(True)
    for q,g in panel.groupby(panel.signal_date.dt.to_period('Q')):
        x=read_features(q,True).merge(g[KEY],on=KEY,validate='1:1')
        x,_=enhance(x,panel,ref=None);x=x.merge(label[KEY+['IV']],on=KEY,validate='1:1')
        for date,z in x.groupby('signal_date'):
            for a,n,h,v,r in zip(A,N,H,V,D):
                good=z[h]==0;zz=z.loc[good,[n,r,'IV']].dropna()
                # Exclude rows without a valid residual (neutral zero was used only for model inputs).
                d=zz[r].replace(0,np.nan);s=zz[n]
                if len(zz)>3:
                    raw=z[v].where(z[v]!=0);y=z.IV
                    vals=[raw.corr(y,method='spearman'),s.corr(zz.IV,method='spearman'),d.corr(zz.IV,method='spearman')]
                    head=d.dropna().nlargest(max(1,d.count()//10)).index
                    rows.append((date,a,len(z),len(zz),d.count(),*vals,zz.loc[head,'IV'].mean()-zz.IV.mean()))
    pd.DataFrame(rows,columns='date anchor names industry_valid residual_valid raw_IC neutral_IC residual_IC residual_head_excess_logH10'.split()).to_parquet(F/'F3_information.parquet',index=False)
    corr=pd.concat(pd.read_parquet(p) for p in F.glob('corr_*.parquet'));mean=corr.groupby('anchor')[COL+['R']].mean()
    mean.to_csv(F/'F3_price_corr.csv')
    groups=[]
    for name,g in corr.groupby(['anchor',corr.date.dt.year]):
        v=g[COL].mean().dropna()
        groups.append((*name,v.abs().idxmax(),v.abs().max(),g.R.mean(),g.pos60.mean(),g.dd60.mean()))
    pd.DataFrame(groups,columns='anchor year most_correlated abs_mean corr_R corr_pos60 corr_dd60'.split()).to_csv(F/'F3_by_year.csv',index=False)
if __name__=='__main__':run()
