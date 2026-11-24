"""Compile the EP39 breakout book from the shared historical signal-day panel."""
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import linear_sum_assignment

HERE = Path(__file__).resolve().parent
OUT = HERE / "results"
LABELS = ["延续", "失败", "中间", "未知"]
SCOPES = {"primary": "主段", "later": "后段"}
POOLS = {"CSI300": "沪深300", "CSI800": "中证800"}
ORDER = ["pool", "signal_date", "instrument"]
SCORE_GAP = 0.10
BREAKOUT_GAP = 0.02
MATCH_COLS = ["pair_id", "pool", "scope", "signal_date", "selected", "continued_id",
              "failed_id", "score_pct_gap", "breakout_gap", "distance", "same_industry"]


def classify(panel):
    cases = panel.loc[panel.breakout.fillna(False)].copy().sort_values(ORDER)
    assert not cases.duplicated(ORDER).any() and cases.breakout_pct.gt(0).all()
    count = cases.above_high_days
    assert count.dropna().between(0, 10).all()
    known = count.notna() & cases.ret10.notna()
    cases["label"] = "中间"
    cases.loc[known & count.ge(6) & cases.ret10.gt(0), "label"] = "延续"
    cases.loc[known & count.le(4) & cases.ret10.lt(0), "label"] = "失败"
    cases.loc[~known, "label"] = "未知"
    cases["unknown_path"] = count.isna()
    cases["unknown_open_return"] = cases.ret10.isna()
    cases["case_id"] = cases.pool + "_" + cases.signal_date.dt.strftime("%Y%m%d") + "_" + cases.instrument
    return cases


def match_pairs(cases):
    rows = []
    for (pool, date, selected), day in cases.groupby(["pool", "signal_date", "selected"]):
        positive = day[day.label.eq("延续")].sort_values("instrument").reset_index(drop=True)
        negative = day[day.label.eq("失败")].sort_values("instrument").reset_index(drop=True)
        if positive.empty or negative.empty:
            continue
        score = abs(np.subtract.outer(positive.score_pct.to_numpy(float), negative.score_pct.to_numpy(float)))
        strength = abs(np.subtract.outer(positive.breakout_pct.to_numpy(float), negative.breakout_pct.to_numpy(float)))
        valid = np.isfinite(score) & np.isfinite(strength) & (score <= SCORE_GAP) & (strength <= BREAKOUT_GAP)
        distance = score / SCORE_GAP + strength / BREAKOUT_GAP
        # Every valid edge costs <= 2. One forbidden edge costs more than all valid edges.
        penalty = 2 * min(len(positive), len(negative)) + 1
        ix, jx = linear_sum_assignment(np.where(valid, distance, penalty))
        for i, j in zip(ix, jx):
            if valid[i, j]:
                a, b = positive.iloc[i], negative.iloc[j]
                rows.append(dict(pool=pool, scope=a.scope, signal_date=date, selected=selected,
                                 continued_id=a.case_id, failed_id=b.case_id,
                                 score_pct_gap=score[i, j], breakout_gap=strength[i, j],
                                 distance=distance[i, j],
                                 same_industry=a.industry == b.industry if pd.notna(a.industry) and pd.notna(b.industry) and a.industry not in ("未知", "UNKNOWN") and b.industry not in ("未知", "UNKNOWN") else pd.NA))
    pairs = pd.DataFrame(rows)
    if pairs.empty:
        return pd.DataFrame(columns=MATCH_COLS)
    pairs = pairs.sort_values(["pool", "signal_date", "continued_id", "failed_id"])
    pairs["pair_id"] = "BR_" + pairs.continued_id.str.replace("_", "-", regex=False) + "_" + pairs.failed_id.str.split("_").str[-1]
    assert not pairs.continued_id.duplicated().any() and not pairs.failed_id.duplicated().any()
    return pairs[MATCH_COLS]


