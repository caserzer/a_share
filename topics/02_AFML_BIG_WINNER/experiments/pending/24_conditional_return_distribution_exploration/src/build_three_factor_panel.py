"""R15: construct a historical earnings/valuation forward-return anchor, no future labels."""
import json
import numpy as np
import pandas as pd
from prepare_panel import DATA,OUT,EP
from run_four_horizons import TECH
DEST=OUT/'r15_three_factor_ablation'
PANEL=OUT/'local_cache/three_factor_panel.parquet'
BASE=['vol63','log_cap']
GROUPS={'C':['credit_spread_3y','credit_change63'],'P':['pe_percentile'],'F':['forward_log_anchor12']}


def forward_anchor(growth_percent,current_pe,prior_median):
    growth=np.clip(np.asarray(growth_percent,dtype=float)/100,-.30,.30)
    return (1+growth)*np.asarray(prior_median)/np.asarray(current_pe)-1


def build():
    DEST.mkdir(exist_ok=True)
    panel=pd.read_parquet(OUT/'local_cache/four_horizon_panel.parquet')
    pieces=[]
    for stock,g in panel.groupby('instrument',sort=True):
        g=g.copy()
        path=OUT/f'local_cache/public_valuation/{stock[2:]}.parquet'
        if path.exists():
            v=pd.read_parquet(path);v['date']=pd.to_datetime(v.TRADE_DATE)
            v=v.sort_values('date').drop_duplicates('date',keep='last')
            pe=pd.to_numeric(v.PE_TTM,errors='coerce').where(lambda x:x>0)
            v['current_pe']=pe
            v['prior_pe_median']=pe.expanding(min_periods=252).median().shift(1)
            v['prior_pe_count']=pe.notna().cumsum().shift(1)
            v['prior_pe_last_date']=v.date.where(pe.notna()).ffill().shift(1)
            g=g.merge(v[['date','current_pe','prior_pe_median','prior_pe_count','prior_pe_last_date']],on='date',how='left',validate='one_to_one')
        pieces.append(g)
    data=pd.concat(pieces,ignore_index=True)
    data['growth_assumption']=np.clip(data.profit_growth/100,-.30,.30)
    data['forward_return_12m']=forward_anchor(data.profit_growth,data.current_pe,data.prior_pe_median)
    data['forward_log_anchor12']=np.log1p(data.forward_return_12m)
    data['financial_age_days']=(data.date-data.financial_report_date).dt.days
    data['credit_age_days']=(data.date-data.yield_observation_date).dt.days
    data=data.replace([np.inf,-np.inf],np.nan)
    old_population=data[TECH+['earnings_yield','book_yield']].notna().all(axis=1)
    required=BASE+[c for cols in GROUPS.values() for c in cols]
    ready=data[required].notna().all(axis=1)&(data.prior_pe_count>=252)&(data.current_pe>0)
    ready &= (data.financial_available_date<data.date)&(data.yield_observation_date<data.date)&(data.prior_pe_last_date<data.date)
    data['common_eligible']=old_population&ready
    data.to_parquet(PANEL,index=False)
    cov=[]
    for year,g in data.groupby(data.date.dt.year):
        old=old_population.loc[g.index];use=g.common_eligible
        cov.append(dict(year=year,all_rows=len(g),r14_rows=int(old.sum()),common_rows=int(use.sum()),
            missing_credit=int(g[GROUPS['C']].isna().any(axis=1).sum()),missing_pe=int(g.pe_percentile.isna().sum()),
            missing_forward=int(g.forward_log_anchor12.isna().sum())))
    pd.DataFrame(cov).to_csv(DEST/'feature_coverage.csv',index=False)
    eligible=data[data.common_eligible];test=eligible[eligible.date>='2021-01-01']
    audit=dict(rows=len(data),common_rows=len(eligible),prediction_stock_dates=len(test),prediction_months=test.date.nunique(),
        current_pe_positive=bool((eligible.current_pe>0).all()),history_strictly_prior=bool((eligible.prior_pe_last_date<eligible.date).all()),
        financial_strictly_prior=bool((eligible.financial_available_date<eligible.date).all()),credit_strictly_prior=bool((eligible.yield_observation_date<eligible.date).all()),
        growth_clipped_fraction=float((test.profit_growth.abs()>30).mean()),
        financial_age_days=test.financial_age_days.quantile([.1,.5,.9]).to_dict(),
        forward_anchor_quantiles=test.forward_return_12m.quantile([.01,.1,.5,.9,.99]).to_dict(),
        note='Scenario-based forward-return anchor, not analyst consensus; past report growth with fixed ±30% cap, constant shares, prior historical median PE in 12m')
    (DEST/'feature_audit.json').write_text(json.dumps(audit,indent=2)+'\n')
    eligible[required].corr(method='spearman').to_csv(DEST/'feature_rank_correlations.csv')
    print(json.dumps(audit,indent=2))


if __name__=='__main__':build()
