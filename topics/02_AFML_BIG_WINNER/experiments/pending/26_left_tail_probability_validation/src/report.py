"""EP26 auditable reports and figures; no fitted models or selection changes."""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.stats import norm
from core import *


def md(frame):
    t=frame.copy()
    for c in t:
        if pd.api.types.is_float_dtype(t[c]):t[c]=t[c].map(lambda x:'NA' if pd.isna(x) else f'{x:.6f}')
    return '| '+' | '.join(map(str,t.columns))+' |\n| '+' | '.join(['---']*len(t.columns))+' |\n'+'\n'.join('| '+' | '.join(map(str,row))+' |' for row in t.itertuples(index=False,name=None))+'\n'


def save(name,content):
    (EP/name).write_text(content)


def risk_deciles():
    full=pd.read_parquet(CACHE/'all_predictions.parquet');records=[]
    for (model,date),g in full.groupby(['model','date']):
        g=g.reset_index(drop=True);order=np.lexsort((tie_keys(g.instrument),g.p_loss20.to_numpy()));decile=np.empty(len(g),int)
        decile[order]=np.minimum(np.arange(len(g))*10//len(g),9)
        for d in range(10):
            part=g[decile==d];known=part.actual.notna()
            if known.any():records.append(dict(model=model,date=date,decile=d+1,rows=int(known.sum()),events=int((part.actual<-.2).sum()),predicted=float(part.loc[known,'p_loss20'].mean()),observed=float((part.loc[known,'actual']<-.2).mean())))
    t=pd.DataFrame(records);t.to_csv(OUT/'risk_decile_monthly.csv',index=False)
    agg=t.groupby(['model','decile']).agg(rows=('rows','sum'),events=('events','sum'),covered_months=('date','size'),predicted=('predicted','mean'),observed=('observed','mean')).reset_index()
    agg.to_csv(OUT/'risk_deciles.csv',index=False)
    return agg


def main():
    summary=pd.read_csv(OUT/'summary.csv');s=summary[summary.threshold==20].copy();intervals=pd.read_csv(OUT/'paired_intervals.csv').drop_duplicates()
    mainci=intervals[(intervals.threshold==20)&(intervals.block==6)]
    primary=mainci[(mainci.candidate=='M_VF')&(mainci.baseline=='M_R')&(mainci.metric=='brier')].iloc[0]
    block12=intervals[(intervals.threshold==20)&(intervals.block==12)&(intervals.candidate=='M_VF')&(intervals.baseline=='M_R')&(intervals.metric=='brier')].iloc[0]
    base=s[s.model.eq('M_R')].iloc[0];joint=s[s.model.eq('M_VF')].iloc[0];val=s[s.model.eq('M_V')].iloc[0];risk=s[s.model.eq('B1')].iloc[0]
    audit=json.loads((OUT/'data_audit.json').read_text());coverage=pd.read_csv(OUT/'outcome_coverage.csv');conditional=pd.read_csv(OUT/'conditional_scores.csv');phases=pd.read_csv(OUT/'phase_intervals.csv')
    ages=pd.read_csv(OUT/'financial_age_audit.csv');cal=pd.read_csv(OUT/'calibration.csv');bias=pd.read_csv(OUT/'probability_bias_intervals.csv');control=json.loads((OUT/'controls.json').read_text())
    portfolio=pd.read_csv(OUT/'portfolio_summary.csv');paudit=json.loads((OUT/'portfolio_audit.json').read_text());cohort=pd.read_csv(OUT/'portfolio_cohort_scores.csv');pci=pd.read_csv(OUT/'portfolio_cohort_intervals.csv');exposure=pd.read_csv(OUT/'portfolio_exposures.csv')
    beta=pd.read_csv(OUT/'portfolio_benchmark_beta.csv');indattr=pd.read_csv(OUT/'portfolio_industry_attribution.csv');esci=pd.read_csv(OUT/'portfolio_es_intervals.csv');opportunity=pd.read_csv(OUT/'portfolio_opportunity_cost.csv')
    if primary.se>0:
        z=C['prospective']['important_absolute_brier_improvement']/primary.se
        power=float(norm.cdf(-1.96+z)+norm.cdf(-1.96-z))
    else:power=1.
    write_json(OUT/'statistical_power.json',dict(primary_months=int(primary.months),approximate_blocks=primary.approximate_blocks,paired_bootstrap_se=primary.se,
        important_absolute_brier_improvement=.002,approximate_two_sided_power_for_important_effect=power,approximate_80pct_detectable_effect=primary.detectable_80pct_effect_approx,
        limitation='local normal/weak-stationary approximation; not exact prospective power, excludes data and historical model-selection bias'))
    save('data_audit.md',f'''# EP26 左尾事件与历史时点审计

标签源截至2026-05-29，审计2026-10-20。EP25阈值与本轮均为严格R_6m<−20%，起点/目标日/复权代理一致。重新读取1647只原始日线与日历，56,000行6月收益及事件逐条重算一致；无标签或池修复。源SHA256在outputs/source_receipts.csv。

原面板56,000行；EP25原资格规则保留43,960行（含训练），预测29,596个股票月；可评分{audit['scorable_rows']:,}行，{audit['events']:,}个重大亏损事件，{audit['months']}个月。到期缺失{audit['mature_missing']}行，不填0；EP25的B1和四分位树p20逐条完全一致。未到期不进入评分，但预测全部保留。

| 问题 | 当前证据 | 对左尾概率的限制 |
| --- | --- | --- |
| 未来ST与幸存者 | 原status_source含沪市lifetime ST exclusion；原池主板400/创业板100 | 可能提前排除日后困境股票，导致重大亏损事件漏计；不能估计池外偏差大小 |
| 财报披露/修订 | available_date=max(NOTICE_DATE,UPDATE_DATE)，严格早于预测日，未把最新可下载版本回填 | 只能保证保守日期规则，不能认证原始披露版本；F组包括年龄与可用性，负结果不等于财务内容永远无效 |
| 456天年龄 | 预测人群财报年龄中位{audit['financial_age_median']:.0f}天，单列分层 | 新鲜财报在已到期子集仅769行/2个预测月，无法可靠评价最新财报信号 |
| 估值历史 | 供应商历史PE/PB等倒数及扩展正PE历史秩 | 不可修订性未认证；PE历史秩不是十年分位，也不是分析师预期 |
| 退市/停牌/公司行动 | 原EP24 R09保留普通分红送转敏感性和未解释变化；主标签仍前复权价格代理 | 缺结算、配股/重整、报价中断可能漏记最坏亏损；无法把已观察股票的好结果外推退市全体 |
| 利息保障/一致预期 | 本轮未接入可靠历史字段 | 未检验这些独立信息来源，未伪造填充 |
| 时间隔离 | 330次正式分类拟合均max(end_6)<季度开始；利率观测、财报可用日严格早于预测日 | 训练隔离不是未参与选择的独立确认 |
| 行业归因 | 历史分类可得比例{audit['industry_known_fraction']:.2%}；陈旧/未知比例{audit['industry_stale_fraction']:.2%} | 只做组合归因，不作为预测新因子；不能宣称精确行业中性 |
| 重叠和选择 | 59个6月起点，整月stationary bootstrap L6/L12 | 约9.8/4.9个块；旧历史已多轮研究，区间只作探索性 |

## 财报陈旧度专门审计

'''+md(ages)+'''
rows为全部预测；known为已到期可观测结果，二者不能混同。<=365天3061条预测仅769条有结果，且只覆盖2个可评分月份；不是有7个月独立“最新财报”检验。>548天等极小组也不能作强结论。完整年龄×模型Brier/AUC/校准在conditional_scores.csv，均保留原样本，没有删陈旧行让模型变好。

到期缺失结果的事件率下/上界在outcome_coverage.csv；各模型Brier最优/最差填充界限在missing_brier_bounds.csv。这只界定原池内25条缺失，不能界定被未来ST筛掉或从未入池的股票。全股票池选择偏差、退市缺失的方向可能使观察左尾过轻，大小仍未知。

原EP24/EP25共1191个可评审文件在prior_episodes_preservation.json承诺，执行后重新核验。只读使用原缓存，没有修改旧结论。全部实验历史是探索性，未新下载行情冒充独立样本。
''')
    save('baseline_comparison.md',f'''# EP26 基线与重大亏损概率评分

主事件严格R_6m<−20%。B0为成熟历史原始事件率；B1为冻结近邻；D_R及D_V/F/VF为EP25冻结分位树；M_*为本轮直接分类器。M_R与M_VF相同训练行、容量、权重、季度拟合，主比较不混淆算法与信息。

有效股票月{int(base.rows):,}，事件{int(base.events):,}；pooled发生率{base.pooled_base_rate:.4%}，先月后年等权的发生率{base.base_rate:.4%}；59个月，不能用股票数当独立时间样本。主要表中的AUC/AP先逐月评价。

'''+md(s[['model','brier','auc','pr_auc','base_rate','predicted','bias','rows','events','months']])+f'''
主要Delta_Brier=M_VF−M_R={primary.estimate:.6f}，相对改善{primary.relative_improvement_percent:.3f}%（负改善即误差增加），95%区间[{primary.low95:.6f}, {primary.high95:.6f}]。L12区间[{block12.low95:.6f}, {block12.high95:.6f}]。主检验不支持联合信息降低概率误差，也不能据此证明信息普遍无效。

## 对基础风险与信息增量的区分

'''+md(mainci[(mainci.metric=='brier')&mainci.candidate.isin(['B1','M_R','M_V','M_F','M_VF','M_VFS'])&mainci.baseline.isin(['B0','B1','D_R','M_R','M_VF'])][['candidate','baseline','estimate','low95','high95','relative_improvement_percent']])+'''
所有阈值、四个主要信息增量及固定市场交互完整配对区间见outputs/paired_intervals.csv。6月loss20四增量对M_R的98.75% Bonferroni区间另列low_family/high_family；其他模型、机制和辅助阈值均为探索性，不挑最有利区间。

## 统计功效与独立性

'''+f'''主要配对bootstrap标准差{primary.se:.6f}，近似80%可检测Brier幅度{primary.detectable_80pct_effect_approx:.6f}。预设重要幅度0.002的局部双侧正态功效约{power:.1%}，尚不足80%。该近似没有计入非平稳与历史模型选择，不能当正式样本量承诺。事件4581次在同月高度相关，时间信息仍只有59个重叠起点，约9.8个6月块。

'''+md(phases[(phases.candidate=='M_VF')&phases.baseline.eq('M_R')][['phase','estimate','low95','high95','months']])+'''
逐年、可观测市场状态和删除月份/年份结果分别保留在conditional_scores.csv、phase_intervals.csv、leave_out_robustness.csv；不得挑某个年份重新定义成功。没有独立新留出样本，所有区间仅为历史探索。
''')
    ab=mainci[mainci.apply(lambda r:(r.candidate,r.baseline) in [('M_V','M_R'),('M_F','M_R'),('M_VF','M_R'),('M_VF','M_V'),('M_VF','M_F'),('M_VFS','M_VF')],axis=1)]
    save('factor_ablation.md','''# EP26 同算法匹配消融

主要五组消融、一个预指定市场状态交互。全部分类候选相同训练/预测行、季度时间隔离、120轮深3、月度权重，无类别加权；缺失字段不删行。F组包含财报年龄，故检验的是财务字段+陈旧度信息组，不是纯粹某一财务比率的因果效应。

'''+md(ab[ab.metric.isin(['brier','auc','pr_auc'])][['candidate','baseline','metric','estimate','low95','high95']])+'''
估值单组M_V相对M_R的AUC增加约0.016973，未调整95%区间略高于0；Brier差−0.001337的区间跨0，PR-AUC增量也跨0。这只支持有限的历史排序线索，尚不支持可靠概率增量或独立发现。M_VF加入财报后未改善主要Brier，且AUC低于M_V；不能把完整模型胜某一基线当作新增F/V成立。

## 共同风险与个股风险分开

Brier恒等分解为(pbar−ybar)^2与中心化横截面项。前项评价当月人群总体风险水平偏差，后项包括个股风险区分与异质性误差；不是独立可交易目标。结合月内AUC/AP判断，不能把单纯市场发生率变化当个股识别。

'''+md(ab[ab.metric.isin(['common_brier','relative_brier'])][['candidate','baseline','metric','estimate','low95','high95']])+'''
市场状态M_VFS相对M_VF的AP有探索性改善，Brier却退化且区间跨0，说明排序和概率水平不是同一性质的优势。旧EP25分布的D_VF−D_R及直接M_R−D_R区间保留在paired_intervals.csv：不能用D_VF相对B1的小幅改善宣称新增因子已验证，也不能宣称直接分类天然优于分布推导。

## 456天信息陈旧的条件结果

'''+md(conditional[(conditional.threshold==20)&conditional.dimension.eq('age_group')&conditional.model.isin(['M_R','M_F','M_VF'])][['model','condition','rows','events','months','brier','auc','bias']])+'''
<=365天组只有2个可评分月份，新增财报模型在该组明显高估概率；样本过少且分布变化大，既不能宣布更新财报无效，也不能把这些行排除以改善整体结果。这里暴露模型/信息时点的适用边界。未追加其他特征组、窗口或参数。
''')
    rank=s[['model','auc','pr_auc','enrichment10','enrichment20','recall10','recall20','fpr10','fpr20','auc_months','pr_auc_months']]
    deciles=risk_deciles()
    save('tail_risk_ranking.md','''# EP26 重大亏损风险区分

AUC/AP均先按同一预测月计算，再等权平均，避免把“某年全市场都差”误称个股排序。PR-AUC采用average precision阶梯积分，非梯形PR曲线面积；参照事件率17.0665%（月等权），pooled发生率另列。没有正类的月份AP记NA、单类月份AUC记NA，并保留有效月份数。

'''+md(rank)+'''
最高10%/20%组在全部当前预测人群上形成，先分组再观察结果；未来缺失不影响排序选择。并列用固定股票代码哈希破除，不使用结果。B0常数概率的分组只是固定随机对照，其偶然富集不代表区分力。enrichment是每月组内发生率/全池发生率再等月平均；recall分母为全部已知重大亏损；FPR分母为全部已知非重大亏损。FPR低不等于高风险预警大多数都会亏损，precision另存monthly_scores.csv。

基础风险排序确有历史信号：B1月内AUC约0.668、D_R约0.673、直接M_R约0.674，高风险20%约1.7倍富集。但这主要来自波动/市值，不是新增V/F的证明。M_VF AUC相对M_R增量区间跨0，且最高20%召回率约34.9%，略低于M_R的35.1%。风险排序不能替代概率校准。

![同月风险排序与富集](outputs/risk_ranking.png)

风险十分位的全部行数、事件数、覆盖月份、预测与实际频率见outputs/risk_deciles.csv；逐月记录见risk_decile_monthly.csv。Pooled AUC/AP见pooled_metrics.csv，只作市场共同变化混杂诊断，不作为主检验。

辅助阈值10%/30%全部模型结果见summary.csv、paired_intervals.csv和calibration.csv；不以表现最好阈值替换20%。不同收益位置的结果说明尾部结构，而非提高普通分类accuracy或收益Rank IC。
''')
    chosen=cal[(cal.threshold==20)&cal.model.eq('M_VF')&cal.dimension.eq('all')&cal.block.eq(6)]
    q=pd.read_csv(OUT/'quantile_coverage.csv').groupby('model')[['cover05','cover10']].mean().reset_index()
    save('probability_calibration.md','''# EP26 概率校准与条件可靠性

本轮没有测试后拟合校准器，直接检查冻结原始概率。所有结果仅探索性，概率未标为独立可信。总体预测均值接近总体发生率，并不证明条件校准。

'''+md(bias[(bias.threshold==20)&bias.block.eq(6)][['model','estimate','low95','high95','months']])+'''
联合模型整体偏差约−0.0654个百分点，但2021–2023低估约7.06个百分点、2024以后高估约10.88个百分点，误差被跨阶段平均抵消。上涨趋势与非上涨趋势、市场高/低波动也有不同偏差；历史排序较好仍会系统性误报概率水平。

'''+md(conditional[(conditional.threshold==20)&conditional.model.isin(['M_R','M_VF','M_VFS'])&conditional.dimension.isin(['phase','regime','vol_regime'])][['model','dimension','condition','rows','events','months','base_rate','bias','brier','auc']])+'''
## 主模型概率桶与偏差区间

'''+md(chosen[['probability_bin','rows','events','covered_months','predicted','observed','bias','bias_low95','bias_high95','evidence']])+'''
固定宽度0.1桶，bin=3表示[0.3,0.4)。表的predicted/observed按每月总体等权定义，在桶内重归一；95%区间使用完整59月日历整月bootstrap，桶缺席月权重为零，不将其当成零事件。所有模型、辅助阈值、年份/市场状态/财报年龄的桶结果在calibration.csv，另有L12敏感性。小于6个覆盖月份标descriptive sparse，即使数千股票也不升级可信。确认性范围标准另见validation_protocol.md。

![亏损概率可靠性](outputs/reliability_loss20.png)

![阶段校准漂移](outputs/calibration_by_phase.png)

## 5%与10%收益分位辅助

'''+md(q)+'''
直接事件分类器的三个概率不能唯一识别收益分位数，所以M_*的Q05/Q10明确为空，不伪造分位输出。这里复用冻结历史/近邻/EP25分位树，理想覆盖分别5%/10%；有限原子/端点截断和未解决退市口径仍限制解释。分位覆盖近名义水平不能替代条件概率可靠性。

25条到期缺失记录可能集中于坏结果；missing_brier_bounds.csv给出每模型最有利/最不利二元结果的Brier界限。不能对未来ST剔除的整个池外人群给出伪精确校准保证。
''')
    ptable=portfolio[['strategy','cost_bps','cumulative_return','annual_return','annual_vol','sharpe_zero_cash','max_drawdown','daily_es05','monthly_es05','mean_equity_fraction','maximum_stale_fraction','turnover_total_nav_multiple','transaction_cost_nav_multiple']]
    attr=indattr.groupby(['comparison','metric'])[['total_difference','industry_allocation','within_industry_residual']].mean().reset_index()
    save('portfolio_risk_test.md',f'''# EP26 风险过滤辅助组合对照

这是风险管理研究代理，不是可执行交易或独立科学确认。S0固定哈希等权基础子池，S1按直接M_R过滤，S2按M_VF过滤；每月板块×规模三分位×波动三分位中排除floor(20%n)，三组各层目标持股数完全相同、目标股票总仓位100%。原池全部预测人群决定名单，不按未来标签或是否缺价筛股票。因各层floor，实际过滤比例略少于20%，三组数量相同。

真实动态辅助曲线使用月末预测、下一交易日收盘成交，避免同收盘信息提前成交。前复权单位模拟，先卖后买、双向10bp及30bp成本，现金守恒；缺报价不能成交，已有持仓按最后可见价估值并记录陈旧风险。未精确模拟真实分红/退市结算、涨跌停、税费和整手。收益源截至2026-05-29，1287个市场交易日，约2021-02至2026-05。

'''+md(ptable)+f'''
实际股票仓位均接近100%，最大同日组间差{paudit['maximum_daily_equity_fraction_difference']:.4%}，在预设1个百分点内，低仓位不是主要比较来源。目标持股数/层计数严格相同；实际报价失败可能造成微小持股数差，portfolio_daily.csv保留每日实际数。不能只凭总仓位接近就宣称风险暴露完全相同。

ES为最差5%样本收益均值，越不负越好。S2最大回撤略优于S1，但日ES更差（−2.6343%对−2.5820%）；月ES和累计收益较好。这些指标不是同一个尾部优势，不能只挑回撤或月ES。全部月收益ES及6月固定名单ES差的整月块区间见portfolio_es_intervals.csv。

## 持有重大亏损股票与配对增量

以下为预测日固定等权名单的6月标签诊断，与按月调仓曲线区分；cohort_return不是提前可得的可交易结果。

'''+md(cohort.groupby('strategy')[['loss20_rate','cohort_return','stock_tail_es05','missing']].mean().reset_index())+md(pci[pci.block.eq(6)][['comparison','metric','estimate','low95','high95','months']])+'''
S1相对S0持有重大亏损率下降约0.8265个百分点；S2相对S0下降约1.2973个百分点。但S2−S1仅约−0.4708个百分点，L6区间[-0.9553, +0.0006]个百分点跨0，L12区间低于0。既定主块长未提供稳健新增信息优势，不能事后挑L12。

## 市值、波动、行业与市场暴露

'''+md(exposure.groupby('strategy')[['log_cap_standardized_vs_s0','vol63_standardized_vs_s0','industry_total_variation_vs_s0','industry_unknown_fraction','industry_stale_fraction']].mean().reset_index())+md(beta)+'''
分层计数完全匹配，连续风险变量仍有残差；S1比S2降低的历史波动更多。实现CSI300 beta只作事后归因，不是训练信号。行业权重总变差和逐行业权重保留在portfolio_exposures.csv、portfolio_industry_weights.csv；分类未知/陈旧的影响不隐藏。

'''+md(attr)+'''
行业分解使用同月原池行业平均结果：总差=行业配置项+行业内残差。S2−S1事件率下降中约0.2676个百分点来自行业配置，占总差约57%；行业内残差约−0.2032个百分点，完整区间见portfolio_attribution_intervals.csv。该恒等诊断不建立行业因果识别，且受缺失/陈旧行业与收益影响。

## 换手成本与机会成本

双边成交额/NAV累计和交易成本在主表；30bp结果全部保留，未通过长期现金回避风险。排除股票的后续收益和大涨机会如下，不因其“高风险”而省略上涨机会：

'''+md(opportunity.groupby('strategy')[['excluded_mean_return','excluded_gain20_rate','selected_mean_return']].mean().reset_index())+'''
陈旧估值最高约1%的资产仍可隐藏真实损失，退市和特殊公司行动未解决；行业中性也未严格达到。因此历史过滤相对S0减少重大亏损暴露可作探索性线索，尚不能证明新增V/F在维持严格可比市场风险暴露后创造稳定尾部经济价值。组合表现不替代概率模型主检验。

![风险过滤辅助净值与回撤](outputs/portfolio_curves.png)
''')
    controls=pd.DataFrame([dict(control=x['control'],metric='Brier model-constant' if x['control']=='known_binary_probability' else 'AUC-0.5',passed=x['passed'],estimate=x['estimate'],low95=x['low95'],high95=x['high95'],monthly_auc=x['monthly_auc']) for x in control['controls']])
    save('final_conclusion.md',f'''# EP26 最终结论

**发现了历史基础风险排序能力及少量估值排序线索；未验证新增估值与财报信息带来稳定、可校准且具有独立经济价值的重大亏损概率优势。全部发现仍属历史探索，尚未独立前瞻确认。**

主要事件为6个月R<−20%，与EP25完全一致。主比较是直接分类M_VF−直接M_R，不把旧分布模型改算法当新增信息。

## 1. 能否预测重大亏损概率？

能够输出逐股概率，并在历史上区分部分风险高低；不能把这些概率标为普遍可靠。风险/市值近邻B1的Brier={risk.brier:.6f}、月内AUC={risk.auc:.6f}；同算法风险分类M_R的Brier={base.brier:.6f}、AUC={base.auc:.6f}。它们优于常数风险排序，而跨阶段概率水平明显漂移。

## 2. 哪些信息产生增量？

联合模型Brier={joint.brier:.6f}，Delta={primary.estimate:.6f}，95%月份块区间[{primary.low95:.6f}, {primary.high95:.6f}]；相对改善{primary.relative_improvement_percent:.3f}%（误差略增），不支持主假设概率质量改善。

估值单独M_V的AUC={val.auc:.6f}，相对M_R增加约0.016973，未调整95%区间略高于0；但Brier改善约0.97%的区间跨0，AP增量也跨0。这是待验证的排序线索，不是稳定概率优势。加入陈旧财报未改善主检验；市场状态交互改善部分AP，整体Brier却更差。所有候选保留，没有扩展搜索。

## 3. 超越传统风险因子的证据如何？

基础高风险20%约1.7倍富集主要已由波动/市值识别。M_VF的AUC和AP对M_R的区间跨0，高风险20%召回约34.9%、并未高于M_R约35.1%。共同偏差Brier与横截面中心化误差分开评价；不能把市场基础发生率变化解释为个股识别。有限的估值AUC线索不能独立验证其超越传统风险的稳定性。

## 4. 概率可靠吗，何时失效？

M_VF整体平均偏差约−0.0654个百分点，但2021–2023低估约7.06个百分点、2024以后高估约10.88个百分点；总体相抵不等于条件校准。趋势/波动状态也存在偏移。财报年龄中位456天；最新≤365天组在成熟样本中仅769条、2个月，模型在该小组高估明显。陈旧版本和新鲜度分布变化限制财报结论，不能以最新下载历史替代原始披露。

## 5. 可比暴露下能降低组合尾损吗？

三组目标仓位和各风险/市值/板块层持股数相同，实际仓位差很小。S1/S2相对S0历史持有重大亏损率下降，但S2−S1的约−0.4708个百分点增量对块长敏感；约57%总差可由行业配置诊断解释。S2回撤/月ES较好，日ES却比S1差，仍有行业、连续风险、陈旧报价和完整收益口径残差。尚不能确认新增信息在严格可比暴露后创造稳定尾部经济价值；也没有靠低仓位制造成功。

## 6. 哪些支持，哪些不足？

历史探索支持“基础风险变量有一定排序能力”和“估值存在局部AUC线索”；不支持本次联合概率模型稳定优于同算法风险基线。估值Brier、财报增量、概率条件校准、组合新增价值与独立前瞻确认仍证据不足。不能推论市场不可预测或任何财报信息永远无效。

有效{audit['scorable_rows']:,}股票月、{audit['events']:,}事件、59个重叠起点仅约9.8个6月块。主要配对80%近似可检测幅度{primary.detectable_80pct_effect_approx:.6f}，对预设0.002幅度近似功效{power:.1%}，不足以精确排除小增量。未来ST筛选、历史估值/财报原始版本、退市/停牌/公司行动和25条已到期缺失可能使左尾漏计。历史已被多轮选择，不能当独立留出。

## 控制、停止与交付

'''+md(controls)+'''
二元正控制恢复平均条件概率，月内真实标签置乱保留每月事件率且AUC区间覆盖0.5；EP25原控制通过记录保留并核验哈希。330次正式分类拟合全部完成（5候选×3阈值×22季度），另有预指定控制拟合；辅助10%/30%、分位覆盖、匹配消融、年份/状态、可靠性、风险分层与组合对照齐备。

旧EP24/EP25记录与结论保持原字节。全部原子/模型/预测有本地哈希收据；代码、报告、测试与汇总按README的GitHub交付范围发布，最终远端提交以本次会话发布回执为准。详细完成证据见completion_audit.md、outputs/validation.json。无新前瞻样本，只有冻结与追加流程；至少36起点、事件数/事件月份及功效门槛后才作一次计划内确认。

预注册候选和消融已完成，停止增加模型、改阈值、挑年份或调参数。负面与证据不足构成完整交付，不以正结果作为Goal完成条件。
''')
    # Figures are standalone artifacts, all from existing scores.
    colors={name:plt.get_cmap('tab10')(i) for i,name in enumerate(['B0','B1','D_R','M_R','M_V','M_F','M_VF','M_VFS'])}
    fig,axes=plt.subplots(1,2,figsize=(12,5),layout='constrained')
    for name,color in colors.items():
        t=cal[(cal.threshold==20)&cal.model.eq(name)&cal.dimension.eq('all')&cal.block.eq(6)].sort_values('predicted')
        axes[0].plot(t.predicted,t.observed,'o-',label=name,color=color,markersize=3)
    axes[0].plot([0,1],[0,1],'--',color='grey');axes[0].set(xlabel='Predicted loss20 probability',ylabel='Observed frequency',title='Month-weighted reliability',xlim=(0,1),ylim=(0,1));axes[0].legend(fontsize=8)
    t=chosen;axes[1].bar(t.probability_bin.astype(str),t.rows,color=colors['M_VF']);axes[1].set(xlabel='Fixed probability decile bin',ylabel='Known stock-months',title='M_VF bin support (not independent cases)')
    fig.savefig(OUT/'reliability_loss20.png',dpi=160);plt.close(fig)
    fig,ax=plt.subplots(figsize=(10,5),layout='constrained')
    for name in ['B1','M_R','M_VF','M_VFS']:
        t=conditional[(conditional.threshold==20)&conditional.model.eq(name)&conditional.dimension.eq('year')].sort_values('condition')
        ax.plot(t.condition,t.bias,'o-',label=name)
    ax.axhline(0,color='grey',linestyle='--');ax.set(xlabel='Origin year',ylabel='Predicted minus observed probability',title='Calibration drift; exploratory already-viewed history');ax.legend();ax.grid(alpha=.2)
    fig.savefig(OUT/'calibration_by_phase.png',dpi=160);plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(12,5),layout='constrained')
    for name in ['B0','B1','M_R','M_V','M_VF','M_VFS']:
        t=deciles[deciles.model.eq(name)];axes[0].plot(t.decile,t.observed,'o-',label=name)
    axes[0].set(xlabel='Within-month risk decile (1 low, 10 high)',ylabel='Observed loss20 frequency',title='Risk groups assigned before observing labels');axes[0].legend(fontsize=8)
    show=s[s.model.isin(['B0','B1','D_R','M_R','M_V','M_VF','M_VFS'])];axes[1].bar(show.model,show.enrichment20);axes[1].axhline(1,color='grey',linestyle='--');axes[1].set(ylabel='Mean monthly enrichment',title='Highest-risk 20%');axes[1].tick_params(axis='x',rotation=45)
    fig.savefig(OUT/'risk_ranking.png',dpi=160);plt.close(fig)
    daily=pd.read_csv(OUT/'portfolio_daily.csv',parse_dates=['date']);fig,axes=plt.subplots(2,1,figsize=(11,7),sharex=True,layout='constrained')
    for strategy in ['S0','S1','S2']:
        t=daily[daily.strategy.eq(strategy)&daily.cost_bps.eq(10)];axes[0].plot(t.date,t.nav,label=strategy);axes[1].plot(t.date,t.drawdown,label=strategy)
    axes[0].set(ylabel='NAV',title='Qfq-unit auxiliary simulation, 10bp each side');axes[0].legend();axes[1].set(ylabel='Drawdown',xlabel='Date');fig.savefig(OUT/'portfolio_curves.png',dpi=160);plt.close(fig)
    write_json(OUT/'conclusion_status.json',dict(overall='INSUFFICIENT_EVIDENCE_FOR_STABLE_INCREMENTAL_PROBABILITY',primary_delta=primary.estimate,primary_ci95=[primary.low95,primary.high95],
        independent_confirmation=False,primary_probability_advantage_supported=False,historical_basic_risk_ranking_supported=True,valuation_ranking_hint_exploratory=True,
        robust_incremental_economic_advantage_confirmed=False,stopped_after_preregistered_candidates=True))
    print((EP/'final_conclusion.md').read_text()[:2200],flush=True)

if __name__=='__main__':main()
