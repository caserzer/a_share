# 全部可比模型指标表：截至 R307

本表列出386个统计组，来自R196–R205的主框架和R276/R281的电池扩展。它不是对307轮里全部重复审计重新训练。其他版本、时钟敏感性、经济价值验证与无资格项见逐轮索引。每组仅保留所有候选都有指标的共同日期，先算各候选跨日期均值，再取候选中位数。34组没有共同可评价日期，保留缺失。RankIC越大越好；Brier、MSE越小越好。不同任务和母体不能拼成总排名。

## r196

| 分组 | 指标 | 候选数 | 共同日期数／区间 | 最佳候选 | 最佳 | 中位数 | 最差 |
|---|---|---|---|---|---|---|---|
| family=core; era=SW2014; level=L2; cohort=F; task=onset; horizon=20; objective=onset | Brier | 3 | 22 / 2020-01-23–2021-10-29 | F/interaction | 0.167576 | 0.167629 | 0.168997 |
| family=core; era=SW2014; level=L2; cohort=FC; task=onset; horizon=20; objective=onset | Brier | 6 | 10 / 2021-01-29–2021-10-29 | FC/base | 0.205826 | 0.209678 | 0.210636 |
| family=core; era=SW2014; level=L2; cohort=FD; task=onset; horizon=20; objective=onset | Brier | 6 | 22 / 2020-01-23–2021-10-29 | F/interaction | 0.167596 | 0.168065 | 0.169001 |
| family=core; era=SW2014; level=L3; cohort=F; task=onset; horizon=20; objective=onset | Brier | 3 | 22 / 2020-01-23–2021-10-29 | F/interaction | 0.171391 | 0.171459 | 0.172410 |
| family=core; era=SW2014; level=L3; cohort=FC; task=onset; horizon=20; objective=onset | Brier | 6 | 10 / 2021-01-29–2021-10-29 | FC/base | 0.212074 | 0.214954 | 0.216273 |
| family=core; era=SW2014; level=L3; cohort=FD; task=onset; horizon=20; objective=onset | Brier | 6 | 22 / 2020-01-23–2021-10-29 | FD/interaction | 0.171422 | 0.171672 | 0.172627 |
| family=core; era=SW2021; level=L2; cohort=F; task=onset; horizon=20; objective=onset | Brier | 3 | 20 / 2025-01-27–2026-08-31 | F/base | 0.141118 | 0.145679 | 0.148696 |
| family=core; era=SW2021; level=L2; cohort=FC; task=onset; horizon=20; objective=onset | Brier | 6 | 20 / 2025-01-27–2026-08-31 | FC/base | 0.137715 | 0.139619 | 0.144756 |
| family=core; era=SW2021; level=L2; cohort=FD; task=onset; horizon=20; objective=onset | Brier | 6 | 20 / 2025-01-27–2026-08-31 | F/base | 0.141137 | 0.144870 | 0.148692 |
| family=core; era=SW2021; level=L3; cohort=F; task=onset; horizon=20; objective=onset | Brier | 3 | 20 / 2025-01-27–2026-08-31 | F/base | 0.152370 | 0.154210 | 0.158996 |
| family=core; era=SW2021; level=L3; cohort=FC; task=onset; horizon=20; objective=onset | Brier | 6 | 20 / 2025-01-27–2026-08-31 | F/base | 0.143605 | 0.146774 | 0.149939 |
| family=core; era=SW2021; level=L3; cohort=FD; task=onset; horizon=20; objective=onset | Brier | 6 | 20 / 2025-01-27–2026-08-31 | F/base | 0.152353 | 0.154027 | 0.158988 |
| family=core; era=SW2021; level=L3; cohort=FDG; task=onset; horizon=20; objective=onset | Brier | 6 | 20 / 2025-01-27–2026-08-31 | F/state | 0.156110 | 0.158939 | 0.166284 |
| family=core; era=SW2021; level=L3; cohort=FG; task=onset; horizon=20; objective=onset | Brier | 6 | 20 / 2025-01-27–2026-08-31 | F/state | 0.156128 | 0.158565 | 0.159215 |
| family=core; era=SW2014; level=L2; cohort=F; task=return; horizon=20; objective=rank | RankIC | 3 | 22 / 2020-01-23–2021-10-29 | F/base | 0.049038 | 0.049038 | 0.047656 |
| family=core; era=SW2014; level=L2; cohort=F; task=return; horizon=20; objective=return | RankIC | 3 | 22 / 2020-01-23–2021-10-29 | F/state | 0.008210 | 0.008200 | 0.001347 |
| family=core; era=SW2014; level=L2; cohort=F; task=return; horizon=60; objective=rank | RankIC | 3 | 19 / 2020-01-23–2021-07-30 | F/interaction | 0.101945 | 0.038054 | 0.038054 |
| family=core; era=SW2014; level=L2; cohort=F; task=return; horizon=60; objective=return | RankIC | 3 | 19 / 2020-01-23–2021-07-30 | F/interaction | 0.027951 | 0.016892 | 0.016496 |
| family=core; era=SW2014; level=L2; cohort=FC; task=return; horizon=20; objective=rank | RankIC | 6 | 10 / 2021-01-29–2021-10-29 | F/base | 0.069125 | 0.068955 | -0.030125 |
| family=core; era=SW2014; level=L2; cohort=FC; task=return; horizon=20; objective=return | RankIC | 6 | 10 / 2021-01-29–2021-10-29 | FC/state | -0.048208 | -0.049475 | -0.094254 |
| family=core; era=SW2014; level=L2; cohort=FC; task=return; horizon=60; objective=rank | RankIC | 6 | 7 / 2021-01-29–2021-07-30 | F/base | 0.056634 | 0.027784 | -0.033715 |
| family=core; era=SW2014; level=L2; cohort=FC; task=return; horizon=60; objective=return | RankIC | 6 | 7 / 2021-01-29–2021-07-30 | FC/state | 0.039925 | 0.022843 | -0.077494 |
| family=core; era=SW2014; level=L2; cohort=FD; task=return; horizon=20; objective=rank | RankIC | 6 | 22 / 2020-01-23–2021-10-29 | F/base | 0.051040 | 0.043956 | 0.030375 |
| family=core; era=SW2014; level=L2; cohort=FD; task=return; horizon=20; objective=return | RankIC | 6 | 22 / 2020-01-23–2021-10-29 | F/base | 0.012973 | 0.001347 | -0.007384 |
| family=core; era=SW2014; level=L2; cohort=FD; task=return; horizon=60; objective=rank | RankIC | 6 | 19 / 2020-01-23–2021-07-30 | F/interaction | 0.097504 | 0.044416 | 0.038960 |
| family=core; era=SW2014; level=L2; cohort=FD; task=return; horizon=60; objective=return | RankIC | 6 | 19 / 2020-01-23–2021-07-30 | FD/interaction | 0.039969 | 0.018679 | 0.016957 |
| family=core; era=SW2014; level=L3; cohort=F; task=return; horizon=20; objective=rank | RankIC | 3 | 22 / 2020-01-23–2021-10-29 | F/interaction | 0.083191 | 0.018297 | 0.018297 |
| family=core; era=SW2014; level=L3; cohort=F; task=return; horizon=20; objective=return | RankIC | 3 | 22 / 2020-01-23–2021-10-29 | F/interaction | 0.058925 | -0.008883 | -0.009265 |
| family=core; era=SW2014; level=L3; cohort=F; task=return; horizon=60; objective=rank | RankIC | 3 | 19 / 2020-01-23–2021-07-30 | F/interaction | 0.077640 | -0.028016 | -0.028026 |
| family=core; era=SW2014; level=L3; cohort=F; task=return; horizon=60; objective=return | RankIC | 3 | 19 / 2020-01-23–2021-07-30 | F/interaction | 0.073635 | -0.055141 | -0.056724 |
| family=core; era=SW2014; level=L3; cohort=FC; task=return; horizon=20; objective=rank | RankIC | 6 | 10 / 2021-01-29–2021-10-29 | F/interaction | 0.059398 | -0.003876 | -0.006106 |
| family=core; era=SW2014; level=L3; cohort=FC; task=return; horizon=20; objective=return | RankIC | 6 | 10 / 2021-01-29–2021-10-29 | F/interaction | 0.013141 | -0.056294 | -0.067796 |
| family=core; era=SW2014; level=L3; cohort=FC; task=return; horizon=60; objective=rank | RankIC | 6 | 7 / 2021-01-29–2021-07-30 | F/interaction | 0.076490 | -0.097357 | -0.106952 |
| family=core; era=SW2014; level=L3; cohort=FC; task=return; horizon=60; objective=return | RankIC | 6 | 7 / 2021-01-29–2021-07-30 | F/interaction | 0.069822 | -0.112079 | -0.137450 |
| family=core; era=SW2014; level=L3; cohort=FD; task=return; horizon=20; objective=rank | RankIC | 6 | 22 / 2020-01-23–2021-10-29 | F/interaction | 0.085898 | 0.020961 | 0.018020 |
| family=core; era=SW2014; level=L3; cohort=FD; task=return; horizon=20; objective=return | RankIC | 6 | 22 / 2020-01-23–2021-10-29 | F/interaction | 0.063577 | -0.004527 | -0.008848 |
| family=core; era=SW2014; level=L3; cohort=FD; task=return; horizon=60; objective=rank | RankIC | 6 | 19 / 2020-01-23–2021-07-30 | F/interaction | 0.079216 | -0.022443 | -0.027466 |
| family=core; era=SW2014; level=L3; cohort=FD; task=return; horizon=60; objective=return | RankIC | 6 | 19 / 2020-01-23–2021-07-30 | F/interaction | 0.076684 | -0.046457 | -0.054580 |
| family=core; era=SW2021; level=L2; cohort=F; task=return; horizon=20; objective=rank | RankIC | 3 | 32 / 2024-01-31–2026-08-31 | F/base | 0.073528 | 0.073528 | 0.032228 |
| family=core; era=SW2021; level=L2; cohort=F; task=return; horizon=20; objective=return | RankIC | 3 | 32 / 2024-01-31–2026-08-31 | F/base | 0.043525 | 0.043431 | 0.002410 |
| family=core; era=SW2021; level=L2; cohort=F; task=return; horizon=60; objective=rank | RankIC | 3 | 18 / 2025-01-27–2026-06-30 | F/interaction | 0.126617 | 0.084153 | 0.084142 |
| family=core; era=SW2021; level=L2; cohort=F; task=return; horizon=60; objective=return | RankIC | 3 | 18 / 2025-01-27–2026-06-30 | F/interaction | 0.109115 | 0.045399 | 0.045357 |
| family=core; era=SW2021; level=L2; cohort=FC; task=return; horizon=20; objective=rank | RankIC | 6 | 32 / 2024-01-31–2026-08-31 | F/base | 0.080906 | 0.075984 | 0.039124 |
| family=core; era=SW2021; level=L2; cohort=FC; task=return; horizon=20; objective=return | RankIC | 6 | 32 / 2024-01-31–2026-08-31 | F/state | 0.046858 | 0.041018 | 0.013541 |
| family=core; era=SW2021; level=L2; cohort=FC; task=return; horizon=60; objective=rank | RankIC | 6 | 18 / 2025-01-27–2026-06-30 | F/interaction | 0.136498 | 0.095480 | 0.094591 |
| family=core; era=SW2021; level=L2; cohort=FC; task=return; horizon=60; objective=return | RankIC | 6 | 18 / 2025-01-27–2026-06-30 | F/interaction | 0.116147 | 0.040523 | 0.035918 |
| family=core; era=SW2021; level=L2; cohort=FD; task=return; horizon=20; objective=rank | RankIC | 6 | 32 / 2024-01-31–2026-08-31 | FD/base | 0.074729 | 0.073460 | 0.032176 |
| family=core; era=SW2021; level=L2; cohort=FD; task=return; horizon=20; objective=return | RankIC | 6 | 32 / 2024-01-31–2026-08-31 | FD/base | 0.046304 | 0.043414 | 0.002273 |
| family=core; era=SW2021; level=L2; cohort=FD; task=return; horizon=60; objective=rank | RankIC | 6 | 18 / 2025-01-27–2026-06-30 | FD/interaction | 0.151283 | 0.087796 | 0.084053 |
| family=core; era=SW2021; level=L2; cohort=FD; task=return; horizon=60; objective=return | RankIC | 6 | 18 / 2025-01-27–2026-06-30 | FD/interaction | 0.122722 | 0.049822 | 0.045559 |
| family=core; era=SW2021; level=L2; cohort=FDG; task=return; horizon=20; objective=rank | RankIC | 6 | 6 / 2024-01-31–2026-03-31 | FDG/base | 0.223655 | 0.197061 | 0.019702 |
| family=core; era=SW2021; level=L2; cohort=FDG; task=return; horizon=20; objective=return | RankIC | 6 | 6 / 2024-01-31–2026-03-31 | FDG/base | 0.167237 | 0.141900 | 0.052293 |
| family=core; era=SW2021; level=L2; cohort=FDG; task=return; horizon=60; objective=rank | RankIC | 6 | 3 / 2025-02-28–2026-03-31 | FDG/base | 0.314131 | 0.303532 | 0.120598 |
| family=core; era=SW2021; level=L2; cohort=FDG; task=return; horizon=60; objective=return | RankIC | 6 | 3 / 2025-02-28–2026-03-31 | F/base | 0.243631 | 0.232409 | 0.182946 |
| family=core; era=SW2021; level=L2; cohort=FG; task=return; horizon=20; objective=rank | RankIC | 6 | 6 / 2024-01-31–2026-03-31 | FG/base | 0.207599 | 0.197019 | 0.019702 |
| family=core; era=SW2021; level=L2; cohort=FG; task=return; horizon=20; objective=return | RankIC | 6 | 6 / 2024-01-31–2026-03-31 | FG/base | 0.155392 | 0.142770 | 0.052293 |
| family=core; era=SW2021; level=L2; cohort=FG; task=return; horizon=60; objective=rank | RankIC | 6 | 3 / 2025-02-28–2026-03-31 | F/base | 0.303532 | 0.294521 | 0.120598 |
| family=core; era=SW2021; level=L2; cohort=FG; task=return; horizon=60; objective=return | RankIC | 6 | 3 / 2025-02-28–2026-03-31 | F/base | 0.243631 | 0.211430 | 0.156324 |
| family=core; era=SW2021; level=L3; cohort=F; task=return; horizon=20; objective=rank | RankIC | 3 | 32 / 2024-01-31–2026-08-31 | F/state | 0.078519 | 0.078519 | 0.062275 |
| family=core; era=SW2021; level=L3; cohort=F; task=return; horizon=20; objective=return | RankIC | 3 | 32 / 2024-01-31–2026-08-31 | F/state | 0.065983 | 0.065710 | 0.045084 |
| family=core; era=SW2021; level=L3; cohort=F; task=return; horizon=60; objective=rank | RankIC | 3 | 18 / 2025-01-27–2026-06-30 | F/interaction | 0.099890 | 0.080866 | 0.080866 |
| family=core; era=SW2021; level=L3; cohort=F; task=return; horizon=60; objective=return | RankIC | 3 | 18 / 2025-01-27–2026-06-30 | F/interaction | 0.091275 | 0.078656 | 0.078566 |
| family=core; era=SW2021; level=L3; cohort=FC; task=return; horizon=20; objective=rank | RankIC | 6 | 32 / 2024-01-31–2026-08-31 | FC/state | 0.071043 | 0.069833 | 0.045904 |
| family=core; era=SW2021; level=L3; cohort=FC; task=return; horizon=20; objective=return | RankIC | 6 | 32 / 2024-01-31–2026-08-31 | FC/state | 0.061426 | 0.055429 | 0.032618 |
| family=core; era=SW2021; level=L3; cohort=FC; task=return; horizon=60; objective=rank | RankIC | 6 | 18 / 2025-01-27–2026-06-30 | F/interaction | 0.095250 | 0.077060 | 0.076088 |
| family=core; era=SW2021; level=L3; cohort=FC; task=return; horizon=60; objective=return | RankIC | 6 | 18 / 2025-01-27–2026-06-30 | F/interaction | 0.094533 | 0.074987 | 0.072081 |
| family=core; era=SW2021; level=L3; cohort=FD; task=return; horizon=20; objective=rank | RankIC | 6 | 32 / 2024-01-31–2026-08-31 | FD/base | 0.082711 | 0.078608 | 0.061056 |
| family=core; era=SW2021; level=L3; cohort=FD; task=return; horizon=20; objective=return | RankIC | 6 | 32 / 2024-01-31–2026-08-31 | F/state | 0.066106 | 0.065175 | 0.043761 |
| family=core; era=SW2021; level=L3; cohort=FD; task=return; horizon=60; objective=rank | RankIC | 6 | 18 / 2025-01-27–2026-06-30 | FD/interaction | 0.110115 | 0.083952 | 0.080866 |
| family=core; era=SW2021; level=L3; cohort=FD; task=return; horizon=60; objective=return | RankIC | 6 | 18 / 2025-01-27–2026-06-30 | FD/interaction | 0.101074 | 0.083802 | 0.078224 |
| family=core; era=SW2021; level=L3; cohort=FDG; task=return; horizon=20; objective=rank | RankIC | 6 | 32 / 2024-01-31–2026-08-31 | FDG/base | 0.098428 | 0.091212 | 0.064667 |
| family=core; era=SW2021; level=L3; cohort=FDG; task=return; horizon=20; objective=return | RankIC | 6 | 32 / 2024-01-31–2026-08-31 | F/interaction | 0.077076 | 0.069107 | 0.067364 |
| family=core; era=SW2021; level=L3; cohort=FDG; task=return; horizon=60; objective=rank | RankIC | 6 | 18 / 2025-01-27–2026-06-30 | F/base | 0.090301 | 0.070766 | 0.065130 |
| family=core; era=SW2021; level=L3; cohort=FDG; task=return; horizon=60; objective=return | RankIC | 6 | 18 / 2025-01-27–2026-06-30 | F/state | 0.031278 | 0.022374 | 0.005908 |
| family=core; era=SW2021; level=L3; cohort=FG; task=return; horizon=20; objective=rank | RankIC | 6 | 32 / 2024-01-31–2026-08-31 | F/base | 0.089184 | 0.088264 | 0.063570 |
| family=core; era=SW2021; level=L3; cohort=FG; task=return; horizon=20; objective=return | RankIC | 6 | 32 / 2024-01-31–2026-08-31 | FG/interaction | 0.085157 | 0.074297 | 0.068973 |
| family=core; era=SW2021; level=L3; cohort=FG; task=return; horizon=60; objective=rank | RankIC | 6 | 18 / 2025-01-27–2026-06-30 | F/base | 0.091075 | 0.064365 | 0.035363 |
| family=core; era=SW2021; level=L3; cohort=FG; task=return; horizon=60; objective=return | RankIC | 6 | 18 / 2025-01-27–2026-06-30 | F/base | 0.031357 | 0.013087 | -0.004810 |
| family=l1; era=SW2021; level=L1; cohort=F; task=return; horizon=20; objective=rank | RankIC | 3 | 32 / 2024-01-31–2026-08-31 | F/base | 0.080192 | 0.080192 | 0.017213 |
| family=l1; era=SW2021; level=L1; cohort=F; task=return; horizon=20; objective=return | RankIC | 3 | 32 / 2024-01-31–2026-08-31 | F/base | 0.042024 | 0.042024 | 0.028453 |
| family=l1; era=SW2021; level=L1; cohort=F; task=return; horizon=60; objective=rank | RankIC | 3 | 18 / 2025-01-27–2026-06-30 | F/interaction | 0.150134 | 0.058221 | 0.058221 |
| family=l1; era=SW2021; level=L1; cohort=F; task=return; horizon=60; objective=return | RankIC | 3 | 18 / 2025-01-27–2026-06-30 | F/interaction | 0.145273 | 0.088866 | 0.088866 |
| family=l1; era=SW2021; level=L1; cohort=FD; task=return; horizon=20; objective=rank | RankIC | 6 | 32 / 2024-01-31–2026-08-31 | F/base | 0.080192 | 0.057082 | 0.017213 |
| family=l1; era=SW2021; level=L1; cohort=FD; task=return; horizon=20; objective=return | RankIC | 6 | 32 / 2024-01-31–2026-08-31 | F/base | 0.042024 | 0.032901 | 0.018838 |
| family=l1; era=SW2021; level=L1; cohort=FD; task=return; horizon=60; objective=rank | RankIC | 6 | 18 / 2025-01-27–2026-06-30 | FD/interaction | 0.156093 | 0.061694 | 0.058221 |
| family=l1; era=SW2021; level=L1; cohort=FD; task=return; horizon=60; objective=return | RankIC | 6 | 18 / 2025-01-27–2026-06-30 | FD/interaction | 0.159095 | 0.100515 | 0.088866 |
| family=core; era=SW2014; level=L2; cohort=F; task=reversal; horizon=20; objective=reversal | Brier | 3 | 10 / 2021-01-29–2021-10-29 | F/base | 0.087087 | 0.087168 | 0.088229 |
| family=core; era=SW2014; level=L2; cohort=FC; task=reversal; horizon=20; objective=reversal | Brier | 6 | 10 / 2021-01-29–2021-10-29 | F/base | 0.086842 | 0.087432 | 0.087989 |
| family=core; era=SW2014; level=L2; cohort=FD; task=reversal; horizon=20; objective=reversal | Brier | 6 | 10 / 2021-01-29–2021-10-29 | F/base | 0.086682 | 0.086798 | 0.088006 |
| family=core; era=SW2014; level=L3; cohort=F; task=reversal; horizon=20; objective=reversal | Brier | 3 | 22 / 2020-01-23–2021-10-29 | F/base | 0.125629 | 0.129244 | 0.131029 |
| family=core; era=SW2014; level=L3; cohort=FC; task=reversal; horizon=20; objective=reversal | Brier | 6 | 10 / 2021-01-29–2021-10-29 | FC/base | 0.099921 | 0.100701 | 0.102371 |
| family=core; era=SW2014; level=L3; cohort=FD; task=reversal; horizon=20; objective=reversal | Brier | 6 | 22 / 2020-01-23–2021-10-29 | F/base | 0.125191 | 0.128319 | 0.130375 |
| family=core; era=SW2021; level=L2; cohort=F; task=reversal; horizon=20; objective=reversal | Brier | 3 | 20 / 2025-01-27–2026-08-31 | F/state | 0.160996 | 0.161589 | 0.162100 |
| family=core; era=SW2021; level=L2; cohort=FC; task=reversal; horizon=20; objective=reversal | Brier | 6 | 20 / 2025-01-27–2026-08-31 | FC/state | 0.167270 | 0.167728 | 0.167992 |
| family=core; era=SW2021; level=L2; cohort=FD; task=reversal; horizon=20; objective=reversal | Brier | 6 | 20 / 2025-01-27–2026-08-31 | FD/state | 0.159810 | 0.161104 | 0.162096 |
| family=core; era=SW2021; level=L3; cohort=F; task=reversal; horizon=20; objective=reversal | Brier | 3 | 20 / 2025-01-27–2026-08-31 | F/state | 0.162922 | 0.163212 | 0.166973 |
| family=core; era=SW2021; level=L3; cohort=FC; task=reversal; horizon=20; objective=reversal | Brier | 6 | 20 / 2025-01-27–2026-08-31 | F/interaction | 0.190147 | 0.191753 | 0.192254 |
| family=core; era=SW2021; level=L3; cohort=FD; task=reversal; horizon=20; objective=reversal | Brier | 6 | 20 / 2025-01-27–2026-08-31 | FD/state | 0.162433 | 0.163072 | 0.167431 |
| family=core; era=SW2021; level=L3; cohort=FDG; task=reversal; horizon=20; objective=reversal | Brier | 6 | 12 / 2025-01-27–2025-12-31 | FDG/base | 0.097127 | 0.098268 | 0.104534 |
| family=core; era=SW2021; level=L3; cohort=FG; task=reversal; horizon=20; objective=reversal | Brier | 6 | 12 / 2025-01-27–2025-12-31 | FG/base | 0.097143 | 0.098058 | 0.104616 |

