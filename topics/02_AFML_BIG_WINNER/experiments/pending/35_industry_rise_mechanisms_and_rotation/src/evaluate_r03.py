import pandas as pd
from common import *
from evaluate_r01 import scores


def run():
    d=pd.read_parquet(ROOT/'data/financial_monthly_panel.parquet');rows=[]
    for key,full in d.groupby(['era','level','date']):
        g=full[full.price_ready].dropna(subset=['dedt_change','margin_delta'])
        common=dict(zip(['era','level','date'],key),price_ready=int(full.price_ready.sum()),paired_n=len(g))
        if len(g)<20:
            rows.append(dict(common,status='insufficient_cross_section'));continue
        f=scores(g).F
        c=(centered_rank(g.dedt_change)+centered_rank(g.margin_delta))/2
        for h in [20,60]:
            y=g[f'excess{h}'];valid=y.notna()
            for method,s in [('F',f),('C',c),('FCfund',(f+c)/2)]:
                ic=s[valid].corr(y[valid],method='spearman') if valid.sum()>=20 else np.nan
                rows.append(dict(common,horizon=h,method=method,outcome_n=int(valid.sum()),ic=ic,status='descriptive_only_less_than_24_months'))
    r=pd.DataFrame(rows);r.to_csv(ROOT/'outputs/r03/date_metrics.csv',index=False)
    r.groupby(['level','method','horizon']).ic.agg(['count','mean']).to_csv(ROOT/'outputs/r03/summary.csv')
    js(ROOT/'outputs/r03/evaluation_receipt.json',dict(code_sha256=sha(__file__),panel_sha256=sha(ROOT/'data/financial_monthly_panel.parquet'),
        protocol_sha256=sha(ROOT/'protocols/r03.json'),status='insufficient_months_for_predictive_claim',rows=len(r)))
    print(r[['level','date','paired_n','horizon','method','ic']].to_string(index=False))

if __name__=='__main__':run()
