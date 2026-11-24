"""Build the oversold casebook from signal-time rankings and mature H10 outcomes."""
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import linear_sum_assignment

from common import get_panel


HERE = Path(__file__).resolve().parent
OUT = HERE / "results"
GROUP = ["pool", "scope", "signal_date"]
KEY = [*GROUP, "instrument"]
LABELS = [
    "持续下跌", "止跌反弹", "破低后收涨", "其他或持平", "路径未知",
]
FEATURES = ["ret5", "ret5_pct", "score_pct", "vol20", "volume_rel20", "entry_gap"]
PAIR_FIELDS = ["instrument", "name", "industry", *FEATURES, "prior_low5", "hold_low10",
               "mae10", "ret10", "entry_buy", "exit_sell"]


def make_cases(panel):
    cases = panel[panel.oversold.fillna(False)].copy()
    complete = cases[["prior_low5", "hold_low10", "ret10"]].notna().all(axis=1)
    breach = cases.hold_low10 < cases.prior_low5
    cases["breached_low"] = breach.astype("boolean").where(complete)
    cases["label"] = np.select(
        [~complete, breach & cases.ret10.lt(0), ~breach & cases.ret10.gt(0),
         breach & cases.ret10.gt(0)],
        ["路径未知", "持续下跌", "止跌反弹", "破低后收涨"],
        default="其他或持平",
    )
    cases["excess_vs_pool"] = cases.ret10 - cases.pool_ret10
    cases["two_open_gates"] = cases.entry_buy.astype("boolean") & cases.exit_sell.astype("boolean")
    return cases.sort_values(KEY, ignore_index=True)


def match_outcomes(cases):
    records = []
    # Compare percentiles inside that day's oversold cohort (except model percentile).
    match_cols = ["ret5_rank_evt", "vol20_rank_evt", "score_pct"]
    work = cases.copy()
    for field in ["ret5", "vol20"]:
        work[field + "_rank_evt"] = work.groupby(GROUP)[field].rank(pct=True)
    for key, same in work.groupby([*GROUP, "selected"], sort=True):
        same = same.dropna(subset=match_cols).sort_values("instrument")
        success = same[same.label.eq("止跌反弹")]
        failure = same[same.label.eq("持续下跌")]
        if success.empty or failure.empty:
            continue
        delta = np.abs(success[match_cols].to_numpy()[:, None] -
                       failure[match_cols].to_numpy()[None, :])
        distance = delta.mean(axis=2)
        si = success.industry.fillna("未知").to_numpy()
        fi = failure.industry.fillna("未知").to_numpy()
        same_sector = (si[:, None] == fi[None, :]) & ~np.isin(si[:, None], ["未知", "", "UNKNOWN"])
        # First maximize exact industry matches and then minimize total distance.
        penalty = min(len(success), len(failure)) + 1
        rows, cols = linear_sum_assignment(distance + penalty * ~same_sector)
        for i, j in zip(rows, cols):
            a, b = success.iloc[i], failure.iloc[j]
            row = dict(zip([*GROUP, "selected"], key))
            row.update(same_industry=bool(same_sector[i, j]), distance=distance[i, j])
            for prefix, stock in [("rebound", a), ("fall", b)]:
                row.update({prefix + "_" + f: stock[f] for f in PAIR_FIELDS})
            records.append(row)
    return pd.DataFrame(records)


