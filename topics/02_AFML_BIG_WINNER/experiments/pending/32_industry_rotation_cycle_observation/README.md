# EP32：细分行业长周期轮动观察

[用户问题](GOAL.md)；[观察方案](research_plan.md)；[第一阶段报告](reports/first_observation.md)。

当前为可修订工作结果，不封存。严格PIT受阻，结果只为Historical-proxy。私有大表留在 `~/.cache/a_share/ep32/`，旧实验只读。

从仓库根目录执行：

```bash
PY=topics/02_AFML_BIG_WINNER/.venv/bin/python
EP=topics/02_AFML_BIG_WINNER/experiments/pending/32_industry_rotation_cycle_observation
"$PY" "$EP/src/acquire_industry.py"
OPENBLAS_NUM_THREADS=1 "$PY" "$EP/src/observe.py"
"$PY" "$EP/src/long_segments.py"
OPENBLAS_NUM_THREADS=1 "$PY" "$EP/src/validate.py"
"$PY" -m pytest -q "$EP/tests"
```
