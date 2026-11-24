"""Render the two CSI300 pairs discussed in the casebooks from archived daily bars."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.lines import Line2D
import numpy as np
import pandas as pd

from common import MARKET, OUT, get_panel


def main():
    chart_font = font_manager.findfont("Noto Sans CJK JP", fallback_to_default=False)
    font = font_manager.FontProperties(fname=chart_font).get_name()
    plt.rcParams.update({"font.family": font, "axes.unicode_minus": False, "font.size": 10})
    bars = {field: pd.read_parquet(MARKET/f"qfq_{field}.parquet")
            for field in ["close", "open", "low", "high"]}
    narrow = get_panel().query("pool=='CSI300'").set_index(["signal_date", "instrument"])
    panels = [
        ("2023-12-27", "SZ000895", "突破延续", "prior_high20"),
        ("2023-12-27", "SH600025", "突破失败", "prior_high20"),
        ("2025-09-05", "SH600760", "止跌反弹", "prior_low5"),
        ("2025-09-05", "SZ000768", "持续下跌", "prior_low5"),
    ]
    fig, axes = plt.subplots(2, 2, figsize=(11, 6.8), sharey="row", sharex=True)
    for ax, (date, stock, label, level) in zip(axes.flat, panels):
        row = narrow.loc[(pd.Timestamp(date), stock)]
        i = bars["close"].index.get_loc(date)
        x = np.arange(-5, 11)
        ref = row[level]
        path = {k: 100 * mat[stock].iloc[i+x].to_numpy()/ref for k, mat in bars.items()}
        np.testing.assert_allclose(bars["open"].iloc[i+11][stock]/bars["open"].iloc[i+1][stock]-1,row.ret10)
        ax.axvspan(0.5, 11.4, color="#eff6f5", zorder=0)
        ax.axhline(100, color="#925836", linestyle="--", lw=1.1)
        ax.vlines(x, path["low"], path["high"], color="#9cabb1", linewidth=2)
        ax.plot(x, path["close"], color="#224c64", marker="o", ms=3.5)
        ax.scatter([1, 11], [100*row.entry_open/ref, 100*row.exit_open/ref], s=43,
                   marker="D", color="#c57728", edgecolors="white", linewidths=.6, zorder=4)
        ax.set_title(f"{label}   {row['name']} {stock}    {row.ret10:+.2%}", loc="left", fontsize=11)
        ax.set_xlim(-5.6,11.6)
        ax.grid(axis="y", color="#c9d2d5", alpha=.5, linewidth=.6)
        ax.spines[["right","top"]].set_visible(False)
        ax.set_xticks([-5,0,1,5,10,11], ["−5","信号","1","5","10","11"])
    axes[0,0].set_ylabel("此前20日高点 = 100")
    axes[1,0].set_ylabel("含信号日的5日低点 = 100")
    for ax in axes[1]: ax.set_xlabel("相对信号日的交易日")
    fig.suptitle("相似的信号，不同的十日走势", x=.09, y=.99, ha="left", fontsize=18)
    fig.text(.09,.928,"上排突破信号 2023-12-27    ·    下排超跌信号 2025-09-05    ·    四只股票均在当日沪深300原模型目标名单内",color="#3d4e55")
    handles=[Line2D([],[],color="#224c64",marker="o",ms=4,label="复权收盘价"),
             Line2D([],[],color="#9cabb1",marker="|",ms=10,ls="",label="日内高低区间"),
             Line2D([],[],color="#925836",ls="--",label="信号参考价位"),
             Line2D([],[],color="#c57728",marker="D",ls="",label="入场／退出开盘报价")]
    fig.legend(handles=handles,loc="lower center",ncol=4,frameon=False,bbox_to_anchor=(.5,.006))
    fig.subplots_adjust(left=.09,right=.975,top=.85,bottom=.14,wspace=.1,hspace=.34)
    fig.savefig(OUT/"example_paths.png",dpi=165,bbox_inches="tight")
    plt.close(fig)


if __name__=="__main__":
    main()
