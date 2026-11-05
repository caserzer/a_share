import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


@pytest.fixture
def bars():
    days = pd.bdate_range("2017-01-03", periods=550)
    rng = np.random.default_rng(31)
    close = 10*np.exp(np.cumsum(rng.normal(0.001, 0.01, len(days))))
    f = pd.DataFrame(dict(date=days, open=close*0.999, high=close*1.01, low=close*0.99,
                          close=close, volume=rng.uniform(1e5, 2e5, len(days)), money=close*1e5,
                          turnover_rate=rng.uniform(0.01, 0.05, len(days)), vendor_trade_status="1",
                          vendor_is_st="0", qfq_divisor=1.0, factor_chain_id="same",
                          factor_source_sha256="source", security_id="S", instrument="SH600000"))
    for col in ["open", "high", "low", "close"]:
        f["qfq_"+col] = f[col]
    for col in ["open", "high", "low", "close", "volume", "money", "turnover_rate"]:
        f[col+"_conflict"] = False
    return f
