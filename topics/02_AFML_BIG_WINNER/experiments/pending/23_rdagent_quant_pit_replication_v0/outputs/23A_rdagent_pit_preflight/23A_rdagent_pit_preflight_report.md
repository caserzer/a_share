# EP23 23A RD-Agent PIT Preflight

生成时间（UTC）：`2026-07-27T16:04:01.280824+00:00`

## 裁决

```text
ready_for_deterministic_baseline = true
ready_for_agent_loop             = true
claim_ceiling                    = paper_protocol_grounded_pit_agent_loop_ready
```

PIT 数据和 Alpha20/双标签 smoke 已通过。完整 agent loop
已通过 uv adapter、聊天模型、embedding 模型和 provider key 的静态就绪检查。
当前 Docker 不可用，但 EP23 的目标 runtime 是 uv，因此 Docker 不是必要条件。

## Source / Data

| 项目 | 值 |
|---|---|
| paper SHA match | True |
| RD-Agent commit | `4f9ecb00` |
| RD-Agent clean | False |
| RD-Agent adapter diff match | True |
| calendar | 2017-01-03 .. 2026-05-29 (2281 sessions) |
| historical PIT-eligible instruments | 862 |
| interval rows | 5697 |
| price-provider instruments | 4597 |
| missing PIT feature directories | 0 |
| Alpha20 smoke | True |
| label smoke | True |

## Runtime

| component | ready | required_for_agent_loop | detail |
|---|---|---|---|
| uv | True | True | uv 0.7.8 |
| docker | False | False | The command 'docker' could not be found in this WSL 2 distro. |
| chat_model | True | True | configured |
| embedding_model | True | True | configured |
| provider_api_key | True | True | configured |
| uv_rdagent_adapter | True | True | validated diff=80c471ae3ba6, python/qrun present |

## 解释

本次通过只说明 PIT 数据、deterministic baseline 与 agent runtime 已达到启动条件，
不说明论文主结果已复现。论文的 CSI300/2008-2020/Wind 数据与本地 PIT universe
不同；后续 agent 结果仍只能按 project adaptation 的证据身份解释。
