# EP31 八项独立裁决

| hypothesis | verdict | estimate | ci_low | ci_high | q_bh | consistent_folds | complete_folds | forward |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| H01 | INCONCLUSIVE | -0.00374054 | -0.00678713 | -0.000416612 | 0.0315 | 0.727273 | 22 | FORWARD_PENDING |
| H02 | INCONCLUSIVE | -0.0114673 | -0.0221158 | -0.00169847 | 0.0408333 | 0.666667 | 21 | FORWARD_PENDING |
| H03 | INCONCLUSIVE | -0.00323156 | -0.00772212 | 0.000618029 | 0.14 | 0.636364 | 22 | FORWARD_PENDING |
| H07 | INCONCLUSIVE | 0.00170306 | 0.000336181 | 0.00295811 | 0.0315 | 0 | 22 | FORWARD_PENDING |
| H09 | BLOCKED_DATA |  |  |  |  |  |  | FORWARD_PENDING |
| H10 | INCONCLUSIVE | 2.23258e-06 | -5.34767e-06 | 9.75122e-06 | 0.3864 | 0.590909 | 22 | FORWARD_PENDING |
| H11 | INCONCLUSIVE | 0.00162525 | -0.00536754 | 0.00721186 | 0.834167 | 0.5 | 22 | FORWARD_PENDING |
| H12 | INCONCLUSIVE | 0.000689045 | -9.15839e-05 | 0.00151652 | 0.9495 | 0.454545 | 22 | FORWARD_PENDING |

FDR 家族为七项实际受检主端点；H09 数据阻断不计为失败或第八份检验。收益端点系控制基线残差的训练尺度偏斜率；H07 为 log variance MSE 改善，H10 为 Brier 改善。这些效应单位不同，不能相加或按数值大小比较。主判断使用扩展窗，36 月滚动仅作稳健性。

本轮 H01/H02/H07 的汇总主端点 q < 0.05，仍未形成完整支持：H01 的训练标签置乱控制存在名义显著改善；H02 只有 14/21 完整季度同向（66.7%）；H07 虽改善未来波动预测损失，但 22 个完整季度的因子系数均为负，不能支持预注册的“异常成交越高、未来波动越高”方向。条件系数的相反方向也不构成成交导致波动下降的因果证明。

**H01**：Negative control significant; independent-information attribution not established。对立解释见 GOAL.md，不作因果推断。

**H02**：correct-direction fold fraction=66.667% < 70%。对立解释见 GOAL.md，不作因果推断。

**H03**：BH-FDR q=0.14 >= 0.05; correct-direction fold fraction=63.636% < 70%。对立解释见 GOAL.md，不作因果推断。

**H07**：correct-direction fold fraction=0.000% < 70%; positive factor coefficient in 0/22 complete folds。对立解释见 GOAL.md，不作因果推断。

**H09**：No timestamp-attested trade-size/count/category source。对立解释见 GOAL.md，不作因果推断。

**H10**：BH-FDR q=0.3864 >= 0.05; correct-direction fold fraction=59.091% < 70%; rolling / leave-year / size / provider stability gate not established。对立解释见 GOAL.md，不作因果推断。

**H11**：BH-FDR q=0.834167 >= 0.05; correct-direction fold fraction=50.000% < 70%; rolling / leave-year / size / provider stability gate not established。对立解释见 GOAL.md，不作因果推断。

**H12**：BH-FDR q=0.9495 >= 0.05; correct-direction fold fraction=45.455% < 70%; rolling / leave-year / size / provider stability gate not established。对立解释见 GOAL.md，不作因果推断。

TRADING_NOT_AUTHORIZED；前瞻独立确认全部 FORWARD_PENDING。
