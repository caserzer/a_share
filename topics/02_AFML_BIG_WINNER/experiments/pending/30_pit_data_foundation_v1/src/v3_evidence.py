"""Source-page based eligibility and rights extraction; ambiguity never means false/zero."""

import json
import re
import sys
from decimal import Decimal
import pandas as pd
from archive import sha, write_json
from v3_core import V3, V2_RELEASE, inventory, code_version
from pit import Calendar

DATE = r"(20\d{2})[年./-](\d{1,2})[月./-](\d{1,2})日?"
PARSER_VERSION = code_version(__file__)


def compact(text):
    return re.sub(r"\s+", "", text).replace("：", ":")


def normalized_date(groups):
    try:
        return str(pd.Timestamp(int(groups[0]), int(groups[1]), int(groups[2])).date())
    except (ValueError, TypeError):
        return None


def original_pages(path, digest, limit=None):
    if sha(path) != digest:
        raise ValueError("original document hash changed")
    suffix = f".first_{limit}" if limit else ""
    target = V3 / f"text/{digest}{suffix}.json"
    if target.exists():
        r = json.loads(target.read_text())
        if r["source_sha256"] != digest:
            raise ValueError("changed text provenance")
        return r["pages"][:limit] if limit else r["pages"]
    sys.path.insert(0, str(V3 / "vendor"))
    import pymupdf

    with pymupdf.open(path) as pdf:
        pages = [
            page.get_text("text", sort=False)
            for page in (pdf[:limit] if limit else pdf)
        ]
    write_json(
        target,
        dict(
            source_sha256=digest,
            engine="pymupdf_1.26.5_get_text_text_sort_false",
            transform_sha256=PARSER_VERSION,
            pages=pages,
        ),
    )
    return pages[:limit] if limit else pages


def security_map():
    inv = inventory()
    mapping = {}
    for r in inv.itertuples():
        mapping.setdefault(r.instrument[2:], set()).add(r.security_id)
    aliases = pd.read_parquet(V2_RELEASE / "normalized/code_intervals.parquet")
    for r in aliases.itertuples():
        mapping.setdefault(r.historical_instrument[2:], set()).add(r.security_id)
    return mapping


def printed_security(pages, mapping):
    candidates = set()
    for text in pages[:2]:
        for code in re.findall(
            r"(?:(?:证券|股票|公司)代码|NEEQ)[:：为]?(\d{6})", compact(text)
        ):
            candidates.update(mapping.get(code, set()))
    return next(iter(candidates)) if len(candidates) == 1 else None


def unique_events(matches):
    result = []
    for field in sorted({m["field"] for m in matches}):
        rows = [m for m in matches if m["field"] == field]
        keys = {
            (r["effective_date"], json.dumps(r["value"], ensure_ascii=False))
            for r in rows
        }
        if len(keys) == 1:
            result.append(rows[0])
    return result


