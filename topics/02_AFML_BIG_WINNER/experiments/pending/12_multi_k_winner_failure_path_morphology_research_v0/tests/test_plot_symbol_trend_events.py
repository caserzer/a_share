from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pandas as pd


EXPERIMENT_DIR = Path(__file__).resolve().parents[1]
RUNNER_PATH = EXPERIMENT_DIR / "src" / "plot_symbol_trend_events.py"


def load_tool():
    spec = importlib.util.spec_from_file_location("plot_symbol_trend_events", RUNNER_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_normalize_symbol_accepts_plain_and_prefixed_a_share_symbols():
    tool = load_tool()

    assert tool.normalize_symbol("600019") == "SH600019"
    assert tool.normalize_symbol("sh600019") == "SH600019"
    assert tool.normalize_symbol("000001") == "SZ000001"
    assert tool.normalize_symbol("300750") == "SZ300750"


def test_risk_on_segments_split_on_non_risk_on_rows():
    tool = load_tool()
    panel = pd.DataFrame(
        {
            "date": pd.to_datetime(["2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05"]),
            "market_regime_bucket": ["risk_on", "transition", "risk_on", "risk_on"],
        }
    )

    segments = tool.risk_on_segments(panel, pd.Timestamp("2024-01-01"), pd.Timestamp("2024-01-10"))

    assert segments == [
        (pd.Timestamp("2024-01-02"), pd.Timestamp("2024-01-03")),
        (pd.Timestamp("2024-01-04"), pd.Timestamp("2024-01-06")),
    ]


def test_event_points_maps_event_dates_to_qfq_close():
    tool = load_tool()
    price = pd.DataFrame(
        {
            "date": pd.to_datetime(["2024-01-02", "2024-01-03"]),
            "close": [10.0, 11.0],
        }
    )
    events = pd.DataFrame(
        {
            "event_t0_date": pd.to_datetime(["2024-01-02", "2024-01-04"]),
            "source_arm_id": ["C0_state_change", "R_core"],
        }
    )

    points = tool.event_points(events, price)

    assert len(points) == 1
    assert float(points.iloc[0]["close"]) == 10.0


def test_big_winner_price_segments_use_low_to_high_window():
    tool = load_tool()
    price = pd.DataFrame(
        {
            "date": pd.to_datetime(["2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05"]),
            "close": [10.0, 10.5, 11.0, 10.8],
        }
    )
    episodes = pd.DataFrame(
        {
            "episode_low_date": pd.to_datetime(["2024-01-03"]),
            "episode_high_date": pd.to_datetime(["2024-01-05"]),
        }
    )

    segments = tool.big_winner_price_segments(episodes, price)

    assert len(segments) == 1
    assert segments[0]["date"].tolist() == list(pd.to_datetime(["2024-01-03", "2024-01-04", "2024-01-05"]))
    assert segments[0]["close"].tolist() == [10.5, 11.0, 10.8]


def test_plot_symbol_writes_png(tmp_path):
    tool = load_tool()
    price = pd.DataFrame(
        {
            "date": pd.date_range("2024-01-02", periods=5, freq="B"),
            "close": [10.0, 10.5, 10.2, 10.9, 11.1],
        }
    )
    panel = pd.DataFrame(
        {
            "date": price["date"],
            "market_regime_bucket": ["risk_on", "risk_on", "transition", "risk_on", "risk_on"],
        }
    )
    events = pd.DataFrame(
        {
            "event_t0_date": [price["date"].iloc[1], price["date"].iloc[3]],
            "source_arm_id": ["C0_state_change", "R_core"],
        }
    )
    episodes = pd.DataFrame(
        {
            "episode_low_date": [price["date"].iloc[1]],
            "episode_high_date": [price["date"].iloc[4]],
        }
    )
    output = tmp_path / "plot.png"

    path = tool.plot_symbol("SH600019", price, panel, episodes, events, output, dpi=90, width=6.0, height=3.0)

    assert path == output
    assert output.exists()
    assert output.stat().st_size > 0
