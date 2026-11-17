# 固定风格比较的全部证据

## 全部成本与账户

| strategy   | cost   |    cagr |    nav |   annual_oneway_turnover |   holdings |
|:-----------|:-------|--------:|-------:|-------------------------:|-----------:|
| HIGHVOL    | main   |  1.7580 | 1.0717 |                   9.1797 |    59.2158 |
| HIGHVOL    | stress | -4.6541 | 0.8275 |                  10.4046 |    59.2158 |
| HIGHVOL    | zero   |  4.2765 | 1.1810 |                   8.7690 |    59.2158 |
| LOWVOL     | main   |  2.1972 | 1.0902 |                   8.9086 |    59.2168 |
| LOWVOL     | stress | -4.1932 | 0.8435 |                  10.0820 |    59.2168 |
| LOWVOL     | zero   |  4.7062 | 1.2004 |                   8.5147 |    59.2168 |
| MIX        | main   |  0.8582 | 1.0345 |                   9.8679 |    59.1978 |
| MIX        | stress | -5.7123 | 0.7916 |                  11.2530 |    59.1978 |
| MIX        | zero   |  3.4423 | 1.1439 |                   9.4057 |    59.1978 |
| MOM        | main   | -1.3620 | 0.9470 |                  10.2146 |    59.2158 |
| MOM        | stress | -7.8100 | 0.7240 |                  11.6590 |    59.2158 |
| MOM        | zero   |  1.1744 | 1.0475 |                   9.7330 |    59.2158 |
| O          | main   |  4.8446 | 1.2067 |                   8.8882 |    59.1978 |
| O          | stress | -2.1190 | 0.9184 |                  10.1309 |    59.1978 |
| O          | zero   |  7.5855 | 1.3370 |                   8.4742 |    59.1978 |
| REV        | main   |  4.5582 | 1.1937 |                   9.4212 |    59.2048 |
| REV        | stress | -2.5741 | 0.9016 |                  10.7867 |    59.2048 |
| REV        | zero   |  7.3687 | 1.3263 |                   8.9680 |    59.2048 |
| SM         | main   |  4.8446 | 1.2067 |                   8.8882 |    59.1978 |
| SM         | stress | -2.1190 | 0.9184 |                  10.1309 |    59.1978 |
| SM         | zero   |  7.5855 | 1.3370 |                   8.4742 |    59.1978 |

SM是原持仓的零支持回退复放，不是成功匹配的投资组合；表中数值仅用于账本核验。主成本10/20bps，零成本0/0，压力成本30/80bps。

## 全部比较

| metric       | comparison      | cost   | primary   | status              |    n |     mean |   ci_low |   ci_high |        p |   p_holm |
|:-------------|:----------------|:-------|:----------|:--------------------|-----:|---------:|---------:|----------:|---------:|---------:|
| annual_daily | O-REV           | main   | False     | ESTIMATED           | 1001 |   0.2471 |  -2.1605 |    2.6415 |   0.8382 | nan      |
| annual_daily | O-MOM           | main   | False     | ESTIMATED           | 1001 |   6.1740 |   2.6096 |   10.3269 |   0.0024 | nan      |
| annual_daily | O-LOWVOL        | main   | False     | ESTIMATED           | 1001 |   2.8321 |  -0.3581 |    6.2742 |   0.0986 | nan      |
| annual_daily | O-HIGHVOL       | main   | False     | ESTIMATED           | 1001 |   2.7972 |  -0.3687 |    6.4092 |   0.1044 | nan      |
| annual_daily | O-MIX           | main   | True      | ESTIMATED           | 1001 |   3.7793 |   0.5929 |    7.1154 |   0.0236 |   0.0944 |
| annual_daily | O-SM            | main   | True      | NO_MATCHING_SUPPORT |    0 | nan      | nan      |  nan      | nan      | nan      |
| annual_daily | O-REV           | zero   | False     | ESTIMATED           | 1001 |   0.1766 |  -2.2202 |    2.5737 |   0.8796 | nan      |
| annual_daily | O-MOM           | zero   | False     | ESTIMATED           | 1001 |   6.2157 |   2.6498 |   10.3842 |   0.0024 | nan      |
| annual_daily | O-LOWVOL        | zero   | False     | ESTIMATED           | 1001 |   2.9870 |  -0.1979 |    6.4238 |   0.0794 | nan      |
| annual_daily | O-HIGHVOL       | zero   | False     | ESTIMATED           | 1001 |   2.9332 |  -0.2431 |    6.5597 |   0.0890 | nan      |
| annual_daily | O-MIX           | zero   | False     | ESTIMATED           | 1001 |   3.8310 |   0.6537 |    7.1853 |   0.0218 | nan      |
| annual_daily | O-SM            | zero   | False     | NO_MATCHING_SUPPORT |    0 | nan      | nan      |  nan      | nan      | nan      |
| annual_daily | O-REV           | stress | False     | ESTIMATED           | 1001 |   0.4346 |  -1.9940 |    2.8303 |   0.7261 | nan      |
| annual_daily | O-MOM           | stress | False     | ESTIMATED           | 1001 |   6.0628 |   2.5078 |   10.1883 |   0.0026 | nan      |
| annual_daily | O-LOWVOL        | stress | False     | ESTIMATED           | 1001 |   2.4203 |  -0.7792 |    5.8745 |   0.1546 | nan      |
| annual_daily | O-HIGHVOL       | stress | False     | ESTIMATED           | 1001 |   2.4353 |  -0.7098 |    6.0061 |   0.1550 | nan      |
| annual_daily | O-MIX           | stress | False     | ESTIMATED           | 1001 |   3.6416 |   0.4478 |    6.9923 |   0.0292 | nan      |
| annual_daily | O-SM            | stress | False     | NO_MATCHING_SUPPORT |    0 | nan      | nan      |  nan      | nan      | nan      |
| H10_event    | BASE_O-BASE_MIX | main   | True      | ESTIMATED           |   46 |   0.3017 |  -0.3720 |    1.0077 |   0.3829 |   1.0000 |
| H10_event    | SM_O-SM_PEER    | main   | True      | NO_MATCHING_SUPPORT |    0 | nan      | nan      |  nan      | nan      | nan      |

