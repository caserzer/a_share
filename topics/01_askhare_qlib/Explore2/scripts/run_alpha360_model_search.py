#!/usr/bin/env python
from __future__ import annotations

import argparse
import subprocess
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from explore2_utils import find_latest_run_artifact, flatten_risk_summary, load_yaml, relpath, topic_path


CANDIDATES: list[dict[str, Any]] = [
    {
        "name": "current_rerun",
        "kwargs": {
            "loss": "mse",
            "colsample_bytree": 0.8879,
            "learning_rate": 0.0421,
            "subsample": 0.8789,
            "lambda_l1": 205.6999,
            "lambda_l2": 580.9768,
            "max_depth": 8,
            "num_leaves": 210,
            "num_threads": 20,
        },
    },
    {
        "name": "low_reg_shallow",
        "kwargs": {
            "loss": "mse",
            "colsample_bytree": 0.8,
            "learning_rate": 0.03,
            "subsample": 0.8,
            "lambda_l1": 20,
            "lambda_l2": 80,
            "max_depth": 6,
            "num_leaves": 64,
            "num_threads": 20,
        },
    },
    {
        "name": "medium_reg",
        "kwargs": {
            "loss": "mse",
            "colsample_bytree": 0.85,
            "learning_rate": 0.03,
            "subsample": 0.85,
            "lambda_l1": 80,
            "lambda_l2": 200,
            "max_depth": 7,
            "num_leaves": 128,
            "num_threads": 20,
        },
    },
    {
        "name": "relaxed_current",
        "kwargs": {
            "loss": "mse",
            "colsample_bytree": 0.8879,
            "learning_rate": 0.0421,
            "subsample": 0.8789,
            "lambda_l1": 100,
            "lambda_l2": 300,
            "max_depth": 8,
            "num_leaves": 210,
            "num_threads": 20,
        },
    },
    {
        "name": "low_lr_deep",
        "kwargs": {
            "loss": "mse",
            "colsample_bytree": 0.85,
            "learning_rate": 0.02,
            "subsample": 0.85,
            "lambda_l1": 80,
            "lambda_l2": 250,
            "max_depth": 9,
            "num_leaves": 255,
            "num_threads": 20,
        },
    },
    {
        "name": "high_lr_shallow",
        "kwargs": {
            "loss": "mse",
            "colsample_bytree": 0.75,
            "learning_rate": 0.08,
            "subsample": 0.75,
            "lambda_l1": 50,
            "lambda_l2": 150,
            "max_depth": 5,
            "num_leaves": 48,
            "num_threads": 20,
        },
    },
    {
        "name": "light_reg_wide",
        "kwargs": {
            "loss": "mse",
            "colsample_bytree": 0.9,
            "learning_rate": 0.05,
            "subsample": 0.9,
            "lambda_l1": 5,
            "lambda_l2": 20,
            "max_depth": 8,
            "num_leaves": 128,
            "num_threads": 20,
        },
    },
    {
        "name": "strong_reg_small_leaf",
        "kwargs": {
            "loss": "mse",
            "colsample_bytree": 0.8,
            "learning_rate": 0.04,
            "subsample": 0.8,
            "lambda_l1": 300,
            "lambda_l2": 800,
            "max_depth": 6,
            "num_leaves": 32,
            "num_threads": 20,
        },
    },
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run expanded Explore2 Alpha360 LightGBM model search.")
    parser.add_argument("--base-config", default="Explore2/configs/qlib_lightgbm_alpha360_mcap500.yaml")
    parser.add_argument("--config-dir", default="Explore2/configs/model_search")
    parser.add_argument("--experiment-prefix", default="alpha360_lightgbm_mcap500_search")
    parser.add_argument("--mlruns-dir", default="mlruns")
    parser.add_argument("--summary", default="Explore2/outputs/reports/alpha360_model_search_summary.csv")
    parser.add_argument("--skip-run", action="store_true", help="Only collect latest existing runs.")
    parser.add_argument("--only", nargs="+", choices=[candidate["name"] for candidate in CANDIDATES])
    return parser.parse_args()


def candidate_experiment(prefix: str, name: str) -> str:
    return f"{prefix}_{name}"


def write_config(base_config: Path, config_dir: Path, candidate: dict[str, Any]) -> Path:
    config = load_yaml(base_config)
    config["task"]["model"]["kwargs"] = candidate["kwargs"]
    path = config_dir / f"qlib_lightgbm_alpha360_mcap500_{candidate['name']}.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as file:
        yaml.safe_dump(config, file, allow_unicode=True, sort_keys=False)
    return path


def latest_pickle(artifact: str, mlruns_dir: str, experiment: str):
    path = find_latest_run_artifact(artifact, mlruns_dir=mlruns_dir, experiment_name=experiment)
    return pd.read_pickle(path), path


def read_metric_history(run_dir: Path, metric_name: str) -> pd.DataFrame:
    path = run_dir / "metrics" / metric_name
    if not path.exists():
        return pd.DataFrame()
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if len(parts) >= 3:
            rows.append({"timestamp": int(parts[0]), "value": float(parts[1]), "step": int(parts[2])})
    return pd.DataFrame(rows)


def collect_candidate(args: argparse.Namespace, candidate: dict[str, Any], config_path: Path) -> dict[str, Any]:
    experiment = candidate_experiment(args.experiment_prefix, candidate["name"])
    pred, pred_path = latest_pickle("pred.pkl", args.mlruns_dir, experiment)
    run_dir = pred_path.parent.parent
    ic, ic_path = latest_pickle("sig_analysis/ic.pkl", args.mlruns_dir, experiment)
    ric, ric_path = latest_pickle("sig_analysis/ric.pkl", args.mlruns_dir, experiment)
    analysis, analysis_path = latest_pickle("portfolio_analysis/port_analysis_1day.pkl", args.mlruns_dir, experiment)

    pred_frame = pred if isinstance(pred, pd.DataFrame) else pred.to_frame("score")
    train = read_metric_history(run_dir, "l2.train")
    valid = read_metric_history(run_dir, "l2.valid")

    row: dict[str, Any] = {
        "candidate": candidate["name"],
        "experiment": experiment,
        "config_path": relpath(config_path),
        "run_dir": relpath(run_dir),
        "pred_path": relpath(pred_path),
        "ic_path": relpath(ic_path),
        "ric_path": relpath(ric_path),
        "port_analysis_path": relpath(analysis_path),
        "pred_rows": len(pred_frame),
    }
    row.update({f"param.{key}": value for key, value in candidate["kwargs"].items()})
    if not train.empty:
        row["final_train_l2"] = float(train["value"].iloc[-1])
        row["train_rounds"] = int(train["step"].max() + 1)
    if not valid.empty:
        best = valid.loc[valid["value"].idxmin()]
        row["best_iteration"] = int(best["step"] + 1)
        row["best_valid_l2"] = float(best["value"])
        row["final_valid_l2"] = float(valid["value"].iloc[-1])
        row["valid_rounds"] = int(valid["step"].max() + 1)
    ic = pd.to_numeric(ic, errors="coerce")
    ric = pd.to_numeric(ric, errors="coerce")
    row["IC"] = float(ic.mean(skipna=True))
    row["ICIR"] = float(ic.mean(skipna=True) / ic.std(skipna=True))
    row["Rank IC"] = float(ric.mean(skipna=True))
    row["Rank ICIR"] = float(ric.mean(skipna=True) / ric.std(skipna=True))
    row.update(flatten_risk_summary(analysis))
    return row


def main() -> int:
    args = parse_args()
    base_config = topic_path(args.base_config)
    config_dir = topic_path(args.config_dir)
    selected = [candidate for candidate in CANDIDATES if args.only is None or candidate["name"] in args.only]

    rows = []
    for candidate in selected:
        config_path = write_config(base_config, config_dir, candidate)
        experiment = candidate_experiment(args.experiment_prefix, candidate["name"])
        if not args.skip_run:
            print(f"running {candidate['name']} -> {experiment}")
            subprocess.run(["uv", "run", "qrun", str(config_path), "-e", experiment], check=True, cwd=topic_path("."))
        try:
            rows.append(collect_candidate(args, candidate, config_path))
        except FileNotFoundError as exc:
            print(f"skip collect for {candidate['name']}: {exc}")

    summary = pd.DataFrame(rows)
    if not summary.empty and "excess_return_with_cost.annualized_return" in summary.columns:
        summary = summary.sort_values("excess_return_with_cost.annualized_return", ascending=False)
    summary_path = topic_path(args.summary)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary.to_csv(summary_path, index=False)
    print(f"wrote {relpath(summary_path)} rows={len(summary)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
