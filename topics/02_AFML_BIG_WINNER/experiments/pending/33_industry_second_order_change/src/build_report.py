"""Build evidence-linked EP33 report and retrospective candidate cards."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from price_experiment import EP,SOURCE,KEY,features,digest


def table(f):
    f=f.copy()
    for col in f:
        if pd.api.types.is_integer_dtype(f[col]):f[col]=f[col].map(str)
        elif pd.api.types.is_float_dtype(f[col]):f[col]=f[col].map(lambda v: 'NA' if pd.isna(v) else f'{v:.4f}')
    return f.to_markdown(index=False,disable_numparse=True)


def main():
    out=EP/'outputs/final';out.mkdir(parents=True,exist_ok=True)
    reports=EP/'reports';reports.mkdir(exist_ok=True)
    panel=pd.read_parquet('/tmp/ep33_r01_panel.parquet')
    market=pd.read_parquet(SOURCE/'CSI_ALL.parquet').close
    selected=pd.read_csv(EP/'outputs/r03/selected.csv.gz',parse_dates=['date'],low_memory=False)
    for f in [panel,selected]:
        f['outcome_status']=np.where(f.excess126.notna(),'KNOWN',np.where(f.day_i+127>=len(market),'CENSORED','PATH_OR_CLASSIFICATION_GAP'))
    status=selected.groupby(['pool','strategy','outcome_status']).size().rename('rows').reset_index()
    status.to_csv(out/'outcome_status.csv',index=False)
    catalog_path=EP.parent/'32_industry_rotation_cycle_observation/extensions/v4_all_industry_review/outputs/industry_coverage.csv'
    catalog=pd.read_csv(catalog_path);catalog=catalog[catalog.level.eq('L3')].copy()
    eligible=panel[panel.acceleration.notna()&panel.coverage.ge(.8)&panel.members.ge(5)]
    counts=eligible.groupby(['era','industry_code']).size().rename('ep33_eligible_weeks').reset_index()
    catalog=catalog.merge(counts,on=['era','industry_code'],how='left');catalog.ep33_eligible_weeks=catalog.ep33_eligible_weeks.fillna(0).astype(int)
    catalog['ep33_status']=np.where(catalog.ep33_eligible_weeks>0,'OBSERVED','NO_ELIGIBLE_WEEK_IN_2021_ONWARD')
    catalog.to_csv(out/'industry_inventory.csv',index=False)
    policy=selected[(selected.pool=='accelerating_improvement')&(selected.strategy=='joint_velocity')].copy()
    # Workload spells, not independently investable cycles.
    spells=[]
    for (era,code),g in policy.groupby(['era','industry_code']):
        g=g.sort_values('date')
        spell=g.day_i.diff().gt(21)|g.day_i.diff().isna()
        spells.append(dict(era=era,industry_code=code,alerts=len(g),workload_spells=int(spell.sum())))
    pd.DataFrame(spells).to_csv(out/'workload_spells.csv',index=False)
    latest=policy[policy.date.eq(policy.date.max())].sort_values('rank').copy()
    raw=pd.read_parquet(SOURCE/'daily_industries.parquet')
    ages=[]
    for _,g in raw[raw.level.eq('L3')].groupby(KEY):
        f=features(g,market)
        state=f.velocity.ge(0)&f.acceleration.gt(0)&f.persistence.ge(.8)&f.breadth_change.gt(0)&f.breadth_acceleration.gt(0)&f.coverage.ge(.8)&f.members.ge(5)
        f['joint_state_age_sessions']=state.groupby((~state).cumsum()).cumsum().astype(int)
        f['industry_return21']=f.nav/f.nav.shift(21)-1
        f['industry_return63']=f.nav/f.nav.shift(63)-1
        ages.append(f.loc[f.date.eq(policy.date.max()),['era','industry_code','date','joint_state_age_sessions','industry_return21','industry_return63']])
    latest=latest.merge(pd.concat(ages),on=['era','industry_code','date'],how='left',validate='one_to_one')
    finance=pd.read_csv(EP/'outputs/r04/industry_coverage.csv.gz',parse_dates=['date'])
    parents=pd.read_parquet('/home/xiaolv/.cache/a_share/ep32/industry_v1/L3.parquet')[['index_code','parent_code']].rename(columns={'index_code':'industry_code'})
    latest=latest.merge(parents,on='industry_code',how='left',validate='one_to_one')
    latest=latest.merge(finance,on=['era','industry_code','date'],how='left',validate='one_to_one')
    # Highest past-63-return correlations are overlap evidence, not causal industry clusters.
    nav=raw[raw.level.eq('L3')&raw.era.eq('SW2021')&raw.date.le(policy.date.max())].pivot(index='date',columns='industry_code',values='nav')
    returns=nav.pct_change(fill_method=None).tail(63)
    codes=latest.industry_code.tolist();corr=returns.reindex(columns=codes).corr(min_periods=42)
    corr.to_csv(out/'latest_candidate_correlations.csv')
    cards=[]
    for _,r in latest.iterrows():
        peers=corr[r.industry_code].drop(r.industry_code).dropna().sort_values(ascending=False)
        peer=peers.index[0] if len(peers) else None
        cards.append(dict(date=str(r.date.date()),rank=int(r['rank']),industry_code=r.industry_code,industry_name=r.industry_name,
            parent_industry_code=str(r.parent_code),quality='Historical-proxy',candidate_type='改善加速且持续扩散',velocity=float(r.velocity),acceleration=float(r.acceleration),
            persistence=float(r.persistence),breadth_change=float(r.breadth_change),breadth_acceleration=float(r.breadth_acceleration),
            joint_state_age_sessions=int(r.joint_state_age_sessions),industry_return21=float(r.industry_return21),industry_return63=float(r.industry_return63),
            price_coverage=float(r.coverage),finance_coverage=None if pd.isna(r.finance_coverage) else float(r.finance_coverage),
            finance_acceleration=None if pd.isna(r.finance_acceleration) else float(r.finance_acceleration),
            related_candidate=peer,related_correlation=None if peer is None else float(peers.iloc[0]),
            hypothesis='价格改善开始持续并向同业扩散；经营驱动尚未确认。',
            competing_explanation='共同市场风格反弹、短期资金轮动或先前下跌后的恢复。',
            next_research='核实改善是否来自可持续的收入、利润或供需变化，以及当前价格已反映多少；本轮未新增这些信息。',
            invalidation='后续相对变化转负、近10日正加速度少于8日、或扩散条件消失时降为待复核；这是状态失效，不是止损承诺。',
            outcome_status=r.outcome_status))
    (out/'candidate_cards.json').write_text(json.dumps(cards,ensure_ascii=False,indent=2)+'\n')
    # Retrospective examples chosen for diagnosis, never used to select current candidates.
    failures=policy[policy.excess126.lt(0)].sort_values('excess126').drop_duplicates(['era','industry_code']).head(5)
    failures[['date','industry_code','industry_name','excess126','return126','adverse126']].to_csv(out/'failure_examples.csv',index=False)
    r03=pd.read_csv(EP/'outputs/r03/summary.csv')
    annual=pd.read_csv(EP/'outputs/r03/annual.csv')
    ann=annual[(annual.pool=='accelerating_improvement')&(annual.treatment=='joint_velocity')&(annual.control=='velocity')]
    r05=pd.read_csv(EP/'outputs/r05/summary.csv')
    global_result=json.loads((out/'global_summary.json').read_text())
    global_annual=pd.read_csv(out/'global_annual.csv')
    dp=pd.read_csv(EP/'outputs/r05/date_pairs.csv',parse_dates=['date'])
    fa=dp[dp.complete].groupby(['pool',dp.date.dt.year]).agg(dates=('delta','size'),delta=('delta','mean')).reset_index().rename(columns={'date':'year'})
    fa.to_csv(out/'financial_annual.csv',index=False)
    r04cov=pd.read_csv(EP/'outputs/r04/coverage.csv')
    summary=r03[(r03.pool=='accelerating_improvement')&r03.treatment.isin(['acceleration','residual','joint_velocity'])&r03.control.eq('velocity')][['treatment','complete_dates','delta_complete','ci12_low','ci12_high']]
    text=f'''# EP33 阶段研究报告：行业二阶变化与配置研究候选

日期：2026-11-11（Asia/Shanghai）。状态：本次探索循环已完成；结论为历史代理探索，独立验证 FORWARD_PENDING。数据终点 {market.index.max().date()}，最新完整周 {policy.date.max().date()}。**不是2026-11-11实时推荐，也不是当时已发布的前瞻信号。**

## 1. 目的、方法与认识变化

目的保持为：优先发现行业变化起点，帮助配置研究分配注意力。用户明确接受非严格PIT及部分缺失后，允许现有代理数据进入探索，仍遵守向后看特征、未来标签隔离及缺失留空。

研究实际经历 R00 数据审计 → R01 二阶幅度排序 → R02 持续与扩散过滤 → R03 控制动量/风险及状态排序 → R04 部分财务代理 → R05 固定财务增量组合。每轮计划、结果和反思分别见 rounds/；本报告没有把探索中看过的数据再命名为独立验证。

认识从“加速度越大可能越值得关注”修正为：**改善加速的持续性和扩散状态可能有筛选价值，但二阶幅度本身未证明稳定排序优势；恶化减速是另一类问题，当前方法效果偏弱。** 财务代理在更广可用池有补充线索，但加到已筛出的价格状态里没有显示进一步增量。

## 2. 主要结果

126交易日为本轮主端点，信号后下一交易日收盘至随后126交易日收盘的行业价格收益减中证全指收益。不是行业基金可成交组合、含息净收益或年化收益。固定规则无需训练，因此没有声称完成模型训练或成熟标签学习；未来结果只用于评价。

R03 改善加速组，同池、同日期、相同名额下相对动量排序的差值如下，数值单位为收益比例，0.01=1个百分点。区间为12个月时间块重采样的探索性95%区间，未调整整个自适应研究的选择偏差。

{table(summary)}

联合状态为：21日相对动量>=0，加速度>0，近10日至少8日加速度为正，21日上涨宽度变化>0且宽度变化再次加速。该状态内按动量排序相对同类型未过滤动量，平均改善约2.17个百分点；在联合状态内加速度排序相对动量约-0.24个百分点，区间跨零。

恶化减速组，R03原始加速度和残差排序相对动量分别约-1.58和-1.27个百分点；联合状态+动量约-2.35个百分点且区间跨零。不能用改善加速分支的结果替代该分支失败。

联合状态+动量的完整配对日期年度差值：

{table(ann[['year','dates','delta']])}

所有年度为正是探索性一致线索；2021/2026样本少且存在分类断点/期限未成熟，不代表每年都获得独立统计确认。

R04 收入加速度单独排序相对动量的区间跨零。R05 固定等权百分位组合结果：

{table(r05)}

财务年度切片见 outputs/final/financial_annual.csv：全财务池组合在2022年为负，2021/2026样本少但效果较大，稳定性弱于价格状态线索。两种线索的池和覆盖不同，不能直接比较上述收益差大小选冠军，也不能叠加为组合收益。

完成审计另补全池基线：A方案相对全部63日合格行业直接按动量排序，在相同名额和双方结果完整的{global_result['complete_dates']}个日期中，月等权差为{global_result['delta']*100:.2f}个百分点，12个月块区间[{global_result['ci_low']*100:.2f},{global_result['ci_high']*100:.2f}]。这是完整候选政策比较，不能单独归因于二阶特征。该比较在方案已选定之后补齐，仍是探索性评价。

{table(global_annual)}

缺失敏感性：对已到期但路径缺失的结果，分别假设未知超额为±50个百分点的双向压力情景，差值可从{global_result['stress_low']*100:.2f}到{global_result['stress_high']*100:.2f}个百分点。这不是概率区间或真实上下界；它说明现有数据不能排除缺失路径导致结论变化。未成熟日期不参与该压力计算。

## 3. 数据覆盖、未知结果与重复提醒

价格来自EP32固定前月成员、月内漂移的行业篮子，SW2014/SW2021分开，缺口切断连续路径；至少5成员和80%可比价格端点为继承的构造规则。这个门槛允许部分缺失，但不是严格PIT认证。全三级目录逐行业清单见 outputs/final/industry_inventory.csv，包括无合格观察的行业，不以已成功行业作母体。

财务使用1647个现有供应商分区，按公告日、更新日及所有派生依赖日期的最大值后一个交易日可见。季度收入由累计收入差分，再同比并对同比作季度差分；至少3家、30%成员覆盖，过旧数据不使用。周均财务可用行业{r04cov.finance_eligible.mean():.2f}个，价格合格行业{r04cov.price_eligible.mean():.2f}个。该缓存并非全市场随机样本；完整版本链和原始披露数值未认证。

结果未知拆分为未成熟 CENSORED 与在总日历已到期但路径/分类中断 PATH_OR_CLASSIFICATION_GAP，详见 outputs/final/outcome_status.csv。A方案2369条提醒中，1853条已知、232条未成熟、284条存在路径或分类缺口；后两类不能混称尚未到期。主比较要求双方已选行业全部有完整期限；未按未来可见性重新选行业，但对完整日期的筛选仍可能带来偏差。各自已知样本诊断、未知率与完整日期结果并列保存在R03表中，不将未知填零。

联合状态动量方案共有{len(policy)}条行业周提醒，按同一行业间隔超过21交易日划分为{sum(x['workload_spells'] for x in spells)}个工作量片段。片段用于估计重复研究负担，不是独立周期或交易；行业间也有共同暴露。K=10为实验设定，池不足则少选，空池不发信号。R03残差对照至少20行业的适用限制另列coverage.csv。

## 4. 早期性、反例与研究卡

当前找到的是可观察的持续扩散状态，**尚未证明比真实基本面拐点更早，也没有完成因果机制识别**。为了避免“早期”被空泛使用，候选卡列出状态持续交易日及过去21/63日涨幅；后续应检验介入时剩余空间，而不能只靠事后周期低点定义成功。

以下为事后最差样例中的不同业代表，仅用于反思，不作为训练或筛选输入：

{table(failures[['date','industry_name','excess126','return126','adverse126']])}

同一条件也会出现明显失败；状态过滤不是收益保证。卡片的失效条件描述研究状态失效，不等于已验证止损规则。

最新历史快照与完整卡片见 [candidate_cards.md](candidate_cards.md)、outputs/final/candidate_cards.json。每张包含观察、竞争解释、待核实问题、失效条件、价格与财务覆盖及相关行业。没有把价格扩散解释为已确认订单/利润改善。

## 5. 验证与局限

- R01：20个连续块的截断未来和未来价格扰动检查，30个独立下一交易日/126日端点复核，成员时点与唯一身份检查。
- 测试覆盖财务未来修订的依赖可见日、缺公告日期、标签不能跨连续块，以及候选选择对未来结果不敏感。测试结果见 validation.json；这些不认证供应商PIT或策略盈利。
- 所有输入与计划/代码哈希随轮次收据保存。原数据与EP32结论未修改；不采集新数据，不部署，不提交Git。
- R01/R02六个月块区间可能不足以描述252日辅助结果的依赖；主结论使用R03/R05的126日端点及12个月块区间，不以辅助期限显著性定胜负。
- EP32冻结方案是早期资格过滤且选全部达标行业，EP33是固定研究名额的状态筛选。本轮不将EP32的24.65%分类精度与本实验收益差比较，也没有声称胜过EP32同口径策略；直接对照留待统一研究名额和资格合同后检验。
- 未训练复杂模型；没有完整策略仓位、费用、交易执行或实际持仓约束。研究候选评价不能证明最终配置决策改善。

## 6. 逐假说裁决与下一步

| 假说 | 本次裁决 |
|---|---|
| H1 恶化减速有筛选价值 | 当前21日加速度及过滤方案不支持升级；不等于否定所有基本面拐点方法 |
| H2 改善加速有增量 | 幅度排序INCONCLUSIVE；持续状态过滤有探索性线索 |
| H3 扩散确认 | 联合持续性有历史代理支持线索，未独立确认其机制或单独因果贡献 |
| H4 基本面补充 | 广覆盖可用子池的固定组合有线索；联合价格状态内增量INCONCLUSIVE，覆盖与修订偏差仍在 |

本次冻结两条分开待验证的研究候选方案，不再继续搜索窗口/阈值：A=持续改善扩散状态+动量排序；B=财务可用池内动量与收入加速度等权。A作为本轮主要候选卡示例，B作为单独补充研究线索，不自动合并。

后续真正需要解决的是独立时段、不同覆盖及实际研究预算下是否保留这些增量，以及候选是否足够早。现有历史已被查看，本次没有可声称独立的未来结果；状态FORWARD_PENDING。这个结论完成的是本次有留痕的探索，不是证明配置方法已经成功。
'''
    text = '> **目标纠正（2026-11-11）：** 本文记录R00–R05收益筛选旁支，未完成“研究变化如何开始”的原目标。原完成声明已撤回；当前目标以 [GOAL](../GOAL.md) 为准。以下数值保留为旁支证据，不能证明起点识别能力。\n\n' + text
    (reports/'stage_report.md').write_text(text)
    cardtext=f'# EP33 历史研究候选卡\n\n观察日 {policy.date.max().date()}，数据终点 {market.index.max().date()}。2026-11-11事后生成，非实时或当时已发布信号。候选只是进入研究pipeline的起点。\n\n'
    for c in cards:
        cardtext+=f'''## {c['rank']}. {c['industry_name']}（{c['industry_code']}）

- 观察：21日对数相对变化 {c['velocity']:.4f}；加速度 {c['acceleration']:.4f}；近10日正加速度比例 {c['persistence']:.0%}；宽度变化 {c['breadth_change']:.4f}，宽度加速度 {c['breadth_acceleration']:.4f}。
- 时机：联合状态已持续 {c['joint_state_age_sessions']} 个交易日；行业过去21/63日价格变化 {c['industry_return21']:.2%} / {c['industry_return63']:.2%}。不能把已涨很多的行业自动称为低位起点。
- 数据：价格覆盖 {c['price_coverage']:.0%}；财务覆盖 {c['finance_coverage']}；收入同比增速变化 {c['finance_acceleration']}。全部标Historical-proxy，缺失不是零。
- 假设：{c['hypothesis']}
- 竞争解释：{c['competing_explanation']}
- 待验证：{c['next_research']}
- 失效条件：{c['invalidation']}
- 层级关联：二级父行业代码 {c['parent_industry_code']}；父子层级不合计为独立机会。
- 同组关联：过去63日与 {c['related_candidate']} 的日收益相关系数 {c['related_correlation']}；不将两个行业当作独立机会。完整相关矩阵另存。
- 未来126日结果：{c['outcome_status']}；不填造结果或胜率。

'''
    (reports/'candidate_cards.md').write_text(cardtext)
    print('report and cards written',len(cards))

if __name__=='__main__':main()
