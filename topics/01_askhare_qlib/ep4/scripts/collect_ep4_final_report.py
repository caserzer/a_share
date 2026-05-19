#!/usr/bin/env python3
"""
Generate the EP4 final report from discussion notes and validated artifacts.

This script intentionally does not rerun any experiment. It reads frozen
reports/manifests under ep4/outputs and writes ep4/FINAL_REPORT.md.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import pandas as pd


EP4_DIR = Path(__file__).resolve().parents[1]
TOPIC_ROOT = EP4_DIR.parent
OUTPUT_PATH = EP4_DIR / "FINAL_REPORT.md"


def repo_path(rel_path: str) -> Path:
    return TOPIC_ROOT / rel_path


def read_csv(rel_path: str) -> pd.DataFrame:
    path = repo_path(rel_path)
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def read_json(rel_path: str) -> dict[str, Any]:
    path = repo_path(rel_path)
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def get_first(df: pd.DataFrame, column: str, default: Any = "") -> Any:
    if df.empty or column not in df.columns:
        return default
    value = df.iloc[0][column]
    if pd.isna(value):
        return default
    return value


def pct(value: Any, digits: int = 2) -> str:
    if value == "" or value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
        return f"{float(value) * 100:.{digits}f}%"
    except Exception:
        return str(value)


def num(value: Any, digits: int = 2) -> str:
    if value == "" or value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
        if float(value).is_integer():
            return f"{int(value):,}"
        return f"{float(value):,.{digits}f}"
    except Exception:
        return str(value)


def signed_pct(value: Any, digits: int = 2) -> str:
    if value == "" or value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
        return f"{float(value) * 100:+.{digits}f}%"
    except Exception:
        return str(value)


def ratio_with_pct(value: Any, ratio_digits: int = 3, pct_digits: int = 1) -> str:
    if value == "" or value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
        numeric = float(value)
        return f"{numeric:.{ratio_digits}f} (={numeric * 100:.{pct_digits}f}%)"
    except Exception:
        return str(value)


def md_table(rows: list[dict[str, Any]], columns: list[str] | None = None) -> str:
    if not rows:
        return "_无可用结构化数据_"
    frame = pd.DataFrame(rows)
    if columns:
        frame = frame[columns]
    return frame.to_markdown(index=False)


def manifest_status(rel_path: str, key: str = "final_decision", default: str = "") -> str:
    data = read_json(rel_path)
    value = data.get(key)
    if value is None:
        value = data.get("validation_status", default)
    return str(value) if value is not None else default


def csv_decision(rel_path: str, key: str = "final_decision") -> str:
    df = read_csv(rel_path)
    return str(get_first(df, key, ""))


def gate_value(
    df: pd.DataFrame,
    *,
    gate_id: str | None = None,
    metric_name: str | None = None,
    split: str | None = None,
    column: str = "metric_value",
    default: Any = "",
) -> Any:
    if df.empty:
        return default
    mask = pd.Series(True, index=df.index)
    if gate_id is not None and "gate_id" in df.columns:
        mask &= df["gate_id"].eq(gate_id)
    if metric_name is not None and "metric_name" in df.columns:
        mask &= df["metric_name"].eq(metric_name)
    if split is not None and "split" in df.columns:
        mask &= df["split"].eq(split)
    sub = df.loc[mask]
    if sub.empty or column not in sub.columns:
        return default
    value = sub.iloc[0][column]
    return default if pd.isna(value) else value


def build_report() -> str:
    created_at = datetime.now(ZoneInfo("Asia/Shanghai")).isoformat()

    r01_gate = read_csv(
        "ep4/outputs/r01_high_recall_probe_fail_fast_v3_post30_profile_seed/reports/r01_gate_audit.csv"
    )
    r01_1_gate = read_csv(
        "ep4/outputs/r01_1_emission_throttled_cooling_entry_probe_fail_fast/reports/r01_1_gate_audit.csv"
    )
    r02_gate = read_csv("ep4/outputs/r02_evidence_family_discovery_v1/reports/r02_gate_audit.csv")
    r02_v2_gate = read_csv(
        "ep4/outputs/r02_winner_anchored_structure_profile_discovery_v2/reports/r02_v2_gate_audit.csv"
    )
    r03a_grid = read_csv(
        "ep4/outputs/r03a_probability_survival_step_feasibility_v1/reports/r03a_candidate_grid_train_selection.csv"
    )
    r03b_seed = read_csv(
        "ep4/outputs/r03b_signal_sequence_big_winner_path_diagnostic_v1/reports/r03b_seed_episode_label_summary.csv"
    )
    r03e_filtered = read_csv(
        "ep4/outputs/r03e_family_signal_bad_shape_filter_diagnostic_v1/reports/r03e_filtered_outcome_summary.csv"
    )
    r04b_final = read_csv(
        "ep4/outputs/r04b_fixed_entry_hold_exit_risk_budget_cta_diagnostic_v1/reports/r04b_final_decision.csv"
    )
    r04c_gate = read_csv("ep4/outputs/r04c_candidate_pool_scanner_v1/reports/r04c_validation_gate_audit.csv")
    r04d_gate = read_csv(
        "ep4/outputs/r04d_volume_money_relative_improvement_risk_budget_replay_v1/reports/r04d_validation_gate_audit.csv"
    )
    r04e_policy = read_csv(
        "ep4/outputs/r04e_union_pool_portfolio_level_diagnostic_v1/reports/r04e_portfolio_policy_summary.csv"
    )
    r05_preflight_gate = read_csv(
        "ep4/outputs/r05_preflight_alpha_pool_quick_feasibility_v1/reports/r05_preflight_gate_audit.csv"
    )
    r05b_final = read_csv(
        "ep4/outputs/r05b_sleeve_allocator_exposure_composition_diagnostic_v1/reports/r05b_final_decision.csv"
    )
    r05b_gate = read_csv(
        "ep4/outputs/r05b_sleeve_allocator_exposure_composition_diagnostic_v1/reports/r05b_validation_gate_audit.csv"
    )
    r05b_risk_on = read_csv(
        "ep4/outputs/r05b_sleeve_allocator_exposure_composition_diagnostic_v1/reports/r05b_risk_on_full_exposure_audit.csv"
    )

    r03b_all = r03b_seed.loc[r03b_seed["split"].eq("all")].iloc[0] if not r03b_seed.empty else {}

    r03e_primary = pd.DataFrame()
    if not r03e_filtered.empty:
        r03e_primary = r03e_filtered.loc[
            r03e_filtered["split"].isin(["validation", "robustness"])
            & r03e_filtered["event_scope"].eq("r02_signal_episode_start")
            & r03e_filtered["event_stage"].eq("r02_episode_start")
            & r03e_filtered["family_group"].eq("all_families_dedup_weighted")
            & r03e_filtered["outcome_anchor"].eq("filter_decision_next_open_anchor")
            & r03e_filtered["denominator_policy"].eq("baseline_1")
            & r03e_filtered["filter_policy"].isin(["no_badshape_filter_t10_survivor", "drop_score_ge5"])
        ]

    r04e_validation_best = pd.DataFrame()
    if not r04e_policy.empty:
        r04e_validation_best = (
            r04e_policy.loc[r04e_policy["split"].eq("validation")]
            .sort_values("period_compounded_return", ascending=False)
            .head(3)
        )

    terminal = get_first(r05b_final, "final_decision", "unknown")
    terminal_reason = get_first(r05b_final, "blocking_reason", "")
    allowed_next = get_first(r05b_final, "allowed_next_requirement", "")
    r05b_cash_allocator = pd.DataFrame()
    if not r05b_gate.empty:
        r05b_cash_allocator = r05b_gate.loc[
            r05b_gate["allocator_policy_id"].eq("market_state_cash_allocator_v1")
        ]

    discussion_rows = [
        {
            "文件": "discussion.md",
            "核心问题": "EP4 从“预测大 winner”改写为“管理右尾 episode 期权”。",
            "对实验设计的影响": "先用 high-recall probe 找到足够覆盖，再要求 fail-fast、延迟入场和 no-harm 约束。",
        },
        {
            "文件": "discussion2.md",
            "核心问题": "后续信号是 evidence accumulation，不天然等于新入场点。",
            "对实验设计的影响": "要求 action-time prior、30D build window、LR/posterior/correlation/risk-budget 审计。",
        },
        {
            "文件": "discussion3.md",
            "核心问题": "同日 evidence bundle 与 survival/fresh evidence 容易产生 denominator 偏差。",
            "对实验设计的影响": "R03a 被收紧为 probability-only feasibility，禁止把 winner-anchored 覆盖直接转成 entry rule。",
        },
        {
            "文件": "discussion4.md",
            "核心问题": "R03 后不再寻找新 anchor，而转向 dynamic exposure eligibility 与风险预算。",
            "对实验设计的影响": "R04 系列改测 exposure/regime/exit/portfolio 层能否把左尾管理转成 OOS 正期望。",
        },
        {
            "文件": "discussion5.md",
            "核心问题": "R04e/R05 后必须区分 alpha pool、relative-improvement pool 与 sleeve allocator。",
            "对实验设计的影响": "R05b 成为 EP4 终局诊断：risk-on full exposure hard kill 先于 allocator gate。",
        },
    ]

    experiment_rows = [
        {
            "阶段": "R01",
            "问题": "高召回 seed + fail-fast 是否能形成可控 probe?",
            "最终状态": "stop_ep4_r01_path",
            "关键证据": (
                f"validation seed day rate {pct(gate_value(r01_gate, gate_id='seed_density_day_cap', split='validation'))} "
                f"> cap {pct(gate_value(r01_gate, gate_id='seed_density_day_cap', split='validation', column='threshold'))}"
            ),
            "结论": "覆盖有了，但触发密度过高，不能直接进入 R02/R03 作为生产入口。",
        },
        {
            "阶段": "R01.1",
            "问题": "throttle/cooling 能否修复 R01 的触发密度?",
            "最终状态": "archive / diagnostic",
            "关键证据": (
                f"train emitted seed day rate {pct(gate_value(r01_1_gate, gate_id='candidate_emitted_seed_day_rate', split='train'))}; "
                f"probe entry day rate {pct(gate_value(r01_1_gate, gate_id='candidate_probe_entry_day_rate', split='train'))}"
            ),
            "结论": "密度可压低，但这是流量控制，不等价于 action-time alpha。",
        },
        {
            "阶段": "R02",
            "问题": "evidence family discovery 能否给出稳定非 baseline family?",
            "最终状态": "archive_family_discovery_no_r03",
            "关键证据": f"hard gates failed {int((r02_gate['status'] == 'failed').sum()) if not r02_gate.empty else 'NA'} / {len(r02_gate)}",
            "结论": "同日 family 组合未证明稳定 LR/EV，也不满足 execution feasible。",
        },
        {
            "阶段": "R02 V2",
            "问题": "winner-anchored structure profile 能否稳定外推?",
            "最终状态": "coverage/profile diagnostic only",
            "关键证据": (
                f"R01 reference overlap {pct(gate_value(r02_v2_gate, gate_id='r01_v3_reference_overlap_rate', column='actual'))}; "
                "validation LR/EV gates 均未通过"
            ),
            "结论": "可解释 winner 结构，但不能作为 action-time selection rule。",
        },
        {
            "阶段": "R03a",
            "问题": "probability-survival step 是否有稳定可选 bucket?",
            "最终状态": "blocked_no_stable_candidate_bucket",
            "关键证据": (
                f"candidate grid {num(get_first(r03a_grid, 'train_grid_total_candidate_count', 0))}; "
                f"train eligible after gate {num(get_first(r03a_grid, 'train_eligible_candidate_count_after_gate', 0))}"
            ),
            "结论": "survival checkpoint 只能作为风险过滤诊断，不能证明独立 entry edge。",
        },
        {
            "阶段": "R03b",
            "问题": "fresh signal sequence 是否确认 big-winner path?",
            "最终状态": "descriptive_sequence_diagnostic_complete",
            "关键证据": (
                f"seed episodes {num(r03b_all.get('seed_episode_count', 0))}; "
                f"fresh episodes {num(r03b_all.get('fresh_episode_count', 0))}; "
                f"failed before first fresh {num(r03b_all.get('failed_before_first_primary_fresh_count', 0))}"
            ),
            "结论": "fresh-count 能解释路径状态，但 survival conditioning 很重，不能直接当入场信号。",
        },
        {
            "阶段": "R03c",
            "问题": "kth fresh / price-aware pooling 是否给出新买点?",
            "最终状态": manifest_status(
                "ep4/outputs/r03c_price_aware_kth_fresh_family_set_pooling_diagnostic_v1/manifests/r03c_price_aware_kth_fresh_family_set_pooling_validation.json"
            ),
            "关键证据": "高 wait-return 行 seed-anchor 强，但 fresh-anchor P_good 低、P_bad 高。",
            "结论": "后续 fresh 更像 late confirmation，不是更好的 fresh-entry alpha。",
        },
        {
            "阶段": "R03d",
            "问题": "family 顺序 / stage role 是否有增量?",
            "最终状态": manifest_status(
                "ep4/outputs/r03d_family_order_stage_role_diagnostic_v1/manifests/r03d_family_order_stage_role_validation.json"
            ),
            "关键证据": "prefix/order denominator 塌缩；pair-order weighted signed lift 约为 0。",
            "结论": "stage role 可作为状态变量；family order 不应进入 entry/add/sizing 规则。",
        },
        {
            "阶段": "R03e",
            "问题": "bad-shape filter 能否剔除 family 信号后的坏路径?",
            "最终状态": manifest_status(
                "ep4/outputs/r03e_family_signal_bad_shape_filter_diagnostic_v1/manifests/r03e_family_signal_bad_shape_filter_validation.json"
            ),
            "关键证据": "drop_score_ge5 在 validation/robustness 均未降低 P_bad，big-winner rate 下降。",
            "结论": "形态坏分不是稳定单调风险过滤器。",
        },
        {
            "阶段": "R04",
            "问题": "RPS + market/industry regime 能否定义 exposure eligibility?",
            "最终状态": manifest_status(
                "ep4/outputs/r04_dynamic_momentum_exposure_eligibility_audit_v1/manifests/r04_dynamic_momentum_exposure_eligibility_validation.json"
            ),
            "关键证据": "single_momentum_rps 有右尾信息，但 regime lift 受 denominator shrink 与 split 不稳定限制。",
            "结论": "descriptive-only，不能发 production exposure gate。",
        },
        {
            "阶段": "R04b",
            "问题": "fixed-entry 后 exit/risk-budget 能否稳定提升收益?",
            "最终状态": get_first(r04b_final, "final_decision", ""),
            "关键证据": (
                f"validation net delta vs hold_120d_no_exit {signed_pct(get_first(r04b_final, 'validation_net_return_mean_delta_vs_hold120'))}; "
                f"robustness same baseline {signed_pct(get_first(r04b_final, 'robustness_net_return_mean_delta_vs_hold120'))}"
            ),
            "结论": "左尾可压缩，但 robustness 均值收益不稳。",
        },
        {
            "阶段": "R04c",
            "问题": "candidate pool scanner 能否找到绝对正期望池?",
            "最终状态": csv_decision("ep4/outputs/r04c_candidate_pool_scanner_v1/reports/r04c_final_decision.csv"),
            "关键证据": f"validation candidate pools {len(r04c_gate)}, passed {(r04c_gate['validation_gate_pass'] == True).sum() if not r04c_gate.empty else 'NA'}",
            "结论": "relative improvement 存在，但绝对 validation net 仍为负。",
        },
        {
            "阶段": "R04d",
            "问题": "volume_money 相对改善池能否经 risk-budget 转正?",
            "最终状态": csv_decision(
                "ep4/outputs/r04d_volume_money_relative_improvement_risk_budget_replay_v1/reports/r04d_final_decision.csv"
            ),
            "关键证据": f"train-selected validation pass {(r04d_gate['validation_gate_pass'] == True).sum() if not r04d_gate.empty else 'NA'} / {len(r04d_gate)}",
            "结论": "简单风险管理压左尾，但 winner retention 与正收益门槛无法同时满足。",
        },
        {
            "阶段": "R04e",
            "问题": "union pool / portfolio-level replay 能否消除单池弱点?",
            "最终状态": manifest_status(
                "ep4/outputs/r04e_union_pool_portfolio_level_diagnostic_v1/manifests/r04e_union_pool_portfolio_level_validation.json"
            ),
            "关键证据": "gate0_stop_low_quality_union；validation 最好组合仍未通过。",
            "结论": "组合层面没有把弱 alpha 拼成可用 portfolio；还有伪分散/活跃库存拥挤问题。",
        },
        {
            "阶段": "R05 Preflight",
            "问题": "是否存在可作为 standalone alpha pool 的候选?",
            "最终状态": manifest_status(
                "ep4/outputs/r05_preflight_alpha_pool_quick_feasibility_v1/manifests/r05_preflight_alpha_pool_quick_feasibility_validation.json"
            ),
            "关键证据": f"candidate pass count {read_json('ep4/outputs/r05_preflight_alpha_pool_quick_feasibility_v1/manifests/r05_preflight_alpha_pool_quick_feasibility_validation.json').get('candidate_pass_count', '')}",
            "结论": "没有候选满足绝对收益/样本底线。",
        },
        {
            "阶段": "R05b",
            "问题": "cash allocator + secondary sleeve 是否能保留右尾并改善风险?",
            "最终状态": terminal,
            "关键证据": terminal_reason,
            "结论": "decision driver 是 risk-on full exposure validation 为负；secondary 不激活和 allocator right-tail retention 失败只是附带证据。",
        },
    ]

    r03e_rows: list[dict[str, Any]] = []
    if not r03e_primary.empty:
        for _, row in r03e_primary.iterrows():
            r03e_rows.append(
                {
                    "split": row["split"],
                    "policy": row["filter_policy"],
                    "baseline_n": num(row["baseline_event_count"]),
                    "passed_n": num(row["passed_event_count"]),
                    "P_good": pct(row["p_good"]),
                    "P_bad": pct(row["p_bad"]),
                    "big_winner_rate": pct(row["big_winner_rate"]),
                    "delta_P_bad": signed_pct(row["delta_p_bad_vs_parent"]),
                    "delta_big_winner": signed_pct(row["delta_big_winner_rate_vs_parent"]),
                }
            )

    r04c_rows: list[dict[str, Any]] = []
    if not r04c_gate.empty:
        for _, row in r04c_gate.iterrows():
            r04c_rows.append(
                {
                    "pool_id": row["pool_id"],
                    "validation_net": signed_pct(row["net_return_mean"]),
                    "matched_delta": signed_pct(row["net_return_mean_delta_vs_matched_baseline_A"]),
                    "p10_delta": signed_pct(row["p10_delta_vs_matched_baseline_A"]),
                    "loss<=-5_delta": signed_pct(row["loss_le_minus5_delta_vs_matched_baseline_A"]),
                    "gate_pass": str(bool(row["validation_gate_pass"])),
                }
            )

    r04d_rows: list[dict[str, Any]] = []
    if not r04d_gate.empty:
        for _, row in r04d_gate.head(8).iterrows():
            r04d_rows.append(
                {
                    "rank": int(row["validation_selected_rank"]),
                    "policy_id": row["policy_id"],
                    "validation_net": signed_pct(row["net_return_mean"]),
                    "delta_vs_hold120": signed_pct(row["net_return_mean_delta_vs_volume_money_hold120"]),
                    "p10_delta": signed_pct(row["p10_delta_vs_volume_money_hold120"]),
                    "retention": pct(row["max_gain50_retention_vs_volume_money_hold120"]),
                    "failed_gate": row["failed_gate_list"],
                }
            )

    r04e_rows: list[dict[str, Any]] = []
    if not r04e_validation_best.empty:
        for _, row in r04e_validation_best.iterrows():
            r04e_rows.append(
                {
                    "portfolio_id": row["portfolio_id"],
                    "cap": row["daily_active_cap"],
                    "policy_id": row["policy_id"],
                    "period_return": signed_pct(row["period_compounded_return"]),
                    "monthly_p10": signed_pct(row["monthly_return_p10"]),
                    "max_drawdown": pct(row["max_drawdown"]),
                    "active_count_p95": num(row["active_count_p95"]),
                }
            )

    r05_preflight_rows: list[dict[str, Any]] = []
    if not r05_preflight_gate.empty:
        for _, row in r05_preflight_gate.iterrows():
            r05_preflight_rows.append(
                {
                    "candidate": row["candidate_id"],
                    "validation_events": num(row["validation_event_count"]),
                    "complete_share": pct(row["validation_complete_event_share"]),
                    "hold20_mean": signed_pct(row["validation_hold20_net_mean"]),
                    "hold20_median": signed_pct(row["validation_hold20_net_median"]),
                    "hold20_p10": signed_pct(row["validation_hold20_net_p10"]),
                    "gate_status": row["preflight_gate_status"],
                    "blocking": row["blocking_reason"],
                }
            )

    r05b_risk_rows: list[dict[str, Any]] = []
    if not r05b_risk_on.empty:
        for _, row in r05b_risk_on.iterrows():
            r05b_risk_rows.append(
                {
                    "split": row["split"],
                    "risk_on_share": pct(row["risk_on_day_share"]),
                    "full_exposure_return": signed_pct(row["full_exposure_primary_period_return"]),
                    "risk_on_full_exposure_return": signed_pct(row["risk_on_full_exposure_period_return"]),
                    "risk_on_daily_mean": signed_pct(row["risk_on_full_exposure_daily_mean"], digits=2),
                    "gate": row["risk_on_full_exposure_gate_status"],
                    "blocking": row["blocking_reason"] if not pd.isna(row["blocking_reason"]) else "",
                }
            )

    r05b_gate_rows: list[dict[str, Any]] = []
    if not r05b_gate.empty:
        for _, row in r05b_gate.iterrows():
            r05b_gate_rows.append(
                {
                    "policy": row["allocator_policy_id"],
                    "validation_status": row["validation_gate_status"],
                    "period_return": signed_pct(row["period_return"]),
                    "monthly_p10_delta": signed_pct(row["monthly_p10_delta_vs_full_exposure"]),
                    "max_dd_delta": signed_pct(row["max_drawdown_delta_vs_full_exposure"]),
                    "avg_gross": pct(row["average_gross_exposure"]),
                    "cash_only": pct(row["cash_only_day_share"]),
                    "right_tail_retention": ratio_with_pct(row["right_tail_retention_vs_full_exposure"]),
                    "right_tail_status": row["right_tail_gate_status"],
                    "blocking": row["blocking_reason"] if not pd.isna(row["blocking_reason"]) else "",
                }
            )

    source_rows = [
        {"用途": "讨论主线", "路径": "ep4/discussion.md ... ep4/discussion5.md"},
        {"用途": "R01 seed/probe", "路径": "ep4/outputs/r01_high_recall_probe_fail_fast_v3_post30_profile_seed/"},
        {"用途": "R02/R02.1 priors", "路径": "ep4/outputs/r02_evidence_family_discovery_v1/; ep4/outputs/r02_1_prior_probability_diagnostic_v1/"},
        {"用途": "R03a-R03e path diagnostics", "路径": "ep4/outputs/r03a_* ... ep4/outputs/r03e_*"},
        {"用途": "R04-R04e exposure/portfolio", "路径": "ep4/outputs/r04_dynamic_* ... ep4/outputs/r04e_union_pool_portfolio_level_diagnostic_v1/"},
        {"用途": "R05/R05b terminal", "路径": "ep4/outputs/r05_preflight_alpha_pool_quick_feasibility_v1/; ep4/outputs/r05b_sleeve_allocator_exposure_composition_diagnostic_v1/"},
    ]

    lines: list[str] = []
    lines.append("# EP4 Final Report: Right-Tail Episode Management Research Closure")
    lines.append("")
    lines.append(f"Generated at: `{created_at}`")
    lines.append("")
    lines.append("## 0. Executive Summary")
    lines.append("")
    lines.append(
        "EP4 的研究问题从一开始就不是“再找一个单点 alpha”，而是：在 EP2/EP3 已经暴露出 "
        "winner 稀疏、路径噪声大、事后解释强于事前可交易性的背景下，是否能把 big-winner "
        "视作一个右尾 episode option，通过高召回 probe、证据积累、失败早停、动态 exposure、"
        "exit/risk-budget 和 sleeve allocation，形成一个可验证、可执行、可通过 OOS 的体系。"
    )
    lines.append("")
    lines.append(
        f"最终答案是否定的。当前终局 artifact 为 R05b，final decision = `{terminal}`，"
        f"blocking reason = `{terminal_reason}`，terminal stop = `{get_first(r05b_final, 'terminal_stop_flag', '')}`，"
        f"allowed next = `{allowed_next}`。这表示 EP4 不应继续在同一 evidence family / 同一 long-only "
        "A-share episode 框架里追加 R05c/R05d 细调；后续只有在研究框架发生实质改变时，才进入 EP5 escape hatch。"
    )
    lines.append("")
    lines.append("最核心的失败链条是：")
    lines.append("")
    lines.append(
        "1. R01/R02 证明了覆盖和结构解释可以做出来，但 action-time 的触发密度、LR/EV、execution feasibility 不够。"
    )
    lines.append(
        "2. R03a-R03e 证明了 sequence、fresh evidence、stage role、bad-shape 都有描述价值，但没有变成稳定 entry/add/sizing edge。"
    )
    lines.append(
        "3. R04-R04e 证明了 left-tail compression、relative improvement、portfolio union 都不能把 validation 变成正期望。"
    )
    lines.append(
        "4. R05/R05b 证明了 standalone alpha pool 不过 preflight；R05b 的正式终止驱动是 risk-on full exposure validation 为负，allocator/right-tail/secondary gate 只提供附带证据。"
    )
    lines.append("")
    lines.append("因此 EP4 的价值不是找到可上线策略，而是把一条看似有很多局部证据的研究线收敛到可审计的终止条件。")
    lines.append("")

    lines.append("## 1. Discussion Evolution")
    lines.append("")
    lines.append(md_table(discussion_rows))
    lines.append("")
    lines.append(
        "这五份 discussion 的共同收敛点是：不能把 winner-anchored 观察、survival 后验、fresh-count 累积、"
        "形态解释或 portfolio 组合，直接翻译成交易规则。每一步都必须回到 action-time、next executable price、"
        "validation-first、robustness-readonly 的约束下重新验证。"
    )
    lines.append("")

    lines.append("## 2. Experiment Timeline")
    lines.append("")
    lines.append(md_table(experiment_rows))
    lines.append("")
    lines.append(
        "Timeline 里的 R01 `stop_ep4_r01_path` 不表示 R02-R05 可以把 R01/R01.1 当作 production entry 继续推进。"
        "R02 之后沿用的是已冻结的 evidence sampling / family signal / path-query artifacts，用于诊断 family、path、portfolio 与 allocator 问题；"
        "这些下游实验不把 R01 或 R01.1 升级为 production-grade probe。"
    )
    lines.append("")
    lines.append(
        "R04 命名说明：本轮 EP4 没有单独发布 `R04a` artifact；`R04 Dynamic Momentum Exposure Eligibility Audit V1` "
        "就是 exposure/regime 方向的首个 R04 artifact，后续扩展从 R04b 开始。"
    )
    lines.append("")

    lines.append("## 3. Stage Findings")
    lines.append("")
    lines.append("### 3.1 R01/R02: Coverage Is Not Entry Quality")
    lines.append("")
    lines.append(
        "R01 的 high-recall 方向能覆盖一部分右尾 episode，但触发密度直接失败。"
        f"在最终 R01 V3 中，validation candidate seed day rate 为 "
        f"{pct(gate_value(r01_gate, gate_id='seed_density_day_cap', split='validation'))}，"
        f"高于 cap {pct(gate_value(r01_gate, gate_id='seed_density_day_cap', split='validation', column='threshold'))}。"
        "R01.1 的 throttle/cooling 可以把 emitted seed 和 probe entry rate 压到阈值内，"
        "但这只解决“太频繁触发”的工程问题，不解决“触发后是否有正期望”的研究问题。"
    )
    lines.append("")
    lines.append(
        "因此，R01/R01.1 的 `stop` / `archive` 语义是禁止 promotion，而不是禁止继续做研究诊断。"
        "后续 R02-R05 使用冻结 evidence/path artifacts 来追问“这些观察是否能在更高层被救回来”，"
        "但所有报告都必须把它们视为 diagnostic inputs，而不是已经批准的 entry signal。"
    )
    lines.append("")
    lines.append(
        "R02 和 R02 V2 进一步说明，family 结构和 winner-anchored profile 可以提供解释性线索，"
        "但不能通过 validation LR/EV/execution gates。R02 V2 的 R01 reference overlap 达到 "
        f"{pct(gate_value(r02_v2_gate, gate_id='r01_v3_reference_overlap_rate', column='actual'))}，"
        "说明它确实是在解释同一类右尾对象；但 validation 中没有足够 family 通过 LR lower-bound 与 EV 门槛。"
    )
    lines.append("")

    lines.append("### 3.2 R03: Path Confirmation Is Not Fresh-Entry Alpha")
    lines.append("")
    lines.append(
        "R03b 是 EP4 中最有解释力的描述性实验之一：all split 有 "
        f"{num(r03b_all.get('seed_episode_count', 0))} 个 seed episodes，其中 "
        f"{num(r03b_all.get('fresh_episode_count', 0))} 个出现过后续 fresh evidence，"
        f"但 {num(r03b_all.get('failed_before_first_primary_fresh_count', 0))} 个在第一根 clean fresh 前已经失败。"
        "这直接揭示了 fresh evidence 的 survival conditioning：能等到后续信号本身就筛掉了大量坏路径。"
    )
    lines.append("")
    lines.append(
        "R03c/R03d 把这个问题拆得更细：kth fresh、wait-return、family set、family order 和 stage role "
        "大多是在描述 seed episode 已经走出来的状态。seed-anchor 的 P_good 可以显著改善，"
        "但从 fresh signal 之后重新计算的 fresh-anchor 机会并没有同步改善。"
        "R03d 的结论更明确：family 有阶段角色，但严格顺序没有可交易增量。"
    )
    lines.append("")
    lines.append(
        "R03e 试图从反面解决问题：如果不能证明谁会成为 winner，能否至少剔除坏形态？结果也不成立。"
        "Primary `drop_score_ge5` 的结果如下："
    )
    lines.append("")
    lines.append(md_table(r03e_rows))
    lines.append("")
    lines.append(
        "validation 中 drop_score_ge5 后 P_bad 从 parent 增加 "
        f"{signed_pct(r03e_primary.loc[(r03e_primary['split'].eq('validation')) & (r03e_primary['filter_policy'].eq('drop_score_ge5')), 'delta_p_bad_vs_parent'].iloc[0]) if not r03e_primary.empty else ''}，"
        "robustness 中也增加；同时 big-winner rate 下降。当前 BadScore V1 因此不能作为硬过滤器。"
    )
    lines.append("")

    lines.append("### 3.3 R04: Left-Tail Compression Did Not Become Positive Expectancy")
    lines.append("")
    lines.append(
        "R04 系列是 EP4 从 signal/path diagnostic 转向 exposure/portfolio 的关键阶段。"
        "R04 v1 发现 single_momentum_rps 仍含右尾信息，但 market/industry regime 带来的改善受 "
        "denominator shrink、split instability 和 background regime effect 限制，只能 descriptive-only。"
    )
    lines.append("")
    lines.append(
        "R04b 显示 fixed-entry 后的 exit/risk-budget 可以显著改善 validation 左尾，"
        f"selected policy validation net delta vs `hold_120d_no_exit` 为 {signed_pct(get_first(r04b_final, 'validation_net_return_mean_delta_vs_hold120'))}，"
        f"但 robustness 同口径 net delta 为 {signed_pct(get_first(r04b_final, 'robustness_net_return_mean_delta_vs_hold120'))}。"
        "这说明左尾管理在差 split 上看起来有效，但没有稳定提高期望收益。"
    )
    lines.append("")
    lines.append("R04c 的候选池扫描结果：")
    lines.append("")
    lines.append(md_table(r04c_rows))
    lines.append("")
    lines.append(
        "`r02_precision_volume_money` 是最有用的 relative-improvement lead：validation 相对 matched baseline 少亏，"
        "但自身 net return 仍为负。R04d 对这个池做 risk-budget replay，结果如下："
    )
    lines.append("")
    lines.append(md_table(r04d_rows))
    lines.append("")
    lines.append(
        "R04d 的最好 validation policy 也仍为负收益，并且往往牺牲 +50 winner retention。"
        "R04e 再把多个弱池合成 union pool，并做 portfolio-level replay，仍未通过 gate0。"
        "按 validation period return 排名最高的组合如下："
    )
    lines.append("")
    lines.append(md_table(r04e_rows))
    lines.append("")
    lines.append(
        "这三组最高排名 portfolio 均触及 cap20 active inventory 上限，`active_count_p95 = 20`。"
        "因此 portfolio 内实际库存结构高度相似，`monthly_p10` 完全一致不是数据错误，而是 cap20 风险结构主导了组合左尾，"
        "exit policy 的微调只改变了 period return 的小幅排序。"
    )
    lines.append("")
    lines.append(
        "这说明 EP4 不能依赖“多个相对改善池组合后自然变成稳健 portfolio”的假设。"
        "弱信号组合会带来 active inventory、calendar clustering 和 pseudo-diversification 风险，"
        "并不会自动创造绝对正期望。"
    )
    lines.append("")

    lines.append("### 3.4 R05/R05b: Alpha Preflight And Sleeve Allocator Terminal Failure")
    lines.append("")
    lines.append("R05 Preflight 对候选 alpha pool 做了冻结 event replay，结果没有任何候选通过：")
    lines.append("")
    lines.append(md_table(r05_preflight_rows))
    lines.append("")
    lines.append(
        "`base_breakout_vcp` 是唯一 validation hold20 mean 为正的候选，但 validation events 只有 73，"
        "触发 insufficient sample。`low_vol_uptrend` 和 `cross_sectional_low_beta_low_vol` 样本更大，"
        "但 validation hold20 mean 均为负，触发 absolute floor failure。"
    )
    lines.append("")
    lines.append(
        "`base_breakout_vcp` 的 validation hold20 mean 为 +1.00%，但 median 为 -1.47%，两者同时为真："
        "73 个 events 的正均值主要来自少数右尾样本，而多数样本仍亏损。因此 sample-insufficient gate 的阻断是正确决定，"
        "不能把它读成“已有可用 alpha”。"
    )
    lines.append("")
    lines.append(
        "R05b decision precedence 中，risk-on full exposure hard kill 先于 allocator gate / mostly-cash / no-policy-pass。"
        f"因此只要该 hard kill 触发，final decision 就必须是 `{terminal}`；"
        "后续 allocator gate 数据只能作为附带证据，说明即使绕过 hard kill，selectable allocator 也没有 pass。"
    )
    lines.append("")
    lines.append("R05b 首先检查 risk-on full exposure 自身是否在 validation 为正：")
    lines.append("")
    lines.append(md_table(r05b_risk_rows))
    lines.append("")
    lines.append(
        "validation risk-on full exposure return 为 "
        f"{signed_pct(r05b_risk_on.loc[r05b_risk_on['split'].eq('validation'), 'risk_on_full_exposure_period_return'].iloc[0]) if not r05b_risk_on.empty else ''}，"
        "daily mean 也为负。因此 R05b 在 allocator gate 之前已经触发 terminal blocker。"
    )
    lines.append("")
    lines.append("allocator policy 的 validation gate 进一步确认失败原因：")
    lines.append("")
    lines.append(md_table(r05b_gate_rows))
    lines.append("")
    lines.append(
        "`market_state_cash_allocator_v1` 的 validation return 虽然从 full exposure 的 -22.81% 改善到 -14.68%，"
        "也降低了 max drawdown，但 right-tail retention ratio 只有 "
        f"{ratio_with_pct(r05b_cash_allocator.iloc[0]['right_tail_retention_vs_full_exposure']) if not r05b_cash_allocator.empty else ''}，"
        "低于 0.600 gate。"
        "`market_state_cash_plus_basebreakout_secondary_v1` 没有带来增量，因为 secondary sleeve validation 激活不足，"
        "实际表现与 cash allocator 相同。"
    )
    lines.append("")

    lines.append("## 4. Why EP4 Failed")
    lines.append("")
    failure_rows = [
        {
            "失败层": "入口覆盖层",
            "症状": "high-recall seed 可以覆盖右尾，但密度过高；throttle 只修流量，不修期望。",
            "证据": "R01 seed density hard gate failed；R01.1 density pass 但 archive。",
        },
        {
            "失败层": "证据层",
            "症状": "family/fresh/sequence 解释路径状态，但不是稳定 action-time entry edge。",
            "证据": "R03b fresh survival conditioning；R03c seed-anchor 强、fresh-anchor 弱；R03d order no increment。",
        },
        {
            "失败层": "过滤层",
            "症状": "bad-shape 不能稳定剔除坏路径，且会损失 winner。",
            "证据": "R03e drop_score_ge5 未降低 P_bad，big-winner rate 下降。",
        },
        {
            "失败层": "风险管理层",
            "症状": "exit/sizing 能压左尾，但不能稳定提高 OOS 均值。",
            "证据": "R04b validation vs hold_120d_no_exit +3.57% net delta，但 robustness 同口径 -3.05%。",
        },
        {
            "失败层": "候选池层",
            "症状": "relative improvement pool 仍不是 absolute positive pool。",
            "证据": "R04c volume_money validation net -2.07%；R04d best policy validation net 仍负。",
        },
        {
            "失败层": "组合层",
            "症状": "union portfolio 不能把弱 alpha 拼成可用组合，反而暴露伪分散和库存拥挤。",
            "证据": "R04e final `r04e_union_not_viable_validation`，gate0 stop。",
        },
        {
            "失败层": "allocator 层",
            "症状": "正式 hard kill 是 risk-on full exposure 本身 validation 为负；cash allocator 降风险但砍掉右尾，secondary sleeve 也未激活。",
            "证据": "R05b risk-on validation -7.91%；allocator right-tail retention ratio 0.462 (=46.2%)。",
        },
    ]
    lines.append(md_table(failure_rows))
    lines.append("")
    lines.append(
        "关键不是某个局部公式失败，而是整条链条每次试图把“描述性改进”升级成“可交易规则”时，"
        "都会在 validation-first 的硬约束下被打回。这个模式出现了多次，因此终止不是过早，而是必要。"
    )
    lines.append("")

    lines.append("## 5. Lessons Learned")
    lines.append("")
    lessons = [
        {
            "lesson": "1. 覆盖率不是 alpha。",
            "detail": "高召回能让研究有样本，但触发太密时，任何后续筛选都可能只是流量管理。必须先看 action-time base rate、密度和执行可行性。",
        },
        {
            "lesson": "2. Winner-anchored 解释不能替代 entry-time prior。",
            "detail": "很多结构在 winner 回看中很漂亮，但一旦回到当时可观察信息，LR/EV 和 sample sufficiency 就消失。",
        },
        {
            "lesson": "3. Survival conditioning 是最大陷阱。",
            "detail": "等到 T+10、等到 kth fresh、等到 price 已经上涨，本身就在筛掉失败路径。必须把 seed-anchor 与 fresh-anchor 分开。",
        },
        {
            "lesson": "4. Fresh evidence 更适合作为持仓状态变量。",
            "detail": "R03b/R03c/R03d 都支持 fresh/sequence/stage role 的解释价值，但不支持把它们当作新入场或加仓规则。",
        },
        {
            "lesson": "5. Bad-shape filter 不能凭直觉上线。",
            "detail": "如果分数桶不单调、drop policy 不降低 P_bad，就算形态描述合理，也不能成为硬风控。",
        },
        {
            "lesson": "6. 左尾改善不等于策略通过。",
            "detail": "R04b/R04d 多次证明可以少亏，但少亏必须同时保留右尾并把 validation net 变成正数，否则只能 diagnostic-only。",
        },
        {
            "lesson": "7. Robustness 不能拯救 validation。",
            "detail": "EP4 多个实验 robustness 看起来更好，但设计上 robustness 是 readonly final readout，不能反过来选择或救活 validation 失败项。",
        },
        {
            "lesson": "8. 组合不是弱信号的免费午餐。",
            "detail": "union pool 如果没有独立的正期望和低相关暴露，只会把同一类拥挤库存摊开到更多日子和更多股票。",
        },
        {
            "lesson": "9. Alpha pool、relative-improvement pool、sleeve 是三种不同对象。",
            "detail": "R04c/R04d 的 relative improvement 不能直接宣称是 alpha；R05b 的 sleeve 也必须单独检查激活、gross exposure、right-tail retention。",
        },
        {
            "lesson": "10. 好的终止规则本身是研究产出。",
            "detail": "EP4 最有价值的不是上线策略，而是把“还能再调一下”的空间压缩成可审计的 stop 条件，避免继续在同一假设族上消耗实验预算。",
        },
    ]
    lines.append(md_table(lessons))
    lines.append("")

    lines.append("## 6. Final Decision And EP5 Boundary")
    lines.append("")
    lines.append(f"- EP4 terminal decision: `{terminal}`")
    lines.append(f"- Terminal blocker: `{terminal_reason}`")
    lines.append(f"- Selected allocator: `{get_first(r05b_final, 'selected_allocator_policy_id', '') or 'None'}`")
    lines.append(f"- Allowed next requirement: `{allowed_next}`")
    lines.append("")
    lines.append("EP4 后不建议继续做以下事情：")
    lines.append("")
    lines.append("- 不建议在同一 R02/R03 family set 上再做 R05c/R05d 参数微调。")
    lines.append("- 不建议把 R04d 的 volume_money relative improvement 包装成 alpha pool。")
    lines.append("- 不建议用 robustness 正收益反推 validation 失败可忽略。")
    lines.append("- 不建议把 cash allocator 的回撤改善当作通过，因为它未保留足够右尾。")
    lines.append("")
    lines.append("EP5 只有在问题定义发生实质变化时才值得启动，例如：")
    lines.append("")
    lines.append("- 改变交易对象或样本宇宙，而不是在同一 EP4 universe 内继续筛。")
    lines.append("- 改变持有 horizon / execution framing，并重新冻结 as-of 与 next-open 合约。")
    lines.append("- 引入对冲腿、market-neutral framing 或 explicit risk overlay，而不是 long-only cash timing。")
    lines.append("- 从“寻找 big winner episode”切换到完全不同的 loss-avoidance / relative-value / regime allocation 问题。")
    lines.append("")

    lines.append("## 7. Source Artifact Index")
    lines.append("")
    lines.append(md_table(source_rows))
    lines.append("")
    lines.append("本报告只读取上述已生成 artifact，没有重新运行任何实验，也没有改变任何 requirement 或 runner。")
    lines.append("")

    return "\n".join(lines)


def main() -> None:
    OUTPUT_PATH.write_text(build_report(), encoding="utf-8")
    print(f"wrote {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
