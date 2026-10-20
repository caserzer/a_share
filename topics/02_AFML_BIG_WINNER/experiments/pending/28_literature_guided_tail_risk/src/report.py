"""Render registered result tables and bounded conclusions; never train or select."""
from core import *


def table(frame,cols=None):
    f=frame[cols] if cols else frame
    def cell(v):
        if isinstance(v,(float,np.floating)):return 'NA' if pd.isna(v) else f'{v:.6f}'
        return str(v)
    return '| '+' | '.join(map(str,f.columns))+' |\n| '+' | '.join(['---']*len(f.columns))+' |\n'+'\n'.join('| '+' | '.join(cell(v) for v in row)+' |' for row in f.itertuples(index=False,name=None))+'\n'


def read(name):return pd.read_csv(OUT/f'{name}.csv')
def write(name,text):(EP/'reports'/name).write_text(text.strip()+'\n')


def main():
    s=read('summary');ints=read('paired_intervals');ph=read('phase_intervals');comp=read('component_intervals')
    primary=ints[(ints.baseline=='M_R')&ints.candidate.isin(['L1','L2','L4'])&(ints.metric=='brier')]
    cols=['candidate','baseline','block','estimate','low95','high95','low_family','high_family','relative_brier_improvement_percent']
    small=['candidate','baseline','metric','estimate','low95','high95']
    primary6=primary[primary.block==6]
    assert (primary.high95>0).all() and (primary.low95<0).all(),'Narrative assumes all primary intervals cross zero; inspect changed artifacts'
    statuses=dict(L1='不支持当前模型的新增预测优势',L2='历史排序与风险结构线索；稳定概率优势证据不足',L3='数据不足，真实分支未执行',L4='不支持整体稳定概率优势；目标迁移结果与阶段差异另报')
    write_json(OUT/'conclusion_status.json',dict(independent_confirmation=False,stable_probability_advantage_found=False,
        mechanism_status=statuses,executable_economic_confirmation=False,all_registered_feasible_experiments_complete=True))
    write('paper_replication.md',f"""
# 文献复现：标签、版本与可实现程度

九项核心来源均完成获取尝试和可复现性审计；取得五份可核验全文，另外四项正文不可得，不能补猜方法。[逐篇矩阵](../literature/literature_matrix.md)列市场、标签/公式、控制、切分、评价、推断、结果限制及材料；[引用及版本](../literature/source_references.md)列原始链接。作者稿、工作稿和proof不冒称最终期刊版。

**Level A 原市场忠实复现：没有完成。** 原始样本/授权数据/财务失败标签/文本语料不具备；Cao等原公式未取得即停止其忠实分支。不能把新CatBoost迁移称为复现论文模型。

**Level B 机制迁移：有限实现。** Kelly–Jiang月内5%尾指数、滞后尾暴露；CHS半年市场调整日收益NCSKEW/DUVOL的计算，经独立公式测试。A股风险结构OLS是Goal明确要求的代理，非Cao原模型。原120月市场回归初始窗改为36月；自由流通换手、6/12月收益等与原文不同，见预注册。仍依赖未经原版认证的回溯报价，不能称完全认证PIT迁移。

Kelly下一月沪深300收益预测OOS R²={json.loads((OUT/'market_mechanism.json').read_text())['oos_r2']:.6f}，相对扩展均值没有优势；这不是6个月个股损失事件。CHS代理在独立偏度目标上的差异如下，负值为改善：

{table(read('shape_intervals').query('block==6'),['target','metric','estimate','low95','high95','months'])}

该增量是“加整组历史价格/换手/偏度代理”相对风险/市值/同类滞后偏度，不单独识别异常换手的因果作用。

**Level C 固定−20%目标迁移：** L1/L2/L4及所有固定消融已运行；L3、文本/不透明度及估值交互停止。三主比较区间都跨零，不能以偏度预测改善宣称重大亏损概率已获验证。[主结论](final_conclusion.md)。
""")
    bounds=pd.read_csv(EP/'outputs/audits/population_event_bounds.csv')
    write('data_integrity.md',f"""
# 数据完整性与历史时点

## D0 原样保留

固定EP27面板43,960行；预测2021-01至2026-04共29,596股票月，6个月可评分起点截至2025-11：59月、27,230已知标签、4,581重大亏损、25成熟缺失。数据源截至2026-05-29。收益严格小于−20%，沿用原月末收盘至目标日后首个交易日收盘的前复权代理，不替换分红/退市标签。原72列逐值核验，EP24–EP27共1,739非缓存文件SHA保留。

原池的未来沪市终身ST筛选、价格可见性和幸存偏差没有消失。EP27审计标记34只沪市终身ST股票；未将该标签当当期可知信息重新筛选。名称变更/风险警示历史存在不能提供完整停牌、重整和逐日可交易性证明。行业来自19次已发布历史表（发布时间严格早于起点）；23.65%左右观测使用陈旧分类，2021–2023版本空档保留。没有使用当前行业倒填。

## 退市报价恢复与D1关卡

原229只退市证券中缺本地价的228只，均通过公开Sina原始日线与复权因子端点取得可解析历史报价。`delisted_source_attempts.jsonl`与`delisted_recovery.jsonl`保存成功、失败及修正解析记录；不删除失败尝试。因子字段为d/f，首次解析字段错误在模型前修正，未修改原源字节。7条非交易日记录隔离，未删除整家公司或猜测其交易日。

三只已有报价的重叠对照各2,281日，原始收盘价最大差0；按共同终点尺度归一的前复权价格差均<0.005。日收益仍受旧数据两位小数及版本尺度影响，最大差约0.00143；这验证运输/尺度一致性，**不认证分红再投资总收益、特殊行动或退市结算**。

{table(bounds,['population','mature','known','missing','events','known_rate','rate_lower','rate_upper'])}

比例界分别把全部缺失事件视作0/1，仅用于敏感性，不填入训练标签。回收报价子样本观察到30.61%损失率，而旧报价覆盖子样本14.22%；人群不同，不能解释为模型增量。回收子样本1,128个到期缺失让发生率界达到24.61%–44.21%。D1完整上市元数据人群仍缺2,411个结果。

D1只是4819只元数据证券的可观察覆盖普查，未认证全A股无偏历史池。缺一致历史总市值、退市结算、停牌交易和特殊行动闭合，**D1正式模型停止**。D1广义日收益池可为明确受限的共同风险代理提供历史观察值；不是宣称D1预测验证成功。

## PIT、标签与剩余限制

公告日期、收益率观察日期、行业发布时间的先后检查通过，但 `max(notice,update)` 不是首次公告财务版本；历史估值日期也不是当时数据库版本证明。因此不运行真实L3、文本、不透明度/估值交互，不沿用现代字段冒充实时数据。

所有训练标签结束日严格早于季度起点；同样本预测/标签逐条配对。新特征截至起点，删除2023年末以后一切行情重算，历史特征逐值不变。收益重叠与横截面共同冲击用整月配对时间块处理，不把股票数当独立样本数。历史重复研究选择不能靠bootstrap消除。

D0缺失的同一未知事件对两个模型同时取0/1，配对Brier上下界见 `outputs/metrics/missing_paired_brier_bounds.csv`；不能分别给不同模型安排有利标签。月等权聚合的点估计界（不包含抽样不确定性）：

{table(read('missing_bounds_summary'))}

全输入路径/哈希见 `outputs/manifests/data_sources.csv`。PIT日期核验与数据版本真实性是两个不同层次，本次只完成前者及有限公开来源证据核查。
""")
    for model,filename,title,interpret in [
        ('L1','common_tail_risk.md','共同尾部风险',
         'L1比M_R平均Brier更差，区间跨零；加入个股滞后暴露相对仅共同尾指数的消融增量接近零。不能认定共同尾因子带来可用概率优势。行业/风险匹配覆盖有限，不把局部匹配差异解释为全池增量。'),
        ('L2','idiosyncratic_volatility.md','特质波动与风险结构',
         'L2平均Brier为0.136503，对M_R差−0.001592，相对改善约1.15%，但两块长95%和四重区间均跨零。L2同月AUC约0.695、行业内约0.642；风险结构有历史排序线索。相对去残差风险的L2_systematic消融改善−0.001821，表明信息与残差风险组有关；这不能替代对M_R的主要检验。RMI_L2−M_RMI的普通95%区间为负，四重区间跨零，而且RMI_L2的绝对Brier仍差于M_R。早期2021–2023差为正、后期2024–2025为负，不能称跨阶段稳定。'),
        ('L4','information_opacity.md','交易分歧、历史涨幅与不透明度',
         '可运行部分只有历史价格/换手/偏度代理；没有可靠原公告文本与历史财务/估值版本，不能声称检验了文本、不透明度或高估值×分歧。L4比M_R整体Brier略差且区间跨零；前期变差、后期改善。去异常换手的消融未显示加入换手有额外Brier优势。偏度目标上的改善单独成立于有限代理设计，不能转述为−20%概率优势，也不能归因于换手单一变量。')]:
        ab={'L1':'L1_common','L2':'L2_systematic','L4':'L4_price_history'}[model]
        selected=ints[(ints.candidate.isin([model,'RMI_'+model]))&(ints.metric=='brier')]
        stage=ph[(ph.candidate==model)&(ph.baseline=='M_R')&(ph.block==6)]
        component=comp[(comp.candidate==model)&(comp.baseline=='M_R')&(comp.block==6)]
        write(filename,f"""
# {title}

{interpret}

所有固定概率对照（含机制内消融与扩展控制；Δ<0为好）：

{table(selected,cols)}

预注册两个阶段：

{table(stage,['phase','estimate','low95','high95','months'])}

误差会计分解（各项差之和等于总体Brier差）：

{table(component,['component','estimate','low95','high95'])}

共同发生率、个股排序和绝对校准必须分开。分解是已实现误差的正交会计，不是因果风险来源，也不是新拟合的预测器。全部年份、市场状态、行业在 `conditional_scores.csv`；逐月/逐年删除在 `leave_out_robustness.csv`，未选择有利子样本。
""")
    controls=json.loads((EP/'outputs/audits/controls.json').read_text())
    pos=pd.DataFrame(controls['positive'])
    write('financial_distress.md',f"""
# 财务困境水平及变化：真实分支停止

结论为**证据不足，未执行真实L3**，不是“不存在财务困境机制”。Campbell等正式全文已取得，原目标为财务失败，不能等同于半年股价亏损；Andreou原公式未取得，不能根据摘要填成任意Merton模型。Meng完整计分公式也未取得。

原始财报首次版本、完整负债/市值分母、偿付能力、失败事件及历史评级等必要信息没有认证。使用最新数据库回填会混淆当期信息与后见修订，因此未用其他因子替补此方向，H3保留在四重主要检验家族中。

人工困境变化世界只是程序正控制：静态水平与变化分开，事件由变化生成，固定算法可以识别这一信号。

{table(pos[pos.world.eq('distress_change')],['world','estimate','low95','high95','passed'])}

控制通过不证明A股真实存在这类可预测结构。要判断变化是否比静态更有用，下一阶段必须先取得首次公告版本、可复算困境定义及新样本，再建立新注册，而非继续试本轮历史集。
""")
    mm=read('matched_monthly');mm['date']=pd.to_datetime(mm.date);monthly=read('monthly_scores');evaldates=pd.to_datetime(monthly.date.unique())
    me=mm[mm.date.isin(evaldates)]
    coverage=me.groupby('model').agg(months=('date','size'),months_with_pairs=('known_pairs',lambda x:int((x>0).sum())),pairs=('known_pairs','sum'),average_stock_coverage=('stock_coverage','mean'),high_events=('high_events','sum'),low_events=('low_events','sum')).reset_index()
    groups=read('conditional_group_audit')
    gc=groups[(groups.model=='M_R')&groups.status.eq('eligible')].groupby('group_type').agg(eligible_stock_months=('known','sum'),events=('events','sum'),months=('date','nunique')).reset_index()
    write('matched_incremental_tests.md',f"""
# 相同股票、日期与风险组的增量

13个模型（4个复用基线、9个新增结构）在59个可评分月、27,230股票月上配对；没有改变标签或删除差年份。主要对照M_R，扩展对照与消融完整报告。

{table(s,['model','brier','auc','pr_auc','industry_auc','matched_cell_auc','industry_coverage','matched_cell_coverage'])}

行业内平均可评价覆盖约39.95%，行业×板块×市值/波动率格约7.20%，不是全池条件AUC。最低8行、2事件、2非事件；未知行业剔除且原因全部在 `conditional_group_audit.csv`。

{table(gc)}

预测差异先形成匹配，再揭示结果；同业同板块、市值/波动率卡尺固定，目标20对/月但普遍不足：

{table(coverage)}

{table(read('matched_intervals').query('block==6'),['model','metric','estimate','low95','high95','defined_months'])}

L2对M_R的有限匹配样本存在正事件差线索，但RMI_L2对M_RMI匹配区间跨零。风险格AUC、连续卡尺配对、总体Brier是不同统计对象；不能用覆盖几个百分点的显著差替代总体预测证据。配对一致率仅在高低结果不同的月份可定义，其缺失月份保留，不按零处理。

主Brier两块长与四重区间：

{table(primary,cols)}
""")
    cal=read('calibration_monthly');cals=cal.groupby('model')[['brier','bias','ece','auc']].mean().reset_index()
    warnings=s[s.model.isin(['M_R','L1','L2','L4'])]
    condition=read('conditional_scores')
    write('probability_calibration.md',f"""
# 概率校准与关键尾部

所有主候选的月均ECE约0.11–0.12，超过预注册0.05诊断容忍度。较小的总体平均bias可由不同月份正负误差抵消，不能说明绝对概率可靠。原始主要模型完整结果：

{table(warnings,['model','brier','bias','ece','precision5','recall5','enrichment5','recall10','enrichment10','recall20','enrichment20'])}

固定5%和20%预警的误报/漏报完整会计如下。TP/FP/FN/TN是股票月计数，Recall/FPR为先月后跨月平均，二者不能混算。FP只是未发生−20%事件，不等于必然上涨；FN为发生事件但未在该比例预警名单中的股票。

{table(read('warning_errors_summary').query("dimension=='all' and model in ['M_R','L1','L2','L4'] and fraction in [0.05,0.2]"),['model','fraction','TP','FP','FN','TN','mean_month_recall','mean_month_fpr','mean_month_false_discovery'])}

固定10%及全部年份/状态/行业的误报漏报也在 `warning_errors_summary.csv`，原逐月记录在 `warning_errors_monthly.csv`；没有只挑选漏报少的行业。5%预警的召回率较低是容量约束与排序能力共同作用，不能以少量高风险股票的富集掩盖大量漏报。

概率可靠性图使用固定0.1宽度概率箱、每月等权；不是用测试标签拟合概率。图中聚合趋势还会掩盖状态漂移，因此同时给出逐月/逐年/状态/行业ECE和bias。

![Reliability](../outputs/metrics/reliability.png)

滚动36个成熟OOS起点、至少12月及30事件/非事件的固定截距校准，没有选择优化版本：

{table(cals)}

四组统一截距校准都使平均Brier恶化。六个月标签滞后使历史发生率不能及时跟踪新状态；这是对本补救方法的结果，不代表所有校准算法都无效。本轮按停止规则不追加算法。校准预测不改变月内风险排序和5/10/20%预警名单；模型回放核验此项。

![Yearly bias](../outputs/metrics/yearly_bias.png)

状态层校准（所有预设状态，不只列有利状态）：

{table(condition[(condition.dimension=='regime')&condition.model.isin(['M_R','L1','L2','L4'])],['model','condition','months','events','brier','bias','ece'])}

行业/年份的全量结果在 `conditional_scores.csv` 与 `calibration_conditional.csv`。最高5/10/20%预警Recall/富集差的两种块区间在 `paired_intervals.csv`。没有把较高AUC或富集自动解释为绝对概率已经可信。
""")
    filters=read('filter_intervals')
    write('portfolio_risk_filter.md',f"""
# 固定5%过滤：持有目标诊断，经济验证停止

S2在评分前指定L4；即使L2历史点估计更好，也不替换S2。S0为过去21日成交额≥500万元的D0可观察池目标等权，S1排除M_R最高5%，S2排除L4最高5%；取ceil，目标股票总仓位100%。这只是当期目标持有名单，未认证为当期实际可交易股票池或实际持仓。

`S2_matched`保持S1在行业×板块×月内市值/波动率格的持有数，再在每格用L4选择剔除名单。它匹配格人数，不能使连续市值/波动率或后续漂移完全相等。

{table(filters[filters.block==6],['candidate','baseline','metric','estimate','low95','high95'])}

事件占比按同月目标持股的已观察6个月标签计算，未观测结果另列，不能称实际持有重大亏损比例。S2相对S1事件占比差约−0.10个百分点，95%区间跨零；匹配格后差约−0.03个百分点，区间也跨零。静态过滤没有显示独立稳定优势，且连续波动率暴露仍不同。

**可执行经济分支停止。** 退市结算、停牌/复牌可交易性、重整/配股等特殊公司行动未认证，不能可靠计算实际持股、日/月ES、最大回撤、扣费累计/年化收益、机会成本及实际暴露漂移。原定100万元、10%参与率、单边10/30bp的参数保留，未伪造成本回测。未把目标等权曲线或简单前复权价格拼接当实盘验证。

该未执行原因满足Goal允许的数据停止条件，不能转述为“经济价值已被否定”。目标名单哈希、月度事件/风格、行业权重及原计划均交付；需要未来结算数据闭合后另设真实经济验证。
""")
    neg=pd.DataFrame([dict(model=x['model'],passed=x['passed'],**x['industry_auc_minus_half']) for x in controls['negative']['checks']])
    power=primary[primary.block==12][['candidate','months','approximate_blocks','estimate','se','detectable_80pct_effect_approx']]
    write('statistical_validation.md',f"""
# 统计有效性、功效和程序控制

月均而非股票逐行独立推断；整个同月横截面一同进入 stationary bootstrap。固定10000次、种子2801，块6/12月，主四假设Bonferroni 98.75%区间（包括未运行H3）。95%为名义区间，不能挑出辅助指标的显著性作为主检验成功。

59月在12月块下约4.92个块，实际有效信息有限。近似80%可检出效应=2.8×块标准误，不是严格小样本功效保证：

{table(power)}

L2点估计约−.0016，小于此处约.0041的近似检出尺度。不能从未显著推断精确零效应；也不能因点估计有利宣布成功。所有已注册模型、两阶段、逐月/逐年删除均完成，保留完整状态和行业结果。

三种正控制：

{table(pos,['world','estimate','low95','high95','passed'])}

同月同行业标签置乱（原事件数量/缺失位置保持）行业AUC−.5：

{table(neg,['model','estimate','low95','high95','low_family','high_family','passed'])}

负控制没有移除共同/行业发生率，所以总体Brier还可能有差异；检验对象是组内个股身份信息。三个固定强信号正控制通过仅证明程序能识别对应人工结构，不保证小真实信号的统计功效。

20项历史核心测试在评分前通过；额外前瞻时点测试在前瞻封存前通过。验证器重放全部198个分类模型、88个置乱模型和88个偏度回归；独立重建逐月Brier/预警、主配对区间、滚动校准、匹配和持股规则，检查1,739份旧文件。实际执行回执见 `outputs/audits/validation.json`，不以文件存在代替通过。

第一次启动在读取EP27季度文件前因路径少了P2_失败，未发生任何拟合；原注册保留为 `preregistration_v1_before_path_fix.json`，路径更正与无规格变化声明在当前注册。其余结果没有按效果调整参数。报告/复核/前瞻操作工具评分后另列支持代码清单，不能追溯称全部预注册。
""")
    write('final_conclusion.md',f"""
# 最终结论

**在本研究的信息集、固定D0历史样本和有限候选下，没有发现已被统计与校准共同支持的稳定6个月重大亏损概率预测优势。** L2风险结构有值得前瞻检验的历史排序线索，但主Brier相对M_R的区间跨零、前后阶段变号、校准漂移明显。真实独立样本尚不存在，经济可执行性未验证。

主要实用对照M_R的Brier=0.138095，不能以击败较弱的M_RMI代替：

{table(primary6,cols)}

完整两块长、四重区间、基线/消融与覆盖见[匹配增量报告](matched_incremental_tests.md)和 `paired_intervals.csv`。

## Q1 哪些机制可可靠复现？

可以核验并实现部分Kelly–Jiang尾指数/滞后暴露及CHS偏度公式，得到有限A股代理迁移；Goal要求的风险结构分解另行实现。**没有完成任何原市场Level A忠实复现**，也没有认证全A股PIT完整样本。五份全文版本有明确标记，四项正文不足停止对应忠实分支。

## Q2 市场共同风险还是个股特有风险？

两者需分别评价。L2整体Brier改善的点估计中，共同误差约贡献−.001078；个股残差误差项约+.000055，未显示额外改善。另一方面，L2在同月行业内部及有限风险匹配组有排序线索。误差会计不能给出“实际亏损有多少由市场因果解释”的比例，更不能把排序改善等同于概率校准改善。

## Q3 特质波动比总波动更有价值吗？

风险结构整组相对M_R的点改善约1.15%，95%区间跨零；相对去残差风险的消融有历史改善，支持继续检验这一信息来源。L2不是单一特质波动变量，包含系统性与行业结构；不能将整组效果归为单因子。RMI_L2相对M_RMI仅有名义区间支持，四重区间跨零，未证明稳定超越所有控制。

## Q4 困境恶化速度比静态指标更强吗？

**证据不足，真实L3停止。** 首次公告版本、完整构造字段及失败标签不足。人工变化信号正控制通过不是A股实证。不能得出机制不存在或模型无效。

## Q5 换手、涨幅、不透明度及分歧有估值以外增量吗？

L4价格/换手代理对−20%主事件未显示整体稳定优势；加入换手的同组消融也无确认增量。独立NCSKEW/DUVOL目标的整组预测改善表明标签迁移很关键，但不能当作主事件成功。估值×分歧、真实文本和财务不透明度分支因版本/正文缺口未运行，无法回答“估值之外”的完整问题。

## Q6 控制行业、市值、波动率后能改善概率吗？

整体稳定改善**尚未获支持**。行业AUC仅覆盖约39.95%已知股票月，风险格约7.20%；连续匹配覆盖更低。L2在有限匹配样本的事件差为正，但扩展控制下相应匹配区间跨零。不能外推为全A股或所有股票状态优势。

## Q7 排序是否同时转化为校准和可比组合风险？

没有。月均ECE约.11–.12，固定成熟历史截距校准反而变差。事前指定L4的5%过滤相比M_R，静态持有目标事件差区间跨零；行业风险格匹配后也无稳定差异。真实ES/净收益等因结算与可交易性缺口停止，不能声称已做实盘可执行验证。

## Q8 哪些可以进入独立前瞻？

当前所有效果均属反复使用历史样本的探索结果。按原注册保留L1/L2/L4及消融，**不因L2历史最好就另选冠军**；与EP27共享同日未来队列，实际当日形成预测与哈希，六个月后另附标签，36/48/60成熟月检查。见[前瞻协议](../validation_protocol.md)。当前没有独立确认、没有自动部署或交易建议。

## 支持、不支持和证据不足

- **支持的有限事实：** 程序能识别三类人工信号；部分CHS代理对偏度目标有历史改善；风险结构/残差风险组有历史排序和消融线索。
- **不支持的主张：** 当前模型已具稳定绝对亏损概率优势；共同尾指数或交易分歧代理整体优于M_R；排序优势自动转化为校准或经济收益。
- **证据不足：** L2真实效应是否持续；困境变化、原文未取得分支、估值交互和文本机制；无偏全A股推广、独立前瞻确认及真实组合经济价值。

限制不是单一“算法不够复杂”：可用信息/原始版本不完整、退市结算及股票池偏差、59个重叠月的统计功效、非平稳校准和已重复研究的历史共同限制结论。固定算法不是所有算法的穷尽检验；不能因本轮结果否定全部理论机制，也不能因此自动扩大搜索。

全部注册可实施候选、消融、B级迁移、正负控制和审计完成；不可实施项有明确证据边界。研究在此停止，不以产生正面结果为完成条件。
""")
    figures()
    print('11 research reports rendered',flush=True)