缺失不是零。REV、MOM和两个波动方向的p是辅助，不能据此重新选择主模型或主结论。所有区间为普通点对点95%，非同时区间；多重校正仍不能清除此前历史搜索偏差。

## 支持范围

| test   |   mean_covered_total_budget |   excluded_budget_coverage |   prior_P_budget_coverage |
|:-------|----------------------------:|---------------------------:|--------------------------:|
| BASE   |                     31.5957 |                    95.2093 |                   99.8928 |
| SM     |                      0.0000 |                     0.0000 |                    0.0000 |

预算覆盖单位%。BASE只有一个行业日期组因原输入缺失而保留；SM所有组均不支持。[逐组原因](../../outputs/diagnostics/e1_excluded_styles_20261117/support.csv) · [逐期资金覆盖](../../outputs/diagnostics/e1_excluded_styles_20261117/coverage.csv) · [各规则行业组名单重叠](../../outputs/diagnostics/e1_excluded_styles_20261117/baseline_overlap.csv)。

## 不可行约束的可达到范围

| style        |   groups_blocked |   max_required_gap |
|:-------------|-----------------:|-------------------:|
| mom60        |              180 |             3.3840 |
| mom20        |              163 |             4.4134 |
| idio60       |              154 |             3.2327 |
| vol60        |              146 |             3.1175 |
| beta60       |              143 |             3.2116 |
| vol20        |              137 |             2.8408 |
| log_total_mv |              137 |             3.1370 |
| log_circ_mv  |              134 |             2.8971 |
| log_money20  |              131 |             4.0798 |
| mom5         |              130 |             5.9195 |
| mom1         |              130 |             3.2640 |
| log_amihud20 |              127 |             4.1199 |
| turnover20   |              115 |             5.8557 |

groups_blocked表示单独看这一风格已经不可行的组数，各风格可以同时阻断同一个组，不能相加。max_required_gap是对照个股权重上限下离原均值最近仍需容忍的差，单位全截面标准差；只作支持范围诊断，未拿它搜索更宽容差。

[逐行业日期、逐风格的目标与可达上下界](../../outputs/diagnostics/e1_excluded_styles_20261117/feasibility_ranges.csv)。364个LP不可行组中331组被至少一个单变量界限阻断，另外33组仅在联合约束下不可行。

## O−MIX逐年和逐月贡献

