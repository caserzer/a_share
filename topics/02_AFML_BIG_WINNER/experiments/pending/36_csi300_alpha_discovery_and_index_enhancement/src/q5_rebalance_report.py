"""Complete Markdown and self-contained HTML report for the Q5 frequency experiment."""
import base64,json,re
import numpy as np,pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import markdown
from common import EP,OUT,PRIVATE,sha,save_json
from q5_rebalance_sensitivity import DEST,CONFIG,MODELS,FREQUENCIES

REPORT=EP/'reports/q5_rebalance_20261116'
LABEL={'1w':'1周','2w':'2周','1m':'1月'}
COLOR={'1w':'#2864a0','2w':'#e69b27','1m':'#21936f'}

def pct(x):return '—' if pd.isna(x) else f'{x:.2%}'
def pp(x):return '—' if pd.isna(x) else f'{x*100:+.2f}'
def num(x):return '—' if pd.isna(x) else f'{x:.2f}'
def table(headers,rows):
    return '| '+' | '.join(headers)+' |\n|'+'|'.join(['---']*len(headers))+'|\n'+'\n'.join('| '+' | '.join(str(x) for x in r)+' |' for r in rows)+'\n'
def ordered(f):
    f=f.copy();f['m']=pd.Categorical(f.model,MODELS,ordered=True);f['q']=pd.Categorical(f.frequency,FREQUENCIES,ordered=True)
    return f.sort_values(['m','q']).drop(columns=['m','q'])

