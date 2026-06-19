#!/usr/bin/env python
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


EXPERIMENT_DIR = Path(__file__).resolve().parents[1]
TOPIC_ROOT = Path(__file__).resolve().parents[4]
REPO_ROOT = Path(__file__).resolve().parents[6]

DEFAULT_PRICE_DIR = TOPIC_ROOT / "data" / "raw" / "akshare" / "day" / "qfq"
DEFAULT_PANEL_PATH = (
    TOPIC_ROOT
    / "experiments"
    / "pending"
    / "08_risk_on_transition_recall_exploration_v0"
    / "outputs"
    / "local_cache"
    / "cross_section_feature_panel.parquet"
)
DEFAULT_EVENT_PATH = (
    EXPERIMENT_DIR
    / "outputs"
    / "publishable"
    / "tables"
    / "12A4_state_change_meta_label_filter_feasibility"
    / "meta_label_event_universe.csv.gz"
)
DEFAULT_EPISODE_PATH = (
    EXPERIMENT_DIR
    / "outputs"
    / "publishable"
    / "tables"
    / "12A0_12A1_winner_registry_lineage_and_r_core_backbone_demotion_audit"
    / "episode_target_registry_06_risk_on_428.csv"
)
DEFAULT_OUTPUT_DIR = (
    EXPERIMENT_DIR
    / "outputs"
    / "publishable"
    / "figures"
    / "symbol_event_timeline"
)

SOURCE_STYLE = {
    "C0_state_change": {
        "label": "C0 state-change event",
        "color": "#d62728",
        "marker": "^",
        "offset": 1.025,
        "size": 34,
        "zorder": 5,
    },
    "R_core": {
        "label": "R-core event",
        "color": "#1f77b4",
        "marker": "v",
        "offset": 0.975,
        "size": 28,
        "zorder": 4,
    },
}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Plot one stock's full qfq close trend, risk-on background, "
            "and 12A4 C0/R-core event markers."
        )
    )
    parser.add_argument("symbol", help="A-share symbol, for example 600019, SH600019, or sh600019.")
    parser.add_argument("--price-dir", default=str(DEFAULT_PRICE_DIR), help="qfq daily CSV directory.")
    parser.add_argument("--panel", default=str(DEFAULT_PANEL_PATH), help="08 cross-section feature panel parquet.")
    parser.add_argument("--events", default=str(DEFAULT_EVENT_PATH), help="12A4 meta_label_event_universe CSV/CSV.GZ.")
    parser.add_argument("--episodes", default=str(DEFAULT_EPISODE_PATH), help="06 risk_on big-winner episode registry CSV.")
    parser.add_argument("--output", default="", help="Output PNG path. Defaults to publishable figures directory.")
    parser.add_argument("--dpi", type=int, default=180)
    parser.add_argument("--width", type=float, default=18.0)
    parser.add_argument("--height", type=float, default=8.0)
    parser.add_argument("--title", default="")
    return parser.parse_args(argv)


