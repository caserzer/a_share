"""Build the two complete, dated eligible cross sections before selecting cases."""
from pathlib import Path
import hashlib
import json
import os

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
OUT = HERE / "results"
EP38 = next(HERE.parent.glob("38_*")) / "three_track/results"
PRIVATE = next(HERE.parent.glob("36_*")) / "private"
MARKET = Path(os.environ.get("EP39_MARKET", Path.home() / ".cache/a_share/ep38_three_track/market"))
PANEL = OUT / "panel.parquet"
KEY = ["signal_date", "instrument"]
FIELDS = ["qfq_close", "qfq_open", "qfq_high", "qfq_low", "volume",
          "open", "opening_trade_status_v2", "limits/daily"]


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def get_panel():
    return pd.read_parquet(PANEL)


def frozen_universes():
    cols = KEY + ["score", "selected", "h10"]
    narrow = pd.read_parquet(EP38 / "rankings.parquet", columns=cols + ["scope"],
                             filters=[("model", "=", "original"), ("cost", "=", "base")])
    wide = pd.read_parquet(EP38 / "wide_rankings.parquet", columns=cols,
                           filters=[("model", "=", "transfer")])
    scopes = narrow[["signal_date", "scope"]].drop_duplicates()
    wide = wide.merge(scopes, on="signal_date", validate="m:1")
    frozen = pd.concat([narrow.assign(pool="CSI300"), wide.assign(pool="CSI800")])
    assert not frozen.duplicated(["pool"] + KEY).any()
    assert frozen.groupby("pool").signal_date.nunique().eq(139).all()
    return frozen.sort_values(["pool"] + KEY).reset_index(drop=True)


def metadata(panel):
    industry = pd.read_parquet(PRIVATE / "industry.parquet")
    industry["instrument"] = industry.ts_code.str[-2:] + industry.ts_code.str[:6]
    rows = []
    for date in panel.signal_date.unique():
        day = pd.Timestamp(date).strftime("%Y%m%d")
        sub = industry[industry.in_date.le(day) & (industry.out_date.isna() | industry.out_date.gt(day))]
        group = sub.groupby("instrument")
        info = group[["l1_name", "name"]].first()
        info = info.where(group[["l1_name", "name"]].nunique().eq(1))
        rows.append(info.rename(columns={"l1_name": "industry"}).assign(signal_date=date))
    return panel.merge(pd.concat(rows).reset_index(), on=KEY, how="left", validate="m:1")


