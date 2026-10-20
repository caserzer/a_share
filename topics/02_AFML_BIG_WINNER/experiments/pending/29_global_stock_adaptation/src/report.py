"""Write bounded interpretations of the completed frozen experiments."""
from common import *
from presentation import table


def main():
    report=EP/'reports'
    s=pd.read_csv(OUT/'summary.csv');iv=pd.read_csv(OUT/'paired_intervals.csv')
    metric_coverage=pd.read_csv(OUT/'monthly_scores.csv').groupby(['foundation','population','model'])[
        ['brier','auc','pr_auc','industry_auc','recall5','recall10','recall20']].count().reset_index()
    metric_coverage.to_csv(OUT/'metric_coverage.csv',index=False)
    phase=pd.read_csv(OUT/'phase_intervals.csv');company=pd.read_csv(OUT/'company_scores.csv')
    aux=pd.read_csv(OUT/'auxiliary_intervals.csv');coverage=pd.read_csv(AUDIT/'cohort_eligibility_coverage.csv')
    fallback=pd.read_csv(OUT/'fallback_accounting.csv');corrections=pd.read_csv(OUT/'corrections.csv')
    strict=pd.read_csv(OUT/'strict_local_monthly.csv').groupby(['population','model'])[['brier','extreme_probability_fraction','oracle_MSE']].mean().reset_index()
    strict_ci=pd.read_csv(OUT/'strict_local_intervals.csv')
    cohort=json.loads((EP/'configs/target_cohort.yaml').read_text());stock=cohort['single_stock']
    for foundation in ['M_R','L2']:
        annotated=pd.read_parquet(CACHE/f'annotated_predictions_{foundation}.parquet')
        annotated[annotated.instrument.isin([r['instrument'] for r in cohort['companies']])].to_csv(
            EP/f'outputs/predictions/cohort40_{foundation}.csv',index=False)
    single=pd.read_csv(EP/'outputs/predictions/single_stock_M_R.csv',parse_dates=['date'])
    def get(a,b,foundation='M_R',population='D0',block=6,weighting='month'):
        return iv[(iv.foundation==foundation)&(iv.population==population)&(iv.candidate==a)&(iv.baseline==b)&(iv.block==block)&(iv.weighting==weighting)].iloc[0]
    def estimate(r):return f"{r.estimate:+.8f}，95%区间[{r.low95:+.8f}, {r.high95:+.8f}]"
    def save(name,text):(report/(name+'.md')).write_text(text.strip()+'\n')
    main6=get('GPI','G');main12=get('GPI','G',block=12);gi=get('GI','G');marginal=get('GPI','GP')
    primary=s[(s.foundation=='M_R')&(s.population=='D0')&s.model.isin(C['formal_models'])]
    peer_counts=fallback[(fallback.foundation=='M_R')&fallback.dimension.eq('peer_reason')]
    peer_intervals=iv[(iv.foundation=='M_R')&(iv.population=='D0')&(iv.weighting=='month')&iv.candidate.isin(['GP','GPI'])&iv.baseline.isin(['G','GI','GP'])]
    peer_ranking=pd.read_csv(OUT/'peer_pair_intervals.csv')
    save('peer_similarity',f"""
# 同行迁移与个股边际贡献

全D0同行修正没有显示总体概率优势。GP−G：{estimate(get('GP','G'))}。加入公司自身历史后GPI−GP：{estimate(marginal)}，约改善GP Brier的{marginal.relative_improvement_percent:.4f}%。这是一条极小的历史个股信息线索，不能解释成同行迁移整体有效或独立确认。

同行只由预测时点的历史行业、log市值、63日波动、市场/行业Beta及特质波动形成。横截面中位数/IQR标准化、等权距离、±5截断；同业最近15家且至少5家，否则同大类30家且至少10家，再不足回退全局。目标自身排除，过期/未知行业或缺特征不构造同行。历史成员需身份匹配且至少21个成熟月、5家有历史同行。没有未通过PIT审计的财务或估值字段。

同行MAP先验sd=.75、修正±1；每历史月份总似然权重1/7。历史共同截距只处理成熟过去的残差，不使用当前未知发生率。当前成员及距离保存在各起点`*_peers.parquet`；单股公开链见 [single_stock_peers.csv](../outputs/predictions/single_stock_peers.csv)。全量链留本地，SHA见缓存清单。

## 所有64预测月的同行路径计数（含尚未到期行）

{table(peer_counts[['reason','predictions','known','events','mean_abs_probability_change']])}

其中概率变化列是最终GPI相对G的变化，不能单独归因同行。同行与公司修正的纯净贡献用下面同样本消融区分。

{table(peer_intervals[['candidate','baseline','block','estimate','low95','high95','low_secondary','high_secondary']])}

## 实际同行之间的风险区分

已冻结同行配对中，仅比较目标与同行结局不同的有向对，较高事件概率排序正确记1、并列0.5。重复配对不视作独立观测，整月块重采样。此为后加的描述性评分；59成熟日历位置保留，只有44月存在有效同行配对，不把缺口压缩成连续44月。

{table(peer_ranking[(peer_ranking.foundation=='M_R')&(peer_ranking.population=='D0')&(peer_ranking.block==6)][['candidate','baseline','estimate','low95','high95','months']])}

正差值表示排序改善，与Brier差值的方向相反。该诊断未纳入初始检验家族，不能用它挑选新模型。同行业AUC、实际同行配对一致率与整体横截面AUC回答不同问题；不能互相替代。全部同行结果受历史行业快照、D0选择和短历史限制。
""")
    control=json.loads((AUDIT/'synthetic_controls.json').read_text())
    control_rows=[dict(world=w['world'],comparison=k,**v) for w in control['results'] for k,v in w['contrasts'].items()]
    identity=json.loads((AUDIT/'identity_control.json').read_text())
    uncertainty=pd.read_csv(OUT/'synthetic_uncertainty.csv')
    save('shrinkage_validation',f"""
# 收缩、控制与过拟合

固定正控制、零附加效应控制和身份置乱均通过预定管道检查。通过控制只证明方法能在构造世界中工作、未制造指定容忍度外的假优势，不证明真实A股存在相同机制。

## 正负合成世界

120家公司、180个月、最后60月评价，固定种子；以6月共享事件块制造重叠，部分公司仅在评价前12月进入。它是二元事件控制世界，不是完整价格路径/公司行动模拟。

{table(pd.DataFrame(control_rows)[['world','comparison','estimate','low95','high95']])}

正世界中，适配公司偏移与真实个体效应相关0.5515；稀少历史公司的同行oracle MSE改善0.011898。零世界反而有GPI Brier损失约0.001406，且仍有1,676行触发个股适配：收缩没有消灭噪声拟合。不能只展示正控制而忽略这种成本。

零事件公司在两个世界分别有698和833条评价行，个股修正均回退0，正式概率保持内部值。首末时间段持久性、至少两个不重叠事件/非事件窗、21成熟月及训练内tau共同控制适配；这些窗口并不等于经济上独立事件。

## 无修正、强收缩、训练内收缩、弱先验与严格无收缩

原注册`L_unshrunk`实际上是Jeffreys(.5,.5)弱平滑，不能冒称严格无收缩。另在真实适配/评分前登记`L_MLE`补足目标要求：同一成熟历史的事件数/月份数，无先验，仅数值clip；无历史回退G。它是诊断，不是新增正式候选。

{table(strict[strict.population.isin(['D0','cohort40','synthetic_positive','synthetic_zero'])])}

无收缩在D0约26.5%的月份等权预测进入<1%或>99%的极端区间；GPI正式预测未出现这种极端。D0中部分池化比无收缩局部模型明显稳健，但40公司队列中L及弱先验的点估计反而较好，不能说分层模型普遍胜出。

{table(strict_ci[(strict_ci.block==6)&strict_ci.population.isin(['D0','cohort40'])][['population','candidate','baseline','estimate','low95','high95']])}

训练内收缩与固定强收缩的D0差异：{estimate(get('GPI','GPI_strong'))}。不据此重新选择tau或改候选。

## 身份置乱

同日期×行业×市值/波动中位数组内一次固定置乱，特征、标签及G概率整行保留；实际改变身份69.23%，小组不能充分置乱，故是部分身份持续性破坏。

{table(pd.DataFrame(identity['comparisons']).query('block == 6')[['comparison','estimate','low95','high95']])}

没有稳定的虚假个股优势。但这不能证明真实公司效应为零，保留的行业/市场结构仍可有信息。

## 不确定性与真实回退

{table(uncertainty)}

上述潜在效应区间覆盖只是人工世界下、触发适配行的近似检查；正世界约93.6%，低于名义95%，零世界100%也不能认证真实覆盖。实际输出的个股区间条件于G、同行和tau；它不是包含数据版本、市场非平稳和超参数误差的完整概率区间。回退标为[0,1]，明确表示缺乏可用个股置信范围。

{table(fallback[(fallback.foundation=='M_R')&fallback.dimension.eq('individual_reason')][['reason','predictions','known','mean_history_months','mean_effective_months']])}
""")
    case=company[(company.foundation=='M_R')&company.instrument.eq(stock)]
    c=case[case.model=='G'].iloc[0];cpi=case[case.model=='GPI'].iloc[0]
    path=single[['date','G','GP','GI','GPI','L','actual','individual_months','nonoverlap_events','peer_offset','individual_offset_GP']].copy()
    path['date']=path.date.dt.strftime('%Y-%m-%d')
    save('single_stock_case',f"""
# {stock}：完整单股案例

选择理由是首起点D0内上市日期最早，代码破并列，未看未来收益或模型成绩。当前显示名称万科A不参与模型，也没有假定其业务稳定。

64个预测月中59个已知到期结果，27个重大亏损标签；合并为5个风险区间阶段，贪心可取7个不重叠事件窗口、全标签9个不重叠窗口。阶段/窗口也不等于独立经济事件，不能把27个重叠标签视作27次独立危机。

GPI Brier {cpi.brier:.6f}，G {c.brier:.6f}，差{cpi.brier-c.brier:+.6f}。历史事件率{c.events/c.months:.2%}，GPI平均预测{c.events/c.months+cpi.bias:.2%}，仍明显低估。个股修正小幅改善不能使这条概率成为可靠赔率。

{table(case[['model','months','events','risk_stages','nonoverlap_events','brier','bias','temporal_auc']])}

这里的temporal AUC是单股跨月份排序，区别于市场月内横截面AUC。所有单股统计区间仅作描述；总体只有少数风险阶段，未作单股显著性或因果宣称。L等更简单历史率在本例点估计更好，不能隐藏。

![完整概率路径](figures/single_stock_path.png)

图中阴影只在触发个股适配时显示固定G/同行后的条件区间；其余回退行完整范围[0,1]留在CSV。每条概率附当时成熟历史的G/GP/GI/GPI/L偏差、Brier/ECE、首末起点、最大到期日及历史有效范围，见 [完整预测CSV](../outputs/predictions/single_stock_M_R.csv)。L2同路径亦公开。历史校准本身也只有少量有效样本，不是验证保证。

## 全部预测月份

`actual`为实际收益，NA表示尚未到期或缺失，不是零收益/无事件。个股计数只包含当时已经成熟的OOS历史；1/7权重不是严格独立样本量。

{table(path)}
""")
    cohort_iv=iv[(iv.foundation=='M_R')&(iv.population=='cohort40')&(iv.candidate=='GPI')&(iv.baseline=='G')]
    g=company[(company.foundation=='M_R')&company.model.eq('G')].set_index('instrument')
    a=company[(company.foundation=='M_R')&company.model.eq('GPI')].set_index('instrument')
    delta=a.brier-g.brier;others=delta.drop(stock)
    save('cross_stock_validation',f"""
# 跨公司验证及适用边界

40家公司在2021-01-29原D0起点冻结，跨39行业，按行业/市值轮转抽样；不按事件数或结果替换。后续只使用原D0出现的月份，没有伪造连续公司历史。

队列共901预测行、866已知标签、1成熟缺失、34未到期；相对40×64潜在公司月，有1,659个不在原D0的公司月。已知覆盖中位数11.5个月，20家公司不足12月、26家不足24月，仅8家至少48月。40不是40份完整独立时间序列。

## 权重改变会改变答案

{table(cohort_iv[['weighting','block','estimate','low95','high95','relative_improvement_percent']])}

月份等权GPI−G为{get('GPI','G',population='cohort40').estimate:+.6f}，但公司等权为{get('GPI','G',population='cohort40',weighting='company').estimate:+.6f}，公司簇×时间块区间跨零。稀疏队列后期月份更多由长历史公司决定；不能把月份等权改善推广成“典型公司改善”。

代码排序的全部40家公司与各自阶段/事件数见 [结果全表](result_tables.md)；按1e−12数值容差，{int((delta < -1e-12).sum())}家点估计改善、{int((delta > 1e-12).sum())}家变差、{int((abs(delta) <= 1e-12).sum())}家相同。不按这些结果筛选成功样本。剔除事前单股后其余39家**公司等权描述性**差值{others.mean():+.6f}，不能声称单股优势在其他公司普遍复制；此补充会计不增加正式检验。

## 事前分组和阶段

{table(phase[(phase.foundation=='M_R')&(phase.candidate=='GPI')&(phase.baseline=='G')&(phase.block==6)][['population','phase','months','estimate','low95','high95']])}

全D0 2021–2023较差、2024以后较好。短历史及少事件公司经常回退，较长历史才可能产生个股信息。上市年龄、事件窗口、行业稳定性和市场状态的所有结果均公开在`conditional_summary.csv`及结果全表，不只展示有利组。它们是事前已知条件，但组间不是随机实验，不能解释为公司年龄或行业造成收益风险变化。

各组的月均是各自可评价月份等权，组份额随月份变化，因此不能直接把组均值相加还原总体。40股几乎每行业一家公司，严格同月行业AUC没有足够覆盖，保留NA；整体横截面和实际同行配对的排序另列，不能代替缺失的同业群体证据。
""")
    calcols=['model','brier','predicted','base_rate','bias','ece','auc','pr_auc','industry_auc','industry_coverage','recall5','recall10','recall20','enrichment5','enrichment10','enrichment20']
    ca=aux[(aux.foundation=='M_R')&(aux.population=='D0')&(aux.candidate=='GPI')&(aux.baseline=='G')&(aux.block==6)]
    save('calibration_report',f"""
# 概率可靠性、排序与尾部识别

GPI没有同时改善绝对概率、排序与尾部识别。主M_R月内AUC由0.673902降到0.670218；同行业AUC也下降。平均概率偏差缩小，但各月共同Brier误差没有相应稳定改善，不能以整体偏差接近零声称校准可靠。

{table(primary[calcols])}

概率误差为预测减真实事件率。ECE使用事前固定0.1箱，先每月算再平均；可靠性图是同样月等权下跨月聚合的箱均，可能掩盖市场状态漂移，因此必须同时看月度ECE和状态表。PR-AUC要连同基础发生率阅读；没有事件的月份相关召回/PR指标为NA，不零填。

有效月份数：全D0 Brier/整体AUC/PR为59月，同业AUC为56月；40公司Brier为59月，AUC/PR/事件召回只有46月，同业AUC为0月。每模型逐字段计数另见`metric_coverage.csv`，这些不同覆盖的指标不能无条件横比。

![可靠性图](figures/reliability.png)

## 配对辅助差异（GPI−G，6月块；描述性）

{table(ca[['metric','estimate','low95','high95']])}

Brier在每月可精确拆为平均概率偏差平方`common_brier`与中心化横截面误差`relative_brier`。这里两个分量的差值合为总差值，但这是误差会计，不是因果贡献。总体均值偏差改善与均方共同误差改善不是同一件事。

5%预警召回/富集有小幅历史改善，10%预警反而下降，20%接近不变；没有跨所有阈值稳定的尾部识别优势。5%、10%、20%名单都在当月全D0形成，子队列沿用；不能事后选择最好比例作为主结论。误报/漏报数量和各月覆盖保留在`monthly_scores.csv`。

L2的同样五模型见结果全表；GPI Brier也变差，平均概率低估加深，不能以L2增强基线掩盖M_R主比较。单股万科A的GPI均值仅约15.9%，同期重叠事件率约45.8%，说明全体平均校准远不能保证目标公司的风险概率可信。

每条公开单股概率附当时已知的历史校准和样本范围。个股MAP区间仅条件于固定全局/同行/tau，缺少参数及版本等不确定性，回退行[0,1]明确无可用个股置信范围。这里没有经独立新样本验证的实盘赔率。
""")
    leave=pd.read_csv(OUT/'leave_out.csv')
    leave=leave[(leave.foundation=='M_R')&(leave.population=='D0')&(leave.candidate=='GPI')&(leave.baseline=='G')]
    bounds=pd.read_csv(OUT/'missing_bounds.csv');bounds=bounds[bounds.foundation=='M_R']
    save('statistical_validation',f"""
# 统计验证及研究有效性

主结果：月份等权GPI−G {estimate(main6)}；12月块为{estimate(main12)}。相对Brier变化为恶化{abs(main6.relative_improvement_percent):.4f}%，没有支持联合适配优于主要全局基线。

全部比较对齐相同股票、预测日和收益标签；先逐月汇总，固定5,000次stationary bootstrap，种子2901，平均块长6及12月。每次完整抽取该月横截面并保留公司随块的时间轨迹；主比较另报告公司簇×时间块抽样。没有逐股票月独立抽样。

{table(iv[(iv.population=='D0')&(iv.candidate=='GPI')&(iv.baseline=='G')][['foundation','weighting','block','estimate','low95','high95','approximate_80pct_detectable_effect']])}

59成熟起点只有约9.83个6月块或4.92个12月块；弱平稳假设和少块近似有限。主比较80%检出量级约{main6.approximate_80pct_detectable_effect:.6f}（2.8×块SE），只是功效诊断，不是完成任务或接受假设的改善门槛。

## 个股历史的极小探索性信号

GI−G：{estimate(gi)}；GPI−GP：{estimate(marginal)}。月等权的6/12月块、原六项次要家族Bonferroni 99.1667%区间仍在零下，但上端非常接近零，公司等权家族校正区间跨零。历史区间反复用于多阶段研究，这种校正不覆盖EP24—EP28的研究选择，不能形成独立确认。

{table(iv[(iv.foundation=='M_R')&(iv.population=='D0')&(iv.weighting=='month')&(((iv.candidate=='GI')&(iv.baseline=='G'))|((iv.candidate=='GPI')&(iv.baseline=='GP')))][['candidate','baseline','block','estimate','low95','high95','low_secondary','high_secondary']])}

五项主消融加L2 GPI−G组成六项家族；其他L2消融、40公司层次、条件分组、强/弱/严格局部诊断均是描述性。数值表中的`low_secondary/high_secondary`统一生成，不表示每个展示行均属于已注册六项家族；只对家族指定比较使用确认式措辞。没有把方向命中、某个最佳年份或后加同行排序当作新主指标。

## 阶段与单月敏感性

{table(phase[(phase.foundation=='M_R')&(phase.population=='D0')&phase.candidate.isin(['GI','GPI'])&phase.baseline.isin(['G','GP'])&(phase.block==6)][['candidate','baseline','phase','estimate','low95','high95']])}

删除任一月份后主差值范围[{leave[leave.removal=='month'].estimate.min():+.6f}, {leave[leave.removal=='month'].estimate.max():+.6f}]，仍较差；删除一个年份范围[{leave[leave.removal=='year'].estimate.min():+.6f}, {leave[leave.removal=='year'].estimate.max():+.6f}]，可变号。个股边际修正主要在2024以后有信息，早期几乎为零，不能称跨阶段稳定。完整删除记录不做选择性删年主分析。

25条成熟缺失加入共同目标后的月份等权配对极值界为[{bounds.lower.mean():+.6f}, {bounds.upper.mean():+.6f}]，不是统计CI，也不能修复退市结算或原池选择偏差。

## 工程与控制证据

32项自动测试包括成熟标签、当前/未来结果不变性、同行不看结果、解析MAP/收缩、重叠事件计数、评分权重、Brier分解及前瞻日期/追加标签。正控制恢复已知个股效应；零世界无假优势但有适配损失；身份置乱无稳定个股优势。各控制种子固定，没有重复搜索。

`validate.py`重新播放16个暖启动全局模型、44个继承季度基础概率，完整重算两个基础全部88起点的适配与同行，再核对月度评分、主比较全部权重区间、选股、原始列、来源和旧文件。最终机器回执为`outputs/audits/validation.json`；测试实录为`unit_tests_final.txt`。报告不以正效果作为验收条件。

极稀疏公司bootstrap可能出现全NA重抽样；保留日历缺口、丢弃无可评价重抽样，并在CSV报告有效抽样数。只有一两个有效起点的公司区间可能退化，不能据此作显著性宣称。固定pandas版本的空表concat提示不影响本轮数值，不能把未来版本兼容性视为已验证。

核心两项正确性修复与补充同行日历修复均保留原源码、旧输出和哈希链。没有以改善结果为由变更模型、标签、股票池、阈值、邻居、窗口或种子。
""")
    save('final_conclusion',f"""
# 最终结论：没有确认稳定、可迁移的联合适配优势

**在本研究的信息集与D0市场样本下，没有发现足以确认的稳定联合风险概率预测优势。** GPI相对M_R的主差值{estimate(main6)}，点估计恶化约{abs(main6.relative_improvement_percent):.3f}%；L2基础下联合适配也未改善主Brier。全部有限候选和控制完成后停止，没有继续搜索。

同时，不能把结果写成“公司历史完全没有信息”：GI−G约−0.000059、GPI−GP约−0.000055，月份等权的固定6/12月块次要家族区间在零下。这是极小、主要出现在2024以后的**探索性个股信号**，并未抵消同行修正的总体损失，也没有解决跨公司覆盖、校准及独立样本缺失问题。

## Q1：统一模型是否有可学习的公司偏差？

历史中有小幅线索：受约束公司修正的GI−G相对改善约{gi.relative_improvement_percent:.4f}%。删除单月/单年后点估计仍为负，但早期阶段近零、公司等权校正区间跨零，且全历史反复使用。支持继续观察这一机制，不支持已获得稳定普遍能力。

## Q2：同行是否提高风险预测质量？

全D0不支持：GP−G {estimate(get('GP','G'))}，Brier和整体排序点估计较差。40公司月份等权和后期有局部改善，不能取代总体主结果。历史行业可靠性、当前D0同行覆盖与残差非平稳均限制迁移。

## Q3：公司自身历史是否提供同行以外的信息？

有极小历史边际线索：GPI−GP {estimate(marginal)}，约改善0.0396%。正控制和身份置乱方向相容；这不是同行改善的同义词，也不是新的独立确认。正式模型没有因此更名、改规则或重新选冠军。

## Q4：分层收缩是否优于纯单股无收缩？

在合成稀疏世界和全D0，GPI明显比严格无收缩局部频率稳健；零世界仍产生额外误差，收缩并不消除过拟合。40公司队列及万科A中局部模型点估计反而更好，故不支持普遍支配。原弱Jeffreys与真正无收缩L_MLE分别报告。

## Q5：效果是否依赖历史、事件及市场状态？

是，存在描述性异质性。主GPI 2021–2023差约+0.000529，2024以后约−0.000373；公司边际信号主要在后期。短历史、少事件、行业陈旧等条件导致自动回退。所有预指定条件全列，不能以有利年份/行业定义新成功样本，条件关联也不是因果机制。

## Q6：稀少事件能否合理回退？

工程上支持：没有足够成熟月、两组不重叠事件/非事件窗、稳定方向或正tau就b=0；同行不足亦a=0。零事件公司未被正式模型赋予零风险。全D0约9%的全部预测行触发个股修正，说明多数预测时点不能支持本设计下的个性化。回退并不使G本身自动校准可靠。

## Q7：改善绝对概率、排序还是基础偏差？

联合模型整体Brier与月内/同业AUC没有改善；平均偏差缩小不等于每月共同误差改善。5%高风险尾部有小幅历史识别线索，10%下降、20%近乎不变。个股单独修正有微小Brier/部分排序线索，三种性质不能混称一个稳定预测优势。

## Q8：单股改善是否在其他预选股票复制？

证据不足。万科A GPI−G约−0.003670，但59个成熟标签只有5个合并风险阶段，平均风险仍严重低估。40公司月份等权差约−0.001434，公司等权却约+0.000471；其余39家公司等权描述性差约{others.mean():+.6f}。队列仅866已知股票月、半数公司不足12月，不能声称普遍复制。

## Q9：能否输出更可信的目标公司概率及不确定性？

能输出可追溯概率、同行、成熟历史、修正和条件区间；**尚不能证明比全局模型更可信**。万科A历史GPI均值约15.9%、事件率约45.8%，显示仍有重大校准缺口。条件MAP区间省略全局、同行、tau和数据版本不确定性；回退[0,1]表示无可用个股置信范围。未经验证的值不是实盘赔率。

## Q10：哪些结论还需要新样本？

本轮所有真实收益结果均为历史探索；只有构造世界的控制和计算一致性得到工程验证。稳定优势、真实公司可迁移性、全面校准以及经济意义都需冻结后的真正前瞻样本。EP27/28/29共享未来月份是同一市场证据，不是三次独立验证。本轮没有产生正式未来预测。

## 限制与停止决定

- **模型**：固定低维截距和持久性收缩可能过于受限，同行修正也可能迁移失败；本轮没有因负结果增加复杂度。
- **信息**：只含风险/市值、历史行业及成熟公司事件；不能推论未经PIT验证的财务、估值或其他信息必然无效。
- **数据**：原池/ST选择、历史行业版本、前复权与退市结算限制仍在；40公司后续D0覆盖稀疏。
- **检验能力**：59重叠成熟月、约5个12月块，主检出量级约0.001；小个股信号处于很小数量级，缺少独立新样本和跨公司稳健性。

**支持**：管道与回退在控制中有效；小幅历史个股边际线索；部分池化在部分样本中抑制纯局部过拟合。**不支持**：联合GPI已稳定优于全局G、同行普遍有益、已获得可直接使用的个股赔率。**证据不足**：独立确认、典型公司泛化、未纳入的信息与完全无偏市场总体。

前瞻规则与操作实现独立锁定，最早可能2026-10-30，必须当日真实生成并不可覆盖，六个月后追加共享源标签。历史补造不计前瞻。本轮工作完成取决于有限实验、审计、控制及归档完成，与是否得到正面结果无关。
""")
    write_json(AUDIT/'conclusion_status.json',dict(independent_confirmation=False,model_search_stopped=True,
        primary='not_supported',individual_history='very_small_exploratory_signal',peer_transfer='no_overall_support',
        cross_company_generalization='insufficient_evidence',calibrated_stock_odds='not_established',
        primary_delta_brier=float(main6.estimate),primary_low95=float(main6.low95),primary_high95=float(main6.high95),
        controls_passed=True,positive_effect_not_required_for_completion=True))
    print('Seven result reports and evidence-status receipt written')


if __name__=='__main__':main()