## r199

| 分组 | 指标 | 候选数 | 共同日期数／区间 | 最佳候选 | 最佳 | 中位数 | 最差 |
|---|---|---|---|---|---|---|---|
| family=financing; era=SW2021; level=L3; cohort=financing; task=onset; horizon=20; objective=onset | Brier | 6 | 16 / 2025-01-27–2026-04-30 | FS/state | 0.163920 | 0.164217 | 0.165262 |
| family=market_style; era=SW2014; level=L2; cohort=market_style; task=onset; horizon=20; objective=onset | Brier | 12 | 22 / 2020-01-23–2021-10-29 | FS/state | 0.169044 | 0.169812 | 0.170608 |
| family=market_style; era=SW2014; level=L3; cohort=market_style; task=onset; horizon=20; objective=onset | Brier | 12 | 22 / 2020-01-23–2021-10-29 | FSM/base | 0.171916 | 0.172291 | 0.172844 |
| family=market_style; era=SW2021; level=L2; cohort=market_style; task=onset; horizon=20; objective=onset | Brier | 12 | 20 / 2025-01-27–2026-08-31 | FSM/interaction | 0.142210 | 0.142999 | 0.145019 |
| family=market_style; era=SW2021; level=L3; cohort=market_style; task=onset; horizon=20; objective=onset | Brier | 12 | 20 / 2025-01-27–2026-08-31 | FSM/base | 0.152635 | 0.154213 | 0.157558 |
| family=size_diffusion; era=SW2014; level=L2; cohort=size_diffusion; task=onset; horizon=20; objective=onset | Brier | 12 | 22 / 2020-01-23–2021-10-29 | F/interaction | 0.167588 | 0.168054 | 0.169022 |
| family=size_diffusion; era=SW2014; level=L3; cohort=size_diffusion; task=onset; horizon=20; objective=onset | Brier | 12 | 22 / 2020-01-23–2021-10-29 | FD/interaction | 0.171544 | 0.171837 | 0.172616 |
| family=size_diffusion; era=SW2021; level=L2; cohort=size_diffusion; task=onset; horizon=20; objective=onset | Brier | 12 | 20 / 2025-01-27–2026-08-31 | F/base | 0.141137 | 0.144260 | 0.148692 |
| family=size_diffusion; era=SW2021; level=L3; cohort=size_diffusion; task=onset; horizon=20; objective=onset | Brier | 12 | 20 / 2025-01-27–2026-08-31 | F/base | 0.152074 | 0.154203 | 0.158716 |
| family=financing; era=SW2021; level=L2; cohort=financing; task=return; horizon=20; objective=return | RankIC | 6 | 28 / 2024-01-31–2026-04-30 | FSE/base | 0.008312 | 0.003499 | -0.010898 |
| family=financing; era=SW2021; level=L2; cohort=financing; task=return; horizon=60; objective=return | RankIC | 6 | 16 / 2025-01-27–2026-04-30 | FS/interaction | -0.054519 | -0.117680 | -0.134061 |
| family=financing; era=SW2021; level=L3; cohort=financing; task=return; horizon=20; objective=return | RankIC | 6 | 28 / 2024-01-31–2026-04-30 | FS/interaction | 0.017360 | -0.010711 | -0.012493 |
| family=financing; era=SW2021; level=L3; cohort=financing; task=return; horizon=60; objective=return | RankIC | 6 | 16 / 2025-01-27–2026-04-30 | FS/interaction | 0.020908 | -0.052177 | -0.059558 |
| family=market_style; era=SW2014; level=L2; cohort=market_style; task=return; horizon=20; objective=return | RankIC | 12 | 22 / 2020-01-23–2021-10-29 | FS/interaction | 0.025562 | -0.006159 | -0.014530 |
| family=market_style; era=SW2014; level=L2; cohort=market_style; task=return; horizon=60; objective=return | RankIC | 12 | 19 / 2020-01-23–2021-07-30 | FSMD/interaction | 0.056830 | 0.014145 | -0.011769 |
| family=market_style; era=SW2014; level=L3; cohort=market_style; task=return; horizon=20; objective=return | RankIC | 12 | 22 / 2020-01-23–2021-10-29 | FS/interaction | 0.071549 | -0.008219 | -0.025415 |
| family=market_style; era=SW2014; level=L3; cohort=market_style; task=return; horizon=60; objective=return | RankIC | 12 | 19 / 2020-01-23–2021-07-30 | FSM/interaction | 0.090117 | -0.011384 | -0.049455 |
| family=market_style; era=SW2021; level=L1; cohort=market_style; task=return; horizon=20; objective=return | RankIC | 12 | 20 / 2025-01-27–2026-08-31 | FSM/base | 0.079637 | 0.050595 | -0.037601 |
| family=market_style; era=SW2021; level=L1; cohort=market_style; task=return; horizon=60; objective=return | RankIC | 12 | 18 / 2025-01-27–2026-06-30 | FSD/interaction | 0.170363 | 0.116331 | 0.075582 |
| family=market_style; era=SW2021; level=L2; cohort=market_style; task=return; horizon=20; objective=return | RankIC | 12 | 20 / 2025-01-27–2026-08-31 | FSM/state | 0.094396 | 0.050587 | 0.021047 |
| family=market_style; era=SW2021; level=L2; cohort=market_style; task=return; horizon=60; objective=return | RankIC | 12 | 18 / 2025-01-27–2026-06-30 | FSD/interaction | 0.129231 | 0.099908 | 0.063670 |
| family=market_style; era=SW2021; level=L3; cohort=market_style; task=return; horizon=20; objective=return | RankIC | 12 | 20 / 2025-01-27–2026-08-31 | FSMD/base | 0.101610 | 0.079188 | 0.044517 |
| family=market_style; era=SW2021; level=L3; cohort=market_style; task=return; horizon=60; objective=return | RankIC | 12 | 18 / 2025-01-27–2026-06-30 | FSMD/base | 0.127967 | 0.117421 | 0.084253 |
| family=size_diffusion; era=SW2014; level=L2; cohort=size_diffusion; task=return; horizon=20; objective=return | RankIC | 12 | 22 / 2020-01-23–2021-10-29 | FS/interaction | 0.016981 | -0.000788 | -0.010955 |
| family=size_diffusion; era=SW2014; level=L2; cohort=size_diffusion; task=return; horizon=60; objective=return | RankIC | 12 | 19 / 2020-01-23–2021-07-30 | FD/interaction | 0.044098 | 0.016540 | -0.016660 |
| family=size_diffusion; era=SW2014; level=L3; cohort=size_diffusion; task=return; horizon=20; objective=return | RankIC | 12 | 22 / 2020-01-23–2021-10-29 | FS/interaction | 0.071604 | -0.007297 | -0.022319 |
| family=size_diffusion; era=SW2014; level=L3; cohort=size_diffusion; task=return; horizon=60; objective=return | RankIC | 12 | 19 / 2020-01-23–2021-07-30 | F/interaction | 0.076144 | -0.046862 | -0.054298 |
| family=size_diffusion; era=SW2021; level=L1; cohort=size_diffusion; task=return; horizon=20; objective=return | RankIC | 12 | 32 / 2024-01-31–2026-08-31 | FS/base | 0.044960 | 0.036007 | 0.018838 |
| family=size_diffusion; era=SW2021; level=L1; cohort=size_diffusion; task=return; horizon=60; objective=return | RankIC | 12 | 18 / 2025-01-27–2026-06-30 | FDS/interaction | 0.166823 | 0.094691 | 0.075336 |
| family=size_diffusion; era=SW2021; level=L2; cohort=size_diffusion; task=return; horizon=20; objective=return | RankIC | 12 | 32 / 2024-01-31–2026-08-31 | FDS/state | 0.052362 | 0.043964 | 0.002273 |
| family=size_diffusion; era=SW2021; level=L2; cohort=size_diffusion; task=return; horizon=60; objective=return | RankIC | 12 | 18 / 2025-01-27–2026-06-30 | FDS/interaction | 0.137814 | 0.064520 | 0.045559 |
| family=size_diffusion; era=SW2021; level=L3; cohort=size_diffusion; task=return; horizon=20; objective=return | RankIC | 12 | 32 / 2024-01-31–2026-08-31 | FDS/state | 0.078864 | 0.065755 | 0.043690 |
| family=size_diffusion; era=SW2021; level=L3; cohort=size_diffusion; task=return; horizon=60; objective=return | RankIC | 12 | 18 / 2025-01-27–2026-06-30 | FDS/interaction | 0.121110 | 0.104633 | 0.078136 |
| family=financing; era=SW2021; level=L3; cohort=financing; task=reversal; horizon=20; objective=reversal | Brier | 6 | 16 / 2025-01-27–2026-04-30 | FSE/interaction | 0.157143 | 0.161127 | 0.162449 |
| family=market_style; era=SW2014; level=L2; cohort=market_style; task=reversal; horizon=20; objective=reversal | Brier | 12 | 10 / 2021-01-29–2021-10-29 | FSM/interaction | 0.086413 | 0.087255 | 0.092586 |
| family=market_style; era=SW2014; level=L3; cohort=market_style; task=reversal; horizon=20; objective=reversal | Brier | 12 | 22 / 2020-01-23–2021-10-29 | FS/base | 0.126991 | 0.131563 | 0.132765 |
| family=market_style; era=SW2021; level=L2; cohort=market_style; task=reversal; horizon=20; objective=reversal | Brier | 12 | 20 / 2025-01-27–2026-08-31 | FSM/state | 0.152132 | 0.158123 | 0.166255 |
| family=market_style; era=SW2021; level=L3; cohort=market_style; task=reversal; horizon=20; objective=reversal | Brier | 12 | 20 / 2025-01-27–2026-08-31 | FSMD/state | 0.156432 | 0.161389 | 0.167304 |
| family=size_diffusion; era=SW2014; level=L2; cohort=size_diffusion; task=reversal; horizon=20; objective=reversal | Brier | 12 | 10 / 2021-01-29–2021-10-29 | F/base | 0.086719 | 0.086834 | 0.088070 |
| family=size_diffusion; era=SW2014; level=L3; cohort=size_diffusion; task=reversal; horizon=20; objective=reversal | Brier | 12 | 22 / 2020-01-23–2021-10-29 | F/base | 0.125161 | 0.128839 | 0.131020 |
| family=size_diffusion; era=SW2021; level=L2; cohort=size_diffusion; task=reversal; horizon=20; objective=reversal | Brier | 12 | 20 / 2025-01-27–2026-08-31 | FDS/state | 0.158659 | 0.161104 | 0.162189 |
| family=size_diffusion; era=SW2021; level=L3; cohort=size_diffusion; task=reversal; horizon=20; objective=reversal | Brier | 12 | 20 / 2025-01-27–2026-08-31 | FD/state | 0.162439 | 0.163117 | 0.168370 |
| family=financing; era=SW2021; level=L2; cohort=financing; task=return; horizon=20; objective=return | MSE | 6 | 28 / 2024-01-31–2026-04-30 | FSE/base | 0.004473 | 0.004516 | 0.004881 |
| family=financing; era=SW2021; level=L2; cohort=financing; task=return; horizon=60; objective=return | MSE | 6 | 16 / 2025-01-27–2026-04-30 | FSE/state | 0.024887 | 0.025018 | 0.025447 |
| family=financing; era=SW2021; level=L3; cohort=financing; task=return; horizon=20; objective=return | MSE | 6 | 28 / 2024-01-31–2026-04-30 | FS/base | 0.005444 | 0.005470 | 0.005886 |
| family=financing; era=SW2021; level=L3; cohort=financing; task=return; horizon=60; objective=return | MSE | 6 | 16 / 2025-01-27–2026-04-30 | FS/interaction | 0.028015 | 0.028195 | 0.028504 |
| family=market_style; era=SW2014; level=L2; cohort=market_style; task=return; horizon=20; objective=return | MSE | 12 | 22 / 2020-01-23–2021-10-29 | FSM/state | 0.004441 | 0.004504 | 0.004545 |
| family=market_style; era=SW2014; level=L2; cohort=market_style; task=return; horizon=60; objective=return | MSE | 12 | 19 / 2020-01-23–2021-07-30 | FSM/base | 0.013832 | 0.014807 | 0.014887 |
| family=market_style; era=SW2014; level=L3; cohort=market_style; task=return; horizon=20; objective=return | MSE | 12 | 22 / 2020-01-23–2021-10-29 | FS/interaction | 0.005460 | 0.005473 | 0.005609 |
| family=market_style; era=SW2014; level=L3; cohort=market_style; task=return; horizon=60; objective=return | MSE | 12 | 19 / 2020-01-23–2021-07-30 | FSM/base | 0.018568 | 0.019617 | 0.019760 |
| family=market_style; era=SW2021; level=L1; cohort=market_style; task=return; horizon=20; objective=return | MSE | 12 | 20 / 2025-01-27–2026-08-31 | FS/base | 0.003817 | 0.003962 | 0.004151 |
| family=market_style; era=SW2021; level=L1; cohort=market_style; task=return; horizon=60; objective=return | MSE | 12 | 18 / 2025-01-27–2026-06-30 | FSMD/state | 0.009748 | 0.009814 | 0.009982 |
| family=market_style; era=SW2021; level=L2; cohort=market_style; task=return; horizon=20; objective=return | MSE | 12 | 20 / 2025-01-27–2026-08-31 | FSMD/base | 0.005377 | 0.005518 | 0.005683 |
| family=market_style; era=SW2021; level=L2; cohort=market_style; task=return; horizon=60; objective=return | MSE | 12 | 18 / 2025-01-27–2026-06-30 | FSD/interaction | 0.015508 | 0.015633 | 0.015801 |
| family=market_style; era=SW2021; level=L3; cohort=market_style; task=return; horizon=20; objective=return | MSE | 12 | 20 / 2025-01-27–2026-08-31 | FSMD/base | 0.006170 | 0.006280 | 0.006409 |
| family=market_style; era=SW2021; level=L3; cohort=market_style; task=return; horizon=60; objective=return | MSE | 12 | 18 / 2025-01-27–2026-06-30 | FSMD/base | 0.017670 | 0.017712 | 0.017964 |
| family=size_diffusion; era=SW2014; level=L2; cohort=size_diffusion; task=return; horizon=20; objective=return | MSE | 12 | 22 / 2020-01-23–2021-10-29 | F/state | 0.004444 | 0.004514 | 0.004545 |
| family=size_diffusion; era=SW2014; level=L2; cohort=size_diffusion; task=return; horizon=60; objective=return | MSE | 12 | 19 / 2020-01-23–2021-07-30 | F/base | 0.013923 | 0.014975 | 0.015031 |
| family=size_diffusion; era=SW2014; level=L3; cohort=size_diffusion; task=return; horizon=20; objective=return | MSE | 12 | 22 / 2020-01-23–2021-10-29 | F/state | 0.005439 | 0.005452 | 0.005587 |
| family=size_diffusion; era=SW2014; level=L3; cohort=size_diffusion; task=return; horizon=60; objective=return | MSE | 12 | 19 / 2020-01-23–2021-07-30 | FS/base | 0.018570 | 0.019690 | 0.019769 |
| family=size_diffusion; era=SW2021; level=L1; cohort=size_diffusion; task=return; horizon=20; objective=return | MSE | 12 | 32 / 2024-01-31–2026-08-31 | F/base | 0.003509 | 0.003794 | 0.003965 |
| family=size_diffusion; era=SW2021; level=L1; cohort=size_diffusion; task=return; horizon=60; objective=return | MSE | 12 | 18 / 2025-01-27–2026-06-30 | FD/interaction | 0.009748 | 0.009835 | 0.009903 |
| family=size_diffusion; era=SW2021; level=L2; cohort=size_diffusion; task=return; horizon=20; objective=return | MSE | 12 | 32 / 2024-01-31–2026-08-31 | FD/base | 0.004870 | 0.005173 | 0.005402 |
| family=size_diffusion; era=SW2021; level=L2; cohort=size_diffusion; task=return; horizon=60; objective=return | MSE | 12 | 18 / 2025-01-27–2026-06-30 | FD/interaction | 0.015401 | 0.015608 | 0.015742 |
| family=size_diffusion; era=SW2021; level=L3; cohort=size_diffusion; task=return; horizon=20; objective=return | MSE | 12 | 32 / 2024-01-31–2026-08-31 | FD/base | 0.005642 | 0.006054 | 0.006317 |
| family=size_diffusion; era=SW2021; level=L3; cohort=size_diffusion; task=return; horizon=60; objective=return | MSE | 12 | 18 / 2025-01-27–2026-06-30 | FD/interaction | 0.017540 | 0.017661 | 0.017777 |

