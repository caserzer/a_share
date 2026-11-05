"""Append-only documentation of frozen EP31 results; no fits or new inference."""
from __future__ import annotations
import csv
import hashlib
import json
import math
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "reports/hypotheses"
INPUTS = {}
CHECKS = []
SPEC = {
    "H01": ("异常换手与后续收益", "MA20(turnover)/MA250(turnover)", 20, -1,
            "异常换手越高，未来20D条件收益越低。", "放量代表有效信息，趋势继续而非反转。"),
    "H02": ("短长成交量偏离与后续收益", "MA21(volume)/MA200(volume)-1", 60, -1,
            "近期量相对长期量越高，未来60D条件收益越低。", "放量是趋势确认，后续收益更高。"),
    "H03": ("动量与换手交互反转", "mom60 × train_ECDF(turnover20)", 20, -1,
            "前期涨幅较高时，高换手对应更弱的未来20D条件收益。", "高换手强势股继续领涨。"),
    "H07": ("异常成交与未来已实现波动", "log(volume/MA20(volume))", 20, 1,
            "异常成交越高，未来20D已实现方差越高且改善预测损失；不预设收益方向。", "成交不含新增波动信息，或其条件方向相反。"),
    "H09": ("小笔成交占比与后续收益", "真实逐笔small-trade count/amount share", 20, 1,
            "小笔成交占比上升预测未来20D正向条件收益。", "小单只反映散户噪声、关注过热或后续反转。"),
    "H10": ("极端换手与小实体的下行风险", "I(relative_turnover≥train_q80) × I(EFF≤train_q20)", 20, 1,
            "高相对换手与小实体共同出现时，未来20D跌幅超过10%的尾部风险升高。", "小实体是筹码吸收，之后价格上涨。"),
    "H11": ("突破相对量与突破后收益", "volume/MA20(volume)", 20, -1,
            "控制可观测突破强度等变量后，低相对成交量突破的20D收益高于高量突破。", "放量突破才是有效确认。"),
    "H12": ("上涨缩量与趋势衰竭", "max(mom20,0) × max(-OLS_slope20(log(turnover)),0)", 20, -1,
            "上涨且成交活跃度下降越强，未来20D条件收益越低。", "缩量上涨是低拥挤的健康趋势。"),
}
WHY = {
    "H01": "主汇总负向，FDR和季度方向比例通过，但训练标签置乱后仍出现名义显著的正损失改善，独立信息归因未建立。滚动窗高减低残差收益还与扩展窗异号，不能据主斜率宣称单调可交易效应。",
    "H02": "主汇总负向且FDR通过，但仅14/21个完整季度同向，低于70%。换手率重表达的区间包含零，且其样本与成交量主定义不同，不能把数值差异全部解释为公司行动。",
    "H03": "交互项点估计负向，但95%区间跨零、FDR未通过，完整季度同向比例低于70%。双排序是描述性检查，不能替代主交互检验。",
    "H07": "log方差预测误差改善且FDR通过，但22个完整扩展窗季度的成交因子系数全部为负。损失改善与预注册正向机制不等价，不能支持“异常成交越高、未来波动越高”，也不能推断成交导致波动下降。",
    "H10": "Brier改善量很小，95%区间跨零、FDR未通过，只有13/22个季度同时满足损失改善与正向系数，稳健性联合门槛也未建立。日线烛形无法证明微观冲击机制。",
    "H11": "主斜率为正，与预注册负方向相反，95%区间跨零、FDR未通过，只有11/22个季度同向。可观测控制下没有建立低量突破优于高量突破的稳定证据。",
    "H12": "主斜率为正，与预注册负方向相反，区间跨零且FDR未通过，只有10/22个季度同向。加入H01/H02后的限制样本中同样未建立负向增量，不能把上涨缩量判为稳定衰竭信号。",
}
DETAIL = {
    "H01": "这里ATR指异常换手比，不是价格True Range。控制包含当期log换手水平，检验相对历史活跃度的增量。",
    "H02": "主特征使用成交股数/量短长比，送转和流通股改变可能污染相对量；另存换手率重算及行动/股本代理变化剔除诊断，独立历史股本未接入。",
    "H03": "turnover20为20D均换手。分位来自本折训练队列经验CDF，不是全样本或每日截面百分位。基线额外包含turnover_percentile及已有mom60，增量项为交互。双排序边界为训练mom60、turnover20各30%/70%，形成九格。",
    "H07": "RV实际为未来20个日对数收益平方的均值（方差，未开平方、未年化）；目标log(RV+1e-12)，t+20收盘15:00成熟。主指标为同队列baseline MSE−augmented MSE，正值为改善，同时检查预注册正系数。另存同方差口径QLIKE。5/20/60历史方差HAR-like基线并非标准日/周/月HAR规格。",
    "H10": "EFF=abs(raw_close-raw_open)/max(raw_high-raw_low,1e-12)。高换手/低EFF来自本折H10训练episode的80%/20%分位，非全证券无条件分位。基线已含两单独指示，增量为交互。目标I(20D价变<−10%)；Ridge线性概率评分时裁剪至[0,1]，Brier为概率均方误差，baseline−augmented正值为改善。这不是Kyle lambda，不能识别主动买卖盘。",
    "H11": "突破强度=close/过去120日最高收盘−1，前高严格排除当前收盘。比较采用线性条件控制，未实施逐对匹配；另存仅价格突破/动量基线。未单独加入价格ATR，不把异常换手ATR混作价格ATR。",
    "H12": "log换手斜率使用20点固定居中时间回归。实际是截断连续交互，并非“上涨且斜率负”的二元标记；大量零值可能使两端排序缺组。主模型不含H01/H02；另在ATR、MAVD共同可用限制样本中加入两者控制。",
}

