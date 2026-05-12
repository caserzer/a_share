#!/usr/bin/env python3
from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import itertools
import json
import multiprocessing as mp
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parent
EP4_DIR = SCRIPT_DIR.parent
TOPIC_DIR = EP4_DIR.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from r01_high_recall_probe_fail_fast_common import (  # noqa: E402
    build_big_winner_reference,
    load_config,
    load_provider_spine,
    prepare_stock_day_panel,
    relpath,
    split_effective_windows,
    topic_path,
    write_csv,
    write_json,
)


DEFAULT_CONFIG = EP4_DIR / "configs" / "r01_high_recall_probe_fail_fast_v2.yaml"
DEFAULT_OUTPUT_ROOT = EP4_DIR / "outputs" / "r01_big_winner_post30_indicator_search_v1"
_WORKER_ATOMS: list["Atom"] = []
_WORKER_MASKS: np.ndarray | None = None
_WORKER_REFERENCE: pd.DataFrame | None = None
_WORKER_ELIGIBLE_MASK: np.ndarray | None = None
_WORKER_ELIGIBLE_COUNT: int = 0


@dataclass(frozen=True)
class Atom:
    name: str
    family: str
    values: np.ndarray


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_div(numer: float, denom: float, default: float = 0.0) -> float:
    return float(numer) / float(denom) if denom else default


def _sanitize_threshold(value: float) -> str:
    text = f"{value:g}".replace("-", "m").replace(".", "_")
    return text


def _rank_pct_by_date(stock: pd.DataFrame, source: pd.Series) -> pd.Series:
    return source.groupby(stock["date"]).rank(pct=True)


def enrich_indicators(stock: pd.DataFrame) -> pd.DataFrame:
    out = stock.sort_values(["instrument", "date"]).copy()
    group = out.groupby("instrument", group_keys=False)
    for window in [3, 5, 10, 20, 60, 120]:
        out[f"vol_{window}d_mean_asof"] = group["volume"].transform(lambda s, w=window: s.shift(1).rolling(w, min_periods=w).mean())
        out[f"money_{window}d_mean_asof"] = group["money"].transform(lambda s, w=window: s.shift(1).rolling(w, min_periods=w).mean())
        out[f"vol_ratio{window}"] = out["volume"] / out[f"vol_{window}d_mean_asof"]
        out[f"money_ratio{window}"] = out["money"] / out[f"money_{window}d_mean_asof"]
        out[f"ma{window}"] = group["close"].transform(lambda s, w=window: s.rolling(w, min_periods=w).mean())
        out[f"ema{window}"] = group["close"].transform(lambda s, w=window: s.ewm(span=w, adjust=False, min_periods=w).mean())
        out[f"close_ma{window}_pct"] = out["close"] / out[f"ma{window}"] - 1.0
        out[f"close_ema{window}_pct"] = out["close"] / out[f"ema{window}"] - 1.0
        out[f"ret{window}"] = group["close"].transform(lambda s, w=window: s / s.shift(w) - 1.0)
        out[f"rps{window}"] = _rank_pct_by_date(out, out[f"ret{window}"])
        out[f"prior_high{window}"] = group["close"].transform(lambda s, w=window: s.shift(1).rolling(w, min_periods=w).max())
        out[f"prior_low{window}"] = group["close"].transform(lambda s, w=window: s.shift(1).rolling(w, min_periods=w).min())
        out[f"close_near_high{window}_pct"] = out["close"] / out[f"prior_high{window}"] - 1.0
        out[f"drawup_from_low{window}_pct"] = out["close"] / out[f"prior_low{window}"] - 1.0
    delta = group["close"].diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_gain = gain.groupby(out["instrument"]).transform(lambda s: s.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean())
    avg_loss = loss.groupby(out["instrument"]).transform(lambda s: s.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean())
    rs = avg_gain / avg_loss
    out["rsi14"] = 100 - 100 / (1 + rs)
    boll_mid = group["close"].transform(lambda s: s.rolling(20, min_periods=20).mean())
    boll_std = group["close"].transform(lambda s: s.rolling(20, min_periods=20).std(ddof=0))
    out["boll20_pct_b_post"] = (out["close"] - (boll_mid - 2 * boll_std)) / (4 * boll_std)
    out["boll20_width"] = 4 * boll_std / boll_mid
    out["boll20_width_ratio60"] = out["boll20_width"] / group["boll20_width"].transform(lambda s: s.shift(1).rolling(60, min_periods=60).median())
    return out