## r200

| 分组 | 指标 | 候选数 | 共同日期数／区间 | 最佳候选 | 最佳 | 中位数 | 最差 |
|---|---|---|---|---|---|---|---|
| family=catchup_main80; era=SW2014; level=L2; cohort=catchup_main80; task=catchup; horizon=0; objective=catchup | RankIC | 6 | 23 / 2020-01-23–2021-11-30 | controls/state | 0.065553 | 0.049563 | 0.038415 |
| family=catchup_main80; era=SW2014; level=L3; cohort=catchup_main80; task=catchup; horizon=0; objective=catchup | RankIC | 6 | 23 / 2020-01-23–2021-11-30 | with_leader/state | 0.005397 | 0.004041 | -0.011814 |
| family=catchup_main80; era=SW2021; level=L1; cohort=catchup_main80; task=catchup; horizon=0; objective=catchup | RankIC | 6 | 1 / 2026-07-31–2026-07-31 | controls/state | 0.326957 | 0.266957 | -0.062609 |
| family=catchup_main80; era=SW2021; level=L2; cohort=catchup_main80; task=catchup; horizon=0; objective=catchup | RankIC | 6 | 19 / 2025-01-27–2026-07-31 | controls/base | 0.049032 | 0.039854 | 0.027912 |
| family=catchup_main80; era=SW2021; level=L3; cohort=catchup_main80; task=catchup; horizon=0; objective=catchup | RankIC | 6 | 19 / 2025-01-27–2026-07-31 | controls/state | 0.060049 | 0.045277 | 0.039656 |
| family=catchup_strict100; era=SW2014; level=L2; cohort=catchup_strict100; task=catchup; horizon=0; objective=catchup | RankIC | 6 | 23 / 2020-01-23–2021-11-30 | controls/state | 0.052555 | 0.033675 | 0.023700 |
| family=catchup_strict100; era=SW2014; level=L3; cohort=catchup_strict100; task=catchup; horizon=0; objective=catchup | RankIC | 6 | 23 / 2020-01-23–2021-11-30 | with_leader/base | 0.004804 | 0.001357 | -0.015070 |
| family=catchup_strict100; era=SW2021; level=L1; cohort=catchup_strict100; task=catchup; horizon=0; objective=catchup | RankIC | 6 | 1 / 2026-07-31–2026-07-31 | with_leader/state | 0.393043 | 0.313043 | 0.044348 |
| family=catchup_strict100; era=SW2021; level=L2; cohort=catchup_strict100; task=catchup; horizon=0; objective=catchup | RankIC | 6 | 19 / 2025-01-27–2026-07-31 | controls/base | 0.054534 | 0.044701 | 0.022467 |
| family=catchup_strict100; era=SW2021; level=L3; cohort=catchup_strict100; task=catchup; horizon=0; objective=catchup | RankIC | 6 | 19 / 2025-01-27–2026-07-31 | controls/state | 0.055839 | 0.038237 | 0.031118 |
| family=leader_main80; era=SW2014; level=L2; cohort=leader_main80; task=onset; horizon=20; objective=onset | Brier | 6 | 22 / 2020-01-23–2021-10-29 | controls/state | 0.175572 | 0.175724 | 0.176019 |
| family=leader_main80; era=SW2014; level=L3; cohort=leader_main80; task=onset; horizon=20; objective=onset | Brier | 6 | 22 / 2020-01-23–2021-10-29 | with_leader/base | 0.175035 | 0.175344 | 0.175849 |
| family=leader_main80; era=SW2021; level=L2; cohort=leader_main80; task=onset; horizon=20; objective=onset | Brier | 6 | 20 / 2025-01-27–2026-08-31 | with_leader/state | 0.141743 | 0.142891 | 0.143539 |
| family=leader_main80; era=SW2021; level=L3; cohort=leader_main80; task=onset; horizon=20; objective=onset | Brier | 6 | 20 / 2025-01-27–2026-08-31 | with_leader/state | 0.150966 | 0.151184 | 0.154304 |
| family=leader_strict100; era=SW2014; level=L2; cohort=leader_strict100; task=onset; horizon=20; objective=onset | Brier | 6 | 22 / 2020-01-23–2021-10-29 | with_leader/interaction | 0.168811 | 0.169463 | 0.170321 |
| family=leader_strict100; era=SW2014; level=L3; cohort=leader_strict100; task=onset; horizon=20; objective=onset | Brier | 6 | 22 / 2020-01-23–2021-10-29 | with_leader/base | 0.172350 | 0.172668 | 0.173302 |
| family=leader_strict100; era=SW2021; level=L2; cohort=leader_strict100; task=onset; horizon=20; objective=onset | Brier | 6 | 20 / 2025-01-27–2026-08-31 | controls/base | 0.138045 | 0.138349 | 0.139838 |
| family=leader_strict100; era=SW2021; level=L3; cohort=leader_strict100; task=onset; horizon=20; objective=onset | Brier | 6 | 20 / 2025-01-27–2026-08-31 | with_leader/state | 0.148616 | 0.149400 | 0.151724 |
| family=leader_main80; era=SW2014; level=L2; cohort=leader_main80; task=return; horizon=20; objective=return | RankIC | 6 | 22 / 2020-01-23–2021-10-29 | with_leader/base | 0.044254 | 0.017645 | -0.011413 |
| family=leader_main80; era=SW2014; level=L2; cohort=leader_main80; task=return; horizon=60; objective=return | RankIC | 6 | 19 / 2020-01-23–2021-07-30 | with_leader/base | 0.076158 | 0.074365 | 0.038299 |
| family=leader_main80; era=SW2014; level=L3; cohort=leader_main80; task=return; horizon=20; objective=return | RankIC | 6 | 22 / 2020-01-23–2021-10-29 | with_leader/interaction | 0.042970 | 0.038126 | 0.006981 |
| family=leader_main80; era=SW2014; level=L3; cohort=leader_main80; task=return; horizon=60; objective=return | RankIC | 6 | 19 / 2020-01-23–2021-07-30 | with_leader/interaction | 0.100372 | 0.019534 | 0.006573 |
| family=leader_main80; era=SW2021; level=L1; cohort=leader_main80; task=return; horizon=20; objective=return | RankIC | 6 | 8 / 2025-01-27–2026-08-31 | controls/base | 0.063235 | 0.050728 | -0.150139 |
| family=leader_main80; era=SW2021; level=L1; cohort=leader_main80; task=return; horizon=60; objective=return | RankIC | 6 | 6 / 2025-01-27–2026-06-30 | with_leader/base | 0.124892 | 0.111436 | 0.088114 |
| family=leader_main80; era=SW2021; level=L2; cohort=leader_main80; task=return; horizon=20; objective=return | RankIC | 6 | 20 / 2025-01-27–2026-08-31 | controls/base | 0.080899 | 0.080462 | 0.002375 |
| family=leader_main80; era=SW2021; level=L2; cohort=leader_main80; task=return; horizon=60; objective=return | RankIC | 6 | 18 / 2025-01-27–2026-06-30 | controls/interaction | 0.093707 | 0.089054 | 0.086178 |
| family=leader_main80; era=SW2021; level=L3; cohort=leader_main80; task=return; horizon=20; objective=return | RankIC | 6 | 20 / 2025-01-27–2026-08-31 | controls/state | 0.096396 | 0.095974 | 0.036325 |
| family=leader_main80; era=SW2021; level=L3; cohort=leader_main80; task=return; horizon=60; objective=return | RankIC | 6 | 18 / 2025-01-27–2026-06-30 | controls/base | 0.129482 | 0.125314 | 0.099232 |
| family=leader_strict100; era=SW2014; level=L2; cohort=leader_strict100; task=return; horizon=20; objective=return | RankIC | 6 | 22 / 2020-01-23–2021-10-29 | with_leader/state | 0.040177 | 0.002945 | -0.009432 |
| family=leader_strict100; era=SW2014; level=L2; cohort=leader_strict100; task=return; horizon=60; objective=return | RankIC | 6 | 19 / 2020-01-23–2021-07-30 | controls/state | 0.045895 | 0.042108 | 0.015475 |
| family=leader_strict100; era=SW2014; level=L3; cohort=leader_strict100; task=return; horizon=20; objective=return | RankIC | 6 | 22 / 2020-01-23–2021-10-29 | with_leader/interaction | 0.044214 | 0.033305 | -0.001561 |
| family=leader_strict100; era=SW2014; level=L3; cohort=leader_strict100; task=return; horizon=60; objective=return | RankIC | 6 | 19 / 2020-01-23–2021-07-30 | with_leader/interaction | 0.097573 | 0.014754 | 0.003641 |
| family=leader_strict100; era=SW2021; level=L1; cohort=leader_strict100; task=return; horizon=20; objective=return | RankIC | 6 | 3 / 2026-06-30–2026-08-31 | controls/base | 0.145869 | 0.139380 | -0.008098 |
| family=leader_strict100; era=SW2021; level=L1; cohort=leader_strict100; task=return; horizon=60; objective=return | RankIC | 6 | 1 / 2026-06-30–2026-06-30 | controls/base | -0.354037 | -0.376623 | -0.442123 |
| family=leader_strict100; era=SW2021; level=L2; cohort=leader_strict100; task=return; horizon=20; objective=return | RankIC | 6 | 20 / 2025-01-27–2026-08-31 | controls/base | 0.069329 | 0.067937 | -0.005008 |
| family=leader_strict100; era=SW2021; level=L2; cohort=leader_strict100; task=return; horizon=60; objective=return | RankIC | 6 | 18 / 2025-01-27–2026-06-30 | controls/interaction | 0.091738 | 0.077623 | 0.076864 |
| family=leader_strict100; era=SW2021; level=L3; cohort=leader_strict100; task=return; horizon=20; objective=return | RankIC | 6 | 20 / 2025-01-27–2026-08-31 | controls/base | 0.098439 | 0.097500 | 0.035564 |
| family=leader_strict100; era=SW2021; level=L3; cohort=leader_strict100; task=return; horizon=60; objective=return | RankIC | 6 | 18 / 2025-01-27–2026-06-30 | controls/base | 0.132046 | 0.127904 | 0.100143 |
| family=leader_main80; era=SW2014; level=L2; cohort=leader_main80; task=reversal; horizon=20; objective=reversal | Brier | 6 | 10 / 2021-01-29–2021-10-29 | with_leader/base | 0.086975 | 0.088179 | 0.092221 |
| family=leader_main80; era=SW2014; level=L3; cohort=leader_main80; task=reversal; horizon=20; objective=reversal | Brier | 6 | 22 / 2020-01-23–2021-10-29 | with_leader/base | 0.127628 | 0.132398 | 0.133634 |
| family=leader_main80; era=SW2021; level=L2; cohort=leader_main80; task=reversal; horizon=20; objective=reversal | Brier | 6 | 20 / 2025-01-27–2026-08-31 | controls/state | 0.158240 | 0.158757 | 0.163678 |
| family=leader_main80; era=SW2021; level=L3; cohort=leader_main80; task=reversal; horizon=20; objective=reversal | Brier | 6 | 20 / 2025-01-27–2026-08-31 | controls/state | 0.157752 | 0.158534 | 0.167414 |
| family=leader_strict100; era=SW2014; level=L2; cohort=leader_strict100; task=reversal; horizon=20; objective=reversal | Brier | 6 | 10 / 2021-01-29–2021-10-29 | with_leader/interaction | 0.087386 | 0.088646 | 0.094737 |
| family=leader_strict100; era=SW2014; level=L3; cohort=leader_strict100; task=reversal; horizon=20; objective=reversal | Brier | 6 | 22 / 2020-01-23–2021-10-29 | with_leader/base | 0.127598 | 0.132286 | 0.133065 |
| family=leader_strict100; era=SW2021; level=L2; cohort=leader_strict100; task=reversal; horizon=20; objective=reversal | Brier | 6 | 20 / 2025-01-27–2026-08-31 | controls/state | 0.158787 | 0.159923 | 0.166101 |
| family=leader_strict100; era=SW2021; level=L3; cohort=leader_strict100; task=reversal; horizon=20; objective=reversal | Brier | 6 | 20 / 2025-01-27–2026-08-31 | controls/state | 0.159960 | 0.160740 | 0.168747 |
| family=catchup_main80; era=SW2014; level=L2; cohort=catchup_main80; task=catchup; horizon=0; objective=catchup | MSE | 6 | 23 / 2020-01-23–2021-11-30 | controls/base | 0.006998 | 0.007153 | 0.007234 |
| family=catchup_main80; era=SW2014; level=L3; cohort=catchup_main80; task=catchup; horizon=0; objective=catchup | MSE | 6 | 23 / 2020-01-23–2021-11-30 | with_leader/base | 0.008115 | 0.008235 | 0.008332 |
| family=catchup_main80; era=SW2021; level=L1; cohort=catchup_main80; task=catchup; horizon=0; objective=catchup | MSE | 6 | 19 / 2025-01-27–2026-07-31 | with_leader/base | 0.005084 | 0.005146 | 0.005426 |
| family=catchup_main80; era=SW2021; level=L2; cohort=catchup_main80; task=catchup; horizon=0; objective=catchup | MSE | 6 | 19 / 2025-01-27–2026-07-31 | controls/base | 0.006175 | 0.006311 | 0.006390 |
| family=catchup_main80; era=SW2021; level=L3; cohort=catchup_main80; task=catchup; horizon=0; objective=catchup | MSE | 6 | 19 / 2025-01-27–2026-07-31 | controls/base | 0.007664 | 0.007735 | 0.007792 |
| family=catchup_strict100; era=SW2014; level=L2; cohort=catchup_strict100; task=catchup; horizon=0; objective=catchup | MSE | 6 | 23 / 2020-01-23–2021-11-30 | controls/base | 0.006927 | 0.007109 | 0.007211 |
| family=catchup_strict100; era=SW2014; level=L3; cohort=catchup_strict100; task=catchup; horizon=0; objective=catchup | MSE | 6 | 23 / 2020-01-23–2021-11-30 | with_leader/base | 0.008141 | 0.008262 | 0.008365 |
| family=catchup_strict100; era=SW2021; level=L1; cohort=catchup_strict100; task=catchup; horizon=0; objective=catchup | MSE | 6 | 19 / 2025-01-27–2026-07-31 | with_leader/base | 0.005261 | 0.005385 | 0.005833 |
| family=catchup_strict100; era=SW2021; level=L2; cohort=catchup_strict100; task=catchup; horizon=0; objective=catchup | MSE | 6 | 19 / 2025-01-27–2026-07-31 | controls/base | 0.005856 | 0.005980 | 0.006093 |
| family=catchup_strict100; era=SW2021; level=L3; cohort=catchup_strict100; task=catchup; horizon=0; objective=catchup | MSE | 6 | 19 / 2025-01-27–2026-07-31 | controls/base | 0.007597 | 0.007666 | 0.007742 |
| family=leader_main80; era=SW2014; level=L2; cohort=leader_main80; task=return; horizon=20; objective=return | MSE | 6 | 22 / 2020-01-23–2021-10-29 | with_leader/state | 0.004448 | 0.004537 | 0.004552 |
| family=leader_main80; era=SW2014; level=L2; cohort=leader_main80; task=return; horizon=60; objective=return | MSE | 6 | 19 / 2020-01-23–2021-07-30 | with_leader/base | 0.014050 | 0.014993 | 0.015141 |
| family=leader_main80; era=SW2014; level=L3; cohort=leader_main80; task=return; horizon=20; objective=return | MSE | 6 | 22 / 2020-01-23–2021-10-29 | with_leader/state | 0.005517 | 0.005565 | 0.005665 |
| family=leader_main80; era=SW2014; level=L3; cohort=leader_main80; task=return; horizon=60; objective=return | MSE | 6 | 19 / 2020-01-23–2021-07-30 | with_leader/base | 0.019090 | 0.020097 | 0.020231 |
| family=leader_main80; era=SW2021; level=L1; cohort=leader_main80; task=return; horizon=20; objective=return | MSE | 6 | 20 / 2025-01-27–2026-08-31 | controls/base | 0.004151 | 0.004337 | 0.004609 |
| family=leader_main80; era=SW2021; level=L1; cohort=leader_main80; task=return; horizon=60; objective=return | MSE | 6 | 18 / 2025-01-27–2026-06-30 | with_leader/base | 0.010478 | 0.010512 | 0.010819 |
| family=leader_main80; era=SW2021; level=L2; cohort=leader_main80; task=return; horizon=20; objective=return | MSE | 6 | 20 / 2025-01-27–2026-08-31 | controls/base | 0.005545 | 0.005686 | 0.005909 |
| family=leader_main80; era=SW2021; level=L2; cohort=leader_main80; task=return; horizon=60; objective=return | MSE | 6 | 18 / 2025-01-27–2026-06-30 | controls/base | 0.016337 | 0.016343 | 0.016472 |
| family=leader_main80; era=SW2021; level=L3; cohort=leader_main80; task=return; horizon=20; objective=return | MSE | 6 | 20 / 2025-01-27–2026-08-31 | controls/base | 0.006278 | 0.006385 | 0.006538 |
| family=leader_main80; era=SW2021; level=L3; cohort=leader_main80; task=return; horizon=60; objective=return | MSE | 6 | 18 / 2025-01-27–2026-06-30 | controls/base | 0.017959 | 0.018005 | 0.018197 |
| family=leader_strict100; era=SW2014; level=L2; cohort=leader_strict100; task=return; horizon=20; objective=return | MSE | 6 | 22 / 2020-01-23–2021-10-29 | with_leader/state | 0.004453 | 0.004533 | 0.004566 |
| family=leader_strict100; era=SW2014; level=L2; cohort=leader_strict100; task=return; horizon=60; objective=return | MSE | 6 | 19 / 2020-01-23–2021-07-30 | with_leader/base | 0.014072 | 0.014914 | 0.015080 |
| family=leader_strict100; era=SW2014; level=L3; cohort=leader_strict100; task=return; horizon=20; objective=return | MSE | 6 | 22 / 2020-01-23–2021-10-29 | with_leader/state | 0.005521 | 0.005559 | 0.005682 |
| family=leader_strict100; era=SW2014; level=L3; cohort=leader_strict100; task=return; horizon=60; objective=return | MSE | 6 | 19 / 2020-01-23–2021-07-30 | with_leader/base | 0.019187 | 0.020211 | 0.020328 |
| family=leader_strict100; era=SW2021; level=L1; cohort=leader_strict100; task=return; horizon=20; objective=return | MSE | 6 | 20 / 2025-01-27–2026-08-31 | controls/base | 0.004456 | 0.004639 | 0.004906 |
| family=leader_strict100; era=SW2021; level=L1; cohort=leader_strict100; task=return; horizon=60; objective=return | MSE | 6 | 18 / 2025-01-27–2026-06-30 | with_leader/interaction | 0.010299 | 0.010374 | 0.010399 |
| family=leader_strict100; era=SW2021; level=L2; cohort=leader_strict100; task=return; horizon=20; objective=return | MSE | 6 | 20 / 2025-01-27–2026-08-31 | controls/base | 0.005488 | 0.005627 | 0.005834 |
| family=leader_strict100; era=SW2021; level=L2; cohort=leader_strict100; task=return; horizon=60; objective=return | MSE | 6 | 18 / 2025-01-27–2026-06-30 | controls/state | 0.016396 | 0.016425 | 0.016547 |
| family=leader_strict100; era=SW2021; level=L3; cohort=leader_strict100; task=return; horizon=20; objective=return | MSE | 6 | 20 / 2025-01-27–2026-08-31 | controls/base | 0.006256 | 0.006361 | 0.006509 |
| family=leader_strict100; era=SW2021; level=L3; cohort=leader_strict100; task=return; horizon=60; objective=return | MSE | 6 | 18 / 2025-01-27–2026-06-30 | controls/base | 0.017821 | 0.017836 | 0.018035 |