def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def read(rel):
    p = ROOT / rel
    INPUTS[rel] = sha(p)
    return p.read_text()

def records(rel):
    # Preserve SHA256 and identifiers as strings; no numeric dtype inference.
    return list(csv.DictReader(read(rel).splitlines()))

def data(name):
    return records("outputs/metrics/" + name + ".csv")

def obj(rel):
    return json.loads(read(rel))

def fmt(v):
    if v is None or v == "":
        return "—"
    if isinstance(v, bool) or str(v) in ("True", "False"):
        return str(v)
    try:
        f = float(v)
        if not math.isfinite(f):
            return "—"
        return str(int(f)) if f.is_integer() and abs(f) < 1e12 else format(f, ".10g")
    except (ValueError, TypeError):
        return str(v).replace("|", "\\|").replace("\n", " ")

def table(rows, cols):
    if not rows:
        return "本项无已保存结果，不补造数值。\n"
    return ("| " + " | ".join(label for _, label in cols) + " |\n| " +
            " | ".join("---" for _ in cols) + " |\n" +
            "\n".join("| " + " | ".join(fmt(r.get(k)) for k, _ in cols) + " |" for r in rows) + "\n")

def link(rel, label=None):
    read(rel)
    return f"[{label or Path(rel).name}](../../{rel})"

def sec(title, body):
    return f"\n## {title}\n\n{body}\n"

def sub(rows, h):
    return [r for r in rows if r.get("hypothesis") == h]

def aggregate(rows, keys, fields):
    groups = defaultdict(lambda: defaultdict(int))
    for r in rows:
        for f in fields:
            groups[tuple(r[k] for k in keys)][f] += int(float(r[f] or 0))
    return [dict(zip(keys, k), **v) for k, v in sorted(groups.items())]

def check(name, passed, **details):
    CHECKS.append(dict(name=name, passed=bool(passed), **details))
    if not passed:
        raise AssertionError(name + ": " + str(details))

def verify_original(stage, publication):
    bad = [r["path"] for r in publication["files"] if
           not (ROOT / r["path"]).exists() or sha(ROOT / r["path"]) != r["sha256"]]
    check("original_publication_unchanged_" + stage, not bad, files=len(publication["files"]), mismatches=bad)

def contract(h, robust):
    text = (
        "数据封存截至**2026-10-21**；EP30 D2-v5 release ID为 "
        "9ba9324e4ff8f3a5db14c03893d76c77097855d3f83e9dde2b476f2760aec72e。"
        "本报告仅展开已保存结果，不新增实验，不重新选择参数或方向。\n\n"
        "OHLCV、成交额、换手率、身份链及复权比率均为**Historical-proxy / inferred**；"
        "known_at=t0 15:00是假定日线完整可用的模拟时点，未获历史逐时点发布证明。"
        "独立行业版本、真实股本、严格PIT、退市终值、真实总回报和成交认证仍受阻。"
        "规模控制raw_close×volume/turnover为代理；板块不等于行业。"
        "后来退市状态和厂商分歧仅用于审计/敏感性，不作为模型输入，不用今日存续证券池回填历史。\n\n"
        "EP30的35,170个文件哈希通过；月度四期限2,103,048行独立重算零差异，"
        "84条无报价标签保持UNKNOWN。这是共有数据对账，不是本H独立样本量。"
        "5,919个身份中86个无报价，特征选中行涉及5,823个证券；warmup/因子不可用者未进入本H预测分母。\n\n"
        "特征按交易日历重排，缺行情不前填；至少250个有效观测，均线另需窗口完整。"
        "冲突特征掩蔽；控制项可由训练中位数及缺失指示处理，标签绝不填零。"
        "price/total/executable是同一前复权价变别名，只用一次，非三份样本或含息收益。\n\n")
    text += table(records("outputs/audits/field_quality.csv"), [("field","字段域"),("quality","质量"),("reason","限制")])
    text += "\n共同证券总体按年板块覆盖见" + link("outputs/audits/population_by_year_board.csv") + "；尚未扣除各H因子缺失，不等于本H评分分母。"
    if h != "H09":
        text += "\n\n本H完整主端点季度的实际扩展窗预测队列如下。年份/板块为各自边际，互相重叠不能相加；已知+未知=总行数。\n\n"
        text += table([r for r in robust if r["scheme"]=="expanding" and r["domain"] in ("year","board")],
                      [("domain","分组"),("level","值"),("total_rows","预测总行"),("rows","主标签已知"),("unknown","未知")])
    return text

