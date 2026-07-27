from pathlib import Path

import numpy as np
import pandas as pd

FACTOR_NAME = "Lagged_VolumeChange_Return_Correlation_20D"
PAIRED_WINDOW = 20
SOURCE_WINDOW = 22


def _calculate_instrument_factor(close: np.ndarray, volume: np.ndarray) -> np.ndarray:
    observation_count = len(close)
    output = np.full(observation_count, np.nan, dtype=np.float64)

    if observation_count < SOURCE_WINDOW:
        return output

    close_valid = np.isfinite(close) & (close > 0.0)
    volume_valid = np.isfinite(volume) & (volume > 0.0)
    source_valid = close_valid & volume_valid

    close_return = np.full(observation_count, np.nan, dtype=np.float64)
    lagged_volume_change = np.full(observation_count, np.nan, dtype=np.float64)

    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        close_return[1:] = np.log(close[1:] / close[:-1])
        lagged_volume_change[2:] = np.log(volume[1:-1] / volume[:-2])

    source_windows = np.lib.stride_tricks.sliding_window_view(
        source_valid, SOURCE_WINDOW
    )
    return_windows = np.lib.stride_tricks.sliding_window_view(
        close_return, PAIRED_WINDOW
    )[SOURCE_WINDOW - PAIRED_WINDOW :]
    volume_change_windows = np.lib.stride_tricks.sliding_window_view(
        lagged_volume_change, PAIRED_WINDOW
    )[SOURCE_WINDOW - PAIRED_WINDOW :]

    complete_source = source_windows.all(axis=1)
    finite_pairs = (
        np.isfinite(return_windows).all(axis=1)
        & np.isfinite(volume_change_windows).all(axis=1)
    )

    mean_return = return_windows.mean(axis=1)
    mean_volume_change = volume_change_windows.mean(axis=1)

    centered_return = return_windows - mean_return[:, None]
    centered_volume_change = volume_change_windows - mean_volume_change[:, None]

    return_variance = np.mean(centered_return * centered_return, axis=1)
    volume_change_variance = np.mean(
        centered_volume_change * centered_volume_change, axis=1
    )
    covariance = np.mean(
        centered_volume_change * centered_return,
        axis=1,
    )

    with np.errstate(invalid="ignore", over="ignore"):
        return_std = np.sqrt(return_variance)
        volume_change_std = np.sqrt(volume_change_variance)
        denominator = volume_change_std * return_std

    valid = (
        complete_source
        & finite_pairs
        & np.isfinite(return_std)
        & (return_std > 0.0)
        & np.isfinite(volume_change_std)
        & (volume_change_std > 0.0)
        & np.isfinite(covariance)
        & np.isfinite(denominator)
        & (denominator > 0.0)
    )

    correlation = np.full(len(source_windows), np.nan, dtype=np.float64)
    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        correlation[valid] = covariance[valid] / denominator[valid]

    correlation[~np.isfinite(correlation)] = np.nan
    output[SOURCE_WINDOW - 1 :] = correlation
    return output


def calculate_lagged_volumechange_return_correlation_20d() -> pd.DataFrame:
    base_path = Path(__file__).resolve().parent
    data_path = base_path / "daily_pv.h5"
    output_path = base_path / "result.h5"

    data = pd.read_hdf(data_path, key="data").sort_index()
    data.index = data.index.set_names(["datetime", "instrument"])

    close = data["$close"].to_numpy(dtype=np.float64, copy=True)
    volume = data["$volume"].to_numpy(dtype=np.float64, copy=True)
    factor_values = np.full(len(data), np.nan, dtype=np.float64)

    instrument_positions = data.groupby(
        level="instrument", sort=False
    ).indices

    for positions in instrument_positions.values():
        positions = np.asarray(positions, dtype=np.int64)
        factor_values[positions] = _calculate_instrument_factor(
            close[positions], volume[positions]
        )

    result = pd.DataFrame(
        {FACTOR_NAME: factor_values},
        index=data.index,
    )
    result.index = result.index.set_names(["datetime", "instrument"])
    result.to_hdf(output_path, key="data", mode="w")
    return result


if __name__ == "__main__":
    calculate_lagged_volumechange_return_correlation_20d()