## r201

| 分组 | 指标 | 候选数 | 共同日期数／区间 | 最佳候选 | 最佳 | 中位数 | 最差 |
|---|---|---|---|---|---|---|---|
| family=common_main80; era=SW2021; level=L3; cohort=common_main80; task=return; horizon=20; objective=return | RankIC | 9 | 0 / None–None | None | — | — | — |
| family=common_main80; era=SW2021; level=L3; cohort=common_main80; task=return; horizon=60; objective=return | RankIC | 9 | 0 / None–None | None | — | — | — |
| family=notice_main80; era=SW2021; level=L3; cohort=notice_main80; task=return; horizon=20; objective=return | RankIC | 6 | 0 / None–None | None | — | — | — |
| family=notice_main80; era=SW2021; level=L3; cohort=notice_main80; task=return; horizon=60; objective=return | RankIC | 6 | 0 / None–None | None | — | — | — |
| family=update_main80; era=SW2021; level=L3; cohort=update_main80; task=return; horizon=20; objective=return | RankIC | 6 | 0 / None–None | None | — | — | — |
| family=update_main80; era=SW2021; level=L3; cohort=update_main80; task=return; horizon=60; objective=return | RankIC | 6 | 0 / None–None | None | — | — | — |
| family=common_main80; era=SW2021; level=L3; cohort=common_main80; task=return; horizon=20; objective=return | MSE | 9 | 15 / 2025-01-27–2026-08-31 | update_model/base | 0.008380 | 0.008591 | 0.008948 |
| family=common_main80; era=SW2021; level=L3; cohort=common_main80; task=return; horizon=60; objective=return | MSE | 9 | 3 / 2026-04-30–2026-06-30 | update_model/state | 0.020911 | 0.021599 | 0.023876 |
| family=notice_main80; era=SW2021; level=L3; cohort=notice_main80; task=return; horizon=20; objective=return | MSE | 6 | 20 / 2025-01-27–2026-08-31 | with_financial/base | 0.008125 | 0.008240 | 0.008706 |
| family=notice_main80; era=SW2021; level=L3; cohort=notice_main80; task=return; horizon=60; objective=return | MSE | 6 | 18 / 2025-01-27–2026-06-30 | controls/base | 0.021906 | 0.022390 | 0.024275 |
| family=update_main80; era=SW2021; level=L3; cohort=update_main80; task=return; horizon=20; objective=return | MSE | 6 | 15 / 2025-01-27–2026-08-31 | with_financial/base | 0.008380 | 0.008581 | 0.008895 |
| family=update_main80; era=SW2021; level=L3; cohort=update_main80; task=return; horizon=60; objective=return | MSE | 6 | 3 / 2026-04-30–2026-06-30 | with_financial/state | 0.020911 | 0.021534 | 0.023876 |