def extract_status(pages, title):
    title = compact(title)
    if ("债" in title and "股票" not in title) or any(
        x in title for x in ["可能", "申请", "进展", "方案", "子公司", "参股公司"]
    ):
        return []
    rows = []
    context = compact("".join(pages[:12]))
    has_delisting_period = "退市整理期" in context and not re.search(
        r"(?:不进入|不再进入|不设|不设置|不适用)退市整理期", context
    )
    for j, text in enumerate(pages[:12]):
        t = compact(text)
        patterns = []
        terminal_title = any(k in title for k in ["终止上市", "摘牌", "退市整理期"])
        if terminal_title:
            # A decision date can precede 15/30 further trading sessions. It is
            # never the boundary of the observed A-share population by itself.
            only_explicit_removal = (
                "摘牌" in title
                or "决定" in title
                or any(k in title for k in ["风险提示", "风险公告", "提示性"])
                or has_delisting_period
            )
            patterns += [
                (
                    "listed",
                    False,
                    r"(?:终止上市暨摘牌日|摘牌日期|摘牌日)[为:是]*" + DATE,
                )
            ]
            if not only_explicit_removal:
                patterns += [
                    (
                        "listed",
                        False,
                        r"(?:终止上市(?:的)?日期|终止上市时间)[为:是]*" + DATE,
                    )
                ]
            patterns += [
                (
                    "listed",
                    False,
                    DATE
                    + r"(?:起|日起)?(?:被|由)?(?:北京证券交易所|深圳证券交易所|上海证券交易所|北交所|深交所|上交所)?(?:对其|对公司股票)?(?:予以)?摘牌",
                ),
                ("termination_decision", True, r"终止上市决定日期[为:是]*" + DATE),
            ]
            if not only_explicit_removal:
                patterns += [
                    (
                        "listed",
                        False,
                        DATE
                        + r"(?:起|日起)?(?:在(?:北交所|深交所|上交所|北京证券交易所|深圳证券交易所|上海证券交易所))?终止上市",
                    )
                ]
            if "决定" in title or ("退市整理期" in t and "终止上市时间" in t):
                patterns += [
                    (
                        "termination_decision",
                        True,
                        r"终止上市(?:日期|时间)[为:是]*" + DATE,
                    )
                ]
        if any(k in title for k in ["恢复上市", "重新上市"]):
            patterns += [
                (
                    "listed",
                    True,
                    r"(?:恢复|重新)上市(?:的)?(?:日期|时间)[为:是]*" + DATE,
                )
            ]
        if "停牌" in title:
            patterns += [
                (
                    "suspended",
                    True,
                    r"(?:停牌日期|停牌起始日|股票停牌日|停牌时间)[为:是]*" + DATE,
                ),
                (
                    "suspended",
                    True,
                    DATE
                    + r"(?:起|日起)?(?:开市起|开市|09:30|上午开市)?(?:起|开始)?(?:连续)?停牌",
                ),
            ]
        if "复牌" in title:
            patterns += [
                (
                    "suspended",
                    False,
                    r"(?:复牌日期|股票复牌日|复牌时间)[为:是]*" + DATE,
                ),
                (
                    "suspended",
                    False,
                    DATE
                    + r"(?:起|日起)?(?:开市起|开市|09:30)?(?:起|开始)?(?:恢复交易|复牌)",
                ),
            ]
        if "风险警示" in title:
            if "撤销" not in title and "实施" in title:
                patterns += [
                    (
                        "is_st",
                        True,
                        r"(?:实施(?:退市|其他)?风险警示(?:的)?(?:起始日|起始日期|日期|时间))[为:是]*"
                        + DATE,
                    )
                ]
            # Removing only *ST can leave another ST warning in force.
            if "撤销" in title:
                field = (
                    "delisting_risk_warning"
                    if "退市风险警示" in title
                    else "other_risk_warning"
                )
                patterns += [
                    (
                        field,
                        False,
                        r"撤销(?:退市|其他)?风险警示(?:的)?(?:起始日|起始日期|日期|时间)[为:是]*"
                        + DATE,
                    )
                ]
                patterns += [
                    (field, False, DATE + r"(?:起|日起)?撤销(?:退市|其他)?风险警示")
                ]
                if "及其他风险警示" in title or "和其他风险警示" in title:
                    patterns += [
                        (
                            "is_st",
                            False,
                            r"撤销[^。]{0,18}风险警示(?:的)?(?:起始日|起始日期|日期|时间)[为:是]*"
                            + DATE,
                        )
                    ]
                new_name = re.search(
                    r"(?:股票|证券)简称由[“\"]?[^，。]{1,20}?[”\"]?(?:变更为|变更至|变为)[“\"]([^”\"]+)[”\"]",
                    t,
                )
                if new_name and "ST" not in new_name[1].upper():
                    patterns += [
                        (
                            "is_st",
                            False,
                            DATE + r"(?:起|日起)?撤销(?:退市|其他)?风险警示",
                        )
                    ]
        for field, value, pattern in patterns:
            for m in re.finditer(pattern, t):
                if any(
                    word in t[max(0, m.start() - 12) : m.start()]
                    for word in ["预计", "可能", "若", "如"]
                ):
                    continue
                d = normalized_date(m.groups())
                if d:
                    precision = (
                        "SESSION_DATE"
                        if field != "suspended"
                        else "DATE_ONLY_EVENT_NOT_DAILY_STATUS"
                    )
                    if field == "suspended":
                        clock = re.match(
                            r"(?:[（(])?(上午|下午)?(\d{1,2})[:时](\d{1,2})",
                            t[m.end() :],
                        )
                        if clock:
                            hour, minute = int(clock[2]), int(clock[3])
                            if clock[1] == "下午" and hour < 12:
                                hour += 12
                            if hour < 24 and minute < 60:
                                d += f" {hour:02d}:{minute:02d}:00"
                                precision = "EXPLICIT_INTRADAY_TIMESTAMP"
                        elif "09:30" in m[0] or "开市" in m[0] or "连续停牌" in m[0]:
                            d += " 09:30:00"
                            precision = "EXPLICIT_OPEN_OR_CONTINUOUS_SUSPENSION_START"
                        else:
                            # A day-only event cannot establish that an intraday
                            # halt already started at midnight or the opening.
                            d += " 23:59:59"
                    rows.append(
                        dict(
                            field=field,
                            value=value,
                            effective_date=d,
                            physical_page=j + 1,
                            exact_clause=m[0],
                            evidence_type="UNIQUE_EXPLICIT_ISSUER_EVENT_DATE",
                            continuous_daily_coverage_attested=False,
                            effective_time_precision=precision,
                        )
                    )
    return unique_events(rows)


