"""Plot the synchronized historical accounts and D10 allocations in the test period."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as dates
import pandas as pd
from prepare import OUT

plt.rcParams.update({"font.family":"Noto Sans CJK JP","axes.spines.top":False,"axes.spines.right":False,"axes.unicode_minus":False})
nav=pd.read_parquet(OUT/"daily.parquet").query("scope=='primary'").pivot(index="date",columns="strategy",values="nav")
weights=pd.read_csv(OUT/"cycles.csv",parse_dates=["entry_date"]).query("scope=='primary' and cost=='main' and strategy=='dynamic'")
fig,(ax,bx)=plt.subplots(2,1,figsize=(10,6.4),sharex=True,gridspec_kw={"height_ratios":[2,1]},layout="constrained")
colors={"dynamic":"#0f6e70","matched":"#865117","balanced":"#544698","d10":"#777d82","dividend":"#ab8587"}
for key,label in [("d10","纯 D10"),("balanced","固定 50/50"),("matched","固定 44.85/55.15"),("dynamic","动态配仓"),("dividend","纯红利价格指数")]:
    ax.plot(nav[key],label=label,color=colors[key],lw=2 if key=="dynamic" else 1.3)
ax.set_title("相同样本外日期的组合净值",loc="left")
ax.set_ylabel("单位初始资金")
ax.legend(ncols=3,fontsize=9,frameon=False)
idx=weights.set_index("entry_date").target_d10
idx.loc[nav.index[-1]]=idx.iloc[-1]
bx.step(idx.index,idx*100,where="post",color=colors["dynamic"],label="动态 D10 仓位")
bx.axhline(weights.target_d10.mean()*100,color=colors["matched"],ls="--",label="动态仓位均值")
bx.set_ylim(0,100)
bx.set_ylabel("D10 目标仓位（%）")
bx.legend(loc="upper right",frameon=False,ncols=2,fontsize=9)
bx.xaxis.set_major_locator(dates.MonthLocator(interval=4))
bx.xaxis.set_major_formatter(dates.DateFormatter("%Y-%m"))
for axis in (ax,bx):
    axis.grid(axis="y",alpha=.2)
fig.savefig(OUT/"allocation.png",dpi=150)
