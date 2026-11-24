"""Render auditable Chinese account tables and the paired-window comparison figure."""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

EP = Path(__file__).resolve().parents[1]
RES = EP / "results"
REVIEW = RES / "training_review"
POOLS = {"CSI300": "沪深300", "CSI800": "中证800"}
SCOPES = {"primary": "主段", "later": "后段"}
TASKS = {"breakout": "突破", "oversold": "超跌"}
INDEX = ["pool", "scope", "task"]


def table(lines, header, rows):
    lines.extend(["", "| " + " | ".join(header) + " |", "|" + "---|" * len(header)])
    for row in rows:
        lines.append("| " + " | ".join(map(str, row)) + " |")
    lines.append("")


def fmt(x):
    return f"{x:+.2f}"


def percent(x):
    return f"{x:.1%}"


def figure(paired):
    plt.rcParams.update({"font.family": ["Noto Sans CJK JP", "DejaVu Sans"], "axes.unicode_minus": False})
    fig, axes = plt.subplots(1, 2, figsize=(11.0, 4.6), sharey=True, sharex=True)
    titles = {"random_mean": "相对同形态、等量随机组均值", "full": "相对全量训练"}
    keys = [(p, s, t) for p in POOLS for s in SCOPES for t in TASKS]
    for ax, (reference, title) in zip(axes, titles.items()):
        g = paired[paired.reference.eq(reference)].set_index(INDEX)
        for pos, key in enumerate(keys):
            row = g.loc[key]
            color = "#166874" if key[-1] == "breakout" else "#9b5632"
            ax.plot([row.low, row.high], [pos, pos], color=color, lw=1.8)
            ax.plot(row.net_bp, pos, "o", color=color, markersize=6)
        ax.axvline(0, color="#42474c", lw=1.1)
        ax.axhline(3.5, color="#d8dee0", lw=.8)
        ax.set_title(title, loc="left", fontsize=13)
        ax.grid(axis="x", alpha=.18)
        ax.spines[["top", "right", "left"]].set_visible(False)
        ax.tick_params(axis="y", length=0)
        ax.set_xlabel("精选减对照，bp / 十个交易日")
        ax.set_xlim(-285,110)
    axes[0].set_yticks(range(len(keys)),[f"{POOLS[p]}   {SCOPES[s]} · {TASKS[t]}" for p,s,t in keys])
    axes[0].invert_yaxis()
    fig.suptitle("精选训练在共同账户窗口的扣费净差", x=.02, ha="left", fontsize=17, fontweight="bold")
    fig.tight_layout(rect=(0,0,1,.94))
    fig.savefig(REVIEW/"paired_differences.png", dpi=155, bbox_inches="tight")
    plt.close(fig)


def pairing_coverage():
    from sys import path
    path.insert(0, str(EP))
    from breakout import classify
    from oversold import make_cases

    weekly = pd.read_parquet(RES/"training_weekly/panel.parquet").dropna(
        subset=["score", "selected", "target_rank", "maturity"])
    folds = pd.read_csv(RES/"training_fit/folds.csv")
    frames = []
    for task, make in [("breakout", classify), ("oversold", make_cases)]:
        cases = make(weekly)
        labels = ("延续", "失败") if task == "breakout" else ("止跌反弹", "持续下跌")
        pairs = pd.read_parquet(RES/f"training_fit/{task}_weekly_pairs.parquet")
        maturity = weekly.groupby("signal_date").maturity.first()
        pairs["maturity"] = pairs.signal_date.map(maturity)
        for f in folds[folds.model.eq(task+"_curated")].itertuples():
            known = cases[cases.maturity.lt(f.cutoff_exclusive)]
            used = pairs[pairs.maturity.lt(f.cutoff_exclusive)]
            sides = known.label.isin(labels).sum()
            assert f.train_rows == 2*len(used) and sides >= f.train_rows
            frames.append(dict(quarter=f.quarter, task=task, mature_scored_triggers=len(known),
                positive_extreme=known.label.eq(labels[0]).sum(), negative_extreme=known.label.eq(labels[1]).sum(),
                pairs=len(used), dates=f.train_dates, instruments=f.train_names,
                paired_fraction_of_extremes=f.train_rows/sides,
                pairs_same_industry=used.same_industry.eq(True).sum(),
                paired_same_industry_fraction=used.same_industry.eq(True).sum()/len(used)))
    result = pd.DataFrame(frames)
    result.to_csv(REVIEW/"pairing_coverage.csv", index=False)
    return result


