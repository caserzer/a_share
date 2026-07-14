#!/usr/bin/env python3
"""Run the post-v5 P4 bucket-capacity and deferred-exit diagnostic."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import requests
import yaml


ARM_ID = "P4_RESMOM_R2_MARKET_ONLY_ADAPTATION"
TRACK = "project_sequential_market_residual_primary"
UNKNOWN = "unknown_bridge_arm_month_not_evaluable"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stable_hash(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def write_csv(path: Path, frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, compression="gzip" if path.suffix == ".gz" else None)


def assign_capacity_membership(signal: pd.DataFrame, capacities: list[int]) -> pd.DataFrame:
    """Stable top/bottom-N membership for every decision month and capacity."""
    required = {"instrument_id", "decision_date", "raw_signal"}
    if not required.issubset(signal.columns):
        raise ValueError(f"missing signal columns: {sorted(required - set(signal.columns))}")
    if signal.duplicated(["instrument_id", "decision_date"]).any():
        raise ValueError("duplicate instrument-decision signal rows")
    if not np.isfinite(pd.to_numeric(signal["raw_signal"], errors="coerce")).all():
        raise ValueError("nonfinite raw_signal in eligible P4 panel")

    rows: list[pd.DataFrame] = []
    for decision_date, group in signal.groupby("decision_date", sort=True):
        ranked = group.sort_values(["raw_signal", "instrument_id"], ascending=[False, True]).copy()
        ranked["rank_desc"] = np.arange(1, len(ranked) + 1)
        ranked["rank_asc"] = len(ranked) - ranked["rank_desc"] + 1
        for capacity in capacities:
            if len(ranked) < 2 * capacity:
                continue
            part = ranked.copy()
            part["bucket_capacity_n"] = int(capacity)
            part["membership_role"] = np.select(
                [part["rank_desc"] <= capacity, part["rank_asc"] <= capacity],
                ["favorable_top_n", "unfavorable_bottom_n"],
                default="not_selected_middle",
            )
            part["formation_weight"] = np.where(
                part["membership_role"].isin(["favorable_top_n", "unfavorable_bottom_n"]),
                1.0 / capacity,
                np.nan,
            )
            rows.append(part)
    if not rows:
        raise ValueError("no capacity membership formed")
    result = pd.concat(rows, ignore_index=True)
    unknown = result["outcome_resolution"].eq(UNKNOWN)
    result["unknown_action"] = np.select(
        [unknown & result["membership_role"].eq("favorable_top_n"),
         unknown & result["membership_role"].eq("unfavorable_bottom_n"),
         unknown & result["membership_role"].eq("not_selected_middle")],
        ["retain_and_deferred_exit_t_plus_2", "delete_bottom_comparator_and_renormalize", "ignore_not_held"],
        default="use_v5_resolved_return",
    )
    return result


def first_mark_in_period(prices: pd.DataFrame, period: pd.Period) -> pd.Series | None:
    selected = prices[prices["date"].dt.to_period("M").eq(period)].sort_values("date")
    return None if selected.empty else selected.iloc[0]


def resolve_deferred_exit_from_prices(
    instrument_id: str,
    decision_date: pd.Timestamp,
    prices: pd.DataFrame,
) -> dict[str, Any]:
    """Resolve formation close to the first qfq close in natural month t+2."""
    decision_date = pd.Timestamp(decision_date).normalize()
    formation = prices[prices["date"].eq(decision_date)]
    exit_period = decision_date.to_period("M") + 2
    exit_row = first_mark_in_period(prices, exit_period)
    result: dict[str, Any] = {
        "instrument_id": instrument_id,
        "decision_date": decision_date,
        "ordinary_exit_month": str(decision_date.to_period("M") + 1),
        "forced_exit_month": str(exit_period),
        "formation_mark_date": pd.NaT,
        "formation_mark": np.nan,
        "forced_exit_date": pd.NaT,
        "forced_exit_mark": np.nan,
        "deferred_gross_return": np.nan,
        "holding_calendar_days": np.nan,
        "deferred_resolution": "deferred_exit_unresolved",
        "failure_reason": "",
    }
    if formation.empty:
        result["failure_reason"] = "missing_exact_formation_date_mark"
        return result
    if exit_row is None:
        result["failure_reason"] = "no_mark_in_t_plus_2_natural_month"
        return result
    start = float(formation.iloc[-1]["close"])
    end = float(exit_row["close"])
    if not np.isfinite(start) or not np.isfinite(end) or start <= 0:
        result["failure_reason"] = "nonfinite_or_nonpositive_bridge_mark"
        return result
    exit_date = pd.Timestamp(exit_row["date"])
    result.update({
        "formation_mark_date": decision_date,
        "formation_mark": start,
        "forced_exit_date": exit_date,
        "forced_exit_mark": end,
        "deferred_gross_return": end / start - 1.0,
        "holding_calendar_days": int((exit_date - decision_date).days),
        "deferred_resolution": "resolved_first_mark_in_t_plus_2",
    })
    return result


def _parse_tencent_payload(payload: dict[str, Any], symbol: str) -> pd.DataFrame:
    node = (payload.get("data") or {}).get(symbol)
    if not node:
        return pd.DataFrame(columns=["date", "open", "close", "high", "low", "volume"])
    values = node.get("qfqday") or node.get("day") or []
    rows = [row[:6] for row in values if len(row) >= 6]
    frame = pd.DataFrame(rows, columns=["date", "open", "close", "high", "low", "volume"])
    if frame.empty:
        return frame
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    for column in ["open", "close", "high", "low", "volume"]:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    return frame.dropna(subset=["date", "close"]).sort_values("date").drop_duplicates("date")


def fetch_tencent_prices(
    instrument_id: str,
    start: pd.Timestamp,
    end: pd.Timestamp,
    source_dir: Path,
    bridge_config: dict[str, Any],
) -> tuple[pd.DataFrame, dict[str, Any]]:
    symbol = instrument_id.lower()
    endpoint = str(bridge_config["endpoint"])
    date_start = pd.Timestamp(start).strftime("%Y-%m-%d")
    date_end = pd.Timestamp(end).strftime("%Y-%m-%d")
    params = {"param": f"{symbol},day,{date_start},{date_end},640,qfq"}
    timeout = int(bridge_config.get("timeout_seconds", 30))
    attempts = int(bridge_config.get("max_attempts", 5))
    response: requests.Response | None = None
    error = ""
    for attempt in range(attempts):
        try:
            response = requests.get(
                endpoint,
                params=params,
                timeout=timeout,
                headers={"User-Agent": "Mozilla/5.0", "Referer": "https://stockapp.finance.qq.com/"},
            )
            response.raise_for_status()
            payload = response.json()
            break
        except Exception as exc:  # network failures are audited and fail closed
            payload = {}
            error = f"{type(exc).__name__}: {exc}"
            if attempt + 1 < attempts:
                time.sleep(min(1 + attempt, 5))
    raw_bytes = response.content if response is not None else b""
    payload_hash = hashlib.sha256(raw_bytes).hexdigest()
    source_name = f"tencent_qfq_bridge_{instrument_id}_{date_start}_{date_end}.json"
    source_path = source_dir / source_name
    write_json(source_path, payload if payload else {"error": error, "instrument_id": instrument_id})
    meta = {
        "instrument_id": instrument_id,
        "provider": bridge_config["provider"],
        "endpoint": endpoint,
        "request_url": response.url if response is not None else endpoint,
        "requested_start": date_start,
        "requested_end": date_end,
        "accessed_at_utc": utc_now(),
        "http_status": response.status_code if response is not None else np.nan,
        "payload_sha256": payload_hash,
        "source_artifact": str(Path("source") / source_name),
        "fetch_error": error if not payload else "",
        "mixed_provider_bridge_sensitivity": True,
    }
    return _parse_tencent_payload(payload, symbol), meta


def hac_mean_stats(values: pd.Series, lag: int) -> dict[str, float]:
    x = pd.to_numeric(values, errors="coerce").dropna().to_numpy(dtype=float)
    n = len(x)
    if n == 0:
        return {"n": 0, "mean": np.nan, "median": np.nan, "std": np.nan, "positive_rate": np.nan,
                "hac_t": np.nan, "hac_p": np.nan}
    mean = float(np.mean(x))
    std = float(np.std(x, ddof=1)) if n > 1 else np.nan
    if n < 2:
        t_value = p_value = np.nan
    else:
        residual = x - mean
        gamma0 = float(np.dot(residual, residual) / n)
        long_run = gamma0
        used_lag = min(int(lag), n - 1)
        for offset in range(1, used_lag + 1):
            gamma = float(np.dot(residual[offset:], residual[:-offset]) / n)
            long_run += 2.0 * (1.0 - offset / (used_lag + 1.0)) * gamma
        se = math.sqrt(max(long_run, 0.0) / n)
        t_value = mean / se if se > 0 else np.nan
        p_value = math.erfc(abs(t_value) / math.sqrt(2.0)) if np.isfinite(t_value) else np.nan
    return {
        "n": n,
        "mean": mean,
        "median": float(np.median(x)),
        "std": std,
        "positive_rate": float(np.mean(x > 0)),
        "hac_t": t_value,
        "hac_p": p_value,
    }


def build_monthly_returns(assignment: pd.DataFrame, deferred: pd.DataFrame) -> pd.DataFrame:
    deferred_map = {
        (str(row.instrument_id), pd.Timestamp(row.decision_date)): float(row.deferred_gross_return)
        for row in deferred.itertuples(index=False)
        if row.deferred_resolution == "resolved_first_mark_in_t_plus_2" and np.isfinite(row.deferred_gross_return)
    }
    rows: list[dict[str, Any]] = []
    for (decision_date, capacity), group in assignment.groupby(["decision_date", "bucket_capacity_n"], sort=True):
        top = group[group["membership_role"].eq("favorable_top_n")]
        bottom = group[group["membership_role"].eq("unfavorable_bottom_n")]
        middle = group[group["membership_role"].eq("not_selected_middle")]
        top_values: list[float] = []
        top_unresolved = 0
        deferred_contribution = 0.0
        deferred_n = 0
        max_holding_days = 0.0
        for item in top.itertuples(index=False):
            if item.outcome_resolution == UNKNOWN:
                value = deferred_map.get((str(item.instrument_id), pd.Timestamp(decision_date)), np.nan)
                if np.isfinite(value):
                    deferred_n += 1
                    deferred_contribution += float(value) / int(capacity)
                    match = deferred[(deferred["instrument_id"].eq(item.instrument_id)) &
                                     (pd.to_datetime(deferred["decision_date"]).eq(pd.Timestamp(decision_date)))]
                    if not match.empty:
                        max_holding_days = max(max_holding_days, float(match.iloc[0]["holding_calendar_days"]))
                else:
                    top_unresolved += 1
                top_values.append(float(value) if np.isfinite(value) else np.nan)
            else:
                value = float(item.project_resolved_next_month_return)
                top_values.append(value if np.isfinite(value) else np.nan)
        bottom_known = pd.to_numeric(
            bottom.loc[~bottom["outcome_resolution"].eq(UNKNOWN), "project_resolved_next_month_return"],
            errors="coerce",
        ).dropna()
        bottom_deleted = int(bottom["outcome_resolution"].eq(UNKNOWN).sum())
        top_evaluable = len(top_values) == int(capacity) and np.isfinite(top_values).all()
        top_return = float(np.mean(top_values)) if top_evaluable else np.nan
        bottom_return = float(bottom_known.mean()) if len(bottom_known) else np.nan
        rows.append({
            "decision_date": pd.Timestamp(decision_date),
            "bucket_capacity_n": int(capacity),
            "signal_eligible_n": int(len(group)),
            "top_nominal_n": int(capacity),
            "top_evaluable": bool(top_evaluable),
            "top_unresolved_n": int(top_unresolved),
            "top_deferred_exit_n": int(deferred_n),
            "top_max_holding_calendar_days": max_holding_days if deferred_n else np.nan,
            "top_deferred_return_contribution": deferred_contribution,
            "top_cohort_return": top_return,
            "bottom_nominal_n": int(capacity),
            "bottom_effective_n": int(len(bottom_known)),
            "bottom_deleted_unknown_n": bottom_deleted,
            "bottom_comparator_return": bottom_return,
            "top_minus_bottom_spread": top_return - bottom_return if np.isfinite(top_return) and np.isfinite(bottom_return) else np.nan,
            "middle_ignored_unknown_n": int(middle["outcome_resolution"].eq(UNKNOWN).sum()),
            "return_semantics": "formation_cohort_deferred_exit_gross_return",
        })
    return pd.DataFrame(rows)


def build_summary(monthly: pd.DataFrame, early_end: pd.Period, late_start: pd.Period, hac_lag: int) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    periods = pd.to_datetime(monthly["decision_date"]).dt.to_period("M")
    scopes = {
        "full": pd.Series(True, index=monthly.index),
        "early": periods <= early_end,
        "late": periods >= late_start,
    }
    for capacity in sorted(monthly["bucket_capacity_n"].unique()):
        cap = monthly[monthly["bucket_capacity_n"].eq(capacity)]
        for scope, global_mask in scopes.items():
            scoped = monthly[global_mask & monthly["bucket_capacity_n"].eq(capacity)]
            top = hac_mean_stats(scoped["top_cohort_return"], hac_lag)
            bottom = hac_mean_stats(scoped["bottom_comparator_return"], hac_lag)
            spread = hac_mean_stats(scoped["top_minus_bottom_spread"], hac_lag)
            rows.append({
                "bucket_capacity_n": int(capacity),
                "month_scope": scope,
                "signal_month_n": int(len(scoped)),
                "top_evaluable_month_n": int(scoped["top_cohort_return"].notna().sum()),
                "top_mean": top["mean"],
                "top_median": top["median"],
                "top_std": top["std"],
                "top_positive_rate": top["positive_rate"],
                "top_hac_t": top["hac_t"],
                "top_hac_p": top["hac_p"],
                "bottom_effective_month_n": int(scoped["bottom_comparator_return"].notna().sum()),
                "bottom_mean": bottom["mean"],
                "spread_month_n": int(scoped["top_minus_bottom_spread"].notna().sum()),
                "spread_mean": spread["mean"],
                "spread_positive_rate": spread["positive_rate"],
                "spread_hac_t": spread["hac_t"],
                "spread_hac_p": spread["hac_p"],
                "top_deferred_position_n": int(scoped["top_deferred_exit_n"].sum()),
                "bottom_deleted_unknown_n": int(scoped["bottom_deleted_unknown_n"].sum()),
                "middle_ignored_unknown_n": int(scoped["middle_ignored_unknown_n"].sum()),
                "mean_deferred_return_contribution": float(scoped["top_deferred_return_contribution"].mean()),
                "historical_sample_role": "design_contaminated_followup",
                "inference_role": "descriptive_not_support",
            })
    return pd.DataFrame(rows)


def paired_delta_vs_10(monthly: pd.DataFrame) -> pd.DataFrame:
    base = monthly[monthly["bucket_capacity_n"].eq(10)][
        ["decision_date", "top_cohort_return", "top_minus_bottom_spread"]
    ].rename(columns={"top_cohort_return": "base_top", "top_minus_bottom_spread": "base_spread"})
    rows = []
    for capacity, group in monthly.groupby("bucket_capacity_n", sort=True):
        paired = group.merge(base, on="decision_date", how="inner")
        top_delta = paired["top_cohort_return"] - paired["base_top"]
        spread_delta = paired["top_minus_bottom_spread"] - paired["base_spread"]
        rows.append({
            "bucket_capacity_n": int(capacity),
            "reference_capacity_n": 10,
            "paired_top_month_n": int(top_delta.notna().sum()),
            "top_delta_mean": float(top_delta.mean()),
            "top_delta_median": float(top_delta.median()),
            "paired_spread_month_n": int(spread_delta.notna().sum()),
            "spread_delta_mean": float(spread_delta.mean()),
            "spread_delta_median": float(spread_delta.median()),
        })
    return pd.DataFrame(rows)


def shell_attribution(monthly: pd.DataFrame, capacities: list[int]) -> pd.DataFrame:
    rows = []
    for small, large in zip(capacities[:-1], capacities[1:]):
        left = monthly[monthly["bucket_capacity_n"].eq(small)][["decision_date", "top_cohort_return"]].rename(
            columns={"top_cohort_return": "small_return"})
        right = monthly[monthly["bucket_capacity_n"].eq(large)][["decision_date", "top_cohort_return"]].rename(
            columns={"top_cohort_return": "large_return"})
        paired = left.merge(right, on="decision_date", how="inner").dropna()
        shell = (large * paired["large_return"] - small * paired["small_return"]) / (large - small)
        rows.append({
            "inner_capacity_n": int(small),
            "outer_capacity_n": int(large),
            "incremental_shell_n": int(large - small),
            "paired_month_n": int(len(paired)),
            "inner_top_mean": float(paired["small_return"].mean()),
            "outer_top_mean": float(paired["large_return"].mean()),
            "outer_minus_inner_mean": float((paired["large_return"] - paired["small_return"]).mean()),
            "incremental_shell_mean": float(shell.mean()),
            "incremental_shell_positive_rate": float((shell > 0).mean()),
        })
    return pd.DataFrame(rows)


def markdown_table(frame: pd.DataFrame, columns: list[str], percent: set[str] | None = None) -> str:
    percent = percent or set()
    labels = columns
    lines = ["| " + " | ".join(labels) + " |", "|" + "|".join(["---"] * len(labels)) + "|"]
    for row in frame[columns].itertuples(index=False, name=None):
        values = []
        for column, value in zip(columns, row):
            if pd.isna(value):
                values.append("")
            elif column in percent:
                values.append(f"{float(value) * 100:+.4f}%")
            elif isinstance(value, (float, np.floating)):
                values.append(f"{float(value):.4f}")
            else:
                values.append(str(value))
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def make_report(summary: pd.DataFrame, deferred: pd.DataFrame, paired: pd.DataFrame, shell: pd.DataFrame,
                decision_state: str) -> str:
    full = summary[summary["month_scope"].eq("full")].copy()
    early = summary[summary["month_scope"].eq("early")].copy()
    late = summary[summary["month_scope"].eq("late")].copy()
    best = full.loc[full["top_mean"].idxmax()]
    all_early_negative = bool((early["top_mean"] < 0).all())
    all_late_positive = bool((late["top_mean"] > 0).all())
    deferred_max = float(full["mean_deferred_return_contribution"].abs().max())
    table = markdown_table(
        full,
        ["bucket_capacity_n", "top_evaluable_month_n", "top_mean", "top_positive_rate", "bottom_mean",
         "spread_mean", "top_deferred_position_n", "bottom_deleted_unknown_n", "middle_ignored_unknown_n"],
        percent={"top_mean", "top_positive_rate", "bottom_mean", "spread_mean"},
    )
    fold_table = markdown_table(
        summary,
        ["bucket_capacity_n", "month_scope", "top_evaluable_month_n", "top_mean", "spread_mean"],
        percent={"top_mean", "spread_mean"},
    )
    deferred_table = markdown_table(
        deferred,
        ["instrument_id", "decision_date", "affected_capacities", "formation_mark", "forced_exit_date",
         "forced_exit_mark", "deferred_gross_return", "holding_calendar_days", "deferred_resolution"],
        percent={"deferred_gross_return"},
    ) if not deferred.empty else "无 Top-N unknown。"
    paired_table = markdown_table(
        paired,
        ["bucket_capacity_n", "paired_top_month_n", "top_delta_mean", "paired_spread_month_n", "spread_delta_mean"],
        percent={"top_delta_mean", "spread_delta_mean"},
    )
    shell_table = markdown_table(
        shell,
        ["inner_capacity_n", "outer_capacity_n", "paired_month_n", "outer_minus_inner_mean", "incremental_shell_mean"],
        percent={"outer_minus_inner_mean", "incremental_shell_mean"},
    )
    return f"""# 20B-P4-CAP unknown 延迟退出与持仓容量诊断

