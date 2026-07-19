# 21E REAKA Predictor / DRC 实现识别报告

- 终态：`21E_multiple_implementation_ambiguities_material`
- 证据角色：`design_contaminated_mechanism_diagnostic`
- 不允许论文精确复现、作者实现或 forward support 宣称。
- 本实验没有生成组合收益、AR、Sharpe、换手或再平衡结论。

## 证据分栏与结论边界

| 证据类别 | 本阶段可确认内容 | 允许使用方式 | 不允许外推 |
|---|---|---|---|
| 论文原文 | 定义 residual target、以 `Z` 为条件的 DDPM、corrected latent，以及 shifted sequence 最后一位作为预测；未披露采样聚合、扩散步数、denoiser/decoder topology、`L_rec` 梯度连接和再平衡频率 | 限定论文明确语义与未披露项 | 不据此补写作者代码 |
| 21C project choice | `8-draw score mean`、20-step concat MLP denoiser、shared linear decoder、当前 coupled reconstruction graph | 作为待识别的本地实现基线 | 不称为论文原实现 |
| 21D prior observation | 21C/21D 已读取 2023 early/late 并据此提出实现差异假设；RankIC gap 可能混合 Predictor、DRC 与其他外部缺口 | 只用于冻结 21E 假设与 arm | 不当作 21E 独立验证 |
| 21E direct evidence | 冻结 arm、3 seeds、early-only 选择、fresh late worker 的 paired RankIC、形态与梯度审计 | 只判断本地实现敏感性和 materiality | 不声称论文精确复现、作者实现或 forward support |

## 1. 论文明确语义与未披露项

论文明确给出了 residual target、conditional DDPM、corrected latent 和最后 shifted position 的预测语义。论文没有足够信息唯一确定 draw 聚合、reverse-path 随机性、扩散步数、denoiser 与 decoder topology、reconstruction gradient coupling，以及投资组合再平衡频率。因此这些项在 21E 中被视为实现歧义，而不是从论文补全出的事实。

## 2. 21C 中属于 project choice 的实现

- Predictor：8 个 row-keyed DDPM draws 在 decoded-score 域取 mean。
- DRC：20 diffusion steps，concat MLP denoiser。
- Decoder：shared linear decoder。
- Training graph：`L_rec -> x0_hat -> denoiser` 保持 coupled。
- 上述选择仅定义 P0/G0/A0 control，不代表论文作者实现。

## 3. Predictor 聚合与 corrected-latent 排序

Validation-late ensemble mean daily RankIC 如下。`zero-noise` 仅是 deterministic reverse-path proxy，不能解释为 DDPM conditional mean；`Koopman-only` 是去掉 corrected residual 的机制 control。

| arm | readout | mean daily RankIC | 与 P0 的含义 |
|---|---|---:|---|
| P4_ZERO_NOISE_REVERSE_PROXY | point | 0.011612 | implementation sensitivity readout |
| P5_KOOPMAN_ONLY | point | 0.011215 | implementation sensitivity readout |
| G1_STOPGRAD_X0_RECON | score_mean64 | 0.010664 | implementation sensitivity readout |
| P1_SINGLE_DRAW0 | point | 0.008467 | implementation sensitivity readout |
| G0_CURRENT_X0_COUPLED | score_mean64 | 0.003419 | implementation sensitivity readout |
| A0_SELECTED_GRAPH_CONTROL | score_mean64 | 0.003419 | implementation sensitivity readout |
| P2_SCORE_MEAN64 | point | 0.003419 | implementation sensitivity readout |
| A2_RESBLOCK_20_STEP | score_mean64 | 0.003177 | implementation sensitivity readout |
| G2_TEACHER_LATENT_RECON_ORACLE | score_mean64 | 0.003063 | implementation sensitivity readout |
| A1_MLP_100_STEP | score_mean64 | -0.001517 | implementation sensitivity readout |
| A3_POINTWISE_MLP_DECODER | score_mean64 | -0.001942 | implementation sensitivity readout |
| P0_CURRENT_SCORE_MEAN8 | point | -0.002304 | 21C current control |
| G0_CURRENT_X0_COUPLED | score_mean256 | -0.003266 | implementation sensitivity readout |
| P3_SCORE_MEAN256_REF | point | -0.003266 | implementation sensitivity readout |
| A1_MLP_100_STEP | score_mean256 | -0.003818 | implementation sensitivity readout |
| P6_SCORE_MEDIAN256 | point | -0.003963 | implementation sensitivity readout |

P1 single draw 相对 P0 的 C01 delta 为 `0.010771`；64-draw mean 的 C02 为 `0.005723`；256-draw mean 的 C03 为 `-0.000962`；median256 相对 mean256 的 C06 为 `-0.000697`。聚合选择会改变排序，Predictor semantics 判定为 material。

## 4. 当前 DRC 相对 Koopman-only