def replacements(panel, cases):
    """Signal-time top-up list if every oversold target was omitted; no cash or carry."""
    selected_cases = cases[cases.selected].set_index(KEY)
    records = []
    for key, daily in panel.groupby(GROUP, sort=True):
        order = daily.sort_values(["score", "instrument"], ascending=False)
        # Unknown features are ineligible as replacement evidence.
        old = order.loc[order.selected & order.oversold.fillna(False)]
        alternates = order.loc[~order.selected & order.oversold.eq(False).fillna(False)]
        assert len(alternates) >= len(old), key
        seats = int(daily.selected.sum())
        for (_, held), (_, alt) in zip(old.iterrows(), alternates.iterrows()):
            row = dict(zip(GROUP, key))
            row.update(original=held.instrument, original_name=held["name"],
                       alternate=alt.instrument, alternate_name=alt["name"],
                       old_score_pct=held.score_pct, alt_score_pct=alt.score_pct, seats=seats,
                       old_ret10=held.ret10, alt_ret10=alt.ret10,
                       old_label=selected_cases.at[(*key, held.instrument), "label"])
            for side, stock in [("old", held), ("alt", alt)]:
                row[side + "_entry_buy"] = stock.entry_buy
                row[side + "_exit_sell"] = stock.exit_sell
            records.append(row)
    rows = pd.DataFrame(records)
    flags = ["old_entry_buy", "alt_entry_buy", "old_exit_sell", "alt_exit_sell"]
    rows["both_fillable_known"] = rows[flags].fillna(False).astype(bool).all(axis=1) & (
        rows.old_ret10.notna() & rows.alt_ret10.notna())
    rows["quote_difference"] = rows.alt_ret10 - rows.old_ret10
    # One unit of fresh cash at entry; sell both legs at the same exit open.
    rows["cash_lot_diff_after_fees"] = (rows.quote_difference * .998 / 1.001).where(rows.both_fillable_known)
    return rows


def percent(x):
    return "缺报价" if pd.isna(x) else f"{x:+.2%}"


def fmt_date(day):
    return pd.Timestamp(day).strftime("%Y-%m-%d")


def identifier(row, prefix=""):
    name = row[prefix+"name"]
    return str(row[prefix+"instrument"]) if pd.isna(name) else f"{name}（{row[prefix+'instrument']}）"


def examples(pairs):
    """Show closer industry-matched pairs, implicitly weighting each pair equally."""
    lines = []
    for (pool, scope), same in pairs.groupby(["pool", "scope"]):
        ordered = same.sort_values(["selected", "same_industry", "distance", "signal_date", "rebound_instrument"],
                                   ascending=[False, False, True, True, True])
        r = ordered.iloc[0]
        stage = "主段" if scope == "primary" else "后段"
        selected = "两股均在原D10" if r.selected else "两股均在D10以外"
        industry = str(r.rebound_industry) if r.same_industry else f"{r.rebound_industry}与{r.fall_industry}"
        lines += [
            f"### {pool} {stage} · {fmt_date(r.signal_date)} · {industry}",
            "",
            f"{selected}。这是本组按入选状态、同行业优先、距离由小到大的顺序选出的第一对。",
            "",
            "| 当时可见 | 后来止跌反弹 | 后来持续下跌 |",
            "|---|---:|---:|",
            f"| 证券 | {identifier(r, 'rebound_')} | {identifier(r, 'fall_')} |",
            f"| 过去5日收益 | {percent(r.rebound_ret5)} | {percent(r.fall_ret5)} |",
            f"| 原分数在池内的百分位 | {r.rebound_score_pct:.1%} | {r.fall_score_pct:.1%} |",
            f"| 20日波动率 | {percent(r.rebound_vol20)} | {percent(r.fall_vol20)} |",
            f"| 当日成交量／20日均量 | {r.rebound_volume_rel20:.2f} | {r.fall_volume_rel20:.2f} |",
            "",
            f"次日开盘后十个交易日，两股最低价相对信号前低分别为"
            f"{percent(r.rebound_hold_low10/r.rebound_prior_low5-1)}、{percent(r.fall_hold_low10/r.fall_prior_low5-1)}。"
            f"从入场开盘到退出开盘，收益分别为 **{percent(r.rebound_ret10)}**、**{percent(r.fall_ret10)}**。"
            f"持有期最低价相对入场开盘的变化分别为{percent(r.rebound_mae10)}、{percent(r.fall_mae10)}。",
            "",
        ]
    return lines