def method(h):
    _, feature, horizon, direction, hypothesis, opposite = SPEC[h]
    cohort = ("按周最后一个完整交易周的最后交易日收盘生成截面。" if h not in ("H10","H11") else
              "日线触发：" + ("relative_turnover>1" if h=="H10" else "close>过去120D最高收盘（排除当日）") +
              "；要求observed/warmup，每证券至少20个市场交易日冷却后才保留新episode。")
    text = f"**主假说：**{hypothesis}\n\n**竞争解释：**{opposite}\n\n**实际特征：**{feature}。{cohort}\n\n{DETAIL[h]}\n\n"
    if h != "H07":
        text += (f"主期限为{horizon}个市场交易日。t0后首个正量、正开盘且未标停牌的可观察开盘为推断入场；"
                 "以t0+h为目标日，取该日或之后且晚于入场的首个可观察开盘离场，成熟于离场日09:30。"
                 "入场延迟会缩短实际持有期；未知端点/身份冲突保持UNKNOWN，未到期保持CENSORED。"
                 "不认证涨跌停可成交性或退市终值。\n\n")
    if h not in ("H07","H10"):
        text += ("主效应是**训练尺度因子对基线残差收益的偏斜率**：训练窗将因子对控制残差化为partial_x，"
                 "OOS内再对partial_x及y−baseline按日期去均值；每日均值xy、xx→月均值→Σ月xy/Σ月xx。"
                 "预注册方向为负；它不是原始收益、训练系数或可执行多空利润。\n\n")
    text += (
        "实际基线13项：mom20、mom60、rv5、rv20、rv60、log_turnover、log_float_cap_proxy、log_money、"
        "amplitude、day_return、breakthrough_strength、market_mom20、market_rv20。"
        "市场动量/方差是可用证券归一化聚合代理，非认证市场指数；行业未控制。\n\n"
        "日期等权Ridge；1%/99% winsor、缺失中位数/指示、标准化及分位边界仅训练拟合。"
        "alpha仅1/100，在成熟性对齐的最近六个月内两段递进三个月验证选一次。外层自然季度扩展窗，rolling36为稳健性。"
        "训练标签成熟时间严格早于季度首日00:00，内层再严格早于验证开始；跨证券排除标签区间重叠，替代统一120D embargo。"
        "R01成熟性修订及H02不足24整月折的排除均在任何外层评分前。\n\n"
        "模型和预测实际于2026-10-22生成、哈希后再评分，不是2021年当时发布的预测；"
        "前序已观察这些历史时期，诚实名为historical simulated OOS / chronological OOF。\n\n"
        "日统计→月统计，stationary月块bootstrap 1,999次，期望块长6月、seed310021；"
        "给出双侧95%区间和事前方向单侧p。七项有效主端点做BH-FDR，H09不进入家族。"
        "q<0.05、完整季度正确方向≥70%、跨窗/剔除稳定和负控制均是裁决条件。"
        "证券行数非独立观察，月份/6只是粗略时间块数。")
    return text

def special(h):
    text = ""
    if h == "H02":
        text += ("换手重表达的表内baseline/augmented同队列，但与主定义跨表样本不同，不做幅度差异归因；"
                 "下列p是敏感性描述，未另授确认性家族。\n\n")
        text += table(data("H02_turnover_sensitivity"), [("scheme","窗口"),("rows","已知"),("unknown","未知"),("months","月数"),
                      ("estimate","斜率"),("ci_low","95%下限"),("ci_high","95%上限"),("p_one_sided","单侧p"),("high_minus_low","高减低残差收益")])
        text += "\n" + link("outputs/metrics/H02_turnover_sensitivity.csv")
    if h == "H03":
        groups = defaultdict(list)
        for r in data("H03_double_sort"):
            groups[(r["scheme"],r["momentum_group"],r["turnover_group"])].append(r)
        rows = [dict(scheme=k[0],momentum=k[1],turnover=k[2],months=len(v),rows=sum(int(r["size"]) for r in v),
                     residual=mean(float(r["mean"]) for r in v)) for k,v in sorted(groups.items())]
        text += "九格−1/0/+1为训练边界下低/中/高组。以下仅把已存逐月格均值等月聚合，非新增显著性检验；记录数为各格已知行之和。\n\n"
        text += table(rows,[("scheme","窗口"),("momentum","动量组"),("turnover","换手组"),("months","格月数"),("rows","记录数"),("residual","等月格残差收益")])
        text += "\n" + link("outputs/metrics/H03_double_sort.csv","逐月九格明细")
    if h in ("H07","H10","H11"):
        text += ("额外基线全部逐折列出，含部分季度标记。HAR-like/历史rv20、controls_only/纯高换手/纯低EFF、"
                 "price_breakout_only分别对应H07/H10/H11。loss_mean为季度内等日期损失，主表先等日期再等月，"
                 "**加权不同，不直接相减构造新主效应**。\n\n")
        rows = sub(data("required_baseline_ablations"),h)
        fm = {(r["scheme"],r["fold"]):r["complete_quarter"] for r in sub(data("outer_fold_metrics"),h)}
        for r in rows:
            r["complete"] = fm[(r["scheme"],r["fold"])]
        text += table(rows,[("scheme","窗口"),("fold","外折"),("complete","完整"),("baseline","额外基线"),("rows","已知"),("dates","日期数"),("loss_mean","季度等日期损失")])
        text += "\n" + link("outputs/metrics/required_baseline_ablations.csv")
    if h == "H10":
        text += "\n\n校准只作已知标签行的描述性分箱，日期可跨模型/箱重复，不能相加为独立试验。未证明前瞻校准或可靠个股赔率。\n\n"
        text += table(data("H10_calibration"),[("scheme","窗口"),("model","模型"),("probability_bin","概率箱"),("rows","行数"),
                      ("dates","日期数"),("mean_probability","均预测概率"),("observed_rate","观测尾部率")])
        text += "\n" + link("outputs/metrics/H10_calibration.csv")
    if h == "H12":
        text += ("下表在H12/H01/H02共同可用队列中，对含H01/H02的基线增加H12。"
                 "表内对照同队列，但与主表不是同样本，不能把跨表差额归因为独立信息减少。p为描述性敏感性。\n\n")
        text += table(data("H12_after_H01_H02"),[("scheme","窗口"),("rows","已知"),("unknown","未知"),("estimate","斜率"),
                      ("ci_low","95%下限"),("ci_high","95%上限"),("p_one_sided","单侧p")])
        text += "\n训练共线性逐折保留，未使用外层标签：\n\n"
        text += table(records("outputs/audits/H12_train_collinearity.csv"),[("scheme","窗口"),("fold","外折"),("train_rows","训练数"),
                      ("corr_H12_H01","H12/H01"),("corr_H12_H02","H12/H02"),("corr_H01_H02","H01/H02")])
        text += "\n" + link("outputs/metrics/H12_after_H01_H02.csv") + "；" + link("outputs/audits/H12_train_collinearity.csv")
    if h == "H01":
        text += "本项另有厂商分歧、200日内复权变化、20日内股本代理跃变、最小规模组和一字行情剔除，完整数值见第7节。没有额外未保存的行业中性结果或规格搜索。"
    text += "\n\n训练期常数预测基线，损失同为季度等日期权，不与主等月损失直接相减：\n\n"
    text += table(sub(data("constant_baseline"),h),[("scheme","窗口"),("fold","季度"),("rows","已知"),("dates","日期数"),("constant","训练常数"),("loss_mean","常数预测损失")])
    return text + "\n" + link("outputs/metrics/constant_baseline.csv")