| comparison   | freq   | period   |   wealth_contribution |
|:-------------|:-------|:---------|----------------------:|
| O-MIX        | Y      | 2021     |                9.4746 |
| O-MIX        | Y      | 2022     |                6.6968 |
| O-MIX        | Y      | 2023     |                0.8966 |
| O-MIX        | Y      | 2024     |               -0.5443 |
| O-MIX        | Y      | 2025     |                0.6976 |
| O-MIX        | M      | 2021-01  |                1.2620 |
| O-MIX        | M      | 2021-02  |                2.9756 |
| O-MIX        | M      | 2021-03  |                0.2103 |
| O-MIX        | M      | 2021-04  |                0.1941 |
| O-MIX        | M      | 2021-05  |                1.1277 |
| O-MIX        | M      | 2021-06  |               -0.8995 |
| O-MIX        | M      | 2021-07  |               -0.8530 |
| O-MIX        | M      | 2021-08  |                2.6935 |
| O-MIX        | M      | 2021-09  |                0.4770 |
| O-MIX        | M      | 2021-10  |                1.7200 |
| O-MIX        | M      | 2021-11  |                0.4599 |
| O-MIX        | M      | 2021-12  |                0.1071 |
| O-MIX        | M      | 2022-01  |                0.3711 |
| O-MIX        | M      | 2022-02  |                2.0155 |
| O-MIX        | M      | 2022-03  |                0.7465 |
| O-MIX        | M      | 2022-04  |                0.0933 |
| O-MIX        | M      | 2022-05  |                1.9330 |
| O-MIX        | M      | 2022-06  |               -0.4778 |
| O-MIX        | M      | 2022-07  |                0.0283 |
| O-MIX        | M      | 2022-08  |                0.7410 |
| O-MIX        | M      | 2022-09  |                0.7583 |
| O-MIX        | M      | 2022-10  |                0.2301 |
| O-MIX        | M      | 2022-11  |                0.0808 |
| O-MIX        | M      | 2022-12  |                0.1767 |
| O-MIX        | M      | 2023-01  |               -0.0725 |
| O-MIX        | M      | 2023-02  |                0.3905 |
| O-MIX        | M      | 2023-03  |                0.2845 |
| O-MIX        | M      | 2023-04  |                2.3459 |
| O-MIX        | M      | 2023-05  |               -0.0187 |
| O-MIX        | M      | 2023-06  |               -1.7881 |
| O-MIX        | M      | 2023-07  |                1.1119 |
| O-MIX        | M      | 2023-08  |               -1.2099 |
| O-MIX        | M      | 2023-09  |                0.3214 |
| O-MIX        | M      | 2023-10  |               -0.1635 |
| O-MIX        | M      | 2023-11  |               -0.1220 |
| O-MIX        | M      | 2023-12  |               -0.1829 |
| O-MIX        | M      | 2024-01  |                1.0879 |
| O-MIX        | M      | 2024-02  |               -0.1156 |
| O-MIX        | M      | 2024-03  |               -0.2335 |
| O-MIX        | M      | 2024-04  |               -0.7256 |
| O-MIX        | M      | 2024-05  |               -0.3635 |
| O-MIX        | M      | 2024-06  |                0.3149 |
| O-MIX        | M      | 2024-07  |                0.8281 |
| O-MIX        | M      | 2024-08  |                0.5313 |
| O-MIX        | M      | 2024-09  |               -0.0963 |
| O-MIX        | M      | 2024-10  |               -0.3121 |
| O-MIX        | M      | 2024-11  |               -1.3936 |
| O-MIX        | M      | 2024-12  |               -0.0664 |
| O-MIX        | M      | 2025-01  |                0.3519 |
| O-MIX        | M      | 2025-02  |                0.3866 |
| O-MIX        | M      | 2025-03  |               -0.0409 |

这是对两条账户终值差的链接分摊，非逐期收益率直接相加，也不是经济因果。[完整股票贡献](../../outputs/diagnostics/e1_excluded_styles_20261117/stock_contributions.csv)。O−SM零差异对应未替换，不能归因到任何风格机制。

## 辅助条件排序

|        n |   periods |   mean |   ci_low |   ci_high |      p |   bootstrap_failed |   bootstrap_sd |
|---------:|----------:|-------:|---------:|----------:|-------:|-------------------:|---------------:|
| 210.0000 |  217.0000 | 0.0099 |  -0.0129 |    0.0334 | 0.4033 |             0.0000 |         0.0118 |

[每周样本数、剩余自由度及条件IC](../../outputs/diagnostics/e1_excluded_styles_20261117/conditional_ic.csv)。晚期未成熟标签保留不可估计。缺失样本不补零。原始分数、目标与交易单在本地private/e1_excluded_styles_20261117/，完整原预算和行业规则保留。

[事件退出情况](../../outputs/diagnostics/e1_excluded_styles_20261117/events.csv) · [账户逐年逐月收益](../../outputs/diagnostics/e1_excluded_styles_20261117/periods.csv) · [主核验](../../outputs/diagnostics/e1_excluded_styles_20261117/validation.json) · [匹配结构核验](../../outputs/diagnostics/e1_excluded_styles_20261117/support_audit.json)。