def build():
    OUT.mkdir(exist_ok=True)
    p = frozen_universes()
    close = pd.read_parquet(MARKET / "qfq_close.parquet")
    days, symbols = close.index, close.columns
    idx = days.get_indexer(p.signal_date)
    col = symbols.get_indexer(p.instrument)
    assert idx.min() >= 20 and idx.max() + 11 < len(days) and col.min() >= 0

    def read(field):
        df = pd.read_parquet(MARKET / (field + ".parquet"))
        assert df.index.equals(days) and df.columns.equals(symbols)
        return df

    def at(frame, offset=0):
        return frame.to_numpy()[idx + offset, col]

    op, high, low, volume = [read(field) for field in ("qfq_open", "qfq_high", "qfq_low", "volume")]
    p["entry_date"], p["exit_date"] = days[idx+1], days[idx+11]
    p["entry_open"], p["exit_open"], p["close"] = at(op, 1), at(op, 11), at(close)
    p["ret10"] = p.exit_open / p.entry_open - 1
    np.testing.assert_allclose(p.ret10, p.h10, atol=1e-12, rtol=0, equal_nan=True)
    p = p.drop(columns="h10")
    p["prior_high20"] = at(high.shift(1).rolling(20, min_periods=20).max())
    p["prior_low5"] = at(low.rolling(5, min_periods=5).min())
    p["breakout_pct"] = p.close / p.prior_high20 - 1
    p["breakout"] = p.close.gt(p.prior_high20).astype("boolean").mask(p.breakout_pct.isna())
    p["ret5"] = p.close / at(close, -5) - 1
    p["vol20"] = at(close.pct_change(fill_method=None).rolling(20).std(ddof=0))
    p["volume_rel20"] = at(volume / volume.rolling(20).mean())
    p["entry_gap"] = p.entry_open / p.close - 1
    context = p.groupby(["pool", "signal_date"])
    p["score_pct"] = context.score.rank(pct=True)
    p["ret5_pct"] = context.ret5.rank(pct=True)
    p["oversold"] = (p.ret5.lt(0) & p.ret5_pct.le(.1)).astype("boolean").mask(p.ret5.isna())
    p["pool_ret10"] = context.ret10.transform("mean")
    closes = np.column_stack([at(close, day) for day in range(1, 11)])
    lows = np.column_stack([at(low, day) for day in range(1, 11)])
    n = (closes >= p.prior_high20.to_numpy()[:, None]).sum(axis=1)
    p["above_high_days"] = np.where(np.isfinite(closes).all(axis=1) & p.prior_high20.notna(), n, np.nan)
    p["hold_low10"] = lows.min(axis=1)
    p["mae10"] = p.hold_low10 / p.entry_open - 1
    p["relative_ret10"] = p.ret10 - p.pool_ret10
    p["ret10_rank_pct"] = context.ret10.rank(pct=True)

    raw, status = read("open"), read("opening_trade_status_v2")
    limits = pd.read_parquet(MARKET / "limits/daily.parquet")
    limits["instrument"] = limits.ts_code.str[-2:] + limits.ts_code.str[:6]
    limits["date"] = pd.to_datetime(limits.trade_date)
    quotes = limits.set_index(["date", "instrument"])
    assert quotes.index.is_unique
    for offset, name, side in [(1, "entry_buy", "buy"), (11, "exit_sell", "sell")]:
        board = quotes.reindex(pd.MultiIndex.from_arrays([days[idx+offset], p.instrument]))
        up, down = board.up_limit.to_numpy(float), board.down_limit.to_numpy(float)
        px, adj, state = at(raw, offset), at(op, offset), at(status, offset)
        known = (np.isfinite(up) & np.isfinite(down) & (up > down) & (px > 0) &
                 (adj > 0) & np.isfinite(px) & np.isfinite(adj) & (state == 1))
        executable = px < up-1e-6 if side == "buy" else px > down+1e-6
        gate = pd.array(executable, dtype="boolean")
        gate[~known] = pd.NA
        gate[state == 0] = False
        p[name] = gate

    membership = pd.read_parquet(PRIVATE/"daily_members.parquet").reindex(index=days, columns=symbols, fill_value=False)
    p["in_legacy300"] = at(membership)
    p = metadata(p)
    p[["industry","name"]] = p[["industry","name"]].fillna("未知")
    pilot = p[p.pool.eq("CSI300")]
    assert (len(pilot), pilot.breakout.sum(), pilot.oversold.sum()) == (40756, 2076, 3987)
    assert (pilot.loc[pilot.breakout, "selected"].sum(), pilot.loc[pilot.oversold, "selected"].sum()) == (268, 413)
    p.to_parquet(PANEL, index=False)
    paths = [MARKET / (f+".parquet") for f in FIELDS]
    paths += [PRIVATE/"industry.parquet", PRIVATE/"daily_members.parquet",
              EP38/"rankings.parquet", EP38/"wide_rankings.parquet", EP38/"verification.json"]
    hashes = {str(path): sha(path) for path in paths}
    expected = json.loads((EP38/"verification.json").read_text())["output_sha256"]
    for name in ["rankings.parquet", "wide_rankings.parquet"]:
        assert hashes[str(EP38/name)] == expected[name]
    (OUT/"panel_receipt.json").write_text(json.dumps(dict(inputs=hashes, panel_sha256=sha(PANEL),
        rows=len(p), unique_stock_dates=len(p.drop_duplicates(KEY)), start=str(p.signal_date.min().date()),
        end=str(p.exit_date.max().date())), indent=2)+"\n")


if __name__ == "__main__":
    build()