def named_dates(pages):
    """Contract dates only. A payment schedule is never called actual cash receipt."""
    fields = {
        "record_date": [r"(?:A股)?股权登记日[为:是]*", r"登记日[为:是]*"],
        "ex_date": [
            r"(?:A股)?除权[（(]息[）)]日[为:是]*",
            r"(?:A股)?除权除息日[为:是]*",
            r"(?:A股)?除息日[为:是]*",
        ],
        "scheduled_cash_payment_date": [
            r"(?:A股)?现金红利发放日[为:是]*",
            r"(?:A股)?现金红利派发日[为:是]*",
            r"(?:A股)?派息日[为:是]*",
            r"代派的现金红利将于",
        ],
        "scheduled_share_delivery_date": [
            r"(?:新增)?(?:无限售条件)?(?:流通)?(?:红股)?(?:转增)?(?:股份)?上市日[为:是]*",
            r"红股上市日[为:是]*",
        ],
        "subscription_start": [r"(?:配股)?缴款起始日[为:是]*"],
        "subscription_end": [r"(?:配股)?缴款截止日[为:是]*"],
    }
    found = []
    for j, text in enumerate(pages[:20]):
        t = compact(text)
        for field, labels in fields.items():
            for label in labels:
                for m in re.finditer(label + DATE, t):
                    d = normalized_date(m.groups())
                    if d:
                        found.append(
                            dict(
                                field=field,
                                value=d,
                                effective_date=d,
                                physical_page=j + 1,
                                exact_clause=m[0],
                                evidence_type="CONTRACT_SCHEDULE_NOT_ACTUAL_RECEIPT",
                            )
                        )
        # Common implementation table puts labels in one row and dates in the next.
        pattern = r"(?:A股)?股权登记日(?:A股)?除权[（(]息[）)]日(?:A股)?现金红利发放日(?:A股)?"
        m = re.search(pattern, t)
        if m:
            tail = t[m.end() : m.end() + 130]
            dates = list(re.finditer(DATE, tail))
            if len(dates) == 3:
                for field, dm in zip(
                    ["record_date", "ex_date", "scheduled_cash_payment_date"], dates
                ):
                    d = normalized_date(dm.groups())
                    if d:
                        found.append(
                            dict(
                                field=field,
                                value=d,
                                effective_date=d,
                                physical_page=j + 1,
                                exact_clause=m[0] + tail[: dates[-1].end()],
                                evidence_type="EXPLICIT_A_SHARE_TABLE_COLUMN_ORDER",
                            )
                        )
    return unique_events(found)