def add_atom(atoms: list[Atom], stock: pd.DataFrame, name: str, family: str, values: pd.Series | np.ndarray) -> None:
    arr = np.asarray(values, dtype=bool)
    if arr.any():
        atoms.append(Atom(name=name, family=family, values=arr))


def build_atoms(stock: pd.DataFrame) -> list[Atom]:
    atoms: list[Atom] = []
    finite_close = np.isfinite(stock["close"].to_numpy(dtype=float))
    add_atom(atoms, stock, "always_pit_executable", "base", finite_close)

    for prefix in ["money_ratio", "vol_ratio"]:
        for window in [3, 5, 10, 20, 60, 120]:
            col = f"{prefix}{window}"
            if col not in stock:
                continue
            for threshold in [0.8, 1.0, 1.2, 1.5, 2.0, 2.5, 3.0, 4.0]:
                add_atom(atoms, stock, f"{col}_gt_{_sanitize_threshold(threshold)}", prefix, stock[col] > threshold)

    for prefix in ["close_ma", "close_ema"]:
        for window in [3, 5, 10, 20, 60, 120]:
            col = f"{prefix}{window}_pct"
            if col not in stock:
                continue
            for threshold in [-0.10, -0.05, -0.02, 0.0, 0.02, 0.05, 0.10]:
                add_atom(atoms, stock, f"{prefix}{window}_gt_{_sanitize_threshold(threshold * 100)}pct", prefix, stock[col] >= threshold)

    for window in [3, 5, 10, 20, 60, 120]:
        for threshold in [-0.10, -0.05, 0.0, 0.02, 0.05, 0.10, 0.20, 0.30]:
            add_atom(atoms, stock, f"ret{window}_gt_{_sanitize_threshold(threshold * 100)}pct", "return", stock[f"ret{window}"] >= threshold)
        for threshold in [0.30, 0.40, 0.50, 0.60, 0.70, 0.80, 0.90]:
            add_atom(atoms, stock, f"rps{window}_gt_{int(threshold * 100)}", "rps", stock[f"rps{window}"] >= threshold)
        for threshold in [-0.10, -0.05, -0.02, 0.0]:
            add_atom(atoms, stock, f"close_near_high{window}_gt_{_sanitize_threshold(threshold * 100)}pct", "high", stock[f"close_near_high{window}_pct"] >= threshold)
        add_atom(atoms, stock, f"close_breaks_high{window}", "high", stock["close"] >= stock[f"prior_high{window}"])
        for threshold in [0.05, 0.10, 0.20, 0.30, 0.50]:
            add_atom(atoms, stock, f"drawup_from_low{window}_gt_{_sanitize_threshold(threshold * 100)}pct", "rebound", stock[f"drawup_from_low{window}_pct"] >= threshold)

    for threshold in [35, 40, 45, 50, 55, 60, 65, 70]:
        add_atom(atoms, stock, f"rsi14_gt_{threshold}", "rsi", stock["rsi14"] >= threshold)
    for threshold in [-0.5, 0.0, 0.2, 0.3, 0.5, 0.8, 1.0, 1.2]:
        add_atom(atoms, stock, f"boll20_pct_b_gt_{_sanitize_threshold(threshold)}", "boll", stock["boll20_pct_b_post"] >= threshold)
    for threshold in [0.5, 0.8, 1.0, 1.2, 1.5]:
        add_atom(atoms, stock, f"boll20_width_ratio60_gt_{_sanitize_threshold(threshold)}", "boll_width", stock["boll20_width_ratio60"] >= threshold)
        add_atom(atoms, stock, f"boll20_width_ratio60_lt_{_sanitize_threshold(threshold)}", "boll_width", stock["boll20_width_ratio60"] <= threshold)

    add_atom(atoms, stock, "ma5_gt_ma10", "stack", stock["ma5"] > stock["ma10"])
    add_atom(atoms, stock, "ma10_gt_ma20", "stack", stock["ma10"] > stock["ma20"])
    add_atom(atoms, stock, "ma20_gt_ma60", "stack", stock["ma20"] > stock["ma60"])
    add_atom(atoms, stock, "ma_bull_5_10_20", "stack", (stock["ma5"] > stock["ma10"]) & (stock["ma10"] > stock["ma20"]))
    add_atom(atoms, stock, "ma_bull_10_20_60", "stack", (stock["ma10"] > stock["ma20"]) & (stock["ma20"] > stock["ma60"]))
    add_atom(atoms, stock, "ema5_gt_ema10", "stack", stock["ema5"] > stock["ema10"])
    add_atom(atoms, stock, "ema10_gt_ema20", "stack", stock["ema10"] > stock["ema20"])
    add_atom(atoms, stock, "ema20_gt_ema60", "stack", stock["ema20"] > stock["ema60"])
    add_atom(atoms, stock, "ema_bull_5_10_20", "stack", (stock["ema5"] > stock["ema10"]) & (stock["ema10"] > stock["ema20"]))
    add_atom(atoms, stock, "ema_bull_10_20_60", "stack", (stock["ema10"] > stock["ema20"]) & (stock["ema20"] > stock["ema60"]))

    add_atom(
        atoms,
        stock,
        "r01_v2_raw_money_rps5_boll20_high10",
        "r01_seed",
        (stock["money_ratio20_mean_asof"] > 1.0)
        & (stock["money_ratio5_mean_asof"] > 2.0)
        & (stock["rps5_rank_pct"] > 0.50)
        & (stock["boll20_pct_b"] > 1.0)
        & (stock["close_near_high10_ratio"] >= 1.0),
    )
    return atoms


