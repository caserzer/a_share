"""Coverage deltas, exact unresolved periods, and unchanged core evidence gates."""

import json

import pandas as pd

from archive import write_json
from v4_core import EP, PUBLIC, V4, baseline
from v4_pipeline import classify_report


def build():
    bridge = json.loads((PUBLIC / "full_bridge_summary.json").read_text())
    identity = json.loads((PUBLIC / "identity_summary.json").read_text())
    chain = json.loads((PUBLIC / "chain_summary.json").read_text())
    reviewed = json.loads((PUBLIC / "reviewed_fact_summary.json").read_text())
    gaps = pd.read_csv(baseline("provenance/v2_selected_financial_recovery_bridge.csv"))
    documents = []
    for p in (V4 / "documents/financial").glob("*.json"):
        r = json.loads(p.read_text())
        a = r["announcement"]
        kind = classify_report(a["title"])
        if (
            r["status"] == "ORIGINAL_PDF_RECOVERED"
            and kind
            and kind["form"] == "full_report"
        ):
            documents.append(
                dict(
                    **a,
                    source_sha256=r["source"]["sha256"],
                    source_reused_from_v3=r.get("source_reused_from_v3", False),
                )
            )
    doc = pd.DataFrame(documents)
    matches = {
        key: g.art_code.tolist()
        for key, g in doc.groupby(["security_id", "report_period"])
    }
    gaps["v4_original_pdf_ids"] = [
        json.dumps(matches.get((r.security_id, str(r.report_year) + "-12-31"), []))
        for r in gaps.itertuples()
    ]
    gaps["v4_original_pdf_recovered"] = gaps.v4_original_pdf_ids.ne("[]")
    gaps["any_archived_version_recovered"] = (
        gaps.v2_original_pdf_recovered
        | gaps.v3_original_pdf_recovered
        | gaps.v4_original_pdf_recovered
    )
    gaps["resolution"] = gaps.any_archived_version_recovered.map(
        lambda x: (
            "INDEX_ASSOCIATED_ORIGINAL_PDF_ARCHIVED_NOT_ALL_FIELDS_CERTIFIED"
            if x
            else "UNRESOLVED_IN_CHECKED_SOURCES_NO_GLOBAL_ABSENCE_CLAIM"
        )
    )
    gaps.to_csv(PUBLIC / "selected_financial_recovery_bridge.csv", index=False)
    gaps[~gaps.any_archived_version_recovered].to_csv(
        PUBLIC / "selected_financial_remaining_gaps.csv", index=False
    )
    labels = pd.read_csv(PUBLIC / "strict_label_counts.csv")
    known = int(labels.loc[labels.status.eq("KNOWN"), "rows"].sum())
    if known:
        raise ValueError("unattested execution was promoted")
    gates = pd.DataFrame(
        [
            dict(
                domain="continuous_code_change_identity",
                status="PARTIAL",
                evidence="3 original-proven changes; 155 duplicate security-months removed",
                remaining="7 other shared-issuer groups require distinct episode and rights review",
            ),
            dict(
                domain="historical_daily_eligibility_and_open_execution",
                status="BLOCKED",
                evidence="2 additional reviewed removals; no positive opening-fill evidence",
                remaining="complete daily qualification, limits and executable opening order evidence",
            ),
            dict(
                domain="post_delisting_issuer_continuity",
                status="PARTIAL",
                evidence="85 identities linked to retired disclosure codes, including 18 new pixel reviews",
                remaining="actual account delivery, complete action ledger and terminal wealth",
            ),
            dict(
                domain="retired_terminal_wealth",
                status="BLOCKED",
                evidence="249 provisional true retirement/transfer cases after removing 3 false delistings",
                remaining="249 terminal wealth outcomes remain unknown; issuer link is not settlement",
            ),
            dict(
                domain="strict_price_total_executable_labels",
                status="BLOCKED",
                evidence=f"{bridge['strict_label_rows']} rebuilt records; 0 known",
                remaining="opening execution plus policy-specific complete rights/paid cash/costs",
            ),
            dict(
                domain="financial_original_versions",
                status="PARTIAL",
                evidence=f"{len(doc)} additional selected report PDFs; 15 newly page-reviewed reported values",
                remaining="field-by-field first/revision completeness and remaining selected report periods",
            ),
            dict(
                domain="financial_valuation_industry_macro_complete_pit",
                status="BLOCKED",
                evidence="reviewed report-version namespace only",
                remaining="canonical first/revision denominators, industry and macro vintages",
            ),
            dict(
                domain="independent_human_acceptance",
                status="BLOCKED",
                evidence="agent source-page review recorded separately",
                remaining="independent human review required by original READY gate",
            ),
        ]
    )
    gates.to_csv(PUBLIC / "domain_quality_gates.csv", index=False)
    summary = dict(
        canonical_inventory_rows=identity["canonical_inventory_rows"],
        continuous_code_changes=3,
        false_retirements_removed=3,
        retired_denominator=249,
        retired_terminal_wealth_known=0,
        linked_retired_issuers=85,
        newly_pixel_reviewed_retired_identities=18,
        new_original_removal_facts=2,
        additional_financial_disclosures=chain["new_financial_disclosures"],
        merged_financial_disclosures=chain["merged_financial_disclosures"],
        selected_annual_original_pdfs=len(doc),
        prior_selected_periods=len(gaps),
        prior_missing_both_v2_v3=int(
            (~(gaps.v2_original_pdf_recovered | gaps.v3_original_pdf_recovered)).sum()
        ),
        newly_recovered_prior_missing_periods=int(
            (
                ~(gaps.v2_original_pdf_recovered | gaps.v3_original_pdf_recovered)
                & gaps.v4_original_pdf_recovered
            ).sum()
        ),
        remaining_prior_selected_missing_periods=int(
            (~gaps.any_archived_version_recovered).sum()
        ),
        reviewed_financial_facts=reviewed["financial_facts"],
        strict_label_records=bridge["strict_label_rows"],
        strict_known=known,
        duplicate_security_months_removed=bridge["duplicate_security_months_removed"],
        canonical_candidate_month_rows=bridge["candidate_month_rows"],
        legacy_rows_preserved=bridge["legacy_rows_preserved"],
        source_mismatch_or_pagination_failures_never_admitted=True,
        independent_human_review=False,
    )
    write_json(PUBLIC / "delivery_summary.json", summary)
    report = f"""# EP30 D2-v4：身份连续性纠错及退市后披露桥接

本轮发现并修复会影响全市场分母的身份问题，同时补充退市权益关联及财报原件。未调整原质量门槛，未训练模型。

- 原件确认 `000022→001872`、`000043→001914`、`300114→302132` 为连续上市主体的代码变更，原持有人股份数量不因代码变更而变化。供应商旧代码退市日不是证券终止上市；暂定证券表 5,922→5,919，2017年以来暂定退市/转板案例 252→249。
- 对全部 10 组重复披露主体标识做普查，仅合并有原件证明的 3 组。其他 7 组涉及转板、重新上市或历史换股，保留为待核验独立区间，未按 org_id 自动拼接。
- 全量重建 {bridge['candidate_month_rows']:,} 个证券月，删除 {bridge['duplicate_security_months_removed']} 个重复证券月。保留全部 {bridge['legacy_rows_preserved']:,} 条旧桥接记录及原列，另标记旧别名行；历史代码按生效区间选择，不将新代码倒填旧日期。
- 重建 {bridge['strict_label_rows']:,} 条严格标签（四期限×三政策）。已知值仍为 **0**，成熟缺证据为 UNKNOWN，未成熟为 CENSORED；价格、含息及可执行收益不混用，不填零。跨三个代码变更的行情按旧码截至变更前、新码自生效日起拼接，保留真实缺价。
- 新增 18 家扫描确权原件的目视核验；退市后披露代码桥接 67→85 家。这证明证券主体与披露代码关联，不证明个体账户股份到账、首次成交或退市终值。249 个暂定退市/转板案例的终值仍未知。
- 新增华仪 2024-01-16、柏龙 2024-01-25 两条原件摘牌事实。知悉时间使用公告日期后的下一已核验交易日，不倒填当日开盘，也不推广为连续每日资格。
- 财报索引新增 {chain['new_financial_disclosures']:,} 条（退市代码 1,181，巨潮原件关联 2），累计 {chain['merged_financial_disclosures']:,} 条、{chain['logical_report_chains']:,} 条逻辑报告链；本批关联原始完整年报 PDF {len(doc)} 份。原先两版共同缺失的 66 个选定公司年度，新补 {summary['newly_recovered_prior_missing_periods']} 个，余 {summary['remaining_prior_selected_missing_periods']} 个。逐项见 `selected_financial_remaining_gaps.csv`。缺失仅指所核查来源未闭合，不声称报告全球不存在；并购财务可能嵌在其他文件中，未冒充独立年报。
- 新增 15 条原页核验数值，限定为已审核报告版本的 `financial:reviewed_reported_*` 命名空间。长生 2018 年补发报告仅自 **2020-11-24 09:30** 可用，2019 年末及 2020-11-23 收盘均不可见。刚泰 2020 年初版与更正版另存并保留 supersedes；不声称财务字段全部修订已闭合。

巨潮分页请求 100 条时实际最多返回 30 条且会发生跨页重复，原失败尝试均保留并拒绝作为完整索引；改用 30 条页长后重新验证全部条数、发行人和日期。中航成飞新代码只有在原件身份桥接后才允许接入，未放宽为同 org_id 即自动接入。受限的 np-cnotice 和 NEEQ 主站未恢复请求。

仍阻断下游严格研究的核心证据：完整逐日资格/开盘可执行状态、持有期完整公司行动、现金实际支付及最终权益结算、财务完整版本分母、行业/宏观旧版本，以及独立人工验收。原始 PDF、响应和大缓存仅保存在私有封存目录；Git 工作区只放代码、摘要、核验及哈希。

重放入口：`v4_prepare.py`、`v4_identity.py`、`v4_pipeline.py queues|parse`、`v4_review.py`、`v4_bridge.py`、`v4_audit.py`。采集入口 `v4_cninfo.py` 不用于离线重放。封存读取器 `D2V4Dataset` 支持纠错身份、严格标签、报告版本以及历史/归档时点区分；可显式提供不可变 v3 baseline 以读取未变更的数据域。
"""
    (EP / "reports/pit_v4.md").write_text(report)


if __name__ == "__main__":
    build()
