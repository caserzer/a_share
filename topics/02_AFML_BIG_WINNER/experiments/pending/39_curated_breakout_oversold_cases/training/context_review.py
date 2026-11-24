"""Describe market-conditioned returns and signal-day D10 industry reallocations."""

from pathlib import Path
import hashlib
import json
import numpy as np
import pandas as pd

EP39 = Path(__file__).resolve().parents[1]
RES = EP39 / "results"
OUT = RES / "training_context"
MARKET = next(EP39.parent.glob("36_*")) / "private/market.parquet"
WINDOWS = RES / "training_review/paired_windows.parquet"
TARGETS = RES / "training_accounts/targets.parquet"
PANEL = RES / "panel.parquet"
DAY = ["pool", "scope", "signal_date"]
SEEDS = (39, 139, 239, 339, 439)
TASK = {"breakout": "突破", "oversold": "超跌"}
POOL = {"CSI300": "沪深300", "CSI800": "中证800"}
SCOPE = {"primary": "主段", "later": "后段"}


def rates_by_state(w):
    close = pd.read_parquet(MARKET, columns=["close"]).close
    momentum = (close / close.shift(20) - 1).rename("csi300_mom20")
    w = w.merge(
        momentum.rename_axis("signal_date"),
        on="signal_date",
        how="left",
        validate="m:1",
    )
    assert w.csi300_mom20.notna().all()
    w["state"] = np.where(w.csi300_mom20.gt(0), "上涨", "持平或下跌")
    g = w.groupby(["pool", "scope", "task", "reference", "state"])
    summary = g.agg(
        n=("signal_date", "size"),
        net_bp=("net_bp", "mean"),
        gross_bp=("gross_bp", "mean"),
        fee_bp=("fee_bp", "mean"),
        turnover_diff=("turnover", "mean"),
        wins=("net_bp", lambda x: int(x.gt(0).sum())),
    ).reset_index()
    return w, summary


def industry_review(dates):
    targets = pd.read_parquet(
        TARGETS, columns=DAY + ["model", "instrument", "weight"]
    ).merge(dates, on=DAY, validate="m:1")
    sectors = pd.read_parquet(PANEL, columns=DAY + ["instrument", "industry"])
    targets = targets.merge(
        sectors, on=DAY + ["instrument"], how="left", validate="m:1", indicator=True
    )
    assert targets._merge.eq("both").all()
    targets["industry"] = targets.industry.fillna("未知")
    base_keys = DAY + ["model"]
    by_sector = (
        targets.groupby(base_keys + ["industry"]).weight.sum().unstack(fill_value=0)
    )
    assert np.allclose(by_sector.sum(axis=1), 1)
    weights = by_sector.to_numpy()
    counts = by_sector.gt(0).sum(axis=1)
    unknown = by_sector.get("未知", pd.Series(0.0, index=by_sector.index))
    head = pd.DataFrame(
        dict(
            top3_weight=np.sort(weights, axis=1)[:, -3:].sum(1),
            hhi=np.square(weights).sum(1),
            industry_count=counts,
            unknown_weight=unknown,
        ),
        index=by_sector.index,
    ).reset_index()
    member = targets.pivot(
        index=DAY + ["industry", "instrument"], columns="model", values="weight"
    ).fillna(0)
    concentration = []
    shifts = []
    for task in TASK:
        curated = task + "_curated"
        random = [task + "_random_" + str(seed) for seed in SEEDS]
        for reference, comparison in [("random_mean", random), ("full", ["full"])]:
            # Concentration is calculated separately in each seed portfolio before averaging.
            arm = head[head.model == curated].drop(columns="model").set_index(DAY)
            ref = (
                head[head.model.isin(comparison)]
                .drop(columns="model")
                .groupby(DAY)
                .mean()
            )
            panel = arm.join(ref, lsuffix="_curated", rsuffix="_ref", validate="1:1")
            concentration.append(
                panel.reset_index().assign(task=task, reference=reference)
            )
            adds = []
            drops = []
            for model in comparison:
                delta = member[curated] - member[model]
                # All models take the same number of equal-weight slots within a date.
                n = int(
                    (
                        (member[curated] > 0)
                        & (member[model] > 0)
                        & (abs(delta) > 1e-12)
                    ).sum()
                )
                assert n == 0
                adds.append(delta.clip(lower=0))
                drops.append((-delta).clip(lower=0))
            change = pd.DataFrame(
                dict(
                    entered=pd.concat(adds, axis=1).mean(axis=1),
                    displaced=pd.concat(drops, axis=1).mean(axis=1),
                )
            )
            sector = change.groupby(DAY + ["industry"]).sum()
            industry_set = targets.industry.unique()
            # Include zero weights on dates with no holdings in a particular industry.
            universe = dates.merge(
                pd.DataFrame({"industry": industry_set}), how="cross"
            )
            sector = sector.reindex(
                pd.MultiIndex.from_frame(universe), fill_value=0.0
            ).reset_index()
            sector["delta"] = sector.entered - sector.displaced
            assert sector.groupby(DAY).delta.sum().abs().max() < 1e-10
            shifts.append(sector.assign(task=task, reference=reference))
    conc = pd.concat(concentration, ignore_index=True)
    shift = pd.concat(shifts, ignore_index=True)
    groups = ["pool", "scope", "task", "reference"]
    av_conc = conc.drop(columns="signal_date").groupby(groups).mean().reset_index()
    av_shift = (
        shift.drop(columns="signal_date")
        .groupby(groups + ["industry"])
        .mean()
        .reset_index()
    )
    return conc, shift, av_conc, av_shift