def event_window_indices(stock: pd.DataFrame, reference: pd.DataFrame, calendar: pd.DatetimeIndex) -> list[np.ndarray]:
    key_to_index = {
        (str(row.instrument), pd.Timestamp(row.date)): i
        for i, row in enumerate(stock[["instrument", "date"]].reset_index(drop=True).itertuples(index=False))
    }
    windows: list[np.ndarray] = []
    for row in reference.sort_values(["split", "instrument", "reference_date"]).itertuples(index=False):
        inst = str(row.instrument)
        ref_date = pd.Timestamp(row.reference_date).normalize()
        idxs: list[int] = []
        for offset in range(0, 31):
            pos = calendar.searchsorted(ref_date, side="left") + offset
            if pos >= len(calendar):
                continue
            key = (inst, pd.Timestamp(calendar[pos]))
            if key in key_to_index:
                idxs.append(key_to_index[key])
        windows.append(np.asarray(idxs, dtype=np.int64))
    return windows


def atom_event_masks(atoms: list[Atom], windows: list[np.ndarray]) -> np.ndarray:
    masks = np.zeros((len(atoms), len(windows)), dtype=np.uint64)
    bits = np.asarray([np.uint64(1) << np.uint64(i) for i in range(31)], dtype=np.uint64)
    for atom_idx, atom in enumerate(atoms):
        values = atom.values
        for event_idx, idxs in enumerate(windows):
            if idxs.size == 0:
                continue
            hit_positions = np.flatnonzero(values[idxs])
            if hit_positions.size:
                masks[atom_idx, event_idx] = np.bitwise_or.reduce(bits[hit_positions])
    return masks


def condition_stats(
    name: str,
    kind: str,
    atom_indices: tuple[int, ...],
    daily_values: np.ndarray,
    event_mask: np.ndarray,
    reference: pd.DataFrame,
    eligible_count: int,
) -> dict[str, Any]:
    covered = event_mask != 0
    closest: list[int] = []
    earliest: list[int] = []
    for mask in event_mask[covered]:
        hit_offsets = [idx for idx in range(31) if int(mask) & (1 << idx)]
        if hit_offsets:
            earliest.append(hit_offsets[0])
            closest.append(hit_offsets[0])
    row = {
        "condition": name,
        "kind": kind,
        "n_terms": len(atom_indices),
        "atom_indices": ",".join(str(i) for i in atom_indices),
        "covered_events_t0_t30": int(covered.sum()),
        "coverage_t0_t30": _safe_div(float(covered.sum()), float(len(reference))),
        "eligible_day_density": _safe_div(float(daily_values.sum()), float(eligible_count)),
        "median_closest_hit_offset": float(np.median(closest)) if closest else np.nan,
        "median_earliest_hit_offset": float(np.median(earliest)) if earliest else np.nan,
    }
    for split, group in reference.reset_index(drop=True).groupby("split"):
        split_idx = group.index.to_numpy()
        split_cov = covered[split_idx]
        row[f"{split}_covered_events"] = int(split_cov.sum())
        row[f"{split}_coverage_t0_t30"] = _safe_div(float(split_cov.sum()), float(len(split_idx)))
    return row


