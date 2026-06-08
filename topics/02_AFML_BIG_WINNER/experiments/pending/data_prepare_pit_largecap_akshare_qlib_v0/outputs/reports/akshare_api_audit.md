# AkShare API Audit

Blocking issues: 0

| category | support_state | function_name | historical | latest_only | fallback_state | notes |
|---|---|---|---:|---:|---|---|
| historical_raw_daily_bars | supported | stock_zh_a_daily | True | False | primary_or_fallback_sampled | Sampled 2024-05-06 through 2024-05-10, adjust=raw. |
| historical_qfq_daily_bars | supported | stock_zh_a_daily | True | False | primary_or_fallback_sampled | Sampled 2024-05-06 through 2024-05-10, adjust=qfq. |
| historical_total_market_cap_or_total_share_asof | supported | stock_zh_a_gbjg_em\|stock_share_change_cninfo | True | False | primary_gbjg_or_cninfo_share_change_fallback | Historical share-change rows can be as-of expanded by trade date. Fallback stock_share_change_cninfo sampled with 变动日期 and 总股本 in 10k-share units. |
| instrument_metadata_board_classification | supported | stock_info_sh_name_code\|stock_info_sz_name_code\|stock_info_sh_delist\|stock_info_sz_delist | True | False | current_lists_plus_delist_lists | Board classification is code-prefix based after excluding non-target prefixes. |
| historical_listed_delisted_status | supported | stock_info_sh_name_code\|stock_info_sz_name_code\|stock_info_sh_delist\|stock_info_sz_delist | True | False | current_lists_plus_delist_lists | Listing status can be constructed from listing/delist dates when metadata audit passes. |
| historical_st_status | supported | stock_info_sz_change_name\|stock_info_change_name\|stock_zh_a_st_em | True | False | supported_with_sh_lifetime_st_exclusion | Unproxied historical ST probe found 2612 dated Shenzhen ST-name-change rows, but Shanghai stock_info_change_name returns names without dates. Policy: remove every Shanghai asset from the whole universe when any returned name contains an ST marker; when AkShare returns no Shanghai name-history table for a symbol, treat it as no recorded Shanghai name-change rows for that symbol. Probe 600003 confirmed a Shanghai ST marker. Current ST list sample failed: ConnectionError: ('Connection aborted.', RemoteDisconnected('Remote end closed connection without response')) |
| suspension_or_tradability_status | supported | stock_tfp_em | True | False | sample_date_respected | Sample for 2024-05-06 matched requested date. |
| trading_calendar | supported | tool_trade_date_hist_sina | True | False | calendar_covers_requested_range | Resolved 2281 sessions from 2017-01-03 to 2026-05-29. |
