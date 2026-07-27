from pathlib import Path

import numpy as np
import pandas as pd

FACTOR_NAME = "Provided_Factor_CrossSectional_Rank_1D"


def calculate_provided_factor_crosssectional_rank_1d() -> pd.DataFrame:
    base_path = Path(__file__).resolve().parent
    data_path = base_path / "daily_pv.h5"
    output_path = base_path / "result.h5"

    data = pd.read_hdf(data_path, key="data").sort_index()
    data.index = data.index.set_names(["datetime", "instrument"])

    source_factor = data["$factor"].astype("float64")
    finite_factor = source_factor.where(np.isfinite(source_factor))

    percentile_rank = finite_factor.groupby(
        level="datetime", sort=False
    ).rank(method="average", ascending=True, pct=True)

    result = percentile_rank.to_frame(name=FACTOR_NAME)
    result.index = result.index.set_names(["datetime", "instrument"])
    result.to_hdf(output_path, key="data", mode="w")
    return result


if __name__ == "__main__":
    calculate_provided_factor_crosssectional_rank_1d()