def application(h):
    variants = {"baseline",h,"combined"}
    rows = [r for r in data("big_winner_incremental") if r["variant"] in variants]
    text = (
        "这是独立于本H主检验的共同应用队列：EP31新建120D价格突破episode，baseline候选由训练预测20D收益90%阈值冻结，"
        "单H/组合采用训练预测20%过滤阈值；组合只按内验证损失选择。H02主期限虽为60D，本应用也统一20D预测规则。"
        "要求10/20/60/120D共同已知及120D完整季度（至2026Q1）。EP20/EP28原基线因队列不可比仍受阻。\n\n"
        "早失败=10D<−5%，确认=20D>5%，持续=60D>10%，赢家=120D>50%。单H未删除候选不等于已证明有效。\n\n")
    text += table(rows,[("scheme","窗口"),("variant","变体"),("baseline_candidates","共同分母"),("retained","保留"),("removed","剔除"),
                  ("baseline_winners","原赢家"),("retained_winners","保留赢家"),("retained_failures_10","保留早失败"),
                  ("winner_recall","赢家召回"),("winner_false_kill_rate","误杀率"),("failure_10_rate","早失败率"),
                  ("confirm_20_rate","确认率"),("continuation_60_rate","持续率"),
                  ("additional_failures_per_additional_winner","失败/赢家变动比"),("cash_opportunity_per_original_candidate","现金机会成本/原候选")])
    text += (
        "\n比率无定义处保留—；过滤器只删除交易，不把比率解释为额外获利交易。"
        "扩展窗组合4294→4287个候选、295→294个赢家，早失败率29.6460%→29.6944%，未建立右尾保护与早失败过滤同时改善。\n\n"
        "以下为往返0/20/50/100bps的假设情景：原候选槽位、日期等权，被过滤槽位为现金零收益；"
        "没有复利、年化或重叠资金账本，没有真实成交认证，不能称策略净利润。\n\n")
    text += table([r for r in data("cost_scenarios") if r["variant"] in variants],
                  [("scheme","窗口"),("variant","变体"),("round_trip_bps","往返bps"),("hypothetical_cohort_net_mean","假设队列净均值"),("dates","日期数")])
    return text + "\n原始证据：" + "；".join(link("outputs/metrics/"+n+".csv") for n in ("big_winner_incremental","big_winner_coverage","cost_scenarios"))

def closing(h):
    text = (
        f"**{h}最终裁决：INCONCLUSIVE。** {WHY[h]}\n\n"
        "严格PIT和完整行业风险调整主张仍为BLOCKED_DATA。独立前瞻仍**FORWARD_PENDING**："
        "行情止于2026-10-21，代码冻结于2026-10-22，真实前瞻预测和独立成熟结果均0；"
        "状态BLOCKED_NEW_T0_DATA。**TRADING_NOT_AUTHORIZED**。\n\n"
        "原计划与实际证据的差异：只保存两端10%与中间80%三组，没有完整十个十分位的单调曲线；"
        "行业和真实股本缺失；单季度最多三个月，逐折95%CI/p未估计，以INSUFFICIENT_TEMPORAL_BLOCKS保留空值。"
        "本H预测的年份×板块联合缺失明细未另存，本报告给出两者边际，共同总体另有联合覆盖表。"
        "不能因补齐报告而认为已经补齐这些实验细节。\n\n"
        "36项既有测试与回放属于共有实现验证，不是本H36份独立经济证据。追溯入口：\n\n")
    paths = ["GOAL.md","configs/preregistration.yaml","configs/revision_01_inner_maturity.yaml",
             "src/volume_price_features.py","src/baselines.py","src/walk_forward.py","src/labels_and_maturity.py",
             "src/hypothesis_tests.py","src/multiple_testing.py","src/evaluate.py","src/report.py",
             "outputs/audits/data_gate.json","outputs/audits/ep30_release_verification.json",
             "outputs/audits/monthly_reconciliation_full.csv","outputs/audits/feature_field_lineage.csv",
             "outputs/audits/tests.json","outputs/audits/all_prediction_columns_replay.json",
             "outputs/forward_shadow/status.json","outputs/manifests/publication.json"]
    return text + "\n".join("- "+link(p,p) for p in paths) + "\n\n[八假说报告索引](README.md)；[原总评分表](../hypothesis_scorecard.md)。"

