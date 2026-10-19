"""Oracle diagnostic ONLY: best realized distribution shared by every stock/month.

Uses future outcomes deliberately; never a candidate forecast or achievement.
For each realized month, its empirical distribution minimizes mean proper scores
among distributions constrained to be identical for all stocks in that month.
"""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from prepare_panel import EP,OUT
from build_margin_information import digest
from diagnose_prediction_target import DEST as TARGET
DEST=OUT/'r35_regularized_information'


def oracle_scores(y):
    y=np.asarray(y,dtype=float);assert len(y) and np.isfinite(y).all()
    p_up=(y>0).mean();bin_id=np.searchsorted([-.2,-.05,.05,.2],y,side='right')
    frequencies=np.bincount(bin_id,minlength=5)/len(y)
    # Empirical mean CRPS = half the empirical pairwise absolute distance.
    ordered=np.sort(y);n=len(y)
    crps=float(np.dot(2*np.arange(n)-n+1,ordered)/(n*n))
    directional=y[y!=0]
    return dict(brier=float(p_up*(1-p_up)),multiclass_brier=float(1-np.dot(frequencies,frequencies)),crps=crps,
                accuracy=float(max((directional>0).sum(),(directional<0).sum())/len(directional)) if len(directional) else np.nan)


def run():
    DEST.mkdir(exist_ok=True);contract=json.loads((TARGET/'target_contract.json').read_text());rows=[];summary=[]
    for source in contract['files']:
        path=Path(source['path']);assert digest(path)==source['sha256'];h=source['months']
        d=pd.read_parquet(path);d=d[d.model.eq('B')&d.actual.notna()].copy()
        d['accuracy']=((d.p_up>d.p_down)==(d.actual>0)).astype(float).where(d.actual.ne(0))
        for date,g in d.groupby('date',sort=True):
            scores=oracle_scores(g.actual)
            # Independent direct losses verify the compact frequency/pair-distance formulas.
            y=g.actual.to_numpy();up=(y>0).astype(float);bins=np.searchsorted([-.2,-.05,.05,.2],y,side='right')
            onehot=np.eye(5)[bins]
            np.testing.assert_allclose(scores['brier'],np.mean((up-up.mean())**2),atol=1e-12)
            np.testing.assert_allclose(scores['multiclass_brier'],np.mean(np.sum((onehot-onehot.mean(axis=0))**2,axis=1)),atol=1e-12)
            np.testing.assert_allclose(scores['crps'],np.abs(y[:,None]-y[None,:]).mean()/2,atol=1e-12)
            for metric,oracle in scores.items():
                rows.append(dict(months=h,date=date,metric=metric,oracle_only=oracle,baseline=g[metric].mean()))
        means=pd.DataFrame(rows);means=means[means.months.eq(h)].groupby('metric')[['oracle_only','baseline']].mean()
        for metric,r in means.iterrows():
            relative=r.oracle_only/r.baseline-1 if metric=='accuracy' else 1-r.oracle_only/r.baseline
            summary.append(dict(months=h,metric=metric,baseline=r.baseline,oracle_only=r.oracle_only,
                oracle_relative_improvement=relative,oracle_reaches_20pct=relative>=.2,
                warning='FUTURE KNOWN ORACLE; identical distribution across stocks; NOT A VALID FORECAST'))
    pd.DataFrame(rows).to_csv(DEST/'shared_distribution_oracle_monthly.csv',index=False)
    summary=pd.DataFrame(summary);summary.to_csv(DEST/'shared_distribution_oracle_summary.csv',index=False)
    (DEST/'shared_distribution_oracle_audit.json').write_text(json.dumps(dict(
        diagnostic_only=True,uses_future_outcomes=True,valid_forecast=False,counts_as_candidate=False,
        all_frozen_baseline_hashes_verified=True,all_month_loss_formulas_independently_verified=True,
        monthly_metric_rows=len(rows),files=contract['files'],summary_sha256=digest(DEST/'shared_distribution_oracle_summary.csv')),indent=2)+'\n')
    lines=['# 事后市场共同分布诊断：不是预测结果','',
        '**使用真实未来结果，不能作为候选模型、回测成绩或目标完成证据。** 这项诊断只限制每个月所有股票使用完全相同的概率分布，但允许事后知道当月所有个股的未来收益。','',
        '该月真实收益的经验分布同时最小化这批股票的平均上涨Brier、五档Brier与CRPS；共同方向则取非零收益的多数方向。分别按原预测月等权，再与冻结B比较。因此这是“同月同分布”这一类方法在当前样本上的理想事后极限，不是一般个股模型的上限，也不证明总体目标不可能。','',
        '|期限|指标|B|事后共同分布|相对改善|达到20%（仅诊断）|','|---|---|---|---|---|---|']
    for r in summary.itertuples():
        lines.append(f'|{r.months}个月|{r.metric}|{r.baseline:.6f}|{r.oracle_only:.6f}|{r.oracle_relative_improvement:+.2%}|{r.oracle_reaches_20pct}|')
    lines+=['','未过门槛的指标说明：即使完美知道每个月的总体分布，仍必须引入有效的个股间概率差异才能满足该项20%目标。市场信息可以参与个股交互；这一结论并不排除这类交互模型。','']
    (EP/'shared_distribution_diagnostic.md').write_text('\n'.join(lines));print(summary.to_string(index=False))


if __name__=='__main__':run()