## r197

| 分组 | 指标 | 候选数 | 共同日期数／区间 | 最佳候选 | 最佳 | 中位数 | 最差 |
|---|---|---|---|---|---|---|---|
| family=eps_raw_proxy; era=SW2021; level=L1; fy_offset=0; population=partial_diagnostic; horizon=20 | MSE | 9 | 19 / 2025-01-27–2026-07-31 | price_only/base | 0.003329 | 0.003434 | 0.003631 |
| family=eps_raw_proxy; era=SW2021; level=L1; fy_offset=0; population=partial_diagnostic; horizon=60 | MSE | 9 | 18 / 2025-01-27–2026-06-30 | expectation_only/base | 0.009011 | 0.009128 | 0.009279 |
| family=eps_raw_proxy; era=SW2021; level=L1; fy_offset=1; population=partial_diagnostic; horizon=20 | MSE | 9 | 18 / 2025-01-27–2026-06-30 | expectation_only/base | 0.002503 | 0.002554 | 0.002704 |
| family=eps_raw_proxy; era=SW2021; level=L1; fy_offset=1; population=partial_diagnostic; horizon=60 | MSE | 9 | 18 / 2025-01-27–2026-06-30 | expectation_only/state | 0.008906 | 0.008979 | 0.009109 |
| family=eps_share_context_guard; era=SW2021; level=L1; fy_offset=0; population=partial_diagnostic; horizon=20 | MSE | 9 | 19 / 2025-01-27–2026-07-31 | price_only/base | 0.003329 | 0.003435 | 0.003635 |
| family=eps_share_context_guard; era=SW2021; level=L1; fy_offset=0; population=partial_diagnostic; horizon=60 | MSE | 9 | 18 / 2025-01-27–2026-06-30 | expectation_only/base | 0.009059 | 0.009178 | 0.009320 |
| family=eps_share_context_guard; era=SW2021; level=L1; fy_offset=1; population=partial_diagnostic; horizon=20 | MSE | 9 | 18 / 2025-01-27–2026-06-30 | expectation_only/base | 0.002502 | 0.002555 | 0.002708 |
| family=eps_share_context_guard; era=SW2021; level=L1; fy_offset=1; population=partial_diagnostic; horizon=60 | MSE | 9 | 18 / 2025-01-27–2026-06-30 | expectation_only/state | 0.008954 | 0.009025 | 0.009162 |
| family=profit_expectations; era=SW2021; level=L2; fy_offset=0; population=partial_diagnostic; horizon=20 | MSE | 9 | 8 / 2026-01-30–2026-08-31 | expectation_only/state | 0.008137 | 0.008272 | 0.008530 |
| family=profit_expectations; era=SW2021; level=L2; fy_offset=0; population=partial_diagnostic; horizon=60 | MSE | 9 | 6 / 2026-01-30–2026-06-30 | price_only/base | 0.031220 | 0.031824 | 0.034347 |
| family=profit_expectations; era=SW2021; level=L2; fy_offset=1; population=partial_diagnostic; horizon=20 | MSE | 9 | 8 / 2026-01-30–2026-08-31 | expectation_only/base | 0.007881 | 0.007991 | 0.008090 |
| family=profit_expectations; era=SW2021; level=L2; fy_offset=1; population=partial_diagnostic; horizon=60 | MSE | 9 | 6 / 2026-01-30–2026-06-30 | expectation_only/base | 0.035492 | 0.035914 | 0.037456 |
| family=eps_raw_proxy; era=SW2021; level=L1; fy_offset=0; population=partial_diagnostic; horizon=20 | RankIC | 9 | 17 / 2025-01-27–2026-05-29 | expectation_only/interaction | 0.092405 | 0.051305 | -0.053070 |
| family=eps_raw_proxy; era=SW2021; level=L1; fy_offset=0; population=partial_diagnostic; horizon=60 | RankIC | 9 | 17 / 2025-01-27–2026-05-29 | price_only/interaction | 0.131188 | -0.023189 | -0.058146 |
| family=eps_raw_proxy; era=SW2021; level=L1; fy_offset=1; population=partial_diagnostic; horizon=20 | RankIC | 9 | 16 / 2025-01-27–2026-04-30 | price_only/base | 0.054227 | 0.008547 | -0.101639 |
| family=eps_raw_proxy; era=SW2021; level=L1; fy_offset=1; population=partial_diagnostic; horizon=60 | RankIC | 9 | 16 / 2025-01-27–2026-04-30 | price_only/interaction | 0.119435 | -0.013315 | -0.105633 |
| family=eps_share_context_guard; era=SW2021; level=L1; fy_offset=0; population=partial_diagnostic; horizon=20 | RankIC | 9 | 17 / 2025-01-27–2026-05-29 | expectation_only/interaction | 0.092203 | 0.048849 | -0.054298 |
| family=eps_share_context_guard; era=SW2021; level=L1; fy_offset=0; population=partial_diagnostic; horizon=60 | RankIC | 9 | 17 / 2025-01-27–2026-05-29 | price_only/interaction | 0.132804 | -0.023771 | -0.056778 |
| family=eps_share_context_guard; era=SW2021; level=L1; fy_offset=1; population=partial_diagnostic; horizon=20 | RankIC | 9 | 16 / 2025-01-27–2026-04-30 | price_only/base | 0.048550 | 0.006487 | -0.101081 |
| family=eps_share_context_guard; era=SW2021; level=L1; fy_offset=1; population=partial_diagnostic; horizon=60 | RankIC | 9 | 16 / 2025-01-27–2026-04-30 | price_only/interaction | 0.123762 | -0.013418 | -0.106458 |
| family=profit_expectations; era=SW2021; level=L2; fy_offset=0; population=partial_diagnostic; horizon=20 | RankIC | 9 | 5 / 2026-01-30–2026-05-29 | expectation_only/base | -0.049806 | -0.152095 | -0.272741 |
| family=profit_expectations; era=SW2021; level=L2; fy_offset=0; population=partial_diagnostic; horizon=60 | RankIC | 9 | 5 / 2026-01-30–2026-05-29 | price_plus_expectation/base | 0.010496 | -0.106886 | -0.234518 |
| family=profit_expectations; era=SW2021; level=L2; fy_offset=1; population=partial_diagnostic; horizon=20 | RankIC | 9 | 5 / 2026-01-30–2026-05-29 | expectation_only/interaction | 0.028516 | -0.084502 | -0.419481 |
| family=profit_expectations; era=SW2021; level=L2; fy_offset=1; population=partial_diagnostic; horizon=60 | RankIC | 9 | 5 / 2026-01-30–2026-05-29 | expectation_only/interaction | 0.037532 | -0.067100 | -0.212511 |

