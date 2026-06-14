# 09A Regime PIT Audit

本审计只确认 09A 使用的事件级 regime 在 t0 可见语义下可复核，不用于重启 transition modeling。

| split | t0_visible | future_join_count | reconstructed_consistency | alias_agreement |
| --- | ---: | ---: | ---: | ---: |
| all | true | 0 | 1.000000 | 1.000000 |
| train | true | 0 | 1.000000 | 1.000000 |
| validation | true | 0 | 1.000000 | 1.000000 |
| robustness | true | 0 | 1.000000 | 1.000000 |

## Source Contract

- event_regime_source_artifact: `candidate_family_canonical_events.csv.gz`
- event_regime_reconstruction_source: `cross_section_feature_panel.parquet`
- episode_regime_source_artifact: `candidate_family_capture.parquet` / membership readout
- transition usage: diagnostic only
