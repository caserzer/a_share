"""Read-only result checks and Chinese delivery for the frozen EP36 A1 run."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import markdown
from alpha_falsification import DEST, LOCAL, EP, CONFIG, verify, LAYERS, design
from common import sha, save_json

REPORT=EP/'reports/alpha_falsification_20261117'


def table(frame, decimals=4):
    f=frame.copy()
    for c in f:
        if pd.api.types.is_float_dtype(f[c]):f[c]=f[c].map(lambda x:f'{x:.{decimals}f}' if pd.notna(x) else 'NA')
    return f.to_markdown(index=False)


def validate():
    cfg,receipt=verify();complete=json.loads((DEST/'complete.json').read_text())
    for artifact in complete['artifacts']:assert sha(artifact['path'])==artifact['sha256']
    scores=pd.read_parquet(LOCAL/'decomposed_scores.parquet')
    detail=pd.read_csv(DEST/'a1_weekly.csv',parse_dates=['signal_date','mature'])
    summary=pd.read_csv(DEST/'a1_summary.csv')
    checks=[]
    def check(name,condition):
        assert condition,name
        checks.append(dict(check=name,passed=True))
    check('unique decomposition key',not scores.duplicated(['model','layer','signal_date','instrument']).any())
    check('score reconstruction',np.allclose(scores.score,scores.explained+scores.residual,atol=1e-12,rtol=1e-12))
    counts=scores.groupby(['signal_date','model','layer']).size().unstack(['model','layer'])
    check('all models and layers same counts',bool(counts.nunique(axis=1).eq(1).all()))
    # Counts alone do not establish identity: compare the actual sorted keys.
    base=None
    for _,g in scores.groupby(['model','layer']):
        keys=g[['signal_date','instrument']].sort_values(['signal_date','instrument']).reset_index(drop=True)
        if base is None:base=keys
        else:check('common identity '+str(_),keys.equals(base))
    check('label counts common across models layers',bool(detail.groupby(['signal_date','horizon']).labeled.nunique().eq(1).all()))
    primary=detail[detail.signal_date.between(cfg['primary_start'],cfg['primary_end']) & detail.mature.le(cfg['primary_end'])]
    for row in summary[summary.interval.eq('primary')].itertuples():
        g=primary[(primary.model==row.model)&(primary.layer==row.layer)&(primary.horizon==row.horizon)]
        check('primary cutoff '+str((row.model,row.layer,row.horizon,row.metric)),int(g[row.metric].count())==row.n and np.isclose(g[row.metric].mean(),row.mean))
    check('six adjusted primary tests',summary.holm_p.notna().sum()==6)
    check('adjustment cannot lower p',bool((summary.loc[summary.holm_p.notna(),'holm_p']>=summary.loc[summary.holm_p.notna(),'p']-1e-12).all()))
    # Independent scipy rank and direct joint-regression checks on chronological samples.
    labels=pd.read_parquet(EP/'private/labels.parquet')
    dates=sorted(scores.signal_date.unique())
    for date in [dates[0],dates[len(dates)//2],dates[-5]]:
        for model in ['E1','E2']:
            for layer in LAYERS:
                g=scores[(scores.signal_date==date)&(scores.model==model)&(scores.layer==layer)].merge(labels,on=['signal_date','instrument']).dropna(subset=['h10'])
                row=detail[(detail.signal_date==date)&(detail.model==model)&(detail.layer==layer)&(detail.horizon=='h10')].iloc[0]
                check('scipy residual IC '+str((date,model,layer)),np.isclose(spearmanr(g.residual,g.h10).statistic,row.residual_ic))
                x=design(g,layer);z=(g.score-g.score.mean())/g.score.std(ddof=0)
                coef=np.linalg.lstsq(np.column_stack([x,z]),g.h10,rcond=1e-12)[0][-1]
                check('joint OLS coefficient '+str((date,model,layer)),np.isclose(coef,row.conditional_slope,atol=1e-12))
    save_json(DEST/'validation.json',dict(check_count=len(checks),checks=checks,original_hashes_verified=True,all_complete_artifacts_verified=True))
    return cfg,summary,detail


def report():
    cfg,s,w=validate()
    REPORT.mkdir(parents=True,exist_ok=True)
    coverage=pd.read_csv(DEST/'coverage_weekly.csv')
    c=coverage[coverage.signal_date.between(cfg['primary_start'],cfg['primary_end'])]
    recon=pd.read_csv(DEST/'reconstruction_weekly.csv')
    valid_dates=w[(w.model=='E1')&(w.layer=='available_style')&(w.horizon=='h10')&w.signal_date.ge(cfg['primary_start'])&w.mature.le(cfg['primary_end'])].signal_date
    rp=recon[recon.signal_date.isin(valid_dates.dt.strftime('%Y-%m-%d'))]
    rm=rp.groupby(['model','layer'])[['r2','adjusted_r2','loo_q2','reconstruction_rank_ic']].mean().reset_index()
    primary=s[(s.interval=='primary')&(s.horizon=='h10')]
    main=primary[(primary.model=='E1')&primary.metric.isin(['original_ic','explained_ic','residual_ic','partial_rank_ic'])][['layer','metric','n','mean','ci_low','ci_high','holm_p']]
    aux=primary[(primary.model=='E2')&(primary.layer=='available_style')][['metric','mean','ci_low','ci_high']]
    slopes=primary[(primary.layer=='available_style')&(primary.metric=='conditional_slope')][['model','mean','ci_low','ci_high']].copy()
    slopes[['mean','ci_low','ci_high']]*=100
    extended=s[(s.interval=='extended')&(s.layer=='available_style')&(s.horizon=='h10')&s.metric.isin(['original_ic','residual_ic','partial_rank_ic'])][['model','metric','n','mean','ci_low','ci_high']]
    horizons=s[(s.interval=='primary')&(s.layer=='available_style')&(s.model=='E1')&s.metric.isin(['original_ic','residual_ic','partial_rank_ic'])][['horizon','metric','n','mean','ci_low','ci_high']]
    fig,axes=plt.subplots(1,2,figsize=(12,4.5),sharex=True)
    colors=['#284b63','#40916c','#bc4749']
    for ax,metric,title in zip(axes,['residual_ic','partial_rank_ic'],['Residual-score RankIC','Partial-rank IC']):
        a=primary[(primary.model=='E1')&(primary.metric==metric)].set_index('layer').loc[list(LAYERS)]
        for j,(layer,row) in enumerate(a.iterrows()):
            ax.errorbar(row['mean'],j,xerr=[[row['mean']-row.ci_low],[row.ci_high-row['mean']]],fmt='o',capsize=5,color=colors[j])
        ax.set_yticks(range(3),['Price + volatility','+ Industry','+ Risk + liquidity']);ax.invert_yaxis();ax.axvline(0,color='gray',ls='--',lw=1)
        ax.set_title(title);ax.set_xlabel('Weekly mean and 95% block-bootstrap interval');ax.grid(axis='x',alpha=.2)
    fig.suptitle('EP36 E1 / H10 / primary interval / same stock sample',fontweight='bold')
    fig.tight_layout();fig.savefig(REPORT/'a1_intervals.png',dpi=170);plt.close(fig)
    sumcols=['union_rows','common_scores','common_sample','unknown_industry']
    counts=c[sumcols].sum()
    nmissing=int(counts.common_scores-counts.common_sample)
    missing=pd.DataFrame([dict(variable=k.removesuffix('_missing'),missing_stock_signals=int(c[k].sum())) for k in c if k.endswith('_missing')])
    used=w[(w.model=='E1')&(w.layer=='available_style')&(w.horizon=='h10')&w.signal_date.isin(valid_dates)]
    annual=w[(w.model=='E1')&(w.layer=='available_style')&(w.horizon=='h10')&w.signal_date.isin(valid_dates)].copy()
    annual['year']=annual.signal_date.dt.year
    yr=annual.groupby('year').agg(weeks=('original_ic','count'),original_ic=('original_ic','mean'),residual_ic=('residual_ic','mean'),partial_rank_ic=('partial_rank_ic','mean')).reset_index()
    text=f'''# EP36 A1 风格剥离与下一阶段执行边界

**首批结论：E1 的排序优势在加入行业及其他已覆盖风格后明显减弱，主区间尚未确认稳定的残差排序增量；但不能据此断言信息已经被风格完全解释。** 收益回归和较长历史区间仍有正向线索，市值控制尚缺，经济价值尚未裁决。

本次完成数据覆盖审计和 A1；A2、B1、B2 仅登记研究指标和边界，完整市值输入与组合匹配合同仍未完成，未运行其经济实验。沿用原 E1/E2 expanding 封存预测，不重训、不运行 E3、不搜索调仓参数、不部署。完整设计见 [实验协议](PROTOCOL.md)，精确执行配置见 [JSON](../../configs/{CONFIG.name})。

## 1 想验证什么

Ridge 分数中，是否存在价格动量、反转、行业、波动、市场风险和流动性无法线性解释、却能预测未来收益的部分？A1 把原分数拆成风格解释分数和残差分数，并独立检查条件排序和条件收益关联。

这一步不能证明残差来自全新经济机制，也不能直接判断交易后是否赚钱。简单线性风格无法覆盖所有非线性、交互作用或遗漏风格。

## 2 E1 主检验结果

主评价期为信号不早于2021-01-08、H10标签不晚于2025-03-03成熟。H10共有{len(valid_dates)}个有效信号，最晚信号为{valid_dates.max():%Y-%m-%d}。以下各层共用同一股票样本与标签；95%区间为13周块 Bootstrap 的未作多重校正的百分位区间，Holm p 来自事先登记的六项主检验。

{table(main)}

![E1 三层控制后的 H10 排序信息区间](a1_intervals.png)

- 原分数平均 RankIC 约0.0412；全部已覆盖风格的解释分数约0.0503。
- 仅控制价格与波动时，残差 RankIC 约0.0164，六项族内 Holm p 约0.027。不能忽略这条正向线索。
- 加入行业后，残差 RankIC 约0.0080；再加入风险和流动性后约0.0084，主区间两者的95%区间均跨零。
- 全部已覆盖风格下，条件排序约0.0105，95%区间也跨零。不能把不同的“残差 IC”与“条件排序 IC”当成同一个检验。

**发现的是加入行业控制后剩余排序关联减弱；不是识别了行业的因果贡献，也不是证明 Ridge 全部由风格复制。** 不能用0.0412下降到0.0084直接声称“解释了约80%的 Alpha”，因为相关系数不是可加的收益或信息分解。

## 3 哪些证据仍然正向

FWL 条件收益回归的平均系数如下，单位为每一原分数截面标准差对应的 H10 收益百分点，采用同一风格控制。这里是收益幅度的线性条件关联，与排序指标不等价；属于辅助解释，未作为主检验成功替代品。

{table(slopes)}

全部可用历史区间的 H10 结果如下。E1 的残差和条件排序区间均偏正，提示区间依赖性；该区间也是反复查看过的历史，不是新盲测。

{table(extended)}

E2 在主区间全部已覆盖风格下的结果如下；它未提供升级复杂模型的主排序证据。仍保留其条件收益回归线索，不选择性省略。

{table(aux)}

## 4 风格能把分数重建到什么程度

以下是主 H10 评价信号上的逐截面统计均值。R²是样本内分数拟合程度，不是未来收益解释率。调整后R²扣除了设计矩阵秩；留一 Q²使用 PRESS，只验证同截面股票间的分数复制能力。

{table(rm)}

E1 的全部已覆盖风格平均解释约50.5%的分数截面方差，但逐股票留一 Q²约29.7%；原分数与解释分数的秩相关约0.66。样本内拟合并不等于可以完整替代 Ridge，更不等于同样的账户净收益。

逐周 Q²缺失数为{int(rp.loo_q2.isna().sum())}（全部模型/层合计）；若单个行业观测形成杠杆值1，不伪造其留一预测。全部周级明细保留。

## 5 数据覆盖与还不能下的结论

主日期范围内有{len(c)}个原信号，历史成分股票信号行共{int(counts.union_rows):,}，E1/E2共同有限分数行{int(counts.common_scores):,}。全部11项风格共同有效后保留{int(counts.common_sample):,}行，占共同有限分数的{counts.common_sample/counts.common_scores:.2%}；额外剔除{nmissing:,}行。每期共同样本介于{int(c.common_sample.min())}至{int(c.common_sample.max())}只股票。

主要缺失来自换手率窗口；下表的缺失可重叠，不能直接相加。共同样本规则会改变原报告的 RankIC，所以本轮原分数结果不应要求与旧全样本数字相等。

{table(missing)}

主H10评价样本仍有{int(used.unknown_labels.sum()):,}个未知股票标签，按同一规则从三种信号评价中剔除；它们没有从事先保存的可交易分数中删除。标签缺失的选择性无法通过配对自动消除。

历史行业使用截至信号日期的区间查询，UNKNOWN保留；主日期全部成分行中行业未知{int(counts.unknown_industry)}行。实际数据仍为 Historical-proxy，没有首发版本认证。总市值和流通市值未纳入；本地估值比率表的 known_at 也不能提供该证明。没有用最新股本倒推历史市值。

因此，本轮结论严格限定在“控制已覆盖线性风格的共同样本”。完整风格检验为 BLOCKED_DATA，不能宣布“所有标准风格均已排除”。

## 6 辅助期限与年度结果

H5/H10/H20共用原H10训练的模型分数，没有训练新模型。每个期限内部样本一致；不同期限因成熟日期和缺失端点不同，不能把下表当作统一事件路径的边际收益分析。

{table(horizons)}

主H10区间按年描述性结果，2025年为部分年度：

{table(yr)}

不按年度结果切换模型或控制层。B2需要同一事件名单、同一风格组合、实际费用和一致路径，不能由这些 RankIC 推算。

## 7 当前裁决与未完成项

| 实验 | 本次状态 | 裁决范围 |
|---|---|---|
| A1 已覆盖风格 | 已执行 | 主区间完整可用风格下残差排序增量未获确认，辅助证据仍有正向线索 |
| A1 包含市值的完整风格 | BLOCKED_DATA | 市值及历史可用时间未审计，不能裁决 |
| A2 组合净增量 | 指标已登记，未执行 | 尚缺完整风格输入、可行性审计和固定组合匹配参数 |
| B1 风格匹配相位差 | 指标已登记，未执行 | 共用A2合同；不能拿原月初收益替代 |
| B2 事件与连续账户寿命 | 指标已登记，未执行 | 不能用不同期限RankIC或重叠事件拼接账户 |
| 真正前瞻 | FORWARD_PENDING | 未启动新信号观察任务 |

A2/B1/B2的协议说明了待完成的参数，而不声称它们已经执行级冻结。继续落实时，应先补足数据与组合构造可行性，且在查看新经济结果前另存完整冻结版本。剩余排序信号为正或为零，都不能免除这些步骤。

本轮没有经济等价界限，不能把“不显著”解释为“简单模型与 Ridge 等价”。本轮也没有净收益实验，不能据此决定实际交易或宣称风格复制策略更赚钱。

## 8 复核与文件

A1计算前冻结输入、预测及源代码 SHA256，结束时逐个复验。原始输入、预测与旧报告未覆盖。详细交易级风格与分解分数存于已忽略的 private/{cfg['run']}/，不作为公开原始数据提交。

- [冻结清单](../../outputs/diagnostics/{cfg['run']}/freeze.json)
- [覆盖审计](../../outputs/diagnostics/{cfg['run']}/data_audit.json) · [逐周覆盖](../../outputs/diagnostics/{cfg['run']}/coverage_weekly.csv)
- [全部指标与区间](../../outputs/diagnostics/{cfg['run']}/a1_summary.csv) · [周级结果](../../outputs/diagnostics/{cfg['run']}/a1_weekly.csv)
- [分数重建](../../outputs/diagnostics/{cfg['run']}/reconstruction_weekly.csv) · [逐年结果](../../outputs/diagnostics/{cfg['run']}/a1_yearly.csv)
- [输出哈希](../../outputs/diagnostics/{cfg['run']}/complete.json) · [独立核验](../../outputs/diagnostics/{cfg['run']}/validation.json)

在EP36目录运行：

```bash
OPENBLAS_NUM_THREADS=4 python -m pytest tests -q
OPENBLAS_NUM_THREADS=4 python src/alpha_falsification.py verify
OPENBLAS_NUM_THREADS=4 python src/alpha_falsification_report.py
```

原运行已封存，freeze/run会拒绝覆盖已完成结果；重放应使用独立副本或新运行目录并保存新清单。
'''
    (REPORT/'REPORT.md').write_text(text)
    for name in ['REPORT','PROTOCOL']:
        source=(REPORT/(name+'.md')).read_text()
        html=markdown.markdown(source,extensions=['tables','fenced_code'])
        (REPORT/(name+'.html')).write_text('<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>EP36 Alpha研究</title><style>body{max-width:1100px;margin:36px auto;padding:0 24px;font:16px/1.8 system-ui;color:#223}table{border-collapse:collapse;display:block;overflow:auto}td,th{padding:7px 12px;border:1px solid #ccd;text-align:left}th{background:#edf3f5}img{max-width:100%}pre{overflow:auto;background:#f4f4f4;padding:16px}a{color:#146887}</style>'+html+'</html>')
    save_json(REPORT/'manifest.json',dict(inputs=[dict(path=str(p),sha256=sha(p)) for p in [CONFIG,DEST/'complete.json',DEST/'validation.json',EP/'src/alpha_falsification_report.py']],reports=[dict(path=str(p),sha256=sha(p)) for p in REPORT.iterdir() if p.is_file() and p.name!='manifest.json']))
    print('report',REPORT,'validation',json.loads((DEST/'validation.json').read_text())['check_count'])


if __name__=='__main__':report()
