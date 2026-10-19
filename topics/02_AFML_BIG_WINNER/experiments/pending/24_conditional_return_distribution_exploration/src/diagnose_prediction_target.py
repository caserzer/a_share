"""R16: freeze the user-confirmed 20% probability and accuracy target; diagnose errors."""
import hashlib
import json
import numpy as np
import pandas as pd
from build_three_factor_panel import DEST as PREVIOUS,OUT,EP
DEST=OUT/'r16_improvement_search'


def run():
    DEST.mkdir(exist_ok=True)
    targets=[];diagnostics=[];months=[];hashes=[]
    for h in [1,3,6]:
        path=PREVIOUS/f'predictions_{h}m.parquet'
        hashes.append(dict(months=h,path=str(path),sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
        d=pd.read_parquet(path);d=d[(d.model=='B')&d.actual.notna()].copy()
        d['accuracy']=np.where(d.actual!=0,((d.p_up>d.p_down)==(d.actual>0)).astype(float),np.nan)
        m=d.groupby('date')[['brier','multiclass_brier','crps','accuracy']].mean()
        for metric in m.columns:
            value=float(m[metric].mean())
            targets.append(dict(months=h,metric=metric,baseline=value,target=value*(1.2 if metric=='accuracy' else .8),comparison='at_least' if metric=='accuracy' else 'at_most'))
        m['months']=h;months.append(m.reset_index())
        month_rates=d.groupby('date').actual.apply(lambda x:float((x>0).mean()))
        oracle_brier=float((month_rates*(1-month_rates)).mean())
        diagnostics.append(dict(months=h,observed_rows=len(d),zero_return_rows=int((d.actual==0).sum()),origin_months=d.date.nunique(),
            baseline_brier=float(m.brier.mean()),future_known_month_rate_brier=oracle_brier,
            apparent_reduction_with_future_month_rate=1-oracle_brier/m.brier.mean(),
            warning='ORACLE DIAGNOSTIC ONLY: uses actual future outcomes; never a valid forecast or target achievement'))
    pd.DataFrame(targets).to_csv(DEST/'frozen_targets.csv',index=False)
    pd.concat(months).to_csv(DEST/'baseline_monthly.csv',index=False)
    pd.DataFrame(diagnostics).to_csv(DEST/'error_diagnostic_oracle_only.csv',index=False)
    manifest=dict(baseline='R15 B risk/size, identical common-feature stock/date population',
        user_target='All 1/3/6m: relative reduction >=20% in up Brier, five-bin Brier and CRPS AND relative increase >=20% in directional accuracy',
        accuracy='predict up when P(up)>P(down), otherwise down; exclude exact-zero realized returns for every model',
        aggregation='equal weight per prediction origin month',files=hashes,
        verification='strict chronological walk-forward; no future outcome based filtering; no best-month/cherry-picked-stock completion')
    path=DEST/'target_contract.json'
    if path.exists():assert json.loads(path.read_text())==manifest
    else:path.write_text(json.dumps(manifest,indent=2)+'\n')
    print(pd.DataFrame(targets).to_string(index=False));print(pd.DataFrame(diagnostics).to_string(index=False))


if __name__=='__main__':run()
