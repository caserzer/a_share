#!/usr/bin/env python3
"""Assemble the complete EP23 Phase-2 replication report and audit manifest."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from ep23_phase2_common import sha256_file


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def markdown_table(path: Path, columns: list[str] | None = None) -> str:
    frame = pd.read_csv(path)
    if columns is not None:
        frame = frame[[column for column in columns if column in frame]]
    return frame.to_markdown(index=False)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, type=Path)
    args = parser.parse_args()
    config_path = args.config.resolve()
    root = config_path.parent
    phase2 = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    dirs = {
        key: root / value
        for key, value in phase2["outputs"].items()
        if key != "local_cache"
    }
    required = {
        "preflight": ["preflight_verdict.json"],
        "benchmark": ["verdict.json", "library_summary.csv"],
        "factor_a20": [
            "verdict.json",
            "run_manifest.json",
            "search_accounting.csv",
        ],
        "factor_a158": [
            "verdict.json",
            "run_manifest.json",
            "search_accounting.csv",
        ],
        "evolution_dynamics": [
            "verdict.json",
            "search_efficiency.csv",
            "branch_comparison.csv",
        ],
        "model_a20": [
            "verdict.json",
            "run_manifest.json",
            "search_accounting.csv",
        ],
        "model_best_library": ["verdict.json", "gate_evidence.json"],
        "execution_bridge": [
            "verdict.json",
            "seed_metrics.csv",
            "matched_seed_deltas.csv",
        ],
        "joint_scheduler": ["verdict.json", "gate_evidence.json"],
    }
    missing = [
        str(dirs[key] / name)
        for key, names in required.items()
        for name in names
        if not (dirs[key] / name).exists()
    ]
    if missing:
        raise FileNotFoundError(
            f"Phase-2 final report blocked by missing artifacts: {missing}"
        )

    g = read_json(dirs["preflight"] / "preflight_verdict.json")
    h = read_json(dirs["benchmark"] / "verdict.json")
    factors = {
        branch: read_json(dirs[key] / "verdict.json")
        for branch, key in (("A20", "factor_a20"), ("A157", "factor_a158"))
    }
    factor_runs = {
        branch: read_json(dirs[key] / "run_manifest.json")
        for branch, key in (("A20", "factor_a20"), ("A157", "factor_a158"))
    }
    j = read_json(dirs["evolution_dynamics"] / "verdict.json")
    k = read_json(dirs["model_a20"] / "verdict.json")
    k_run = read_json(dirs["model_a20"] / "run_manifest.json")
    k2 = read_json(dirs["model_best_library"] / "verdict.json")
    execution = read_json(dirs["execution_bridge"] / "verdict.json")
    m = read_json(dirs["joint_scheduler"] / "verdict.json")

    static_table = markdown_table(
        dirs["benchmark"] / "library_summary.csv",
        [
            "library_id",
            "validation_paper_proxy_ic",
            "validation_paper_proxy_rank_ic",
            "historical_test_paper_proxy_ic",
            "historical_test_paper_proxy_rank_ic",
            "historical_test_paper_proxy_net_arr",
            "historical_test_executable_bridge_net_arr",
            "usable_feature_count",
            "effective_rank",
            "effective_rank_per_feature",
            "median_abs_pairwise_corr",
            "max_abs_pairwise_corr",
        ],
    )
    search_table = markdown_table(
        dirs["evolution_dynamics"] / "search_efficiency.csv"
    )
    factor_final_table = pd.DataFrame(
        [
            {
                "branch": branch,
                "status": verdict["status"],
                "completed_loops": factor_runs[branch]["trace"][
                    "complete_loop_count"
                ],
                "agent_accepted_factors": verdict["accepted_factor_count"],
                "ep23_retained_factors": verdict["retained_factor_count"],
                "provider_cost_usd": factor_runs[branch].get(
                    "openrouter_key_usage_delta_usd"
                ),
            }
            for branch, verdict in factors.items()
        ]
    ).to_markdown(index=False)
    execution_deltas = pd.read_csv(
        dirs["execution_bridge"] / "matched_seed_deltas.csv"
    )
    execution_summary = (
        execution_deltas.groupby(["branch", "metric"], as_index=False)
        .agg(
            median_delta=("delta", "median"),
            positive_seeds=("delta", lambda values: int((values > 0).sum())),
        )
    )
    execution_summary = execution_summary[
        execution_summary["metric"].isin(
            [
                "execution_net_arr",
                "execution_net_ir",
                "execution_net_mdd",
                "execution_mean_one_way_turnover",
                "paper_net_arr",
            ]
        )
    ].to_markdown(index=False)

    total_formal_cost = sum(
        float(value or 0)
        for value in (
            factor_runs["A20"].get("openrouter_key_usage_delta_usd"),
            factor_runs["A157"].get("openrouter_key_usage_delta_usd"),
            k_run.get("openrouter_key_usage_delta_usd"),
        )
    )
    invalidated_cost = float(j.get("invalidated_schema_bug_cost_usd") or 0)
    report = f"""# EP23：RD-Agent Quant PIT 深度复刻完整报告

