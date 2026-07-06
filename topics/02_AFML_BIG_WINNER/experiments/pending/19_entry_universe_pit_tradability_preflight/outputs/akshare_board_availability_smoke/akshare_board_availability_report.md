# AkShare Board Availability Smoke Test

- generated_at_utc: `2026-07-06T07:12:12Z`
- akshare_version: `1.18.10`
- summary_csv: `/home/xiaolv/code/a_share/topics/02_AFML_BIG_WINNER/experiments/pending/19_entry_universe_pit_tradability_preflight/outputs/akshare_board_availability_smoke/akshare_board_availability_summary.csv`
- removed_proxy_env_keys: `none`
- remaining_proxy_env_keys_after_cleanup: `none`

## Readout

- Eastmoney industry: name=ok, current_membership=ok, current_quote=ok, historical_board_index_ohlcv=ok.
- Eastmoney concept: name=ok, current_membership=timeout, current_quote=ok, historical_board_index_ohlcv=ok.
- THS industry: name=ok, current_membership_api=api_missing, current_info=ok, current_overview=ok, historical_board_index_ohlcv=ok, historical_membership_api=api_missing.
- THS concept: name=ok, current_membership_api=api_missing, current_info=ok, concept_event_table=ok, historical_board_index_ohlcv=ok, historical_membership_api=api_missing.
- Historical PIT stock membership: not proven by these AkShare board endpoints. Current constituents/snapshots require daily archiving before they can become PIT features.

## Endpoint Summary

| check_id | provider | board_type | role | api | sample_symbol | status | rows | first_date | last_date | error_type |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| em_industry_name | eastmoney | industry | current_board_list | stock_board_industry_name_em |  | ok | 496 |  |  |  |
| em_industry_cons_current | eastmoney | industry | current_membership | stock_board_industry_cons_em | 小金属 | ok | 25 |  |  |  |
| em_industry_hist_ohlcv | eastmoney | industry | historical_board_index_ohlcv | stock_board_industry_hist_em | 小金属 | ok | 118 | 2024-01-02 | 2024-07-01 |  |
| em_industry_spot_current | eastmoney | industry | current_board_quote | stock_board_industry_spot_em | 小金属 | ok | 10 |  |  |  |
| em_concept_name | eastmoney | concept | current_board_list | stock_board_concept_name_em |  | ok | 495 |  |  |  |
| em_concept_cons_current | eastmoney | concept | current_membership | stock_board_concept_cons_em | 融资融券 | timeout |  |  |  | CallTimeoutError |
| em_concept_hist_ohlcv | eastmoney | concept | historical_board_index_ohlcv | stock_board_concept_hist_em | 绿色电力 | ok | 118 | 2024-01-02 | 2024-07-01 |  |
| em_concept_spot_current | eastmoney | concept | current_board_quote | stock_board_concept_spot_em | 可燃冰 | ok | 10 |  |  |  |
| ths_industry_name | ths | industry | current_board_list | stock_board_industry_name_ths |  | ok | 90 |  |  |  |
| ths_industry_cons_missing | ths | industry | current_membership | stock_board_industry_cons_ths | 半导体 | api_missing |  |  |  | AttributeError |
| ths_industry_hist_membership_missing | ths | industry | historical_membership | stock_board_industry_hist_ths | 半导体 | api_missing |  |  |  | AttributeError |
| ths_industry_info_current | ths | industry | current_board_info | stock_board_industry_info_ths | 半导体 | ok | 10 |  |  |  |
| ths_industry_index_ohlcv | ths | industry | historical_board_index_ohlcv | stock_board_industry_index_ths | 半导体 | ok | 118 | 2024-01-02 | 2024-07-01 |  |
| ths_industry_summary_current | ths | industry | current_board_overview | stock_board_industry_summary_ths |  | ok | 90 |  |  |  |
| ths_concept_name | ths | concept | current_board_list | stock_board_concept_name_ths |  | ok | 374 |  |  |  |
| ths_concept_cons_missing | ths | concept | current_membership | stock_board_concept_cons_ths | 阿里巴巴概念 | api_missing |  |  |  | AttributeError |
| ths_concept_hist_membership_missing | ths | concept | historical_membership | stock_board_concept_hist_ths | 阿里巴巴概念 | api_missing |  |  |  | AttributeError |
| ths_concept_info_current | ths | concept | current_board_info | stock_board_concept_info_ths | 阿里巴巴概念 | ok | 10 |  |  |  |
| ths_concept_index_ohlcv | ths | concept | historical_board_index_ohlcv | stock_board_concept_index_ths | 阿里巴巴概念 | ok | 118 | 2024-01-02 | 2024-07-01 |  |
| ths_concept_summary_current | ths | concept | concept_event_table | stock_board_concept_summary_ths |  | ok | 50 | 2023-11-14 | 2026-07-01 |  |

## Interpretation Rule

- `historical_board_index_ohlcv` means the board/concept index price history is available.
- It does not prove historical stock membership in that industry or concept.
- `current_membership` or current board snapshots can only become PIT usable after daily snapshotting with snapshot dates.
