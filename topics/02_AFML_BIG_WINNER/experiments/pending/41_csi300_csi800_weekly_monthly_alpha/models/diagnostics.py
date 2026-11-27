"""Further diagnostics for the exploratory tree, industry and downside tests."""
import json
from sklearn.metrics import roc_auc_score
from ep41inputs import *

def veto_intervals():
    oof=pd.read_parquet(OUT/'weekly_oof.parquet').query("in_core").dropna(subset=['event'])
    rows=[];rng=np.random.default_rng(4101)
    for f in sorted(OUT.glob('*_fold.json')):
        q=pd.Period(f.name[:6]);v=oof[oof.m10<q.start_time]
        block=v.signal_date.dt.to_period('M')
        months=sorted(block.unique());n=len(months)
        monthid=np.searchsorted(months,block)
        for name in ['inc','tail','history']:
            p=v[name].to_numpy();y=v.event.to_numpy();bins=np.digitize(p,[.02,.05,.1,.2,.5])
            # Preaggregate paired errors and ranks by tied forecast for weighted AUC.
            order=p.argsort(kind='stable');u=np.unique(p[order],return_index=True)[1]
            oo=monthid[order];yy=y[order]
            auc=[];brier=[];ece=[]
            draws=rng.integers(0,n-2,size=(500,(n+2)//3))
            for starts in draws:
                ix=(starts[:,None]+np.arange(3)).ravel()[:n]
                w=np.bincount(ix,minlength=n)
                pos=np.add.reduceat(w[oo]*yy,u)
                neg=np.add.reduceat(w[oo]*(1-yy),u)
                if pos.sum()==0 or neg.sum()==0:continue
                auc.append(pos@(neg.cumsum()-neg/2)/(pos.sum()*neg.sum()))
                wt=w[monthid];brier.append(np.average((p-y)**2,weights=wt))
                ece.append(abs(np.bincount(bins,weights=wt*(p-y))).sum()/wt.sum())
            for kind,values in [('auc',auc),('brier',brier),('ece',ece)]:
                rows.append((str(q),name,kind,*np.quantile(values,[.025,.975])))
    pd.DataFrame(rows,columns='fold model measure lo hi'.split()).to_csv(OUT/'veto_block_intervals.csv',index=False)

def rank_exposure(panel):
    industry=pd.read_parquet(CACHE/'industry.parquet')
    grouping=[panel.signal_date,panel.l1_name]
    groups=panel[STOCK].groupby(grouping)
    counts=groups.transform('count')
    valid=panel[STOCK].notna()
    fallback=(counts.lt(5)|np.repeat(panel.l1_name.eq('未知').to_numpy()[:,None],len(STOCK),axis=1)) & valid
    unique=groups.transform('max').eq(groups.transform('min')) & valid & ~fallback
    pop=panel[STOCK].groupby(panel.signal_date)
    unique|=pop.transform('max').eq(pop.transform('min')) & fallback
    z=panel[KEY+['outer','l1_name','vol20']].copy()
    z['fallback_fields']=fallback.sum(axis=1);z['constant_fields']=unique.sum(axis=1)
    z['observed_fields']=valid.sum(axis=1);z['industry_size']=panel.groupby(grouping).instrument.transform('size')
    z=z[z.outer].set_index(KEY)
    holdings=pd.read_parquet(OUT/'target_lists.parquet')
    holdings=holdings[holdings.arm.isin(['M1_raw','M1_global','M1_industry','top_M1_industry'])].explode('instruments')
    holdings=holdings.rename(columns={'date':'signal_date','instruments':'instrument'}).join(z,on=KEY,validate='m:1')
    holdings.groupby(['signal_date','arm'])[['fallback_fields','constant_fields','observed_fields','industry_size','vol20']].mean().to_csv(OUT/'m1_target_exposure.csv')
    quantiles=[]
    for q,h in panel.loc[panel.outer].groupby(panel.loc[panel.outer,'signal_date'].dt.to_period('Q')):
        audit=json.loads((OUT/(str(q)+'_fold.json')).read_text())
        for variant in ['M1_raw','M1_global','M1_industry','M3_depth3','M3_08','M3_stop']:
            raw=panel.loc[h.index,STOCK] if variant=='M1_raw' else (industry if variant=='M1_industry' else GLOBAL).loc[h.index]
            tree=audit['trees'][variant]
            f=pd.DataFrame(tree['splits'],columns=['col','value'])
            for c,thresholds in f.groupby('col'):
                x=np.sort(raw[c].dropna().to_numpy())
                if len(x):
                    qtls=np.searchsorted(x,thresholds.value)/len(x)
                    quantiles.append((str(q),variant,c,len(qtls),*np.quantile(qtls,[.25,.5,.75])))
    pd.DataFrame(quantiles,columns='fold model feature nodes outer_pct25 outer_pct50 outer_pct75'.split()).to_csv(OUT/'threshold_percentiles.csv',index=False)

def accounts():
    mm=pd.read_csv(OUT/'complete_months.csv')
    idx=json.loads((ep.PRIVATE/'net_excess_20261116/H00300.CSI.json').read_text())['data']
    bench=pd.DataFrame(idx['items'],columns=idx['fields']);bench.index=pd.to_datetime(bench.trade_date);bench=bench.sort_index().close
    indexret=bench.groupby(bench.index.strftime('%Y-%m')).last().pct_change()
    mm['index']=mm.month.map(indexret)
    g=mm.arm.str.startswith('I')
    mm.loc[g,'active']=mm.loc[g,'net']-mm.loc[g,'index']
    m=mm[g].groupby(['segment','arm']).active.agg(['mean','std','count']);m['annualized_tracking_error']=m['std']*np.sqrt(12)
    m.to_csv(OUT/'industry_tracking.csv')
    p=mm.pivot_table(index=['segment','month'],columns=['arm','hold'],values=['net','gross','fee'])
    rows=[]
    for rule in ['alert','momentum']:
        for seg,z in p.groupby(level=0):
            for col in ['net','gross','fee']:
                x=z[col].xs(10,axis=1,level=1)
                base=x.R;allocate=x['I2_'+rule+'_ridge']-base;stock=x.I2_original_peer-base
                combined=x['I2_'+rule+'_peer']-base;interaction=combined-allocate-stock
                for mth,a,s,c,it in zip(x.index,allocate,stock,combined,interaction):rows.append((seg,mth[1],rule,col,a,s,it,c))
    pd.DataFrame(rows,columns='segment month rule measure allocation stock interaction combined'.split()).to_csv(OUT/'i2_attribution.csv',index=False)

if __name__=='__main__':
    panel=pd.read_parquet(CACHE/'panel.parquet');GLOBAL=pd.read_parquet(CACHE/'global.parquet')
    rank_exposure(panel);veto_intervals();accounts()