def report(state, conc, shift):
    lines = [
        "# 市场环境和行业持仓复核",
        "",
        "本页只读共同标准费账户及当时的D10目标。沪深300主段100期、后段39期，中证800主段98期、后段39期。五个随机种子各自成账，每个窗口先平均五个账户收益，再与精选账户同日比较。",
        "",
        "## 同一模型在不同市场环境下的净收益差",
        "",
        "信号收盘时，用当日沪深300价格指数收盘相对20个交易日前收盘的涨跌判定市场方向。同一个信号日的两个部署池使用同一市场指标。正值为上涨，零值和负值归在另一组。数值为每个H10整组合在实际成交和标准费后的算术平均差，按日期等权。",
        "",
        "| 池 | 区间 | 任务 | 上涨期数 | 上涨时精选减随机，bp | 持平或下跌期数 | 持平或下跌时精选减随机，bp |",
        "|---|---|---|---:|---:|---:|---:|",
    ]
    by = state[state.reference.eq("random_mean")]
    for (pool, scope, task), g in by.groupby(["pool", "scope", "task"]):
        up, down = (g[g.state == s].iloc[0] for s in ("上涨", "持平或下跌"))
        lines.append(
            f"| {POOL[pool]} | {SCOPE[scope]} | {TASK[task]} | {up.n} | {up.net_bp:+.2f} | {down.n} | {down.net_bp:+.2f} |"
        )
    lines += [
        "",
        "市场方向只是信号日背景。分组后样本量更少，且上涨与下跌日期并非随机分派。以上差值用来检查效果是否由某个市场阶段集中贡献。两个池有重叠，不把同一市场日视作两次独立验证。[逐期市场读数](../results/training_context/market_windows.csv) · [含全量对照的分组读数](../results/training_context/market_state_summary.csv)",
        "",
        "## 精选模型把哪些行业推入前10%",
        "",
        "行业按历史面板的信号日申万一级分类。先按当日名单的等权目标资金计算每个账户前三大行业合计，再对日期等权。随机列先算各账户各自的前三大行业，再平均五个结果。“进入”和“挤出”指同一天精选名单相对随机名单的区别，同一个行业可能同时有不同个股进入和挤出。表内列出平均净权重变化最大、最小的行业，括号为该行业进入减挤出的百分点。",
        "",
        "| 池 | 区间 | 任务 | 前三行业合计，精选 / 随机 | 权重净增最多 | 权重净减最多 |",
        "|---|---|---|---:|---|---|",
    ]
    cb = conc[conc.reference.eq("random_mean")]
    for r in cb.itertuples():
        g = shift[
            (shift.pool == r.pool)
            & (shift.scope == r.scope)
            & (shift.task == r.task)
            & (shift.reference == r.reference)
        ]
        hi = g.loc[g.delta.idxmax()]
        lo = g.loc[g.delta.idxmin()]
        lines.append(
            f"| {POOL[r.pool]} | {SCOPE[r.scope]} | {TASK[r.task]} | {r.top3_weight_curated:.1%} / {r.top3_weight_ref:.1%} | {hi.industry}（{hi.delta * 100:+.2f}） | {lo.industry}（{lo.delta * 100:+.2f}） |"
        )
    covmin = 1 - conc[["unknown_weight_curated", "unknown_weight_ref"]].to_numpy().max()
    lines += [
        "",
        f"未知行业单列并计入总目标资金与集中度分母。按池、区间、任务和参照组计算，已成功分类的平均目标资金占比最低为{covmin:.3%}。未归类的平均资金占比最高为{(1 - covmin):.3%}。账户成交限制和个股走势也会改变实际持仓及收益，行业权重差不能证明行业造成了收益差。",
        "",
        "[逐期目标集中度、HHI与未知比例](../results/training_context/industry_concentration.parquet) · [逐期行业进入、挤出和净权重](../results/training_context/industry_changes.parquet) · [分段行业权重调整](../results/training_context/industry_changes_summary.csv) · [分段集中度](../results/training_context/industry_concentration_summary.csv)",
        "",
    ]
    (EP39 / "training/CONTEXT_RESULTS.md").write_text("\n".join(lines))


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    w = pd.read_parquet(
        WINDOWS,
        filters=[("cost", "=", "base"), ("reference", "in", ["full", "random_mean"])],
    )
    assert not w.duplicated(DAY + ["task", "reference"]).any()
    dates = w[DAY].drop_duplicates()
    assert w.groupby(DAY).size().eq(4).all()
    wm, sm = rates_by_state(w)
    conc, shift, ac, ashift = industry_review(dates)
    wm.to_csv(OUT / "market_windows.csv", index=False)
    sm.to_csv(OUT / "market_state_summary.csv", index=False)
    conc.to_parquet(OUT / "industry_concentration.parquet", index=False)
    shift.to_parquet(OUT / "industry_changes.parquet", index=False)
    ac.to_csv(OUT / "industry_concentration_summary.csv", index=False)
    ashift.to_csv(OUT / "industry_changes_summary.csv", index=False)
    report(sm, ac, ashift)

    def sha(path):
        with path.open("rb") as stream:
            return hashlib.file_digest(stream, "sha256").hexdigest()

    files = [
        MARKET,
        WINDOWS,
        TARGETS,
        PANEL,
        Path(__file__),
        EP39 / "training/CONTEXT_RESULTS.md",
    ]
    files.extend(p for p in OUT.iterdir() if p.name != "receipt.json")
    (OUT / "receipt.json").write_text(
        json.dumps({str(p): sha(p) for p in sorted(files)}, indent=2) + "\n"
    )


if __name__ == "__main__":
    main()
