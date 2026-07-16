# 21C Full REAKA PIT Proxy Local Validation Sanity

## 1. 决策与 claim ceiling

`21C_FULL_r2_direction_not_supported`。本结论仅为 validation-only full-architecture local sanity。

## 2. 独立 scope restart

本次 human scope restart 跳过 nested ablation，但不授权 historical holdout、经济 replay 或部署。

## 3. corrected 21B/21A lineage

21B_v5 contract-erratum corrected successor 与 21A M2 paper-lineage erratum 均已 hash pin；M2 仅为 project return-only diagnostic。

## 4. paper-vs-local setup differences

本地为 PIT top-400 main board + top-100 ChiNext、157-feature registered adaptation、2018-2023 validation proxy，不与论文市场数值直接比较。

### 4.1 v3 PIT universe exclusion successor

根据 sealed v2 teacher materialization failure，完整排除 `396` 个缺少严格同 instrument `t+1` approved feature-cache key 的 instrument，且对 train、validation-early、validation-late 统一移除整只 instrument 历史。该变化是显式 estimand change，不是缺失行填补。

- train: `396207` -> `335393`（排除 `60814` rows）
- validation_early: `51932` -> `51932`（排除 `0` rows）
- validation_late: `50167` -> `50167`（排除 `0` rows）
- exclusion registry SHA256: `3c3d903821ee56a49f1ea0d83327606b58f87826ae317d6f95e5a5d4236aef11`

### 4.2 v4 performance successor

v3 在首个 seed 约 32 分钟仍未完成后按用户要求停止，保留 unsealed building evidence。v4 不改变 training batch、optimizer step、模型、loss、seed、epoch或 patience；feature cache改为进程内共享 RAM copy，validation inference batch固定为 `1024`，每个 row/draw 的 20 个 CPU noise tensors一次生成并一次传入 GPU。row-draw SHA256 seed公式不变，但该 CPU RNG route不与未完成 v3 CUDA RNG route宣称数值等价。

## 5. full R2 architecture/config/search accounting

R2 使用双 LSTM、shared gate、4-operator AKS、20-step DDPM、8 draws；只运行 seeds `(20260713, 20260714, 20260715)`，无 sensitivity/search。

## 6. early selection 与 late seal

Checkpoint 仅由 validation_early 选择，pre-gate seal 后由 fresh inference-only worker 读取 validation_late。

## 7. R2 RankIC 与稳定性

validation_late ensemble mean RankIC = `-0.00230413`；positive seeds = `1/3`；positive LOMO = `1/6`。

## 8. R2 vs M1/M3 paired comparison

R2-M1 paired delta = `-0.02189803`；R2-M3 paired delta = `-0.01298650`。

## 9. paper reference table

论文静态值仅作 reference；`numerically_comparable=false`，不构成本地 threshold。

## 10. paper-proxy Top30 gross diagnostic

仅报告 close-to-close gross morphology；不含 next-open、交易限制、成本或连续 NAV，不是 executable PnL。

## 11. 不支持的结论

不支持 exact replication、单模块机制归因、盈利确认、policy training 或 deployment-ready。

## 12. access/hash/reproducibility audit

Historical holdout access 全部为 0；runner/config/test、upstream errata、checkpoint、scores、metrics 与 manifests 均进入 hash closure。

## 13. 下一步

任何 historical test、nested ablation、execution bridge 或 forward confirmation 均需新的人工 requirement 与授权。
