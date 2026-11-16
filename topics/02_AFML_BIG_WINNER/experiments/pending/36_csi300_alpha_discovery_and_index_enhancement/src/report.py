"""Chinese delivery with primary blockers separate from valuation sensitivities."""
import json
import numpy as np,pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from common import *
from summarize import metrics
MODELS=['E0-MOM','E0-REV','E0-RES','E0-MIX','E1','E2','E3']

def percent(x):return '—' if pd.isna(x) else f'{x:.2%}'
def decimal(x):return '—' if pd.isna(x) else f'{x:.4f}'
def table(rows,headers):return '| '+' | '.join(headers)+' |\n|'+'|'.join(['---']*len(headers))+'|\n'+'\n'.join('| '+' | '.join(map(str,r))+' |' for r in rows)+'\n'

def main():
 dest=EP/'reports';dest.mkdir(exist_ok=True)
 rk=pd.read_csv(OUT/'path_a/expanding_ranking_summary.csv');primary=rk.loc[rk.horizon.eq('h10')&rk.seed.isin(['fixed','equal_seed_ensemble'])].set_index('model').loc[MODELS]
 roll=pd.read_csv(OUT/'path_a/rolling36_ranking_summary.csv');roll=roll.loc[roll.horizon.eq('h10')&roll.seed.isin(['fixed','equal_seed_ensemble'])].set_index('model')
 ac=pd.read_csv(OUT/'account_metrics.csv');mainac=ac.loc[ac.scheme.eq('expanding')&ac.scenario.eq('weekly')&ac.cost.eq('main')].set_index(['path','model'])
 rows=[]
 for model,r in primary.iterrows():
  a=mainac.loc[('A',model)];b=mainac.loc[('B',model)];rows.append([model,decimal(r.mean_rank_ic),f'[{r.ic_ci_low:.4f}, {r.ic_ci_high:.4f}]',decimal(roll.loc[model,'mean_rank_ic']),percent(r.mean_q5_q1),str(a.failure_date)[:10],str(b.failure_date)[:10]])
 comparison=table(rows,['模型','H10 RankIC','95% 时间块区间','rolling36 RankIC','H10 Q5−Q1 均值','A 严格账户中止','B 严格账户中止'])
 fig,ax=plt.subplots(figsize=(9,4.5));y=np.arange(len(primary));ax.errorbar(primary.mean_rank_ic,y,xerr=np.vstack([primary.mean_rank_ic-primary.ic_ci_low,primary.ic_ci_high-primary.mean_rank_ic]),fmt='o',capsize=4,color='#245c94');ax.set_yticks(y,primary.index);ax.axvline(0,color='gray',linewidth=1);ax.invert_yaxis();ax.set_xlabel('Mean weekly H10 RankIC; 95% 13-week block interval');ax.set_title('CSI 300 historical simulated OOS: 2021–2026');ax.grid(axis='x',alpha=.2);fig.tight_layout();fig.savefig(dest/'rank_ic.png',dpi=160);plt.close(fig)
 fig,axes=plt.subplots(1,2,figsize=(12,4))
 for path,ax in zip(['A','B'],axes):
  for model in MODELS:
   f=pd.read_csv(OUT/'accounts'/f'expanding_weekly_{path}_{model}_main.csv',parse_dates=['date']);ax.plot(f.date,f.nav,label=model,linewidth=1.3)
  ax.set_title(f'{path}: strict account valid prefixes ONLY');ax.set_ylabel('NAV (initial capital = 1)');ax.grid(alpha=.2);ax.tick_params(axis='x',rotation=25)
 axes[1].legend(fontsize=8,ncol=2);fig.suptitle('Stopped at missing held prices; NOT full-period performance');fig.tight_layout();fig.savefig(dest/'ab_strict_prefix_nav.png',dpi=160);plt.close(fig)
 # Separate sensitivity summaries, retaining every termination and differing benchmark horizon.
 sens=[]
 for scenario in ['suspend_flat','suspend_haircut20']:
  sd=OUT/'sensitivity'/scenario
  for path in ['A','B']:
   control='EW' if path=='A' else 'B0';bench=pd.read_csv(sd/(path+'_'+control+'.csv'),parse_dates=['date']).set_index('date').nav
   for model in MODELS+[control]:
    key=path+'_'+model;f=pd.read_csv(sd/(key+'.csv'),parse_dates=['date']).set_index('date');r=json.loads((sd/(key+'.json')).read_text());ix=f.index.intersection(bench.index);m=metrics(f.nav.loc[ix],bench.loc[ix]) if len(ix) else {}
    sens.append(dict(scenario=scenario,path=path,model=model,days=len(f),start=f.index.min(),end=f.index.max(),completed=not r['failures'],failure_date=r['failures'][0]['date'] if r['failures'] else '',failure_instruments=r['failures'][0]['instruments'] if r['failures'] else '',available_prefix_total_return=f.nav.iloc[-1]-1,matched_days=len(ix),matched_relative_nav_cagr=m.get('relative_nav_cagr') if len(ix)>=252 else np.nan,quality='NONCERTIFIED_SUSPENSION_MARK_SENSITIVITY'))
 sf=pd.DataFrame(sens);sf.to_csv(OUT/'sensitivity/suspension_account_summary.csv',index=False)
 sensible=table([[r.scenario,r.path,r.model,r.days,r.matched_days,str(r.failure_date)[:10] or '至数据截止',r.failure_instruments or '—',percent(r.matched_relative_nav_cagr)] for r in sf.loc[sf.model.isin(['E1','E2','E3','EW','B0'])].itertuples()],['估值情景','路径','模型','有净值日数','与对照共同日数','中止日','缺价持仓','共同段相对年化（代理）'])
 # Yearly ranking is complete even where account years are blocked.
 yearly=pd.read_csv(OUT/'path_a/expanding_ranking_year.csv');yearly=yearly.loc[yearly.horizon.eq('h10')&yearly.seed.isin(['fixed','equal_seed_ensemble'])].pivot(index='year',columns='model',values='rank_ic').reindex(columns=MODELS)
 yr=table([[int(year)]+[decimal(v) for v in r] for year,r in yearly.iterrows()],['年份']+MODELS)
 validation=json.loads((OUT/'manifests/final_validation.json').read_text());replay=json.loads((OUT/'manifests/model_replay.json').read_text());coverage=pd.read_csv(OUT/'data_audit/weekly_coverage.csv');states=pd.read_csv(OUT/'data_audit/execution_and_weights_weekly.csv');oos=states.loc[states.signal_date>='2021-01-01'];nvalid=int(oos.benchmark_status.eq('RECONSTRUCTED_PROXY').sum())
 introduction='''# EP36：沪深300 Alpha 初步验证与指数增强

**结论：存在历史排序线索，但尚不能认定 Q5 长仓具有成本后价值或 B 实现净增强。** Ridge 是本轮更稳定的排序基线；LightGBM 主模型没有显示出稳健的增量优势。严格账户因持仓缺价受阻，正式 B 还缺少权重历史可用时间与一致的官方全收益比较。

证据身份为 `historical_simulated_oos`，前瞻保持 `FORWARD_PENDING`。行情为 2017-01-03—2026-10-21，完整周信号止于 2026-10-16；外层季度为 2021Q1—2026Q4，2026Q4 仅是截至数据端点的部分季度。没有实盘、自动监控或真实前瞻验收。

## 模型对照

'''
 text=introduction+comparison+'''
Q5−Q1 是固定 H10 标签的分组均值差，不是可执行多空收益，也不能拼成净值。RankIC 使用可评分且标签已知证券；未知标签不填零。区间使用 13 周时间块、2,000 次抽样，保留同周截面和重叠标签的时间结构。7 个登记模型、多个固定分支均完整披露，没有家族显著性校正，不把事后领先者视为新盲测胜者。

![RankIC](rank_ic.png)

## A/B 严格账户净值

'''+f'192 个登记账户分支均已实际运行，并在第一个不能可靠估值的持仓端点停止；其中 {validation["valuation_blocked_branches"]} 个因估值缺口中止。以下曲线仅表示中止前的可核对区间，不能横向比较不同终点，更不能作为 2021—2026 的完整回测。\n\n'+'''![A/B严格账户可核对区间](ab_strict_prefix_nav.png)

典型阻断：SH600340（华夏幸福）2021-01-29 停牌无当日行情；SZ002352（顺丰控股）2021-02-05 停牌无行情。严格规则没有将旧价写成当日真实净值。证券、日期、账户和原因见 `outputs/data_audit/account_valuation_failures.csv`；费用、未成交、现金和持仓在私有逐笔/逐日账本中保留哈希。

## 逐年排序与账户覆盖

'''+yr+'''
2026 为不完整年度。逐年/逐季度账户文件显式填列中止后的 `BLOCKED_AFTER`，对应收益留空；短区间年化只在 `account_metrics.csv` 中作为可核对前缀诊断，不用于主模型裁决。少于两个 13 周时间块的账户区间不估计置信区间。

## 四个问题分别回答

1. **有没有排序信息？** expanding 下 E1/E2/E3 的平均 RankIC 及时间块区间均为正；rolling36 下 E2/E3 区间穿过零，Ridge 仍为正。因此有历史线索，但树模型的窗口稳定性不足。
2. **Q5 是否成本后有价值？** 严格账户中止，不能认证完整时期结论。即使 Q5−Q1 为正，也可能主要来自低分组较差；分组诊断和账户净收益分别保留。
3. **B 是否有净增强？** 正式 B 未获证明。重建权重代理和停牌估值敏感性不能替代正式 B，特别是调样空档、公司行动终值和基准口径仍未闭合。
4. **LightGBM 是否比简单方法有增量？** 主 E2 的 RankIC 低于 Ridge；两者配对差异未支持 E2 的可靠优势。E3 在 expanding 相对 E2 改善，但 rolling36 仍不稳定，不能据此事后选择赢家并升级证据。

## 估值敏感性（不替换严格结果）

在完整停复牌列表确认“全天停牌”且无报价的日期，单列上一已知前复权收盘估值最多 20 个市场日，以及该估值折价 20% 两种情景。该价格不是实际报价，不参与特征、标签或成交；订单仍需真实未复权开盘和交易状态。无停牌依据、超出 20 日或无法处理换股终值仍中止。

'''+sensible+'''
完整结果：`outputs/sensitivity/suspension_account_summary.csv`。部分 A 账户可延伸至数据截止，但对照账户会因海通证券等合并换股终值缺口提前中止；因此“完成自身净值”和“具有完整匹配基准”必须分开。B 还会受到调出遗留、终止上市和不可交易持仓影响。上述代理不得用于宣称已建立真实权益账本。

## 数据、时点与执行限制

'''+f'- 共 607 只历史成分股，501 个完整周信号，每周原始成员 300；78 个核心和 12 个扩展特征。\n- 全历史只有 177/501 周可按原始报价规则重建完整基准；外层为 {nvalid}/{len(oos)} 周。其余周原因包括成分快照不一致、权重基准日或执行日缺价。代理 B/B0 明确跳过这些调仓，保留真实已有仓位，不把新成分未知权重设为零。\n'+'''- 成分来自 BaoStock 每周历史快照，保留 updateDate；只能标为历史代理，不能证明日内临时调样和首次发布版本。跨周标准化按当时快照向后使用，禁止当前成员回填。
- Tushare 月度权重没有历史发布时间；本轮仅在快照日期之后的市场收盘可用，并用已发生报价漂移，不读未来快照。调样与公司行动仍有缺口，因此正式 B 受阻。
- 交易状态：完整停复牌日期分区与原始涨跌停报价交叉核验；2 条来源冲突与其他无法解析状态保留未知。不开盘成交能力、排队数量与实际冲击仍未经认证。
- 行业为历史区间代理，不能宣称严格历史行业中性。官方 CSI300 为价格指数；与前复权账户比较仅作价格指数诊断，不能当作一致全收益超额。B0/EW 为同引擎账户，不能代替官方指数。
- 前复权单位账本从头到尾使用同一 qfq 开收盘；原始价格仅用于交易状态与限价检查，没有混算真实股数和前复权价格。单位审计 1,322,377 条量额报价中，VWAP/原始收盘的 0.1%—99.9% 分位约为 0.950—1.049，无 100 倍单位错配证据。
- 特征文档限制：冻结字典中 `ret_lag0` 与 `mom1` 是完全重复的两列；训练前未另存单独去重审计。本轮保持原字典与预测，不在看过结果后删列重训。详见 `outputs/data_audit/feature_duplicate_audit.json`。
- 不因退市、未来标签缺失或表现差删除历史成员；不为持仓未知终值填零。原始数据与模型置于 Git 忽略的 `private/`，没有提交或推送。

## 固定稳健性与版本记录

已运行 expanding/rolling36，周频/固定双周/延迟一交易日，三种成本，H5/H20 同预测期限敏感性，三种子及等权组合，逐年/季度、同证券配对、完整标签日期、排除既有复权争议证券的敏感性。所有路径共享同一封存预测；没有为成本情景重训。

执行 v1 发现历史交易状态字段缺失，账户大量持有现金，已经归档并撤销作为策略证据；v2 在查看该诊断后补齐历史停复牌数据。随后修复完全清仓浮点残留及 QP 极小误差可能触发非成员买入的问题，最终 v2.2 增加硬成员买入门。经济参数和模型预测未变；前序结果保存在 `outputs/archive/` 与 `private/archive/`。停牌估值情景也是见到缺口后登记的敏感性，不冒充预先未见结果。今后若补齐合并换股权益，应另开执行版本，不能覆盖当前阻断记录。

## 验证与文件

'''+f'- 工程交付检查：{validation["status"]}，{len(validation["checks"])} 项；它不等于金融结论认证。\n- 14 项时间/账户单元测试通过；另有 32 个估值敏感性账本审计通过。\n- 48 个季度/窗口折、336 个 Ridge/LightGBM 模型重放，最大预测差为零；三种子等权平均和 A/B 消费哈希一致。\n'+'''- 主表：`outputs/model_comparison.csv`；逐年：`outputs/annual_performance.csv`；逐季度：`outputs/quarterly_performance.csv`。
- A 独立报告：[A_report_cn.md](A_report_cn.md)；B 独立报告：[B_report_cn.md](B_report_cn.md)。
- 实际可用范围与失败清单：`outputs/data_audit/`；预测、模型与账户凭据：`outputs/manifests/`；完整预测：`outputs/fold_predictions/`。
- 官方接口依据：[月度指数权重](https://tushare.pro/document/2?doc_id=96)、[每日停复牌](https://tushare.pro/document/2?doc_id=214)。原始版本、来源哈希及参数保存在本轮采集凭据中。
'''
 (dest/'REPORT.md').write_text(text)
 (dest/'A_report_cn.md').write_text('# A：排序与 Q5 长仓独立裁决\n\n排序存在历史线索；完整成本后长仓价值仍受估值缺口阻断。A 的结果不用于取消 B。\n\n'+comparison+'\n![排序区间](rank_ic.png)\n\n'+yr+'\n严格账户使用下一市场开盘调仓、五等分 Q5 等权和真实现金扣费。所有成本及固定调仓敏感性均已运行至可核对终点；停牌无报价直接中止。不可将 H10 重叠标签均值拼接为净值。\n\n停牌估值与折价情景仅为独立代理诊断：\n\n'+sensible+'\n同证券 E2/E3 与基线配对、来源差异排除、缺失标签敏感性见 `../outputs/sensitivity/`。完整时点和数据限制见 [总报告](REPORT.md)。')
 (dest/'B_report_cn.md').write_text('# B：受约束增强独立裁决\n\n**正式沪深300净增强未获证明；A 排序偏弱或偏强均不替代本裁决。**\n\n'+comparison+'\n围绕历史月度权重漂移的基准，用固定排名倾斜和欧氏投影，约束个股、行业、换手与现金。未知分数留零倾斜；不可交易持仓优先保留，求解不可行状态和实际偏离逐次记录。初始建仓计费，后续换手包含现金。\n\n历史权重发布时间缺失、调样空档和前复权/官方价格指数口径不同使正式 B 受阻。代理 B/B0 对基准缺失日期跳过调仓，是单独的受限代理，而非完整正式协议的实现结果。严格账户另外在真实持仓缺价处中止。\n\n'+sensible+'\nB0 是带相同交易时钟的账户，战胜 B0 不等于战胜官方指数；本轮更不能将短区间或不完整代理的正估计升级为净增强。详见 [总报告](REPORT.md) 与 `../outputs/data_audit/benchmark_price_gaps.csv`。')
 print('reports written',dest)
if __name__=='__main__':main()
