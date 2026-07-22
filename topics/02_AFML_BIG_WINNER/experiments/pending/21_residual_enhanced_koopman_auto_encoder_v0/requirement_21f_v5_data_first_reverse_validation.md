# 21F v5 Data-first 与反向验证 Requirement

> Requirement version：`21F_DATA_FIRST_REVERSE_VALIDATION_v5`
> 证据角色：`provisional_design_contaminated_diagnostic`
> 密封权限：`false`，直到 full reverse validation 完成

## 1. 背景与故障归因

21F v4 的 E2 已完成并闭合 30/30 inner checkpoints。E3 在 Predictor candidate 阶段没有 estimator 通过全部 convergence gates，因此触发最昂贵的 `Q2_SCORE_MEAN256_REF` fallback。随后 24 个未缓存 arm/fold/seed checkpoints 串行执行完整 `256 draws × 20 DDPM steps`。审计显示每个 checkpoint 约 22 分钟；row-keyed noise 又以 Python 单线程逐行创建 CPU Generator、SHA256 seed 与 `(20,10,64)` tensor，造成单核约 100%、GPU 约 30%–50%。E3 的静态 12 小时预算与约 14–15 小时实际工作量不一致。

v4 在北京时间 2026-07-21 19:26 人工停止。停止前 E2 manifest SHA256=`84280a14f2c470eaf6d016c7cbd74278ca116c6818407d268cff0c6ca9988dc5`，30 个 checkpoint byte hashes 全部匹配；E3 内存中的 draw cache、arm scores 与未落盘 convergence rows 不可复用。

## 2. 目标

将流程拆为两个严格分层的阶段：

1. `DATA_FIRST`：尽快生成可检查的 inner-arm、provisional refit 和 2023 readout 数据；
2. `REVERSE_VALIDATION`：在数据生成后，用高成本 Q2 对 provisional 选择进行反向核验。

DATA_FIRST 结果只允许用于定位方向、比较符号与发现实现问题，不得作为最终 repair candidate，不得覆盖 v4 终态，不得密封。

## 3. E2 复用合同

E2 不重新训练。v5 必须从只读 source root 读取并验证：

- `inner_checkpoint_manifest.json` byte hash；
- manifest `entry_n=30` 与 global `job_order=1..30`；
- 每个 checkpoint 的 size、byte SHA256；
- `.state/inner_training_complete.json` byte hash；
- inner registry 36 rows、gradient calibration 210 rows、collapse audit 30 rows；
- pre-2023 row index 与 upstream config hashes。

任一验证失败立即停止，不得部分导入。导入使用 hardlink；不修改 source root。

## 4. DATA_FIRST arm readout

固定 proxy estimator=`Q1_SCORE_MEAN64`，保持 v4 row-key CRN、64 draws、20-step DDPM、逐 draw decode、float64 ascending accumulation。Q1 在本阶段是 provisional proxy，不宣称已通过 Q2 convergence。

两路按 inner fold 隔离：

```text
lane_0 = I0_SELECT_2021 × 5 arms × 3 seeds
lane_1 = I1_SELECT_2022 × 5 arms × 3 seeds
```

每个 checkpoint 完成后立即原子写出 score `.npy` 与 progress record；重启时只有 checkpoint SHA、score shape、finite 与 score SHA 全部匹配才可跳过。两 lane 不共享可写文件。coordinator 只在两路完成后合并 prediction parquet。

provisional arm 选择只使用：finite/coverage、两个 fold ensemble RankIC、positive seed count、cross-seed Spearman/Top30、turnover、LOMO 和 collapse audit。跳过 Q1-vs-Q2 convergence gate、bootstrap/Holm 与全 estimator family selection。选择规则仍按 worst-fold RankIC、rho、overlap、turnover、arm order；没有 eligible arm 时以该排序第一名作为 provisional fallback。

## 5. Provisional refit 性能合同

复用 E2 六个 selected epochs 的 lower median。固定 epoch refit 不再在每个 epoch执行无控制作用的 Q8 readout；训练 batch 顺序、optimizer、loss、tau、gumbel/diffusion generators 和最终 epoch 数保持 v4。由于 readout 是 `no_grad` 且使用独立 row-key generators，跳过它不得改变 optimizer/model state。三个 seeds 以两路执行并逐 seed 持久化 checkpoint。

## 6. 2023 fast readout

DESIGN_EARLY 与 DESIGN_LATE 两路并行。首次数据只计算：

- provisional selected DRC：Q1 prefix64；
- same-backbone K0：Q6；
- sealed 21C control：Q0 prefix8。

首次不计算 Q2 ref256。每个 `(fold,variant,seed)` 立即持久化。输出必须包含 daily RankIC、selected−K0、selected−Q0、cross-seed morphology、Top30、turnover 与 LOMO，并生成中文 provisional report。

## 7. REVERSE_VALIDATION

DATA_FIRST 完成后才允许启动。第一层 targeted reverse validation 对以下对象计算 exact Q2/ref256：

- provisional selected arm 的 6 个 inner checkpoints；
- Q1 排名第二 arm 的 6 个 inner checkpoints；
- provisional refit 的 3 seeds × 2 design folds。

两 inner folds / 两 design folds 分 lane 并逐 checkpoint 持久化。必须验证 Q1-vs-Q2 convergence、候选两 arm 排名是否翻转、2023 RankIC 与 selected−K0 增量是否翻转。

targeted validation 通过只允许标记 `targeted_reverse_supported`，仍不等于 full validation。其余三个 arms 的 Q2、完整 estimator family、bootstrap/Holm 与原 42 gates 可在 full reverse validation 中补齐。只有 full reverse validation、closed-schema 和全部 artifact gates 完成后才可另行授权密封。

## 8. 终止与发布边界

- DATA_FIRST canonical output 不存在；只保留 `.building` provisional bundle。
- `seal_authorized=false` 与 `next_requirement_execution_authorized=false`。
- 技术失败保留逐任务 progress；安全重启不得重算已验证 score/checkpoint。
- 单文件超过 20 MiB 保持 local-only，Git 只发布 requirement/config/runner/test/report 等小文件。