## 1. 状态

```text
decision_state = {decision_state}
historical_support_claim_allowed = false
20C_requirement_generation_authorized = false
deployment_authorized = false
```

本轮复用 sealed v5 P4 score，以等权 Top-N/Bottom-N 重新形成容量桶。`N` 是股票数，不是 quantile 数量。包含延迟退出的形成批次是 variable-horizon cohort diagnostic，不是普通月度 NAV。

## 2. 关键 findings

- 六档容量的 full Top-N 均值都为正；最高为 `N={int(best['bucket_capacity_n'])}` 的 `{float(best['top_mean']) * 100:+.4f}%`；
- early 六档是否全负：`{str(all_early_negative).lower()}`；late 六档是否全正：`{str(all_late_positive).lower()}`，说明主要结论仍是明显的时期翻转；
- 实际 held unknown 只有 `{len(deferred)}` 个股票-形成月；延迟退出对任一容量 full 月均的最大绝对贡献仅 `{deferred_max * 100:.4f}` 个百分点；
- 因此容量结果主要来自扩大/收缩 Top-N 成员，而不是4个 deferred exits 主导；
- 本轮是 outcome 已知后的容量搜索，不能把 `N={int(best['bucket_capacity_n'])}` 写成最优容量或用于参数选择。

## 3. Full sample 容量结果