> 生成时间：{utc_now()}
>
> 论文：R&D-Agent-Quant（arXiv:2505.15155v2）
>
> 运行模型：`openai/gpt-5.6-sol-pro`（OpenRouter）
>
> Embedding：`openai/text-embedding-3-small`（OpenRouter）
>
> 环境：`uv`；所有 OpenRouter 请求经冻结 HTTP/HTTPS proxy；报告不记录密钥或
> proxy 地址。

## 1. 最终结论

```text
23G factor-library preflight = {g.get("status", g.get("verdict"))}
23H static benchmark = {h.get("status", h.get("verdict"))}
23I A20 = {factors["A20"]["status"]}
23I A157 registered adaptation = {factors["A157"]["status"]}
23J evolution dynamics = {j["status"]}
23K1 model evolution = {k["status"]}
23K2 best-library sensitivity = {k2["status"]}
23L execution / Big Winner = {execution["status"]}
23M joint scheduler = {m["status"]}
deployment_authorized = false
```

本阶段完整执行了预注册的静态库、双起点因子进化、进化路径诊断、模型进化、
next-open 执行与 Big Winner bridge。23M 是否付费运行严格服从 gate；
`not_run_by_preregistered_gate` 是实验终态，而不是缺失结果。

## 2. 复刻身份与边界

- A20 是 RD-Agent 本地固定 20 因子起点。
- 原生 Alpha158 因 `$vwap` 缺失不可精确物化；正式第二分支是明确命名的
  `A157_QLIB_NO_VWAP_REGISTERED_ADAPTATION`，不能简称为完整 Alpha158。
- A300 是无 VWAP 的更宽静态 registered adaptation。
- Alpha101 缺少经参考值验证的 canonical 本地重建；AutoAlpha 缺少论文冻结
  artifact；二者保留 blocked，不用替代品伪装精确复刻。
- Agent 只看 train、early-stop valid 与 2022 feedback；2023 confirmation
  对搜索隐藏；2024–2026 historical test 首次由 23L 揭示。
- historical test 已用于当前研究闭环，因此经济证据身份固定为
  `design_contaminated_historical_real_market_evidence`，不构成生产授权。

## 3. 23H 静态因子库

{static_table}

静态库按 2022–2023 validation 选择，不以 2024–2026 test 倒选。宽库的名义
维度不能替代有效秩与验证稳定性；因此同时报告 IC/RankIC、净收益、effective
rank 和相关性。

## 4. 23I 双起点 RD-Factor

{factor_final_table}

Agent 的 `Decision=true` 只代表 2022 feedback 接受。最终 frozen evolved
library 还必须通过 2023 matched five-seed、4/5 同向与相关度 `<0.99` gate。
所有拒绝、实现失败、checkpoint 和 schema 修复前的 invalid run 均保留。

## 5. 23J 搜索动态与效率

{search_table}

hypothesis 聚类固定使用 `openai/text-embedding-3-small`；只发送 hypothesis
与 reason 文本。refine/shift/reuse 使用预注册 cosine 规则，并报告
0.75/0.80/0.85 敏感性。schema-bug run 成本单列，不进入成功率分母。

## 6. 23K 模型进化

