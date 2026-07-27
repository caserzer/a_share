from pathlib import Path

import numpy as np
import pandas as pd

FACTOR_NAME = "Return_VolumeChange_Correlation_20D"
PAIRED_WINDOW = 20
SOURCE_WINDOW = 21


def calculate_return_volumechange_correlation_20d() -> pd.DataFrame:
    base_path = Path(__file__).resolve().parent
    data_path = base_path / "daily_pv.h5"
    output_path = base_path / "result.h5"

    data = pd.read_hdf(data_path, key="data").sort_index()
    data.index = data.index.set_names(["datetime", "instrument"])

    close = data["$close"].astype("float64")
    volume = data["$volume"].astype("float64")
    factor = pd.Series(np.nan, index=data.index, dtype="float64")

    instrument_positions = data.groupby(
        level="instrument", sort=False
    ).indices

    for positions in instrument_positions.values():
        positions = np.asarray(positions, dtype=np.int64)
        observation_count = positions.size

        if observation_count < SOURCE_WINDOW:
            continue

        close_values = close.iloc[positions].to_numpy(dtype=np.float64)
        volume_values = volume.iloc[positions].to_numpy(dtype=np.float64)

        valid_close = np.isfinite(close_values) & (close_values > 0.0)
        valid_volume = np.isfinite(volume_values) & (volume_values > 0.0)
        valid_source = valid_close & valid_volume

        log_close = np.full(observation_count, np.nan, dtype=np.float64)
        log_volume = np.full(observation_count, np.nan, dtype=np.float64)
        log_close[valid_close] = np.log(close_values[valid_close])
        log_volume[valid_volume] = np.log(volume_values[valid_volume])

        close_returns = np.diff(log_close)
        volume_changes = np.diff(log_volume)

        source_valid_windows = np.lib.stride_tricks.sliding_window_view(
            valid_source, SOURCE_WINDOW
        ).all(axis=1)
        return_windows = np.lib.stride_tricks.sliding_window_view(
            close_returns, PAIRED_WINDOW
        )
        volume_change_windows = np.lib.stride_tricks.sliding_window_view(
            volume_changes, PAIRED_WINDOW
        )

        candidate = (
            source_valid_windows
            & np.isfinite(return_windows).all(axis=1)
            & np.isfinite(volume_change_windows).all(axis=1)
        )

        group_factor = np.full(
            observation_count - PAIRED_WINDOW, np.nan, dtype=np.float64
        )

        if candidate.any():
            candidate_indices = np.flatnonzero(candidate)
            valid_returns = return_windows[candidate_indices]
            valid_volume_changes = volume_change_windows[candidate_indices]

            mean_returns = valid_returns.mean(axis=1)
            mean_volume_changes = valid_volume_changes.mean(axis=1)
            centered_returns = valid_returns - mean_returns[:, None]
            centered_volume_changes = (
                valid_volume_changes - mean_volume_changes[:, None]
            )

            return_std = np.sqrt(
                np.mean(centered_returns * centered_returns, axis=1)
            )
            volume_change_std = np.sqrt(
                np.mean(
                    centered_volume_changes * centered_volume_changes,
                    axis=1,
                )
            )
            covariance = np.mean(
                centered_returns * centered_volume_changes, axis=1
            )
            denominator = return_std * volume_change_std

            valid_moments = (
                np.isfinite(return_std)
                & (return_std > 0.0)
                & np.isfinite(volume_change_std)
                & (volume_change_std > 0.0)
                & np.isfinite(covariance)
                & np.isfinite(denominator)
                & (denominator > 0.0)
            )

            correlations = np.full(candidate_indices.size, np.nan, dtype=np.float64)
            correlations[valid_moments] = (
                covariance[valid_moments] / denominator[valid_moments]
            )
            correlations[~np.isfinite(correlations)] = np.nan
            group_factor[candidate_indices] = correlations

        factor.iloc[positions[PAIRED_WINDOW:]] = group_factor

    result = factor.to_frame(name=FACTOR_NAME).sort_index()
    result.index = result.index.set_names(["datetime", "instrument"])
    result.to_hdf(output_path, key="data", mode="w")
    return result


if __name__ == "__main__":
    calculate_return_volumechange_correlation_20d()
