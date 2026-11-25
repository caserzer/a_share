from common_inputs import *
from scipy.stats import rankdata
def holm(p):
    ix=np.argsort(p);v=np.asarray(p)[ix]*np.arange(len(p),0,-1)
    return np.minimum(1,np.maximum.accumulate(v))[np.argsort(ix)]
from collections import defaultdict
KEYS='scope arm h phase delay mul'.split()

def read(name):return pd.read_parquet(DEST/(name+'.parquet'))
def save(name,rows):pd.DataFrame(rows).to_csv(DEST/(name+'.csv'),index=False)
def interval(a,k):
    a=np.asarray(a);n=len(a)
    start=np.random.default_rng(4001).integers(n,size=(10000,(n+k-1)//k,1))
    ix=((start+np.arange(k))%n).reshape(10000,-1)[:,:n]
    draws=a[ix].mean(axis=1)
    lo,hi=np.quantile(draws,[.025,.975])
    return lo,hi,min(1.,2*min((sum(draws-a.mean()>=a.mean())+1)/10001,(sum(draws-a.mean()<=a.mean())+1)/10001))
def main():
    days=pd.read_parquet(PRIVATE/'market.parquet',columns=[]).index
    record=json.loads((PRIVATE/'net_excess_20261116/H00300.CSI.json').read_text())['data']
    idx=pd.DataFrame(record['items'],columns=record['fields'])
    ix=idx.set_index(pd.to_datetime(idx.trade_date)).close.sort_index()
    windows=read('windows'); daily=read('daily')
    acc=[];months=[]
    for k,g in daily.groupby(KEYS):
        meta=dict(zip(KEYS,k));v=g.set_index('date').nav.sort_index()
        a,b=v.index[[0,-1]]
        n=days.get_loc(b)-days.get_loc(a);bench=ix.at[b]/ix.at[a]
        w=windows
        returns=v.groupby(v.index.to_period('M')).last().pct_change()
        returns.iloc[0]=v[v.index.to_period('M')==returns.index[0]].iloc[-1]-1
        for m,r in returns.items():
            complete=(days[days.to_period('M')==m][0]>=a and days[days.to_period('M')==m][-1]<=b and m!=returns.index[0])
            months.append(dict(**meta,month=str(m),net=r,complete=complete))
        acc.append(dict(**meta,start=a,end=b,nav=v.iloc[-1],cagr=v.iloc[-1]**(252/n)-1,mdd=(v/v.cummax().clip(lower=1)-1).min(),index_cagr=bench**(252/n)-1))
    acc=pd.DataFrame(acc).merge(windows.groupby(KEYS)[['net','fee','turnover']].mean().reset_index(),on=KEYS)
    save('accounts',acc);months=pd.DataFrame(months);months.to_parquet(DEST/'months.parquet',index=False)
    paired=[]
    for k,g in windows.groupby(['scope','h','phase','delay','mul']):
        meta=dict(zip(['scope','h','phase','delay','mul'],k))
        net=g.pivot(index='entry_idx',columns='arm',values='net');fee=g.pivot(index='entry_idx',columns='arm',values='fee')
        defs={a+'-R':{a:1,'R':-1} for a in net if a!='R' and not a.startswith('P')}
        for a,b in [('X10','X00'),('X01','X00'),('B','V'),('B','J'),('B','BI'),('B','BIV'),('T','TI'),('T','TIV'),('B','A'),('C','T'),('R','E'),('G2','G1'),('T','G2'),('F01','F00'),('T','F10'),('F10','F00'),('T','F01'),('T','T20')]+[(a,'U') for a in ['B','T','R']]+[('T',a) for a in ['no_dd','no_amp','no_path','leaf100','l2_5']]:
            defs[a+'-'+b]={a:1,b:-1}
        defs.update(Xinteraction={'X11':1,'X10':-1,'X01':-1,'X00':1},market_interaction={'T':1,'T69':-1,'R':-1,'R69':1},recipe_interaction={'T':1,'F10':-1,'F01':-1,'F00':1})
        for contrast,weights in defs.items():
            if not set(weights)<=set(net):continue
            d=sum(net[a]*z for a,z in weights.items())*1e4
            f=sum(fee[a]*z for a,z in weights.items())*1e4
            lo,hi,p=interval(d,3);l6,h6,_=interval(d,6)
            paired.append(dict(**meta,contrast=contrast,n=len(d),wins=sum(d>0),net_bp=d.mean(),fee_bp=f.mean(),gross_bp=(d+f).mean(),lo=lo,hi=hi,lo6=l6,hi6=h6,p=p))
    pairs=pd.DataFrame(paired)
    for _,g in pairs.groupby(['scope','h','phase','delay','mul']):
        for fam in [['X10-X00','X01-X00','Xinteraction'],['T-no_dd','T-no_amp','T-no_path']]:
            f=g[g.contrast.isin(fam)]
            if len(f)==3:pairs.loc[f.index,'holm']=holm(f.p)
    save('paired',pairs)
    complete=months.query('complete and mul==1 and delay==0')
    index_month=ix.groupby(ix.index.to_period('M')).last().pct_change()
    index_month.index=index_month.index.astype(str)
    concentration=[];risk=[];phase_ci=[]
    for scope in ['primary','later']:
        z=complete.query('scope==@scope and h==10').pivot(index='month',columns=['phase','arm'],values='net')
        for a in ['T','B','A','X11']:
            mat=pd.concat([z[p,a]-z[p,'R'] for p in range(10)],axis=1).dropna()
            diff=mat.mean(axis=1)*1e4
            lo,hi,_=interval(diff,3)
            phase_ci.append(dict(scope=scope,arm=a,months=len(diff),bp_month=diff.mean(),lo=lo,hi=hi))
            v=z[0][[a,'R']].dropna();market=index_month.loc[v.index]
            diff=v[a]-v.R
            def coef(y,x):return np.linalg.lstsq(np.column_stack([np.ones(len(x)),x]),y,rcond=None)[0]
            intercept,beta=coef(diff,market)
            active=v[a]-market
            risk.append(dict(scope=scope,arm=a,n=len(v),active_mean_annual=12*active.mean(),tracking_error=active.std()*np.sqrt(12),IR=active.mean()/active.std()*np.sqrt(12),monthly_intercept=intercept,beta=beta))
            allm=months.query('scope==@scope and h==10 and phase==0 and mul==1 and delay==0').pivot(index='month',columns='arm',values='net')
            order=(allm[a]-allm.R).sort_values(ascending=False).index
            for label,drop in [('best1',order[:1]),('best3',order[:3])]+[(y,allm.index[allm.index.str.startswith(y)]) for y in sorted(set(allm.index.str[:4]))]:
                rest=(1+allm.drop(drop)[[a,'R']]).prod()
                concentration.append(dict(scope=scope,arm=a,excluded=label,months=','.join(drop),remaining_pp=100*(rest[a]-rest.R)))
    save('common_month_phase',phase_ci);save('monthly_risk',risk);save('concentration',concentration)
if __name__=='__main__':main()