def report(h,v):
    title,feature,horizon,direction,_,_ = SPEC[h]
    pooled = sub(data("pooled_oos_metrics"),h)
    folds = sub(data("outer_fold_metrics"),h)
    robust = sub(data("robustness"),h)
    manifest = obj(f"outputs/manifests/{h}_folds.json")
    complete = [r for r in folds if r["scheme"]=="expanding" and r["complete_quarter"]=="True"]
    main = next(r for r in pooled if r["scheme"]=="expanding")
    correct = sum(float(r["estimate"])*direction>0 and (h not in ("H07","H10") or float(r["factor_coefficient"])>0) for r in complete)
    check(h+"_verdict_fraction",abs(correct/len(complete)-float(v["consistent_folds"]))<1e-12)
    check(h+"_manifest_folds",len(folds)==len(manifest["folds"]))
    for scheme in ("expanding","rolling36"):
        rs = [r for r in folds if r["scheme"]==scheme and r["complete_quarter"]=="True"]
        p = next(r for r in pooled if r["scheme"]==scheme)
        for f in ("rows","total_rows","unknown"):
            check(h+"_"+scheme+"_"+f,sum(int(r[f]) for r in rs)==int(p[f]))
    text = (f"# {h} 详细测试报告：{title}\n\n**裁决：{v['verdict']}；独立前瞻：FORWARD_PENDING。** {WHY[h]}\n\n"
            "以下展开已冻结测试，区分主检验、稳健性与描述性应用。表格从已存CSV/manifest提取，"
            "不新增模型、重采样或筛选。数值保留10位有效数字，精确值见CSV。\n")
    text += sec("1. 数据契约、来源与覆盖",contract(h,robust))
    text += sec("2. 假说、实际变量与检验方法",method(h))
    rows = aggregate(sub(data("maturity_coverage"),h),["scheme","horizon","complete_quarter","status"],
                     ["rows","delayed_entry","delayed_exit","complete_path"])
    t = ("下表每期限独立汇总。True为该期限季度完整成熟，False为部分季度；部分季度的短标签不拼入主汇总。"
         "窗口/期限互相重叠，不累加为独立样本；延迟入/离场及路径计数可重叠。KNOWN_INFERRED也只是推断价变。\n\n")
    if h=="H07":
        t += "**特别说明：本表是价变标签覆盖，不是future_variance有效性。** H07主方差已知/未知以第4、5节为准。\n\n"
    t += table(rows,[("scheme","窗口"),("horizon","期限"),("complete_quarter","完整季度"),("status","状态"),("rows","行数"),
                    ("delayed_entry","延迟入场"),("delayed_exit","延迟离场"),("complete_path","完整收盘路径")])
    t += "\n"+link("outputs/metrics/maturity_coverage.csv","逐假说×窗口×期限×季度×状态明细")
    if h in ("H10","H11"):
        t += "\n\n下面为共用特征生成阶段的本事件覆盖，含训练及部分季度，尚未扣除模型因子缺失，不能与主评分行数直接相减。\n\n"
        t += table(records("outputs/audits/daily_event_and_episode_coverage.csv"),[("year","年"),("board","板块"),
                    (h.lower()+"_event_days","事件日"),(h.lower()+"_episodes","冷却后episode")])
        t += "\n"+link("outputs/audits/daily_event_and_episode_coverage.csv")
    text += sec("3. 事件、成熟性与缺失分母",t)
    t = table(pooled,[("scheme","窗口"),("endpoint","主端点"),("rows","标签已知"),("total_rows","预测总行"),("unknown","未知"),
                     ("months","月数"),("complete_quarters","完整季度"),("independent_time_blocks_approx","粗略6月块"),("estimate","主效应"),
                     ("ci_low","95%下限"),("ci_high","95%上限"),("p_one_sided","单侧p"),("q_bh","主裁决q")])
    t += ("\n主判断expanding；rolling36是预定稳健性。原评分器分别对扩展窗、滚动窗各七项主端点计算BH，"
          "此表逐行保留各窗口自己的q_bh；正式裁决只使用扩展窗q，不在两窗口之间择优。"
          "两窗口观测重叠，不能当两次独立确认。\n\n")
    gates = [
        dict(gate="BH-FDR q<0.05",actual=main["q_bh"],passed=float(main["q_bh"])<.05),
        dict(gate="完整季度正确方向≥70%",actual=f"{correct}/{len(complete)} = {correct/len(complete):.6%}",passed=correct/len(complete)>=.7),
        dict(gate="滚动/留年/规模/厂商联合稳定",actual=v["stable_leave_year_size_provider"],passed=v["stable_leave_year_size_provider"]=="True"),
        dict(gate="无显著正向置乱控制异常",actual="negative_control_flag="+v["negative_control_flag"],passed=v["negative_control_flag"]=="False")]
    t += table(gates,[("gate","标准"),("actual","实际"),("passed","通过")])
    if h in ("H07","H10"):
        lw = sum(float(r["estimate"])>0 for r in complete)
        cp = sum(float(r["factor_coefficient"])>0 for r in complete)
        t += f"\n季度同时要求损失改善且训练因子系数>0；仅损失改善为{lw}/{len(complete)}，正系数为{cp}/{len(complete)}，同时为{correct}/{len(complete)}。\n"
    t += "\n辅助描述（时间权重同主表；H07的y为log方差，H10的y为尾部0/1，不能写成收益）：\n\n"
    t += table(pooled,[("scheme","窗口"),("rank_ic","因子/残差Rank IC"),("high_minus_low","高减低残差"),("base_loss","基线损失"),
                      ("aug_loss","加因子损失"),("qlike_gain","QLIKE改善"),("y_mean","y均值"),("y_median","y日中位数均值"),
                      ("worst_5pct","y日5%分位均值"),("return_skew","价变偏度均值")])
    t += "\n"+link("outputs/metrics/pooled_oos_metrics.csv")+"；"+link("outputs/metrics/hypothesis_verdicts.csv")
    text += sec("4. 汇总主结果与逐条裁决标准",t)
    t = ("包含全部准入折；False部分季度仅展示，不计主裁决。训练系数与OOS偏斜率不同。"
         "每季最多三个月，CI/p原表为空（INSUFFICIENT_TEMPORAL_BLOCKS），不伪造逐季95%区间。\n\n")
    t += table(folds,[("scheme","窗口"),("fold","季度"),("complete_quarter","完整"),("rows","已知"),("total_rows","总行"),("unknown","未知"),
                     ("factor_coefficient","训练因子系数"),("estimate","OOS主效应"),("rank_ic","Rank IC"),("high_minus_low","高减低残差"),
                     ("base_loss","基线损失"),("aug_loss","加因子损失"),("qlike_gain","QLIKE改善"),("inference_status","区间状态")])
    text += sec("5. 逐季度外层结果",t+"\n"+link("outputs/metrics/outer_fold_metrics.csv"))
    text += sec("6. 本假说专门检验与基线消融",special(h))
    t = ("以下为全部已存切片，不挑最好年份/板块；p及区间为描述性稳健性，未另建确认性FDR家族。"
         "equal_security_descriptive是证券均权xy/xx且未按日期去均值，与主估计量不同，不解释成纯权重消融；H07/H10该项无斜率。\n\n")
    t += ("切片说明：year为年份，board为主板/创业板/科创板/北交所；size_group与liquidity_group按训练期"
          "规模/成交额代理三分位分组，market_state按市场动量代理正/非正划分；leave_one_year_out为逐年剔除。"
          "exclude_provider_disagreement、exclude_recent_factor_change、exclude_share_proxy_change、"
          "exclude_smallest_cap、exclude_one_price_bar分别剔除厂商分歧、200日内复权变化、20日内股本代理变化、"
          "最小规模组及一字行情。剔除是敏感性，不是把当时未知的未来身份用于交易过滤。\n\n")
    t += table(robust,[("scheme","窗口"),("domain","切片/剔除"),("level","值"),("rows","已知"),("unknown","未知"),("months","月数"),
                      ("estimate","效应"),("ci_low","95%下限"),("ci_high","95%上限"),("p_one_sided","描述性单侧p")])
    text += sec("7. 年份、市场状态、规模、流动性与缺失敏感性",t+"\n"+link("outputs/metrics/robustness.csv"))
    t = ("shuffle_gain：训练与测试分别同日同板块置乱因子；permlabel_gain：训练标签同日同板块置乱后，用真实未来标签评价baseline/augmented；"
         "lag_gain：全部输入精确滞后20个交易日，只在可用子集评分。板块置乱未达到行业内置乱，持续性使lag也不是数学零假说。\n\n"
         "本表全为**预测损失改善**；收益H主效应为偏斜率，单位不同，不直接比较数值。"
         "正向置乱改善且名义p<0.05是诊断异常，不能断言已证明泄漏。\n\n")
    t += table(sub(data("placebo"),h),[("scheme","窗口"),("control","对照"),("estimate","损失改善"),("ci_low","95%下限"),
                  ("ci_high","95%上限"),("p_one_sided","名义单侧p"),("months","月数")])
    t += "\n**诊断案例：**"+WHY[h]
    text += sec("8. 负控制、滞后与不能支持的案例",t+"\n\n"+link("outputs/metrics/placebo.csv"))
    t = ("只报告低10%（−1）、中间80%（0）、高10%（+1）组；边界训练确定，不是完整十分位曲线。"
         "每日先均值再等日期汇总，每期限仅其完整季度已知标签，队列/日期可不同；MFE/MAE还需完整路径。"
         "路径指标为可观察收盘及离场开盘、含零，不是盘中最优成交。六历月−20%损失比例另按已知标签行等权，"
         "不同于其余指标的日期等权；无新确认性p/q。\n\n")
    t += table(sub(data("secondary_endpoints"),h),[("scheme","窗口"),("horizon","期限"),("factor_quantile","训练分组"),("rows","已知行"),
                  ("dates","日期"),("return_mean","价变均值"),("mfe","MFE均值"),("mae","MAE均值"),("six_month_loss_below_minus20","六历月损失<−20%")])
    text += sec("9. 次要期限、两端分组与路径尾部",t+"\n"+link("outputs/metrics/secondary_endpoints.csv"))
    text += sec("10. Big Winner单H增量及成本情景",application(h))
    timeline = []
    for r in manifest["folds"]:
        timeline.append(dict(scheme=r["scheme"],fold=r["fold"],start=r["train_start"][:10],end=r["train_end"][:10],
                             train_rows=r["train_rows"],max_mature=r["max_train_mature_at"],cutoff=r["fit_cutoff"],alpha=r["alpha"],
                             inner=" / ".join(x["start"][:10] for x in r["inner_timeline"]),test_rows=r["test_rows"]))
        check(h+"_maturity_"+r["scheme"]+"_"+r["fold"],r["max_train_mature_at"]<r["fit_cutoff"])
        for x in r["inner_timeline"]:
            check(h+"_inner_"+r["scheme"]+"_"+r["fold"]+"_"+x["start"],x["max_maturity"]<x["start"])
    t = ("完整变换参数、每个内层候选损失、模型/预测路径及全SHA256见manifest。"
         "其中outer_outcomes_scored=false记录冻结时状态，不代表后来未评分。\n\n")
    t += table(timeline,[("scheme","窗口"),("fold","外折"),("start","训练t0首"),("end","训练t0末"),("train_rows","训练行"),
                        ("max_mature","训练最晚成熟"),("cutoff","拟合截止"),("alpha","alpha"),("inner","两段内验证起点"),("test_rows","预测行")])
    if h=="H02":
        t += "\nH02 2021Q1扩展/滚动两折被精确日历门禁阻断：首内训练2018-01-12至2020-01-03不足24整月，在任何外评分之前排除；原临时预测不进主结果，未迁移原定测试起点。\n"
    t += "\n事件标签同时存续峰值说明重叠，不是独立样本量。H07此计数沿用价变入/离场，不替代RV窗口重叠量。\n\n"
    t += table(sub(data("label_concurrency"),h),[("scheme","窗口"),("fold","外折"),("unique_dates","t0日期数"),("rows","预测数"),
                  ("mature","主y已知"),("max_concurrency","路径并发峰值")])
    t += "\n"+"；".join(link(p) for p in (f"outputs/manifests/{h}_folds.json",f"outputs/audits/{h}_fold_timeline.csv",
                                         "outputs/metrics/label_concurrency.csv","outputs/fold_predictions/index.csv"))
    text += sec("11. 训练时间线、参数、预测与哈希追溯",t)
    return text + sec("12. 独立裁决、未完成细节与证据入口",closing(h))

