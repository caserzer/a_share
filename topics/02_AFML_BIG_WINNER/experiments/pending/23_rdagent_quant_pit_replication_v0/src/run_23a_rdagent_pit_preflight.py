#!/usr/bin/env python3
"""EP23 paper, PIT data, and RD-Agent runtime preflight."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import qlib
import yaml
from qlib.data import D


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def find_topic_root(config_path: Path) -> Path:
    for parent in [config_path.parent, *config_path.parents]:
        if (parent / "pyproject.toml").exists() and (parent / "data").is_dir():
            return parent
    raise RuntimeError(f"cannot resolve topic root from {config_path}")


def run_text(command: list[str], cwd: Path | None = None) -> tuple[int, str]:
    result = subprocess.run(
        command,
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode, (result.stdout + result.stderr).strip()


def git_diff_sha256(repo_path: Path) -> tuple[int, str]:
    result = subprocess.run(
        ["git", "diff", "--binary"],
        cwd=repo_path,
        capture_output=True,
        check=False,
    )
    return result.returncode, hashlib.sha256(result.stdout).hexdigest()


def configured_names(dotenv_path: Path, names: list[str]) -> dict[str, bool]:
    configured = {name: bool(os.environ.get(name, "").strip()) for name in names}
    if not dotenv_path.exists():
        return configured
    for raw_line in dotenv_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key in configured and value.strip().strip("'\""):
            configured[key] = True
    return configured


def normalize_feature_frame(frame: pd.DataFrame) -> pd.DataFrame:
    if list(frame.index.names) == ["instrument", "datetime"]:
        frame = frame.swaplevel()
    if list(frame.index.names) != ["datetime", "instrument"]:
        frame.index = frame.index.set_names(["datetime", "instrument"])
    return frame.sort_index()


def markdown_table(rows: list[dict[str, Any]], columns: list[str]) -> str:
    header = "| " + " | ".join(columns) + " |"
    divider = "|" + "|".join("---" for _ in columns) + "|"
    body = [
        "| " + " | ".join(str(row.get(column, "")) for column in columns) + " |"
        for row in rows
    ]
    return "\n".join([header, divider, *body])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args()

    config_path = Path(args.config).resolve()
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    topic_root = find_topic_root(config_path)
    output_dir = topic_root / config["outputs"]["preflight"]
    output_dir.mkdir(parents=True, exist_ok=True)

    paper_path = topic_root / config["paper"]["path"]
    provider_path = topic_root / config["data"]["provider_uri"]
    calendar_path = topic_root / config["data"]["calendar_file"]
    instrument_path = topic_root / config["data"]["instrument_file"]
    rdagent_path = Path(config["rdagent"]["checkout"]).resolve()

    paper_sha = sha256_file(paper_path)
    commit_rc, commit_text = run_text(
        ["git", "rev-parse", "--short=8", "HEAD"], cwd=rdagent_path
    )
    status_rc, status_text = run_text(
        ["git", "status", "--short"], cwd=rdagent_path
    )
    adapter_diff_rc, adapter_diff_sha = git_diff_sha256(rdagent_path)
    uv_rc, uv_text = run_text(["uv", "--version"])
    docker_binary = shutil.which("docker")
    if docker_binary:
        docker_rc, docker_text = run_text(
            [docker_binary, "info", "--format", "{{.ServerVersion}}"]
        )
    else:
        docker_rc, docker_text = 127, "docker binary not found"

    credential_names = [
        "CHAT_MODEL",
        "EMBEDDING_MODEL",
        "OPENAI_API_KEY",
        "AZURE_API_KEY",
        "DEEPSEEK_API_KEY",
        "LITELLM_PROXY_API_KEY",
        "MODEL_COSTEER_ENV_TYPE",
        "FACTOR_COSTEER_ENV_TYPE",
        "FACTOR_COSTEER_PYTHON_BIN",
    ]
    credentials = configured_names(rdagent_path / ".env", credential_names)
    chat_ready = credentials["CHAT_MODEL"]
    embedding_ready = credentials["EMBEDDING_MODEL"]
    provider_key_ready = any(
        credentials[name]
        for name in credential_names
        if name.endswith("_API_KEY")
    )
    uv_python = rdagent_path / ".venv/bin/python"
    uv_qrun = rdagent_path / ".venv/bin/qrun"
    uv_adapter_ready = all(
        [
            adapter_diff_rc == 0,
            adapter_diff_sha == config["rdagent"]["adapter_diff_sha256"],
            uv_python.is_file(),
            uv_qrun.is_file(),
            credentials["MODEL_COSTEER_ENV_TYPE"],
            credentials["FACTOR_COSTEER_ENV_TYPE"],
            credentials["FACTOR_COSTEER_PYTHON_BIN"],
        ]
    )

    calendar = [
        line.strip()
        for line in calendar_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    interval_rows = [
        line.strip()
        for line in instrument_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    historical_instruments = {
        row.split("\t", 1)[0].upper() for row in interval_rows
    }
    feature_directories = list((provider_path / "features").iterdir())
    price_provider_instruments = {
        path.name.upper() for path in feature_directories if path.is_dir()
    }
    missing_pit_feature_directories = sorted(
        historical_instruments - price_provider_instruments
    )

    qlib.init(provider_uri=str(provider_path), region="cn")
    instruments = D.list_instruments(
        D.instruments(config["data"]["market"]),
        start_time="2024-01-02",
        end_time="2024-03-29",
        freq="day",
        as_list=True,
    )
    smoke_instruments = sorted(instruments)[:20]
    alpha_names = list(config["alpha20"])
    alpha_expressions = [config["alpha20"][name] for name in alpha_names]
    label_names = list(config["labels"])
    label_expressions = [
        config["labels"][name]["expression"] for name in label_names
    ]
    expressions = [*alpha_expressions, *label_expressions]
    columns = [*alpha_names, *label_names]
    smoke = D.features(
        smoke_instruments,
        expressions,
        start_time="2024-01-02",
        end_time="2024-03-29",
        freq="day",
    )
    smoke = normalize_feature_frame(smoke)
    smoke.columns = columns

    expression_rows = []
    for name in columns:
        series = pd.to_numeric(smoke[name], errors="coerce")
        finite = np.isfinite(series.to_numpy(dtype=float, na_value=np.nan))
        expression_rows.append(
            {
                "name": name,
                "role": "alpha20" if name in alpha_names else "label",
                "rows": int(len(series)),
                "finite_rows": int(finite.sum()),
                "finite_ratio": round(float(finite.mean()), 8),
            }
        )
    expression_audit = pd.DataFrame(expression_rows)
    expression_audit.to_csv(output_dir / "alpha20_expression_smoke.csv", index=False)

    hardcode_specs = [
        (
            "provider_uri",
            rdagent_path
            / "rdagent/scenarios/qlib/experiment/factor_template/conf_baseline.yaml",
            '~/.qlib/qlib_data/cn_data',
        ),
        (
            "market",
            rdagent_path
            / "rdagent/scenarios/qlib/experiment/factor_template/conf_baseline.yaml",
            "market: &market csi300",
        ),
        (
            "conda_runtime",
            rdagent_path / "rdagent/utils/env.py",
            "class QlibCondaConf",
        ),
    ]
    hardcode_rows = []
    for item, path, needle in hardcode_specs:
        text = path.read_text(encoding="utf-8")
        hardcode_rows.append(
            {
                "item": item,
                "path": str(path.relative_to(rdagent_path)),
                "needle": needle,
                "present": needle in text,
                "requires_ep23_adapter": needle in text,
            }
        )
    pd.DataFrame(hardcode_rows).to_csv(
        output_dir / "rdagent_hardcode_audit.csv", index=False
    )

    gap_rows = [
        {
            "gap": "market_universe",
            "paper": "CSI300",
            "ep23": config["data"]["market"],
            "classification": "required_project_adaptation",
        },
        {
            "gap": "sample_period",
            "paper": "2008-01-01..2020-08-01",
            "ep23": f"{calendar[0]}..{calendar[-1]}",
            "classification": "exact_replication_unreachable",
        },
        {
            "gap": "fundamental_data",
            "paper": "Wind fields without full timestamp contract",
            "ep23": "PIT-audited local price-volume fields only",
            "classification": "primary_scope_restriction",
        },
        {
            "gap": "execution_timing",
            "paper": "text says t+1 open; YAML uses close",
            "ep23": "paper_proxy and executable_bridge lanes",
            "classification": "dual_lane_required",
        },
        {
            "gap": "runtime",
            "paper": "official conda/docker path",
            "ep23": "uv only",
            "classification": "runtime_adapter_required",
        },
        {
            "gap": "llm_backend",
            "paper": "GPT-4o/o3-mini and text-embedding-ada-002",
            "ep23": "not configured at preflight",
            "classification": "external_runtime_blocker",
        },
    ]
    pd.DataFrame(gap_rows).to_csv(
        output_dir / "replication_gap_registry.csv", index=False
    )

    finite_floor = 0.80
    alpha_smoke_ready = bool(
        (expression_audit.loc[expression_audit["role"] == "alpha20", "finite_ratio"]
        >= finite_floor).all()
    )
    label_smoke_ready = bool(
        (expression_audit.loc[expression_audit["role"] == "label", "finite_ratio"]
        >= finite_floor).all()
    )
    data_ready = all(
        [
            calendar[0] == config["data"]["expected_calendar_start"],
            calendar[-1] == config["data"]["expected_calendar_end"],
            len(historical_instruments)
            >= int(config["data"]["minimum_historical_instruments"]),
            not missing_pit_feature_directories,
            alpha_smoke_ready,
            label_smoke_ready,
        ]
    )
    source_tree_ready = (
        not status_text
        if config["rdagent"]["require_clean_checkout"]
        else adapter_diff_sha == config["rdagent"]["adapter_diff_sha256"]
    )
    source_ready = all(
        [
            paper_sha == config["paper"]["sha256"],
            commit_rc == 0,
            commit_text == config["rdagent"]["expected_commit"],
            status_rc == 0,
            adapter_diff_rc == 0,
            source_tree_ready,
        ]
    )
    runtime_rows = [
        {
            "component": "uv",
            "ready": uv_rc == 0,
            "required_for_agent_loop": True,
            "detail": uv_text.splitlines()[0] if uv_text else "",
        },
        {
            "component": "docker",
            "ready": docker_rc == 0,
            "required_for_agent_loop": False,
            "detail": docker_text.splitlines()[0] if docker_text else "",
        },
        {
            "component": "chat_model",
            "ready": chat_ready,
            "required_for_agent_loop": True,
            "detail": "configured" if chat_ready else "missing",
        },
        {
            "component": "embedding_model",
            "ready": embedding_ready,
            "required_for_agent_loop": True,
            "detail": "configured" if embedding_ready else "missing",
        },
        {
            "component": "provider_api_key",
            "ready": provider_key_ready,
            "required_for_agent_loop": True,
            "detail": "configured" if provider_key_ready else "missing",
        },
        {
            "component": "uv_rdagent_adapter",
            "ready": uv_adapter_ready,
            "required_for_agent_loop": True,
            "detail": (
                f"validated diff={adapter_diff_sha[:12]}, python/qrun present"
                if uv_adapter_ready
                else "adapter diff, uv executables, or env selection mismatch"
            ),
        },
    ]
    pd.DataFrame(runtime_rows).to_csv(
        output_dir / "runtime_readiness.csv", index=False
    )

    ready_for_agent_loop = bool(
        source_ready
        and data_ready
        and all(
            row["ready"]
            for row in runtime_rows
            if row["required_for_agent_loop"]
        )
    )
    decision = {
        "episode_id": config["episode_id"],
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "paper_sha256": paper_sha,
        "paper_sha256_match": paper_sha == config["paper"]["sha256"],
        "rdagent_commit": commit_text,
        "rdagent_commit_match": commit_text == config["rdagent"]["expected_commit"],
        "rdagent_clean": not bool(status_text),
        "rdagent_adapter_diff_sha256": adapter_diff_sha,
        "rdagent_adapter_diff_match": (
            adapter_diff_sha == config["rdagent"]["adapter_diff_sha256"]
        ),
        "calendar_start": calendar[0],
        "calendar_end": calendar[-1],
        "calendar_sessions": len(calendar),
        "historical_instruments": len(historical_instruments),
        "instrument_interval_rows": len(interval_rows),
        "price_provider_instruments": len(feature_directories),
        "missing_pit_instrument_feature_directories": (
            missing_pit_feature_directories
        ),
        "smoke_instruments": len(smoke_instruments),
        "smoke_rows": len(smoke),
        "alpha20_finite_floor": finite_floor,
        "alpha20_smoke_ready": alpha_smoke_ready,
        "label_smoke_ready": label_smoke_ready,
        "source_ready": source_ready,
        "data_ready": data_ready,
        "ready_for_deterministic_baseline": bool(source_ready and data_ready),
        "ready_for_agent_loop": ready_for_agent_loop,
        "agent_loop_blockers": [
            row["component"]
            for row in runtime_rows
            if row["required_for_agent_loop"] and not row["ready"]
        ],
        "claim_ceiling": (
            "paper_protocol_grounded_pit_agent_loop_ready"
            if ready_for_agent_loop
            else (
                "paper_protocol_and_pit_baseline_ready_agent_loop_blocked"
                if source_ready and data_ready
                else "preflight_blocked"
            )
        ),
    }
    (output_dir / "preflight_decision.json").write_text(
        json.dumps(decision, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    report = f"""# EP23 23A RD-Agent PIT Preflight

