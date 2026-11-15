"""Pre-registered fixed ranking comparisons; selected missing outcomes stay missing."""
import pandas as pd
from common import *

VARIANTS={'F':['mom20','mom60','vol20','dd60'], 'FD':['breadth21','breadth63'], 'FC':['turn_rank504'], 'FG':['pe_rank504'], 'FDG':['breadth21','breadth63','pe_rank504']}


def scores(g):
    r=g[['mom20','mom60','vol20','dd60','breadth21','breadth63','turn_rank504','pe_rank504']].apply(centered_rank)
    f=((r.mom20+r.mom60)/2-r.vol20+r.dd60)/3
    dif=(r.breadth21+r.breadth63)/2; crowded=-r.turn_rank504; cheap=-r.pe_rank504
    return pd.DataFrame(dict(momentum=r.mom60,F=f,FD=(f+dif)/2,FC=(f+crowded)/2,FG=(f+cheap)/2,FDG=(f+dif+cheap)/3),index=g.index)


def bootstrap(x, alpha=.05):
    x=np.asarray(x,float); x=x[np.isfinite(x)]; n=len(x)
    if n<12:return (np.nan,np.nan)
    rng=np.random.default_rng(3501)
    starts=rng.integers(0,n,size=(2000,(n+5)//6))
    indices=(starts[:,:,None]+np.arange(6))%n
    means=x[indices.reshape(2000,-1)[:,:n]].mean(axis=1)
    return tuple(np.quantile(means,[alpha/2,1-alpha/2]))


def run():
    out=ROOT/'outputs/r01'
    assert sha(ROOT/'data/monthly_panel.parquet')==json.loads((out/'panel_receipt.json').read_text())['sha256']
    panel=pd.read_parquet(ROOT/'data/monthly_panel.parquet')
    rows=[]; coverage=[]; selections=[]
    for key,full in panel.groupby(['era','level','date'],sort=True):
        g=full[full.price_ready].copy()
        for cohort,needed in VARIANTS.items():
            z=g.dropna(subset=needed).copy()
            coverage.append(dict(zip(['era','level','date'],key),cohort=cohort,catalogue_rows=len(full),price_ready=len(g),paired_rows=len(z)))
            if len(z)<20:continue
            sc=scores(z)
            methods=['momentum','F'] if cohort=='F' else ['F',cohort]
            for method in methods:
                s=sc[method];order=z.assign(score=s).sort_values(['score','industry_code'],ascending=[False,True])
                k=max(1,int(np.ceil(len(z)*.2))); top=order.head(k);bottom=order.tail(k)
                for h in [20,60]:
                    y=z[f'excess{h}'];valid=y.notna()&s.notna()
                    # An observed-outcome correlation always discloses its changed denominator.
                    ic=s[valid].corr(y[valid],method='spearman') if valid.sum()>=20 and y[valid].nunique()>1 else np.nan
                    top_complete=top[f'excess{h}'].notna().all();bot_complete=bottom[f'excess{h}'].notna().all()
                    top_x=top[f'excess{h}'].mean() if top_complete else np.nan
                    bottom_x=bottom[f'excess{h}'].mean() if bot_complete else np.nan
                    ew=z[f'excess{h}'].mean() if y.notna().all() else np.nan
                    rows.append(dict(zip(['era','level','date'],key),cohort=cohort,method=method,horizon=h,n_signal=len(z),n_outcome=int(valid.sum()),ic=ic,
                        top_n=k,top_complete=top_complete,top_excess=top_x,bottom_excess=bottom_x,spread=top_x-bottom_x,
                        universe_excess=ew,top_minus_equal=top_x-ew,
                        top_excess_cost20bps=top_x-.004,top_excess_cost50bps=top_x-.01))
                for code in top.industry_code:
                    selections.append(dict(zip(['era','level','date'],key),cohort=cohort,method=method,industry_code=code,weight=1/k))
    r=pd.DataFrame(rows);r['year']=r.date.dt.year;r.to_csv(out/'date_metrics.csv',index=False)
    pd.DataFrame(coverage).to_csv(out/'paired_coverage.csv',index=False)
    pd.DataFrame(selections).to_parquet(out/'selections.parquet',index=False)
    agg={'ic':['count','mean','std'],'top_excess':['count','mean'],'spread':'mean','top_minus_equal':'mean','top_excess_cost20bps':'mean','top_excess_cost50bps':'mean'}
    for name,keys in [('summary',['era','level','cohort','method','horizon']),('annual',['era','level','cohort','method','horizon','year'])]:
        a=r.groupby(keys).agg(agg);a.columns=['_'.join(x) for x in a.columns];a.to_csv(out/f'{name}.csv')
    differences=[]
    for key,g in r[r.cohort.ne('F')].groupby(['era','level','cohort','horizon']):
        p=g.pivot(index='date',columns='method',values='ic').dropna();x=p[key[2]]-p.F
        lo,hi=bootstrap(x); adjlo,adjhi=bootstrap(x,.05/16)
        yearly=x.groupby(x.index.year).mean();n=len(x)
        acceptance=n>=24 and adjlo>0 and (yearly>0).mean()>=2/3
        differences.append(dict(zip(['era','level','cohort','horizon'],key),months=n,delta_ic=x.mean(),ci95_low=lo,ci95_high=hi,
            multiplicity_low=adjlo,multiplicity_high=adjhi,positive_years=int((yearly>0).sum()),years=len(yearly),
            result='historical_increment_supported' if acceptance and key[3]==20 else 'not_established' if key[3]==20 else 'secondary_descriptive'))
    pd.DataFrame(differences).to_csv(out/'paired_increments.csv',index=False)
    js(out/'run_receipt.json',dict(protocol_sha256=sha(ROOT/'protocols/r01.json'),panel_sha256=sha(ROOT/'data/monthly_panel.parquet'),
        code_hashes={p.name:sha(p) for p in (ROOT/'src').glob('*.py')},date_metric_rows=len(r),quality='Historical-proxy',trained_models=False))
    print(pd.DataFrame(differences).query('horizon==20')[['era','level','cohort','months','delta_ic','result']].to_string(index=False))

if __name__=='__main__':run()
