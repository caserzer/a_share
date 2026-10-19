"""R15 report and factorial heatmaps, with a bounded interpretation of the proxy."""
import os
os.environ.setdefault('MPLCONFIGDIR','/tmp/ep24-mpl')
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from build_three_factor_panel import DEST,EP
ORDER=['B','BC','BP','BF','BCP','BCF','BPF','BCPF','historical']
NAMES={'B':'基础','BC':'基础+信用','BP':'基础+PE','BF':'基础+前瞻锚','BCP':'基础+信用+PE','BCF':'基础+信用+前瞻锚','BPF':'基础+PE+前瞻锚','BCPF':'三个因素全加','historical':'无条件历史'}
FACTORS={'C':'信用利差','P':'PE分位','F':'前瞻估值锚'}


def report():
    summary=pd.read_csv(DEST/'summary.csv')
    effects=pd.read_csv(DEST/'factor_effects.csv')
    audit=json.loads((DEST/'feature_audit.json').read_text())
    phase=pd.read_csv(DEST/'phase_scores.csv')
    fig,axes=plt.subplots(1,2,figsize=(11,6))
    for ax,metric,title in zip(axes,['brier','multiclass_brier'],['Up probability Brier vs B','Five-bin Brier vs B']):
        matrix=[]
        for name in ORDER[:-1]:
            values=[]
            for h in [1,3,6]:
                g=summary[summary.months==h].set_index('model');values.append(g.loc[name,metric]-g.loc['B',metric])
            matrix.append(values)
        matrix=np.asarray(matrix);limit=max(abs(matrix.min()),abs(matrix.max()),1e-6)
        im=ax.imshow(matrix,cmap='RdBu_r',vmin=-limit,vmax=limit,aspect='auto')
        ax.set_xticks(range(3),['1m','3m','6m']);ax.set_yticks(range(8),ORDER[:-1]);ax.set_title(title+'\nnegative = better')
        for i in range(8):
            for j in range(3):ax.text(j,i,f'{matrix[i,j]:+.4f}',ha='center',va='center',fontsize=9,color='white' if abs(matrix[i,j])>limit*.6 else 'black')
        fig.colorbar(im,ax=ax,shrink=.7)
    fig.tight_layout();fig.savefig(DEST/'ablation_effects.png',dpi=150);plt.close(fig)
    lines=['# 信用利差、PE分位与前瞻收益率：消融实验（R15）','',
        '完成1/3/6个月逐月walk-forward，共8种因子组合和1个无条件历史基线。所有组合共用同一训练/预测人群，不用策略收益评价。','',
        '## 当前结论','',
        '**在完整历史窗口中，三个因素全加没有优于仅波动率/市值的基础模型。** 信用利差单独加入及在完整模型中保留，都使1/6个月方向或区间评分变差；3个月变化不够稳定。PE分位没有稳定增量。前瞻锚单独加入时，6个月分数略好，但置信区间跨零。', '',
        '前瞻锚在完整模型中对6个月五档分数有条件增量：含F相对移除F的差值约−0.00199，12月时间块95%区间约[−0.00316,−0.00088]；但完整模型五档分数0.79971仍差于基础模型0.79469。这表示它缓解了较差组合的问题，不能解读成整个方案已胜出。', '',
        '前瞻锚的1/3月五档效果在2021–23偏差、2024+略好，6月也主要在后段略好；缺少跨阶段稳定改善，因此不按单个时段选择性宣布成功。', '',
        '## 三个因素实际怎样构造','',
        '- **C 信用利差**：3年AAA中短票减3年国债，及其63观测日变化；取预测日之前最近观测。',
        '- **P PE分位**：当日正PE在截至当日可得正PE历史中的位置，至少252个有效值；数据主要从2018年开始，不是十年分位。',
        '- **F 前瞻估值锚**：`(1+增长假设) × 此前正PE中位数 / 当日PE − 1`。增长假设取当时可用报告的归母利润同比，固定截为±30%；假设总股数不变、12个月后PE回到历史中位。输入使用该回报的log(1+R)，没有引入未来实际收益。', '',
        '**F是公开历史信息构造的情景代理，不是分析师一致预期，也不是已经验证的未来盈利预测。** 不包含股息；三个预测期限都使用同一12月定价锚。', '',
        '## 样本和可用性限制','',
        f"共同预测样本为{audit['prediction_stock_dates']:,}个股票月、{audit['prediction_months']}个月；旧R14为29,596个股票月，本次基础模型也在共同样本上重算。",
        f"可用财报年龄中位数{audit['financial_age_days']['0.5']:.0f}天，90%分位{audit['financial_age_days']['0.9']:.0f}天；盈利增长假设截断比例{audit['growth_clipped_fraction']:.1%}。这些限制会削弱F代表真实前瞻盈利信息的能力。",
        '共同特征样本中，PE分位与前瞻锚秩相关约−0.84；两者共享估值信息，不能解释为两个独立来源。财报取公告/更新较晚日期，均严格早于预测日；PE中位数严格只用此前历史。','',
        '## 全部组合评分','',
        'B为原风险/规模模型。以下分数越小越好，按预测月份先平均；方向与五档Brier不能互相比大小。','',
        '|期限|组合|上涨Brier|五档Brier|CRPS|Q05跌破|90%覆盖|','|---|---|---|---|---|---|---|']
    for h in [1,3,6]:
        g=summary[summary.months==h].set_index('model')
        for name in ORDER:
            r=g.loc[name];lines.append(f'|{h}月|{name}：{NAMES[name]}|{r.brier:.5f}|{r.multiclass_brier:.5f}|{r.crps:.5f}|{r.below_q05:.1%}|{r.coverage90:.1%}|')
    lines+=['','## 逐个加入：相对基础B的变化','',
        '差值为“加入后−加入前”，负数表示改善；括号为12个月时间块的95%探索性区间。6个月块的结果也保存在CSV；并未做多模型比较校正。','',
        '|期限|因素|方向分数变化 [95%区间]|五档分数变化 [95%区间]|','|---|---|---|---|']
    for h in [1,3,6]:
        for f in 'CPF':
            g=effects[(effects.months==h)&(effects.phase=='all')&(effects.block_months==12)&(effects.factor==f)&(effects.background=='B')].set_index('metric')
            vals=[f'{g.loc[m,"difference"]:+.5f} [{g.loc[m,"lower95"]:+.5f}, {g.loc[m,"upper95"]:+.5f}]' for m in ['brier','multiclass_brier']]
            lines.append(f'|{h}月|{FACTORS[f]}|'+ '|'.join(vals)+'|')
    lines+=['','## 从完整模型移除：检验该因素在其余因素存在时的增量','',
        '下表仍以“包含该因素−移除该因素”计差，负数才支持保留它。不能将“在较差组合中有帮助”混同为“优于原始基础模型”。','',
        '|期限|因素|方向分数增量|五档分数增量|','|---|---|---|---|']
    for h in [1,3,6]:
        for f in 'CPF':
            g=effects[(effects.months==h)&(effects.phase=='all')&(effects.block_months==12)&(effects.factor==f)&(effects.with_model=='BCPF')].set_index('metric')
            vals=[f'{g.loc[m,"difference"]:+.5f} [{g.loc[m,"lower95"]:+.5f}, {g.loc[m,"upper95"]:+.5f}]' for m in ['brier','multiclass_brier']]
            lines.append(f'|{h}月|{FACTORS[f]}|'+ '|'.join(vals)+'|')
    lines+=['','![消融差异](outputs/r15_three_factor_ablation/ablation_effects.png)','',
        '## 时段稳定性与解释边界','',
        'phase_scores.csv和factor_effects.csv分开报告2021–2023与2024+阶段；annual_scores.csv逐年报告。probability_calibration.csv包含上涨、下跌和五档概率组的预测/实际频率。不能只看总平均或最好的组合。', '',
        '这里检验的是固定近邻模型、固定因子定义和可用历史数据下的增量。信用利差是共同时间状态，可能同时改变近邻的历史时段构成；PE与F高度相关；F使用较旧财报且对估值回归作了强假设。因此负面结果不能推出这些经济信息本身没有预测价值。', '',
        '本次没有调参找最好结果，没有引入新的独立封存时段。源修订、股票池选择偏差、前复权价格代理等旧限制保留。', '',
        '## 复跑','', '```bash','EP=experiments/pending/24_conditional_return_distribution_exploration',
        '.venv/bin/python "$EP/src/build_three_factor_panel.py"',
        'OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python "$EP/src/run_three_factor_ablation.py"',
        '.venv/bin/python "$EP/src/evaluate_three_factor_ablation.py"',
        '.venv/bin/python "$EP/src/score_three_factor_extension.py"',
        '.venv/bin/python "$EP/src/report_three_factor_ablation.py"',
        '.venv/bin/python "$EP/src/audit_three_factor_ablation.py"','```']
    extra=pd.read_csv(DEST/'newly_matured_sensitivity/summary.csv').query("scope=='stable_source'")
    lines+=['','## 新增到期标签的回溯敏感性','',
        '这批标签已在R14查看，本次绝不是新独立测试。1/3/6月仍只有1/2/4个预测月份，源一致样本分别407/808/1605个股票月；所有组合在相同样本上比较。', '',
        '|期限|模型|方向Brier|五档Brier|Q05跌破|90%覆盖|','|---|---|---|---|---|---|']
    for h in [1,3,6]:
        g=extra[extra.months==h].set_index('model')
        for name in ['B','BC','BF','BCPF']:
            r=g.loc[name];lines.append(f'|{h}月|{name}|{r.brier:.5f}|{r.multiclass_brier:.5f}|{r.below_q05:.1%}|{r.coverage90:.1%}|')
    lines+=['','信用利差在新增6月样本中出现了相反表现：BC相对B方向、五档与尾部覆盖均改善，Q05跌破从约12.3%降至9.3%，但仍高于5%。前瞻锚在这些新增6月样本中反而使分数变差。3月完整模型略好，1/6月完整模型较差。', '',
        '这种符号变化说明增量具有明显时段依赖，不能简单概括为信用因子永远有害，或前瞻锚已经有效。新增月份少且已查看，不据此选择新参数或宣称市场状态机制已被证实。', '',
        '补充复跑：`src/score_three_factor_extension.py`；输出在 `outputs/r15_three_factor_ablation/newly_matured_sensitivity/`。它重评分已有预测，不把已看到的新标签回填进本轮历史训练。']
    (EP/'three_factor_ablation_report.md').write_text('\n'.join(lines)+'\n')


if __name__=='__main__':report()