def build_summary(cases):
    rows = []
    for (pool, scope), group in cases.groupby(["pool", "scope"]):
        for selection, mask in [("全部", np.ones(len(group), dtype=bool)), ("D10", group.selected)]:
            block = group.loc[mask]
            counts = block.label.value_counts().reindex(LABELS, fill_value=0)
            rows.append(dict(pool=pool, scope=scope, selection=selection, n=len(block),
                             dates=block.signal_date.nunique(), instruments=block.instrument.nunique(),
                             **counts.to_dict()))
    return pd.DataFrame(rows)


def plot(summary):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib import font_manager
    available = {f.name for f in font_manager.fontManager.ttflist}
    font = next((f for f in ["Noto Sans CJK SC", "WenQuanYi Zen Hei", "Noto Sans CJK JP"] if f in available), None)
    if font:
        plt.rcParams["font.sans-serif"] = [font, *plt.rcParams["font.sans-serif"]]
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.1), sharex=True, sharey=True)
    colors = ["#177e71", "#bd554a", "#bdc6cc", "#403a4c"]
    for ax, pool in zip(axes, POOLS):
        y = 0
        for scope in SCOPES:
            for selection in ["全部", "D10"]:
                r = summary[(summary.pool == pool) & (summary.scope == scope) & (summary.selection == selection)].iloc[0]
                left = 0
                for label, color in zip(LABELS, colors):
                    pct = 100*r[label]/r.n if r.n else 0
                    ax.barh(y, pct, left=left, color=color, height=.68, label=label if y==0 else None)
                    if pct >= 16:
                        ax.text(left+pct/2, y, f"{pct:.0f}%", ha="center", va="center",
                                color="white" if label != "中间" else "#222", fontsize=9)
                    left += pct
                y += 1
        ax.set_title(POOLS[pool]); ax.set_xlim(0,100)
        ax.set_yticks(range(4), ["主段全部", "主段D10", "后段全部", "后段D10"])
        ax.set_xlabel("占该组突破案例数（%）")
        ax.spines[["right","top"]].set_visible(False)
    axes[0].invert_yaxis()
    fig.legend(*axes[0].get_legend_handles_labels(), loc="lower center", ncol=4, frameon=False)
    fig.tight_layout(rect=(0,.13,1,1))
    fig.savefig(OUT/"breakout_outcomes.png", dpi=160, bbox_inches="tight")
    plt.close(fig)


def fmt(x, pattern):
    return format(x, pattern) if pd.notna(x) else "未知"


def signed(x):
    return fmt(x, "+.2%")


def flag(x):
    return ("可" if x else "受限") if pd.notna(x) else "未知"


def stock(r):
    name = r["name"] if pd.notna(r["name"]) else ""
    return f"{name} {r.instrument}".strip()


def gate(r):
    return f"{flag(r.entry_buy)}／{flag(r.exit_sell)}"


def example_pairs(pairs, cases):
    table = cases.set_index("case_id", drop=False)
    picked = []
    shown = set()
    for pool in POOLS:
        for scope in SCOPES:
            block = pairs.loc[(pairs.pool == pool) & (pairs.scope == scope)].copy()
            if block.empty:
                continue
            block["already_shown"] = [
                (a.split("_", 1)[1], b.split("_", 1)[1]) in shown
                for a,b in zip(block.continued_id, block.failed_id)
            ]
            order = ["selected", "already_shown", "distance", "signal_date", "continued_id", "failed_id"]
            r = block.sort_values(order, ascending=[False,True,True,True,True,True]).iloc[0]
            shown.add((r.continued_id.split("_",1)[1], r.failed_id.split("_",1)[1]))
            picked.append((r, table.loc[r.continued_id], table.loc[r.failed_id]))
    return picked


