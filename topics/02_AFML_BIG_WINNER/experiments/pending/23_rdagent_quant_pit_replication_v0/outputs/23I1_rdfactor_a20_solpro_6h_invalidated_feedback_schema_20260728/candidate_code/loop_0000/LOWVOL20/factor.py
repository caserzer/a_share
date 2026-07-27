from pathlib import Path

import pandas as pd


def calculate_lowvol20() -> pd.DataFrame:
    base_dir = Path(__file__).resolve().parent
    input_path = base_dir / "daily_pv.h5"
    output_path = base_dir / "result.h5"

    data = pd.read_hdf(input_path, key="data").sort_index()
    close = data["$close"].astype("float64")

    daily_return = close.groupby(level="instrument", sort=False).pct_change(
        periods=1,
        fill_method=None,
    )

    rolling_volatility = daily_return.groupby(
        level="instrument", sort=False
    ).transform(
        lambda values: values.rolling(
            window=20,
            min_periods=20,
        ).std(ddof=1)
    )

    result = (-rolling_volatility).to_frame(name="LOWVOL20")
    result.index = result.index.set_names(["datetime", "instrument"])
    result.to_hdf(output_path, key="data", mode="w")
    return result


if __name__ == "__main__":
    calculate_lowvol20()