def _combo_name(combo: tuple[int, ...], operator: str) -> str:
    return f" {operator} ".join(_WORKER_ATOMS[i].name for i in combo)


def _eval_combo_chunk(task: tuple[str, list[tuple[int, ...]]]) -> list[dict[str, Any]]:
    kind, combos = task
    assert _WORKER_MASKS is not None
    assert _WORKER_REFERENCE is not None
    assert _WORKER_ELIGIBLE_MASK is not None
    rows: list[dict[str, Any]] = []
    for combo in combos:
        if kind == "kof_2of3":
            values = np.vstack([_WORKER_ATOMS[i].values for i in combo])
            daily = (values.sum(axis=0) >= 2) & _WORKER_ELIGIBLE_MASK
            event_mask = (
                (_WORKER_MASKS[combo[0]] & _WORKER_MASKS[combo[1]])
                | (_WORKER_MASKS[combo[0]] & _WORKER_MASKS[combo[2]])
                | (_WORKER_MASKS[combo[1]] & _WORKER_MASKS[combo[2]])
            )
            name = _combo_name(combo, "2_OF_3")
        else:
            daily = _WORKER_ELIGIBLE_MASK.copy()
            event_mask = np.full(_WORKER_MASKS.shape[1], np.uint64((1 << 31) - 1), dtype=np.uint64)
            for idx in combo:
                daily &= _WORKER_ATOMS[idx].values
                event_mask &= _WORKER_MASKS[idx]
            if not daily.any():
                continue
            name = _combo_name(combo, "AND")
        rows.append(condition_stats(name, kind, combo, daily, event_mask, _WORKER_REFERENCE, _WORKER_ELIGIBLE_COUNT))
    return rows


def _chunks(items: list[tuple[int, ...]], size: int) -> list[list[tuple[int, ...]]]:
    return [items[i : i + size] for i in range(0, len(items), size)]


def _evaluate_combo_tasks(tasks: list[tuple[str, list[tuple[int, ...]]]], workers: int) -> list[dict[str, Any]]:
    if workers <= 1 or len(tasks) <= 1:
        rows: list[dict[str, Any]] = []
        for task in tasks:
            rows.extend(_eval_combo_chunk(task))
        return rows
    ctx = mp.get_context("fork")
    rows = []
    with concurrent.futures.ProcessPoolExecutor(max_workers=workers, mp_context=ctx) as executor:
        for chunk_rows in executor.map(_eval_combo_chunk, tasks):
            rows.extend(chunk_rows)
    return rows


def evaluate_conditions(
    atoms: list[Atom],
    masks: np.ndarray,
    reference: pd.DataFrame,
    eligible_mask: np.ndarray,
    workers: int = 1,
    chunk_size: int = 1000,
) -> pd.DataFrame:
    global _WORKER_ATOMS, _WORKER_MASKS, _WORKER_REFERENCE, _WORKER_ELIGIBLE_MASK, _WORKER_ELIGIBLE_COUNT
    _WORKER_ATOMS = atoms
    _WORKER_MASKS = masks
    _WORKER_REFERENCE = reference
    _WORKER_ELIGIBLE_MASK = eligible_mask
    _WORKER_ELIGIBLE_COUNT = int(eligible_mask.sum())
    eligible_count = int(eligible_mask.sum())
    rows: list[dict[str, Any]] = []
    atom_coverages = []
    for idx, atom in enumerate(atoms):
        event_mask = masks[idx]
        rows.append(condition_stats(atom.name, "single", (idx,), atom.values & eligible_mask, event_mask, reference, eligible_count))
        atom_coverages.append((idx, float((event_mask != 0).mean()), float((atom.values & eligible_mask).mean())))

    ranked_atoms = [idx for idx, _, _ in sorted(atom_coverages, key=lambda x: (-x[1], x[2]))]
    selected_for_pairs = ranked_atoms[:90]
    selected_for_triples = ranked_atoms[:55]
    selected_for_quads = ranked_atoms[:28]

    combo_tasks: list[tuple[str, list[tuple[int, ...]]]] = []
    for kind, combos in [
        ("and2", list(itertools.combinations(selected_for_pairs, 2))),
        ("and3", list(itertools.combinations(selected_for_triples, 3))),
        ("and4", list(itertools.combinations(selected_for_quads, 4))),
        ("kof_2of3", list(itertools.combinations(selected_for_triples[:45], 3))),
    ]:
        combo_tasks.extend((kind, chunk) for chunk in _chunks(combos, chunk_size))
    rows.extend(_evaluate_combo_tasks(combo_tasks, workers))

    out = pd.DataFrame(rows)
    out = out.sort_values(["coverage_t0_t30", "eligible_day_density"], ascending=[False, True]).reset_index(drop=True)
    return out