P0 current score-mean8 RankIC 为 `-0.002304`，P5 Koopman-only 为 `0.011215`，后者高 `0.013519`。预注册 C05 使用 Koopman-only 对 mean256 corrected-latent，late delta 为 `0.014481`，3 seeds 中 `2` 个同向，判定 `true`。因此在本地 2023 diagnostic 上，当前 corrected residual 路径相对该 control 是伤害而非增益；这不等价于论文 DRC 本身无效。

## 5. Reconstruction gradient coupling 与 collapse

G0 coupled 的 denoiser `L_rec` gradient L2 均值为 `9.288957e-04`；G1 stop-grad 对应值为 `0.000000e+00`，验证 detach 确实切断该路径。G0 的 denoiser `L_total` global-gradient share 均值为 `0.998018`，但审计中的 additional collapse flags 总数为 `0`：没有触发预注册的新增 collapse。late RankIC 从 G0 `0.003419` 提升到 G1 `0.010664`，C10 delta `0.007245`、`3/3` seeds 同向并 material。结论是 gradient path 对结果 material；证据不支持把差距简化为已观测到的 gradient-dominance collapse。

## 6. DRC steps、denoiser 与 decoder 的 materiality

| 变体 | contrast | late delta | 同向 seeds | material | 结论 |
|---|---|---:|---:|---|---|
| A1 100 steps | C20 | -0.004936 | 2/3 | false | 仅增加 steps 未通过四项 conjunction |
| A2 residual-block denoiser | C21 | -0.000242 | 1/3 | false | topology 改变未判 material |
| A3 pointwise MLP decoder | C22 | -0.005361 | 3/3 | true | decoder topology material |

机械状态汇总：Predictor `material`；DRC training graph `material`；DRC architecture `not_material`；Decoder topology `material`。

## 7. Oracle 与 diagnostic controls

- G2 teacher-latent reconstruction 使用 inference 不可获得的 teacher target，只能作为 oracle control，永远不可晋级。
- P4 zero-noise reverse path 只是 deterministic proxy，不是 DDPM conditional mean。
- P5 Koopman-only 用于识别 corrected residual 的局部贡献，不是完整 REAKA 替代实现。
- 所有 2023 readouts 的 evidence role 均为 `design_contaminated_mechanism_diagnostic`。

## 8. 为什么不能声称找到论文作者实现

本实验只比较有限、预注册的本地 arms。material 表明结果对该实现维度敏感，不表示胜出的 arm 等于作者代码；not-material 也不能排除未测试的 architecture。没有官方代码、作者确认、完整 decoder/采样细节时，作者实现不可识别。

## 9. 为什么不报告组合收益与再平衡结论

本 requirement 没有授权生成组合、AR、Sharpe、换手或 execution ledger，portfolio artifact absence gate 已通过。论文再平衡频率仍未被唯一识别，因此不能把本实验 RankIC 直接转换为日频或其他频率的投资模拟；相关验证必须另立 requirement。

## 10. 剩余不可识别项与下一步边界

仍缺少官方 sampling aggregation、reverse stochastic contract、完整 denoiser/decoder topology、reconstruction coupling 说明、训练细节和再平衡合同。外部官方代码或作者说明出现前，终态保持 implementation ambiguities material，且 `next_requirement_execution_authorized=false`。

## 预注册 contrasts 完整表

| contrast | family | mean delta | seed同向数 | median score rho | material |
|---|---|---:|---:|---:|---|
| C01 | predictor_semantics | 0.010771 | 3 | 0.333850 | true |
| C02 | predictor_semantics | 0.005723 | 2 | 0.342234 | true |
| C03 | predictor_semantics | -0.000962 | 2 | 0.171592 | false |
| C04 | predictor_semantics | 0.014878 | 2 | 0.136525 | true |
| C05 | corrected_latent | 0.014481 | 2 | 0.131532 | true |
| C06 | predictor_semantics | -0.000697 | 2 | 0.787578 | false |
| C10 | drc_training_graph | 0.007245 | 3 | 0.148173 | true |
| C11 | drc_training_graph | -0.000356 | 0 | 0.074976 | false |
| C20 | drc_architecture | -0.004936 | 2 | -0.000842 | false |
| C21 | drc_architecture | -0.000242 | 1 | -0.039827 | false |
| C22 | decoder_topology | -0.005361 | 3 | 0.385350 | true |

## 假设与终态

- 预注册假设 readout 行数：`12`。
- 终态：`21E_multiple_implementation_ambiguities_material`。
- 决策规则：mechanical first-match from pre-registered materiality。

## 本地 canonical 与 Git 发布边界

canonical bundle 在本地完整保留。以下单文件超过 20 MiB，Git 发布时必须按 exact path ignore，但不得删除、截断或替换为空文件：
- `predictions/validation_early_prediction_scores.parquet`（129.35 MiB，本地 canonical only）
- `predictions/validation_late_prediction_scores.parquet`（124.51 MiB，本地 canonical only）

其余 canonical artifacts 可按仓库规则正常发布；本报告不执行 Git commit/push。