def write_book(cases, pairs, repl):
    lines = [
        "# 超跌案例册 · 哪些原本想买的股票还会继续跌？", "",
        "本册中沪深300有3,987次超跌，其中413次进入原模型的最高十分组。把这413个席位全部换掉，会一并错过206个到期盈利的原目标。", "",
        "每行代表一只股票的一个信号日。以信号日收盘可知的信息筛出近5个交易日收益为负、在当期合格池收益排名后10%的股票。"
        "分别在沪深300原评分和中证800迁移评分上核对。两池重叠的股票出现两行，反映各池不同的相对排名。同一股票也会在多个日期入册。", "",
        "最近5日最低价包含信号当日。次日开盘入场，观察入场日至退出日前一日共10个交易日的盘中最低价。到第十个交易日之后的下一开盘比较两端价格。"
        "日线最低价只用于事后观察路径。报价按项目复权口径，收益为毛收益，复权价格单位不能直接当作当时的委托价格。", "",
        "| 事后分类 | 入册判定 |",
        "|---|---|",
        "| 持续下跌 | 持有期最低价严格低于信号前低，且开盘到开盘收益为负。期间允许出现反弹，微幅亏损也计入本组，跌幅大小另看数值。 |",
        "| 止跌反弹 | 持有期未破前低，且开盘到开盘收益为正。 |",
        "| 破低后收涨 | 持有期破前低，但持有至退出开盘收益为正。 |",
        "| 其他或持平 | 未破前低但期末亏损，或期末收益为零。 |",
        "| 路径未知 | 前低、完整十日最低价或开盘收益有缺口。 |", "",
        "## 全部触发与原模型选择", "",
        "| 池 | 区间 | 股票日 | 日期 | 不同股票 | 原D10目标 | 持续下跌 | 止跌反弹 | 破低后收涨 | 其他或持平 | 未知 |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for (pool, scope), g in cases.groupby(["pool","scope"]):
        nums = [len(g), g.signal_date.nunique(), g.instrument.nunique(), int(g.selected.sum()),
                *[int(g.label.eq(v).sum()) for v in LABELS]]
        stage = "主段" if scope=="primary" else "后段"
        lines.append(f"| {pool} | {stage} | " + " | ".join(map(str,nums))+" |")
    lines += ["", "主段100期，入场2021-01-11至最后退出2025-03-03。后段39期，至2026-10-12。D10指原模型评分最高十分组，表中为收盘后生成的目标名单。开盘能否买入、到期能否卖出在明细中分列。"
              "所有触发均入册，包括普通路径、形态不明确和报价缺失的情形。"
              "[全案例 CSV](results/oversold_cases.csv.gz) · [分日期、标签与入选状态计数](results/oversold_counts.csv)", "",
              "## 同日成败对照", "",
              "仅将“持续下跌”和“止跌反弹”配成一对，要求股票池、信号日、原D10入选状态一致。"
              "在可配股票中先最大化同行业配对数，再最小化匹配距离。距离为5日收益在当日超跌组的百分位差、20日波动率在该组的百分位差、原分数在整个池的百分位差三者的绝对值均值。"
              "同一组内每只股票最多匹配一次。不同D10席位的成败两例数量不等时只保留可成对部分，跨行业例在明细明确标注。", "",
              f"共有{len(pairs):,}对，其中{int(pairs.same_industry.sum()):,}对同行业，{int(pairs.selected.sum()):,}对都属于D10。"
              "以下展示按信号日信息选出的代表对。成败标签来自当时尚未知的后续结果，收益差只能用于辨认形态，两池的案例也可能相同。"
              "[全部同日配对](results/oversold_pairs.csv.gz) · [两组配对的实际价格路径](results/example_paths.png)", ""]
    lines.extend(examples(pairs))
    lines += ["## 破低仍收涨的真实路径", "",
              "仅凭盘中再破前低就回避，会错过部分到期盈利的股票。下表按池和区间展示原D10中“破低后收涨”的一例，取终点收益最接近该组中位数者，再按日期和代码打破平局。", "",
              "| 池 | 区间 | 信号日 | 股票 | 原5日跌幅 | 入场后最低价相对前低 | 开盘到开盘 |",
              "|---|---|---|---|---:|---:|---:|"]
    for (pool,scope),g in cases[cases.selected & cases.label.eq("破低后收涨")].groupby(["pool","scope"]):
        r = g.assign(dist=(g.ret10-g.ret10.median()).abs()).sort_values(["dist","signal_date","instrument"]).iloc[0]
        stage = "主段" if scope=="primary" else "后段"
        lines.append(f"| {pool} | {stage} | {fmt_date(r.signal_date)} | {identifier(r)} | {percent(r.ret5)} | {percent(r.hold_low10/r.prior_low5-1)} | {percent(r.ret10)} |")
    lines += ["", "## 如果回避所有超跌席位，会错过多少反弹？", "",
              "用一条可在信号收盘时形成的简单规则做机会成本对照。将原D10中的超跌目标移出，按原分数依次从D10以外补入非超跌股票。"
              "同日同池每个替代股只使用一次，排序平局时取代码较大者，和原模型取尾组的方向一致。替代名单不读取次日成交门控或未来收益。", "",
              "| 池 | 区间 | 对照席位 | 原股持续下跌 | 原股到期盈利 | 两股买卖均可成交且有报价 | 单位现金扣费收益差，替代减原股（bp） |",
              "|---|---|---:|---:|---:|---:|---:|"]
    for (pool,scope),g in repl.groupby(["pool","scope"]):
        stage = "主段" if scope=="primary" else "后段"
        lines.append(f"| {pool} | {stage} | {len(g)} | {g.old_label.eq('持续下跌').sum()} | {g.old_ret10.gt(0).sum()} | {g.both_fillable_known.sum()} | {g.cash_lot_diff_after_fees.mean()*1e4:+.2f} |")
    lines += ["", "最右列对原股和替代股各用一单位现金从同一开盘买入，持有到同一开盘卖出。只有双方的入场买门、退出卖门和开盘价都可核查时才计算。买费10 bp、卖费20 bp。"
              "每行等权平均席位差，分母为可比席位数。受限和缺价的席位仍留在底表。连续账户的跨期持仓差额、现金拖累和延迟卖出需要单独回放。"
              "[原目标与同日替代明细](results/oversold_replacements.csv.gz)", "",
              "当前标签衡量买入后的十日路径。用于训练时，仅能抽取退出日已经到期的案例。人工阅读这些历史案例会消耗独立检验信息，后续应使用未参与选例的时间段检验回避模型。", ""]
    (HERE/"OVERSOLD_CASEBOOK.md").write_text("\n".join(lines))


def main():
    panel = get_panel()
    cases = make_cases(panel)
    pairs = match_outcomes(cases)
    repl = replacements(panel, cases)
    assert not cases.duplicated(KEY).any()
    assert (cases.ret5 < 0).all()
    assert (cases.ret5_pct <= .10 + 1e-12).all()
    assert len(repl) == int(cases.selected.sum())
    assert not repl.duplicated([*GROUP,"alternate"]).any()
    assert not pairs.duplicated([*GROUP,"rebound_instrument"]).any()
    assert not pairs.duplicated([*GROUP,"fall_instrument"]).any()
    assert len(cases[cases.pool.str.contains("300")]) == 3987
    assert cases[cases.pool.str.contains("300")].selected.sum() == 413
    OUT.mkdir(exist_ok=True)
    for frame, filename in [(cases, "oversold_cases"), (pairs, "oversold_pairs"),
                            (repl, "oversold_replacements")]:
        frame.to_csv(OUT/f"{filename}.csv.gz", index=False, compression={"method":"gzip","mtime":0})
    counts = cases.groupby([*GROUP,"label","selected"]).size().rename("count").reset_index()
    counts.to_csv(OUT/"oversold_counts.csv",index=False)
    write_book(cases, pairs, repl)
    print(f"oversold cases={len(cases)}, pairs={len(pairs)}, replacement seats={len(repl)}")


if __name__ == "__main__":
    main()