def write_report(output_root: Path, all_conditions: pd.DataFrame, ge85: pd.DataFrame, reference: pd.DataFrame, atom_count: int) -> None:
    reports = output_root / "reports"
    best = ge85.sort_values(["eligible_day_density", "n_terms"], ascending=[True, True]).head(1)
    split_rows = []
    if not best.empty:
        row = best.iloc[0]
        for split, group in reference.groupby("split"):
            split_rows.append(
                {
                    "split": split,
                    "event_count": len(group),
                    "covered_t0_t30": int(row.get(f"{split}_covered_events", 0)),
                    "coverage_t0_t30": float(row.get(f"{split}_coverage_t0_t30", np.nan)),
                }
            )
    lines = [
        "# Big Winner T+0 到 T+30 组合指标覆盖率搜索 v1",
        "",
        f"- 样本：{len(reference)} 个 canonical R01 primary big winner",
        "- 覆盖定义：同一股票在 reference_date 的 T+0 到 T+30 至少一天满足日级条件",
        "- 密度定义：条件在 R01 PIT-executable eligible stock-days 上的日级触发比例",
        f"- 搜索规模：{atom_count} 个原子条件，{len(all_conditions)} 个单条件/组合条件",
        "",
    ]
    if best.empty:
        lines += ["## 结果", "", "没有找到覆盖率 >=85% 的条件。", ""]
    else:
        row = best.iloc[0]
        lines += [
            "## 推荐的低密度 T+0..T+30 覆盖条件（coverage >=85%）",
            "",
            "```text",
            str(row["condition"]),
            "```",
            "",
            "| metric | value |",
            "|:--|--:|",
            f"| kind | {row['kind']} |",
            f"| coverage T+0..T+30 | {row['coverage_t0_t30']:.2%} |",
            f"| covered events | {int(row['covered_events_t0_t30'])} / {len(reference)} |",
            f"| eligible-day density | {row['eligible_day_density']:.2%} |",
            f"| median closest hit offset | {row['median_closest_hit_offset']} |",
            f"| median earliest hit offset | {row['median_earliest_hit_offset']} |",
            "",
            "## Split 覆盖",
            "",
            pd.DataFrame(split_rows).to_markdown(index=False),
            "",
        ]
    lines += [
        "## 覆盖 >=85% 的 Top 100 低密度条件",
        "",
        ge85.sort_values(["eligible_day_density", "coverage_t0_t30"], ascending=[True, False]).head(100)[
            [
                "condition",
                "kind",
                "n_terms",
                "coverage_t0_t30",
                "covered_events_t0_t30",
                "eligible_day_density",
                "median_closest_hit_offset",
                "median_earliest_hit_offset",
            ]
        ].to_markdown(index=False)
        if not ge85.empty
        else "无。",
        "",
        "## 观察",
        "",
        "1. 这个搜索是 post-reference 画像搜索，不是可提前执行的 seed。它回答 winner 出现后 30 天内哪些状态最常共现。",
        "2. 因为窗口在 T+0..T+30，覆盖率更容易被趋势确认、均线站上、成交活跃和强势排序条件推高；这些条件若用于 entry，需要另行证明可执行性和成本。",
        "3. `AND` 条件更像日级 seed；`kof` 条件更像宽松状态画像，覆盖高但通常密度更高。",
        "",
        "## 输出文件",
        "",
        "- `reports/post30_condition_search_v1_all.csv`",
        "- `reports/post30_condition_search_v1_ge85.csv`",
        "- `reports/post30_condition_search_v1_top_single.csv`",
        "- `reports/post30_condition_search_v1_top_and2.csv`",
        "- `reports/post30_condition_search_v1_top_and3.csv`",
        "- `reports/post30_condition_search_v1_top_and4.csv`",
        "- `reports/post30_condition_search_v1_top_kof.csv`",
    ]
    (reports / "post30_condition_search_v1_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(config_path: Path, output_root: Path, workers: int, chunk_size: int) -> dict[str, Any]:
    config, _, ep2_config = load_config(config_path)
    panel, calendar = load_provider_spine(config, ep2_config)
    stock = prepare_stock_day_panel(config, ep2_config, panel, calendar)
    stock = enrich_indicators(stock)
    data_max = pd.to_datetime(stock["date"]).max()
    effective_windows, _ = split_effective_windows(config, calendar, data_max)
    reference = build_big_winner_reference(stock, config, calendar, effective_windows).sort_values(["split", "instrument", "reference_date"]).reset_index(drop=True)
    atoms = build_atoms(stock)
    windows = event_window_indices(stock.reset_index(drop=True), reference, calendar)
    masks = atom_event_masks(atoms, windows)
    eligible_mask = stock["eligible_stock_day"].astype(bool).to_numpy()
    all_conditions = evaluate_conditions(atoms, masks, reference, eligible_mask, workers=workers, chunk_size=chunk_size)
    ge85 = all_conditions.loc[all_conditions["coverage_t0_t30"] >= 0.85].copy()

    reports = output_root / "reports"
    manifests = output_root / "manifests"
    reports.mkdir(parents=True, exist_ok=True)
    manifests.mkdir(parents=True, exist_ok=True)
    write_csv(all_conditions, reports / "post30_condition_search_v1_all.csv")
    write_csv(ge85, reports / "post30_condition_search_v1_ge85.csv")
    for kind, name in [
        ("single", "post30_condition_search_v1_top_single.csv"),
        ("and2", "post30_condition_search_v1_top_and2.csv"),
        ("and3", "post30_condition_search_v1_top_and3.csv"),
        ("and4", "post30_condition_search_v1_top_and4.csv"),
    ]:
        write_csv(all_conditions.loc[all_conditions["kind"].eq(kind)].sort_values(["coverage_t0_t30", "eligible_day_density"], ascending=[False, True]).head(200), reports / name)
    write_csv(all_conditions.loc[all_conditions["kind"].str.startswith("kof")].sort_values(["coverage_t0_t30", "eligible_day_density"], ascending=[False, True]).head(200), reports / "post30_condition_search_v1_top_kof.csv")
    write_report(output_root, all_conditions, ge85, reference, len(atoms))

    best = ge85.sort_values(["eligible_day_density", "n_terms"], ascending=[True, True]).head(1)
    manifest = {
        "phase": "ep4_big_winner_post30_condition_search_v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "reference_source": "canonical R01 primary big winner reconstructed from PIT provider",
        "config_path": relpath(topic_path(config_path)),
        "config_hash": _hash_file(topic_path(config_path)),
        "output_root": relpath(output_root),
        "event_count": int(len(reference)),
        "atom_count": int(len(atoms)),
        "condition_count": int(len(all_conditions)),
        "workers": int(workers),
        "chunk_size": int(chunk_size),
        "coverage_target": 0.85,
        "coverage_window": "T+0 through T+30 trading days after reference_date",
        "ge85_condition_count": int(len(ge85)),
        "best_low_density_condition": "" if best.empty else str(best.iloc[0]["condition"]),
        "best_low_density_kind": "" if best.empty else str(best.iloc[0]["kind"]),
        "best_low_density_coverage_t0_t30": None if best.empty else float(best.iloc[0]["coverage_t0_t30"]),
        "best_low_density": None if best.empty else float(best.iloc[0]["eligible_day_density"]),
    }
    write_json(manifest, manifests / "post30_condition_search_v1_manifest.json")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Search post-reference T+0..T+30 indicator coverage for EP4 R01 big winners.")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--output-root", default=str(DEFAULT_OUTPUT_ROOT))
    parser.add_argument("--workers", type=int, default=max(1, min(8, (os.cpu_count() or 2) - 1)))
    parser.add_argument("--chunk-size", type=int, default=800)
    args = parser.parse_args()
    result = run(Path(args.config), Path(args.output_root), workers=max(1, args.workers), chunk_size=max(1, args.chunk_size))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