生成时间（UTC）：`{decision["generated_at_utc"]}`

## 裁决

```text
ready_for_deterministic_baseline = {str(decision["ready_for_deterministic_baseline"]).lower()}
ready_for_agent_loop             = {str(decision["ready_for_agent_loop"]).lower()}
claim_ceiling                    = {decision["claim_ceiling"]}
```

PIT 数据和 Alpha20/双标签 smoke 已{"通过" if data_ready else "失败"}。完整 agent loop
{"已通过 uv adapter、聊天模型、embedding 模型和 provider key 的静态就绪检查。" if ready_for_agent_loop else "仍存在必需 runtime blocker。"}
当前 Docker 不可用，但 EP23 的目标 runtime 是 uv，因此 Docker 不是必要条件。

## Source / Data

| 项目 | 值 |
|---|---|
| paper SHA match | {decision["paper_sha256_match"]} |
| RD-Agent commit | `{commit_text}` |
| RD-Agent clean | {decision["rdagent_clean"]} |
| RD-Agent adapter diff match | {decision["rdagent_adapter_diff_match"]} |
| calendar | {calendar[0]} .. {calendar[-1]} ({len(calendar)} sessions) |
| historical PIT-eligible instruments | {len(historical_instruments)} |
| interval rows | {len(interval_rows)} |
| price-provider instruments | {len(feature_directories)} |
| missing PIT feature directories | {len(missing_pit_feature_directories)} |
| Alpha20 smoke | {alpha_smoke_ready} |
| label smoke | {label_smoke_ready} |

## Runtime

{markdown_table(runtime_rows, ["component", "ready", "required_for_agent_loop", "detail"])}

## 解释

本次通过只说明 PIT 数据、deterministic baseline 与 agent runtime 已达到启动条件，
不说明论文主结果已复现。论文的 CSI300/2008-2020/Wind 数据与本地 PIT universe
不同；后续 agent 结果仍只能按 project adaptation 的证据身份解释。
"""
    (output_dir / "23A_rdagent_pit_preflight_report.md").write_text(
        report, encoding="utf-8"
    )
    print(json.dumps(decision, indent=2, sort_keys=True))
    return 0 if decision["ready_for_deterministic_baseline"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
