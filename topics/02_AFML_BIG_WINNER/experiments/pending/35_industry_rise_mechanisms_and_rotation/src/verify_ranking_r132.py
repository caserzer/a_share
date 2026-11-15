"""Independent centered ranks, membership, outcome completeness and intervals."""
import pandas as pd
from scipy.stats import spearmanr
from common import *
from verify_evaluation_r131 import interval


def run():
    out=ROOT/'outputs/r132';receipt=json.loads((out/'receipt.json').read_text())
    for p,h in receipt['reads'].items():assert sha(p)==h,p
    for p,h in receipt['outputs'].items():assert sha(out/p)==h,p
    dest=out/'evaluation/outputs/r01';panel=pd.read_parquet(ROOT/'outputs/r130/monthly_panel.parquet');metrics=pd.read_csv(dest/'date_metrics.csv',parse_dates=['date']);selection=pd.read_parquet(dest/'selections.parquet');coverage=pd.read_csv(dest/'paired_coverage.csv',parse_dates=['date'])
    gk=['era','level','date','cohort'];metric_index=metrics.set_index(gk+['method','horizon']);covindex=coverage.set_index(gk);checks=0;selection_rows=[]
    variants={'F':['mom20','mom60','vol20','dd60'],'FD':['breadth21','breadth63'],'FC':['turn_rank504'],'FG':['pe_rank504'],'FDG':['breadth21','breadth63','pe_rank504']}
    for key,full in panel.groupby(['era','level','date']):
        base=full[full.price_ready]
        for cohort,needed in variants.items():
            z=base.dropna(subset=needed);rec=covindex.loc[key+(cohort,)];assert rec.catalogue_rows==len(full) and rec.price_ready==len(base) and rec.paired_rows==len(z)
            if len(z)<20:continue
            r=z[['mom20','mom60','vol20','dd60','breadth21','breadth63','turn_rank504','pe_rank504']].copy()
            for c in r:r[c]=(r[c].rank(method='average')-.5)/r[c].count()-.5
            f=(.5*(r.mom20+r.mom60)-r.vol20+r.dd60)/3;diff=.5*(r.breadth21+r.breadth63)
            scores={'momentum':r.mom60,'F':f,'FD':(f+diff)/2,'FC':(f-r.turn_rank504)/2,'FG':(f-r.pe_rank504)/2,'FDG':(f+diff-r.pe_rank504)/3}
            for method in (['momentum','F'] if cohort=='F' else ['F',cohort]):
                s=scores[method];ordered=z.assign(score=s).sort_values(['score','industry_code'],ascending=[False,True]);k=max(1,int(np.ceil(len(z)/5)));top=ordered.iloc[:k];bottom=ordered.iloc[-k:]
                for code in top.industry_code:selection_rows.append(dict(zip(['era','level','date'],key),cohort=cohort,method=method,industry_code=code,weight=1/k))
                for h in [20,60]:
                    row=metric_index.loc[key+(cohort,method,h)];y=z[f'excess{h}'];valid=y.notna()&s.notna();ic=spearmanr(s[valid],y[valid]).statistic if valid.sum()>=20 and y[valid].nunique()>1 else np.nan
                    tx=top[f'excess{h}'].mean() if top[f'excess{h}'].notna().all() else np.nan;bx=bottom[f'excess{h}'].mean() if bottom[f'excess{h}'].notna().all() else np.nan;ew=y.mean() if y.notna().all() else np.nan
                    expect={'ic':ic,'top_excess':tx,'bottom_excess':bx,'spread':tx-bx,'universe_excess':ew,'top_minus_equal':tx-ew,'top_excess_cost20bps':tx-.004,'top_excess_cost50bps':tx-.01}
                    for c,value in expect.items():assert np.isclose(row[c],value,atol=1e-12,rtol=1e-12,equal_nan=True)
                    assert row.n_signal==len(z) and row.n_outcome==int(valid.sum()) and row.top_n==k;assert bool(row.top_complete)==bool(top[f'excess{h}'].notna().all());checks+=1
    keys=['era','level','date','cohort','method','industry_code'];expected=pd.DataFrame(selection_rows);pd.testing.assert_frame_equal(expected.sort_values(keys).reset_index(drop=True),selection.sort_values(keys).reset_index(drop=True))
    increments=pd.read_csv(dest/'paired_increments.csv')
    for row in increments.to_dict('records'):
        g=metrics
        for k in ['era','level','cohort','horizon']:g=g[g[k].eq(row[k])]
        p=g.pivot(index='date',columns='method',values='ic').dropna();x=p[row['cohort']]-p.F;annual=x.groupby(x.index.year).mean()
        assert len(x)==row['months'] and int((annual>0).sum())==row['positive_years'] and len(annual)==row['years']
        assert np.isclose(x.mean(),row['delta_ic'],atol=1e-12,rtol=1e-12,equal_nan=True)
        for a,low,high in [(.05,'ci95_low','ci95_high'),(.05/16,'multiplicity_low','multiplicity_high')]:assert np.allclose(interval(x,a),[row[low],row[high]],atol=1e-12,rtol=1e-12,equal_nan=True)
        accept=len(x)>=24 and row['multiplicity_low']>0 and (annual>0).mean()>=2/3;status='historical_increment_supported' if accept and row['horizon']==20 else 'not_established' if row['horizon']==20 else 'secondary_descriptive';assert status==row['result']
    js(out/'verification.json',dict(status='PASS',date_metrics=checks,selections=len(selection),paired_comparisons=len(increments),scope='All fixed-rule ranks, selections, completeness, cost diagnostics and interval decisions'))
    print('PASS',checks,len(selection),len(increments))

if __name__=='__main__':run()
