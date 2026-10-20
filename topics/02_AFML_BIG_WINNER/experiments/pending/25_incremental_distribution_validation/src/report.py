"""Generate reports and standalone figures from frozen experimental outputs."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from core import *


def table(frame):
    t=frame.copy()
    for c in t:
        if pd.api.types.is_float_dtype(t[c]):t[c]=t[c].map(lambda x:'NA' if pd.isna(x) else f'{x:.6f}')
    return '| '+' | '.join(map(str,t.columns))+' |\n| '+' | '.join(['---']*len(t.columns))+' |\n'+'\n'.join('| '+' | '.join(map(str,row))+' |' for row in t.itertuples(index=False,name=None))+'\n'


def save(name,content):
    (EP/name).write_text(content)


def main():
    s=pd.read_csv(OUT/'summary.csv');ci=pd.read_csv(OUT/'paired_intervals.csv');monthly=pd.read_csv(OUT/'monthly_scores.csv',parse_dates=['date'])
    audit=json.loads((OUT/'data_audit.json').read_text());execution=json.loads((OUT/'execution_audit.json').read_text());controls=json.loads((OUT/'controls.json').read_text())
    coverage=pd.read_csv(OUT/'outcome_coverage.csv');strata=pd.read_csv(OUT/'stratum_scores.csv');phases=pd.read_csv(OUT/'phase_intervals.csv');robust=pd.read_csv(OUT/'leave_out_robustness.csv')
    n=monthly.groupby('horizon').date.nunique().rename('months').reset_index()
    base=s[['horizon','model','crps','brier','tail_brier','rank_ic']].merge(n,on='horizon')
    mainci=ci[(ci.metric=='crps')&(ci.baseline=='B1')&(ci.mean_block==ci.horizon.clip(lower=6))]
    primary=mainci[(mainci.horizon==6)&(mainci.candidate=='M_VF')].iloc[0]
    primary2=ci[(ci.metric=='crps')&(ci.baseline=='B1')&(ci.candidate=='M_VF')&(ci.horizon==6)&(ci.mean_block==12)].iloc[0]
    tailci=ci[(ci.metric=='tail_brier')&(ci.baseline=='B1')&(ci.candidate=='M_VF')&(ci.horizon==6)&(ci.mean_block==6)].iloc[0]
    tailab=ci[(ci.metric=='tail_brier')&(ci.baseline=='M_R')&(ci.candidate=='M_VF')&(ci.horizon==6)&(ci.mean_block==6)].iloc[0]
    b=s[(s.horizon==6)&(s.model=='B1')].iloc[0];m=s[(s.horizon==6)&(s.model=='M_VF')].iloc[0]
    rel=-primary.delta/b.crps*100
    support=primary.high95<0
    hist='有历史点估计改善且95%区间低于零' if support else '没有获得配对区间支持的历史改善'
    # Safety includes monthly absolute coverage errors, not only signed coverage differences.
    safety=[]
    x=monthly[(monthly.horizon==6)&(monthly.model=='M_VF')].sort_values('date');z=monthly[(monthly.horizon==6)&(monthly.model=='B1')].sort_values('date')
    for metric,margin in [('brier',.01),('tail_brier',.01)]:
        diff=paired(x,z,metric);safety.append(dict(metric=metric,margin=margin,**interval(diff,6)))
    for level in [5,10,50,90,95]:
        col=f'cover{level:02}';diff=np.abs(x[col].to_numpy()-level/100)-np.abs(z[col].to_numpy()-level/100)
        safety.append(dict(metric=f'absolute_{col}_error',margin=.05,**interval(diff,6)))
    safe=pd.DataFrame(safety);safe['point_within_margin']=safe.delta<=safe.margin;safe['upper95_within_margin']=safe.high95<=safe.margin
    safe.to_csv(OUT/'primary_safety.csv',index=False)
    save('data_audit.md',f'''# EP25 数据与历史时点审计

审计日期2026-10-20；行情/标签冻结截至{audit['data_cutoff']}。本文件报告当前本地实际字节，原EP24报告保持不变。

全量面板{audit['raw_rows']:,}行、{audit['instruments']}只；R10原资格规则保留{audit['eligible_rows']:,}行、{audit['eligible_instruments']}只（含训练记录）。逐只读取原始前复权日线、核对市场日历与四期限结束日，全部可观察标签重算一致（容差1e-12）；未替换标签或股票。重算可观察标签计数：{audit['observed_labels_checked']}。基线原子float32逐元素一致；64位评分最大差异{execution['baseline_max_error']:.3g}。所有训练标签严格结束于季度开始前。

| 审计项 | 证据与结果 | 未解决边界 |
| --- | --- | --- |
| 股票池 | 本地data_audit.json和源prepare_panel.py保留主板400/创业板100历史成员；status_source含lifetime ST exclusion | 沪市全生命周期ST排除有选择偏差；不是无偏全A或退市全覆盖 |
| 财报公告与版本 | 本地原缓存{audit['financial_rows']:,}条原始财报，其中{audit['revised_after_notice']:,}条UPDATE_DATE晚于NOTICE_DATE；选中行available_date严格早于预测日 | max(公告,更新)只提供保守规则，不能证明全部数值原始版本；财报年龄10/50/90分位为{audit['financial_age_days_quantiles']}天 |
| 估值 | enrich_panel.py用供应商历史日度PE/PB/PS/PCF倒数及扩展PE秩；输入哈希保留 | 未独立认证历史原始版本；PE秩不是十年分位 |
| 盈利预期 | 本轮使用已实现历史财报增长，不使用一致预期或未来盈利预测 | 无新增已认证时点的盈利预期信息，不能评价此类信息的潜力 |
| 分红退市公司行动 | 主标签仍为前复权价格变化代理；引用EP24 R09公开行动对照及未解释跳变 | 未完整解决含分红总收益、退市结算、配股融资、重整；不称总回报模型 |
| 标签时隔 | 每次拟合检查max(label_end)<quarter_start；当前/未来缺失标签的股票仍预测 | 已到期缺失端点可能非随机，另列方向/尾部事件率界限；不补零 |
| 重叠与共同冲击 | 先等权汇总月份，再对整月作stationary bootstrap；L=max(6,h)及2L | 独立有效时间块很少；非平稳性、模型选择历史和股票池偏差不被bootstrap消除 |
| 独立验证 | EP24 R01–R47和R14新增到期区间已查看 | 没有真正未参与选择的测试区间；所有EP25历史结果仅探索性 |

原EP24总结的122,461为其当轮有效财报数量；此处122,947为现存缓存原始行数，统计口径不同，不覆盖旧报告。EP24后续已下载行情扩展到2026-10-19，但跨源且已被查看；不与本轮R10固定标签暗中拼接。

## 到期与缺失

'''+table(coverage.groupby('horizon')[['predicted','mature','observed','mature_missing','immature']].sum().reset_index())+'''
预测覆盖是全模型共同人群；评分仅在共同可观察结果上进行。outputs/missing_event_bounds.csv保留成熟缺失结果在全部上涨/全部下跌、全部重大亏损/全部非重大亏损时的事件率识别界限。收益没有有来源支持的有限上界，故不伪造CRPS缺失值界限。

来源与复核：outputs/input_receipts.json包括输入面板、1647只价格文件、日历、旧冻结预测哈希；outputs/ep24_preservation_before.json记录1040个原研究文件，执行后全部哈希一致。此承诺不涵盖未使用的全部4GB旧缓存，不能扩大为所有缓存逐字节审计。旧缓存没有写入路径。outputs/eligibility_by_year.csv列出样本资格变化，outputs/outcome_coverage.csv逐月列出未到期与到期缺失。
''')
    save('baseline_comparison.md',f'''# EP25 基线比较

所有结果为已查看历史上的探索性walk-forward；并非独立留出确认。CRPS与收益同单位，收益1代表100%。负Delta表示候选更好。每月股票等权，再等权平均月份；四期限分别评价，无方向硬门槛。

B0/B1按EP24 R10冻结公式重算，四候选同样本、同标签。B1是分位数重心收缩，不是两种CDF的混合。M_R用于识别算法/训练权重影响；只有同算法消融能把变化更直接归于信息。

'''+table(base)+f'''
## 候选相对B1的配对CRPS差异

'''+table(mainci[['horizon','candidate','delta','low95','high95','months','mean_block','approximate_blocks']])+f'''
6月主要对比M_VF−B1：Delta={primary.delta:.6f}，95%区间[{primary.low95:.6f}, {primary.high95:.6f}]，相对B1改善点估计{rel:.2f}%。块长12的区间[{primary2.low95:.6f}, {primary2.high95:.6f}]。{hist}。6月四候选同时报告98.75% Bonferroni区间（其他期限和消融95%区间为探索性）：

'''+table(mainci[mainci.horizon==6][['candidate','delta','low_family','high_family']])+'''
## 跨阶段与单一冲击检查

'''+table(phases[(phases.horizon==6)&(phases.baseline=='B1')][['candidate','phase','delta','low95','high95','months']])+'''
完整逐年分数、逐月删除/逐年删除结果见outputs/annual_scores.csv、leave_out_robustness.csv；不得挑选有利年份。下表为主要对比删除后的Delta范围：

'''+table(robust[(robust.horizon==6)&(robust.candidate=='M_VF')&(robust.baseline=='B1')].groupby('removal').delta.agg(['min','max']).reset_index())+f'''
原始每月差异的bootstrap标准差给出的近似80%功效可检测幅度为{primary.detectable_80pct_effect_approx:.6f}（2.8×bootstrap标准差，仅局部近似，不是严格功效认证）。{int(primary.months)}个6月重叠起点约{primary.approximate_blocks:.1f}个平均长度6月块，远少于股票条数。区间依赖弱平稳近似，不能消除结构变化和旧历史选择。

所有候选对B0/B1及五组同算法消融的两种块长区间见outputs/paired_intervals.csv；完整逐月评分见monthly_scores.csv。没有因结果增加、删除候选或调整标准。
''')
    contrasts=ci[(ci.baseline.str.startswith('M_'))&(ci.mean_block==ci.horizon.clip(lower=6))]
    ablate=contrasts[contrasts.metric=='crps'][['horizon','candidate','baseline','delta','low95','high95']]
    mechanism=contrasts[(contrasts.horizon==6)&contrasts.metric.isin(['common_cdf_distance','relative_crps','tail_brier'])][['candidate','baseline','metric','delta','low95','high95']]
    save('factor_ablation.md','''# EP25 因子增量与机制

四个CatBoost使用完全相同样本、权重、参数与期限。M_V−M_R检验估值，M_F−M_R检验财报，M_VF−M_R检验合并，M_VF−M_F和M_VF−M_V分别检验条件增量。所有比较都是探索性；不选择表现最好的一组重新定义主模型。

'''+table(ablate)+'''
## 6月改善来源

共同分布项：将同月所有个股预测CDF按等权混合，对本月实现收益的横截面经验CDF计算积分平方距离，数值越低越好。这评价当月人群整体分布的预测，不能解释为纯市场指数择时。相对项：预测按本月预测均值、实现标签按本月实现均值中心化后的CRPS，是事后机制诊断；不能当成提前已知大盘收益的可实施预测。尾部项：P(R<−20%)的Brier，与CRPS和排序分别解释。

'''+table(mechanism)+'''
同月Rank IC与首尾五分组收益差如下；B0常数分布没有排序，IC为NA。预期收益的高阶尾部依赖有限原子表示；排序能力应同时参考中位数IC（完整表见summary.csv）。

'''+table(s[s.horizon==6][['model','rank_ic','median_rank_ic','top_bottom_spread','common_cdf_distance','relative_crps','tail_brier']])+'''
## 条件与阶段

以下按预测时已知的大盘过去126日动量、原板块、当月规模和风险中位数划分；均未使用未来市场状态筛样本。小组点估计只用于范围诊断，不能从多个组里挑选成功。

'''+table(strata[(strata.horizon==6)&(strata.model.isin(['B1','M_R','M_VF']))][['model','dimension','group','months','crps','brier','tail_brier']])+'''
不存在独立信息来源的新证据，故本轮完成既定消融后停止，不根据局部好结果扩展算法、特征或参数。未发现全样本稳定改善不等同于证明估值/财报普遍无信息；尤其保守财报规则检验的是陈旧信息，且股票池和估值版本仍有限制。
''')
    cal=s[['horizon','model','p_up','observed_up','brier','p_tail','observed_tail','tail_brier','tail_error','tail_absolute_error']]
    quant=s[['horizon','model','cover05','cover10','cover50','cover90','cover95','coverage90','pit','direction']]
    save('calibration_report.md','''# EP25 概率可靠性、PIT与尾部

概率及观察事件率先按月平均。上涨是R>0，重大亏损为R<−20%；阈值相等时不计入事件。tail_error为预测减观察事件率，tail_absolute_error为逐条绝对概率误差；尾部Brier为主要尾部诊断。方向命中仅诊断。

'''+table(cal)+'''
## 分位数覆盖

coverXX=P(实现收益≤预测QXX)，理想为XX%；并列用≤。90%区间含两端，PIT用离散CDF左右极限的中点。离散原子和端点截断会产生并列，因此PIT并非连续分布下严格均匀变换；直方图形状结合条件校准理解，不进行伪独立股票样本的KS显著性检验。

'''+table(quant)+'''
## 主要对比安全性

退化Delta=联合模型−B1。覆盖项比较每月|覆盖率−名义分位|。预注册界限分别为Brier增加0.01、覆盖绝对误差增加5个百分点。只有区间上界也落在界限内才能对该诊断给出不退化的统计支持；不是仅按点估计宣布可靠。

'''+table(safe[['metric','delta','low95','high95','margin','point_within_margin','upper95_within_margin']])+'''
完整分位覆盖差异及两种块长区间在outputs/paired_intervals.csv；所有期限的条件校准在stratum_scores.csv与reliability.csv，PIT条件直方图在pit_histograms.csv。可靠性图使用固定概率十分位桶，样本先给每个预测月相等权重；表内保留各桶行数及月权重。图未绘制伪独立股票误差条。

总体覆盖接近名义水平不等于条件可靠：6月B1的Q05覆盖为5.48%，联合模型为6.29%，但上涨概率可靠性曲线明显偏离对角线，高预测概率桶并未稳定对应更高实现事件率。部分边缘桶样本很少，须同时查rows和month_weight。预定义安全界限内的相对退化检验通过，也不代表绝对概率已校准。

![上涨概率可靠性](outputs/reliability_up.png)

![重大亏损可靠性](outputs/reliability_tail.png)

![6月PIT](outputs/pit_6m.png)

有限原子表示并不提供无界右尾或真实灾难损失的可靠上界。缺失端点事件率界限另存missing_event_bounds.csv。缺失退市/重整数据不能由漂亮校准图修复。
''')
    controltable=pd.DataFrame(controls['controls'])[['control','model_crps','baseline_crps','delta','low95','high95','passed']]
    save('final_conclusion.md',f'''# EP25 最终结论

**在本研究的信息集和市场样本下，尚未发现可确认的稳定条件收益分布预测优势；总体判断为“证据不足”，不能宣称已独立验证。**

主要6月联合模型M_VF的CRPS为{m.crps:.6f}，冻结风险/市值基线B1为{b.crps:.6f}；Delta={primary.delta:.6f}，95%月份块区间[{primary.low95:.6f}, {primary.high95:.6f}]，相对改善点估计{rel:.2f}%。{hist}。完整1/3/6/12月结果、所有候选及置信区间均已保留，不用表现最好的期限替代主检验。

“支持”：只可用于正控制已知合成信号被管道识别、以及报告中具体有限的历史点估计；不能用于A股独立增量预测命题。“不支持”：本轮若某项消融或模型未取得CRPS和稳定性证据，就不支持该特定模型在该历史样本中的优势，不证明市场不可预测。“证据不足”：没有真正未参与选择的新测试区间，财报/估值历史版本、股票池与收益口径仍有限制，故不管历史结果符号如何，都不能完成独立样本外确认。

## 限制结论的具体因素

1. 信息：本轮仅使用历史估值与保守可用财报。财报年龄中位456天；无经认证的历史一致预期。负面结果不能排除更新、更真实的时点信息有效。
2. 模型：仅检验一个固定CatBoost概率模型及其同算法消融；M_R与B1差异含算法、训练权重及分布表达差异。不能把两者差异直接归为估值/财报增量。未搜索替代算法。
3. 数据：原沪市终身ST排除、历史估值原始版本不明、含分红/退市/配股/特殊行动未全覆盖。全部标签是明确标注的前复权价格代理，未为结果重写股票池或标签。
4. 统计能力：6月只有{int(primary.months)}个重叠预测月，约{primary.approximate_blocks:.1f}个6月时间块；近似80%可检测幅度{primary.detectable_80pct_effect_approx:.6f}。共同冲击、非平稳性和历史多轮选择限制区间解释。旧EP24区间全部是已查看历史，不再称独立留出。

## 局部改善为何不足以支持稳定信息优势

6月联合模型相对B1在2021–2023的CRPS差为+0.003269，2024以后为−0.001114，阶段间反号；删除单个月仍全部退化，删除整年则可能变号。这表明阶段依赖明显，不能挑后段改善确认成功。6月联合模型预测均值Rank IC为−0.015578，中位数Rank IC为+0.075263；不同分布位置的排序表现不同，不能混成一个选股优势。

尾部确有值得保留的探索性信号：6月重大亏损Brier相对B1差为{tailci.delta:.6f}，95%区间[{tailci.low95:.6f}, {tailci.high95:.6f}]；但相对同算法M_R的差为{tailab.delta:.6f}，区间[{tailab.low95:.6f}, {tailab.high95:.6f}]跨零。因此不能把这项局部尾部改善明确归于新增估值/财报，更不能抵消总体CRPS退化。它不是独立确认，亦未通过跨模型、跨期限多重比较的确认性检验。

1月风险/市值树M_R相对B1的CRPS差为−0.000170、95%区间低于零；它没有新增估值或财报信息。V/F/VF相对M_R的1月CRPS差点估计均为正。这区分了算法/表达改动与信息增量：本轮不支持估值、陈旧财报带来稳定完整分布优势；对其在更可信信息时点、其他人群或未来样本是否有效，证据仍不足。

因子消融、共同人群分布、相对排序和尾部风险分别见factor_ablation.md；安全性、分位覆盖与条件可靠性见calibration_report.md。某一机制改善不能合并声称全面优势。

## 控制与交付状态

'''+table(controltable)+f'''
正控制使用已知条件信号；负控制分别置乱合成训练/测试标签，防止跨界标签泄漏。两者使用相同概率预测、200原子CRPS和月度区间路径。控制通过说明管道可发现信号且未对置乱数据虚构优势，不能替代市场数据有效性或独立留出。

已完成{execution['fit_quarters']}个期限×季度、{execution['models_fit']}次固定候选拟合，B0/B1复算与原冻结预测一致；每个可评价期限完整输出。EP24清单中1040个旧文件哈希保持一致，原双20%未达结论不变。自动测试及复现记录见outputs/validation.json与README.md；完整原子、逐条预测和拟合模型保留本地outputs/local_cache，哈希收据可查。原始输入本来就未全部纳入Git，不能声称仅克隆即可精确重现。

停止：四候选与既定消融已全部执行，不新增候选、不改基线、不挑年份、不追逐正结果。未来验证流程可在新月末取得可信时点数据后冻结预测并追加到期标签；至少36个连续成熟6月起点才作计划内确认。已提供代码流程，尚无前瞻预测、没有自动定时任务。当前无法提供独立确认，这是证据限制，而非用未达到改善幅度判断研究未完成。
''')
    reliability=pd.read_csv(OUT/'reliability.csv');pits=pd.read_csv(OUT/'pit_histograms.csv')
    colors=dict(zip(['B0','B1','M_R','M_V','M_F','M_VF'],plt.get_cmap('tab10').colors[:6]))
    for event in ['up','tail']:
        fig,axes=plt.subplots(2,2,figsize=(11,8),layout='constrained')
        for h,ax in zip(CONFIG['horizons'],axes.flat):
            ax.plot([0,1],[0,1],color='grey',linestyle='--')
            for name in colors:
                t=reliability[(reliability.horizon==h)&(reliability.model==name)&(reliability.dimension=='all')&(reliability.event==event)].sort_values('predicted')
                ax.plot(t.predicted,t.observed,'o-',label=name,color=colors[name],markersize=3)
            ax.set(title=f'{h} month, {event}',xlabel='Predicted probability',ylabel='Observed event frequency',xlim=(0,1),ylim=(0,1));ax.grid(alpha=.2)
        axes.flat[0].legend(fontsize=8)
        fig.suptitle('Exploratory history; equal weight per origin month')
        fig.savefig(OUT/f'reliability_{event}.png',dpi=160);plt.close(fig)
    fig,axes=plt.subplots(2,3,figsize=(12,7),layout='constrained')
    for name,ax in zip(colors,axes.flat):
        t=pits[(pits.horizon==6)&(pits.model==name)&(pits.dimension=='all')].set_index('bin').probability.reindex(range(10),fill_value=0)
        ax.bar((np.arange(10)+.5)/10,t,width=.09,color=colors[name]);ax.axhline(.1,color='grey',linestyle='--');ax.set(title=name,xlim=(0,1),xlabel='Mid-PIT',ylabel='Month-weighted share')
    fig.suptitle('6 month finite-distribution PIT; exploratory history')
    fig.savefig(OUT/'pit_6m.png',dpi=160);plt.close(fig)
    write_json(OUT/'conclusion_status.json',dict(overall='INSUFFICIENT_EVIDENCE',independent_confirmation=False,primary_delta=float(primary.delta),primary_ci95=[float(primary.low95),float(primary.high95)],historical_primary_interval_below_zero=bool(support),safety_point_all_pass=bool(safe.point_within_margin.all()),safety_upper95_all_pass=bool(safe.upper95_within_margin.all()),stopped_after_registered_candidates=True))
    print((EP/'final_conclusion.md').read_text()[:1800])

if __name__=='__main__':main()