```text
status = {k["status"]}
predictive_model_pass = {str(bool(k.get("predictive_model_pass"))).lower()}
model_execution_gate_pass = {str(bool(k.get("model_execution_gate_pass"))).lower()}
accepted_agent_model_count = {k.get("accepted_agent_model_count")}
provider_cost_usd = {float(k_run.get("openrouter_key_usage_delta_usd") or 0):.6f}
```

每个 Agent-accepted model 均与 frozen LightGBM、flattened MLP、last-state GRU、
attentive GRU 和 capacity-matched neural control 做五 seed 归因。以实际
`model.py`、参数量、optimizer/loss/scheduler/clip/window 和训练记录为真值，
不以 LLM spec 代替 runtime。

## 7. 23L Next-Open 与 Big Winner

```json
{json.dumps(execution.get("branch_gates", {}), ensure_ascii=False, indent=2, sort_keys=True)}
```

主要 matched 经济增量：

{execution_summary}

执行复用 23F 状态机：close t 形成 score、next tradable open 成交、动态 PIT
membership、停牌/ST/上市退市、涨跌停、TopK/dropout、佣金/印花税/最低佣金/
滑点、失败订单与持仓延续。Big Winner 同时检查 right-tail enrichment、episode
recall、severe-left-tail、morphology、lifecycle、score decile 与集中度。

## 8. 23M Joint Scheduler

```json
{json.dumps(m, ensure_ascii=False, indent=2, sort_keys=True)}
```

只有 factor、model、runtime trace 与 frozen-artifact compatibility 四项同时
为真，才允许启动 bandit/random/LLM-directed 三条 12 小时付费 arm。gate 为假
时不强行运行，避免把违反预注册的额外搜索包装成“完整实验”。

## 9. 成本、异常与可审计性

```text
formal_provider_cost_usd = {total_formal_cost:.6f}
invalidated_schema_bug_cost_usd = {invalidated_cost:.6f}
combined_observed_provider_cost_usd = {total_formal_cost + invalidated_cost:.6f}
```

- invalidated A20 run 暴露了 feedback 字段兼容问题，修复后通过独立 schema
  smoke，再从空 namespace 重启；
- formal factor/model 分支使用独立 trace、workspace 和 pickle cache；
- 原始 LLM decision 与 checkpoint decision 分列对账；
- secret scan 命中必须为 0；
- provider cost 使用 OpenRouter key usage delta，不用缺失的 LiteLLM 价格映射
  伪造 0 成本。

## 10. 最终解释

本实验回答的是：在当前 A 股 PIT universe、本地 Qlib provider、registered
factor adaptations、冻结时间边界与 OpenRouter 模型配置下，RD-Agent 是否能
产生经独立 confirmation 和 next-open 经济验证的增量。它不是对论文所有
数据、所有因子 artifact 和所有算力条件的逐字节复现。

任何未同时通过 predictive、execution 和 Big Winner gate 的信号，只能按证据
降级为 risk overlay、participation filter、meta-label 或
`no_incremental_utility`；不得称为生产 Big Winner selector。
"""
    report_path = root / "EP23_PHASE2_FULL_REPLICATION_REPORT.md"
    report_path.write_text(report, encoding="utf-8")

    artifact_paths = [
        path
        for key in required
        for path in dirs[key].rglob("*")
        if path.is_file()
        and not any(
            part in {"raw_rdagent_trace", "workspaces", "pickle_cache"}
            for part in path.parts
        )
    ]
    manifest = {
        "generated_at_utc": utc_now(),
        "status": "phase2_replication_complete",
        "report": {
            "path": str(report_path),
            "sha256": sha256_file(report_path),
        },
        "required_artifact_missing_count": 0,
        "artifact_count": len(artifact_paths),
        "artifact_hashes": {
            str(path.relative_to(root)): sha256_file(path)
            for path in sorted(artifact_paths)
        },
        "formal_provider_cost_usd": total_formal_cost,
        "invalidated_schema_bug_cost_usd": invalidated_cost,
        "deployment_authorized": False,
    }
    write_path = root / "phase2_completion_manifest.json"
    write_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": manifest["status"],
                "report": str(report_path),
                "artifact_count": manifest["artifact_count"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