## r202

| 分组 | 指标 | 候选数 | 共同日期数／区间 | 最佳候选 | 最佳 | 中位数 | 最差 |
|---|---|---|---|---|---|---|---|
| era=SW2014; level=L2; lag=45; horizon=20 | RankIC | 9 | 26 / 2019-09-30–2021-10-29 | F_macro/interaction | 0.067852 | 0.017778 | -0.043985 |
| era=SW2014; level=L2; lag=45; horizon=60 | RankIC | 9 | 23 / 2019-09-30–2021-07-30 | F_macro/interaction | 0.040584 | -0.010780 | -0.077901 |
| era=SW2014; level=L2; lag=75; horizon=20 | RankIC | 9 | 26 / 2019-09-30–2021-10-29 | F_macro/state | 0.064836 | 0.050085 | 0.017862 |
| era=SW2014; level=L2; lag=75; horizon=60 | RankIC | 9 | 23 / 2019-09-30–2021-07-30 | F_macro/interaction | 0.061430 | 0.017429 | 0.001119 |
| era=SW2014; level=L3; lag=45; horizon=20 | RankIC | 9 | 26 / 2019-09-30–2021-10-29 | F_macro/interaction | 0.070355 | 0.049172 | 0.000167 |
| era=SW2014; level=L3; lag=45; horizon=60 | RankIC | 9 | 23 / 2019-09-30–2021-07-30 | F_macro/interaction | 0.062580 | 0.036576 | -0.025276 |
| era=SW2014; level=L3; lag=75; horizon=20 | RankIC | 9 | 26 / 2019-09-30–2021-10-29 | F_macro/interaction | 0.077760 | 0.056220 | 0.013898 |
| era=SW2014; level=L3; lag=75; horizon=60 | RankIC | 9 | 23 / 2019-09-30–2021-07-30 | F_macro/interaction | 0.080741 | 0.047320 | 0.008025 |
| era=SW2021; level=L1; lag=45; horizon=20 | RankIC | 9 | 30 / 2024-03-29–2026-08-31 | F_exposure/interaction | 0.076220 | 0.030448 | -0.064436 |
| era=SW2021; level=L1; lag=45; horizon=60 | RankIC | 9 | 28 / 2024-03-29–2026-06-30 | F_exposure/interaction | 0.070709 | -0.009856 | -0.077531 |
| era=SW2021; level=L1; lag=75; horizon=20 | RankIC | 9 | 30 / 2024-03-29–2026-08-31 | F_exposure/state | 0.032215 | 0.026357 | -0.036099 |
| era=SW2021; level=L1; lag=75; horizon=60 | RankIC | 9 | 28 / 2024-03-29–2026-06-30 | F_exposure/state | 0.068212 | -0.000137 | -0.009856 |
| era=SW2021; level=L2; lag=45; horizon=20 | RankIC | 9 | 30 / 2024-03-29–2026-08-31 | F_exposure/interaction | 0.059457 | 0.023866 | -0.044467 |
| era=SW2021; level=L2; lag=45; horizon=60 | RankIC | 9 | 28 / 2024-03-29–2026-06-30 | F_exposure/interaction | 0.082436 | 0.013927 | -0.024953 |
| era=SW2021; level=L2; lag=75; horizon=20 | RankIC | 9 | 30 / 2024-03-29–2026-08-31 | F/base | 0.023866 | 0.012608 | -0.025962 |
| era=SW2021; level=L2; lag=75; horizon=60 | RankIC | 9 | 28 / 2024-03-29–2026-06-30 | F_macro/state | 0.043668 | 0.028112 | 0.013927 |
| era=SW2021; level=L3; lag=45; horizon=20 | RankIC | 9 | 30 / 2024-03-29–2026-08-31 | F_exposure/interaction | 0.048511 | 0.007736 | -0.053857 |
| era=SW2021; level=L3; lag=45; horizon=60 | RankIC | 9 | 28 / 2024-03-29–2026-06-30 | F_exposure/interaction | 0.055857 | 0.000310 | -0.024016 |
| era=SW2021; level=L3; lag=75; horizon=20 | RankIC | 9 | 30 / 2024-03-29–2026-08-31 | F_exposure/interaction | 0.013378 | 0.001721 | -0.045798 |
| era=SW2021; level=L3; lag=75; horizon=60 | RankIC | 9 | 28 / 2024-03-29–2026-06-30 | F_macro/base | 0.034629 | 0.011541 | -0.005957 |

