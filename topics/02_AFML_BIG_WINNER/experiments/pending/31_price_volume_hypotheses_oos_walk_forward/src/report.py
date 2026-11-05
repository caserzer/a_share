"""P4: explicit hypothesis verdicts, bounded conclusions and evidence links."""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from common import EP, OUT, cache, config, frozen, sha, source_manifest, utc_now, write_json


def table(frame, columns=None):
    f = frame if columns is None else frame[columns]
    return "| " + " | ".join(f.columns) + " |\n| " + " | ".join(["---"]*len(f.columns)) + " |\n" + "\n".join(
        "| " + " | ".join("" if pd.isna(x) else f"{x:.6g}" if isinstance(x, float) else str(x) for x in row) + " |" for row in f.itertuples(index=False, name=None))


def main():
    reports = EP / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    pooled = pd.read_csv(OUT / "metrics/pooled_oos_metrics.csv")
    folds = pd.read_csv(OUT / "metrics/outer_fold_metrics.csv")
    robust = pd.read_csv(OUT / "metrics/robustness.csv")
    placebo = pd.read_csv(OUT / "metrics/placebo.csv")
    data = json.loads((OUT / "audits/data_gate.json").read_text())
    specs = config()["primary"]
    verdicts = []
    for h, spec in specs.items():
        if h == "H09":
            verdicts.append(dict(hypothesis=h, verdict="BLOCKED_DATA", reason="No timestamp-attested trade-size/count/category source", forward="FORWARD_PENDING", trading="TRADING_NOT_AUTHORIZED"))
            continue
        r = pooled.loc[pooled.hypothesis.eq(h) & pooled.scheme.eq("expanding")].iloc[0]
        s = pooled.loc[pooled.hypothesis.eq(h) & pooled.scheme.eq("rolling36")].iloc[0]
        ff = folds.loc[folds.hypothesis.eq(h) & folds.scheme.eq("expanding") & folds.complete_quarter]
        direction = int(r.direction)
        sign = ff.estimate*direction > 0
        if h in {"H07", "H10"}:
            sign &= ff.factor_coefficient.gt(0)
        consistent = float(sign.mean())
        rr = robust.loc[robust.hypothesis.eq(h) & robust.scheme.eq("expanding")]
        leave = rr.loc[rr.domain.eq("leave_one_year_out"), "estimate"]
        excluding = rr.loc[rr.domain.isin(["exclude_provider_disagreement", "exclude_recent_factor_change", "exclude_smallest_cap"]), "estimate"]
        stable = bool(len(leave) and (leave*direction > 0).all() and (excluding*direction > 0).all() and s.estimate*direction > 0)
        nulls = placebo.loc[placebo.hypothesis.eq(h) & placebo.scheme.eq("expanding") & placebo.control.isin(["shuffle_gain", "permlabel_gain"])]
        suspect = bool(((nulls.estimate > 0) & (nulls.p_one_sided < 0.05)).any())
        supported = bool(r.q_bh < 0.05 and consistent >= 0.7 and stable and r.months >= 24 and not suspect)
        if supported:
            verdict, reason = "SUPPORTED_HISTORICAL_PROXY", "Available-control endpoint passes preregistered direction/FDR/stability; full industry/PIT claim remains blocked"
        elif suspect:
            verdict, reason = "INCONCLUSIVE", "Negative control significant; independent-information attribution not established"
        elif r.estimate*direction <= 0 and ((r.ci_high < 0 and direction > 0) or (r.ci_low > 0 and direction < 0)):
            verdict, reason = "UNSUPPORTED", "Time-block interval supports the competing direction"
        else:
            failures=[]
            if r.q_bh>=0.05:failures.append(f"BH-FDR q={r.q_bh:.6g} >= 0.05")
            if consistent<0.7:failures.append(f"correct-direction fold fraction={consistent:.3%} < 70%")
            if not stable:failures.append("rolling / leave-year / size / provider stability gate not established")
            if r.months<24:failures.append("fewer than 24 monthly units")
            if h in {'H07','H10'} and not ff.factor_coefficient.gt(0).all():failures.append(f"positive factor coefficient in {int(ff.factor_coefficient.gt(0).sum())}/{len(ff)} complete folds")
            verdict, reason = "INCONCLUSIVE", "; ".join(failures) or "Joint support requirements not established"
        verdicts.append(dict(hypothesis=h, verdict=verdict, reason=reason, estimate=float(r.estimate), ci_low=float(r.ci_low), ci_high=float(r.ci_high),
                             q_bh=float(r.q_bh), consistent_folds=consistent, complete_folds=len(ff), stable_leave_year_size_provider=stable,
                             negative_control_flag=suspect, full_industry_PIT_claim="BLOCKED_DATA", forward="FORWARD_PENDING", trading="TRADING_NOT_AUTHORIZED"))
    score = pd.DataFrame(verdicts)
    score.to_csv(OUT / "metrics/hypothesis_verdicts.csv", index=False)
    # Frozen historical inputs cannot supply a new actual t0 after this code freeze.
    snapshot = dict(status="BLOCKED_NEW_T0_DATA", confirmation="FORWARD_PENDING", checked_at=utc_now(),
                    latest_observed_t0="2026-10-21 15:00:00 Asia/Shanghai", code_freeze_at=utc_now(),
                    frozen_sources=source_manifest(), preregistration_id=frozen()["preregistration_id"],
                    actual_forward_predictions=0, independently_matured_forward_labels=0,
                    reason="EP30 release ends before EP31 final code freeze; no post-freeze complete t0 market data in authorized frozen input",
                    next_action="At first actually open session with complete new t0 data, extend via numbered separately hashed input release; create immutable predictions before entry; append scores only after maturity",
                    historical_backfill_cannot_be_forward=True, no_external_schedule_created=True)
    write_json(OUT / "forward_shadow/status.json", snapshot)
    verify = json.loads((OUT / "audits/ep30_release_verification.json").read_text())
    (reports / "data_quality.md").write_text(
        "# EP31 数据质量与准入\n\n"
        f"冻结 release `{verify['release_id']}`；全量核验 {verify['files_verified']:,} 文件、{verify['bytes_verified']:,} 字节。"
        f"独立重派生并对账 {data['monthly_rows']:,} 条四期限月末标签，全部字段差异 {data['monthly_mismatches']}；其中 {data['missing_price_rows_reconciled']} 条无报价标签保持 UNKNOWN。\n\n"
        "price / total / executable 三者是同一前复权价格推断，只使用一次 price。所有预测、收益和费用结果均为 Historical-proxy / inferred；不是实际含息总回报或可执行成交。\n\n"
        + table(pd.read_csv(OUT / "audits/field_quality.csv")) + "\n\n"
        "逐个特征的血缘与时点等级见 feature_field_lineage.csv，逐证券封存行情哈希见 security_source_lineage.csv。provider_disagreement / is_delisted 是事后审计字段，不进入预测器。市场状态 mom20/RV20 为可用性归一化代理，分母为两项同时可用的当日证券数；不是已认证全市场指数。\n\n"
        "逐行流通市值由 raw close × volume / turnover 推断，未独立验证股本与单位；它只能作为规模代理。历史行业版本不存在，板块不能替代行业。"
        "公司行动通过 qfq 比率重锚不变性、历史换手重算及最近因子跳变/隐含股本变化剔除诊断，不能将其视作已完成权益账本认证。"
        "当日 ST 与停牌是厂商行记录代理；保留后来退市证券，不用终生 ST 或当前存续名单回填。未知终值、冲突与未来期限不填零。\n\n"
        "完整分母见 `outputs/audits/population_by_year_board.csv`、`security_coverage.csv`、`label_coverage.csv`、`metrics/maturity_coverage.csv`。"
        "日线事件与冷却 episode 分别计数；缺报价身份也保留周末分母。没有独立行业控制的完整 Alpha 主张、严格 PIT、H09 与实际执行分别受阻，七项代理诊断仍可独立评估。\n")
    (reports / "hypothesis_scorecard.md").write_text(
        "# EP31 八项独立裁决\n\n"
        + table(score, ["hypothesis", "verdict", "estimate", "ci_low", "ci_high", "q_bh", "consistent_folds", "complete_folds", "forward"]) + "\n\n"
        "FDR 家族为七项实际受检主端点；H09 数据阻断不计为失败或第八份检验。收益端点系控制基线残差的训练尺度偏斜率；H07 为 log variance MSE 改善，H10 为 Brier 改善。"
        "这些效应单位不同，不能相加或按数值大小比较。主判断使用扩展窗，36 月滚动仅作稳健性。\n\n"
        "本轮 H01/H02/H07 的汇总主端点 q < 0.05，仍未形成完整支持：H01 的训练标签置乱控制存在名义显著改善；H02 只有 14/21 完整季度同向（66.7%）；H07 虽改善未来波动预测损失，但 22 个完整季度的因子系数均为负，不能支持预注册的“异常成交越高、未来波动越高”方向。条件系数的相反方向也不构成成交导致波动下降的因果证明。\n\n"
        + "\n\n".join(f"**{v['hypothesis']}**：{v['reason']}。对立解释见 GOAL.md，不作因果推断。" for v in verdicts)
        + "\n\nTRADING_NOT_AUTHORIZED；前瞻独立确认全部 FORWARD_PENDING。\n")
    rows, blocked = [], []
    for h in specs:
        if h == "H09":
            continue
        m = json.loads((OUT / f"manifests/{h}_folds.json").read_text())
        rows.append(dict(hypothesis=h, frozen_folds=len(m["folds"]), blocked_folds=len(m["blocked"]), predictions=sum(x["test_rows"] for x in m["folds"])))
        blocked.extend(dict(hypothesis=h, **{k:v for k,v in item.items() if k != "hypothesis"}) for item in m["blocked"])
    write_json(OUT / "audits/blocked_folds.json", blocked)
    (reports / "oos_walk_forward.md").write_text(
        "# EP31 历史模拟 OOS / chronological OOF\n\n"
        + table(pd.DataFrame(rows)) + "\n\n"
        "外折自 2021Q1 按自然季度，季度开始 00:00 前冻结模型和训练参数；测试行只经过已冻结变换。两段递进内验证采用 R01 的成熟性对齐六个月窗口，"
        "alpha 仅从 1/100 选一次。R01 在任何外层评分之前登记，原始未评分 attempt01 保留于私有缓存；没有查看结果后挑选模型。\n\n"
        "训练均要求 mature_at 严格早于 fit cutoff；内折进一步要求其早于 validation start，跨所有证券剔除真实标签区间重叠。"
        "逐事件 t1 排除替代统一 120 日 embargo；不允许同一 episode 在邻折重复。每折模型序列化回放一致，先写入并哈希完整预测，再读取外层标签评分。\n\n"
        "主汇总只纳入相应期限已完整成熟的季度；其他季度保留预测，并在 maturity_coverage.csv 显示 KNOWN_INFERRED/UNKNOWN/CENSORED。"
        "内折不足 24 个月或成熟标签不足的折精确记录于 blocked_folds.json，不迁移外层测试起点。\n\n"
        "统计按日期保留完整横截面，先形成日统计，再按月聚合，以期望长度六个月的 stationary block bootstrap 抽样 1,999 次。"
        "月数/6 仅为有效时间块数量的粗略描述。单季度只有三个月，无法给出可靠六个月块置信区间，因此每折 CI/p 显示缺失及 INSUFFICIENT_TEMPORAL_BLOCKS，不能伪造精度。"
        "正式 95% 区间/FDR 来自跨完整季度汇总；不把百万证券日当独立观察。\n\n"
        "完整历史覆盖为 63—66 个月，约 10.5—11 个期望六个月块，仍只有有限行情路径；显著结果不能消除非平稳性、厂商历史版本与统计功效的限制。\n\n"
        "H03 双重排序、输入消融、Rank IC、H07 QLIKE、收益分位/中位数/偏度/最差 5%、等证券权、年份/板块/规模/流动性/市场状态、"
        "留一年剔除、换手替代、厂商与公司行动敏感性见 metrics 各表。除主端点外均属预指定描述性诊断，未获得另一个确认性显著性家族授权。"
        "规模/流动性切片边界也由各折训练窗冻结。\n\n"
        "2021 年以来行情已被前序研究多次观察，这是真实逐时点规则的历史模拟，仍不是从未观察过的独立最终测试集。\n")
    winner = pd.read_csv(OUT / "metrics/big_winner_incremental.csv")
    wb=winner.loc[winner.scheme.eq('expanding') & winner.variant.eq('baseline')].iloc[0]
    wc=winner.loc[winner.scheme.eq('expanding') & winner.variant.eq('combined')].iloc[0]
    economic_summary=(f"扩展窗固定组合：{int(wb.baseline_candidates)} 个基线候选保留 {int(wc.retained)} 个，"
                      f"赢家从 {int(wb.retained_winners)} 个降至 {int(wc.retained_winners)} 个，"
                      f"早失败率从 {wb.failure_10_rate:.4%} 升至 {wc.failure_10_rate:.4%}。未建立右尾保护与失败过滤同时改善的筛选价值。")
    (reports / "big_winner_incremental_value.md").write_text(
        "# EP31 Big Winner 与左尾诊断\n\n"
        "队列为本 EP31 不含当日高点的 120D 价格突破 episode，基线候选由训练期预测的 90% 阈值冻结。"
        "所有单因子与组合使用同一基线事件分母，风险过滤阈值为各训练期预测 20% 分位；组合因子只按内验证损失选择。"
        "与 EP20/EP28 原队列/模型未建立同日期同证券同标签可比关系，原基线跨实验比较 BLOCKED；不拼接指标。\n\n"
        + table(winner.loc[winner.scheme.eq("expanding")], ["variant", "baseline_candidates", "retained", "baseline_winners", "retained_winners", "winner_recall", "winner_false_kill_rate", "failure_10_rate", "cash_opportunity_per_original_candidate"]) + "\n\n"
        + economic_summary + "\n\n"
        "赢家定义 120D > 50%，早失败 10D < -5%，20D 确认 > 5%，60D 持续 > 10%；都是预先固定价格推断规则。"
        "主比较要求四期限共同可观测及 120D 季度完整成熟，未来/未知单独保留在 big_winner_coverage.csv。不能把对可观测结果的条件诊断推广到缺终值样本。\n\n"
        "右尾召回、误杀与左尾失败/现金机会成本同时报告。过滤器只删掉交易，因此每额外赢家的额外失败在分母无变化时无定义；不能用这项比率掩盖召回损失。"
        "0/20/50/100bps 是往返情景；cost_scenarios.csv 给出原始候选槽位等日期权的净队列结果，过滤槽位记现金零收益。"
        "该表不复利、不年化，重叠资金账本与真实成交未认证，不能称可执行策略 P&L。\n")
    supported = score.loc[score.verdict.eq("SUPPORTED_HISTORICAL_PROXY"), "hypothesis"].tolist()
    final = (
        "# EP31 最终结论\n\n"
        f"已完成七项可由封存日线定义的历史代理检验；H09 独立裁决为 BLOCKED_DATA。满足现有控制下历史代理标准的假说：{', '.join(supported) if supported else '无'}。"
        "各项统计裁决见 hypothesis_scorecard.md。不能把七项数据诊断写成八项已验证。\n\n"
        "**量价是否有超越价格/风险/规模的独立增量？** 本实验只对可用历史价格、动量、波动、成交及规模代理给出条件诊断。"
        "独立行业版本和真实股本缺失，严格 PIT、完整风险/行业控制后的 Alpha 主张仍 BLOCKED_DATA；相关性不是因果。"
        "没有共同通过方向、FDR、折间稳定和稳健性标准的变量，不能被称作可靠新增信息。\n\n"
        "**对 Big Winner 筛选的作用？** 已在同一新突破队列中比较 baseline → single H → train-only-selected all H，"
        "同时记录右尾召回、早期失败、误杀与现金机会成本。实际数值见 big_winner_incremental_value.md；"
        "原 EP20/EP28 基线、真实执行/总回报与重叠资金策略盈利未认证，不能据此建立实盘配置结论。\n\n"
        + economic_summary + "\n\n"
        "**是否有真正未见未来数据支持？** 没有。真实前瞻预测数 0、独立成熟结果数 0，FORWARD_PENDING。"
        "冻结行情止于 2026-10-21，而代码在 2026-10-22 才冻结；没有代码冻结后的完整新 t0 行情，"
        "forward_shadow/status.json 记录 BLOCKED_NEW_T0_DATA，不能把历史补录伪装为当时预测。\n\n"
        "TRADING_NOT_AUTHORIZED。正向、反向、无效或受阻结果均保留，不按外层结果继续挑窗口/参数。"
        "GOAL.md 原文与原 P0 不改写；R01、模型/预测哈希、数据 lineage、测试和前序不变性证据均另存。\n")
    (reports / "final_conclusion.md").write_text(final)
    write_json(OUT / "audits/conclusion.json", dict(historical_supported_available_controls=supported, h09="BLOCKED_DATA",
               full_industry_PIT_independence="BLOCKED_DATA", forward="FORWARD_PENDING", trading="TRADING_NOT_AUTHORIZED",
               report_generated_at=utc_now(), actual_forward_predictions=0, independently_matured_forward_labels=0))
    print(score[["hypothesis", "verdict"]].to_string(index=False))


if __name__ == "__main__":
    main()
