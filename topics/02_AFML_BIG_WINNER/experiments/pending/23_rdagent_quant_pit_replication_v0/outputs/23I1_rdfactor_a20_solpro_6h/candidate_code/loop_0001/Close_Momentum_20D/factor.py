from pathlib import Path

import numpy as np
import pandas as pd

FACTOR_NAME = "Close_Momentum_20D"
LOOKBACK = 20


def calculate_close_momentum_20d() -> pd.DataFrame:
    data_path = Path(__file__).resolve().parent / "daily_pv.h5"
    output_path = Path(__file__).resolve().parent / "result.h5"

    data = pd.read_hdf(data_path, key="data").sort_index()
    close = data["$close"].astype("float64")
    lagged_close = close.groupby(level="instrument", sort=False).shift(LOOKBACK)

    valid = (
        np.isfinite(close)
        & np.isfinite(lagged_close)
        & (close > 0)
        & (lagged_close > 0)
    )
    momentum = close.div(lagged_close).sub(1.0).where(valid)

    result = momentum.to_frame(name=FACTOR_NAME)
    result.index = result.index.set_names(["datetime", "instrument"])
    result.to_hdf(output_path, key="data", mode="w")
    return result


if __name__ == "__main__":
    calculate_close_momentum_20d()
