# EP35 research archive — 2026-11-15

This commit archives EP35 research through R307 and the subsequent results report, monthly L3 holdings and selected industry score attribution. The research goal remains paused. It does not deploy models or change production trading behavior.

Start with [the complete results report](reports/results_asof_r307_20261114/REPORT.md), [all experiment rounds](reports/results_asof_r307_20261114/EXPERIMENT_INDEX.md), and [the monthly holdings viewer](reports/results_asof_r307_20261114/l3_monthly_holdings/holdings.html). Historical README/STATUS/log statements are preserved as dated research history; statements that work would continue do not override the current pause.

## Archive boundary

Code, protocols, reports and compact result summaries are included. Provider source data, downloaded document bodies, bulk prediction/price panels, runtime caches and duplicated evaluation workspaces remain local. PUBLICATION_MANIFEST.json records included and omitted artifact hashes and reasons. It excludes itself from its included-file hash list.

This is an evidence archive, not a self-contained dataset release. A fresh clone cannot replay data-dependent scripts without the original local inputs. Historical reports retain original absolute local paths and receipts; some references intentionally point to local-only files. Those files are not silently replaced or represented as published. Original scripts can require the existing project environment and local cache.

Results remain Historical-proxy, not strict PIT or independently confirmed prospective performance. The 18.85% L3 portfolio uses price features and a rank target on the breadth-eligible cohort; it differs from the 22.26% L2 price-plus-valuation return-target portfolio. Selected L3 industries are equal weighted; the top-five preview is not the full portfolio. No model adoption is implied.

## Verification

The EP35 test suite passed: 122 tests. The R307 report verifier independently checks 386 comparison groups, 2,702 candidate means, 1,164 portfolio groups and the 307-round catalogue against local source artifacts. Monthly holdings have 32 periods, 53 industries per period and weights summing to one; selected identities match the top 53 predictions. Credential-pattern and publication-boundary checks apply to the staged archive, not to unrelated EP34 changes.