def report(panel, cases, pairs, summary):
    total = summary[summary.selection.eq("全部")].groupby("pool")[["n", *LABELS]].sum()
    lines = [
        "# 突破案例册",
        "",
        "哪一种突破能让次日开盘买入的人赚到钱？这里把“突破后还站在前高之上”和“次日开盘买入后的十日收益”分别记录。一只股票在收盘时发出信号，两项结果都要到后来才能看到。",
        "",
        "沪深300有{:,}个突破股票日，其中{:,.0f}个延续、{:,.0f}个失败；中证800有{:,}个，其中{:,.0f}个延续、{:,.0f}个失败。案例包含相似突破在后来走向两端的记录；能否提前区分它们，需要在后续冻结训练和完整账户中检验。".format(*total.loc["CSI300", ["n","延续","失败"]], *total.loc["CSI800", ["n","延续","失败"]]),
        "",
        "## 入册与标签",
        "",
        "逐个历史信号日，在当期合格成分中选出信号日收盘价严格高于此前20个交易日最高价的股票。前高用前复权最高价，窗口截至前一交易日。突破幅度等于信号收盘价除以前高再减一。同一证券在不同日期可以多次出现，同日同时属于两池的证券分别记录其池内分位和D10席位。",
        "",
        "信号后第1个交易日为入场日，随后第10个持有日收盘后，在第11个交易日开盘计退出。十日站稳天数是这10个持有日的收盘价大于或等于原前高的天数。十日收益按复权开盘报价计算。6至10天站稳且收益为正，标为**延续**；0至4天站稳且收益为负，标为**失败**。5天站稳、收益为零、形态与收益方向矛盾等情况记为**中间**。开盘收益缺失或十日收盘路径不全记为**未知**。这是本册为区分清晰两端设定的操作定义，尚待后续时期检验。",
        "",
        "次日开盘跳空属于事后观察。入场买入和退出卖出的门控另外保存，遇到封板或停牌时仍保留报价案例。实付费、等待成交和组合现金需要单独重放账户。",
        "",
        "## 完整样本",
        "",
        "| 池和区间 | 样本 | 股票日 | 信号日 | 不同股票 | 延续 | 失败 | 中间 | 未知 |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for pool in POOLS:
        for scope in SCOPES:
            for _,r in summary[(summary.pool==pool)&(summary.scope==scope)].iterrows():
                lines.append(f"| {POOLS[pool]}·{SCOPES[scope]} | {r.selection} | {r.n} | {r.dates} | {r.instruments} | " + " | ".join(str(r[s]) for s in LABELS) + " |")
    lines += ["", "![两池主段与后段全部突破和D10突破的结果分布](results/breakout_outcomes.png)", "",
              "主段为100个原时钟窗口，后段为39个。表中信号日只统计该组至少有一个突破的日期，所有百分比按股票日计算。D10是信号日原评分选入的股票。两池重叠、同一证券重复出现、同日个股共同受市场影响，都需要在后续验证中保留。",
              "", "## 同日、相近评分与相近突破幅度的对照", "",
              "在每个池、信号日、D10身份内，对延续与失败案例作一对一匹配。原模型池内分位相差至多10个百分点，突破幅度相差至多2个百分点。先最大化可配对数量，再最小化两项差值分别除以上限后的总和。并列时按证券代码排序后进行匹配。该步骤使用到期后的标签，只用于对读案例。配对不控制行业，判读时保留行业名称。",
              "", "| 股票池 | 区间 | 全部配对 | D10配对 |", "|---|---|---:|---:|"]
    for pool in POOLS:
        for scope in SCOPES:
            p = pairs[(pairs.pool==pool)&(pairs.scope==scope)]
            lines.append(f"| {POOLS[pool]} | {SCOPES[scope]} | {len(p)} | {p.selected.sum()} |")
    lines += ["","每个区间优先展示真实D10决策中差距最小的一对，跨池展示时优先取未展示过的证券对。读者可用相同规则从完整配对表重建本页。以下“信号收盘／前高”均为前复权档案报价。"]
    for r,a,b in example_pairs(pairs,cases):
        lines += ["", f"### {POOLS[r.pool]} · {SCOPES[r.scope]} · {r.signal_date:%Y-%m-%d}", "",
                  f"两只股票{'均进入' if r.selected else '均未进入'}D10。原分位相差{r.score_pct_gap*100:.2f}个百分点，突破幅度相差{r.breakout_gap*100:.2f}个百分点。先读下表中的信号日信息。", "",
                  "| 股票 | 行业 | 信号收盘／前高 | 突破幅度 | 原分位 | 近5日收益 | 量比（20日） |", "|---|---|---:|---:|---:|---:|---:|"]
        for s in [a,b]:
            lines.append(f"| {stock(s)} | {s.industry if pd.notna(s.industry) else '未知'} | {fmt(s.close,'.3f')}／{fmt(s.prior_high20,'.3f')} | {signed(s.breakout_pct)} | {fmt(s.score_pct,'.1%')} | {signed(s.ret5)} | {fmt(s.volume_rel20,'.2f')} |")
        lines += ["",f"取{a.entry_date:%Y-%m-%d}与{a.exit_date:%Y-%m-%d}两个开盘报价计算收益。", "",
                  "| 股票 | 次日开盘跳空 | 站稳天数／10 | 十日毛收益 | 较本池等权（百分点） | 入场买／退出卖 | 结果 |","|---|---:|---:|---:|---:|---|---|"]
        for s in [a,b]:
            lines.append(f"| {stock(s)} | {signed(s.entry_gap)} | {s.above_high_days:.0f} | {signed(s.ret10)} | {fmt(100*(s.ret10-s.pool_ret10),'+.2f')} | {gate(s)} | {s.label} |")
        if r.pool == "CSI300" and r.scope == "primary":
            lines += ["", "[两组配对的实际价格路径](results/example_paths.png)"]
    lines += ["","## 两端之外的案例","","同一规则也会遇到以下情形。每类取档案中最早的信号日，再按池和代码选首例。空缺用“未知”表示。", "",
              "| 情形 | 股票池 | 信号日 | 股票 | 突破幅度 | 站稳天数 | 十日毛收益 |", "|---|---|---|---|---:|---:|---:|"]
    masks=[("站稳但开盘买入后亏损",cases.above_high_days.ge(6)&cases.ret10.lt(0)),
           ("站稳不足五天但开盘买入后盈利",cases.above_high_days.le(4)&cases.ret10.gt(0)),
           ("结果未知",cases.label.eq("未知"))]
    for desc,mask in masks:
        sample=cases.loc[mask].sort_values(["signal_date","pool","instrument"])
        if len(sample):
            s=sample.iloc[0]
            lines.append(f"| {desc} | {POOLS[s.pool]} | {s.signal_date:%Y-%m-%d} | {stock(s)} | {signed(s.breakout_pct)} | {fmt(s.above_high_days,'.0f')} | {signed(s.ret10)} |")
    unknown_input = panel.breakout.isna().sum()
    lines += ["", f"信号日信息不足以判断是否突破的股票日为{unknown_input:,}个（两池相加）。入册后十日路径不全的记录为{int(cases.unknown_path.sum()):,}个，进出开盘端点缺失为{int(cases.unknown_open_return.sum()):,}个，两种缺口可能重合。", "",
              "[完整突破案例 CSV](results/breakout_cases.csv.gz) · [全部一对一配对 CSV](results/breakout_pairs.csv.gz) · [分组统计](results/breakout_summary.csv) · [生成程序](breakout.py)", ""]
    return "\n".join(lines)


def main():
    from common import get_panel
    panel = get_panel()
    cases = classify(panel)
    pairs = match_pairs(cases)
    summary = build_summary(cases)
    OUT.mkdir(parents=True, exist_ok=True)
    for frame, name in [(cases, "cases"),(pairs, "pairs")]:
        frame.to_csv(OUT/f"breakout_{name}.csv.gz", index=False,
                     compression={"method":"gzip","mtime":0})
    summary.to_csv(OUT/"breakout_summary.csv",index=False)
    example_rows = []
    for pair, a, b in example_pairs(pairs, cases):
        for row in (a, b):
            sample = row[["pool", "scope", "signal_date", "entry_date", "exit_date", "case_id",
                          "instrument", "name", "label", "prior_high20", "close", "above_high_days", "ret10"]].to_dict()
            example_rows.append(dict(pair_id=pair.pair_id, **sample))
    pd.DataFrame(example_rows).to_csv(OUT/"breakout_examples.csv", index=False)
    plot(summary)
    (HERE/"BREAKOUT_CASEBOOK.md").write_text(report(panel,cases,pairs,summary))


if __name__ == "__main__":
    main()