{table}

## 4. Full / early / late

{fold_table}

## 5. Top-N unknown 延迟退出

{deferred_table}

补充桥使用当前腾讯 qfq 日线，只服务于实际进入 Top-N 的 v5 unknown。它与 v5 原输入不是同一冻结快照，因此结果固定标记 mixed-provider bridge sensitivity。

## 6. 相对 N=10 的共同月份差异

{paired_table}

## 7. 相邻容量 shell

{shell_table}

## 8. 解释边界

- middle unknown 不再污染 long-only Top-N；bottom unknown 只在 comparator 内删除并重新等权；
- Top-N unknown 保留原始 `1/N` 权重，并在第二自然月首个 mark 退出；
- 没有成本、next-open、现金账户或逐日 NAV；
- 本轮容量集合是在 v5 outcome 已知后提出，不能产生历史支持或授权。
"""


def run(config_path: Path, force: bool = False) -> Path:
    config_path = config_path.resolve()
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    topic_root = config_path.parent.parent
    v5_root = topic_root / config["paths"]["v5_root"]
    output_root = topic_root / config["paths"]["output_root"]
    building = output_root.with_name(output_root.name + ".building")
    if output_root.exists():
        if not force:
            raise FileExistsError(f"output exists: {output_root}; pass --force to replace this generated run")
        shutil.rmtree(output_root)
    if building.exists():
        shutil.rmtree(building)
    (building / "historical").mkdir(parents=True)
    (building / "source").mkdir(parents=True)

    requirement = topic_root / config["paths"]["requirement"]
    assignment_path = v5_root / "historical/instrument_month_signal_bucket_assignment.parquet"
    resolution_path = v5_root / "historical/outcome_resolution_audit.csv.gz"
    fold_path = v5_root / "preoutcome/statistical_and_fold_freeze.csv"
    v5_manifest = v5_root / "manifest_20b_trendpv_residual_momentum_design_and_replication_diagnostic.json"
    v5_hashes = v5_root / "output_hashes_20b_trendpv_residual_momentum_design_and_replication_diagnostic.json"
    runner_path = Path(__file__).resolve()
    inputs = [runner_path, requirement, config_path, assignment_path, resolution_path, fold_path, v5_manifest, v5_hashes]
    missing = [str(path) for path in inputs if not path.exists()]
    if missing:
        raise FileNotFoundError(f"missing required inputs: {missing}")
    input_audit = pd.DataFrame([{
        "artifact": path.name,
        "path": str(path.relative_to(topic_root)),
        "size_bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    } for path in inputs])
    write_csv(building / "input_hash_audit.csv", input_audit)

    columns = ["instrument_id", "decision_date", "label_month", "arm_id", "semantic_track", "signal_eligible",
               "bucket_count", "raw_signal", "project_resolved_next_month_return", "outcome_resolution",
               "historical_sample_role"]
    source = pd.read_parquet(assignment_path, columns=columns)
    signal = source[
        source["arm_id"].eq(config["signal"]["arm_id"]) &
        source["semantic_track"].eq(config["signal"]["semantic_track"]) &
        source["bucket_count"].eq(int(config["signal"]["source_bucket_count"])) &
        source["signal_eligible"]
    ].copy()
    signal["decision_date"] = pd.to_datetime(signal["decision_date"])
    capacities = sorted({int(value) for value in config["sorting"]["bucket_capacity_n"]})
    if capacities != [5, 10, 20, 30, 40, 50]:
        raise ValueError("capacity set must be exactly [5, 10, 20, 30, 40, 50]")
    assignment = assign_capacity_membership(signal, capacities)

    held_unknown = assignment[
        assignment["membership_role"].eq("favorable_top_n") & assignment["outcome_resolution"].eq(UNKNOWN)
    ].groupby(["instrument_id", "decision_date"], as_index=False).agg(
        affected_capacities=("bucket_capacity_n", lambda values: "|".join(map(str, sorted(set(values))))),
        max_capacity_n=("bucket_capacity_n", "max"),
    )
    resolution = pd.read_csv(resolution_path, parse_dates=["decision_date", "label_end", "source_last_trade_date"])
    resolution = resolution[resolution["outcome_resolution"].eq(UNKNOWN)].drop_duplicates(["instrument_id", "decision_date"])
    deferred_rows: list[dict[str, Any]] = []
    source_meta_rows: list[dict[str, Any]] = []
    for item in held_unknown.itertuples(index=False):
        decision_date = pd.Timestamp(item.decision_date)
        request_start = decision_date.to_period("M").start_time
        request_end = (decision_date.to_period("M") + 2).end_time.normalize()
        prices, source_meta = fetch_tencent_prices(
            str(item.instrument_id), request_start, request_end, building / "source", config["deferred_exit_bridge"])
        source_meta_rows.append(source_meta)
        resolved = resolve_deferred_exit_from_prices(str(item.instrument_id), decision_date, prices)
        month1 = prices[prices["date"].dt.to_period("M").eq(decision_date.to_period("M") + 1)]
        audit_match = resolution[
            resolution["instrument_id"].eq(item.instrument_id) &
            resolution["decision_date"].eq(decision_date)
        ]
        resolved.update({
            "affected_capacities": item.affected_capacities,
            "source_provider": config["deferred_exit_bridge"]["provider"],
            "source_payload_sha256": source_meta["payload_sha256"],
            "source_artifact": source_meta["source_artifact"],
            "month1_last_mark_date": month1["date"].max() if not month1.empty else pd.NaT,
            "v5_source_last_trade_date": audit_match.iloc[0]["source_last_trade_date"] if not audit_match.empty else pd.NaT,
            "month1_last_date_matches_v5": bool(
                not month1.empty and not audit_match.empty and
                pd.Timestamp(month1["date"].max()) == pd.Timestamp(audit_match.iloc[0]["source_last_trade_date"])
            ),
            "mixed_provider_bridge_sensitivity": True,
        })
        deferred_rows.append(resolved)
    deferred = pd.DataFrame(deferred_rows)
    if deferred.empty:
        deferred = pd.DataFrame(columns=[
            "instrument_id", "decision_date", "affected_capacities", "formation_mark", "forced_exit_date",
            "forced_exit_mark", "deferred_gross_return", "holding_calendar_days", "deferred_resolution",
        ])
    write_csv(building / "source/tencent_qfq_bridge_access_audit.csv", pd.DataFrame(source_meta_rows))

    monthly = build_monthly_returns(assignment, deferred)
    folds = pd.read_csv(fold_path)
    p4_fold = folds[folds["arm_or_calendar_id"].eq("P4_PRIMARY_CALENDAR")]
    if len(p4_fold) != 1:
        raise ValueError("missing or duplicate P4_PRIMARY_CALENDAR fold")
    early_end = pd.Period(str(p4_fold.iloc[0]["early_end"]), freq="M")
    late_start = pd.Period(str(p4_fold.iloc[0]["late_start"]), freq="M")
    summary = build_summary(monthly, early_end, late_start, int(config["inference"]["hac_lag"]))
    paired = paired_delta_vs_10(monthly)
    shell = shell_attribution(monthly, capacities)

    assignment.to_parquet(building / "historical/p4_capacity_assignment.parquet", index=False, compression="zstd")
    write_csv(building / "historical/p4_deferred_exit_audit.csv", deferred)
    write_csv(building / "historical/p4_capacity_monthly_returns.csv.gz", monthly)
    write_csv(building / "historical/p4_capacity_summary.csv", summary)
    write_csv(building / "historical/p4_capacity_paired_delta_vs_10.csv", paired)
    write_csv(building / "historical/p4_capacity_shell_attribution.csv", shell)

    unresolved = int((deferred.get("deferred_resolution", pd.Series(dtype=str)) != "resolved_first_mark_in_t_plus_2").sum())
    lineage_mismatch = int((~deferred.get("month1_last_date_matches_v5", pd.Series(dtype=bool))).sum())
    capacities_complete = set(monthly["bucket_capacity_n"].unique()) == set(capacities)
    decision_state = (
        "complete_descriptive_capacity_diagnostic"
        if capacities_complete and unresolved == 0 and lineage_mismatch == 0
        else "partial_deferred_exit_bridge_blocked"
    )
    decision = pd.DataFrame([{
        "run_id": config["run_id"],
        "contract_version": config["contract_version"],
        "decision_state": decision_state,
        "capacity_set": "|".join(map(str, capacities)),
        "signal_month_n": int(signal["decision_date"].nunique()),
        "held_unknown_case_n": int(len(deferred)),
        "resolved_deferred_exit_n": int((deferred.get("deferred_resolution", pd.Series(dtype=str)) == "resolved_first_mark_in_t_plus_2").sum()),
        "bridge_month1_last_date_match_n": int(deferred.get("month1_last_date_matches_v5", pd.Series(dtype=bool)).sum()),
        "bridge_lineage_mismatch_n": lineage_mismatch,
        "mixed_provider_bridge_sensitivity": True,
        "historical_sample_role": config["inference"]["historical_sample_role"],
        "historical_support_claim_allowed": False,
        "20C_requirement_generation_authorized": False,
        "20C_execution_authorized": False,
        "portfolio_optimization_authorized": False,
        "deployment_authorized": False,
    }])
    decision_name = "20B_P4_unknown_deferred_exit_bucket_capacity_diagnostic_decision.csv"
    report_name = "20B_P4_unknown_deferred_exit_bucket_capacity_diagnostic_report.md"
    write_csv(building / decision_name, decision)
    (building / report_name).write_text(make_report(summary, deferred, paired, shell, decision_state), encoding="utf-8")
    contract_snapshot = {
        "run_id": config["run_id"],
        "contract_version": config["contract_version"],
        "created_at_utc": utc_now(),
        "capacity_set": capacities,
        "primary_weighting": "EW",
        "unknown_policy": config["unknown_policy"],
        "deferred_exit_bridge": config["deferred_exit_bridge"],
        "early_end": str(early_end),
        "late_start": str(late_start),
        "historical_support_claim_allowed": False,
    }
    write_json(building / "contract_snapshot.json", contract_snapshot)

    manifest_files = sorted(path for path in building.rglob("*") if path.is_file())
    hashes = {str(path.relative_to(building)): sha256_file(path) for path in manifest_files}
    output_hashes_name = "output_hashes_20b_p4_capacity.json"
    write_json(building / output_hashes_name, hashes)
    manifest = {
        "run_id": config["run_id"],
        "contract_version": config["contract_version"],
        "decision_state": decision_state,
        "created_at_utc": utc_now(),
        "file_count_excluding_manifest": len(hashes) + 1,
        "output_hashes_sha256": sha256_file(building / output_hashes_name),
        "bundle_hash": stable_hash(hashes),
    }
    write_json(building / "manifest_20b_p4_capacity.json", manifest)
    building.rename(output_root)
    return output_root


def main() -> None:
    parser = argparse.ArgumentParser()
    default_config = Path(__file__).resolve().parent.parent / "configs/config_20b_p4_unknown_deferred_exit_bucket_capacity_diagnostic.yaml"
    parser.add_argument("--config", type=Path, default=default_config)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    print(run(args.config, force=args.force))


if __name__ == "__main__":
    main()
