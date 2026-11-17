"""Report fixed REV follow-up and genuine prospective readiness separately."""
import markdown
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from e1_reversal_validation import *
def table(a,percent=()):
 a=a.copy()
 for c in percent:a[c]*=100
 return a.to_markdown(index=False,floatfmt='.4f')
def link(f):return f'../../outputs/diagnostics/{RUN}/{f}'
def report(name,text):
 (R/(name+'.md')).write_text(text)
 (R/(name+'.html')).write_text('<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>E1与固定反转比较</title><style>body{max-width:1120px;margin:36px auto;padding:0 24px;font:16px/1.8 system-ui;color:#223}table{border-collapse:collapse;display:block;overflow:auto}td,th{padding:7px 12px;border:1px solid #ccd}th{background:#edf3f5}img{max-width:100%}a{color:#146887}</style>'+markdown.markdown(text,extensions=['tables','fenced_code'])+'</html>')
def main():
 for n in ['freeze','selection_complete','events_complete','analysis_complete']:verify(n)
 stat=pd.read_csv(D/'event_statistics.csv');main=stat[(stat.cost=='main')&(stat.field=='net_return')];period=pd.read_csv(D/'period_returns.csv');annual=period[period.freq=='Y'];contrib=pd.read_csv(D/'period_contributions.csv');stocks=pd.read_csv(D/'stock_contributions.csv').sort_values('wealth_contribution',ascending=False);curve=pd.read_csv(D/'marked_curve.csv');check=json.loads((D/'validation.json').read_text());forward=json.loads((D/'forward_contract.json').read_text());selection=pd.read_csv(D/'selection_checks.csv');ey=pd.read_csv(D/'event_years.csv')
 # A header-only ledger is intentionally empty, not simulated forward evidence.
 ledger=D/'forward_observations.csv'
 if not ledger.exists():pd.DataFrame(columns=['signal_date','signal_decision_at','generated_at','entry_at','protocol_sha256','input_manifest_sha256','model_sha256','predictions_sha256','targets_sha256','status']).to_csv(ledger,index=False)
 assert pd.read_csv(ledger).empty
 save_json(D/'forward_readiness.json',dict(status='AWAITING_NEW_SIGNAL',new_prospective_observations=0,protocol_sha256=sha(D/'forward_contract.json'),selection_contract_sha256=forward['selection_contract_sha256'],gate=str(EP/'src/e1_reversal_forward_gate.py'),gate_sha256=sha(EP/'src/e1_reversal_forward_gate.py'),ledger_sha256=sha(ledger),gate_scope='metadata checks only; actual hashes, source known_at, phase calendar and trading receipts must be independently checked before acceptance',automation=False,new_model_trained=False,required=forward['pending']))
 fig,axes=plt.subplots(1,2,figsize=(12,4.3))
 axes[0].errorbar(main.horizon,main['mean']*100,yerr=np.vstack([main['mean']-main.ci_low,main.ci_high-main['mean']])*100,fmt='o',capsize=5)
 axes[0].axhline(0,color='gray',ls='--');axes[0].set_xticks([5,10,20],['H5 (aux)','H10 (primary)','H20 (aux)']);axes[0].set_ylabel('O minus REV net event return (pp)');axes[0].set_title('Ordinary 95% intervals; paired samples differ')
 axes[1].bar(annual.period.astype(str),annual.return_difference*100,color=['#27877b' if x>0 else '#b96a65' for x in annual.return_difference]);axes[1].axhline(0,color='gray');axes[1].set_ylabel('Calendar account return difference (pp)');axes[1].set_title('Whole accounts; 2021 and 2025 partial years')
 fig.tight_layout();fig.savefig(R/'horizons_years.png',dpi=170);plt.close(fig)
 fig,ax=plt.subplots(figsize=(9,4));ax.plot(curve.horizon,curve['mean']*100);ax.fill_between(curve.horizon,curve.ci_low*100,curve.ci_high*100,alpha=.2);ax.axhline(0,color='gray',ls='--');ax.set_xlabel('Trading days after next-open entry');ax.set_ylabel('O minus REV marked value difference (pp)');ax.set_title('Entry cost only; not executable exit returns; pointwise 95% intervals');fig.tight_layout();fig.savefig(R/'marked_path.png',dpi=170);plt.close(fig)
 report('REPORT',f'''# E1相对固定短期反转：期限和路径复核

**本轮仍未确认E1相对简单反转具有稳定增量。** H10净事件差约+0.17个百分点，区间跨零；连续账户中E1的领先集中在2021—2022年，2023年之后反转组合表现更好。不能因此宣布二者等价，也不能将之前观察到的同行业内收益差直接称为独立Alpha。

## 固定了什么

完全复用上一轮已封存的原E1和REV名单、行业预算、日期与交易合同，没有重选股票。REV公式保持1日、5日收益分位均值的相反数；候选和支持范围依然依赖原E1，不是独立全市场反转模型。

只抽出两组合中可支持比较的原被排除部分，平均占原资金{selection.budget.mean()*100:.2f}%；其他原持仓保留。每期两边子组合各自归一化为1元，股票数量相同，约{selection.O_count.mean():.2f}只；资本权重重叠平均{selection.overlap.mean()*100:.2f}%。这与上一轮按行业组等权的34.9%重叠口径不同。

## H10主结果与辅助期限

下一交易日开盘入场，分别固定持有5、10、20交易日，尝试完整退出；主成本买10bps、卖20bps。50个计划月度事件，终点成熟不晚于2025-03-03。

{table(main[['horizon','primary','n','mean','ci_low','ci_high','p']],['mean','ci_low','ci_high'])}

收益和区间为每事件pp。H10为45个可执行配对，均值+0.173pp，95%[−0.273,+0.575]，p约0.411，未确认E1优势。5期至少一边不能完整退出，保留缺失。全部50期按期末市值计算、只扣入场成本的H10差约+0.239pp，区间仍跨零；未伪造清算。

H5/H20均为预先列出的辅助项，也没有明确差异。各期限可执行配对不同，H20还少一个未成熟月，因此**不能用三个点的大小直接推出Alpha何时衰减**。本轮未挑最好期限修改策略。

![固定期限与逐年比较](horizons_years.png)

## 全期接近 不代表逐年稳定

原完整账户净CAGR约+4.84%，局部改用REV约+4.56%，来自上一轮已观察结果，本轮只复核路径。它们都保留约68.4%的其他原E1目标资金。

{table(annual[['period','days','O_return','REV_return','return_difference']],['O_return','REV_return','return_difference'])}

前两列收益为%，差为pp。2021从1月11日开始，2025仅截至3月3日。2021、2022年E1领先；2023、2024及2025当前片段落后。分年样本较少，不给每年单独“显著/不显著”的新裁决。

两账户初始100元，最终仅相差约1.304元：2021、2022的链接差分贡献约+3.20、+2.51元，2023、2024和2025约−1.20、−3.02、−0.19元。具体股票正负贡献均保留在[明细](DETAILS.md)，不是仅展示成功案例。

## 事件时间路径能说明什么

![事件市值路径](marked_path.png)

同一批固定单位持仓在第0—20交易日的市值差，仅扣实际入场费用，不假装每天卖出。阴影是逐点普通95%区间，未作整条曲线同时覆盖校正。后段样本成熟度不同，不用于挑最优卖出日或声称等价。

## 前瞻：已冻结口径 尚无新观测

[前瞻合同](FORWARD.md)已登记。本轮历史终点仍为2025-03-03；不把2025—2026已有数据重新命名为未见样本。只接受2026-11-17之后、原月内第一相位、且在下一交易日入场前封存的新信号。

需要保留数据到达时间、原E1模型、预测和目标的哈希及交易限制凭据。当前前瞻登记表为空，**新观测=0，状态AWAITING_NEW_SIGNAL**；没有启动调度、训练新模型、执行交易或发送通知。元数据校验函数不是严格PIT认证。

第一固定确认性复核安排在24个计划月度事件后，不能因途中结果好看提前停止；这不保证统计功效，缺失退出仍须报告。当前无事前等价界限，因此未来也不能仅凭不显著宣布等价。

## 当前研究判断

短期反转仍是解释这部分持仓收益的候选，但历史检验尚不能证明它完整解释E1，也未证明E1在它之外具有稳定增量。更合理的下一步是守住冻结比较、积累真正新信号；继续在同一历史调窗口或权重无法补足独立确认。

[方法](METHOD.md) · [所有成本、月份及股票明细](DETAILS.md) · [前瞻合同](FORWARD.md) · [本轮冻结协议](PROTOCOL.md)。

85项测试、{check['count']}项核验通过；原子组合H10精确复放，原连续账户只读复用，未修改模型、原名单或旧报告。历史探索、Historical-proxy及未认证known_at边界保留；未提交、推送或部署。
''')
 report('DETAILS',f'''# E1−REV完整证据

## 全部成本及期限

{table(stat[['cost','horizon','field','primary','n','mean','ci_low','ci_high','p']],['mean','ci_low','ci_high'])}

net_return为实际能够完整退出的事件净收益；marked_return只扣入场成本，不能当作可执行净收益。主口径仅main/H10/net_return；其他均辅助。不同期限和成本的可交易剩余单位可能影响退出可行性，缺失不填零。

## 每年H10事件表现

{table(ey[ey.horizon==10],['mean','median'])}

单位pp，count为有效配对数。2025只有1个可执行事件，不能据此推断全年或当前市场状态。

## 连续账户逐月收益

{table(period[period.freq=='M'][['period','days','O_return','REV_return','return_difference']],['O_return','REV_return','return_difference'])}

## 链接到终值差的逐年贡献

{table(contrib[contrib.freq=='Y'])}

单位初始100元的终值差贡献，可加总。与各年月收益率差是两种量，不得混用。

## 正负各十项股票贡献

{table(pd.concat([stocks.head(10),stocks.tail(10)]))}

包括两条完整账户中买入、少买、权重漂移、费用和现金的差异；不等于单股持有收益。所有正负股票和逐月贡献见[股票]({link('stock_contributions.csv')})、[期间]({link('period_contributions.csv')})。

[完整事件退出明细]({link('events.csv')}) · [逐事件差值]({link('event_pairs.csv')}) · [固定持仓市值路径]({link('event_paths.csv')}) · [重叠与预算]({link('selection_checks.csv')}) · [原连续账户对比]({link('account_comparison.csv')})。
''')
 report('METHOD',f'''# 固定名单复核方法

## 子组合提取

O和REV完整目标已在上一轮收益计算前封存；BASE_O记录原可支持部分归一化权重，coverage记录其原预算b。令保留部分u=O−b×BASE_O，则本轮REV子组合=(REV−u)/b。必须逐股非负、总预算为b，且两边股票数相同；不根据未来收益重新筛选日期或股票。

该方法允许两边重叠股票；重叠资金不是增量选股。子组合归一化事件收益按月份等权，不等于对原账户按预算加权的收益归因。

## 事件与缺失

沿用原交易引擎、历史成员、开盘交易限制和估值规则。事件在信号后下一开盘买入，固定单位到第h个交易日开盘尝试全卖出，h=5/10/20。若不能完整退出，净收益为缺失；市值仍可能可知，但只作标记价值对照。评价终点不晚于2025-03-03。

H10每月配对差是唯一主端点，循环3月日历块Bootstrap5000、种子20261117，普通95%区间和近似双侧p。未事先定义等价界限，故不做等价或非劣检验。REV因上轮表现接近而被推进，属于历史选择后的验证，不能靠本轮冻结恢复盲测资格。

H5/H20与成本对照为辅助，不选择赢家；曲线逐点区间不是同时置信带。不同期限因缺失与成熟度不同而样本不同。

## 连续账户与归因

原O/REV六条成本账户只读复用、同区间1001日。原主成本交易单重建每日股票损益、费用和现金，精确闭合净值日收益；对各组件使用log(1+r)/r链接。两条账户链接组件相减，再乘终值差/对数终值比，得到可按月份和股票加总的终值差分配。

账户全年收益差是当年各自复合收益相减；与日收益差均值年化、链接贡献均不同。此处不重新按年现金开仓，也不移除不利年份重算策略。

## 前瞻边界

前瞻历史排除日期固定为2026-11-17。模型仍须遵循原E1既定扩展训练配方，每个实际检查点必须有信号前可得凭据；本轮没有训练或部署未来模型。缺失数据或检查点凭据时不能注册合格信号。

元数据入口src/e1_reversal_forward_gate.py在基本时序检查上增加信号日与北京时间决策日期一致、晚于登记、入场必须后于信号日等校验，防止给旧决策换一个未来日期。该入口仍无法单靠自报字段证明known_at或真实收盘日历，须另外核实原始来源、内容哈希及交易日历。

[冻结输入与代码]({link('freeze.json')}) · [名单封存]({link('selection_complete.json')}) · [事件封存]({link('events_complete.json')}) · [分析封存]({link('analysis_complete.json')}) · [核验]({link('validation.json')})。
''')
 report('FORWARD',f'''# E1−固定REV前瞻登记

**当前仅完成合同与校验准备，没有新增前瞻信号。** 新观测数0，未启动自动运行。空登记表不是模拟样本，也不使用已有2025—2026收益填充。

- 登记时间：{forward['at']}。
- 排除所有信号日不晚于2026-11-17的记录。
- 使用原每月第一个完整周信号，实际交易日由届时交易日历核实，不在此猜测日期。
- REV公式、支持范围、行业预算和持仓数沿用已冻结合同；规则变更必须建立独立新版本，不能混入本确认序列。
- E1沿用原配方，实际检查点须在信号决策前存在并封存；未来未具备模型凭据时暂停登记该条记录，不用未来训练结果回填。
- 原始来源的known_at、数据清单、模型、预测、目标哈希必须在下一交易日入场前封存。元数据声明须能对应真实内容；不能靠声明替代证据。
- 主比较为当期可支持的原E1与REV归一化子组合H10成本后收益差，主费用10/20bps；不可退出、缺数据、不可评分均保留原因。
- 所有计划月度事件持续记录，不以收益选择记录或停止时点。首次固定确认性复核在24个计划月度事件后；少于6个可执行配对时统计推断不足，24期本身也不保证功效。
- 当前没有事前等价界限；差异不显著不能说两者等价。
- 不启动真实订单、自动调度、模型重训、邮件或其他通知。

[机器可读合同]({link('forward_contract.json')}) · [准备状态]({link('forward_readiness.json')}) · [当前空登记表]({link('forward_observations.csv')})。

严格入口为src/e1_reversal_forward_gate.py的validate_metadata，协议哈希参数应使用forward_contract.json的SHA256。它拒绝历史信号、事后封存、信号日与决策时间不一致、未声明未来收益未见、协议变化等记录；实际日历、来源及文件哈希仍必须另行核验。测试中的日期只是合成用例，不是未来交易日承诺或真实信号。
''')
 save_json(R/'manifest.json',dict(files=record(sorted(R.glob('*.md'))+sorted(R.glob('*.html'))+sorted(R.glob('*.png'))+[D/'forward_readiness.json',D/'forward_observations.csv']),sources=record([Path(__file__),EP/'src/e1_reversal_validation.py',EP/'src/e1_reversal_forward_gate.py',EP/'tests/test_e1_reversal_validation.py']),tests=85,checks=check['count'],visual_review='PENDING',new_prospective_observations=0,forward='FORWARD_PENDING'))
 print('reports ready',flush=True)
if __name__=='__main__':main()
