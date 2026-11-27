from fund_panel import *
def transform(z):
    z=z.copy();g=z.groupby(['signal_date','industry']);gd=z.groupby('signal_date')
    count=g[A].transform('count');r=(g[A].rank()/(count+1)-.5).where(count>=10)
    for a in A:
        z['n_'+a]=r[a].where(~z.industry.isin(['未知','冲突']))
        z['raw_'+a]=gd[a].rank()/(gd[a].transform('count')+1)-.5
    return z
def main():
    p=pd.read_parquet(F/'panel.parquet')
    w=pd.read_parquet(LOCAL/'wide_features.parquet',columns=KEY[:2]+['weekly_ok'])
    w=w[w.weekly_ok];s=frozen(True)
    for k,d in [('training',w),('scoring',s)]:
        v=d[KEY[:2]].merge(p,on=KEY[:2],validate='1:1')
        transform(v).to_parquet(F/(k+'_panel.parquet'),index=False)
    audit=w[KEY[:2]].merge(s[KEY[:2]],on=KEY[:2],how='outer',indicator=True)
    audit.groupby(['signal_date','_merge'],observed=True).size().unstack(fill_value=0).to_csv(F/'universe_audit.csv')
if __name__=='__main__':main()