def distribution_amounts(pages):
    """Only explicit gross CNY and per-ten-share units; tax-net figures excluded."""
    number = r"(\d+(?:\.\d+)?)"
    patterns = [
        (
            "cash_gross_CNY_per_share",
            10,
            r"每10股(?:派发|派送|派|分配)(?:人民币)?(?:现金红利|现金股利|现金|红利)?(?:人民币)?"
            + number
            + r"元[（(]含税",
        ),
        (
            "cash_gross_CNY_per_share",
            1,
            r"每股(?:派发|派送|派)?(?:现金红利|现金股利|现金|红利)(?:人民币)?"
            + number
            + r"元[（(]含税",
        ),
        ("bonus_shares_per_share", 10, r"每10股(?:送红股|送股)" + number + r"股"),
        (
            "capitalization_shares_per_share",
            10,
            r"每10股(?:转增股本|转增)" + number + r"股",
        ),
    ]
    found = []
    for j, page in enumerate(pages[:20]):
        text = compact(page).replace(",", "")
        for field, denominator, pattern in patterns:
            for m in re.finditer(pattern, text):
                found.append(
                    dict(
                        field=field,
                        value=format((Decimal(m[1]) / denominator).normalize(), "f"),
                        physical_page=j + 1,
                        exact_clause=m[0],
                        source_denominator_shares=denominator,
                        effective_date="ENTITLEMENT_DATES_IN_SEPARATE_ORIGINAL_FIELDS",
                        evidence_type="EXPLICIT_GROSS_OR_SHARE_RATIO_UNIT_CONVERSION",
                    )
                )
    return unique_events(found)


def retirement_codes(pages):
    found = []
    for j, text in enumerate(pages):
        t = compact(text)
        for m in re.finditer(
            r"(?:证券|股票)(?:转让)?代码[:为]?[“\"]?((?:400|420)\d{3})", t
        ):
            found.append(
                dict(
                    code=m[1],
                    physical_page=j + 1,
                    exact_clause=m[0],
                    not_zero_terminal_wealth=True,
                )
            )
    return [r for r in found if sum(x["code"] != r["code"] for x in found) == 0][:1]


def parse_document(record, mapping):
    source = record["source"]
    pages = original_pages(source["archive_path"], source["sha256"])
    title = record["announcement"]["title"]
    security = printed_security(pages, mapping)
    states = extract_status(pages, title) if security else []
    schedules = (
        named_dates(pages)
        if record["evidence_kind"] == "DISTRIBUTION_IMPLEMENTATION" and security
        else []
    )
    return dict(
        security_id=security,
        title=title,
        original_pages=len(pages),
        extractable_text_characters=sum(len(t.strip()) for t in pages),
        states=states,
        distribution_contract_dates=schedules,
        retirement_codes=retirement_codes(pages),
        distribution_contract_amounts=distribution_amounts(pages) if schedules else [],
        actual_cash_received=False,
        original_source_sha256=source["sha256"],
        index_sha256=record["announcement"]["index_sha256"],
        source=source,
        notice_date=record["announcement"]["notice_date"][:10],
        art_code=record["announcement"]["art_code"],
        evidence_kind=record["evidence_kind"],
        transform_sha256=PARSER_VERSION,
        agent_review_only=True,
    )


def calendar():
    return Calendar(pd.read_parquet(V2_RELEASE / "normalized/calendar.parquet").date)