def figures():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    rel=read('reliability_monthly');rel['weight']=rel.rows/rel.groupby(['model','date']).rows.transform('sum')
    fig,ax=plt.subplots(figsize=(7,5))
    for name in ['M_R','L1','L2','L4']:
        g=rel[rel.model==name];points=[]
        for _,z in g.groupby('bin'):points.append([np.average(z.predicted,weights=z.weight),np.average(z.observed,weights=z.weight)])
        p=np.array(points);ax.plot(p[:,0],p[:,1],marker='o',label=name)
    ax.plot([0,1],[0,1],'k--',alpha=.5);ax.set(xlabel='Forecast loss probability',ylabel='Observed event rate',title='Reliability: equal origin-month mixture')
    ax.legend();fig.tight_layout();fig.savefig(OUT/'reliability.png',dpi=180);plt.close(fig)
    c=read('conditional_scores');c=c[(c.dimension=='year')&c.model.isin(['M_R','L1','L2','L4'])]
    grid=c.pivot(index='model',columns='condition',values='bias').reindex(['M_R','L1','L2','L4'])
    fig,ax=plt.subplots(figsize=(8,3));im=ax.imshow(grid,cmap='RdBu_r',vmin=-.25,vmax=.25)
    ax.set(xticks=range(len(grid.columns)),xticklabels=grid.columns,yticks=range(4),yticklabels=grid.index,title='Annual mean probability bias (forecast minus realized)')
    for i in range(4):
        for j in range(len(grid.columns)):ax.text(j,i,f'{grid.iloc[i,j]:.3f}',ha='center',va='center')
    fig.colorbar(im,ax=ax);fig.tight_layout();fig.savefig(OUT/'yearly_bias.png',dpi=180);plt.close(fig)
    t=read('paired_intervals');t=t[(t.metric=='brier')&(t.baseline=='M_R')&t.candidate.isin(['L1','L2','L4'])&(t.block==6)]
    fig,ax=plt.subplots(figsize=(7,3));ax.errorbar(t.estimate,range(3),xerr=[t.estimate-t.low95,t.high95-t.estimate],fmt='o',capsize=4)
    ax.axvline(0,color='black',linestyle='--');ax.set(yticks=range(3),yticklabels=t.candidate,xlabel='Brier difference vs M_R (negative is better)',title='Primary historical comparisons: 95% block-6 intervals')
    fig.tight_layout();fig.savefig(OUT/'primary_intervals.png',dpi=180);plt.close(fig)


if __name__=='__main__':main()
