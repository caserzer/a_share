# EP32 V2：完整历史与基准收益差

[本轮方案](research_plan.md)；[完整报告](reports/full_history_observation.md)；[跑赢基准名单](reports/04_screened_cases.md)。V1保持不变，工作结果可修订。

从仓库根目录，使用 `topics/02_AFML_BIG_WINNER/.venv/bin/python`，依次执行本目录：`src/acquire.py`、`src/run.py --build-panel`、`src/validate_v2.py`。已有完整、哈希匹配面板时，`src/run.py`可复用私有面板；只读前代输入。