def main():
    REPORT.mkdir(parents=True,exist_ok=True)
    config=json.loads(CONFIG.read_text());period=json.loads((DEST/'comparison_periods.json').read_text());validation=json.loads((DEST/'validation.json').read_text());assert validation['status']=='PASS'
    allm=pd.read_csv(DEST/'all_metrics.csv');main=ordered(pd.read_csv(DEST/'model_frequency_comparison.csv'));inv=pd.read_csv(DEST/'account_inventory.csv');annual=pd.read_csv(DEST/'primary_annual.csv');pairs=pd.read_csv(DEST/'paired_frequency_differences.csv');curves=pd.read_parquet(DEST/'primary_curves.parquet')
    common_end=period['main_common_end'][:10];anchor=period['signal_close_anchor'][:10]
    benchmark=main.benchmark_cagr.iloc[0]
    price=allm.loc[allm.scope.eq('main_common')&allm.valuation.eq('suspend_flat')&allm.cost.eq('main')&allm.benchmark.eq('CSI300_PRICE')].benchmark_cagr.iloc[0]
    for relative,name in [(False,'net_nav'),(True,'relative_nav')]:
        fig,axes=plt.subplots(1,3,figsize=(14,4.4),sharex=True)
        for ax,model in zip(axes,MODELS):
            for frequency in FREQUENCIES:
                f=curves.loc[curves.model.eq(model)&curves.frequency.eq(frequency)].sort_values('date')
                ax.plot(pd.to_datetime(f.date),f.relative_nav if relative else f.nav,label=frequency,color=COLOR[frequency],linewidth=1.7)
            if relative:ax.axhline(1,color='#555555',linestyle='--',linewidth=1)
            else:ax.plot(pd.to_datetime(f.date),f.benchmark_nav,label='CSI300 total return',color='#777777',linestyle='--',linewidth=1.2)
            ax.set_title(model);ax.grid(alpha=.2);ax.tick_params(axis='x',rotation=25);ax.legend(fontsize=8)
        axes[0].set_ylabel('Portfolio NAV / benchmark NAV' if relative else 'Net NAV; initial capital = 1')
        fig.suptitle(f'Q5 equal weight | main costs | {anchor} to {common_end}\nExplicit suspension-value proxy; identical comparison dates')
        fig.tight_layout();fig.savefig(REPORT/(name+'.png'),dpi=160);plt.close(fig)
    # Drawdown paths use the initial capital point in running peaks.
    fig,axes=plt.subplots(1,3,figsize=(14,3.8),sharex=True)
    for ax,model in zip(axes,MODELS):
        for frequency in FREQUENCIES:
            f=curves.loc[curves.model.eq(model)&curves.frequency.eq(frequency)].sort_values('date');peak=np.maximum.accumulate(np.r_[1.,f.nav.to_numpy()])[1:]
            ax.plot(pd.to_datetime(f.date),100*(f.nav/peak-1),label=frequency,color=COLOR[frequency])
        ax.set_title(model);ax.grid(alpha=.2);ax.tick_params(axis='x',rotation=25)
    axes[0].set_ylabel('Net NAV drawdown (%)');axes[-1].legend(fontsize=8);fig.tight_layout();fig.savefig(REPORT/'drawdowns.png',dpi=160);plt.close(fig)
    columns=['模型','调仓','净年化收益','对全收益指数年化差（百分点）','相对净值年化','最大回撤','年化单边换手（倍）']
    core=table(columns,[[r.model,LABEL[r.frequency],pct(r.cagr),pp(r.cagr_difference),pct(r.relative_nav_cagr),pct(r.max_drawdown),num(r.annual_one_way_traded_ex_initial)] for r in main.itertuples()])
    risk=table(['模型','调仓','IR','TE','相对净值最大回撤','平均现金','平均持仓数'],[[r.model,LABEL[r.frequency],num(r.information_ratio),pct(r.tracking_error),pct(r.relative_max_drawdown),pct(r.mean_cash),num(r.mean_holdings)] for r in main.itertuples()])
    costs=allm.loc[allm.scope.eq('main_common')&allm.valuation.eq('suspend_flat')&allm.benchmark.eq('CSI300_TOTAL_RETURN')].pivot(index=['model','frequency'],columns='cost',values='cagr')
    costtable=table(['模型','调仓','零成本年化','主成本净年化','压力成本净年化','零成本−主成本（百分点）'],[[m,LABEL[q],pct(costs.loc[(m,q),'zero']),pct(costs.loc[(m,q),'main']),pct(costs.loc[(m,q),'stress']),pp(costs.loc[(m,q),'zero']-costs.loc[(m,q),'main'])] for m in MODELS for q in FREQUENCIES])
    yearrows=[]
    for year,g in annual.groupby('year'):
        row=[str(year)+('（部分）' if year in [int(anchor[:4]),int(common_end[:4])] else '')]
        z=g.set_index(['model','frequency'])
        for m in MODELS:
            for q in FREQUENCIES:row.append(pp(z.loc[(m,q),'excess_difference']))
        yearrows.append(row)
    yeartable=table(['年份']+[m+' '+LABEL[q] for m in MODELS for q in FREQUENCIES],yearrows)
    netyeartable=table(['年份']+[m+' '+LABEL[q] for m in MODELS for q in FREQUENCIES],[[str(year)+('（部分）' if year in [int(anchor[:4]),int(common_end[:4])] else '')]+[pct(g.set_index(['model','frequency']).loc[(m,q),'net_return']) for m in MODELS for q in FREQUENCIES] for year,g in annual.groupby('year')])
    pr=pairs.loc[pairs.scope.eq('main_common')]
    paired=table(['模型','比较','净 CAGR 差（百分点）','年化日均收益差（百分点）','后者 95% 时间块区间（百分点）'],[[r.model,r.comparison.replace('2w_minus_1w','双周−周').replace('1m_minus_1w','月−周'),pp(r.cagr_difference),pp(r.annualized_mean_daily_return_difference),f'[{pp(r.ci_low)}, {pp(r.ci_high)}]'] for r in pr.itertuples()])
    hair=ordered(allm.loc[allm.scope.eq('main_common')&allm.valuation.eq('suspend_haircut20')&allm.cost.eq('main')&allm.benchmark.eq('CSI300_TOTAL_RETURN')]);base=main.set_index(['model','frequency'])
    hairtable=table(['模型','调仓','停牌平价净年化','停牌折价20%净年化','变化（百分点）'],[[r.model,LABEL[r.frequency],pct(base.loc[(r.model,r.frequency),'cagr']),pct(r.cagr),pp(r.cagr-base.loc[(r.model,r.frequency),'cagr'])] for r in hair.itertuples()])
    available=ordered(allm.loc[allm.scope.eq('native')&allm.valuation.eq('suspend_flat')&allm.cost.eq('main')&allm.benchmark.eq('CSI300_TOTAL_RETURN')]);iv=inv.loc[inv.valuation.eq('suspend_flat')&inv.cost.eq('main')].set_index(['model','frequency'])
    native=table(['模型','调仓','可用终点','交易日数','净年化收益','对全收益指数年化差（百分点）','中止证券'],[[r.model,LABEL[r.frequency],r.end[:10],r.sessions,pct(r.cagr),pp(r.cagr_difference),iv.loc[(r.model,r.frequency),'failure_instruments'] if pd.notna(iv.loc[(r.model,r.frequency),'failure_instruments']) else '无，至数据截止'] for r in available.itertuples()])
    own=ordered(allm.loc[allm.scope.eq('model_common')&allm.valuation.eq('suspend_flat')&allm.cost.eq('main')&allm.benchmark.eq('CSI300_TOTAL_RETURN')]);own_table=table(['模型','调仓','同模型共同终点','净年化收益','对全收益指数年化差（百分点）'],[[r.model,LABEL[r.frequency],r.end[:10],pct(r.cagr),pp(r.cagr_difference)] for r in own.itertuples()])
    morepairs=pairs.loc[pairs.scope.eq('model_common')]
    morepaired=table(['模型','比较','共同终点','净 CAGR 差（百分点）','年化日均差 95% 区间（百分点）'],[[r.model,r.comparison,r.end[:10],pp(r.cagr_difference),f'[{pp(r.ci_low)}, {pp(r.ci_high)}]'] for r in morepairs.itertuples()])
    quoteaudit=inv.groupby(['valuation','complete']).size().reset_index(name='accounts')
    flags=table(['估值口径','是否到数据截止','账户数'],[[r.valuation,str(r.complete),r.accounts] for r in quoteaudit.itertuples()])
    interpretations=[]
    for model in MODELS:
        g=main.loc[main.model.eq(model)].set_index('frequency');best=g.cagr.idxmax()
        change=g.loc['1m','cagr']-g.loc['1w','cagr'];reduction=1-g.loc['1m','annual_one_way_traded_ex_initial']/g.loc['1w','annual_one_way_traded_ex_initial']
        interpretations.append(f'- **{model}**：本轮净年化最高为 {LABEL[best]}。月度比周度提高 {change*100:.2f} 个百分点/年，年化单边换手降低约 {reduction:.1%}。')
    lines=[f'# Q5 等权长仓：1周／2周／1月调仓敏感性完整报告','', '日期：2026-11-16；研究版本：`q5_rebalance_20261116`；历史模拟样本外，真实前瞻 `FORWARD_PENDING`。','', '**主结论：在统一比较区间和主成本下，月度调仓的净年化收益在 E1、E2、E3 三个模型上均最高；双周并不普遍优于周度。降低换手明显改善成本后的实现效果，但不能据此宣称月度对所有未来时期都稳定最优。**','',f'主表共同区间：**{anchor} 信号日收盘—{common_end} 收盘，{period["main_sessions"]} 个交易日**。首笔在 2021-01-11 开盘执行，全部建仓费用计入。共同终点由九个组合的可估值范围机械决定，没有按收益选终点；零／主／压力成本及停牌折价情景也都覆盖该区间。', '',f'同期沪深300全收益指数年化 **{pct(benchmark)}**，沪深300价格指数年化 **{pct(price)}**。主表使用含分红的全收益基准 H00300，避免将股息口径差异全部归入选股超额。','', '## 1. 主结果：九个组合同日期比较','',core,'','年化差为组合 CAGR−指数 CAGR，以百分点/年表示；相对净值年化为 `(组合净值/指数净值)^(252/N)−1`，两者不可混用。单边成交换手为 `0.5×(买入/NAV+卖出/NAV)`，扣除首次建仓后按 252/N 年化；包含现金维度的换手另列于 CSV。正超额不等于正绝对收益。','',*interpretations,'','![净值曲线](net_nav.png)','', '![相对全收益指数净值](relative_nav.png)','', '## 2. 固定规则与实验范围','', '- **只改变调仓日历**：E1 使用原 Ridge；E2/E3 使用原固定三 seed 等权预测。全部沿用 expanding 季度训练、H10 预测与原始封存分数，不为月度另训 H20，不改特征、选股比例、费用或模型种子。','- **1周**：每个原始周信号后，下一市场交易日开盘调仓。','- **2周**：从 2021-01-08 所在周起，按 W-FRI 自然周序号每隔两周选择信号；春节等整周休市不改变后续锚点。这与旧代码按“实际出现的信号行奇偶”抽样不同，旧结果保留，新规则提前冻结。','- **1月**：每个自然月第一个可用周信号后调仓；不是每4周，也不是月末最后一个交易日。该定义能复用同一套周频封存预测，并让三种周期同日开始。','- **Q5 等权**：只在调仓日按当前可评分沪深300成员重新取最高约20%；无分数不填零，同分按证券代码排序。留存股票也向等权目标调整。调仓之间权重自然漂移，不因新周分数、指数调出或买入未成交而临时追单。','- **真实现金和持仓**：不能买入留现金，不能卖出保留实际持仓；不融资、不做空、不虚构清仓，非当前信号成员禁止新买入。qfq 合成单位用于资金账本，原始开盘和涨跌停价用于成交检查。','- **成本**：零成本 0/0 bps；主成本买入10/卖出20 bps；压力成本买入30/卖出80 bps。均按实际成交额扣除，含滑点／冲击代理，不另重复收费。','- **估值**：严格实际报价、已确认全天停牌的旧 qfq 收盘估值（最多20个市场日）、同一停牌估值折价20%。特征和预测不使用填补估值。没有停牌依据、超过20日或换股权益无法估值时中止。主表延续上次净超额测算的停牌估值代理，严格分支完整保留。','- 共 **81 个账户**：3模型×3周期×3成本×3估值。完整数据截止 2026-10-21；可用周预测共296个，双周149个，月度70个。原先各周期结果已见，不将本轮称为新的盲测。', '', '## 3. 成本如何改变排序','',costtable,'','E1 的周度零成本收益高于月度，但较高换手使其主成本净收益落后；E3 也有类似情况。E2 的月度在零成本下已高于周度，扣费后差距进一步扩大。因此改进不全由手续费解释，也包括不同信号采样和持有路径。压力成本下三个月度组合的绝对收益仍为负，不能将“降低交易频率”理解为消除交易成本风险。','', '## 4. 风险、现金与持仓','',risk,'','IR 使用日主动收益均值／样本标准差×√252；TE 使用日主动收益标准差×√252。相对回撤来自组合净值／基准净值曲线，不是组合回撤减指数回撤。','', '![净值回撤](drawdowns.png)','', '## 5. 逐年收益与超额','', '**组合净收益：**','',netyeartable,'','**组合收益率−沪深300全收益指数收益率（百分点）：**','',yeartable,'','2021 从 1月8日信号收盘开始，2025 仅到共同终点；部分年度不能按完整年度比较。全部可用区间的逐年和逐季度表另列，遇到估值中止后的时期标为 BLOCKED，不填零收益。','', '## 6. 配对不确定性：是否稳定优于周度','',paired,'','在同一天对两种调仓账户的日收益作差，以65个交易日为块，进行2,000次循环时间块抽样，固定种子20261116。区间对应“日均收益差×252”，不对应 CAGR 差；两者在上表分列。没有为这6个比较做家族多重检验校正。','', '**本轮共同区间只有 E2 的月度−周度配对区间高于零。E1、E3 的月度点估计改善，但区间包含零；双周相对周度的三个区间也包含零。** 月度首次周信号只是一个固定日历相位，未测试月末或其他周作为月度调仓日，不能排除相位效应。更长周期还使持仓时间超出模型 H10 的预测期限，结果是执行层敏感性，不是模型预测能力变强的证明。','', '## 7. 停牌估值敏感性','',hairtable,'','折价20%不是实际成交价格，只用于标记停牌持仓的估值敏感性；订单仍受真实报价和交易状态限制。两种估值假设都不解决吸收合并、换股对价和退市终值数据缺口。','', '## 8. 更长可用区间与阻断','', '**各账户全部可用范围：不同结束日期不能直接横比。**','',native,'','**同模型三个周期的最长共同区间：可以比较周期，但不要跨不同结束日期比较模型。**','',own_table,'','E2/E3 的三个周期均可延伸至行情截止日；为保留全量信息，额外给出其同模型长区间的配对结果，不替换九组合统一主表。','',morepaired,'','**全部81分支覆盖状态：**','',flags,'','严格报价账户会在顺丰控股等停牌无报价处中止；停牌估值代理可以延长账户，但 E1 周度／双周在海通证券换股终值缺口处结束，E1 月度则在后续 SH601059 缺价处结束。数据缺口不被当作亏损归零，也不因资产表现好坏调整退出日期。','', '## 9. 验证、复现与交付文件','',f'- 账户与来源审计：**{validation["status"]}，{len(validation["checks"])} 项检查**。校验原始输入哈希、所有周期消费同一预测、仅在计划日交易、无非成员买入、阻止未成交订单、现金与费用守恒、净值与持仓一致、等权目标与中止日期。','- 全部测试通过：17 passed（含新增三个日历测试；1 条第三方 OSQP 默认值弃用提醒）。新增日历测试覆盖长假后的双周相位、自然月而非四周、追加未来日期不改变过去计划。周度主成本结果逐一与原有停牌敏感性账户核对一致。','- 原预测、旧账户和已交付报告没有被覆盖。所有新配置、结果、失败与账本分别保存在本轮目录，原始大表与详细持仓账本仍在 Git 忽略的 private 中。','', f'- [主比较表](../../outputs/sensitivity/{DEST.name}/model_frequency_comparison.csv)','- [81分支清单](../../outputs/sensitivity/'+DEST.name+'/account_inventory.csv)','- [所有指标、成本与可用区间](../../outputs/sensitivity/'+DEST.name+'/all_metrics.csv)','- [逐年](../../outputs/sensitivity/'+DEST.name+'/annual_performance.csv) · [逐季度](../../outputs/sensitivity/'+DEST.name+'/quarterly_performance.csv)','- [配对差异](../../outputs/sensitivity/'+DEST.name+'/paired_frequency_differences.csv) · [审计](../../outputs/sensitivity/'+DEST.name+'/validation.json)','', '复现脚本：`src/q5_rebalance_sensitivity.py`（冻结及执行）、`src/q5_rebalance_analyze.py`（指标及审计）、`src/q5_rebalance_report.py`（本报告）。运行配置为 `configs/q5_rebalance_20261116.json`。','', '## 最终裁决','', '**本轮数据支持将月度调仓作为下一轮冻结验证的重点，主要理由是更低换手、较小回撤和更好的主成本净收益。E1/E2 月度在本轮主表表现接近；E2 的月度相对自身周度有较清晰的配对支持。双周并不是普遍改进。**','', '这仍是历史模拟样本外、具有明确估值代理假设的结果，不是严格权益账本或实盘认证；真实前瞻保持 FORWARD_PENDING。本轮未部署策略、未启动监控。']
    content='\n'.join(lines)+'\n';(REPORT/'REPORT.md').write_text(content)
    html=markdown.markdown(content,extensions=['tables','fenced_code'])
    for name in ['net_nav','relative_nav','drawdowns']:
        encoded=base64.b64encode((REPORT/(name+'.png')).read_bytes()).decode()
        html=html.replace('src="'+name+'.png"','src="data:image/png;base64,'+encoded+'"')
    page='<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Q5 调仓周期敏感性报告</title><style>body{max-width:1280px;margin:36px auto;padding:0 24px;font:16px/1.7 system-ui,sans-serif;color:#202a35}h1{font-size:29px}h2{margin-top:38px;border-bottom:1px solid #ccd7df;padding-bottom:8px}table{border-collapse:collapse;display:block;overflow-x:auto;margin:18px 0;font-size:14px}th,td{border:1px solid #dce3e8;padding:8px 12px;white-space:nowrap}th{background:#edf3f8}tr:nth-child(even){background:#f7f9fb}img{width:100%;height:auto}code{background:#eef2f5;padding:2px 5px}a{color:#185f94}strong{color:#173b59}</style><body>'+html+'</body></html>'
    (REPORT/'REPORT.html').write_text(page)
    save_json(DEST/'report_manifest.json',dict(report_path=str(REPORT/'REPORT.md'),report_sha256=sha(REPORT/'REPORT.md'),html_sha256=sha(REPORT/'REPORT.html'),figures={x:sha(REPORT/(x+'.png')) for x in ['net_nav','relative_nav','drawdowns']},source_sha256=sha(EP/'src/q5_rebalance_report.py'),metrics_sha256=sha(DEST/'all_metrics.csv'),validation_sha256=sha(DEST/'validation.json'),primary_period=period))
    print('Reports written:',REPORT)
if __name__=='__main__':main()
