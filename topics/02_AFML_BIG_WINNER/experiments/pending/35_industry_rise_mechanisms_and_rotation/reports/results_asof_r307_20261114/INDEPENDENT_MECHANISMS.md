# 独立机制实验20日详细结果

每组候选池和日期范围不同，不横向排总冠军。60日、旧时代及其他目标请见完整模型表。后续时钟及风险核验见总报告与307轮索引。

| 来源／母体 | 指标 | 候选数／共同日期 | 最佳候选 | 最佳 | 中位数 | 最差 |
|---|---|---|---|---|---|---|
| r199 / family=financing; era=SW2021; level=L3; cohort=financing; task=onset; horizon=20; objective=onset | Brier | 6 / 16 | FS/state | 0.163920 | 0.164217 | 0.165262 |
| r199 / family=market_style; era=SW2021; level=L2; cohort=market_style; task=onset; horizon=20; objective=onset | Brier | 12 / 20 | FSM/interaction | 0.142210 | 0.142999 | 0.145019 |
| r199 / family=market_style; era=SW2021; level=L3; cohort=market_style; task=onset; horizon=20; objective=onset | Brier | 12 / 20 | FSM/base | 0.152635 | 0.154213 | 0.157558 |
| r199 / family=size_diffusion; era=SW2021; level=L2; cohort=size_diffusion; task=onset; horizon=20; objective=onset | Brier | 12 / 20 | F/base | 0.141137 | 0.144260 | 0.148692 |
| r199 / family=size_diffusion; era=SW2021; level=L3; cohort=size_diffusion; task=onset; horizon=20; objective=onset | Brier | 12 / 20 | F/base | 0.152074 | 0.154203 | 0.158716 |
| r199 / family=financing; era=SW2021; level=L2; cohort=financing; task=return; horizon=20; objective=return | RankIC | 6 / 28 | FSE/base | 0.008312 | 0.003499 | -0.010898 |
| r199 / family=financing; era=SW2021; level=L3; cohort=financing; task=return; horizon=20; objective=return | RankIC | 6 / 28 | FS/interaction | 0.017360 | -0.010711 | -0.012493 |
| r199 / family=market_style; era=SW2021; level=L1; cohort=market_style; task=return; horizon=20; objective=return | RankIC | 12 / 20 | FSM/base | 0.079637 | 0.050595 | -0.037601 |
| r199 / family=market_style; era=SW2021; level=L2; cohort=market_style; task=return; horizon=20; objective=return | RankIC | 12 / 20 | FSM/state | 0.094396 | 0.050587 | 0.021047 |
| r199 / family=market_style; era=SW2021; level=L3; cohort=market_style; task=return; horizon=20; objective=return | RankIC | 12 / 20 | FSMD/base | 0.101610 | 0.079188 | 0.044517 |
| r199 / family=size_diffusion; era=SW2021; level=L1; cohort=size_diffusion; task=return; horizon=20; objective=return | RankIC | 12 / 32 | FS/base | 0.044960 | 0.036007 | 0.018838 |
| r199 / family=size_diffusion; era=SW2021; level=L2; cohort=size_diffusion; task=return; horizon=20; objective=return | RankIC | 12 / 32 | FDS/state | 0.052362 | 0.043964 | 0.002273 |
| r199 / family=size_diffusion; era=SW2021; level=L3; cohort=size_diffusion; task=return; horizon=20; objective=return | RankIC | 12 / 32 | FDS/state | 0.078864 | 0.065755 | 0.043690 |
| r199 / family=financing; era=SW2021; level=L3; cohort=financing; task=reversal; horizon=20; objective=reversal | Brier | 6 / 16 | FSE/interaction | 0.157143 | 0.161127 | 0.162449 |
| r199 / family=market_style; era=SW2021; level=L2; cohort=market_style; task=reversal; horizon=20; objective=reversal | Brier | 12 / 20 | FSM/state | 0.152132 | 0.158123 | 0.166255 |
| r199 / family=market_style; era=SW2021; level=L3; cohort=market_style; task=reversal; horizon=20; objective=reversal | Brier | 12 / 20 | FSMD/state | 0.156432 | 0.161389 | 0.167304 |
| r199 / family=size_diffusion; era=SW2021; level=L2; cohort=size_diffusion; task=reversal; horizon=20; objective=reversal | Brier | 12 / 20 | FDS/state | 0.158659 | 0.161104 | 0.162189 |
| r199 / family=size_diffusion; era=SW2021; level=L3; cohort=size_diffusion; task=reversal; horizon=20; objective=reversal | Brier | 12 / 20 | FD/state | 0.162439 | 0.163117 | 0.168370 |
| r199 / family=financing; era=SW2021; level=L2; cohort=financing; task=return; horizon=20; objective=return | MSE | 6 / 28 | FSE/base | 0.004473 | 0.004516 | 0.004881 |
| r199 / family=financing; era=SW2021; level=L3; cohort=financing; task=return; horizon=20; objective=return | MSE | 6 / 28 | FS/base | 0.005444 | 0.005470 | 0.005886 |
| r199 / family=market_style; era=SW2021; level=L1; cohort=market_style; task=return; horizon=20; objective=return | MSE | 12 / 20 | FS/base | 0.003817 | 0.003962 | 0.004151 |
| r199 / family=market_style; era=SW2021; level=L2; cohort=market_style; task=return; horizon=20; objective=return | MSE | 12 / 20 | FSMD/base | 0.005377 | 0.005518 | 0.005683 |
| r199 / family=market_style; era=SW2021; level=L3; cohort=market_style; task=return; horizon=20; objective=return | MSE | 12 / 20 | FSMD/base | 0.006170 | 0.006280 | 0.006409 |
| r199 / family=size_diffusion; era=SW2021; level=L1; cohort=size_diffusion; task=return; horizon=20; objective=return | MSE | 12 / 32 | F/base | 0.003509 | 0.003794 | 0.003965 |
| r199 / family=size_diffusion; era=SW2021; level=L2; cohort=size_diffusion; task=return; horizon=20; objective=return | MSE | 12 / 32 | FD/base | 0.004870 | 0.005173 | 0.005402 |
| r199 / family=size_diffusion; era=SW2021; level=L3; cohort=size_diffusion; task=return; horizon=20; objective=return | MSE | 12 / 32 | FD/base | 0.005642 | 0.006054 | 0.006317 |
| r200 / family=leader_main80; era=SW2021; level=L2; cohort=leader_main80; task=onset; horizon=20; objective=onset | Brier | 6 / 20 | with_leader/state | 0.141743 | 0.142891 | 0.143539 |
| r200 / family=leader_main80; era=SW2021; level=L3; cohort=leader_main80; task=onset; horizon=20; objective=onset | Brier | 6 / 20 | with_leader/state | 0.150966 | 0.151184 | 0.154304 |
| r200 / family=leader_strict100; era=SW2021; level=L2; cohort=leader_strict100; task=onset; horizon=20; objective=onset | Brier | 6 / 20 | controls/base | 0.138045 | 0.138349 | 0.139838 |
| r200 / family=leader_strict100; era=SW2021; level=L3; cohort=leader_strict100; task=onset; horizon=20; objective=onset | Brier | 6 / 20 | with_leader/state | 0.148616 | 0.149400 | 0.151724 |
| r200 / family=leader_main80; era=SW2021; level=L1; cohort=leader_main80; task=return; horizon=20; objective=return | RankIC | 6 / 8 | controls/base | 0.063235 | 0.050728 | -0.150139 |
| r200 / family=leader_main80; era=SW2021; level=L2; cohort=leader_main80; task=return; horizon=20; objective=return | RankIC | 6 / 20 | controls/base | 0.080899 | 0.080462 | 0.002375 |
| r200 / family=leader_main80; era=SW2021; level=L3; cohort=leader_main80; task=return; horizon=20; objective=return | RankIC | 6 / 20 | controls/state | 0.096396 | 0.095974 | 0.036325 |
| r200 / family=leader_strict100; era=SW2021; level=L1; cohort=leader_strict100; task=return; horizon=20; objective=return | RankIC | 6 / 3 | controls/base | 0.145869 | 0.139380 | -0.008098 |
| r200 / family=leader_strict100; era=SW2021; level=L2; cohort=leader_strict100; task=return; horizon=20; objective=return | RankIC | 6 / 20 | controls/base | 0.069329 | 0.067937 | -0.005008 |
| r200 / family=leader_strict100; era=SW2021; level=L3; cohort=leader_strict100; task=return; horizon=20; objective=return | RankIC | 6 / 20 | controls/base | 0.098439 | 0.097500 | 0.035564 |
| r200 / family=leader_main80; era=SW2021; level=L2; cohort=leader_main80; task=reversal; horizon=20; objective=reversal | Brier | 6 / 20 | controls/state | 0.158240 | 0.158757 | 0.163678 |
| r200 / family=leader_main80; era=SW2021; level=L3; cohort=leader_main80; task=reversal; horizon=20; objective=reversal | Brier | 6 / 20 | controls/state | 0.157752 | 0.158534 | 0.167414 |
| r200 / family=leader_strict100; era=SW2021; level=L2; cohort=leader_strict100; task=reversal; horizon=20; objective=reversal | Brier | 6 / 20 | controls/state | 0.158787 | 0.159923 | 0.166101 |
| r200 / family=leader_strict100; era=SW2021; level=L3; cohort=leader_strict100; task=reversal; horizon=20; objective=reversal | Brier | 6 / 20 | controls/state | 0.159960 | 0.160740 | 0.168747 |
| r200 / family=leader_main80; era=SW2021; level=L1; cohort=leader_main80; task=return; horizon=20; objective=return | MSE | 6 / 20 | controls/base | 0.004151 | 0.004337 | 0.004609 |
| r200 / family=leader_main80; era=SW2021; level=L2; cohort=leader_main80; task=return; horizon=20; objective=return | MSE | 6 / 20 | controls/base | 0.005545 | 0.005686 | 0.005909 |
| r200 / family=leader_main80; era=SW2021; level=L3; cohort=leader_main80; task=return; horizon=20; objective=return | MSE | 6 / 20 | controls/base | 0.006278 | 0.006385 | 0.006538 |
| r200 / family=leader_strict100; era=SW2021; level=L1; cohort=leader_strict100; task=return; horizon=20; objective=return | MSE | 6 / 20 | controls/base | 0.004456 | 0.004639 | 0.004906 |
| r200 / family=leader_strict100; era=SW2021; level=L2; cohort=leader_strict100; task=return; horizon=20; objective=return | MSE | 6 / 20 | controls/base | 0.005488 | 0.005627 | 0.005834 |
| r200 / family=leader_strict100; era=SW2021; level=L3; cohort=leader_strict100; task=return; horizon=20; objective=return | MSE | 6 / 20 | controls/base | 0.006256 | 0.006361 | 0.006509 |
| r201 / family=common_main80; era=SW2021; level=L3; cohort=common_main80; task=return; horizon=20; objective=return | RankIC | 9 / 0 | None | — | — | — |
| r201 / family=notice_main80; era=SW2021; level=L3; cohort=notice_main80; task=return; horizon=20; objective=return | RankIC | 6 / 0 | None | — | — | — |
| r201 / family=update_main80; era=SW2021; level=L3; cohort=update_main80; task=return; horizon=20; objective=return | RankIC | 6 / 0 | None | — | — | — |
| r201 / family=common_main80; era=SW2021; level=L3; cohort=common_main80; task=return; horizon=20; objective=return | MSE | 9 / 15 | update_model/base | 0.008380 | 0.008591 | 0.008948 |
| r201 / family=notice_main80; era=SW2021; level=L3; cohort=notice_main80; task=return; horizon=20; objective=return | MSE | 6 / 20 | with_financial/base | 0.008125 | 0.008240 | 0.008706 |
| r201 / family=update_main80; era=SW2021; level=L3; cohort=update_main80; task=return; horizon=20; objective=return | MSE | 6 / 15 | with_financial/base | 0.008380 | 0.008581 | 0.008895 |
| r197 / family=eps_raw_proxy; era=SW2021; level=L1; fy_offset=0; population=partial_diagnostic; horizon=20 | MSE | 9 / 19 | price_only/base | 0.003329 | 0.003434 | 0.003631 |
| r197 / family=eps_raw_proxy; era=SW2021; level=L1; fy_offset=1; population=partial_diagnostic; horizon=20 | MSE | 9 / 18 | expectation_only/base | 0.002503 | 0.002554 | 0.002704 |
| r197 / family=eps_share_context_guard; era=SW2021; level=L1; fy_offset=0; population=partial_diagnostic; horizon=20 | MSE | 9 / 19 | price_only/base | 0.003329 | 0.003435 | 0.003635 |
| r197 / family=eps_share_context_guard; era=SW2021; level=L1; fy_offset=1; population=partial_diagnostic; horizon=20 | MSE | 9 / 18 | expectation_only/base | 0.002502 | 0.002555 | 0.002708 |
| r197 / family=profit_expectations; era=SW2021; level=L2; fy_offset=0; population=partial_diagnostic; horizon=20 | MSE | 9 / 8 | expectation_only/state | 0.008137 | 0.008272 | 0.008530 |
| r197 / family=profit_expectations; era=SW2021; level=L2; fy_offset=1; population=partial_diagnostic; horizon=20 | MSE | 9 / 8 | expectation_only/base | 0.007881 | 0.007991 | 0.008090 |
| r197 / family=eps_raw_proxy; era=SW2021; level=L1; fy_offset=0; population=partial_diagnostic; horizon=20 | RankIC | 9 / 17 | expectation_only/interaction | 0.092405 | 0.051305 | -0.053070 |
| r197 / family=eps_raw_proxy; era=SW2021; level=L1; fy_offset=1; population=partial_diagnostic; horizon=20 | RankIC | 9 / 16 | price_only/base | 0.054227 | 0.008547 | -0.101639 |
| r197 / family=eps_share_context_guard; era=SW2021; level=L1; fy_offset=0; population=partial_diagnostic; horizon=20 | RankIC | 9 / 17 | expectation_only/interaction | 0.092203 | 0.048849 | -0.054298 |
| r197 / family=eps_share_context_guard; era=SW2021; level=L1; fy_offset=1; population=partial_diagnostic; horizon=20 | RankIC | 9 / 16 | price_only/base | 0.048550 | 0.006487 | -0.101081 |
| r197 / family=profit_expectations; era=SW2021; level=L2; fy_offset=0; population=partial_diagnostic; horizon=20 | RankIC | 9 / 5 | expectation_only/base | -0.049806 | -0.152095 | -0.272741 |
| r197 / family=profit_expectations; era=SW2021; level=L2; fy_offset=1; population=partial_diagnostic; horizon=20 | RankIC | 9 / 5 | expectation_only/interaction | 0.028516 | -0.084502 | -0.419481 |
| r202 / era=SW2021; level=L1; lag=45; horizon=20 | RankIC | 9 / 30 | F_exposure/interaction | 0.076220 | 0.030448 | -0.064436 |
| r202 / era=SW2021; level=L1; lag=75; horizon=20 | RankIC | 9 / 30 | F_exposure/state | 0.032215 | 0.026357 | -0.036099 |
| r202 / era=SW2021; level=L2; lag=45; horizon=20 | RankIC | 9 / 30 | F_exposure/interaction | 0.059457 | 0.023866 | -0.044467 |
| r202 / era=SW2021; level=L2; lag=75; horizon=20 | RankIC | 9 / 30 | F/base | 0.023866 | 0.012608 | -0.025962 |
| r202 / era=SW2021; level=L3; lag=45; horizon=20 | RankIC | 9 / 30 | F_exposure/interaction | 0.048511 | 0.007736 | -0.053857 |
| r202 / era=SW2021; level=L3; lag=75; horizon=20 | RankIC | 9 / 30 | F_exposure/interaction | 0.013378 | 0.001721 | -0.045798 |
| r204 / era=SW2021; level=L2; cohort=F; horizon=20 | RankIC | 8 / 32 | F/interaction | 0.052559 | 0.009091 | -0.047198 |
| r204 / era=SW2021; level=L2; cohort=FC; horizon=20 | RankIC | 8 / 32 | FC/fixed | 0.069684 | 0.013902 | -0.022010 |
| r204 / era=SW2021; level=L2; cohort=FD; horizon=20 | RankIC | 8 / 32 | FD/interaction | 0.058061 | 0.009921 | -0.019515 |
| r204 / era=SW2021; level=L3; cohort=F; horizon=20 | RankIC | 8 / 32 | F/interaction | 0.070320 | 0.022140 | -0.041198 |
| r204 / era=SW2021; level=L3; cohort=FC; horizon=20 | RankIC | 8 / 32 | FC/base | 0.064820 | 0.036289 | -0.008804 |
| r204 / era=SW2021; level=L3; cohort=FD; horizon=20 | RankIC | 8 / 32 | FD/interaction | 0.095998 | 0.013629 | -0.018235 |
| r204 / era=SW2021; level=L3; cohort=FDG; horizon=20 | RankIC | 8 / 32 | F/interaction | 0.119629 | 0.007355 | -0.011920 |
| r204 / era=SW2021; level=L3; cohort=FG; horizon=20 | RankIC | 8 / 32 | F/interaction | 0.119629 | 0.000000 | -0.011920 |
| r204 / era=SW2021; level=L2; cohort=F; horizon=20 | MSE | 8 / 0 | None | — | — | — |
| r204 / era=SW2021; level=L2; cohort=FC; horizon=20 | MSE | 8 / 0 | None | — | — | — |
| r204 / era=SW2021; level=L2; cohort=FD; horizon=20 | MSE | 8 / 0 | None | — | — | — |
| r204 / era=SW2021; level=L3; cohort=F; horizon=20 | MSE | 8 / 0 | None | — | — | — |
| r204 / era=SW2021; level=L3; cohort=FC; horizon=20 | MSE | 8 / 0 | None | — | — | — |
| r204 / era=SW2021; level=L3; cohort=FD; horizon=20 | MSE | 8 / 0 | None | — | — | — |
| r204 / era=SW2021; level=L3; cohort=FDG; horizon=20 | MSE | 8 / 0 | None | — | — | — |
| r204 / era=SW2021; level=L3; cohort=FG; horizon=20 | MSE | 8 / 0 | None | — | — | — |
| r205 / family=fixed_fy; era=SW2021; level=L2; target_type=matched_post; horizon=20 | MSE | 6 / 370 | controls/base | 0.003234 | 0.003259 | 0.003492 |
| r205 / family=fixed_fy; era=SW2021; level=L2; target_type=post; horizon=20 | MSE | 6 / 371 | controls/base | 0.003767 | 0.003855 | 0.004072 |
| r205 / family=fixed_fy; era=SW2021; level=L3; target_type=matched_post; horizon=20 | MSE | 6 / 350 | controls/base | 0.003817 | 0.003978 | 0.004757 |
| r205 / family=fixed_fy; era=SW2021; level=L3; target_type=post; horizon=20 | MSE | 6 / 362 | controls/base | 0.004350 | 0.004517 | 0.004938 |
| r205 / family=paired_fy; era=SW2021; level=L2; target_type=post; horizon=20 | MSE | 6 / 325 | controls/base | 0.003563 | 0.003681 | 0.003967 |
| r205 / family=paired_fy; era=SW2021; level=L3; target_type=post; horizon=20 | MSE | 6 / 319 | with_revision/base | 0.004168 | 0.004367 | 0.004884 |
| r205 / family=unknown_controls; era=SW2021; level=L2; target_type=matched_post; horizon=20 | MSE | 6 / 370 | controls/base | 0.003234 | 0.003259 | 0.003492 |
| r205 / family=unknown_controls; era=SW2021; level=L2; target_type=post; horizon=20 | MSE | 6 / 371 | controls/base | 0.003767 | 0.003855 | 0.004072 |
| r205 / family=unknown_controls; era=SW2021; level=L3; target_type=matched_post; horizon=20 | MSE | 6 / 350 | controls/base | 0.003817 | 0.003978 | 0.004757 |
| r205 / family=unknown_controls; era=SW2021; level=L3; target_type=post; horizon=20 | MSE | 6 / 362 | controls/base | 0.004350 | 0.004517 | 0.004938 |
| r198 / era=SW2021; level=L2; industry_code=801737.SI; horizon=20 | MSE | 12 / 20 | FSM/state | 0.007719 | 0.007976 | 0.008360 |
| r198 / era=SW2021; level=L3; industry_code=857371.SI; horizon=20 | MSE | 12 / 20 | FSM/base | 0.006931 | 0.007811 | 0.008689 |
| r276 / era=SW2021; level=L2; industry_code=801737.SI; horizon=20 | MSE | 12 / 8 | FS/base | 0.004362 | 0.005314 | 0.006448 |
| r276 / era=SW2021; level=L3; industry_code=857371.SI; horizon=20 | MSE | 12 / 8 | FS/base | 0.004192 | 0.006017 | 0.007459 |
| r281 / era=SW2021; level=L2; industry_code=801737.SI; horizon=20 | MSE | 30 / 8 | FS/base | 0.004362 | 0.007125 | 0.010220 |
| r281 / era=SW2021; level=L3; industry_code=857371.SI; horizon=20 | MSE | 30 / 8 | FS/base | 0.004192 | 0.006593 | 0.007459 |