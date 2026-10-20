"""EP27 evidence-bounded reports. Does not fit models, select candidates or alter predictions."""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.stats import norm
from core import *


def table(frame):
    t=frame.copy()
    for c in t:
        if pd.api.types.is_float_dtype(t[c]):t[c]=t[c].map(lambda v:'NA' if pd.isna(v) else f'{v:.6f}')
    return '| '+' | '.join(map(str,t.columns))+' |\n| '+' | '.join(['---']*len(t.columns))+' |\n'+'\n'.join('| '+' | '.join(map(str,row))+' |' for row in t.itertuples(index=False,name=None))+'\n'


def save(name,text):
    (EP/name).write_text(text)


def main():
    summary=pd.read_csv(OUT/'summary.csv');s=summary[summary.horizon.eq(6)];ci_=pd.read_csv(OUT/'paired_intervals.csv');mainci=ci_[ci_.horizon.eq(6)&ci_.block.eq(6)]
    primary=mainci[mainci.candidate.eq('M_RMIVF')&mainci.baseline.eq('M_RMI')&mainci.metric.eq('brier')].iloc[0]
    long=ci_[ci_.horizon.eq(6)&ci_.block.eq(12)&ci_.candidate.eq('M_RMIVF')&ci_.baseline.eq('M_RMI')&ci_.metric.eq('brier')].iloc[0]
    base=s[s.model.eq('M_RMI')].iloc[0];full=s[s.model.eq('M_RMIVF')].iloc[0];risk=s[s.model.eq('M_R')].iloc[0]
    p0=json.loads((OUT/'p0_audit.json').read_text());labelaudit=json.loads((OUT/'label_sensitivity_audit.json').read_text());controls=json.loads((OUT/'controls.json').read_text())
    monthly=pd.read_csv(OUT/'monthly_scores.csv',parse_dates=['date']);groups=pd.read_csv(OUT/'conditional_group_audit.csv');variance=pd.read_csv(OUT/'ep26_prediction_variance_structure.csv');component=pd.read_csv(OUT/'component_intervals.csv')
    conditional=pd.read_csv(OUT/'conditional_scores.csv');phases=pd.read_csv(OUT/'phase_intervals.csv');robust=pd.read_csv(OUT/'leave_out_robustness.csv');endpoints=pd.read_csv(OUT/'endpoint_context_intervals.csv')
    match=pd.read_csv(OUT/'matched_monthly.csv',parse_dates=['date']);pairs=pd.read_csv(OUT/'matched_pairs.csv',parse_dates=['date']);mci=pd.read_csv(OUT/'matched_intervals.csv')
    stats6=monthly[monthly.horizon.eq(6)&monthly.model.eq('M_RMI')];dates=set(stats6.date);matched=match[match.date.isin(dates)];knownpairs=pairs[pairs.both_known]
    cov=pd.read_csv(OUT/'fixed_population_coverage.csv');census=pd.read_csv(OUT/'census_coverage_by_month.csv');stocks=pd.read_csv(OUT/'listing_st_delisting_audit.csv')
    cal=pd.read_csv(OUT/'calibration_monthly_scores.csv');calmean=cal.groupby('model')[['brier','auc','bias','base_rate','enrichment20','recall20']].mean().reset_index();calci=pd.read_csv(OUT/'calibration_comparisons.csv');calgroups=pd.read_csv(OUT/'calibrated_conditional_scores.csv');rel=pd.read_csv(OUT/'reliability.csv');tieaudit=pd.read_csv(OUT/'calibration_rank_invariance.csv')
    port=pd.read_csv(OUT/'portfolio_summary.csv');pci=pd.read_csv(OUT/'portfolio_intervals.csv');pexp=pd.read_csv(OUT/'portfolio_exposures.csv');pcoh=pd.read_csv(OUT/'portfolio_cohorts.csv');pes=pd.read_csv(OUT/'portfolio_es_intervals.csv');pactual=pd.read_csv(OUT/'portfolio_actual_industry_imbalance.csv');beta=pd.read_csv(OUT/'portfolio_beta.csv');opp=pd.read_csv(OUT/'portfolio_opportunity_cost.csv')
    powz=.002/primary.se if primary.se>0 else np.inf;power=float(norm.cdf(-1.96+powz)+norm.cdf(-1.96-powz))
    write_json(OUT/'statistical_power.json',dict(important_absolute_brier_effect=.002,bootstrap_se=primary.se,approximate_two_sided_power=power,approximate_80pct_detectable_effect=primary.detectable_80pct_effect_approx,
        origin_months=int(primary.months),blocks_6=primary.approximate_blocks,blocks_12=long.approximate_blocks,limitations='local normal/weak-stationary approximation, not independent confirmation or correction for historical selection'))
    stocksummary=stocks.groupby(['exchange','is_delisted']).agg(stocks=('instrument','size'),missing_price_files=('source',lambda x:x.eq('missing_price_file').sum()),in_raw_top500=('in_fixed_pool','sum'),lifetime_ST_marked=('sh_lifetime_st','sum')).reset_index()
    save('data_integrity_audit.md',f'''# EP27 数据完整性与历史时点审计

P0在任何EP27模型评分前完成，p0_audit.json与来源哈希已注册。主事件严格R_6m<−20%，沿用EP26月末收盘至日期加6月后首个市场交易日收盘，前复权代理，数据截至2026-05-29。原56,000行的四期限标签重新核对，主标签/人群未更改。

## 两类总体分开

A为EP26原资格规则人群：43,960行含训练；29,596个预测股票月。6月有效27,230行、4,581事件、59个起点、25条成熟缺失。预测至2026-04，6月实际可评价起点只至2025-11，不能把2026预测月份当已到期测试。

B为上市日期/退市日期及当月正报价覆盖普查，不做终身ST排除。它不是已认证完整无偏PIT池：退市价格、源历史版本及上海暂停/终止日期语义仍不完整，不能用“代码按日期过滤”证明投资者当年确有同样数据。

'''+table(stocksummary)+f'''
研究期内元数据4819只，其中229只已退市，228只缺价格文件（SH89、SZ139）；原raw top500仅1只已退市。SH34只被全生命周期ST标志排除，仍缺可靠的上海逐日ST起止历史。原ST名单是事后诊断标志，绝不作为新模型输入。无法量化池外全部真实亏损率，不把缺文件判0或判全损。

B的2021以后报价覆盖有275,287个预测股票月，成熟252,471，已知252,011、事件35,829、成熟终点缺460。其观测发生率与A的比较受市值/上市年龄/资格结构影响，不是ST排除的因果效应；B没有一致财务特征，不在其上伪造候选评分。census_coverage_by_month.csv单列结果，in_fixed_pool指EP24原raw top500、未经过EP26特征资格筛选。

SZ30评价子集另列conditional_scores.csv，使用同一冻结预测；其ST规则按有日期的名称变更执行，但源版本、退市覆盖和主训练池偏差未解，不能称完全无偏，也不能与A混合。

## 市场与行业时点

CSI300过去126日动量、63日波动已从独立指数日线重建；信用观测严格早于预测日。宽度/周转及行业同伴状态改由B的上市/正报价覆盖快照计算，排除终身ST、未来退市标志、未来收益列进入状态构造。该构造减少显式未来ST筛选传递，仍受源价格覆盖幸存者缺口影响，未认证为完整当时全A市场。

19份历史发布分类，严格published<date，原PDF/解析表哈希核对；不以当前分类倒填。legacy/revised编码保留，无法识别原表部门的代码标UNKNOWN。重建后固定人群已知分类{p0['industry_known_fraction']:.2%}，陈旧比例{p0['industry_stale_fraction']:.2%}；2021–2023发布空档仍在。过去同伴动量/宽度剔除本股，至少5个可见同伴，前缀与留一计算有自动测试。历史文件来自迁移网站，原始历史字节未独立存证。

## 财报、估值及公司行动

财报严格max(公告,更新)<date，不回填最新版本；年龄中位456天。<=365天财报在成熟样本仅2个可评分月份，不能检验最新财报效果。information_age.csv保留分布，缺失不删人。估值观测日期距预测日0天只表示按TRADE_DATE合并，不证明原始版本0天；历史版本修订风险未知。历史股本/市值按原asof规则，未逐条认证原始披露版本。

普通现金/送转再投资代理同样本可检查{labelaudit['valid_same_sample_rows']:,}行；主事件率{labelaudit['main_event_rate']:.6%}、替代代理{labelaudit['reinvested_proxy_event_rate']:.6%}，事件不同{labelaudit['event_disagreements']}行。主定义没有修复替换。配股、未知金额、行动无价格及R09无法解释跳变窗口不称可靠总收益；退市结算、重整等仍未解决。return_sensitivity_monthly.csv对全部模型统一在相同有效子集重评分，不与主结果混合。

固定池成熟缺失的事件率界限见fixed_population_coverage.csv，各模型Brier界限见missing_brier_bounds.csv。它们不能界定被排除或没有原始报价的池外风险。

P0仅放行有限固定观察样本的机制诊断，禁止完整市场或独立确认。source_receipts.csv含7995项原始来源；inherited_baseline_receipts.csv另核对原EP25/26已公开checkpoint中的冻结分布与预测。prior_preservation.json保护1304个既有文件，原成果不改。
''')
    layers=mainci[mainci.metric.eq('brier')&mainci.apply(lambda r:(r.candidate,r.baseline) in [('M_R','B0'),('M_RM','M_R'),('M_RMI','M_RM'),('M_RMIVF','M_RMI')],axis=1)]
    save('market_risk_decomposition.md','''# EP27 市场共同风险与传统个股风险

所有市场字段都是过去/当期已可见信息，没有未来市场跌幅输入。市场宽度仅为覆盖样本代理，不能称全A资金流。六个模型相同架构/训练规则，人群和标签配对；增量沿注册顺序定义。

'''+table(s[['model','brier','auc','pr_auc','common_brier','relative_brier']])+table(layers[['candidate','baseline','estimate','low95','high95']])+'''
风险/市值M_R比历史B0改善Brier约0.005120。加入市场M后，点估计反而变差0.004157，区间跨0；不支持本次固定市场字段/模型带来稳定新增概率优势。不能因此断言市场永远无信息，M_R已包含会随市场变化的波动率。

## EP26原预测的时间结构，不是因果份额

'''+table(variance)+'''
例如EP26 M_R预测概率变异的13.41%体现在月均值，35.24%在同行业均值差，31.51%在行业内风险格均值差，19.84%在格内残差。M_VF对应17.62%、37.61%、21.95%、22.83%。这些是已观察概率的嵌套结构，不是“有效预测能力由市场/行业因果解释的百分比”；训练分布、股票池结构与小格也会产生它们。

Oracle真实Y方差单独存oracle_outcome_variance_not_a_forecast.csv，不属于任何模型输入/候选。它用未来结果作事后会计，小格均值会过度拟合，不能拿该表当可交易预测优势或真实风险来源的无偏估计。

概率误差的精确分解另见error_decomposition.csv与component_intervals.csv：共同均值、行业均值、行业内规模/波动格、格内误差之和等于Brier。区别于概率结构方差，前者评价误差，后者描述预测形状。
''')
    indlayer=mainci[mainci.candidate.eq('M_RMI')&mainci.baseline.eq('M_RM')]
    save('industry_risk_decomposition.md','''# EP27 行业风险与同行业评价

行业分类只使用预测前已经发布的表，时点和未知/陈旧状态见data_integrity_audit.md。行业状态从未做未来ST排除的报价覆盖重建，同伴排除本股；数据覆盖仍不是完整历史市场。

'''+table(indlayer[indlayer.metric.isin(['brier','auc','industry_auc','matched_cell_auc'])][['metric','estimate','low95','high95']])+'''
行业M_RMI相对M_RM的Brier差约−0.000520，但区间跨0；本模型没有验证稳定的行业新增概率优势。不能把“行业均值能重现一部分风险分数”当作有效行业预测。

## 同月同行业与风险格的评分覆盖

'''+table(s[['model','industry_auc','industry_coverage','industry_eligible_groups','matched_cell_auc','matched_cell_coverage','matched_cell_eligible_groups']])+'''
同行业至少8行、2正2负才评价。主对照行业AUC覆盖平均39.95%的已知股票月，56/59个月有可评价组；风险格仅7.20%、49/59个月。未覆盖部分不填AUC=0.5或0，不能声称结果适用全部行业和股票。风险格更窄的覆盖不能与全池AUC直接当等人群比较。

conditional_group_audit.csv保存每个模型、日期、行业/风险格的已知行数、事件/非事件、状态及排除原因。组资格仅用于评价是否可定义AUC，原预测人群和模型没有因事后事件数改变。月内组AUC按正负对数加权，再跨月平均，不把小组当独立样本。

![分层AUC与覆盖](outputs/conditional_auc.png)
''')
    primrows=mainci[mainci.candidate.eq('M_RMIVF')&mainci.baseline.eq('M_RMI')]
    comp=component[component.candidate.eq('M_RMIVF')&component.baseline.eq('M_RMI')&component.block.eq(6)]
    save('idiosyncratic_risk_report.md','''# EP27 个股条件风险与分层误差

“个股独立”在本实验中的可检验含义是：在固定市场/行业控制模型、同行业及近似风险匹配条件下仍有增量。它不是已证明完全排除所有连续风险因素或因果脆弱性。

'''+table(primrows[primrows.metric.isin(['brier','auc','pr_auc','industry_auc','matched_cell_auc','recall20','enrichment20'])][['metric','estimate','low95','high95','defined_months']])+'''
主要Brier与同行业AUC存在历史改善；较窄风险格的AUC增量约0.0512，但只覆盖约7.2%股票月，98.75%区间跨0，不能扩大为全部股票的强证据。匹配高低组另外用增量logit分数而非行业集中度，详见matched_risk_group_test.md。

## 改善位于哪些误差层

'''+table(comp[['component','estimate','low95','high95']])+'''
总Brier改善约0.003479中，共同均值项−0.001108、行业项−0.001459、风险格项−0.000221、格内项−0.000691，代数和精确。行业项贡献较大，不能把全部改善都称个股特有风险。格内项的历史改善仍受小格/有限样本、连续风险匹配误差及多重比较影响。

分解中的行业/格均值使用实现标签，只是误差会计，不是未来可用预测。真正新增信息的评价仍是注册模型样本外概率、同日/同行业条件AUC和预先形成的匹配组，不能拿Oracle替代。

完整模型Brier仍略高于M_R（0.138253对0.138095）。endpoint_context_intervals.csv是注册层增量的端点算术背景，明确为注册后解释性对照，不替代主检验。新增信息恢复了部分扩展基线的退化，不能据主比较获胜宣称全面优于简单风险模型。
''')
    abl=mainci[mainci.apply(lambda r:(r.candidate,r.baseline) in [('M_RMIV','M_RMI'),('M_RMIF','M_RMI'),('M_RMIVF','M_RMI'),('M_RMIVF','M_RMIV'),('M_RMIVF','M_RMIF')],axis=1)]
    save('valuation_financial_ablation.md',f'''# EP27 估值与财务条件增量

主比较raw Full−raw RMI；训练行、参数、月权重、季度拟合及标签相同，缺失不删人。四个主期限Brier次要检验族事前指定，不按结果挑选。

'''+table(abl[abl.metric.isin(['brier','auc','industry_auc','matched_cell_auc'])][['candidate','baseline','metric','estimate','low95','high95']])+f'''
6月主Delta={primary.estimate:.6f}，相对RMI下降{primary.relative_brier_improvement_percent:.3f}%，95%区间[{primary.low95:.6f}, {primary.high95:.6f}]；L12区间[{long.low95:.6f}, {long.high95:.6f}]。98.75%族区间[{primary.low_family:.6f}, {primary.high_family:.6f}]也低于0。

估值单组改善约−0.002964，联合−0.003479；财务单组−0.000553区间跨0，联合对估值再加F的Brier增量−0.000515区间也跨0。主要证据来自估值信息组；不能将联合成功解释为财务比率已独立验证。F组含陈旧度与可用性，且中位年龄456天，不是最新盈利预期。

'''+table(phases[phases.candidate.eq('M_RMIVF')&phases.baseline.eq('M_RMI')][['phase','estimate','low95','high95','months']])+'''
两个旧历史阶段均改善；逐月/逐年删除保存在leave_out_robustness.csv，不选择有利年份。源估值历史版本未认证、旧测试已反复使用、控制基线较弱，因此仍是固定样本/固定模型的历史条件增量，不是独立确认。

辅助1/3/12月分别报告，不能取代6月主结果：

'''+table(ci_[ci_.candidate.eq('M_RMIVF')&ci_.baseline.eq('M_RMI')&ci_.metric.eq('brier')&ci_.block.eq(12)][['horizon','estimate','low95','high95','months']])+'''
辅助12月优先参考L12，L6对其重叠结构不足以单独支持强结论。所有模型、期限、市场状态与SZ30子集均保留在summary.csv、conditional_scores.csv；各总体不混合。
''')
    calshow=['M_RMI','M_RMI__global','M_RMI__state','M_RMIVF','M_RMIVF__global','M_RMIVF__state']
    save('conditional_calibration.md','''# EP27 市场状态条件校准

校准只用过去真正样本外概率及严格已成熟标签，最近36起点、至少12起点/30事件/30非事件；不足精确退回raw。global固定原logit斜率1拟合截距，state再按过去市场状态调整共同截距。没有训练内概率、未来标签或事后改校准算法。

'''+table(calmean[calmean.model.isin(calshow)])+table(calci[calci.metric.eq('brier')&calci.block.eq(6)][['candidate','baseline','estimate','low95','high95']])+'''
两种校准均退化，而非仅没有显著改善。Full的global增加Brier约0.013584，state增加0.018694，95%区间均为正；不能挑局部年份的偏差修复当整体成功。

'''+table(calgroups[calgroups.model.isin(['M_RMIVF','M_RMIVF__global','M_RMIVF__state'])&calgroups.dimension.eq('phase')][['model','condition','brier','auc','bias','base_rate','months']])+'''
raw Full在2021–23低估约8.57个百分点，后段高估约5.92个百分点。整体校准减小前段平均偏差，却使后段高估加重至约11个百分点；状态校准也未稳定修复。这说明预注册可观测状态/有限成熟历史没有可靠外推漂移，不证明所有市场状态方法永远无效。

384份校准记录中108份因预热不足原样回退，276份成功拟合，优化失败0。全部训练键、最大成熟日期、系数和训练内变换记录在calibration_fits.json。主要判定仍未校准Full−RMI，不能以另一个校准版本重定主检验。

理论上共同logit偏移保存同月排序。实际双精度中两个模型各有1个月的并列被约1e−17打破，预警名单不变，Full两种校准排序精确不变；不将浮点并列噪声称排序增量。原概率文件未改，细节见calibration_rank_invariance.csv。

可靠性固定0.1桶，reliability.csv含行数、事件数、覆盖月份及整月块偏差区间；稀疏桶不标可信。年份/趋势/高低波动/高风险20%组见calibrated_conditional_scores.csv；空桶月零权重，不伪造零事件。

![原始与滚动校准可靠性](outputs/reliability.png)
''')
    matchci=mci[mci.metric.eq('event_difference')&mci.block.eq(6)].iloc[0]
    save('matched_risk_group_test.md',f'''# EP27 匹配风险组

每月同历史行业、同板块；行业至少10只，增量分数logit(Full)−logit(RMI)最高/最低20%（ceil），市值log差≤0.35、波动log差≤0.20。按可观测距离贪心无放回、最多20对/月；不是用未来损失找相似样本。

形成{int(match.formed_pairs.sum())}对，成熟双端可观察{len(knownpairs)}对；主评价59个月，未到期/端点缺失保留在matched_monthly.csv。实际平均每月对数低于目标时不放宽卡尺，不能把不足样本删除。每个高/低端数量相同，行业和板块精确一致，连续风险仅近似匹配。

'''+table(matched[['formed_pairs','known_pairs','missing_pairs','log_cap_gap_mean','log_vol_gap_mean']].agg(['mean','min','max']).reset_index().rename(columns={'index':'statistic'}))+table(mci[['metric','estimate','low95','high95','months','defined_months','block']])+f'''
按月等权，高−低重大亏损发生率差{matchci.estimate*100:.3f}个百分点，95%区间[{matchci.low95*100:.3f}, {matchci.high95*100:.3f}]；L12同方向。配对标签不同时的条件一致率约71.9%，51个月可定义，不能把同样标签的对当成独立成功。

按全部已知对合并（与等月估计权重不同），高组事件率约20.34%、低组11.46%；平均RMI概率差约−0.092个百分点，Full差约8.489个百分点。高低差不是仅按原基线更高风险选出的。仍不能排除连续风险残差、有限匹配覆盖、历史选择及估值版本问题，不作为因果识别。

matched_pairs.csv含每对身份、距离、源行业、预测差、结果及缺失；名单按预测信息先生成。自动测试在替换/反转全部未来标签后要求匹配结果完全不变。

![配对高低组风险差](outputs/matched_groups.png)
''')
    ptable=port[['strategy','cost_bps','cumulative_return','annual_return','annual_vol','sharpe_zero_cash','daily_es05','monthly_es05','max_drawdown','drawdown_duration_sessions','mean_equity','turnover','fees','liquidity_limited_orders']]
    save('portfolio_tail_risk_test.md','''# EP27 行业中性风险过滤辅助检验

S1=raw RMI，S2=raw Full，S0=固定哈希基础子池。行业主要代码×板块×规模/波动中位数逐格相同保留数、等权，UNKNOWN三组全保留。因此目标已发布行业权重、风险格计数、总仓位、持股数精确一致。格内floor(20%n)意味着小格实际不筛选，整体过滤比例明显低于20%；不为了收益提高筛选比例。

可交易代理池要求当时过去21日金额≥500万元，仍不是完整交易所可交易性认证。模拟资本100万元、下一交易日收盘、双向10/30bp费用，成交额最多上一交易日为止21日平均金额的10%，现金守恒，不用当天收盘后量决定成交。缺报价不交易，已有资产最后价估值且显式记录。

'''+table(ptable)+'''
三组实际股票仓位均接近100%，最大同日差为0，没有低仓位/现金规避制造成功。持股数/目标行业计数精确匹配；实际仓位随价格和报价失败略漂移，不能忽略。

'''+table(pci[pci.comparison.eq('S2-S1')][['metric','cost_bps','estimate','low95','high95','block']])+'''
S2−S1持有重大亏损率只下降约0.080个百分点，区间跨0；10bp下S2累计收益略低、最大回撤与日ES略差，月ES略好，30bp收益排序因换手费用略反转。风险排序/概率改善没有转化为本过滤规则下稳定的新增组合尾部价值。

'''+table(pes[pes.comparison.eq('S2-S1')][['dataset','delta_es05','low95','high95','block']])+'''
ES为最差5%收益均值，差为左减右，正值表示较少亏损。6月静态名单与按月调仓时间序列分开，不把股票横截面尾部误作组合时间尾部。回撤持续时间单位为交易日，窗口末未恢复仍计到末日。

## 暴露与归因

'''+table(pexp.groupby('strategy')[['holdings','tradable_proxy_rows','log_cap_std_diff_vs_s0','vol63_std_diff_vs_s0','stale_industry_fraction']].mean().reset_index())+table(beta)+table(pactual[pactual.cost_bps.eq(10)].groupby('comparison').agg(mean_industry_TV=('industry_total_variation','mean'),max_industry_TV=('industry_total_variation','max')).reset_index())+'''
S2/S1实际行业总变差均值约0.16%、最高0.66%；发布日变更与价格漂移都有影响。目标行业严格中性是对当时可见分类而言，原分类陈旧、未知或退市结算缺口仍不消失；连续规模/波动及实现市场beta残差另外记录。没有通过事后行业择时选择组合。

## 收益机会成本

'''+table(opp.groupby('strategy')[['excluded_rows','excluded_mean_return','excluded_gain20_rate','selected_mean_return']].mean().reset_index())+'''
被排除股票也可能大涨，机会成本完整保留。陈旧估值最高约1%资产可隐藏未记录损失，前复权单位不是完整真实交易收益。经济实验只作辅助，本结果不支持本策略的独立经济价值，也不抹掉历史概率主检验的条件增量。

![组合净值及回撤](outputs/portfolio.png)
''')
    controlsrows=[]
    for item in controls['positive_controls']:controlsrows.append(dict(control=item['world'],metric='correct-source Delta Brier',estimate=item['correct_source_gain']['estimate'],low95=item['correct_source_gain']['low95'],high95=item['correct_source_gain']['high95'],passed=item['passed']))
    neg=controls['negative_control'];nci=neg['full_minus_base_industry_auc'];controlsrows.append(dict(control='conditional permutation',metric='Full-RMI industry AUC',estimate=nci['estimate'],low95=nci['low95'],high95=nci['high95'],passed=neg['passed']))
    controlsdf=pd.DataFrame(controlsrows)
    save('statistical_validation.md',f'''# EP27 统计有效性与自动核验

主指标Delta Brier=raw Full−raw RMI。每月股票等权、再跨月等权；stationary bootstrap整月横截面一起取样，L6/L12、10000次固定种子。没有把27,230股票月或4,581事件当成独立市场时间试验。59个重叠起点约9.83个6月/4.92个12月块。

主效应{primary.estimate:.6f}，95%区间[{primary.low95:.6f}, {primary.high95:.6f}]，L12[{long.low95:.6f}, {long.high95:.6f}]，四项Brier族98.75%区间[{primary.low_family:.6f}, {primary.high_family:.6f}]。所有这些区间只支持旧固定样本中的历史条件效果，不消除167+后续多轮研究选择、数据版本和池偏差。

主要配对标准差{primary.se:.6f}，近似80%可检测幅度{primary.detectable_80pct_effect_approx:.6f}；对预设0.002幅度的近似功效{power:.1%}，不足80%。该局部正态近似不计结构变化，不能当成前瞻样本量保证。条件AUC保留原59月时间格，行业可定义56月、风险格49月；不将不相邻月份压成连续。

'''+table(controlsdf)+'''
三种合成世界分别只有市场、行业、个股信号，正确信息块都被识别；个股无信号的控制没有虚构独立优势。真实月×行业置乱保持事件数和缺失位置，Full行业内AUC约0.512，Full−RMI约0.0032且区间跨0；市场/行业总体发生率仍存在，不要求pooled AUC降到0.5。控制的四项空信号判断按注册98.75%区间，主要研究95%不变。EP25/26原控制及哈希保留。

## 稳健性与边界

逐年/阶段、趋势/波动状态、行业陈旧度、财报年龄、SZ30评价子集、收益代理敏感性及删除月份/年份均交付；不挑有利一格替换主检验。endpoint_context_intervals.csv是注册层增量的算术端点背景，注册后生成且明确不作正式主检验；它提示Full未胜简单M_R，不能以较弱扩展基线夸大优势。

Oracle输出严格独立命名，不进入训练或可交易评分。误差/概率方差分解是事后会计，特别小格能产生表面“解释份额”，不作因果来源百分比。

自动测试实际回执在outputs/pytest.txt；全528模型重放、全部概率/主要指标重建、校准成熟历史/参数、匹配不看未来、行业中性/流动性/现金核验及1304项旧文件哈希在validation.json。完整输入/预测依赖本地原始缓存；只克隆代码不等于这些结果已经由第三方独立复现。未来验证协议另行封存，没有新样本时明确尚未独立验证。
''')
    support=bool(primary.high95<0);tag='历史固定样本中支持有限条件增量；尚未独立验证' if support else '历史主检验不支持稳定条件增量；独立证据不足'
    save('final_conclusion.md',f'''# EP27 最终结论

**{tag}。没有证据把本结果升级为全A股稳定、可校准且具有新增组合尾部价值的个股独立风险能力。**

## 一、EP26风险识别有多少来自共同、行业和传统结构？

原风险模型M_R的预测概率变异，月共同结构13.41%、行业35.24%、行业内规模/波动格31.51%、格内19.84%。原VF为17.62%、37.61%、21.95%、22.83%。这些是概率结构会计，包含训练/池结构与小格效应，不能声称相同比例的有效预测能力被因果解释。

新预测消融中，M_R比B0有历史优势；加入市场M及行业I没有稳定Brier增量（市场点估计变差，行业改善区间跨0）。不能用Oracle或组均值解释率替代真实时点预测验证。

## 二、控制这些因素后，估值财务还能区分风险吗？

在注册模型/旧固定观察样本下，**存在历史条件增量**：Full行业内AUC比RMI提高约0.0301，95%区间[0.0138,0.0484]。同行业近似市值/波动匹配，高增量组比低组重大亏损率高约9.53个百分点，95%区间[4.21,15.49]。

但行业AUC只覆盖约40%、风险格AUC约7.2%股票月；934个已知对仍只提供59个重叠起点。连续风险并未完全匹配，不是因果或所有行业的独立证据。真正PIT池、估值原始版本、退市风险仍未认证。

## 三、改善概率还是只有排序？

主6月raw Full Brier={full.brier:.6f}，raw RMI={base.brier:.6f}；Delta={primary.estimate:.6f}，相对下降{primary.relative_brier_improvement_percent:.2f}%，95%区间[{primary.low95:.6f}, {primary.high95:.6f}]，12月块与四检验族区间也低于0。因此在该注册比较中，概率评分与条件排序都有历史改善，不能说只是AUC。

来源主要是估值：V−RMI改善约−0.002964；F单组和在V上再加F的Brier区间跨0。总误差改善部分位于行业项，并非全部个股格内。更关键的是Full Brier仍略高于简单M_R的{risk.brier:.6f}；主胜利是相对较弱扩展控制基线的条件增量，不是全面优于传统风险模型。

## 四、已知市场状态能修复校准漂移吗？

本轮不能。raw Full在2021–23低估约8.57个百分点，后段高估约5.92个百分点。严格成熟历史global/state校准分别令Brier增加约0.01358/0.01869，区间均为正，后段高估加重。它们按定义没有新增个股排序；浮点并列噪声不算排序增量。

观察到状态/阶段关联，不等于已知市场状态足够解释或可预测未来漂移。不能把整体平均偏差或某年校准好转贴为概率可信。

## 五、行业和风格可比后能改善组合尾部吗？

本预注册过滤规则未确认。目标已发布行业权重、风险格持股数、总仓位精确匹配，实际仓位差为0；但S2−S1持有重大亏损率仅约−0.080个百分点，区间跨0。10bp下S2累计收益略低、回撤和日ES略差，月ES略好；30bp因换手成本收益顺序轻微反转。没有稳定新增经济价值，不能选最有利风险指标宣称成功。

## 六、证据分级与下一步边界

**历史支持**：注册Full−RMI的有限条件概率增量、估值主要贡献、部分行业/匹配范围内的风险区分；三来源控制说明管道能分层识别已知信号。

**本轮不支持**：市场/行业字段在当前固定模型中带来稳定新增概率优势；财务组独立Brier增量；滚动global/state校准有效；本行业中性过滤带来稳定新增尾部价值。

**证据不足/尚未独立验证**：全A真实时点信息的稳定独立作用、绝对概率可靠性、退市/特殊行动完整尾部、其他低事件行业及新市场状态泛化。研究期229只退市股票中228只缺本地价格，原ST/源版本偏差未修复；历史多轮模型选择不能被bootstrap消除。

已完成P0–P4、六候选四期限528次基础拟合、注册消融/校准/控制、匹配及组合检验。原EP24/25/26与双20%结论保持原义。代码/配置/评分/报告/测试/哈希及复现依赖独立交付；完整预测模型留本地缓存，不能声称仅克隆Git即可精确复现。

按停止规则结束本轮，不添加模型、改阈值、换基线或挑年份。值得保留的是未经校准的条件估值风险线索；前瞻协议已冻结来源、模型、校准、人群、标签、统计及哈希，最早2026-10-30真实新队列，等待标签真正到期。当前没有新前瞻样本，不声称完成独立确认。
''')
    # Standalone publication figures, no stochastic fitting.
    selected=['B1','M_R','M_RM','M_RMI','M_RMIV','M_RMIF','M_RMIVF'];t=s.set_index('model').loc[selected]
    fig,axes=plt.subplots(1,2,figsize=(12,5),layout='constrained')
    for column,label in [('auc','same month'),('industry_auc','within industry'),('matched_cell_auc','industry/risk cell')]:axes[0].plot(range(len(t)),t[column],'o-',label=label)
    axes[0].set_xticks(range(len(t)),selected,rotation=40);axes[0].axhline(.5,color='grey',linestyle='--');axes[0].legend(fontsize=8);axes[0].set(ylabel='AUC',title='Exploratory conditional discrimination')
    axes[1].bar(['Industry','Industry/risk cell'],[base.industry_coverage,base.matched_cell_coverage]);axes[1].set(ylim=(0,1),ylabel='Mean known-stock coverage',title='AUC eligibility: n>=8, positive>=2, negative>=2')
    fig.savefig(OUT/'conditional_auc.png',dpi=160);plt.close(fig)
    fig,ax=plt.subplots(figsize=(7,6),layout='constrained')
    for name in ['M_RMI','M_RMIVF','M_RMIVF__global','M_RMIVF__state']:
        q=rel[rel.model.eq(name)&rel.dimension.eq('all')&rel.block.eq(6)].sort_values('predicted');ax.plot(q.predicted,q.observed,'o-',label=name,markersize=4)
    ax.plot([0,1],[0,1],'--',color='grey');ax.set(xlabel='Predicted loss probability',ylabel='Observed frequency',title='Reliability: month-equal history',xlim=(0,1),ylim=(0,1));ax.legend(fontsize=8);fig.savefig(OUT/'reliability.png',dpi=160);plt.close(fig)
    fig,axes=plt.subplots(2,1,figsize=(10,7),sharex=True,layout='constrained');m=matched.copy();m['high_rate']=m.high_events/m.known_pairs.replace(0,np.nan);m['low_rate']=m.low_events/m.known_pairs.replace(0,np.nan)
    axes[0].plot(m.date,m.high_rate,label='High incremental score');axes[0].plot(m.date,m.low_rate,label='Low incremental score');axes[0].legend();axes[0].set(ylabel='Observed loss frequency',title='Observable matched pairs; historical exploration')
    axes[1].bar(m.date,m.known_pairs,width=20);axes[1].axhline(20,color='grey',linestyle='--');axes[1].set(ylabel='Known pairs',xlabel='Origin month');fig.savefig(OUT/'matched_groups.png',dpi=160);plt.close(fig)
    daily=pd.read_csv(OUT/'portfolio_daily.csv',parse_dates=['date']);fig,axes=plt.subplots(2,1,figsize=(11,7),sharex=True,layout='constrained')
    for strategy in ['S0','S1','S2']:
        q=daily[daily.strategy.eq(strategy)&daily.cost_bps.eq(10)];axes[0].plot(q.date,q.nav,label=strategy);axes[1].plot(q.date,q.drawdown,label=strategy)
    axes[0].legend();axes[0].set(ylabel='NAV',title='Industry/risk matched targets, 10bp each side');axes[1].set(ylabel='Drawdown',xlabel='Date');fig.savefig(OUT/'portfolio.png',dpi=160);plt.close(fig)
    write_json(OUT/'conclusion_status.json',dict(overall='HISTORICAL_CONDITIONAL_INCREMENT_SUPPORTED_NOT_INDEPENDENTLY_VALIDATED' if support else 'INSUFFICIENT_EVIDENCE',primary_delta=primary.estimate,primary_ci95=[primary.low95,primary.high95],
        historical_primary_supported=support,independent_confirmation=False,full_market_PIT_claim=False,stable_calibration_supported=False,incremental_economic_value_confirmed=False,stopped_after_registered_experiments=True))
    print((EP/'final_conclusion.md').read_text()[:2100],flush=True)

if __name__=='__main__':main()