def blocked_report():
    text = ("# H09 详细准入报告：小笔成交占比与后续收益\n\n"
            "**裁决：BLOCKED_DATA；FORWARD_PENDING；TRADING_NOT_AUTHORIZED。** "
            "本项未执行收益预测检验，不存在可报告的效应、区间、p/q或支持率。数据受阻不是统计检验失败。\n")
    text += sec("1. 数据契约与实际来源",contract("H09",[]))
    text += sec("2. 待检验命题及竞争解释",
                "主命题：小笔成交占比上升预测20D正向条件收益。竞争解释：小单只反映散户噪声、注意力过热或后续反转。"
                "预注册要求真实逐笔成交计数/金额占比，小额阈值按当时训练样本冻结，记录类别和可见时点。\n\n"
                "日线volume、money、turnover和市值代理无法恢复每笔分布：相同日总量可以由不同大小、不同笔数的成交构成。"
                "不能将小盘股、高换手、小实体或低成交额改名为小单。")
    rows = [
        dict(field="trade_size / trade_count",need="逐笔股数/金额与可复核笔数",actual="UNKNOWN；仅日线聚合",result="BLOCKED"),
        dict(field="timestamp / known_at",need="逐笔时点及当时可见证明",actual="无时点证明来源",result="BLOCKED"),
        dict(field="trade_category / direction",need="方向或适当成交类别及可比口径",actual="无逐笔/委托类别",result="BLOCKED"),
        dict(field="identity / adjustments",need="证券链、送转及单位变化可追溯",actual="有日线代理，未建立逐笔链",result="BLOCKED"),
        dict(field="coverage / license",need="按年板块证券覆盖及可使用依据",actual="本轮未接入微观源",result="BLOCKED")]
    text += sec("3. 专门准入逐项核验",
                table(rows,[("field","字段/合同"),("need","准入要求"),("actual","实际证据"),("result","结论")])+
                "\n"+"；".join(link(p) for p in ("outputs/audits/data_gate.json","outputs/audits/field_quality.csv",
                                               "tests/test_microstructure_h09_gate.py")))
    text += sec("4. 预测、成熟性、训练和评分状态",
                "H09模型数=0、外层预测数=0、已评分主端点数=0；不生成不存在的逐折表。"
                "共同EP30月度对账不能代替H09微观数据对账，其他假说的周线/20D标签也不是H09样本。"
                "没有小单定义/队列，就无法确认特征起点、缺失分母、阈值、训练/验证/测试归属或历史偏差。\n\n"
                "八条假说仅七条进入有效主端点BH-FDR家族，H09不按第八个失败计入，不使用p=1、零收益或方向失败占位。")
    text += sec("5. 正反对照、稳健性及负控制",
                "未执行：没有真实特征，无法进行条件回归、排序、消融、置乱或滞后收益检验。"
                "test_microstructure_h09_gate.py只验证防止日线冒充逐笔的门禁，不是H09经济命题的实证支持。"
                "共同36项软件测试不等于本项有36份微观证据。\n\n"
                "诊断案例：把“高换手的小盘股”称为“小单占比上升”会改变对象，并引入规模/流动性混淆。"
                "本轮没有做这项替代，因此没有捏造其收益或泄漏案例。")
    text += sec("6. Big Winner应用与费用情景",
                "H09未进入单H过滤器或train-only组合，不从其他H结果外推小单筛选能力。"
                "不存在本项赢家召回、误杀、早失败改善或净效用估计；baseline不变也不能写成H09无效。"
                "费用情景不能补救输入不可识别。")
    text += sec("7. 未来重启所需的独立新实验",
                "先取得真实且获准使用的逐笔/委托源，明确类别、单位、历史覆盖、known_at及身份/行动链，"
                "审计按年板块证券分母，再用新版本预注册冻结小额阈值、聚合规则、队列和时间划分。"
                "其后才执行成熟隔离、同队列条件基线、时间块推断、置乱及独立前瞻。\n\n"
                "本节仅说明数据需求，不授权采购、获取凭据、采集新源或事后补设阈值；BLOCKED_DATA原样保留。")
    text += sec("8. 最终裁决及追溯",
                "**H09=BLOCKED_DATA**：缺有时点证明的真实成交大小、笔数和类别。尚未检验不等于证伪，"
                "本轮不能评价正方向和竞争解释谁成立。独立前瞻FORWARD_PENDING，真实新时点预测及成熟结果均0。"
                "TRADING_NOT_AUTHORIZED。\n\n"+
                "；".join(link(p) for p in ("GOAL.md","configs/preregistration.yaml","outputs/metrics/hypothesis_verdicts.csv",
                                          "outputs/audits/tests.json","outputs/forward_shadow/status.json"))+
                "\n\n[八假说报告索引](README.md)。")
    return text

