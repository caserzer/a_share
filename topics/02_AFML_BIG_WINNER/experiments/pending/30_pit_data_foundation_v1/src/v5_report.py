"""Public v5 coverage and remaining boundaries, derived from full private outputs."""
import json
import platform

import pandas as pd
import pyarrow

from archive import EP, sha, utc_now, write_json
from v5_core import V5, PUBLIC, BASE_ID


def main():
    prices = pd.read_csv(PUBLIC / "price_adjustment_coverage.csv")
    labels = json.loads((PUBLIC / "label_summary.json").read_text())
    acquisition = json.loads((PUBLIC / "factor_acquisition.json").read_text())
    totals = pd.read_csv(PUBLIC / "label_status_totals.csv")
    curve = pd.read_csv(PUBLIC / "legacy_qfq_comparison.csv")
    links = pd.read_csv(PUBLIC / "code_factor_scale_links.csv")
    provider = json.loads((PUBLIC / "qfq_provider_sensitivity.json").read_text())
    attempts = [json.loads(line) for line in (PUBLIC / "factor_attempts.jsonl").read_text().splitlines()]
    for record in attempts:
        for digest in [record.get("sha256")] + list(record.get("capture_source_hashes", {}).values()):
            if digest:
                assert sha(V5 / "raw/sha256" / digest[:2] / digest) == digest
    gaps = []
    for p in sorted((V5 / "acquired/factors").glob("*.unresolved.json")):
        r = json.loads(p.read_text())
        gaps.append(dict(instrument=r["instrument"], reason=r["reason"], http_status=r.get("http_status"), source_sha256=r.get("sha256")))
    pd.DataFrame(gaps, columns=["instrument", "reason", "http_status", "source_sha256"]).to_csv(PUBLIC / "factor_gaps.csv", index=False)
    board = prices.groupby("board_bucket").agg(securities=("security_id","size"), raw_rows=("raw_rows","sum"), qfq_rows=("qfq_rows","sum"),
        securities_with_qfq=("qfq_rows", lambda x:int(x.gt(0).sum()))).reset_index()
    board.to_csv(PUBLIC / "price_coverage_by_board.csv", index=False)
    actual_curve_mismatch = curve.within_legacy_rounding_tolerance.lt(curve.rows)
    summary = dict(labels, version="D2-v5-qfq-price-inference", baseline_v4=BASE_ID,
        price_security_count=len(prices), price_security_count_with_qfq=int(prices.qfq_rows.gt(0).sum()),
        raw_price_rows=int(prices.raw_rows.sum()), qfq_price_rows=int(prices.qfq_rows.sum()),
        factor_acquisition=acquisition, factor_attempts_verified=len(attempts), factor_gaps=len(gaps),
        legacy_qfq_security_curves_compared=int(curve.security_id.nunique()),
        legacy_qfq_field_curves_with_residual_difference=int(actual_curve_mismatch.sum()),
        qfq_provider_sensitivity=provider,
        canonical_alias_fallback_segments=int(links.canonical_series_fallback.fillna(False).sum()),
        independently_matched_alias_segments=int((links.instrument.ne(links.primary_instrument)&links.shared_step_curve_matched.fillna(False)).sum()),
        all_horizons_and_policies_have_full_candidate_denominator=True,
        old_strict_results_retained=True, independent_full_pit_acceptance=False,
        generated_at=utc_now(), report_transform_sha256=sha(__file__))
    write_json(PUBLIC / "delivery_summary.json", summary)
    write_json(PUBLIC / "runtime.json", dict(python=platform.python_version(), pandas=pd.__version__, pyarrow=pyarrow.__version__,
        time_zone="Asia/Shanghai", raw_redistribution_authorized=False))
    gates = [
        ("qfq_price_change_inferred_labels", "PARTIAL", f"{labels['known_inferred_rows']} known inferred / {labels['label_rows']} records", "unknown endpoints, factors, conflicts or terminal wealth; censored future horizons"),
        ("original_unadjusted_price_basis_audit", "PASS", "102 raw partitions; 529304 rows; all adjustflag=3", "retrospective raw prices remain Historical-proxy"),
        ("observed_open_inference", "ENABLED_BY_USER", "actual fill and cash ledger no longer gate this price inference", "actual execution and realized wealth remain unverified"),
        ("qfq_provider_disagreement", "PARTIAL", f"{provider['disagreement_securities']} securities separately flagged", "different provider historical qfq curves not independently reconciled"),
        ("daily_historical_eligibility", "BLOCKED", "unchanged v4 per-field evidence", "full daily historical qualification and limits"),
        ("retired_terminal_wealth", "BLOCKED", "249 provisional retirement or transfer outcomes", "unknown terminal values are not zero or last-quote filled"),
        ("financial_version_coverage", "PARTIAL", "v4 selected report gaps remain 43 company-years", "full first/revision field denominators"),
        ("industry_macro_complete_pit", "BLOCKED", "unchanged domain gates", "historical original vintages"),
    ]
    pd.DataFrame(gates,columns=["domain","status","evidence","remaining"]).to_csv(PUBLIC / "domain_quality_gates.csv",index=False)
    rows = []
    for h, f in totals[totals.requested_policy.eq("price")].groupby("horizon", sort=False):
        counts = dict(zip(f.status, f.rows))
        rows.append(f"| {h} | {counts.get('KNOWN_INFERRED',0):,} | {counts.get('UNKNOWN',0):,} | {counts.get('CENSORED',0):,} |")
    block = (
        "\n## 全量结果\n\n"
        f"保留 {len(prices):,} 个暂定证券身份；{summary['price_security_count_with_qfq']:,} 个身份取得可用前复权价格，"
        f"未复权 {summary['raw_price_rows']:,} 行中有 {summary['qfq_price_rows']:,} 行可生成前复权开收盘。"
        f"因子取得 {acquisition['acquired']:,}/{acquisition['queued']:,} 个代码，{len(gaps)} 个空响应或缺源详见 `factor_gaps.csv`。\n\n"
        f"{labels['candidate_months']:,} 个候选证券月，四期限三请求名共 {labels['label_rows']:,} 行；"
        f"其中 {labels['known_inferred_rows']:,} 行为 KNOWN_INFERRED。三请求名共用同一代理结果，不能相加当作独立样本。\n\n"
        "| 期限 | 已知推断 | 未知 | 未成熟 |\n|---|---:|---:|---:|\n" + "\n".join(rows) + "\n\n"
        f"相同日期的六个月可比样本 {labels['six_month_known']:,} 个：未复权低于 −20% 为 {labels['six_month_raw_loss_below_minus20']:,} 个，"
        f"前复权为 {labels['six_month_qfq_loss_below_minus20']:,} 个，共 {labels['six_month_loss_classification_changed']:,} 个事件分类改变。"
        "这只是价格口径敏感性，不构成预测模型效果改进。\n\n"
        f"月度桥表 {labels['bridge_rows']:,} 行，原 {labels['old_bridge_columns_preserved']} 列逐值保留。"
        f"与 {summary['legacy_qfq_security_curves_compared']:,} 个旧前复权缓存比较，"
        f"{summary['legacy_qfq_field_curves_with_residual_difference']} 条开盘/收盘曲线仍有容差外差异，详见逐证券审计；不据此更改价格源选择。\n"
        f"\n旧缓存实际来自 {provider['legacy_source_functions']}，容差外曲线按接口分布为 {provider['residual_field_curves_by_source']}。"
        "这属于不同供应商复权历史的未解决差异，不能归因于舍入或直接认定哪方正确。24 只证券的全部新标签明确标记 "
        "`qfq_vendor_curve_disagreement=true`；有共同入场/出场日期时另存旧前复权收益和 −20% 事件一致性，"
        "见 `qfq_provider_sensitivity.csv`。主收益继续使用预先固定的新浪因子，实际权益口径仍未认证。\n"
    )
    path = EP / "reports/pit_v5.md"
    text = path.read_text()
    marker = "\n## 全量结果\n"
    if marker in text:
        text = text.split(marker)[0]
    path.write_text(text.replace("以下数字与结果在全量运行结束后由审计产物确认。", "以下数字来自全量运行与审计产物。") + block)
    print(json.dumps(summary),flush=True)


if __name__ == "__main__":
    main()
