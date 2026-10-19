"""Join explicitly dated original earnings forecasts to unchanged decision rows."""
import json
import numpy as np
import pandas as pd
from build_improvement_features import FEATURE_PANEL
from fetch_eps_reports import DEST
from prepare_panel import OUT

PANEL=OUT/'local_cache/eps_forecast_panel.parquet'


def pair_for_year(raw,year):
    if not isinstance(raw,str):return None
    values=json.loads(raw)
    pair=[values.get(str(year)),values.get(str(year+1))]
    if any(v is None or not np.isfinite(v) for v in pair):return None
    return np.asarray(pair,dtype=float)


def forecast_features(row):
    empty=dict(eps_pair_available=False,eps_positive=False,earnings_pair_available=False,earnings_positive=False,
        eps_log_growth=np.nan,earnings_log_growth=np.nan,forecast_next_loss=np.nan,
        forecast_basis_profit=np.nan,forecast_age_days=np.nan)
    available=pd.to_datetime(row.get('available_date'),errors='coerce')
    if pd.isna(available) or not available<row['date'] or (row['date']-available).days>180:return empty
    if row.get('status') not in ['parsed','profit_only']:return empty
    conflicts=[row.get('eps_conflict'),row.get('profit_conflict')]
    if any(pd.notna(v) and bool(v) for v in conflicts):return empty
    eps=pair_for_year(row.get('forecasts'),row['date'].year)
    profit=pair_for_year(row.get('profit_forecasts'),row['date'].year)
    result=empty.copy();result['forecast_age_days']=(row['date']-available).days
    if eps is not None:
        result['eps_pair_available']=True;result['eps_positive']=bool((eps>0).all())
        if result['eps_positive']:result['eps_log_growth']=float(np.log(eps[1]/eps[0]))
    selected=eps if eps is not None else profit
    if selected is not None:
        result['earnings_pair_available']=True;result['earnings_positive']=bool((selected>0).all())
        result['forecast_basis_profit']=float(eps is None)
        result['forecast_next_loss']=float(selected[1]<=0)
        if result['earnings_positive']:result['earnings_log_growth']=float(np.log(selected[1]/selected[0]))
    return result


def build():
    selection=json.loads((DEST/'selection.json').read_text())
    extractions=pd.read_parquet(DEST/'full_extractions.parquet')
    if len(extractions)!=selection['selected_reports'] or extractions.status.eq('fetch_failed').any():
        raise RuntimeError('Full source retrieval not complete; pilot/partial output cannot be scored as the full experiment')
    from validate_eps_extractions import validate
    extractions=validate()
    assert not extractions.infoCode.duplicated().any()
    mapping=pd.read_parquet(DEST/'decision_report_map.parquet')
    joined=mapping.merge(extractions,on='infoCode',how='left',validate='many_to_one')
    known=joined.infoCode.notna()
    assert joined.loc[known,'stockCode'].eq(joined.loc[known,'instrument'].str[2:]).all()
    rows=[forecast_features(row) for row in joined.to_dict('records')]
    features=pd.concat([joined[['date','instrument','infoCode','available_date']].reset_index(drop=True),pd.DataFrame(rows)],axis=1)
    base=pd.read_parquet(FEATURE_PANEL)
    result=base.merge(features,on=['date','instrument'],how='left',validate='one_to_one')
    for col in ['eps_pair_available','eps_positive','earnings_pair_available','earnings_positive']:
        result[col]=result[col].fillna(False).astype(bool)
    reversion=np.log(result.prior_pe_median/result.current_pe)
    result['eps_capped_log_growth']=np.log1p(np.expm1(result.eps_log_growth).clip(-.3,.3))
    result['eps_capped_anchor']=result.eps_capped_log_growth+reversion
    result['eps_raw_anchor']=result.eps_log_growth+reversion
    result['earnings_raw_anchor']=result.earnings_log_growth+reversion
    result['historical_log_growth']=np.log1p(result.growth_assumption)
    result.to_parquet(PANEL,index=False)
    test=result[result.common_eligible&(result.date>='2021-01-01')]
    assert len(test)==27600
    for flag in ['eps_pair_available','earnings_pair_available']:
        assert (pd.to_datetime(test.loc[test[flag],'available_date'])<test.loc[test[flag],'date']).all()
    coverage=test.groupby(test.date.dt.year).agg(rows=('instrument','size'),eps_rows=('eps_pair_available','sum'),
        eps_positive=('eps_positive','sum'),earnings_rows=('earnings_pair_available','sum'),earnings_positive=('earnings_positive','sum'))
    coverage.to_csv(DEST/'feature_coverage.csv')
    audit=dict(source_reports=len(extractions),source_statuses=extractions.status.value_counts().to_dict(),prediction_rows=len(test),
        eps_available=int(test.eps_pair_available.sum()),eps_positive=int(test.eps_positive.sum()),
        earnings_available=int(test.earnings_pair_available.sum()),earnings_positive=int(test.earnings_positive.sum()),
        forecast_age_days=test.loc[test.earnings_pair_available,'forecast_age_days'].quantile([.1,.5,.9]).to_dict(),
        fiscal_year_rule='use explicit decision-calendar-year and following-year forecasts; not a rolling-12m consensus EPS',
        profit_proxy='if EPS pair absent, ordinary attributed net-profit growth is a separate constant-share proxy; never relabeled EPS',
        missing='empty original, ambiguous parsing, unavailable years and future publication remain missing; never zero-filled')
    (DEST/'feature_audit.json').write_text(json.dumps(audit,indent=2)+'\n')
    print(json.dumps(audit,indent=2))


if __name__=='__main__':build()