def main():
    publication = obj("outputs/manifests/publication.json")
    verify_original("before",publication)
    DEST.mkdir(parents=True,exist_ok=True)
    generated = []
    index_rows = []
    for v in data("hypothesis_verdicts"):
        h = v["hypothesis"]
        content = blocked_report() if h=="H09" else report(h,v)
        p = DEST/(h+".md")
        p.write_text(content)
        generated.append(p)
        index_rows.append(dict(h=f"[{h}]({h}.md)",title=SPEC[h][0],verdict=v["verdict"],
                               reason="真实逐笔缺失，未执行主检验。" if h=="H09" else WHY[h]))
        print(f"{h}: {len(content.encode())} bytes, {len(content.splitlines())} lines")
    content = (
        "# EP31 每项假设的详细测试报告\n\n"
        "此前总评分表只列结论，缺少逐H完整展开。本目录补齐八份可独立阅读的报告："
        "数据与分母、实际变量/标签、nested walk-forward、两窗口汇总、全部外折、专门消融、稳健性、负控制、"
        "次要端点、Big Winner应用、训练时间线和证据链接。H09为独立准入报告，不能称已完成收益检验。\n\n"
        "此次只整理已冻结证据：七项历史检验均INCONCLUSIVE，H09为BLOCKED_DATA；"
        "不修改GOAL、预注册、模型、预测、主指标或裁决。全部独立前瞻FORWARD_PENDING。\n\n")
    content += table(index_rows,[("h","报告"),("title","假设"),("verdict","裁决"),("reason","关键原因")])
    content += (
        "\n建议先读各报告第4节主结果与标准，再读第5节逐折表；H09从第3节准入表阅读。"
        "空值、受阻及原计划未落实细节明确保留，文档补齐不代表新的实验通过。\n\n"
        "[原总评分表](../hypothesis_scorecard.md)；[原总论](../final_conclusion.md)；[原GOAL](../../GOAL.md)；"
        "[本次报告审计](../../outputs/audits/hypothesis_reports_v1.json)；"
        "[本次扩展清单](../../outputs/manifests/hypothesis_reports_v1.json)。\n\n"
        "复现命令（EP31目录下）：python reporting/build_hypothesis_reports.py。"
        "只读已存CSV/JSON，部分表为已有逐月值的描述性算术聚合，不训练、不重抽样、不改裁决。"
        "采用单独扩展清单，原142个publication文件字节不变；扩展清单不包含它自身。\n")
    p = DEST/"README.md"
    p.write_text(content)
    generated.append(p)
    check("eight_reports_and_index",len(generated)==9)
    for p in generated:
        content = p.read_text()
        targets = re.findall(r"\[[^\]]*\]\(([^)]+)\)",content)
        missing = []
        for target in targets:
            if "://" in target or target.startswith("#"):
                continue
            q = (p.parent/target.split("#")[0]).resolve()
            if q.name == "hypothesis_reports_v1.json":
                continue  # created below, then checked independently
            if not q.exists():
                missing.append(target)
        check(p.name+"_links",not missing,checked=len(targets),missing=missing)
        if p.name!="README.md":
            check(p.name+"_required_content",all(s in content for s in
                  ("数据契约","裁决","FORWARD_PENDING","TRADING_NOT_AUTHORIZED","负控制")))
    verify_original("after",publication)
    audit_path = ROOT/"outputs/audits/hypothesis_reports_v1.json"
    audit = dict(status="PASS",generated_at=datetime.now(timezone.utc).isoformat(),
                 scope="append_only_reporting_extension_no_new_experiment",report_count=8,index_count=1,
                 original_publication_sha256=INPUTS["outputs/manifests/publication.json"],checks=CHECKS,
                 no_refit=True,no_new_bootstrap=True,unchanged_saved_verdicts=True,
                 limitations=["H09 not tested: microstructure absent","industry/PIT uncertified",
                              "three tail groups, not full ten-decile curve","quarter CI unavailable",
                              "H11 conditional regression, not pair matching","H07 HAR-like, not canonical HAR",
                              "zero forward predictions and independently matured forward labels"])
    audit_path.write_text(json.dumps(audit,ensure_ascii=False,indent=2)+"\n")
    generated += [Path(__file__).resolve(),audit_path]
    extension = dict(status="PASS",generated_at=audit["generated_at"],self_excluded=True,
                     original_publication_files=len(publication["files"]),
                     original_publication_sha256=INPUTS["outputs/manifests/publication.json"],
                     source_artifacts=[dict(path=p,sha256=s) for p,s in sorted(INPUTS.items())],
                     files=[dict(path=str(p.relative_to(ROOT)),bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(generated)])
    target = ROOT/"outputs/manifests/hypothesis_reports_v1.json"
    target.write_text(json.dumps(extension,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps(dict(status="PASS",reports=8,original_files_verified=len(publication["files"]),checks=len(CHECKS))))

if __name__=="__main__":
    main()
