import pandas as pd
from common import *

def run():
    out=ROOT/'outputs/r13';inc=pd.read_csv(out/'increments.csv');summary=pd.read_csv(out/'summary.csv');receipt=json.loads((out/'receipt.json').read_text())
    table=[]
    for row in inc.query("lag==45 and horizon==20 and baseline=='F'").itertuples():
        delayed=inc[(inc.era==row.era)&(inc.level==row.level)&(inc.lag==75)&(inc.horizon==20)&(inc.baseline=='F')].iloc[0]
        table.append(f'| {row.era} | {row.level} | {row.months} | {row.delta_ic:+.4f} | [{row.adjusted_low:+.4f}, {row.adjusted_high:+.4f}] | {delayed.delta_ic:+.4f} |')
    text="""# R13 宏观状态与事前行业敏感度

## 想验证什么

宏观值同日由行业共享，不能直接作为横截面区分变量。本轮检验两项有限假说：增长敏感行业对制造业景气状态反应不同；融资敏感行业对M2同比加速反应不同。M2不代表股票购买力，经验敏感度也不是因果传导系数。原始来源由R11恢复，实验前冻结 protocols/r13.json。

本轮覆盖SW2014二/三级、SW2021一/二/三级；原分类断点分开处理，一级使用R05合成历史成员篮子，没有补造SW2014一级。没有更改EP32—34，也没有下载新数据。

## 时点、敏感度与对照

制造业PMI状态为(PMI−50)/100；货币状态为M2同比的精确三个统计月变化/100。经济月份缺失时不压缩，不填零。主时钟为所属月末加45日，敏感性时钟加75日；必须严格早于信号日。两者都是历史代理假设，不是已认证的原始发布日期，不能排除数据修订。

逐行业用信号日前36个日历月内、至少24个完整月度观测估计敏感度。因变量为历史s日已知的过去20日市场超额，解释变量为s前一个完整月末已知的宏观状态；不是用未来20日标签回归当前宏观。只在历史窗口内计算均值、标准差，联合Ridge alpha=1、有截距，保存系数和最后训练日期。这里的过去20交易日与自然月长度并不完全一致。

固定敏感度分数取两个标准化斜率的平均；宏观条件分数取斜率乘当前宏观相对训练均值的标准化偏离后加总。它们分别先在行业横截面中心化秩变换，再与原R01价格分数各占50%。保留三种方法：F价格、F_exposure价格加固定敏感度、F_macro价格加宏观条件分数。比较F_macro对F，及F_macro对F_exposure，防止把静态行业暴露误当作状态择时。

两个时钟和三种方法使用相同行业日期，至少20个行业才评价；缺少成熟收益不影响先行选择，前20%中任一目标缺失则整组收益未知，不换入其它行业。20日主期限、60日次期限，次日收盘入点。日期等权IC与年度结果全部保留。

## 发现什么

共保存"""+str(receipt['sensitivity_rows'])+"""个行业时点/时钟敏感度估计，双时钟共同可估计原点"""+str(receipt['common_origins'])+"""个；评价表"""+str(receipt['date_metric_rows'])+"""行。共同原点尚需满足价格和每期行业数量门槛，不能把这些计数都称为有效交易机会。

以下是宏观条件版本相对价格基准的20日Rank IC增量。区间采用6个可评价月为一块的循环bootstrap、2000次，并对5个分类层级×2个基准共10项主比较作Bonferroni调整；75日结果为预先登记的延迟敏感性，不能择优替换45日主结果。

| 分类 | 层级 | 配对月数 | 45日主时钟ΔIC | 多重调整区间 | 75日时钟ΔIC |
|---|---|---:|---:|---|---:|
"""+'\n'.join(table)+"""

主时钟下五个分类/层级的增量均为负，所有调整区间均跨0。相对固定敏感度版本，SW2014二/三级有正均值，但仍不满足调整区间要求；SW2021三个层级为负。没有一项通过事前增量标准。不能因为部分75日结果较好而把主口径改为75日；时钟敏感性本身是稳定性边界。

顶部分组收益、单边20/50基点诊断以及60日次要结果全部保存在summary.csv和annual.csv。各组完整目标月份可能不同，因此分组收益均值不能在忽略缺失选择的情况下代替严格配对IC。这里的成本仅按每个固定持有窗口进入/退出各一次扣减，不是换手优化、连续策略曲线或真实可执行成交。

## 能与不能下的结论

该具体经验敏感度与两项宏观状态的固定合成没有改善行业排序；不能据此否定宏观对行业盈利的经济作用，也不能泛化为所有宏观变量无用。可能解释包括状态滞后、宏观历史修订、线性敏感度不稳定，以及价格已反映信息。本轮没有通过增加窗口、指标或动态权重来挽救失败。

结果属于反复使用历史的模拟，而不是独立前瞻验证。历史成员、复权与行业篮子代理限制延续；没有全风格控制，也不能从经验敏感度命名已证实的经济阶段。已有经济所属期与可用时钟清楚，但真实初发/修订版本仍不足以称严格PIT。

## 验证与分支决定

独立验证用正规方程重算分层抽样的敏感度，并核验全部训练截止、至少24观测、两种时钟下相同价格基准，以及逐期所有顶部名单在结果前选定。单元测试覆盖严格日期边界、缺失统计月、未来宏观记录不改变历史对齐，以及最小样本和零方差。

本分支保留失败并停止无依据参数搜索。下一项有依据的研究可转回新报告修正事件的价格响应，以补足R12月末快照无法定位事件时点的缺口；产业供需原文与真实数据版本仍单独补充，不将本轮宏观代理当作产业领先证据。整体EP35仍未完成。

复现：src/macro_r13.py；独立验证：src/verify_r13.py；本报告：src/report_macro.py。所有原始来源和协议哈希在outputs/r13/receipt.json，敏感度、当前/滞后状态和训练窗口记录在data/r13_*。
"""
    (ROOT/'reports/R13_宏观状态与行业敏感度.md').write_text(text)
    fields=pd.read_csv(ROOT/'outputs/factor_dictionary.csv').columns
    row=dict(module='A',factor='PMI_M2_prior_sensitivity_interaction',theory='增长与融资状态对行业现金流及折现条件的差异影响',formula='sum(beta_j * (state_j-train_mean_j)/train_sd_j)',direction='经验敏感度方向，待验证',applicable_industries='各分类层级内>=24历史观测，横截面>=20行业',economic_date='PMI及M2统计月份',publication_date='未逐月核验',available_at='月末+45日主/+75日敏感性，严格早于信号',frequency='月',source='R11本地宏观JSON与R01/R05历史篮子',historical_revisions='现时历史表，修订版本未认证',aggregation='PMI及M2联合历史Ridge，宏观条件秩分数与价格各50%',missing_rule='缺失不压缩统计月份；两时钟共同母体；不补零',failure_condition='同样本价格控制已解释；延迟后不稳；主增量未通过',replication_status='EP35扩展Historical-proxy，本轮未确立增量',horizon='主20/次60交易日')
    pd.DataFrame([row],columns=fields).to_csv(out/'factor_dictionary.csv',index=False)
if __name__=='__main__':run()
