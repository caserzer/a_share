# R02 Family Signal 120D Path Analysis

This report is descriptive evidence for R03 design. It is not an entry rule, strategy validation, or trading instruction.

## Raw Trigger Vs Episode

- `review_momentum_oscillator_pullback_volume`: raw=5229, episodes=4613, compression=0.8822
- `review_momentum_oscillator_range_volume`: raw=5929, episodes=5257, compression=0.8867
- `review_momentum_pullback_volatility_volume`: raw=5228, episodes=4617, compression=0.8831
- `review_oscillator_pullback_volatility_volume`: raw=5510, episodes=4801, compression=0.8713
- `single_momentum_rps`: raw=44120, episodes=16582, compression=0.3758
- `single_oscillator`: raw=23132, episodes=15698, compression=0.6786
- `single_price_trend`: raw=34592, episodes=17518, compression=0.5064
- `single_pullback_drawdown`: raw=56446, episodes=19235, compression=0.3408
- `single_range_breakout`: raw=68679, episodes=36142, compression=0.5262
- `single_volatility_band`: raw=28211, episodes=18699, compression=0.6628
- `single_volume_money`: raw=22806, episodes=19178, compression=0.8409

## R03 Handoff

- `review_momentum_oscillator_pullback_volume`: needs_entry_delay_or_stop_design; blocker=none; opportunity=upside_exists_but_path_needs_risk_design; basis=first_plus10_hit_rate=0.691439;mfe_high_t20_p50=0.0801403;transient_spike_rate=0.0803998
- `review_momentum_oscillator_range_volume`: needs_entry_delay_or_stop_design; blocker=none; opportunity=upside_exists_but_path_needs_risk_design; basis=first_plus10_hit_rate=0.696149;mfe_high_t20_p50=0.0804875;transient_spike_rate=0.0792985
- `review_momentum_pullback_volatility_volume`: needs_entry_delay_or_stop_design; blocker=none; opportunity=upside_exists_but_path_needs_risk_design; basis=first_plus10_hit_rate=0.687799;mfe_high_t20_p50=0.0802907;transient_spike_rate=0.08033
- `review_oscillator_pullback_volatility_volume`: needs_entry_delay_or_stop_design; blocker=none; opportunity=upside_exists_but_path_needs_risk_design; basis=first_plus10_hit_rate=0.673346;mfe_high_t20_p50=0.0768157;transient_spike_rate=0.0797328
- `single_momentum_rps`: needs_entry_delay_or_stop_design; blocker=none; opportunity=upside_exists_but_path_needs_risk_design; basis=first_plus10_hit_rate=0.702092;mfe_high_t20_p50=0.0808601;transient_spike_rate=0.0819732
- `single_oscillator`: needs_entry_delay_or_stop_design; blocker=none; opportunity=upside_exists_but_path_needs_risk_design; basis=first_plus10_hit_rate=0.674178;mfe_high_t20_p50=0.0672645;transient_spike_rate=0.0674753
- `single_price_trend`: needs_entry_delay_or_stop_design; blocker=none; opportunity=upside_exists_but_path_needs_risk_design; basis=first_plus10_hit_rate=0.701911;mfe_high_t20_p50=0.0819237;transient_spike_rate=0.0831903
- `single_pullback_drawdown`: needs_entry_delay_or_stop_design; blocker=none; opportunity=upside_exists_but_path_needs_risk_design; basis=first_plus10_hit_rate=0.697854;mfe_high_t20_p50=0.0782256;transient_spike_rate=0.0803292
- `single_range_breakout`: needs_entry_delay_or_stop_design; blocker=none; opportunity=upside_exists_but_path_needs_risk_design; basis=first_plus10_hit_rate=0.666768;mfe_high_t20_p50=0.0648961;transient_spike_rate=0.0607262
- `single_volatility_band`: needs_entry_delay_or_stop_design; blocker=none; opportunity=upside_exists_but_path_needs_risk_design; basis=first_plus10_hit_rate=0.67281;mfe_high_t20_p50=0.0695225;transient_spike_rate=0.0675596
- `single_volume_money`: needs_entry_delay_or_stop_design; blocker=none; opportunity=upside_exists_but_path_needs_risk_design; basis=first_plus10_hit_rate=0.65833;mfe_high_t20_p50=0.0642968;transient_spike_rate=0.0629144

## Episode Path Quality

- `review_momentum_oscillator_pullback_volume`: early_failure=0.5128, clean_continuation=0.1204, transient_spike=0.0804, severe_drawdown=0.8162, atr=low_coverage_audit_only
- `review_momentum_oscillator_range_volume`: early_failure=0.5044, clean_continuation=0.1228, transient_spike=0.0793, severe_drawdown=0.8122, atr=low_coverage_audit_only
- `review_momentum_pullback_volatility_volume`: early_failure=0.5161, clean_continuation=0.1190, transient_spike=0.0803, severe_drawdown=0.8094, atr=low_coverage_audit_only
- `review_oscillator_pullback_volatility_volume`: early_failure=0.4970, clean_continuation=0.1234, transient_spike=0.0797, severe_drawdown=0.7746, atr=low_coverage_audit_only
- `single_momentum_rps`: early_failure=0.5125, clean_continuation=0.1189, transient_spike=0.0820, severe_drawdown=0.8134, atr=low_coverage_audit_only
- `single_oscillator`: early_failure=0.4338, clean_continuation=0.1281, transient_spike=0.0675, severe_drawdown=0.6810, atr=low_coverage_audit_only
- `single_price_trend`: early_failure=0.5247, clean_continuation=0.1197, transient_spike=0.0832, severe_drawdown=0.8188, atr=low_coverage_audit_only
- `single_pullback_drawdown`: early_failure=0.5032, clean_continuation=0.1226, transient_spike=0.0803, severe_drawdown=0.7922, atr=low_coverage_audit_only
- `single_range_breakout`: early_failure=0.4183, clean_continuation=0.1283, transient_spike=0.0607, severe_drawdown=0.6649, atr=low_coverage_audit_only
- `single_volatility_band`: early_failure=0.4544, clean_continuation=0.1244, transient_spike=0.0676, severe_drawdown=0.6909, atr=low_coverage_audit_only
- `single_volume_money`: early_failure=0.4109, clean_continuation=0.1292, transient_spike=0.0629, severe_drawdown=0.6760, atr=low_coverage_audit_only
