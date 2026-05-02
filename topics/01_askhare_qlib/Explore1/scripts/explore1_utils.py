from __future__ import annotations

import sys
from pathlib import Path
from typing import Iterable

import pandas as pd
import yaml


EXPLORE_DIR = Path(__file__).resolve().parents[1]
TOPIC_DIR = EXPLORE_DIR.parent
ROOT_SCRIPTS_DIR = TOPIC_DIR / "scripts"


def add_root_scripts_to_path() -> None:
    scripts_path = str(ROOT_SCRIPTS_DIR)
    if scripts_path not in sys.path:
        sys.path.insert(0, scripts_path)


def topic_path(value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return TOPIC_DIR / path


def explore_path(value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return EXPLORE_DIR / path


def relpath(path: str | Path) -> str:
    resolved = Path(path).resolve()
    try:
        return str(resolved.relative_to(TOPIC_DIR))
    except ValueError:
        return str(resolved)


def instrument_from_code(code: str, exchange: str | None = None) -> str:
    text = "".join(ch for ch in str(code).upper() if ch.isdigit()).zfill(6)
    market = exchange
    if market is None:
        market = "SH" if text.startswith("6") else "SZ"
    return f"{market.upper()}{text}"


def qlib_symbol(code: str, exchange: str | None = None) -> str:
    text = "".join(ch for ch in str(code).upper() if ch.isdigit()).zfill(6)
    market = exchange
    if market is None:
        market = "SH" if text.startswith("6") else "SZ"
    return f"{text}.{market.upper()}"


def write_qlib_instruments(universe: pd.DataFrame, output_path: str | Path, start_date: str, end_date: str) -> None:
    path = topic_path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as file:
        for instrument in universe["instrument"]:
            file.write(f"{instrument}\t{start_date}\t{end_date}\n")


def risk_summary(report: pd.DataFrame, freq: str = "day") -> pd.DataFrame:
    from qlib.contrib.evaluate import risk_analysis

    analysis = {
        "excess_return_without_cost": risk_analysis(report["return"] - report["bench"], freq=freq),
        "excess_return_with_cost": risk_analysis(report["return"] - report["bench"] - report["cost"], freq=freq),
        "benchmark": risk_analysis(report["bench"], freq=freq),
        "strategy_return_without_cost": risk_analysis(report["return"], freq=freq),
        "strategy_return_with_cost": risk_analysis(report["return"] - report["cost"], freq=freq),
    }
    return pd.concat(analysis)


def flatten_risk_summary(analysis: pd.DataFrame, prefix: str | None = None) -> dict[str, float]:
    values: dict[str, float] = {}
    risk_col = analysis["risk"] if isinstance(analysis, pd.DataFrame) and "risk" in analysis.columns else analysis
    for index, value in risk_col.items():
        if isinstance(index, tuple):
            key = ".".join(str(part) for part in index)
        else:
            key = str(index)
        if prefix:
            key = f"{prefix}.{key}"
        values[key] = float(value)
    return values


def indicator_summary(indicators: pd.DataFrame | None) -> dict[str, float]:
    if indicators is None or indicators.empty:
        return {}
    result = {}
    for column in ["ffr", "pa", "pos", "deal_amount", "value", "count"]:
        if column in indicators.columns:
            result[column] = float(pd.to_numeric(indicators[column], errors="coerce").mean(skipna=True))
    return result


def load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file)
    return data or {}


def iter_experiment_dirs(mlruns_dir: str | Path, experiment_name: str | None = None) -> Iterable[Path]:
    root = topic_path(mlruns_dir)
    if not root.exists():
        return []
    matches: list[Path] = []
    for meta_path in root.glob("*/meta.yaml"):
        meta = load_yaml(meta_path)
        if experiment_name is None or meta.get("name") == experiment_name:
            matches.append(meta_path.parent)
    return matches


def find_latest_run_artifact(
    artifact_relpath: str,
    *,
    mlruns_dir: str | Path = "mlruns",
    experiment_name: str | None = None,
) -> Path:
    candidates: list[tuple[float, Path]] = []
    for exp_dir in iter_experiment_dirs(mlruns_dir, experiment_name):
        for artifact_path in exp_dir.glob(f"*/artifacts/{artifact_relpath}"):
            candidates.append((artifact_path.stat().st_mtime, artifact_path))
    if not candidates:
        detail = f" experiment={experiment_name!r}" if experiment_name else ""
        raise FileNotFoundError(f"No artifact {artifact_relpath!r} found under {mlruns_dir!r}{detail}")
    return max(candidates, key=lambda item: item[0])[1]


def save_pickle_csv(obj, pickle_path: str | Path, csv_path: str | Path | None = None) -> None:
    pkl = topic_path(pickle_path)
    pkl.parent.mkdir(parents=True, exist_ok=True)
    pd.to_pickle(obj, pkl)
    if csv_path is not None:
        csv = topic_path(csv_path)
        csv.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(obj, (pd.DataFrame, pd.Series)):
            obj.to_csv(csv)