## r204

| 分组 | 指标 | 候选数 | 共同日期数／区间 | 最佳候选 | 最佳 | 中位数 | 最差 |
|---|---|---|---|---|---|---|---|
| era=SW2014; level=L2; cohort=F; horizon=20 | RankIC | 8 | 22 / 2020-01-23–2021-10-29 | F/fixed | 0.070368 | -0.010765 | -0.070368 |
| era=SW2014; level=L2; cohort=F; horizon=60 | RankIC | 8 | 19 / 2020-01-23–2021-07-30 | F/fixed | 0.050364 | 0.000000 | -0.050364 |
| era=SW2014; level=L2; cohort=FC; horizon=20 | RankIC | 8 | 10 / 2021-01-29–2021-10-29 | F/fixed | 0.124330 | -0.057815 | -0.124330 |
| era=SW2014; level=L2; cohort=FC; horizon=60 | RankIC | 8 | 7 / 2021-01-29–2021-07-30 | F/fixed | 0.070277 | -0.003359 | -0.070277 |
| era=SW2014; level=L2; cohort=FD; horizon=20 | RankIC | 8 | 22 / 2020-01-23–2021-10-29 | F/fixed | 0.070368 | -0.034238 | -0.070368 |
| era=SW2014; level=L2; cohort=FD; horizon=60 | RankIC | 8 | 19 / 2020-01-23–2021-07-30 | F/fixed | 0.050364 | -0.033636 | -0.073411 |
| era=SW2014; level=L3; cohort=F; horizon=20 | RankIC | 8 | 22 / 2020-01-23–2021-10-29 | F/fixed | 0.061556 | 0.016080 | -0.061556 |
| era=SW2014; level=L3; cohort=F; horizon=60 | RankIC | 8 | 19 / 2020-01-23–2021-07-30 | F/fixed | 0.061851 | -0.008123 | -0.061851 |
| era=SW2014; level=L3; cohort=FC; horizon=20 | RankIC | 8 | 10 / 2021-01-29–2021-10-29 | F/fixed | 0.085356 | 0.022018 | -0.085356 |
| era=SW2014; level=L3; cohort=FC; horizon=60 | RankIC | 8 | 7 / 2021-01-29–2021-07-30 | FC/interaction | 0.029132 | -0.035725 | -0.046996 |
| era=SW2014; level=L3; cohort=FD; horizon=20 | RankIC | 8 | 22 / 2020-01-23–2021-10-29 | F/fixed | 0.062418 | -0.034483 | -0.062418 |
| era=SW2014; level=L3; cohort=FD; horizon=60 | RankIC | 8 | 19 / 2020-01-23–2021-07-30 | F/fixed | 0.062182 | -0.028099 | -0.062182 |
| era=SW2021; level=L2; cohort=F; horizon=20 | RankIC | 8 | 32 / 2024-01-31–2026-08-31 | F/interaction | 0.052559 | 0.009091 | -0.047198 |
| era=SW2021; level=L2; cohort=F; horizon=60 | RankIC | 8 | 18 / 2025-01-27–2026-06-30 | F/interaction | 0.031888 | 0.004880 | -0.021481 |
| era=SW2021; level=L2; cohort=FC; horizon=20 | RankIC | 8 | 32 / 2024-01-31–2026-08-31 | FC/fixed | 0.069684 | 0.013902 | -0.022010 |
| era=SW2021; level=L2; cohort=FC; horizon=60 | RankIC | 8 | 18 / 2025-01-27–2026-06-30 | F/interaction | 0.052888 | 0.043193 | 0.014695 |
| era=SW2021; level=L2; cohort=FD; horizon=20 | RankIC | 8 | 32 / 2024-01-31–2026-08-31 | FD/interaction | 0.058061 | 0.009921 | -0.019515 |
| era=SW2021; level=L2; cohort=FD; horizon=60 | RankIC | 8 | 18 / 2025-01-27–2026-06-30 | FD/base | 0.044271 | 0.004880 | -0.044271 |
| era=SW2021; level=L3; cohort=F; horizon=20 | RankIC | 8 | 32 / 2024-01-31–2026-08-31 | F/interaction | 0.070320 | 0.022140 | -0.041198 |
| era=SW2021; level=L3; cohort=F; horizon=60 | RankIC | 8 | 18 / 2025-01-27–2026-06-30 | momentum/base | 0.030291 | -0.005949 | -0.030291 |
| era=SW2021; level=L3; cohort=FC; horizon=20 | RankIC | 8 | 32 / 2024-01-31–2026-08-31 | FC/base | 0.064820 | 0.036289 | -0.008804 |
| era=SW2021; level=L3; cohort=FC; horizon=60 | RankIC | 8 | 18 / 2025-01-27–2026-06-30 | FC/base | 0.045152 | 0.032795 | -0.006952 |
| era=SW2021; level=L3; cohort=FD; horizon=20 | RankIC | 8 | 32 / 2024-01-31–2026-08-31 | FD/interaction | 0.095998 | 0.013629 | -0.018235 |
| era=SW2021; level=L3; cohort=FD; horizon=60 | RankIC | 8 | 18 / 2025-01-27–2026-06-30 | FD/base | 0.047571 | -0.015535 | -0.047571 |
| era=SW2021; level=L3; cohort=FDG; horizon=20 | RankIC | 8 | 32 / 2024-01-31–2026-08-31 | F/interaction | 0.119629 | 0.007355 | -0.011920 |
| era=SW2021; level=L3; cohort=FDG; horizon=60 | RankIC | 8 | 18 / 2025-01-27–2026-06-30 | FDG/fixed | 0.012225 | -0.001991 | -0.078446 |
| era=SW2021; level=L3; cohort=FG; horizon=20 | RankIC | 8 | 32 / 2024-01-31–2026-08-31 | F/interaction | 0.119629 | 0.000000 | -0.011920 |
| era=SW2021; level=L3; cohort=FG; horizon=60 | RankIC | 8 | 18 / 2025-01-27–2026-06-30 | FG/fixed | 0.083086 | -0.001991 | -0.083086 |
| era=SW2014; level=L2; cohort=F; horizon=20 | MSE | 8 | 0 / None–None | None | — | — | — |
| era=SW2014; level=L2; cohort=F; horizon=60 | MSE | 8 | 0 / None–None | None | — | — | — |
| era=SW2014; level=L2; cohort=FC; horizon=20 | MSE | 8 | 0 / None–None | None | — | — | — |
| era=SW2014; level=L2; cohort=FC; horizon=60 | MSE | 8 | 0 / None–None | None | — | — | — |
| era=SW2014; level=L2; cohort=FD; horizon=20 | MSE | 8 | 0 / None–None | None | — | — | — |
| era=SW2014; level=L2; cohort=FD; horizon=60 | MSE | 8 | 0 / None–None | None | — | — | — |
| era=SW2014; level=L3; cohort=F; horizon=20 | MSE | 8 | 0 / None–None | None | — | — | — |
| era=SW2014; level=L3; cohort=F; horizon=60 | MSE | 8 | 0 / None–None | None | — | — | — |
| era=SW2014; level=L3; cohort=FC; horizon=20 | MSE | 8 | 0 / None–None | None | — | — | — |
| era=SW2014; level=L3; cohort=FC; horizon=60 | MSE | 8 | 0 / None–None | None | — | — | — |
| era=SW2014; level=L3; cohort=FD; horizon=20 | MSE | 8 | 0 / None–None | None | — | — | — |
| era=SW2014; level=L3; cohort=FD; horizon=60 | MSE | 8 | 0 / None–None | None | — | — | — |
| era=SW2021; level=L2; cohort=F; horizon=20 | MSE | 8 | 0 / None–None | None | — | — | — |
| era=SW2021; level=L2; cohort=F; horizon=60 | MSE | 8 | 0 / None–None | None | — | — | — |
| era=SW2021; level=L2; cohort=FC; horizon=20 | MSE | 8 | 0 / None–None | None | — | — | — |
| era=SW2021; level=L2; cohort=FC; horizon=60 | MSE | 8 | 0 / None–None | None | — | — | — |
| era=SW2021; level=L2; cohort=FD; horizon=20 | MSE | 8 | 0 / None–None | None | — | — | — |
| era=SW2021; level=L2; cohort=FD; horizon=60 | MSE | 8 | 0 / None–None | None | — | — | — |
| era=SW2021; level=L3; cohort=F; horizon=20 | MSE | 8 | 0 / None–None | None | — | — | — |
| era=SW2021; level=L3; cohort=F; horizon=60 | MSE | 8 | 0 / None–None | None | — | — | — |
| era=SW2021; level=L3; cohort=FC; horizon=20 | MSE | 8 | 0 / None–None | None | — | — | — |
| era=SW2021; level=L3; cohort=FC; horizon=60 | MSE | 8 | 0 / None–None | None | — | — | — |
| era=SW2021; level=L3; cohort=FD; horizon=20 | MSE | 8 | 0 / None–None | None | — | — | — |
| era=SW2021; level=L3; cohort=FD; horizon=60 | MSE | 8 | 0 / None–None | None | — | — | — |
| era=SW2021; level=L3; cohort=FDG; horizon=20 | MSE | 8 | 0 / None–None | None | — | — | — |
| era=SW2021; level=L3; cohort=FDG; horizon=60 | MSE | 8 | 0 / None–None | None | — | — | — |
| era=SW2021; level=L3; cohort=FG; horizon=20 | MSE | 8 | 0 / None–None | None | — | — | — |
| era=SW2021; level=L3; cohort=FG; horizon=60 | MSE | 8 | 0 / None–None | None | — | — | — |

## r205