def main():
    summary = pd.read_csv(REVIEW/"paired_summary.csv")
    all_windows = summary[summary.segment.eq("all")].copy()
    base = all_windows[all_windows.cost.eq("base")]
    figure(base)
    lines = ["# EP39 两类精选训练的账户与选股明细", "",
        "2026-11-24。两项任务各有一个精选模型及五个等量随机模型，共用一个沪深300全量训练基线。下表中，正的收益差代表精选领先。1 bp 等于0.01个百分点。所有日期均为已观察的历史。"]
    coverage = pairing_coverage()
    lines += ["", "## 训练案例覆盖", "",
        "触发行须具备历史折外评分和已成熟的原池收益秩。配对率的分母为该任务两个极端结局的股票日之和，每对包含两个不重复的股票日。超跌配对优先同行业，突破配对约束同日同原D10身份、评分分位差和突破幅度差。"]
    rows = []
    for f in coverage[coverage.quarter.isin(["2021Q1", "2026Q3"])].itertuples():
        rows.append([f.quarter,TASKS[f.task],f.mature_scored_triggers,f.positive_extreme,f.negative_extreme,
            f.pairs,f.dates,f.instruments,percent(f.paired_fraction_of_extremes),percent(f.paired_same_industry_fraction)])
    table(lines,["季度","任务","成熟可抽取触发","正例","反例","采用对数","覆盖日期","覆盖股票","极端结局入选率","配对同行业比例"],rows)
    lines += ["[23季完整覆盖表](../results/training_review/pairing_coverage.csv)", ""]
    for task, title in TASKS.items():
        model = task + "_curated"
        lines += [f"## {title}精选的收益、费用和随机波动", "",
            "每一行使用该池该段13组均可估值的同一组窗口。每个数据点是一个十交易日账户净收益。随机组先在同一窗口内对五个净收益取平均。"]
        rows, sensitivity = [], []
        for pool, pname in POOLS.items():
            for scope, sname in SCOPES.items():
                g = all_windows[(all_windows.pool==pool)&(all_windows.scope==scope)&(all_windows.task==task)]
                standard = g[g.cost.eq("base")].set_index("reference")
                cur = standard.loc["random_mean"]
                seeds = standard[standard.index.str.startswith(task+"_random_")]
                rows.append([pname,sname,cur.n,fmt(cur.gross_bp),fmt(cur.fee_bp),fmt(cur.net_bp),
                    f"{cur.wins}/{cur.n}",f"{fmt(seeds.net_bp.min())} 至 {fmt(seeds.net_bp.max())}",f"{(seeds.net_bp>0).sum()}/5"])
                diff = g.pivot(index="reference",columns="cost",values="net_bp")
                sensitivity.append([pname,sname,*[fmt(diff.at[ref,c]) for ref in ["random_mean","full"] for c in ["zero","base","double"]]])
        table(lines,["池","期间","期数","毛差 bp","实付费差 bp","净差 bp","领先随机均值的期数","相对单个种子的净差范围 bp","均值领先的种子数"],rows)
        lines += ["毛差将实际费用加回标准费账户，反映同一批交易。零费及双倍费均从初始资金重新执行，费率会改变后续可用资金。"]
        table(lines,["池","期间","对随机 · 零费","标准费","双倍费","对全量 · 零费","标准费","双倍费"],sensitivity)
    lines += ["## 账户年化与最大回撤", "",
        "每个独立账段从净值1起算，标准费为买10 bp、卖20 bp。括号内依次为净年化收益和最大回撤。双边换手是一个H10内买入加卖出金额占期初净值之比，100%表示买卖合计等于期初资产。"]
    accounts = pd.read_csv(RES/"training_accounts/account_summary.csv")
    books = accounts[accounts.series.eq("common")&accounts.cost.eq("base")]
    rows=[]
    for (pool,scope,segment), b in books.groupby(["pool","scope","segment"],sort=False):
        b=b.set_index("model")
        models=["full","breakout_curated","oversold_curated"]
        first=b.loc["full"]
        rows.append([POOLS[pool],SCOPES[scope],f"{first.start} 至 {first.end}",first.n,
            *[f"{b.at[m,'cagr']:.2%} / {b.at[m,'mdd']:.2%}" for m in models],
            " / ".join(percent(b.at[m,"turnover"]) for m in models)])
    table(lines,["池","期间","起止日期","期数","全量 · 年化 / 回撤","突破 · 年化 / 回撤","超跌 · 年化 / 回撤","换手（全量 / 突破 / 超跌）"],rows)
    lines += ["## 排序和换入股票", "",
        "此处读全部139个信号截面，包含中证800主段两次账户缺口所涉及的信号日。RankIC是每个截面评分与H10收益的秩相关，再对日期等权。D10重合为两名单共同股票数除以原席位数。毛超额用D10等权报价收益减本池当日全部有报价股票的等权收益。"]
    ranks=pd.read_csv(RES/"training_fit/ranking_summary.csv")
    seats=pd.read_csv(REVIEW/"seat_summary.csv")
    rows=[]
    for pool in POOLS:
        for scope in SCOPES:
            g=ranks[ranks.pool.eq(pool)&ranks.scope.eq(scope)].set_index("model")
            for task,title in TASKS.items():
                model=task+"_curated"
                s=seats[(seats.pool==pool)&(seats.scope==scope)&(seats.model==model)].iloc[0]
                seeds=g[g.index.str.startswith(task+"_random_")]
                rows.append([POOLS[pool],SCOPES[scope],title,
                    " / ".join(f"{x:.3f}" for x in [g.at["full","rankic"],seeds.rankic.mean(),g.at[model,"rankic"]]),
                    percent(g.at[model,"overlap"]),fmt(g.at[model,"gross_selection_bp"]),
                    f"{s.both_fillable:,}/{s.paired_seats:,}",fmt(s.equal_cash_netdiff*1e4)])
    table(lines,["池","期间","任务","RankIC（全量 / 随机 / 精选）","与全量D10重合","精选D10毛超额 bp","两端均能成交的换股对 / 全部","换入减换出 bp"],rows)
    lines += ["换股对在同一日将新入选名单与被挤出名单按各自评分顺序一一对齐。仅当双方买卖均可执行且两端报价完整时，才计算投入相同现金、承担相同费率的收益差。每对等权。这一列用于核对替补质量，实际仓位延续、现金和交易限制已纳入前述账户。","",
        "## 中证800新增成分的实际贡献","",
        "按各窗口信号日的原300成分档案，归集原300以外持股的实际权重、成交与含费损益。权重取开盘执行后，净贡献以整个账户期初净值为分母。随机一列来自各自任务的五个账户。"]
    w=pd.read_parquet(RES/"training_accounts/windows.parquet")
    w=w[w.pool.eq("CSI800")&w.series.eq("common")&w.cost.eq("base")]
    rows=[]
    for scope in SCOPES:
        g=w[w.scope.eq(scope)].groupby("model").mean(numeric_only=True)
        for task,title in TASKS.items():
            cur=g.loc[task+"_curated"]; others=g[g.index.str.startswith(task+"_random_")].mean()
            full=g.loc["full"]
            rows.append([SCOPES[scope],title,*(percent(cur[f]) for f in ["outside300_weight","outside300_turnover"]),
                *[fmt(1e4*x.outside300_net) for x in [full,others,cur]],
                fmt(1e4*(cur.outside300_net-others.outside300_net))])
    table(lines,["期间","任务","精选期初持仓","精选双边换手","全量净贡献 bp","随机净贡献 bp","精选净贡献 bp","精选减随机 bp"],rows)
    lines+=["## 月份分布","",
        "按每个独立账段的日净值计算自然月或首尾部分月份。五个随机账户分别计算月收益后取均值。中证800两个缺口两边独立记账，同一月份如有两段则分别计数。"]
    months=pd.read_csv(REVIEW/"paired_months.csv")
    rows=[]
    for (pool,scope,task),g in months.groupby(INDEX):
        lo=g.loc[g.vs_random_bp.idxmin()];hi=g.loc[g.vs_random_bp.idxmax()]
        rows.append([POOLS[pool],SCOPES[scope],TASKS[task],f"{(g.vs_random_bp>0).sum()}/{len(g)}",
            f"{lo.month}（{fmt(lo.vs_random_bp)}）",f"{hi.month}（{fmt(hi.vs_random_bp)}）"])
    table(lines,["池","期间","任务","领先随机的月段","最弱月段 bp","最强月段 bp"],rows)
    lines += ["[主报告](../TRAINING_REPORT.md) · [到账段和模型的全部年化、净值、回撤](../results/training_accounts/account_summary.csv) · [逐窗净差和换手](../results/training_review/paired_windows.parquet) · [所有目标持仓](../results/training_accounts/targets.parquet) · [实际净订单](../results/training_accounts/orders.parquet)"]
    (EP/"training/ACCOUNT_DETAILS.md").write_text("\n".join(lines)+"\n")


if __name__ == "__main__":
    main()