def topic_path(value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    text = str(path)
    if text.startswith("topics/"):
        return REPO_ROOT / path
    if text.startswith(("data/", "experiments/")):
        return TOPIC_ROOT / path
    if text.startswith(("outputs/", "configs/", "src/", "tests/")):
        return EXPERIMENT_DIR / path
    return EXPERIMENT_DIR / path


def normalize_symbol(symbol: str) -> str:
    value = str(symbol).strip().upper()
    value = value.replace(".", "").replace("-", "").replace("_", "")
    if value.startswith(("SH", "SZ", "BJ")) and len(value) >= 8:
        return value[:2] + value[2:8]
    digits = "".join(ch for ch in value if ch.isdigit())
    if len(digits) != 6:
        raise ValueError(f"Cannot normalize symbol: {symbol!r}")
    if digits.startswith(("6", "9")):
        prefix = "SH"
    elif digits.startswith(("0", "2", "3")):
        prefix = "SZ"
    elif digits.startswith(("4", "8")):
        prefix = "BJ"
    else:
        prefix = "SH"
    return prefix + digits


def candidate_price_paths(price_dir: Path, instrument: str) -> list[Path]:
    raw = instrument[2:]
    return [
        price_dir / f"{instrument}.csv",
        price_dir / f"{instrument.lower()}.csv",
        price_dir / f"{raw}.csv",
        price_dir / f"{raw.lower()}.csv",
    ]


def find_price_path(price_dir: Path, instrument: str) -> Path:
    for path in candidate_price_paths(price_dir, instrument):
        if path.exists():
            return path
    matches = sorted(price_dir.glob(f"*{instrument[2:]}*.csv"))
    if matches:
        return matches[0]
    raise FileNotFoundError(f"No qfq daily CSV found for {instrument} under {price_dir}")


def read_price(price_dir: Path, instrument: str) -> pd.DataFrame:
    path = find_price_path(price_dir, instrument)
    frame = pd.read_csv(path, low_memory=False)
    required = {"date", "close"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"{path} missing required columns: {sorted(missing)}")
    out = frame.copy()
    out["date"] = pd.to_datetime(out["date"], errors="coerce")
    out["close"] = pd.to_numeric(out["close"], errors="coerce")
    out = out.dropna(subset=["date", "close"]).sort_values("date").drop_duplicates("date", keep="last")
    if out.empty:
        raise ValueError(f"{path} has no valid date/close rows")
    return out[["date", "close"]].reset_index(drop=True)


def read_regime_calendar(panel_path: Path) -> pd.DataFrame:
    columns = ["date", "instrument", "market_regime_bucket"]
    frame = pd.read_parquet(panel_path, columns=columns)
    out = frame.copy()
    out["date"] = pd.to_datetime(out["date"], errors="coerce")
    out = out.dropna(subset=["date", "market_regime_bucket"])
    per_date_regime_n = out.groupby("date")["market_regime_bucket"].nunique(dropna=True)
    conflict_dates = per_date_regime_n.loc[per_date_regime_n.gt(1)]
    if not conflict_dates.empty:
        sample_dates = [str(x.date()) for x in conflict_dates.index[:5]]
        raise ValueError(f"Market regime is not unique by date; sample conflict dates: {sample_dates}")
    out = out.sort_values("date").drop_duplicates("date", keep="last")
    return out[["date", "market_regime_bucket"]].reset_index(drop=True)


def read_panel(panel_path: Path, instrument: str) -> pd.DataFrame:
    return read_regime_calendar(panel_path)


def read_events(event_path: Path, instrument: str) -> pd.DataFrame:
    frame = pd.read_csv(event_path, low_memory=False)
    required = {"instrument", "event_t0_date", "source_arm_id"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"{event_path} missing required columns: {sorted(missing)}")
    out = frame.loc[frame["instrument"].astype(str).eq(instrument)].copy()
    out = out.loc[out["source_arm_id"].astype(str).isin(SOURCE_STYLE)].copy()
    out["event_t0_date"] = pd.to_datetime(out["event_t0_date"], errors="coerce")
    out = out.dropna(subset=["event_t0_date"])
    return out.sort_values(["event_t0_date", "source_arm_id"]).reset_index(drop=True)


def read_big_winner_episodes(episode_path: Path, instrument: str) -> pd.DataFrame:
    frame = pd.read_csv(episode_path, low_memory=False)
    required = {"instrument", "episode_low_date", "episode_high_date"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"{episode_path} missing required columns: {sorted(missing)}")
    out = frame.loc[frame["instrument"].astype(str).eq(instrument)].copy()
    out["episode_low_date"] = pd.to_datetime(out["episode_low_date"], errors="coerce")
    out["episode_high_date"] = pd.to_datetime(out["episode_high_date"], errors="coerce")
    out = out.dropna(subset=["episode_low_date", "episode_high_date"])
    out = out.loc[out["episode_high_date"].ge(out["episode_low_date"])].copy()
    return out.sort_values(["episode_low_date", "episode_high_date"]).reset_index(drop=True)


def risk_on_segments(panel: pd.DataFrame, price_min_date: pd.Timestamp, price_max_date: pd.Timestamp) -> list[tuple[pd.Timestamp, pd.Timestamp]]:
    if panel.empty:
        return []
    frame = panel.loc[panel["date"].between(price_min_date, price_max_date)].copy()
    if frame.empty:
        return []
    frame = frame.sort_values("date").reset_index(drop=True)
    frame["_risk_on"] = frame["market_regime_bucket"].astype(str).eq("risk_on")
    group_id = frame["_risk_on"].ne(frame["_risk_on"].shift(fill_value=False)).cumsum()
    segments = []
    for _, group in frame.groupby(group_id, sort=True):
        if not bool(group["_risk_on"].iloc[0]):
            continue
        start = group["date"].iloc[0]
        end = group["date"].iloc[-1] + pd.Timedelta(days=1)
        segments.append((start, end))
    return segments


def big_winner_price_segments(episodes: pd.DataFrame, price: pd.DataFrame) -> list[pd.DataFrame]:
    segments: list[pd.DataFrame] = []
    if episodes.empty:
        return segments
    for row in episodes.itertuples(index=False):
        start = getattr(row, "episode_low_date")
        end = getattr(row, "episode_high_date")
        segment = price.loc[price["date"].between(start, end)].copy()
        if not segment.empty:
            segments.append(segment)
    return segments


def event_points(events: pd.DataFrame, price: pd.DataFrame) -> pd.DataFrame:
    if events.empty:
        return events.assign(close=pd.Series(dtype=float))
    price_lookup = price.set_index("date")["close"]
    out = events.copy()
    out["close"] = out["event_t0_date"].map(price_lookup)
    return out.dropna(subset=["close"]).reset_index(drop=True)


def summarize_events(events: pd.DataFrame) -> dict[str, int]:
    counts = events["source_arm_id"].value_counts().to_dict() if not events.empty else {}
    return {
        "c0_event_n": int(counts.get("C0_state_change", 0)),
        "r_core_event_n": int(counts.get("R_core", 0)),
        "total_event_n": int(sum(counts.values())),
    }


def plot_symbol(
    instrument: str,
    price: pd.DataFrame,
    panel: pd.DataFrame,
    episodes: pd.DataFrame,
    events: pd.DataFrame,
    output_path: Path,
    *,
    dpi: int,
    width: float,
    height: float,
    title: str = "",
) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(width, height))

    segments = risk_on_segments(panel, price["date"].min(), price["date"].max())
    risk_label_added = False
    for start, end in segments:
        ax.axvspan(
            start,
            end,
            color="#8fd19e",
            alpha=0.20,
            linewidth=0,
            label="risk_on regime" if not risk_label_added else None,
            zorder=0,
        )
        risk_label_added = True

    ax.plot(price["date"], price["close"], color="#222222", linewidth=1.25, label="qfq close", zorder=2)

    winner_segments = big_winner_price_segments(episodes, price)
    winner_label_added = False
    for segment in winner_segments:
        ax.plot(
            segment["date"],
            segment["close"],
            color="#B8860B",
            linewidth=3.0,
            alpha=0.95,
            solid_capstyle="round",
            label=f"identified big winner low-to-high (n={len(winner_segments)})" if not winner_label_added else None,
            zorder=3,
        )
        winner_label_added = True

    points = event_points(events, price)
    for source_arm_id, style in SOURCE_STYLE.items():
        sub = points.loc[points["source_arm_id"].astype(str).eq(source_arm_id)]
        if sub.empty:
            continue
        ax.scatter(
            sub["event_t0_date"],
            sub["close"] * float(style["offset"]),
            s=float(style["size"]),
            marker=str(style["marker"]),
            color=str(style["color"]),
            edgecolors="white",
            linewidths=0.45,
            alpha=0.88,
            label=f"{style['label']} (n={len(sub)})",
            zorder=int(style["zorder"]),
        )

    ax.set_title(title or f"{instrument} qfq close with big winners, risk_on regime, and 12A4 events")
    ax.set_xlabel("date")
    ax.set_ylabel("qfq close")
    ax.grid(True, axis="y", color="#d0d0d0", linewidth=0.5, alpha=0.7)
    ax.grid(True, axis="x", color="#e8e8e8", linewidth=0.35, alpha=0.35)
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.xaxis.set_minor_locator(mdates.MonthLocator(interval=3))
    ax.margins(x=0.01, y=0.08)
    ax.legend(loc="upper left", frameon=True, framealpha=0.92)
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(output_path, dpi=dpi)
    plt.close(fig)
    return output_path