| 分组 | 指标 | 候选数 | 共同日期数／区间 | 最佳候选 | 最佳 | 中位数 | 最差 |
|---|---|---|---|---|---|---|---|
| family=fixed_fy; era=SW2021; level=L2; target_type=matched_post; horizon=20 | MSE | 6 | 370 / 2024-01-02–2026-04-30 | controls/base | 0.003234 | 0.003259 | 0.003492 |
| family=fixed_fy; era=SW2021; level=L2; target_type=matched_post; horizon=60 | MSE | 6 | 201 / 2025-01-03–2026-04-30 | controls/interaction | 0.014864 | 0.014947 | 0.015071 |
| family=fixed_fy; era=SW2021; level=L2; target_type=post; horizon=20 | MSE | 6 | 371 / 2024-01-02–2026-04-30 | controls/base | 0.003767 | 0.003855 | 0.004072 |
| family=fixed_fy; era=SW2021; level=L2; target_type=post; horizon=60 | MSE | 6 | 201 / 2025-01-03–2026-04-30 | controls/interaction | 0.015680 | 0.015795 | 0.015870 |
| family=fixed_fy; era=SW2021; level=L3; target_type=matched_post; horizon=20 | MSE | 6 | 350 / 2024-01-02–2026-04-30 | controls/base | 0.003817 | 0.003978 | 0.004757 |
| family=fixed_fy; era=SW2021; level=L3; target_type=matched_post; horizon=60 | MSE | 6 | 178 / 2025-01-03–2026-04-30 | controls/interaction | 0.019122 | 0.019227 | 0.019284 |
| family=fixed_fy; era=SW2021; level=L3; target_type=post; horizon=20 | MSE | 6 | 362 / 2024-01-02–2026-04-30 | controls/base | 0.004350 | 0.004517 | 0.004938 |
| family=fixed_fy; era=SW2021; level=L3; target_type=post; horizon=60 | MSE | 6 | 193 / 2025-01-03–2026-04-30 | controls/interaction | 0.019377 | 0.019633 | 0.019676 |
| family=paired_fy; era=SW2021; level=L2; target_type=post; horizon=20 | MSE | 6 | 325 / 2024-01-02–2026-01-05 | controls/base | 0.003563 | 0.003681 | 0.003967 |
| family=paired_fy; era=SW2021; level=L2; target_type=post; horizon=60 | MSE | 6 | 155 / 2025-01-03–2026-01-05 | controls/base | 0.011447 | 0.011552 | 0.012520 |
| family=paired_fy; era=SW2021; level=L3; target_type=post; horizon=20 | MSE | 6 | 319 / 2024-01-02–2026-01-05 | with_revision/base | 0.004168 | 0.004367 | 0.004884 |
| family=paired_fy; era=SW2021; level=L3; target_type=post; horizon=60 | MSE | 6 | 150 / 2025-01-03–2026-01-05 | controls/interaction | 0.016070 | 0.016285 | 0.016802 |
| family=unknown_controls; era=SW2021; level=L2; target_type=matched_post; horizon=20 | MSE | 6 | 370 / 2024-01-02–2026-04-30 | controls/base | 0.003234 | 0.003259 | 0.003492 |
| family=unknown_controls; era=SW2021; level=L2; target_type=matched_post; horizon=60 | MSE | 6 | 201 / 2025-01-03–2026-04-30 | controls/interaction | 0.014865 | 0.014948 | 0.015072 |
| family=unknown_controls; era=SW2021; level=L2; target_type=post; horizon=20 | MSE | 6 | 371 / 2024-01-02–2026-04-30 | controls/base | 0.003767 | 0.003855 | 0.004072 |
| family=unknown_controls; era=SW2021; level=L2; target_type=post; horizon=60 | MSE | 6 | 201 / 2025-01-03–2026-04-30 | controls/interaction | 0.015680 | 0.015795 | 0.015870 |
| family=unknown_controls; era=SW2021; level=L3; target_type=matched_post; horizon=20 | MSE | 6 | 350 / 2024-01-02–2026-04-30 | controls/base | 0.003817 | 0.003978 | 0.004757 |
| family=unknown_controls; era=SW2021; level=L3; target_type=matched_post; horizon=60 | MSE | 6 | 178 / 2025-01-03–2026-04-30 | controls/interaction | 0.019127 | 0.019231 | 0.019289 |
| family=unknown_controls; era=SW2021; level=L3; target_type=post; horizon=20 | MSE | 6 | 362 / 2024-01-02–2026-04-30 | controls/base | 0.004350 | 0.004517 | 0.004938 |
| family=unknown_controls; era=SW2021; level=L3; target_type=post; horizon=60 | MSE | 6 | 193 / 2025-01-03–2026-04-30 | controls/interaction | 0.019377 | 0.019633 | 0.019676 |

## r198

| 分组 | 指标 | 候选数 | 共同日期数／区间 | 最佳候选 | 最佳 | 中位数 | 最差 |
|---|---|---|---|---|---|---|---|
| era=SW2021; level=L2; industry_code=801737.SI; horizon=20 | MSE | 12 | 20 / 2025-01-27 00:00:00–2026-08-31 00:00:00 | FSM/state | 0.007719 | 0.007976 | 0.008360 |
| era=SW2021; level=L2; industry_code=801737.SI; horizon=60 | MSE | 12 | 18 / 2025-01-27 00:00:00–2026-06-30 00:00:00 | FSMB/base | 0.015099 | 0.017012 | 0.021567 |
| era=SW2021; level=L3; industry_code=857371.SI; horizon=20 | MSE | 12 | 20 / 2025-01-27 00:00:00–2026-08-31 00:00:00 | FSM/base | 0.006931 | 0.007811 | 0.008689 |
| era=SW2021; level=L3; industry_code=857371.SI; horizon=60 | MSE | 12 | 18 / 2025-01-27 00:00:00–2026-06-30 00:00:00 | FSM/base | 0.020571 | 0.025839 | 0.031156 |

## r276

| 分组 | 指标 | 候选数 | 共同日期数／区间 | 最佳候选 | 最佳 | 中位数 | 最差 |
|---|---|---|---|---|---|---|---|
| era=SW2021; level=L2; industry_code=801737.SI; horizon=20 | MSE | 12 | 8 / 2026-01-30 00:00:00–2026-08-31 00:00:00 | FS/base | 0.004362 | 0.005314 | 0.006448 |
| era=SW2021; level=L2; industry_code=801737.SI; horizon=60 | MSE | 12 | 6 / 2026-01-30 00:00:00–2026-06-30 00:00:00 | FSX/base | 0.008228 | 0.009889 | 0.012432 |
| era=SW2021; level=L3; industry_code=857371.SI; horizon=20 | MSE | 12 | 8 / 2026-01-30 00:00:00–2026-08-31 00:00:00 | FS/base | 0.004192 | 0.006017 | 0.007459 |
| era=SW2021; level=L3; industry_code=857371.SI; horizon=60 | MSE | 12 | 6 / 2026-01-30 00:00:00–2026-06-30 00:00:00 | FSX/base | 0.015556 | 0.018603 | 0.022408 |

## r281

| 分组 | 指标 | 候选数 | 共同日期数／区间 | 最佳候选 | 最佳 | 中位数 | 最差 |
|---|---|---|---|---|---|---|---|
| era=SW2021; level=L2; industry_code=801737.SI; horizon=20 | MSE | 30 | 8 / 2026-01-30 00:00:00–2026-08-31 00:00:00 | FS/base | 0.004362 | 0.007125 | 0.010220 |
| era=SW2021; level=L2; industry_code=801737.SI; horizon=60 | MSE | 30 | 6 / 2026-01-30 00:00:00–2026-06-30 00:00:00 | DR/base | 0.007647 | 0.009923 | 0.017242 |
| era=SW2021; level=L3; industry_code=857371.SI; horizon=20 | MSE | 30 | 8 / 2026-01-30 00:00:00–2026-08-31 00:00:00 | FS/base | 0.004192 | 0.006593 | 0.007459 |
| era=SW2021; level=L3; industry_code=857371.SI; horizon=60 | MSE | 30 | 6 / 2026-01-30 00:00:00–2026-06-30 00:00:00 | DR/base | 0.014176 | 0.018162 | 0.022408 |

## 每个候选的指标

[2,702条候选指标明细](/home/xiaolv/code/a_share/topics/02_AFML_BIG_WINNER/experiments/pending/35_industry_rise_mechanisms_and_rotation/reports/results_asof_r307_20261114/candidate_metrics.json)。模型名、共同日期口径和各候选值也在 [comparable_model_statistics.json](/home/xiaolv/code/a_share/topics/02_AFML_BIG_WINNER/experiments/pending/35_industry_rise_mechanisms_and_rotation/reports/results_asof_r307_20261114/comparable_model_statistics.json) 中保留。

## 日频概率校准（独立口径）

| 轮次／任务 | 时代／层级／年 | 校准频率 | 日期数 | 成熟样本最少数 | 未知样本最多数 | 最佳 | 最佳Brier | 中位Brier | 最差Brier |
|---|---|---|---|---|---|---|---|---|---|
| R256 onset | SW2014 L2 2020 | daily | 243 | 13042 | 13 | interaction | 0.133150 | 0.133638 | 0.133641 |
| R256 onset | SW2014 L2 2020 | monthly | 243 | 13042 | 13 | interaction | 0.136192 | 0.136216 | 0.138387 |
| R256 onset | SW2014 L2 2021 | daily | 199 | 9583 | 848 | base | 0.199415 | 0.199476 | 0.199699 |
| R256 onset | SW2014 L2 2021 | monthly | 199 | 9583 | 848 | base | 0.210369 | 0.213807 | 0.215946 |
| R256 onset | SW2014 L3 2020 | daily | 243 | 24446 | 41 | interaction | 0.137503 | 0.137744 | 0.138162 |
| R256 onset | SW2014 L3 2020 | monthly | 243 | 24446 | 41 | interaction | 0.138993 | 0.139606 | 0.140934 |
| R256 onset | SW2014 L3 2021 | daily | 199 | 17975 | 1584 | base | 0.205756 | 0.206152 | 0.206276 |
| R256 onset | SW2014 L3 2021 | monthly | 199 | 17975 | 1584 | state | 0.214158 | 0.214582 | 0.221214 |
| R256 onset | SW2021 L2 2025 | daily | 243 | 15078 | 0 | base | 0.174120 | 0.195457 | 0.196969 |
| R256 onset | SW2021 L2 2025 | monthly | 243 | 15078 | 0 | base | 0.172268 | 0.186437 | 0.187049 |
| R256 onset | SW2021 L2 2026 | daily | 170 | 11661 | 627 | interaction | 0.132133 | 0.132935 | 0.133885 |
| R256 onset | SW2021 L2 2026 | monthly | 170 | 11661 | 627 | state | 0.131354 | 0.134345 | 0.134638 |
| R256 onset | SW2021 L3 2025 | daily | 243 | 32285 | 0 | base | 0.181725 | 0.198441 | 0.210629 |
| R256 onset | SW2021 L3 2025 | monthly | 243 | 32285 | 0 | base | 0.181725 | 0.185122 | 0.195830 |
| R256 onset | SW2021 L3 2026 | daily | 170 | 23978 | 1591 | interaction | 0.145598 | 0.145912 | 0.146857 |
| R256 onset | SW2021 L3 2026 | monthly | 170 | 23978 | 1591 | state | 0.143638 | 0.147507 | 0.148206 |
| R295 reversal | SW2014 L2 2021 | daily | 199 | 9418 | 1296 | state | 0.095032 | 0.095043 | 0.099056 |
| R295 reversal | SW2014 L2 2021 | monthly | 199 | 9418 | 1296 | state | 0.097748 | 0.100469 | 0.100487 |
| R295 reversal | SW2014 L3 2020 | daily | 243 | 17601 | 23 | base | 0.147929 | 0.152086 | 0.154654 |
| R295 reversal | SW2014 L3 2020 | monthly | 243 | 17601 | 23 | base | 0.150840 | 0.155117 | 0.159747 |
| R295 reversal | SW2014 L3 2021 | daily | 199 | 18609 | 2464 | state | 0.112990 | 0.114860 | 0.116107 |
| R295 reversal | SW2014 L3 2021 | monthly | 199 | 18609 | 2464 | state | 0.114845 | 0.115027 | 0.115778 |
| R295 reversal | SW2021 L2 2025 | daily | 243 | 15713 | 0 | base | 0.092393 | 0.093629 | 0.093733 |
| R295 reversal | SW2021 L2 2025 | monthly | 243 | 15713 | 0 | base | 0.094639 | 0.097690 | 0.098786 |
| R295 reversal | SW2021 L2 2026 | daily | 170 | 6341 | 1690 | state | 0.223961 | 0.223973 | 0.226768 |
| R295 reversal | SW2021 L2 2026 | monthly | 170 | 6341 | 1690 | state | 0.224577 | 0.225432 | 0.225909 |
| R295 reversal | SW2021 L3 2025 | daily | 243 | 32976 | 20 | base | 0.098244 | 0.100105 | 0.101411 |
| R295 reversal | SW2021 L3 2025 | monthly | 243 | 32976 | 20 | base | 0.100108 | 0.101282 | 0.105211 |
| R295 reversal | SW2021 L3 2026 | daily | 170 | 14526 | 3312 | state | 0.229306 | 0.231789 | 0.233723 |
| R295 reversal | SW2021 L3 2026 | monthly | 170 | 14526 | 3312 | state | 0.228747 | 0.231049 | 0.234206 |