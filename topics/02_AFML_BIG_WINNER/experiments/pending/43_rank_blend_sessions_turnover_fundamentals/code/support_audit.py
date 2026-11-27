from fund_fit import *
def main():
    m=book(True);tables=[]
    memb=m.members.astype(bool);new=memb & ~np.vstack([memb[0],memb[:-1]])
    last=np.full(m.n,-100000);recent=np.zeros_like(memb)
    for i in range(len(m.days)):
        last[new[i]]=i;recent[i]=(i-last<=20)
    for name,path in [('proxy',F/'scoring_panel.parquet'),('original',F/'strict/qualified_panel.parquet')]:
        p=pd.read_parquet(path,columns=KEY[:2]+A+N+['industry'])
        for col in A+N:p[col]=p[col].notna().astype(float)
        p['joint_raw']=p[A].min(axis=1);p['joint_neutral']=p[N].min(axis=1);cols=A+N+['joint_raw','joint_neutral']
        for sg,span in enumerate(SEG800,1):
            tr=pd.read_parquet(O/f'accounts/800/W/R/{sg}/transactions.parquet')
            tr=tr[(tr.target>0)|(tr.flow>0)].copy();tr['buy_capital']=tr.flow.clip(lower=0);tr['instrument']=m.symbols[tr.stock];tr['signal_date']=m.days[tr.day-1]
            tr=tr.merge(p,on=KEY[:2],how='left',validate='m:1');tr['recent_member']=recent[tr.day-1,tr.stock];tr['in_endpoint_index']=memb[m.days.get_loc('2026-10-12'),tr.stock]
            tr['finance']=tr.industry.str.contains('银行|非银',na=False)
            tr['year']=tr.signal_date.dt.year
            for (year,fin,joined,ending),sub in tr.groupby(['year','finance','recent_member','in_endpoint_index']):
                for col in cols:
                    tables.append((name,sg,year,fin,joined,ending,col,len(sub),sub.target.sum(),(sub.target*sub[col]).sum(),sub.buy_capital.sum(),(sub.buy_capital*sub[col]).sum()))
    pd.DataFrame(tables,columns='source segment year financial recent_member20 member_at_endpoint anchor stocks_sleeves target_capital target_covered buy_capital buy_covered'.split()).to_csv(F/'F2_funded_support.csv',index=False)
if __name__=='__main__':main()