def default_output_path(instrument: str) -> Path:
    return DEFAULT_OUTPUT_DIR / f"{instrument}_qfq_close_risk_on_c0_r_core_events.png"


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    instrument = normalize_symbol(args.symbol)
    price_dir = topic_path(args.price_dir)
    panel_path = topic_path(args.panel)
    event_path = topic_path(args.events)
    episode_path = topic_path(args.episodes)
    output_path = topic_path(args.output) if args.output else default_output_path(instrument)

    price = read_price(price_dir, instrument)
    regime_calendar = read_regime_calendar(panel_path)
    episodes = read_big_winner_episodes(episode_path, instrument)
    events = read_events(event_path, instrument)
    plotted_events = event_points(events, price)
    summary = summarize_events(plotted_events)
    plot_symbol(
        instrument,
        price,
        regime_calendar,
        episodes,
        events,
        output_path,
        dpi=args.dpi,
        width=args.width,
        height=args.height,
        title=args.title,
    )

    print(f"instrument={instrument}")
    print(f"price_rows={len(price)} date_range={price['date'].min().date()}..{price['date'].max().date()}")
    print(
        f"regime_calendar_rows={len(regime_calendar)} "
        f"risk_on_segments={len(risk_on_segments(regime_calendar, price['date'].min(), price['date'].max()))}"
    )
    print(f"big_winner_episode_n={len(episodes)}")
    print(f"c0_event_n={summary['c0_event_n']} r_core_event_n={summary['r_core_event_n']} total_event_n={summary['total_event_n']}")
    print(f"output={output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
